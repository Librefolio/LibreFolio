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
        nav: {light: '#1a4031', dark: '#4ade80'}, // NAV / MWRR — prominent
        invested: {light: '#2563eb', dark: '#60a5fa'}, // Invested / TWRR
        cash: {light: '#9caf9c', dark: '#94a3b8'}, // Cash / ROI — subdued
    };

    // =========================================================================
    // Derived data for chart
    // =========================================================================

    const dates = $derived(history.map((pt) => pt.date));

    const eurSeries = $derived([
        {
            name: $_('dashboard.navValue'),
            data: history.map((pt) => (pt.nav_value != null ? Number(pt.nav_value.amount) : null)),
            lineStyle: 'solid' as const,
            colorKey: 'nav' as const,
            areaOpacity: 0.1,
        },
        {
            name: $_('dashboard.investedCapital'),
            data: history.map((pt) => (pt.invested_value != null ? Number(pt.invested_value.amount) : null)),
            lineStyle: 'dashed' as const,
            colorKey: 'invested' as const,
            areaOpacity: 0,
        },
        {
            name: $_('dashboard.cashValue'),
            data: history.map((pt) => (pt.cash_value != null ? Number(pt.cash_value.amount) : null)),
            lineStyle: 'dotted' as const,
            colorKey: 'cash' as const,
            areaOpacity: 0,
        },
    ]);

    const pctSeries = $derived([
        {
            name: $_('dashboard.mwrr'),
            data: history.map((pt) => (pt.mwrr != null ? Number(pt.mwrr) * 100 : null)),
            lineStyle: 'solid' as const,
            colorKey: 'nav' as const,
            areaOpacity: 0,
        },
        {
            name: $_('dashboard.twrr'),
            data: history.map((pt) => (pt.twrr != null ? Number(pt.twrr) * 100 : null)),
            lineStyle: 'dashed' as const,
            colorKey: 'invested' as const,
            areaOpacity: 0,
        },
        {
            name: $_('dashboard.simpleRoi'),
            data: history.map((pt) => (pt.roi != null ? Number(pt.roi) * 100 : null)),
            lineStyle: 'dotted' as const,
            colorKey: 'cash' as const,
            areaOpacity: 0,
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

        // If chartInstance points to a stale/detached element (e.g. after {#if loading}
        // unmounted and remounted the container), dispose it and start fresh.
        if (chartInstance && chartInstance.getDom() !== chartContainer) {
            chartInstance.dispose();
            chartInstance = undefined;
        }

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
        }

        const isDark = document.documentElement.classList.contains('dark');
        const activeSeries = viewMode === 'eur' ? eurSeries : pctSeries;
        const activeDates = dates;

        const textColor = isDark ? '#94a3b8' : '#64748b';
        const gridColor = isDark ? '#1e293b' : '#f1f5f9';
        const tooltipBg = isDark ? '#1e293b' : '#ffffff';
        const tooltipBorder = isDark ? '#334155' : '#e2e8f0';

        const series: echarts.SeriesOption[] = activeSeries.map((s) => ({
            name: s.name,
            type: 'line',
            data: s.data,
            smooth: false,
            connectNulls: false,
            symbol: 'none',
            lineStyle: {
                color: COLORS[s.colorKey][isDark ? 'dark' : 'light'],
                width: 2,
                type: s.lineStyle,
            },
            itemStyle: {
                color: COLORS[s.colorKey][isDark ? 'dark' : 'light'],
            },
            areaStyle:
                s.areaOpacity > 0
                    ? {
                          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                              {offset: 0, color: COLORS[s.colorKey][isDark ? 'dark' : 'light'] + '1a'},
                              {offset: 1, color: COLORS[s.colorKey][isDark ? 'dark' : 'light'] + '00'},
                          ]),
                      }
                    : undefined,
        }));

        const yAxisFormatter = viewMode === 'eur' ? (v: number) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)) : (v: number) => `${v.toFixed(1)}%`;

        const option: echarts.EChartsOption = {
            animation: false,
            backgroundColor: 'transparent',
            grid: {left: '3%', right: '4%', bottom: '30px', top: '10px', containLabel: true},
            tooltip: {
                trigger: 'axis',
                backgroundColor: tooltipBg,
                borderColor: tooltipBorder,
                borderWidth: 1,
                textStyle: {color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 12},
                formatter: (params: any) => {
                    const date = Array.isArray(params) ? params[0]?.axisValue : '';
                    const lines = (Array.isArray(params) ? params : [params])
                        .filter((p: any) => p.value != null)
                        .map((p: any) => {
                            const val = viewMode === 'eur' ? `${baseCurrency} ${Number(p.value).toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : `${Number(p.value).toFixed(2)}%`;
                            return `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:6px"></span>${p.seriesName}: <b>${val}</b>`;
                        });
                    return `<div style="font-size:11px;color:${textColor};margin-bottom:4px">${date}</div>${lines.join('<br/>')}`;
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
