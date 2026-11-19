<!--
  ProfileHistoryChart — the big chart of «Storia del dato» (plan 68, E6b; the mock's shot 13): the steps of one voice
  from its first day, a point where each step starts in its source's colour (`profileHistory`). It publishes the number
  of points it draws (`data-point-count`) and how many were written by hand (`data-hand-count`).

  The colours are roles, read on the chart's own element at each draw: the line is the price line's, a hand-written
  point the info role, the axes the price axes' neutrals. A theme switch, or the Designer Lab, draws it again.

  Pattern: Svelte 5 Runes, ECharts, colour roles only.
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {CHART_INIT_THEME} from '$lib/components/charts/chartFont';
    import {chartInitOptions} from '$lib/components/charts/chartPixelRatio';
    import {CHART_ANIMATION_CONFIG, CHART_SET_OPTION_OPTS} from '$lib/components/charts/echartsAnimationConfig';
    import {buildTooltipTheme} from '$lib/components/charts/echartsTooltipHelpers';
    import {createResizeWatcher} from '$lib/utils/core/resizeWatcher';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {PRICE_SERIES, chartNeutrals} from '$lib/theme/chartTheme';
    import {chartRoles} from '$lib/theme/roleColors';
    import {themed} from '$lib/theme/themePair';
    import {isDarkTheme, onChartColorsChange, onThemeClassChange} from '$lib/theme/themeMode';
    import {buildHistoryOption, type HistoryPoint} from './profileHistory';

    interface Props {
        points: HistoryPoint[];
        /** A point's stored value as the profile writes it (the tooltip). */
        formatValue: (stored: unknown) => string;
        /** A day as the profile writes it (the tooltip). */
        formatDay: (iso: string) => string;
        /** A point's source by name (the tooltip). */
        sourceName: (code: string) => string;
        height?: string;
        testId?: string;
    }

    let {points, formatValue, formatDay, sourceName, height = '220px', testId = 'profile-history-chart'}: Props = $props();

    let container: HTMLDivElement | undefined = $state(undefined);
    let chart: echarts.ECharts | null = null;
    let dark = $state(false);
    let colorsRevision = $state(0);
    const resizeWatcher = createResizeWatcher(() => chart?.resize());

    onMount(() => {
        dark = isDarkTheme();
        const darkObserver = onThemeClassChange(() => (dark = isDarkTheme()));
        const chartColors = onChartColorsChange(() => (colorsRevision += 1));
        return () => {
            darkObserver.disconnect();
            chartColors.disconnect();
            resizeWatcher.disconnect();
            chart?.dispose();
        };
    });

    $effect(() => {
        void points;
        void dark;
        void colorsRevision;
        void tick().then(render);
    });

    function render(): void {
        if (!container) return;
        if (!chart) chart = echarts.init(container, CHART_INIT_THEME, chartInitOptions(container));
        resizeWatcher.observe(container);
        const roles = chartRoles(dark, container);
        const axes = chartNeutrals(dark, container).priceAxis;
        const option = buildHistoryOption(points, {line: themed(PRICE_SERIES.line, dark), hand: roles.color('--lf-info'), axisLine: axes.line, axisLabel: axes.label, gridLine: axes.gridLine, formatDay});
        const box = buildTooltipTheme(dark, container);
        chart.setOption(
            {
                ...CHART_ANIMATION_CONFIG,
                ...option,
                tooltip: {
                    trigger: 'item',
                    confine: true,
                    backgroundColor: box.bg,
                    borderColor: box.border,
                    textStyle: {color: box.textColor},
                    formatter: (params: {dataIndex?: number}) => {
                        const point = points[params.dataIndex ?? -1];
                        if (!point || point.value === null) return '';
                        return `<div style="font-weight:600">${escapeHtml(formatValue(point.stored))}</div><div>${escapeHtml(formatDay(point.date))} · ${escapeHtml(sourceName(point.source))}</div>`;
                    },
                },
            },
            CHART_SET_OPTION_OPTS,
        );
    }
</script>

<div bind:this={container} class="w-full" style:height data-testid={testId} data-point-count={points.filter((point) => point.marked && point.value !== null).length} data-hand-count={points.filter((point) => point.marked && point.byHand).length}></div>
