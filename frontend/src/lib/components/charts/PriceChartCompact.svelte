<!--
  PriceChartCompact — Miniature line chart for card views.
  No toolbar, no zoom, no edit. Just a clean line with optional area fill.
  Supports viewMode for percentage segment coloring.
  Shows mini Y-axis with 2-3 ticks for value reference.
  Used by FxCard, AssetCard, ChartSettingsModal preview, etc.
-->
<script lang="ts">
    import type {LineDataPoint} from './LineChart.svelte';
    import LineChart from './LineChart.svelte';
    import type {RenderedSignal} from '$lib/charts/signals';
    import type {AxisScaleSettings} from '$lib/stores/chartSettingsStore.svelte';
    import {PRICE_SERIES} from '$lib/theme/chartTheme';
    import ResolutionBadge from './ResolutionBadge.svelte';
    import type {ChartResolution} from './timeSeriesAggregation';

    interface Props {
        data: LineDataPoint[];
        height?: string;
        lineColor?: string;
        areaFill?: boolean;
        viewMode?: 'absolute' | 'percentage';
        showMiniAxis?: boolean;
        /** Enable baseline coloring (red below 0, green above in % mode) */
        colorByBaseline?: boolean;
        /** Base of the colouring in the absolute view; without it, the first point of `data` */
        baselineValue?: number;
        /** Show grid lines */
        showGridLines?: boolean;
        /** Show stale-data gradient (per-point opacity). Default: false for compact */
        showGradient?: boolean;
        /** Overlay signals to render as additional line series */
        overlaySignals?: RenderedSignal[];
        /** Scale profile for the active absolute/percentage primary axis. */
        axisScale?: AxisScaleSettings;
        /** Stable semantic settings for active non-primary axes. */
        secondaryAxisScales?: Record<string, AxisScaleSettings>;
        /** The step the backend already applied to `data` (a card's `max_points`): the badge shows the coarser of it and the chart's own */
        sampledResolution?: ChartResolution;
    }

    let {
        data = [],
        height = '80px',
        lineColor = PRICE_SERIES.line.light,
        areaFill = true,
        viewMode = 'absolute',
        showMiniAxis = true,
        colorByBaseline,
        baselineValue,
        showGridLines,
        showGradient = false,
        overlaySignals = [],
        axisScale,
        secondaryAxisScales = {},
        sampledResolution = 'daily',
    }: Props = $props();

    // Default colorByBaseline to true only in percentage mode
    let effectiveColorByBaseline = $derived(colorByBaseline ?? viewMode === 'percentage');

    // The aggregation level of the card, as the detail's badge says it (Y5-F3): what the backend sampled, or what the chart
    // itself aggregates for this plot, whichever is coarser.
    const COARSENESS: Record<ChartResolution, number> = {daily: 0, weekly: 1, monthly: 2};
    let chartResolution = $state<ChartResolution>('daily');
    let shownResolution = $derived<ChartResolution>(COARSENESS[sampledResolution] >= COARSENESS[chartResolution] ? sampledResolution : chartResolution);
</script>

<div class="relative">
    <LineChart
        {areaFill}
        {baselineValue}
        colorByBaseline={effectiveColorByBaseline}
        compact={true}
        {data}
        {height}
        {lineColor}
        {overlaySignals}
        {secondaryAxisScales}
        {showGradient}
        {showGridLines}
        {showMiniAxis}
        {viewMode}
        yAxisMax={axisScale?.max}
        yAxisMin={axisScale?.min}
        yAxisMode={axisScale?.mode}
        onresolution={(resolution) => {
            if (resolution !== chartResolution) chartResolution = resolution;
        }}
    />
    <div class="pointer-events-none absolute left-1 top-0 scale-90 origin-top-left">
        <ResolutionBadge resolution={shownResolution} />
    </div>
</div>
