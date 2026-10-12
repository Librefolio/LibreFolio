---
title: "Phase 0 / 41 — broker P&L lines without jumps at transfers, then F: one native-cash ledger"
category: source
source_type: plan
date_ingested: 2026-10-12
original_path: LibreFolio_developer_journal/Release_2/Phase_0/41_brokerPnlFlows/plan-phase00BrokerPnlFlows.prompt.md
tags: [phase0, release2, workstream-i, lot-41, portfolio-engine, broker-pnl, internal-transfers, broker-cards, native-cash, fx, ai-export]
related:
  - decisions/native-cash-daily-revaluation
  - entities/native-cash
  - problems/foreign-cash-never-revalued
  - problems/dirty-days-ignore-fx-only-moves
  - decisions/portfolio-pnl-series-contracts
  - decisions/broker-card-aggregation-no-n-plus-one
  - concepts/3-pool-cash-model
  - entities/portfolio-engine
  - entities/portfolio-service
  - sources/phase00-performance-charts-2026-09
---

# Source: Phase 0 / 41 — broker P&L lines, the cards, and native cash

## Summary

The plan of workstream I's lot 41 (1 479 lines, 2026-10-10 → 2026-10-12, still in `Phase_0/` at `5d0585595`). It
started from a developer report — «non mi torna che il tratteggiato mostri quelle cifre, dovrebbe mostrare i p&l di
quei broker, e quelle cifre sono liquidità pura» ("the dashed line should show those brokers' P&L, and those figures
are plain cash") — and fixed the per-broker P&L lines, which jumped by −X / +X whenever money or securities moved
between two of the user's brokers. Its inventory then found that four loops recomputed cash with their own rules and
that foreign cash was never revalued; the developer chose to fix both in 1.2. The lot shipped in three deliveries:
the engine (train 32), the broker cards read from the engine (step H, train 35) and F, the native-cash ledger with its
«FX on cash» row (train 42).

## Key takeaways

- **Internal transfers are zero-sum capital flows between broker lines** (decisions D1–D6, checkpoint 1: `883681766`,
  docs `3801cf93e`, merge `46272c3f0`). On the arrival day a `linked_internal` pair moves X — what enters the
  receiver's NAV, securities at market value — from the sender's capital to the receiver's
  (`_internal_transfer_flows()`); in filtered views a leg whose partner is outside, or deleted, is capital at market
  value (`_transfer_leg_capital()`); orphaned cash legs become external flows (D5); ADJUSTMENT pairs keep their
  capital at cost (D4, backlog B6). Recorded in [[decisions/portfolio-pnl-series-contracts]] (G1a).
- **The broker cards read the same capital (step H**, `801b4a168`, merge `8a546c046`): `capital_contribution` and
  `in_transit_contribution` from the engine's per-broker slice; the service's own capital mirror is gone.
  [[decisions/broker-card-aggregation-no-n-plus-one]].
- **F — one native-cash ledger, foreign cash revalued every day**, k2 for the pools, policy (a) for a missing rate,
  the «FX on cash» row in the minimal form, F-AI (a) now and (b) after 1.2 with a typed code:
  [[decisions/native-cash-daily-revaluation]], [[entities/native-cash]], [[problems/foreign-cash-never-revalued]].
  Commits `36b181836`, `aa6b6077a`, `a5f41f60c`, `c04e44ff5`, `9a0d9280c` (frontend), `a4332b25b` (docs); merge
  `15cbff6fb`.
- **Method worth reusing**: the red tests and a byte-for-byte golden of the report-currency guard were written
  **before** the code (F-0) and the golden was never regenerated; a before/after report on the mock database
  isolated F (`git archive` of the target as «before»), with determinism checked by a second run.
- **The plan corrected itself twice**: the hypothesis that the row would stay inside `period_other_result` for AI
  Export was half wrong (the broker export already lists it by name); and the probe cost was wrong — it runs on the
  lane's synthetic data, not on production data.
- **Left after 1.2** (backlog section I): B1, B2, B3, B5–B8, B10, the securities half of B11
  ([[problems/dirty-days-ignore-fx-only-moves]]), the quantities of B12, B15, B17–B19; B9 went to T (U3); F-AI (b) is
  a decision of the developer still to enter the backlog.
- **Found on the way and handed over**: `reconciled` flipping on a 1e-24 residual in AI Export (C-53,
  [[problems/ai-export-reconciled-false-on-rounding-dust]]); F-5's translation debt (75 errors, 75 warnings on six
  English pages) to workstream M, cleared in its batch 18.

## Wiki pages created or updated

- Created: [[decisions/native-cash-daily-revaluation]], [[entities/native-cash]],
  [[problems/foreign-cash-never-revalued]], [[problems/dirty-days-ignore-fx-only-moves]].
- Updated: [[decisions/portfolio-pnl-series-contracts]] (G1a: the text the plan proposed in §13, checked on the code),
  [[decisions/broker-card-aggregation-no-n-plus-one]], [[concepts/3-pool-cash-model]], [[entities/portfolio-engine]],
  [[concepts/pre-frame-frame-separation]], [[entities/portfolio-service]],
  [[problems/ai-export-cash-fx-valuation-basis-mismatch]], [[features/F-054]], [[features/F-055]],
  [[domains/calculations]].

## Not in the plan, recorded from the coordinator

- The developer's decision on F-AI: (a) now, (b) after 1.2 with a typed code (2026-10-12).
- The confirmation on real data: after importing his Scalable Capital reports, the per-broker P&L chart looked «come
  me lo aspettavo» (2026-10-12).

## Source files

| Role | Path |
|------|------|
| The plan (§0–§17) | `LibreFolio_developer_journal/Release_2/Phase_0/41_brokerPnlFlows/plan-phase00BrokerPnlFlows.prompt.md` |
| Backlog section I | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
| Native cash | `backend/app/services/financial_math/native_cash.py` |
| Internal flows, transfer legs, revaluation | `backend/app/services/financial_math/portfolio/daily_state.py` |
| Cards, histories, contributions | `backend/app/services/portfolio_service.py` |
| Internal-flow tests and aggregate guard | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_broker_internal_flows.py` |
| Report-currency guard | `backend/test_scripts/test_services/test_financial/test_native_cash_guard.py` |
| Theory — internal transfers in the broker lines | `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.en.md` |
