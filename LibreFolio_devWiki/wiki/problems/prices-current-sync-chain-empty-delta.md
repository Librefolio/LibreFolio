---
title: "Chaining `/prices/current` + `/sync` always returns empty `changed_points`"
category: problem
status: resolved
date: 2026-04-24
tags: [backend, frontend, assets, prices, api-contract, side-effect, live-polling, anti-pattern]
related:
  - concepts/prices-current-side-effect
  - concepts/daily-point-policy
  - features/F-033
---

# Problem: `/current` then `/sync` reports "no changes" that actually happened

## Symptom

On the asset detail page, the live minute poll was implemented as:

1. `await getCurrentPrices([assetId])` to get the latest quote
2. `await syncPrices(assetId)` as a "silent sync" to capture the delta
   (`changed_points`) and drive a targeted chart refresh.

Step 2 consistently returned `changed_points = None` (empty), so the
chart appeared to never need updating — even though the tick had clearly
moved. Visually the chart was stale until a manual sync or page reload.

## Root Cause

`GET /api/v1/assets/prices/current` is **not** read-only. Its backend
implementation, `AssetSourceManager.get_current_prices_bulk`
(`backend/app/services/asset_source.py`, ~L2877), performs an F.2/F.3
side-effect: for every fetched quote whose `as_of_date == today`, it
upserts today's OHLC row into `PriceHistory` as part of the same request.

By the time `/sync` runs, the DB is already current. `_count_actual_price_changes`
compares provider data to DB and correctly finds no delta — because
`/current` just applied it.

See [[concepts/prices-current-side-effect]] for the full contract.

## Solution

Remove the silent-sync detour. Use **one** endpoint per responsibility:

- **Live minute poll on the detail chart**: call `/current` only, use the
  returned `FACurrentPriceItem` directly to merge today's point into the
  in-memory chart (`pollCurrentPriceOnce` in
  `frontend/src/routes/(app)/assets/[id]/+page.svelte`).
- **Manual "Sync" button**: call `/sync` only. Its `changed_points` is
  authoritative when not preceded by a `/current` call for the same asset.

Landed in I-bis #24 v4 (2026-04-24).

## Prevention

- **Never chain `/current` + `/sync`** for the same asset in the same flow.
- Treat `/current` as both a reader *and* an intra-day writer — that is
  its contract, documented in the method docstring and in
  [[concepts/prices-current-side-effect]].
- When adding a new caller of `AssetSourceManager.get_current_prices_bulk`,
  assume it writes; plan the UI update from the returned payload, not
  from a follow-up sync.

## Impact

- 3 plan iterations of I-bis #24 (v1→v4) chasing a "phantom" empty-delta
  bug before the side-effect was identified.
- The frontend carries an extensive comment block in
  `pollCurrentPriceOnce` to prevent the anti-pattern from being
  reintroduced by a future refactor.

## Source files

| Role | Path |
|------|------|
| Backend writer (root cause) | `backend/app/services/asset_source.py` (`AssetSourceManager.get_current_prices_bulk`, ~L2877) |
| Frontend fix | `frontend/src/routes/(app)/assets/[id]/+page.svelte` (`pollCurrentPriceOnce`) |
| Post-mortem | `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part3_1_Closure_2.prompt.md` (§ "I-bis #24 — Auto-refresh mirato post-sync", v3→v4) |
| Commit message | `/tmp/libreFolio_commit_ibis24_v4.txt` |

