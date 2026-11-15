# Case: multi-screen-mock

## What this stresses

The pipeline branch of `create-app`: a `mock-ui` mockup folder in, one `.pa.yaml` per
screen out, with the screens wired to each other. The input is the three-screen Kitroom
example that ships with `mock-ui` (`supersub/mockup/`, a copy of
`skills/mock-ui/assets/example/`): a loan list, a new-loan form and a loan detail, all
sharing one sidebar and top bar.

Specifically:

- **One file per screen.** `structure.screens` is exactly 1. Three screens in one file
  is the single-mockup habit; the pipeline hands over a folder.
- **Real navigation, not placeholders.** Each `data-nav` becomes `Navigate()` to a
  screen id in `sitemap.json`. Scoring one file alone would call those dangling, so the
  case names the sitemap (`navigation.sitemap`) and a target in it resolves. A target
  in neither the file nor the sitemap is still a failure, and so is a lint warning: the
  linter gets the same screen list.
- **Data hints stay static.** `data-repeat="Loans"` on the list and `data-source` on
  the form and detail card are drawn as sample controls. `Gallery`, `Form` and
  `DataTable` are forbidden: they are unattempted in the catalog, and a conversion that
  emits one has guessed.
- **The detail panel is marked `data-unsupported="box-shadow"`.** The reference keeps
  the panel's 1px border as the substitute and says so in a comment. The case does not
  assert it with a `limitations` block, because the same assertions run on all three
  files and only one of them carries the mark. Check it by hand (below).

## Why one file at a time

`run_eval.py` scores one `.pa.yaml` against one case. Scoring a folder would mean a
second shape of case, per-screen expectation blocks and a reference list instead of
one reference: a redesign of the scorer, which this case does not attempt. Instead:

1. Each screen file is scored on its own against the assertions here, which hold for
   all three screens.
2. What only shows across files is the linter's job:

   ```bash
   python skills/create-app/scripts/pa_lint.py --app-dir <app dir> \
       --sitemap tests/evals/multi-screen-mock/supersub/mockup/sitemap.json
   ```

   That compares control names across the screens (`L3.duplicate-control-name-in-app`)
   and checks that no screen id is defined twice (`L3.duplicate-screen-in-app`).
   `tests/test_pa_lint.py` runs it on the reference app and on fixtures that collide.

## Running it on a fresh conversion

1. In a session with the plugin loaded: *Convert the mock-ui mockup in
   `tests/evals/multi-screen-mock/supersub/mockup/` to Power Apps screens.*
2. Save the files it hands back into one folder, for example `/tmp/run1/app/`.
3. Score each screen, then lint the folder:

   ```bash
   for f in /tmp/run1/app/*.pa.yaml; do
     python scripts/run_eval.py "$f" --case tests/evals/multi-screen-mock
   done
   python skills/create-app/scripts/pa_lint.py --app-dir /tmp/run1/app \
       --sitemap tests/evals/multi-screen-mock/supersub/mockup/sitemap.json
   ```

4. Check by hand what neither tool asserts:
   - there are exactly three files, named `scrLoanList`, `scrNewLoan`, `scrLoanDetail`;
   - `PASTE-ORDER.md` is there and says to create every screen before judging a
     `Navigate()` error;
   - `scrLoanDetail` names `box-shadow` in a comment and keeps the panel's border;
   - each action button (`Apply`, `Send request`, `Mark returned`, `Report lost`) has a
     placeholder `OnSelect` with a comment naming its `data-action`;
   - the hand-off names `create-list` and `create-flow`.

## Reference output

`supersub/app/` holds the three screens and `PASTE-ORDER.md`. They were written in the
Phase 04 working session by following `SKILL.md` and `references/from-mock-ui.md`, with
the mockup in view: one sample, **not** a fresh-session model run. They lint
`SAFE TO PASTE` as one app with the sitemap. The case scores `scrLoanDetail` in the CI
self-check; the other two pass the same assertions when scored by hand.
