# Screen patterns

Building blocks for mockup screens. Each one says what it is for, how to mark it up so it
obeys `html-contract.md`, the geometry that keeps it convertible under `power-apps`, and
what `create-app` turns it into. The finished example in `assets/example/` uses the shell,
list, form and detail patterns; read its files for complete markup.

Geometry below assumes the `power-apps` canvas, 1366 × 768. Under `web`, keep the
structure and attributes and let the layout flow.

**Write every screen in full.** Repeated structures (navigation rows, form fields, cards,
table rows) are written out every time. A file that shows three rows and a comment saying
"repeat for the rest" is not a screen anybody can click through or convert.

## Shared chrome first

Decide the chrome (sidebar, top bar, footer) once, write its CSS and markup once, then
paste it unchanged into every screen file. Only the active navigation row differs. A
screen whose chrome is 4px off from its neighbours makes the prototype jump and the
converted app inconsistent.

## App shell

Persistent navigation around a content column.

```
x 0          280                                              1366
  ┌──────────┬────────────────────────────────────────────────┐ y 0
  │ logo     │ top bar: title / user name, role, avatar        │
  │          ├────────────────────────────────────────────────┤ y 64
  │ nav row  │   content column x 304 … 1342 (1038 wide)        │
  │ nav row  │   first line at y 88                             │
  │ …        │                                                  │
  └──────────┴────────────────────────────────────────────────┘ y 768
```

- Sidebar: `<nav class="sidebar">`, 280 × 768. Logo at (24, 18). Nav rows start at
  y 104 with a 48px pitch (104, 152, 200, …).
- Each nav row is `<a class="nav-item" href="<file>" data-nav="<ScreenId>">` holding an
  inline-SVG icon at (16, 12) and the label at x 56. `create-app` makes every nav row a
  Button, so draw it as one clickable row, never as text next to an icon link.
- The active row has its own fill and a marker block
  `<span class="nav-marker"></span>` 4 × 48 at its left edge. That block, not a
  `border-left`, is the substitute the profile names for a one-sided border.
- Top bar: 1086 × 64 at x 280, then a 1px rule block at y 63. User name and role
  right-aligned, avatar placeholder 40 × 40 at x 1022 (relative to the bar), y 12.

## List

Many records of one list.

- Title row: `<h1>` at (304, 88), 36 high; primary action at the right, a 40-high button
  at y 86 so it centres on the title.
- Filters (optional): labelled `<select>` and `<input>` with no `data-field`, and an
  Apply `<button type="button" data-action="filter:<List>">`.
- Table: a card with a header row (40 high) outside the repeat container, then
  `<div data-repeat="<List>">` holding **two or three** rows, each 48 high, each with its
  cells marked `data-field`. A status cell is a badge with a word in it.
- Each row's "Open" control is `<a href="<detail file>" data-nav="<DetailScreenId>">`.
- Lay columns out with px `left` and `width` that close the row:
  `last left + last width = card inner width − right padding`.
- `create-app` has no confirmed Gallery. It converts the sample rows as written and
  hands over a paste test for a Gallery bound to the list. Three good rows are enough
  for that; seventeen copies are not better.

## Detail

One record, read-only, with what can be done to it.

- A card with `data-source="<List>"`; inside, label/value rows 40 high with a 1px rule
  block at the top of each row. The value carries `data-field`.
- Read-only values are text, never inputs. An input means "you can edit this".
- Actions in a side panel or a footer row: `<button type="button" data-action="…">`
  for actions that stay, and a Back link
  `<a href="<list file>" data-nav="<ListScreenId>">`.

## Form

Create or edit one record.

- `<form class="card" action="<file to show next>" method="get" data-source="<List>">`.
- Fields in a grid of px columns. Two columns inside a 686-wide card with 24px padding:
  inner 636 (686 − 2 border − 48 padding), columns 306 + 24 gap + 306.
- Each field: `<label for>` 16 high, 6px gap, control 40 high, so 62 per field and 16
  between rows. Textareas have an explicit height.
- `<select>` with every real option. A date is `<input type="date">`; a yes/no is a
  checkbox. Do not disguise a constrained choice as a text box.
- Footer buttons, right-aligned: Cancel is
  `<a href="<previous file>" data-nav="<PreviousScreenId>">`; the submit button is
  `<button type="submit" data-action="submit:<List>" data-nav="<NextScreenId>">`,
  plus `run-flow:<Flow>` in the same `data-action` when submitting starts a flow.
- A form taller than the canvas is fine: compute the height, set it on `body` and in
  `sitemap.json` with `"scrolls": true`.

## Dashboard

Numbers and short lists at a glance.

- A row of stat tiles in a px grid (for four tiles in 1038: 4 × 241.5 does not close,
  so use 3 gaps of 24 and tiles of 241, 241, 241, 243 — the residue goes to the last).
- Each tile: label (caption), value (display size), optional delta with a word, never
  colour alone. The value carries `data-field` inside a container with
  `data-source`, if it comes from a list.
- A tile that opens a filtered list is an `<a href data-nav>` covering the tile.
- Charts: a placeholder box with `data-image="<what the chart shows>"`. Power Apps chart
  controls are not in the `create-app` catalog.

## Dialog

A confirmation or a short form over the current screen.

- Its own screen file, `"kind": "dialog"` in `sitemap.json`, opened by
  `<a href="<dialog file>" data-nav="<DialogScreenId>">`.
- Draw the parent screen's chrome dimmed by a scrim block (a full-canvas `div` with a
  token colour), and the dialog card centred on top: for a 480 × 240 card,
  x = (1366 − 480) / 2 = 443, y = (768 − 240) / 2 = 264.
- Every button leads somewhere: Cancel navigates back to the opener; Confirm carries its
  `data-action` and `data-nav` back. A dialog with no way out is a `no-way-back`.

## Empty state

What a list or dashboard shows before there is any data.

- Draw it as a state variant of the list screen: `request-list-empty.html`,
  `scrRequestListEmpty`, `"kind": "state"`, `"variantOf": "scrRequestList"`, linked from
  `index.html`. Same chrome, same title row; only the content differs.
- An illustration placeholder (`data-image`), one sentence on why it is empty, and the
  one action that fills it (`<a data-nav>` to the form).

## Error state

What the user sees when something fails.

- Field errors: a caption-size line under the field in the error colour, plus the field
  border in the error colour. Text says what to do, not just what is wrong.
- Page errors: a banner block at the top of the content column with a filled
  background, a word ("Error") and a sentence. A left accent is a 4px block, not a
  one-sided border.
- Show the error state as a state variant (`new-request-error.html`, `"kind": "state"`,
  `"variantOf"` the form screen) and link it from `index.html`. Its Cancel and submit
  controls work like the form's own.
