# End-to-end walk-through: a leave request app

One small scenario taken through all five skills: **Restday**, a leave request app with
one SharePoint list and one notification flow. Every artifact is saved under
[`tests/e2e/leave-request/`](../tests/e2e/leave-request/) in the layout the hand-off
contract fixes, and [`tests/test_e2e_leave_request.py`](../tests/test_e2e_leave_request.py)
re-checks it on every CI run.

## How this was produced, plainly

The phase brief asked for a run in a fresh session. **This was not one.** The artifacts
were written in the phase 07 working session by following each skill's `SKILL.md` and
references, by the same model that had just read the whole repository. That model knew
the skills far better than a fresh session would, so this walk-through shows that the
pipeline *can* produce consistent, lint-clean files; it does not show that a fresh
session *will*. Release test plan item `E0` repeats it in a fresh session.

Two more things to know:

- The deterministic steps really ran the skills' scripts: `tokens_to_css.py` made the
  `:root` block, the linters gave the verdicts below, `build_list.py` and
  `build_flow_package.py` built the binaries. Model judgment went into `DESIGN.md`, the
  HTML, the `.pa.yaml`, the specs, `lists.md` and `flow.md`.
- The mockup's shared chrome and the screens' sidebar and top bar follow the bundled
  Kitroom example (same geometry), re-coloured and re-labelled. Content, fields, palette
  and data are new.

The user's request and their one round of answers are in
[`brief.md`](../tests/e2e/leave-request/brief.md). They write in Thai, so visible text in
every artifact is Thai and every identifier is ASCII.

## The steps

**Machine-checked** means a script in this repository settles it and CI re-runs it.
**Owner** means only a person with the real tool can settle it; each such item has an id
in [`release-test-plan.md`](release-test-plan.md).

### 1. design-md → `DESIGN.md`

- **Built**: `DESIGN.md`, target `power-apps`: pine-green action colour, Segoe UI, 6px
  controls and 8px panels, three status badges, all eleven sections.
- **Verdict**: `design_lint.py --target power-apps` → `VERDICT: CLEAN` (no findings).
- **Machine-checked**: tokens, references, contrast of every filled component, the
  Power Apps profile (no shadow, blur, motion, one-sided border, non-Segoe font).
- **Owner**: whether it looks calm and plain, as asked (`E1`, together with the mockup).
- **Next**: `mock-ui`.

### 2. mock-ui → `supersub/mockup/`

- **Built**: `leave-list.html` (`scrLeaveList`, start: my requests with status badges),
  `new-leave.html` (`scrNewLeave`: the form), `index.html`, `sitemap.json`. Two screens,
  as the user agreed.
- **Verdict**: `mock_lint.py supersub/mockup --design DESIGN.md --strict` →
  `VERDICT: CLEAN`.
- **Machine-checked**: every control navigates or names its action; links agree with the
  sitemap; every screen reachable with a way back; the `:root` block equals what
  `tokens_to_css.py` makes from `DESIGN.md` today; nothing needs the network; fixed px
  canvas.
- **Owner**: open `index.html` in a browser and click through; Thai renders (`U1`).
- **Implies**: list `LeaveRequests` (fields `LeaveType`, `StartDate`, `EndDate`,
  `Reason`, `ApproverEmail`, `Status`); flow `NotifyApprover` (`run-flow:` on ส่งใบลา).
- **Next**: `create-app`, `create-list`, `create-flow`.

### 3. create-app → `supersub/app/`

- **Built**: `scrLeaveList.pa.yaml`, `scrNewLeave.pa.yaml`, `PASTE-ORDER.md`.
- **Verdict**: `pa_lint.py --app-dir supersub/app --sitemap supersub/mockup/sitemap.json`
  → `VERDICT: SAFE TO PASTE` for both, 0 errors, 0 warnings, no control name shared
  between the two files.
- **Machine-checked**: schema v3.0, only catalogued controls and properties, every
  `Navigate()` target exists, each file's screen id is the sitemap's.
- **Declared, not hidden**: date fields are text inputs (DatePicker unattempted), the
  three rows are static (Gallery unattempted), ส่งใบลา only navigates (data binding
  unverified, and the flow has a button trigger).
- **Owner**: paste both into a new app (`E2`), which also answers the multi-screen
  questions `M1`–`M4`.
- **Next**: `create-list`, `create-flow`.

### 4. create-list → `supersub/lists/`

- **Built**: `lists.md`, `LeaveRequests.list.json`, `LeaveRequests.xlsx` (one table plus
  a `Setup` sheet), `LeaveRequests.csv` with `LeaveRequests.Setup.md`. Three sample rows
  (`sampleRows: true`), `example.com` addresses only.
- **Verdict**: `list_lint.py supersub/lists` → `VERDICT: USABLE, WITH 6 ITEM(S) TO CHECK
  (6 on unverified import behaviour)`: `title-mapping`, `offer-text`, `offer-choice`,
  `choice-from-data`, `offer-note`, `offer-datetime`. For the `.csv`, `csv-values` is
  added. `build_list.py` → `VERIFIED` for both formats.
- **Machine-checked**: names, types, choices, row values, the table and typed cells of the
  `.xlsx` on reopening; the rebuilt files equal the saved ones byte for byte.
- **Owner**: import the `.xlsx` and record what the screen proposed (`E3`); the same
  questions as the type probe (`P1`–`P8`).
- **Next**: `create-app` binds to these names; `create-flow` sends to `ApproverEmail`.

### 5. create-flow → `supersub/flows/`

- **Built**: `flow.md` (one flow, and why one), `NotifyApprover.flow.json`,
  `NotifyApprover_LegacyPackage.zip` (`--seed e2e-leave-request`, so it rebuilds to the
  same bytes).
- **Status**: `package with unverified steps`. The trigger is a button, not Power Apps
  or a new list item: both of those are `unattempted` in the catalog, and `flow.md` says
  so as an open question.
- **Verdict**: `flow_lint.py supersub/flows` → `VERDICT: SHOULD IMPORT, WITH 1 ITEM(S) TO
  CHECK`: the generated connection reference (`package_connection_reference`).
  `build_flow_package.py` → `VERIFIED: 5 entries in the reference layout, every file
  parses, ids agree.`
- **Machine-checked**: every step is a catalog entry; no tenant value, address or
  connection is embedded; the zip layout matches the owner's import-tested reference.
- **Owner**: import and run it once; does the e-mail arrive with readable Thai (`E4`)?
- **Next**: `create-app` would call it once a Power Apps trigger is harvested.

## The hand-off, checked

`tests/test_e2e_leave_request.py` also checks that names survive each hand-off: every
`data-source` and sitemap `source` is a list spec's `name`; every `data-field` and sitemap
field is a column; every `run-flow:` action is a flow spec's `name`; every `.pa.yaml`
carries its sitemap screen id and names only real columns in its comments; the
sitemap's `design` path resolves to the project's `DESIGN.md`.

## What this walk-through does not prove

That any of it pastes, imports or runs. Every green line above is a script agreeing with
this repository's own catalogs. The owner items `E0`–`E4` are where that changes.
