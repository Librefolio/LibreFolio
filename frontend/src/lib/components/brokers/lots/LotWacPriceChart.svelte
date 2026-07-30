<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {z} from 'zod';
    import {schemas} from '$lib/api';
    import {_} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import {CHART_ANIMATION_CONFIG, CHART_SET_OPTION_OPTS, namedPoint} from '$lib/components/charts/echartsAnimationConfig';
    import {buildDataZoom} from '$lib/components/charts/chartCoreHelpers';
    import ResolutionBadge from '$lib/components/charts/ResolutionBadge.svelte';
    import {aggregateLineSeries, cascadeResolution, chooseInitialResolution, computeDensity, mapDateToBucket, type ChartResolution} from '$lib/components/charts/timeSeriesAggregation';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import {attachDataZoomSync, type DataZoomSyncHandle} from '$lib/components/charts/echartsDataZoomSync';
    import {attachDataZoomTouchPan, type DataZoomTouchPanHandle} from '$lib/components/charts/echartsDataZoomTouchPan';
    import {buildGridColors, buildTooltipDivider, buildTooltipHeader, buildTooltipRow, buildTooltipTheme, scheduleFirstRenderStabilityFix, setupTooltipAutoHide, tooltipPositionSide} from '$lib/components/charts/echartsTooltipHelpers';
    import {getBrokerColor, type BrokerLike} from '$lib/utils/broker/brokerColors';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {lotDisplayState, lotStateColor, lotStateSymbol, type LotDisplayState} from './lotStateVisual';

    type BrokerWACHistoryPoint = z.infer<typeof schemas.BrokerWACHistoryPoint>;
    type CumulativeWACHistoryPoint = z.infer<typeof schemas.CumulativeWACHistoryPoint>;
    type LotPriceHistoryPoint = z.infer<typeof schemas.LotPriceHistoryPoint>;
    type LotTimelineEventSchema = z.infer<typeof schemas.LotTimelineEventSchema>;
    type LotSummarySchema = z.infer<typeof schemas.LotSummarySchema>;
    type DisplayMode = 'absolute' | 'percentage';
    type EventMarkerSeriesKind = 'buy' | 'sell' | 'transfer' | 'adjustment' | 'split';

    // Bidirectional "back-and-forth" arrow (custom path renders identically in chart + legend,
    // unlike a rotated built-in which the legend icon ignores).
    const TRANSFER_MARKER_SYMBOL = 'path://M1 10 L6 5 L6 8 L14 8 L14 5 L19 10 L14 15 L14 12 L6 12 L6 15 Z';
    // Buy ▲ / Sell ▽ as explicit mirrored paths: the ECharts legend icon ignores `symbolRotate`,
    // so a rotated built-in triangle would show upward in the legend for BOTH buy and sell.
    const BUY_MARKER_SYMBOL = 'path://M0 17 L20 17 L10 0 Z';
    const SELL_MARKER_SYMBOL = 'path://M0 0 L20 0 L10 17 Z';
    const SPLIT_MARKER_SYMBOL = 'diamond';
    const MARKER_VERTICAL_OFFSET_STEP = 12;
    // Per-lot performance bubbles (plan v3 round-2 §5/§6): opening-marker overlay migrated here from
    // the removed LotPerformanceBubbleChart. Radius scales sqrt-proportionally to a per-mode metric
    // (ABS→open_quantity, %→opening value) between these bounds.
    const LOT_BUBBLE_MIN_RADIUS = 7;
    const LOT_BUBBLE_MAX_RADIUS = 22;
    const LOT_BUBBLE_ZERO_EPS = 0.0005;
    // Income (dividend/interest) "|" markers share this series id so the ECharts series stays stable.
    const LOT_INCOME_MARKER_SERIES_ID = 'lot-income-markers';
    // Fixed (non-containLabel) grid bounds shared byte-for-byte with LotGanttChart.svelte so the
    // two charts' X axes are pixel-perfect aligned regardless of how wide either chart's Y-axis
    // labels happen to be (containLabel:true would make that alignment drift with content).
    const GRID_TOP_PX = 62;
    const GRID_LEFT_PX = 56;
    const GRID_RIGHT_PX = 18;
    const GRID_BOTTOM_PX = 34;
    const MARKER_CATEGORY_ORDER: Record<EventMarkerSeriesKind, number> = {
        buy: 0,
        sell: 1,
        transfer: 2,
        adjustment: 3,
        split: 4,
    };

    type ComponentProps = {
        brokerWacHistory: BrokerWACHistoryPoint[];
        cumulativeWacHistory: CumulativeWACHistoryPoint[];
        priceHistory: LotPriceHistoryPoint[];
        lotEvents: LotTimelineEventSchema[];
        /** Lots to overlay as per-lot performance bubbles (plan v3 round-2). Only LONG lots are drawn. */
        lots?: LotSummarySchema[];
        /** Implicit selection (plan v3 §13): empty = all visible lots; otherwise only these are highlighted. */
        selectedLotIds?: number[];
        /** Asset-linked DIVIDEND/INTEREST transactions (plan v3 §11): rendered as dashed vertical
         * markers on the date of the income transaction. */
        incomeEvents?: ReadonlyArray<LotIncomeEvent>;
        brokers: ReadonlyArray<BrokerLike>;
        currency: string;
        /** Asset quote_base_quantity (e.g. 100 for bonds priced per 100 nominal). Used to rescale the
         * per-single-unit WAC / opening_unit_price (cost ÷ raw quantity) UP to the per-quote market
         * scale that price_history.close uses, so cost lines/bubbles align with the market line.
         * Defaults to 1 (no-op for stocks). */
        quoteBaseQuantity?: number;
        xAxisRange?: {min: string; max: string} | null;
        onZoomChange?: (start: number, end: number) => void;
        externalZoomStart?: number | null;
        externalZoomEnd?: number | null;
        onRangeComputed?: (min: string, max: string) => void;
        onLoadingChange?: (loading: boolean) => void;
        /** Double-click on an event marker (BUY/SELL/TRANSFER/SPLIT/ADJUSTMENT) — plan v3 §9. */
        onEventDoubleClick?: (event: LotTimelineEventSchema) => void;
        /** Click on a performance bubble toggles that lot's selection (plan v3 §13). */
        onSelectionChange?: (ids: number[]) => void;
    };

    /** Local mirror of LotComparisonChart's LotIncomeEvent — shape matches the LotIncomeEventSchema DTO. */
    type LotIncomeEvent = {
        type: 'DIVIDEND' | 'INTEREST';
        date: string;
        broker_id: number | null;
        amount: string;
        lot_ids: number[];
    };

    interface ValuePoint {
        date: string;
        absolute: number | null;
        percent: number | null;
    }

    type ValueKey = 'absolute' | 'percent';

    interface LogicalRange {
        startDate: string;
        endDate: string;
    }

    interface BrokerSeries {
        brokerId: number | null;
        name: string;
        isCombined: boolean;
        points: ValuePoint[];
        hasAbsoluteData: boolean;
        hasPercentData: boolean;
    }

    interface MarketPriceLookupPoint {
        date: string;
        absolute: number;
        percent: number | null;
    }

    interface EventMarkerDatum {
        id: string;
        date: string;
        absolute: number;
        percent: number | null;
        category: EventMarkerSeriesKind;
        event: LotTimelineEventSchema;
        transferDepartDate: string | null;
        transferArriveDate: string | null;
        verticalOffsetPx: number;
    }

    interface EventStateSnapshot {
        quantityBefore: number | null;
        quantityAfter: number | null;
        unitPriceBefore: number | null;
        unitPriceAfter: number | null;
    }

    interface LotEventState {
        quantity: number | null;
        unitPrice: number | null;
    }

    interface EventMarkerSeries {
        category: EventMarkerSeriesKind;
        points: EventMarkerDatum[];
    }

    interface MarkerSeriesDefinition {
        key: EventMarkerSeriesKind;
        label: string;
        symbol: string;
        symbolSize: number;
        /** Optional rotation in degrees, e.g. 180 to turn the BUY up-triangle into a SELL down-triangle. */
        symbolRotate?: number;
        color: string;
    }

    let {
        brokerWacHistory = [],
        cumulativeWacHistory = [],
        priceHistory = [],
        lotEvents = [],
        lots = [],
        selectedLotIds = [],
        incomeEvents = [],
        brokers = [],
        currency,
        quoteBaseQuantity = 1,
        xAxisRange = null,
        onZoomChange,
        externalZoomStart = null,
        externalZoomEnd = null,
        onRangeComputed,
        onLoadingChange,
        onEventDoubleClick,
        onSelectionChange,
    }: ComponentProps = $props();

    let displayMode = $state<DisplayMode>('absolute');
    // #3: absolute Y axis — automatic (data-fit) or anchored at 0. Mirrors the LotComparisonChart
    // value toggle and prevents the percentage-mode 0-clamp from leaking into abs on toggle-back.
    let absYFromZero = $state(false);
    let wrapperEl: HTMLDivElement | undefined = $state(undefined);
    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | undefined = undefined;
    let resizeObserver: ResizeObserver | null = null;
    let darkModeObserver: MutationObserver | null = null;
    let pulseTimers: ReturnType<typeof setTimeout>[] = [];

    /** Public: briefly pulse (highlight → downplay, cycled ×3) the bubble for the given lot so clicking a
     * data-quality warning row draws the eye to the matching bubble. Scrolls the chart into view first.
     * No-op if the lot has no bubble (filtered out, or price-less with a null return). */
    export function pulseLot(lotId: number): void {
        wrapperEl?.scrollIntoView({behavior: 'smooth', block: 'nearest'});
        if (!chartInstance) return;
        const dataIndex = buildRenderableLotBubbles().findIndex((entry) => entry.point.lotId === lotId);
        if (dataIndex < 0) return;
        for (const timer of pulseTimers) clearTimeout(timer);
        pulseTimers = [];
        for (let cycle = 0; cycle < 3; cycle += 1) {
            pulseTimers.push(setTimeout(() => chartInstance?.dispatchAction({type: 'highlight', seriesId: 'lot-performance-bubbles', dataIndex}), cycle * 440));
            pulseTimers.push(setTimeout(() => chartInstance?.dispatchAction({type: 'downplay', seriesId: 'lot-performance-bubbles', dataIndex}), cycle * 440 + 220));
        }
    }
    let tooltipCleanup: (() => void) | null = null;
    let dataZoomTouchPanHandle: DataZoomTouchPanHandle | null = null;
    let dataZoomSyncHandle: DataZoomSyncHandle | null = null;
    let isDark = $state(false);
    let needsInitialLayoutStabilityPass = false;
    let currentResolution: ChartResolution = $state('daily');
    let shouldPickInitialResolution = true;
    let resolutionDebounceTimer: ReturnType<typeof setTimeout> | null = null;
    let dataZoomResolutionCleanup: (() => void) | null = null;
    let lastResolutionInputRefs: [BrokerWACHistoryPoint[], CumulativeWACHistoryPoint[], LotPriceHistoryPoint[]] | null = null;

    function escapeHtml(value: string): string {
        return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function translatedOr(key: string, fallback: string): string {
        const translated = $_(key);
        return !translated || translated === key ? fallback : translated;
    }

    function safeScalar<T>(value: T | Array<T | null> | null | undefined): T | null {
        if (Array.isArray(value)) return value[0] ?? null;
        return value ?? null;
    }

    function safeString(value: string | Array<string | null> | null | undefined): string | null {
        return safeScalar(value);
    }

    function safeInt(value: number | Array<number | null> | null | undefined): number | null {
        return safeScalar(value);
    }

    function parseNumber(value: string | number | Array<string | number | null> | null | undefined): number | null {
        const raw = safeScalar(value);
        if (raw == null) return null;
        const parsed = typeof raw === 'number' ? raw : Number.parseFloat(raw);
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

    function formatShortDate(value: number | string, withYear = false): string {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return String(value);
        return date.toLocaleDateString($currentLanguage || undefined, withYear ? {year: 'numeric', month: 'short', day: 'numeric'} : {month: 'short', day: 'numeric'});
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

    function sortDates(a: string, b: string): number {
        return a.localeCompare(b);
    }

    const lineSeriesDates = $derived.by(() => {
        const dateSet = new Set<string>();
        for (const point of brokerWacHistory) dateSet.add(point.date);
        for (const point of cumulativeWacHistory) dateSet.add(point.date);
        for (const point of priceHistory) dateSet.add(point.date);
        return Array.from(dateSet).sort(sortDates);
    });

    function nullifyZeroWac(wac: number | null, poolQty: number | null): number | null {
        if (wac == null) return null;
        return wac === 0 || poolQty === 0 ? null : wac;
    }

    /** Positive quote_base_quantity scale factor (1 for stocks, e.g. 100 for bonds priced per 100
     * nominal). */
    const qbqScale = $derived(quoteBaseQuantity > 0 ? quoteBaseQuantity : 1);

    /** Rescale a per-single-unit price (WAC / opening_unit_price = cost ÷ raw quantity) up to the
     * per-quote_base_quantity market scale that price_history.close uses (e.g. ×100 → bond par ≈ 100),
     * so cost lines, bubbles and the market line share one ABS price axis. No-op for qbq=1 (stocks).
     * In % mode the constant factor cancels in the first-value normalisation, so callers may apply it
     * unconditionally. */
    function scaleUnitPrice(value: number | null): number | null {
        return value == null ? null : value * qbqScale;
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

    function brokerName(brokerId: number | null): string {
        if (brokerId == null) return '—';
        return brokers.find((broker) => broker.id === brokerId)?.name ?? `Broker ${brokerId}`;
    }

    function buildBrokerSeries(brokerId: number | null, points: Array<{date: string; value: number | null}>): BrokerSeries {
        const valuePoints = toPercentSeries([...points].sort((a, b) => sortDates(a.date, b.date)));
        return {
            brokerId,
            name: brokerId == null ? labels.combined : brokerName(brokerId),
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

    function resetResolutionIfInputsChanged() {
        const refs: [BrokerWACHistoryPoint[], CumulativeWACHistoryPoint[], LotPriceHistoryPoint[]] = [brokerWacHistory, cumulativeWacHistory, priceHistory];
        if (lastResolutionInputRefs && refs.every((ref, index) => ref === lastResolutionInputRefs?.[index])) return;

        lastResolutionInputRefs = refs;
        currentResolution = 'daily';
        shouldPickInitialResolution = true;
    }

    function isoDateToUtcMs(date: string): number {
        const [year, month, day] = date.split('-').map(Number);
        if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) return Number.NaN;
        return Date.UTC(year, month - 1, day);
    }

    function utcMsToIsoDate(ms: number): string {
        const date = new Date(ms);
        const year = date.getUTCFullYear();
        const month = String(date.getUTCMonth() + 1).padStart(2, '0');
        const day = String(date.getUTCDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function getFullLineRange(): LogicalRange | null {
        if (lineSeriesDates.length === 0) return null;
        return {
            startDate: lineSeriesDates[0],
            endDate: lineSeriesDates[lineSeriesDates.length - 1],
        };
    }

    function getXAxisBounds(): {min: string; max: string} | null {
        const min = xAxisRange?.min ?? groupedChartData.minDate ?? lineSeriesDates[0] ?? null;
        const max = xAxisRange?.max ?? groupedChartData.maxDate ?? lineSeriesDates[lineSeriesDates.length - 1] ?? null;
        if (!min || !max) return null;
        return min <= max ? {min, max} : {min: max, max: min};
    }

    /** Extend the x-domain horizontally by the largest bubble radius so lots opened on the first/last
     * date don't spill past — and get clipped at (series use clip:true) — the plot edges. Mirrors the
     * vertical bubble padding already applied to the y-axis (computeAutoYAxisBounds). The pixel radius
     * is converted into a time delta via the current plot width; because ECharts maps the padded
     * [min,max] linearly across the plot, the span cancels out and each side reserves exactly
     * maxBubbleRadius px regardless of how wide the date range is. Applied to the axis display bounds
     * only (not getXAxisBounds, which drives zoom/bucketing). No-op without bubbles or a real span. */
    function padXBoundsForBubbles(bounds: {min: string; max: string} | null): {min: string; max: string} | null {
        if (!bounds) return bounds;
        const maxBubbleRadius = Math.max(0, ...buildRenderableLotBubbles().map((entry) => entry.radius));
        if (maxBubbleRadius <= 0) return bounds;
        const minMs = new Date(bounds.min).getTime();
        const maxMs = new Date(bounds.max).getTime();
        if (!Number.isFinite(minMs) || !Number.isFinite(maxMs) || maxMs <= minMs) return bounds;
        const plotWidth = Math.max(1, (chartContainer?.clientWidth ?? 640) - GRID_LEFT_PX - GRID_RIGHT_PX);
        const edgeFraction = Math.min(0.3, maxBubbleRadius / plotWidth);
        const padMs = ((maxMs - minMs) * edgeFraction) / Math.max(0.1, 1 - 2 * edgeFraction);
        return {min: new Date(minMs - padMs).toISOString(), max: new Date(maxMs + padMs).toISOString()};
    }

    function getAxisLogicalRange(): LogicalRange | null {
        const bounds = getXAxisBounds();
        return bounds ? {startDate: bounds.min, endDate: bounds.max} : getFullLineRange();
    }

    function getPlotWidthPx(): number {
        if (!chartInstance) return 1;
        return Math.max(chartInstance.getWidth() - GRID_LEFT_PX - GRID_RIGHT_PX, 1);
    }

    function computeLineBucketCounts(range: LogicalRange): {dailyCount: number; weeklyCount: number; monthlyCount: number} {
        let dailyCount = 0;
        const weekly = new Set<string>();
        const monthly = new Set<string>();

        for (const date of lineSeriesDates) {
            if (date < range.startDate || date > range.endDate) continue;
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
            const start = typeof zoom?.start === 'number' ? zoom.start : 0;
            const end = typeof zoom?.end === 'number' ? zoom.end : 100;
            return {
                start: Math.min(100, Math.max(0, start)),
                end: Math.min(100, Math.max(0, end)),
            };
        } catch (_) {
            return {start: 0, end: 100};
        }
    }

    function getVisibleLogicalRangeFromChart(): LogicalRange | null {
        const axisRange = getAxisLogicalRange();
        if (!axisRange) return null;

        const minMs = isoDateToUtcMs(axisRange.startDate);
        const maxMs = isoDateToUtcMs(axisRange.endDate);
        if (!Number.isFinite(minMs) || !Number.isFinite(maxMs) || maxMs <= minMs) return axisRange;

        const zoom = getZoomPercent();
        const startPercent = Math.min(zoom.start, zoom.end);
        const endPercent = Math.max(zoom.start, zoom.end);
        const spanMs = maxMs - minMs;

        return {
            startDate: utcMsToIsoDate(minMs + spanMs * (startPercent / 100)),
            endDate: utcMsToIsoDate(minMs + spanMs * (endPercent / 100)),
        };
    }

    function pickInitialResolution() {
        if (!shouldPickInitialResolution) return;
        shouldPickInitialResolution = false;

        const fullRange = getFullLineRange();
        if (!fullRange) {
            currentResolution = 'daily';
            return;
        }

        const counts = computeLineBucketCounts(fullRange);
        const plotWidthPx = getPlotWidthPx();
        currentResolution = computeDensity(counts.dailyCount, plotWidthPx) === 0 ? 'daily' : chooseInitialResolution(counts, plotWidthPx);
    }

    function syncResolutionToViewport() {
        if (!chartInstance || lineSeriesDates.length === 0) return;

        const range = getVisibleLogicalRangeFromChart() ?? getFullLineRange();
        if (!range) return;

        const counts = computeLineBucketCounts(range);
        const plotWidthPx = getPlotWidthPx();
        if (computeDensity(counts.dailyCount, plotWidthPx) === 0) return;

        const nextResolution = cascadeResolution(currentResolution, counts, plotWidthPx);
        if (nextResolution === currentResolution) return;

        currentResolution = nextResolution;
        chartInstance.dispatchAction({type: 'hideTip'});
        renderChart({animate: false});
    }

    function scheduleResolutionSync() {
        if (resolutionDebounceTimer) clearTimeout(resolutionDebounceTimer);
        resolutionDebounceTimer = setTimeout(() => {
            resolutionDebounceTimer = null;
            syncResolutionToViewport();
        }, 200);
    }

    function aggregateValuePoints(points: ValuePoint[], valueKey: ValueKey): ReturnType<typeof namedPoint>[] {
        const source: LineDataPoint[] = points.map((point) => ({
            date: point.date,
            value: point[valueKey] ?? Number.NaN,
        }));
        return aggregateLineSeries(source, currentResolution).map((point) => namedPoint(point.date, Number.isFinite(point.value) ? point.value : null));
    }

    function computeAutoYAxisBounds(valueKey: ValueKey): {min: number; max: number} | null {
        const values: number[] = [];
        const collectValues = (points: ValuePoint[]) => {
            for (const point of aggregateValuePoints(points, valueKey)) {
                const value = point.value[1];
                if (value == null || value === 0 || !Number.isFinite(value)) continue;
                values.push(value);
            }
        };

        for (const brokerSeries of groupedChartData.realSeries) {
            if (brokerSeries.points.some((point) => point[valueKey] != null)) collectValues(brokerSeries.points);
        }
        if (groupedChartData.combinedSeries?.points.some((point) => point[valueKey] != null)) collectValues(groupedChartData.combinedSeries.points);
        if (groupedChartData.marketPricePoints.some((point) => point[valueKey] != null)) collectValues(groupedChartData.marketPricePoints);

        const bubbles = buildRenderableLotBubbles();
        values.push(...bubbles.map((entry) => entry.yValue));
        if (valueKey === 'percent' || absYFromZero) values.push(0);

        if (values.length === 0) return null;
        const min = Math.min(...values);
        const max = Math.max(...values);
        const span = max - min;
        const padding = span > 0 ? span * 0.04 : Math.max(Math.abs(min), Math.abs(max), 1) * 0.04;
        let paddedMin = min - padding;
        let paddedMax = max + padding;

        const maxBubbleRadius = Math.max(0, ...bubbles.map((entry) => entry.radius));
        if (maxBubbleRadius > 0) {
            const plotHeight = Math.max(1, (chartContainer?.clientHeight ?? 288) - GRID_TOP_PX - GRID_BOTTOM_PX);
            const edgeFraction = Math.min(0.3, maxBubbleRadius / plotHeight);
            const paddedSpan = paddedMax - paddedMin;
            const bubblePadding = (paddedSpan * edgeFraction) / Math.max(0.1, 1 - 2 * edgeFraction);
            paddedMin -= bubblePadding;
            paddedMax += bubblePadding;
        }

        return {
            min: paddedMin,
            max: paddedMax,
        };
    }

    function eventKey(event: LotTimelineEventSchema): string {
        return `${event.lot_id}:${event.date}:${event.kind}:${event.transaction_id}:${event.related_transaction_id ?? ''}:${event.fragment_id ?? ''}`;
    }

    function eventKindLabel(kind: LotTimelineEventSchema['kind']): string {
        return labels.eventType[kind];
    }

    function eventCategory(kind: LotTimelineEventSchema['kind']): EventMarkerSeriesKind | null {
        if (kind === 'BUY') return 'buy';
        if (kind === 'SELL') return 'sell';
        if (kind === 'TRANSFER_ARRIVE') return 'transfer';
        if (kind === 'ADJUSTMENT_IN' || kind === 'ADJUSTMENT_OUT') return 'adjustment';
        if (kind === 'SPLIT') return 'split';
        return null;
    }

    function formatQuantityValue(value: number): string {
        return formatDecimalForDisplay(Math.abs(value), {minFrac: 0, maxFrac: 8});
    }

    function formatSignedQuantityValue(value: number): string {
        const normalized = normalizeZero(value);
        const sign = normalized > 0 ? '+' : normalized < 0 ? '-' : '';
        return `${sign}${formatQuantityValue(normalized)}`;
    }

    function formatMaybeQuantity(value: number | null): string {
        return value == null ? '—' : formatQuantityValue(value);
    }

    function formatMaybeMoney(value: number | null): string {
        return value == null ? '—' : formatCurrencyAmountPlain(value, currency);
    }

    function eventQuantityText(event: LotTimelineEventSchema): string | null {
        const quantity = parseNumber(event.quantity);
        return quantity == null ? null : formatQuantityValue(quantity);
    }

    function resolveMarketPriceAtOrBefore(date: string, points: ReadonlyArray<MarketPriceLookupPoint>): MarketPriceLookupPoint | null {
        let low = 0;
        let high = points.length - 1;
        let matchIndex = -1;

        while (low <= high) {
            const mid = Math.floor((low + high) / 2);
            if (points[mid].date <= date) {
                matchIndex = mid;
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }

        return matchIndex >= 0 ? points[matchIndex] : null;
    }

    function findTransferDepartEvent(arriveEvent: LotTimelineEventSchema, departEvents: ReadonlyArray<LotTimelineEventSchema>): LotTimelineEventSchema | null {
        const candidates = departEvents.filter((candidate) => {
            if (candidate.lot_id !== arriveEvent.lot_id) return false;
            if (sortDates(candidate.date, arriveEvent.date) > 0) return false;
            if (candidate.source_broker_id != null && arriveEvent.source_broker_id != null && candidate.source_broker_id !== arriveEvent.source_broker_id) return false;
            if (candidate.destination_broker_id != null && arriveEvent.destination_broker_id != null && candidate.destination_broker_id !== arriveEvent.destination_broker_id) return false;
            if (arriveEvent.related_transaction_id != null && candidate.transaction_id === arriveEvent.related_transaction_id) return true;
            if (candidate.related_transaction_id != null && candidate.related_transaction_id === arriveEvent.transaction_id) return true;
            if (arriveEvent.fragment_id != null && candidate.fragment_id != null && candidate.fragment_id === arriveEvent.fragment_id) return true;
            return false;
        });

        candidates.sort((left, right) => sortDates(right.date, left.date) || right.transaction_id - left.transaction_id);
        return candidates[0] ?? null;
    }

    function findTransferArriveEvent(departEvent: LotTimelineEventSchema, arriveEvents: ReadonlyArray<LotTimelineEventSchema>): LotTimelineEventSchema | null {
        const candidates = arriveEvents.filter((candidate) => {
            if (candidate.lot_id !== departEvent.lot_id) return false;
            if (sortDates(candidate.date, departEvent.date) < 0) return false;
            if (candidate.source_broker_id != null && departEvent.source_broker_id != null && candidate.source_broker_id !== departEvent.source_broker_id) return false;
            if (candidate.destination_broker_id != null && departEvent.destination_broker_id != null && candidate.destination_broker_id !== departEvent.destination_broker_id) return false;
            if (departEvent.related_transaction_id != null && candidate.transaction_id === departEvent.related_transaction_id) return true;
            if (candidate.related_transaction_id != null && candidate.related_transaction_id === departEvent.transaction_id) return true;
            if (departEvent.fragment_id != null && candidate.fragment_id != null && candidate.fragment_id === departEvent.fragment_id) return true;
            return false;
        });

        candidates.sort((left, right) => sortDates(left.date, right.date) || left.transaction_id - right.transaction_id);
        return candidates[0] ?? null;
    }

    function eventTimelineOrder(event: LotTimelineEventSchema): number {
        if (event.kind === 'TRANSFER_DEPART') return 0;
        if (event.kind === 'TRANSFER_ARRIVE') return 1;
        if (event.kind === 'SPLIT') return 2;
        if (event.kind === 'BUY' || event.kind === 'ADJUSTMENT_IN') return 3;
        return 4;
    }

    function cloneLotEventState(state: LotEventState | undefined): LotEventState {
        return {quantity: state?.quantity ?? null, unitPrice: state?.unitPrice ?? null};
    }

    const eventStateSnapshots = $derived.by(() => {
        const stateByLot = new Map<number, LotEventState>();
        const snapshots = new Map<string, EventStateSnapshot>();
        const sortedEvents = [...lotEvents].sort((left, right) => sortDates(left.date, right.date) || eventTimelineOrder(left) - eventTimelineOrder(right) || left.transaction_id - right.transaction_id);

        for (const event of sortedEvents) {
            const state = cloneLotEventState(stateByLot.get(event.lot_id));
            const beforeQuantity = state.quantity;
            const beforeUnitPrice = state.unitPrice;
            const quantity = parseNumber(event.quantity);
            const unitPrice = parseNumber(event.unit_price ?? event.open_unit_price ?? event.close_unit_price);
            const ratio = parseNumber(event.ratio);
            let afterQuantity = beforeQuantity;
            let afterUnitPrice = beforeUnitPrice;

            if (event.kind === 'BUY') {
                const openedQuantity = quantity == null ? null : Math.abs(quantity);
                const baseQuantity = beforeQuantity ?? 0;
                afterQuantity = openedQuantity == null ? beforeQuantity : baseQuantity + openedQuantity;
                afterUnitPrice = unitPrice ?? beforeUnitPrice;
            } else if (event.kind === 'ADJUSTMENT_IN') {
                const addedQuantity = quantity == null ? null : Math.abs(quantity);
                const baseQuantity = beforeQuantity ?? 0;
                if (addedQuantity != null) {
                    afterQuantity = baseQuantity + addedQuantity;
                    if (unitPrice != null && beforeUnitPrice != null && baseQuantity > 0) {
                        afterUnitPrice = (beforeUnitPrice * baseQuantity + unitPrice * addedQuantity) / afterQuantity;
                    } else {
                        afterUnitPrice = unitPrice ?? beforeUnitPrice;
                    }
                }
            } else if (event.kind === 'SELL' || event.kind === 'ADJUSTMENT_OUT') {
                const closedQuantity = quantity == null ? null : Math.abs(quantity);
                afterQuantity = beforeQuantity != null && closedQuantity != null ? Math.max(0, beforeQuantity - closedQuantity) : beforeQuantity;
                afterUnitPrice = beforeUnitPrice;
            } else if (event.kind === 'SPLIT') {
                const fallbackAfterQuantity = quantity == null ? null : Math.abs(quantity);
                const fallbackBeforeQuantity = ratio != null && ratio !== 0 && fallbackAfterQuantity != null ? fallbackAfterQuantity / ratio : null;
                const splitBeforeQuantity = beforeQuantity ?? fallbackBeforeQuantity;
                afterQuantity = splitBeforeQuantity != null && ratio != null ? splitBeforeQuantity * ratio : beforeQuantity;
                afterUnitPrice = beforeUnitPrice != null && ratio != null && ratio !== 0 ? beforeUnitPrice / ratio : beforeUnitPrice;
            } else if (event.kind === 'TRANSFER_DEPART' || event.kind === 'TRANSFER_ARRIVE') {
                afterQuantity = beforeQuantity ?? (quantity == null ? null : Math.abs(quantity));
                afterUnitPrice = beforeUnitPrice ?? unitPrice;
            }

            snapshots.set(eventKey(event), {
                quantityBefore: beforeQuantity,
                quantityAfter: afterQuantity,
                unitPriceBefore: beforeUnitPrice,
                unitPriceAfter: afterUnitPrice,
            });
            stateByLot.set(event.lot_id, {quantity: afterQuantity, unitPrice: afterUnitPrice});
        }

        return snapshots;
    });

    function buildMarkerSeriesDefinitions(): MarkerSeriesDefinition[] {
        return [
            {
                key: 'buy',
                label: labels.markerLegend.buy,
                symbol: BUY_MARKER_SYMBOL,
                symbolSize: 12,
                color: isDark ? '#86efac' : '#16a34a',
            },
            {
                key: 'sell',
                label: labels.markerLegend.sell,
                symbol: SELL_MARKER_SYMBOL,
                symbolSize: 12,
                color: isDark ? '#fca5a5' : '#dc2626',
            },
            {
                key: 'transfer',
                label: labels.markerLegend.transfer,
                symbol: TRANSFER_MARKER_SYMBOL,
                symbolSize: 16,
                color: isDark ? '#93c5fd' : '#1d4ed8',
            },
            {
                key: 'adjustment',
                label: labels.markerLegend.adjustment,
                symbol: 'rect',
                symbolSize: 11,
                color: isDark ? '#fcd34d' : '#d97706',
            },
            {
                key: 'split',
                label: labels.markerLegend.split,
                symbol: SPLIT_MARKER_SYMBOL,
                symbolSize: 18,
                color: isDark ? '#c4b5fd' : '#7c3aed',
            },
        ];
    }

    const labels = $derived.by(() => {
        const marketPrice = $_('chart.marketPrice');
        const abs = $_('dashboard.abs');
        const pct = $_('dashboard.pct');
        const combined = $_('brokers.lots.combined');
        const noData = $_('common.noData');
        const broker = $_('common.broker');
        const quantity = $_('common.quantity');
        const from = $_('common.from');
        const to = $_('common.to');
        const unitPrice = $_('brokers.lots.chartMarkers.unitPrice');
        const transitInterval = $_('brokers.lots.chartMarkers.transitInterval');
        const proceeds = $_('brokers.lots.chartMarkers.proceeds');
        const realizedPnl = $_('brokers.lots.chartMarkers.realizedPnl');
        const markerLegendBuy = $_('brokers.lots.chartMarkers.legend.buy');
        const markerLegendSell = $_('brokers.lots.chartMarkers.legend.sell');
        const markerLegendTransfer = $_('brokers.lots.chartMarkers.legend.transfer');
        const markerLegendAdjustment = $_('brokers.lots.chartMarkers.legend.adjustment');
        const markerLegendSplit = $_('brokers.lots.chartMarkers.legend.split');
        const markerLegendIncome = $_('brokers.lots.chartMarkers.legend.income');
        const eventTypeBuy = $_('brokers.lots.chartMarkers.eventType.BUY');
        const eventTypeSell = $_('brokers.lots.chartMarkers.eventType.SELL');
        const eventTypeAdjustmentIn = $_('brokers.lots.chartMarkers.eventType.ADJUSTMENT_IN');
        const eventTypeAdjustmentOut = $_('brokers.lots.chartMarkers.eventType.ADJUSTMENT_OUT');
        const eventTypeTransferDepart = $_('brokers.lots.chartMarkers.eventType.TRANSFER_DEPART');
        const eventTypeTransferArrive = $_('brokers.lots.chartMarkers.eventType.TRANSFER_ARRIVE');
        const eventTypeSplit = $_('brokers.lots.chartMarkers.eventType.SPLIT');
        const pmc = $_('dashboard.pmc');
        const openingValue = translatedOr('brokers.lots.chartMarkers.openingValue', 'Opening value');
        const quantitySold = translatedOr('brokers.lots.chartMarkers.quantitySold', 'Quantity sold');
        const residualQuantity = translatedOr('brokers.lots.chartMarkers.residualQuantity', 'Residual quantity');
        const salePrice = translatedOr('brokers.lots.chartMarkers.salePrice', 'Sale price');
        const completeSale = translatedOr('brokers.lots.chartMarkers.completeSale', 'Complete sale');
        const partialSale = translatedOr('brokers.lots.chartMarkers.partialSale', 'Partial sale');
        const adjustmentType = translatedOr('brokers.lots.chartMarkers.adjustmentType', 'Adjustment type');
        const eventDate = translatedOr('brokers.lots.chartMarkers.eventDate', 'Date');
        const quantityEffect = translatedOr('brokers.lots.chartMarkers.quantityEffect', 'Lot quantity effect');
        const previousQuantity = translatedOr('brokers.lots.chartMarkers.previousQuantity', 'Previous quantity');
        const nextQuantity = translatedOr('brokers.lots.chartMarkers.nextQuantity', 'Next quantity');
        const previousPrice = translatedOr('brokers.lots.chartMarkers.previousPrice', 'Previous price');
        const nextPrice = translatedOr('brokers.lots.chartMarkers.nextPrice', 'Next price');
        const totalCost = translatedOr('brokers.lots.chartMarkers.totalCost', 'Total cost');
        const unchanged = translatedOr('brokers.lots.chartMarkers.unchanged', 'Unchanged');
        const bubbleOpeningDate = $_('brokers.lots.openingDate');
        const bubbleOpeningValue = $_('brokers.lots.openingValue');
        const bubbleTotalPnl = $_('brokers.lots.totalPnl');
        const bubbleTotalReturn = $_('brokers.lots.totalReturn');
        const bubbleAssetIncome = $_('brokers.lots.assetIncome');
        const bubbleEstimatedAtCost = $_('brokers.lots.estimatedAtCost');
        const bubbleSeriesName = $_('brokers.lots.performanceBubbleTitle');
        const bubbleState = $_('brokers.lots.status');
        const bubbleStateOpen = $_('brokers.lots.states.OPEN');
        const bubbleStatePartial = $_('brokers.lots.states.PARTIALLY_CLOSED');
        const bubbleStateClosed = $_('brokers.lots.states.CLOSED');
        const yAuto = translatedOr('brokers.lots.yAxisAuto', 'Auto');
        const yFromZero = translatedOr('brokers.lots.yAxisFromZero', 'From 0');

        return {
            wac: !pmc || pmc === 'dashboard.pmc' ? 'WAC' : pmc,
            marketPrice: !marketPrice || marketPrice === 'chart.marketPrice' ? 'Market Price' : marketPrice,
            abs: !abs || abs === 'dashboard.abs' ? 'ABS' : abs,
            pct: !pct || pct === 'dashboard.pct' ? '%' : pct,
            yAuto,
            yFromZero,
            combined: !combined || combined === 'brokers.lots.combined' ? 'Combined' : combined,
            noData: !noData || noData === 'common.noData' ? 'No data' : noData,
            broker: !broker || broker === 'common.broker' ? 'Broker' : broker,
            quantity: !quantity || quantity === 'common.quantity' ? 'Quantity' : quantity,
            from: !from || from === 'common.from' ? 'From' : from,
            to: !to || to === 'common.to' ? 'To' : to,
            unitPrice: !unitPrice || unitPrice === 'brokers.lots.chartMarkers.unitPrice' ? 'Unit Price' : unitPrice,
            transitInterval: !transitInterval || transitInterval === 'brokers.lots.chartMarkers.transitInterval' ? 'Transit Interval' : transitInterval,
            proceeds: !proceeds || proceeds === 'brokers.lots.chartMarkers.proceeds' ? 'Proceeds' : proceeds,
            realizedPnl: !realizedPnl || realizedPnl === 'brokers.lots.chartMarkers.realizedPnl' ? 'Realized P&L' : realizedPnl,
            openingValue,
            quantitySold,
            residualQuantity,
            salePrice,
            completeSale,
            partialSale,
            adjustmentType,
            eventDate,
            quantityEffect,
            previousQuantity,
            nextQuantity,
            previousPrice,
            nextPrice,
            totalCost,
            unchanged,
            bubbleOpeningDate: !bubbleOpeningDate || bubbleOpeningDate === 'brokers.lots.openingDate' ? 'Opening Date' : bubbleOpeningDate,
            bubbleOpeningValue: !bubbleOpeningValue || bubbleOpeningValue === 'brokers.lots.openingValue' ? 'Opening Value' : bubbleOpeningValue,
            bubbleTotalPnl: !bubbleTotalPnl || bubbleTotalPnl === 'brokers.lots.totalPnl' ? 'Total P&L' : bubbleTotalPnl,
            bubbleTotalReturn: !bubbleTotalReturn || bubbleTotalReturn === 'brokers.lots.totalReturn' ? 'Total return' : bubbleTotalReturn,
            bubbleAssetIncome: !bubbleAssetIncome || bubbleAssetIncome === 'brokers.lots.assetIncome' ? 'Income' : bubbleAssetIncome,
            bubbleEstimatedAtCost: !bubbleEstimatedAtCost || bubbleEstimatedAtCost === 'brokers.lots.estimatedAtCost' ? 'Estimated at cost' : bubbleEstimatedAtCost,
            bubbleSeriesName: !bubbleSeriesName || bubbleSeriesName === 'brokers.lots.performanceBubbleTitle' ? 'Lot performance' : bubbleSeriesName,
            bubbleState: !bubbleState || bubbleState === 'brokers.lots.status' ? 'State' : bubbleState,
            bubbleStateOpen: !bubbleStateOpen || bubbleStateOpen === 'brokers.lots.states.OPEN' ? 'Open' : bubbleStateOpen,
            bubbleStatePartial: !bubbleStatePartial || bubbleStatePartial === 'brokers.lots.states.PARTIALLY_CLOSED' ? 'Partially closed' : bubbleStatePartial,
            bubbleStateClosed: !bubbleStateClosed || bubbleStateClosed === 'brokers.lots.states.CLOSED' ? 'Closed' : bubbleStateClosed,
            markerLegend: {
                buy: !markerLegendBuy || markerLegendBuy === 'brokers.lots.chartMarkers.legend.buy' ? 'Buys' : markerLegendBuy,
                sell: !markerLegendSell || markerLegendSell === 'brokers.lots.chartMarkers.legend.sell' ? 'Sales' : markerLegendSell,
                transfer: !markerLegendTransfer || markerLegendTransfer === 'brokers.lots.chartMarkers.legend.transfer' ? 'Transfers' : markerLegendTransfer,
                adjustment: !markerLegendAdjustment || markerLegendAdjustment === 'brokers.lots.chartMarkers.legend.adjustment' ? 'Adjustments' : markerLegendAdjustment,
                split: !markerLegendSplit || markerLegendSplit === 'brokers.lots.chartMarkers.legend.split' ? 'Split' : markerLegendSplit,
                income: !markerLegendIncome || markerLegendIncome === 'brokers.lots.chartMarkers.legend.income' ? 'Dividend / interest' : markerLegendIncome,
            },
            eventType: {
                BUY: !eventTypeBuy || eventTypeBuy === 'brokers.lots.chartMarkers.eventType.BUY' ? 'Buy' : eventTypeBuy,
                SELL: !eventTypeSell || eventTypeSell === 'brokers.lots.chartMarkers.eventType.SELL' ? 'Sale' : eventTypeSell,
                ADJUSTMENT_IN: !eventTypeAdjustmentIn || eventTypeAdjustmentIn === 'brokers.lots.chartMarkers.eventType.ADJUSTMENT_IN' ? 'Adjustment In' : eventTypeAdjustmentIn,
                ADJUSTMENT_OUT: !eventTypeAdjustmentOut || eventTypeAdjustmentOut === 'brokers.lots.chartMarkers.eventType.ADJUSTMENT_OUT' ? 'Adjustment Out' : eventTypeAdjustmentOut,
                TRANSFER_DEPART: !eventTypeTransferDepart || eventTypeTransferDepart === 'brokers.lots.chartMarkers.eventType.TRANSFER_DEPART' ? 'Transfer' : eventTypeTransferDepart,
                TRANSFER_ARRIVE: !eventTypeTransferArrive || eventTypeTransferArrive === 'brokers.lots.chartMarkers.eventType.TRANSFER_ARRIVE' ? 'Transfer' : eventTypeTransferArrive,
                SPLIT: !eventTypeSplit || eventTypeSplit === 'brokers.lots.chartMarkers.eventType.SPLIT' ? 'Split' : eventTypeSplit,
            },
        };
    });

    const groupedChartData = $derived.by(() => {
        const groupedBrokerPoints = new Map<number, Array<{date: string; value: number | null}>>();
        for (const point of brokerWacHistory) {
            const brokerPoints = groupedBrokerPoints.get(point.broker_id) ?? [];
            brokerPoints.push({
                date: point.date,
                value: scaleUnitPrice(nullifyZeroWac(parseNumber(point.wac), parseNumber(point.pool_qty))),
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
                          value: scaleUnitPrice(nullifyZeroWac(parseNumber(point.wac), parseNumber(point.pool_qty))),
                      })),
                  )
                : null;

        const marketPriceByDate = new Map<string, number | null>();
        const estimatedByDate = new Map<string, boolean>();
        for (const point of priceHistory) {
            const value = parseNumber(point.market_price);
            const isEstimated = point.estimated === true;
            if (!marketPriceByDate.has(point.date)) {
                marketPriceByDate.set(point.date, value);
                estimatedByDate.set(point.date, isEstimated);
                continue;
            }
            if (marketPriceByDate.get(point.date) == null && value != null) {
                marketPriceByDate.set(point.date, value);
                estimatedByDate.set(point.date, isEstimated);
            }
            // A real quote on the same date downgrades the flag: the segment is not an estimate.
            if (!isEstimated) estimatedByDate.set(point.date, false);
        }

        const marketPricePoints = toPercentSeries(
            Array.from(marketPriceByDate.entries())
                .map(([date, value]) => ({date, value}))
                .sort((a, b) => sortDates(a.date, b.date)),
        );

        const marketPriceLookupPoints: MarketPriceLookupPoint[] = marketPricePoints.flatMap((point) =>
            point.absolute == null
                ? []
                : [
                      {
                          date: point.date,
                          absolute: point.absolute,
                          percent: point.percent,
                      },
                  ],
        );

        const transferDepartEvents = lotEvents.filter((event) => event.kind === 'TRANSFER_DEPART');
        const transferArriveEvents = lotEvents.filter((event) => event.kind === 'TRANSFER_ARRIVE');
        const rawMarkerPoints: EventMarkerDatum[] = [];
        for (const event of lotEvents) {
            const category = eventCategory(event.kind);
            if (category == null) continue;

            const marketPricePoint = resolveMarketPriceAtOrBefore(event.date, marketPriceLookupPoints);
            if (!marketPricePoint) continue;

            const transferDepart = event.kind === 'TRANSFER_ARRIVE' ? findTransferDepartEvent(event, transferDepartEvents) : null;
            const transferArrive = event.kind === 'TRANSFER_DEPART' ? findTransferArriveEvent(event, transferArriveEvents) : null;
            rawMarkerPoints.push({
                id: eventKey(event),
                date: event.date,
                absolute: marketPricePoint.absolute,
                percent: marketPricePoint.percent,
                category,
                event,
                transferDepartDate: transferDepart?.date ?? null,
                transferArriveDate: transferArrive?.date ?? null,
                verticalOffsetPx: 0,
            });
        }

        const markerPointsByDate = new Map<string, EventMarkerDatum[]>();
        for (const point of rawMarkerPoints) {
            const groupedPoints = markerPointsByDate.get(point.date) ?? [];
            groupedPoints.push(point);
            markerPointsByDate.set(point.date, groupedPoints);
        }

        for (const sameDatePoints of markerPointsByDate.values()) {
            sameDatePoints.sort((left, right) => {
                const categoryOrder = MARKER_CATEGORY_ORDER[left.category] - MARKER_CATEGORY_ORDER[right.category];
                if (categoryOrder !== 0) return categoryOrder;
                return left.event.transaction_id - right.event.transaction_id;
            });

            // Same-day events stack on identical X/Y coordinates. Small deterministic Y-offset
            // keeps each marker individually hoverable without hiding sibling events.
            sameDatePoints.forEach((point, index) => {
                point.verticalOffsetPx = (index - (sameDatePoints.length - 1) / 2) * MARKER_VERTICAL_OFFSET_STEP;
            });
        }

        const markerSeriesMap = new Map<EventMarkerSeriesKind, EventMarkerDatum[]>([
            ['buy', []],
            ['sell', []],
            ['transfer', []],
            ['adjustment', []],
            ['split', []],
        ]);
        for (const point of rawMarkerPoints) {
            markerSeriesMap.get(point.category)?.push(point);
        }

        const markerSeries: EventMarkerSeries[] = Array.from(markerSeriesMap.entries()).map(([category, points]) => ({category, points}));

        const allDates = [...brokerWacHistory.map((point) => point.date), ...cumulativeWacHistory.map((point) => point.date), ...priceHistory.map((point) => point.date), ...rawMarkerPoints.map((point) => point.date)].sort(sortDates);

        return {
            realSeries,
            combinedSeries,
            marketPricePoints,
            estimatedByDate,
            markerSeries,
            minDate: allDates[0] ?? null,
            maxDate: allDates.at(-1) ?? null,
            hasAbsoluteData: realSeries.some((series) => series.hasAbsoluteData) || (combinedSeries?.hasAbsoluteData ?? false) || marketPricePoints.some((point) => point.absolute != null) || rawMarkerPoints.some((point) => point.absolute != null),
            hasPercentData: realSeries.some((series) => series.hasPercentData) || (combinedSeries?.hasPercentData ?? false) || marketPricePoints.some((point) => point.percent != null) || rawMarkerPoints.some((point) => point.percent != null),
            totalPointCount: brokerWacHistory.length + cumulativeWacHistory.length + priceHistory.length + rawMarkerPoints.length,
        };
    });

    let hasAbsoluteData = $derived(groupedChartData.hasAbsoluteData);
    let hasLotBubblePercentData = $derived(lots.some((lot) => lot.direction === 'LONG' && parseNumber(lot.total_return) != null));
    let hasPercentData = $derived(groupedChartData.hasPercentData || hasLotBubblePercentData);
    let showChart = $derived((groupedChartData.totalPointCount > 0 || (displayMode === 'percentage' && hasLotBubblePercentData)) && (displayMode === 'absolute' ? hasAbsoluteData : hasPercentData));
    let emptyMessage = $derived.by(() => {
        if (groupedChartData.totalPointCount === 0 && !(displayMode === 'percentage' && hasLotBubblePercentData)) return labels.noData;
        if (displayMode === 'absolute' && !hasAbsoluteData) return labels.noData;
        if (displayMode === 'percentage' && !hasPercentData) return labels.noData;
        return '';
    });

    function incomeMarkerColor(): string {
        return isDark ? '#c4b5fd' : '#7c3aed';
    }

    function incomeEventTypeLabel(type: LotIncomeEvent['type']): string {
        return type === 'DIVIDEND' ? $_('brokers.lots.incomeMarkerDividend') : $_('brokers.lots.incomeMarkerInterest');
    }

    let incomeMarkerEvents = $derived.by((): LotIncomeEvent[] => (incomeEvents ?? []).filter((event): event is LotIncomeEvent => (event?.type === 'DIVIDEND' || event?.type === 'INTEREST') && !!event.date));

    function buildIncomeEventTooltip(event: LotIncomeEvent | null): string {
        if (!event) return '';
        const theme = buildTooltipTheme(isDark);
        const amount = Number.parseFloat(event.amount);
        const rows = [
            buildTooltipRow(escapeHtml($_('brokers.lots.incomeMarkerType')), escapeHtml(incomeEventTypeLabel(event.type)), incomeMarkerColor()),
            buildTooltipRow(escapeHtml($_('brokers.lots.incomeMarkerDate')), escapeHtml(formatShortDate(event.date))),
            buildTooltipRow(escapeHtml($_('brokers.lots.incomeMarkerBroker')), escapeHtml(brokerName(event.broker_id))),
            buildTooltipRow(escapeHtml($_('brokers.lots.incomeMarkerAmount')), escapeHtml(Number.isFinite(amount) ? formatCurrencyAmountPlain(amount, currency) : String(event.amount))),
            buildTooltipRow(escapeHtml($_('brokers.lots.incomeMarkerLotCount')), escapeHtml(String(event.lot_ids?.length ?? 0))),
        ];
        return `<div style="font-size:11px;color:${theme.textColor}">${buildTooltipHeader(escapeHtml(incomeEventTypeLabel(event.type)), theme.textColor)}${buildTooltipDivider(theme.border)}${rows.join('')}</div>`;
    }

    /** Opening unit price (cost basis / share) per lot id — the fallback height for income "|" markers on
     * transactions-only assets that have no market price (e.g. Lonate: the buy price height). */
    const openingUnitPriceByLot = $derived.by(() => {
        const map = new Map<number, number>();
        for (const lot of lots) {
            const value = scaleUnitPrice(parseNumber(lot.opening_unit_price));
            if (value != null) map.set(lot.lot_id, value);
        }
        return map;
    });

    /** Y (price) at which to drop an income "|" marker: the market price on that date, or — when the asset
     * has no price history — the mean opening unit price of the lots the distribution was allocated to. */
    function incomeMarkerYValue(event: LotIncomeEvent): number | null {
        const market = resolveMarketPriceAtOrBefore(event.date, priceLookupPoints)?.absolute ?? null;
        if (market != null) return market;
        const prices = (event.lot_ids ?? []).map((id) => openingUnitPriceByLot.get(id)).filter((value): value is number => value != null);
        if (prices.length === 0) return null;
        return prices.reduce((sum, value) => sum + value, 0) / prices.length;
    }

    /** Income markers as short vertical "|" glyphs (rect 2×16px) sitting at the price line on the
     * distribution date. Only meaningful on the price axis, so
     * rendered in ABS mode; returns undefined otherwise or when there are no income events. */
    function buildIncomeMarkerSeries(): echarts.SeriesOption | undefined {
        if (displayMode !== 'absolute' || incomeMarkerEvents.length === 0) return undefined;
        const data = incomeMarkerEvents
            .map((event) => {
                const y = incomeMarkerYValue(event);
                if (y == null) return null;
                return {
                    value: [event.date, y],
                    incomeEvent: event,
                    itemStyle: {color: incomeMarkerColor(), opacity: 0.95},
                };
            })
            .filter((entry): entry is {value: (string | number)[]; incomeEvent: LotIncomeEvent; itemStyle: {color: string; opacity: number}} => entry != null);
        if (data.length === 0) return undefined;
        return {
            id: LOT_INCOME_MARKER_SERIES_ID,
            name: labels.markerLegend.income,
            type: 'scatter',
            symbol: 'rect',
            symbolSize: [2, 16],
            itemStyle: {color: incomeMarkerColor(), opacity: 0.95},
            clip: true,
            z: 5,
            data,
            emphasis: {scale: 1.4},
            tooltip: {
                trigger: 'item',
                formatter: (param: any) => buildIncomeEventTooltip((param?.data?.incomeEvent ?? null) as LotIncomeEvent | null),
            },
        } as echarts.SeriesOption;
    }

    /** Append the income "|" markers so vertical distribution glyphs appear on the income dates
     * (plan v3 §11). No-op when there are no income events / not in ABS mode. */
    function attachIncomeMarkers(series: echarts.SeriesOption[]): echarts.SeriesOption[] {
        const markerSeries = buildIncomeMarkerSeries();
        if (!markerSeries) return series;
        return [...series, markerSeries];
    }

    interface LotBubblePoint {
        lotId: number;
        openingDate: string;
        label: string;
        brokerId: number | null;
        brokerName: string;
        fillColor: string;
        priceAtOpening: number | null;
        openingUnitPrice: number | null;
        totalReturn: number | null;
        totalPnl: number;
        openQuantity: number;
        originalQuantity: number;
        openingValue: number;
        assetIncome: number;
        estimatedAtCost: boolean;
        state: LotDisplayState;
        active: boolean;
    }

    interface RenderableLotBubble {
        point: LotBubblePoint;
        baseY: number;
        /** Y of the connector's fixed vertex — the market price on the opening day ("prezzo di quel
         *  giorno"), so the segment starts on the price curve, not at the lot's cost basis. */
        connectorBaseY: number;
        yValue: number;
        metric: number;
        radius: number;
        offsetX: number;
    }

    function lotBubbleFillColor(brokerId: number | null): string {
        if (brokerId == null) return isDark ? '#94a3b8' : '#475569';
        const colors = getBrokerColor(brokerId, brokers);
        return isDark ? colors.vivid : colors.vividLight;
    }

    function lotBubbleSignColor(signed: number): string {
        if (signed > LOT_BUBBLE_ZERO_EPS) return isDark ? '#4ade80' : '#16a34a';
        if (signed < -LOT_BUBBLE_ZERO_EPS) return isDark ? '#f87171' : '#dc2626';
        return isDark ? '#94a3b8' : '#64748b';
    }

    function lotBubbleRadius(value: number, minValue: number, maxValue: number): number {
        const mid = (LOT_BUBBLE_MIN_RADIUS + LOT_BUBBLE_MAX_RADIUS) / 2;
        if (maxValue <= minValue) return mid;
        const minRoot = Math.sqrt(Math.max(0, minValue));
        const maxRoot = Math.sqrt(Math.max(0, maxValue));
        if (maxRoot === minRoot) return mid;
        const valueRoot = Math.sqrt(Math.max(0, value));
        const normalized = Math.min(1, Math.max(0, (valueRoot - minRoot) / (maxRoot - minRoot)));
        return LOT_BUBBLE_MIN_RADIUS + normalized * (LOT_BUBBLE_MAX_RADIUS - LOT_BUBBLE_MIN_RADIUS);
    }

    const lotSelectionSet = $derived.by(() => new Set(selectedLotIds));

    /** Sorted, deduped, non-null market prices for at-or-before lookups (bubble opening price). */
    const priceLookupPoints = $derived.by<MarketPriceLookupPoint[]>(() => {
        const byDate = new Map<string, number | null>();
        for (const point of priceHistory) {
            const value = parseNumber(point.market_price);
            if (!byDate.has(point.date)) {
                byDate.set(point.date, value);
                continue;
            }
            if (byDate.get(point.date) == null && value != null) byDate.set(point.date, value);
        }
        return Array.from(byDate.entries())
            .flatMap(([date, value]) => (value == null ? [] : [{date, absolute: value, percent: null}]))
            .sort((left, right) => sortDates(left.date, right.date));
    });

    const lotBubblePoints = $derived.by<LotBubblePoint[]>(() => {
        const longLots = lots.filter((lot) => lot.direction === 'LONG');
        return longLots.map((lot) => {
            const priceAtOpening = resolveMarketPriceAtOrBefore(lot.opening_date, priceLookupPoints)?.absolute ?? null;
            const openQuantity = Math.max(0, parseNumber(lot.open_quantity) ?? 0);
            const originalQuantity = Math.max(0, parseNumber(lot.original_quantity) ?? 0);
            return {
                lotId: lot.lot_id,
                openingDate: lot.opening_date,
                label: formatDate(lot.opening_date),
                brokerId: lot.opening_broker_id,
                brokerName: brokerName(lot.opening_broker_id),
                fillColor: lotBubbleFillColor(lot.opening_broker_id),
                priceAtOpening,
                openingUnitPrice: parseNumber(lot.opening_unit_price),
                totalReturn: parseNumber(lot.total_return),
                totalPnl: parseNumber(lot.total_pnl) ?? 0,
                openQuantity,
                originalQuantity,
                openingValue: Math.max(0, parseNumber(lot.original_cost) ?? 0),
                assetIncome: parseNumber(lot.asset_income) ?? 0,
                estimatedAtCost: safeString(lot.value_source) === 'ESTIMATED_AT_COST',
                state: lotDisplayState(openQuantity, originalQuantity),
                active: lotSelectionSet.size === 0 || lotSelectionSet.has(lot.lot_id),
            };
        });
    });

    function lotBubbleStateLabel(state: LotDisplayState): string {
        if (state === 'OPEN') return labels.bubbleStateOpen;
        if (state === 'PARTIAL') return labels.bubbleStatePartial;
        return labels.bubbleStateClosed;
    }

    function buildBubbleTooltip(point: LotBubblePoint | null): string {
        if (!point) return '';
        const theme = buildTooltipTheme(isDark);
        const rows = [
            buildTooltipRow(escapeHtml(labels.bubbleOpeningDate), escapeHtml(formatDate(point.openingDate))),
            buildTooltipRow(escapeHtml(labels.broker), escapeHtml(point.brokerName), point.fillColor),
            buildTooltipRow(escapeHtml(labels.bubbleState), escapeHtml(lotBubbleStateLabel(point.state)), lotStateColor(point.state, isDark)),
            buildTooltipRow(escapeHtml(labels.bubbleOpeningValue), escapeHtml(formatCurrencyAmountPlain(point.openingValue, currency))),
            buildTooltipRow(escapeHtml(labels.bubbleTotalPnl), `<span style="color:${lotBubbleSignColor(point.totalPnl)}">${escapeHtml(formatCurrencyAmountPlain(point.totalPnl, currency))}</span>`),
            buildTooltipRow(escapeHtml(labels.bubbleTotalReturn), point.totalReturn == null ? '—' : `<span style="color:${lotBubbleSignColor(point.totalReturn)}">${escapeHtml(formatPercent(point.totalReturn * 100))}</span>`),
        ];
        if (point.assetIncome > 0) {
            rows.push(buildTooltipRow(escapeHtml(labels.bubbleAssetIncome), escapeHtml(formatCurrencyAmountPlain(point.assetIncome, currency))));
        }
        if (point.estimatedAtCost) {
            rows.push(buildTooltipRow(escapeHtml(labels.bubbleEstimatedAtCost), escapeHtml('•'), point.fillColor));
        }
        return `<div style="font-size:11px;color:${theme.textColor}">${buildTooltipHeader(escapeHtml(point.label), theme.textColor)}${buildTooltipDivider(theme.border)}${rows.join('')}</div>`;
    }

    function buildRenderableLotBubbles(): RenderableLotBubble[] {
        const isAbsolute = displayMode === 'absolute';
        const renderable = lotBubblePoints
            .map((point) => {
                if (point.totalReturn == null) return null;
                if (isAbsolute) {
                    // Base the ABS bubble on the lot's own opening unit price (cost basis / share) rather
                    // than the market close on the opening day. total_return is computed against the lot's
                    // cost basis, so opening_unit_price * (1 + total_return) collapses to the current unit
                    // price → same-asset lots with no distributions land at the same height. It also lets
                    // price-less assets (transactions only) still show a bubble (they always have a cost).
                    // opening_unit_price is per-single-unit (cost ÷ raw quantity); rescale it up to the
                    // per-quote_base_quantity market scale used by the price/WAC lines (e.g. ×100 → bond
                    // par ≈ 100) so the bubble sits on those lines. No-op for stocks (qbq=1).
                    const baseY = scaleUnitPrice(point.openingUnitPrice);
                    if (baseY == null) return null;
                    // Closed lots have no open quantity — size them by the original quantity instead so
                    // they stay visible rather than collapsing to the minimum radius.
                    const metric = point.openQuantity > 0 ? point.openQuantity : point.originalQuantity;
                    // Connector's fixed vertex sits on the market price line at the opening day ("prezzo di
                    // quel giorno") so the segment starts where the lot was created on the price curve, not
                    // at its (often higher) cost basis. Same-day lots share this anchor → a single fan pivot.
                    // Falls back to the cost basis when the asset has no market price on that date (e.g. a
                    // matured / price-less instrument), preserving the old behaviour in that case.
                    const connectorBaseY = point.priceAtOpening ?? baseY;
                    return {point, baseY, connectorBaseY, yValue: baseY * (1 + point.totalReturn), metric};
                }
                return {point, baseY: 0, connectorBaseY: 0, yValue: point.totalReturn * 100, metric: point.openingValue};
            })
            .filter((entry): entry is {point: LotBubblePoint; baseY: number; connectorBaseY: number; yValue: number; metric: number} => entry != null);

        if (renderable.length === 0) return [];

        const metrics = renderable.map((entry) => entry.metric);
        const minMetric = Math.min(...metrics);
        const maxMetric = Math.max(...metrics);
        const withRadius: RenderableLotBubble[] = renderable.map((entry) => ({
            ...entry,
            radius: lotBubbleRadius(entry.metric, minMetric, maxMetric),
            offsetX: 0,
        }));

        // Fan out lots opened on the same day so N same-day lots render as N distinct bubbles
        // instead of a single overlapping blob. Offset is applied in pixels (symbolOffset) so the
        // logical [date, value] stays intact — tooltips, axis and connectors keep the true date.
        const byDate = new Map<string, RenderableLotBubble[]>();
        for (const entry of withRadius) {
            const bucket = byDate.get(entry.point.openingDate);
            if (bucket) bucket.push(entry);
            else byDate.set(entry.point.openingDate, [entry]);
        }
        // ISO 'YYYY-MM-DD' compares chronologically as plain strings → cheap min/max for edge detection.
        const minDate = withRadius.reduce((min, entry) => (entry.point.openingDate < min ? entry.point.openingDate : min), withRadius[0].point.openingDate);
        const maxDate = withRadius.reduce((max, entry) => (entry.point.openingDate > max ? entry.point.openingDate : max), withRadius[0].point.openingDate);
        const hasSpan = minDate !== maxDate;
        for (const [date, bucket] of byDate) {
            if (bucket.length < 2) continue;
            const step = Math.max(...bucket.map((entry) => entry.radius)) * 1.6;
            const count = bucket.length;
            // Anchor the fan so groups sitting on an axis edge grow inward instead of spilling past the plot:
            // the earliest date grows rightwards (offsets 0,1,2…), the latest grows leftwards (…-2,-1,0),
            // everything in between stays centred. Only when there is an actual date span (a lone same-day
            // group keeps the symmetric centred layout).
            const anchor = hasSpan && date === minDate ? 'left' : hasSpan && date === maxDate ? 'right' : 'center';
            bucket.forEach((entry, index) => {
                const rel = anchor === 'left' ? index : anchor === 'right' ? index - (count - 1) : index - (count - 1) / 2;
                entry.offsetX = Math.round(rel * step);
            });
        }
        return withRadius;
    }

    /** Per-lot performance bubbles + dashed baseline→bubble connectors (ABS: from the lot's opening unit
     * price / cost basis; %: from the 0% baseline) + a small centre marker whose shape/colour encodes the
     * lot's open/partial/closed state. Empty selection = all visible lots highlighted; otherwise
     * non-selected bubbles are dimmed. */
    function buildLotBubbleSeries(): echarts.SeriesOption[] {
        const renderable = buildRenderableLotBubbles();
        if (renderable.length === 0) return [];

        const series: echarts.SeriesOption[] = [];

        // One connector per bubble. The base stays pinned to the true event x (opening date, no offset)
        // while the apex follows the bubble's fanned pixel position — the SAME +offsetX px applied to the
        // bubble's symbolOffset — so with N same-day lots you get N oblique lines spreading from the shared
        // event to each bubble instead of a single overlapping vertical. A `custom` renderItem is required
        // because the fan-out is a pixel offset, not a data-space shift: api.coord() re-resolves both
        // endpoints on every zoom/pan so each line stays glued to its bubble. Sign colour + baseY→yValue
        // height logic are unchanged. params.dataIndex is the original index, so renderable[…] stays aligned
        // even when dataZoom filters items out of the window.
        series.push({
            id: 'lot-bubble-connectors',
            name: 'lot-bubble-connectors',
            type: 'custom',
            silent: true,
            clip: true,
            z: 4,
            tooltip: {show: false},
            encode: {x: 0, y: 1},
            data: renderable.map((entry) => ({value: [entry.point.openingDate, entry.yValue]})),
            renderItem: (params: any, api: any) => {
                const entry = renderable[params.dataIndex];
                if (!entry) return null;
                const base = api.coord([entry.point.openingDate, entry.connectorBaseY]);
                const apex = api.coord([entry.point.openingDate, entry.yValue]);
                if (!base || !apex) return null;
                return {
                    type: 'line',
                    silent: true,
                    shape: {x1: base[0], y1: base[1], x2: apex[0] + entry.offsetX, y2: apex[1]},
                    style: {stroke: lotBubbleSignColor(entry.point.totalReturn ?? 0), lineWidth: 1.25, lineDash: [4, 4], opacity: entry.point.active ? 0.8 : 0.16},
                };
            },
        } as echarts.SeriesOption);

        series.push({
            id: 'lot-performance-bubbles',
            name: labels.bubbleSeriesName,
            type: 'scatter',
            symbol: 'circle',
            clip: true,
            z: 6,
            data: renderable.map((entry) => ({
                name: `lot-bubble-${entry.point.lotId}`,
                value: [entry.point.openingDate, entry.yValue],
                lotBubbleId: entry.point.lotId,
                point: entry.point,
                symbolSize: entry.radius * 2,
                symbolOffset: [entry.offsetX, 0],
                itemStyle: {
                    color: entry.point.fillColor,
                    borderColor: isDark ? '#0f172a' : '#ffffff',
                    borderWidth: entry.point.estimatedAtCost ? 2.5 : 1.5,
                    borderType: entry.point.estimatedAtCost ? 'dashed' : 'solid',
                    opacity: entry.point.active ? 0.9 : 0.22,
                },
                emphasis: {scale: true, itemStyle: {opacity: 1, borderColor: isDark ? '#e2e8f0' : '#0f172a', borderWidth: 2}},
            })),
            symbolSize: (_value: unknown, params: any) => params?.data?.symbolSize ?? 18,
            cursor: onSelectionChange ? 'pointer' : 'default',
            tooltip: {
                trigger: 'item',
                formatter: (param: any) => buildBubbleTooltip((param?.data?.point as LotBubblePoint | undefined) ?? null),
            },
        } as echarts.SeriesOption);

        // Centre marker: silent so hover/click fall through to the bubble beneath; shape + colour encode
        // the lot's open / partially-closed / closed state.
        series.push({
            id: 'lot-performance-bubble-centers',
            name: 'lot-performance-bubble-centers',
            type: 'scatter',
            clip: true,
            silent: true,
            z: 7,
            data: renderable.map((entry) => ({
                value: [entry.point.openingDate, entry.yValue],
                symbol: lotStateSymbol(entry.point.state),
                symbolOffset: [entry.offsetX, 0],
                itemStyle: {
                    color: lotStateColor(entry.point.state, isDark),
                    borderColor: isDark ? '#0f172a' : '#ffffff',
                    borderWidth: 1,
                    opacity: entry.point.active ? 1 : 0.28,
                },
            })),
            symbolSize: 6,
            tooltip: {show: false},
        } as echarts.SeriesOption);

        // Legend-only keys explaining the bubble-centre state glyphs (open ● / partial ◆ / closed ▮).
        // Empty-data series so nothing is plotted; listed only for states actually present in the period.
        const presentStates = (['OPEN', 'PARTIAL', 'CLOSED'] as LotDisplayState[]).filter((state) => renderable.some((entry) => entry.point.state === state));
        for (const state of presentStates) {
            series.push({
                name: lotBubbleStateLabel(state),
                type: 'scatter',
                data: [],
                symbol: lotStateSymbol(state),
                symbolSize: 10,
                silent: true,
                itemStyle: {color: lotStateColor(state, isDark)},
                tooltip: {show: false},
            } as echarts.SeriesOption);
        }

        return series;
    }

    function buildSeries(): echarts.SeriesOption[] {
        const valueKey: ValueKey = displayMode === 'absolute' ? 'absolute' : 'percent';
        const series: echarts.SeriesOption[] = [];

        for (const brokerSeries of groupedChartData.realSeries) {
            if (displayMode === 'absolute' && !brokerSeries.hasAbsoluteData) continue;
            if (displayMode === 'percentage' && !brokerSeries.hasPercentData) continue;
            const color = getSeriesColor(brokerSeries);
            series.push({
                name: `${labels.wac} — ${brokerSeries.name}`,
                type: 'line',
                data: aggregateValuePoints(brokerSeries.points, valueKey),
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
                    data: aggregateValuePoints(combinedSeries.points, valueKey),
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
            const marketColor = isDark ? '#4ade80' : '#16a34a';
            // Where the value is estimated from the last-known trade (no real quote), dash the segment
            // that *ends* on that point so the estimated stretch reads as such while staying one curve.
            const marketData = aggregateValuePoints(groupedChartData.marketPricePoints, valueKey).map((item) => {
                const date = String(item.value[0]);
                return groupedChartData.estimatedByDate.get(date) === true ? {...item, lineStyle: {type: 'dashed' as const}} : item;
            });
            series.push({
                name: labels.marketPrice,
                type: 'line',
                data: marketData,
                showSymbol: false,
                symbol: 'circle',
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 2.5, color: marketColor},
                itemStyle: {color: marketColor},
            });
        }

        for (const definition of buildMarkerSeriesDefinitions()) {
            const markerSeries = groupedChartData.markerSeries.find((seriesGroup) => seriesGroup.category === definition.key);
            if (!markerSeries || markerSeries.points.length === 0) continue;

            series.push({
                name: definition.label,
                type: 'scatter',
                symbol: definition.symbol,
                symbolSize: definition.symbolSize,
                symbolRotate: definition.symbolRotate,
                clip: false,
                z: 5,
                data: markerSeries.points.map((point) => ({
                    name: point.id,
                    value: [point.date, point[valueKey]],
                    symbolOffset: [0, point.verticalOffsetPx],
                    meta: point,
                })),
                itemStyle: {
                    color: definition.color,
                    opacity: 0.96,
                    borderColor: isDark ? '#0f172a' : '#ffffff',
                    borderWidth: 1.5,
                },
                emphasis: {
                    scale: 1.15,
                    itemStyle: {
                        borderColor: isDark ? '#e2e8f0' : '#0f172a',
                        borderWidth: 2,
                    },
                },
                tooltip: {
                    trigger: 'item',
                    formatter: (param: any) => buildMarkerTooltip((param?.data?.meta as EventMarkerDatum | undefined) ?? null),
                },
            });
        }

        series.push(...buildLotBubbleSeries());

        return series;
    }

    function markerTooltipRow(label: string, value: string, color?: string): string {
        return buildTooltipRow(escapeHtml(label), escapeHtml(value), color);
    }

    function splitRatioText(event: LotTimelineEventSchema): string | null {
        const ratio = parseNumber(event.ratio);
        return ratio == null ? null : `${formatDecimalForDisplay(ratio, {minFrac: 0, maxFrac: 8})}:1`;
    }

    function saleHeaderLabel(snapshot: EventStateSnapshot | null): string {
        if (snapshot?.quantityAfter == null) return labels.eventType.SELL;
        return Math.abs(snapshot.quantityAfter) <= LOT_BUBBLE_ZERO_EPS ? labels.completeSale : labels.partialSale;
    }

    function quantityEffectText(event: LotTimelineEventSchema, snapshot: EventStateSnapshot | null): string {
        if (snapshot?.quantityBefore != null && snapshot.quantityAfter != null) {
            const delta = snapshot.quantityAfter - snapshot.quantityBefore;
            return `${formatSignedQuantityValue(delta)} (${formatQuantityValue(snapshot.quantityBefore)} → ${formatQuantityValue(snapshot.quantityAfter)})`;
        }

        const quantity = parseNumber(event.quantity);
        if (quantity == null) return '—';
        const sign = event.kind === 'ADJUSTMENT_OUT' ? -1 : 1;
        return formatSignedQuantityValue(sign * Math.abs(quantity));
    }

    function transferIntervalText(datum: EventMarkerDatum): string {
        const departDate = datum.event.kind === 'TRANSFER_ARRIVE' ? datum.transferDepartDate : datum.date;
        const arriveDate = datum.event.kind === 'TRANSFER_DEPART' ? datum.transferArriveDate : datum.date;
        if (departDate != null && arriveDate != null && departDate !== arriveDate) {
            return `${formatDate(departDate)} → ${formatDate(arriveDate)}`;
        }
        return formatDate(datum.date);
    }

    function markerHeaderLabel(event: LotTimelineEventSchema, snapshot: EventStateSnapshot | null): string {
        if (event.kind === 'SELL') return saleHeaderLabel(snapshot);
        if (event.kind === 'SPLIT') {
            const ratio = splitRatioText(event);
            return ratio == null ? eventKindLabel(event.kind) : `${eventKindLabel(event.kind)} ${ratio}`;
        }
        return eventKindLabel(event.kind);
    }

    function buildMarkerTooltip(datum: EventMarkerDatum | null): string {
        if (!datum) return '';

        const theme = buildTooltipTheme(isDark);
        const event = datum.event;
        const snapshot = eventStateSnapshots.get(datum.id) ?? null;
        const rows: string[] = [];

        if (event.kind === 'BUY') {
            const quantity = parseNumber(event.quantity);
            const unitPrice = parseNumber(event.unit_price);
            const openingValue = quantity != null && unitPrice != null ? Math.abs(quantity) * unitPrice : null;
            rows.push(markerTooltipRow(labels.quantity, quantity == null ? '—' : formatQuantityValue(quantity)));
            rows.push(markerTooltipRow(labels.unitPrice, formatMaybeMoney(unitPrice)));
            rows.push(markerTooltipRow(labels.openingValue, formatMaybeMoney(openingValue)));
            rows.push(markerTooltipRow(labels.broker, brokerName(safeInt(event.broker_id))));
        } else if (event.kind === 'SELL') {
            const quantity = parseNumber(event.quantity);
            const salePrice = parseNumber(event.close_unit_price ?? event.unit_price);
            const proceeds = parseNumber(event.proceeds);
            const realizedPnl = parseNumber(event.realized_pnl);
            const residualQuantity = snapshot?.quantityAfter ?? null;
            rows.push(markerTooltipRow(labels.quantitySold, quantity == null ? '—' : formatQuantityValue(quantity)));
            if (residualQuantity != null && Math.abs(residualQuantity) > LOT_BUBBLE_ZERO_EPS) {
                rows.push(markerTooltipRow(labels.residualQuantity, formatQuantityValue(residualQuantity)));
            }
            rows.push(markerTooltipRow(labels.salePrice, formatMaybeMoney(salePrice)));
            rows.push(markerTooltipRow(labels.proceeds, formatMaybeMoney(proceeds)));
            rows.push(markerTooltipRow(labels.realizedPnl, formatMaybeMoney(realizedPnl)));
        } else if (event.kind === 'TRANSFER_DEPART' || event.kind === 'TRANSFER_ARRIVE') {
            const sourceBrokerId = safeInt(event.source_broker_id);
            const destinationBrokerId = safeInt(event.destination_broker_id);
            rows.push(markerTooltipRow(labels.from, brokerName(sourceBrokerId)));
            rows.push(markerTooltipRow(labels.to, brokerName(destinationBrokerId)));
            rows.push(markerTooltipRow(labels.quantity, eventQuantityText(event) ?? '—'));
            rows.push(markerTooltipRow(labels.transitInterval, transferIntervalText(datum)));
        } else if (event.kind === 'ADJUSTMENT_IN' || event.kind === 'ADJUSTMENT_OUT') {
            rows.push(markerTooltipRow(labels.adjustmentType, eventKindLabel(event.kind)));
            rows.push(markerTooltipRow(labels.eventDate, formatDate(event.date)));
            rows.push(markerTooltipRow(labels.quantity, eventQuantityText(event) ?? '—'));
            rows.push(markerTooltipRow(labels.quantityEffect, quantityEffectText(event, snapshot)));
        } else if (event.kind === 'SPLIT') {
            const ratio = parseNumber(event.ratio);
            const fallbackAfterQuantity = parseNumber(event.quantity);
            const previousQuantity = snapshot?.quantityBefore ?? (ratio != null && ratio !== 0 && fallbackAfterQuantity != null ? Math.abs(fallbackAfterQuantity) / ratio : null);
            const nextQuantity = snapshot?.quantityAfter ?? (previousQuantity != null && ratio != null ? previousQuantity * ratio : fallbackAfterQuantity == null ? null : Math.abs(fallbackAfterQuantity));
            const previousPrice = snapshot?.unitPriceBefore ?? null;
            const nextPrice = snapshot?.unitPriceAfter ?? (previousPrice != null && ratio != null && ratio !== 0 ? previousPrice / ratio : null);
            rows.push(markerTooltipRow(labels.previousQuantity, formatMaybeQuantity(previousQuantity)));
            rows.push(markerTooltipRow(labels.nextQuantity, formatMaybeQuantity(nextQuantity)));
            rows.push(markerTooltipRow(labels.previousPrice, formatMaybeMoney(previousPrice)));
            rows.push(markerTooltipRow(labels.nextPrice, formatMaybeMoney(nextPrice)));
            rows.push(markerTooltipRow(labels.totalCost, labels.unchanged));
        }

        const header = `${markerHeaderLabel(event, snapshot)} · ${formatDate(datum.date)}`;
        return `<div style="font-size:11px;color:${theme.textColor}">${buildTooltipHeader(escapeHtml(header), theme.textColor)}${buildTooltipDivider(theme.border)}${rows.join('')}</div>`;
    }

    function buildTooltip(params: any[]): string {
        const theme = buildTooltipTheme(isDark);
        const markerParams = params.filter((param) => param?.seriesType === 'scatter' && param?.data?.meta);
        if (markerParams.length === 1) {
            return buildMarkerTooltip((markerParams[0].data.meta as EventMarkerDatum | undefined) ?? null);
        }

        const rawDate: number | string = params[0]?.axisValue ?? params[0]?.value?.[0] ?? '';
        const rows = params
            .filter((param) => param?.seriesType !== 'scatter')
            .map((param) => {
                const rawValue = Array.isArray(param.value) ? param.value[1] : param.value;
                if (rawValue == null || rawValue === '') return null;
                const value = Number(rawValue);
                if (!Number.isFinite(value)) return null;
                const formatted = displayMode === 'absolute' ? formatCurrencyAmountPlain(value, currency) : formatPercent(value);
                return buildTooltipRow(escapeHtml(String(param.seriesName ?? '')), escapeHtml(formatted), typeof param.color === 'string' ? param.color : undefined);
            })
            .filter((row): row is string => row != null);

        if (rows.length === 0) return '';
        return `<div style="font-size:11px;color:${theme.textColor}">${buildTooltipHeader(escapeHtml(formatDate(rawDate)), theme.textColor)}${buildTooltipDivider(theme.border)}${rows.join('')}</div>`;
    }

    /** Legend names, excluding internal helper series that shouldn't appear as toggles: the per-lot
     * bubble→baseline connectors and the bubble state centre markers. Keeps the real WAC/market lines,
     * event markers, income markers and the single "lot-performance-bubbles" entry. */
    function collectLegendNames(series: echarts.SeriesOption[]): string[] {
        const names: string[] = [];
        for (const item of series) {
            const name = (item as {name?: unknown}).name;
            if (typeof name !== 'string' || name.length === 0) continue;
            if (name.startsWith('__')) continue;
            if (name.startsWith('lot-bubble-connector')) continue;
            if (name === 'lot-performance-bubble-centers') continue;
            names.push(name);
        }
        return names;
    }

    function buildOption(): echarts.EChartsOption {
        const theme = buildTooltipTheme(isDark);
        const gridColors = buildGridColors(isDark);
        const series = attachIncomeMarkers(buildSeries());
        const rawXBounds = getXAxisBounds();
        // Derive the multi-year flag from the *raw* bounds so the horizontal bubble padding below can't
        // nudge an edge across a year boundary and spuriously flip the axis to the year-labelled format.
        const multiYearAxis = !!rawXBounds && new Date(rawXBounds.min).getFullYear() !== new Date(rawXBounds.max).getFullYear();
        const xAxisBounds = padXBoundsForBubbles(rawXBounds);
        const autoYBounds = computeAutoYAxisBounds(displayMode === 'absolute' ? 'absolute' : 'percent');
        const yAxisMin = displayMode === 'percentage' ? (autoYBounds ? Math.min(0, autoYBounds.min) : (value: {min: number}) => Math.min(0, value.min)) : absYFromZero ? 0 : ((autoYBounds?.min ?? null) as unknown as number);
        const yAxisMax = displayMode === 'percentage' ? (autoYBounds ? Math.max(0, autoYBounds.max) : (value: {max: number}) => Math.max(0, value.max)) : ((autoYBounds?.max ?? null) as unknown as number);

        // In percentage mode, emphasise the 0% baseline so gains/losses read against a clear zero.
        if (displayMode === 'percentage') {
            series.push({
                name: '__zero-baseline',
                type: 'line',
                data: [],
                silent: true,
                markLine: {
                    silent: true,
                    symbol: 'none',
                    animation: false,
                    label: {show: false},
                    lineStyle: {color: isDark ? 'rgba(148,163,184,0.75)' : 'rgba(71,85,105,0.6)', width: 1.5, type: 'solid'},
                    data: [{yAxis: 0}],
                },
                z: 0,
                zlevel: 0,
            } as echarts.SeriesOption);
        }

        return {
            ...CHART_ANIMATION_CONFIG,
            grid: {
                top: GRID_TOP_PX,
                right: GRID_RIGHT_PX,
                bottom: GRID_BOTTOM_PX,
                left: GRID_LEFT_PX,
                containLabel: false,
            },
            legend: {
                type: 'scroll',
                data: collectLegendNames(series),
                top: 4,
                left: 'center',
                right: 8,
                itemWidth: 10,
                itemHeight: 10,
                itemGap: 12,
                pageIconColor: gridColors.textColor,
                pageTextStyle: {
                    color: gridColors.textColor,
                },
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
                ...(xAxisBounds ? {min: xAxisBounds.min, max: xAxisBounds.max} : {}),
                axisLine: {
                    lineStyle: {color: gridColors.gridColor},
                },
                axisTick: {show: false},
                splitLine: {show: false},
                axisLabel: {
                    color: gridColors.textColor,
                    hideOverlap: true,
                    formatter: (value: number) => formatShortDate(value, multiYearAxis),
                },
            },
            yAxis: {
                type: 'value',
                scale: true,
                // Always set min/max explicitly: setOption merges yAxis, so omitting them lets the
                // percentage-mode 0-clamp persist into absolute mode (user report). Runtime null =
                // "auto" (ECharts clears the merged bound); cast keeps TS happy without changing it.
                min: yAxisMin,
                max: yAxisMax,
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
            series,
            // Preserve the shared zoom window across re-renders: setOption otherwise resets
            // dataZoom to 0-100 on every data/label change, silently desyncing this chart from
            // the Gantt (whose window stayed put). Applying the external window here keeps the
            // x-axis in sync; setOption does not re-emit a 'dataZoom' event, so no ping-pong.
            dataZoom: applySharedZoomWindow(buildDataZoom([0])),
        };
    }

    function applySharedZoomWindow<T extends {start?: number; end?: number}>(zooms: T[]): T[] {
        if (externalZoomStart == null || externalZoomEnd == null) return zooms;
        return zooms.map((zoom) => ({...zoom, start: externalZoomStart as number, end: externalZoomEnd as number}));
    }

    function setupResizeObserver() {
        if (!chartContainer || resizeObserver) return;
        resizeObserver = new ResizeObserver(() => {
            chartInstance?.resize();
            scheduleResolutionSync();
        });
        resizeObserver.observe(chartContainer);
    }

    function renderChart(opts?: {animate?: boolean}) {
        if (!chartContainer) return;

        syncTheme();
        resetResolutionIfInputsChanged();

        if (chartInstance && chartInstance.getDom() !== chartContainer) {
            tooltipCleanup?.();
            resizeObserver?.disconnect();
            resizeObserver = null;
            dataZoomTouchPanHandle?.dispose();
            dataZoomTouchPanHandle = null;
            dataZoomSyncHandle?.dispose();
            dataZoomSyncHandle = null;
            dataZoomResolutionCleanup?.();
            dataZoomResolutionCleanup = null;
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
            const zoomInstance = chartInstance;
            const onDataZoom = () => scheduleResolutionSync();
            zoomInstance.on('dataZoom', onDataZoom);
            dataZoomResolutionCleanup = () => zoomInstance.off('dataZoom', onDataZoom);
            chartInstance.on('dblclick', (params: any) => {
                const event = (params?.seriesType === 'scatter' ? (params?.data?.meta as EventMarkerDatum | undefined)?.event : undefined) ?? null;
                if (event) onEventDoubleClick?.(event);
            });
            chartInstance.on('click', (params: any) => {
                const lotBubbleId = params?.data?.lotBubbleId as number | undefined;
                if (lotBubbleId == null || !onSelectionChange) return;
                const current = new Set(selectedLotIds);
                if (current.has(lotBubbleId)) current.delete(lotBubbleId);
                else current.add(lotBubbleId);
                onSelectionChange(Array.from(current));
            });
        }

        if (!showChart) {
            currentResolution = 'daily';
            shouldPickInitialResolution = true;
            chartInstance.clear();
            return;
        }

        pickInitialResolution();

        const option = buildOption();
        if (opts?.animate === false) {
            // A selection-only change just re-tints bubbles/lines — don't replay the entry animation.
            (option as {animation?: boolean}).animation = false;
            (option as {animationDurationUpdate?: number}).animationDurationUpdate = 0;
        }
        chartInstance.setOption(option, CHART_SET_OPTION_OPTS);
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
            if (resolutionDebounceTimer) clearTimeout(resolutionDebounceTimer);
            for (const timer of pulseTimers) clearTimeout(timer);
            pulseTimers = [];
            tooltipCleanup?.();
            darkModeObserver?.disconnect();
            resizeObserver?.disconnect();
            dataZoomTouchPanHandle?.dispose();
            dataZoomTouchPanHandle = null;
            dataZoomSyncHandle?.dispose();
            dataZoomSyncHandle = null;
            dataZoomResolutionCleanup?.();
            dataZoomResolutionCleanup = null;
            chartInstance?.dispose();
        };
    });

    $effect(() => {
        if (displayMode === 'percentage' && !hasPercentData && hasAbsoluteData) {
            displayMode = 'absolute';
        }
    });

    let prevRenderDeps: unknown[] = [];
    $effect(() => {
        const renderDeps: unknown[] = [groupedChartData, displayMode, absYFromZero, currency, labels, $currentLanguage, brokers, xAxisRange, eventStateSnapshots, lotBubblePoints];
        void selectedLotIds;

        // Selection-only re-renders leave every geometry input referentially identical (the $derived
        // inputs only get a new reference when their sources change) — suppress animation for those so
        // a tap doesn't replay the whole chart's entry transition (see mobile Gantt tooltip fix).
        const selectionOnly = prevRenderDeps.length > 0 && renderDeps.every((value, index) => value === prevRenderDeps[index]);
        prevRenderDeps = renderDeps;

        if (!chartContainer) return;
        tick().then(() => {
            renderChart(selectionOnly ? {animate: false} : undefined);
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
        scheduleResolutionSync();
    });
</script>

<div bind:this={wrapperEl} class="rounded-lg border border-gray-200/80 bg-gray-50/80 p-4 dark:border-slate-700 dark:bg-slate-900/30" data-testid="lot-wac-price-chart">
    <div class="mb-3 flex items-center justify-between gap-3">
        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-200">{labels.wac} / {labels.marketPrice}</h3>

        <div class="flex items-center gap-2">
            {#if displayMode === 'absolute'}
                <div class="flex overflow-hidden rounded-lg border border-gray-200 text-xs font-medium dark:border-slate-600" data-testid="lot-wac-yaxis-toggle">
                    <button
                        type="button"
                        class="px-3 py-1 transition-colors {!absYFromZero ? 'bg-libre-green text-white' : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-400 dark:hover:bg-slate-700'}"
                        onclick={() => (absYFromZero = false)}
                        aria-pressed={!absYFromZero}
                        data-testid="lot-wac-yaxis-auto"
                    >
                        {labels.yAuto}
                    </button>
                    <button
                        type="button"
                        class="border-l border-gray-200 px-3 py-1 transition-colors dark:border-slate-600 {absYFromZero ? 'bg-libre-green text-white' : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-400 dark:hover:bg-slate-700'}"
                        onclick={() => (absYFromZero = true)}
                        aria-pressed={absYFromZero}
                        data-testid="lot-wac-yaxis-zero"
                    >
                        {labels.yFromZero}
                    </button>
                </div>
            {/if}

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
    </div>

    <div class="relative h-72 w-full">
        <div class="absolute left-2 top-2 z-10 pointer-events-none">
            <ResolutionBadge resolution={currentResolution} />
        </div>

        {#if emptyMessage}
            <div class="absolute inset-0 z-10 flex items-center justify-center text-center text-sm text-gray-400 dark:text-gray-500">
                {emptyMessage}
            </div>
        {/if}

        <div bind:this={chartContainer} class="h-full w-full" class:invisible={!showChart}></div>
    </div>
</div>
