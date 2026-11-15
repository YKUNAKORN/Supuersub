#!/usr/bin/env python3
"""Turn a linted <FlowName>.flow.json into a legacy Power Automate import package.

    python3 scripts/build_flow_package.py SPEC.flow.json [--out DIR]
                                          [--set NAME=VALUE ...]
                                          [--seed TEXT] [--created-time ISO]
    python3 scripts/build_flow_package.py --verify PACKAGE.zip

Writes <name>_LegacyPackage.zip, for My flows > Import > Import Package (Legacy), in
exactly the layout of the reference package (references/package-format.md): five
deflated entries, no directory entries, no wrapping folder, UTF-8 JSON without a
byte-order mark, two-space indent, LF, no trailing newline, non-ASCII as \\uXXXX.

The builder generates every GUID, operationMetadataId, both manifests, both maps and
definition.json; it adds host.apiId, the authentication input and the connection
references. It never embeds a connection: the user selects one per connector at import.

It lints first (scripts/flow_lint.py) and refuses on any error. After writing, it
reopens the archive and prints VERIFIED only when the layout, every file's encoding and
JSON, and the ids across files agree. --verify runs that check alone on any package.

--set fills a {{Placeholder}} with a value at build time; the value goes into the zip
only, never into the spec. Unfilled placeholders stay as {{Name}} and are listed in the
post-import checklist. --seed makes every GUID reproducible; --created-time fixes the
manifest's createdTime and the zip timestamps (both used by the tests).

Exit codes: 0 built and VERIFIED | 1 lint errors, or verification failed | 2 usage
problem, or the catalog could not be read (PyYAML missing). Standard library plus PyYAML
for the catalog.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent

_spec = importlib.util.spec_from_file_location("flow_lint", HERE / "flow_lint.py")
flow_lint = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(flow_lint)

LOGICFLOWS_API = "/providers/Microsoft.PowerApps/apis/shared_logicflows"
WORKFLOW_SCHEMA = ("https://schema.management.azure.com/providers/Microsoft.Logic/"
                   "schemas/2016-06-01/workflowdefinition.json#")
FLOWS_DIR = "Microsoft.Flow/flows"
GUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
FILE_MODE = 0o600 << 16  # what the reference archive carries


# --------------------------------------------------------------------------- ids


class Ids:
    """Fresh GUIDs; reproducible ones when a seed is given."""

    def __init__(self, seed: str | None, name: str):
        self.seed, self.name, self.n = seed, name, 0

    def new(self) -> str:
        if self.seed is None:
            return str(uuid.uuid4())
        self.n += 1
        digest = hashlib.sha256(f"{self.seed}:{self.name}:{self.n}".encode()).digest()
        return str(uuid.UUID(bytes=digest[:16], version=4))


def dump(obj) -> bytes:
    """The reference's encoding: indent 2, ASCII with \\uXXXX, LF, no trailing newline."""
    return json.dumps(obj, indent=2, ensure_ascii=True).encode("ascii")


def created_stamp(dt: datetime) -> str:
    """2026-11-09T07:29:55.6862280Z: seven fractional digits, as in the reference."""
    dt = dt.astimezone(timezone.utc)
    return f"{dt:%Y-%m-%dT%H:%M:%S}.{dt.microsecond:06d}0Z"


# --------------------------------------------------------------------------- definition


def fill(node, values: dict):
    """Copy of node with every {{Name}} that has a value replaced by it."""
    if isinstance(node, str):
        return flow_lint.PLACEHOLDER_RE.sub(
            lambda m: values.get(m.group(1), m.group(0)), node)
    if isinstance(node, dict):
        return {k: fill(v, values) for k, v in node.items()}
    if isinstance(node, list):
        return [fill(v, values) for v in node]
    return node


def with_metadata(item: dict, ids: Ids, first: tuple[str, ...]) -> dict:
    """item with metadata.operationMetadataId, keys ordered as in the reference."""
    meta = {"operationMetadataId": ids.new()}
    meta.update({k: v for k, v in (item.get("metadata") or {}).items()
                 if k != "operationMetadataId"})
    out = {k: item[k] for k in first if k in item}
    out["metadata"] = meta
    out.update({k: v for k, v in item.items() if k not in out})
    return out


def connector_inputs(inputs: dict) -> dict:
    host = inputs.get("host") or {}
    api = host["connectionName"]
    out = {"host": {"apiId": flow_lint.API_PREFIX + api, "connectionName": api,
                    "operationId": host["operationId"]}}
    if "parameters" in inputs:
        out["parameters"] = inputs["parameters"]
    out["authentication"] = flow_lint.AUTH_INPUT
    out.update({k: v for k, v in inputs.items() if k not in out})
    return out


def build_action(action: dict, ids: Ids) -> dict:
    action = dict(action)
    if action.get("type") in flow_lint.CONNECTOR_TYPES and isinstance(action.get("inputs"),
                                                                       dict):
        action["inputs"] = connector_inputs(action["inputs"])
    if isinstance(action.get("actions"), dict):
        action["actions"] = build_actions(action["actions"], ids)
    for branch in ("else", "default"):
        if isinstance(action.get(branch), dict) and isinstance(
                action[branch].get("actions"), dict):
            action[branch] = dict(action[branch],
                                  actions=build_actions(action[branch]["actions"], ids))
    if isinstance(action.get("cases"), dict):
        action["cases"] = {
            c: (dict(b, actions=build_actions(b["actions"], ids))
                if isinstance(b, dict) and isinstance(b.get("actions"), dict) else b)
            for c, b in action["cases"].items()}
    return with_metadata(action, ids, ("runAfter",))


def build_actions(actions: dict, ids: Ids) -> dict:
    return {k: build_action(v, ids) for k, v in actions.items()}


def build_trigger(trigger: dict, ids: Ids) -> dict:
    trigger = dict(trigger)
    if isinstance(trigger.get("inputs"), dict) and isinstance(trigger["inputs"].get("host"),
                                                              dict):
        trigger["inputs"] = connector_inputs(trigger["inputs"])
    return with_metadata(trigger, ids, ())


# --------------------------------------------------------------------------- package


def build_entries(spec: dict, catalog: dict, values: dict, seed: str | None,
                  created: datetime) -> list[tuple[str, bytes]]:
    """The five (entry name, bytes) pairs of the package, in archive order."""
    ids = Ids(seed, spec["name"])
    flow_key, def_name, telemetry = ids.new(), ids.new(), ids.new()
    body = fill({"triggers": spec["triggers"], "actions": spec["actions"]}, values)

    resources: dict[str, dict] = {}
    api_ids: dict[str, str] = {}
    conn_ids: dict[str, str] = {}
    conn_refs: dict[str, dict] = {}
    connector_resources: dict[str, dict] = {}
    for api in spec["connectors"]:
        entry = catalog["connectors"][api]
        api_ids[api], conn_ids[api] = ids.new(), ids.new()
        icon = entry.get("icon_uri")
        api_details = {"displayName": entry["display_name"]}
        conn_details = {"displayName": entry.get("connection_display_name")
                        or f"{entry['display_name']} connection"}
        if icon:
            api_details["iconUri"] = conn_details["iconUri"] = icon
        connector_resources[api_ids[api]] = {
            "id": flow_lint.API_PREFIX + api, "name": api, "type": "Microsoft.PowerApps/apis",
            "suggestedCreationType": "Existing", "details": api_details,
            "configurableBy": "System", "hierarchy": "Child", "dependsOn": []}
        connector_resources[conn_ids[api]] = {
            "type": "Microsoft.PowerApps/apis/connections",
            "suggestedCreationType": "Existing", "creationType": "Existing",
            "details": conn_details, "configurableBy": "User", "hierarchy": "Child",
            "dependsOn": [api_ids[api]]}
        # A generated name in the reference's shape; it points at no real connection.
        conn_refs[api] = {"connectionName": f"{api.replace('_', '-')}-{ids.new()}",
                          "source": "Embedded", "id": flow_lint.API_PREFIX + api,
                          "tier": "NotSpecified"}

    resources[flow_key] = {
        "type": "Microsoft.Flow/flows", "suggestedCreationType": "New",
        "creationType": "Existing, New, Update",
        "details": {"displayName": spec["displayName"]},
        "configurableBy": "User", "hierarchy": "Root",
        "dependsOn": [i for api in spec["connectors"] for i in (api_ids[api], conn_ids[api])]}
    resources.update(connector_resources)

    root_manifest = {
        "schema": "1.0",
        "details": {"displayName": spec["displayName"], "description": spec["description"],
                    "createdTime": created_stamp(created), "packageTelemetryId": telemetry,
                    "creator": "N/A", "sourceEnvironment": ""},
        "resources": resources}
    flows_manifest = {"packageSchemaVersion": "1.0",
                      "flowAssets": {"assetPaths": [flow_key]}}
    definition = {
        "name": def_name,
        "id": f"/providers/Microsoft.Flow/flows/{def_name}",
        "type": "Microsoft.Flow/flows",
        "properties": {
            "apiId": LOGICFLOWS_API,
            "displayName": spec["displayName"],
            "definition": {
                "$schema": WORKFLOW_SCHEMA,
                "contentVersion": "1.0.0.0",
                "parameters": {
                    "$connections": {"defaultValue": {}, "type": "Object"},
                    "$authentication": {"defaultValue": {}, "type": "SecureObject"}},
                "triggers": {k: build_trigger(v, ids) for k, v in body["triggers"].items()},
                "actions": build_actions(body["actions"], ids)},
            "connectionReferences": conn_refs,
            "flowFailureAlertSubscribed": False}}
    folder = f"{FLOWS_DIR}/{flow_key}"
    return [("manifest.json", dump(root_manifest)),
            (f"{FLOWS_DIR}/manifest.json", dump(flows_manifest)),
            (f"{folder}/definition.json", dump(definition)),
            (f"{folder}/apisMap.json", dump(api_ids)),
            (f"{folder}/connectionsMap.json", dump(conn_ids))]


def write_zip(path: Path, entries, created: datetime) -> None:
    stamp = created.astimezone(timezone.utc).timetuple()[:6]
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries:
            info = zipfile.ZipInfo(name, date_time=stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = FILE_MODE
            zf.writestr(info, data)


# --------------------------------------------------------------------------- verify


def verify_package(path: Path) -> list[str]:
    """Every way the archive differs from the reference layout; empty means VERIFIED."""
    problems: list[str] = []
    try:
        zf = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        return [f"not a readable zip: {exc}"]
    with zf:
        infos = zf.infolist()
        names = [i.filename for i in infos]
        if len(names) != 5:
            problems.append(f"{len(names)} entries; the layout has exactly 5")
        for n in names:
            if n.endswith("/"):
                problems.append(f"directory entry {n!r}")
            if "\\" in n:
                problems.append(f"backslash in entry name {n!r}")
        if "manifest.json" not in names:
            problems.append("no manifest.json at the root of the archive (a wrapping "
                            "folder makes the import fail)")
        data: dict[str, object] = {}
        for i in infos:
            if i.filename.endswith("/"):
                continue
            if i.compress_type != zipfile.ZIP_DEFLATED:
                problems.append(f"{i.filename}: not deflated")
            raw = zf.read(i)
            if raw.startswith(b"\xef\xbb\xbf"):
                problems.append(f"{i.filename}: starts with a byte-order mark")
            if b"\r" in raw:
                problems.append(f"{i.filename}: CR line endings")
            if raw.endswith(b"\n"):
                problems.append(f"{i.filename}: trailing newline")
            try:
                data[i.filename] = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                problems.append(f"{i.filename}: not UTF-8 JSON ({exc})")
    if problems:
        return problems

    try:
        root, flows = data["manifest.json"], data[f"{FLOWS_DIR}/manifest.json"]
        assets = flows["flowAssets"]["assetPaths"]
        if flows.get("packageSchemaVersion") != "1.0" or len(assets) != 1:
            problems.append("Microsoft.Flow/flows/manifest.json: want packageSchemaVersion "
                            "1.0 and one asset path")
        key = assets[0]
        folder = f"{FLOWS_DIR}/{key}"
        expected = ["manifest.json", f"{FLOWS_DIR}/manifest.json", f"{folder}/definition.json",
                    f"{folder}/apisMap.json", f"{folder}/connectionsMap.json"]
        if names != expected:
            problems.append(f"entries are {names}; expected {expected}")
            return problems
        definition = data[f"{folder}/definition.json"]
        apis, conns = data[f"{folder}/apisMap.json"], data[f"{folder}/connectionsMap.json"]
        res = root["resources"]
        if root.get("schema") != "1.0":
            problems.append("manifest.json: schema is not 1.0")
        flow_res = res.get(key)
        if not flow_res or flow_res.get("type") != "Microsoft.Flow/flows":
            problems.append("manifest.json: no Microsoft.Flow/flows resource keyed by the "
                            "flow folder name")
            return problems
        for rid in res:
            if not GUID_RE.match(rid):
                problems.append(f"manifest.json: resource key {rid!r} is not a GUID")
        if sorted(flow_res.get("dependsOn", [])) != sorted(k for k in res if k != key):
            problems.append("manifest.json: the flow's dependsOn does not list every other "
                            "resource exactly once")
        if sorted(apis) != sorted(conns):
            problems.append("apisMap.json and connectionsMap.json name different APIs")
        for api, rid in apis.items():
            r = res.get(rid) or {}
            if r.get("type") != "Microsoft.PowerApps/apis" or r.get("name") != api \
                    or r.get("id") != flow_lint.API_PREFIX + api:
                problems.append(f"apisMap.json: {api} -> {rid} is not that API's resource")
        for api, rid in conns.items():
            r = res.get(rid) or {}
            if r.get("type") != "Microsoft.PowerApps/apis/connections" \
                    or r.get("dependsOn") != [apis.get(api)]:
                problems.append(f"connectionsMap.json: {api} -> {rid} is not a connection "
                                "resource depending on its API")
        name = definition.get("name")
        if name == key:
            problems.append("definition.json: name equals the flow folder name; the "
                            "reference uses a different GUID")
        if definition.get("id") != f"/providers/Microsoft.Flow/flows/{name}":
            problems.append("definition.json: id does not end in its own name")
        props = definition["properties"]
        if props.get("displayName") != flow_res["details"].get("displayName"):
            problems.append("definition.json and manifest.json disagree on the display name")
        refs = props.get("connectionReferences") or {}
        if sorted(refs) != sorted(apis):
            problems.append("definition.json: connectionReferences do not match apisMap.json")
        wf = props["definition"]
        if len(wf.get("triggers") or {}) != 1:
            problems.append("definition.json: not exactly one trigger")
        hosts = [s for w, s in flow_lint.iter_strings(wf) if w.endswith("/host/connectionName")]
        for api in hosts:
            if api not in refs:
                problems.append(f"definition.json: a step uses {api}, which has no "
                                "connection reference")
    except (KeyError, TypeError, IndexError, AttributeError) as exc:
        problems.append(f"a required field is missing or misshapen: {exc!r}")
    return problems


# --------------------------------------------------------------------------- cli


def post_import(spec: dict, catalog: dict, values: dict, report: dict) -> list[str]:
    lines = ["Post-import checklist",
             "  1. My flows > Import > Import Package (Legacy); upload the zip.",
             "  2. Flow resource: Create as new (or Update to replace an existing flow).",
             "  3. Select a connection for each connector:"]
    for api in spec["connectors"]:
        c = catalog["connectors"][api]
        lines.append(f"       - {c.get('connection_display_name') or c['display_name']} ({api})")
    lines.append("  4. Import, open the flow, set what is below, save, turn it on, run it once.")
    open_ph = [n for n in sorted(spec.get("placeholders") or {}) if n not in values]
    for n in open_ph:
        ph = spec["placeholders"][n]
        lines.append(f"       - {{{{{n}}}}}: {ph.get('description')} -> {ph.get('setAfterImport')}")
    unverified = report["flows"][0]["unverified"] if report["flows"] else []
    if unverified:
        lines.append("Unverified (say so to the user, verbatim):")
        lines += [f"  - {u}" for u in unverified]
    return lines


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="build_flow_package.py",
        description="Build a legacy Power Automate import package from a flow spec.")
    parser.add_argument("spec", nargs="?", type=Path, help="<FlowName>.flow.json")
    parser.add_argument("--out", type=Path, help="output folder (default: the spec's)")
    parser.add_argument("--set", action="append", default=[], metavar="NAME=VALUE",
                        help="fill a placeholder at build time (repeatable)")
    parser.add_argument("--catalog", type=Path, default=flow_lint.DEFAULT_CATALOG)
    parser.add_argument("--seed", help="make every GUID reproducible")
    parser.add_argument("--created-time", help="ISO time for createdTime and zip stamps")
    parser.add_argument("--verify", type=Path, metavar="ZIP",
                        help="only check an existing package")
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover
        pass

    if args.verify:
        problems = verify_package(args.verify)
        for p in problems:
            print(f"  [PROBLEM] {p}")
        print("VERIFIED" if not problems else f"NOT VERIFIED — {len(problems)} problem(s)")
        return 0 if not problems else 1
    if not args.spec or not args.spec.is_file():
        print(f"ERROR: no such spec: {args.spec}", file=sys.stderr)
        return 2
    try:
        values = flow_lint.parse_values(args.set)
        created = (datetime.fromisoformat(args.created_time.replace("Z", "+00:00"))
                   if args.created_time else datetime.now(timezone.utc))
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    catalog, why = flow_lint.load_catalog(args.catalog)
    if catalog is None:
        print(f"ERROR: {why}", file=sys.stderr)
        return 2
    report = flow_lint.lint_files([args.spec], args.catalog, values)
    print(report["verdict"])
    if report["errors"]:
        print("Not built. Run flow_lint.py on the spec and fix every error.")
        return 1
    for note in report["degraded"]:
        print(f"  NOTE: {note}")

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    entries = build_entries(spec, catalog, values, args.seed, created)
    out = (args.out or args.spec.parent) / f"{spec['name']}_LegacyPackage.zip"
    write_zip(out, entries, created)
    problems = verify_package(out)
    print(f"Wrote {out}")
    for p in problems:
        print(f"  [PROBLEM] {p}")
    if problems:
        print(f"NOT VERIFIED — {len(problems)} problem(s). Do not hand this package over.")
        return 1
    print("VERIFIED: 5 entries in the reference layout, every file parses, ids agree.")
    print()
    print("\n".join(post_import(spec, catalog, values, report)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
