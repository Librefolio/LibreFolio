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
        /** Show stale-data gradient (per-point opacity). Default: false for compact */
        showGradient?: boolean;
        /** Overlay signals to render as additional line series */
        overlaySignals?: RenderedSignal[];
        /** Scale profile for the active absolute/percentage primary axis. */
        axisScale?: AxisScaleSettings;
        /** Stable semantic settings for active non-primary axes. */
        secondaryAxisScales?: Record<string, AxisScaleSettings>;
    }

    let {data = [], height = '80px', lineColor = '#1a4031', areaFill = true, viewMode = 'absolute', showMiniAxis = true, colorByBaseline, showGridLines, showGradient = false, overlaySignals = [], axisScale, secondaryAxisScales = {}}: Props = $props();

    // Default colorByBaseline to true only in percentage mode
    let effectiveColorByBaseline = $derived(colorByBaseline ?? viewMode === 'percentage');
</script>

<LineChart {areaFill} colorByBaseline={effectiveColorByBaseline} compact={true} {data} {height} {lineColor} {overlaySignals} {secondaryAxisScales} {showGradient} {showGridLines} {showMiniAxis} {viewMode} yAxisMax={axisScale?.max} yAxisMin={axisScale?.min} yAxisMode={axisScale?.mode} />
