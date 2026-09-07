---
title: "An absence sentinel wearing a datum's clothes"
category: concept
date: 2026-08-31
tags: [frontend, typescript, fx, types, refactoring-method]
related_problems: [i18n-key-assertion-false-green]
related: [problems/commit-reported-success-on-rolled-back-batch, sources/settings-lane-and-sixteen-defects]
---

# Concept: when a magic value stands for "missing", make the type say so

## The shape of the bug

`apiResultToFxDataPoint` converted a null/undefined `rate` from the API into
**`0`**.

But **zero is not a possible exchange rate**. It was the absence sentinel,
travelling with the shape of a good datum — and it sat at the boundary with the
API, so it was upstream of everything.

Worse, the backend *declared* the absence: `backend/app/schemas/fx.py:157` has
`rate: Optional[SafeDecimal] = Field(None, …)`, the generated client types it
`(string | null) | undefined`, and the generated Zod validates a union with
`null`. The API said "I have no rate for that day" and the frontend **threw the
information away exactly where it arrived**.

## The tell: a codebase that defends against its own sentinel, half the time

`fxConversionHelper.ts` contained both halves of the contradiction:

```ts
const spread = marketRate !== 0 ? computeSpread(...) : null;   // line 87: zero means absent
...
`${data.marketRate.toFixed(4)}`                                 // line 107: zero means zero
```

**When you find a guard against a magic value in one place and not another, the
magic value is a missing type, not a convention.** That asymmetry is the cheapest
signal available: no bug report is needed to spot it.

## What it actually cost

Fixing only the tooltip was the first, insufficient attempt. The zero was
reaching:

| where | what the user saw |
|---|---|
| `FxCard` chart | **a line collapsing to zero** |
| `FxTable` | `0.0000` in the cell, and **sorted on it** |
| `fx/[pair]` delta | guarded only `first === 0`, so **−100 %** was reachable |
| asset pages | FX signal overlays computing on the zero |
| `FxDataEditorSection` | displayed `rate: 0` and then **refused to save it** (`rate > 0`) |

The last one is the purest form of the defect: a surface exposing a value it
itself classifies as invalid.

## The method: change the type first

`FxDataPoint.rate: number` → `number | null`, **before** touching any consumer.

`svelte-check` then named **40 sites across 7 files** — turning a hunt into a
list, and finding two consumers (`FxPriceSummary`, `FxPairSignal`) that manual
analysis had missed. The prior estimate had been 20-30; the compiler was more
accurate than the survey.

This generalises: when a value's *meaning* is wrong, widen the type first and let
the type checker enumerate the work. The alternative — grepping for the field
name — finds usages but not obligations.

## Keep the two absences distinct

They are not the same and collapsing them loses information:

| value | meaning |
|---|---|
| `undefined` | **no point** for that date |
| `{rate: null}` | a point exists for that date, **without a rate** |

## Charts: break the line, do not join it

`LineDataPoint.value` stays `number`; points gain an explicit `missing?: boolean`,
and `null` reaches ECharts only at render time.

Joining the two ends across a gap would draw a movement that never happened —
**the same lie as the zero, better dressed**. A gap is the honest rendering.

⚠️ A near-miss worth remembering: the first implementation set
`connectNulls: false` **globally** on `LineChart`, which would have changed every
overlay in the application, FX or not. Overlays had been `true`. It is now
opt-in, requested only by `FxPairSignal`, with a test pinning that a series
containing no `missing` points renders byte-for-byte as before. See
[[problems/shared-component-option-changed-globally]].

## Source files

| Role | Path |
|------|------|
| The sentinel's origin | `frontend/src/lib/stores/fxStoreRegistry.ts` — `apiResultToFxDataPoint` |
| The half-guard | `frontend/src/lib/utils/currency/fxConversionHelper.ts` |
| Chart gap | `frontend/src/lib/components/charts/LineChart.svelte`, `lineChartHelpers.ts` |
| Backend contract | `backend/app/schemas/fx.py:157` |

## See also

- [[problems/commit-reported-success-on-rolled-back-batch]] — the mirror image:
  a status value was **narrowed** without enumerating its consumers, and a
  filter downstream silently returned fewer rows.
- [[sources/settings-lane-and-sixteen-defects]] — item D2, and the user's
  decision behind it.
