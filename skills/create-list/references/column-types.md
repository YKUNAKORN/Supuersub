# Column types: what to import, what it should become, what to do after

Every column in a `<ListName>.list.json` names three things, kept apart because the
import screen's behaviour is only partly known ([`import-behavior.md`](import-behavior.md)):

- `finalType`: the SharePoint column type the design calls for;
- `importType`: what to pick in the import screen's drop-down, or `skip` to leave the
  column out of the file and create it by hand;
- the post-import steps that turn the first into the second, plus the settings the
  import cannot set (required, indexed, enforce unique, default value, choices, lookup
  target, display name).

`scripts/list_lint.py` and `scripts/build_list.py` read the type table below. The first
`importType` in a row is the default; any other one listed is allowed.

## Type table

| finalType | SharePoint type | importType | Value in `rows` |
|---|---|---|---|
| `text` | Single line of text | `text` | string, at most 255 characters |
| `note` | Multiple lines of text | `note`, `text` | string |
| `number` | Number | `number` | JSON number |
| `currency` | Currency | `currency`, `number` | JSON number |
| `date` | Date and time, format Date only | `datetime` | `"YYYY-MM-DD"` |
| `datetime` | Date and time, with time | `datetime` | `"YYYY-MM-DDTHH:MM"` (seconds optional) |
| `boolean` | Yes/No | `boolean`, `text` | `true` or `false` |
| `choice` | Choice, one value | `choice`, `text` | one of `choices` |
| `multichoice` | Choice, allow multiple selections | `text`, `skip` | list of values from `choices` |
| `person` | Person or Group | `person`, `text`, `skip` | string: a display name or an `example.com` address |
| `hyperlink` | Hyperlink | `hyperlink`, `text` | `"https://..."` |
| `lookup` | Lookup | `skip`, `text` | string: a value of the target column |

Each `importType` except `skip` has an `offer-<importType>` row in the evidence table:
whether the drop-down offers it. All of those start `unverified`, so every spec gets a
warning per import type it uses until the owner has seen the drop-down.

Types not in the table (Location, Image, Managed Metadata, Calculated, ...) are not
covered by any evidence. Import them as `text` when the data still helps, or leave them
out, and create them by hand after the import. The hand-over says which and why.

## Per type

**`text`.** Nothing to change. Keep values under 255 characters, the limit of a single
line of text; what the importer does with a longer value is untested.

**`note`.** Importing as `text` and changing to Multiple lines of text afterwards is safe
in that direction. Rich text, append changes: set after import.

**`number`, `currency`.** Values are real numbers in the file, never text with a currency
sign or thousands separator. Decimal places, minimum, maximum and the currency format are
set after import. If Currency is not offered, import as Number and change the type.

**`date`.** Values are real dates (in the `.xlsx` a date cell with format `yyyy-mm-dd`).
Pick Date and time; if the screen offers Date only, pick it, otherwise set
**Date and time format: Date only** in the column settings after import.

**`datetime`.** As `date`, with the time kept. How the importer treats time zones is
untested; check one imported value against the file.

**`boolean`.** Values `true`/`false` become `TRUE`/`FALSE` cells. If Yes/No is not
offered, import as text and create a Yes/No column by hand; the column settings may not
offer a change from text to Yes/No (untested).

**`choice`.** List every choice in `choices`, in display order. After import, open the
column settings and check the choices: add any missing, fix the order, set the default.
This is needed whatever `choice-from-data` turns out to be.

**`multichoice`.** No evidence about multi-value cells. Default `text`, with the values
joined by `; ` in one cell, so the data is not lost; then change the column to Choice and
tick **Allow multiple selections**, or create it by hand and leave the column out
(`skip`).

**`person`.** Do not put real people's addresses in a file the plugin ships or a sample.
For an import of real data, the user's own file holds the real values. If Person is not
offered, import as text (the names stay readable) and create a Person or Group column by
hand; do not count on the column settings changing text into Person (untested).

**`hyperlink`.** Values start `https://`. If Hyperlink is not offered, import as text.

**`lookup`.** Nothing shows the import creating a lookup, so it is not attempted. Create
the target list first (the
`lists.md` creation order), then add the Lookup column by hand: **Add column > Lookup**,
the target list, the target column. Default `skip`. Use `text` only to keep the values
for reference while the lookup is set up, and say that the text column is deleted after.

## Settings the import never sets

Apply these after import, in this order, per column:

1. Display name (rename; the internal name stays the header).
2. Type change, when `importType` differs from `finalType`.
3. Choices and default value.
4. Required.
5. **Indexed, then Enforce unique values**: set the index first, then turn on unique
   values. The owner's reference workbook records this order from their own setup; the
   linter therefore requires `indexed` wherever `unique` is set.
