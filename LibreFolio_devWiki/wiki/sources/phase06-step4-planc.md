---
type: source
group: phase06-step4-planc
ingested: 2026-05-24
git_hash: e8ab12a
covers: [F-020, F-042, F-060, F-061]
---

# Source: Phase 06 Step 4 Plan C (Currency Conversion, Multi-FX Comparison, Provider Cache)

## What this source covers

PlanC + post-validation fixes covering: backend FX-aware price queries (C1-C2), frontend chart staleness and live ticker conversion (C3-C4), comparison overlay conversion (C5), multi-FX comparison with staircase fix and per-pair banners (C4), the core-level provider cache and thread isolation architecture (plan-partC_7), and two UX refinement rounds (D, C5).

## Key decisions extracted

- **Dual price fields (`close` + `original_close`)**: Backend returns both converted and original values in one fetch. `original_close` (and `original_currency`) are populated when `target_currency` was applied; `null` means no conversion.
- **OHLC scaling by FX factor**: When converting, all four OHLC values are scaled proportionally by the `close` conversion factor — not converted individually. This preserves the candle shape even if only `close` has a direct FX rate.
- **FX staleness composited with price staleness**: `AssetBackwardFillInfo` extends `BackwardFillInfo` adding `fx_rate_date` + `fx_days_back`. The tooltip shows both independently (`⚠ Price: N days old` + `⚠ FX rate: N days old`). Chart opacity uses `max(staleDays, fxStaleDays)`.
- **Staircase fix via null gaps**: Comparison points where `original_close == null AND currency != targetCurrency` are set to `value: null` in `loadComparisonData.ts`, producing a gap in the chart instead of a cross-scale jump.
- **`sync_pairs_bulk` bug**: `_process_route()` was defined but never called — function returned `None` → 500 error. Fix: added `await asyncio.gather(...)` call and `FXSyncBulkResponse` assembly. (See also [[problems/sync-pairs-bulk-none]] if created.)
- **"Go to" opens new tab**: Navigation from signal cards uses `window.open(url, '_blank')` instead of `goto(url)` to prevent losing chart state.
- **Core-level cache wraps ALL provider calls**: Thread isolation and 5-layer cache are the core's responsibility, not individual providers'. Providers can assume sync I/O is fine — the core runs them in dedicated threads.
- **Probe bypasses all caches**: `probe_provider_config()` is always a live call — it's a dry-run test, not a real fetch.

## Key problems recorded

- **BUG: `sync_pairs_bulk` returns None** (D1): `_process_route()` inner function defined but `asyncio.gather()` never called. Hard 500. Fix: 3 lines in `fx.py`. See [[problems/sync-pairs-bulk-none]] (if created) or verify directly in `backend/app/services/fx.py`.
- **BUG: Staircase on comparison signals** (C4 Step 1): Backend returns unconverted (native currency) points mixed with converted (target currency) points when FX data is incomplete. The chart value axis mixes two scales. Fix: null-gap filtering in `loadComparisonData.ts`.
- **BUG: `fxPairCreateSlug` guard always-true** (C5 Step 1): `fxPairCreateSlug = ''` then `if (!fxPairCreateSlug)` — guard was always `true`. Fix: extract `oncreated` as named function `handleFxPairCreated`, capture `wasForComparison` before clearing.

## Features enriched

- [[F-020]] — Backend C1-C2: `target_currency` in price query, OHLC scaling, `original_currency`, `AssetBackwardFillInfo`, `convert_bulk()` integration; frontend C3-C5: chart staleness, live ticker conversion, comparison overlay conversion
- [[F-042]] — Staircase fix in `loadComparisonData.ts`, `currency`/`currencyFlag` in RenderedSignal, per-pair FX banners (`requiredFxPairs`, `FxStatusBanner`), `PageSyncAllModal` for bulk sync
- [[F-060]] — Thread isolation pattern: `_run_provider_in_thread()` wraps ALL provider calls; details of `ThreadPoolExecutor(max_workers=1)` + fresh event loop per call
- [[F-061]] — 5-layer cache architecture details: smart history range gap filling, per-date granularity, 2-level search cache (24h item / 15min query)

## Source files ingested

| File | Purpose |
|------|---------|
| `plan-partCCurrencyConversion.prompt.md` | C1-C5: backend schema changes, OHLC scaling, frontend staleness, live ticker, comparison overlays |
| `plan-partC_1_PostValidation.prompt.md` | D1-D6: sync_pairs_bulk fix, "go to" new tab, FX data gap banner, FX sync in AssetPriceSummary, sync toast with event counts, original value in CurrencySearchSelect |
| `plan-partC_4_MultiFxComparison.prompt.md` | Staircase fix, currency labels on all signals, per-pair FX banners + controls, sync-all modal (2 sections), create FX pair for comparison |
| `plan-partC_5_UxRefinement.prompt.md` | Svelte bug fix (fxPairCreateSlug guard), SearchSelect for comparison/FX, data-gap banner with asset names, signal line styles by category, banner with flags + Lucide icons, SyncModal architecture |
| `plan-partC_7_AssetProviderCoreCache.prompt.md` | Core-level thread isolation + 5-layer cache: `_run_provider_in_thread()`, smart history range gap filling, 2-level search cache, probe bypass |
