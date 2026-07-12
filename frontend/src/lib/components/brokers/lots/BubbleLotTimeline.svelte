<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {z} from 'zod';
    import {schemas} from '$lib/api';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import {CHART_ANIMATION_CONFIG, CHART_SET_OPTION_OPTS} from '$lib/components/charts/echartsAnimationConfig';
    import {buildGridColors, buildTooltipDivider, buildTooltipHeader, buildTooltipRow, buildTooltipTheme, setupTooltipAutoHide, tooltipPositionSide} from '$lib/components/charts/echartsTooltipHelpers';
    import {getBrokerColor, type BrokerLike} from '$lib/utils/broker/brokerColors';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';

    type OpenLotSchema = z.infer<typeof schemas.OpenLotSchema>;
    type ClosedLotSchema = z.infer<typeof schemas.ClosedLotSchema>;

    interface Props {
        openLots: ReadonlyArray<OpenLotSchema>;
        closedLots: ReadonlyArray<ClosedLotSchema>;
        brokers?: ReadonlyArray<BrokerLike>;
        currency: string;
        onLotClick?: (buyTransactionId: number) => void;
        xAxisRange?: {min: string; max: string} | null;
    }

    interface BaseLotPoint {
        buyTransactionId: number;
        brokerId: number;
        buyDate: string;
        gainPercent: number;
        buyPrice: number;
        pnlAmount: number;
        costBasis: number;
    }

    interface OpenLotPoint extends BaseLotPoint {
        kind: 'open';
        originalQuantity: number;
        remainingQuantity: number;
        heldRatio: number;
    }

    interface ClosedLotPoint extends BaseLotPoint {
        kind: 'closed';
        quantity: number;
        sellDate: string;
        sellPrice: number;
    }

    type LotPoint = OpenLotPoint | ClosedLotPoint;

    interface ScatterPointDatum {
        name: string;
        value: [string, number];
        meta: LotPoint;
        symbolSize: number;
        itemStyle?: {
            color?: string;
            opacity?: number;
            borderColor?: string;
            borderWidth?: number;
            borderType?: 'solid' | 'dashed' | 'dotted';
            shadowBlur?: number;
            shadowColor?: string;
        };
    }

    let {openLots = [], closedLots = [], brokers = [], currency, onLotClick, xAxisRange = null}: Props = $props();

    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | undefined = undefined;
    let resizeObserver: ResizeObserver | null = null;
    let darkModeObserver: MutationObserver | null = null;
    let tooltipCleanup: (() => void) | null = null;
    let isDark = $state(false);

    function syncTheme() {
        isDark = document.documentElement.classList.contains('dark');
    }

    function safeScalar<T>(value: T | Array<T | null> | null | undefined): T | null {
        if (Array.isArray(value)) return value[0] ?? null;
        return value ?? null;
    }

    function parseNumber(value: string | Array<string | null> | null | undefined): number {
        const raw = safeScalar(value);
        if (raw == null) return 0;
        const parsed = Number.parseFloat(raw);
        return Number.isFinite(parsed) ? parsed : 0;
    }

    function escapeHtml(value: string): string {
        return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function clamp(value: number, min: number, max: number): number {
        return Math.min(max, Math.max(min, value));
    }

    function normalizeZero(value: number): number {
        return Object.is(value, -0) ? 0 : value;
    }

    function formatPercent(value: number, digits = 2): string {
        const normalized = normalizeZero(value);
        const sign = normalized > 0 ? '+' : '';
        return `${sign}${normalized.toFixed(digits)}%`;
    }

    function formatQuantity(value: number): string {
        return value.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 6});
    }

    function formatDate(value: string): string {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return value;
        return date.toLocaleDateString($currentLanguage || undefined, {year: 'numeric', month: 'short', day: 'numeric'});
    }

    function formatDateValue(value: number | string): string {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return String(value);
        return date.toLocaleDateString($currentLanguage || undefined, {month: 'short', day: 'numeric'});
    }

    function pnlColor(value: number, themeDark: boolean): string {
        if (value > 0) return themeDark ? '#4ade80' : '#16a34a';
        if (value < 0) return themeDark ? '#f87171' : '#dc2626';
        return themeDark ? '#60a5fa' : '#2563eb';
    }

    function lotBrokerName(brokerId: number): string {
        return brokers.find((broker) => broker.id === brokerId)?.name ?? `#${brokerId}`;
    }

    function lotBrokerColor(brokerId: number, themeDark: boolean): string {
        const brokerColor = getBrokerColor(brokerId, brokers);
        return themeDark ? brokerColor.vivid : brokerColor.vividLight;
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

    function bubbleSize(quantity: number, maxQuantity: number): number {
        if (maxQuantity <= 0) return 14;
        const normalized = clamp(quantity, 0, maxQuantity) / maxQuantity;
        return 12 + Math.sqrt(normalized) * 26;
    }

    function buildOpenLotPoint(lot: OpenLotSchema): OpenLotPoint {
        const buyPrice = parseNumber(lot.buy_price);
        const originalQuantity = Math.max(0, parseNumber(lot.original_quantity));
        const remainingQuantity = Math.max(0, parseNumber(lot.remaining_quantity));
        const pnlAmount = parseNumber(lot.unrealized_pnl);
        const costBasis = buyPrice * originalQuantity;
        const heldRatio = originalQuantity > 0 ? clamp(remainingQuantity / originalQuantity, 0, 1) : 0;
        const gainPercent = costBasis > 0 ? normalizeZero((pnlAmount / costBasis) * 100) : 0;

        return {
            kind: 'open',
            buyTransactionId: lot.buy_transaction_id,
            brokerId: lot.broker_id,
            buyDate: lot.buy_date,
            gainPercent,
            buyPrice,
            pnlAmount,
            costBasis,
            originalQuantity,
            remainingQuantity,
            heldRatio,
        };
    }

    function buildClosedLotPoint(lot: ClosedLotSchema): ClosedLotPoint {
        const buyPrice = parseNumber(lot.buy_price);
        const sellPrice = parseNumber(lot.sell_price);
        const quantity = Math.max(0, parseNumber(lot.quantity));
        const pnlAmount = parseNumber(lot.realized_pnl);
        const costBasis = buyPrice * quantity;
        const gainPercent = costBasis > 0 ? normalizeZero((pnlAmount / costBasis) * 100) : 0;

        return {
            kind: 'closed',
            buyTransactionId: lot.buy_transaction_id,
            brokerId: lot.broker_id,
            buyDate: lot.buy_date,
            gainPercent,
            buyPrice,
            pnlAmount,
            costBasis,
            quantity,
            sellDate: lot.sell_date,
            sellPrice,
        };
    }

    const chartModel = $derived.by(() => {
        const open = openLots.map(buildOpenLotPoint).sort((a, b) => a.buyDate.localeCompare(b.buyDate));
        const closed = closedLots.map(buildClosedLotPoint).sort((a, b) => a.buyDate.localeCompare(b.buyDate));
        const all = [...open, ...closed];
        const gains = all.map((point) => point.gainPercent);
        const rawMin = gains.length > 0 ? Math.min(...gains) : -5;
        const rawMax = gains.length > 0 ? Math.max(...gains) : 5;
        const spread = rawMax - rawMin;
        const padding = spread > 0 ? spread * 0.18 : 6;
        const axisMin = Math.floor((rawMin - padding) * 100) / 100;
        const axisMax = Math.ceil((rawMax + padding) * 100) / 100;
        const maxQuantity = Math.max(1, ...open.flatMap((point) => [point.originalQuantity, point.remainingQuantity]), ...closed.map((point) => point.quantity));

        return {
            open,
            closed,
            hasData: all.length > 0,
            maxQuantity,
            axisMin: axisMin === axisMax ? axisMin - 1 : axisMin,
            axisMax: axisMin === axisMax ? axisMax + 1 : axisMax,
        };
    });

    const brokerLegendItems = $derived.by(() => {
        const seenBrokerIds = new Set<number>();
        const items: Array<{brokerId: number; name: string}> = [];

        for (const point of [...chartModel.open, ...chartModel.closed]) {
            if (seenBrokerIds.has(point.brokerId)) continue;
            seenBrokerIds.add(point.brokerId);
            items.push({
                brokerId: point.brokerId,
                name: lotBrokerName(point.brokerId),
            });
        }

        return items;
    });

    function buildOpenBackdropData(themeDark: boolean): ScatterPointDatum[] {
        return chartModel.open.map((point) => {
            const color = lotBrokerColor(point.brokerId, themeDark);
            return {
                name: `open-original-${point.buyTransactionId}`,
                value: [point.buyDate, point.gainPercent],
                meta: point,
                symbolSize: bubbleSize(point.originalQuantity, chartModel.maxQuantity),
                itemStyle: {
                    color: 'transparent',
                    borderColor: color,
                    borderWidth: point.heldRatio < 0.999 ? 1.5 : 1,
                    borderType: point.heldRatio < 0.999 ? 'dashed' : 'solid',
                    opacity: point.heldRatio < 0.999 ? 0.35 : 0.18,
                },
            };
        });
    }

    function buildOpenSeriesData(themeDark: boolean): ScatterPointDatum[] {
        return chartModel.open.map((point) => {
            const color = lotBrokerColor(point.brokerId, themeDark);
            return {
                name: `open-${point.buyTransactionId}`,
                value: [point.buyDate, point.gainPercent],
                meta: point,
                symbolSize: bubbleSize(point.remainingQuantity, chartModel.maxQuantity),
                itemStyle: {
                    color,
                    opacity: 0.52 + point.heldRatio * 0.38,
                    borderColor: themeDark ? '#0f172a' : '#ffffff',
                    borderWidth: point.heldRatio < 0.999 ? 2 : 1,
                    shadowBlur: 10,
                    shadowColor: withAlpha(color, 0.2),
                },
            };
        });
    }

    function buildClosedSeriesData(themeDark: boolean): ScatterPointDatum[] {
        return chartModel.closed.map((point) => {
            const color = lotBrokerColor(point.brokerId, themeDark);
            return {
                name: `closed-${point.buyTransactionId}-${point.sellDate}`,
                value: [point.buyDate, point.gainPercent],
                meta: point,
                symbolSize: bubbleSize(point.quantity, chartModel.maxQuantity),
                itemStyle: {
                    color,
                    opacity: 0.72,
                    borderColor: themeDark ? '#475569' : '#cbd5e1',
                    borderWidth: 1.5,
                },
            };
        });
    }

    function buildZeroDotData(themeDark: boolean): ScatterPointDatum[] {
        return [...chartModel.open, ...chartModel.closed].map((point) => ({
            name: `__zero-dot-${point.kind}-${point.buyTransactionId}-${point.buyDate}`,
            value: [point.buyDate, point.gainPercent],
            meta: point,
            symbolSize: 5,
            itemStyle: {
                color: pnlColor(point.gainPercent, themeDark),
                opacity: 1,
            },
        }));
    }

    function buildZeroConnectorSeries(themeDark: boolean): echarts.LineSeriesOption[] {
        return [...chartModel.open, ...chartModel.closed].map((point, index) => ({
            name: `__zero-connector-${index}`,
            type: 'line',
            silent: true,
            tooltip: {show: false},
            data: [
                [point.buyDate, 0],
                [point.buyDate, point.gainPercent],
            ],
            showSymbol: false,
            connectNulls: false,
            emphasis: {disabled: true},
            lineStyle: {
                type: 'dashed',
                width: 1,
                color: pnlColor(point.gainPercent, themeDark),
            },
            z: 1.1,
        }));
    }

    function buildTooltip(meta: LotPoint, themeDark: boolean): string {
        const theme = buildTooltipTheme(themeDark);
        const pointColor = pnlColor(meta.gainPercent, themeDark);
        let html = buildTooltipHeader(escapeHtml(formatDate(meta.buyDate)), theme.textColor);
        html += buildTooltipRow(escapeHtml($t('common.broker') || 'Broker'), escapeHtml(lotBrokerName(meta.brokerId)));
        html += buildTooltipRow(escapeHtml($t('dashboard.status') || 'Status'), escapeHtml(meta.kind === 'open' ? $t('dashboard.openPositions') || 'Open' : $t('dashboard.closedPositions') || 'Closed'), pointColor);

        if (meta.kind === 'open') {
            html += buildTooltipRow(escapeHtml($t('dashboard.quantity') || 'Qty'), escapeHtml(formatQuantity(meta.originalQuantity)));
            html += buildTooltipRow(escapeHtml($t('common.remaining') || 'Remaining'), escapeHtml(`${formatQuantity(meta.remainingQuantity)} (${formatPercent(meta.heldRatio * 100, 1)})`));
            html += buildTooltipRow(escapeHtml($t('dashboard.price') || 'Price'), escapeHtml(formatCurrencyAmountPlain(meta.buyPrice, currency)));
            html += buildTooltipDivider(theme.border);
            html += buildTooltipRow(escapeHtml($t('dashboard.unrealizedPnl') || 'Unrealized P&L'), `<span style="color:${pointColor}">${escapeHtml(formatCurrencyAmountPlain(meta.pnlAmount, currency, {showSign: true}))}</span>`);
        } else {
            html += buildTooltipRow(escapeHtml($t('dashboard.quantity') || 'Qty'), escapeHtml(formatQuantity(meta.quantity)));
            html += buildTooltipRow(escapeHtml($t('dashboard.price') || 'Price'), escapeHtml(`${formatCurrencyAmountPlain(meta.buyPrice, currency)} → ${formatCurrencyAmountPlain(meta.sellPrice, currency)}`));
            html += buildTooltipDivider(theme.border);
            html += buildTooltipRow(escapeHtml($t('dashboard.realized') || 'Realized'), `<span style="color:${pointColor}">${escapeHtml(formatCurrencyAmountPlain(meta.pnlAmount, currency, {showSign: true}))}</span>`);
        }

        html += buildTooltipRow(escapeHtml($t('dashboard.unrealizedPnlPercent') || 'P&L %'), `<span style="color:${pointColor}">${escapeHtml(formatPercent(meta.gainPercent))}</span>`);
        return `<div style="font-size:11px;color:${theme.textColor}">${html}</div>`;
    }

    function buildOption(themeDark: boolean): echarts.EChartsOption {
        const theme = buildTooltipTheme(themeDark);
        const gridColors = buildGridColors(themeDark);
        const openLabel = $t('dashboard.openPositions') || 'Open';
        const closedLabel = $t('dashboard.closedPositions') || 'Closed';

        return {
            ...CHART_ANIMATION_CONFIG,
            animationDurationUpdate: 500,
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
                selectedMode: false,
                textStyle: {
                    color: gridColors.textColor,
                    fontSize: 11,
                },
            },
            tooltip: {
                trigger: 'item',
                position: tooltipPositionSide,
                backgroundColor: theme.bg,
                borderColor: theme.border,
                textStyle: {color: theme.textColor},
                formatter: (params: any) => {
                    const meta = params.data?.meta as LotPoint | undefined;
                    return meta ? buildTooltip(meta, themeDark) : '';
                },
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
                    formatter: (value: number) => formatDateValue(value),
                },
            },
            yAxis: {
                type: 'value',
                min: chartModel.axisMin,
                max: chartModel.axisMax,
                axisLine: {show: false},
                axisTick: {show: false},
                splitLine: {
                    lineStyle: {
                        color: gridColors.gridColor,
                    },
                },
                axisLabel: {
                    color: gridColors.textColor,
                    formatter: (value: number) => `${normalizeZero(value).toFixed(0)}%`,
                },
            },
            series: [
                ...buildZeroConnectorSeries(themeDark),
                {
                    name: '__open-original',
                    type: 'scatter',
                    silent: true,
                    tooltip: {show: false},
                    data: buildOpenBackdropData(themeDark),
                    symbol: 'circle',
                    emphasis: {disabled: true},
                    z: 1,
                },
                {
                    name: openLabel,
                    type: 'scatter',
                    data: buildOpenSeriesData(themeDark),
                    symbol: 'circle',
                    emphasis: {
                        scale: 1.2,
                    },
                    z: 3,
                },
                {
                    name: closedLabel,
                    type: 'scatter',
                    data: buildClosedSeriesData(themeDark),
                    symbol: 'circle',
                    emphasis: {
                        scale: 1.2,
                    },
                    z: 2,
                },
                {
                    name: '__zero-dot',
                    type: 'scatter',
                    silent: true,
                    tooltip: {show: false},
                    data: buildZeroDotData(themeDark),
                    symbol: 'circle',
                    emphasis: {disabled: true},
                    z: 4,
                },
            ],
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
            chartInstance.dispose();
            chartInstance = undefined;
        }

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
            setupResizeObserver();
            tooltipCleanup?.();
            tooltipCleanup = setupTooltipAutoHide(chartContainer, () => chartInstance);
            chartInstance.on('dblclick', (params: any) => {
                const meta = params.data?.meta as LotPoint | undefined;
                if (!meta) return;
                onLotClick?.(meta.buyTransactionId);
            });
        }

        if (!chartModel.hasData) {
            chartInstance.clear();
            return;
        }

        chartInstance.setOption(buildOption(isDark), CHART_SET_OPTION_OPTS);
        chartInstance.resize();
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
            chartInstance?.dispose();
        };
    });

    $effect(() => {
        void openLots;
        void closedLots;
        void brokers;
        void currency;
        void onLotClick;
        void xAxisRange;
        void chartModel;
        void $currentLanguage;

        if (!chartContainer) return;

        tick().then(() => {
            renderChart();
        });
    });
</script>

<div class="w-full">
    <div data-testid="bubble-lot-timeline" class="relative h-80 w-full">
        <div bind:this={chartContainer} class="h-full w-full"></div>
        {#if !chartModel.hasData}
            <div class="pointer-events-none absolute inset-0 flex items-center justify-center text-sm text-gray-400 italic dark:text-gray-500">
                {$t('common.noData')}
            </div>
        {/if}
    </div>

    {#if brokerLegendItems.length >= 2}
        <div data-testid="bubble-broker-legend" class="mt-3 flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-xs text-gray-600 dark:text-gray-300">
            {#each brokerLegendItems as broker (broker.brokerId)}
                <span class="inline-flex items-center gap-1.5">
                    <span class="inline-block h-2.5 w-2.5 rounded-full" style={`background-color: ${lotBrokerColor(broker.brokerId, isDark)}`}></span>
                    <span>{broker.name}</span>
                </span>
            {/each}
        </div>
    {/if}
</div>
