# review-kit

A standalone Claude Code workflow for reviewing a nontrivial file or module
and then executing the review's suggestions in small, test-verified batches.

Designed to ship with template repos: fork the template, run `/review-init`
once, and the workflow is live. Nothing machine-specific or author-specific
needs to be edited by hand.

## Which doc do you want?

- **[USAGE.md](USAGE.md)** — day-to-day use. Walkthrough, flag reference,
  common workflows, troubleshooting. Read this if the kit is already installed
  in a repo you're working in.
- **[TEMPLATE_AUTHORS.md](TEMPLATE_AUTHORS.md)** — how to package the kit
  into your own template repo and customize it for your house style. Read
  this if you maintain a library template.

## The three commands at a glance

| Command             | When to run                | What it does |
| ------------------- | -------------------------- | ------------ |
| `/review-init`      | Once, after forking        | Detects defaults from the repo, asks a few setup questions, fills placeholders. |
| `/review <target>`  | Whenever you want a review | Fans out specialist reviewers in parallel; writes one synthesised report to `.claude/review-reports/`. |
| `/review-apply`     | After a `/review`          | Applies the report's findings in small, test-gated batches, one commit per batch. |

## How the two parts fit together

**Part 1 — `/review`** fans out 5 specialist subagents (Python, frontend, API
consistency, UI heuristics, theming), each reviewing one concern of the
target. A coordinator merges their outputs into one prioritized report with
🔴 / 🟡 / 🟢 severity. No files are edited; the report is the artifact.

**Part 2 — `/review-apply`** reads that report, groups findings into small
batches, and for each batch: makes the edits, runs the test suite, commits on
green, stops on red. Designed to be resumable — a sidecar state file lets you
pick up where you left off.

**Tests are mandatory in Part 2.** Before any edits, it runs the test suite on
the clean tree to confirm a green baseline; after every batch it runs the
suite again and refuses to commit red. There's a `--no-tests` escape hatch
that requires interactive confirmation, but using it throws away the
"which batch caused the regression?" bisection property for every later batch.

## Kit layout

```
review-kit/
├── README.md               (this file)
├── USAGE.md                (user guide — read when using the kit)
├── TEMPLATE_AUTHORS.md     (for template maintainers packaging the kit)
└── .claude/
    ├── agents/
    │   ├── code-python-reviewer.md
    │   ├── code-frontend-reviewer.md
    │   ├── code-api-consistency-reviewer.md
    │   ├── code-ui-heuristics-reviewer.md
    │   └── code-theming-reviewer.md
    └── commands/
        ├── review-init.md  (setup — run once after fork)
        ├── review.md       (Part 1 — fan-out review)
        └── review-apply.md (Part 2 — batched apply + verify)
```

## Severity rubric (used by all specialists)

- 🔴 **High** — Correctness bugs, data corruption, memory issues, API contract violations, accessibility lockouts.
- 🟡 **Medium** — Long-function smells, missing docstrings on public API, inefficient patterns, naming inconsistencies, friction bugs.
- 🟢 **Low** — Style nits, minor naming, small simplifications.

Findings are always anchored at `<file>:<line>`.

## Design notes

- Specialists use `model: sonnet` and tools `Glob, Grep, Read` only. They
  cannot edit — that's deliberate. Part 2 is where edits happen, with a
  test-gated batch loop.
- The coordinator spawns all specialists in a single message (parallel `Agent`
  calls) and does not re-read the source. This keeps the coordinator's
  context small enough to hold all specialist reports comfortably.
- The API-consistency reviewer reads **signatures only**, not method bodies.
  Produces a canonical naming table as its primary artifact.
- UI rubric defaults to Nielsen's 10 heuristics. Swap for an internal style
  guide if you have one — see `TEMPLATE_AUTHORS.md`.
- Part 2 commits one batch per commit, so `git log` shows the full trail and
  you can revert any individual batch without unwinding the rest.
