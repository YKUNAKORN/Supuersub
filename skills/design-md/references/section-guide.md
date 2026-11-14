# What goes in each section

The body of a `DESIGN.md` explains the tokens: why each value was chosen and how to apply
it. Write it for two readers: a person deciding whether the system fits, and an agent
building a screen from it later (`mock-ui`, then `create-app`). Both need the reasoning,
not adjectives.

Lengths are for a typical product. A dense dashboard needs more in Components; a
marketing site more in Layout and Responsive Behavior. The `###` headings marked
**(standard)** are the ones nearly every current file in the collection uses; keep their
exact wording so a reader can find them. Add others where the system needs them.

General rules:

- Every hex value in the prose is the value of a colour token, and the token is named
  next to it: `**Signal Blue** ({colors.primary} — #1f4fd1)`.
- Name tokens with their YAML path in braces: `{colors.primary}`, `{typography.body-md}`,
  `{rounded.md}`, `{spacing.lg}`, `{components.button-primary}`.
- Say why. "Body at 16px / 1.5 because the audience reads long approval notes on
  laptops" beats "Clean, modern body text".
- Never describe another company's product. A site the user admires contributes
  qualities (density, restraint, contrast), which you describe in your own terms.
- Write in the user's language. Token names, section headings and `###` headings stay in
  English so tools and later skills can find them.

## Overview (150–300 words)

What the product is, who uses it, and the feeling the interface should create. Then the
principle that decides close calls ("data first, chrome last"). End with
**Key Characteristics:**, five to eight bullets, each a concrete rule a reader could check
on a screen. State the target (`web` or `power-apps`) in the first paragraph.

## Colors (one bullet per token)

Open with one or two sentences on the palette's logic (one accent or several, warm or
cool neutrals, how dark mode is handled).

- `### Brand & Accent` **(standard)**: `primary` and any accent, with what each is
  reserved for.
- `### Surface` **(standard)**: canvas, raised surfaces, inverted surfaces.
- `### Text` **(standard)**: text colours and which surface each sits on.
- `### Semantic` **(standard)**: success, warning, error, info, each with its `on-` pair.
- Optional: `### Borders & Dividers`, `### Data Visualization`.

Each bullet: `**Display Name** ({colors.token} — #hex): role, and where not to use it.`

## Typography

- `### Font Family` **(standard)**: each family, its role, and the full fallback stack.
- `### Hierarchy` **(standard)**: a table with one row per typography token:
  `| Token | Size | Weight | Line Height | Letter Spacing | Use |`.
- `### Principles` **(standard)**: four to six rules (weight ladder, where tracking
  tightens, when to use the mono face).
- `### Note on Font Substitutes` **(standard)**: what to use where the preferred face is
  not available. Name the open alternative and any metric adjustments. Never claim a
  proprietary face is licensed or installed.

## Layout

- `### Spacing System` **(standard)**: the base unit, every `spacing` token with its value,
  and the common uses (card padding, section gaps, form rows).
- `### Grid & Container` **(standard)**: max content width, columns, gutters. Under
  `power-apps`, the canvas (1366 × 768 by default) and how the grid sits on it.
- `### Whitespace Philosophy` **(standard)**: one paragraph on density and why.

## Elevation & Depth

A table of levels (`| Level | Treatment | Use |`), then a paragraph on how hierarchy is
shown. Under `power-apps` there are no shadows or blur: depth comes from surface colour
and 1px borders, and the section says so.

- `### Decorative Depth` **(standard)**: gradients, imagery, overlays, or "none" and why.

## Shapes

- `### Border Radius Scale` **(standard)**: `| Token | Value | Use |` for every `rounded`
  token.
- Optional: `### Iconography`, `### Imagery`: stroke weight, corner style, aspect ratios.

## Components

One `###` group per family; inside it, one paragraph per component, opening with its
name in bold code: ``**`button-primary`** — …``. Give colours, type, radius and padding
by token, then the states (hover, active, focus, disabled) and where it is used.

- `### Buttons` **(standard)**
- `### Cards & Containers` **(standard)**
- `### Inputs & Forms` **(standard)**: include error and helper text.
- Others as needed: `### Navigation`, `### Badges & Status`, `### Tables & Lists`,
  `### Feedback` (alerts, toasts), `### Footer`.

Under `power-apps`, mention which canvas control each component becomes when it is
obvious (a button is a Button, a card is a container), and that hover/pressed states
exist only on buttons and icons.

## Do's and Don'ts

- `### Do` **(standard)**: six to ten rules, each naming tokens.
- `### Don't` **(standard)**: six to ten rules, each the mirror of a real temptation.

## Responsive Behavior

- `### Breakpoints`: `| Name | Width | Key Changes |`.
- `### Touch Targets`: the minimum (44 × 44px is the common floor) and which components
  meet it.
- `### Collapsing Strategy`: what happens to navigation, grids and tables as width drops.

Under `power-apps` a canvas screen has a fixed size; say so, give the canvas, and
describe phone or tablet layouts only if the user wants separate screens for them.

## Iteration Guide

Five to eight numbered rules for whoever changes the system next: change one component
at a time, keep token names stable (mockups refer to them), add variants as suffixed
components, reference tokens instead of hex, where to record a new decision.

## Known Gaps

What the system does not decide yet, and what was asked for but cannot be delivered.
Under `power-apps`, list every effect the profile rules out that the user asked for,
each with its substitute: `- **Card shadow** (box-shadow): not reproducible on a canvas;
cards use {colors.border} at 1px instead.` If nothing is missing, say what was checked.
