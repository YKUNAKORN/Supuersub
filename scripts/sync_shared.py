#!/usr/bin/env python3
"""Copy the files several skills need from shared/ into each skill that needs them.

A skill can only read its own folder at run time (in chat, only that folder reaches the
sandbox), so a file two skills need cannot live in one place. It lives once in shared/
at the repository root and is copied, byte for byte, into
skills/<skill>/references/shared/. The copies are never edited by hand.

    python scripts/sync_shared.py --check    # exit 1 if any copy is missing or differs
    python scripts/sync_shared.py --write    # bring every copy up to date

--check also fails on a file in a references/shared/ folder that the manifest does not
name: a stale copy would otherwise linger after its source was removed.

Standard library only. scripts/validate.py runs --check.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"
SKILLS = ROOT / "skills"

# Which skill receives which shared file. Add a skill here when it starts needing one;
# a skill that is not listed gets no references/shared/ folder at all.
MANIFEST: dict[str, list[str]] = {
    "design-md": ["handoff.md", "powerapps-profile.md"],
    "mock-ui": ["handoff.md", "powerapps-profile.md"],
    "create-list": ["handoff.md"],
    "create-flow": ["handoff.md"],
}


def plan(root: Path = ROOT, manifest: dict[str, list[str]] | None = None
         ) -> list[tuple[str, Path, Path | None]]:
    """(state, target, source) for every copy the manifest implies, plus strays.

    state is one of: ok, missing, differs, no-source, stray.
    """
    manifest = MANIFEST if manifest is None else manifest
    shared = root / "shared"
    out: list[tuple[str, Path, Path | None]] = []
    for skill, files in sorted(manifest.items()):
        dest_dir = root / "skills" / skill / "references" / "shared"
        for name in files:
            src = shared / name
            dst = dest_dir / name
            if not src.is_file():
                out.append(("no-source", dst, src))
            elif not dst.is_file():
                out.append(("missing", dst, src))
            elif dst.read_bytes() != src.read_bytes():
                out.append(("differs", dst, src))
            else:
                out.append(("ok", dst, src))
        if dest_dir.is_dir():
            for extra in sorted(p for p in dest_dir.iterdir() if p.is_file()):
                if extra.name not in files:
                    out.append(("stray", extra, None))
    # A references/shared/ folder in a skill the manifest does not mention is a stray too.
    skills_dir = root / "skills"
    if skills_dir.is_dir():
        for d in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
            dest_dir = d / "references" / "shared"
            if d.name not in manifest and dest_dir.is_dir():
                for extra in sorted(p for p in dest_dir.iterdir() if p.is_file()):
                    out.append(("stray", extra, None))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sync_shared.py", description=__doc__.split("\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report drift, change nothing")
    mode.add_argument("--write", action="store_true", help="copy shared/ files into skills")
    args = parser.parse_args(argv)

    rows = plan()
    bad = 0
    for state, dst, src in rows:
        rel = dst.relative_to(ROOT).as_posix()
        if state == "ok":
            print(f"  ok        {rel}")
            continue
        if state == "no-source":
            print(f"  NO SOURCE {rel}  (manifest names {src.relative_to(ROOT).as_posix()}, "
                  "which does not exist)")
            bad += 1
            continue
        if args.write and state in ("missing", "differs"):
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
            print(f"  written   {rel}")
            continue
        if args.write and state == "stray":
            dst.unlink()
            print(f"  removed   {rel}  (not in the manifest)")
            continue
        label = {"missing": "MISSING  ", "differs": "DIFFERS  ", "stray": "STRAY    "}[state]
        print(f"  {label} {rel}")
        bad += 1

    if bad:
        print(f"{bad} shared cop{'y is' if bad == 1 else 'ies are'} out of date. "
              "Run: python scripts/sync_shared.py --write")
        return 1
    print("Shared copies are in sync.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
