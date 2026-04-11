---
name: smart-delegate
description: >
  Quality-first subagent delegation. Routes tasks to the cheapest model that reliably handles them,
  spawns subagents for parallelizable work, and biases upward when uncertain.
  Auto-triggers when Claude is about to do multi-file exploration, run reviews, perform research,
  or handle tasks that would benefit from parallel agents. Also triggers on "delegate", "use agents",
  "smart delegate", "/smart-delegate".
---

# Smart Delegate — Quality-First Subagent Routing

Spawn subagents aggressively. Pick the cheapest model that **reliably** handles the task. When uncertain, always go one tier up.

## Model Tiers

| Tier | Model | Cost | Use when |
|------|-------|------|----------|
| **T1** | `haiku` | Lowest | Task has a single, clear answer. No judgment calls. |
| **T2** | `sonnet` | Mid | Task requires reasoning, synthesis, or multi-step logic. |
| **T3** | `opus` | Highest | Task requires deep architectural reasoning, ambiguous tradeoffs, or creative problem-solving. |

## The Upgrade Rule

> **In doubt between T1 and T2 → use T2. In doubt between T2 and T3 → use T3.**
>
> A wrong answer at a cheaper tier costs more than the right answer at the next tier up.
> Re-work from a bad subagent wastes far more tokens than the delta between models.

## Task → Model Routing Table

### Haiku (T1) — Mechanical, well-scoped tasks

- **File lookup / glob**: "Find files matching X pattern"
- **Simple grep**: "Search for symbol X in the codebase"
- **Format conversion**: "Convert this JSON to YAML"
- **Boilerplate generation**: Repetitive code from a clear template
- **Syntax checks**: "Does this file parse correctly?"
- **Extracting data**: "Pull all import statements from these files"
- **Simple Q&A**: "What's the default port for X?"

### Sonnet (T2) — Reasoning with clear boundaries

- **Code exploration**: "How does module X work?" (Explore agent)
- **Code review**: Lint, naming, error handling, style checks
- **Test writing**: Unit tests for well-defined functions
- **Bug diagnosis**: "Why does X fail when Y?"
- **Refactoring**: Rename, extract method, reorganize — when scope is clear
- **Documentation**: Summarize what code does
- **Research**: Web search + synthesis of results
- **Implementation**: Feature work with a clear spec/plan

### Opus (T3) — Judgment, ambiguity, architecture

- **Architecture design**: System design, tradeoff analysis
- **Plan review**: Evaluating whether a plan is complete and sound
- **Ambiguous bugs**: Unclear repro, multiple possible causes
- **Security review**: Threat modeling, subtle vulnerability detection
- **Complex refactoring**: Cross-cutting changes affecting multiple systems
- **Creative problem-solving**: "What's the best approach to X?" with no clear answer
- **Final verification**: When the stakes are high and correctness matters most

## When to Spawn Subagents

Spawn a subagent instead of doing the work inline when **any** of these apply:

1. **Parallelizable**: Two or more independent tasks exist → spawn all in parallel
2. **Exploratory**: You need to read 3+ files to answer a question → Explore agent
3. **Reviewable**: Code needs review from a specific angle → dedicated review agent
4. **Context-preserving**: The work would pollute main context with noise (large search results, verbose outputs)
5. **Isolatable**: The task has clear inputs and outputs, doesn't need main conversation state

**Do NOT spawn a subagent when:**
- The task takes <30 seconds inline
- You need the result immediately and there's nothing else to do in parallel
- The task requires back-and-forth with the user
- You already have the answer from context

## Parallel Spawning Rules

When multiple independent subagents are needed, **always spawn them in a single message** (one message, multiple Agent tool calls). Never spawn sequentially when parallel is possible.

Example — exploring a codebase:
```
Agent(model: "haiku", "Find all API route files")
Agent(model: "haiku", "Find all database migration files")  
Agent(model: "sonnet", "How does the auth middleware work?")
```
All three in one message. Haiku for the lookups, Sonnet for the reasoning.

## Decision Flowchart

```
Is the task mechanical with a single clear answer?
├── Yes → Haiku
├── Unsure → Sonnet (upgrade rule)
└── No →
    Does it require reasoning within clear boundaries?
    ├── Yes → Sonnet
    ├── Unsure → Opus (upgrade rule)
    └── No → Opus
```

## Anti-Patterns

- **Haiku for exploration**: Haiku can grep, but it can't synthesize across files well. Use Sonnet for Explore agents.
- **Opus for everything**: Wastes budget on tasks Sonnet handles perfectly. Save Opus for where judgment matters.
- **Sequential when parallel**: If tasks are independent, spawn them together. The wall-clock time savings alone justify it.
- **Skipping subagents to "save tokens"**: A focused subagent that reads 10 files costs less than polluting main context with 10 file reads.
- **Downgrading under pressure**: When the user says "this is important", that's a signal to go UP a tier, not down.
