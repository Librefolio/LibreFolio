---
title: "Policy D — Destructive symmetric wipe on asset currency change"
category: decision
status: resolved
date: 2026-04-23
tags: [assets, currency, fx, prices, asset-events, transactions, fifo, destructive, backup]
related:
  - decisions/price-currency-hard-reject
  - sources/phase07-part3-closure
  - sources/phase07-part3-closure2
  - entities/backup-router
  - features/F-046
  - features/F-051
  - features/F-056
  - features/F-073
---

# Decision: Policy D — Destructive Symmetric Wipe on Asset Currency Change

> Authoritative semantics for `PATCH /assets/{id}` when the request changes
> `currency` and the asset has any price/event history. Implemented in
> commit `8fc018ab` (2026-04-23, Phase 7 Part 3 Closure Batch 3 / R3-3 / R3-3b).

## Context

After Blocco I.3 ([[decisions/price-currency-hard-reject]]) introduced the
**HTTP 409** response when a currency PATCH would invalidate existing prices,
the user-facing flow needed concrete deletion semantics for the "yes, proceed
anyway" path. Three options were debated:

1. **Policy A — keep historical rows untouched** (just flip `Asset.currency`)
   Rejected: existing prices and events were denominated in the *old* currency;
   they would silently misrepresent value forever.

2. **Policy B — convert in place** (FX-translate every row to the new currency)
   Rejected: lossy (FX rates have gaps), violates the [[concepts/single-migration-strategy]]
   "no implicit data transformation" rule, and depends on FX provider availability.

3. **Policy C — selective wipe** (delete prices only, keep manual events)
   Rejected: events still carry currency-denominated `value` fields; mixing
   old-currency events with new-currency prices would reintroduce the same
   inconsistency that triggered I.3 in the first place.

## Decision

**Policy D — destructive symmetric wipe + transaction disconnection.**

When `PATCH /assets/{id}` succeeds in changing `currency`:

| Resource | Action |
|----------|--------|
| `price_history` rows for asset | **DELETE all** |
| `asset_events` rows for asset | **DELETE all** (manual + provider-generated) |
| `transactions.asset_event_id` pointing to deleted events | **SET NULL** (rows preserved) |
| `transactions` themselves (FIFO history) | **PRESERVED** — only the event link is severed |
| `provider_assignment` row | **UPDATE** (kept), provider re-syncs from scratch |
| `Asset.currency` field | flipped to new value |

The transaction-row preservation is critical: FIFO cost-basis history (see
[[features/F-056]]) depends on the transaction stream being intact. Severing
only `asset_event_id` keeps FIFO valid while letting the orphan link be
re-resolved later (or stay null forever — the user accepted the loss when
they confirmed the destructive PATCH).

### Mandatory pre-confirm backup endpoints

Because the wipe is irreversible, a new read-only router was introduced to
let the frontend snapshot the data **before** showing the confirm dialog:

- `GET /backup/asset/{id}/prices` — full price history (CSV/JSON)
- `GET /backup/asset/{id}/events` — full event history with FX backfill columns
- `GET /backup/fx/{base}/{quote}/rates` — FX pair rates (respecting normalised
  pair direction)

The frontend `AssetCurrencyChangeModal` calls `/backup/asset/{id}/prices` and
`/backup/asset/{id}/events`, offers the user a download, and only then enables
the "Confirm destructive change" button. See [[entities/backup-router]] for
the full router definition; the backup router is the per-series implementation
of [[features/F-073]] (Backup & Restore).

## Consequences

**Gained**:
- Single deterministic semantic — no ambiguous "old currency" rows linger.
- Predictable FIFO behaviour (transaction rows survive).
- User has a chance to save a snapshot before destruction.
- Simple to test (G-batch6 covered the wipe end-to-end).

**Traded off**:
- All historical prices/events for the asset are gone after a currency change.
  The provider must re-sync from scratch in the new currency, which loses
  any data older than the provider's available history window.
- Manual events (e.g. user-entered dividends) are wiped along with provider
  events — Policy D is intentionally symmetric. Distinct from `#R6-4`
  (scheduled-investment param-change wipe) which preserves manual events.

## Comparison with #R6-4 (scheduled-investment param change)

| Aspect | Policy D (currency change) | #R6-4 (schedule-param change) |
|--------|---------------------------|-------------------------------|
| Trigger | `PATCH Asset.currency` | `scheduled_investment` provider params change |
| Prices | wiped | wiped |
| Provider-generated events | wiped | wiped |
| Manual events | **wiped** | **preserved** |
| Transactions → events | `asset_event_id = NULL` | `asset_event_id = NULL` |
| Transactions | preserved | preserved |
| Provider assignment row | UPDATE (re-sync from zero) | UPDATE (re-generate schedule) |

The asymmetry is intentional: a currency change invalidates the meaning of
every amount, regardless of source. A schedule-param change only invalidates
provider-generated content; manual user input remains semantically valid.

## Bug surfaced during Policy D test coverage

`assets.py::market_data_summary` and `wipe_market_data` both used
`AssetSourceError.code` (non-existent attribute) instead of `error_code`,
raising HTTP 500 instead of 404. Fixed in G-batch6 — see
[[problems/assets-wipe-error-attr-mismatch]].

## Source files

| Role | Path |
|------|------|
| Wipe service | `backend/app/services/asset_source.py::wipe_market_data_for_currency_change` |
| PATCH handler | `backend/app/api/v1/assets.py` (currency-change branch) |
| Backup router | `backend/app/api/v1/backup.py` |
| Currency-change modal | `frontend/src/lib/components/assets/AssetCurrencyChangeModal.svelte` |
| Test (wipe) | `backend/test_scripts/test_api/test_market_data_wipe.py` |
| Test (backup endpoints) | `backend/test_scripts/test_api/test_backup_export_extras.py` |
| Test (PATCH 409 + flow) | `backend/test_scripts/test_api/test_asset_currency_change.py` |

