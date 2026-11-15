#!/usr/bin/env python3
"""The end-to-end scenario in tests/e2e/leave-request/, checked again on every run.

docs/e2e-walkthrough.md records the verdict of each step. This test re-runs every
linter on the saved artifacts and fails if a verdict changes, rebuilds the import files
and the flow package from their specs and compares the bytes, and checks that the names
handed from one skill to the next agree (shared/handoff.md, "Names every skill uses").

Run:  python -m unittest tests.test_e2e_leave_request
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

import yaml

ROOT = Path(__file__).resolve().parent.parent
E2E = ROOT / "tests" / "e2e" / "leave-request"
SKILLS = ROOT / "skills"
HAS_OPENPYXL = importlib.util.find_spec("openpyxl") is not None
HAS_JSONSCHEMA = importlib.util.find_spec("jsonschema") is not None

# The verdict of each step, as docs/e2e-walkthrough.md records it.
EXPECTED = {
    "design-md": "safe",
    "mock-ui": "safe",
    "create-app": "safe",
    "create-list": "unverified",
    "create-flow": "unverified",
}


def lint(script: Path, *args: str) -> dict:
    proc = subprocess.run([sys.executable, str(script), *args, "--json"], cwd=str(E2E),
                          capture_output=True, text=True, timeout=120)
    return json.loads(proc.stdout)


def codes(report: dict) -> list[str]:
    if "report" in report:
        return [report["report"]["verdict_code"]]
    return [f["verdict_code"] for f in report["files"]]


def checks(report: dict) -> set[str]:
    found = report["report"]["findings"] if "report" in report else [
        f for file in report["files"] for f in file["findings"]]
    return {f["check"] for f in found}


class TestVerdicts(unittest.TestCase):
    def test_design_md(self):
        r = lint(SKILLS / "design-md" / "scripts" / "design_lint.py", "DESIGN.md",
                 "--target", "power-apps")
        self.assertEqual(codes(r), [EXPECTED["design-md"]])

    def test_mock_ui(self):
        r = lint(SKILLS / "mock-ui" / "scripts" / "mock_lint.py", "supersub/mockup",
                 "--design", "DESIGN.md", "--strict")
        self.assertEqual(codes(r), [EXPECTED["mock-ui"]])

    @unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema missing: the verdict would be UNPROVEN")
    def test_create_app(self):
        r = lint(SKILLS / "create-app" / "scripts" / "pa_lint.py", "--app-dir",
                 "supersub/app", "--sitemap", "supersub/mockup/sitemap.json")
        self.assertEqual(codes(r), [EXPECTED["create-app"]] * 2)

    @unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema missing: the verdict would be UNPROVEN")
    def test_create_list(self):
        r = lint(SKILLS / "create-list" / "scripts" / "list_lint.py", "supersub/lists")
        self.assertEqual(codes(r), [EXPECTED["create-list"]])
        self.assertEqual(checks(r), {"unverified-behavior"})

    @unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema missing: the verdict would be UNPROVEN")
    def test_create_flow(self):
        r = lint(SKILLS / "create-flow" / "scripts" / "flow_lint.py", "supersub/flows")
        self.assertEqual(codes(r), [EXPECTED["create-flow"]])
        self.assertEqual(checks(r), {"unverified-step"})

    def test_mockup_root_block_is_the_generated_one(self):
        proc = subprocess.run([sys.executable, str(SKILLS / "mock-ui" / "scripts" /
                                                    "tokens_to_css.py"), "DESIGN.md",
                               "--target", "power-apps"], cwd=str(E2E),
                              capture_output=True, text=True)
        block = proc.stdout.strip()
        for page in ("leave-list.html", "new-leave.html", "index.html"):
            html = (E2E / "supersub" / "mockup" / page).read_text(encoding="utf-8")
            flat = "\n".join(l.strip() for l in html.splitlines())
            self.assertIn("\n".join(l.strip() for l in block.splitlines()), flat, page)


class TestRebuild(unittest.TestCase):
    """The binary artifacts are what their specs build today, byte for byte."""

    def build_list(self, fmt: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run([sys.executable, str(SKILLS / "create-list" / "scripts" /
                                                        "build_list.py"),
                                   "supersub/lists/LeaveRequests.list.json", "--format", fmt,
                                   "--out", tmp], cwd=str(E2E), capture_output=True,
                                  text=True)
            self.assertIn("VERIFIED", proc.stdout, proc.stderr)
            for name in ([f"LeaveRequests.{fmt}"]
                         + (["LeaveRequests.Setup.md"] if fmt == "csv" else [])):
                self.assertEqual((Path(tmp) / name).read_bytes(),
                                 (E2E / "supersub" / "lists" / name).read_bytes(), name)

    @unittest.skipUnless(HAS_OPENPYXL, "openpyxl missing")
    def test_xlsx(self):
        self.build_list("xlsx")

    def test_csv(self):
        self.build_list("csv")

    def test_flow_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run([sys.executable, str(SKILLS / "create-flow" / "scripts" /
                                                        "build_flow_package.py"),
                                   "supersub/flows/NotifyApprover.flow.json", "--out", tmp,
                                   "--seed", "e2e-leave-request", "--created-time",
                                   "2026-11-15T00:00:00Z"], cwd=str(E2E),
                                  capture_output=True, text=True)
            self.assertIn("VERIFIED", proc.stdout, proc.stderr)
            name = "NotifyApprover_LegacyPackage.zip"
            self.assertEqual((Path(tmp) / name).read_bytes(),
                             (E2E / "supersub" / "flows" / name).read_bytes())


class TestHandoffNames(unittest.TestCase):
    """What one skill writes, the next one reads under exactly the same name."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.sitemap = json.loads((E2E / "supersub" / "mockup" / "sitemap.json")
                                 .read_text(encoding="utf-8"))
        cls.lists = {s["name"]: s for s in (
            json.loads(p.read_text(encoding="utf-8"))
            for p in (E2E / "supersub" / "lists").glob("*.list.json"))}
        cls.flows = {s["name"]: s for s in (
            json.loads(p.read_text(encoding="utf-8"))
            for p in (E2E / "supersub" / "flows").glob("*.flow.json"))}

    def test_layout(self):
        for rel in ("DESIGN.md", "supersub/mockup/index.html", "supersub/mockup/sitemap.json",
                    "supersub/app/PASTE-ORDER.md", "supersub/lists/lists.md",
                    "supersub/flows/flow.md"):
            self.assertTrue((E2E / rel).is_file(), rel)

    def test_sitemap_design_path_resolves(self):
        design = E2E / "supersub" / "mockup" / self.sitemap["design"]
        self.assertEqual(design.resolve(), (E2E / "DESIGN.md").resolve())

    def test_every_data_source_is_a_list_and_every_field_a_column(self):
        for screen in self.sitemap["screens"]:
            for data in screen["data"]:
                with self.subTest(screen=screen["id"], source=data["source"]):
                    self.assertIn(data["source"], self.lists)
                    columns = {c["name"] for c in self.lists[data["source"]]["columns"]}
                    self.assertLessEqual(set(data["fields"]), columns)

    def test_every_run_flow_action_is_a_flow(self):
        named = {a["id"].split(":", 1)[1] for s in self.sitemap["screens"]
                 for a in s["actions"] if a["id"].startswith("run-flow:")}
        self.assertEqual(named, set(self.flows))

    def test_every_html_data_field_is_a_column(self):
        columns = {c["name"] for spec in self.lists.values() for c in spec["columns"]}
        for page in (E2E / "supersub" / "mockup").glob("*.html"):
            fields = set(re.findall(r'data-field="([^"]+)"', page.read_text(encoding="utf-8")))
            self.assertLessEqual(fields, columns, page.name)

    def test_screen_files_carry_the_sitemap_ids(self):
        ids = {s["id"] for s in self.sitemap["screens"]}
        on_disk = set()
        for p in (E2E / "supersub" / "app").glob("*.pa.yaml"):
            doc = yaml.safe_load(p.read_text(encoding="utf-8"))
            names = list(doc["Screens"])
            self.assertEqual([p.name], [f"{names[0]}.pa.yaml"])
            on_disk.update(names)
        self.assertEqual(on_disk, ids)

    def test_screen_comments_name_real_columns(self):
        columns = {f"{n}.{c['name']}" for n, s in self.lists.items() for c in s["columns"]}
        for p in (E2E / "supersub" / "app").glob("*.pa.yaml"):
            used = set(re.findall(r"#\s*(LeaveRequests\.[A-Za-z]+)", p.read_text(encoding="utf-8")))
            self.assertLessEqual(used, columns, p.name)


if __name__ == "__main__":
    unittest.main()
