---
name: Fixture Minimal
version: alpha
description: The smallest DESIGN.md that lints clean. Every invalid fixture is this file with one defect.
colors:
  primary: "#1f4fd1"
  on-primary: "#ffffff"
  surface: "#ffffff"
  on-surface: "#1b1d22"
typography:
  display: {fontFamily: "Inter, sans-serif", fontSize: 40px, fontWeight: 600, lineHeight: 1.1, letterSpacing: -0.02em}
  headline-lg: {fontFamily: "Inter, sans-serif", fontSize: 32px, fontWeight: 600, lineHeight: 1.2}
  headline-md: {fontFamily: "Inter, sans-serif", fontSize: 24px, fontWeight: 600, lineHeight: 1.25}
  title: {fontFamily: "Inter, sans-serif", fontSize: 20px, fontWeight: 600, lineHeight: 1.3}
  body-lg: {fontFamily: "Inter, sans-serif", fontSize: 18px, fontWeight: 400, lineHeight: 1.5}
  body-md: {fontFamily: "Inter, sans-serif", fontSize: 16px, fontWeight: 400, lineHeight: 1.5}
  body-sm: {fontFamily: "Inter, sans-serif", fontSize: 14px, fontWeight: 400, lineHeight: 1.45}
  label: {fontFamily: "Inter, sans-serif", fontSize: 14px, fontWeight: 600, lineHeight: 1.2, letterSpacing: 0.01em}
  caption: {fontFamily: "Inter, sans-serif", fontSize: 12px, fontWeight: 400, lineHeight: 1.4, fontStyle: italic}
rounded:
  sm: 4px
  md: 8px
spacing:
  base: 8px
  md: 16px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: 8px 16px
    borderColor: "{colors.on-surface}"
  card:
    backgroundColor: "#ffffff"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: "{spacing.md}"
---

## Overview

A minimal fixture. The primary action is `{components.button-primary}` in #1f4fd1.

## Colors

### Brand & Accent
- **Primary** (`{colors.primary}` — #1f4fd1).

## Typography

Body text is `{typography.body-md}`.

## Layout

Spacing steps on `{spacing.base}`.

## Elevation & Depth

Flat.

## Shapes

`{rounded.sm}` for buttons, `{rounded.md}` for cards.

## Components

`{components.card}` holds content.

## Do's and Don'ts

### Do
- Use the tokens.

### Don't
- Inline hex values.

## Responsive Behavior

Not applicable to a fixture.

## Iteration Guide

1. Change one component at a time.

## Known Gaps

None.
