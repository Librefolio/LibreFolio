---
title: "front check does not check what you think it checks"
category: problem
status: resolved
date: 2026-09-05
tags: [frontend, tooling, svelte-check, typescript, e2e, api-client, gates, false-green, false-red]
related:
  - concepts/api-client-generation
  - problems/datatable-filter-options-disappear
---

# Problem: `front check` does not check what you think it checks

## Symptom

`./dev.py front check` (svelte-check) has two independent blind spots that pull in
opposite directions, and both were hit inside a single session:

1. **A false green.** Running it after editing a Playwright spec reports "0 errors"
   while never having opened the file.
2. **A false red.** Running it on a freshly created worktree reported
   **278 errors across 70 files** — in files that had not been touched, including
   4 errors on a line proved byte-identical to `HEAD`.

Either one, taken at face value, produces a wrong conclusion about the change under
test: the first says "my spec type-checks" when nothing checked it, the second says
"my change broke seventy files" when it broke none.

## Root Cause

**Two unrelated causes.**

*The false green*: `frontend/tsconfig.json` carries an `exclude` list containing
`e2e/**`. The E2E specs are therefore outside the checked project. A separate
`frontend/tsconfig.e2e.json` exists, but no gate, script, or CI step references it —
it is configuration that nothing runs.

*The false red*: the Zodios API client is a **generated, git-ignored artifact**.
The repository ships `frontend/src/lib/api/generated.ts.gitkeep` and
`openapi.json.gitkeep` — placeholders, not the files. Until `./dev.py api sync` is
run, the `schemas` object is untyped, every consumer degrades to `any`, and the errors
surface far from the cause. A fresh clone or a new worktree is therefore *born red*.
After `api sync` the same command on the same code reported **2 errors** — both real,
both mine.

The trap is that neither failure mode announces itself. The blind spot is silent by
construction, and the missing-artifact errors look exactly like ordinary type errors
in other people's files.

## Solution

- Run `./dev.py api sync` **before** trusting any `front check` result in a new
  worktree or clone. Treat a first-run error count as an environment reading, not a
  code reading.
- When the count is large and spread across untouched files, verify one instance
  against `git show HEAD:<path>` before believing it. A type error on a line identical
  to `HEAD` is evidence about the toolchain, not about the diff.
- Never cite a `front check` pass as evidence that an E2E spec is type-correct.
  The only real gate on specs is running them.

## Prevention

Treat "which files does this gate actually read?" as a question to answer once, from
the config, rather than inferred from the command name. `exclude` lists and generated
prerequisites are both invisible in the command's output.

A gate that cannot fail on a class of file is not a weak gate — it is *no gate* for
that class, and reporting its green as coverage is a false statement about risk.

## Impact

Any workstream that edits E2E specs and reports "svelte-check clean" is reporting
nothing. Any workstream that opens a new worktree and reports a large error count is
reporting the absence of a generated file.

## Source files

| Role | Path |
|------|------|
| Excludes `e2e/**` | `frontend/tsconfig.json` |
| Exists, referenced by no gate | `frontend/tsconfig.e2e.json` |
| Placeholder for the generated client | `frontend/src/lib/api/generated.ts.gitkeep` |
| Post-generation fixup, evidence the class of problem is known | `frontend/scripts/fix-openapi-discriminators.mjs` |
