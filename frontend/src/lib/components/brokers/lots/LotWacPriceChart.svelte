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
    import {buildGridColors, buildTooltipDivider, buildTooltipHeader, buildTooltipRow, buildTooltipTheme, scheduleFirstRenderStabilityFix, setupTooltipAutoHide, tooltipPositionSide} from '$lib/components/charts/echartsTooltipHelpers';
    import {getBrokerColor, type BrokerLike} from '$lib/utils/broker/brokerColors';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';

    type BrokerWACHistoryPoint = z.infer<typeof schemas.BrokerWACHistoryPoint>;
    type CumulativeWACHistoryPoint = z.infer<typeof schemas.CumulativeWACHistoryPoint>;
    type LotPriceHistoryPoint = z.infer<typeof schemas.LotPriceHistoryPoint>;
    type LotTimelineEventSchema = z.infer<typeof schemas.LotTimelineEventSchema>;
    type DisplayMode = 'absolute' | 'percentage';
    type EventMarkerSeriesKind = 'buy' | 'sell' | 'transfer' | 'adjustment' | 'split';

    const DAY_MS = 24 * 60 * 60 * 1000;
    const TRANSFER_MARKER_SYMBOL = 'path://M1 10 L6 5 L6 8 L14 8 L14 5 L19 10 L14 15 L14 12 L6 12 L6 15 Z';
    const SPLIT_MARKER_SYMBOL = 'path://M8 1 H12 V8 H16 V12 H12 V19 H8 V12 H4 V8 H8 Z';
    const MARKER_VERTICAL_OFFSET_STEP = 12;
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
        marketPriceDate: string;
        transferDepartDate: string | null;
        verticalOffsetPx: number;
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
        color: string;
    }

    let {brokerWacHistory = [], cumulativeWacHistory = [], priceHistory = [], lotEvents = [], brokers = [], currency, xAxisRange = null, onZoomChange, externalZoomStart = null, externalZoomEnd = null, onRangeComputed, onLoadingChange}: ComponentProps = $props();

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

    function eventQuantityText(event: LotTimelineEventSchema): string | null {
        const quantity = parseNumber(event.quantity);
        return quantity == null ? null : formatQuantityValue(quantity);
    }

    function deriveEventAmount(event: LotTimelineEventSchema): number | null {
        const quantity = parseNumber(event.quantity);
        const unitPrice = parseNumber(event.unit_price);

        if (event.kind === 'SELL') {
            return parseNumber(event.proceeds) ?? (quantity != null && unitPrice != null ? Math.abs(quantity) * unitPrice : null);
        }
        if (event.kind === 'BUY') {
            return quantity != null && unitPrice != null ? -Math.abs(quantity) * unitPrice : null;
        }
        if (event.kind === 'ADJUSTMENT_OUT') {
            return parseNumber(event.proceeds) ?? (quantity != null && unitPrice != null ? -Math.abs(quantity) * unitPrice : null);
        }
        if (event.kind === 'ADJUSTMENT_IN') {
            return quantity != null && unitPrice != null ? Math.abs(quantity) * unitPrice : null;
        }
        return null;
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

    function buildMarkerSeriesDefinitions(): MarkerSeriesDefinition[] {
        return [
            {
                key: 'buy',
                label: labels.markerLegend.buy,
                symbol: 'circle',
                symbolSize: 10,
                color: isDark ? '#86efac' : '#16a34a',
            },
            {
                key: 'sell',
                label: labels.markerLegend.sell,
                symbol: 'diamond',
                symbolSize: 12,
                color: isDark ? '#fca5a5' : '#dc2626',
            },
            {
                key: 'transfer',
                label: labels.markerLegend.transfer,
                symbol: TRANSFER_MARKER_SYMBOL,
                symbolSize: 15,
                color: isDark ? '#93c5fd' : '#2563eb',
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
        const days = $_('datePicker.granularity.days');
        const combined = $_('brokers.lots.combined');
        const noData = $_('common.noData');
        const broker = $_('common.broker');
        const quantity = $_('common.quantity');
        const amount = $_('common.amount');
        const from = $_('common.from');
        const to = $_('common.to');
        const unitPrice = $_('brokers.lots.chartMarkers.unitPrice');
        const transitInterval = $_('brokers.lots.chartMarkers.transitInterval');
        const ratio = $_('brokers.lots.chartMarkers.ratio');
        const proceeds = $_('brokers.lots.chartMarkers.proceeds');
        const realizedPnl = $_('brokers.lots.chartMarkers.realizedPnl');
        const markerLegendBuy = $_('brokers.lots.chartMarkers.legend.buy');
        const markerLegendSell = $_('brokers.lots.chartMarkers.legend.sell');
        const markerLegendTransfer = $_('brokers.lots.chartMarkers.legend.transfer');
        const markerLegendAdjustment = $_('brokers.lots.chartMarkers.legend.adjustment');
        const markerLegendSplit = $_('brokers.lots.chartMarkers.legend.split');
        const eventTypeBuy = $_('brokers.lots.chartMarkers.eventType.BUY');
        const eventTypeSell = $_('brokers.lots.chartMarkers.eventType.SELL');
        const eventTypeAdjustmentIn = $_('brokers.lots.chartMarkers.eventType.ADJUSTMENT_IN');
        const eventTypeAdjustmentOut = $_('brokers.lots.chartMarkers.eventType.ADJUSTMENT_OUT');
        const eventTypeTransferDepart = $_('brokers.lots.chartMarkers.eventType.TRANSFER_DEPART');
        const eventTypeTransferArrive = $_('brokers.lots.chartMarkers.eventType.TRANSFER_ARRIVE');
        const eventTypeSplit = $_('brokers.lots.chartMarkers.eventType.SPLIT');

        return {
            wac: 'WAC',
            marketPrice: !marketPrice || marketPrice === 'chart.marketPrice' ? 'Market Price' : marketPrice,
            abs: !abs || abs === 'dashboard.abs' ? 'ABS' : abs,
            pct: !pct || pct === 'dashboard.pct' ? '%' : pct,
            days: !days || days === 'datePicker.granularity.days' ? 'Days' : days,
            combined: !combined || combined === 'brokers.lots.combined' ? 'Combined' : combined,
            noData: !noData || noData === 'common.noData' ? 'No data' : noData,
            broker: !broker || broker === 'common.broker' ? 'Broker' : broker,
            quantity: !quantity || quantity === 'common.quantity' ? 'Quantity' : quantity,
            amount: !amount || amount === 'common.amount' ? 'Amount' : amount,
            from: !from || from === 'common.from' ? 'From' : from,
            to: !to || to === 'common.to' ? 'To' : to,
            unitPrice: !unitPrice || unitPrice === 'brokers.lots.chartMarkers.unitPrice' ? 'Unit Price' : unitPrice,
            transitInterval: !transitInterval || transitInterval === 'brokers.lots.chartMarkers.transitInterval' ? 'Transit Interval' : transitInterval,
            ratio: !ratio || ratio === 'brokers.lots.chartMarkers.ratio' ? 'Ratio' : ratio,
            proceeds: !proceeds || proceeds === 'brokers.lots.chartMarkers.proceeds' ? 'Proceeds' : proceeds,
            realizedPnl: !realizedPnl || realizedPnl === 'brokers.lots.chartMarkers.realizedPnl' ? 'Realized P&L' : realizedPnl,
            markerLegend: {
                buy: !markerLegendBuy || markerLegendBuy === 'brokers.lots.chartMarkers.legend.buy' ? 'Buys' : markerLegendBuy,
                sell: !markerLegendSell || markerLegendSell === 'brokers.lots.chartMarkers.legend.sell' ? 'Sales' : markerLegendSell,
                transfer: !markerLegendTransfer || markerLegendTransfer === 'brokers.lots.chartMarkers.legend.transfer' ? 'Transfers' : markerLegendTransfer,
                adjustment: !markerLegendAdjustment || markerLegendAdjustment === 'brokers.lots.chartMarkers.legend.adjustment' ? 'Adjustments' : markerLegendAdjustment,
                split: !markerLegendSplit || markerLegendSplit === 'brokers.lots.chartMarkers.legend.split' ? 'Split' : markerLegendSplit,
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
        const rawMarkerPoints: EventMarkerDatum[] = [];
        for (const event of lotEvents) {
            const category = eventCategory(event.kind);
            if (category == null) continue;

            const marketPricePoint = resolveMarketPriceAtOrBefore(event.date, marketPriceLookupPoints);
            if (!marketPricePoint) continue;

            const transferDepart = event.kind === 'TRANSFER_ARRIVE' ? findTransferDepartEvent(event, transferDepartEvents) : null;
            rawMarkerPoints.push({
                id: eventKey(event),
                date: event.date,
                absolute: marketPricePoint.absolute,
                percent: marketPricePoint.percent,
                category,
                event,
                marketPriceDate: marketPricePoint.date,
                transferDepartDate: transferDepart?.date ?? null,
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
            markerSeries,
            minDate: allDates[0] ?? null,
            maxDate: allDates.at(-1) ?? null,
            hasAbsoluteData: realSeries.some((series) => series.hasAbsoluteData) || (combinedSeries?.hasAbsoluteData ?? false) || marketPricePoints.some((point) => point.absolute != null) || rawMarkerPoints.some((point) => point.absolute != null),
            hasPercentData: realSeries.some((series) => series.hasPercentData) || (combinedSeries?.hasPercentData ?? false) || marketPricePoints.some((point) => point.percent != null) || rawMarkerPoints.some((point) => point.percent != null),
            totalPointCount: brokerWacHistory.length + cumulativeWacHistory.length + priceHistory.length + rawMarkerPoints.length,
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

        for (const definition of buildMarkerSeriesDefinitions()) {
            const markerSeries = groupedChartData.markerSeries.find((seriesGroup) => seriesGroup.category === definition.key);
            if (!markerSeries) continue;

            series.push({
                name: definition.label,
                type: 'scatter',
                symbol: definition.symbol,
                symbolSize: definition.symbolSize,
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

        return series;
    }

    function buildMarkerTooltip(datum: EventMarkerDatum | null): string {
        if (!datum) return '';

        const theme = buildTooltipTheme(isDark);
        const event = datum.event;
        const quantity = eventQuantityText(event);
        const amount = deriveEventAmount(event);
        const unitPrice = parseNumber(event.unit_price);
        const proceeds = parseNumber(event.proceeds);
        const realizedPnl = parseNumber(event.realized_pnl);
        const ratio = parseNumber(event.ratio);
        const brokerId = safeInt(event.broker_id) ?? safeInt(event.destination_broker_id) ?? safeInt(event.source_broker_id);
        const rows: string[] = [];

        if (datum.category === 'transfer') {
            const sourceBrokerId = safeInt(event.source_broker_id);
            const destinationBrokerId = safeInt(event.destination_broker_id);
            if (sourceBrokerId != null) {
                rows.push(buildTooltipRow(escapeHtml(labels.from), escapeHtml(brokerName(sourceBrokerId))));
            }
            if (destinationBrokerId != null) {
                rows.push(buildTooltipRow(escapeHtml(labels.to), escapeHtml(brokerName(destinationBrokerId))));
            }
            if (sourceBrokerId == null && destinationBrokerId == null && brokerId != null) {
                rows.push(buildTooltipRow(escapeHtml(labels.broker), escapeHtml(brokerName(brokerId))));
            }
        } else if (brokerId != null) {
            rows.push(buildTooltipRow(escapeHtml(labels.broker), escapeHtml(brokerName(brokerId))));
        }

        if (quantity != null) {
            rows.push(buildTooltipRow(escapeHtml(labels.quantity), escapeHtml(quantity)));
        }
        if (amount != null) {
            rows.push(buildTooltipRow(escapeHtml(labels.amount), escapeHtml(formatCurrencyAmountPlain(amount, currency))));
        }
        if (unitPrice != null) {
            rows.push(buildTooltipRow(escapeHtml(labels.unitPrice), escapeHtml(formatCurrencyAmountPlain(unitPrice, currency))));
        }
        if (datum.category === 'transfer') {
            const transitInterval = datum.transferDepartDate != null && datum.transferDepartDate !== datum.date ? `${formatDate(datum.transferDepartDate)} → ${formatDate(datum.date)}` : formatDate(datum.date);
            rows.push(buildTooltipRow(escapeHtml(labels.transitInterval), escapeHtml(transitInterval)));
        }
        if (ratio != null) {
            rows.push(buildTooltipRow(escapeHtml(labels.ratio), escapeHtml(formatDecimalForDisplay(ratio, {minFrac: 0, maxFrac: 8}))));
        }
        if (proceeds != null) {
            rows.push(buildTooltipRow(escapeHtml(labels.proceeds), escapeHtml(formatCurrencyAmountPlain(proceeds, currency))));
        }
        if (realizedPnl != null) {
            rows.push(buildTooltipRow(escapeHtml(labels.realizedPnl), escapeHtml(formatCurrencyAmountPlain(realizedPnl, currency))));
        }

        const marketPriceValue = datum.marketPriceDate === datum.date ? formatCurrencyAmountPlain(datum.absolute, currency) : `${formatCurrencyAmountPlain(datum.absolute, currency)} · ${formatDate(datum.marketPriceDate)}`;
        rows.push(buildTooltipRow(escapeHtml(labels.marketPrice), escapeHtml(marketPriceValue)));

        return `<div style="font-size:11px;color:${theme.textColor}">${buildTooltipHeader(escapeHtml(formatDate(datum.date)), theme.textColor)}<div style="font-size:12px;font-weight:600;color:${theme.textColor};margin-bottom:4px">${escapeHtml(eventKindLabel(event.kind))}</div>${buildTooltipDivider(theme.border)}${rows.join('')}</div>`;
    }

    function buildTooltip(params: any[]): string {
        const theme = buildTooltipTheme(isDark);
        const markerParams = params.filter((param) => param?.seriesType === 'scatter' && param?.data?.meta);
        if (markerParams.length === 1) {
            return buildMarkerTooltip((markerParams[0].data.meta as EventMarkerDatum | undefined) ?? null);
        }

        const rawDate: number | string = params[0]?.axisValue ?? params[0]?.value?.[0] ?? '';
        const elapsedDays = chartStartDate ? elapsedDaysBetween(chartStartDate, rawDate) : null;
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
                top: 62,
                right: 18,
                bottom: 34,
                left: 22,
                containLabel: true,
            },
            legend: {
                type: 'scroll',
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
