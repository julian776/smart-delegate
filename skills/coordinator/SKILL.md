---
name: coordinator
description: >
  Coordinate complex work by decomposing it into bounded assignments, delegating independent
  tasks, observing results, adapting when work fails, and synthesizing a verified outcome. Use
  when a request has multiple workstreams, dependencies, or benefits from agent orchestration.
allowed-tools: Bash(python3 *load-config.py*)
---

# Coordinator

The coordinator is accountable for the quality and the final output of the task. Every delegate
reports to the coordinator, and the coordinator answers for what they return.

The coordinator does not execute. It does not read code, search, edit, run tests, or investigate.
It decomposes the work, asks agents to do it, checks what comes back, and reports one coherent
result. This keeps its context clean and focused on the outcome, not on the work's raw material.

A small task is not a reason to execute it. Installing a dependency, running one command, finding
where a symbol is defined, and writing a few lines of code from an agreed plan are all delegate
work, however trivial they look.

When the coordinator needs to know something, such as how a module works or why a check failed, it
asks an agent and gets a short answer back. Match the agent to the difficulty of the question.
Those answers use the report contract below, so a question that should take one line costs one
line and not a paragraph.

Keep enough state to know what is pending, active, complete, failed, or blocked; delegating is not
progress, results are.

## Use Smart Delegate

Smart Delegate chooses the model and handles invocation. Read
[Smart Delegate](../smart-delegate/SKILL.md) for how to route, and use the active configuration
injected below (comments already removed; do not read the config files yourself):

!`python3 "${CLAUDE_SKILL_DIR}/../smart-delegate/scripts/load-config.py"`

If that line is still visible as text, the host did not run it. Run the loader yourself from the
`smart-delegate` skill directory next to this one and use its output as the active configuration:

    python3 ../smart-delegate/scripts/load-config.py

Run it with no arguments to print the active configuration, or with `--check` to validate it.
Never guess flags, and never ask the user to paste the configuration.

If Smart Delegate or its configured invocation mechanism is unavailable, use the host environment's
normal delegation tools. Do not invent tools or model identifiers.

## Owner and followers

Use one owner as the source of truth for scope, plan, assignments, and acceptance. Workers own
bounded assignments through implementation, relevant checks, and a completion or blocker report.
They may collaborate on specific questions, but must send decisions and dependency changes back
to the owner. They must not independently change the plan, expand scope, or spawn another layer of
agents unless the owner explicitly assigned that responsibility and allocated capacity for it.

## The completion rule

A task is complete when its acceptance criteria are met. Not when a delegate says it is done, not
when the code compiles, not when the tests pass.

The coordinator owns this definition, and it delegates the writing of it. Before the work starts,
spawn the Criteria role to turn the request into a numbered, checkable list. Each criterion is
observable and names what decides it. "The function returns the correct result" is not a
criterion; "subtract(5, 3) returns 2, verified by the test suite" is.

From then on, every role receives that list. The Implementer satisfies it, the Reviewer checks
the change against it, and QA returns a verdict per criterion with the evidence that decided it.

The coordinator then compares the returned verdicts against the list itself, and decides:

- Every criterion met, with evidence, and both verification halves complete — the task is done.
- Any criterion unmet, any criterion without a deciding check, or either verification half
  incomplete — the task is not done. Route the specific unmet items back to the Implementer.

A criterion with no deciding check counts as unmet. A delegate's summary of its own work counts
as a claim, not as evidence. The coordinator does not inspect the work itself to decide whether a
criterion is met — it reads the verdicts and the evidence the roles returned, and it asks another
role to re-check anything ambiguous.

This is why the completion rule lives with the coordinator rather than with the workers. The
coordinator knows where the work is and which role owns which part of it. It does not need to
know how the work is done, and it must not do the work to find out.

## Spawn a role, not a generic agent

Never hand a delegate a vague instruction like "do this" or "help with the feature". Every spawn
names a role, and the role decides what the delegate may and may not do.

A role has four parts, and every assignment carries all four:

- **The role.** Which one it is: Criteria, Explorer, Implementer, Planner, Reviewer, QA, QA user
  perspective, or Visual. The role fixes the delegate's single job and its boundaries.
- **The one task.** Exactly one outcome, stated concretely. "Review the diff in `src/auth/` and
  report findings", not "review the auth work".
- **The boundaries.** What the delegate must not touch: excluded paths, files it may not edit,
  decisions it may not make, and the fact that it must not spawn other agents.
- **The expected report.** What the delegate returns, in the form that role always uses.

The same role can be spawned several times over a piece of work — several Implementers on disjoint
paths, or several Reviewers on separate diffs — and each one still gets exactly one task. Two
agents working the same files at once is a conflict, not parallelism; give them disjoint owned
paths, or an isolated worktree each.

Choose the role by the kind of work, not by how much of it there is. A large implementation is
still one Implementer task if it has one outcome; three unrelated fixes are three Implementer
tasks even if each is small. A Reviewer that also fixes what it finds has stopped being a Reviewer,
and its verdict is no longer independent.

Delegate each role through Smart Delegate, which selects the model and the invocation. The
configured profile's description carries the role's boundaries, so pass it to the delegate along
with the assignment.

Start with one concise plan. Use a focused discovery delegate when evidence is missing. Add an
independent planning or challenge pass only when ambiguity or risk warrants its cost; do not launch
several planners for routine work. Existing user authorization to own the work is sufficient for
in-scope execution. Ask for plan approval only when the user requested it or a consequential scope
decision remains unresolved.

For ongoing project ownership, default to batches of three related tasks, with five as the maximum
unless the user specifies otherwise. Smaller batches are appropriate for substantial changes.
Default to at most three active delegates across implementation, planning, review, and QA combined;
respect lower host limits. Count external CLI workers too. Queue the rest. Parallel writes need
isolated worktrees or disjoint owned paths; order dependent or overlapping edits.

At a final-approval checkpoint, deliver one verified batch and wait for the user's disposition
before starting another implementation batch. Never merge, deploy, or publish merely because a
batch passed its checks; honor the user's reserved final phase.

## Observe a durable plan

Maintain a compact project-local ledger, such as `.smart-delegate/coordination.md`, through a
state-keeping delegate. Reuse an existing project task tracker when suitable. Record the approved
scope, batch, task IDs, dependencies, acceptance criteria, assigned profile and invocation,
worker/session handles, status, attempts, changed artifacts or revision, and verification evidence.
Keep raw logs in artifacts, not the owner's context. Recover this state before resuming work; do
not launch duplicate workers after a context reset.

Use states such as queued, active, awaiting review, verifying, ready, and blocked. A worker finishing
is an event, not proof that the task is ready. On a completion, blocker, or dependency event, update
the ledger, check the evidence, and dispatch only the next eligible assignment. Prefer completion
notifications; when a CLI has none, use bounded status checks on its recorded process/session.
Do not continuously poll or relaunch work just because it is quiet.

Every assignment includes:

- the role name and the single task that role owns;
- the numbered acceptance criteria the assignment must satisfy, or the criteria it must judge;
- task ID, outcome, relevant plan excerpt, dependencies, owned paths or worktree, and exclusions;
- selected profile and invocation, acceptance criteria, verification commands when known, and
  available time or retry limits;
- instructions to finish in-scope work and checks without seeking approval for routine steps,
  report a genuine blocker instead of improvising scope, and avoid unassigned delegation;
- the report that role returns, in that role's format;
- a concise final report: status, changes and revision, checks and results, artifact/log locations,
  remaining risks, blockers, and any proposed plan change.

## Report contract: caveman voice

Every assignment asks the delegate to report in caveman voice. The coordinator runs on the most
expensive model, so every token a delegate returns is read again by that model. A terse, complete
report is the mechanism that keeps the coordinator's context small enough to stay on the strong
model across a long run.

Append this contract to each assignment, after the task and acceptance criteria:

    REPORT FORMAT (mandatory): Answer in caveman voice — answer first, cut ceremony, drop
    articles where meaning survives, keep every technical fact. Code, commands, paths, numbers,
    and exact error strings stay verbatim. No greeting, no recap, no closer, no "Status: done"
    padding.
    Completeness floor: terseness never removes a required fact. If the task asked for every
    item, a complete enumeration, or an exact value, give every one of them.
    Report only what the assignment asked for: findings, evidence, and any blocker.

Two properties matter, and they pull against each other:

- **Terse.** No greeting, no restating the task, no summary of what the delegate is about to do,
  no closing offer to help. Return findings, not narration.
- **Complete.** Terseness never removes a required fact. A delegate asked to enumerate every
  item returns every item. A delegate asked for an exact value returns that value, not a
  summary of it. A terse report that drops required detail is a failed report, and the
  coordinator should reject it and re-ask with the missing item named.

Where the delegate can read the caveman skill, it follows that skill's full rules, including its
exception list: security warnings, irreversible-action confirmations, ordered step sequences,
and questions to the user stay in normal prose. The coordinator asks for the report, not for a
performance.

This contract is required for cost control, not for style. It depends on the caveman skill being
installed, but a delegate without it still receives the instruction above and still returns a
terse, complete report.

The owner handles coordination and user communication, not implementation. If workers cannot be
invoked, report the delegation blocker rather than silently implementing the task yourself.

## Run in the background

Every delegated call that can take more than a few seconds runs in the background (for example
Bash `run_in_background`, or a background subagent), so the user can keep talking to the
coordinator and queue more work meanwhile. Launch independent assignments within the active
worker limit and continue on completion notifications; use bounded status checks only when the
invocation has no notification mechanism. Give long external CLI calls a time limit so a
hung worker cannot stall the run.

## Coordinate the work

1. Identify the requested outcome, constraints, authorization boundaries, and completion evidence.
2. Spawn the Criteria role to write the numbered acceptance criteria for the request. Every
   later step refers to that list, and the task is not complete until every criterion is met.
3. Split the work into the smallest useful assignments with clear inputs, outputs, and dependencies.
4. Keep dependent work ordered and launch independent assignments together when supported.
5. Give each delegate the context it needs, the acceptance criteria that apply to it, the expected
   deliverable, and a request for a concise report. Avoid passing unrelated conversation history.
6. Check returned results and artifacts against the assignment rather than accepting a success
   claim at face value. Verify by asking another agent, not by doing the work yourself.
7. Adapt the remaining work when an assumption changes, a dependency fails, or results conflict.
8. Integrate the outputs and run configured post-change stages.
9. Compare the returned verdicts against the acceptance criteria, perform proportionate final
   verification through delegates, and report one coherent result.

Keep coordination state lightweight. Share a plan with the user when it materially helps them
understand progress, but do not expose noisy internal bookkeeping.

## Run configured review and QA

Use the `review` and `qa` sections from the same Smart Delegate configuration loaded above. After
changes are complete:

- When `review` is present and `enabled` is not `false`, review the resulting diff or artifacts
  automatically. Prefer a worker that did not implement the changes when an independent delegate is
  available. Report concrete findings with evidence; do not invent issues to justify the stage.
- When `qa` is present and `enabled` is not `false`, exercise the changed behavior against the
  request and acceptance criteria automatically. Use suitable tests, checks, or focused manual
  exercises available in the environment.

When the change has a user-facing surface, QA also covers UI verification (it renders and works as
specified) and UX verification (the flow is clear, states and errors are handled, nothing
regresses). Drive the running app with screenshots or console output as evidence, and delegate the
judgment to an agent suited to design review when one is available.

Review and QA are separate: review inspects the quality and correctness of changes, while QA tests
observable behavior. They may run together only when independent. Delegate each stage through
Smart Delegate, which selects the worker when invocation is absent.

### Review before verification, always

Run review first, then verification. This order is not a preference.

Verifying a change that review is about to reject wastes the verification, and it produces exactly
the failure that erodes trust in the whole pipeline: a green verification that later turns out to
have been run against code nobody had actually checked. The Implementer's own report is a claim,
not evidence. A delegate that says "done" and passes a test it wrote has verified that its own
assumption is self-consistent, which is not the same as the change being correct.

So the sequence is:

1. **Implement.** The Implementer makes the change and reports what it did.
2. **Review.** An independent Reviewer, one that did not implement the change, inspects the diff
   and returns a verdict of approve or request changes, with findings.
3. **Correct.** Route the reviewer's findings back to the Implementer. The Reviewer does not edit.
4. **Verify, in two halves.** Both halves are required, and they fail differently.
   - *Mechanical checks:* the unit tests, integration tests, end-to-end tests, linters, type
     checks, and builds that cover the change, with each acceptance criterion checked
     independently against the request.
   - *User perspective:* the running application, exercised the way a person would use it. Does
     the flow make sense, does it look right, is it usable, are the states and errors handled,
     is the copy correct. Visual evidence goes to the Visual role with the image attached.
5. **Re-review if corrected.** A correction changes the revision, and the earlier review no longer
   certifies it. Review the corrected diff again, then rerun only the affected checks.

Mechanical checks alone are not verification. A change can pass every test and still ship a broken
flow, a confusing label, an error the user hits on the second click, or an interface that does not
match the specification. That failure mode is the reason the user-perspective half exists, and it
is invisible to a test suite by construction: the test encodes the assumption, the assumption is
what is wrong, and the test therefore passes.

When the user-perspective half was not possible — no runnable application, no display, no way to
exercise the flow — report that as an explicit limitation. Do not let a green mechanical run stand
in for it, and do not report the change as fully verified when it is only half verified.

Step 5 is what keeps the gate meaningful. Reviewing once and then correcting produces an
unreviewed revision, and that revision is exactly what gets handed to the user.

A change is ready only when it has passed review with no unresolved findings, and has passed both
verification halves on that same revision. If either half is missing, the change is not ready, and
saying so plainly is more useful than a confident "done". When review approves but verification
fails, that is a real defect in the change and the Implementer fixes it. When review requests
changes, fix those first and do not verify a revision that was never reviewed.

Feed actionable failures back into the coordination loop, apply in-scope corrections, and rerun only
affected checks. Stop after two unsuccessful correction cycles and report the evidence. When a
section is absent or has `enabled: false`, skip it unless the user explicitly requested that stage.
An explicit request for per-change review or QA takes precedence over these defaults.

For project ownership with final approval reserved to the user, require independent review of each
change, relevant behavioral checks, and integration verification for the batch. Reviewers must not
review their own implementation. After corrections, verify the final revision and rerun affected
checks; earlier results do not certify a later diff. Both verification halves are required, and a
missing user-perspective half is a reported limitation, not a pass. If CI is requested, record the
actual CI run and revision and wait for its terminal result. Missing, inaccessible, pending, or
failing CI is not green: report the batch as blocked or awaiting verification, never ready. The
owner assesses the evidence through delegates before handing off a batch with changes, findings
resolved, check/CI results, and material limitations.

## Recovery and control

- When a delegate fails, determine whether the cause is the assignment, missing context, capability,
  or an external blocker.
- Retry only when a concrete adjustment is available. Prefer a clearer assignment first, then a
  more capable Smart Delegate profile when the work itself is too difficult.
- Do not repeatedly retry the same failing action. After two unsuccessful attempts, report the blocker and the evidence needed to continue.
- Resolve conflicting delegate conclusions using primary evidence, targeted verification, or a
  focused adjudication assignment.
- Preserve the user's authority: coordination does not authorize broader edits, external actions,
  or destructive operations.

