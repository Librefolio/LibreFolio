---
title: "Phase 0 / 30 — one average cost (issue #32) and validated global settings"
category: source
source_type: plan
date_ingested: 2026-10-09
original_path: LibreFolio_developer_journal/Release_2/phases/30_wacUnification/
tags: [phase0, release2, wac, average-cost, financial-math, issue-32, settings, validation, workstream-p]
related:
  - decisions/financial-math-single-average-cost
  - problems/zero-purchase-cost-foreign-asset-paid-in-report-currency
  - problems/global-settings-bulk-saved-unvalidated-values
  - features/F-097
  - entities/portfolio-engine
  - entities/portfolio-service
  - entities/lots-analysis-service
---

# Source: Phase 0 / 30 — WAC unification and settings bulk validation

## Summary

Two plans of workstream P, archived on 2026-10-09. The main one answered issue #32 (a foreign asset bought with a
zero cost in the report currency) not with a patch but with **one average-cost function**, `compute_average_costs()`,
in a new `backend/app/services/financial_math/` layer, used by the engine, the WAC facade, the lots analysis and the
broker summary (P0–P12, `de252a38a`, 2026-10-07). The second makes the global settings bulk write validate every
value and commit all or nothing (`84d9e3360`, 2026-10-09). The #32 work was filed in the wiki on 2026-10-07, while it
landed; this page indexes it and adds what was not filed then.

## Key takeaways

- The decision, its rejected alternatives and the behaviour changes: [[decisions/financial-math-single-average-cost]].
- The bug and its same-root twins: [[problems/zero-purchase-cost-foreign-asset-paid-in-report-currency]].
- Pages realigned on 2026-10-07 (see the two "Workstream P" entries in `log.md`): [[features/F-097]],
  [[decisions/wac-target-currency-last-acquisition]], [[entities/portfolio-engine]], [[entities/portfolio-service]],
  [[entities/lots-analysis-service]], [[concepts/inline-wac-computation]], [[concepts/3-pool-cash-model]],
  [[concepts/pre-frame-frame-separation]], [[problems/wac-feedback-loop]], [[features/F-058]],
  [[problems/test-transaction-implied-constructor-mismatch]].
- Not filed then: a missing cost now surfaces as a `MISSING_COST_BASIS` data-quality warning with a
  `navigate_asset` call to action (`portfolio_engine.py`, group key `missing_cost_basis`) — which is why a
  Dashboard E2E that counted asset links page-wide broke the next day
  ([[sources/phase00-fx-dashboard-sync-2026-10]]).
- Yield on Cost divides by the same average cost: the engine's `position.wac` comes from `compute_average_costs()`
  ([[decisions/yield-on-cost-definition]]).
- Settings bulk validation: [[problems/global-settings-bulk-saved-unvalidated-values]].

## Residuals (backlog 38)

P-1 an Auto cost with no position saves 0 without a warning (decided 2026-10-09: entering and leaving at 0 is
accepted; a later lot reuses the missing-cost flow) · P-2 WAC preview mislabels split rows, dead `add_at_wac` branch ·
P-3 per-position contribution drops unconverted dividends/costs without a signal · P-4 IANA timezone database in the
Docker image · P-5 migrate `roi_utils`/`valuation_utils` into `financial_math` (decision D1: "later we factor the
others") · **P-6 the graph update for the 2026-10-07 pages — still pending: the graph has not been rebuilt since
2026-09-09** · P-7 close issues #32 and #35 at release · P-8 stale header comment in `tx-clone.spec.ts` · P-9 Black on two
API test files.

## Wiki pages updated

- [[problems/global-settings-bulk-saved-unvalidated-values]] — new.
- [[decisions/settings-write-path-contract]] — note on the server's all-or-nothing bulk write.
- This page — new, indexes the 2026-10-07 filings.

## Source files

| Role | Path |
|------|------|
| Plan (P0–P12, §9 residuals) | `LibreFolio_developer_journal/Release_2/phases/30_wacUnification/plan-phase00WacUnification.prompt.md` |
| Plan (settings bulk validation) | `LibreFolio_developer_journal/Release_2/phases/30_wacUnification/plan-phase00SettingsBulkValidation.prompt.md` |
| `compute_average_costs()` | `backend/app/services/financial_math/average_cost.py` |
| Layer rule (D1) | `backend/app/services/financial_math/__init__.py` |
| `MISSING_COST_BASIS` issue with `navigate_asset` | `backend/app/services/portfolio_engine.py` |
| Settings validation | `backend/app/schemas/settings.py` |
| Developer doc (WAC) | `mkdocs_src/docs/developer/backend/transactions/wac.md` |
