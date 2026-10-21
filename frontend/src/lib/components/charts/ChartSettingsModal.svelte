<!--
  ChartSettingsModal — Modal for configuring chart aesthetics and overlay signals.

  Thin wrapper around:
  - ChartAestheticsSection (toggles + Y-axis mode)
  - ChartSignalsSection (add/remove/reorder overlay signals)
  - Preview chart (PriceChartFull, the detail pages' chart, with live rendering)

  Both sections are also used standalone in the FX detail page (inline foldable panels).

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {CalendarSync, Settings, X} from 'lucide-svelte';
    import {untrack} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import {ConfirmModal} from '$lib/components/table';
    import type {LineDataPoint} from './LineChart.svelte';
    import PriceChartFull from './PriceChartFull.svelte';
    import ChartAestheticsSection from './ChartAestheticsSection.svelte';
    import ChartSignalsSection from './ChartSignalsSection.svelte';
    import {DEFAULT_AXIS_SCALE, DEFAULT_CHART_SETTINGS, DEFAULT_PERCENTAGE_AXIS_SCALE, effectiveCalendarReturnWindow, normalizeAxisScaleSettings, type AxisScaleSettings, type ChartAxisSettings, type ChartPrimaryView, type ChartSettings} from '$lib/stores/chartSettingsStore.svelte';
    import {calendarReturnWindowDays, type CalendarReturnPresetKey, type CalendarReturnWindowSelection, type CalendarReturnWindowUnit} from './calendarReturnWindow';
    import AssetCalendarWindowControls from '$lib/components/assets/detail/AssetCalendarWindowControls.svelte';
    import {collectConfigurableSecondaryAxes} from './chartCoreHelpers';
    import {exchangeRateAxisLabel, percentageAxisLabel, priceAxisLabel, secondaryAxisLabel} from './axisLabelHelpers';
    import {getRegisteredSignalTypes, resolveSignalPreview, type RenderedSignal, type SignalConfig, type SignalDefinition} from '$lib/charts/signals';
    import {NO_SIGNAL_SOURCES, renderLocalSignal, type SignalDataSources} from '$lib/charts/chartSignalRendering';
    import {SineSignal} from '$lib/charts/signals/SineSignal';
    import {buildOverlaySignalInfoMap} from '$lib/charts/signalLabel';

    /** The days of the global preview's synthetic curve. */
    const SYNTHETIC_DAYS = 365;

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        open?: boolean;
        /** Current settings to edit */
        settings: ChartSettings;
        /** 'global' = filter bar, 'pair' = per-card/detail */
        mode?: 'global' | 'pair';
        /** Selects the semantic primary-axis label used by the shared preview. */
        axisDomain?: 'asset' | 'fx';
        /** Currency or displayed FX pair used to contextualize the primary axis. */
        axisContext?: string;
        /** Available FX pairs for FxPairSignal dynamic options (slug format: 'EUR-GBP') */
        availablePairs?: string[];
        /** Available assets for AssetComparisonSignal dynamic options */
        availableAssets?: Array<{id: number; display_name: string; icon_url?: string | null; asset_type?: string | null}>;
        /** Definitions available in the current Asset/FX domain. */
        signalDefinitions?: SignalDefinition[];
        /** Last applied backend signal rendering supplied by the current page. */
        backendPreviewSignals?: RenderedSignal[];
        /** Resolve latest backend preview for the modal's active view mode. */
        backendPreviewSignalResolver?: (viewMode: 'absolute' | 'percentage') => RenderedSignal[];
        /**
         * Global mode only: compute backend signals live on the synthetic preview
         * curve (backend indicators can't run in the browser). Returns rendered
         * overlay signals for the given live-edited configs.
         */
        backendPreviewLiveResolver?: (configs: SignalConfig[], points: LineDataPoint[], viewMode: 'absolute' | 'percentage') => Promise<RenderedSignal[]>;
        /** Explicit backend signal loading error. */
        signalBackendError?: string | null;
        /** Retry backend catalog/result loading. */
        onretrySignalBackend?: () => void;
        /** True while a backend signal request is in flight (forwarded to the
         *  signals section — suppresses the transient red state on the cards). */
        signalsLoading?: boolean;
        /** Pair-specific data for preview chart (used in pair mode). If omitted, uses synthetic demo data. */
        pairData?: LineDataPoint[];
        /**
         * Where the preview's FX pair and comparison signals get their series: the same sources the cards use, so the
         * preview draws them as the card does (Y-39a). Omitted: those signals are not drawn.
         */
        signalSources?: SignalDataSources;
        /** The days of the period on screen: while the rolling-return window is automatic, the largest preset that fits them (Y-40). */
        calendarRangeDays?: number;
        /**
         * The rolling return of the preview (Y-40): the page computes it over `windowDays` on `points` (the card's data, or the
         * synthetic curve lengthened by the window), with the comparisons of `configs`. Omitted: no rolling-return view.
         */
        calendarPreviewResolver?: (windowDays: number, configs: SignalConfig[], points: LineDataPoint[]) => Promise<{points: LineDataPoint[]; overlays: RenderedSignal[]} | null>;
        /** Called when user saves */
        onsave?: (settings: ChartSettings) => void;
        /** Called when user closes without saving */
        onclose?: () => void;
    }

    let {
        open = false,
        settings,
        mode = 'global',
        axisDomain = 'asset',
        axisContext = '',
        availablePairs = [],
        availableAssets = [],
        signalDefinitions,
        backendPreviewSignals = [],
        backendPreviewSignalResolver,
        backendPreviewLiveResolver,
        signalBackendError = null,
        signalsLoading = false,
        onretrySignalBackend,
        pairData,
        signalSources = NO_SIGNAL_SOURCES,
        calendarRangeDays = SYNTHETIC_DAYS,
        calendarPreviewResolver,
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
    let axisScales: ChartAxisSettings = $state(deepClone(DEFAULT_CHART_SETTINGS.axisScales));
    let signals: SignalConfig[] = $state([]);
    /** The view of the preview: the saved view of the chart, which Apply saves (Y-40, V-3 a). */
    let previewView: ChartPrimaryView = $state(untrack(() => openingView(settings)));
    let calendarWindow: CalendarReturnWindowSelection = $state(deepClone(DEFAULT_CHART_SETTINGS.calendarReturnWindow));
    let calendarWindowAuto = $state(true);
    let calendarCustomAmount = $state(DEFAULT_CHART_SETTINGS.calendarReturnWindow.customAmount);
    let calendarCustomUnit: CalendarReturnWindowUnit = $state(DEFAULT_CHART_SETTINGS.calendarReturnWindow.customUnit);
    let calendarCustomEditing = $state(false);

    // Reset local state when modal opens
    $effect(() => {
        if (open && settings) {
            previewView = openingView(settings);
            calendarWindow = deepClone(settings.calendarReturnWindow);
            calendarWindowAuto = settings.calendarReturnWindowAuto;
            calendarCustomAmount = settings.calendarReturnWindow.customAmount;
            calendarCustomUnit = settings.calendarReturnWindow.customUnit;
            calendarCustomEditing = false;
            colorByBaseline = settings.colorByBaseline;
            areaFill = settings.areaFill;
            gridLines = settings.gridLines;
            staleGradient = settings.staleGradient;
            axisScales = deepClone(settings.axisScales);
            signals = JSON.parse(JSON.stringify(settings.signals));
        }
    });

    /** The view the preview opens on: the saved one; the rolling return only where it is offered (the asset charts). */
    function openingView(saved: ChartSettings | undefined): ChartPrimaryView {
        const view = saved?.primaryView ?? 'percentage';
        return view === 'calendar-return' && axisDomain !== 'asset' ? 'percentage' : view;
    }

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
        if (JSON.stringify(axisScales) !== JSON.stringify(settings.axisScales)) return true;
        if (JSON.stringify(signals) !== JSON.stringify(settings.signals)) return true;
        if (previewView !== settings.primaryView) return true;
        if (calendarWindowAuto !== settings.calendarReturnWindowAuto || JSON.stringify(calendarWindow) !== JSON.stringify(settings.calendarReturnWindow)) return true;
        return false;
    }

    let confirmCloseOpen = $state(false);

    function normalizedAxisScales(): ChartAxisSettings {
        return {
            absolute: normalizeAxisScaleSettings(axisScales.absolute, DEFAULT_AXIS_SCALE),
            percentage: normalizeAxisScaleSettings(axisScales.percentage, DEFAULT_PERCENTAGE_AXIS_SCALE),
            secondary: Object.fromEntries(Object.entries(axisScales.secondary).map(([key, scale]) => [key, normalizeAxisScaleSettings(scale, DEFAULT_AXIS_SCALE)])),
        };
    }

    function handleAxisChange(key: string, scale: AxisScaleSettings): void {
        if (key === 'primary:absolute') {
            axisScales = {...axisScales, absolute: {...scale}};
        } else if (key === 'primary:percentage') {
            axisScales = {...axisScales, percentage: {...scale}};
        } else {
            axisScales = {
                ...axisScales,
                secondary: {...axisScales.secondary, [key]: {...scale}},
            };
        }
    }

    function handleSave() {
        const result: ChartSettings = {
            colorByBaseline,
            areaFill,
            gridLines,
            staleGradient,
            axisScales: normalizedAxisScales(),
            calendarReturnWindow: deepClone(calendarWindow),
            calendarReturnWindowAuto: calendarWindowAuto,
            primaryView: previewView,
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
        }
    }

    function confirmDiscardAndClose() {
        confirmCloseOpen = false;
        onclose?.();
    }

    // =========================================================================
    // Preview chart data
    // =========================================================================

    /** The price view under the preview: the rolling return has the percentage one under it, as on the detail page. */
    let previewViewMode: 'absolute' | 'percentage' = $derived(previewView === 'absolute' ? 'absolute' : 'percentage');
    let previewIsCalendar = $derived(previewView === 'calendar-return');

    function generateSyntheticData(DAYS: number = SYNTHETIC_DAYS): LineDataPoint[] {
        const baseDates: LineDataPoint[] = [];
        const today = new Date();
        for (let i = 0; i < DAYS; i++) {
            const d = new Date(today);
            d.setDate(d.getDate() - (DAYS - 1 - i));
            baseDates.push({date: d.toISOString().slice(0, 10), value: 1.0});
        }
        const sineInstance = new SineSignal('demo-sine', {color: '#000', lineWidth: 2, lineType: 'solid', markerStart: null, markerEnd: null}, {amplitude: 20, period: 120, offset: 0});
        const points = sineInstance.computePoints(baseDates);
        const stalePatches = [
            {start: 80, days: Array.from({length: 20}, (_, i) => i + 1)},
            {start: 220, days: Array.from({length: 10}, (_, i) => i + 1)},
        ];
        for (const patch of stalePatches) {
            const lastFreshValue = patch.start > 0 ? points[patch.start - 1].value : points[0].value;
            for (let j = 0; j < patch.days.length && patch.start + j < points.length; j++) {
                const idx = patch.start + j;
                points[idx] = {...points[idx], value: lastFreshValue, staleDays: patch.days[j]};
            }
        }
        return points;
    }

    const syntheticData = generateSyntheticData();

    // =========================================================================
    // The rolling-return preview (Y-40)
    // =========================================================================

    let effectiveWindow = $derived(effectiveCalendarReturnWindow({calendarReturnWindow: calendarWindow, calendarReturnWindowAuto: calendarWindowAuto}, calendarRangeDays));
    let calendarWindowDays = $derived(calendarReturnWindowDays(effectiveWindow) ?? 30);
    let calendarPreview = $state<{state: 'idle' | 'loading' | 'ready' | 'error'; points: LineDataPoint[]; overlays: RenderedSignal[]}>({state: 'idle', points: [], overlays: []});
    let calendarPreviewToken = 0;
    /** A comparison changed asks the return again; any other edit does not. */
    let calendarComparisonFingerprint = $derived(JSON.stringify(signals.filter((config) => config.signalType === 'asset-comparison').map((config) => config.params.assetId)));

    function chooseCalendarPreset(preset: CalendarReturnPresetKey): void {
        calendarCustomEditing = false;
        calendarWindow = {...calendarWindow, kind: 'preset', preset};
        calendarWindowAuto = false;
    }

    function chooseCalendarCustom(customAmount: number, customUnit: CalendarReturnWindowUnit): void {
        const selection: CalendarReturnWindowSelection = {...calendarWindow, kind: 'custom', customAmount, customUnit};
        if (calendarReturnWindowDays(selection) === null) return;
        calendarWindow = selection;
        calendarWindowAuto = false;
    }

    $effect(() => {
        const active = open && previewIsCalendar && !!calendarPreviewResolver;
        const windowDays = calendarWindowDays;
        void calendarComparisonFingerprint;
        // The global preview's year has a return from its first day: the curve starts a window earlier.
        const points = mode === 'global' || !pairData?.length ? generateSyntheticData(SYNTHETIC_DAYS + windowDays) : pairData;
        if (!active) {
            calendarPreview = {state: 'idle', points: [], overlays: []};
            return;
        }
        const resolver = calendarPreviewResolver!;
        const configs = untrack(() => deepClone(signals));
        const firstShown = mode === 'global' || !pairData?.length ? syntheticData[0].date : null;
        const token = ++calendarPreviewToken;
        calendarPreview = {...untrack(() => calendarPreview), state: 'loading'};
        resolver(windowDays, configs, points)
            .then((result) => {
                if (token !== calendarPreviewToken) return;
                if (!result) {
                    calendarPreview = {state: 'error', points: [], overlays: []};
                    return;
                }
                const shown = firstShown ? result.points.filter((point) => point.date >= firstShown) : result.points;
                calendarPreview = {state: 'ready', points: shown, overlays: result.overlays};
            })
            .catch(() => {
                if (token !== calendarPreviewToken) return;
                calendarPreview = {state: 'error', points: [], overlays: []};
            });
    });

    let previewDataAbs = $derived(mode === 'pair' && pairData && pairData.length > 0 ? pairData : syntheticData);

    let activeSignalDefinitions = $derived(signalDefinitions ?? getRegisteredSignalTypes());

    // =========================================================================
    // Global-mode live backend preview (compute indicators on the synthetic curve)
    // =========================================================================

    let backendLivePreviewSignals = $state<RenderedSignal[]>([]);
    let backendLivePreviewError = $state(false);
    let livePreviewToken = 0;

    let globalLivePreviewActive = $derived(mode === 'global' && !!backendPreviewLiveResolver);

    // Fingerprint of the backend-source configs only, so aesthetics / local-signal
    // edits don't trigger a backend recompute.
    let backendConfigFingerprint = $derived.by(() => {
        const defs = new Map(activeSignalDefinitions.map((definition) => [definition.type, definition]));
        const backend = signals.filter((config) => defs.get(config.signalType)?.source === 'backend');
        return JSON.stringify(backend.map((config) => ({id: config.id, type: config.signalType, params: config.params})));
    });

    $effect(() => {
        // Reactive deps: recompute when the modal opens, the backend configs
        // change, the preview data changes, or the view mode toggles.
        const fingerprint = backendConfigFingerprint;
        const points = previewDataAbs;
        const viewMode = previewViewMode;
        const active = open && globalLivePreviewActive && !previewIsCalendar;

        if (!active || fingerprint === '[]' || points.length === 0) {
            backendLivePreviewSignals = [];
            backendLivePreviewError = false;
            return;
        }

        const resolver = backendPreviewLiveResolver!;
        const configsSnapshot = untrack(() => signals.map((config) => ({...config, params: {...config.params}})));
        const token = ++livePreviewToken;
        const timer = setTimeout(() => {
            resolver(configsSnapshot, points, viewMode)
                .then((result) => {
                    if (token !== livePreviewToken) return;
                    backendLivePreviewSignals = result;
                    backendLivePreviewError = false;
                })
                .catch(() => {
                    if (token !== livePreviewToken) return;
                    backendLivePreviewSignals = [];
                    backendLivePreviewError = true;
                });
        }, 250);
        return () => clearTimeout(timer);
    });

    function renderLocalPreview(cfg: SignalConfig): RenderedSignal[] {
        return renderLocalSignal(cfg, previewDataAbs, previewViewMode, signalSources);
    }

    let previewResolution = $derived.by(() => {
        return resolveSignalPreview({
            configs: signals,
            definitions: activeSignalDefinitions,
            mode,
            backendSignals: globalLivePreviewActive ? backendLivePreviewSignals : (backendPreviewSignalResolver?.(previewViewMode) ?? backendPreviewSignals),
            renderLocal: renderLocalPreview,
            globalLivePreview: globalLivePreviewActive,
            backendError: globalLivePreviewActive ? backendLivePreviewError : false,
        });
    });
    let previewSignals = $derived(previewResolution.signals);
    /** What the preview chart draws over its line: the comparisons' returns in the rolling-return view (V-5 a), else the signals. */
    let previewOverlays = $derived(previewIsCalendar ? calendarPreview.overlays : previewSignals);
    let previewSignalInfo = $derived(buildOverlaySignalInfoMap(previewOverlays));
    let previewPrimaryScale = $derived(previewViewMode === 'percentage' ? axisScales.percentage : axisScales.absolute);
    let previewPrimaryLabel = $derived.by(() => {
        const translate = (key: string, values?: Record<string, string>) => $t(key, {values});
        if (previewViewMode === 'percentage') return percentageAxisLabel(translate);
        const context = axisContext || $t('common.preview');
        return axisDomain === 'fx' ? exchangeRateAxisLabel(translate, context) : priceAxisLabel(translate, context);
    });
    let previewAxisRows = $derived([
        {
            key: `primary:${previewViewMode}`,
            label: previewPrimaryLabel,
            settings: previewPrimaryScale,
        },
        ...collectConfigurableSecondaryAxes(previewOverlays).map((axis) => ({
            key: axis.key,
            label: secondaryAxisLabel((key, values) => $t(key, {values}), axis),
            settings: axisScales.secondary[axis.key] ?? DEFAULT_AXIS_SCALE,
        })),
    ]);

    let backendPreviewMessageKey = $derived(
        previewResolution.backendState === 'real-target-required'
            ? 'chartSettings.backendPreviewRealTarget'
            : previewResolution.backendState === 'apply-required'
              ? 'chartSettings.backendPreviewApply'
              : previewResolution.backendState === 'unavailable'
                ? 'chartSettings.backendPreviewUnavailable'
                : null,
    );
</script>

<ModalBase {open} maxWidth="3xl" onRequestClose={handleClose} testId="chart-settings-modal">
    <div class="flex flex-col max-h-[85vh] text-lf-primary">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-lf-subtle">
            <div class="flex items-center gap-2">
                <Settings class="text-lf-link" size={20} />
                <h2 class="text-lg font-semibold text-lf-primary">
                    {mode === 'global' ? $t('chartSettings.title') : $t('chartSettings.titleLocal')}
                </h2>
            </div>
            <button class="p-1 rounded-lg text-lf-muted hover:text-lf-secondary hover:bg-lf-hover transition-colors" onclick={handleClose} type="button">
                <X size={18} />
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
            <ChartAestheticsSection bind:areaFill bind:colorByBaseline bind:gridLines bind:staleGradient axisRows={previewAxisRows} onaxischange={handleAxisChange} />

            <!-- Preview Chart -->
            <div>
                <div class="flex items-center justify-between mb-2">
                    <h3 class="text-sm font-semibold text-lf-secondary">{$t('common.preview')}</h3>
                    <div class="flex rounded-lg border border-lf-subtle overflow-hidden">
                        <button
                            class="px-2.5 py-1 text-[10px] font-medium transition-colors {previewView === 'absolute' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
                            data-testid="chart-settings-preview-view-absolute"
                            aria-pressed={previewView === 'absolute'}
                            onclick={() => (previewView = 'absolute')}
                            type="button"
                            >Abs
                        </button>
                        <button
                            class="px-2.5 py-1 text-[10px] font-medium transition-colors {previewView === 'percentage' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
                            data-testid="chart-settings-preview-view-percentage"
                            aria-pressed={previewView === 'percentage'}
                            onclick={() => (previewView = 'percentage')}
                            type="button"
                            >%
                        </button>
                        {#if axisDomain === 'asset' && calendarPreviewResolver}
                            <button
                                class="inline-flex items-center px-2.5 py-1 text-[10px] font-medium transition-colors {previewView === 'calendar-return' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
                                data-testid="chart-settings-preview-view-calendar-return"
                                aria-pressed={previewView === 'calendar-return'}
                                aria-label={$t('signals.riskRollingReturn.name')}
                                title={$t('signals.riskRollingReturn.name')}
                                onclick={() => (previewView = 'calendar-return')}
                                type="button"
                            >
                                <CalendarSync size={12} />
                            </button>
                        {/if}
                    </div>
                </div>
                {#if previewIsCalendar}
                    <div class="mb-2" data-testid="chart-settings-calendar-window" data-window-days={calendarWindowDays} data-window-auto={calendarWindowAuto ? 'true' : 'false'}>
                        <AssetCalendarWindowControls selection={effectiveWindow} bind:customAmount={calendarCustomAmount} bind:customUnit={calendarCustomUnit} bind:customEditing={calendarCustomEditing} onpreset={chooseCalendarPreset} oncustom={chooseCalendarCustom} />
                    </div>
                {/if}
                <div class="rounded-lg border border-lf-subtle overflow-hidden bg-lf-panel">
                    <!-- The detail pages' chart (Y-39b): absolute data, the view chosen above, the line only, no events, measure or edit -->
                    {#if previewIsCalendar && calendarPreview.points.length === 0}
                        <div class="h-[220px] flex items-center justify-center text-xs text-lf-muted" data-testid="chart-settings-calendar-preview-state" data-state={calendarPreview.state}>
                            {calendarPreview.state === 'error' ? $t('chartSettings.signalResultsUnavailable') : calendarPreview.state === 'loading' ? $t('common.loading') : $t('common.noData')}
                        </div>
                    {:else}
                        <PriceChartFull
                            {areaFill}
                            {colorByBaseline}
                            chartHeight="220px"
                            currency={mode === 'pair' && pairData && pairData.length > 0 ? '' : 'Preview'}
                            data={previewIsCalendar ? calendarPreview.points : previewDataAbs}
                            disableCandlestick={true}
                            externalChartType="line"
                            externalViewMode={previewIsCalendar ? 'absolute' : previewViewMode}
                            fxStaleLabel={$t('chart.tooltip.fxStale')}
                            hideToolbar={true}
                            hideViewModeToggle={true}
                            overlaySignalInfoMap={previewSignalInfo}
                            overlaySignals={previewOverlays}
                            showGradient={staleGradient}
                            showGridLines={gridLines}
                            showMainDelta={!previewIsCalendar}
                            staleLabel={$t('chart.tooltip.stale')}
                            valueUnit={previewIsCalendar ? 'percentage' : 'price'}
                            yAxisMax={previewPrimaryScale.max}
                            yAxisMin={previewPrimaryScale.min}
                            yAxisMode={previewPrimaryScale.mode}
                            secondaryAxisScales={axisScales.secondary}
                        />
                    {/if}
                </div>
                <p class="text-[10px] text-lf-muted mt-1 italic">
                    {mode === 'global' ? $t('chartSettings.previewDescGlobal') : $t('chartSettings.previewDescPair')}
                </p>
                {#if backendPreviewMessageKey}
                    <div class="mt-2" data-testid="backend-signal-preview-message">
                        <InfoBanner variant="info">
                            {$t(backendPreviewMessageKey)}
                        </InfoBanner>
                    </div>
                {/if}
            </div>

            <!-- Signals Section (extracted component) -->
            <ChartSignalsSection {availablePairs} {availableAssets} definitions={signalDefinitions} backendError={signalBackendError} onretrybackend={onretrySignalBackend} {signalsLoading} bind:signals />
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-end gap-2 px-6 py-4 border-t border-lf-subtle">
            <button class="px-4 py-2 text-sm font-medium text-lf-secondary bg-lf-panel rounded-lg hover:bg-lf-neutral transition-colors" onclick={handleClose} type="button">
                {$t('common.cancel')}
            </button>
            <button class="px-4 py-2 text-sm font-medium text-lf-on-action bg-lf-action rounded-lg hover:bg-lf-action-hover transition-colors" onclick={handleSave} type="button" data-testid="chart-settings-apply">
                {$t('common.apply')}
            </button>
        </div>
    </div>
</ModalBase>

<!-- Confirm discard changes -->
<ConfirmModal
    confirmText={$t('chartSettings.discard')}
    danger={false}
    message={$t('chartSettings.discardMessage')}
    onCancel={() => {
        confirmCloseOpen = false;
    }}
    onConfirm={confirmDiscardAndClose}
    open={confirmCloseOpen}
    title={$t('chartSettings.discardTitle')}
    warning={true}
    zIndex={70}
/>
