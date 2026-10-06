<!--
  R9.8: the geography exposure as two world maps, the ideal distribution (target shares) and the
  actual one (shares after the plan), on one colour scale. Pointing at a country in either map highlights it in both, and the box shows the two
  weights with the direction; the two maps zoom and pan together. Weights are public: nothing to mask.
  A category the map cannot place (the catch-all «Other», the uncategorised share, a code the map
  does not know) is listed under the maps, so no weight is left out.
-->
<script lang="ts" module>
    import * as echarts from 'echarts';
    import {buildGeoNameMaps} from '$lib/components/charts/geographyMapHelpers';

    /** The world map, fetched and registered once, then shared by every planner result. */
    let worldMap: Promise<Record<string, string>> | null = null;

    function loadWorldMap(): Promise<Record<string, string>> {
        worldMap ??= fetch('/data/world.json')
            .then((response) => {
                if (!response.ok) throw new Error(`world map: HTTP ${response.status}`);
                return response.json();
            })
            .then((geoJson) => {
                echarts.registerMap('world', geoJson);
                return buildGeoNameMaps(geoJson).iso3ToGeoName;
            })
            .catch((error: unknown) => {
                worldMap = null;
                throw error;
            });
        return worldMap;
    }
</script>

<script lang="ts">
    import {onMount, tick} from 'svelte';
    import {t} from '$lib/i18n';
    import {attachChartReady} from '$lib/utils/chartReady';
    import {createResizeWatcher} from '$lib/utils/core/resizeWatcher';
    import {CHART_SET_OPTION_OPTS} from '$lib/components/charts/echartsAnimationConfig';
    import {buildTooltipTheme, scheduleFirstRenderStabilityFix} from '$lib/components/charts/echartsTooltipHelpers';
    import {centroidOf} from '$lib/components/charts/geographyMapHelpers';
    import {formatExactPercent, formatPlannerPercentUnits} from '../format';
    import HelpTip from '../shared/HelpTip.svelte';
    import {HINT} from '../ui';
    import {exposureTooltipHtml, exposureTooltipText} from './exposureTooltip';
    import {chartPercent, type MapWeightRow} from './model';
    const KEY = 'tools.pacAllocator.planner.result';

    interface Props {
        rows: readonly MapWeightRow[];
    }

    let {rows}: Props = $props();

    type Side = 'target' | 'final';
    type MapView = {zoom?: number; center?: (number | string)[]};
    const SIDES: readonly Side[] = ['target', 'final'];
    const SERIES_ID = 'pac-planner-exposure-map';
    /** The colours of the portfolio map (`GeographyMap`), so one weight reads the same on both pages. */
    const SCALE = {
        light: ['#f0fdf4', '#bbf7d0', '#86efac', '#4ade80', '#22c55e', '#16a34a'],
        dark: ['#1e3a2f', '#22543d', '#276749', '#2f855a', '#38a169', '#48bb78'],
    };

    let geoNames = $state<Record<string, string> | null>(null);
    let failed = $state(false);
    let dark = $state(false);
    let frame = $state<HTMLDivElement | null>(null);
    const containers = $state<Record<Side, HTMLDivElement | null>>({target: null, final: null});
    const charts: Record<Side, echarts.ECharts | null> = {target: null, final: null};
    const touchCleanups: Record<Side, (() => void) | null> = {target: null, final: null};
    const resizeWatcher = createResizeWatcher(() => {
        for (const side of SIDES) charts[side]?.resize();
    });
    let renderGeneration = 0;

    function geoName(row: MapWeightRow): string | null {
        if (!geoNames) return null;
        return geoNames[row.code] ?? geoNames[row.code.toUpperCase()] ?? null;
    }

    const placed = $derived(geoNames ? rows.filter((row) => geoName(row) !== null) : []);
    const offMap = $derived(failed ? rows : geoNames ? rows.filter((row) => geoName(row) === null) : []);
    /** No map while nothing can be placed on it (only «Other» or the uncategorised share): the list says it all. */
    const showMaps = $derived(!failed && (geoNames === null || placed.length > 0));
    const byGeoName = $derived(new Map(placed.map((row) => [geoName(row) as string, row])));
    /** One scale for both maps: up to the largest weight either map draws, rounded up to a whole percent. */
    const scaleMax = $derived.by(() => {
        const values = placed.flatMap((row) => [chartPercent(row.target), chartPercent(row.final)]).filter((value): value is number => value !== null);
        const widest = Math.ceil(Math.max(0, ...values));
        return widest > 0 ? widest : 100;
    });
    const text = $derived(exposureTooltipText($t));
    const colours = $derived(dark ? SCALE.dark : SCALE.light);

    onMount(() => {
        const readTheme = () => {
            dark = document.documentElement.classList.contains('dark');
        };
        readTheme();
        const observer = new MutationObserver(readTheme);
        observer.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
        loadWorldMap()
            .then((names) => {
                geoNames = names;
            })
            .catch((error: unknown) => {
                console.error('PAC planner: world map not available', error);
                failed = true;
            });
        return () => {
            renderGeneration += 1;
            observer.disconnect();
            resizeWatcher.disconnect();
            for (const side of SIDES) release(side);
        };
    });

    $effect(() => {
        const elements = {target: containers.target, final: containers.final};
        const options = {target: option('target'), final: option('final')};
        const wrapper = frame;
        if (!geoNames || !elements.target || !elements.final || !wrapper) return;
        const generation = ++renderGeneration;
        tick().then(() => {
            if (generation !== renderGeneration) return;
            for (const side of SIDES) draw(side, elements[side] as HTMLDivElement, options[side]);
            resizeWatcher.observe(wrapper);
        });
    });

    function option(side: Side): echarts.EChartsOption {
        const theme = buildTooltipTheme(dark);
        const tooltipText = text;
        const rowsByName = byGeoName;
        return {
            tooltip: {
                trigger: 'item',
                confine: true,
                backgroundColor: theme.bg,
                borderColor: theme.border,
                textStyle: {color: theme.textColor, fontSize: 12},
                formatter: (params: unknown) => {
                    const row = rowsByName.get(String((params as {name?: string}).name ?? ''));
                    return row ? exposureTooltipHtml(row, tooltipText, theme) : '';
                },
            },
            visualMap: {show: false, min: 0, max: scaleMax, seriesIndex: 0, inRange: {color: colours}},
            series: [
                {
                    id: SERIES_ID,
                    type: 'map',
                    map: 'world',
                    roam: true,
                    scaleLimit: {min: 1, max: 5},
                    selectedMode: false,
                    // A country outside the plan has no box: only the plan's countries switch it back on.
                    tooltip: {show: false},
                    emphasis: {label: {show: false}, itemStyle: {areaColor: dark ? '#fbbf24' : '#f59e0b'}},
                    itemStyle: {areaColor: dark ? '#334155' : '#e2e8f0', borderColor: dark ? '#1e293b' : '#cbd5e1', borderWidth: 0.5},
                    label: {show: false},
                    data: placed.map((row) => ({name: geoName(row) as string, value: chartPercent(side === 'target' ? row.target : row.final) ?? '-', tooltip: {show: true}})),
                },
            ],
        };
    }

    function release(side: Side): void {
        touchCleanups[side]?.();
        touchCleanups[side] = null;
        charts[side]?.dispose();
        charts[side] = null;
    }

    function draw(side: Side, element: HTMLDivElement, next: echarts.EChartsOption): void {
        // The maps come back on a new node after being hidden: start again on it.
        if (charts[side] && charts[side]?.getDom() !== element) release(side);
        let chart = charts[side];
        const fresh = chart === null;
        if (!chart) {
            chart = echarts.init(element, undefined, {renderer: 'canvas'});
            charts[side] = chart;
            attachChartReady(chart, element, `pac-planner-exposure-map-${side}`);
            follow(side, chart);
            touchCleanups[side] = touchPan(side, element);
        }
        chart.setOption(next, CHART_SET_OPTION_OPTS);
        if (fresh) scheduleFirstRenderStabilityFix(chart, element);
    }

    function other(side: Side): echarts.ECharts | null {
        return charts[side === 'target' ? 'final' : 'target'];
    }

    function viewOf(chart: echarts.ECharts): MapView {
        return (chart.getOption() as {series?: MapView[]}).series?.[0] ?? {};
    }

    /** The other map follows: the same country highlighted, the same zoom and position. */
    function follow(side: Side, chart: echarts.ECharts): void {
        chart.on('mouseover', (params) => other(side)?.dispatchAction({type: 'highlight', seriesId: SERIES_ID, name: params.name}));
        chart.on('mouseout', (params) => other(side)?.dispatchAction({type: 'downplay', seriesId: SERIES_ID, name: params.name}));
        // `setOption` does not emit `georoam`, so the two maps never echo each other.
        chart.on('georoam', () => {
            const {zoom, center} = viewOf(chart);
            other(side)?.setOption({series: [{id: SERIES_ID, zoom, center}]} as echarts.EChartsOption);
        });
    }

    /**
     * Two fingers pan a zoomed map on a touch screen, as on the portfolio map: one finger always
     * scrolls the page, and ECharts does not pan on touch by itself (see `GeographyMap`).
     */
    function touchPan(side: Side, element: HTMLDivElement): () => void {
        let last: {x: number; y: number} | null = null;
        const zoomedIn = () => {
            const chart = charts[side];
            return chart !== null && (viewOf(chart).zoom ?? 1) > 1.01;
        };
        const start = (event: TouchEvent) => {
            last = event.touches.length === 2 && zoomedIn() ? centroidOf(event.touches) : null;
        };
        const move = (event: TouchEvent) => {
            const chart = charts[side];
            if (event.touches.length !== 2) {
                last = null;
                return;
            }
            if (!last || !chart) return;
            const next = centroidOf(event.touches);
            event.preventDefault();
            chart.dispatchAction({type: 'geoRoam', seriesId: SERIES_ID, dx: next.x - last.x, dy: next.y - last.y});
            last = next;
        };
        element.addEventListener('touchstart', start, {passive: true});
        element.addEventListener('touchmove', move, {passive: false});
        element.addEventListener('touchend', start, {passive: true});
        element.addEventListener('touchcancel', start, {passive: true});
        return () => {
            element.removeEventListener('touchstart', start);
            element.removeEventListener('touchmove', move);
            element.removeEventListener('touchend', start);
            element.removeEventListener('touchcancel', start);
        };
    }

    function afterText(row: MapWeightRow): string {
        return row.final.kind === 'available' ? formatExactPercent(row.final.value) : '—';
    }
</script>

<div data-testid="pac-planner-exposures-maps" data-state={failed ? 'failed' : geoNames ? 'ready' : 'loading'}>
    {#if failed}
        <p class={HINT}>{$t(`${KEY}.exposures.mapUnavailable`, {default: 'The map could not be loaded: the weights are listed here.'})}</p>
    {:else if showMaps}
        <div bind:this={frame} class="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {#each SIDES as side (side)}
                <figure class="min-w-0">
                    <figcaption class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                        {side === 'target' ? text.target : text.final}
                    </figcaption>
                    <div bind:this={containers[side]} class="mt-1 h-52 w-full sm:h-60" data-testid="pac-planner-exposures-map" data-side={side} aria-hidden="true"></div>
                </figure>
            {/each}
        </div>
        <div class="mt-2 flex flex-wrap items-center gap-2 text-xs text-gray-500 dark:text-gray-400" data-testid="pac-planner-exposures-scale">
            <span>{$t(`${KEY}.exposures.scale`, {default: 'Colour scale'})}</span>
            <span class="tabular-nums">{formatPlannerPercentUnits('0', 0)}</span>
            <span class="h-2 w-32 rounded-sm" style:background="linear-gradient(to right, {colours.join(', ')})" aria-hidden="true"></span>
            <span class="tabular-nums">{formatPlannerPercentUnits(String(scaleMax), 0)}</span>
            <HelpTip
                label={$t(`${KEY}.exposures.scale`, {default: 'Colour scale'})}
                help={$t(`${KEY}.exposures.scaleHelp`, {default: 'One scale for both maps: the same colour is the same weight. Point at a country, or tap it, to see its two weights.'})}
                testid="pac-planner-exposures-scale-help"
            />
        </div>
    {/if}
    {#if offMap.length > 0}
        <p class="mt-2 {HINT}" data-testid="pac-planner-exposures-off-map">
            {#if !failed && showMaps}<span class="font-medium">{$t(`${KEY}.exposures.offMap`, {default: 'Not on the map'})}:</span>{' '}{/if}
            {#each offMap as row, index (row.id)}{index > 0 ? ' · ' : ''}{row.label} {formatExactPercent(row.target)} → {afterText(row)}{/each}
        </p>
    {/if}
</div>
