---
title: "`/prices/current` has a persistence side-effect — never chain with `/sync`"
category: concept
tags: [backend, frontend, assets, prices, api-contract, side-effect, anti-pattern, live-polling]
related:
  - problems/prices-current-sync-chain-empty-delta
  - concepts/daily-point-policy
  - concepts/timeseries-store-pattern
  - features/F-033
date: 2026-04-24
---

# Concept: `/api/v1/assets/prices/current` writes to the DB

## Definition

Despite its read-only-looking name and HTTP verb, the endpoint
`GET /api/v1/assets/prices/current` is **not** side-effect-free. Every call
that returns a provider quote whose `as_of_date == today` also **persists
today's OHLC row into `PriceHistory`** as part of the request.

This is implemented in:

- `backend/app/services/asset_source.py`
  → `AssetSourceManager.get_current_prices_bulk` (around line 2877)

The method's docstring states the contract explicitly:

> Side effect (F.2 + F.3): for every fetched quote whose `as_of_date` is
> today, the current OHLC point is upserted into `PriceHistory` (F.2
> bootstrap when today's row is missing, F.3 intra-day extend when it
> already exists).

So `/current` doubles as the canonical **intra-day writer** for today's
daily point. It is how live/minute ticks mature into the persisted
one-point-per-day series described in [[concepts/daily-point-policy]].

## Where it applies

Any call path that hits `AssetSourceManager.get_current_prices_bulk`:

- `GET /api/v1/assets/prices/current` (bulk live prices, used by the
  live ticker and the asset detail chart minute poll)
- Any internal caller that reuses the same bulk fetch helper

In contrast, the historical/delta writer is `sync_prices` (the `/sync`
endpoint), which returns a `changed_points` list computed by
`_count_actual_price_changes`.

## Consequence: the `/current` + `/sync` anti-pattern

Because `/current` already persisted today's row, a subsequent `/sync`
call for the same asset will find the DB already up to date and report
`changed_points = None` (empty). This looks like **"no changes"** but is
actually **"the changes just happened — by the previous request"**.

### Anti-pattern — DO NOT DO THIS

```ts
// ❌ WRONG: /current already wrote today's OHLC; /sync sees no delta.
await getCurrentPrices([assetId]);
const delta = await syncPrices(assetId); // delta.changed_points === null
```

### Correct patterns

**Live minute-tick polling on the asset detail chart** — call `/current`
only and merge the returned `FACurrentPriceItem` directly into the
in-memory chart series:

- `frontend/src/routes/(app)/assets/[id]/+page.svelte`
  → `pollCurrentPriceOnce` (extensive comment block documents why the
    silent-sync detour was removed)

**Manual "Sync" button** — call `/sync` only. Its `changed_points` delta
is authoritative *only* when the request is not preceded, in the same
flow, by a `/current` call for the same asset.

**Summary rule**: use one OR the other, never both back-to-back for the
same asset.

## Examples

### Backend (the writer)

```python
# backend/app/services/asset_source.py
class AssetSourceManager:
    async def get_current_prices_bulk(self, ...):
        """...
        Side effect (F.2 + F.3): for every fetched quote whose as_of_date
        is today, the OHLC point is upserted into PriceHistory.
        """
```

### Frontend (the correct live-polling pattern)

```ts
// frontend/src/routes/(app)/assets/[id]/+page.svelte
async function pollCurrentPriceOnce() {
  // Do NOT chain with /sync — /current already persists today's point.
  const items = await getCurrentPrices([assetId]);
  mergeTodayPointIntoChart(items[0]);
}
```

## History

Discovered during the final iteration of **I-bis #24 — "Auto-refresh
mirato post-sync"** (post-mortem v3 → v4), 2026-04-24. An earlier version
of the asset-detail live poll tried a "silent sync" detour to capture a
fresh delta after each `/current` call; it always produced an empty
`changed_points` and was removed in v4.

## Source files

| Role | Path |
|------|------|
| Backend writer (side-effect owner) | `backend/app/services/asset_source.py` (`AssetSourceManager.get_current_prices_bulk`, ~L2756, L2877) |
| Backend delta reader | `backend/app/services/asset_source.py` (`_count_actual_price_changes`) |
| Frontend live poll (correct pattern) | `frontend/src/routes/(app)/assets/[id]/+page.svelte` (`pollCurrentPriceOnce`) |
| Post-mortem | `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part3_1_Closure_2.prompt.md` (§ "I-bis #24 — Auto-refresh mirato post-sync", v3→v4 paragraph) |
| Commit message | `/tmp/libreFolio_commit_ibis24_v4.txt` |

