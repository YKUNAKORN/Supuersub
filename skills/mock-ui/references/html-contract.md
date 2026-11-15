# The HTML contract between `mock-ui` and `create-app`

A mockup is two things at once: a prototype the user clicks through in a browser, and the
input the `create-app` skill converts into Power Apps screens. This file is the interface
between the two skills. `scripts/mock_lint.py` checks every rule that can be checked
mechanically; the check id is given beside each rule.

The rules exist because of how conversions have gone wrong. The `create-app` eval suite
holds five mockups that show it: a `<select>` drawn as a text box loses its constrained
choice (`multi-section-form`); a repeated row written once and then "and so on" is not a
screen (`card-grid`); a shadow nobody declared is either faked or silently dropped
(`impossible-effects`); and every fixture there is self-contained, because a file that
needs the network is not a reliable input.

Words used below: a **screen file** is one `.html` per screen; the **mockup folder** holds
the screen files, `index.html` and `sitemap.json`. In a project it is `supersub/mockup/`.

## 1. One file per screen

- Name: `supersub/mockup/<kebab-name>.html`, lowercase letters, digits and hyphens
  (`request-list.html`).
- The `<body>` carries the screen id and its display title:
  `<body data-screen="scrRequestList" data-title="Requests">`.
- The screen id is `scr` + PascalCase, letters and digits only, unique across the mockup
  (`screen-id`, `screen-duplicate`). `create-app` uses it as the Power Apps screen name,
  and every `Navigate()` target comes from it. `data-title` may be in any language
  (`screen-title` warns when it is missing).
- `index.html` is not a screen. It has no `data-screen`.
- A **state variant** (the list when it is empty, the form after a failed submit) is its
  own screen file too, listed with `"kind": "state"` and `"variantOf": "<ScreenId>"`.
  `index.html` links it; it is exempt from the reachability check because with
  JavaScript off nothing can trigger it, but it still needs a way back. For
  `create-app` it describes a second visible state of the screen it varies, not a new
  screen; say so when handing the mockup over.
- A **dialog** is its own screen file, listed with `"kind": "dialog"` in `sitemap.json`,
  drawn as the dialog panel on the canvas. Its buttons navigate back to the screen that
  opened it. This keeps it clickable with JavaScript off and convertible as a screen.

## 2. Self-contained

- Exactly one inline `<style>` element (`style-blocks`). No `<link rel="stylesheet">`.
- No URL with a scheme or `//host` in `src`, `href`, `action`, `formaction`, `poster`, an
  `@import` or a `url(…)` (`external-resource`). That rules out web fonts, CDNs, remote
  images and remote scripts. `data:` URIs are allowed but rarely needed.
- No reference to a local non-HTML file either (`local-asset`): the page must work when
  it is the only file the user has.
- Icons are inline `<svg>` with `fill="currentColor"`, or CSS shapes.
- Images are placeholder boxes with a fill and `data-image="<what it shows>"`:
  `<div class="photo" data-image="Photo of the borrowed item"></div>`.
- No `<script>` (`script`). Navigation must work with JavaScript off, and the contract
  needs no other behaviour.

## 3. Tokens first

- The first thing in `<style>` is one `:root { … }` block generated from the `DESIGN.md`
  front matter by `scripts/tokens_to_css.py`. Never edit it by hand; regenerate it.
- Every colour, font, font size, radius and spacing value in the rest of the CSS is
  `var(--…)` of a name from that block. The names are fixed:

  | `DESIGN.md` token | CSS custom property |
  |---|---|
  | `colors.<name>` | `--color-<name>` |
  | `typography.<level>.fontFamily` / `fontSize` / `fontWeight` / `lineHeight` / `letterSpacing` | `--font-<level>-family` / `-size` / `-weight` / `-line-height` / `-letter-spacing` |
  | `rounded.<name>` | `--radius-<name>` |
  | `spacing.<name>` | `--space-<name>` |
  | `components.<name>.backgroundColor` / `textColor` / `rounded` / `padding` / `height` / `width` / `size` | `--<name>-bg` / `-text` / `-radius` / `-padding` / `-height` / `-width` / `-size` |
  | canvas (power-apps only) | `--canvas-width`, `--canvas-height` |

- A component property that references a token becomes `var()` of that token, so
  `--button-primary-bg: var(--color-primary);`. Style a button with
  `background: var(--button-primary-bg)`, and `create-app` can follow the chain back to
  the token.
- A `var(--x)` with no `--x` in `:root` is an error (`var-undefined`). A hex colour
  outside `:root` is a warning (`literal-hex`). With `--design DESIGN.md` the linter also
  reports a `:root` value that differs from the `DESIGN.md`, or a missing token
  (`token-drift`).
- Pixel numbers for geometry (`left: 304px`, `width: 686px`) are not tokens; write them as
  numbers. Spacing tokens are for the gaps the design names.

## 4. No dead controls

Every `<a>`, `<button>`, `[role="button"]` and `<input type="submit|button|reset|image">`
is one of these (`dead-control` otherwise):

- **Navigation.** It carries `data-nav="<ScreenId>"`, and with JavaScript off a click
  really opens that screen's file:
  - `<a href="request-list.html" data-nav="scrRequestList">`, styled as a button when it
    looks like one; or
  - a submit button inside `<form action="request-list.html">` (or with
    `formaction="…"`).
  `data-nav` must equal the `data-screen` of the file it opens (`nav-mismatch`), and the
  file must exist (`broken-link`). A control that navigates without `data-nav` is a
  `nav-mismatch` too: the navigation is real but undeclared.
- **Action that stays on the screen.** It carries `data-action="<verb>:<Object>"`
  (`action-format`), and a `<button>` is `type="button"` so it does not submit its form.
  Verbs are lowercase with hyphens, the object is the list, flow or thing it acts on:

  | Verb | Object | Example |
  |---|---|---|
  | `submit` | the list a form writes to | `submit:Requests` |
  | `update`, `delete` | the list | `update:Loans` |
  | `run-flow` | the Power Automate flow | `run-flow:NotifyApprover` |
  | `filter`, `sort`, `search` | the list being shown | `filter:Loans` |
  | `select` | the item being chosen | `select:Request` |
  | `download`, `upload`, `print`, `refresh` | the thing | `upload:Attachment` |

  Several actions that run in order are space-separated:
  `data-action="submit:Loans run-flow:NotifyApprover"`.
- **Action that then moves on** carries both: the form's submit button has
  `data-action="submit:Loans" data-nav="scrLoanList"` inside
  `<form action="loan-list.html">`.

`[role="button"]` on a `<div>` cannot navigate without JavaScript, so it can only carry
`data-action`. Prefer a real `<button>`.

A link to the screen it sits on (the active sidebar row) is allowed and is chrome: the
navigation-graph checks ignore it, and `sitemap.json` need not list it.

## 5. Real form controls

- Use the element that matches the data: `<input type="text|number|date|email|…">`,
  `<select>` with its real options (at least two, `select-options`), `<textarea>`,
  `<input type="checkbox|radio">`. A choice from a fixed set is always a `<select>` or
  radios, never a text box.
- Every field has `<label for="<its id>">` (`label-missing`).
- A field backed by data carries `data-field="<ColumnInternalName>"`, and its form (or
  any container around it) carries `data-source="<ListName>"` (`field-source`). Internal
  names are ASCII PascalCase with no spaces (`data-name`); the visible label may be in any
  language.
- A field that is not stored anywhere (a filter, a search box) has no `data-field`.

## 6. Repeating data

- The container carries `data-repeat="<ListName>"` and holds **two or three sample rows**
  as its direct children (`repeat-rows`). Headers sit outside the container.
- Inside each row, cells that show a column carry `data-field`.
- Write every row in full. Sample rows differ in their values (and in status, where the
  list has one) so the user sees the range.
- A fixed set that is not data (navigation rows, step indicators, a fixed grid of
  tiles) is written out in full however many items it has; it gets no `data-repeat`.

## 7. Target `power-apps`

The fixed canvas from the hand-off contract (D5): 1366 × 768 unless the user says
otherwise.

- **Explicit canvas.** `body { width: var(--canvas-width); height: …px; }` resolving to
  px. The width equals the sitemap's `canvas.width`; the height is at least
  `canvas.height` and equals the screen's `height` in `sitemap.json` (`canvas-size`).
- **Overflow.** When content runs past the viewport, the height is still explicit (the
  content bottom plus the bottom margin, rounded up to 8) and the screen has
  `"scrolls": true` in `sitemap.json` (`scroll-flag`). `create-app` sets the screen's own
  `Height` from it.
- **Geometry by arithmetic.** Lengths are px: `position: absolute` with `left`, `top`,
  `width`, `height` is the most predictable, and flex or grid with px sizes and px gaps
  is fine because `create-app`'s layout mapping resolves them by arithmetic. No length
  that depends on text or viewport: `em`, `rem`, `vw`, `vh`, `ch`, `min-content`,
  `max-content`, `fit-content`, `auto-fill`, `auto-fit` (`pa-geometry`, after resolving
  `var()`). Give every text box an explicit height; text that could wrap gets a height
  for the number of lines it may use.
- **Only what the profile allows.** `references/shared/powerapps-profile.md` lists the
  effects the canvas cannot reproduce: `box-shadow`, `backdrop-blur`, `css-transition`,
  `group-hover`, `border-left-only` (any one-sided border), `non-segoe-font`. Leave them
  out (`pa-effect`), using the profile's substitute: a 1px border for elevation, an
  opaque fill for blur, instant hover states on the control itself, a thin block along
  the edge for a one-sided border, Segoe UI first in every font stack.
- **When the user wants the intended look anyway**, mark the element and scope the CSS to
  the mark, so the effect cannot leak onto anything unmarked:

  ```html
  <aside class="card actions" data-unsupported="box-shadow">…</aside>
  ```
  ```css
  .actions[data-unsupported~="box-shadow"] { box-shadow: 0px 2px 8px var(--color-border); }
  ```

  The mark tells `create-app` the effect is intended and known to be impossible, so it
  declares the gap in the `.pa.yaml` and applies the substitute instead of faking or
  silently dropping it. The id must be one the profile defines (`unsupported-id`). Inline `style`
  attributes count too: an element whose `style` uses an effect needs the mark itself.
- Controls the profile calls unattempted (a date picker, a toggle, a gallery) are fine in
  the mockup when the design needs them: they are real HTML. `create-app` hands over an
  isolated paste test for each one rather than a guess.

## 8. Target `web`

Responsive layout is allowed: relative units, wrapping flex and grid, media queries.
Rules 1–6 still apply, and so does the linter, without the power-apps checks.

## 9. `sitemap.json`

One per mockup folder, validated against `assets/sitemap.schema.json` (`sitemap-invalid`):

```json
{
  "version": 1,
  "target": "power-apps",
  "canvas": { "width": 1366, "height": 768 },
  "design": "<path of DESIGN.md relative to this file>",
  "start": "scrHome",
  "screens": [
    {
      "id": "scrHome",
      "file": "home.html",
      "title": "Home",
      "purpose": "Landing screen with the user's open requests",
      "height": 768,
      "nav": [ { "label": "New request", "to": "scrNewRequest" } ],
      "data": [ { "source": "Requests", "mode": "read", "fields": ["Title", "Status"] } ],
      "actions": [ { "id": "run-flow:NotifyApprover", "on": "Submit" } ]
    }
  ]
}
```

- In the standard project layout the mockup sits two folders below the project root, so
  `design` is the parent of the parent folder followed by `DESIGN.md`. With no
  `DESIGN.md`, omit `design` and write the style brief in `styleBrief`.
- `canvas` and each screen's `height` are required under `power-apps`; `scrolls` is
  `true` when `height` exceeds `canvas.height`. `kind` is `screen` (default), `dialog`
  or `state`; a `state` names the screen it varies in `variantOf`.
- **Screens** match the screen files one to one: same file, same id (`sitemap-screens`).
  `start` is one of them.
- **`nav`** lists every screen this screen links to, and nothing else; the linter
  compares the set of targets with the links it finds in the HTML (`sitemap-nav`). Every
  screen except a `state` variant must be reachable from `start` by clicking
  (`unreachable`); a screen with no way
  back to `start` is a warning (`no-way-back`).
- **`data`** names each list the screen reads or writes (`mode`: `read`, `create`,
  `update`, `delete`) with the columns it shows or sets. It must agree with the
  `data-source`, `data-repeat` and `data-field` attributes (`sitemap-data`).
  `create-list` builds the lists from it.
- **`actions`** lists every `data-action` id on the screen, with the label of the control
  that triggers it (`sitemap-actions`). `create-flow` plans the flows from the
  `run-flow:` ones.

## 10. `index.html`

A screen map, not a screen: the mockup's name, the target and canvas, the `DESIGN.md` it
came from (or the style brief), then every screen as a link in flow order with its id and
purpose (`index-missing` warns on a screen it does not link). End it with the lists and
flows the mockup implies. Its links carry `data-nav` like any other.
