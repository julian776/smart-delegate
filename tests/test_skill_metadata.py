import unittest

from support import METADATA, run, temp_tree, write

ORIGINAL = """---
name: run-backtest
description: >
  Run a local strategy backtest.
  Keep this folded line.
metadata:
  author: project-team
  tags: internal
allowed-tools: Bash(make *)
---

# Run backtest

Body line with `# a hash` inside code.
Trailing spaces stay.   
"""

UNREGISTERED = """---
name: later
description: Existing skill without metadata.
---

# Later

Body.
"""


class SkillMetadataTest(unittest.TestCase):
    def setUp(self):
        self._tree, self.root = temp_tree()
        self.home = self.root / "home"
        self.project = self.root / "project"
        self.skill = write(self.project / "skills" / "run-backtest" / "SKILL.md", ORIGINAL)
        self.unregistered = write(self.project / "skills" / "later" / "SKILL.md", UNREGISTERED)

    def tearDown(self):
        self._tree.cleanup()

    def metadata(self, *args, expect=0):
        result = run([METADATA, *args], self.project, self.home)
        self.assertEqual(expect, result.returncode, result.stdout + result.stderr)
        return result

    def body(self, text):
        return text.split("\n---\n", 1)[1]

    def test_register_preserves_body_and_unrelated_metadata(self):
        before = self.skill.read_text()
        self.metadata("register", self.skill, "--type", "operation,verification",
                      "--capabilities", "backtesting,simulation")
        after = self.skill.read_text()
        self.assertEqual(self.body(before), self.body(after))
        self.assertIn("author: project-team", after)
        self.assertIn("tags: internal", after)
        self.assertIn('smart-delegate: "true"', after)
        self.assertIn('smart-delegate-type: "operation,verification"', after)
        self.assertIn('smart-delegate-capabilities: "backtesting,simulation"', after)
        self.assertIn("allowed-tools: Bash(make *)", after)
        self.assertIn("Trailing spaces stay.   ", after)

    def test_idempotent(self):
        self.metadata("register", self.skill, "--type", "operation",
                      "--capabilities", "backtesting")
        before = self.skill.read_text()
        result = self.metadata("register", self.skill, "--type", "operation",
                               "--capabilities", "backtesting")
        self.assertEqual("unchanged", result.stdout.strip().split()[0])
        self.assertEqual(before, self.skill.read_text())

    def test_conflict_requires_force(self):
        self.metadata("register", self.skill, "--type", "operation",
                      "--capabilities", "backtesting")
        before = self.skill.read_text()
        result = self.metadata("register", self.skill, "--type", "verification",
                               "--capabilities", "ui", expect=2)
        self.assertIn("existing metadata differs", result.stderr)
        self.assertEqual(before, self.skill.read_text())
        self.metadata("register", self.skill, "--type", "verification",
                      "--capabilities", "ui", "--force")
        after = self.skill.read_text()
        self.assertIn('smart-delegate-type: "verification"', after)
        self.assertIn("author: project-team", after)

    def test_dry_run_writes_nothing(self):
        before = self.skill.read_text()
        result = self.metadata("register", self.unregistered, "--type", "operation",
                               "--capabilities", "docs", "--dry-run")
        self.assertIn("+metadata:", result.stdout)
        self.assertEqual(UNREGISTERED, self.unregistered.read_text())
        self.assertEqual(before, self.skill.read_text())

    def test_missing_frontmatter_is_refused(self):
        plain = write(self.project / "skills" / "plain" / "SKILL.md", "# Plain\n\nBody.\n")
        result = self.metadata("register", plain, "--type", "operation",
                               "--capabilities", "x", expect=2)
        self.assertIn("must start with", result.stderr)

    def test_missing_description_is_refused(self):
        no_description = write(
            self.project / "skills" / "nodesc" / "SKILL.md",
            "---\nname: nodesc\n---\n\n# Body\n",
        )
        result = self.metadata("register", no_description, "--type", "operation",
                               "--capabilities", "x", expect=2)
        self.assertIn("needs a description", result.stderr)

    def test_crlf_preserved(self):
        crlf = ORIGINAL.replace("\n", "\r\n")
        target = write(self.project / "skills" / "crlf" / "SKILL.md", crlf, newline="")
        self.metadata("register", target, "--type", "operation", "--capabilities", "x")
        data = target.read_bytes()
        self.assertIn(b"\r\n", data)
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
        self.assertIn(b'author: project-team\r\n', data)

    def test_no_op_preserves_unquoted_existing_keys(self):
        text = """---
name: plain
description: Plain.
metadata:
  smart-delegate: true
  smart-delegate-type: operation
  smart-delegate-capabilities: docs
---

# Plain
"""
        target = write(self.project / "skills" / "plain" / "SKILL.md", text)
        result = self.metadata("register", target, "--type", "operation",
                               "--capabilities", "docs")
        self.assertIn("unchanged", result.stdout)
        self.assertEqual(text, target.read_text())

    def test_validate_reports_registration(self):
        self.metadata("register", self.skill, "--type", "operation",
                      "--capabilities", "backtesting")
        result = self.metadata("validate", self.skill, self.unregistered, expect=1)
        self.assertIn("PASS", result.stdout)
        self.assertIn("WARN", result.stdout)
        self.assertIn("not registered", result.stdout)
        self.metadata("register", self.unregistered, "--type", "operation",
                      "--capabilities", "docs")
        result = self.metadata("validate", self.skill, self.unregistered)
        self.assertIn("Result: PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
