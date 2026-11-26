import json
import unittest

from support import ISSUE_STATE, run, temp_tree, write


class IssueStateTest(unittest.TestCase):
    def setUp(self):
        self._tree, self.root = temp_tree()
        self.home = self.root / "home"
        self.project = self.root / "project"
        self.state_dir = self.project / ".smart-delegate" / "issues"
        self.criteria = write(
            self.project / "criteria.json",
            json.dumps([
                {"text": "Export action visible", "check": "browser shows Export"},
                {"text": "Authorized export returns rows", "check": "GET /export 200"},
                {"text": "Cross-tenant export blocked", "check": "GET /export 403"},
            ]),
        )

    def tearDown(self):
        self._tree.cleanup()

    def state(self, *args, expect=0):
        result = run([ISSUE_STATE, "--issue", "PAY-142", *args], self.project, self.home)
        self.assertEqual(expect, result.returncode, result.stdout + result.stderr)
        return result

    def init(self, *args):
        return self.state(
            "init", "--objective", "Add transaction export", "--implementer", "impl-a",
            "--revision", "rev1", "--criteria", self.criteria, *args,
        )

    def complete_evidence(self):
        for number, evidence in ((1, "screenshot export.png"), (2, "200 with 12 rows"),
                                 (3, "403 for tenant B")):
            self.state("criteria-verdict", "--id", f"C{number}", "--verdict", "pass",
                       "--evidence", evidence, "--by", "verifier-b")
        self.state("review", "--verdict", "approve", "--reviewer", "reviewer-b")
        self.state("ci", "--status", "green")
        self.state("pr", "--url", "https://example.test/pr/1", "--state", "ready")

    def test_complete_issue_passes_gate(self):
        self.init()
        self.complete_evidence()
        result = self.state("gate")
        self.assertIn("PASS PAY-142", result.stdout)
        self.state("set-phase", "done")
        report = self.state("report")
        self.assertIn("Status: Verified, merge ready", report.stdout)
        self.assertIn("C1 PASS", report.stdout)

    def test_self_verification_blocks_completion(self):
        self.init()
        for number, evidence in ((1, "looked at it"), (2, "ran it"), (3, "ran it")):
            self.state("criteria-verdict", "--id", f"C{number}", "--verdict", "pass",
                       "--evidence", evidence, "--by", "impl-a")
        self.state("review", "--verdict", "approve", "--reviewer", "impl-a")
        self.state("ci", "--status", "green")
        self.state("pr", "--url", "https://example.test/pr/1", "--state", "ready")
        result = self.state("gate", expect=1)
        self.assertIn("was verified by its implementer", result.stdout)
        self.assertIn("reviewer is the implementer", result.stdout)

    def test_not_verified_is_not_pass(self):
        self.init()
        self.complete_evidence()
        self.state("criteria-verdict", "--id", "C2", "--verdict", "not-verified",
                   "--evidence", "dev credentials unavailable", "--by", "verifier-b")
        result = self.state("gate", expect=1)
        self.assertIn("C2 is NOT VERIFIED", result.stdout)

    def test_new_revision_invalidates_evidence(self):
        self.init()
        self.complete_evidence()
        self.state("gate")
        self.state("set-revision", "rev2")
        result = self.state("gate", expect=1)
        self.assertIn("C1 is PENDING", result.stdout)
        self.assertIn("review verdict is none", result.stdout)
        self.assertIn("required CI is unknown", result.stdout)
        self.complete_evidence()
        self.state("gate")

    def test_criterion_cannot_be_weakened_without_approval(self):
        self.init()
        self.complete_evidence()
        self.state("gate")
        refused = self.state(
            "criteria-amend", "--id", "C3", "--text", "Cross-tenant access acceptable",
            "--justification", "make it pass", "--approved-by", "impl-a", expect=2,
        )
        self.assertIn("needs independent approval", refused.stderr)
        self.state("criteria-amend", "--id", "C3", "--text", "Cross-tenant access acceptable",
                   "--justification", "scope reduced by product", "--approved-by", "reviewer-b")
        result = self.state("gate", expect=1)
        self.assertIn("C3 is PENDING", result.stdout)

    def test_unrecorded_criterion_edit_is_detected(self):
        self.init()
        self.complete_evidence()
        path = self.state_dir / "PAY-142.json"
        data = json.loads(path.read_text())
        data["criteria"][2]["text"] = "Anything is acceptable"
        path.write_text(json.dumps(data))
        result = self.state("gate", expect=1)
        self.assertIn("content changed without a recorded amendment", result.stdout)

    def test_unrecorded_check_edit_is_detected(self):
        self.init()
        self.complete_evidence()
        path = self.state_dir / "PAY-142.json"
        data = json.loads(path.read_text())
        data["criteria"][2]["check"] = "tester says it works"
        path.write_text(json.dumps(data))
        result = self.state("gate", expect=1)
        self.assertIn("content changed without a recorded amendment", result.stdout)

    def test_amendment_approval_must_be_independent(self):
        self.init()
        path = self.state_dir / "PAY-142.json"
        data = json.loads(path.read_text())
        data["criteria"][0]["amendments"] = [{
            "at": "now", "from_text": "Export action visible", "to_text": "Export action visible",
            "from_check": "browser shows Export", "to_check": "browser shows Export",
            "justification": "trust me", "approved_by": ["impl-a"],
        }]
        path.write_text(json.dumps(data))
        result = self.state("gate", expect=1)
        self.assertIn("amendment lacks independent approval", result.stdout)

    def test_implementer_is_required(self):
        result = self.state("init", "--objective", "no owner", expect=2)
        self.assertIn("--implementer", result.stderr)

    def test_cost_ceiling_blocks_completion(self):
        self.init("--max-model-cost-usd", "5")
        self.complete_evidence()
        self.state("budget", "--model-cost-usd", "500")
        result = self.state("gate", expect=4)
        self.assertIn("model cost $500.0 exceeds ceiling $5.0", result.stdout)

    def test_merge_requires_recorded_authorization(self):
        self.init()
        self.complete_evidence()
        self.state("pr", "--state", "merged")
        result = self.state("gate", expect=1)
        self.assertIn("PR merged without recorded merge authorization", result.stdout)
        self.state("authorize-merge", "--by", "user request")
        self.state("gate")

    def test_malformed_nested_state_is_readable(self):
        self.init()
        path = self.state_dir / "PAY-142.json"
        data = json.loads(path.read_text())
        data["ci"] = "green"
        path.write_text(json.dumps(data))
        result = self.state("gate", expect=2)
        self.assertIn("ci is not a mapping", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_unsafe_issue_id_is_refused(self):
        result = run([ISSUE_STATE, "--issue", "PAY 142", "status"], self.project, self.home)
        self.assertEqual(2, result.returncode)
        self.assertIn("issue id must match", result.stderr)

    def test_disabling_required_ci_needs_reason(self):
        self.init()
        result = self.state("ci", "--status", "failing", "--no-required", expect=2)
        self.assertIn("needs --reason", result.stderr)
        self.state("ci", "--status", "failing", "--no-required", "--reason", "docs-only commit")

    def test_criteria_json_must_be_a_list(self):
        bad = write(self.project / "bad.json", json.dumps({"text": "one"}))
        result = self.state("init", "--objective", "bad", "--implementer", "impl-a",
                            "--criteria", bad, expect=2)
        self.assertIn("must be a list", result.stderr)

    def test_blocking_review_finding_blocks_completion(self):
        self.init()
        self.complete_evidence()
        self.state("review", "--verdict", "approve", "--reviewer", "reviewer-b",
                   "--blocking", "missing idempotency")
        result = self.state("gate", expect=1)
        self.assertIn("blocking review finding", result.stdout)

    def test_ci_and_pr_required_by_default(self):
        self.init()
        self.state("criteria-verdict", "--id", "C1", "--verdict", "pass",
                   "--evidence", "ok", "--by", "verifier-b")
        self.state("criteria-verdict", "--id", "C2", "--verdict", "pass",
                   "--evidence", "ok", "--by", "verifier-b")
        self.state("criteria-verdict", "--id", "C3", "--verdict", "pass",
                   "--evidence", "ok", "--by", "verifier-b")
        self.state("review", "--verdict", "approve", "--reviewer", "reviewer-b")
        result = self.state("gate", expect=1)
        self.assertIn("required CI is unknown", result.stdout)
        self.assertIn("PR url missing", result.stdout)

    def test_lightweight_issue_can_skip_ci_and_pr(self):
        self.init("--no-ci-required", "--no-pr-required", "--profile", "lightweight")
        for number in (1, 2, 3):
            self.state("criteria-verdict", "--id", f"C{number}", "--verdict", "pass",
                       "--evidence", "docs render", "--by", "reviewer-b")
        self.state("review", "--verdict", "approve", "--reviewer", "reviewer-b")
        self.state("gate")

    def test_blocker_report_and_exit_code(self):
        self.init("--no-ci-required", "--no-pr-required")
        result = self.state(
            "block", "--kind", "credentials", "--problem", "dev provider secret unavailable",
            "--attempted", "read .env", "--attempted", "checked local mock",
            "--options", "provide dev credentials", "--next-action", "provide dev credentials",
            expect=3,
        )
        self.assertIn("blocked", result.stdout)
        gate = self.state("gate", expect=3)
        self.assertIn("BLOCKED PAY-142", gate.stdout)
        report = self.state("report")
        self.assertIn("Status: Blocked", report.stdout)
        self.assertIn("- Attempted: read .env", report.stdout)
        self.assertIn("Required human action: provide dev credentials", report.stdout)

    def test_budget_exhaustion_terminates(self):
        self.init("--max-correction-cycles", "1")
        self.state("record", "correction", "--summary", "attempt one")
        self.state("record", "correction", "--summary", "attempt two")
        result = self.state("gate", expect=4)
        self.assertIn("exceed maximum 1", result.stdout)

    def test_deadline_exhaustion_terminates(self):
        self.init("--deadline", "2020-01-01T00:00:00Z")
        result = self.state("gate", expect=4)
        self.assertIn("deadline 2020-01-01T00:00:00Z passed", result.stdout)

    def test_duplicate_init_refused_without_force(self):
        self.init()
        result = self.state("init", "--objective", "again", "--implementer", "impl-a", expect=2)
        self.assertIn("already exists", result.stderr)
        self.state("init", "--objective", "again", "--implementer", "impl-a", "--force")

    def test_cannot_mark_done_before_gate(self):
        self.init()
        result = self.state("set-phase", "done", expect=2)
        self.assertIn("cannot mark done", result.stderr)

    def test_unreadable_state_is_reported(self):
        self.state_dir.mkdir(parents=True)
        (self.state_dir / "PAY-142.json").write_text("{not json")
        result = run([ISSUE_STATE, "--issue", "PAY-142", "status"], self.project, self.home)
        self.assertEqual(2, result.returncode)
        self.assertIn("unreadable state", result.stderr)

    def test_report_write_and_recovery_status(self):
        self.init()
        self.state("record", "delegate", "--name", "implementer", "--profile", "Focused")
        status = self.state("status")
        self.assertIn("delegates 1/3", status.stdout)
        self.state("report", "--write")
        report = (self.state_dir / "PAY-142.md").read_text()
        self.assertIn("# PAY-142", report)
        self.assertIn("Delegates: 1/3", report)

    def test_pending_init_without_criteria_fails_gate(self):
        self.state("init", "--objective", "no criteria", "--implementer", "impl-a")
        result = self.state("gate", expect=1)
        self.assertIn("no acceptance criteria recorded", result.stdout)


if __name__ == "__main__":
    unittest.main()
