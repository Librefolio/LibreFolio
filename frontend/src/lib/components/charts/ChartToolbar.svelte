<!--
  ChartToolbar — Toolbar for chart type and view mode selection.
  Note: Measure mode is always-on (3-click cycle), no toggle button needed.
-->
<script lang="ts">
    // =========================================================================
    // Types
    // =========================================================================

    export type ChartType = 'line' | 'candlestick';
    export type ViewMode = 'absolute' | 'percentage';

    interface Props {
        chartType?: ChartType;
        viewMode?: ViewMode;
        onChartTypeChange?: (type: ChartType) => void;
        onViewModeChange?: (mode: ViewMode) => void;
        /** Disable candlestick option (e.g., when stub not yet implemented) */
        disableCandlestick?: boolean;
    }

    let {chartType = 'line', viewMode = 'absolute', onChartTypeChange, onViewModeChange, disableCandlestick = false}: Props = $props();
</script>

<div class="flex flex-wrap items-center gap-2 text-sm text-lf-primary">
    <!-- Chart Type Toggle -->
    <div class="flex rounded-lg border border-lf-subtle overflow-hidden">
        <button class="px-3 py-1.5 transition-colors {chartType === 'line' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-secondary hover:bg-lf-hover'}" data-testid="chart-type-line" onclick={() => onChartTypeChange?.('line')}> Line </button>
        <button
            class="px-3 py-1.5 transition-colors {chartType === 'candlestick' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-secondary hover:bg-lf-hover'}
                {disableCandlestick ? 'opacity-50 cursor-not-allowed' : ''}"
            data-testid="chart-type-candlestick"
            disabled={disableCandlestick}
            onclick={() => !disableCandlestick && onChartTypeChange?.('candlestick')}
            title={disableCandlestick ? 'Coming soon' : ''}
        >
            Candle
        </button>
    </div>

    <!-- Divider -->
    <div class="w-px h-6 bg-lf-subtle hidden sm:block"></div>

    <!-- View Mode Toggle -->
    <div class="flex rounded-lg border border-lf-subtle overflow-hidden">
        <button class="px-3 py-1.5 transition-colors {viewMode === 'absolute' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-secondary hover:bg-lf-hover'}" onclick={() => onViewModeChange?.('absolute')}> Abs </button>
        <button class="px-3 py-1.5 transition-colors {viewMode === 'percentage' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-secondary hover:bg-lf-hover'}" onclick={() => onViewModeChange?.('percentage')}> % </button>
    </div>
</div>
