---
title: "ASSET_SET risk scope has no primary series, so single-series analytics cannot serve it"
category: problem
status: resolved
date: 2026-09-05
updated: 2026-09-23
tags: [backend, risk, asset-set, scope, plugins, kpi, drawdown, var, architecture]
related:
  - decisions/asset-global-page-shows-no-money
  - problems/generated-client-widens-nullable-scalar
---

# Problem: the ASSET_SET risk scope has no primary series

## Symptom

A plan proposed adding per-asset risk KPI columns (volatility, Sharpe, max drawdown)
to the Asset Global page by asking the existing risk analytics for them over the
selected asset set. No such data can be returned, and the reason is structural rather
than a missing feature flag.

## Root Cause

The risk plugins divide cleanly by what they consume:

- `correlation` and `stress` consume **a set of series** and declare support for
  `ASSET_SET`;
- `historical_kpi`, `drawdown_summary`, `historical_var` and `comparison` each compute
  from **one primary series** — a single asset's history, or the portfolio's aggregate
  valuation curve.

An asset set is neither. It is *n* independent series with no weights, so there is no
aggregate curve to reduce: a drawdown "of the set" is undefined until someone says how
much of each asset is held, and saying that turns the set into a portfolio.

The scope declarations in the plugins are therefore correct, not an oversight. The
four single-series plugins support `ASSET` and `PORTFOLIO` and deliberately never
declare `ASSET_SET`.

This is the same fact, seen from the other side, as the rule that this page shows no
money: **no weights → no aggregate → neither a euro nor a drawdown.**

## Solution

Not worked around. Per-asset KPI columns were deferred rather than faked.

The two honest routes, if the feature is wanted later:

1. **Fan out** — request the single-asset analytics once per selected asset and render
   a column of independent per-asset values. This is *n* separate analyses displayed
   side by side, not an analysis of the set; it costs *n* backend computations and
   must never be labelled as a property of the set.
2. **Give the set weights** — at which point it is a portfolio and belongs on the
   portfolio surface, under the rules that govern that surface.

## Prevention

Before proposing that an existing analytic serve a new scope, check what the analytic
*consumes*, not whether its signature could accept the scope enum. A scope enum is
cheap to add and says nothing about whether the mathematics has an input.

## Impact

One planned deliverable was cancelled for v1 and recorded as deferred. No fallback
value, no zero, and no placeholder number was introduced — which matters, because a
plausible-looking wrong number in a risk column is worse than an absent column.

## Later development — delivered 2026-09-21, verified 2026-09-23

The per-asset analytics exist now, and by neither of the two routes above.

**Route 1 was rejected — first for cost, then, decisively, for correctness.** The asset-set
contract (`A-contratto-asset-set.md`, clause ⓪ — *one preparation per request*): *n* requests at
`asset` scope are *n* preparations with *n* different joint calendars, drawn side by side as if
commensurable. *"The fan-out was not expensive: it was wrong."*

**What was built — one joint measurement, transposed.** One `ASSET_SET` request; the service
prepares the joint series **once per request, before any analytic runs** (the benchmark, when
asked for, joins that same preparation); each analytic answers with one row per asset.

- **Backend — `d3afb92b6`** (workstream P): five auto-discovered plugins — `asset_set_kpi`,
  `asset_set_var`, `asset_set_drawdown`, `asset_set_risk_return`, `asset_set_comparison` — each
  declaring one scope (`ASSET_SET`) and one mode (`HISTORICAL`). `asset_set_kpi` publishes, per
  asset, volatility, max drawdown and its duration, Sharpe, Sortino, worst realization, DaR, CDaR
  and ulcer index; its docstring: *"THE SET IS NEVER SUMMARIZED … this analytic answers n
  questions rather than one, and publishes n rows."* New payload shapes (`RiskAssetSet*Output`)
  rather than new fields on the singular outputs; `RiskAssetSetReturnOutput` has no field for a
  set-level aggregate, so a capital market line cannot come back through the data.
- **Frontend — `032b86959`** (workstream A): L1° and L3° as tables of one row per selected asset —
  *"the ruler becomes the columns, the assets become the rows"*. The five analytics travel in
  **one request** for the two levels, the benchmark in the same one; a selected asset that
  cannot be measured keeps its row, with null cells. The helpers take no currency. (The
  correlation and replay sections still make their own requests.)

**The root cause above still holds, and the code says so twice.** The four singular analytics
still declare only `ASSET` and `PORTFOLIO`. And the observation gate in `service.py` had to learn
the new codes: `context.n_observations` counts the scope's own primary returns and is zero for a
weightless scope, so on the default branch the new analytics were refused for insufficient history
before `compute()` ran; for them the gate now counts the prepared set. No aggregate was invented —
the set still has neither a euro nor a drawdown of its own.

Status moved `open` → `resolved` on 2026-09-23: the deliverable exists; the structural fact that
cancelled the first plan is unchanged.

## Source files

| Role | Path |
|------|------|
| Builds the scope; empty values for an asset set; one preparation per request; observation gate counts the prepared set for `asset_set_*` | `backend/app/services/risk/service.py` |
| Supports ASSET_SET; consumes many series | `backend/app/services/risk_plugins/correlation.py` |
| Supports ASSET_SET; returns no amount without weights | `backend/app/services/risk_plugins/stress.py` |
| Scope and payload schemas; `RiskAssetSet*Output` | `backend/app/schemas/risk.py` |
| Per-asset KPIs on one prepared set (21/09) | `backend/app/services/risk_plugins/asset_set_kpi.py` |
| Per-asset VaR/CVaR | `backend/app/services/risk_plugins/asset_set_var.py` |
| Per-asset drawdown | `backend/app/services/risk_plugins/asset_set_drawdown.py` |
| Per-asset risk/return points, no aggregate | `backend/app/services/risk_plugins/asset_set_risk_return.py` |
| Per-asset beta/correlation against one benchmark | `backend/app/services/risk_plugins/asset_set_comparison.py` |
| Still `ASSET` + `PORTFOLIO` only | `backend/app/services/risk_plugins/historical_kpi.py` |
| Backend tests of the family | `backend/test_scripts/test_services/test_risk_asset_set.py` |
| One request for L1° and L3° | `frontend/src/lib/components/risk/AssetSetComparisonLevels.svelte` |
| Row assembly, no currency parameter | `frontend/src/lib/components/risk/assetSetLevels.ts` |
| Clause ⓪ — why the fan-out was rejected | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/A-contratto-asset-set.md` |
