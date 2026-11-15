---
name: create-list
description: >-
  Designs SharePoint lists with the user (which lists, which columns, which type each,
  how lists relate) and builds an .xlsx or .csv to create each list with New list > From
  Excel or From CSV, plus a checklist of the settings to apply after import. Use when
  someone needs a SharePoint list or Microsoft Lists list, asks to "design the list",
  "which columns" a list needs, or wants to import from Excel or CSV, including the data
  behind a mock-ui mockup. Not for building flows (that is create-flow) or screens (that
  is create-app); both use the list and column names this skill fixes.
---

# SharePoint lists: design, then build the import file

Produce, per list, a spec `<ListName>.list.json`, an import file (`.xlsx`, or `.csv`
with `<ListName>.Setup.md`) and, for the whole design, `lists.md`. Reply in the user's
language; display names and setup text follow it, internal names stay ASCII. Paths are
relative to this skill's folder: `${CLAUDE_SKILL_DIR}`, or run from that folder.

## The workflow (in order)

1. **Understand the data.** From the user's description, and from
   `supersub/mockup/sitemap.json` when it exists: its `data` entries name the lists
   (`source`) and columns (`fields`); the pages' `data-field` names match. Use those
   names. Ask only what is missing: what one row is, who fills it in, which values are
   fixed choices, which columns point at another list, what must be unique.
2. **Propose the design in `lists.md`**: one table per list (column, display name,
   finalType, required, unique, choices, notes), the relationships between lists, and
   the order to create them in (a lookup's target list first). Name columns by
   [`references/naming.md`](references/naming.md); pick types from
   [`references/column-types.md`](references/column-types.md). **Get the user's
   agreement before building anything.**
3. **Write the spec, lint it, build the file.** One `<ListName>.list.json` per list
   (schema: [`assets/list.schema.json`](assets/list.schema.json); a finished example:
   [`assets/example/Holidays.list.json`](assets/example/Holidays.list.json)). Then
   `python3 ${CLAUDE_SKILL_DIR}/scripts/list_lint.py supersub/lists` (`scripts/list_lint.py`;
   add `--format csv` for a CSV) and fix every error. Then, per list,
   `python3 ${CLAUDE_SKILL_DIR}/scripts/build_list.py supersub/lists/X.list.json --format xlsx`
   (`scripts/build_list.py`). If `openpyxl` is missing, the script says so: offer
   `pip install openpyxl` or `--format csv`.
4. **Verify by reopening.** `build_list.py` reopens what it wrote and prints `VERIFIED`
   only when the table exists, its headers equal the spec, and date and number cells are
   real dates and numbers. Anything else is not finished.
5. **Hand over** (below).
6. **Ask what the import screen actually showed**: for each column the type it proposed
   and the types its drop-down offered, whether it asked for a Title column, whether
   non-ASCII text looked right. Tell the user to record it in the results table at the
   end of [`references/import-behavior.md`](references/import-behavior.md), and to report
   it to the plugin's maintainer; only the owner's own import changes a row to
   `import-tested`.

## Rules

- **Three things per column, never blurred**: `importType` (what to pick in the import
  drop-down, or `skip`), `finalType` (what the design needs), and the post-import steps
  between them. The import cannot set required, indexed, unique, default, choices,
  lookups or display names; the setup guidance always lists them.
- **Headers are internal names**, chosen once: ASCII PascalCase, no spaces or
  punctuation, a letter first, short, unique ignoring case, and not `ID`, `Created`,
  `Modified`, `Author`, `Editor` or `Attachments`. Display names, in any language, are
  applied after import.
- **Types follow the data, so the file holds data**: at least three representative rows,
  each imported column filled in at least three times, dates as real dates, numbers as
  real numbers. When the rows are samples, set `sampleRows: true` and tell the user to
  delete them after import. Invent sample data; never a real person's name or address
  (use `example.com`).
- **Stay under 5,000 rows.**
- **A type the evidence does not cover** (no row in the type table: Location, Image,
  Managed Metadata, Calculated, ...) is imported as `text` or left out (`skip`), then
  created by hand. Say which, and why.
- **Evidence first.** [`references/import-behavior.md`](references/import-behavior.md)
  says how sure we are of each import behaviour. Use a `doc` or `import-tested` row
  without comment. For every `unverified-behavior` warning the linter prints, tell the
  user what was assumed and what to check on the import screen. Never present an
  unverified row as fact.
- **No secrets or real tenant details** in any file: no site URLs, tenant names, list
  GUIDs or real addresses.
- Write under `supersub/lists/` in the project when one is writable; otherwise create the
  files and hand them to the user.

## Hand-off

[`references/shared/handoff.md`](references/shared/handoff.md) is the contract between
the five skills. Never assume an earlier skill ran. Hand over:

- `lists.md`, every spec and every import file, with the lint verdict;
- **the import steps** (from `import-behavior.md`): Lists app, SharePoint
  **Create > List**, or Teams; **From Excel** (select the table named after the list)
  or **From CSV**; the file is saved to the site's Site Assets library; From Excel is
  not available in GCC High and DoD;
- **per column, the type to choose** on the import screen, from the `Setup` sheet or
  `<ListName>.Setup.md`;
- **the post-import checklist**, per list and in creation order: rename to display
  names, change types, choices and defaults, required, indexed then unique, lookups
  created by hand, sample rows deleted;
- **every assumption resting on an `unverified` row**, as the linter named it, with what
  to look for on the screen and what to do if it differs (for example: if the screen
  insists on a Title column, map the column that best names a row and say so);
- the next steps: **`create-app`** binds screens to these list and column names (hand
  over the `name` → `displayName` table); **`create-flow`** uses the same names for
  flows that read or write the lists.
