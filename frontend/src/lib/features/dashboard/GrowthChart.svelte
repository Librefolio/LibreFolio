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
    import {CHART_INIT_THEME} from '$lib/components/charts/chartFont';
    import {chartInitOptions} from '$lib/components/charts/chartPixelRatio';
    import {attachChartReady} from '$lib/utils/chartReady';
    import {getUserStorage, setUserStorage} from '$lib/utils/storage';
    import {maskFormattedNumber, shouldMaskAmount} from '$lib/utils/privacy/maskable';
    import {createResizeWatcher} from '$lib/utils/core/resizeWatcher';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import {CHART_ANIMATION_CONFIG, CHART_SET_OPTION_OPTS} from '$lib/components/charts/echartsAnimationConfig';
    import {_} from '$lib/i18n';
    import {axisLabelMeasure, buildResponsiveXAxisPolicy, timeAxisGridRight} from '$lib/components/charts/responsiveXAxis';
    import {clampGrowthLogicalRange, type GrowthLogicalRange} from './growthChartRange';
    import {planLadderAxis, ladderAxisOption, type LadderAxisPlan} from './growthLadderAxis';
    import {countCalendarBuckets} from './growthLadderBuckets';
    import {todayIso} from '$lib/utils/dateOnly';
    import ResolutionBadge from '$lib/components/charts/ResolutionBadge.svelte';
    import {cascadeResolution, chooseInitialResolution, computeDensity, type ChartGrammar} from '$lib/components/charts/timeSeriesAggregation';
    import type {ChartResolution} from '$lib/components/charts/timeSeriesAggregation';
    import type {PortfolioHistoryPoint, PortfolioBrokerPnlHistory, PortfolioPnlCandleSeries, PortfolioIncomeHistorySeries, PortfolioCostHistorySeries, PortfolioDepositHistorySeries, PortfolioAcquisitionFundingSeries} from '$lib/stores/portfolio/portfolioStore.svelte';
    import {buildTooltipTheme, tooltipPositionSide, setupTooltipAutoHide, scheduleFirstRenderStabilityFix} from '$lib/components/charts/echartsTooltipHelpers';
    import {INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG} from '$lib/components/charts/chartCoreHelpers';
    import {attachDataZoomTouchPan, type DataZoomTouchPanHandle} from '$lib/components/charts/echartsDataZoomTouchPan';
    import {ChartLine, ChartCandlestick, Coins} from 'lucide-svelte';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import {uiLocale} from '$lib/stores/app/uiLocale';
    import {chartNeutrals} from '$lib/theme/chartTheme';
    import {isDarkTheme, onChartColorsChange, onThemeClassChange} from '$lib/theme/themeMode';
    import {
        alignFlowToDates,
        buildLadderData,
        buildResolutionData,
        buildZoomWindow,
        cascadeIndicesAt,
        countBuckets,
        ladderIndicesAt,
        mapBrokerPnlSeries,
        mapCandlesByDate,
        mapEurStackedData,
        mapPctValues,
        type AggregatedResolutionData,
        type AggregationInputs,
        type CandleWidth,
    } from './growthChartData';
    import {buildGrowthFullSeries, buildGrowthUpdateSeries, INCOME_BAR_SHARE, PNL_REFERENCE_SERIES_NAME, type GrowthMode, type GrowthSeriesContext, type GrowthSeriesData, type PnlSubmode} from './growthChartSeries';
    import {buildGrowthTooltip, type GrowthTooltipView} from './growthChartTooltip';

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

    // The mode and the P&L submode persist per user, with one key shared by Dashboard and
    // Broker detail (AllocationPanel and PositionsPanel do the same). The candle width is
    // deliberately NOT persisted: every entry into the ladder applies its opening rule.
    const MODE_STORAGE_KEY = 'dashboard-growth-mode';
    const SUBMODE_STORAGE_KEY = 'dashboard-growth-pnl-submode';

    function readStoredMode(): GrowthMode {
        const stored = getUserStorage(MODE_STORAGE_KEY, 'eur');
        return stored === 'pct' || stored === 'pnl' ? stored : 'eur';
    }

    function readStoredSubmode(): PnlSubmode {
        const stored = getUserStorage(SUBMODE_STORAGE_KEY, 'line');
        return stored === 'candles' || stored === 'income' ? stored : 'line';
    }

    const restoredMode = readStoredMode();
    const restoredSubmode = readStoredSubmode();
    let viewMode: GrowthMode = $state(restoredMode);
    // pnlSubmode = line|candles|income (plan §5.1). All three submodes are live and the
    // picker is rendered (data-testid growth-pnl-submode-*); 'candles' is where the
    // synthetic OHLC series is shown.
    let pnlSubmode: PnlSubmode = $state(restoredSubmode);
    /** The view fell back from % to Abs because the loaded history has no % data (see the effect below). */
    let pctFallback = false;

    function isIncomeView(): boolean {
        return viewMode === 'pnl' && pnlSubmode === 'income';
    }

    function selectMode(mode: GrowthMode) {
        const wasIncome = isIncomeView();
        viewMode = mode;
        pctFallback = false;
        setUserStorage(MODE_STORAGE_KEY, mode);
        if (!wasIncome && isIncomeView()) incomeOpeningPending = true;
    }

    function selectSubmode(submode: PnlSubmode) {
        const wasIncome = isIncomeView();
        pnlSubmode = submode;
        setUserStorage(SUBMODE_STORAGE_KEY, submode);
        if (!wasIncome && isIncomeView()) incomeOpeningPending = true;
    }
    // Named for the zoom it drives, NOT for a submode: it began life income-only, but
    // the mechanism was always the shared visible range. Deliberately "zoom" and not
    // "window" alone, to keep it distinct from the candle-WIDTH ladder (DBT-7), which
    // is a different control answering a different question.
    /**
     * Candle-width ladder — which calendar period one OHLC body, or one group of Income bars,
     * covers.
     *
     * This is NOT a time window: the x axis always shows the whole available history and
     * only the number of bodies changes. It was previously implemented as a visible-range
     * selector and renamed `zoom*` to match, which made the wrong reading look like
     * established vocabulary; the developer's original wording was "non rappresentano il
     * tempo da mostrare, ma la larghezza in giorni, che una candela copre".
     *
     * Each rung is a calendar period (developer's decision of 06/10/2026, replacing D16-ii's
     * plain day counts): `1W` runs Monday to Sunday, `1M` from the 1st, `3M`, `6M` and `1Y` are
     * quarters, halves and years, and `3D` and `2W` are fixed blocks whose edges never move.
     * The periods are `growthLadderBuckets`'s.
     */
    const CANDLE_WIDTH_ORDER: CandleWidth[] = ['1D', '3D', '1W', '2W', '1M', '3M', '6M', '1Y'];
    /**
     * Rung captions are localized: the unit letter is NOT part of the key.
     *
     * `1W` is English shorthand — French writes `1S` (semaine), and the project already
     * ships those letters in `datePicker.granularity.*Short`, used by the date picker's
     * own custom-duration editor. Reusing them keeps one vocabulary for "a week" across
     * the app instead of two that agree only in English.
     */
    const CANDLE_WIDTH_UNIT: Record<CandleWidth, 'days' | 'weeks' | 'months' | 'years'> = {
        '1D': 'days',
        '3D': 'days',
        '1W': 'weeks',
        '2W': 'weeks',
        '1M': 'months',
        '3M': 'months',
        '6M': 'months',
        '1Y': 'years',
    };
    /**
     * Unit letter for a rung, resolved through four LITERAL translation calls.
     *
     * A key assembled from a template literal works at runtime and is invisible to the
     * project's own i18n sweep, which extracts literal arguments and
     * then checks that every referenced key resolves in all four locales. A key built at
     * runtime is never extracted, so it is never checked: the four keys happened to exist
     * everywhere, but nothing would have said so if one had not.
     *
     * Verbose on purpose. The guarantee is worth more than the four lines.
     */
    function candleWidthUnit(w: CandleWidth): string {
        const unit = CANDLE_WIDTH_UNIT[w];
        if (unit === 'days') return $_('datePicker.granularity.daysShort');
        if (unit === 'weeks') return $_('datePicker.granularity.weeksShort');
        if (unit === 'months') return $_('datePicker.granularity.monthsShort');
        return $_('datePicker.granularity.yearsShort');
    }
    const candleWidthLabel = (w: CandleWidth) => `${w.slice(0, -1)}${candleWidthUnit(w)}`;
    /** Income bars start one rung up: a single day of personal cash flow is almost always empty. */
    const INCOME_MIN_WIDTH: CandleWidth = '1W';
    /**
     * The rung Income opens on, on every entry into it (developer, 05/10/2026: «facciamo che
     * il bucket di default è 1M»): a month of personal cash flow reads, a week is mostly
     * empty. When the geometry cannot draw it, Income opens on the offered rung nearest to
     * it. Candles keep their own opening, the finest rung they can draw.
     */
    const INCOME_OPENING_WIDTH: CandleWidth = '1M';
    /**
     * Narrowest candle body the ladder will still OFFER.
     *
     * Deliberately NOT `CANDLE_MIN_SLOT_PX`, and the difference is the point. That
     * constant governs *silent* aggregation: there a body too thin to read is a
     * deception, because the chart changed the bucket without saying so, so it is set
     * generously at 8px. Here the user picks the width on a labelled control and can see
     * the result — a dense chart is then a legitimate choice, not a lie, and the rule
     * only has to stop offering what cannot be drawn at all.
     *
     * Calibrated on the developer's expectation that 1D still be available at a 6-month
     * range: 180 days across a ~527px plot is 2.93px per body, so the threshold has to
     * sit below that. 2.5 keeps 1D up to ~210 days and leaves room for narrower plots.
     */
    const LADDER_MIN_BODY_PX = 2.5;
    /**
     * Narrowest Income bar the ladder will still offer — a bucket of 20.6 px with the Income gaps
     * (`INCOME_BAR_SHARE`, declared with the series in `growthChartSeries.ts`).
     *
     * Set by the developer's target of 06/10/2026: at nine months on a desktop, 2W is the
     * finest width («a 9 mesi, 2S mi paiono strette ma sono più accettabili»). Measured plots:
     * 484, 573 and 734 px at 1280, 1440 and 1728 px windows, 279 px on a 390 px phone; at nine
     * months 1W makes 40 buckets there (12–18 px each), 2W 21 (23–35 px).
     */
    const INCOME_MIN_BAR_PX = 4.5;
    /** Below three bodies a "chart" is a couple of rectangles — except at 1D, which is exempt. */
    const LADDER_MIN_BODIES = 3;
    let candleWidth: CandleWidth = $state('1W');
    /** True until the ladder has picked its own opening rung; see reconcileCandleWidth(). */
    let candleWidthPending = $state(true);
    /** Set on every entry into Income — mounting on a restored Income, or switching into it —
     *  and consumed by reconcileCandleWidth(), so a redraw inside Income keeps the user's pick. */
    let incomeOpeningPending = restoredMode === 'pnl' && restoredSubmode === 'income';
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
    /** Privacy state the axis labels were last drawn with. ECharts caches axis labels, so a
     *  toggle needs a full rebuild; the tooltip formatter reads the state on every hover. */
    let lastRenderedMasked: boolean | null = null;
    /** Names of the series last drawn, in order. A broker that joins, leaves or is swapped
     *  under the P&L line changes this list, which the partial path cannot express: it sends
     *  `{name, data}` only, and ECharts would keep the old series and legend entries. */
    let lastRenderedSeriesKey: string | null = null;
    let lastHistoryRef: PortfolioHistoryPoint[] | null = null;
    /**
     * First|last day of the data currently on screen.
     *
     * Tracked separately from `lastHistoryRef` because the two answer different
     * questions: the reference says "is this a new array", the domain says "is this a
     * different PERIOD". Preserving the user's zoom is right for the first and wrong for
     * the second — see the reset below.
     */
    let lastDomainKey: string | null = null;
    let lastSyncedGrammar: ChartGrammar | null = null;
    let responsiveXAxisCompact = false;
    /** The grid's right edge on screen: the time-axis inset that keeps the last label whole (plan 52), or the '4%' base. */
    let appliedGridRight: number | string = '4%';
    const resizeWatcher = createResizeWatcher(() => {
        chartInstance?.resize();
        if (chartContainer) containerWidthPx = chartContainer.clientWidth;
        syncPlotGeometry();
        // The ladder's axis is planned from the measured grid, by the resolution sync
        // below; the responsive policy is for the cascade's time axis only.
        if (chartInstance && chartContainer && activeChartData && !ladderActive) {
            const policy = buildResponsiveXAxisPolicy({
                width: chartContainer.clientWidth,
                values: activeChartData.dates,
                locale: uiLocale(),
                axisType: 'time',
            });
            const wasCompact = responsiveXAxisCompact;
            responsiveXAxisCompact = policy.compact;
            if (policy.axisLabel) {
                chartInstance.setOption({xAxis: {splitNumber: policy.splitNumber, axisLabel: policy.axisLabel}}, {lazyUpdate: true});
            } else if (wasCompact) {
                renderChart(true);
            }
            // The '4%' base stands for other pixels at another width, so the inset may change with it.
            const gridRight = timeAxisGridRight({
                width: chartContainer.clientWidth,
                values: activeChartData.dates,
                locale: uiLocale(),
                base: '4%',
                measure: axisLabelMeasure(chartInstance, 14),
            });
            if (gridRight !== appliedGridRight) {
                appliedGridRight = gridRight;
                // Not lazy: syncPlotGeometry() reads the grid this call lays out.
                chartInstance.setOption({grid: {right: gridRight}});
                syncPlotGeometry();
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

    /**
     * Candles need a far wider bucket slot than a line to stay legible, so the resolution
     * cascade is asked a grammar-specific question. Only the submode decides this — the
     * bucketing itself is identical for every grammar.
     */
    const resolutionGrammar: ChartGrammar = $derived.by(() => (viewMode === 'pnl' && pnlSubmode === 'candles' ? 'candle' : 'line'));

    /** True while a P&L submode that is driven by the ladder is on screen. */
    const ladderActive = $derived.by(() => viewMode === 'pnl' && (pnlSubmode === 'candles' || pnlSubmode === 'income'));

    /**
     * Which rungs the current geometry can actually draw.
     *
     * Two rules, deliberately asymmetric:
     *   (1) DENSITY  — a candle body must be at least LADDER_MIN_BODY_PX wide; in Income,
     *                  each of the bucket's three bars must be at least INCOME_MIN_BAR_PX
     *                  wide. Applies to every rung, 1D included, and 1D is the first to
     *                  fall because it is the densest.
     *   (2) SCARCITY — a rung needs at least LADDER_MIN_BODIES bodies to be a chart rather
     *                  than a couple of rectangles. 1D is EXEMPT: "deve sempre essere
     *                  possibile, anche se ci fosse solo 1 punto".
     *
     * The density half reuses `computeDensity` from the shared module — the same
     * bucket/px arithmetic the line charts have always used. What changed is not the
     * calculation but what is done with its result: it used to silently pick a
     * resolution while the label kept saying something else, and now it decides which
     * labels exist at all. A control that aggregates behind its own caption is a control
     * that lies; one that removes the option it cannot honour does not.
     */
    const availableCandleWidths = $derived.by(() => {
        const dayCount = dates.length;
        const plotPx = plotWidthPxMeasured;
        const income = ladderActive && pnlSubmode === 'income';
        const floor = income ? CANDLE_WIDTH_ORDER.indexOf(INCOME_MIN_WIDTH) : 0;
        if (dayCount === 0 || plotPx <= 0) return CANDLE_WIDTH_ORDER.slice(floor);

        const offered = CANDLE_WIDTH_ORDER.slice(floor).filter((width) => {
            // The buckets the ladder will actually draw: calendar periods, so the offer and the
            // drawing count the same thing.
            const bodies = countCalendarBuckets(dates, width);
            const density = computeDensity(bodies, plotPx);
            if (!(density > 0)) return false;
            const slotPx = 1 / density;
            const drawable = income ? slotPx * INCOME_BAR_SHARE >= INCOME_MIN_BAR_PX : slotPx >= LADDER_MIN_BODY_PX;
            if (!drawable) return false;
            return width === '1D' || bodies >= LADDER_MIN_BODIES;
        });

        // The list may never be empty: the floor rung stays offered even when nothing fits.
        return offered.length > 0 ? offered : [CANDLE_WIDTH_ORDER[floor]];
    });

    const resolutionCache = new Map<ChartResolution, {inputs: AggregationInputs; data: AggregatedResolutionData}>();
    /**
     * Same identity-keyed memo as resolutionCache, for the ladder branch — keyed on the day as
     * well, because which period is still in progress depends on it: a page left open past
     * midnight must not keep yesterday's current period.
     */
    const ladderCache = new Map<CandleWidth, {inputs: AggregationInputs; today: string; data: AggregatedResolutionData}>();
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
    /**
     * Fallback for the plot's left edge, used only until ECharts has laid the grid out once.
     *
     * The grid itself does not use it: `grid.left` is `'3%'` with `containLabel: true`, so
     * ECharts draws the y tick labels inside that inset and the real plot starts at
     * `3% of the width + the widest label`. That edge is measured from the laid-out grid
     * into `plotLeftPx` below, and the overlays follow the measurement. A px constant used
     * to be the grid's `left` as well; once the overlays measured, it only left an empty
     * gutter before the labels (developer review, on mobile).
     */
    const PLOT_LEFT_FALLBACK_PX = 52;
    /** Measured left edge of the plotting rectangle; see syncPlotGeometry(). */
    let plotLeftPx = $state(PLOT_LEFT_FALLBACK_PX);
    /** Measured width of the plotting rectangle; drives the candle-width availability rule. */
    let plotWidthPxMeasured = $state(0);
    /** Measured room between the plot's right edge and the canvas edge: how far the ladder's
     *  last label may reach before the canvas clips it. Read only by the axis planner. */
    let plotRightRoomPx = 0;
    /**
     * Measured TOP of the plotting rectangle — where the highest y-axis label sits.
     *
     * The overlays used to start at the top of the canvas, which put them a few pixels
     * below that label: mathematically adjacent, visually unaligned. Centring them on the
     * measured grid top lines them up with the label a reader actually compares them to.
     */
    let plotTopPx = $state(0);
    /**
     * Width of the chart container, measured by the existing ResizeObserver.
     *
     * The control labels used to collapse on a `sm:` Tailwind breakpoint, i.e. on the
     * VIEWPORT. That is the wrong quantity: a narrow chart inside a wide window kept its
     * labels and overflowed. What decides whether a label fits is the width of the box it
     * sits in, so the box is what gets measured.
     */
    let containerWidthPx = $state(0);
    const CONTROLS_COMPACT_BELOW_PX = 640;
    const controlsCompact = $derived.by(() => containerWidthPx > 0 && containerWidthPx < CONTROLS_COMPACT_BELOW_PX);
    const CHART_FULL_UPDATE_OPTS = {...CHART_SET_OPTION_OPTS, replaceMerge: [...CHART_SET_OPTION_OPTS.replaceMerge, 'xAxis']};

    // =========================================================================
    // Derived data for chart
    // =========================================================================

    const dates = $derived(history.map((pt) => pt.date));

    // EUR mode: the Capital Baseline narrative (stacked book value, NAV and baseline); see `mapEurStackedData`.
    const eurStackedData = $derived(mapEurStackedData(history));

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
        // R11: the purchase value, the KPI card's own key, names both acquisition zones;
        // the two labels above stay for the tooltip rows of its halves.
        bookValue: $_('dashboard.bookValue'),
    });

    /** P&L mode broker overlay (G1a): one line per broker, aligned to `dates`; see `mapBrokerPnlSeries`. */
    const pnlBrokerSeriesRaw = $derived(mapBrokerPnlSeries(brokerPnlHistory, dates));

    /** P&L candles submode (G1b): per-date OHLC lookup; a date absent from it is a genuine gap, never guessed. */
    const pnlCandleByDate = $derived(mapCandlesByDate(pnlCandles));

    /** P&L income submode (G1c): signed dividend/interest values aligned to `dates`.
     *  A date absent from incomeHistory.points means no DIVIDEND/INTEREST that day —
     *  rendered as 0 (a sparse-flow series, distinct from candle "gap" semantics). */
    const dividendValues = $derived(alignFlowToDates(dates, incomeHistory?.points ?? [], (p) => Number(p.dividend.amount)));
    const interestValues = $derived(alignFlowToDates(dates, incomeHistory?.points ?? [], (p) => Number(p.interest.amount)));

    /** Batch 2 income-submode dimensions: costs (FEE+TAX, signed/negative), deposits
     *  (fresh external cash), and the new-vs-reinvested BUY funding split. Same sparse
     *  "absent date -> 0" semantics as dividend/interest above. */
    const costValues = $derived(alignFlowToDates(dates, costHistory?.points ?? [], (p) => Number(p.cost.amount)));
    const depositValues = $derived(alignFlowToDates(dates, depositHistory?.points ?? [], (p) => Number(p.deposit.amount)));
    const acqFromNewCapitalValues = $derived(alignFlowToDates(dates, acquisitionFunding?.points ?? [], (p) => Number(p.from_new_capital.amount)));
    const acqFromReinvestedValues = $derived(alignFlowToDates(dates, acquisitionFunding?.points ?? [], (p) => Number(p.from_reinvested.amount)));

    // Values are split from labels deliberately: the aggregation memo reads ONLY these,
    // so a language switch rebuilds `pctSeriesRaw` (names) without invalidating the cache.
    const pctValuesRaw = $derived(mapPctValues(history));

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
     * The COMPLETE set of reactive values an aggregation is allowed to read.
     *
     * This exists to make cache invalidation correct *by construction* rather than by a
     * hand-maintained list somebody must remember to join. Because it is `$derived`, Svelte
     * rebuilds this object — giving it a fresh identity — whenever any member changes; and
     * because the aggregations (`buildResolutionData`, `buildLadderData`) receive their inputs
     * ONLY from here, a new input physically cannot be consumed without first becoming a
     * member, which automatically enrols it in invalidation. Adding a field (here and in
     * `AggregationInputs`) is the whole ceremony.
     *
     * The bug this replaces (G1b): seven inputs woke the render effect while exactly ONE
     * (`history`) cleared `resolutionCache`, whose key spanned only `resolution`. A lazily
     * arriving prop (`pnlCandles`) therefore re-rendered against an entry computed before
     * its data existed — every candle a `'-'` gap, forever, surviving re-entry.
     *
     * Deliberately EXCLUDED, and the exclusion matters: `eurLabels`, `pnlLabels`, `uiLocale()`
     * and `baseCurrency`. They are in the render effect's dependency list (labels must
     * re-render on a language switch) but the aggregation never reads them — only
     * `pctValuesRaw`, which is split from the labels for exactly this reason. Invalidating on them would trade a
     * silent-wrong bug for a silent-slow one, discarding a memo that exists for a reason.
     */
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

    // The % button is disabled without % data, so a % view must not outlive a completed load that has none — a %
    // view restored from storage, or one the user picked before switching to a period or a broker without %
    // (I-03). It falls back to Abs for display only: the stored choice is kept, and the view returns to % once
    // a loaded history can draw it again, unless the user has picked another mode meanwhile (`selectMode`).
    $effect(() => {
        if (loading) return;
        if (viewMode === 'pct' && !hasPctData) {
            viewMode = 'eur';
            pctFallback = true;
        } else if (pctFallback && hasPctData) {
            pctFallback = false;
            viewMode = 'pct';
        }
    });

    function resetResolutionState(preservedRange: GrowthLogicalRange | null = null) {
        resolutionCache.clear();
        ladderCache.clear();
        lastSyncedGrammar = null;
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

    function getResolutionData(resolution: ChartResolution): AggregatedResolutionData {
        // Identity check, not an equality list: `aggregationInputs` is rebuilt by Svelte
        // whenever any input changes, so a stale entry cannot be returned by construction.
        const inputs = aggregationInputs;
        const cached = resolutionCache.get(resolution);
        if (cached && cached.inputs === inputs) return cached.data;

        const entry = buildResolutionData(inputs, resolution);
        resolutionCache.set(resolution, {inputs, data: entry});
        return entry;
    }

    /**
     * Ladder branch of the same memo: identical shape, identical invalidation discipline
     * (identity of `aggregationInputs`), different bucket builder (`buildLadderData`).
     */
    function getLadderData(width: CandleWidth): AggregatedResolutionData {
        const inputs = aggregationInputs;
        const today = todayIso();
        const cached = ladderCache.get(width);
        if (cached && cached.inputs === inputs && cached.today === today) return cached.data;

        const entry = buildLadderData(inputs, width, today);
        ladderCache.set(width, {inputs, today, data: entry});
        return entry;
    }

    /** The aggregation the current mode should render: ladder for candles/income, density
     *  cascade for everything else. One entry point, so callers never choose. */
    function getActiveAggregation(): AggregatedResolutionData {
        return ladderActive ? getLadderData(candleWidth) : getResolutionData(currentResolution);
    }

    function computeBucketCounts(startDate: string, endDate: string): {dailyCount: number; weeklyCount: number; monthlyCount: number} {
        return countBuckets(dates, startDate, endDate);
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
        const entry = activeChartData;
        // A cascade entry is only readable at the resolution it was built for; a ladder
        // entry carries its own buckets, whatever the cascade's resolution says.
        if (!entry || (!entry.ladder && entry.resolution !== currentResolution)) return null;
        if (entry.buckets.length === 0) return null;

        const {start, end} = getZoomPercent();
        // Each window is read the way its axis draws it: the ladder's categories by index,
        // the cascade's time axis in time.
        const {startIndex, endIndex} = entry.ladder ? ladderIndicesAt(entry, start, end) : cascadeIndicesAt(entry, start, end);
        const startBucket = entry.buckets[startIndex];
        const endBucket = entry.buckets[endIndex];

        return {
            startDate: startBucket.bucketStart,
            endDate: endBucket.bucketEnd,
        };
    }

    /** Key of the ladder axis plan on screen; null while none is (fresh instance, cascade option). */
    let lastLadderPlanKey: string | null = null;

    /**
     * Painted width of a ladder axis label: the axis' 14 px, in the chart's font family.
     *
     * WHY lazy: the family is read from the chart model at the first measure of a plan (there is
     * no model before the first option, and then nothing to measure), and `echarts.format` only
     * inside the call, so a test that mocks ECharts without it still mounts the chart.
     */
    function ladderLabelMeasure(): (text: string) => number {
        let font: string | undefined;
        return (text) => {
            if (font === undefined) {
                const family = (chartInstance as unknown as {getModel?: () => {get?: (path: string[]) => unknown} | undefined} | undefined)?.getModel?.()?.get?.(['textStyle', 'fontFamily']);
                font = `14px ${typeof family === 'string' && family !== '' ? family : 'sans-serif'}`;
            }
            return echarts.format.getTextRect(text, font).width;
        };
    }

    /**
     * The ladder axis plan for `entry` seen through `zoom`, on the grid measured last.
     *
     * The window is passed in, not read from the chart: a render plans the window it is
     * about to send, which the chart does not hold yet. The planner rounds the fractional
     * indices the way ECharts snaps a category window, and returns an empty plan (key '')
     * while the grid is not measured.
     */
    function planLadderFor(entry: AggregatedResolutionData, zoom: {start: number; end: number}): LadderAxisPlan {
        const last = Math.max(entry.buckets.length - 1, 0);
        return planLadderAxis({
            closingDates: entry.dates,
            firstDate: entry.buckets[0]?.bucketStart ?? '',
            visibleStartIndex: (zoom.start / 100) * last,
            visibleEndIndex: (zoom.end / 100) * last,
            plotWidthPx: plotWidthPxMeasured,
            leftRoomPx: plotLeftPx,
            rightRoomPx: plotRightRoomPx,
            locale: uiLocale(),
            rung: entry.rung ?? candleWidth,
            quarterLabel: (quarter) => $_('dashboard.pnlAxisQuarter', {values: {quarter}}),
            labelWithYear: (label, year) => $_('dashboard.pnlAxisWithYear', {values: {label, year}}),
            measureLabelPx: ladderLabelMeasure(),
        });
    }

    /**
     * Re-plan the ladder axis for the window on screen, and send it only when the plan
     * changed — as an `{xAxis}`-only option. A zoom calls this, so the update must not
     * carry `dataZoom` (it would fight the gesture) nor series (nothing moved).
     */
    function refreshLadderAxis(zoom: {start: number; end: number} = getZoomPercent()) {
        const entry = activeChartData;
        if (!chartInstance || !ladderActive || !entry?.ladder) return;
        const plan = planLadderFor(entry, zoom);
        if (plan.key === lastLadderPlanKey) return;
        lastLadderPlanKey = plan.key;
        chartInstance.setOption({xAxis: ladderAxisOption(plan)});
    }

    /**
     * Pick a candle width. This does NOT move the visible range: the window stays on the
     * same days and only the number of bodies changes, which is the entire point of the
     * control and the opposite of what it used to do.
     */
    function selectCandleWidth(width: CandleWidth) {
        if (!availableCandleWidths.includes(width)) return;
        candleWidth = width;
        candleWidthPending = false;
        renderChart();
    }

    /**
     * Keep the selection honest when the geometry moves.
     *
     * On narrowing the chart, the current rung can stop being drawable. The developer's
     * rule is to climb — and with eight rungs the climb is ONE step, not a jump to the
     * first valid rung: the smallest move that restores a drawable chart is also the one
     * that preserves most of what the user asked for.
     */
    function reconcileCandleWidth() {
        const offered = availableCandleWidths;
        if (offered.length === 0) return;

        // Income opens on its own rung on every entry (INCOME_OPENING_WIDTH), or on the
        // offered rung nearest to it. The width is then shared with Candles, as before.
        if (incomeOpeningPending && isIncomeView()) {
            candleWidth = nearestOfferedWidth(offered, INCOME_OPENING_WIDTH);
            incomeOpeningPending = false;
            candleWidthPending = false;
            return;
        }

        // Opening pick: the LOWEST drawable rung — the finest detail the geometry can
        // honour. Same convention the line charts already use for their initial
        // resolution, so the two controls do not teach the user two different habits.
        if (candleWidthPending) {
            candleWidth = offered[0];
            candleWidthPending = false;
            return;
        }

        if (offered.includes(candleWidth)) return;
        const current = CANDLE_WIDTH_ORDER.indexOf(candleWidth);
        const next = CANDLE_WIDTH_ORDER.find((w, i) => i > current && offered.includes(w));
        candleWidth = next ?? offered[offered.length - 1];
    }

    /** The offered rung nearest to `target`: `target` itself when offered. The offer is contiguous, so this is a clamp. */
    function nearestOfferedWidth(offered: readonly CandleWidth[], target: CandleWidth): CandleWidth {
        if (offered.includes(target)) return target;
        const at = CANDLE_WIDTH_ORDER.indexOf(target);
        const distance = (width: CandleWidth) => Math.abs(CANDLE_WIDTH_ORDER.indexOf(width) - at);
        return offered.reduce((best, width) => (distance(width) < distance(best) ? width : best));
    }

    /** The view on screen, read now: what the series are built for. */
    function seriesContext(): GrowthSeriesContext {
        return {viewMode, pnlSubmode, eurLabels, pnlLabels, pctSeries, aggregationInputs};
    }

    function buildChartUpdateSeries(_isDark: boolean, entry: AggregatedResolutionData, referenceDate: string | null = null): GrowthSeriesData[] {
        return buildGrowthUpdateSeries(seriesContext(), entry, referenceDate);
    }

    function buildFullSeries(isDark: boolean, seriesData: GrowthSeriesData[]): echarts.SeriesOption[] {
        return buildGrowthFullSeries(seriesContext(), isDark, seriesData);
    }

    /**
     * What the tooltip reads on hover: the entry and the view on screen at that moment, as the
     * formatter always has. The theme it is drawn in is the one the option was built with.
     */
    function tooltipView(): Omit<GrowthTooltipView, 'isDark' | 'theme'> {
        return {entry: activeChartData, viewMode, pnlSubmode, ladderActive, candleWidthCaption: () => candleWidthLabel(candleWidth), eurLabels, pnlLabels, baseCurrency, t: $_};
    }

    function updateChartData(entry: AggregatedResolutionData, isDark: boolean, zoomWindow: {start: number; end: number}, skipAnimation: boolean, referenceDate: string | null = null) {
        if (!chartInstance) return;

        const seriesData = buildChartUpdateSeries(isDark, entry, referenceDate);

        // skipAnimation is only ever true for a resolution switch (daily <-> weekly/monthly),
        // where the data-point count per series changes drastically. If a tooltip is
        // currently showing (user hovering while zooming — the exact gesture that triggers
        // a resolution switch), ECharts can crash inside its internal _showAxisTooltip
        // reading stale series/dataIndex references once series are replaced via
        // replaceMerge. Hiding the tooltip first clears that internal state safely.
        if (skipAnimation) {
            chartInstance.dispatchAction({type: 'hideTip'});
        }

        let xAxis: Record<string, unknown>;
        let gridRight: number | string | undefined;
        if (entry.ladder) {
            // A category axis takes its positions from `data` alone, so the bucket closings
            // travel with every update: a rung change replaces all of them. The labels are
            // planned for the window this update sends, not for the one on screen.
            const plan = planLadderFor(entry, zoomWindow);
            lastLadderPlanKey = plan.key;
            xAxis = {data: entry.dates, ...ladderAxisOption(plan)};
        } else {
            const xAxisPolicy = buildResponsiveXAxisPolicy({
                width: chartContainer?.clientWidth ?? 0,
                values: entry.dates,
                locale: uiLocale(),
                axisType: 'time',
            });
            if (responsiveXAxisCompact && !xAxisPolicy.compact) {
                applyFullOption(isDark, buildFullSeries(isDark, seriesData), zoomWindow);
                return;
            }
            responsiveXAxisCompact = xAxisPolicy.compact;
            xAxis = xAxisPolicy.compact ? {splitNumber: xAxisPolicy.splitNumber, axisLabel: xAxisPolicy.axisLabel} : {axisLabel: {formatter: xAxisPolicy.formatter}};
            gridRight = timeAxisGridRight({
                width: chartContainer?.clientWidth ?? 0,
                values: entry.dates,
                locale: uiLocale(),
                base: '4%',
                measure: axisLabelMeasure(chartInstance, 14),
            });
            appliedGridRight = gridRight;
        }

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
                // New dates are new labels: the inset travels with the axis they are drawn on.
                ...(gridRight === undefined ? {} : {grid: {right: gridRight}}),
                xAxis,
                series,
            },
            CHART_SERIES_UPDATE_OPTS,
        );
        // The partial path also relays out the grid — new values can widen the y-axis
        // labels and with them the gutter — so the overlay geometry must be re-read here
        // too, not only after a full build. The ladder's labels were planned on the old
        // grid, so they are planned again on the new one; the call sends nothing when the
        // plan did not change.
        syncPlotGeometry();
        if (entry.ladder) refreshLadderAxis(zoomWindow);
    }

    function syncResolutionToViewport() {
        if (!chartInstance || history.length === 0) return;

        const logicalRange = getLogicalRangeFromChart() ?? ensureLogicalRange();
        if (!logicalRange) return;

        visibleStartDate = logicalRange.startDate;
        visibleEndDate = logicalRange.endDate;

        // Under the ladder the user owns the bucket width, so a zoom never changes it: only
        // the axis labels are planned again, for the new window. A resize can still take
        // the pressed rung out of the offer — the first measurement after an unmeasured
        // first paint does exactly that — and then the chart is rebuilt at the rung
        // reconcileCandleWidth() picks.
        if (ladderActive) {
            if (availableCandleWidths.includes(candleWidth)) refreshLadderAxis();
            else renderChart();
            return;
        }

        const counts = computeBucketCounts(logicalRange.startDate, logicalRange.endDate);
        const plotWidthPx = chartInstance.getWidth();
        const targetResolution = cascadeResolution(currentResolution, counts, plotWidthPx, resolutionGrammar);

        if (targetResolution === currentResolution) return;

        currentResolution = targetResolution;
        const entry = getResolutionData(targetResolution);
        const isDark = isDarkTheme();
        const zoomWindow = buildZoomWindow(entry, logicalRange.startDate, logicalRange.endDate);

        activeChartData = entry;
        updateChartData(entry, isDark, zoomWindow, true, logicalRange.startDate);
    }

    /**
     * Read the laid-out grid rectangle back from ECharts and publish its left edge and
     * width, so the floating overlays align with the PLOT instead of with an assumption
     * about how wide the tick labels are.
     *
     * Measuring beats computing here: with `containLabel: true` the gutter is derived
     * from the widest rendered label, which depends on the formatter, the font, the
     * locale and the data — every one of which can change without this file changing.
     */
    function syncPlotGeometry() {
        if (!chartInstance) return;
        const rect = (chartInstance as unknown as {getModel?: () => {getComponent?: (t: string) => {coordinateSystem?: {getRect?: () => {x: number; y: number; width: number}}} | undefined}}).getModel?.()?.getComponent?.('grid')?.coordinateSystem?.getRect?.();
        if (!rect || !Number.isFinite(rect.x) || !Number.isFinite(rect.width)) return;
        plotLeftPx = Math.round(rect.x);
        plotWidthPxMeasured = Math.round(rect.width);
        plotRightRoomPx = Math.max(0, Math.round(chartInstance.getWidth() - rect.x - rect.width));
        if (Number.isFinite(rect.y)) plotTopPx = Math.round(rect.y);
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
        darkModeObserver = onThemeClassChange(() => renderChart());
        // C4: a Designer Lab edit of a category colour rebuilds the whole option, the broker lines included (TD-1b).
        const chartColours = onChartColorsChange(() => renderChart(true));

        return () => {
            if (resolutionDebounceTimer) clearTimeout(resolutionDebounceTimer);
            dataZoomCleanup?.();
            tooltipCleanup?.();
            darkModeObserver?.disconnect();
            chartColours.disconnect();
            resizeWatcher.disconnect();
            dataZoomTouchPanHandle?.dispose();
            dataZoomTouchPanHandle = null;
            if (chartInstance) delete (chartInstance.getDom() as unknown as Record<string, unknown>).__lfChart;
            chartInstance?.dispose();
            lastLadderPlanKey = null;
        };
    });

    // G1b — lazy candle fetch: fire the request-callback once when the user activates the
    // candles submode and no data has arrived yet. Re-fires harmlessly if pnlCandles is
    // still null next time this effect runs (e.g. after a broker/date-range refetch reset
    // it) — the caller's own report cache makes a repeat request cheap.
    // The callback runs TRACKED on purpose (Y-16): what the caller reads synchronously inside
    // it becomes a dependency of this effect. The Dashboard's loader reads `canAsk` there, so a
    // saved Candles view on a fresh page asks again once the brokers are known; an `untrack`
    // around the call would leave it empty (pinned in e2e/portfolio/page-busy.spec.ts). After a failed
    // request the page's retry (`createLazyReportRetry`, Y-24) says when the loader may ask again — at most
    // three times, 2, 4 and 8 s later: its `canAsk`, read in the loader's guard, is what wakes this effect.
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
        void uiLocale();
        // Read here, not in renderChart: the render runs inside `tick().then`, where a read
        // registers no dependency, so the privacy toggle would not redraw the axis.
        void shouldMaskAmount();

        if (history !== lastHistoryRef) {
            // Keeping the visible window across a data refresh is a courtesy; keeping it
            // across a RANGE CHANGE is a bug. `clampGrowthLogicalRange` narrows a window
            // to the new domain but never widens it, so switching 3M -> 1Y left the old
            // three-month window sitting inside a one-year domain: no expansion, and the
            // user had to scroll to find the rest of their own data. The dashed reference
            // line, anchored to the first visible day, stayed on the old day for the same
            // reason.
            //
            // So the window is preserved only when the PERIOD is unchanged — a re-fetch,
            // a sync, a currency switch — and dropped when the period itself moved.
            const domainKey = dates.length > 0 ? `${dates[0]}|${dates[dates.length - 1]}` : '';
            const periodChanged = lastDomainKey !== null && domainKey !== lastDomainKey;
            const preservedRange = periodChanged ? null : getLogicalRangeFromChart();

            lastHistoryRef = history;
            lastDomainKey = domainKey;
            resetResolutionState(preservedRange);
        }

        if (chartContainer) {
            tick().then(() => {
                setupResizeObserver();
                renderChart();
                // Switching submode changes the grammar, and the grammar changes the
                // density threshold the cascade answers with — but nothing else on this
                // path re-runs the cascade (it fires only on dataZoom and resize). Without
                // this, entering the candles submode keeps the resolution chosen under the
                // line threshold and the candles stay unreadably narrow until the user
                // happens to zoom.
                if (resolutionGrammar !== lastSyncedGrammar) {
                    lastSyncedGrammar = resolutionGrammar;
                    syncResolutionToViewport();
                }
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
            delete (chartInstance.getDom() as unknown as Record<string, unknown>).__lfChart;
            chartInstance.dispose();
            chartInstance = undefined;
            lastRenderedMode = null;
            lastRenderedDark = null;
            lastRenderedMasked = null;
            lastRenderedSeriesKey = null;
            lastLadderPlanKey = null;
        }

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, CHART_INIT_THEME, chartInitOptions(chartContainer));
            attachChartReady(chartInstance, chartContainer, 'growth');
            // ECharts draws to a canvas, so an axis label or a bar has no DOM a test could
            // read. Exposing the instance is the only way to assert what reached the option
            // — same hook, same name, as PriceChartFull.svelte.
            (chartContainer as unknown as Record<string, unknown>).__lfChart = chartInstance;
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

        const isDark = isDarkTheme();
        const liveRange = getLogicalRangeFromChart();
        if (liveRange) {
            visibleStartDate = liveRange.startDate;
            visibleEndDate = liveRange.endDate;
        }
        const logicalRange = ensureLogicalRange();
        if (!logicalRange) return;

        if (resolutionResetPending) {
            const counts = computeBucketCounts(logicalRange.startDate, logicalRange.endDate);
            currentResolution = chooseInitialResolution(counts, chartInstance.getWidth(), resolutionGrammar);
            resolutionResetPending = false;
        }

        // The ladder owns Candles and Income; the density cascade still owns Value and %.
        // reconcile() runs first so a rung the geometry can no longer draw is climbed out
        // of BEFORE it is asked to produce buckets. The window is then placed on the
        // buckets of whichever grid is drawn, so a rung change, a privacy toggle or a new
        // locale keeps what the user was looking at.
        if (ladderActive) reconcileCandleWidth();
        const activeData = getActiveAggregation();
        const zoomWindow = buildZoomWindow(activeData, logicalRange.startDate, logicalRange.endDate);
        activeChartData = activeData;

        // Determine if this is a data-only update (same mode+submode, same dark) or full re-init
        const renderedModeKey = viewMode === 'pnl' ? `pnl:${pnlSubmode}` : viewMode;
        const masked = shouldMaskAmount();
        const seriesData = buildChartUpdateSeries(isDark, activeData, logicalRange.startDate);
        const seriesKey = seriesData.map((series) => series.name).join('\u0000');
        const needsFullInit = forceFullXAxisRebuild || lastRenderedMode !== renderedModeKey || lastRenderedDark !== isDark || lastRenderedMasked !== masked || lastRenderedSeriesKey !== seriesKey;

        if (needsFullInit) {
            applyFullOption(isDark, buildFullSeries(isDark, seriesData), zoomWindow);
        } else {
            updateChartData(activeData, isDark, zoomWindow, false, logicalRange.startDate);
        }

        lastRenderedMode = renderedModeKey;
        lastRenderedDark = isDark;
        lastRenderedMasked = masked;
        lastRenderedSeriesKey = seriesKey;
    }

    function applyFullOption(isDark: boolean, series: echarts.SeriesOption[], zoomWindow: {start: number; end: number}) {
        if (!chartInstance) return;
        const neutrals = chartNeutrals(isDark, chartContainer);
        const {bg: tooltipBg, border: tooltipBorder, textColor, mutedColor} = buildTooltipTheme(isDark, chartContainer);
        const gridColor = neutrals.dashboard.gridLine;
        /**
         * Bucket separators need their own colour. `gridColor` is tuned for horizontal
         * value lines, which run the full width and read even when very faint; a vertical
         * separator is a short stroke competing with the bars beside it, so at the same
         * tint it disappeared — in dark mode entirely (#1e293b is barely off the slate-800
         * background it is drawn on).
         */
        const bucketLineColor = neutrals.growth.bucketSeparator;
        // The ladder (Candles and Income) draws on a category axis: one slot per bucket,
        // so every bar and body gets the same width from the first render, whatever the
        // zoom. Its labels and separators come from the ladder plan, not from the shared
        // responsive policy, which only serves the time axis of the other modes. The zoom
        // pipeline (buildZoomWindow/getLogicalRangeFromChart) is index/percentage-based,
        // so it reads both axes the same way.
        const xAxisPolicy = ladderActive
            ? null
            : buildResponsiveXAxisPolicy({
                  width: chartContainer?.clientWidth ?? 0,
                  values: activeChartData?.dates ?? dates,
                  locale: uiLocale(),
                  axisType: 'time',
              });
        responsiveXAxisCompact = xAxisPolicy?.compact ?? false;
        // The time axis widens the right inset to keep its last label whole (plan 52); the
        // ladder's category axis ends each label at its slot and keeps the base.
        const gridRight = xAxisPolicy
            ? timeAxisGridRight({
                  width: chartContainer?.clientWidth ?? 0,
                  values: activeChartData?.dates ?? dates,
                  locale: uiLocale(),
                  base: '4%',
                  measure: axisLabelMeasure(chartInstance, 14),
              })
            : '4%';
        appliedGridRight = gridRight;
        // Planned for the window this option is about to send. Before the first layout
        // the grid is unmeasured and the plan is empty; refreshLadderAxis() below fills
        // it in as soon as syncPlotGeometry() has read the grid.
        const ladderPlan = ladderActive && activeChartData?.ladder ? planLadderFor(activeChartData, zoomWindow) : null;
        lastLadderPlanKey = ladderPlan?.key ?? null;
        const ladderAxis = ladderPlan ? ladderAxisOption(ladderPlan) : null;

        // Income draws bars, which stand on zero; every other view draws a line or candles.
        const incomeBars = viewMode === 'pnl' && pnlSubmode === 'income';

        const formatTick =
            viewMode === 'pct'
                ? (v: number) => formatPercent(v, {digits: 1, signed: false})
                : (v: number) => {
                      // D18: the scaled value prints exactly, so two ticks never share a label
                      // (`5.5k`, `1.25M`) and a whole one has no decimals (`2k`, `1M`). D23: the
                      // digits and the minus come from the locale; a negative zero prints `0`.
                      // D8: the sign stays outside the mask, the k/M suffix inside it: `•••k`
                      // would still disclose the order of magnitude.
                      const abs = Math.abs(v);
                      const [scale, suffix]: [number, string] = abs >= 1_000_000 ? [1_000_000, 'M'] : abs >= 1_000 ? [1_000, 'k'] : [1, ''];
                      const scaled = v === 0 ? 0 : v / scale;
                      return maskFormattedNumber(`${scaled.toLocaleString(uiLocale(), {maximumSignificantDigits: 15})}${suffix}`);
                  };
        // Tick 0 is the computed lower edge, which D25 hides with `showMinLabel: false`. But
        // `containLabel` still measures the hidden label, and D18 prints that raw edge in full
        // (`55,588k`), so the plot moved right by the width of a label nobody sees (developer
        // review, 05/10/2026: a left gap in Abs and P&L). Blank text measures nothing. Income
        // keeps its zero label: its axis starts at 0, which bars need to stand on.
        const yAxisFormatter = (v: number, index?: number) => (!incomeBars && index === 0 ? '' : formatTick(v));

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
            // `left: '3%'` is the OUTER inset: with `containLabel: true` ECharts draws the
            // y tick labels inside it, so the plot edge moves with the widest label (another
            // currency, a larger portfolio). The floating overlays never assume that edge;
            // they read it back after layout (syncPlotGeometry → plotLeftPx). A px constant
            // here, shared with the overlays, left an empty gutter before the labels.
            // `top` stays 10px in every mode: the toggle is an OVERLAY and must float on
            // the plot, not push it down (developer review — reserving a band shortened
            // the chart, which was never what was asked for).
            grid: {left: '3%', right: gridRight, bottom: '30px', top: '10px', containLabel: true},
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
                axisPointer: {type: 'line', lineStyle: {color: neutrals.axisPointer.line}},
                backgroundColor: tooltipBg,
                borderColor: tooltipBorder,
                borderWidth: 1,
                textStyle: {color: neutrals.tooltip.box.text, fontSize: 12},
                formatter: (params: any) => buildGrowthTooltip(params, {...tooltipView(), isDark, theme: {bg: tooltipBg, border: tooltipBorder, textColor, mutedColor}}),
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
            xAxis: ladderAxis
                ? {
                      type: 'category',
                      data: activeChartData?.dates ?? dates,
                      boundaryGap: true,
                      // `rotate` comes from the plan, always: 0, or 45 when one label does not fit. So do `width`
                      // and `lineHeight`, the box of a rotated label (undefined here: this render replaces the axis).
                      axisLabel: {color: textColor, fontSize: 14, ...ladderAxis.axisLabel, width: ladderAxis.axisLabel.width ?? undefined, lineHeight: ladderAxis.axisLabel.lineHeight ?? undefined},
                      axisLine: {lineStyle: {color: gridColor}},
                      // Bucket separators. With boundaryGap they fall BETWEEN categories,
                      // on the bucket boundaries, which is what makes a wide body read as
                      // one bucket. Which boundaries carry one is the plan's decision, not
                      // ECharts' `'auto'`, which follows the label interval and dropped
                      // separators wherever a label was skipped. Declared once, here: a
                      // later `splitLine` key in the same literal would silently win.
                      splitLine: {show: true, lineStyle: {color: bucketLineColor, type: 'dashed'}, interval: ladderAxis.splitLine.interval},
                  }
                : {
                      type: 'time',
                      ...(xAxisPolicy?.compact ? {splitNumber: xAxisPolicy.splitNumber} : {}),
                      axisLabel: {
                          color: textColor,
                          fontSize: 14,
                          rotate: 0,
                          formatter: xAxisPolicy?.formatter,
                          ...(xAxisPolicy?.axisLabel ?? {}),
                      },
                      axisLine: {lineStyle: {color: gridColor}},
                      splitLine: {show: false},
                  },
            yAxis: {
                type: 'value',
                // Lines and candles: a min function so the y-axis auto-scales rather than
                // forcing 0, which gives detail visibility when portfolio values are large.
                // ECharts labels that edge with its raw value, not a round tick, so the label
                // is hidden and the edge stays where it is (D25). Income keeps ECharts'
                // defaults: an axis that includes 0, like any bar chart. Its two keys stay
                // PRESENT as `undefined`: the full rebuild merges `yAxis` into the previous
                // option (CHART_FULL_UPDATE_OPTS replaces only `series` and `xAxis`), so an
                // omitted key would keep the line's min function and hidden label.
                min: incomeBars ? undefined : (value: {min: number; max: number}) => Math.floor(value.min - (value.max - value.min) * 0.08),
                axisLabel: {color: textColor, fontSize: 14, formatter: yAxisFormatter, showMinLabel: incomeBars ? undefined : false},
                axisLine: {show: false},
                splitLine: {lineStyle: {color: gridColor, type: 'dashed'}},
            },
            series,
        };

        chartInstance.setOption(option, CHART_FULL_UPDATE_OPTS);
        // The grid is laid out by setOption, so the plot rectangle only becomes readable
        // after it — never before.
        syncPlotGeometry();
        if (ladderAxis) refreshLadderAxis(zoomWindow);
        if (chartContainer) containerWidthPx = chartContainer.clientWidth;
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

<div class="bg-lf-card text-lf-primary rounded-xl border border-lf-subtle shadow-sm shadow-lf-shadow-card p-4 flex flex-col gap-3" data-testid="growth-chart">
    <!-- Header row: title + toggle -->
    <div class="flex items-center justify-between">
        <h2 class="text-sm font-semibold text-lf-secondary">{$_('dashboard.growth')}</h2>

        <!-- Abs / % / P&L segmented toggle -->
        <div class="flex rounded-lg overflow-hidden border border-lf-subtle text-xs font-medium">
            <button class="px-3 py-1 transition-colors {viewMode === 'eur' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}" onclick={() => selectMode('eur')} aria-pressed={viewMode === 'eur'} data-testid="growth-toggle-eur">
                {$_('dashboard.abs')}
            </button>
            <button
                class="px-3 py-1 transition-colors border-l border-lf-subtle {viewMode === 'pct' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'} {!hasPctData ? 'opacity-50 cursor-not-allowed' : ''}"
                onclick={() => hasPctData && selectMode('pct')}
                disabled={!hasPctData}
                title={!hasPctData ? $_('common.noData') : ''}
                aria-pressed={viewMode === 'pct'}
                data-testid="growth-toggle-pct"
            >
                {$_('dashboard.pct')}
            </button>
            <button class="px-3 py-1 transition-colors border-l border-lf-subtle {viewMode === 'pnl' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}" onclick={() => selectMode('pnl')} aria-pressed={viewMode === 'pnl'} data-testid="growth-toggle-pnl">
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
        <div class="absolute z-10 flex flex-wrap items-center gap-1.5" style="left: {plotLeftPx}px; top: {plotTopPx}px; transform: translateY(-50%)">
            {#if viewMode === 'pnl'}
                <!-- Icon + label. Below `sm` the label folds away and only the icon
                     remains (developer review), but the label text is NOT lost: it stays
                     reachable as `title`/`aria-label` on the button in BOTH states, so the
                     control remains usable with a screen reader exactly where it is
                     hardest to use. `data-testid` is deliberately identical across
                     breakpoints — a testid that changes with viewport would make every
                     E2E selector viewport-dependent. -->
                <div class="flex rounded-lg border border-lf-subtle/70 overflow-hidden shadow-sm opacity-75 hover:opacity-100 transition-opacity text-xs font-medium">
                    <button
                        class="{controlsCompact ? 'px-2' : 'px-3'} py-1 transition-colors inline-flex items-center gap-1.5 {pnlSubmode === 'line' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card/90 text-lf-muted hover:bg-lf-hover'}"
                        onclick={() => selectSubmode('line')}
                        title={$_('dashboard.pnlSubmodeLine')}
                        aria-label={$_('dashboard.pnlSubmodeLine')}
                        aria-pressed={pnlSubmode === 'line'}
                        data-testid="growth-pnl-submode-line"
                    >
                        <ChartLine size={14} aria-hidden="true" />
                        <span class={controlsCompact ? 'hidden' : 'inline'}>{$_('dashboard.pnlSubmodeLine')}</span>
                    </button>
                    <button
                        class="{controlsCompact ? 'px-2' : 'px-3'} py-1 transition-colors inline-flex items-center gap-1.5 border-l border-lf-subtle/70 {pnlSubmode === 'candles' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card/90 text-lf-muted hover:bg-lf-hover'}"
                        onclick={() => selectSubmode('candles')}
                        title={$_('dashboard.pnlSubmodeCandles')}
                        aria-label={$_('dashboard.pnlSubmodeCandles')}
                        aria-pressed={pnlSubmode === 'candles'}
                        data-testid="growth-pnl-submode-candles"
                    >
                        <ChartCandlestick size={14} aria-hidden="true" />
                        <span class={controlsCompact ? 'hidden' : 'inline'}>{$_('dashboard.pnlSubmodeCandles')}</span>
                    </button>
                    <button
                        class="{controlsCompact ? 'px-2' : 'px-3'} py-1 transition-colors inline-flex items-center gap-1.5 border-l border-lf-subtle/70 {pnlSubmode === 'income' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card/90 text-lf-muted hover:bg-lf-hover'}"
                        onclick={() => selectSubmode('income')}
                        title={$_('dashboard.pnlSubmodeIncome')}
                        aria-label={$_('dashboard.pnlSubmodeIncome')}
                        aria-pressed={pnlSubmode === 'income'}
                        data-testid="growth-pnl-submode-income"
                    >
                        <Coins size={14} aria-hidden="true" />
                        <span class={controlsCompact ? 'hidden' : 'inline'}>{$_('dashboard.pnlSubmodeIncome')}</span>
                    </button>
                </div>
            {/if}
            <div class="pointer-events-none">
                <!-- Hidden under the ladder: there the width is the user's explicit choice and the
                     selector already states it, so a second caption could only ever disagree.
                     The badge stays where the resolution is chosen FOR the user (Value / %). -->
                {#if !ladderActive}
                    <ResolutionBadge resolution={currentResolution} />
                {/if}
            </div>
        </div>
        {#if ladderActive}
            <!-- Candle-width ladder, top-RIGHT. Shown only where a body exists to widen:
                 Candles and Income. It selects HOW MANY DAYS one body covers — the axis
                 keeps showing the whole history — which is what the developer asked for
                 originally: "non rappresentano il tempo da mostrare, ma la larghezza in
                 giorni, che una candela copre".
                 This replaces a visible-range selector that had been built here by
                 mistake and then renamed `zoom*`, which made the wrong reading look like
                 settled vocabulary. The Line submode has no selector: a line has no body
                 whose width could change. -->
            <div class="absolute right-0 z-10 flex items-center gap-1.5" style="top: {plotTopPx}px; transform: translateY(-50%)">
                <div class="flex rounded-lg border border-lf-subtle/70 overflow-hidden shadow-sm opacity-75 hover:opacity-100 transition-opacity text-xs font-medium" data-testid="growth-candle-width">
                    <!-- One button per drawable rung. A rung that the current geometry
                         cannot render is REMOVED, not disabled: a disabled control still
                         claims the chart could show that width, which is the same lie the
                         old silent aggregation told. -->
                    {#each availableCandleWidths as width (width)}
                        <button
                            class="{controlsCompact ? 'px-2' : 'px-2.5'} py-1 transition-colors border-l border-lf-subtle/70 first:border-l-0 {candleWidth === width ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card/90 text-lf-muted hover:bg-lf-hover'}"
                            onclick={() => selectCandleWidth(width)}
                            aria-pressed={candleWidth === width}
                            data-testid="growth-candle-width-{width.toLowerCase()}">{candleWidthLabel(width)}</button
                        >
                    {/each}
                </div>
            </div>
        {/if}
        <!-- Skeleton / empty overlay -->
        {#if loading}
            <div class="absolute inset-0 z-10 bg-lf-panel rounded animate-pulse"></div>
        {:else if history.length === 0}
            <div class="absolute inset-0 z-10 flex items-center justify-center text-lf-muted text-sm">
                {$_('common.noData')}
            </div>
        {/if}
        <!-- Persistent chart container — never destroyed -->
        <div bind:this={chartContainer} style="height: 100%; width: 100%;" class:invisible={loading || history.length === 0}></div>
    </div>
    {#if !loading && history.length > 0 && viewMode === 'pct' && hasPctData && !hasNonZeroPctData}
        <p class="text-center text-xs text-lf-muted italic mt-1">
            {$_('dashboard.roiAllZero')}
        </p>
    {/if}
    {#if !loading && viewMode === 'pnl' && pnlSubmode === 'candles'}
        <!-- Mandatory always-visible synthetic-candle disclosure (plan §3.3): one line in the short
             register, scrolling instead of wrapping where it does not fit (R9). -->
        <p use:scrollOnOverflow class="{overflowScrollTextClass} text-center text-xs text-lf-muted italic mt-1" data-testid="growth-pnl-candles-hypothetical-label">{$_('dashboard.pnlCandlesHypotheticalShort')}</p>
    {/if}
</div>
