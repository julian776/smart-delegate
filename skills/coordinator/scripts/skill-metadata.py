#!/usr/bin/env python3
"""Register or validate a project skill's Smart Delegate metadata.

`register` adds only the three discovery keys to an existing `SKILL.md` frontmatter. The skill
body, description, other metadata, and supporting files are left byte-for-byte unchanged.
Registration is a discovery operation, not certification.

    skill-metadata.py register skills/run-backtest/SKILL.md \
        --type operation --capabilities backtesting,simulation

`validate` checks name, description, and metadata shape. Use `--dry-run` to inspect the change.
Standard library only. Exit 0 on success/unchanged, 1 on validation failures, 2 on refusal.
"""
import argparse
import difflib
import importlib.util
import os
import re
import sys
import tempfile

KEYS = ("smart-delegate", "smart-delegate-type", "smart-delegate-capabilities")
KEY_RE = re.compile(r"^(?P<indent>\s+)(?P<key>smart-delegate(?:-type|-capabilities)?)\s*:\s*(?P<value>.*?)\s*$")


def load_discovery():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "discover-skills.py")
    spec = importlib.util.spec_from_file_location("smart_delegate_discover", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def split_document(text):
    """Return (opening, frontmatter_lines, rest) or raise ValueError."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("file must start with a '---' frontmatter block")
    for index in range(1, len(lines)):
        if lines[index].strip() in ("---", "..."):
            return lines[0], lines[1:index], lines[index:]
    raise ValueError("frontmatter block is not closed with '---'")


def metadata_bounds(front):
    """Return (start, end) line indexes of the top-level metadata block, or None."""
    start = None
    for index, line in enumerate(front):
        if re.match(r"^metadata\s*:", line):
            start = index
            break
    if start is None:
        return None
    if front[start].split(":", 1)[1].strip() not in ("", "#"):
        raise ValueError("inline metadata mapping is not supported; make it a block mapping")
    end = start + 1
    while end < len(front) and (not front[end].strip() or front[end][:1] in (" ", "\t")):
        end += 1
    return start, end


def current_values(front, bounds):
    values = {}
    start, end = bounds
    for line in front[start + 1:end]:
        match = KEY_RE.match(line)
        if match:
            values[match.group("key")] = match.group("value").strip().strip("\"'")
    return values


def desired_values(args):
    types = [part.strip() for part in args.type.split(",") if part.strip()]
    bad = [part for part in types if part not in ("operation", "verification")]
    if not types or bad:
        raise ValueError("--type must contain operation, verification, or both")
    capabilities = [part.strip() for part in args.capabilities.split(",") if part.strip()]
    if not capabilities:
        raise ValueError("--capabilities needs at least one keyword")
    return {
        "smart-delegate": "true",
        "smart-delegate-type": ",".join(types),
        "smart-delegate-capabilities": ",".join(capabilities),
    }


def render_line(indent, key, value):
    return f'{indent}{key}: "{value}"\n'


def register_text(text, args):
    opening, front, rest = split_document(text)
    newline = "\r\n" if opening.endswith("\r\n") else "\n"
    if newline == "\r\n":
        front = [line[:-2] + "\n" if line.endswith("\r\n") else line for line in front]
        rest = [line[:-2] + "\n" if line.endswith("\r\n") else line for line in rest]
        opening = opening[:-2] + "\n"
    joined = "".join(front)
    if not re.search(r"^name\s*:\s*\S", joined, re.MULTILINE):
        raise ValueError("frontmatter needs a non-empty name")
    if not re.search(r"^description\s*:", joined, re.MULTILINE):
        raise ValueError("frontmatter needs a description")
    wanted = desired_values(args)
    bounds = metadata_bounds(front)
    if bounds is not None:
        existing = current_values(front, bounds)
        if all(existing.get(key) == wanted[key] for key in KEYS):
            return text
    if bounds is None:
        front = front + ["metadata:\n"] + [render_line("  ", key, wanted[key]) for key in KEYS]
    else:
        start, end = bounds
        existing = current_values(front, bounds)
        conflicts = {key: value for key, value in existing.items() if value != wanted.get(key)}
        if conflicts and not args.force:
            detail = ", ".join(f"{key}={value!r}" for key, value in conflicts.items())
            raise ValueError(f"existing metadata differs ({detail}); pass --force to update it")
        replaced = set()
        for index in range(start + 1, end):
            match = KEY_RE.match(front[index])
            if not match:
                continue
            key = match.group("key")
            front[index] = render_line(match.group("indent"), key, wanted[key])
            replaced.add(key)
        missing = [key for key in KEYS if key not in replaced]
        if missing:
            insert_at = end
            front[insert_at:insert_at] = [render_line("  ", key, wanted[key]) for key in missing]
    if newline == "\r\n":
        result = opening.replace("\n", "\r\n") + "".join(front).replace("\n", "\r\n") + "".join(rest).replace("\n", "\r\n")
    else:
        result = opening + "".join(front) + "".join(rest)
    return result


def cmd_register(args):
    try:
        with open(args.path, encoding="utf-8", newline="") as handle:
            text = handle.read()
    except OSError as error:
        print(f"FAIL {args.path}: {error}", file=sys.stderr)
        return 2
    if text.startswith("\ufeff"):
        print(f"FAIL {args.path}: UTF-8 BOM is not supported; save as plain UTF-8", file=sys.stderr)
        return 2
    try:
        updated = register_text(text, args)
    except ValueError as error:
        print(f"FAIL {args.path}: {error}", file=sys.stderr)
        return 2
    if updated == text:
        if not args.dry_run:
            print(f"unchanged {args.path}")
        return 0
    if args.dry_run:
        diff = difflib.unified_diff(
            text.splitlines(keepends=True), updated.splitlines(keepends=True),
            fromfile=args.path, tofile=args.path,
        )
        sys.stdout.writelines(diff)
        return 0
    try:
        mode = os.stat(args.path).st_mode & 0o777
        directory = os.path.dirname(os.path.abspath(args.path))
        handle, tmp = tempfile.mkstemp(dir=directory, prefix=".skill-", suffix=".md")
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="") as out:
                out.write(updated)
                out.flush()
                os.fsync(out.fileno())
            os.chmod(tmp, mode)
            os.replace(tmp, args.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    except OSError as error:
        print(f"FAIL {args.path}: {error}", file=sys.stderr)
        return 2
    print(f"registered {args.path}")
    return 0


def validate_one(path):
    discovery = load_discovery()
    skill = discovery.read_skill(path)
    problems = list(skill["warnings"])
    if not skill["registered"]:
        problems.append("not registered for Smart Delegate (metadata.smart-delegate is not true)")
    return skill, problems


def cmd_validate(args):
    paths = list(args.path)
    for root in args.path_root or []:
        if os.path.isdir(root):
            for child in sorted(os.listdir(root)):
                candidate = os.path.join(root, child, "SKILL.md")
                if os.path.isfile(candidate):
                    paths.append(candidate)
    if not paths:
        print("FAIL no SKILL.md paths given", file=sys.stderr)
        return 2
    failures = 0
    for path in paths:
        skill, problems = validate_one(path)
        if problems:
            failures += 1
            print(f"WARN {path}: {', '.join(problems)}")
        else:
            print(f"PASS {path}: {skill['name']} [{','.join(skill['type'])}]")
    print(f"Result: {'FAIL' if failures else 'PASS'} ({len(paths)} skill(s), {failures} with warnings)")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description="Register or validate project skill metadata.")
    sub = parser.add_subparsers(dest="command", required=True)
    register = sub.add_parser("register", help="add Smart Delegate metadata to a SKILL.md")
    register.add_argument("path")
    register.add_argument("--type", required=True, help="operation, verification, or both")
    register.add_argument("--capabilities", required=True, help="comma separated keywords")
    register.add_argument("--dry-run", action="store_true")
    register.add_argument("--force", action="store_true", help="replace conflicting Smart Delegate keys")
    register.set_defaults(func=cmd_register)
    validate = sub.add_parser("validate", help="check skill frontmatter and registration")
    validate.add_argument("path", nargs="*")
    validate.add_argument("--path-root", action="append", help="directory whose child skills to check")
    validate.set_defaults(func=cmd_validate)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
