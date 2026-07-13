<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {z} from 'zod';
    import {schemas, zodiosApi} from '$lib/api';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import {CHART_ANIMATION_CONFIG, CHART_SET_OPTION_OPTS, namedPoint} from '$lib/components/charts/echartsAnimationConfig';
    import {buildGridColors, buildTooltipDivider, buildTooltipHeader, buildTooltipRow, buildTooltipTheme, scheduleFirstRenderStabilityFix, setupTooltipAutoHide, tooltipPositionSide} from '$lib/components/charts/echartsTooltipHelpers';
    import {buildDataZoom} from '$lib/components/charts/chartCoreHelpers';
    import {attachDataZoomTouchPan, type DataZoomTouchPanHandle} from '$lib/components/charts/echartsDataZoomTouchPan';
    import {attachDataZoomSync, type DataZoomSyncHandle} from '$lib/components/charts/echartsDataZoomSync';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import {getBrokerColor, type BrokerLike} from '$lib/utils/broker/brokerColors';

    type AssetHistoryPoint = z.infer<typeof schemas.AssetHistoryPoint>;
    type DisplayMode = 'absolute' | 'percentage';

    const DAY_MS = 24 * 60 * 60 * 1000;

    interface Props {
        assetId: number;
        brokerIds: number[];
        brokers: ReadonlyArray<BrokerLike>;
        currency: string;
    }

    type ComponentProps = {
        assetId: number;
        brokerIds?: number[];
        brokerId?: number;
        brokers?: ReadonlyArray<BrokerLike>;
        currency: string;
        onRangeComputed?: (min: string, max: string) => void;
        xAxisRange?: {min: string; max: string} | null;
        /** Fired whenever this chart's own internal loading state changes (true at fetch
         *  start, false at fetch end regardless of success/failure). Lets a parent (e.g.
         *  FIFOLotsPanel) gate a combined skeleton that covers both this chart and a
         *  sibling chart, so they only ever appear together once both are ready. */
        onLoadingChange?: (loading: boolean) => void;
        /** Cross-chart zoom/pan sync (e.g. with FIFOLotsPanel's bubble-lot chart) — fired
         *  whenever THIS chart's own dataZoom changes (user or programmatic). */
        onZoomChange?: (start: number, end: number) => void;
        /** Cross-chart zoom/pan sync — apply an externally-sourced zoom window (e.g. from
         *  the linked bubble-lot chart) onto this chart. */
        externalZoomStart?: number | null;
        externalZoomEnd?: number | null;
    };

    interface ChartPoint {
        date: string;
        brokerId: number | null;
        wac: number | null;
        marketPrice: number | null;
        roi: number | null;
        twrr: number | null;
    }

    interface BrokerSeries {
        brokerId: number | null;
        name: string;
        isCombined: boolean;
        points: ChartPoint[];
        hasWacData: boolean;
        hasPercentData: boolean;
    }

    interface MarketPricePoint {
        date: string;
        value: number | null;
    }

    let {assetId, brokerIds = [], brokerId, brokers = [], currency, onRangeComputed, xAxisRange = null, onLoadingChange, onZoomChange, externalZoomStart = null, externalZoomEnd = null}: ComponentProps = $props();

    const effectiveBrokerIds = $derived.by(() => (brokerIds.length > 0 ? brokerIds : brokerId != null ? [brokerId] : []));

    let displayMode = $state<DisplayMode>('absolute');
    let loading = $state(false);
    let error = $state<string | null>(null);
    let history = $state<AssetHistoryPoint[]>([]);
    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | undefined = undefined;
    let resizeObserver: ResizeObserver | null = null;
    let darkModeObserver: MutationObserver | null = null;
    let tooltipCleanup: (() => void) | null = null;
    let dataZoomTouchPanHandle: DataZoomTouchPanHandle | null = null;
    let dataZoomSyncHandle: DataZoomSyncHandle | null = null;
    let isDark = $state(false);
    let needsInitialLayoutStabilityPass = false;
    let fetchVersion = 0;

    function tr(key: string, fallback: string): string {
        const translated = $t(key);
        return !translated || translated === key ? fallback : translated;
    }

    function escapeHtml(value: string): string {
        return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function parseNumber(value: string | null | undefined): number | null {
        if (value == null) return null;
        const parsed = Number.parseFloat(value);
        return Number.isFinite(parsed) ? parsed : null;
    }

    /**
     * WAC is a REQUIRED (non-optional) backend field — it's never `null`, it's `0`
     * whenever the position pool is empty (before the first purchase, OR after a full
     * sell-off) — see compute_wac_from_txlist's `elif new_qty == 0: wac = 0` sentinel
     * (backend/app/utils/financial/wac_utils.py). A WAC of exactly 0 therefore always
     * means "not currently holding any units", NOT a genuine zero cost basis — treat it
     * as a gap (null) so the line doesn't draw a flat, meaningless segment along the
     * x-axis for periods before/without any holding.
     */
    function nullifyZeroWac(value: number | null): number | null {
        return value === 0 ? null : value;
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

    /**
     * Parse a date to UTC-midnight milliseconds. Accepts either an ISO date string
     * ('2024-06-15') or a NUMERIC timestamp — the latter is what ECharts' tooltip
     * `axisValue` provides for a `type: 'time'` xAxis (never a stringified number: passing
     * a numeric-looking STRING to `Date.parse`/`new Date()` fails to parse — it is NOT
     * the same as passing a genuine `number` — which previously caused the tooltip to
     * show the raw timestamp digits instead of a formatted date).
     */
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

    function syncTheme() {
        isDark = document.documentElement.classList.contains('dark');
    }

    async function loadHistory(nextAssetId: number, nextBrokerIds: number[], version: number) {
        loading = true;
        onLoadingChange?.(true);
        error = null;

        try {
            const response = await zodiosApi.get_asset_history_api_v1_portfolio_asset_history_get({
                queries: {
                    asset_id: nextAssetId,
                    broker_ids: nextBrokerIds,
                },
            });

            if (version !== fetchVersion) return;
            history = (response as AssetHistoryPoint[]) ?? [];
        } catch (err) {
            if (version !== fetchVersion) return;
            console.error('Failed to load asset history chart:', err);
            history = [];
            error = 'Failed to load chart';
        } finally {
            // Notifying onLoadingChange(false) here (before the reactive effect below has a
            // chance to run) would race ahead of onRangeComputed — a parent gating a SHARED
            // "both ready" reveal on wacLoading turning false could reveal the chart(s) in the
            // brief window before assetHistoryRange updates, defeating the whole point of the
            // gate. Only `loading` itself is set synchronously here; the "done" notification to
            // the parent is deferred to the merged effect below, which guarantees
            // onRangeComputed (when applicable) always runs first.
            if (version === fetchVersion) loading = false;
        }
    }

    function resolveBrokerName(brokerId: number): string {
        return brokers.find((broker) => broker.id === brokerId)?.name ?? `Broker ${brokerId}`;
    }

    function sortDates(a: string, b: string): number {
        return a.localeCompare(b);
    }

    function buildBrokerSeries(brokerId: number | null, points: ChartPoint[]): BrokerSeries {
        const sortedPoints = [...points].sort((a, b) => sortDates(a.date, b.date));
        return {
            brokerId,
            name: brokerId == null ? labels.combined : resolveBrokerName(brokerId),
            isCombined: brokerId == null,
            points: sortedPoints,
            hasWacData: sortedPoints.some((point) => point.wac != null),
            hasPercentData: sortedPoints.some((point) => point.roi != null || point.twrr != null),
        };
    }

    function getSeriesColor(series: BrokerSeries): string {
        if (series.isCombined || series.brokerId == null) {
            return isDark ? '#94a3b8' : '#475569';
        }

        const colors = getBrokerColor(series.brokerId, brokers);
        return isDark ? colors.vivid : colors.vividLight;
    }

    const labels = $derived.by(() => ({
        wac: 'WAC',
        marketPrice: 'Market Price',
        roi: tr('dashboard.roi', 'ROI'),
        twrr: tr('dashboard.twrr', 'TWRR'),
        abs: tr('dashboard.abs', 'Abs'),
        pct: tr('dashboard.pct', '%'),
        days: tr('datePicker.granularity.days', 'Days'),
        combined: tr('brokers.lots.combined', 'Combined'),
        noData: tr('common.noData', 'No data'),
    }));

    const groupedChartData = $derived.by(() => {
        const grouped = new Map<number | 'combined', ChartPoint[]>();

        for (const point of history) {
            const normalizedPoint: ChartPoint = {
                date: point.date,
                brokerId: point.broker_id ?? null,
                wac: nullifyZeroWac(parseNumber(point.wac)),
                marketPrice: parseNumber(point.market_price),
                roi: parseNumber(point.roi) != null ? parseNumber(point.roi)! * 100 : null,
                twrr: parseNumber(point.twrr) != null ? parseNumber(point.twrr)! * 100 : null,
            };
            const key = normalizedPoint.brokerId ?? 'combined';
            const existing = grouped.get(key);
            if (existing) {
                existing.push(normalizedPoint);
            } else {
                grouped.set(key, [normalizedPoint]);
            }
        }

        const brokerOrder = new Map(effectiveBrokerIds.map((id, index) => [id, index]));
        const realSeries = Array.from(grouped.entries())
            .filter(([key]) => key !== 'combined')
            .map(([key, points]) => buildBrokerSeries(key as number, points))
            .sort((a, b) => {
                const aOrder = brokerOrder.get(a.brokerId ?? -1) ?? Number.MAX_SAFE_INTEGER;
                const bOrder = brokerOrder.get(b.brokerId ?? -1) ?? Number.MAX_SAFE_INTEGER;
                return aOrder - bOrder || (a.brokerId ?? 0) - (b.brokerId ?? 0);
            });

        const combinedSeries = grouped.has('combined') ? buildBrokerSeries(null, grouped.get('combined') ?? []) : null;
        const marketPriceSourceSeries = realSeries.length > 0 ? realSeries : combinedSeries ? [combinedSeries] : [];
        const marketPriceByDate = new Map<string, number | null>();

        for (const series of marketPriceSourceSeries) {
            for (const point of series.points) {
                if (!marketPriceByDate.has(point.date)) {
                    marketPriceByDate.set(point.date, point.marketPrice);
                    continue;
                }
                if (marketPriceByDate.get(point.date) == null && point.marketPrice != null) {
                    marketPriceByDate.set(point.date, point.marketPrice);
                }
            }
        }

        const marketPricePoints: MarketPricePoint[] = Array.from(marketPriceByDate.entries())
            .map(([date, value]) => ({date, value}))
            .sort((a, b) => sortDates(a.date, b.date));

        const hasEurData = realSeries.some((series) => series.hasWacData) || (combinedSeries?.hasWacData ?? false) || marketPricePoints.some((point) => point.value != null);
        const hasPercentData = realSeries.some((series) => series.hasPercentData) || (combinedSeries?.hasPercentData ?? false);

        return {
            realSeries,
            combinedSeries,
            marketPricePoints,
            hasEurData,
            hasPercentData,
            totalPointCount: history.length,
        };
    });

    let hasEurData = $derived(groupedChartData.hasEurData);
    let hasPercentData = $derived(groupedChartData.hasPercentData);
    let chartStartDate = $derived.by(() => {
        let minDate: string | null = null;
        for (const point of history) {
            if (minDate == null || point.date < minDate) minDate = point.date;
        }
        return minDate;
    });
    let showChart = $derived(!loading && !error && groupedChartData.totalPointCount > 0 && (displayMode === 'absolute' ? hasEurData : hasPercentData));
    let emptyMessage = $derived.by(() => {
        if (error) return error;
        if (loading) return '';
        if (groupedChartData.totalPointCount === 0) return labels.noData;
        if (displayMode === 'percentage' && !hasPercentData) return 'No data yet';
        if (displayMode === 'absolute' && !hasEurData) return labels.noData;
        return '';
    });

    function buildEurSeries(): echarts.SeriesOption[] {
        const eurSeries: echarts.SeriesOption[] = [];

        for (const series of groupedChartData.realSeries) {
            if (!series.hasWacData) continue;
            const color = getSeriesColor(series);
            eurSeries.push({
                name: `${labels.wac} — ${series.name}`,
                type: 'line',
                data: series.points.map((point) => namedPoint(point.date, point.wac)),
                showSymbol: false,
                symbol: 'circle',
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 2, color},
                itemStyle: {color},
            });
        }

        if (groupedChartData.combinedSeries?.hasWacData) {
            const color = getSeriesColor(groupedChartData.combinedSeries);
            eurSeries.push({
                name: `${labels.wac} — ${groupedChartData.combinedSeries.name}`,
                type: 'line',
                data: groupedChartData.combinedSeries.points.map((point) => namedPoint(point.date, point.wac)),
                showSymbol: false,
                symbol: 'circle',
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 2.5, color, type: 'dashed'},
                itemStyle: {color},
            });
        }

        if (groupedChartData.marketPricePoints.some((point) => point.value != null)) {
            eurSeries.push({
                name: labels.marketPrice,
                type: 'line',
                data: groupedChartData.marketPricePoints.map((point) => namedPoint(point.date, point.value)),
                showSymbol: false,
                symbol: 'circle',
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 2.5, color: isDark ? '#4ade80' : '#16a34a'},
                itemStyle: {color: isDark ? '#4ade80' : '#16a34a'},
            });
        }

        return eurSeries;
    }

    function buildPercentSeries(): echarts.SeriesOption[] {
        const percentSeries: echarts.SeriesOption[] = [];

        for (const series of groupedChartData.realSeries) {
            if (!series.hasPercentData) continue;
            const color = getSeriesColor(series);
            percentSeries.push(
                {
                    name: `${labels.roi} — ${series.name}`,
                    type: 'line',
                    data: series.points.map((point) => namedPoint(point.date, point.roi)),
                    showSymbol: false,
                    symbol: 'circle',
                    connectNulls: false,
                    smooth: false,
                    lineStyle: {width: 2.5, color},
                    itemStyle: {color},
                },
                {
                    name: `${labels.twrr} — ${series.name}`,
                    type: 'line',
                    data: series.points.map((point) => namedPoint(point.date, point.twrr)),
                    showSymbol: false,
                    symbol: 'circle',
                    connectNulls: false,
                    smooth: false,
                    lineStyle: {width: 2, color, type: 'dashed'},
                    itemStyle: {color},
                },
            );
        }

        if (groupedChartData.combinedSeries?.hasPercentData) {
            const color = getSeriesColor(groupedChartData.combinedSeries);
            percentSeries.push(
                {
                    name: `${labels.roi} — ${groupedChartData.combinedSeries.name}`,
                    type: 'line',
                    data: groupedChartData.combinedSeries.points.map((point) => namedPoint(point.date, point.roi)),
                    showSymbol: false,
                    symbol: 'circle',
                    connectNulls: false,
                    smooth: false,
                    lineStyle: {width: 2.5, color, type: 'dashed'},
                    itemStyle: {color},
                },
                {
                    name: `${labels.twrr} — ${groupedChartData.combinedSeries.name}`,
                    type: 'line',
                    data: groupedChartData.combinedSeries.points.map((point) => namedPoint(point.date, point.twrr)),
                    showSymbol: false,
                    symbol: 'circle',
                    connectNulls: false,
                    smooth: false,
                    lineStyle: {width: 2, color, type: 'dotted'},
                    itemStyle: {color},
                },
            );
        }

        return percentSeries;
    }

    function buildSeries(): echarts.SeriesOption[] {
        return displayMode === 'absolute' ? buildEurSeries() : buildPercentSeries();
    }

    function buildTooltip(params: any[]): string {
        const theme = buildTooltipTheme(isDark);
        // Keep the RAW type — for a `type: 'time'` xAxis, `axisValue` is a NUMERIC
        // timestamp; stringifying it before parsing (the previous bug) made
        // `new Date(...)`/`Date.parse(...)` fail silently, showing the raw digits
        // instead of a formatted date. `value?.[0]` (the fallback) is the original ISO
        // date string from the series data — parseDateToUtcMs/formatDate handle both.
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
                // scale:true → fit the ACTUAL data range (min/max, with padding) instead of
                // ECharts' default of always forcing 0 into the range (getNeedCrossZero()
                // returns !option.scale — see LineChart.svelte's yAxisMode for the same
                // pattern). A forced 0 baseline compressed the visually-interesting WAC/price
                // variation into a thin band whenever those values sit far from 0.
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
        void assetId;
        void effectiveBrokerIds.join(',');

        fetchVersion += 1;
        const version = fetchVersion;
        history = [];
        void loadHistory(assetId, [...effectiveBrokerIds], version);
    });

    $effect(() => {
        if (displayMode === 'percentage' && !hasPercentData && hasEurData) {
            displayMode = 'absolute';
        }
    });

    $effect(() => {
        void groupedChartData;
        void displayMode;
        void currency;
        void labels;
        void loading;
        void error;
        void showChart;
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
        void loading;
        void error;
        void onRangeComputed;
        void onLoadingChange;

        if (loading) return; // still fetching — loadHistory() already notified onLoadingChange(true) synchronously.

        if (!error && groupedChartData.totalPointCount > 0) {
            let minDate: string | null = null;
            let maxDate: string | null = null;

            for (const point of history) {
                if (!minDate || point.date < minDate) minDate = point.date;
                if (!maxDate || point.date > maxDate) maxDate = point.date;
            }

            if (minDate && maxDate) {
                onRangeComputed?.(minDate, maxDate);
            }
        }

        // Fetch has settled (success, error, or empty) — notify the parent AFTER any
        // onRangeComputed call above, in the SAME synchronous pass, so a parent gating a
        // shared "both charts ready" reveal on this signal never reveals before the range
        // has already been reported for this asset.
        onLoadingChange?.(false);
    });

    $effect(() => {
        const start = externalZoomStart;
        const end = externalZoomEnd;
        if (start == null || end == null) return;
        dataZoomSyncHandle?.applyExternal(start, end);
    });
</script>

<div class="rounded-lg border border-gray-200/80 bg-gray-50/80 p-4 dark:border-slate-700 dark:bg-slate-900/30" data-testid="asset-wac-price-chart">
    <div class="mb-3 flex items-center justify-between gap-3">
        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-200">
            {displayMode === 'absolute' ? `${labels.wac} / ${labels.marketPrice}` : `${labels.roi} / ${labels.twrr}`}
        </h3>

        <div class="flex rounded-lg overflow-hidden border border-gray-200 dark:border-slate-600 text-xs font-medium">
            <button
                type="button"
                class="px-3 py-1 transition-colors {displayMode === 'absolute' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                onclick={() => (displayMode = 'absolute')}
                aria-pressed={displayMode === 'absolute'}
                data-testid="wac-toggle-absolute"
            >
                {labels.abs}
            </button>
            <button
                type="button"
                class="px-3 py-1 transition-colors border-l border-gray-200 dark:border-slate-600 {displayMode === 'percentage' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'} {!hasPercentData
                    ? 'cursor-not-allowed opacity-50'
                    : ''}"
                onclick={() => hasPercentData && (displayMode = 'percentage')}
                aria-pressed={displayMode === 'percentage'}
                disabled={!hasPercentData}
                title={!hasPercentData ? labels.noData : ''}
                data-testid="wac-toggle-percentage"
            >
                {labels.pct}
            </button>
        </div>
    </div>

    <div class="relative h-72 w-full">
        {#if loading}
            <div class="absolute inset-0 z-10 animate-pulse rounded bg-gray-100 dark:bg-slate-700"></div>
        {:else if emptyMessage}
            <div class="absolute inset-0 z-10 flex items-center justify-center text-center text-sm text-gray-400 dark:text-gray-500">
                {emptyMessage}
            </div>
        {/if}

        <div bind:this={chartContainer} class="h-full w-full" class:invisible={!showChart}></div>
    </div>
</div>
