<!--
  PriceChartCompact — Miniature line chart for card views.
  No toolbar, no zoom, no edit. Just a clean line with optional area fill.
  Supports viewMode for percentage segment coloring.
  Shows mini Y-axis with 2-3 ticks for value reference.
  Used by FxCard, AssetCard, ChartSettingsModal preview, etc.
-->
<script lang="ts">
    import LineChart from './LineChart.svelte';
    import type {LineDataPoint} from './LineChart.svelte';
    import type {RenderedSignal} from '$lib/charts/signals';
    interface Props {
        data: LineDataPoint[];
        height?: string;
        lineColor?: string;
        areaFill?: boolean;
        viewMode?: 'absolute' | 'percentage';
        showMiniAxis?: boolean;
        /** Enable baseline coloring (red below 0, green above in % mode) */
        colorByBaseline?: boolean;
        /** Show grid lines */
        showGridLines?: boolean;
        /** Overlay signals to render as additional line series */
        overlaySignals?: RenderedSignal[];
    }
    let {
        data = [],
        height = '80px',
        lineColor = '#1a4031',
        areaFill = true,
        viewMode = 'absolute',
        showMiniAxis = true,
        colorByBaseline,
        showGridLines,
        overlaySignals = [],
    }: Props = $props();

    // Default colorByBaseline to true only in percentage mode
    let effectiveColorByBaseline = $derived(colorByBaseline ?? (viewMode === 'percentage'));
</script>
<LineChart
    {data}
    {height}
    {lineColor}
    areaFill={areaFill}
    compact={true}
    {showMiniAxis}
    showGradient={false}
    colorByBaseline={effectiveColorByBaseline}
    showGridLines={showGridLines}
    {viewMode}
    {overlaySignals}
/>
