<!--
  PriceChartFull — Full-featured price chart compositor.

  Assembles: ChartToolbar + LineChart + DataZoomBar
  The DataZoomBar controls the visible range of the LineChart via shared zoom state.

  Note: Range presets (1W, 1M, etc.) are handled by DateRangePicker outside of this component.
-->
<script lang="ts">
    import ChartToolbar from './ChartToolbar.svelte';
    import LineChart from './LineChart.svelte';
    import DataZoomBar from './DataZoomBar.svelte';
    import type {LineDataPoint} from './LineChart.svelte';
    import type {ChartType, ViewMode} from './ChartToolbar.svelte';

    // =========================================================================
    // Types
    // =========================================================================

    interface Props {
        /** Chart data points */
        data: LineDataPoint[];
        /** Pending edit overlay points */
        pendingData?: LineDataPoint[];
        /** Currency label */
        currency?: string;
        /** Main chart height */
        chartHeight?: string;
        /** DataZoom bar height */
        zoomHeight?: string;
        /** Initial chart type */
        initialChartType?: ChartType;
        /** Initial view mode */
        initialViewMode?: ViewMode;
        /** Whether edit mode is active (enables click-to-edit) */
        editMode?: boolean;
        /** Called when a point is clicked (for edit) */
        onPointClick?: (date: string, value: number) => void;
    }

    let {
        data = [],
        pendingData = [],
        currency = '',
        chartHeight = '350px',
        zoomHeight = '60px',
        initialChartType = 'line',
        initialViewMode = 'absolute',
        editMode = false,
        onPointClick,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let chartType: ChartType = $state(initialChartType);
    let viewMode: ViewMode = $state(initialViewMode);
    let zoomRange: [number, number] = $state([0, 100]);

    // =========================================================================
    // Derived data (percentage mode)
    // =========================================================================

    let displayData = $derived.by(() => {
        if (viewMode === 'absolute' || data.length === 0) return data;

        // Percentage mode: relative to first visible point
        const baseValue = data[0].value;
        if (baseValue === 0) return data;

        return data.map(d => ({
            ...d,
            value: ((d.value - baseValue) / baseValue) * 100,
        }));
    });

    let displayPending = $derived.by(() => {
        if (viewMode === 'absolute' || data.length === 0 || !pendingData || pendingData.length === 0) return pendingData;

        const baseValue = data[0].value;
        if (baseValue === 0) return pendingData;

        return pendingData.map(d => ({
            ...d,
            value: ((d.value - baseValue) / baseValue) * 100,
        }));
    });

    // Determine line color based on viewMode and data trend
    let lineColor = $derived.by(() => {
        if (viewMode !== 'percentage' || displayData.length < 2) return undefined; // use default
        const last = displayData[displayData.length - 1].value;
        // Percentage mode: negative = red, positive = green
        return last < 0 ? '#ef4444' : '#16a34a'; // red-500 / green-600
    });

    let darkLineColor = $derived.by(() => {
        if (viewMode !== 'percentage' || displayData.length < 2) return undefined;
        const last = displayData[displayData.length - 1].value;
        return last < 0 ? '#f87171' : '#4ade80'; // red-400 / green-400
    });

    // Zoom data for DataZoomBar (always absolute for the overview)
    let zoomData = $derived(data.map(d => ({date: d.date, value: d.value})));

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleChartTypeChange(type: ChartType) {
        chartType = type;
    }

    function handleViewModeChange(mode: ViewMode) {
        viewMode = mode;
    }

    function handleZoomChange(start: number, end: number) {
        zoomRange = [start, end];
    }

    function handlePointClick(date: string, value: number) {
        if (editMode && onPointClick) {
            // Convert back to absolute value if in percentage mode
            if (viewMode === 'percentage' && data.length > 0) {
                const baseValue = data[0].value;
                const absoluteValue = baseValue * (1 + value / 100);
                onPointClick(date, absoluteValue);
            } else {
                onPointClick(date, value);
            }
        }
    }
</script>

<div class="space-y-2">
    <!-- Toolbar (chart type + view mode only, no range presets) -->
    <ChartToolbar
        {chartType}
        {viewMode}
        onChartTypeChange={handleChartTypeChange}
        onViewModeChange={handleViewModeChange}
        disableCandlestick={true}
    />

    <!-- Main Chart -->
    {#if chartType === 'line'}
        <LineChart
            data={displayData}
            pendingData={displayPending}
            {currency}
            height={chartHeight}
            showGradient={true}
            areaFill={true}
            onPointClick={editMode ? handlePointClick : undefined}
            {zoomRange}
            {lineColor}
            {darkLineColor}
            viewMode={viewMode}
        />
    {:else}
        <!-- Candlestick stub — will be replaced in Step 6 -->
        <div class="flex items-center justify-center bg-gray-50 dark:bg-slate-800 rounded-lg border border-dashed border-gray-300 dark:border-slate-600" style="height: {chartHeight};">
            <p class="text-gray-400 dark:text-slate-500 text-sm">Candlestick chart — Coming soon</p>
        </div>
    {/if}

    <!-- DataZoom Bar (connected to main chart via zoomRange) -->
    {#if zoomData.length > 0}
        <DataZoomBar
            data={zoomData}
            {zoomRange}
            onZoomChange={handleZoomChange}
            height={zoomHeight}
        />
    {/if}
</div>
