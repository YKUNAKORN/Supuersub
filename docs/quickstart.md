# Quickstart

Install `supersub` on the surface you use, run one skill, then read the section for the
skill you need. The five skills are the same everywhere; what differs is how they are
installed and where their files go.

## Table of contents

- [Install in Claude chat or Cowork](#install-in-claude-chat-or-cowork)
- [Install in Claude Code](#install-in-claude-code)
- [First run](#first-run)
- [design-md](#design-md)
- [mock-ui](#mock-ui)
- [create-app](#create-app)
- [create-list](#create-list)
- [create-flow](#create-flow)

## Install in Claude chat or Cowork

Chat means claude.ai, the desktop app and mobile. The skills' scripts run in the
code-execution sandbox, so code execution must be enabled for your account.

**From the marketplace (recommended).**

1. Customize > Plugins > **Add** > **Add marketplace**.
2. Enter `YKUNAKORN/power-app-yaml` (or the full GitHub URL).
3. Install **supersub** from that marketplace.

**From a file.**

1. In a clone: `pip install pyyaml`, then `python scripts/package_plugin.py`. It writes
   `dist/supersub.zip` and prints the file count and size (well under the 5,000-file,
   200 MB limit).
2. Customize > Plugins > **Add** > **Upload plugin**, and choose `dist/supersub.zip`.

Check: ask *"Which skills do you have from plugins?"*. Claude should name `design-md`,
`mock-ui`, `create-app`, `create-list` and `create-flow`. Type `/` and they appear as
`supersub:<name>`.

A plugin installed on your claude.ai account also reaches Claude Code on your machines
as a synced plugin.

**Where the files go in chat.** There is no project folder. Each skill creates its files
with the fixed names (`DESIGN.md`, `sitemap.json`, `LeaveRequests.xlsx`, ...) and hands
them to you as downloads. To continue with the next skill, attach them again in the
conversation.

## Install in Claude Code

```bash
/plugin marketplace add YKUNAKORN/power-app-yaml
/plugin install supersub@supersub
```

Update later with `/plugin marketplace update supersub`. Skills run as
`/supersub:design-md`, `/supersub:mock-ui`, `/supersub:create-app`,
`/supersub:create-list` and `/supersub:create-flow`, or simply describe the task.

To try a clone without installing it: `claude --plugin-dir /path/to/clone` from your
project folder. `claude plugin validate /path/to/clone` checks the manifests.

The scripts run with your Python. Install what they use once:

```bash
pip install pyyaml jsonschema openpyxl
```

`pyyaml` is required. Without `jsonschema` the linters for screens, lists and flows say
**UNPROVEN** instead of passing a file, because a check did not run. Without `openpyxl`,
`create-list` offers a `.csv` instead of an `.xlsx`.

**Where the files go in Claude Code.** In your project:

```
<project>/
├── DESIGN.md
└── supersub/
    ├── mockup/   index.html, one .html per screen, sitemap.json
    ├── app/      one .pa.yaml per screen, PASTE-ORDER.md
    ├── lists/    lists.md, <ListName>.list.json, .xlsx or .csv
    └── flows/    flow.md, <FlowName>.flow.json, <FlowName>_LegacyPackage.zip
```

## First run

Ask, in any language:

> Set up a design system for a small leave request app. It will be built in Power Apps.

`design-md` loads, asks at most two rounds of questions, writes `DESIGN.md`, lints it and
ends with the verdict and the next step (`mock-ui`). If a different skill loaded, or none
did, check the [trigger matrix](trigger-matrix.md) and report it.

## design-md

Writes a `DESIGN.md` design system.

- **Ask for**: a design system, style guide, brand, design tokens, or a check of an
  existing `DESIGN.md`. Say "for Power Apps" to get the `power-apps` target.
- **You get**: `DESIGN.md` with the verdict of `scripts/design_lint.py` (`CLEAN`, or
  usable with warnings) and the reason each warning stands.
- **Check it yourself**: `python3 skills/design-md/scripts/design_lint.py DESIGN.md`
  (add `--target power-apps`).
- **Next**: `mock-ui`.

## mock-ui

Writes a clickable HTML mockup.

- **Ask for**: a mockup, wireframe or click-through prototype; attach the `DESIGN.md`.
- **First** it shows a screen inventory and waits for your agreement.
- **You get**: one `.html` per screen, `index.html`, `sitemap.json`, the lint verdict,
  and the lists and flows the mockup implies.
- **Open it**: double-click `index.html`; it works from disk, without JavaScript.
- **Check it yourself**: `python3 skills/mock-ui/scripts/mock_lint.py supersub/mockup --design DESIGN.md`.
- **Next**: `create-app`, `create-list`, `create-flow`.

## create-app

Writes Power Apps Canvas screens (`.pa.yaml`) for **Paste code**.

- **Ask for**: "turn this into a Power Apps screen" with a mockup folder, an HTML file or
  a screenshot. To add to an app that exists, attach its export (`.msapp` or `pac canvas
  download`).
- **You get**: one `.pa.yaml` per screen, `PASTE-ORDER.md` for several screens, the
  verdict of `scripts/pa_lint.py` and an isolated snippet for each unverified item.
- **Paste**: in Studio add a **blank screen**, select it, **Paste code**, paste the whole
  file. Paste any snippets on a scratch screen first.
- **Check it yourself**: `python3 skills/create-app/scripts/pa_lint.py --app-dir supersub/app --sitemap supersub/mockup/sitemap.json`.
- **Detail**: [`create-app.md`](create-app.md); paste errors: [`troubleshooting.md`](troubleshooting.md).
- **Next**: `create-list`, `create-flow`.

## create-list

Designs SharePoint lists and builds their import files.

- **Ask for**: a SharePoint or Microsoft Lists list, which columns a list needs, or an
  import from Excel or CSV.
- **First** it shows `lists.md` and waits for your agreement.
- **You get**: per list a `.list.json`, an `.xlsx` (with a `Setup` sheet) or a `.csv` with
  `Setup.md`, the type to pick per column on the import screen, and the post-import
  checklist. Every assumption that rests on an unverified import behaviour is named.
- **Import**: Lists app or SharePoint **Create > List** > **From Excel** (pick the table
  named after the list) or **From CSV**; then apply the checklist.
- **Tell us what the import screen showed**: [`CONTRIBUTING.md`](../CONTRIBUTING.md#reporting-a-sharepoint-import-result).
- **Next**: `create-app`, `create-flow`.

## create-flow

Plans Power Automate flows and builds legacy import packages.

- **Ask for**: "automate this process", which flows you need, a notification or an
  approval, or help with a package that failed to import.
- **First** it writes `flow.md` and builds nothing until you agree.
- **You get**: per flow a `.flow.json` and `<FlowName>_LegacyPackage.zip` (verified by
  reopening), the connections to select, the post-import checklist and the unverified
  list.
- **Import**: Power Automate > **My flows** > **Import** > **Import Package (Legacy)**;
  pick a connection for each connector; save, turn the flow on, run it once. If
  **Create in Dataverse solutions** is on, the legacy import may not be offered.
- **Tell us whether it imported**: [`CONTRIBUTING.md`](../CONTRIBUTING.md#reporting-a-power-automate-import-result).
- **Next**: `create-app` (calls the flows), `create-list` (owns the lists flows read).
