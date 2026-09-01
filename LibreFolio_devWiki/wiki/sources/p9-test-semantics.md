---
title: "P9 — test semantics: what the suite is allowed to assert"
category: source
source_type: plan
date_ingested: 2026-08-31
original_path: "LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/plan-p9-test-semantics-COMPLETO.md"
tags: [testing, semantics, coverage, method, backend, frontend]
related:
  - concepts/load-only-red-is-a-product-defect
  - concepts/characterisation-test-latch
  - problems/namedcache-clear-leaves-admission-filter
  - problems/svelte-template-branches-not-instrumented
---

# Source: P9 — test semantics

## Summary

P9 is the lane that asked what the suite's numbers actually *mean*, after P7 made
JS coverage visible and P8 made the execution model explicit. Its output is less
code than vocabulary: which reds are product defects, which are instrumentation,
and which measurements may be quoted.

## Key Takeaways

- **OOM under JS coverage is instrumentation, not product.** A `SIGABRT` in a
  V8 heap during a consolidated coverage run says the run is too large, not that
  the application leaks. It produced the chunking rule in
  [[concepts/playwright-run-consolidation]].
- **A red that appears only under load is a product defect** — the rule and its
  four supporting cases are in
  [[concepts/load-only-red-is-a-product-defect]].
- **Behaviour that is wrong but undecided gets frozen, not fixed** — see
  [[concepts/characterisation-test-latch]].
- **The `NamedCache.clear()` defect** was found here:
  [[problems/namedcache-clear-leaves-admission-filter]]. theine 2.0.0's W-TinyLFU
  admission filter survived the clear and rejected every subsequent `set()`,
  permanently and silently. The 19-vs-20-entry boundary is what identified it.
- **W9** closed the lane by reconciling the suite's numbers against a single
  clean run instead of an accumulation of partial ones.

## The method note worth keeping

P9 repeatedly refused to accept a green as evidence. Two habits carried it:

1. **A test that does not fail against HEAD has not described the bug.** The
   first hypothesis for the risk-catalogue hang was disproved exactly this way —
   the unit test written on it passed against unpatched code.
2. **Compare the same file across reports** rather than trusting one report's
   summary. It is how two instrument defects were caught in P7 and how the
   backend-coverage copy-back hole was caught later.

## Source files

| Role | Path |
|------|------|
| Cache wrapper | `backend/app/utils/cache_utils.py` |
| Consolidation and chunking | `scripts/test_runner/_consolidate.py` |
| Triage protocol | `.github/skills/devpy-tools/test-triage/SKILL.md` |
| Original plan | `LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/plan-p9-test-semantics-COMPLETO.md` |
