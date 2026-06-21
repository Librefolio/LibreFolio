<!--
  GrowthChart — Multi-series portfolio growth chart for the Dashboard Home.

  Shows the portfolio's historical performance with a toggle between:
  - EUR mode: 3 absolute series (NAV, Invested Capital, Cash)
  - % mode:   3 relative series (MWRR, TWRR, Simple ROI)

  Uses ECharts directly (LineChart wrapper is single-series only).

  Props:
  - history: PortfolioHistoryPoint[]
  - height: CSS height (default "360px")
  - loading: Show skeleton
  - baseCurrency: Label for Y-axis in EUR mode (default "EUR")

  Pattern: Svelte 5 Runes, ECharts, MutationObserver for dark mode,
           ResizeObserver for responsive sizing.
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {_} from '$lib/i18n';
    import type {PortfolioHistoryPoint} from '$lib/stores/portfolio/portfolioStore.svelte';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        history: PortfolioHistoryPoint[];
        height?: string;
        loading?: boolean;
        baseCurrency?: string;
    }

    let {history = [], height = '360px', loading = false, baseCurrency = 'EUR'}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let viewMode: 'eur' | 'pct' = $state('eur');
    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | undefined = undefined;
    let resizeObserver: ResizeObserver | null = null;
    let observedContainer: HTMLDivElement | undefined = undefined;
    let darkModeObserver: MutationObserver | null = null;

    // Color palettes
    const COLORS = {
        nav: {light: '#1a4031', dark: '#4ade80'}, // NAV — prominent line
        costBasis: {light: '#3b82f6', dark: '#60a5fa'}, // Open cost basis — blue area
        cash: {light: '#9caf9c', dark: '#6b8e6b'}, // Cash — subdued green area
        inTransit: {light: '#f59e0b', dark: '#fbbf24'}, // In-transit — amber area
        invested: {light: '#2563eb', dark: '#60a5fa'}, // TWRR (% mode)
        pctCash: {light: '#9caf9c', dark: '#94a3b8'}, // ROI (% mode)
    };

    // =========================================================================
    // Derived data for chart
    // =========================================================================

    const dates = $derived(history.map((pt) => pt.date));

    /** Helper to safely extract amount from an optional Currency field (handles union types). */
    function amt(field: any): number | null {
        if (field != null && !Array.isArray(field) && typeof field === 'object' && 'amount' in field) return Number(field.amount);
        return null;
    }

    // EUR mode: stacked area (open_cost_basis + cash + in_transit_book_value) + NAV overlay
    const eurStackedData = $derived({
        costBasis: history.map((pt) => amt(pt.open_cost_basis)),
        cash: history.map((pt) => (pt.cash_value != null ? Number(pt.cash_value.amount) : null)),
        inTransit: history.map((pt) => amt(pt.in_transit_book_value)),
        nav: history.map((pt) => (pt.nav_value != null ? Number(pt.nav_value.amount) : null)),
    });

    const pctSeries = $derived([
        {
            name: $_('dashboard.mwrr'),
            data: history.map((pt) => (pt.mwrr != null ? Number(pt.mwrr) * 100 : null)),
            lineStyle: 'solid' as const,
            colorKey: 'nav' as const,
        },
        {
            name: $_('dashboard.twrr'),
            data: history.map((pt) => (pt.twrr != null ? Number(pt.twrr) * 100 : null)),
            lineStyle: 'dashed' as const,
            colorKey: 'invested' as const,
        },
        {
            name: $_('dashboard.simpleRoi'),
            data: history.map((pt) => (pt.roi != null ? Number(pt.roi) * 100 : null)),
            lineStyle: 'dotted' as const,
            colorKey: 'pctCash' as const,
        },
    ]);

    const hasPctData = $derived(history.some((pt) => pt.mwrr != null || pt.twrr != null || pt.roi != null));
    const hasNonZeroPctData = $derived(history.some((pt) => Number(pt.mwrr ?? 0) !== 0 || Number(pt.twrr ?? 0) !== 0 || Number(pt.roi ?? 0) !== 0));

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(() => {
        darkModeObserver = new MutationObserver(() => renderChart());
        darkModeObserver.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});

        return () => {
            darkModeObserver?.disconnect();
            resizeObserver?.disconnect();
            chartInstance?.dispose();
        };
    });

    $effect(() => {
        // Re-render when data or viewMode changes
        void history;
        void viewMode;
        if (chartContainer) {
            tick().then(() => {
                setupResizeObserver();
                renderChart();
            });
        }
    });

    // =========================================================================
    // Helpers
    // =========================================================================

    function setupResizeObserver() {
        if (!chartContainer) return;
        // If already observing the same element, nothing to do
        if (resizeObserver && observedContainer === chartContainer) return;
        resizeObserver?.disconnect();
        resizeObserver = new ResizeObserver(() => chartInstance?.resize());
        resizeObserver.observe(chartContainer);
        observedContainer = chartContainer;
    }

    function renderChart() {
        if (!chartContainer || loading) return;

        if (chartInstance && chartInstance.getDom() !== chartContainer) {
            chartInstance.dispose();
            chartInstance = undefined;
        }

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
        }

        const isDark = document.documentElement.classList.contains('dark');
        const activeDates = dates;

        const textColor = isDark ? '#94a3b8' : '#64748b';
        const gridColor = isDark ? '#1e293b' : '#f1f5f9';
        const tooltipBg = isDark ? '#1e293b' : '#ffffff';
        const tooltipBorder = isDark ? '#334155' : '#e2e8f0';

        let series: echarts.SeriesOption[];

        if (viewMode === 'eur') {
            const cc = (key: keyof typeof COLORS) => COLORS[key][isDark ? 'dark' : 'light'];
            series = [
                // Stacked area: open_cost_basis (bottom) — visible boundary line
                {
                    name: $_('dashboard.openCostBasis'),
                    type: 'line',
                    stack: 'bookValue',
                    data: eurStackedData.costBasis,
                    smooth: false,
                    symbol: 'none',
                    lineStyle: {color: cc('costBasis'), width: 1, opacity: 0.7},
                    areaStyle: {color: cc('costBasis') + '55'},
                    itemStyle: {color: cc('costBasis')},
                    emphasis: {focus: 'series'},
                },
                // Stacked area: cash (middle) — visible boundary line
                {
                    name: $_('dashboard.cashValue'),
                    type: 'line',
                    stack: 'bookValue',
                    data: eurStackedData.cash,
                    smooth: false,
                    symbol: 'none',
                    lineStyle: {color: cc('cash'), width: 1, opacity: 0.7},
                    areaStyle: {color: cc('cash') + '55'},
                    itemStyle: {color: cc('cash')},
                    emphasis: {focus: 'series'},
                },
                // Stacked area: in-transit book value (top) — visible boundary line
                {
                    name: $_('dashboard.inTransit'),
                    type: 'line',
                    stack: 'bookValue',
                    data: eurStackedData.inTransit,
                    smooth: false,
                    symbol: 'none',
                    lineStyle: {color: cc('inTransit'), width: 1, opacity: 0.7},
                    areaStyle: {color: cc('inTransit') + '55'},
                    itemStyle: {color: cc('inTransit')},
                    emphasis: {focus: 'series'},
                },
                // Overlay line: NAV (not stacked) — prominent
                {
                    name: $_('dashboard.navValue'),
                    type: 'line',
                    data: eurStackedData.nav,
                    smooth: false,
                    symbol: 'none',
                    lineStyle: {color: cc('nav'), width: 2, type: 'solid'},
                    itemStyle: {color: cc('nav')},
                    emphasis: {focus: 'series'},
                },
            ];
        } else {
            series = pctSeries.map((s) => ({
                name: s.name,
                type: 'line' as const,
                data: s.data,
                smooth: false,
                connectNulls: false,
                symbol: 'none',
                lineStyle: {
                    color: COLORS[s.colorKey][isDark ? 'dark' : 'light'],
                    width: 2,
                    type: s.lineStyle,
                },
                itemStyle: {color: COLORS[s.colorKey][isDark ? 'dark' : 'light']},
            }));
        }

        const yAxisFormatter = viewMode === 'eur'
            ? (v: number) => {
                  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
                  if (Math.abs(v) >= 1_000) return `${(v / 1_000).toFixed(0)}k`;
                  return String(v);
              }
            : (v: number) => `${v.toFixed(1)}%`;

        /** Format a number as currency — same pattern as the dashboard formatMoney helper. */
        const fmtCurrency = (v: number | null | undefined) =>
            v != null
                ? `${baseCurrency} ${v.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`
                : '—';

        const option: echarts.EChartsOption = {
            animation: false,
            backgroundColor: 'transparent',
            grid: {left: '3%', right: '4%', bottom: '30px', top: '10px', containLabel: true},
            tooltip: {
                trigger: 'axis',
                axisPointer: {type: 'cross', label: {backgroundColor: '#6a7985'}},
                backgroundColor: tooltipBg,
                borderColor: tooltipBorder,
                borderWidth: 1,
                textStyle: {color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 12},
                formatter: (params: any) => {
                    const items = Array.isArray(params) ? params : [params];
                    const date = items[0]?.axisValue ?? '';

                    if (viewMode === 'eur') {
                        // ECharts stacks values cumulatively in params[i].value — use raw data index instead
                        const idx = items[0]?.dataIndex ?? 0;
                        const costVal = eurStackedData.costBasis[idx];
                        const cashVal = eurStackedData.cash[idx];
                        const itVal = eurStackedData.inTransit[idx];
                        const navVal = eurStackedData.nav[idx];

                        const bv = (costVal ?? 0) + (cashVal ?? 0) + (itVal ?? 0);
                        const ugl = navVal != null ? navVal - bv : null;

                        const cc = (key: keyof typeof COLORS) => COLORS[key][isDark ? 'dark' : 'light'];
                        const dot = (key: keyof typeof COLORS) =>
                            `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${cc(key)};margin-right:6px;flex-shrink:0"></span>`;

                        let html = `<div style="font-size:11px;color:${textColor};margin-bottom:4px">${date}</div>`;
                        html += `<div style="display:flex;justify-content:space-between;gap:16px"><span>${dot('nav')}<b>${$_('dashboard.navValue')}</b></span><b>${fmtCurrency(navVal)}</b></div>`;
                        html += `<div style="display:flex;justify-content:space-between;gap:16px"><span><b>${$_('dashboard.bookValue')}</b></span><b>${fmtCurrency(bv || null)}</b></div>`;
                        if (ugl != null) {
                            const uglColor = ugl >= 0 ? (isDark ? '#4ade80' : '#16a34a') : (isDark ? '#f87171' : '#dc2626');
                            html += `<div style="display:flex;justify-content:space-between;gap:16px;color:${uglColor}"><span>± P/L</span><b>${ugl >= 0 ? '+' : ''}${fmtCurrency(Math.abs(ugl))}</b></div>`;
                        }
                        html += `<hr style="border:none;border-top:1px solid ${tooltipBorder};margin:4px 0"/>`;
                        html += `<div style="display:flex;justify-content:space-between;gap:16px"><span>${dot('costBasis')}${$_('dashboard.openCostBasis')}</span>${fmtCurrency(costVal)}</div>`;
                        html += `<div style="display:flex;justify-content:space-between;gap:16px"><span>${dot('cash')}${$_('dashboard.cashValue')}</span>${fmtCurrency(cashVal)}</div>`;
                        if (itVal && itVal > 0) {
                            html += `<div style="display:flex;justify-content:space-between;gap:16px"><span>${dot('inTransit')}${$_('dashboard.inTransit')}</span>${fmtCurrency(itVal)}</div>`;
                        }
                        return html;
                    }

                    // % mode: simple list with colored dots
                    const lines = items
                        .filter((p: any) => p.value != null)
                        .map((p: any) => {
                            const val = `${Number(p.value).toFixed(2)}%`;
                            return `<div style="display:flex;justify-content:space-between;gap:16px"><span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:6px"></span>${p.seriesName}</span><b>${val}</b></div>`;
                        });
                    return `<div style="font-size:11px;color:${textColor};margin-bottom:4px">${date}</div>${lines.join('')}`;
                },
            },
            legend: {
                bottom: 0,
                left: 'center',
                textStyle: {color: textColor, fontSize: 11},
                itemWidth: 14,
                itemHeight: 8,
            },
            dataZoom: [{type: 'inside', start: 0, end: 100}],
            xAxis: {
                type: 'category',
                data: activeDates,
                axisLabel: {color: textColor, fontSize: 11, rotate: 0},
                axisLine: {lineStyle: {color: gridColor}},
                splitLine: {show: false},
                boundaryGap: false,
            },
            yAxis: {
                type: 'value',
                // Use a min function so the y-axis auto-scales rather than forcing 0.
                // This gives detail visibility when portfolio values are large.
                min: (value: {min: number; max: number}) =>
                    Math.floor(value.min - (value.max - value.min) * 0.08),
                axisLabel: {color: textColor, fontSize: 11, formatter: yAxisFormatter},
                axisLine: {show: false},
                splitLine: {lineStyle: {color: gridColor, type: 'dashed'}},
            },
            series,
        };

        chartInstance.setOption(option, {notMerge: true});
    }
</script>

<div class="bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm p-4 flex flex-col gap-3" data-testid="growth-chart">
    <!-- Header row: title + toggle -->
    <div class="flex items-center justify-between">
        <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-200">{$_('dashboard.growth')}</h2>

        <!-- Abs / % segmented toggle -->
        <div class="flex rounded-lg overflow-hidden border border-gray-200 dark:border-slate-600 text-xs font-medium">
            <button class="px-3 py-1 transition-colors {viewMode === 'eur' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}" onclick={() => (viewMode = 'eur')} data-testid="growth-toggle-eur">
                {$_('dashboard.abs')}
            </button>
            <button
                class="px-3 py-1 transition-colors border-l border-gray-200 dark:border-slate-600 {viewMode === 'pct' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'} {!hasPctData
                    ? 'opacity-50 cursor-not-allowed'
                    : ''}"
                onclick={() => hasPctData && (viewMode = 'pct')}
                disabled={!hasPctData}
                title={!hasPctData ? $_('dashboard.noData') : ''}
                data-testid="growth-toggle-pct"
            >
                {$_('dashboard.pct')}
            </button>
        </div>
    </div>

    <!-- Chart area -->
    {#if loading || history.length === 0}
        <div class="flex items-center justify-center text-gray-400 dark:text-gray-500 text-sm" style="height: {height}">
            {#if loading}
                <div class="w-full h-full bg-gray-100 dark:bg-slate-700 rounded animate-pulse"></div>
            {:else}
                {$_('dashboard.noData')}
            {/if}
        </div>
    {:else}
        <div bind:this={chartContainer} style="height: {height}; width: 100%;"></div>
        {#if viewMode === 'pct' && hasPctData && !hasNonZeroPctData}
            <p class="text-center text-xs text-gray-400 dark:text-gray-500 italic mt-1">
                {$_('dashboard.roiAllZero')}
            </p>
        {/if}
    {/if}
</div>
