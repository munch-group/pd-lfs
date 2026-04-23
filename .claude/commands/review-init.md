---
description: One-time setup for the review kit in a freshly forked template repo. Detects un-instantiated placeholders across the specialist agents and the apply command, asks the user the minimum set of questions, and writes the answers back into the relevant files.
argument-hint: (no arguments)
---

# /review-init

You are bootstrapping the review kit into this repository. The kit ships with
`{{PLACEHOLDER}}` tokens that must be filled before `/review` and `/review-apply`
will work. Your job is to do that, once, with as few questions as possible.

## Step 1: Detect the current state

Run these greps and report the counts:

```
grep -l "{{TARGET_FILE}}"    .claude/agents/code-*-reviewer.md
grep -l "{{LINE_RANGES}}"    .claude/agents/code-*-reviewer.md
grep -l "{{TEST_COMMAND}}"   .claude/commands/review-apply.md
grep -l "{{LINT_COMMAND}}"   .claude/commands/review-apply.md
```

If every placeholder is already replaced, tell the user the kit is already
configured and stop — re-running init would overwrite their choices.

## Step 2: Ask the minimum set of questions

Ask the user — in a single batched question block — for:

1. **Target file or module** (path relative to repo root). The default scope for
   every specialist. The user can override per-run by passing a different
   `$ARGUMENTS` to `/review`, but this sets the baseline.

2. **Which specialists are relevant.** Present the five as a multi-select with
   sensible defaults based on what you observe in the repo:
   - `python` — default ON if any `*.py` exists
   - `frontend` — default ON if the target file contains inline CSS/JS, OR if the repo has `.css`/`.ts`/`.tsx`/`.jsx` files
   - `api-consistency` — default ON if the target has multiple sibling public methods (e.g. several `add_*`, `create_*`, `make_*`)
   - `ui-heuristics` — default OFF unless frontend is ON
   - `theming` — default OFF unless the target has theme/palette-like constants

3. **Test command.** Suggest a default by detecting what's in the repo:
   - `pyproject.toml` with `pytest` → `pytest -x -q`
   - `package.json` with a `test` script → `npm test`
   - `pixi.toml` → `pixi run test`
   - Cargo.toml → `cargo test`
   - otherwise → ask, no default
   This is **required**; if the user has no test suite yet, tell them
   `/review-apply` cannot run safely without one and offer to leave the
   placeholder so they see the error later.

4. **Lint command.** Optional — offer detected defaults:
   - `ruff` config present → `ruff check .`
   - ESLint config present → `npm run lint`
   - otherwise → blank (skip)

Do not ask about line ranges — those are per-file and are better set lazily
when `/review` is first run on a given file. For now, the `{{LINE_RANGES}}`
block in each agent stays as the "describe scope here" instruction, and the
user fills it in the first time they review that file.

## Step 3: Write the answers

For each specialist in the chosen set:
- Replace `{{TARGET_FILE}}` with the target path (all occurrences, every agent file).
- Leave `{{LINE_RANGES}}` as-is if the user had no specifics to say. (The block contains inline instructions for the user to edit later.)

For specialists NOT in the chosen set:
- Delete the agent file.
- Remove the corresponding entry from `commands/review.md`'s fan-out step.

In `commands/review-apply.md`:
- Replace `{{TEST_COMMAND}}` with the answer (or leave as placeholder if the user opted out, per Step 2).
- Replace `{{LINT_COMMAND}}` with the answer (or leave as placeholder for no linter).

Use `Edit` with `replace_all: true` where a placeholder appears multiple times
in a single file.

## Step 4: Commit

Stage only the files you changed and commit:

```
chore: instantiate review-kit for this repo

Configured specialists: <list>
Target: <target>
Test command: <cmd>
Lint command: <cmd or "(none)">

Co-Authored-By: Claude <noreply@anthropic.com>
```

If the repo is not a git repo, skip the commit and tell the user.

## Step 5: Next steps

Tell the user:
- `/review <target>` to generate a review report.
- `/review-apply` to apply its findings in test-gated batches.
- They can re-edit the agent files any time — this was a one-shot bootstrap,
  not a lock-in.

## Rules

- **Ask as little as possible.** Detect defaults from the repo before asking.
- **Don't invent placeholders the kit didn't ship with.** Only the four listed above exist.
- **Never overwrite an already-configured kit.** Step 1 is the guard.
- **Prefer leaving `{{LINE_RANGES}}` untouched** over asking the user to enumerate line ranges they haven't thought about yet. The first `/review` run is a better time for that.
