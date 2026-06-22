<!--
  AllocationHistoryChart — 100% stacked area chart for allocation history.

  Shows how portfolio allocation by type, sector, or geography evolved over time.
  Each category is a stacked area layer whose height = percentage weight.

  Props:
  - data: AllocationHistoryPoint[] from POST /allocation-history
  - height: CSS height (default "100%")
  - loading: Show skeleton

  Pattern: Svelte 5 Runes, ECharts, dark mode support.
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {_} from '$lib/i18n';

    interface AllocationComponent {
        name: string;
        value: string;
        amount: string;
    }

    interface AllocationHistoryPoint {
        date: string;
        components: AllocationComponent[];
    }

    interface Props {
        data: AllocationHistoryPoint[];
        height?: string;
        loading?: boolean;
    }

    let {data = [], height = '100%', loading = false}: Props = $props();

    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | undefined = undefined;
    let resizeObserver: ResizeObserver | null = null;
    let darkModeObserver: MutationObserver | null = null;

    // Distinct colors for allocation categories (up to 12)
    const PALETTE_LIGHT = ['#1a4031', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#84cc16', '#ec4899', '#f97316', '#14b8a6', '#6366f1', '#a3a3a3'];
    const PALETTE_DARK = ['#4ade80', '#60a5fa', '#fbbf24', '#f87171', '#a78bfa', '#22d3ee', '#a3e635', '#f472b6', '#fb923c', '#2dd4bf', '#818cf8', '#d4d4d4'];

    // ── Derived: extract unique category names + build per-category series ──
    const categoryNames = $derived.by(() => {
        const names = new Set<string>();
        for (const pt of data) {
            for (const c of pt.components) names.add(c.name);
        }
        return [...names].sort();
    });

    const dates = $derived(data.map((pt) => pt.date));

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
        void data;
        if (chartContainer) {
            tick().then(() => {
                if (!resizeObserver && chartContainer) {
                    resizeObserver = new ResizeObserver(() => chartInstance?.resize());
                    resizeObserver.observe(chartContainer);
                }
                renderChart();
            });
        }
    });

    function renderChart() {
        if (!chartContainer || loading || data.length === 0) return;

        if (chartInstance && chartInstance.getDom() !== chartContainer) {
            chartInstance.dispose();
            chartInstance = undefined;
        }
        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
        }

        const isDark = document.documentElement.classList.contains('dark');
        const palette = isDark ? PALETTE_DARK : PALETTE_LIGHT;
        const textColor = isDark ? '#94a3b8' : '#64748b';
        const gridColor = isDark ? '#1e293b' : '#f1f5f9';
        const tooltipBg = isDark ? '#1e293b' : '#ffffff';
        const tooltipBorder = isDark ? '#334155' : '#e2e8f0';

        // Build one series per category, stacked to 100%
        const series: echarts.SeriesOption[] = categoryNames.map((name, i) => ({
            name,
            type: 'line',
            stack: 'allocation',
            data: data.map((pt) => {
                const comp = pt.components.find((c) => c.name === name);
                return comp ? Number(comp.value) : 0;
            }),
            smooth: false,
            symbol: 'none',
            // Visible boundary line matching area color (same style as GrowthChart stacked)
            lineStyle: {color: palette[i % palette.length], width: 1, opacity: 0.7},
            areaStyle: {color: palette[i % palette.length] + '88'},
            itemStyle: {color: palette[i % palette.length]},
            emphasis: {focus: 'series'},
        }));

        // Pre-build per-category data index for accurate tooltip values
        const seriesDataByName: Record<string, number[]> = {};
        for (const name of categoryNames) {
            seriesDataByName[name] = data.map((pt) => {
                const comp = pt.components.find((c) => c.name === name);
                return comp ? Number(comp.value) : 0;
            });
        }

        const option: echarts.EChartsOption = {
            animation: false,
            backgroundColor: 'transparent',
            grid: {left: '3%', right: '4%', bottom: '40px', top: '10px', containLabel: true},
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
                    const idx = items[0]?.dataIndex ?? 0;

                    // Use raw (non-cumulative) data for correct percentages
                    const lines = categoryNames
                        .map((name, i) => ({
                            name,
                            value: seriesDataByName[name]?.[idx] ?? 0,
                            color: palette[i % palette.length],
                        }))
                        .filter((x) => x.value > 0.01)
                        .sort((a, b) => b.value - a.value)
                        .map((x) => `<div style="display:flex;justify-content:space-between;gap:16px">` + `<span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${x.color};margin-right:6px"></span>${x.name}</span>` + `<b>${x.value.toFixed(1)}%</b></div>`);
                    return `<div style="font-size:11px;color:${textColor};margin-bottom:4px">${date}</div>${lines.join('')}`;
                },
            },
            legend: {
                bottom: 0,
                left: 'center',
                textStyle: {color: textColor, fontSize: 10},
                itemWidth: 12,
                itemHeight: 8,
                type: 'scroll',
            },
            dataZoom: [{type: 'inside', start: 0, end: 100}],
            xAxis: {
                type: 'category',
                data: dates,
                axisLabel: {color: textColor, fontSize: 10, rotate: 0},
                axisLine: {lineStyle: {color: gridColor}},
                splitLine: {show: false},
                boundaryGap: false,
            },
            yAxis: {
                type: 'value',
                max: 100,
                axisLabel: {color: textColor, fontSize: 10, formatter: (v: number) => `${v}%`},
                axisLine: {show: false},
                splitLine: {lineStyle: {color: gridColor, type: 'dashed'}},
            },
            series,
        };

        chartInstance.setOption(option, {notMerge: true});
    }
</script>

{#if loading}
    <div class="w-full h-full bg-gray-100 dark:bg-slate-700 rounded animate-pulse" style="height: {height}"></div>
{:else if data.length === 0}
    <div class="flex items-center justify-center text-gray-400 dark:text-gray-500 text-sm" style="height: {height}">
        {$_('dashboard.noData')}
    </div>
{:else}
    <div bind:this={chartContainer} style="height: {height}; width: 100%;"></div>
{/if}
