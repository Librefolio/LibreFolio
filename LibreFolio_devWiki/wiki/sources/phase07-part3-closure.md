---
type: source
title: "Phase 07 — Part 3 Closure: Blocco I decisions + I-bis issues + Blocco H implementation"
date_ingested: 2026-04-24
git_hash: 66ad026a
path: LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part3_1_Closure.md
status: completed
---

# Phase 07 Part 3 Closure

> Closure plan for Part 3. Contains the authoritative terminal decisions on Blocco E,
> the full I-bis issue log (26 items), Policy D backup endpoints, and R3-x retest rounds.

## Purpose

After Part 3 Blocchi A–H were implemented and tests passed, a functional review
checklist was written BEFORE manual testing. Reading it revealed design contradictions
that invalidated parts of Blocchi E and F. The Closure plan records:

1. **Authoritative terminal decisions on Blocco E** (see part3 source — most are cancelled)
2. **Blocco I implementation** (currency simplification, hard-400, 409 on change)
3. **I-bis issue queue** (26 UX/BE follow-ups from manual testing 2026-04-22)
4. **Policy D (R3-3)**: backup/restore endpoints
5. **Retest rounds R3, R4, R5** (post-implementation verification)

## I-bis Issue Queue (key items)

The manual testing session on 2026-04-22 produced 26 I-bis follow-up issues. Notable ones:

| # | Status | Summary |
|---|--------|---------|
| #1 | ✅ | Navigation back from FX → asset detail (goBack bug) |
| #2 | ✅ | Save Without Testing gating (form validation before save) |
| #5 | ✅ | CsvEditor: auto-detect separator + tolerant header |
| #7 | ✅ | HTTP 409 for asset currency change with existing prices |
| #9 | ✅ | ErasableNumberCell placeholder (`notSet`) fixes |
| #12 | ✅ | Toast reduction (3 toasts → 1 contextual) |
| #19 | ✅ doc-only | `Asset.active` semantic → deferred to Phase 8/9 |
| #22 | ✅ | `saveWithRetry` helper + adopted in 8+ modals |
| #23 | ✅ | Unified sync handler (`buildAssetSyncToast`) |
| #24 | ✅ | Backend `changed_points` delta + FE incremental merge (live-poll) |
| #25 | ✅ | Resolved in intermediate commit |
| #26 | ✅ | Scheduled investment Step 2/4 reorder + cache key test |

## R3-3 Policy D — Backup Endpoints

`GET /api/v1/system/export` and `POST /api/v1/system/import` — basic backup/restore
endpoints added. The full backup feature (F-073) remains largely unimplemented; these
endpoints are the first scaffolding.

## #R6-4 — Scheduled Investment Symmetric Wipe

Critical fix: when `scheduled_investment` provider params change:
- Prices deleted ✅
- Provider-generated events deleted ✅ (events with non-null `provider_assignment_id`)
- Manual events preserved ✅ (events with `provider_assignment_id IS NULL`)
- Transactions pointing to deleted events: `asset_event_id = NULL`, **row preserved** ✅
  (so FIFO history is intact, just the event link is severed)
- Assignment row: **UPDATE** (not DELETE/INSERT) so FK chain stays stable

Prior to this fix, only prices were wiped — stale auto-events contradicted the regenerated
schedule and made `get_current_value` undefined.

## #R6-5 — Auto-Sync After Provider Change

When a user changes provider (non-parametric providers like yfinance/JustETF), an
automatic non-blocking sync is triggered after successful save. The chart updates
without requiring a page reload.

## FxBackwardFillInfo Refactor

`FxBackwardFillInfo` extracted as a standalone Pydantic mixin (from `common.py`):
- `fx_rate_date: Optional[date]`
- `fx_days_back: Optional[int]`

`AssetBackwardFillInfo` inherits from `BackwardFillInfo + FxBackwardFillInfo`.
`FAAssetEventPointOut` (events) gets `fx_info: Optional[FxBackwardFillInfo]` directly
(events have no price-backward-fill semantics — only FX staleness is meaningful).

## Wiki Cross-References

- [[decisions/price-currency-hard-reject]]
- [[decisions/tx-link-uuid-semantics]]
- [[concepts/savewithretry-frontend-pattern]] (emerging, formalized in Closure_2)
- [[F-012]] BRIM Framework
- [[F-046]] Transaction Model & Bulk API
- [[sources/phase07-part3-closure2]] — continuation

## Source files

| Role | Path |
|------|------|
| Transaction service | `backend/app/services/transaction_service.py` |
| Asset source (wipe logic) | `backend/app/services/asset_source.py` |
| Schemas (common FxBackwardFillInfo) | `backend/app/schemas/common.py` |
| Scheduled investment provider | `backend/app/services/asset_source_providers/scheduled_investment.py` |
| Asset currency change modal | `frontend/src/lib/components/assets/AssetCurrencyChangeModal.svelte` |
| Navigation store | `frontend/src/lib/stores/navigationStore.ts` |
