---
type: source
title: "Phase 07 — Part 3: API Consolidation + Transfer Semantics + Currency Simplification"
date_ingested: 2026-04-24
git_hash: c9b269
path: LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part3.md
status: feature_complete
---

# Phase 07 Part 3 — API Consolidation

> The largest and most architecturally significant plan of Phase 07.
> Introduced multi-broker atomic transactions, transfer semantics, and
> the currency simplification (Blocco I) that invalidated several earlier designs.

## Overview

Plan unified:
1. **Blocco A+B** — Bulk endpoints (POST/PATCH/DELETE /transactions/bulk), multi-broker atomic
2. **Blocco C** — `POST /transactions/validate` (dry-run) + `POST /transactions/events/suggest`
3. **Blocco D** — i18n delete-event toasts + mock data
4. **Blocco E** — Price currency coherence (partially cancelled — see Blocco I)
5. **Blocco F** — OHLC partial upsert + sentinel `-1` + current-price auto-extend
6. **Blocco H** — Transfer semantics + promotion endpoint
7. **Blocco I** — Currency simplification (major revision of Blocco E design)

## Major Architectural Deviations

### Deviation 1 — Multi-Broker Atomic (not broker-scoped)

**Original plan**: `POST /brokers/{broker_id}/transactions/bulk` — reject any item with `broker_id ≠ path`.

**Problem discovered**: TRANSFER cross-broker requires both transactions in the same DB session
for the DEFERRABLE FK to resolve `link_uuid → related_transaction_id`. The existing test
`test_query_linked_tx_both_have_related_id` already required this pattern.

**Decision**: endpoints under `/transactions/*` (not broker-scoped). Accept items on multiple
brokers in one batch:
- Each distinct `broker_id` → EDITOR access check
- `_validate_broker_balances` called per broker touched
- Any violation (FK, balance, access, type mismatch) → total rollback + `rolled_back=True`

**Final endpoints:**
- `POST /transactions/bulk` (create)
- `PATCH /transactions/bulk` (update)
- `DELETE /transactions/bulk?ids=...` (delete)
- `POST /transactions/validate` (dry-run — mixed create+update+delete in one request)
- `GET /transactions?ids=1,2,3` (ordered by ids param)
- `POST /transactions/events/suggest` (±tolerance_days ∈ [0,7])
- **REMOVED**: `GET /transactions/{tx_id}` (replaced by ?ids= filter)

### Deviation 2 — Blocco H: Transfer Semantics (new, emerged in review)

Four design questions surfaced during Blocco A+B review:

1. **TRANSFER validation**: must have distinct brokers; pair must share same `type`.
   FX_CONVERSION is intra-broker OK (real use case).

2. **DEPOSIT/WITHDRAWAL soft linking**: optionally link with `link_uuid` for a "cash
   transfer between my brokers" UX. No new transaction type (`CASH_TRANSFER` rejected —
   no effect on FIFO, adds cognitive overhead). Just a `related_transaction_id` marker.

3. **Transfer suggest dropped** (POST /transactions/transfers/suggest): rejected.
   Replaced by extending `GET /transactions` with filters:
   `amount_abs_min`, `amount_abs_max`, `only_unlinked`, `exclude_ids`.
   Client calculates params from seed transaction — more composable.

4. **Promote endpoint**: `POST /transactions/transfers/promote` — atomic endpoint that
   converts a DEPOSIT/WITHDRAWAL pair → TRANSFER or FX_CONVERSION pair.
   Flow: validate → delete pair → create pair with new type + link (same `create_bulk` logic).

### Deviation 3 — Blocco I: Currency Simplification (superseded Blocco E)

Blocco E had planned soft-skip on currency mismatch, FX auto-registration, multiple banners.
A checklist review BEFORE executing them revealed design contradictions:

| E item | Fate | Reason |
|--------|------|--------|
| E.1 `fx_error` discriminator | ❌ Cancelled | `requiredFxPairs` in +page.svelte already handles 4 states |
| E.2 `currency_breakdown` | ❌ Cancelled | Redundant with I.2 hard-reject (all prices same currency) |
| E.3 soft-skip per-item | 🟡 → Hard 400 | Replaced by I.2 |
| E.4 FX auto-registration | ❌ Cancelled | Violates self-hosted philosophy (explicit control) |
| E.5 PriceCurrencyMismatchBanner | ❌ Cancelled | Not reachable via normal UI after I.2 |
| E.6 FX-missing banner variants | ❌ Cancelled | Superseded by `requiredFxPairs` |
| E.7 DataEditor currency column | ❌ Cancelled | Removed by I.8 |
| E.8 events target_currency | ✅ Done | `FAAssetEventPointOut.original_value + fx_rate_date + fx_days_back` |

**Blocco I decisions (implemented):**
- **I.2**: `upsert_prices_bulk` → HTTP 400 on any currency mismatch (hard reject)
- **I.3**: `PATCH /assets/{id}` with `currency` change when prices exist → **HTTP 409**
  with `{existing_count, oldest_date, newest_date}`. User must DELETE prices first, then PATCH.
- **I.4**: `GET /assets/{id}/prices/export` — CSV/JSON export endpoint
- **I.5**: Clean up redundant UI banners (one consolidated `requiredFxPairs` system)
- **I.6**: Asset currency change triggers 3 distinct toasts (delete + changedTo + sync)
- **I.7**: `FxBackwardFillInfo` extracted as standalone building block — both `FAPricePoint`
  and `FAAssetEventPointOut` now use it
- **I.8**: Remove `FAPricePoint.currency` from API response (kept in DB as forensic column).
  Frontend uses `asset.currency` as single source of truth.
- **I.11**: `AssetCurrencyChangeModal` — 3-toast + `navigationStore` stack-based back navigation

**Events currency policy:**
- `asset_events.currency` stays free (ADR: US stock paying dividends in EUR/JPY is valid)
- This is an intentional asymmetry from `price_history.currency`

## Blocco F — OHLC Sentinel

- **F.1**: Provider prices > user-cleared fields (provider wins on conflict)
- **F.2**: `_get_current_value` bootstrap: if no history exists, creates a synthetic OHLC row
- **F.3**: `_extend_ohlc_bounds`: current-price intraday extends low/high of existing day record
- **F.4**: Sentinel `-1` from provider → `None` in DB (partial upsert — `None` = "no data", not merge)
- **F.5**: Eraser 🧽 in DataEditor (`ErasableNumberCell`) + `notSet` i18n placeholder

## E.8 — Event FX Conversion

`query_events_bulk` now accepts `target_currency` and returns:
- `original_value: Optional[Currency]` — original amount + code
- `fx_rate_date: Optional[date]`
- `fx_days_back: Optional[int]`

`get_prices_bulk(include_events=True)` also applies conversion pass to events (27 lines mirrored).
Frontend tooltip: `💰 {value} (flag ISO3) 💱` / `orig. {originalValue} (origFlag origISO3)`.

## Wiki Cross-References

- [[decisions/multi-broker-atomic-tx]]
- [[decisions/tx-link-uuid-semantics]]
- [[decisions/price-currency-hard-reject]]
- [[F-046]] Transaction Model & Bulk API — updated
- [[F-051]] Transaction ↔ AssetEvent Link — events/suggest
- [[sources/phase07-part3-closure]] — continuation

## Source files

| Role | Path |
|------|------|
| Transaction service | `backend/app/services/transaction_service.py` |
| Transaction API | `backend/app/api/v1/transactions.py` |
| Asset source (prices, events) | `backend/app/services/asset_source.py` |
| Assets API | `backend/app/api/v1/assets.py` |
| Schemas (prices, assets) | `backend/app/schemas/prices.py`, `backend/app/schemas/assets.py` |
| Price chart (event tooltip) | `frontend/src/routes/(app)/assets/[id]/+page.svelte` |
| Asset currency change modal | `frontend/src/lib/components/assets/AssetCurrencyChangeModal.svelte` |
| mkdocs (transactions) | `mkdocs_src/docs/developer/architecture/database/brokers_transactions.md` |
