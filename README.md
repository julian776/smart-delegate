# Smart Delegate

A provider-agnostic plugin for **intelligent multi-agent coordination**. Its two skills separate orchestration from model selection: Coordinator owns the outcome, while Smart Delegate routes each assignment to the right capability profile.

## Skills

- **Coordinator** is accountable for the quality and output of the task. It never executes work itself: it decomposes, delegates, checks what every agent reports back, recovers from failures, and synthesizes a verified outcome, keeping its own context clean. When it needs information, it asks an agent sized to the difficulty.
- **Smart Delegate** selects a suitable configured profile, model, and invocation mechanism for each assignment.

Use Coordinator for multi-step or multi-agent work. It automatically applies Smart Delegate when choosing how each assignment should run.

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

review:
  enabled: true
  description: |
    Review completed changes for regressions.
    Include maintainability findings with evidence.

qa:
  enabled: true
  description: |
    Exercise changed behavior.
    Verify the request's acceptance criteria.
  invocation: |
    Run `my-qa-tool --changed`.
    Summarize failures and preserve command output.
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

For a new computer without a checkout, this Bash recipe installs both skills globally and
downloads the expanded configuration. Change `routing_example` to `multi-provider.config.yaml`
for the compact version. It backs up any existing config and downloads before replacing it:

```bash
npx skills add https://github.com/julian776/smart-delegate -g --skill smart-delegate
npx skills add https://github.com/julian776/smart-delegate -g --skill coordinator

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

The contract ships in every bundled and example configuration, and both skills append it to each
assignment. Configurations that define their own `invocation` should keep the contract block in
those invocations; profiles without an `invocation` get it from the skills themselves.

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

`-g` installs globally, so the `smart-delegate` and `coordinator` skills are available in every
project and every supported agent. Update later with `npx skills update`.

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
│   └── multi-provider-expanded.config.yaml # Expanded pool with concrete model IDs
├── .claude-plugin/
│   └── plugin.json          # Claude Code plugin manifest
└── skills/
    ├── coordinator/
    │   └── SKILL.md          # Orchestration and observation loop
    └── smart-delegate/
        ├── SKILL.md          # Provider-agnostic routing rules
        ├── scripts/load-config.py  # Loads the active config with comments stripped
        └── config.yaml       # Bundled default tiers
```

## Contributing

The profiles in `skills/smart-delegate/config.yaml` are the most opinionated part. If you find a task class that's consistently misrouted, open an issue or PR with:

1. The task description
2. Which profile it was routed to
3. Which profile actually handled it well
4. Why (what about the task made it harder/easier than expected)

## License

MIT
