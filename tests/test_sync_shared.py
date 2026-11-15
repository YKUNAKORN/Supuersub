#!/usr/bin/env python3
"""Tests for scripts/sync_shared.py and for the derived Power Apps profile.

The profile (shared/powerapps-profile.md) is derived from the create-app catalog,
skills/create-app/references/controls.yaml. These tests fail when the catalog gains an
entry the profile does not cover, so the two cannot drift apart silently.

Run:  python -m unittest discover tests
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SYNC = ROOT / "scripts" / "sync_shared.py"
PROFILE = ROOT / "shared" / "powerapps-profile.md"
CATALOG = ROOT / "skills" / "create-app" / "references" / "controls.yaml"


def load_sync():
    spec = importlib.util.spec_from_file_location("sync_shared", SYNC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestSync(unittest.TestCase):
    def test_repository_copies_are_in_sync(self):
        proc = subprocess.run([sys.executable, str(SYNC), "--check"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_plan_reports_each_state(self):
        mod = load_sync()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "shared").mkdir()
            (root / "shared" / "a.md").write_text("A\n")
            (root / "shared" / "b.md").write_text("B\n")
            dest = root / "skills" / "one" / "references" / "shared"
            dest.mkdir(parents=True)
            (dest / "a.md").write_text("A\n")
            (dest / "b.md").write_text("edited by hand\n")
            (dest / "old.md").write_text("stale\n")
            other = root / "skills" / "two" / "references" / "shared"
            other.mkdir(parents=True)
            (other / "x.md").write_text("x\n")
            manifest = {"one": ["a.md", "b.md", "c.md"]}
            states = {(s, p.name) for s, p, _ in mod.plan(root, manifest)}
        self.assertEqual(states, {("ok", "a.md"), ("differs", "b.md"),
                                  ("no-source", "c.md"), ("stray", "old.md"),
                                  ("stray", "x.md")})

    def test_every_manifest_source_exists(self):
        mod = load_sync()
        for skill, files in mod.MANIFEST.items():
            self.assertTrue((ROOT / "skills" / skill).is_dir(), skill)
            for name in files:
                self.assertTrue((ROOT / "shared" / name).is_file(), name)


class TestPowerAppsProfile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
        cls.profile = PROFILE.read_text(encoding="utf-8")

    def test_every_impossible_css_id_is_in_the_profile(self):
        ids = [e["id"] for e in self.catalog["impossible_css"]]
        self.assertTrue(ids)
        missing = [i for i in ids if f"impossible_css[id={i}]" not in self.profile]
        self.assertEqual(missing, [], "catalog impossible_css ids the profile does not cover")

    def test_catalog_substitutes_are_quoted(self):
        for entry in self.catalog["impossible_css"]:
            if entry.get("substitute"):
                self.assertIn(entry["substitute"], self.profile, entry["id"])

    def test_every_confirmed_control_and_property_is_listed(self):
        for control in self.catalog["controls"]:
            name = control["name"]
            key = f"controls[{name}].properties_confirmed"
            self.assertIn(key, self.profile, name)
            row = next((l for l in self.profile.splitlines()
                        if l.startswith(f"| {name} |")), "")
            self.assertIn(control["type"], row, name)
            for prop in control.get("properties_confirmed") or []:
                self.assertIn(prop, row, f"{name}.{prop}")

    def test_unattempted_controls_are_listed(self):
        self.assertIn("unattempted_controls", self.profile)
        for name in self.catalog["unattempted_controls"]:
            self.assertIn(name, self.profile)

    def test_linter_detectors_cover_the_prose_effects(self):
        spec = importlib.util.spec_from_file_location(
            "design_lint", ROOT / "skills" / "design-md" / "scripts" / "design_lint.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ids = {e["id"] for e in self.catalog["impossible_css"]}
        handled = set(mod.PA_DETECTORS) | {"non-segoe-font"}
        self.assertEqual(ids - handled, set(),
                         "impossible_css ids design_lint.py has no detector for")


if __name__ == "__main__":
    unittest.main()
