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

<div class="flex flex-wrap items-center gap-2 text-sm">
    <!-- Chart Type Toggle -->
    <div class="flex rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
        <button class="px-3 py-1.5 transition-colors {chartType === 'line' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}" onclick={() => onChartTypeChange?.('line')}> Line </button>
        <button
            class="px-3 py-1.5 transition-colors {chartType === 'candlestick' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}
                {disableCandlestick ? 'opacity-50 cursor-not-allowed' : ''}"
            disabled={disableCandlestick}
            onclick={() => !disableCandlestick && onChartTypeChange?.('candlestick')}
            title={disableCandlestick ? 'Coming soon' : ''}
        >
            Candle
        </button>
    </div>

    <!-- Divider -->
    <div class="w-px h-6 bg-gray-200 dark:bg-slate-600 hidden sm:block"></div>

    <!-- View Mode Toggle -->
    <div class="flex rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
        <button class="px-3 py-1.5 transition-colors {viewMode === 'absolute' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}" onclick={() => onViewModeChange?.('absolute')}> Abs </button>
        <button class="px-3 py-1.5 transition-colors {viewMode === 'percentage' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}" onclick={() => onViewModeChange?.('percentage')}> % </button>
    </div>
</div>
