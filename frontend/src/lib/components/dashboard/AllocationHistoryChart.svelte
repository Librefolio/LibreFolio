<!--
  AllocationHistoryChart — 100% stacked area chart for allocation history.

  Shows how portfolio allocation by type, sector, or geography evolved over time.
  Each category is a stacked area layer whose height = percentage weight.

  Props:
  - data: AllocationHistoryPoint[] from POST /allocation-history
  - height: CSS height (default "100%")
  - loading: Show skeleton

  Pattern: Svelte 5 Runes, ECharts, dark mode support.
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {CHART_ANIMATION_CONFIG, namedPoint} from '$lib/components/charts/echartsAnimationConfig';
    import {INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG} from '$lib/components/charts/chartCoreHelpers';
    import {attachDataZoomTouchPan, type DataZoomTouchPanHandle} from '$lib/components/charts/echartsDataZoomTouchPan';
    import ResolutionBadge from '$lib/components/charts/ResolutionBadge.svelte';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import {aggregateLineSeries, cascadeResolution, chooseInitialResolution, mapDateToBucket, type ChartResolution} from '$lib/components/charts/timeSeriesAggregation';
    import {_, t} from '$lib/i18n';
    import {buildTooltipTheme, buildTooltipHeader, buildTooltipByThreshold, buildTooltipTopN, tooltipPositionSide, setupTooltipAutoHide, scheduleFirstRenderStabilityFix} from '$lib/components/charts/echartsTooltipHelpers';
    import {getCountryInfo, ensureCountriesLoaded} from '$lib/stores/reference/countryStore';
    import {getSectorEmoji, ensureSectorsLoaded} from '$lib/stores/reference/sectorStore';
    import {sectorI18nKey} from '$lib/utils/assetTypes';
    import {currentLanguage} from '$lib/stores/app/language';

    interface AllocationComponent {
        name: string;
        value: string;
        amount: string;
    }

    interface AllocationHistoryPoint {
        date: string;
        components: AllocationComponent[];
    }

    interface Props {
        data: AllocationHistoryPoint[];
        height?: string;
        loading?: boolean;
        /** Which allocation dimension is being displayed — affects label localization. */
        dimension?: 'type' | 'sector' | 'geo';
    }

    interface LogicalRange {
        startDate: string;
        endDate: string;
    }

    interface TemporalBucketRow {
        date: string;
        bucketStart: string;
        bucketEnd: string;
        valuesByName: Record<string, number>;
    }

    interface AggregatedAllocationDataset {
        resolution: ChartResolution;
        categoryNames: string[];
        rows: TemporalBucketRow[];
        dates: string[];
        sortedNames: string[];
        avgWeights: Record<string, number>;
        rawDataByName: Record<string, number[]>;
        seriesDataByName: Record<string, ReturnType<typeof namedPoint>[]>;
        lineSeriesByName: Record<string, LineDataPoint[]>;
    }

    // Resolution switches recompute dataZoom with absolute startValue/endValue (not
    // percentages). The shared CHART_SET_OPTION_OPTS only replaceMerges 'series', so a plain
    // merge would combine the new startValue/endValue with any stale percentage-based
    // start/end left over from the user's own interactive zoom — a documented ECharts
    // conflict that collapses the visible window to empty (blank chart). Replacing
    // 'dataZoom' wholesale avoids that merge conflict.
    // https://github.com/apache/echarts/issues/8230
    const CHART_SERIES_UPDATE_OPTS: {notMerge: boolean; replaceMerge: string[]} = {notMerge: false, replaceMerge: ['series', 'dataZoom']};

    let {data = [], height = '100%', loading = false, dimension = 'type'}: Props = $props();

    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | undefined = undefined;
    let dataZoomTouchPanHandle: DataZoomTouchPanHandle | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let darkModeObserver: MutationObserver | null = null;
    let tooltipCleanup: (() => void) | null = null;
    let visibilityObservers: MutationObserver[] = [];
    let visibilityObserved = false;
    let lastKnownVisibility: boolean | null = null;
    let currentResolution: ChartResolution = $state('daily');
    let logicalRange: LogicalRange | null = $state(null);

    let refDataVersion = $state(0);

    const aggregatedDataCache = new Map<ChartResolution, AggregatedAllocationDataset>();
    let lastDataRef: AllocationHistoryPoint[] | null = null;
    let lastRenderedResolution: ChartResolution | null = null;
    let resolutionCheckTimer: ReturnType<typeof setTimeout> | null = null;
    let shouldPickInitialResolution = true;
    let suppressDataZoomHandling = false;
    let needsInitialLayoutStabilityPass = false;

    // Distinct colors for allocation categories (up to 12)
    const PALETTE_LIGHT = ['#1a4031', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#84cc16', '#ec4899', '#f97316', '#14b8a6', '#6366f1', '#a3a3a3'];
    const PALETTE_DARK = ['#4ade80', '#60a5fa', '#fbbf24', '#f87171', '#a78bfa', '#22d3ee', '#a3e635', '#f472b6', '#fb923c', '#2dd4bf', '#818cf8', '#d4d4d4'];

    /** Get an emoji/icon label for a category. */
    function getCategoryEmoji(rawName: string): string {
        if (dimension === 'sector') return getSectorEmoji(rawName);
        if (dimension === 'geo') {
            if (rawName === 'Other' || rawName === 'Unknown') return '🏳️';
            return getCountryInfo(rawName).flag_emoji || '🌍';
        }
        if (dimension === 'type') {
            const typeEmojis: Record<string, string> = {
                STOCK: '📈',
                ETF: '📊',
                BOND: '🏛️',
                CRYPTO: '₿',
                FUND: '💼',
                HOLD: '⏸️',
                CROWDFUND: '🤝',
                INDEX: '📉',
                OTHER: '📦',
                Liquidity: '💰',
            };
            return typeEmojis[rawName] ?? '📊';
        }
        return '';
    }

    onMount(() => {
        darkModeObserver = new MutationObserver(() => renderChart());
        darkModeObserver.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});

        const loadRefs = async () => {
            await Promise.allSettled([ensureCountriesLoaded($currentLanguage), ensureSectorsLoaded()]);
            refDataVersion++;
        };
        loadRefs();

        return () => {
            if (resolutionCheckTimer) clearTimeout(resolutionCheckTimer);
            tooltipCleanup?.();
            disconnectVisibilityObservers();
            darkModeObserver?.disconnect();
            resizeObserver?.disconnect();
            dataZoomTouchPanHandle?.dispose();
            dataZoomTouchPanHandle = null;
            chartInstance?.dispose();
        };
    });

    $effect(() => {
        void data;
        void dimension;
        void refDataVersion;
        void $currentLanguage;
        if (chartContainer) {
            tick().then(() => {
                setupVisibilityObservers();
                if (!resizeObserver && chartContainer) {
                    resizeObserver = new ResizeObserver(() => {
                        chartInstance?.resize();
                        scheduleResolutionCheck();
                    });
                    resizeObserver.observe(chartContainer);
                }
                syncVisibilityState();
                renderChart();
            });
        }
    });

    function disconnectVisibilityObservers() {
        for (const observer of visibilityObservers) observer.disconnect();
        visibilityObservers = [];
        visibilityObserved = false;
    }

    function isChartVisible(container: HTMLElement): boolean {
        if (!container.isConnected || container.getClientRects().length === 0) return false;
        const style = getComputedStyle(container);
        return style.display !== 'none' && style.visibility !== 'hidden';
    }

    function syncVisibilityState() {
        if (!chartContainer) return;
        const visible = isChartVisible(chartContainer);
        if (visible === lastKnownVisibility) return;
        lastKnownVisibility = visible;

        if (!visible) {
            chartInstance?.dispatchAction({type: 'hideTip'});
            return;
        }

        if (chartInstance) {
            chartInstance.resize();
        }
        renderChart({skipAnimation: true});
    }

    function setupVisibilityObservers() {
        if (!chartContainer || visibilityObserved) return;
        let ancestor = chartContainer.parentElement;
        while (ancestor) {
            const observer = new MutationObserver(() => syncVisibilityState());
            observer.observe(ancestor, {attributes: true, attributeFilter: ['class', 'style', 'hidden']});
            visibilityObservers.push(observer);
            ancestor = ancestor.parentElement;
        }
        visibilityObserved = true;
    }

    /** Localize category label. Temporal resolution pipeline stays fully separate. */
    function localizeName(rawName: string): string {
        if (dimension === 'geo') {
            if (rawName === 'Other' || rawName === 'Unknown') return $_('common.other') || 'Other';
            const info = getCountryInfo(rawName);
            return info.name || rawName;
        }
        if (dimension === 'sector') {
            const key = `sectors.${sectorI18nKey(rawName)}`;
            const localized = $t(key);
            return localized !== key ? localized : rawName;
        }
        if (dimension === 'type') {
            return $t(`assets.types.${rawName}`) || rawName;
        }
        return rawName;
    }

    function toUtcDate(value: string): Date {
        return new Date(`${value}T00:00:00Z`);
    }

    function normalizeAxisDate(value: unknown): string | null {
        if (typeof value === 'string') return value.slice(0, 10);
        if (typeof value === 'number') return new Date(value).toISOString().slice(0, 10);
        if (value instanceof Date) return value.toISOString().slice(0, 10);
        return null;
    }

    function getFullLogicalRangeFromData(): LogicalRange | null {
        if (data.length === 0) return null;
        const sorted = [...data].sort((left, right) => left.date.localeCompare(right.date));
        return {
            startDate: sorted[0].date,
            endDate: sorted[sorted.length - 1].date,
        };
    }

    function invalidateTemporalCacheIfNeeded() {
        if (data === lastDataRef) return;
        aggregatedDataCache.clear();
        lastDataRef = data;
        currentResolution = 'daily';
        logicalRange = getFullLogicalRangeFromData();
        lastRenderedResolution = null;
        shouldPickInitialResolution = true;
        if (resolutionCheckTimer) {
            clearTimeout(resolutionCheckTimer);
            resolutionCheckTimer = null;
        }
    }

    function finalizeDataset(resolution: ChartResolution, rows: TemporalBucketRow[], categoryNames: string[]): AggregatedAllocationDataset {
        const avgWeights: Record<string, number> = {};
        const rawDataByName: Record<string, number[]> = {};
        const lineSeriesByName: Record<string, LineDataPoint[]> = {};

        for (const name of categoryNames) {
            const values = rows.map((row) => row.valuesByName[name] ?? 0);
            rawDataByName[name] = values;
            lineSeriesByName[name] = rows.map((row) => ({date: row.date, value: row.valuesByName[name] ?? 0}));
            avgWeights[name] = values.length > 0 ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
        }

        const sortedNames = [...categoryNames].sort((left, right) => (avgWeights[right] ?? 0) - (avgWeights[left] ?? 0));
        const seriesDataByName: Record<string, ReturnType<typeof namedPoint>[]> = {};

        for (const name of sortedNames) {
            seriesDataByName[name] = rows.map((row) => namedPoint(row.date, row.valuesByName[name] ?? 0));
        }

        return {
            resolution,
            categoryNames,
            rows,
            dates: rows.map((row) => row.date),
            sortedNames,
            avgWeights,
            rawDataByName,
            seriesDataByName,
            lineSeriesByName,
        };
    }

    function buildDailyDataset(): AggregatedAllocationDataset {
        const sortedPoints = [...data].sort((left, right) => left.date.localeCompare(right.date));
        const categoryNames = [...new Set(sortedPoints.flatMap((point) => point.components.map((component) => component.name)))];
        const rows = sortedPoints.map((point) => {
            const valueMap = new Map(point.components.map((component) => [component.name, Number(component.value)]));
            const valuesByName: Record<string, number> = {};

            for (const name of categoryNames) {
                valuesByName[name] = valueMap.get(name) ?? 0;
            }

            return {
                date: point.date,
                bucketStart: point.date,
                bucketEnd: point.date,
                valuesByName,
            };
        });

        return finalizeDataset('daily', rows, categoryNames);
    }

    function buildAggregatedDataset(resolution: Exclude<ChartResolution, 'daily'>): AggregatedAllocationDataset {
        const dailyDataset = getResolutionDataset('daily');
        const rowsByDate = new Map<string, TemporalBucketRow>();

        for (const name of dailyDataset.categoryNames) {
            const aggregatedPoints = aggregateLineSeries(dailyDataset.lineSeriesByName[name] ?? [], resolution);

            for (const point of aggregatedPoints) {
                const meta = point as LineDataPoint & {bucketStart?: string; bucketEnd?: string};
                const bucketStart = meta.bucketStart ?? point.date;
                const bucketEnd = meta.bucketEnd ?? point.date;
                const existing = rowsByDate.get(point.date);

                if (existing) {
                    existing.valuesByName[name] = point.value ?? 0;
                    if (bucketStart < existing.bucketStart) existing.bucketStart = bucketStart;
                    if (bucketEnd > existing.bucketEnd) existing.bucketEnd = bucketEnd;
                } else {
                    rowsByDate.set(point.date, {
                        date: point.date,
                        bucketStart,
                        bucketEnd,
                        valuesByName: {[name]: point.value ?? 0},
                    });
                }
            }
        }

        const rows = [...rowsByDate.values()]
            .sort((left, right) => left.date.localeCompare(right.date))
            .map((row) => {
                const valuesByName: Record<string, number> = {};
                for (const name of dailyDataset.categoryNames) {
                    valuesByName[name] = row.valuesByName[name] ?? 0;
                }
                return {...row, valuesByName};
            });

        return finalizeDataset(resolution, rows, dailyDataset.categoryNames);
    }

    function getResolutionDataset(resolution: ChartResolution): AggregatedAllocationDataset {
        const cached = aggregatedDataCache.get(resolution);
        if (cached) return cached;

        const dataset = resolution === 'daily' ? buildDailyDataset() : buildAggregatedDataset(resolution);
        aggregatedDataCache.set(resolution, dataset);
        return dataset;
    }

    function getBucketCountsForRange(range: LogicalRange | null): {dailyCount: number; weeklyCount: number; monthlyCount: number} {
        const dailyDataset = getResolutionDataset('daily');
        const visibleRows = range ? dailyDataset.rows.filter((row) => row.date >= range.startDate && row.date <= range.endDate) : dailyDataset.rows;

        const weeklyBuckets = new Set<string>();
        const monthlyBuckets = new Set<string>();

        for (const row of visibleRows) {
            const weekly = mapDateToBucket(row.date, 'weekly');
            weeklyBuckets.add(`${weekly.bucketStart}|${weekly.bucketEnd}`);

            const monthly = mapDateToBucket(row.date, 'monthly');
            monthlyBuckets.add(`${monthly.bucketStart}|${monthly.bucketEnd}`);
        }

        return {
            dailyCount: visibleRows.length,
            weeklyCount: weeklyBuckets.size,
            monthlyCount: monthlyBuckets.size,
        };
    }

    function getRowsIntersectingRange(rows: TemporalBucketRow[], range: LogicalRange | null): TemporalBucketRow[] {
        if (!range) return rows;
        return rows.filter((row) => row.bucketEnd >= range.startDate && row.bucketStart <= range.endDate);
    }

    function findRowIndexAtOrAfter(rows: TemporalBucketRow[], date: string): number {
        const index = rows.findIndex((row) => row.date >= date);
        return index === -1 ? Math.max(rows.length - 1, 0) : index;
    }

    function findRowIndexAtOrBefore(rows: TemporalBucketRow[], date: string): number {
        for (let index = rows.length - 1; index >= 0; index--) {
            if (rows[index].date <= date) return index;
        }
        return 0;
    }

    function getRangeFromPercentages(rows: TemporalBucketRow[], start: number, end: number): LogicalRange | null {
        if (rows.length === 0) return null;
        const lastIndex = rows.length - 1;
        const clampedStart = Math.min(Math.max(start, 0), 100);
        const clampedEnd = Math.min(Math.max(end, 0), 100);
        const startIndex = Math.min(Math.floor((clampedStart / 100) * lastIndex), lastIndex);
        const endIndex = Math.min(Math.ceil((clampedEnd / 100) * lastIndex), lastIndex);
        const firstRow = rows[Math.min(startIndex, endIndex)];
        const lastRow = rows[Math.max(startIndex, endIndex)];

        return {
            startDate: firstRow.bucketStart,
            endDate: lastRow.bucketEnd,
        };
    }

    function getCurrentVisibleLogicalRange(): LogicalRange | null {
        const dataset = aggregatedDataCache.get(currentResolution);
        if (!chartInstance || !dataset || dataset.rows.length === 0) return logicalRange;

        let rawStart: unknown;
        let rawEnd: unknown;

        try {
            const option = chartInstance.getOption() as any;
            const dataZoom = option?.dataZoom?.[0];
            rawStart = dataZoom?.startValue;
            rawEnd = dataZoom?.endValue;

            if (rawStart == null || rawEnd == null) {
                const start = typeof dataZoom?.start === 'number' ? dataZoom.start : 0;
                const end = typeof dataZoom?.end === 'number' ? dataZoom.end : 100;
                return getRangeFromPercentages(dataset.rows, start, end);
            }
        } catch (_) {
            return logicalRange;
        }

        const startDate = normalizeAxisDate(rawStart);
        const endDate = normalizeAxisDate(rawEnd);
        if (!startDate || !endDate) return logicalRange;

        const firstIndex = findRowIndexAtOrAfter(dataset.rows, startDate);
        const lastIndex = findRowIndexAtOrBefore(dataset.rows, endDate);
        const firstRow = dataset.rows[Math.min(firstIndex, lastIndex)];
        const lastRow = dataset.rows[Math.max(firstIndex, lastIndex)];

        return {
            startDate: firstRow.bucketStart,
            endDate: lastRow.bucketEnd,
        };
    }

    function buildDataZoomOption(dataset: AggregatedAllocationDataset, range: LogicalRange | null): Record<string, unknown>[] {
        const baseDataZoom = {type: 'inside', ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG};
        const visibleRows = getRowsIntersectingRange(dataset.rows, range);
        if (visibleRows.length === 0) return [{...baseDataZoom, start: 0, end: 100}];
        return [
            {
                ...baseDataZoom,
                startValue: visibleRows[0].date,
                endValue: visibleRows[visibleRows.length - 1].date,
            },
        ];
    }

    function formatMonthLabel(date: string): string {
        return new Intl.DateTimeFormat($currentLanguage, {
            month: 'long',
            year: 'numeric',
            timeZone: 'UTC',
        }).format(toUtcDate(date));
    }

    function buildAllocationTooltipHeader(row: TemporalBucketRow, mutedColor: string): string {
        if (currentResolution === 'weekly') {
            return buildTooltipHeader($t('chart.tooltip.weekRange', {values: {start: row.bucketStart, end: row.bucketEnd}}), mutedColor) + buildTooltipHeader($t('chart.tooltip.valueAt', {values: {date: row.date}}), mutedColor);
        }

        if (currentResolution === 'monthly') {
            return buildTooltipHeader($t('chart.tooltip.monthLabel', {values: {month: formatMonthLabel(row.bucketStart)}}), mutedColor) + buildTooltipHeader($t('chart.tooltip.valueAt', {values: {date: row.date}}), mutedColor);
        }

        return buildTooltipHeader(row.date, mutedColor);
    }

    function getDisplayName(rawName: string): string {
        const emoji = getCategoryEmoji(rawName);
        const localized = localizeName(rawName);
        return emoji ? `${emoji} ${localized}` : localized;
    }

    function buildChartOption(dataset: AggregatedAllocationDataset, isDark: boolean, skipAnimation: boolean): echarts.EChartsOption {
        const palette = isDark ? PALETTE_DARK : PALETTE_LIGHT;
        const textColor = isDark ? '#94a3b8' : '#64748b';
        const gridColor = isDark ? '#1e293b' : '#f1f5f9';
        const tooltipBg = isDark ? '#1e293b' : '#ffffff';
        const tooltipBorder = isDark ? '#334155' : '#e2e8f0';

        const series: echarts.SeriesOption[] = dataset.sortedNames.map((name, index) => {
            const emoji = getCategoryEmoji(name);
            const showLabel = dataset.avgWeights[name] >= 3 && emoji;

            return {
                id: name,
                name: getDisplayName(name),
                type: 'line',
                stack: 'allocation',
                data: dataset.seriesDataByName[name],
                smooth: false,
                symbol: 'none',
                lineStyle: {color: palette[index % palette.length], width: 1, opacity: 0.7},
                areaStyle: {color: palette[index % palette.length] + '88'},
                itemStyle: {color: palette[index % palette.length]},
                emphasis: {focus: 'series'},
                label: showLabel
                    ? {
                          show: true,
                          position: 'inside',
                          formatter: () => emoji,
                          fontSize: 14,
                          color: isDark ? '#ffffff' : '#000000',
                          textShadowColor: isDark ? '#000' : '#fff',
                          textShadowBlur: 2,
                      }
                    : {show: false},
            };
        });

        return {
            ...(skipAnimation ? {animation: false, animationDuration: 0, animationDurationUpdate: 0} : CHART_ANIMATION_CONFIG),
            backgroundColor: 'transparent',
            grid: {left: '3%', right: '4%', bottom: '40px', top: '10px', containLabel: true},
            tooltip: {
                trigger: 'axis',
                // Bugfix: `appendToBody` moves the tooltip DOM to `document.body`, which
                // requires ECharts/zrender to convert our chart-local position into
                // document-absolute coordinates (accounting for scroll) — the exact same
                // class of bug already fixed once in PriceChartFull.svelte (see commit
                // fcdd89e8: "Fix mobile tooltip scroll offset ... instead of
                // cursor-relative positioning that shifted with vertical scroll") and again
                // in GrowthChart.svelte, by dropping `appendToBody` entirely. Without it,
                // the tooltip stays nested inside this chart's own container (forced to
                // `position:relative`), scrolling as ONE unit with the rest of the page —
                // no coordinate conversion needed at all, so it can't drift out of sync
                // with scroll. Not needed for clipping either: this card (AllocationPanel)
                // has no `overflow-hidden` ancestor around the chart itself.
                confine: true,
                position: tooltipPositionSide,
                axisPointer: {type: 'line'},
                backgroundColor: tooltipBg,
                borderColor: tooltipBorder,
                borderWidth: 1,
                textStyle: {color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 12},
                formatter: (params: unknown) => {
                    const items = Array.isArray(params) ? params : [params];
                    const idx = (items[0] as {dataIndex?: number} | undefined)?.dataIndex ?? 0;
                    const row = dataset.rows[idx];
                    if (!row) return '';

                    const theme = buildTooltipTheme(isDark);
                    const allItems = dataset.sortedNames
                        .map((name, seriesIndex) => ({
                            name: getDisplayName(name),
                            value: dataset.rawDataByName[name]?.[idx] ?? 0,
                            color: palette[seriesIndex % palette.length],
                        }))
                        .filter((item) => item.value > 0.01);

                    const header = buildAllocationTooltipHeader(row, theme.mutedColor);
                    const rows =
                        dimension === 'type'
                            ? allItems.length <= 6
                                ? buildTooltipTopN(allItems, allItems.length, theme, $_('common.remaining') || 'Remaining')
                                : buildTooltipTopN(allItems, 5, theme, $_('common.remaining') || 'Remaining')
                            : buildTooltipByThreshold(allItems, 3, theme, $_('common.remaining') || 'Remaining');

                    return header + rows;
                },
            },
            legend: {
                bottom: 0,
                left: 'center',
                textStyle: {color: textColor, fontSize: 14},
                itemWidth: 12,
                itemHeight: 8,
                type: 'scroll',
                width: '90%',
                pageTextStyle: {color: textColor},
                pageIconColor: textColor,
                pageIconInactiveColor: isDark ? '#334155' : '#cbd5e1',
            },
            dataZoom: buildDataZoomOption(dataset, logicalRange),
            xAxis: {
                type: 'time',
                axisLabel: {color: textColor, fontSize: 14, rotate: 0},
                axisLine: {lineStyle: {color: gridColor}},
                splitLine: {show: false},
            },
            yAxis: {
                type: 'value',
                max: 100,
                axisLabel: {color: textColor, fontSize: 14, formatter: (value: number) => `${value}%`},
                axisLine: {show: false},
                splitLine: {lineStyle: {color: gridColor, type: 'dashed'}},
            },
            series,
        };
    }

    function attachDataZoomListener() {
        if (!chartInstance) return;

        chartInstance.off('dataZoom');
        chartInstance.on('dataZoom', () => {
            if (suppressDataZoomHandling) return;
            scheduleResolutionCheck();
        });
    }

    // NOTE: getCurrentVisibleLogicalRange() internally calls chartInstance.getOption(),
    // which deep-clones the entire chart option (documented ECharts behavior) — expensive
    // on charts with years of daily data. It must only run ONCE, inside the debounced
    // timeout body below (after the zoom/resize gesture settles for 200ms), never on every
    // raw dataZoom/resize tick — otherwise it runs at interaction frequency (~60/sec) and
    // causes visible stutter.
    function scheduleResolutionCheck() {
        if (resolutionCheckTimer) clearTimeout(resolutionCheckTimer);

        resolutionCheckTimer = setTimeout(() => {
            resolutionCheckTimer = null;
            if (!chartInstance) return;

            const range = getCurrentVisibleLogicalRange() ?? logicalRange ?? getFullLogicalRangeFromData();
            if (!range) return;

            logicalRange = range;

            const nextResolution = cascadeResolution(currentResolution, getBucketCountsForRange(range), Math.max(chartInstance.getWidth(), 1));
            if (nextResolution === currentResolution) return;

            currentResolution = nextResolution;
            renderChart({skipAnimation: true});
        }, 200);
    }

    function renderChart(options: {skipAnimation?: boolean} = {}) {
        if (!chartContainer || loading || data.length === 0) return;
        if (!isChartVisible(chartContainer)) return;

        invalidateTemporalCacheIfNeeded();

        if (chartInstance && chartInstance.getDom() !== chartContainer) {
            dataZoomTouchPanHandle?.dispose();
            dataZoomTouchPanHandle = null;
            chartInstance.dispose();
            chartInstance = undefined;
        }

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
            needsInitialLayoutStabilityPass = true;
            tooltipCleanup?.();
            tooltipCleanup = setupTooltipAutoHide(chartContainer, () => chartInstance);
            dataZoomTouchPanHandle = attachDataZoomTouchPan(chartInstance, chartContainer);
        }

        const fullRange = logicalRange ?? getFullLogicalRangeFromData();
        if (!logicalRange) logicalRange = fullRange;

        if (shouldPickInitialResolution && fullRange) {
            currentResolution = chooseInitialResolution(getBucketCountsForRange(fullRange), Math.max(chartInstance.getWidth(), 1));
            shouldPickInitialResolution = false;
        }

        const activeDataset = getResolutionDataset(currentResolution);
        const isDark = document.documentElement.classList.contains('dark');
        const skipAnimation = options.skipAnimation ?? (lastRenderedResolution !== null && lastRenderedResolution !== currentResolution);
        const option = buildChartOption(activeDataset, isDark, skipAnimation);

        // skipAnimation is true exactly when the resolution changed (daily <-> weekly/monthly),
        // where the number of stacked series/points differs from the previous render. If a
        // tooltip is currently showing (user hovering while zooming — the exact gesture that
        // triggers a resolution switch), ECharts can crash inside its internal
        // _showAxisTooltip reading stale series/dataIndex references once the series are
        // replaced via replaceMerge. Hiding the tooltip first clears that internal state safely.
        if (skipAnimation) {
            chartInstance.dispatchAction({type: 'hideTip'});
        }

        suppressDataZoomHandling = true;
        chartInstance.setOption(option, CHART_SERIES_UPDATE_OPTS);
        Promise.resolve().then(() => {
            suppressDataZoomHandling = false;
        });
        if (needsInitialLayoutStabilityPass) {
            needsInitialLayoutStabilityPass = false;
            scheduleFirstRenderStabilityFix(chartInstance, chartContainer);
        }

        attachDataZoomListener();
        lastRenderedResolution = currentResolution;
    }
</script>

<div class="relative" style="height: {height}">
    <div class="absolute top-2 left-2 z-10 pointer-events-none">
        <ResolutionBadge resolution={currentResolution} />
    </div>

    {#if loading}
        <div class="absolute inset-0 z-10 bg-gray-100 dark:bg-slate-700 rounded animate-pulse"></div>
    {:else if data.length === 0}
        <div class="absolute inset-0 z-10 flex items-center justify-center text-gray-400 dark:text-gray-500 text-sm">
            {$_('common.noData')}
        </div>
    {/if}

    <div bind:this={chartContainer} style="height: 100%; width: 100%;" class:invisible={loading || data.length === 0}></div>
</div>
