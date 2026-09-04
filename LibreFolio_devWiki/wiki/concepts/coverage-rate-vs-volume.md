---
title: "Reading coverage: rate versus volume"
category: concept
date: 2026-08-31
tags: [testing, coverage, metrics, frontend, backend, method]
related: [concepts/run-cache-and-campaign-semantics, concepts/test-isolation-classes]
related_problems: [svelte-template-branches-not-instrumented, coverage-percent-mixed-lines-and-branches, e2e-python-coverage-lost-above-two-workers]
---

# Concept: a coverage percentage is a ratio, and both halves move

## The rule

> Before reading a movement in a coverage percentage, ask which of the two terms
> moved. Most of the disappointment about "the number barely moves" is the
> denominator growing at the same time as the numerator.

## What a point costs

| scope | one percentage point |
|---|---|
| Frontend JS/Svelte statements | ~362 statements (denominator 36 195) |
| Frontend lines (istanbul map) | ~321 lines |

Concrete instance: five lanes covered **1 413 lines** and the number moved
**+1 point net**, because the denominator grew in the meantime. Another run
added **+1 366 covered lines** while the denominator grew by 1 448 — files that
no unit test imported were not in the unit map at all, and now are.

> The honest figure for that work is **+1 366 lines**, not the percentage.

## It is a long tail, and that is why it is slow

| | uncovered lines | share |
|---|---|---|
| top 10 files | 2 438 | 30,1 % |
| top 20 | 3 640 | 44,9 % |
| top 50 | 5 444 | 67,2 % |
| top 100 | 6 988 | 86,3 % |

And the suspicion of "whole untested areas" was measured and found **false**:
393 of 394 source files appear in the report; files never executed at all are
**11 files / 148 lines** — 2 % of what is uncovered. The remaining 8 000 lines
are **inside files that are already covered**: they are the branches the happy
path does not walk.

## There is no single number — there are six

The monocart HTML report publishes five and titles itself with the most
generous:

| metric | value | what it counts |
|---|---|---|
| **Bytes** | 83,17 % | bytes of file executed — includes static markup, CSS, strings |
| Lines | 80,35 % | 73 796 / 91 843 non-empty lines |
| Functions | 74,73 % | 7 450 / 9 969 |
| Statements | 69,84 % | 27 708 / 39 675 |
| **Branches** | **53,75 %** | 12 307 / 22 896 |

A sixth exists: *lines containing at least one istanbul statement*
(24 052 / 32 151 = 74,81 %). It is stricter than *Lines* because it excludes
imports, type declarations, markup and CSS — 92 000 lines against 32 000, and
those 60 000 are covered merely because the file loaded.

**The honest one is Branches.** It is the only one that answers *"was this
behaviour verified?"* instead of *"was this line traversed?"*. An
`if (err) log(err)` where `err` is always truthy is 100 % by line and 50 % by
branch: the line is green, the decision was never taken both ways.

The gap says how shallow the coverage is:

| | statements | branches | spread |
|---|---|---|---|
| Backend | 92,39 % | 82,64 % | **9,8 pp** |
| Frontend | 69,84 % | 53,75 % | **16,1 pp** |

The frontend does not merely have less coverage; it has **shallower** coverage.

## What changes for the work

Chasing **lines** is why the number moves slowly: one more line costs a test, one
more branch often costs *the same test written better* — the same mount with a
different prop.

⚠️ Operational trap: `./dev.py test coverage-report --lang js` classifies by
**statement**, the metric the double compilation inflates. To choose where to go,
read **uncovered branches**, not statements.

## Two caveats that make some numbers uncitable

**Branch percentages on small `.svelte` files lie.** A `SettingSelect` at 50 % is
1 arm out of 2: istanbul instruments the *compiled* Svelte, and small controls
expose very few arms in that output. The real matrix has to be counted by hand.
The deeper reason is worse — the `branchMap` for template `{#if}` is **empty**.
See [[problems/svelte-template-branches-not-instrumented]].

**Splitting large files does not raise coverage by itself.** It makes testable
what currently is not. The proof is in-house: the four modules extracted from
`ImportWizardModal` are at **100 %** while the residual `.svelte` is at 57,5 % —
not because those modules were tested better, but because they had been inside
closures reachable only by walking seven wizard steps.

For the same reason a before/after percentage on an extracted file is not a
comparison: the two numbers do not measure the same thing. Saying so is more
useful than showing a delta that would not hold.

## Where to attack, by yield (frontend, measured)

| area | uncovered | coverage | files |
|---|---|---|---|
| `components/transactions` | **1 542** | 69,9 % | 29 |
| **routes (pages)** | **1 074** | 67,8 % | 21 |
| `components/ui` | 947 | 75,5 % | 53 |
| `components/assets` | 720 | 69,3 % | 18 |
| `components/brokers` | **672** | 75,5 % | 17 — *never had a lane* |
| `components/charts` | 618 | 74,6 % | 31 |
| `components/table` | 440 | 67,2 % | 7 |

## Source files

| Role | Path |
|------|------|
| Coverage CLI and report classification | `scripts/test_runner/_coverage.py` |
| Python coverage config | `.coveragerc` |
| JS coverage merge (istanbul) | `frontend/scripts/js-coverage-report.js` |
| JS instrumentation | `frontend/vite.config.ts`, `frontend/vitest.config.ts` |
| Report outputs | `htmlcov-backend/`, `htmlcov-backend-e2e/`, `htmlcov-frontend/` |

> **Path note (2026-09-01)**: this table cited `frontend/mcr.config.js`. **That file
> has never existed** — it was proposal B.3 of `plan-p7-js-coverage.md:227`, and the
> proposal was not taken. **Monocart was removed from the project**: its only job was
> resolving V8 coverage ranges back through sourcemaps to `.svelte`/`.ts`, and
> instrumenting the build at `vite` level removed the job. See the comment in
> `frontend/e2e/fixtures/playwright.ts` (~L297): *"there is no monocart here any
> more"*. JS coverage today is **istanbul end to end** — `vite-plugin-istanbul` for
> the build, `@vitest/coverage-istanbul` for units, `istanbul-lib-coverage` for the
> merge.
