<!--
  AllocationPieChart — Pie chart for allocation distribution (sector or asset type).

  Supports two modes:
  - 'sector' (default): translates sector keys via sectors.* i18n; shows only
    the leading emoji inside each slice, full label in legend and tooltip.
  - 'type': translates asset-type keys via assets.types.*; shows the PNG icon
    inside each slice (ECharts rich text), icon + label in legend and tooltip.

  Props:
  - data: Record<string, number> — key → weight (0–1)
  - height: CSS height (default "280px")
  - mode: 'sector' | 'type' (default 'sector')

  Used by:
  - Dashboard page (allocation panel, both type and sector tabs)
  - Asset Detail Page (metadata section, sector distribution)
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {_ as t} from '$lib/i18n';
    import {sectorI18nKey, getAssetTypeIconUrl} from '$lib/utils/assetTypes';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Allocation data: key → weight (0-1) */
        data: Record<string, number>;
        /** CSS height of the chart container */
        height?: string;
        /** Display mode: 'sector' uses i18n sector labels with emojis; 'type' uses asset type PNG icons */
        mode?: 'sector' | 'type';
        /**
         * Legend placement strategy.
         * - 'auto' (default): legend on the right when wide, below when narrow (<400px)
         * - 'bottom': legend always below the pie (better for constrained-height panels)
         */
        legendPosition?: 'auto' | 'bottom';
    }

    let {data = {}, height = '280px', mode = 'sector', legendPosition = 'auto'}: Props = $props();

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
        resizeObserver = new ResizeObserver(() => renderChart());
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

        const entries = Object.entries(data).filter(([, v]) => v > 0);
        if (entries.length === 0) {
            chartInstance.setOption({series: []}, true);
            return;
        }

        // Build chart data.
        // sector: name = full translated label (e.g. "💻 Technology")
        // type:   name = raw key (e.g. "STOCK") — translated in formatters
        const chartData = entries
            .map(([key, value]) => {
                let name: string;
                if (mode === 'sector') {
                    const i18nKey = `sectors.${sectorI18nKey(key)}`;
                    name = tr(i18nKey) !== i18nKey ? tr(i18nKey) : key.replace(/_/g, ' ');
                } else {
                    name = key;
                }
                return {name, value: +(value * 100).toFixed(2)};
            })
            .sort((a, b) => b.value - a.value);

        // Build ECharts rich-text image styles for type mode (one key per asset type)
        const richStyles: Record<string, any> = {};
        if (mode === 'type') {
            for (const {name} of chartData) {
                const safeKey = `img_${name.replace(/[^A-Z_]/g, '')}`;
                richStyles[safeKey] = {
                    backgroundColor: {image: getAssetTypeIconUrl(name)},
                    width: 16,
                    height: 16,
                    align: 'center',
                };
            }
        }

        // Responsive: narrow containers → legend below the pie
        const containerWidth = chartContainer.getBoundingClientRect().width;
        const isNarrow = containerWidth < 400;
        const legendBelow = legendPosition === 'bottom' || isNarrow;

        // Legend — type mode adds rich-text icon in front of each label
        const legendBaseTextStyle: any = {color: isDark ? '#94a3b8' : '#64748b', fontSize: 11};
        const legendTextStyle = mode === 'type' ? {...legendBaseTextStyle, rich: richStyles} : legendBaseTextStyle;

        const legendTypeExtras =
            mode === 'type'
                ? {
                      formatter: (name: string) => {
                          const safeKey = `img_${name.replace(/[^A-Z_]/g, '')}`;
                          return `{${safeKey}|} ${tr(`assets.types.${name}`) || name}`;
                      },
                  }
                : {};

        const legendConfig: any = legendBelow
            ? {
                  ...legendTypeExtras,
                  type: 'plain',
                  orient: 'horizontal',
                  bottom: 0,
                  left: 'center',
                  width: '95%',
                  textStyle: legendTextStyle,
              }
            : {
                  ...legendTypeExtras,
                  type: 'scroll',
                  orient: 'vertical',
                  right: 10,
                  top: 20,
                  bottom: 20,
                  textStyle: legendTextStyle,
                  pageTextStyle: {color: isDark ? '#94a3b8' : '#64748b'},
                  pageIconColor: isDark ? '#94a3b8' : '#64748b',
                  pageIconInactiveColor: isDark ? '#334155' : '#cbd5e1',
              };

        const pieCenter = legendBelow ? ['50%', '40%'] : ['35%', '50%'];
        const pieRadius = legendBelow ? ['25%', '55%'] : ['35%', '70%'];

        // Inner label — sector: emoji only; type: PNG icon via rich text.
        // Both modes wrap in semi-transparent white circle badge for contrast.
        const labelConfig: any =
            mode === 'sector'
                ? {
                      show: true,
                      position: 'inner',
                      // Extract only the leading emoji (first token before the space)
                      formatter: (params: any) => (params.name as string).split(' ')[0],
                      fontSize: 14,
                      backgroundColor: 'rgba(255, 255, 255, 0.75)',
                      borderRadius: 20,
                      padding: [4, 4],
                  }
                : {
                      show: true,
                      position: 'inner',
                      formatter: (params: any) => `{img_${(params.name as string).replace(/[^A-Z_]/g, '')}|}`,
                      rich: richStyles,
                      backgroundColor: 'rgba(255, 255, 255, 0.75)',
                      borderRadius: 20,
                      padding: [4, 4],
                  };

        // Tooltip — icon/emoji + full translated name + percentage
        const tooltipFormatter = (params: any) => {
            if (mode === 'type') {
                const translated = tr(`assets.types.${params.name}`) || params.name;
                const iconUrl = getAssetTypeIconUrl(params.name);
                return `<img src="${iconUrl}" style="width:14px;height:14px;vertical-align:middle;margin-right:5px;">${translated}: ${params.value}%`;
            }
            // Sector: name already contains the leading emoji
            return `${params.name}: ${params.value}%`;
        };

        const option: echarts.EChartsOption = {
            color: palette,
            tooltip: {
                trigger: 'item',
                formatter: tooltipFormatter,
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
                    label: labelConfig,
                    labelLayout: {hideOverlap: true},
                    emphasis: {
                        // Tooltip is sufficient on hover — hide inner label instead of replacing it with text
                        label: {show: false},
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
