# supersub

[![validate](https://github.com/YKUNAKORN/supersub/actions/workflows/validate.yml/badge.svg)](https://github.com/YKUNAKORN/supersub/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**supersub** is a Claude plugin of five skills that take a Power Platform app from a
design system to mockups, Power Apps Canvas screens, SharePoint lists and Power Automate
flows. It installs in Claude chat (claude.ai, the desktop app, mobile), in Cowork and in
Claude Code.

It is for makers and developers who build internal apps on Power Apps, SharePoint and
Power Automate and want Claude to produce files they can paste or import, not prose they
have to retype. Every skill works from a catalog of what is known to work, checks its
output with an offline linter that ends in a verdict, and labels anything it could not
confirm instead of guessing.

## Table of contents

- [The pipeline](#the-pipeline)
- [The five skills](#the-five-skills)
- [Install](#install)
- [What it cannot do](#what-it-cannot-do)
- [Repository layout](#repository-layout)
- [Contributing](#contributing)
- [Attribution](#attribution)
- [License](#license)

## The pipeline

```
design-md ──▶ mock-ui ──▶ create-app
 DESIGN.md      │  mockup/*.html      app/*.pa.yaml
                │  sitemap.json
                ├──▶ create-list   lists/*.xlsx | *.csv   (data the screens need)
                └──▶ create-flow   flows/*.zip            (actions the screens trigger)
```

Each skill also works alone. None assumes the previous one ran: hand it the file, paste
it, or describe what you have. Files have fixed names (`DESIGN.md`,
`supersub/mockup/sitemap.json`, `supersub/lists/<ListName>.list.json`, ...), so a later
skill finds what an earlier one wrote. In chat there is no project folder: the same files
come to you as downloads and go back as attachments.

Every linter ends in one of four verdicts: nothing to check, usable with items to check,
will fail, or unproven (a check could not run). Every skill ends its hand-off the same
way: what was built, what is unverified, what to test, and which skill comes next.

## The five skills

### `design-md`: a design system

Interviews you (at most two rounds of questions), offers two or three directions if you
have no strong view, and writes a `DESIGN.md`: tokens in YAML front matter and eleven
sections of prose, in the format Google published for Stitch. For a design headed for
Power Apps it keeps to what the canvas can reproduce and says what it cannot.

> Set up a design system for our new HR intranet app. It will be a Power Apps app.

### `mock-ui`: a clickable mockup

Takes a `DESIGN.md` and what the product must do, agrees a screen inventory with you,
then writes one self-contained `.html` per screen with every button and link wired, an
`index.html` screen map and a `sitemap.json`. Open `index.html` from disk and click
through; it works with JavaScript off.

> Make a clickable mockup of the leave request screens from this DESIGN.md.

### `create-app`: Power Apps Canvas screens

Converts a mockup folder, an HTML/CSS export or a screenshot into `.pa.yaml` (source
schema v3.0) for **Paste code** in Power Apps Studio, one file per screen, using only
controls a real paste test confirmed. Also fixes a file that failed to paste and adds a
screen to an existing app. Detail: [`docs/create-app.md`](docs/create-app.md).

> Turn this HTML into a Power Apps screen.

### `create-list`: SharePoint lists

Designs the lists with you in a `lists.md` (columns, types, relationships, creation
order), then builds an `.xlsx` or `.csv` per list for **New list > From Excel / From CSV**
plus the settings the import cannot set. `.xlsx` output needs `openpyxl`.

> What columns should my leave request list have? Build me the Excel file to import.

### `create-flow`: Power Automate flows

Plans the flows a system needs in a `flow.md` and builds nothing until you agree. Then it
writes one `.zip` per flow for **My flows > Import > Import Package (Legacy)**, with the
connections to pick and a post-import checklist. Connections are never embedded.

> Email the approver whenever someone submits a leave request.

A worked example through all five, with every file: [`docs/e2e-walkthrough.md`](docs/e2e-walkthrough.md).
Which skill answers which request: [`docs/trigger-matrix.md`](docs/trigger-matrix.md).

## Install

Full steps for both surfaces: [`docs/quickstart.md`](docs/quickstart.md).

**Claude chat and Cowork.** Customize > Plugins > Add, then either **Add marketplace**
with `YKUNAKORN/supersub`, or **Upload plugin** with `dist/supersub.zip` built by
`python scripts/package_plugin.py`. Type `/` and pick `supersub:<skill>`, or just describe
the task.

**Claude Code.**

```bash
/plugin marketplace add YKUNAKORN/supersub
/plugin install supersub@supersub
```

Skills run as `/supersub:design-md`, `/supersub:mock-ui`, `/supersub:create-app`,
`/supersub:create-list` and `/supersub:create-flow`. To try a clone without installing:
`claude --plugin-dir .`.

The scripts need Python 3 with `pyyaml`; `jsonschema` and `openpyxl` are optional, and a
linter that cannot run a check says **UNPROVEN** and names the install command rather
than claiming the file is clean.

Upgrading from `power-app-yaml@power-app-yaml`: the plugin was renamed in 2.0.0; see the
migration note in [`CHANGELOG.md`](CHANGELOG.md).

## What it cannot do

- **Nothing renders anything.** Colours, fonts and visual hierarchy are never checked by
  a machine. A mockup or a screen can pass every check and still look wrong.
- **The linters approximate the real tools.** `pa_lint.py` is not Power Apps Studio,
  `list_lint.py` is not the SharePoint import screen, `flow_lint.py` is not the Power
  Automate importer. Where they disagree, the real tool is right.
- **Some CSS has no Power Apps equivalent**: box shadows, blur, transitions, hover on a
  parent, one-sided borders, any font but Segoe UI. The skills say so and offer the
  nearest substitute; they never fake a property. The list is `impossible_css` in
  [`controls.yaml`](skills/create-app/references/controls.yaml).
- **Data binding is unconfirmed.** Gallery, Form, DataTable, DatePicker and the modern
  layout containers have never been paste-tested here. Screens show sample rows as static
  controls; the paste-test kit is how that changes.
- **The SharePoint import screen is mostly undocumented.** Which types its drop-down
  offers, whether it insists on a Title column and how it reads a UTF-8 CSV are all
  `unverified`; the linter warns every time a list depends on one.
- **Only one flow shape is import-tested**: a button trigger, Compose and Office 365
  Outlook *Send an email (V2)*. SharePoint, Approvals, Teams, conditions, loops and the
  Power Apps trigger are unattempted; build such a flow once by hand, export it, and
  harvest it. A package the builder generates has not been imported yet.
- **No skill calls a Power Platform API**, creates a connection, or touches your tenant.
  You paste and import; the skills produce files.
- **Multi-screen paste order is untested.** Whether Studio keeps a pasted screen's name,
  and whether a `Navigate()` to a screen that does not exist yet can be pasted, are open
  questions in [`docs/test-plan.md`](docs/test-plan.md#multi-screen-paste).

What only the owner can verify before a release: [`docs/release-test-plan.md`](docs/release-test-plan.md).

## Repository layout

```
<repo>/
├── .claude-plugin/           plugin.json and marketplace.json
├── skills/                   what ships: one folder per skill, everything it runs inside it
│   ├── design-md/            scripts/design_lint.py
│   ├── mock-ui/              scripts/tokens_to_css.py, mock_lint.py
│   ├── create-app/           scripts/pa_lint.py, app_inventory.py, harvest_controls.py
│   ├── create-list/          scripts/list_lint.py, build_list.py
│   └── create-flow/          scripts/flow_lint.py, build_flow_package.py, harvest_flow.py
├── shared/                   files several skills need; copied into each by scripts/sync_shared.py
├── scripts/                  maintainer tools, never run inside an installed skill:
│                             validate.py, skill_checks.py, sync_shared.py, run_eval.py,
│                             package_plugin.py
├── docs/                     quickstart, per-skill detail, test plans, evals, troubleshooting
├── tests/                    unittest suite, fixtures, eval cases, the e2e scenario
└── .github/                  issue and PR templates, CI
```

Checks before a pull request:

```bash
python scripts/validate.py
python -m unittest discover tests
python scripts/run_eval.py
```

## Contributing

The most valuable contribution is a real result: a Studio paste, a SharePoint import, a
Power Automate import. See [`CONTRIBUTING.md`](CONTRIBUTING.md), and please follow the
[Code of Conduct](CODE_OF_CONDUCT.md). Security issues: [`SECURITY.md`](SECURITY.md).

## Attribution

- `skills/create-app/references/schema-v3.pa.yaml` is Microsoft's Power Apps `pa.yaml`
  v3.0 schema from [`microsoft/PowerApps-Tooling`](https://github.com/microsoft/PowerApps-Tooling)
  (MIT, © Microsoft Corporation), unmodified.
- `skills/create-app/references/control-ids-candidate.yaml` mirrors the control-id list
  from the same repository.
- `design-md` describes the [DESIGN.md format](https://github.com/google-labs-code/design.md)
  published by Google (Apache-2.0); no passage of the specification is copied.

Details and license texts: [`NOTICE`](NOTICE).

## License

MIT; see [`LICENSE`](LICENSE). Third-party material is covered separately; see
[`NOTICE`](NOTICE).
