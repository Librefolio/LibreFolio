---
title: "Signal Label Unification (signalLabel.ts utility)"
category: decision
status: resolved
date: 2026-04-10
tags: [frontend, signals, charts, ui, refactor]
related: [features/F-037, features/F-033, features/F-042, features/F-043]
---

# Decision: Signal Label Unification

## Context

Before this decision, signal visual labels were inconsistent across three different consumer contexts:

1. **`PriceChartFull.svelte` tooltip**: Used a colored dot (`●`) + series name string — no icons, no asset type images.
2. **`MeasurePanel.svelte`**: Accepted a single `pairLabel: string` prop for the main series; overlay signals had no icon resolution.
3. **`AssetComparisonSignal.getLabel()`**: Hardcoded `📊 {assetName}` — emoji was fine in plain-text contexts but wrong in tooltip HTML and measure panel rows.
4. **`FxPairSignal.getLabel()`**: Used `💱 {slug}` emoji prefix.

As the number of overlay signal types grew (asset comparison, FX pair comparison, benchmarks), the inconsistency became visible: tooltips showed raw emojis where icon `<img>` tags should appear, and the measure panel couldn't differentiate signal types visually.

## Options Considered

1. **Per-component ad-hoc label rendering** — each component resolves its own icon logic. Simple short-term but diverges over time.
2. **`RenderedSignal` carries display metadata** — enrich the existing `RenderedSignal` type with `iconUrl?`, `assetType?`, `currency?`, `currencyFlag?` so consumers don't re-resolve. But the tooltip `formatter` works on `seriesName` (string), not `RenderedSignal` instances — needs a lookup map.
3. **Unified `signalLabel.ts` utility + enriched `RenderedSignal`** — single source of truth. `signalLabelToHtml()` generates consistent HTML for any consumer; `buildOverlaySignalInfoMap()` builds the name→info lookup the tooltip needs.

## Decision

**Option 3**: create `frontend/src/lib/charts/signalLabel.ts` with `SignalLabelInfo` struct and two functions. Simultaneously enrich `RenderedSignal` with the metadata fields. Remove all hardcoded emojis from `getLabel()` in comparison signals.

```typescript
// signalLabel.ts
export interface SignalLabelInfo {
    label: string;
    iconUrl?: string | null;
    assetType?: string | null;
    color?: string;
    currency?: string;
    currencyFlag?: string;
    isCrown?: boolean;
}
export function signalLabelToHtml(info: SignalLabelInfo, truncateAt?: number): string
export function signalLabelToText(info: SignalLabelInfo): string
export function buildOverlaySignalInfoMap(overlaySignals: ...): Map<string, SignalLabelInfo>
```

## Consequences

- `ChartSignal.ts` — `RenderedSignal` gained `iconUrl?`, `assetType?`, `currency?`, `currencyFlag?`
- `AssetComparisonSignal.ts` — `getLabel()` returns plain name (no emoji); `render()` populates `iconUrl`/`assetType` from injected `_assetIconUrl`/`_assetType` params
- `MeasurePanel.svelte` — `pairLabel: string` prop replaced by `mainSignalInfo: SignalLabelInfo`
- `PriceChartFull.svelte` — tooltip `formatter` uses `signalLabelToHtml()` via `overlaySignalInfoMap` prop (built by parent pages)
- Both asset detail and FX detail pages now build and pass `overlaySignalInfoMap` and `mainSignalInfo`
- `loadComparisonData.ts` injects `_assetIconUrl`/`_assetType` into comparison signal params at load time

## Links

- [[features/F-037]] Signal Library Framework (framework change)
- [[features/F-033]] Asset Detail Page (consumer)
- [[features/F-042]] FX Pair Comparison Signal (consumer)
- [[features/F-043]] Asset Comparison Signal (primary beneficiary)
- Source: `developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step4/PlanA/plan-phase06Step4PartA-Bugfix_8_SignalLabelUnificationFxWiringDefaultPercent.prompt.md`

## Source files

| Role | Path |
|------|------|
| Utility | `frontend/src/lib/charts/signalLabel.ts` |
| Abstract signal base | `frontend/src/lib/charts/signals/ChartSignal.ts` |
| Asset comparison signal | `frontend/src/lib/charts/signals/AssetComparisonSignal.ts` |
| Measure panel | `frontend/src/lib/components/charts/MeasurePanel.svelte` |
| Price chart (tooltip consumer) | `frontend/src/lib/components/charts/PriceChartFull.svelte` |
