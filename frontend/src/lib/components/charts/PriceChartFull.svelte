<!--
  PriceChartFull — Full-featured price chart compositor.

  Assembles: ChartToolbar + LineChart + DataZoomBar + MeasureOverlay
  Bidirectional zoom: LineChart ↔ DataZoomBar sync both ways.
  MeasureOverlay: 3-click cycle with Y-coordinate mapping.

  Note: Range presets (1W, 1M, etc.) are handled by DateRangePicker outside of this component.
-->
<script lang="ts">
    import ChartToolbar from './ChartToolbar.svelte';
    import LineChart from './LineChart.svelte';
    import DataZoomBar from './DataZoomBar.svelte';
    import MeasureOverlay from './MeasureOverlay.svelte';
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

    let chartType: ChartType = $state('line');
    let viewMode: ViewMode = $state('absolute');
    let zoomRange: [number, number] = $state([0, 100]);
    let measureMode = $state(false);

    // Sync from props when they change externally
    $effect(() => { chartType = initialChartType; });
    $effect(() => { viewMode = initialViewMode; });

    // =========================================================================
    // Derived data (percentage mode)
    // =========================================================================

    let displayData = $derived.by(() => {
        if (viewMode === 'absolute' || data.length === 0) return data;

        // Percentage mode: relative to first point in data (range start)
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

    // Zoom data for DataZoomBar (always absolute for the overview)
    let zoomData = $derived(data.map(d => ({date: d.date, value: d.value})));

    // Y-range for MeasureOverlay coordinate mapping
    let yRange = $derived.by(() => {
        if (displayData.length === 0) return null;
        const values = displayData.map(d => d.value);
        const min = Math.min(...values);
        const max = Math.max(...values);
        // Add padding (same as ECharts scale: true)
        const padding = (max - min) * 0.1 || 0.01;
        return {min: min - padding, max: max + padding};
    });

    // Approximate chart grid bounds based on typical ECharts rendering
    // These match the grid config in LineChart.svelte
    let chartGridBounds = $derived.by(() => {
        // Approximate based on LineChart grid config:
        // {top: 35, right: 15, bottom: 35, left: 15, containLabel: true}
        // With containLabel, the actual grid includes label widths.
        // We estimate: left ~60px (Y-axis labels), right ~15px, top ~35px, bottom ~35px
        return {
            left: 60,
            right: 15,
            top: 35,
            bottom: 35,
            width: 0,  // Will be overridden — width not critical for % mapping
            height: 0, // Same
        };
    });

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleChartTypeChange(type: ChartType) {
        chartType = type;
    }

    function handleViewModeChange(mode: ViewMode) {
        viewMode = mode;
    }

    function handleMeasureModeChange(enabled: boolean) {
        measureMode = enabled;
    }

    /** Called by DataZoomBar when user drags the slider */
    function handleZoomBarChange(start: number, end: number) {
        zoomRange = [start, end];
    }

    /** Called by LineChart when user zooms with mouse wheel/drag */
    function handleChartZoomChange(start: number, end: number) {
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
        {measureMode}
        onChartTypeChange={handleChartTypeChange}
        onViewModeChange={handleViewModeChange}
        onMeasureModeChange={handleMeasureModeChange}
        disableCandlestick={true}
    />

    <!-- Main Chart (with MeasureOverlay) -->
    <div class="relative">
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
                onZoomChange={handleChartZoomChange}
                viewMode={viewMode}
            />
        {:else}
            <!-- Candlestick stub -->
            <div class="flex items-center justify-center bg-gray-50 dark:bg-slate-800 rounded-lg border border-dashed border-gray-300 dark:border-slate-600" style="height: {chartHeight};">
                <p class="text-gray-400 dark:text-slate-500 text-sm">Candlestick chart — Coming soon</p>
            </div>
        {/if}

        <!-- MeasureOverlay (3-click cycle: start → complete → dismiss) -->
        <MeasureOverlay
            enabled={measureMode}
            data={displayData}
            {currency}
            viewMode={viewMode}
            {chartGridBounds}
            {yRange}
        />
    </div>

    <!-- DataZoom Bar (single overview line, synced bidirectionally) -->
    {#if zoomData.length > 0}
        <DataZoomBar
            data={zoomData}
            {zoomRange}
            onZoomChange={handleZoomBarChange}
            height={zoomHeight}
        />
    {/if}
</div>
