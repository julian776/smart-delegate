# Smart Delegate

A provider-agnostic plugin for **intelligent multi-agent coordination**. Its two skills separate orchestration from model selection: Coordinator owns the outcome, while Smart Delegate routes each assignment to the right capability profile.

## Skills

- **Coordinator** decomposes work, delegates independent assignments, observes results, recovers from failures, and synthesizes a verified outcome.
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

Quality comes first: when a task sits between two tiers, the stronger one wins. Smart Delegate only recommends the model; the host environment's own delegation instructions decide how the agent is launched. Any config file you create (project or user-wide) replaces these defaults entirely.

### Configuration

Smart Delegate and Coordinator use the same optional general configuration file. Create `.smart-delegate/config.yaml` in a project, or `~/.config/smart-delegate/config.yaml` for user-wide preferences. Each time a skill is invoked, `skills/smart-delegate/scripts/load-config.py` loads the first available file (project, then user, then bundled defaults; no merging) and injects it into the model's context with comments stripped, so comments cost no tokens. The selected profile's `invocation` is passed verbatim into every delegated assignment. Only full-line `#` comments are removed; text inside `|` and `>` blocks is kept exactly.

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
example for running Claude as the host while delegating some work to **Codex CLI** (`codex exec`,
including `codex exec review`) and **OpenCode** (`opencode run`). It documents how to invoke each
one: assignment on stdin or attached file, model selection, read-only defaults, where results
appear, and what to do on failure. It is not a default and is never loaded automatically; copy it
to `.smart-delegate/config.yaml` or `~/.config/smart-delegate/config.yaml` and replace the
`<model>` placeholders with models you have access to.

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

### The Upgrade Rule

> **When in doubt between two tiers, always use the higher one.**

This is the core principle. The cost difference between capability profiles is small compared to the cost of re-doing work because a cheaper model gave a wrong or shallow answer.

### Subagent Spawning

The skill instructs the host agent to delegate when work is:

- **Parallelizable** — multiple independent tasks get spawned simultaneously
- **Exploratory** — reading 3+ files to answer a question
- **Context-heavy** — results would pollute the main conversation with noise
- **Isolatable** — clear inputs and outputs, no user interaction needed

## Installation

### Step 1: Add the marketplace

From within Claude Code, add this repository as a plugin marketplace:

```
/plugin marketplace add julian776/smart-delegate
```

### Step 2: Install the plugin

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
- Explore multiple files across a codebase
- Run code reviews
- Perform research tasks
- Handle any work that benefits from parallel agents

You can also invoke it explicitly:

```
/smart-delegate:smart-delegate
/smart-delegate:coordinator
```

## Routing Examples

### Fast tier
- "Find all files matching `*.test.ts`"
- "Search for `DatabaseConnection` in the codebase"
- "Extract all environment variables from this config"
- "Convert this JSON schema to TypeScript types"

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
