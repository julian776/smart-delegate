import importlib.util
import json
import re
import unittest
from pathlib import Path

from support import EXAMPLES, ROOT, SCRIPTS, SKILLS

NEW_TEXT_FILES = [
    SKILLS / "verification" / "SKILL.md",
    SKILLS / "create-operation-skill" / "SKILL.md",
    SKILLS / "create-operation-skill" / "references" / "setup-workflow.md",
    SKILLS / "create-verification-skill" / "SKILL.md",
] + sorted((EXAMPLES / "project-skills").rglob("*.md"))


def load_discovery():
    spec = importlib.util.spec_from_file_location(
        "contract_discover", SCRIPTS / "discover-skills.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.discovery = load_discovery()
        cls.plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())

    def test_every_skill_has_matching_frontmatter(self):
        for path in sorted(SKILLS.glob("*/SKILL.md")):
            with self.subTest(path=str(path)):
                skill = self.discovery.read_skill(str(path))
                self.assertEqual(path.parent.name, skill["name"])
                self.assertTrue(skill["description"])
                self.assertEqual([], skill["warnings"])

    def test_project_skill_examples_are_registered_and_operational(self):
        for path in sorted((EXAMPLES / "project-skills").glob("*/SKILL.md")):
            with self.subTest(path=str(path)):
                skill = self.discovery.read_skill(str(path))
                self.assertTrue(skill["registered"])
                self.assertTrue(skill["type"])
                self.assertTrue(skill["capabilities"])
                body = Path(path).read_text().split("\n---\n", 1)[1]
                forbidden = [
                    r"\bacceptance criteria\b", r"\bcoordinator\b", r"\bblocking\b",
                    r"\bcorrection\b", r"\bverdict\b", r"\bindependent\b", r"\bdelegat",
                ]
                for pattern in forbidden:
                    self.assertIsNone(re.search(pattern, body, re.IGNORECASE), pattern)

    def test_new_instructions_respect_line_width(self):
        for path in NEW_TEXT_FILES:
            for number, line in enumerate(path.read_text().splitlines(), 1):
                with self.subTest(path=str(path), line=number):
                    self.assertLessEqual(len(line), 100, line)

    def test_verification_skill_defines_the_three_verdicts(self):
        text = (SKILLS / "verification" / "SKILL.md").read_text()
        self.assertIn("**PASS**", text)
        self.assertIn("**FAIL**", text)
        self.assertIn("**NOT VERIFIED**", text)
        self.assertIn("Never report NOT VERIFIED as PASS", text)
        self.assertIn("revision", text.lower())

    def test_coordinator_has_autonomous_issue_contract(self):
        text = (SKILLS / "coordinator" / "SKILL.md").read_text()
        for phrase in (
            "## Autonomous issue mode",
            "issue-state.py",
            "discover-skills.py",
            "Acceptance criteria",
            "Correction loop",
            "PR and CI",
            "State and recovery",
            "Terminate on evidence",
            "Never weaken one",
            "Project Coordinator",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_setup_skills_share_discovery_and_registration(self):
        for name in ("create-operation-skill", "create-verification-skill"):
            text = (SKILLS / name / "SKILL.md").read_text()
            with self.subTest(skill=name):
                self.assertIn("discover-skills.py", text)
                self.assertIn("skill-metadata.py", text)
                self.assertIn("register", text)
                self.assertIn("validat", text.lower())
        operation = (SKILLS / "create-operation-skill" / "SKILL.md").read_text()
        self.assertIn("references/setup-workflow.md", operation)
        verification = (SKILLS / "create-verification-skill" / "SKILL.md").read_text()
        self.assertIn("create-operation-skill/references/setup-workflow.md", verification)

    def test_readme_documents_the_mvp_surface(self):
        text = (ROOT / "README.md").read_text()
        for phrase in (
            "Autonomous issue execution",
            "verification",
            "create-operation-skill",
            "create-verification-skill",
            "discover-skills.py",
            "issue-state.py",
            "execution:",
            "unittest",
            "Project Coordinator",
            "smart-delegate-type",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_example_project_skills_cannot_be_loaded_as_global_skills(self):
        roots = [EXAMPLES / "project-skills"]
        found = []
        for root in roots:
            for path in sorted(root.glob("*/SKILL.md")):
                found.append(self.discovery.read_skill(str(path))["name"])
        self.assertEqual(["run-backtest", "verify-backtest-platform"], found)


if __name__ == "__main__":
    unittest.main()
