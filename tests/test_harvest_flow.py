#!/usr/bin/env python3
"""Tests for skills/create-flow/scripts/harvest_flow.py.

Harvesting the owner's reference package must yield exactly the seeded catalog
(references/connectors.yaml), evidence and sources aside. A synthetic export full of
tenant values must come out with none of them left.

Run:  python -m unittest discover tests
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "create-flow"
HARVESTER = SKILL / "scripts" / "harvest_flow.py"
CATALOG = SKILL / "references" / "connectors.yaml"
REFERENCE = ROOT / "tests" / "fixtures" / "flows" / "reference-package.zip"
UNPACKED = SKILL / "assets" / "reference-package"

TENANT = ["contoso.sharepoint.com", "somchai.j@contoso.co.th",
          "3f2504e0-4f89-41d3-9a0c-0305e82c3301", "shared-sharepointonl-9b1c2d3e",
          "Somchai Jaidee", "Leave Requests HR"]


def load():
    spec = importlib.util.spec_from_file_location("harvest_flow", HARVESTER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(*args: str, cwd: Path = ROOT):
    return subprocess.run([sys.executable, str(HARVESTER), *args], capture_output=True,
                          text=True, encoding="utf-8", cwd=str(cwd))


def tenant_package(path: Path) -> None:
    """The reference package plus a SharePoint step and a connection full of tenant data."""
    with zipfile.ZipFile(REFERENCE) as zf:
        files = {i.filename: json.loads(zf.read(i)) for i in zf.infolist()}
    root = files["manifest.json"]
    root["resources"]["aaaaaaaa-0000-4000-8000-000000000001"] = {
        "id": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
        "name": "shared_sharepointonline", "type": "Microsoft.PowerApps/apis",
        "details": {"displayName": "SharePoint",
                    "iconUri": "https://connectoricons-prod.azureedge.net/sharepoint/icon.png"}}
    root["resources"]["aaaaaaaa-0000-4000-8000-000000000002"] = {
        "type": "Microsoft.PowerApps/apis/connections",
        "details": {"displayName": "somchai.j@contoso.co.th"},
        "dependsOn": ["aaaaaaaa-0000-4000-8000-000000000001"]}
    def_name = next(n for n in files if n.endswith("definition.json"))
    props = files[def_name]["properties"]
    props["connectionReferences"]["shared_sharepointonline"] = {
        "connectionName": "shared-sharepointonl-9b1c2d3e-0000-4000-8000-000000000003"}
    props["definition"]["actions"]["Create_item_for_Somchai_Jaidee"] = {
        "runAfter": {}, "type": "OpenApiConnection",
        "inputs": {
            "host": {"apiId": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
                     "connectionName": "shared_sharepointonline", "operationId": "PostItem"},
            "parameters": {
                "dataset": "https://contoso.sharepoint.com/sites/HR",
                "table": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
                "item/Title": "Leave Requests HR",
                "item/Requester": "somchai.j@contoso.co.th",
                "item/Count": 3,
                "item/Link": "@concat('https://contoso.sharepoint.com/sites/HR/', "
                             "'somchai.j@contoso.co.th')"}}}
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, obj in files.items():
            zf.writestr(name, json.dumps(obj, indent=2))


class TestReference(unittest.TestCase):
    def test_reference_yields_the_seeded_catalog(self):
        mod = load()
        catalog = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
        h = mod.harvest([REFERENCE])
        self.assertEqual(h.packages, 1)
        self.assertEqual(mod.shape(mod.to_catalog(h, "export", "x")), mod.shape(catalog))

    def test_unpacked_folder_equals_zip(self):
        mod = load()
        a = mod.to_catalog(mod.harvest([REFERENCE]), "export", "x")
        b = mod.to_catalog(mod.harvest([UNPACKED]), "export", "x")
        self.assertEqual(a, b)

    def test_cli_fragment_parses_and_has_no_guid(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = run(str(REFERENCE), "--date", "2026-11-15", cwd=Path(tmp))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        frag = yaml.safe_load(proc.stdout)
        self.assertEqual(frag["connectors"]["shared_office365"]["evidence"], "export")
        mod = load()
        for needle in ("00000000-0000-4000-8000-000000000001", "33168822", "207d9c43",
                       "955ed331", "Get_Bangkok_time", "Your own email address"):
            self.assertNotIn(needle, proc.stdout)
        self.assertEqual(mod.guard(proc.stdout), [])

    def test_report(self):
        proc = run(str(REFERENCE), "--report")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("absence is not evidence", proc.stdout)
        self.assertIn("connector shared_office365  (import-tested)", proc.stdout)


class TestTenantValues(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.zip = Path(cls.tmp.name) / "export.zip"
        tenant_package(cls.zip)
        cls.proc = run(str(cls.zip), "--date", "2026-11-15")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_harvests(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)
        frag = yaml.safe_load(self.proc.stdout)
        op = frag["connectors"]["shared_sharepointonline"]["operations"]["PostItem"]
        self.assertEqual(sorted(op["parameters"]), ["dataset", "item/Count", "item/Link",
                                                    "item/Requester", "item/Title", "table"])
        self.assertEqual(op["example"]["dataset"], "{{Dataset}}")
        self.assertEqual(op["example"]["table"], "{{Table}}")
        self.assertIn("{{SiteAddress}}", op["example"]["item/Link"])
        self.assertIn("{{EmailAddress}}", op["example"]["item/Link"])
        self.assertEqual(frag["connectors"]["shared_sharepointonline"]
                         ["connection_display_name"], "SharePoint connection")

    def test_no_tenant_value_survives(self):
        for needle in TENANT:
            self.assertNotIn(needle, self.proc.stdout)

    def test_guard_catches_what_is_left(self):
        mod = load()
        self.assertTrue(mod.guard("dataset: https://contoso.sharepoint.com/sites/HR"))
        self.assertTrue(mod.guard("to: somchai.j@contoso.co.th"))
        self.assertTrue(mod.guard("table: 3f2504e0-4f89-41d3-9a0c-0305e82c3301"))

    def test_not_a_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "readme.txt").write_text("x", encoding="utf-8")
            self.assertEqual(run(tmp).returncode, 1)


if __name__ == "__main__":
    unittest.main()
