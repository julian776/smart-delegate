# AGENTS.md

Guidance for agents working in this repository.

`CLAUDE.md` is a symlink to this file. Claude Code reads `CLAUDE.md`, most other agents read
`AGENTS.md`, and OpenCode prefers `AGENTS.md` in a directory over `CLAUDE.md`, so the symlink keeps
both hosts on one source of truth without loading the guidance twice.

## Project Overview

**Smart Delegate** is a provider-agnostic plugin for multi-agent coordination. It ships two skills
that separate orchestration from model selection:

- `skills/coordinator/` — owns the outcome. It decomposes work, delegates it, checks what comes
  back, and synthesizes a verified result. It never executes work itself.
- `skills/smart-delegate/` — selects the model, profile, and invocation mechanism for each
  assignment, and launches it.

The same optional configuration file drives both skills. It is read by
`skills/smart-delegate/scripts/load-config.py`, which resolves the first file found and does not
merge: `./.smart-delegate/config.yaml`, then `~/.config/smart-delegate/config.yaml`, then the
bundled `skills/smart-delegate/config.yaml`.

## Repository layout

```
skills/coordinator/SKILL.md          orchestration skill
skills/smart-delegate/SKILL.md       routing skill
skills/smart-delegate/config.yaml    bundled defaults
skills/smart-delegate/scripts/load-config.py   config loader and validator
examples/                            multi-provider routing examples
.claude-plugin/                      Claude Code plugin manifest
```

## Commands

```bash
# Print the active configuration with YAML comments removed
python3 skills/smart-delegate/scripts/load-config.py

# Validate the active configuration: YAML syntax, profile titles, CLI presence
python3 skills/smart-delegate/scripts/load-config.py --check
```

Run the loader from the project whose routing is being inspected. It prints the source path it
selected, so you can tell which file is in effect. `--check` needs PyYAML; it does not verify
authentication, model access, or execution.

## Working in this repository

- **The configuration schema is fixed.** Profiles use `title`, `model`, `description`, `priority`,
  `invocation`, and the optional `review` and `qa` stages. Do not invent new keys — the loader and
  both skills read only the documented fields.
- **A configuration file replaces the defaults entirely.** There is no merging. A profile list
  that omits a tier means that tier does not exist, not that it falls back.
- **Keep comments outside block scalars.** `load-config.py` strips only full-line `#` comments.
  Lines inside `|` and `>` blocks are kept verbatim, including lines starting with `#`.
- **Both skills must agree.** A change to how work is delegated usually touches
  `skills/coordinator/SKILL.md`, `skills/smart-delegate/SKILL.md`, the bundled `config.yaml`, and
  the `examples/` in the same commit, because the same behaviour is described in four places.
- **Examples are templates, not live config.** `examples/*.config.yaml` use placeholders or dated
  concrete model IDs. Keep the placeholders in the compact example.
- **`README.md` is the user-facing document.** It explains the routing model, the report contract,
  and the completion rule. Update it when the behaviour changes, not only the skills.

## Conventions

- Python is standard library only. `load-config.py` must run without PyYAML installed; PyYAML is
  imported lazily and only for `--check`.
- Prose in Markdown wraps at the sentence. The skills stay under about 100 characters per line;
  `README.md` uses long lines for paragraphs, so match the file you are editing.
- The skills are read by models, so their sentences are instructions, not prose. Keep the
  imperative voice.

<!-- rtk-instructions v2 -->
# Command output

Command output here is condensed to save tokens, keeping every signal and
dropping costly noise. Treat it as the complete result: run commands
normally, and batch related commands into one call to avoid extra turns.
Truncated results state their recovery path in their own output. Re-run a
command as `rtk bypass <cmd>` only when its result is unusable: empty when
output was clearly expected, contradicting its exit code, or garbled.
<!-- /rtk-instructions -->
