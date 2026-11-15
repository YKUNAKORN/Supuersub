---
version: alpha
name: Token Fixture
description: Exercises every conversion tokens_to_css.py makes.
colors:
  primary: "#1f4fd1"
  on-primary: "#ffffff"
  surface: rgb(245, 246, 248)
typography:
  display:
    fontFamily: "Fraunces Variable, Georgia, serif"
    fontSize: 2rem
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: -0.02em
  body-md:
    fontFamily: "Segoe UI, system-ui, sans-serif"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 20px
    letterSpacing: 0px
rounded:
  md: 0.375rem
  full: 9999px
spacing:
  sm: 0.5rem
  md: 16px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: 0.5rem 1.25rem
    height: 40px
  card:
    backgroundColor: "#ffffff"
    padding: "{spacing.md}"
---

## Overview

Fixture for tests/test_tokens_to_css.py.
