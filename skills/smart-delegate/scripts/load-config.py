#!/usr/bin/env python3
"""Print the active Smart Delegate configuration with YAML comments removed.

Lookup order (first file found wins, no merging):
  1. ./.smart-delegate/config.yaml
  2. ~/.config/smart-delegate/config.yaml
  3. ../config.yaml next to this script (bundled defaults)

Only full-line comments are removed. Lines inside block scalars (`|` or `>`) are kept verbatim,
including lines that start with `#`. Standard library only.

Run with `--check` to validate the active configuration (YAML syntax, model titles, CLI
availability) and print a PASS/WARN report.
"""
import os
import re
import shutil
import sys

BLOCK_START = re.compile(r"^(\s*)(?:-\s+)?[^\s#][^:]*:\s*[|>][+-]?\d*\s*$|^(\s*)-\s*[|>][+-]?\d*\s*$")
CLI_RE = re.compile(r"(?<![\w./-])(claude|codex|opencode|gemini)(?![\w/-])")


def candidates():
    here = os.path.dirname(os.path.abspath(__file__))
    yield os.path.join(os.getcwd(), ".smart-delegate", "config.yaml")
    yield os.path.join(os.path.expanduser("~"), ".config", "smart-delegate", "config.yaml")
    yield os.path.join(here, "..", "config.yaml")


def strip_comments(text):
    out = []
    block_indent = None  # indent of the line that opened the current block scalar
    for line in text.splitlines():
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if block_indent is not None:
            if stripped == "" or indent > block_indent:
                out.append(line.rstrip())
                continue
            block_indent = None
        if stripped.startswith("#"):
            continue
        out.append(line.rstrip())
        m = BLOCK_START.match(line)
        if m:
            block_indent = indent
    # collapse runs of blank lines and trim the ends
    result = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
    return result


def main():
    for path in candidates():
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    body = strip_comments(f.read())
            except OSError as e:
                print(f"Smart Delegate configuration unreadable ({path}): {e}")
                return 0
            print(f"Smart Delegate configuration (source: {os.path.normpath(path)})")
            print(body if body else "(empty: route using models and tools available in the environment)")
            return 0
    print("No Smart Delegate configuration found: route using models and tools available in the environment.")
    return 0


def check():
    path = None
    for candidate in candidates():
        if os.path.isfile(candidate):
            path = candidate
            break
    if path is None:
        print("WARN no config found")
        return 1

    print(f"Smart Delegate config check (source: {os.path.normpath(path)})")

    try:
        import yaml
    except ImportError:
        print("WARN PyYAML not installed; cannot validate (pip install pyyaml)")
        return 1

    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as e:
        lines = str(e).splitlines()
        print(f"WARN yaml: {lines[0] if lines else e}")
        return 1
    print("PASS yaml: parsed")

    if data is None:
        data = {}
    if not isinstance(data, dict):
        print("WARN top level is not a mapping")
        return 1

    warnings = 0
    models = data.get("models", [])

    if not isinstance(models, list):
        print("WARN models: not a list")
        warnings += 1
    else:
        titled = True
        for i, entry in enumerate(models):
            title = entry.get("title") if isinstance(entry, dict) else None
            if not (isinstance(title, str) and title.strip()):
                print(f"WARN models[{i}]: missing title")
                warnings += 1
                titled = False
        if titled:
            print(f"PASS models: {len(models)} entries titled")

    invocations = []
    if isinstance(models, list):
        for entry in models:
            if isinstance(entry, dict):
                value = entry.get("invocation")
                if isinstance(value, str):
                    invocations.append(value)
    for section_name in ("review", "qa"):
        section = data.get(section_name)
        if isinstance(section, dict):
            value = section.get("invocation")
            if isinstance(value, str):
                invocations.append(value)

    sources = {}
    for source in invocations:
        for match in CLI_RE.finditer(source):
            name = match.group(1)
            if name not in sources:
                sources[name] = source

    for name in sorted(sources):
        exe = shutil.which(name)
        if exe:
            print(f"PASS cli: {name} ({exe})")
        else:
            print(f"WARN cli: {name} not on PATH ({sources[name]})")
            warnings += 1

    if warnings:
        print(f"Result: WARN ({warnings})")
        return 1
    print("Result: PASS")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(main())
    elif args == ["--check"]:
        sys.exit(check())
    else:
        print("usage: load-config.py [--check]", file=sys.stderr)
        sys.exit(2)
