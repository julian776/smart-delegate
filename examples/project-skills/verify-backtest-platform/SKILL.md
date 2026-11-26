---
name: verify-backtest-platform
description: >
  Launch the backtesting web platform, authenticate as a development user, and inspect strategies,
  runs, and results.
metadata:
  smart-delegate: "true"
  smart-delegate-type: verification
  smart-delegate-capabilities: ui,browser,e2e
---

# Verify backtest platform

## Start

1. From repository root:

       make dev

2. Wait for `Listening on http://localhost:3000`.
3. Readiness:

       curl --fail --silent http://localhost:3000/healthz

4. Server log: `output/dev-server.log`.

## Authenticate

- URL: `http://localhost:3000/login`
- User: `dev@example.test`
- Password source: `.env.local`, key `DEV_PASSWORD`
- Missing user: `make seed-user` (idempotent)
- Do not use production accounts or production data.

## Navigate

| Page | Path | Purpose |
|---|---|---|
| Strategies | `/strategies` | strategy list and parameters |
| Backtests | `/backtests` | run and inspect backtests |
| Results | `/backtests/<id>` | metrics, trades, equity chart |
| Settings | `/settings` | data and fee configuration |

## Exercise

1. Open `/login`; sign in with the development user.
2. Open `/strategies`; confirm `momentum` is listed.
3. Open `/backtests`; select `momentum`, `BTC-USD`, `1h`; range `2026-01-01` to `2026-03-01`.
4. Run; wait for row status `completed`.
5. Open the result; expect metrics cards and a non-empty equity chart.

## Evidence

- Screenshots: `artifacts/verify-platform/<step>.png`
- API result: `curl --silent localhost:3000/api/backtests | jq '.[0] | {status, id}'`
- Browser console errors: capture verbatim.
- Run log: `output/backtest.log`

## Failure

- Login bounces to `/login`: seed the user, confirm `DEV_PASSWORD`, check `output/dev-server.log`.
- Empty table: check `/api/backtests` response and browser console for the failing request.
- Port in use: `make dev PORT=3001`, then use `http://localhost:3001`.
- Chart missing: confirm `output/equity.csv` exists for the run.

## Reference

- Result fields and API access: `references/backtest-results.md`
- Dashboard interactions: `references/dashboard.md`
