#!/usr/bin/env python3
"""Fixture-driven tests for skills/design-md/scripts/design_lint.py.

Each fixture under tests/fixtures/design-md/{valid,invalid}/ is a small DESIGN.md paired
with a <name>.expected.json sidecar naming the target, the check ids that must fire, the
exit code and the verdict code. Every invalid fixture is the valid base,
valid/minimal-clean.md, with one defect.

Assertions are on check ids, exit codes and verdict codes only -- never on wording.

Run:  python -m unittest discover tests
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "design-md"
LINTER = SKILL / "scripts" / "design_lint.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "design-md"
EXAMPLE = SKILL / "assets" / "example" / "DESIGN.md"
TEMPLATE = SKILL / "assets" / "DESIGN.template.md"


def run_linter(*args: str, cwd: Path = ROOT) -> tuple[int, dict, str]:
    proc = subprocess.run([sys.executable, str(LINTER), *args, "--json"],
                          capture_output=True, text=True, encoding="utf-8", cwd=str(cwd))
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - failure path
        raise AssertionError(f"--json did not emit JSON (exit {proc.returncode}).\n"
                             f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}") from exc
    return proc.returncode, payload, proc.stderr


def fixture_pairs() -> list[tuple[Path, dict]]:
    pairs = []
    for md in sorted(FIXTURES.rglob("*.md")):
        sidecar = md.with_suffix(".expected.json")
        if not sidecar.is_file():
            raise AssertionError(f"fixture {md.name} has no .expected.json sidecar")
        pairs.append((md, json.loads(sidecar.read_text(encoding="utf-8"))))
    return pairs


def load_module():
    spec = importlib.util.spec_from_file_location("design_lint", LINTER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def documented_ids(section: str) -> set[str]:
    """Check ids listed under a heading of the linter's docstring."""
    doc = load_module().__doc__
    block = doc.split(section, 1)[1].split("\n\n", 1)[0]
    return set(re.findall(r"^  ([a-z][a-z-]+)\s", block, re.M))


class TestFixtures(unittest.TestCase):
    def test_enough_fixtures(self):
        self.assertGreaterEqual(len(fixture_pairs()), 20)

    def test_fixtures_produce_expected_findings(self):
        for md, expected in fixture_pairs():
            with self.subTest(fixture=md.name):
                code, payload, stderr = run_linter(str(md), "--target", expected["target"])
                report = payload["files"][0]
                got = Counter(f["check"] for f in report["findings"])
                want = Counter(f["check"] for f in expected["expected_findings"])
                self.assertEqual(got, want, f"\n{md.name}: {expected['description']}")
                self.assertEqual(code, expected["expected_exit_code"], md.name)
                self.assertEqual(report["verdict_code"], expected["expected_verdict_code"],
                                 md.name)
                self.assertEqual(stderr.strip(), "", "linter must not leak a traceback")

    def test_every_error_check_has_an_invalid_fixture(self):
        errors = documented_ids("ERRORS")
        self.assertGreaterEqual(len(errors), 15, "docstring ERRORS list did not parse")
        covered = set()
        for md, expected in fixture_pairs():
            if md.parent.name == "invalid":
                covered |= {f["check"] for f in expected["expected_findings"]}
        self.assertEqual(errors - covered, set(), "error checks with no invalid fixture")

    def test_every_documented_check_is_emitted_somewhere(self):
        documented = (documented_ids("ERRORS") | documented_ids("WARNINGS")
                      | documented_ids("With --target power-apps"))
        covered = {f["check"] for _, e in fixture_pairs() for f in e["expected_findings"]}
        self.assertEqual(documented - covered, set(), "documented checks never exercised")


class TestCli(unittest.TestCase):
    def test_runs_from_outside_the_repo_by_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, payload, _ = run_linter(str(FIXTURES / "valid" / "minimal-clean.md"),
                                          cwd=Path(tmp))
        self.assertEqual(code, 0)
        self.assertEqual(payload["files"][0]["verdict_code"], "safe")

    def test_power_apps_profile_is_found_from_outside_the_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, payload, _ = run_linter(str(FIXTURES / "valid" / "minimal-clean.md"),
                                       "--target", "power-apps", cwd=Path(tmp))
        self.assertIsNone(payload["files"][0]["degraded"])

    def test_strict_turns_warnings_into_exit_2(self):
        code, _, _ = run_linter(str(FIXTURES / "invalid" / "warnings-prose.md"), "--strict")
        self.assertEqual(code, 2)

    def test_missing_profile_is_unproven_not_safe(self):
        code, payload, _ = run_linter(str(FIXTURES / "valid" / "minimal-clean.md"),
                                      "--target", "power-apps",
                                      "--profile", str(FIXTURES / "no-such-profile.md"))
        self.assertEqual(payload["files"][0]["verdict_code"], "unproven")
        self.assertEqual(code, 0)
        code, _, _ = run_linter(str(FIXTURES / "valid" / "minimal-clean.md"),
                                "--target", "power-apps", "--strict",
                                "--profile", str(FIXTURES / "no-such-profile.md"))
        self.assertEqual(code, 2)

    def test_missing_file_is_a_usage_error(self):
        proc = subprocess.run([sys.executable, str(LINTER), "nope.md"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)

    def test_text_output_ends_in_a_verdict(self):
        proc = subprocess.run([sys.executable, str(LINTER),
                               str(FIXTURES / "invalid" / "contrast.md")],
                              capture_output=True, text=True, encoding="utf-8")
        self.assertTrue(proc.stdout.strip().splitlines()[-1].startswith("VERDICT:"))


class TestColours(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_module()

    def test_black_on_white_is_21(self):
        black, white = self.m.parse_color("#000"), self.m.parse_color("white")
        self.assertAlmostEqual(self.m.contrast_ratio(black, white), 21.0, places=2)

    def test_forms_that_parse(self):
        p = self.m.parse_color
        self.assertEqual(self.m.to_hex(p("rgb(255, 0, 0)")), "#ff0000")
        self.assertEqual(self.m.to_hex(p("rgb(0 128 255 / 50%)")), "#0080ff80")
        self.assertEqual(self.m.to_hex(p("hsl(120, 100%, 25%)")), "#008000")
        self.assertEqual(self.m.to_hex(p("#abcd")), "#aabbccdd")
        self.assertEqual(p("transparent")[3], 0.0)

    def test_forms_that_do_not(self):
        self.assertEqual(self.m.parse_color("oklch(0.7 0.1 200)"), "unparsed")
        self.assertIsNone(self.m.parse_color("#12345"))
        self.assertIsNone(self.m.parse_color("bluish"))
        self.assertIsNone(self.m.parse_color("rgb(300, 0, 0)"))

    def test_dimensions(self):
        d = self.m.is_dimension
        self.assertTrue(d("12px") and d("-0.02em") and d("1.5rem") and d(0) and d("0"))
        self.assertFalse(d("12") or d(12) or d("12pt") or d("1.5"))
        self.assertTrue(d(1.5, allow_number=True))
        self.assertTrue(self.m.is_padding("8px 16px 4px"))
        self.assertFalse(self.m.is_padding("8px 16"))


class TestBundledFiles(unittest.TestCase):
    def test_example_lints_clean(self):
        code, payload, _ = run_linter(str(EXAMPLE))
        report = payload["files"][0]
        self.assertEqual(report["findings"], [], "assets/example/DESIGN.md must lint clean")
        self.assertEqual(code, 0)

    def test_template_has_no_errors_and_all_sections(self):
        _, payload, _ = run_linter(str(TEMPLATE))
        checks = {f["check"] for f in payload["files"][0]["findings"]}
        self.assertEqual(payload["files"][0]["errors"], 0, checks)
        self.assertNotIn("section-missing", checks)


if __name__ == "__main__":
    unittest.main()
