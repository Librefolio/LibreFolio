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
    import {_ as t} from '$lib/i18n';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import {ConfirmModal} from '$lib/components/table';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';
    import type {ChartSettings} from '$lib/stores/chartSettingsStore.svelte';
    import {
        type SignalConfig,
        type SignalStyle,
        type MarkerType,
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
                <div class="flex items-start gap-2 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50">
                    <AlertTriangle size={16} class="text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
                    <p class="text-xs text-amber-700 dark:text-amber-300">
                        {$t('chartSettings.globalWarning')}
                    </p>
                </div>
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

                                <!-- Row 3: Visual Style Preview Strip (Layout C) -->
                                <div class="flex items-center gap-2 pt-1.5 border-t border-gray-100 dark:border-slate-700">
                                    <!-- Marker start selector (visual symbols) -->
                                    <select
                                        class="w-8 px-0 py-0.5 text-center text-xs border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200"
                                        title={$t('chartSettings.style.markerStart')}
                                        onchange={(e) => {
                                            const val = e.currentTarget.value;
                                            updateSignalStyle(signal.id, 'markerStart', val === '' ? null : val as MarkerType);
                                        }}
                                    >
                                        <option value="" selected={!signal.style.markerStart}>·</option>
                                        <option value="arrow" selected={signal.style.markerStart === 'arrow'}>◁</option>
                                        <option value="circle" selected={signal.style.markerStart === 'circle'}>○</option>
                                        <option value="diamond" selected={signal.style.markerStart === 'diamond'}>◇</option>
                                        <option value="pin" selected={signal.style.markerStart === 'pin'}>📍</option>
                                    </select>

                                    <!-- SVG line preview strip (shows actual color + width + dash pattern) -->
                                    <div class="flex-1 h-6 flex items-center">
                                        <svg width="100%" height="24" class="overflow-visible">
                                            <line
                                                x1="0" y1="12" x2="100%" y2="12"
                                                stroke={signal.style.color}
                                                stroke-width={signal.style.lineWidth}
                                                stroke-dasharray={signal.style.lineType === 'dashed' ? '8,4' : signal.style.lineType === 'dotted' ? '2,4' : 'none'}
                                            />
                                        </svg>
                                    </div>

                                    <!-- Marker end selector (visual symbols) -->
                                    <select
                                        class="w-8 px-0 py-0.5 text-center text-xs border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200"
                                        title={$t('chartSettings.style.markerEnd')}
                                        onchange={(e) => {
                                            const val = e.currentTarget.value;
                                            updateSignalStyle(signal.id, 'markerEnd', val === '' ? null : val as MarkerType);
                                        }}
                                    >
                                        <option value="" selected={!signal.style.markerEnd}>·</option>
                                        <option value="arrow" selected={signal.style.markerEnd === 'arrow'}>▷</option>
                                        <option value="circle" selected={signal.style.markerEnd === 'circle'}>○</option>
                                        <option value="diamond" selected={signal.style.markerEnd === 'diamond'}>◇</option>
                                        <option value="pin" selected={signal.style.markerEnd === 'pin'}>📍</option>
                                    </select>

                                    <!-- Divider -->
                                    <div class="w-px h-5 bg-gray-200 dark:bg-slate-600"></div>

                                    <!-- Color picker -->
                                    <input
                                        type="color"
                                        value={signal.style.color}
                                        class="w-6 h-6 p-0 border border-gray-200 dark:border-slate-600 rounded cursor-pointer"
                                        title={$t('chartSettings.style.color')}
                                        oninput={(e) => updateSignalStyle(signal.id, 'color', e.currentTarget.value)}
                                    />

                                    <!-- Width selector (visual thickness preview) -->
                                    <select
                                        class="w-12 px-0.5 py-0.5 text-xs border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700"
                                        title={$t('chartSettings.style.width')}
                                        onchange={(e) => updateSignalStyle(signal.id, 'lineWidth', Number(e.currentTarget.value))}
                                    >
                                        {#each [1, 2, 3, 4] as w}
                                            <option value={w} selected={signal.style.lineWidth === w}>{'━'.repeat(w)}</option>
                                        {/each}
                                    </select>

                                    <!-- Line type selector (visual dash pattern) -->
                                    <select
                                        class="w-12 px-0.5 py-0.5 text-xs border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700"
                                        title={$t('chartSettings.style.lineType')}
                                        onchange={(e) => {
                                            const val = e.currentTarget.value;
                                            if (val === 'solid' || val === 'dashed' || val === 'dotted') {
                                                updateSignalStyle(signal.id, 'lineType', val);
                                            }
                                        }}
                                    >
                                        <option value="solid" selected={signal.style.lineType === 'solid'}>━━━</option>
                                        <option value="dashed" selected={signal.style.lineType === 'dashed'}>╌╌╌</option>
                                        <option value="dotted" selected={signal.style.lineType === 'dotted'}>···</option>
                                    </select>
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

