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

Every task gets matched to a semantic capability profile. The bundled defaults are:

| Profile | When to use |
|---------|-------------|
| **Mechanical** | Tasks with a single clear answer — file lookups, searches, format conversion, boilerplate |
| **General reasoning** | Tasks requiring reasoning within clear boundaries — code review, bug diagnosis, test writing, exploration |
| **Deep judgment** | Tasks requiring judgment under ambiguity — architecture design, security review, complex refactoring |

The skill does not assume Claude, OpenAI, or any other provider. Unless configuration supplies invocation instructions, the agent chooses an appropriate model and delegation tool available in its current environment.

### Shared Configuration

Smart Delegate and Coordinator use the same optional configuration file. Create `.smart-delegate/models.yaml` in a project, or `~/.config/smart-delegate/models.yaml` for user-wide preferences. The plugin detects the first available file automatically and injects its relevant preferences and invocation guidance into delegated assignments:

```yaml
models:
  - title: Fast local model
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

### Mechanical profile
- "Find all files matching `*.test.ts`"
- "Search for `DatabaseConnection` in the codebase"
- "Extract all environment variables from this config"
- "Convert this JSON schema to TypeScript types"

### General reasoning profile
- "How does the authentication middleware work?"
- "Review this PR for code quality issues"
- "Write unit tests for the `UserService` class"
- "Why does the build fail when running on CI?"

### Deep judgment profile
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
        └── models.yaml       # Bundled default profiles
```

## Contributing

The profiles in `skills/smart-delegate/models.yaml` are the most opinionated part. If you find a task class that's consistently misrouted, open an issue or PR with:

1. The task description
2. Which profile it was routed to
3. Which profile actually handled it well
4. Why (what about the task made it harder/easier than expected)

## License

MIT
