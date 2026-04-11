# Smart Delegate

A Claude Code skill that optimizes token costs through **intelligent subagent delegation** — not by compressing output or dumbing down responses, but by routing each task to the right model tier and parallelizing work.

## Philosophy

Most token-saving tools cut corners: shorter responses, smaller models everywhere, fewer tool calls. Smart Delegate takes the opposite approach — **spend tokens wisely, not fewer tokens blindly**.

- A wrong answer from Haiku costs more in rework than using Sonnet would have
- A Sonnet attempt at architecture review wastes time when Opus gets it right the first try
- 10 files read into main context costs more than one focused subagent reading all 10

The savings come from **delegation efficiency**: parallel execution, context isolation, and matching model capability to task complexity.

## How It Works

### Model Routing

Every task Claude encounters gets classified into one of three tiers:

| Tier | Model | When to use |
|------|-------|-------------|
| **T1** | Haiku | Mechanical tasks with a single clear answer — file lookups, greps, format conversion, boilerplate |
| **T2** | Sonnet | Tasks requiring reasoning within clear boundaries — code review, bug diagnosis, test writing, exploration |
| **T3** | Opus | Tasks requiring judgment under ambiguity — architecture design, security review, complex refactoring |

### The Upgrade Rule

> **When in doubt between two tiers, always use the higher one.**

This is the core principle. The cost difference between model tiers is small compared to the cost of re-doing work because a cheaper model gave a wrong or shallow answer.

### Subagent Spawning

The skill instructs Claude to spawn subagents when work is:

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

The skill auto-triggers when Claude is about to:
- Explore multiple files across a codebase
- Run code reviews
- Perform research tasks
- Handle any work that benefits from parallel agents

You can also invoke it explicitly:

```
/smart-delegate:smart-delegate
```

## Routing Examples

### Haiku gets these right every time
- "Find all files matching `*.test.ts`"
- "Search for `DatabaseConnection` in the codebase"
- "Extract all environment variables from this config"
- "Convert this JSON schema to TypeScript types"

### Sonnet is the workhorse
- "How does the authentication middleware work?"
- "Review this PR for code quality issues"
- "Write unit tests for the `UserService` class"
- "Why does the build fail when running on CI?"

### Opus is for when it matters
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
│   └── plugin.json          # Plugin manifest
└── skills/
    └── smart-delegate/
        └── SKILL.md          # Skill definition with routing rules
```

## Contributing

The routing table in `skills/smart-delegate/SKILL.md` is the most opinionated part. If you find a task class that's consistently misrouted, open an issue or PR with:

1. The task description
2. Which tier it was routed to
3. Which tier actually handled it well
4. Why (what about the task made it harder/easier than expected)

## License

MIT
