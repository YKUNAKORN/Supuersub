# create-app in depth

The detail behind the `create-app` skill: why `.pa.yaml` needs a skill, how the skill
spends its context, the linter, the existing-app branch, the paste-test kit, the catalog
and the evals. This was the body of the README before the plugin held five skills; the
README now has one short section per skill and links here.

The `mock-ui` branch (a mockup folder in, one file per screen out) is in
[`references/from-mock-ui.md`](../skills/create-app/references/from-mock-ui.md).

## Why a skill for "just YAML"

`.pa.yaml` is narrow, version-pinned, and full of naming quirks you cannot derive from web intuition:

- `Label` has **no** prefix, but `Classic/Button` has a `Classic/` prefix.
- `Icon` and `Classic/Icon` are **different controls** with different capabilities.
- Every property value must start with `=`, and commas inside `RGBA(...)` break flow-style YAML.

The method is: **use only what's confirmed, label every guess honestly, and let the user paste-test
small pieces before trusting them.**

## Designed to run on a small model

The instructions are an ordered workflow, lookup tables, fill-in templates, and a pre-send checklist
rather than prose you have to reason through. You can run it on a lightweight/low-effort model and
still get output that pastes cleanly, because the hard-won specifics (which control, which version,
which properties) are looked up, not derived.

## How the skill spends its context

`SKILL.md` is procedure only — workflow, control picker, templates, rules, checklist —
and it is kept under 8 KB on purpose. Everything else is loaded on demand, cheapest
first:

| Read | Size | When |
|---|---|---|
| `references/controls.yaml` | ~10 KB | Always. The catalog of what works. |
| `assets/patterns/*.pa.yaml` | 30–85 lines each | Always. Pick only the patterns the mockup needs. |
| `references/layout-mapping.md` | ~26 KB | Whenever geometry has to be derived from HTML/CSS. |
| `assets/examples/INDEX.md` | ~7 KB | To find a line range before opening an example. |
| `assets/examples/*.yaml` | 3,234 lines total | Last resort, and as a slice, never whole. |

The reason for the pattern library: `example-card-grid.yaml` is 1,732 lines, and the
pattern actually worth learning from it lives in about 85 of them — the other 95% is the
same card repeated 16 more times. Reading the catalog *and* the nearest example in full
used to cost roughly 20k tokens before the first line of output. The patterns are
extracted from those same example files (each one cites its source file, line range and
evidence level), so they are not a second source of truth — they are the same evidence,
addressable in 40 lines instead of 1,700.

`layout-mapping.md` exists because turning flex/grid/Tailwind into absolute
`X`/`Y`/`Width`/`Height` is the step a model is most likely to fake. There is no
confirmed flex, grid, gap or padding property in Power Apps canvas YAML, so the geometry
has to be resolved into numbers by arithmetic, once, at authoring time.

## Verify before you paste

`skills/create-app/scripts/pa_lint.py` is the step that stops the user acting as the compiler. It runs
offline, in four layers, and ends in a verdict:

```bash
python skills/create-app/scripts/pa_lint.py myscreen.pa.yaml
```

| Layer | Severity | Checks | Studio equivalent |
|---|---|---|---|
| **L0** | error | the file parses as YAML | a paste that silently does nothing |
| **L1** | error | Microsoft's bundled v3.0 schema | `PA1001` — blocks the whole paste |
| **L2** | warning | this repo's control catalog | `PA2108` — unknown control or property |
| **L3** | warning | SKILL.md's own conventions | **nothing** |

L3 is the layer with no Studio counterpart, and it is where the expensive failures
live: a duplicate control name is silently renamed to `_1` on paste, so the names you
wrote and the names in the app quietly diverge. Nothing errors. The app is just wrong.

Four verdicts are possible — `SAFE TO PASTE`, `PASTES, BUT n UNVERIFIED ITEM(S)`,
`WILL FAIL`, and `UNPROVEN` (which is what you get when `jsonschema` is not installed
and the layer that catches `PA1001` never ran; reporting "safe" there would be a claim
the run cannot back up). Each one, and what to do about it, is in
[`docs/troubleshooting.md`](troubleshooting.md#the-linters-verdict-lines).

The linter is an approximation of Studio, built from the bundled schema and a catalog
of paste-tested controls. Where the two disagree, Studio is right — and that
disagreement is worth reporting, because it is how the catalog grows.

## Working with an app that already exists

Adding a screen to a real app fails in ways a blank canvas cannot: a control name that
collides is silently renamed to `_1`, a `Navigate()` goes to a screen that was never
there, and the palette gets hard-coded a second time next to the theme variables
`App.OnStart` already defines. All three are silent — the paste succeeds and the app is
subtly wrong.

```bash
python skills/create-app/scripts/app_inventory.py <Src-folder-or-.msapp>
```

About a page: screens in editor order, controls per screen with nesting depth, the
control types **with the versions that app uses**, the `App.OnStart` variables with
their literal values, the `DataSources:` entries, the components, and every name already
taken. The export itself is tens of thousands of tokens of property values nobody is
going to read, so the tool has a hard byte budget and drops to coarser detail rather
than overflowing it; `--json` and `--names` are the unbudgeted escape hatches. The
procedure that uses it is
[`references/extend-existing-app.md`](../skills/create-app/references/extend-existing-app.md).

## The paste-test kit

Gallery, Form, DataTable, Toggle, DatePicker, ComboBox, Slider, Timer, CheckBox,
HtmlText and the modern layout containers are **not** in the catalog, and this repo has
no evidence about any of them. Guessing is what the project exists to avoid, so instead
[`assets/test-snippets/`](../skills/create-app/assets/test-snippets/) holds one
single-control file per control, each a complete `Screens:` wrapper with one property per
line so a failure can be bisected by deleting lines. Results go in
[`docs/test-plan.md`](test-plan.md), and only a real Studio result puts a control in
the catalog.

The layout containers are the honest gap: Microsoft's own control-id enum lists
`GroupContainer` and no `Container` / `HorizontalContainer` / `VerticalContainer`, while
community guides use a bare `Container`. Rather than pick one, the kit ships both
hypotheses with the unknown part marked as a placeholder, and says the cheapest test is
to insert a container in Studio and read its own code back.

## Keep the catalog honest

Everything in `skills/create-app/references/confirmed-controls.md` was confirmed by pasting into a
specific version of Power Apps Studio. Studio pins control versions, so a newer Studio may emit
different version numbers (it will warn and auto-substitute). **When your own Studio confirms or
corrects something, update your copy of the catalog** — and, ideally,
[report it](https://github.com/YKUNAKORN/power-app-yaml/issues/new?template=control-report.yml) so
everyone benefits. Anything not in the catalog is treated as unverified by design.

**Grow the catalog from a real export.** If you can download your app's source — `pac canvas
download -d <dir>`, or just unzip the `.msapp` — the `.pa.yaml` files under `src/` are Studio's own
output, and `skills/create-app/scripts/harvest_controls.py` turns them into catalog entries:

```bash
python skills/create-app/scripts/harvest_controls.py ./myapp/src --report   # what's new, what's untested
python skills/create-app/scripts/harvest_controls.py ./myapp/src --merge    # fold it in, then review the diff
```

One caveat governs all of it, and Microsoft documents it: *only properties that differ from the
default values are serialized.* **A property missing from an export is not evidence that the
control lacks it** — so the harvester only ever makes positive claims, and never writes a "does not
support" list. Full walkthrough, both extraction routes, and the review checklist:
[`references/harvesting.md`](../skills/create-app/references/harvesting.md).

## Telling better output from worse

The linter proves a file will paste. It cannot tell you whether the screen is the one
the mockup showed, and it cannot tell you whether an edit to `SKILL.md` helped or hurt.
[`tests/evals/`](../tests/evals/) and `scripts/run_eval.py` are the part that can.

Six cases, each a small self-contained mockup, an `expectations.yaml` of
mechanically checkable assertions, and a `notes.md` saying what the case is meant to
stress: **app shell**, **multi-section form**, **card grid**, **mixed shell + form**,
a deliberately hard one built entirely from effects listed under `impossible_css`
— which has no right conversion, only a right disclosure — and **multi-screen-mock**,
whose input is a three-screen `mock-ui` folder and whose output is one file per screen.

```bash
python scripts/run_eval.py out.pa.yaml --case tests/evals/app-shell
```

**The boundary is the important part.** This scores a `.pa.yaml` that already exists.
Producing that file means running a model, and CI does not run a model — there is
deliberately no API-key step in the scorer and none in the workflow, because a harness
that quietly depended on a key would be green on every run where the key was missing.
So the loop is manual and has three steps: ask Claude for a case's mockup, save the
answer, run the scorer. The whole procedure, including what the harness *cannot* see,
is in [`docs/evals.md`](evals.md).

What CI does run is the half that needs no model: `python scripts/run_eval.py` with no
arguments scores the three bundled example screens against their matching cases. That
proves the scorer works. It proves nothing about the skill — the examples were written
by hand, not generated — and the tool says so on every run.

## What it can't do (honestly)

Some CSS effects have no verified Power Fx equivalent: box shadows, `backdrop-blur`, CSS
transitions/animations, `group-hover`, true one-sided borders, and any non-`Segoe UI` font. The
full list is `impossible_css` in
[`controls.yaml`](../skills/create-app/references/controls.yaml). The skill will tell you plainly
and suggest the closest practical substitute (e.g. a thin `Rectangle` for a left border) rather than
faking a property or silently dropping the requirement — and the `impossible-effects` eval case
exists to check that it actually does.

Beyond that: nothing here renders anything, so colours, fonts and visual hierarchy are
never verified automatically; and the linter is an approximation of Studio, not Studio.
Only a real paste test settles a control.

## Walkthrough: from a mockup to a pasted screen

The linter needs `pip install pyyaml jsonschema`; without `jsonschema` it says
**UNPROVEN** instead of **SAFE TO PASTE**, because the layer that catches `PA1001` did
not run.

### 2. Give Claude a mockup

Anything visual works:

- An HTML/CSS export from Google Stitch, v0, or Figma
- A screenshot of a UI
- A hand-drawn wireframe photo

Ask, in plain words:

> Convert this to pa.yaml — make it a Power Apps screen.

If the screen is going into an **app that already exists**, say so and hand over an
export of it (`pac canvas download -d <dir>`, or just unzip the `.msapp`). Claude
runs `skills/create-app/scripts/app_inventory.py` over it first, so the new screen matches the app's
naming convention, reuses its theme variables, and does not collide with a name
that is already taken. See
[`extend-existing-app.md`](../skills/create-app/references/extend-existing-app.md).

### 3. Claude produces the `.pa.yaml`

It reads the confirmed-controls catalog, picks the patterns the mockup needs,
derives the absolute coordinates, and writes the full file. Anything it is not
sure about is tagged `# UNVERIFIED` and comes with a small isolated paste-test
snippet.

### 4. Lint it before it goes near Studio

This is the step that saves the round trip, and Claude runs it as part of its own
workflow. Run it yourself on anything you did not watch it lint:

```bash
python skills/create-app/scripts/pa_lint.py myscreen.pa.yaml
```

Four layers run in order, and each maps to something Studio would have told you
later:

| Layer | Checks | Studio equivalent |
|---|---|---|
| **L0** | the file is YAML at all | a paste that does nothing |
| **L1** | the bundled Microsoft v3.0 schema | `PA1001` — blocks the whole paste |
| **L2** | this repo's control catalog | `PA2108` — unknown control or property |
| **L3** | SKILL.md's own conventions | nothing; Studio accepts these silently |

The last line is the verdict. **`VERDICT: SAFE TO PASTE` is the only one that
means go.** The others, and what to do about each, are in
[troubleshooting](troubleshooting.md#the-linters-verdict-lines).

Useful flags: `--quiet` prints only the verdict, `--strict` exits non-zero on
warnings, `--json` is for scripting.

### 5. Paste into Power Apps Studio

1. Open your Canvas app in **Power Apps Studio**.
2. Add a **blank screen**.
3. With the screen selected, use **Paste code** (the tree-view context menu, or
   `Ctrl+V` after copying the whole file).
4. Paste the **entire** file — Studio needs the full `Screens:` wrapper, not a
   fragment.

If the file came with isolated paste-test snippets, paste each of those onto a
scratch screen **first**. That is what they are for: a one-control file fails in a
way you can attribute, and a 200-control file does not.

### 6. Feed results back

If Studio shows an error or warning, paste the exact text back to Claude. It
knows which codes block a paste (`PA1001`, `PA2108`) and which are harmless
version warnings (`PA2105`, `PA2106`) — see [troubleshooting](troubleshooting.md).

If a Studio test confirms a control the catalog did not have, record it in your
own `controls.yaml` and `confirmed-controls.md`, and please
[report it](https://github.com/YKUNAKORN/power-app-yaml/issues/new?template=control-report.yml)
so the next person benefits. Results for the twelve bundled test snippets go in
[`test-plan.md`](test-plan.md).
