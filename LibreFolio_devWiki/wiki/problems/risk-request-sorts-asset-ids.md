---
title: "A risk request sorts asset_ids, so payload order is not render order"
category: problem
date: 2026-09-18
tags: [frontend, risk, testing, e2e, caching]
---

# A risk request sorts `asset_ids`, so payload order is not render order

## Summary

`buildRiskRequest` canonicalises an asset-set scope by sorting `asset_ids` numerically
ascending, so that the same *set* of assets produces the same cache key regardless of the
order the user picked them. The UI, meanwhile, renders selection chips in **name** order.
The two orders therefore disagree, and any test that stubs a risk response by *position*
— "the finding I planted at index 1" — will read the wrong asset unless it reproduces the
sort. This cost a full E2E debugging cycle, because the component was rendering correctly
and only the test's index arithmetic was wrong.

## Details

The normalisation lives in the request builder:

```ts
// frontend/src/lib/risk/riskRequest.ts
return {...scope, asset_ids: sortedNumbers(scope.asset_ids)};
```

This is good design, not a bug: it makes the cache key a property of the *set*, so
selecting `[A, B]` and `[B, A]` hits one cache entry rather than two.

The trap appears when a test mocks the risk endpoint. A correlation payload is positional
— `asset_ids[i]` indexes row/column `i` of the matrix — so a stub that wants to plant "a
redundant pair" must know which asset sits at which position. Reading those ids from the
rendered chips is the obvious move and it is wrong:

| Order | Source | Example |
|-------|--------|---------|
| Chip / DOM order | selection, name-sorted | Apple, Bitcoin, Ethereum, Microsoft |
| Request / payload order | `sortedNumbers`, id-ascending | Apple, Microsoft, Bitcoin, Ethereum |

The fix in a spec is to reproduce the request's own normalisation rather than to work
around the symptom:

```ts
const matrix = [...(await chipIds(page))].sort((left, right) => left - right).slice(0, LIMIT);
```

**Symptom to recognise**: the assertion fails naming an asset pair that is genuinely on
screen and genuinely correct — the rendering is right, the index is not. If a correlation
test fails but a screenshot shows a sensible matrix, suspect the ordering before the
component.

A related consequence outside tests: **never** derive a label, colour, or `data-testid`
from a payload index by looking it up in the selection array. Always go through
`output.asset_ids[i]`, which is the payload's own key.

## Source files

| Role | Path |
|------|------|
| Normalisation | `frontend/src/lib/risk/riskRequest.ts` |
| Positional consumer | `frontend/src/lib/components/risk/correlationHelpers.ts` |
| Spec that hit the trap | `frontend/e2e/portfolio/risk-lab.spec.ts` |

Related: [[problems/front-check-does-not-check-what-you-think]]
