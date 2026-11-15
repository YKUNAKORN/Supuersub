#!/usr/bin/env python3
"""Build the SharePoint import file for one create-list spec, then reopen and verify it.

    python3 scripts/build_list.py SPEC.list.json [--format xlsx|csv] [--out DIR]
                                  [--with OTHER.list.json ...] [--empty-table]
                                  [--csv-encoding utf-8-sig|utf-8] [--json]

--format xlsx (default) writes <ListName>.xlsx: a data sheet named after the list
holding one Excel table of the same name (header row, TableStyleMedium2, row stripes),
the header row frozen, typed cells (dates are dates with format yyyy-mm-dd, numbers are
numbers), and a Setup sheet: per column, the type to choose on the import screen, the
settings to apply after import, and notes; below it, the post-import notes. Needs
openpyxl (pip install openpyxl); without it, use --format csv.

--format csv writes <ListName>.csv (UTF-8 with a byte-order mark and CRLF line ends by
default; see references/import-behavior.md, row csv-encoding) and <ListName>.Setup.md
with the same setup guidance. Standard library only.

The spec is linted first (scripts/list_lint.py, with every *.list.json next to it, or
the --with specs, as lookup targets). Any lint error stops the build. A column whose
importType is skip is left out of the file and appears in the setup guidance only.
--empty-table writes the headers and no data rows: the type-probe case for the
empty-table evidence row, nothing else.

The same spec always gives the same bytes. Exit codes: 0 built and verified | 1 lint
errors or verification failed | 2 usage problem or a missing dependency.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import json
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent  # this skill's own folder

FIXED_TIME = datetime(2000, 1, 1, 0, 0, 0)
ZIP_TIME = (1980, 1, 1, 0, 0, 0)
TABLE_STYLE = "TableStyleMedium2"
SETUP_SHEET = "Setup"
SETUP_WIDTHS = (18, 34, 48, 52)
SETUP_FILL = "1F4E78"
DATE_FORMAT, DATETIME_FORMAT, CURRENCY_FORMAT = "yyyy-mm-dd", "yyyy-mm-dd hh:mm", "#,##0.00"

DEFAULT_HEADERS = ["Column", "Type to choose on the import screen",
                   "Settings after import (column settings)", "Notes"]
DEFAULT_NOTES_HEADING = "After import:"

IMPORT_LABELS = {
    "text": "Single line of text", "note": "Multiple lines of text", "number": "Number",
    "currency": "Currency", "datetime": "Date and time", "boolean": "Yes/No",
    "choice": "Choice", "person": "Person", "hyperlink": "Hyperlink",
    "skip": "(not in the file)",
}


def have_openpyxl() -> bool:
    try:
        import openpyxl  # type: ignore  # noqa: F401
        return True
    except ImportError:
        return False


def load_lint():
    spec = importlib.util.spec_from_file_location("list_lint", HERE / "list_lint.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------- setup text


def import_label(col: dict) -> str:
    label = IMPORT_LABELS[col["importType"]]
    if col["finalType"] == "date" and col["importType"] == "datetime":
        label += " (Date only, if offered)"
    return label


def post_import_steps(col: dict, types: dict) -> str:
    """The settings to apply after import, in the order the column settings need them."""
    ft, it = col["finalType"], col["importType"]
    target = types.get(ft, {}).get("label", ft)
    steps: list[str] = []
    if col["displayName"] != col["name"]:
        steps.append(f"Display name: {col['displayName']}")
    if it == "skip":
        steps.append(f"Not in the file: create by hand as {target}")
    elif ft == "date":
        steps.append("Date and time format: Date only")
    elif ft == "multichoice":
        steps.append("Change type to Choice, tick Allow multiple selections")
    elif ft in ("boolean", "person", "lookup") and it == "text":
        steps.append(f"Create a {target} column by hand, copy the values, delete this one")
    elif it != ft and not (ft == "datetime" and it == "datetime"):
        steps.append(f"Change type to {target}")
    if ft == "lookup" and isinstance(col.get("lookup"), dict):
        steps.append(f"Lookup: list {col['lookup']['list']}, column {col['lookup']['column']}")
    if col.get("choices"):
        steps.append("Choices: " + "; ".join(col["choices"]))
    if col.get("default") is not None:
        steps.append(f"Default value: {col['default']}")
    if col.get("unique"):
        steps.append("Indexed + Enforce unique values = Yes")
    elif col.get("indexed"):
        steps.append("Indexed")
    if col.get("required"):
        steps.append("Required")
    if col.get("postImport"):
        steps.append(col["postImport"])
    return "; ".join(steps)


def setup_rows(spec: dict, types: dict) -> list[list[str]]:
    return [[c["name"], import_label(c), post_import_steps(c, types), c.get("notes") or ""]
            for c in spec["columns"]]


def setup_text(spec: dict) -> tuple[list[str], str, list[str]]:
    setup = spec.get("setup") or {}
    headers = setup.get("headers") or DEFAULT_HEADERS
    heading = setup.get("notesHeading") or DEFAULT_NOTES_HEADING
    notes = setup.get("notes")
    if notes is None:
        notes = ["Rename each column to its display name; the header stays the internal name."]
        if any(c.get("unique") for c in spec["columns"]):
            notes.append("Set Indexed first, then Enforce unique values.")
        if spec.get("sampleRows"):
            notes.append("The rows are samples: delete them once the list exists.")
    return headers, heading, notes


# --------------------------------------------------------------------------- values


def file_columns(spec: dict) -> list[dict]:
    return [c for c in spec["columns"] if c["importType"] != "skip"]


def cell_value(value, col: dict):
    """The Python value written to the .xlsx cell."""
    if value is None or value == "" or value == []:
        return None
    ft = col["finalType"]
    if ft in ("date", "datetime"):
        return datetime.fromisoformat(value)
    if ft == "multichoice":
        return "; ".join(value)
    if ft == "boolean" and col["importType"] == "text":
        return "TRUE" if value else "FALSE"
    return value


def csv_value(value, col: dict) -> str:
    v = cell_value(value, col)
    if v is None:
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d") if col["finalType"] == "date" else v.strftime(
            "%Y-%m-%d %H:%M")
    if isinstance(v, float):
        return repr(v)
    return str(v)


def number_format(col: dict) -> str | None:
    return {"date": DATE_FORMAT, "datetime": DATETIME_FORMAT}.get(
        col["finalType"], CURRENCY_FORMAT if col["finalType"] == "currency" else None)


def column_width(col: dict, rows: list[dict]) -> float:
    if col["finalType"] == "date":
        return 15.0
    if col["finalType"] == "datetime":
        return 18.0
    longest = max([len(col["name"])] + [len(csv_value(r.get(col["name"]), col))
                                        for r in rows] or [0])
    return float(min(max(longest + 2, 12), 50))


def col_letter(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


# --------------------------------------------------------------------------- xlsx


def build_xlsx(spec: dict, types: dict, empty: bool) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.table import Table, TableStyleInfo

    cols = file_columns(spec)
    rows = [] if empty else spec["rows"]
    wb = Workbook()
    ws = wb.active
    ws.title = spec["name"]
    ws.append([c["name"] for c in cols])
    for row in rows:
        ws.append([cell_value(row.get(c["name"]), c) for c in cols])
    for j, col in enumerate(cols, start=1):
        fmt = number_format(col)
        if fmt:
            for i in range(2, len(rows) + 2):
                ws.cell(row=i, column=j).number_format = fmt
        ws.column_dimensions[col_letter(j)].width = column_width(col, rows)
    # An Excel table needs at least one row under the header; an empty table gets one
    # blank row.
    last_row = max(len(rows), 1) + 1
    table = Table(displayName=spec["name"], ref=f"A1:{col_letter(len(cols))}{last_row}")
    table.tableStyleInfo = TableStyleInfo(name=TABLE_STYLE, showFirstColumn=False,
                                          showLastColumn=False, showRowStripes=True,
                                          showColumnStripes=False)
    ws.add_table(table)
    ws.freeze_panes = "A2"

    su = wb.create_sheet(SETUP_SHEET)
    headers, heading, notes = setup_text(spec)
    su.append(headers)
    for r in setup_rows(spec, types):
        su.append(r)
    su.append([])
    su.append([heading])
    for note in notes:
        su.append([f"- {note}"])
    head_font = Font(bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor=SETUP_FILL)
    for cell in su[1]:
        cell.font, cell.fill = head_font, head_fill
    for row in su.iter_rows(min_row=2):
        for cell in row:
            if cell.value is not None:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
    for j, w in enumerate(SETUP_WIDTHS, start=1):
        su.column_dimensions[col_letter(j)].width = w

    wb.properties.creator = "supersub create-list"
    wb.properties.created = wb.properties.modified = FIXED_TIME
    buf = io.BytesIO()
    wb.save(buf)
    return deterministic_zip(buf.getvalue())


def deterministic_zip(data: bytes) -> bytes:
    """Rewrite the package with fixed timestamps so the same spec gives the same bytes."""
    stamp = FIXED_TIME.strftime("%Y-%m-%dT%H:%M:%SZ")
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as zin, \
            zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            body = zin.read(info.filename)
            if info.filename == "docProps/core.xml":
                body = re.sub(rb"(<dcterms:(?:created|modified)[^>]*>)[^<]*(<)",
                              rb"\g<1>" + stamp.encode() + rb"\g<2>", body)
            zi = zipfile.ZipInfo(info.filename, date_time=ZIP_TIME)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zout.writestr(zi, body)
    return out.getvalue()


def verify_xlsx(path: Path, spec: dict, empty: bool) -> list[str]:
    """Reopen the file and compare it with the spec. Returns the problems found."""
    from openpyxl import load_workbook

    problems: list[str] = []
    cols = file_columns(spec)
    wb = load_workbook(path)
    if wb.sheetnames != [spec["name"], SETUP_SHEET]:
        problems.append(f"sheets are {wb.sheetnames}")
        return problems
    ws = wb[spec["name"]]
    tables = list(ws.tables.values())
    if len(tables) != 1 or tables[0].name != spec["name"]:
        problems.append("the data sheet does not hold exactly one table named after the list")
    headers = [c.value for c in ws[1]]
    if headers != [c["name"] for c in cols]:
        problems.append(f"headers {headers} differ from the spec")
    if ws.freeze_panes != "A2":
        problems.append("the header row is not frozen")
    if not empty:
        for i, row in enumerate(spec["rows"], start=2):
            for j, col in enumerate(cols, start=1):
                cell = ws.cell(row=i, column=j)
                want = row.get(col["name"])
                if want is None or want == "":
                    continue
                ft = col["finalType"]
                if ft in ("date", "datetime") and not isinstance(cell.value, datetime):
                    problems.append(f"{cell.coordinate} is not a date")
                elif ft in ("number", "currency") and (
                        isinstance(cell.value, bool) or not isinstance(cell.value, (int, float))):
                    problems.append(f"{cell.coordinate} is not a number")
                if ft == "date" and cell.number_format != DATE_FORMAT:
                    problems.append(f"{cell.coordinate} has format {cell.number_format}")
    return problems[:20]


# --------------------------------------------------------------------------- csv


def build_csv(spec: dict, empty: bool, encoding: str) -> bytes:
    cols = file_columns(spec)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow([c["name"] for c in cols])
    for row in ([] if empty else spec["rows"]):
        writer.writerow([csv_value(row.get(c["name"]), c) for c in cols])
    return buf.getvalue().encode(encoding)


def build_setup_md(spec: dict, types: dict, encoding: str) -> bytes:
    headers, heading, notes = setup_text(spec)

    def cell(s: str) -> str:
        return str(s).replace("|", "\\|").replace("\n", " ")

    bom = "with" if encoding == "utf-8-sig" else "without"
    lines = [f"# {spec['displayName']} ({spec['name']})", "",
             spec.get("description") or "", "",
             f"Import file: `{spec['name']}.csv`, UTF-8 {bom} a byte-order mark. "
             "Choose **From CSV**.", "",
             "| " + " | ".join(cell(h) for h in headers) + " |",
             "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(cell(v) for v in r) + " |" for r in setup_rows(spec, types)]
    lines += ["", f"**{heading}**", ""] + [f"- {n}" for n in notes] + [""]
    return "\n".join(lines).encode("utf-8")


def verify_csv(path: Path, spec: dict, empty: bool, encoding: str) -> list[str]:
    raw = path.read_bytes()
    problems: list[str] = []
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    if has_bom != (encoding == "utf-8-sig"):
        problems.append("byte-order mark does not match --csv-encoding")
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline="")))
    if not rows or rows[0] != [c["name"] for c in file_columns(spec)]:
        problems.append("the header row differs from the spec")
    want = 1 + (0 if empty else len(spec["rows"]))
    if len(rows) != want:
        problems.append(f"{len(rows)} lines, expected {want}")
    return problems


# --------------------------------------------------------------------------- main


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="build_list.py",
                                     description="Build a SharePoint list import file.")
    parser.add_argument("spec", type=Path, help="<ListName>.list.json")
    parser.add_argument("--format", choices=("xlsx", "csv"), default="xlsx")
    parser.add_argument("--out", type=Path, help="output folder (default: the spec's)")
    parser.add_argument("--with", dest="others", type=Path, nargs="*", default=None,
                        help="other specs of the design, as lookup targets "
                             "(default: every *.list.json next to the spec)")
    parser.add_argument("--empty-table", action="store_true",
                        help="headers only, no data rows (type probe)")
    parser.add_argument("--csv-encoding", choices=("utf-8-sig", "utf-8"),
                        default="utf-8-sig")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover
        pass

    if not args.spec.is_file():
        print(f"ERROR: no such spec: {args.spec}", file=sys.stderr)
        return 2
    if args.format == "xlsx" and not have_openpyxl():
        print("ERROR: --format xlsx needs openpyxl, which is not installed.\n"
              "  Install it:  pip install openpyxl\n"
              "  Or build a CSV instead:  --format csv", file=sys.stderr)
        return 2

    lint = load_lint()
    others = args.others
    if others is None:
        others = [p for p in sorted(args.spec.resolve().parent.glob("*.list.json"))
                  if p.resolve() != args.spec.resolve()]
    report = lint.lint_files([args.spec, *others], args.format, args.empty_table)
    mine = args.spec.as_posix()
    errors = [f for f in report["findings"] if f["severity"] == "error"]
    if errors:
        print(lint.render(report), file=sys.stderr)
        print("Not built: fix the lint errors first.", file=sys.stderr)
        return 1

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    types = lint.load_types()
    out_dir = args.out or args.spec.resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    if args.format == "xlsx":
        path = out_dir / f"{spec['name']}.xlsx"
        path.write_bytes(build_xlsx(spec, types, args.empty_table))
        written.append(path)
        problems = verify_xlsx(path, spec, args.empty_table)
    else:
        path = out_dir / f"{spec['name']}.csv"
        path.write_bytes(build_csv(spec, args.empty_table, args.csv_encoding))
        md = out_dir / f"{spec['name']}.Setup.md"
        md.write_bytes(build_setup_md(spec, types, args.csv_encoding))
        written += [path, md]
        problems = verify_csv(path, spec, args.empty_table, args.csv_encoding)

    warnings = [f for f in report["findings"]
                if f["severity"] == "warning" and f["file"] == mine]
    result = {"written": [p.as_posix() for p in written], "verified": not problems,
              "problems": problems, "format": args.format,
              "columns_in_file": [c["name"] for c in file_columns(spec)],
              "columns_by_hand": [c["name"] for c in spec["columns"]
                                  if c["importType"] == "skip"],
              "rows": 0 if args.empty_table else len(spec["rows"]),
              "sample_rows": bool(spec.get("sampleRows")),
              "warnings": warnings}
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        for p in written:
            print(f"wrote {p.as_posix()}")
        print(f"columns in the file: {', '.join(result['columns_in_file'])}")
        if result["columns_by_hand"]:
            print(f"create by hand after import: {', '.join(result['columns_by_hand'])}")
        print(f"rows: {result['rows']}" + (" (samples: delete after import)"
                                           if result["sample_rows"] else ""))
        for w in warnings:
            print(f"  [WARNING] {w['check']}: {w['message']}")
        print("VERIFIED: reopened, the table, headers and typed cells match the spec"
              if not problems else "NOT VERIFIED:\n  " + "\n  ".join(problems))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
