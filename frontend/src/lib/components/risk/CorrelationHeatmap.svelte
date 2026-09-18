<script lang="ts">
    /**
     * CorrelationHeatmap — the matrix, made readable.
     *
     * The chart this replaces drew a full N×N grid whose loudest diagonal said
     * that each asset correlates with itself, truncated every label twice (once
     * by a fixed 110px grid, once by an `overflow: 'truncate'` at 100px), and
     * opened a tooltip that reported a number without ever naming the two
     * assets it belonged to. The one question a correlation matrix exists to
     * answer — *which of these two things are the same bet?* — was the one it
     * refused to answer.
     *
     * Four changes, in the order they matter:
     *
     * 1. **Names in the tooltip.** Both of them, plus a plain-language reading
     *    of the coefficient. `labels` was already in scope; nobody had written
     *    it in.
     * 2. **Half the matrix.** The diagonal is a tautology and the upper
     *    triangle is a mirror; a 10-asset matrix drops from 100 cells to 45
     *    with no fact lost.
     * 3. **Labels that survive.** Truncated once, deliberately, by
     *    `truncateName`, with the grid margins *computed* from the truncation
     *    rather than fixed and hoped for.
     * 4. **Order by similarity.** Assets that move together become adjacent, so
     *    blocks of redundancy appear as squares instead of scattered dots.
     *
     * The arithmetic lives in `correlationHelpers.ts` and is unit-tested there;
     * this file is the drawing.
     */
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {attachChartReady} from '$lib/utils/chartReady';
    import {CHART_ANIMATION_CONFIG, CHART_SET_OPTION_OPTS} from '$lib/components/charts/echartsAnimationConfig';
    import {scheduleFirstRenderStabilityFix, tooltipPositionAboveFinger} from '$lib/components/charts/echartsTooltipHelpers';
    import {createResizeWatcher} from '$lib/utils/core/resizeWatcher';
    import {truncateName} from '$lib/utils/text';

    import {_ as t} from '$lib/i18n';
    import type {RiskCorrelationOutput} from '$lib/risk/riskTypes';
    import CorrelationPairsList from './CorrelationPairsList.svelte';
    import {buildLookup, clusterOrder, correlationBand, lowerTrianglePoints, NEAR_IDENTICAL, PAIR_LIST_THRESHOLD} from './correlationHelpers';

    interface Props {
        output: RiskCorrelationOutput;
        assetLabels?: ReadonlyMap<number, string>;
        height?: string;
        /** `similarity` groups assets that move together; `original` keeps the payload order. */
        initialOrdering?: 'similarity' | 'original';
    }

    let {output, assetLabels = new Map(), height = '420px', initialOrdering = 'similarity'}: Props = $props();
    /** `null` means "the caller's choice still stands"; any click pins it locally. */
    let orderingOverride = $state<'similarity' | 'original' | null>(null);
    let ordering = $derived(orderingOverride ?? initialOrdering);
    let container: HTMLDivElement | undefined = $state(undefined);
    let chart: echarts.ECharts | null = null;
    const resizeWatcher = createResizeWatcher(() => chart?.resize());

    /** Long enough to tell two ETFs apart, short enough not to eat the plot. */
    const LABEL_MAX_CHARS = 18;
    /** Approximate advance width of the 12px axis font, in pixels per character. */
    const CHAR_PX = 6.6;
    const X_LABEL_ROTATION = 45;

    let lookup = $derived(buildLookup(output.cells));
    let order = $derived(ordering === 'similarity' ? clusterOrder(output.asset_ids, lookup) : [...output.asset_ids]);

    function nameOf(assetId: number): string {
        return assetLabels.get(assetId) ?? `#${assetId}`;
    }

    /**
     * Past this size the matrix stops being the answer and becomes the
     * context: the in-cell numbers are already gone, and hunting for the
     * darkest of four hundred squares is not reading. The list goes first, the
     * picture stays underneath — demoted, not removed.
     */
    let pairsLead = $derived(order.length > PAIR_LIST_THRESHOLD);

    onMount(() => {
        const darkObserver = new MutationObserver(() => render());
        darkObserver.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
        return () => {
            darkObserver.disconnect();
            resizeWatcher.disconnect();
            chart?.dispose();
        };
    });

    $effect(() => {
        void output;
        void assetLabels;
        void ordering;
        if (container) void tick().then(render);
    });

    /**
     * Reserve exactly the room the labels need.
     *
     * The old grid hard-coded `left: 110, bottom: 95` and then told ECharts to
     * truncate at 100px anyway, so a name was cut even when there was space for
     * it. Here the truncation is the single source of truth and the margins are
     * derived from it: horizontally for the y-axis, and by `width · sin(45°)`
     * for the rotated x-axis, which is the vertical footprint of a diagonal
     * label.
     */
    function margins(labels: readonly string[]): {left: number; bottom: number} {
        const longest = labels.reduce((max, label) => Math.max(max, label.length), 0);
        const widthPx = longest * CHAR_PX;
        const radians = (X_LABEL_ROTATION * Math.PI) / 180;
        return {
            left: Math.min(160, Math.ceil(widthPx) + 18),
            bottom: Math.min(150, Math.ceil(widthPx * Math.sin(radians)) + 52),
        };
    }

    /** Asset names are user data and the tooltip is raw HTML. */
    function escapeHtml(value: string): string {
        return value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
    }

    function render(): void {
        if (!container || output.asset_ids.length === 0) return;
        if (!chart) {
            chart = echarts.init(container);
            attachChartReady(chart, container, 'correlation-heatmap');
            scheduleFirstRenderStabilityFix(chart, container);
        }
        resizeWatcher.observe(container);

        const dark = document.documentElement.classList.contains('dark');
        const labels = order.map((assetId) => truncateName(nameOf(assetId), LABEL_MAX_CHARS));
        const data = lowerTrianglePoints(order, lookup);
        const {left, bottom} = margins(labels);
        const axisColor = dark ? '#cbd5e1' : '#475569';

        chart.setOption(
            {
                ...CHART_ANIMATION_CONFIG,
                grid: {left, right: 40, top: 30, bottom},
                xAxis: {
                    type: 'category',
                    data: labels,
                    axisLabel: {rotate: X_LABEL_ROTATION, color: axisColor},
                    splitArea: {show: true},
                },
                yAxis: {
                    type: 'category',
                    data: labels,
                    axisLabel: {color: axisColor},
                    splitArea: {show: true},
                },
                visualMap: {
                    min: -1,
                    max: 1,
                    calculable: false,
                    orient: 'horizontal',
                    left: 'center',
                    bottom: 6,
                    text: ['+1', '-1'],
                    textStyle: {color: axisColor},
                    inRange: {color: ['#b91c1c', '#f8fafc', '#1d4ed8']},
                },
                tooltip: {
                    position: tooltipPositionAboveFinger,
                    confine: true,
                    formatter: (params: {data?: (typeof data)[number]}) => {
                        const item = params.data;
                        if (!item) return '';
                        const value = item.value[2];
                        const band = correlationBand(value);
                        const heading = `<div style="font-weight:600">${escapeHtml(nameOf(item.rowAssetId))}</div><div style="font-weight:600">${escapeHtml(nameOf(item.columnAssetId))}</div>`;
                        const reading =
                            typeof value === 'number' && band
                                ? `<div style="margin-top:4px">ρ = ${value.toFixed(3)} · ${$t(`risk.assetSet.band.${band}`)}${value >= NEAR_IDENTICAL ? ` · ${$t('risk.assetSet.nearIdentical')}` : ''}</div>`
                                : `<div style="margin-top:4px">${$t(`risk.valueStatus.${item.status}`)}</div>`;
                        const metadata = `<div style="opacity:0.75;margin-top:2px">${$t('risk.metadata.observations')}: ${item.observations} · ${$t('risk.metadata.coverage')}: ${(item.coverage * 100).toFixed(1)}%</div>`;
                        return `${heading}${reading}${metadata}`;
                    },
                },
                series: [
                    {
                        name: $t('risk.analytics.correlation.name'),
                        type: 'heatmap',
                        data,
                        label: {
                            show: order.length <= 12,
                            formatter: (params: {data?: (typeof data)[number]}) => {
                                const value = params.data?.value?.[2];
                                return typeof value === 'number' ? value.toFixed(2) : '—';
                            },
                            color: dark ? '#e2e8f0' : '#0f172a',
                        },
                        emphasis: {itemStyle: {shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.25)'}},
                    },
                ],
            },
            CHART_SET_OPTION_OPTS,
        );
    }
</script>

<div class="space-y-3">
    <div class="flex items-center justify-end">
        <div class="inline-flex overflow-hidden rounded-lg border border-gray-200 dark:border-slate-600" role="group" aria-label={$t('risk.assetSet.ordering.label')}>
            {#each ['similarity', 'original'] as const as mode}
                <button
                    type="button"
                    class="px-2.5 py-1 text-xs font-medium transition-colors {ordering === mode ? 'bg-libre-green text-white' : 'bg-white text-gray-600 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-300 dark:hover:bg-slate-700'}"
                    aria-pressed={ordering === mode}
                    onclick={() => (orderingOverride = mode)}
                    data-testid="risk-correlation-ordering-{mode}"
                >
                    {$t(`risk.assetSet.ordering.${mode}`)}
                </button>
            {/each}
        </div>
    </div>

    <div class="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]" data-testid="risk-correlation-layout" data-pairs-lead={pairsLead}>
        <!-- `data-asset-order` publishes the very array the chart is built from, so a
             test can assert the reordering itself instead of the button's pressed state.
             Without it the only observable effect of the toggle is inside a canvas. -->
        <div class="w-full overflow-x-auto {pairsLead ? 'lg:order-2' : ''}" data-testid="risk-correlation-heatmap" data-asset-order={order.join(',')}>
            <div bind:this={container} class="min-w-[520px] w-full" style:height></div>
        </div>
        <div class={pairsLead ? 'lg:order-1' : ''}>
            <CorrelationPairsList {output} {assetLabels} limit={pairsLead ? 8 : 5} />
        </div>
    </div>
</div>
