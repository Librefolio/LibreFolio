---
title: "ASSET_SET risk scope has no primary series, so single-series analytics cannot serve it"
category: problem
status: open
date: 2026-09-05
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

## Source files

| Role | Path |
|------|------|
| Builds the scope; empty values for an asset set | `backend/app/services/risk/service.py` |
| Supports ASSET_SET; consumes many series | `backend/app/services/risk_plugins/correlation.py` |
| Supports ASSET_SET; returns no amount without weights | `backend/app/services/risk_plugins/stress.py` |
| Scope and payload schemas | `backend/app/schemas/risk.py` |
