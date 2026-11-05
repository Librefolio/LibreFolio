<script lang="ts">
    /**
     * ReturnHistogramChart — the distribution of daily returns, drawn by ECharts.
     *
     * The decisions (the real bar edges on an axis of returns, the colour of each bar, the cut line, the hit area that gives an
     * empty bin its tooltip) are in `returnHistogramChartHelpers.ts`, pure and unit-tested; this file is the drawing and its life
     * cycle, copied from `ScatterChart`: the instance is made once and disposed with the element, redrawn when the option, the
     * language or the colours change, and publishes `data-chart-ready` (`attachChartReady`) because a canvas says nothing to a test.
     *
     * The component takes no i18n and no figure rule of its own: the axis, the cut's label and every line of the tooltip come in
     * already written, by the caller that owns the catalogue and the share rule.
     */
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';

    import {CHART_INIT_THEME} from '$lib/components/charts/chartFont';
    import {chartInitOptions} from '$lib/components/charts/chartPixelRatio';
    import {uiLocale} from '$lib/stores/app/uiLocale';
    import {isDarkTheme, onChartColorsChange, onThemeClassChange} from '$lib/theme/themeMode';
    import {attachChartReady} from '$lib/utils/chartReady';
    import {createResizeWatcher} from '$lib/utils/core/resizeWatcher';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';

    import {CHART_ANIMATION_CONFIG, CHART_SET_OPTION_OPTS} from './echartsAnimationConfig';
    import {buildTooltipTheme, scheduleFirstRenderStabilityFix, tooltipPositionAboveFinger} from './echartsTooltipHelpers';
    import {buildReturnHistogramOption, type HistogramBin} from './returnHistogramChartHelpers';

    interface Props {
        bins: readonly HistogramBin[];
        /** The VaR cut in percent units, or `null`. */
        cut: number | null;
        /** A position on the return axis, in percent units, written. */
        formatAxis: (percent: number) => string;
        /** The label of the cut line, written. */
        cutLabel: string;
        /** The lines of one bar's tooltip, written; the first is the heading. */
        tooltipLines: (bin: HistogramBin, index: number) => string[];
        height?: string;
        testId?: string;
    }

    let {bins, cut, formatAxis, cutLabel, tooltipLines, height = '140px', testId = 'risk-l1-histogram-chart'}: Props = $props();

    let container: HTMLDivElement | undefined = $state(undefined);
    let chart: echarts.ECharts | null = null;
    let dark = $state(false);
    const resizeWatcher = createResizeWatcher(() => chart?.resize());

    /** Bumped by the Designer Lab's colour edits: the option is rebuilt and its roles read again. */
    let chartColorsRevision = $state(0);
    let built = $derived.by(() => {
        void chartColorsRevision;
        return buildReturnHistogramOption({bins, cut, dark, scope: container ?? null, formatAxis, cutLabel});
    });

    onMount(() => {
        dark = isDarkTheme();
        const darkObserver = onThemeClassChange(() => {
            dark = isDarkTheme();
        });
        const chartColors = onChartColorsChange(() => {
            chartColorsRevision += 1;
        });
        return () => {
            darkObserver.disconnect();
            chartColors.disconnect();
            resizeWatcher.disconnect();
            chart?.dispose();
        };
    });

    $effect(() => {
        void built;
        // The axis and the tooltip are written in the interface language: a switch redraws them.
        void uiLocale();
        void tick().then(() => {
            // Going empty removes the canvas host and would leave the instance bound to a detached node.
            if (built.isEmpty || !container) {
                chart?.dispose();
                chart = null;
                return;
            }
            render();
        });
    });

    function render(): void {
        if (!container) return;
        if (!chart) {
            chart = echarts.init(container, CHART_INIT_THEME, chartInitOptions(container));
            attachChartReady(chart, container, testId);
            scheduleFirstRenderStabilityFix(chart, container);
        }
        resizeWatcher.observe(container);

        const box = buildTooltipTheme(dark, container);
        chart.setOption(
            {
                ...CHART_ANIMATION_CONFIG,
                ...built.option,
                tooltip: {
                    trigger: 'item',
                    position: tooltipPositionAboveFinger,
                    confine: true,
                    backgroundColor: box.bg,
                    borderColor: box.border,
                    textStyle: {color: box.textColor},
                    formatter: (params: {data?: {binIndex?: number}}) => {
                        const index = params.data?.binIndex;
                        const bin = index === undefined ? undefined : bins[index];
                        if (index === undefined || !bin) return '';
                        const [heading, ...rest] = tooltipLines(bin, index);
                        // Written text, escaped as every tooltip here: a name or a figure never reaches the box as markup.
                        return [`<div style="font-weight:600">${escapeHtml(heading ?? '')}</div>`, ...rest.map((line) => `<div style="color:${box.mutedColor}">${escapeHtml(line)}</div>`)].join('');
                    },
                },
            },
            CHART_SET_OPTION_OPTS,
        );
    }
</script>

<div bind:this={container} class="w-full" style:height data-testid={testId}></div>
