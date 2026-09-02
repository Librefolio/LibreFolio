---
title: "The 2026-08 coverage campaign"
category: source
source_type: plan
date_ingested: 2026-08-31
original_path: "LibreFolio_developer_journal/Release_2/phases/07_coverageAndConsolidationCampaign/plan-storico-coverage-campaign.md, plan-storico-coverage-campaign-2.md"
tags: [testing, coverage, campaign, frontend, backend, metrics]
related:
  - concepts/coverage-rate-vs-volume
  - concepts/run-cache-and-campaign-semantics
  - problems/coverage-percent-mixed-lines-and-branches
  - problems/e2e-python-coverage-lost-above-two-workers
  - problems/svelte-template-branches-not-instrumented
---

# Source: coverage campaign, parts 1 and 2

## Summary

A multi-lane campaign to raise frontend coverage after P7 made it measurable.
Lanes were organised by area (`assets`, `table`, `transactions`, `fx`, `sync`,
`logic`, `settings`, …), each closing with a measurement and a written account of
what it found beyond coverage.

Final position: suite **15/15** in 46 m 55 s, lines **78,02 %**, branch arms
**59,45 %**, backend **90,18 %**.

> **⚠️ Read the caveat before quoting these three figures** →
> [§ Caveats attached to the numbers](#caveats-attached-to-the-numbers).
> Two of them are reconstructible only in kind; the third is not covered by the
> caveat at all.

### How these three were taken

| figure | instrument | provenance |
|---|---|---|
| lines **78,02 %** | frontend istanbul, whole-frontend merge via `js-coverage-report.js` | **comparable.** It sits inside the band the lanes recorded around it — 78,07 % (`plan-storico-scheduler-e-fx`, L184) and 78,13 % (`plan-storico-undici-difetti`, L187) — same metric, same instrument |
| branch arms **59,45 %** | same run, `arm` count not statement count | **comparable**, same band: 59,39 % and 59,53 % at those two checkpoints. Note the campaign's own warning that this number is **mixed and half-blind**: istanbul instruments *compiled* Svelte, so template branches barely register in the denominator |
| backend **90,18 %** | `coverage report` TOTAL, **lines + branch arms** — the *same formula* as 90,10 % | **established** (see below) |

**Command and worker count, for this measurement only:**

```bash
dev.py test --fresh-run --coverage all \
    --cov-clean-js --cov-clean-backend --cov-clean-backend-e2e --workers 8 all
```

The earlier figures quoted across the campaign were taken at worker counts that were not
written down, and for those the count remains **not reconstructible**. This one is known.

#### `90,18 %` is not a fourth definition — it is 90,10 % measured later

It comes from the `TOTAL` row of `htmlcov-backend/index.html` produced by that run:

```
TOTAL    37085    2810    11048    1719    90.18%
```

`statements = 37085`, `miss = 2810`, `branches = 11048`, `partial = 1719`. That is the
**mixed lines-and-branch-arms** formula — **the same one that produced 90,10 %**, not a
third scale. The gap between them is not a change of definition and not a regression: they
are two successive measurements with different code in between, and what landed in between
is the scheduler work and the tests covering it.

> **If you try to check the arithmetic by hand, it will not come out.** `(37085 − 2810 +
> 11048 − 1719) / (37085 + 11048)` gives **90,59 %**, not 90,18 %. The column labelled
> `partial` in the HTML report is **not** the term `coverage.py` puts in the numerator —
> it uses `missing_branches`, which is a larger number (≈ 1 917 here, against 1 719
> partials). The five visible numbers do not reproduce the total on their own. This is
> recorded because the natural next move on seeing a figure you cannot reproduce is to
> assume it is wrong, and here it is not.


## Key Takeaways

- **Rate versus volume** is the campaign's central lesson: five lanes covered
  1 413 lines for **+1 point**, because the denominator grew alongside. See
  [[concepts/coverage-rate-vs-volume]] for the full arithmetic, the long-tail
  table, and the six competing metrics.
- **"The backend never dropped."** The apparent 92,33 → 90,10 regression was a
  change of formula, not of coverage:
  [[problems/coverage-percent-mixed-lines-and-branches]]. The signal was there —
  branch coverage had not moved.
- **E2E Python coverage was being lost above two workers**, writing five empty
  files with no warning:
  [[problems/e2e-python-coverage-lost-above-two-workers]].
- **Comparisons need a clean baseline.** Coverage data accumulates across runs
  unless `--cov-clean-*` is passed; `--fresh-run` does not do it. See
  [[concepts/run-cache-and-campaign-semantics]].
- **Splitting a file does not raise coverage; it makes coverage possible.** The
  four modules extracted from `ImportWizardModal` sit at 100 % while the residual
  `.svelte` is at 57,5 %.
- The suspicion of "whole untested areas" was **measured and found false**: 393
  of 394 source files appear in the report, and code never executed at all is
  11 files / 148 lines — 2 % of what is uncovered.

## Where the remaining work is

| area | uncovered lines | coverage | note |
|---|---|---|---|
| `components/transactions` | 1 542 | 69,9 % | largest single pool |
| routes (pages) | 1 074 | 67,8 % | |
| `components/ui` | 947 | 75,5 % | |
| `components/assets` | 720 | 69,3 % | |
| `components/brokers` | 672 | 75,5 % | **never had a lane** |

## Caveats attached to the numbers

Figures quoted across the campaign's own documents disagree with each other because
they were taken at different worker counts **and under two different formulas**. Which
formula each one uses is the thing that was never written next to it:

| backend figure | formula | note |
|---|---|---|
| **92,33 %** | **lines only** | the pre-change baseline — the only pure-lines figure in the set |
| **90,10 %** | lines + branch arms (mixed) | the same coverage as 92,33 under the other formula. This pair *is* the phantom "regression" |
| **90,46 %** | mixed | 90,10 with E2E Python coverage folded in (+0,36) |
| **92,40 %** | mixed | closing figure of the sync/logic lanes |
| **90,18 %** | mixed | final validation run, 2026-08-31, `--workers 8` |

**Comparing 92,33 with 90,18 means comparing two formulas** — precisely the error this
campaign documented in [[problems/coverage-percent-mixed-lines-and-branches]] and then
committed again in its own closing line. Within the mixed column the figures *are*
comparable to each other; across the columns they are not, at any worker count.

Frontend lines quoted across the same documents: 74,81 / 75,29 / 77,07 / 78,02 / 83,17 —
these differ by scope and run, not by formula.

> **Corrected 2026-09-01.** This caveat previously listed only `92,33 / 90,10` for the
> backend, which left the **`90,18 %` quoted in the Final position forty lines above it
> uncovered** — a reader who took the closing figure at face value got no warning at all,
> and the warning that existed named two numbers that were not the one on the page. The
> provenance of `90,18 %` was supplied by the project owner on 2026-09-01 from
> `htmlcov-backend/index.html`; it had been recorded here as "not reconstructible", which
> was true of the wiki's sources but not of the artefact on disk.

### What would settle it

The historical figures are settled only by re-measuring. One run, with **the worker
count and the formula written down next to the result** — as was done for the 2026-08-31
run above, which is why that one number needed no guessing:

```bash
dev.py test --fresh-run --coverage all \
    --cov-clean-js --cov-clean-backend --cov-clean-backend-e2e --workers 8 all
```

`branch = true` in `.coveragerc` makes `coverage report`'s TOTAL a **mixed**
lines-and-branch-arms percentage. That single unwritten fact produced the phantom
`92,33 → 90,10` "regression" —
[[problems/coverage-percent-mixed-lines-and-branches]]. A coverage number without its
formula is not a number; a coverage number without its worker count is not comparable.

## Source files

| Role | Path |
|------|------|
| Coverage CLI and cleanup flags | `scripts/test_runner/_coverage.py`, `_cli.py` |
| Python coverage config | `.coveragerc` |
| JS merge (istanbul) | `frontend/scripts/js-coverage-report.js` |
| JS instrumentation | `frontend/vite.config.ts`, `frontend/vitest.config.ts` |
| Extraction precedent | `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` |
| Original plans | `LibreFolio_developer_journal/Release_2/phases/07_coverageAndConsolidationCampaign/plan-storico-coverage-campaign.md`, `.../plan-storico-coverage-campaign-2.md` |

> **Path note (2026-09-01)**: this table cited `frontend/mcr.config.js`. **That file
> has never existed** — it was proposal B.3 of `plan-p7-js-coverage.md:227`, and the
> proposal was not taken. **Monocart was removed from the project**: its only job was
> resolving V8 coverage ranges back through sourcemaps to `.svelte`/`.ts`, and
> instrumenting the build at `vite` level removed the job. See the comment in
> `frontend/e2e/fixtures/playwright.ts` (~L297): *"there is no monocart here any
> more"*. JS coverage today is **istanbul end to end** — `vite-plugin-istanbul` for
> the build, `@vitest/coverage-istanbul` for units, `istanbul-lib-coverage` for the
> merge.
