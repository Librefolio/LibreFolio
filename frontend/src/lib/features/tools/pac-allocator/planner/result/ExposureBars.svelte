<!--
  R9.8: one exposure dimension (Asset type, sector) as horizontal bars: for each category the target
  and the weight after the plan, side by side. The numbers on the bars and in the box are the
  backend's exact weights, formatted; the lengths are drawing only. Weights are public: nothing to mask.
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {t} from '$lib/i18n';
    import {attachChartReady} from '$lib/utils/chartReady';
    import {createResizeWatcher} from '$lib/utils/core/resizeWatcher';
    import {CHART_SET_OPTION_OPTS} from '$lib/components/charts/echartsAnimationConfig';
    import {buildGridColors, buildTooltipTheme, scheduleFirstRenderStabilityFix} from '$lib/components/charts/echartsTooltipHelpers';
    import {formatExactPercent} from '../format';
    import {exposureTooltipHtml, exposureTooltipText} from './exposureTooltip';
    import {chartPercent, type WeightRow} from './model';

    interface Props {
        rows: readonly WeightRow[];
        /** The dimension, for the chart's name and test hook. */
        dimension: string;
    }

    let {rows, dimension}: Props = $props();

    /** Target in grey and after in green, as the bars of the allocation table. */
    const COLOURS = {
        light: {target: '#9ca3af', final: '#1a4031'},
        dark: {target: '#6b7280', final: '#00d681'},
    };

    let dark = $state(false);
    let container = $state<HTMLDivElement>();
    let chart: echarts.ECharts | null = null;
    const resizeWatcher = createResizeWatcher(() => chart?.resize());
    let renderGeneration = 0;

    const text = $derived(exposureTooltipText($t));
    /** Two bars and their gap per category, plus the legend. */
    const height = $derived(Math.max(120, rows.length * 44 + 40));

    onMount(() => {
        const readTheme = () => {
            dark = document.documentElement.classList.contains('dark');
        };
        readTheme();
        const observer = new MutationObserver(readTheme);
        observer.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
        return () => {
            renderGeneration += 1;
            observer.disconnect();
            resizeWatcher.disconnect();
            chart?.dispose();
            chart = null;
        };
    });

    $effect(() => {
        const element = container;
        const next = option();
        void height;
        if (!element) return;
        const generation = ++renderGeneration;
        tick().then(() => {
            if (generation !== renderGeneration) return;
            const fresh = chart === null;
            if (!chart) {
                chart = echarts.init(element, undefined, {renderer: 'canvas'});
                attachChartReady(chart, element, `pac-planner-exposure-bars-${dimension}`);
            }
            chart.setOption(next, CHART_SET_OPTION_OPTS);
            chart.resize();
            if (fresh) scheduleFirstRenderStabilityFix(chart, element);
            resizeWatcher.observe(element);
        });
    });

    function finalText(row: WeightRow): string {
        return row.final.kind === 'available' ? formatExactPercent(row.final.value) : '—';
    }

    function option(): echarts.EChartsOption {
        const grid = buildGridColors(dark);
        const theme = buildTooltipTheme(dark);
        const colours = dark ? COLOURS.dark : COLOURS.light;
        const shown = [...rows];
        const tooltipText = text;
        const label = (format: (row: WeightRow) => string) => ({
            show: true,
            position: 'right' as const,
            color: grid.textColor,
            fontSize: 10,
            formatter: (params: unknown) => {
                const row = shown[(params as {dataIndex?: number}).dataIndex ?? -1];
                return row ? format(row) : '';
            },
        });
        return {
            grid: {left: 8, right: 64, top: 28, bottom: 4, containLabel: true},
            legend: {top: 0, left: 0, itemWidth: 10, itemHeight: 10, textStyle: {color: grid.textColor, fontSize: 11}, data: [tooltipText.target, tooltipText.final]},
            tooltip: {
                trigger: 'axis',
                axisPointer: {type: 'shadow'},
                confine: true,
                backgroundColor: theme.bg,
                borderColor: theme.border,
                textStyle: {color: theme.textColor, fontSize: 12},
                formatter: (params: unknown) => {
                    const first = Array.isArray(params) ? params[0] : params;
                    const row = shown[(first as {dataIndex?: number} | undefined)?.dataIndex ?? -1];
                    return row ? exposureTooltipHtml(row, tooltipText, theme, colours) : '';
                },
            },
            xAxis: {type: 'value', min: 0, show: false},
            yAxis: {
                type: 'category',
                inverse: true,
                data: shown.map((row) => row.label),
                axisTick: {show: false},
                axisLine: {lineStyle: {color: grid.gridColor}},
                axisLabel: {color: grid.textColor, fontSize: 11, width: 160, overflow: 'truncate'},
            },
            series: [
                {
                    name: tooltipText.target,
                    type: 'bar',
                    barMaxWidth: 14,
                    barGap: '25%',
                    itemStyle: {color: colours.target, borderRadius: [0, 3, 3, 0]},
                    label: label((row) => formatExactPercent(row.target)),
                    data: shown.map((row) => chartPercent(row.target) ?? '-'),
                },
                {
                    name: tooltipText.final,
                    type: 'bar',
                    barMaxWidth: 14,
                    itemStyle: {color: colours.final, borderRadius: [0, 3, 3, 0]},
                    label: label(finalText),
                    data: shown.map((row) => chartPercent(row.final) ?? '-'),
                },
            ],
        };
    }
</script>

<div bind:this={container} class="w-full" style:height="{height}px" data-testid="pac-planner-exposures-bars" data-dimension={dimension} aria-hidden="true"></div>
