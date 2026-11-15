# Interview: what to ask and what each answer decides

Ask only for what is missing. Read everything the user already gave (brief, logo,
screenshots, an existing `DESIGN.md`, a brand guide) and fill in what it answers before
asking anything. Then ask the rest in **at most two rounds**, grouped, in the user's
language. When the user says "you decide", decide, and say which defaults you took.

## Round 1: the essentials

| # | Ask | Decides | Default when unanswered |
|---|---|---|---|
| 1 | Is this headed for Power Apps, or for the web? | target (`web` / `power-apps`) | `web` |
| 2 | What is the product, and who uses it for what? | Overview; density; type scale | (must ask) |
| 3 | Brand assets: logo colours, brand fonts, an existing style guide? | `colors.primary` and accents; `fontFamily` | derive from directions (step 3) |
| 4 | Two or three sites or apps you like, and what you like about each? | qualities: density, contrast, radius, restraint | none |
| 5 | Light, dark, or both? | surface and text colours; a second set of `-dark` tokens | light |

## Round 2: only if still unclear

| # | Ask | Decides | Default |
|---|---|---|---|
| 6 | Where is it used most: phone, tablet, laptop, large monitor? | Responsive Behavior; base font size; touch targets | laptop |
| 7 | How much on one screen: calm and spacious, or dense? | spacing base unit; body size; table row height | balanced: 8px base, 16px body |
| 8 | Accessibility needs beyond WCAG AA (low vision, colour-blind users, public sector)? | contrast target; never colour alone for status | AA 4.5:1 for text |
| 9 | Tone: formal, friendly, playful, technical? | radius scale; weight ladder; accent saturation | neutral-professional |
| 10 | Languages and scripts the UI must show (Thai, Japanese, Arabic)? | font stack with script coverage; line height | Latin plus the user's language |
| 11 | Anything to avoid (a competitor's colour, a style the team dislikes)? | Don'ts | none |

## Turning answers into tokens

- **Primary**: the brand colour if there is one. If it fails 4.5:1 with white or with the
  text colour on it, keep it for large accents and make `primary` a darker step of the
  same hue for buttons and links. Say so in Colors.
- **Neutrals**: pick a cast (cool, warm, true grey) that suits the primary. Five to seven
  steps cover surfaces, borders and text.
- **Semantic**: `success`, `warning`, `error`, `info`, each with an `on-` text colour that
  passes 4.5:1 on it. Status must also be shown by text or icon, never colour alone.
- **Typography**: 9–15 levels. From body size, step up with a ratio of 1.2 (dense) to
  1.333 (editorial). Line height 1.4–1.6 for body, 1.1–1.25 for display. Tighten
  letter spacing only at display sizes.
- **Radius**: `none`, `sm`, `md`, `lg`, `full`. Small radii (2–4px) read technical and
  formal, 8–12px friendly, `full` pills read consumer and soft.
- **Spacing**: a base unit (4px or 8px) and a scale of multiples. State the base unit.

## Fonts: preference and fallback

Write a font the user names as a preference with an open fallback stack, e.g.
`"Brand Sans, Inter, system-ui, sans-serif"`. Never state that a proprietary typeface is
available or licensed. In `### Note on Font Substitutes`, name the open alternative.

Under `power-apps`, put `Segoe UI` first: the profile marks every other font as
unverified on the canvas. If the user wants a brand face anyway, keep it second in the
stack and record it in Known Gaps.

## When the user has no strong view: directions

Offer two or three directions that differ in a way the user can feel. For each:

- a **name** (two or three words, invented, not a company or product),
- **one sentence** on the feeling and who it suits,
- a **palette**: `primary`, one surface, one text colour, one accent, as hex,
- a **type pairing**: display face and body face, each with its open fallback.

Example shape (not content to reuse):

> **Quiet Ledger**: calm, high-contrast neutrals for people who read numbers all day.
> Palette #1f4fd1 / #f7f8fa / #1b1d22 / #0f7b5f. Type: Inter for everything, IBM Plex
> Mono for figures.

Let the user pick one or mix ("the palette of the first with the type of the second").

## Admired sites: qualities, not copies

Translate each admired site into qualities and write only the qualities down:

| They say | Write down |
|---|---|
| "I like how X looks" | Ask what exactly: whitespace? one accent colour? big type? |
| "Clean like X" | low density, a single accent, generous section spacing |
| "Professional like X" | restrained radius, neutral palette, strong type hierarchy |

Never reuse another company's name, logo, wordmark, slogan or signature colour
combination, and never name the admired site in the `DESIGN.md`.

## Updating an existing DESIGN.md

Read it first. Keep every token name that already exists, even when its value changes:
mockups and screens built on it refer to the names. Add new tokens beside the old ones;
retire a token only when the user agrees, and list it in Iteration Guide.
