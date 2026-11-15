#!/usr/bin/env python3
"""Grow references/connectors.yaml from legacy packages the owner exported.

    python3 scripts/harvest_flow.py SRC [SRC...] [--out FILE] [--level LEVEL]
                                    [--date YYYY-MM-DD] [--report] [--catalog PATH]

SRC is a legacy package (.zip) exported with My flows > Export > Package (.zip), or a
folder holding one unpacked. Run it on packages exported from your own environment.

Default output: a connectors.yaml fragment with every connector (API name, display name,
icon), each operation with its parameter keys and a scrubbed example, every trigger
shape with its input hints, and every built-in action type, at evidence `export`
(--level changes that, e.g. `unverified` for a package that was generated rather than
exported). Review it, then copy the entries you want into references/connectors.yaml.

--report prints a coverage diff instead: what the export adds to the catalog, what it
would raise to `export`, and what the catalog holds that the export does not use. That
last list is not evidence of anything: an export only shows what that flow happens to use.

Tenant values never reach the output. The catalog keeps keys and shapes only; in the
examples every literal value becomes a named placeholder ({{EmailMessageSubject}}), and
e-mail addresses, URLs and GUIDs inside expressions become {{EmailAddress}}, {{Url}},
{{SiteAddress}} and {{Guid}}. Connection names, action names, input titles and
descriptions are not copied at all. A connection display name that holds an address is
replaced by "<connector> connection". As a last guard the output is scanned again, and
the script refuses to print it if anything tenant-like is left.

Exit codes: 0 done | 1 nothing harvestable, or the guard found a tenant value | 2 usage
problem, or PyYAML missing. Needs PyYAML.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import zipfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("flow_lint", HERE / "flow_lint.py")
flow_lint = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(flow_lint)

META_KEYS = ("evidence", "source", "notes")
ICON_RE = re.compile(r"^https://[A-Za-z0-9.-]+\.(?:azureedge\.net|azurefd\.net|"
                     r"powerautomate\.com|microsoft\.com)/[\x21-\x7e]+$")
URL_RE = re.compile(r"https?://[^\s'\"<>]+")


# --------------------------------------------------------------------------- reading


def read_package(src: Path) -> dict[str, bytes]:
    """Entry name -> bytes, from a zip or an unpacked folder."""
    if src.is_dir():
        return {p.relative_to(src).as_posix(): p.read_bytes()
                for p in sorted(src.rglob("*")) if p.is_file()}
    with zipfile.ZipFile(src) as zf:
        return {i.filename: zf.read(i) for i in zf.infolist() if not i.filename.endswith("/")}


def _json(raw: bytes):
    return json.loads(raw.decode("utf-8-sig"))


# --------------------------------------------------------------------------- scrubbing


def pascal(key: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", key)
    name = "".join(p[:1].upper() + p[1:] for p in parts if p)
    return name if name[:1].isalpha() else f"Value{name}"


def scrub_text(text: str) -> str:
    """An expression with every tenant-looking literal replaced by a placeholder."""
    text = flow_lint.EMAIL_RE.sub("{{EmailAddress}}", text)
    text = URL_RE.sub(lambda m: "{{SiteAddress}}" if flow_lint.TENANT_URL_RE.search(m.group(0))
                      else "{{Url}}", text)
    text = flow_lint.TENANT_URL_RE.sub("{{SiteAddress}}", text)
    text = flow_lint.GUID_RE.sub("{{Guid}}", text)
    return flow_lint.SECRET_RE.sub("{{Secret}}", text)


def scrub_value(key: str, value):
    """An example value with nothing of the tenant left in it."""
    if isinstance(value, dict):
        return {k: scrub_value(f"{key}/{k}", v) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub_value(key, v) for v in value]
    if isinstance(value, str) and (value.startswith("@") or "@{" in value):
        return scrub_text(value)
    if isinstance(value, bool) or value is None:
        return value
    return f"{{{{{pascal(key)}}}}}"


def connection_display(raw: str | None, display: str) -> str:
    if not raw or flow_lint.EMAIL_RE.search(raw) or flow_lint.GUID_RE.search(raw) \
            or URL_RE.search(raw):
        return f"{display} connection"
    return raw


# --------------------------------------------------------------------------- harvesting


class Harvest:
    def __init__(self):
        self.connectors: dict[str, dict] = {}
        self.triggers: dict[str, dict] = {}
        self.actions: set[str] = set()
        self.skipped: list[str] = []
        self.packages = 0

    def connector(self, api: str) -> dict:
        return self.connectors.setdefault(api, {"operations": {}})

    def operation(self, api: str, op: str, params) -> None:
        entry = self.connector(api)["operations"].setdefault(op, {"parameters": {},
                                                                  "example": {}})
        for k, v in (params or {}).items():
            entry["parameters"].setdefault(k, None)
            entry["example"].setdefault(k, scrub_value(k, v))

    def walk_actions(self, actions: dict) -> None:
        for _, scope in flow_lint.iter_scopes(actions):
            for action in scope.values():
                if not isinstance(action, dict) or not action.get("type"):
                    continue
                atype = str(action["type"])
                self.actions.add(atype)
                host = (action.get("inputs") or {}).get("host") \
                    if isinstance(action.get("inputs"), dict) else None
                if isinstance(host, dict) and host.get("connectionName"):
                    api = str(host.get("apiId") or host["connectionName"]).rsplit("/", 1)[-1]
                    if not flow_lint.API_NAME_RE.match(api):
                        self.skipped.append(f"a step on {api!r} (a custom connector or an "
                                            "unexpected name); not catalogued")
                        continue
                    self.operation(api, str(host.get("operationId")),
                                   action["inputs"].get("parameters"))

    def walk_trigger(self, trigger: dict) -> None:
        inputs = trigger.get("inputs") if isinstance(trigger.get("inputs"), dict) else {}
        host = inputs.get("host") if isinstance(inputs.get("host"), dict) else None
        if host and host.get("connectionName"):
            api = str(host.get("apiId") or host["connectionName"]).rsplit("/", 1)[-1]
            host = dict(host, connectionName=api)
            trigger = dict(trigger, inputs=dict(inputs, host=host))
        key = flow_lint.trigger_key(trigger)
        entry = self.triggers.setdefault(key, {"type": trigger.get("type")})
        if trigger.get("kind"):
            entry["kind"] = trigger["kind"]
        if host:
            entry.setdefault("parameters", {})
            entry.setdefault("example", {})
            for k, v in (inputs.get("parameters") or {}).items():
                entry["parameters"].setdefault(k, None)
                entry["example"].setdefault(k, scrub_value(k, v))
        props = (inputs.get("schema") or {}).get("properties") \
            if isinstance(inputs.get("schema"), dict) else None
        for prop in (props or {}).values():
            if isinstance(prop, dict) and prop.get("x-ms-content-hint"):
                shape = {"type": prop.get("type")}
                if prop.get("format"):
                    shape["format"] = prop["format"]
                entry.setdefault("input_hints", {}).setdefault(str(prop["x-ms-content-hint"]),
                                                               shape)

    def read(self, label: str, files: dict[str, bytes]) -> None:
        try:
            root = _json(files["manifest.json"])
        except KeyError:
            self.skipped.append(f"{label}: no manifest.json at the root of the archive")
            return
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.skipped.append(f"{label}: manifest.json is not JSON ({exc})")
            return
        resources = root.get("resources") or {}
        for rid, res in resources.items():
            if not isinstance(res, dict) or res.get("type") != "Microsoft.PowerApps/apis":
                continue
            api = str(res.get("name") or str(res.get("id", "")).rsplit("/", 1)[-1])
            if not flow_lint.API_NAME_RE.match(api):
                self.skipped.append(f"{label}: connector {api!r} is custom or unexpected; "
                                    "not catalogued")
                continue
            entry = self.connector(api)
            details = res.get("details") or {}
            entry["display_name"] = details.get("displayName") or api
            conn = next((r for r in resources.values() if isinstance(r, dict)
                         and r.get("type") == "Microsoft.PowerApps/apis/connections"
                         and rid in (r.get("dependsOn") or [])), {})
            entry["connection_display_name"] = connection_display(
                (conn.get("details") or {}).get("displayName"), entry["display_name"])
            icon = details.get("iconUri")
            if isinstance(icon, str) and ICON_RE.match(icon):
                entry["icon_uri"] = icon
            elif icon:
                self.skipped.append(f"{label}: icon of {api} is not on a Microsoft CDN; "
                                    "left out")
        found = False
        for name, raw in files.items():
            if not re.match(r"^Microsoft\.Flow/flows/[^/]+/definition\.json$", name):
                continue
            try:
                wf = _json(raw)["properties"]["definition"]
            except (KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                self.skipped.append(f"{label}: {name} has no readable definition ({exc!r})")
                continue
            found = True
            for trigger in (wf.get("triggers") or {}).values():
                if isinstance(trigger, dict):
                    self.walk_trigger(trigger)
            self.walk_actions(wf.get("actions") or {})
        if found:
            self.packages += 1
        else:
            self.skipped.append(f"{label}: no Microsoft.Flow/flows/<id>/definition.json")


def harvest(sources) -> Harvest:
    h = Harvest()
    for src in sources:
        src = Path(src)
        try:
            h.read(src.name, read_package(src))
        except (OSError, zipfile.BadZipFile) as exc:
            h.skipped.append(f"{src.name}: not readable ({exc})")
    return h


# --------------------------------------------------------------------------- output


def to_catalog(h: Harvest, level: str, source: str) -> dict:
    """The harvest as connectors.yaml entries."""
    def meta(d: dict) -> dict:
        return {**d, "evidence": level, "source": source}

    connectors = {}
    for api in sorted(h.connectors):
        c = h.connectors[api]
        entry = {k: c[k] for k in ("display_name", "connection_display_name", "icon_uri")
                 if k in c}
        ops = {}
        for op in sorted(c["operations"]):
            o = c["operations"][op]
            ops[op] = meta({})
            ops[op]["parameters"] = {k: level for k in o["parameters"]}
            ops[op]["example"] = o["example"]
        connectors[api] = meta(entry)
        connectors[api]["operations"] = ops
    triggers = {}
    for key in sorted(h.triggers):
        t = dict(h.triggers[key])
        if "parameters" in t:
            t["parameters"] = {k: level for k in t["parameters"]}
        triggers[key] = meta(t)
    actions = {a: meta({}) for a in sorted(h.actions)}
    return {"connectors": connectors, "triggers": triggers, "actions": actions}


def shape(catalog: dict) -> dict:
    """A catalog with evidence, sources and notes stripped: what a harvest can reproduce."""
    def strip(node):
        if isinstance(node, dict):
            return {k: strip(v) for k, v in node.items() if k not in META_KEYS}
        return node

    out = {"connectors": {}, "triggers": {}, "actions": sorted(catalog.get("actions") or {})}
    for api, c in (catalog.get("connectors") or {}).items():
        c = strip(c)
        c["operations"] = {op: {"parameters": sorted(o.get("parameters") or {}),
                                "example": o.get("example") or {}}
                           for op, o in (c.get("operations") or {}).items()}
        out["connectors"][api] = c
    for key, t in (catalog.get("triggers") or {}).items():
        t = strip(t)
        if "parameters" in t:
            t["parameters"] = sorted(t["parameters"])
        out["triggers"][key] = t
    return out


def guard(text: str) -> list[str]:
    """Anything tenant-like left in the output (icons on a Microsoft CDN are allowed)."""
    hits = []
    body = "\n".join(line for line in text.splitlines() if "icon_uri:" not in line)
    for name, rx in (("e-mail address", flow_lint.EMAIL_RE), ("tenant URL",
                     flow_lint.TENANT_URL_RE), ("GUID", flow_lint.GUID_RE),
                     ("connection name", flow_lint.CONNECTION_NAME_RE)):
        for m in rx.finditer(body):
            hits.append(f"{name}: {m.group(0)[:12]}...")
    return hits


def build_report(h: Harvest, catalog: dict, level: str) -> str:
    out = ["=" * 72, "harvest_flow.py coverage report", "=" * 72,
           f"  packages    {h.packages} read",
           f"  connectors  {len(h.connectors)}   triggers {len(h.triggers)}   "
           f"action types {len(h.actions)}", ""]
    if h.skipped:
        out += ["Skipped", "-" * 72] + [f"  {s}" for s in h.skipped] + [""]
    new, raise_, same = [], [], []

    def sort(label, entry):
        if entry is None:
            new.append(label)
        elif flow_lint.level_of(entry) == "unverified" and level != "unverified":
            raise_.append(f"{label}  (unverified -> {level})")
        else:
            same.append(f"{label}  ({flow_lint.level_of(entry)})")

    cat_c = catalog.get("connectors") or {}
    for api, c in sorted(h.connectors.items()):
        sort(f"connector {api}", cat_c.get(api))
        cat_ops = (cat_c.get(api) or {}).get("operations") or {}
        for op, o in sorted(c["operations"].items()):
            sort(f"operation {api}/{op}", cat_ops.get(op))
            known = (cat_ops.get(op) or {}).get("parameters") or {}
            for k in o["parameters"]:
                sort(f"parameter {api}/{op} {k}", known.get(k))
    for key in sorted(h.triggers):
        sort(f"trigger {key}", (catalog.get("triggers") or {}).get(key))
    for a in sorted(h.actions):
        sort(f"action type {a}", (catalog.get("actions") or {}).get(a))
    for title, rows in (("New to the catalog", new),
                        (f"Would rise to {level}", raise_), ("Already catalogued", same)):
        out += [title, "-" * 72] + ([f"  {r}" for r in rows] or ["  (none)"]) + [""]
    unused = [f"connector {a}" for a in sorted(cat_c) if a not in h.connectors]
    unused += [f"trigger {t}" for t in sorted(catalog.get("triggers") or {})
               if t not in h.triggers]
    unused += [f"action type {a}" for a in sorted(catalog.get("actions") or {})
               if a not in h.actions]
    out += ["In the catalog, not used by this export (absence is not evidence)", "-" * 72]
    out += [f"  {u}" for u in unused] or ["  (none)"]
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="harvest_flow.py",
                                     description=__doc__.split("\n")[0])
    parser.add_argument("sources", nargs="+", type=Path, help="exported .zip or folder")
    parser.add_argument("--out", type=Path, help="write the fragment here, not to stdout")
    parser.add_argument("--level", default="export", choices=flow_lint.LEVELS,
                        help="evidence level for the entries (default export)")
    parser.add_argument("--date", default=date.today().isoformat(),
                        help="harvest date for the source field (default today)")
    parser.add_argument("--report", action="store_true", help="print a coverage diff")
    parser.add_argument("--catalog", type=Path, default=flow_lint.DEFAULT_CATALOG)
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover
        pass
    try:
        import yaml  # type: ignore
    except ImportError:
        print("ERROR: PyYAML is not installed. Install it with: pip install pyyaml",
              file=sys.stderr)
        return 2
    missing = [str(s) for s in args.sources if not s.exists()]
    if missing:
        print(f"ERROR: no such source: {', '.join(missing)}", file=sys.stderr)
        return 2

    h = harvest(args.sources)
    if not h.packages:
        print("Nothing harvested:\n  " + "\n  ".join(h.skipped), file=sys.stderr)
        return 1
    if args.report:
        catalog, why = flow_lint.load_catalog(args.catalog)
        if catalog is None:
            print(f"ERROR: {why}", file=sys.stderr)
            return 2
        text = build_report(h, catalog, args.level)
    else:
        source = f"owner export, harvested {args.date} by scripts/harvest_flow.py"
        frag = to_catalog(h, args.level, source)
        text = ("# connectors.yaml fragment -- GENERATED by scripts/harvest_flow.py.\n"
                "# Review it, then copy the entries into references/connectors.yaml.\n"
                + yaml.safe_dump(frag, sort_keys=False, allow_unicode=False, width=100))
    hits = guard(text)
    if hits:
        print("REFUSED: a tenant-like value is still in the output:\n  "
              + "\n  ".join(hits), file=sys.stderr)
        return 1
    if args.out and not args.report:
        args.out.write_text(text, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(text)
    for s in h.skipped:
        print(f"  NOTE: {s}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
