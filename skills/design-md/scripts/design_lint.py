#!/usr/bin/env python3
"""Offline linter for a DESIGN.md design system, ending in a verdict.

    python3 scripts/design_lint.py DESIGN.md [DESIGN.md ...]
                                   [--target web|power-apps] [--profile PATH]
                                   [--json] [--strict] [--quiet]

Checks the format Google published for Stitch (docs/spec.md in
github.com/google-labs-code/design.md, version `alpha`) as this skill writes it: every
token in YAML front matter, eight canonical `##` sections followed by three extension
sections. Each finding has a stable check id; tests assert on ids, never on wording.

ERRORS (the file is wrong; fix before handing it over)
  frontmatter-missing   no `---` front matter at the top
  yaml-parse            front matter is not valid YAML, or not a mapping
  duplicate-key         a YAML key appears twice in the same mapping
  unknown-key           a top-level key the format does not define
  version               `version` missing or not `alpha`
  name-missing          `name` missing or empty
  primary-missing       no `colors.primary`
  group-shape           a token group, typography level or component is not a mapping
  color-invalid         a colour value that is not a CSS colour
  broken-ref            a `{path}` reference that resolves to nothing, or loops
  group-ref             outside `components`, a reference to a group, not a value
  ref-type              a component property resolves to the wrong kind of token
  typography-incomplete a typography level without fontFamily/fontSize/fontWeight/lineHeight
  typography-value      fontWeight not a number 1-1000, or fontFamily not a string
  dimension-unit        a dimension without px, em or rem
  section-order         `##` sections out of canonical order
  section-duplicate     the same `##` section twice
  contrast              component textColor on backgroundColor below 4.5:1

WARNINGS (review; fix, or say why it stands)
  key-order             top-level keys not in the order version..components
  section-missing       one of the eleven sections is absent
  typography-levels     fewer than 9 or more than 15 typography levels
  color-unparsed        a valid CSS colour form this script does not convert
  contrast-unmeasured   contrast could not be measured (transparent, alpha, unparsed)
  component-literal     a component colour written as a literal, not a reference
  component-prop        a component property outside the eight the spec lists
  typography-prop       a typography property outside the seven the spec lists
  orphaned-color        a colour token no component uses, directly or through a chain
  prose-hex             a hex value in the prose that equals no colour token
  prose-ref             a `{group.name}` reference in the prose that resolves to nothing
  prose-ref-singular    `{component.x}` in the prose; the YAML path is `components.x`
  yaml-block-in-body    a fenced yaml block in the body that defines token groups

With --target power-apps (reads references/shared/powerapps-profile.md):
  pa-effect             the design relies on an effect the profile rules out
  pa-unverified         the design relies on a property the profile marks unverified

Colours: hex (#RGB, #RGBA, #RRGGBB, #RRGGBBAA), rgb()/rgba(), hsl()/hsla() and the CSS
named colours are converted and measured. hwb(), lab(), lch(), oklab(), oklch() and
color-mix() are valid per the spec but not converted here: they raise color-unparsed
and their contrast is reported as unmeasured, never as passing.

Exit codes: 0 no errors | 1 any error | 2 warnings (or unproven) with --strict, or a
usage problem. Requires PyYAML.
"""

from __future__ import annotations

import argparse
import colorsys
import json
import math
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: PyYAML is not installed. Run: pip install pyyaml", file=sys.stderr)
    raise SystemExit(2)

SKILL_DIR = Path(__file__).resolve().parent.parent  # this skill's own folder
DEFAULT_PROFILE = SKILL_DIR / "references" / "shared" / "powerapps-profile.md"

ERROR, WARNING = "error", "warning"

# Top-level keys, in the order the collection writes them. `omitted` is in the spec but
# the collection never uses it; it is accepted and expected right after `description`.
KEY_ORDER = ("version", "name", "description", "omitted", "colors", "typography",
             "rounded", "spacing", "components")
TOKEN_GROUPS = ("colors", "typography", "rounded", "spacing", "components")

CANONICAL_SECTIONS = ("Overview", "Colors", "Typography", "Layout", "Elevation & Depth",
                      "Shapes", "Components", "Do's and Don'ts")
SECTION_ALIASES = {"Brand & Style": "Overview", "Layout & Spacing": "Layout",
                   "Elevation": "Elevation & Depth"}
EXTENSION_SECTIONS = ("Responsive Behavior", "Iteration Guide", "Known Gaps")
ALL_SECTIONS = CANONICAL_SECTIONS + EXTENSION_SECTIONS
SECTION_INDEX = {s: i for i, s in enumerate(ALL_SECTIONS)}

TYPO_REQUIRED = ("fontFamily", "fontSize", "fontWeight", "lineHeight")
TYPO_KNOWN = TYPO_REQUIRED + ("letterSpacing", "fontFeature", "fontVariation")
COMPONENT_COLOR_PROPS = ("backgroundColor", "textColor")
COMPONENT_DIM_PROPS = ("rounded", "padding", "size", "height", "width")
COMPONENT_PROPS = COMPONENT_COLOR_PROPS + ("typography",) + COMPONENT_DIM_PROPS
TYPO_LEVELS = (9, 15)
WCAG_AA = 4.5

REF_RE = re.compile(r"^\{([A-Za-z0-9_\-]+(?:\.[A-Za-z0-9_\-]+)+)\}$")
PROSE_REF_RE = re.compile(r"\{([A-Za-z]+)\.([A-Za-z0-9_\-]+(?:\.[A-Za-z0-9_\-]+)*)\}")
DIM_RE = re.compile(r"^-?(?:\d+\.?\d*|\.\d+)(?:px|em|rem)$")
NUM_RE = re.compile(r"^-?(?:\d+\.?\d*|\.\d+)$")
HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
PROSE_HEX_RE = re.compile(r"(?<![\w&/\]])(?<!\]\()#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])")
HEADING_RE = re.compile(r"^(#{2,3})\s+(.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)\s*([\w-]*)")
UNPARSED_FUNCS = ("hwb(", "lab(", "lch(", "oklab(", "oklch(", "color-mix(", "color(")

# CSS named colours (CSS Color Module Level 4), name -> RRGGBB.
_NAMED = (
    "aliceblue f0f8ff antiquewhite faebd7 aqua 00ffff aquamarine 7fffd4 azure f0ffff "
    "beige f5f5dc bisque ffe4c4 black 000000 blanchedalmond ffebcd blue 0000ff "
    "blueviolet 8a2be2 brown a52a2a burlywood deb887 cadetblue 5f9ea0 chartreuse 7fff00 "
    "chocolate d2691e coral ff7f50 cornflowerblue 6495ed cornsilk fff8dc crimson dc143c "
    "cyan 00ffff darkblue 00008b darkcyan 008b8b darkgoldenrod b8860b darkgray a9a9a9 "
    "darkgreen 006400 darkgrey a9a9a9 darkkhaki bdb76b darkmagenta 8b008b "
    "darkolivegreen 556b2f darkorange ff8c00 darkorchid 9932cc darkred 8b0000 "
    "darksalmon e9967a darkseagreen 8fbc8f darkslateblue 483d8b darkslategray 2f4f4f "
    "darkslategrey 2f4f4f darkturquoise 00ced1 darkviolet 9400d3 deeppink ff1493 "
    "deepskyblue 00bfff dimgray 696969 dimgrey 696969 dodgerblue 1e90ff firebrick b22222 "
    "floralwhite fffaf0 forestgreen 228b22 fuchsia ff00ff gainsboro dcdcdc "
    "ghostwhite f8f8ff gold ffd700 goldenrod daa520 gray 808080 green 008000 "
    "greenyellow adff2f grey 808080 honeydew f0fff0 hotpink ff69b4 indianred cd5c5c "
    "indigo 4b0082 ivory fffff0 khaki f0e68c lavender e6e6fa lavenderblush fff0f5 "
    "lawngreen 7cfc00 lemonchiffon fffacd lightblue add8e6 lightcoral f08080 "
    "lightcyan e0ffff lightgoldenrodyellow fafad2 lightgray d3d3d3 lightgreen 90ee90 "
    "lightgrey d3d3d3 lightpink ffb6c1 lightsalmon ffa07a lightseagreen 20b2aa "
    "lightskyblue 87cefa lightslategray 778899 lightslategrey 778899 lightsteelblue b0c4de "
    "lightyellow ffffe0 lime 00ff00 limegreen 32cd32 linen faf0e6 magenta ff00ff "
    "maroon 800000 mediumaquamarine 66cdaa mediumblue 0000cd mediumorchid ba55d3 "
    "mediumpurple 9370db mediumseagreen 3cb371 mediumslateblue 7b68ee "
    "mediumspringgreen 00fa9a mediumturquoise 48d1cc mediumvioletred c71585 "
    "midnightblue 191970 mintcream f5fffa mistyrose ffe4e1 moccasin ffe4b5 "
    "navajowhite ffdead navy 000080 oldlace fdf5e6 olive 808000 olivedrab 6b8e23 "
    "orange ffa500 orangered ff4500 orchid da70d6 palegoldenrod eee8aa palegreen 98fb98 "
    "paleturquoise afeeee palevioletred db7093 papayawhip ffefd5 peachpuff ffdab9 "
    "peru cd853f pink ffc0cb plum dda0dd powderblue b0e0e6 purple 800080 "
    "rebeccapurple 663399 red ff0000 rosybrown bc8f8f royalblue 4169e1 "
    "saddlebrown 8b4513 salmon fa8072 sandybrown f4a460 seagreen 2e8b57 seashell fff5ee "
    "sienna a0522d silver c0c0c0 skyblue 87ceeb slateblue 6a5acd slategray 708090 "
    "slategrey 708090 snow fffafa springgreen 00ff7f steelblue 4682b4 tan d2b48c "
    "teal 008080 thistle d8bfd8 tomato ff6347 turquoise 40e0d0 violet ee82ee "
    "wheat f5deb3 white ffffff whitesmoke f5f5f5 yellow ffff00 yellowgreen 9acd32"
).split()
NAMED_COLORS = {_NAMED[i]: _NAMED[i + 1] for i in range(0, len(_NAMED), 2)}

# Under --target power-apps: what in the prose reveals each effect the profile rules
# out. Keyed by the catalog's impossible_css id; a detector only runs when the profile
# names its id, so the profile -- derived from the catalog -- stays the authority.
# `non-segoe-font` is checked on typography tokens instead of prose.
PA_DETECTORS = {
    "box-shadow": re.compile(r"\bbox-shadow\b|\bdrop[- ]shadows?\b|\bshadows?\b", re.I),
    "backdrop-blur": re.compile(r"\bbackdrop(?:-filter)?\b|\bblur(?:red|s)?\b|\bfrosted\b|"
                                r"\bglassmorphism\b", re.I),
    "css-transition": re.compile(r"\btransitions?\b|\banimations?\b|\banimated\b|"
                                 r"\bkeyframes?\b|\bfade[- ](?:in|out)\b", re.I),
    "group-hover": re.compile(r"\bgroup-hover\b|\bparent (?:is )?hovered\b|"
                              r"\bwhen the (?:card|row|tile|container|parent) is hovered\b|"
                              r"\bon (?:card|row|tile|container) hover\b", re.I),
    "border-left-only": re.compile(r"\bborder-(?:left|right|top|bottom)\b|"
                                   r"\b(?:left|right|top|bottom)[- ]border\b|"
                                   r"\b(?:left|right|top|bottom)[- ]edge (?:accent|stripe|bar)\b",
                                   re.I),
}
PROFILE_ID_RE = re.compile(r"impossible_css\[id=([a-z0-9-]+)\]")


# --------------------------------------------------------------------------- findings


class Finding:
    __slots__ = ("check", "severity", "message", "path", "line", "detail")

    def __init__(self, check, severity, message, path=None, line=None, detail=None):
        self.check = check
        self.severity = severity
        self.message = message
        self.path = path
        self.line = line
        self.detail = detail

    def as_dict(self):
        return {"check": self.check, "severity": self.severity, "message": self.message,
                "path": self.path, "line": self.line, "detail": self.detail}


# --------------------------------------------------------------------------- colours


def parse_color(value) -> tuple[float, float, float, float] | str | None:
    """(r, g, b, a) in 0..1, the string "unparsed" for a valid form not converted here,
    or None when the value is not a CSS colour."""
    if not isinstance(value, str):
        return None
    s = value.strip().lower()
    if HEX_RE.match(s):
        h = s[1:]
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)
    if s == "transparent":
        return (0.0, 0.0, 0.0, 0.0)
    if s in NAMED_COLORS:
        return parse_color("#" + NAMED_COLORS[s])
    m = re.match(r"^(rgba?|hsla?)\((.*)\)$", s)
    if m:
        return _parse_func(m.group(1), m.group(2))
    if s.startswith(UNPARSED_FUNCS) and s.endswith(")"):
        return "unparsed"
    return None


def _parse_func(fn: str, args: str):
    alpha_part = None
    if "/" in args:
        args, alpha_part = args.split("/", 1)
        parts = [p for p in re.split(r"[\s,]+", args.strip()) if p]
    else:
        parts = [p for p in re.split(r"[\s,]+", args.strip()) if p]
        if len(parts) == 4:
            alpha_part = parts.pop()
    if len(parts) != 3:
        return None
    try:
        a = _num_or_pct(alpha_part.strip(), 1.0) if alpha_part is not None else 1.0
        if fn.startswith("rgb"):
            r, g, b = (_num_or_pct(p, 255.0) for p in parts)
            vals = (r / 255, g / 255, b / 255)
        else:
            h = _hue(parts[0])
            sat = _num_or_pct(parts[1], 100.0) / 100
            light = _num_or_pct(parts[2], 100.0) / 100
            vals = colorsys.hls_to_rgb(h, light, sat)
    except ValueError:
        return None
    if not all(0 <= v <= 1.0001 for v in vals) or not 0 <= a <= 1.0001:
        return None
    return (min(vals[0], 1.0), min(vals[1], 1.0), min(vals[2], 1.0), min(a, 1.0))


def _num_or_pct(text: str, scale: float) -> float:
    """A number, or a percentage of `scale`."""
    if text.endswith("%"):
        return float(text[:-1]) / 100 * scale
    return float(text)


def _hue(text: str) -> float:
    for unit, per_turn in (("deg", 360.0), ("grad", 400.0), ("rad", 2 * math.pi),
                           ("turn", 1.0)):
        if text.endswith(unit):
            return (float(text[: -len(unit)]) / per_turn) % 1.0
    return (float(text) / 360.0) % 1.0


def _luminance(rgb) -> float:
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg, bg) -> float:
    """WCAG 2.x contrast. A translucent foreground is composited over an opaque bg."""
    a = fg[3]
    fg_rgb = tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3))
    l1, l2 = _luminance(fg_rgb), _luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def to_hex(rgba) -> str:
    r, g, b, a = (round(c * 255) for c in rgba)
    return f"#{r:02x}{g:02x}{b:02x}" + ("" if a == 255 else f"{a:02x}")


def is_dimension(value, allow_number=False) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        # Unitless zero is a valid CSS length; any other bare number needs a unit,
        # except where the spec allows a number (spacing, lineHeight).
        return allow_number or value == 0
    if isinstance(value, str):
        s = value.strip()
        return bool(DIM_RE.match(s)) or s == "0" or (allow_number and bool(NUM_RE.match(s)))
    return False


def is_padding(value) -> bool:
    """One to four dimensions, CSS shorthand order."""
    if not isinstance(value, str):
        return is_dimension(value)
    parts = value.split()
    return 1 <= len(parts) <= 4 and all(is_dimension(p) for p in parts)


# --------------------------------------------------------------------------- document


class Document:
    """A DESIGN.md split into front matter (with line numbers) and body."""

    def __init__(self, text: str):
        self.text = text.replace("\r\n", "\n")
        self.lines = self.text.split("\n")
        self.fm_text = None
        self.fm_start = 0          # 1-based line of the first front-matter content line
        self.body_start = 1        # 1-based line where the body starts
        if self.lines and self.lines[0].strip() == "---":
            for i in range(1, len(self.lines)):
                if self.lines[i].strip() == "---":
                    self.fm_text = "\n".join(self.lines[1:i])
                    self.fm_start = 2
                    self.body_start = i + 2
                    break

    def body_lines(self):
        """(line_no, text, in_fence, fence_lang) for every body line."""
        in_fence, lang = False, ""
        for idx in range(self.body_start - 1, len(self.lines)):
            line = self.lines[idx]
            m = FENCE_RE.match(line)
            if m:
                if not in_fence:
                    in_fence, lang = True, m.group(2).lower()
                    yield idx + 1, line, True, lang
                    continue
                yield idx + 1, line, True, lang
                in_fence, lang = False, ""
                continue
            yield idx + 1, line, in_fence, lang


def _compose_index(node, offset: int, prefix: str, lines: dict, dups: list):
    """Walk a composed YAML node: record path -> line, and duplicate keys."""
    if isinstance(node, yaml.MappingNode):
        seen = set()
        for key_node, value_node in node.value:
            key = str(key_node.value)
            path = f"{prefix}.{key}" if prefix else key
            line = key_node.start_mark.line + offset
            if key in seen:
                dups.append((path, line))
            seen.add(key)
            lines.setdefault(path, line)
            _compose_index(value_node, offset, path, lines, dups)
    elif isinstance(node, yaml.SequenceNode):
        for i, item in enumerate(node.value):
            _compose_index(item, offset, f"{prefix}[{i}]", lines, dups)


# --------------------------------------------------------------------------- linting


class Linter:
    def __init__(self, doc: Document, target: str, profile_ids: set[str] | None):
        self.doc = doc
        self.target = target
        self.profile_ids = profile_ids
        self.findings: list[Finding] = []
        self.lines: dict[str, int] = {}
        self.data: dict = {}
        self.symbols: dict[str, object] = {}
        self.used_colors: set[str] = set()
        # Token paths already reported as invalid where they are defined. A component
        # that references one is not reported again: one defect, one finding.
        self.bad_paths: set[str] = set()
        self.last_path: str | None = None

    # -- helpers
    def add(self, check, severity, message, path=None, detail=None, line=None):
        if severity == ERROR and path is not None:
            self.bad_paths.add(path)
        if line is None and path is not None:
            line = self.lines.get(path)
        self.findings.append(Finding(check, severity, message, path, line, detail))

    def resolve(self, ref_path: str, record_colors=False):
        """('value', v) | ('group', v) | ('missing', None) | ('circular', None)."""
        seen = set()
        path = ref_path
        while True:
            if path in seen or len(seen) > 20:
                return "circular", None
            seen.add(path)
            if record_colors and path.startswith("colors."):
                self.used_colors.add(path[len("colors."):])
            self.last_path = path
            if path not in self.symbols:
                return "missing", None
            value = self.symbols[path]
            if isinstance(value, dict):
                return "group", value
            if isinstance(value, str):
                m = REF_RE.match(value.strip())
                if m:
                    path = m.group(1)
                    continue
            return "value", value

    # -- layers
    def run(self):
        tokens_ok = self.front_matter()
        if tokens_ok:
            self.tokens()
        self.sections()
        if tokens_ok:
            self.prose()
            if self.target == "power-apps":
                self.power_apps()

    def front_matter(self) -> bool:
        doc = self.doc
        if doc.fm_text is None:
            self.add("frontmatter-missing", ERROR,
                     "No YAML front matter. The file must start with a line `---`, the "
                     "tokens, and a closing `---`.", line=1)
            return False
        try:
            node = yaml.compose(doc.fm_text, Loader=yaml.SafeLoader)
            data = yaml.safe_load(doc.fm_text)
        except yaml.YAMLError as exc:
            mark = getattr(exc, "problem_mark", None)
            line = mark.line + doc.fm_start if mark is not None else doc.fm_start
            self.add("yaml-parse", ERROR, "Front matter is not valid YAML.",
                     detail=str(exc).splitlines()[0] if str(exc) else None, line=line)
            return False
        if not isinstance(data, dict):
            self.add("yaml-parse", ERROR, "Front matter must be a YAML mapping of keys.",
                     line=doc.fm_start)
            return False
        dups: list = []
        _compose_index(node, doc.fm_start, "", self.lines, dups)
        for path, line in dups:
            self.add("duplicate-key", ERROR,
                     f"Key '{path}' is defined twice; YAML keeps only the last one, so "
                     "the first is silently lost.", path=path, line=line)
        self.data = data

        for key in data:
            if key not in KEY_ORDER:
                self.add("unknown-key", ERROR,
                         f"Top-level key '{key}' is not part of the format. Allowed: "
                         f"{', '.join(KEY_ORDER)}.", path=str(key))
        present = [k for k in data if k in KEY_ORDER]
        expected = [k for k in KEY_ORDER if k in data]
        if present != expected:
            self.add("key-order", WARNING,
                     "Top-level keys are not in the usual order.",
                     detail=f"got {', '.join(present)}; expected {', '.join(expected)}",
                     line=doc.fm_start)
        if data.get("version") != "alpha":
            self.add("version", ERROR,
                     f"`version` must be `alpha` (got {data.get('version')!r}).",
                     path="version" if "version" in data else None, line=doc.fm_start
                     if "version" not in data else None)
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            self.add("name-missing", ERROR, "`name` is missing or empty.",
                     path="name" if "name" in data else None,
                     line=None if "name" in data else doc.fm_start)
        return True

    def tokens(self):
        data = self.data
        groups = {}
        for g in TOKEN_GROUPS:
            if g not in data or data[g] is None:
                groups[g] = {}
                continue
            if not isinstance(data[g], dict):
                self.add("group-shape", ERROR, f"`{g}` must be a mapping of token names.",
                         path=g)
                groups[g] = {}
                continue
            groups[g] = data[g]

        # symbol table: primitives and typography groups; components are not in it
        for g in ("colors", "rounded", "spacing"):
            for name, value in groups[g].items():
                if isinstance(value, dict):
                    self.add("group-shape", ERROR,
                             f"`{g}.{name}` is a nested group; this format wants one value "
                             "per token.", path=f"{g}.{name}")
                    continue
                self.symbols[f"{g}.{name}"] = value
        for name, level in groups["typography"].items():
            if not isinstance(level, dict):
                self.add("group-shape", ERROR,
                         f"`typography.{name}` must be a mapping of font properties.",
                         path=f"typography.{name}")
                continue
            self.symbols[f"typography.{name}"] = level
            for prop, value in level.items():
                self.symbols[f"typography.{name}.{prop}"] = value

        if "primary" not in groups["colors"]:
            self.add("primary-missing", ERROR,
                     "No `colors.primary`. The format expects one primary colour.",
                     path="colors" if "colors" in data else None,
                     line=None if "colors" in data else self.doc.fm_start)

        self.check_colors(groups["colors"])
        self.check_typography(groups["typography"])
        for g in ("rounded", "spacing"):
            for name, value in groups[g].items():
                if isinstance(value, dict):
                    continue
                path = f"{g}.{name}"
                value = self.deref_primitive(path, value)
                if value is _SKIP:
                    continue
                if not is_dimension(value, allow_number=(g == "spacing")):
                    self.add("dimension-unit", ERROR,
                             f"`{path}` is {value!r}; a dimension needs px, em or rem"
                             + (" (spacing may also be a plain number)." if g == "spacing"
                                else "."), path=path)
        self.check_components(groups["components"])

        n = len([v for v in groups["typography"].values() if isinstance(v, dict)])
        if n and not TYPO_LEVELS[0] <= n <= TYPO_LEVELS[1]:
            self.add("typography-levels", WARNING,
                     f"{n} typography levels; most design systems have "
                     f"{TYPO_LEVELS[0]}-{TYPO_LEVELS[1]}.", path="typography")

        for name in groups["colors"]:
            if name not in self.used_colors:
                self.add("orphaned-color", WARNING,
                         f"`colors.{name}` is not used by any component.",
                         path=f"colors.{name}",
                         detail="Use it in a component, or say in the prose where it applies "
                                "and why no component carries it.")

    def deref_primitive(self, path, value):
        """For a token outside components: follow a reference to a primitive value.
        Returns the value, or _SKIP after reporting a broken or group reference."""
        if isinstance(value, str) and REF_RE.match(value.strip()):
            kind, resolved = self.resolve(REF_RE.match(value.strip()).group(1))
            if kind in ("missing", "circular"):
                self.add("broken-ref", ERROR,
                         f"`{path}` references {value}, which "
                         + ("does not exist." if kind == "missing" else "loops back on itself."),
                         path=path)
                return _SKIP
            if kind == "group":
                self.add("group-ref", ERROR,
                         f"`{path}` references {value}, a group. Outside `components` a "
                         "reference must point at a single value.", path=path)
                return _SKIP
            return resolved
        return value

    def check_colors(self, colors):
        for name, value in colors.items():
            if isinstance(value, dict):
                continue
            path = f"colors.{name}"
            value = self.deref_primitive(path, value)
            if value is _SKIP:
                continue
            parsed = parse_color(value)
            if parsed is None:
                self.add("color-invalid", ERROR, f"`{path}` is {value!r}, not a CSS colour.",
                         path=path)
            elif parsed == "unparsed":
                self.add("color-unparsed", WARNING,
                         f"`{path}` is {value!r}: valid per the spec, but this script does "
                         "not convert it, so contrast involving it is not measured.",
                         path=path)

    def check_typography(self, typography):
        for name, level in typography.items():
            if not isinstance(level, dict):
                continue
            base = f"typography.{name}"
            missing = [p for p in TYPO_REQUIRED if p not in level]
            if missing:
                self.add("typography-incomplete", ERROR,
                         f"`{base}` lacks {', '.join(missing)}.", path=base)
            for prop, raw in level.items():
                path = f"{base}.{prop}"
                if prop not in TYPO_KNOWN:
                    self.add("typography-prop", WARNING,
                             f"`{path}` is not a typography property the spec lists "
                             f"({', '.join(TYPO_KNOWN)}).", path=path)
                    continue
                value = self.deref_primitive(path, raw)
                if value is _SKIP:
                    continue
                if prop == "fontFamily":
                    if not isinstance(value, str) or not value.strip():
                        self.add("typography-value", ERROR,
                                 f"`{path}` must be a font family name or stack.", path=path)
                elif prop == "fontWeight":
                    ok = False
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        ok = 1 <= value <= 1000
                    elif isinstance(value, str) and NUM_RE.match(value.strip()):
                        ok = 1 <= float(value) <= 1000
                    if not ok:
                        self.add("typography-value", ERROR,
                                 f"`{path}` is {value!r}; fontWeight is a number 1-1000.",
                                 path=path)
                elif prop in ("fontSize", "letterSpacing"):
                    if not is_dimension(value):
                        self.add("dimension-unit", ERROR,
                                 f"`{path}` is {value!r}; a dimension needs px, em or rem.",
                                 path=path)
                elif prop == "lineHeight":
                    if not is_dimension(value, allow_number=True):
                        self.add("dimension-unit", ERROR,
                                 f"`{path}` is {value!r}; lineHeight is a number or a "
                                 "dimension in px, em or rem.", path=path)

    def check_components(self, components):
        for comp, props in components.items():
            base = f"components.{comp}"
            if not isinstance(props, dict):
                self.add("group-shape", ERROR,
                         f"`{base}` must be a mapping of properties.", path=base)
                continue
            colors: dict[str, object] = {}
            for prop, raw in props.items():
                path = f"{base}.{prop}"
                if prop not in COMPONENT_PROPS:
                    self.add("component-prop", WARNING,
                             f"`{path}` is not one of the eight component properties the "
                             "spec lists; consumers accept it with a warning.", path=path)
                    if isinstance(raw, str) and REF_RE.match(raw.strip()):
                        kind, _ = self.resolve(REF_RE.match(raw.strip()).group(1),
                                               record_colors=True)
                        if kind in ("missing", "circular"):
                            self.add("broken-ref", ERROR,
                                     f"`{path}` references {raw}, which does not resolve.",
                                     path=path)
                    continue
                is_ref = isinstance(raw, str) and REF_RE.match(raw.strip())
                if is_ref:
                    target = is_ref.group(1)
                    kind, value = self.resolve(target, record_colors=True)
                    if kind in ("missing", "circular"):
                        hint = ""
                        if target.split(".")[0] in ("component", "components"):
                            hint = " Components cannot reference other components."
                        self.add("broken-ref", ERROR,
                                 f"`{path}` references {raw}, which "
                                 + ("does not exist." if kind == "missing"
                                    else "loops back on itself.") + hint, path=path)
                        continue
                    if prop == "typography":
                        if kind != "group" or not target.startswith("typography."):
                            self.add("ref-type", ERROR,
                                     f"`{path}` must reference a typography level, "
                                     f"got {raw}.", path=path)
                        continue
                    if kind == "group":
                        self.add("ref-type", ERROR,
                                 f"`{path}` references the group {raw}; it needs a single "
                                 "value.", path=path)
                        continue
                    if self.last_path in self.bad_paths:
                        continue  # already reported where the token is defined
                else:
                    value = raw
                    if prop == "typography":
                        self.add("ref-type", ERROR,
                                 f"`{path}` must be a reference such as "
                                 "\"{typography.body-md}\".", path=path)
                        continue

                if prop in COMPONENT_COLOR_PROPS:
                    parsed = parse_color(value)
                    if parsed is None:
                        check = "ref-type" if is_ref else "color-invalid"
                        self.add(check, ERROR, f"`{path}` is {value!r}, not a colour.",
                                 path=path)
                        continue
                    if not is_ref and str(value).strip().lower() != "transparent":
                        self.add("component-literal", WARNING,
                                 f"`{path}` is the literal {value!r}; reference a colour "
                                 "token instead.", path=path)
                    colors[prop] = parsed
                else:  # dimension properties
                    ok = is_padding(value) if prop == "padding" else is_dimension(value)
                    if not ok:
                        check = "ref-type" if is_ref else "dimension-unit"
                        self.add(check, ERROR,
                                 f"`{path}` is {value!r}; it needs a dimension in px, em "
                                 "or rem.", path=path)

            if len(colors) == 2:
                self.check_contrast(base, colors["textColor"], colors["backgroundColor"])

    def check_contrast(self, base, fg, bg):
        if fg == "unparsed" or bg == "unparsed":
            self.add("contrast-unmeasured", WARNING,
                     f"`{base}`: contrast not measured; a colour uses a form this script "
                     "does not convert.", path=base)
            return
        if bg[3] < 1:
            self.add("contrast-unmeasured", WARNING,
                     f"`{base}`: backgroundColor {to_hex(bg)} is not opaque, so the real "
                     "background is whatever sits behind it. Check the text against each "
                     "surface it is used on.", path=base)
            return
        ratio = contrast_ratio(fg, bg)
        if ratio < WCAG_AA:
            self.add("contrast", ERROR,
                     f"`{base}`: text {to_hex(fg)} on {to_hex(bg)} is {ratio:.2f}:1, below "
                     f"WCAG AA {WCAG_AA}:1.", path=base)

    # -- body
    def sections(self):
        seen: dict[str, int] = {}
        last_idx, last_name = -1, None
        for line_no, text, in_fence, _ in self.doc.body_lines():
            if in_fence:
                continue
            m = HEADING_RE.match(text)
            if not m or m.group(1) != "##":
                continue
            raw = m.group(2).replace("’", "'").strip()
            name = SECTION_ALIASES.get(raw, raw)
            if name not in SECTION_INDEX:
                continue  # unknown sections are preserved and ignored
            if name in seen:
                self.add("section-duplicate", ERROR,
                         f"`## {raw}` appears again (first at line {seen[name]}).",
                         line=line_no)
                continue
            seen[name] = line_no
            idx = SECTION_INDEX[name]
            if idx < last_idx:
                self.add("section-order", ERROR,
                         f"`## {raw}` comes after `## {last_name}`. Order: "
                         f"{', '.join(ALL_SECTIONS)}.", line=line_no)
            else:
                last_idx, last_name = idx, raw
        missing = [s for s in ALL_SECTIONS if s not in seen]
        if missing:
            self.add("section-missing", WARNING,
                     f"Missing section(s): {', '.join(missing)}. Write all eleven; say "
                     "\"not applicable\" in one that has nothing to hold.")

    def section_of_lines(self):
        """line_no -> (section, subsection) for every body line outside a fence."""
        out = {}
        section = sub = None
        for line_no, text, in_fence, _ in self.doc.body_lines():
            if not in_fence:
                m = HEADING_RE.match(text)
                if m:
                    title = m.group(2).replace("’", "'").strip()
                    if m.group(1) == "##":
                        section, sub = SECTION_ALIASES.get(title, title), None
                    else:
                        sub = title
            out[line_no] = (section, sub, in_fence)
        return out

    def prose(self):
        token_hex = set()
        for name in (self.data.get("colors") or {}):
            kind, value = self.resolve(f"colors.{name}")
            parsed = parse_color(value) if kind == "value" else None
            if isinstance(parsed, tuple):
                token_hex.add(to_hex(parsed))
        hex_seen, ref_seen, singular_seen = set(), set(), set()
        yaml_blocks: list[tuple[int, list[str]]] = []
        current: list[str] | None = None
        for line_no, text, in_fence, lang in self.doc.body_lines():
            if in_fence:
                if lang in ("yaml", "yml"):
                    if FENCE_RE.match(text) and current is None:
                        current = []
                        yaml_blocks.append((line_no, current))
                    elif FENCE_RE.match(text):
                        current = None
                    elif current is not None:
                        current.append(text)
                continue
            for m in PROSE_HEX_RE.finditer(text):
                h = to_hex(parse_color("#" + m.group(1)))
                if h not in token_hex and h not in hex_seen:
                    hex_seen.add(h)
                    self.add("prose-hex", WARNING,
                             f"#{m.group(1)} in the prose matches no colour token.",
                             line=line_no,
                             detail="Every colour in the prose must be a token. Add it, or "
                                    "use the token's value.")
            for m in PROSE_REF_RE.finditer(text):
                group, rest = m.group(1), m.group(2)
                ref = m.group(0)
                if group == "component":
                    if ref not in singular_seen:
                        singular_seen.add(ref)
                        known = rest.split(".")[0] in (self.data.get("components") or {})
                        self.add("prose-ref-singular", WARNING,
                                 f"{ref}: the YAML path is `components.{rest}`; write "
                                 f"{{components.{rest}}}."
                                 + ("" if known else f" No component `{rest}` exists either."),
                                 line=line_no)
                    continue
                if group == "components":
                    ok = rest.split(".")[0] in (self.data.get("components") or {})
                elif group in ("colors", "typography", "rounded", "spacing"):
                    ok = self.resolve(f"{group}.{rest}")[0] in ("value", "group")
                else:
                    continue  # not a token reference (e.g. {path.to.token} as an example)
                if not ok and ref not in ref_seen:
                    ref_seen.add(ref)
                    self.add("prose-ref", WARNING,
                             f"{ref} in the prose does not resolve to a token.", line=line_no)
        for line_no, block in yaml_blocks:
            try:
                parsed = yaml.safe_load("\n".join(block))
            except yaml.YAMLError:
                continue
            if isinstance(parsed, dict) and any(k in KEY_ORDER for k in parsed):
                self.add("yaml-block-in-body", WARNING,
                         "A fenced yaml block in the body defines token keys. The spec "
                         "merges such blocks, but this skill keeps every token in the "
                         "front matter; move them there.", line=line_no)

    def power_apps(self):
        ids = self.profile_ids or set()
        where = self.section_of_lines()
        hits: dict[str, list[int]] = {}
        for line_no, text, in_fence, _ in self.doc.body_lines():
            section, sub, fenced = where.get(line_no, (None, None, False))
            if fenced or section == "Known Gaps":
                continue  # Known Gaps is where a ruled-out effect is declared
            if sub and sub.lower().startswith("don"):
                continue  # a Don't list names effects in order to forbid them
            stripped = text.lstrip("-* ").lower()
            if stripped.startswith(("don't", "don’t", "never", "avoid", "no ")):
                continue
            for eid, rx in PA_DETECTORS.items():
                if eid in ids and rx.search(text):
                    hits.setdefault(eid, []).append(line_no)
        for eid, lines in hits.items():
            self.add("pa-effect", WARNING,
                     f"The prose relies on `{eid}`, which the Power Apps profile rules out "
                     f"(line(s) {', '.join(map(str, lines[:6]))}).",
                     line=lines[0],
                     detail="Under the power-apps target, replace it with the profile's "
                            "substitute and record it in ## Known Gaps.")
        if "non-segoe-font" in ids:
            faces: dict[str, list[str]] = {}
            for name, level in (self.data.get("typography") or {}).items():
                if not isinstance(level, dict):
                    continue
                fam = level.get("fontFamily")
                first = str(fam).split(",")[0].strip().strip("'\"") if fam else ""
                if first and first.lower() != "segoe ui":
                    faces.setdefault(first, []).append(name)
            for face, levels in faces.items():
                self.add("pa-effect", WARNING,
                         f"{len(levels)} typography level(s) start with {face!r} "
                         f"({', '.join(levels[:4])}{', ...' if len(levels) > 4 else ''}); "
                         "the profile marks any font other than Segoe UI as unverified "
                         "(non-segoe-font).", path=f"typography.{levels[0]}.fontFamily")
        spaced = [n for n, lv in (self.data.get("typography") or {}).items()
                  if isinstance(lv, dict) and lv.get("letterSpacing") not in (None, 0, "0",
                                                                             "0px", "0em",
                                                                             "0rem")]
        if spaced:
            self.add("pa-unverified", WARNING,
                     f"letterSpacing is set on {', '.join(spaced[:6])}"
                     + (" and more" if len(spaced) > 6 else "")
                     + "; the profile has no catalogued property for it.",
                     path="typography")


_SKIP = object()


# --------------------------------------------------------------------------- driver


def load_profile_ids(path: Path) -> set[str] | None:
    try:
        return set(PROFILE_ID_RE.findall(path.read_text(encoding="utf-8")))
    except OSError:
        return None


def lint_file(path: Path, target: str, profile_ids: set[str] | None) -> dict:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = None
    degraded = None
    if text is None:
        findings = [Finding("yaml-parse", ERROR, "The file is not UTF-8 text.")]
    else:
        linter = Linter(Document(text), target, profile_ids)
        linter.run()
        findings = linter.findings
    if target == "power-apps" and not profile_ids:
        degraded = ("the Power Apps profile could not be read, so the power-apps checks "
                    "did not run. Expected references/shared/powerapps-profile.md in this "
                    "skill's folder.")

    errors = sum(1 for f in findings if f.severity == ERROR)
    warnings = sum(1 for f in findings if f.severity == WARNING)
    if errors:
        code, verdict = "will_fail", f"VERDICT: WILL FAIL — {errors} error(s) to fix"
    elif degraded:
        suffix = f", {warnings} warning(s)" if warnings else ""
        code, verdict = "unproven", f"VERDICT: UNPROVEN — power-apps checks skipped{suffix}"
    elif warnings:
        code, verdict = "unverified", f"VERDICT: USABLE, WITH {warnings} WARNING(S) TO REVIEW"
    else:
        code, verdict = "safe", "VERDICT: CLEAN"
    findings.sort(key=lambda f: (0 if f.severity == ERROR else 1, f.line or 0, f.check))
    return {"path": path.as_posix(), "target": target,
            "findings": [f.as_dict() for f in findings], "errors": errors,
            "warnings": warnings, "verdict": verdict, "verdict_code": code,
            "degraded": degraded}


def render(report: dict, quiet=False) -> str:
    out = []
    if not quiet:
        out += ["=" * 72, f"{report['path']}  (target: {report['target']})", "=" * 72]
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
                where = [f"line {f['line']}"] if f["line"] else []
                if f["path"]:
                    where.append(f["path"])
                if where:
                    out.append(f"    at: {' | '.join(where)}")
                if f["detail"]:
                    out.append(f"    {f['detail']}")
                out.append("")
        if not report["findings"]:
            out += ["  No findings.", ""]
    out.append(report["verdict"])
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="design_lint.py",
        description="Check a DESIGN.md design system offline and end with a verdict.")
    parser.add_argument("files", nargs="+", type=Path, help="DESIGN.md file(s) to check")
    parser.add_argument("--target", choices=("web", "power-apps"), default="web",
                        help="web (default) or power-apps, which adds the profile checks")
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

    profile_ids = load_profile_ids(args.profile) if args.target == "power-apps" else None
    reports = []
    for path in args.files:
        if not path.is_file():
            print(f"ERROR: no such file: {path}", file=sys.stderr)
            return 2
        reports.append(lint_file(path, args.target, profile_ids))

    errors = sum(r["errors"] for r in reports)
    warnings = sum(r["warnings"] for r in reports)
    degraded = any(r["degraded"] for r in reports)
    if errors:
        code = 1
    elif (warnings or degraded) and args.strict:
        code = 2
    else:
        code = 0

    if args.json:
        print(json.dumps({"version": 1, "target": args.target,
                          "profile": args.profile.as_posix() if args.target == "power-apps"
                          else None,
                          "files": reports,
                          "summary": {"files": len(reports), "errors": errors,
                                      "warnings": warnings, "exit_code": code}},
                         indent=2, ensure_ascii=False))
        return code
    for r in reports:
        print(render(r, quiet=args.quiet))
    if len(reports) > 1 and not args.quiet:
        print(f"\nSUMMARY: {len(reports)} files, {errors} error(s), {warnings} warning(s)")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
