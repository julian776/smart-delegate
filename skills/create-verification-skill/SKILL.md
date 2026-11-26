---
name: create-verification-skill
description: >
  Teach agents how to launch, access, and exercise a project so they can verify behavior: web
  applications, backend services, CLIs, data pipelines, and desktop apps where supported. Use when
  the user asks to capture how to interact with an application, or to make an existing verification
  skill discoverable.
---

# Create verification skill

Produce a project skill that explains how to operate the application. It teaches access and
observation, not how to decide an issue is complete.

Follow [the shared setup workflow](../create-operation-skill/references/setup-workflow.md) for
discovery, the user choice, registration, adaptation, generation, and independent validation. This
file adds the verification-specific checklist and template.

Scripts are in the coordinator skill's `scripts/` directory:

    python3 ../coordinator/scripts/discover-skills.py --project "$PWD"
    python3 ../coordinator/scripts/skill-metadata.py register <skill>/SKILL.md \
        --type verification --capabilities ui,browser,e2e

## Invocation

    $create-verification-skill how to verify the strategy dashboard in the dev environment
    /create-verification-skill capture how to exercise the payments API locally

## Ask for the surface

    Which surface must an agent exercise, how is it started, and which environment is authorized?

Inspect the repository for the answer first. Typical surfaces:

- **Web**: dev server command, port, login or seeded user, key routes, browser tooling.
- **Backend service**: process or container command, base URL, auth header or token source, health
  endpoint, representative requests.
- **CLI**: entry point, arguments, fixture input, expected output and exit codes.
- **Data pipeline**: input location, run command, output location, how to inspect a record.
- **Desktop**: launch command, display or automation constraints, supported evidence.

If authentication or seed data is required, document the development source. Never embed a real
secret. Do not use production or customer data without explicit authorization.

## Verification checklist

- launch command, working directory, port, and readiness check;
- prerequisites: database, queue, migrations, seed data, environment file;
- how to reach the feature: URL, route, menu path, CLI invocation;
- how to authenticate in development, including the test user or token source;
- the smallest interaction that exercises the surface, and the observable result;
- how to capture evidence: screenshot location, console output, network response, log path;
- how to inspect server or browser logs when the interaction fails;
- reset or teardown so repeated runs start clean;
- known environment limitations such as headless-only or no browser.

If the host provides browser tooling, use it and name the actions, not a vendor-specific API:
open URL, click, type, read text, screenshot. If no browser tool exists, document a runnable
alternative already in the repository (for example a Playwright script), including its path and
command. Do not invent a tool.

## Template

```markdown
---
name: verify-platform
description: Launch the backtesting web platform and exercise the dashboard.
metadata:
  smart-delegate: "true"
  smart-delegate-type: verification
  smart-delegate-capabilities: ui,browser,e2e
---

# Verify platform

## Start

1. `make dev` from repository root.
2. Wait for `Listening on http://localhost:3000`.
3. Health: `curl --fail http://localhost:3000/healthz`

## Authenticate

- URL: `http://localhost:3000/login`
- User: `dev@example.test`
- Password source: `.env.local` `DEV_PASSWORD`; if absent, `make seed-user`
- Do not use production accounts.

## Exercise

1. Open `/login`, sign in with the development user.
2. Open `/strategies`, select `momentum`.
3. Open `Backtests`, choose date range, run.
4. Expect a row with status `completed` and a link to metrics.

## Evidence

- Screenshot: `artifacts/verify-platform/<step>.png`
- Browser console: capture errors verbatim.
- Server log: `output/dev-server.log`
- API check: `curl -s localhost:3000/api/backtests | jq '.[0].status'`

## Failure

- Login redirects: confirm `make seed-user` ran; inspect `output/dev-server.log`.
- Blank dashboard: check browser console for the failed request.
- Port busy: `make dev PORT=3001`, then use that base URL.
```

Use discovered values, routes, and commands. Delete inapplicable sections. Keep feature-specific
detail in `references/` when `SKILL.md` grows.

## Do not add policy

The generated skill explains operation. It must not contain issue acceptance criteria, deciding
checks, verdicts, independence requirements, delegation rules, review requirements, evidence
reporting protocols, correction loops, or coordinator completion conditions. A verifier receives
those in its assignment. A skill that also contains them stops being reusable by humans and other
agents.

## Validate independently

Give the generated skill to an agent that did not write it. That agent launches the application,
authenticates, performs one real interaction, retrieves the stated evidence, and checks the failure
instructions for the most likely error. Fix inaccurate commands or paths, then re-check. If the
environment cannot run the application, report which parts remain unverified. A text review is not
validation.

## Done

Report: action taken, skill path, surface covered, validation evidence, known environment
limitations, and unverified portions. No file changed without authorization.
