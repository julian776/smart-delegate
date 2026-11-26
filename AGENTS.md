# AGENTS.md

Guidance for agents working in this repository.

This is the only instruction file in the repository. `AGENTS.md` is the cross-host standard —
OpenCode, Codex, and Cursor read it — so it holds the guidance for every agent working here. There
is deliberately no `CLAUDE.md`: one file, one source of truth.

## Project Overview

**Smart Delegate** is a provider-agnostic plugin for multi-agent coordination. It ships execution
skills and setup skills:

- `skills/coordinator/` — owns the outcome. It decomposes work, delegates it, checks what comes
  back, and synthesizes a verified result. It never implements. Autonomous issue mode adds a
  criteria-to-evidence completion gate, corrections, PR/CI lifecycle, persistence, and budgets.
- `skills/smart-delegate/` — selects the model, profile, and invocation mechanism for each
  assignment, and launches it.
- `skills/verification/` — independently exercises a delivered revision and returns PASS, FAIL, or
  NOT VERIFIED per criterion with reproducible evidence.
- `skills/create-operation-skill/` — generates, registers, or adapts a project skill for an
  operation. Its `references/setup-workflow.md` is the shared setup workflow.
- `skills/create-verification-skill/` — same, for exercising an application or service.

The same optional configuration file drives every skill. It is read by
`skills/smart-delegate/scripts/load-config.py`, which resolves the first file found and does not
merge: `./.smart-delegate/config.yaml`, then `~/.config/smart-delegate/config.yaml`, then the
bundled `skills/smart-delegate/config.yaml`.

## Repository layout

```
skills/coordinator/SKILL.md                     orchestration and autonomous issue mode
skills/coordinator/scripts/issue-state.py        persistence, budgets, completion gate
skills/coordinator/scripts/discover-skills.py    frontmatter-only skill catalog
skills/coordinator/scripts/skill-metadata.py     byte-preserving registration and validation
skills/smart-delegate/SKILL.md                   routing skill
skills/smart-delegate/config.yaml                bundled defaults
skills/smart-delegate/scripts/load-config.py     config loader and validator
skills/verification/SKILL.md                     independent verification role
skills/create-operation-skill/                   operation skill generator
skills/create-verification-skill/                verification skill generator
examples/                                        routing and generated project-skill examples
tests/                                           unittest suite and MVP scenario map
.claude-plugin/                                  Claude Code plugin manifest
```

## Commands

```bash
# Print the active configuration with YAML comments removed
python3 skills/smart-delegate/scripts/load-config.py

# Validate the active configuration: YAML syntax, profile titles, execution limits, CLI presence
python3 skills/smart-delegate/scripts/load-config.py --check

# Run the automated suite
python3 -m unittest discover -s tests
```

Run the loader from the project whose routing is being inspected. It prints the source path it
selected, so you can tell which file is in effect. `--check` needs PyYAML; it does not verify
authentication, model access, or execution. The test suite is standard library only.

## Working in this repository

- **The configuration schema is fixed.** Profiles use `title`, `model`, `description`, `priority`,
  `invocation`, and the optional `review`, `qa`, and `execution` stages. Do not invent new keys —
  the loader and every skill read only the documented fields.
- **A configuration file replaces the defaults entirely.** There is no merging. A profile list
  that omits a tier means that tier does not exist, not that it falls back.
- **Keep comments outside block scalars.** `load-config.py` strips only full-line `#` comments.
  Lines inside `|` and `>` blocks are kept verbatim, including lines starting with `#`.
- **Skills must agree.** A change to how work is delegated usually touches the coordinator skill,
  the routing skill, the bundled `config.yaml`, and the `examples/` in the same commit, because the
  same behaviour is described in several places.
- **Keep project knowledge out of orchestration.** Generated project skills teach operation only.
  Acceptance criteria, verdicts, independence, review requirements, and completion conditions
  belong to the coordinator assignment, never to a project skill.
- **Registration changes metadata only.** `skill-metadata.py register` must preserve the skill body
  byte-for-byte. Adaptation needs explicit user authorization and the smallest necessary change.
- **Examples are templates, not live config.** `examples/*.config.yaml` use placeholders or dated
  concrete model IDs. Keep the placeholders in the compact example. `examples/project-skills/` are
  illustrative generated skills, not installed globals.
- **`README.md` is the user-facing document.** It explains routing, the autonomous issue loop, the
  metadata convention, the gate, and the completion rule. Update it when behaviour changes, not
  only the skills.
- **The completion gate is deterministic.** `issue-state.py gate` is the authority for success. Do
  not weaken it to make an example pass; a failing gate is a finding.

## Conventions

- Python is standard library only. `load-config.py` must run without PyYAML installed; PyYAML is
  imported lazily and only for `--check`.
- Prose in Markdown wraps at the sentence. The skills stay under about 100 characters per line;
  `README.md` uses long lines for paragraphs, so match the file you are editing.
- The skills are read by models, so their sentences are instructions, not prose. Keep the
  imperative voice. Project skills use caveman style: exact commands, no filler.

<!-- rtk-instructions v2 -->
# Command output

Command output here is condensed to save tokens, keeping every signal and
dropping costly noise. Treat it as the complete result: run commands
normally, and batch related commands into one call to avoid extra turns.
Truncated results state their recovery path in their own output. Re-run a
command as `rtk bypass <cmd>` only when its result is unusable: empty when
output was clearly expected, contradicting its exit code, or garbled.
<!-- /rtk-instructions -->
