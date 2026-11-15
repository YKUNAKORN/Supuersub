#!/usr/bin/env python3
"""Tests for scripts/package_plugin.py: the archive for "Upload plugin".

Builds the real archive into a temp folder and checks its shape, then breaks one rule at
a time on a throwaway plugin and checks the build refuses. When the `claude` CLI is on
PATH, the unpacked archive is also run through `claude plugin validate`.

Run:  python -m unittest tests.test_package_plugin
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import package_plugin  # noqa: E402  (needs the sys.path line above)

ALLOWED_TOP = {".claude-plugin", "skills", "README.md", "LICENSE", "NOTICE"}
SKILL_NAMES = sorted(d.name for d in (ROOT / "skills").iterdir() if d.is_dir())


def _claude_can_validate() -> bool:
    """True when `claude plugin validate --help` runs. Some builds only support `claude -p`."""
    exe = shutil.which("claude")
    if not exe:
        return False
    try:
        return subprocess.run([exe, "plugin", "validate", "--help"], capture_output=True,
                              timeout=60).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


class TestRealArchive(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls._tmp.name)
        cls.path, cls.count, cls.size = package_plugin.build(ROOT, cls.out, yaml)
        with zipfile.ZipFile(cls.path) as zf:
            cls.names = zf.namelist()
            cls.plugin = json.loads(zf.read(".claude-plugin/plugin.json"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_name_and_location(self):
        self.assertEqual(self.path.name, "supersub.zip")

    def test_manifest_at_the_archive_root(self):
        self.assertIn(".claude-plugin/plugin.json", self.names)
        self.assertEqual(self.plugin["name"], "supersub")

    def test_only_what_an_installed_plugin_needs(self):
        tops = {n.split("/", 1)[0] for n in self.names}
        self.assertLessEqual(tops, ALLOWED_TOP)
        self.assertNotIn(".claude-plugin/marketplace.json", self.names)
        for bad in ("tests/", "docs/", "scripts/", "shared/", "dev-prompts/", "bin/"):
            self.assertFalse(any(n.startswith(bad) for n in self.names), bad)

    def test_no_caches_or_directory_entries(self):
        self.assertFalse(any("__pycache__" in n or n.endswith((".pyc", "/", ".DS_Store"))
                             for n in self.names))

    def test_every_skill_is_inside(self):
        for name in SKILL_NAMES:
            self.assertIn(f"skills/{name}/SKILL.md", self.names)
        self.assertIn("README.md", self.names)
        self.assertIn("LICENSE", self.names)
        self.assertIn("NOTICE", self.names)

    def test_every_skill_file_is_inside(self):
        on_disk = {p.relative_to(ROOT).as_posix() for p in (ROOT / "skills").rglob("*")
                   if p.is_file() and "__pycache__" not in p.parts
                   and p.suffix not in (".pyc", ".pyo") and p.name != ".DS_Store"}
        self.assertEqual(on_disk, {n for n in self.names if n.startswith("skills/")})

    def test_count_and_limits(self):
        self.assertEqual(self.count, len(self.names))
        self.assertLessEqual(self.count, package_plugin.MAX_FILES)
        self.assertLessEqual(self.size, package_plugin.MAX_BYTES)

    def test_reproducible(self):
        with tempfile.TemporaryDirectory() as other:
            again, _, _ = package_plugin.build(ROOT, Path(other), yaml)
            self.assertEqual(again.read_bytes(), self.path.read_bytes())

    @unittest.skipUnless(shutil.which("claude"), "claude CLI not on PATH")
    @unittest.skipUnless(_claude_can_validate(),
                         "claude CLI cannot run `claude plugin validate`")
    def test_claude_plugin_validate_accepts_the_unpacked_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(self.path) as zf:
                zf.extractall(tmp)
            proc = subprocess.run(["claude", "plugin", "validate", "."], cwd=tmp,
                                  capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("Validation passed", proc.stdout + proc.stderr)


def make_plugin(root: Path) -> None:
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "supersub", "version": "2.0.0"}), encoding="utf-8")
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"name": "supersub", "owner": {"name": "x"},
                    "plugins": [{"name": "supersub", "source": "."}]}), encoding="utf-8")
    skill = root / "skills" / "demo-skill"
    skill.mkdir(parents=True)
    fm = yaml.safe_dump({"name": "demo-skill", "description":
                         "Does one well-described thing for a test fixture, long enough "
                         "to clear the forty-character floor."}, sort_keys=False, width=1000)
    (skill / "SKILL.md").write_text(f"---\n{fm}---\n\n# Demo\n", encoding="utf-8")
    for name in ("README.md", "LICENSE", "NOTICE"):
        (root / name).write_text("x\n", encoding="utf-8")


class TestRefusals(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "plugin"
        self.out = Path(self._tmp.name) / "out"
        make_plugin(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def assertRefused(self, fragment: str, **limits) -> None:
        with self.assertRaises(package_plugin.Refused) as ctx:
            package_plugin.build(self.root, self.out, yaml, **limits)
        self.assertIn(fragment, str(ctx.exception))
        self.assertFalse((self.out / "supersub.zip").exists())

    def test_minimal_plugin_builds(self):
        path, count, _ = package_plugin.build(self.root, self.out, yaml)
        self.assertEqual(count, 5)
        self.assertTrue(path.is_file())

    def test_top_level_bin_refuses(self):
        (self.root / "bin").mkdir()
        self.assertRefused("bin/")

    def test_failing_skill_check_refuses(self):
        skill_md = self.root / "skills" / "demo-skill" / "SKILL.md"
        skill_md.write_text(skill_md.read_text().replace("name: demo-skill", "name: other"))
        self.assertRefused("frontmatter name equals folder name")

    def test_too_many_files_refuses(self):
        self.assertRefused("over the limit of 4", max_files=4)

    def test_too_many_bytes_refuses(self):
        self.assertRefused("over the limit of 10", max_bytes=10)

    def test_missing_notice_refuses(self):
        (self.root / "NOTICE").unlink()
        self.assertRefused("NOTICE")

    def test_cli_prints_count_and_size(self):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "package_plugin.py"),
                               "--out", str(self.out)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertRegex(proc.stdout, r"\d+ files, [\d,]+ bytes")


if __name__ == "__main__":
    unittest.main()
