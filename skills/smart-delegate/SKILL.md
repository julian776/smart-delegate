---
name: smart-delegate
description: >
  Quality-first delegation that routes independent work to suitable agents or models without
  assuming a particular provider. Use for multi-file exploration, reviews, research, parallel
  work, or when the user asks to delegate or use agents.
---

# Smart Delegate

Delegate focused work when doing so improves quality, speed, or context isolation. Select the
least expensive available model that can reliably complete each task, and prefer the more capable
option when uncertain.

## Inject routing preferences automatically

Whenever this skill activates, look for a model profile configuration in this order:

1. `.smart-delegate/models.yaml` in the current project
2. `~/.config/smart-delegate/models.yaml`
3. [models.yaml](models.yaml), the bundled defaults

If a file exists, read it automatically and use the first one found; do not merge files. Inject its
relevant preferences and invocation guidance into every delegated assignment. Do not require the
user to mention or paste the configuration. If no file exists, route using the available models and
tools without configuration.

A configuration may contain an ordered `models` list:

```yaml
models:
  - title: Focused worker
    priority: 10
    description: Use for bounded implementation, investigation, and synthesis.
    invocation: |
      Optional instructions for invoking a particular agent, model, CLI, or external tool.
```

- Every field is optional. Ignore empty entries and unknown fields that cannot inform routing.
- `title` is a human-readable label; it does not need to match a provider's model identifier.
- `description` explains when the profile should be selected. Infer suitability from the other
  fields and current environment when it is absent.
- `priority` uses lower numbers when multiple profiles are equally suitable.
  Profiles without a priority retain file order after profiles with an explicit priority.
- `invocation` is free-form guidance. When present, include it in the delegated assignment and
  follow it to invoke that profile.
- Additional fields may provide hints, but must not be required for routing.

Treat descriptions as selection guidance, not keyword rules. If no invocation is provided, choose
an available provider, model, agent type, and invocation mechanism based on the task and current
environment. Never invent an unavailable model or tool. If a configured invocation cannot be used,
select the next suitable profile or use the environment's normal delegation mechanism.

## Decide when to delegate

Delegate when at least one of these applies:

- Two or more independent tasks can run in parallel.
- Exploration requires reading several files or sources and returning a synthesis.
- A focused review benefits from an isolated context.
- The task has clear inputs and outputs and does not need user interaction.

Work inline when delegation overhead exceeds the likely benefit, the result is needed before any
other work can proceed, or the task requires user dialogue.

When several independent tasks exist, launch them together when the environment supports it. Give
each delegate a bounded assignment and ask for conclusions or artifacts rather than raw context.

## Route work

Compare the task against any configured profile information. Consider ambiguity, breadth, required
judgment, risk, and the cost of a weak answer. Choose the lowest-cost profile that is clearly
capable. If uncertain between candidates, choose the more capable one even when its priority is
lower.

Typical routing signals:

- Mechanical lookups and transformations need little judgment.
- Bounded implementation, diagnosis, review, and synthesis need general reasoning.
- Architecture, security, ambiguous tradeoffs, and high-stakes verification need deeper judgment.

Configuration expresses user preferences but does not override availability, safety constraints,
or explicit instructions in the current request.
