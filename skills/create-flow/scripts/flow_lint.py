#!/usr/bin/env python3
"""Offline checker for create-flow specs (<FlowName>.flow.json), ending in a verdict.

    python3 scripts/flow_lint.py SPEC.flow.json [MORE.flow.json ...]
                                 [--set NAME=VALUE ...] [--catalog PATH]
                                 [--json] [--strict] [--quiet]

Pass every flow of one flow.md together: display names must be unique among them. A
folder argument means every *.flow.json in it. The catalog is references/connectors.yaml
inside this skill. Each finding has a stable check id; tests assert on ids, never on
wording.

ERRORS (the spec breaks the rules, or the package would rest on nothing; fix first)
  spec-invalid          not JSON, or breaks assets/flow.schema.json (one trigger, every
                        action has type and runAfter, statuses Succeeded / Failed /
                        Skipped / TimedOut)
  name-duplicate        two specs with the same name or display name (ignoring case)
  action-key-invalid    an action key that is not 1-80 ASCII letters, digits, _ - ( ) .
  action-key-duplicate  two actions with the same key anywhere in the flow
  run-after-unknown     runAfter names an action that is not at the same level, or itself
  run-after-cycle       actions at one level that wait for each other
  connector-undeclared  a connector step whose connector is not in the spec's connectors
  host-invalid          a connector step without host.connectionName and operationId, or
                        whose host.apiId does not match its connectionName
  catalog-missing       a connector, operation, parameter key, trigger shape, trigger
                        input hint or action type the catalog does not hold (it is
                        unattempted: build that step by hand, or harvest an export)
  connection-embedded   connectionReferences, $connections or a real-looking connection
                        name in the spec; connections are chosen at import
  expression-unbalanced an @{ without its }, or unbalanced parentheses in an expression
  expression-reference  outputs('X'), body('X'), actions('X'), result('X') or items('X')
                        naming an action that does not exist
  placeholder-undeclared a {{Name}} that placeholders does not declare
  sensitive-value       an e-mail address (outside example.com/.org/.net), a tenant URL
                        (SharePoint, onmicrosoft.com, Dynamics, a sign-in URL) or
                        something that looks like a secret

WARNINGS (review; fix, or say why it stands)
  unverified-step       the spec uses a catalog item (or the package layout itself) whose
                        evidence is below import-tested; the message names it
  placeholder-unresolved a declared placeholder with no value; it stays as {{Name}} in the
                        package and must be set after import
  placeholder-unused    a declared placeholder that nothing uses
  connector-unused      a declared connector that no step uses
  guid-literal          a GUID written into the spec (a list or item id belongs in a
                        placeholder)

Exit codes: 0 no errors | 1 any error | 2 warnings (or unproven) with --strict, or a
usage problem. Needs PyYAML for the catalog; jsonschema is optional. Without either the
verdict is UNPROVEN and says what to install.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent  # this skill's own folder
SCHEMA_PATH = SKILL_DIR / "assets" / "flow.schema.json"
DEFAULT_CATALOG = SKILL_DIR / "references" / "connectors.yaml"

ERROR, WARNING = "error", "warning"
LEVELS = ("import-tested", "export", "doc", "unverified")
REQUIRED_KEYS = ("version", "name", "displayName", "description", "connectors",
                 "triggers", "actions", "placeholders")
STATUSES = ("Succeeded", "Failed", "Skipped", "TimedOut")
CONNECTOR_TYPES = ("OpenApiConnection", "OpenApiConnectionWebhook",
                   "OpenApiConnectionNotification")
API_PREFIX = "/providers/Microsoft.PowerApps/apis/"
AUTH_INPUT = "@parameters('$authentication')"

ACTION_KEY_RE = re.compile(r"^[A-Za-z0-9_\-().]{1,80}$")
API_NAME_RE = re.compile(r"^shared_[a-z0-9]+$")
PLACEHOLDER_RE = re.compile(r"\{\{([A-Za-z][A-Za-z0-9]*)\}\}")
REF_RE = re.compile(r"\b(outputs|body|actions|result|items)\(\s*'([^']*)'\s*\)")
GUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                     r"[0-9a-fA-F]{12}\b")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
SAFE_EMAIL_DOMAIN_RE = re.compile(r"(?:^|\.)example\.(?:com|org|net)$|\.(?:example|test|invalid)$",
                                  re.I)
TENANT_URL_RE = re.compile(
    r"(?:https?://)?[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\."
    r"(?:sharepoint\.com|sharepoint\.us|sharepoint-mil\.us|onmicrosoft\.com|"
    r"dynamics\.com|crm\d*\.dynamics\.com)\b"
    r"|login\.microsoftonline\.(?:com|us)/[^\s'\"]+", re.I)
SECRET_RE = re.compile(
    r"(?i)\b(?:password|passwd|pwd|client_secret|secret|api[_-]?key|access[_-]?token|"
    r"sig|sv)=[^&\s'\"]+"
    r"|\bBearer\s+[A-Za-z0-9\-._~+/]{20,}=*"
    r"|(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9+/])")
CONNECTION_NAME_RE = re.compile(r"\bshared-[a-z0-9]+-[0-9a-f]{8}-[0-9a-f]{4}-", re.I)


# --------------------------------------------------------------------------- catalog


def load_catalog(path: Path = DEFAULT_CATALOG) -> tuple[dict | None, str]:
    """(catalog, why-not). catalog is None when PyYAML is missing or the file is bad."""
    try:
        import yaml  # type: ignore
    except ImportError:
        return None, ("PyYAML is not installed, so the catalog could not be read and no "
                      "catalog check ran. Install it with: pip install pyyaml")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return None, f"the catalog {path} could not be read: {exc}"
    if not isinstance(data, dict):
        return None, f"the catalog {path} is not a mapping"
    for key in ("connectors", "triggers", "actions"):
        if not isinstance(data.get(key), dict):
            data[key] = {}
    return data, ""


def level_of(entry) -> str:
    """The evidence level of a catalog entry (a mapping with evidence, or a bare level)."""
    if isinstance(entry, dict):
        entry = entry.get("evidence")
    return entry if entry in LEVELS else "unverified"


def trigger_key(trigger: dict) -> str:
    """How the catalog names a trigger shape: type/kind, or type/api/operation."""
    ttype = str(trigger.get("type", ""))
    host = (trigger.get("inputs") or {}).get("host") if isinstance(trigger.get("inputs"),
                                                                   dict) else None
    if isinstance(host, dict) and host.get("connectionName"):
        return f"{ttype}/{host.get('connectionName')}/{host.get('operationId')}"
    return f"{ttype}/{trigger['kind']}" if trigger.get("kind") else ttype


# --------------------------------------------------------------------------- walking


def iter_scopes(actions: dict, where: str = "actions"):
    """(where, actions mapping) for the top level and every nested action container."""
    if not isinstance(actions, dict):
        return
    yield where, actions
    for key, action in actions.items():
        if not isinstance(action, dict):
            continue
        base = f"{where}/{key}"
        if isinstance(action.get("actions"), dict):
            yield from iter_scopes(action["actions"], f"{base}/actions")
        if isinstance(action.get("else"), dict):
            yield from iter_scopes(action["else"].get("actions") or {},
                                   f"{base}/else/actions")
        if isinstance(action.get("default"), dict):
            yield from iter_scopes(action["default"].get("actions") or {},
                                   f"{base}/default/actions")
        if isinstance(action.get("cases"), dict):
            for case, body in action["cases"].items():
                if isinstance(body, dict):
                    yield from iter_scopes(body.get("actions") or {},
                                           f"{base}/cases/{case}/actions")


def iter_strings(node, where: str = ""):
    """(where, string) for every string value below node."""
    if isinstance(node, str):
        yield where, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from iter_strings(v, f"{where}/{k}" if where else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from iter_strings(v, f"{where}/{i}")


def iter_keys(node, where: str = ""):
    if isinstance(node, dict):
        for k, v in node.items():
            here = f"{where}/{k}" if where else str(k)
            yield here, k
            yield from iter_keys(v, here)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from iter_keys(v, f"{where}/{i}")


def expression_problem(text: str) -> str:
    """Why an expression in text is unbalanced, or ''."""
    def scan(s: str, i: int, closer: str) -> int:
        """Index just past the matching closer, or -1."""
        depth, quoted = 0, False
        while i < len(s):
            c = s[i]
            if quoted:
                if c == "'":
                    if i + 1 < len(s) and s[i + 1] == "'":
                        i += 1
                    else:
                        quoted = False
            elif c == "'":
                quoted = True
            elif c in "({[":
                depth += 1
            elif c in ")}]":
                if depth == 0:
                    return i + 1 if c == closer else -1
                depth -= 1
            i += 1
        return -1

    if text.startswith("@") and not text.startswith(("@@", "@{")):
        body = text[1:] + "\0"
        depth, quoted = 0, False
        for c in body[:-1]:
            if quoted:
                quoted = c != "'"
            elif c == "'":
                quoted = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth < 0:
                    return "a ')' with no '(' before it"
        if quoted:
            return "an unterminated 'string'"
        if depth:
            return f"{depth} '(' not closed"
        return ""
    i = 0
    while True:
        i = text.find("@{", i)
        if i < 0:
            return ""
        if i > 0 and text[i - 1] == "@":
            i += 2
            continue
        end = scan(text, i + 2, "}")
        if end < 0:
            return f"the '@{{' at character {i} has no matching '}}'"
        i = end


# --------------------------------------------------------------------------- findings


class Finding:
    __slots__ = ("check", "severity", "message", "file", "where", "detail")

    def __init__(self, check, severity, message, file=None, where=None, detail=None):
        self.check, self.severity, self.message = check, severity, message
        self.file, self.where, self.detail = file, where, detail

    def as_dict(self):
        return {"check": self.check, "severity": self.severity, "message": self.message,
                "file": self.file, "where": self.where, "detail": self.detail}


# Keywords that exist only in JSON Schema 2020-12. The bundled schema uses none of
# them, so Draft 7 validates it the same way; this list guards a future schema edit.
_DRAFT_2020_ONLY = {"prefixItems", "unevaluatedProperties", "unevaluatedItems",
                    "dependentRequired", "dependentSchemas", "$dynamicRef",
                    "$dynamicAnchor", "minContains", "maxContains"}


def _keys(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from _keys(v)
    elif isinstance(node, list):
        for v in node:
            yield from _keys(v)


def make_validator(jsonschema, schema):
    """Pick the newest validator this jsonschema offers: 2020-12, else Draft 7.

    Returns (validator or None, note or None). A note means the schema layer is reduced
    (the run is then UNPROVEN); None for the validator means no usable class at all.
    """
    cls = getattr(jsonschema, "Draft202012Validator", None)
    if cls is not None:
        return cls(schema), None
    cls = getattr(jsonschema, "Draft7Validator", None)
    if cls is None:
        return None, ("this jsonschema is too old to validate the schema (needs 3.0 or "
                      "newer), so the schema layer ran a reduced check. Install it with: "
                      "pip install -U jsonschema")
    used = sorted(set(_keys(schema)) & _DRAFT_2020_ONLY)
    if used:
        return cls(schema), ("this jsonschema predates Draft 2020-12 and the schema uses "
                             f"{used}; those rules were not checked. Install it with: "
                             "pip install -U jsonschema")
    return cls(schema), None


class Linter:
    def __init__(self, catalog_path: Path = DEFAULT_CATALOG, values: dict | None = None):
        self.values = dict(values or {})
        self.findings: list[Finding] = []
        self.degraded: list[str] = []
        self.catalog, why = load_catalog(catalog_path)
        if self.catalog is None:
            self.degraded.append(why)
        self.validator = None
        try:
            import jsonschema  # type: ignore
            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            self.validator, note = make_validator(jsonschema, schema)
            if note:
                self.degraded.append(note[0].upper() + note[1:])
        except ImportError:
            self.degraded.append("jsonschema is not installed, so the schema layer ran a "
                                 "reduced check. Install it with: pip install jsonschema")
        self.unverified: dict[str, list[str]] = {}

    def add(self, check, severity, message, file=None, where=None, detail=None):
        self.findings.append(Finding(check, severity, message, file, where, detail))

    # -- structure ---------------------------------------------------------------

    def structurally_ok(self, spec, file) -> bool:
        if not isinstance(spec, dict):
            self.add("spec-invalid", ERROR, "the spec is not a JSON object", file)
            return False
        if self.validator is not None:
            for err in sorted(self.validator.iter_errors(spec), key=lambda e: list(e.path)):
                path = "/".join(str(p) for p in err.absolute_path) or "(root)"
                self.add("spec-invalid", ERROR, f"schema: {err.message}", file, path)
        else:
            missing = [k for k in REQUIRED_KEYS if k not in spec]
            if missing:
                self.add("spec-invalid", ERROR, f"missing keys: {missing}", file)
            trig = spec.get("triggers")
            if isinstance(trig, dict) and len(trig) != 1:
                self.add("spec-invalid", ERROR, f"{len(trig)} triggers; a flow has one",
                         file, "triggers")
            for where, scope in iter_scopes(spec.get("actions") or {}):
                for key, action in scope.items():
                    if not isinstance(action, dict) or "type" not in action \
                            or not isinstance(action.get("runAfter"), dict):
                        self.add("spec-invalid", ERROR, "an action needs type and runAfter",
                                 file, f"{where}/{key}")
                        continue
                    for dep, sts in action["runAfter"].items():
                        if not isinstance(sts, list) or not sts \
                                or any(s not in STATUSES for s in sts):
                            self.add("spec-invalid", ERROR,
                                     f"runAfter {dep!r} needs a list of {list(STATUSES)}",
                                     file, f"{where}/{key}/runAfter")
        return (isinstance(spec.get("name"), str)
                and isinstance(spec.get("triggers"), dict)
                and all(isinstance(t, dict) for t in spec["triggers"].values())
                and isinstance(spec.get("actions"), dict)
                and isinstance(spec.get("connectors", []), list)
                and isinstance(spec.get("placeholders", {}), dict))

    # -- one spec ----------------------------------------------------------------

    def note_unverified(self, file, label: str, entry):
        level = level_of(entry)
        if level == "import-tested":
            return
        items = self.unverified.setdefault(file, [])
        if label not in items:
            items.append(label)
            self.add("unverified-step", WARNING, f"{label} is {level}, not import-tested",
                     file, None,
                     "Say so when handing over, with what to check after import.")

    def lint_spec(self, spec: dict, file: str):
        cat = self.catalog
        connectors = [c for c in spec.get("connectors") or [] if isinstance(c, str)]
        used_connectors: set[str] = set()
        if cat is not None:
            self.note_unverified(file, "the legacy package layout", cat.get("package"))
            if connectors:
                self.note_unverified(file, "the generated connection reference (a "
                                     "connectionName that points at no real connection)",
                                     cat.get("package_connection_reference"))

        # every action key, flow-wide
        all_actions: dict[str, dict] = {}
        for where, scope in iter_scopes(spec["actions"]):
            for key, action in scope.items():
                if not ACTION_KEY_RE.match(key):
                    self.add("action-key-invalid", ERROR,
                             f"action key {key!r} is not 1-80 ASCII letters, digits, _ - ( ) .",
                             file, f"{where}/{key}", "Use underscores for spaces.")
                if key in all_actions:
                    self.add("action-key-duplicate", ERROR,
                             f"two actions are named {key!r}", file, f"{where}/{key}")
                all_actions[key] = action if isinstance(action, dict) else {}
            self.check_run_after(scope, where, file)

        # trigger
        for tname, trigger in spec["triggers"].items():
            self.check_trigger(tname, trigger, file, connectors, used_connectors)

        # actions
        for where, scope in iter_scopes(spec["actions"]):
            for key, action in scope.items():
                if isinstance(action, dict):
                    self.check_action(key, action, f"{where}/{key}", file, connectors,
                                      used_connectors)

        for c in connectors:
            if c not in used_connectors:
                self.add("connector-unused", WARNING,
                         f"connector {c} is declared but no step uses it", file, "connectors",
                         "An unused connector still asks for a connection at import.")

        body = {"triggers": spec["triggers"], "actions": spec["actions"]}
        self.check_connections(spec, file)
        self.check_expressions(body, all_actions, file)
        self.check_placeholders(spec, body, file)
        self.check_sensitive(spec, file)

    def check_run_after(self, scope: dict, where: str, file):
        graph: dict[str, list[str]] = {}
        for key, action in scope.items():
            if not isinstance(action, dict) or not isinstance(action.get("runAfter"), dict):
                continue
            deps = []
            for dep in action["runAfter"]:
                if dep == key or dep not in scope:
                    self.add("run-after-unknown", ERROR,
                             f"{key!r} runs after {dep!r}, which is not an action at this "
                             "level" if dep != key else f"{key!r} runs after itself",
                             file, f"{where}/{key}/runAfter")
                else:
                    deps.append(dep)
            graph[key] = deps
        state: dict[str, int] = {}
        reported: set[frozenset] = set()

        def visit(node, stack):
            state[node] = 1
            for dep in graph.get(node, []):
                if state.get(dep) == 1:
                    cycle = stack[stack.index(dep):] + [dep] if dep in stack else [node, dep]
                    sig = frozenset(cycle)
                    if sig not in reported:
                        reported.add(sig)
                        self.add("run-after-cycle", ERROR,
                                 "actions wait for each other: " + " -> ".join(cycle),
                                 file, where)
                elif not state.get(dep):
                    visit(dep, stack + [dep])
            state[node] = 2

        for node in graph:
            if not state.get(node):
                visit(node, [node])

    def check_host(self, host, where, file, connectors, used) -> tuple[str, str] | None:
        if isinstance(host, dict) and API_NAME_RE.match(str(host.get("connectionName", ""))):
            used.add(str(host["connectionName"]))
        if not isinstance(host, dict) or not host.get("connectionName") \
                or not host.get("operationId"):
            self.add("host-invalid", ERROR,
                     "a connector step needs inputs.host.connectionName and operationId",
                     file, where)
            return None
        api, op = str(host["connectionName"]), str(host["operationId"])
        if "apiId" in host and host["apiId"] != API_PREFIX + api:
            self.add("host-invalid", ERROR,
                     f"host.apiId {host['apiId']!r} does not match connectionName {api!r}",
                     file, where, f"Leave apiId out; the builder writes {API_PREFIX}{api}.")
        if not API_NAME_RE.match(api):
            return None  # check_connections reports it
        used.add(api)
        if api not in connectors:
            self.add("connector-undeclared", ERROR,
                     f"{api} is used but not listed in connectors", file, where)
        return api, op

    def check_parameters(self, params, known: dict, label: str, where, file):
        if not isinstance(params, dict):
            return
        for pkey in params:
            if pkey not in known:
                self.add("catalog-missing", ERROR,
                         f"parameter {pkey!r} of {label} is not in the catalog", file,
                         f"{where}/inputs/parameters",
                         "Harvest an export that sets it, or build this step by hand.")
            else:
                self.note_unverified(file, f"parameter {pkey} of {label}", known[pkey])

    def check_trigger(self, tname, trigger, file, connectors, used):
        where = f"triggers/{tname}"
        inputs = trigger.get("inputs") if isinstance(trigger.get("inputs"), dict) else {}
        if isinstance(inputs.get("host"), dict) or trigger.get("type") in CONNECTOR_TYPES:
            self.check_host(inputs.get("host"), where, file, connectors, used)
        if self.catalog is None:
            return
        key = trigger_key(trigger)
        entry = self.catalog["triggers"].get(key)
        if not isinstance(entry, dict):
            self.add("catalog-missing", ERROR, f"trigger shape {key!r} is not in the catalog",
                     file, where,
                     "Only catalogued triggers can be generated. Build it by hand, then "
                     "export and harvest the flow.")
            return
        self.note_unverified(file, f"trigger {key}", entry)
        self.check_parameters(inputs.get("parameters"), entry.get("parameters") or {},
                              f"trigger {key}", where, file)
        props = ((inputs.get("schema") or {}).get("properties")
                 if isinstance(inputs.get("schema"), dict) else None)
        hints = entry.get("input_hints") or {}
        for pname, prop in (props or {}).items():
            if not isinstance(prop, dict):
                continue
            hint = prop.get("x-ms-content-hint")
            shape = hints.get(hint) if hint else None
            if not isinstance(shape, dict):
                self.add("catalog-missing", ERROR,
                         f"trigger input {pname!r} has content hint {hint!r}, which the "
                         "catalog does not hold", file, f"{where}/inputs/schema/{pname}",
                         f"Known hints: {sorted(hints)}")
                continue
            if prop.get("type") != shape.get("type") \
                    or prop.get("format") != shape.get("format"):
                self.add("catalog-missing", ERROR,
                         f"trigger input {pname!r} ({hint}) has type/format "
                         f"{prop.get('type')}/{prop.get('format')}; the catalog knows "
                         f"{shape.get('type')}/{shape.get('format')}", file,
                         f"{where}/inputs/schema/{pname}")
                continue
            self.note_unverified(file, f"trigger input hint {hint}", entry)

    def check_action(self, key, action, where, file, connectors, used):
        atype = action.get("type")
        cat = self.catalog
        inputs = action.get("inputs") if isinstance(action.get("inputs"), dict) else {}
        if atype in CONNECTOR_TYPES:
            pair = self.check_host(inputs.get("host"), where, file, connectors, used)
            if inputs.get("authentication") not in (None, AUTH_INPUT):
                self.add("host-invalid", ERROR,
                         f"authentication must be {AUTH_INPUT!r} or left out", file, where)
        else:
            pair = None
        if cat is None:
            return
        entry = cat["actions"].get(atype)
        if not isinstance(entry, (dict, str)):
            self.add("catalog-missing", ERROR, f"action type {atype!r} is not in the catalog",
                     file, where,
                     "Build this step by hand, then export and harvest the flow.")
        else:
            self.note_unverified(file, f"action type {atype}", entry)
        if not pair:
            return
        api, op = pair
        conn = cat["connectors"].get(api)
        if not isinstance(conn, dict):
            self.add("catalog-missing", ERROR, f"connector {api} is not in the catalog", file,
                     where, "Build this step by hand, then export and harvest the flow.")
            return
        self.note_unverified(file, f"connector {api}", conn)
        ops = conn.get("operations") or {}
        if not isinstance(ops.get(op), dict):
            self.add("catalog-missing", ERROR,
                     f"operation {op} of {api} is not in the catalog", file, where,
                     f"Catalogued operations of {api}: {sorted(ops)}")
            return
        self.note_unverified(file, f"operation {api}/{op}", ops[op])
        self.check_parameters(inputs.get("parameters"), ops[op].get("parameters") or {},
                              f"{api}/{op}", where, file)

    def check_connections(self, spec, file):
        for where, key in iter_keys(spec):
            if key in ("connectionReferences", "$connections"):
                self.add("connection-embedded", ERROR,
                         f"{key} does not belong in a spec", file, where,
                         "The builder writes the connection references; the user picks "
                         "the connections at import.")
        for where, text in iter_strings({"triggers": spec["triggers"],
                                         "actions": spec["actions"]}):
            if CONNECTION_NAME_RE.search(text) or (
                    where.endswith("/host/connectionName") and not API_NAME_RE.match(text)):
                self.add("connection-embedded", ERROR,
                         f"{text!r} looks like a connection name", file, where,
                         "host.connectionName is the API name, e.g. shared_office365.")

    def check_expressions(self, body, all_actions: dict, file):
        for where, text in iter_strings(body):
            if "@" not in text:
                continue
            why = expression_problem(text)
            if why:
                self.add("expression-unbalanced", ERROR, f"expression: {why}", file, where)
            for fn, name in REF_RE.findall(text):
                if name not in all_actions:
                    self.add("expression-reference", ERROR,
                             f"{fn}('{name}') names no action in this flow", file, where)

    def check_placeholders(self, spec, body, file):
        declared = spec.get("placeholders") or {}
        used: dict[str, str] = {}
        for where, text in iter_strings(body):
            for name in PLACEHOLDER_RE.findall(text):
                used.setdefault(name, where)
        for name, where in sorted(used.items()):
            if name not in declared:
                self.add("placeholder-undeclared", ERROR,
                         f"{{{{{name}}}}} is used but not declared in placeholders", file,
                         where)
            elif name not in self.values:
                info = declared[name] if isinstance(declared[name], dict) else {}
                self.add("placeholder-unresolved", WARNING,
                         f"{{{{{name}}}}} has no value: {info.get('description', '')}",
                         file, where,
                         f"Set after import: {info.get('setAfterImport', '?')}. Or build "
                         f"with --set {name}=VALUE.")
        for name in sorted(declared):
            if name not in used:
                self.add("placeholder-unused", WARNING,
                         f"placeholder {name} is declared but nothing uses it", file,
                         f"placeholders/{name}")

    def check_sensitive(self, spec, file):
        for where, text in iter_strings(spec):
            for m in EMAIL_RE.finditer(text):
                if not SAFE_EMAIL_DOMAIN_RE.search(m.group(1)):
                    self.add("sensitive-value", ERROR, "an e-mail address is written into "
                             "the spec", file, where,
                             "Use a trigger input, a list column or a {{Placeholder}}.")
                    break
            if TENANT_URL_RE.search(text):
                self.add("sensitive-value", ERROR, "a tenant URL is written into the spec",
                         file, where, "Use a {{Placeholder}} such as {{SiteAddress}}.")
            if SECRET_RE.search(text):
                self.add("sensitive-value", ERROR, "something that looks like a secret is "
                         "written into the spec", file, where,
                         "Never put a password, key, token or signature in a flow spec.")
            if GUID_RE.search(text):
                self.add("guid-literal", WARNING, "a GUID is written into the spec", file,
                         where, "A list or item id belongs in a {{Placeholder}}.")


# --------------------------------------------------------------------------- driver


def collect(paths) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        p = Path(p)
        out += sorted(p.glob("*.flow.json")) if p.is_dir() else [p]
    return out


def lint_files(paths, catalog_path: Path = DEFAULT_CATALOG, values: dict | None = None
               ) -> dict:
    linter = Linter(catalog_path, values)
    loaded: list[tuple[str, dict]] = []
    for path in paths:
        file = Path(path).as_posix()
        try:
            spec = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            linter.add("spec-invalid", ERROR, f"not readable JSON: {exc}", file)
            continue
        if linter.structurally_ok(spec, file):
            loaded.append((file, spec))
    names: dict[str, str] = {}
    flows = []
    for file, spec in loaded:
        for label, value in (("name", spec["name"]), ("display name", spec.get("displayName"))):
            low = f"{label}:{str(value).strip().lower()}"
            if low in names:
                linter.add("name-duplicate", ERROR,
                           f"{label} {value!r} is also used by {names[low]}", file)
            names[low] = file
        linter.lint_spec(spec, file)
        trig = next(iter(spec["triggers"].items()))
        flows.append({
            "file": file, "name": spec["name"], "displayName": spec.get("displayName"),
            "trigger": f"{trig[0]} ({trigger_key(trig[1])})",
            "actions": sum(len(s) for _, s in iter_scopes(spec["actions"])),
            "connectors": list(spec.get("connectors") or []),
            "placeholders": sorted(spec.get("placeholders") or {}),
            "unverified": linter.unverified.get(file, []),
        })
    return build_report(linter, paths, flows)


def build_report(linter: Linter, paths, flows) -> dict:
    findings = linter.findings
    errors = sum(f.severity == ERROR for f in findings)
    warnings = sum(f.severity == WARNING for f in findings)
    unverified = sum(f.check == "unverified-step" for f in findings)
    if errors:
        code, verdict = "will_fail", f"VERDICT: WILL FAIL — {errors} error(s) to fix"
    elif linter.degraded:
        suffix = f", {warnings} warning(s)" if warnings else ""
        code, verdict = "unproven", f"VERDICT: UNPROVEN — a check could not run{suffix}"
    elif warnings:
        code = "unverified"
        verdict = (f"VERDICT: SHOULD IMPORT, WITH {warnings} ITEM(S) TO CHECK "
                   f"({unverified} unverified catalog item(s))")
    else:
        code, verdict = "safe", "VERDICT: SAFE TO IMPORT"
    findings.sort(key=lambda f: (0 if f.severity == ERROR else 1, f.file or "",
                                 f.check, f.where or ""))
    return {"paths": [Path(p).as_posix() for p in paths], "flows": flows,
            "findings": [f.as_dict() for f in findings], "errors": errors,
            "warnings": warnings, "verdict": verdict, "verdict_code": code,
            "degraded": linter.degraded}


def render(report: dict, quiet=False) -> str:
    out: list[str] = []
    if not quiet:
        names = ", ".join(f"{f['name']} ({f['actions']} actions)"
                          for f in report["flows"]) or "no flow read"
        out += ["=" * 72, names, "=" * 72]
        for note in report["degraded"]:
            out += [f"  NOTE: {note}", ""]
        for sev, title in ((ERROR, "Errors"), (WARNING, "Warnings")):
            group = [f for f in report["findings"] if f["severity"] == sev]
            if not group:
                continue
            out += [title, "-" * 72]
            for f in group:
                out.append(f"  [{sev.upper()}] {f['check']}")
                out.append(f"    {f['message']}")
                where = " ".join(x for x in (f["file"], f["where"] and f"at {f['where']}")
                                 if x)
                if where:
                    out.append(f"    in: {where}")
                if f["detail"]:
                    out.append(f"    {f['detail']}")
                out.append("")
        if not report["findings"]:
            out += ["  No findings.", ""]
    out.append(report["verdict"])
    return "\n".join(out)


def exit_code(report: dict, strict: bool) -> int:
    if report["errors"]:
        return 1
    if strict and (report["warnings"] or report["degraded"]):
        return 2
    return 0


def parse_values(pairs) -> dict[str, str]:
    values: dict[str, str] = {}
    for pair in pairs or []:
        name, sep, value = pair.partition("=")
        if not sep or not re.match(r"^[A-Za-z][A-Za-z0-9]*$", name):
            raise ValueError(f"--set expects NAME=VALUE, got {pair!r}")
        values[name] = value
    return values


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="flow_lint.py",
        description="Check create-flow specs offline and end with a verdict.")
    parser.add_argument("specs", nargs="+", type=Path,
                        help="<FlowName>.flow.json files, or a folder of them")
    parser.add_argument("--set", action="append", default=[], metavar="NAME=VALUE",
                        help="a placeholder value the build will fill in (repeatable)")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG,
                        help="catalog (default: references/connectors.yaml)")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--strict", action="store_true",
                        help="exit 2 when there are warnings but no errors")
    parser.add_argument("--quiet", action="store_true", help="print only the verdict")
    args = parser.parse_args(argv)

    if not args.json:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    try:
        values = parse_values(args.set)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    paths = collect(args.specs)
    missing = [p for p in paths if not p.is_file()]
    if missing or not paths:
        print(f"ERROR: no such spec: {', '.join(map(str, missing)) or args.specs}",
              file=sys.stderr)
        return 2

    report = lint_files(paths, args.catalog, values)
    code = exit_code(report, args.strict)
    if args.json:
        print(json.dumps({"version": 1, "report": report, "exit_code": code},
                         indent=2, ensure_ascii=False))
    else:
        print(render(report, quiet=args.quiet))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
