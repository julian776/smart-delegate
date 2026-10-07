---
name: coordinator
description: >
  Coordinate complex work by decomposing it into bounded assignments, delegating independent
  tasks, observing results, adapting when work fails, and synthesizing a verified outcome. Use
  when a request has multiple workstreams, dependencies, or benefits from agent orchestration.
allowed-tools: Bash(python3 *load-config.py*)
---

# Coordinator

Own the outcome while delegates perform bounded work. Maintain enough state to know what is
pending, active, complete, failed, or blocked; do not treat delegation itself as progress.

## Use Smart Delegate

Before assigning work, read [Smart Delegate](../smart-delegate/SKILL.md) for how to route, and use
the active configuration injected below (comments already removed; do not read the config files
yourself):

!`python3 "${CLAUDE_SKILL_DIR}/../smart-delegate/scripts/load-config.py"`

Pass the selected profile's `invocation` text verbatim in every assignment, each time you delegate. The coordinator decides what to delegate; Smart Delegate
decides how and where to delegate it.

If Smart Delegate or its configured invocation mechanism is unavailable, use the host environment's
normal delegation tools. Do not invent tools or model identifiers.

## Coordinate the work

1. Identify the requested outcome, constraints, authorization boundaries, and completion evidence.
2. Split the work into the smallest useful assignments with clear inputs, outputs, and dependencies.
3. Keep dependent work ordered and launch independent assignments together when supported.
4. Give each delegate the context it needs, the expected deliverable, and the relevant Smart
   Delegate profile or invocation guidance. Avoid passing unrelated conversation history.
5. Observe returned results and artifacts. Check them against the assignment rather than accepting
   a success claim at face value.
6. Adapt the remaining work when an assumption changes, a dependency fails, or results conflict.
7. Integrate the outputs and run configured post-change stages.
8. Perform proportionate final verification and report one coherent result.

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

Review and QA are separate: review inspects the quality and correctness of changes, while QA tests
observable behavior. They may run together only when independent. Inject each section's description
and invocation into its assignment, using Smart Delegate to select a worker when invocation is absent.

Feed actionable failures back into the coordination loop, apply in-scope corrections, and rerun only
affected checks. Stop after two unsuccessful correction cycles and report the evidence. When a
section is absent or has `enabled: false`, skip it without prompting the user.

## Recovery and control

- When a delegate fails, determine whether the cause is the assignment, missing context, capability,
  or an external blocker.
- Retry only when a concrete adjustment is available. Prefer a clearer assignment first, then a
  more capable Smart Delegate profile when the work itself is too difficult.
- Do not repeatedly retry the same failing action. After two unsuccessful attempts, handle the work
  directly when practical or report the blocker and the evidence needed to continue.
- Resolve conflicting delegate conclusions using primary evidence, targeted verification, or a
  focused adjudication assignment.
- Preserve the user's authority: coordination does not authorize broader edits, external actions,
  or destructive operations.

The coordinator may complete small or tightly coupled tasks directly when delegation would add more
overhead than value.
