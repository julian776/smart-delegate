# Smart Delegate

A provider-agnostic plugin for **intelligent multi-agent coordination**. It separates four concerns: project knowledge (project skills), model routing (Smart Delegate), issue orchestration (Coordinator), and independent evaluation (Verification).

Assign one engineering issue and leave. Coordinator owns it from acceptance criteria through implementation, independent review, behavioral verification, corrections, and the PR/CI lifecycle. It returns either a verified, merge-ready result or an actionable blocker. Routine failures do not come back to you.

## Skills

- **Coordinator** is accountable for the quality and output of the task. It never implements work itself: it decomposes, delegates, checks what every agent reports back, recovers from failures, and synthesizes a verified outcome. In autonomous issue mode it owns one issue through a mechanically gated completion check.
- **Smart Delegate** selects a suitable configured profile, model, and invocation mechanism for each assignment.
- **Verification** independently exercises the delivered revision and returns a PASS, FAIL, or NOT VERIFIED verdict per acceptance criterion, with reproducible evidence.
- **create-operation-skill** and **create-verification-skill** prepare a repository: they discover existing project skills, then register, minimally adapt, or generate one that teaches agents how to run an operation or exercise an application.

Use Coordinator for multi-step or multi-agent work. It automatically applies Smart Delegate when choosing how each assignment should run, and Verification when behavioral evidence is required.

## Philosophy

Most token-saving tools cut corners: shorter responses, smaller models everywhere, fewer tool calls. Smart Delegate takes the opposite approach — **spend tokens wisely, not fewer tokens blindly**.

- A wrong answer from a lightweight model costs more in rework than using a stronger model would have
- A general-purpose model can waste time on architecture review when a deeper reasoner gets it right the first try
- 10 files read into main context costs more than one focused subagent reading all 10

The savings come from **delegation efficiency**: parallel execution, context isolation, and matching model capability to task complexity.

## How It Works

### Model Routing

Every task gets matched to a capability tier. With no configuration of your own, the bundled defaults in `skills/smart-delegate/config.yaml` apply:

| Tier | Models (first available) | When to use |
|------|--------------------------|-------------|
| **Fast** | OpenCode DeepSeek Flash Free, then Haiku or Luna through the host | Simple, low-risk tasks with one verifiable answer — exploration, searches, extraction, boilerplate |
| **Focused** | Sonnet, Terra | Well-scoped tasks with clear instructions — implementation, tests, bug diagnosis, routine review |
| **Deep** | Opus, Sol | Ambiguous or difficult work — architecture, refactor planning, security analysis, tradeoffs |
| **Strongest** | Fable | Highest-stakes or hardest problems — costly-to-reverse decisions, final verification |

Quality comes first: when a task sits between two tiers, the stronger one wins. Smart Delegate selects the model *and* launches the worker: a profile with an `invocation` is run through that command (for example `codex exec` or `opencode run`), and a profile without one falls back to the host environment's own delegation tools. Any config file you create (project or user-wide) replaces these defaults entirely.

OpenCode is optional. When the CLI or free model is unavailable, Smart Delegate records the reason and uses the next suitable profile. The configuration check may warn about a missing OpenCode executable even when the native fallback is available. Model names such as Haiku and Luna select workers through the host. External routes specify an explicit invocation.

### Roles and the completion rule

A configuration may describe **roles** instead of capability tiers. A role is one job with one model,
one expected report, and explicit boundaries: Explorer, Implementer, Planner, Criteria, Reviewer,
QA, QA user perspective, Visual. The coordinator spawns a role, never a generic agent, and every
assignment names the role, the single task, the boundaries, and the report that role returns.

The same role can be spawned several times — several Implementers on disjoint paths, several
Reviewers on separate diffs — and each one still gets exactly one task.

**A task is complete when its acceptance criteria are met.** Not when a delegate says it is done,
not when the code compiles, not when the tests pass. Before the work starts, the coordinator spawns
the Criteria role to turn the request into a numbered list where each criterion is observable and
names the check that decides it. "The function returns the correct result" is not a criterion;
"subtract(5, 3) returns 2, verified by the test suite" is. Every later role receives that list,
and QA returns a verdict per criterion with the evidence that decided it. A criterion with no
deciding check counts as unmet.

This is what makes the difference, and it is measurable. The same buggy change, judged by the same
model, was caught only when the criteria named the deciding check literally:

| Criteria | Verdict on buggy code |
|---|---|
| "calc.py defines subtract(a, b) returning a - b" | **PASS** — bug missed |
| "returns a - b — check: the return expression is a - b" | **UNMET** — bug caught |

The free-text form noticed the code branched on `isinstance` and passed it anyway as a footnote.
The literal check made it a failure. The Criteria role writes the deciding check, and that check
is what the defect walks into.

#### Verification has two mandatory halves

Both are required, and they fail differently:

1. **Mechanical checks.** Unit tests, integration tests, end-to-end tests, linters, type checks,
   builds. Each acceptance criterion checked independently.
2. **User perspective.** The running application, exercised the way a person would use it. Does the
   flow make sense, does it look right, is it usable, are the states and errors handled, is the
   copy correct. Visual evidence goes to the Visual role with the image attached.

Mechanical checks alone are not verification. A change can pass every test and still ship a broken
flow or an error the user hits on the second click. That failure mode is invisible to a test suite
by construction: the test encodes the assumption, the assumption is what is wrong, and the test
therefore passes. When the user-perspective half is not possible, report it as an explicit
limitation rather than letting a green mechanical run stand in for it.

#### Order: implement, review, correct, verify

Review runs before verification, always. Verifying a change that review is about to reject wastes
the verification and produces exactly the outcome that erodes trust in the pipeline — a green
result on code nobody checked. The Implementer's own report is a claim; the Reviewer's verdict and
QA's evidence are the two independent things that make a change ready.

```
implement -> review -> correct -> verify (both halves) -> re-review if corrected -> ready
```

A correction changes the revision, so the earlier review no longer certifies it. Reviewing once
and then correcting leaves an unreviewed revision, and that revision is what reaches the user.

### Autonomous issue execution

Assign one issue, authorize the repository and delivery state, and leave. Coordinator discovers project capabilities, delegates acceptance criteria, implements, reviews, verifies, corrects, opens or updates the PR, watches required CI, and terminates with evidence.

**Input**: issue objective, repository, execution permissions, resource budget, optional acceptance criteria and project constraints.
**Output**: final status, implementation revision, evidence per criterion, PR state, resource consumption, blockers.

This is the complete interface a future Project Coordinator, CLI, or Linear integration needs. It does not need to know about internal review, correction, or verification steps.

The loop:

```
intake -> discover skills -> criteria -> implement -> independent review
  -> correct -> independent verification -> PR -> required CI -> gate -> report
```

Review precedes verification, because verifying a revision that review will reject wastes the run. PR creation may start earlier when it shortens the loop. A correction pins a new revision, invalidates evidence tied to the old one, and re-runs only affected checks.

Three execution profiles, selected by the coordinator without asking the user:

| Profile | Use for | Work |
|---|---|---|
| Lightweight | docs, mechanical, contained fixes | minimal criteria, implementation, independent review plus an appropriate check, CI |
| Standard | ordinary bugs, features, API and UI changes | criteria, implementation, review, behavioral verification, corrections, PR and CI |
| Enhanced | performance, concurrency, security, complex integration | standard plus specialist investigation and stronger or additional independent evaluation |

**Acceptance criteria are recorded before implementation.** Each criterion names an observable outcome and its deciding check. The coordinator may amend one when investigation proves an assumption wrong, but only with a justification and independent approval, and the change is recorded. The completion gate rejects an edit made outside that record, so a criterion cannot be silently weakened to make a failing implementation pass.

**Independent evaluation is mandatory.** The Implementer never approves its own work. Reviewer and Verifier are separate responsibilities and separate execution contexts; the gate rejects a reviewer or verifier named as an implementer. Different model families improve independence when risk justifies the cost, but separation matters more than vendor diversity.

**State, recovery, and budgets.** One issue's state lives in `.smart-delegate/issues/<id>.json`, written through the coordinator's state script:

```bash
python3 skills/coordinator/scripts/issue-state.py --issue PAY-142 init \
  --objective "Add transaction export" --implementer "Implementer profile" \
  --criteria criteria.md --revision abc123

python3 skills/coordinator/scripts/issue-state.py --issue PAY-142 status
python3 skills/coordinator/scripts/issue-state.py --issue PAY-142 gate
python3 skills/coordinator/scripts/issue-state.py --issue PAY-142 report --write
```

`gate` exits 0 only when every criterion is PASS with evidence on the delivered revision, an independent reviewer approved that revision with no blocking findings, required CI is green on that revision, the PR is in its authorized state, no blocker remains, and the budget is not exhausted. Exit 1 lists open gates, exit 3 is a recorded blocker, exit 4 is an exhausted budget. On interruption, read the state, reconcile the branch and PR, and resume from the recorded phase without duplicating implementation, workers, or PRs.

Limits come from the optional `execution` configuration section: `max_delegates` (default 3), `max_correction_cycles` (default 3), `deadline`, `delivery`, `auto_merge`, and `max_model_cost_usd`. After three correction cycles without meaningful progress, the coordinator changes strategy or reports a blocker instead of repeating the same failing action.

**Termination is evidence-based.** A completion report is concise:

```
PAY-142 — Payments endpoint optimization
Status: Verified, merge ready.
Outcome: p95 latency 200 ms -> 46 ms on the defined workload.
Criteria: latency PASS, payment correctness PASS, idempotency PASS, tenant isolation PASS.
Review: no unresolved blocking findings.
CI: all required checks passed at revision 9f2c1ab.
Corrections: 2. Human interventions: 0.
PR: https://github.com/example/repo/pull/142
Resources: 41 min, 6 delegates, cost not reported by provider.
```

A blocker report states the exact problem, attempted solutions, remaining options, and the human action required:

```
BT-81 — Historical market data integration
Status: Blocked (credentials).
Completed: implementation, unit tests, independent review.
Blocker: development provider API credentials unavailable.
Attempted: existing dev config, local mocks, provider sandbox.
Required action: provide authorized development credentials or approve mock-based verification.
```

NOT VERIFIED is never reported as PASS, and missing or pending CI is never reported as green.

Host limitation: autonomous execution needs a host that can run delegated work without continuous human turns. Claude Code background agents, OpenCode `run`, Codex `exec`, and similar CLI invocations satisfy this when run in the background. A Markdown skill alone does not create a scheduler; use `nohup`, `tmux`, or `systemd-run` around the configured CLI when the host has no background mechanism, and resume from the state file. Do not build a separate orchestration runtime for the MVP.

### Project skills

Project skills teach agents how to operate a particular repository: run a backtest, start an application, authenticate in development, replay an event, seed data, run a benchmark. They are useful to humans and other agents without Smart Delegate. They must not contain issue orchestration policy.

Setup skills generate, register, or adapt them. Both discover first:

```bash
python3 skills/coordinator/scripts/discover-skills.py --project "$PWD"
python3 skills/coordinator/scripts/discover-skills.py --project "$PWD" --registered --json
```

Discovery reads frontmatter only, so a catalog costs a few hundred tokens instead of every skill body. Coordinator loads full instructions only when an assignment needs them and passes the location to the delegate. Unregistered skills remain usable through normal repository context; they are never registered or rewritten during issue execution.

Registration is three optional metadata keys:

```yaml
---
name: run-backtest
description: Execute local strategy backtests.
metadata:
  smart-delegate: "true"
  smart-delegate-type: operation
  smart-delegate-capabilities: backtesting,simulation
---
```

`smart-delegate-type` accepts `operation`, `verification`, or both. Registration means discoverable; it does not imply Smart Delegate ownership, certification, exclusive use, or permission to run sensitive operations. A malformed or missing field produces a warning and never blocks issue execution.

Registering an existing skill changes only those keys. The body, description, other metadata, references, and formatting stay byte-for-byte unchanged, and registration does not trigger a validation ceremony:

```bash
python3 skills/coordinator/scripts/skill-metadata.py register \
  .agents/skills/run-backtest/SKILL.md --type operation --capabilities backtesting
```

When an existing skill genuinely lacks operational information, the user may authorize a minimal adaptation. The setup skills present the existing capabilities, the real gap, and a recommendation, then ask whether to register, adapt, create a separate skill, or change nothing. No file is modified before that choice. New skills are validated by an agent that did not write them, using the actual commands; unverified instructions are reported rather than claimed.

Generated skills follow the caveman writing standard: imperative, exact commands and paths, explicit parameters and output locations, no filler, no invented commands, and progressive disclosure through `references/`. Complete [operation](examples/project-skills/run-backtest/SKILL.md) and [verification](examples/project-skills/verify-backtest-platform/SKILL.md) examples are in the repository. The shared discovery, authorization, generation, and validation workflow is in [setup-workflow.md](skills/create-operation-skill/references/setup-workflow.md).

### Choosing models by measurement, not by tier name

A model name implies nothing about how good it is at a given job. Measure the job.

On the same reviewer task — a buggy Python function pasted inline, same model family, same
prompt — DeepSeek V4.1 Flash found every defect that Qwen3.8 Max found, **plus two more**: `Decimal`
truncation, and scientific notation like `"1e3"` raising `ValueError` through `int()`. It also
*executed* the function to produce verified repros rather than reasoning about the code. As the
Criteria role it produced deciding checks plus float-tolerance edge cases (`0.1 - 0.05`, and
`5.5 - 2.2` needing an epsilon comparison) that were not obvious in advance.

Its rates are $0.30/$1.20 per 1M with a **$0.006 cached-read rate**, roughly 5x cheaper than the
next best. Cached reads dominate agent cost because the context is re-read on every turn, so the
cheapest cached rate is often the cheapest route, regardless of the sticker rate.

Two checks worth running before you commit a model to a role:

- **Vision.** Attach an image and ask the model to describe it. Models differ sharply here, and a
  blind model routed a visual task fails outright rather than degrading. DeepSeek V4 Pro and
  GLM 5.3 both refused image input; DeepSeek V4.1 Flash, Qwen3.8 Flash, GLM 5.3 Flash, MiniMax
  M3, Qwen3.8 Max, HY4, and Grok 4.7 all read images.
- **Whether the model actually runs the code.** A model that executes the function finds a
  different class of defect than one that reads it, and the executed repro is evidence the
  coordinator can record.

### Configuration

Smart Delegate and Coordinator use the same optional general configuration file. Create `.smart-delegate/config.yaml` in a project, or `~/.config/smart-delegate/config.yaml` for user-wide preferences. Each time a skill is invoked, `skills/smart-delegate/scripts/load-config.py` loads the first available file (project, then user, then bundled defaults; no merging) and injects it into the model's context with comments stripped, so comments cost no tokens. Only full-line `#` comments are removed; text inside `|` and `>` blocks are kept exactly. Claude Code runs that command while loading the skill; hosts that do not execute commands inside skill files (OpenCode, for example) instruct the agent to run the loader itself, so the same routing table is available in every host.

```yaml
models:
  - title: Fast local model
    model: [Sonnet, Terra]
    priority: 10
    description: |
      Use for private, mechanical tasks.
      Prefer work that fits in a small context.
    invocation: |
      Run `my-agent --model local-fast`.
      Pass the complete assignment on stdin.

  - title: Best available reasoner
    priority: 20
    description: Use for ambiguous, high-impact work where quality matters most.

  # A role: one job, one model, one expected report, explicit boundaries.
  - title: Reviewer
    priority: 40
    description: >
      Judges completed work. Reviews a diff for correctness, regressions, and security problems.
      MUST NOT: edit any file or fix anything. A reviewer never writes.
      A reviewer must not review a change it implemented.
      Returns: a verdict of approve or request changes, then each finding with its file
      reference and why it matters, most severe first. Report "no findings" plainly when the
      work is sound.
    invocation: |
      Run `opencode run --agent plan --model provider/reviewer-model --format json --archived "$assignment"`.
      The `--agent plan` flag is required for this role: it is the one that cannot edit.
      Capture stdout, stderr, exit status, and the final `step_finish` event.

review:
  enabled: true
  description: |
    Review completed changes for regressions.
    Include maintainability findings with evidence.
    Run this stage BEFORE verification.
  invocation: |
    Route through the Reviewer role's invocation.
    Pass the completed diff and the acceptance criteria on stdin.
    Record the revision that was reviewed.
qa:
  enabled: true
  description: |
    Exercise changed behavior.
    Verify the request's acceptance criteria.
  invocation: |
    Run `my-qa-tool --changed`.
    Summarize failures and preserve command output.

execution:
  max_delegates: 3
  max_correction_cycles: 3
  delivery: merge-ready
  auto_merge: false
```

The file, every section, and every parameter are optional:

| Parameter | Meaning |
|-----------|---------|
| `models` | List of available routing profiles. Environment defaults are used when omitted. |
| `models[].title` | Human-readable label; it does not need to be a provider model ID. |
| `models[].model` | Optional model name/ID or list in preference order (for example `[Sonnet, Terra]`). The first available is used; the host default applies when omitted. |
| `models[].description` | Guidance describing the work suited to the profile. |
| `models[].priority` | Numeric preference among equally suitable profiles; lower numbers win. |
| `models[].invocation` | Free-form instructions for invoking the agent, model, CLI, API, or tool. |
| `review` | Enables automatic post-change review when present, unless explicitly disabled. |
| `review.enabled` | Set to `false` to disable review; omission means enabled. |
| `review.description` | Free-form review scope and worker-selection guidance. |
| `review.invocation` | Free-form instructions for invoking the reviewer or review tool. |
| `qa` | Enables automatic post-change behavioral QA when present, unless explicitly disabled. |
| `qa.enabled` | Set to `false` to disable QA; omission means enabled. |
| `qa.description` | Free-form QA scope, acceptance criteria, and worker-selection guidance. |
| `qa.invocation` | Free-form instructions for invoking the QA agent, test runner, or tool. |
| `execution` | Optional autonomous issue limits, read by Coordinator. |
| `execution.max_delegates` | Maximum concurrent delegated workers; default 3. |
| `execution.max_correction_cycles` | Corrections allowed before strategy change or blocker; default 3. |
| `execution.deadline` | ISO 8601 deadline for the issue, for example `2026-11-26T18:00:00Z`. |
| `execution.delivery` | `merge-ready` (default) or `merged`; `merged` requires explicit authorization. |
| `execution.auto_merge` | Boolean; `true` only where merge authorization is explicit. |
| `execution.max_model_cost_usd` | Optional spend ceiling when the provider reports cost. |

All `description` and `invocation` parameters accept single-line or multiline YAML strings. Use `|`
when line breaks are meaningful and `>` when wrapped lines should be folded into a paragraph. The
plugin preserves the parsed multiline value when injecting it into an assignment.

#### Examples: multiple providers

Choose one complete configuration; examples are alternatives, not files to merge:

| Example | Profiles | When to use |
|---------|----------|-------------|
| [Compact](examples/multi-provider.config.yaml) | 8 reader/writer profiles with model placeholders | Start with a small routing pool and native Claude fallback. |
| [Expanded](examples/multi-provider-expanded.config.yaml) | 14 reader/writer profiles with concrete model IDs | Reuse a larger pool across computers, invoking OpenCode, Claude, and Codex through their CLIs. |

The compact example routes both readers and writers through Fast OpenCode MiniMax, Focused
OpenCode DeepSeek, Deep Codex, and Deep fallback native Claude Sonnet. The host does not need
to be Claude for external CLI routes; native Claude fallback requires a host that can launch it.

The expanded example adds more escalation choices and uses external CLIs for every profile:

| Tier | Reader and writer model | Invocation |
|------|-------------------------|------------|
| Fast | MiniMax M3 | OpenCode |
| Focused | DeepSeek V4.1 Flash | OpenCode |
| Deep | DeepSeek V4 Pro | OpenCode |
| Deep, different-family fallback | Claude Sonnet 5.5 | Claude CLI |
| Advanced | GPT-6.1 Sol | Codex CLI |
| Expert | Claude Opus 5.5 | Claude CLI |
| Strongest | GPT-6 Astra | Codex CLI |

Its concrete IDs reflect research on November 15, 2026, not a guarantee of current account
access. This is a proposed escalation policy, not a benchmark ranking. Keep ordinary work on
capable lower tiers; the larger pool does not require more agents or calls per task.

Readers investigate, diagnose, plan, and review without project edits. Writers implement within
assigned paths and run relevant checks. Both examples use OpenCode `plan` versus `build`, and
Codex `read-only` versus `workspace-write`. These controls differ: an agent's plan policy is not
an operating-system sandbox. Checks that generate build artifacts may need a writer in an
isolated worktree. Role names are routing guidance in existing `title` and `description` fields;
there are no new `reader` or `writer` configuration keys.

Choose the role first, then a capable tier. Independent review selects a reader other than the
implementer, preferably from another model family for substantive changes. Both review and QA
are enabled in both examples; bundled defaults leave them optional. A routine batch does not need
a strongest-model pass.

Neither example is loaded automatically. From a checkout, copy your chosen example to
`~/.config/smart-delegate/config.yaml`, preserving any existing configuration first.

For a new computer without a checkout, this Bash recipe installs all five skills globally and
downloads the expanded configuration. Change `routing_example` to `multi-provider.config.yaml`
for the compact version. It backs up any existing config and downloads before replacing it:

```bash
npx skills add https://github.com/julian776/smart-delegate -g --skill smart-delegate
npx skills add https://github.com/julian776/smart-delegate -g --skill coordinator
npx skills add https://github.com/julian776/smart-delegate -g --skill verification
npx skills add https://github.com/julian776/smart-delegate -g --skill create-operation-skill
npx skills add https://github.com/julian776/smart-delegate -g --skill create-verification-skill

(
  set -e
  routing_example=multi-provider-expanded.config.yaml
  routing_dir="$HOME/.config/smart-delegate"
  mkdir -p "$routing_dir"
  routing_download=$(mktemp "$routing_dir/config.download.XXXXXX")
  trap 'rm -f "$routing_download"' EXIT
  curl --fail --location \
    "https://raw.githubusercontent.com/julian776/smart-delegate/main/examples/$routing_example" \
    --output "$routing_download"
  if [ -e "$routing_dir/config.yaml" ]; then
    routing_backup=$(mktemp "$routing_dir/config.backup.XXXXXX")
    cp -p "$routing_dir/config.yaml" "$routing_backup"
  fi
  mv "$routing_download" "$routing_dir/config.yaml"
)
```

Inspect and adapt the downloaded configuration before invoking the skills. For the compact
example, replace `<minimax-provider/model>`, `<deepseek-provider/model>`, and `<codex-model>`.
For the expanded example, confirm the concrete IDs are available to your accounts. Install and
authenticate the required CLIs separately on each computer; installing skills grants no provider
access and copies no credentials. Console, Go, and direct OpenCode providers can have different
IDs and billing. Inspect `opencode models` and each CLI's help before using a route. Neither
example has been validated with live cross-provider calls.

For project-only routing, copy to `.smart-delegate/config.yaml` instead. That project file takes
precedence over the entire personal file. Keep personal routing outside the installed skill so
skill updates do not replace your preferences. Run the installed `smart-delegate` skill's
`scripts/load-config.py --check` from the target project to check the selected file, YAML, model
titles, and CLI presence. This check does not verify authentication, model access, or execution.

#### Complex invocations

Keep short calls inline. For multi-step commands, branching, retries, substantial quoting, or logic
shared by several profiles, put the implementation in a script and use `invocation` to teach the
agent how to run it:

```yaml
review:
  invocation: |
    Run `.smart-delegate/scripts/review.sh` from the project root.
    Pass the complete review assignment on stdin.
    Read JSON findings from stdout.
    Exit code 0 means the review completed, even when findings exist.
    A nonzero exit means execution failed; preserve and report stderr.
```

Document the script path and runtime, working directory, inputs, outputs or generated artifacts,
exit-code semantics, prerequisites, and safe failure behavior. Paths should be relative to the
configuration file or project, with the base stated explicitly. The agent should inspect the
script's help or relevant source before first use and must not guess missing arguments.

Review inspects the quality and correctness of the changes. QA exercises observable behavior. Coordinator runs enabled stages automatically, routes them through Smart Delegate, and feeds actionable failures back into the correction loop.

### Owner and follower coordination

Coordinator holds one durable plan and observes worker completion and blocker events. Workers
receive bounded tasks, finish implementation and checks, and report evidence back. They do not
expand scope or create more agents without an explicit assignment. The owner delegates execution
and verifies results through independent workers.

For ongoing project ownership, the defaults are three tasks per batch (maximum five) and at most
three active delegates, including external CLI workers. At the user's final-approval checkpoint,
the owner hands over one verified batch and waits before implementing another. Explicit requests
for reviews, QA, or CI apply even when optional configuration sections are absent or disabled.
Requested CI must pass on the final revision before the batch is called ready.

The project-local ledger records assignments, dependencies, worker handles, routing, revisions,
and verification evidence, allowing coordination to resume without duplicating work. Routine work
uses one concise plan; extra planning agents are reserved for ambiguity or risk.

### Provider selection

Configured external invocations execute through their own provider, even when the host cannot
spawn that model natively. Native agents have no automatic preference. Capability and configured
priority determine selection; failed routes and fallbacks are recorded rather than silently
replaced. Provider diversity does not require redundant calls on every task.

Both multi-provider examples separate **Reader** (investigation and review) from **Writer**
(assigned edits and checks) at each tier. They route small mechanical tasks to OpenCode MiniMax,
routine work to OpenCode DeepSeek, and complex work to higher-capability profiles. The compact
example uses native Claude fallback; the expanded example invokes Claude through its CLI.
Select the role first, then the lowest capable tier; reader and writer descriptions guide routing
and do not enforce filesystem permissions. Independent review selects a separate reader worker.
Both require installed, authenticated CLIs and accessible model IDs. Replace the compact
example's placeholders or verify the expanded example's concrete IDs. Installing the plugin alone
does not configure access to other providers.

### The Upgrade Rule

> **When in doubt between two tiers, always use the higher one.**

This is the core principle. The cost difference between capability profiles is small compared to the cost of re-doing work because a cheaper model gave a wrong or shallow answer.

### The Report Contract

Delegates report in **caveman voice**: answer first, cut ceremony, drop articles where meaning
survives, keep every technical fact. Code, commands, paths, numbers, and exact error strings stay
verbatim. No greeting, no recap, no closing offer to help.

This is a cost control, not a style choice. The coordinator runs on the most expensive model, and
every token a delegate returns is read again by that model. A terse report is what keeps the
coordinator's context small enough to stay on the strong model across a long run. Measured on an
identical task with the same model, the contract cut returned output tokens by roughly a quarter;
the savings grow as the delegate has more to narrate.

Two properties pull against each other, and both are required:

- **Terse.** Return findings, not narration.
- **Complete.** Terseness never removes a required fact. A delegate asked to enumerate every
  item returns every item; one asked for an exact value returns that value, not a summary of it.
  A terse report that drops required detail is a failed report — reject it and re-ask with the
  missing item named.

Where the delegate can read the [caveman skill](https://skills.sh/juliusbrussee/caveman/caveman),
it follows that skill's full rules, including its exception list: security warnings,
irreversible-action confirmations, ordered step sequences, and questions to the user stay in
normal prose.

**The caveman skill is required for the full behavior.** It supplies the rules, the persistence
model, and the exception list. Without it installed, delegates still receive the report-format
instruction above — they still return a terse, complete report — but they lose the skill's
judgment about when terseness should yield to clarity. Install it with:

```
npx skills add JuliusBrussee/caveman@caveman -g
```

The contract ships in every bundled and example configuration, and every execution skill appends it
to each assignment. Configurations that define their own `invocation` should keep the contract block
in those invocations; profiles without an `invocation` get it from the skills themselves.

### Subagent Spawning

The reasoning tier plans and judges; delegates execute. Delegation is the default, not the
exception, and a task being small is never a reason to execute it inline:

- **Executor work** — installing or downloading dependencies, running a command, build, or test,
  locating where something is defined, writing code from an agreed shape, repeating one mechanical
  edit across files
- **Parallelizable** — independent tasks run concurrently within the owner's capacity limit
- **Exploratory** — reading 3+ files to answer a question
- **Context-heavy** — results would pollute the main conversation with noise
- **Isolatable** — clear inputs and outputs, no user interaction needed

Delegation overhead is never a reason to keep executor work inline: pick the cheapest profile
that can do it. A one-line task is still a delegation, and it goes to the cheapest tier. The
reasoning tier keeps the work that needs reasoning: deciding what to do, writing the assignment,
judging the result, and talking to the user.

## Installation

### Recommended: skills.sh (all your environments)

```bash
npx skills add julian776/smart-delegate -g
```

`-g` installs globally, so the execution skills (`smart-delegate`, `coordinator`, `verification`)
and the setup skills (`create-operation-skill`, `create-verification-skill`) are available in every
project and every supported agent. Update later with `npx skills update`.

The setup skills call scripts from the coordinator skill directory. Install them from the same
repository, or keep the five skill directories together; without its sibling coordinator, a setup
skill cannot discover or register skills.

### Alternative: Claude Code plugin

#### Step 1: Add the marketplace

From within Claude Code, add this repository as a plugin marketplace:

```
/plugin marketplace add julian776/smart-delegate
```

#### Step 2: Install the plugin

```
/plugin install smart-delegate@julian776-smart-delegate
```

Choose your preferred scope when prompted:
- **User** (recommended) — applies across all your projects
- **Project** — shared with collaborators via `.claude/settings.json`
- **Local** — just you, just this repo

### Alternative: Local development

Clone and load directly with `--plugin-dir` (useful for testing or customization):

```bash
git clone https://github.com/julian776/smart-delegate.git
claude --plugin-dir ./smart-delegate
```

## Usage

The skill auto-triggers when the host agent is about to:
- Install or download a dependency, tool, or package
- Run a command, build, test, or linter
- Find where something is defined, or list usages
- Write code, tests, scripts, or documentation
- Explore multiple files across a codebase
- Run code reviews
- Perform research tasks
- Handle any work that benefits from parallel agents

You can also invoke it explicitly:

For the Claude Code plugin:

```
/smart-delegate:smart-delegate
/smart-delegate:coordinator
```

For skills.sh installations, invoke `smart-delegate` or `coordinator` using the host's skill
syntax (for example `$coordinator` in Codex). Plugin-prefixed commands apply to the Claude plugin.

For ongoing ownership, an example request is:

> Own this project's small, safe fixes. Delegate implementation, independently review each
> change, and verify checks and CI on the final revision. Deliver three related tasks per batch,
> with no more than three workers active. I will review the verified batch and handle deployment.

The owner keeps assignments and evidence in a project-local ledger, such as
`.smart-delegate/coordination.md`, and pauses at the final-approval checkpoint. A missing worker
route or unavailable CI is reported as a blocker, not silently replaced by inline implementation
or a claim that checks passed.

For autonomous issue ownership, assign the issue and the delivery boundary:

> Own PAY-142. Add transaction history export to the account page. Work on an isolated branch,
> deliver a verified, green, merge-ready PR, and do not merge or deploy. Verify tenant isolation
> and idempotency independently. Report any genuine blocker.

Coordinator returns the concise completion or blocker report. It does not ask for review,
correction, verification, or CI follow-up in between.

Setup skills are invoked when preparing a repository:

```
$create-operation-skill how to run the local strategy backtest
$create-verification-skill how to exercise the dashboard in the dev environment
```

Both discover existing skills first and present the register, adapt, create, or leave choice. They
modify nothing without authorization.

## Validation and tests

Run the automated suite from the repository root:

```bash
python3 -m unittest discover -s tests
```

It covers the completion gate, evidence invalidation after a revision change, independent-reviewer
enforcement, amendment and tamper detection, blocker and budget termination, persistence and
recovery, skill discovery with malformed metadata, byte-preserving registration, config validation,
and the skill contracts.

[SCENARIOS.md](tests/SCENARIOS.md) maps MVP acceptance scenarios A-U to automated coverage or a
reproducible manual procedure. Real multi-repository pilot results are not reported here: no
representative external projects were assigned in this environment. The pilot procedure and metrics
are documented so results can be collected without fabrication. This repository's own MVP work was
executed as one issue: criteria recorded, tests run, independent review and behavioral verification
returned against the final revision.

Known limitations:

- **Unattended run depends on the host.** Coordinator is a skill, not a scheduler. Use a host with
  background agents or run the configured CLI in the background and resume from the state file.
- **Model cost is often unavailable.** The state records it only when the provider reports it;
  otherwise the report says `not reported`.
- **CI applies only when the repository defines checks.** A missing workflow is reported as not
  applicable, never as green.
- **Merging is not automatic.** Default delivery is a verified, merge-ready PR. `auto_merge` and
  `delivery: merged` require explicit authorization.
- **Skill discovery is convention-based.** It scans the standard project and user skill roots plus
  `SMART_DELEGATE_SKILL_PATHS`. A host with a different layout must pass `--path`.
- **Verification quality still depends on the assignment.** A criterion with a vague deciding check
  produces vague evidence; the gate rejects missing checks but cannot measure how decisive an
  existing check is.

## Routing Examples

### Fast tier
- "Find all files matching `*.test.ts`"
- "Search for `DatabaseConnection` in the codebase"
- "Extract all environment variables from this config"
- "Convert this JSON schema to TypeScript types"
- "Install the missing dependency and confirm the build passes"

### Focused tier
- "How does the authentication middleware work?"
- "Review this PR for code quality issues"
- "Write unit tests for the `UserService` class"
- "Why does the build fail when running on CI?"

### Deep tier
- "Design the data model for the new billing system"
- "Is this migration safe under concurrent writes?"
- "What's the best approach to decompose this monolith?"
- "Review for security vulnerabilities in the auth flow"

## What This Is NOT

- **Not a compression tool** — responses stay full-quality, full-length
- **Not a cost-mode toggle** — there's no "strict" or "lite" mode that degrades output
- **Not a blunt instrument** — every routing decision is context-dependent, with an explicit bias toward quality when uncertain

## Comparison with Other Approaches

| Approach | Strategy | Risk |
|----------|----------|------|
| Output compression (Caveman, etc.) | Fewer tokens per response | Can lose nuance in complex explanations |
| Blanket model downgrade | Always use cheapest model | Wrong answers → expensive rework |
| **Smart Delegate** | Right model per task + parallel subagents | Slightly higher per-task cost, but fewer wasted cycles |

Smart Delegate **stacks** with compression tools. Use Caveman for output style + Smart Delegate for execution routing — they target different parts of the token budget.

## Project Structure

```
smart-delegate/
├── examples/
│   ├── multi-provider.config.yaml # Compact reader/writer routing example
│   ├── multi-provider-expanded.config.yaml # Expanded pool with concrete model IDs
│   └── project-skills/            # Generated operation and verification examples
├── .claude-plugin/
│   └── plugin.json                # Claude Code plugin manifest
├── tests/                         # Standard-library unittest suite and scenario map
└── skills/
    ├── coordinator/
    │   ├── SKILL.md               # Supervised and autonomous issue orchestration
    │   └── scripts/
    │       ├── issue-state.py     # Persistence, recovery, budgets, completion gate
    │       ├── discover-skills.py # Frontmatter-only capability catalog
    │       └── skill-metadata.py  # Byte-preserving registration and validation
    ├── smart-delegate/
    │   ├── SKILL.md               # Provider-agnostic routing rules
    │   ├── scripts/load-config.py # Loads the active config with comments stripped
    │   └── config.yaml            # Bundled defaults and optional execution limits
    ├── verification/
    │   └── SKILL.md               # Independent behavioral verification
    ├── create-operation-skill/
    │   ├── SKILL.md               # Operation skill generator
    │   └── references/setup-workflow.md  # Shared setup workflow
    └── create-verification-skill/
        └── SKILL.md               # Verification skill generator
```

## Contributing

The profiles in `skills/smart-delegate/config.yaml` are the most opinionated part. If you find a task class that's consistently misrouted, open an issue or PR with:

1. The task description
2. Which profile it was routed to
3. Which profile actually handled it well
4. Why (what about the task made it harder/easier than expected)

## License

MIT
