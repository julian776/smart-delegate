---
name: smart-delegate
description: >
  Routes work to the cheapest capable agent or model and delegates execution instead of doing it
  inline. Use for installing or downloading dependencies, running commands, builds, or tests,
  finding where something is defined, writing code, tests, or docs, multi-file exploration,
  reviews, research, and any parallel or multi-step work, or when the user asks to delegate or
  use agents.
allowed-tools: Bash(python3 *load-config.py*)
---

# Smart Delegate

Delegate the work. This skill exists so the reasoning tier spends its tokens on reasoning and
delegates the rest to the cheapest model that can reliably do it. Quality comes first: pick the
least expensive model that can reliably complete the task, and prefer the more capable one when
uncertain. A weak answer from a cheaper model costs more in rework than the stronger model would
have.

This skill selects the model for an assignment and launches it. When the selected profile has an
`invocation`, follow it as the delegation mechanism (for example a CLI such as `codex` or
`opencode`). Otherwise use the host environment's own delegation tools. Run slow invocations in the
background with a time limit.

## Active configuration

Every time this skill is invoked, the active configuration is loaded by
`scripts/load-config.py` and injected below with YAML comments removed. Use only this injected
text, or the loader's own output when the host did not run the command. Do not read the
configuration files yourself, and do not ask the user to paste them.

!`python3 "${CLAUDE_SKILL_DIR}/scripts/load-config.py"`

If that line is still visible as text, the host did not run it. Run the loader yourself and use its
output as the active configuration:

    python3 <this skill's directory>/scripts/load-config.py

The loader lives next to this file, so the directory is the one holding this SKILL.md. Common
locations: `~/.agents/skills/smart-delegate/scripts/`, `~/.config/opencode/skills/smart-delegate/scripts/`,
`~/.claude/skills/smart-delegate/scripts/`. Run it with no arguments to print the active
configuration, or with `--check` to validate it. Never guess flags, and never ask the user to paste
the configuration.

The script uses the first file found and does not merge: `.smart-delegate/config.yaml` in the
current project, then `~/.config/smart-delegate/config.yaml`, then the bundled
[config.yaml](config.yaml) defaults (four tiers: Fast, Focused, Deep, Strongest, each listing
preferred model names). With no injected text and no configuration file, route using the models
and delegation tools available in the environment.

When you delegate, pass the selected profile's `invocation` text verbatim in the assignment, along
with its `description` when it helps the delegate. Do this on every delegation, not only the first.
For enabled `review` and `qa` stages, pass their `description` and `invocation` the same way.

A configuration may contain an ordered `models` list and optional `review` and `qa` stages:

```yaml
models:
  - title: Focused worker
    model: Sonnet
    priority: 10
    description: |
      Use for bounded implementation and investigation.
      Synthesize evidence into a concise result.
    invocation: |
      Invoke the configured worker with the assignment on stdin.
      Preserve the worker's structured result.

review:
  enabled: true
  description: |
    Review completed changes for correctness and regressions.
    Include maintainability findings supported by evidence.
  invocation: |
    Invoke the configured reviewer with the completed diff.
    Request prioritized findings with file references.

qa:
  enabled: true
  description: |
    Exercise changed behavior.
    Verify every acceptance criterion independently.
  invocation: |
    Run the configured QA tool against the changed behavior.
    Preserve commands, results, and failure evidence.
```

This is the only configuration file used by both Smart Delegate and Coordinator. The file, every
section, and every parameter are optional. Supported parameters are:

- `models`: list of available routing profiles. When absent or empty, select from models and tools
  available in the environment.
- `models[].title`: human-readable profile label; it does not need to match a provider model ID.
- `models[].model`: optional model name or ID, or a list of them in preference order (for example
  `[Sonnet, Terra]`). Use the first one available in the environment, passing it as the model
  parameter of the host's delegation tool when that tool accepts one, or injecting it into
  `invocation`. When absent or none is available, use the host's default model for the profile; if
  that is also unsuitable, fall back to the next suitable profile.
- `models[].description`: guidance describing which tasks suit the profile. When absent, infer
  suitability from the other fields and current environment.
- `models[].priority`: numeric preference among equally suitable profiles; lower numbers are
  preferred. Entries without it retain file order after entries with an explicit priority.
- `models[].invocation`: free-form instructions for invoking the profile through an agent, model,
  CLI, API, or other tool. Inject it into the assignment and follow it when the profile is selected.
- `review`: post-change review stage. Its presence enables automatic review unless disabled.
- `review.enabled`: boolean; `false` disables review and any other value or omission enables it.
- `review.description`: free-form review scope and selection guidance.
- `review.invocation`: free-form instructions for invoking a reviewer or review tool.
- `qa`: post-change quality-assurance stage. Its presence enables automatic QA unless disabled.
- `qa.enabled`: boolean; `false` disables QA and any other value or omission enables it.
- `qa.description`: free-form QA scope, acceptance criteria, and selection guidance.
- `qa.invocation`: free-form instructions for invoking a QA agent, test runner, or other tool.

Every `description` and `invocation` accepts a single-line YAML string or a multiline block scalar.
Use `|` to preserve line breaks exactly. Use `>` to fold wrapped lines into spaces. Preserve the
parsed text when injecting it into assignments; do not flatten, truncate, or split instructions.

Keep simple invocations inline. When invocation requires several commands, branching, retries,
substantial quoting, or reusable logic, put that behavior in a script instead of embedding it in
YAML. The `invocation` value should explain to the agent:

- the script path and required runtime;
- how to pass the assignment and any other inputs;
- expected stdout, artifacts, and exit-code meaning;
- prerequisites and safe failure behavior.

Prefer paths relative to the configuration file or project and state which base is used. The agent
must inspect the script's usage help or relevant source before its first execution, must not guess
missing arguments, and must preserve the user's authorization boundaries when running it.

Ignore empty model entries and unknown parameters that cannot inform routing. For an enabled review
or QA stage without `invocation`, select an appropriate configured profile and available delegation
mechanism. Pass enabled stages to Coordinator; Smart Delegate selects and invokes their workers.

Treat descriptions as selection guidance, not keyword rules. If no invocation is provided, use the
environment's normal delegation mechanism with the selected model. Never invent an unavailable
model or tool. If a configured invocation cannot be used, select the next suitable profile or use
the environment's normal delegation mechanism.

## Delegate the work, do not do the work

The agent running this skill is the reasoning tier. It decides what to do, writes the assignment,
judges what comes back, and talks to the user. Execution belongs to a delegate.

Delegate by default. This is executor work, however small:

- installing, downloading, or configuring a dependency, tool, or package
- running a build, test, lint, format, or any other command to produce a result
- finding where something is defined, listing usages, tracing a call path
- writing code, tests, scripts, or documentation from a decided shape or plan
- applying a change that has already been decided
- repeating one mechanical operation across many files

Keep these yourself:

- anything that needs the user: a question, a confirmation, a report
- deciding what to do, writing the assignment, and judging the delegate's result
- reading just enough to write that assignment

Delegation overhead is never a reason to keep executor work inline. Pick the cheapest profile that
can do it instead. A one-line task is still a delegation, and it goes to the cheapest tier.

When several independent assignments exist, launch them together when the environment supports it.
Give each delegate a bounded assignment and ask for conclusions or artifacts rather than raw
context.

## Route work

Compare the task against any configured profile information. Consider ambiguity, breadth, required
judgment, risk, and the cost of a weak answer. Choose the lowest-cost profile that is clearly
capable. If uncertain between candidates, choose the more capable one even when its priority is
lower.

Typical routing signals:

- Installs, downloads, command runs, lookups, exploration, and transformations need little
  judgment (Fast). This is the default tier for mechanical work, not the exception.
- Bounded implementation from a decided shape, diagnosis, review, and synthesis with clear
  instructions (Focused).
- Architecture, ambiguity, security, and tradeoffs need deeper judgment (Deep).
- Costly-to-reverse or highest-stakes decisions justify the strongest tier (Strongest).

Escalate one tier when a delegate returns a wrong or shallow result. Do not escalate because a
task looked small: smallness is not a reason to pick a stronger model.

Configuration expresses user preferences but does not override availability, safety constraints,
or explicit instructions in the current request.
