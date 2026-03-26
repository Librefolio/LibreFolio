<!--
  ChartSignalsSection — Extracted signal overlay management section.

  Contains the 3 categorized dropdowns (Indicators, Comparison, Benchmarks),
  OrderableList of configured signals with parameters, and style popovers.

  Used by: ChartSettingsModal (in ModalBase) and FX detail page (inline foldable panel).
  Pure component: receives signal configs, emits changes via callbacks.

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {Trash2, ArrowLeftRight, Info, RotateCw, ExternalLink} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import SignalStyleEditor from './SignalStyleEditor.svelte';
    import type {SelectOption} from '$lib/components/ui/select/types';
    import {getCurrencyInfo} from '$lib/stores/currencyStore';
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
        /** Current signal configurations (bindable) */
        signals?: SignalConfig[];
        /** Available FX pairs for FxPairSignal (slug format: 'EUR-GBP') */
        availablePairs?: string[];
        /** Slug of the main chart pair (for crown emoji in dropdown) */
        mainPairSlug?: string;
        /** Called when signals change */
        onchange?: (signals: SignalConfig[]) => void;
        /** Called when user clicks Sync on an FxPair signal */
        onsyncpair?: (slug: string) => void;
        /** Called when user clicks Detail on an FxPair signal */
        ondetailpair?: (slug: string) => void;
    }

    let {
        signals = $bindable([]),
        availablePairs = [],
        mainPairSlug = '',
        onchange,
        onsyncpair,
        ondetailpair,
    }: Props = $props();

    // =========================================================================
    // Signal types from registry
    // =========================================================================

    const signalTypes: SignalTypeInfo[] = getRegisteredSignalTypes();

    const SIGNAL_TYPE_I18N_KEY: Record<string, string> = {
        'fx-pair': 'fxPair', 'linear': 'linear', 'compound': 'compound',
        'sine': 'sine', 'ema': 'ema', 'macd': 'macd', 'rsi': 'rsi',
        'bollinger': 'bollinger',
    };

    function getSignalName(st: SignalTypeInfo): string {
        const key = SIGNAL_TYPE_I18N_KEY[st.type];
        return key ? $t(`chartSettings.signals.${key}`) : st.displayName;
    }

    function getSignalAbbr(signalType: string): string {
        const key = SIGNAL_TYPE_I18N_KEY[signalType];
        if (!key) return '';
        const abbrKey = `chartSettings.signals.${key}Abbr`;
        const abbr = $t(abbrKey);
        return abbr !== abbrKey ? abbr : '';
    }

    function getSignalFullName(signalType: string): string {
        const key = SIGNAL_TYPE_I18N_KEY[signalType];
        if (!key) return '';
        const fullKey = `chartSettings.signals.${key}Full`;
        const full = $t(fullKey);
        return full !== fullKey ? full : '';
    }

    function getSignalDesc(signalType: string): string {
        const key = SIGNAL_TYPE_I18N_KEY[signalType];
        if (!key) return '';
        const descKey = `chartSettings.signals.${key}Desc`;
        const desc = $t(descKey);
        return desc !== descKey ? desc : getSignalFullName(signalType);
    }

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
    // Category dropdowns
    // =========================================================================

    let indicatorOptions: SelectOption[] = $derived(signalTypes
        .filter(st => st.category === 'indicator')
        .map(st => {
            const name = getSignalName(st);
            const full = getSignalFullName(st.type);
            return {value: st.type, label: full ? `${name} — ${full}` : name, icon: st.icon, data: {name, fullName: full}};
        }));

    let comparisonOptions: SelectOption[] = $derived(signalTypes
        .filter(st => st.category === 'comparison')
        .map(st => {
            const name = getSignalName(st);
            const full = getSignalFullName(st.type);
            return {value: st.type, label: full ? `${name} — ${full}` : name, icon: st.icon, data: {name, fullName: full}};
        }));

    let benchmarkOptions: SelectOption[] = $derived(signalTypes
        .filter(st => st.category === 'benchmark')
        .map(st => {
            const name = getSignalName(st);
            const full = getSignalFullName(st.type);
            return {value: st.type, label: full ? `${name} — ${full}` : name, icon: st.icon, data: {name, fullName: full}};
        }));

    let indicatorSelect = $state('');
    let comparisonSelect = $state('');
    let benchmarkSelect = $state('');

    // =========================================================================
    // Marker/Style constants
    // =========================================================================

    const LINE_TYPES: ('solid' | 'dashed' | 'dotted')[] = ['solid', 'dashed', 'dotted'];

    // =========================================================================
    // Signal management
    // =========================================================================

    function emitChange() {
        onchange?.(signals);
    }

    function addSignal(type: string) {
        // Collect colors already in use by existing signals
        const usedColors = signals.map(s => s.style.color);
        const signal = createSignal(type, signals.length, usedColors);
        if (signal) {
            signals = [...signals, signal.toConfig()];
            emitChange();
        }
    }

    function removeSignal(id: string) {
        signals = signals.filter(s => s.id !== id);
        emitChange();
    }

    function handleSignalReorder(newSignals: SignalConfig[]) {
        signals = newSignals;
        emitChange();
    }

    function updateSignalParam(id: string, key: string, value: unknown) {
        signals = signals.map(s =>
            s.id === id ? {...s, params: {...s.params, [key]: value}} : s
        );
        emitChange();
    }

    function updateSignalStyle<K extends keyof SignalStyle>(id: string, key: K, value: SignalStyle[K]) {
        signals = signals.map(s =>
            s.id === id ? {...s, style: {...s.style, [key]: value}} : s
        );
        emitChange();
    }

    function resolveDynamicOptions(dynamicKey: string): Array<{value: string; label: string}> {
        if (dynamicKey === 'configuredFxPairs') {
            return availablePairs.map(slug => ({
                value: slug,
                label: slug.replace('-', '/'),
            }));
        }
        return [];
    }

    /** Set of pair slugs currently syncing (for rotating icon) */
    let syncingPairs = $state<Set<string>>(new Set());

    async function handleSyncPairWithSpin(slug: string) {
        syncingPairs = new Set([...syncingPairs, slug]);
        try {
            await onsyncpair?.(slug);
        } finally {
            syncingPairs = new Set([...syncingPairs].filter(s => s !== slug));
        }
    }

    /** Set of pair slugs already used by other FxPair signals */
    let usedPairSlugs = $derived(new Set(
        signals.filter(s => s.signalType === 'fx-pair' && s.params.pairSlug)
            .map(s => String(s.params.pairSlug))
    ));
</script>

<div>
    <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">{$t('chartSettings.overlaySignals')}</h3>

    <!-- Add signal dropdowns by category -->
    <div class="mb-3">
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {#if indicatorOptions.length > 0}
                <div>
                    <span class="block text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase mb-1">📊 {$t('chartSettings.categories.indicator')}</span>
                    <SimpleSelect
                        bind:value={indicatorSelect}
                        options={indicatorOptions}
                        placeholder={$t('common.select')}
                        dropdownPosition="auto"
                        onchange={(v) => { addSignal(v); indicatorSelect = ''; }}
                    >
                        {#snippet item(option)}
                            {#if option.data}
                                <span class="truncate">
                                    {option.icon} <span class="font-medium">{(option.data as {name: string}).name}</span>
                                    {#if (option.data as {fullName: string}).fullName}<span class="text-[11px] text-gray-400 dark:text-gray-500 ml-1">{(option.data as {fullName: string}).fullName}</span>{/if}
                                </span>
                            {/if}
                        {/snippet}
                    </SimpleSelect>
                </div>
            {/if}
            {#if comparisonOptions.length > 0}
                <div>
                    <span class="block text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase mb-1">💱 {$t('chartSettings.categories.comparison')}</span>
                    <SimpleSelect
                        bind:value={comparisonSelect}
                        options={comparisonOptions}
                        placeholder={$t('common.select')}
                        dropdownPosition="auto"
                        onchange={(v) => { addSignal(v); comparisonSelect = ''; }}
                    >
                        {#snippet item(option)}
                            {#if option.data}
                                <span class="truncate">
                                    {option.icon} <span class="font-medium">{(option.data as {name: string}).name}</span>
                                    {#if (option.data as {fullName: string}).fullName}<span class="text-[11px] text-gray-400 dark:text-gray-500 ml-1">{(option.data as {fullName: string}).fullName}</span>{/if}
                                </span>
                            {/if}
                        {/snippet}
                    </SimpleSelect>
                </div>
            {/if}
            {#if benchmarkOptions.length > 0}
                <div>
                    <span class="block text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase mb-1">📐 {$t('chartSettings.categories.benchmark')}</span>
                    <SimpleSelect
                        bind:value={benchmarkSelect}
                        options={benchmarkOptions}
                        placeholder={$t('common.select')}
                        dropdownPosition="auto"
                        onchange={(v) => { addSignal(v); benchmarkSelect = ''; }}
                    >
                        {#snippet item(option)}
                            {#if option.data}
                                <span class="truncate">
                                    {option.icon} <span class="font-medium">{(option.data as {name: string}).name}</span>
                                    {#if (option.data as {fullName: string}).fullName}<span class="text-[11px] text-gray-400 dark:text-gray-500 ml-1">{(option.data as {fullName: string}).fullName}</span>{/if}
                                </span>
                            {/if}
                        {/snippet}
                    </SimpleSelect>
                </div>
            {/if}
        </div>
    </div>

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
            {#snippet children({ item: signal })}
                {#if true}
                    {@const typeInfo = getSignalTypeInfo(signal.signalType)}
                    {@const signalName = typeInfo ? getSignalName(typeInfo) : signal.signalType}
                    {@const signalFullName = getSignalFullName(signal.signalType)}
                    {@const signalDescText = getSignalDesc(signal.signalType)}
                    <div class="space-y-2">
                        <!-- Signal header -->
                        <div class="flex items-center justify-between gap-1">
                            <div class="flex items-center gap-1.5 min-w-0">
                                <span class="text-sm flex-shrink-0">{typeInfo?.icon ?? '❓'}</span>
                                <span class="text-xs font-medium text-gray-600 dark:text-gray-300 flex-shrink-0">{signalName}</span>
                                {#if signalFullName}
                                    <span class="text-[10px] text-gray-400 dark:text-gray-500 truncate">{signalFullName}</span>
                                {/if}
                                {#if typeInfo?.docsPath}
                                    <DocsLink path={typeInfo.docsPath} label={signalDescText || signalName} math />
                                {/if}
                            </div>
                            <div class="flex items-center gap-0.5 flex-shrink-0">
                                <button
                                    type="button"
                                    class="p-1 rounded text-gray-400 hover:text-red-500 transition-colors"
                                    title={$t('chartSettings.removeSignal')}
                                    onclick={() => removeSignal(signal.id)}
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        </div>

                        <!-- Parameters -->
                        {#if typeInfo && typeInfo.paramDescriptors.length > 0}
                            <div class="flex flex-wrap gap-2">
                                {#each typeInfo.paramDescriptors as desc}
                                    <div class="flex items-center gap-1.5">
                                        <span class="text-[10px] text-gray-500 dark:text-gray-400 uppercase">
                                            {$t(`chartSettings.params.${desc.key}`) !== `chartSettings.params.${desc.key}` ? $t(`chartSettings.params.${desc.key}`) : desc.label}
                                        </span>
                                        {#if desc.tooltip}
                                            <Tooltip text={$t(desc.tooltip)} math position="top">
                                                <Info size={12} class="text-gray-400 hover:text-libre-green cursor-help transition-colors" />
                                            </Tooltip>
                                        {/if}
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
                                            {#if desc.dynamicOptionsKey === 'configuredFxPairs'}
                                                {@const currentPairSlug = getParamString(signal, desc.key)}
                                                <div class="flex items-center gap-1">
                                                    <div class="w-48">
                                                        <SimpleSelect
                                                            value={currentPairSlug}
                                                            options={resolveDynamicOptions('configuredFxPairs').map(o => {
                                                                const parts = o.value.split('-');
                                                                const isCurrent = o.value === currentPairSlug;
                                                                // When this card's signal is inverted, swap display order for the selected pair
                                                                const showInverted = isCurrent && Boolean(signal.params._inverted);
                                                                const base = showInverted ? parts[1] : parts[0];
                                                                const quote = showInverted ? parts[0] : parts[1];
                                                                const baseFlag = getCurrencyInfo(base).flag_emoji;
                                                                const quoteFlag = getCurrencyInfo(quote).flag_emoji;
                                                                const isUsedElsewhere = !isCurrent && usedPairSlugs.has(o.value);
                                                                const isMain = !!mainPairSlug && o.value === mainPairSlug;
                                                                // Suffix: 👑 always on the main chart pair, ✓ on this card's selection, 📌 on other overlay signals
                                                                const suffix = isMain ? ' 👑' : isCurrent ? ' ✓' : isUsedElsewhere ? ' 📌' : '';
                                                                return {value: o.value, label: `${baseFlag} ${base} → ${quoteFlag} ${quote}${suffix}`};
                                                            })}
                                                            placeholder="— {$t('chartSettings.params.currencyPair')}"
                                                            dropdownPosition="auto"
                                                            onchange={(v) => {
                                                                updateSignalParam(signal.id, desc.key, v);
                                                                updateSignalParam(signal.id, '_inverted', false);
                                                            }}
                                                        />
                                                    </div>
                                                    <button
                                                        type="button"
                                                        class="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors
                                                            {signal.params._inverted ? 'text-libre-green' : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}"
                                                        title={$t('common.swapDirection')}
                                                        onclick={() => updateSignalParam(signal.id, '_inverted', !signal.params._inverted)}
                                                    >
                                                        <ArrowLeftRight size={12} />
                                                    </button>
                                                    {#if onsyncpair}
                                                        {@const pairSlug = String(signal.params.pairSlug)}
                                                        <button
                                                            type="button"
                                                            class="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-blue-500 transition-colors"
                                                            title={$t('common.sync')}
                                                            disabled={syncingPairs.has(pairSlug)}
                                                            onclick={() => handleSyncPairWithSpin(pairSlug)}
                                                        >
                                                            <RotateCw size={12} class={syncingPairs.has(pairSlug) ? 'animate-spin' : ''} />
                                                        </button>
                                                    {/if}
                                                    {#if ondetailpair}
                                                        <button
                                                            type="button"
                                                            class="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-libre-green transition-colors"
                                                            title={$t('common.detail')}
                                                            onclick={() => ondetailpair?.(String(signal.params.pairSlug))}
                                                        >
                                                            <ExternalLink size={12} />
                                                        </button>
                                                    {/if}
                                                </div>
                                            {:else}
                                                {@const opts = desc.options ?? []}
                                                <div class="w-36">
                                                    <SimpleSelect
                                                        value={getParamString(signal, desc.key)}
                                                        options={opts}
                                                        dropdownPosition="auto"
                                                        onchange={(v) => updateSignalParam(signal.id, desc.key, v)}
                                                    />
                                                </div>
                                            {/if}
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

                        <!-- Style strip (non-MACD) -->
                        {#if signal.signalType !== 'macd'}
                            <div class="pt-1.5 border-t border-gray-100 dark:border-slate-700">
                            <SignalStyleEditor
                                style={signal.style}
                                onstylechange={(key, value) => updateSignalStyle(signal.id, key, value)}
                            />
                            </div>
                        {/if}

                        <!-- MACD: simplified single color+line style (full MACD popover stays in modal for now) -->
                        {#if signal.signalType === 'macd'}
                            <div class="flex items-center gap-1.5 pt-1.5 border-t border-gray-100 dark:border-slate-700">
                                <input
                                    type="color"
                                    value={signal.style.color}
                                    class="w-6 h-6 p-0 border border-gray-200 dark:border-slate-600 rounded cursor-pointer shrink-0"
                                    title={$t('chartSettings.macdLineColor')}
                                    oninput={(e) => updateSignalStyle(signal.id, 'color', e.currentTarget.value)}
                                />
                                <span class="text-[10px] text-gray-400 dark:text-gray-500">MACD</span>
                                <div class="flex gap-1">
                                    {#each LINE_TYPES as lt}
                                        <button type="button" aria-label={lt}
                                            class="w-8 h-5 flex items-center justify-center rounded border transition-colors
                                                {signal.style.lineType === lt ? 'border-libre-green bg-libre-green/10' : 'border-gray-200 dark:border-slate-600'}"
                                            onclick={() => updateSignalStyle(signal.id, 'lineType', lt)}>
                                            <svg width="24" height="4"><line x1="2" y1="2" x2="22" y2="2" stroke={signal.style.color} stroke-width="1.5"
                                                stroke-dasharray={lt === 'dashed' ? '4,2' : lt === 'dotted' ? '2,2' : 'none'} /></svg>
                                        </button>
                                    {/each}
                                </div>
                            </div>
                        {/if}
                    </div>
                {/if}
            {/snippet}
        </OrderableList>
    {/if}
</div>


