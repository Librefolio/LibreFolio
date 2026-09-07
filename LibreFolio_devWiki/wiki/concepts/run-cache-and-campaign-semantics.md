---
title: "--fresh-run, --resume, and the third state that is neither"
category: concept
date: 2026-08-31
tags: [testing, test-runner, coverage, cli, gotcha]
related: [concepts/derived-test-inventory, concepts/coverage-rate-vs-volume]
related_problems: [resume-mode-stale-import, coverage-mode-stale-import, coverage-percent-mixed-lines-and-branches]
---

# Concept: the run cache has three states, and only two have names

## The two flags

| Flag | What it does |
|---|---|
| `--fresh-run` | **deletes** `.run_cache.json` before starting, and opens a new *campaign* |
| `--resume` | **consults** the cache: units already recorded green are not re-run |

Both write to the cache: `mark_passed` / `mark_failed` run unconditionally, on
every invocation, whether or not either flag was given.

## The third state

Omitting both is **not** the same as `--fresh-run`, and the difference is easy to
miss because the visible behaviour of the run itself is identical (everything
executes — `is_passed` is gated behind `resume and …`).

What differs is the **state left behind**:

| | cache cleared | cache consulted | cache written | campaign reset |
|---|---|---|---|---|
| `--fresh-run` | ✅ | ❌ | ✅ | ✅ |
| `--resume` | ❌ | ✅ | ✅ | ❌ (continues) |
| neither | ❌ | ❌ | ✅ | ❌ |

So a bare run **merges its results into whatever a previous run left there**.
The next `--resume` then trusts a cache assembled from two different worlds.

The same shape applies to coverage, and that is where it has already cost a
wrong reading: `--fresh-run` clears the *run cache*, not the *coverage data*.
Those are separate flags — `--cov-clean-backend`, `--cov-clean-frontend` (which
actually means backend-from-E2E) and `--cov-clean-js`. A percentage quoted from
a run that did not clean is a percentage **accumulated over runs that were never
cleaned**, and it will read higher than the truth.

> The 92,33 % backend baseline used for months was accumulated that way. It was
> not wrong by much — but it was not the number anyone thought they were reading,
> and it sat next to a *second* reading error
> ([[problems/coverage-percent-mixed-lines-and-branches]]) which made a
> non-existent regression look real.

## The campaign file is deliberately separate

`.campaign.json` is not part of the run cache, for a precise reason:

> `clear_all()` wipes the run cache, and the campaign is exactly what has to
> **survive the wipe that starts it**.

One campaign = one `--fresh-run` plus every `--resume` after it. It reports two
durations, answering two different questions:

| | meaning |
|---|---|
| **machine time** | the sum of the invocations — what the suite costs to run |
| **wall time** | from the fresh-run to now — machine time plus the gaps, which is where the fixes were written |

Reporting only the first hides that a "40-minute suite" took an afternoon;
reporting only the second blames the runner for time spent editing.

`--run-status`, a bare `--fresh-run` with no category, and the reporting
sub-commands are deliberately **untimed**: they run no tests, and 0 s
invocations would make the invocation count mean less than it should.

## Operational rule

For any number you intend to **quote, compare or record**:

```bash
./dev.py test --fresh-run --coverage all --cov-clean-backend --cov-clean-js --workers 8 all
```

For any number you intend to **act on locally**, anything is fine — but do not
carry it forward.

## Related failure modes already recorded

Both of the previous run-cache defects were the *same* Python gotcha, in two
different modules:

- [[problems/resume-mode-stale-import]] — `from ._common import _RESUME_MODE`
  freezes `False` at import time; 13 modules never saw `--resume`.
- [[problems/coverage-mode-stale-import]] — identical, for the coverage flag.

The prevention is written on both pages: never import a **mutable global flag**
by name; import the module and read the attribute.

## Source files

| Role | Path |
|------|------|
| Cache + campaign | `scripts/test_runner/_run_cache.py` |
| Flag parsing, `_timed_run`, `_apply_coverage_mode` | `scripts/test_runner/_cli.py` |
| `resume` gating in the serial path | `scripts/test_runner/_common.py` (~257) |
| `resume` gating in the consolidated path | `scripts/test_runner/_consolidate.py` — `already_green` |
| Coverage cleanup helpers | `scripts/test_runner/_coverage.py` |
