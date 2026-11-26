# MVP acceptance scenarios

Maps the acceptance tests in the MVP brief to automated coverage or a reproducible manual
procedure. Run the automated suite first:

```bash
python3 -m unittest discover -s tests
```

| Scenario | Coverage | Where |
|---|---|---|
| A successful autonomous issue | manual, dogfooded on this MVP | procedure below |
| B reviewer finds a defect | manual | procedure below |
| C tests pass, behavior wrong | automated proxy | `test_not_verified_is_not_pass`; manual below |
| D CI failure recovered | manual | procedure below |
| E genuine blocker | automated | `test_blocker_report_and_exit_code` |
| F interrupted execution resumes | automated plus manual | `test_duplicate_init_refused_without_force`, `test_report_write_and_recovery_status`; reconcile-and-resume below |
| G resource exhaustion | automated | `test_budget_exhaustion_terminates`, `test_deadline_exhaustion_terminates`, `test_cost_ceiling_blocks_completion` |
| H criteria manipulation | automated | `test_criterion_cannot_be_weakened_without_approval`, `test_unrecorded_criterion_edit_is_detected` |
| I lightweight task | automated | `test_lightweight_issue_can_skip_ci_and_pr` |
| J no existing project skill | manual | setup procedure below |
| K existing complete skill | manual | setup procedure below |
| L registration-only preservation | automated | `test_register_preserves_body_and_unrelated_metadata` |
| M existing incomplete skill | manual | setup procedure below |
| N independent skill creation | manual | setup procedure below |
| O user cancels | manual | setup procedure below |
| P coordinator discovery | automated | `test_catalog_reads_metadata_without_bodies`, `test_registered_and_type_filters` |
| Q useful unregistered skill | automated | `test_unregistered_and_malformed_are_graceful` |
| R malformed metadata | automated | `test_unregistered_and_malformed_are_graceful` |
| S operational skill responsibility | automated | `test_project_skill_examples_are_registered_and_operational` |
| T evidence invalidation | automated | `test_new_revision_invalidates_evidence` |
| U concurrent issue isolation | manual | procedure below |

## Autonomous issue procedure

Run against a disposable repository or branch. Requires a host that can delegate without continuous
human turns, plus a configured worker.

1. Write criteria as a numbered Markdown list. Each line: outcome, then `— check: <deciding check>`.
2. Initialize state with the implementer name, revision, and criteria.
3. Delegate implementation on an isolated branch or worktree.
4. Delegate review to a worker that did not implement. Record it with `review`.
5. Delegate verification to a different worker. Record one `criteria-verdict` per criterion; PASS
   and FAIL require evidence.
6. Run `gate`. For B, introduce a reproducible defect before step 5; expect a blocking finding,
   correction, and re-review. For C, ensure existing tests cannot cover the behavior; expect
   NOT VERIFIED or FAIL, not PASS.
7. For D, push a correctable CI failure; expect diagnosis, correction, and a new revision. Old
   evidence must show as PENDING.
8. For U, run two issues in separate worktrees and confirm neither sees the other's changes and
   unrelated user changes remain.

## Interrupted execution procedure

Start an issue, record one verified criterion, stop the host, then resume:

1. `issue-state.py --issue ID status` shows phase and recorded evidence.
2. Reconcile the branch and PR by hand.
3. Continue from that phase. Do not re-run completed criteria or open a second PR.

## Setup skill procedure

1. Ask for an operation the repository does not document. Expect discovery to find nothing, then a
   generated skill with real commands, output paths, and metadata.
2. Ask for an operation an existing skill already covers. Expect a metadata-only recommendation.
   Approve it and compare the body: it must be byte-identical.
3. Ask for an operation a skill covers incompletely. Expect an adaptation recommendation and no
   write before approval. Approve and check that the change is minimal.
4. Ask for a separate skill despite an existing one. Expect the original untouched and the new
   skill free of orchestration policy.
5. Decline every option. Expect no modified files (`git status` clean for those paths).

## Pilot plan and metrics

The MVP brief asks for roughly ten real issues across backend, UI, performance, concurrency, CI
recovery, and a genuine blocker. No external pilot was executed here; results are not fabricated.
To run one, record per issue:

| Metric | Source |
|---|---|
| human interventions | coordinator log and final report |
| autonomous completion | `gate` exit 0 |
| criteria verified | `status` PASS count / total |
| CI failures resolved | PR check history |
| duration | state `created_at` to final event |
| delegates | `budget.delegates` |
| model consumption and cost | provider usage, or `not reported` |
| correction cycles | `budget.correction_cycles` |
| defects found in human review | human review notes |
| repeated discovery or verification | state events |

Targets are evaluation goals, not current claims: at least 80% verified completion without routine
intervention, 100% of completed issues with evidence on the final revision, zero unauthorized merges
or deployments, zero silent criteria weakening, zero unauthorized project-skill edits, and zero
completion claims with known blocking defects.
