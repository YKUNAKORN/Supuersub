# `flow.md`: the structure

`flow.md` is what the user reads and approves before anything is built, so write it
for them, in their language. Identifiers (flow `name`, action keys, list and column
names) stay ASCII. Copy the skeleton below and fill in every part. Leave nothing out:
when a part does not apply, say so in one line.

Status values, used in the inventory and in each flow's heading:

- `package`: every step is in the catalog. A zip will be built.
- `package with unverified steps`: a zip will be built; the steps listed under
  *Unverified* rest on catalog entries below `import-tested`. Today the generated
  connection reference is one of them in every flow that uses a connector.
- `build by hand`: at least one step is not in the catalog (it is unattempted). No zip;
  the designer builds the flow from the numbered steps. Exporting that flow afterwards
  and running `scripts/harvest_flow.py` on it makes those steps reusable.

````markdown
# Flows: <system name>

Status: draft for approval · <date> · built from: <sitemap.json / lists / description>

## The system in brief

<Three to six sentences: what happens, who does what, and where a flow takes over.>

**Assumptions** (correct any that are wrong):

- <assumption>

**Open questions**:

- <question, or "none">

## Inventory

| # | Flow (display name) | Name | Trigger | What it does | Connectors | Lists read / written | Called by | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | <display name> | `<PascalName>` | <button / Power Apps / schedule / list event> | <one line> | Office 365 Outlook | reads `Loans` | `scrNewLoan` Submit (`run-flow:NotifyApprover`) | package with unverified steps |

**<n> flows, and why this number**: <why each is separate (different trigger, owner,
schedule or failure handling) and why none is merged or split further>.

## 1. <display name> (`<PascalName>`): <status>

- **Trigger and inputs**: <trigger>; inputs `<name>` (<type>): <meaning>.
- **Steps**:
  1. <step> (<connector / action type>)
  2. <step>
- **Outputs**: <what the caller or the user gets back>.
- **When it fails**: <what happens on a failed step; who finds out>.
- **Connections needed at import**: <connector connection, one per connector>.
- **Set after import**: <each {{Placeholder}} and where to set it; "nothing" if none>.
- **Unverified**: <the linter's unverified items for this flow, or "none">.
- **Build by hand** (only for that status): <numbered steps in the designer's own words,
  naming the connector, the action and every field to fill in>.
````
