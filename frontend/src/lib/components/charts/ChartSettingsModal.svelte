<!--
  ChartSettingsModal — Modal for configuring chart aesthetics and overlay signals.

  Thin wrapper around:
  - ChartAestheticsSection (toggles + Y-axis mode)
  - ChartSignalsSection (add/remove/reorder overlay signals)
  - Preview chart (LineChart with live rendering)

  Both sections are also used standalone in the FX detail page (inline foldable panels).

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {Settings, X} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import {ConfirmModal} from '$lib/components/table';
    import type {LineDataPoint} from './LineChart.svelte';
    import LineChart from './LineChart.svelte';
    import ChartAestheticsSection from './ChartAestheticsSection.svelte';
    import ChartSignalsSection from './ChartSignalsSection.svelte';
    import type {ChartSettings} from '$lib/stores/chartSettingsStore.svelte';
    import {type RenderedSignal, type SignalConfig, signalFromConfig,} from '$lib/charts/signals';
    import {SineSignal} from '$lib/charts/signals/SineSignal';
    import {normalizeToPercentage} from '$lib/utils/chartUtils';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        open?: boolean;
        /** Current settings to edit */
        settings: ChartSettings;
        /** 'global' = filter bar, 'pair' = per-card/detail */
        mode?: 'global' | 'pair';
        /** Available FX pairs for FxPairSignal dynamic options (slug format: 'EUR-GBP') */
        availablePairs?: string[];
        /** Available assets for AssetComparisonSignal dynamic options */
        availableAssets?: Array<{id: number, display_name: string, icon_url?: string | null, asset_type?: string | null}>;
        /** Pair-specific data for preview chart (used in pair mode). If omitted, uses synthetic demo data. */
        pairData?: LineDataPoint[];
        /** Map of pair slug → data points for resolving FxPairSignal data in preview */
        pairsDataMap?: Record<string, LineDataPoint[]>;
        /** Map of asset ID → data points for resolving AssetComparisonSignal data in preview */
        assetsDataMap?: Record<string, LineDataPoint[]>;
        /** Called when user saves */
        onsave?: (settings: ChartSettings) => void;
        /** Called when user closes without saving */
        onclose?: () => void;
    }

    let {
        open = $bindable(false),
        settings,
        mode = 'global',
        availablePairs = [],
        availableAssets = [],
        pairData,
        pairsDataMap = {},
        assetsDataMap = {},
        onsave,
        onclose,
    }: Props = $props();

    // =========================================================================
    // Local editing state (cloned from props)
    // =========================================================================

    let colorByBaseline = $state(true);
    let areaFill = $state(true);
    let gridLines = $state(true);
    let staleGradient = $state(true);
    let yAxisMode = $state<'auto' | 'include0' | 'custom'>('auto');
    let yAxisMin = $state<number | undefined>(undefined);
    let yAxisMax = $state<number | undefined>(undefined);
    let signals = $state<SignalConfig[]>([]);

    // Reset local state when modal opens
    $effect(() => {
        if (open && settings) {
            colorByBaseline = settings.colorByBaseline;
            areaFill = settings.areaFill;
            gridLines = settings.gridLines;
            staleGradient = settings.staleGradient;
            yAxisMode = settings.yAxisMode ?? 'auto';
            yAxisMin = settings.yAxisMin;
            yAxisMax = settings.yAxisMax;
            signals = JSON.parse(JSON.stringify(settings.signals));
        }
    });

    // =========================================================================
    // Save / Close
    // =========================================================================

    function deepClone<T>(obj: T): T {
        return JSON.parse(JSON.stringify(obj));
    }

    function isDirty(): boolean {
        if (!settings) return false;
        if (colorByBaseline !== settings.colorByBaseline) return true;
        if (areaFill !== settings.areaFill) return true;
        if (gridLines !== settings.gridLines) return true;
        if (staleGradient !== settings.staleGradient) return true;
        if (yAxisMode !== (settings.yAxisMode ?? 'auto')) return true;
        if (yAxisMin !== settings.yAxisMin) return true;
        if (yAxisMax !== settings.yAxisMax) return true;
        if (JSON.stringify(signals) !== JSON.stringify(settings.signals)) return true;
        return false;
    }

    let confirmCloseOpen = $state(false);

    function handleSave() {
        let savedMin = yAxisMode === 'custom' ? yAxisMin : undefined;
        let savedMax = yAxisMode === 'custom' ? yAxisMax : undefined;
        if (savedMin !== undefined && savedMax !== undefined && savedMin > savedMax) {
            [savedMin, savedMax] = [savedMax, savedMin];
            yAxisMin = savedMin;
            yAxisMax = savedMax;
        }
        const result: ChartSettings = {
            colorByBaseline,
            areaFill,
            gridLines,
            staleGradient,
            yAxisMode,
            yAxisMin: savedMin,
            yAxisMax: savedMax,
            signals: deepClone(signals),
        };
        onsave?.(result);
        open = false;
    }

    function handleClose() {
        if (isDirty()) {
            confirmCloseOpen = true;
        } else {
            onclose?.();
            open = false;
        }
    }

    function confirmDiscardAndClose() {
        confirmCloseOpen = false;
        onclose?.();
        open = false;
    }

    // =========================================================================
    // Preview chart data
    // =========================================================================

    let previewViewMode = $state<'absolute' | 'percentage'>('percentage');

    function generateSyntheticData(): LineDataPoint[] {
        const baseDates: LineDataPoint[] = [];
        const today = new Date();
        const DAYS = 365;
        for (let i = 0; i < DAYS; i++) {
            const d = new Date(today);
            d.setDate(d.getDate() - (DAYS - 1 - i));
            baseDates.push({date: d.toISOString().slice(0, 10), value: 1.0});
        }
        const sineInstance = new SineSignal(
            'demo-sine',
            {color: '#000', lineWidth: 2, lineType: 'solid', markerStart: null, markerEnd: null},
            {amplitude: 20, period: 120, offset: 0},
        );
        const points = sineInstance.computePoints(baseDates);
        const stalePatches = [
            {start: 80, days: Array.from({length: 20}, (_, i) => i + 1)},
            {start: 220, days: Array.from({length: 10}, (_, i) => i + 1)},
        ];
        for (const patch of stalePatches) {
            const lastFreshValue = patch.start > 0 ? points[patch.start - 1].value : points[0].value;
            for (let j = 0; j < patch.days.length && (patch.start + j) < points.length; j++) {
                const idx = patch.start + j;
                points[idx] = {...points[idx], value: lastFreshValue, staleDays: patch.days[j]};
            }
        }
        return points;
    }

    const syntheticData = generateSyntheticData();

    let previewDataAbs = $derived(
        mode === 'pair' && pairData && pairData.length > 0 ? pairData : syntheticData
    );

    let previewData = $derived.by((): LineDataPoint[] => {
        if (previewViewMode !== 'percentage' || previewDataAbs.length === 0) return previewDataAbs;
        return normalizeToPercentage(previewDataAbs);
    });

    let previewSignals = $derived.by((): RenderedSignal[] => {
        if (signals.length === 0) return [];
        const rendered: RenderedSignal[] = [];
        for (const cfg of signals) {
            const instance = signalFromConfig(cfg);
            if (!instance) continue;
            if (cfg.signalType === 'fx-pair') {
                const pairSlug = String(cfg.params.pairSlug || '');
                if (!pairSlug) continue;
                const resolvedData = pairsDataMap[pairSlug];
                if (!resolvedData || resolvedData.length === 0) continue;
                instance.params._resolvedData = resolvedData;
            }
            if (cfg.signalType === 'asset-comparison') {
                const targetId = String(cfg.params.assetId || '');
                if (!targetId) continue;
                const resolvedData = assetsDataMap[targetId];
                if (!resolvedData || resolvedData.length === 0) continue;
                instance.params._resolvedData = resolvedData;
            }
            const results = instance.renderMulti(previewDataAbs, previewViewMode);
            for (const result of results) {
                if (result.data.length > 0) rendered.push(result);
            }
        }
        return rendered;
    });
</script>

<ModalBase
        bind:open
        maxWidth="3xl"
        onRequestClose={handleClose}
        testId="chart-settings-modal"
>
    <div class="flex flex-col max-h-[85vh]">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-slate-700">
            <div class="flex items-center gap-2">
                <Settings class="text-libre-green" size={20}/>
                <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">
                    {mode === 'global' ? $t('chartSettings.title') : $t('chartSettings.titleLocal')}
                </h2>
            </div>
            <button
                    class="p-1 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
                    onclick={handleClose}
                    type="button"
            >
                <X size={18}/>
            </button>
        </div>

        <!-- Scrollable content -->
        <div class="flex-1 overflow-y-auto px-6 py-4 space-y-6">
            <!-- Global override warning -->
            {#if mode === 'global'}
                <InfoBanner variant="warning">
                    {$t('chartSettings.globalWarning')}
                </InfoBanner>
            {/if}

            <!-- Aesthetics Section (extracted component) -->
            <ChartAestheticsSection
                    bind:areaFill
                    bind:colorByBaseline
                    bind:gridLines
                    bind:staleGradient
                    bind:yAxisMax
                    bind:yAxisMin
                    bind:yAxisMode
            />

            <!-- Preview Chart -->
            <div>
                <div class="flex items-center justify-between mb-2">
                    <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300">{$t('chartSettings.preview')}</h3>
                    <div class="flex rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
                        <button
                                class="px-2.5 py-1 text-[10px] font-medium transition-colors {previewViewMode === 'absolute' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                                onclick={() => previewViewMode = 'absolute'}
                                type="button"
                        >Abs
                        </button>
                        <button
                                class="px-2.5 py-1 text-[10px] font-medium transition-colors {previewViewMode === 'percentage' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                                onclick={() => previewViewMode = 'percentage'}
                                type="button"
                        >%
                        </button>
                    </div>
                </div>
                <div class="rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden bg-gray-50 dark:bg-slate-800/50">
                    <LineChart
                            areaFill={areaFill}
                            colorByBaseline={colorByBaseline}
                            compact={false}
                            currency={mode === 'pair' && pairData && pairData.length > 0 ? '' : 'Preview'}
                            data={previewData}
                            height="140px"
                            overlaySignals={previewSignals}
                            showGradient={staleGradient}
                            showGridLines={gridLines}
                            showMiniAxis={false}
                            viewMode={previewViewMode}
                            yAxisMax={yAxisMax}
                            yAxisMin={yAxisMin}
                            yAxisMode={yAxisMode}
                    />
                </div>
                <p class="text-[10px] text-gray-400 dark:text-gray-500 mt-1 italic">
                    {mode === 'global' ? $t('chartSettings.previewDescGlobal') : $t('chartSettings.previewDescPair')}
                </p>
            </div>

            <!-- Signals Section (extracted component) -->
            <ChartSignalsSection
                    {availablePairs}
                    {availableAssets}
                    bind:signals
            />
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-end gap-2 px-6 py-4 border-t border-gray-100 dark:border-slate-700">
            <button
                    class="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-slate-700 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
                    onclick={handleClose}
                    type="button"
            >
                {$t('common.cancel')}
            </button>
            <button
                    class="px-4 py-2 text-sm font-medium text-white bg-libre-green rounded-lg hover:bg-libre-green/90 transition-colors"
                    onclick={handleSave}
                    type="button"
            >
                {$t('chartSettings.apply')}
            </button>
        </div>
    </div>
</ModalBase>

<!-- Confirm discard changes -->
<ConfirmModal
        confirmText={$t('chartSettings.discard')}
        danger={false}
        message={$t('chartSettings.discardMessage')}
        onCancel={() => { confirmCloseOpen = false; }}
        onConfirm={confirmDiscardAndClose}
        open={confirmCloseOpen}
        title={$t('chartSettings.discardTitle')}
        warning={true}
        zIndex={70}
/>
