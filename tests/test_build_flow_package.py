#!/usr/bin/env python3
"""Tests for skills/create-flow/scripts/build_flow_package.py.

The round trip is the test that matters: building assets/example/SendTestEmail.flow.json
must reproduce the owner's reference package (tests/fixtures/flows/reference-package.zip)
once GUIDs and the creation time are normalised -- the same entry names in the same
order, and equal JSON in all five files.

Run:  python -m unittest discover tests
"""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "create-flow"
BUILDER = SKILL / "scripts" / "build_flow_package.py"
EXAMPLE = SKILL / "assets" / "example" / "SendTestEmail.flow.json"
REFERENCE = ROOT / "tests" / "fixtures" / "flows" / "reference-package.zip"
CREATED = "2026-11-09T07:29:55.686228Z"
GUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
STAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{7}Z")


def load_builder():
    spec = importlib.util.spec_from_file_location("build_flow_package", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(spec_path: Path, out: Path, *args: str, cwd: Path = ROOT):
    return subprocess.run([sys.executable, str(BUILDER), str(spec_path), "--out", str(out),
                           *args], capture_output=True, text=True, encoding="utf-8",
                          cwd=str(cwd))


def normalised(path: Path) -> list[tuple[str, str]]:
    """(entry name, file text) with every GUID renamed by first appearance and the
    creation time blanked, so two packages built at different moments compare equal."""
    mapping: dict[str, str] = {}

    def sub(text: str) -> str:
        text = GUID_RE.sub(lambda m: mapping.setdefault(m.group(0), f"GUID-{len(mapping)}"),
                           text)
        return STAMP_RE.sub("CREATED", text)

    with zipfile.ZipFile(path) as zf:
        return [(sub(i.filename), sub(zf.read(i).decode("utf-8"))) for i in zf.infolist()]


class TestRoundTrip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.proc = build(EXAMPLE, cls.out, "--seed", "test", "--created-time", CREATED)
        cls.zip = cls.out / "SendTestEmail_LegacyPackage.zip"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_builds_and_verifies(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stdout + self.proc.stderr)
        self.assertIn("VERIFIED", self.proc.stdout)
        self.assertTrue(self.zip.is_file())

    def test_same_entries_and_equal_json_as_the_reference(self):
        ours, ref = normalised(self.zip), normalised(REFERENCE)
        self.assertEqual([n for n, _ in ours], [n for n, _ in ref])
        for (name, a), (_, b) in zip(ours, ref):
            with self.subTest(entry=name):
                self.assertEqual(json.loads(a), json.loads(b))

    def test_same_bytes_as_the_reference_after_normalising(self):
        # Stronger than equal JSON: key order, indent and escapes match too.
        self.assertEqual(normalised(self.zip), normalised(REFERENCE))

    def test_reference_fixture_verifies(self):
        self.assertEqual(load_builder().verify_package(REFERENCE), [])


class TestArchiveShape(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        build(EXAMPLE, cls.out)
        cls.zip = cls.out / "SendTestEmail_LegacyPackage.zip"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_shape(self):
        with zipfile.ZipFile(self.zip) as zf:
            infos = zf.infolist()
            self.assertEqual(len(infos), 5)
            self.assertEqual(infos[0].filename, "manifest.json")
            for info in infos:
                self.assertFalse(info.filename.endswith("/"), "no directory entries")
                self.assertNotIn("\\", info.filename)
                self.assertEqual(info.compress_type, zipfile.ZIP_DEFLATED)
                raw = zf.read(info)
                self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), "no byte-order mark")
                self.assertNotIn(b"\r", raw)
                self.assertFalse(raw.endswith(b"\n"))
                raw.decode("ascii")  # non-ASCII is written as \\uXXXX
            self.assertEqual(sum(1 for i in infos if "/" not in i.filename), 1,
                             "only manifest.json at the root, no wrapping folder")

    def test_fresh_guids_without_a_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            build(EXAMPLE, Path(tmp))
            other = Path(tmp) / "SendTestEmail_LegacyPackage.zip"
            with zipfile.ZipFile(self.zip) as a, zipfile.ZipFile(other) as b:
                self.assertNotEqual(a.namelist(), b.namelist())

    def test_no_real_connection_name(self):
        with zipfile.ZipFile(self.zip) as zf:
            definition = json.loads(zf.read(zf.namelist()[2]))
        ref = definition["properties"]["connectionReferences"]["shared_office365"]
        self.assertTrue(ref["connectionName"].startswith("shared-office365-"))
        self.assertEqual(ref["source"], "Embedded")


class TestBehaviour(unittest.TestCase):
    def test_deterministic_with_seed_and_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a", Path(tmp) / "b"
            build(EXAMPLE, a, "--seed", "s", "--created-time", CREATED)
            build(EXAMPLE, b, "--seed", "s", "--created-time", CREATED)
            name = "SendTestEmail_LegacyPackage.zip"
            self.assertEqual((a / name).read_bytes(), (b / name).read_bytes())

    def test_refuses_on_lint_errors(self):
        spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        spec["connectors"] = []
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Bad.flow.json"
            path.write_text(json.dumps(spec), encoding="utf-8")
            proc = build(path, Path(tmp))
            self.assertEqual(proc.returncode, 1)
            self.assertIn("WILL FAIL", proc.stdout)
            self.assertFalse(list(Path(tmp).glob("*.zip")))

    def test_placeholders_filled_or_listed(self):
        spec = copy.deepcopy(json.loads(EXAMPLE.read_text(encoding="utf-8")))
        params = spec["actions"]["Send_an_email_(V2)"]["inputs"]["parameters"]
        params["emailMessage/Subject"] = "{{Subject}} / {{Footer}}"
        for n in ("Subject", "Footer"):
            spec["placeholders"][n] = {"description": n, "setAfterImport": "the email step"}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Ph.flow.json"
            path.write_text(json.dumps(spec), encoding="utf-8")
            proc = build(path, Path(tmp), "--set", "Subject=Hello")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("{{Footer}}", proc.stdout)  # in the post-import checklist
            with zipfile.ZipFile(Path(tmp) / "SendTestEmail_LegacyPackage.zip") as zf:
                text = zf.read(zf.namelist()[2]).decode("ascii")
            self.assertIn("Hello / {{Footer}}", text)
            # the value never goes back into the spec
            self.assertNotIn("Hello", path.read_text(encoding="utf-8"))

    def test_verify_rejects_a_wrapping_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            wrapped = Path(tmp) / "wrapped.zip"
            with zipfile.ZipFile(REFERENCE) as src, \
                    zipfile.ZipFile(wrapped, "w", zipfile.ZIP_DEFLATED) as dst:
                for info in src.infolist():
                    dst.writestr(f"Package/{info.filename}", src.read(info))
            proc = subprocess.run([sys.executable, str(BUILDER), "--verify", str(wrapped)],
                                  capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("NOT VERIFIED", proc.stdout)

    def test_verify_rejects_mismatched_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.zip"
            with zipfile.ZipFile(REFERENCE) as src, \
                    zipfile.ZipFile(bad, "w", zipfile.ZIP_DEFLATED) as dst:
                for info in src.infolist():
                    data = src.read(info)
                    if info.filename.endswith("apisMap.json"):
                        data = b'{\n  "shared_office365": "00000000-0000-4000-8000-0000000000ff"\n}'
                    dst.writestr(info, data)
            self.assertTrue(load_builder().verify_package(bad))

    def test_runs_from_outside_the_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = build(EXAMPLE, Path(tmp), cwd=Path(tmp))
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
