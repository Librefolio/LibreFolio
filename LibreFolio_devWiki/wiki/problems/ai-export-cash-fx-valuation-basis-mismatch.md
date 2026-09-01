---
title: "AI Export falsely required transaction-date engine cash to equal snapshot-date native-cash exposure"
category: problem
status: resolved
date: 2026-07-26
updated: 2026-07-27
mkdocs: "developer/architecture/patterns/ai_export_snapshot.md"
tags: [backend, ai-export, portfolio, cash, fx, denominator, e2e, financial-semantics]
related:
  - sources/phase00-ai-export-backend-snapshot
  - decisions/ai-export-versioned-snapshot-boundary
  - entities/ai-export-snapshot-service
  - entities/portfolio-engine
  - entities/portfolio-service
  - concepts/3-pool-cash-model
---

# Problem: AI Export falsely required transaction-date engine cash to equal snapshot-date native-cash exposure

## Symptom

The live cross-domain E2E reached Dashboard AI Export but the Portfolio snapshot returned HTTP 503 `snapshot_source_failure`, with the internal operation reported as `portfolio_service.cash_balance_total_mismatch`. Native cash balances were present and convertible, yet a validation invariant rejected the snapshot because their snapshot-date converted total did not equal `PortfolioSummary.cash_total`.

## Root Cause

The compared values are both factual, but they answer different questions on different valuation clocks:

- **Portfolio Engine accounting cash** converts each transaction amount using FX on `tx.date`. Its summary and latest history point preserve portfolio economics and the three-pool decomposition between contributed capital and generated returns.
- **Native-currency cash exposure** preserves actual currency balances, then converts each balance at `snapshot_as_of` so the export can describe current currency exposure.

FX movement between transaction dates and the snapshot date makes those totals legitimately different. The equality check therefore conflated engine-owned accounting/NAV with a snapshot-date exposure view and treated a valid temporal-basis difference as source corruption.

## Solution

- Preserve `PortfolioSummary.cash_total` and the latest history point's `cash_value`, `cash_from_contributed_capital`, and `cash_from_generated_returns` exactly as supplied by Portfolio Engine/Service.
- Preserve native cash amounts and convert them at `snapshot_as_of` only for the currency-exposure allocation.
- Calculate `allocation_by_currency_pct` over its declared own denominator:
  `trading_currency_positions_plus_native_cash_snapshot_value`.
- Declare the corresponding method as
  `trading_currency_positions_plus_native_cash_snapshot_conversion`.
- Keep fail-closed checks for genuinely inconsistent native-balance sources and failed FX conversion, but remove the invalid cross-basis equality invariant.
- Do **not** change Portfolio Engine math, cash decomposition, NAV, or transaction-date FX treatment.

## Prevention

- Every exported metric must declare unit, period, method, universe, and denominator; never reconcile values unless those semantics match.
- Tests must include differing FX clocks. The regression fixture uses USD 100 represented as EUR 90 in engine cash but EUR 95 at snapshot exposure, yielding coherent currency weights of 89.39% EUR and 10.61% USD over the exposure denominator.
- Keep accounting views and exposure views as separately named facts rather than forcing one to rewrite the other.
- A source failure remains appropriate when broker-level and aggregate native balances disagree, a required conversion is unavailable, or the converter returns an invalid date/currency.

## Impact

The invalid invariant blocked an otherwise valid Portfolio export during live E2E and surfaced as a user-visible 503. It did not corrupt persisted data and did not reveal an error in Portfolio Engine calculations; the fix was isolated to AI Export assembly semantics and regression coverage.

## Final verification

The 27 July Phase 0 gate retained the corrected denominator through the cross-domain browser flow and approved representative desktop/mobile Portfolio Snapshot and prompt behavior. The plan chain is closed and indexed by `Release_2/Phase_0/01_signalMigration/02_aiExport/README.md`; no Portfolio Engine rewrite was introduced.

## Links

- [[entities/portfolio-engine]]
- [[concepts/3-pool-cash-model]]
- [[entities/ai-export-snapshot-service]]
- [[decisions/ai-export-versioned-snapshot-boundary]]

## Source files

| Role | Path |
|------|------|
| Final plan and archive index | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/plan-phase00AiExportBackendSnapshotImplementation.prompt.md`, `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/README.md` |
| Portfolio payload (successor to the deleted assembler) | `backend/app/services/ai_export/components/payloads/portfolio_broker.py` |
| Portfolio financial components (cash totals, balances, allocations) | `backend/app/services/ai_export/components/portfolio_financial.py` |
| Composition entrypoint | `backend/app/services/ai_export/composer.py` |
| Regression tests (successors) | `backend/test_scripts/test_services/test_ai_export_components_portfolio_broker_financial.py`, `backend/test_scripts/test_services/test_ai_export_components_portfolio_broker_integration.py` |
| Transaction-date cash conversion | `backend/app/services/portfolio_engine.py` |
| Portfolio summary/history source | `backend/app/services/portfolio_service.py` |
| Snapshot service / error boundary | `backend/app/services/ai_export/runtime_service.py` |
| Live browser E2E | `frontend/e2e/ai-export/` |
| Developer explanation | `mkdocs_src/docs/developer/architecture/patterns/ai_export_snapshot.md` |

> ### Path note (2026-09-01) — the modules this page names were **dismantled**, not moved
>
> `ai_export/assemblers/` and `ai_export/profiles/` still exist as directories, but they
> contain nothing except `__pycache__` — stale bytecode of files that are gone. That litter
> is the only reason `ls` still shows them, and it is what makes them look like a move.
> They were **deleted** in commit **`615a52eb` (2026-08-05)**, *"refactor(ai-export): remove
> legacy runtime"*, which removed **22 233 lines against 1 577 added**: the whole
> `assemblers/` + `profiles/` + `resolver.py` + `sampling.py` + `technical.py` +
> `normalization.py` + `service.py` stack, and the tests that covered it.
>
> The commit states the reason in one sentence: *"Keep one production path so catalog,
> prompts, and tests cannot drift between V3 composition and **an unreachable
> profile/assembler stack**."* It was not dead weight being tidied — it was a **second
> path that could still be reached by some callers and had begun to disagree with the
> first**. The fix was to delete the loser, not to reconcile them. Compare
> [[problems/registered-but-unreachable-test-actions]] and
> [[concepts/silent-no-op-option]]: same family — code that is present, plausible, and
> not the one that runs.
>
> The surviving path is **V3 composition**: `components/` (one module per payload),
> `datasets/` and `analyses/` (catalog + spec), `temporal/`, `composer.py` and
> `runtime_service.py`. The table above points there.
>
> **This page was written on 2026-08-31, twenty-six days after the deletion.** It named
> the deleted modules because it was written from the plan that proposed them, not from
> the tree — the same failure that produced the invented `scripts/test_runner/` paths.
