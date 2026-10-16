---
title: "Svelte template branches were invisible to V8 coverage: an empty `branchMap` for `{#if}` — istanbul instrumentation of the source counts them (`2e104b919`)"
category: problem
status: resolved
date: 2026-08-31
tags: [frontend, testing, coverage, svelte, istanbul, measurement]
related: [concepts/coverage-rate-vs-volume]
---

# Problem: `{#if}` in markup produces an empty `branchMap`

## Symptom

A lane reported a branch that a **green test asserts on both sides** and that
coverage reports as uncovered.

`ProviderAssignmentSection.svelte:402`, `{#if idTypeAutoSet}` — the test asserts
the true side (element present) *and* the false side (element absent). The
measurement says `arms=[0, 4]`: one side never executed.

## Root cause

Verified on a purpose-built minimal case: a component with a single `{#if}` and
two tests rendering the two sides.

```
Toggle.svelte in the report: True
branchMap: {}          ← empty
hits b   : {}
```

**V8 registers no branch at all for an `{#if}` in a Svelte template**: the compiler turns conditional markup into
closures that V8 does not recognise as decisions. The branches that *do* appear in a `.svelte` file come from its
`<script>` block, which is ordinary JavaScript. Conditional markup was invisible to the measurement, and where it did
appear it was mis-attributed.

> *Corrected on 2026-10-13 (backlog C-72)*: this paragraph said «Istanbul registers no branch». The empty `branchMap`
> was V8's, read back through sourcemaps; istanbul instrumentation applied to the source **before** the Svelte
> compiler does count the template's branches — on the same minimal component, V8 saw none where istanbul saw two.

Three lanes hit this independently — `table` reported "branches demonstrably
executed yet reported uncovered", `assets` measured "36 % and 58 %
under-estimates" — before it was isolated.

## Consequences

1. **The frontend's 53,75 % branch figure is an under-estimate.** The
   denominator ignores template conditionals while the numerator suffers from the
   mis-attributions.
2. **Branch percentages of `.svelte` files are indicative only, and must never be
   quoted.** Those of `.ts` files are exact.
3. **Extracting logic into `.ts` was right for a reason nobody had stated.** It
   is not only about testing without mounting — it is **the only way to measure**
   it. A branch that stays in the `.svelte` can be neither counted nor proven
   covered.

Point 3 is the durable one: it turned a stylistic preference into a measurement
requirement, and it is why the file-splitting work
(`ImportWizardModal` → four extracted modules at 100 %) is worth doing even where
it does not move the headline number.

## Related distortion

A second, smaller distortion has the same flavour: **branch percentages on small
`.svelte` files**. A `SettingSelect` at 50 % is one arm out of two — the compiled
output of a small control exposes very few arms, so the ratio is dominated by
noise. The real matrix has to be counted by hand.

## Status

**Resolved** by `2e104b919` (2026-08-30, shipped in 1.1.0), the day before this page was written from the earlier
measurement: the build is instrumented by `vite-plugin-istanbul`, which reads the source before the compiler
rewrites it, and the branches counted on `.svelte` files went from 0 to 11 620. The same commit made the JS pipeline
istanbul end to end and stopped a double count of shared files. Points 1 and 2 of the consequences describe the V8
measurement; point 3 stands. What remains is weaker and documented: the remap from compiled closures is reliable about
*whether a component was reached*, much less about *whether line X is covered* (`coverage-model.md`, «Coverage is a
map, not a grade»).

Until 2026-10-13 this section read «Accepted, not fixed»; the backlog's C-72 found it contradicted by `2e104b919`.

## Source files

| Role | Path |
|------|------|
| Real case | `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte` (~402) |
| Coverage merge (istanbul) | `frontend/scripts/js-coverage-report.js` |
| Build instrumentation | `frontend/vite.config.ts` — `vite-plugin-istanbul`, gated on `COVERAGE_INSTRUMENT=1` |
| Vitest coverage provider | `frontend/vitest.config.ts` — `provider: 'istanbul'` (V8 reports an **empty branch map** for a Svelte template; that is the whole reason for this page) |
| Report classification | `scripts/test_runner/_coverage.py` — `coverage-report --lang js` |
| Developer docs, «Why istanbul, and no monocart any more» | `mkdocs_src/docs/developer/test-walkthrough/coverage-model.md` |
| Extraction precedent | `frontend/src/lib/features/transactions/import/ImportWizardModal.svelte` |

> **Path note (2026-09-01)**: this table cited `frontend/mcr.config.js`. **That file
> has never existed** — it was proposal B.3 of `plan-p7-js-coverage.md:227`, and the
> proposal was not taken. **Monocart was removed from the project**: its only job was
> resolving V8 coverage ranges back through sourcemaps to `.svelte`/`.ts`, and
> instrumenting the build at `vite` level removed the job. See the comment in
> `frontend/e2e/fixtures/playwright.ts` (~L297): *"there is no monocart here any
> more"*. JS coverage today is **istanbul end to end** — `vite-plugin-istanbul` for
> the build, `@vitest/coverage-istanbul` for units, `istanbul-lib-coverage` for the
> merge.
