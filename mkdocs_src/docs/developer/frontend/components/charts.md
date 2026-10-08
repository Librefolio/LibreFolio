# Chart Animations

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
- Partial `setOption` on data-only updates: each series is sent as `{name, data}` only (no full option rebuild)
- Full `setOption` only when something the partial update cannot express has changed (see below)

**Key insight** (from ECharts developers):

> ECharts performs shift animation if it recognizes part of the old data in the new
> data. This matching is done via the `name` property on each data point.

```typescript
// echartsAnimationConfig.ts
export function namedPoint(date: string, value: number | null) {
    return {name: date, value: [date, value]};
}
```

**Partial vs Full update pattern** (`lib/components/dashboard/GrowthChart.svelte`, used by the
Dashboard and Broker detail):

```typescript
// GrowthChart.svelte — renderChart(forceFullXAxisRebuild = false)
const renderedModeKey = viewMode === 'pnl' ? `pnl:${pnlSubmode}` : viewMode;
const masked = shouldMaskAmount();
const needsFullInit =
    forceFullXAxisRebuild ||
    lastRenderedMode !== renderedModeKey ||
    lastRenderedDark !== isDark ||
    lastRenderedMasked !== masked;

if (needsFullInit) {
    // Axes, tooltip, legend, series: setOption(option, CHART_FULL_UPDATE_OPTS)
    applyFullOption(isDark, buildFullSeries(isDark, seriesData), zoomWindow);
} else {
    // Data only, {name, data} per series: setOption({...}, CHART_SERIES_UPDATE_OPTS)
    updateChartData(activeData, isDark, zoomWindow, false, logicalRange.startDate);
}
```

| Full rebuild trigger | Why the partial update is not enough |
|---|---|
| `renderedModeKey` | The mode (`eur`, `pct`, `pnl`) and, in `pnl`, the submode: the series *type* changes (line, candlestick, bar), which `{name, data}` cannot express. |
| `isDark` | Colours are set once, in the full option. |
| `masked` | The privacy toggle: ECharts caches the axis labels, so the tick formatter has to run again. The tooltip formatter reads the flag on every hover. |
| `forceFullXAxisRebuild` | The x-axis leaves its compact layout (a narrow container widening on resize). |

The two flag sets differ on purpose:

- `CHART_SERIES_UPDATE_OPTS = {notMerge: false, replaceMerge: ['dataZoom']}` — `series` must
  **not** be in `replaceMerge` here: the partial update sends only `{name, data}`, and replacing
  the matched series would drop the type and styles set by the full option, leaving a blank chart.
- `CHART_FULL_UPDATE_OPTS = {...CHART_SET_OPTION_OPTS, replaceMerge: ['series', 'xAxis']}`.

A resolution switch (daily ↔ weekly/monthly, chosen from the zoom) goes through the partial path
without animation, after hiding the tooltip.

**Privacy redraw.** The render runs inside `tick().then(…)`, where reading a store registers no
dependency, so the render `$effect` reads `shouldMaskAmount()` itself: toggling privacy re-runs it,
and the changed `masked` value forces the full rebuild. The y-axis ticks mask the digits and keep
the sign outside the mask and the `k`/`M` suffix inside it. The general rule is in
[ECharts formatters](../state/app-state.md#privacy-echarts).

#### P&L submodes

The `pnl` mode has three submodes (`pnlSubmode`). The mode and the submode persist per user
(`dashboard-growth-mode`, `dashboard-growth-pnl-submode`), shared by Dashboard and Broker detail.

| Submode | Series | x-axis |
|---|---|---|
| `line` | Total P&L split by sign into two series (zero crossings interpolated), a dashed reference line flat at the first visible day's P&L (`__pnlReference__`, left out of the legend), and one line per broker | Time axis, shift animation |
| `candles` | One candlestick series of the total P&L, without broker overlay. A gap is ECharts' empty value `'-'`: a `null` item crashes the candlestick series on a category axis | Category axis (the ladder) |
| `income` | Six bar series in three columns per bucket: the income stack (dividends and interest above zero, costs below), deposits, and acquisitions split between new capital and reinvested returns | Category axis (the ladder) |

**The ladder** (Candles and Income) draws on a category axis, one slot per bucket, so every
candle body and bar gets the same width at any zoom; its labels and separators come from a ladder
plan instead of the responsive time-axis policy. The candle widths offered depend on the measured
plot width (`availableCandleWidths`) and are not persisted. A partial first bucket is drawn faded
in both. Each submode keeps a fixed number of series in a fixed order, which the partial update
relies on across zoom and pan.

### 2. Detail page charts (LineChart, CandlestickChart, PriceChartFull)

These use **instant rendering** (`animation: false`) because:

- Complex segmented series (baseline coloring, stale gradient) create N sub-series
  with variable count between renders
- ECharts cannot reliably match segments across period changes
- The visual priority is precision, not animation

For these charts, the UX pattern is: **keep old data visible until new data arrives**
(stale-while-revalidate at the store level), then swap instantly.

## Pie Charts (AllocationPieChart)

`lib/components/charts/AllocationPieChart.svelte` draws the allocation pies of the Dashboard and
Broker detail (`AllocationPanel`, type and sector tabs) and the sector distribution of the asset
detail page. It uses **segment morph** animation:

- Data-only updates send just the slices' `data`; ECharts matches slices by `name` and animates
  the arcs.
- `mode="type"` groups asset types by family (`assetTypeFamily`, through `allocationHierarchy.ts`).
  As soon as one family on screen contains a subtype, the chart draws **two rings**
  (`buildAllocationRings`, `allocationRings.ts`): the inner ring holds one arc per family, the
  outer ring splits the families that have subtypes into their members and gives the others a
  filler drawn invisibly, so the two rings stay aligned. Without subtypes the single ring is drawn
  as before; `mode="sector"` always draws one ring.
- With two rings, a data-only update refreshes both series by id (`alloc-base`, `alloc-outer`):
  updating only the first would leave the outer ring on the previous numbers, with no error.
- A full option is built on init, on a dark-mode change, on resize (without animation), and when
  the set of asset types on screen — the ring layout included — differs from the last full build.
- `setOption` merges series by index. When the layout switches between one ring and two
  (`rings !== lastRings`), the full option is applied with `replaceMerge: ['series']`, so the old
  ring series do not stay on screen; every other full build merges with `notMerge: false` alone.

## Numeric Values (TweenedValue)

The `TweenedValue.svelte` component interpolates between numbers:

```svelte
<TweenedValue value={navHeroAmt} format={(v) => formatCurrencyAmountPlain(v, displayCurrency, {showSign: false})} />
```

- Uses Svelte's `tweened()` store with `cubicOut` easing
- Default duration: 900ms (`duration` prop)
- `loading` shows a skeleton pulse instead of the number
- Used by `KpiSection` (hero values), `KpiMetricBar` (when `numericValue` is set) and
  `RiskMetricCard`

A value counts up from 0 when it first appears. A page that already knows its figures — served from
the page cache — calls `setTweenHydration(isHydrated)` during its init: every `TweenedValue` below
it that mounts while `isHydrated()` is true starts at its value, and still tweens on later changes.
The Dashboard and Broker detail pages do this.

## KPI Bars (CSS transitions)

Both bars live in `lib/components/ui/display/` (see [Display blocks](core-ui/atoms.md#display-blocks)):

- `KpiMetricBar`: bar width and marker position animate via `duration-700` transitions; its value
  tweens over 700 ms
- `KpiDivergingFlowBar`: the left and right bars animate independently (`transition-all duration-700`)
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
