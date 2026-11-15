# Legacy package format, field by field

What `scripts/build_flow_package.py` writes, and how sure we are of each part. The
layout is copied from the owner's reference package, kept unpacked in
[`assets/reference-package/`](../assets/reference-package/manifest.json). The builder
reproduces it exactly, and the round-trip test proves that.

Evidence tags in this file:

- **sample**: read from the owner's reference package. It looks generated rather than
  exported (`creator: "N/A"`, Unix zip attributes). The owner reported on 2026-11-15
  that it **imported and ran** in their own tenant, so this layout is known to work.
  It still shows only what *one* working package looked like. It does not show which
  of its fields the importer actually needs.
- **doc**: stated by Microsoft Learn, *Export and import a non-solution flow*
  (<https://learn.microsoft.com/en-us/power-automate/export-import-flow-non-solution>,
  read 2026-11-15).
- **corroborated**: the open-source PyPowerAutomate library builds the same thing
  (<https://ntt-security-japan.github.io/PyPowerAutomate/package/package.html>, read
  2026-11-15). That is a second implementation agreeing, not a test.
- **unverified**: nothing above settles it.

The `package` entry in `connectors.yaml` is `import-tested` (owner, 2026-11-15) because
the reference package imported. One field the builder writes differently is the
generated `connectionReferences` name (below). It is a separate entry,
`package_connection_reference`, and stays `unverified` until a package the builder made
has been imported.

## The archive

| Fact | Evidence |
|---|---|
| A non-solution flow travels as a `.zip` and is imported with **My flows > Import > Import Package (Legacy)** | doc |
| Exactly five file entries, in this order: `manifest.json`, `Microsoft.Flow/flows/manifest.json`, `Microsoft.Flow/flows/<flowKey>/definition.json`, `…/apisMap.json`, `…/connectionsMap.json` | sample, corroborated (same names) |
| `manifest.json` sits at the root, with no wrapping folder | sample, corroborated. A community report says that an extra folder level makes the import fail (unverified here). |
| No directory entries, forward slashes, deflate | sample, corroborated (deflate) |
| Each file: UTF-8, no byte-order mark, two-space indent, LF, no trailing newline, non-ASCII as `\uXXXX` | sample. Whether the importer *needs* any of this is unverified. |
| Unix attributes `0600` on each entry | sample. Almost certainly irrelevant; kept so the output matches the sample. |
| One flow per package | doc ("export one flow") |

## `manifest.json` (root)

| Field | Value written | Evidence |
|---|---|---|
| `schema` | `"1.0"` | sample, corroborated |
| `details.displayName`, `details.description` | from the spec | sample |
| `details.createdTime` | build time, `YYYY-MM-DDTHH:MM:SS.fffffffZ` | sample |
| `details.packageTelemetryId` | a fresh GUID | sample, corroborated |
| `details.creator` | `"N/A"` | sample, corroborated |
| `details.sourceEnvironment` | `""` | sample, corroborated |
| `resources` | a map keyed by GUID: the flow, then per connector its API and its connection | sample, corroborated |

**Flow resource** (key = the flow folder name `<flowKey>`): `type`
`Microsoft.Flow/flows`, `suggestedCreationType` `New`, `creationType`
`Existing, New, Update`, `details.displayName`, `configurableBy` `User`, `hierarchy`
`Root`, `dependsOn` listing every API and connection resource id (per connector: the
API, then the connection). Evidence: sample, corroborated. The order of `dependsOn`
with two or more connectors is unverified. The **Create as new / Update** choice at
import is doc.

**API resource**, one per connector: `id` `/providers/Microsoft.PowerApps/apis/<api>`,
`name` `<api>`, `type` `Microsoft.PowerApps/apis`, `suggestedCreationType` `Existing`,
`details` (`displayName`, `iconUri`), `configurableBy` `System`, `hierarchy` `Child`,
`dependsOn` `[]`. Evidence: sample, corroborated. `displayName` and `iconUri` come from
the catalog. Whether `iconUri` is required, and its value for any connector except
`shared_office365`, are unverified. The builder leaves `iconUri` out when the catalog
has none.

**Connection resource**, one per connector: `type`
`Microsoft.PowerApps/apis/connections`, `suggestedCreationType` and `creationType`
`Existing`, `details` (`displayName`, `iconUri`), `configurableBy` `User`, `hierarchy`
`Child`, `dependsOn` `[<API resource id>]`. Evidence: sample, corroborated. Microsoft
describes a per-row **Import setup** under *Related Resources*, where the user picks the
item (doc); that this row is where the user selects a connection is unverified.

Which manifest fields are optional is unverified. The builder writes all of them.

## `Microsoft.Flow/flows/manifest.json`

`packageSchemaVersion` `"1.0"`, `flowAssets.assetPaths` `[<flowKey>]`. Evidence: sample,
corroborated.

## `apisMap.json` and `connectionsMap.json`

`{"<api>": "<API resource id>"}` and `{"<api>": "<connection resource id>"}`. Evidence:
sample, corroborated.

## `definition.json`

| Field | Value written | Evidence |
|---|---|---|
| `name` | a fresh GUID, **different** from `<flowKey>` | sample, corroborated |
| `id` | `/providers/Microsoft.Flow/flows/<name>` | sample |
| `type` | `Microsoft.Flow/flows` | sample |
| `properties.apiId` | `/providers/Microsoft.PowerApps/apis/shared_logicflows` | sample, corroborated |
| `properties.displayName` | from the spec | sample |
| `properties.definition` | the workflow definition: `$schema` (2016-06-01), `contentVersion` `1.0.0.0`, parameters `$connections` (Object) and `$authentication` (SecureObject), then the spec's `triggers` and `actions` | sample |
| `metadata.operationMetadataId` | a fresh GUID on every trigger and action | sample. Whether it is required is unverified. |
| connector steps | `inputs.host` = `apiId`, `connectionName` (the API name), `operationId`; then `parameters`; then `authentication` `@parameters('$authentication')` | sample |
| `properties.connectionReferences` | per connector: `connectionName` `shared-<name>-<fresh GUID>`, `source` `Embedded`, `id` the API path, `tier` `NotSpecified` | sample (the imported reference held a real connection's name here). **Unverified** (`package_connection_reference`): the generated name points at no real connection, and the assumption is that the connection chosen at import replaces it. PyPowerAutomate writes `source` `Invoker`, or leaves the map empty. If an import fails on connections, try these first. |
| `properties.flowFailureAlertSubscribed` | `false` | sample, corroborated |

PyPowerAutomate also writes `isManaged: false`; the sample does not. Following the
sample, the builder leaves it out.

## What the builder never writes

No connection id from a real environment, no environment id, no tenant or user id, no
site address or list id unless the user supplied it with `--set` at build time (that
value then lives in the zip only).
