---
title: "AI Export catalog granularity and composition"
category: concept
date: 2026-08-04
updated: 2026-08-05
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

The released AI Export V1 catalog is a modular composition system with **67 reusable
components**, **40 internal datasets**, **8 public Export Data choices**, and
**11 public Request Analysis choices** across Portfolio, Broker, Asset, and FX.
Analyses request only facts material to the task, components build once per
request, and internal projections remain available for composition without
exposing implementation-level fragmentation in the UI.

The public catalog deliberately presents one general and one detailed data
export per domain. Granular legacy datasets remain internal, and direct requests
for their IDs fail closed.

## Where It Applies

### Public catalog

| Domain | Export Data | Request Analysis |
|---|---:|---:|
| Portfolio | 2 | 4 |
| Broker | 2 | 3 |
| Asset | 2 | 2 |
| FX | 2 | 2 |
| **Total** | **8** | **11** |

`DatasetSpec` selects required/optional components and section order.
`AnalysisSpec` selects required/optional datasets plus instructions, response
contract, and Additional Data recommendations. Required datasets fail closed;
optional datasets are attempted and omitted only when unavailable or
inapplicable. Additional Data is not already in the prompt: it is a suggested
second export.

The public data pairs are:

| Domain | General | Detailed |
|---|---|---|
| Portfolio | `portfolio.overview_and_history` | `portfolio.asset_history` |
| Broker | `broker.overview_and_history` | `broker.asset_history` |
| Asset | `asset.position_and_history` | `asset.market_history` |
| FX | `fx.market_and_exposure` | `fx.market_history` |

### PAC and rebalancing are not aggregate-only

`portfolio.pac_planning` and `portfolio.rebalancing` require
`portfolio.overview_and_history`. The receiving AI therefore gets composition,
positions, cash, performance, flows, income, recorded costs, economic FIFO
summary, provenance and compact per-Asset market context. The optional
`portfolio.asset_history` export adds the denser per-Asset history when needed.

They do not invent budget, targets, risk tolerance, liquidity needs, tax rules
or execution constraints; these remain explicit user inputs.

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

The V1 public reduction removes the old menu collision between Overview, Performance,
Technical Summary, Asset Snapshot, Asset Comparison and Technical. Users choose
only:

- a general cross-domain factual export;
- a detailed historical export;
- one task-specific Analysis.

The backend still composes granular projections internally, but internal
dataset IDs are not public API choices. Data exports contain facts only;
Analyses add an objective, response contract, user questions and recommendations
for a second public export.

## Verification

Final candidate `20260804T224056.073291Z` generated all **114/114** public
variants with zero failure/skip and 36 retained prompts. Comparison against
baseline `20260804T214400.268752Z` found 114/114 stable keys unchanged, with
zero character, byte, composition, event or state deltas. Secret scan,
UI/probe equivalence and primary/source database immutability passed.

Task Adequacy covers all 66 Analysis variants (11 choices × 2 periods × 3
details): 54 invariant reviews were carried forward and the 12 fiscal variants
were reread; all 66 are `OPTIMAL`.

## Related pages

- [[decisions/ai-export-versioned-snapshot-boundary]]
- [[decisions/ai-export-prompt-catalog]]
- [[decisions/ai-export-technical-series-and-density-contract]]
- [[entities/ai-export-snapshot-service]]
- [[sources/phase00-ai-export-backend-snapshot]]

## Source files

| Role | Path |
|------|------|
| Discovery/report | `LibreFolio_developer_journal/Release_2/phases/01_signalMigration/02_aiExport/report-phase00AiExportUiPromptCatalogExplainedV1.md` |
| Final audit and closure | `LibreFolio_developer_journal/Release_2/phases/01_signalMigration/02_aiExport/report-phase00AiExportFinalAuditAndClosureV1.md` |
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
