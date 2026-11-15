#!/usr/bin/env python3
"""Fixture tests for skills/create-flow/scripts/flow_lint.py.

The base is the skill's own example, assets/example/SendTestEmail.flow.json (it rebuilds
the owner's reference package). Each case below is one defect, written as an edit to a
copy of that base, with what the linter must report: the exact set of check ids, the
exit code and the verdict code.

The cases run against a copy of references/connectors.yaml with every evidence level
set to import-tested, so unverified-step does not mask the check under test. Separate
tests run against the real catalog.

Assertions are on check ids, exit codes and verdict codes only -- never on wording.

Run:  python -m unittest discover tests
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "create-flow"
LINTER = SKILL / "scripts" / "flow_lint.py"
CATALOG = SKILL / "references" / "connectors.yaml"
BASE = json.loads((SKILL / "assets" / "example" / "SendTestEmail.flow.json")
                  .read_text(encoding="utf-8"))
SEND = "Send_an_email_(V2)"


def trusted(node):
    """The catalog with every evidence level raised to import-tested."""
    if isinstance(node, dict):
        return {k: ("import-tested" if v in ("unverified", "export", "doc") else trusted(v))
                for k, v in node.items()}
    if isinstance(node, list):
        return [trusted(v) for v in node]
    return node


def params(s):
    return s["actions"][SEND]["inputs"]["parameters"]


def _declare(s, name="Subject"):
    s["placeholders"][name] = {"description": "the subject line",
                               "setAfterImport": "Send an email (V2) > Subject"}


def _set(path, value):
    def edit(s):
        node = s
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
    return edit


def _delete(path):
    def edit(s):
        node = s
        for key in path[:-1]:
            node = node[key]
        del node[path[-1]]
    return edit


def _add_action(key, action):
    def edit(s):
        s["actions"][key] = action
    return edit


GUID = "12345678-1234-4123-8123-123456789abc"

# name -> (edit, extra args, expected check ids, exit code, verdict code)
CASES = {
    "clean": (None, [], set(), 0, "safe"),
    "spec-invalid-missing": (_delete(["triggers"]), [], {"spec-invalid"}, 1, "will_fail"),
    "spec-invalid-status": (_set(["actions", "Build_message", "runAfter"],
                                 {"Get_Bangkok_time": ["Done"]}), [], {"spec-invalid"}, 1,
                            "will_fail"),
    "spec-invalid-two-triggers": (_set(["triggers", "manual2"],
                                       {"type": "Request", "kind": "Button"}), [],
                                  {"spec-invalid"}, 1, "will_fail"),
    "action-key-invalid": (_add_action("Bad key!", {"runAfter": {}, "type": "Compose",
                                                    "inputs": "x"}), [],
                           {"action-key-invalid"}, 1, "will_fail"),
    "action-key-duplicate": (_add_action("Group", {
        "runAfter": {}, "type": "Scope",
        "actions": {"Get_Bangkok_time": {"runAfter": {}, "type": "Compose", "inputs": "x"}}}),
        [], {"action-key-duplicate", "catalog-missing"}, 1, "will_fail"),
    "run-after-unknown": (_set(["actions", "Build_message", "runAfter"],
                               {"Nope": ["Succeeded"]}), [], {"run-after-unknown"}, 1,
                          "will_fail"),
    "run-after-cycle": (_set(["actions", "Get_Bangkok_time", "runAfter"],
                             {SEND: ["Succeeded"]}), [], {"run-after-cycle"}, 1, "will_fail"),
    "connector-undeclared": (_set(["connectors"], []), [], {"connector-undeclared"}, 1,
                             "will_fail"),
    "host-invalid-operation": (_delete(["actions", SEND, "inputs", "host", "operationId"]),
                               [], {"host-invalid"}, 1, "will_fail"),
    "host-invalid-apiid": (_set(["actions", SEND, "inputs", "host", "apiId"],
                                "/providers/Microsoft.PowerApps/apis/shared_teams"), [],
                           {"host-invalid"}, 1, "will_fail"),
    "catalog-missing-operation": (_set(["actions", SEND, "inputs", "host", "operationId"],
                                       "SendEmailV3"), [], {"catalog-missing"}, 1,
                                  "will_fail"),
    "catalog-missing-parameter": (lambda s: params(s).update({"emailMessage/Cc": "x"}), [],
                                  {"catalog-missing"}, 1, "will_fail"),
    "catalog-missing-trigger": (_set(["triggers", "manual", "kind"], "Http"), [],
                                {"catalog-missing"}, 1, "will_fail"),
    "catalog-missing-hint": (_set(["triggers", "manual", "inputs", "schema", "properties",
                                   "text", "x-ms-content-hint"], "NUMBER"), [],
                             {"catalog-missing"}, 1, "will_fail"),
    "catalog-missing-action-type": (_add_action("Stop", {"runAfter": {SEND: ["Succeeded"]},
                                                         "type": "Terminate"}), [],
                                    {"catalog-missing"}, 1, "will_fail"),
    "connection-embedded": (_set(["actions", SEND, "inputs", "host", "connectionName"],
                                 f"shared-office365-{GUID}"), [],
                            {"connection-embedded", "connector-unused", "guid-literal"}, 1,
                            "will_fail"),
    "expression-unbalanced": (lambda s: params(s).update(
        {"emailMessage/Body": "<p>@{outputs('Build_message')</p>"}), [],
        {"expression-unbalanced"}, 1, "will_fail"),
    "expression-unbalanced-parens": (_set(["actions", "Get_Bangkok_time", "inputs"],
                                          "@convertFromUtc(utcNow(), 'UTC'"), [],
                                     {"expression-unbalanced"}, 1, "will_fail"),
    "expression-reference": (lambda s: params(s).update(
        {"emailMessage/Body": "<p>@{outputs('Missing')}</p>"}), [],
        {"expression-reference"}, 1, "will_fail"),
    "placeholder-undeclared": (lambda s: params(s).update(
        {"emailMessage/Subject": "{{Subject}}"}), [], {"placeholder-undeclared"}, 1,
        "will_fail"),
    "placeholder-unresolved": (lambda s: (params(s).update(
        {"emailMessage/Subject": "{{Subject}}"}), _declare(s)), [],
        {"placeholder-unresolved"}, 0, "unverified"),
    "placeholder-resolved-by-set": (lambda s: (params(s).update(
        {"emailMessage/Subject": "{{Subject}}"}), _declare(s)), ["--set", "Subject=Hi"],
        set(), 0, "safe"),
    "placeholder-unused": (lambda s: _declare(s), [], {"placeholder-unused"}, 0,
                           "unverified"),
    "connector-unused": (_set(["connectors"], ["shared_office365", "shared_teams"]), [],
                         {"connector-unused"}, 0, "unverified"),
    "sensitive-email": (lambda s: params(s).update({"emailMessage/To": "somchai@contoso.co.th"}),
                        [], {"sensitive-value"}, 1, "will_fail"),
    "sensitive-email-example-ok": (lambda s: params(s).update(
        {"emailMessage/To": "someone@example.com"}), [], set(), 0, "safe"),
    "sensitive-tenant-url": (lambda s: params(s).update(
        {"emailMessage/Subject": "see https://contoso.sharepoint.com/sites/HR"}), [],
        {"sensitive-value"}, 1, "will_fail"),
    "sensitive-secret": (lambda s: params(s).update(
        {"emailMessage/Subject": "password=hunter2"}), [], {"sensitive-value"}, 1,
        "will_fail"),
    "guid-literal": (lambda s: params(s).update({"emailMessage/Subject": f"list {GUID}"}),
                     [], {"guid-literal"}, 0, "unverified"),
    "strict": (lambda s: _declare(s), ["--strict"], {"placeholder-unused"}, 2,
               "unverified"),
}


def run_linter(paths, *args: str, cwd: Path = ROOT) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, str(LINTER), *map(str, paths), *args, "--json"],
                          capture_output=True, text=True, encoding="utf-8", cwd=str(cwd))
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - failure path
        raise AssertionError(f"--json did not emit JSON (exit {proc.returncode}).\n"
                             f"stderr: {proc.stderr}") from exc
    return proc.returncode, payload["report"]


class TestCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.catalog = cls.dir / "trusted.yaml"
        cat = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
        cls.catalog.write_text(yaml.safe_dump(trusted(cat), sort_keys=False),
                               encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def write(self, name: str, spec) -> Path:
        path = self.dir / f"{name}.flow.json"
        text = spec if isinstance(spec, str) else json.dumps(spec, ensure_ascii=False)
        path.write_text(text, encoding="utf-8")
        return path

    def test_cases(self):
        for name, (edit, args, ids, code, verdict) in CASES.items():
            with self.subTest(case=name):
                spec = copy.deepcopy(BASE)
                if edit:
                    edit(spec)
                path = self.write(name, spec)
                rc, report = run_linter([path], "--catalog", str(self.catalog), *args)
                self.assertEqual({f["check"] for f in report["findings"]}, ids)
                self.assertEqual(rc, code)
                self.assertEqual(report["verdict_code"], verdict)

    def test_not_json(self):
        rc, report = run_linter([self.write("broken", "{")], "--catalog", str(self.catalog))
        self.assertEqual({f["check"] for f in report["findings"]}, {"spec-invalid"})
        self.assertEqual(rc, 1)

    def test_name_duplicate(self):
        a = self.write("a", BASE)
        b = self.write("b", BASE)
        rc, report = run_linter([a, b], "--catalog", str(self.catalog))
        self.assertEqual({f["check"] for f in report["findings"]}, {"name-duplicate"})
        self.assertEqual(rc, 1)

    def test_every_check_id_is_exercised(self):
        documented = {"spec-invalid", "name-duplicate", "action-key-invalid",
                      "action-key-duplicate", "run-after-unknown", "run-after-cycle",
                      "connector-undeclared", "host-invalid", "catalog-missing",
                      "connection-embedded", "expression-unbalanced",
                      "expression-reference", "placeholder-undeclared", "sensitive-value",
                      "unverified-step", "placeholder-unresolved", "placeholder-unused",
                      "connector-unused", "guid-literal"}
        doc = LINTER.read_text(encoding="utf-8").split('"""')[1]
        for check in documented:
            self.assertIn(check, doc)
        covered = set().union(*(c[2] for c in CASES.values())) | {"unverified-step",
                                                                   "name-duplicate"}
        self.assertEqual(documented - covered, set())


class TestRealCatalog(unittest.TestCase):
    def test_example_warns_only_on_unverified_steps(self):
        rc, report = run_linter([SKILL / "assets" / "example" / "SendTestEmail.flow.json"])
        checks = {f["check"] for f in report["findings"]}
        self.assertEqual(checks, {"unverified-step"})
        self.assertEqual(rc, 0)
        self.assertEqual(report["verdict_code"], "unverified")
        # The reference package was import-tested (owner, 2026-11-15); what the builder
        # writes differently from it -- the generated connection reference -- is not.
        self.assertEqual(len(report["flows"][0]["unverified"]), 1)
        self.assertIn("connection reference", report["flows"][0]["unverified"][0])

    def test_runs_from_outside_the_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, report = run_linter([SKILL / "assets" / "example" / "SendTestEmail.flow.json"],
                                    cwd=Path(tmp))
        self.assertEqual(rc, 0)
        self.assertEqual(report["verdict_code"], "unverified")

    def test_unreadable_catalog_is_unproven(self):
        rc, report = run_linter([SKILL / "assets" / "example" / "SendTestEmail.flow.json"],
                                "--catalog", str(ROOT / "no-such-catalog.yaml"))
        self.assertEqual(report["verdict_code"], "unproven")
        self.assertEqual(rc, 0)

    def test_every_catalog_level_is_declared(self):
        cat = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
        levels = []

        def walk(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == "evidence":
                        levels.append(v)
                    elif k == "parameters" and isinstance(v, dict):
                        levels.extend(v.values())
                    else:
                        walk(v)
        walk({k: v for k, v in cat.items() if k != "unattempted"})
        self.assertTrue(levels)
        self.assertLessEqual(set(levels), {"import-tested", "export", "doc", "unverified"})


if __name__ == "__main__":
    unittest.main()
