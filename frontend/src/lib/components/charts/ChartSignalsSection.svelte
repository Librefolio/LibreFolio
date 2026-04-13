<!--
  ChartSignalsSection — Extracted signal overlay management section.

  Contains the 3 categorized dropdowns (Indicators, Comparison, Benchmarks),
  OrderableList of configured signals with parameters, and style popovers.

  Used by: ChartSettingsModal (in ModalBase) and FX detail page (inline foldable panel).
  Pure component: receives signal configs, emits changes via callbacks.

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {ArrowLeftRight, BarChart3, Coins, ExternalLink, Info, RotateCw, Trash2, AlertTriangle} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import SignalStyleEditor from './SignalStyleEditor.svelte';
    import type {SelectOption} from '$lib/components/ui/select/types';
    import {getCurrencyInfo} from '$lib/stores/currencyStore';
    import {createSignal, getRegisteredSignalTypes, type SignalConfig, type SignalStyle, type SignalTypeInfo,} from '$lib/charts/signals';

    // =========================================================================
    // Types
    // =========================================================================

    export interface SignalDataSummary {
        pointCount: number;
        eventCounts: Record<string, number>;
        firstDate: string | null;
    }

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Current signal configurations (bindable) */
        signals?: SignalConfig[];
        /** Available FX pairs for FxPairSignal (slug format: 'EUR-GBP') */
        availablePairs?: string[];
        /** Available assets for AssetComparisonSignal */
        availableAssets?: Array<{id: number, display_name: string, icon_url?: string | null, asset_type?: string | null, currency?: string}>;
        /** Slug of the main chart pair (for crown emoji in dropdown) */
        mainPairSlug?: string;
        /** Called when signals change */
        onchange?: (signals: SignalConfig[]) => void;
        /** Called when user clicks Sync on an FxPair signal */
        onsyncpair?: (slug: string) => void;
        /** Called when user clicks Detail on an FxPair signal */
        ondetailpair?: (slug: string) => void;
        /** Called when user clicks Sync on an AssetComparison signal */
        onsyncasset?: (assetId: number) => void;
        /** Called when user clicks Detail on an AssetComparison signal */
        ondetailasset?: (assetId: number) => void;
        /** Data summaries per signal id (point count, event counts, first date) */
        signalSummaries?: Map<string, SignalDataSummary>;
        /** Current chart date range start (for "data missing before" warning) */
        dateStart?: string;
        /** Current display currency (for FX pair status on comparison signals) */
        displayCurrency?: string;
        /** All configured FX pair slugs (for FX pair existence check) */
        configuredFxSlugs?: string[];
        /** Called when user clicks "Create FX pair" on a comparison signal */
        oncreatefxpair?: (slug: string) => void;
        /** Called when user clicks "Sync FX pair" on a comparison signal */
        onsyncfxpair?: (slug: string) => void;
    }

    let {
        signals = $bindable([]),
        availablePairs = [],
        availableAssets = [],
        mainPairSlug = '',
        onchange,
        onsyncpair,
        ondetailpair,
        onsyncasset,
        ondetailasset,
        signalSummaries = new Map(),
        dateStart = '',
        displayCurrency = '',
        configuredFxSlugs = [],
        oncreatefxpair,
        onsyncfxpair,
    }: Props = $props();

    // =========================================================================
    // Signal types from registry
    // =========================================================================

    const signalTypes: SignalTypeInfo[] = getRegisteredSignalTypes();

    const SIGNAL_TYPE_I18N_KEY: Record<string, string> = {
        'fx-pair': 'fxPair', 'asset-comparison': 'assetComparison', 'linear': 'linear', 'compound': 'compound',
        'sine': 'sine', 'ema': 'ema', 'macd': 'macd', 'rsi': 'rsi',
        'bollinger': 'bollinger',
    };

    function getSignalName(st: SignalTypeInfo): string {
        const key = SIGNAL_TYPE_I18N_KEY[st.type];
        return key ? $t(`chartSettings.signals.${key}`) : st.displayName;
    }

    /** Extract typed data from dropdown option (avoids TS `as` cast in template) */
    function getOptionData(option: SelectOption): { name: string; fullName: string } {
        const d = (option.data ?? {}) as Record<string, string>;
        return { name: d.name ?? '', fullName: d.fullName ?? '' };
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

    function resolveDynamicOptions(dynamicKey: string): Array<{ value: string; label: string }> {
        if (dynamicKey === 'configuredFxPairs') {
            return availablePairs.map(slug => ({
                value: slug,
                label: slug.replace('-', '/'),
            }));
        }
        if (dynamicKey === 'configuredAssets') {
            return (availableAssets ?? []).map(a => ({
                value: String(a.id),
                label: a.display_name,
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

    /** Set of asset IDs currently syncing (for rotating icon) */
    let syncingAssets = $state<Set<number>>(new Set());

    async function handleSyncAssetWithSpin(assetId: number) {
        syncingAssets = new Set([...syncingAssets, assetId]);
        try {
            await onsyncasset?.(assetId);
        } finally {
            syncingAssets = new Set([...syncingAssets].filter(id => id !== assetId));
        }
    }

    /** Set of pair slugs already used by other FxPair signals */
    let usedPairSlugs = $derived(new Set(
        signals.filter(s => s.signalType === 'fx-pair' && s.params.pairSlug)
            .map(s => String(s.params.pairSlug))
    ));

    /** Asset type → icon filename mapping (same as AssetCard) */
    const ASSET_TYPE_ICON_MAP: Record<string, string> = {
        STOCK: 'stock', ETF: 'etf', BOND: 'bond', CRYPTO: 'crypto',
        FUND: 'fund', HOLD: 'hold', CROWDFUND_LOAN: 'crowdfunding', OTHER: 'other',
    };

    /** Find asset info by id for icon rendering */
    function findAssetInfo(assetId: string) {
        return (availableAssets ?? []).find(a => String(a.id) === assetId);
    }

    /** Set of asset IDs already used by asset-comparison signals */
    let usedAssetIds = $derived(new Set(
        signals.filter(s => s.signalType === 'asset-comparison' && s.params.assetId)
            .map(s => Number(s.params.assetId))
    ));

    /** Main asset ID parsed from mainPairSlug (format: "asset-123") */
    let mainAssetId = $derived(mainPairSlug.startsWith('asset-') ? Number(mainPairSlug.slice(6)) : 0);

    const EVENT_EMOJI: Record<string, string> = {
        DIVIDEND: '💰',
        INTEREST: '💎',
        PRICE_ADJUSTMENT: '🔧',
        MATURITY_SETTLEMENT: '📅',
        SPLIT: '✂️',
    };

    /** Map event type → i18n badge key suffix */
    const EVENT_BADGE_KEY: Record<string, string> = {
        DIVIDEND: 'badgeDividend',
        INTEREST: 'badgeInterest',
        PRICE_ADJUSTMENT: 'badgePriceAdjustment',
        MATURITY_SETTLEMENT: 'badgeMaturitySettlement',
        SPLIT: 'badgeSplit',
    };
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
                                {@const d = getOptionData(option)}
                                <span class="truncate">
                                    {option.icon} <span class="font-medium">{d.name}</span>
                                    {#if d.fullName}<span
                                            class="text-[11px] text-gray-400 dark:text-gray-500 ml-1">{d.fullName}</span>{/if}
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
                                {@const d = getOptionData(option)}
                                <span class="truncate">
                                    {option.icon} <span class="font-medium">{d.name}</span>
                                    {#if d.fullName}<span
                                            class="text-[11px] text-gray-400 dark:text-gray-500 ml-1">{d.fullName}</span>{/if}
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
                                {@const d = getOptionData(option)}
                                <span class="truncate">
                                    {option.icon} <span class="font-medium">{d.name}</span>
                                    {#if d.fullName}<span
                                            class="text-[11px] text-gray-400 dark:text-gray-500 ml-1">{d.fullName}</span>{/if}
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
            {#snippet children({item: signal})}
                {#if true}
                    {@const typeInfo = getSignalTypeInfo(signal.signalType)}
                    {@const signalName = typeInfo ? getSignalName(typeInfo) : signal.signalType}
                    {@const signalFullName = getSignalFullName(signal.signalType)}
                    {@const signalDescText = getSignalDesc(signal.signalType)}
                    {@const summary = signalSummaries.get(signal.id)}
                    {@const dataStartsLate = summary?.firstDate && dateStart && summary.firstDate > dateStart}
                    {@const hasNoData = summary && summary.pointCount === 0}
                    {@const conversionFailed = signal.signalType === 'asset-comparison' && Boolean(signal.params._conversionFailed)}
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
                                    <DocsLink path={typeInfo.docsPath} label={signalDescText || signalName} math/>
                                {/if}
                                {#if hasNoData}
                                    <Tooltip text={$t('chartSettings.noDataAvailable')} position="top">
                                        <AlertTriangle size={13} class="text-amber-500 shrink-0 cursor-help"/>
                                    </Tooltip>
                                {:else if conversionFailed}
                                    <Tooltip text={signal.params._conversionError ? String(signal.params._conversionError) : $t('chartSettings.conversionFailed')} position="top">
                                        <AlertTriangle size={13} class="text-amber-500 shrink-0 cursor-help"/>
                                    </Tooltip>
                                {:else if dataStartsLate}
                                    <Tooltip text={$t('chartSettings.dataMissingBefore', {values: {date: summary?.firstDate ?? ''}})} position="top">
                                        <AlertTriangle size={13} class="text-amber-500 shrink-0 cursor-help"/>
                                    </Tooltip>
                                {/if}
                            </div>
                            <div class="flex items-center gap-1 flex-shrink-0">
                                <!-- Summary badges (inline in title) -->
                                {#if summary && summary.pointCount > 0}
                                    <Tooltip text={$t('chartSettings.badgePoints', {values: {count: summary.pointCount}})} position="top">
                                        <span class="text-[10px] text-gray-400 dark:text-gray-500 px-1 py-0.5 bg-gray-100 dark:bg-slate-700 rounded cursor-help">
                                            📈{summary.pointCount}
                                        </span>
                                    </Tooltip>
                                {/if}
                                {#if summary}
                                    {#each Object.entries(summary.eventCounts) as [evType, count]}
                                        <Tooltip text={$t(`chartSettings.${EVENT_BADGE_KEY[evType] ?? 'badgePoints'}`, {values: {count}})} position="top">
                                            <span class="text-[10px] text-gray-400 dark:text-gray-500 px-1 py-0.5 bg-gray-100 dark:bg-slate-700 rounded cursor-help">
                                                {EVENT_EMOJI[evType] ?? '📊'}{count}
                                            </span>
                                        </Tooltip>
                                    {/each}
                                {/if}
                                <button
                                        type="button"
                                        class="p-1 rounded text-gray-400 hover:text-red-500 transition-colors"
                                        title={$t('chartSettings.removeSignal')}
                                        onclick={() => removeSignal(signal.id)}
                                >
                                    <Trash2 size={14}/>
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
                                                <Info size={12} class="text-gray-400 hover:text-libre-green cursor-help transition-colors"/>
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
                                                        <ArrowLeftRight size={12}/>
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
                                                            <RotateCw size={12} class={syncingPairs.has(pairSlug) ? 'animate-spin' : ''}/>
                                                        </button>
                                                    {/if}
                                                    {#if ondetailpair}
                                                        <button
                                                                type="button"
                                                                class="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-libre-green transition-colors"
                                                                title={$t('common.detail')}
                                                                onclick={() => ondetailpair?.(String(signal.params.pairSlug))}
                                                        >
                                                            <ExternalLink size={12}/>
                                                        </button>
                                                    {/if}
                                                </div>
                                            {:else if desc.dynamicOptionsKey === 'configuredAssets'}
                                                {@const assetIdStr = getParamString(signal, desc.key)}
                                                <div class="flex items-center gap-1">
                                                    <div class="w-48">
                                                        <SimpleSelect
                                                                value={assetIdStr}
                                                                options={resolveDynamicOptions('configuredAssets').map(o => {
                                                                    const aid = Number(o.value);
                                                                    const isCurrent = o.value === assetIdStr;
                                                                    const isMain = mainAssetId > 0 && aid === mainAssetId;
                                                                    const isUsedElsewhere = !isCurrent && usedAssetIds.has(aid);
                                                                    const suffix = isMain ? ' 👑' : isCurrent ? ' ✓' : isUsedElsewhere ? ' 📌' : '';
                                                                    return {...o, label: `${o.label}${suffix}`};
                                                                })}
                                                                placeholder="— Select asset"
                                                                dropdownPosition="auto"
                                                                onchange={(v) => updateSignalParam(signal.id, desc.key, v)}
                                                        >
                                                            {#snippet item(option)}
                                                                {@const info = findAssetInfo(option.value)}
                                                                <span class="flex items-center gap-1.5 truncate">
                                                                    {#if info?.icon_url}
                                                                        <img src={info.icon_url} alt="" class="w-4 h-4 rounded-full object-cover shrink-0" />
                                                                    {:else if info?.asset_type && ASSET_TYPE_ICON_MAP[info.asset_type]}
                                                                        <img src="/icons/asset-types/{ASSET_TYPE_ICON_MAP[info.asset_type]}.png" alt="" class="w-4 h-4 object-contain shrink-0" />
                                                                    {:else}
                                                                        <BarChart3 size={14} class="text-gray-400 shrink-0" />
                                                                    {/if}
                                                                    <span class="text-xs">{option.label}</span>
                                                                </span>
                                                            {/snippet}
                                                            {#snippet selectedItem(option)}
                                                                {@const info = findAssetInfo(option.value)}
                                                                <span class="flex items-center gap-1.5 truncate">
                                                                    {#if info?.icon_url}
                                                                        <img src={info.icon_url} alt="" class="w-4 h-4 rounded-full object-cover shrink-0" />
                                                                    {:else if info?.asset_type && ASSET_TYPE_ICON_MAP[info.asset_type]}
                                                                        <img src="/icons/asset-types/{ASSET_TYPE_ICON_MAP[info.asset_type]}.png" alt="" class="w-4 h-4 object-contain shrink-0" />
                                                                    {:else}
                                                                        <BarChart3 size={14} class="text-gray-400 shrink-0" />
                                                                    {/if}
                                                                    <span class="text-xs">{option.label}</span>
                                                                </span>
                                                            {/snippet}
                                                        </SimpleSelect>
                                                    </div>
                                                    {#if onsyncasset && assetIdStr}
                                                        {@const aid = Number(assetIdStr)}
                                                        <button
                                                                type="button"
                                                                class="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-blue-500 transition-colors"
                                                                title={$t('common.sync')}
                                                                disabled={syncingAssets.has(aid)}
                                                                onclick={() => handleSyncAssetWithSpin(aid)}
                                                        >
                                                            <RotateCw size={12} class={syncingAssets.has(aid) ? 'animate-spin' : ''}/>
                                                        </button>
                                                    {/if}
                                                    {#if ondetailasset && assetIdStr}
                                                        <button
                                                                type="button"
                                                                class="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-libre-green transition-colors"
                                                                title={$t('common.detail')}
                                                                onclick={() => ondetailasset?.(Number(assetIdStr))}
                                                        >
                                                            <ExternalLink size={12}/>
                                                        </button>
                                                    {/if}
                                                    {#if assetIdStr}
                                                        {@const currencyInfo = findAssetInfo(assetIdStr)}
                                                        {#if currencyInfo?.currency}
                                                            <span class="text-[10px] px-1.5 py-0.5 bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-gray-400 rounded font-mono">
                                                                {getCurrencyInfo(currencyInfo.currency).flag_emoji} {currencyInfo.currency}
                                                            </span>
                                                            <!-- FX pair controls for comparison signal -->
                                                            {#if displayCurrency && currencyInfo.currency !== displayCurrency}
                                                                {@const fxBase = currencyInfo.currency < displayCurrency ? currencyInfo.currency : displayCurrency}
                                                                {@const fxQuote = currencyInfo.currency < displayCurrency ? displayCurrency : currencyInfo.currency}
                                                                {@const fxSlug = `${fxBase}-${fxQuote}`}
                                                                {@const fxExists = configuredFxSlugs.includes(fxSlug)}
                                                                {#if !fxExists && oncreatefxpair}
                                                                    <Tooltip text={$t('assetDetail.fxPairMissing', {values: {base: fxBase, quote: fxQuote}})} position="top">
                                                                        <button
                                                                            type="button"
                                                                            class="p-0.5 rounded text-amber-500 hover:text-amber-600 transition-colors"
                                                                            onclick={() => oncreatefxpair?.(fxSlug)}
                                                                        >
                                                                            <AlertTriangle size={12}/>
                                                                        </button>
                                                                    </Tooltip>
                                                                {:else if fxExists && conversionFailed && onsyncfxpair}
                                                                    <Tooltip text={$t('chartSettings.conversionFailed')} position="top">
                                                                        <button
                                                                            type="button"
                                                                            class="p-0.5 rounded text-amber-500 hover:text-amber-600 transition-colors"
                                                                            onclick={() => onsyncfxpair?.(fxSlug)}
                                                                        >
                                                                            <RotateCw size={11}/>
                                                                        </button>
                                                                    </Tooltip>
                                                                {:else if fxExists}
                                                                    <a href="/fx/{fxSlug}" class="p-0.5 rounded text-gray-400 hover:text-libre-green transition-colors" title="FX {fxSlug.replace('-','/')}">
                                                                        <Coins size={11}/>
                                                                    </a>
                                                                {/if}
                                                            {/if}
                                                        {/if}
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
                                            <svg width="24" height="4">
                                                <line x1="2" y1="2" x2="22" y2="2" stroke={signal.style.color} stroke-width="1.5"
                                                      stroke-dasharray={lt === 'dashed' ? '4,2' : lt === 'dotted' ? '2,2' : 'none'}/>
                                            </svg>
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


