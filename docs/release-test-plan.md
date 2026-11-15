# Release test plan: supersub 2.0.0

What only the owner can check before the 2.0.0 release, as a checklist with space for
the result. Everything a machine can check is in CI (`scripts/validate.py`, the unittest
suite, `scripts/run_eval.py`); this page is the rest.

Each item has an id and appears here exactly once. Items carried over from earlier
phases keep the id they have in [`test-plan.md`](test-plan.md), where the full
procedure and the larger results tables are; record the detail there and tick the box
here. The **Settles** column names the evidence rows or catalog entries an item can
move; each one is named once on this page. `scripts/validate.py` checks both.

Result: write `pass`, `fail: <exact message>`, or `skipped: <why>`, and the date. Never
write a tenant name, site URL, environment name or e-mail address.

Build the upload file first:

```bash
pip install pyyaml jsonschema openpyxl
python scripts/package_plugin.py
```

## 1. Claude chat (claude.ai, desktop, mobile) and Cowork

| Done | ID | Check | Settles | Result | Date |
|---|---|---|---|---|---|
| [ ] | C1 | Customize > Plugins > Add > **Upload plugin** with `dist/supersub.zip`. Accepted without an error? | the upload format (one `plugin.json` at the archive root) | | |
| [ ] | C2 | The plugin page lists five skills: `design-md`, `mock-ui`, `create-app`, `create-list`, `create-flow`. | | | |
| [ ] | C3 | In a new chat: *"Which skills do you have from plugins?"* Claude names all five. Typing `/` shows `supersub:<name>` for each. | | | |
| [ ] | C4 | `design-md`: *"Set up a design system for a small leave request app, for Power Apps."* It runs `scripts/design_lint.py` in the code-execution sandbox and reports a verdict (not "script not found"). | that skill scripts resolve from the skill folder in chat | | |
| [ ] | C5 | `mock-ui`: attach the `DESIGN.md` from C4 and ask for a two-screen mockup. It runs `tokens_to_css.py` and `mock_lint.py` and hands over the files as downloads. | | | |
| [ ] | C6 | `create-app`: attach the mockup files from C5 and ask for Power Apps screens. It runs `pa_lint.py` and reports `SAFE TO PASTE` or lists what is unverified. With no `jsonschema` in the sandbox the verdict is `UNPROVEN`: record which. | whether `jsonschema` exists in the chat sandbox | | |
| [ ] | C7 | `create-list`: *"Design a SharePoint list for leave requests and build the Excel file."* It runs `list_lint.py` and `build_list.py`, which prints `VERIFIED`. Record whether `openpyxl` was there or it fell back to CSV. | whether `openpyxl` exists in the chat sandbox | | |
| [ ] | C8 | `create-flow`: *"Email the approver whenever someone submits a leave request."* It writes `flow.md`, stops, and after your OK runs `flow_lint.py` and `build_flow_package.py`, which prints `VERIFIED`. | | | |
| [ ] | C9 | Remove the uploaded plugin. Customize > Plugins > Add > **Add marketplace** with the repository URL. `supersub` installs from it and C2 holds. | the marketplace route | | |
| [ ] | T1 | Send five messages from [`trigger-matrix.md`](trigger-matrix.md) in separate chats: rows 1, 2, 8, 14 and 21. Note which skill loaded for each. Any row where it was not the owner: fix that description. | the trigger matrix, which was reasoned, not measured | | |

## 2. Claude Code

| Done | ID | Check | Settles | Result | Date |
|---|---|---|---|---|---|
| [ ] | K1 | `/plugin marketplace add YKUNAKORN/power-app-yaml` succeeds. | | | |
| [ ] | K2 | `/plugin install supersub@supersub` succeeds. If `power-app-yaml@power-app-yaml` was installed before, follow the migration note in `CHANGELOG.md` first and record whether the `renames` entry did anything. | the rename migration | | |
| [ ] | K3 | In a project folder, run each of `/supersub:design-md`, `/supersub:mock-ui`, `/supersub:create-app`, `/supersub:create-list`, `/supersub:create-flow` once. Each finds its scripts (`${CLAUDE_SKILL_DIR}` resolved) and writes under `supersub/`. | `${CLAUDE_SKILL_DIR}` substitution in an installed plugin | | |

## 3. The design and the mockup

| Done | ID | Check | Settles | Result | Date |
|---|---|---|---|---|---|
| [ ] | B1 | Brief `01-approval-tool-power-apps.md`, scored as [`evals.md`](evals.md#design-md-written-briefs-scored-by-hand) says. | | | |
| [ ] | B2 | Brief `02-marketing-site.md`. | | | |
| [ ] | B3 | Brief `03-data-dense-dashboard.md`. | | | |
| [ ] | U1 | Open both example mockups in a browser and click through ([`test-plan.md`](test-plan.md#mock-ui-a-browser-click-through)). | | | |

## 4. The end-to-end scenario

Artifacts: [`tests/e2e/leave-request/`](../tests/e2e/leave-request/); what was checked:
[`e2e-walkthrough.md`](e2e-walkthrough.md).

| Done | ID | Check | Settles | Result | Date |
|---|---|---|---|---|---|
| [ ] | E0 | In a **fresh** session with the plugin installed, give Claude the request in `brief.md` and the same answers, skill by skill. Do all five verdicts match the walk-through? Note every difference. | that a fresh session, not the authoring one, gets there | | |
| [ ] | E1 | Does `DESIGN.md` plus the mockup look calm and plain, as the brief asked? | | | |
| [ ] | E2 | Power Apps Studio: paste `scrLeaveList.pa.yaml` and `scrNewLeave.pa.yaml` into a new app as `PASTE-ORDER.md` says. Both paste? Navigation works once both exist? | | | |
| [ ] | E3 | SharePoint: import `LeaveRequests.xlsx` with **From Excel**, apply the `Setup` sheet, delete the sample rows. Proposed types as the `Setup` sheet says? Record the detail under P1. | | | |
| [ ] | E4 | Power Automate: import `NotifyApprover_LegacyPackage.zip`, pick an Outlook connection, run it once with your own address. E-mail arrives, Thai readable? | | | |

## 5. Power Apps Studio (create-app)

Procedure: [`test-plan.md`](test-plan.md#multi-screen-paste). Use the Kitroom screens or
the E2 screens.

| Done | ID | Check | Settles | Result | Date |
|---|---|---|---|---|---|
| [ ] | M1 | Does a pasted screen keep the name under `Screens:`? | `PASTE-ORDER.md` rename step | | |
| [ ] | M2 | Can a screen whose `Navigate()` names a missing screen be pasted? | the paste order | | |
| [ ] | M3 | Does that formula error clear once the target screen is pasted? | the paste order | | |
| [ ] | M4 | After all screens, does any control name end in `_1`? | `L3.duplicate-control-name-in-app` | | |
| [ ] | S1 | Optional, carried over from 1.0.0: the twelve one-control paste tests (Gallery, Form, ...), [`test-plan.md`](test-plan.md#results). Not needed for 2.0.0. | `unattempted_controls` in `controls.yaml` | | |

## 6. SharePoint list import (create-list)

Procedure: [`test-plan.md`](test-plan.md#sharepoint-list-import-create-list). Build the
four type-probe files as shown there, import each as a new list, stop on the type screen.

| Done | ID | Check | Settles | Result | Date |
|---|---|---|---|---|---|
| [ ] | R0 | Did the owner's reference workbook `9AM_Holidays.xlsx` import as intended? | evidence for date and text from a real file | | |
| [ ] | P1 | `TypeProbe.xlsx`: per column, the proposed type and every type the drop-down offered. | `offer-text`, `offer-note`, `offer-number`, `offer-currency`, `offer-datetime`, `offer-boolean`, `offer-choice`, `offer-person`, `offer-hyperlink` | | |
| [ ] | P2 | `TypeProbe.csv`: the same table. Were `YYYY-MM-DD`, digits and `TRUE`/`FALSE` typed as date, number and Yes/No? | `csv-values` | | |
| [ ] | P3 | Did the screen ask for or force a Title column? | `title-mapping` | | |
| [ ] | P4 | `probe/empty/TypeProbe.xlsx` (headers only): what types, and could the list be created? | `empty-table` | | |
| [ ] | P5 | `ProbeThai` after `TypeProbe.csv` (byte-order mark): readable? | `csv-encoding` | | |
| [ ] | P6 | The same for `probe/no-bom/TypeProbe.csv` (no byte-order mark). | (with P5) | | |
| [ ] | P7 | `ProbeChoice` imported as Choice: are its choices already there? | `choice-from-data` | | |
| [ ] | P8 | Is the internal name of `ProbeDateTime` exactly `ProbeDateTime`? | `internal-name` | | |

## 7. Power Automate import (create-flow)

Procedure: [`test-plan.md`](test-plan.md#power-automate-import-create-flow).

| Done | ID | Check | Settles | Result | Date |
|---|---|---|---|---|---|
| [ ] | F1 | The reference package, still open: how was the connection selected, and did the Thai text arrive readable? | | | |
| [ ] | F2a | Round-trip package (`SendTestEmail`): upload shows one flow row and one connection row. | `package_connection_reference` | | |
| [ ] | F2b | It imports. If not, the exact message, and the alternatives in `package-format.md` one at a time. | (with F2a) | | |
| [ ] | F2c | *Send an email (V2)* shows the connection picked at import. | (with F2a) | | |
| [ ] | F2d | One run succeeds; Thai readable. | (with F2a) | | |
| [ ] | F3 | Optional: one package for the next unverified or unattempted item you need. | the item it uses | | |
| [ ] | F4 | Optional: another, as F3. | the item it uses | | |

## After the checklist

- Move only what passed: an evidence row to `import-tested` with the date, a control to
  `studio-tested` with the Studio version. Run the CI checks again.
- Every `fail` goes into the CHANGELOG's known issues for 2.0.0 before the tag.
- Then follow the release steps below.

## 8. Release steps (owner only)

Nothing below has been done. The development branch was not tagged, pushed or
published.

1. **Run the checks** on a clean checkout of `feat/new-skills`:
   `python scripts/validate.py`, `python -m unittest discover tests`,
   `python scripts/run_eval.py`, `claude plugin validate .`.
2. **Sections 1 to 7 above.** At least C1–C9 and K1–K3 before the tag; record every
   `fail` as a known issue in the 2.0.0 entry of [`CHANGELOG.md`](../CHANGELOG.md).
3. **Set the release date** in `## [2.0.0] - 2026-11-15` if it is not today.
4. **Decision D2, the repository rename.** Decide whether the repository becomes
   `YKUNAKORN/supersub`. If it does, rename it on GitHub (GitHub redirects the old URL),
   then replace `YKUNAKORN/power-app-yaml` in one pass. Occurrences at the time of
   writing:

   | File | Count | Note |
   |---|---|---|
   | `.claude-plugin/plugin.json` | 2 | `homepage`, `repository` |
   | `.github/ISSUE_TEMPLATE/config.yml` | 1 | Discussions link |
   | `CHANGELOG.md` | 9 | the 2.0.0 known issue and migration commands; keep released entries as they were |
   | `CODE_OF_CONDUCT.md` | 1 | |
   | `CONTRIBUTING.md` | 5 | issue-template links |
   | `README.md` | 3 | badge (2), install |
   | `SECURITY.md` | 1 | |
   | `SUPPORT.md` | 4 | |
   | `docs/create-app.md` | 2 | report link, issue template |
   | `docs/quickstart.md` | 2 | marketplace add (chat, Claude Code) |
   | `docs/release-test-plan.md` | 1 | K1 |
   | `docs/troubleshooting.md` | 3 | |
   | `skills/create-app/references/harvesting.md` | 1 | ships in the plugin |
   | `skills/create-list/assets/list.schema.json` | 1 | ships in the plugin (`$id`) |

   Re-count before editing: `grep -rIc "YKUNAKORN/power-app-yaml" --exclude-dir=.git .`.
   The marketplace and plugin names (`supersub`) do not change.
5. **Merge** `feat/new-skills` into `main` through a pull request, so CI runs.
6. **Tag and release**: `git tag -a v2.0.0 -m "supersub 2.0.0"`, push the tag, and
   create a GitHub release with the 2.0.0 entry of the CHANGELOG as notes and
   `dist/supersub.zip` (from `python scripts/package_plugin.py` on the tagged commit)
   attached.
7. **After the release**: in Claude Code, `/plugin marketplace update supersub` and
   confirm `2.0.0` is installed; on claude.ai, confirm the marketplace shows 2.0.0. Tell
   existing users about the rename: their `power-app-yaml@power-app-yaml` install stops
   resolving.
