#!/usr/bin/env python3
"""Privacy guard for a public repository.

Two checks over every tracked file (plus untracked files that are not ignored, so a
new file is covered before its first commit):

1. Private terms. When a local, untracked ``.private-terms.txt`` exists at the repo
   root (one term per line, ``#`` comments allowed), every file's content and every
   file name is matched against it, case-insensitively, as substrings. A hit prints
   the file and line but never the term. A hit in a file *name* prints the name's
   position in the file list instead of the name, because the name holds the term.
   Without the file the check is skipped and passes: CI never has it.
2. Shape check, independent of that file. Fails on an e-mail address whose domain is
   not example.com, example.org or contoso.*; a ``*.sharepoint.com`` or
   ``*.onmicrosoft.com`` host whose tenant is not ``contoso``; and an absolute home
   path.

Usage: python scripts/privacy_check.py        (exit 0 clean, 1 on a hit)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TERMS_FILE = ".private-terms.txt"
SKIP_MESSAGE = f"skip (no {TERMS_FILE})"

# Patterns are assembled from pieces so this file does not match its own rules.
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})")
_EMAIL_OK = re.compile(r"(?:^|\.)(?:example\.(?:com|org)|contoso\.[a-z.]+)$", re.I)
_HOST = re.compile(r"([A-Za-z0-9-]+)\.(?:share" + r"point|onmicro" + r"soft)\.com", re.I)
_HOST_OK = {"contoso", "contoso-my"}
_HOME = re.compile(
    r"(?<![\w.:/-])/(?:Us" + r"ers|ho" + r"me)/[\w.-]"
    r"|[A-Za-z]:\\{1,2}Us" + r"ers\\{1,2}[\w.-]")


def candidate_files(root: Path = ROOT) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root, capture_output=True, check=True).stdout.decode("utf-8", "replace")
    names = sorted({n for n in out.split("\0") if n})
    return [n for n in names if n != TERMS_FILE and (root / n).is_file()]


def load_terms(root: Path = ROOT) -> list[str] | None:
    path = root / TERMS_FILE
    if not path.is_file():
        return None
    terms = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            terms.append(line.lower())
    return terms


def _text(path: Path) -> str | None:
    data = path.read_bytes()
    if b"\0" in data:
        return None
    return data.decode("utf-8", "replace")


def scan_terms(root: Path, files: list[str], terms: list[str]) -> list[str]:
    hits = []
    for i, name in enumerate(files, 1):
        name_hit = any(t in name.lower() for t in terms)
        shown = f"<file name #{i} in the file list>" if name_hit else name
        if name_hit:
            hits.append(f"{shown}: a private term is in the file name")
        text = _text(root / name)
        if text is None:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            low = line.lower()
            if any(t in low for t in terms):
                hits.append(f"{shown}:{n}: a private term is on this line")
    return hits


def scan_shapes(root: Path, files: list[str]) -> list[str]:
    hits = []
    for name in files:
        text = _text(root / name)
        if text is None:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for m in _EMAIL.finditer(line):
                if not _EMAIL_OK.search(m.group(1)):
                    hits.append(f"{name}:{n}: e-mail address outside example.com, "
                                "example.org and contoso.*")
            for m in _HOST.finditer(line):
                if m.group(1).lower() not in _HOST_OK:
                    hits.append(f"{name}:{n}: tenant host other than contoso")
            if _HOME.search(line):
                hits.append(f"{name}:{n}: absolute home path")
    return hits


def run(root: Path = ROOT) -> tuple[list[str], list[str]]:
    """Return (private-term hits, shape hits); term hits are empty without the file."""
    files = candidate_files(root)
    terms = load_terms(root)
    term_hits = [] if terms is None else scan_terms(root, files, terms)
    return term_hits, scan_shapes(root, files)


def main() -> int:
    root = ROOT
    terms = load_terms(root)
    print(SKIP_MESSAGE if terms is None else f"private terms: {len(terms)} loaded")
    term_hits, shape_hits = run(root)
    for h in term_hits + shape_hits:
        print("  HIT", h)
    return 1 if term_hits or shape_hits else 0


if __name__ == "__main__":
    sys.exit(main())
