# Backtest result fields

`GET /api/backtests/<id>` returns:

| Field | Type | Meaning |
|---|---|---|
| `status` | string | `queued`, `running`, `completed`, `failed` |
| `metrics.sharpe` | number | annualized Sharpe ratio |
| `metrics.total_return` | number | fraction, `0.12` means 12% |
| `metrics.max_drawdown` | number | fraction, negative or zero |
| `trades` | array | executed trades |
| `equity` | array | `{timestamp, value}` points |

Database access for local checks:

    psql "$DATABASE_URL" -c \
      "select id, status, created_at from backtests order by created_at desc limit 5;"

Compare two runs without the UI:

    curl --silent localhost:3000/api/backtests/<id>/metrics | jq -S .
