---
title: "P7 — JavaScript/Svelte coverage instrumentation"
category: source
source_type: plan
date_ingested: 2026-08-31
original_path: "LibreFolio_developer_journal/Release_2/phases/07_coverageAndConsolidationCampaign/plan-p7-js-coverage.md"
tags: [testing, coverage, frontend, svelte, playwright, vitest, monocart, instrumentation]
related:
  - concepts/coverage-rate-vs-volume
  - problems/svelte-template-branches-not-instrumented
  - problems/e2e-python-coverage-lost-above-two-workers
---

# Source: P7 — JavaScript coverage, levels A and B

## Summary

Before P7 the project measured **only Python**. All three HTML reports were
Python: `htmlcov-backend` (backend tests), `htmlcov-frontend` (the backend, as
driven by frontend E2E) and `htmlcov` (combined). Across **92 603 lines of
`.svelte`** and **41 338 of `.ts`** the visibility was **zero** — no data on which
components the E2E walk, and none on which nobody touches.

P7 added two levels — **A**: vitest unit coverage; **B**: Playwright E2E coverage
via `page.coverage` — merged into one report through
`monocart-coverage-reports` 2.12.12 and `vitest-monocart-coverage` 4.0.2.

## The verification that made it cheap

The obstacle assumed to be largest — *"the E2E would have to run against a
different artefact from the one we ship"* — **did not exist**. Every claim below
was measured on the repository with a spike, not estimated:

| checked | outcome |
|---|---|
| E2E already run a **debug** build | ✅ `cmd_server`: `if test_mode: debug_mode = True` |
| On-disk marker | ✅ `frontend/build/.build-debug` = `1` |
| Sourcemaps reach `.svelte` | ✅ 83 maps, 77 with `sourcesContent`, **196/199** components reachable |
| V8 coverage collected from Chromium on the served build | ✅ 14 scripts, 12 with usable sourcemap |
| Remap of executed bytes → `src/**/*.svelte` | ✅ original paths correct |
| Both Playwright projects are Chromium | ✅ `desktop` + `mobile` — `page.coverage` is Chromium-only, not a limit here |
| `auto_build_frontend` handles a mode mismatch | ✅ rebuilds by itself |

## Architecture

```
vitest    ──(vitest-monocart-coverage)──▶ coverage-js/unit/raw ─┐
                                                                ├─▶ mcr merge ─▶ coverage-js/combined
Playwright ──(page.coverage fixture)───▶ coverage-js/e2e/raw   ─┘
```

`raw` as the meeting format deliberately mirrors the Python side, where
subprocess `.coverage.*` files are merged with `coverage combine`. Anyone who
knows `_coverage.py` recognises the shape.

## Key Takeaways

- **A fixture, not `monocart-reporter`.** The reporter would also replace the
  test report, which today is Playwright's HTML and works. A fixture adds
  coverage without touching anything else.
- **`sourceFilter` restricted to `src/`.** The spike produced 47 false positives
  from `src/runtime/client/*.js` — SvelteKit's internal runtime, not our code.
  Without the filter the report lies.
- **`all` (never-executed files at 0 %) only on the combined report.** Listing
  199 `.svelte` at 0 % on the unit report would be noise: vitest cannot execute
  them by construction. On the combined report it is exactly the requested
  information — *what nobody touches*.
- **No blocking thresholds.** Svelte 5 compiles templates into closures; the
  remap reliably says *whether* a component or branch was traversed, but per-line
  percentages are not trustworthy enough to pass or fail a build. This
  observation later hardened into
  [[problems/svelte-template-branches-not-instrumented]].

## What it found

Eight excursions off-plan, of which **three product defects** and **two defects
of the measuring instrument** — the `gracefulShutdown` window and the two-step
merge. Both instrument defects produced **missing data without failing**, which
is why the final verification did not stop at "green" but compared the same files
across all three reports.

That pattern recurred later at a larger scale in
[[problems/e2e-python-coverage-lost-above-two-workers]].

## Source files

| Role | Path |
|------|------|
| Merge (istanbul-lib-coverage) | `frontend/scripts/js-coverage-report.js` |
| Build instrumentation | `frontend/vite.config.ts` — `vite-plugin-istanbul` |
| Unit coverage provider | `frontend/vitest.config.ts` — `provider: 'istanbul'` |
| Dependencies | `frontend/package.json` — `vite-plugin-istanbul`, `@vitest/coverage-istanbul`, `istanbul-lib-*` |
| E2E coverage fixture | `frontend/e2e/fixtures/playwright.ts` |
| Coverage CLI | `scripts/test_runner/_coverage.py` |
| Reports | `htmlcov-frontend/`, `frontend/coverage-js/` |
| Original plan | `LibreFolio_developer_journal/Release_2/phases/07_coverageAndConsolidationCampaign/plan-p7-js-coverage.md` |

> **Path note (2026-09-01)**: this table cited `frontend/mcr.config.js`. **That file
> has never existed** — it was proposal B.3 of `plan-p7-js-coverage.md:227`, and the
> proposal was not taken. **Monocart was removed from the project**: its only job was
> resolving V8 coverage ranges back through sourcemaps to `.svelte`/`.ts`, and
> instrumenting the build at `vite` level removed the job. See the comment in
> `frontend/e2e/fixtures/playwright.ts` (~L297): *"there is no monocart here any
> more"*. JS coverage today is **istanbul end to end** — `vite-plugin-istanbul` for
> the build, `@vitest/coverage-istanbul` for units, `istanbul-lib-coverage` for the
> merge.
