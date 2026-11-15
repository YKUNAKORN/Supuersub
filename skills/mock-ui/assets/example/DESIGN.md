---
version: alpha
name: Kitroom
description: An internal equipment-loan tool for a small office team, built as a Power Apps canvas app. Cool grey surfaces, one harbour-blue action colour, Segoe UI throughout, 6px corners, flat panels separated by 1px hairlines instead of shadows.
colors:
  primary: "#0f5c8c"
  primary-hover: "#0b4a72"
  on-primary: "#ffffff"
  surface: "#f3f5f7"
  surface-raised: "#ffffff"
  surface-sunken: "#e6eaee"
  on-surface: "#1b2228"
  text-muted: "#4f5b66"
  border: "#c9d1d8"
  nav-active: "#dbe9f3"
  success: "#1d6b45"
  on-success: "#ffffff"
  warning: "#8a5a00"
  on-warning: "#ffffff"
  error: "#b3261e"
  on-error: "#ffffff"
  info: "#1f5f8b"
  on-info: "#ffffff"
typography:
  display:
    fontFamily: "Segoe UI, system-ui, sans-serif"
    fontSize: 28px
    fontWeight: 700
    lineHeight: 36px
  headline:
    fontFamily: "Segoe UI, system-ui, sans-serif"
    fontSize: 22px
    fontWeight: 700
    lineHeight: 28px
  title:
    fontFamily: "Segoe UI, system-ui, sans-serif"
    fontSize: 18px
    fontWeight: 700
    lineHeight: 24px
  body-lg:
    fontFamily: "Segoe UI, system-ui, sans-serif"
    fontSize: 16px
    fontWeight: 400
    lineHeight: 24px
  body-md:
    fontFamily: "Segoe UI, system-ui, sans-serif"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 20px
  body-strong:
    fontFamily: "Segoe UI, system-ui, sans-serif"
    fontSize: 14px
    fontWeight: 700
    lineHeight: 20px
  label-md:
    fontFamily: "Segoe UI, system-ui, sans-serif"
    fontSize: 14px
    fontWeight: 700
    lineHeight: 20px
  label-sm:
    fontFamily: "Segoe UI, system-ui, sans-serif"
    fontSize: 12px
    fontWeight: 700
    lineHeight: 16px
  caption:
    fontFamily: "Segoe UI, system-ui, sans-serif"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 16px
rounded:
  none: 0px
  sm: 4px
  md: 6px
  lg: 8px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: 0px 20px
    height: 40px
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.on-primary}"
  button-secondary:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.primary}"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: 0px 20px
    height: 40px
  button-disabled:
    backgroundColor: "{colors.surface-sunken}"
    textColor: "{colors.text-muted}"
  nav-item:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-lg}"
    height: 48px
  nav-item-active:
    backgroundColor: "{colors.nav-active}"
    textColor: "{colors.primary}"
  top-bar:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.on-surface}"
    height: 64px
  card:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
    padding: "{spacing.lg}"
  page:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-muted}"
    typography: "{typography.body-md}"
  input-text:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: 0px 12px
    height: 40px
  divider:
    backgroundColor: "{colors.border}"
    height: 1px
  table-head:
    backgroundColor: "{colors.surface-sunken}"
    textColor: "{colors.on-surface}"
    typography: "{typography.label-sm}"
    height: 40px
  badge-on-loan:
    backgroundColor: "{colors.info}"
    textColor: "{colors.on-info}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.sm}"
    padding: 2px 8px
  badge-returned:
    backgroundColor: "{colors.success}"
    textColor: "{colors.on-success}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.sm}"
    padding: 2px 8px
  badge-overdue:
    backgroundColor: "{colors.warning}"
    textColor: "{colors.on-warning}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.sm}"
    padding: 2px 8px
  input-error-text:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.error}"
    typography: "{typography.caption}"
  badge-lost:
    backgroundColor: "{colors.error}"
    textColor: "{colors.on-error}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.sm}"
    padding: 2px 8px
---

## Overview

Kitroom is the loan desk for an office team's shared equipment: laptops, monitors,
headsets, cameras. Staff open it on a desktop browser to borrow an item, see what they
hold, and mark it returned. It runs as a Power Apps canvas app on a fixed 1366 × 768
canvas. Target: `power-apps`.

The interface should feel like a tidy stock sheet: quiet, legible, obviously clickable
where it matters and nowhere else. When two choices are close, choose the one the
`create-app` catalog can reproduce.

**Key Characteristics:**
- Cool grey page ({colors.surface} — #f3f5f7) with white panels ({colors.surface-raised} — #ffffff).
- One action colour, Harbour ({colors.primary} — #0f5c8c); nothing else looks clickable.
- Segoe UI for everything; two weights only, 400 and 700.
- 6px corners on controls, 8px on panels; no pills.
- Flat: depth comes from tone and 1px hairlines ({colors.border} — #c9d1d8) alone.
- A 280px sidebar and a 64px top bar on every screen.

## Colors

One blue action colour on cool neutrals, with a full set of status colours. Every filled
colour has an `on-` partner that passes 4.5:1.

### Brand & Accent
- **Harbour** ({colors.primary} — #0f5c8c): primary buttons, links, the active nav label.
- **Deep Harbour** ({colors.primary-hover} — #0b4a72): hover and pressed state of Harbour.
- **Tide** ({colors.nav-active} — #dbe9f3): the active navigation row only.

### Surface
- **Mist** ({colors.surface} — #f3f5f7): the page behind every panel.
- **Sheet** ({colors.surface-raised} — #ffffff): panels, inputs, sidebar, top bar.
- **Slate** ({colors.surface-sunken} — #e6eaee): table header rows and disabled buttons.
- **Hairline** ({colors.border} — #c9d1d8): 1px borders and dividers.

### Text
- **Ink** ({colors.on-surface} — #1b2228): headings and body text.
- **Graphite** ({colors.text-muted} — #4f5b66): labels, helper text, secondary columns.
- **On colour** ({colors.on-primary} — #ffffff): text on every filled colour.

### Semantic
- **Returned** ({colors.success} — #1d6b45) with {colors.on-success}: item is back.
- **Overdue** ({colors.warning} — #8a5a00) with {colors.on-warning}: past its due date.
- **Lost / Error** ({colors.error} — #b3261e) with {colors.on-error}: lost items, form errors.
- **On loan** ({colors.info} — #1f5f8b) with {colors.on-info}: currently borrowed.

Status is never shown by colour alone: every badge carries a word.

## Typography

### Font Family
- **Everything**: `Segoe UI, system-ui, sans-serif`: the face the canvas renders without
  question.

### Hierarchy

| Token | Size | Weight | Line Height | Letter Spacing | Use |
|---|---|---|---|---|---|
| `{typography.display}` | 28px | 700 | 36px | 0px | Screen title |
| `{typography.headline}` | 22px | 700 | 28px | 0px | Logo wordmark |
| `{typography.title}` | 18px | 700 | 24px | 0px | Panel titles |
| `{typography.body-lg}` | 16px | 400 | 24px | 0px | Navigation rows |
| `{typography.body-md}` | 14px | 400 | 20px | 0px | Body, table cells, inputs |
| `{typography.body-strong}` | 14px | 700 | 20px | 0px | Emphasised values |
| `{typography.label-md}` | 14px | 700 | 20px | 0px | Buttons |
| `{typography.label-sm}` | 12px | 700 | 16px | 0px | Badges, table headers |
| `{typography.caption}` | 12px | 400 | 16px | 0px | Field labels, helper text |

### Principles
- Two weights: 400 for reading, 700 for anything that names or acts.
- Line heights are pixel values so every row height is arithmetic.
- Nothing a user must read is below 12px.
- No letter spacing.

### Note on Font Substitutes
Segoe UI is the platform face on the target machines; `system-ui` is the fallback in a
browser preview.

## Layout

### Spacing System
- **Base unit:** 4px.
- **Tokens:** `{spacing.xs}` 4px · `{spacing.sm}` 8px · `{spacing.md}` 16px ·
  `{spacing.lg}` 24px · `{spacing.xl}` 32px.
- Panel padding is `{spacing.lg}`; form rows are 16px apart; panels are 24px apart.

### Grid & Container
Fixed 1366 × 768 canvas. A 280px sidebar on the left, a 64px top bar across the
remaining 1086px, and a content column from x 304 to x 1342 (1038px wide, 24px margins).

### Whitespace Philosophy
Medium density: a loan list of ten rows fits on one canvas without scrolling, and every
row stays a comfortable 48px click target.

## Elevation & Depth

| Level | Treatment | Use |
|---|---|---|
| Page | Mist fill | Behind everything |
| Panel | Sheet fill, 1px Hairline border | Cards, tables, forms |
| Inset | Slate fill | Table header rows |

Hierarchy is tone and 1px borders only; the canvas has no confirmed elevation effect.

### Decorative Depth
None. Images are product photos in placeholder boxes, never decoration.

## Shapes

### Border Radius Scale

| Token | Value | Use |
|---|---|---|
| `{rounded.none}` | 0px | Sidebar, top bar, table rows |
| `{rounded.sm}` | 4px | Badges |
| `{rounded.md}` | 6px | Buttons, inputs |
| `{rounded.lg}` | 8px | Panels |

## Components

### Buttons

**`button-primary`**: Harbour fill, white `{typography.label-md}`, `{rounded.md}`, 40px
high, 20px side padding; hover is `{components.button-primary-hover}`; disabled is
`{components.button-disabled}`. One per screen.

**`button-secondary`**: white fill with a 1px Hairline border and Harbour text, same
geometry. Cancel, Back, secondary actions.

### Cards & Containers

**`card`**: Sheet fill, 1px Hairline border, `{rounded.lg}`, `{spacing.lg}` padding.

**`divider`**: a 1px Hairline rule between rows.

**`nav-item`** and **`nav-item-active`**: 48px rows in the sidebar; the active row has a
Tide fill, Harbour text, and a 4px Harbour strip on its left edge (a thin block, not a
one-sided border).

**`top-bar`**: 64px Sheet bar with the user's name and avatar on the right.

**`table-head`**: 40px Slate row of `{typography.label-sm}` column names.

### Inputs & Forms

**`input-text`**: Sheet fill, 1px Hairline border, `{rounded.md}`, 40px high, 12px side
padding. Selects share the same box. Labels sit 6px above in `{typography.caption}`.

**`input-error-text`**: `{typography.caption}` in the error colour under the field.

### Badges & Status

**`badge-on-loan`**, **`badge-returned`**, **`badge-overdue`**, **`badge-lost`**: 4px
corners, `{typography.label-sm}`, always a word inside.

## Do's and Don'ts

### Do
- Use Harbour ({colors.primary} — #0f5c8c) only for things that act.
- Separate panels with Hairline borders and Mist gaps.
- Put a word in every badge.
- Keep every row height a multiple of 4.
- Keep the sidebar and top bar identical on every screen.
- Mark a field label with `{typography.caption}` in Graphite.

### Don't
- Don't add elevation, frosted panels or motion; the canvas cannot reproduce them.
- Don't use a one-sided border; draw a thin block instead.
- Don't introduce a third font weight.
- Don't use a font other than Segoe UI.
- Don't use colour alone to show status.
- Don't round the sidebar or top bar.

## Responsive Behavior

### Breakpoints

| Name | Width | Key Changes |
|---|---|---|
| Canvas | 1366px fixed | None: the app is a fixed canvas |

### Touch Targets
- Navigation rows are 48px high; buttons and inputs 40px.

### Collapsing Strategy
- None. The canvas is fixed at 1366 × 768; a screen whose content is taller sets its own
  height and scrolls.

## Iteration Guide

1. Change one component at a time and reference it by its key.
2. Keep token names stable; mockups and screens refer to them.
3. Add states as suffixed components, not new colours.
4. Reference tokens; never write a hex value into a component.
5. Check every new effect against the Power Apps profile before adding it.

## Known Gaps

- No dark theme yet.
- Elevation: the team asked for soft card elevation; the canvas has no confirmed
  equivalent, so panels use a 1px Hairline border instead.
- The active navigation marker is a left-edge accent; one-sided borders are ruled out, so
  it is a 4px block along the edge.
