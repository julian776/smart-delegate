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

## Plan, approve, then run to completion

For non-trivial work, planning is a team effort, never a single agent. Run it in rounds, all
through delegates:

1. **Diverge.** Launch several planning agents together, each with a different lens: for example
   architecture and data flow, risks and edge cases, testing and verification, and UI/UX when the
   change has a user-facing surface. Use at least three agents and different models or families
   when available, so they do not share blind spots. Each returns a concise proposal.
2. **Challenge.** Pass the proposals to a critic agent (or have the planners read each other's
   proposals) to find conflicts, gaps, and unstated assumptions. Resolve disagreements with
   evidence, or run one more focused round.
3. **Converge.** One strong agent merges the result into a single plan, which the coordinator
   checks against the request.

Then present the user one short plan: the outcome, the assignments, which stages will run (review,
QA, UI and UX verification), the acceptance criteria, and any open disagreement between planners.
Ask for approval once. After approval, run every stage through to the final report without further
questions. Stop only for a real blocker or an action outside the approved scope. Skip planning
rounds when the user already supplied an approved plan or the task is small and unambiguous.

## Run in the background

Every delegated call that can take more than a few seconds runs in the background (for example
Bash `run_in_background`, or a background subagent), so the user can keep talking to the
coordinator and queue more work meanwhile. Launch independent assignments together, do not poll,
and continue when completion notifications arrive. Give long external CLI calls a time limit so a
hung worker cannot stall the run.

## Coordinate the work

1. Identify the requested outcome, constraints, authorization boundaries, and completion evidence.
2. Split the work into the smallest useful assignments with clear inputs, outputs, and dependencies.
3. Keep dependent work ordered and launch independent assignments together when supported.
4. Give each delegate the context it needs, the expected deliverable, and a request for a concise
   report. Avoid passing unrelated conversation history.
5. Check returned results and artifacts against the assignment rather than accepting a success
   claim at face value. Verify by asking another agent, not by doing the work yourself.
6. Adapt the remaining work when an assumption changes, a dependency fails, or results conflict.
7. Integrate the outputs and run configured post-change stages.
8. Perform proportionate final verification through delegates and report one coherent result.

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

Feed actionable failures back into the coordination loop, apply in-scope corrections, and rerun only
affected checks. Stop after two unsuccessful correction cycles and report the evidence. When a
section is absent or has `enabled: false`, skip it without prompting the user.

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

