---
title: "The contracts K1–K9 between the first-round Risk streams, and where each one lives in today's code"
category: concept
date: 2026-10-12
tags: [risk, contracts, coordination, workstreams, backend, frontend, release-1.2]
related:
  - concepts/risk-binding-decisions
  - features/F-110
  - features/F-111
  - features/F-112
  - sources/phase00-risk-integration-2026-09
---

# Concept: the K contracts of the first Risk round

## Definition

The first implementation round of folder 02 (2026-09-17/18) split the work into eleven streams (A, B, C, D, E, F, G,
H, I, J, N), run as parallel mandates. Where one stream's output was another's input, the two agreed a **contract**
first, K1–K9 (`implementation/contracts/`), so neither waited for the other. Round 1 was later reviewed and partly
redone by `implementation_2/` (whose `PRIMITIVE.md` replaces K5), but the contracts still say where each shared shape
lives.

| Contract | What it fixes | Where it lives today |
|----------|---------------|----------------------|
| K1, A→E | The underwater series and the histogram bins | `services/risk/metrics.py` (`_MAX_HISTOGRAM_BINS`), `schemas/risk.py` |
| K2, B→G | `primaryAssetType` returns the type held, not the container (D85) | `utils/assetTypes.ts`, `charts/allocationHierarchy.ts` |
| K3, B→E,F | The benchmark selector in sections, reusing `AssetSelect` (D50, D60, D73) | `features/risk/BenchmarkSelect.svelte` |
| K4, C→E,F,H | An optional field of `PortfolioRiskScope` slices the portfolio by asset | `schemas/risk.py` (`sliced_asset_ids`) |
| K5, D→E,F | Display primitives under `ui/display` (history; replaced by round 2's `PRIMITIVE.md`) | `components/ui/display/KpiMetricBar.svelte` |
| K6, H→E | The simulation's mode and its cone as two separate axes | `risk_plugins/simulation/plugin.py`, `levels/SimulationProvenance.svelte` |
| K7, I→E,F,H | Documentation slugs frozen first: a wrong slug fails only in front of the user | `components/ui/DocsLink.svelte` |
| K8, N→E,I | KPIs acquired for L1 and L2 (effective number of assets, diversification ratio) | `risk_plugins/historical_kpi/plugin.py`, `levels/L2Diversification.svelte` |
| K9, E→F | The historical replay apart from the hypothetical shock — superseded by D372/D376 | `features/risk/AssetSetReplaySection.svelte` |

The contract files still mark K6 and K7 «agreed, not yet implemented»: the code above shows both delivered.

## Source files

| Role | Path |
|------|------|
| Contracts index | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation/contracts/README.md` |
| K1 home | `backend/app/services/risk/metrics.py` |
| K4 home | `backend/app/schemas/risk.py` |
| K7 home | `frontend/src/lib/components/ui/DocsLink.svelte` |
