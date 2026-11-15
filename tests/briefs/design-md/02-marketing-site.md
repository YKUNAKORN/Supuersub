# Brief 2: marketing site (target `web`)

Scored by `design_lint.py` plus a human read. Not automated: a person gives Claude the
brief, saves the `DESIGN.md` it writes, lints it, and ticks the checklist.

## What to tell Claude

> We're launching a small bakery-supply brand online and need a style guide before we
> design the site. I love how a certain big tech company's product pages look, so
> minimal and premium, and I'd like to use their system font. No logo yet. You decide
> the colours.

## Checklist

Lint:

- [ ] `design_lint.py` verdict is CLEAN, or USABLE with each warning explained.
- [ ] If Node.js was available, the Google CLI was run and differences were reported.

Originality (the trap in this brief):

- [ ] The admired company is not named anywhere in the `DESIGN.md`.
- [ ] Its qualities are written down instead (low density, one accent, large type,
      generous section spacing), in Claude's own words.
- [ ] Its proprietary typeface is not stated as available. If mentioned at all, it is a
      preference with an open fallback stack, and `### Note on Font Substitutes` names
      the open alternative.
- [ ] The palette is not that company's signature colour combination.

Directions:

- [ ] Because the user has no colours, Claude offered two or three named directions,
      each with one sentence, a palette and a type pairing, before writing the file.

Tokens and writing:

- [ ] A `primary`, neutrals, surfaces, text and semantic colours; every colour is used by
      a component (no `orphaned-color` warnings).
- [ ] 9–15 typography levels with display sizes for hero headlines.
- [ ] Responsive Behavior has breakpoints, touch targets and a collapsing strategy.
- [ ] Every hex in the prose is a token named beside it (no `prose-hex` warnings).
- [ ] Component references in prose use `{components.…}` (no `prose-ref-singular`).
- [ ] Ends by naming `mock-ui`.
