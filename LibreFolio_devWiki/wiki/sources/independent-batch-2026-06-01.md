---
title: "Batch 4: Five Independent Mini-Plans (Log Audit, Candlestick, FxRange, LazyImage, RSI Bands)"
category: source
source_type: plan
date_ingested: 2026-06-01
original_path: LibreFolio_developer_journal/RoadmapV4_UI/plan-independent-*.prompt.md
tags: [backend, frontend, logging, charts, fx, cache, signals, independent]
related: [features/F-076, features/F-080, features/F-086, features/F-039, features/F-072, concepts/log-level-policy, concepts/image-preview-cache-pattern]
---

# Source: Batch 4 — Five Independent Mini-Plans

## Summary

Five self-contained plans executed in parallel on 2026-06-01, each addressing a distinct improvement area with zero cross-dependencies. They span backend logging infrastructure, frontend charting (candlestick OHLCV), FX store DRY refactoring, image preview caching, and RSI signal visual enhancement. All completed in a single day, demonstrating the "independent mini-plan" workflow for non-blocking improvements.

## Plans Ingested

| Plan | Commit | Area |
|------|--------|------|
| `plan-independent-BackendLogAudit.prompt.md` | `b5a0bf9` | Backend: TRACE level + log policy + full audit |
| `plan-independent-CandlestickChart.prompt.md` | `92c0516` | Frontend: CandlestickChart.svelte + volume bars |
| `plan-independent-FxRangeHelper.prompt.md` | `f5aadec` | Frontend: ensureFxRangeLoaded DRY refactor |
| `plan-independent-LazyImageCache.prompt.md` | `ce2bc92` | Frontend: client-side image preview cache |
| `plan-independent-RsiSignalBands.prompt.md` | `6f0d4c6` | Frontend: RSI zone-driven line style |

## Key Takeaways

- **Log Level Policy**: 6 levels formalized (CRITICAL→TRACE). TRACE=5 registered in both stdlib and structlog. Practical rule: "user did X"→INFO, "system decided X"→DEBUG, "value X for date Y"→TRACE.
- **structlog TRACE bug**: `LEVEL_TO_NAME` dict didn't include level 5 → `KeyError`. Fixed by patching the dict + adding `.trace()` method to stdlib Logger.
- **Candlestick architecture**: 2-grid layout (price+volume), ECharts format is `[open, close, low, high]` (not standard OHLC order). Volume grid hidden when all values null.
- **ensureFxRangeLoaded**: Centralized gap-detect→bulk-fetch→merge pattern from 4 pages (6 inline occurrences) into one function in `fxStoreRegistry.ts`.
- **Image cache decision**: No ref counting — objectUrls held for page lifetime (~2MB for 100 images acceptable). `clearImagePreviewCache()` on logout. Higher-resolution cached images reused for lower-resolution requests via CSS object-fit.
- **RSI zone segmentation**: `renderMulti()` override splits RSI line into segments by zone (oversold/neutral/overbought). Junction points included in both adjacent segments to avoid 1px gaps. lineType selector hidden in RSI style editor.
- **Svelte 4→5 migration**: LazyImage.svelte and FileGrid.svelte migrated as part of LazyImageCache plan.

## Wiki Pages Updated

- [[features/F-076]] — status → implemented, added implementation details
- [[features/F-080]] — status → implemented, added architecture notes
- [[features/F-086]] — status → implemented, added cache decision
- [[features/F-039]] — added RSI zone band rendering notes
- [[concepts/log-level-policy]] — new: formalized log level definitions
- [[concepts/image-preview-cache-pattern]] — new: objectUrl cache with size-based reuse
- [[concepts/fx-range-helper-pattern]] — new: ensureFxRangeLoaded centralization
