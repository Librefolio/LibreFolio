---
title: "--fresh-run, --resume, and the third state that is neither"
category: concept
date: 2026-08-31
updated: 2026-11-13
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
Those are separate flags — `--cov-clean-backend`, `--cov-clean-backend-e2e` (the old
spelling `--cov-clean-frontend` is an alias: it means backend-from-E2E) and `--cov-clean-js`. A percentage quoted from
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

For any number you intend to **quote, compare or record** (since project 71, 13/11/2026):

```bash
./dev.py test --quotable all
```

`--quotable` stands for `--fresh-run --coverage all` and the three cleanings, all of them —
`--cov-clean-backend-e2e` included, which the hand-written command once forgot. It refuses
whatever would make the run partial (`--resume`, test names, `--fail-fast`, the provider
filters, another `--coverage`, `--list`, `--run-status`), and the summary it writes,
`.coverage_data/coverage-summary.json`, says `quotable: true` only for a green run with every
coverage piece present and a tree that was clean when it began. See
[[concepts/coverage-rate-vs-volume]] for how to read it.

For any number you intend to **act on locally**, anything is fine — but do not
carry it forward.

## Each invocation times itself

Until 13/11/2026 the campaign file held **one** slot for the start of the running
invocation. Two invocations of the same checkout at once — a long run, and a short
`dev.py test utils …` started by hand meanwhile — shared it: the short one took the slot and,
ending, cleared it; the long one then ended with no start, recorded nothing, and its closing
note read the short one's seconds («This invocation: 3s» after an hour). Now
`campaign_begin()` returns the start to its own invocation and `campaign_end()` takes it back;
the file only collects the finished runs. Pinned by
`TestEachInvocationTimesItself` in `backend/test_scripts/test_utilities/test_test_runner_cli.py`.

Each run also keeps its durations — per category, Playwright spec and test, vitest file,
pytest unit — in `.coverage_data/durations.json`, and its campaign record names the file.

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
| `resume` gating in the serial path | `scripts/test_runner/_common.py` (~296) |
| `resume` gating in the consolidated path | `scripts/test_runner/_consolidate.py` — `already_green` |
| Coverage cleanup helpers, piece check, summary | `scripts/test_runner/_coverage.py` |
| `--quotable` expansion and refusals | `scripts/test_runner/_cli.py` — `_prepare_args`, `_refused_quotable` |
| Durations accumulator | `scripts/test_runner/_run_cache.py` — `RunDurations`, `write_durations` |
