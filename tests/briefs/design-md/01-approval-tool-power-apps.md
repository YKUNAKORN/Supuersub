# Brief 1: internal approval tool (target `power-apps`)

Scored by `design_lint.py --target power-apps` plus a human read. Not automated: a
person gives Claude the brief, saves the `DESIGN.md` it writes, lints it, and ticks the
checklist. See the design-md section of the evals guide in this repository's `docs`.

## What to tell Claude

> I need a design system for an internal purchase-approval app we will build in Power
> Apps. Managers approve or reject requests from their team, mostly on a laptop, some on
> a tablet. Our brand colour is a dark teal and we use Segoe UI. I'd like the cards to
> float with a soft shadow, and the approve button should glow a little when you hover
> over the card. Light mode only. Some approvers are colour-blind.

## Checklist

Lint:

- [ ] `design_lint.py --target power-apps` verdict is CLEAN or USABLE; no errors.
- [ ] Every remaining warning is listed in the hand-over with its reason.

Target and profile:

- [ ] The Overview states the target `power-apps` and the 1366 × 768 canvas.
- [ ] Claude says plainly that the card shadow (`box-shadow`) and the hover-on-card
      effect (`group-hover`) cannot be reproduced on a canvas, and names a substitute for
      each (a border or tone step; hover on the button itself).
- [ ] Both appear in `## Known Gaps` with their substitutes, and neither appears as a
      design instruction elsewhere.
- [ ] Every `fontFamily` starts with `Segoe UI`.
- [ ] Hover, pressed and disabled states are described for buttons and icons only.

Tokens:

- [ ] `primary` is a teal that passes 4.5:1 with its `on-primary` text.
- [ ] `success`/`warning`/`error` exist with `on-` partners; approve and reject are not
      distinguished by colour alone (a word or icon is required by the prose).
- [ ] 9–15 typography levels; a spacing scale with a stated base unit.
- [ ] Components cover at least: approve and reject buttons with states, a request card,
      a status badge, a text input with error text.

Writing:

- [ ] All eleven sections, in order; prose explains why, not just what.
- [ ] No more than two rounds of questions before the file was written.
- [ ] Ends by naming `mock-ui` as the next step.
