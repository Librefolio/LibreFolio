<!--
  ChartAestheticsSection — Extracted chart aesthetics controls.

  Contains the 4 toggles (baseline colors, area fill, grid lines, stale gradient)
  and Y-axis mode selector (Auto/Include0/Custom with min/max).

  Used by: ChartSettingsModal (in ModalBase) and FX detail page (inline foldable panel).
  Pure component: receives values via props, emits changes via callbacks.

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        colorByBaseline?: boolean;
        areaFill?: boolean;
        gridLines?: boolean;
        staleGradient?: boolean;
        yAxisMode?: 'auto' | 'include0' | 'custom';
        yAxisMin?: number | undefined;
        yAxisMax?: number | undefined;
        /** Called when any value changes */
        onchange?: (values: {colorByBaseline: boolean; areaFill: boolean; gridLines: boolean; staleGradient: boolean; yAxisMode: 'auto' | 'include0' | 'custom'; yAxisMin: number | undefined; yAxisMax: number | undefined}) => void;
    }

    let {
        colorByBaseline = $bindable(true),
        areaFill = $bindable(true),
        gridLines = $bindable(true),
        staleGradient = $bindable(true),
        yAxisMode = $bindable<'auto' | 'include0' | 'custom'>('auto'),
        yAxisMin = $bindable<number | undefined>(undefined),
        yAxisMax = $bindable<number | undefined>(undefined),
        onchange,
    }: Props = $props();

    // =========================================================================
    // Emit changes
    // =========================================================================

    function emitChange() {
        onchange?.({colorByBaseline, areaFill, gridLines, staleGradient, yAxisMode, yAxisMin, yAxisMax});
    }
</script>

<div>
    <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">{$t('common.aesthetics')}</h3>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <!-- Color by baseline -->
        <div class="flex items-center justify-between gap-3 p-2.5 rounded-lg border border-gray-200 dark:border-slate-600">
            <span>
                <span class="block text-sm font-medium text-gray-700 dark:text-gray-200">{$t('chartSettings.baselineColors')}</span>
                <span class="block text-xs text-gray-500 dark:text-gray-400">{$t('chartSettings.baselineColorsDesc')}</span>
            </span>
            <button
                aria-label={$t('chartSettings.baselineColors')}
                class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors {colorByBaseline ? 'bg-libre-green' : 'bg-gray-300 dark:bg-slate-600'}"
                onclick={() => {
                    colorByBaseline = !colorByBaseline;
                    emitChange();
                }}
                type="button"
            >
                <span class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {colorByBaseline ? 'translate-x-6' : 'translate-x-1'}"></span>
            </button>
        </div>

        <!-- Area fill -->
        <div class="flex items-center justify-between gap-3 p-2.5 rounded-lg border border-gray-200 dark:border-slate-600">
            <span>
                <span class="block text-sm font-medium text-gray-700 dark:text-gray-200">{$t('chartSettings.areaFill')}</span>
                <span class="block text-xs text-gray-500 dark:text-gray-400">{$t('chartSettings.areaFillDesc')}</span>
            </span>
            <button
                aria-label={$t('chartSettings.areaFill')}
                class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors {areaFill ? 'bg-libre-green' : 'bg-gray-300 dark:bg-slate-600'}"
                onclick={() => {
                    areaFill = !areaFill;
                    emitChange();
                }}
                type="button"
            >
                <span class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {areaFill ? 'translate-x-6' : 'translate-x-1'}"></span>
            </button>
        </div>

        <!-- Grid lines -->
        <div class="flex items-center justify-between gap-3 p-2.5 rounded-lg border border-gray-200 dark:border-slate-600">
            <span>
                <span class="block text-sm font-medium text-gray-700 dark:text-gray-200">{$t('chartSettings.gridLines')}</span>
                <span class="block text-xs text-gray-500 dark:text-gray-400">{$t('chartSettings.gridLinesDesc')}</span>
            </span>
            <button
                aria-label={$t('chartSettings.gridLines')}
                class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors {gridLines ? 'bg-libre-green' : 'bg-gray-300 dark:bg-slate-600'}"
                onclick={() => {
                    gridLines = !gridLines;
                    emitChange();
                }}
                type="button"
            >
                <span class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {gridLines ? 'translate-x-6' : 'translate-x-1'}"></span>
            </button>
        </div>

        <!-- Stale gradient -->
        <div class="flex items-center justify-between gap-3 p-2.5 rounded-lg border border-gray-200 dark:border-slate-600">
            <span>
                <span class="block text-sm font-medium text-gray-700 dark:text-gray-200">{$t('chartSettings.staleGradient')}</span>
                <span class="block text-xs text-gray-500 dark:text-gray-400">{$t('chartSettings.staleGradientDesc')}</span>
            </span>
            <button
                aria-label={$t('chartSettings.staleGradient')}
                class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors {staleGradient ? 'bg-libre-green' : 'bg-gray-300 dark:bg-slate-600'}"
                onclick={() => {
                    staleGradient = !staleGradient;
                    emitChange();
                }}
                type="button"
            >
                <span class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {staleGradient ? 'translate-x-6' : 'translate-x-1'}"></span>
            </button>
        </div>

        <!-- Y-axis scale mode -->
        <div class="flex items-center justify-between gap-3 p-2.5 rounded-lg border border-gray-200 dark:border-slate-600 sm:col-span-2">
            <span class="shrink-0">
                <span class="block text-sm font-medium text-gray-700 dark:text-gray-200">{$t('chartSettings.yAxisScale')}</span>
                <span class="block text-xs text-gray-500 dark:text-gray-400">{$t('chartSettings.yAxisScaleDesc')}</span>
            </span>
            <div class="flex items-center gap-2 flex-wrap">
                <div class="flex rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
                    <button
                        class="px-2.5 py-1 text-[10px] font-medium transition-colors {yAxisMode === 'auto' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                        onclick={() => {
                            yAxisMode = 'auto';
                            emitChange();
                        }}
                        type="button"
                        >Auto
                    </button>
                    <button
                        class="px-2.5 py-1 text-[10px] font-medium transition-colors {yAxisMode === 'include0' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                        onclick={() => {
                            yAxisMode = 'include0';
                            emitChange();
                        }}
                        type="button">{$t('chartSettings.yAxisInclude0')}</button
                    >
                    <button
                        class="px-2.5 py-1 text-[10px] font-medium transition-colors {yAxisMode === 'custom' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                        onclick={() => {
                            yAxisMode = 'custom';
                            emitChange();
                        }}
                        type="button">{$t('common.custom')}</button
                    >
                </div>
                {#if yAxisMode === 'custom'}
                    <div class="flex items-center gap-1.5 text-xs">
                        <span class="text-[10px] text-gray-500 dark:text-gray-400">Min</span>
                        <input
                            type="number"
                            class="w-20 px-1.5 py-0.5 text-xs border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 focus:ring-1 focus:ring-libre-green"
                            step="any"
                            value={yAxisMin ?? ''}
                            oninput={(e) => {
                                const v = e.currentTarget.value;
                                yAxisMin = v === '' ? undefined : Number(v);
                                emitChange();
                            }}
                            placeholder="—"
                        />
                        <span class="text-[10px] text-gray-500 dark:text-gray-400">Max</span>
                        <input
                            type="number"
                            class="w-20 px-1.5 py-0.5 text-xs border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 focus:ring-1 focus:ring-libre-green"
                            step="any"
                            value={yAxisMax ?? ''}
                            oninput={(e) => {
                                const v = e.currentTarget.value;
                                yAxisMax = v === '' ? undefined : Number(v);
                                emitChange();
                            }}
                            placeholder="—"
                        />
                    </div>
                {/if}
            </div>
        </div>
    </div>
</div>
