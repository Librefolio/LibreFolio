---
title: "FIFO v4 engine architecture: one canonical path, native+target events, inline audit"
category: decision
status: resolved
date: 2026-07-22
tags: [backend, fifo, architecture, fx, audit]
related: [fifo-v4-cost-allocation-ladder, fifo-v4-income-eligibility-d1, entities/fifo-lot-engine, entities/lots-analysis-service]
---

# Decision: FIFO v4 engine architecture — one canonical path, native+target events, inline audit

## Context
Before v4, quantitative lot replay lived in the engine, income allocation lived in the service
(`LotsAnalysisService._allocate_asset_income`), and costs lived only in the Portfolio Engine. This split-truth
setup also had no answer for cross-currency allocation or provenance/audit of *why* a given lot got a given
fee/income share.

## Options Considered
1. **Engine architecture — staged coexistence vs one canonical path**: keep the old and new income/economic
   code paths running side by side during a transition, or merge atomically into a single public
   `FifoLotEngine.run(...)` entry point. **Chosen: atomic merge**, one canonical path — the old allocator had to
   be deleted once engine-side income landed, not left dormant, to avoid double counting or split truth.
2. **Currency/event model** — three options were weighed:
   - **A. Target-only events**: engine works purely in the user's target currency; FX resolved before the
     engine sees anything. Rejected: loses native-currency audit trail.
   - **B. Native + target amounts on every `EconomicEvent`** — engine receives both, compares in target
     currency but can still report native amounts. **CHOSEN.**
   - **C. FX resolver injected into the engine** (pass `_FxRateResolver` in): rejected — pulls async/DB/FX I/O
     into what should be a pure, synchronously-testable engine.
3. **Where does the canonical multi-currency total live?** Sum each event's already-converted target amount, or
   convert the native pool total once. **Chosen: convert once** — `TargetPool = FXConvert(NativePool, ...)`,
   with per-event target values used only for weighting/audit, never re-summed as the source of truth. This
   avoids a second, driftable source of the "total" and keeps conservation checks simple (native and target
   each individually conserve).
4. **Audit granularity** — v3 had an optional, flat `COST_ALLOCATIONS` payload, requested separately; a v4
   review found even a non-optional flat group structure insufficient (can't represent a mixed BUY+SELL pool,
   or the same lot appearing once as an OPENING allocation and once as a CLOSURE allocation in the same pool).
   **Chosen: always-inline, 3-level hierarchical audit** — `EconomicAllocationGroup → TargetOperationAllocation
   → EconomicLotAllocation`, shipped inline in `LotsAnalysisResponse`, not a separate on-request endpoint.

## Decision
- Single public engine entry point (`FifoLotEngine.run(...)`) owns quantitative replay **and** economic
  pooling/allocation; no parallel legacy income/cost path is allowed to coexist after the merge.
- Every `EconomicEvent` carries both native and target-currency amounts (Option B); the engine is
  "target-value aware" for comparisons but "FX-mechanism agnostic" — it never resolves FX itself, the service
  layer does, using the existing `_FxRateResolver`.
- The native pool is canonical; the target total is derived by converting the native pool exactly once per
  pool; per-event target amounts exist only for intra-pool weighting and audit display.
- Every allocation (cost or income) is recorded as a 3-level inline audit trail, always present in the API
  response, never an optional/secondary payload.

## Consequences
- `LotsAnalysisService` changed role: it no longer allocates income itself — it prepares FX/target amounts,
  builds the economic events, calls the engine, then maps the engine's economic groups back into the public
  DTO (fee/tax/income outputs, net summary/history, status).
- Response payload size grows (full 3-level audit is always present), but every euro/dollar of fee, tax or
  income is traceable back to the specific pool and operation that produced it — no extra endpoint needed to
  get that provenance.
- The engine stays pure and unit-testable (no I/O), at the cost of the service having to pre-resolve FX and
  build richer input objects (`FifoInputTransaction` gained `target_amount`/`target_currency`).
- Both native and target conservation are checked independently as a correctness invariant.

## Related
- [[entities/fifo-lot-engine]]
- [[entities/lots-analysis-service]]
- [[fifo-v4-cost-allocation-ladder]]
- [[fifo-v4-income-eligibility-d1]]
- [[sources/fifo-v4-fee-tax-integration]]

## Source files

| Role | Path |
|------|------|
| Final architecture | `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/hig-level-analysis-v5.md` §2.3-§5, §7.2, §10.2, §20-§21 |
| Currency-model pivot (Option B) | `.../v4-fee_tax_integration/feasibility-analysis-v4.1.md` §1.2-§1.3, §2.1-§2.3 |
| Rejected Option C critique | `.../v4-fee_tax_integration/feasibility-analysis-v4-review.md` §10 |
| Rejected flat-audit critique | `.../v4-fee_tax_integration/feasibility-analysis-v4-review.md` C1/§9 |
| Executable plan | `.../v4-fee_tax_integration/implementation-plan-v5.md` §1.1, §3, §7.3-§7.4, Fase 2-8 |
| Engine | `backend/app/services/fifo_lot_engine.py` |
| Orchestration service | `backend/app/services/lots_analysis_service.py` |
| Public DTO | `backend/app/schemas/portfolio.py` |
