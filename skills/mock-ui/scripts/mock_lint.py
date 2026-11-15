#!/usr/bin/env python3
"""Offline checker for a mock-ui mockup folder, ending in a verdict.

    python3 scripts/mock_lint.py MOCKUP_DIR [--target web|power-apps]
                                 [--design DESIGN.md] [--profile PATH]
                                 [--json] [--strict] [--quiet]

MOCKUP_DIR holds one .html file per screen, index.html and sitemap.json, as
references/html-contract.md describes. The target defaults to the one sitemap.json
declares. Each finding has a stable check id; tests assert on ids, never on wording.

ERRORS (the mockup breaks the contract; fix before handing it over)
  sitemap-missing     no sitemap.json in the folder
  sitemap-invalid     sitemap.json is not JSON, or breaks assets/sitemap.schema.json
  sitemap-screens     a screen file and its sitemap entry disagree (missing, extra, id)
  sitemap-nav         the sitemap's nav edges differ from the edges in the HTML
                      (a link to the screen it sits on is ignored on both sides)
  screen-id           a screen without a valid data-screen on <body>
  screen-duplicate    two screens with the same data-screen
  dead-control        a link or button with neither data-nav nor data-action
  action-format       a data-action that is not <verb>:<Object> (several, space-
                      separated, run in order)
  nav-mismatch        data-nav disagrees with where the control really goes with
                      JavaScript off, or a control navigates without saying so
  broken-link         a local href, src, action or formaction to a missing file
  external-resource   a URL with a scheme or //host, or any @import
  unreachable         a screen that cannot be reached from `start` (a "state"
                      variant is exempt: index.html opens it)
  var-undefined       var(--x) used but --x is defined nowhere on the page
  canvas-size         power-apps: <body> without an explicit px width and height that
                      match the sitemap's canvas and the screen's height
  pa-effect           power-apps: an effect the profile rules out, not scoped to an
                      element marked data-unsupported="<profile id>"

WARNINGS (review; fix, or say why it stands)
  no-way-back         a screen from which `start` cannot be reached
  literal-hex         a hex colour outside :root
  token-drift         --design: a :root value differs from what tokens_to_css.py
                      prints for that DESIGN.md, or a token is missing
  sitemap-data        data-source / data-repeat / data-field differ from sitemap data
  sitemap-actions     data-action ids differ from the sitemap's actions
  scroll-flag         power-apps: height above the canvas without "scrolls": true,
                      or the reverse
  pa-geometry         power-apps: a length that depends on text or viewport
                      (em, rem, vw, vh, ch, min/max/fit-content, auto-fill/auto-fit)
  unsupported-id      data-unsupported names an id the profile does not have
  label-missing       a form field without a <label for>
  select-options      a <select> with fewer than two options
  data-name           a data-source/data-repeat/data-field that is not PascalCase
  field-source        a data-field with no data-source or data-repeat around it
  repeat-rows         a data-repeat container without two or three sample rows
  local-asset         a reference to a local non-HTML file (the page must stand alone)
  script              a <script>; navigation must work with JavaScript off
  style-blocks        not exactly one <style> element
  screen-title        a screen without data-title
  index-missing       no index.html, or it does not link every screen

Exit codes: 0 no errors | 1 any error | 2 warnings (or unproven) with --strict, or a
usage problem. Standard library only; --design also needs PyYAML.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import defaultdict, deque
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

SKILL_DIR = Path(__file__).resolve().parent.parent  # this skill's own folder
DEFAULT_PROFILE = SKILL_DIR / "references" / "shared" / "powerapps-profile.md"
SCHEMA_PATH = SKILL_DIR / "assets" / "sitemap.schema.json"
TOKENS_SCRIPT = Path(__file__).resolve().parent / "tokens_to_css.py"

ERROR, WARNING = "error", "warning"
SCREEN_RE = re.compile(r"^scr[A-Z][A-Za-z0-9]*$")
NAME_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
ACTION_RE = re.compile(r"^[a-z][a-z0-9-]*:[A-Za-z][A-Za-z0-9]*$")
SCHEME_RE = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|//)")
HEX_RE = re.compile(r"(?<![\w&-])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])")
VAR_RE = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)\s*(?:,([^()]*(?:\([^()]*\)[^()]*)*))?\)")
URL_RE = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.I)
PX_RE = re.compile(r"^(\d+(?:\.\d+)?)px$")
PROFILE_ID_RE = re.compile(r"impossible_css\[id=([a-z0-9-]+)\]")

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "param", "source", "track", "wbr"}
FIELD_SKIP_TYPES = {"hidden", "submit", "button", "reset", "image"}
CONTROL_INPUT_TYPES = {"submit", "button", "reset", "image"}
LINK_ATTRS = ("href", "src", "action", "formaction", "poster", "data")

# power-apps geometry: properties whose value must be arithmetic on a fixed canvas.
GEOMETRY_PROPS = re.compile(
    r"^(?:width|height|min-width|min-height|max-width|max-height|top|left|right|bottom|"
    r"inset|gap|row-gap|column-gap|padding(?:-\w+)?|margin(?:-\w+)?|flex-basis|flex|"
    r"grid-template-columns|grid-template-rows|grid-auto-rows|grid-auto-columns|"
    r"font-size|border-radius|border-width)$")
FLUID_RE = re.compile(r"(?<![\w-])-?(?:\d+\.?\d*|\.\d+)(?:em|rem|vw|vh|vmin|vmax|ch|ex)\b|"
                      r"\b(?:min-content|max-content|fit-content|auto-fill|auto-fit)\b", re.I)
SEGOE_RE = re.compile(r"^\s*['\"]?segoe ui['\"]?\s*$", re.I)
SIDE_BORDER_RE = re.compile(r"^border-(?:left|right|top|bottom)(?:-width|-style|-color)?$|"
                            r"^border-(?:inline|block)(?:-start|-end)?(?:-width|-style|-color)?$")


# --------------------------------------------------------------------------- findings


class Finding:
    __slots__ = ("check", "severity", "message", "file", "line", "detail")

    def __init__(self, check, severity, message, file=None, line=None, detail=None):
        self.check, self.severity, self.message = check, severity, message
        self.file, self.line, self.detail = file, line, detail

    def as_dict(self):
        return {"check": self.check, "severity": self.severity, "message": self.message,
                "file": self.file, "line": self.line, "detail": self.detail}


# --------------------------------------------------------------------------- HTML


class Element:
    __slots__ = ("tag", "attrs", "parent", "children", "line", "text")

    def __init__(self, tag, attrs, parent, line):
        self.tag, self.parent, self.line = tag, parent, line
        self.attrs = {k.lower(): (v if v is not None else "") for k, v in attrs}
        self.children: list[Element] = []
        self.text = ""

    def get(self, name, default=None):
        return self.attrs.get(name, default)

    def ancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()


class Page(HTMLParser):
    """A small DOM: elements with attributes, parents, line numbers, and style text."""

    def __init__(self, text: str):
        super().__init__(convert_charrefs=True)
        self.root = Element("#document", [], None, 1)
        self.stack = [self.root]
        self.styles: list[tuple[str, int]] = []      # (css text, line where it starts)
        self.style_count = 0
        self._in_style = False
        self.feed(text)
        self.close()

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        el = Element(tag, attrs, self.stack[-1], line)
        self.stack[-1].children.append(el)
        if tag == "style":
            self.style_count += 1
            self._in_style = True
        if tag not in VOID:
            self.stack.append(el)

    def handle_startendtag(self, tag, attrs):
        line = self.getpos()[0]
        self.stack[-1].children.append(Element(tag, attrs, self.stack[-1], line))

    def handle_endtag(self, tag):
        if tag == "style":
            self._in_style = False
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self._in_style:
            self.styles.append((data, self.getpos()[0]))
        elif self.stack:
            self.stack[-1].text += data

    def elements(self):
        for child in self.root.children:
            yield from child.walk()

    def first(self, tag):
        return next((e for e in self.elements() if e.tag == tag), None)


# --------------------------------------------------------------------------- CSS


class Rule:
    __slots__ = ("selector", "decls", "line", "at")

    def __init__(self, selector, decls, line, at=None):
        self.selector, self.decls, self.line, self.at = selector, decls, line, at


def _blank_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), css, flags=re.S)


def parse_declarations(block: str, line: int) -> list[tuple[str, str, int]]:
    out, offset = [], 0
    for part in re.split(r";(?![^(]*\))", block):
        if ":" in part:
            prop, value = part.split(":", 1)
            lead = len(part) - len(part.lstrip())
            out.append((prop.strip().lower(), value.strip(),
                        line + block.count("\n", 0, offset + lead)))
        offset += len(part) + 1
    return out


def parse_css(css: str, line: int) -> tuple[list[Rule], list[tuple[str, int]]]:
    """(rules, at-statements). @media/@supports blocks are flattened into rules."""
    css = _blank_comments(css)
    rules: list[Rule] = []
    ats: list[tuple[str, int]] = []
    i, n = 0, len(css)
    while i < n:
        j = i
        while j < n and css[j] not in "{;":
            j += 1
        prelude = css[i:j].strip()
        pline = line + css.count("\n", 0, i + (len(css[i:j]) - len(css[i:j].lstrip())))
        if j >= n:
            break
        if css[j] == ";":
            if prelude.startswith("@"):
                ats.append((prelude, pline))
            i = j + 1
            continue
        depth, k = 1, j + 1
        while k < n and depth:
            depth += {"{": 1, "}": -1}.get(css[k], 0)
            k += 1
        body = css[j + 1:k - 1]
        bline = line + css.count("\n", 0, j + 1)
        low = prelude.lower()
        if low.startswith(("@media", "@supports", "@layer", "@container")):
            inner, inner_ats = parse_css(body, bline)
            rules += inner
            ats += inner_ats
        elif low.startswith("@"):
            ats.append((prelude, pline))
            rules.append(Rule(prelude, parse_declarations(body, bline), pline, at=low.split()[0]))
        else:
            rules.append(Rule(prelude, parse_declarations(body, bline), pline))
        i = k
    return rules, ats


def is_root_selector(selector: str) -> bool:
    return all(s.strip() in (":root", "html") for s in selector.split(","))


def resolve(value: str, root: dict[str, str], depth: int = 0) -> str:
    if depth > 12 or "var(" not in value:
        return value

    def sub(m):
        name, fallback = m.group(1), m.group(2)
        if name in root:
            return resolve(root[name], root, depth + 1)
        return resolve(fallback.strip(), root, depth + 1) if fallback else ""
    return VAR_RE.sub(sub, value)


# --------------------------------------------------------------------------- schema


def validate_schema(value, schema: dict, root: dict, path: str = "$") -> list[str]:
    """The subset of JSON Schema that assets/sitemap.schema.json uses, standard library
    only: $ref, type, const, enum, pattern, minimum, minLength, minItems, required,
    properties, additionalProperties, items."""
    if "$ref" in schema:
        node = root
        for part in schema["$ref"].lstrip("#/").split("/"):
            node = node[part]
        return validate_schema(value, node, root, path)
    errs: list[str] = []
    kind = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "boolean": bool,
             "integer": int, "number": (int, float)}
    if kind:
        ok = isinstance(value, types[kind])
        if kind in ("integer", "number") and isinstance(value, bool):
            ok = False
        if not ok:
            return [f"{path}: expected {kind}"]
    if "const" in schema and value != schema["const"]:
        errs.append(f"{path}: must be {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: must be one of {schema['enum']}")
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errs.append(f"{path}: {value!r} does not match {schema['pattern']}")
        if len(value) < schema.get("minLength", 0):
            errs.append(f"{path}: too short")
    if isinstance(value, (int, float)) and "minimum" in schema and value < schema["minimum"]:
        errs.append(f"{path}: below {schema['minimum']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errs.append(f"{path}: needs at least {schema['minItems']} item(s)")
        if "items" in schema:
            for i, item in enumerate(value):
                errs += validate_schema(item, schema["items"], root, f"{path}[{i}]")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errs.append(f"{path}: missing '{key}'")
        props = schema.get("properties", {})
        for key, item in value.items():
            if key in props:
                errs += validate_schema(item, props[key], root, f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: unknown key '{key}'")
    return errs


# --------------------------------------------------------------------------- linter


class ScreenFile:
    def __init__(self, path: Path, page: Page):
        self.path, self.page = path, page
        self.body = page.first("body")
        self.screen = self.body.get("data-screen") if self.body is not None else None
        self.rules: list[Rule] = []
        self.ats: list[tuple[str, int]] = []
        for css, line in page.styles:
            rules, ats = parse_css(css, line)
            self.rules += rules
            self.ats += ats
        self.root: dict[str, str] = {}
        for rule in self.rules:
            if is_root_selector(rule.selector):
                for prop, value, _line in rule.decls:
                    if prop.startswith("--"):
                        self.root[prop] = value
        self.edges: list[tuple[str, Element]] = []   # (target screen id, control)


class Linter:
    def __init__(self, folder: Path, target: str | None, design: Path | None,
                 profile: Path):
        self.folder = folder
        self.cli_target = target
        self.design = design
        self.profile = profile
        self.findings: list[Finding] = []
        self.degraded: list[str] = []
        self.sitemap: dict | None = None
        self.target = target or "web"
        self.screens: dict[str, ScreenFile] = {}       # file name -> ScreenFile
        self.by_id: dict[str, ScreenFile] = {}
        self.profile_ids: set[str] = set()

    def add(self, check, severity, message, file=None, line=None, detail=None):
        self.findings.append(Finding(check, severity, message, file, line, detail))

    def rel(self, path: Path) -> str:
        try:
            return path.relative_to(self.folder).as_posix()
        except ValueError:
            return path.as_posix()

    # ------------------------------------------------------------------ driver

    def run(self):
        self.load_sitemap()
        if self.target == "power-apps":
            try:
                self.profile_ids = set(PROFILE_ID_RE.findall(
                    self.profile.read_text(encoding="utf-8")))
            except OSError:
                self.profile_ids = set()
            if not self.profile_ids:
                self.degraded.append(
                    "the Power Apps profile could not be read, so pa-effect did not run. "
                    "Expected references/shared/powerapps-profile.md in this skill's folder.")
        for path in sorted(self.folder.glob("*.html")):
            try:
                page = Page(path.read_text(encoding="utf-8-sig"))
            except UnicodeDecodeError:
                self.add("screen-id", ERROR, "The file is not UTF-8 text.", path.name)
                continue
            sf = ScreenFile(path, page)
            self.screens[path.name] = sf
        for name, sf in self.screens.items():
            if name == "index.html":
                continue
            self.check_screen_id(sf)
        for sf in self.screens.values():
            self.check_resources(sf)
            self.check_css(sf)
            self.check_controls(sf)
            if sf.path.name != "index.html":
                self.check_fields(sf)
                if self.target == "power-apps":
                    self.check_power_apps(sf)
        self.check_sitemap_screens()
        self.check_graph()
        self.check_index()
        if self.design is not None:
            self.check_design()

    # ------------------------------------------------------------------ sitemap

    def load_sitemap(self):
        path = self.folder / "sitemap.json"
        if not path.is_file():
            self.add("sitemap-missing", ERROR, "There is no sitemap.json in the mockup folder.",
                     detail="Write it from the screen inventory; assets/sitemap.schema.json "
                            "is its schema.")
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self.add("sitemap-invalid", ERROR, f"sitemap.json is not valid JSON: {exc}",
                     "sitemap.json")
            return
        try:
            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            schema = None
            self.degraded.append("assets/sitemap.schema.json could not be read, so the "
                                 "sitemap was not checked against its schema.")
        errs = validate_schema(data, schema, schema) if schema else []
        if isinstance(data, dict) and data.get("target") == "power-apps":
            if "canvas" not in data:
                errs.append("$: power-apps target needs 'canvas'")
            for i, s in enumerate(data.get("screens") or []):
                if isinstance(s, dict) and "height" not in s:
                    errs.append(f"$.screens[{i}]: power-apps target needs 'height'")
        if isinstance(data, dict):
            ids = [s.get("id") for s in data.get("screens") or [] if isinstance(s, dict)]
            dup = sorted({i for i in ids if ids.count(i) > 1})
            if dup:
                errs.append(f"$.screens: duplicate id(s) {dup}")
            if data.get("start") not in ids:
                errs.append(f"$.start: {data.get('start')!r} is not one of the screens")
        for e in errs:
            self.add("sitemap-invalid", ERROR, f"sitemap.json: {e}", "sitemap.json")
        if isinstance(data, dict):
            self.sitemap = data
            if self.cli_target is None and data.get("target") in ("web", "power-apps"):
                self.target = data["target"]

    def sitemap_screen(self, file_name: str) -> dict | None:
        for s in (self.sitemap or {}).get("screens") or []:
            if isinstance(s, dict) and s.get("file") == file_name:
                return s
        return None

    def check_sitemap_screens(self):
        if self.sitemap is None:
            return
        listed = {s.get("file"): s for s in self.sitemap.get("screens") or []
                  if isinstance(s, dict)}
        for file_name, entry in listed.items():
            sf = self.screens.get(file_name)
            if sf is None:
                self.add("sitemap-screens", ERROR,
                         f"sitemap.json lists {file_name}, which is not in the folder.",
                         "sitemap.json")
            elif sf.screen and entry.get("id") != sf.screen:
                self.add("sitemap-screens", ERROR,
                         f"sitemap.json calls {file_name} {entry.get('id')!r}, but its "
                         f"<body> says data-screen=\"{sf.screen}\".", file_name,
                         sf.body.line if sf.body is not None else None)
        for file_name in self.screens:
            if file_name != "index.html" and file_name not in listed:
                self.add("sitemap-screens", ERROR,
                         f"{file_name} is a screen file that sitemap.json does not list.",
                         file_name)

    # ------------------------------------------------------------------ per file

    def check_screen_id(self, sf: ScreenFile):
        name = sf.path.name
        if sf.body is None or not sf.screen:
            self.add("screen-id", ERROR, "<body> has no data-screen attribute.", name,
                     sf.body.line if sf.body is not None else None,
                     'Write <body data-screen="scrPascalName" data-title="...">.')
            return
        if not SCREEN_RE.match(sf.screen):
            self.add("screen-id", ERROR,
                     f"data-screen=\"{sf.screen}\" is not scr + PascalCase (letters and "
                     "digits only).", name, sf.body.line)
        if sf.screen in self.by_id:
            self.add("screen-duplicate", ERROR,
                     f"data-screen=\"{sf.screen}\" is also used by "
                     f"{self.by_id[sf.screen].path.name}.", name, sf.body.line)
        else:
            self.by_id[sf.screen] = sf
        if not (sf.body.get("data-title") or "").strip():
            self.add("screen-title", WARNING, "<body> has no data-title.", name, sf.body.line)

    def local_target(self, sf: ScreenFile, url: str) -> Path | None:
        """The local file a URL points at, or None for a fragment, empty or remote URL."""
        url = (url or "").strip()
        if not url or url.startswith("#") or SCHEME_RE.match(url):
            return None
        path_part = unquote(re.split(r"[?#]", url, 1)[0])
        return (sf.path.parent / path_part) if path_part else None

    def check_resources(self, sf: ScreenFile):
        name = sf.path.name
        for el in sf.page.elements():
            for attr in LINK_ATTRS:
                url = el.get(attr)
                if url is None:
                    continue
                url = url.strip()
                if url.lower().startswith("javascript:") or url.lower().startswith("data:"):
                    continue
                if SCHEME_RE.match(url):
                    self.add("external-resource", ERROR,
                             f"<{el.tag} {attr}=\"{url}\"> needs the network.", name, el.line,
                             "A mockup is one self-contained file: inline the CSS, draw "
                             "icons as inline SVG, use a placeholder box with data-image "
                             "for a picture, and system fonts.")
                    continue
                target = self.local_target(sf, url)
                if target is None:
                    continue
                if not target.is_file():
                    self.add("broken-link", ERROR,
                             f"<{el.tag} {attr}=\"{url}\"> points at a file that does not "
                             "exist.", name, el.line)
                elif target.suffix.lower() != ".html":
                    self.add("local-asset", WARNING,
                             f"<{el.tag} {attr}=\"{url}\"> loads a separate file; the page "
                             "must stand alone.", name, el.line)
            if el.tag == "script":
                self.add("script", WARNING,
                         "The page has a <script>. Navigation must work with JavaScript off, "
                         "and the contract needs no other behaviour.", name, el.line)
            if el.tag == "link" and "stylesheet" in (el.get("rel") or "").lower() \
                    and not SCHEME_RE.match(el.get("href") or ""):
                self.add("style-blocks", WARNING,
                         "A <link rel=stylesheet>: put all CSS in the page's one <style>.",
                         name, el.line)
        if sf.page.style_count != 1:
            self.add("style-blocks", WARNING,
                     f"The page has {sf.page.style_count} <style> elements; the contract "
                     "asks for exactly one.", name)
        for prelude, line in sf.ats:
            if prelude.lower().startswith("@import"):
                self.add("external-resource", ERROR,
                         f"`{prelude}`: an @import loads another file.", name, line)
        for text, line in self.style_texts(sf):
            for m in URL_RE.finditer(text):
                url = m.group(2).strip()
                if not url or url.lower().startswith("data:") or url.startswith("#"):
                    continue
                if SCHEME_RE.match(url):
                    self.add("external-resource", ERROR,
                             f"url({url}) needs the network.", name, line)
                else:
                    target = self.local_target(sf, url)
                    if target is not None and not target.is_file():
                        self.add("broken-link", ERROR, f"url({url}) points at a missing "
                                 "file.", name, line)
                    else:
                        self.add("local-asset", WARNING, f"url({url}) loads a separate "
                                 "file; the page must stand alone.", name, line)

    def style_texts(self, sf: ScreenFile):
        """(css text, line) for every declaration value, in rules and style attributes."""
        for rule in sf.rules:
            for prop, value, line in rule.decls:
                yield value, line
        for el in sf.page.elements():
            if el.get("style"):
                yield el.get("style"), el.line

    def inline_decls(self, sf: ScreenFile):
        for el in sf.page.elements():
            if el.get("style"):
                for prop, value, _line in parse_declarations(el.get("style"), el.line):
                    yield el, prop, value

    def check_css(self, sf: ScreenFile):
        name = sf.path.name
        used: set[tuple[str, int]] = set()
        for rule in sf.rules:
            root = is_root_selector(rule.selector)
            for prop, value, line in rule.decls:
                for m in VAR_RE.finditer(value):
                    used.add((m.group(1), line))
                if not root and HEX_RE.search(value):
                    self.add("literal-hex", WARNING,
                             f"`{prop}: {value}` in `{rule.selector}` is a literal colour; "
                             "use var(--color-...).", name, line)
        for el, prop, value in self.inline_decls(sf):
            for m in VAR_RE.finditer(value):
                used.add((m.group(1), el.line))
            if HEX_RE.search(value):
                self.add("literal-hex", WARNING,
                         f"style=\"{prop}: {value}\" on <{el.tag}> is a literal colour; use "
                         "var(--color-...).", name, el.line)
        missing: dict[str, int] = {}
        for var, line in sorted(used, key=lambda x: x[1]):
            if var not in sf.root and var not in missing:
                missing[var] = line
        for var, line in missing.items():
            self.add("var-undefined", ERROR,
                     f"var({var}) is used, but {var} is not defined in :root.", name, line)

    def check_controls(self, sf: ScreenFile):
        name = sf.path.name
        for el in sf.page.elements():
            kind = None
            if el.tag in ("a", "button"):
                kind = el.tag
            elif el.tag == "input" and (el.get("type") or "").lower() in CONTROL_INPUT_TYPES:
                kind = "input"
            elif (el.get("role") or "").lower() == "button":
                kind = "role"
            if kind is None:
                continue
            nav = (el.get("data-nav") or "").strip()
            act = (el.get("data-action") or "").strip()
            label = self.control_label(el)
            if not nav and not act:
                self.add("dead-control", ERROR,
                         f"<{el.tag}> {label} has neither data-nav nor data-action.",
                         name, el.line,
                         "Give it data-nav=\"scrTarget\" and a real href/form action, or "
                         "data-action=\"verb:Object\".")
            bad = [a for a in act.split() if not ACTION_RE.match(a)]
            if bad:
                self.add("action-format", ERROR,
                         f"data-action=\"{act}\" on {label}: {', '.join(bad)} is not "
                         "<verb>:<Object> (for example submit:Requests, "
                         "run-flow:NotifyApprover).", name, el.line)
            url = self.navigation_url(el, kind)
            target = self.local_target(sf, url) if url else None
            target_screen = None
            if target is not None and target.is_file() and target.suffix.lower() == ".html":
                other = self.screens.get(target.name) if target.parent.resolve() == \
                    self.folder.resolve() else None
                target_screen = other.screen if other is not None else None
                if target_screen and sf.path.name != "index.html":
                    sf.edges.append((target_screen, el))
            if nav:
                if url is None or target is None:
                    self.add("nav-mismatch", ERROR,
                             f"{label} says data-nav=\"{nav}\", but with JavaScript off it "
                             "goes nowhere.", name, el.line,
                             "Use <a href=\"file.html\">, or a submit button inside "
                             "<form action=\"file.html\">.")
                elif target.is_file() and nav != target_screen:
                    self.add("nav-mismatch", ERROR,
                             f"{label} says data-nav=\"{nav}\", but {url} is "
                             f"{target_screen or 'not a screen'}.", name, el.line)
            elif target is not None and target.is_file():
                self.add("nav-mismatch", ERROR,
                         f"{label} navigates to {url} but carries no data-nav.",
                         name, el.line,
                         "An action that moves on carries both data-action and data-nav; "
                         "a button that should stay on the screen is type=\"button\".")

    def navigation_url(self, el: Element, kind: str) -> str | None:
        if kind == "a":
            href = el.get("href")
            if href is None or href.strip().startswith("#") or \
                    href.strip().lower().startswith("javascript:"):
                return None
            return href
        if kind in ("button", "input"):
            default = "submit" if kind == "button" else ""
            if (el.get("type") or default).lower() not in ("submit", "image"):
                return None
            if el.get("formaction") is not None:
                return el.get("formaction")
            form = next((a for a in el.ancestors() if a.tag == "form"), None)
            if form is None:
                return None
            return form.get("action")
        return None

    @staticmethod
    def control_label(el: Element) -> str:
        text = " ".join(" ".join(c.text for c in el.walk()).split())
        text = text or el.get("aria-label") or el.get("value") or el.get("title") or ""
        return f"\"{text[:40]}\"" if text else f"(line {el.line})"

    def check_fields(self, sf: ScreenFile):
        name = sf.path.name
        labels_for = {e.get("for") for e in sf.page.elements() if e.tag == "label"}
        for el in sf.page.elements():
            if el.tag in ("input", "select", "textarea"):
                kind = (el.get("type") or "text").lower()
                if el.tag == "input" and kind in FIELD_SKIP_TYPES:
                    continue
                fid = el.get("id")
                wrapped = any(a.tag == "label" for a in el.ancestors())
                if not wrapped and (not fid or fid not in labels_for):
                    self.add("label-missing", WARNING,
                             f"<{el.tag}{' id=' + fid if fid else ''}> has no <label for>.",
                             name, el.line)
                if el.tag == "select":
                    options = [c for c in el.walk() if c.tag == "option"]
                    if len(options) < 2:
                        self.add("select-options", WARNING,
                                 "A <select> needs its real options (at least two); a "
                                 "single option reads as a text box.", name, el.line)
            for attr in ("data-source", "data-repeat", "data-field"):
                val = el.get(attr)
                if val is not None and not NAME_RE.match(val):
                    self.add("data-name", WARNING,
                             f"{attr}=\"{val}\" is not a PascalCase internal name.",
                             name, el.line)
            if el.get("data-field") is not None and not any(
                    a.get("data-source") or a.get("data-repeat") for a in el.ancestors()):
                self.add("field-source", WARNING,
                         f"data-field=\"{el.get('data-field')}\" has no data-source or "
                         "data-repeat around it.", name, el.line)
            if el.get("data-repeat") is not None:
                rows = [c for c in el.children if not c.tag.startswith("#")]
                if not 2 <= len(rows) <= 3:
                    self.add("repeat-rows", WARNING,
                             f"data-repeat=\"{el.get('data-repeat')}\" holds {len(rows)} "
                             "row(s); write two or three sample rows and keep headers "
                             "outside the container.", name, el.line)

    # ------------------------------------------------------------------ power-apps

    def body_size(self, sf: ScreenFile) -> tuple[str | None, str | None, int | None]:
        width = height = None
        line = sf.body.line if sf.body is not None else None
        for rule in sf.rules:
            if any(s.strip() == "body" for s in rule.selector.split(",")):
                for prop, value, dline in rule.decls:
                    if prop == "width":
                        width, line = resolve(value, sf.root).strip(), dline
                    elif prop == "height":
                        height = resolve(value, sf.root).strip()
        if sf.body is not None and sf.body.get("style"):
            for prop, value, _l in parse_declarations(sf.body.get("style"), sf.body.line):
                if prop == "width":
                    width = resolve(value, sf.root).strip()
                elif prop == "height":
                    height = resolve(value, sf.root).strip()
        return width, height, line

    def check_power_apps(self, sf: ScreenFile):
        name = sf.path.name
        canvas = (self.sitemap or {}).get("canvas") or {}
        entry = self.sitemap_screen(name) or {}
        width, height, line = self.body_size(sf)
        cw, ch = canvas.get("width"), canvas.get("height")
        wpx = PX_RE.match(width or "")
        hpx = PX_RE.match(height or "")
        if not wpx or not hpx:
            self.add("canvas-size", ERROR,
                     f"<body> needs an explicit px width and height (found width "
                     f"{width or 'none'}, height {height or 'none'}).", name, line,
                     "Write body { width: var(--canvas-width); height: <screen height>px; }.")
        else:
            w, h = float(wpx.group(1)), float(hpx.group(1))
            if cw is not None and w != cw:
                self.add("canvas-size", ERROR,
                         f"<body> is {width} wide; the sitemap canvas is {cw}px.", name, line)
            if ch is not None and h < ch:
                self.add("canvas-size", ERROR,
                         f"<body> is {height} tall, less than the {ch}px canvas.", name, line)
            if entry.get("height") is not None and h != entry.get("height"):
                self.add("canvas-size", ERROR,
                         f"<body> is {height} tall; sitemap.json says height "
                         f"{entry.get('height')}.", name, line)
            if ch is not None:
                tall = h > ch
                if tall != bool(entry.get("scrolls")):
                    self.add("scroll-flag", WARNING,
                             f"<body> is {height} tall on a {ch}px canvas, but sitemap.json "
                             f"has \"scrolls\": {str(bool(entry.get('scrolls'))).lower()}.",
                             name, line)
        self.check_effects(sf)

    def marked(self, el: Element, pid: str) -> bool:
        return pid in (el.get("data-unsupported") or "").split()

    def check_effects(self, sf: ScreenFile):
        name = sf.path.name
        ids = self.profile_ids

        def selector_marked(selector: str, pid: str) -> bool:
            parts = [s.strip() for s in selector.split(",")]
            return all(re.search(r"\[data-unsupported~=['\"]?%s['\"]?\]" % re.escape(pid), p)
                       for p in parts)

        def effects(prop: str, value: str, selector: str | None) -> list[str]:
            v = value.strip().lower()
            found = []
            if prop in ("box-shadow", "text-shadow") and v not in ("none", "0", ""):
                found.append("box-shadow")
            if prop in ("filter", "-webkit-filter") and "drop-shadow" in v:
                found.append("box-shadow")
            if prop in ("backdrop-filter", "-webkit-backdrop-filter") and v != "none":
                found.append("backdrop-blur")
            if prop in ("filter", "-webkit-filter") and "blur(" in v:
                found.append("backdrop-blur")
            if (prop.startswith("transition") or prop.startswith("animation")) and \
                    v not in ("none", "0s", "0"):
                found.append("css-transition")
            if SIDE_BORDER_RE.match(prop) and not re.match(r"^(none|0|0px)\b", v) \
                    and "hidden" not in v:
                found.append("border-left-only")
            if prop in ("font-family", "font"):
                fam = resolve(value, sf.root)
                if prop == "font":
                    m = re.search(r"\d(?:px|pt|em|rem|%)(?:/\S+)?\s+(.+)$", fam)
                    fam = m.group(1) if m else ""
                first = fam.split(",")[0] if fam.strip() else ""
                if first and first.strip().lower() not in ("inherit", "initial", "unset") \
                        and not SEGOE_RE.match(first):
                    found.append("non-segoe-font")
            return [f for f in found if f in ids]

        for rule in sf.rules:
            if is_root_selector(rule.selector):
                continue
            if rule.at == "@keyframes" or (rule.selector.lower().startswith("@keyframes")):
                if "css-transition" in ids:
                    self.add("pa-effect", ERROR,
                             f"`{rule.selector}` animates; the profile rules out "
                             "css-transition.", name, rule.line,
                             "Drop it; a canvas changes state instantly.")
                continue
            hover_parts = [s for s in rule.selector.split(",")
                           if re.search(r":hover\s*(?:[>+~]|\s)\s*[^\s,{]", s)]
            if hover_parts and "group-hover" in ids and not selector_marked(
                    rule.selector, "group-hover"):
                self.add("pa-effect", ERROR,
                         f"`{rule.selector.strip()}` styles a child when its parent is "
                         "hovered (group-hover).", name, rule.line,
                         "Put the hover on the control itself, or scope the rule to "
                         "[data-unsupported~=\"group-hover\"].")
            for prop, value, line in rule.decls:
                for pid in effects(prop, value, rule.selector):
                    if not selector_marked(rule.selector, pid):
                        self.add("pa-effect", ERROR,
                                 f"`{prop}: {value}` in `{rule.selector.strip()}` is "
                                 f"{pid}, which the Power Apps profile rules out.",
                                 name, line,
                                 f"Use the profile's substitute, or scope the rule to "
                                 f"[data-unsupported~=\"{pid}\"] and mark the element.")
                self.geometry(sf, prop, value, line)
        for el, prop, value in self.inline_decls(sf):
            for pid in effects(prop, value, None):
                if not self.marked(el, pid):
                    self.add("pa-effect", ERROR,
                             f"style=\"{prop}: {value}\" on <{el.tag}> is {pid}, which the "
                             "Power Apps profile rules out.", name, el.line,
                             f"Add data-unsupported=\"{pid}\" to the element, or use the "
                             "substitute.")
            self.geometry(sf, prop, value, el.line)
        for el in sf.page.elements():
            for pid in (el.get("data-unsupported") or "").split():
                if ids and pid not in ids:
                    self.add("unsupported-id", WARNING,
                             f"data-unsupported=\"{pid}\" is not an id in the Power Apps "
                             f"profile ({', '.join(sorted(ids))}).", name, el.line)

    def geometry(self, sf: ScreenFile, prop: str, value: str, line: int):
        if prop.startswith("--") or not GEOMETRY_PROPS.match(prop):
            return
        resolved = resolve(value, sf.root)
        if FLUID_RE.search(resolved):
            self.add("pa-geometry", WARNING,
                     f"`{prop}: {value}` depends on text or viewport size; on a fixed "
                     "canvas every length is px arithmetic.", sf.path.name, line)

    # ------------------------------------------------------------------ graph

    def check_graph(self):
        if self.sitemap is None:
            return
        start = self.sitemap.get("start")
        graph: dict[str, set[str]] = defaultdict(set)
        for sf in self.screens.values():
            if sf.screen and sf.path.name != "index.html":
                for target, _el in sf.edges:
                    if target != sf.screen:      # a link to the current screen is chrome
                        graph[sf.screen].add(target)
        ids = [sf.screen for n, sf in self.screens.items()
               if n != "index.html" and sf.screen and SCREEN_RE.match(sf.screen)]

        def reach(src):
            seen, queue = {src}, deque([src])
            while queue:
                for nxt in graph.get(queue.popleft(), ()):
                    if nxt not in seen:
                        seen.add(nxt)
                        queue.append(nxt)
            return seen

        states = {e.get("id"): e.get("variantOf") for e in self.sitemap.get("screens") or []
                  if isinstance(e, dict) and e.get("kind") == "state"}
        for sid, base in states.items():
            if base not in ids:
                self.add("sitemap-invalid", ERROR,
                         f"sitemap.json: state screen {sid} needs \"variantOf\" naming one "
                         "of the screens.", "sitemap.json")
        if start in ids:
            reachable = reach(start)
            for sid in ids:
                # A state variant (empty, error) is opened from index.html, like a
                # storyboard frame; it still needs a way back.
                if sid not in reachable and sid not in states:
                    self.add("unreachable", ERROR,
                             f"{sid} cannot be reached by clicking from {start}.",
                             self.by_id[sid].path.name)
            for sid in ids:
                if sid != start and sid in reachable and start not in reach(sid):
                    self.add("no-way-back", WARNING,
                             f"From {sid} there is no way back to {start}.",
                             self.by_id[sid].path.name)

        for entry in self.sitemap.get("screens") or []:
            if not isinstance(entry, dict):
                continue
            sf = self.screens.get(entry.get("file"))
            if sf is None or not sf.screen:
                continue
            declared = {n.get("to") for n in entry.get("nav") or []
                        if isinstance(n, dict) and n.get("to") != sf.screen}
            found = graph.get(sf.screen, set())
            for to in sorted(found - declared):
                self.add("sitemap-nav", ERROR,
                         f"{sf.screen} links to {to} in the HTML, but sitemap.json's nav "
                         "does not list it.", sf.path.name)
            for to in sorted(declared - found):
                self.add("sitemap-nav", ERROR,
                         f"sitemap.json says {sf.screen} links to {to}, but no control in "
                         "the HTML does.", "sitemap.json")
            self.compare_data(entry, sf)

    def compare_data(self, entry: dict, sf: ScreenFile):
        html_sources: dict[str, set[str]] = defaultdict(set)
        html_actions: set[str] = set()
        for el in sf.page.elements():
            src = el.get("data-source") or el.get("data-repeat")
            if src:
                html_sources[src]
            if el.get("data-field"):
                owner = next((a.get("data-source") or a.get("data-repeat")
                              for a in el.ancestors()
                              if a.get("data-source") or a.get("data-repeat")), None)
                if owner:
                    html_sources[owner].add(el.get("data-field"))
            if el.get("data-action"):
                html_actions.update(el.get("data-action").split())
        map_sources: dict[str, set[str]] = defaultdict(set)
        for d in entry.get("data") or []:
            if isinstance(d, dict) and d.get("source"):
                map_sources[d["source"]] |= set(d.get("fields") or [])
        name = sf.path.name
        for src in sorted(set(html_sources) ^ set(map_sources)):
            where = "the HTML" if src in html_sources else "sitemap.json"
            self.add("sitemap-data", WARNING,
                     f"Data source {src} appears on {sf.screen} only in {where}.", name)
        for src in sorted(set(html_sources) & set(map_sources)):
            extra = html_sources[src] - map_sources[src]
            if extra:
                self.add("sitemap-data", WARNING,
                         f"{sf.screen} shows {src} fields {sorted(extra)} that sitemap.json "
                         "does not list.", name)
        map_actions = {a.get("id") for a in entry.get("actions") or [] if isinstance(a, dict)}
        for act in sorted(html_actions ^ map_actions):
            where = "the HTML" if act in html_actions else "sitemap.json"
            self.add("sitemap-actions", WARNING,
                     f"Action {act} appears on {sf.screen} only in {where}.", name)

    def check_index(self):
        index = self.screens.get("index.html")
        if index is None:
            self.add("index-missing", WARNING, "There is no index.html screen map.")
            return
        linked = set()
        for el in index.page.elements():
            if el.tag == "a" and el.get("href"):
                target = self.local_target(index, el.get("href"))
                if target is not None:
                    linked.add(target.name)
        for file_name in sorted(self.screens):
            if file_name != "index.html" and file_name not in linked:
                self.add("index-missing", WARNING,
                         f"index.html does not link {file_name}.", "index.html")

    # ------------------------------------------------------------------ design

    def check_design(self):
        try:
            spec = importlib.util.spec_from_file_location("tokens_to_css", TOKENS_SCRIPT)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            fm = mod.front_matter(self.design.read_text(encoding="utf-8-sig"))
        except ImportError as exc:
            self.degraded.append(f"--design needs PyYAML ({exc}); token-drift did not run.")
            return
        except OSError as exc:
            self.degraded.append(f"--design could not be read ({exc}); token-drift did "
                                 "not run.")
            return
        except Exception as exc:  # TokenError and anything the DESIGN.md triggers
            self.degraded.append(f"--design is not usable ({exc}); token-drift did not run.")
            return
        canvas = (self.sitemap or {}).get("canvas") or {}
        size = (canvas.get("width", 1366), canvas.get("height", 768))
        expected = mod.as_map(fm, self.target, size)

        def norm(v: str) -> str:
            return re.sub(r"\s+", " ", v.strip().lower().replace("'", '"'))

        for name, sf in sorted(self.screens.items()):
            if name == "index.html":
                continue
            missing = sorted(set(expected) - set(sf.root))
            if missing:
                self.add("token-drift", WARNING,
                         f":root lacks {len(missing)} token(s) from the DESIGN.md: "
                         f"{', '.join(missing[:6])}{' ...' if len(missing) > 6 else ''}.",
                         name, detail="Regenerate the block with tokens_to_css.py.")
            for var in sorted(set(expected) & set(sf.root)):
                if norm(expected[var]) != norm(sf.root[var]):
                    self.add("token-drift", WARNING,
                             f"{var} is {sf.root[var]} here but {expected[var]} in the "
                             "DESIGN.md.", name)


# --------------------------------------------------------------------------- driver


def lint_folder(folder: Path, target: str | None = None, design: Path | None = None,
                profile: Path = DEFAULT_PROFILE) -> dict:
    linter = Linter(folder, target, design, profile)
    linter.run()
    findings = linter.findings
    errors = sum(1 for f in findings if f.severity == ERROR)
    warnings = sum(1 for f in findings if f.severity == WARNING)
    degraded = " ".join(linter.degraded) or None
    if errors:
        code, verdict = "will_fail", f"VERDICT: WILL FAIL — {errors} error(s) to fix"
    elif degraded:
        suffix = f", {warnings} warning(s)" if warnings else ""
        code, verdict = "unproven", f"VERDICT: UNPROVEN — some checks did not run{suffix}"
    elif warnings:
        code, verdict = "unverified", f"VERDICT: USABLE, WITH {warnings} WARNING(S) TO REVIEW"
    else:
        code, verdict = "safe", "VERDICT: CLEAN"
    findings.sort(key=lambda f: (0 if f.severity == ERROR else 1, f.file or "",
                                 f.line or 0, f.check))
    screens = sorted(sf.screen for n, sf in linter.screens.items()
                     if n != "index.html" and sf.screen)
    return {"path": folder.as_posix(), "target": linter.target, "screens": screens,
            "findings": [f.as_dict() for f in findings], "errors": errors,
            "warnings": warnings, "verdict": verdict, "verdict_code": code,
            "degraded": degraded}


def render(report: dict, quiet=False) -> str:
    out = []
    if not quiet:
        out += ["=" * 72,
                f"{report['path']}  (target: {report['target']}, "
                f"{len(report['screens'])} screen(s))", "=" * 72]
        if report["degraded"]:
            out += [f"  NOTE: {report['degraded']}", ""]
        for sev, title in ((ERROR, "Errors"), (WARNING, "Warnings")):
            group = [f for f in report["findings"] if f["severity"] == sev]
            if not group:
                continue
            out += [title, "-" * 72]
            for f in group:
                out.append(f"  [{sev.upper()}] {f['check']}")
                out.append(f"    {f['message']}")
                where = f["file"] or ""
                if f["line"]:
                    where += f" line {f['line']}"
                if where:
                    out.append(f"    at: {where.strip()}")
                if f["detail"]:
                    out.append(f"    {f['detail']}")
                out.append("")
        if not report["findings"]:
            out += ["  No findings.", ""]
    out.append(report["verdict"])
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="mock_lint.py",
        description="Check a mock-ui mockup folder offline and end with a verdict.")
    parser.add_argument("folder", type=Path, help="the mockup folder (holds sitemap.json)")
    parser.add_argument("--target", choices=("web", "power-apps"),
                        help="override the target sitemap.json declares")
    parser.add_argument("--design", type=Path,
                        help="the DESIGN.md the :root block was generated from")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE,
                        help="Power Apps profile (default: the copy in this skill)")
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
    if not args.folder.is_dir():
        print(f"ERROR: not a folder: {args.folder}", file=sys.stderr)
        return 2
    if args.design is not None and not args.design.is_file():
        print(f"ERROR: no such file: {args.design}", file=sys.stderr)
        return 2

    report = lint_folder(args.folder, args.target, args.design, args.profile)
    if report["errors"]:
        code = 1
    elif (report["warnings"] or report["degraded"]) and args.strict:
        code = 2
    else:
        code = 0
    if args.json:
        print(json.dumps({"version": 1, "report": report, "exit_code": code},
                         indent=2, ensure_ascii=False))
    else:
        print(render(report, quiet=args.quiet))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
