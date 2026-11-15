#!/usr/bin/env python3
"""Fixture-driven tests for skills/create-app/scripts/pa_lint.py.

Each fixture under tests/fixtures/{valid,invalid}/ is a small .pa.yaml paired with a
<name>.expected.json sidecar naming the layer and check id that must fire.

Assertions are on **check ids and exit codes only** -- never on message wording -- so
rephrasing a diagnostic does not break the suite.

Run:  python -m unittest discover tests
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINTER = ROOT / "skills" / "create-app" / "scripts" / "pa_lint.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
EXAMPLES = ROOT / "skills" / "create-app" / "assets" / "examples"


def run_linter(*args: str) -> tuple[int, dict, str]:
    """Run the linter and return (exit_code, parsed_json, stderr)."""
    proc = subprocess.run(
        [sys.executable, str(LINTER), *args, "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT),
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - failure path
        raise AssertionError(
            f"--json did not emit valid JSON (exit {proc.returncode}).\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        ) from exc
    return proc.returncode, payload, proc.stderr


def fixture_pairs() -> list[tuple[Path, dict]]:
    pairs = []
    for yaml_path in sorted(FIXTURES.rglob("*.pa.yaml")):
        sidecar = yaml_path.with_name(yaml_path.name.replace(".pa.yaml", ".expected.json"))
        if not sidecar.is_file():
            raise AssertionError(f"fixture {yaml_path.name} has no .expected.json sidecar")
        pairs.append((yaml_path, json.loads(sidecar.read_text(encoding="utf-8"))))
    return pairs


def finding_ids(file_report: dict) -> set[tuple[str, str]]:
    return {(f["layer"], f["check"]) for f in file_report["findings"]}


def expected_ids(expected: dict) -> set[tuple[str, str]]:
    return {(f["layer"], f["check"]) for f in expected["expected_findings"]}


class TestLinterExists(unittest.TestCase):
    def test_linter_script_is_present(self):
        self.assertTrue(LINTER.is_file(), f"missing {LINTER}")

    def test_every_fixture_has_a_sidecar(self):
        self.assertGreaterEqual(len(fixture_pairs()), 10, "expected at least 10 fixtures")


class TestFixtures(unittest.TestCase):
    """Every fixture must produce exactly the findings its sidecar declares."""

    def test_fixtures_produce_expected_findings(self):
        for yaml_path, expected in fixture_pairs():
            with self.subTest(fixture=yaml_path.name):
                code, payload, stderr = run_linter(str(yaml_path))
                self.assertEqual(len(payload["files"]), 1, "one file in, one report out")
                report = payload["files"][0]

                self.assertEqual(
                    finding_ids(report),
                    expected_ids(expected),
                    f"\n{yaml_path.name}: {expected['description']}"
                    f"\n  got:      {sorted(finding_ids(report))}"
                    f"\n  expected: {sorted(expected_ids(expected))}",
                )
                self.assertEqual(code, expected["expected_exit_code"], yaml_path.name)
                self.assertEqual(
                    report["verdict_code"], expected["expected_verdict_code"], yaml_path.name
                )
                self.assertEqual(stderr.strip(), "", "linter must not leak a traceback")


class TestLayerShortCircuit(unittest.TestCase):
    """A layer that makes later layers meaningless must stop the run."""

    def test_parse_error_suppresses_later_layers(self):
        _, payload, _ = run_linter(str(FIXTURES / "invalid" / "broken-yaml.pa.yaml"))
        layers = {f["layer"] for f in payload["files"][0]["findings"]}
        self.assertEqual(layers, {"L0"})

    def test_schema_error_suppresses_catalog_and_convention_layers(self):
        _, payload, _ = run_linter(str(FIXTURES / "invalid" / "missing-equals.pa.yaml"))
        layers = {f["layer"] for f in payload["files"][0]["findings"]}
        self.assertEqual(layers, {"L1"})


class TestFindingShape(unittest.TestCase):
    def test_schema_findings_carry_a_yaml_path(self):
        _, payload, _ = run_linter(str(FIXTURES / "invalid" / "missing-equals.pa.yaml"))
        finding = payload["files"][0]["findings"][0]
        self.assertTrue(finding["path"].startswith("Screens.Home.Children["))
        self.assertTrue(finding["path"].endswith("Properties.Text"))

    def test_parse_error_reports_line_and_column(self):
        _, payload, _ = run_linter(str(FIXTURES / "invalid" / "broken-yaml.pa.yaml"))
        finding = payload["files"][0]["findings"][0]
        self.assertIsInstance(finding["line"], int)
        self.assertIsInstance(finding["column"], int)

    def test_severity_maps_errors_to_l0_l1_and_warnings_to_l2_l3(self):
        for name, layer, severity in [
            ("missing-equals.pa.yaml", "L1", "error"),
            ("invented-control-type.pa.yaml", "L2", "warning"),
        ]:
            with self.subTest(fixture=name):
                _, payload, _ = run_linter(str(FIXTURES / "invalid" / name))
                match = [f for f in payload["files"][0]["findings"] if f["layer"] == layer]
                self.assertTrue(match)
                self.assertEqual(match[0]["severity"], severity)


class TestIsolatedTestSnippet(unittest.TestCase):
    """Acceptance criterion: an L2 warning ships a ready-to-paste test snippet."""

    def _l2_snippet(self, fixture_name: str) -> str:
        _, payload, _ = run_linter(str(FIXTURES / "invalid" / fixture_name))
        l2 = [f for f in payload["files"][0]["findings"] if f["layer"] == "L2"]
        self.assertTrue(l2, "expected an L2 finding")
        snippet = l2[0]["snippet"]
        self.assertIsInstance(snippet, str)
        return snippet

    def test_unverified_control_snippet_is_a_full_screens_wrapper(self):
        snippet = self._l2_snippet("invented-control-type.pa.yaml")
        self.assertIn("Screens:", snippet)
        self.assertIn("SuperGrid@1.0.0", snippet)

    def test_snippet_parses_and_contains_exactly_one_control(self):
        import yaml  # local import keeps the rest of the suite dependency-free

        snippet = self._l2_snippet("invented-control-type.pa.yaml")
        doc = yaml.safe_load(snippet)
        screens = doc["Screens"]
        self.assertEqual(len(screens), 1)
        children = next(iter(screens.values()))["Children"]
        self.assertEqual(len(children), 1, "snippet must isolate a single control")

    def test_unverified_property_snippet_isolates_that_property(self):
        import yaml

        snippet = self._l2_snippet("invented-property.pa.yaml")
        doc = yaml.safe_load(snippet)
        children = next(iter(doc["Screens"].values()))["Children"]
        props = next(iter(children[0].values()))["Properties"]
        self.assertIn("BoxShadow", props)


class TestBundledExamples(unittest.TestCase):
    """Acceptance criterion: the three shipped examples must lint at exit 0."""

    def test_all_bundled_examples_exit_zero(self):
        examples = sorted(EXAMPLES.glob("*.yaml"))
        self.assertEqual(len(examples), 3, "expected three bundled examples")
        code, payload, stderr = run_linter(*[str(p) for p in examples])
        self.assertEqual(stderr.strip(), "")
        self.assertEqual(code, 0, "bundled examples must not produce blocking errors")
        for report in payload["files"]:
            with self.subTest(example=Path(report["path"]).name):
                blocking = [f for f in report["findings"] if f["severity"] == "error"]
                self.assertEqual(blocking, [], "no L0/L1 errors in a shipped example")


class TestDegradedWithoutJsonschema(unittest.TestCase):
    """Without jsonschema the L1 layer cannot run, so the linter must not claim the
    file is safe -- it has not checked the layer that catches PA1001."""

    def _run_without_jsonschema(self, fixture: Path, *extra: str):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as stub_dir:
            # A module that raises on import, simulating an environment where the
            # optional dependency is absent.
            Path(stub_dir, "jsonschema.py").write_text(
                'raise ImportError("simulated missing dependency")\n', encoding="utf-8"
            )
            env = dict(os.environ, PYTHONPATH=stub_dir)
            proc = subprocess.run(
                [sys.executable, str(LINTER), str(fixture), *extra],
                capture_output=True, text=True, encoding="utf-8",
                cwd=str(ROOT), env=env,
            )
        return proc

    def test_does_not_crash_without_jsonschema(self):
        proc = self._run_without_jsonschema(FIXTURES / "invalid" / "missing-equals.pa.yaml")
        self.assertNotIn("Traceback", proc.stderr)

    def test_says_the_schema_layer_was_skipped(self):
        proc = self._run_without_jsonschema(FIXTURES / "invalid" / "missing-equals.pa.yaml")
        self.assertIn("jsonschema", proc.stdout)

    def test_never_reports_safe_to_paste_when_the_schema_layer_was_skipped(self):
        proc = self._run_without_jsonschema(FIXTURES / "invalid" / "missing-equals.pa.yaml")
        self.assertNotIn("SAFE TO PASTE", proc.stdout)

    def test_a_clean_file_is_also_unproven_not_safe(self):
        proc = self._run_without_jsonschema(FIXTURES / "valid" / "clean-screen.pa.yaml")
        self.assertNotIn("SAFE TO PASTE", proc.stdout)

    def test_catalog_layers_still_run(self):
        proc = self._run_without_jsonschema(FIXTURES / "invalid" / "invented-control-type.pa.yaml")
        self.assertIn("L2.unverified-control-type", proc.stdout)

    def test_strict_refuses_to_pass_an_unproven_file(self):
        proc = self._run_without_jsonschema(
            FIXTURES / "valid" / "clean-screen.pa.yaml", "--strict"
        )
        self.assertEqual(proc.returncode, 2)


class TestExitCodes(unittest.TestCase):
    def test_strict_turns_warnings_into_exit_2(self):
        target = str(FIXTURES / "invalid" / "navigate-missing-screen.pa.yaml")
        proc = subprocess.run(
            [sys.executable, str(LINTER), target, "--strict"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
        )
        self.assertEqual(proc.returncode, 2)

    def test_strict_does_not_downgrade_a_real_error(self):
        target = str(FIXTURES / "invalid" / "missing-equals.pa.yaml")
        proc = subprocess.run(
            [sys.executable, str(LINTER), target, "--strict"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
        )
        self.assertEqual(proc.returncode, 1)

    def test_clean_file_is_exit_zero_even_with_strict(self):
        target = str(FIXTURES / "valid" / "clean-screen.pa.yaml")
        proc = subprocess.run(
            [sys.executable, str(LINTER), target, "--strict"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
        )
        self.assertEqual(proc.returncode, 0)


APP_FIXTURES = FIXTURES / "app"
REFERENCE_APP = ROOT / "tests" / "evals" / "multi-screen-mock" / "supersub"


def run_raw(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(LINTER), *args],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
    )


def by_name(payload: dict) -> dict:
    return {Path(r["path"]).name: r for r in payload["files"]}


class TestAppFixtures(unittest.TestCase):
    """Several files linted as one app: each <case>.app.expected.json names the
    arguments and the findings every file must produce."""

    def test_app_fixtures_produce_expected_findings(self):
        sidecars = sorted(APP_FIXTURES.glob("*.app.expected.json"))
        self.assertGreaterEqual(len(sidecars), 2, "expected at least two app fixtures")
        for sidecar in sidecars:
            expected = json.loads(sidecar.read_text(encoding="utf-8"))
            with self.subTest(fixture=sidecar.name):
                code, payload, stderr = run_linter(*expected["args"])
                self.assertEqual(stderr.strip(), "", "linter must not leak a traceback")
                self.assertEqual(code, expected["expected_exit_code"])
                self.assertTrue(payload["app_checked"])
                reports = by_name(payload)
                self.assertEqual(set(reports), set(expected["expected_files"]),
                                 "one report per file in the app directory")
                for name, want in expected["expected_files"].items():
                    report = reports[name]
                    self.assertEqual(finding_ids(report), expected_ids(want),
                                     f"\n{sidecar.name} / {name}: "
                                     f"{expected['description']}")
                    self.assertEqual(report["verdict_code"],
                                     want["expected_verdict_code"], name)

    def test_the_later_file_carries_one_finding_per_reused_name(self):
        _, payload, _ = run_linter("--app-dir", str(APP_FIXTURES / "collisions"))
        reused = [f for f in by_name(payload)["b-second.pa.yaml"]["findings"]
                  if f["check"] == "L3.duplicate-control-name-in-app"]
        self.assertEqual(sorted(f["path"].rsplit(".", 1)[-1] for f in reused),
                         ["btnBack", "lblTitle"])

    def test_one_app_on_files_matches_app_dir(self):
        files = sorted(str(p) for p in (APP_FIXTURES / "collisions").glob("*.pa.yaml"))
        _, from_files, _ = run_linter(*files, "--one-app")
        _, from_dir, _ = run_linter("--app-dir", str(APP_FIXTURES / "collisions"))
        self.assertEqual(
            {n: finding_ids(r) for n, r in by_name(from_files).items()},
            {n: finding_ids(r) for n, r in by_name(from_dir).items()})

    def test_files_passed_together_are_not_compared_without_one_app(self):
        """Unrelated files (the bundled patterns all use one placeholder screen name)
        must not be compared just because they were linted in one call."""
        files = sorted(str(p) for p in (APP_FIXTURES / "collisions").glob("*.pa.yaml"))
        _, payload, _ = run_linter(*files)
        self.assertFalse(payload["app_checked"])
        for report in payload["files"]:
            checks = {f["check"] for f in report["findings"]}
            self.assertFalse(checks & {"L3.duplicate-control-name-in-app",
                                       "L3.duplicate-screen-in-app"},
                             Path(report["path"]).name)

    def test_the_bundled_patterns_stay_safe_together(self):
        patterns = sorted(str(p) for p in
                          (ROOT / "skills" / "create-app" / "assets" / "patterns")
                          .glob("*.pa.yaml"))
        _, payload, _ = run_linter(*patterns)
        self.assertEqual({r["verdict_code"] for r in payload["files"]}, {"safe"})

    def test_without_the_sitemap_a_screen_only_listed_there_is_missing(self):
        _, payload, _ = run_linter("--app-dir", str(APP_FIXTURES / "clean"))
        self.assertEqual(finding_ids(by_name(payload)["scrDetail.pa.yaml"]),
                         {("L3", "L3.navigate-target-missing")})
        self.assertEqual(finding_ids(by_name(payload)["scrHome.pa.yaml"]), set(),
                         "a screen in another file of the app resolves")


class TestKnownScreens(unittest.TestCase):
    def test_known_screens_resolve_a_navigate_target(self):
        target = str(APP_FIXTURES / "collisions" / "a-first.pa.yaml")
        _, alone, _ = run_linter(target)
        self.assertIn(("L3", "L3.navigate-target-missing"),
                      finding_ids(alone["files"][0]))
        code, known, _ = run_linter(target, "--known-screens", "scrB, scrOther")
        self.assertEqual(finding_ids(known["files"][0]), set())
        self.assertEqual(known["files"][0]["verdict_code"], "safe")
        self.assertEqual(known["known_screens"], ["scrB", "scrOther"])
        self.assertEqual(code, 0)

    def test_sitemap_resolves_a_single_file(self):
        target = str(APP_FIXTURES / "clean" / "scrDetail.pa.yaml")
        _, payload, _ = run_linter(
            target, "--sitemap", str(APP_FIXTURES / "clean" / "sitemap.json"))
        self.assertEqual(finding_ids(payload["files"][0]), set())
        self.assertFalse(payload["app_checked"], "a sitemap alone is not app mode")

    def test_a_target_in_neither_file_nor_sitemap_is_still_missing(self):
        target = str(FIXTURES / "invalid" / "navigate-missing-screen.pa.yaml")
        _, payload, _ = run_linter(
            target, "--sitemap", str(APP_FIXTURES / "clean" / "sitemap.json"))
        self.assertEqual(finding_ids(payload["files"][0]),
                         {("L3", "L3.navigate-target-missing")})

    def test_a_commented_placeholder_still_passes(self):
        target = str(FIXTURES / "valid" / "navigate-placeholder-commented.pa.yaml")
        _, payload, _ = run_linter(target, "--known-screens", "scrUnrelated")
        self.assertEqual(payload["files"][0]["verdict_code"], "safe")


class TestAppUsageErrors(unittest.TestCase):
    """Bad arguments exit 2 with one sentence on stderr, never a traceback."""

    def test_unreadable_sitemap(self):
        for bad in ("tests/fixtures/app/no-such-sitemap.json",
                    "tests/fixtures/app/clean/scrHome.pa.yaml"):
            with self.subTest(sitemap=bad):
                proc = run_raw(str(FIXTURES / "valid" / "clean-screen.pa.yaml"),
                               "--sitemap", bad)
                self.assertEqual(proc.returncode, 2)
                self.assertIn("sitemap", proc.stderr)
                self.assertNotIn("Traceback", proc.stderr)

    def test_missing_or_empty_app_dir(self):
        for bad in ("tests/fixtures/app/no-such-dir", "tests/fixtures/app"):
            with self.subTest(app_dir=bad):
                proc = run_raw("--app-dir", bad)
                self.assertEqual(proc.returncode, 2)
                self.assertNotIn("Traceback", proc.stderr)

    def test_no_file_and_no_app_dir_is_a_usage_error(self):
        proc = run_raw()
        self.assertEqual(proc.returncode, 2)
        self.assertNotIn("Traceback", proc.stderr)


class TestReferenceApp(unittest.TestCase):
    """Acceptance for the mock-ui branch: the phase 03 example, converted one file
    per screen, lints with no error, no unresolved target and no collision."""

    def test_reference_app_is_safe_as_one_app_with_its_sitemap(self):
        code, payload, stderr = run_linter(
            "--app-dir", str(REFERENCE_APP / "app"),
            "--sitemap", str(REFERENCE_APP / "mockup" / "sitemap.json"))
        self.assertEqual(stderr.strip(), "")
        self.assertEqual(code, 0)
        reports = by_name(payload)
        self.assertEqual(set(reports), {"scrLoanList.pa.yaml", "scrNewLoan.pa.yaml",
                                        "scrLoanDetail.pa.yaml"})
        for name, report in reports.items():
            with self.subTest(file=name):
                self.assertEqual(report["findings"], [])
                self.assertEqual(report["verdict_code"], "safe")

    def test_one_screen_per_file_named_after_its_screen(self):
        import yaml
        for path in sorted((REFERENCE_APP / "app").glob("*.pa.yaml")):
            with self.subTest(file=path.name):
                screens = list(yaml.safe_load(path.read_text(encoding="utf-8"))["Screens"])
                self.assertEqual(screens, [path.name.replace(".pa.yaml", "")])

    def test_every_sitemap_screen_has_a_file(self):
        sitemap = json.loads((REFERENCE_APP / "mockup" / "sitemap.json")
                             .read_text(encoding="utf-8"))
        ids = {s["id"] for s in sitemap["screens"]}
        files = {p.name.replace(".pa.yaml", "")
                 for p in (REFERENCE_APP / "app").glob("*.pa.yaml")}
        self.assertEqual(ids, files)
        self.assertTrue((REFERENCE_APP / "app" / "PASTE-ORDER.md").is_file())


class TestHumanOutput(unittest.TestCase):
    def _run_text(self, *args: str) -> tuple[int, str]:
        proc = subprocess.run(
            [sys.executable, str(LINTER), *args],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
        )
        return proc.returncode, proc.stdout

    def test_verdict_line_is_present_for_each_outcome(self):
        for fixture, fragment in [
            (FIXTURES / "valid" / "clean-screen.pa.yaml", "VERDICT: SAFE TO PASTE"),
            (FIXTURES / "invalid" / "missing-equals.pa.yaml", "VERDICT: WILL FAIL"),
            (FIXTURES / "invalid" / "navigate-missing-screen.pa.yaml", "VERDICT: PASTES, BUT"),
        ]:
            with self.subTest(fixture=fixture.name):
                _, out = self._run_text(str(fixture))
                self.assertIn(fragment, out)

    def test_quiet_prints_only_the_verdict(self):
        _, out = self._run_text(str(FIXTURES / "invalid" / "navigate-missing-screen.pa.yaml"), "--quiet")
        lines = [ln for ln in out.splitlines() if ln.strip()]
        self.assertTrue(all(ln.startswith("VERDICT:") for ln in lines), out)

    def test_no_raw_jsonschema_traceback_leaks(self):
        _, out = self._run_text(str(FIXTURES / "invalid" / "missing-equals.pa.yaml"))
        self.assertNotIn("Traceback", out)
        self.assertNotIn("is not valid under any of the given schemas", out)


if __name__ == "__main__":
    unittest.main()
