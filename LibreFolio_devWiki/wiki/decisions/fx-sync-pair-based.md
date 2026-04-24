---
title: "FX Sync Redesign: Currency-Based → Pair-Based"
category: decision
status: resolved
date: 2026-03-06
tags: [fx, api, sync, breaking-change]
related_features: [F-017, F-016, F-018]
---

# Decision: FX Sync API — Pair-Based Bulk Sync

## Context
The original FX sync endpoint (`GET /api/v1/fx/currencies/sync`) accepted a flat list of **currencies** (e.g. `USD,GBP,CHF`). The backend derived pairs from these, causing ambiguity and generating spurious "cartesian" pairs that didn't exist in the user's configuration.

## Problem with old design
1. **Ambiguity**: passing `USD,GBP,CHF` — the backend didn't know which pairs to sync (EUR/USD? USD/GBP? all combinations?)
2. **Vague response**: returned only `synced: N` and `currencies: [...]` — no per-pair info
3. **Spurious pairs**: backend generated cartesian pairs (`c1 < c2`) not in user config
4. **No provider info**: if a pair fell back to a secondary provider, the frontend had no visibility

## Decision
Replace with `POST /api/v1/fx/currencies/sync` accepting explicit **pair list** with per-pair results.

**Breaking change**: GET → POST. Old GET endpoint removed.

## New design
- Request: `{ pairs: ["EUR-USD", "EUR-GBP"], start: date, end: date }`
- Pair normalization: alphabetical order enforced server-side (USD-EUR → EUR-USD)
- Response: per-pair `{ pair, status, provider_used, points_fetched, points_changed, message }`
- Summary: `{ ok: N, partial: N, failed: N }`

## Why pair-based
- User controls exactly which pairs are synced
- Frontend can show granular feedback (provider used, data points changed)
- No surprise implicit pairs
- Consistent with the `FxConversionRoute` model which is pair-centric

## Resolved
✅ Completed 2026-03-12 — `plan-fxSyncApiRedesign.prompt.md`

## Source files

| Role | Path |
|------|------|
| FX service (sync logic) | `backend/app/services/fx.py` |
| FX providers directory | `backend/app/services/fx_providers/` |
| DB model (FxConversionRoute) | `backend/app/db/models.py` |
| mkdocs | `mkdocs_src/docs/developer/backend/fx/architecture.md` |
