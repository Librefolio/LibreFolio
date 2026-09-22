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
    import type {AxisScaleMode, AxisScaleSettings} from '$lib/stores/chartSettingsStore.svelte';

    import {numericArrows} from '$lib/actions/numericArrows';
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
        /** Contextual primary + active semantic secondary axes. */
        axisRows?: Array<{
            key: string;
            label: string;
            settings: AxisScaleSettings;
        }>;
        /** Called when one contextual axis profile changes. */
        onaxischange?: (key: string, settings: AxisScaleSettings) => void;
        /** Fields that don't apply in current chart type — rendered greyed out and non-interactive */
        disabledFields?: Set<string>;
    }

    let {
        colorByBaseline = $bindable(true),
        areaFill = $bindable(true),
        gridLines = $bindable(true),
        staleGradient = $bindable(true),
        yAxisMode = $bindable<'auto' | 'include0' | 'custom'>('auto'),
        yAxisMin = $bindable<number | undefined>(),
        yAxisMax = $bindable<number | undefined>(),
        onchange,
        axisRows,
        onaxischange,
        disabledFields = new Set<string>(),
    }: Props = $props();

    // =========================================================================
    // Emit changes
    // =========================================================================

    function emitChange() {
        onchange?.({colorByBaseline, areaFill, gridLines, staleGradient, yAxisMode, yAxisMin, yAxisMax});
    }

    let effectiveAxisRows = $derived(
        axisRows?.length
            ? axisRows
            : [
                  {
                      key: 'legacy',
                      label: '',
                      settings: {
                          mode: yAxisMode,
                          min: yAxisMin,
                          max: yAxisMax,
                      },
                  },
              ],
    );

    function axisTestId(key: string): string {
        return key.replace(/[^a-zA-Z0-9_-]/g, '-').toLowerCase();
    }

    function updateAxis(key: string, current: AxisScaleSettings, patch: Partial<AxisScaleSettings>): void {
        const next = {...current, ...patch};
        if (key === 'legacy') {
            yAxisMode = next.mode;
            yAxisMin = next.min;
            yAxisMax = next.max;
            emitChange();
            return;
        }
        onaxischange?.(key, next);
    }
</script>

<div>
    <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">{$t('common.aesthetics')}</h3>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <!-- Color by baseline -->
        <div class="flex items-center justify-between gap-3 p-2.5 rounded-lg border border-gray-200 dark:border-slate-600 {disabledFields.has('colorByBaseline') ? 'opacity-40 pointer-events-none' : ''}">
            <span>
                <span class="block text-sm font-medium text-gray-700 dark:text-gray-200">{$t('chartSettings.baselineColors')}</span>
                <span class="block text-xs text-gray-500 dark:text-gray-400">{$t('chartSettings.baselineColorsDesc')}</span>
            </span>
            <button
                aria-label={$t('chartSettings.baselineColors')}
                data-testid="chart-aesthetic-baseline"
                aria-pressed={colorByBaseline}
                class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors {colorByBaseline ? 'bg-libre-green' : 'bg-gray-300 dark:bg-slate-600'}"
                disabled={disabledFields.has('colorByBaseline')}
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
        <div class="flex items-center justify-between gap-3 p-2.5 rounded-lg border border-gray-200 dark:border-slate-600 {disabledFields.has('areaFill') ? 'opacity-40 pointer-events-none' : ''}">
            <span>
                <span class="block text-sm font-medium text-gray-700 dark:text-gray-200">{$t('chartSettings.areaFill')}</span>
                <span class="block text-xs text-gray-500 dark:text-gray-400">{$t('chartSettings.areaFillDesc')}</span>
            </span>
            <button
                aria-label={$t('chartSettings.areaFill')}
                data-testid="chart-aesthetic-area-fill"
                aria-pressed={areaFill}
                class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors {areaFill ? 'bg-libre-green' : 'bg-gray-300 dark:bg-slate-600'}"
                disabled={disabledFields.has('areaFill')}
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
                data-testid="chart-aesthetic-grid-lines"
                aria-pressed={gridLines}
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
        <div class="flex items-center justify-between gap-3 p-2.5 rounded-lg border border-gray-200 dark:border-slate-600 {disabledFields.has('staleGradient') ? 'opacity-40 pointer-events-none' : ''}">
            <span>
                <span class="block text-sm font-medium text-gray-700 dark:text-gray-200">{$t('chartSettings.staleGradient')}</span>
                <span class="block text-xs text-gray-500 dark:text-gray-400">{$t('chartSettings.staleGradientDesc')}</span>
            </span>
            <button
                aria-label={$t('chartSettings.staleGradient')}
                data-testid="chart-aesthetic-stale-gradient"
                aria-pressed={staleGradient}
                class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors {staleGradient ? 'bg-libre-green' : 'bg-gray-300 dark:bg-slate-600'}"
                disabled={disabledFields.has('staleGradient')}
                onclick={() => {
                    staleGradient = !staleGradient;
                    emitChange();
                }}
                type="button"
            >
                <span class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {staleGradient ? 'translate-x-6' : 'translate-x-1'}"></span>
            </button>
        </div>

        <!-- Contextual Y-axis scale modes -->
        <div class="p-2.5 rounded-lg border border-gray-200 dark:border-slate-600 sm:col-span-2 space-y-2">
            <span>
                <span class="block text-sm font-medium text-gray-700 dark:text-gray-200">{$t('chartSettings.yAxisScale')}</span>
                <span class="block text-xs text-gray-500 dark:text-gray-400">{$t('chartSettings.yAxisScaleDesc')}</span>
            </span>
            <div class="space-y-2">
                {#each effectiveAxisRows as row (row.key)}
                    <div class="flex items-center justify-between gap-3 flex-wrap" data-testid={`chart-axis-row-${axisTestId(row.key)}`}>
                        {#if row.label}
                            <span class="text-xs font-medium text-gray-600 dark:text-gray-300">{row.label}</span>
                        {/if}
                        <div class="flex items-center gap-2 flex-wrap {row.label ? '' : 'ml-auto'}">
                            <div class="flex rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
                                {#each ['auto', 'include0', 'custom'] as mode}
                                    <button
                                        class="px-2.5 py-1 text-[10px] font-medium transition-colors {row.settings.mode === mode ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                                        data-testid={`chart-axis-${axisTestId(row.key)}-${mode}`}
                                        aria-pressed={row.settings.mode === mode}
                                        onclick={() => updateAxis(row.key, row.settings, {mode: mode as AxisScaleMode})}
                                        type="button"
                                    >
                                        {mode === 'auto' ? 'Auto' : mode === 'include0' ? $t('chartSettings.yAxisInclude0') : $t('common.custom')}
                                    </button>
                                {/each}
                            </div>
                            {#if row.settings.mode === 'custom'}
                                <div class="flex items-center gap-1.5 text-sm sm:text-xs">
                                    <span class="text-xs sm:text-[10px] text-gray-500 dark:text-gray-400">Min</span>
                                    <input
                                        type="number"
                                        use:numericArrows
                                        data-testid={`chart-axis-${axisTestId(row.key)}-min`}
                                        class="lf-compact-number-input w-20 px-1.5 py-0.5 border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 focus:ring-1 focus:ring-libre-green"
                                        step="any"
                                        value={row.settings.min ?? ''}
                                        oninput={(event) => {
                                            const value = event.currentTarget.value;
                                            updateAxis(row.key, row.settings, {
                                                min: value === '' ? undefined : Number(value),
                                            });
                                        }}
                                        placeholder="—"
                                    />
                                    <span class="text-xs sm:text-[10px] text-gray-500 dark:text-gray-400">Max</span>
                                    <input
                                        type="number"
                                        use:numericArrows
                                        data-testid={`chart-axis-${axisTestId(row.key)}-max`}
                                        class="lf-compact-number-input w-20 px-1.5 py-0.5 border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 focus:ring-1 focus:ring-libre-green"
                                        step="any"
                                        value={row.settings.max ?? ''}
                                        oninput={(event) => {
                                            const value = event.currentTarget.value;
                                            updateAxis(row.key, row.settings, {
                                                max: value === '' ? undefined : Number(value),
                                            });
                                        }}
                                        placeholder="—"
                                    />
                                </div>
                            {/if}
                        </div>
                    </div>
                {/each}
            </div>
        </div>
    </div>
</div>
