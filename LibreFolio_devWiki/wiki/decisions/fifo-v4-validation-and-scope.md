---
title: "FIFO v4 validation approach and release scope (deferred PE reconciliation)"
category: decision
status: resolved
date: 2026-07-22
tags: [backend, validation, data-quality, scope, portfolio-engine]
related: [fifo-v4-engine-architecture, entities/portfolio-engine, problems/transaction-update-bypassed-sign-validation]
---

# Decision: FIFO v4 validation approach and release scope

## Context
Two scoping questions came up late in the plan: (1) how strongly to enforce that FEE/TAX transaction amounts
are negative (since downstream math assumes costs are positive magnitudes derived from `-amount`), and (2)
whether Portfolio-Engine-side reconciliation with the new FIFO-side fee/tax/income figures should land in the
same release.

## Options Considered
- **Sign enforcement**: a DB `CHECK` constraint tied to transaction type/amount sign, plus API validation, was
  the strongest end-to-end guarantee and was recommended in `feasibility-analysis-v4.1.md` §5/§13. The final
  implementation plan overrode this: **no DB CHECK**, because a CHECK coupled to an enum/type column was judged
  fragile (schema/enum evolution risk); instead: fix the actual gap (CREATE validated sign, UPDATE did not),
  add a one-off read-only audit script, and keep an internal defensive sign guard as a diagnostic, not a hard
  DB-level constraint.
- **Portfolio Engine reconciliation**: block this release until FIFO-side and Portfolio-Engine-side fee/tax/
  income totals are cross-checked with a runtime reconciliation and new pre-share absolute accumulators, vs.
  **ship the FIFO-side work now, defer PE-side reconciliation** — chosen to defer: `portfolio_engine.py` already
  has two separate accumulator paths and share-application logic scattered across multiple call sites (a
  "high-risk, hot file"), there is no current consumer relying on cross-engine agreement, and FIFO-side
  conservation tests were judged sufficient evidence of correctness for this release on their own.

## Decision
- Validate FEE/TAX sign at the **API/service layer**: the shared transaction business-rule validator now runs
  against the **final merged state** on UPDATE (previously it only checked `id > 0`), closing the gap where
  CREATE enforced negative amounts but PATCH did not. No schema migration, no DB CHECK constraint.
- A read-only diagnostic script (`audit_transaction_signs.py`) was added as a one-time/CI-style gate to prove
  the "costs are negative amounts" assumption holds across existing data — it found zero anomalies in the real
  DB at time of the audit.
- Portfolio Engine cross-engine reconciliation and pre-share absolute accumulators are explicitly **deferred**,
  not abandoned — tracked as future work, not a bug in this release.

## Consequences
- No irreversible schema change; validation logic can evolve without a migration.
- The internal sign guard is a diagnostic signal only — an unexpected sign is not currently surfaced as a
  public data-quality flag, only defended against internally.
- No displayed value changes today as a result of the deferral, but FIFO-computed and Portfolio-Engine-computed
  fee/tax/income totals can in principle drift apart until reconciliation work is scheduled — see
  [[entities/portfolio-engine]] for the current state of that file.
- [[problems/transaction-update-bypassed-sign-validation]] documents the specific bug this validation fix
  closed.

## Related
- [[problems/transaction-update-bypassed-sign-validation]]
- [[entities/portfolio-engine]]
- [[fifo-v4-engine-architecture]]
- [[sources/fifo-v4-fee-tax-integration]]

## Source files

| Role | Path |
|------|------|
| DB CHECK recommendation (superseded) | `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/feasibility-analysis-v4.1.md` §5, §13 |
| Final validation approach | `.../v4-fee_tax_integration/implementation-plan-v5.md` Fase 0.1-0.3 |
| Audit script + recap | `.../v4-fee_tax_integration/implementation-recap-v5.md` §1 |
| PE deferral rationale | `.../v4-fee_tax_integration/implementation-recap-v5.md` §1, §5; `post-implementation-review-v5.md` §4, §9; `review-checklist-v5.md` R1 |
| Validator | `backend/app/schemas/transactions.py`, `backend/app/services/transaction_service.py` |
| Audit script | `backend/test_scripts/test_db/audit_transaction_signs.py` |
| Portfolio Engine | `backend/app/services/portfolio_engine.py` |
