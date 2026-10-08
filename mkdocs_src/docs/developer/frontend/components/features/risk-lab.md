# 🧪 Risk UI: Correlation and Dashboard Risk Tabs

This page covers the **UI rules** of two risk surfaces. The **Correlation** tab of the Assets page — the
*Asset Global* lab — runs the risk engine on a hand-picked selection of assets
(`{kind: "asset_set", asset_ids: [...]}`): how the selection is built and kept, how the engine's
eligibility verdicts are used, which requests each section sends, and how each section draws and
discloses its results. The **Risk** tab of the Dashboard and of Broker Detail runs it on a portfolio
(`{kind: "portfolio", broker_ids: [...]}`) as four levels: see [Dashboard Risk Tab](#dashboard-risk-tab).

It does not repeat the engine. The request flow, the analytics, the eligibility rules and thresholds, the
panel controller and the shared benchmark store are in
[Risk Engine](../../../backend/risk/architecture.md); the mathematics is in
[Risk Metrics](../../../../financial-theory/technical-analysis/risk-metrics/index.md); what users see is in
the [Correlation Tab](../../../../user/assets/correlation.md) and
[Risk Tab](../../../../user/dashboard/risk.md) user pages.

Paths are relative to `frontend/src/lib/components/risk/` unless stated otherwise. The lab never shows an
amount of money: a selection has no weights.

---

## 🗺️ Source Map {: #source-map }

| Source | Responsibility |
|---|---|
| `frontend/src/routes/(app)/assets/+page.svelte` | Mounts the lab on the Correlation tab with the page's full asset list; hides the list filters there (l.1310); its toolbar's **Sync selection** and **Reload All** call the lab's `openSync()` and `reload()` (l.1509, l.1524); `onfitperiod` moves the toolbar range (l.1609-1614); `targetCurrency` is the instance default currency (l.1618). |
| `AssetSetRiskPanel.svelte` | The lab: selection card, eligibility, holdings command, benchmark picker snippet, banner and notice, and the four sections (l.847-864). |
| `assetSetSelection.ts` | Opening selection, persistence, bulk actions, `labBenchmarkId()`, `labL3Waits()`. |
| `eligibility.ts` | Reads and words the engine's verdicts; batches; `fitPeriodOffer()`. |
| `LabAssetPicker.svelte` | The **+**: `AssetPickerPanel` in multi mode. |
| `AssetSetCorrelationSection.svelte`, `CorrelationHeatmap.svelte`, `CorrelationPairsList.svelte`, `correlationHelpers.ts`, `matrixMetadata.svelte.ts` | Correlation section. |
| `AssetSetComparisonLevels.svelte`, `AssetSetLossComparisonSection.svelte`, `AssetSetRiskReturnSection.svelte`, `RiskReturnLevel.svelte`, `assetSetLevels.ts`, `assetSetTable.ts` | L1° (losses) and L3° (risk and return). |
| `AssetSetReplaySection.svelte`, `levels/l4/L4Replay.svelte`, `levels/l4/TornadoChart.svelte` | L4° (historical replay). |
| `levels/RiskLevelSection.svelte`, `levels/RiskPartialNotice.svelte`, `levels/partialNotice.ts`, `levels/levelMetadata.ts`, `syncTargets.ts` | Section frames, the shared notice, banner actions. |

The UI strings live under `risk.assetSet.*` (lab-only) and `risk.levels.*` (shared with the Dashboard).

---

## 🧺 Selection {: #selection }

### 🚪 Opening Selection {: #opening-selection }

`resolveInitialSelectionWithSource()` (`assetSetSelection.ts:137`) picks the first rung that yields ids,
and the card publishes it as `data-selection-source` (`AssetSetRiskPanel.svelte:707`):

1. **`persisted`** — the last selection, stored in `localStorage` under
   `lf_<userId>_assetGlobal.riskSelection.v1` (`assetSetSelection.ts:39`, l.64) and intersected with the
   page's list, so deleted or merged ids drop out.
2. **`mine`** — the assets held on `dateEnd` in every accessible broker. `heldAssetIds()` reads a light
   `fetchReport()` without the daily and allocation histories (`AssetSetRiskPanel.svelte:509`), asks once
   more when it answers `null` (l.510-516), and keeps only ids of the page's list.
3. **`fallback`** — the `FALLBACK_SELECTION_SIZE` (6) active assets with the most transactions, ties by
   id (`assetSetSelection.ts:37`, l.165).

Every rung is capped at `MAX_SELECTED_ASSETS` (100, `assetSetSelection.ts:31`), which is the API's limit
for the scope. A change the user makes while rung 2 is loading wins: the late seed is dropped
(`selectionTouched`, `AssetSetRiskPanel.svelte:466`). Every later change is written back (l.479).

### 🧰 Bulk Actions and Holdings {: #bulk-actions }

- `applyBulkAction()` (`assetSetSelection.ts:198`) acts on `candidates`: the page's list minus the
  `ineligible` assets (`AssetSetRiskPanel.svelte:347`). Neither the **+** filters nor the Assets-tab
  filters narrow it. `all` adds every candidate, inactive ones included, up to 100; `none` empties the
  selection, parked assets included; `invert` swaps the candidates and leaves parked assets where they
  are.
- **My assets** runs `runHoldingsPreset(brokerId | null)` (`AssetSetRiskPanel.svelte:537`): it
  **replaces** the selection with the assets held on `dateEnd` (all accessible brokers, or one), sliced
  to 100 (l.554), ineligible ones included. It is a command, not a filter: a date change does not run it
  again. A failed report sets `risk.states.loadFailed` (l.547); nothing held leaves the selection as it
  was and shows `risk.assetSet.preset.noneHeld` (l.551).
- The **+** is `LabAssetPicker.svelte`, a thin wrapper around
  [AssetPickerPanel](../core-ui/select.md#assetpickerpanel) in multi mode: rows in name order, a search
  over the name, the currency and the type label (`searchText`, `LabAssetPicker.svelte:60`), and
  `room = 100 − selection size` (`AssetSetRiskPanel.svelte:368`). The panel's own behaviour (Select
  visible, filters, blocked section) is documented there.

### ✅ Eligibility in the Lab {: #eligibility }

The rules behind `POST /api/v1/risk/eligibility` — the reasons, the 20-quote floor, the seven-day
lateness, `common_range` and `suggested_range` — are in
[Analysis Eligibility](../../../backend/risk/architecture.md#eligibility). The lab uses the verdicts in
three ways:

- **The whole list is asked**, in batches of `ELIGIBILITY_BATCH` (500, `eligibility.ts:47`), after a
  300 ms debounce (`AssetSetRiskPanel.svelte:246`), and again when the list, the period or the currency
  changes; a superseded answer is dropped. A failed call leaves no verdict (l.294-295): every asset stays
  selectable and the card shows `risk.assetSet.eligibilityFailed`.
- **An `ineligible` asset is parked**: it stays in `selectedAssetIds` as a dashed chip, with the reasons
  in its tooltip, but only `analysedIds` (l.357) reaches the sections. The counter shows
  `analysedIds.length` of `candidates.length` (l.791). A warning chip is analysed.
- **The selection is asked again on its own** (`selectionVerdicts`, l.316-340), so that unselected assets
  cannot narrow the period offered. `fitPeriodOffer()` (`eligibility.ts:109`) returns the answer's
  `suggested_range` when at least one selected asset is not `eligible` and is not `no_price_history`.
  The ranges survive only a single-batch answer, which a selection of at most 100 ids always is. The
  strip's button calls `onfitperiod`; the page clears its preset badge and applies the range to the
  toolbar (`+page.svelte:1609-1614`).

---

## 🔌 Requests and the Shared Window {: #requests }

Each section owns a controller (`createRiskPanelController`), and all four are mounted under the panel's
`{#if analysedIds.length > 0}` (`AssetSetRiskPanel.svelte:847`), so an empty selection never reaches the
API. Which analytics each section asks for is the table in
[By Level](../../../backend/risk/architecture.md#by-level).

| Section | Controller | Benchmark |
|---|---|---|
| Correlation | `AssetSetCorrelationSection.svelte:64` | Never |
| L1° *How much did each of these hurt?* | `lossController`, `includeAssetSetLossLevels` (`AssetSetComparisonLevels.svelte:114-123`) | Never |
| L3° *What did each of these pay for its risk?* | `RiskControllerHost`, `includeAssetSetPaidLevels` (`AssetSetComparisonLevels.svelte:244`) | `assetSetBenchmarkId` (l.138) |
| L4° *What if…?* | `AssetSetReplaySection.svelte`, replay on demand | Never |

- **Rates.** Every lab controller sends `appliedRiskFreePercent: 0` (`AssetSetCorrelationSection.svelte:72`,
  `AssetSetComparisonLevels.svelte:120`, l.136, `AssetSetReplaySection.svelte:84`), and the KPI and the
  comparison send `target_annual_return: 0` (`riskAnalysisHelpers.ts:334`, l.368-371). The lab has no
  control for either.
- **Bad month.** `MONTHLY_VAR_HORIZON_DAYS = 30` calendar days (`riskAnalysisHelpers.ts:280`, used at
  l.340). The engine turns them into observations at the observed frequency — about 21 on a
  trading-day calendar, 30 on an every-day one — as explained in
  [Value at Risk](../../../../financial-theory/technical-analysis/risk-metrics/value-at-risk.md#the-observation-count-is-not-the-history-length).
- **One calendar per request.** The engine prepares one joint calendar per request from the scope, the
  window and the currency ([Request Flow](../../../backend/risk/architecture.md#request-flow), step 4).
  Requests that agree on those three share it, so a matrix cell, an L1° row and an L3° dot cover the same
  dates (`AssetSetComparisonLevels.svelte:20-29`). A benchmark joins only L3°'s request, so only L3°'s
  window can move with it; its period line says so. How a short history narrows the calendar is in
  [Alignment](../../../../financial-theory/technical-analysis/risk-metrics/data-quality.md#alignment-what-missing-data-actually-costs).
- **L3° waits.** `labBenchmarkId()` (`assetSetSelection.ts:228`) passes a benchmark only in state `set`.
  `labL3Waits()` (l.245) keeps L3°'s controller unmounted while the picker is `pending`, or while a chosen
  benchmark waits for the lab's verdicts, so L3° asks once and never tries a benchmark that turns out
  `blocked`. The Beta and Correlation columns follow the answer, not the choice:
  `benchmarkApplies = benchmarkId !== null && comparison.status === 'ok'`
  (`AssetSetComparisonLevels.svelte:207`).
- **Sync and reload.** `openSync()` opens a `PageSyncModal` on the selection's prices and the configured
  FX pairs that convert them (`buildSyncTargets()`, `syncTargets.ts:43`). After an accepted sync, and on
  `reload()`, the panel calls `invalidateRisk()` and bumps `refreshVersion` for every section
  (`AssetSetRiskPanel.svelte:200-228`); the replay also forgets its answer
  (`AssetSetReplaySection.svelte:99`).

---

## 🕸️ Correlation Section {: #correlation-section }

- **Triangle.** Only the strict lower triangle is drawn: the first asset has no row and the last has no
  column (`CorrelationHeatmap.svelte:172`, `lowerTrianglePoints()` in `correlationHelpers.ts:439`). Fewer
  than two assets draw nothing (l.424). A cell prints ρ with two decimals (l.506); the tooltip gives ρ
  with three, its band, the observations and coverage of the pair, and each asset's three largest
  sectors and countries plus a folded rest (l.343, l.487-489). The colour scale runs red at −1, neutral at
  0 and blue at +1 (l.128-129).
- **Bands and lists.** `correlationBand()` (`correlationHelpers.ts:69-82`): `high` above 0.7, `inverse` at
  −0.3 or below; `near-identical` at 0.9 or above (`NEAR_IDENTICAL`, l.268). `topPairs()` (l.290) lists
  only `high` pairs (*The most alike*) and `inverse` pairs (*The ones that offset*), five each; past
  `PAIR_LIST_THRESHOLD` (20) assets it lists eight, and the lists move ahead of the matrix on `lg`
  screens (`CorrelationHeatmap.svelte:290`, l.616). The *opposite* tag starts at `OPPOSITE = −0.7`
  (`CorrelationPairsList.svelte:47`); a pair's colour follows the heatmap's polarity (l.62).
- **Orderings.** `similarity`, the default, is `clusterOrder()` (`correlationHelpers.ts:148`):
  average-linkage clustering on `1 − |ρ|`, a missing pair at distance 1 (l.124-127), ties broken by
  position. `type` follows the asset-type menu order, then the name. `sector` and `region` use
  `dominantExposure()` (l.362): the key holding at least `DOMINANT_SHARE` (0.5, l.337) of the classified
  weight, *Other* left out; `exposureOrder()` (l.396) then sorts named groups, *Diversified*, *Other*
  only and *Unclassified*. A mode is offered only when its data exist (`CorrelationHeatmap.svelte:93`).
  The sector and country distributions come from one bulk `GET /api/v1/assets?asset_ids=…`
  (`matrixMetadata.svelte.ts:85`); a failed read only hides those two buttons.

---

## 📉 Loss Table (L1°) {: #loss-table }

- **Columns by horizon**: Bad day, Bad month, Worst fall (with its `lasted N d` line), Below peak now,
  Rise to peak (`AssetSetLossComparisonSection.svelte:178-224`). The order is the point: a one-day loss
  printed beside a multi-year drawdown must not read as something to add up.
- **Signs.** The VaR/CVaR contract is positive and the drawdown contract negative; both are drawn as
  falls with U+2212 (`fall()`, l.106) and sorted as drawn (`drawnLoss()`, l.120), an unmeasured cell
  last. Every loss uses one red (l.124): no per-asset colour, no ranking.
- **Rows.** Rows come from the selected ids, so every analysed asset has one and a blank is a dash whose
  tooltip explains it (`figureCell()`, `assetSetTable.ts:25`).
- **Widths.** Each figure column opens at its title's measured width, which is also its minimum
  (`titleWidth()`, l.137; `headerWidth()`, `riskReturnLevel.ts:106`).
- **Mixed outcomes.** `asset_set_drawdown` needs 2 observations and the other four analytics 20, so a
  short window returns one `ok` beside four `unavailable` (`AssetSetComparisonLevels.svelte:39-47`;
  floors in [The Analytics](../../../backend/risk/architecture.md#analytics)).

---

## ⚖️ Risk and Return (L3°) {: #risk-return }

- **Shared level.** `RiskReturnLevel.svelte` also renders the portfolio's L3. The lab declares
  `capabilities={{ratios: true, benchmark: benchmarkApplies}}` and no weight
  (`AssetSetRiskReturnSection.svelte:198`), so Beta and Correlation exist only with a measured benchmark
  (`RiskReturnLevel.svelte:261`).
- **Benchmark row.** `withBenchmarkRow()` (`assetSetLevels.ts:296`) adds a `ref-<id>` row for a benchmark
  outside the selection; a selected benchmark keeps its own row. `referenceRowsFirst()` opens the table
  with it (`RiskReturnLevel.svelte:95`).
- **Chart and line.** The chart needs two placeable points (l.101). `capitalMarketLineAnchor()`
  (`frontend/src/lib/components/charts/scatterChartHelpers.ts:160`) anchors the line on a benchmark with positive
  volatility, else on the portfolio, which a selection never has: no benchmark, no line. The notes come
  from `riskReturnNotes()` (`riskReturnLevel.ts:174`): `above` and `line` only with a line, `return` and
  `priceOnly` always. The line starts at `LAB_RISK_FREE_RATE = 0` (`AssetSetRiskReturnSection.svelte:137`).
- **Period line.** `assetSetCalculationWindow()` (`assetSetLevels.ts:391`) reads the first result with
  metadata — from `end − calendar_days + 1` to `end` — and sets `narrowed` when that start is more than
  `NARROWED_AFTER_DAYS` (7, l.368) after the toolbar's start, or that end more than 7 days before the
  toolbar's end. The length is spelled in calendar units by `calendarLength()` (l.436).
- **Selection.** Rows and dots share the table's single selection; a selected asset's dot is drawn larger
  in the selection green, while the benchmark keeps its colour (the same `scatterChartHelpers.ts`, l.101).

---

## ⏮️ Replay (L4°) {: #replay }

- **One rung.** `AssetSetReplaySection.svelte` hands `L4WhatIf` the `replay` snippet only (l.135): no
  hypothetical shock and no simulation on an unweighted scope. The frame is `collapsible` and loads the
  scenario catalogue on first open (l.133); `showMoney={false}`.
- **Controls.** `L4Replay.svelte` puts *No preset* first (l.95). A preset sets the dates; a quick range or
  a typed date drops the preset; both reset the answer (l.151-170). The quick ranges exclude `MAX`
  (l.231). The composition total is withheld when `portfolio_return` is null, as it is on every unweighted
  scope (l.269), and `TornadoChart` drops the weight, contribution and amount columns when no row carries
  them (`levels/l4/TornadoChart.svelte:57-60`).
- **Lifetime.** A finished replay is discarded when the base signature moves, i.e. the selection or the
  dates ([The Panel Controller](../../../backend/risk/architecture.md#panel-controller)), and after an
  accepted sync (`AssetSetReplaySection.svelte:99`). Coverage, exclusion reasons and the suggested replay
  period are in [Replay Coverage](../../../backend/risk/architecture.md#replay-coverage).

---

## 🚩 Notices and Frames {: #notices }

- **One notice.** `partialNotice()` (`levels/partialNotice.ts:40`) runs over the results of the
  correlation section and the two levels, read through each section's `qualitySource()`
  (`AssetSetRiskPanel.svelte:625`). The replay hands it no results (`AssetSetReplaySection.svelte:127`)
  and keeps its own status. Only `partial` results become badges; the two VaR instances are labelled
  *Bad day* and *Bad month* (`VAR_LABELS`, `AssetSetComparisonLevels.svelte:158`). The notice is blue,
  titled *Holdings without prices…*, only when every reason is `no_price_source`, and titled *Worth
  knowing…* when nothing is partial (`levels/RiskPartialNotice.svelte:42`, l.54).
- **One banner.** The four controllers' `dataQualityIssues` are merged by `mergeQualityIssues()`
  (`AssetSetRiskPanel.svelte:633`) and rendered by [DataQualityBanner](../../data-quality-banner.md) in
  `grouped` mode. `labQualityAction()` (`syncTargets.ts:78-82`) maps any `sync_*` action to the lab's own
  sync, and `navigate_asset`, `navigate_fx` and `add_fx_pair` to navigation.
- **Frames.** `RiskLevelSection` keeps under each section only what did not come back
  (`levelErrorHealth()`, `levels/partialNotice.ts:49`), in an amber alert
  (`levels/RiskLevelSection.svelte:179`), plus `answer_discarded` (`ANSWER_DISCARDED_CODE`,
  `frontend/src/lib/stores/risk/riskPanelController.svelte.ts:57`) once the controller's re-asks are exhausted — the
  bound and the wording are in [The Panel Controller](../../../backend/risk/architecture.md#panel-controller).
  The section bodies offer **Retry** (`loadBase(true)`) when they have no figure to show, for example
  `AssetSetCorrelationSection.svelte:139`, l.153.
- **Calculation details.** The frame's `<details>` (`levels/RiskLevelSection.svelte:229`) lists the observations,
  coverage, annualization factor and return basis. `levelMetadata()` (`levels/levelMetadata.ts:54`)
  collapses analytics that agree into one row, and leaves out `method`.
- **Manual links.** Each frame's book icon (`docsPath`) opens the theory: the correlation page, the risk
  metrics index for L1° and L3°, the historical replay page for L4°.

---

## 🛡️ Dashboard Risk Tab {: #dashboard-risk-tab }

The **Risk** tab of the Dashboard and of Broker Detail mounts `levels/RiskLevelsPanel.svelte`: one
`createRiskPanelController`, a header (`levels/RiskPanelHeader.svelte`), the shared notice and four
levels, L1–L4. The two hosts pass the same props with a different scope. What users see is in the
[Risk Tab](../../../../user/dashboard/risk.md) user page; which analytics each level asks for is in
[By Level](../../../backend/risk/architecture.md#by-level).

| Host | Scope | What differs |
|---|---|---|
| `frontend/src/routes/(app)/dashboard/+page.svelte:1040-1054` | `broker_ids: ownedBrokerIds` (l.222): the brokers the user owns with a share above 0 (`getOwnedBrokers()`, `frontend/src/lib/stores/reference/brokerStore.ts:262`) | The broker filter is not applied: `subtitle` becomes `risk.dashboardFullPortfolio` while it is on (l.1048), and `scopeValue` is `null` then (l.1046), because the summary follows the filter. `assetIds` are the summary's holdings (l.1045). |
| `frontend/src/routes/(app)/brokers/[id]/+page.svelte:680-694` | `broker_ids: [broker.id]` | `scopeValue` is that broker's net worth (l.686); `internalSubset` prints `risk.internalSubset` (l.688). |

- **No owned broker, no request.** The Dashboard host mounts the panel only when `canAsk` (l.226);
  otherwise it shows `common.noData` (l.1056), or a spinner while the brokers load (l.1059).
- **Waves.** The controller opts into `includeDrawdownSummary`, `includeMonthlyVar` and
  `includeCurrentCompositionRiskReturn` (`levels/RiskLevelsPanel.svelte:85-103`; the options are in
  [The Panel Controller](../../../backend/risk/architecture.md#panel-controller)). The historical wave
  reads the portfolio's TWRR ([The Primary Series](../../../backend/risk/architecture.md#primary-series)),
  which is why deposits and withdrawals are neither gains nor losses here. Neither host sends a slice, so
  the backtest notice (`backtestDeclared()`, l.249, l.322) never shows on these pages.

### 📉 How Much Can It Hurt? {: #dashboard-hurt }

`levels/L1HowMuchItHurts.svelte`, over `historical_var` (two instances), `drawdown_summary` and
`historical_kpi` (`L1_CODES`, `levels/RiskLevelsPanel.svelte:125`).

- **Cards.** `buildHurtRows()` (`levels/levelHelpers.ts:374`) builds day → month → worst. The day and
  month cards lead with the CVaR at 95 % (l.384); the VaR is computed as `secondaryLoss` but never drawn,
  and appears only as the histogram's cut. The 30-day horizon is the lab's: see [Requests](#requests),
  *Bad month*. A rung whose analytic failed is omitted, never zero-filled (l.369).
- **Worst fall.** Depth and duration come from `drawdown_summary`, falling back to `historical_kpi`
  (`levelHelpers.ts:410`). The *recovery needed* line is `requiredRecovery()` (l.356: −50 % needs +100 %), drawn at
  `L1HowMuchItHurts.svelte:169` and l.197.
- **Current drawdown.** `buildCurrentDrawdown()` returns `null` at a peak (`levelHelpers.ts:437`), so the
  card exists only below one (`L1HowMuchItHurts.svelte:190`).
- **Tail measures as second rows.** The worst realization sits under the day card; drawdown at risk and
  conditional drawdown at risk under the worst fall (`L1HowMuchItHurts.svelte:174`, l.180; `buildTailMeasures()`,
  `levels/l1/l1Helpers.ts:227`). The ulcer index is the caption of the underwater chart
  (`levels/l1/UnderwaterChart.svelte:69`).
- **Histogram.** `buildReturnHistogram()` (`l1Helpers.ts:136`) flags the bin holding the VaR cut
  (`holdsCut`, l.92), drawn amber, and the bins wholly beyond it (`belowCut`, l.101), drawn red; the
  straddling bin is neither (`levels/l1/ReturnHistogram.svelte:51`). A bar's `title` gives its range
  (l.79).
- **Money.** `lossMoney()` is `scopeValue` × loss (`L1HowMuchItHurts.svelte:86`), shown only for a
  positive `scopeValue` (l.65): on the Dashboard, never while a broker filter is on.
- **Labels and links.** Each card prints a `technicalName` line
  (`frontend/src/lib/components/ui/display/RiskMetricCard.svelte:107`, keys `risk.levels.l1.technical.*`)
  and links its own metric page (`DOC_PATHS` and `TAIL_DOCS`, `L1HowMuchItHurts.svelte:117`, l.127).

### 🧩 Diversification {: #dashboard-diversification }

`levels/L2Diversification.svelte`, over `risk_contribution` (current composition, portfolio scope only:
[The Analytics](../../../backend/risk/architecture.md#analytics)) and `correlation` (historical wave).

- **Rows.** `buildDivergenceRows()` (`levels/levelHelpers.ts:476`) drops a row without weight or
  contribution (l.485) and sorts on the signed gap `contribution − weight` (l.496). Eight rows show
  before *Show all* (`visibleRows`, `L2Diversification.svelte:77`, l.338).
- **Lead.** `leadDivergence()` returns the top row only when its gap reaches 5 points (`minimumGap`,
  `levelHelpers.ts:507`); `levels/RiskLevelsPanel.svelte:307` words it.
- **Cards.** `buildConcentration()` (`levelHelpers.ts:556`) returns the effective number of assets and
  the diversification ratio together or not at all. The first card's caption compares the index with the
  measured rows — above, below or equal (`effectiveAssetsReading`, `L2Diversification.svelte:149`).
  `uncoveredWeight()` (`levelHelpers.ts:601`) splits `cash_weight` into cash and `excluded_weight`,
  worded by `uncoveredCaption` (`L2Diversification.svelte:172`). A card whose metric the scope lacks is
  not drawn (l.243).
- **Matrix.** The shared heatmap ([Correlation Section](#correlation-section)) receives only `output` and
  `assetLabels` (`L2Diversification.svelte:363`): no type, sector or region data, so only `similarity` and `name` are offered and
  no exposure badges show. When no pair reaches `NEAR_IDENTICAL`, a line says so (`hasRedundantPair`,
  l.114, l.359). On both surfaces, a click on a listed pair reveals, highlights and opens its cell, and a
  second click closes it (`selectPair()`, `CorrelationHeatmap.svelte:393`).

### ⚖️ Being Paid {: #dashboard-being-paid }

`levels/L3Benchmark.svelte` (the picker) and `levels/L3RiskAdjusted.svelte` (table and chart), over the
current-composition `historical_kpi` and `asset_risk_return` and the on-demand `comparison`.

- **Perimeter.** `selectKpiWave()` (`levels/l3Helpers.ts:64`) reads `historical_kpi` from the
  current-composition wave, falling back to the historical one; the title appends
  `risk.levels.l3.perimeter.*` from the answer's `metadata.mode` (`L3RiskAdjusted.svelte:59-61`).
- **Benchmark.** Picker and store are [Benchmark and Eligibility](../../../backend/risk/architecture.md#benchmark).
  Instead of the lab's `labL3Waits()` ([Requests](#requests)): `measuredAssetIds={[]}`, so a held asset
  may be the benchmark (`L3Benchmark.svelte:158`); an effect asks the comparison once per
  `baseEpoch|benchmark` when the picker reports `set` and the catalogue is `ready` (l.83-93); any other
  state bumps the generation and drops the answer (l.101-107).
- **Rates.** The comparison runs on `current_composition` with the page's risk-free rate and
  `target_annual_return: 0` (`L3Benchmark.svelte:133`). That rate is `appliedRiskFreePercent = 0`, with no control
  (`levels/RiskLevelsPanel.svelte:77`): the same zeros as the lab ([Requests](#requests), *Rates*).
- **Table and chart.** The shared `RiskReturnLevel` ([Risk and Return (L3°)](#risk-return)), with
  `capabilities={{weight: true, ratios: true, benchmark: benchmarkApplies}}` (`L3RiskAdjusted.svelte:113`).
  `benchmarkApplies` is a measured beta or a benchmark row (l.97), not the lab's `status === 'ok'`. The
  portfolio gets a reference row from the KPI (l.93) and a dot from `asset_risk_return`'s portfolio
  figures (`levels/l3Helpers.ts:142-151`), so with no measured benchmark the line runs through the
  portfolio instead of vanishing. `weight: true` adds the weight column and the dot-size note
  (`riskReturnLevel.ts:187`); widths and visible columns persist under
  `storageKey="risk-l3"` (`L3RiskAdjusted.svelte:117`), and the column menu sits in the level's header
  (`levels/RiskLevelsPanel.svelte:342-346`). Only a click on a column title sorts (`RiskReturnLevel.svelte:14`).
  Dashes: a blank figure has the `blankNote` tooltip (l.227), an uncalculated ratio a bare dash (l.224),
  the benchmark's own beta and correlation `referenceItself` (l.212), and a benchmark nobody holds
  `notHeld` under the weight (l.216).

### 🔮 What If…? {: #dashboard-what-if }

`levels/L4WhatIf.svelte` with three snippets — `L4Replay`, `L4Shock`, `L4Simulation`
(`levels/RiskLevelsPanel.svelte:366-376`) — in a collapsible frame that loads the
[scenario catalogue](../../../backend/risk/architecture.md#scenario-catalog) on first open (l.364).

- **Tool selector.** With more than one snippet the level is `selectable` (`L4WhatIf.svelte:88`): one
  *Add:* button per tool, always in `L4_TOOLS` order (l.7). The open set is read at mount from
  `risk.l4.openTools` in user storage (l.13, l.90, l.100), so the Dashboard and every broker page share
  it, and written by `add()` and `close()` (l.109, l.113); `close()` also resets that tool's analysis.
  Folding the frame unmounts the body (`levels/RiskLevelSection.svelte:170`) and keeps the controller's
  answers.
- **Replay.** Controls and lifetime are the lab's ([Replay (L4°)](#replay)); coverage, exclusions and the
  suggested period are in [Replay Coverage](../../../backend/risk/architecture.md#replay-coverage). On a
  weighted scope the excluded weight becomes a zero-return residual
  (`backend/app/services/risk_plugins/stress.py:562`), worded by `excludedHeader()`
  (`levels/l4/L4Replay.svelte:203`). `showMoney` follows `metadata.scope === 'portfolio'` (l.99), so the
  total sentence (l.269) and the amounts show here.
- **Shock.** A preset click adopts the scenario's dimension and bucket shocks and runs it
  (`levels/l4/L4Shock.svelte:82`); nothing runs without buckets (l.73); editing a bucket clears the
  preset and the answer (l.91); a note shows when `classification_coverage < 1` (l.170).
- **Simulation.** Defaults and the five modes are in
  [Simulation Parameters](../../../backend/risk/architecture.md#simulation-parameters). In the UI the
  sampling select exists for GBM only (`levels/l4/L4Simulation.svelte:62`), the seed input is hidden on
  QMC (l.64), and `SOBOL_START_INDEX` is fixed at 0 (l.45). The answer shows the terminal mean, the
  probability of loss and the P5–P95 band (l.216-222), the drift-uncertainty note (l.225) and
  `SimulationProvenance` (l.244). The beta banner and the model warning are drawn in the simulation box
  only (`L4WhatIf.svelte:156-160`).
- **Disclosure.** L4 keeps its own: every degraded status, named per step (`L4_STEP_LABELS`,
  `RiskLevelsPanel.svelte:229`), its reasons (l.239), its errors with discarded runs (l.240) and its
  metadata (l.241). The replay enters through `replaySectionView()` (l.214), so its warnings are read in
  the replay block alone.

### 🚩 Notices and Refresh {: #dashboard-notices }

- **Header.** `levels/RiskPanelHeader.svelte` draws the title and subtitle, **Sync** and **Refresh**
  (l.84-104), the load error (l.109-113) and the [DataQualityBanner](../../data-quality-banner.md) in
  `grouped` mode over the controller's merged issues (l.116). Instead of the lab's `labQualityAction()`,
  `handleQualityAction()` (l.66) opens the header's own `PageSyncModal` for any `sync` action and
  navigates for `navigate_asset`, `navigate_fx` and `add_fx_pair`.
- **Sync targets.** `syncAssets` are the host's `assetIds` — on the Dashboard the summary's holdings,
  which follow the broker filter — and `syncFxPairs` the configured pairs between their currencies and
  the target (`RiskPanelHeader.svelte:38-64`); the button is disabled when both are empty (l.89). After a sync, `handleSynced()`
  marks the answers stale and the host's `onsynced` reloads its own data (Dashboard host l.1050, Broker
  Detail host l.690).
- **Notice.** The shared notice is described in [Notices and Frames](#notices). Here it reads the L1
  results, `risk_contribution`, `correlation` and the L3 results (`levels/RiskLevelsPanel.svelte:154`), groups
  each partial badge under the first level that renders it (`levelOf`, l.162), and names the two VaR
  instances and L3's KPI as the levels show them (`L1_LABELS`, l.128; l.141). The L1–L3 frames keep only
  `unavailable` and `failed` (`levelErrorHealth`, l.334-346); L4 keeps its own (above). Calculation
  details are per level (l.191-193, l.241), as in [Notices and Frames](#notices).
- **Refresh and retry.** There is no **Retry** button. The header's **Refresh** is `loadBase(true)`
  (`levels/RiskPanelHeader.svelte:98`); the Dashboard's own Refresh bumps `refreshVersion` (Dashboard host,
  l.695-698), which the controller turns into `loadBase(true)`
  (`frontend/src/lib/stores/risk/riskPanelController.svelte.ts:647-656`). Re-asks, `answer_discarded`,
  the page cache and `loadError` are in [The Panel Controller](../../../backend/risk/architecture.md#panel-controller).
  Here `onrefreshfailed` toasts `risk.states.loadFailed` (`RiskLevelsPanel.svelte:82`),
  `setTweenHydration()` stops cached cards from counting up (l.106), and `loadError` replaces the notice
  and the levels (l.328).
- **Signature.** A new period, currency or scope discards the on-demand answers and relaunches only those
  in flight ([The Panel Controller](../../../backend/risk/architecture.md#panel-controller)); L3's
  comparison is asked again by its own effect (`levels/L3Benchmark.svelte:84-92`).
- **Manual links.** Every level's book icon opens the risk-metrics index without an anchor, which would
  break on the translated sites (`levels/RiskLevelsPanel.svelte:331-333`); cards and second rows link their own
  metric pages (`levels/L1HowMuchItHurts.svelte:117`, l.127; `levels/L2Diversification.svelte:258`, l.268, l.284).

---

## 🔗 Related {: #related }

- 📘 **[Correlation Tab](../../../../user/assets/correlation.md)** — the user page
- 📗 **[Risk Tab](../../../../user/dashboard/risk.md)** — the Dashboard's user page
- 📉 **[Risk Engine](../../../backend/risk/architecture.md)** — request flow, analytics, eligibility, controller and benchmark store
- 🧺 **[AssetPickerPanel](../core-ui/select.md#assetpickerpanel)** — the panel behind the lab's **+**
- 🛡️ **[DataQualityBanner](../../data-quality-banner.md)** — the banner above the sections
- 📊 **[Risk Metrics](../../../../financial-theory/technical-analysis/risk-metrics/index.md)** — the mathematics
