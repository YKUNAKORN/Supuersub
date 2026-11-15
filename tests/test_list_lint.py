#!/usr/bin/env python3
"""Fixture-driven tests for skills/create-list/scripts/list_lint.py.

tests/fixtures/lists/lint/base/ holds two specs (Sites, and Requests with a lookup to
Sites) that use every type in the type table and lint clean once every evidence row is
trusted. Each tests/fixtures/lists/lint/cases/<name>.json describes one defect as edits to
a copy of that base, the extra arguments, and what the linter must report: the exact
set of check ids, the exit code and the verdict code.

The cases run against a copy of references/import-behavior.md with every level set to
import-tested, so the unverified-behavior warning does not mask the check under test.
Separate tests run against the real evidence table.

Assertions are on check ids, exit codes and verdict codes only -- never on wording.

Run:  python -m unittest discover tests
"""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "create-list"
LINTER = SKILL / "scripts" / "list_lint.py"
EVIDENCE = SKILL / "references" / "import-behavior.md"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "lists" / "lint"
BASE = FIXTURES / "base"
CASES = sorted((FIXTURES / "cases").glob("*.json"))

try:
    import jsonschema  # noqa: F401
    HAVE_JSONSCHEMA = True
except ImportError:  # pragma: no cover
    HAVE_JSONSCHEMA = False


def load_module():
    spec = importlib.util.spec_from_file_location("list_lint", LINTER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_linter(paths, *args: str, cwd: Path = ROOT) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, str(LINTER), *map(str, paths), *args, "--json"],
                          capture_output=True, text=True, encoding="utf-8", cwd=str(cwd))
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - failure path
        raise AssertionError(f"--json did not emit JSON (exit {proc.returncode}).\n"
                             f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}") from exc
    return proc.returncode, payload["report"]


def trusted_evidence(dest: Path) -> Path:
    text = EVIDENCE.read_text(encoding="utf-8")
    text = re.sub(r"\| (unverified|export) \|", "| import-tested |", text)
    path = dest / "evidence-trusted.md"
    path.write_text(text, encoding="utf-8")
    return path


def _walk(doc, path: str):
    """(parent, last key) for a slash path; list indexes are numbers."""
    parts = path.split("/")
    node = doc
    for p in parts[:-1]:
        node = node[int(p)] if isinstance(node, list) else node[p]
    last = parts[-1]
    return node, (int(last) if isinstance(node, list) else last)


def apply_edits(edits: list[dict], folder: Path) -> None:
    for edit in edits:
        path = folder / edit["file"]
        if "write" in edit:
            path.write_text(edit["write"], encoding="utf-8")
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        if "set" in edit:
            parent, key = _walk(doc, edit["set"])
            parent[key] = edit["value"]
        elif "delete" in edit:
            parent, key = _walk(doc, edit["delete"])
            if isinstance(parent, list):
                assert key < len(parent), f"no index {key} to delete in {edit}"
            else:
                assert key in parent, f"no key {key!r} to delete in {edit}"
            del parent[key]
        elif "append" in edit:
            parent, key = _walk(doc, edit["append"])
            parent[key].append(edit["value"])
        elif "rename_key" in edit:
            old, new = edit["rename_key"]
            for row in doc["rows"]:
                assert old in row, f"row without {old!r}"
                row[new] = row.pop(old)
        elif "generate_rows" in edit:
            template = doc["rows"][0]
            doc["rows"] = []
            for i in range(edit["generate_rows"]):
                row = copy.deepcopy(template)
                for k, v in row.items():
                    if isinstance(v, str):
                        row[k] = v if k == "Region" else f"{v}{i}"
                doc["rows"].append(row)
        else:  # pragma: no cover
            raise AssertionError(f"unknown edit {edit}")
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


class CaseTests(unittest.TestCase):
    def test_cases_exist(self):
        self.assertGreaterEqual(len(CASES), 20)

    def test_every_check_has_a_case(self):
        mod = load_module()
        ids = set(re.findall(r"^  ([a-z][a-z-]+[a-z]) ", mod.__doc__, re.M))
        covered = set()
        for case in CASES:
            covered |= set(json.loads(case.read_text(encoding="utf-8"))["checks"])
        covered.add("unverified-behavior")  # tested against the real table below
        self.assertEqual(sorted(ids - covered), [], "check ids without a fixture case")

    def test_each_case(self):
        for case_path in CASES:
            case = json.loads(case_path.read_text(encoding="utf-8"))
            with self.subTest(case=case_path.stem), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                work = tmp / "specs"
                shutil.copytree(BASE, work)
                apply_edits(case["edits"], work)
                specs = [work / n for n in case["only"]] if "only" in case else [work]
                code, report = run_linter(specs, *case.get("args", []), "--evidence",
                                          str(trusted_evidence(tmp)))
                found = sorted({f["check"] for f in report["findings"]})
                expect = sorted(case["checks"])
                if not HAVE_JSONSCHEMA and case_path.stem != "clean":  # pragma: no cover
                    self.assertTrue(set(expect) - {"spec-invalid"} <= set(found))
                    continue
                self.assertEqual(found, expect, report["verdict"])
                if HAVE_JSONSCHEMA:
                    self.assertEqual(code, case["exit"])
                    self.assertEqual(report["verdict_code"], case["verdict"])


class OldJsonschemaTests(unittest.TestCase):
    """jsonschema older than 4.0 has no Draft202012Validator; the linter must not crash."""

    @unittest.skipUnless(HAVE_JSONSCHEMA, "jsonschema not installed")
    def test_falls_back_to_draft7_when_2020_12_is_missing(self):
        import jsonschema
        mod = load_module()
        # A jsonschema 3.x look-alike: Draft 7 exists, Draft202012Validator does not.
        old = types.SimpleNamespace(Draft7Validator=jsonschema.Draft7Validator)
        with mock.patch.dict(sys.modules, {"jsonschema": old}):
            linter = mod.Linter()
        self.assertIsInstance(linter.validator, jsonschema.Draft7Validator)
        self.assertEqual(linter.degraded, "")  # the bundled schema has no 2020-12-only keyword
        self.assertTrue(list(linter.validator.iter_errors({})))

    @unittest.skipUnless(HAVE_JSONSCHEMA, "jsonschema not installed")
    def test_2020_12_only_keyword_is_reported_unproven_on_draft7(self):
        import jsonschema
        mod = load_module()
        validator, note = mod.make_validator(
            types.SimpleNamespace(Draft7Validator=jsonschema.Draft7Validator),
            {"type": "array", "prefixItems": [{"type": "string"}]})
        self.assertIsNotNone(validator)
        self.assertIn("prefixItems", note)

    def test_no_validator_class_degrades_like_a_missing_package(self):
        mod = load_module()
        validator, note = mod.make_validator(types.SimpleNamespace(), {})
        self.assertIsNone(validator)
        self.assertIn("too old", note)


class EvidenceTests(unittest.TestCase):
    def test_base_warns_on_unverified_rows(self):
        code, report = run_linter([BASE])
        self.assertEqual(code, 0)
        checks = {f["check"] for f in report["findings"]}
        self.assertEqual(checks, {"unverified-behavior"})
        rows = " ".join(f["message"] for f in report["findings"])
        for row_id in ("offer-person", "offer-hyperlink", "title-mapping",
                       "choice-from-data"):
            self.assertIn(row_id, rows)
        self.assertNotIn("csv-encoding", rows)
        self.assertEqual(report["creation_order"], ["Sites", "Requests"])

    def test_csv_adds_the_csv_rows(self):
        _, report = run_linter([BASE], "--format", "csv")
        rows = " ".join(f["message"] for f in report["findings"])
        self.assertIn("csv-encoding", rows)
        self.assertIn("csv-values", rows)

    def test_empty_table_names_its_row(self):
        _, report = run_linter([BASE], "--empty-table")
        self.assertIn("empty-table", " ".join(f["message"] for f in report["findings"]))

    def test_trusting_a_row_removes_its_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = re.sub(r"(\| `offer-person` \|[^\n]*?\| )unverified( \|)",
                          r"\1import-tested\2", EVIDENCE.read_text(encoding="utf-8"))
            ev = Path(tmp) / "ev.md"
            ev.write_text(text, encoding="utf-8")
            _, report = run_linter([BASE], "--evidence", str(ev))
        rows = " ".join(f["message"] for f in report["findings"])
        self.assertNotIn("offer-person", rows)
        self.assertIn("offer-hyperlink", rows)

    def test_evidence_and_types_parse(self):
        mod = load_module()
        ev = mod.load_evidence()
        self.assertTrue(all(v["level"] in mod.LEVELS for v in ev.values()))
        self.assertEqual(ev["row-limit"]["level"], "doc")
        types = mod.load_types()
        self.assertEqual(types["lookup"]["imports"][0], "skip")
        self.assertEqual(types["date"]["imports"], ["datetime"])


class CommandLineTests(unittest.TestCase):
    def test_runs_from_outside_the_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, report = run_linter([BASE / "Sites.list.json"], cwd=Path(tmp))
        self.assertEqual(code, 0)
        self.assertEqual(report["lists"][0]["name"], "Sites")

    def test_missing_file_is_a_usage_error(self):
        proc = subprocess.run([sys.executable, str(LINTER), "no-such.list.json"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)

    def test_without_jsonschema_the_verdict_is_unproven(self):
        script = ("import sys, runpy; sys.modules['jsonschema'] = None; "
                  f"sys.argv = ['list_lint.py', {str(BASE)!r}, '--json']; "
                  f"runpy.run_path({str(LINTER)!r}, run_name='__main__')")
        proc = subprocess.run([sys.executable, "-c", script], capture_output=True,
                              text=True, encoding="utf-8")
        report = json.loads(proc.stdout)["report"]
        self.assertEqual(report["verdict_code"], "unproven")
        self.assertIn("pip install jsonschema", report["degraded"])

    def test_human_output_ends_in_a_verdict(self):
        proc = subprocess.run([sys.executable, str(LINTER), str(BASE)],
                              capture_output=True, text=True, encoding="utf-8")
        self.assertTrue(proc.stdout.strip().splitlines()[-1].startswith("VERDICT:"))


if __name__ == "__main__":
    unittest.main()
