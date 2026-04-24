---
type: source
group: phase06-step4-plana
ingested: 2026-05-24
git_hash: e8ab12a
covers: [F-033, F-037, F-042, F-043]
---

# Source: Phase 06 Step 4 Plan A (Asset Detail Page, Chart Polish, Signal Unification)

## What this source covers

Plan0 + PlanA bugfix rounds covering: (0) Asset list parity with FX list + AssetComparisonSignal creation; (A) full implementation of the asset detail page at `/assets/[id]`; chart/layout redesign; event markers on chart; signal label unification across tooltip/measure panel; FX wiring for comparison signals; default `%` view mode.

## Key decisions extracted

- **Asset detail mirrors FX detail**: The `/assets/[id]/+page.svelte` is modelled after `/fx/[pair]/+page.svelte` — same signal overlay pattern, same responsive layout helper, same foldable panels, same measure tool. Code duplication was then reduced by extracting `loadComparisonData.ts`.
- **Signal label unification via `signalLabel.ts`**: All signal display (tooltip, measure panel, legend) goes through a single `SignalLabelInfo`/`signalLabelToHtml()` utility. Removes hardcoded emojis (e.g. `📊`) from `getLabel()` and centralises icon resolution. See [[decisions/signal-label-unification]].
- **`RenderedSignal` enriched with metadata**: `iconUrl?`, `assetType?`, `currency?`, `currencyFlag?` added to `RenderedSignal` so downstream consumers (MeasurePanel, tooltip) don't need to re-resolve asset info.
- **Panel layout redesign**: Aesthetics panel moved from above-chart foldable to vertical toolbar (⚙️/✏️/📏 icons) on the left side of the chart. Signals panel takes the slot where Aesthetics was.
- **`viewMode` defaults to `'percentage'`**: Both asset detail and FX detail default to percentage view — users usually compare trends, not absolute values.
- **`loadComparisonData.ts` shared utility**: Asset and FX detail pages shared identical `query_prices_bulk` + `_resolvedData` injection logic for comparison signals. Extracted to avoid divergence.
- **INDEX removed from `PNG_MAP`** (and `index.png` deleted): INDEX is a virtual benchmark type — it has an icon but is NOT a real purchasable asset.
- **FX auto-sync after pair creation from asset detail**: When user creates a new FX pair from asset detail page, the system auto-syncs rates in the current date range and updates `displayCurrency`.
- **F5 Two-Panel layout cancelled**: The Two-Panel Split layout for ProviderAssignmentSection was removed at the user's request.

## Key problems recorded

- **BUG: `effect_update_depth_exceeded` in ModalBase.svelte** (Bugfix 1): `tick()` in Svelte 4 reactive caused `flushSync()` recursion with Svelte 5 `$effect`. Fix: replace `tick().then(...)` with `requestAnimationFrame(...)` in ModalBase; wrap AssetModal `$effect` body in `untrack()`.
- **BUG: Classification "Loading..." forever** (Bugfix 6, §1): Bitcoin and assets without distributions had no `classification_params` — the loading state never cleared. Fix: add `classificationLoaded` flag, show "No classification data" on completed-but-empty.
- **BUG: Chart colors not updating without F5** (Bugfix 3, Issue 1): MutationObserver not added to `SectorPieChart` / `GeographyMap`. Fix: add MutationObserver in `onMount()`.
- **BUG: Navigation between assets leaves old classification charts** (Bugfix 6, §6): `reloadMetadata()` didn't reset the loading flag. Fix: set `classificationLoaded = false` before re-fetch.

## Features enriched

- [[F-033]] — Full asset detail page implementation: state management, onMount parallel loading, event markers (A6), panel/toolbar redesign, edit modal integration, responsive filter bar
- [[F-037]] — Signal Library: `signalLabel.ts`, `RenderedSignal` enrichment, `loadComparisonData.ts`, signal line styles by category, MeasurePanel refactor
- [[F-042]] — FX Pair Comparison Signal: `currency`/`currencyFlag` in RenderedSignal, injected `_assetCurrency`
- [[F-043]] — Asset Comparison Signal: `iconUrl`/`assetType`/`currency` injected from parent page; emoji removed from `getLabel()`

## Source files ingested

| File | Purpose |
|------|---------|
| `plan-phase06Step4Part0-AssetListParityAndBugfixes.prompt.md` | Asset card parity with FX card (signals, %, settings button), AssetComparisonSignal creation |
| `plan-phase06Step4PartA-AssetDetailPage.prompt.md` | Asset detail page A1-A10: scaffold, state, chart, filter bar, metadata, i18n, event markers progress |
| `plan-phase06Step4PartA-Bugfix_3_ChartLayoutToastPanel.prompt.md` | Panel redesign (Bugfix 3–5): vertical toolbar, MutationObserver charts, toast/tooltip FX warning |
| `plan-phase06Step4PartA-Bugfix_6_ClassifTooltipEventMarkers.prompt.md` | Classification loading fix, FX warning→tooltip, user_url positioning, A6 event markers spec |
| `plan-phase06Step4PartA-Bugfix_7_EventMarkersFxAutoSync.prompt.md` | A6 event markers implementation + FX auto-sync from asset detail |
| `plan-phase06Step4PartA-Bugfix_8_SignalLabelUnificationFxWiringDefaultPercent.prompt.md` | Signal label unification (signalLabel.ts), RenderedSignal enrichment, FX detail wiring, default % viewMode |
