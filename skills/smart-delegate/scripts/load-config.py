#!/usr/bin/env python3
"""Print the active Smart Delegate configuration with YAML comments removed.

Lookup order (first file found wins, no merging):
  1. ./.smart-delegate/config.yaml
  2. ~/.config/smart-delegate/config.yaml
  3. ../config.yaml next to this script (bundled defaults)

Only full-line comments are removed. Lines inside block scalars (`|` or `>`) are kept verbatim,
including lines that start with `#`. Standard library only.
"""
import os
import re
import sys

BLOCK_START = re.compile(r"^(\s*)(?:-\s+)?[^\s#][^:]*:\s*[|>][+-]?\d*\s*$|^(\s*)-\s*[|>][+-]?\d*\s*$")


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


if __name__ == "__main__":
    sys.exit(main())
