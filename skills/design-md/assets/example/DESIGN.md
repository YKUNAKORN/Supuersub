---
version: alpha
name: Mossgate Commons
description: A calm, outdoorsy booking site for a network of community garden plots. Warm paper surfaces, one moss-green action colour and a terracotta accent for seasonal moments; an editorial serif for headings and a plain humanist sans for everything a gardener has to read. Generous spacing, soft 8px corners, no decorative shadows.
colors:
  primary: "#2f6b3a"
  primary-hover: "#245530"
  on-primary: "#ffffff"
  accent: "#b4532a"
  on-accent: "#ffffff"
  surface: "#fbfaf6"
  surface-raised: "#ffffff"
  surface-sunken: "#f1efe7"
  on-surface: "#1e2420"
  text-muted: "#5a625c"
  border: "#d9d5c8"
  success: "#1d6b45"
  on-success: "#ffffff"
  warning: "#8a5a00"
  on-warning: "#ffffff"
  error: "#b3261e"
  on-error: "#ffffff"
  info: "#1f5f8b"
  on-info: "#ffffff"
typography:
  display-lg:
    fontFamily: "Fraunces, Georgia, serif"
    fontSize: 48px
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: -0.02em
  display-md:
    fontFamily: "Fraunces, Georgia, serif"
    fontSize: 36px
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: "Fraunces, Georgia, serif"
    fontSize: 28px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: 0px
  headline-md:
    fontFamily: "Source Sans 3, system-ui, sans-serif"
    fontSize: 22px
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: 0px
  title:
    fontFamily: "Source Sans 3, system-ui, sans-serif"
    fontSize: 18px
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: 0px
  body-lg:
    fontFamily: "Source Sans 3, system-ui, sans-serif"
    fontSize: 18px
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: 0px
  body-md:
    fontFamily: "Source Sans 3, system-ui, sans-serif"
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: 0px
  body-sm:
    fontFamily: "Source Sans 3, system-ui, sans-serif"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: 0px
  label-md:
    fontFamily: "Source Sans 3, system-ui, sans-serif"
    fontSize: 15px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: 0.01em
  label-sm:
    fontFamily: "Source Sans 3, system-ui, sans-serif"
    fontSize: 12px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: 0.04em
  caption:
    fontFamily: "Source Sans 3, system-ui, sans-serif"
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: 0px
  data-mono:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: 0px
rounded:
  none: 0px
  sm: 4px
  md: 8px
  lg: 14px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
  section: 80px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: 10px 20px
    height: 44px
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.on-primary}"
  button-primary-disabled:
    backgroundColor: "{colors.surface-sunken}"
    textColor: "{colors.text-muted}"
  button-secondary:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.primary}"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: 10px 20px
    height: 44px
  button-seasonal:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    typography: "{typography.label-md}"
    rounded: "{rounded.full}"
    padding: 10px 24px
    height: 44px
  text-link:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    typography: "{typography.body-md}"
  nav-bar:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.on-surface}"
    typography: "{typography.label-md}"
    height: 64px
    padding: 0px 32px
  plot-card:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
    padding: "{spacing.lg}"
  season-panel:
    backgroundColor: "{colors.surface-sunken}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-lg}"
    rounded: "{rounded.lg}"
    padding: "{spacing.xl}"
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
  input-error-text:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.error}"
    typography: "{typography.caption}"
  divider:
    backgroundColor: "{colors.border}"
    height: 1px
  badge-available:
    backgroundColor: "{colors.success}"
    textColor: "{colors.on-success}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.full}"
    padding: 2px 10px
  badge-waitlist:
    backgroundColor: "{colors.warning}"
    textColor: "{colors.on-warning}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.full}"
    padding: 2px 10px
  badge-closed:
    backgroundColor: "{colors.error}"
    textColor: "{colors.on-error}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.full}"
    padding: 2px 10px
  alert-info:
    backgroundColor: "{colors.info}"
    textColor: "{colors.on-info}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: "{spacing.md}"
  footer:
    backgroundColor: "{colors.surface-sunken}"
    textColor: "{colors.text-muted}"
    typography: "{typography.body-sm}"
    padding: 48px 32px
---

## Overview

Mossgate Commons is the booking site for a network of community garden plots. Its
users are neighbours, mostly not technical, who come a few times a year: to find a free
plot near them, join a waitlist, or renew before the season starts. Many read on a phone
standing at the garden gate. Target: `web`.

The interface should feel like a well-kept noticeboard: calm, warm and trustworthy, never
like a dashboard. Paper-toned surfaces carry the content; one moss-green colour marks
every action; a terracotta accent appears only for seasonal moments (spring sign-up,
harvest day). When two choices are close, choose the one that is easier to read outdoors.

**Key Characteristics:**
- Warm paper surface ({colors.surface} — #fbfaf6) instead of pure white for the page.
- One action colour, Moss ({colors.primary} — #2f6b3a); nothing else looks clickable.
- Terracotta ({colors.accent} — #b4532a) at most once per screen, for seasonal calls.
- Editorial serif headings (Fraunces) over a plain humanist sans body (Source Sans 3).
- Body text at 16px with 1.55 line height; nothing a user must read is below 13px.
- Soft 8px corners on controls, 14px on cards, full pills only for status and seasonal.
- Flat surfaces: depth comes from tone and 1px borders, never shadows.

## Colors

The palette is one green action colour on warm neutrals, with a single warm accent and a
full set of status colours. Every filled colour has an `on-` partner that passes 4.5:1.

### Brand & Accent
- **Moss** ({colors.primary} — #2f6b3a): every primary button, link and focus ring. The
  only colour that means "you can act here".
- **Deep Moss** ({colors.primary-hover} — #245530): hover and pressed state of Moss.
- **Terracotta** ({colors.accent} — #b4532a): seasonal calls to action only, one per
  screen. Never for errors, which have their own red.

### Surface
- **Paper** ({colors.surface} — #fbfaf6): the page background.
- **Sheet** ({colors.surface-raised} — #ffffff): cards, inputs, the navigation bar.
- **Soil** ({colors.surface-sunken} — #f1efe7): panels set into the page, the footer,
  and disabled buttons.
- **Twine** ({colors.border} — #d9d5c8): 1px borders on cards and inputs, and dividers.

### Text
- **Ink** ({colors.on-surface} — #1e2420): all body and heading text on every surface.
- **Pencil** ({colors.text-muted} — #5a625c): helper text, captions, footer text,
  disabled labels. Still 4.5:1 on Paper, Sheet and Soil.
- **On colour** ({colors.on-primary} — #ffffff): text on Moss, Terracotta and every
  status fill.

### Semantic
- **Available** ({colors.success} — #1d6b45) with {colors.on-success}: free plots.
- **Waitlist** ({colors.warning} — #8a5a00) with {colors.on-warning}: full, joinable.
- **Closed / Error** ({colors.error} — #b3261e) with {colors.on-error}: closed plots,
  form errors.
- **Notice** ({colors.info} — #1f5f8b) with {colors.on-info}: neutral announcements.

Status is never shown by colour alone: every badge carries a word, and every error a
sentence.

## Typography

### Font Family
- **Display**: `Fraunces, Georgia, serif`, an open-licence serif with a friendly,
  slightly old-fashioned voice, used for the three largest levels only.
- **Text and UI**: `Source Sans 3, system-ui, sans-serif`, an open-licence humanist sans
  that stays legible small and in bright light.
- **Figures**: `IBM Plex Mono, ui-monospace, monospace` for plot numbers, dates and
  fees, so columns of figures line up.

### Hierarchy

| Token | Size | Weight | Line Height | Letter Spacing | Use |
|---|---|---|---|---|---|
| `{typography.display-lg}` | 48px | 600 | 1.1 | -0.02em | Home page headline |
| `{typography.display-md}` | 36px | 600 | 1.15 | -0.01em | Garden page headline |
| `{typography.headline-lg}` | 28px | 600 | 1.2 | 0px | Section headings |
| `{typography.headline-md}` | 22px | 600 | 1.3 | 0px | Card group headings |
| `{typography.title}` | 18px | 600 | 1.35 | 0px | Card titles, dialog titles |
| `{typography.body-lg}` | 18px | 400 | 1.6 | 0px | Lead paragraphs, season panel |
| `{typography.body-md}` | 16px | 400 | 1.55 | 0px | Default text, inputs |
| `{typography.body-sm}` | 14px | 400 | 1.5 | 0px | Secondary text, footer, alerts |
| `{typography.label-md}` | 15px | 600 | 1.2 | 0.01em | Buttons, navigation |
| `{typography.label-sm}` | 12px | 600 | 1.2 | 0.04em | Badges |
| `{typography.caption}` | 13px | 400 | 1.4 | 0px | Helper and error text |
| `{typography.data-mono}` | 14px | 400 | 1.45 | 0px | Plot numbers, dates, fees |

### Principles
- Serif only at 28px and above; below that, everything is the sans.
- Two weights: 400 for reading, 600 for headings, labels and anything clickable.
- Negative letter spacing only on the two display levels.
- Badges are the only small text; they get positive spacing to stay readable at 12px.
- Figures that users compare (fees, plot sizes, dates) use `{typography.data-mono}`.

### Note on Font Substitutes
All three families are open-licence and can be self-hosted. Where they cannot be loaded,
the stacks fall back to Georgia, the system UI face and the system monospace. With the
system UI face, keep the sizes and drop body line height to 1.5; system faces run
slightly taller.

## Layout

### Spacing System
- **Base unit:** 8px, with a 4px half step for tight internal gaps.
- **Tokens:** `{spacing.xs}` 4px · `{spacing.sm}` 8px · `{spacing.md}` 16px ·
  `{spacing.lg}` 24px · `{spacing.xl}` 32px · `{spacing.xxl}` 48px ·
  `{spacing.section}` 80px.
- **Card padding:** `{spacing.lg}`. **Season panel padding:** `{spacing.xl}`.
- **Form rows:** `{spacing.md}` between fields, `{spacing.xs}` between a field and its
  helper text.
- **Sections:** `{spacing.section}` between page sections on desktop, `{spacing.xxl}` on
  phones.

### Grid & Container
- Max content width 1120px, centred, with 24px side margins on phones.
- 12-column grid with 24px gutters on desktop; plot cards take 4 columns (three per row),
  6 on tablets, 12 on phones.
- Forms never exceed 560px wide, whatever the screen.

### Whitespace Philosophy
Space is what makes the site feel unhurried. A page shows one task at a time: find a
plot, or renew, or read the news. Generous gaps between sections mean a user standing in
sunlight can still find their place after glancing away.

## Elevation & Depth

| Level | Treatment | Use |
|---|---|---|
| Page | {colors.surface} | Page background |
| Raised | {colors.surface-raised} plus a 1px {colors.border} border | Cards, inputs, navigation |
| Set-in | {colors.surface-sunken}, no border | Season panel, footer |

Hierarchy comes from tone and borders, never from shadows. A card is white on paper with
a hairline; a panel is a shade darker than the page. Focus is a 2px {colors.primary}
outline offset by 2px, the only "lift" in the system.

### Decorative Depth
None in the interface. Atmosphere comes from photographs of the gardens, shown full
width at the top of a garden page, never behind text.

## Shapes

### Border Radius Scale

| Token | Value | Use |
|---|---|---|
| `{rounded.none}` | 0px | Full-width photographs, the navigation bar |
| `{rounded.sm}` | 4px | Checkboxes, small tags inside tables |
| `{rounded.md}` | 8px | Buttons, inputs, alerts |
| `{rounded.lg}` | 14px | Plot cards, season panel |
| `{rounded.full}` | 9999px | Status badges, the seasonal button |

### Iconography
Outline icons with a 1.5px stroke and rounded joins, at 20px in text and 24px in
navigation, always in the colour of the text beside them.

## Components

### Navigation

**`nav-bar`**: {colors.surface-raised} bar, 64px high, with a 1px {colors.border}
bottom border. Logo left, links in `{typography.label-md}` and {colors.on-surface}, the
current page underlined in {colors.primary}. Padding 0 × 32px.

### Buttons

**`button-primary`**: {colors.primary} fill, {colors.on-primary} text in
`{typography.label-md}`, `{rounded.md}`, padding 10px × 20px, 44px high. One per screen
for the main action ("Book this plot").
- Hover and pressed: `{components.button-primary-hover}`, fill {colors.primary-hover}.
- Disabled: `{components.button-primary-disabled}`, fill {colors.surface-sunken}, text
  {colors.text-muted}, with a sentence nearby saying why it is disabled.
- Focus: 2px {colors.primary} outline, offset 2px.

**`button-secondary`**: {colors.surface-raised} fill, {colors.primary} text, 1px
{colors.primary} border, otherwise as `{components.button-primary}`. For the second
action ("Join waitlist").

**`button-seasonal`**: {colors.accent} fill, {colors.on-accent} text, `{rounded.full}`,
padding 10px × 24px. Only for the one seasonal call on the home page.

**`text-link`**: {colors.primary} text in `{typography.body-md}`, underlined, on any
surface.

### Cards & Containers

**`plot-card`**: {colors.surface-raised}, 1px {colors.border} border, `{rounded.lg}`,
padding `{spacing.lg}`. Photo on top (4:3, corners matching the card), plot name in
`{typography.title}`, size and fee in `{typography.data-mono}`, a status badge, then
`{components.button-primary}` or `{components.button-secondary}`.

**`season-panel`**: {colors.surface-sunken}, no border, `{rounded.lg}`, padding
`{spacing.xl}`, text in `{typography.body-lg}`. Holds dates and news for the season.

**`divider`**: a 1px line in {colors.border}, full width of its container.

### Inputs & Forms

**`input-text`**: {colors.surface-raised}, 1px {colors.border} border, `{rounded.md}`,
44px high, padding 10px × 12px, text in `{typography.body-md}`. Label above in
`{typography.label-md}`. Focus: border becomes 2px {colors.primary}.
- **`input-helper`**: `{typography.caption}` in {colors.text-muted}, 4px below.
- **`input-error-text`**: replaces the helper, in {colors.error}; the input border turns
  {colors.error} too.

### Badges & Status

**`badge-available`**, **`badge-waitlist`**, **`badge-closed`**: pills in
`{rounded.full}`, `{typography.label-sm}`, padding 2px × 10px, on {colors.success},
{colors.warning} and {colors.error} respectively, each with white text and always a word
("Available", "Waitlist", "Closed").

**`alert-info`**: {colors.info} fill, {colors.on-info} text in `{typography.body-sm}`,
`{rounded.md}`, padding `{spacing.md}`, for announcements at the top of a page.

### Footer

**`footer`**: {colors.surface-sunken}, text in {colors.text-muted} and
`{typography.body-sm}`, padding 48px × 32px. Contact, opening hours, accessibility
statement.

## Do's and Don'ts

### Do
- Use {colors.primary} for every action and nothing else.
- Keep one `{components.button-primary}` per screen.
- Put a word in every status badge.
- Use `{typography.data-mono}` for fees, sizes and dates.
- Keep forms one column and at most 560px wide.
- Show the reason next to any disabled button.
- Leave `{spacing.section}` between page sections on desktop.

### Don't
- Don't use {colors.accent} for errors or for more than one element per screen.
- Don't add shadows; use a {colors.border} hairline or a tone step.
- Don't set the serif below 28px.
- Don't put text over photographs.
- Don't use pure black text; {colors.on-surface} is the darkest text colour.
- Don't show status by colour alone.

## Responsive Behavior

### Breakpoints

| Name | Width | Key Changes |
|---|---|---|
| Phone | up to 639px | One column; navigation collapses to a menu button; section gaps drop to `{spacing.xxl}` |
| Tablet | 640–1023px | Plot cards two per row; season panel full width |
| Desktop | 1024px and up | Plot cards three per row; content locks at 1120px |

### Touch Targets
- Minimum 44 × 44px. Buttons and inputs are 44px high by token.
- Badges are not interactive, so their 20px height is fine.

### Collapsing Strategy
- **Navigation:** links collapse into a menu below 640px; the logo and the menu button
  stay.
- **Plot grid:** 3 → 2 → 1 columns.
- **Headlines:** `{typography.display-lg}` becomes `{typography.display-md}` below 640px.

## Iteration Guide

1. Change one component at a time and reference it by its key, e.g.
   `{components.plot-card}`.
2. Keep token names stable; mockups and screens refer to them. Change values, not names.
3. Add states as suffixed components (`-hover`, `-disabled`), not as new colours.
4. Reference tokens; never write a hex value into a component.
5. A new colour needs a role in Colors, an `on-` partner that passes 4.5:1, and a
   component that uses it.
6. Record each decision that is not obvious from the tokens in this file's prose.

## Known Gaps

- Dark mode is not designed yet; surfaces and text would need a second set of tokens.
- Map views of garden locations are not specified; they will need their own marker and
  cluster styles.
- Data tables for administrators are out of scope for this public site.
