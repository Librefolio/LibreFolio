---
title: "Svelte template branches are not instrumented"
category: problem
status: accepted
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

**Istanbul registers no branch at all for an `{#if}` in a Svelte template.** The
branches that *do* appear in a `.svelte` file come from its `<script>` block,
which is ordinary JavaScript. Conditional markup is invisible to the measurement,
and where it does appear it is mis-attributed.

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

**Accepted, not fixed.** No workaround was attempted: instrumenting Svelte
markup would mean changing the compile pipeline. The mitigation is editorial —
read `.ts` branch figures, treat `.svelte` ones as hints, and extract logic when
a branch matters.

## Source files

| Role | Path |
|------|------|
| Real case | `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte` (~402) |
| Coverage merge (istanbul) | `frontend/scripts/js-coverage-report.js` |
| Build instrumentation | `frontend/vite.config.ts` — `vite-plugin-istanbul`, gated on `COVERAGE_INSTRUMENT=1` |
| Vitest coverage provider | `frontend/vitest.config.ts` — `provider: 'istanbul'` (V8 reports an **empty branch map** for a Svelte template; that is the whole reason for this page) |
| Report classification | `scripts/test_runner/_coverage.py` — `coverage-report --lang js` |
| Extraction precedent | `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` |

> **Path note (2026-09-01)**: this table cited `frontend/mcr.config.js`. **That file
> has never existed** — it was proposal B.3 of `plan-p7-js-coverage.md:227`, and the
> proposal was not taken. **Monocart was removed from the project**: its only job was
> resolving V8 coverage ranges back through sourcemaps to `.svelte`/`.ts`, and
> instrumenting the build at `vite` level removed the job. See the comment in
> `frontend/e2e/fixtures/playwright.ts` (~L297): *"there is no monocart here any
> more"*. JS coverage today is **istanbul end to end** — `vite-plugin-istanbul` for
> the build, `@vitest/coverage-istanbul` for units, `istanbul-lib-coverage` for the
> merge.
