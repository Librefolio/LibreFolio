<!--
  F4a of project 67, step 8: one exposure dimension of the Rebalancer as a bullet chart (the developer's decision of
  13/11, option (c)). For every category a grey bar «today» (`before_weight`), a coloured bar «after the plan»
  (`final_weight`) and a thin tick on the target (`target_weight`) across both; the cash row has the same form and is the
  last. Rows by target, largest first, then by the weight after; above 12 categories the first 12 and «Show all», never
  an «Others» row (a sum). Every number is a published weight; the lengths are drawing only. Weights are public.
  Colours (skill `design-system`, «Charts»): today in the PAC's neutral grey; after in the category's colour, ranked over
  every row, so «Show all» recolours nothing; the cash in its role; the tick in the primary text with a card halo.
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import {MediaQuery} from 'svelte/reactivity';
    import * as echarts from 'echarts';
    import {CHART_INIT_THEME} from '$lib/components/charts/chartFont';
    import {chartInitOptions} from '$lib/components/charts/chartPixelRatio';
    import {t} from '$lib/i18n';
    import {attachChartReady} from '$lib/utils/chartReady';
    import {createResizeWatcher} from '$lib/utils/core/resizeWatcher';
    import {CHART_SET_OPTION_OPTS} from '$lib/components/charts/echartsAnimationConfig';
    import {buildGridColors, buildTooltipTheme, scheduleFirstRenderStabilityFix} from '$lib/components/charts/echartsTooltipHelpers';
    import {categoryColor, COUNTRY_SEQUENCE, sequenceColor} from '$lib/theme/chartCategories';
    import {shadePoles} from '$lib/theme/chartShades';
    import {chartNeutrals} from '$lib/theme/chartTheme';
    import {chartRoles} from '$lib/theme/roleColors';
    import {isDarkTheme, onChartColorsChange, onThemeClassChange} from '$lib/theme/themeMode';
    import {BUTTON_LINK} from '../ui';
    import {actualColours, idealColour} from './exposureBarColours';
    import {chartPercent, compareExact, UNCATEGORISED_CATEGORY_ID, type WeightRow} from './model';
    import {bulletTooltipHtml, bulletTooltipText, type BulletRow} from './rebalancerExposureTooltip';
    import {getPlannerProfile, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();
    const KEY = 'tools.portfolioRebalancer.planner.result.exposure';

    interface Props {
        rows: readonly BulletRow[];
        dimension: 'asset_type' | 'sector' | 'geography';
    }

    let {rows, dimension}: Props = $props();

    /** Above this many categories, the rest is one click away (the cash row stays, the last). */
    const VISIBLE = 12;
    /** Geometry, fixed so the tick spans both bars: two bars of 8 px and their gap, the tick 2 px wider than nothing. */
    const BAR = 8;
    const TICK = {width: 2, height: 24};
    const HALO = {width: TICK.width + 2, height: TICK.height + 2};

    let dark = $state(false);
    let colorsVersion = $state(0);
    let showAll = $state(false);
    let container = $state<HTMLDivElement>();
    let chart: echarts.ECharts | null = null;
    const resizeWatcher = createResizeWatcher(() => chart?.resize());
    let renderGeneration = 0;
    /** On a phone the name goes above the bars, on the full width. */
    const phone = new MediaQuery('max-width: 640px');

    const text = $derived(bulletTooltipText($t));

    /** A published weight, or nothing: unavailable sorts last. */
    function descending(a: BulletRow['final'], b: BulletRow['final']): number {
        if (a.kind !== 'available' || b.kind !== 'available') return Number(a.kind !== 'available') - Number(b.kind !== 'available');
        return -(compareExact(a.value, b.value) ?? 0);
    }

    /** Every category in display order (target, then after, then today, all largest first; ties by id), then the cash. */
    const ordered = $derived.by(() => {
        const categories = rows.filter((row) => row.kind === 'category');
        categories.sort((a, b) => -(compareExact(a.target, b.target) ?? 0) || descending(a.final, b.final) || descending(a.before, b.before) || a.id.localeCompare(b.id));
        return {categories, cash: rows.filter((row) => row.kind === 'cash')};
    });
    const hidden = $derived(Math.max(0, ordered.categories.length - VISIBLE));
    const shown = $derived([...(showAll ? ordered.categories : ordered.categories.slice(0, VISIBLE)), ...ordered.cash]);
    const rowHeight = $derived(phone.current ? 52 : 36);
    const height = $derived(Math.max(96, shown.length * rowHeight + 16));

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
        if (!element) return;
        const generation = ++renderGeneration;
        tick().then(() => {
            if (generation !== renderGeneration) return;
            const fresh = chart === null;
            if (!chart) {
                chart = echarts.init(element, CHART_INIT_THEME, chartInitOptions(element));
                attachChartReady(chart, element, testId(`exposure-bullets-${dimension}`, profile));
            }
            // Whole options: a row hidden by «Show all» must not linger.
            chart.setOption(next, {...CHART_SET_OPTION_OPTS, notMerge: true});
            chart.resize();
            if (fresh) scheduleFirstRenderStabilityFix(chart, element);
            resizeWatcher.observe(element);
        });
    });

    /** The colour after the plan of every category, by its id: ranked over every category, never over the shown ones. */
    function categoryColours(poles: ReturnType<typeof shadePoles>): Map<string, string> {
        const categories = ordered.categories;
        if (dimension === 'geography') {
            let rank = 0;
            return new Map(categories.map((row) => [row.id, row.key === UNCATEGORISED_CATEGORY_ID ? categoryColor('sector', 'Unknown', dark, container ?? null) : sequenceColor(COUNTRY_SEQUENCE, rank++, dark, poles, container ?? null)]));
        }
        const weights = categories.map((row): WeightRow => ({id: row.key, label: row.label, target: row.target, final: row.final}));
        const colours = actualColours(weights, dimension, dark, poles);
        return new Map(categories.map((row, index) => [row.id, colours[index]]));
    }

    function option(): echarts.EChartsOption {
        void colorsVersion;
        const grid = buildGridColors(dark, container ?? null);
        const theme = buildTooltipTheme(dark, container ?? null);
        const neutrals = chartNeutrals(dark, container ?? null);
        const roles = chartRoles(dark, container ?? null);
        const card = roles.color('--lf-surface-card');
        const marks = {now: idealColour(dark), target: roles.color('--lf-text-primary'), halo: card};
        const byId = categoryColours(shadePoles(dark, card));
        const cash = categoryColor('sector', 'Liquidity', dark, container ?? null);
        const rowsShown = [...shown];
        const after = rowsShown.map((row) => (row.kind === 'cash' ? cash : (byId.get(row.id) ?? categoryColor('sector', 'Unknown', dark, container ?? null))));
        const tooltipText = text;
        const ticks = rowsShown.map((row, index) => [chartPercent(row.target), index]);
        const onPhone = phone.current;
        return {
            grid: onPhone ? {left: 4, right: 12, top: 18, bottom: 4, containLabel: false} : {left: 8, right: 24, top: 8, bottom: 4, containLabel: true},
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
                    const row = rowsShown[index];
                    return row ? bulletTooltipHtml(row, tooltipText, theme, {now: marks.now, after: after[index], target: marks.target}) : '';
                },
            },
            xAxis: {type: 'value', min: 0, show: false},
            yAxis: {
                type: 'category',
                inverse: true,
                data: rowsShown.map((row) => row.label),
                axisTick: {show: false},
                axisLine: {lineStyle: {color: grid.gridColor}},
                axisLabel: onPhone ? {inside: true, color: grid.textColor, fontSize: 11, align: 'left', verticalAlign: 'bottom', margin: 0, padding: [0, 0, BAR + 6, 0]} : {color: grid.textColor, fontSize: 11, width: 160, overflow: 'truncate'},
            },
            series: [
                {id: 'now', name: tooltipText.now, type: 'bar', barWidth: BAR, barGap: '25%', itemStyle: {color: marks.now, borderRadius: [0, 2, 2, 0]}, data: rowsShown.map((row) => chartPercent(row.before))},
                {id: 'after', name: tooltipText.after, type: 'bar', barWidth: BAR, itemStyle: {borderRadius: [0, 2, 2, 0]}, data: rowsShown.map((row, index) => ({value: chartPercent(row.final), itemStyle: {color: after[index]}}))},
                // The tick on the target: a halo in the card's colour under it, one pixel each side, so it reads on the grey,
                // on every category colour and on the empty track, in both themes.
                {id: 'target-halo', name: tooltipText.target, type: 'scatter', symbol: 'rect', symbolSize: [HALO.width, HALO.height], itemStyle: {color: marks.halo}, z: 3, silent: true, data: ticks},
                {id: 'target', name: tooltipText.target, type: 'scatter', symbol: 'rect', symbolSize: [TICK.width, TICK.height], itemStyle: {color: marks.target}, z: 4, data: ticks},
            ],
        };
    }
</script>

<div bind:this={container} class="w-full" style:height="{height}px" data-testid={testId('exposures-bullets', profile)} data-dimension={dimension} aria-hidden="true"></div>
{#if hidden > 0}
    <button type="button" class="{BUTTON_LINK} mt-1" aria-expanded={showAll} data-testid={testId('exposures-show-all', profile)} onclick={() => (showAll = !showAll)}>
        {showAll ? $t(`${KEY}.showFewer`, {default: 'Show fewer'}) : $t(`${KEY}.showAll`, {default: 'Show all ({count})', values: {count: ordered.categories.length}})}
    </button>
{/if}
