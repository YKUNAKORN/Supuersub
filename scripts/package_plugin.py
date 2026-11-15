#!/usr/bin/env python3
"""Build dist/supersub.zip for Customize > Plugins > Add > Upload plugin.

    python scripts/package_plugin.py            # writes dist/supersub.zip
    python scripts/package_plugin.py --out DIR  # writes DIR/supersub.zip

The archive holds only what an installed plugin needs:

    .claude-plugin/plugin.json   at the archive root, as the upload expects
    skills/                      the five skills, without caches
    README.md, LICENSE, NOTICE

`marketplace.json` is left out on purpose: it describes the repository as a
marketplace for the "Add marketplace" route, and an uploaded plugin is not a
marketplace.

The build refuses (exit 1, nothing written) when the repository has a top-level bin/
(claude.ai and Cowork refuse such a plugin), when any skill fails the generic checks in
scripts/skill_checks.py, or when the result would exceed 5,000 files or 200 MB, the
claude.ai limits. It prints the file count and the size.

Entries are sorted and carry one fixed timestamp, so the same tree gives the same bytes.
Needs PyYAML (for the skill checks).
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import skill_checks  # noqa: E402  (needs the sys.path line above)

ARCHIVE_NAME = "supersub.zip"
TOP_FILES = ("README.md", "LICENSE", "NOTICE")
MANIFEST = ".claude-plugin/plugin.json"
MAX_FILES = 5000
MAX_BYTES = 200 * 1024 * 1024
# Any fixed date at or after 1980 (the zip format's epoch) makes the output reproducible.
STAMP = (2026, 1, 1, 0, 0, 0)
SKIP_NAMES = {"__pycache__", ".DS_Store", "Thumbs.db"}
SKIP_SUFFIXES = (".pyc", ".pyo")


class Refused(Exception):
    """The archive must not be built; the message says why."""


def collect(root: Path) -> list[tuple[str, Path]]:
    """(archive name, source path) for every file that ships, sorted by name."""
    files: list[tuple[str, Path]] = []
    manifest = root / MANIFEST
    if not manifest.is_file():
        raise Refused(f"{MANIFEST} is missing")
    files.append((MANIFEST, manifest))
    for name in TOP_FILES:
        p = root / name
        if not p.is_file():
            raise Refused(f"{name} is missing at the plugin root")
        files.append((name, p))
    skills = root / "skills"
    if not skills.is_dir():
        raise Refused("skills/ is missing")
    for p in sorted(skills.rglob("*")):
        rel = p.relative_to(root)
        if not p.is_file() or set(rel.parts) & SKIP_NAMES or p.suffix in SKIP_SUFFIXES:
            continue
        files.append((rel.as_posix(), p))
    return sorted(files)


def preflight(root: Path, yaml_mod) -> None:
    if (root / "bin").exists():
        raise Refused("the plugin root has a top-level bin/; claude.ai and Cowork refuse "
                      "to install such a plugin")
    failed = [f"{label}: {detail}" if detail else label
              for ok, label, detail in skill_checks.run_all(root, yaml_mod) if not ok]
    if failed:
        raise Refused("the generic skill checks fail:\n  " + "\n  ".join(failed))


def build(root: Path, out_dir: Path, yaml_mod, max_files: int = MAX_FILES,
          max_bytes: int = MAX_BYTES) -> tuple[Path, int, int]:
    """Write <out_dir>/supersub.zip. Returns (path, file count, archive bytes)."""
    preflight(root, yaml_mod)
    files = collect(root)
    raw = sum(p.stat().st_size for _, p in files)
    if len(files) > max_files:
        raise Refused(f"{len(files)} files, over the limit of {max_files}")
    if raw > max_bytes:
        raise Refused(f"{raw} bytes before compression, over the limit of {max_bytes}")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / ARCHIVE_NAME
    tmp = target.with_suffix(".zip.tmp")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, path in files:
            info = zipfile.ZipInfo(name, date_time=STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())
    size = tmp.stat().st_size
    if size > max_bytes:
        tmp.unlink()
        raise Refused(f"the archive is {size} bytes, over the limit of {max_bytes}")
    tmp.replace(target)
    return target, len(files), size


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=ROOT / "dist",
                    help="output folder (default: dist/)")
    args = ap.parse_args(argv)
    try:
        import yaml
    except ImportError:
        print("REFUSED: PyYAML is needed for the skill checks: pip install pyyaml",
              file=sys.stderr)
        return 1
    try:
        path, count, size = build(ROOT, args.out, yaml)
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 1
    try:
        shown = path.relative_to(Path.cwd())
    except ValueError:
        shown = path
    print(f"Wrote {shown}: {count} files, {size:,} bytes ({size / 1024 / 1024:.2f} MB)")
    print(f"Limits: {MAX_FILES:,} files, {MAX_BYTES // 1024 // 1024} MB.")
    print("Upload it at Customize > Plugins > Add > Upload plugin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
