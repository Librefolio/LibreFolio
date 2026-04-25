---
type: source
title: "Phase 07 — Part 3 Closure: Blocco I decisions + I-bis issues + Blocco H implementation"
date_ingested: 2026-04-24
date_updated: 2026-04-25
git_hash: a61b0dfa
path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte3/plan-phase07-transaction-Part3_1_Closure.md
status: "✅ DONE"
related:
  - decisions/price-currency-hard-reject
  - decisions/tx-link-uuid-semantics
  - decisions/policy-d-currency-wipe
  - concepts/savewithretry-frontend-pattern
  - entities/backup-router
  - features/F-012
  - features/F-046
  - features/F-051
---

# Phase 07 Part 3 Closure

> Closure plan for Part 3. Contains the authoritative terminal decisions on Blocco E,
> the full I-bis issue log (26 items), Policy D backup endpoints, and R3-x retest rounds.
>
> **Path note**: archived 2026-04-25 into `phases/phase-07-subplan/Parte3/`. ✅ DONE.

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

## R3-3 Policy D — Destructive Currency-Change Wipe + Backup Endpoints

When `PATCH /assets/{id}` changes `currency` and the asset has price/event history,
the chosen semantics is **Policy D — destructive symmetric wipe + transaction
disconnection** (commit `8fc018ab`, 2026-04-23):

- All `price_history` rows for the asset → DELETED
- All `asset_events` rows for the asset → DELETED (manual + provider-generated)
- `transactions.asset_event_id` for affected events → set to `NULL` (rows preserved
  so FIFO history stays intact, only the event link is severed)
- `provider_assignment` row → re-pointed (provider can re-sync from scratch in new currency)

Because the wipe is irrecoverable, a **new read-only backup router** was introduced
to allow the user to export a snapshot before confirming the destructive PATCH.

### New router: `backend/app/api/v1/backup.py`

| Endpoint | Purpose |
|----------|---------|
| `GET /backup/asset/{asset_id}/prices` | Export price history (CSV/JSON). Replaces legacy `/assets/{id}/prices/export`. |
| `GET /backup/asset/{asset_id}/events` | **NEW** — Export asset events with FX backfill columns (`date, type, source, amount, currency, fx_rate_date, fx_days_back, original_amount, original_currency, description, provider_assignment_id`). |
| `GET /backup/fx/{base}/{quote}/rates` | **NEW** — Export FX pair rates respecting normalised pair direction (`date, rate, source_plugin_key, fetched_at`). |

The frontend `AssetCurrencyChangeModal` now calls `/backup/asset/{id}/prices` and
`/backup/asset/{id}/events` pre-confirm so the user can save a CSV/JSON snapshot
before executing the destructive PATCH. See [[decisions/policy-d-currency-wipe]]
and [[entities/backup-router]] for details.

> ⚠️ **Note vs the old "R3-3 Policy D" placeholder line**: an earlier draft of this
> wiki page mentioned `/api/v1/system/export` + `/api/v1/system/import` as Policy D.
> That description was wrong — it was never implemented. The actual Policy D
> backup feature is the per-resource `backup.py` router described above.

## #R6-4 — Scheduled Investment Symmetric Wipe

Critical fix: when `scheduled_investment` provider params change:
- Prices deleted ✅
- Provider-generated events deleted ✅ (events with non-null `provider_assignment_id`)
- Manual events preserved ✅ (events with `provider_assignment_id IS NULL`)
- Transactions pointing to deleted events: `asset_event_id = NULL`, **row preserved** ✅
  (so FIFO history is intact, just the event link is severed — see [[features/F-056]])
- Assignment row: **UPDATE** (not DELETE/INSERT) so FK chain stays stable

Prior to this fix, only prices were wiped — stale auto-events contradicted the regenerated
schedule and made `get_current_value` undefined.

> **Distinction from Policy D**: #R6-4 (scheduled-investment param-change) is
> *selective* — only provider-generated events are wiped. Policy D (currency change)
> is *destructive symmetric* — all events deleted regardless of source, because the
> currency change invalidates the meaning of every historical amount.

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
