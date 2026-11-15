# From a `mock-ui` mockup: one `.pa.yaml` per screen

Use this branch when the input is a mockup folder made by the `mock-ui` skill: a
`sitemap.json` plus one `.html` file per screen and an `index.html`. In a project it sits
at `supersub/mockup/`. In chat the files arrive as attachments. The output is one
`.pa.yaml` per screen, each a complete `Screens:` wrapper, with `Navigate()` wired
between the screens and a `PASTE-ORDER.md` that says how to put them into one app.

The single-mockup workflow in `SKILL.md` still does the work. This file adds what changes
when there are several screens: reading the sitemap, naming across files, navigation,
the `data-*` hints, and the hand-off.

## 1. Read `sitemap.json` first

Before any HTML, read the sitemap. If it is missing, ask for it. Do not rebuild it from
the HTML: the HTML says what each page links to, not which pages belong to the app.

| Field | Use |
|---|---|
| `target` | Must be `power-apps`. See below for `web`. |
| `canvas` | Width and height of every screen (1366 × 768 unless the user chose otherwise). Use it in place of the canvas question in `layout-mapping.md`. |
| `start` | The first screen. Paste it first and make it the start screen. |
| `screens[].id` | The screen name in Power Apps and every `Navigate()` target. Use it as given. |
| `screens[].file` | The screen file to convert. |
| `screens[].height`, `scrolls` | When `scrolls` is true, set the screen's own `Height` to `height`. |
| `screens[].kind` | `screen` or `dialog`: convert it as a screen. `state`: see below. |
| `screens[].nav` | The links the screen must have. Check each one became a `Navigate()`. |
| `screens[].data` | Lists and columns the screen reads or writes. Section 5. |
| `screens[].actions` | Every `data-action` on the screen. Section 6. |

**A `web` target is refused, politely.** Say why: a `web` mockup is responsive, with
relative units and wrapping layouts, and a Power Apps screen needs one fixed canvas and
absolute positions. Nothing in the files says which width to freeze, so any conversion
would be a guess presented as a design. Offer two ways on: convert one screen the way
a screenshot is converted (the user names the width, and the result is a single
screen), or ask `mock-ui` to redo the mockup with the `power-apps` target.

**A `state` screen** (`"kind": "state"`, with `variantOf`) is a second look of another
screen, such as the list when it is empty. It is not a new screen. Write no file for it.
List it in `PASTE-ORDER.md` under "By hand afterwards" with what differs. Showing one of
two states needs `Visible` formulas over a variable, and none of that is confirmed.

## 2. Convert the screens one at a time

Work through `sitemap.screens` in order. For each screen file, run steps 1–7 of
`SKILL.md` as if it were the only mockup:

- **Geometry is in the CSS already.** A `power-apps` mockup places every box with px
  values. Copy them. Child `X`/`Y` inside a card are measured from the card, as in the
  bundled examples.
- **Colours follow the `var()` chain** to the `:root` block, then to the hex value.
  `--button-primary-bg: var(--color-primary)` and `--color-primary: #0f5c8c` give
  `Fill: =RGBA(15, 92, 140, 1)`.
- **Shared chrome** (sidebar, top bar) is converted once, from the first screen that
  has it, and then repeated in every screen file with the same geometry and that
  screen's names. Only the active nav row changes.

## 3. Names are unique across the app

Studio needs control names to be unique in the whole app, not only on one screen. A
pasted control whose name is taken is renamed with `_1`, without an error, and every
formula that uses the name you wrote then points at the other screen's control.

Put the screen in every name: **type prefix, then the screen id without `scr`, then the
role**. On `scrLoanList`: `lblLoanListTitle`, `btnLoanListNavLoans`,
`grpLoanListSidebar`. Prefixes: `lbl` Label, `btn` Button, `grp` GroupContainer, `rec`
Rectangle, `ico` Icon, `img` Image, `txt` TextInput, `dd` DropDown, `rdo` Radio. The
ten-screen test app in the plugin's source repository names its content controls this
way (`lblAppr1Title`) and puts the screen last on its chrome (`btnNavHomeAppr`). What
matters is that every name carries its screen; use one order throughout.

When the screens go into an app that already exists, also run
`python3 ${CLAUDE_SKILL_DIR}/scripts/app_inventory.py <src>` (that is
`scripts/app_inventory.py`) and avoid every name it lists.

## 4. Navigation

- Each `data-nav="<ScreenId>"` becomes
  `OnSelect: =Navigate(<ScreenId>, ScreenTransition.None)` on the control's Button. A
  nav row is a `Classic/Button@2.2.0` as always (rule 5).
- The active sidebar row links to its own screen. Keep that `Navigate()`: it is harmless
  and keeps the chrome identical.
- `SKILL.md` rule 7 is widened for this branch. A target is valid when it is a screen in
  the same file, **a screen id in `sitemap.json`**, or **a screen already in the app**
  (from `app_inventory.py`). Such a `Navigate()` needs no placeholder comment.
- A target that is none of these still gets the placeholder and a same-line comment.

## 5. Data hints: static first

`data-source`, `data-field` and `data-repeat` say where the screen's data comes from.
The confirmed path is static controls, so:

- **Render the sample content as it is.** Three sample rows under `data-repeat` become
  three rows of Labels. A form under `data-source` becomes its input controls.
- **Name the binding in a comment** on the control that shows the column:
  `- lblLoanListRow1Item:  # Loans.Title`. For a repeated block, put one comment on the
  first row saying it is sample row 1 of n and which list it repeats.
- **Hand over the matching paste test** from `assets/test-snippets/`: `gallery.pa.yaml`
  for `data-repeat`, `form.pa.yaml` for a create or update form, `datepicker.pa.yaml`
  for `<input type="date">`. Say what each one would unlock.
- **Never in the main file:** `Gallery`, `Form` or `DataTable` while they are in
  `unattempted_controls`, an `App:` block, or a `DataSources:` block.
  `references/data-binding.md` is the place for what is known about binding, and none of
  it is confirmed in Studio.

## 6. Actions: placeholders that say what they are for

Each `data-action` becomes a placeholder `OnSelect` with a comment on the same line
naming the action:

```yaml
OnSelect: =false  # placeholder - action filter:Loans not wired: data binding UNVERIFIED (data-binding.md)
```

When the control also carries `data-nav`, the `Navigate()` is real and the comment names
the actions that are not wired:

```yaml
OnSelect: =Navigate(scrLoanList, ScreenTransition.None)  # action submit:Loans + run-flow:NotifyApprover not wired: data binding UNVERIFIED (data-binding.md)
```

For `run-flow:<FlowName>`, go no further than `references/data-binding.md` section 7: a
flow is a `Type: Actions` data source, and calling it with `<FlowName>.Run(...)` is
UNVERIFIED. Its arguments are defined by the flow, not by the app, so never write them.
`create-flow` plans the flow from the sitemap's `run-flow:` actions.

## 7. `data-unsupported`

An element marked `data-unsupported="<id>"` carries an effect the user wants that Power
Apps cannot draw. Treat it as `impossible_css` in `controls.yaml` prescribes: apply the
catalog's substitute, and name the effect and the substitute in a comment on the control
and in the file header. A `box-shadow` panel keeps its 1px border; a one-sided border
becomes a thin `Rectangle`. Never fake the effect with an invented property.

## 8. Design tokens

Write literal `RGBA(…)` values on every control. That is the confirmed path. Then offer,
as a separate text block and not as `.pa.yaml`, a `Set()` the user can paste into
`App.OnStart` themselves if they want named colours:

```text
Set(varTheme, { Primary: RGBA(15, 92, 140, 1), Surface: RGBA(243, 245, 247, 1), ... })
```

One field per colour token in `DESIGN.md` (or in the `:root` block), PascalCase. Say it
is not paste-tested and that nothing in the screens reads it.

## 9. Lint the screens as one app

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/pa_lint.py --app-dir supersub/app --sitemap supersub/mockup/sitemap.json
```

That is `scripts/pa_lint.py`. `--app-dir` lints every `.pa.yaml` in the folder and
compares the files: `L3.duplicate-control-name-in-app` is a name used on two screens,
`L3.duplicate-screen-in-app` is a screen id defined twice. `--sitemap` makes the
sitemap's screen ids valid `Navigate()` targets; `--known-screens a,b` does the same for
screens already in the app. Hand nothing over with an L0/L1 error, an unresolved
navigation target, or a cross-file duplicate. Report every other warning, as in step 6.

## 10. Output and `PASTE-ORDER.md`

Write `supersub/app/<ScreenId>.pa.yaml` for each screen and `supersub/app/PASTE-ORDER.md`.
Without a project folder, create the same files and hand them over.

Each screen file opens with a header comment: the source file, the data hints and which
paste test unlocks them, the actions and why they are placeholders, and the declared
gaps.

`PASTE-ORDER.md` holds:

1. A table: order, file, screen id, where it navigates, its actions. The start screen
   is first.
2. What to paste-test first: every isolated snippet the linter generated, or "none".
3. How to paste each screen. Open the app in Power Apps Studio, add a **blank screen**,
   select it, use **Paste code**, and paste the **whole** file.
4. **Create every screen before judging a `Navigate()` error.** Whether a screen that
   navigates to a screen not pasted yet can be pasted at all, and whether the error
   clears once the target exists, is not known. Neither is whether a pasted screen keeps
   the name under `Screens:`. State both as questions for the user to settle in Studio,
   to record in the multi-screen section of `test-plan.md` in the plugin's source
   repository, and tell them to rename any screen whose name did not stick.
5. By hand afterwards: set the start screen, delete the app's empty starting screen,
   build any `state` variants, connect data and flows.
6. The optional theme block from section 8.

## 11. Hand-off

Send every screen file and `PASTE-ORDER.md`, then the paste tests, each labelled. Then
name the next skills:

- **`create-list`** builds the SharePoint lists the screens expect, from the `data`
  entries in `sitemap.json`.
- **`create-flow`** plans the flows behind the `run-flow:` actions, from the `actions`
  entries.
