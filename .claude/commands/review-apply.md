---
description: Part 2 of the review kit. Reads a review report produced by /review, groups its findings into small test-verified batches, and applies them — editing, running tests, committing on green, stopping on red. Resumable.
argument-hint: [report-path] [--severity 🔴|🟡|🟢] [--skip-tags ui,api] [--only-tags python,theme] [--dry-run]
---

# /review-apply

You are executing **Part 2** of the review kit. Your job is to take a report written by `/review` and apply its findings in **small, test-verified batches**, committing each successful batch to git so the trail is visible and any batch can be reverted independently.

## Configuration — fill these at template-instantiation time

- `{{TEST_COMMAND}}` — **required**. e.g. `pytest -x -q`, `npm test`, `pixi run test`. Testing is the core safety mechanism of Part 2: without it, automated batch application is not safe. If this is still the literal placeholder, **stop immediately** at Step 1 and tell the user to configure it (or pass `--no-tests` to run unsafely at their own risk).
- `{{LINT_COMMAND}}` — optional. e.g. `ruff check .`, `npm run lint`. If still the literal placeholder, skip lint checks silently.

## Step 1: Safety and inputs

1. **Working tree must be clean.** Run `git status --porcelain`. If anything is listed other than the report file itself, stop and ask the user to commit or stash first. Reason: batched auto-edits mixed with in-progress work is a recipe for lost changes.

2. **Resolve the report path** from `$ARGUMENTS`:
   - If a path is given, use it.
   - If none, pick the newest file matching `.claude/review-reports/*.md`.
   - If none exists, tell the user to run `/review <target>` first and stop.

3. **Parse flags** from `$ARGUMENTS`:
   - `--severity <levels>` — comma-separated subset of `🔴,🟡,🟢`. Default: `🔴,🟡`.
   - `--skip-tags <tags>` — comma-separated reviewer tags to exclude. Default: `ui` (Nielsen findings usually need human design judgment).
   - `--only-tags <tags>` — if set, restrict to these tags; overrides `--skip-tags`.
   - `--dry-run` — print the batch plan without editing.
   - `--batch-size <n>` — cap findings per batch. Default: 5.
   - `--no-tests` — **escape hatch only.** Disables the per-batch test gate. Requires explicit acknowledgement: if passed, print a one-line warning that batches will be committed without verification and ask the user to confirm with "yes, apply without tests" before proceeding. Never enable this silently.

4. **Check the test command is configured.** If `{{TEST_COMMAND}}` is still the literal placeholder and `--no-tests` was not passed, stop with:
   > "Testing is the safety gate for /review-apply. Run `/review-init` to configure the test command for this repo, or re-run with `--no-tests` to apply without verification."

5. **Baseline test run.** Before any edits, run `{{TEST_COMMAND}}` once on the clean working tree to confirm the suite passes *as-is*. If it fails, stop — there is no point batching fixes against a red baseline, since we can't tell whether a batch made things worse. Report the failure and ask the user to fix the suite first. (Skip this step if `--no-tests` was confirmed.)

6. **Load apply-state.** Sidecar file `<report-path>.apply-state.json`. Schema:
   ```json
   {
     "baseline_tests": "passed|skipped|failed",
     "findings": {
       "<finding-id>": {"status": "done|skipped|failed|pending", "commit": "<sha>", "note": "..."}
     }
   }
   ```
   A finding-id is the SHA1 (first 8 chars) of its full text. If the file does not exist, treat every finding as `pending`. Record the baseline result here.

## Step 2: Read and parse the report

Read the report file. Extract each finding into a structured record:

```
{
  id: <8-char sha1 of the finding text>,
  severity: 🔴 | 🟡 | 🟢,
  tag: python|frontend|api|ui|theme,
  file: <path>,
  line: <number>,
  title: <short title>,
  problem: <text>,
  suggestion: <text>
}
```

Drop findings whose status in apply-state is already `done` or `skipped`.
Apply the severity / tag filters from Step 1.

## Step 3: Batch the filtered findings

Group into batches with these rules (in order):

1. **Same file, overlapping or adjacent line ranges first.** Findings within ~100 lines of each other in the same file should be in the same batch — they're likely to share context and conflict if applied separately.
2. **Then same reviewer tag.** A batch should ideally be all `[python]` or all `[theme]`, not mixed.
3. **Cap at `--batch-size` findings per batch** (default 5).
4. **Order batches by severity** — all 🔴 batches first, then 🟡, then 🟢.

Produce a **batch plan** and show it to the user:

```
Batch plan (N batches, M findings):
  Batch 1 [🔴 python] src/foo.py — 3 findings (lines 42, 58, 91)
  Batch 2 [🔴 theme]  src/foo.py — 2 findings (lines 310, 340)
  Batch 3 [🟡 python] src/bar.py — 4 findings (lines 12, 15, 20, 44)
  ...
```

If `--dry-run`, stop here.

## Step 4: Apply batches one at a time

For each pending batch, in order:

1. **Announce the batch.** One line: which batch number, tag, severity, file, finding count.

2. **Read the target file region(s).** Only the lines you need. Don't blindly reload the whole file.

3. **Make the edits.** Use `Edit` for localized changes, `Write` only for a full rewrite (rare). Keep the edit minimal — this is a focused fix, not a refactor. Do not add unrelated cleanup.

4. **Run the tests — mandatory.** Run `{{TEST_COMMAND}}` on the edited tree. This gate is not optional: a batch is only considered applicable if the test suite still passes after its edits. On failure, go to step 6 (fail path) — do **not** continue to lint or commit.

   - If `--no-tests` was confirmed in Step 1, skip the test run but include a `[no-tests]` marker in the commit message so the history records that this batch was unverified.
   - Never heuristically decide "this edit looks safe, I'll skip tests." The whole point of Part 2 is that a failing test after a batch tells you *which batch* caused the regression; skipping breaks that property for every later batch too.

5. **Run the linter, if configured.** If `{{LINT_COMMAND}}` is configured, run it. On failure, go to step 6 (fail path).

6. **On success: commit.** Stage only the files you touched (never `git add -A`) and commit with a HEREDOC message:

   ```
   review-apply: <tag> batch <N> — <short summary>

   Applied findings from <report-path>:
   - <finding title 1> (<file>:<line>)
   - <finding title 2> (<file>:<line>)
   ...

   Co-Authored-By: Claude <noreply@anthropic.com>
   ```

   Update apply-state: each finding → `status: "done"`, `commit: <new sha>`. Write the state file.

7. **On failure: stop.** Do not try another batch. Do not auto-revert — the user may want to inspect and fix by hand. Report:
   - Which batch failed.
   - First ~50 lines of the failure output.
   - Path to the report and the state file.
   - Three options for the user:
     - "Fix it manually, then re-run `/review-apply <report>` to continue."
     - "Revert this batch: `git restore <files>` then re-run with `--skip-tags` adjusted."
     - "Mark the batch as `failed` and continue: re-run with `--skip-failed`."

   Update apply-state for each finding in the failed batch → `status: "failed"`, with a short `note`.

## Step 5: Wrap up

After all batches are done (or on a stop), summarize:

- Batches applied / skipped / failed.
- Commits created (SHAs and titles).
- Findings still pending.
- The report path and state file path, so the user can resume.

## Rules

- **Tests gate every batch.** Baseline must be green before any edits; tests must be green after every batch before the commit lands. No exceptions unless the user explicitly opted in with `--no-tests`.
- **One batch, one commit.** Never squash batches. Never amend. If you need to undo, that's `git revert <sha>`.
- **Never bypass hooks or signing.** No `--no-verify`. If a pre-commit hook fails, treat it like a lint failure: stop, report, let the user fix.
- **Don't refactor outside the finding.** If a fix touches three lines, edit three lines. If the surrounding code is ugly, that's a separate review, not this one.
- **Don't mock away a failing test.** If tests go red, the fix is wrong or incomplete — stop, don't paper over it.
- **`--skip-tags ui` by default.** UI/heuristic findings usually need human judgment; the user can opt in explicitly.
- **State file is source of truth for resumability.** Update it after every commit and at every stop.
