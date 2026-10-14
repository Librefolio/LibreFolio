# 05 — Historical color studies & decisions (historical data only)

> Collected 2026-10-14 from `LibreFolio_developer_journal/` and `LibreFolio_devWiki/`. **Historical, not current truth**: status notes come from quick greps in `frontend/src`, nothing rendered.
> Finding: **no single dedicated "color study" exists**; color work is spread over the items below (search for colorblind/WCAG/"studio colori" found nothing standalone).

## 1. Chronology

| # | When | Document | Decided / proposed | Status today |
|---|---|---|---|---|
| 1 | 2026-01-08, Phase 0 setup | `RoadmapV4_UI/phases/phase-00-setup.md:40-43`; repeated in `knowledge_base/02_frontend.md:43`, `05_project_conventions.md:70-75` (colors only in CSS `@theme`) | Brand tokens: `libre-green #1a4031`, `libre-beige #f5f4ef`, `libre-sage #9caf9c`, `libre-dark #111111` | Present `app.css:15-19`. **Undocumented drift**: dark `--color-libre-green: #00d681` (`app.css:151`) |
| 2 | Phase 4 (undated) | `RoadmapV4_UI/phases/phase-04-subplan/GUIDA-DARK-MODE.md` | `--theme-*` dark set on slate: bg `#0f172a/#1e293b/#334155`, text `#f8fafc/#cbd5e1/#64748b/#94a3b8`, borders `#334155/#1e293b`, accent `#22c55e`/`#16a34a`. Optional high-contrast variant (l.59-81): bg `#0a0f1a/#1a2332/#2a3342`, input border `#546175`, text `#e2e8f0/#a8b4c4`, inputs on bg-tertiary | Base set present `app.css:153-167`; high-contrast variant **never adopted** (only `#546175` survived, as dark input border) |
| 3 | RoadMapV2 | `RoadMapV2/frontendIdeas/frontend_integration_plan.md` | nothing color-related | — |
| 4 | Phase 5 (by 2026-03-11) | `RoadmapV4_UI/phases/phase-05-subplan/plan-fxCardRedesignChartSettings.prompt.md:139-141,449` | `DEFAULT_SIGNAL_COLORS = #3b82f6 #f59e0b #8b5cf6 #ec4899 #06b6d4 #84cc16`, rotation; per-signal color picker; `colorByBaseline` default true | Present `lib/charts/signals/ChartSignal.ts:194` |
| 5 | Phase 6 Step 4 Plan A, Bugfix 6/7 | `phase-06-subplan/Bugfix-Step4/PlanA/plan-phase06Step4PartA-Bugfix_6_ClassifTooltipEventMarkers.prompt.md:71-75,117`, `…Bugfix_7_EventMarkersFxAutoSyncSectorMapping.prompt.md:125-129,215-217` | `EVENT_COLORS`: INTEREST `#10b981`, DIVIDEND `#3b82f6`, PRICE_ADJUSTMENT `#f59e0b`, MATURITY_SETTLEMENT `#ef4444`, SPLIT `#8b5cf6`, fallback `#6b7280`. Tooltip dark/light: bg `#1e293b/#ffffff`, border `#334155/#e2e8f0`, text `#e2e8f0/#1e293b` | `EVENT_COLORS` symbol not found; dividend later moved to gold (#9) → partly superseded |
| 6 | Release 2, Riskfolio, decision D71 ("Mandato G") | `Release_2/Phase_0/02_riskfolioIntegration/implementation/G-frontend-colori-allocazione.md`, `…/progress/G-esecuzione.md` | Subtypes = shifted shade of the parent category color (exact numbers in tooltip); same in stacked history; color per data item, not series index; history palette 12→14 (wrap-around collision); slots 13/14 `#a21caf/#e879f9`, `#7e22ce/#c084fc`; `#0f172a` rejected (too close to `#1a4031`). Note: dark palettes uniformly light, light ones not (`#6366f1` L=67). Gotcha: alpha by string concat `+ '88'` only works for 6-digit hex | Present: `AllocationHistoryChart.svelte:173`, `AllocationPieChart.svelte:110-111`; `SemiDonutChart.svelte:68` still separate 8-color light-only palette |
| 7 | 2026-09-24/25 | `LibreFolio_devWiki/wiki/decisions/heatmap-emphasis-is-hue-free.md` | Correlation red(−1)→blue(+1); selected cell = **neutral** border (light `#0f172a` + white halo; dark `#ffffff` + `rgba(2,6,23,.95)` halo). Rejected: amber glow, green `#22c55e` glow, dimming. Rule: emphasis on diverging scales by luminance, not hue | Present `risk/CorrelationHeatmap.svelte:521`; label text flips `#ffffff/#0f172a` at |v|≥0.6 (`:284`) |
| 8 | 2026-10-01, D26 | `Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsRound4-PostMergeReview.prompt.md:544,5208-5255,5846` | New capital in Income: sage `#9caf9c/#6b8e6b` → KPI blue `cc('bookAssetLike')` `#3b82f6/#60a5fa` (= `bg-blue-500/dark:bg-blue-400`); reinvested stays emerald `#10b981/#34d399`. Principle: **same name, same color** | Present; pinned by `chartCoreHelpers.test.ts:4023-4027`. Sage still in `GrowthChart.svelte:351,355` |
| 9 | 2026-10-07 | `Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsIncomeColorsAxisLabels.prompt.md:53,88-106,545`; `devWiki/wiki/concepts/echarts-chart-gotchas.md:38-39` | Dividends → gold `#b08d00`/`#facc15` everywhere incl. lots. Why: dividend teal `#0891b2` vs deposit teal `#0d9488` too similar; yellow-600 `#ca8a04` only 2.94:1 on white (< WCAG 1.4.11 3:1). Measured: `#b08d00` 3.16:1 on white, `#facc15` 9.55:1 on `#1e293b`; ΔE vs neighbours (dark gold ≈ broker amber `#fbbf24`, ΔE 5.1, accepted). Broker palette untouched. "Rich token" idea (§10) declared superseded (l.596) | Present `GrowthChart.svelte:359`, `lotComparisonChartHelpers.ts:193`. **Drift:** rejected `#ca8a04` still used for SPLIT (`LotGanttChart.svelte:967`) and in `AllocationPieChart` `PALETTE_LIGHT` |

## 2. Principles already agreed in the past (reusable by the designer)

- Brand green `#1a4031` first in categorical palettes.
- **Same meaning → same color** (D26, dividend gold).
- **Measure contrast** (WCAG 1.4.11, 3:1 for graphics) and ΔE vs neighbours before adopting a color.
- **Emphasis by luminance, not hue** on diverging scales.
- **Color per data item**, never by series index; avoid palette wrap-around.
- **Subtypes = shades of the parent hue.**
- Tailwind 500/600/700 in light, 400 in dark, paired by hand (no shared chart token layer; `cc()` helper only in some charts).
- Colors defined only in CSS `@theme` (Tailwind v4 convention).

## 3. Abandoned ideas
Amber / green heatmap highlights, cell dimming, high-contrast dark variant, `#0f172a` as palette color, sage for new capital, teal for dividends, "rich token" chart-color idea.

## 4. Gaps left by history
- No colorblind study at all (red/green gain/loss everywhere).
- No documented decision for the dark brand green `#00d681`, nor for the `!important` dark remap layer in `app.css`.
- No unified categorical palette across allocation charts.

## 5. Open questions
1. Keep/document dark `--color-libre-green: #00d681` (≠ dark accent `#22c55e`)?
2. Remove `#ca8a04` from Gantt SPLIT and AllocationPie (fails 3:1, already rejected once)?
3. Unify allocation palettes (pie, history, semi-donut) and keep signal/event palettes separate or not?
4. Gold `#facc15` = dividend (Growth) and SPLIT dark (Gantt): acceptable collision?
5. Was old `EVENT_COLORS` (dividend blue) fully migrated to gold?
6. Colorblind-safety pass on palettes?
7. Central chart tokens (TS module or CSS vars)?
