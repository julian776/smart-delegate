import unittest

from support import LOAD_CONFIG, run, temp_tree, write

try:
    import yaml  # noqa: F401
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

PROJECT_CONFIG = """# project routing
models:
  - title: Focused
    model: [Sonnet, Terra]
    priority: 20
    description: >
      Well-scoped implementation.
    invocation: |
      Run the focused worker.
      Keep this # line inside the block.
execution:
  max_delegates: 2
  max_correction_cycles: 3
  delivery: merge-ready
  auto_merge: false
"""


class LoadConfigTest(unittest.TestCase):
    def setUp(self):
        self._tree, self.root = temp_tree()
        self.home = self.root / "home"
        self.project = self.root / "project"

    def tearDown(self):
        self._tree.cleanup()

    def config(self, text):
        return write(self.project / ".smart-delegate" / "config.yaml", text)

    def load(self, *args, expect=0):
        result = run([LOAD_CONFIG, *args], self.project, self.home)
        self.assertEqual(expect, result.returncode, result.stdout + result.stderr)
        return result

    def test_project_config_wins_and_comments_are_stripped(self):
        self.config(PROJECT_CONFIG)
        user = self.home / ".config" / "smart-delegate" / "config.yaml"
        write(user, "models:\n  - title: User\n")
        result = self.load()
        self.assertIn(str(self.project / ".smart-delegate" / "config.yaml"), result.stdout)
        self.assertNotIn("# project routing", result.stdout)
        self.assertIn("Keep this # line inside the block.", result.stdout)
        self.assertNotIn("User", result.stdout)

    def test_bundled_fallback_used_without_config(self):
        result = self.load()
        self.assertIn("skills/smart-delegate/config.yaml", result.stdout)
        self.assertIn("title: Fast", result.stdout)

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed")
    def test_check_accepts_valid_execution_limits(self):
        self.config(PROJECT_CONFIG)
        result = self.load("--check")
        self.assertIn("PASS yaml", result.stdout)
        self.assertIn("PASS execution: 4 setting(s)", result.stdout)
        self.assertIn("Result: PASS", result.stdout)

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed")
    def test_check_rejects_invalid_execution_values(self):
        cases = [
            ("max_delegates: many", "execution.max_delegates: invalid value"),
            ("max_correction_cycles: -1", "execution.max_correction_cycles: invalid value"),
            ("delivery: production", "execution.delivery: invalid value"),
            ("auto_merge: sometimes", "execution.auto_merge: invalid value"),
            ("max_model_cost_usd: 0", "execution.max_model_cost_usd: invalid value"),
            ("deadline: tomorrow", "execution.deadline: invalid value"),
            ("max_agents: 4", "execution.max_agents: unknown key"),
        ]
        for line, message in cases:
            with self.subTest(line=line):
                self.config("execution:\n  " + line + "\n")
                result = self.load("--check", expect=1)
                self.assertIn("WARN", result.stdout)
                self.assertIn(message, result.stdout)

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed")
    def test_check_reports_missing_title(self):
        self.config("models:\n  - model: Sonnet\n")
        result = self.load("--check", expect=1)
        self.assertIn("WARN models[0]: missing title", result.stdout)

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed")
    def test_check_reports_invalid_yaml(self):
        self.config("models: [\n")
        result = self.load("--check", expect=1)
        self.assertIn("WARN yaml", result.stdout)


if __name__ == "__main__":
    unittest.main()
