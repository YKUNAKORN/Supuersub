#!/usr/bin/env python3
"""Offline checker for create-list specs (<ListName>.list.json), ending in a verdict.

    python3 scripts/list_lint.py SPEC.list.json [MORE.list.json ...]
                                 [--format xlsx|csv] [--empty-table]
                                 [--evidence PATH] [--json] [--strict] [--quiet]

Pass every list of one design together: a lookup's target must be among the specs
passed. A folder argument means every *.list.json in it. The type table comes from
references/column-types.md and the evidence levels from references/import-behavior.md,
both inside this skill. Each finding has a stable check id; tests assert on ids, never on
wording.

ERRORS (the spec breaks the rules; fix before building)
  spec-invalid        not JSON, or breaks assets/list.schema.json
  name-invalid        a list or column name that is not ASCII PascalCase, is too long
                      (list 31, column 32), or (list) reads as an Excel cell reference
  name-duplicate      two columns of one list, or two lists, whose names differ only by
                      case or not at all
  name-reserved       a column named like a built-in column (ID, Created, Modified,
                      Author, Editor, Attachments)
  import-type         an importType the type table does not allow for the finalType
  choices-missing     a choice or multichoice column with fewer than two choices
  lookup-target       a lookup column without a target, a target list or column that is
                      not among the specs passed, a lookup on a non-lookup column, or a
                      cycle of lookups
  unique-not-indexed  unique is set and indexed is not (the index comes first)
  unique-values       a unique column with the same value in two rows
  row-value           a row value that does not parse as its column's type (dates are
                      "YYYY-MM-DD", numbers are JSON numbers, choices come from choices)
  row-unknown-column  a row key that is not a column name
  row-count           more than 5,000 rows (the import limit)
  rows-too-few        fewer than three rows; types are proposed from the data
                      (skipped with --empty-table, the type-probe case)

WARNINGS (review; fix, or say why it stands)
  unverified-behavior the spec relies on an import behaviour whose evidence row is not
                      doc or import-tested; the message names the row
  title-column        a column named Title (whether import maps Title is unverified)
  column-sparse       an imported column with fewer than three values in the rows
  required-empty      a required column left empty in a row
  personal-data       sample rows holding an e-mail address outside example.com/.org/.net

Exit codes: 0 no errors | 1 any error | 2 warnings (or unproven) with --strict, or a
usage problem. Standard library only; jsonschema is optional (without it the schema
layer is reduced and the verdict is UNPROVEN: pip install jsonschema).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent  # this skill's own folder
SCHEMA_PATH = SKILL_DIR / "assets" / "list.schema.json"
TYPES_PATH = SKILL_DIR / "references" / "column-types.md"
DEFAULT_EVIDENCE = SKILL_DIR / "references" / "import-behavior.md"

ERROR, WARNING = "error", "warning"
TRUSTED_LEVELS = {"doc", "import-tested"}
LEVELS = {"import-tested", "export", "doc", "unverified"}
NAME_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
CELL_REF_RE = re.compile(r"^(?:[A-Za-z]{1,3}[0-9]+|R[0-9]*C[0-9]*|R|C)$", re.I)
RESERVED = ("ID", "Created", "Modified", "Author", "Editor", "Attachments")
LIST_NAME_MAX, COLUMN_NAME_MAX = 31, 32
ROW_LIMIT, ROWS_MIN, CHOICES_MIN, TEXT_MAX = 5000, 3, 2, 255
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
SAFE_EMAIL_DOMAINS = re.compile(r"(?:^|\.)example\.(?:com|org|net)$|\.(?:example|test|invalid)$",
                                re.I)
REQUIRED_KEYS = ("version", "name", "displayName", "description", "columns", "rows",
                 "sampleRows")
COLUMN_KEYS = ("name", "displayName", "importType", "finalType", "required", "unique",
               "indexed", "default", "choices", "lookup", "notes")


# --------------------------------------------------------------------------- references


def _table_rows(text: str, heading: str) -> list[list[str]]:
    """Cells of every body row of the first Markdown table under `## heading`."""
    m = re.search(rf"^## {re.escape(heading)}\s*$", text, re.M)
    if not m:
        return []
    rows: list[list[str]] = []
    started = False
    for line in text[m.end():].splitlines():
        if line.startswith("## "):
            break
        if line.startswith("|"):
            started = True
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue
            rows.append(cells)
        elif started and line.strip():
            break
    return rows[1:]  # drop the header row


def _code(cell: str) -> list[str]:
    return re.findall(r"`([^`]+)`", cell)


def load_types(path: Path = TYPES_PATH) -> dict[str, dict]:
    """finalType -> {"label": SharePoint type, "imports": [importType, ...]}."""
    types: dict[str, dict] = {}
    for cells in _table_rows(path.read_text(encoding="utf-8"), "Type table"):
        if len(cells) < 4 or not _code(cells[0]):
            continue
        types[_code(cells[0])[0]] = {"label": cells[1], "imports": _code(cells[2])}
    return types


def load_evidence(path: Path = DEFAULT_EVIDENCE) -> dict[str, dict]:
    """Behaviour id -> {"level", "behaviour", "source", "date"}."""
    rows: dict[str, dict] = {}
    for cells in _table_rows(path.read_text(encoding="utf-8"), "Evidence table"):
        if len(cells) < 5 or not _code(cells[0]):
            continue
        rows[_code(cells[0])[0]] = {"behaviour": cells[1].replace("**", "").replace("`", ""),
                                    "level": cells[2].strip("` "),
                                    "source": cells[3], "date": cells[4]}
    return rows


# --------------------------------------------------------------------------- findings


class Finding:
    __slots__ = ("check", "severity", "message", "file", "where", "detail")

    def __init__(self, check, severity, message, file=None, where=None, detail=None):
        self.check, self.severity, self.message = check, severity, message
        self.file, self.where, self.detail = file, where, detail

    def as_dict(self):
        return {"check": self.check, "severity": self.severity, "message": self.message,
                "file": self.file, "where": self.where, "detail": self.detail}


# --------------------------------------------------------------------------- values


def parse_value(value, final_type: str, choices) -> tuple[bool, str]:
    """(ok, why) for one non-empty row value against its column's finalType."""
    if final_type in ("text", "note", "person"):
        if not isinstance(value, str):
            return False, "expected a string"
        if final_type == "text" and len(value) > TEXT_MAX:
            return False, f"longer than {TEXT_MAX} characters (use note)"
        return True, ""
    if final_type in ("number", "currency"):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False, "expected a JSON number, not text"
        return True, ""
    if final_type == "date":
        if not isinstance(value, str) or not DATE_RE.match(value):
            return False, 'expected "YYYY-MM-DD"'
        try:
            date.fromisoformat(value)
        except ValueError:
            return False, "not a calendar date"
        return True, ""
    if final_type == "datetime":
        if not isinstance(value, str) or not DATETIME_RE.match(value):
            return False, 'expected "YYYY-MM-DDTHH:MM"'
        try:
            datetime.fromisoformat(value)
        except ValueError:
            return False, "not a calendar date and time"
        return True, ""
    if final_type == "boolean":
        return (isinstance(value, bool), "expected true or false")
    if final_type == "choice":
        if not isinstance(value, str) or value not in (choices or []):
            return False, "not one of the column's choices"
        return True, ""
    if final_type == "multichoice":
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            return False, "expected a list of choices"
        bad = [v for v in value if v not in (choices or [])]
        return (not bad, f"not among the choices: {bad}")
    if final_type == "hyperlink":
        ok = isinstance(value, str) and re.match(r"^https?://\S+$", value) is not None
        return ok, "expected a URL starting https://"
    if final_type == "lookup":
        return (isinstance(value, (str, int, float)) and not isinstance(value, bool),
                "expected a value of the target column")
    return False, f"unknown finalType {final_type!r}"


def is_empty(value) -> bool:
    return value is None or value == "" or value == []


# --------------------------------------------------------------------------- linting


class Linter:
    def __init__(self, fmt="xlsx", allow_empty=False, evidence_path=DEFAULT_EVIDENCE,
                 types_path=TYPES_PATH):
        self.fmt, self.allow_empty = fmt, allow_empty
        self.types = load_types(types_path)
        self.evidence = load_evidence(evidence_path)
        self.findings: list[Finding] = []
        self.degraded = ""
        self.validator = None
        try:
            import jsonschema  # type: ignore
            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            self.validator = jsonschema.Draft202012Validator(schema)
        except ImportError:
            self.degraded = ("jsonschema is not installed, so the schema layer ran a reduced "
                             "check. Install it with: pip install jsonschema")

    def add(self, check, severity, message, file=None, where=None, detail=None):
        self.findings.append(Finding(check, severity, message, file, where, detail))

    # -- structure ---------------------------------------------------------------

    def structurally_ok(self, spec, file) -> bool:
        if not isinstance(spec, dict):
            self.add("spec-invalid", ERROR, "the spec is not a JSON object", file)
            return False
        ok = True
        if self.validator is not None:
            for err in sorted(self.validator.iter_errors(spec), key=lambda e: list(e.path)):
                path = "/".join(str(p) for p in err.absolute_path) or "(root)"
                self.add("spec-invalid", ERROR, f"schema: {err.message}", file, path)
                ok = False
        else:
            missing = [k for k in REQUIRED_KEYS if k not in spec]
            if missing:
                self.add("spec-invalid", ERROR, f"missing keys: {missing}", file)
                ok = False
            for i, col in enumerate(spec.get("columns") or []):
                if not isinstance(col, dict) or any(k not in col for k in COLUMN_KEYS):
                    self.add("spec-invalid", ERROR, "a column misses required keys", file,
                             f"columns/{i}", f"needs: {list(COLUMN_KEYS)}")
                    ok = False
        # Deeper checks need this much shape, whatever the schema layer said, and
        # known types so the value checks cannot crash.
        cols, rows = spec.get("columns"), spec.get("rows")
        shaped = (isinstance(spec.get("name"), str)
                  and isinstance(cols, list) and isinstance(rows, list)
                  and all(isinstance(c, dict) and isinstance(c.get("name"), str)
                          for c in cols)
                  and all(isinstance(r, dict) for r in rows))
        return shaped and (ok or all(c.get("finalType") in self.types for c in cols))

    # -- one spec ----------------------------------------------------------------

    def lint_spec(self, spec: dict, file: str, all_specs: dict[str, dict]):
        name = spec["name"]
        if not NAME_RE.match(name) or len(name) > LIST_NAME_MAX or CELL_REF_RE.match(name):
            self.add("name-invalid", ERROR,
                     f"list name {name!r} must be ASCII PascalCase, at most "
                     f"{LIST_NAME_MAX} characters, and not read as a cell reference",
                     file, "name")
        cols = spec["columns"]
        by_name: dict[str, dict] = {}
        seen: dict[str, str] = {}
        for i, col in enumerate(cols):
            cname = col["name"]
            where = f"columns/{i} ({cname})"
            if not NAME_RE.match(cname) or len(cname) > COLUMN_NAME_MAX:
                self.add("name-invalid", ERROR,
                         f"column name {cname!r} must be ASCII PascalCase, at most "
                         f"{COLUMN_NAME_MAX} characters", file, where)
            low = cname.lower()
            if low in seen:
                self.add("name-duplicate", ERROR,
                         f"column {cname!r} collides with {seen[low]!r} (case is ignored)",
                         file, where)
            seen.setdefault(low, cname)
            by_name.setdefault(cname, col)
            if low in {r.lower() for r in RESERVED}:
                self.add("name-reserved", ERROR,
                         f"{cname!r} is the name of a built-in column; choose another",
                         file, where)
            if low == "title":
                self.add("title-column", WARNING,
                         "a column named Title: whether an imported list maps Title is "
                         "unverified (evidence row title-mapping)", file, where)
            ft, it = col.get("finalType"), col.get("importType")
            tinfo = self.types.get(ft)
            if tinfo is None:
                self.add("import-type", ERROR, f"finalType {ft!r} is not in the type table",
                         file, where)
            elif it not in tinfo["imports"]:
                self.add("import-type", ERROR,
                         f"importType {it!r} is not allowed for finalType {ft!r}",
                         file, where, f"allowed: {tinfo['imports']}")
            if ft in ("choice", "multichoice"):
                ch = col.get("choices")
                if not isinstance(ch, list) or len([c for c in ch if c]) < CHOICES_MIN:
                    self.add("choices-missing", ERROR,
                             f"a {ft} column needs at least {CHOICES_MIN} choices", file, where)
            if col.get("unique") and not col.get("indexed"):
                self.add("unique-not-indexed", ERROR,
                         "unique is set but indexed is not: the column is indexed first, "
                         "then made unique", file, where)
            self.check_lookup(col, file, where, all_specs)
        self.check_rows(spec, by_name, file)
        self.check_behaviour(spec, file)

    def check_lookup(self, col, file, where, all_specs):
        lk = col.get("lookup")
        if col.get("finalType") != "lookup":
            if lk:
                self.add("lookup-target", ERROR,
                         "lookup is set on a column whose finalType is not lookup", file, where)
            return
        if not isinstance(lk, dict) or not lk.get("list") or not lk.get("column"):
            self.add("lookup-target", ERROR, "a lookup column needs lookup.list and "
                     "lookup.column", file, where)
            return
        target = all_specs.get(lk["list"])
        if target is None:
            self.add("lookup-target", ERROR,
                     f"target list {lk['list']!r} is not among the specs passed", file, where,
                     "pass every list of the design together")
            return
        names = {c.get("name") for c in target.get("columns") or [] if isinstance(c, dict)}
        if lk["column"] not in names:
            self.add("lookup-target", ERROR,
                     f"target column {lk['column']!r} is not a column of {lk['list']!r}",
                     file, where)

    def check_rows(self, spec, by_name, file):
        rows = spec["rows"]
        n = len(rows)
        if n > ROW_LIMIT:
            self.add("row-count", ERROR, f"{n} rows; the import takes at most {ROW_LIMIT}",
                     file, "rows")
        if n < ROWS_MIN and not self.allow_empty:
            self.add("rows-too-few", ERROR,
                     f"{n} row(s); give at least {ROWS_MIN} representative rows, because "
                     "column types are proposed from the data", file, "rows")
        values: dict[str, list] = {c: [] for c in by_name}
        for r, row in enumerate(rows):
            for key, value in row.items():
                col = by_name.get(key)
                if col is None:
                    self.add("row-unknown-column", ERROR, f"row key {key!r} is not a column",
                             file, f"rows/{r}")
                    continue
                if is_empty(value):
                    continue
                values[key].append(value)
                if col.get("finalType") not in self.types:
                    continue
                ok, why = parse_value(value, col["finalType"], col.get("choices"))
                if not ok:
                    self.add("row-value", ERROR, f"{key} = {value!r}: {why}", file,
                             f"rows/{r}")
                if spec.get("sampleRows") and isinstance(value, str):
                    for dom in EMAIL_RE.findall(value):
                        if not SAFE_EMAIL_DOMAINS.search(dom):
                            self.add("personal-data", WARNING,
                                     f"{key}: sample rows hold an address at {dom}; use "
                                     "example.com", file, f"rows/{r}")
            for cname, col in by_name.items():
                if col.get("required") and is_empty(row.get(cname)):
                    self.add("required-empty", WARNING,
                             f"{cname} is required but empty in this row", file, f"rows/{r}")
        if n >= ROWS_MIN:
            for cname, col in by_name.items():
                if col.get("importType") != "skip" and len(values[cname]) < ROWS_MIN:
                    self.add("column-sparse", WARNING,
                             f"{cname} has {len(values[cname])} value(s); the importer "
                             f"proposes a type from the data, so give it at least {ROWS_MIN}",
                             file, f"columns ({cname})")
        for cname, col in by_name.items():
            if col.get("unique"):
                seen = set()
                for v in values[cname]:
                    key = json.dumps(v, sort_keys=True, ensure_ascii=False)
                    if key in seen:
                        self.add("unique-values", ERROR,
                                 f"{cname} is unique but {v!r} appears twice", file, "rows")
                        break
                    seen.add(key)

    def check_behaviour(self, spec, file):
        uses: dict[str, list[str]] = {}
        title_free = True
        for col in spec["columns"]:
            it = col.get("importType")
            if it and it != "skip":
                uses.setdefault(f"offer-{it}", []).append(col["name"])
            if it == "choice":
                uses.setdefault("choice-from-data", []).append(col["name"])
            if str(col.get("name", "")).lower() == "title":
                title_free = False
        if title_free:
            uses["title-mapping"] = []
        if self.allow_empty:
            uses["empty-table"] = []
        if self.fmt == "csv":
            uses["csv-encoding"] = []
            typed = [c["name"] for c in spec["columns"] if c.get("importType") in
                     ("number", "currency", "datetime", "boolean")]
            if typed:
                uses["csv-values"] = typed
        for row_id in sorted(uses):
            ev = self.evidence.get(row_id)
            level = ev["level"] if ev else "missing"
            if level in TRUSTED_LEVELS:
                continue
            cols = uses[row_id]
            what = ev["behaviour"] if ev else "no row in the evidence table"
            self.add("unverified-behavior", WARNING,
                     f"relies on {row_id} ({level}): {what}", file,
                     ", ".join(cols) if cols else None,
                     "tell the user what was assumed and what to check on the import screen")

    # -- all specs ---------------------------------------------------------------

    def creation_order(self, specs: dict[str, dict], files: dict[str, str]) -> list[str]:
        """Lookup targets first. A cycle is a lookup-target error."""
        deps = {n: sorted({c["lookup"]["list"] for c in s["columns"]
                           if c.get("finalType") == "lookup" and isinstance(c.get("lookup"), dict)
                           and c["lookup"].get("list") in specs and c["lookup"]["list"] != n})
                for n, s in specs.items()}
        order: list[str] = []
        state: dict[str, int] = {}

        def visit(n, trail):
            if state.get(n) == 2:
                return
            if state.get(n) == 1:
                cycle = trail[trail.index(n):] + [n]
                self.add("lookup-target", ERROR, "lookups form a cycle: "
                         + " -> ".join(cycle), files.get(n))
                return
            state[n] = 1
            for d in deps[n]:
                visit(d, trail + [n])
            state[n] = 2
            order.append(n)

        for n in sorted(specs):
            visit(n, [])
        return order


def collect(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_dir():
            out += sorted(p.glob("*.list.json"))
        else:
            out.append(p)
    return out


def lint_files(paths: list[Path], fmt="xlsx", allow_empty=False,
               evidence_path: Path = DEFAULT_EVIDENCE) -> dict:
    linter = Linter(fmt, allow_empty, evidence_path)
    loaded: list[tuple[str, dict]] = []
    for path in paths:
        file = path.as_posix()
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
            linter.add("spec-invalid", ERROR, f"not readable JSON: {e}", file)
            continue
        if linter.structurally_ok(spec, file):
            loaded.append((file, spec))
    specs: dict[str, dict] = {}
    files: dict[str, str] = {}
    lowered: dict[str, str] = {}
    for file, spec in loaded:
        low = spec["name"].lower()
        if low in lowered:
            linter.add("name-duplicate", ERROR,
                       f"list {spec['name']!r} collides with {lowered[low]!r}", file, "name")
            continue
        lowered[low] = spec["name"]
        specs[spec["name"]] = spec
        files[spec["name"]] = file
    for n, spec in specs.items():
        linter.lint_spec(spec, files[n], specs)
    order = linter.creation_order(specs, files)
    return build_report(linter, paths, specs, order, fmt)


def build_report(linter: Linter, paths, specs, order, fmt) -> dict:
    findings = linter.findings
    errors = sum(f.severity == ERROR for f in findings)
    warnings = sum(f.severity == WARNING for f in findings)
    unverified = sum(f.check == "unverified-behavior" for f in findings)
    if errors:
        code, verdict = "will_fail", f"VERDICT: WILL FAIL — {errors} error(s) to fix"
    elif linter.degraded:
        suffix = f", {warnings} warning(s)" if warnings else ""
        code, verdict = "unproven", f"VERDICT: UNPROVEN — schema layer reduced{suffix}"
    elif warnings:
        code = "unverified"
        verdict = (f"VERDICT: USABLE, WITH {warnings} ITEM(S) TO CHECK "
                   f"({unverified} on unverified import behaviour)")
    else:
        code, verdict = "safe", "VERDICT: READY TO BUILD"
    findings.sort(key=lambda f: (0 if f.severity == ERROR else 1, f.file or "",
                                 f.check, f.where or ""))
    lists = [{"name": n, "displayName": s.get("displayName"),
              "columns": len(s["columns"]), "rows": len(s["rows"])}
             for n, s in sorted(specs.items())]
    return {"paths": [p.as_posix() for p in paths], "format": fmt, "lists": lists,
            "creation_order": order, "findings": [f.as_dict() for f in findings],
            "errors": errors, "warnings": warnings, "verdict": verdict,
            "verdict_code": code, "degraded": linter.degraded}


def render(report: dict, quiet=False) -> str:
    out: list[str] = []
    if not quiet:
        names = ", ".join(f"{l['name']} ({l['columns']} columns, {l['rows']} rows)"
                          for l in report["lists"]) or "no list read"
        out += ["=" * 72, f"{names}  (format: {report['format']})", "=" * 72]
        if report["creation_order"]:
            out += ["  Create in this order: " + " -> ".join(report["creation_order"]), ""]
        if report["degraded"]:
            out += [f"  NOTE: {report['degraded']}", ""]
        for sev, title in ((ERROR, "Errors"), (WARNING, "Warnings")):
            group = [f for f in report["findings"] if f["severity"] == sev]
            if not group:
                continue
            out += [title, "-" * 72]
            for f in group:
                out.append(f"  [{sev.upper()}] {f['check']}")
                out.append(f"    {f['message']}")
                where = " ".join(x for x in (f["file"], f["where"] and f"at {f['where']}")
                                 if x)
                if where:
                    out.append(f"    in: {where}")
                if f["detail"]:
                    out.append(f"    {f['detail']}")
                out.append("")
        if not report["findings"]:
            out += ["  No findings.", ""]
    out.append(report["verdict"])
    return "\n".join(out)


def exit_code(report: dict, strict: bool) -> int:
    if report["errors"]:
        return 1
    if strict and (report["warnings"] or report["degraded"]):
        return 2
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="list_lint.py",
        description="Check create-list specs offline and end with a verdict.")
    parser.add_argument("specs", nargs="+", type=Path,
                        help="<ListName>.list.json files, or a folder of them")
    parser.add_argument("--format", choices=("xlsx", "csv"), default="xlsx",
                        help="the import file that will be built (default xlsx)")
    parser.add_argument("--empty-table", action="store_true",
                        help="the file will hold headers only (type-probe case)")
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE,
                        help="evidence table (default: references/import-behavior.md)")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--strict", action="store_true",
                        help="exit 2 when there are warnings but no errors")
    parser.add_argument("--quiet", action="store_true", help="print only the verdict")
    args = parser.parse_args(argv)

    if not args.json:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    paths = collect(args.specs)
    missing = [p for p in paths if not p.is_file()]
    if missing or not paths:
        print(f"ERROR: no such spec: {', '.join(map(str, missing)) or args.specs}",
              file=sys.stderr)
        return 2
    if not args.evidence.is_file():
        print(f"ERROR: no such evidence file: {args.evidence}", file=sys.stderr)
        return 2

    report = lint_files(paths, args.format, args.empty_table, args.evidence)
    code = exit_code(report, args.strict)
    if args.json:
        print(json.dumps({"version": 1, "report": report, "exit_code": code},
                         indent=2, ensure_ascii=False))
    else:
        print(render(report, quiet=args.quiet))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
