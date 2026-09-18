---
title: "Generated client widens a nullable scalar into a scalar-or-array union"
category: problem
status: open
date: 2026-09-05
tags: [frontend, api-client, openapi, zodios, typescript, risk, correlation, generated-code]
related:
  - problems/front-check-does-not-check-what-you-think
  - concepts/api-client-generation
---

# Problem: generated client widens a nullable scalar into a scalar-or-array union

## Symptom

For `RiskMatrixCell.value` the generated Zodios client states two different things
about the same field:

- the **Zod validator** says `z.union([z.number(), z.null()]).optional()` — a nullable
  scalar, which matches the backend;
- the **TypeScript type** says `number | (number | null)[] | null | undefined` — a
  scalar *or an array*.

The runtime validator will reject an array. The compiler will happily accept one.

## Root Cause

The type emitted by the OpenAPI → TypeScript step is wider than the schema it was
generated from. The backend never emits an array in that position, so nothing fails at
runtime and the drift is invisible in normal use.

The damage is done at the consumer. The previous correlation heatmap passed
`cell.value` straight into an ECharts data tuple with no annotation, so the widened
type was accepted silently: a value the validator would have rejected would have been
typed as legal on the way into the chart. The compiler was not wrong — it was told the
wrong thing.

The project already carries `frontend/scripts/fix-openapi-discriminators.mjs`, a
post-generation fixup, which shows this *class* of generator drift is known. This
particular instance is not covered by it.

## Solution

Consumers must narrow explicitly rather than trusting the generated type. In
`correlationHelpers.ts` the widened shape is accepted at the boundary and passed
through a local `scalar()` narrowing helper, which returns a `number | null` and is
the only thing downstream arithmetic sees.

The narrowing is deliberately **local and dependency-free**: importing the project's
existing `singleValue` helper would pull `generated.ts` into the module graph, and a
unit test must not depend on an artifact that has to be generated before the test can
run.

## Prevention

When a generated type is a union that the backend schema cannot produce, do not widen
the consumer to match it — narrow at the boundary and keep the narrow type inside.
Treat a mismatch between the emitted validator and the emitted type as a generator
bug worth recording, not a fact about the API.

## Impact

Latent, not active: no endpoint currently returns an array there. The cost was a
missing compile-time guard on a path where a malformed cell would have reached a chart
renderer untyped.

## Source files

| Role | Path |
|------|------|
| Backend schema — the authority | `backend/app/schemas/risk.py` |
| Emits the N x N matrix | `backend/app/services/risk_plugins/correlation.py` |
| Narrows at the boundary | `frontend/src/lib/components/risk/correlationHelpers.ts` |
| Consumer that previously trusted the wide type | `frontend/src/lib/components/risk/CorrelationHeatmap.svelte` |
| Existing post-generation fixup for a sibling problem | `frontend/scripts/fix-openapi-discriminators.mjs` |
