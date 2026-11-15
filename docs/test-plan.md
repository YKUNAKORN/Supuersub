# Paste-test plan

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
