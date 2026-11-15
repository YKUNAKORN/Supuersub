# Test plan

What only a person with the real tools can settle, skill by skill. Every section says
what is automated and what needs a hand. The release checklist,
[`release-test-plan.md`](release-test-plan.md), points into this page; record results
here, where the tables are.

| Skill | Automated | Manual, in this page |
|---|---|---|
| `design-md` | linter and fixtures | [the three briefs](#design-md-the-three-briefs) |
| `mock-ui` | linter, fixtures, JavaScript-off check | [a browser click-through](#mock-ui-a-browser-click-through) |
| `create-app` | linter, scorer, patterns | [paste tests](#paste-test-plan-create-app), [multi-screen paste](#multi-screen-paste) |
| `create-list` | linter, builder, reopen-and-verify | [the SharePoint import](#sharepoint-list-import-create-list) |
| `create-flow` | linter, builder, round trip, harvester | [the Power Automate import](#power-automate-import-create-flow) |

## design-md: the three briefs

Automated: `tests/test_design_lint.py` (every check on its fixture), and the bundled
example and template lint. Manual: give Claude each brief in
[`tests/briefs/design-md/`](../tests/briefs/design-md/) and tick its checklist; the
procedure is in [`evals.md`](evals.md#design-md-written-briefs-scored-by-hand).

| # | Brief | Lint verdict | Checklist all ticked? | Date |
|---|---|---|---|---|
| B1 | `01-approval-tool-power-apps.md` | | | |
| B2 | `02-marketing-site.md` | | | |
| B3 | `03-data-dense-dashboard.md` | | | |

## mock-ui: a browser click-through

Automated: `tests/test_mock_lint.py` and the JavaScript-off check. Manual: nothing
renders in CI.

| # | Check | Answer | Browser | Date |
|---|---|---|---|---|
| U1 | Open `skills/mock-ui/assets/example/index.html` and `tests/e2e/leave-request/supersub/mockup/index.html` from disk. Every link and button goes where the sitemap says; Thai text is readable; nothing looks broken against its `DESIGN.md`. | | | |

## Paste-test plan (create-app)

Twelve controls are in the skill's blind spot: the conversion knows they exist and has
no evidence about any of them. This page is the worksheet for closing that gap. Only
someone with Power Apps Studio open can, so everything here is written to be filled in
by hand, one row at a time, without asking anything back.

The snippets live in
[`skills/create-app/assets/test-snippets/`](../skills/create-app/assets/test-snippets/).
Each is a complete file: paste the whole thing onto a **blank** screen with **Paste
code**, one file per screen.

## Find your Studio version once

Studio → the **?** (help) menu → **About**. Write it in the box below and use the same
string in every row; `controls.yaml` has a `studio_version_tested:` field that is
currently `unknown`, and this is what finally fills it in.

```
Studio version tested:  ______________________     Date: ____________
```

## Result codes

Use one of these in the Result column. They are the buckets that change what happens
next, so a row with `PA2108 Items` is worth ten rows of "didn't work".

| Code | Means | What it proves |
|---|---|---|
| `OK` | Pasted with no message at all | The control id **and every property in the file** are real. Best possible result. |
| `OK/ver X` | Pasted, Studio warned `PA2105`/`PA2106` and substituted version X | The id works. Record X — it is the `@version` the catalog should carry. |
| `PA2108 <Prop>` | Blocked, naming a property | That property is wrong **at that version**. Everything else is still untested — delete that line and paste again. |
| `PA1001` | Blocked on schema | The file shape or the control id is wrong. Stop deleting properties. |
| `UNKNOWN-ID` | Studio says the control type is not recognised | The id is wrong. Try `Classic/<Id>`, then read the real id off a Studio-inserted control. |
| `OTHER: <text>` | Anything else | Paste Studio's exact words. |

Bisecting: delete **one** line below the `# -- UNVERIFIED below here --` marker, paste
again, repeat. The last line you deleted is the culprit. Record every property that had
to go, not just the first.

## Suggested order

Rows 1–2 unlock data binding, which is the largest thing the skill currently cannot do.
Row 11 is the cheapest test in the table and answers two rows at once. Everything after
that is cosmetic-control coverage and can be done whenever.

## Results

| # | Control | Snippet file | Studio version | Result | Properties that failed | Date |
|---|---|---|---|---|---|---|
| 1 | Gallery | `gallery.pa.yaml` | | | | |
| 2 | Form | `form.pa.yaml` | | | | |
| 3 | DataTable | `datatable.pa.yaml` | | | | |
| 4 | Toggle | `toggle.pa.yaml` | | | | |
| 5 | DatePicker | `datepicker.pa.yaml` | | | | |
| 6 | ComboBox | `combobox.pa.yaml` | | | | |
| 7 | Slider | `slider.pa.yaml` | | | | |
| 8 | Timer | `timer.pa.yaml` | | | | |
| 9 | CheckBox | `checkbox.pa.yaml` | | | | |
| 10 | HtmlText | `htmltext.pa.yaml` | | | | |
| 11 | Auto-layout container (A: Variant) | `container-auto-layout-a-variant.pa.yaml` | | | | |
| 12 | Auto-layout container (B: own type id) | `container-auto-layout-b-typeid.pa.yaml` | | | | |

### Row 11 and 12 need two extra boxes

The type id for the modern layout containers is genuinely unknown here — Microsoft's
own control-id enum lists only `GroupContainer`, community guides use a bare
`Container`, and the two cannot both be right. Rather than bisect guesses, insert a
container in Studio and read its code back:

**+ Insert → Layout → Vertical container**, select it, copy its code.

```
Vertical container   Control: ______________________  Variant: ______________
Horizontal container Control: ______________________  Variant: ______________
Container (plain)    Control: ______________________  Variant: ______________
```

Those three lines settle rows 11 and 12 together and are worth more than any paste test
in the table.

### Data-binding expressions

[`references/data-binding.md`](../skills/create-app/references/data-binding.md)
carries the Power Fx for SharePoint lists, `Patch`, `SubmitForm` and `User().Email`
filtering. Every expression in it is marked UNVERIFIED and points at a row above.
Those rows must pass before any of that prose can be trusted, because a `Gallery`
that will not paste makes `Gallery.Items` moot.

```
DataSources: block survives a Studio round-trip?   yes / no / not applicable  ______
  (schema-legal -- see data-binding.md -- but whether "Paste code" accepts a
   non-Screens block at all is a separate, untested question)
```

## Multi-screen paste

`create-app` turns a `mock-ui` mockup into one `.pa.yaml` per screen, with `Navigate()`
between them. Each file pastes onto its own blank screen. Two things about putting
several of them into one app are **unverified**, and until they are settled the
skill's `PASTE-ORDER.md` tells the user to create every screen before judging any
`Navigate()` error.

Use the three screens in
[`tests/evals/multi-screen-mock/supersub/app/`](../tests/evals/multi-screen-mock/supersub/app/)
(they lint `SAFE TO PASTE` and navigate to each other) in a **new, empty** app.

| # | Question | How to test | Answer | Studio version | Date |
|---|---|---|---|---|---|
| M1 | Does a pasted screen keep the name under `Screens:` (`scrNewLoan`), or does Studio keep its own (`Screen2`)? | Add a blank screen, paste `scrNewLoan.pa.yaml`, read the name in the tree view. | | | |
| M2 | Can a screen be pasted when its `Navigate()` names a screen that does not exist yet? | In the same app, before any other screen: was M1's paste blocked, accepted with a warning, or accepted with a formula error on the nav buttons? Copy Studio's exact words. | | | |
| M3 | Does that formula error clear once the target screen is pasted? | Paste `scrLoanList.pa.yaml` onto a second blank screen. Do the errors on `scrNewLoan`'s Loans and Cancel buttons go away by themselves, or only after the formula is edited? | | | |
| M4 | After all three, does any control name end in `_1`? | Paste `scrLoanDetail.pa.yaml`, then search the tree view for `_1`. Expected: none, because the three files share no control name. | | | |

What each answer changes:

- **M1 no** (Studio keeps its own name): `PASTE-ORDER.md` must tell the user to rename
  every screen to its id before anything navigates, and `from-mock-ui.md` should say so
  as a fact, not a check.
- **M2 blocked**: the paste order becomes a dependency order (targets first), and a
  cycle such as list ↔ detail needs a placeholder on one side, wired after both exist.
- **M2 accepted and M3 yes**: the order does not matter; drop "create every screen
  first" from `PASTE-ORDER.md`.

## SharePoint list import (`create-list`)

`create-list` builds files for **New list > From Excel** and **From CSV**. Microsoft's
page documents the entry points, the table requirement, the 5,000-row limit and that
types are proposed from the data, but not which types the drop-down offers, whether a
Title column is demanded, or how a CSV is decoded. Each open question is a row in
[`import-behavior.md`](../skills/create-list/references/import-behavior.md); this
section settles them in one sitting with the **type probe**: one column per candidate
import type, four sample rows, Thai text in `ProbeThai`.

Not yet recorded either: whether the owner's reference workbook
(`tests/fixtures/lists/9AM_Holidays.xlsx`) imported as intended. If it did, say so with
the date, and `offer-datetime` and `offer-text` can move to `import-tested` from that
alone.

### Build the four probe files once

```bash
python skills/create-list/scripts/build_list.py skills/create-list/assets/type-probe.list.json --format xlsx --out probe
python skills/create-list/scripts/build_list.py skills/create-list/assets/type-probe.list.json --format csv --out probe
python skills/create-list/scripts/build_list.py skills/create-list/assets/type-probe.list.json --format csv --csv-encoding utf-8 --out probe/no-bom
python skills/create-list/scripts/build_list.py skills/create-list/assets/type-probe.list.json --format xlsx --empty-table --out probe/empty
```

Import each into a test site as a **new** list (Lists app or SharePoint
**Create > List**), stopping on the screen with the type drop-downs. Delete the lists
afterwards. Tenant kind (commercial, GCC, ...), never a tenant name or URL:

```
Tenant kind:  ______________   Entry point (Lists / SharePoint / Teams):  __________   Date: __________
```

### P1–P2: per column, what the drop-down proposed and offered

Write the type the screen preselected in **Proposed**, and every type in the drop-down
in **Offered** (or "same list as row 1" after the first column).

| Column | importType asked for | Evidence row | xlsx: proposed | xlsx: offered | csv: proposed | csv: offered |
|---|---|---|---|---|---|---|
| `ProbeText` | Single line of text | `offer-text` | | | | |
| `ProbeNote` | Multiple lines of text | `offer-note` | | | | |
| `ProbeNumber` | Number | `offer-number` | | | | |
| `ProbeCurrency` | Currency | `offer-currency` | | | | |
| `ProbeDate` | Date and time (is Date only offered?) | `offer-datetime` | | | | |
| `ProbeDateTime` | Date and time | `offer-datetime`, `csv-values` | | | | |
| `ProbeYesNo` | Yes/No | `offer-boolean`, `csv-values` | | | | |
| `ProbeChoice` | Choice | `offer-choice` | | | | |
| `ProbePerson` | Person | `offer-person` | | | | |
| `ProbeLink` | Hyperlink | `offer-hyperlink` | | | | |
| `ProbeThai` | Single line of text | `offer-text` | | | | |

### P3–P8: the other open questions

| # | Question | Evidence row | How to see it | Answer |
|---|---|---|---|---|
| P3 | Did the screen ask for, or force, a column mapped to Title? Did the created list have a Title column? | `title-mapping` | The import screen; then List settings > Columns | |
| P4 | `probe/empty/TypeProbe.xlsx` (headers, one blank row): what types were proposed? Could the list be created? | `empty-table` | The import screen | |
| P5 | `ProbeThai` after importing `probe/TypeProbe.csv` (with byte-order mark): readable Thai, or garbled? | `csv-encoding` | The created list | |
| P6 | The same for `probe/no-bom/TypeProbe.csv` (no byte-order mark) | `csv-encoding` | The created list | |
| P7 | `ProbeChoice` imported as Choice: are Draft, Submitted and Approved already the choices? | `choice-from-data` | Column settings of ProbeChoice | |
| P8 | Internal names: open List settings > `ProbeDateTime`; the URL ends in `Field=<internal name>`. Is it `ProbeDateTime`? | `internal-name` | The browser's address bar | |

What each answer changes:

- An `offer-*` row confirmed for both formats becomes `import-tested` in
  `import-behavior.md` with the date, and the linter stops warning about that type. A
  type **not** offered: say so in the row's Behaviour and keep the level; then
  `column-types.md` should make `text` or `skip` the default for that type.
- **P3 forced**: the skill must tell the user which column to map to Title before the
  import, and `naming.md` changes from a check to a step.
- **P5 garbled, P6 fine**: change the default `--csv-encoding` to `utf-8` and record why.
  Both garbled: recommend From Excel for any non-ASCII data.
- **P7 yes**: the post-import "check the choices" step stays (order and default still
  need it), but can say the choices arrive from the data.

## Power Automate import (`create-flow`)

`create-flow` builds `.zip` packages for **My flows > Import > Import Package
(Legacy)**. The entries in
[`connectors.yaml`](../skills/create-flow/references/connectors.yaml) are copied from
your reference package (`ClaudeImportTest_LegacyPackage.zip`). After F1 they are
`import-tested`, except `package_connection_reference`: the builder generates a
connection name where the reference held a real one, and F2 settles that. This section
moves further entries to `import-tested` and grows the catalog.

Environment kind (default, developer, ...), never a tenant or environment name:

```
Environment kind:  ______________   Create in Dataverse solutions on?  yes / no   Date: __________
```

### F1: did the reference package import?

The answer settles more than any other row. Write it down even if it was months ago.

| # | Package | Imported? (exact message if not) | Connection selected at import? | Ran once? E-mail arrived, Thai readable? | Date |
|---|---|---|---|---|---|
| F1 | your original `ClaudeImportTest_LegacyPackage.zip` | Yes (owner's report) | not reported | Ran (owner's report); Thai not reported | reported 2026-11-15 |

### F2: the round-trip package

Build the example. It is the reference rebuilt by the skill: fresh GUIDs, and a
generated connection name in place of the original one.

```bash
python skills/create-flow/scripts/build_flow_package.py skills/create-flow/assets/example/SendTestEmail.flow.json --out flow-test
```

Import `flow-test/SendTestEmail_LegacyPackage.zip` as **Create as new**, select your
Office 365 Outlook connection, open the flow, turn it on, run it with your own address,
then delete the flow.

| # | Question | Catalog entries it settles | Answer |
|---|---|---|---|
| F2a | Did the upload show the package details, with one flow row and one connection row under Related resources? | `package_connection_reference` | |
| F2b | Did the import succeed? If not, the exact message | `package_connection_reference` | |
| F2c | After import, did *Send an email (V2)* show your connection, or ask for one? (Tests the generated `connectionReferences`) | `package_connection_reference` | |
| F2d | Did the run succeed and the e-mail arrive with readable Thai? | confirms F1 for a built package; Thai readability was not reported in F1 | |

If F2b fails on connections, rebuild with the alternative in
[`package-format.md`](../skills/create-flow/references/package-format.md)
(`connectionReferences` `source` `Invoker`, or empty), one change at a time, and record
each attempt as F2b-1, F2b-2.

### F3 and on: one package per unverified item you care about

For each item, write the smallest spec that uses it (the example plus one step), build
it, import it, run it once:

| # | Item (catalog entry) | Spec | Imported? | Ran? | Exact message if not | Date |
|---|---|---|---|---|---|---|
| F3 | | | | | | |
| F4 | | | | | | |

What each answer changes: an item that imported **and** ran becomes `import-tested` in
`connectors.yaml` with `source:` naming this row and the date. One that imported but did
not run keeps its level, with a note. One that did not import keeps its level, and the
exact message goes into
[`import-and-fix.md`](../skills/create-flow/references/import-and-fix.md).

### Harvest procedure: growing the catalog

Everything under `unattempted` (SharePoint, Approvals, Teams, Word, conditions, loops,
variables, the Power Apps trigger) becomes usable this way:

1. Build one flow by hand in Power Automate that uses the steps you need. Run it once.
2. **My flows** > the flow > **Export** > **Package (.zip)**. Download it. Keep it out
   of the repository.
3. `python skills/create-flow/scripts/harvest_flow.py <export>.zip --report` shows what
   is new, what would rise to `export`, and what the catalog holds that this export does
   not use (not evidence of anything).
4. `python skills/create-flow/scripts/harvest_flow.py <export>.zip --out fragment.yaml`
   writes the entries at `export`, with every literal value replaced by a placeholder.
   The script refuses to write if anything tenant-like is left. **Read the fragment
   anyway.** Then copy the entries into `connectors.yaml` and remove them from
   `unattempted`.
5. `python scripts/validate.py && python -m unittest discover tests`, then commit
   `connectors.yaml` only, never the export.

## Feeding a result back into the catalog

A result becomes durable only when it lands in
[`controls.yaml`](../skills/create-app/references/controls.yaml), which is the file
the linter and the skill actually read. For an `OK` or `OK/ver X` row, add a `controls:`
entry with `name`, `type` (the id **and** the version Studio confirmed — the bare id is
not enough), `evidence: studio-tested`, a `source:` naming this test plan and the Studio
version, `accepts_children`, `variant`, and the properties that pasted in
`properties_confirmed`; then remove the control from `unattempted_controls` (leave it
there if it is not listed), add the matching row and property bullet to
[`confirmed-controls.md`](../skills/create-app/references/confirmed-controls.md) in
the same commit — `scripts/validate.py` fails if the two files disagree — and run
`python scripts/validate.py && python -m unittest discover tests`. For a `PA2108` row,
record only the properties that *did* paste; a property that failed goes in
`properties_unverified` with a note saying the Studio version that rejected it, never
into a "does not support" list, because Studio only serialises non-default values and
absence never proves absence. For `PA1001` / `UNKNOWN-ID`, change nothing in
`controls.yaml` — an id that does not paste is not a catalog entry — and instead note
the failure in this table so the next attempt starts from it. If you have a real app
export to hand, `python skills/create-app/scripts/harvest_controls.py <export> --report --merge` is the
better route for everything except the version question, and
[`harvesting.md`](../skills/create-app/references/harvesting.md) covers it.
