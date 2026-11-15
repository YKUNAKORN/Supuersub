---
name: mock-ui
description: >-
  Turns a DESIGN.md plus a description of what the product must do into a clickable HTML
  mockup: one self-contained .html per screen with every button and link wired, an
  index.html screen map and a sitemap.json. Use when someone wants a mockup, wireframe or
  click-through prototype, asks to "prototype the screens" or "make HTML pages from this
  design", or wants screens planned before building a Power Apps app. Not for writing
  the design system itself (that is design-md) and not for converting HTML into Power
  Apps (that is create-app, which reads what this skill writes).
---

# Mockup: screen inventory, then linked HTML pages

Produce a mockup folder: one `.html` per screen, `index.html`, `sitemap.json`. Reply in
the user's language; visible text in the pages follows it, identifiers stay ASCII.
Paths are relative to this skill's folder: `${CLAUDE_SKILL_DIR}`, or run from that folder.

## The workflow (in order)

1. **Inputs.** A `DESIGN.md` (a path, an attachment or pasted text) and the requirements:
   what the product does, for whom, which records it keeps, what happens on submit. With
   no `DESIGN.md`, say so and offer the `design-md` skill. If the user declines, agree a
   short style brief (primary colour, surface, text colour, font, corner radius) and
   record it in `index.html` and in `sitemap.json` as `styleBrief`.
2. **Target.** `power-apps` when the mockup is headed for `create-app` (the default when
   the `DESIGN.md` says `Target: power-apps` or the user mentions Power Apps), otherwise
   `web`. For `power-apps`, read
   [`references/shared/powerapps-profile.md`](references/shared/powerapps-profile.md) now;
   the canvas is 1366 × 768 unless the user says otherwise.
3. **Screen inventory before any HTML.** Show one table: screen id (`scr` +
   PascalCase), file name, title, purpose, the data it reads or writes (list and
   columns), and where each control leads or which action it fires. Mark the start
   screen. Check that every screen is reachable and has a way back. **Get the user's
   agreement**; changing a row now is cheap, changing ten HTML files is not.
4. **Generate the token block:**
   `python3 ${CLAUDE_SKILL_DIR}/scripts/tokens_to_css.py DESIGN.md --target <target>`
   (`scripts/tokens_to_css.py`). Paste its `:root` block unchanged as the first thing in
   every page's `<style>`. With only a style brief, write the same variable names by hand.
5. **Write the pages** from [`assets/page.template.html`](assets/page.template.html),
   following [`references/html-contract.md`](references/html-contract.md) and the
   building blocks in [`references/screen-patterns.md`](references/screen-patterns.md).
   Write the shared chrome first, then paste it unchanged into every screen. **Write
   every screen in full**: every row, field, card and navigation item, never "repeat
   for the rest". [`assets/example/`](assets/example/index.html) is a finished,
   lint-clean three-screen mockup; read it for the level of detail, never copy its
   content.
6. **Write `sitemap.json`** (schema: [`assets/sitemap.schema.json`](assets/sitemap.schema.json))
   **and `index.html`** from [`assets/index.template.html`](assets/index.template.html).
7. **Lint** with `python3 ${CLAUDE_SKILL_DIR}/scripts/mock_lint.py supersub/mockup --design DESIGN.md`
   (`scripts/mock_lint.py`; the target comes from `sitemap.json`). Fix every error and
   lint again until the verdict has no errors. Report every warning with the fix you
   made or the reason it stands.
8. **Hand over** (next section).

## Rules

- **Self-contained.** One inline `<style>`, no web font, CDN, remote image or script.
  Icons are inline SVG; images are placeholder boxes with `data-image="<what it shows>"`.
- **No dead controls.** Every link and button navigates (`data-nav` plus a real `href` or
  form `action`, so it works from disk with JavaScript off) or names its action
  (`data-action="submit:Requests"`, `run-flow:NotifyApprover`), or both.
- **Real form controls.** A choice is a `<select>` with its real options or radios, a
  date is a date input, every field has a `<label for>`. Data-backed fields carry
  `data-field`, their form `data-source`; repeated data sits in `data-repeat` with two or
  three full sample rows.
- **Tokens first.** Every colour, font, size, radius and spacing value is `var(--…)` from
  the generated block. Geometry is px.
- **Under `power-apps`:** explicit px canvas on `<body>`, px geometry throughout, no
  effect the profile rules out. When the user still wants one, mark the element
  `data-unsupported="<profile id>"` and scope the CSS to that mark, so the intended look
  is visible and `create-app` knows to declare it and apply the substitute.
- **Original content.** Invent names and sample data; never reproduce another product's
  branding or a real person's details.
- **One mockup folder per product.** Write it under `supersub/mockup/` in the project when
  one is writable; otherwise create the files and hand them to the user.

## Hand-off

[`references/shared/handoff.md`](references/shared/handoff.md) is the contract between
the five skills. Never assume an earlier skill ran. Hand over:

- the files, and how to open the mockup: double-click `index.html`, or open it in a
  browser, then click through;
- the lint verdict and every warning;
- **the lists the mockup implies**: every `data-source` and `data-repeat`, with the
  columns from `data-field`;
- **the flows it implies**: every `run-flow:` action, with the screen and control that
  triggers it;
- the next steps: **`create-app`** converts each screen into a `.pa.yaml`;
  **`create-list`** builds the lists; **`create-flow`** plans the flows.
