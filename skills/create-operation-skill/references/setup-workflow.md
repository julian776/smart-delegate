# Shared setup workflow

Used by `create-operation-skill` and `create-verification-skill`. Both skills generate, register, or
adapt project skills. The difference is what the generated skill teaches, not how it is delivered.

Path base: the Smart Delegate checkout or installed skill tree. Scripts live in
`../../coordinator/scripts/` relative to this reference file, or `../coordinator/scripts/` relative
to either setup skill directory. Resolve them from the coordinator skill directory when the install
layout differs.

## 1. Understand the request

Establish the operational capability in one sentence:

    Operation: run a local backtest and retrieve its metrics.
    Verification: launch the web platform, authenticate, and inspect a strategy dashboard.

Ask only for what the repository cannot answer: which environment, which credential source, and
whether execution is authorized. Do not require the user to describe commands the repository
already contains.

## 2. Discover before creating

Run discovery against the project:

    python3 <coordinator-skill-dir>/scripts/discover-skills.py --project "$PWD" --json

Read the candidate `SKILL.md` files that could cover the capability. Judge actual instructions, not
directory names or descriptions alone. Check:

- Does it already explain the requested operation end to end?
- Are its commands, paths, and parameters current?
- Does it retrieve results, or stop at launching?
- Is anything genuinely missing for the operation itself?

Do not treat missing Smart Delegate policy as a gap. Acceptance criteria, independence rules,
verdicts, review requirements, and completion conditions do not belong in a project skill.

## 3. Present the choice

Report concisely: skill name, location, existing capability, genuine gaps, and your recommendation.
Then ask which the user wants:

1. Register the existing skill with metadata only.
2. Adapt the existing skill.
3. Create a separate skill.
4. Leave everything unchanged.

Multiple overlapping skills: list each capability briefly, recommend the simplest fit, and do not
consolidate or delete anything without explicit authorization.

No changes before authorization. User cancellation ends the task with no file writes. This
interaction belongs to setup, never to autonomous issue execution.

## 4. Act on the choice

### Register only

    python3 <coordinator-skill-dir>/scripts/skill-metadata.py register \
        <skill>/SKILL.md --type operation --capabilities keyword,keyword

This adds three frontmatter keys. Preserve the body, description, other metadata, references, and
formatting exactly. Registration is discovery, not certification: do not run a validation ceremony
and do not rewrite the skill.

### Adapt

Make the smallest change that supplies the missing operational information. Preserve existing
commands, structure, metadata, and references. Add the three registration keys. Validate the
changed operational behavior when practical. Never rewrite for style, never add orchestration
policy.

### Create independently

Keep the original untouched. Create a new skill directory with the requested capability, reference
the existing instructions where useful, and avoid duplicating long documentation. Include the
registration keys. Choose a name that distinguishes its scope.

### Leave unchanged

Report that nothing changed. Do not stage, format, or register anything.

## 5. Generate the skill

Inspect the repository for real behavior before writing:

- build and task runners: `Makefile`, `justfile`, `package.json`, `pyproject.toml`, `go.mod`,
  `Cargo.toml`, `docker-compose.yml`;
- entry points and configuration: `README`, `.env.example`, config directories;
- CI definitions for the commands the project actually runs;
- existing scripts and their `--help` output.

Execute the operation in an authorized environment when practical. Record the working directory,
exact command, required parameters, prerequisites, output paths, result retrieval, and the shortest
useful failure diagnostic.

Write in caveman style:

- imperative, one idea per sentence;
- exact commands, paths, parameters, ports, and output locations;
- prerequisites and authorization constraints;
- progressive disclosure: keep `SKILL.md` short, put feature depth in `references/`;
- no filler, tutorials, invented commands, or repeated repository documentation;
- do not strip necessary technical detail to save tokens.

Frontmatter:

    ---
    name: <kebab-case>
    description: <one sentence: what operation, when to use it>
    metadata:
      smart-delegate: "true"
      smart-delegate-type: operation        # or verification, or both
      smart-delegate-capabilities: keyword,keyword
    ---

Registration keys may be added by the script instead of hand-written. New skills include them.

Project skills belong to the target repository, conventionally `.agents/skills/<name>/SKILL.md`
or the host's supported project skill directory. Do not store them in the Smart Delegate repository.

## 6. Validate independently

Delegate validation to an agent that did not write the instructions. That agent follows the skill
with normal repository context and checks:

- commands exist and run;
- prerequisites are documented;
- parameters are accurate;
- output and log locations are correct;
- the operation completes and its result can be retrieved;
- common failures produce an understandable error.

Fix genuine inaccuracies, then re-check the changed instruction. If execution is unavailable,
report exactly which instructions remain unverified. Reading the text is not validation. Do not add
issue-level policy as a result of validation.

## 7. Report

Return: action taken, skill path, registration metadata, files changed, validation performed,
unverified portions, and any authorization still needed. Keep it concise.

## Content boundary

Include: tools, prerequisites, commands, parameters, configuration, paths, navigation, output and
log locations, result retrieval, project-specific troubleshooting, safety constraints.

Exclude: issue acceptance criteria, deciding checks for a specific issue, agent independence
policy, delegation or routing rules, review requirements, verdict formats, evidence-reporting
protocols, correction loops, coordinator completion conditions. Those belong to the coordinator's
assignment.
