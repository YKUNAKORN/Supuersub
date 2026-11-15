#!/usr/bin/env python3
"""Tests for scripts/skill_checks.py -- the checks validate.py runs on every skill.

Each test builds a throwaway plugin in a temp directory, breaks exactly one rule, and
asserts that the matching check fails while the others still pass. The last test
runs the checks over this repository, which is what CI relies on.

Run:  python -m unittest discover tests
"""

from __future__ import annotations

import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import skill_checks  # noqa: E402  (needs the sys.path line above)

GOOD_DESCRIPTION = ("Does one well-described thing for a test fixture, long enough to "
                    "clear the forty-character floor.")


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding="utf-8")
    return path


def make_skill(root: Path, folder: str = "demo-skill", name: str | None = None,
               description: str = GOOD_DESCRIPTION, body: str = "# Demo\n") -> Path:
    skill = root / "skills" / folder
    fm = yaml.safe_dump({"name": name or folder, "description": description},
                        sort_keys=False, width=1000)
    write(skill / "SKILL.md", f"---\n{fm}---\n\n{body}")
    return skill


def make_manifests(root: Path, plugin_name: str = "supersub",
                   entry_name: str = "supersub") -> None:
    write(root / ".claude-plugin" / "plugin.json",
          json.dumps({"name": plugin_name, "version": "2.0.0"}))
    write(root / ".claude-plugin" / "marketplace.json",
          json.dumps({"name": "supersub", "owner": {"name": "x"},
                      "plugins": [{"name": entry_name, "source": "."}]}))


def failed(results) -> list[str]:
    return [label for ok, label, _ in results if not ok]


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()


class TestSkillIdentity(Base):
    def test_clean_skill_passes(self):
        skill = make_skill(self.root)
        self.assertEqual(failed(skill_checks.check_skill_identity(skill, yaml)), [])

    def test_name_must_equal_folder(self):
        skill = make_skill(self.root, folder="demo-skill", name="other-skill")
        self.assertIn("demo-skill: frontmatter name equals folder name",
                      failed(skill_checks.check_skill_identity(skill, yaml)))

    def test_camel_case_folder_is_rejected(self):
        skill = make_skill(self.root, folder="createApp")
        self.assertTrue(any("kebab-case" in f
                            for f in failed(skill_checks.check_skill_identity(skill, yaml))))

    def test_folder_name_over_64_chars_is_rejected(self):
        skill = make_skill(self.root, folder="a" * 65)
        self.assertTrue(any("kebab-case" in f
                            for f in failed(skill_checks.check_skill_identity(skill, yaml))))

    def test_description_bounds(self):
        short = make_skill(self.root, folder="short-one", description="Too short.")
        long_ = make_skill(self.root, folder="long-one", description="x" * 651)
        for skill in (short, long_):
            self.assertTrue(any("description is 40-650" in f
                                for f in failed(skill_checks.check_skill_identity(skill, yaml))),
                            skill.name)

    def test_skill_md_byte_budget(self):
        skill = make_skill(self.root, body="x" * 8200)
        self.assertTrue(any("8192 bytes" in f
                            for f in failed(skill_checks.check_skill_identity(skill, yaml))))


class TestSelfContained(Base):
    def escaping(self, skill: Path) -> list[str]:
        return [p for _f, p in skill_checks.find_escaping_paths(skill)]

    def test_paths_inside_the_skill_pass(self):
        skill = make_skill(self.root, body=(
            "Run `python3 ${CLAUDE_SKILL_DIR}/scripts/tool.py`.\n"
            "See [the guide](references/guide.md).\n"))
        write(skill / "scripts" / "tool.py", "")
        write(skill / "references" / "guide.md", "Back to [SKILL.md](../SKILL.md).\n")
        write(skill / "assets" / "kit" / "README.md",
              "Catalog: [x](../../references/guide.md). This README.md is the kit.\n")
        self.assertEqual(self.escaping(skill), [])

    def test_parent_link_out_of_the_skill_fails(self):
        skill = make_skill(self.root, body="Rationale: [README](../../README.md).\n")
        self.assertIn("../../README.md", self.escaping(skill))

    def test_repo_root_directory_fails(self):
        skill = make_skill(self.root, body="Read docs/harvesting.md first.\n")
        self.assertIn("docs/harvesting.md", self.escaping(skill))

    def test_repo_root_file_in_a_reference_fails(self):
        skill = make_skill(self.root)
        write(skill / "references" / "rules.md", "See CONTRIBUTING.md for the process.\n")
        self.assertIn("CONTRIBUTING.md", self.escaping(skill))

    def test_bare_dotdot_in_an_asset_markdown_fails(self):
        skill = make_skill(self.root)
        write(skill / "assets" / "notes.md", "cp ../../../docs/x.md here\n")
        self.assertTrue(any(p.startswith("../../../") for p in self.escaping(skill)))

    def test_urls_are_ignored(self):
        skill = make_skill(self.root, body=(
            "[issue](https://github.com/o/r/issues/new) and "
            "https://learn.microsoft.com/power-apps/docs/thing\n"))
        self.assertEqual(self.escaping(skill), [])

    def test_check_wraps_the_finder(self):
        skill = make_skill(self.root, body="See tests/evals.\n")
        self.assertEqual(len(failed(skill_checks.check_self_contained(skill))), 1)


class TestMentionedFilesExist(Base):
    def test_missing_script_fails(self):
        skill = make_skill(self.root, body="Run `python3 ${CLAUDE_SKILL_DIR}/scripts/lint.py`.\n")
        self.assertEqual(len(failed(skill_checks.check_mentioned_files_exist(skill))), 1)

    def test_missing_reference_fails(self):
        skill = make_skill(self.root, body="Read `references/catalog.yaml`.\n")
        self.assertEqual(len(failed(skill_checks.check_mentioned_files_exist(skill))), 1)

    def test_present_files_pass(self):
        skill = make_skill(self.root, body=(
            "Run `python3 ${CLAUDE_SKILL_DIR}/scripts/lint.py` and read "
            "`references/catalog.yaml`.\n"))
        write(skill / "scripts" / "lint.py", "")
        write(skill / "references" / "catalog.yaml", "")
        self.assertEqual(failed(skill_checks.check_mentioned_files_exist(skill)), [])


class TestPluginLayout(Base):
    def test_clean_layout_passes(self):
        make_manifests(self.root)
        self.assertEqual(failed(skill_checks.check_plugin_layout(self.root)), [])

    def test_top_level_bin_fails(self):
        make_manifests(self.root)
        (self.root / "bin").mkdir()
        self.assertIn("no top-level bin/ directory",
                      failed(skill_checks.check_plugin_layout(self.root)))

    def test_root_claude_md_fails(self):
        make_manifests(self.root)
        write(self.root / "CLAUDE.md", "x\n")
        self.assertIn("no CLAUDE.md at the plugin root",
                      failed(skill_checks.check_plugin_layout(self.root)))

    def test_wrong_plugin_name_fails(self):
        make_manifests(self.root, plugin_name="power-app-yaml", entry_name="power-app-yaml")
        self.assertIn("plugin.json name is 'supersub'",
                      failed(skill_checks.check_plugin_layout(self.root)))

    def test_marketplace_entry_must_match(self):
        make_manifests(self.root, entry_name="something-else")
        self.assertIn("marketplace.json has a plugin entry named like plugin.json",
                      failed(skill_checks.check_plugin_layout(self.root)))


HANDOFF_BODY = ("# Demo\n\n## Hand-off\n\n[`handoff.md`](references/shared/handoff.md) is the "
                "contract. Next: **`other-skill`** reads this output.\n")


class TestCrossSkill(Base):
    """Phase 07: descriptions say what a skill is not for, hand-offs agree."""

    def test_not_for_with_a_named_skill_passes(self):
        skill = make_skill(self.root, description=GOOD_DESCRIPTION
                           + " Not for flows: that is other-skill.")
        self.assertEqual(failed(skill_checks.check_says_not_for(skill, ["other-skill"], yaml)),
                         [])

    def test_description_without_not_for_fails(self):
        skill = make_skill(self.root, description=GOOD_DESCRIPTION + " Pairs with other-skill.")
        self.assertEqual(len(failed(skill_checks.check_says_not_for(skill, ["other-skill"],
                                                                     yaml))), 1)

    def test_not_for_without_naming_a_skill_fails(self):
        skill = make_skill(self.root, description=GOOD_DESCRIPTION + " Not for flows.")
        self.assertEqual(len(failed(skill_checks.check_says_not_for(skill, ["other-skill"],
                                                                     yaml))), 1)

    def test_handoff_section_passes(self):
        skill = make_skill(self.root, body=HANDOFF_BODY)
        self.assertEqual(failed(skill_checks.check_names_next_step(skill, ["other-skill"])), [])

    def test_missing_handoff_section_fails(self):
        skill = make_skill(self.root, body="# Demo\n\n## Output\n\nNext: `other-skill`.\n")
        self.assertIn("demo-skill: SKILL.md has a '## Hand-off' section",
                      failed(skill_checks.check_names_next_step(skill, ["other-skill"])))

    def test_handoff_that_names_no_skill_fails(self):
        skill = make_skill(self.root, body=HANDOFF_BODY.replace("`other-skill`", "the next one"))
        self.assertIn("demo-skill: the hand-off names the next skill",
                      failed(skill_checks.check_names_next_step(skill, ["other-skill"])))

    def test_next_skill_outside_the_section_does_not_count(self):
        body = ("# Demo\n\nUse `other-skill` later.\n\n## Hand-off\n\n"
                "[`handoff.md`](references/shared/handoff.md). Done.\n\n## Rules\n\nnone\n")
        skill = make_skill(self.root, body=body)
        self.assertIn("demo-skill: the hand-off names the next skill",
                      failed(skill_checks.check_names_next_step(skill, ["other-skill"])))

    def test_path_into_another_skill_fails_with_or_without_skills_prefix(self):
        skill = make_skill(self.root, body="Read other-skill/references/naming.md first.\n")
        write(skill / "references" / "x.md", "See other-skill/scripts/lint.py.\n")
        hits = [p for _f, p in skill_checks.find_cross_skill_paths(skill, ["other-skill"])]
        self.assertEqual(sorted(hits), ["other-skill/references/naming.md",
                                        "other-skill/scripts/lint.py"])

    def test_naming_another_skill_in_words_passes(self):
        skill = make_skill(self.root, body="Hand the folder to `other-skill`.\n")
        self.assertEqual(failed(skill_checks.check_no_cross_skill_path(skill, ["other-skill"])),
                         [])

    def test_layout_folder_outside_the_contract_fails(self):
        skill = make_skill(self.root, body="Write supersub/mockups/index.html.\n")
        self.assertEqual(len(failed(skill_checks.check_layout_folders(skill))), 1)

    def test_layout_folders_in_the_contract_pass(self):
        skill = make_skill(self.root, body=(
            "Read supersub/mockup/sitemap.json, write supersub/app/, supersub/lists/ "
            "and supersub/flows/.\n"))
        self.assertEqual(failed(skill_checks.check_layout_folders(skill)), [])


class TestThisRepository(unittest.TestCase):
    def test_every_check_passes_here(self):
        self.assertEqual(failed(skill_checks.run_all(ROOT, yaml)), [])


if __name__ == "__main__":
    unittest.main()
