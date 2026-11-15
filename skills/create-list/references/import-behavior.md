# How SharePoint's list import behaves, and how sure we are

What happens when a user creates a list with **From Excel** or **From CSV** decides
which file `create-list` builds and what it tells the user. Much of it is not documented.
This page keeps what is known apart from what is assumed.

`scripts/list_lint.py` reads the evidence table below. A spec that relies on a row whose
level is not `doc` or `import-tested` gets an `unverified-behavior` warning naming the
row, and the skill tells the user what it assumed and what to check on the import screen.
Editing a row's level here changes the warnings; nothing else needs to change.

## Evidence levels

| Level | Means |
|---|---|
| `import-tested` | The plugin owner imported a file into their own tenant and saw it. Only the owner's report sets this, with the date. |
| `export` | Read from a real export out of the owner's tenant. |
| `doc` | Stated by Microsoft documentation, at the URL in the Source column. |
| `unverified` | Everything else: community guides, memory, a reasonable guess. |

Absence is not evidence. A type missing from a doc page does not prove the import screen
lacks it.

## Evidence table

Source **[MS]** is Microsoft's support page *Create a list based on a spreadsheet*,
<https://support.microsoft.com/en-us/topic/380cfeb5-6e14-438e-988a-c2b9bea574fa>, read
on 2026-11-15.

| Id | Behaviour | Level | Source | Date |
|---|---|---|---|---|
| `entry-points` | A list can be created from Excel or from CSV in the Lists app, in SharePoint (**Create > List**) and in Teams. | doc | [MS] | 2026-11-15 |
| `excel-table` | From Excel needs the data in an Excel **table**; the user selects a table in the file. | doc | [MS] | 2026-11-15 |
| `row-limit` | A table of up to 5,000 rows can be used. | doc | [MS] | 2026-11-15 |
| `site-assets` | A file uploaded from the device is saved to the site's Site Assets library. | doc | [MS] | 2026-11-15 |
| `headers-to-columns` | Table headings become columns; the other rows become list items. | doc | [MS] | 2026-11-15 |
| `type-from-data` | Column types are proposed from the data, and each column has a drop-down to change its type before the list is created. Types can be changed later in List settings. | doc | [MS] | 2026-11-15 |
| `no-default-title` | Importing is "also a way to create a list without the default Title column". | doc | [MS] | 2026-11-15 |
| `gcc-high` | From Excel is not available in GCC High and DoD environments. | doc | [MS] | 2026-11-15 |
| `offer-text` | The drop-down offers **Single line of text**. | unverified | not listed by [MS] | 2026-11-15 |
| `offer-note` | The drop-down offers **Multiple lines of text**. | unverified | not listed by [MS] | 2026-11-15 |
| `offer-number` | The drop-down offers **Number**. | unverified | not listed by [MS] | 2026-11-15 |
| `offer-currency` | The drop-down offers **Currency**. | unverified | [MS] mentions currency only for SharePoint 2016, after import | 2026-11-15 |
| `offer-datetime` | The drop-down offers **Date and time**. | unverified | not listed by [MS] | 2026-11-15 |
| `offer-boolean` | The drop-down offers **Yes/No**. | unverified | not listed by [MS] | 2026-11-15 |
| `offer-choice` | The drop-down offers **Choice**. | unverified | not listed by [MS] | 2026-11-15 |
| `offer-person` | The drop-down offers **Person**. Community guides disagree: one says not for Excel, another describes it for CSV. | unverified | community guides | 2026-11-15 |
| `offer-hyperlink` | The drop-down offers **Hyperlink**. One community guide says not for Excel. | unverified | community guides | 2026-11-15 |
| `title-mapping` | No column has to be mapped to Title. [MS] suggests so (`no-default-title`); a 2025 community guide says a Title mapping is mandatory. | unverified | [MS] and a community guide, in conflict | 2026-11-15 |
| `empty-table` | How a table with headers and no rows is typed. | unverified | none | 2026-11-15 |
| `csv-encoding` | From CSV reads UTF-8 with a byte-order mark correctly, including Thai and other non-ASCII text. | unverified | none | 2026-11-15 |
| `csv-values` | From CSV types `YYYY-MM-DD` as a date, plain digits as a number, and `TRUE`/`FALSE` as Yes/No. | unverified | none | 2026-11-15 |
| `choice-from-data` | A column imported as Choice gets its choices from the distinct values in the data. | unverified | none | 2026-11-15 |
| `internal-name` | The header becomes the internal name; spaces become `_x0020_`; long names are truncated. | unverified | widely reported | 2026-11-15 |

Ids are stable: the linter, the type probe and the test plan refer to them.

## The import steps (from [MS])

1. Open the Lists app, or a SharePoint site (**Create > List**), or in Teams the
   channel's **Files** tab, then open the library in SharePoint.
2. Choose **From Excel** or **From CSV**.
3. Upload the file from the device, or pick it from the site.
4. From Excel: select the table. Check each column's type in the drop-down above it; a
   column can be left out.
5. Name the list, add a description, pick a colour and icon, then **Create**.

What to tell the user to look at in step 4 depends on the rows above that are not
`doc`: which types the drop-down actually offered, whether it asked for a Title column,
and whether non-ASCII text looked right.

## Choices `create-list` made because of this table

- **Headers are the internal names** (ASCII PascalCase, no spaces, short), so the answer
  to `internal-name` does not matter. Display names, in any language, are set after
  import. See [`naming.md`](naming.md).
- **No column is named Title** unless the design calls for it, and the hand-over says
  what to do if the import screen asks for one (`title-mapping`).
- **Every file holds at least three rows**, because types are proposed from the data
  (`type-from-data`) and an empty table is untested (`empty-table`).
- **CSV encoding: UTF-8 with a byte-order mark** (`utf-8-sig`), lines ending CRLF.
  Reason: the byte-order mark is how Excel and other Microsoft tools recognise UTF-8;
  without it a file may be read in the machine's legacy code page and Thai text breaks.
  Whether SharePoint's importer needs or tolerates the mark is `csv-encoding`,
  unverified. `build_list.py --csv-encoding utf-8` writes the file without the mark, so
  both can be tried.
- **Choice columns** list their choices in the spec, and the post-import checklist says
  to check them, whatever `choice-from-data` turns out to be.
- **The setup guidance is always written down** (the `Setup` sheet, or
  `<ListName>.Setup.md` for CSV): the import screen cannot set required, indexed,
  unique, default values, display names or lookups.

## Recording what an import showed

After an import, ask the user what the screen showed for each column (the type it
proposed, the types it offered), whether it asked for a Title column, and whether the
text looked right. Write it in the results table below with the date and tenant kind
(commercial, GCC, ...), never a tenant name or site URL. A result from anyone but the
plugin owner stays `unverified` until the owner repeats it; then the owner changes the
row's level to `import-tested` and puts the date in the Date column.

| Date | Who | File (xlsx / csv) | Row id | What the screen showed |
|---|---|---|---|---|
| | | | | |
