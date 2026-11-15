---
version: alpha
name: Fixture Desk
description: Minimal design used only by the mock_lint tests.
colors:
  primary: "#1f4fd1"
  on-primary: "#ffffff"
  surface: "#f5f6f8"
  surface-raised: "#ffffff"
  on-surface: "#1b1d22"
  border: "#d5d9e0"
typography:
  body-md:
    fontFamily: "Segoe UI, sans-serif"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5
  label-md:
    fontFamily: "Segoe UI, sans-serif"
    fontSize: 14px
    fontWeight: 700
    lineHeight: 20px
rounded:
  md: 6px
spacing:
  md: 16px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.md}"
    height: 40px
---

## Overview

Test fixture. Target: `power-apps`.
