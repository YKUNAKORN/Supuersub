#!/usr/bin/env python3
"""Plugin-wide checks that apply to every skill under skills/.

Imported by scripts/validate.py; kept in its own module so tests can call each check
on a throwaway directory instead of on this repository.

Every function returns a list of (ok, label, detail) tuples and never prints, so the
caller decides how a failure is reported. The rules come from dev-prompts/00-CONTEXT.md
section 4: a skill is portable only if everything it needs at run time sits inside its
own folder, because in chat that folder is all that reaches the sandbox.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

Result = tuple[bool, str, str]

PLUGIN_NAME = "supersub"
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SKILL_NAME_MAX = 64
SKILL_MD_MAX_BYTES = 8192
DESCRIPTION_MIN_CHARS = 40
DESCRIPTION_MAX_CHARS = 650

# Top-level directories of this repository that never ship inside a skill. A path
# that starts with one of them only resolves in a clone of the repo.
# shared/ is listed because a skill reads its synced copy in references/shared/, never
# the master.
REPO_ROOT_DIRS = ("docs", "tests", "skills", "shared", "dev-prompts", ".github",
                  ".claude-plugin")
# Repo-root files. A bare mention is allowed only when the mentioning file has a
# sibling of that name (assets/test-snippets/README.md talking about itself).
REPO_ROOT_FILES = ("README.md", "CONTRIBUTING.md", "CHANGELOG.md", "CODE_OF_CONDUCT.md",
                   "SECURITY.md", "SUPPORT.md", "NOTICE", "LICENSE")

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
_DOTDOT_RE = re.compile(r"(?<![\w.])((?:\.\./)+[\w.\-/]*)")
_ROOT_DIR_RE = re.compile(
    r"(?<![\w./-])((?:%s)/[\w.\-/]*)" % "|".join(re.escape(d) for d in REPO_ROOT_DIRS))
_ROOT_FILE_RE = re.compile(
    r"(?<![\w./-])(%s)(?![\w-])" % "|".join(re.escape(f) for f in REPO_ROOT_FILES))
# Also matches after `${CLAUDE_SKILL_DIR}/`, the form SKILL.md uses for script calls.
_SKILL_PATH_RE = re.compile(r"(?:(?<![\w./-])|(?<=\}/))(scripts|references)/([\w.\-]+)")


def read_frontmatter(skill_md: Path, yaml_mod) -> dict | None:
    """The parsed frontmatter mapping, or None when there is none or it does not parse."""
    m = _FRONTMATTER_RE.match(skill_md.read_text(encoding="utf-8"))
    if not m:
        return None
    try:
        fm = yaml_mod.safe_load(m.group(1))
    except yaml_mod.YAMLError:
        return None
    return fm if isinstance(fm, dict) else None


def check_skill_identity(skill_dir: Path, yaml_mod) -> list[Result]:
    """Folder name, frontmatter name, description length, SKILL.md size."""
    out: list[Result] = []
    folder = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    out.append((skill_md.is_file(), f"{folder}: SKILL.md present", ""))
    if not skill_md.is_file():
        return out

    out.append((bool(SKILL_NAME_RE.match(folder)) and len(folder) <= SKILL_NAME_MAX,
                f"{folder}: folder name is kebab-case, at most {SKILL_NAME_MAX} chars",
                "lowercase letters, digits and single hyphens only"))

    fm = read_frontmatter(skill_md, yaml_mod)
    out.append((fm is not None, f"{folder}: frontmatter parses", ""))
    if fm is None:
        return out
    name = fm.get("name")
    out.append((name == folder, f"{folder}: frontmatter name equals folder name",
                f"got {name!r}"))
    desc = fm.get("description")
    n = len(desc.strip()) if isinstance(desc, str) else 0
    out.append((DESCRIPTION_MIN_CHARS <= n <= DESCRIPTION_MAX_CHARS,
                f"{folder}: description is {DESCRIPTION_MIN_CHARS}-"
                f"{DESCRIPTION_MAX_CHARS} chars",
                f"got {n}. Cut justification sentences, never a trigger phrase."))
    size = len(skill_md.read_bytes())
    out.append((size <= SKILL_MD_MAX_BYTES,
                f"{folder}: SKILL.md is within {SKILL_MD_MAX_BYTES} bytes",
                f"got {size} ({size - SKILL_MD_MAX_BYTES} over)"))
    return out


def _scanned_files(skill_dir: Path) -> list[Path]:
    files = [skill_dir / "SKILL.md"]
    refs = skill_dir / "references"
    if refs.is_dir():
        files += sorted(p for p in refs.rglob("*") if p.is_file())
    assets = skill_dir / "assets"
    if assets.is_dir():
        files += sorted(assets.rglob("*.md"))
    return [f for f in files if f.is_file()]


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def find_escaping_paths(skill_dir: Path) -> list[tuple[str, str]]:
    """(file, offending path) for every path in a scanned file that leaves the skill.

    Scanned: SKILL.md, everything under references/, and assets/**/*.md -- the files
    Claude reads at run time. A path escapes when it is a link or ../ path that
    resolves outside the skill folder, when it starts with a repo-root directory
    (docs/, tests/, ...), or when it names a repo-root file with no sibling of that
    name next to the file that mentions it.
    """
    found: list[tuple[str, str]] = []
    for f in _scanned_files(skill_dir):
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = f.relative_to(skill_dir).as_posix()
        hits: set[str] = set()
        for target in _LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_part = target.split("#", 1)[0]
            if path_part and not _inside(f.parent / path_part, skill_dir):
                hits.add(target)
        for target in _DOTDOT_RE.findall(text):
            if not _inside(f.parent / target, skill_dir):
                hits.add(target)
        hits.update(_ROOT_DIR_RE.findall(text))
        for name in _ROOT_FILE_RE.findall(text):
            if not (f.parent / name).is_file():
                hits.add(name)
        found += [(rel, h) for h in sorted(hits)]
    return found


def check_self_contained(skill_dir: Path) -> list[Result]:
    folder = skill_dir.name
    escaping = find_escaping_paths(skill_dir)
    return [(not escaping,
             f"{folder}: no path in SKILL.md, references/ or assets/**/*.md leaves the skill",
             "; ".join(f"{f}: {p}" for f, p in escaping[:12])
             + ". In chat only the skill folder reaches the sandbox.")]


def check_mentioned_files_exist(skill_dir: Path) -> list[Result]:
    """Every scripts/<file> and references/<file> SKILL.md names exists in the skill."""
    folder = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return []
    text = skill_md.read_text(encoding="utf-8")
    missing = sorted({f"{d}/{n}" for d, n in _SKILL_PATH_RE.findall(text)
                      if not (skill_dir / d / n.rstrip(".")).exists()})
    return [(not missing, f"{folder}: every scripts/ and references/ file SKILL.md names exists",
             f"missing inside the skill: {missing}")]


def check_plugin_layout(root: Path) -> list[Result]:
    """Repo-root rules: no bin/, no CLAUDE.md, plugin and marketplace names agree."""
    out: list[Result] = [
        (not (root / "bin").exists(), "no top-level bin/ directory",
         "claude.ai and Cowork refuse to install a plugin that has one"),
        (not (root / "CLAUDE.md").exists(), "no CLAUDE.md at the plugin root",
         "it is not loaded as context and `claude plugin validate` warns about it"),
    ]
    plugin = market = None
    try:
        plugin = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        out.append((False, "plugin.json is readable JSON", str(e)))
    try:
        market = json.loads(
            (root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        out.append((False, "marketplace.json is readable JSON", str(e)))
    if isinstance(plugin, dict):
        out.append((plugin.get("name") == PLUGIN_NAME,
                    f"plugin.json name is '{PLUGIN_NAME}'", f"got {plugin.get('name')!r}"))
    if isinstance(plugin, dict) and isinstance(market, dict):
        names = [p.get("name") for p in market.get("plugins") or [] if isinstance(p, dict)]
        out.append((plugin.get("name") in names,
                    "marketplace.json has a plugin entry named like plugin.json",
                    f"plugin.json: {plugin.get('name')!r}, entries: {names}"))
    return out


# --- Cross-skill consistency (phase 07) ---------------------------------------------
# The hand-off contract (shared/handoff.md) fixes one folder per skill under supersub/.
LAYOUT_FOLDERS = ("mockup", "app", "lists", "flows")
_LAYOUT_RE = re.compile(r"(?<![\w-])supersub/([A-Za-z0-9_.-]+)")
_NOT_FOR_RE = re.compile(r"\b(not for|does not)\b", re.I)
_HANDOFF_HEADING_RE = re.compile(r"^## Hand-off\b.*$", re.M)


def _description(skill_dir: Path, yaml_mod) -> str:
    fm = read_frontmatter(skill_dir / "SKILL.md", yaml_mod) if (
        skill_dir / "SKILL.md").is_file() else None
    desc = (fm or {}).get("description")
    return desc if isinstance(desc, str) else ""


def check_says_not_for(skill_dir: Path, others: list[str], yaml_mod) -> list[Result]:
    """The description says what the skill is not for, and names a skill that is."""
    folder = skill_dir.name
    desc = _description(skill_dir, yaml_mod)
    named = [o for o in others if o in desc]
    return [(bool(_NOT_FOR_RE.search(desc)) and bool(named),
             f"{folder}: description says what it is not for and names another skill",
             f"needs 'Not for ...' or 'Does not ...' plus one of {others}; "
             f"names {named or 'none'}")]


def handoff_section(text: str) -> str | None:
    """The text of the '## Hand-off' section of a SKILL.md, or None."""
    m = _HANDOFF_HEADING_RE.search(text)
    if not m:
        return None
    rest = text[m.end():]
    nxt = re.search(r"^## ", rest, re.M)
    return rest[:nxt.start()] if nxt else rest


def check_names_next_step(skill_dir: Path, others: list[str]) -> list[Result]:
    """SKILL.md has a '## Hand-off' section that links the contract and names a skill."""
    folder = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return []
    section = handoff_section(skill_md.read_text(encoding="utf-8"))
    out: list[Result] = [(section is not None, f"{folder}: SKILL.md has a '## Hand-off' section",
                          "every skill ends the same way (shared/handoff.md)")]
    if section is None:
        return out
    out.append(("references/shared/handoff.md" in section,
                f"{folder}: the hand-off links references/shared/handoff.md",
                "the contract every skill hands off by"))
    named = [o for o in others if f"`{o}`" in section]
    out.append((bool(named), f"{folder}: the hand-off names the next skill",
                f"none of {others} appears in backticks in the section"))
    return out


def find_cross_skill_paths(skill_dir: Path, others: list[str]) -> list[tuple[str, str]]:
    """(file, path) for every path into another skill's folder, with or without skills/."""
    if not others:
        return []
    pat = re.compile(r"(?<![\w-])((?:%s)/(?:references|scripts|assets)/[\w.\-/]*)"
                     % "|".join(re.escape(o) for o in others))
    found: list[tuple[str, str]] = []
    for f in _scanned_files(skill_dir):
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = f.relative_to(skill_dir).as_posix()
        found += [(rel, h) for h in sorted({h.rstrip(".") for h in pat.findall(text)})]
    return found


def check_no_cross_skill_path(skill_dir: Path, others: list[str]) -> list[Result]:
    folder = skill_dir.name
    hits = find_cross_skill_paths(skill_dir, others)
    return [(not hits, f"{folder}: no path points into another skill's folder",
             "; ".join(f"{f}: {p}" for f, p in hits[:12])
             + ". Name the other skill in words; its files are not in this sandbox.")]


def check_layout_folders(skill_dir: Path) -> list[Result]:
    """Every supersub/<folder> a skill mentions is one the hand-off contract defines."""
    folder = skill_dir.name
    bad: set[str] = set()
    for f in _scanned_files(skill_dir):
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for name in _LAYOUT_RE.findall(text):
            name = name.rstrip(".")
            if name not in LAYOUT_FOLDERS:
                bad.add(f"{f.relative_to(skill_dir).as_posix()}: supersub/{name}")
    return [(not bad, f"{folder}: every supersub/<folder> it names is in the hand-off layout",
             f"{sorted(bad)}; allowed: {list(LAYOUT_FOLDERS)}")]


def skill_dirs(root: Path) -> list[Path]:
    base = root / "skills"
    return sorted(d for d in base.iterdir() if d.is_dir()) if base.is_dir() else []


def run_all(root: Path, yaml_mod) -> list[Result]:
    results: list[Result] = []
    dirs = skill_dirs(root)
    results.append((bool(dirs), "skills/ holds at least one skill", ""))
    names = [d.name for d in dirs]
    for d in dirs:
        others = [n for n in names if n != d.name]
        results += check_skill_identity(d, yaml_mod)
        results += check_self_contained(d)
        results += check_mentioned_files_exist(d)
        if others:
            results += check_says_not_for(d, others, yaml_mod)
            results += check_names_next_step(d, others)
            results += check_no_cross_skill_path(d, others)
        results += check_layout_folders(d)
    results += check_plugin_layout(root)
    return results
