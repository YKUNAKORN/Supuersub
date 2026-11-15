---
version: alpha
name: "<Design system name>"
description: "<One paragraph: what the product is, who uses it, the feeling of the interface, and the two or three choices that create that feeling.>"
# Every value below is a placeholder that lints. Replace each one; keep the key order.
# Token names are lowercase kebab-case. Add tokens freely; remove a group's example
# entries only when the system truly has no such token.
colors:
  primary: "#1f4fd1"            # the action colour; must pass 4.5:1 with on-primary
  primary-hover: "#173da6"
  on-primary: "#ffffff"
  surface: "#f7f8fa"            # page background
  surface-raised: "#ffffff"     # cards, inputs
  on-surface: "#1b1d22"         # body and heading text
  text-muted: "#5b616e"         # secondary text; must still pass 4.5:1 on surfaces
  border: "#d5d9e0"
  success: "#1d6b45"
  on-success: "#ffffff"
  warning: "#8a5a00"
  on-warning: "#ffffff"
  error: "#b3261e"
  on-error: "#ffffff"
typography:
  # 9-15 levels. Required on each: fontFamily, fontSize, fontWeight, lineHeight.
  display:
    fontFamily: "<Display face>, system-ui, sans-serif"
    fontSize: 40px
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: "<Display face>, system-ui, sans-serif"
    fontSize: 32px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: 0px
  headline-md:
    fontFamily: "<Text face>, system-ui, sans-serif"
    fontSize: 24px
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: 0px
  title:
    fontFamily: "<Text face>, system-ui, sans-serif"
    fontSize: 20px
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: 0px
  body-lg:
    fontFamily: "<Text face>, system-ui, sans-serif"
    fontSize: 18px
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: 0px
  body-md:
    fontFamily: "<Text face>, system-ui, sans-serif"
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: 0px
  body-sm:
    fontFamily: "<Text face>, system-ui, sans-serif"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: 0px
  label:
    fontFamily: "<Text face>, system-ui, sans-serif"
    fontSize: 14px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: 0.01em
  caption:
    fontFamily: "<Text face>, system-ui, sans-serif"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: 0px
rounded:
  none: 0px
  sm: 4px
  md: 8px
  lg: 12px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  section: 64px
components:
  # Reference tokens; never write a colour literal here. Variants are suffixed keys.
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: 10px 20px
    height: 44px
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.on-primary}"
  button-secondary:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.primary}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: 10px 20px
    height: 44px
  card:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
    padding: "{spacing.lg}"
  input-text:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: 10px 12px
    height: 44px
  input-helper:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-muted}"
    typography: "{typography.caption}"
  divider:
    backgroundColor: "{colors.border}"
    height: 1px
  badge-success:
    backgroundColor: "{colors.success}"
    textColor: "{colors.on-success}"
    typography: "{typography.caption}"
    rounded: "{rounded.full}"
    padding: 2px 10px
  badge-warning:
    backgroundColor: "{colors.warning}"
    textColor: "{colors.on-warning}"
    typography: "{typography.caption}"
    rounded: "{rounded.full}"
    padding: 2px 10px
  badge-error:
    backgroundColor: "{colors.error}"
    textColor: "{colors.on-error}"
    typography: "{typography.caption}"
    rounded: "{rounded.full}"
    padding: 2px 10px
---

## Overview

<What the product is and who uses it, for what, on which devices. Target: `web` or
`power-apps`. The feeling the interface should create, and the principle that decides
close calls.>

**Key Characteristics:**
- <A concrete rule a reader could check on a screen, naming a token.>
- <Five to eight of these.>

## Colors

<One or two sentences on the palette's logic.>

### Brand & Accent
- **<Display name>** ({colors.primary} — #1f4fd1): <role, and where not to use it>.
- **<Display name>** ({colors.primary-hover} — #173da6): <role>.

### Surface
- **<Display name>** ({colors.surface} — #f7f8fa): <role>.
- **<Display name>** ({colors.surface-raised} — #ffffff): <role>.
- **<Display name>** ({colors.border} — #d5d9e0): <role>.

### Text
- **<Display name>** ({colors.on-surface} — #1b1d22): <role>.
- **<Display name>** ({colors.text-muted} — #5b616e): <role>.

### Semantic
- **<Display name>** ({colors.success} — #1d6b45) with {colors.on-success}: <role>.
- **<Display name>** ({colors.warning} — #8a5a00) with {colors.on-warning}: <role>.
- **<Display name>** ({colors.error} — #b3261e) with {colors.on-error}: <role>.

## Typography

### Font Family
- **Display**: `<stack>`: <why this face>.
- **Text and UI**: `<stack>`: <why this face>.

### Hierarchy

| Token | Size | Weight | Line Height | Letter Spacing | Use |
|---|---|---|---|---|---|
| `{typography.display}` | 40px | 600 | 1.1 | -0.02em | <use> |
| `{typography.body-md}` | 16px | 400 | 1.5 | 0px | <use> |

### Principles
- <Four to six rules: weight ladder, where tracking tightens, smallest size.>

### Note on Font Substitutes
<The open alternative for each preferred face, and any size or line-height adjustment.
Never state that a proprietary face is available.>

## Layout

### Spacing System
- **Base unit:** <4px or 8px>.
- **Tokens:** `{spacing.xs}` 4px · `{spacing.sm}` 8px · `{spacing.md}` 16px ·
  `{spacing.lg}` 24px · `{spacing.xl}` 32px · `{spacing.section}` 64px.
- <Common uses: card padding, form rows, section gaps.>

### Grid & Container
<Max width, columns, gutters. Under power-apps: the canvas (1366 × 768 by default).>

### Whitespace Philosophy
<One paragraph on density and why.>

## Elevation & Depth

| Level | Treatment | Use |
|---|---|---|
| <level> | <treatment> | <use> |

<How hierarchy is shown. Under power-apps: no shadows or blur; tone and 1px borders.>

### Decorative Depth
<Gradients, imagery, overlays, or "none" and why.>

## Shapes

### Border Radius Scale

| Token | Value | Use |
|---|---|---|
| `{rounded.none}` | 0px | <use> |
| `{rounded.sm}` | 4px | <use> |
| `{rounded.md}` | 8px | <use> |
| `{rounded.lg}` | 12px | <use> |
| `{rounded.full}` | 9999px | <use> |

## Components

### Buttons

**`button-primary`**: <fill, text, type, radius, padding, height by token; states:
`{components.button-primary-hover}`, focus, disabled; where it is used>.

**`button-secondary`**: <…>.

### Cards & Containers

**`card`**: <…>.

**`divider`**: <…>.

### Inputs & Forms

**`input-text`**: <…, including focus and error states>.

**`input-helper`**: <…>.

### Badges & Status

**`badge-success`**, **`badge-warning`**, **`badge-error`**: <…; status is never shown
by colour alone>.

## Do's and Don'ts

### Do
- <Six to ten rules naming tokens.>

### Don't
- <Six to ten rules, each the mirror of a real temptation.>

## Responsive Behavior

### Breakpoints

| Name | Width | Key Changes |
|---|---|---|
| <name> | <range> | <changes> |

### Touch Targets
- <Minimum size and which components meet it.>

### Collapsing Strategy
- <Navigation, grids, tables as width drops. Under power-apps: the fixed canvas.>

## Iteration Guide

1. Change one component at a time and reference it by its key.
2. Keep token names stable; mockups and screens refer to them.
3. Add states as suffixed components, not new colours.
4. Reference tokens; never write a hex value into a component.
5. <Rules specific to this system.>

## Known Gaps

- <What the system does not decide yet.>
- <Under power-apps: each requested effect the profile rules out, with its substitute.>
