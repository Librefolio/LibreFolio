---
type: source
title: "Phase 07 — Part 3 Closure_2: Batch 4 + BlockG test coverage (G1..G7)"
date_ingested: 2026-04-24
date_updated: 2026-04-25
git_hash: a61b0dfa
path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte3/plan-phase07-transaction-Part3_1_Closure_2.prompt.md
status: "✅ DONE"
companion_files:
  - phases/phase-07-subplan/Parte3/plan-phase07-transaction-Part3_1_Closure_2-Batch4dPart2.prompt.md
  - phases/phase-07-subplan/Parte3/plan-phase07-transaction-Part3_1_Closure_2-Batch4dPart3.prompt.md
  - phases/phase-07-subplan/Parte3/plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md
related:
  - concepts/savewithretry-frontend-pattern
  - decisions/price-currency-hard-reject
  - decisions/policy-d-currency-wipe
  - problems/assets-wipe-error-attr-mismatch
  - problems/babel-currency-symbol-echo
  - features/F-046
  - features/F-049
  - features/F-012
---

# Phase 07 Part 3 Closure_2 — Batch 4 + BlockG (G1..G7)

> Companion to the Closure plan. Contains the pending batches at time of split
> (parent plan had grown to ~1700 lines): all Batch 4 sub-items and the complete
> BlockG test coverage pass — including the post-G follow-ups G-batch6 / G-batch7
> that took backend coverage from ~57% (start of Phase 7) to **87.06%** in two days.
>
> **Path note**: archived 2026-04-25 into `phases/phase-07-subplan/Parte3/`. ✅ DONE.

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
via `CHANGED_POINTS_PAYLOAD_CAP`). Semantics:
- `[]` (empty list) on idempotent no-op sync (provider returned same points already in DB)
- list with up to 500 deltas when ≤ cap
- `None` when above cap (frontend falls back to full series reload)

Backend implementation in `backend/app/schemas/refresh.py` + `backend/app/services/asset_source.py`.
Frontend's live-poll now merges the polled point directly into the chart store
without triggering a full series reload (commit `ddb1fcfb` — "silent-sync detour
removed"). The previous "silent sync" pattern compared the provider fetch with the
freshly-written DB row and produced spurious `changed_points=None`.

### 4.g — #9 ErasableNumberCell `null` semantics (commit `83328b6b`)

`ErasableNumberCell` was rendering "0" instead of the empty placeholder when a
draft value was cleared. Fix: declare the draft as `$state<number | null>` (not
`number`) so the eraser 🧽 can produce a true `null` distinct from `0`.
Aligned with `notSet` i18n placeholder. Validates [F.5 sentinel/eraser](../../sources/phase07-part3-api-consolidation.md#blocco-f--ohlc-sentinel)
end-to-end.

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

**Result**: 7/7 test groups green, **76.05% backend coverage** (post G-batch5,
2026-04-24). Two further follow-up rounds drove this to 87.06% — see below.

## G-batch6 — Post-G coverage gap-fill (2026-04-25)

Trigger: a full coverage run after G-batch5 closed showed **8 production functions
still at 0% coverage** despite contracts shipped. G-batch6 added 17 tests in three
new files (commit `c943f219`):

| Test file | Area | Tests |
|-----------|------|-------|
| `test_market_data_wipe.py` | Policy D wipe + summary endpoints (`/assets/{id}/market_data/{summary,wipe}`) | 5 |
| `test_backup_export_extras.py` | New `/backup/asset/{id}/events` + `/backup/fx/{base}/{quote}/rates` (CSV/JSON, inverted pair, 400, empty) | 8 |
| `test_brim_provider_base.py` | `BRIMProvider.docs_url`, `icon_url`, `plugin_version`, `to_plugin_info` defaults | 4 |

**Coverage delta**: 76.05% → **85.34%**. Brought `api/v1/backup.py::backup_asset_events`
and `backup_fx_rates` from 0% to ~95–100%, plus `services/asset_source.py::wipe_market_data_for_currency_change` to full coverage.

### 🐛 Production bug #1 — discovered & fixed in G-batch6

`backend/app/api/v1/assets.py` — both `market_data_summary` and `wipe_market_data`
caught `AssetSourceError` and read `e.code`, but the exception class only exposes
`e.error_code`. Result: any failure path raised `AttributeError`, masking real
errors as **HTTP 500** instead of the intended 404.

- **Fix**: `e.code` → `e.error_code` (2 occurrences).
- **Filed as**: [[problems/assets-wipe-error-attr-mismatch]]
- **Test that caught it**: `test_market_data_wipe.py::test_wipe_unknown_asset_returns_404`

## G-batch7 — Audit-driven gap-fill (2026-04-25, commit `a61b0dfa`)

After G-batch6, an audit identified 6 partially-covered production hotspots worth
covering (high value/cost ratio). 22 new tests added across 6 suites, taking
coverage **85.34% → 87.06%**.

| Suite | Area | Tests |
|-------|------|-------|
| `test_currency_utils.py::TestNormalizeCurrency` | symbol/name/multi-match resolution | 10 |
| `test_uploads_serve_file.py` | text preview, image preview, attachment header, MIME detection | 6 |
| FX chain edge cases | inverted pair, missing rate fallback | (folded into existing suites) |
| `validate_assets_bulk` | pre-PATCH validate dry-run | (folded) |
| `query_events_bulk` defensive branches | provider exceptions, identifier-type fallbacks | (folded) |
| `get_prices_bulk` FX target_currency fallback | partial coverage retained where mocking would be fragile | (folded) |

### 🐛 Production bug #2 — discovered & fixed in G-batch7

`backend/app/utils/currency_utils.py::normalize_currency` was relying on
`babel.numbers.get_currency_symbol(code)`, which **echoes the input back** for
unknown codes (so `get_currency_symbol("ZZZZZZ")` returns `"ZZZZZZ"`). The
function therefore reported any garbage string as a valid currency.

- **Fix**: replaced `babel` lookup with strict `pycountry.currencies.get(alpha_3=...)`
  + explicit `None` fallback. Symbol resolution still uses `SYMBOL_TO_ISO` map.
- **Filed as**: [[problems/babel-currency-symbol-echo]]
- **Test that caught it**: `test_currency_utils.py::TestNormalizeCurrency::test_unknown_garbage_returns_none`

## Coverage progression — Phase 7 final

| Stage | Backend coverage | Tests added | Notes |
|-------|------------------|-------------|-------|
| Phase 7 Part 3 entry | ~57% | — | baseline before BlockG |
| Post G-batch5 (2026-04-24) | **76.05%** | +60 (G.3..G.13) | 7/7 groups green |
| Post G-batch6 (2026-04-25) | **85.34%** | +17 (0%-functions) | + 1 prod fix (`e.error_code`) |
| Post G-batch7 (2026-04-25) | **87.06%** | +22 (gap-fill) | + 1 prod fix (`normalize_currency`) |

**Bottom line**: backend coverage went from ~57% → **87.06%** in 2 days of focused
test work, surfacing 2 latent production bugs in the process.

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
