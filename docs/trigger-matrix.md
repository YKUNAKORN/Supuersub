# Trigger matrix

Which skill should load for a given request. A skill loads when its frontmatter
`description` matches what the user asked, so five descriptions that overlap would make
two skills compete for one message, and a description that never says what it is *not*
for invites the wrong one. This page is the check: realistic messages, in English and
Thai, each with the one skill that owns it, and the neighbour most likely to fire by
mistake.

**How the owner was decided.** By reading the five descriptions side by side, not by
measuring which skill Claude actually loaded. Nothing here was run against a model. The
release test plan has the measured version: ask in chat and see which skill loads
(`docs/release-test-plan.md`, item `T1`). If a row turns out wrong, fix the
description, not this table.

Each description now ends with what the skill is not for, naming the skill that is:

| Skill | Says it is not for |
|---|---|
| `design-md` | building pages or screens (`mock-ui`) |
| `mock-ui` | writing the design system (`design-md`), converting HTML into Power Apps (`create-app`) |
| `create-app` | drawing a mockup (`mock-ui`), lists or flows |
| `create-list` | building flows (`create-flow`) or screens (`create-app`) |
| `create-flow` | creating lists or screens (`create-list`, `create-app`) |

`scripts/validate.py` checks that this stays true and that every owner below is one of
the five skills or `none`.

## The matrix

| # | Message | Owner | Near miss | Why the owner, not the near miss |
|---|---|---|---|---|
| 1 | Turn this HTML into a Power Apps screen. | `create-app` | `mock-ui` | The HTML exists already. `mock-ui` writes HTML and says it does not convert it into Power Apps. |
| 2 | What columns should my list have for tracking leave requests? | `create-list` | `mock-ui` | "which columns" a list needs is a `create-list` trigger. `mock-ui` only names lists a mockup implies. |
| 3 | We're starting a new intranet app. Can you set up a design system first? | `design-md` | `mock-ui` | "design system" and "about to start designing" are `design-md` triggers. |
| 4 | Make me a clickable prototype of the three screens before we build anything. | `mock-ui` | `create-app` | "click-through prototype" is `mock-ui`. There is no mockup yet for `create-app` to convert. |
| 5 | Convert this screenshot to pa.yaml. | `create-app` | none | Named trigger. |
| 6 | Paste code failed with PA2108 on `Fill`. What's wrong with my file? | `create-app` | none | "fix a .pa.yaml that failed to paste (PA1001 / PA2108)". |
| 7 | Which Power Automate flows do I need for an approval process? | `create-flow` | `create-list` | "asks which flows they need". The lists an approval reads are a later step for `create-list`. |
| 8 | Email the manager when someone submits a leave request. | `create-flow` | `create-list` | "a notification or an approval". Added in phase 07: the description used to need the word "flow". |
| 9 | Import this Excel sheet as a SharePoint list. | `create-list` | none | "import from Excel or CSV". |
| 10 | My flow package failed to import with "Something went wrong". | `create-flow` | none | "brings a package that failed to import". Added in phase 07. |
| 11 | Check this DESIGN.md for problems. | `design-md` | `mock-ui` | "wants an existing DESIGN.md updated or checked". `mock-ui` reads a DESIGN.md but does not judge it. |
| 12 | Make HTML pages from this DESIGN.md. | `mock-ui` | `design-md` | Named trigger. `design-md` says it is not for building pages or screens. |
| 13 | Add a settings screen to my existing app. Here's the .msapp. | `create-app` | `mock-ui` | "add a screen to an existing app". |
| 14 | ช่วยออกแบบโทนสีและฟอนต์สำหรับแอป Power Apps ของฝ่ายบุคคลหน่อย (design the colours and fonts for an HR Power Apps app) | `design-md` | `create-app` | A visual language, not a screen. `design-md`: "also for a design headed for Power Apps". |
| 15 | ทำ mockup หน้าจอระบบยืมอุปกรณ์ให้หน่อย (make a mockup of the equipment-loan screens) | `mock-ui` | `design-md` | "mockup". |
| 16 | แปลงไฟล์ HTML นี้เป็นหน้าจอ Power Apps (convert this HTML file into a Power Apps screen) | `create-app` | `mock-ui` | Same as row 1. |
| 17 | list SharePoint สำหรับเก็บคำขอลาควรมีคอลัมน์อะไรบ้าง (which columns should a SharePoint list for leave requests have) | `create-list` | `mock-ui` | Same as row 2. |
| 18 | อยากให้ระบบส่งอีเมลแจ้งหัวหน้าอัตโนมัติเมื่อมีคำขอลาใหม่ (automatically email the manager when a new leave request arrives) | `create-flow` | `create-list` | Same as row 8. |
| 19 | นำเข้าไฟล์ CSV เป็น list ใน SharePoint ยังไง (how do I import a CSV as a SharePoint list) | `create-list` | none | Same as row 9. |
| 20 | flow ที่ import เข้าไปขึ้น error ช่วยดูหน่อย (the flow I imported shows an error, please look) | `create-flow` | none | Same as row 10. |
| 21 | Build me a leave request app in Power Apps. | `mock-ui` | `design-md`, `create-app` | No artifact exists yet, and "wants screens planned before building a Power Apps app" is `mock-ui`. Its step 1 offers `design-md` when there is no DESIGN.md. There is no router skill (decision D6), so this row has the weakest owner in the table. |
| 22 | Write a Power Fx formula that filters a gallery to the current user. | `none` | `create-app` | A formula question, not a screen. `create-app` does not claim formulas, and its data-binding reference is all unverified. Claude answers without a skill. |
| 23 | Fix the CSS on my React website. | `none` | `mock-ui` | `mock-ui` makes mockups from a DESIGN.md; it does not edit a live site. |

## Description changes made in phase 07

- `create-app`: ends with "Not for drawing a mockup (mock-ui), lists or flows." To fit
  650 characters, "(sitemap.json + screen HTML files)" after "a mock-ui folder" was
  cut. No trigger phrase was dropped.
- `create-flow`: adds "a notification or an approval" and "brings a package that failed
  to import" (rows 8, 10, 18, 20).
- `design-md`, `mock-ui`, `create-list`: unchanged; each already said what it is not for.
