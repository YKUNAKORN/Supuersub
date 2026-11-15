# Evals — telling better from worse

Every earlier phase of this project answered "is this file valid?". `pa_lint.py`
proves a `.pa.yaml` will paste. It cannot tell you whether the screen is the one
the mockup showed, and it cannot tell you whether a change you just made to
`SKILL.md` helped or hurt.

This is the part that can. It is small, and the boundary around it is the most
important thing on this page.

## Table of contents

- [What is automated and what is not](#what-is-automated-and-what-is-not)
- [The loop, in three commands](#the-loop-in-three-commands)
- [Reading the table](#reading-the-table)
- [What a case asserts](#what-a-case-asserts)
- [The cases](#the-cases)
- [A mockup folder: multi-screen-mock](#a-mockup-folder-multi-screen-mock)
- [Comparing two runs](#comparing-two-runs)
- [What the harness cannot see](#what-the-harness-cannot-see)
- [Adding a case](#adding-a-case)
- [The self-check CI runs](#the-self-check-ci-runs)
- [design-md: written briefs, scored by hand](#design-md-written-briefs-scored-by-hand)
- [mock-ui](#mock-ui)
- [create-list](#create-list)
- [create-flow](#create-flow)
- [The whole plugin](#the-whole-plugin)

## Per skill, at a glance

| Skill | Automated (CI) | Manual (a person, with the plugin installed) |
|---|---|---|
| `create-app` | linter fixtures; the scorer against bundled references; patterns and examples lint | convert a case's mockup, save it, score it with `run_eval.py`; paste in Studio |
| `design-md` | linter fixtures; the example and template lint | three written briefs, linter plus a human read |
| `mock-ui` | linter fixtures; the example lints clean; works with JavaScript off | open the pages in a browser and click through; judge the look |
| `create-list` | linter fixtures; build compared with the owner's workbook; same spec, same bytes | import the files and record what the screen showed |
| `create-flow` | linter fixtures; round trip against the owner's package; harvest scrub | import a built package and run it once |
| all five | sandbox simulation; packaging; e2e scenario re-linted and rebuilt | trigger check in chat; the release test plan |

The sections below say what each row means. No step in CI runs a model.

## What is automated and what is not

`scripts/run_eval.py` is a **scorer**, not an eval loop. It takes a `.pa.yaml`
that already exists and checks it against assertions that can be settled
mechanically.

It does not produce that file. Producing it means giving a model a mockup and
asking for a conversion, and **CI does not run a model**. There is deliberately
no API-key step in the scorer and none in `.github/workflows/validate.yml`,
because a harness that quietly depended on a key would be an eval loop in name
only — green on every run where the key happened to be missing, and nobody the
wiser.

So:

| Step | Who does it |
|---|---|
| Give Claude `mockup.html`, get a `.pa.yaml` back | you, by hand |
| Save the answer to a file | you, by hand |
| Score the file against the case | `scripts/run_eval.py` |
| Score the bundled references, to prove the scorer works | CI, on every push |

The manual half is two minutes of work per case. It is manual because the
alternative is a green checkmark that means nothing.

## The loop, in three commands

```bash
# 1. Ask Claude to convert one case's mockup. In a session with the skill loaded:
#
#       Convert tests/evals/app-shell/mockup.html to pa.yaml.
#
# 2. Save the .pa.yaml it hands back.
#    (Save the whole file, including any comments — the scorer reads them.)

# 3. Score it.
python scripts/run_eval.py /tmp/app-shell-run1.pa.yaml --case tests/evals/app-shell
```

`--case` is required when you pass a file: the scorer never guesses which case an
output belongs to.

List what is available:

```bash
python scripts/run_eval.py --list
```

## Reading the table

```
RESULT  CHECK                             EXPECTED         ACTUAL
PASS    controls.by_type:Classic/Button   7-16             9
FAIL    lint.verdict                      safe             unverified
          -> VERDICT: PASTES, BUT 5 UNVERIFIED ITEM(S)
```

| Result | Meaning |
|---|---|
| `PASS` | The assertion held. |
| `FAIL` | It did not. This is the only result that means something is wrong. |
| `XFAIL` | It did not hold, and the case says so in advance with a reason. Reference runs only — see [the self-check](#the-self-check-ci-runs). |
| `XPASS` | A declared deviation stopped failing. The waiver is stale; delete it. Counts as a failure so it cannot be ignored. |
| `UNPROVEN` | The evidence could not be gathered. Almost always `jsonschema` not installed, which disables the layer that catches `PA1001`. Never silently counted as a pass. |
| `SKIP` | The case does not assert this. Not a result, just a reminder of what is unmeasured. |

Exit code is `0` when nothing is `FAIL` or `XPASS`, `1` when something is, and
`2` for a usage or file error. `--json` emits the same rows for scripting.

## What a case asserts

A case is a directory under `tests/evals/`:

```
tests/evals/app-shell/
├── mockup.html          the input — small, self-contained, no external assets
├── expectations.yaml    the assertions
└── notes.md             what this case is meant to stress, in prose
```

`expectations.yaml` has seven optional blocks. Anything you leave out is reported
`SKIP`, never assumed.

| Block | Asserts |
|---|---|
| `structure` | how many screens, and which screen properties must be present |
| `lint` | `pa_lint.py`'s verdict code, error and warning ceilings, per-check budgets |
| `controls` | total count, per-type counts, types that must appear, types that must not |
| `geometry` | every `X`/`Y`/`Width`/`Height` inside the canvas; how many may be non-numeric |
| `navigation` | how many `Navigate()` calls, and that every target resolves |
| `catalog` | how many unverified items may go untagged, how many unverified properties are allowed at all |
| `limitations` | which `impossible_css` effects must be named in a comment, which invented property names must not appear, which substitute controls must |

**Every count is a range.** Two good conversions of the same mockup will not agree
on control count — one draws a divider with a `Rectangle`, another leaves it out —
so an exact number would score style rather than correctness. The ranges are wide
enough to admit any sane reading of the mockup and narrow enough to catch an
output that dropped a region or padded it with filler.

A few details worth knowing:

- **`geometry.in_bounds` reads the screen's own `Height`** when the output sets
  one, and the canvas height otherwise. A screen that correctly declares
  `Height: =2232` because its content scrolls is not punished for it.
- **A geometry value that is not a plain number is counted, never guessed at.**
  `Width: =Parent.Width - 40` is legitimate, but placing it on the canvas would
  mean evaluating Power Fx, which this scorer never does. `geometry.max_unresolved`
  is the budget for those.
- **`navigation.targets_resolve` accepts a commented placeholder**, per SKILL.md
  rule 7. A single-screen deliverable cannot contain the screen it navigates to;
  what it can do is say so on the line.
- **`navigation.sitemap` names a `mock-ui` sitemap.json**, relative to the case.
  Its screen ids count as existing `Navigate()` targets, for the navigation row and
  for the lint verdict alike, because they are the other files of the same app.
- **`catalog.max_untagged_unverified` reuses `pa_lint`'s L3 check** rather than
  reimplementing "an unverified item with no `# UNVERIFIED` comment", so the two
  cannot drift apart.

## The cases

| Case | Stresses | Reference output |
|---|---|---|
| [`app-shell`](../tests/evals/app-shell/notes.md) | persistent chrome; nav rows that must be Buttons, not Labels | `example-app-shell.yaml` |
| [`multi-section-form`](../tests/evals/multi-section-form/notes.md) | `<select>` vs `<input>` fidelity; a screen that must declare `Height` | `example-form.yaml` |
| [`card-grid`](../tests/evals/card-grid/notes.md) | 17 repeated rows without abbreviating; per-row state; no `Gallery` | `example-card-grid.yaml` |
| [`shell-with-form`](../tests/evals/shell-with-form/notes.md) | the seam — three layout idioms in one coordinate space | none |
| [`impossible-effects`](../tests/evals/impossible-effects/notes.md) | honesty: declare the limitation, or fake it | none |
| [`multi-screen-mock`](../tests/evals/multi-screen-mock/notes.md) | a `mock-ui` folder in, one file per screen out, wired navigation | `supersub/app/scrLoanDetail.pa.yaml` |

`impossible-effects` is the one that matters most and the one a scorer is least
obviously able to check. Every effect in its mockup is listed under
`impossible_css` in `controls.yaml`, so there is no right conversion — only a
right disclosure. The case asserts that each effect is **named in a comment in the
produced file**, that none of the invented property names a model reaches for
(`BoxShadow`, `BorderLeftThickness`, `Transition`, …) appear, and that the
sanctioned substitute for the one-sided border — a thin `Rectangle` — is actually
there, so "dropped it" and "substituted it" do not score alike.

## A mockup folder: multi-screen-mock

The other cases take one `mockup.html` and expect one screen back. This one takes the
three-screen mockup `mock-ui` ships (a copy, kept identical by a test, in
`tests/evals/multi-screen-mock/supersub/mockup/`) and expects three files back.

`run_eval.py` still scores **one file per run**. Teaching it to score a folder would
need a second shape of case: per-screen expectation blocks and a list of references in
place of one. That is a redesign of the scorer, and this case does not attempt it.
Instead the work is split:

| What | Checked by |
|---|---|
| Each screen file: structure, lint verdict, control counts, no `Gallery`/`Form`, geometry, navigation to the sitemap's screens | `run_eval.py <file> --case tests/evals/multi-screen-mock`, once per file. The ranges hold for all three screens. |
| Across the files: a control name used on two screens, a screen id defined twice, every target resolving | `pa_lint.py --app-dir <dir> --sitemap tests/evals/multi-screen-mock/supersub/mockup/sitemap.json` |
| Three files with the right names, `PASTE-ORDER.md`, the `box-shadow` declaration on the detail screen, placeholder actions, the hand-off to `create-list` and `create-flow` | **you**, by hand, from the checklist in the case's `notes.md` |

```bash
for f in /tmp/run1/app/*.pa.yaml; do
  python scripts/run_eval.py "$f" --case tests/evals/multi-screen-mock
done
python skills/create-app/scripts/pa_lint.py --app-dir /tmp/run1/app \
    --sitemap tests/evals/multi-screen-mock/supersub/mockup/sitemap.json
```

The CI self-check scores the reference `scrLoanDetail.pa.yaml`; the unit tests score the
other two reference screens and lint all three as one app. Like every reference here,
they were not produced by a fresh model session.

## Comparing two runs

The harness exists to answer one question: *did that change to `SKILL.md` make
output better or worse?* The procedure is the boring one.

1. Before the change, run every case once and keep the outputs and the tables.
2. Make the change.
3. Run the same cases again with the same prompts.
4. Diff the tables.

```bash
for c in app-shell multi-section-form card-grid shell-with-form impossible-effects; do
  python scripts/run_eval.py "runs/before/$c.pa.yaml" --case "tests/evals/$c" --json \
    > "runs/before/$c.json"
done
# ... make the change, regenerate, then:
diff <(jq -r '.results[0].rows[] | "\(.check) \(.result)"' runs/before/app-shell.json) \
     <(jq -r '.results[0].rows[] | "\(.check) \(.result)"' runs/after/app-shell.json)
```

Two honest cautions about that number:

- **One run per case is a sample of one.** Model output varies between runs on the
  same prompt. A single row flipping from PASS to FAIL is weak evidence; the same
  row flipping across three runs is worth acting on.
- **A row that goes from PASS to PASS tells you nothing about what changed inside
  the range.** Control counts moving from 25 to 38 while both sit inside 16–40 is
  invisible to the table and may matter. `--json` carries the actual numbers; look
  at them when a change was supposed to affect size.

## What the harness cannot see

Stated plainly, because a scorer that oversells itself is worse than no scorer:

- **Whether the screen looks like the mockup.** Nothing here renders anything.
  Colours, fonts, alignment, spacing rhythm, and visual hierarchy are all
  unmeasured. A conversion that puts every control in the right coordinate space
  with the wrong colours scores full marks.
- **Whether the file actually pastes into Studio.** `pa_lint.py` checks the
  bundled v3.0 schema and this repo's catalog, both of which are approximations of
  what Studio enforces. Only a paste test settles it.
- **Prose.** A conversion that explains its limitations beautifully in chat and
  says nothing in the YAML scores FAIL on `limitations.declared`, and that is the
  intended verdict — whoever pastes the file in six months has the file, not the
  conversation.
- **Whether a control is the *right* control**, beyond the type counts. Using a
  `Label` where a `Classic/Button` belongs is caught because the counts move; using
  the wrong one of two Labels is not.

## Adding a case

1. `mkdir tests/evals/<name>` and write a **small, self-contained** `mockup.html`
   — no CDN, no webfont, no image file. A case that needs the network scores
   differently on a machine that does not have it.
2. Write `notes.md` first, in prose: what is this case meant to stress, and what
   is the specific wrong answer you expect it to catch? If you cannot name that,
   the case is not earning its place.
3. Write `expectations.yaml`. Start from the nearest existing case. Derive every
   range from the mockup, and write the derivation into a comment next to it —
   `# 16 <input> in the mockup` is what makes the number reviewable a year later.
4. Run it against a real conversion before committing it. A case nobody has ever
   seen pass is a case with unknown thresholds.
5. Add a `reference.output` **only** if a file already in this repo is genuinely a
   conversion of that mockup. Hand-writing one to make CI greener means scoring an
   answer against itself.

`scripts/validate.py` checks the shape of every case on each run: the three files
exist, the mockup pulls nothing external, `expectations.yaml` parses and asserts
something, every `known_deviations` entry carries a reason, and every reference
output exists and still scores as the case says it will.

## The self-check CI runs

```bash
python scripts/run_eval.py          # no arguments
```

With no arguments, the scorer runs every case that names a `reference.output` and
scores it against that file. Four of the six do. In three of them the reference is
one of the bundled example screens; in `multi-screen-mock` it is one of the three
screens converted from the `mock-ui` example in the Phase 04 working session.

**This exercises the scorer. It says nothing about the skill's output quality.**
The examples were written by hand, long before the harness, and were never
generated by a model. What the self-check proves is that the assertions run, that
they read the files correctly, and that a change to `pa_lint.py` or to the catalog
has not quietly changed what the harness measures.

`app-shell` carries three declared deviations, all the same five `FontWeight`
properties on `Classic/Button`: `controls.yaml` confirms `FontWeight` on `Label`
only and marks it explicitly unverified on `Button`, while the example uses it.
That contradiction is real, open, and settled only by a Studio paste test —
recorded in the [0.2.0 known issues](../CHANGELOG.md) and waived here with the
reason written out in `tests/evals/app-shell/expectations.yaml`. If a Studio
result settles it, the row turns `XPASS` and the waiver should be deleted.

## design-md: written briefs, scored by hand

Everything above is about `create-app`. The `design-md` skill has no scorer of the
`run_eval.py` kind. What it has is narrower, and this section says exactly how narrow.

**Automated, in CI:**

| What | Where |
|---|---|
| Each lint check fires on its fixture, and only there | `tests/test_design_lint.py`, `tests/fixtures/design-md/` |
| The bundled example `DESIGN.md` lints with zero findings | `scripts/validate.py`, `tests/test_design_lint.py` |
| The template lints with no errors and has all eleven sections | same |
| The Power Apps profile covers every `impossible_css` id in the catalog | `tests/test_sync_shared.py` |

**Not automated: the three briefs.** [`tests/briefs/design-md/`](../tests/briefs/design-md/)
holds three written briefs:

| Brief | Target | What it tests |
|---|---|---|
| [`01-approval-tool-power-apps.md`](../tests/briefs/design-md/01-approval-tool-power-apps.md) | `power-apps` | declaring effects the profile rules out, with substitutes |
| [`02-marketing-site.md`](../tests/briefs/design-md/02-marketing-site.md) | `web` | offering directions; not copying an admired brand or its typeface |
| [`03-data-dense-dashboard.md`](../tests/briefs/design-md/03-data-dense-dashboard.md) | `web` | extending an existing `DESIGN.md` with stable token names; dark mode; Thai |

Each brief is scored by **the linter plus a human read**:

1. Give Claude the brief's "What to tell Claude" text (and its attachment, if any), with
   the plugin installed.
2. Save the `DESIGN.md` it writes.
3. Run `python3 skills/design-md/scripts/design_lint.py DESIGN.md` (add
   `--target power-apps` for brief 1). That settles the lint lines of the checklist.
4. Read the file and the conversation and tick the rest of the checklist by hand.

As with `create-app`, CI does not run a model, so none of this is a measure of output
quality until a person has done steps 1-4. The checklists say what a good result
contains; they are not evidence that the skill produces it.

## mock-ui

There is no scorer for mockups: whether a page looks right is a human judgment.

**Automated, in CI:**

| What | Where |
|---|---|
| Every check id fires on its fixture (48 cases, each one defect on a clean base) | `tests/test_mock_lint.py`, `tests/fixtures/mock-ui/` |
| The bundled example lints `CLEAN` for its declared target, with the token-drift check | `scripts/validate.py` |
| The example works with JavaScript off: every control is a real link or form | `tests/test_mock_lint.py` |
| `tokens_to_css.py` turns `DESIGN.md` into the `:root` block every page starts with | `tests/test_tokens_to_css.py` |
| One example page converts to a `.pa.yaml` that lints `SAFE TO PASTE` | `tests/fixtures/mock-ui/converted/` (written by hand, one sample) |

**Manual:** open `index.html` from disk in a browser, click through every screen, and
compare with the `DESIGN.md`. Release test plan item `U1`.

## create-list

**Automated, in CI:**

| What | Where |
|---|---|
| Every check id fires on its fixture (28 cases over a two-list base) | `tests/test_list_lint.py` |
| The example builds to the shape of the owner's reference workbook | `tests/test_build_list.py`, `tests/fixtures/lists/reference-holidays.xlsx` |
| Same spec, same bytes; CSV with and without the byte-order mark; refusal on errors | `tests/test_build_list.py` |
| The evidence table and the schema enums agree with the type table | `scripts/validate.py` |

**Manual:** everything the import screen does. The type probe and its results table are
in [`test-plan.md`](test-plan.md#sharepoint-list-import-create-list). Only the owner's own
import moves a row of `import-behavior.md` to `import-tested`.

## create-flow

**Automated, in CI:**

| What | Where |
|---|---|
| Every check id fires on its case | `tests/test_flow_lint.py` |
| The example rebuilds the owner's reference package: same entry names, same normalised bytes | `tests/test_build_flow_package.py` |
| Harvesting the reference gives the seeded catalog; tenant values never survive | `tests/test_harvest_flow.py` |
| Every catalog entry has an evidence level; the real connection id appears nowhere | `scripts/validate.py` |

**Manual:** importing a package the builder made, and running it.
[`test-plan.md`](test-plan.md#power-automate-import-create-flow), F2 onwards.

## The whole plugin

| What | Where | Automated |
|---|---|---|
| Each skill runs every script its `SKILL.md` names from a copy of its own folder alone (chat's sandbox), and from an empty project folder (Claude Code) | `tests/test_sandbox_simulation.py` | yes |
| `dist/supersub.zip` has the right shape and `claude plugin validate` accepts it unpacked (when the CLI is on PATH) | `tests/test_package_plugin.py` | yes |
| The leave request scenario: every step re-linted, binaries rebuilt byte for byte, names agree across skills | `tests/test_e2e_leave_request.py`, [`e2e-walkthrough.md`](e2e-walkthrough.md) | yes, on saved artifacts |
| Descriptions say what each skill is not for; hand-offs link the contract and name the next skill | `scripts/skill_checks.py` | yes |
| Which skill actually loads for a message | [`trigger-matrix.md`](trigger-matrix.md), release test plan `T1` | no |
| Installing and running on each surface | [`release-test-plan.md`](release-test-plan.md) | no |

