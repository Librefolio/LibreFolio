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
the sign outside the mask and the `k`/`M` suffix inside it. Tooltip amounts go through the chart's
own `fmtCurrency` (the currency code, then `maskFormattedNumber`), so the code and the sign stay
readable; the Abs composition rows (assets at cost, returns, capital) print `—` at zero, masked or
not. The general rule is in [ECharts formatters](../state/app-state.md#privacy-echarts).

#### P&L submodes

The `pnl` mode has three submodes (`pnlSubmode`). The mode and the submode persist per user
(`dashboard-growth-mode`, `dashboard-growth-pnl-submode`), shared by Dashboard and Broker detail;
the defaults are `eur` and `line`. A restored `pct` waits for the first completed load: without %
data (`hasPctData`) the chart shows `eur` and the % button is disabled, but the stored value is
kept, so the next mount with % data opens on `pct`. The submode buttons float over the plot's
top-left corner and fold to their icon below a 640 px container (`CONTROLS_COMPACT_BELOW_PX`),
keeping the label as `title` and `aria-label`.

| Submode | Series | x-axis |
|---|---|---|
| `line` | Total P&L split by sign into two series (zero crossings interpolated), a dashed reference line flat at the first visible day's P&L (`__pnlReference__`, left out of the legend), and one line per broker when `brokerPnlHistory` holds two or more (Broker detail passes none) | Time axis, shift animation |
| `candles` | One candlestick series of the total P&L, without broker overlay. A gap is ECharts' empty value `'-'`: a `null` item crashes the candlestick series on a category axis | Category axis (the ladder) |
| `income` | Six bar series in three columns per bucket: the income stack (dividends and interest above zero, costs below), deposits, and acquisitions split between new capital and reinvested returns | Category axis (the ladder) |

**The ladder** (Candles and Income) draws on a category axis, one slot per bucket, so every
candle body and bar gets the same width at any zoom; its labels and separators come from a ladder
plan (`growthLadderAxis.ts`) instead of the responsive time-axis policy. Each submode keeps a fixed
number of series in a fixed order, which the partial update relies on across zoom and pan.

- **Rungs are calendar periods** (`growthLadderBuckets.ts`): `1D`; `1W` from Monday to Sunday;
  `1M` from the 1st; `3M`, `6M` and `1Y` as quarters, halves and years. `3D` and `2W` have no
  calendar unit: they are fixed blocks counted from 1970-01-01 and from Monday 1969-12-29, so their
  edges never move. The caption's unit letter comes from `datePicker.granularity.*Short`.
- **Axis labels** (`planLadderAxis`): a label names the **start** of its bucket's calendar period
  on the entry's rung (`entry.rung`), even when the series covers only part of it: data from
  Thursday 1 January 2026 gets *Dec 29* as its first `1W` label. On the day rungs (`1D`, `3D`,
  `1W`, `2W`) a label is the day number, with the month on the first visible label and wherever
  the month changes, and the two-digit year as well wherever the year changes — *Oct 6 · 13 · 20 ·
  27 · Nov 3 · 10 … Dec 29 · Jan 5 '26 · 12 …* — but never the year on the first visible label.
  `1M` prints the month, `3M` the quarter (`dashboard.pnlAxisQuarter`, `Q{quarter}`) and `6M` the
  months it spans joined by an en dash, each with the two-digit year (`dashboard.pnlAxisWithYear`,
  `{label} ''{year}`) on the first visible label and wherever the year changes: *Oct '25 · Nov ·
  Dec · Jan '26*, *Q4 '25 · Q1 '26 · Q2 · Q3*, *Jul–Dec '25 · Jan–Jun '26*. `1Y` prints the year,
  *2026*. "Changes" compares a bucket with the previous labelled one, so two neighbouring labels
  never read the same. Dates go through `Intl.DateTimeFormat` in the interface locale and both
  keys are translated, so a quarter reads *Q4 '25* in English and *T4 25* in Italian.
- **Label layout**: horizontal labels need 8 px between them (`LADDER_LABEL_GAP_PX`, widths
  estimated at 0.6 × font size × characters), and the outermost ones move inward to stay 2 px
  inside the canvas (`LADDER_EDGE_SAFETY_PX`). If even one visible label does not fit, all of them
  turn 45°, never just some. Turned labels are thinned only when they would still overlap, that is
  when slot × √½ is less than one label row (`LADDER_LABEL_ROW_EM`): then every second, third…
  bucket keeps a label, counted back from the most recent one, which keeps its own. In practice
  only dense Candles get there; an Income slot is always wide enough. A turned label that the
  canvas edge would cut off is left out (on the left, the next candidate becomes the first label).
  For the band under the axis, `ladderLabelMeasure` measures the turned labels at 14 px in the
  chart's font (`echarts.format.getTextRect`) and gives every label the widest one's box
  (`labelBox`), so `containLabel` reserves room for it.
- **Offer** (`availableCandleWidths`, against the measured plot width): a rung is removed, not
  disabled, when a candle body would be narrower than 2.5 px (`LADDER_MIN_BODY_PX`) or, in Income,
  when each of the three bars would be narrower than 4.5 px (`INCOME_MIN_BAR_PX`; the bars keep
  30 % of the slot between buckets and 10 % of a bar between columns). A rung also needs three
  buckets, except `1D`. Income starts at `1W`, and the offer is never empty: the floor rung stays.
- **Selection** (`reconcileCandleWidth`): the first ladder render takes the finest rung offered,
  and every entry into Income takes `1M`, or the nearest rung offered (`incomeOpeningPending`).
  Otherwise Candles and Income share `candleWidth`. A rung that leaves the offer climbs to the next
  wider one offered, or to the widest. The width is not persisted, and a zoom never changes it: it
  only re-plans the axis labels.
- **Edges of the series**: a bucket the series starts inside, or a past bucket it stops inside, is
  `partial` and drawn at half opacity (`PARTIAL_BUCKET_OPACITY`) in both submodes; otherwise the
  bucket that has not ended yet is `current` and drawn whole. The tooltip header prints the rung
  and the calendar period (`1M - 2026-10-01 → 2026-10-31`), then `chart.tooltip.partialBucket` or
  `chart.tooltip.currentBucket` (none on a one-day bucket), then `chart.tooltip.valueAt` the last
  day with data, except in Income, whose bars are sums. A `1D` bucket prints only its date.
- **Candles**: the daily OHLC comes from the backend (see
  [Price Resolver](../../backend/transactions/price_resolver.md#intraday-range-open-high-low)),
  requested through `onRequestPnlCandles` on entry while none is loaded. A bucket takes the first
  open, the highest high, the lowest low and the last close of its days that have a candle
  (`ladderCandleMetric`); a bucket with none is a gap, whose tooltip prints `common.noData`. The
  disclosure caption (`dashboard.pnlCandlesHypotheticalShort`) stays on one line under the plot,
  scrolled by `scrollOnOverflow` when it does not fit, unless the user prefers reduced motion.
- **Income**: a bucket sums its days (`ladderFlowMetric`). Both acquisition series are named
  `dashboard.bookValue`, so the legend, deduplicated by name, lists five entries and one click
  toggles both zones; since ECharts keeps legend state by name, it also toggles the Abs area with
  the same text. The tooltip lists dividend, interest and their total, then costs, deposit and the
  purchase value with its two `↳` halves, each only when non-zero. The four flow series come from
  `POST /api/v1/portfolio/report` (`include_income_history`, `include_cost_history`,
  `include_deposit_history`, `include_acquisition_funding`): the first three scan the transactions
  of each broker in scope, asset-linked or not, keep their sign, and leave out an amount whose FX
  conversion fails, listing its pair in `missing_fx_pairs`; the funding split comes from the
  engine's per-broker cash pools, where a `BUY` spends the returns pool before capital.

### 2. Detail page charts (LineChart, CandlestickChart, PriceChartFull)

These use **instant rendering** (`animation: false`) because:

- Complex segmented series (baseline coloring, stale gradient) create N sub-series
  with variable count between renders
- ECharts cannot reliably match segments across period changes
- The visual priority is precision, not animation

For these charts, the UX pattern is: **keep old data visible until new data arrives**
(stale-while-revalidate at the store level), then swap instantly.

#### Asset detail: Prices and Rolling Return

`routes/(app)/assets/[id]/+page.svelte` keeps the primary series in `primaryMode`, `'price'` or
`'calendar-return'` (the **Prices** and **Rolling Return** buttons). It starts on `'price'` on every
mount and is never persisted; `setPrimaryMode()` stops the measure mode of the panel it leaves.

| | `'price'` | `'calendar-return'` |
|---|---|---|
| Main series | the resolved closes (`chartData`) | the `ASSET_CALENDAR_ROLLING_RETURN` points (`calendarReturnView`) |
| Signals panel | every definition | `allowedSignalTypes = ['asset-comparison']`: the other configs stay saved, only hidden; no backend indicator is requested |
| `PriceChartFull` | line or candlestick, Abs/% toggle, event markers, `editMode` | `valueUnit="percentage"`, `disableCandlestick`, `hideViewModeToggle`, no event markers |
| Measures | `MeasurePanel` | a second `MeasurePanel`, `measurementUnit="percentage-points"`: **Δ pp** and **Days** replace **Δ %** and **Δ%/yr** |
| Data editor | its button and panel | button hidden, panel hidden and `inert` |

The rolling return is a backend signal. `loadChartData()` sends one
`POST /api/v1/assets/prices/query`: the main asset's item carries
`{signal_code: 'ASSET_CALENDAR_ROLLING_RETURN', params: {window_days}}`, with `target_currency` when
the chart is converted, and each Asset comparison gets an item of its own — `include_price: false`,
`include_events: true`, `target_currency` set to the chart currency — with the same signal request,
so every line uses one window and one currency. A page-local wrapper,
`queryAssetPricesBulkWithSignalIsolation()`, validates each signal result on its own, so one
malformed result does not discard the response. The plugin is `catalog_visible = False`
(see [Plugin Contract](../../architecture/patterns/signal_plugin_guide.md#plugin-contract)), so no
selector offers it.

`calendarReturnWindow.ts` turns the **Window** control into days: presets `1w`, `1m`, `3m`, `1y`
are 7, 30, 90 and 365 days, and a custom amount is multiplied by 7, 30 or 365 (weeks, months,
years); the default is `1m`. The selection is saved in the asset's chart settings
(`calendarReturnWindow`, below).

Each point of the answer carries a `provenance`: its status, `reference_target_date`, and the price
and FX dates actually used, each with its `days_back`. `PriceChartFull` reads it through
`mainPointContext` and adds up to three tooltip rows to the main line: `↩` the reference target
date (followed by `chart.tooltip.valueAt` when the reference price is older), `📅` the current price
date when it is older than the point, and `💱` the current and reference FX dates. The plugin leaves
a point empty (`missing_reference`, `invalid_current_price`, `invalid_reference_price`) rather than
estimating it and trims the leading empty points, so each line starts on its own first computable
date. With some empty points the result is `partial` (`undefined_metric_window` warning); with no
computable point it is `unavailable` (`undefined_metric`).

#### Asset detail: where the chart state lives

| Layer | Holds |
|---|---|
| Backend database | Asset prices and events, FX rates: the only persisted sources |
| Chart settings in `localStorage` ([Where settings live](#where-settings-live)) | The asset's override `asset-<id>`, including its `calendarReturnWindow` and its `signals` (indicator and comparison configs with their params, order and styles) |
| The period in `sessionStorage` | The start and end shared by the pages of the tab |
| Page runtime | Signal results, the rolling-return series and their provenance, comparison series, synthetic benchmarks, measures: a reload discards them |

Measure rows and their endpoint results are runtime-only. Each measure's summary `DataTable` keeps
only its own layout (page size, column widths, order and visibility) under its `storageKey`
(`measure-summary-<id>`, `asset-calendar-measure-summary-<id>`).

#### Asset detail: page sync and comparison sync

`requiredFxPairs` lists the FX pairs the page needs to convert into the chart currency: the
asset's, each Asset comparison's, and those of their events' currencies. Each pair has a status
(`ok`, `missing`, `no-data`, `partial-gap`) that drives the data-quality banners. The toolbar
**Sync** (`handleSync()`) opens the page sync modal with the main asset (when it has a provider),
the comparison assets, and every listed pair except the `missing` ones: a pair is never registered
implicitly. The button is disabled for an asset without a provider and for an archived one.

A comparison card's **Sync** (`handleSyncAsset()` → `runSyncAsset()`) sends, in parallel,
`POST /api/v1/assets/prices/sync` for the peer and `POST /api/v1/fx/currencies/sync` for
`collectConfiguredComparisonFxSlugs()` — the configured pairs between the chart currency and the
peer's currency or its events' currencies. Both use `buildComparisonSyncRange()`
(`charts/loadComparisonData.ts`): the chart range, extended back by the window in
`'calendar-return'` mode, then widened by `padSyncRange()` (7 days either side, the end capped at
today). In `'price'` mode, comparison points the backend could not convert stay in their native
currency (see [Price Query](../../backend/assets/architecture.md#data-flow-price-query));
`loadComparisonAssetsData()` (same file) drops them and flags the card with `_conversionFailed`, so
a comparison line never mixes currencies.

## Chart Settings and Axis Scales

The FX and Asset charts (list cards, detail pages, and the **Chart Settings** modal's preview)
share one settings store and one set of axis controls.

### Where settings live

`lib/stores/chartSettingsStore.svelte.ts` keeps the settings in `localStorage`, per user
(`lf_<userId>_chartSettingsStore`, written 250 ms after the last change). Each chart reads, in
order:

1. its own override, keyed by the pair slug for FX and `asset-<id>` for an asset: a card's ⚙️ and
   the detail page's aesthetics and Signals panels all write this one;
2. its scope's default, `__global_fx__` or `__global_assets__`, written by **Settings** in the
   list toolbar;
3. the base defaults (`DEFAULT_CHART_SETTINGS`): area fill, baseline colours, grid lines and stale
   gradient on, the price axis on Auto and the percentage axis on Include 0, no signals.

Saving a scope default (`setGlobalSettings(settings, scope)`) deletes every override of that
scope, detail pages included, and leaves the other scope alone. The period is not a chart
setting: `dateRangeStore.svelte.ts` keeps it in `sessionStorage` (`librefolio_dateRange`), shared
by the Dashboard, broker, asset and FX pages of the tab.

### Axis rows and ranges

`axisScales` holds one setting per axis: `absolute` and `percentage` for the primary axis,
`secondary[key]` for the others. The detail pages and the modal build their axis rows from the
primary row of the active view plus `collectConfigurableSecondaryAxes()` (`chartCoreHelpers.ts`),
which lists one row per secondary axis that the overlays on screen use, keyed
`independent:<axisKey>`, `volume:<axisKey>` or `legacy:<index>`.

Each row has three modes, resolved by `buildPriceYAxis()` for the primary axis and
`resolveSecondaryAxisScale()` for the others:

- **Auto**: the range of the data shown;
- **Include 0**: the same range, stretched to zero;
- **Custom**: the **Min** and **Max** typed in, swapped if inverted; an empty field leaves that
  end to the data.

No plugin bound is applied. The `minimum` and `maximum` a backend signal declares on its axis
(RSI's 0–100, for example) reach the row descriptor as `defaultMin` / `defaultMax`, but no range
reads them: Auto fits the data.

**Min** and **Max** are `type="number"` inputs with `use:numericArrows`
(`lib/actions/numericArrows.ts`: ↑/↓ step by 1, a held key speeds up by powers of ten at round
values, within the field's `min`/`max` when set) and the `.lf-compact-number-input` class
(`app.css`: 0.75rem tabular figures). Below 768 px the iOS zoom guard
([Mobile CSS](../pwa.md#mobile-css)) sets every input without `.zoom-guard-exempt` to 16 px; the
class then only resets the line height.

## Responsive Date Axis

`lib/components/charts/responsiveXAxis.ts` (`buildResponsiveXAxisPolicy()`) decides how many date
labels fit:

- The usable width is the chart width minus `horizontalPadding`, 64 px by default.
- The axis turns **compact** when that width is under 480 px, or when it leaves fewer than 24 px
  per point.
- A compact axis keeps between 2 and 12 labels, one per 48 px on a time axis or per 56 px on a
  category axis: a time axis gets that count as `splitNumber`, a category axis an `interval` that
  spreads them.
- Compact labels are shorter, by span (`formatCompactXAxisDate()`, in the interface locale): month
  and two-digit year from a year up, the month alone beyond 90 days, day and month below. They
  never rotate, overlapping ones hide, and the first and last stay.

It serves `PriceChartFull` (the asset and FX detail charts, with its `CandlestickChart`),
`LineChart` (the asset and FX cards through `PriceChartCompact`, the **Chart Settings** preview,
and the risk charts), `GrowthChart` in its time-axis views (the Candles and Income ladders plan
their own labels, above), `AllocationHistoryChart`, and the broker lots charts
(`LotWacPriceChart`, `LotComparisonChart` and `LotGanttChart`, which pass their own padding).

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
- Every arc of both rings takes its family's label as its `name`, so the legend lists families only
  and one click hides a family's arcs on both rings. The inner ring shows the family icon only on
  arcs of at least 18° (`minShowLabelAngle`); the outer ring captions each member outside with its
  share, the generic member as `dashboard.allocationGeneric` ("Generic ETF"), and its tooltip adds
  a `↳ <family> <share>%` line.
- Shades (`shadeForDepth`, `allocationHierarchy.ts`): the generic member keeps the family colour,
  each subtype is shaded by its rank among the subtypes. With one or two subtypes the lightness
  walks away from the nearer extreme; from three on, the shades spread on both sides of the base
  within lightness 10–90, every other one at half saturation.

`AllocationPanel` persists its view and tab per user (`dashboard-allocation-view`,
`dashboard-allocation-tab`), shared with Broker detail; a restored History requests its data on
mount, as the click does. Its History view, `AllocationHistoryChart`, groups types by the same
families but draws one area per family, without shades; the tooltip lists each family's members,
the generic one as `dashboard.allocationGeneric`.

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
