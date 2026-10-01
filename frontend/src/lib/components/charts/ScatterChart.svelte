<script lang="ts">
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    /**
     * ScatterChart — risk against return, one dot per thing.
     *
     * This exists because `LineChart` cannot draw it, and the reason is worth
     * stating once so nobody spends an afternoon rediscovering it: `LineChart`
     * pins every series to `{type: 'category', data: dates}` and offers no prop
     * to change that. It has an internal scatter mode, but it feeds it
     * `dates.indexOf(d.date)` — a date turned into a category index. A
     * risk/return plot has no dates at all: both coordinates are continuous
     * numbers. Routed through `LineChart` the result is not a broken chart, it
     * is a *plausible* one — diamonds sitting on a time axis, correct-looking
     * and wrong.
     *
     * So both axes here are `type: 'value'`, and there is a unit test that says
     * so, because that single word is the whole reason for the file.
     *
     * Following the house pattern (`CorrelationHeatmap`), the arithmetic lives
     * in `scatterChartHelpers.ts` and is unit-tested there; this file is the
     * drawing. Its own spec, `ScatterChart.test.ts`, pins only the wiring the
     * builder cannot see: the selection reaching it, and a click coming back as
     * the id of the point clicked.
     *
     * Three things the container publishes deliberately:
     *
     * - `data-point-count` / `data-dropped-count`: what actually got plotted.
     *   A dot lost to a `NaN` is invisible inside a canvas, and a test that
     *   cannot see it cannot fail on it.
     * - `data-selected-id`: the selection the chart was handed, `""` for none.
     *   A highlight inside a canvas is just as invisible.
     * - `data-chart-ready`, via `attachChartReady`: without it an E2E has no
     *   signal to wait on and goes back to sleeping for a fixed number of
     *   milliseconds, which is how a suite becomes slow and flaky at once.
     */
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';

    import {attachChartReady} from '$lib/utils/chartReady';
    import {createResizeWatcher} from '$lib/utils/core/resizeWatcher';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import {CHART_ANIMATION_CONFIG, CHART_SET_OPTION_OPTS} from './echartsAnimationConfig';
    import {scheduleFirstRenderStabilityFix, tooltipPositionAboveFinger} from './echartsTooltipHelpers';
    import {buildScatterOption, type RiskReturnPoint} from './scatterChartHelpers';

    interface Props {
        points: readonly RiskReturnPoint[];
        /**
         * Axis titles and the line's name, already translated. The component
         * takes no i18n dependency of its own: the caller owns the catalogue
         * and knows which surface the chart is standing on.
         */
        labels: {volatility: string; return: string; capitalMarketLine: string};
        /** As a fraction (0.02 = 2%). Anchors the Capital Market Line at x = 0. */
        riskFreeRate?: number;
        height?: string;
        /** Rendered as `data-testid`; also namespaces the chart-ready signal. */
        testId?: string;
        /** Shown when nothing is placeable. Supplied already translated; defaults to the house em-dash. */
        emptyLabel?: string;
        /**
         * Id of the point to draw as selected, or `null` for none. The caller owns the
         * selection; the chart only shows it. The Dashboard passes nothing.
         */
        selectedId?: string | null;
        /** Called with the id of the point clicked. A click on the line or on empty space calls nothing. */
        onpointclick?: (id: string) => void;
    }

    let {points, labels, riskFreeRate = 0, height = '420px', testId = 'risk-return-scatter', emptyLabel = '—', selectedId = null, onpointclick}: Props = $props();

    let container: HTMLDivElement | undefined = $state(undefined);
    let chart: echarts.ECharts | null = null;
    let dark = $state(false);
    const resizeWatcher = createResizeWatcher(() => chart?.resize());

    let built = $derived(buildScatterOption({points, riskFreeRate, dark, labels, selectedId}));

    onMount(() => {
        dark = document.documentElement.classList.contains('dark');
        const darkObserver = new MutationObserver(() => {
            dark = document.documentElement.classList.contains('dark');
        });
        darkObserver.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
        return () => {
            darkObserver.disconnect();
            resizeWatcher.disconnect();
            chart?.dispose();
        };
    });

    $effect(() => {
        void built;
        void tick().then(() => {
            // Going empty removes the canvas host from the DOM, leaving the ECharts
            // instance bound to a detached node. Refilling then draws into nothing
            // — a blank chart with no error anywhere. Dispose instead, and let the
            // next non-empty render build a fresh instance.
            if (built.isEmpty || !container) {
                chart?.dispose();
                chart = null;
                return;
            }
            render();
        });
    });

    /** Both coordinates are fractions, so both read as percentages. */
    function axisPercent(value: number): string {
        return formatPercent(value, {scale: 100, signed: false, digits: 1});
    }

    function render(): void {
        if (!container) return;
        if (!chart) {
            chart = echarts.init(container);
            attachChartReady(chart, container, testId);
            scheduleFirstRenderStabilityFix(chart, container);
            // Once per instance: `render()` runs on every option change, and a listener
            // added each time would report one click as many. The line's datum is a bare
            // pair and carries no id, so only a dot answers.
            chart.on('click', (params) => {
                const id = (params?.data as {id?: unknown} | undefined)?.id;
                if (typeof id === 'string') onpointclick?.(id);
            });
        }
        resizeWatcher.observe(container);

        const {xAxis, yAxis, ...rest} = built.option;

        chart.setOption(
            {
                ...CHART_ANIMATION_CONFIG,
                ...rest,
                // The helper leaves the numbers as fractions; turning 0.1 into "10.0%"
                // is presentation, so it is applied here rather than baked into the
                // option builder that the unit tests assert on.
                xAxis: {...xAxis, axisLabel: {...xAxis.axisLabel, formatter: axisPercent}},
                yAxis: {...yAxis, axisLabel: {...yAxis.axisLabel, formatter: axisPercent}},
                tooltip: {
                    position: tooltipPositionAboveFinger,
                    confine: true,
                    formatter: (params: {data?: {name?: string; value?: [number, number]}}) => {
                        const item = params.data;
                        if (!item?.value) return '';
                        const [volatility, annualReturn] = item.value;
                        const nameHtml = escapeHtml(String(item.name ?? ''));
                        return [`<div style="font-weight:600">${nameHtml}</div>`, `<div style="margin-top:4px">${labels.volatility}: ${axisPercent(volatility)}</div>`, `<div>${labels.return}: ${formatPercent(annualReturn, {scale: 100, digits: 1})}</div>`].join('');
                    },
                },
            },
            CHART_SET_OPTION_OPTS,
        );
    }
</script>

<div class="w-full" data-testid={testId} data-point-count={points.length - built.droppedCount} data-dropped-count={built.droppedCount} data-selected-id={selectedId ?? ''}>
    {#if built.isEmpty}
        <!-- An empty canvas is indistinguishable from a broken one, so the empty
             case says so in words rather than rendering nothing. -->
        <div class="flex items-center justify-center rounded-lg border border-dashed border-gray-300 text-sm text-gray-500 dark:border-slate-600 dark:text-gray-400" style:height data-testid="{testId}-empty">
            {emptyLabel}
        </div>
    {:else}
        <div bind:this={container} class="w-full" style:height></div>
    {/if}
</div>
