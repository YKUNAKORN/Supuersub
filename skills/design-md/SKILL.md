---
name: design-md
description: >-
  Interviews the user and writes a DESIGN.md: a design system (colours, typography,
  spacing, radii, components as tokens, plus the reasoning in prose) in the format
  Google published for Stitch. Use when someone is about to start designing a website or
  app, asks for a design system, style guide, brand or visual language, design tokens, or
  a DESIGN.md, or wants an existing DESIGN.md updated or checked. Also for a design
  headed for Power Apps. Not for building pages or screens: that is mock-ui, which reads
  the DESIGN.md this skill writes.
---

# DESIGN.md: interview, then write the design system

Produce one file, `DESIGN.md`: tokens in YAML front matter, eleven `##` sections of prose
explaining them. Reply in the user's language; token names and headings stay English.
Paths are relative to this skill's folder: `${CLAUDE_SKILL_DIR}`, or run from that folder.

## The workflow (in order)

1. **Establish the target.** `web` (default) or `power-apps` (the design will become a
   Power Apps canvas app through `create-app`). Ask if it is not clear. For
   `power-apps`, read
   [`references/shared/powerapps-profile.md`](references/shared/powerapps-profile.md)
   now and keep every later choice inside it.
2. **Collect what exists.** Read what the user already gave: brief, logo, screenshots,
   brand guide, an existing `DESIGN.md`. Then ask only for what is missing, from
   [`references/interview.md`](references/interview.md): product and audience, brand
   colours and fonts, sites they admire and why, devices, density, light or dark,
   accessibility needs. **At most two rounds of questions.** If the user says "you
   decide", decide and say which defaults you took.
3. **No strong view? Offer two or three directions.** Each: an invented name, one
   sentence, a palette (primary, surface, text, accent as hex), a type pairing with open
   fallbacks. Let the user pick or mix.
4. **Derive the tokens**, in this order:
   - colours: a `primary`, neutrals, surfaces, text, and semantic states (`success`,
     `warning`, `error`, `info`), each filled colour with an `on-` partner;
   - typography: 9–15 levels, each with `fontFamily`, `fontSize`, `fontWeight`,
     `lineHeight` (add `letterSpacing` where it is not zero);
   - `rounded`: a radius scale; `spacing`: a scale on a stated base unit (4px or 8px);
   - components that reference those tokens: buttons with states, cards, inputs with
     helper and error text, badges, navigation. Every colour token is used by at least
     one component.
5. **Write the whole file** from [`assets/DESIGN.template.md`](assets/DESIGN.template.md):
   all eleven sections, in order. [`references/section-guide.md`](references/section-guide.md)
   says what goes in each `##` and `###` and how long.
   [`references/format.md`](references/format.md) is the format itself: keys, types,
   references, lint rules. [`assets/example/DESIGN.md`](assets/example/DESIGN.md) is a
   finished, lint-clean example for an invented brand; read it for tone and depth,
   never copy its values.
6. **Lint** with `python3 ${CLAUDE_SKILL_DIR}/scripts/design_lint.py DESIGN.md`
   (`scripts/design_lint.py`; add `--target power-apps` for that target). Fix every
   error and lint again. Report every warning with the fix you made or the reason it
   stands. If Node.js is available, also run `npx @google/design.md lint DESIGN.md` and
   report where the two disagree; [`references/format.md`](references/format.md) §7 lists
   the known differences.
7. **Hand over** the complete file (write `DESIGN.md` at the project root when there is a
   project folder; otherwise give the user the file), with the lint verdict and the
   warnings. Name the next step: **`mock-ui`** turns this `DESIGN.md` plus the screen
   requirements into HTML mockups.

## Rules

- **Tokens are normative.** Prose explains them. Every hex value in the prose is the
  value of a token, named beside it: `**Moss** ({colors.primary} — #2f6b3a)`.
- **Components reference tokens**, never colour literals: `"{colors.primary}"`.
  Components cannot reference other components; make each variant its own component
  (`button-primary-hover`).
- **References name the YAML path**: `{colors.primary}`, `{typography.body-md}`, and
  `{components.button-primary}` (plural, as the key is). The collection writes the
  singular `{component.…}` in prose; the linter warns on it.
- **Contrast.** Text on every filled component meets 4.5:1 (WCAG AA). The linter
  measures it; a failing pair is an error, not a warning. Status is never shown by
  colour alone.
- **The design system is the user's own.** A site they admire is a source of qualities
  (density, restraint, contrast), not something to reproduce. Never reuse another
  company's name, logo, wordmark or signature palette, and never name the admired site
  in the file.
- **Fonts.** Write a typeface the user wants as a preference with an open fallback
  stack. Never state that a proprietary typeface is available or licensed.
- **Updating an existing `DESIGN.md`:** keep every token name stable, even when its value
  changes. Mockups and screens already built on it refer to the names. Add rather than
  rename; list anything retired in Iteration Guide.
- **Under `power-apps`:** when the user asks for an effect the profile rules out
  (shadows, blur, transitions, hover on a parent, one-sided borders, a non-Segoe font),
  say plainly that the canvas cannot reproduce it, name the substitute, use the
  substitute in the tokens, and record both in `## Known Gaps`. Describe hover, pressed
  and disabled states only for buttons and icons. Never present an unverified item as
  confirmed.

## Hand-off

[`references/shared/handoff.md`](references/shared/handoff.md) is the contract between
the five skills: where `DESIGN.md` goes, identifier rules, targets. Never assume an
earlier skill ran, and end by naming `mock-ui`.
