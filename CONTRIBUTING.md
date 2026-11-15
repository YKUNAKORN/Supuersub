# Contributing

Thanks for helping make `supersub` better. The single most valuable
contribution is a **real result from the real tool**: a Power Apps Studio paste, a
SharePoint list import, a Power Automate import. Every skill lives or dies by whether
its catalog matches what those tools actually accept.

## Ways to contribute

| You have… | Do this |
|---|---|
| A control/property that Studio **accepted** or **rejected**, and the catalog is wrong or silent about it | Open a [Control test report](https://github.com/YKUNAKORN/supersub/issues/new?template=control-report.yml) issue, then (optionally) a PR editing `skills/create-app/references/confirmed-controls.md` |
| A `.pa.yaml` the skill produced that failed to paste | Open a [Bug report](https://github.com/YKUNAKORN/supersub/issues/new?template=bug_report.yml) with the file and the exact Studio error |
| A SharePoint import of a file `create-list` built (worked or not) | Open a [List import report](https://github.com/YKUNAKORN/supersub/issues/new?template=list-import-report.yml) |
| A Power Automate import of a package `create-flow` built (worked or not) | Open a [Flow import report](https://github.com/YKUNAKORN/supersub/issues/new?template=flow-import-report.yml) |
| An idea for the workflow, templates, or a new example screen | Open a [Feature request](https://github.com/YKUNAKORN/supersub/issues/new?template=feature_request.yml) |

## Reporting a control test result

Because Studio pins control versions, a test result is only useful with context.
Always include:

1. **Control type + version** exactly as it appeared, e.g. `Classic/DropDown@2.3.1`
2. **The property** you tested (or "the control itself")
3. **Studio outcome** — pasted cleanly / warning `PA2105` / blocked `PA1001` / etc.
4. **Studio version** — Power Apps Studio → `?` → About, e.g. `3.24102.x`
5. **The minimal YAML snippet** you pasted (full `Screens:` wrapper, one control)

For the twelve controls the catalog is silent about — Gallery, Form, DataTable, Toggle,
DatePicker, ComboBox, Slider, Timer, CheckBox, HtmlText and the modern layout containers
— that snippet is already written for you in
[`skills/create-app/assets/test-snippets/`](skills/create-app/assets/test-snippets/),
one file per control, one property per line so a failure can be bisected by deleting
lines. [`docs/test-plan.md`](docs/test-plan.md) is the results table and explains exactly
what to change in `controls.yaml` for each kind of outcome.

Example of a good catalog entry:

```markdown
| `Classic/DropDown@2.3.1` | `ChevronBackground` | ✅ Confirmed | Studio 3.24102.x — pasted cleanly, no warning |
```

## Reporting a SharePoint import result

`create-list` knows little about the import screen for certain: which types its
drop-down offers, whether it insists on a Title column, how it reads a UTF-8 CSV. Each
of those is a row in `skills/create-list/references/import-behavior.md` with an evidence
level, and an import report is what moves one. Always include:

1. **The file**: `.xlsx` or `.csv`, and for a CSV whether it had a byte-order mark
   (`build_list.py` writes one unless `--csv-encoding utf-8`).
2. **The entry point**: Lists app, SharePoint **Create > List**, or Teams; and the
   tenant kind (commercial, GCC, ...), never a tenant name or URL.
3. **Per column**: the type the screen proposed, and every type its drop-down offered.
4. **Title**: did the screen ask for, or force, a column mapped to Title?
5. **Non-ASCII text**: readable or garbled after import.
6. **The evidence rows it bears on** (`offer-person`, `title-mapping`, `csv-encoding`,
   ...): the linter's `unverified-behavior` warnings name them.
7. **The date**.

The type probe in [`docs/test-plan.md`](docs/test-plan.md#sharepoint-list-import-create-list)
asks every open question in one sitting. A report from anyone is passed to the
maintainer; only the owner's own import changes a row to `import-tested`, with the date.
Never attach a file with real people's names or addresses.

## Reporting a Power Automate import result

`create-flow` is the riskiest skill: a slightly wrong package fails with an unhelpful
message. Always include:

1. **The package**: which spec, built with which command (`--seed` if any), and whether
   `build_flow_package.py` printed `VERIFIED`.
2. **The environment kind** (default, developer, ...) and whether **Create in Dataverse
   solutions** is on; never an environment or tenant name.
3. **Upload**: did the package details show one flow row and one connection row per
   connector?
4. **Import**: succeeded, or the **exact** message.
5. **Connection**: did the action show the connection you picked at import, or ask for
   one?
6. **Run**: did one run succeed? Non-ASCII text readable?
7. **The catalog entries it bears on**: the linter's `unverified-step` warnings name
   them.
8. **The date**.

The round-trip test (F2) and one-package-per-item tests (F3 on) are in
[`docs/test-plan.md`](docs/test-plan.md#power-automate-import-create-flow). Never attach
an exported package from your tenant: run `harvest_flow.py` on it and attach the
fragment it writes, after reading it.

## Editing the catalog (`controls.yaml` + `confirmed-controls.md`)

The catalog lives in **two files that must be edited together**:

| File | Role |
|---|---|
| `references/controls.yaml` | machine-readable source of truth — what `skills/create-app/scripts/pa_lint.py` reads |
| `references/confirmed-controls.md` | the human-readable view of the same facts |

`scripts/validate.py` fails if a control appears in one file but not the other, so a PR
touching only the Markdown will not pass CI.

Two other files sit alongside them:

| File | Role |
|---|---|
| `references/control-ids-candidate.yaml` | Microsoft's first-party control-id enum, mirrored. Every entry is `evidence: unverified` and CI enforces that. It only improves a linter message; nothing in it may be promoted to `controls.yaml` without a Studio test. |
| `skills/create-app/scripts/harvest_controls.py` | Grows `controls.yaml` from a real Studio export. See [`references/harvesting.md`](skills/create-app/references/harvesting.md). |

If you grew the catalog from an export rather than a paste test, say so in the PR and leave the
entry at `evidence: studio-export`. And remember the caveat that governs harvesting: Studio only
serialises properties that differ from their default, so **absence in an export is never evidence
that a control lacks a property**. Never add a "does not support" claim from a harvest.

- **Never** move an item from "unverified" to "confirmed" without a Studio test to cite.
- Keep the empirical tone: say *which Studio version* confirmed it.
- If a newer Studio changes a version number, add a row — don't overwrite history.

## Privacy guard

This repository is public. `scripts/validate.py` runs `scripts/privacy_check.py`, which
fails on any e-mail address outside `example.com`, `example.org` and `contoso.*`, any
SharePoint or Microsoft 365 tenant host other than `contoso`, and any absolute home path.
You can also keep a local, untracked `.private-terms.txt` at the repo root (one term per
line, `#` comments allowed) listing words that must never appear in a tracked file or file
name; the check matches them case-insensitively, reports only the file and line, never the
term, and passes with a "skip" note when the file is absent, as it is in CI. Never write
those terms into the repository, a test, a doc or a commit message.

## YAML / skill style

- Every property value starts with `=` (`Text: ="hi"`, `X: =0`).
- Block-style `Properties:` only — never inline `{ }` (RGBA commas break flow YAML).
- Example screens under `assets/examples/` must be **real, paste-tested** files with
  generic sample content — no real customer data, no secrets.
- Run the checks locally before opening a PR:

```bash
python scripts/validate.py
python -m unittest discover tests
```

Both need `pyyaml` and `jsonschema`; the `create-list` `.xlsx` tests also need
`openpyxl` and skip without it:

```bash
pip install pyyaml jsonschema openpyxl
```

To check a `.pa.yaml` you are working on:

```bash
python skills/create-app/scripts/pa_lint.py path/to/screen.pa.yaml
```

## Changing SKILL.md, the catalog, or the patterns

These change what the model produces, and "it looked fine when I tried it" is not
evidence. Before and after your change, run at least two of the eval cases by hand and
compare the tables:

```bash
# ask Claude to convert tests/evals/<case>/mockup.html, save the answer, then:
python scripts/run_eval.py /tmp/out.pa.yaml --case tests/evals/app-shell
```

Put the before/after in the PR. [`docs/evals.md`](docs/evals.md) explains the loop, why
it is manual, and — importantly — what the scorer cannot see, so the comparison is not
oversold. One run per case is a sample of one; a row that flips once is weak evidence.

## Pull request checklist

- [ ] `python scripts/validate.py` passes
- [ ] `python -m unittest discover tests` passes
- [ ] Catalog changes cite a Studio version, an import date, or a documentation URL
- [ ] Changes to `SKILL.md` / catalog / patterns show a before-and-after eval run
- [ ] `CHANGELOG.md` updated under `## [Unreleased]`
- [ ] If behaviour changed, `plugin.json` `version` bumped (SemVer)

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By
participating you agree to uphold it.

## Licensing of contributions

By submitting a contribution you agree it is licensed under the repository's
[MIT License](LICENSE). Do not add third-party files without updating `NOTICE`.
