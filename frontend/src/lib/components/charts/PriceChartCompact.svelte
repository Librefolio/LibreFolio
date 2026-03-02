<!--
  PriceChartCompact — Miniature line chart for card views.
  No toolbar, no zoom, no edit. Just a clean line with optional area fill.
  Used by FxCard, AssetCard, etc.
-->
<script lang="ts">
    import LineChart from './LineChart.svelte';
    import type {LineDataPoint} from './LineChart.svelte';
    interface Props {
        data: LineDataPoint[];
        height?: string;
        lineColor?: string;
        areaFill?: boolean;
    }
    let {
        data = [],
        height = '80px',
        lineColor = '#1a4031',
        areaFill = true,
    }: Props = $props();
</script>
<LineChart
    {data}
    {height}
    {lineColor}
    {areaFill}
    compact={true}
    showGradient={false}
/>
