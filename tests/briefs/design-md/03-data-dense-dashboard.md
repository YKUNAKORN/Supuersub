# Brief 3: data-dense operations dashboard (target `web`)

Scored by `design_lint.py` plus a human read. Not automated: a person gives Claude the
brief, saves the `DESIGN.md` it writes, lints it, and ticks the checklist.

## What to tell Claude

> Here's our existing DESIGN.md (attach one). We're adding a dark-mode operations
> dashboard for warehouse shift leads: big monitors, lots of tables and live status,
> people glance at it from across the room. Please extend the design system rather than
> start over. Labels must work in English and Thai.

(Attach any lint-clean `DESIGN.md`, for example the skill's own
`assets/example/DESIGN.md`.)

## Checklist

Lint:

- [ ] `design_lint.py` verdict is CLEAN, or USABLE with each warning explained.

Updating, not replacing:

- [ ] Every token name in the attached file still exists in the result. Values may
      change; names do not.
- [ ] New tokens are added beside the old ones (e.g. `surface-dark`, `on-surface-dark`),
      and the Iteration Guide records what was added.

Density and dark mode:

- [ ] A smaller base unit or tighter scale for tables is stated and justified.
- [ ] Dark surfaces and text pass 4.5:1 for every component pair (the linter enforces
      it); status colours have dark-mode `on-` partners.
- [ ] Table, row, and live-status components exist; status uses a word or icon as well
      as colour.
- [ ] A monospace or tabular-figure level exists for numbers.

Language:

- [ ] Font stacks cover Thai (e.g. a Thai-capable open face in the stack), and line
      heights leave room for Thai vowels and tone marks above and below the line.
- [ ] Prose follows the user's language; token names and headings stay English.

Writing:

- [ ] All eleven sections, in order.
- [ ] Ends by naming `mock-ui`.
