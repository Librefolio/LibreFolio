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
    import {X, Plus, Trash2, Settings, AlertTriangle} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';
    import type {ChartSettings} from '$lib/stores/chartSettingsStore';
    import {
        type SignalConfig,
        type SignalStyle,
        getRegisteredSignalTypes,
        createSignal,
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
            signals = structuredClone(settings.signals);
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

    function handleSave() {
        const result: ChartSettings = {
            colorByBaseline,
            areaFill,
            gridLines,
            staleGradient,
            signals: structuredClone(signals),
        };
        onsave?.(result);
        open = false;
    }

    function handleClose() {
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
                    {mode === 'global' ? 'Chart Settings' : 'Chart Settings (Local)'}
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
                <div class="flex items-start gap-2 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50">
                    <AlertTriangle size={16} class="text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
                    <p class="text-xs text-amber-700 dark:text-amber-300">
                        These settings will override all per-card customizations.
                    </p>
                </div>
            {/if}

            <!-- Aesthetics Section -->
            <div>
                <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Aesthetics</h3>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <!-- Color by baseline -->
                    <label class="flex items-center gap-3 p-2.5 rounded-lg border border-gray-200 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-700/50 cursor-pointer transition-colors">
                        <input type="checkbox" bind:checked={colorByBaseline}
                            class="w-4 h-4 rounded border-gray-300 dark:border-slate-500 text-libre-green focus:ring-libre-green" />
                        <span>
                            <span class="block text-sm font-medium text-gray-700 dark:text-gray-200">Baseline Colors</span>
                            <span class="block text-xs text-gray-500 dark:text-gray-400">Green above / Red below baseline</span>
                        </span>
                    </label>

                    <!-- Area fill -->
                    <label class="flex items-center gap-3 p-2.5 rounded-lg border border-gray-200 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-700/50 cursor-pointer transition-colors">
                        <input type="checkbox" bind:checked={areaFill}
                            class="w-4 h-4 rounded border-gray-300 dark:border-slate-500 text-libre-green focus:ring-libre-green" />
                        <span>
                            <span class="block text-sm font-medium text-gray-700 dark:text-gray-200">Area Fill</span>
                            <span class="block text-xs text-gray-500 dark:text-gray-400">Gradient fill under the line</span>
                        </span>
                    </label>

                    <!-- Grid lines -->
                    <label class="flex items-center gap-3 p-2.5 rounded-lg border border-gray-200 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-700/50 cursor-pointer transition-colors">
                        <input type="checkbox" bind:checked={gridLines}
                            class="w-4 h-4 rounded border-gray-300 dark:border-slate-500 text-libre-green focus:ring-libre-green" />
                        <span>
                            <span class="block text-sm font-medium text-gray-700 dark:text-gray-200">Grid Lines</span>
                            <span class="block text-xs text-gray-500 dark:text-gray-400">Show horizontal dashed grid</span>
                        </span>
                    </label>

                    <!-- Stale gradient -->
                    <label class="flex items-center gap-3 p-2.5 rounded-lg border border-gray-200 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-700/50 cursor-pointer transition-colors">
                        <input type="checkbox" bind:checked={staleGradient}
                            class="w-4 h-4 rounded border-gray-300 dark:border-slate-500 text-libre-green focus:ring-libre-green" />
                        <span>
                            <span class="block text-sm font-medium text-gray-700 dark:text-gray-200">Stale Gradient</span>
                            <span class="block text-xs text-gray-500 dark:text-gray-400">Fade old backward-filled data</span>
                        </span>
                    </label>
                </div>
            </div>

            <!-- Signals Section -->
            <div>
                <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Overlay Signals</h3>

                {#if signals.length === 0}
                    <p class="text-xs text-gray-400 dark:text-gray-500 italic mb-3">
                        No overlay signals configured. Add one below.
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
                                        title="Remove signal"
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

                                <!-- Style controls: color, width, lineType, arrows -->
                                <div class="flex flex-wrap items-center gap-2 pt-1 border-t border-gray-100 dark:border-slate-700">
                                    <!-- Color picker -->
                                    <div class="flex items-center gap-1">
                                        <span class="text-[10px] text-gray-500 dark:text-gray-400">Color</span>
                                        <input
                                            type="color"
                                            value={signal.style.color}
                                            class="w-6 h-6 p-0 border border-gray-200 dark:border-slate-600 rounded cursor-pointer"
                                            oninput={(e) => updateSignalStyle(signal.id, 'color', e.currentTarget.value)}
                                        />
                                    </div>

                                    <!-- Line width -->
                                    <div class="flex items-center gap-1">
                                        <span class="text-[10px] text-gray-500 dark:text-gray-400">Width</span>
                                        <select
                                            class="px-1 py-0.5 text-xs border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200"
                                            onchange={(e) => updateSignalStyle(signal.id, 'lineWidth', Number(e.currentTarget.value))}
                                        >
                                            <option value="1" selected={signal.style.lineWidth === 1}>1</option>
                                            <option value="2" selected={signal.style.lineWidth === 2}>2</option>
                                            <option value="3" selected={signal.style.lineWidth === 3}>3</option>
                                            <option value="4" selected={signal.style.lineWidth === 4}>4</option>
                                        </select>
                                    </div>

                                    <!-- Line type -->
                                    <div class="flex items-center gap-1">
                                        <span class="text-[10px] text-gray-500 dark:text-gray-400">Style</span>
                                        <select
                                            class="px-1 py-0.5 text-xs border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200"
                                            onchange={(e) => {
                                                const val = e.currentTarget.value;
                                                if (val === 'solid' || val === 'dashed' || val === 'dotted') {
                                                    updateSignalStyle(signal.id, 'lineType', val);
                                                }
                                            }}
                                        >
                                            <option value="solid" selected={signal.style.lineType === 'solid'}>Solid</option>
                                            <option value="dashed" selected={signal.style.lineType === 'dashed'}>Dashed</option>
                                            <option value="dotted" selected={signal.style.lineType === 'dotted'}>Dotted</option>
                                        </select>
                                    </div>

                                    <!-- Arrow start -->
                                    <label class="flex items-center gap-1 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={signal.style.arrowStart}
                                            class="w-3 h-3 rounded border-gray-300 dark:border-slate-500 text-libre-green focus:ring-libre-green"
                                            onchange={(e) => updateSignalStyle(signal.id, 'arrowStart', e.currentTarget.checked)}
                                        />
                                        <span class="text-[10px] text-gray-500 dark:text-gray-400">Arrow ←</span>
                                    </label>

                                    <!-- Arrow end -->
                                    <label class="flex items-center gap-1 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={signal.style.arrowEnd}
                                            class="w-3 h-3 rounded border-gray-300 dark:border-slate-500 text-libre-green focus:ring-libre-green"
                                            onchange={(e) => updateSignalStyle(signal.id, 'arrowEnd', e.currentTarget.checked)}
                                        />
                                        <span class="text-[10px] text-gray-500 dark:text-gray-400">Arrow →</span>
                                    </label>
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
                Cancel
            </button>
            <button
                type="button"
                class="px-4 py-2 text-sm font-medium text-white bg-libre-green rounded-lg hover:bg-libre-green/90 transition-colors"
                onclick={handleSave}
            >
                Apply
            </button>
        </div>
    </div>
</ModalBase>

