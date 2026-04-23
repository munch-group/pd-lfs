---
description: Part 1 of the review kit. Fan-out review of a target file across up to 5 specialist agents (Python, frontend, API consistency, UI heuristics, theming), then aggregate findings into a single prioritized report written to .claude/review-reports/.
argument-hint: <path/to/target/file>
---

# /review

You are the orchestrator of the review kit's **Part 1**. You do NOT read the target file yourself. Your only job is to spawn specialists, collect their reports, and synthesize them into one prioritized document on disk.

## Step 0: Check the kit is instantiated

Run `grep -l '{{TARGET_FILE}}' .claude/agents/code-*-reviewer.md` (allow failure).
If any specialist still contains the literal `{{TARGET_FILE}}` placeholder, the
kit has not been instantiated yet. Stop and tell the user:

> "This repo's review kit is not yet configured. Run `/review-init` first — it
> detects sensible defaults from the repo and asks a small set of setup
> questions."

## Step 1: Resolve the target

The user-supplied argument (`$ARGUMENTS`) is the path to the file under review.

- If no argument was given, use the `{{TARGET_FILE}}` baseline from the agent files (they were all instantiated to the same default by `/review-init`). If that doesn't exist either, stop and ask which file to review.
- Run `ls "$ARGUMENTS"` to verify the file exists. If missing, stop and tell the user.
- Compute a **slug** = filename with `/` and `.` replaced by `-` (e.g. `src/foo/bar.py` → `src-foo-bar-py`).
- Compute a **timestamp** = `YYYYMMDD-HHMMSS` from `date +%Y%m%d-%H%M%S`.
- Report path = `.claude/review-reports/<slug>-<timestamp>.md`. Ensure the directory exists.

## Step 2: Decide which specialists to spawn

Look at the agent files under `.claude/agents/code-*-reviewer.md`. For this repo, some may have been deleted during template instantiation (a pure-Python library won't have `code-frontend-reviewer`, etc.). Spawn **only the specialists that exist on disk**.

The baseline set is:

1. `code-python-reviewer`
2. `code-frontend-reviewer`
3. `code-api-consistency-reviewer`
4. `code-ui-heuristics-reviewer`
5. `code-theming-reviewer`

## Step 3: Spawn all available specialists in parallel

In a **single message**, make one `Agent` tool call per available specialist. Each prompt should be minimal — the specialist's system prompt already contains its scope and output format. A suitable prompt for each is:

> "Review `$ARGUMENTS` per your configured scope. Return the structured report in the exact format your system prompt specifies."

Do not pass extra context. Do not re-read the source.

## Step 4: Aggregate into one report

After all specialists return, synthesize a **single report** with this structure and write it to the report path from Step 1:

```
# Review — <target file>

_Generated <timestamp> by /review. Specialists run: <list>._

## Executive summary
<3–5 bullets: overall health, biggest themes across reviewers>

## 🔴 Critical
<all 🔴 findings from all reviewers, each tagged with [python]/[frontend]/[api]/[ui]/[theme] and anchored at file:line>

## 🟡 Medium
<all 🟡 findings, same format, grouped by reviewer tag>

## 🟢 Nits
<🟢 findings — summarize counts per reviewer and list only the top ~10>

## Cross-cutting themes
<patterns flagged by 2+ reviewers>

## Canonical naming table
<from api reviewer, verbatim. Omit section if api reviewer didn't run.>

## Recommended theme schema
<from theming reviewer, verbatim. Omit section if theming reviewer didn't run.>

## Top 5 UI priority fixes
<from ui reviewer, verbatim. Omit section if ui reviewer didn't run.>

---

_To apply findings in batches, run: `/review-apply <path-to-this-report>`._
```

## Step 5: Report back to the user

Tell the user:
- Where the report was written.
- How many findings total, split by severity.
- That Part 2 is `/review-apply <report-path>`.

## Rules

- Do **not** re-read the source file. The specialists did that work.
- Do **not** add findings of your own. You are a synthesizer, not a reviewer.
- **Do** de-duplicate: if two reviewers flagged the same file:line concern, merge them into one entry and tag it with both reviewer names.
- **Do** preserve concrete file:line references — they are the most useful thing in the report.
- If a specialist reports zero findings in a category, keep the category header with "(none)" so the structure is predictable.
- Cap 🟢 listing at ~10 items total; summarize the rest by count per reviewer.
