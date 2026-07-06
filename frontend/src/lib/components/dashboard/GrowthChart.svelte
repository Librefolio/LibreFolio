<!--
  GrowthChart — Multi-series portfolio growth chart for the Dashboard Home.

  Shows the portfolio's historical performance with a toggle between:
  - ABS mode: Stacked areas (Asset Cost + Returns + Capital) with NAV and
              Deposited Capital overlay lines. P&L = NAV − Deposited Capital.
  - % mode:   3 relative series (MWRR cumulative, TWRR, Simple ROI)

  Uses ECharts directly (LineChart wrapper is single-series only).

  Props:
  - history: PortfolioHistoryPoint[]
  - height: CSS height (default "360px")
  - loading: Show skeleton
  - baseCurrency: Label for Y-axis in ABS mode (default "EUR")

  Pattern: Svelte 5 Runes, ECharts, MutationObserver for dark mode,
           ResizeObserver for responsive sizing.
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {CHART_ANIMATION_CONFIG, CHART_SET_OPTION_OPTS, namedPoint} from '$lib/components/charts/echartsAnimationConfig';
    import {_} from '$lib/i18n';
    import type {PortfolioHistoryPoint} from '$lib/stores/portfolio/portfolioStore.svelte';
    import {buildTooltipTheme, buildDot, buildTooltipHeader, buildTooltipRow, buildTooltipDivider, tooltipPositionSide, setupTooltipAutoHide} from '$lib/components/charts/echartsTooltipHelpers';

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
    /** Tracks last viewMode used for full init — dark mode or viewMode switch requires full re-init */
    let lastRenderedMode: 'eur' | 'pct' | null = null;
    let lastRenderedDark: boolean | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let observedContainer: HTMLDivElement | undefined = undefined;
    let darkModeObserver: MutationObserver | null = null;
    /** True only for the very first render pass right after echarts.init() — mobile
     *  layout (KPI cards etc.) can still be settling then, so ONLY that pass forces an
     *  extra resize() to avoid stale cached dimensions. Later full rebuilds (dark mode
     *  toggle, data updates) happen on an already-stable page and must NOT force a
     *  resize(), since that always triggers a full internal re-render that can
     *  interrupt an active tap-triggered tooltip on mobile — see applyFullOption(). */
    let isFirstRenderPass = false;

    // Color palettes
    const COLORS = {
        nav: {light: '#1a4031', dark: '#4ade80'}, // NAV — prominent line
        bookAssetLike: {light: '#3b82f6', dark: '#60a5fa'}, // Assets at cost — blue area
        cashContributed: {light: '#9caf9c', dark: '#6b8e6b'}, // Capital cash — subdued green area
        cashGenerated: {light: '#10b981', dark: '#34d399'}, // Returns cash — bright emerald area
        capitalBaseline: {light: '#6b7280', dark: '#9ca3af'}, // Capital baseline — grey dashed
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

    // EUR mode: Capital Baseline narrative
    // Stacked areas: book_asset_like + cash_from_contributed + cash_from_generated = book_value
    // Overlay: NAV line (solid) + Capital Baseline line (dashed)
    // P&L = NAV - Capital Baseline (visible as gap between NAV line and baseline line)
    //
    // Convention "returns consumed first":
    //   - Cash from contributed capital = undeployed external capital sitting in cash
    //   - Cash from generated returns = income/gains not yet reinvested
    //   - When buying, returns are consumed first → deposit residuals stay as capital cash
    const eurStackedData = $derived({
        bookAssetLike: history.map((pt) => amt(pt.book_asset_like)),
        cashContributed: history.map((pt) => amt(pt.cash_from_contributed_capital)),
        cashGenerated: history.map((pt) => amt(pt.cash_from_generated_returns)),
        nav: history.map((pt) => (pt.nav_value != null ? Number(pt.nav_value.amount) : null)),
        capitalBaseline: history.map((pt) => amt(pt.capital_baseline)),
        totalPnl: history.map((pt) => amt(pt.total_pnl)),
    });

    /**
     * Period-relative P&L baseline: Total P&L already accumulated at the start of the shown period.
     * Subtracting this gives "how much was gained IN this period", starting at 0.
     */
    const periodBasePnl = $derived(
        (() => {
            const idx = eurStackedData.totalPnl.findIndex((v) => v != null);
            if (idx < 0) return 0;
            return eurStackedData.totalPnl[idx] ?? 0;
        })(),
    );

    // Translated labels for EUR mode (tracked for reactivity on locale change)
    const eurLabels = $derived({
        bookAssetLike: $_('dashboard.assetsAtCost'),
        bookAssetLikeTooltip: $_('dashboard.assetsAtCostTooltip'),
        cashContributed: $_('dashboard.cashFromContributedCapital'),
        cashGenerated: $_('dashboard.cashFromGeneratedReturns'),
        nav: $_('dashboard.navValue'),
        capitalBaseline: $_('dashboard.capitalBaseline'),
        capitalBaselineTooltip: $_('dashboard.capitalBaselineTooltip'),
    });

    const pctSeriesRaw = $derived([
        {
            name: $_('dashboard.mwrrCum'),
            data: history.map((pt) => (pt.mwrr_cumulative != null ? Number(pt.mwrr_cumulative) * 100 : null)),
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
            name: $_('dashboard.roi'),
            data: history.map((pt) => (pt.roi != null ? Number(pt.roi) * 100 : null)),
            lineStyle: 'dotted' as const,
            colorKey: 'pctCash' as const,
        },
    ]);
    // Filter out series with all-null data (e.g. MWRR when marked unreliable)
    const pctSeries = $derived(pctSeriesRaw.filter((s) => s.data.some((v) => v != null)));

    const hasPctData = $derived(history.some((pt) => pt.mwrr_cumulative != null || pt.twrr != null || pt.roi != null));
    const hasNonZeroPctData = $derived(history.some((pt) => Number(pt.mwrr_cumulative ?? 0) !== 0 || Number(pt.twrr ?? 0) !== 0 || Number(pt.roi ?? 0) !== 0));

    // =========================================================================
    // Lifecycle
    // =========================================================================

    let tooltipCleanup: (() => void) | null = null;

    onMount(() => {
        darkModeObserver = new MutationObserver(() => renderChart());
        darkModeObserver.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});

        return () => {
            tooltipCleanup?.();
            darkModeObserver?.disconnect();
            resizeObserver?.disconnect();
            chartInstance?.dispose();
        };
    });

    $effect(() => {
        // Re-render when data, viewMode, or locale changes
        void history;
        void viewMode;
        void pctSeries;
        void eurLabels;
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
        if (!chartContainer || loading || history.length === 0) return;

        if (chartInstance && chartInstance.getDom() !== chartContainer) {
            chartInstance.dispose();
            chartInstance = undefined;
            lastRenderedMode = null;
            lastRenderedDark = null;
        }

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
            isFirstRenderPass = true;
            // Setup mobile tooltip auto-hide
            tooltipCleanup?.();
            tooltipCleanup = setupTooltipAutoHide(chartContainer, () => chartInstance);
        }

        const isDark = document.documentElement.classList.contains('dark');
        const activeDates = dates;

        // Determine if this is a data-only update (same mode, same dark) or full re-init
        const needsFullInit = lastRenderedMode !== viewMode || lastRenderedDark !== isDark;

        // Build series data using named points for ECharts diff matching
        let seriesData: Array<{name: string; data: any[]}>;

        if (viewMode === 'eur') {
            const cc = (key: keyof typeof COLORS) => COLORS[key][isDark ? 'dark' : 'light'];
            seriesData = [
                {name: eurLabels.bookAssetLike, data: activeDates.map((d, i) => namedPoint(d, eurStackedData.bookAssetLike[i]))},
                {name: eurLabels.cashContributed, data: activeDates.map((d, i) => namedPoint(d, eurStackedData.cashContributed[i]))},
                {name: eurLabels.cashGenerated, data: activeDates.map((d, i) => namedPoint(d, eurStackedData.cashGenerated[i]))},
                {name: eurLabels.nav, data: activeDates.map((d, i) => namedPoint(d, eurStackedData.nav[i]))},
                {name: eurLabels.capitalBaseline, data: activeDates.map((d, i) => namedPoint(d, eurStackedData.capitalBaseline[i]))},
            ];

            if (needsFullInit) {
                // Full init with all visual config
                const series: echarts.SeriesOption[] = [
                    {
                        name: eurLabels.bookAssetLike,
                        type: 'line',
                        stack: 'bookValue',
                        data: seriesData[0].data,
                        smooth: false,
                        symbol: 'none',
                        lineStyle: {color: cc('bookAssetLike'), width: 1, opacity: 0.7},
                        areaStyle: {color: cc('bookAssetLike') + '44'},
                        itemStyle: {color: cc('bookAssetLike')},
                        emphasis: {focus: 'series'},
                    },
                    {
                        name: eurLabels.cashContributed,
                        type: 'line',
                        stack: 'bookValue',
                        data: seriesData[1].data,
                        smooth: false,
                        symbol: 'none',
                        lineStyle: {color: cc('cashContributed'), width: 1, opacity: 0.7},
                        areaStyle: {color: cc('cashContributed') + '44'},
                        itemStyle: {color: cc('cashContributed')},
                        emphasis: {focus: 'series'},
                    },
                    {
                        name: eurLabels.cashGenerated,
                        type: 'line',
                        stack: 'bookValue',
                        data: seriesData[2].data,
                        smooth: false,
                        symbol: 'none',
                        lineStyle: {color: cc('cashGenerated'), width: 1, opacity: 0.7},
                        areaStyle: {color: cc('cashGenerated') + '44'},
                        itemStyle: {color: cc('cashGenerated')},
                        emphasis: {focus: 'series'},
                    },
                    {name: eurLabels.nav, type: 'line', data: seriesData[3].data, smooth: false, symbol: 'none', lineStyle: {color: cc('nav'), width: 2, type: 'solid'}, itemStyle: {color: cc('nav')}, emphasis: {focus: 'series'}},
                    {name: eurLabels.capitalBaseline, type: 'line', data: seriesData[4].data, smooth: false, symbol: 'none', lineStyle: {color: cc('capitalBaseline'), width: 1.5, type: 'dashed'}, itemStyle: {color: cc('capitalBaseline')}, emphasis: {focus: 'series'}},
                ];
                applyFullOption(isDark, series);
            } else {
                // Data-only update — partial setOption for smooth transition
                chartInstance.setOption({
                    series: seriesData.map((s) => ({name: s.name, data: s.data})),
                });
            }
        } else {
            seriesData = pctSeries.map((s) => ({
                name: s.name,
                data: activeDates.map((d, i) => namedPoint(d, s.data[i])),
            }));

            if (needsFullInit) {
                const series: echarts.SeriesOption[] = pctSeries.map((s, idx) => ({
                    name: s.name,
                    type: 'line' as const,
                    data: seriesData[idx].data,
                    smooth: false,
                    connectNulls: false,
                    symbol: 'none',
                    lineStyle: {color: COLORS[s.colorKey][isDark ? 'dark' : 'light'], width: 2, type: s.lineStyle},
                    itemStyle: {color: COLORS[s.colorKey][isDark ? 'dark' : 'light']},
                }));
                applyFullOption(isDark, series);
            } else {
                chartInstance.setOption({
                    series: seriesData.map((s) => ({name: s.name, data: s.data})),
                });
            }
        }

        lastRenderedMode = viewMode;
        lastRenderedDark = isDark;
    }

    function applyFullOption(isDark: boolean, series: echarts.SeriesOption[]) {
        if (!chartInstance) return;
        const textColor = isDark ? '#94a3b8' : '#64748b';
        const gridColor = isDark ? '#1e293b' : '#f1f5f9';
        const tooltipBg = isDark ? '#1e293b' : '#ffffff';
        const tooltipBorder = isDark ? '#334155' : '#e2e8f0';

        const yAxisFormatter =
            viewMode === 'eur'
                ? (v: number) => {
                      if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
                      if (Math.abs(v) >= 1_000) return `${(v / 1_000).toFixed(0)}k`;
                      return String(v);
                  }
                : (v: number) => `${v.toFixed(1)}%`;

        /** Format a number as currency — same pattern as the dashboard formatMoney helper. */
        const fmtCurrency = (v: number | null | undefined) => (v != null ? `${baseCurrency} ${v.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : '—');

        const option: echarts.EChartsOption = {
            ...CHART_ANIMATION_CONFIG,
            backgroundColor: 'transparent',
            grid: {left: '3%', right: '4%', bottom: '30px', top: '10px', containLabel: true},
            tooltip: {
                trigger: 'axis',
                appendToBody: true,
                confine: true,
                position: tooltipPositionSide,
                axisPointer: {type: 'line'},
                backgroundColor: tooltipBg,
                borderColor: tooltipBorder,
                borderWidth: 1,
                textStyle: {color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 12},
                formatter: (params: any) => {
                    const items = Array.isArray(params) ? params : [params];
                    // With time axis, axisValue is a timestamp — format to date string
                    const rawDate = items[0]?.axisValue;
                    const date = rawDate instanceof Date ? rawDate.toISOString().slice(0, 10) : typeof rawDate === 'number' ? new Date(rawDate).toISOString().slice(0, 10) : String(rawDate ?? '');
                    const idx = items[0]?.dataIndex ?? 0;

                    if (viewMode === 'eur') {
                        const assetCostVal = eurStackedData.bookAssetLike[idx];
                        const cashGenVal = eurStackedData.cashGenerated[idx];
                        const cashContribVal = eurStackedData.cashContributed[idx];
                        const navVal = eurStackedData.nav[idx];
                        const baselineVal = eurStackedData.capitalBaseline[idx];
                        const totalPnlVal = eurStackedData.totalPnl[idx];

                        const cc = (key: keyof typeof COLORS) => COLORS[key][isDark ? 'dark' : 'light'];
                        const dot = (key: keyof typeof COLORS) => `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${cc(key)};margin-right:6px;flex-shrink:0"></span>`;
                        const fmtOrDash = (v: number | null | undefined) => (v != null && v !== 0 ? fmtCurrency(v) : '—');

                        let html = `<div style="font-size:11px;color:${textColor};margin-bottom:4px">${date}</div>`;
                        // NAV
                        html += `<div style="display:flex;justify-content:space-between;gap:16px"><span>${dot('nav')}<b>${eurLabels.nav}</b></span><b>${fmtCurrency(navVal)}</b></div>`;
                        // Capital Baseline (full label in tooltip)
                        html += `<div style="display:flex;justify-content:space-between;gap:16px"><span>${dot('capitalBaseline')}${eurLabels.capitalBaselineTooltip}</span>${fmtCurrency(baselineVal)}</div>`;
                        // Total P&L + formula hint immediately below
                        if (totalPnlVal != null) {
                            const pnlColor = totalPnlVal >= 0 ? (isDark ? '#4ade80' : '#16a34a') : isDark ? '#f87171' : '#dc2626';
                            html += `<div style="display:flex;justify-content:space-between;gap:16px;color:${pnlColor}"><span><b>${$_('dashboard.totalPnl')}</b></span><b>${totalPnlVal >= 0 ? '+' : '−'}${fmtCurrency(Math.abs(totalPnlVal))}</b></div>`;
                        }
                        html += `<div style="font-size:10px;color:${textColor};opacity:0.7">${$_('dashboard.pnlFormulaHint')}</div>`;
                        html += `<hr style="border:none;border-top:1px solid ${tooltipBorder};margin:4px 0"/>`;
                        // Stacked breakdown — always show (use — for zero)
                        html += `<div style="display:flex;justify-content:space-between;gap:16px"><span>${dot('bookAssetLike')}${eurLabels.bookAssetLikeTooltip}</span>${fmtOrDash(assetCostVal)}</div>`;
                        html += `<div style="display:flex;justify-content:space-between;gap:16px"><span>${dot('cashGenerated')}${eurLabels.cashGenerated}</span>${fmtOrDash(cashGenVal)}</div>`;
                        html += `<div style="display:flex;justify-content:space-between;gap:16px"><span>${dot('cashContributed')}${eurLabels.cashContributed}</span>${fmtOrDash(cashContribVal)}</div>`;
                        return html;
                    }

                    // % mode: simple list with colored dots
                    const lines = items
                        .filter((p: any) => p.value != null)
                        .map((p: any) => {
                            // With namedPoint format, p.value is [date, number] — extract the numeric part
                            const rawVal = Array.isArray(p.value) ? p.value[1] : p.value;
                            const val = `${Number(rawVal).toFixed(2)}%`;
                            return `<div style="display:flex;justify-content:space-between;gap:16px"><span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:6px"></span>${p.seriesName}</span><b>${val}</b></div>`;
                        });
                    return `<div style="font-size:11px;color:${textColor};margin-bottom:4px">${date}</div>${lines.join('')}`;
                },
            },
            legend: {
                type: 'scroll',
                bottom: 0,
                left: 'center',
                textStyle: {color: textColor, fontSize: 11},
                itemWidth: 14,
                itemHeight: 8,
            },
            dataZoom: [{type: 'inside', start: 0, end: 100}],
            xAxis: {
                type: 'time',
                axisLabel: {color: textColor, fontSize: 11, rotate: 0},
                axisLine: {lineStyle: {color: gridColor}},
                splitLine: {show: false},
            },
            yAxis: {
                type: 'value',
                // Use a min function so the y-axis auto-scales rather than forcing 0.
                // This gives detail visibility when portfolio values are large.
                min: (value: {min: number; max: number}) => Math.floor(value.min - (value.max - value.min) * 0.08),
                axisLabel: {color: textColor, fontSize: 11, formatter: yAxisFormatter},
                axisLine: {show: false},
                splitLine: {lineStyle: {color: gridColor, type: 'dashed'}},
            },
            series,
        };

        chartInstance.setOption(option, CHART_SET_OPTION_OPTS);
        // Bugfix: on mobile, the very FIRST render can happen while the surrounding
        // layout (KPI cards etc.) is still settling, so ECharts caches stale internal
        // dimensions — causing the position-aware tooltip (tooltipPositionSide) to
        // compute wildly wrong coordinates (reported: tooltip appears far below the
        // viewport on first load, translate3d(...) with a huge Y offset). Toggling the
        // view mode "fixed" it because that path re-triggers this same full-rebuild
        // branch on a LATER, already-settled pass.
        //
        // IMPORTANT: this forced resize() must be scoped to ONLY the very first render
        // pass, never to later full rebuilds (dark mode toggle, data updates) — resize()
        // always triggers a full internal re-render (see node_modules/echarts
        // .../TooltipView.js `render()`/`_keepShow()`), which was found to interrupt a
        // just-shown tap-triggered tooltip on mobile (it would flash and disappear
        // immediately) if a rebuild happened to fire while the tooltip was showing.
        // A plain immediate resize() alone isn't always enough either — some mobile
        // layouts keep shifting for another frame or two after our own tick() resolves
        // (e.g. KPI cards populating async data) — so also schedule one more resize()
        // on the next animation frame, still gated to first-render-only.
        if (isFirstRenderPass) {
            isFirstRenderPass = false;
            chartInstance.resize();
            const instanceAtSchedule = chartInstance;
            requestAnimationFrame(() => {
                if (instanceAtSchedule && !instanceAtSchedule.isDisposed()) instanceAtSchedule.resize();
            });
        }
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
                title={!hasPctData ? $_('common.noData') : ''}
                data-testid="growth-toggle-pct"
            >
                {$_('dashboard.pct')}
            </button>
        </div>
    </div>

    <!-- Chart area — container always in DOM for animation persistence -->
    <div class="relative" style="height: {height}">
        <!-- Skeleton / empty overlay -->
        {#if loading}
            <div class="absolute inset-0 z-10 bg-gray-100 dark:bg-slate-700 rounded animate-pulse"></div>
        {:else if history.length === 0}
            <div class="absolute inset-0 z-10 flex items-center justify-center text-gray-400 dark:text-gray-500 text-sm">
                {$_('common.noData')}
            </div>
        {/if}
        <!-- Persistent chart container — never destroyed -->
        <div bind:this={chartContainer} style="height: 100%; width: 100%;" class:invisible={loading || history.length === 0}></div>
    </div>
    {#if !loading && history.length > 0 && viewMode === 'pct' && hasPctData && !hasNonZeroPctData}
        <p class="text-center text-xs text-gray-400 dark:text-gray-500 italic mt-1">
            {$_('dashboard.roiAllZero')}
        </p>
    {/if}
</div>
