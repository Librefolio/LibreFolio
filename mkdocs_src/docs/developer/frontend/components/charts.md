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

**Partial vs Full update pattern** (`lib/features/dashboard/GrowthChart.svelte`, used by the
Dashboard and Broker detail):

```typescript
// GrowthChart.svelte — renderChart(forceFullXAxisRebuild = false)
const renderedModeKey = viewMode === 'pnl' ? `pnl:${pnlSubmode}` : viewMode;
const masked = shouldMaskAmount();
const seriesData = buildChartUpdateSeries(isDark, activeData, logicalRange.startDate);
const seriesKey = seriesData.map((series) => series.name).join('\u0000');
const needsFullInit =
    forceFullXAxisRebuild ||
    lastRenderedMode !== renderedModeKey ||
    lastRenderedDark !== isDark ||
    lastRenderedMasked !== masked ||
    lastRenderedSeriesKey !== seriesKey;

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
| `seriesKey` | The names of the series last drawn, in order: a broker that joins, leaves or is swapped under the P&L line changes the list, and from `{name, data}` alone ECharts would keep the old series and their legend entries. |
| `forceFullXAxisRebuild` | The x-axis leaves its compact layout (a narrow container widening on resize). |

The two flag sets differ on purpose:

- `CHART_SERIES_UPDATE_OPTS = {notMerge: false, replaceMerge: ['dataZoom']}` — `series` must
  **not** be in `replaceMerge` here: the partial update sends only `{name, data}`, and replacing
  the matched series would drop the type and styles set by the full option, leaving a blank chart.
- `CHART_FULL_UPDATE_OPTS = {...CHART_SET_OPTION_OPTS, replaceMerge: ['series', 'xAxis']}`.

A resolution switch (daily ↔ weekly/monthly, chosen from the zoom) goes through the partial path
without animation, after hiding the tooltip.

**Where GrowthChart's code lives.** The component keeps everything reactive; what it computes
lives in three modules in the same folder, which hold no state and see the component only through
their arguments:

| File | Holds |
|---|---|
| `GrowthChart.svelte` | Props, state, the `$derived` inputs and the memo of each aggregation, zoom handling, the ECharts lifecycle (`renderChart`, `updateChartData`, `applyFullOption`) and the template. `buildChartUpdateSeries` and `buildFullSeries` are thin wrappers that pass the view on screen to the series module. |
| `growthChartData.ts` | The inputs mapped to one value per day (`mapEurStackedData`, `mapPctValues`, `mapBrokerPnlSeries`, `mapCandlesByDate`, `alignFlowToDates`), the buckets (`buildBucketInfos` for the cascade of Abs, % and the P&L line, `buildLadderBuckets` for the ladder of Candles and Income), their reductions (`aggregateMetric`, `aggregateFlowMetric`, `aggregateCandleMetric` and their `ladder*` counterparts), one entry per resolution or rung (`buildResolutionData`, `buildLadderData`) and the zoom-window geometry (`buildZoomWindow`, `cascadeIndicesAt`, `ladderIndicesAt`). |
| `growthChartSeries.ts` | What each view draws: `buildGrowthUpdateSeries` (the `{name, data}` of the partial update) and `buildGrowthFullSeries` (every series with its type and style, for the full option), with `splitBySign`, `toCandlestickPoint` (the `'-'` gap), `findReferenceTotalPnl` and `PNL_REFERENCE_SERIES_NAME`. |
| `growthChartTooltip.ts` | `buildGrowthTooltip`, the HTML ECharts shows on hover, built from a `GrowthTooltipView` the formatter assembles on every hover (entry on screen, mode, labels, translator, currency); amounts are masked under privacy. |

The one rule: an aggregation reads its data only through `AggregationInputs`. Each memo
(`resolutionCache`, `ladderCache`) is keyed on the identity of the `aggregationInputs` `$derived`
object, which Svelte rebuilds whenever one of its members changes, so a new input is added to that
object and to the `AggregationInputs` type, never passed as one more argument (the other arguments
are the memo's keys: the resolution or rung, and `today` for the ladder). An input that bypasses
the object does not invalidate the memo, which keeps returning entries computed before it changed.

**Weekly and monthly points.** In the time-axis views (Abs, % and the P&L `line` submode, whose
daily, weekly and monthly resolutions the code calls the *cascade*), `buildBucketInfos` stands each
weekly or monthly point on the last day of its bucket that the history holds, the day its
aggregated value comes from (`aggregateLineSeries` keeps a bucket's last point): the calendar end
of a whole period, the last day with data of the period still running. The line reaches the latest
data and the axis ends on that day, never on a Sunday or a month end still to come. On a time axis
ECharts maps a dataZoom percent linearly to time over the drawn extent, not to a point index; the
two agree only while the points are evenly spaced, which the running period's point, or a gap in
the history, breaks. So the cascade reads and writes its window in time: `getLogicalRangeFromChart`
turns the percents into days from the first point (`cascadeDayOffsetsOf`) and widens the window to
the points at or outside its edges (`cascadeIndicesAt`), so a partly visible period is never lost;
an edge within 0.1 day of a point (`ZOOM_EDGE_SNAP_DAYS`) stands on it, which absorbs float and DST
error. `buildZoomWindow` writes the percents the same way, in days over the drawn span. The ladder
(below) keeps index percents on its category axis, each edge rounded to the nearest bucket as
ECharts snaps it (`ladderIndicesAt`).

**Tooltip dates.** The tooltip headers of `GrowthChart`, `AllocationHistoryChart` and the broker
lots' `LotComparisonChart` write every day in the interface locale, never as a raw ISO date:
through `formatDay` (`lib/utils/core/formatAxisDate.ts`: *1 Oct 2026* in `en-GB`, *Oct 1, 2026* in
`en-US`) in the first two, through the chart's own `formatLongDate`, same format, in the third. On
their time axes, `chart.tooltip.valueAt` under a weekly or monthly point prints the point's own
day, and a weekly header (`chart.tooltip.weekRange`) runs from the bucket's first day up to it
(`bucketSpanUpTo`, `priceChartHelpers.ts`, as in `PriceChartFull` and `CandlestickChart`): a whole
week or month ends on its bucket end, the one still running, or the one the series stops inside,
on its last day with data, never on a day still to come. `LotComparisonChart` reads that day from
the hovered point (`tooltipBucketInfo`, `lotComparisonChartHelpers.ts`). The ladder header names
the whole calendar period instead (below).

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
the defaults are `eur` and `line`. After every completed load, a `pct` view, restored or picked,
over a history without % data (`hasPctData`) shows `eur`, and the % button is disabled. The
fallback is display-only: the stored value is kept and `pctFallback` marks the fallback, so the next
loaded history with % data brings the view back to `pct`, and the next mount still restores `pct`;
`selectMode()` clears `pctFallback`, so a mode picked meanwhile, `eur` included, wins. The submode
buttons float over the plot's top-left corner and fold to their icon below a 640 px container
(`CONTROLS_COMPACT_BELOW_PX`), keeping the label as `title` and `aria-label`.

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
  and the whole calendar period, by design (`1M - 1 Oct 2026 → 31 Oct 2026` in `en-GB`), then
  `chart.tooltip.partialBucket` or `chart.tooltip.currentBucket` (none on a one-day bucket), then
  `chart.tooltip.valueAt` the last day with data, except in Income, whose bars are sums. Every day
  goes through `formatDay`; a `1D` bucket prints only its date.
- **Candles**: the daily OHLC comes from the backend (see
  [Price Resolver](../../backend/transactions/price_resolver.md#intraday-range-open-high-low)),
  requested through `onRequestPnlCandles` on entry while none is loaded. The effect calls it
  tracked, on purpose: what the page's loader reads before its first `await` becomes a dependency,
  so a saved Candles view asks again once the Dashboard knows its brokers (`canAsk`), and a failed
  request is asked again when a retry falls due, at most three times, 2, 4 and 8 s later
  ([Lazy sections after a failure](../state/domain-state.md#lazy-report-retry)); an `untrack`
  around the call would silence both. A bucket takes the first
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
so every line uses one window and one currency. The page's `queryAssetPricesBulkWithSignalIsolation()`
sends it, and `parseAssetPriceQueryWithSignalIsolation()`
(`lib/components/assets/detail/assetDetailPriceQuery.ts`) validates each signal result on its own, so one
malformed result does not discard the response. The page then reads the signal results inside a `try` of
their own (X-R16): a malformed one fails the signals only, with the panel's notice «Technical signals could
not be updated», while the prices still reach the chart, the price cache and the **All** start. The FX
detail page reads `POST /api/v1/fx/currencies/convert` the same way, through
`parseFxConvertWithSignalIsolation()` (`lib/components/fx/fxDetailConvertQuery.ts`), so its rates survive a
malformed signal result too.

The same plugin is also in the signal catalog (see
[Plugin Contract](../../architecture/patterns/signal_plugin_guide.md#plugin-contract)): in
`'price'` mode the Signals panel offers it in its Risk group as **Rolling Return**, a config of
`signalType` `asset-calendar-rolling-return` whose card edits `window_days` (30 by default, at
least 1). `buildBackendSignalRequestPlan()` requests it like any other backend indicator, and its
`calendar_return` line is drawn over the prices on a secondary axis of its own,
`independent:calendar_return`. Overlay and mode compute the same metric, the price return against
the resolved close `window_days` calendar days earlier, but never in the same request:
`loadChartData()` requests the overlay only in `'price'` mode, with its card's window, and the
mode's series only in `'calendar-return'` mode, with the **Window** control's days. In
`'calendar-return'` mode the overlay config stays saved and hidden, like every config but the
Asset comparisons.

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

`requiredFxPairs` (built by `buildRequiredFxPairs()`, `lib/components/assets/detail/assetDetailFxRequirements.ts`)
lists the FX pairs the page needs to convert into the chart currency: the
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

#### Measure mode {: #measure-mode }

The asset detail and FX pair pages measure on their chart through `MeasurePanel`
(`lib/components/charts/MeasurePanel.svelte`). The asset page mounts one panel per primary mode and
talks to the one on screen (`activeMeasurePanel()`). 📏 calls the panel's `startMeasureMode()` or
`stopMeasureMode()`; the panel reports its mode through `onmeasuremodechange`, and the page hands it
to the chart as `measureMode`, with the chart's two measure callbacks wired to the panel:

- `onMeasureClick(date, value)` calls `addPoint(date, value)`. The first click leaves the start
  pending. A second click on the start's day is ignored: no measure, measure mode stays on, the start
  stays pending. A click on another day adds the measure, its dates sorted, and stops measure mode.
- `onMeasureHover(date, value)` returns `updatePendingEnd(date, value)` straight through:
  `(date, value) => activeMeasurePanel()?.updatePendingEnd(date, value)` in
  `routes/(app)/assets/[id]/+page.svelte`, `(date, value) => measurePanel?.updatePendingEnd(date, value)`
  in `routes/(app)/fx/[pair]/+page.svelte`. `updatePendingEnd` draws the dashed live preview
  (`__pending__`) from the start to `date` and returns a `boolean`: `true` on the pending start's
  day, where it also removes the preview if one is drawn; `false` elsewhere, with measure mode off, or
  with no start pending.

No measure spans a single day (lot Y-N65, as in the
[date pickers](core-ui/datePickers.md#no-single-day-range)). The expanded card's `DateRangePicker`
cannot publish a range of one day, so `updateMeasureDates` no longer refuses one on its own: that
silent refusal was bug N65, where the card's picker showed the same day in «From» and «To» while the
measure kept its old dates. The panel's **+** (`addMeasureFromChartData()`) measures from the first
measurable point to the last, and does nothing when both fall on the same day.

**The cursor.** zrender writes its own cursor inline on its element at every pointer move, before
its listeners run (`Handler.mousemove`, zrender 6), so the `cursor-crosshair` class that the chart
container carries in measure mode was hardly ever seen. `PriceChartFull` (line view) and
`CandlestickChart` (candles) therefore set their cursor through zrender:

- On every zr `mousemove` while `measureMode` is on (and an `onMeasureHover` is given), synchronously
  and before the `requestAnimationFrame` throttle, the chart calls `zr.setCursorStyle('crosshair')`,
  or `'not-allowed'` while the last resolved hover was refused.
- In the frame it resolves the point under the pointer, calls `onMeasureHover`, and applies the
  cursor of the new answer. `onMeasureHover` is typed `(date, value) => boolean | void`; `true` means
  refused. The container publishes the answer as `data-measure-hover`: `"blocked"` over a refused day
  (the measure's start), `"free"` anywhere else, including off every point. Out of measure mode the
  attribute is absent, and a hover still queued when measure mode ends publishes nothing.
- Outside measure mode the chart never calls `setCursorStyle`: zrender keeps its own cursor.

These rules are pinned in the Y-N65 describes of `MeasurePanel.test.ts` and `PriceChartFull.test.ts`.
The latter runs each case on the line view and on the candle view, with an ECharts stand-in whose zr
records every `setCursorStyle` call.

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

The stored document carries a `version`, `STORAGE_VERSION` (3). When the store reads it,
`migratePersistedChartSettings()` brings a version 1 or 2 document to version 3, in the global
settings and in every override; a document of any other version is ignored, and the defaults
apply. Version 3 follows the developer's decision 29, one Rolling Return measured in calendar
days: the observation-count `RISK_ROLLING_RETURN` plugin is gone, so every saved
`risk-rolling-return` config becomes an `asset-calendar-rolling-return` one. Its `window` param
becomes `window_days`, with the same number; the style of its `rolling_return` output moves to
`calendar_return` in `componentStyles`; and the secondary-axis scale saved under
`independent:risk_return` moves to `independent:calendar_return`, unless that key already holds
one. Every other field and every other signal stay as they were. A window of N observations thus
becomes N calendar days: 30 observations of an exchange-traded asset, about 42 calendar days,
become 30 days, while a crypto-asset, quoted every day, sees no change. The store writes the
migrated document back to `localStorage` at once; `chartSettingsStore.migration.test.ts` covers
both the function and that rewrite.

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

### Signal rendering shared by cards, preview and detail pages {: #signal-rendering }

`lib/charts/chartSignalRendering.ts` is the one place that turns a chart's saved signals into
`RenderedSignal[]`. It is pure (no Svelte state, no store read): the caller says where the series
come from.

| Function | Role |
|----------|------|
| `renderLocalSignal(config, baseData, viewMode, sources)` | one saved local signal, rebuilt with `signalFromConfig()`, given its data, rendered on `baseData`; nothing if the type is unknown or the series it reads is missing |
| `renderLocalSignals(configs, definitionsByType, baseData, viewMode, sources)` | a chart's local signals in order; backend-owned and unknown definitions are skipped |
| `renderBackendResults(configs, results, definitionsByType, baseData, viewMode, translate?)` | a chart's backend results in order, each drawn with the current config of its id |
| `SignalDataSources` | `fxPairData(slug)`, `comparisonTarget(assetId)` and `selfAssetId`: where an FX-pair or comparison signal gets its series; `NO_SIGNAL_SOURCES` is the empty set |

The Assets list (`routes/(app)/assets/+page.svelte`), the FX list (`routes/(app)/fx/+page.svelte`)
and `ChartSettingsModal` call these functions with their own `SignalDataSources`, so a signal
looks the same on a card and in its preview: a comparison is named after its target, a comparison
with the chart's own asset (`selfAssetId`) is never drawn, and an FX pair follows the direction of
the card.

The two detail pages (`routes/(app)/assets/[id]/+page.svelte` and `routes/(app)/fx/[pair]/+page.svelte`)
use the same functions: `renderLocalSignals` for their saved local signals, `renderBackendResults`
for their backend results and, on the FX page, the module's `fxPointToLineDataPoint` to turn store
points into chart points. They build their `SignalDataSources` with the pure helper
`detailPageSignalSources({configs, assets, fxPairPoints, selfAssetId?})`
(`lib/charts/chartPageSignals.ts`):

- an FX pair reads the points of the FX store, straight (the signal's own `_inverted` turns them),
  asked lazily, one pair at a time;
- a comparison reads the series that the comparison load wrote into its config
  (`params._resolvedData`), named with icon and type by the assets the page knows (an unknown asset
  gets the catalogue fallback name);
- there is no base point, because the detail pages draw daily data;
- the asset detail page passes its own asset as `selfAssetId`.

So a signal looks the same on a card, in the preview and on a detail page.
`signalRendering.gate.test.ts` keeps it that way: no file outside the module calls
`signalFromConfig()`, and the list of known copies (`KNOWN_COPIES`) is empty and can only shrink.

### Preview chart in the modal {: #settings-preview-chart }

The preview in `ChartSettingsModal` is `PriceChartFull`, the chart of the detail pages, not a
bespoke `LineChart`. It is configured as follows:

| Prop | Value |
|------|-------|
| `data` | the **absolute** series: the card's real data in `pair` mode, a synthetic curve in `global` mode |
| `externalViewMode` | the modal's view selector (**Abs** / **%** / **Rolling Return**, see [Three views](#primary-views)): the chart takes the percentage view itself |
| `externalChartType` | `'line'` (no candlesticks) |
| `hideToolbar` | `true` |
| `chartHeight` | `'220px'` |
| `areaFill`, `colorByBaseline`, `showGridLines`, `showGradient` | the aesthetics being edited, not the saved ones |
| `yAxisMode` / `yAxisMin` / `yAxisMax`, `secondaryAxisScales` | the axis scales being edited, for the primary scale of the active view and for the secondary axes |
| `overlaySignals`, `overlaySignalInfoMap` | the preview signals and `buildOverlaySignalInfoMap()` of them, so a comparison shows its asset's icon and type in the tooltip like on the detail page |

The modal passes no events, measure or edit props, so none of them is drawn. The mouse-wheel zoom
is the chart's own `inside` dataZoom.

### Baseline colour on cards {: #cards-baseline-colour }

The list cards (`AssetCard`, `FxCard`) pass `colorByBaseline` from the chart settings to
`PriceChartCompact`, which forwards it to `LineChart`; before, compact charts ignored it. The
series is green from the baseline up and red below it, with a dashed baseline line. The base is:

- **absolute view**: the `baselineValue` prop when a page gives one, else the first non-missing
  point of the `data` the chart received. A card thins a dense series to weekly or monthly points
  *inside* `LineChart`, after this base is taken, so the base is the real start of the period and
  not the end of the first bucket;
- **percentage view**: always 0, whatever `baselineValue` says.

`baselineValue` is an optional prop of `LineChart`, forwarded by `PriceChartCompact`, for a page
that knows a better base than the first point of the data it hands over. No list page uses it today.

### Three views: Abs, % and Rolling Return {: #primary-views }

A chart's saved view is `ChartSettings.primaryView` (`ChartPrimaryView`: `'absolute' | 'percentage' |
'calendar-return'`, default `'percentage'`), next to `calendarReturnWindow` and
`calendarReturnWindowAuto`. The Assets list and the FX list use all three; the FX list opens on
`'absolute'` (`scopeDefaultView('fx')` in the store, as before), every other chart on `'percentage'`.
`ChartSettingsModal` offers the third view only when the page passes `calendarPreviewResolver`
(otherwise it falls back to `'percentage'` when a chart opens on `'calendar-return'`); both lists
pass it. `STORAGE_VERSION` is unchanged: a document saved before these fields existed
is filled by the sanitiser (`primaryView` = `'percentage'`; `calendarReturnWindowAuto` = `true` only
when the stored window is the default one).

| Function | Role |
|----------|------|
| `setScopePrimaryView(view, scope)` | the list's top bar: sets the scope default (`__global_<scope>__`) and resets every override of the scope to `view`, keeping their other fields; the other scope is untouched |
| `setItemPrimaryView(slug, view, scope?)` | one chart (a card's button, the detail page); an override it creates starts from the scope's settings |
| `nextCardPrimaryView(view)` | the card button's order: `'percentage'` → `'calendar-return'` → `'absolute'` → `'percentage'`; the button shows the view it goes to |
| `effectiveCalendarReturnWindow(settings, rangeDays)` | the window in force: the saved one, or, while `calendarReturnWindowAuto` is `true`, the preset chosen by `largestCalendarReturnPresetFor(rangeDays)` (`calendarReturnWindow.ts`: the largest preset whose days fit the range, the smallest when none does) |
| `detailModesForPrimaryView(view)` / `primaryViewForDetailModes(mode, viewMode)` | the mapping with the detail page's `primaryMode` and `viewMode` (below) |

`calendarReturnWindowAuto` stays `true` until the user chooses a window. The rule is in the store:
any save through `setPairSettings` or `setGlobalSettings` whose `calendarReturnWindow` differs from
the one stored before sets it to `false`, whoever saves (modal, detail page). From then on the saved
window is used as it is, whatever the period.

**How the list asks for the rolling return.** For a card whose view is `'calendar-return'`, the list
(`routes/(app)/assets/+page.svelte`) sends the card's item with a calendar signal
(`ASSET_CALENDAR_ROLLING_RETURN`, `window_days` from `effectiveCalendarReturnWindow()` over the
list's range) instead of the card's backend signals. `buildReducedQuery()` (`lib/utils/reducedPriceQuery.ts`),
given the card's `calendar` option, adds one item for every comparison target — cached or not — as
`sample_like` the card's item, with the same signal, `include_price: false` and `target_currency` =
the card's currency, so every line has one window and one currency. The list keeps the answers per
card in `calendarByCard` (the card's own view and its targets'), read with
`extractCalendarReturnView()`. A card in this view draws the own points and
`renderCalendarComparisons(configs, views, target, fallbackName, selfAssetId)`
(`chartSignalRendering.ts`): the asset-comparison configs whose target view is `ready` or `partial`,
each as a percentage line with the config's style, in the asset's name and icon; a comparison with
the chart's own asset or without a ready view draws nothing. The other signals stay saved and are
not requested. With no points, `AssetCard` shows the problem message (for example, less history than
the window) instead of the chart.

**The FX side.** The FX list (`routes/(app)/fx/+page.svelte`) works the same way, with
`buildFxCalendarQuery()` (`lib/utils/reducedFxQuery.ts`) over `POST /fx/currencies/convert` (sampling:
[backend FX architecture](../../backend/fx/architecture.md#convert-sampling)). For each card in the
view it builds one conversion of 1 unit in the direction the card shows the pair (a flipped card asks
the flipped rate), with the calendar signal, `key` `fx:<slug>` and `max_points` from the card's plot
width. Every compared `fx-pair` signal adds a conversion of 1 unit in the direction its signal shows
its pair, with the same signal and `sample_like` the card's key; the members of a card share a group,
so `bulkBatches.ts` never cuts between them. The page reads the signals from `signal_results`, matched
to its entries by `request_index` (local to the batch), into `calendarBySlug` (`extractCalendarReturnView()`);
the rates of these conversions are never merged into the FX stores, and the cards' daily rates stay
the stores' (not sampled). A card draws the own points and `renderCalendarPairComparisons(configs,
views)` (`chartSignalRendering.ts`): each `fx-pair` signal whose view is `ready` or `partial`, as a
percentage line with the signal's style; asset comparisons on FX cards are not drawn. The modal's
preview (`resolveCalendarPreview`) for one pair converts the same way; for all charts it posts the
demo points to `/signals/preview`.

**The detail page.** The asset detail page opens in the view of its card: it reads
`primaryView` with `detailModesForPrimaryView(settings.primaryView)` (`'calendar-return'` gives
`{primaryMode: 'calendar-return', viewMode: 'percentage'}`, the two others give
`{primaryMode: 'price', viewMode: view}`), and saves the user's change of mode or view as the card's
view, `primaryViewForDetailModes(primaryMode, viewMode)`. It saves it with `setPairSettings()` and the
settings it holds, its signals included, not with `setItemPrimaryView()`, which rebuilds the override
from the store's copy and would drop what the page writes into its signal configs (a comparison's
`_resolvedData`). Its window is `effectiveCalendarReturnWindow(settings, rangeDays)`, so the asset
detail page uses the same window as the list, and a window chosen there is saved through the
settings, which marks it as chosen.

## Responsive Date Axis

`lib/components/charts/responsiveXAxis.ts` (`buildResponsiveXAxisPolicy()`) decides how many date
labels fit and how they read, in the interface locale (`uiLocale()`) unless a `locale` is passed.
Two neighbouring labels never read the same (pinned in `chartCoreHelpers.test.ts`).

- **Compact or wide**: the usable width is the chart width minus `horizontalPadding`, 64 px by
  default. The axis turns compact when that width is under 480 px, or leaves fewer than 24 px per
  point. A compact axis keeps 2 to 12 labels, one per 48 px on a time axis or per 56 px on a
  category axis: a time axis gets that count as `splitNumber`, a category axis with more points an
  `interval` that spreads them.
- **Compact labels**: `axisLabel` turns on `hideOverlap`, `showMinLabel` and `showMaxLabel`, sets
  `rotate: 0` and carries the formatter. A category axis also gets `alignMaxLabel: 'right'`: the
  forced last label ends at its tick instead of spilling past the chart's right edge on a phone. A
  time axis does not: ECharts ranks time labels by tick level before hiding overlaps, so a month or
  year tick next to the edge would win, and the end label, pulled inward, would be the one hidden;
  its charts make room for the label instead (next bullet). The first label needs no alignment: it
  spills at most into the y-axis labels, inside the chart.
- **Zoom** (category axis): an optional `visibleCount`, how many points a zoom leaves visible,
  replaces `values.length` in the compactness test and the `interval`; without it, every value
  counts. On the whole series, 365 daily points in 800 px get `interval` 33, which leaves a 34-point
  zoom only its edge labels; counted on that window, `interval` is 2. `visiblePointCountFromZoom()`
  reads the count from a `dataZoom` event or a `{start, end}` window, never from `getOption()`, which
  deep-clones the whole option. `categoryAxisLabelPatch()`, the
  `axisLabel` merged with `setOption`, puts `interval: 'auto'` first, so no merge keeps the previous
  window's step, and gives the compact keys back their ECharts defaults once the window is wide.
  `LineChart` and `CandlestickChart` merge it when a gesture pauses for `ZOOM_LABEL_SETTLE_MS`
  (120 ms), `PriceChartFull` in its 200 ms `scheduleResolutionRecompute()`; resizes and full renders
  count the visible window too. Time axes need none of it: ECharts spreads their `splitNumber` ticks
  over the visible extent.
- **Arrow markers** (category axis): an overlay signal may end in an arrow
  (`markerStart`/`markerEnd: 'arrow'`), aimed along the line's on-screen slope, which a zoom, a pan
  or a resize can change. `updateArrowRotations()` (`lineChartHelpers.ts`) reads `getOption()`, so
  it re-aims them once a gesture or a resize pauses, in the settle that re-spaces the labels, which
  a `dataZoom` event or a `ResizeObserver` callback re-arms instead; a full render re-aims them at
  once, after restoring the zoom. It writes the series back only when an arrow turns by more than
  `ARROW_ROTATE_EPSILON_DEG` (0.01°), so the stability pass after a first draw and the settle after
  a redraw write nothing if no arrow moved. `noteArrowMarkers()`, called right after each full
  render (`setOption(option, true)`), records whether that option draws an arrow: on a chart without
  one (most charts), `updateArrowRotations()` returns before `getOption()`. It reads the option
  afresh on every call, so its write-back, which carries every series' colours, never brings back
  those from before a theme switch or a chart-colour change (pinned in `LineChart.test.ts`,
  `PriceChartFull.test.ts`, `lineChartHelpers.test.ts` and `chartCoreHelpers.test.ts`).
- **Right inset** (time axis, compact or wide): the axis ends on the last day of the data or of the
  zoom, and ECharts centres that day's label on its tick, so half of it overhangs the plot's right
  edge. `grid.containLabel: true` reserves the labels' height, never that overhang, so on a phone
  the last label would be cut. `timeAxisGridRight()` takes the chart's `width`, the axis `values`,
  the `locale`, the grid's `base` right edge and a `measure` function, and returns the grid's
  `right`: half the widest label the axis can draw, rounded up, plus 2 px, when that is wider than
  `base` (px, or a percentage of `width` as ECharts reads it); otherwise `base` itself, so a desktop
  keeps its percentage and follows its own width. `containLabel: true` stays. ECharts 6's
  `outerBoundsMode: 'same'` with `outerBoundsContain: 'axisLabel'` was rejected: it estimates the
  label room once, before `hideOverlap` picks the ticks that survive, so on a narrower plot it cut
  labels that were whole and lost first labels (and `containLabel: true` ignores the `outerBounds*`
  keys). The price is a narrower plot on a phone (about 13–15 px in the dashboard charts, 4–5 px in
  `LotComparisonChart`), so sometimes one label fewer; `hideOverlap` may still hide the end label
  when the previous tick sits too close: a missing label, never a cut one.
- **Inset candidates** (`timeAxisLabelCandidates`, cached for up to 16 locale-and-range keys): the
  widest label is taken over every text `buildTimeAxisFormatter` (below) can write, compact or wide,
  on an axis whose data runs from the first to the last of `values`. These are the two end days in
  the endpoint format (day and month, plus the two-digit year when the range crosses a calendar
  year), and the label of each local midnight from the day before the first to the day after the
  last, since zoom can put the axis edge on any day of the data and ECharts widens a one-day extent
  by a day on each side: *15 Jul* on a day other than the 1st, *2026* on 1 January, both *Aug* and
  *1 Aug* on another 1st (in `en-GB`). Past 366 days, every day of a leap year (2024) stands in for
  the calendar, except 1 January, which adds the year of each real one in range. Measured before
  the render, the inset is conservative: equal to, or a few px wider than, what ECharts draws.
  `axisLabelMeasure(chart, fontSize)` gives the `measure`: the width `echarts.format.getTextRect()`
  returns in the font of `axisLabelFont(chart, fontSize)`, the chart model's `textStyle.fontFamily`
  or, before a first option, ECharts 6's own default (`sans-serif`, `Microsoft YaHei` on Windows).
  It is lazy on purpose: the font is resolved at the first measure and `echarts.format` read only
  inside the call, so a test that mocks ECharts without `format` still mounts a chart that measures
  nothing.
- **Wide labels**: no `axisLabel` overrides, only the `formatter`, which the consumers apply in
  both modes: ECharts' own labels are English on a time axis and raw ISO dates on a category one.
- **Time axis** (`buildTimeAxisFormatter`): a label names the tick ECharts places, not the length
  of the period, so ticks a week apart read *8 Aug*, *15 Aug* (in `en-GB`), never *Aug Aug*. A day
  tick reads *15 Jul* and 1 January *2026*. The 1st of another month reads *Aug* when the ticks are
  months (tick level 0), *1 Aug* when it is a month boundary among day ticks. A tick off local
  midnight gets no label: it would repeat a day already on the axis. When compact, with the end
  labels forced on, the first and last data points keep their day, plus a two-digit year when the
  range crosses a calendar year; the midnight of a last day that ends mid-day gets no label.
- **Category axis** (`buildCategoryAxisFormatter`): a compact axis labels one point every
  `interval + 1`. Month names stand alone only when every two neighbouring labels fall in different
  months; otherwise a label reads day and month. The two-digit year appears where it changes from
  the previous label, and on the first and last point when the data crosses a year. A label off
  the regular grid (the last point, or one moved by zoom) keeps its day. A wide axis has no
  `interval`: ECharts picks the labels, so each carries what it needs, the month for monthly data,
  the day otherwise, the year whenever the data crosses one.

The category axis serves `PriceChartFull` (asset and FX detail, with its `CandlestickChart`) and
`LineChart` (the **Chart Settings** preview and the risk charts; the asset and FX cards draw it
through `PriceChartCompact`, date axis hidden). The time axis serves `GrowthChart` in its time-axis
views (the Candles and Income ladders plan their own labels, above), `AllocationHistoryChart` and
the broker lots charts (`LotWacPriceChart`, `LotComparisonChart` and `LotGanttChart`, which pass
their own padding). When a chart goes back from compact to wide, its consumer rebuilds the whole
option, or merges `categoryAxisLabelPatch()` on a zoom, so compact-only keys such as
`alignMaxLabel` do not linger.

Three of the time-axis charts take the right inset. `GrowthChart` (`base: '4%'`, 14 px labels)
computes it in its time-axis views only (the ladders keep `'4%'`: their plan keeps the outermost
labels inside the canvas, above), in the full option, in the partial update (new dates are new
labels, so the inset travels with the axis they are drawn on) and on resize, since `'4%'` stands
for other pixels at another width; the resize applies it at once, not lazily, because
`syncPlotGeometry()` reads the grid that call lays out. `AllocationHistoryChart` (`'4%'`, 14 px)
computes it with every option it builds and on resize (`lazyUpdate`). `LotComparisonChart`
(`base: 18` px, 12 px labels) computes it on its axis date range (`xAxisRange`, else the series'
own) only when it builds the option: a px base does not follow the width. `LotWacPriceChart` and
`LotGanttChart` keep a fixed 18 px (`GRID_RIGHT_PX`).

## Chart Text and Tooltips {: #chart-text-and-tooltips }

ECharts reads none of the app's CSS: it draws legends, labels and axes on a canvas, and writes its
tooltip as HTML with an inline `font`. Two rules follow, one for the font of that text and one for
the tooltip's HTML.

### Flags in chart text {: #chart-flag-font }

The app draws flags (the regional indicator symbols U+1F1E6–1F1FF) with the `'LF Flags'` face that
starts its CSS font stacks ([Fonts](../styling.md#fonts)). That CSS never reaches chart text:
ECharts drew it in its own default family, and a flag in a legend, a label, an axis or a tooltip
fell back to the system, which prints two letters where it has no flag glyphs (Windows among them).

`lib/components/charts/chartFont.ts` exports the charts' font:

- `CHART_FONT_FAMILY`: `'LF Flags'`, then ECharts' own default family (`sans-serif`, or
  `'Microsoft YaHei'` on Windows, chosen the way ECharts chooses it). The face covers the flags and
  nothing else, so every other character falls through to that default and keeps its font.
- `CHART_INIT_THEME`: `{textStyle: {fontFamily: CHART_FONT_FAMILY}}`.

Every chart is created with that theme, and with the options of
[`chartInitOptions`](#chart-pixel-density):

```typescript
chartInstance = echarts.init(chartContainer, CHART_INIT_THEME, chartInitOptions(chartContainer));
```

A theme's `textStyle` is ECharts' global font: the canvas text and the tooltip's inline `font` use
it unless a component sets its own `fontFamily`. It is a theme rather than a `textStyle` in each
option because ECharts merges the theme again on every `setOption`, a `notMerge` one included, so
no option builder has to repeat it. A component that sets its own family uses `CHART_FONT_FAMILY`,
as `CorrelationHeatmap` does on its axis labels, which it measures with a canvas context in that
same font. The code that measures chart text from the chart model (`axisLabelFont`, see
[Responsive Date Axis](#responsive-date-axis), and `GrowthChart`'s ladder labels) reads its
`textStyle.fontFamily`, which is this family too.

The chart colours stay in `lib/theme/chartTheme.ts`, and the font is kept out of it on purpose:
that module holds colours only, and `chartTheme.test.ts` requires every string it exports to be a
colour.

**Loading the face.** A canvas paints its text once, with the faces loaded at that moment, and the
browser fetches a `unicode-range` face only for page text that needs it: canvas text does not
count. Two steps cover this:

1. `chartFont.ts` asks for the face when the first chart module loads, before any chart can paint:
   `chartFontReady()` calls `document.fonts.load()` once, with a flag as sample text (other text
   would load nothing), and never rejects, so a face that fails to load leaves the system fallback.
   Without `document.fonts`, in a test or on the server, it resolves at once.
2. `scheduleFirstRenderStabilityFix` (`echartsTooltipHelpers.ts`), which a chart calls once after
   its first full `setOption`, checks `chartFontLoaded()`: when the face is not in yet, it repaints
   the chart (`resize()`) once the request of `chartFontReady()` settles. Every chart calls it
   except `LotGanttChart`.

### Pixel density {: #chart-pixel-density }

A chart's canvases hold its CSS size times a pixel density. zrender reads the screen's density once,
when its module loads, and fixes it for a chart at `init`: a tab opened on a 1× screen drew every
chart at 1×, the ones opened later too, and blurred them once the window moved to a Retina screen
or the browser zoomed in. `lib/components/charts/chartPixelRatio.ts` handles both moments:

- **At creation:** `chartInitOptions(element)` gives `echarts.init` the canvas renderer and the
  screen's density at that moment (`devicePixelRatio`, never under 1, zrender's own rule).
- **When the density changes:** one `matchMedia` resolution query for the whole app, armed by the
  first chart and re-armed at each change. Every chart created through `chartInitOptions` and
  still alive is brought to the new density in place (`setChartPixelRatio`): its zoom, legend,
  selection and handlers stay, and nothing is drawn again from its options.

In place means the members of zrender 6's canvas painter that its own `resize()` uses
(`painter.dpr`, `getLayers()`, each layer's `dpr`, `ctx.dpr` and `resize()`, then
`refresh(true)`). They are checked before anything is touched: when one is not there, the chart
keeps its density, with a warning in debug builds.

### Tooltip HTML {: #chart-tooltip-escaping }

ECharts sets what a tooltip formatter returns as `innerHTML`. Every value a formatter takes from
the data or from currency metadata (names, captions, currency codes, flags, event types) goes
through the shared `escapeHtml` (`lib/utils/core/escapeHtml.ts`) where it is interpolated; a flag
is such a value, read from `getCurrencyInfo(code).flag_emoji`. A series label with its icon goes
through `signalLabelToHtml` (`lib/charts/signalLabel.ts`), which escapes it.

The frontend sources hold one HTML escaper: write no local copy. `escapeHtml` escapes `&`, `<`,
`>`, `"` and `'`, so its output is also safe inside an attribute, whichever quote the call site
uses; a copy that escapes fewer characters is the defect this rule removes. One file is exempt:
`lib/utils/inlineMath.ts`, whose KaTeX variant keeps the apostrophe on purpose (`f'(x)` is prime
notation). The rule for every hand-built HTML string, and its other gates, is in
[Output Escaping](../../architecture/security.md#output-escaping).

### Guards {: #chart-text-guards }

`./dev.py test front-portfolio chart-safety-unit` runs them:

| Test | Checks |
|---|---|
| `lib/components/charts/chartFlagFont.test.ts` | With the real ECharts, rendered server-side to SVG: a chart created with `CHART_INIT_THEME` draws its legend, axis and pie labels with `'LF Flags'` first, also after `setOption(option, true)`. A static scan of the production sources: every `echarts.init(` passes exactly `CHART_INIT_THEME` as its second argument and `chartInitOptions(<its element>)` as its third, every chart included since DV-14. `PIXEL_RATIO_PENDING` is kept, empty, for a chart that cannot migrate at once: a listed file that passes it, has no call or is gone fails the gate. And no module reaches ECharts' `init` under another name. The scan skips `lib/dev/designer-lab/`, whose engine creates a 1×1 probe that never paints. |
| `lib/components/charts/chartFont.load.test.ts` | The face is requested before the first paint, and a chart that painted before it arrived paints again once it is in. |
| `lib/components/charts/chartPixelRatio.test.ts` | A chart is created at the density of that moment; a change of density re-arms the query and brings every live chart to it; the update in place runs on the real zrender, so an upgrade that moves its painter's members fails here. What it does not recognise, an SVG chart or a disposed one, it leaves alone, never throwing. |
| `*.tooltipEscape.test.ts`: `AllocationPieChart`, `CandlestickChart` and `PriceChartFull` beside the charts, `CorrelationHeatmap` in `lib/features/risk/` | Fed a value that carries markup, the tooltip injects no element and shows the value as text; the heatmap's also requires the shared `escapeHtml`'s output, quotes included. |
| `lib/utils/core/escapeHtml.single.test.ts` | No production source holds an HTML escaper (`&` mapped to `&amp;`) outside `escapeHtml.ts` and the exempt `inlineMath.ts`; an exempt file that no longer holds one fails too, so an exemption cannot go stale. |

Beside them, `SemiDonutChart.test.ts` checks that a chart's `init` receives the canvas renderer and
the screen's density, and `./dev.py test front-portfolio chart-pixel-ratio`
(`e2e/portfolio/chart-pixel-ratio.spec.ts`) changes the density of a live Dashboard through
Chromium's device metrics: its charts follow in place, the same instances and canvases, and a chart
opened after the change is born at the new density.

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
