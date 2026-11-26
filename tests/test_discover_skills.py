import json
import unittest

from support import DISCOVER, run, temp_tree, write


def skill_text(name, description, metadata=None, body="# Skill\n"):
    lines = ["---", f"name: {name}", "description: >", f"  {description}"]
    if metadata is not None:
        lines.append("metadata:")
        for key, value in metadata.items():
            lines.append(f'  {key}: "{value}"')
    lines += ["---", "", body]
    return "\n".join(lines)


class DiscoverSkillsTest(unittest.TestCase):
    def setUp(self):
        self._tree, self.root = temp_tree()
        self.home = self.root / "home"
        self.project = self.root / "project"
        self.skills = self.project / ".agents" / "skills"
        write(self.skills / "alpha" / "SKILL.md", skill_text(
            "run-backtest", "Run a local strategy backtest.",
            {"smart-delegate": "true", "smart-delegate-type": "operation",
             "smart-delegate-capabilities": "backtesting,simulation"}))
        write(self.skills / "beta" / "SKILL.md", skill_text(
            "verify-platform", "Exercise the dashboard. Keep this sentence.",
            {"smart-delegate": "true", "smart-delegate-type": "operation,verification",
             "smart-delegate-capabilities": "ui,browser"}))
        write(self.skills / "gamma" / "SKILL.md", skill_text(
            "legacy-notes", "Existing unregistered skill."))
        write(self.skills / "delta" / "SKILL.md",
              "---\nname: broken\ndescription: unterminated\n\n# Broken\n")
        write(self.skills / "epsilon" / "SKILL.md", skill_text(
            "odd", "Unknown type skill.",
            {"smart-delegate": "true", "smart-delegate-type": "magic",
             "smart-delegate-capabilities": "x"}))
        write(self.skills / "alpha" / "references" / "deep" / "SKILL.md",
              skill_text("nested", "Must not be listed."))
        write(self.skills / "nostamp" / "SKILL.md", "# no frontmatter\n")

    def tearDown(self):
        self._tree.cleanup()

    def discover(self, *args, expect=0):
        result = run([DISCOVER, "--project", self.project, *args], self.project, self.home)
        self.assertEqual(expect, result.returncode, result.stdout + result.stderr)
        return result

    def test_catalog_reads_metadata_without_bodies(self):
        result = self.discover("--json")
        data = json.loads(result.stdout)
        names = {skill["name"] for skill in data["skills"]}
        self.assertIn("run-backtest", names)
        self.assertIn("verify-platform", names)
        self.assertIn("legacy-notes", names)
        self.assertNotIn("nested", names)
        alpha = next(skill for skill in data["skills"] if skill["name"] == "run-backtest")
        self.assertTrue(alpha["registered"])
        self.assertEqual(["operation"], alpha["type"])
        self.assertEqual(["backtesting", "simulation"], alpha["capabilities"])
        beta = next(skill for skill in data["skills"] if skill["name"] == "verify-platform")
        self.assertEqual(["operation", "verification"], beta["type"])
        self.assertEqual("Exercise the dashboard. Keep this sentence.", beta["description"])
        self.assertNotIn("magic", beta["type"])

    def test_unregistered_and_malformed_are_graceful(self):
        result = self.discover("--json")
        data = json.loads(result.stdout)
        legacy = next(skill for skill in data["skills"] if skill["name"] == "legacy-notes")
        self.assertFalse(legacy["registered"])
        self.assertEqual([], legacy["type"])
        warnings = "\n".join(data["warnings"])
        self.assertIn("missing frontmatter", warnings)
        self.assertIn("unterminated frontmatter", warnings)
        self.assertIn("unknown smart-delegate-type 'magic'", warnings)

    def test_registered_and_type_filters(self):
        data = json.loads(self.discover("--registered", "--json").stdout)
        names = {skill["name"] for skill in data["skills"]}
        self.assertEqual({"run-backtest", "verify-platform", "odd"}, names)
        data = json.loads(self.discover("--type", "verification", "--json").stdout)
        self.assertEqual({"verify-platform"}, {skill["name"] for skill in data["skills"]})

    def test_table_output(self):
        result = self.discover()
        self.assertIn("| name | type | capabilities | description | location |", result.stdout)
        self.assertIn("run-backtest", result.stdout)
        self.assertIn("WARN", result.stderr)

    def test_empty_project_is_not_an_error(self):
        empty = self.root / "empty"
        empty.mkdir()
        result = run([DISCOVER, "--project", empty], empty, self.home)
        self.assertEqual(0, result.returncode)
        self.assertIn("No skills found", result.stdout)

    def test_env_path_and_direct_skill_path(self):
        extra = self.root / "extra" / "skills" / "zeta"
        write(extra / "SKILL.md", skill_text(
            "zeta", "Extra skill.",
            {"smart-delegate": "true", "smart-delegate-type": "verification",
             "smart-delegate-capabilities": "api"}))
        empty = self.root / "empty"
        empty.mkdir()
        result = run([DISCOVER, "--project", empty, "--path", extra, "--json"],
                     self.root, self.home)
        data = json.loads(result.stdout)
        self.assertIn("zeta", {skill["name"] for skill in data["skills"]})
        result = run([DISCOVER, "--project", empty, "--json"], self.root, self.home,
                     env_extra={"SMART_DELEGATE_SKILL_PATHS": extra})
        data = json.loads(result.stdout)
        self.assertIn("zeta", {skill["name"] for skill in data["skills"]})

    def test_project_skill_shadows_duplicate_name(self):
        write(self.home / ".agents" / "skills" / "alpha" / "SKILL.md", skill_text(
            "run-backtest", "User copy.",
            {"smart-delegate": "true", "smart-delegate-type": "operation",
             "smart-delegate-capabilities": "old"}))
        data = json.loads(self.discover("--json").stdout)
        matches = [skill for skill in data["skills"] if skill["name"] == "run-backtest"]
        self.assertEqual(1, len(matches))
        self.assertIn("Run a local strategy backtest.", matches[0]["description"])
        self.assertTrue(any("duplicate skill name" in warning for warning in data["warnings"]))
        filtered = json.loads(self.discover("--registered", "--json").stdout)
        self.assertIn("run-backtest", {skill["name"] for skill in filtered["skills"]})
        self.assertTrue(any("duplicate skill name" in warning for warning in filtered["warnings"]))


if __name__ == "__main__":
    unittest.main()
