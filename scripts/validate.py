#!/usr/bin/env python3
"""Repository sanity checks for the supersub plugin and its skills.

Run locally before opening a PR:

    python scripts/validate.py

Exits non-zero if anything fails. Requires PyYAML (`pip install pyyaml`).

The checks that apply to every skill under skills/ live in scripts/skill_checks.py;
everything below them is specific to the create-app skill.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import privacy_check  # noqa: E402
import skill_checks  # noqa: E402  (needs the sys.path line above)

SKILL_DIR = ROOT / "skills" / "create-app"
SKILL_SCRIPTS = SKILL_DIR / "scripts"

# --- Budgets -----------------------------------------------------------------
# SKILL.md is loaded into context on every single invocation, so its size is a
# running cost, not a one-off. Everything that is not procedure belongs in
# README.md or a references/ file that is read on demand.
SKILL_MD_MAX_BYTES = 8192
# The frontmatter description is what makes the skill fire. It has to keep every
# distinct trigger phrase, which is why the ceiling is a ceiling and not a target:
# trim justification prose, never a trigger.
DESCRIPTION_MAX_CHARS = 650
DESCRIPTION_MIN_CHARS = 40
# Pattern snippets exist to be read instead of a 1,700-line example, so they stay
# small. tile-grid-cell is an acknowledged exception: it is a six-control
# composite (card, title, subtitle, checkbox, check icon, click overlay) and
# cutting it to 60 lines would mean dropping the selection mechanic that is the
# whole reason to extract it.
PATTERN_MAX_LINES = 60
PATTERN_MAX_LINES_EXCEPTIONS = {"tile-grid-cell.pa.yaml": 90}
PATTERN_MIN_LINES = 20
# Every pattern file opens with these header fields, so a reader knows what it is
# and -- crucially -- where the evidence for it came from.
PATTERN_HEADER_FIELDS = ("PATTERN", "What", "Controls", "Source", "Evidence")
# A paste-test snippet is the opposite of a pattern: a pattern is extracted evidence,
# a snippet is an isolated guess for the user to disprove in Studio. The header has to
# say which control is under test, where its property names came from, how to run it
# and where the answer goes.
SNIPPET_HEADER_FIELDS = ("SNIPPET", "What", "Control", "Evidence", "Test", "Record")
SNIPPET_MIN = 12
# The inventory tool exists to save context. If its one-page summary of a ten-screen
# app stops fitting on a page, it has stopped doing its job.
INVENTORY_MAX_BYTES = 2048
# Eval cases. Five archetypes, each covering a layout shape the others do not --
# plus the hard one, which covers the honesty path rather than a layout at all --
# and the mock-ui pipeline: a mockup folder in, one file per screen out.
EVAL_CASES_MIN = 6
REQUIRED_EVAL_CASES = {
    "app-shell", "multi-section-form", "card-grid",
    "shell-with-form", "impossible-effects", "multi-screen-mock",
}
# A case asserting one or two of these is not measuring enough to tell a good
# conversion from a bad one.
EVAL_ASSERTION_BLOCKS = ("structure", "lint", "controls", "geometry", "navigation",
                         "catalog", "limitations")

errors: list[str] = []
checks = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global checks
    checks += 1
    if ok:
        print(f"  ok   {label}")
    else:
        msg = f"{label}" + (f" -- {detail}" if detail else "")
        print(f"  FAIL {msg}")
        errors.append(msg)


def load_yaml():
    try:
        import yaml  # type: ignore
        return yaml
    except ImportError:
        print("ERROR: PyYAML is not installed. Run: pip install pyyaml")
        sys.exit(2)


yaml = load_yaml()

print("Every skill (portability rules)")
for ok, label, detail in skill_checks.run_all(ROOT, yaml):
    check(ok, label, detail)

print("Layout (create-app)")
check(SKILL_DIR.is_dir(), "skills/create-app/ exists")
skill_md = SKILL_DIR / "SKILL.md"
check(skill_md.is_file(), "SKILL.md present")
schema = SKILL_DIR / "references" / "schema-v3.pa.yaml"
check(schema.is_file(), "bundled Microsoft schema present",
      "references/schema-v3.pa.yaml is referenced by NOTICE and must not be removed")
check((SKILL_DIR / "references" / "confirmed-controls.md").is_file(),
      "confirmed-controls.md present")
check((SKILL_DIR / "references" / "controls.yaml").is_file(),
      "controls.yaml present", "the machine-readable catalog scripts/pa_lint.py reads")
check((SKILL_DIR / "references" / "layout-mapping.md").is_file(),
      "layout-mapping.md present",
      "the HTML/CSS -> X/Y/Width/Height reference SKILL.md step 3 sends the model to")
check((SKILL_DIR / "assets" / "patterns").is_dir(),
      "assets/patterns/ present", "the extracted pattern snippets SKILL.md step 2 uses")
check((SKILL_DIR / "assets" / "examples" / "INDEX.md").is_file(),
      "assets/examples/INDEX.md present",
      "the line-range index that lets a slice be read instead of a whole example")
check((SKILL_SCRIPTS / "pa_lint.py").is_file(), "skills/create-app/scripts/pa_lint.py present")
check((SKILL_DIR / "references" / "extend-existing-app.md").is_file(),
      "extend-existing-app.md present",
      "the procedure SKILL.md branches to when the app already exists")
check((SKILL_DIR / "references" / "data-binding.md").is_file(),
      "data-binding.md present", "the UNVERIFIED data-binding groundwork")
check((SKILL_DIR / "assets" / "test-snippets").is_dir(),
      "assets/test-snippets/ present", "the one-control paste-test kit")
check((ROOT / "docs" / "test-plan.md").is_file(), "docs/test-plan.md present",
      "the results table the paste-test kit reports into")
check((SKILL_SCRIPTS / "app_inventory.py").is_file(),
      "skills/create-app/scripts/app_inventory.py present",
      "the one-page summariser for an app that already exists")
check((ROOT / "tests" / "apps" / "ten-screen-app").is_dir(),
      "tests/apps/ten-screen-app/ present",
      "the synthetic fixture the inventory byte budget is measured against")
check((SKILL_SCRIPTS / "harvest_controls.py").is_file(),
      "skills/create-app/scripts/harvest_controls.py present",
      "the Studio-export harvester documented in references/harvesting.md")
check((SKILL_DIR / "references" / "harvesting.md").is_file(),
      "references/harvesting.md present", "SKILL.md step 8 sends the reader there")
for moved in ("pa_lint.py", "app_inventory.py", "harvest_controls.py"):
    check(not (ROOT / "scripts" / moved).exists(),
          f"no stale scripts/{moved} at the repo root",
          "run-time scripts live inside the skill so an installed plugin can reach them")
check((SKILL_DIR / "references" / "control-ids-candidate.yaml").is_file(),
      "control-ids-candidate.yaml present",
      "the mirrored Microsoft control-id enum pa_lint.py reads for wording")
check(not (ROOT / "skill").exists(), "no stray top-level skill/ directory")
check(not (ROOT / "confirmed-controls.md").exists(),
      "no duplicate confirmed-controls.md at repo root")

print("SKILL.md frontmatter")
if skill_md.is_file():
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    check(bool(m), "has a YAML frontmatter block")
    if m:
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError as e:  # pragma: no cover
            fm = {}
            check(False, "frontmatter parses as YAML", str(e))
        check(isinstance(fm.get("name"), str) and fm.get("name").strip() != "",
              "frontmatter has non-empty 'name'")
        check(fm.get("name") == "create-app",
              "frontmatter name is 'create-app'", f"got {fm.get('name')!r}")
        desc = fm.get("description")
        check(isinstance(desc, str) and len(desc.strip()) >= DESCRIPTION_MIN_CHARS,
              "frontmatter has a substantive 'description'")
        if isinstance(desc, str):
            n = len(desc.strip())
            check(n <= DESCRIPTION_MAX_CHARS,
                  f"frontmatter description is within {DESCRIPTION_MAX_CHARS} chars",
                  f"got {n}. Cut justification sentences, never a trigger phrase -- "
                  "the triggers are what make the skill fire.")

print("SKILL.md size budget")
if skill_md.is_file():
    size = len(skill_md.read_bytes())
    check(size <= SKILL_MD_MAX_BYTES,
          f"SKILL.md is within {SKILL_MD_MAX_BYTES} bytes",
          f"got {size} ({size - SKILL_MD_MAX_BYTES} over). SKILL.md is procedure only: "
          "move rationale to README.md and detail to references/.")
    body = skill_md.read_text(encoding="utf-8")
    # The things SKILL.md must never lose while being shrunk.
    for needle, label in (
        ("## The workflow", "the ordered workflow"),
        ("## Control picker", "the control picker table"),
        ("## Templates", "the templates"),
        ("## Rules while writing", "the rules list"),
        ("## Pre-send checklist", "the pre-send checklist"),
        ("assets/patterns/", "a pointer to assets/patterns/"),
        ("layout-mapping.md", "a pointer to layout-mapping.md"),
        ("INDEX.md", "a pointer to the example INDEX.md"),
        ("pa_lint.py", "the lint step"),
        ("extend-existing-app.md", "the existing-app branch"),
        ("data-binding.md", "the data-binding branch"),
        ("test-snippets", "a pointer to the paste-test kit"),
    ):
        check(needle in body, f"SKILL.md still contains {label}", f"missing {needle!r}")

print("Example screens are valid YAML")
examples = sorted((SKILL_DIR / "assets" / "examples").glob("*.yaml"))
check(len(examples) >= 1, "at least one example screen exists")
for ex in examples:
    try:
        doc = yaml.safe_load(ex.read_text(encoding="utf-8"))
        top = next(iter(doc)) if isinstance(doc, dict) else None
        check(isinstance(doc, dict) and top in {"Screens", "App", "ComponentDefinitions"},
              f"{ex.name} parses and has a known top-level key", f"top-level key: {top!r}")
    except yaml.YAMLError as e:
        check(False, f"{ex.name} parses as YAML", str(e))

print("Control catalog (controls.yaml <-> confirmed-controls.md)")
catalog_path = SKILL_DIR / "references" / "controls.yaml"
catalog = None
if catalog_path.is_file():
    try:
        catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
        check(isinstance(catalog, dict), "controls.yaml parses as a YAML mapping")
    except yaml.YAMLError as e:
        check(False, "controls.yaml parses as YAML", str(e))

if isinstance(catalog, dict):
    for key in ("schema_version", "evidence_levels", "universal_properties", "controls"):
        check(key in catalog, f"controls.yaml has '{key}'")

    entries = catalog.get("controls") or []
    check(all(isinstance(e, dict) and {"name", "type", "evidence"} <= set(e)
              for e in entries),
          "every catalog entry has name/type/evidence")

    levels = set(catalog.get("evidence_levels") or [])
    bad_evidence = sorted({e.get("evidence") for e in entries} - levels)
    check(not bad_evidence, "every entry's evidence is a declared level",
          f"unknown: {bad_evidence}")

    # An entry without a source is an entry without evidence, which is the exact
    # failure mode this project exists to prevent.
    missing_source = [e.get("type") for e in entries if not str(e.get("source") or "").strip()]
    check(not missing_source, "every catalog entry cites a source", f"missing: {missing_source}")

    yaml_types = {e.get("type") for e in entries}

    # A harvest merge adds a control entry but deliberately does not edit the
    # hand-curated "not yet attempted" list; this is the check that catches the
    # leftover. See skills/create-app/references/harvesting.md.
    catalogued_bases = {str(t).split("@", 1)[0].rsplit("/", 1)[-1] for t in yaml_types}
    overlap = sorted(catalogued_bases & set(catalog.get("unattempted_controls") or []))
    check(not overlap,
          "no control is both catalogued and listed in unattempted_controls",
          f"remove from unattempted_controls: {overlap}")

    # Cross-check against the human-readable view: the two must not drift apart.
    md_text = (SKILL_DIR / "references" / "confirmed-controls.md").read_text(encoding="utf-8")
    section = md_text.split("## Control types", 1)[-1].split("\n## ", 1)[0]
    control_id_re = re.compile(r"^[A-Z][A-Za-z0-9]*(?:/[A-Z][A-Za-z0-9]*)?@\d+\.\d+\.\d+$")
    md_types = set()
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        for token in re.findall(r"`([^`]+)`", cells[1]):
            if control_id_re.match(token):
                md_types.add(token)
                break

    check(bool(md_types), "confirmed-controls.md control table is parseable")
    check(md_types <= yaml_types, "every control in confirmed-controls.md is in controls.yaml",
          f"missing from controls.yaml: {sorted(md_types - yaml_types)}")
    check(yaml_types <= md_types, "every control in controls.yaml is in confirmed-controls.md",
          f"missing from the markdown: {sorted(yaml_types - md_types)}")

print("Candidate control ids (control-ids-candidate.yaml)")
candidates_path = SKILL_DIR / "references" / "control-ids-candidate.yaml"
candidates = None
if candidates_path.is_file():
    try:
        candidates = yaml.safe_load(candidates_path.read_text(encoding="utf-8"))
        check(isinstance(candidates, dict), "control-ids-candidate.yaml parses as a mapping")
    except yaml.YAMLError as e:
        check(False, "control-ids-candidate.yaml parses as YAML", str(e))

if isinstance(candidates, dict):
    ids = candidates.get("control_ids") or []
    check(bool(ids), "control-ids-candidate.yaml lists control_ids")
    # The whole point of this file is that it is a hint, not evidence. A single entry
    # promoted here would quietly turn Microsoft's internal enum into a confirmation.
    not_unverified = [e.get("id") for e in ids
                      if not isinstance(e, dict) or e.get("evidence") != "unverified"]
    check(not not_unverified,
          "every candidate control id is marked evidence: unverified",
          f"not unverified: {not_unverified}")
    for key in ("upstream_repo", "upstream_path", "upstream_commit", "retrieved"):
        check(bool(str(candidates.get(key) or "").strip()),
              f"control-ids-candidate.yaml records '{key}'",
              "provenance is the only thing that makes this file re-checkable")

print("Linter accepts the bundled examples")
lint = SKILL_SCRIPTS / "pa_lint.py"
if lint.is_file() and examples:
    proc = subprocess.run(
        [sys.executable, str(lint), *[str(p) for p in examples], "--quiet"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
    )
    check(proc.returncode == 0,
          "pa_lint.py returns 0 for all three bundled examples",
          f"exit {proc.returncode}\n{proc.stdout}\n{proc.stderr}")


def lint_json(paths):
    """Run pa_lint.py over paths and return its JSON report, or None."""
    if not lint.is_file() or not paths:
        return None
    proc = subprocess.run(
        [sys.executable, str(lint), *[str(x) for x in paths], "--json"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        check(False, "pa_lint.py --json produced parseable output",
              f"exit {proc.returncode}\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}")
        return None


print("Pattern snippets (assets/patterns/)")
patterns = sorted((SKILL_DIR / "assets" / "patterns").glob("*.pa.yaml"))
check(len(patterns) >= 10, "assets/patterns/ holds the extracted snippets",
      f"found {len(patterns)}")

for pat in patterns:
    src = pat.read_text(encoding="utf-8")
    lines = src.splitlines()
    header = "\n".join(ln for ln in lines if ln.startswith("#"))
    missing = [f for f in PATTERN_HEADER_FIELDS if f"# {f}" not in header]
    check(not missing, f"{pat.name} header records {'/'.join(PATTERN_HEADER_FIELDS)}",
          f"missing: {missing}. A pattern without a cited Source and Evidence level is "
          "an unsourced claim, which is the failure mode this repo exists to prevent.")
    # The Source field has to name a real bundled example -- patterns are extracted,
    # never invented.
    cites = [ex.name for ex in examples if ex.name in header]
    check(bool(cites), f"{pat.name} cites a bundled example as its source",
          "no assets/examples/*.yaml filename appears in the header")
    cap = PATTERN_MAX_LINES_EXCEPTIONS.get(pat.name, PATTERN_MAX_LINES)
    check(PATTERN_MIN_LINES <= len(lines) <= cap,
          f"{pat.name} is {PATTERN_MIN_LINES}-{cap} lines",
          f"got {len(lines)}. Patterns are read instead of a 1,700-line example; "
          "split it or move detail into the header comment.")

report = lint_json(patterns)
if report:
    for f in report.get("files", []):
        name = Path(f["path"]).name
        check(f.get("verdict_code") == "safe",
              f"{name} lints SAFE TO PASTE",
              f"{f.get('verdict')}: "
              + "; ".join(x["message"] for x in f.get("findings", [])))

print("Paste-test snippets (assets/test-snippets/)")
snippets = sorted((SKILL_DIR / "assets" / "test-snippets").glob("*.pa.yaml"))
check(len(snippets) >= SNIPPET_MIN,
      f"assets/test-snippets/ holds at least {SNIPPET_MIN} paste tests",
      f"found {len(snippets)}")


def control_count(node) -> int:
    """Control instances under a Screens: mapping, counted recursively."""
    total = 0
    for screen in (node or {}).values():
        total += _children_count((screen or {}).get("Children"))
    return total


def _children_count(children) -> int:
    total = 0
    for item in children or []:
        if not isinstance(item, dict):
            continue
        for body in item.values():
            if isinstance(body, dict):
                total += 1 + _children_count(body.get("Children"))
    return total


for snip in snippets:
    src = snip.read_text(encoding="utf-8")
    header = "\n".join(ln for ln in src.splitlines() if ln.startswith("#"))
    missing = [f for f in SNIPPET_HEADER_FIELDS if f"# {f}" not in header]
    check(not missing, f"{snip.name} header records {'/'.join(SNIPPET_HEADER_FIELDS)}",
          f"missing: {missing}. A snippet without a stated Evidence line reads as a "
          "recommendation, which is the opposite of what this kit is.")
    # The kit's whole premise: a failure must be attributable to one control.
    try:
        doc = yaml.safe_load(src) or {}
        count = control_count(doc.get("Screens"))
        check(count == 1, f"{snip.name} contains exactly one control",
              f"found {count}. Two controls in one file means a paste failure cannot "
              "be attributed to either of them.")
    except yaml.YAMLError as e:
        check(False, f"{snip.name} parses as YAML", str(e))
    # One property per line is what makes bisecting-by-deletion work.
    check("UNVERIFIED below here" in src,
          f"{snip.name} marks where the unverified properties start",
          "the bisect marker is the line the user deletes downward from")

report = lint_json(snippets)
if report:
    for f in report.get("files", []):
        name = Path(f["path"]).name
        blocking = [x for x in f.get("findings", []) if x["layer"] in ("L0", "L1")]
        check(not blocking, f"{name} has no L0/L1 error",
              "; ".join(x["message"] for x in blocking))
        # L2 warnings are the POINT. A snippet that lints clean is either already
        # catalogued -- so it does not belong in the kit -- or the catalog drifted.
        check(any(x["layer"] == "L2" for x in f.get("findings", [])),
              f"{name} raises an L2 unverified warning",
              "nothing in this file is unverified any more; either it belongs in "
              "assets/patterns/ now, or controls.yaml changed underneath it")

print("docs/test-plan.md covers every snippet")
test_plan = ROOT / "docs" / "test-plan.md"
if test_plan.is_file() and snippets:
    plan = test_plan.read_text(encoding="utf-8")
    uncovered = [s.name for s in snippets if s.name not in plan]
    check(not uncovered, "every test-snippet file has a row in the results table",
          f"missing rows: {uncovered}. A snippet with nowhere to report its result "
          "will never be run.")
    check("controls.yaml" in plan,
          "test-plan.md says how a result gets into the catalog")

print("data-binding.md keeps every expression marked")
data_binding = SKILL_DIR / "references" / "data-binding.md"
if data_binding.is_file():
    text = data_binding.read_text(encoding="utf-8")
    # Every fenced yaml/text block is a Power Fx or .pa.yaml example, and the phase
    # brief is explicit: all of them are unverified until a Studio test says otherwise.
    unmarked = [body.splitlines()[0][:50]
                for _lang, body in re.findall(r"(?ms)^```(yaml|text)\n(.*?)^```", text)
                if "UNVERIFIED" not in body]
    check(not unmarked, "every yaml/text example in data-binding.md is marked UNVERIFIED",
          f"unmarked blocks start: {unmarked}")
    # Each recipe has to name the paste test that unblocks it, and that file has to
    # exist -- otherwise the pairing is decoration.
    # `schema-v3.pa.yaml` and friends are references/ files, not snippets.
    named = {n for n in re.findall(r"`([a-z0-9-]+\.pa\.yaml)`", text)
             if not (SKILL_DIR / "references" / n).is_file()}
    have = {s.name for s in snippets}
    check(named <= have, "every snippet data-binding.md names exists",
          f"named but missing: {sorted(named - have)}")
    check(bool(named), "data-binding.md pairs its recipes with paste-test snippets")
    check("schema-v3.pa.yaml" in text,
          "data-binding.md cites the bundled schema for the DataSources block")
    # The yaml blocks are complete documents, so they can be proven, not just claimed.
    blocks = re.findall(r"(?ms)^```yaml\n(.*?)^```", text)
    tmp = ROOT / ".validate-tmp-db"
    written = []
    try:
        if blocks:
            tmp.mkdir(exist_ok=True)
            for i, block in enumerate(blocks):
                f = tmp / f"data-binding-block-{i}.pa.yaml"
                f.write_text(block, encoding="utf-8")
                written.append(f)
        rep = lint_json(written)
        if rep:
            for f in rep.get("files", []):
                bad = [x for x in f.get("findings", []) if x["layer"] in ("L0", "L1")]
                check(not bad,
                      f"data-binding.md example ({Path(f['path']).name}) is valid pa.yaml",
                      "; ".join(x["message"] for x in bad))
    finally:
        for f in written:
            f.unlink(missing_ok=True)
        if tmp.is_dir():
            tmp.rmdir()

print("app_inventory.py stays inside its page budget")
inventory = SKILL_SCRIPTS / "app_inventory.py"
fixture = ROOT / "tests" / "apps" / "ten-screen-app"
if inventory.is_file() and fixture.is_dir():
    proc = subprocess.run([sys.executable, str(inventory), str(fixture)],
                          capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
    check(proc.returncode == 0, "app_inventory.py runs against the 10-screen fixture",
          f"exit {proc.returncode}\n{proc.stderr[-500:]}")
    size = len(proc.stdout.encode("utf-8"))
    check(size < INVENTORY_MAX_BYTES,
          f"the 10-screen summary is under {INVENTORY_MAX_BYTES} bytes",
          f"got {size}. Summarise harder -- the tool exists to save context, not to "
          "reformat the source.")
    for needle, label in (("SCREENS", "the screen list"),
                          ("TYPES:", "the control types with their versions"),
                          ("ONSTART", "the App.OnStart variables"),
                          ("DATASOURCES", "the data sources"),
                          ("COMPONENTS", "the component definitions"),
                          ("_1", "the collision warning")):
        check(needle in proc.stdout, f"the summary still carries {label}",
              f"missing {needle!r}")

print("layout-mapping.md recommends only catalogued properties")
layout_md = SKILL_DIR / "references" / "layout-mapping.md"
if layout_md.is_file() and isinstance(catalog, dict):
    entries = catalog.get("controls") or []
    # Every property name the catalog knows about, at any evidence level. An
    # unverified property is still a real property; an absent one is an invention.
    known = set(catalog.get("universal_properties") or [])
    for e in entries:
        for key in ("properties_confirmed", "properties_example_file",
                    "properties_unverified"):
            known |= set(e.get(key) or [])
    # Not properties, but legitimately written in backticks: the .pa.yaml structural
    # keys, the control base names, and the Variant values -- all derived from the
    # catalog itself rather than hand-listed, so they cannot drift.
    structural = {"Screens", "Properties", "Children", "Control", "Variant",
                  "App", "ComponentDefinitions"}
    for e in entries:
        structural.add(str(e.get("name")))
        structural.add(str(e.get("type")).split("@", 1)[0].rsplit("/", 1)[-1])
        if e.get("variant"):
            structural.add(str(e["variant"]))
    vocabulary = known | structural

    def resolves(token: str) -> bool:
        """True if token is a catalogued property, a structural key, or a Prop* stem."""
        if token in vocabulary:
            return True
        if token.endswith("*"):
            stem = token[:-1]
            return any(k.startswith(stem) for k in vocabulary)
        return False

    for md in (layout_md, skill_md):
        prose = re.sub(r"(?ms)^```.*?^```", "", md.read_text(encoding="utf-8"))
        offenders = set()
        for span in set(re.findall(r"`([^`\n]+)`", prose)):
            # "Name: =value" -- unambiguously a property being written.
            assigned = re.match(r"^([A-Za-z][A-Za-z0-9.]*\*?)\s*:", span)
            if assigned:
                if not resolves(assigned.group(1)):
                    offenders.add(assigned.group(1))
                continue
            # A bare multi-word CamelCase identifier reads as a property name
            # (LayoutGap, PaddingTop, DropShadow, FillPortions...). Single-word
            # tokens are too ambiguous to flag -- they are just as likely prose.
            if re.match(r"^(?:[A-Z][a-z0-9]+){2,}\*?$", span) and not resolves(span):
                offenders.add(span)
        check(not offenders,
              f"{md.name} names no property absent from controls.yaml",
              f"not in the catalog: {sorted(offenders)}. Either add it to "
              "controls.yaml with a cited Studio test, or stop recommending it.")

print("layout-mapping.md's worked example lints clean")
if layout_md.is_file():
    blocks = re.findall(r"(?ms)^```yaml\n(.*?)^```", layout_md.read_text(encoding="utf-8"))
    check(bool(blocks), "layout-mapping.md contains a worked .pa.yaml example")
    tmp = ROOT / ".validate-tmp"
    written = []
    try:
        if blocks:
            tmp.mkdir(exist_ok=True)
            for i, block in enumerate(blocks):
                f = tmp / f"layout-mapping-block-{i}.pa.yaml"
                f.write_text(block, encoding="utf-8")
                written.append(f)
        rep = lint_json(written)
        if rep:
            for f in rep.get("files", []):
                check(f.get("verdict_code") == "safe",
                      f"layout-mapping.md worked example ({Path(f['path']).name}) "
                      "lints SAFE TO PASTE",
                      f"{f.get('verdict')}: "
                      + "; ".join(x["message"] for x in f.get("findings", [])))
    finally:
        for f in written:
            f.unlink(missing_ok=True)
        if tmp.is_dir():
            tmp.rmdir()

print("Eval cases (tests/evals/)")
evals_dir = ROOT / "tests" / "evals"
check(evals_dir.is_dir(), "tests/evals/ present",
      "the eval fixtures scripts/run_eval.py scores against")
case_dirs = sorted(d for d in evals_dir.iterdir()
                   if d.is_dir()) if evals_dir.is_dir() else []
check(len(case_dirs) >= EVAL_CASES_MIN,
      f"at least {EVAL_CASES_MIN} eval cases exist", f"found {len(case_dirs)}")
missing_required = REQUIRED_EVAL_CASES - {d.name for d in case_dirs}
check(not missing_required,
      "every required case (five archetypes + the mock-ui pipeline) exists",
      f"missing: {sorted(missing_required)}. Each one covers a layout shape the "
      "others do not, and the hard case covers the honesty path.")

for case_dir in case_dirs:
    name = case_dir.name
    # The input is one mockup.html, or (for the mock-ui pipeline) a mockup folder
    # with sitemap.json and one .html per screen, in the project layout.
    mock_folder = case_dir / "supersub" / "mockup"
    folder_case = (mock_folder / "sitemap.json").is_file()
    required = ("expectations.yaml", "notes.md")
    if not folder_case:
        required = ("mockup.html",) + required
    for filename in required:
        check((case_dir / filename).is_file(), f"{name}/{filename} present",
              "a case is a mockup (mockup.html, or supersub/mockup/ with a "
              "sitemap.json), its assertions, and a written reason to exist")

    inputs = ([case_dir / "mockup.html"] if not folder_case
              else sorted(mock_folder.glob("*.html")))
    if folder_case:
        check(len(inputs) >= 2, f"{name}/supersub/mockup/ holds screen files",
              "a mockup folder needs index.html and at least one screen file")
    for mockup in inputs:
        if not mockup.is_file():
            continue
        html = mockup.read_text(encoding="utf-8")
        # A case that needs the network scores differently on a machine without it.
        external = re.search(r"""(?:src|href)\s*=\s*["'](?:https?:)?//""", html, re.I)
        imported = re.search(r"""@import\s+(?:url\()?['"]?(?:https?:)?//""", html, re.I)
        check(external is None and imported is None,
              f"{name}/{mockup.relative_to(case_dir).as_posix()} is self-contained",
              "it pulls an external asset; a fixture that needs the network is not "
              "a fixture")

    spec_path = case_dir / "expectations.yaml"
    if not spec_path.is_file():
        continue
    try:
        spec = yaml.safe_load(spec_path.read_text(encoding="utf-8-sig")) or {}
        check(isinstance(spec, dict), f"{name}/expectations.yaml is a mapping")
    except yaml.YAMLError as e:
        check(False, f"{name}/expectations.yaml parses", str(e))
        continue
    if not isinstance(spec, dict):
        continue

    asserted = [b for b in EVAL_ASSERTION_BLOCKS if b in spec]
    check(len(asserted) >= 3,
          f"{name}/expectations.yaml asserts something worth running",
          f"only {asserted}. A case with one or two blocks is not measuring enough "
          "to tell a good conversion from a bad one.")

    # Every waiver has to say why. A deviation nobody can read is indistinguishable
    # from a bug that was never fixed.
    ref = spec.get("reference") or {}
    for entry in ref.get("known_deviations") or []:
        label = (entry or {}).get("check", "<unnamed>")
        check(bool((entry or {}).get("check")) and bool((entry or {}).get("reason")),
              f"{name} known deviation {label} states a reason",
              "a waiver without a stated reason hides a regression")
    if ref.get("output"):
        target = (case_dir / ref["output"]).resolve()
        check(target.is_file(), f"{name} reference output exists",
              f"{ref['output']} does not resolve to a file")

    # The hard case must assert effects controls.yaml actually takes a position on.
    if "limitations" in spec and isinstance(catalog, dict):
        known_ids = {e.get("id") for e in (catalog.get("impossible_css") or [])}
        for entry in spec["limitations"].get("declared") or []:
            eid = (entry or {}).get("id")
            check(eid in known_ids,
                  f"{name} limitation {eid!r} is in controls.yaml's impossible_css",
                  "asserting an effect the catalog takes no position on means the "
                  "case and the skill disagree about what is impossible")

# The acceptance criterion, run rather than asserted: the scorer must score the
# bundled examples against their matching cases without crashing.
if case_dirs:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_eval.py"), "--json"],
        capture_output=True, text=True, cwd=str(ROOT))
    payload = None
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        pass
    check(proc.returncode in (0, 1) and payload is not None,
          "run_eval.py scores the bundled references without crashing",
          f"exit {proc.returncode}: {proc.stderr.strip()[:300]}")
    if payload:
        scored = {r["case"] for r in payload["results"]}
        check(len(scored) >= 3,
              "at least three cases carry a reference output",
              f"scored: {sorted(scored)}")
        bad = [(r["case"], row["check"], row["result"])
               for r in payload["results"] for row in r["rows"]
               if row["result"] in ("FAIL", "XPASS")]
        check(not bad, "the eval self-check is clean",
              f"{bad[:4]} -- an XPASS means a known deviation is stale and its "
              "waiver should be deleted; a FAIL means the references drifted.")
    check((ROOT / "docs" / "evals.md").is_file(), "docs/evals.md present",
          "the manual loop; the scorer is deliberately not wired to a model")
    evals_doc = (ROOT / "docs" / "evals.md")
    if evals_doc.is_file():
        text = evals_doc.read_text(encoding="utf-8")
        check("CI does not run a model" in text,
              "docs/evals.md states the boundary",
              "the one thing a reader must not get wrong is that the scored half "
              "and the generated half are different halves")

print("Shared files (scripts/sync_shared.py --check)")
proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "sync_shared.py"), "--check"],
                      capture_output=True, text=True, cwd=str(ROOT))
check(proc.returncode == 0, "every skill's references/shared/ copy matches shared/",
      proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else proc.stderr.strip())

print("design-md")
DM_DIR = ROOT / "skills" / "design-md"
DM_LINT = DM_DIR / "scripts" / "design_lint.py"
for rel in ("references/format.md", "references/section-guide.md",
            "references/interview.md", "references/shared/handoff.md",
            "references/shared/powerapps-profile.md", "assets/DESIGN.template.md",
            "assets/example/DESIGN.md", "scripts/design_lint.py"):
    check((DM_DIR / rel).is_file(), f"skills/design-md/{rel} present")


def dm_lint(path: Path, *extra: str):
    proc = subprocess.run([sys.executable, str(DM_LINT), str(path), "--json", *extra],
                          capture_output=True, text=True, cwd=str(ROOT))
    try:
        return proc.returncode, json.loads(proc.stdout)["files"][0]
    except (json.JSONDecodeError, KeyError, IndexError):
        return proc.returncode, {"findings": [], "errors": -1,
                                 "verdict": proc.stderr.strip()[:200]}


if DM_LINT.is_file():
    code, report = dm_lint(DM_DIR / "assets" / "example" / "DESIGN.md")
    check(code == 0 and report["errors"] == 0 and not report["findings"],
          "assets/example/DESIGN.md lints clean (no errors, no warnings)",
          f"{report['verdict']}: "
          + ", ".join(sorted({f['check'] for f in report['findings']})))
    code, report = dm_lint(DM_DIR / "assets" / "DESIGN.template.md")
    check(report["errors"] == 0, "assets/DESIGN.template.md lints without errors",
          report["verdict"])
    check(not any(f["check"] == "section-missing" for f in report["findings"]),
          "assets/DESIGN.template.md has all eleven sections")
# The owner's reference DESIGN.md analyses a real company's brand: it must never ship
# inside a skill or the test suite.
leaked = [p.relative_to(ROOT).as_posix()
          for base in (ROOT / "skills", ROOT / "tests") if base.is_dir()
          for p in base.rglob("*") if p.is_file() and "apple" in p.name.lower()]
check(not leaked, "no collection DESIGN.md is bundled in skills/ or tests/",
      f"found: {leaked}")
briefs = sorted((ROOT / "tests" / "briefs" / "design-md").glob("*.md"))
check(len(briefs) >= 3, "tests/briefs/design-md/ holds at least three briefs",
      f"found {len(briefs)}")

print("mock-ui")
MU_DIR = ROOT / "skills" / "mock-ui"
MU_LINT = MU_DIR / "scripts" / "mock_lint.py"
MU_EXAMPLE = MU_DIR / "assets" / "example"
for rel in ("references/html-contract.md", "references/screen-patterns.md",
            "references/shared/handoff.md", "references/shared/powerapps-profile.md",
            "assets/page.template.html", "assets/index.template.html",
            "assets/sitemap.schema.json", "assets/example/index.html",
            "assets/example/sitemap.json", "scripts/tokens_to_css.py",
            "scripts/mock_lint.py"):
    check((MU_DIR / rel).is_file(), f"skills/mock-ui/{rel} present")
mu_skill = MU_DIR / "SKILL.md"
if mu_skill.is_file():
    mu_text = mu_skill.read_text(encoding="utf-8")
    mu_fm = skill_checks.read_frontmatter(mu_skill, yaml) or {}
    mu_desc = str(mu_fm.get("description") or "").lower()
    # The phrases the skill has to fire on, and the two neighbours it must hand off to
    # rather than imitate.
    for phrase in ("mockup", "wireframe", "prototype the screens",
                   "html pages from this design", "design-md", "create-app"):
        check(phrase in mu_desc, f"mock-ui description mentions {phrase!r}")
    for needle, label in (("## The workflow", "the ordered workflow"),
                          ("Screen inventory", "the inventory-before-HTML step"),
                          ("tokens_to_css.py", "the token step"),
                          ("mock_lint.py", "the lint step"),
                          ("html-contract.md", "a pointer to the contract"),
                          ("screen-patterns.md", "a pointer to the patterns"),
                          ("every screen in full", "the no-abbreviation rule"),
                          ("create-list", "the create-list hand-off"),
                          ("create-flow", "the create-flow hand-off")):
        check(needle in mu_text, f"mock-ui SKILL.md still contains {label}",
              f"missing {needle!r}")
if MU_LINT.is_file() and (MU_EXAMPLE / "sitemap.json").is_file():
    # The bundled example must lint clean for the target its own sitemap declares, with
    # the drift check against the DESIGN.md it was generated from.
    mu_map = json.loads((MU_EXAMPLE / "sitemap.json").read_text(encoding="utf-8"))
    mu_args = [sys.executable, str(MU_LINT), str(MU_EXAMPLE), "--json", "--strict"]
    if mu_map.get("design"):
        mu_args += ["--design", str(MU_EXAMPLE / mu_map["design"])]
    proc = subprocess.run(mu_args, capture_output=True, text=True, cwd=str(ROOT))
    try:
        mu_report = json.loads(proc.stdout)["report"]
    except (json.JSONDecodeError, KeyError):
        mu_report = {"verdict_code": None, "verdict": proc.stderr.strip()[:200],
                     "findings": [], "target": None}
    check(proc.returncode == 0 and mu_report["verdict_code"] == "safe",
          f"assets/example/ lints clean for its declared target "
          f"({mu_map.get('target')})",
          f"{mu_report['verdict']}: "
          + ", ".join(sorted({f['check'] for f in mu_report['findings']})))
    check(mu_report.get("target") == mu_map.get("target"),
          "mock_lint.py read the target from the example's sitemap.json")
    if mu_map.get("design") and DM_LINT.is_file():
        code, report = dm_lint(MU_EXAMPLE / mu_map["design"], "--target",
                               mu_map.get("target", "web"),
                               "--profile", str(ROOT / "shared" / "powerapps-profile.md"))
        check(report["errors"] == 0 and not report["findings"],
              "the example's DESIGN.md lints clean with design-md's linter",
              f"{report['verdict']}")

print("create-list")
CL_DIR = ROOT / "skills" / "create-list"
CL_LINT = CL_DIR / "scripts" / "list_lint.py"
for rel in ("references/import-behavior.md", "references/column-types.md",
            "references/naming.md", "references/shared/handoff.md",
            "assets/list.schema.json", "assets/type-probe.list.json",
            "assets/example/Holidays.list.json", "scripts/list_lint.py",
            "scripts/build_list.py"):
    check((CL_DIR / rel).is_file(), f"skills/create-list/{rel} present")
check((ROOT / "tests" / "fixtures" / "lists" / "reference-holidays.xlsx").is_file(),
      "tests/fixtures/lists/reference-holidays.xlsx present",
      "the owner's reference workbook the build is compared with")
cl_skill = CL_DIR / "SKILL.md"
if cl_skill.is_file():
    cl_text = cl_skill.read_text(encoding="utf-8")
    cl_desc = str((skill_checks.read_frontmatter(cl_skill, yaml) or {})
                  .get("description") or "").lower()
    # The phrases the skill has to fire on, and the two neighbours it must name as the
    # skills that do what it does not.
    for phrase in ("sharepoint list", "design the list", "which columns", "from excel",
                   "csv", "not for building flows", "create-flow", "create-app"):
        check(phrase in cl_desc, f"create-list description mentions {phrase!r}")
    for needle, label in (("## The workflow", "the ordered workflow"),
                          ("lists.md", "the design-before-build step"),
                          ("list_lint.py", "the lint step"),
                          ("build_list.py", "the build step"),
                          ("VERIFIED", "the reopen-and-verify step"),
                          ("import-behavior.md", "a pointer to the evidence table"),
                          ("column-types.md", "a pointer to the type table"),
                          ("naming.md", "a pointer to the naming rule"),
                          ("unverified-behavior", "the unverified-assumption rule"),
                          ("create-app", "the create-app hand-off"),
                          ("create-flow", "the create-flow hand-off")):
        check(needle in cl_text, f"create-list SKILL.md still contains {label}",
              f"missing {needle!r}")
if CL_LINT.is_file():
    _spec = importlib.util.spec_from_file_location("list_lint", CL_LINT)
    cl_mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(cl_mod)
    evidence = cl_mod.load_evidence()
    types = cl_mod.load_types()
    bad_levels = sorted(k for k, v in evidence.items() if v["level"] not in cl_mod.LEVELS)
    check(evidence and not bad_levels, "every evidence row has a declared level",
          f"bad: {bad_levels}")
    undated = sorted(k for k, v in evidence.items()
                     if v["level"] == "import-tested" and not re.match(r"\d{4}-\d{2}-\d{2}",
                                                                      v["date"]))
    check(not undated, "every import-tested row carries a date", f"undated: {undated}")
    # The six open questions of the phase brief. Each must stay a row of its own, so
    # that settling one is an edit to one row.
    for row_id in ("offer-person", "offer-hyperlink", "title-mapping", "empty-table",
                   "csv-encoding", "choice-from-data", "internal-name"):
        check(row_id in evidence, f"evidence table has row {row_id!r}")
    imports = sorted({i for t in types.values() for i in t["imports"]} - {"skip"})
    no_row = [i for i in imports if f"offer-{i}" not in evidence]
    check(types and not no_row, "every importType has an offer-<type> evidence row",
          f"missing: {no_row}")
    cl_schema = json.loads((CL_DIR / "assets" / "list.schema.json").read_text(encoding="utf-8"))
    col_props = cl_schema["$defs"]["column"]["properties"]
    check(sorted(col_props["finalType"]["enum"]) == sorted(types),
          "list.schema.json finalType enum equals the type table")
    check(sorted(col_props["importType"]["enum"]) == sorted(imports + ["skip"]),
          "list.schema.json importType enum equals the type table")
    for rel, fmt in (("assets/example/Holidays.list.json", "xlsx"),
                     ("assets/example/Holidays.list.json", "csv"),
                     ("assets/type-probe.list.json", "xlsx"),
                     ("assets/type-probe.list.json", "csv")):
        rep = cl_mod.lint_files([CL_DIR / rel], fmt)
        others = sorted({f["check"] for f in rep["findings"]} - {"unverified-behavior"})
        check(rep["errors"] == 0 and not others,
              f"{rel} lints with no finding but unverified-behavior ({fmt})",
              f"{rep['verdict']}: {others}")

print("create-flow")
CF_DIR = ROOT / "skills" / "create-flow"
CF_LINT = CF_DIR / "scripts" / "flow_lint.py"
for rel in ("references/connectors.yaml", "references/package-format.md",
            "references/flow-md-template.md", "references/import-and-fix.md",
            "references/shared/handoff.md", "assets/flow.schema.json",
            "assets/example/SendTestEmail.flow.json",
            "assets/reference-package/manifest.json",
            "assets/reference-package/Microsoft.Flow/flows/manifest.json",
            "scripts/flow_lint.py", "scripts/build_flow_package.py",
            "scripts/harvest_flow.py"):
    check((CF_DIR / rel).is_file(), f"skills/create-flow/{rel} present")
check((ROOT / "tests" / "fixtures" / "flows" / "reference-package.zip").is_file(),
      "tests/fixtures/flows/reference-package.zip present",
      "the owner's reference package the round-trip test compares with")
# The owner's reference held a connection id from a real environment. The shipped and
# test copies carry a dummy in its place; the real one must never come back.
leaked = [p.relative_to(ROOT).as_posix()
          for base in (ROOT / "skills", ROOT / "tests") if base.is_dir()
          for p in base.rglob("*") if p.is_file() and b"a8e246ea" in p.read_bytes()]
check(not leaked, "the reference's real connection id is in no shipped or test file",
      f"found in: {leaked}")
cf_skill = CF_DIR / "SKILL.md"
if cf_skill.is_file():
    cf_text = cf_skill.read_text(encoding="utf-8")
    cf_desc = str((skill_checks.read_frontmatter(cf_skill, yaml) or {})
                  .get("description") or "").lower()
    # The phrases the skill has to fire on, and the neighbours it must name as the
    # skills that do what it does not.
    for phrase in ("power automate", "flow", "automate this process", "import package",
                   "does not create lists or", "create-list", "create-app"):
        check(phrase in cf_desc, f"create-flow description mentions {phrase!r}")
    for needle, label in (("## The workflow", "the ordered workflow"),
                          ("flow.md", "the plan-before-build step"),
                          ("Build nothing until the user agrees", "the stop after flow.md"),
                          ("flow_lint.py", "the lint step"),
                          ("build_flow_package.py", "the build step"),
                          ("VERIFIED", "the reopen-and-verify step"),
                          ("WILL FAIL", "the never-hand-over rule"),
                          ("harvest_flow.py", "the harvest offer"),
                          ("unverified-step", "the unverified-step rule"),
                          ("never embedded", "the connection rule"),
                          ("create-app", "the create-app hand-off"),
                          ("create-list", "the create-list hand-off")):
        check(needle in cf_text, f"create-flow SKILL.md still contains {label}",
              f"missing {needle!r}")
if CF_LINT.is_file():
    _spec = importlib.util.spec_from_file_location("flow_lint", CF_LINT)
    cf_mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(cf_mod)
    catalog, why = cf_mod.load_catalog()
    check(catalog is not None, "references/connectors.yaml loads", why)
    if catalog is not None:
        entries = [("package", catalog.get("package")),
                   ("package_connection_reference",
                    catalog.get("package_connection_reference"))]
        for api, c in catalog["connectors"].items():
            entries.append((f"connector {api}", c))
            for op, o in (c.get("operations") or {}).items():
                entries.append((f"operation {api}/{op}", o))
                entries += [(f"parameter {api}/{op} {k}", {"evidence": v, "source":
                             o.get("source", "")})
                            for k, v in (o.get("parameters") or {}).items()]
            check(bool(c.get("display_name")), f"connector {api} has a display_name")
        entries += [(f"trigger {k}", t) for k, t in catalog["triggers"].items()]
        entries += [(f"action type {k}", a) for k, a in catalog["actions"].items()]
        bad = [n for n, e in entries
               if not isinstance(e, dict) or e.get("evidence") not in cf_mod.LEVELS]
        check(not bad, "every catalog entry has a declared evidence level", f"bad: {bad}")
        undated = [n for n, e in entries if isinstance(e, dict)
                   and e.get("evidence") == "import-tested"
                   and not re.search(r"\d{4}-\d{2}-\d{2}", str(e.get("source", "")))]
        check(not undated, "every import-tested catalog entry cites a date",
              f"undated: {undated}")
        check(isinstance(catalog.get("unattempted"), dict),
              "the catalog lists what is unattempted")
    rep = cf_mod.lint_files([CF_DIR / "assets" / "example" / "SendTestEmail.flow.json"])
    others = sorted({f["check"] for f in rep["findings"]} - {"unverified-step"})
    check(rep["errors"] == 0 and not others,
          "assets/example/SendTestEmail.flow.json lints with no finding but unverified-step",
          f"{rep['verdict']}: {others}")
    _spec = importlib.util.spec_from_file_location(
        "build_flow_package", CF_DIR / "scripts" / "build_flow_package.py")
    cf_build = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(cf_build)
    problems = cf_build.verify_package(ROOT / "tests" / "fixtures" / "flows" /
                                       "reference-package.zip")
    check(not problems, "the reference package passes the builder's verification",
          "; ".join(problems))

print("Cross-skill consistency")
SKILL_NAMES = [d.name for d in skill_checks.skill_dirs(ROOT)]
VERDICT_CODES = ("safe", "unverified", "will_fail", "unproven")
# One verdict vocabulary: every linter can end in each of the four codes.
for lint_py in sorted((ROOT / "skills").glob("*/scripts/*_lint.py")):
    src = lint_py.read_text(encoding="utf-8")
    missing = [c for c in VERDICT_CODES if f'"{c}"' not in src]
    check(not missing, f"{lint_py.relative_to(ROOT).as_posix()} uses the four verdict codes",
          f"missing {missing}; shared/handoff.md, 'Verdicts'")


def verdict_codes(payload) -> list[str]:
    found: list[str] = []
    if isinstance(payload, dict):
        for k, v in payload.items():
            if k == "verdict_code" and isinstance(v, str):
                found.append(v)
            else:
                found += verdict_codes(v)
    elif isinstance(payload, list):
        for v in payload:
            found += verdict_codes(v)
    return found


# Every bundled example passes its own linter: no error, and every check ran.
EXAMPLE_LINTS = [
    ("create-app", ["scripts/pa_lint.py", *sorted(
        p.relative_to(ROOT / "skills" / "create-app").as_posix()
        for p in (ROOT / "skills" / "create-app" / "assets" / "examples").glob("*.yaml"))]),
    ("design-md", ["scripts/design_lint.py", "assets/example/DESIGN.md"]),
    ("mock-ui", ["scripts/mock_lint.py", "assets/example", "--design",
                 "assets/example/DESIGN.md"]),
    ("create-list", ["scripts/list_lint.py", "assets/example"]),
    ("create-flow", ["scripts/flow_lint.py", "assets/example"]),
]
for skill, args in EXAMPLE_LINTS:
    sdir = ROOT / "skills" / skill
    proc = subprocess.run([sys.executable, str(sdir / args[0]), *args[1:], "--json"],
                          capture_output=True, text=True, cwd=str(sdir))
    try:
        got = verdict_codes(json.loads(proc.stdout))
    except json.JSONDecodeError:
        got = []
    check(bool(got) and all(c in ("safe", "unverified") for c in got),
          f"{skill}: every bundled example passes its own linter", f"verdicts: {got}")

# Identifier rules agree wherever they are written down (shared/handoff.md, "Names").
_mu_src = (ROOT / "skills" / "mock-ui" / "scripts" / "mock_lint.py").read_text(encoding="utf-8")
_cl_src = (ROOT / "skills" / "create-list" / "scripts" / "list_lint.py").read_text(encoding="utf-8")
_sm_schema = json.loads((ROOT / "skills" / "mock-ui" / "assets" / "sitemap.schema.json")
                        .read_text(encoding="utf-8"))
_fl_schema = json.loads((ROOT / "skills" / "create-flow" / "assets" / "flow.schema.json")
                        .read_text(encoding="utf-8"))


def _regex(src: str, var: str) -> str | None:
    m = re.search(rf'^{var} = re\.compile\(r"([^"]+)"\)', src, re.M)
    return m.group(1) if m else None


_name_mu, _name_cl = _regex(_mu_src, "NAME_RE"), _regex(_cl_src, "NAME_RE")
check(_name_mu is not None and _name_mu == _name_cl
      == _sm_schema["$defs"]["internalName"]["pattern"],
      "list and column name rule is one rule (mock_lint, list_lint, sitemap schema)",
      f"{_name_mu!r} / {_name_cl!r} / {_sm_schema['$defs']['internalName']['pattern']!r}")
check(_regex(_mu_src, "SCREEN_RE") == _sm_schema["$defs"]["screenId"]["pattern"],
      "screen id rule is one rule (mock_lint, sitemap schema)")
_flow_pat = _fl_schema["properties"]["name"]["pattern"]
check(all(bool(re.match(_flow_pat, n)) == bool(re.match(_name_mu or "$^", n))
          for n in ("NotifyApprover", "A", "notify", "Notify_Approver", "Notify2")),
      "flow names follow the same PascalCase rule as run-flow:<Name> objects",
      f"flow.schema.json name pattern {_flow_pat!r}")

# The trigger matrix: at least fifteen rows, English and Thai, one real owner each.
tm = ROOT / "docs" / "trigger-matrix.md"
check(tm.is_file(), "docs/trigger-matrix.md present")
if tm.is_file():
    rows = re.findall(r"^\| (\d+) \| (.+?) \| `?([a-z-]+)`? \|", tm.read_text(encoding="utf-8"),
                      re.M)
    owners = [o for _, _, o in rows]
    check(len(rows) >= 15, "trigger matrix has at least fifteen messages", f"{len(rows)}")
    check(all(o in SKILL_NAMES + ["none"] for o in owners),
          "every trigger-matrix owner is a skill or 'none'",
          f"{sorted(set(owners) - set(SKILL_NAMES) - {'none'})}")
    check(set(SKILL_NAMES) <= set(owners), "every skill owns at least one message",
          f"no row for {sorted(set(SKILL_NAMES) - set(owners))}")
    thai = [m for _, m, _ in rows if re.search(r"[\u0e00-\u0e7f]", m)]
    check(len(thai) >= 5, "trigger matrix mixes English and Thai (at least five Thai)",
          f"{len(thai)} Thai rows")

# The release test plan: every unverified item from phases 02-06 exactly once.
rtp = ROOT / "docs" / "release-test-plan.md"
check(rtp.is_file(), "docs/release-test-plan.md present")
if rtp.is_file():
    rtp_text = rtp.read_text(encoding="utf-8")
    plan_text = (ROOT / "docs" / "test-plan.md").read_text(encoding="utf-8")
    ids = sorted(set(re.findall(r"^\| ((?:B|U|M|P|F)\d+[a-z]?) \|", plan_text, re.M)))
    ids += ["T1", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "K1", "K2", "K3",
            "E0", "E1", "E2", "E3", "E4", "R0", "P1", "P2", "S1"]
    for item in sorted(set(ids)):
        n = len(re.findall(rf"^\| \[ \] \| {re.escape(item)} \|", rtp_text, re.M))
        check(n == 1, f"release test plan has item {item} exactly once", f"found {n}")
    ib = (ROOT / "skills" / "create-list" / "references" / "import-behavior.md").read_text(
        encoding="utf-8")
    unverified = re.findall(r"^\| `([a-z-]+)` \|[^|]*\| unverified \|", ib, re.M)
    cf_catalog = yaml.safe_load((ROOT / "skills" / "create-flow" / "references" /
                                 "connectors.yaml").read_text(encoding="utf-8"))
    unverified += [k for k, v in cf_catalog.items()
                   if isinstance(v, dict) and v.get("evidence") == "unverified"]
    check(bool(unverified), "found the unverified evidence rows to look for")
    for row in unverified:
        n = rtp_text.count(f"`{row}`")
        check(n == 1, f"release test plan names unverified row `{row}` exactly once",
              f"found {n}")

# The end-to-end scenario and the README's section per skill.
for rel in ("tests/e2e/leave-request/DESIGN.md", "tests/e2e/leave-request/brief.md",
            "docs/e2e-walkthrough.md", "docs/create-app.md", "scripts/package_plugin.py"):
    check((ROOT / rel).is_file(), f"{rel} present")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
for name in SKILL_NAMES:
    check(f"### `{name}`" in readme, f"README.md has a section for {name}")
check("## What it cannot do" in readme, "README.md says what the plugin cannot do")
check("/dist/" in (ROOT / ".gitignore").read_text(encoding="utf-8"),
      ".gitignore ignores dist/", "package_plugin.py writes there")

print("Plugin metadata")
plugin_json = ROOT / ".claude-plugin" / "plugin.json"
market_json = ROOT / ".claude-plugin" / "marketplace.json"
plugin = market = None
try:
    plugin = json.loads(plugin_json.read_text(encoding="utf-8"))
    check(True, "plugin.json is valid JSON")
except (OSError, json.JSONDecodeError) as e:
    check(False, "plugin.json is valid JSON", str(e))
try:
    market = json.loads(market_json.read_text(encoding="utf-8"))
    check(True, "marketplace.json is valid JSON")
except (OSError, json.JSONDecodeError) as e:
    check(False, "marketplace.json is valid JSON", str(e))

if plugin:
    check(bool(re.match(r"^\d+\.\d+\.\d+$", str(plugin.get("version", "")))),
          "plugin.json version is SemVer", f"got {plugin.get('version')!r}")
if plugin and market:
    names = [p.get("name") for p in market.get("plugins", [])]
    check(plugin.get("name") in names,
          "marketplace.json lists the plugin", f"plugins: {names}")

print("CHANGELOG mentions the current version")
if plugin:
    cl = (ROOT / "CHANGELOG.md")
    cl_text = cl.read_text(encoding="utf-8") if cl.is_file() else ""
    version = str(plugin.get("version"))
    if f"[{version}]" in cl_text:
        check(True, f"CHANGELOG.md has a section for {version}")
    else:
        # Between the version bump and the release, the entries sit under
        # [Unreleased]. Accept that only while the version is newer than every
        # released section, so a forgotten entry for an old version still fails.
        def _v(s: str) -> tuple[int, ...]:
            return tuple(int(x) for x in s.split("."))
        released = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", cl_text, re.M)
        newer = bool(re.match(r"^\d+\.\d+\.\d+$", version)) and all(
            _v(version) > _v(r) for r in released)
        check("## [Unreleased]" in cl_text and newer,
              f"CHANGELOG.md has a section for {version}, or it is pending under "
              "[Unreleased]",
              f"no [{version}] section, and either [Unreleased] is missing or "
              f"{version} is not newer than {released[:1]}")

print("Privacy guard (see CONTRIBUTING.md)")
_term_hits, _shape_hits = privacy_check.run(ROOT)
if privacy_check.load_terms(ROOT) is None:
    check(True, privacy_check.SKIP_MESSAGE)
else:
    check(not _term_hits, "no private term in any tracked file or file name",
          "; ".join(_term_hits[:10]))
check(not _shape_hits,
      "no stray e-mail address, tenant host or home path in any tracked file",
      "; ".join(_shape_hits[:10]))

print("Internal Markdown links resolve")
md_files = [p for p in ROOT.rglob("*.md") if ".git" not in p.parts]
link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
for md in md_files:
    for target in link_re.findall(md.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path_part = target.split("#", 1)[0]
        if not path_part:
            continue
        resolved = (md.parent / path_part).resolve()
        check(resolved.exists(),
              f"link in {md.relative_to(ROOT).as_posix()} -> {target}")

print()
if errors:
    print(f"{len(errors)} of {checks} checks FAILED")
    sys.exit(1)
print(f"All {checks} checks passed")
