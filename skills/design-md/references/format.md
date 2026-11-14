# The DESIGN.md format, condensed

This is the skill's own summary of the format, written for the work this skill does. It
does not copy the specification. The authority is the specification,
<https://github.com/google-labs-code/design.md/blob/main/docs/spec.md> (Apache-2.0, format version `alpha`,
still changing). Read it there when this summary and a tool disagree.

What the summary was checked against (2026-11-15): the spec at repository commit
`1ed38aa` and the published CLI `@google/design.md` 0.4.0 (npm). The two already differ:
the repository's spec allows tokens in fenced `yaml` blocks in the body, the published
CLI's `spec` command describes front matter only. This skill writes front matter only,
which both accept.

## 1. Shape of the file

```
---
<YAML front matter: every token>
---

## Overview
...prose...
## Colors
...
```

- The front matter opens with a line that is exactly `---` and closes with another.
- **Tokens are normative. Prose explains how to apply them.** When they disagree, the
  token wins and the prose is wrong.
- An optional `#` title may precede the sections; it is not a section.

## 2. Top-level keys, in this order

| Key | Type | Notes |
|---|---|---|
| `version` | string | `alpha` |
| `name` | string | The design system's name. Required by this skill. |
| `description` | string | One paragraph: what the system feels like and why. |
| `colors` | map name → Color | Must include `primary`. |
| `typography` | map name → Typography | 9–15 levels is the usual range. |
| `rounded` | map level → Dimension | Corner radius scale. |
| `spacing` | map level → Dimension or number | A number is for counts or ratios. |
| `components` | map name → map property → value | Values are references or literals. |

The spec also defines `omitted` (a list of sections left out on purpose); the collection
never uses it and this skill does not need it, because it writes every section.

Each key appears once. A duplicated key is an error, at the top level or inside a group.
Any other top-level key is an error for this skill's linter (the spec tolerates custom
keys; the Google CLI warns only when one looks like a typo of a real key).

## 3. Value types

- **Color**: any CSS colour. Write `#RRGGBB` (lowercase), which every tool reads. The
  spec also accepts `#RGB`, `#RGBA`, `#RRGGBBAA`, named colours, `rgb()`, `rgba()`,
  `hsl()`, `hsla()`, `hwb()`, `lab()`, `lch()`, `oklab()`, `oklch()`, `color-mix()`.
  `design_lint.py` measures hex, `rgb()/rgba()`, `hsl()/hsla()` and named colours; the
  rest are accepted but their contrast is reported as unmeasured.
- **Dimension**: a number with `px`, `em` or `rem`. Write `0px`, not `0` (the linter
  accepts a bare zero, as CSS does, but other tools may not).
- **Typography**: `fontFamily` (string), `fontSize` (Dimension), `fontWeight` (number,
  e.g. `600`), `lineHeight` (Dimension or unitless number, e.g. `1.5`), and optionally
  `letterSpacing` (Dimension), `fontFeature`, `fontVariation` (strings). This skill always
  writes the first four.
- **Padding** in a component may be a CSS shorthand of one to four dimensions
  (`8px 16px`). The spec types it as a single Dimension; the collection uses shorthand
  throughout and the Google CLI accepts it.

## 4. References

- A reference is a whole value wrapped in braces: `"{colors.primary}"`. Quote it in YAML.
- It names a path in the YAML tree: `colors.<name>`, `typography.<name>`,
  `typography.<name>.<property>`, `rounded.<level>`, `spacing.<level>`.
- It must resolve. A chain (`a` → `b` → value) is fine; a loop is an error.
- **Outside `components`** a reference must reach a single value, not a group.
  `"{typography.body-md}"` is only valid as a component's `typography`.
- **Components cannot reference components.** Neither `{components.button.textColor}`
  nor `{component.button.textColor}` resolves in the Google CLI; components are not part
  of the token tree it resolves against. Make a variant its own component instead.

### References in prose

The Google CLI does not read the prose at all: a reference written in a paragraph is
never resolved, so any spelling lints clean there. The collection writes component
references in prose in the singular, `{component.button-primary}`, although the YAML key
is `components`. This skill writes the path that exists in the YAML tree:

```
{components.button-primary}     a component, by its YAML path
{colors.primary}                any other token
```

`design_lint.py` resolves prose references against the tokens and warns on the singular
form (`prose-ref-singular`) and on a reference that resolves to nothing (`prose-ref`).

## 5. Component properties

The spec lists eight: `backgroundColor`, `textColor` (Color), `typography` (reference to
a typography level), `rounded`, `padding`, `size`, `height`, `width` (Dimension). Any
other property is accepted with a warning. The collection also uses `description`,
`border` and `borderColor`; this skill avoids them in tokens and describes borders in the
prose with a colour token.

Variants are separate components with a suffix: `button-primary`,
`button-primary-hover`, `button-primary-active`, `button-primary-disabled`.

## 6. Sections

`##` headings, in this order. Sections may be left out, but those present keep the order;
a heading that appears twice is an error.

1. Overview *(alias: Brand & Style)*
2. Colors
3. Typography
4. Layout *(alias: Layout & Spacing)*
5. Elevation & Depth *(alias: Elevation)*
6. Shapes
7. Components
8. Do's and Don'ts
9. Responsive Behavior
10. Iteration Guide
11. Known Gaps

The first eight are the spec's order. The last three are additions the collection makes
to every current file; the spec preserves unknown sections, so they are legal. This skill
writes all eleven and keeps the three additions after the eight. Any other `##` heading
is allowed and ignored by the order check.

## 7. Lint rules

### Google CLI

`npx @google/design.md lint DESIGN.md` prints JSON findings. The authoritative list is
`npx @google/design.md spec --rules`. In 0.4.0:

| Rule | Severity | Checks |
|---|---|---|
| `broken-ref` | error | a component reference that does not resolve; unknown component properties (warning) |
| `missing-primary` | warning | colours defined, no `primary` |
| `contrast-ratio` | warning | a component's `textColor` on `backgroundColor` below 4.5:1 |
| `orphaned-tokens` | warning | a colour no component references (exempts Material-style families such as `primary`, `on-*`, `surface`) |
| `token-summary` | info | counts of each token type |
| `missing-sections` | info | no `spacing` or `rounded` |
| `missing-typography` | warning | colours defined, no typography |
| `section-order` | warning | canonical sections out of order (first violation only) |
| `unknown-key` | warning | a top-level key one or two edits from a real one |
| `token-like-ignored` | warning | an unknown top-level key that looks like tokens |
| `omitted-rules` | info | entries of `omitted` |

### `design_lint.py` (this skill, offline)

Stricter, because it checks this skill's own output. Run
`python3 scripts/design_lint.py --help` or read its docstring for every check id. Where
it differs from the Google CLI 0.4.0:

| Topic | Google CLI 0.4.0 | `design_lint.py` |
|---|---|---|
| Missing `primary`, section order, contrast below 4.5:1 | warning | error |
| Duplicate `##` heading | not detected (the spec says error) | error |
| Duplicate YAML key | warning | error |
| `version` other than `alpha`; missing `fontWeight`; `fontSize: 16` | not detected | error |
| Unknown top-level key | warning only for a near-typo | error |
| Transparent `backgroundColor` | composited as black, then measured | `contrast-unmeasured` warning |
| Orphaned colours | exempts Material-style families | flags every colour no component uses |
| References and hex values in prose | not read | resolved and compared with tokens (warnings) |
| Typography level count | not checked | warning outside 9–15 |
| `--target power-apps` | n/a | findings from the Power Apps profile |
