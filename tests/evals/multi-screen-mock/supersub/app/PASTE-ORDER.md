# Paste order: Kitroom (3 screens)

Converted from `supersub/mockup/` (target `power-apps`, canvas 1366 × 768) by
`create-app`. One `.pa.yaml` per screen. Each file is a complete `Screens:` wrapper and
lints on its own:

```bash
python3 scripts/pa_lint.py --app-dir supersub/app --sitemap supersub/mockup/sitemap.json
```

Result when written: `VERDICT: SAFE TO PASTE` for all three files, 0 errors, 0 warnings,
no cross-file name collision.

| # | File | Screen | Navigates to | Actions (not wired) |
|---|---|---|---|---|
| 1 | `scrLoanList.pa.yaml` | `scrLoanList` (start) | `scrNewLoan`, `scrLoanDetail`, itself | `filter:Loans` |
| 2 | `scrNewLoan.pa.yaml` | `scrNewLoan` | `scrLoanList`, itself | `submit:Loans`, `run-flow:NotifyApprover` |
| 3 | `scrLoanDetail.pa.yaml` | `scrLoanDetail` | `scrLoanList`, `scrNewLoan` | `update:Loans`, `run-flow:ReportLostItem` |

## Before you paste

Nothing in these files is unverified, so there is no isolated snippet to paste-test
first. The snippets below are for **later**, when the static sample rows are replaced
by data. They are not needed to paste these three screens:

- `assets/test-snippets/gallery.pa.yaml` (the loan rows on `scrLoanList`)
- `assets/test-snippets/form.pa.yaml` (the form on `scrNewLoan`)
- `assets/test-snippets/datepicker.pa.yaml` (Due back on `scrNewLoan`)

## Paste the screens

The procedure for each screen is the one in `docs/quickstart.md`, step 5: open the app in
Power Apps Studio, add a **blank screen**, select it, use **Paste code**, and paste the
**whole** file.

1. Paste `scrLoanList.pa.yaml`, then `scrNewLoan.pa.yaml`, then `scrLoanDetail.pa.yaml`.
2. **Paste all three before you judge any `Navigate()` error.** Each screen navigates to
   the others, so whichever you paste first refers to screens that do not exist yet.
   Whether Studio blocks that, warns, or shows a formula error that clears once the
   target exists is **not known**. Until it is, create every screen first and read the
   formula errors afterwards.
3. Check the screen names in the tree view: they must be `scrLoanList`, `scrNewLoan`
   and `scrLoanDetail`, because every `Navigate()` uses those names. If Studio kept its
   own name (`Screen2`) or added `_1`, rename the screen to the id in the table.
4. Check that no control name ends in `_1`. The three files share no control name, so
   a `_1` means a name collided with something already in the app.

## By hand afterwards

- Make `scrLoanList` the start screen: drag it to the top of the tree view, or set the
  app's `StartScreen`. The files carry no `App:` block.
- Delete the blank screen the new app started with, if it is still empty.
- Each action button has a placeholder `OnSelect` with a comment naming its action.
  `create-list` builds the `Loans` list the screens show and write; `create-flow` plans
  `NotifyApprover` and `ReportLostItem`. Wiring them needs a data source and a flow
  connection, which `references/data-binding.md` marks UNVERIFIED.

## Optional: theme variables

The screens use literal `RGBA(…)` values on every control, which is the confirmed path.
If you want named colours for your own formulas, paste this into `App.OnStart` yourself.
Not paste-tested here, and nothing in the three files reads it.

```text
Set(varTheme, {
    Primary:      RGBA(15, 92, 140, 1),
    PrimaryHover: RGBA(11, 74, 114, 1),
    OnPrimary:    RGBA(255, 255, 255, 1),
    Surface:      RGBA(243, 245, 247, 1),
    SurfaceRaised: RGBA(255, 255, 255, 1),
    SurfaceSunken: RGBA(230, 234, 238, 1),
    OnSurface:    RGBA(27, 34, 40, 1),
    TextMuted:    RGBA(79, 91, 102, 1),
    Border:       RGBA(201, 209, 216, 1),
    NavActive:    RGBA(219, 233, 243, 1),
    Success:      RGBA(29, 107, 69, 1),
    Warning:      RGBA(138, 90, 0, 1),
    Error:        RGBA(179, 38, 30, 1),
    Info:         RGBA(31, 95, 139, 1)
})
```

## Questions for Studio

Record the answers in `docs/test-plan.md`, section "Multi-screen paste".

1. Does a pasted screen keep the name under `Screens:`?
2. Can a screen whose `Navigate()` names a screen that does not exist yet be pasted, and
   does the formula error clear once that screen is pasted?
