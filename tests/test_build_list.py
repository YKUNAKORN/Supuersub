#!/usr/bin/env python3
"""Tests for skills/create-list/scripts/build_list.py.

The central test builds assets/example/Holidays.list.json and compares the workbook
structurally with tests/fixtures/lists/9AM_Holidays.xlsx, the owner's reference: sheet
names, table name, range, style and columns, the frozen pane, the Python type and number
format of the date cells, and the Setup header row. Bytes are never compared with the
reference (a different writer produced it); they are compared between two builds of the
same spec, which must be identical.

The .xlsx tests need openpyxl and skip with a message when it is absent
(pip install openpyxl). The CSV tests use the standard library only.

Run:  python -m unittest discover tests
"""

from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "create-list"
BUILD = SKILL / "scripts" / "build_list.py"
EXAMPLE = SKILL / "assets" / "example" / "Holidays.list.json"
PROBE = SKILL / "assets" / "type-probe.list.json"
REFERENCE = Path(__file__).resolve().parent / "fixtures" / "lists" / "9AM_Holidays.xlsx"
LINT_BASE = Path(__file__).resolve().parent / "fixtures" / "lists" / "lint" / "base"

try:
    import openpyxl
    HAVE_OPENPYXL = True
except ImportError:  # pragma: no cover
    HAVE_OPENPYXL = False
NEEDS_OPENPYXL = unittest.skipUnless(
    HAVE_OPENPYXL, "openpyxl is not installed: pip install openpyxl (xlsx tests skipped)")


def build(spec: Path, out: Path, *args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(BUILD), str(spec), "--out", str(out), *args],
                          capture_output=True, text=True, encoding="utf-8", cwd=str(cwd))


def shape(path: Path) -> dict:
    """What the structural comparison looks at."""
    wb = openpyxl.load_workbook(path)
    data = wb.worksheets[0]
    (table,) = data.tables.values()
    date_cells = [data.cell(row=r, column=1) for r in range(2, data.max_row + 1)]
    return {
        "sheets": wb.sheetnames,
        "table": (table.name, table.ref, table.tableStyleInfo.name,
                  bool(table.tableStyleInfo.showRowStripes),
                  [c.name for c in table.tableColumns]),
        "freeze": data.freeze_panes,
        "date_types": {type(c.value) for c in date_cells},
        "date_formats": {c.number_format for c in date_cells},
        "setup_header": [c.value for c in wb["Setup"][1]],
    }


@NEEDS_OPENPYXL
class ReferenceTests(unittest.TestCase):
    def test_example_matches_the_reference_structurally(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = build(EXAMPLE, Path(tmp))
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("VERIFIED", proc.stdout)
            got = shape(Path(tmp) / "Holidays.xlsx")
        want = shape(REFERENCE)
        self.assertEqual(want["sheets"], ["Holidays", "Setup"])
        self.assertEqual(want["table"][:3], ("Holidays", "A1:B22", "TableStyleMedium2"))
        self.assertEqual(want["date_types"], {datetime})
        self.assertEqual(want["date_formats"], {"yyyy-mm-dd"})
        for key in want:
            self.assertEqual(got[key], want[key], key)

    def test_values_match_the_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            build(EXAMPLE, Path(tmp))
            got = list(openpyxl.load_workbook(Path(tmp) / "Holidays.xlsx")
                       ["Holidays"].iter_rows(values_only=True))
        want = list(openpyxl.load_workbook(REFERENCE)["Holidays"].iter_rows(values_only=True))
        self.assertEqual(got, want)

    def test_setup_sheet_styles(self):
        with tempfile.TemporaryDirectory() as tmp:
            build(EXAMPLE, Path(tmp))
            su = openpyxl.load_workbook(Path(tmp) / "Holidays.xlsx")["Setup"]
            self.assertTrue(all(c.font.bold for c in su[1]))
            self.assertTrue(su["A2"].alignment.wrap_text)
            self.assertFalse(su.tables)
            self.assertIn("Enforce unique values", su["C2"].value)
            self.assertIn("Required", su["C2"].value)


@NEEDS_OPENPYXL
class XlsxTests(unittest.TestCase):
    def test_same_spec_same_bytes(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            build(EXAMPLE, Path(a))
            build(EXAMPLE, Path(b))
            self.assertEqual((Path(a) / "Holidays.xlsx").read_bytes(),
                             (Path(b) / "Holidays.xlsx").read_bytes())

    def test_skip_columns_stay_out_and_types_are_real(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = build(LINT_BASE / "Requests.list.json", Path(tmp), "--json")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads(proc.stdout)
            self.assertEqual(result["columns_by_hand"], ["Site"])
            ws = openpyxl.load_workbook(Path(tmp) / "Requests.xlsx")["Requests"]
            headers = [c.value for c in ws[1]]
            self.assertNotIn("Site", headers)
            row = dict(zip(headers, [c for c in ws[2]]))
            self.assertIsInstance(row["Quantity"].value, int)
            self.assertIsInstance(row["Amount"].value, float)
            self.assertIs(row["Urgent"].value, True)
            self.assertEqual(row["SubmittedAt"].value, datetime(2026, 1, 10, 9, 30))
            self.assertEqual(row["Tags"].value, "Tools")
            self.assertEqual(dict(zip(headers, [c.value for c in ws[3]]))["Tags"],
                             "Safety; Tools")

    def test_empty_table_keeps_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = build(PROBE, Path(tmp), "--empty-table")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            ws = openpyxl.load_workbook(Path(tmp) / "TypeProbe.xlsx")["TypeProbe"]
            (table,) = ws.tables.values()
            self.assertTrue(table.ref.endswith("2"))
            self.assertIsNone(ws["A2"].value)

    def test_probe_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = build(PROBE, Path(tmp))
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            ws = openpyxl.load_workbook(Path(tmp) / "TypeProbe.xlsx")["TypeProbe"]
            self.assertEqual(len([c for c in ws[1]]), 11)

    def test_runs_from_outside_the_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = build(EXAMPLE, Path(tmp) / "out", cwd=Path(tmp))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((Path(tmp) / "out" / "Holidays.xlsx").is_file())


class CsvTests(unittest.TestCase):
    def test_csv_has_bom_crlf_and_iso_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = build(EXAMPLE, Path(tmp), "--format", "csv")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            raw = (Path(tmp) / "Holidays.csv").read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
            self.assertIn(b"\r\n", raw)
            rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline="")))
            self.assertEqual(rows[0], ["HolidayDate", "Name"])
            self.assertEqual(rows[1][0], "2026-12-07")
            self.assertEqual(len(rows), 22)
            setup = (Path(tmp) / "Holidays.Setup.md").read_text(encoding="utf-8")
            self.assertIn("หมายเหตุ", setup)
            self.assertIn("Enforce unique values", setup)

    def test_csv_without_bom(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = build(PROBE, Path(tmp), "--format", "csv", "--csv-encoding", "utf-8")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            raw = (Path(tmp) / "TypeProbe.csv").read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertIn("ทดสอบภาษาไทย", raw.decode("utf-8"))

    def test_csv_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            build(LINT_BASE / "Requests.list.json", Path(tmp), "--format", "csv")
            rows = list(csv.DictReader(io.StringIO(
                (Path(tmp) / "Requests.csv").read_text(encoding="utf-8-sig"), newline="")))
        self.assertEqual(rows[0]["Urgent"], "TRUE")
        self.assertEqual(rows[0]["SubmittedAt"], "2026-01-10 09:30")
        self.assertEqual(rows[0]["Amount"], "120.5")
        self.assertNotIn("Site", rows[0])

    def test_same_spec_same_csv(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            build(PROBE, Path(a), "--format", "csv")
            build(PROBE, Path(b), "--format", "csv")
            for name in ("TypeProbe.csv", "TypeProbe.Setup.md"):
                self.assertEqual((Path(a) / name).read_bytes(), (Path(b) / name).read_bytes())


class RefusalTests(unittest.TestCase):
    def test_lint_errors_stop_the_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
            spec["rows"] = spec["rows"][:2]
            path = Path(tmp) / "Holidays.list.json"
            path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            proc = build(path, Path(tmp), "--format", "csv")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("rows-too-few", proc.stderr)
            self.assertFalse((Path(tmp) / "Holidays.csv").exists())

    def test_lookup_target_found_next_to_the_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = build(LINT_BASE / "Requests.list.json", Path(tmp), "--format", "csv",
                         "--with")
            self.assertEqual(proc.returncode, 1, "with no target the lookup is an error")
            self.assertIn("lookup-target", proc.stderr)

    def test_missing_openpyxl_says_how_to_install(self):
        script = ("import sys, runpy; sys.modules['openpyxl'] = None; "
                  f"sys.argv = ['build_list.py', {str(EXAMPLE)!r}, '--format', 'xlsx']; "
                  f"runpy.run_path({str(BUILD)!r}, run_name='__main__')")
        proc = subprocess.run([sys.executable, "-c", script], capture_output=True,
                              text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("pip install openpyxl", proc.stderr)
        self.assertIn("--format csv", proc.stderr)


if __name__ == "__main__":
    unittest.main()
