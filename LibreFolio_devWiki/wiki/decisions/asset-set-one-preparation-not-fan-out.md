---
title: "The Lab asks one ASSET_SET request, not one request per asset: comparable points need one preparation on one calendar"
category: decision
status: resolved
date: 2026-09-21
tags: [risk, lab, asset-set, scope, calendar, correctness, backend, frontend, release-1.2]
related:
  - features/F-112
  - features/F-110
  - decisions/lab-eligibility-from-risk-engine
  - problems/asset-set-scope-has-no-primary-series
  - concepts/risk-binding-decisions
  - sources/phase00-risk-integration-2026-09
---

# Decision: one preparation for the whole selection

## Context

The Lab of Asset Global ([[features/F-112]]) compares a selection of assets on its reduced levels L1° and L3°. The
first implementation fanned out: one `asset`-scope request per asset. Each was prepared on its own joint calendar, so
the points plotted together came from different windows — enough to break `σ_b = ρ·σ_p/β` by about a fifth: a chart
that is wrong while looking right.

## Decision

The asset-set contract of the second round (`implementation_2/A-contratto-asset-set.md`, ratified by the coordinator on
2026-09-21), clause ⓪: **one request, one preparation**, so every asset shares one calendar. In its words: «Il fan-out
non era caro: era sbagliato.» — a choice made for cost reopens as soon as the cost changes; one made for correctness
does not.

`d3afb92b6` («feat(risk): serve the weightless ASSET_SET scope with a per-asset analytic family»): `AssetSetRiskScope`
(`kind=asset_set`, 1–100 unique asset ids, no weights) is served by a family of per-asset plugins —
`asset_set_kpi`, `asset_set_risk_return`, `asset_set_var`, `asset_set_drawdown`, `asset_set_comparison` — each declaring
`supported_scopes=(ASSET_SET,)`.

## Consequences

- The contract's table of what supported `ASSET_SET` (2 of 9 plugins when written) is overtaken: the family above
  replaces, rather than extends, the portfolio plugins for this scope.
- A selection has no primary series, which the eligibility and the benchmark rules must handle —
  [[problems/asset-set-scope-has-no-primary-series]], [[decisions/lab-eligibility-from-risk-engine]].

## Source files

| Role | Path |
|------|------|
| `AssetSetRiskScope` | `backend/app/schemas/risk.py` |
| One of the asset-set plugins | `backend/app/services/risk_plugins/asset_set_kpi/plugin.py` |
| The Lab's L1° and L3° | `frontend/src/lib/features/risk/AssetSetComparisonLevels.svelte` |
| Journal (the contract) | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/A-contratto-asset-set.md` |
