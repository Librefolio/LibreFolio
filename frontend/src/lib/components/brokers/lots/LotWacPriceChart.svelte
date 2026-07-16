<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {z} from 'zod';
    import {schemas} from '$lib/api';
    import {_} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import {CHART_ANIMATION_CONFIG, CHART_SET_OPTION_OPTS, namedPoint} from '$lib/components/charts/echartsAnimationConfig';
    import {buildDataZoom} from '$lib/components/charts/chartCoreHelpers';
    import {attachDataZoomSync, type DataZoomSyncHandle} from '$lib/components/charts/echartsDataZoomSync';
    import {attachDataZoomTouchPan, type DataZoomTouchPanHandle} from '$lib/components/charts/echartsDataZoomTouchPan';
    import {
        buildGridColors,
        buildTooltipDivider,
        buildTooltipHeader,
        buildTooltipRow,
        buildTooltipTheme,
        scheduleFirstRenderStabilityFix,
        setupTooltipAutoHide,
        tooltipPositionSide,
    } from '$lib/components/charts/echartsTooltipHelpers';
    import {getBrokerColor, type BrokerLike} from '$lib/utils/broker/brokerColors';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';

    type BrokerWACHistoryPoint = z.infer<typeof schemas.BrokerWACHistoryPoint>;
    type CumulativeWACHistoryPoint = z.infer<typeof schemas.CumulativeWACHistoryPoint>;
    type LotPriceHistoryPoint = z.infer<typeof schemas.LotPriceHistoryPoint>;
    type DisplayMode = 'absolute' | 'percentage';

    const DAY_MS = 24 * 60 * 60 * 1000;

    type ComponentProps = {
        brokerWacHistory: BrokerWACHistoryPoint[];
        cumulativeWacHistory: CumulativeWACHistoryPoint[];
        priceHistory: LotPriceHistoryPoint[];
        brokers: ReadonlyArray<BrokerLike>;
        currency: string;
        xAxisRange?: {min: string; max: string} | null;
        onZoomChange?: (start: number, end: number) => void;
        externalZoomStart?: number | null;
        externalZoomEnd?: number | null;
        onRangeComputed?: (min: string, max: string) => void;
        onLoadingChange?: (loading: boolean) => void;
    };

    interface ValuePoint {
        date: string;
        absolute: number | null;
        percent: number | null;
    }

    interface BrokerSeries {
        brokerId: number | null;
        name: string;
        isCombined: boolean;
        points: ValuePoint[];
        hasAbsoluteData: boolean;
        hasPercentData: boolean;
    }

    let {
        brokerWacHistory = [],
        cumulativeWacHistory = [],
        priceHistory = [],
        brokers = [],
        currency,
        xAxisRange = null,
        onZoomChange,
        externalZoomStart = null,
        externalZoomEnd = null,
        onRangeComputed,
        onLoadingChange,
    }: ComponentProps = $props();

    let displayMode = $state<DisplayMode>('absolute');
    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | undefined = undefined;
    let resizeObserver: ResizeObserver | null = null;
    let darkModeObserver: MutationObserver | null = null;
    let tooltipCleanup: (() => void) | null = null;
    let dataZoomTouchPanHandle: DataZoomTouchPanHandle | null = null;
    let dataZoomSyncHandle: DataZoomSyncHandle | null = null;
    let isDark = $state(false);
    let needsInitialLayoutStabilityPass = false;

    function escapeHtml(value: string): string {
        return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function parseNumber(value: string | null | undefined): number | null {
        if (value == null) return null;
        const parsed = Number.parseFloat(value);
        return Number.isFinite(parsed) ? parsed : null;
    }

    function normalizeZero(value: number): number {
        return Object.is(value, -0) ? 0 : value;
    }

    function formatDate(value: number | string): string {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return String(value);
        return date.toLocaleDateString($currentLanguage || undefined, {year: 'numeric', month: 'short', day: 'numeric'});
    }

    function formatShortDate(value: number | string): string {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return String(value);
        return date.toLocaleDateString($currentLanguage || undefined, {month: 'short', day: 'numeric'});
    }

    function formatPercent(value: number): string {
        const normalized = normalizeZero(value);
        const sign = normalized > 0 ? '+' : '';
        return `${sign}${normalized.toFixed(2)}%`;
    }

    function formatAxisNumber(value: number): string {
        const normalized = normalizeZero(value);
        const abs = Math.abs(normalized);
        if (abs >= 1000) {
            return new Intl.NumberFormat(undefined, {notation: 'compact', maximumFractionDigits: 1}).format(normalized);
        }
        return normalized.toLocaleString(undefined, {minimumFractionDigits: abs < 10 && abs % 1 !== 0 ? 2 : 0, maximumFractionDigits: 2});
    }

    function parseDateToUtcMs(value: string | number): number | null {
        if (typeof value === 'number') {
            if (!Number.isFinite(value)) return null;
            const date = new Date(value);
            return Number.isNaN(date.getTime()) ? null : Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
        }

        const dateOnlyMatch = value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
        if (dateOnlyMatch) {
            const [, year, month, day] = dateOnlyMatch;
            return Date.UTC(Number(year), Number(month) - 1, Number(day));
        }

        const parsed = Date.parse(value);
        if (!Number.isFinite(parsed)) return null;
        const date = new Date(parsed);
        return Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
    }

    function elapsedDaysBetween(start: string, end: string | number): number | null {
        const startMs = parseDateToUtcMs(start);
        const endMs = parseDateToUtcMs(end);
        if (startMs == null || endMs == null || endMs < startMs) return null;
        return Math.floor((endMs - startMs) / DAY_MS);
    }

    function sortDates(a: string, b: string): number {
        return a.localeCompare(b);
    }

    function nullifyZeroWac(wac: number | null, poolQty: number | null): number | null {
        if (wac == null) return null;
        return wac === 0 || poolQty === 0 ? null : wac;
    }

    function toPercentSeries(points: Array<{date: string; value: number | null}>): ValuePoint[] {
        let baseline: number | null = null;
        for (const point of points) {
            if (point.value != null && point.value !== 0) {
                baseline = point.value;
                break;
            }
        }

        return points.map((point) => ({
            date: point.date,
            absolute: point.value,
            percent: point.value != null && baseline != null ? ((point.value - baseline) / baseline) * 100 : null,
        }));
    }

    function resolveBrokerName(brokerId: number): string {
        return brokers.find((broker) => broker.id === brokerId)?.name ?? `Broker ${brokerId}`;
    }

    function buildBrokerSeries(brokerId: number | null, points: Array<{date: string; value: number | null}>): BrokerSeries {
        const valuePoints = toPercentSeries([...points].sort((a, b) => sortDates(a.date, b.date)));
        return {
            brokerId,
            name: brokerId == null ? labels.combined : resolveBrokerName(brokerId),
            isCombined: brokerId == null,
            points: valuePoints,
            hasAbsoluteData: valuePoints.some((point) => point.absolute != null),
            hasPercentData: valuePoints.some((point) => point.percent != null),
        };
    }

    function getSeriesColor(series: BrokerSeries): string {
        if (series.isCombined || series.brokerId == null) {
            return isDark ? '#94a3b8' : '#475569';
        }

        const colors = getBrokerColor(series.brokerId, brokers);
        return isDark ? colors.vivid : colors.vividLight;
    }

    function syncTheme() {
        isDark = document.documentElement.classList.contains('dark');
    }

    const labels = $derived.by(() => ({
        wac: 'WAC',
        marketPrice: $_('chart.marketPrice'),
        abs: $_('dashboard.abs'),
        pct: $_('dashboard.pct'),
        days: $_('datePicker.granularity.days'),
        combined: $_('brokers.lots.combined'),
        noData: $_('common.noData'),
    }));

    const groupedChartData = $derived.by(() => {
        const groupedBrokerPoints = new Map<number, Array<{date: string; value: number | null}>>();
        for (const point of brokerWacHistory) {
            const brokerPoints = groupedBrokerPoints.get(point.broker_id) ?? [];
            brokerPoints.push({
                date: point.date,
                value: nullifyZeroWac(parseNumber(point.wac), parseNumber(point.pool_qty)),
            });
            groupedBrokerPoints.set(point.broker_id, brokerPoints);
        }

        const brokerOrder = new Map(brokers.map((broker, index) => [broker.id, index]));
        const realSeries = Array.from(groupedBrokerPoints.entries())
            .map(([brokerId, points]) => buildBrokerSeries(brokerId, points))
            .sort((a, b) => {
                const aOrder = brokerOrder.get(a.brokerId ?? -1) ?? Number.MAX_SAFE_INTEGER;
                const bOrder = brokerOrder.get(b.brokerId ?? -1) ?? Number.MAX_SAFE_INTEGER;
                return aOrder - bOrder || (a.brokerId ?? 0) - (b.brokerId ?? 0);
            });

        const distinctBrokerIds = new Set(brokerWacHistory.map((point) => point.broker_id));
        const combinedSeries =
            distinctBrokerIds.size >= 2 && cumulativeWacHistory.length > 0
                ? buildBrokerSeries(
                      null,
                      cumulativeWacHistory.map((point) => ({
                          date: point.date,
                          value: nullifyZeroWac(parseNumber(point.wac), parseNumber(point.pool_qty)),
                      })),
                  )
                : null;

        const marketPriceByDate = new Map<string, number | null>();
        for (const point of priceHistory) {
            const value = parseNumber(point.market_price);
            if (!marketPriceByDate.has(point.date)) {
                marketPriceByDate.set(point.date, value);
                continue;
            }
            if (marketPriceByDate.get(point.date) == null && value != null) {
                marketPriceByDate.set(point.date, value);
            }
        }

        const marketPricePoints = toPercentSeries(
            Array.from(marketPriceByDate.entries())
                .map(([date, value]) => ({date, value}))
                .sort((a, b) => sortDates(a.date, b.date)),
        );

        const allDates = [
            ...brokerWacHistory.map((point) => point.date),
            ...cumulativeWacHistory.map((point) => point.date),
            ...priceHistory.map((point) => point.date),
        ].sort(sortDates);

        return {
            realSeries,
            combinedSeries,
            marketPricePoints,
            minDate: allDates[0] ?? null,
            maxDate: allDates.at(-1) ?? null,
            hasAbsoluteData:
                realSeries.some((series) => series.hasAbsoluteData) ||
                (combinedSeries?.hasAbsoluteData ?? false) ||
                marketPricePoints.some((point) => point.absolute != null),
            hasPercentData:
                realSeries.some((series) => series.hasPercentData) ||
                (combinedSeries?.hasPercentData ?? false) ||
                marketPricePoints.some((point) => point.percent != null),
            totalPointCount: brokerWacHistory.length + cumulativeWacHistory.length + priceHistory.length,
        };
    });

    let hasAbsoluteData = $derived(groupedChartData.hasAbsoluteData);
    let hasPercentData = $derived(groupedChartData.hasPercentData);
    let chartStartDate = $derived(groupedChartData.minDate);
    let showChart = $derived(groupedChartData.totalPointCount > 0 && (displayMode === 'absolute' ? hasAbsoluteData : hasPercentData));
    let emptyMessage = $derived.by(() => {
        if (groupedChartData.totalPointCount === 0) return labels.noData;
        if (displayMode === 'absolute' && !hasAbsoluteData) return labels.noData;
        if (displayMode === 'percentage' && !hasPercentData) return labels.noData;
        return '';
    });

    function buildSeries(): echarts.SeriesOption[] {
        const valueKey = displayMode === 'absolute' ? 'absolute' : 'percent';
        const series: echarts.SeriesOption[] = [];

        for (const brokerSeries of groupedChartData.realSeries) {
            if (displayMode === 'absolute' && !brokerSeries.hasAbsoluteData) continue;
            if (displayMode === 'percentage' && !brokerSeries.hasPercentData) continue;
            const color = getSeriesColor(brokerSeries);
            series.push({
                name: `${labels.wac} — ${brokerSeries.name}`,
                type: 'line',
                data: brokerSeries.points.map((point) => namedPoint(point.date, point[valueKey])),
                showSymbol: false,
                symbol: 'circle',
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 2, color},
                itemStyle: {color},
            });
        }

        if (groupedChartData.combinedSeries) {
            const combinedSeries = groupedChartData.combinedSeries;
            const hasData = displayMode === 'absolute' ? combinedSeries.hasAbsoluteData : combinedSeries.hasPercentData;
            if (hasData) {
                const color = getSeriesColor(combinedSeries);
                series.push({
                    name: `${labels.wac} — ${combinedSeries.name}`,
                    type: 'line',
                    data: combinedSeries.points.map((point) => namedPoint(point.date, point[valueKey])),
                    showSymbol: false,
                    symbol: 'circle',
                    connectNulls: false,
                    smooth: false,
                    lineStyle: {width: 2.5, color, type: 'dashed'},
                    itemStyle: {color},
                });
            }
        }

        const marketHasData = groupedChartData.marketPricePoints.some((point) => point[valueKey] != null);
        if (marketHasData) {
            series.push({
                name: labels.marketPrice,
                type: 'line',
                data: groupedChartData.marketPricePoints.map((point) => namedPoint(point.date, point[valueKey])),
                showSymbol: false,
                symbol: 'circle',
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 2.5, color: isDark ? '#4ade80' : '#16a34a'},
                itemStyle: {color: isDark ? '#4ade80' : '#16a34a'},
            });
        }

        return series;
    }

    function buildTooltip(params: any[]): string {
        const theme = buildTooltipTheme(isDark);
        const rawDate: number | string = params[0]?.axisValue ?? params[0]?.value?.[0] ?? '';
        const elapsedDays = chartStartDate ? elapsedDaysBetween(chartStartDate, rawDate) : null;
        const rows = params
            .map((param) => {
                const rawValue = Array.isArray(param.value) ? param.value[1] : param.value;
                if (rawValue == null || rawValue === '') return null;
                const value = Number(rawValue);
                if (!Number.isFinite(value)) return null;
                const formatted = displayMode === 'absolute' ? formatCurrencyAmountPlain(value, currency) : formatPercent(value);
                return buildTooltipRow(escapeHtml(String(param.seriesName ?? '')), escapeHtml(formatted), typeof param.color === 'string' ? param.color : undefined);
            })
            .filter((row): row is string => row != null);

        if (elapsedDays != null) {
            rows.unshift(buildTooltipRow(escapeHtml(labels.days), escapeHtml(String(elapsedDays))));
        }

        if (rows.length === 0) return '';
        return `<div style="font-size:11px;color:${theme.textColor}">${buildTooltipHeader(escapeHtml(formatDate(rawDate)), theme.textColor)}${buildTooltipDivider(theme.border)}${rows.join('')}</div>`;
    }

    function buildOption(): echarts.EChartsOption {
        const theme = buildTooltipTheme(isDark);
        const gridColors = buildGridColors(isDark);

        return {
            ...CHART_ANIMATION_CONFIG,
            grid: {
                top: 44,
                right: 18,
                bottom: 34,
                left: 22,
                containLabel: true,
            },
            legend: {
                top: 4,
                left: 'center',
                itemWidth: 10,
                itemHeight: 10,
                textStyle: {
                    color: gridColors.textColor,
                    fontSize: 11,
                },
            },
            tooltip: {
                trigger: 'axis',
                position: tooltipPositionSide,
                backgroundColor: theme.bg,
                borderColor: theme.border,
                textStyle: {color: theme.textColor},
                axisPointer: {
                    type: 'line',
                    lineStyle: {
                        color: gridColors.gridColor,
                        width: 1,
                    },
                },
                formatter: (params: any) => buildTooltip(Array.isArray(params) ? params : [params]),
            },
            xAxis: {
                type: 'time',
                ...(xAxisRange ? {min: xAxisRange.min, max: xAxisRange.max} : {}),
                axisLine: {
                    lineStyle: {color: gridColors.gridColor},
                },
                axisTick: {show: false},
                splitLine: {show: false},
                axisLabel: {
                    color: gridColors.textColor,
                    hideOverlap: true,
                    formatter: (value: number) => formatShortDate(value),
                },
            },
            yAxis: {
                type: 'value',
                scale: true,
                axisLine: {show: false},
                axisTick: {show: false},
                splitLine: {
                    lineStyle: {
                        color: gridColors.gridColor,
                    },
                },
                axisLabel: {
                    color: gridColors.textColor,
                    formatter: (value: number) => (displayMode === 'absolute' ? formatAxisNumber(value) : `${normalizeZero(value).toFixed(0)}%`),
                },
            },
            series: buildSeries(),
            dataZoom: buildDataZoom([0]),
        };
    }

    function setupResizeObserver() {
        if (!chartContainer || resizeObserver) return;
        resizeObserver = new ResizeObserver(() => chartInstance?.resize());
        resizeObserver.observe(chartContainer);
    }

    function renderChart() {
        if (!chartContainer) return;

        syncTheme();

        if (chartInstance && chartInstance.getDom() !== chartContainer) {
            tooltipCleanup?.();
            resizeObserver?.disconnect();
            resizeObserver = null;
            dataZoomTouchPanHandle?.dispose();
            dataZoomTouchPanHandle = null;
            dataZoomSyncHandle?.dispose();
            dataZoomSyncHandle = null;
            chartInstance.dispose();
            chartInstance = undefined;
        }

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
            needsInitialLayoutStabilityPass = true;
            setupResizeObserver();
            tooltipCleanup?.();
            tooltipCleanup = setupTooltipAutoHide(chartContainer, () => chartInstance);
            dataZoomTouchPanHandle = attachDataZoomTouchPan(chartInstance, chartContainer);
            dataZoomSyncHandle = attachDataZoomSync(chartInstance, (start, end) => onZoomChange?.(start, end));
        }

        if (!showChart) {
            chartInstance.clear();
            return;
        }

        chartInstance.setOption(buildOption(), CHART_SET_OPTION_OPTS);
        if (needsInitialLayoutStabilityPass) {
            needsInitialLayoutStabilityPass = false;
            scheduleFirstRenderStabilityFix(chartInstance, chartContainer);
        }
    }

    onMount(() => {
        syncTheme();
        darkModeObserver = new MutationObserver(() => {
            syncTheme();
            renderChart();
        });
        darkModeObserver.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});

        return () => {
            tooltipCleanup?.();
            darkModeObserver?.disconnect();
            resizeObserver?.disconnect();
            dataZoomTouchPanHandle?.dispose();
            dataZoomTouchPanHandle = null;
            dataZoomSyncHandle?.dispose();
            dataZoomSyncHandle = null;
            chartInstance?.dispose();
        };
    });

    $effect(() => {
        if (displayMode === 'percentage' && !hasPercentData && hasAbsoluteData) {
            displayMode = 'absolute';
        }
    });

    $effect(() => {
        void groupedChartData;
        void displayMode;
        void currency;
        void labels;
        void $currentLanguage;
        void brokers;
        void xAxisRange;

        if (!chartContainer) return;
        tick().then(() => {
            renderChart();
        });
    });

    $effect(() => {
        void groupedChartData;
        void onRangeComputed;
        void onLoadingChange;

        if (groupedChartData.minDate && groupedChartData.maxDate) {
            onRangeComputed?.(groupedChartData.minDate, groupedChartData.maxDate);
        }
        onLoadingChange?.(false);
    });

    $effect(() => {
        const start = externalZoomStart;
        const end = externalZoomEnd;
        if (start == null || end == null) return;
        dataZoomSyncHandle?.applyExternal(start, end);
    });
</script>

<div class="rounded-lg border border-gray-200/80 bg-gray-50/80 p-4 dark:border-slate-700 dark:bg-slate-900/30" data-testid="lot-wac-price-chart">
    <div class="mb-3 flex items-center justify-between gap-3">
        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-200">WAC / {labels.marketPrice}</h3>

        <div class="flex overflow-hidden rounded-lg border border-gray-200 text-xs font-medium dark:border-slate-600">
            <button
                type="button"
                class="px-3 py-1 transition-colors {displayMode === 'absolute' ? 'bg-libre-green text-white' : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-400 dark:hover:bg-slate-700'}"
                onclick={() => (displayMode = 'absolute')}
                aria-pressed={displayMode === 'absolute'}
                data-testid="lot-wac-toggle-absolute"
            >
                {labels.abs}
            </button>
            <button
                type="button"
                class="border-l border-gray-200 px-3 py-1 transition-colors dark:border-slate-600 {displayMode === 'percentage' ? 'bg-libre-green text-white' : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-400 dark:hover:bg-slate-700'} {!hasPercentData
                    ? 'cursor-not-allowed opacity-50'
                    : ''}"
                onclick={() => hasPercentData && (displayMode = 'percentage')}
                aria-pressed={displayMode === 'percentage'}
                disabled={!hasPercentData}
                title={!hasPercentData ? labels.noData : ''}
                data-testid="lot-wac-toggle-percentage"
            >
                {labels.pct}
            </button>
        </div>
    </div>

    <div class="relative h-72 w-full">
        {#if emptyMessage}
            <div class="absolute inset-0 z-10 flex items-center justify-center text-center text-sm text-gray-400 dark:text-gray-500">
                {emptyMessage}
            </div>
        {/if}

        <div bind:this={chartContainer} class="h-full w-full" class:invisible={!showChart}></div>
    </div>
</div>
