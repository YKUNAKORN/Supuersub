---
name: create-flow
description: >-
  Plans the Power Automate flows a system needs with the user in a flow.md (how many
  flows, what triggers each, what each does), then builds one .zip per approved flow
  for import with My flows > Import > Import Package (Legacy), with the connections to
  pick and a post-import checklist. Use when someone wants to "automate this process",
  asks which flows they need, wants a Power Automate flow, a notification or an
  approval, or an import package, brings a package that failed to import, or has
  run-flow actions in a mock-ui mockup. Does not create lists or screens: that is
  create-list and create-app.
---

# Power Automate flows: plan in flow.md, then build legacy import packages

Produce `flow.md` (the plan the user approves), then per approved flow a spec
`<FlowName>.flow.json` and `<FlowName>_LegacyPackage.zip`. Reply in the user's language;
display names and `flow.md` follow it, identifiers stay ASCII. Paths are relative to this
skill's folder: `${CLAUDE_SKILL_DIR}`, or run from that folder.

**This is the riskiest skill in the plugin.** A slightly wrong package fails on import
with an unhelpful message. Only the owner's reference flow (button trigger, Compose,
Send an email (V2)) has been import-tested. Work from the catalog, label everything
else, and never present a guess as a fact.

## The workflow (in order)

1. **Listen, then ask.** Restate the system as you understand it. Ask about triggers
   (button, Power Apps, schedule, list event), who is notified, approvals, documents,
   schedules, failure cases and volumes, in at most two rounds. Use
   `supersub/mockup/sitemap.json` when it exists (its `run-flow:<Name>` actions name the
   flows and the screen and control that call them) and `supersub/lists/*.list.json`
   (list and column internal names). Never assume either exists.
2. **Write `flow.md` and stop.** Follow
   [`references/flow-md-template.md`](references/flow-md-template.md): the system in
   brief with assumptions and open questions, the inventory table with a status per flow
   (`package`, `package with unverified steps`, `build by hand`), each flow in full, and
   why the count is that number. **Build nothing until the user agrees.**
3. **Write one spec per flow marked `package`**, from catalog entries only
   ([`references/connectors.yaml`](references/connectors.yaml); schema
   [`assets/flow.schema.json`](assets/flow.schema.json); a finished example:
   [`assets/example/SendTestEmail.flow.json`](assets/example/SendTestEmail.flow.json)).
   Write `triggers` and `actions` as in a flow definition, without GUIDs,
   `operationMetadataId`, `host.apiId`, `authentication` or connection references: the
   builder adds them. A step that needs an entry under `unattempted`, or anything the
   catalog lacks, moves the flow to `build by hand` with written steps for the
   designer. Tell the user, and say that building it once, exporting it as a package
   and running `scripts/harvest_flow.py` on it makes that step reusable.
4. **Lint, then build.**
   `python3 ${CLAUDE_SKILL_DIR}/scripts/flow_lint.py supersub/flows`
   (`scripts/flow_lint.py`), fix every error, then per flow
   `python3 ${CLAUDE_SKILL_DIR}/scripts/build_flow_package.py supersub/flows/X.flow.json`
   (`scripts/build_flow_package.py`). The builder lints again and refuses on errors.
   **Never hand over a package whose verdict is WILL FAIL.** UNPROVEN means a check could
   not run: say which (`pip install pyyaml` or `jsonschema`) before going further.
5. **Verify by reopening.** The builder reopens the zip and prints `VERIFIED` only when
   it has five entries in the reference layout, every file parses and the ids agree
   across files. Anything else is not finished.
   `python3 ${CLAUDE_SKILL_DIR}/scripts/build_flow_package.py --verify X.zip` checks any
   package on its own.
6. **Hand over** (below).
7. **Read back the result.** Ask whether the import worked and whether one run
   succeeded. When the import fails, ask for the exact message and fix only what it
   points to ([`references/import-and-fix.md`](references/import-and-fix.md)).

## Rules

- **No secrets and no tenant values in a spec**: no site addresses, list or item ids,
  e-mail addresses, connection names, keys or passwords. Write a named placeholder,
  `{{SiteAddress}}`, and declare it under `placeholders` with what it is and where to set
  it after import. If the user gives the value, pass it at build time with
  `--set SiteAddress=<value>`: it goes into the zip only, never into the spec.
- **Connections are chosen by the user at import, never embedded.**
- **One flow per package. Display names are unique within `flow.md`.**
- **Every `unverified-step` warning is said out loud.** The catalog records each
  entry's level. The generated connection reference is still `unverified`, so it is
  in every flow that uses a connector
  ([`references/package-format.md`](references/package-format.md) says how each part is
  known). Generating such a step is allowed; hiding that it is unverified is not.
- Only the owner's own import moves a catalog entry to `import-tested`. A user's report
  is passed on to the plugin's maintainer, not written into the catalog.
- Out of scope: solution-aware flows, the Dataverse import route, desktop flows,
  creating connections, calling any Power Platform API.
- Write under `supersub/flows/` when a project folder is writable; otherwise create the
  files and hand them to the user.

## Hand-off

[`references/shared/handoff.md`](references/shared/handoff.md) is the contract between
the five skills. Never assume an earlier skill ran. Hand over:

- `flow.md`, every spec and every zip, with the lint verdict and `VERIFIED`;
- **the import steps** from `import-and-fix.md`: Environment Maker role; **My flows >
  Import > Import Package (Legacy)**; Create as new or Update; a connection for each
  connector; and the stop sign when **Create in Dataverse solutions** is on;
- **the connections to select**, one per connector, as the builder printed them;
- **the post-import checklist**: set each placeholder still in the flow, save, turn the
  flow on, run it once and check the run;
- **the unverified list, verbatim**, as the builder printed it;
- for each `build by hand` flow, its steps, and the harvest offer;
- the next steps: **`create-app`** calls the flows from the screens named in the
  inventory (`run-flow:` actions); **`create-list`** owns the lists the flows read and
  write, so a new column belongs there first.
