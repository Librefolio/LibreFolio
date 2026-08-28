<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {attachChartReady} from '$lib/utils/chartReady';
    import {z} from 'zod';
    import {schemas} from '$lib/api';
    import {_} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import {CHART_ANIMATION_CONFIG, namedPoint} from '$lib/components/charts/echartsAnimationConfig';
    import {buildDataZoom, getChartZoomWindow} from '$lib/components/charts/chartCoreHelpers';
    import {attachDataZoomTouchPan, type DataZoomTouchPanHandle} from '$lib/components/charts/echartsDataZoomTouchPan';
    import {buildGridColors, buildTooltipDivider, buildTooltipHeader, buildTooltipRow, buildTooltipTheme, scheduleFirstRenderStabilityFix, setupTooltipAutoHide, tooltipPositionSide} from '$lib/components/charts/echartsTooltipHelpers';
    import ResolutionBadge from '$lib/components/charts/ResolutionBadge.svelte';
    import {aggregateLineSeries, cascadeResolution, chooseInitialResolution, computeDensity, mapDateToBucket, type ChartResolution} from '$lib/components/charts/timeSeriesAggregation';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {finiteNumber} from '$lib/utils/core/finiteNumber';
    import {translateOr} from '$lib/utils/core/translateOr';
    import {formatAxisDate} from '$lib/utils/core/formatAxisDate';
    import {safeScalar, safeString} from '$lib/types';

    type LotSummarySchema = z.infer<typeof schemas.LotSummarySchema>;
    type LotValueHistoryPoint = z.infer<typeof schemas.LotValueHistoryPoint>;
    type LotReturnHistoryPoint = z.infer<typeof schemas.LotReturnHistoryPoint>;
    type ChartMode = 'value' | 'return';
    type LotValueSource = 'MARKET_PRICE' | 'ESTIMATED_AT_COST';
    type ReturnUnit = 'abs' | 'pct';

    export type LotIncomeEvent = {
        type: 'DIVIDEND' | 'INTEREST';
        date: string;
        broker_id: number | null;
        amount: string;
        lot_ids: number[];
    };

    interface Props {
        selectedLots: ReadonlyArray<LotSummarySchema>;
        valueHistory: ReadonlyArray<LotValueHistoryPoint>;
        returnHistory: ReadonlyArray<LotReturnHistoryPoint>;
        brokers: ReadonlyArray<BrokerLike>;
        currency: string;
        xAxisRange: {min: string; max: string} | null;
        incomeEvents?: ReadonlyArray<LotIncomeEvent>;
    }

    interface LotModel {
        lotId: number;
        label: string;
        valueSource: LotValueSource | null;
    }

    interface LotValueSeriesPoint {
        date: string;
        proceeds: number;
        openValue: number;
        originalCost: number;
        pnl: number;
        income: number;
    }

    interface LotReturnSeriesPoint {
        date: string;
        totalReturn: number | null;
        relativeReturn: number | null;
    }

    interface AggregatedValuePoint {
        date: string;
        openValue: number;
        proceeds: number;
        originalCost: number;
        income: number;
    }

    interface AggregateReturnPoint {
        date: string;
        totalReturn: number | null;
        openingValue: number;
        pnlWithIncome: number;
    }

    interface BucketInfo {
        date: string;
        bucketStart: string;
        bucketEnd: string;
        resolution: ChartResolution;
    }

    interface AutoYAxisRange {
        min: number;
        max: number;
    }

    interface StackAccumulator {
        positive: Map<string, number>;
        negative: Map<string, number>;
    }

    type ChartSeriesPoint = ReturnType<typeof namedPoint> & {
        bucketStart?: string;
        bucketEnd?: string;
        resolution?: ChartResolution;
        sourcePointCount?: number;
    };

    const LOT_COMPARISON_SET_OPTION_OPTS: {notMerge: boolean; replaceMerge: string[]} = {
        notMerge: false,
        replaceMerge: ['series', 'xAxis', 'yAxis', 'legend', 'dataZoom'],
    };

    /**
     * Empirically confirmed ECharts 6.0.0 bug (r2-hover-lines-disappear-per-lot): with the
     * chart-level `tooltip.trigger:'axis'` (needed for the Aggregate mode's "all values at this
     * date" tooltip, which works correctly), hovering ANYWHERE on the chart makes every
     * *individual per-lot* line series (different lots open on different dates, so their data
     * arrays start/stop at different points) vanish completely — not just their tooltip marker,
     * the whole rendered line — for as long as the tooltip is open. Reproduced deterministically
     * (exact same date, `chartInstance.convertToPixel`-computed hover position) and ruled out by
     * elimination, one candidate at a time, via a live-debuggable chart instance:
     * `emphasis`/`blur` config (incl. `emphasis:{disabled:true}`), `z`/`zlevel`, `stack` removal,
     * normalizing every series to one shared date backbone with explicit `null`s, `connectNulls`,
     * `hoverLayerThreshold`, `clip`, `sampling`/`large`/`progressive`, `animation`, dropping the
     * per-point `name` field, the `renderer` (canvas vs `svg` — same bug in both, so it is not a
     * canvas dirty-rect/hover-layer repaint artifact), and every `tooltip.axisPointer.type`
     * (`line`/`shadow`/`cross`/`none`). The ONLY thing that fixes it is giving the per-lot line
     * series their OWN `tooltip.trigger:'item'` (confirmed live): ECharts merges this with the
     * chart-level tooltip config, so these series just fall out of the axis-trigger tooltip
     * computation that corrupts their rendering, while still using the same formatter/theme when
     * hovered directly (the shared formatter below already normalizes a single item's `params`
     * into a 1-element array). The visible trade-off is minor: hovering a specific per-lot line
     * shows only that lot's tooltip instead of joining the shared axis tooltip, but the lines
     * never disappear again — a clear net win over the alternative (rewriting the whole tooltip
     * as fully custom, non-native DOM to sidestep axis-trigger entirely).
     */
    const PER_LOT_LINE_TOOLTIP_OVERRIDE: {trigger: 'item'} = {trigger: 'item'};

    /**
     * Hidden full-range line that participates in the chart-level axis tooltip so the shared
     * "values at this date" infobox fires even when EVERY visible series carries the
     * PER_LOT_LINE_TOOLTIP_OVERRIDE above (return mode with a single plotted lot / no aggregate
     * return series). Without it those modes have no axis-trigger series left, so the axis tooltip
     * never fires and no infobox appears (r2 fix4). It is opacity-0 / symbol:'none' so it never
     * paints, and every tooltip builder filters it out by this id so it contributes no row.
     */
    const AXIS_TRIGGER_ANCHOR_ID = 'axis-trigger-anchor';

    /**
     * Empty scatter overlay that renders the "position dot" on each visible per-lot line at the
     * hovered date (r3 fix5). The per-lot lines carry PER_LOT_LINE_TOOLTIP_OVERRIDE (item trigger),
     * so ECharts never draws a native axisPointer symbol on them; we drive this overlay manually
     * from the `updateAxisPointer` event and clear it on `globalout`. Kept out of the tooltip and
     * legend; per-point color matches each lot's line.
     */
    const PER_LOT_HOVER_DOTS_ID = 'per-lot-hover-dots';

    /** Income (dividend/interest) "|" markers series id — filtered out of the legend and axis tooltip. */
    const LOT_INCOME_MARKER_SERIES_ID = 'lot-income-markers';
    const AGGREGATE_RETURN_SERIES_ID = 'return-aggregate';

    let {selectedLots = [], valueHistory = [], returnHistory = [], brokers = [], currency, xAxisRange = null, incomeEvents = []}: Props = $props();

    let mode = $state<ChartMode>('value');
    let valueYFromZero = $state(false);
    let returnYFromZero = $state(false);
    let returnUnit = $state<ReturnUnit>('abs');
    let currentResolution: ChartResolution = $state('daily');
    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | undefined = undefined;
    let resizeObserver: ResizeObserver | null = null;
    let resizeAnimationFrame: number | null = null;
    let lastObservedChartSize: {width: number; height: number} | null = null;
    let darkModeObserver: MutationObserver | null = null;
    let tooltipCleanup: (() => void) | null = null;
    let dataZoomTouchPanHandle: DataZoomTouchPanHandle | null = null;
    let isDark = $state(false);
    let needsInitialLayoutStabilityPass = false;
    let lastHoverDotAxisValue: number | null = null;
    let zoomWindow = $state<{start: number; end: number} | null>(null);
    let resolutionDebounceTimer: ReturnType<typeof setTimeout> | null = null;
    let lastResolutionSourceSignature: string | null = null;

    function safeValueSource(value: LotSummarySchema['value_source']): LotValueSource | null {
        const source = safeString(value);
        return source === 'MARKET_PRICE' || source === 'ESTIMATED_AT_COST' ? source : null;
    }

    function parseNumber(value: string | Array<string | null> | null | undefined): number | null {
        const raw = safeString(value);
        if (raw == null) return null;
        const parsed = Number.parseFloat(raw);
        return Number.isFinite(parsed) ? parsed : null;
    }

    function parseRequiredNumber(value: string | Array<string | null> | null | undefined): number {
        return parseNumber(value) ?? 0;
    }

    function normalizeZero(value: number): number {
        return Object.is(value, -0) ? 0 : value;
    }

    function syncTheme() {
        if (typeof document === 'undefined') return;
        isDark = document.documentElement.classList.contains('dark');
    }

    function clamp(value: number, min: number, max: number): number {
        return Math.min(max, Math.max(min, value));
    }

    function withAlpha(color: string, alpha: number): string {
        const hslMatch = color.match(/^hsl\((.+)\)$/i);
        if (hslMatch) return `hsla(${hslMatch[1]}, ${alpha})`;
        const hexMatch = color.match(/^#([0-9a-f]{6})$/i);
        if (hexMatch)
            return `${color}${Math.round(clamp(alpha, 0, 1) * 255)
                .toString(16)
                .padStart(2, '0')}`;
        return color;
    }

    function formatShortDate(value: string): string {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return value;
        return date.toLocaleDateString($currentLanguage || undefined, {day: '2-digit', month: '2-digit', year: '2-digit'});
    }

    function formatLongDate(value: number | string): string {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return String(value);
        return date.toLocaleDateString($currentLanguage || undefined, {year: 'numeric', month: 'short', day: 'numeric'});
    }

    function formatPercent(value: number): string {
        const normalized = normalizeZero(value);
        const sign = normalized > 0 ? '+' : '';
        return `${sign}${normalized.toFixed(2)}%`;
    }

    function formatAxisPercent(value: number): string {
        const normalized = normalizeZero(value);
        const abs = Math.abs(normalized);
        const decimals = abs < 10 && abs % 1 !== 0 ? 2 : 1;
        return `${normalized.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: decimals})}%`;
    }

    function formatAxisNumber(value: number): string {
        const normalized = normalizeZero(value);
        const abs = Math.abs(normalized);
        if (abs >= 1000) {
            return new Intl.NumberFormat(undefined, {notation: 'compact', maximumFractionDigits: 1}).format(normalized);
        }
        return normalized.toLocaleString(undefined, {minimumFractionDigits: abs < 10 && abs % 1 !== 0 ? 2 : 0, maximumFractionDigits: 2});
    }

    function formatAxisCurrency(value: number): string {
        const normalized = normalizeZero(value);
        try {
            return new Intl.NumberFormat(undefined, {
                style: 'currency',
                currency,
                currencyDisplay: 'narrowSymbol',
                notation: 'compact',
                maximumFractionDigits: 1,
            }).format(normalized);
        } catch (_) {
            return `${formatAxisNumber(normalized)} ${currency}`;
        }
    }

    function lotColor(lotId: number): string {
        const hue = Math.round((lotId * 137.508) % 360);
        return isDark ? `hsl(${hue} 78% 68%)` : `hsl(${hue} 68% 44%)`;
    }

    function brokerName(brokerId: number | null): string {
        if (brokerId == null) return '—';
        return brokers.find((broker) => broker.id === brokerId)?.name ?? `#${brokerId}`;
    }

    function incomeEventColor(type: LotIncomeEvent['type']): string {
        if (type === 'DIVIDEND') return isDark ? '#2dd4bf' : '#0f766e';
        return isDark ? '#a78bfa' : '#6d28d9';
    }

    function lotLabel(openingDate: string, direction: 'LONG' | 'SHORT'): string {
        const dateLabel = formatShortDate(openingDate);
        if (direction === 'SHORT') {
            const translated = $_('brokers.lots.shortLotLabel', {values: {date: dateLabel}});
            return !translated || translated === 'brokers.lots.shortLotLabel' ? `Short ${dateLabel}` : translated;
        }
        const translated = $_('brokers.lots.lotLabel', {values: {date: dateLabel}});
        return !translated || translated === 'brokers.lots.lotLabel' ? `Lot ${dateLabel}` : translated;
    }

    function pointKey(lotId: number, date: string): string {
        return `${lotId}:${date}`;
    }

    function seriesValue(param: any): number | null {
        const rawValue = Array.isArray(param?.value) ? param.value[1] : param?.value;
        if (rawValue == null || rawValue === '') return null;
        const value = Number(rawValue);
        return Number.isFinite(value) ? value : null;
    }

    function parseTimeMs(value: unknown): number | null {
        if (value instanceof Date) {
            const time = value.getTime();
            return Number.isFinite(time) ? time : null;
        }
        if (typeof value === 'number') return Number.isFinite(value) ? value : null;
        if (typeof value !== 'string' || value.trim() === '') return null;

        const numeric = Number(value);
        if (Number.isFinite(numeric)) return numeric;

        const parsed = Date.parse(value);
        return Number.isFinite(parsed) ? parsed : null;
    }

    function tooltipXValue(param: any): unknown {
        if (param?.axisValue != null) return param.axisValue;
        if (Array.isArray(param?.data?.value)) return param.data.value[0];
        if (Array.isArray(param?.data)) return param.data[0];
        if (Array.isArray(param?.value)) return param.value[0];
        return null;
    }

    function tooltipRawDate(params: any[]): number | string {
        for (const param of params) {
            const raw = tooltipXValue(param);
            if (typeof raw === 'number' || (typeof raw === 'string' && raw.trim() !== '')) return raw;
        }
        return '';
    }

    function tooltipTimestamp(params: any[]): number | null {
        return parseTimeMs(tooltipRawDate(params));
    }

    function findPointAtOrBefore<T extends {date: string}>(points: ReadonlyArray<T>, timestampMs: number): T | null {
        let found: T | null = null;
        for (const point of points) {
            const pointTime = parseTimeMs(point.date);
            if (pointTime == null) continue;
            if (pointTime > timestampMs) break;
            found = point;
        }
        return found;
    }

    function valueEstimatedLineColor(): string {
        return isDark ? '#94a3b8' : '#64748b';
    }

    function aggregateReturnColor(): string {
        return isDark ? '#fbbf24' : '#d97706';
    }

    function lotIdFromSeriesId(param: any, prefix: string): number | null {
        const raw = typeof param?.seriesId === 'string' || typeof param?.seriesId === 'number' ? String(param.seriesId) : '';
        if (!raw.startsWith(prefix)) return null;
        const lotId = Number(raw.slice(prefix.length));
        return Number.isInteger(lotId) ? lotId : null;
    }

    function returnTooltipLotId(param: any): number | null {
        const fromId = lotIdFromSeriesId(param, 'return-');
        if (fromId != null) return fromId;
        const name = String(param?.seriesName ?? '');
        return visibleLots.find((lot) => lot.label === name || name === returnSeriesName(lot.label))?.lotId ?? null;
    }

    function isInternalTooltipSeries(param: any): boolean {
        const id = String(param?.seriesId ?? '');
        return id === AXIS_TRIGGER_ANCHOR_ID || id === PER_LOT_HOVER_DOTS_ID || id === LOT_INCOME_MARKER_SERIES_ID;
    }

    function applyCurrentZoomWindow() {
        if (!chartInstance) return;
        const window = getChartZoomWindow(chartInstance);
        if (window) zoomWindow = window;
    }

    function resetResolutionState(): void {
        currentResolution = 'daily';
        zoomWindow = null;
    }

    function lineDataPoint(date: string, value: number | null | undefined): LineDataPoint | null {
        if (value == null || !Number.isFinite(value)) return null;
        return {date, value};
    }

    function pointBucketMeta(point: LineDataPoint): {bucketStart: string; bucketEnd: string; resolution: ChartResolution; sourcePointCount?: number} {
        const meta = point as Partial<{bucketStart: string; bucketEnd: string; resolution: ChartResolution; sourcePointCount: number}>;
        return {
            bucketStart: typeof meta.bucketStart === 'string' ? meta.bucketStart : point.date,
            bucketEnd: typeof meta.bucketEnd === 'string' ? meta.bucketEnd : point.date,
            resolution: meta.resolution ?? 'daily',
            sourcePointCount: meta.sourcePointCount,
        };
    }

    function toChartSeriesPoints(points: LineDataPoint[], resolution: ChartResolution = currentResolution): ChartSeriesPoint[] {
        return aggregateLineSeries(points, resolution).map((point) => {
            const meta = pointBucketMeta(point);
            return {
                ...namedPoint(point.date, point.value),
                ...meta,
            };
        });
    }

    function chartSeriesPointValue(raw: unknown, index: number): {key: string; value: number | null} | null {
        const source = Array.isArray(raw) ? raw : raw && typeof raw === 'object' && 'value' in raw ? (raw as {value?: unknown}).value : raw;

        if (Array.isArray(source)) {
            const x = source[0];
            if (typeof x !== 'string' && typeof x !== 'number') return null;
            const y = source[1];
            return {key: String(x), value: y == null ? null : finiteNumber(y)};
        }

        const value = source == null ? null : finiteNumber(source);
        return value == null ? null : {key: `__index_${index}`, value};
    }

    function paddedAutoYAxisRange(min: number, max: number): AutoYAxisRange {
        const range = max - min;
        const magnitude = Math.max(Math.abs(min), Math.abs(max));
        const padding = range > 0 ? range * 0.05 : Math.max(magnitude * 0.05, Number.EPSILON);
        let paddedMin = min - padding;
        let paddedMax = max + padding;

        if (min > 0 && paddedMin <= 0) paddedMin = min * 0.95;
        if (max < 0 && paddedMax >= 0) paddedMax = max * 0.95;

        return {min: paddedMin, max: paddedMax};
    }

    function computeAutoYAxisRange(series: echarts.SeriesOption[]): AutoYAxisRange | null {
        let min: number | null = null;
        let max: number | null = null;
        const stackTotals = new Map<string, StackAccumulator>();

        for (const item of series) {
            const data = (item as {data?: unknown[]}).data;
            if (!Array.isArray(data)) continue;

            const stack = (item as {stack?: unknown}).stack;
            const stackKey = typeof stack === 'string' && stack.trim() !== '' ? stack : null;
            let accumulator: StackAccumulator | null = null;
            if (stackKey) {
                accumulator = stackTotals.get(stackKey) ?? {positive: new Map<string, number>(), negative: new Map<string, number>()};
                stackTotals.set(stackKey, accumulator);
            }

            for (const [index, raw] of data.entries()) {
                const point = chartSeriesPointValue(raw, index);
                if (!point || point.value == null) continue;

                let plottedValue = point.value;
                if (accumulator) {
                    const totals = plottedValue >= 0 ? accumulator.positive : accumulator.negative;
                    plottedValue = (totals.get(point.key) ?? 0) + plottedValue;
                    totals.set(point.key, plottedValue);
                }

                if (plottedValue === 0) continue;
                min = min == null ? plottedValue : Math.min(min, plottedValue);
                max = max == null ? plottedValue : Math.max(max, plottedValue);
            }
        }

        return min == null || max == null ? null : paddedAutoYAxisRange(min, max);
    }

    function buildBucketInfos(sourceDates: string[], resolution: ChartResolution): BucketInfo[] {
        if (resolution === 'daily') {
            return sourceDates.map((date) => ({date, bucketStart: date, bucketEnd: date, resolution}));
        }

        const buckets: BucketInfo[] = [];
        let lastBucketEnd: string | null = null;

        for (const date of sourceDates) {
            const {bucketStart, bucketEnd} = mapDateToBucket(date, resolution);
            if (bucketEnd === lastBucketEnd) continue;

            buckets.push({date: bucketEnd, bucketStart, bucketEnd, resolution});
            lastBucketEnd = bucketEnd;
        }

        return buckets;
    }

    function computeBucketCounts(startDate: string, endDate: string): {dailyCount: number; weeklyCount: number; monthlyCount: number} {
        let dailyCount = 0;
        const weekly = new Set<string>();
        const monthly = new Set<string>();

        for (const date of resolutionSourceDates) {
            if (date < startDate || date > endDate) continue;
            dailyCount += 1;
            weekly.add(mapDateToBucket(date, 'weekly').bucketEnd);
            monthly.add(mapDateToBucket(date, 'monthly').bucketEnd);
        }

        return {dailyCount, weeklyCount: weekly.size, monthlyCount: monthly.size};
    }

    function plotWidthPx(): number {
        return chartInstance?.getWidth() ?? chartContainer?.clientWidth ?? 0;
    }

    function getLogicalRangeFromChart(): {startDate: string; endDate: string} | null {
        if (resolutionSourceDates.length === 0) return null;
        const buckets = buildBucketInfos(resolutionSourceDates, currentResolution);
        if (buckets.length === 0) return null;

        const window = chartInstance ? getChartZoomWindow(chartInstance) : zoomWindow;
        if (window) zoomWindow = window;
        const start = window?.start ?? 0;
        const end = window?.end ?? 100;
        const maxIndex = Math.max(buckets.length - 1, 0);
        const startIndex = Math.max(0, Math.min(maxIndex, Math.floor((start / 100) * maxIndex)));
        const endIndex = Math.max(startIndex, Math.min(maxIndex, Math.ceil((end / 100) * maxIndex)));
        const startBucket = buckets[startIndex];
        const endBucket = buckets[endIndex];

        return {
            startDate: startBucket.bucketStart,
            endDate: endBucket.bucketEnd,
        };
    }

    function buildZoomWindowForRange(resolution: ChartResolution, startDate: string, endDate: string): {start: number; end: number} {
        const buckets = buildBucketInfos(resolutionSourceDates, resolution);
        if (buckets.length <= 1) return {start: 0, end: 100};

        const startIndex = Math.max(
            0,
            buckets.findIndex((bucket) => bucket.bucketEnd >= startDate),
        );
        const endIndex = Math.max(
            startIndex,
            buckets.findLastIndex((bucket) => bucket.bucketStart <= endDate),
        );
        const denominator = buckets.length - 1;

        return {
            start: (startIndex / denominator) * 100,
            end: (endIndex / denominator) * 100,
        };
    }

    function syncInitialResolution(): void {
        if (currentResolution !== 'daily' || zoomWindow || resolutionSourceDates.length === 0) return;

        const startDate = resolutionSourceDates[0];
        const endDate = resolutionSourceDates[resolutionSourceDates.length - 1];
        const counts = computeBucketCounts(startDate, endDate);
        const width = plotWidthPx();
        if (computeDensity(counts.dailyCount, width) <= 0) return;

        currentResolution = chooseInitialResolution(counts, width);
    }

    function syncResolutionToViewport(): void {
        if (!chartInstance || resolutionSourceDates.length === 0) return;

        const logicalRange = getLogicalRangeFromChart();
        if (!logicalRange) return;

        const counts = computeBucketCounts(logicalRange.startDate, logicalRange.endDate);
        const width = plotWidthPx();
        if (computeDensity(counts.dailyCount, width) <= 0) return;

        const targetResolution = cascadeResolution(currentResolution, counts, width);
        if (targetResolution === currentResolution) return;

        currentResolution = targetResolution;
        zoomWindow = buildZoomWindowForRange(targetResolution, logicalRange.startDate, logicalRange.endDate);
        renderChart();
    }

    function scheduleResolutionSync(): void {
        if (resolutionDebounceTimer) clearTimeout(resolutionDebounceTimer);
        resolutionDebounceTimer = setTimeout(() => {
            resolutionDebounceTimer = null;
            syncResolutionToViewport();
        }, 200);
    }

    function handleDataZoom(): void {
        applyCurrentZoomWindow();
        scheduleResolutionSync();
    }

    function formatTooltipMonth(date: string): string {
        const [year, month] = date.split('-').map(Number);
        return new Intl.DateTimeFormat($currentLanguage || undefined, {
            month: 'long',
            year: 'numeric',
            timeZone: 'UTC',
        }).format(new Date(Date.UTC(year, month - 1, 1)));
    }

    function tooltipBucketInfo(params: any[]): BucketInfo | null {
        for (const param of params) {
            const data = param?.data;
            if (!data || typeof data !== 'object') continue;
            const bucketStart = typeof data.bucketStart === 'string' ? data.bucketStart : null;
            const bucketEnd = typeof data.bucketEnd === 'string' ? data.bucketEnd : null;
            const resolution = data.resolution === 'weekly' || data.resolution === 'monthly' || data.resolution === 'daily' ? data.resolution : null;
            if (bucketStart && bucketEnd && resolution) return {date: bucketEnd, bucketStart, bucketEnd, resolution};
        }
        return null;
    }

    function buildTooltipBucketHeader(params: any[], fallbackDate: number | string, theme: ReturnType<typeof buildTooltipTheme>): string {
        const bucket = tooltipBucketInfo(params);
        if (!bucket || bucket.resolution === 'daily') return buildTooltipHeader(escapeHtml(formatLongDate(fallbackDate)), theme.textColor);

        const contextLine = `<div style="font-size:10px;color:${theme.mutedColor};margin-bottom:4px">${escapeHtml($_('chart.tooltip.valueAt', {values: {date: formatLongDate(bucket.bucketEnd)}}))}</div>`;
        if (bucket.resolution === 'weekly') {
            const label = $_('chart.tooltip.weekRange', {values: {start: formatLongDate(bucket.bucketStart), end: formatLongDate(bucket.bucketEnd)}});
            return `${buildTooltipHeader(escapeHtml(label), theme.textColor)}${contextLine}`;
        }

        const month = formatTooltipMonth(bucket.bucketEnd);
        const label = $_('chart.tooltip.monthLabel', {values: {month}});
        return `${buildTooltipHeader(escapeHtml(label), theme.textColor)}${contextLine}`;
    }

    const modeLabels = $derived.by(() => ({
        value: translateOr($_, 'common.value', 'Value'),
        return: translateOr($_, 'brokers.lots.modeReturn', 'Return'),
        valueTitle: translateOr($_, 'brokers.lots.valueComparisonTitle', 'Value of selected lots'),
        returnTitle: translateOr($_, 'brokers.lots.returnComparisonTitle', 'Return from opening date'),
        residualValue: translateOr($_, 'brokers.lots.aggregateResidualValue', 'Residual value'),
        residualValueEstimatedAtCost: translateOr($_, 'brokers.lots.aggregateResidualValueEstimatedAtCost', 'Residual value estimated at cost'),
        saleProceeds: translateOr($_, 'brokers.lots.aggregateSaleProceeds', 'Sale proceeds'),
        cumulativeIncome: translateOr($_, 'brokers.lots.aggregateCumulativeIncome', 'Cumulative income'),
        comprehensiveValue: translateOr($_, 'brokers.lots.aggregateComprehensiveValue', 'Comprehensive value'),
        aggregateOpeningValue: translateOr($_, 'brokers.lots.aggregateOpeningValue', 'Opening value'),
        aggregateReturn: translateOr($_, 'brokers.lots.aggregateReturn', 'Aggregate return'),
        fifoPnl: translateOr($_, 'brokers.lots.fifoPnl', 'FIFO P&L'),
        totalPnl: translateOr($_, 'brokers.lots.tooltip.totalPnl', 'Total P&L'),
        totalReturn: translateOr($_, 'brokers.lots.totalReturn', 'Total return'),
        yAuto: translateOr($_, 'brokers.lots.yAxisAuto', 'Auto'),
        yFromZero: translateOr($_, 'brokers.lots.yAxisFromZero', 'From 0'),
        returnUnitAbs: translateOr($_, 'brokers.lots.returnUnitAbs', 'Abs'),
        returnUnitPercent: translateOr($_, 'brokers.lots.returnUnitPercent', '%'),
        returnPctUndefined: translateOr($_, 'brokers.lots.returnPctUndefined', 'Not definable (opening value ≤ 0)'),
        openReturn: translateOr($_, 'brokers.lots.openReturn', 'Open Return'),
        selectLots: translateOr($_, 'brokers.lots.selectLotsToCompare', 'Select one or more lots to compare'),
        noVisibleLots: translateOr($_, 'brokers.lots.noVisibleLots', 'No visible lots in chart'),
        noData: translateOr($_, 'common.noData', 'No data'),
        estimatedAtCostLegend: translateOr($_, 'brokers.lots.estimatedAtCostLegend', 'Dashed neutral lines use value estimated at cost.'),
        incomeDividend: translateOr($_, 'brokers.lots.incomeMarkerDividend', 'Dividend'),
        incomeInterest: translateOr($_, 'brokers.lots.incomeMarkerInterest', 'Interest'),
        incomeType: translateOr($_, 'brokers.lots.incomeMarkerType', 'Type'),
        incomeDate: translateOr($_, 'brokers.lots.incomeMarkerDate', 'Transaction date'),
        incomeBroker: translateOr($_, 'brokers.lots.incomeMarkerBroker', 'Broker'),
        incomeAmount: translateOr($_, 'brokers.lots.incomeMarkerAmount', 'Amount'),
        incomeLotCount: translateOr($_, 'brokers.lots.incomeMarkerLotCount', 'Lots involved'),
    }));

    const lotModels = $derived.by(() => {
        const models = selectedLots.map((lot) => ({
            lotId: lot.lot_id,
            direction: lot.direction,
            openingDate: lot.opening_date,
            baseLabel: lotLabel(lot.opening_date, lot.direction),
            valueSource: safeValueSource(lot.value_source),
        }));

        const labelCounts = new Map<string, number>();
        for (const model of models) labelCounts.set(model.baseLabel, (labelCounts.get(model.baseLabel) ?? 0) + 1);

        return models.map((model) => ({
            lotId: model.lotId,
            label: (labelCounts.get(model.baseLabel) ?? 0) > 1 ? `${model.baseLabel} · #${model.lotId}` : model.baseLabel,
            valueSource: model.valueSource,
        })) satisfies LotModel[];
    });

    const visibleLots = $derived.by(() => lotModels);

    const hasEstimatedAtCostLots = $derived.by(() => visibleLots.some((lot) => lot.valueSource === 'ESTIMATED_AT_COST'));

    const incomeMarkerEvents = $derived.by(() =>
        (incomeEvents ?? []).filter((event): event is LotIncomeEvent => (event?.type === 'DIVIDEND' || event?.type === 'INTEREST') && !!event.date).sort((left, right) => left.date.localeCompare(right.date) || left.type.localeCompare(right.type) || (left.broker_id ?? -1) - (right.broker_id ?? -1)),
    );

    const valuePointsByLotId = $derived.by(() => {
        const grouped = new Map<number, LotValueSeriesPoint[]>();
        for (const point of valueHistory) {
            const existing = grouped.get(point.lot_id);
            const datum = {
                date: point.date,
                proceeds: parseRequiredNumber(point.proceeds),
                openValue: parseRequiredNumber(point.open_value),
                originalCost: parseRequiredNumber(point.original_cost),
                pnl: parseRequiredNumber(point.pnl),
                income: parseRequiredNumber(point.income),
            } satisfies LotValueSeriesPoint;
            if (existing) existing.push(datum);
            else grouped.set(point.lot_id, [datum]);
        }
        for (const points of grouped.values()) {
            points.sort((left, right) => left.date.localeCompare(right.date));
        }
        return grouped;
    });

    const valuePointByLotDate = $derived.by(() => {
        const byLotDate = new Map<string, LotValueSeriesPoint>();
        for (const [lotId, points] of valuePointsByLotId.entries()) {
            for (const point of points) {
                byLotDate.set(pointKey(lotId, point.date), point);
            }
        }
        return byLotDate;
    });

    const aggregatedValuePoints = $derived.by(() => {
        const totals = new Map<string, AggregatedValuePoint>();
        for (const lot of visibleLots) {
            for (const point of valuePointsByLotId.get(lot.lotId) ?? []) {
                const current = totals.get(point.date) ?? {
                    date: point.date,
                    openValue: 0,
                    proceeds: 0,
                    originalCost: 0,
                    income: 0,
                };
                current.openValue += point.openValue;
                current.proceeds += point.proceeds;
                current.originalCost += point.originalCost;
                current.income += point.income;
                totals.set(point.date, current);
            }
        }
        return Array.from(totals.values()).sort((left, right) => left.date.localeCompare(right.date));
    });

    const returnPointsByLotId = $derived.by(() => {
        const grouped = new Map<number, LotReturnSeriesPoint[]>();
        for (const point of returnHistory) {
            const existing = grouped.get(point.lot_id);
            const datum = {
                date: point.date,
                totalReturn: parseNumber(point.total_return),
                relativeReturn: parseNumber(point.relative_return),
            } satisfies LotReturnSeriesPoint;
            if (existing) existing.push(datum);
            else grouped.set(point.lot_id, [datum]);
        }
        for (const points of grouped.values()) {
            points.sort((left, right) => left.date.localeCompare(right.date));
        }
        return grouped;
    });

    const lotOpeningValueById = $derived.by(() => {
        const values = new Map<number, number>();
        for (const lot of visibleLots) {
            const firstValuePoint = valuePointsByLotId.get(lot.lotId)?.[0];
            values.set(lot.lotId, firstValuePoint?.originalCost ?? 0);
        }
        return values;
    });

    const returnAbsLotsWithData = $derived.by(() => visibleLots.filter((lot) => (valuePointsByLotId.get(lot.lotId)?.length ?? 0) > 0));

    const returnPctLotsWithData = $derived.by(() =>
        visibleLots.filter((lot) => {
            const openingValue = lotOpeningValueById.get(lot.lotId) ?? 0;
            return openingValue > 0 && (returnPointsByLotId.get(lot.lotId)?.some((point) => point.totalReturn != null) ?? false);
        }),
    );

    const returnPctUndefinedLots = $derived.by(() =>
        visibleLots.filter((lot) => {
            const hasData = (valuePointsByLotId.get(lot.lotId)?.length ?? 0) > 0 || (returnPointsByLotId.get(lot.lotId)?.length ?? 0) > 0;
            return hasData && (lotOpeningValueById.get(lot.lotId) ?? 0) <= 0;
        }),
    );

    const activeReturnLotsWithData = $derived.by(() => (returnUnit === 'pct' ? returnPctLotsWithData : returnAbsLotsWithData));

    const aggregateReturnPoints = $derived.by(() => {
        if (returnAbsLotsWithData.length < 1 && returnPctLotsWithData.length < 1) return [] satisfies AggregateReturnPoint[];

        const pctEligibleLotIds = new Set(returnPctLotsWithData.map((lot) => lot.lotId));
        const totals = new Map<string, {date: string; pnlWithIncome: number; pctPnlWithIncome: number; pctOpeningValue: number}>();
        for (const lot of returnAbsLotsWithData) {
            for (const point of valuePointsByLotId.get(lot.lotId) ?? []) {
                const current = totals.get(point.date) ?? {date: point.date, pnlWithIncome: 0, pctPnlWithIncome: 0, pctOpeningValue: 0};
                current.pnlWithIncome += point.pnl + point.income;
                if (pctEligibleLotIds.has(lot.lotId) && point.originalCost > 0) {
                    current.pctPnlWithIncome += point.pnl + point.income;
                    current.pctOpeningValue += point.originalCost;
                }
                totals.set(point.date, current);
            }
        }

        return Array.from(totals.values())
            .map((point) => ({
                date: point.date,
                totalReturn: point.pctOpeningValue > 0 ? point.pctPnlWithIncome / point.pctOpeningValue : null,
                openingValue: point.pctOpeningValue,
                pnlWithIncome: point.pnlWithIncome,
            }))
            .sort((left, right) => left.date.localeCompare(right.date)) satisfies AggregateReturnPoint[];
    });

    const aggregateReturnSeriesPoints = $derived.by(() => aggregateReturnPoints.map((point) => lineDataPoint(point.date, returnUnit === 'pct' ? (point.totalReturn == null ? null : point.totalReturn * 100) : point.pnlWithIncome)).filter((point): point is LineDataPoint => point != null));

    const showAggregateReturn = $derived(activeReturnLotsWithData.length >= 1 && aggregateReturnSeriesPoints.length > 0);

    const resolutionSourceDates = $derived.by(() => {
        const dates = new Set<string>();

        if (mode === 'value') {
            for (const point of aggregatedValuePoints) dates.add(point.date);
        } else if (returnUnit === 'pct') {
            for (const point of aggregateReturnPoints) {
                if (point.totalReturn != null) dates.add(point.date);
            }
            for (const lot of returnPctLotsWithData) {
                for (const point of returnPointsByLotId.get(lot.lotId) ?? []) {
                    if (point.totalReturn != null) dates.add(point.date);
                }
            }
        } else {
            for (const point of aggregateReturnPoints) dates.add(point.date);
            for (const lot of returnAbsLotsWithData) {
                for (const point of valuePointsByLotId.get(lot.lotId) ?? []) dates.add(point.date);
            }
        }

        return Array.from(dates).sort((left, right) => left.localeCompare(right));
    });

    const resolutionSourceSignature = $derived(`${mode}|${returnUnit}|${xAxisRange?.min ?? ''}|${xAxisRange?.max ?? ''}|${resolutionSourceDates.join('|')}`);

    const emptyMessage = $derived.by(() => {
        if (selectedLots.length === 0) return modeLabels.selectLots;
        if (visibleLots.length === 0) return modeLabels.noVisibleLots;

        if (mode === 'value') {
            return aggregatedValuePoints.length > 0 ? '' : modeLabels.noData;
        }

        return activeReturnLotsWithData.length > 0 ? '' : modeLabels.noData;
    });

    const chartTitle = $derived.by(() => {
        if (mode === 'value') return modeLabels.valueTitle;
        return modeLabels.returnTitle;
    });

    function incomeEventTypeLabel(type: LotIncomeEvent['type']): string {
        return type === 'DIVIDEND' ? modeLabels.incomeDividend : modeLabels.incomeInterest;
    }

    function buildIncomeEventTooltip(event: LotIncomeEvent | null): string {
        if (!event) return '';
        const theme = buildTooltipTheme(isDark);
        const rows = [
            buildTooltipRow(escapeHtml(modeLabels.incomeType), escapeHtml(incomeEventTypeLabel(event.type)), incomeEventColor(event.type)),
            buildTooltipRow(escapeHtml(modeLabels.incomeDate), escapeHtml(formatLongDate(event.date))),
            buildTooltipRow(escapeHtml(modeLabels.incomeBroker), escapeHtml(brokerName(event.broker_id))),
            buildTooltipRow(escapeHtml(modeLabels.incomeAmount), escapeHtml(formatCurrencyAmountPlain(parseRequiredNumber(event.amount), currency, {showSign: true}))),
            buildTooltipRow(escapeHtml(modeLabels.incomeLotCount), escapeHtml(String(event.lot_ids?.length ?? 0))),
        ];
        return `<div style="font-size:11px;color:${theme.textColor}">${buildTooltipHeader(escapeHtml(incomeEventTypeLabel(event.type)), theme.textColor)}${buildTooltipDivider(theme.border)}${rows.join('')}</div>`;
    }

    function returnSeriesUnitLabel(): string {
        return returnUnit === 'pct' ? modeLabels.returnUnitPercent : modeLabels.returnUnitAbs;
    }

    function returnSeriesName(label: string): string {
        return `${label} (${returnSeriesUnitLabel()})`;
    }

    function returnDisplayValue(value: number): string {
        return returnUnit === 'pct' ? formatPercent(value) : formatCurrencyAmountPlain(value, currency, {showSign: true});
    }

    function returnValueForLotAt(lotId: number, timestampMs: number): number | null {
        if (returnUnit === 'pct') {
            if ((lotOpeningValueById.get(lotId) ?? 0) <= 0) return null;
            const point = findPointAtOrBefore(returnPointsByLotId.get(lotId) ?? [], timestampMs);
            return point?.totalReturn == null ? null : point.totalReturn * 100;
        }

        const point = findPointAtOrBefore(valuePointsByLotId.get(lotId) ?? [], timestampMs);
        return point ? point.pnl + point.income : null;
    }

    /** Income "|" markers (rect 2×16px) sitting on the relevant line at each distribution date:
     *  - value mode: one marker on the aggregate comprehensive-value line.
     *  - return mode: one marker per involved lot at its total-return line height.
     * Coloured by type (dividend/interest). */
    function buildIncomeMarkerData(): Array<{value: [string, number]; incomeEvent: LotIncomeEvent; itemStyle: {color: string; opacity: number}}> {
        const data: Array<{value: [string, number]; incomeEvent: LotIncomeEvent; itemStyle: {color: string; opacity: number}}> = [];
        for (const event of incomeMarkerEvents) {
            const timestamp = parseTimeMs(event.date);
            if (timestamp == null) continue;
            const color = incomeEventColor(event.type);
            if (mode === 'value') {
                const agg = findPointAtOrBefore(aggregatedValuePoints, timestamp);
                if (agg) data.push({value: [event.date, agg.openValue + agg.proceeds + agg.income], incomeEvent: event, itemStyle: {color, opacity: 0.95}});
            } else if (mode === 'return') {
                for (const lotId of event.lot_ids ?? []) {
                    if (!visibleLots.some((lot) => lot.lotId === lotId)) continue;
                    const y = returnValueForLotAt(lotId, timestamp);
                    if (y == null) continue;
                    data.push({value: [event.date, y], incomeEvent: event, itemStyle: {color, opacity: 0.95}});
                }
            }
        }
        return data;
    }

    function buildIncomeMarkerSeries(): echarts.SeriesOption | undefined {
        if (incomeMarkerEvents.length === 0) return undefined;
        const data = buildIncomeMarkerData();
        if (data.length === 0) return undefined;
        return {
            id: LOT_INCOME_MARKER_SERIES_ID,
            name: LOT_INCOME_MARKER_SERIES_ID,
            type: 'scatter',
            symbol: 'rect',
            symbolSize: [2, 16],
            clip: true,
            z: 8,
            zlevel: 0,
            data,
            emphasis: {scale: 1.4},
            tooltip: {
                trigger: 'item',
                formatter: (param: any) => buildIncomeEventTooltip((param?.data?.incomeEvent ?? null) as LotIncomeEvent | null),
            },
        } as echarts.SeriesOption;
    }

    function attachIncomeMarkers(series: echarts.SeriesOption[]): echarts.SeriesOption[] {
        const markerSeries = buildIncomeMarkerSeries();
        if (!markerSeries) return series;
        return [...series, markerSeries];
    }

    function seriesDataDateRange(series: echarts.SeriesOption[]): [string, string] | null {
        let min: string | null = null;
        let max: string | null = null;
        for (const item of series) {
            const data = (item as {data?: unknown[]}).data;
            if (!Array.isArray(data)) continue;
            for (const raw of data) {
                const x = Array.isArray((raw as {value?: unknown[]})?.value) ? (raw as {value: unknown[]}).value[0] : Array.isArray(raw) ? (raw as unknown[])[0] : null;
                if (typeof x !== 'string' || x.trim() === '') continue;
                if (min == null || x < min) min = x;
                if (max == null || x > max) max = x;
            }
        }
        return min != null && max != null ? [min, max] : null;
    }

    /** Every distinct x-date present in the given series, sorted ascending. Used to build a DENSE
     * axis-trigger anchor so the shared infobox + per-lot hover dots fire at every plotted date
     * (with a time axis, a 2-point anchor only snaps near its endpoints). */
    function seriesDataDates(series: echarts.SeriesOption[]): string[] {
        const dates = new Set<string>();
        for (const item of series) {
            const data = (item as {data?: unknown[]}).data;
            if (!Array.isArray(data)) continue;
            for (const raw of data) {
                const x = Array.isArray((raw as {value?: unknown[]})?.value) ? (raw as {value: unknown[]}).value[0] : Array.isArray(raw) ? (raw as unknown[])[0] : null;
                if (typeof x !== 'string' || x.trim() === '') continue;
                dates.add(x);
            }
        }
        return Array.from(dates).sort((left, right) => left.localeCompare(right));
    }

    /** Prepend the hidden axis-trigger anchor (see AXIS_TRIGGER_ANCHOR_ID) only when no visible
     * series is left to drive the chart-level axis tooltip — i.e. every series opted out via the
     * per-lot item-trigger override. No-op otherwise, so value mode keeps its native axis
     * tooltip untouched. */
    function ensureAxisTriggerAnchor(series: echarts.SeriesOption[]): echarts.SeriesOption[] {
        const hasAxisSeries = series.some((item) => {
            const trigger = (item as {tooltip?: {trigger?: string}}).tooltip?.trigger;
            const data = (item as {data?: unknown[]}).data;
            return trigger !== 'item' && Array.isArray(data) && data.length > 0;
        });
        if (hasAxisSeries) return series;

        const anchorDates = seriesDataDates(series);
        let anchorData: Array<ReturnType<typeof namedPoint>>;
        if (anchorDates.length > 0) {
            anchorData = anchorDates.map((date) => namedPoint(date, 0));
        } else {
            const range = xAxisRange ? ([xAxisRange.min, xAxisRange.max] as [string, string]) : seriesDataDateRange(series);
            if (!range) return series;
            anchorData = [namedPoint(range[0], 0), namedPoint(range[1], 0)];
        }

        const anchor: echarts.SeriesOption = {
            id: AXIS_TRIGGER_ANCHOR_ID,
            name: AXIS_TRIGGER_ANCHOR_ID,
            type: 'line',
            data: anchorData,
            showSymbol: false,
            symbol: 'none',
            connectNulls: false,
            lineStyle: {opacity: 0, width: 0},
            itemStyle: {opacity: 0},
            emphasis: {disabled: true},
            z: 0,
            zlevel: 0,
        };
        return [anchor, ...series];
    }

    function buildReturnIndividualTooltipRows(timestampMs: number, excludedLotIds: ReadonlySet<number>): string[] {
        const rows = activeReturnLotsWithData
            .map((lot) => {
                if (excludedLotIds.has(lot.lotId)) return null;
                const value = returnValueForLotAt(lot.lotId, timestampMs);
                if (value == null) return null;
                return buildTooltipRow(escapeHtml(lot.label), escapeHtml(returnDisplayValue(value)), lotColor(lot.lotId));
            })
            .filter((row): row is string => row != null);

        if (returnUnit === 'pct') {
            for (const lot of returnPctUndefinedLots) {
                if (excludedLotIds.has(lot.lotId)) continue;
                rows.push(buildTooltipRow(escapeHtml(lot.label), escapeHtml(modeLabels.returnPctUndefined), isDark ? '#94a3b8' : '#64748b'));
            }
        }

        return rows;
    }

    function buildAggregateReturnTooltipRows(timestampMs: number): string[] {
        if (!showAggregateReturn) return [];
        const point = findPointAtOrBefore(aggregateReturnPoints, timestampMs);
        if (!point) return [];
        const rawValue = returnUnit === 'pct' ? (point.totalReturn == null ? null : point.totalReturn * 100) : point.pnlWithIncome;
        if (rawValue == null) return [];
        const value = returnDisplayValue(rawValue);
        return [buildTooltipRow(escapeHtml(modeLabels.aggregateReturn), escapeHtml(value), aggregateReturnColor())];
    }

    function buildValueTooltip(params: any[]): string {
        if (params.length === 0) return '';
        const theme = buildTooltipTheme(isDark);
        const rawDate = tooltipRawDate(params);
        const realParams = params.filter((param) => !isInternalTooltipSeries(param));
        const axisRows = realParams
            .map((param) => {
                const value = seriesValue(param);
                if (value == null) return null;
                return buildTooltipRow(escapeHtml(String(param.seriesName ?? '')), escapeHtml(formatCurrencyAmountPlain(value, currency)), typeof param.color === 'string' ? param.color : undefined);
            })
            .filter((row): row is string => row != null);

        if (axisRows.length === 0) return '';
        return `<div style="font-size:11px;color:${theme.textColor}">${buildTooltipBucketHeader(params, rawDate, theme)}${buildTooltipDivider(theme.border)}${axisRows.join('')}</div>`;
    }

    function buildReturnTooltip(params: any[]): string {
        if (params.length === 0) return '';
        const theme = buildTooltipTheme(isDark);
        const rawDate = tooltipRawDate(params);
        const timestamp = tooltipTimestamp(params);
        const realParams = params.filter((param) => !isInternalTooltipSeries(param));
        const excludedLotIds = new Set(realParams.map(returnTooltipLotId).filter((lotId): lotId is number => lotId != null));
        const blocks = realParams
            .map((param) => {
                const lotId = returnTooltipLotId(param);
                const lot = lotId == null ? null : visibleLots.find((item) => item.lotId === lotId);
                if (!lot) return null;
                const value = seriesValue(param);
                if (value == null) return null;
                const paramTimestamp = parseTimeMs(tooltipXValue(param));
                if (paramTimestamp == null) return null;

                const color = typeof param.color === 'string' ? param.color : lotColor(lot.lotId);
                const returnPoint = findPointAtOrBefore(returnPointsByLotId.get(lot.lotId) ?? [], paramTimestamp);
                const valuePoint = findPointAtOrBefore(valuePointsByLotId.get(lot.lotId) ?? [], paramTimestamp);
                if (returnUnit === 'pct' && (!returnPoint || returnPoint.totalReturn == null)) return null;
                if (returnUnit === 'abs' && !valuePoint) return null;

                const pointDate = (returnUnit === 'pct' ? returnPoint?.date : valuePoint?.date) ?? String(tooltipXValue(param));
                const exactValuePoint = valuePointByLotDate.get(pointKey(lot.lotId, pointDate)) ?? valuePoint;
                const headlineLabel = returnUnit === 'pct' ? modeLabels.totalReturn : modeLabels.totalPnl;
                const headlineValue = returnDisplayValue(value);
                const rows: string[] = [buildTooltipRow(escapeHtml(headlineLabel), escapeHtml(headlineValue), color)];

                if (returnPoint?.relativeReturn != null) {
                    rows.push(buildTooltipRow(escapeHtml(modeLabels.openReturn), escapeHtml(formatPercent(returnPoint.relativeReturn * 100))));
                }
                if (exactValuePoint) {
                    rows.push(buildTooltipRow(escapeHtml(modeLabels.residualValue), escapeHtml(formatCurrencyAmountPlain(exactValuePoint.openValue, currency))));
                    rows.push(buildTooltipRow(escapeHtml(modeLabels.saleProceeds), escapeHtml(formatCurrencyAmountPlain(exactValuePoint.proceeds, currency))));
                    rows.push(buildTooltipRow(escapeHtml(modeLabels.fifoPnl), `<span style="color:${exactValuePoint.pnl >= 0 ? (isDark ? '#4ade80' : '#16a34a') : isDark ? '#f87171' : '#dc2626'}">${escapeHtml(formatCurrencyAmountPlain(exactValuePoint.pnl, currency, {showSign: true}))}</span>`));
                }

                return `${buildTooltipHeader(escapeHtml(`${lot.label} · ${formatLongDate(pointDate)}`), theme.textColor)}${rows.join('')}`;
            })
            .filter((block): block is string => block != null);
        const aggregateRows = timestamp == null ? [] : buildAggregateReturnTooltipRows(timestamp);
        const individualRows = timestamp == null ? [] : buildReturnIndividualTooltipRows(timestamp, excludedLotIds);
        const tooltipBlocks = [...(aggregateRows.length > 0 ? [aggregateRows.join('')] : []), ...blocks, ...(individualRows.length > 0 ? [individualRows.join('')] : [])];

        if (tooltipBlocks.length === 0) return '';
        return `<div style="font-size:11px;color:${theme.textColor}">${buildTooltipBucketHeader(params, rawDate, theme)}${buildTooltipDivider(theme.border)}${tooltipBlocks.join(buildTooltipDivider(theme.border))}</div>`;
    }

    function buildValueSeries(): echarts.SeriesOption[] {
        const residualColor = isDark ? '#60a5fa' : '#2563eb';
        const proceedsColor = isDark ? '#34d399' : '#059669';
        const incomeColor = isDark ? '#a78bfa' : '#7c3aed';
        const originalCostColor = isDark ? '#cbd5e1' : '#475569';
        const estimatedValueColor = valueEstimatedLineColor();
        const residualLineColor = hasEstimatedAtCostLots ? estimatedValueColor : residualColor;
        const residualSeriesName = hasEstimatedAtCostLots ? modeLabels.residualValueEstimatedAtCost : modeLabels.residualValue;
        const aggregateTotalColor = hasEstimatedAtCostLots ? estimatedValueColor : isDark ? '#e2e8f0' : '#0f172a';
        const aggregateLineType = hasEstimatedAtCostLots ? 'dashed' : 'solid';
        const residualData = toChartSeriesPoints(aggregatedValuePoints.map((point) => lineDataPoint(point.date, point.openValue)).filter((point): point is LineDataPoint => point != null));
        const proceedsData = toChartSeriesPoints(aggregatedValuePoints.map((point) => lineDataPoint(point.date, point.proceeds)).filter((point): point is LineDataPoint => point != null));
        const incomeData = toChartSeriesPoints(aggregatedValuePoints.map((point) => lineDataPoint(point.date, point.income)).filter((point): point is LineDataPoint => point != null));
        const comprehensiveData = toChartSeriesPoints(aggregatedValuePoints.map((point) => lineDataPoint(point.date, point.openValue + point.proceeds + point.income)).filter((point): point is LineDataPoint => point != null));
        const openingData = toChartSeriesPoints(aggregatedValuePoints.map((point) => lineDataPoint(point.date, point.originalCost)).filter((point): point is LineDataPoint => point != null));

        const series: echarts.SeriesOption[] = [
            {
                id: 'value-residual',
                name: residualSeriesName,
                type: 'line',
                stack: 'value-aggregate',
                data: residualData,
                showSymbol: false,
                symbol: 'none',
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 1.8, color: residualLineColor, type: aggregateLineType},
                areaStyle: {color: withAlpha(residualLineColor, isDark ? 0.4 : 0.22)},
                itemStyle: {color: residualLineColor},
                emphasis: {scale: false, focus: 'none'},
                blur: {lineStyle: {opacity: 1}, itemStyle: {opacity: 1}, areaStyle: {opacity: isDark ? 0.4 : 0.22}},
                z: 3,
                zlevel: 0,
            },
            {
                id: 'value-proceeds',
                name: modeLabels.saleProceeds,
                type: 'line',
                stack: 'value-aggregate',
                data: proceedsData,
                showSymbol: false,
                symbol: 'none',
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 1.8, color: proceedsColor},
                areaStyle: {color: withAlpha(proceedsColor, isDark ? 0.42 : 0.26)},
                itemStyle: {color: proceedsColor},
                emphasis: {scale: false, focus: 'none'},
                blur: {lineStyle: {opacity: 1}, itemStyle: {opacity: 1}, areaStyle: {opacity: isDark ? 0.42 : 0.26}},
                z: 1,
                zlevel: 0,
            },
            {
                id: 'value-income',
                name: modeLabels.cumulativeIncome,
                type: 'line',
                stack: 'value-aggregate',
                data: incomeData,
                showSymbol: false,
                symbol: 'none',
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 1.8, color: incomeColor},
                areaStyle: {color: withAlpha(incomeColor, isDark ? 0.36 : 0.2)},
                itemStyle: {color: incomeColor},
                emphasis: {scale: false, focus: 'none'},
                blur: {lineStyle: {opacity: 1}, itemStyle: {opacity: 1}, areaStyle: {opacity: isDark ? 0.36 : 0.2}},
                z: 1,
                zlevel: 0,
            },
            {
                id: 'value-comprehensive',
                name: modeLabels.comprehensiveValue,
                type: 'line',
                data: comprehensiveData,
                showSymbol: false,
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 2.6, color: aggregateTotalColor, type: aggregateLineType},
                itemStyle: {color: aggregateTotalColor},
                emphasis: {scale: false, focus: 'none'},
                blur: {lineStyle: {opacity: 1}, itemStyle: {opacity: 1}},
                z: 5,
                zlevel: 0,
            },
            {
                id: 'value-opening',
                name: modeLabels.aggregateOpeningValue,
                type: 'line',
                data: openingData,
                showSymbol: false,
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 2.2, color: originalCostColor},
                itemStyle: {color: originalCostColor},
                emphasis: {scale: false, focus: 'none'},
                blur: {lineStyle: {opacity: 1}, itemStyle: {opacity: 1}},
                z: 4,
                zlevel: 0,
            },
        ];

        return attachIncomeMarkers(series);
    }

    function buildReturnSeries(): echarts.SeriesOption[] {
        const series: echarts.SeriesOption[] = [];

        if (showAggregateReturn) {
            const color = aggregateReturnColor();
            series.push({
                id: AGGREGATE_RETURN_SERIES_ID,
                name: returnSeriesName(modeLabels.aggregateReturn),
                type: 'line',
                data: toChartSeriesPoints(aggregateReturnSeriesPoints),
                showSymbol: false,
                symbol: 'none',
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 2.4, color},
                areaStyle: {color: withAlpha(color, isDark ? 0.18 : 0.14), origin: 0},
                itemStyle: {color},
                emphasis: {scale: false, focus: 'none'},
                blur: {lineStyle: {opacity: 1}, itemStyle: {opacity: 1}, areaStyle: {opacity: isDark ? 0.18 : 0.14}},
                z: 2,
                zlevel: 0,
            });
        }

        // Individual lot lines only when 2+ lots are plotted; with a single lot we show the
        // aggregate area alone (R7.5) so the shape reads the P&L from 0 instead of a lone flat line.
        if (activeReturnLotsWithData.length >= 2) {
            for (const lot of activeReturnLotsWithData) {
                const color = lotColor(lot.lotId);
                const data =
                    returnUnit === 'pct'
                        ? toChartSeriesPoints((returnPointsByLotId.get(lot.lotId) ?? []).map((point) => lineDataPoint(point.date, point.totalReturn == null ? null : point.totalReturn * 100)).filter((point): point is LineDataPoint => point != null))
                        : toChartSeriesPoints((valuePointsByLotId.get(lot.lotId) ?? []).map((point) => lineDataPoint(point.date, point.pnl + point.income)).filter((point): point is LineDataPoint => point != null));
                series.push({
                    id: `return-${lot.lotId}`,
                    name: returnSeriesName(lot.label),
                    type: 'line',
                    data,
                    showSymbol: false,
                    connectNulls: false,
                    smooth: false,
                    lineStyle: {width: 2.5, color},
                    itemStyle: {color},
                    emphasis: {scale: false, focus: 'none'},
                    tooltip: PER_LOT_LINE_TOOLTIP_OVERRIDE,
                    z: 6,
                    zlevel: 0,
                });
            }
        }

        return attachIncomeMarkers(series);
    }

    const plottedBaseSeries = $derived.by(() => ensureAxisTriggerAnchor(mode === 'value' ? buildValueSeries() : buildReturnSeries()));

    const autoYAxisRange = $derived.by(() => computeAutoYAxisRange(plottedBaseSeries));

    /** Position dots for return-mode per-lot lines at a hovered date (r3 fix5). */
    function buildPerLotHoverDotData(axisValueMs: number): Array<{value: [number, number]; itemStyle: {color: string}}> {
        const dots: Array<{value: [number, number]; itemStyle: {color: string}}> = [];
        if (mode !== 'return' || activeReturnLotsWithData.length < 2) return dots;

        for (const lot of activeReturnLotsWithData) {
            const y = returnValueForLotAt(lot.lotId, axisValueMs);
            if (y == null) continue;
            dots.push({value: [axisValueMs, y], itemStyle: {color: lotColor(lot.lotId)}});
        }
        return dots;
    }

    function emptyHoverDotsSeries(): echarts.SeriesOption {
        return {
            id: PER_LOT_HOVER_DOTS_ID,
            name: PER_LOT_HOVER_DOTS_ID,
            type: 'scatter',
            data: [],
            symbol: 'circle',
            symbolSize: 9,
            silent: true,
            tooltip: {show: false},
            animation: false,
            legendHoverLink: false,
            itemStyle: {borderColor: isDark ? '#0f172a' : '#ffffff', borderWidth: 1.5},
            emphasis: {disabled: true},
            z: 12,
            zlevel: 0,
        };
    }

    function updateHoverDots(axisValueMs: number | null): void {
        if (!chartInstance) return;
        if (axisValueMs === lastHoverDotAxisValue) return;
        lastHoverDotAxisValue = axisValueMs;
        const data = axisValueMs == null ? [] : buildPerLotHoverDotData(axisValueMs);
        chartInstance.setOption({series: [{id: PER_LOT_HOVER_DOTS_ID, data}]});
    }

    function handleUpdateAxisPointer(event: any): void {
        const axesInfo = Array.isArray(event?.axesInfo) ? event.axesInfo : [];
        const xInfo = axesInfo.find((info: any) => info?.axisDim === 'x');
        const rawValue = xInfo?.value;
        const axisValueMs = typeof rawValue === 'number' ? rawValue : parseTimeMs(rawValue);
        updateHoverDots(axisValueMs);
    }

    function handleChartGlobalOut(): void {
        updateHoverDots(null);
    }

    function buildOption(): echarts.EChartsOption | null {
        if (emptyMessage) return null;
        syncInitialResolution();

        const theme = buildTooltipTheme(isDark);
        const gridColors = buildGridColors(isDark);
        const baseSeries = plottedBaseSeries;
        const legendData = baseSeries.map((item) => (item as {name?: unknown}).name).filter((name): name is string => typeof name === 'string' && name !== AXIS_TRIGGER_ANCHOR_ID && name !== PER_LOT_HOVER_DOTS_ID && name !== LOT_INCOME_MARKER_SERIES_ID);
        const axisFallbackRange = seriesDataDateRange(baseSeries);
        const axisDateRange = xAxisRange ?? (axisFallbackRange ? {min: axisFallbackRange[0], max: axisFallbackRange[1]} : null);
        const multiYearAxis = !!axisDateRange && new Date(axisDateRange.min).getFullYear() !== new Date(axisDateRange.max).getFullYear();
        return {
            ...CHART_ANIMATION_CONFIG,
            grid: {
                top: 62,
                right: 18,
                bottom: 34,
                left: 24,
                containLabel: true,
            },
            legend: {
                show: true,
                type: 'scroll',
                data: legendData,
                top: 4,
                left: 'center',
                right: 8,
                itemWidth: 10,
                itemHeight: 10,
                itemGap: 12,
                pageIconColor: gridColors.textColor,
                pageTextStyle: {color: gridColors.textColor},
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
                    snap: false,
                    lineStyle: {color: gridColors.gridColor, width: 1},
                },
                formatter: (params: any) => {
                    const items = Array.isArray(params) ? params : [params];
                    if (mode === 'value') return buildValueTooltip(items);
                    return buildReturnTooltip(items);
                },
            },
            xAxis: {
                type: 'time',
                ...(xAxisRange ? {min: xAxisRange.min, max: xAxisRange.max} : {}),
                axisLine: {lineStyle: {color: gridColors.gridColor}},
                axisTick: {show: false},
                splitLine: {show: false},
                axisLabel: {
                    color: gridColors.textColor,
                    hideOverlap: true,
                    formatter: (value: number) => formatAxisDate($currentLanguage, value, multiYearAxis),
                },
            },
            yAxis: {
                type: 'value',
                ...(mode === 'value' && valueYFromZero
                    ? {min: 0, scale: false}
                    : mode === 'return' && returnYFromZero
                      ? {min: (v: {min: number}) => Math.min(0, v.min), max: (v: {max: number}) => Math.max(0, v.max), scale: true}
                      : autoYAxisRange
                        ? {min: autoYAxisRange.min, max: autoYAxisRange.max, scale: true}
                        : {scale: true}),
                axisLine: {show: false},
                axisTick: {show: false},
                splitLine: {lineStyle: {color: gridColors.gridColor}},
                axisLabel: {
                    color: gridColors.textColor,
                    formatter: (value: number) => (mode === 'return' ? (returnUnit === 'pct' ? formatAxisPercent(value) : formatAxisCurrency(value)) : formatAxisNumber(value)),
                },
            },
            series: [...baseSeries, emptyHoverDotsSeries()],
            dataZoom: buildDataZoom([0]).map((zoom) => (zoomWindow ? {...zoom, start: zoomWindow.start, end: zoomWindow.end} : zoom)),
        };
    }

    function resetResizeObserverState() {
        if (resizeAnimationFrame != null) {
            cancelAnimationFrame(resizeAnimationFrame);
            resizeAnimationFrame = null;
        }
        lastObservedChartSize = null;
    }

    function setupResizeObserver() {
        if (!chartContainer || resizeObserver) return;
        resizeObserver = new ResizeObserver((entries) => {
            const entry = entries[0];
            if (!entry) return;

            const width = Math.round(entry.contentRect.width * 100) / 100;
            const height = Math.round(entry.contentRect.height * 100) / 100;
            if (width <= 0 || height <= 0) return;
            if (lastObservedChartSize && Math.abs(lastObservedChartSize.width - width) < 0.5 && Math.abs(lastObservedChartSize.height - height) < 0.5) return;

            lastObservedChartSize = {width, height};
            if (resizeAnimationFrame != null) return;

            resizeAnimationFrame = requestAnimationFrame(() => {
                resizeAnimationFrame = null;
                if (!chartInstance || !lastObservedChartSize) return;
                chartInstance.resize(lastObservedChartSize);
                scheduleResolutionSync();
            });
        });
        resizeObserver.observe(chartContainer);
    }

    function renderChart() {
        if (!chartContainer) return;

        syncTheme();

        if (chartInstance && chartInstance.getDom() !== chartContainer) {
            tooltipCleanup?.();
            resizeObserver?.disconnect();
            resizeObserver = null;
            resetResizeObserverState();
            dataZoomTouchPanHandle?.dispose();
            dataZoomTouchPanHandle = null;
            chartInstance.off('datazoom', handleDataZoom);
            chartInstance.off('updateAxisPointer', handleUpdateAxisPointer);
            chartInstance.getZr()?.off('globalout', handleChartGlobalOut);
            chartInstance.dispose();
            chartInstance = undefined;
        }

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
            attachChartReady(chartInstance, chartContainer, 'lot-comparison');
            needsInitialLayoutStabilityPass = true;
            setupResizeObserver();
            tooltipCleanup?.();
            tooltipCleanup = setupTooltipAutoHide(chartContainer, () => chartInstance);
            dataZoomTouchPanHandle = attachDataZoomTouchPan(chartInstance, chartContainer);
            chartInstance.on('datazoom', handleDataZoom);
            chartInstance.on('updateAxisPointer', handleUpdateAxisPointer);
            chartInstance.getZr().on('globalout', handleChartGlobalOut);
        }

        lastHoverDotAxisValue = null;
        const option = buildOption();
        if (!option) {
            chartInstance.clear();
            return;
        }

        chartInstance.setOption(option, LOT_COMPARISON_SET_OPTION_OPTS);
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
            resetResizeObserverState();
            dataZoomTouchPanHandle?.dispose();
            dataZoomTouchPanHandle = null;
            if (resolutionDebounceTimer) clearTimeout(resolutionDebounceTimer);
            resolutionDebounceTimer = null;
            chartInstance?.off('datazoom', handleDataZoom);
            chartInstance?.off('updateAxisPointer', handleUpdateAxisPointer);
            chartInstance?.getZr()?.off('globalout', handleChartGlobalOut);
            chartInstance?.dispose();
        };
    });

    $effect(() => {
        void selectedLots;
        void valueHistory;
        void returnHistory;
        void brokers;
        void currency;
        void incomeEvents;
        void mode;
        void valueYFromZero;
        void returnYFromZero;
        void returnUnit;
        void currentResolution;
        void xAxisRange;
        void lotModels;
        void visibleLots;
        void hasEstimatedAtCostLots;
        void incomeMarkerEvents;
        void valuePointsByLotId;
        void aggregatedValuePoints;
        void returnPointsByLotId;
        void lotOpeningValueById;
        void returnAbsLotsWithData;
        void returnPctLotsWithData;
        void returnPctUndefinedLots;
        void activeReturnLotsWithData;
        void aggregateReturnPoints;
        void aggregateReturnSeriesPoints;
        void showAggregateReturn;
        void plottedBaseSeries;
        void autoYAxisRange;
        void resolutionSourceDates;
        void resolutionSourceSignature;
        void emptyMessage;
        void $currentLanguage;

        if (resolutionSourceSignature !== lastResolutionSourceSignature) {
            lastResolutionSourceSignature = resolutionSourceSignature;
            resetResolutionState();
        }

        if (!chartContainer) return;

        tick().then(() => {
            renderChart();
        });
    });
</script>

<div class="flex w-full flex-col gap-3 rounded-xl border border-gray-100 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800" data-testid="lot-comparison-chart">
    <div class="flex flex-wrap items-center justify-between gap-3">
        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-200">
            {chartTitle}
        </h3>

        <div class="ml-auto flex w-full flex-col items-end gap-2 sm:w-auto sm:flex-row sm:flex-wrap sm:items-center">
            <div class="order-last flex flex-wrap items-center justify-end gap-2 sm:order-none">
                {#if mode === 'value'}
                    <div class="flex overflow-hidden rounded-lg border border-gray-200 text-xs font-medium dark:border-slate-600" data-testid="lot-comparison-value-yaxis-toggle">
                        <button
                            type="button"
                            class="px-3 py-1 transition-colors {!valueYFromZero ? 'bg-libre-green text-white' : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-400 dark:hover:bg-slate-700'}"
                            onclick={() => (valueYFromZero = false)}
                            aria-pressed={!valueYFromZero}
                            data-testid="lot-comparison-value-yaxis-auto"
                        >
                            {modeLabels.yAuto}
                        </button>
                        <button
                            type="button"
                            class="border-l border-gray-200 px-3 py-1 transition-colors dark:border-slate-600 {valueYFromZero ? 'bg-libre-green text-white' : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-400 dark:hover:bg-slate-700'}"
                            onclick={() => (valueYFromZero = true)}
                            aria-pressed={valueYFromZero}
                            data-testid="lot-comparison-value-yaxis-zero"
                        >
                            {modeLabels.yFromZero}
                        </button>
                    </div>
                {:else}
                    <div class="flex overflow-hidden rounded-lg border border-gray-200 text-xs font-medium dark:border-slate-600" data-testid="lot-comparison-return-abs-pct-toggle">
                        <button
                            type="button"
                            class="px-3 py-1 transition-colors {returnUnit === 'abs' ? 'bg-libre-green text-white' : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-400 dark:hover:bg-slate-700'}"
                            onclick={() => (returnUnit = 'abs')}
                            aria-pressed={returnUnit === 'abs'}
                            data-testid="lot-comparison-return-abs"
                        >
                            {modeLabels.returnUnitAbs}
                        </button>
                        <button
                            type="button"
                            class="border-l border-gray-200 px-3 py-1 transition-colors dark:border-slate-600 {returnUnit === 'pct' ? 'bg-libre-green text-white' : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-400 dark:hover:bg-slate-700'}"
                            onclick={() => (returnUnit = 'pct')}
                            aria-pressed={returnUnit === 'pct'}
                            data-testid="lot-comparison-return-pct"
                        >
                            {modeLabels.returnUnitPercent}
                        </button>
                    </div>

                    <div class="flex overflow-hidden rounded-lg border border-gray-200 text-xs font-medium dark:border-slate-600" data-testid="lot-comparison-return-yaxis-toggle">
                        <button
                            type="button"
                            class="px-3 py-1 transition-colors {!returnYFromZero ? 'bg-libre-green text-white' : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-400 dark:hover:bg-slate-700'}"
                            onclick={() => (returnYFromZero = false)}
                            aria-pressed={!returnYFromZero}
                            data-testid="lot-comparison-return-yaxis-auto"
                        >
                            {modeLabels.yAuto}
                        </button>
                        <button
                            type="button"
                            class="border-l border-gray-200 px-3 py-1 transition-colors dark:border-slate-600 {returnYFromZero ? 'bg-libre-green text-white' : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-400 dark:hover:bg-slate-700'}"
                            onclick={() => (returnYFromZero = true)}
                            aria-pressed={returnYFromZero}
                            data-testid="lot-comparison-return-yaxis-zero"
                        >
                            {modeLabels.yFromZero}
                        </button>
                    </div>
                {/if}
            </div>

            <div class="order-first flex overflow-hidden rounded-lg border border-gray-200 text-xs font-medium dark:border-slate-600 sm:order-none" data-testid="lot-comparison-mode-toggle">
                <button
                    type="button"
                    class="px-3 py-1 transition-colors {mode === 'value' ? 'bg-libre-green text-white' : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-400 dark:hover:bg-slate-700'}"
                    onclick={() => (mode = 'value')}
                    aria-pressed={mode === 'value'}
                    data-testid="lot-comparison-mode-value"
                >
                    {modeLabels.value}
                </button>
                <button
                    type="button"
                    class="border-l border-gray-200 px-3 py-1 transition-colors dark:border-slate-600 {mode === 'return' ? 'bg-libre-green text-white' : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-400 dark:hover:bg-slate-700'}"
                    onclick={() => (mode = 'return')}
                    aria-pressed={mode === 'return'}
                    data-testid="lot-comparison-mode-return"
                >
                    {modeLabels.return}
                </button>
            </div>
        </div>
    </div>

    {#if selectedLots.length === 0}
        <div class="flex h-80 items-center justify-center rounded-lg border border-dashed border-gray-200 px-6 text-center text-sm text-gray-500 dark:border-slate-600 dark:text-gray-400" data-testid="lot-comparison-empty">
            {modeLabels.selectLots}
        </div>
    {:else}
        <div class="relative h-80 w-full">
            <div class="pointer-events-none absolute left-2 top-2 z-10">
                <ResolutionBadge resolution={currentResolution} />
            </div>
            {#if emptyMessage}
                <div class="absolute inset-0 z-10 flex items-center justify-center text-center text-sm text-gray-400 dark:text-gray-500">
                    {emptyMessage}
                </div>
            {/if}

            <div bind:this={chartContainer} class="h-full w-full" class:invisible={!!emptyMessage} data-testid="lot-comparison-echart"></div>
        </div>
        {#if mode === 'value' && hasEstimatedAtCostLots}
            <p class="flex items-center gap-2 text-[11px] text-slate-500 dark:text-slate-400" data-testid="lot-comparison-estimated-at-cost-legend">
                <span class="h-0 w-8 border-t border-dashed border-slate-500 dark:border-slate-400"></span>
                <span>{modeLabels.estimatedAtCostLegend}</span>
            </p>
        {/if}
    {/if}
</div>
