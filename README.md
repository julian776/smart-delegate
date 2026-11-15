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
| **Fast** | Haiku, Luna | Simple, low-risk tasks with one verifiable answer — exploration, searches, extraction, boilerplate |
| **Focused** | Sonnet, Terra | Well-scoped tasks with clear instructions — implementation, tests, bug diagnosis, routine review |
| **Deep** | Opus, Sol | Ambiguous or difficult work — architecture, refactor planning, security analysis, tradeoffs |
| **Strongest** | Fable | Highest-stakes or hardest problems — costly-to-reverse decisions, final verification |

Quality comes first: when a task sits between two tiers, the stronger one wins. Smart Delegate selects the model *and* launches the worker: a profile with an `invocation` is run through that command (for example `codex exec` or `opencode run`), and a profile without one falls back to the host environment's own delegation tools. Any config file you create (project or user-wide) replaces these defaults entirely.

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

#### Example: multiple providers

[`examples/multi-provider.config.yaml`](examples/multi-provider.config.yaml) is a copy-and-edit
example with explicit reader and writer profiles. It uses OpenCode and Codex CLI invocations,
with native Claude workers as fallback. The host does not need to be Claude for external CLI
routes; native Claude fallback requires a host that can actually launch those workers.

| Role | Fast | Focused | Deep | Deep fallback |
|------|------|---------|------|---------------|
| Reader | OpenCode MiniMax | OpenCode DeepSeek | Codex | Native Claude Sonnet |
| Writer | OpenCode MiniMax | OpenCode DeepSeek | Codex | Native Claude Sonnet |

Readers investigate, diagnose, plan, and review without project edits. Writers implement within
assigned paths and run relevant checks. The example uses OpenCode `plan` versus `build`, and
Codex `read-only` versus `workspace-write`. These controls differ: an agent's plan policy is not
an operating-system sandbox. Checks that generate build artifacts may need a writer in an
isolated worktree. Role names are routing guidance in existing `title` and `description` fields;
there are no new `reader` or `writer` configuration keys.

Choose the role first, then a capable tier. Independent review selects a reader other than the
implementer, preferably from another model family for substantive changes. Both review and QA
are enabled in this example; bundled defaults leave them optional. A routine batch does not need
a strongest-model pass.

The example is never loaded automatically. After installing the skills, copy it from a checkout:

```bash
mkdir -p ~/.config/smart-delegate
cp examples/multi-provider.config.yaml ~/.config/smart-delegate/config.yaml
```

Preserve any existing personal config before copying. Replace `<minimax-provider/model>`,
`<deepseek-provider/model>`, and `<codex-model>` with IDs available to your accounts. Authenticate
the CLIs separately; installing skills does not grant provider access. Console, Go, and direct
OpenCode providers can have different IDs and billing. Inspect `opencode models` and the CLI's
help before using a route. This example has not been validated with live cross-provider calls.

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

The multi-provider example separates **Reader** (investigation and review) from **Writer**
(assigned edits and checks) at each tier. It routes small mechanical tasks to OpenCode MiniMax,
routine work to OpenCode DeepSeek, and complex work to Codex, with native Claude fallback.
Select the role first, then the lowest capable tier; reader and writer descriptions guide routing
and do not enforce filesystem permissions. Independent review selects a separate reader worker.
It requires installed, authenticated CLIs and real model IDs in place of placeholders. Installing
the plugin alone does not configure access to other providers.

### The Upgrade Rule

> **When in doubt between two tiers, always use the higher one.**

This is the core principle. The cost difference between capability profiles is small compared to the cost of re-doing work because a cheaper model gave a wrong or shallow answer.

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
│   └── multi-provider.config.yaml # Reader/writer routing example
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
