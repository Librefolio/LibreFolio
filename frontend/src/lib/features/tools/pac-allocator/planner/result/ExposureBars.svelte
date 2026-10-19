<!--
  R9.8: one exposure dimension (Asset type, sector) as horizontal bars: for each category the target
  and the weight after the plan, side by side. The numbers on the bars and in the box are the
  backend's exact weights, formatted; the lengths are drawing only. Weights are public: nothing to mask.
  TD-1: the weight after the plan in its category's colour, as on the dashboard (`./exposureBarColours`);
  the target in the designer's neutral grey (`PAC_EXPOSURE_COLORS.ideal`, round 3, §1.7).
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {CHART_INIT_THEME} from '$lib/components/charts/chartFont';
    import {t} from '$lib/i18n';
    import {attachChartReady} from '$lib/utils/chartReady';
    import {createResizeWatcher} from '$lib/utils/core/resizeWatcher';
    import {CHART_SET_OPTION_OPTS} from '$lib/components/charts/echartsAnimationConfig';
    import {buildGridColors, buildTooltipTheme, scheduleFirstRenderStabilityFix} from '$lib/components/charts/echartsTooltipHelpers';
    import {formatExactPercent} from '../format';
    import {exposureTooltipHtml, exposureTooltipText} from './exposureTooltip';
    import {chartPercent, type WeightRow} from './model';
    import {uiLocale} from '$lib/stores/app/uiLocale';
    import {shadePoles} from '$lib/theme/chartShades';
    import {chartNeutrals} from '$lib/theme/chartTheme';
    import {chartRoles} from '$lib/theme/roleColors';
    import {isDarkTheme, onChartColorsChange, onThemeClassChange} from '$lib/theme/themeMode';
    import {actualColours, idealColour} from './exposureBarColours';

    interface Props {
        rows: readonly WeightRow[];
        /** The dimension, for the chart's name and test hook. */
        dimension: string;
    }

    let {rows, dimension}: Props = $props();

    let dark = $state(false);
    /** Bumped by a Designer Lab edit of a category colour (C4): the next option is rebuilt whole. */
    let colorsVersion = $state(0);
    let container = $state<HTMLDivElement>();
    let chart: echarts.ECharts | null = null;
    const resizeWatcher = createResizeWatcher(() => chart?.resize());
    let renderGeneration = 0;

    const text = $derived(exposureTooltipText($t));
    /** Two bars and their gap per category, plus the legend. */
    const height = $derived(Math.max(120, rows.length * 44 + 40));

    onMount(() => {
        const readTheme = () => {
            dark = isDarkTheme();
        };
        readTheme();
        const observer = onThemeClassChange(readTheme);
        const colours = onChartColorsChange(() => {
            colorsVersion += 1;
        });
        return () => {
            renderGeneration += 1;
            observer.disconnect();
            colours.disconnect();
            resizeWatcher.disconnect();
            chart?.dispose();
            chart = null;
        };
    });

    $effect(() => {
        const element = container;
        const next = option();
        void height;
        // The figures on the bars are written in the interface locale: a language switch redraws them (M-18).
        void uiLocale();
        if (!element) return;
        const generation = ++renderGeneration;
        tick().then(() => {
            if (generation !== renderGeneration) return;
            const fresh = chart === null;
            if (!chart) {
                chart = echarts.init(element, CHART_INIT_THEME, {renderer: 'canvas'});
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
        void colorsVersion;
        // The roles of the chart's own element: a forced theme subtree, or the Lab's preview, has its own.
        const grid = buildGridColors(dark, container ?? null);
        const theme = buildTooltipTheme(dark, container ?? null);
        const neutrals = chartNeutrals(dark, container ?? null);
        const roles = chartRoles(dark, container ?? null);
        const ideal = idealColour(dark);
        const card = roles.color('--lf-surface-card');
        const shown = [...rows];
        const actual = actualColours(shown, dimension, dark, shadePoles(dark, card));
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
            legend: {
                top: 0,
                left: 0,
                itemWidth: 10,
                itemHeight: 10,
                textStyle: {color: grid.textColor, fontSize: 11},
                // The actual weight has a colour per row: its swatch is an outline in the text colour, on the card.
                data: [
                    {name: tooltipText.target, itemStyle: {color: ideal}},
                    {name: tooltipText.final, itemStyle: {color: card, borderColor: grid.textColor, borderWidth: 1}},
                ],
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: {type: 'shadow', shadowStyle: {color: neutrals.axisPointer.shadow}},
                confine: true,
                backgroundColor: theme.bg,
                borderColor: theme.border,
                textStyle: {color: theme.textColor, fontSize: 12},
                formatter: (params: unknown) => {
                    const first = Array.isArray(params) ? params[0] : params;
                    const index = (first as {dataIndex?: number} | undefined)?.dataIndex ?? -1;
                    const row = shown[index];
                    return row ? exposureTooltipHtml(row, tooltipText, theme, {target: ideal, final: actual[index]}) : '';
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
                    itemStyle: {color: ideal, borderRadius: [0, 3, 3, 0]},
                    label: label((row) => formatExactPercent(row.target)),
                    data: shown.map((row) => chartPercent(row.target) ?? '-'),
                },
                {
                    name: tooltipText.final,
                    type: 'bar',
                    barMaxWidth: 14,
                    itemStyle: {borderRadius: [0, 3, 3, 0]},
                    label: label(finalText),
                    data: shown.map((row, index) => ({value: chartPercent(row.final) ?? '-', itemStyle: {color: actual[index]}})),
                },
            ],
        };
    }
</script>

<div bind:this={container} class="w-full" style:height="{height}px" data-testid="pac-planner-exposures-bars" data-dimension={dimension} aria-hidden="true"></div>
