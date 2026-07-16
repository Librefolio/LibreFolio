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
        currency: string;
        xAxisRange: {min: string; max: string} | null;
    }

    interface LotModel {
        lotId: number;
        direction: 'LONG' | 'SHORT';
        openingDate: string;
        label: string;
        openingUnitPrice: number;
        originalCost: number;
        summaryOpenValue: number | null;
        summaryProceeds: number | null;
        summaryTotalValue: number | null;
        summaryPnl: number | null;
    }

    interface LotValueSnapshot {
        proceeds: number;
        openValue: number;
        totalValue: number;
        originalCost: number;
        pnl: number;
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

    const LOT_COMPARISON_SET_OPTION_OPTS: {notMerge: boolean; replaceMerge: string[]} = {
        notMerge: false,
        replaceMerge: ['series', 'xAxis', 'yAxis', 'legend', 'dataZoom'],
    };

    let {selectedLots = [], valueHistory = [], returnHistory = [], priceHistory = [], brokerWacHistory = [], cumulativeWacHistory = [], currency, xAxisRange = null}: Props = $props();

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

    function nullifyZeroWac(value: number | null): number | null {
        return value === 0 ? null : value;
    }

    function lotColor(lotId: number): string {
        const hue = Math.round((lotId * 137.508) % 360);
        return isDark ? `hsl(${hue} 78% 68%)` : `hsl(${hue} 68% 44%)`;
    }

    function brokerColor(brokerId: number): string {
        const hue = Math.round((brokerId * 67) % 360);
        return isDark ? `hsl(${hue} 72% 68%)` : `hsl(${hue} 62% 42%)`;
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

    function toggleLotVisibility(lotId: number) {
        lotVisibility = {...lotVisibility, [lotId]: !(lotVisibility[lotId] ?? true)};
    }

    function togglePriceOverlay(id: string) {
        priceOverlayVisibility = {...priceOverlayVisibility, [id]: !(priceOverlayVisibility[id] ?? false)};
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
        title: tr('brokers.lots.comparisonTitle', 'Lot comparison'),
        valueTitle: tr('brokers.lots.valueComparisonTitle', 'Value of selected lots'),
        returnTitle: tr('brokers.lots.returnComparisonTitle', 'Return from opening date'),
        priceTitle: tr('brokers.lots.priceComparisonTitle', 'Price and average cost'),
        proceeds: tr('brokers.lots.cumulativeProceeds', 'Cumulative proceeds'),
        residualValue: tr('brokers.lots.residualOpenValue', 'Residual open value'),
        originalCost: tr('brokers.lots.originalCostReference', 'Original cost'),
        selectLots: tr('brokers.lots.selectLotsToCompare', 'Select one or more lots to compare'),
        noVisibleLots: tr('brokers.lots.noVisibleLots', 'No visible lots in chart'),
        marketPrice: tr('chart.marketPrice', 'Market Price'),
        openingPrice: tr('brokers.lots.openingPriceReference', 'Opening price'),
        cumulativeWac: tr('brokers.lots.cumulativeWac', 'Cumulative WAC'),
        brokerWac: tr('brokers.lots.brokerWac', 'Broker WAC'),
        noData: tr('common.noData', 'No data'),
    }));

    const lotModels = $derived.by(() => {
        const models = selectedLots.map((lot) => ({
            lotId: lot.lot_id,
            direction: lot.direction,
            openingDate: lot.opening_date,
            baseLabel: lotLabel(lot.opening_date, lot.direction),
            openingUnitPrice: parseRequiredNumber(lot.opening_unit_price),
            originalCost: parseRequiredNumber(lot.original_cost),
            summaryOpenValue: parseNumber(lot.open_value),
            summaryProceeds: parseRequiredNumber(lot.cumulative_proceeds),
            summaryTotalValue: parseNumber(lot.total_value),
            summaryPnl: parseNumber(lot.pnl),
        }));

        const labelCounts = new Map<string, number>();
        for (const model of models) labelCounts.set(model.baseLabel, (labelCounts.get(model.baseLabel) ?? 0) + 1);

        return models.map((model) => ({
            lotId: model.lotId,
            direction: model.direction,
            openingDate: model.openingDate,
            label: (labelCounts.get(model.baseLabel) ?? 0) > 1 ? `${model.baseLabel} · #${model.lotId}` : model.baseLabel,
            openingUnitPrice: model.openingUnitPrice,
            originalCost: model.originalCost,
            summaryOpenValue: model.summaryOpenValue,
            summaryProceeds: model.summaryProceeds,
            summaryTotalValue: model.summaryTotalValue,
            summaryPnl: model.summaryPnl,
        })) satisfies LotModel[];
    });

    const lotMap = $derived.by(() => new Map(lotModels.map((lot) => [lot.lotId, lot])));

    const visibleLots = $derived.by(() => lotModels.filter((lot) => lotVisibility[lot.lotId] ?? true));

    const latestValueByLotId = $derived.by(() => {
        const latest = new Map<number, {date: string; snapshot: LotValueSnapshot}>();
        for (const point of valueHistory) {
            const current = latest.get(point.lot_id);
            if (current && current.date > point.date) continue;
            latest.set(point.lot_id, {
                date: point.date,
                snapshot: {
                    proceeds: parseRequiredNumber(point.proceeds),
                    openValue: parseRequiredNumber(point.open_value),
                    totalValue: parseRequiredNumber(point.total_value),
                    originalCost: parseRequiredNumber(point.original_cost),
                    pnl: parseRequiredNumber(point.pnl),
                },
            });
        }

        const byLotId = new Map<number, LotValueSnapshot>();
        for (const lot of lotModels) {
            const fromHistory = latest.get(lot.lotId)?.snapshot;
            byLotId.set(lot.lotId, {
                proceeds: fromHistory?.proceeds ?? lot.summaryProceeds ?? 0,
                openValue: fromHistory?.openValue ?? lot.summaryOpenValue ?? 0,
                totalValue: fromHistory?.totalValue ?? lot.summaryTotalValue ?? (fromHistory?.proceeds ?? lot.summaryProceeds ?? 0) + (fromHistory?.openValue ?? lot.summaryOpenValue ?? 0),
                originalCost: fromHistory?.originalCost ?? lot.originalCost,
                pnl: fromHistory?.pnl ?? lot.summaryPnl ?? 0,
            });
        }

        return byLotId;
    });

    const returnSeriesByLotId = $derived.by(() => {
        const grouped = new Map<number, ReturnType<typeof namedPoint>[]>();
        for (const point of returnHistory) {
            const existing = grouped.get(point.lot_id);
            const value = parseNumber(point.relative_return);
            const datum = namedPoint(point.date, value == null ? null : value * 100);
            if (existing) existing.push(datum);
            else grouped.set(point.lot_id, [datum]);
        }
        for (const points of grouped.values()) {
            points.sort((left, right) => String(left.value[0]).localeCompare(String(right.value[0])));
        }
        return grouped;
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
            .map((point) => namedPoint(point.date, nullifyZeroWac(parseNumber(point.wac))))
    );

    const brokerWacSeries = $derived.by(() => {
        const grouped = new Map<number, ReturnType<typeof namedPoint>[]>();
        for (const point of brokerWacHistory) {
            const existing = grouped.get(point.broker_id);
            const datum = namedPoint(point.date, nullifyZeroWac(parseNumber(point.wac)));
            if (existing) existing.push(datum);
            else grouped.set(point.broker_id, [datum]);
        }

        return Array.from(grouped.entries())
            .map(([brokerId, points]) => ({
                brokerId,
                points: points.sort((left, right) => String(left.value[0]).localeCompare(String(right.value[0]))),
            }))
            .sort((left, right) => left.brokerId - right.brokerId) satisfies BrokerWacSeries[];
    });

    const priceToggleItems = $derived.by(() => {
        const items: PriceToggleItem[] = [];
        const hasCumulativeData = cumulativeWacPoints.some((point) => point.value[1] != null);
        if (hasCumulativeData) {
            items.push({
                id: 'cumulative-wac',
                label: modeLabels.cumulativeWac,
                color: isDark ? '#cbd5e1' : '#475569',
                visible: priceOverlayVisibility['cumulative-wac'] ?? true,
            });
        }

        for (const series of brokerWacSeries) {
            if (!series.points.some((point) => point.value[1] != null)) continue;
            items.push({
                id: `broker-wac-${series.brokerId}`,
                label: `${modeLabels.brokerWac} #${series.brokerId}`,
                color: brokerColor(series.brokerId),
                visible: priceOverlayVisibility[`broker-wac-${series.brokerId}`] ?? false,
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

        if (mode === 'value') {
            if (visibleLots.length === 0) return modeLabels.noVisibleLots;
            const hasData = visibleLots.some((lot) => {
                const snapshot = latestValueByLotId.get(lot.lotId);
                return snapshot != null && [snapshot.proceeds, snapshot.openValue, snapshot.originalCost, snapshot.totalValue].some((value) => Math.abs(value) > 0);
            });
            return hasData ? '' : modeLabels.noData;
        }

        if (mode === 'return') {
            if (visibleLots.length === 0) return modeLabels.noVisibleLots;
            const hasData = visibleLots.some((lot) => returnSeriesByLotId.get(lot.lotId)?.some((point) => point.value[1] != null));
            return hasData ? '' : modeLabels.noData;
        }

        const hasOpeningReference = visibleLots.some((lot) => Number.isFinite(lot.openingUnitPrice));
        const hasMarketPrice = marketPricePoints.some((point) => point.value[1] != null);
        const hasVisibleOverlay = priceToggleItems.some((item) => item.visible);
        return hasOpeningReference || hasMarketPrice || hasVisibleOverlay ? '' : modeLabels.noData;
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
        void brokerWacSeries;
        void cumulativeWacPoints;
        const nextVisibility = {...priceOverlayVisibility};
        if (cumulativeWacPoints.some((point) => point.value[1] != null) && nextVisibility['cumulative-wac'] == null) {
            nextVisibility['cumulative-wac'] = true;
        }
        for (const series of brokerWacSeries) {
            const key = `broker-wac-${series.brokerId}`;
            if (series.points.some((point) => point.value[1] != null) && nextVisibility[key] == null) {
                nextVisibility[key] = false;
            }
        }
        if (JSON.stringify(nextVisibility) !== JSON.stringify(priceOverlayVisibility)) {
            priceOverlayVisibility = nextVisibility;
        }
    });

    function buildValueTooltip(params: any[]): string {
        if (params.length === 0) return '';
        const lot = visibleLots[params[0]?.dataIndex ?? -1];
        if (!lot) return '';

        const snapshot = latestValueByLotId.get(lot.lotId);
        if (!snapshot) return '';

        const theme = buildTooltipTheme(isDark);
        const accent = lotColor(lot.lotId);
        const rows = [
            buildTooltipRow(escapeHtml(modeLabels.proceeds), escapeHtml(formatCurrencyAmountPlain(snapshot.proceeds, currency)), withAlpha(accent, 0.85)),
            buildTooltipRow(escapeHtml(modeLabels.residualValue), escapeHtml(formatCurrencyAmountPlain(snapshot.openValue, currency)), withAlpha(accent, 0.4)),
            buildTooltipRow(escapeHtml(modeLabels.originalCost), escapeHtml(formatCurrencyAmountPlain(snapshot.originalCost, currency)), accent),
            buildTooltipRow(escapeHtml(tr('dashboard.totalPnl', 'Total P&L')), `<span style="color:${snapshot.pnl >= 0 ? (isDark ? '#4ade80' : '#16a34a') : isDark ? '#f87171' : '#dc2626'}">${escapeHtml(formatCurrencyAmountPlain(snapshot.pnl, currency, {showSign: true}))}</span>`),
        ];

        return `<div style="font-size:11px;color:${theme.textColor}">${buildTooltipHeader(escapeHtml(`${lot.label} · ${formatLongDate(lot.openingDate)}`), theme.textColor)}${buildTooltipDivider(theme.border)}${rows.join('')}</div>`;
    }

    function buildTimeTooltip(params: any[]): string {
        if (params.length === 0) return '';
        const theme = buildTooltipTheme(isDark);
        const rawDate: number | string = params[0]?.axisValue ?? params[0]?.value?.[0] ?? '';
        const rows = params
            .map((param) => {
                const rawValue = Array.isArray(param.value) ? param.value[1] : param.value;
                if (rawValue == null || rawValue === '') return null;
                const value = Number(rawValue);
                if (!Number.isFinite(value)) return null;
                const formatted = mode === 'return' ? formatPercent(value) : formatCurrencyAmountPlain(value, currency);
                return buildTooltipRow(escapeHtml(String(param.seriesName ?? '')), escapeHtml(formatted), typeof param.color === 'string' ? param.color : undefined);
            })
            .filter((row): row is string => row != null);

        if (rows.length === 0) return '';
        return `<div style="font-size:11px;color:${theme.textColor}">${buildTooltipHeader(escapeHtml(formatAxisDate(rawDate)), theme.textColor)}${buildTooltipDivider(theme.border)}${rows.join('')}</div>`;
    }

    function buildValueSeries(): echarts.SeriesOption[] {
        return [
            {
                name: modeLabels.proceeds,
                type: 'bar',
                stack: 'lot-value',
                barMaxWidth: 42,
                data: visibleLots.map((lot) => ({
                    value: latestValueByLotId.get(lot.lotId)?.proceeds ?? 0,
                    itemStyle: {
                        color: withAlpha(lotColor(lot.lotId), 0.88),
                        borderRadius: [6, 6, 0, 0],
                    },
                })),
            },
            {
                name: modeLabels.residualValue,
                type: 'bar',
                stack: 'lot-value',
                barMaxWidth: 42,
                data: visibleLots.map((lot) => ({
                    value: latestValueByLotId.get(lot.lotId)?.openValue ?? 0,
                    itemStyle: {
                        color: withAlpha(lotColor(lot.lotId), 0.38),
                        borderColor: withAlpha(lotColor(lot.lotId), 0.85),
                        borderWidth: 1,
                        borderRadius: [6, 6, 0, 0],
                    },
                })),
            },
            {
                name: modeLabels.originalCost,
                type: 'scatter',
                symbol: 'diamond',
                symbolSize: 13,
                data: visibleLots.map((lot) => ({
                    value: [lot.label, latestValueByLotId.get(lot.lotId)?.originalCost ?? lot.originalCost],
                    itemStyle: {
                        color: lotColor(lot.lotId),
                        borderColor: isDark ? '#0f172a' : '#f8fafc',
                        borderWidth: 1.5,
                    },
                })),
                z: 4,
            },
        ];
    }

    function buildReturnSeries(): echarts.SeriesOption[] {
        return visibleLots
            .filter((lot) => returnSeriesByLotId.get(lot.lotId)?.length)
            .map((lot) => {
                const color = lotColor(lot.lotId);
                return {
                    name: lot.label,
                    type: 'line',
                    data: returnSeriesByLotId.get(lot.lotId) ?? [],
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
            const data =
                maxDate > lot.openingDate
                    ? [namedPoint(lot.openingDate, lot.openingUnitPrice), namedPoint(maxDate, lot.openingUnitPrice)]
                    : [namedPoint(lot.openingDate, lot.openingUnitPrice)];
            series.push({
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

        if ((priceOverlayVisibility['cumulative-wac'] ?? true) && cumulativeWacPoints.some((point) => point.value[1] != null)) {
            series.push({
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

        for (const brokerSeries of brokerWacSeries) {
            const key = `broker-wac-${brokerSeries.brokerId}`;
            if (!(priceOverlayVisibility[key] ?? false) || !brokerSeries.points.some((point) => point.value[1] != null)) continue;
            const color = brokerColor(brokerSeries.brokerId);
            series.push({
                name: `${modeLabels.brokerWac} #${brokerSeries.brokerId}`,
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
        const baseOption: echarts.EChartsOption = {
            ...CHART_ANIMATION_CONFIG,
            grid: {
                top: 18,
                right: 18,
                bottom: mode === 'value' ? 68 : 34,
                left: 24,
                containLabel: true,
            },
            legend: {show: false},
        };

        if (mode === 'value') {
            return {
                ...baseOption,
                tooltip: {
                    trigger: 'axis',
                    axisPointer: {type: 'shadow'},
                    position: tooltipPositionSide,
                    backgroundColor: theme.bg,
                    borderColor: theme.border,
                    textStyle: {color: theme.textColor},
                    formatter: (params: any) => buildValueTooltip(Array.isArray(params) ? params : [params]),
                },
                xAxis: {
                    type: 'category',
                    data: visibleLots.map((lot) => lot.label),
                    axisLine: {lineStyle: {color: gridColors.gridColor}},
                    axisTick: {show: false},
                    axisLabel: {
                        color: gridColors.textColor,
                        interval: 0,
                    },
                },
                yAxis: {
                    type: 'value',
                    axisLine: {show: false},
                    axisTick: {show: false},
                    splitLine: {lineStyle: {color: gridColors.gridColor}},
                    axisLabel: {
                        color: gridColors.textColor,
                        formatter: (value: number) => formatAxisNumber(value),
                    },
                },
                series: buildValueSeries(),
                dataZoom: [],
            };
        }

        return {
            ...baseOption,
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
                formatter: (params: any) => buildTimeTooltip(Array.isArray(params) ? params : [params]),
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
            series: mode === 'return' ? buildReturnSeries() : buildPriceSeries(),
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
        void currency;
        void mode;
        void xAxisRange;
        void lotModels;
        void visibleLots;
        void latestValueByLotId;
        void returnSeriesByLotId;
        void marketPricePoints;
        void cumulativeWacPoints;
        void brokerWacSeries;
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
