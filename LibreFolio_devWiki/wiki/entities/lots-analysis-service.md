---
title: "Lots Analysis Service"
category: entity
type: service
tags: [backend, fifo, lots, orchestration, fx]
related:
  - entities/fifo-lot-engine
  - entities/portfolio-engine
  - decisions/fifo-v4-engine-architecture
  - decisions/fifo-v4-gross-net-status-model
  - problems/fifo-income-silently-dropped-after-full-close
  - concepts/fifo-lot-tracking
---

# Lots Analysis Service

## Role

Orchestration layer between the API and [[entities/fifo-lot-engine]]. Owns FX resolution, builds the engine's
economic input objects, invokes the engine, and maps its output back into the public API response (fee/tax/
income breakdowns, net summary and history series, status). As of v4 it is **no longer the allocator of
record** for income — that logic moved into the engine itself (see [[decisions/fifo-v4-engine-architecture]]).

## Location

`backend/app/services/lots_analysis_service.py` (~1980 lines)

## Key Interfaces

- Prepares FX rates and target-currency amounts for trades/income before building `EconomicEvent`s.
- Calls `FifoLotEngine.run(...)` and receives quantitative + economic results in one pass.
- Maps engine `EconomicAllocationGroup`/`TargetOperationAllocation`/`EconomicLotAllocation` audit objects into
  the public DTO's inline 3-level audit shape (`backend/app/schemas/portfolio.py`).
- Computes net summary and net history series from the engine's per-lot economic accumulators.
- Maps internal `analysis_status` (`COMPLETE|DEGRADED|FAILED`) to the public `calculation_status` field.

## Design Notes

- **`_allocate_asset_income` was removed** — this was the pre-v4 service-level dividend/interest allocator
  (asset-wide, income-date-based, no broker scoping). It could not coexist with the engine's own D-1/
  broker-scoped allocation without risking double counting or split truth, so it was deleted as part of the
  atomic v4 merge, not deprecated gradually. See [[decisions/fifo-v4-engine-architecture]].
- The old allocator had a silent-drop bug on top of being superseded: it simply skipped an income event when
  no lot was open, losing that income with no trace. See
  [[problems/fifo-income-silently-dropped-after-full-close]] for the specific behavior fixed.
- Still the right layer for FX resolution — the engine deliberately stays FX-mechanism-agnostic and pure; this
  service is where `_FxRateResolver` actually gets called.

## Source files

| Role | Path |
|------|------|
| Service | `backend/app/services/lots_analysis_service.py` |
| Engine it orchestrates | `backend/app/services/fifo_lot_engine.py` |
| Public DTO | `backend/app/schemas/portfolio.py` |
| Service-level tests | `backend/test_scripts/test_services/test_financial/test_lots_analysis_service.py` |
| Developer docs | `mkdocs_src/docs/developer/backend/transactions/lots_analysis_service.md` |
