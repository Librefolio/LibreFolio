<!--
  ChartSettingsModal — Modal for configuring chart aesthetics and overlay signals.

  Features:
  - Aesthetics section: 4 toggles (colorByBaseline, areaFill, gridLines, staleGradient)
  - Signals section: OrderableList of signal overlays
    - Dynamic param rendering from SignalParamDescriptor[]
    - Style controls: color, lineWidth, lineType, arrowStart, arrowEnd
    - Add signal dropdown with all registered types
    - Remove signal per-row
  - Global mode: banner warning that overrides all per-card settings
  - Pair mode: only affects the specific pair
  - ModalBase wrapper with Svelte 5 runes

  Used by: FX list page (global), FxCard (pair), FX detail page (pair)
-->
<script lang="ts">
    import {X, Plus, Trash2, Settings} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import {ConfirmModal} from '$lib/components/table';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';
    import PriceChartCompact from '$lib/components/charts/PriceChartCompact.svelte';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import type {ChartSettings} from '$lib/stores/chartSettingsStore.svelte';
    import {
        type SignalConfig,
        type SignalStyle,
        type MarkerType,
        type RenderedSignal,
        getRegisteredSignalTypes,
        createSignal,
        signalFromConfig,
        type SignalTypeInfo,
    } from '$lib/charts/signals';

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
        /** Pair-specific data for preview chart (used in pair mode). If omitted, uses synthetic demo data. */
        pairData?: LineDataPoint[];
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
        pairData,
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
    let signals = $state<SignalConfig[]>([]);

    // Reset local state when modal opens
    $effect(() => {
        if (open && settings) {
            colorByBaseline = settings.colorByBaseline;
            areaFill = settings.areaFill;
            gridLines = settings.gridLines;
            staleGradient = settings.staleGradient;
            signals = JSON.parse(JSON.stringify(settings.signals));
        }
    });

    // =========================================================================
    // Signal types from registry
    // =========================================================================

    const signalTypes: SignalTypeInfo[] = getRegisteredSignalTypes();

    // =========================================================================
    // Signal management
    // =========================================================================

    function addSignal(type: string) {
        const signal = createSignal(type, signals.length);
        if (signal) {
            signals = [...signals, signal.toConfig()];
        }
    }

    function removeSignal(id: string) {
        signals = signals.filter(s => s.id !== id);
    }

    function handleSignalReorder(newSignals: SignalConfig[]) {
        signals = newSignals;
    }

    function updateSignalParam(id: string, key: string, value: unknown) {
        signals = signals.map(s =>
            s.id === id ? {...s, params: {...s.params, [key]: value}} : s
        );
    }

    function updateSignalStyle<K extends keyof SignalStyle>(id: string, key: K, value: SignalStyle[K]) {
        signals = signals.map(s =>
            s.id === id ? {...s, style: {...s.style, [key]: value}} : s
        );
    }

    // =========================================================================
    // Dynamic options resolution
    // =========================================================================

    function resolveDynamicOptions(dynamicKey: string): Array<{value: string; label: string}> {
        if (dynamicKey === 'configuredFxPairs') {
            return availablePairs.map(slug => ({
                value: slug,
                label: slug.replace('-', '/'),
            }));
        }
        return [];
    }

    // =========================================================================
    // Save / Close
    // =========================================================================

    /** Deep-clone that works with Svelte 5 proxy objects ($state) */
    function deepClone<T>(obj: T): T {
        return JSON.parse(JSON.stringify(obj));
    }

    /** Check if local state differs from initial settings */
    function isDirty(): boolean {
        if (!settings) return false;
        if (colorByBaseline !== settings.colorByBaseline) return true;
        if (areaFill !== settings.areaFill) return true;
        if (gridLines !== settings.gridLines) return true;
        if (staleGradient !== settings.staleGradient) return true;
        if (JSON.stringify(signals) !== JSON.stringify(settings.signals)) return true;
        return false;
    }

    // Confirm close state
    let confirmCloseOpen = $state(false);

    function handleSave() {
        const result: ChartSettings = {
            colorByBaseline,
            areaFill,
            gridLines,
            staleGradient,
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
    // Helpers
    // =========================================================================

    function getSignalTypeInfo(signalType: string): SignalTypeInfo | undefined {
        return signalTypes.find(t => t.type === signalType);
    }

    function getParamNumber(signal: SignalConfig, key: string, fallback: unknown): number {
        const v = signal.params[key];
        return typeof v === 'number' ? v : Number(fallback ?? 0);
    }

    function getParamString(signal: SignalConfig, key: string): string {
        const v = signal.params[key];
        return typeof v === 'string' ? v : '';
    }

    // =========================================================================
    // Marker cycling (click to cycle: null → arrow → circle → diamond → pin → null)
    // =========================================================================

    // =========================================================================
    // Marker types for 2×3 grid in unified popover
    // =========================================================================

    const MARKER_OPTIONS: (MarkerType | null)[] = [null, 'arrow', 'circle', 'diamond', 'rect', 'pin'];
    const MARKER_SYMBOLS_START: Record<string, string> = {
        arrow: '◁', circle: '●', diamond: '◆', rect: '■', pin: '📍',
    };
    const MARKER_SYMBOLS_END: Record<string, string> = {
        arrow: '▷', circle: '●', diamond: '◆', rect: '■', pin: '📍',
    };

    // =========================================================================
    // Unified style popover (one popover per signal with markers + line config)
    // =========================================================================

    let stylePopoverId = $state<string | null>(null);

    function toggleStylePopover(id: string) {
        stylePopoverId = stylePopoverId === id ? null : id;
    }

    function closeAllPopovers() {
        stylePopoverId = null;
    }

    // =========================================================================
    // Preview chart data — synthetic sinusoidal (global) or real pair data
    // =========================================================================

    /**
     * Generate synthetic sinusoidal demo data for the preview chart.
     * Sine wave oscillates around 1.0 with ±0.15 amplitude over 90 days,
     * showing both positive and negative zones relative to baseline.
     */
    function generateSyntheticData(): LineDataPoint[] {
        const points: LineDataPoint[] = [];
        const today = new Date();
        const DAYS = 90;
        for (let i = 0; i < DAYS; i++) {
            const d = new Date(today);
            d.setDate(d.getDate() - (DAYS - 1 - i));
            const t = i / DAYS;
            // Sine wave: ~2 full cycles, amplitude 0.15 around base 1.0
            const value = 1.0 + 0.15 * Math.sin(t * 4 * Math.PI);
            points.push({
                date: d.toISOString().slice(0, 10),
                value,
            });
        }
        return points;
    }

    const syntheticData = generateSyntheticData();

    /** Preview chart data: pair-specific if available, else synthetic */
    let previewData = $derived(
        mode === 'pair' && pairData && pairData.length > 0 ? pairData : syntheticData
    );

    /** Compute rendered overlay signals for the preview chart from current modal state */
    let previewSignals = $derived.by((): RenderedSignal[] => {
        if (signals.length === 0) return [];
        const rendered: RenderedSignal[] = [];
        for (const cfg of signals) {
            const instance = signalFromConfig(cfg);
            if (!instance) continue;
            // For FxPairSignal, we don't have resolved data in preview — skip
            if (cfg.signalType === 'fx-pair') continue;
            const result = instance.render(previewData, 'absolute');
            if (result.data.length > 0) {
                rendered.push(result);
            }
        }
        return rendered;
    });
</script>

<ModalBase
    bind:open
    maxWidth="xl"
    onRequestClose={handleClose}
    testId="chart-settings-modal"
>
    <div class="flex flex-col max-h-[85vh]">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-slate-700">
            <div class="flex items-center gap-2">
                <Settings size={20} class="text-libre-green" />
                <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">
                    {mode === 'global' ? $t('chartSettings.title') : $t('chartSettings.titleLocal')}
                </h2>
            </div>
            <button
                type="button"
                class="p-1 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
                onclick={handleClose}
            >
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

            <!-- Aesthetics Section -->
            <div>
                <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">{$t('chartSettings.aesthetics')}</h3>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <!-- Color by baseline -->
                    <div class="flex items-center justify-between gap-3 p-2.5 rounded-lg border border-gray-200 dark:border-slate-600">
                        <span>
                            <span class="block text-sm font-medium text-gray-700 dark:text-gray-200">{$t('chartSettings.baselineColors')}</span>
                            <span class="block text-xs text-gray-500 dark:text-gray-400">{$t('chartSettings.baselineColorsDesc')}</span>
                        </span>
                        <button
                            type="button"
                            class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors {colorByBaseline ? 'bg-libre-green' : 'bg-gray-300 dark:bg-slate-600'}"
                            onclick={() => { colorByBaseline = !colorByBaseline; }}
                            aria-label="Toggle baseline colors"
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
                            type="button"
                            class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors {areaFill ? 'bg-libre-green' : 'bg-gray-300 dark:bg-slate-600'}"
                            onclick={() => { areaFill = !areaFill; }}
                            aria-label="Toggle area fill"
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
                            type="button"
                            class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors {gridLines ? 'bg-libre-green' : 'bg-gray-300 dark:bg-slate-600'}"
                            onclick={() => { gridLines = !gridLines; }}
                            aria-label="Toggle grid lines"
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
                            type="button"
                            class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors {staleGradient ? 'bg-libre-green' : 'bg-gray-300 dark:bg-slate-600'}"
                            onclick={() => { staleGradient = !staleGradient; }}
                            aria-label="Toggle stale gradient"
                        >
                            <span class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {staleGradient ? 'translate-x-6' : 'translate-x-1'}"></span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- Preview Chart -->
            <div>
                <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">{$t('chartSettings.preview')}</h3>
                <div class="rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden bg-gray-50 dark:bg-slate-800/50">
                    <PriceChartCompact
                        data={previewData}
                        height="100px"
                        areaFill={areaFill}
                        colorByBaseline={colorByBaseline}
                        showGridLines={gridLines}
                        viewMode="percentage"
                        overlaySignals={previewSignals}
                    />
                </div>
                <p class="text-[10px] text-gray-400 dark:text-gray-500 mt-1 italic">
                    {mode === 'global' ? $t('chartSettings.previewDescGlobal') : $t('chartSettings.previewDescPair')}
                </p>
            </div>

            <!-- Signals Section -->
            <div>
                <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">{$t('chartSettings.overlaySignals')}</h3>

                {#if signals.length === 0}
                    <p class="text-xs text-gray-400 dark:text-gray-500 italic mb-3">
                        {$t('chartSettings.noSignals')}
                    </p>
                {:else}
                    <OrderableList
                        items={signals}
                        keyFn={(s) => s.id}
                        onReorder={handleSignalReorder}
                    >
                        {#snippet children({ item: signal, index })}
                            {@const typeInfo = getSignalTypeInfo(signal.signalType)}
                            <div class="space-y-2">
                                <!-- Signal header: icon + type name + remove button -->
                                <div class="flex items-center justify-between">
                                    <div class="flex items-center gap-2">
                                        <span class="text-sm">{typeInfo?.icon ?? '❓'}</span>
                                        <span class="text-xs font-medium text-gray-600 dark:text-gray-300">
                                            {typeInfo?.displayName ?? signal.signalType}
                                        </span>
                                    </div>
                                    <button
                                        type="button"
                                        class="p-1 rounded text-gray-400 hover:text-red-500 transition-colors"
                                        title={$t('chartSettings.removeSignal')}
                                        onclick={() => removeSignal(signal.id)}
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>

                                <!-- Type-specific parameters -->
                                {#if typeInfo && typeInfo.paramDescriptors.length > 0}
                                    <div class="flex flex-wrap gap-2">
                                        {#each typeInfo.paramDescriptors as desc}
                                            <div class="flex items-center gap-1.5">
                                                <span class="text-[10px] text-gray-500 dark:text-gray-400 uppercase">
                                                    {desc.label}
                                                </span>
                                                {#if desc.type === 'number'}
                                                    <div class="flex items-center gap-1">
                                                        <input
                                                            type="number"
                                                            value={getParamNumber(signal, desc.key, desc.default)}
                                                            min={desc.min}
                                                            max={desc.max}
                                                            step={desc.step}
                                                            class="w-16 px-1.5 py-0.5 text-xs border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 focus:ring-1 focus:ring-libre-green"
                                                            oninput={(e) => updateSignalParam(signal.id, desc.key, Number(e.currentTarget.value))}
                                                        />
                                                        {#if desc.suffix}
                                                            <span class="text-[10px] text-gray-400">{desc.suffix}</span>
                                                        {/if}
                                                    </div>
                                                {:else if desc.type === 'select'}
                                                    {@const options = desc.dynamicOptionsKey
                                                        ? resolveDynamicOptions(desc.dynamicOptionsKey)
                                                        : desc.options ?? []}
                                                    <select
                                                        class="px-1.5 py-0.5 text-xs border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 focus:ring-1 focus:ring-libre-green"
                                                        onchange={(e) => updateSignalParam(signal.id, desc.key, e.currentTarget.value)}
                                                    >
                                                        <option value="" selected={getParamString(signal, desc.key) === ''}>—</option>
                                                        {#each options as opt}
                                                            <option value={opt.value} selected={getParamString(signal, desc.key) === opt.value}>{opt.label}</option>
                                                        {/each}
                                                    </select>
                                                {:else}
                                                    <input
                                                        type="text"
                                                        value={getParamString(signal, desc.key)}
                                                        class="w-24 px-1.5 py-0.5 text-xs border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 focus:ring-1 focus:ring-libre-green"
                                                        oninput={(e) => updateSignalParam(signal.id, desc.key, e.currentTarget.value)}
                                                    />
                                                {/if}
                                            </div>
                                        {/each}
                                    </div>
                                {/if}

                                <!-- Row 3: Visual Style Strip — color + SVG preview (click opens unified popover) -->
                                <div class="flex items-center gap-1.5 pt-1.5 border-t border-gray-100 dark:border-slate-700">
                                    <!-- Color picker -->
                                    <input
                                        type="color"
                                        value={signal.style.color}
                                        class="w-6 h-6 p-0 border border-gray-200 dark:border-slate-600 rounded cursor-pointer shrink-0"
                                        title={$t('chartSettings.style.color')}
                                        oninput={(e) => updateSignalStyle(signal.id, 'color', e.currentTarget.value)}
                                    />

                                    <!-- SVG live preview — click to open unified popover -->
                                    <div class="flex-1 relative">
                                        <button
                                            type="button"
                                            class="w-full h-7 flex items-center cursor-pointer rounded hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors relative"
                                            title={$t('chartSettings.style.lineType')}
                                            onclick={() => toggleStylePopover(signal.id)}
                                        >
                                            <!-- Start marker (absolute left) -->
                                            <svg class="absolute left-0 top-1/2 -translate-y-1/2 overflow-visible" width="16" height="24">
                                                {#if signal.style.markerStart === 'arrow'}
                                                    <polygon points="12,5 4,12 12,19" fill={signal.style.color} />
                                                {:else if signal.style.markerStart === 'circle'}
                                                    <circle cx="8" cy="12" r="5" fill={signal.style.color} />
                                                {:else if signal.style.markerStart === 'diamond'}
                                                    <polygon points="8,4 14,12 8,20 2,12" fill={signal.style.color} />
                                                {:else if signal.style.markerStart === 'rect'}
                                                    <rect x="2" y="6" width="12" height="12" fill={signal.style.color} rx="1"></rect>
                                                {:else if signal.style.markerStart === 'pin'}
                                                    <circle cx="8" cy="4" r="3.5" fill={signal.style.color} />
                                                    <line x1="8" y1="7.5" x2="8" y2="12" stroke={signal.style.color} stroke-width="1.5" />
                                                    <circle cx="8" cy="12" r="1.5" fill={signal.style.color} />
                                                {/if}
                                            </svg>
                                            <!-- Line (full width via %) -->
                                            <svg width="100%" height="24" class="absolute inset-0">
                                                <line
                                                    x1="2%" y1="14" x2="98%" y2="14"
                                                    stroke={signal.style.color}
                                                    stroke-width={signal.style.lineWidth}
                                                    stroke-dasharray={signal.style.lineType === 'dashed' ? '8,4' : signal.style.lineType === 'dotted' ? '2,4' : 'none'}
                                                />
                                            </svg>
                                            <!-- End marker (absolute right) -->
                                            <svg class="absolute right-0 top-1/2 -translate-y-1/2 overflow-visible" width="16" height="24">
                                                {#if signal.style.markerEnd === 'arrow'}
                                                    <polygon points="4,5 12,12 4,19" fill={signal.style.color} />
                                                {:else if signal.style.markerEnd === 'circle'}
                                                    <circle cx="8" cy="12" r="5" fill={signal.style.color} />
                                                {:else if signal.style.markerEnd === 'diamond'}
                                                    <polygon points="8,4 14,12 8,20 2,12" fill={signal.style.color} />
                                                {:else if signal.style.markerEnd === 'rect'}
                                                    <rect x="2" y="6" width="12" height="12" fill={signal.style.color} rx="1" />
                                                {:else if signal.style.markerEnd === 'pin'}
                                                    <circle cx="8" cy="4" r="3.5" fill={signal.style.color} />
                                                    <line x1="8" y1="7.5" x2="8" y2="12" stroke={signal.style.color} stroke-width="1.5" />
                                                    <circle cx="8" cy="12" r="1.5" fill={signal.style.color} />
                                                {/if}
                                            </svg>
                                        </button>

                                        <!-- Unified style popover (opens upward) -->
                                        {#if stylePopoverId === signal.id}
                                            <!-- svelte-ignore a11y_no_static_element_interactions -->
                                            <!-- svelte-ignore a11y_click_events_have_key_events -->
                                            <div class="fixed inset-0 z-10" onclick={closeAllPopovers}></div>
                                            <!-- svelte-ignore a11y_no_static_element_interactions -->
                                            <!-- svelte-ignore a11y_click_events_have_key_events -->
                                            <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 z-20
                                                bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600
                                                rounded-lg shadow-lg p-3 w-max"
                                                onclick={(e) => e.stopPropagation()}>
                                                <div class="flex items-center gap-4">
                                                    <!-- Left: Start marker 2×3 grid -->
                                                    <div class="flex flex-col items-center">
                                                        <span class="text-[9px] text-gray-400 dark:text-gray-500 uppercase block mb-1.5">{$t('chartSettings.style.markerStart')}</span>
                                                        <div class="grid grid-cols-2 gap-1.5">
                                                            {#each MARKER_OPTIONS as mk}
                                                                <button type="button"
                                                                    aria-label={mk ?? 'none'}
                                                                    class="w-8 h-8 flex items-center justify-center rounded border transition-colors
                                                                        {signal.style.markerStart === mk ? 'border-libre-green bg-libre-green/10' : 'border-gray-200 dark:border-slate-600 hover:border-gray-300 dark:hover:border-slate-500'}"
                                                                    onclick={() => updateSignalStyle(signal.id, 'markerStart', mk)}
                                                                >
                                                                    {#if mk === null}
                                                                        <span class="text-[10px] text-gray-400">✕</span>
                                                                    {:else}
                                                                        <span style="color: {signal.style.color}" class="text-sm leading-none">{MARKER_SYMBOLS_START[mk]}</span>
                                                                    {/if}
                                                                </button>
                                                            {/each}
                                                        </div>
                                                    </div>

                                                    <!-- Center: Line type + Width -->
                                                    <div class="flex flex-col items-center border-x border-gray-200 dark:border-slate-600 px-4">
                                                        <!-- Line type -->
                                                        <span class="text-[9px] text-gray-400 dark:text-gray-500 uppercase block mb-1.5">{$t('chartSettings.style.lineType')}</span>
                                                        <div class="flex gap-1.5 mb-3">
                                                            {#each ['solid', 'dashed', 'dotted'] as lt}
                                                                <button
                                                                    type="button"
                                                                    aria-label={lt}
                                                                    class="w-10 h-6 flex items-center justify-center rounded border transition-colors
                                                                        {signal.style.lineType === lt
                                                                            ? 'border-libre-green bg-libre-green/10'
                                                                            : 'border-gray-200 dark:border-slate-600 hover:border-gray-300'}"
                                                                    onclick={() => updateSignalStyle(signal.id, 'lineType', lt as 'solid' | 'dashed' | 'dotted')}
                                                                >
                                                                    <svg width="32" height="6">
                                                                        <line x1="2" y1="3" x2="30" y2="3"
                                                                            stroke={signal.style.color}
                                                                            stroke-width="2"
                                                                            stroke-dasharray={lt === 'dashed' ? '5,3' : lt === 'dotted' ? '2,3' : 'none'}
                                                                        />
                                                                    </svg>
                                                                </button>
                                                            {/each}
                                                        </div>
                                                        <!-- Width -->
                                                        <span class="text-[9px] text-gray-400 dark:text-gray-500 uppercase block mb-1.5">{$t('chartSettings.style.width')}</span>
                                                        <div class="flex gap-1.5">
                                                            {#each [1, 2, 3, 4] as w}
                                                                <button
                                                                    type="button"
                                                                    aria-label="width {w}"
                                                                    class="w-7 h-6 flex items-center justify-center rounded border transition-colors
                                                                        {signal.style.lineWidth === w
                                                                            ? 'border-libre-green bg-libre-green/10'
                                                                            : 'border-gray-200 dark:border-slate-600 hover:border-gray-300'}"
                                                                    onclick={() => updateSignalStyle(signal.id, 'lineWidth', w)}
                                                                >
                                                                    <svg width="20" height="10">
                                                                        <line x1="2" y1="5" x2="18" y2="5"
                                                                            stroke={signal.style.color}
                                                                            stroke-width={w}
                                                                        />
                                                                    </svg>
                                                                </button>
                                                            {/each}
                                                        </div>
                                                    </div>

                                                    <!-- Right: End marker 2×3 grid -->
                                                    <div class="flex flex-col items-center">
                                                        <span class="text-[9px] text-gray-400 dark:text-gray-500 uppercase block mb-1.5">{$t('chartSettings.style.markerEnd')}</span>
                                                        <div class="grid grid-cols-2 gap-1.5">
                                                            {#each MARKER_OPTIONS as mk}
                                                                <button type="button"
                                                                    aria-label={mk ?? 'none'}
                                                                    class="w-8 h-8 flex items-center justify-center rounded border transition-colors
                                                                        {signal.style.markerEnd === mk ? 'border-libre-green bg-libre-green/10' : 'border-gray-200 dark:border-slate-600 hover:border-gray-300 dark:hover:border-slate-500'}"
                                                                    onclick={() => updateSignalStyle(signal.id, 'markerEnd', mk)}
                                                                >
                                                                    {#if mk === null}
                                                                        <span class="text-[10px] text-gray-400">✕</span>
                                                                    {:else}
                                                                        <span style="color: {signal.style.color}" class="text-sm leading-none">{MARKER_SYMBOLS_END[mk]}</span>
                                                                    {/if}
                                                                </button>
                                                            {/each}
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        {/if}
                                    </div>
                                </div>
                            </div>
                        {/snippet}
                    </OrderableList>
                {/if}

                <!-- Add signal buttons -->
                <div class="mt-3">
                    <div class="flex flex-wrap gap-2">
                        {#each signalTypes as st}
                            <button
                                type="button"
                                class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg
                                    border border-gray-200 dark:border-slate-600
                                    bg-white dark:bg-slate-700
                                    text-gray-600 dark:text-gray-300
                                    hover:bg-libre-green/10 hover:border-libre-green/50
                                    transition-colors"
                                onclick={() => addSignal(st.type)}
                            >
                                <Plus size={12} />
                                <span>{st.icon} {st.displayName}</span>
                            </button>
                        {/each}
                    </div>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-end gap-2 px-6 py-4 border-t border-gray-100 dark:border-slate-700">
            <button
                type="button"
                class="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-slate-700 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
                onclick={handleClose}
            >
                {$t('common.cancel')}
            </button>
            <button
                type="button"
                class="px-4 py-2 text-sm font-medium text-white bg-libre-green rounded-lg hover:bg-libre-green/90 transition-colors"
                onclick={handleSave}
            >
                {$t('chartSettings.apply')}
            </button>
        </div>
    </div>
</ModalBase>

<!-- Confirm discard changes -->
<ConfirmModal
    open={confirmCloseOpen}
    title={$t('chartSettings.discardTitle')}
    message={$t('chartSettings.discardMessage')}
    confirmText={$t('chartSettings.discard')}
    danger={false}
    warning={true}
    onConfirm={confirmDiscardAndClose}
    onCancel={() => { confirmCloseOpen = false; }}
    zIndex={70}
/>

