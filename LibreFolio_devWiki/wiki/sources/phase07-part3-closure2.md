---
type: source
title: "Phase 07 — Part 3 Closure_2: Batch 4 + BlockG test coverage"
date_ingested: 2026-04-24
git_hash: 1bff6ad1
path: LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part3_1_Closure_2.prompt.md
status: completed
companion_files:
  - plan-phase07-transaction-Part3_1_Closure_2-Batch4dPart2.prompt.md
  - plan-phase07-transaction-Part3_1_Closure_2-Batch4dPart3.prompt.md
  - plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md
---

# Phase 07 Part 3 Closure_2 — Batch 4 + BlockG

> Companion to the Closure plan. Contains only pending batches at time of split
> (parent plan had grown to ~1700 lines). All Batch 4 sub-items and the complete
> BlockG test coverage pass.

## Batch 4 — I-bis Closure

All 7 outstanding I-bis items were resolved before starting BlockG (deliberate decision:
write tests against final behavior, not code that's about to change).

### 4.a — #2 Save Without Testing Gating
Form validation gating: block Save if required fields are incomplete, showing inline
`formError` without triggering network calls.

### 4.b — #7 HTTP 409 for Currency Change with Prices
`PATCH /assets/:id` with `currency` change when price history exists → 409 with:
`{existing_count, oldest_date, newest_date}`. Frontend shows `AssetCurrencyChangeModal`.

### 4.c — #26 Scheduled Investment Step Reorder
Step 2 (schedule config) and Step 4 (preview) reordered for better UX. Cache key
aligned with new step order.

### 4.d — #22 `saveWithRetry` Helper + Modal Adoption
New helper `saveWithRetry(fn, opts)` in `frontend/src/lib/utils/saveWithRetry.ts`:
- Centralized error extraction (Zodios error → human message)
- Optional toast on success/failure
- `onError` hook for per-modal custom handling (e.g., map 409 to `formError`)
- Returns `{status: 'success'|'error', message}`

Adopted across **8+ modals** (3 sub-batches):
- Part1: `BrokerModal`, `CashTransactionModal`, `AssetCurrencyChangeModal`
- Part2: `PasswordChangeModal`, `FxPairAddModal`, `BrokerImportFilesModal`, `BrokerSharingModal`, `AssetModal`
- Part3 (#R6-6/#R6-7/#R6-8 drift): upload/delete toasts, ConfirmModal for bulk delete

Key design for `AssetModal`: the `saveWithRetry` wrapper calls `saveCreate`/`saveEdit`
internally. The 409 "currency-change" intercept (reconstructs `patchResp` from
`detail.results[]`) runs INSIDE `saveEdit` and is NOT surfaced as an error — this
preserves the existing `AssetCurrencyChangeModal` flow.

### 4.e — #5 CSV Auto-Detect Separator
`CsvEditor`: auto-detects separator (`,`/`;`/`\t`) and is tolerant of extra header
columns. Ensures CSV export → CSV import round-trip works reliably.

### 4.f — #24 Backend `changed_points` + FE Incremental Merge
Backend `FARefreshResult` gains `changed_points: Optional[list]` (capped at 500 entries
via `CHANGED_POINTS_PAYLOAD_CAP`). `None` when above cap (full reload). `[]` on
no-op sync. Frontend's live-poll now merges the delta directly into the chart store
without triggering a full series reload (commit `ddb1fcfb` — "silent-sync detour removed").

## BlockG — Test Coverage Pass

Full backend test coverage for Phase 07 Part 3. Scope after audit:

| Test file | Area | Tests |
|-----------|------|-------|
| `test_ohlc_sentinel.py` | F.4 sentinel `-1` → NULL | 7 |
| `test_current_price_bootstrap.py` | F.2/F.3 `_extend_ohlc_bounds` unit | 8 |
| `test_current_price_persistence.py` | F.2/F.3 side-effect via /current API | 5 |
| `test_asset_prices_export.py` | I.4 export + round-trip | 5 |
| `test_prices_currency_coherence.py` | I.2 hard-400 mismatch | 5 |
| `test_asset_currency_change.py` | I.3 PATCH + 409 semantics | 4 |
| `test_prices_sync_delta.py` | #24 changed_points contract | 5 |
| `test_transactions_validate.py` | Blocco C.1 dry-run | 6 |
| `test_events_suggest.py` | Blocco C.2 events/suggest | 7 |
| `test_scheduled_investment_param_change.py` | #R6-4 wipe + tx disconnect | 3 |
| `test_broker_multiuser_api.py` | VIEWER PATCH/DELETE 403 | +2 |
| `test_transaction_service.py` | Blocco A/H audit | no gap |

**Result**: 7/7 test groups green, **76.05% backend coverage** (2026-04-24).

### G discovery — Side-effect of `/current` endpoint (G.6c)

Not in the original plan: the `/current` endpoint's side effect of persisting the current
price as a synthetic OHLC row to history was documented in concept but never tested.
G.6c added 5 end-to-end tests for this.

### G discovery — `test_asset_source_refresh.py` regression (G.9)

`test_refresh_currency_fallback_uses_asset_currency` was obsolete post-Phase-7 I.2
(hard-reject on currency mismatch). Renamed and aligned to test the happy pipeline
with matching currency instead.

## Wiki Cross-References

- [[concepts/savewithretry-frontend-pattern]]
- [[decisions/price-currency-hard-reject]]
- [[F-046]] Transaction Model & Bulk API
- [[F-012]] BRIM Framework
- [[sources/phase07-part3-closure]] — predecessor

## Source files

| Role | Path |
|------|------|
| saveWithRetry helper | `frontend/src/lib/utils/saveWithRetry.ts` |
| AssetModal | `frontend/src/lib/components/assets/AssetModal.svelte` |
| BrokerImportFilesModal | `frontend/src/lib/components/brokers/BrokerImportFilesModal.svelte` |
| BrokerSharingModal | `frontend/src/lib/components/brokers/BrokerSharingModal.svelte` |
| CsvEditor | `frontend/src/lib/components/ui/data-editor/CsvEditor.svelte` |
| Transaction validate test | `backend/test_scripts/test_api/test_transactions_validate.py` |
| Events suggest test | `backend/test_scripts/test_api/test_events_suggest.py` |
| OHLC sentinel test | `backend/test_scripts/test_services/test_ohlc_sentinel.py` |
| Prices currency coherence test | `backend/test_scripts/test_services/test_prices_currency_coherence.py` |
| Asset currency change test | `backend/test_scripts/test_api/test_asset_currency_change.py` |
| Scheduled investment param change test | `backend/test_scripts/test_services/test_scheduled_investment_param_change.py` |
