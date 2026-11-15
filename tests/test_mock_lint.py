#!/usr/bin/env python3
"""Fixture-driven tests for skills/mock-ui/scripts/mock_lint.py.

tests/fixtures/mock-ui/base/ is a two-screen power-apps mockup that lints clean with
--strict and --design. Each tests/fixtures/mock-ui/cases/<name>.json describes one defect
as edits to a copy of that base (find/replace, create a file, delete a file), the extra
arguments, and what the linter must report: the exact set of check ids, the exit code
and the verdict code. A find string that is not in the base fails the test, so an edit
can never silently do nothing.

Assertions are on check ids, exit codes and verdict codes only -- never on wording.

Run:  python -m unittest discover tests
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "mock-ui"
LINTER = SKILL / "scripts" / "mock_lint.py"
SCHEMA = SKILL / "assets" / "sitemap.schema.json"
EXAMPLE = SKILL / "assets" / "example"
PROFILE = ROOT / "shared" / "powerapps-profile.md"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "mock-ui"
BASE = FIXTURES / "base"


def load_module():
    spec = importlib.util.spec_from_file_location("mock_lint", LINTER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_linter(folder: Path, *args: str, cwd: Path = ROOT) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, str(LINTER), str(folder), *args, "--json"],
                          capture_output=True, text=True, encoding="utf-8", cwd=str(cwd))
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - failure path
        raise AssertionError(f"--json did not emit JSON (exit {proc.returncode}).\n"
                             f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}") from exc
    return proc.returncode, payload["report"]


def apply_case(spec: dict, dest: Path) -> None:
    shutil.copytree(BASE, dest)
    for edit in spec["edits"]:
        path = dest / edit["file"]
        if edit.get("delete"):
            path.unlink()
        elif "create" in edit:
            path.write_text(edit["create"], encoding="utf-8")
        else:
            text = path.read_text(encoding="utf-8")
            if edit["find"] not in text:
                raise AssertionError(f"edit find string not in {edit['file']}: "
                                     f"{edit['find'][:80]!r}")
            path.write_text(text.replace(edit["find"], edit["replace"],
                                         -1 if edit.get("all") else 1), encoding="utf-8")


def cases() -> list[tuple[str, dict]]:
    return [(p.stem, json.loads(p.read_text(encoding="utf-8")))
            for p in sorted((FIXTURES / "cases").glob("*.json"))]


def documented_checks() -> set[str]:
    doc = load_module().__doc__
    section = doc.split("ERRORS", 1)[1].split("Exit codes", 1)[0]
    return set(re.findall(r"^  ([a-z][a-z-]+)\s{2,}", section, re.M))


class TestFixtureCases(unittest.TestCase):

    def test_base_is_clean_under_strict_with_design(self):
        code, report = run_linter(BASE, "--strict", "--design", str(BASE / "DESIGN.md"))
        self.assertEqual((code, report["verdict_code"]), (0, "safe"), report["findings"])
        self.assertEqual(report["target"], "power-apps")
        self.assertEqual(report["screens"], ["scrHome", "scrNewRequest"])

    def test_each_case(self):
        found = cases()
        self.assertGreaterEqual(len(found), 40)
        for name, spec in found:
            with self.subTest(case=name), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp) / "mockup"
                apply_case(spec, folder)
                args = [a.replace("{dir}", str(folder)) for a in spec["args"]]
                code, report = run_linter(folder, *args)
                got = sorted({f["check"] for f in report["findings"]})
                expect = spec["expect"]
                self.assertEqual(got, expect["checks"], report["findings"])
                self.assertEqual(code, expect["exit"])
                self.assertEqual(report["verdict_code"], expect["verdict"])

    def test_the_six_named_defects_have_a_case(self):
        """The phase brief names these; each must exist and fail the way it says."""
        named = {"dead-button": "dead-control", "broken-href": "broken-link",
                 "nav-disagrees-with-target": "nav-mismatch",
                 "external-font": "external-resource",
                 "unreachable-screen": "unreachable", "sitemap-disagrees": "sitemap-nav"}
        by_name = dict(cases())
        for case, check in named.items():
            with self.subTest(case=case):
                self.assertIn(case, by_name)
                self.assertIn(check, by_name[case]["expect"]["checks"])

    def test_every_documented_check_is_exercised(self):
        documented = documented_checks()
        self.assertGreaterEqual(len(documented), 30)
        exercised = {c for _n, spec in cases() for c in spec["expect"]["checks"]}
        self.assertEqual(sorted(documented - exercised), [],
                         "documented check ids no fixture exercises")
        self.assertEqual(sorted(exercised - documented), [],
                         "fixtures expect check ids the docstring does not document")

    def test_every_verdict_is_reachable(self):
        verdicts = {spec["expect"]["verdict"] for _n, spec in cases()}
        self.assertEqual(verdicts, {"safe", "unverified", "will_fail", "unproven"})


class TestProfileCoverage(unittest.TestCase):

    def test_every_profile_effect_has_a_detector(self):
        """A new impossible_css id in the profile must not be silently ignored."""
        ids = set(re.findall(r"impossible_css\[id=([a-z0-9-]+)\]",
                             PROFILE.read_text(encoding="utf-8")))
        self.assertTrue(ids)
        source = LINTER.read_text(encoding="utf-8")
        for pid in sorted(ids):
            with self.subTest(id=pid):
                self.assertIn(f'"{pid}"', source)


class TestSitemapSchema(unittest.TestCase):

    def setUp(self):
        self.mod = load_module()
        self.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def test_example_and_base_validate(self):
        for folder in (EXAMPLE, BASE):
            data = json.loads((folder / "sitemap.json").read_text(encoding="utf-8"))
            self.assertEqual(self.mod.validate_schema(data, self.schema, self.schema), [])

    def test_standard_library_validator_agrees_with_jsonschema(self):
        try:
            import jsonschema  # type: ignore
        except ImportError:  # pragma: no cover - optional dependency
            self.skipTest("jsonschema not installed (pip install jsonschema)")
        jsonschema.Draft202012Validator.check_schema(self.schema)
        validator = jsonschema.Draft202012Validator(self.schema)
        good = json.loads((EXAMPLE / "sitemap.json").read_text(encoding="utf-8"))
        bad_docs = []
        for mutate in (
            lambda d: d.pop("start"),
            lambda d: d.update(version=2),
            lambda d: d.update(target="mobile"),
            lambda d: d.update(extra=True),
            lambda d: d["screens"][0].update(id="Home"),
            lambda d: d["screens"][0].update(file="Home.HTML"),
            lambda d: d["screens"][0]["nav"].append({"label": "x"}),
            lambda d: d["screens"][0]["data"].append(
                {"source": "my list", "mode": "read", "fields": []}),
            lambda d: d["screens"][0]["actions"].append({"id": "Submit", "on": "x"}),
            lambda d: d["canvas"].update(width="1366"),
            lambda d: d["screens"][0].update(kind="popup"),
            lambda d: d.update(screens=[]),
        ):
            doc = json.loads(json.dumps(good))
            mutate(doc)
            bad_docs.append(doc)
        for doc in [good] + bad_docs:
            ours = not self.mod.validate_schema(doc, self.schema, self.schema)
            theirs = validator.is_valid(doc)
            self.assertEqual(ours, theirs, json.dumps(doc)[:200])


class TestExample(unittest.TestCase):
    """assets/example/ is what the skill points at as 'finished and lint-clean'."""

    def test_example_lints_clean_for_its_declared_target(self):
        sitemap = json.loads((EXAMPLE / "sitemap.json").read_text(encoding="utf-8"))
        code, report = run_linter(EXAMPLE, "--strict", "--design",
                                  str(EXAMPLE / sitemap["design"]))
        self.assertEqual(report["target"], sitemap["target"])
        self.assertEqual((code, report["verdict_code"]), (0, "safe"), report["findings"])
        self.assertEqual(len(report["screens"]), 3)

    def test_example_works_with_javascript_off(self):
        """No script anywhere, and every data-nav rides on a real href or form action."""
        mod = load_module()
        for path in sorted(EXAMPLE.glob("*.html")):
            page = mod.Page(path.read_text(encoding="utf-8"))
            self.assertFalse([e for e in page.elements() if e.tag == "script"], path.name)
            for el in page.elements():
                if not el.get("data-nav"):
                    continue
                if el.tag == "a":
                    self.assertTrue((el.get("href") or "").endswith(".html"), path.name)
                else:
                    form = next(a for a in el.ancestors() if a.tag == "form")
                    self.assertTrue(form.get("action", "").endswith(".html"), path.name)

    def test_example_index_links_every_screen_in_flow_order(self):
        sitemap = json.loads((EXAMPLE / "sitemap.json").read_text(encoding="utf-8"))
        index = (EXAMPLE / "index.html").read_text(encoding="utf-8")
        positions = [index.find(f'href="{s["file"]}"') for s in sitemap["screens"]]
        self.assertNotIn(-1, positions)
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(sitemap["screens"][0]["id"], sitemap["start"])


class TestConversionSample(unittest.TestCase):
    """One example page converted by following create-app's SKILL.md. One sample, not
    proof that every mockup converts; it keeps the contract and create-app honest with
    each other while phase 04 has not changed create-app."""

    CONVERTED = FIXTURES / "converted" / "scrNewLoan.pa.yaml"
    PA_LINT = ROOT / "skills" / "create-app" / "scripts" / "pa_lint.py"

    def test_sample_lints_safe_to_paste(self):
        proc = subprocess.run([sys.executable, str(self.PA_LINT), str(self.CONVERTED),
                               "--json"], capture_output=True, text=True, cwd=str(ROOT))
        report = json.loads(proc.stdout)["files"][0]
        self.assertEqual(report["verdict_code"], "safe", report["findings"])

    def test_sample_screen_name_is_the_mockup_screen_id(self):
        page = load_module().Page((EXAMPLE / "new-loan.html").read_text(encoding="utf-8"))
        screen = page.first("body").get("data-screen")
        text = self.CONVERTED.read_text(encoding="utf-8")
        self.assertRegex(text, rf"(?m)^  {screen}:$")


class TestCli(unittest.TestCase):

    def test_runs_from_outside_the_repo_by_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, report = run_linter(EXAMPLE, cwd=Path(tmp))
            self.assertEqual((code, report["verdict_code"]), (0, "safe"), report["findings"])

    def test_text_output_ends_in_a_verdict(self):
        proc = subprocess.run([sys.executable, str(LINTER), str(BASE)], capture_output=True,
                              text=True, encoding="utf-8", cwd=str(ROOT))
        self.assertTrue(proc.stdout.strip().splitlines()[-1].startswith("VERDICT: "))

    def test_not_a_folder_exits_2(self):
        proc = subprocess.run([sys.executable, str(LINTER), str(BASE / "home.html")],
                              capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
