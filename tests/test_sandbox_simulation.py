#!/usr/bin/env python3
"""Sandbox simulation: each skill runs from a copy of its own folder and nothing else.

In Claude chat, a skill's folder is what reaches the code-execution sandbox. Nothing
documents that the rest of the plugin comes with it. This is the closest a machine gets
to that: copy only skills/<name>/ into an empty temporary directory, change into it, and
run every script the skill's SKILL.md mentions with the relative `scripts/<file>.py`
path, against the skill's own bundled example. No repository file is reachable: the
working directory is the copy, and PYTHONPATH is cleared.

A script SKILL.md names but this file has no command for fails the test, so a new
script cannot skip the simulation.

Run:  python -m unittest tests.test_sandbox_simulation
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
HAS_OPENPYXL = importlib.util.find_spec("openpyxl") is not None

# (command after `python3`, what stdout must contain). Paths are relative to the skill
# folder, exactly as SKILL.md writes them. `out/` is created inside the copy.
COMMANDS: dict[str, list[tuple[list[str], str]]] = {
    "design-md": [
        (["scripts/design_lint.py", "assets/example/DESIGN.md"], "VERDICT: CLEAN"),
        (["scripts/design_lint.py", "assets/DESIGN.template.md"], "VERDICT:"),
    ],
    "mock-ui": [
        (["scripts/tokens_to_css.py", "assets/example/DESIGN.md", "--target", "power-apps"],
         ":root {"),
        (["scripts/mock_lint.py", "assets/example", "--design", "assets/example/DESIGN.md"],
         "VERDICT: CLEAN"),
    ],
    "create-app": [
        (["scripts/pa_lint.py", "assets/examples/example-form.yaml"], "VERDICT: SAFE TO PASTE"),
        (["scripts/pa_lint.py", "assets/patterns/screen-shell.pa.yaml"], "VERDICT: SAFE TO PASTE"),
        (["scripts/app_inventory.py", "assets/examples"], "Screens"),
        # Named in references/harvesting.md rather than SKILL.md; run it anyway.
        (["scripts/harvest_controls.py", "assets/examples", "--report"], ""),
    ],
    "create-list": [
        (["scripts/list_lint.py", "assets/example"], "VERDICT: USABLE"),
        (["scripts/build_list.py", "assets/example/Holidays.list.json", "--format", "csv",
          "--out", "out"], "VERIFIED"),
    ] + ([
        (["scripts/build_list.py", "assets/example/Holidays.list.json", "--format", "xlsx",
          "--out", "out"], "VERIFIED"),
    ] if HAS_OPENPYXL else []),
    "create-flow": [
        (["scripts/flow_lint.py", "assets/example"], "VERDICT: SHOULD IMPORT"),
        (["scripts/build_flow_package.py", "assets/example/SendTestEmail.flow.json",
          "--out", "out", "--seed", "sandbox", "--created-time", "2026-11-15T00:00:00Z"],
         "VERIFIED"),
        (["scripts/build_flow_package.py", "--verify",
          "out/SendTestEmail_LegacyPackage.zip"], "VERIFIED"),
        (["scripts/harvest_flow.py", "assets/reference-package", "--report"], ""),
    ],
}

_SCRIPT_RE = re.compile(r"scripts/([A-Za-z0-9_.-]+\.py)")


def mentioned_scripts(skill: str) -> set[str]:
    return set(_SCRIPT_RE.findall((SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")))


def run_in_sandbox(skill: str) -> list[tuple[list[str], int, str, str]]:
    """Copy skills/<skill>/ alone into a temp dir and run its commands there."""
    results = []
    with tempfile.TemporaryDirectory(prefix=f"sandbox-{skill}-") as tmp:
        box = Path(tmp) / skill
        shutil.copytree(SKILLS / skill, box,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        for args, _ in COMMANDS[skill]:
            proc = subprocess.run([sys.executable, *args], cwd=str(box), env=env,
                                  capture_output=True, text=True, timeout=120)
            results.append((args, proc.returncode, proc.stdout, proc.stderr))
    return results


def run_from_project_dir(skill: str) -> list[tuple[list[str], int, str, str]]:
    """Claude Code's case: the working directory is the user's project, not the skill.

    Paths that SKILL.md writes as `${CLAUDE_SKILL_DIR}/scripts/...` become absolute
    paths into the repository's skill folder; outputs go to the empty project dir.
    """
    results = []
    base = SKILLS / skill
    with tempfile.TemporaryDirectory(prefix=f"project-{skill}-") as tmp:
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        for args, _ in COMMANDS[skill]:
            mapped = [str(base / a) if a.startswith(("scripts/", "assets/")) else a
                      for a in args]
            proc = subprocess.run([sys.executable, *mapped], cwd=tmp, env=env,
                                  capture_output=True, text=True, timeout=120)
            results.append((args, proc.returncode, proc.stdout, proc.stderr))
    return results


class TestSandboxSimulation(unittest.TestCase):
    def test_every_skill_has_commands(self):
        skills = sorted(d.name for d in SKILLS.iterdir() if d.is_dir())
        self.assertEqual(sorted(COMMANDS), skills)

    def test_every_mentioned_script_is_simulated(self):
        for skill in COMMANDS:
            covered = {Path(args[0]).name for args, _ in COMMANDS[skill]
                       if args[0].startswith("scripts/")}
            with self.subTest(skill=skill):
                self.assertLessEqual(mentioned_scripts(skill), covered,
                                     "add a command for every script SKILL.md names")

    def test_from_a_project_directory(self):
        for skill in COMMANDS:
            self._check(skill, run_from_project_dir)

    def _check(self, skill: str, runner=run_in_sandbox) -> None:
        expected = {tuple(a): want for a, want in COMMANDS[skill]}
        for args, code, out, err in runner(skill):
            with self.subTest(skill=skill, command=" ".join(args)):
                self.assertEqual(code, 0, f"exit {code}\nstdout:\n{out[-1500:]}\n"
                                          f"stderr:\n{err[-1500:]}")
                self.assertIn(expected[tuple(args)], out)
                self.assertNotIn("Traceback", err)

    def test_design_md(self):
        self._check("design-md")

    def test_mock_ui(self):
        self._check("mock-ui")

    def test_create_app(self):
        self._check("create-app")

    def test_create_list(self):
        self._check("create-list")

    def test_create_flow(self):
        self._check("create-flow")


if __name__ == "__main__":
    unittest.main()
