---
name: create-operation-skill
description: >
  Teach agents a project-specific operation by generating, registering, or adapting a project skill:
  run backtests or benchmarks, replay events, run migrations, seed test data, profile a service, or
  prepare a development environment. Use when the user asks to capture how to perform an operation
  in this repository, or to make an existing operation skill discoverable.
---

# Create operation skill

Turn one operational capability into a reusable project skill. The skill must work for a human, a
standalone coding agent, and Smart Delegate without modification.

Follow [the shared setup workflow](references/setup-workflow.md) for discovery, the user choice,
registration, adaptation, generation, and independent validation. This file adds the
operation-specific checklist.

Scripts are in the coordinator skill's `scripts/` directory, next to this skill's sibling:

    python3 ../coordinator/scripts/discover-skills.py --project "$PWD"
    python3 ../coordinator/scripts/skill-metadata.py register <skill>/SKILL.md ...

If the installed layout differs, resolve both scripts from the coordinator skill directory.

## Invocation

    $create-operation-skill how to run the local strategy backtest
    /create-operation-skill capture how to replay Kafka events into the dev cluster

## Ask for the capability

One sentence is enough when the repository holds the rest:

    Which operation, in which environment, and is executing it here authorized?

Do not ask the user to supply commands the repository already contains. Inspect, run, and record
them. Ask for credentials only when the operation requires them, and never write a secret into the
skill.

## Operation checklist

Discover and verify, do not assume:

- entry command and working directory;
- required tools, versions, services, and environment variables;
- required parameters and their valid ranges or enum values;
- input files or data sets, and how to obtain or generate them;
- configuration file and the fields that matter;
- output location for each result: metrics, rows, artifacts, logs;
- how to retrieve and interpret the result well enough to know the operation ran;
- expected duration and any cost or external side effect;
- exact failure output for the two or three common failures, and the log or command that diagnoses
  each;
- safety constraints: read-only vs mutating, data that must not be used, services that must not be
  touched.

Run the operation once in an authorized environment. If it cannot run, say which parts are
unverified rather than presenting guessed commands.

## Template

```markdown
---
name: run-backtest
description: Run local strategy backtest and retrieve metrics.
metadata:
  smart-delegate: "true"
  smart-delegate-type: operation
  smart-delegate-capabilities: backtesting,simulation
---

# Run backtest

## Prerequisites

- Python 3.13, `make deps`
- Market data at `data/market/` (generate: `make seed-data`)

## Run

1. Set strategy: `config/strategy.yaml` (`name`, `symbol`, `timeframe`).
2. Set dates: `config/backtest.yaml` (`start`, `end`).
3. Execute from repository root:

       make backtest STRATEGY=momentum

## Results

- Metrics: `output/metrics.json`
- Trades: `output/trades.csv`
- Equity curve: `output/equity.csv`

Read `output/metrics.json`; `sharpe` and `total_return` are the headline values.

## Failure

- `data not found`: run `make seed-data`, then retry.
- `strategy invalid`: inspect `config/strategy.yaml`; the error names the bad field.
- Logs: `output/backtest.log`
```

Replace every placeholder with discovered values. Delete sections that do not apply. Do not add a
section describing how an agent should judge issue success or report evidence.

## Progressive disclosure

Keep `SKILL.md` to prerequisites, the run sequence, result retrieval, and troubleshooting. Move
strategy-specific parameters, dashboard behavior, or data-set details into `references/` and link
them. Do not create reference files for a simple operation.

## Done

Report: skill path, whether it was created, adapted, or registered, the exact operation it teaches,
validation evidence, and any unverified instruction. No file changed without authorization.
