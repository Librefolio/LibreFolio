\\  # Chart Animations

How we implement smooth transitions in LibreFolio's ECharts-based charts.

## Architecture

```
echartsAnimationConfig.ts          ← Centralized config + helpers
├── CHART_ANIMATION_CONFIG         ← Timing/easing settings
├── CHART_SET_OPTION_OPTS          ← setOption flags (notMerge/replaceMerge)
└── namedPoint(date, value)        ← Named data point for shift animation
```

## Two Animation Strategies

### 1. Dashboard charts (GrowthChart, AllocationHistoryChart)

These use **shift animation** — when the time period changes, shared dates translate
to new positions and new dates appear/disappear smoothly.

**Requirements:**

- `xAxis: { type: 'time' }` — ECharts understands temporal coordinates
- Data as `namedPoint(date, value)` → `{name: date, value: [date, val]}`
- Partial `setOption({series: [...]})` on data-only updates (no full option rebuild)
- Full `setOption(option, CHART_SET_OPTION_OPTS)` only on init or mode/dark change

**Key insight** (from ECharts developers):

> ECharts performs shift animation if it recognizes part of the old data in the new
> data. This matching is done via the `name` property on each data point.

```typescript
// echartsAnimationConfig.ts
export function namedPoint(date: string, value: number | null) {
    return {name: date, value: [date, value]};
}
```

**Partial vs Full update pattern:**

```typescript
// GrowthChart.svelte — renderChart()
const needsFullInit = lastRenderedMode !== viewMode || lastRenderedDark !== isDark;

if (!needsFullInit && chartInstance) {
    // Data-only: ECharts diffs named points → shift animation
    chartInstance.setOption({
        series: seriesData.map(s => ({name: s.name, data: s.data})),
    });
} else {
    // Full init: axes, tooltip, legend, series
    chartInstance.setOption(fullOption, CHART_SET_OPTION_OPTS);
}
```

### 2. Detail page charts (LineChart, CandlestickChart, PriceChartFull)

These use **instant rendering** (`animation: false`) because:

- Complex segmented series (baseline coloring, stale gradient) create N sub-series
  with variable count between renders
- ECharts cannot reliably match segments across period changes
- The visual priority is precision, not animation

For these charts, the UX pattern is: **keep old data visible until new data arrives**
(stale-while-revalidate at the store level), then swap instantly.

## Pie Charts (AllocationPieChart)

Uses **segment morph** animation:

- Partial `setOption({series: [{data: [{name, value}]}]})` for data updates
- ECharts matches pie segments by `name` → animates area transitions
- Full option only on init or dark mode change

## Numeric Values (TweenedValue)

The `TweenedValue.svelte` component interpolates between numbers:

```svelte
<TweenedValue value={navAmount} format={(v) => formatMoney('EUR', v)} />
```

- Uses Svelte's `tweened()` store with `cubicOut` easing
- Default duration: 900ms
- Applied to: 3 hero KPI values + 11 metric bar values = 14 animated numbers

## KPI Bars (CSS transitions)

- `KpiMetricBar`: bar width + marker position animate via `transition-all duration-700`
- `KpiDivergingFlowBar`: deposit/withdraw bars animate independently
- Color changes: `transition-colors duration-300`

## Stale-While-Revalidate Pattern

Dashboard loading states are designed to never blank the screen on subsequent visits:

```typescript
// summaryLoading only true when NO data exists yet
let summaryLoading = $derived(reportLoading && !summary);
```

When the user changes period:
1. Old data stays visible (summaryLoading = false because summary ≠ null)
2. Backend fetch runs in background
3. New data arrives → reactive updates trigger → charts animate to new values

## Configuration Reference

```typescript
// echartsAnimationConfig.ts
export const CHART_ANIMATION_CONFIG = {
    animation: true,
    animationDuration: 600,        // New elements enter
    animationDurationUpdate: 800,  // Existing elements update
    animationEasing: 'cubicOut',
    animationEasingUpdate: 'cubicOut',
};

export const CHART_SET_OPTION_OPTS = {
    notMerge: false,               // Enable diffing against previous state
    replaceMerge: ['series'],      // Replace series (matched by name) with animation
};
```

## DOM Persistence

Chart containers must **never** be destroyed between data updates:

```svelte
<!-- ✗ WRONG: container destroyed when loading changes -->
{#if loading}
    <Skeleton />
{:else}
    <div bind:this={chartContainer}></div>
{/if}

<!-- ✓ CORRECT: container always present, skeleton as overlay -->
<div class="relative">
    {#if loading}
        <div class="absolute inset-0 z-10"><Skeleton /></div>
    {/if}
    <div bind:this={chartContainer} class:invisible={loading}></div>
</div>
```

If the DOM element is destroyed, the ECharts instance is lost and must be recreated
from scratch — eliminating any possibility of transition animation.
