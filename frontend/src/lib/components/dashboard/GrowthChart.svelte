<!--
  GrowthChart — Multi-series portfolio growth chart for the Dashboard Home.

  Shows the portfolio's historical performance with a toggle between:
  - ABS mode: Stacked areas (Asset Cost + Returns + Capital) with NAV and
              Deposited Capital overlay lines. P&L = NAV − Deposited Capital.
  - % mode:   3 relative series (MWRR cumulative, TWRR, Simple ROI)

  Uses ECharts directly (LineChart wrapper is single-series only).

  Props:
  - history: PortfolioHistoryPoint[]
  - height: CSS height (default "360px")
  - loading: Show skeleton
  - baseCurrency: Label for Y-axis in ABS mode (default "EUR")

  Pattern: Svelte 5 Runes, ECharts, MutationObserver for dark mode,
           ResizeObserver for responsive sizing.
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {attachChartReady} from '$lib/utils/chartReady';
    import {createResizeWatcher} from '$lib/utils/core/resizeWatcher';
    import {CHART_ANIMATION_CONFIG, CHART_SET_OPTION_OPTS, namedPoint} from '$lib/components/charts/echartsAnimationConfig';
    import {_, locale} from '$lib/i18n';
    import {buildResponsiveXAxisPolicy} from '$lib/components/charts/responsiveXAxis';
    import {clampGrowthLogicalRange, type GrowthLogicalRange} from './growthChartRange';
    import ResolutionBadge from '$lib/components/charts/ResolutionBadge.svelte';
    import {aggregateLineSeries, mapDateToBucket, cascadeResolution, chooseInitialResolution} from '$lib/components/charts/timeSeriesAggregation';
    import type {ChartResolution} from '$lib/components/charts/timeSeriesAggregation';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import type {PortfolioHistoryPoint, PortfolioBrokerPnlHistory, PortfolioPnlCandleSeries, PortfolioIncomeHistorySeries, PortfolioCostHistorySeries, PortfolioDepositHistorySeries, PortfolioAcquisitionFundingSeries} from '$lib/stores/portfolio/portfolioStore.svelte';
    import {aggregateOHLCV, aggregateSumSeries} from '$lib/components/charts/timeSeriesAggregation';
    import {buildTooltipTheme, buildTooltipHeader, buildTooltipRow, buildTooltipDivider, tooltipPositionSide, setupTooltipAutoHide, scheduleFirstRenderStabilityFix} from '$lib/components/charts/echartsTooltipHelpers';
    import {INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG} from '$lib/components/charts/chartCoreHelpers';
    import {attachDataZoomTouchPan, type DataZoomTouchPanHandle} from '$lib/components/charts/echartsDataZoomTouchPan';
    import {buildOhlcQuad} from '$lib/components/charts/candlestickChartHelpers';
    import {ChartLine, ChartCandlestick, Coins} from 'lucide-svelte';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        history: PortfolioHistoryPoint[];
        /** G1a — per-broker additive P&L overlay. Empty/omitted: total-only P&L mode
         *  (single-broker scope or broker-detail mount, per plan §3.2). */
        brokerPnlHistory?: PortfolioBrokerPnlHistory[];
        /** G1b — synthetic total-P&L candle series. null/undefined while not yet
         *  fetched (candles are lazy per plan §4.1) or on the candles submode's first
         *  activation, in which case `onRequestPnlCandles` fires once. */
        pnlCandles?: PortfolioPnlCandleSeries | null;
        /** G1b — called at most once per activation when the user switches to the
         *  candles submode and `pnlCandles` is not yet loaded. The caller (Dashboard)
         *  owns the actual fetch/cache; GrowthChart only signals "now I need it". */
        onRequestPnlCandles?: () => void;
        /** G1c — signed DIVIDEND/INTEREST history. Eager (not lazy like pnlCandles):
         *  the caller fetches it on every ordinary load, per plan §4.1's sparse-payload
         *  policy — no onRequest callback needed here. */
        incomeHistory?: PortfolioIncomeHistorySeries;
        /** Batch 2 — signed FEE+TAX cost history. Same eager caller policy as incomeHistory. */
        costHistory?: PortfolioCostHistorySeries;
        /** Batch 2 — DEPOSIT history. Same eager caller policy as incomeHistory. */
        depositHistory?: PortfolioDepositHistorySeries;
        /** Batch 2 — new-vs-reinvested BUY funding split. Same eager caller policy as incomeHistory. */
        acquisitionFunding?: PortfolioAcquisitionFundingSeries;
        height?: string;
        loading?: boolean;
        baseCurrency?: string;
    }

    let {history = [], brokerPnlHistory = [], pnlCandles = null, onRequestPnlCandles, incomeHistory = undefined, costHistory = undefined, depositHistory = undefined, acquisitionFunding = undefined, height = '360px', loading = false, baseCurrency = 'EUR'}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    // coreMode = value|return|pnl (plan §5.1); kept as the existing 'eur'/'pct'/'pnl'
    // literal union for minimal churn on the 14 existing branches, not a rename.
    let viewMode: 'eur' | 'pct' | 'pnl' = $state('eur');
    // pnlSubmode = line|candles|income (plan §5.1); only 'line' has a real branch until
    // G1b/G1c land — no submode picker UI is shown while the other two are inert.
    let pnlSubmode: 'line' | 'candles' | 'income' = $state('line');
    // Zoom-window preset, shared by ALL THREE P&L submodes (see selectZoomWindow).
    // Named for the zoom it drives, NOT for a submode: it began life income-only, but
    // the mechanism was always the shared visible range. Deliberately "zoom" and not
    // "window" alone, to keep it distinct from the candle-WIDTH ladder (DBT-7), which
    // is a different control answering a different question.
    type ZoomWindowPreset = '1W' | '1M' | '1Y' | 'all';
    let zoomWindowPreset: ZoomWindowPreset = $state('1M');
    let currentResolution: ChartResolution = $state('daily');
    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | undefined = undefined;
    let dataZoomTouchPanHandle: {dispose: () => void} | null = null;
    /** Tracks last (viewMode, pnlSubmode) combination used for full init. A pnlSubmode
     *  change (line -> candles) needs a full rebuild too even though viewMode stays 'pnl':
     *  the series TYPE changes (line -> candlestick), which the partial-update path
     *  (`{name, data}` only, see CHART_SERIES_UPDATE_OPTS) cannot express. */
    let lastRenderedMode: string | null = null;
    let lastRenderedDark: boolean | null = null;
    let lastHistoryRef: PortfolioHistoryPoint[] | null = null;
    let responsiveXAxisCompact = false;
    const resizeWatcher = createResizeWatcher(() => {
        chartInstance?.resize();
        if (chartInstance && chartContainer && activeChartData) {
            const isCandlesSubmode = viewMode === 'pnl' && pnlSubmode === 'candles';
            const policy = buildResponsiveXAxisPolicy({
                width: chartContainer.clientWidth,
                values: activeChartData.dates,
                locale: $locale ?? undefined,
                axisType: isCandlesSubmode ? 'category' : 'time',
            });
            const wasCompact = responsiveXAxisCompact;
            responsiveXAxisCompact = policy.compact;
            if (policy.axisLabel) {
                // splitNumber is a time/value/log-axis concept — ECharts ignores it on a
                // category axis, so this stays unconditional (no need to fork on
                // isCandlesSubmode): policy.splitNumber is simply undefined there already
                // (see buildResponsiveXAxisPolicy).
                chartInstance.setOption({xAxis: {splitNumber: policy.splitNumber, axisLabel: policy.axisLabel}}, {lazyUpdate: true});
            } else if (wasCompact) {
                renderChart(true);
            }
        }
        scheduleResolutionSync();
    });
    let darkModeObserver: MutationObserver | null = null;
    let visibleStartDate: string | null = null;
    let visibleEndDate: string | null = null;
    let resolutionResetPending = true;
    let resolutionDebounceTimer: ReturnType<typeof setTimeout> | null = null;
    let dataZoomCleanup: (() => void) | null = null;
    /** True only for very first full render after `echarts.init()`. Later rebuilds
     *  must not force extra resizes because that can interrupt a visible mobile tooltip. */
    let needsInitialLayoutStabilityPass = false;

    // Color palettes
    const COLORS = {
        nav: {light: '#1a4031', dark: '#4ade80'}, // NAV — prominent line
        bookAssetLike: {light: '#3b82f6', dark: '#60a5fa'}, // Assets at cost — blue area
        cashContributed: {light: '#9caf9c', dark: '#6b8e6b'}, // Capital cash — subdued green area
        cashGenerated: {light: '#10b981', dark: '#34d399'}, // Returns cash — bright emerald area
        capitalBaseline: {light: '#6b7280', dark: '#9ca3af'}, // Capital baseline — grey dashed
        invested: {light: '#2563eb', dark: '#60a5fa'}, // TWRR (% mode)
        pctCash: {light: '#9caf9c', dark: '#94a3b8'}, // ROI (% mode)
        totalPnl: {light: '#1a4031', dark: '#4ade80'}, // P&L mode — Total line (same prominence as NAV)
        dividend: {light: '#0891b2', dark: '#22d3ee'}, // P&L income submode — Dividend stacked bar
        interest: {light: '#7c3aed', dark: '#a78bfa'}, // P&L income submode — Interest stacked bar
        costs: {light: '#ea580c', dark: '#fb923c'}, // P&L income submode — Costs (FEE+TAX) bar (batch 2)
        deposit: {light: '#0d9488', dark: '#2dd4bf'}, // P&L income submode — Deposit-size bar (batch 2)
    };

    // Rotating palette for the P&L broker overlay (G1a) — distinct hues, cycled by index
    // so any broker count renders with a stable, distinguishable color per line.
    const BROKER_PALETTE: Array<{light: string; dark: string}> = [
        {light: '#2563eb', dark: '#60a5fa'}, // blue
        {light: '#d97706', dark: '#fbbf24'}, // amber
        {light: '#7c3aed', dark: '#a78bfa'}, // violet
        {light: '#db2777', dark: '#f472b6'}, // pink
        {light: '#0891b2', dark: '#22d3ee'}, // cyan
        {light: '#65a30d', dark: '#a3e635'}, // lime
    ];

    function brokerColor(index: number, isDark: boolean): string {
        const entry = BROKER_PALETTE[index % BROKER_PALETTE.length];
        return isDark ? entry.dark : entry.light;
    }

    type SeriesPoint = ReturnType<typeof namedPoint> & {
        bucketStart: string;
        bucketEnd: string;
        resolution: ChartResolution;
    };

    type EurSeriesKey = 'bookAssetLike' | 'cashContributed' | 'cashGenerated' | 'nav' | 'capitalBaseline' | 'totalPnl';
    type PctSeriesKey = 'mwrrCum' | 'twrr' | 'roi';

    interface BucketInfo {
        date: string;
        bucketStart: string;
        bucketEnd: string;
        resolution: ChartResolution;
    }

    interface AggregatedMetric {
        values: Array<number | null>;
        points: SeriesPoint[];
    }

    interface AggregatedLookupEntry {
        value: number;
        bucketStart: string;
        bucketEnd: string;
    }

    /** One broker's P&L overlay line, aggregated at a given resolution (G1a). */
    interface AggregatedBrokerPnl {
        brokerId: number;
        brokerName: string;
        metric: AggregatedMetric;
    }

    /** One synthetic P&L candle point, aggregated at a given resolution (G1b). */
    type CandleSeriesPoint = SeriesPoint & {
        open: number | null;
        high: number | null;
        low: number | null;
        close: number | null;
    };

    interface AggregatedCandleMetric {
        points: CandleSeriesPoint[];
    }

    interface AggregatedResolutionData {
        resolution: ChartResolution;
        dates: string[];
        buckets: BucketInfo[];
        eur: Record<EurSeriesKey, AggregatedMetric>;
        pct: Record<PctSeriesKey, AggregatedMetric>;
        pnl: {
            total: AggregatedMetric;
            brokers: AggregatedBrokerPnl[];
            candle: AggregatedCandleMetric;
            income: {dividend: AggregatedMetric; interest: AggregatedMetric};
            costs: AggregatedMetric;
            deposits: AggregatedMetric;
            acquisition: {fromNewCapital: AggregatedMetric; fromReinvested: AggregatedMetric};
        };
    }

    const resolutionCache = new Map<ChartResolution, {inputs: AggregationInputs; data: AggregatedResolutionData}>();
    let activeChartData: AggregatedResolutionData | null = null;
    // IMPORTANT: 'series' must NOT be in replaceMerge here. updateChartData() below sends only
    // {name, data} per series (a deliberate partial update for smooth transitions, unchanged
    // since before this feature) — with replaceMerge, ECharts fully REPLACES matched series
    // instead of merging, discarding type/stack/lineStyle/areaStyle/itemStyle/label (which are
    // only ever set once, in applyFullOption()'s buildFullSeries()) and rendering nothing
    // (no error, just a blank chart). 'dataZoom' stays in replaceMerge defensively (this chart's
    // dataZoom is always percentage-based start/end, never startValue/endValue, so there is no
    // percentage/absolute-value merge conflict here — unlike AllocationHistoryChart — but
    // replacing it wholesale on a resolution switch is still the clearest way to reposition it).
    const CHART_SERIES_UPDATE_OPTS = {notMerge: false, replaceMerge: ['dataZoom']};
    /** ECharts' empty-value sentinel. MUST be used instead of `null` for a gap in a
     *  candlestick series on a category axis — a `null` item crashes
     *  `whiskerBoxCommon.getInitialData` during SeriesModel.init (see
     *  `toCandlestickPoint`). */
    const ECHARTS_EMPTY_VALUE = '-';
    /** Name of the non-data decoration series behind the P&L Line submode's dashed
     *  reference line. Declared once and referenced everywhere (series construction
     *  AND the legend exclusion in applyFullOption) so the sentinel never becomes a
     *  magic string that a second site has to remember independently. */
    const PNL_REFERENCE_SERIES_NAME = '__pnlReference__';
    /** Left inset of the plot area, in px. Used for BOTH `grid.left` and the floating
     *  overlay cluster's `left`, so the controls clear the y-axis label gutter by
     *  construction rather than by a coincidence that holds for today's tick labels.
     *  Deliberately a single shared constant: with `containLabel: true` the gutter
     *  width is computed by ECharts from the widest label, so any independently-chosen
     *  CSS offset would silently desynchronise the moment a label grew (a different
     *  base currency, a larger portfolio, a negative thousands value). */
    const CHART_PLOT_LEFT_PX = 52;
    const CHART_FULL_UPDATE_OPTS = {...CHART_SET_OPTION_OPTS, replaceMerge: [...CHART_SET_OPTION_OPTS.replaceMerge, 'xAxis']};

    // =========================================================================
    // Derived data for chart
    // =========================================================================

    const dates = $derived(history.map((pt) => pt.date));

    /** Helper to safely extract amount from an optional Currency field (handles union types). */
    function amt(field: any): number | null {
        if (field != null && !Array.isArray(field) && typeof field === 'object' && 'amount' in field) return Number(field.amount);
        return null;
    }

    // EUR mode: Capital Baseline narrative
    // Stacked areas: book_asset_like + cash_from_contributed + cash_from_generated = book_value
    // Overlay: NAV line (solid) + Capital Baseline line (dashed)
    // P&L = NAV - Capital Baseline (visible as gap between NAV line and baseline line)
    //
    // Convention "returns consumed first":
    //   - Cash from contributed capital = undeployed external capital sitting in cash
    //   - Cash from generated returns = income/gains not yet reinvested
    //   - When buying, returns are consumed first → deposit residuals stay as capital cash
    const eurStackedData = $derived({
        bookAssetLike: history.map((pt) => amt(pt.book_asset_like)),
        cashContributed: history.map((pt) => amt(pt.cash_from_contributed_capital)),
        cashGenerated: history.map((pt) => amt(pt.cash_from_generated_returns)),
        nav: history.map((pt) => (pt.nav_value != null ? Number(pt.nav_value.amount) : null)),
        capitalBaseline: history.map((pt) => amt(pt.capital_baseline)),
        totalPnl: history.map((pt) => amt(pt.total_pnl)),
    });

    /**
     * Period-relative P&L baseline: Total P&L already accumulated at the start of the shown period.
     * Subtracting this gives "how much was gained IN this period", starting at 0.
     */
    const periodBasePnl = $derived(
        (() => {
            const idx = eurStackedData.totalPnl.findIndex((v) => v != null);
            if (idx < 0) return 0;
            return eurStackedData.totalPnl[idx] ?? 0;
        })(),
    );

    // Translated labels for EUR mode (tracked for reactivity on locale change)
    const eurLabels = $derived({
        bookAssetLike: $_('dashboard.assetsAtCost'),
        bookAssetLikeTooltip: $_('dashboard.assetsAtCostTooltip'),
        cashContributed: $_('dashboard.cashFromContributedCapital'),
        cashGenerated: $_('dashboard.cashFromGeneratedReturns'),
        nav: $_('dashboard.navValue'),
        capitalBaseline: $_('dashboard.capitalBaseline'),
        capitalBaselineTooltip: $_('dashboard.capitalBaselineTooltip'),
    });

    // Translated labels for P&L mode (G1a)
    const pnlLabels = $derived({
        total: $_('dashboard.totalPnl'),
        // G1c: reuse the existing transaction-type labels (dynamic-prefix protected,
        // but a plain static reference to an existing key is safe) — no new i18n key.
        dividend: $_('transactions.types.DIVIDEND'),
        interest: $_('transactions.types.INTEREST'),
        // Batch 2: reuse existing keys — the dashboard KPI's own "Fees & taxes" grouping
        // and the DEPOSIT transaction-type label — no new i18n key for either.
        costs: $_('dashboard.feesAndTaxes'),
        deposit: $_('transactions.types.DEPOSIT'),
        acqNewCapital: $_('dashboard.pnlAcqNewCapital'),
        acqReinvested: $_('dashboard.pnlAcqReinvested'),
    });

    /**
     * P&L mode broker overlay (G1a): one aligned-to-`dates` values array per broker in
     * `brokerPnlHistory`, built via a date lookup (a broker's points may not cover every
     * date 1:1 with `history` — e.g. it joined the scope later). `total_pnl` here is the
     * SAME already-computed `eurStackedData.totalPnl` used by EUR mode — canonical,
     * inception-based, never rebased (plan §3.2). Only rendered when ≥2 brokers are
     * present, matching "one selected broker: total line only".
     */
    const pnlBrokerSeriesRaw = $derived(
        brokerPnlHistory.length >= 2
            ? brokerPnlHistory.map((broker) => {
                  const byDate = new Map(broker.points.map((p) => [p.date, amt(p.total_pnl)]));
                  return {
                      brokerId: broker.broker_id,
                      brokerName: broker.broker_name,
                      values: dates.map((d) => byDate.get(d) ?? null),
                  };
              })
            : [],
    );

    /** P&L candles submode (G1b): per-date OHLC lookup from the fetched series. A date
     *  absent from the map means that day's candle was unavailable (a resolved held-asset
     *  valuation was MISSING) — a genuine gap, never guessed. */
    const pnlCandleByDate = $derived(new Map((pnlCandles?.points ?? []).map((p) => [p.date, {open: Number(p.open.amount), high: Number(p.high.amount), low: Number(p.low.amount), close: Number(p.close.amount)}])));

    /** P&L income submode (G1c): signed dividend/interest values aligned to `dates`.
     *  A date absent from incomeHistory.points means no DIVIDEND/INTEREST that day —
     *  rendered as 0 (a sparse-flow series, distinct from candle "gap" semantics). */
    const dividendValues = $derived.by(() => {
        const byDate = new Map((incomeHistory?.points ?? []).map((p) => [p.date, Number(p.dividend.amount)]));
        return dates.map((d) => byDate.get(d) ?? 0);
    });
    const interestValues = $derived.by(() => {
        const byDate = new Map((incomeHistory?.points ?? []).map((p) => [p.date, Number(p.interest.amount)]));
        return dates.map((d) => byDate.get(d) ?? 0);
    });

    /** Batch 2 income-submode dimensions: costs (FEE+TAX, signed/negative), deposits
     *  (fresh external cash), and the new-vs-reinvested BUY funding split. Same sparse
     *  "absent date -> 0" semantics as dividend/interest above. */
    const costValues = $derived.by(() => {
        const byDate = new Map((costHistory?.points ?? []).map((p) => [p.date, Number(p.cost.amount)]));
        return dates.map((d) => byDate.get(d) ?? 0);
    });
    const depositValues = $derived.by(() => {
        const byDate = new Map((depositHistory?.points ?? []).map((p) => [p.date, Number(p.deposit.amount)]));
        return dates.map((d) => byDate.get(d) ?? 0);
    });
    const acqFromNewCapitalValues = $derived.by(() => {
        const byDate = new Map((acquisitionFunding?.points ?? []).map((p) => [p.date, Number(p.from_new_capital.amount)]));
        return dates.map((d) => byDate.get(d) ?? 0);
    });
    const acqFromReinvestedValues = $derived.by(() => {
        const byDate = new Map((acquisitionFunding?.points ?? []).map((p) => [p.date, Number(p.from_reinvested.amount)]));
        return dates.map((d) => byDate.get(d) ?? 0);
    });

    // Values are split from labels deliberately: the aggregation memo reads ONLY these,
    // so a language switch rebuilds `pctSeriesRaw` (names) without invalidating the cache.
    const pctValuesRaw = $derived({
        mwrrCum: history.map((pt) => (pt.mwrr_cumulative != null ? Number(pt.mwrr_cumulative) * 100 : null)),
        twrr: history.map((pt) => (pt.twrr != null ? Number(pt.twrr) * 100 : null)),
        roi: history.map((pt) => (pt.roi != null ? Number(pt.roi) * 100 : null)),
    });

    const pctSeriesRaw = $derived([
        {
            key: 'mwrrCum' as const,
            name: $_('dashboard.mwrrCum'),
            values: pctValuesRaw.mwrrCum,
            lineStyle: 'solid' as const,
            colorKey: 'nav' as const,
        },
        {
            key: 'twrr' as const,
            name: $_('dashboard.twrr'),
            values: pctValuesRaw.twrr,
            lineStyle: 'dashed' as const,
            colorKey: 'invested' as const,
        },
        {
            key: 'roi' as const,
            name: $_('dashboard.roi'),
            values: pctValuesRaw.roi,
            lineStyle: 'dotted' as const,
            colorKey: 'pctCash' as const,
        },
    ]);
    // Filter out series with all-null data (e.g. MWRR when marked unreliable)
    const pctSeries = $derived(pctSeriesRaw.filter((s) => s.values.some((v) => v != null)));

    /**
     * The COMPLETE set of reactive values `getResolutionData()` is allowed to read.
     *
     * This exists to make cache invalidation correct *by construction* rather than by a
     * hand-maintained list somebody must remember to join. Because it is `$derived`, Svelte
     * rebuilds this object — giving it a fresh identity — whenever any member changes; and
     * because `getResolutionData()` reads its inputs ONLY from here, a new input physically
     * cannot be consumed without first becoming a member, which automatically enrols it in
     * invalidation. Adding a field is the whole ceremony.
     *
     * The bug this replaces (G1b): seven inputs woke the render effect while exactly ONE
     * (`history`) cleared `resolutionCache`, whose key spanned only `resolution`. A lazily
     * arriving prop (`pnlCandles`) therefore re-rendered against an entry computed before
     * its data existed — every candle a `'-'` gap, forever, surviving re-entry.
     *
     * Deliberately EXCLUDED, and the exclusion matters: `eurLabels`, `pnlLabels`, `$locale`
     * and `baseCurrency`. They are in the render effect's dependency list (labels must
     * re-render on a language switch) but the aggregation never reads them — only
     * `pctValuesRaw`, which is split from the labels for exactly this reason. Invalidating on them would trade a
     * silent-wrong bug for a silent-slow one, discarding a memo that exists for a reason.
     */
    type AggregationInputs = {
        dates: string[];
        eurStackedData: typeof eurStackedData;
        pctValuesRaw: typeof pctValuesRaw;
        pnlBrokerSeriesRaw: typeof pnlBrokerSeriesRaw;
        pnlCandleByDate: typeof pnlCandleByDate;
        dividendValues: number[];
        interestValues: number[];
        costValues: number[];
        depositValues: number[];
        acqFromNewCapitalValues: number[];
        acqFromReinvestedValues: number[];
    };

    const aggregationInputs: AggregationInputs = $derived({
        dates,
        eurStackedData,
        pctValuesRaw,
        pnlBrokerSeriesRaw,
        pnlCandleByDate,
        dividendValues,
        interestValues,
        costValues,
        depositValues,
        acqFromNewCapitalValues,
        acqFromReinvestedValues,
    });

    const hasPctData = $derived(history.some((pt) => pt.mwrr_cumulative != null || pt.twrr != null || pt.roi != null));
    const hasNonZeroPctData = $derived(history.some((pt) => Number(pt.mwrr_cumulative ?? 0) !== 0 || Number(pt.twrr ?? 0) !== 0 || Number(pt.roi ?? 0) !== 0));

    function resetResolutionState(preservedRange: GrowthLogicalRange | null = null) {
        resolutionCache.clear();
        activeChartData = null;
        currentResolution = 'daily';
        resolutionResetPending = true;
        const nextRange = clampGrowthLogicalRange(preservedRange, dates);
        visibleStartDate = nextRange?.startDate ?? null;
        visibleEndDate = nextRange?.endDate ?? null;
    }

    function ensureLogicalRange(): {startDate: string; endDate: string} | null {
        if (dates.length === 0) return null;
        visibleStartDate ??= dates[0];
        visibleEndDate ??= dates[dates.length - 1];
        return {startDate: visibleStartDate, endDate: visibleEndDate};
    }

    function buildBucketInfos(resolution: ChartResolution, dates: string[]): BucketInfo[] {
        if (resolution === 'daily') {
            return dates.map((date) => ({
                date,
                bucketStart: date,
                bucketEnd: date,
                resolution,
            }));
        }

        const buckets: BucketInfo[] = [];
        let lastBucketEnd: string | null = null;

        for (const date of dates) {
            const {bucketStart, bucketEnd} = mapDateToBucket(date, resolution);
            if (bucketEnd === lastBucketEnd) continue;

            buckets.push({
                date: bucketEnd,
                bucketStart,
                bucketEnd,
                resolution,
            });
            lastBucketEnd = bucketEnd;
        }

        return buckets;
    }

    function toSeriesPoint(bucket: BucketInfo, value: number | null): SeriesPoint {
        return {
            ...namedPoint(bucket.date, value),
            bucketStart: bucket.bucketStart,
            bucketEnd: bucket.bucketEnd,
            resolution: bucket.resolution,
        };
    }

    function aggregateMetric(values: Array<number | null>, resolution: ChartResolution, buckets: BucketInfo[]): AggregatedMetric {
        if (resolution === 'daily') {
            return {
                values: [...values],
                points: buckets.map((bucket, index) => toSeriesPoint(bucket, values[index] ?? null)),
            };
        }

        const sourcePoints: LineDataPoint[] = dates.flatMap((date, index) => {
            const value = values[index];
            return value == null ? [] : [{date, value}];
        });
        const aggregated = aggregateLineSeries(sourcePoints, resolution);
        const lookup = new Map<string, AggregatedLookupEntry>(
            aggregated.map((point) => [
                point.date,
                {
                    value: point.value,
                    bucketStart: 'bucketStart' in point && typeof point.bucketStart === 'string' ? point.bucketStart : point.date,
                    bucketEnd: 'bucketEnd' in point && typeof point.bucketEnd === 'string' ? point.bucketEnd : point.date,
                },
            ]),
        );

        const aggregatedValues = buckets.map((bucket) => lookup.get(bucket.date)?.value ?? null);
        const points = buckets.map((bucket, index) => {
            const meta = lookup.get(bucket.date);
            return toSeriesPoint(
                {
                    ...bucket,
                    bucketStart: meta?.bucketStart ?? bucket.bucketStart,
                    bucketEnd: meta?.bucketEnd ?? bucket.bucketEnd,
                },
                aggregatedValues[index],
            );
        });

        return {values: aggregatedValues, points};
    }

    /** Aggregate a sparse economic-flow metric (signed DIVIDEND/INTEREST, G1c) using
     *  aggregateSumSeries — mirrors aggregateMetric()'s structure exactly but sums
     *  every day in a bucket instead of taking the last value (plan §3.4/§5.2: "Weekly/
     *  monthly buckets sum them; they never use end-of-period/last-value semantics"). */
    function aggregateFlowMetric(values: number[], resolution: ChartResolution, buckets: BucketInfo[]): AggregatedMetric {
        if (resolution === 'daily') {
            return {
                values: [...values],
                points: buckets.map((bucket, index) => toSeriesPoint(bucket, values[index] ?? 0)),
            };
        }

        const sourcePoints: LineDataPoint[] = dates.map((date, index) => ({date, value: values[index] ?? 0}));
        const aggregated = aggregateSumSeries(sourcePoints, resolution);
        const lookup = new Map<string, AggregatedLookupEntry>(
            aggregated.map((point) => [
                point.date,
                {
                    value: point.value,
                    bucketStart: 'bucketStart' in point && typeof point.bucketStart === 'string' ? point.bucketStart : point.date,
                    bucketEnd: 'bucketEnd' in point && typeof point.bucketEnd === 'string' ? point.bucketEnd : point.date,
                },
            ]),
        );

        const aggregatedValues = buckets.map((bucket) => lookup.get(bucket.date)?.value ?? 0);
        const points = buckets.map((bucket, index) => {
            const meta = lookup.get(bucket.date);
            return toSeriesPoint(
                {
                    ...bucket,
                    bucketStart: meta?.bucketStart ?? bucket.bucketStart,
                    bucketEnd: meta?.bucketEnd ?? bucket.bucketEnd,
                },
                aggregatedValues[index],
            );
        });

        return {values: aggregatedValues, points};
    }

    /** Aggregate the daily synthetic P&L candle series to a coarser resolution, reusing
     *  the shared aggregateOHLCV reducer (first open / max high / min low / last close) —
     *  the exact "compose daily first, then roll up" contract (plan §4.3), never re-derived
     *  here. Days with no candle (map miss) are excluded before aggregating, matching
     *  aggregateMetric()'s null-filtering convention for the same reason: a bucket with no
     *  contributing day must not synthesize a false zero-range candle. */
    function aggregateCandleMetric(byDate: Map<string, {open: number; high: number; low: number; close: number}>, resolution: ChartResolution, buckets: BucketInfo[]): AggregatedCandleMetric {
        if (resolution === 'daily') {
            return {
                points: buckets.map((bucket) => {
                    const c = byDate.get(bucket.date);
                    return {...toSeriesPoint(bucket, c?.close ?? null), open: c?.open ?? null, high: c?.high ?? null, low: c?.low ?? null, close: c?.close ?? null};
                }),
            };
        }

        const sourcePoints: LineDataPoint[] = dates.flatMap((date) => {
            const c = byDate.get(date);
            return c ? [{date, value: c.close, open: c.open, high: c.high, low: c.low, close: c.close}] : [];
        });
        const aggregated = aggregateOHLCV(sourcePoints, resolution);
        const lookup = new Map(
            aggregated.map((point) => [
                point.date,
                {
                    open: point.open ?? null,
                    high: point.high ?? null,
                    low: point.low ?? null,
                    close: point.close ?? null,
                    bucketStart: 'bucketStart' in point && typeof point.bucketStart === 'string' ? point.bucketStart : point.date,
                    bucketEnd: 'bucketEnd' in point && typeof point.bucketEnd === 'string' ? point.bucketEnd : point.date,
                },
            ]),
        );

        const points = buckets.map((bucket) => {
            const meta = lookup.get(bucket.date);
            return {
                ...toSeriesPoint({...bucket, bucketStart: meta?.bucketStart ?? bucket.bucketStart, bucketEnd: meta?.bucketEnd ?? bucket.bucketEnd}, meta?.close ?? null),
                open: meta?.open ?? null,
                high: meta?.high ?? null,
                low: meta?.low ?? null,
                close: meta?.close ?? null,
            };
        });

        return {points};
    }

    function getResolutionData(resolution: ChartResolution): AggregatedResolutionData {
        // Identity check, not an equality list: `aggregationInputs` is rebuilt by Svelte
        // whenever any input changes, so a stale entry cannot be returned by construction.
        const inputs = aggregationInputs;
        const cached = resolutionCache.get(resolution);
        if (cached && cached.inputs === inputs) return cached.data;

        const buckets = buildBucketInfos(resolution, inputs.dates);
        const entry: AggregatedResolutionData = {
            resolution,
            dates: buckets.map((bucket) => bucket.date),
            buckets,
            eur: {
                bookAssetLike: aggregateMetric(inputs.eurStackedData.bookAssetLike, resolution, buckets),
                cashContributed: aggregateMetric(inputs.eurStackedData.cashContributed, resolution, buckets),
                cashGenerated: aggregateMetric(inputs.eurStackedData.cashGenerated, resolution, buckets),
                nav: aggregateMetric(inputs.eurStackedData.nav, resolution, buckets),
                capitalBaseline: aggregateMetric(inputs.eurStackedData.capitalBaseline, resolution, buckets),
                totalPnl: aggregateMetric(inputs.eurStackedData.totalPnl, resolution, buckets),
            },
            pct: {
                mwrrCum: aggregateMetric(inputs.pctValuesRaw.mwrrCum, resolution, buckets),
                twrr: aggregateMetric(inputs.pctValuesRaw.twrr, resolution, buckets),
                roi: aggregateMetric(inputs.pctValuesRaw.roi, resolution, buckets),
            },
            pnl: {
                // Reuses the exact same Decimal-sourced totalPnl values as EUR mode's
                // tooltip line — one canonical, non-rebased total_pnl series (plan §3.2).
                total: aggregateMetric(inputs.eurStackedData.totalPnl, resolution, buckets),
                brokers: inputs.pnlBrokerSeriesRaw.map((broker) => ({
                    brokerId: broker.brokerId,
                    brokerName: broker.brokerName,
                    metric: aggregateMetric(broker.values, resolution, buckets),
                })),
                candle: aggregateCandleMetric(inputs.pnlCandleByDate, resolution, buckets),
                income: {
                    dividend: aggregateFlowMetric(inputs.dividendValues, resolution, buckets),
                    interest: aggregateFlowMetric(inputs.interestValues, resolution, buckets),
                },
                costs: aggregateFlowMetric(inputs.costValues, resolution, buckets),
                deposits: aggregateFlowMetric(inputs.depositValues, resolution, buckets),
                acquisition: {
                    fromNewCapital: aggregateFlowMetric(inputs.acqFromNewCapitalValues, resolution, buckets),
                    fromReinvested: aggregateFlowMetric(inputs.acqFromReinvestedValues, resolution, buckets),
                },
            },
        };

        resolutionCache.set(resolution, {inputs, data: entry});
        return entry;
    }

    function computeBucketCounts(startDate: string, endDate: string): {dailyCount: number; weeklyCount: number; monthlyCount: number} {
        let dailyCount = 0;
        const weekly = new Set<string>();
        const monthly = new Set<string>();

        for (const date of dates) {
            if (date < startDate || date > endDate) continue;
            dailyCount += 1;
            weekly.add(mapDateToBucket(date, 'weekly').bucketEnd);
            monthly.add(mapDateToBucket(date, 'monthly').bucketEnd);
        }

        return {
            dailyCount,
            weeklyCount: weekly.size,
            monthlyCount: monthly.size,
        };
    }

    function getZoomPercent(): {start: number; end: number} {
        if (!chartInstance) return {start: 0, end: 100};

        try {
            const option = chartInstance.getOption() as {dataZoom?: Array<{start?: number; end?: number}>};
            const zoom = option.dataZoom?.[0];
            if (typeof zoom?.start === 'number' && typeof zoom?.end === 'number') {
                return {start: zoom.start, end: zoom.end};
            }
        } catch (_) {}

        return {start: 0, end: 100};
    }

    function getLogicalRangeFromChart(): {startDate: string; endDate: string} | null {
        if (!activeChartData || activeChartData.resolution !== currentResolution) return null;
        const entry = activeChartData;
        if (entry.buckets.length === 0) return null;

        const {start, end} = getZoomPercent();
        const maxIndex = Math.max(entry.buckets.length - 1, 0);
        const startIndex = Math.max(0, Math.min(maxIndex, Math.floor((start / 100) * maxIndex)));
        const endIndex = Math.max(startIndex, Math.min(maxIndex, Math.ceil((end / 100) * maxIndex)));
        const startBucket = entry.buckets[startIndex];
        const endBucket = entry.buckets[endIndex];

        return {
            startDate: startBucket.bucketStart,
            endDate: endBucket.bucketEnd,
        };
    }

    function buildZoomWindow(resolution: ChartResolution, startDate: string, endDate: string): {start: number; end: number} {
        const entry = getResolutionData(resolution);
        if (entry.buckets.length <= 1) return {start: 0, end: 100};

        const startIndex = Math.max(
            0,
            entry.buckets.findIndex((bucket) => bucket.bucketEnd >= startDate),
        );
        const endIndex = Math.max(
            startIndex,
            entry.buckets.findLastIndex((bucket) => bucket.bucketStart <= endDate),
        );
        const denominator = entry.buckets.length - 1;

        return {
            start: (startIndex / denominator) * 100,
            end: (endIndex / denominator) * 100,
        };
    }

    /** Batch 2 — Income submode window selector (1W/1M/1Y/All), independent UI on top
     *  of the SAME shared zoom/dataZoom mechanism the chart already uses for drag/scroll
     *  zoom (not a parallel windowing system) — a preset button is just a convenient way
     *  to set visibleStartDate/visibleEndDate + the resulting dataZoom percentages,
     *  exactly as a manual zoom gesture would. Shared with Line/Candles since they use
     *  the same underlying state: switching submodes after picking a window keeps it. */
    function computeZoomWindowRange(preset: ZoomWindowPreset): {startDate: string; endDate: string} | null {
        if (dates.length === 0) return null;
        const endDate = dates[dates.length - 1];
        if (preset === 'all') return {startDate: dates[0], endDate};
        const daysBack = preset === '1W' ? 7 : preset === '1M' ? 30 : 365;
        const startMs = new Date(endDate).getTime() - daysBack * 24 * 60 * 60 * 1000;
        const computedStart = new Date(startMs).toISOString().slice(0, 10);
        return {startDate: computedStart < dates[0] ? dates[0] : computedStart, endDate};
    }

    function selectZoomWindow(preset: ZoomWindowPreset) {
        zoomWindowPreset = preset;
        const range = computeZoomWindowRange(preset);
        if (!range || !chartInstance) return;
        visibleStartDate = range.startDate;
        visibleEndDate = range.endDate;
        const zoomWindow = buildZoomWindow(currentResolution, range.startDate, range.endDate);
        chartInstance.setOption({dataZoom: [{type: 'inside', ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG, start: zoomWindow.start, end: zoomWindow.end}]}, {replaceMerge: ['dataZoom']});
    }

    function formatTooltipMonth(date: string): string {
        const activeLocale = $locale ?? 'en';
        const [year, month, day] = date.split('-').map(Number);
        return new Intl.DateTimeFormat(activeLocale, {
            month: 'long',
            year: 'numeric',
            timeZone: 'UTC',
        }).format(new Date(Date.UTC(year, month - 1, day)));
    }

    function buildTooltipBucketHeader(bucket: BucketInfo, theme: ReturnType<typeof buildTooltipTheme>): string {
        if (bucket.resolution === 'daily') {
            return buildTooltipHeader(bucket.bucketEnd, theme.textColor);
        }

        const contextLine = `<div style="font-size:10px;color:${theme.mutedColor};margin-bottom:4px">${$_('chart.tooltip.valueAt', {values: {date: bucket.bucketEnd}})}</div>`;

        if (bucket.resolution === 'weekly') {
            return `${buildTooltipHeader($_('chart.tooltip.weekRange', {values: {start: bucket.bucketStart, end: bucket.bucketEnd}}), theme.textColor)}${contextLine}`;
        }

        return `${buildTooltipHeader($_('chart.tooltip.monthLabel', {values: {month: formatTooltipMonth(bucket.bucketEnd)}}), theme.textColor)}${contextLine}`;
    }

    /** ECharts candlestick data point for a `category` xAxis: a flat `[open, close,
     *  low, high]` quad (note the element order — NOT open/high/low/close),
     *  reusing the exact same shared convention as CandlestickChart.svelte via
     *  `buildOhlcQuad` (see PR discussion: candlestick series silently fails to
     *  paint any body/wick on a `time` xAxis — a known upstream ECharts limitation
     *  — so this submode uses a `category` axis instead, matching the codebase's
     *  own already-proven Asset Detail price-chart pattern).
     *
     *  A gap day/bucket (no candle) MUST be ECharts' empty-value sentinel `'-'`,
     *  never `null`. On a category base axis the candlestick series clones its data
     *  through `whiskerBoxCommon.getInitialData`, which branches
     *  `isArray(item) -> … else if (isArray(item.value))` — so a `null` item
     *  dereferences `null.value` and throws *inside SeriesModel.init*, before the
     *  GlobalModel finishes building. The chart then has no `_seriesIndices`, so
     *  every later `setOption` silently no-ops and the canvas freezes on the
     *  previous submode's paint. `'-'` falls through that same branch chain
     *  harmlessly (verified empirically against this exact echarts build, not
     *  inferred: `null` throws "Cannot read properties of null (reading 'value')",
     *  `'-'` renders). Position in the array (not the date itself) is what aligns
     *  a point to the shared `xAxis.data` category list, so the gap must still
     *  occupy its slot — which is exactly why it can't just be omitted. */
    function toCandlestickPoint(point: CandleSeriesPoint): number[] | string {
        if (point.open == null || point.close == null || point.low == null || point.high == null) return ECHARTS_EMPTY_VALUE;
        return buildOhlcQuad(point.open, point.close, point.low, point.high, false, 1);
    }

    /** A category xAxis aligns series data by position, not by `[date, value]`
     *  pairs — extract the plain value so the broker-line overlay lines up with
     *  the candlestick's category positions in `pnlSubmode==='candles'`. */
    function toPositionalValue(point: SeriesPoint): number | null {
        return point.value[1];
    }

    /** Clip a point's value to null when it doesn't match `keepPositive` — used to
     *  split the Total P&L line into two fixed, same-length series (positive-part /
     *  negative-part), each with its own solid green/red color. A FIXED two-series
     *  split (rather than a variable number of contiguous same-sign segments) keeps
     *  `updateChartData`'s partial by-index series merge valid across zoom/pan,
     *  where the count of sign-crossings in the visible window can change on every
     *  frame. ECharts' visualMap does not reliably recolor a line series'
     *  lineStyle/areaStyle per value — a documented upstream limitation (see
     *  apache/echarts#8034) — so per-point coloring needs this series-split
     *  approach instead, same spirit as LineChart.svelte's segment-based coloring. */
    function clipToSign(point: SeriesPoint, keepPositive: boolean): SeriesPoint {
        const v = point.value[1];
        if (v == null || v >= 0 === keepPositive) return point;
        return {...point, value: [point.value[0], null]};
    }

    /** The Total P&L value at (or just after) `referenceDate` — the reference for
     *  the #3 dashed baseline (plan follow-up: "was P&L up or down over the
     *  examined period"). Mirrors buildZoomWindow's own bucket-lookup convention
     *  (first bucket whose end reaches the date). Falls back to the first point
     *  when nothing qualifies (empty range or a reference before all data). */
    function findReferenceTotalPnl(entry: AggregatedResolutionData, referenceDate: string | null): number | null {
        const points = entry.pnl.total.points;
        if (points.length === 0) return null;
        const point = (referenceDate != null && points.find((p) => p.bucketEnd >= referenceDate)) || points[0];
        return point.value[1];
    }

    function buildChartUpdateSeries(_isDark: boolean, entry: AggregatedResolutionData, referenceDate: string | null = null): {name: string; data: SeriesPoint[]}[] {
        if (viewMode === 'eur') {
            return [
                {name: eurLabels.bookAssetLike, data: entry.eur.bookAssetLike.points},
                {name: eurLabels.cashContributed, data: entry.eur.cashContributed.points},
                {name: eurLabels.cashGenerated, data: entry.eur.cashGenerated.points},
                {name: eurLabels.nav, data: entry.eur.nav.points},
                {name: eurLabels.capitalBaseline, data: entry.eur.capitalBaseline.points},
            ];
        }

        if (viewMode === 'pnl' && pnlSubmode === 'line') {
            // Split into a fixed positive/negative pair (clip-to-null, see clipToSign)
            // instead of a variable number of sign-crossing segments, plus a third
            // fixed slot for the #3 dashed reference line (flat at the first-visible-
            // day P&L) — all three keep updateChartData's partial by-index series
            // merge valid across zoom/pan.
            const referenceValue = findReferenceTotalPnl(entry, referenceDate);
            const referencePoints: SeriesPoint[] = entry.pnl.total.points.map((p) => ({...p, value: [p.value[0], referenceValue]}));
            return [
                {name: pnlLabels.total, data: entry.pnl.total.points.map((p) => clipToSign(p, true))},
                {name: pnlLabels.total, data: entry.pnl.total.points.map((p) => clipToSign(p, false))},
                {name: PNL_REFERENCE_SERIES_NAME, data: referencePoints},
                ...entry.pnl.brokers.map((broker) => ({name: broker.brokerName, data: broker.metric.points})),
            ];
        }

        if (viewMode === 'pnl' && pnlSubmode === 'candles') {
            // Hybrid rendering (plan §3.3): total as candlestick, broker close-P&L lines
            // (reusing the exact same per-broker data as the Line submode, just
            // repositioned for the category axis) overlaid when the scope has ≥2
            // brokers. Candlestick data is structurally a flat quad, not a SeriesPoint
            // — cast through unknown; ECharts itself doesn't care, only the shared
            // return-type annotation does (see buildFullSeries's matching cast).
            return [{name: pnlLabels.total, data: entry.pnl.candle.points.map(toCandlestickPoint) as unknown as SeriesPoint[]}, ...entry.pnl.brokers.map((broker) => ({name: broker.brokerName, data: broker.metric.points.map(toPositionalValue) as unknown as SeriesPoint[]}))];
        }

        if (viewMode === 'pnl' && pnlSubmode === 'income') {
            // DIVIDEND/INTEREST stacked bars (plan §3.4) + batch 2's costs/deposit/
            // acquisition dimensions — no broker overlay for this submode (the plan's
            // hybrid-overlay rule is specific to Line/Candles). Fixed 6-slot order
            // matches buildFullSeries's matching index reads exactly.
            return [
                {name: pnlLabels.dividend, data: entry.pnl.income.dividend.points},
                {name: pnlLabels.interest, data: entry.pnl.income.interest.points},
                {name: pnlLabels.costs, data: entry.pnl.costs.points},
                {name: pnlLabels.deposit, data: entry.pnl.deposits.points},
                {name: pnlLabels.acqNewCapital, data: entry.pnl.acquisition.fromNewCapital.points},
                {name: pnlLabels.acqReinvested, data: entry.pnl.acquisition.fromReinvested.points},
            ];
        }

        // See buildChartUpdateSeries's matching guard.
        if (viewMode === 'pnl') return [];

        return pctSeries.map((series) => ({
            name: series.name,
            data: entry.pct[series.key].points,
        }));
    }

    function buildFullSeries(isDark: boolean, seriesData: {name: string; data: SeriesPoint[]}[]): echarts.SeriesOption[] {
        if (viewMode === 'eur') {
            const cc = (key: keyof typeof COLORS) => COLORS[key][isDark ? 'dark' : 'light'];
            return [
                {
                    name: eurLabels.bookAssetLike,
                    type: 'line',
                    stack: 'bookValue',
                    data: seriesData[0].data,
                    smooth: false,
                    symbol: 'none',
                    lineStyle: {color: cc('bookAssetLike'), width: 1, opacity: 0.7},
                    areaStyle: {color: cc('bookAssetLike') + '44'},
                    itemStyle: {color: cc('bookAssetLike')},
                    emphasis: {focus: 'series'},
                },
                {
                    name: eurLabels.cashContributed,
                    type: 'line',
                    stack: 'bookValue',
                    data: seriesData[1].data,
                    smooth: false,
                    symbol: 'none',
                    lineStyle: {color: cc('cashContributed'), width: 1, opacity: 0.7},
                    areaStyle: {color: cc('cashContributed') + '44'},
                    itemStyle: {color: cc('cashContributed')},
                    emphasis: {focus: 'series'},
                },
                {
                    name: eurLabels.cashGenerated,
                    type: 'line',
                    stack: 'bookValue',
                    data: seriesData[2].data,
                    smooth: false,
                    symbol: 'none',
                    lineStyle: {color: cc('cashGenerated'), width: 1, opacity: 0.7},
                    areaStyle: {color: cc('cashGenerated') + '44'},
                    itemStyle: {color: cc('cashGenerated')},
                    emphasis: {focus: 'series'},
                },
                {name: eurLabels.nav, type: 'line', data: seriesData[3].data, smooth: false, symbol: 'none', lineStyle: {color: cc('nav'), width: 2, type: 'solid'}, itemStyle: {color: cc('nav')}, emphasis: {focus: 'series'}},
                {name: eurLabels.capitalBaseline, type: 'line', data: seriesData[4].data, smooth: false, symbol: 'none', lineStyle: {color: cc('capitalBaseline'), width: 1.5, type: 'dashed'}, itemStyle: {color: cc('capitalBaseline')}, emphasis: {focus: 'series'}},
            ];
        }

        if (viewMode === 'pnl' && pnlSubmode === 'line') {
            const greenColor = isDark ? '#4ade80' : '#16a34a';
            const redColor = isDark ? '#f87171' : '#dc2626';
            // Positive/negative split (see clipToSign) instead of a single fixed-color
            // line — ECharts visualMap doesn't reliably recolor a line's
            // lineStyle/areaStyle per value (apache/echarts#8034), so this uses the
            // same "split into multiple series" idiom as LineChart.svelte's own
            // segment coloring, just as a fixed 2-slot pair (not a variable segment
            // count) so it stays compatible with updateChartData's partial merge.
            const positiveSeries: echarts.SeriesOption = {
                name: pnlLabels.total,
                type: 'line',
                data: seriesData[0].data,
                smooth: false,
                connectNulls: false,
                symbol: 'none',
                lineStyle: {color: greenColor, width: 2, type: 'solid'},
                itemStyle: {color: greenColor},
                areaStyle: {color: greenColor, opacity: 0.15},
                emphasis: {focus: 'series'},
            };
            const negativeSeries: echarts.SeriesOption = {
                name: pnlLabels.total,
                type: 'line',
                data: seriesData[1].data,
                smooth: false,
                connectNulls: false,
                symbol: 'none',
                lineStyle: {color: redColor, width: 2, type: 'solid'},
                itemStyle: {color: redColor},
                areaStyle: {color: redColor, opacity: 0.15},
                emphasis: {focus: 'series'},
            };
            // Dashed reference line at the first-visible-day P&L (plan follow-up #3) —
            // drawn as a dedicated flat-line series, not markLine, to avoid an ECharts
            // bug where markLine + visualMap (piecewise, dimension:1, tuple data)
            // crashes with "Cannot read properties of undefined (reading 'coord')"
            // (same precedent as LineChart.svelte's own baseline reference line).
            const referenceSeries: echarts.SeriesOption = {
                type: 'line',
                name: PNL_REFERENCE_SERIES_NAME,
                data: seriesData[2].data,
                symbol: 'none',
                showSymbol: false,
                lineStyle: {color: isDark ? '#64748b' : '#9ca3af', type: 'dashed', width: 1},
                itemStyle: {color: 'transparent'},
                emphasis: {disabled: true},
                tooltip: {show: false},
                silent: true,
                z: 0,
            };
            const brokerSeries: echarts.SeriesOption[] = seriesData.slice(3).map((s, index) => ({
                name: s.name,
                type: 'line' as const,
                data: s.data,
                smooth: false,
                connectNulls: false,
                symbol: 'none',
                lineStyle: {color: brokerColor(index, isDark), width: 1.5, type: 'dashed'},
                itemStyle: {color: brokerColor(index, isDark)},
                emphasis: {focus: 'series'},
            }));
            return [positiveSeries, negativeSeries, referenceSeries, ...brokerSeries];
        }

        if (viewMode === 'pnl' && pnlSubmode === 'candles') {
            // Same up/down colors as the P&L tooltip's sign coloring, for consistency.
            const greenColor = isDark ? '#4ade80' : '#16a34a';
            const redColor = isDark ? '#f87171' : '#dc2626';
            // seriesData[0].data is really (number[]|null)[] here (see the matching cast
            // in buildChartUpdateSeries) — a flat [open,close,low,high] quad per category
            // position, matching CandlestickChart.svelte's own category-axis convention
            // (a `time` xAxis silently fails to paint any candlestick body/wick — a known
            // upstream ECharts limitation). `any` here matches the existing
            // CandlestickChart.svelte convention (`const series: any[] = []`) rather than
            // fighting the generated types file-wide.
            const candleSeries: any = {
                name: pnlLabels.total,
                type: 'candlestick',
                data: seriesData[0].data,
                barWidth: '80%',
                itemStyle: {color: greenColor, color0: redColor, borderColor: greenColor, borderColor0: redColor},
            };
            const brokerSeries: echarts.SeriesOption[] = seriesData.slice(1).map((s, index) => ({
                name: s.name,
                type: 'line' as const,
                data: s.data,
                smooth: false,
                connectNulls: false,
                symbol: 'none',
                lineStyle: {color: brokerColor(index, isDark), width: 1.5, type: 'dashed'},
                itemStyle: {color: brokerColor(index, isDark)},
                emphasis: {focus: 'series'},
            }));
            return [candleSeries, ...brokerSeries];
        }

        if (viewMode === 'pnl' && pnlSubmode === 'income') {
            const cc = (key: keyof typeof COLORS) => COLORS[key][isDark ? 'dark' : 'light'];
            return [
                {name: pnlLabels.dividend, type: 'bar' as const, stack: 'income', data: seriesData[0].data, itemStyle: {color: cc('dividend')}},
                {name: pnlLabels.interest, type: 'bar' as const, stack: 'income', data: seriesData[1].data, itemStyle: {color: cc('interest')}},
                {name: pnlLabels.costs, type: 'bar' as const, data: seriesData[2].data, itemStyle: {color: cc('costs')}},
                {name: pnlLabels.deposit, type: 'bar' as const, data: seriesData[3].data, itemStyle: {color: cc('deposit')}},
                // Acquisition 2-zone stacked bar (batch 2, plan §5.2): reuses the exact
                // same capital/returns-pool colors as EUR mode's own cashContributed/
                // cashGenerated areas — same underlying financial concept (K/R pool),
                // so the same color means the same thing everywhere in the app.
                {name: pnlLabels.acqNewCapital, type: 'bar' as const, stack: 'acquisition', data: seriesData[4].data, itemStyle: {color: cc('cashContributed')}},
                {name: pnlLabels.acqReinvested, type: 'bar' as const, stack: 'acquisition', data: seriesData[5].data, itemStyle: {color: cc('cashGenerated')}},
            ];
        }

        // See buildChartUpdateSeries's matching guard.
        if (viewMode === 'pnl') return [];

        return pctSeries.map((series, index) => ({
            name: series.name,
            type: 'line' as const,
            data: seriesData[index].data,
            smooth: false,
            connectNulls: false,
            symbol: 'none',
            lineStyle: {color: COLORS[series.colorKey][isDark ? 'dark' : 'light'], width: 2, type: series.lineStyle},
            itemStyle: {color: COLORS[series.colorKey][isDark ? 'dark' : 'light']},
        }));
    }

    function updateChartData(entry: AggregatedResolutionData, isDark: boolean, zoomWindow: {start: number; end: number}, skipAnimation: boolean, referenceDate: string | null = null) {
        if (!chartInstance) return;

        const seriesData = buildChartUpdateSeries(isDark, entry, referenceDate);
        const isCandlesSubmode = viewMode === 'pnl' && pnlSubmode === 'candles';
        const xAxisPolicy = buildResponsiveXAxisPolicy({
            width: chartContainer?.clientWidth ?? 0,
            values: entry.dates,
            locale: $locale ?? undefined,
            axisType: isCandlesSubmode ? 'category' : 'time',
        });
        const wasCompact = responsiveXAxisCompact;

        // skipAnimation is only ever true for a resolution switch (daily <-> weekly/monthly),
        // where the data-point count per series changes drastically. If a tooltip is
        // currently showing (user hovering while zooming — the exact gesture that triggers
        // a resolution switch), ECharts can crash inside its internal _showAxisTooltip
        // reading stale series/dataIndex references once series are replaced via
        // replaceMerge. Hiding the tooltip first clears that internal state safely.
        if (skipAnimation) {
            chartInstance.dispatchAction({type: 'hideTip'});
        }

        if (wasCompact && !xAxisPolicy.compact) {
            applyFullOption(isDark, buildFullSeries(isDark, seriesData), zoomWindow);
            return;
        }

        responsiveXAxisCompact = xAxisPolicy.compact;
        const series = seriesData.map((seriesEntry) => ({
            name: seriesEntry.name,
            data: seriesEntry.data,
        }));
        chartInstance.setOption(
            {
                ...(skipAnimation
                    ? {
                          animation: false,
                          animationDuration: 0,
                          animationDurationUpdate: 0,
                      }
                    : CHART_ANIMATION_CONFIG),
                dataZoom: [{type: 'inside', ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG, start: zoomWindow.start, end: zoomWindow.end}],
                // Candles submode's category axis must keep `data` (the bucket dates) in
                // lockstep with `entry.dates` on every update — unlike the time axis, whose
                // positions are computed from the timestamps embedded in each data point, a
                // category axis's positions come ONLY from this array. A resolution switch
                // (daily <-> weekly/monthly) changes both, so it can't be gated behind the
                // `compact` check the time-axis branch uses for its label-only refresh.
                xAxis: isCandlesSubmode ? {data: entry.dates, ...(xAxisPolicy.compact ? {axisLabel: xAxisPolicy.axisLabel} : {})} : xAxisPolicy.compact ? {splitNumber: xAxisPolicy.splitNumber, axisLabel: xAxisPolicy.axisLabel} : {},
                series,
            },
            CHART_SERIES_UPDATE_OPTS,
        );
    }

    function syncResolutionToViewport() {
        if (!chartInstance || history.length === 0) return;

        const logicalRange = getLogicalRangeFromChart() ?? ensureLogicalRange();
        if (!logicalRange) return;

        visibleStartDate = logicalRange.startDate;
        visibleEndDate = logicalRange.endDate;

        const counts = computeBucketCounts(logicalRange.startDate, logicalRange.endDate);
        const plotWidthPx = chartInstance.getWidth();
        const targetResolution = cascadeResolution(currentResolution, counts, plotWidthPx);

        if (targetResolution === currentResolution) return;

        currentResolution = targetResolution;
        const entry = getResolutionData(targetResolution);
        const isDark = document.documentElement.classList.contains('dark');
        const zoomWindow = buildZoomWindow(targetResolution, logicalRange.startDate, logicalRange.endDate);

        activeChartData = entry;
        updateChartData(entry, isDark, zoomWindow, true, logicalRange.startDate);
    }

    function scheduleResolutionSync() {
        if (resolutionDebounceTimer) clearTimeout(resolutionDebounceTimer);
        resolutionDebounceTimer = setTimeout(() => {
            resolutionDebounceTimer = null;
            syncResolutionToViewport();
        }, 200);
    }

    // =========================================================================
    // Lifecycle
    // =========================================================================

    let tooltipCleanup: (() => void) | null = null;

    onMount(() => {
        darkModeObserver = new MutationObserver(() => renderChart());
        darkModeObserver.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});

        return () => {
            if (resolutionDebounceTimer) clearTimeout(resolutionDebounceTimer);
            dataZoomCleanup?.();
            tooltipCleanup?.();
            darkModeObserver?.disconnect();
            resizeWatcher.disconnect();
            dataZoomTouchPanHandle?.dispose();
            dataZoomTouchPanHandle = null;
            chartInstance?.dispose();
        };
    });

    // G1b — lazy candle fetch: fire the request-callback once when the user activates the
    // candles submode and no data has arrived yet. Re-fires harmlessly if pnlCandles is
    // still null next time this effect runs (e.g. after a broker/date-range refetch reset
    // it) — the caller's own report cache makes a repeat request cheap.
    $effect(() => {
        if (viewMode === 'pnl' && pnlSubmode === 'candles' && pnlCandles == null) {
            onRequestPnlCandles?.();
        }
    });

    $effect(() => {
        // Re-render when data, viewMode, or locale changes.
        // Every lazily-arriving data prop must be listed: the dashboard happens to assign
        // the four income-family props in one contiguous block, so `incomeHistory` used to
        // wake the effect for the other three — correct by adjacency, not by design.
        void history;
        void viewMode;
        void pnlSubmode;
        void pctSeries;
        void eurLabels;
        void pnlLabels;
        void brokerPnlHistory;
        void pnlCandles;
        void incomeHistory;
        void costHistory;
        void depositHistory;
        void acquisitionFunding;
        void $locale;

        if (history !== lastHistoryRef) {
            const preservedRange = getLogicalRangeFromChart();
            lastHistoryRef = history;
            resetResolutionState(preservedRange);
        }

        if (chartContainer) {
            tick().then(() => {
                setupResizeObserver();
                renderChart();
            });
        }
    });

    // =========================================================================
    // Helpers
    // =========================================================================

    function setupResizeObserver() {
        resizeWatcher.observe(chartContainer);
    }

    function renderChart(forceFullXAxisRebuild = false) {
        if (!chartContainer || loading || history.length === 0) return;

        if (chartInstance && chartInstance.getDom() !== chartContainer) {
            dataZoomCleanup?.();
            dataZoomTouchPanHandle?.dispose();
            dataZoomTouchPanHandle = null;
            chartInstance.dispose();
            chartInstance = undefined;
            lastRenderedMode = null;
            lastRenderedDark = null;
        }

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
            attachChartReady(chartInstance, chartContainer, 'growth');
            needsInitialLayoutStabilityPass = true;
            // Setup mobile tooltip auto-hide
            tooltipCleanup?.();
            tooltipCleanup = setupTooltipAutoHide(chartContainer, () => chartInstance);
            dataZoomTouchPanHandle = attachDataZoomTouchPan(chartInstance, chartContainer);
            dataZoomCleanup?.();
            const zoomInstance = chartInstance;
            const onDataZoom = () => scheduleResolutionSync();
            zoomInstance.on('dataZoom', onDataZoom);
            dataZoomCleanup = () => zoomInstance.off('dataZoom', onDataZoom);
        }

        const isDark = document.documentElement.classList.contains('dark');
        const liveRange = getLogicalRangeFromChart();
        if (liveRange) {
            visibleStartDate = liveRange.startDate;
            visibleEndDate = liveRange.endDate;
        }
        const logicalRange = ensureLogicalRange();
        if (!logicalRange) return;

        if (resolutionResetPending) {
            const counts = computeBucketCounts(logicalRange.startDate, logicalRange.endDate);
            currentResolution = chooseInitialResolution(counts, chartInstance.getWidth());
            resolutionResetPending = false;
        }

        const activeData = getResolutionData(currentResolution);
        const zoomWindow = buildZoomWindow(currentResolution, logicalRange.startDate, logicalRange.endDate);
        activeChartData = activeData;

        // Determine if this is a data-only update (same mode+submode, same dark) or full re-init
        const renderedModeKey = viewMode === 'pnl' ? `pnl:${pnlSubmode}` : viewMode;
        const needsFullInit = forceFullXAxisRebuild || lastRenderedMode !== renderedModeKey || lastRenderedDark !== isDark;
        const seriesData = buildChartUpdateSeries(isDark, activeData, logicalRange.startDate);

        if (needsFullInit) {
            applyFullOption(isDark, buildFullSeries(isDark, seriesData), zoomWindow);
        } else {
            updateChartData(activeData, isDark, zoomWindow, false, logicalRange.startDate);
        }

        lastRenderedMode = renderedModeKey;
        lastRenderedDark = isDark;
    }

    function applyFullOption(isDark: boolean, series: echarts.SeriesOption[], zoomWindow: {start: number; end: number}) {
        if (!chartInstance) return;
        const {bg: tooltipBg, border: tooltipBorder, textColor, mutedColor} = buildTooltipTheme(isDark);
        const gridColor = isDark ? '#1e293b' : '#f1f5f9';
        // Candles submode uses a category axis (see buildFullSeries's matching comment
        // for why: candlestick silently fails to paint on a time axis, a known ECharts
        // limitation) — every other mode/submode keeps the shared time axis. The zoom
        // pipeline (buildZoomWindow/getLogicalRangeFromChart) is already index/percentage-
        // based, never timestamp-based, so this fork needs no changes there.
        const isCandlesSubmode = viewMode === 'pnl' && pnlSubmode === 'candles';
        const xAxisPolicy = buildResponsiveXAxisPolicy({
            width: chartContainer?.clientWidth ?? 0,
            values: activeChartData?.dates ?? dates,
            locale: $locale ?? undefined,
            axisType: isCandlesSubmode ? 'category' : 'time',
        });
        responsiveXAxisCompact = xAxisPolicy.compact;

        const yAxisFormatter =
            viewMode === 'pct'
                ? (v: number) => `${v.toFixed(1)}%`
                : (v: number) => {
                      if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
                      if (Math.abs(v) >= 1_000) return `${(v / 1_000).toFixed(0)}k`;
                      return String(v);
                  };

        /** Format a number as currency — same pattern as the dashboard formatMoney helper. */
        const fmtCurrency = (v: number | null | undefined) => (v != null ? `${baseCurrency} ${v.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : '—');

        const option: echarts.EChartsOption = {
            ...CHART_ANIMATION_CONFIG,
            backgroundColor: 'transparent',
            // `top` reserves a band for the floating overlay controls (submode toggle
            // left, window selector right) so they never sit on top of the plot or its
            // y-axis labels — the developer's review found the toggle drawn over the
            // axis "600" label. Reserving in the grid rather than nudging the overlay
            // keeps the plot honest at small heights: the chart shrinks by exactly the
            // band it gives away, instead of silently drawing content underneath a
            // control. Only P&L mode shows those overlays, so only it pays the cost.
            // `left` is an explicit px constant shared with the floating overlay cluster
            // (see CHART_PLOT_LEFT_PX): the controls must clear the y-axis label gutter,
            // and with `containLabel: true` that gutter is COMPUTED from the widest tick
            // label — so a hardcoded Tailwind offset on the overlay would align only by
            // coincidence and break the first time a label got wider (another currency,
            // a larger portfolio). One number, two uses, agreeing by construction.
            // `top` stays 10px in every mode: the toggle is an OVERLAY and must float on
            // the plot, not push it down (developer review — reserving a band shortened
            // the chart, which was never what was asked for).
            grid: {left: CHART_PLOT_LEFT_PX, right: '4%', bottom: '30px', top: '10px', containLabel: true},
            tooltip: {
                trigger: 'axis',
                // Bugfix: `appendToBody` moves the tooltip DOM to `document.body`, which
                // requires ECharts/zrender to convert our chart-local position into
                // document-absolute coordinates (accounting for scroll) — the exact same
                // class of bug already fixed once in PriceChartFull.svelte (see commit
                // fcdd89e8: "Fix mobile tooltip scroll offset ... instead of
                // cursor-relative positioning that shifted with vertical scroll") by
                // dropping `appendToBody` entirely. Without it, the tooltip stays nested
                // inside this chart's own container (forced to `position:relative`),
                // scrolling as ONE unit with the rest of the page — no coordinate
                // conversion needed at all, so it can't drift out of sync with scroll.
                // Not needed for clipping either: this card has no `overflow-hidden`
                // ancestor.
                confine: true,
                position: tooltipPositionSide,
                axisPointer: {type: 'line'},
                backgroundColor: tooltipBg,
                borderColor: tooltipBorder,
                borderWidth: 1,
                textStyle: {color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 12},
                formatter: (params: any) => {
                    const items = Array.isArray(params) ? params : [params];
                    const idx = items[0]?.dataIndex ?? 0;
                    const bucket = activeChartData?.buckets[idx];
                    if (!bucket) return '';
                    let html = buildTooltipBucketHeader(bucket, {bg: tooltipBg, border: tooltipBorder, textColor, mutedColor});

                    if (viewMode === 'eur') {
                        const assetCostVal = activeChartData?.eur.bookAssetLike.values[idx];
                        const cashGenVal = activeChartData?.eur.cashGenerated.values[idx];
                        const cashContribVal = activeChartData?.eur.cashContributed.values[idx];
                        const navVal = activeChartData?.eur.nav.values[idx];
                        const baselineVal = activeChartData?.eur.capitalBaseline.values[idx];
                        const totalPnlVal = activeChartData?.eur.totalPnl.values[idx];

                        const cc = (key: keyof typeof COLORS) => COLORS[key][isDark ? 'dark' : 'light'];
                        const fmtOrDash = (v: number | null | undefined) => (v != null && v !== 0 ? fmtCurrency(v) : '—');

                        html += buildTooltipRow(`<b>${eurLabels.nav}</b>`, fmtCurrency(navVal), cc('nav'));
                        html += buildTooltipRow(eurLabels.capitalBaselineTooltip, fmtCurrency(baselineVal), cc('capitalBaseline'));
                        if (totalPnlVal != null) {
                            const pnlColor = totalPnlVal >= 0 ? (isDark ? '#4ade80' : '#16a34a') : isDark ? '#f87171' : '#dc2626';
                            html += `<div style="display:flex;justify-content:space-between;gap:16px;color:${pnlColor}"><span><b>${$_('dashboard.totalPnl')}</b></span><b>${totalPnlVal >= 0 ? '+' : '−'}${fmtCurrency(Math.abs(totalPnlVal))}</b></div>`;
                        }
                        html += `<div style="font-size:10px;color:${textColor};opacity:0.7">${$_('dashboard.pnlFormulaHint')}</div>`;
                        html += buildTooltipDivider(tooltipBorder);
                        html += buildTooltipRow(eurLabels.bookAssetLikeTooltip, fmtOrDash(assetCostVal), cc('bookAssetLike'));
                        html += buildTooltipRow(eurLabels.cashGenerated, fmtOrDash(cashGenVal), cc('cashGenerated'));
                        html += buildTooltipRow(eurLabels.cashContributed, fmtOrDash(cashContribVal), cc('cashContributed'));
                        return html;
                    }

                    if (viewMode === 'pnl' && pnlSubmode === 'line') {
                        const totalVal = activeChartData?.pnl.total.values[idx];
                        const cc = (key: keyof typeof COLORS) => COLORS[key][isDark ? 'dark' : 'light'];
                        const pnlRow = (label: string, v: number | null | undefined, color: string) => {
                            if (v == null) return buildTooltipRow(label, '—', color);
                            const signColor = v >= 0 ? (isDark ? '#4ade80' : '#16a34a') : isDark ? '#f87171' : '#dc2626';
                            return `<div style="display:flex;justify-content:space-between;gap:16px;color:${color}"><span>${label}</span><b style="color:${signColor}">${v >= 0 ? '+' : '−'}${fmtCurrency(Math.abs(v))}</b></div>`;
                        };
                        html += pnlRow(`<b>${pnlLabels.total}</b>`, totalVal, cc('totalPnl'));
                        activeChartData?.pnl.brokers.forEach((broker, index) => {
                            html += pnlRow(broker.brokerName, broker.metric.values[idx], brokerColor(index, isDark));
                        });
                        return html;
                    }

                    if (viewMode === 'pnl' && pnlSubmode === 'candles') {
                        const cc = (key: keyof typeof COLORS) => COLORS[key][isDark ? 'dark' : 'light'];
                        const candle = activeChartData?.pnl.candle.points[idx];
                        const ohlcRow = (label: string, v: number | null | undefined) => `<div style="display:flex;justify-content:space-between;gap:16px;color:${textColor}"><span>${label}</span><b>${v != null ? fmtCurrency(v) : '—'}</b></div>`;
                        if (candle && candle.close != null) {
                            html += ohlcRow($_('dataEditor.col.open'), candle.open);
                            html += ohlcRow($_('dataEditor.col.close'), candle.close);
                            html += ohlcRow($_('dataEditor.col.high'), candle.high);
                            html += ohlcRow($_('dataEditor.col.low'), candle.low);
                        } else {
                            html += `<div style="color:${mutedColor}">${$_('common.noData')}</div>`;
                        }
                        // Compact form for the tooltip; the always-visible caption below
                        // the chart carries the full sentence (…HypotheticalShort vs
                        // …Hypothetical — two distinct keys, not a truncation).
                        html += `<div style="font-size:10px;color:${textColor};opacity:0.7;margin-top:4px">${$_('dashboard.pnlCandlesHypotheticalShort')}</div>`;
                        activeChartData?.pnl.brokers.forEach((broker, index) => {
                            const v = broker.metric.values[idx];
                            if (v == null) return;
                            const signColor = v >= 0 ? (isDark ? '#4ade80' : '#16a34a') : isDark ? '#f87171' : '#dc2626';
                            html += `<div style="display:flex;justify-content:space-between;gap:16px;color:${brokerColor(index, isDark)}"><span>${broker.brokerName}</span><b style="color:${signColor}">${v >= 0 ? '+' : '−'}${fmtCurrency(Math.abs(v))}</b></div>`;
                        });
                        return html;
                    }

                    if (viewMode === 'pnl' && pnlSubmode === 'income') {
                        const cc = (key: keyof typeof COLORS) => COLORS[key][isDark ? 'dark' : 'light'];
                        const divVal = activeChartData?.pnl.income.dividend.values[idx] ?? 0;
                        const intVal = activeChartData?.pnl.income.interest.values[idx] ?? 0;
                        const costVal = activeChartData?.pnl.costs.values[idx] ?? 0;
                        const depositVal = activeChartData?.pnl.deposits.values[idx] ?? 0;
                        const acqNewVal = activeChartData?.pnl.acquisition.fromNewCapital.values[idx] ?? 0;
                        const acqReinvestedVal = activeChartData?.pnl.acquisition.fromReinvested.values[idx] ?? 0;
                        const signedRow = (label: string, v: number, color: string) => {
                            const signColor = v >= 0 ? (isDark ? '#4ade80' : '#16a34a') : isDark ? '#f87171' : '#dc2626';
                            return `<div style="display:flex;justify-content:space-between;gap:16px;color:${color}"><span>${label}</span><b style="color:${signColor}">${v >= 0 ? '+' : '−'}${fmtCurrency(Math.abs(v))}</b></div>`;
                        };
                        html += signedRow(pnlLabels.dividend, divVal, cc('dividend'));
                        html += signedRow(pnlLabels.interest, intVal, cc('interest'));
                        html += buildTooltipDivider(tooltipBorder);
                        html += signedRow(`<b>${$_('assets.distribution.total')}</b>`, divVal + intVal, textColor);
                        // Batch 2 dimensions: costs/deposit/acquisition are distinct economic
                        // concepts from personal income, so each gets its own row rather than
                        // folding into the income total above.
                        if (costVal !== 0 || depositVal !== 0 || acqNewVal !== 0 || acqReinvestedVal !== 0) {
                            html += buildTooltipDivider(tooltipBorder);
                            if (costVal !== 0) html += signedRow(pnlLabels.costs, costVal, cc('costs'));
                            if (depositVal !== 0) html += signedRow(pnlLabels.deposit, depositVal, cc('deposit'));
                            if (acqNewVal !== 0 || acqReinvestedVal !== 0) {
                                html += signedRow(pnlLabels.acqNewCapital, acqNewVal, cc('cashContributed'));
                                html += signedRow(pnlLabels.acqReinvested, acqReinvestedVal, cc('cashGenerated'));
                            }
                        }
                        return html;
                    }

                    // See buildChartUpdateSeries's matching guard.
                    if (viewMode === 'pnl') return html;

                    html += items
                        .filter((p: any) => p.value != null)
                        .map((p: any) => {
                            const rawVal = Array.isArray(p.value) ? p.value[1] : p.value;
                            const val = `${Number(rawVal).toFixed(2)}%`;
                            return buildTooltipRow(p.seriesName, val, p.color);
                        })
                        .join('');
                    return html;
                },
            },
            legend: {
                type: 'scroll',
                bottom: 0,
                left: 'center',
                textStyle: {color: textColor, fontSize: 14},
                itemWidth: 14,
                itemHeight: 8,
                // Without an explicit `data`, ECharts derives the legend from EVERY
                // series name — which leaked the internal PNL_REFERENCE_SERIES_NAME
                // decoration into the UI. Derived from the real series here rather
                // than hand-listed, so a future series is included automatically and
                // only genuine non-data decorations need to opt out.
                // Duplicates are collapsed on purpose: the P&L Line submode's
                // positive/negative halves deliberately share `pnlLabels.total`, so
                // they must show as ONE "Total P&L" entry that toggles both halves.
                data: [...new Set(series.map((s) => s.name).filter((n): n is string => typeof n === 'string' && n !== PNL_REFERENCE_SERIES_NAME))],
            },
            dataZoom: [{type: 'inside', ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG, start: zoomWindow.start, end: zoomWindow.end}],
            xAxis: isCandlesSubmode
                ? {
                      type: 'category',
                      data: activeChartData?.dates ?? dates,
                      boundaryGap: true,
                      axisLabel: {
                          color: textColor,
                          fontSize: 14,
                          rotate: 0,
                          ...(xAxisPolicy.axisLabel ?? {}),
                      },
                      axisLine: {lineStyle: {color: gridColor}},
                      splitLine: {show: false},
                  }
                : {
                      type: 'time',
                      ...(xAxisPolicy.compact ? {splitNumber: xAxisPolicy.splitNumber} : {}),
                      axisLabel: {
                          color: textColor,
                          fontSize: 14,
                          rotate: 0,
                          ...(xAxisPolicy.axisLabel ?? {}),
                      },
                      axisLine: {lineStyle: {color: gridColor}},
                      splitLine: {show: false},
                  },
            yAxis: {
                type: 'value',
                // Use a min function so the y-axis auto-scales rather than forcing 0.
                // This gives detail visibility when portfolio values are large.
                min: (value: {min: number; max: number}) => Math.floor(value.min - (value.max - value.min) * 0.08),
                axisLabel: {color: textColor, fontSize: 14, formatter: yAxisFormatter},
                axisLine: {show: false},
                splitLine: {lineStyle: {color: gridColor, type: 'dashed'}},
            },
            series,
        };

        chartInstance.setOption(option, CHART_FULL_UPDATE_OPTS);
        // Bugfix: on mobile, the very FIRST render can happen while the surrounding
        // layout (KPI cards etc.) is still settling, so ECharts caches stale internal
        // dimensions — causing the position-aware tooltip (tooltipPositionSide) to
        // compute wildly wrong coordinates (reported: tooltip appears far below the
        // viewport on first load, translate3d(...) with a huge Y offset). Toggling the
        // view mode "fixed" it because that path re-triggers this same full-rebuild
        // branch on a LATER, already-settled pass.
        //
        // IMPORTANT: this forced resize() must be scoped to ONLY the very first render
        // pass, never to later full rebuilds (dark mode toggle, data updates) — resize()
        // always triggers a full internal re-render (see node_modules/echarts
        // .../TooltipView.js `render()`/`_keepShow()`), which was found to interrupt a
        // just-shown tap-triggered tooltip on mobile (it would flash and disappear
        // immediately) if a rebuild happened to fire while the tooltip was showing.
        //
        // A fixed-delay chain (immediate + next-frame + a guessed timeout) is fragile:
        // it still regressed once when unrelated dashboard changes made surrounding
        // async content settle slower, and it can still fire too early on a genuinely
        // slow COLD reload (fonts/images/KPI network calls all racing at once) — which
        // matches this bug being reported ONLY on cold reload, never on warm in-app
        // navigation where the layout is already stable by the time this mounts.
        // Two more principled, non-magic-number signals instead:
        //  1) Poll ACTUAL layout stability (position AND size — a ResizeObserver alone
        //     misses a pure reflow/reposition caused by content ABOVE this chart, e.g.
        //     a cash-balances skeleton collapsing once its data arrives) via rAF, and
        //     resize only once the container's rect stops moving for 2 straight frames.
        //  2) Also resize on the browser's `load` event — fired precisely when every
        //     page resource (fonts, images) is done loading, i.e. exactly the "cold
        //     reload settling" signal a fixed timeout could only ever approximate.
        if (needsInitialLayoutStabilityPass && chartContainer) {
            needsInitialLayoutStabilityPass = false;
            scheduleFirstRenderStabilityFix(chartInstance, chartContainer);
        }
    }
</script>

<div class="bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm p-4 flex flex-col gap-3" data-testid="growth-chart">
    <!-- Header row: title + toggle -->
    <div class="flex items-center justify-between">
        <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-200">{$_('dashboard.growth')}</h2>

        <!-- Abs / % / P&L segmented toggle -->
        <div class="flex rounded-lg overflow-hidden border border-gray-200 dark:border-slate-600 text-xs font-medium">
            <button class="px-3 py-1 transition-colors {viewMode === 'eur' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}" onclick={() => (viewMode = 'eur')} data-testid="growth-toggle-eur">
                {$_('dashboard.abs')}
            </button>
            <button
                class="px-3 py-1 transition-colors border-l border-gray-200 dark:border-slate-600 {viewMode === 'pct' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'} {!hasPctData
                    ? 'opacity-50 cursor-not-allowed'
                    : ''}"
                onclick={() => hasPctData && (viewMode = 'pct')}
                disabled={!hasPctData}
                title={!hasPctData ? $_('common.noData') : ''}
                data-testid="growth-toggle-pct"
            >
                {$_('dashboard.pct')}
            </button>
            <button
                class="px-3 py-1 transition-colors border-l border-gray-200 dark:border-slate-600 {viewMode === 'pnl' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                onclick={() => (viewMode = 'pnl')}
                data-testid="growth-toggle-pnl"
            >
                {$_('dashboard.pnl')}
            </button>
        </div>
    </div>

    <!-- Chart area — container always in DOM for animation persistence -->
    <div class="relative" style="height: {height}">
        <!-- Top-left cluster: P&L submode toggle + resolution badge on ONE row.
             The submode toggle moved here (developer review: "il selettore su linea,
             candela e income doveva essere a sinistra"), which collided with the
             badge's former solo top-left slot. Reconciled using PriceChartFull's own
             established pattern — its controls and ResolutionBadge already share a
             single left-aligned flex row with the badge last — rather than inventing
             a new placement or silently displacing the badge. -->
        <div class="absolute top-2 z-10 flex flex-wrap items-center gap-1.5" style="left: {CHART_PLOT_LEFT_PX}px">
            {#if viewMode === 'pnl'}
                <!-- Icon + label. Below `sm` the label folds away and only the icon
                     remains (developer review), but the label text is NOT lost: it stays
                     reachable as `title`/`aria-label` on the button in BOTH states, so the
                     control remains usable with a screen reader exactly where it is
                     hardest to use. `data-testid` is deliberately identical across
                     breakpoints — a testid that changes with viewport would make every
                     E2E selector viewport-dependent. -->
                <div class="flex rounded-lg border border-gray-200/70 dark:border-slate-600/70 overflow-hidden shadow-sm opacity-75 hover:opacity-100 transition-opacity text-xs font-medium">
                    <button
                        class="px-2 sm:px-3 py-1 transition-colors inline-flex items-center gap-1.5 {pnlSubmode === 'line' ? 'bg-libre-green text-white' : 'bg-white/90 dark:bg-slate-800/90 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                        onclick={() => (pnlSubmode = 'line')}
                        title={$_('dashboard.pnlSubmodeLine')}
                        aria-label={$_('dashboard.pnlSubmodeLine')}
                        aria-pressed={pnlSubmode === 'line'}
                        data-testid="growth-pnl-submode-line"
                    >
                        <ChartLine size={14} aria-hidden="true" />
                        <span class="hidden sm:inline">{$_('dashboard.pnlSubmodeLine')}</span>
                    </button>
                    <button
                        class="px-2 sm:px-3 py-1 transition-colors inline-flex items-center gap-1.5 border-l border-gray-200/70 dark:border-slate-600/70 {pnlSubmode === 'candles'
                            ? 'bg-libre-green text-white'
                            : 'bg-white/90 dark:bg-slate-800/90 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                        onclick={() => (pnlSubmode = 'candles')}
                        title={$_('dashboard.pnlSubmodeCandles')}
                        aria-label={$_('dashboard.pnlSubmodeCandles')}
                        aria-pressed={pnlSubmode === 'candles'}
                        data-testid="growth-pnl-submode-candles"
                    >
                        <ChartCandlestick size={14} aria-hidden="true" />
                        <span class="hidden sm:inline">{$_('dashboard.pnlSubmodeCandles')}</span>
                    </button>
                    <button
                        class="px-2 sm:px-3 py-1 transition-colors inline-flex items-center gap-1.5 border-l border-gray-200/70 dark:border-slate-600/70 {pnlSubmode === 'income'
                            ? 'bg-libre-green text-white'
                            : 'bg-white/90 dark:bg-slate-800/90 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                        onclick={() => (pnlSubmode = 'income')}
                        title={$_('dashboard.pnlSubmodeIncome')}
                        aria-label={$_('dashboard.pnlSubmodeIncome')}
                        aria-pressed={pnlSubmode === 'income'}
                        data-testid="growth-pnl-submode-income"
                    >
                        <Coins size={14} aria-hidden="true" />
                        <span class="hidden sm:inline">{$_('dashboard.pnlSubmodeIncome')}</span>
                    </button>
                </div>
            {/if}
            <div class="pointer-events-none">
                <ResolutionBadge resolution={currentResolution} />
            </div>
        </div>
        {#if viewMode === 'pnl'}
            <!-- Zoom-window selector (1W/1M/1Y/All), top-RIGHT. Shown in ALL THREE P&L
                 submodes (developer review: "i range li hai messi solo negli income!
                 devi farli anche nelle candele"). Only the guard was ever
                 income-specific — `selectZoomWindow` has always written the SHARED
                 `visibleStartDate`/`visibleEndDate` + dataZoom, so a window picked in one
                 submode already carried across the others; widening the guard exposes a
                 mechanism that was there, it does not add one.
                 NOTE this is a ZOOM selector, not the candle-width ladder (DBT-7): both
                 are wanted and neither substitutes for the other. The `income*` naming
                 below is now inaccurate and a rename is proposed separately — testids are
                 developer-visible churn, so it is not done unilaterally here. -->
            <div class="absolute top-2 right-2 z-10 flex items-center gap-1.5">
                <div class="flex rounded-lg border border-gray-200/70 dark:border-slate-600/70 overflow-hidden shadow-sm opacity-75 hover:opacity-100 transition-opacity text-xs font-medium">
                    <button
                        class="px-2.5 py-1 transition-colors {zoomWindowPreset === '1W' ? 'bg-libre-green text-white' : 'bg-white/90 dark:bg-slate-800/90 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                        onclick={() => selectZoomWindow('1W')}
                        data-testid="growth-zoom-window-1w">1W</button
                    >
                    <button
                        class="px-2.5 py-1 transition-colors border-l border-gray-200/70 dark:border-slate-600/70 {zoomWindowPreset === '1M' ? 'bg-libre-green text-white' : 'bg-white/90 dark:bg-slate-800/90 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                        onclick={() => selectZoomWindow('1M')}
                        data-testid="growth-zoom-window-1m">1M</button
                    >
                    <button
                        class="px-2.5 py-1 transition-colors border-l border-gray-200/70 dark:border-slate-600/70 {zoomWindowPreset === '1Y' ? 'bg-libre-green text-white' : 'bg-white/90 dark:bg-slate-800/90 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                        onclick={() => selectZoomWindow('1Y')}
                        data-testid="growth-zoom-window-1y">1Y</button
                    >
                    <button
                        class="px-2.5 py-1 transition-colors border-l border-gray-200/70 dark:border-slate-600/70 {zoomWindowPreset === 'all' ? 'bg-libre-green text-white' : 'bg-white/90 dark:bg-slate-800/90 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                        onclick={() => selectZoomWindow('all')}
                        data-testid="growth-zoom-window-all">All</button
                    >
                </div>
            </div>
        {/if}
        <!-- Skeleton / empty overlay -->
        {#if loading}
            <div class="absolute inset-0 z-10 bg-gray-100 dark:bg-slate-700 rounded animate-pulse"></div>
        {:else if history.length === 0}
            <div class="absolute inset-0 z-10 flex items-center justify-center text-gray-400 dark:text-gray-500 text-sm">
                {$_('common.noData')}
            </div>
        {/if}
        <!-- Persistent chart container — never destroyed -->
        <div bind:this={chartContainer} style="height: 100%; width: 100%;" class:invisible={loading || history.length === 0}></div>
    </div>
    {#if !loading && history.length > 0 && viewMode === 'pct' && hasPctData && !hasNonZeroPctData}
        <p class="text-center text-xs text-gray-400 dark:text-gray-500 italic mt-1">
            {$_('dashboard.roiAllZero')}
        </p>
    {/if}
    {#if !loading && viewMode === 'pnl' && pnlSubmode === 'candles'}
        <!-- Mandatory always-visible synthetic-candle disclosure (plan §3.3). -->
        <p class="text-center text-xs text-gray-400 dark:text-gray-500 italic mt-1" data-testid="growth-pnl-candles-hypothetical-label">{$_('dashboard.pnlCandlesHypothetical')}</p>
    {/if}
</div>
