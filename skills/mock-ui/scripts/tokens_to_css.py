#!/usr/bin/env python3
"""Turn the YAML front matter of a DESIGN.md into the one `:root { ... }` block a mockup
page uses.

    python3 scripts/tokens_to_css.py DESIGN.md [--target web|power-apps]
                                     [--canvas 1366x768] [--out FILE] [--json]

Every value in the rest of a mockup's CSS is `var(--...)` of a name printed here, so the
names are a contract with `mock_lint.py` and with the `create-app` conversion:

    colors.<name>                    --color-<name>
    typography.<level>.<property>    --font-<level>-family | -size | -weight
                                     | -line-height | -letter-spacing
                                     | -feature | -variation
    rounded.<name>                   --radius-<name>
    spacing.<name>                   --space-<name>
    components.<name>.<property>     --<name>-bg | -text | -radius | -padding
                                     | -height | -width | -size
    (power-apps only)                --canvas-width, --canvas-height

A component property written as a `{group.token}` reference becomes `var(--...)` of
that token, so the chain survives into the CSS. A component `typography` reference names
a whole level, which no single CSS value can hold; it is printed as a comment and the
page uses the level's own variables.

`--target power-apps` makes every length arithmetic, because the canvas has no text
reflow to lean on: rem and em become px (1rem = 16px; an em letter-spacing is relative
to its level's font size, any other em to 16px), and a unit-less lineHeight becomes
fontSize x lineHeight in px, rounded to the nearest pixel. Under `web` every value is
copied as written.

Exit codes: 0 written | 1 the DESIGN.md has no usable front matter | 2 usage problem or
PyYAML missing. Requires PyYAML.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

GROUP_PREFIX = {"colors": "color", "rounded": "radius", "spacing": "space"}
TYPO_SUFFIX = {"fontFamily": "family", "fontSize": "size", "fontWeight": "weight",
               "lineHeight": "line-height", "letterSpacing": "letter-spacing",
               "fontFeature": "feature", "fontVariation": "variation"}
COMPONENT_SUFFIX = {"backgroundColor": "bg", "textColor": "text", "rounded": "radius",
                    "padding": "padding", "height": "height", "width": "width",
                    "size": "size"}
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
REF_RE = re.compile(r"^\{([A-Za-z]+)\.([A-Za-z0-9_-]+)\}$")
LENGTH_RE = re.compile(r"^(-?(?:\d+\.?\d*|\.\d+))(px|rem|em)?$")
ROOT_PX = 16.0
DEFAULT_CANVAS = (1366, 768)


class TokenError(Exception):
    """The DESIGN.md cannot be turned into variables."""


def _yaml():
    try:
        import yaml  # type: ignore
        return yaml
    except ImportError:
        return None


def front_matter(text: str) -> dict:
    """The parsed front matter of a DESIGN.md. Raises TokenError when there is none."""
    yaml = _yaml()
    if yaml is None:
        raise ImportError("PyYAML is not installed. Run: pip install pyyaml")
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        raise TokenError("no `---` front matter at the top of the file")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            try:
                data = yaml.safe_load("\n".join(lines[1:i]))
            except yaml.YAMLError as exc:
                raise TokenError(f"front matter is not valid YAML: {exc}") from exc
            if not isinstance(data, dict):
                raise TokenError("front matter is not a mapping")
            return data
    raise TokenError("front matter is never closed with `---`")


def _fmt(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else f"{n:.2f}".rstrip("0").rstrip(".")


def to_px(value, em_base: float = ROOT_PX) -> str:
    """One length (or a space-separated list of them) in px; anything else unchanged."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{_fmt(value)}px" if value else "0"
    if not isinstance(value, str):
        return str(value)
    parts = value.split()
    out = []
    for part in parts:
        m = LENGTH_RE.match(part)
        if not m:
            out.append(part)
            continue
        num, unit = float(m.group(1)), m.group(2)
        if unit == "rem":
            num *= ROOT_PX
        elif unit == "em":
            num *= em_base
        out.append(f"{_fmt(round(num, 2))}px" if (unit or num) else "0")
    return " ".join(out)


def _px_number(value) -> float | None:
    """A single length as a number of px, or None."""
    if value is None:
        return None
    m = re.match(r"^(-?\d+\.?\d*)px$", to_px(value))
    return float(m.group(1)) if m else None


def font_stack(value) -> str:
    """`Segoe UI, system-ui, sans-serif` -> `"Segoe UI", system-ui, sans-serif`."""
    if not isinstance(value, str):
        return str(value)
    generic = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui",
               "ui-serif", "ui-sans-serif", "ui-monospace", "ui-rounded", "emoji",
               "math", "fangsong"}
    out = []
    for fam in (f.strip() for f in value.split(",")):
        if not fam:
            continue
        if fam[0] in "\"'" or fam in generic or re.match(r"^[A-Za-z][\w-]*$", fam):
            out.append(fam)
        else:
            out.append(f'"{fam}"')
    return ", ".join(out)


def ref_var(value) -> str | None:
    """`{colors.primary}` -> `var(--color-primary)`; None when it is not a value ref."""
    if not isinstance(value, str):
        return None
    m = REF_RE.match(value.strip())
    if not m or m.group(1) not in GROUP_PREFIX:
        return None
    return f"var(--{GROUP_PREFIX[m.group(1)]}-{m.group(2)})"


def variables(fm: dict, target: str = "web",
              canvas: tuple[int, int] = DEFAULT_CANVAS) -> list[tuple[str, str | None, str]]:
    """(css-name, value, comment) in output order. value None means a comment line."""
    pa = target == "power-apps"
    out: list[tuple[str, str | None, str]] = []

    def name_ok(group: str, name) -> str:
        if not isinstance(name, str) or not NAME_RE.match(name):
            raise TokenError(f"{group}: token name {name!r} cannot be a CSS custom property")
        return name

    if pa:
        out.append(("", None, "canvas (power-apps target)"))
        out.append(("--canvas-width", f"{canvas[0]}px", ""))
        out.append(("--canvas-height", f"{canvas[1]}px", ""))

    colors = fm.get("colors") or {}
    if colors:
        out.append(("", None, "colors"))
        for name, value in colors.items():
            out.append((f"--color-{name_ok('colors', name)}", str(value), ""))

    typography = fm.get("typography") or {}
    if typography:
        out.append(("", None, "typography"))
        for level, props in typography.items():
            name_ok("typography", level)
            if not isinstance(props, dict):
                continue
            size_px = _px_number(props.get("fontSize")) or ROOT_PX
            for prop, suffix in TYPO_SUFFIX.items():
                if prop not in props:
                    continue
                value = props[prop]
                if prop == "fontFamily":
                    css = font_stack(value)
                elif prop == "fontWeight":
                    css = str(value)
                elif prop == "lineHeight":
                    if pa and isinstance(value, (int, float)) and not isinstance(value, bool):
                        css = f"{_fmt(round(size_px * value))}px"
                    elif pa and isinstance(value, str) and re.match(r"^\d+\.?\d*$", value):
                        css = f"{_fmt(round(size_px * float(value)))}px"
                    else:
                        css = to_px(value, size_px) if pa else str(value)
                elif prop == "letterSpacing":
                    css = to_px(value, size_px) if pa else str(value)
                elif prop == "fontSize":
                    css = to_px(value) if pa else str(value)
                else:
                    css = str(value)
                out.append((f"--font-{level}-{suffix}", css, ""))

    for group in ("rounded", "spacing"):
        tokens = fm.get(group) or {}
        if tokens:
            out.append(("", None, group))
            for name, value in tokens.items():
                css = to_px(value) if pa else str(value)
                out.append((f"--{GROUP_PREFIX[group]}-{name_ok(group, name)}", css, ""))

    components = fm.get("components") or {}
    if components:
        out.append(("", None, "components"))
        for comp, props in components.items():
            name_ok("components", comp)
            if not isinstance(props, dict):
                continue
            for prop, value in props.items():
                if prop == "typography":
                    m = REF_RE.match(str(value).strip())
                    level = m.group(2) if m else value
                    out.append(("", None, f"{comp} typography: --font-{level}-*"))
                    continue
                suffix = COMPONENT_SUFFIX.get(prop) or re.sub(
                    r"(?<!^)(?=[A-Z])", "-", str(prop)).lower()
                css = ref_var(value)
                if css is None:
                    css = to_px(value) if pa else str(value)
                out.append((f"--{comp}-{suffix}", css, ""))
    return out


def as_map(fm: dict, target: str = "web",
           canvas: tuple[int, int] = DEFAULT_CANVAS) -> dict[str, str]:
    """css-name -> value, for mock_lint.py's drift check."""
    return {n: v for n, v, _c in variables(fm, target, canvas) if v is not None}


def render(fm: dict, target: str = "web", canvas: tuple[int, int] = DEFAULT_CANVAS,
           source: str = "DESIGN.md") -> str:
    name = str(fm.get("name") or "").replace("*/", "")
    lines = [":root {",
             f"  /* Generated by tokens_to_css.py from {source}"
             + (f" ({name})" if name else "") + f", target {target}.",
             "     Regenerate instead of editing; mock_lint.py --design checks for drift. */"]
    for css_name, value, comment in variables(fm, target, canvas):
        if value is None:
            lines.append(f"  /* {comment} */")
        else:
            lines.append(f"  {css_name}: {value};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def parse_canvas(text: str) -> tuple[int, int]:
    m = re.match(r"^(\d+)\s*[xX×]\s*(\d+)$", text.strip())
    if not m:
        raise argparse.ArgumentTypeError("canvas must look like 1366x768")
    return int(m.group(1)), int(m.group(2))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="tokens_to_css.py",
        description="Turn DESIGN.md front matter into a mockup's :root block.")
    parser.add_argument("design", type=Path, help="the DESIGN.md to read")
    parser.add_argument("--target", choices=("web", "power-apps"), default="web")
    parser.add_argument("--canvas", type=parse_canvas, default=DEFAULT_CANVAS,
                        help="power-apps canvas, default 1366x768")
    parser.add_argument("--out", type=Path, help="write here instead of stdout")
    parser.add_argument("--json", action="store_true",
                        help="print {name: value} instead of CSS")
    args = parser.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover
        pass
    if not args.design.is_file():
        print(f"ERROR: no such file: {args.design}", file=sys.stderr)
        return 2
    try:
        fm = front_matter(args.design.read_text(encoding="utf-8-sig"))
        text = (json.dumps(as_map(fm, args.target, args.canvas), indent=2,
                           ensure_ascii=False) + "\n" if args.json
                else render(fm, args.target, args.canvas, args.design.name))
    except ImportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except TokenError as exc:
        print(f"ERROR: {args.design}: {exc}", file=sys.stderr)
        return 1
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
