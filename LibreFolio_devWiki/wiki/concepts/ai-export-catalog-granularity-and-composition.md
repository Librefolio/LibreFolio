---
title: "AI Export catalog granularity and composition"
category: concept
date: 2026-08-04
mkdocs: "developer/architecture/patterns/ai_export_composition.md"
tags: [ai-export, composition, datasets, analyses, ux, granularity, prices, all-data]
related:
  - decisions/ai-export-versioned-snapshot-boundary
  - decisions/ai-export-prompt-catalog
  - decisions/ai-export-technical-series-and-density-contract
  - entities/ai-export-snapshot-service
  - sources/phase00-ai-export-backend-snapshot
---

# Concept: AI Export catalog granularity and composition

## Definition

The current AI Export catalog is a modular composition system with **65 reusable
components**, **32 public Export Data datasets**, and **17 Request Analysis
choices** across Portfolio, Broker, Asset, and FX. This decomposition is useful
internally: analyses request only the facts material to their task, components
build once per request, and focused projections avoid forcing complete technical
series into every prompt.

The same decomposition is harder to understand when exposed almost directly in
the UI. Users must currently infer whether a choice is aggregate, per Asset,
current-state, historical, position-accounting, market-context, or evidence-only.
The main UX issue is therefore not missing per-Asset data in PAC or rebalancing;
it is missing visible granularity and data-shape cues.

## Where It Applies

### Public catalog

| Domain | Export Data | Request Analysis |
|---|---:|---:|
| Portfolio | 10 | 8 |
| Broker | 10 | 4 |
| Asset | 6 | 2 |
| FX | 6 | 3 |
| **Total** | **32** | **17** |

`DatasetSpec` selects required/optional components and section order.
`AnalysisSpec` selects required/optional datasets plus instructions, response
contract, and Additional Data recommendations. Required datasets fail closed;
optional datasets are attempted and omitted only when unavailable or
inapplicable. Additional Data is not already in the prompt: it is a suggested
second export.

### PAC and rebalancing are not aggregate-only

`portfolio.pac_planning` always composes `portfolio.overview` and
`portfolio.performance_flows`, and optionally composes
`portfolio.asset_snapshot` and `portfolio.drawdown_context`. The receiving AI
therefore gets per-position rows with Asset, Broker, quantity, position unit
price, current value, WAC, P&L, and weight. When the focused optional projection
is available, it also gets per-Asset observed market price, recent returns,
extrema, trend, momentum, volatility, events, and compact Asset Drawdown context.

`portfolio.rebalancing` always composes `portfolio.overview`, and optionally
composes `portfolio.performance_flows`, `portfolio.asset_comparison`, and
`portfolio.drawdown_context`. It likewise receives per-position accounting rows
and, when available, uniform per-Asset market context. It does not automatically
receive targets, full technical history, FIFO lots, or future tax/execution
assumptions; those are user inputs or follow-up exports.

## Three Distinct Price Semantics

The word “price” currently covers three different facts:

1. **Position unit price** — the valuation price used for a `(Broker, Asset)`
   position, normally represented in the target valuation currency and exported
   by Overview alongside quantity, value, WAC, P&L, and weight.
2. **Observed market price** — the latest dated native-market observation for an
   Asset, with market and technical context, exported by Asset Snapshot,
   Asset Comparison, and related focused contexts.
3. **Price history** — the bucketed time series exported by complete Technical
   datasets; its density changes with Compact, Standard, and Full.

These values can be related without being interchangeable. UI labels and future
documentation should state which one is present instead of using “price” alone.

## `all_data` Semantics

`*.all_data` is not the union of every visible menu choice. It is the deduplicated
union of each domain's **canonical complete source datasets**:

| `all_data` | Canonical source datasets |
|---|---|
| Portfolio | Overview + Performance/Flows + Technical + FIFO |
| Broker | Overview + Performance/Flows + Technical + FIFO |
| Asset | Overview + Position Performance + Market Technical |
| FX | Overview + Market Technical + Direct Exposure |

Focused summaries, contexts, comparisons, and task-specific evidence are
deliberately excluded because they project facts already represented by the
complete sources. Including both would duplicate rows and semantics. The precise
meaning is therefore “all canonical complete data,” not “every option shown in
the UI.”

## UX Interpretation

The most easily confused choices are:

| Choice | Granularity | Per-Asset price | Per-Asset Drawdown | History |
|---|---|:---:|:---:|:---:|
| Technical Summary | aggregate | no | no | no |
| Asset Snapshot | per Asset | observed current | yes | no |
| Asset Comparison | per Asset | observed current | no | no |
| Technical | Asset × Signal × bucket/event | current + bucketed | no | yes |

Two other collisions recur:

- **Overview vs Performance** — Overview is current state and position
  valuation; Performance is economic change and contributor rows over a period.
- **Context dataset vs similarly named Analysis** — a `*.context` choice exports
  facts, while an Analysis adds a task, response structure, required/optional
  dataset composition, and user notes.

No granularity badges currently make these distinctions explicit. Candidate
presentation cues are `Aggregated`, `Per Asset`, `Current price`, `Price
history`, and `Lots`, together with grouping into Base, Asset comparison,
specific evidence, and complete/advanced choices. These are findings for future
product discussion, not an approved UI change.

## Potential Contract Gaps

The 4 August review identified two concrete mismatches to keep visible:

1. **Broker Technical has no raw price-history component.**
   `broker.technical` contains coverage, indicator history, events, and breadth,
   but not a `broker.technical_prices`/raw OHLC section comparable to Portfolio,
   Asset, or FX complete technical exports. Current price remains available from
   Broker Overview or Asset Comparison.
2. **Asset Trend promises Drawdown without composing it.**
   The Italian UI description for `asset.trend_analysis` says it explains
   “trend, momentum, volatilità, drawdown ed eventi,” but the current
   `AnalysisSpec` requires only `asset.overview` and
   `asset.market_technical`; `asset.drawdown_context` is not included. The
   instruction and response contract likewise cover trend/momentum/volatility
   and events, not a supplied Drawdown section.

Neither gap was changed by this discovery/report.

## Verification

The report explains all **49/49 public choices** against the current runtime
catalog, payload models, instructions, response contracts, and Italian labels.
Five representative Portfolio prompts were also generated and read in full in
`real_prompt_probe/20260804T085052.052297Z`:

- Portfolio Overview;
- Portfolio Asset Snapshot;
- Portfolio Asset Comparison;
- PAC Planning;
- Portfolio Rebalancing.

The run passed **5/5**, with zero failures and zero public-output violations,
UI/probe equivalence, a passed secret scan, and unchanged source and production
databases. The report deliberately follows the live `_PORTFOLIO_ANALYSES`,
`_BROKER_ANALYSES`, `_ASSET_ANALYSES`, and `_FX_ANALYSES` declarations rather
than the stale historical mapping in the module docstring.

## Related pages

- [[decisions/ai-export-versioned-snapshot-boundary]]
- [[decisions/ai-export-prompt-catalog]]
- [[decisions/ai-export-technical-series-and-density-contract]]
- [[entities/ai-export-snapshot-service]]
- [[sources/phase00-ai-export-backend-snapshot]]

## Source files

| Role | Path |
|------|------|
| Discovery/report | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/report-phase00AiExportUiPromptCatalogExplainedV1.md` |
| Developer composition overview | `mkdocs_src/docs/developer/architecture/patterns/ai_export_composition.md` |
| Dataset catalog and `all_data` unions | `backend/app/services/ai_export/datasets/catalog.py`, `backend/app/services/ai_export/datasets/spec.py` |
| Analysis composition | `backend/app/services/ai_export/analyses/catalog.py`, `backend/app/services/ai_export/analyses/spec.py` |
| Component catalog | `backend/app/services/ai_export/components/catalog.py` |
| Portfolio/Broker component builders | `backend/app/services/ai_export/components/portfolio_broker_registry.py` |
| Asset/FX component builders | `backend/app/services/ai_export/components/asset_fx_registry.py` |
| Analysis instructions | `frontend/src/lib/features/ai-export/templates/sharedInstructions.ts` |
| Response contracts | `frontend/src/lib/features/ai-export/templates/responseContracts.ts` |
| Current Italian UI labels | `frontend/src/lib/i18n/it.json` |
| Real-prompt probe implementation | `backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py` |
