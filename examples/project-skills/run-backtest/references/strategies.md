# Strategy parameters

`config/strategy.yaml` fields:

| Field | Values | Default |
|---|---|---|
| `name` | `momentum`, `mean-reversion`, `breakout` | `momentum` |
| `symbol` | any symbol in `data/market/` (`BTC-USD`, `ETH-USD`) | `BTC-USD` |
| `timeframe` | `1m`, `5m`, `1h`, `1d` | `1h` |
| `lookback` | integer bars, 10-500 | `50` |
| `fee_bps` | integer basis points | `10` |

List available strategies and their parameters:

    python3 -m backtest.strategies --list --format json

Validate a config without running:

    python3 -m backtest.validate config/strategy.yaml
