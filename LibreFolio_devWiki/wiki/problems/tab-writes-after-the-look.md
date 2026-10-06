---
title: "The tab that writes after the look — contamination ends with the connection, not with the observer"
category: problem
status: workaround
date: 2026-09-23
tags: [testing, method, lanes, contamination, prices, side-effect, browser, measurement]
related:
  - concepts/span-as-a-detector
  - concepts/prices-current-side-effect
  - problems/discarded-risk-answer-read-as-empty
---

# Problem: the tab that writes after the look

> Declared in R2-101; filed 2026-09-23 from R2-98 (18/09), with S5's passo 1e and the family
> entries R2-74, R2-111 and R2-115.

## Symptom (18/09, S5's lane `6167`)

The coordinator had revoked the standing instruction "leave the server up" and ordered
*stop → prove the port → repopulate*. S5 took the fingerprint **before** killing the process —
*"because once it is dead, nobody says it any more"* — and found a late burst at `18:43:47Z`,
not the one already known (`18:22:45Z`). The scheduler was proven off
(`"Scheduler disabled via LIBREFOLIO_NO_SCHEDULER — loop not started"`), so the server was not
acting on its own. The log named the author:

```
POST /api/v1/assets/prices/current   ×8, from 8 distinct ephemeral ports (61241…62572)
18:44:15.902Z  "Current-price persist: processing 14 fresh provider quote(s) … (existing rows today: 14)"
18:44:15.903Z  14 × "[Intra-day price extend] … patch_fields=['close']"
18:44:15.907Z  "commit OK (14 row(s) written/updated)"
at shutdown:   2 connections ESTABLISHED on 6167
```

It wrote a minute after the order to stop.

## Root cause

As recorded: ***"the act that writes is not the decision to look: it is the connection that
stays open."*** A browser tab left open keeps rewriting after the look is over. Rule Ⓓ —
*measuring the data and looking at the app in the same lane are incompatible* — was too weak: it
treated looking as an event with an end.

**The writer, in code** (verified 2026-09-23; the registry names it only as "the tab"). The
Assets page, where the visual gate was run, has a live-price `$effect`: while the page's date
range ends today it calls `fetchLivePrices()` on mount and then every 30 s, and each call is a
`POST /api/v1/assets/prices/current` for the page's assets. That endpoint persists: for every fresh
quote dated today it bootstraps today's `price_history` row or extends it — `_extend_ohlc_bounds`
widens `low`/`high` to cover the new `close`, then `close` is overwritten and `fetched_at`
re-stamped. The `Current-price persist` and `[Intra-day price extend]` lines above come from there
(`price_query.py`). That is the signature R2-64 found — a new `close`, `high` widened, `open`/`low`/
`volume` untouched — which R2-64 attributed to the equivalent bounds merge in `price_store.py`. One
request carrying 14 quotes fits the list page; the asset-detail poll sends a single id. The poll
stops when the page is left, the range stops including today, or the server goes away — not when
anyone stops looking.

## Solution (as recorded)

- **Stopping the server is not hygiene: it is the remedy.**
- The corrected order: **repopulate → measure → look → close the tab and stop the server →
  discard the lane.**
- Proved, not declared: `kill` → `lsof -nP -iTCP:6167` (no listener, no connection) →
  `db populate --force --clean` → span 5 885 s → **0.1 s**, N's detector 10 → **0**, assets with a
  single price 7 → **0**, assets with history 16/17 → **9/17**.
- The repopulation gave back the fact the visit had destroyed: **8 of 17 assets without prices** —
  the property of the generator on which the coordinator had chosen the gate's assets (R2-74).

## Prevention

- Treat looking as a write and budget for it (R2-74: *"looking is a write"*).
- Before any numeric measurement on a lane a browser has touched: close the tab, stop the server,
  prove the port free with `lsof`, repopulate, then run the span gate —
  [[concepts/span-as-a-detector]].
- Collect provenance while the process is alive: dead, it testifies to nothing.
- Keep an irreproducible artefact out of `/tmp` and out of the data dir (R2-115). The only proof of
  this finding, S5's `server.log`, was kept on purpose and left in `/tmp`: *the knowledge survives
  in R2-98; the proof does not.*

## The family — verifying mutates what the next verification reads

| entry | the act | what it changed |
|---|---|---|
| R2-74 | looking | created history: 8 assets with zero prices → 7 with exactly one, today's — and one observation has zero variance |
| **R2-98** | leaving the tab open | kept writing after the look |
| R2-111 | `services risk-all` | runs `db create-clean`: the gate empties the lane the next gate reads |
| R2-115 | `sqlite3` on a wrong path | opens for writing and materialises a 0-byte file; `file:…?mode=ro` cannot |

## Impact

What browser writes into measured lanes cost this campaign, during the look and after it:

- A lane that has been looked at is not equal even to itself: each visit rewrites today's row
  (R2-68).
- One shared anomalous point (+30 % and +217 % on the same day) dominated a 32-observation
  covariance and decayed with the window exactly like a tail artefact (R2-64) — R2-61's "recent
  correlations are a tail artefact" was retracted because of it.
- The log that proved this finding is gone (R2-115).

## Source files

| Role | Path |
|------|------|
| Live-price `$effect` — on mount, then every 30 s while the range ends today | `frontend/src/routes/(app)/assets/+page.svelte` |
| `POST /api/v1/assets/prices/current` from the client | `frontend/src/lib/services/livePriceService.ts` |
| The endpoint | `backend/app/api/v1/assets.py` |
| The `/prices/current` writer — F.2 bootstrap, F.3 intra-day extend (`_extend_ohlc_bounds`); the log lines above | `backend/app/services/asset_sources/price_query.py` |
| The equivalent bounds merge R2-64 cited (bulk upserts); every write stamps `fetched_at` | `backend/app/services/asset_sources/price_store.py` |
| Rule Ⓓ, the order, the gate | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/_comune.md` |
| The measurement — passo 1e, *Fuori pista* 1 | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/progress/S5-esecuzione.md` |
| Registry — R2-64, R2-68, R2-74, R2-98, R2-101, R2-111, R2-115 | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/REGISTRO.md` |
