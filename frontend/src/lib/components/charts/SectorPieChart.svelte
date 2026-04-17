<!--
  SectorPieChart — Pie chart for sector distribution visualization.

  Shows sector allocation as a standard pie chart with ECharts.
  Supports i18n sector labels, dark mode, and responsive sizing.

  Props:
  - data: Record<string, number> — sector key → weight (0–1)
  - height: CSS height (default "280px")

  Used by:
  - Asset Detail Page (metadata section)
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {_ as t} from '$lib/i18n';
    import {sectorI18nKey} from '$lib/utils/assetTypes';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Sector distribution: key = sector name, value = weight (0-1) */
        data: Record<string, number>;
        /** CSS height of the chart container */
        height?: string;
    }

    let {data = {}, height = '280px'}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | null = null;
    let resizeObserver: ResizeObserver | null = null;

    // Diversified color palette — high chromatic distance
    const PALETTE_LIGHT = ['#1a4031', '#2563eb', '#7c3aed', '#dc2626', '#d97706', '#0d9488', '#be185d', '#4f46e5', '#059669', '#ea580c', '#6366f1', '#0891b2', '#ca8a04', '#9333ea'];
    const PALETTE_DARK = ['#4ade80', '#60a5fa', '#a78bfa', '#f87171', '#fbbf24', '#2dd4bf', '#f472b6', '#818cf8', '#34d399', '#fb923c', '#a5b4fc', '#22d3ee', '#facc15', '#c084fc'];

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(() => {
        // Re-render on dark mode toggle
        const observer = new MutationObserver(() => renderChart());
        observer.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
        return () => {
            observer.disconnect();
            cleanup();
        };
    });

    $effect(() => {
        if (chartContainer && data) {
            tick().then(() => {
                setupResizeObserver();
                renderChart();
            });
        }
    });

    function setupResizeObserver() {
        if (resizeObserver || !chartContainer) return;
        resizeObserver = new ResizeObserver(() => {
            renderChart();
        });
        resizeObserver.observe(chartContainer);
    }

    function cleanup() {
        resizeObserver?.disconnect();
        resizeObserver = null;
        chartInstance?.dispose();
        chartInstance = null;
    }

    // =========================================================================
    // Chart Rendering
    // =========================================================================

    function renderChart() {
        if (!chartContainer) return;

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
        }

        const isDark = document.documentElement.classList.contains('dark');
        const tr = $t;
        const palette = isDark ? PALETTE_DARK : PALETTE_LIGHT;

        // Build chart data from Record
        const entries = Object.entries(data).filter(([, v]) => v > 0);
        if (entries.length === 0) {
            chartInstance.setOption({series: []}, true);
            return;
        }

        const chartData = entries
            .map(([key, value]) => {
                // Try i18n translation, fallback to raw key
                const i18nKey = `sectors.${sectorI18nKey(key)}`;
                const label = tr(i18nKey) !== i18nKey ? tr(i18nKey) : key.replace(/_/g, ' ');
                return {
                    name: label,
                    value: +(value * 100).toFixed(2),
                };
            })
            .sort((a, b) => b.value - a.value);

        // Responsive: if container is narrow, put legend below instead of right
        const containerWidth = chartContainer.getBoundingClientRect().width;
        const isNarrow = containerWidth < 400;

        const legendConfig: any = isNarrow
            ? {
                  type: 'plain',
                  orient: 'horizontal',
                  bottom: 0,
                  left: 'center',
                  width: '95%',
                  textStyle: {color: isDark ? '#94a3b8' : '#64748b', fontSize: 11},
              }
            : {
                  type: 'scroll',
                  orient: 'vertical',
                  right: 10,
                  top: 20,
                  bottom: 20,
                  textStyle: {color: isDark ? '#94a3b8' : '#64748b', fontSize: 11},
                  pageTextStyle: {color: isDark ? '#94a3b8' : '#64748b'},
                  pageIconColor: isDark ? '#94a3b8' : '#64748b',
                  pageIconInactiveColor: isDark ? '#334155' : '#cbd5e1',
              };

        const pieCenter = isNarrow ? ['50%', '40%'] : ['35%', '50%'];
        const pieRadius = isNarrow ? ['25%', '55%'] : ['35%', '70%'];

        const option: echarts.EChartsOption = {
            color: palette,
            tooltip: {
                trigger: 'item',
                formatter: '{b}: {c}%',
                backgroundColor: isDark ? '#1e293b' : '#fff',
                borderColor: isDark ? '#334155' : '#e2e8f0',
                textStyle: {color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 12},
            },
            legend: legendConfig,
            series: [
                {
                    type: 'pie',
                    radius: pieRadius,
                    center: pieCenter,
                    avoidLabelOverlap: true,
                    padAngle: 1,
                    itemStyle: {
                        borderRadius: 4,
                        borderColor: isDark ? '#293548' : '#ffffff',
                        borderWidth: 2,
                    },
                    label: {
                        show: false,
                    },
                    emphasis: {
                        label: {
                            show: true,
                            fontSize: 13,
                            fontWeight: 'bold',
                            formatter: '{b}\n{c}%',
                            color: isDark ? '#e2e8f0' : '#1e293b',
                        },
                        scaleSize: 5,
                    },
                    labelLine: {show: false},
                    data: chartData,
                },
            ],
        };

        chartInstance.setOption(option, true);
        chartInstance.resize();
    }
</script>

<div bind:this={chartContainer} class="w-full" style="height: {height};"></div>
