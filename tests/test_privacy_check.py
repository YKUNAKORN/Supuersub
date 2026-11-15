#!/usr/bin/env python3
"""Tests for scripts/privacy_check.py.

The terms used here are nonsense words made up for the test, written only into a
temporary directory. Never put a real term in this file.

Run:  python -m unittest discover tests
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "privacy_check", ROOT / "scripts" / "privacy_check.py")
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)

NONSENSE = "qzxwvu-plinth"


def make_repo(files: dict[str, str]) -> Path:
    tmp = Path(tempfile.mkdtemp())
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
    for name, text in files.items():
        p = tmp / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
    return tmp


class TestPrivateTerms(unittest.TestCase):
    def test_absent_terms_file_skips(self):
        repo = make_repo({"a.txt": f"{NONSENSE}\n"})
        self.assertIsNone(pc.load_terms(repo))
        self.assertEqual(pc.run(repo)[0], [])

    def test_terms_that_do_not_occur_pass(self):
        repo = make_repo({"a.txt": "hello\n"})
        (repo / ".private-terms.txt").write_text(
            f"# a comment\n\n{NONSENSE}\n", encoding="utf-8")
        self.assertEqual(pc.run(repo)[0], [])

    def test_content_hit_reports_file_and_line_not_term(self):
        repo = make_repo({"doc/a.txt": f"one\ntwo {NONSENSE.upper()} three\n"})
        (repo / ".private-terms.txt").write_text(NONSENSE + "\n", encoding="utf-8")
        hits = pc.run(repo)[0]
        self.assertEqual(len(hits), 1)
        self.assertIn("doc/a.txt:2", hits[0])
        self.assertNotIn(NONSENSE, hits[0].lower())

    def test_file_name_hit_does_not_print_the_name(self):
        repo = make_repo({f"{NONSENSE}-notes.txt": "clean\n"})
        (repo / ".private-terms.txt").write_text(NONSENSE + "\n", encoding="utf-8")
        hits = pc.run(repo)[0]
        self.assertEqual(len(hits), 1)
        self.assertNotIn(NONSENSE, hits[0].lower())

    def test_binary_content_is_not_scanned_but_name_is(self):
        repo = make_repo({"b.bin": f"\0{NONSENSE}"})
        (repo / ".private-terms.txt").write_text(NONSENSE + "\n", encoding="utf-8")
        self.assertEqual(pc.run(repo)[0], [])


class TestShapes(unittest.TestCase):
    def shapes(self, text: str) -> list[str]:
        return pc.run(make_repo({"f.txt": text}))[1]

    def test_allowed_forms_pass(self):
        ok = ("a@example.com b@example.org c@contoso.com d@contoso.co.th "
              "https://contoso.sharepoint.com/sites/HR contoso.onmicrosoft.com "
              "pkg@1.2.3 @types/node")
        self.assertEqual(self.shapes(ok), [])

    def test_foreign_email_fails(self):
        at = "@"  # keep literal addresses out of this file: the guard scans it too
        self.assertEqual(len(self.shapes(f"mail me at someone{at}elsewhere.net")), 1)
        self.assertEqual(len(self.shapes(f"x{at}notexample.com")), 1)

    def test_foreign_tenant_hosts_fail(self):
        h1 = "https://acme" + ".share" + "point.com/sites/x"
        h2 = "bob" + "@acme" + ".onmicro" + "soft.com"
        self.assertTrue(self.shapes(h1))
        self.assertTrue(self.shapes(h2))

    def test_home_paths_fail(self):
        for p in ("/Us" + "ers/someone/x", "see /ho" + "me/someone/x",
                  "C:\\Us" + "ers\\someone"):
            self.assertTrue(self.shapes(p), p)

    def test_repository_itself_is_clean(self):
        self.assertEqual(pc.scan_shapes(ROOT, pc.candidate_files(ROOT)), [])


if __name__ == "__main__":
    unittest.main()
