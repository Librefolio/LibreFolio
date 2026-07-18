<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {z} from 'zod';
    import {schemas} from '$lib/api';
    import {_} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import {CHART_ANIMATION_CONFIG, namedPoint} from '$lib/components/charts/echartsAnimationConfig';
    import {buildDataZoom, getChartZoomWindow} from '$lib/components/charts/chartCoreHelpers';
    import {attachDataZoomTouchPan, type DataZoomTouchPanHandle} from '$lib/components/charts/echartsDataZoomTouchPan';
    import {buildGridColors, buildTooltipDivider, buildTooltipHeader, buildTooltipRow, buildTooltipTheme, scheduleFirstRenderStabilityFix, setupTooltipAutoHide, tooltipPositionSide} from '$lib/components/charts/echartsTooltipHelpers';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';

    type LotSummarySchema = z.infer<typeof schemas.LotSummarySchema>;
    type LotValueHistoryPoint = z.infer<typeof schemas.LotValueHistoryPoint>;
    type LotReturnHistoryPoint = z.infer<typeof schemas.LotReturnHistoryPoint>;
    type ChartMode = 'value' | 'return';
    type LotValueSource = 'MARKET_PRICE' | 'ESTIMATED_AT_COST';

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
    // C1: Return chart can be read as weighted % (default) or as absolute currency P&L,
    // where the aggregate is the plain visible sum of the individual lots.
    let returnDisplay = $state<'percentage' | 'absolute'>('percentage');
    // C2: Value chart Y axis — automatic (data-fit) or anchored at 0.
    let valueYFromZero = $state(false);
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

    function safeScalar<T>(value: T | Array<T | null> | null | undefined): T | null {
        if (Array.isArray(value)) return value[0] ?? null;
        return value ?? null;
    }

    function safeString(value: string | Array<string | null> | null | undefined): string | null {
        return safeScalar(value);
    }

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

    function tr(key: string, fallback: string): string {
        const translated = $_(key);
        return !translated || translated === key ? fallback : translated;
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

    function escapeHtml(value: string): string {
        return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function formatShortDate(value: string): string {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return value;
        return date.toLocaleDateString($currentLanguage || undefined, {day: '2-digit', month: '2-digit'});
    }

    function formatLongDate(value: number | string): string {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return String(value);
        return date.toLocaleDateString($currentLanguage || undefined, {year: 'numeric', month: 'short', day: 'numeric'});
    }

    function formatAxisDate(value: number | string): string {
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
        return visibleLots.find((lot) => lot.label === name)?.lotId ?? null;
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

    const modeLabels = $derived.by(() => ({
        value: tr('common.value', 'Value'),
        return: tr('brokers.lots.modeReturn', 'Return'),
        valueTitle: tr('brokers.lots.valueComparisonTitle', 'Value of selected lots'),
        returnTitle: tr('brokers.lots.returnComparisonTitle', 'Return from opening date'),
        residualValue: tr('brokers.lots.aggregateResidualValue', 'Residual value'),
        residualValueEstimatedAtCost: tr('brokers.lots.aggregateResidualValueEstimatedAtCost', 'Residual value estimated at cost'),
        saleProceeds: tr('brokers.lots.aggregateSaleProceeds', 'Sale proceeds'),
        cumulativeIncome: tr('brokers.lots.aggregateCumulativeIncome', 'Cumulative income'),
        comprehensiveValue: tr('brokers.lots.aggregateComprehensiveValue', 'Comprehensive value'),
        aggregateOpeningValue: tr('brokers.lots.aggregateOpeningValue', 'Opening value'),
        aggregateReturn: tr('brokers.lots.aggregateReturn', 'Aggregate return'),
        aggregateReturnNotComputable: tr('brokers.lots.aggregateReturnNotComputable', 'Not computable (opening value <= 0)'),
        fifoPnl: tr('brokers.lots.fifoPnl', 'FIFO P&L'),
        totalReturn: tr('brokers.lots.totalReturn', 'Total return'),
        totalPnl: tr('brokers.lots.tooltip.totalPnl', 'Total P&L'),
        abs: tr('dashboard.abs', 'Abs'),
        pct: tr('dashboard.pct', '%'),
        yAuto: tr('brokers.lots.yAxisAuto', 'Auto'),
        yFromZero: tr('brokers.lots.yAxisFromZero', 'From 0'),
        openReturn: tr('brokers.lots.openReturn', 'Open Return'),
        selectLots: tr('brokers.lots.selectLotsToCompare', 'Select one or more lots to compare'),
        noVisibleLots: tr('brokers.lots.noVisibleLots', 'No visible lots in chart'),
        noData: tr('common.noData', 'No data'),
        estimatedAtCostLegend: tr('brokers.lots.estimatedAtCostLegend', 'Dashed neutral lines use value estimated at cost.'),
        incomeDividend: tr('brokers.lots.incomeMarkerDividend', 'Dividend'),
        incomeInterest: tr('brokers.lots.incomeMarkerInterest', 'Interest'),
        incomeType: tr('brokers.lots.incomeMarkerType', 'Type'),
        incomeDate: tr('brokers.lots.incomeMarkerDate', 'Transaction date'),
        incomeBroker: tr('brokers.lots.incomeMarkerBroker', 'Broker'),
        incomeAmount: tr('brokers.lots.incomeMarkerAmount', 'Amount'),
        incomeLotCount: tr('brokers.lots.incomeMarkerLotCount', 'Lots involved'),
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

    const returnLotsWithData = $derived.by(() => visibleLots.filter((lot) => returnPointsByLotId.get(lot.lotId)?.some((point) => point.totalReturn != null)));

    const aggregateReturnPoints = $derived.by(() => {
        if (returnLotsWithData.length < 2) return [] satisfies AggregateReturnPoint[];

        const totals = new Map<string, {date: string; pnlWithIncome: number; openingValue: number}>();
        for (const lot of returnLotsWithData) {
            for (const point of valuePointsByLotId.get(lot.lotId) ?? []) {
                const current = totals.get(point.date) ?? {date: point.date, pnlWithIncome: 0, openingValue: 0};
                current.pnlWithIncome += point.pnl + point.income;
                current.openingValue += point.originalCost;
                totals.set(point.date, current);
            }
        }

        return Array.from(totals.values())
            .map((point) => ({
                date: point.date,
                totalReturn: point.openingValue > 0 ? point.pnlWithIncome / point.openingValue : null,
                openingValue: point.openingValue,
                pnlWithIncome: point.pnlWithIncome,
            }))
            .sort((left, right) => left.date.localeCompare(right.date)) satisfies AggregateReturnPoint[];
    });

    const showAggregateReturn = $derived(returnLotsWithData.length >= 2 && aggregateReturnPoints.length > 0);

    const emptyMessage = $derived.by(() => {
        if (selectedLots.length === 0) return modeLabels.selectLots;
        if (visibleLots.length === 0) return modeLabels.noVisibleLots;

        if (mode === 'value') {
            return aggregatedValuePoints.length > 0 ? '' : modeLabels.noData;
        }

        return returnLotsWithData.length > 0 ? '' : modeLabels.noData;
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
                    if (returnDisplay === 'absolute') {
                        const vp = findPointAtOrBefore(valuePointsByLotId.get(lotId) ?? [], timestamp);
                        if (!vp) continue;
                        data.push({value: [event.date, vp.pnl + vp.income], incomeEvent: event, itemStyle: {color, opacity: 0.95}});
                    } else {
                        const point = findPointAtOrBefore(returnPointsByLotId.get(lotId) ?? [], timestamp);
                        if (!point || point.totalReturn == null) continue;
                        data.push({value: [event.date, point.totalReturn * 100], incomeEvent: event, itemStyle: {color, opacity: 0.95}});
                    }
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

        const range = xAxisRange ? ([xAxisRange.min, xAxisRange.max] as [string, string]) : seriesDataDateRange(series);
        if (!range) return series;

        const anchor: echarts.SeriesOption = {
            id: AXIS_TRIGGER_ANCHOR_ID,
            name: AXIS_TRIGGER_ANCHOR_ID,
            type: 'line',
            data: [namedPoint(range[0], 0), namedPoint(range[1], 0)],
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
        return returnLotsWithData
            .map((lot) => {
                if (excludedLotIds.has(lot.lotId)) return null;
                if (returnDisplay === 'absolute') {
                    const vp = findPointAtOrBefore(valuePointsByLotId.get(lot.lotId) ?? [], timestampMs);
                    if (!vp) return null;
                    return buildTooltipRow(escapeHtml(lot.label), escapeHtml(formatCurrencyAmountPlain(vp.pnl + vp.income, currency, {showSign: true})), lotColor(lot.lotId));
                }
                const point = findPointAtOrBefore(returnPointsByLotId.get(lot.lotId) ?? [], timestampMs);
                if (!point || point.totalReturn == null) return null;
                return buildTooltipRow(escapeHtml(lot.label), escapeHtml(formatPercent(point.totalReturn * 100)), lotColor(lot.lotId));
            })
            .filter((row): row is string => row != null);
    }

    function buildAggregateReturnTooltipRows(timestampMs: number): string[] {
        if (!showAggregateReturn) return [];
        const point = findPointAtOrBefore(aggregateReturnPoints, timestampMs);
        if (!point) return [];
        const value =
            returnDisplay === 'absolute'
                ? formatCurrencyAmountPlain(point.pnlWithIncome, currency, {showSign: true})
                : point.totalReturn == null || point.openingValue <= 0
                  ? modeLabels.aggregateReturnNotComputable
                  : formatPercent(point.totalReturn * 100);
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
        return `<div style="font-size:11px;color:${theme.textColor}">${buildTooltipHeader(escapeHtml(formatLongDate(rawDate)), theme.textColor)}${buildTooltipDivider(theme.border)}${axisRows.join('')}</div>`;
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
                const value = seriesValue(param);
                if (value == null) return null;
                const lotId = returnTooltipLotId(param);
                const lot = lotId == null ? null : visibleLots.find((item) => item.lotId === lotId);
                if (!lot) return null;
                const paramTimestamp = parseTimeMs(tooltipXValue(param));
                const returnPoint = paramTimestamp == null ? null : findPointAtOrBefore(returnPointsByLotId.get(lot.lotId) ?? [], paramTimestamp);
                if (!returnPoint || returnPoint.totalReturn == null) return null;

                const color = typeof param.color === 'string' ? param.color : lotColor(lot.lotId);
                const valuePoint = valuePointByLotDate.get(pointKey(lot.lotId, returnPoint.date));
                const headlineLabel = returnDisplay === 'absolute' ? modeLabels.totalPnl : modeLabels.totalReturn;
                const headlineValue = returnDisplay === 'absolute' ? formatCurrencyAmountPlain(value, currency, {showSign: true}) : formatPercent(value);
                const rows: string[] = [buildTooltipRow(escapeHtml(headlineLabel), escapeHtml(headlineValue), color)];

                if (returnPoint.relativeReturn != null) {
                    rows.push(buildTooltipRow(escapeHtml(modeLabels.openReturn), escapeHtml(formatPercent(returnPoint.relativeReturn * 100))));
                }
                if (valuePoint) {
                    rows.push(buildTooltipRow(escapeHtml(modeLabels.residualValue), escapeHtml(formatCurrencyAmountPlain(valuePoint.openValue, currency))));
                    rows.push(buildTooltipRow(escapeHtml(modeLabels.saleProceeds), escapeHtml(formatCurrencyAmountPlain(valuePoint.proceeds, currency))));
                    rows.push(
                        buildTooltipRow(escapeHtml(modeLabels.fifoPnl), `<span style="color:${valuePoint.pnl >= 0 ? (isDark ? '#4ade80' : '#16a34a') : isDark ? '#f87171' : '#dc2626'}">${escapeHtml(formatCurrencyAmountPlain(valuePoint.pnl, currency, {showSign: true}))}</span>`),
                    );
                }

                return `${buildTooltipHeader(escapeHtml(`${lot.label} · ${formatLongDate(returnPoint.date)}`), theme.textColor)}${rows.join('')}`;
            })
            .filter((block): block is string => block != null);
        const aggregateRows = timestamp == null ? [] : buildAggregateReturnTooltipRows(timestamp);
        const individualRows = timestamp == null ? [] : buildReturnIndividualTooltipRows(timestamp, excludedLotIds);
        const tooltipBlocks = [...(aggregateRows.length > 0 ? [aggregateRows.join('')] : []), ...blocks, ...(individualRows.length > 0 ? [individualRows.join('')] : [])];

        if (tooltipBlocks.length === 0) return '';
        return `<div style="font-size:11px;color:${theme.textColor}">${buildTooltipHeader(escapeHtml(formatLongDate(rawDate)), theme.textColor)}${buildTooltipDivider(theme.border)}${tooltipBlocks.join(buildTooltipDivider(theme.border))}</div>`;
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

        const series: echarts.SeriesOption[] = [
            {
                id: 'value-residual',
                name: residualSeriesName,
                type: 'line',
                stack: 'value-aggregate',
                data: aggregatedValuePoints.map((point) => namedPoint(point.date, point.openValue)),
                showSymbol: false,
                symbol: 'none',
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 1.8, color: residualLineColor, type: aggregateLineType},
                areaStyle: {color: withAlpha(residualLineColor, isDark ? 0.4 : 0.22)},
                itemStyle: {color: residualLineColor},
                emphasis: {scale: false, focus: 'none'},
                blur: {lineStyle: {opacity: 1}, itemStyle: {opacity: 1}, areaStyle: {opacity: isDark ? 0.4 : 0.22}},
                z: 1,
                zlevel: 0,
            },
            {
                id: 'value-proceeds',
                name: modeLabels.saleProceeds,
                type: 'line',
                stack: 'value-aggregate',
                data: aggregatedValuePoints.map((point) => namedPoint(point.date, point.proceeds)),
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
                data: aggregatedValuePoints.map((point) => namedPoint(point.date, point.income)),
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
                data: aggregatedValuePoints.map((point) => namedPoint(point.date, point.openValue + point.proceeds + point.income)),
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
                data: aggregatedValuePoints.map((point) => namedPoint(point.date, point.originalCost)),
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
                name: modeLabels.aggregateReturn,
                type: 'line',
                data: aggregateReturnPoints.map((point) => namedPoint(point.date, returnDisplay === 'absolute' ? point.pnlWithIncome : point.totalReturn == null ? null : point.totalReturn * 100)),
                showSymbol: false,
                symbol: 'none',
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 2.4, color},
                areaStyle: {color: withAlpha(color, isDark ? 0.18 : 0.14)},
                itemStyle: {color},
                emphasis: {scale: false, focus: 'none'},
                blur: {lineStyle: {opacity: 1}, itemStyle: {opacity: 1}, areaStyle: {opacity: isDark ? 0.18 : 0.14}},
                z: 2,
                zlevel: 0,
            });
        }

        for (const lot of returnLotsWithData) {
            const color = lotColor(lot.lotId);
            series.push({
                id: `return-${lot.lotId}`,
                name: lot.label,
                type: 'line',
                data:
                    returnDisplay === 'absolute'
                        ? (valuePointsByLotId.get(lot.lotId) ?? []).map((point) => namedPoint(point.date, point.pnl + point.income))
                        : (returnPointsByLotId.get(lot.lotId) ?? []).map((point) => namedPoint(point.date, point.totalReturn == null ? null : point.totalReturn * 100)),
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

        return attachIncomeMarkers(series);
    }

    /** Position dots for return-mode per-lot lines at a hovered date (r3 fix5). */
    function buildPerLotHoverDotData(axisValueMs: number): Array<{value: [number, number]; itemStyle: {color: string}}> {
        const dots: Array<{value: [number, number]; itemStyle: {color: string}}> = [];
        if (mode !== 'return') return dots;

        for (const lot of returnLotsWithData) {
            const point = findPointAtOrBefore(returnPointsByLotId.get(lot.lotId) ?? [], axisValueMs);
            if (!point || point.totalReturn == null) continue;
            dots.push({value: [axisValueMs, point.totalReturn * 100], itemStyle: {color: lotColor(lot.lotId)}});
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

        const theme = buildTooltipTheme(isDark);
        const gridColors = buildGridColors(isDark);
        const baseSeries = ensureAxisTriggerAnchor(mode === 'value' ? buildValueSeries() : buildReturnSeries());
        const legendData = baseSeries.map((item) => (item as {name?: unknown}).name).filter((name): name is string => typeof name === 'string' && name !== AXIS_TRIGGER_ANCHOR_ID && name !== PER_LOT_HOVER_DOTS_ID && name !== LOT_INCOME_MARKER_SERIES_ID);
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
                    formatter: (value: number) => formatAxisDate(value),
                },
            },
            yAxis: {
                type: 'value',
                ...(mode === 'value' && valueYFromZero ? {min: 0, scale: false} : {scale: true}),
                axisLine: {show: false},
                axisTick: {show: false},
                splitLine: {lineStyle: {color: gridColors.gridColor}},
                axisLabel: {
                    color: gridColors.textColor,
                    formatter: (value: number) => (mode === 'return' && returnDisplay === 'percentage' ? `${normalizeZero(value).toFixed(0)}%` : formatAxisNumber(value)),
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
            chartInstance.off('datazoom', applyCurrentZoomWindow);
            chartInstance.off('updateAxisPointer', handleUpdateAxisPointer);
            chartInstance.getZr()?.off('globalout', handleChartGlobalOut);
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
            chartInstance.on('datazoom', applyCurrentZoomWindow);
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
            chartInstance?.off('datazoom', applyCurrentZoomWindow);
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
        void returnDisplay;
        void valueYFromZero;
        void xAxisRange;
        void lotModels;
        void visibleLots;
        void hasEstimatedAtCostLots;
        void incomeMarkerEvents;
        void valuePointsByLotId;
        void aggregatedValuePoints;
        void returnPointsByLotId;
        void returnLotsWithData;
        void aggregateReturnPoints;
        void showAggregateReturn;
        void emptyMessage;
        void $currentLanguage;

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

        <div class="flex flex-wrap items-center gap-2">
            <div class="flex overflow-hidden rounded-lg border border-gray-200 text-xs font-medium dark:border-slate-600" data-testid="lot-comparison-mode-toggle">
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

            {#if mode === 'return'}
                <div class="flex overflow-hidden rounded-lg border border-gray-200 text-xs font-medium dark:border-slate-600" data-testid="lot-comparison-return-display-toggle">
                    <button
                        type="button"
                        class="px-3 py-1 transition-colors {returnDisplay === 'percentage' ? 'bg-libre-green text-white' : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-400 dark:hover:bg-slate-700'}"
                        onclick={() => (returnDisplay = 'percentage')}
                        aria-pressed={returnDisplay === 'percentage'}
                        data-testid="lot-comparison-return-display-pct"
                    >
                        {modeLabels.pct}
                    </button>
                    <button
                        type="button"
                        class="border-l border-gray-200 px-3 py-1 transition-colors dark:border-slate-600 {returnDisplay === 'absolute' ? 'bg-libre-green text-white' : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-400 dark:hover:bg-slate-700'}"
                        onclick={() => (returnDisplay = 'absolute')}
                        aria-pressed={returnDisplay === 'absolute'}
                        data-testid="lot-comparison-return-display-abs"
                    >
                        {modeLabels.abs}
                    </button>
                </div>
            {:else}
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
            {/if}
        </div>
    </div>

    {#if selectedLots.length === 0}
        <div class="flex h-80 items-center justify-center rounded-lg border border-dashed border-gray-200 px-6 text-center text-sm text-gray-500 dark:border-slate-600 dark:text-gray-400" data-testid="lot-comparison-empty">
            {modeLabels.selectLots}
        </div>
    {:else}
        <div class="relative h-80 w-full">
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
