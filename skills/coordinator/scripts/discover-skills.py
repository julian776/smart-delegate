#!/usr/bin/env python3
"""Discover project and user skills without loading their bodies.

Scans the skill roots a host uses, reads only YAML frontmatter, and prints a capability catalog:
name, description, declared Smart Delegate type, capabilities, and location. Unregistered and
malformed skills are listed with a warning; discovery never fails an execution because one skill
has bad metadata.

Lookup roots (project first): `./.agents/skills`, `./.claude/skills`, `./.opencode/skills`,
`./.cursor/skills`, `~/.agents/skills`, `~/.claude/skills`, `~/.config/opencode/skills`, then
`SMART_DELEGATE_SKILL_PATHS` (colon separated), then each `--path`. A `--path` that is itself a
skill directory is scanned as one skill.

Standard library only. Exit 0 even when nothing is found.
"""
import argparse
import json
import os
import re
import sys

VALID_TYPES = ("operation", "verification")
TRUE_VALUES = ("true", "yes", "1")


def unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    match = re.match(r"^(.*?)\s+#\s.*$", value)
    if match:
        return match.group(1).strip()
    return value


def parse_yaml_subset(text):
    """Parse the small mapping subset skills use: scalars, nested maps, `|` and `>` blocks."""
    root = {}
    stack = [(-1, root)]
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue
        if ":" not in stripped or stripped.startswith("- "):
            index += 1
            continue
        indent = len(raw) - len(raw.lstrip())
        key, _, value = stripped.partition(":")
        key = unquote(key.strip())
        value = value.strip()
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value[:1] in ("|", ">"):
            folded = value.startswith(">")
            block = []
            block_indent = None
            index += 1
            while index < len(lines):
                line = lines[index]
                line_indent = len(line) - len(line.lstrip())
                if line.strip() and line_indent <= indent:
                    break
                if block_indent is None and line.strip():
                    block_indent = line_indent
                if block_indent is not None and len(line) >= block_indent:
                    block.append(line[block_indent:])
                else:
                    block.append("")
                index += 1
            text_block = (" " if folded else "\n").join(
                part.strip() if folded else part for part in block
            ).strip()
            parent[key] = text_block
            continue
        if value == "":
            child = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = unquote(value)
        index += 1
    return root


def as_text(value):
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def read_frontmatter(path):
    """Read only up to the closing delimiter; the skill body is never loaded."""
    with open(path, encoding="utf-8") as handle:
        first = handle.readline()
        if first.strip() != "---":
            return None, "missing frontmatter"
        lines = []
        for line in handle:
            if line.strip() in ("---", "..."):
                return "\n".join(lines), ""
            lines.append(line.rstrip("\n"))
    return None, "unterminated frontmatter"


def read_skill(path):
    name = os.path.basename(os.path.dirname(path))
    warnings = []
    try:
        frontmatter, problem = read_frontmatter(path)
    except (OSError, UnicodeDecodeError) as error:
        return {
            "name": name, "description": "", "type": [], "capabilities": [],
            "location": path, "registered": False, "warnings": [f"unreadable: {error}"],
        }
    if frontmatter is None:
        warnings.append(problem)
        return {
            "name": name, "description": "", "type": [], "capabilities": [],
            "location": path, "registered": False, "warnings": warnings,
        }
    data = parse_yaml_subset(frontmatter)
    declared_name = as_text(data.get("name")).strip()
    if declared_name:
        name = declared_name
    else:
        warnings.append("missing name")
    description = " ".join(as_text(data.get("description")).split())
    if not description:
        warnings.append("missing description")
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
        if "metadata" in data:
            warnings.append("metadata is not a mapping")
    raw_types = [part.strip().lower() for part in as_text(metadata.get("smart-delegate-type")).split(",")]
    types = [part for part in raw_types if part in VALID_TYPES]
    for part in raw_types:
        if part and part not in VALID_TYPES:
            warnings.append(f"unknown smart-delegate-type {part!r}")
    capabilities = [part.strip() for part in as_text(metadata.get("smart-delegate-capabilities")).split(",") if part.strip()]
    marker = as_text(metadata.get("smart-delegate")).strip().lower()
    registered = marker in TRUE_VALUES
    if marker and not registered:
        warnings.append(f"smart-delegate marker is {marker!r}, not true")
    if registered and not types:
        warnings.append("registered without a valid smart-delegate-type")
    if registered and not capabilities:
        warnings.append("registered without capabilities")
    return {
        "name": name,
        "description": description,
        "type": types,
        "capabilities": capabilities,
        "location": os.path.abspath(path),
        "registered": registered,
        "warnings": warnings,
    }


def discover_roots(project, extra):
    project = os.path.abspath(project)
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(project, ".agents", "skills"),
        os.path.join(project, ".claude", "skills"),
        os.path.join(project, ".opencode", "skills"),
        os.path.join(project, ".cursor", "skills"),
        os.path.join(home, ".agents", "skills"),
        os.path.join(home, ".claude", "skills"),
        os.path.join(home, ".config", "opencode", "skills"),
    ]
    for raw in os.environ.get("SMART_DELEGATE_SKILL_PATHS", "").split(os.pathsep):
        if raw.strip():
            candidates.append(raw.strip())
    candidates.extend(extra or [])
    roots = []
    seen = set()
    for candidate in candidates:
        real = os.path.realpath(os.path.abspath(os.path.expanduser(candidate)))
        if real not in seen:
            seen.add(real)
            roots.append(real)
    return roots


def skill_files(roots):
    files = []
    seen = set()
    for root in roots:
        if not os.path.isdir(root):
            continue
        direct = os.path.join(root, "SKILL.md")
        paths = [direct] if os.path.isfile(direct) else []
        if not paths:
            try:
                children = sorted(os.listdir(root))
            except OSError:
                children = []
            for child in children:
                candidate = os.path.join(root, child, "SKILL.md")
                if os.path.isfile(candidate):
                    paths.append(candidate)
        for path in paths:
            real = os.path.realpath(path)
            if real not in seen:
                seen.add(real)
                files.append(path)
    return files


def catalog(project, extra, registered_only=False, wanted_types=None):
    roots = discover_roots(project, extra)
    skills = []
    seen = {}
    for path in skill_files(roots):
        skill = read_skill(path)
        key = skill["name"].lower()
        if key in seen:
            kept = seen[key]
            kept["warnings"].append(
                f"duplicate skill name; ignoring {skill['location']} (using {kept['location']})")
            continue
        seen[key] = skill
        skills.append(skill)
    if registered_only:
        skills = [skill for skill in skills if skill["registered"]]
    if wanted_types:
        skills = [skill for skill in skills if set(skill["type"]) & set(wanted_types)]
    skills.sort(key=lambda skill: (skill["name"].lower(), skill["location"]))
    warnings = []
    for skill in skills:
        for warning in skill["warnings"]:
            warnings.append(f"{skill['name']} ({skill['location']}): {warning}")
    return skills, warnings


def print_table(skills):
    if not skills:
        print("No skills found.")
        return
    print("| name | type | capabilities | description | location |")
    print("|------|------|--------------|-------------|----------|")
    for skill in skills:
        types = ",".join(skill["type"]) or ("unregistered" if not skill["registered"] else "?")
        description = skill["description"].replace("|", "\\|") or "-"
        print(f"| {skill['name']} | {types} | {','.join(skill['capabilities']) or '-'} | "
              f"{description} | {skill['location']} |")


def main():
    parser = argparse.ArgumentParser(description="Print a lightweight catalog of available skills.")
    parser.add_argument("--project", default=os.getcwd(), help="project root to scan (default cwd)")
    parser.add_argument("--path", action="append", help="extra skill root or skill directory")
    parser.add_argument("--registered", action="store_true", help="only Smart Delegate registered skills")
    parser.add_argument("--type", action="append", choices=VALID_TYPES, help="filter by declared type")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    parser.add_argument("--quiet", action="store_true", help="suppress metadata warnings")
    args = parser.parse_args()
    skills, warnings = catalog(args.project, args.path, args.registered, args.type)
    if args.json:
        print(json.dumps({"skills": skills, "warnings": warnings}, indent=2))
    else:
        print_table(skills)
        if warnings and not args.quiet:
            for warning in warnings:
                print(f"WARN {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
