# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Phase 04 of 2.0.0: `create-app` takes a `mock-ui` mockup folder and writes one
`.pa.yaml` per screen. Phase 03: the `mock-ui` skill, and the HTML contract between it
and `create-app`.

### Added (phase 04)
- **`create-app` pipeline branch**, `references/from-mock-ui.md`: read `sitemap.json`
  first (a `web` target is refused with the reason and two ways on), convert the screens
  one at a time with the existing steps, repeat the shared chrome with per-screen names,
  turn every `data-nav` into a real `Navigate()`, render `data-repeat`/`data-source`
  content as static controls with the binding named in a comment (no `Gallery` or
  `Form` while they are unattempted), give each `data-action` a placeholder `OnSelect`
  that names it, apply the catalog's substitute for `data-unsupported`, offer theme
  `Set()` formulas as text only, and write `PASTE-ORDER.md`.
- **`pa_lint.py --app-dir DIR`** (or `--one-app` with files): lints the screen files of
  one app together. New L3 checks `L3.duplicate-control-name-in-app` (a control name on
  two screens: Studio renames the second with `_1`) and `L3.duplicate-screen-in-app`
  (a screen id defined twice). A screen in another file of the app is a valid
  `Navigate()` target.
- **`pa_lint.py --sitemap PATH` and `--known-screens a,b`**: their screen ids are valid
  `Navigate()` targets. The JSON report gains `app_checked` and `known_screens`.
- **Eval case `multi-screen-mock`**: the `mock-ui` Kitroom example (a copy kept
  identical by a test) and three converted screens with `PASTE-ORDER.md`. The screens
  were written in the Phase 04 working session by following the skill, not in a fresh
  model session. They lint `SAFE TO PASTE` as one app with the sitemap.
- **`run_eval.py`: `navigation.sitemap`** in a case's expectations. The sitemap's screens
  count as existing targets, for the navigation row and the lint verdict.
- Fixtures `tests/fixtures/app/clean/` and `tests/fixtures/app/collisions/`, each screen
  file with its single-file sidecar and each folder with a `<case>.app.expected.json`.
- `docs/test-plan.md`, section "Multi-screen paste": four questions for Studio (does a
  pasted screen keep its name; can a screen that navigates to a missing screen be
  pasted; does the error clear; any `_1` after all three).

### Changed (phase 04)
- `create-app` `SKILL.md`: a third branch pointing to `from-mock-ui.md`; rule 7 accepts a
  target in the sitemap or the app; the hand-off names `create-list` and `create-flow`;
  the description names a mock-ui folder as input (650 characters, no trigger dropped).
  The pre-send checklist now points at rules 1–7 instead of repeating them, to stay
  inside the 8,192-byte budget (8,184).
- Cross-file checks run only when the files are declared one app (`--app-dir` or
  `--one-app`). Files passed together without the flag are linted as before: the
  bundled patterns all use one placeholder screen name, and comparing them would be
  wrong.
- `validate.py` and `tests/test_run_eval.py`: a case's input may be a
  `supersub/mockup/` folder with a `sitemap.json` instead of `mockup.html`;
  `multi-screen-mock` is a required case (six in all).
- Docs: `docs/evals.md` (the case, and why it is scored one file at a time),
  `docs/troubleshooting.md`, `README.md`, `references/extend-existing-app.md`.

### Evidence (phase 04)
- Before/after eval, one blind subagent run per case and skill version (a sample of
  one each). `app-shell`: 20 pass / 2 fail before and after, the same two rows
  (`controls.by_type:GroupContainer` 7 > 6, and `navigation.count` 0: both runs wrote
  `OnSelect: =false` with a comment rather than a commented `Navigate()` placeholder).
  `impossible-effects`: 29 / 29 before and after. No row changed between versions.
- Both `app-shell` failures were followed up:
  - `navigation.count`: rule 7 said "keep the placeholder" without showing one, and
    "never invent a screen name" pushed both runs to `=false`. Rule 7 now shows the
    placeholder the skill's own examples and docs use, a commented `Navigate()` named
    after the link, and says never `=false`.
  - `GroupContainer` 7 > 6: the range was derived from the reference, which draws
    glyph icons. The mockup's `.ico` is a rounded CSS square, and `GroupContainer` is
    the only control with confirmed `Radius*`, so the range is now 1–8, with the
    derivation in a comment.
  - A blind re-run with the fixed skill: 22 / 22 on `app-shell`, with 4 placeholder
    `Navigate()` calls. One run.

### Not changed (phase 04)
- No catalog entry, no check id, message or exit code. Every v1 fixture and eval
  self-check passes with its expected file untouched. No `App:` or `DataSources:` block
  is emitted.

### Added (phase 03)
- **Skill `mock-ui`** (`skills/mock-ui/`). Takes a `DESIGN.md` (or, if the user declines
  `design-md`, a short style brief recorded in the output) plus the requirements, agrees a
  screen inventory with the user before any HTML, then writes one self-contained `.html`
  per screen, an `index.html` screen map and a `sitemap.json`. Every link and button
  either navigates (`data-nav` on a real `href` or form `action`, so the prototype works
  from disk with JavaScript off) or names its action (`data-action="verb:Object"`,
  several space-separated). Targets `web` and `power-apps` (fixed 1366 × 768 canvas, px
  geometry, effects the profile rules out only on elements marked
  `data-unsupported="<profile id>"`). Dialogs and state variants (empty, error) are
  screen files of their own with `kind` in the sitemap.
- **`references/html-contract.md`**: the interface `create-app` converts from, each rule
  paired with the linter check id that enforces it. **`references/screen-patterns.md`**:
  app shell, list, detail, form, dashboard, dialog, empty and error states, with the
  px arithmetic for the power-apps canvas.
- **`scripts/tokens_to_css.py`**: `DESIGN.md` front matter -> the one `:root` block every
  page starts with (`--color-*`, `--font-<level>-*`, `--radius-*`, `--space-*`,
  `--<component>-*` as `var()` chains, `--canvas-*`). Under `power-apps` every length
  becomes px (rem, em, unit-less line height). PyYAML.
- **`scripts/mock_lint.py`**: offline checker for a mockup folder, standard library
  only (`--design` also needs PyYAML), 15 error and 18 warning checks with stable ids,
  `--target`, `--design`, `--json`, `--strict`, ending in a verdict like `pa_lint.py`.
  It validates `sitemap.json` against `assets/sitemap.schema.json` with a small built-in
  validator for the schema keywords it uses; a test checks it agrees with `jsonschema`.
- **Assets**: `page.template.html`, `index.template.html`, `sitemap.schema.json`, and an
  original three-screen example (Kitroom, an equipment-loan tool, `power-apps` target)
  with its own `DESIGN.md`, lint-clean under `mock_lint.py --strict --design` and
  `design_lint.py --target power-apps`.
- Tests: `tests/test_mock_lint.py` (48 fixture cases under `tests/fixtures/mock-ui/`,
  each one defect applied to a clean two-screen base; every documented check id and
  every verdict is exercised; the example must lint clean for its declared target and
  work with JavaScript off; both scripts run from outside the repo by absolute path) and
  `tests/test_tokens_to_css.py`.
- `tests/fixtures/mock-ui/converted/scrNewLoan.pa.yaml`: the example's `new-loan.html`
  converted by following `create-app`'s SKILL.md. `pa_lint.py`: SAFE TO PASTE. One
  sample, written by hand, not proof that every mockup converts.

### Changed (phase 03)
- `scripts/sync_shared.py` also copies `handoff.md` and `powerapps-profile.md` into
  `skills/mock-ui/references/shared/`.
- `scripts/validate.py` checks the mock-ui files and description triggers, requires the
  bundled example to lint clean for the target its `sitemap.json` declares (with the
  token-drift check), and lints the example's `DESIGN.md` with `design_lint.py`.
- README: a section on `mock-ui` and its line in the repository layout.

Phase 02 of 2.0.0: the `design-md` skill, and a `shared/` folder for files more than
one skill needs.

### Added (phase 02)
- **Skill `design-md`** (`skills/design-md/`). Interviews the user (at most two rounds),
  offers two or three directions when they have no strong view, and writes a
  `DESIGN.md` in Google's Stitch format as the VoltAgent collection practises it: all
  tokens in YAML front matter (`version`, `name`, `description`, `colors`,
  `typography`, `rounded`, `spacing`, `components`) and eleven `##` sections, the
  spec's eight followed by Responsive Behavior, Iteration Guide and Known Gaps. Two
  targets: `web`, and `power-apps`, which keeps the design inside what `create-app` can
  reproduce and declares each ruled-out effect with its substitute. References:
  `format.md` (own condensed description of the spec, with the lint rules),
  `section-guide.md`, `interview.md`. Assets: a lint-clean template with all eleven
  sections and an original example for an invented brand (Mossgate Commons).
- **`skills/design-md/scripts/design_lint.py`**: offline linter, standard library plus
  PyYAML, 18 error checks and 13 warning checks with stable ids, `--target power-apps`,
  `--json`, `--strict`, ending in a verdict like `pa_lint.py`. It is stricter than
  Google's CLI 0.4.0 where the spec says "error" and the CLI does not check (duplicate
  `##` headings, `version`, missing `fontWeight`, unit-less `fontSize`) and it reads the
  prose, which the CLI never does. Every difference is tabled in `format.md` §7.
- **`shared/`** with `handoff.md` (the hand-off contract, written for a skill to read)
  and `powerapps-profile.md` (derived from `create-app`'s `controls.yaml`: confirmed
  controls and properties, `unattempted_controls`, every `impossible_css` entry; each
  statement names its catalog key). **`scripts/sync_shared.py`** copies them into
  `skills/<skill>/references/shared/` from a manifest; `--check` fails on a missing,
  edited or stray copy.
- Tests: `tests/test_design_lint.py` (25 fixtures under `tests/fixtures/design-md/`,
  every error check covered by an invalid fixture, every documented check exercised)
  and `tests/test_sync_shared.py` (fails when a catalog `impossible_css` id, confirmed
  control or property is missing from the profile).
- Three written briefs under `tests/briefs/design-md/`, scored by the linter plus a
  human read, as `docs/evals.md` now states. They are not automated.

### Changed (phase 02)
- `scripts/validate.py` runs `sync_shared.py --check`, lints the bundled example (must
  have zero findings) and the template (no errors, all eleven sections), and fails if a
  collection `DESIGN.md` is found in `skills/` or `tests/`.
- `scripts/skill_checks.py`: a skill may not point at the repository's `shared/`
  folder; it reads its synced copy instead.
- `NOTICE` records the Apache-2.0 DESIGN.md specification the new skill describes.
  Nothing from it is copied.

Phase 01 of 2.0.0: rename the plugin to `supersub`, rename the skill to `create-app`,
and move everything the skill runs into the skill's own folder. The conversion
behaviour is unchanged: the linter prints the same verdicts and `run_eval.py` prints
the same table as in 1.0.0.

### Changed -- BREAKING
- **Plugin renamed `power-app-yaml` -> `supersub`**, marketplace renamed the same way,
  version set to `2.0.0`. A plugin's `name` is its install identifier, so every
  existing install of `power-app-yaml@power-app-yaml` stops resolving. `supersub` will
  hold five skills; this phase ships the first.
- **Skill renamed `power-app-yaml` -> `create-app`** (`skills/create-app/`, frontmatter
  `name: create-app`). In Claude Code it runs as `/supersub:create-app`. Every trigger
  phrase in the description is kept.
- `.claude-plugin/marketplace.json`: top-level `description` added; `metadata`
  (`description`, `pluginRoot: "."`) removed, because `pluginRoot` only affects bare
  source names and has no effect next to `"source": "."`. A `renames` map
  (`"power-app-yaml": "supersub"`) records the rename as Claude Code's documented
  migration path for a renamed plugin entry.

### Moved
- `scripts/pa_lint.py`, `scripts/app_inventory.py`, `scripts/harvest_controls.py` ->
  `skills/create-app/scripts/`, and `docs/harvesting.md` ->
  `skills/create-app/references/harvesting.md`. **Why:** `SKILL.md` told Claude to run
  `scripts/pa_lint.py` and linked to `../../README.md` and `../../docs/harvesting.md`.
  Those paths exist only in a clone of this repository. Installed as a plugin the
  working directory is the user's project, and in chat only the skill's own folder is
  copied into the sandbox, so the lint step -- which the whole method depends on --
  could not be relied on outside this repo. The scripts now find their data through
  their own location (`Path(__file__).resolve().parent.parent`), so they work from any
  directory. `scripts/run_eval.py` and `scripts/validate.py` stay at the repo root:
  they are maintainer tools and never run inside an installed skill.

### Changed
- `SKILL.md` calls scripts as `python3 ${CLAUDE_SKILL_DIR}/scripts/<file>.py` and says
  that every path is relative to the skill folder. The `README.md` rationale link is
  gone and the harvesting link points at `references/harvesting.md`. Still under the
  8,192-byte budget (8,178).
- `references/*`, `assets/test-snippets/README.md` and the snippet `# Record` headers no
  longer point outside the skill (`docs/test-plan.md`, `CONTRIBUTING.md`,
  `scripts/validate.py`, `../../../docs/...`); they name those things in words instead.
  Comments only -- no catalog entry, pattern or snippet body changed.
- `scripts/validate.py` runs a new set of checks over **every** folder under
  `skills/` (in `scripts/skill_checks.py`): folder name equals frontmatter `name` and is
  kebab-case and at most 64 characters; description 40-650 characters; `SKILL.md` at
  most 8,192 bytes; no path in `SKILL.md`, `references/**` or `assets/**/*.md` leaves the
  skill; every `scripts/` and `references/` file `SKILL.md` names exists in the skill.
  Plus plugin-level checks: no top-level `bin/`, no root `CLAUDE.md`, `plugin.json` name
  is `supersub` and matches the marketplace entry. Tests: `tests/test_skill_checks.py`.
- The CHANGELOG check accepts a version that is newer than every released section and
  whose entries are still under `[Unreleased]`.
- README, CONTRIBUTING, docs, issue template, `LICENSE`, `NOTICE` and `SECURITY.md`:
  names, paths and install commands updated. GitHub URLs are unchanged until the
  repository itself is renamed.
- `.gitignore`: ignores the owner's `dev-prompts/`, local Claude Code state, the
  validator's scratch directories, root-level plugin packages (`*.zip`, `*.plugin`,
  `dist/`), tool caches and `.env` files.

### Migration from `power-app-yaml@power-app-yaml`
In Claude Code:

```bash
/plugin uninstall power-app-yaml@power-app-yaml
/plugin marketplace remove power-app-yaml
/plugin marketplace add YKUNAKORN/power-app-yaml
/plugin install supersub@supersub
```

The `renames` entry only maps the plugin name inside one marketplace; the marketplace
itself is also renamed, so remove and re-add it rather than relying on the automatic
migration. If you copied the skill folder by hand, replace `skills/power-app-yaml/`
with `skills/create-app/`. Anything that called `scripts/pa_lint.py` from a clone now
calls `skills/create-app/scripts/pa_lint.py`.

## [1.0.0] - 2026-09-11

Phase 5: make it possible to tell whether a change to the skill made output better or
worse -- and ship.

The first four phases each made the output more likely to be right: a catalog of what
actually pastes (0.2.0), an offline linter that proves it before the user sees it
(0.2.0), a harvester that grows the catalog from real exports (0.3.0), a pattern library
and a real geometry algorithm (0.4.0), and the branches for an app that already exists
and for data binding (0.5.0). None of them could answer the question that matters when
you edit `SKILL.md`: **did that help?** This release answers it, within a boundary it
states plainly rather than papering over.

### Added
- `tests/evals/` -- **five eval cases**, each a directory of three files: a small,
  self-contained `mockup.html` (no CDN, no webfont, no image file -- a fixture that
  needs the network is not a fixture), an `expectations.yaml` of assertions that can be
  settled mechanically on whatever `.pa.yaml` the skill produces, and a `notes.md`
  saying in prose what the case is meant to stress and which specific wrong answer it
  is there to catch.
  - `app-shell` -- persistent chrome. Nav rows drawn as plain text that must become
    `Classic/Button`s anyway (SKILL.md rule 5); a 4 x 48 active indicator that is a
    one-sided border by another name; `Navigate()` targets that cannot exist in a
    single-screen file and must therefore be commented.
  - `multi-section-form` -- `<select>` vs `<input>` fidelity, which is invisible in a
    rendered mockup and silently loses the constrained choice when got wrong; five
    structurally identical cards that must not be abbreviated; content running to
    ~2032px, so the screen has to declare `Height:`.
  - `card-grid` -- seventeen rows that all have to be there, per-row selection state,
    and `Gallery` forbidden precisely because it is the answer a Power Apps developer
    would reach for and the one this repo has no evidence for.
  - `shell-with-form` -- the seam. Sidebar coordinates from a fixed box, form
    coordinates from a wrapping flex grid, summary-panel coordinates from a stack of
    rows, all landing in one coordinate space; and read-only summary text that must not
    become editable fields.
  - `impossible-effects` -- **the deliberately hard one.** Every effect in the mockup is
    listed under `impossible_css` in `controls.yaml`: `box-shadow`, `backdrop-filter:
    blur`, CSS transitions, `group-hover`, `border-left` only, and a non-Segoe font.
    There is no right conversion, only a right disclosure, and the case separates the
    three ways to get it wrong -- fake it (an invented `BoxShadow:`), drop it silently,
    or declare it and offer the sanctioned substitute.
- `scripts/run_eval.py` -- the scorer.
  - `python scripts/run_eval.py OUTPUT.pa.yaml --case tests/evals/<name>` checks the
    file against that case and prints a pass/fail table. `--case` is required with an
    output file; the scorer never guesses which case a file belongs to.
  - Seven optional assertion blocks -- `structure`, `lint`, `controls`, `geometry`,
    `navigation`, `catalog`, `limitations`. Anything a case leaves out is reported
    `SKIP`, never assumed.
  - **Every count is a range.** Two good conversions of one mockup will not agree on
    control count, so an exact number would score style rather than correctness. Each
    range carries a comment giving its derivation from the mockup.
  - Six results, and three of them are not failures: `PASS`, `FAIL`, `XFAIL` (a
    deviation the case declared in advance, with a reason), `XPASS` (a declared
    deviation that stopped failing -- the waiver is stale, and this counts as a failure
    so it cannot be ignored), `UNPROVEN` (the evidence could not be gathered -- almost
    always `jsonschema` missing, which disables the layer that catches `PA1001`), and
    `SKIP`.
  - Geometry is resolved through the control tree, so a child's `X`/`Y` are measured
    against its ancestors, and a screen's own `Height:` overrides the canvas height --
    a screen that correctly declares it scrolls is not punished for it. A value that is
    not a plain number (`Width: =Parent.Width - 40`) is **counted, never guessed at**:
    placing it would mean evaluating Power Fx, which this tool does not do.
  - The catalog assertions reuse `pa_lint.py`'s own L2/L3 findings rather than
    reimplementing "an unverified item with no `# UNVERIFIED` comment", so the linter
    and the scorer cannot drift apart.
- `docs/evals.md` -- the manual loop, the table legend, what a case asserts, how to
  compare two runs, how to add a case, and a section titled **what the harness cannot
  see**: it renders nothing, so colour, font and visual hierarchy are unmeasured; it is
  not Studio, so only a paste test settles a control; and prose the model writes in chat
  is not in the file and cannot be scored.
- `tests/test_run_eval.py` -- 24 tests, mostly negative: an abbreviated screen fails on
  count and not on parse, a control past the canvas edge fails on geometry, the same
  control on a screen that declares a taller `Height` does not, a dangling `Navigate()`
  fails while a commented one passes, a file that will not parse produces exactly one
  `FAIL` row and not fifteen, and each of the three failure modes in the hard case lands
  on its own row. Plus the acceptance criterion as an assertion, and a test that the
  "not model-generated" disclaimer is still printed.
- `scripts/validate.py` -- eval-case checks, each negative-tested: all five archetypes
  present; every case has its three files; every mockup is self-contained; every
  `expectations.yaml` parses and asserts at least three blocks; **every known deviation
  states a reason** (a waiver nobody can read is indistinguishable from a bug); every
  reference output resolves; every `limitations.declared` id is one `controls.yaml`
  actually takes a position on; and `run_eval.py` is executed against the bundled
  references with the result asserted clean.

### Changed
- **`docs/quickstart.md` now has the lint step**, as step 4 of 6, with the four-layer
  table and the note that `jsonschema` is what separates `SAFE TO PASTE` from
  `UNPROVEN`. Also: the branch for an app that already exists, pasting the isolated
  snippets before the main file, and pointers to harvesting and evals.
- **`docs/troubleshooting.md` now explains the linter's verdict lines** alongside the
  PA-code table, and opens by separating the two sources of truth -- the linter is an
  approximation of Studio built from the bundled schema and this repo's catalog, and
  where they disagree Studio is right. Added: the four-layer table with the observation
  that L3 has *no* Studio counterpart and is therefore where the expensive silent
  failures live; why `PASTES, BUT n UNVERIFIED ITEM(S)` is not a failure; why `UNPROVEN`
  is deliberately not `SAFE`; and new entries for a control renamed to `_1`, a
  non-`ManualLayout` container ignoring child `X`/`Y`, and pasting into an app that
  already exists.
- `README.md` -- new sections "Verify before you paste" and "Telling better output from
  worse"; the repository layout now shows `tests/` broken out; the `impossible_css`
  paragraph names the full list and its file; and "what it can't do" now also admits
  that nothing renders and the linter is not Studio.
- `CONTRIBUTING.md` -- a section saying that a change to `SKILL.md`, the catalog or the
  patterns needs a before-and-after eval run in the PR, and the same as a checklist item.
- `.github/workflows/validate.yml` -- runs `python scripts/run_eval.py` as its own step.
  **No API key, by design**: the scored half needs no model, and a workflow that quietly
  depended on a key would be green on every run where the key was missing.
- **The three bundled examples gained comments, and nothing else.** Twelve `Navigate()`
  lines now say on the line that the target is not a screen in this file (SKILL.md rule
  7), and five `FontWeight` properties on `Classic/Button` in `example-app-shell.yaml`
  are tagged `# UNVERIFIED` (rule 8). This clears 17 of the 22 warnings recorded as a
  known issue in 0.2.0. The change is comment-only -- no geometry, no property values,
  no line-count change -- so the line ranges in `INDEX.md` and the patterns extracted
  from these files are unaffected. It matters because a model reading an example copies
  what it sees, including an uncommented dangling `Navigate()`.
  - `example-form.yaml` and `example-card-grid.yaml` now lint **SAFE TO PASTE**.
- `plugin.json` version 0.5.0 -> 1.0.0.

### Fixed
- `LICENSE` needed no change: the copyright line has read
  `Copyright (c) 2026 YKUNAKORN (https://github.com/YKUNAKORN)` since the repackaging
  commit, and the README sentence that once said to fill it in was removed in that same
  commit. Recorded here because the phase brief expected a placeholder and there is not
  one.

### Known issues
- **`FontWeight` on `Classic/Button` is still unresolved.** `controls.yaml` confirms it
  on `Label` only and marks it explicitly unverified on `Button`;
  `example-app-shell.yaml` uses it on five Buttons. Tagging them settles the *labelling*
  question, not the *evidence* question -- the file still lints
  `PASTES, BUT 5 UNVERIFIED ITEM(S)`, and the `app-shell` eval case carries three
  declared deviations because of it. One Studio paste test settles all of it; delete the
  waivers when it does.
- **The scorer cannot see whether the screen looks like the mockup.** Nothing renders.
  Colours, fonts, alignment and visual hierarchy are unmeasured, and a conversion with
  every control in the right place and the wrong palette scores full marks. Stated in
  `docs/evals.md` under "what the harness cannot see" rather than left to be discovered.
- **The reference outputs are not model output.** The three bundled examples were
  hand-written long before this harness and are used only so the scorer can be exercised
  in CI. A green self-check proves the assertions run; it says nothing about the skill's
  output quality, and `run_eval.py` prints that on every run.
- **A limitation declared in chat rather than in the file scores `FAIL`.** The scorer
  reads the `.pa.yaml`, and a `#` comment is the only channel a `.pa.yaml` has. This is
  a real limit of the harness, and it is also the behaviour worth having: whoever pastes
  the file in six months has the file, not the conversation.
- All twelve rows of `docs/test-plan.md` remain empty, `controls.yaml` is byte-identical
  to 0.3.0, and `studio_version_tested` is still `unknown`. Nothing in this phase could
  be confirmed against Studio, because nothing in this phase touched Studio.

## [0.5.0] - 2026-09-11

Phase 4: make the skill useful on an app that already exists, and prepare -- without
assuming -- data binding and the modern layout controls.

### Added
- `scripts/app_inventory.py` -- a one-page summary of an app that already exists, so
  the export never has to be pasted into the conversation.
  - `python scripts/app_inventory.py SRC [--json] [--names] [--max-bytes N]`. SRC is a
    folder of `.pa.yaml`, a single file, or an `.msapp` (read in memory, `src/**/*.pa.yaml`
    only -- everything outside `src/` is build output and is ignored).
  - Reports: screens in `EditorState.ScreensOrder` order when the export has one and
    says so when it does not; per screen the controls and their nesting depth, never
    property values; the control types **with the `@version` that app uses**, which is
    what a new screen has to match; `Set`/`Collect`/`ClearCollect` targets from
    `App.OnStart` with the value when the value is a literal and `~expr` when it is not;
    `DataSources:` entries with their `Type:`; `ComponentDefinitions:` names; and a
    collision list of every screen and control name already taken.
  - **The byte budget is the feature.** The text summary is capped at 2048 bytes. Rather
    than overflow, the tool steps down a ladder of detail -- every control, then controls
    grouped by type, then bare names, then counts, then name prefixes -- and its last
    line states which level it used. The 10-screen, 171-control fixture in
    `tests/apps/ten-screen-app/` (96 KB of source) summarises in 1,807 bytes; the three
    bundled examples (270 controls) in 1,023. `--json` and `--names` are unbudgeted.
  - It never evaluates Power Fx. `Set(varUserEmail, User().Email)` is reported as
    `varUserEmail=~expr`, not as a guessed value -- a half-evaluated formula would be
    worse than no value.
- `skills/power-app-yaml/references/extend-existing-app.md` -- the procedure branch for
  a host app: get an export, run the inventory first, read the naming convention off it
  and match it, check every new name against the collision list, `Navigate()` only to
  screens the inventory lists, reuse the `App.OnStart` theme variables instead of
  re-hardcoding hex, and paste onto a **new blank** screen. Each step names the silent
  failure it prevents -- all six fail by succeeding, which is worse than `PA1001`.
- `skills/power-app-yaml/assets/test-snippets/` -- **the paste-test kit**: twelve
  single-control files covering Gallery, Form, DataTable, Toggle, DatePicker, ComboBox,
  Slider, Timer, CheckBox, HtmlText and the modern layout containers. Each is a complete
  `Screens:` wrapper with exactly one control, geometry above a bisect marker and the
  unverified properties below it, **one property per line** so a failure is bisected by
  deleting lines. Every file states where its property names came from, what the paste
  test is, and where to record the answer.
  - Property names are taken from Microsoft's published per-control reference (mirrored
    in `MicrosoftDocs/powerapps-docs`, retrieved 2026-09-11), so they are real Power Fx
    property names -- which is **not** the same as confirmed for a `.pa.yaml` paste, and
    each header says so.
  - No `@version` is written on the bare ids: this repo has no evidence for one, and an
    invented version number is the exact failure mode the project exists to prevent. The
    schema makes the version optional, so the bare id is legal to write.
  - Enum-valued properties are mostly left out on purpose -- `Format:
    =DateTimeFormat.ShortDate` stacks a guess about the enum member on a guess about the
    property name, so a failure would not say which half was wrong. Where an enum was
    unavoidable the header says so and suggests trying a plain number first.
- `docs/test-plan.md` -- the results worksheet: a row per snippet with Studio version,
  result, failing properties and date; a result-code table (`OK`, `OK/ver X`,
  `PA2108 <Prop>`, `PA1001`, `UNKNOWN-ID`, `OTHER`) chosen so each code implies a
  different next step; a suggested test order; and a paragraph on exactly what to write
  into `controls.yaml` and `confirmed-controls.md` for each outcome -- including that a
  property which failed goes to `properties_unverified` with the Studio version that
  rejected it, never to a "does not support" list.
- `skills/power-app-yaml/references/data-binding.md` -- SharePoint lists, `Gallery.Items`,
  `User().Email` filtering, two sites, `SubmitForm`, `Patch` and calling a Power Automate
  flow, every expression marked **UNVERIFIED** and every section naming the paste test it
  is blocked on. Three confidence markers are kept apart: SCHEMA-VERIFIED (checked here
  against the bundled schema, with the command to re-check), DOCUMENTED (in Microsoft's
  reference, never pasted here) and UNVERIFIED.
- `tests/apps/ten-screen-app/` -- a synthetic 10-screen, 171-control app with a
  deliberately non-alphabetical `EditorState.ScreensOrder`, literal and non-literal
  `App.OnStart` variables, three `DataSources:` entries and two components.
- `tests/test_app_inventory.py` -- 33 tests, including the acceptance criterion as an
  assertion (10-screen app under 2 KB), that the tier really is chosen by fit, that
  `ScreensOrder` is honoured and its absence admitted, that non-literal values are never
  guessed, that `--names` reaches controls three levels deep, and that an `.msapp`
  produces the same inventory as the unpacked folder.

### Changed
- **`SKILL.md` gains two branches and stays under its 8 KB budget** (8,169 bytes): "the
  app already exists" points at `app_inventory.py` + `extend-existing-app.md`, and
  "anything data-bound" at `data-binding.md` plus the matching test snippet. Paid for by
  trimming rationale prose that `README.md` already carries, not by dropping procedure.
  `scripts/validate.py` now also checks that these two pointers survive future shrinking.
- `scripts/validate.py` -- new checks, each one negative-tested: every test snippet
  carries the full header, parses, and contains **exactly one control** (two would make a
  failure unattributable); every snippet has no L0/L1 error **and raises at least one L2
  warning** (a snippet that lints clean is either catalogued already or the catalog moved
  under it); every snippet has a row in `docs/test-plan.md`; every `yaml`/`text` example
  in `data-binding.md` is marked UNVERIFIED, every snippet it names exists, and its YAML
  blocks are extracted and linted; and `app_inventory.py` is run against the 10-screen
  fixture with its output size asserted under 2 KB and its sections asserted present.
- `README.md` gains "Working with an app that already exists" and "The paste-test kit",
  and the repository layout covers the new files.
- `CONTRIBUTING.md` points a control test report at the ready-made snippet and at
  `docs/test-plan.md`.
- `plugin.json` version 0.4.0 -> 0.5.0.

### Not changed, on purpose
- **`controls.yaml` is byte-identical.** Not one of the twelve controls entered the
  catalog in this phase. They enter it when a real Studio result exists and not before,
  which is the entire point of shipping the kit instead of the entries.

### Known issues
- **The modern layout containers' type ids are unknown and are not guessed.** Microsoft's
  own first-party control-id enum (mirrored in `control-ids-candidate.yaml`) contains
  `GroupContainer` and contains no `Container`, `HorizontalContainer` or
  `VerticalContainer`; community-written Power Apps YAML material uses a bare
  `Container`. The two cannot both be right, so the kit ships both hypotheses with the
  unknown part as a clearly marked placeholder -- the `Variant:` string in
  `container-auto-layout-a-variant.pa.yaml`, the `Control:` id in
  `container-auto-layout-b-typeid.pa.yaml` -- and says plainly that the cheapest test is
  to insert a container in Studio and read its own code back, which settles the id, the
  version and the variant at once.
- The layout-property names in that snippet come from three sources of different
  strength, and the file says which is which: `LayoutDirection` and `LayoutAlignItems`
  are named verbatim in the prose of Microsoft's published Horizontal container
  reference; `LayoutMinWidth` and `FillPortions` appear in `microsoft/PowerApps-Tooling`
  issue #224, which describes an **older** source format; `LayoutGap`,
  `LayoutJustifyContent`, `LayoutWrap` and `LayoutOverflowY` are in common community use
  with no first-party citation found.
- **The bundled v3.0 schema's `DataSources` block has no SharePoint-shaped entry.**
  `Type` is an enum of exactly `Table` and `Actions`; the `Table` branch allows only
  `Parameters.TableLogicalName`, which is Dataverse vocabulary. `ConnectorId` is declared
  under `properties` and then rejected by both `oneOf` branches, which reads like an
  upstream bug. How Studio actually serialises a SharePoint list is unverified, and
  `data-binding.md` says to read it off a real export rather than infer it.
- Whether "Paste code" accepts a file carrying a top-level `DataSources:` block at all --
  as opposed to ignoring it or refusing the paste -- is untested. `data-binding.md` takes
  the conservative reading that connections are a manual Studio step.
- Every expression in `data-binding.md` remains UNVERIFIED, and all twelve rows of
  `docs/test-plan.md` are empty. Nothing in this phase was confirmed against Studio,
  because nothing in this phase could be.

## [0.4.0] - 2026-09-11

Phase 3: cut what the skill costs to run, and give it a real algorithm for the
hardest part of the job — turning HTML/CSS into absolute X/Y.

### Added
- `skills/power-app-yaml/assets/patterns/` — 13 pattern snippets, each a standalone
  `.pa.yaml` that lints **SAFE TO PASTE**, each opening with a header naming what it
  is, which controls it uses, the example file and **line range** it was extracted
  from, and its evidence level: `screen-shell`, `sidebar-nav-item`, `top-bar`,
  `card-container`, `section-header`, `form-field-text`, `form-field-dropdown`,
  `tile-grid-cell`, `badge`, `divider`, `avatar-row`, `footer-nav`,
  `two-column-split`. Every one is **extracted** from the three bundled examples, not
  invented; the headers cite the source lines so any claim is re-checkable.
  - `radio-group` was requested and is **not included**: no bundled example contains a
    `Classic/Radio`, so there was nothing to extract. `empty-state` likewise — no
    example has an empty/zero-results region.
  - `divider` carries an explicit HONEST SCOPE note: the thin-`Rectangle` *mechanism*
    is extracted verbatim (`recDot1`, 48 × 4; `recNavActiveIndicator`, 4 × 48) but the
    *role* of a full-width section rule has no precedent in any example.
- `skills/power-app-yaml/assets/examples/INDEX.md` — per example: a one-paragraph
  description, a control inventory with counts, and the line ranges of every notable
  region, mapped to the pattern that covers it. Lets a 40-line slice be read instead of
  a 1,732-line file. Plus a cross-file table for the sidebar / top bar / progress
  regions that repeat in all three.
- `skills/power-app-yaml/references/layout-mapping.md` — the geometry reference.
  Canvas sizing and the scale factor (with the rounding rule and the row-closing
  check); Tailwind→px tables for spacing, text sizes and line heights, font weights,
  `rounded-*` and border widths, each under a standing warning that they are Tailwind
  **defaults** and the mockup's own config wins; flex row/column → cumulative
  coordinates covering every `justify-*` and `items-*` and `flex-1`; grid → column
  width math with gutters, residue handling and `col-span`; the nesting arithmetic
  (not just the rule); vertical overflow → how to compute the screen's `Height`; and a
  fully worked 3-column `gap-6` `p-8` card grid from a 1440px mockup down to the exact
  `X`/`Y`/`Width`/`Height` of every control, with the arithmetic shown at each step.
  - **The 1366 × 768 canvas assumption is labelled.** It is *sourced* from the bundled
    examples' own geometry (top bar `X: =280` + `Width: =1086` = 1366; sidebar
    `Height: =768`). The separate claim that this is Power Apps' *documented default*
    for a tablet-format app is marked **UNVERIFIED** — no citation exists in this repo
    — with an instruction to confirm it from Studio → Settings → Display.
  - Nothing in the file recommends a property absent from `controls.yaml`, and
    `scripts/validate.py` now enforces that mechanically.
- `confirmed-controls.md` gains a "Linter warnings about a control type" section: the
  `L2.unverified-control-type` / `L2.candidate-control-type` table moved out of
  SKILL.md, where it was costing context on every invocation.
- `README.md` gains "How the skill spends its context" — the per-file read budget, why
  the pattern library exists, and why `layout-mapping.md` exists. This is the rationale
  prose moved out of SKILL.md.

### Changed
- **`SKILL.md` rewritten: 14,371 → 7,987 bytes, under the 8 KB budget.** It is now
  procedure only — workflow, control picker, templates, rules, defaults, hand-off,
  checklist. The new step order is: read the catalog → pick the pattern(s) → apply
  `layout-mapping.md` → open a full example *only* if the patterns don't cover it, and
  then only a slice via `INDEX.md` → write → **lint** → hand off. "Why a whole skill
  for just YAML" and the design philosophy moved to `README.md`.
- **Frontmatter `description` tightened 917 → 642 characters with every trigger phrase
  kept** (HTML/CSS mockup, Google Stitch, v0, Figma export, UI screenshot, design
  export, `.pa.yaml`, source schema v3.0, "Paste code", blank screen, Power Apps Studio,
  "convert this to pa.yaml", "make this a Power Apps screen", "turn this design into
  code I can paste into Power Apps", "even without the term .pa.yaml", fix, debug, failed
  to paste, `PA1001`, `PA2108`, add a new screen to an existing app, extend a screen made
  this way). The only thing cut is the closing justification sentence — "carries a catalog
  of control types and properties that are confirmed to work versus merely guessed — the
  #1 cause of paste failures" — which sells the skill rather than triggering it; the rest
  of the saving is wording. "wireframe" was added: it appears in README's audience list
  and was the one plausible trigger the description lacked.
- `scripts/validate.py` — new checks: every `assets/patterns/*.pa.yaml` lints with
  verdict SAFE TO PASTE (not merely exit 0); every pattern header carries
  PATTERN/What/Controls/Source/Evidence **and cites a real bundled example**; pattern
  line counts stay in budget (`tile-grid-cell` is a declared exception at 90, being a
  six-control composite); SKILL.md stays under `SKILL_MD_MAX_BYTES` **and** still
  contains the workflow, picker, templates, rules and checklist plus its pointers; the
  frontmatter description stays under `DESCRIPTION_MAX_CHARS`; `layout-mapping.md` and
  `SKILL.md` name no property absent from `controls.yaml`; and the worked example's
  YAML block is extracted and linted on every run, so it cannot drift.
- `plugin.json` version 0.3.0 → 0.4.0.

## [0.3.0] - 2026-09-10

### Added
- `scripts/harvest_controls.py` — grows the control catalog from real Power Apps Studio
  exports instead of one hand-fed paste test at a time.
  - Reads a `.pa.yaml` file, a folder of them, or an `.msapp` (unzipped in memory,
    `src/**/*.pa.yaml` only). Walks `Screens:` and `ComponentDefinitions:` recursively
    through nested `Children:`.
  - Records per control type: version, `Variant`, whether `Children` was seen, every
    property name observed, occurrence count, and the source files.
  - Emits a `controls.yaml` fragment with `evidence: studio-export` and
    `source: "<file> (harvested <date>)"`.
  - `--merge` folds the fragment into `controls.yaml` **as text**, so every comment in
    the file survives: it adds new controls, unions new property names into
    `properties_confirmed` (keeping the hand-written order, with a `# harvested <date>`
    provenance comment), and never overwrites a hand-written `notes`, never downgrades a
    `studio-tested` entry, and never removes anything. Conflicts — same control at a
    different version, a mismatched `Variant`, `Children` the catalog says cannot exist,
    a control id with no `@version` — are reported and left alone; the run exits 2.
    A merge with nothing to change does not write the file at all.
  - `--report` prints a coverage diff in both directions, `--out` writes the fragment,
    `--dry-run` reports a merge without performing it.
- `docs/harvesting.md` — both extraction routes (Power Platform CLI and manual `.msapp`
  unzip) with exact flags, where `src/` lives, how to run the harvester, a checklist for
  reviewing a merge diff before committing, and how to report a result upstream through
  the `control-report.yml` issue template.
- `skills/power-app-yaml/references/control-ids-candidate.yaml` — Microsoft's 62-entry
  first-party control-id enum, mirrored from `microsoft/PowerApps-Tooling`
  (`src/schemas/pa-yaml/v3.0/ControlLibraryVDev/ControlTypeId-1P-controls-enum.schema.yaml`
  @ `aed72a3`, 2026-08-24). **Every entry is marked `evidence: unverified`** and
  `scripts/validate.py` fails if one is not.
- `scripts/pa_lint.py`: new L2 check `L2.candidate-control-type`. A control type absent
  from the catalog but present in that enum now reads "known to Microsoft's tooling but
  not yet paste-tested here" instead of "unknown control". Same WARNING severity, same
  `# UNVERIFIED` tagging requirement, same generated paste-test snippet — the enum is a
  wording aid, never evidence. New `--candidates PATH` flag; a missing file degrades to
  the old wording rather than failing.
- `scripts/validate.py`: checks for the harvester, `docs/harvesting.md`, the candidate
  file's provenance keys and its all-`unverified` invariant, and a new catalog rule that
  a control cannot be both catalogued and listed in `unattempted_controls`.
- `tests/test_harvest_controls.py` — 21 tests covering the acceptance criteria directly
  (the bundled examples reproduce the 8 catalogued control types with zero conflicts; a
  merge against an unchanged catalog is byte-identical; comments, `notes` and evidence
  levels survive a real merge; conflicts exit 2 and change nothing), plus `.msapp`
  reading and the absence-caveat invariants.
- `tests/fixtures/invalid/candidate-control-type.*` — fixture for the new L2 check.

### Changed
- `controls.yaml` now opens with **THE ABSENCE CAVEAT** as a prominent top-level comment:
  Studio only serialises properties whose value differs from the default (Microsoft's own
  wording), so a property missing from an export — or from this catalog — is not evidence
  that the control lacks it. The harvester enforces the same rule mechanically: it never
  writes `properties_unverified`, never emits a "does not support" list, and labels its
  "never exercised by this export" report section as untested, not unsupported.
- `SKILL.md`, `README.md` and `CONTRIBUTING.md` document the harvesting route and the
  two control-type warnings the linter can now raise.
- `plugin.json` version 0.2.0 → 0.3.0.

### Known issues
- The Power Platform CLI route (`pac canvas list` / `pac canvas download -d`) is
  **documented from Microsoft's reference but not verified against a real tenant** by
  this repo. `docs/harvesting.md` says so at the top of that section, and the manual
  `.msapp` unzip route is a complete substitute that needs no CLI.
- The mirrored control-id enum disagrees with this repo's own Studio tests about the
  `Classic/` prefix: it lists bare `Button`, `TextInput`, `DropDown` and `Radio`, while
  `controls.yaml` records `Classic/Button@2.2.0`, `Classic/TextInput@2.3.2`,
  `Classic/DropDown@2.3.1` and `Classic/Radio@2.3.0` from paste tests. Unresolved, and
  recorded in `docs/harvesting.md`; it is one of the reasons nothing in that file is
  treated as evidence.
- Harvesting `assets/examples/` surfaces `FontWeight` on `Classic/Button` as *held back*:
  the examples use it, but `controls.yaml` explicitly flags it unverified there. The
  merge will not promote it. Still needs the Studio paste test noted in 0.2.0.

## [0.2.0] - 2026-09-10

### Added
- `skills/power-app-yaml/references/controls.yaml` — machine-readable control catalog,
  now the single source of truth. `confirmed-controls.md` is the human-readable view of
  the same facts; `scripts/validate.py` fails if the two drift apart.
- `scripts/pa_lint.py` — an offline verification loop that proves a `.pa.yaml` before it
  reaches the user, instead of the user acting as the compiler:
  - **L0** YAML parse, with line/column and a special case for flow-style `Properties`
    containing `RGBA(...)`.
  - **L1** JSON Schema against the bundled Microsoft v3.0 schema (ERROR, maps to
    `PA1001`), with raw `jsonschema` messages translated into human sentences carrying a
    YAML path.
  - **L2** catalog lint (WARNING, maps to `PA2108`) for unverified control types and
    properties, each shipping a generated isolated paste-test snippet.
  - **L3** convention checks from SKILL.md's own rules: unreachable `Navigate()` targets,
    duplicate control names, child `X`/`Y` under a non-`ManualLayout` container, and
    untagged unverified items.
- `tests/` — 14 fixtures with `.expected.json` sidecars and a stdlib `unittest` suite
  asserting on check ids rather than message wording.
- CI now installs `jsonschema` and runs `python -m unittest discover tests`.

### Changed
- `SKILL.md`: running `scripts/pa_lint.py` is now a mandatory workflow step before
  handing a file over, and appears in the pre-send checklist.

### Known issues
- `controls.yaml` records `studio_version_tested: unknown` — `confirmed-controls.md`
  names no Studio build, so no honest value exists yet.
- Linting the bundled examples surfaces 22 pre-existing warnings and 0 errors: 12
  `Navigate()` calls to screens outside their own single-screen file, 5 uses of
  `FontWeight` on `Classic/Button` that contradict the catalog's explicit "not verified
  on Button" note, and the 5 untagged-item warnings that follow from those. Left as-is
  because the example files are out of scope for this phase.

## [0.1.0] - 2026-08-27

### Added
- Initial public release of the `power-app-yaml` Claude skill.
- Workflow, control picker, fill-in templates, and pre-send checklist in
  `skills/power-app-yaml/SKILL.md`.
- Empirical control catalog `skills/power-app-yaml/references/confirmed-controls.md`,
  built from real Power Apps Studio paste tests.
- Bundled Microsoft `pa.yaml` v3.0 schema for offline reference (see `NOTICE`).
- Three real, paste-tested example screens under
  `skills/power-app-yaml/assets/examples/` (app shell, form, card grid).
- Claude Code plugin packaging: `.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json`.
- Repository documentation: `README`, `docs/quickstart.md`,
  `docs/troubleshooting.md`.
- Community health files: `CONTRIBUTING`, `CODE_OF_CONDUCT`, `SECURITY`,
  `SUPPORT`, GitHub issue/PR templates.
- CI: `scripts/validate.py` and `.github/workflows/validate.yml`.

[Unreleased]: https://github.com/YKUNAKORN/power-app-yaml/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/YKUNAKORN/power-app-yaml/compare/v0.5.0...v1.0.0
[0.5.0]: https://github.com/YKUNAKORN/power-app-yaml/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/YKUNAKORN/power-app-yaml/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/YKUNAKORN/power-app-yaml/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/YKUNAKORN/power-app-yaml/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/YKUNAKORN/power-app-yaml/releases/tag/v0.1.0
