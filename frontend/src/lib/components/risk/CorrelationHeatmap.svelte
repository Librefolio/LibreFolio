<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';

    import {_ as t} from '$lib/i18n';
    import type {RiskCorrelationOutput} from '$lib/risk/riskTypes';

    interface Props {
        output: RiskCorrelationOutput;
        assetLabels?: ReadonlyMap<number, string>;
        height?: string;
    }

    let {output, assetLabels = new Map(), height = '420px'}: Props = $props();
    let container: HTMLDivElement | undefined = $state(undefined);
    let chart: echarts.ECharts | null = null;
    let resizeObserver: ResizeObserver | null = null;

    let labels = $derived(output.asset_ids.map((assetId) => assetLabels.get(assetId) ?? `#${assetId}`));

    onMount(() => {
        const darkObserver = new MutationObserver(() => render());
        darkObserver.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
        return () => {
            darkObserver.disconnect();
            resizeObserver?.disconnect();
            chart?.dispose();
        };
    });

    $effect(() => {
        void output;
        void assetLabels;
        if (container) void tick().then(render);
    });

    function render(): void {
        if (!container || output.asset_ids.length === 0) return;
        if (!chart) {
            chart = echarts.init(container);
            resizeObserver = new ResizeObserver(() => chart?.resize());
            resizeObserver.observe(container);
        }

        const dark = document.documentElement.classList.contains('dark');
        const indexByAsset = new Map(output.asset_ids.map((assetId, index) => [assetId, index]));
        const data = (output.cells ?? [])
            .map((cell) => {
                const row = indexByAsset.get(cell.row_asset_id);
                const column = indexByAsset.get(cell.column_asset_id);
                if (row === undefined || column === undefined) return null;
                return {
                    value: [column, row, cell.status === 'ok' ? cell.value : null],
                    observations: cell.observations,
                    coverage: cell.coverage,
                    status: cell.status,
                };
            })
            .filter((item): item is NonNullable<typeof item> => item !== null);

        chart.setOption(
            {
                animation: false,
                grid: {left: 110, right: 40, top: 30, bottom: 95},
                xAxis: {
                    type: 'category',
                    data: labels,
                    axisLabel: {rotate: labels.length > 5 ? 35 : 0, color: dark ? '#cbd5e1' : '#475569', overflow: 'truncate', width: 100},
                    splitArea: {show: true},
                },
                yAxis: {
                    type: 'category',
                    data: labels,
                    axisLabel: {color: dark ? '#cbd5e1' : '#475569', overflow: 'truncate', width: 95},
                    splitArea: {show: true},
                },
                visualMap: {
                    min: -1,
                    max: 1,
                    calculable: false,
                    orient: 'horizontal',
                    left: 'center',
                    bottom: 10,
                    text: ['+1', '-1'],
                    textStyle: {color: dark ? '#cbd5e1' : '#475569'},
                    inRange: {color: ['#b91c1c', '#f8fafc', '#1d4ed8']},
                },
                tooltip: {
                    position: 'top',
                    formatter: (params: {data?: {value?: [number, number, number | null]; observations?: number; coverage?: number; status?: string}}) => {
                        const item = params.data;
                        const value = item?.value?.[2];
                        const status = item?.status ?? 'undefined';
                        const valueLabel = typeof value === 'number' ? value.toFixed(3) : $t(`risk.valueStatus.${status}`);
                        return `${valueLabel}<br/>${$t('risk.metadata.observations')}: ${item?.observations ?? 0}<br/>${$t('risk.metadata.coverage')}: ${(((item?.coverage ?? 0) as number) * 100).toFixed(1)}%`;
                    },
                },
                series: [
                    {
                        name: $t('risk.analytics.correlation.name'),
                        type: 'heatmap',
                        data,
                        label: {
                            show: output.asset_ids.length <= 12,
                            formatter: (params: {data?: {value?: [number, number, number | null]}}) => {
                                const value = params.data?.value?.[2];
                                return typeof value === 'number' ? value.toFixed(2) : '—';
                            },
                            color: dark ? '#e2e8f0' : '#0f172a',
                        },
                        emphasis: {itemStyle: {shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.25)'}},
                    },
                ],
            },
            true,
        );
    }
</script>

<div class="w-full overflow-x-auto" data-testid="risk-correlation-heatmap">
    <div bind:this={container} class="min-w-[520px] w-full" style:height></div>
</div>
