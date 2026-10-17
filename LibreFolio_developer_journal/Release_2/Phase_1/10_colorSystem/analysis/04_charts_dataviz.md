# 04 — Data visualization colors (charts)

> Snapshot: `dev_release2` @ `6d0b1266c` (v1.2), 2026-10-14. Read-only. Produced by the chart-audit sub-agent; light/dark rendering not visually verified.


Paths are relative to `/Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/`. I found colours with a hex/rgba grep over the scoped folders plus `lib/components/brokers/lots/`, where the lot charts live. I read the key places but did not read every chart file end to end, and I made no changes.

**Short version:**
- No chart reads the colour variables in `app.css` (`var(--…)` or `getComputedStyle`). Every chart colour is a hardcoded light/dark hex pair, picked by checking whether the page has the `dark` class.
- The same idea is drawn in different colours from chart to chart. Gain/loss alone uses three greens and two reds.
- The dark-mode brand green in charts (`#4ade80`) doesn't match the app's dark tokens (`#00d681` / `#22c55e`).
- Gain/loss is shown with red vs green only, which is hard to tell apart for colour-blind users.

---

## 1. Categorical palettes (arrays of colours for series, slices, brokers, signals)

| # | Name | File:line | Values | Count | Used by |
|---|---|---|---|---|---|
| P1 | `PALETTE_LIGHT` | `lib/components/charts/AllocationPieChart.svelte:110` | #1a4031 #2563eb #7c3aed #dc2626 #d97706 #0d9488 #be185d #4f46e5 #059669 #ea580c #6366f1 #0891b2 #ca8a04 #9333ea | 14 | Allocation pie/donut slices; subtypes get shades via `shadeForDepth` (§3) |
| P2 | `PALETTE_DARK` | `AllocationPieChart.svelte:111` | #4ade80 #60a5fa #a78bfa #f87171 #fbbf24 #2dd4bf #f472b6 #818cf8 #34d399 #fb923c #a5b4fc #22d3ee #facc15 #c084fc | 14 | Same chart, dark mode |
| P3 | `PALETTE` (light only) | `lib/components/charts/SemiDonutChart.svelte:68` | #1a4031 #2563eb #7c3aed #dc2626 #d97706 #0d9488 #be185d #4f46e5 | 8 | Semi-donut. These are the first 8 entries of P1. **There is no dark version.** |
| P4 | `PALETTE_LIGHT` | `lib/components/dashboard/AllocationHistoryChart.svelte:173` | #1a4031 #3b82f6 #f59e0b #ef4444 #8b5cf6 #06b6d4 #84cc16 #ec4899 #f97316 #14b8a6 #6366f1 #a3a3a3 #a21caf #7e22ce | 14 | Allocation-history stacked areas. Colours repeat after 14; a debug warning is logged (comment at ~165-172). |
| P5 | `PALETTE_DARK` | `AllocationHistoryChart.svelte:174` | #4ade80 #60a5fa #fbbf24 #f87171 #a78bfa #22d3ee #a3e635 #f472b6 #fb923c #2dd4bf #818cf8 #d4d4d4 #e879f9 #c084fc | 14 | Same chart, dark mode |
| P6 | `BROKER_PALETTE` | `lib/components/dashboard/GrowthChart.svelte:367-374` | light: #2563eb #d97706 #7c3aed #db2777 #0891b2 #65a30d · dark: #60a5fa #fbbf24 #a78bfa #f472b6 #22d3ee #a3e635 | 6 pairs | Per-broker P&L lines in the Growth chart, picked by index via `brokerColor()` (`:376`) |
| P7 | `DEFAULT_SIGNAL_COLORS` | `lib/charts/signals/ChartSignal.ts:194` | #3b82f6 #f59e0b #8b5cf6 #ec4899 #06b6d4 #84cc16 | 6 | Default colour when a signal is added; `registry.ts` picks the colour whose hue is farthest from those already used (§3). Same in light and dark. |
| P8 | `ROLE_COLORS` | `lib/charts/signals/signalVisualStyle.ts:3-9` | secondary #f59e0b, positive #16a34a, negative #dc2626, neutral #64748b, accent #8b5cf6 | 5 | Parts of backend indicators (e.g. MACD, Bollinger bands). Light only. |
| P9 | Geography choropleth (map shaded by value) | `lib/components/charts/GeographyMap.svelte:297` | light #f0fdf4 #bbf7d0 #86efac #4ade80 #22c55e #16a34a · dark #1e3a2f #22543d #276749 #2f855a #38a169 #48bb78 | 6+6 | Map colour scale (ECharts `visualMap`). The dark ramp is not Tailwind green. |
| P10 | Same choropleth, copied | `lib/features/tools/pac-allocator/planner/result/ExposureMaps.svelte:60-61` | same values as P9 | 6+6 | PAC planner exposure maps |
| P11 | Correlation scale | `lib/components/risk/CorrelationHeatmap.svelte:131-132` | light #b91c1c → #f8fafc → #1d4ed8 · dark #b91c1c → #334155 → #1d4ed8 | 3 stops | Heatmap from red (−1) through neutral to blue (+1); `CorrelationPairsList.svelte:55-56` reuses #1d4ed8 / #b91c1c |
| P12 | Allocation hierarchy fallbacks | `lib/components/charts/allocationHierarchy.ts:30-31` (doc) | #1a4031, #6366f1 | — | Comments explaining the lightness analysis of P1/P4 |
| P13 | Lot colours (generated) | `lib/components/brokers/lots/lotComparisonChartHelpers.ts:183` | `hsl(id·137.508 mod 360, 68%, 44%)` light / `78% 68%` dark | unlimited | Per-lot lines in `LotComparisonChart` |
| P14 | Broker colours (generated) | `lib/utils/broker/brokerColors.ts:36` → `getIndexColor(idx, 200)` | HSL by golden-ratio rotation | unlimited | Lot Gantt segments (`lotGanttChartHelpers.ts:141`), LotWacPriceChart broker colours (~`:979`), broker badges |

The ai-export feature (`lib/features/ai-export/**`) has no hex/HSL colours and no `fill=`/`stroke=` attributes, so it does not pick chart colours.

## 2. Colours with a fixed meaning

### Gain/loss and positive/negative

| Where | Positive | Negative | Neutral |
|---|---|---|---|
| `charts/lineChartHelpers.ts:46-51` (`COLORS`), used by `chartCoreHelpers.ts:47` `getChartColors` → Line chart, Candlestick (`CandlestickChart.svelte:363-367`, `color0`/`borderColor0` = red), Price chart | L #16a34a / D #4ade80 | **L #ef4444** / D #f87171 | — |
| `charts/priceChartHelpers.ts:588` `buildDeltaHtml` (Δ in tooltip) | **#10b981** (same both themes) | **#ef4444** | — |
| `dashboard/PerformanceChart.svelte:257-264` | #16a34a / #4ade80 | **#dc2626** / #f87171 | #64748b / #cbd5e1 |
| `dashboard/GrowthChart.svelte:1727-1728, 1793-1794, 2256` | #16a34a / #4ade80 | #dc2626 / #f87171 | — |
| `dashboard/ExposureTreemap.svelte:488-497` `pnlColor` (computed scale) | rgb(22,163,74) towards (12,133,94) / dark (34,197,94) towards (74,237,134) | rgb(220,38,38) towards (240,58,58) / dark (248,113,113) towards (248,73,73) | #6b7280 when value is null |
| `ExposureTreemap.svelte:595` | #16a34a / #4ade80 | #dc2626 / #f87171 | — |
| `dashboard/KpiSection.svelte:251` timing effect | rgba(22,163,74,α) | rgba(220,38,38,α) | — |
| `signals/signalVisualStyle.ts:5-6`, `SignalVisualLegend.svelte:118-120` | #16a34a | #dc2626 | #64748b |
| `brokers/lots/lotGanttChartHelpers.ts:123`, `lotWacPriceChartHelpers.ts:299-302`, `LotComparisonChart.svelte:855` | #16a34a / #4ade80 | #dc2626 / #f87171 | #64748b / #94a3b8 |
| `LotWacPriceChart.svelte:550,557` | #16a34a / **#86efac** | #dc2626 / **#fca5a5** | — |
| `features/tools/.../ExposureBars.svelte:29-30` | #1a4031 / **#00d681** (brand tokens) | — | #9ca3af / #6b7280 |

### Growth and Performance series (`GrowthChart.svelte:349-362`, `PerformanceChart.svelte:257-264`)

| Meaning | Light | Dark |
|---|---|---|
| NAV / total P&L line | #1a4031 | #4ade80 |
| Assets at cost (area) | #3b82f6 | #60a5fa |
| Contributed cash | #9caf9c (sage) | #6b8e6b |
| Generated cash | #10b981 | #34d399 |
| Capital baseline (dashed) | #6b7280 | #9ca3af |
| TWRR (% mode, `invested`) | #2563eb | #60a5fa |
| ROI (% mode, `pctCash`) | #9caf9c | #94a3b8 |
| **Dividend** | #b08d00 | #facc15 (also in `lotComparisonChartHelpers.ts:193`) |
| **Interest** | #7c3aed | #a78bfa; **#6d28d9** in `lotComparisonChartHelpers.ts:194` |
| **Costs (fees + tax)** | **#ea580c** in Growth | #fb923c |
| Costs in Performance | **#dc2626** | #f87171 |
| Income in Performance | #d97706 | #fbbf24 |
| Unrealized / Realized / Other (Performance) | #2563eb / #16a34a / #7c3aed | #60a5fa / #4ade80 / #a78bfa |
| Deposit | #0d9488 | #2dd4bf |

### Portfolio vs benchmark, risk, lots, other markers

| Meaning | Colour | Where |
|---|---|---|
| Portfolio | #0284c7 / #38bdf8 (sky) | `scatterChartHelpers.ts:191` |
| Benchmark | #d97706 / #fbbf24 (amber) | `scatterChartHelpers.ts:192` |
| Other assets | #64748b / #94a3b8 | `scatterChartHelpers.ts:193` |
| Selected point | #22c55e / #4ade80 | `scatterChartHelpers.ts:102` |
| Risk panel accents | #f59e0b and #2563eb | `RiskAnalysisPanel.svelte:235, 259` |
| L4 simulation | #2563eb | `levels/l4/L4Simulation.svelte:95` |
| Risk/return level tints | sky / amber / green at 10-14% alpha | `RiskReturnLevel.svelte:368-393` |
| Lot state: open / estimated / closed | sky #0284c7/#38bdf8, amber #d97706/#fbbf24, slate #64748b/#94a3b8 | `lotStateVisual.ts:19-26` |
| Gantt events: sell, transfer, split, buy | #dc2626, #7c3aed, #ca8a04, #059669 (with dark pairs) | `LotGanttChart.svelte:967` |
| Gantt in-transit / no broker | #7c3aed / #2563eb | `lotGanttChartHelpers.ts:142-143` |
| Lot comparison: residual, proceeds, income, original cost | #2563eb, #059669, #7c3aed, #475569 | `LotComparisonChart.svelte:870-873` |
| WAC chart lines | green, red, blue #1d4ed8/#93c5fd, amber #d97706/#fcd34d, violet #7c3aed/#c4b5fd | `LotWacPriceChart.svelte:550-578` |
| WAC market line | #16a34a / #4ade80 | `LotWacPriceChart.svelte:1291` |
| Stale-data warnings | #f59e0b (same both themes) | `priceChartHelpers.ts:615`, `CandlestickChart.svelte:523,526`, `LineChart.svelte:121,780` |
| Map highlight | #f59e0b / #fbbf24 | `GeographyMap.svelte:316,320`, `ExposureMaps.svelte:158` |
| Measure tool | #f97316 | `signals/MeasureSignal.ts:44` |
| Event markers on comparison overlays | the signal's own colour, else #6b7280 | `priceChartHelpers.ts:530` |
| Price line (compact chart) | #1a4031 | `PriceChartCompact.svelte:35` |
| Signal default colour | #3b82f6 | `ChartSignal.ts:153`, `registry.ts:37` |

### Axes, grid and tooltips: four slightly different sets

| Helper | Axis line | Labels | Grid / split lines | Tooltip background / border / text |
|---|---|---|---|---|
| `chartCoreHelpers.ts:47-55` `getChartColors` | #d1d5db / #475569 | #6b7280 / #94a3b8 | #d1d5db / **#4b5563** | — |
| `echartsTooltipHelpers.ts:161` `buildGridColors` | — | #64748b / #94a3b8 | **#f1f5f9 / #1e293b** | — |
| `echartsTooltipHelpers.ts:26` `buildTooltipTheme` | — | — | — | #fff / #1e293b · #e2e8f0 / #334155 · #1e293b / #e2e8f0 (muted #64748b / #94a3b8) |
| Inline in `CandlestickChart.svelte:541-547` | — | — | — | border **#e5e7eb**, text **#111827** / #e2e8f0; titles **#1f2937** (`:191-202`) |
| Inline in `PriceChartFull.svelte:868-918`, `LineChart.svelte:704-706`, `AllocationHistoryChart.svelte:652-655`, `SemiDonutChart.svelte:296-298`, `AllocationPieChart.svelte:470-472` | — | — | — | copies of the `buildTooltipTheme` values |
| `PerformanceChart.svelte:652, 957` | — | — | rgba(148,163,184,0.12–0.16) | — |
| `CorrelationHeatmap.svelte:521` | — | — | — | rgba(255,255,255,0.95) / rgba(2,6,23,0.95) |

## 3. Functions that compute colours

| Function | File:line | How it works | Input → output | Used by |
|---|---|---|---|---|
| `getIndexColor(index, startHue=140, opts?)` | `lib/utils/colors.ts:36` | Hue = start + index × 0.618 × 360 (golden ratio); saturation 35–55% varying by index; fixed lightness 92/30 (light bg/text) and 25/82 (dark); `vivid` = 75%/50%, `vividLight` = 60%/80% | number → `ColorSet` of `hsl()` strings | `getBrokerColor`, `getPriorityBadgeStyle`, `getStringColor` |
| `getProviderColor(code)` | `colors.ts:76` | Fixed hues for ECB 220, FED 30, BOE 150, SNB 340, MANUAL 0; other codes are hashed (×127) then golden-ratio spread; saturation 55% with alpha 0.12–0.3 | string → `{bg, darkBg, border, darkBorder}` | FX provider chips |
| `getPriorityBadgeStyle(i)` | `colors.ts:117` | `getIndexColor(i, 140)` turned into CSS variables | → style string | Badges |
| `hslToHex` / `hexToHsl` | `colors.ts:128` / `:157` | Exact conversion both ways | | `shadeForDepth`, colour inputs |
| `hashString` (private), `getStringColor(label, 200)`, `getStringBadgeStyle` | `colors.ts:189`, `:208`, `:217` | djb2 hash with XOR fold, fed into `getIndexColor` | string → `ColorSet` | Tag chips |
| `getBrokerColor(id, brokers)` | `utils/broker/brokerColors.ts:36` | Position of the broker when sorted by id → `getIndexColor(idx, 200)` | → `ColorSet` | Lot Gantt, WAC chart, broker badges, `UnifiedLotsTable` (`color-mix`) |
| `shadeForDepth(base, depth, step, groupSize?)` | `components/charts/allocationHierarchy.ts:137` | Convert to HSL and move lightness away from the nearer extreme by `step × depth`. Groups larger than 3 spread shades on both sides and halve saturation on even depths. Returns the base colour if it isn't hex. | hex → hex | Allocation pie subtypes (P1/P2) |
| `hexToHue` + max-distance picker | `lib/charts/signals/registry.ts:37` onward | Picks the palette colour whose hue is farthest (around the wheel) from colours already used | used colours → hex | Adding new signals (P7) |
| `resolveSignalColor(base, role)` | `signalVisualStyle.ts:11` | `primary` keeps the base colour, other roles use fixed `ROLE_COLORS` | → hex | Backend indicator parts |
| `hexToRgba(hex, α)` | `lineChartHelpers.ts:21` | Parses `#rrggbb` only (breaks on `#rgb` or `hsl`) | → `rgba()` | Line/area fills |
| `getStaleOpacity(days, max=14)` | `lineChartHelpers.ts:~33` | Opacity falls linearly from 1 to 0.15 | → number | Line chart staleness fading |
| `withAlpha(color, α)` | `brokers/lots/lotChartShared.ts:71` | `hsl()` → `hsla()`; `#rrggbb` → `#rrggbbaa`; anything else unchanged | | Lot charts (e.g. `LotGanttChart.svelte:848`) |
| `lotColor(lotId, isDark)` | `lotComparisonChartHelpers.ts:183` | Hue = id × 137.508 (golden angle) | → `hsl()` | LotComparisonChart |
| `incomeEventColor`, `signedColorField`, `segmentBaseColor`, `lotBubbleSignColor`, `lotStateColor` | `lotComparisonChartHelpers.ts:192`, `lotGanttChartHelpers.ts:119,141`, `lotWacPriceChartHelpers.ts:299`, `lotStateVisual.ts:19` | Choose between fixed light/dark pairs | | Lot charts |
| `brokerColor(index, isDark)` | `GrowthChart.svelte:376` | P6 indexed modulo 6 | | Growth broker overlay |
| `pnlColor(pct)` | `ExposureTreemap.svelte:488` | Linear RGB interpolation; intensity = min(|pct|×100, 50)/50; reads the `dark` class itself | → `rgb()` | Treemap tiles |
| `timingColor(base, span)` | `KpiSection.svelte:249` | Alpha = base + intensity × span on fixed green/red | → CSS | KPI text |
| `colorForRole`, `selectedColor` | `scatterChartHelpers.ts:190`, `:101` | Fixed pairs | | Risk-return scatter chart |
| `otherEffectColor(category, dark)` | `PerformanceChart.svelte:~267` | Category → value from `palette()` | | Performance chart |
| `getChartColors`, `buildTooltipTheme`, `buildGridColors` | `chartCoreHelpers.ts:47`, `echartsTooltipHelpers.ts:26, 161` | Theme getters returning hardcoded pairs | `isDark` → object | Line, Price and Candlestick charts |

## 4. Dark mode in charts

**How it works:** each chart checks `document.documentElement.classList.contains('dark')` (e.g. `LineChart.svelte:366`, `PriceChartFull.svelte:688`, `GrowthChart.svelte:1958,2130`, `AllocationPieChart.svelte:172`, `ExposureTreemap.svelte:490,549`, `PerformanceChart.svelte:428`, the three Lot charts at `:221/:245/:339`). Each chart then chooses from hardcoded light/dark pairs. No chart reads `--theme-*` (the only `getComputedStyle` calls measure layout or fonts: `AllocationHistoryChart.svelte:266`, `ExposureTreemap.svelte:232`, `riskReturnLevel.ts:120`). `CandlestickChart` also accepts an `isDarkProp`.

**Re-rendering on theme change:** each chart sets up its own `MutationObserver` on the `class` attribute of `<html>`. This is in AllocationPie `:118`, Candlestick `:145`, LineChart `:170`, PriceChartFull `:257`, GeographyMap `:103`, ScatterChart `:82`, AllocationHistory `:188`, ExposureTreemap `:92`, GrowthChart `:1999`, PerformanceChart `:1116`, CorrelationHeatmap `:300`, LotWac `:1714`, LotGantt `:1333`, LotComparison `:1259`, ExposureBars `:48`, ExposureMaps `:100`, and OtherPeriodEffectsTable `:208` (a table).

**Not (fully) theme-aware:**
- **SemiDonutChart:** its slice palette P3 (`:68`) is light-only, so `#1a4031` (brand dark green) is nearly invisible on the dark card (#1e293b). Its text, labels and tooltip do switch (`:188` onward).
- **Signal palettes P7/P8:** one set of colours for both themes. #16a34a, #dc2626 and #64748b are dark and lose contrast on #0f172a / #1e293b.
- **Fixed in both themes:** `buildDeltaHtml` (#10b981 / #ef4444), the stale-warning amber #f59e0b, MeasureSignal #f97316, the event-marker fallback #6b7280, ExposureTreemap's null colour #6b7280, `PriceChartCompact` #1a4031 (`:35`, apparently a fixed default line colour), and L4Simulation / RiskAnalysisPanel #2563eb / #f59e0b.
- **CorrelationHeatmap:** the end colours #b91c1c and #1d4ed8 are the same in both themes; only the neutral middle changes.
- **KpiSection:** the timing-effect rgba colours are the same in both themes.

## 5. Consistency findings

**Same meaning, different colours**
1. **Gain green:** #16a34a in most places, #10b981 in tooltip deltas (`priceChartHelpers.ts:588`), #22c55e in the geo ramp and scatter selection. Dark mode uses #4ade80, #86efac (WAC) or #22c55e (`--theme-accent`).
2. **Loss red:** #dc2626 (Performance, Growth, Treemap, Lots, Signals) vs #ef4444 (`lineChartHelpers.ts:50`, so Line/Candle/Price charts, and Δ tooltips). Dark mode: #f87171 vs #fca5a5 (WAC).
3. **Costs:** orange #ea580c in Growth vs red #dc2626 in Performance.
4. **Interest:** #7c3aed in Growth and Performance vs #6d28d9 in `lotComparisonChartHelpers.ts:194`.
5. **Income:** amber #d97706 in Performance; dividend gold #b08d00 in Growth and Lots.
6. **Dark brand / NAV / main line:** #4ade80 in charts vs `--color-libre-green` dark #00d681 (`app.css:151`) and `--theme-accent` dark #22c55e (`app.css:167`). Only `ExposureBars.svelte:30` uses #00d681.
7. **Tooltip and axis neutrals** come from four helper sets plus inline copies (table in §2). For example the dark grid line is #4b5563 in one helper and #1e293b in another; the light tooltip border is #e2e8f0 vs #e5e7eb; title text is #1e293b, #1f2937 or #111827.
8. **Blue TWRR vs assets at cost:** #2563eb vs #3b82f6 in the same Growth chart, both #60a5fa in dark mode.

**Same colour, different meanings**
- #7c3aed / #a78bfa: interest (Growth), "other effects" (Performance), in-transit and transfer (Gantt), income (LotComparison), and slot 3 of the allocation palette.
- #d97706 / #fbbf24: benchmark (scatter), estimated lot state, income (Performance), broker slot 2 (P6), allocation slot 5.
- #16a34a / #4ade80: gain, realized P&L, WAC market line, scatter selection, and dark-mode slot 1 of P2/P5 (the NAV/brand colour). An allocation slice can be the same green as "gain".
- #dc2626 / #f87171: loss, costs, sell events, and slot 4 of the allocation palettes. An allocation slice can look like a loss.
- #f59e0b: stale warning, map highlight, signal "secondary" role, signal palette slot 2, allocation-history slot 3.
- #2563eb: unrealized P&L, TWRR, broker slot 1, risk accents, Gantt "no broker", allocation slot 2.

**Duplicated palettes**
- P1, P3 and P4 are three separate allocation palettes. P3 is a prefix of P1. P1 and P4 share #1a4031, #6366f1 and most of the dark entries, but in a different order. The same category therefore gets different colours in the Allocation pie and in Allocation history.
- P6 and P7 are both blue/amber/violet/pink/cyan/lime with different shades (600 vs 500).
- P9 and P10 are copied, not shared.
- Code comments already admit there is no shared palette module: `GrowthChart.svelte:357-358` and `lotComparisonChartHelpers.ts` say "change both together".

**Match with `app.css` tokens**
- `--theme-*` text and border colours are Tailwind **gray** (#111827, #4b5563, #6b7280, #9ca3af, #e5e7eb) in light mode and **slate** in dark mode. Charts mix gray (#6b7280, #d1d5db, #9ca3af) and slate (#64748b, #94a3b8, #e2e8f0) inside light mode.
- Light tooltip border #e2e8f0 differs from `--theme-border-primary` #e5e7eb.
- Dark tooltip background #1e293b matches `--theme-bg-card`.
- Sage #9caf9c (`--color-libre-sage`) is used for contributed cash in light mode; in dark mode the charts use #6b8e6b, which is not a token.
- The brand primary scale (`--color-primary-*`) is not used in charts except #1a4031.

**Colour-blind safety**
- Gain/loss everywhere is red vs green only: candlesticks, Performance bars, treemap, Lot P&L, KPI timing, signal positive/negative. The treemap encodes P&L only through red↔green colour strength.
- The geography ramp is a single green hue (fine). The correlation heatmap is red↔blue (fine).
- Within P1, slots #1a4031 (dark green) and #dc2626 (red), and #059669 vs #0d9488, are hard to separate for colour-blind users.

**Neighbouring palette entries that look alike**
- P1: #4f46e5 / #6366f1 / #7c3aed / #9333ea (four indigo/violet entries); #0d9488 / #059669 / #0891b2; #d97706 / #ca8a04 / #ea580c.
- P2: #818cf8 / #a5b4fc / #a78bfa / #c084fc; #2dd4bf / #34d399 / #22d3ee; #fbbf24 / #facc15.
- P4: #8b5cf6 / #6366f1 / #a21caf / #7e22ce; #06b6d4 / #14b8a6.
- Generated golden-ratio hues (lots, brokers) have no lightness variation in chart use, so with many items hues collide.

**Other oddities**
- `ExposureTreemap.pnlColor` in light mode: bigger gains get darker, but bigger losses get *lighter* (220→240, 38→58), so the light-mode loss scale goes the opposite way to the gain scale.
- `hexToRgba` (`lineChartHelpers.ts:21`) silently breaks if given `#rgb` or `hsl()` colours.

## 6. Open questions for the designer

1. Should there be one source of chart colours, either CSS custom properties (e.g. `--chart-gain`, `--chart-loss`, `--chart-cat-1…n`) read at runtime, or a single TS module? Today every chart hardcodes its own pairs.
2. Which exact gain and loss colours, per theme? Should gain/loss get a second cue for colour-blind users (▲/▼, patterns, or a blue/orange option)?
3. Should the dark-mode brand/NAV line follow `--color-libre-green` #00d681, `--theme-accent` #22c55e, or keep #4ade80?
4. Should allocation categories have one shared palette for the Pie, Semi-donut and Allocation-history charts, so a category keeps its colour across charts? Should that palette leave out the reserved gain/loss/brand colours (green, red, #1a4031)?
5. How many categorical colours are needed (14 today, with repeats beyond that), and should the palette be ordered for maximum contrast between neighbours?
6. Should income/costs/dividend/interest get a fixed set of meaning colours (costs orange or red? interest #7c3aed or #6d28d9?), kept apart from the colours used for categories?
7. Should benchmark vs portfolio (amber vs sky today) be the same in every chart, including Growth signals?
8. Should signal default colours and indicator role colours get dark-mode versions?
9. Should neutral chart colours (axes, grid, tooltips, labels) use the `--theme-*` gray/slate tokens, ending the mix of gray and slate within one theme?
10. Is the light-only SemiDonut palette intended? It needs a dark version.
11. For treemap and heatmap colour scales: what range, which neutral middle point, and which direction should the scale run?
12. Should generated colours (lots and brokers via golden-ratio hues) stay, or be replaced by a curated, colour-blind-safe sequence?