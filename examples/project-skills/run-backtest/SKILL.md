---
name: run-backtest
description: Run a local strategy backtest and retrieve its metrics, trades, and equity curve.
metadata:
  smart-delegate: "true"
  smart-delegate-type: operation
  smart-delegate-capabilities: backtesting,simulation
---

# Run backtest

## Prerequisites

- Python 3.13; install tools: `make deps`
- Market data: `data/market/` (seed: `make seed-data`)
- Strategy config: `config/strategy.yaml`

## Run

1. Set `name`, `symbol`, `timeframe` in `config/strategy.yaml`.
2. Set `start`, `end` in `config/backtest.yaml` (ISO dates, inclusive).
3. Execute from repository root:

       make backtest

4. Duration: 10-90 s depending on range.

## Results

- Metrics: `output/metrics.json` (`sharpe`, `total_return`, `max_drawdown`)
- Trades: `output/trades.csv`
- Equity curve: `output/equity.csv`
- Run log: `output/backtest.log`

Read metrics with:

    jq '{sharpe, total_return, max_drawdown}' output/metrics.json

## Failure

- `market data not found`: run `make seed-data`, retry.
- `unknown strategy`: `config/strategy.yaml` `name` does not match `src/strategies/`; list valid
  names with `python3 -m backtest.strategies --list`.
- `no trades`: widen the date range or symbol; confirm data covers the range.
- Nonzero exit: read the last `ERROR` line in `output/backtest.log`.

## Reference

- Strategy parameters: `references/strategies.md`
