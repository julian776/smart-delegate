"""Shared helpers for the Smart Delegate test suite. Standard library only."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "coordinator" / "scripts"
ISSUE_STATE = SCRIPTS / "issue-state.py"
DISCOVER = SCRIPTS / "discover-skills.py"
METADATA = SCRIPTS / "skill-metadata.py"
LOAD_CONFIG = ROOT / "skills" / "smart-delegate" / "scripts" / "load-config.py"
SKILLS = ROOT / "skills"
EXAMPLES = ROOT / "examples"


def clean_env(home):
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["SMART_DELEGATE_SKILL_PATHS"] = ""
    env.pop("XDG_CONFIG_HOME", None)
    return env


def run(args, cwd, home, timeout=60):
    return subprocess.run(
        [sys.executable, *map(str, args)],
        cwd=str(cwd),
        env=clean_env(home),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def write(path, text, newline=""):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline=newline) as handle:
        handle.write(text)
    return path


def temp_tree():
    directory = tempfile.TemporaryDirectory()
    root = Path(directory.name)
    (root / "home").mkdir()
    (root / "project").mkdir()
    return directory, root
