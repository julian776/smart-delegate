# Dashboard interactions

## Run a backtest

1. `/backtests` → `New backtest`.
2. Strategy select: `momentum`.
3. Symbol select: `BTC-USD`.
4. Timeframe select: `1h`.
5. Date range: start and end, inclusive.
6. `Run`.
7. Row appears with `running`, then `completed`; refresh if the status is stale.
8. Open the row to reach `/backtests/<id>`.

## Read a result

- Metrics cards: Sharpe, total return, max drawdown.
- Trades tab: table sorted by timestamp; empty state text is `No trades`.
- Equity tab: chart; hover shows timestamp and value.

## Common states

| State | Meaning |
|---|---|
| `queued` | worker has not started; wait |
| `running` | in progress; poll up to 2 min |
| `completed` | results available |
| `failed` | open the row; error text names the cause |

## Evidence capture

- Full page: screenshot after the result renders.
- Metrics: screenshot of the cards, or the API JSON.
- Error: screenshot plus the browser console line and `output/dev-server.log` tail.
