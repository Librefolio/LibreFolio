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
    import LineShapePicker from './LineShapePicker.svelte';
    import PreferenceSourceBadge from '$lib/components/ui/PreferenceSourceBadge.svelte';
    import Switch from '$lib/components/ui/input/Switch.svelte';
    import type {LineShape} from './lineShape';
    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        colorByBaseline?: boolean;
        areaFill?: boolean;
        gridLines?: boolean;
        staleGradient?: boolean;
        /** The shape of this chart's lines (FB-3). The row is shown only when the page passes `onlineshapechange`. */
        lineShape?: LineShape;
        /**
         * The chart has no shape of its own and the user none either: its lines follow the administrator's default, and the row
         * says so with a «Global» badge (lot UIP).
         */
        lineShapeFollowsGlobal?: boolean;
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
        /** Called when the user picks a shape. A page that keeps no per-chart shape leaves it out and the row is not shown. */
        onlineshapechange?: (shape: LineShape) => void;
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
        lineShape = 'segments',
        lineShapeFollowsGlobal = false,
        onlineshapechange,
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

<div class="text-lf-primary">
    <h3 class="text-sm font-semibold text-lf-secondary mb-3">{$t('common.aesthetics')}</h3>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <!-- Color by baseline -->
        <div class="flex items-center justify-between gap-3 p-2.5 rounded-lg border border-lf-subtle {disabledFields.has('colorByBaseline') ? 'opacity-40 pointer-events-none' : ''}">
            <span>
                <span class="block text-sm font-medium text-lf-secondary">{$t('chartSettings.baselineColors')}</span>
                <span class="block text-xs text-lf-muted">{$t('chartSettings.baselineColorsDesc')}</span>
            </span>
            <Switch
                semantics="pressed"
                class="shrink-0"
                dim={false}
                label={$t('chartSettings.baselineColors')}
                testId="chart-aesthetic-baseline"
                checked={colorByBaseline}
                disabled={disabledFields.has('colorByBaseline')}
                onchange={(next) => {
                    colorByBaseline = next;
                    emitChange();
                }}
            />
        </div>

        <!-- Area fill -->
        <div class="flex items-center justify-between gap-3 p-2.5 rounded-lg border border-lf-subtle {disabledFields.has('areaFill') ? 'opacity-40 pointer-events-none' : ''}">
            <span>
                <span class="block text-sm font-medium text-lf-secondary">{$t('chartSettings.areaFill')}</span>
                <span class="block text-xs text-lf-muted">{$t('chartSettings.areaFillDesc')}</span>
            </span>
            <Switch
                semantics="pressed"
                class="shrink-0"
                dim={false}
                label={$t('chartSettings.areaFill')}
                testId="chart-aesthetic-area-fill"
                checked={areaFill}
                disabled={disabledFields.has('areaFill')}
                onchange={(next) => {
                    areaFill = next;
                    emitChange();
                }}
            />
        </div>

        <!-- Grid lines -->
        <div class="flex items-center justify-between gap-3 p-2.5 rounded-lg border border-lf-subtle">
            <span>
                <span class="block text-sm font-medium text-lf-secondary">{$t('chartSettings.gridLines')}</span>
                <span class="block text-xs text-lf-muted">{$t('chartSettings.gridLinesDesc')}</span>
            </span>
            <Switch
                semantics="pressed"
                class="shrink-0"
                dim={false}
                label={$t('chartSettings.gridLines')}
                testId="chart-aesthetic-grid-lines"
                checked={gridLines}
                onchange={(next) => {
                    gridLines = next;
                    emitChange();
                }}
            />
        </div>

        <!-- Stale gradient -->
        <div class="flex items-center justify-between gap-3 p-2.5 rounded-lg border border-lf-subtle {disabledFields.has('staleGradient') ? 'opacity-40 pointer-events-none' : ''}">
            <span>
                <span class="block text-sm font-medium text-lf-secondary">{$t('chartSettings.staleGradient')}</span>
                <span class="block text-xs text-lf-muted">{$t('chartSettings.staleGradientDesc')}</span>
            </span>
            <Switch
                semantics="pressed"
                class="shrink-0"
                dim={false}
                label={$t('chartSettings.staleGradient')}
                testId="chart-aesthetic-stale-gradient"
                checked={staleGradient}
                disabled={disabledFields.has('staleGradient')}
                onchange={(next) => {
                    staleGradient = next;
                    emitChange();
                }}
            />
        </div>

        {#if onlineshapechange}
            <!-- Line shape (FB-3) -->
            <div class="flex items-center justify-between gap-3 p-2.5 rounded-lg border border-lf-subtle sm:col-span-2 flex-wrap" data-testid="chart-aesthetic-line-shape-row">
                <span>
                    <span class="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-medium text-lf-secondary">
                        <span>{$t('chartSettings.lineShape')}</span>
                        {#if lineShapeFollowsGlobal}
                            <PreferenceSourceBadge kind="global" testId="chart-aesthetic-line-shape-badge-global" />
                        {/if}
                    </span>
                    <span class="block text-xs text-lf-muted">{$t('chartSettings.lineShapeDesc')}</span>
                </span>
                <LineShapePicker value={lineShape} onchange={onlineshapechange} testIdPrefix="chart-aesthetic-line-shape" />
            </div>
        {/if}

        <!-- Contextual Y-axis scale modes -->
        <div class="p-2.5 rounded-lg border border-lf-subtle sm:col-span-2 space-y-2">
            <span>
                <span class="block text-sm font-medium text-lf-secondary">{$t('chartSettings.yAxisScale')}</span>
                <span class="block text-xs text-lf-muted">{$t('chartSettings.yAxisScaleDesc')}</span>
            </span>
            <div class="space-y-2">
                {#each effectiveAxisRows as row (row.key)}
                    <div class="flex items-center justify-between gap-3 flex-wrap" data-testid={`chart-axis-row-${axisTestId(row.key)}`}>
                        {#if row.label}
                            <span class="text-xs font-medium text-lf-secondary">{row.label}</span>
                        {/if}
                        <div class="flex items-center gap-2 flex-wrap {row.label ? '' : 'ml-auto'}">
                            <div class="flex rounded-lg border border-lf-subtle overflow-hidden">
                                {#each ['auto', 'include0', 'custom'] as mode}
                                    <button
                                        class="px-2.5 py-1 text-[10px] font-medium transition-colors {row.settings.mode === mode ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
                                        data-testid={`chart-axis-${axisTestId(row.key)}-${mode}`}
                                        aria-pressed={row.settings.mode === mode}
                                        onclick={() => updateAxis(row.key, row.settings, {mode: mode as AxisScaleMode})}
                                        type="button"
                                    >
                                        {mode === 'auto' ? $t('chartSettings.yAxisAuto') : mode === 'include0' ? $t('chartSettings.yAxisInclude0') : $t('common.custom')}
                                    </button>
                                {/each}
                            </div>
                            {#if row.settings.mode === 'custom'}
                                <div class="flex items-center gap-1.5 text-sm sm:text-xs">
                                    <span class="text-xs sm:text-[10px] text-lf-muted">{$t('common.min')}</span>
                                    <input
                                        type="number"
                                        use:numericArrows
                                        data-testid={`chart-axis-${axisTestId(row.key)}-min`}
                                        class="lf-compact-number-input w-20 px-1.5 py-0.5 border border-lf-input rounded bg-lf-field text-lf-primary placeholder:text-lf-placeholder hover:border-lf-input-hover focus:ring-1 focus:ring-lf-focus"
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
                                    <span class="text-xs sm:text-[10px] text-lf-muted">{$t('common.max')}</span>
                                    <input
                                        type="number"
                                        use:numericArrows
                                        data-testid={`chart-axis-${axisTestId(row.key)}-max`}
                                        class="lf-compact-number-input w-20 px-1.5 py-0.5 border border-lf-input rounded bg-lf-field text-lf-primary placeholder:text-lf-placeholder hover:border-lf-input-hover focus:ring-1 focus:ring-lf-focus"
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
