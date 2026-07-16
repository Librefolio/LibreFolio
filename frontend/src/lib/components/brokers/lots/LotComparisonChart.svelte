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
    import {getBrokerColor, type BrokerLike} from '$lib/utils/broker/brokerColors';

    type LotSummarySchema = z.infer<typeof schemas.LotSummarySchema>;
    type LotValueHistoryPoint = z.infer<typeof schemas.LotValueHistoryPoint>;
    type LotReturnHistoryPoint = z.infer<typeof schemas.LotReturnHistoryPoint>;
    type LotPriceHistoryPoint = z.infer<typeof schemas.LotPriceHistoryPoint>;
    type BrokerWACHistoryPoint = z.infer<typeof schemas.BrokerWACHistoryPoint>;
    type CumulativeWACHistoryPoint = z.infer<typeof schemas.CumulativeWACHistoryPoint>;
    type ChartMode = 'value' | 'return' | 'price';

    interface Props {
        selectedLots: ReadonlyArray<LotSummarySchema>;
        valueHistory: ReadonlyArray<LotValueHistoryPoint>;
        returnHistory: ReadonlyArray<LotReturnHistoryPoint>;
        priceHistory: ReadonlyArray<LotPriceHistoryPoint>;
        brokerWacHistory?: ReadonlyArray<BrokerWACHistoryPoint>;
        cumulativeWacHistory?: ReadonlyArray<CumulativeWACHistoryPoint>;
        brokers: ReadonlyArray<BrokerLike>;
        currency: string;
        xAxisRange: {min: string; max: string} | null;
    }

    interface LotModel {
        lotId: number;
        direction: 'LONG' | 'SHORT';
        openingDate: string;
        label: string;
        openingUnitPrice: number;
    }

    interface LotValueSeriesPoint {
        date: string;
        proceeds: number;
        openValue: number;
        totalValue: number;
        originalCost: number;
        pnl: number;
    }

    interface LotReturnSeriesPoint {
        date: string;
        totalReturn: number | null;
        relativeReturn: number | null;
        referencePriceSource: string | null;
    }

    interface AggregatedValuePoint {
        date: string;
        openValue: number;
        proceeds: number;
        originalCost: number;
    }

    interface BrokerWacSeries {
        brokerId: number;
        points: ReturnType<typeof namedPoint>[];
    }

    interface PriceToggleItem {
        id: string;
        label: string;
        color: string;
        visible: boolean;
    }

    interface ValueToggleItem {
        lotId: number;
        label: string;
        color: string;
        visible: boolean;
    }

    const LOT_COMPARISON_SET_OPTION_OPTS: {notMerge: boolean; replaceMerge: string[]} = {
        notMerge: false,
        replaceMerge: ['series', 'xAxis', 'yAxis', 'legend', 'dataZoom'],
    };

    let {
        selectedLots = [],
        valueHistory = [],
        returnHistory = [],
        priceHistory = [],
        brokerWacHistory = [],
        cumulativeWacHistory = [],
        brokers = [],
        currency,
        xAxisRange = null,
    }: Props = $props();

    let mode = $state<ChartMode>('value');
    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | undefined = undefined;
    let resizeObserver: ResizeObserver | null = null;
    let darkModeObserver: MutationObserver | null = null;
    let tooltipCleanup: (() => void) | null = null;
    let dataZoomTouchPanHandle: DataZoomTouchPanHandle | null = null;
    let isDark = $state(false);
    let needsInitialLayoutStabilityPass = false;
    let zoomWindow = $state<{start: number; end: number} | null>(null);
    let lotVisibility = $state<Record<number, boolean>>({});
    let priceOverlayVisibility = $state<Record<string, boolean>>({});
    let valueSeriesVisibility = $state<Record<number, boolean>>({});

    function safeScalar<T>(value: T | Array<T | null> | null | undefined): T | null {
        if (Array.isArray(value)) return value[0] ?? null;
        return value ?? null;
    }

    function safeString(value: string | Array<string | null> | null | undefined): string | null {
        return safeScalar(value);
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

    function formatLongDate(value: string): string {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return value;
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

    function nullifyZeroWac(wac: number | null, poolQty?: number | null): number | null {
        if (wac == null) return null;
        return wac === 0 || poolQty === 0 ? null : wac;
    }

    function lotColor(lotId: number): string {
        const hue = Math.round((lotId * 137.508) % 360);
        return isDark ? `hsl(${hue} 78% 68%)` : `hsl(${hue} 68% 44%)`;
    }

    function brokerName(brokerId: number | null): string {
        if (brokerId == null) return '—';
        return brokers.find((broker) => broker.id === brokerId)?.name ?? `#${brokerId}`;
    }

    function brokerColor(brokerId: number): string {
        const colors = getBrokerColor(brokerId, brokers);
        return isDark ? colors.vivid : colors.vividLight;
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

    function toggleLotVisibility(lotId: number) {
        lotVisibility = {...lotVisibility, [lotId]: !(lotVisibility[lotId] ?? true)};
    }

    function togglePriceOverlay(id: string) {
        priceOverlayVisibility = {...priceOverlayVisibility, [id]: !(priceOverlayVisibility[id] ?? false)};
    }

    function toggleValueSeries(lotId: number) {
        valueSeriesVisibility = {...valueSeriesVisibility, [lotId]: !(valueSeriesVisibility[lotId] ?? false)};
    }

    function applyCurrentZoomWindow() {
        if (!chartInstance) return;
        const window = getChartZoomWindow(chartInstance);
        if (window) zoomWindow = window;
    }

    const modeLabels = $derived.by(() => ({
        value: tr('common.value', 'Value'),
        return: tr('brokers.lots.modeReturn', 'Return'),
        price: tr('dashboard.price', 'Price'),
        valueTitle: tr('brokers.lots.valueComparisonTitle', 'Value of selected lots'),
        returnTitle: tr('brokers.lots.returnComparisonTitle', 'Return from opening date'),
        priceTitle: tr('brokers.lots.priceComparisonTitle', 'Price and average cost'),
        proceeds: tr('brokers.lots.cumulativeProceeds', 'Cumulative proceeds'),
        residualValue: tr('brokers.lots.residualOpenValue', 'Residual open value'),
        aggregateOriginalCost: tr('brokers.lots.aggregateOriginalCost', 'Total original cost'),
        totalValue: tr('common.totalValue', 'Total Value'),
        totalReturn: tr('brokers.lots.totalReturn', 'Total return'),
        openReturn: tr('brokers.lots.openReturn', 'Open Return'),
        selectLots: tr('brokers.lots.selectLotsToCompare', 'Select one or more lots to compare'),
        noVisibleLots: tr('brokers.lots.noVisibleLots', 'No visible lots in chart'),
        marketPrice: tr('chart.marketPrice', 'Market Price'),
        openingPrice: tr('brokers.lots.openingPriceReference', 'Opening price'),
        cumulativeWac: tr('brokers.lots.cumulativeWac', 'Cumulative WAC'),
        noData: tr('common.noData', 'No data'),
    }));

    const lotModels = $derived.by(() => {
        const models = selectedLots.map((lot) => ({
            lotId: lot.lot_id,
            direction: lot.direction,
            openingDate: lot.opening_date,
            baseLabel: lotLabel(lot.opening_date, lot.direction),
            openingUnitPrice: parseRequiredNumber(lot.opening_unit_price),
        }));

        const labelCounts = new Map<string, number>();
        for (const model of models) labelCounts.set(model.baseLabel, (labelCounts.get(model.baseLabel) ?? 0) + 1);

        return models.map((model) => ({
            lotId: model.lotId,
            direction: model.direction,
            openingDate: model.openingDate,
            label: (labelCounts.get(model.baseLabel) ?? 0) > 1 ? `${model.baseLabel} · #${model.lotId}` : model.baseLabel,
            openingUnitPrice: model.openingUnitPrice,
        })) satisfies LotModel[];
    });

    const lotMap = $derived.by(() => new Map(lotModels.map((lot) => [lot.lotId, lot])));

    const visibleLots = $derived.by(() => lotModels.filter((lot) => lotVisibility[lot.lotId] ?? true));

    const valuePointsByLotId = $derived.by(() => {
        const grouped = new Map<number, LotValueSeriesPoint[]>();
        for (const point of valueHistory) {
            const existing = grouped.get(point.lot_id);
            const datum = {
                date: point.date,
                proceeds: parseRequiredNumber(point.proceeds),
                openValue: parseRequiredNumber(point.open_value),
                totalValue: parseRequiredNumber(point.total_value),
                originalCost: parseRequiredNumber(point.original_cost),
                pnl: parseRequiredNumber(point.pnl),
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
                };
                current.openValue += point.openValue;
                current.proceeds += point.proceeds;
                current.originalCost += point.originalCost;
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
                referencePriceSource: safeString(point.reference_price_source),
            } satisfies LotReturnSeriesPoint;
            if (existing) existing.push(datum);
            else grouped.set(point.lot_id, [datum]);
        }
        for (const points of grouped.values()) {
            points.sort((left, right) => left.date.localeCompare(right.date));
        }
        return grouped;
    });

    const returnPointByLotDate = $derived.by(() => {
        const byLotDate = new Map<string, LotReturnSeriesPoint>();
        for (const [lotId, points] of returnPointsByLotId.entries()) {
            for (const point of points) {
                byLotDate.set(pointKey(lotId, point.date), point);
            }
        }
        return byLotDate;
    });

    const marketPricePoints = $derived.by(() => {
        const byDate = new Map<string, number | null>();
        const sorted = [...priceHistory].sort((left, right) => left.date.localeCompare(right.date));
        for (const point of sorted) {
            const nextValue = parseNumber(point.market_price);
            if (!byDate.has(point.date)) {
                byDate.set(point.date, nextValue);
                continue;
            }
            if (byDate.get(point.date) == null && nextValue != null) {
                byDate.set(point.date, nextValue);
            }
        }
        return Array.from(byDate.entries())
            .map(([date, value]) => namedPoint(date, value))
            .sort((left, right) => String(left.value[0]).localeCompare(String(right.value[0])));
    });

    const cumulativeWacPoints = $derived.by(() =>
        [...cumulativeWacHistory]
            .sort((left, right) => left.date.localeCompare(right.date))
            .map((point) => namedPoint(point.date, nullifyZeroWac(parseNumber(point.wac), parseNumber(point.pool_qty))))
    );

    const brokerWacSeries = $derived.by(() => {
        const grouped = new Map<number, ReturnType<typeof namedPoint>[]>();
        for (const point of brokerWacHistory) {
            const existing = grouped.get(point.broker_id);
            const datum = namedPoint(point.date, nullifyZeroWac(parseNumber(point.wac), parseNumber(point.pool_qty)));
            if (existing) existing.push(datum);
            else grouped.set(point.broker_id, [datum]);
        }

        const brokerOrder = new Map(brokers.map((broker, index) => [broker.id, index]));
        return Array.from(grouped.entries())
            .map(([brokerId, points]) => ({
                brokerId,
                points: points.sort((left, right) => String(left.value[0]).localeCompare(String(right.value[0]))),
            }))
            .sort((left, right) => {
                const leftOrder = brokerOrder.get(left.brokerId) ?? Number.MAX_SAFE_INTEGER;
                const rightOrder = brokerOrder.get(right.brokerId) ?? Number.MAX_SAFE_INTEGER;
                return leftOrder - rightOrder || left.brokerId - right.brokerId;
            }) satisfies BrokerWacSeries[];
    });

    const activeBrokerIds = $derived.by(() => {
        const latestByBroker = new Map<number, {date: string; poolQty: number | null}>();
        for (const point of brokerWacHistory) {
            const current = latestByBroker.get(point.broker_id);
            if (current && current.date > point.date) continue;
            latestByBroker.set(point.broker_id, {date: point.date, poolQty: parseNumber(point.pool_qty)});
        }
        return Array.from(latestByBroker.entries())
            .filter(([, meta]) => (meta.poolQty ?? 0) > 0)
            .map(([brokerId]) => brokerId)
            .sort((left, right) => left - right);
    });

    const showCumulativeWac = $derived.by(() => activeBrokerIds.length >= 2 && cumulativeWacPoints.some((point) => point.value[1] != null));

    const valueToggleItems = $derived.by(() =>
        visibleLots
            .filter((lot) => (valuePointsByLotId.get(lot.lotId) ?? []).some((point) => point.totalValue !== 0 || point.openValue !== 0 || point.proceeds !== 0))
            .map((lot) => ({
                lotId: lot.lotId,
                label: `${modeLabels.totalValue} — ${lot.label}`,
                color: lotColor(lot.lotId),
                visible: valueSeriesVisibility[lot.lotId] ?? false,
            })) satisfies ValueToggleItem[]
    );

    const priceToggleItems = $derived.by(() => {
        const items: PriceToggleItem[] = [];
        if (showCumulativeWac) {
            items.push({
                id: 'cumulative-wac',
                label: modeLabels.cumulativeWac,
                color: isDark ? '#cbd5e1' : '#475569',
                visible: priceOverlayVisibility['cumulative-wac'] ?? true,
            });
        }

        const singleBrokerMode = activeBrokerIds.length === 1;
        for (const brokerId of activeBrokerIds) {
            const series = brokerWacSeries.find((item) => item.brokerId === brokerId);
            if (!series || !series.points.some((point) => point.value[1] != null)) continue;
            const key = `broker-wac-${brokerId}`;
            items.push({
                id: key,
                label: `WAC — ${brokerName(brokerId)}`,
                color: brokerColor(brokerId),
                visible: priceOverlayVisibility[key] ?? singleBrokerMode,
            });
        }
        return items;
    });

    const priceTimeMaxDate = $derived.by(() => {
        let maxDate: string | null = xAxisRange?.max ?? null;

        for (const lot of lotModels) {
            if (!maxDate || lot.openingDate > maxDate) maxDate = lot.openingDate;
        }
        for (const point of priceHistory) {
            if (!maxDate || point.date > maxDate) maxDate = point.date;
        }
        for (const point of brokerWacHistory) {
            if (!maxDate || point.date > maxDate) maxDate = point.date;
        }
        for (const point of cumulativeWacHistory) {
            if (!maxDate || point.date > maxDate) maxDate = point.date;
        }

        return maxDate;
    });

    const emptyMessage = $derived.by(() => {
        if (selectedLots.length === 0) return modeLabels.selectLots;
        if (visibleLots.length === 0) return modeLabels.noVisibleLots;

        if (mode === 'value') {
            return aggregatedValuePoints.length > 0 ? '' : modeLabels.noData;
        }

        if (mode === 'return') {
            const hasData = visibleLots.some((lot) => returnPointsByLotId.get(lot.lotId)?.some((point) => point.totalReturn != null));
            return hasData ? '' : modeLabels.noData;
        }

        const hasOpeningReference = visibleLots.some((lot) => Number.isFinite(lot.openingUnitPrice));
        const hasMarketPrice = marketPricePoints.some((point) => point.value[1] != null);
        const hasBrokerWac = activeBrokerIds.some((brokerId) => brokerWacSeries.find((series) => series.brokerId === brokerId)?.points.some((point) => point.value[1] != null));
        return hasOpeningReference || hasMarketPrice || showCumulativeWac || hasBrokerWac ? '' : modeLabels.noData;
    });

    const chartTitle = $derived.by(() => {
        if (mode === 'value') return modeLabels.valueTitle;
        if (mode === 'return') return modeLabels.returnTitle;
        return modeLabels.priceTitle;
    });

    $effect(() => {
        void lotModels;
        const nextVisibility: Record<number, boolean> = {};
        for (const lot of lotModels) nextVisibility[lot.lotId] = lotVisibility[lot.lotId] ?? true;
        const changed = Object.keys(nextVisibility).length !== Object.keys(lotVisibility).length || Object.entries(nextVisibility).some(([key, value]) => lotVisibility[Number(key)] !== value);
        if (changed) lotVisibility = nextVisibility;
    });

    $effect(() => {
        void lotModels;
        const nextVisibility: Record<number, boolean> = {};
        for (const lot of lotModels) nextVisibility[lot.lotId] = valueSeriesVisibility[lot.lotId] ?? false;
        const changed = Object.keys(nextVisibility).length !== Object.keys(valueSeriesVisibility).length || Object.entries(nextVisibility).some(([key, value]) => valueSeriesVisibility[Number(key)] !== value);
        if (changed) valueSeriesVisibility = nextVisibility;
    });

    $effect(() => {
        void activeBrokerIds;
        void showCumulativeWac;
        const singleBrokerMode = activeBrokerIds.length === 1;
        const allowedKeys = new Set<string>(activeBrokerIds.map((brokerId) => `broker-wac-${brokerId}`));
        if (showCumulativeWac) allowedKeys.add('cumulative-wac');

        const nextVisibility: Record<string, boolean> = {};
        if (showCumulativeWac) {
            nextVisibility['cumulative-wac'] = priceOverlayVisibility['cumulative-wac'] ?? true;
        }
        for (const brokerId of activeBrokerIds) {
            const key = `broker-wac-${brokerId}`;
            nextVisibility[key] = priceOverlayVisibility[key] ?? singleBrokerMode;
        }

        for (const [key, value] of Object.entries(priceOverlayVisibility)) {
            if (allowedKeys.has(key) && nextVisibility[key] == null) nextVisibility[key] = value;
        }

        if (JSON.stringify(nextVisibility) !== JSON.stringify(priceOverlayVisibility)) {
            priceOverlayVisibility = nextVisibility;
        }
    });

    function buildValueTooltip(params: any[]): string {
        if (params.length === 0) return '';
        const theme = buildTooltipTheme(isDark);
        const rawDate: number | string = params[0]?.axisValue ?? params[0]?.value?.[0] ?? '';
        const rows = params
            .map((param) => {
                const value = seriesValue(param);
                if (value == null) return null;
                return buildTooltipRow(escapeHtml(String(param.seriesName ?? '')), escapeHtml(formatCurrencyAmountPlain(value, currency)), typeof param.color === 'string' ? param.color : undefined);
            })
            .filter((row): row is string => row != null);

        if (rows.length === 0) return '';
        return `<div style="font-size:11px;color:${theme.textColor}">${buildTooltipHeader(escapeHtml(formatAxisDate(rawDate)), theme.textColor)}${buildTooltipDivider(theme.border)}${rows.join('')}</div>`;
    }

    function buildReturnTooltip(params: any[]): string {
        if (params.length === 0) return '';
        const theme = buildTooltipTheme(isDark);
        const rawDate: number | string = params[0]?.axisValue ?? params[0]?.value?.[0] ?? '';
        const dateKeyPart = String(rawDate);
        const blocks = params
            .map((param) => {
                const value = seriesValue(param);
                if (value == null) return null;
                const lot = visibleLots.find((item) => item.label === String(param.seriesName ?? ''));
                if (!lot) return null;
                const returnPoint = returnPointByLotDate.get(pointKey(lot.lotId, dateKeyPart));
                if (!returnPoint || returnPoint.totalReturn == null) return null;

                const color = typeof param.color === 'string' ? param.color : lotColor(lot.lotId);
                const valuePoint = valuePointByLotDate.get(pointKey(lot.lotId, dateKeyPart));
                const rows: string[] = [buildTooltipRow(escapeHtml(modeLabels.totalReturn), escapeHtml(formatPercent(value)), color)];

                if (returnPoint.relativeReturn != null) {
                    rows.push(buildTooltipRow(escapeHtml(modeLabels.openReturn), escapeHtml(formatPercent(returnPoint.relativeReturn * 100))));
                }
                if (valuePoint) {
                    rows.push(buildTooltipRow(escapeHtml(modeLabels.residualValue), escapeHtml(formatCurrencyAmountPlain(valuePoint.openValue, currency))));
                    rows.push(buildTooltipRow(escapeHtml(modeLabels.proceeds), escapeHtml(formatCurrencyAmountPlain(valuePoint.proceeds, currency))));
                    rows.push(
                        buildTooltipRow(
                            escapeHtml(tr('brokers.lots.fifoPnl', 'FIFO P&L')),
                            `<span style="color:${valuePoint.pnl >= 0 ? (isDark ? '#4ade80' : '#16a34a') : isDark ? '#f87171' : '#dc2626'}">${escapeHtml(formatCurrencyAmountPlain(valuePoint.pnl, currency, {showSign: true}))}</span>`,
                        ),
                    );
                }

                return `${buildTooltipHeader(escapeHtml(`${lot.label} · ${formatLongDate(dateKeyPart)}`), theme.textColor)}${rows.join('')}`;
            })
            .filter((block): block is string => block != null);

        if (blocks.length === 0) return '';
        return `<div style="font-size:11px;color:${theme.textColor}">${buildTooltipHeader(escapeHtml(formatAxisDate(rawDate)), theme.textColor)}${buildTooltipDivider(theme.border)}${blocks.join(buildTooltipDivider(theme.border))}</div>`;
    }

    function buildPriceTooltip(params: any[]): string {
        if (params.length === 0) return '';
        const theme = buildTooltipTheme(isDark);
        const rawDate: number | string = params[0]?.axisValue ?? params[0]?.value?.[0] ?? '';
        const rows = params
            .map((param) => {
                const value = seriesValue(param);
                if (value == null) return null;
                return buildTooltipRow(escapeHtml(String(param.seriesName ?? '')), escapeHtml(formatCurrencyAmountPlain(value, currency)), typeof param.color === 'string' ? param.color : undefined);
            })
            .filter((row): row is string => row != null);

        if (rows.length === 0) return '';
        return `<div style="font-size:11px;color:${theme.textColor}">${buildTooltipHeader(escapeHtml(formatAxisDate(rawDate)), theme.textColor)}${buildTooltipDivider(theme.border)}${rows.join('')}</div>`;
    }

    function buildValueSeries(): echarts.SeriesOption[] {
        const residualColor = isDark ? '#60a5fa' : '#2563eb';
        const proceedsColor = isDark ? '#34d399' : '#059669';
        const originalCostColor = isDark ? '#cbd5e1' : '#475569';

        const series: echarts.SeriesOption[] = [
            {
                id: 'value-residual',
                name: modeLabels.residualValue,
                type: 'line',
                stack: 'value-aggregate',
                data: aggregatedValuePoints.map((point) => namedPoint(point.date, point.openValue)),
                showSymbol: false,
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 1.8, color: residualColor},
                areaStyle: {color: withAlpha(residualColor, isDark ? 0.4 : 0.22)},
                itemStyle: {color: residualColor},
            },
            {
                id: 'value-proceeds',
                name: modeLabels.proceeds,
                type: 'line',
                stack: 'value-aggregate',
                data: aggregatedValuePoints.map((point) => namedPoint(point.date, point.proceeds)),
                showSymbol: false,
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 1.8, color: proceedsColor},
                areaStyle: {color: withAlpha(proceedsColor, isDark ? 0.42 : 0.26)},
                itemStyle: {color: proceedsColor},
            },
            {
                id: 'value-original-cost',
                name: modeLabels.aggregateOriginalCost,
                type: 'line',
                data: aggregatedValuePoints.map((point) => namedPoint(point.date, point.originalCost)),
                showSymbol: false,
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 2.2, color: originalCostColor},
                itemStyle: {color: originalCostColor},
                z: 3,
            },
        ];

        for (const lot of visibleLots) {
            if (!(valueSeriesVisibility[lot.lotId] ?? false)) continue;
            const points = valuePointsByLotId.get(lot.lotId) ?? [];
            if (!points.some((point) => point.totalValue !== 0 || point.openValue !== 0 || point.proceeds !== 0)) continue;
            const color = lotColor(lot.lotId);
            series.push({
                id: `value-total-${lot.lotId}`,
                name: `${modeLabels.totalValue} — ${lot.label}`,
                type: 'line',
                data: points.map((point) => namedPoint(point.date, point.totalValue)),
                showSymbol: false,
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 2.2, color},
                itemStyle: {color},
                z: 4,
            });
        }

        return series;
    }

    function buildReturnSeries(): echarts.SeriesOption[] {
        return visibleLots
            .filter((lot) => returnPointsByLotId.get(lot.lotId)?.some((point) => point.totalReturn != null))
            .map((lot) => {
                const color = lotColor(lot.lotId);
                return {
                    id: `return-${lot.lotId}`,
                    name: lot.label,
                    type: 'line',
                    data: (returnPointsByLotId.get(lot.lotId) ?? []).map((point) => namedPoint(point.date, point.totalReturn == null ? null : point.totalReturn * 100)),
                    showSymbol: false,
                    connectNulls: false,
                    smooth: false,
                    lineStyle: {width: 2.5, color},
                    itemStyle: {color},
                } satisfies echarts.SeriesOption;
            });
    }

    function buildPriceSeries(): echarts.SeriesOption[] {
        const series: echarts.SeriesOption[] = [];

        if (marketPricePoints.some((point) => point.value[1] != null)) {
            series.push({
                id: 'price-market',
                name: modeLabels.marketPrice,
                type: 'line',
                data: marketPricePoints,
                showSymbol: false,
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 2.5, color: isDark ? '#4ade80' : '#16a34a'},
                itemStyle: {color: isDark ? '#4ade80' : '#16a34a'},
            });
        }

        const maxDate = priceTimeMaxDate;
        for (const lot of visibleLots) {
            if (!maxDate) continue;
            const color = lotColor(lot.lotId);
            const data = maxDate > lot.openingDate ? [namedPoint(lot.openingDate, lot.openingUnitPrice), namedPoint(maxDate, lot.openingUnitPrice)] : [namedPoint(lot.openingDate, lot.openingUnitPrice)];
            series.push({
                id: `price-opening-${lot.lotId}`,
                name: `${modeLabels.openingPrice} — ${lot.label}`,
                type: 'line',
                data,
                showSymbol: false,
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 2, color, type: 'dashed'},
                itemStyle: {color},
            });
        }

        if ((priceOverlayVisibility['cumulative-wac'] ?? true) && showCumulativeWac) {
            series.push({
                id: 'price-cumulative-wac',
                name: modeLabels.cumulativeWac,
                type: 'line',
                data: cumulativeWacPoints,
                showSymbol: false,
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 2.2, color: isDark ? '#cbd5e1' : '#475569'},
                itemStyle: {color: isDark ? '#cbd5e1' : '#475569'},
            });
        }

        for (const brokerId of activeBrokerIds) {
            const brokerSeries = brokerWacSeries.find((item) => item.brokerId === brokerId);
            const key = `broker-wac-${brokerId}`;
            if (!brokerSeries || !(priceOverlayVisibility[key] ?? activeBrokerIds.length === 1) || !brokerSeries.points.some((point) => point.value[1] != null)) continue;
            const color = brokerColor(brokerId);
            series.push({
                id: key,
                name: `WAC — ${brokerName(brokerId)}`,
                type: 'line',
                data: brokerSeries.points,
                showSymbol: false,
                connectNulls: false,
                smooth: false,
                lineStyle: {width: 1.8, color, type: 'dotted'},
                itemStyle: {color},
            });
        }

        return series;
    }

    function buildOption(): echarts.EChartsOption | null {
        if (emptyMessage) return null;

        const theme = buildTooltipTheme(isDark);
        const gridColors = buildGridColors(isDark);
        return {
            ...CHART_ANIMATION_CONFIG,
            grid: {
                top: 18,
                right: 18,
                bottom: 34,
                left: 24,
                containLabel: true,
            },
            legend: {show: false},
            tooltip: {
                trigger: 'axis',
                position: tooltipPositionSide,
                backgroundColor: theme.bg,
                borderColor: theme.border,
                textStyle: {color: theme.textColor},
                axisPointer: {
                    type: 'line',
                    lineStyle: {color: gridColors.gridColor, width: 1},
                },
                formatter: (params: any) => {
                    const items = Array.isArray(params) ? params : [params];
                    if (mode === 'value') return buildValueTooltip(items);
                    if (mode === 'return') return buildReturnTooltip(items);
                    return buildPriceTooltip(items);
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
                scale: true,
                axisLine: {show: false},
                axisTick: {show: false},
                splitLine: {lineStyle: {color: gridColors.gridColor}},
                axisLabel: {
                    color: gridColors.textColor,
                    formatter: (value: number) => (mode === 'return' ? `${normalizeZero(value).toFixed(0)}%` : formatAxisNumber(value)),
                },
            },
            series: mode === 'value' ? buildValueSeries() : mode === 'return' ? buildReturnSeries() : buildPriceSeries(),
            dataZoom: buildDataZoom([0]).map((zoom) => (zoomWindow ? {...zoom, start: zoomWindow.start, end: zoomWindow.end} : zoom)),
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
        }

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
            dataZoomTouchPanHandle?.dispose();
            dataZoomTouchPanHandle = null;
            chartInstance?.off('datazoom', applyCurrentZoomWindow);
            chartInstance?.dispose();
        };
    });

    $effect(() => {
        void selectedLots;
        void valueHistory;
        void returnHistory;
        void priceHistory;
        void brokerWacHistory;
        void cumulativeWacHistory;
        void brokers;
        void currency;
        void mode;
        void xAxisRange;
        void lotModels;
        void visibleLots;
        void valuePointsByLotId;
        void aggregatedValuePoints;
        void returnPointsByLotId;
        void marketPricePoints;
        void cumulativeWacPoints;
        void brokerWacSeries;
        void activeBrokerIds;
        void showCumulativeWac;
        void valueSeriesVisibility;
        void priceOverlayVisibility;
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
            <button
                type="button"
                class="border-l border-gray-200 px-3 py-1 transition-colors dark:border-slate-600 {mode === 'price' ? 'bg-libre-green text-white' : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-400 dark:hover:bg-slate-700'}"
                onclick={() => (mode = 'price')}
                aria-pressed={mode === 'price'}
                data-testid="lot-comparison-mode-price"
            >
                {modeLabels.price}
            </button>
        </div>
    </div>

    {#if selectedLots.length === 0}
        <div class="flex h-80 items-center justify-center rounded-lg border border-dashed border-gray-200 px-6 text-center text-sm text-gray-500 dark:border-slate-600 dark:text-gray-400" data-testid="lot-comparison-empty">
            {modeLabels.selectLots}
        </div>
    {:else}
        <div class="flex flex-wrap gap-2" data-testid="lot-comparison-lot-legend">
            {#each lotModels as lot (lot.lotId)}
                <label
                    class="inline-flex cursor-pointer items-center gap-2 rounded-full border px-3 py-1 text-xs transition-colors {lotVisibility[lot.lotId] ?? true ? 'border-gray-200 text-gray-700 dark:border-slate-600 dark:text-gray-200' : 'border-gray-200/70 text-gray-400 dark:border-slate-700 dark:text-gray-500'}"
                    data-testid={`lot-comparison-toggle-${lot.lotId}`}
                >
                    <input type="checkbox" checked={lotVisibility[lot.lotId] ?? true} onchange={() => toggleLotVisibility(lot.lotId)} style={`accent-color:${lotColor(lot.lotId)};`} />
                    <span class="h-2.5 w-2.5 rounded-full" style={`background:${lotColor(lot.lotId)};`}></span>
                    <span>{lot.label}</span>
                </label>
            {/each}
        </div>

        {#if mode === 'value' && valueToggleItems.length > 0}
            <div class="flex flex-wrap gap-2" data-testid="lot-comparison-value-legend">
                {#each valueToggleItems as item (item.lotId)}
                    <label
                        class="inline-flex cursor-pointer items-center gap-2 rounded-full border px-3 py-1 text-xs transition-colors {item.visible ? 'border-gray-200 text-gray-700 dark:border-slate-600 dark:text-gray-200' : 'border-gray-200/70 text-gray-400 dark:border-slate-700 dark:text-gray-500'}"
                        data-testid={`lot-comparison-value-toggle-${item.lotId}`}
                    >
                        <input type="checkbox" checked={item.visible} onchange={() => toggleValueSeries(item.lotId)} style={`accent-color:${item.color};`} />
                        <span class="h-2.5 w-2.5 rounded-full" style={`background:${item.color};`}></span>
                        <span>{item.label}</span>
                    </label>
                {/each}
            </div>
        {/if}

        {#if mode === 'price' && priceToggleItems.length > 0}
            <div class="flex flex-wrap gap-2" data-testid="lot-comparison-price-legend">
                {#each priceToggleItems as item (item.id)}
                    <label
                        class="inline-flex cursor-pointer items-center gap-2 rounded-full border px-3 py-1 text-xs transition-colors {item.visible ? 'border-gray-200 text-gray-700 dark:border-slate-600 dark:text-gray-200' : 'border-gray-200/70 text-gray-400 dark:border-slate-700 dark:text-gray-500'}"
                        data-testid={`lot-comparison-price-toggle-${item.id}`}
                    >
                        <input type="checkbox" checked={item.visible} onchange={() => togglePriceOverlay(item.id)} style={`accent-color:${item.color};`} />
                        <span class="h-2.5 w-2.5 rounded-full" style={`background:${item.color};`}></span>
                        <span>{item.label}</span>
                    </label>
                {/each}
            </div>
        {/if}

        <div class="relative h-80 w-full">
            {#if emptyMessage}
                <div class="absolute inset-0 z-10 flex items-center justify-center text-center text-sm text-gray-400 dark:text-gray-500">
                    {emptyMessage}
                </div>
            {/if}

            <div bind:this={chartContainer} class="h-full w-full" class:invisible={!!emptyMessage} data-testid="lot-comparison-echart"></div>
        </div>
    {/if}
</div>
