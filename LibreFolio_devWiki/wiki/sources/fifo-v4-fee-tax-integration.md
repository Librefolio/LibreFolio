---
title: "FIFO Engine v4 — FEE/TAX Integration"
category: source
source_type: plan
date_ingested: 2026-07-22
original_path: LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/
tags: [backend, fifo, transactions, calculations, fee, tax, dividend, cost-basis]
related: [decisions/fifo-v4-income-eligibility-d1, decisions/fifo-v4-cost-allocation-ladder, decisions/fifo-v4-engine-architecture, decisions/fifo-v4-gross-net-status-model, decisions/fifo-v4-validation-and-scope, entities/fifo-lot-engine, entities/lots-analysis-service, concepts/d1-income-eligibility-window, concepts/deterministic-cost-matching-ladder, concepts/asset-orphan-vs-portfolio-level-cost, concepts/gross-net-dual-reporting, problems/datatable-net-columns-hidden-override-model, problems/transaction-update-bypassed-sign-validation, problems/fifo-income-silently-dropped-after-full-close, decisions/fifo-runtime-decision, concepts/fifo-lot-tracking, entities/portfolio-engine, features/F-056]
---

# Source: FIFO Engine v4 — FEE/TAX Integration

## Summary

This plan chain closed a gap between FIFO lot analysis (quantity/custody replay, implemented in v3) and the real
economic life of an asset: dividends, interest, fees and taxes were previously handled outside the FIFO domain
(split between an ad-hoc income allocator in `LotsAnalysisService` and the Portfolio Engine), with no per-lot
cost attribution. The implemented v4/v5 design moved asset-linked income/FEE/TAX allocation into the FIFO engine
itself through one canonical flow: quantitative replay first, then deterministic economic pooling/allocation,
then combined status classification. Income entitlement was tightened to **D-1** (day before the income date)
and scoped to the **paying broker**, with transfer-aware custody rules. Asset-linked FEE/TAX now flow through
distinct deterministic matching ladders and become per-lot `allocated_fees` / `allocated_taxes`, feeding
**net** metrics that are always gross minus allocated costs — gross formulas and `original_cost` are never
mutated. The API/DTO/frontend were extended with net columns, inline 3-level economic audit, orphan aggregates,
and a 3-state analysis status. The FIFO-side of this work is implemented and verified; Portfolio-Engine-side
cross-engine reconciliation was deliberately deferred as a separate, higher-risk piece of work.

This is the plan behind the `mkdocs_src/docs/financial-theory/` doc updates (fifo-lot-analysis.en.md "Income
Allocation" D-1 rewrite + new "Costs & Net Metrics" section; fee.en.md new attribution admonition) translated
into IT/FR/ES in the same devWiki session, immediately before this ingest.

## Key Takeaways

- **D-1 income eligibility, broker-scoped**: `EligibleQuantity_i(D) = OpenQuantity_i(D-1)`, matched within the
  paying broker only (with asymmetric From/To transfer rules) — replaces the old "all LONG lots open on the
  income date itself, across all brokers" behavior. See [[decisions/fifo-v4-income-eligibility-d1]].
- **Distinct deterministic cost ladders for FEE vs TAX** (FEE is trade-centric; TAX is income-first) route
  asset-linked costs to lots, with same-day BUY+SELL pools split by value-weight and orphan as the deterministic
  fallback (never adjacent-day D+1 matching). See [[decisions/fifo-v4-cost-allocation-ladder]].
- **Assetless costs (`asset_id = null`) never enter FIFO** — they stay portfolio/broker-level, handled by the
  Portfolio Engine. See [[concepts/asset-orphan-vs-portfolio-level-cost]].
- **Gross metrics are untouched**; net metrics are additive (`gross - allocated_fees - allocated_taxes`), with a
  deliberate asymmetry: per-lot history net P&L is capital-only, while summary `net_total_pnl`/`net_total_return`
  are income-inclusive. See [[decisions/fifo-v4-gross-net-status-model]], [[concepts/gross-net-dual-reporting]].
- **One canonical engine path**: `FifoLotEngine.run()` now owns quantitative + economic allocation; the old
  service-level income allocator (`LotsAnalysisService._allocate_asset_income`) was removed, not left coexisting.
  See [[entities/fifo-lot-engine]], [[entities/lots-analysis-service]].
- **Portfolio Engine reconciliation deliberately deferred** — no pre-share absolute accumulators / cross-engine
  conservation check landed this round; flagged as future work, not a regression. See [[entities/portfolio-engine]].
- Real bugs found and fixed along the way: a `DataTable.svelte` visibility-snapshot bug hid net columns despite
  real costs ([[problems/datatable-net-columns-hidden-override-model]]); transaction UPDATE could persist a
  positive FEE/TAX where CREATE couldn't ([[problems/transaction-update-bypassed-sign-validation]]); the old
  income allocator silently dropped income when no lot was open ([[problems/fifo-income-silently-dropped-after-full-close]]).
- The wiki's pre-existing [[decisions/fifo-runtime-decision]] and [[features/F-056]] pages referenced
  `transaction_service.py` as "the FIFO engine" — verified stale (FIFO logic now lives in `fifo_lot_engine.py` /
  `lots_analysis_service.py`); corrected as part of this ingest.

## Iteration history (why so many drafts)

The directory contains 6 feasibility-analysis drafts and 4 high-level-analysis drafts before settling on the
`-v5` / `-v4.1` versions actually implemented. The rejected intermediate approaches are recorded inline in each
decision page's "Options Considered" section rather than as separate pages — notable pivots: adjacent-day D+1
matching → previous-day-only; one unified FEE+TAX ladder → separate ladders; partially-orphan TAX pools →
all-or-nothing pool; FX resolver inside the engine (Option C) → FX resolved in the service, engine stays pure
(Option B, native+target events); optional on-request cost audit → always-inline 3-level audit.

## Wiki Pages Updated

- [[decisions/fifo-v4-income-eligibility-d1]] — new
- [[decisions/fifo-v4-cost-allocation-ladder]] — new
- [[decisions/fifo-v4-engine-architecture]] — new
- [[decisions/fifo-v4-gross-net-status-model]] — new
- [[decisions/fifo-v4-validation-and-scope]] — new
- [[entities/fifo-lot-engine]] — new
- [[entities/lots-analysis-service]] — new
- [[entities/portfolio-engine]] — updated (deferred reconciliation note)
- [[concepts/d1-income-eligibility-window]] — new
- [[concepts/deterministic-cost-matching-ladder]] — new
- [[concepts/asset-orphan-vs-portfolio-level-cost]] — new
- [[concepts/gross-net-dual-reporting]] — new
- [[concepts/fifo-lot-tracking]] — updated (v4 evolution note)
- [[problems/datatable-net-columns-hidden-override-model]] — new
- [[problems/transaction-update-bypassed-sign-validation]] — new
- [[problems/fifo-income-silently-dropped-after-full-close]] — new
- [[decisions/fifo-runtime-decision]] — updated (fixed stale file reference)
- [[features/F-056]] — updated (fixed stale file reference, mkdocs column)

## Source files

| Role | Path |
|------|------|
| Post-implementation review (authoritative) | `RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/post-implementation-review-v5.md` |
| Implementation recap (authoritative) | `RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/implementation-recap-v5.md` |
| Review checklist (authoritative) | `RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/review-checklist-v5.md` |
| High-level design (authoritative) | `RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/hig-level-analysis-v5.md` |
| Feasibility / final pivots (authoritative) | `RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/feasibility-analysis-v4.1.md` |
| Detailed executable plan (authoritative) | `RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/implementation-plan-v5.md` |
| Superseded feasibility drafts | `RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/feasibility-analysis{,-v2,-v3,-v4,-v4-review}.md` |
| Superseded high-level drafts | `RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/{high-level-analysis,high-level-analysis-v2,hig-level-analysis-v3}.md` |
| Parent background (partly superseded, see above) | `RoadmapV4_UI/fifo-engine/{REPORT-fifo-lots-transfer-mismatch,fifo-engine-current-state,fifo-segment-model-analysis,portfolio-engine-cache-analysis}.md` |
| mkdocs docs updated as a direct result | `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.en.md`, `mkdocs_src/docs/financial-theory/instruments/transaction-types/fee.en.md` (+ it/fr/es translations) |
