---
title: "R2 SP-B — Backend Tests WAC + Mock Data"
category: source
source_type: plan
date_ingested: 2026-06-01
original_path: LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/plan-R2-SP-B-BackendTests.prompt.md
tags: [phase07, transactions, wac, testing, backend, mock-data, fx]
related:
  - sources/r2-walktest-feedback-master
  - sources/r2-sp-a-cost-basis-wac
  - features/F-097
  - features/F-068
---

# Source: R2 SP-B — Backend Tests WAC + Mock Data

## Summary
Test coverage plan (✅ completed, commit `473d2611`) for the WAC feature. Creates `test_transactions_wac.py` with 13 API tests (WAC-1→WAC-13) covering the new Currency schema, auto-calc WAC, FX cross-currency, recalc-wac endpoint, and validation error cases. Self-contained tests — each creates its own user+broker+asset via API.

## Key Takeaways

### Test matrix (13 tests)
| ID | Scenario | Verifies |
|----|----------|----------|
| WAC-1 | TRANSFER with explicit `cost_basis_override: {code:"EUR", amount:"42.50"}` | Currency object accepted and persisted |
| WAC-2 | TRANSFER without override, BUY all EUR | Auto-calc WAC = weighted avg of BUYs |
| WAC-3 | TRANSFER without override, BUY EUR+USD with FX pair | WAC converted via FX, `wac_info.conversions` populated |
| WAC-4 | TRANSFER without override, BUY EUR+CHF without FX pair | `wac=None`, `missing_pairs` contains `"CHF/EUR"` |
| WAC-5 | TRANSFER without override, no BUY | `{code:target, amount:"0"}` |
| WAC-6 | recalc-wac: 2 TX same asset, different brokers | Both updated |
| WAC-7 | recalc-wac: TX with different assets | 400 error |
| WAC-8 | recalc-wac: non-TRANSFER TX | `updated=false` (ignored) |
| WAC-9 | Old format `"42.50"` (plain string) | 422 validation error |
| WAC-10 | Invalid currency `{code:"INVALID", amount:"10"}` | 422 validation error |
| WAC-11 | PATCH update cost_basis_override with Currency | GET confirms update |
| WAC-12 | Promote batch with resolved_fields.cost_basis_override | Receiver gets Currency |
| WAC-13 | Promote legacy endpoint with cost_basis_override | New receiver has Currency |

### Implementation patterns
- Helper functions: `create_user_broker_asset()`, `commit_batch()`, `get_tx_by_id()`, `create_fx_pair_with_rate()`
- TRANSFER pair creation: DEPOSIT → BUY → TRANSFER sender (qty<0) + receiver (qty>0) with shared `link_uuid`
- WAC-3 creates FX pair+rate via API inline (no populate_mock_data.py modification)
- `wac_info` lives only in commit/promote response (`TXBatchResultItem`), NOT in GET /transactions

### Key insight
- `wac_info` is transient: available only in the commit response, not persisted or re-fetchable via GET
- Tests must verify `wac_info` from commit response, and `cost_basis_override` from subsequent GET

## Source files
| Role | Path |
|------|------|
| WAC test file | `backend/test_scripts/test_api/test_transactions_wac.py` |
| Test server helper | `backend/test_scripts/test_server_helper.py` |
| Test utilities | `backend/test_scripts/test_utils.py` |
| Test runner registration | `scripts/test_runner/_backend_api.py` |
