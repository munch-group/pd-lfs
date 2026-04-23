# Using review-kit

This guide is for people working in a repo where review-kit is already installed
(you see a `.claude/commands/review*.md` tree). If you're setting up a fresh
repo, run `/review-init` first — it configures the kit against your project
and is described briefly at the end of this document.

---

## The mental model

The kit is two workflows wired together:

1. **Review** (`/review <target>`) — several specialist reviewers read the file
   in parallel, each from a narrow angle (Python quality, frontend, public-API
   consistency, UI usability, theming). A coordinator merges their outputs into
   one prioritized report saved under `.claude/review-reports/`.
2. **Apply** (`/review-apply`) — that report is parsed, grouped into small
   batches, and the edits are made one batch at a time. After every batch the
   test suite runs; a batch is only committed if tests stay green.

The split exists so you get:
- a reviewing phase that's cheap to re-run and safe to read (nothing is edited),
- an applying phase that's safe to leave running (every commit is test-verified).

Every commit Part 2 creates references the findings it resolved, so `git log`
is a readable audit trail and `git revert <sha>` cleanly undoes any one batch.

---

## A complete walkthrough

Suppose you want to improve `src/mylib/parser.py`.

### 1. Start from a clean tree

```bash
git status          # should be clean; commit or stash in-progress work
```

Part 2 refuses to run on a dirty tree because mixing auto-edits with
in-progress work is a recipe for losing both.

### 2. Generate a review

```
/review src/mylib/parser.py
```

What happens:
- The coordinator verifies the file exists.
- It fans out every specialist the kit is configured for (in parallel — one
  Claude Code `Agent` call each).
- Each specialist reads only its relevant slice of the file and returns a
  structured report with 🔴 / 🟡 / 🟢 findings anchored at `file:line`.
- The coordinator de-duplicates overlaps, surfaces cross-cutting themes, and
  writes a single markdown report to:

  ```
  .claude/review-reports/src-mylib-parser-py-20260423-151200.md
  ```

- You get back a one-paragraph summary: path to the report, counts by
  severity, and a reminder that `/review-apply` is the next step.

**You can stop here.** The report is a useful artifact on its own — share it,
skim it, cherry-pick fixes by hand. `/review-apply` is only needed if you want
to apply findings in bulk.

### 3. Read the report

Open the newest file under `.claude/review-reports/`. Structure:

```
# Review — src/mylib/parser.py

## Executive summary
...

## 🔴 Critical
[python] Silent exception swallows parse errors — src/mylib/parser.py:118
Problem: ...
Suggestion: ...

## 🟡 Medium
...

## 🟢 Nits
...

## Cross-cutting themes
...
```

Each finding has a tag in square brackets — `[python]`, `[frontend]`, `[api]`,
`[ui]`, `[theme]` — identifying which specialist flagged it. You'll use those
tags to filter Part 2.

### 4. Apply the report

```
/review-apply
```

With no arguments, this picks up the newest report in `.claude/review-reports/`.
What happens:

1. **Safety checks.** Clean git tree? Test command configured? Then it runs
   the full test suite once on the clean tree to confirm a green baseline.
   If the baseline is red, it stops — there's no point applying fixes on top
   of a broken suite.
2. **Batch plan.** The findings are grouped into batches of ≤ 5, preferring
   to bundle findings that touch the same file and nearby lines. It prints
   the plan and starts applying.
3. **For each batch:**
   - Makes the edits.
   - Runs the configured test command.
   - On green: runs the linter (if configured), then commits the batch.
   - On red: stops immediately and tells you what failed.
4. **A sidecar state file** (`<report>.apply-state.json`) records which
   findings are done, skipped, or failed. If a batch fails and you fix it
   by hand, re-running `/review-apply` picks up where it left off.

### 5. Review the commits

```bash
git log --oneline -20
```

You'll see one commit per batch, each titled something like:

```
review-apply: python batch 3 — extract parse_header helpers
```

Each commit body lists the specific findings it resolved (title + file:line).
If a batch caused a regression that tests didn't catch, `git revert <sha>`
reverses just that batch.

---

## Filtering what gets applied

Defaults for `/review-apply`:
- severity: `🔴,🟡` — skip nits
- skip-tags: `ui` — Nielsen UX findings usually want human judgment

Override with flags:

| Flag | Meaning | Example |
| ---- | ------- | ------- |
| `--severity` | Comma-separated severities to include | `--severity 🔴` (only critical) |
| `--skip-tags` | Reviewer tags to exclude | `--skip-tags ui,api` |
| `--only-tags` | Restrict to these tags (overrides `--skip-tags`) | `--only-tags python` |
| `--batch-size` | Max findings per batch (default 5) | `--batch-size 3` |
| `--dry-run` | Show the batch plan, make no edits | `--dry-run` |
| `--no-tests` | **Escape hatch** — skip test gate. Requires interactive confirmation | `--no-tests` |

You can also pass an explicit report path as the first positional argument:

```
/review-apply .claude/review-reports/src-mylib-parser-py-20260423-151200.md
```

Useful when you have multiple reports and want to apply an older one.

---

## Common workflows

**"I want to triage critical issues only, then iterate."**

```
/review src/mylib/parser.py
/review-apply --severity 🔴
# inspect the commits
/review-apply --severity 🟡 --only-tags python,api
```

Each invocation picks up the same report — findings committed in the first
run are marked `done` in the state file and skipped on the second run.

**"I just want the report, I'll apply fixes by hand."**

```
/review src/mylib/parser.py
# open the .md under .claude/review-reports/ and work from there
```

No `/review-apply` required.

**"A batch failed. What now?"**

Part 2 stops on the first red batch and prints:
- what failed (first ~50 lines of test output),
- which findings were in the failed batch,
- three options it offers you:
  1. Fix by hand, then re-run `/review-apply <report>` to continue.
  2. Revert (`git restore <files>`) and re-run with an adjusted `--skip-tags`.
  3. Mark the failed batch as `failed` in the state file and skip past it.

The state file survives across runs, so you can stop and resume days later.

**"I want to re-review the same file after applying fixes."**

Just run `/review <target>` again. It writes a new timestamped report —
previous reports and state files are kept.

---

## What each specialist looks at

| Tag         | Specialist file                          | Focus                                                                                  |
| ----------- | ---------------------------------------- | -------------------------------------------------------------------------------------- |
| `[python]`  | `code-python-reviewer.md`                | Long-function smells, repeated patterns across siblings, type hints, docstrings, numpy/pandas use, error handling. |
| `[frontend]`| `code-frontend-reviewer.md`              | Inline CSS, HTML templates, ES6/WebGL JS, event handlers, memory cleanup, accessibility. |
| `[api]`     | `code-api-consistency-reviewer.md`       | Public surface only (signatures + docstrings). Argument naming, defaults, symmetry, return values. |
| `[ui]`      | `code-ui-heuristics-reviewer.md`         | Nielsen's 10 heuristics applied to user-visible behavior (controls, shortcuts, tooltips). |
| `[theme]`   | `code-theming-reviewer.md`               | Theme dicts, dark/light parity, hardcoded-color leaks, user extensibility.             |

`/review-init` deletes specialists that aren't relevant to your repo — a
pure-Python library typically keeps only `python` and `api`.

If you want to customize a specialist (different rubric, extra checks, narrower
scope), the files are plain markdown — edit them directly and the next
`/review` picks up your changes.

---

## Troubleshooting

**"The kit says it's not yet configured."**
Run `/review-init`. It fills placeholders once and commits the setup.

**"`/review-apply` refuses to run because the tree is dirty."**
Commit or stash. The kit will not mix its edits with yours — that trade-off
is deliberate.

**"Baseline tests fail before any edits."**
Not a kit problem — your suite was already red. Fix it first, then re-run.

**"The batch plan looks wrong — too many findings clumped together."**
Lower `--batch-size`, or use `--only-tags` to narrow the set so fewer findings
survive to be batched.

**"A specialist's scope (line ranges) is out of date after I refactored."**
The `{{LINE_RANGES}}` block in each agent file is plain markdown. Edit the
range list directly; the next `/review` will use the new scope.

**"I want to stop mid-apply."**
Interrupt Claude Code as usual. The state file is written after every
committed batch, so resuming picks up from the last green commit — the
in-progress batch is not marked `done`, so it re-runs next time.

**"I committed an unverified batch with `--no-tests` and now tests are red."**
`git log` shows which batch it was (commit message will include `[no-tests]`);
`git revert <sha>` removes just that batch. In general, prefer not to use
`--no-tests` — it costs you the bisection property for every later batch
until the next green batch lands.

---

## The setup command (`/review-init`)

If you're in a freshly forked template and the `{{...}}` placeholders haven't
been filled yet, run:

```
/review-init
```

It will:

1. Detect what's in the repo (test runner, presence of JS/CSS, linter config)
   and pick sensible defaults.
2. Ask a short question set: target file/module, which specialists are
   relevant, test command, optional lint command.
3. Fill placeholders in each specialist, delete specialists you don't need,
   and commit the setup as a single commit.

You can re-edit the files any time after — it's a one-shot bootstrap, not a
lock-in. `/review-init` refuses to run a second time against an already-configured
kit, so you can't accidentally overwrite your choices.
