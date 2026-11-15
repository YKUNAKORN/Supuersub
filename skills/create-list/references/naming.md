# Naming lists and columns

A column's internal name is fixed when the column is created and cannot be changed
later. Power Apps formulas, flows and the REST API all use it. `create-list` therefore
chooses it once, in the spec, and makes it the column header in the import file.

## The rule

List and column names (`name` in the spec) are:

- ASCII letters and digits only, PascalCase, starting with a capital letter:
  `HolidayDate`, `RequestStatus`, `CostCentre`;
- no spaces, underscores, hyphens or other punctuation;
- short: at most 32 characters for a column, at most 31 for a list (an Excel sheet name
  is limited to 31, and the data sheet is named after the list);
- unique within the list, ignoring case (`Status` and `status` collide);
- not a built-in column name: `ID`, `Created`, `Modified`, `Author`, `Editor`,
  `Attachments`;
- for a list name, not something Excel reads as a cell reference (`AB12`, `R1C1`),
  because the Excel table is named after the list.

The human-readable name, in any language, goes in `displayName` and is applied after the
import by renaming the column. Renaming changes only the display name.

## Why this rule

What SharePoint does with a header that has spaces, non-ASCII letters or many characters
is widely reported (spaces become `_x0020_`, long names are cut short) but not verified
here: see `internal-name` in [`import-behavior.md`](import-behavior.md). A header that is
short, ASCII and has no spaces gives the same internal name under every one of those
reports, so the answer does not matter.

## Title

Every list created the ordinary way has a `Title` column. Whether an imported list must
map a column to Title is unverified (`title-mapping`). The spec does not name a column
`Title` unless the design wants the built-in Title. The linter warns when one does. If
the import screen asks for a Title column, the user picks the column that best names a
row, and records what the screen asked.

## Names other skills use

- `mock-ui` writes `data-source` (a list name) and `data-field` (a column name) in
  PascalCase; use the same names, so `create-app` binds to columns that exist.
- `create-app` and `create-flow` refer to columns by internal name. Hand over the
  `name` → `displayName` table so nobody guesses.
