#!/usr/bin/env python3
"""Tests for skills/mock-ui/scripts/tokens_to_css.py.

The variable names it prints are a contract with mock_lint.py and with the create-app
conversion, so these tests pin the names and the power-apps unit conversion, and check
that the bundled example's pages still carry exactly the block the script prints.

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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "mock-ui"
SCRIPT = SKILL / "scripts" / "tokens_to_css.py"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "mock-ui" / "tokens" / "DESIGN.md"
EXAMPLE = SKILL / "assets" / "example"


def load_module():
    spec = importlib.util.spec_from_file_location("tokens_to_css", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True,
                          text=True, encoding="utf-8", cwd=str(cwd))


class TestNames(unittest.TestCase):
    """The name scheme in references/html-contract.md section 3."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()
        fm = cls.mod.front_matter(FIXTURE.read_text(encoding="utf-8"))
        cls.web = cls.mod.as_map(fm, "web")
        cls.pa = cls.mod.as_map(fm, "power-apps")

    def test_colors(self):
        self.assertEqual(self.web["--color-primary"], "#1f4fd1")
        self.assertEqual(self.web["--color-surface"], "rgb(245, 246, 248)")

    def test_typography(self):
        for suffix in ("family", "size", "weight", "line-height", "letter-spacing"):
            self.assertIn(f"--font-display-{suffix}", self.web)
        self.assertEqual(self.web["--font-display-family"],
                         '"Fraunces Variable", Georgia, serif')

    def test_rounded_and_spacing(self):
        self.assertEqual(self.web["--radius-md"], "0.375rem")
        self.assertEqual(self.web["--space-md"], "16px")

    def test_component_references_become_var(self):
        self.assertEqual(self.web["--button-primary-bg"], "var(--color-primary)")
        self.assertEqual(self.web["--button-primary-text"], "var(--color-on-primary)")
        self.assertEqual(self.web["--button-primary-radius"], "var(--radius-md)")
        self.assertEqual(self.web["--card-padding"], "var(--space-md)")
        self.assertEqual(self.web["--card-bg"], "#ffffff")

    def test_typography_reference_is_a_comment_not_a_property(self):
        self.assertFalse(any(k.startswith("--button-primary-typography") for k in self.web))
        css = run(str(FIXTURE)).stdout
        self.assertIn("/* button-primary typography: --font-body-md-* */", css)

    def test_canvas_only_under_power_apps(self):
        self.assertNotIn("--canvas-width", self.web)
        self.assertEqual(self.pa["--canvas-width"], "1366px")
        self.assertEqual(self.pa["--canvas-height"], "768px")


class TestPowerAppsUnits(unittest.TestCase):
    """Under power-apps every length is px, so geometry is arithmetic."""

    @classmethod
    def setUpClass(cls):
        mod = load_module()
        cls.pa = mod.as_map(mod.front_matter(FIXTURE.read_text(encoding="utf-8")),
                            "power-apps")

    def test_rem_becomes_px(self):
        self.assertEqual(self.pa["--font-display-size"], "32px")
        self.assertEqual(self.pa["--radius-md"], "6px")
        self.assertEqual(self.pa["--space-sm"], "8px")
        self.assertEqual(self.pa["--button-primary-padding"], "8px 20px")

    def test_unitless_line_height_becomes_px(self):
        self.assertEqual(self.pa["--font-display-line-height"], "40px")   # 32 x 1.25

    def test_em_letter_spacing_is_relative_to_its_font_size(self):
        self.assertEqual(self.pa["--font-display-letter-spacing"], "-0.64px")  # 32 x -0.02

    def test_px_values_unchanged(self):
        self.assertEqual(self.pa["--font-body-md-line-height"], "20px")
        self.assertEqual(self.pa["--radius-full"], "9999px")

    def test_no_relative_unit_left(self):
        for name, value in self.pa.items():
            self.assertNotRegex(value, r"\d(?:rem|em)\b", name)

    def test_canvas_option(self):
        out = json.loads(run(str(FIXTURE), "--target", "power-apps", "--canvas", "1280x800",
                             "--json").stdout)
        self.assertEqual((out["--canvas-width"], out["--canvas-height"]), ("1280px", "800px"))


class TestCli(unittest.TestCase):

    def test_prints_one_root_block(self):
        proc = run(str(FIXTURE))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(proc.stdout.startswith(":root {"))
        self.assertEqual(proc.stdout.count("{"), 1, "exactly one block, no nested rules")
        self.assertTrue(proc.stdout.rstrip().endswith("}"))

    def test_out_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "root.css"
            proc = run(str(FIXTURE), "--out", str(out))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("--color-primary: #1f4fd1;", out.read_text(encoding="utf-8"))

    def test_no_front_matter_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "DESIGN.md"
            bad.write_text("# Just prose\n", encoding="utf-8")
            self.assertEqual(run(str(bad)).returncode, 1)

    def test_missing_file_exits_2(self):
        self.assertEqual(run("no-such-DESIGN.md").returncode, 2)

    def test_runs_from_outside_the_repo_by_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = run(str(FIXTURE), "--target", "power-apps", cwd=Path(tmp))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("--canvas-width: 1366px;", proc.stdout)


class TestExampleUsesTheGeneratedBlock(unittest.TestCase):
    """Every example screen starts its <style> with the block the script prints."""

    def test_example_root_blocks_match(self):
        sitemap = json.loads((EXAMPLE / "sitemap.json").read_text(encoding="utf-8"))
        block = run(str(EXAMPLE / sitemap["design"]), "--target", sitemap["target"]).stdout
        expected = [ln.strip() for ln in block.splitlines()]
        for screen in sitemap["screens"]:
            html = (EXAMPLE / screen["file"]).read_text(encoding="utf-8")
            m = re.search(r"<style>\s*(:root \{.*?\n\s*\})", html, re.S)
            self.assertIsNotNone(m, f"{screen['file']} does not open its <style> with :root")
            got = [ln.strip() for ln in m.group(1).splitlines()]
            self.assertEqual(got, expected, f"{screen['file']}: regenerate its :root block")


if __name__ == "__main__":
    unittest.main()
