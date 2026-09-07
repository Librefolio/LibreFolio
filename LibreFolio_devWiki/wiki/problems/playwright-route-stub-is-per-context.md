---
title: "page.route() binds one browser context, not the suite"
category: problem
status: resolved
date: 2026-08-31
tags: [frontend, testing, playwright, parallelism, global-state]
related: [concepts/test-isolation-classes, concepts/transaction-hygiene-fixture, concepts/load-only-red-is-a-product-defect]
---

# Problem: stubbing a write does not stop the other workers from writing

## Symptom

`asset-modal.spec.ts` — *"switching away from a parametric provider … only
destroys on confirm"* — failed **only in the full run**:

```
Error: confirming the switch must discard the invented series
Expected: 0
Received: 1
```

Green in isolation (15 passed). Green for the whole category, even at
`--workers 4`. Red once, in a 50-minute run of all fifteen categories.

## Root cause

The test creates an asset, seeds a parametric price series, switches provider,
and asserts the series was destroyed by reading the **total** stored price count
from `GET /assets/{id}/market-data/summary`.

It defends itself carefully against the writers it knows about, stubbing
`prices/sync` and `prices/current` — the latter because `get_current_prices_bulk`
performs an OHLC write-back that creates today's row on every successful fetch,
so *displaying* an asset writes to it.

But `page.route()` intercepts **the context that installs it**, and `Asset` and
`PriceHistory` carry **no `user_id`**. The asset this test creates is visible to
every other worker. Any worker rendering the asset list fetches current prices
for all assets — this one included — and writes today's row through a context
the test cannot reach.

The backend log of the failing run states it plainly:

```
"event": "Current-price persist: commit OK (14 row(s) written/updated)"   ×217
```

Fourteen being every asset in the database.

So the assertion was on a number with **several authors** — the classic "never
assert a count you did not create", except the count looked private because the
asset was created by the test.

## Why "it passes in isolation" proved nothing

Serialising removes the other authors instead of removing the assumption. The
three green runs (isolated, category, category at 4 workers) were all evidence
about a world with fewer writers, not about the assertion being sound.

## Fix

Count only rows dated inside the invented series' window, read **verbatim** from
the backup stream, which returns one row per `(asset_id, date)` with no
backward-fill:

```
GET /api/v1/backup/asset/{id}/prices?format=json  →  {rows: [{date: "YYYY-MM-DD", …}]}
```

The window `2024-01-15 → 2026-01-15` is entirely in the past, and the only row a
stranger can create is **today's**. So a row inside the window after the wipe can
only be a survivor: the assertion is true by construction rather than by luck.
The window bounds are constants shared by the seed and the assertion, so they
cannot drift apart, and the test verifies the window is in the past rather than
assuming it.

Polling the **dates** instead of a number also makes the failure name the
survivors.

Falsification confirmed the diagnosis numerically: moved before the confirm, the
assertion fails listing **25 dates** — the series' real size — which proves the
single survivor had been today's row all along.

## Generalisation

`page.route()`, `page.on()`, and every other interception is **per context**. On
any table without a `user_id` — `Asset`, `Transaction`, `PriceHistory`, `FxRate`,
`Broker`, all settings tables — an interception is a statement about your own
traffic, never about the row.

## Source files

| Role | Path |
|------|------|
| Test | `frontend/e2e/assets/asset-modal.spec.ts` (~line 418) |
| Verbatim read precedent | `frontend/e2e/fx/fx-destructive.spec.ts` (~line 97) |
| The write-back | `get_current_prices_bulk` — OHLC write-back F.2/F.3 |
| Isolation classes | `scripts/test_runner/_inventory.py` |

## See also

- [[concepts/test-isolation-classes]] — why a table without `user_id` forces
  `WRITE_GLOBAL` and cannot be made parallel-safe by stubbing.
- [[concepts/transaction-hygiene-fixture]] — the same reasoning applied to
  cleanup: ownership must be an intersection of two facts, never an inference
  from timing.
- [[concepts/load-only-red-is-a-product-defect]] — this red only appeared in the
  full run, and it was real.
- [[sources/frontend-parallelism-tappe-7-11]] — the lane that produced it.
