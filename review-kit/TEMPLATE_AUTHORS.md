# Shipping review-kit with a template repo

This guide is for people who maintain a template repo (e.g. a cookiecutter,
a GitHub "template repository", or a starter fork) and want the review-kit
to be available out-of-the-box when someone forks or templates from it.

If you just want to **use** the kit, see `USAGE.md`.

---

## What to ship

Copy the `.claude/` directory from this kit into the root of your template
repo:

```
your-template/
├── ...
└── .claude/
    ├── agents/
    │   ├── code-api-consistency-reviewer.md
    │   ├── code-frontend-reviewer.md
    │   ├── code-python-reviewer.md
    │   ├── code-theming-reviewer.md
    │   └── code-ui-heuristics-reviewer.md
    └── commands/
        ├── review-init.md
        ├── review.md
        └── review-apply.md
```

If your template already has a `.claude/` directory, merge — don't overwrite.
The kit only adds files under `agents/code-*-reviewer.md` and `commands/review*.md`,
so conflicts with other Claude Code config are unlikely.

Also ship `USAGE.md` (so forkers have a user guide), and optionally this file.
The kit's `README.md` is a landing page you can keep, adapt, or drop.

---

## What forkers experience

When someone forks your template and opens Claude Code, they see three slash
commands available: `/review-init`, `/review`, `/review-apply`.

If they run `/review` or `/review-apply` first, those commands detect
un-instantiated `{{PLACEHOLDER}}` tokens and route them to `/review-init`.
So the **expected first interaction** is always `/review-init`.

`/review-init` does a one-shot setup:

- Detects defaults from the repo (test runner, linter, which specialists are
  relevant based on file types present).
- Asks a short question set (target file, which specialists to keep, test
  command, optional lint command).
- Fills placeholders in each specialist, deletes specialists the repo doesn't
  need, removes the deleted specialists from `/review`'s fan-out list, and
  commits the result as a single setup commit.

Forkers don't need to read any `.claude/` file by hand unless they want to
customize beyond the init flow.

---

## Customizing the kit for your template

All of these are optional — the stock kit is designed to be useful as-is.

### Pre-instantiate placeholders

If your template always targets the same layout (e.g. every fork has a main
module at `src/<name>/core.py`), you can pre-fill `{{TARGET_FILE}}` in the
specialist files before shipping. `/review-init` still runs cleanly — it just
has nothing to do for the pre-filled placeholders.

### Drop specialists you'll never need

If your template is for pure-Python libraries, you can delete:
- `code-frontend-reviewer.md`
- `code-ui-heuristics-reviewer.md`
- `code-theming-reviewer.md`

Also remove them from the fan-out list in `commands/review.md`. `/review-init`
will not recreate them.

### Adjust severity rubric or scope

The severity rubric (🔴 / 🟡 / 🟢) and per-specialist `## What to check`
sections are plain markdown in each agent file. Edit them to match your
house style — e.g. swap Nielsen's 10 heuristics for an internal design
guide in `code-ui-heuristics-reviewer.md`, or add a fourth severity tier.

The orchestrator (`commands/review.md`) doesn't know the rubric details; it
just stitches the reports together. So rubric changes inside a specialist
propagate naturally without any cross-file updates.

### Tighten the default test command

If your template always uses the same test runner, edit
`commands/review-apply.md` to replace `{{TEST_COMMAND}}` with the fixed value
before shipping. `/review-init` will skip asking about it.

Do **not** remove the test-gate logic itself — the whole safety story of Part 2
depends on it. If your forkers genuinely have no tests, prefer leaving the
placeholder so they hit the "configure tests or pass `--no-tests`" message
rather than silently applying unverified edits.

### Add a specialist

The convention for a new specialist:

1. Create `.claude/agents/code-<name>-reviewer.md` with frontmatter:
   ```
   name: code-<name>-reviewer
   description: "..."
   tools: Glob, Grep, Read
   model: sonnet
   ```
2. Use the same output format as the other specialists: opening one-liner,
   severity-tagged findings anchored at `file:line`, closing cross-cutting
   themes section.
3. Add it to the fan-out list in `commands/review.md`.
4. Pick a short tag name (`security`, `perf`, `docs`) and tell users to use it
   with `--only-tags` / `--skip-tags`. Document the tag in `USAGE.md`'s
   "What each specialist looks at" table.

Specialists are stateless markdown files — there's no registry, no index,
no import plumbing to update.

---

## Versioning the kit inside your template

The kit is a set of flat markdown files with no versioning mechanism of its
own. If you want to track which version of the kit your template carries,
the lightest option is to record the upstream commit hash in a comment at
the top of `.claude/agents/README.md` (or similar), and bump it when you
pull in changes.

Forkers inherit whatever version you shipped. There's no auto-update path —
that's on purpose, because the files are meant to be edited per-project.
