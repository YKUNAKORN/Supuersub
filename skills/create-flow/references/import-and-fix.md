# Import, check, fix

Evidence: the import steps and the requirements are from Microsoft Learn, *Export and
import a non-solution flow*
(<https://learn.microsoft.com/en-us/power-automate/export-import-flow-non-solution>,
read 2026-11-15). Everything marked *unverified* is a hypothesis.

## Before importing (doc)

- The user needs the **Environment Maker** role in the destination environment.
- Third-party cookies must be enabled in the browser.
- If an admin has turned on **Create in Dataverse solutions** (solutions by default),
  packages with non-solution flows cannot be imported, and this skill's route is closed.
  Say so and stop. Solution import is out of scope.

## Import steps (doc)

1. Power Automate > **My flows** > **Import** > **Import Package (Legacy)**.
2. **Upload**, choose the `<FlowName>_LegacyPackage.zip`, wait until the package
   details appear.
3. First row (the flow), **Import setup**: **Create as new**, or **Update** to replace
   a flow that already exists. **Save**.
4. **Related resources**: open **Import setup** on each row, select the item (for a
   connection: the user's own connection for that connector, created first if none
   exists), **Save**. Matching one row per connector to a connection is *unverified*;
   the flow's `flow.md` entry names the connections to expect.
5. **Import** becomes active once every required row is set. Select it.

## After importing (the post-import checklist)

1. Open the flow. Each connector step should show the chosen connection.
2. Set every value `flow.md` lists under *Set after import*: each `{{Placeholder}}`
   still in a field (a site address, a list, a recipient).
3. **Save**. Fix any error the designer's flow checker shows.
4. **Turn on** the flow if it is off.
5. **Run it once** with test input, and check the run history and the result (the
   e-mail, the item).
6. Report back: imported or not (the exact message), and whether the run succeeded.
   Only that report lets the owner move a catalog entry to `import-tested`.

## Known and suspected failure causes

| Symptom | Likely cause | Evidence | What to do |
|---|---|---|---|
| Import is not offered, or is refused for non-solution flows | Create in Dataverse solutions is on | doc | Stop; this route is closed in that environment |
| No permission to import | Missing Environment Maker role | doc | Ask an admin for the role |
| Upload fails or the package details never appear | A wrapping folder in the zip, or an entry with the wrong name | community report, unverified | `build_flow_package.py --verify` the zip; rebuild it, never re-zip by hand |
| Fails on a connection or a related resource | The generated `connectionReferences` (source `Embedded`) | unverified | Record the exact message. Candidates: `source` `Invoker`, or an empty `connectionReferences` (both from PyPowerAutomate) |
| Imports, but a step shows `{{Something}}` | A placeholder not filled at build time | by design | Set the value in the designer (checklist step 2) |
| Imports, but a step is broken or asks for a field again | A parameter key or shape the catalog has below `import-tested` | unverified | Record the step and the message; harvest an export of the fixed flow |
| Third-party cookie or pop-up error | Browser blocks third-party cookies | doc | Allow them for Power Automate |

## When an import fails

Ask for the **exact** message, word for word, or a screenshot. Fix only what it points
to, rebuild, and verify again. Never change several things at once: then nobody learns
which one mattered. Record the message and the fix in the results table of the
plugin's test plan (the owner's copy), so the catalog can learn from it.
