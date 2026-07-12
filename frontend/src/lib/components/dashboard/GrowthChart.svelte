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
    import {CHART_ANIMATION_CONFIG, CHART_SET_OPTION_OPTS, namedPoint} from '$lib/components/charts/echartsAnimationConfig';
    import {_, locale} from '$lib/i18n';
    import ResolutionBadge from '$lib/components/charts/ResolutionBadge.svelte';
    import {aggregateLineSeries, mapDateToBucket, cascadeResolution, chooseInitialResolution} from '$lib/components/charts/timeSeriesAggregation';
    import type {ChartResolution} from '$lib/components/charts/timeSeriesAggregation';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import type {PortfolioHistoryPoint} from '$lib/stores/portfolio/portfolioStore.svelte';
    import {buildTooltipTheme, buildTooltipHeader, buildTooltipRow, buildTooltipDivider, tooltipPositionSide, setupTooltipAutoHide, scheduleFirstRenderStabilityFix} from '$lib/components/charts/echartsTooltipHelpers';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        history: PortfolioHistoryPoint[];
        height?: string;
        loading?: boolean;
        baseCurrency?: string;
    }

    let {history = [], height = '360px', loading = false, baseCurrency = 'EUR'}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let viewMode: 'eur' | 'pct' = $state('eur');
    let currentResolution: ChartResolution = $state('daily');
    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | undefined = undefined;
    /** Tracks last viewMode used for full init — dark mode or viewMode switch requires full re-init */
    let lastRenderedMode: 'eur' | 'pct' | null = null;
    let lastRenderedDark: boolean | null = null;
    let lastHistoryRef: PortfolioHistoryPoint[] | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let observedContainer: HTMLDivElement | undefined = undefined;
    let darkModeObserver: MutationObserver | null = null;
    let visibleStartDate: string | null = null;
    let visibleEndDate: string | null = null;
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
    };

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

    interface AggregatedResolutionData {
        resolution: ChartResolution;
        dates: string[];
        buckets: BucketInfo[];
        eur: Record<EurSeriesKey, AggregatedMetric>;
        pct: Record<PctSeriesKey, AggregatedMetric>;
    }

    const resolutionCache = new Map<ChartResolution, AggregatedResolutionData>();
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

    const pctSeriesRaw = $derived([
        {
            key: 'mwrrCum' as const,
            name: $_('dashboard.mwrrCum'),
            values: history.map((pt) => (pt.mwrr_cumulative != null ? Number(pt.mwrr_cumulative) * 100 : null)),
            lineStyle: 'solid' as const,
            colorKey: 'nav' as const,
        },
        {
            key: 'twrr' as const,
            name: $_('dashboard.twrr'),
            values: history.map((pt) => (pt.twrr != null ? Number(pt.twrr) * 100 : null)),
            lineStyle: 'dashed' as const,
            colorKey: 'invested' as const,
        },
        {
            key: 'roi' as const,
            name: $_('dashboard.roi'),
            values: history.map((pt) => (pt.roi != null ? Number(pt.roi) * 100 : null)),
            lineStyle: 'dotted' as const,
            colorKey: 'pctCash' as const,
        },
    ]);
    // Filter out series with all-null data (e.g. MWRR when marked unreliable)
    const pctSeries = $derived(pctSeriesRaw.filter((s) => s.values.some((v) => v != null)));

    const hasPctData = $derived(history.some((pt) => pt.mwrr_cumulative != null || pt.twrr != null || pt.roi != null));
    const hasNonZeroPctData = $derived(history.some((pt) => Number(pt.mwrr_cumulative ?? 0) !== 0 || Number(pt.twrr ?? 0) !== 0 || Number(pt.roi ?? 0) !== 0));

    function resetResolutionState() {
        resolutionCache.clear();
        activeChartData = null;
        currentResolution = 'daily';
        visibleStartDate = null;
        visibleEndDate = null;
    }

    function ensureLogicalRange(): {startDate: string; endDate: string} | null {
        if (dates.length === 0) return null;
        visibleStartDate ??= dates[0];
        visibleEndDate ??= dates[dates.length - 1];
        return {startDate: visibleStartDate, endDate: visibleEndDate};
    }

    function buildBucketInfos(resolution: ChartResolution): BucketInfo[] {
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

    function getResolutionData(resolution: ChartResolution): AggregatedResolutionData {
        const cached = resolutionCache.get(resolution);
        if (cached) return cached;

        const buckets = buildBucketInfos(resolution);
        const entry: AggregatedResolutionData = {
            resolution,
            dates: buckets.map((bucket) => bucket.date),
            buckets,
            eur: {
                bookAssetLike: aggregateMetric(eurStackedData.bookAssetLike, resolution, buckets),
                cashContributed: aggregateMetric(eurStackedData.cashContributed, resolution, buckets),
                cashGenerated: aggregateMetric(eurStackedData.cashGenerated, resolution, buckets),
                nav: aggregateMetric(eurStackedData.nav, resolution, buckets),
                capitalBaseline: aggregateMetric(eurStackedData.capitalBaseline, resolution, buckets),
                totalPnl: aggregateMetric(eurStackedData.totalPnl, resolution, buckets),
            },
            pct: {
                mwrrCum: aggregateMetric(pctSeriesRaw[0].values, resolution, buckets),
                twrr: aggregateMetric(pctSeriesRaw[1].values, resolution, buckets),
                roi: aggregateMetric(pctSeriesRaw[2].values, resolution, buckets),
            },
        };

        resolutionCache.set(resolution, entry);
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
        const entry = getResolutionData(currentResolution);
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

    function buildChartUpdateSeries(_isDark: boolean, entry: AggregatedResolutionData): {name: string; data: SeriesPoint[]}[] {
        if (viewMode === 'eur') {
            return [
                {name: eurLabels.bookAssetLike, data: entry.eur.bookAssetLike.points},
                {name: eurLabels.cashContributed, data: entry.eur.cashContributed.points},
                {name: eurLabels.cashGenerated, data: entry.eur.cashGenerated.points},
                {name: eurLabels.nav, data: entry.eur.nav.points},
                {name: eurLabels.capitalBaseline, data: entry.eur.capitalBaseline.points},
            ];
        }

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

    function updateChartData(entry: AggregatedResolutionData, isDark: boolean, zoomWindow: {start: number; end: number}, skipAnimation: boolean) {
        if (!chartInstance) return;

        const series = buildChartUpdateSeries(isDark, entry).map((seriesEntry) => ({
            name: seriesEntry.name,
            data: seriesEntry.data,
        }));

        // skipAnimation is only ever true for a resolution switch (daily <-> weekly/monthly),
        // where the data-point count per series changes drastically. If a tooltip is
        // currently showing (user hovering while zooming — the exact gesture that triggers
        // a resolution switch), ECharts can crash inside its internal _showAxisTooltip
        // reading stale series/dataIndex references once series are replaced via
        // replaceMerge. Hiding the tooltip first clears that internal state safely.
        if (skipAnimation) {
            chartInstance.dispatchAction({type: 'hideTip'});
        }

        chartInstance.setOption(
            {
                ...(skipAnimation
                    ? {
                          animation: false,
                          animationDuration: 0,
                          animationDurationUpdate: 0,
                      }
                    : CHART_ANIMATION_CONFIG),
                dataZoom: [{type: 'inside', start: zoomWindow.start, end: zoomWindow.end}],
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
        updateChartData(entry, isDark, zoomWindow, true);
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
            resizeObserver?.disconnect();
            chartInstance?.dispose();
        };
    });

    $effect(() => {
        // Re-render when data, viewMode, or locale changes
        void history;
        void viewMode;
        void pctSeries;
        void eurLabels;
        void $locale;

        if (history !== lastHistoryRef) {
            lastHistoryRef = history;
            resetResolutionState();
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
        if (!chartContainer) return;
        // If already observing the same element, nothing to do
        if (resizeObserver && observedContainer === chartContainer) return;
        resizeObserver?.disconnect();
        resizeObserver = new ResizeObserver(() => {
            chartInstance?.resize();
            scheduleResolutionSync();
        });
        resizeObserver.observe(chartContainer);
        observedContainer = chartContainer;
    }

    function renderChart() {
        if (!chartContainer || loading || history.length === 0) return;

        if (chartInstance && chartInstance.getDom() !== chartContainer) {
            dataZoomCleanup?.();
            chartInstance.dispose();
            chartInstance = undefined;
            lastRenderedMode = null;
            lastRenderedDark = null;
        }

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
            needsInitialLayoutStabilityPass = true;
            // Setup mobile tooltip auto-hide
            tooltipCleanup?.();
            tooltipCleanup = setupTooltipAutoHide(chartContainer, () => chartInstance);
            dataZoomCleanup?.();
            const zoomInstance = chartInstance;
            const onDataZoom = () => scheduleResolutionSync();
            zoomInstance.on('dataZoom', onDataZoom);
            dataZoomCleanup = () => zoomInstance.off('dataZoom', onDataZoom);
        }

        const isDark = document.documentElement.classList.contains('dark');
        const logicalRange = ensureLogicalRange();
        if (!logicalRange) return;

        if (currentResolution === 'daily' && visibleStartDate === dates[0] && visibleEndDate === dates[dates.length - 1]) {
            const counts = computeBucketCounts(logicalRange.startDate, logicalRange.endDate);
            currentResolution = chooseInitialResolution(counts, chartInstance.getWidth());
        }

        const activeData = getResolutionData(currentResolution);
        const zoomWindow = buildZoomWindow(currentResolution, logicalRange.startDate, logicalRange.endDate);
        activeChartData = activeData;

        // Determine if this is a data-only update (same mode, same dark) or full re-init
        const needsFullInit = lastRenderedMode !== viewMode || lastRenderedDark !== isDark;
        const seriesData = buildChartUpdateSeries(isDark, activeData);

        if (needsFullInit) {
            applyFullOption(isDark, buildFullSeries(isDark, seriesData), zoomWindow);
        } else {
            updateChartData(activeData, isDark, zoomWindow, false);
        }

        lastRenderedMode = viewMode;
        lastRenderedDark = isDark;
    }

    function applyFullOption(isDark: boolean, series: echarts.SeriesOption[], zoomWindow: {start: number; end: number}) {
        if (!chartInstance) return;
        const {bg: tooltipBg, border: tooltipBorder, textColor, mutedColor} = buildTooltipTheme(isDark);
        const gridColor = isDark ? '#1e293b' : '#f1f5f9';

        const yAxisFormatter =
            viewMode === 'eur'
                ? (v: number) => {
                      if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
                      if (Math.abs(v) >= 1_000) return `${(v / 1_000).toFixed(0)}k`;
                      return String(v);
                  }
                : (v: number) => `${v.toFixed(1)}%`;

        /** Format a number as currency — same pattern as the dashboard formatMoney helper. */
        const fmtCurrency = (v: number | null | undefined) => (v != null ? `${baseCurrency} ${v.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : '—');

        const option: echarts.EChartsOption = {
            ...CHART_ANIMATION_CONFIG,
            backgroundColor: 'transparent',
            grid: {left: '3%', right: '4%', bottom: '30px', top: '10px', containLabel: true},
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
            },
            dataZoom: [{type: 'inside', start: zoomWindow.start, end: zoomWindow.end}],
            xAxis: {
                type: 'time',
                axisLabel: {color: textColor, fontSize: 14, rotate: 0},
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

        chartInstance.setOption(option, CHART_SET_OPTION_OPTS);
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

        <!-- Abs / % segmented toggle -->
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
        </div>
    </div>

    <!-- Chart area — container always in DOM for animation persistence -->
    <div class="relative" style="height: {height}">
        <div class="absolute top-2 left-2 z-10 pointer-events-none">
            <ResolutionBadge resolution={currentResolution} />
        </div>
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
</div>
