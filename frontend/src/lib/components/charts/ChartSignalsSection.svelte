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
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import SearchSelect from '$lib/components/ui/select/SearchSelect.svelte';
    import SignalStyleEditor from './SignalStyleEditor.svelte';
    import SignalParamControl from './SignalParamControl.svelte';
    import SignalVisualLegend from './SignalVisualLegend.svelte';
    import SignalTreeSelect, {type SignalTreeGroup} from './SignalTreeSelect.svelte';
    import {getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {createSignalConfig, getRegisteredSignalTypes, getSignalProblemSeverity, type SignalConfig, type SignalDefinition, type SignalIndicatorGroup, type SignalInputField, type SignalParamDescriptor, type SignalProblem, type SignalProblemSeverity, type SignalStyle} from '$lib/charts/signals';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {humanizeKey} from '$lib/utils/text';
    import {INPUT_FIELD_ORDER, formatSignalProblem, getParamNumber, getParamString} from './chartSignalsHelpers';

    import {numericArrows} from '$lib/actions/numericArrows';
    // =========================================================================
    // Types
    // =========================================================================

    export interface SignalDataSummary {
        pointCount: number;
        eventCounts: Record<string, number>;
        firstDate: string | null;
        problem?: SignalProblem;
    }

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Current signal configurations (bindable) */
        signals?: SignalConfig[];
        /** Definitions available in the current Asset/FX domain. */
        definitions?: SignalDefinition[];
        /** Explicit catalog/request error shown without hiding local signals. */
        backendError?: string | null;
        /** Retry callback for backend signal loading. */
        onretrybackend?: () => void;
        /** Available FX pairs for FxPairSignal (slug format: 'EUR-GBP') */
        availablePairs?: string[];
        /** Available assets for AssetComparisonSignal */
        availableAssets?: Array<{id: number; display_name: string; icon_url?: string | null; asset_type?: string | null; currency?: string}>;
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
        definitions,
        backendError = null,
        onretrybackend,
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

    let signalTypes = $derived(definitions ?? getRegisteredSignalTypes());

    function getSignalName(definition: SignalDefinition): string {
        if (!definition.displayNameKey) return definition.displayName;
        const translated = $t(definition.displayNameKey);
        return translated !== definition.displayNameKey ? translated : definition.displayName;
    }

    function translatedValue(key: string | undefined): string {
        if (!key) return '';
        const value = $t(key);
        return value !== key ? value : '';
    }

    function getSignalSubtitle(definition: SignalDefinition): string {
        if (definition.source === 'backend') return translatedValue(definition.descriptionKey);
        const fullKey = definition.displayNameKey ? `${definition.displayNameKey}Full` : undefined;
        return translatedValue(fullKey) || translatedValue(definition.descriptionKey);
    }

    function getSignalFullName(signalType: string): string {
        const definition = getSignalTypeInfo(signalType);
        return definition ? getSignalSubtitle(definition) : '';
    }

    function getSignalDesc(signalType: string): string {
        const definition = getSignalTypeInfo(signalType);
        return translatedValue(definition?.descriptionKey) || getSignalFullName(signalType);
    }

    function getSignalTypeInfo(signalType: string): SignalDefinition | undefined {
        return signalTypes.find((t) => t.type === signalType);
    }

    function signalFieldLabel(field: SignalInputField): string {
        return $t(`signals.dataFields.${field}`);
    }

    function signalParamAffectsLabel(definition: SignalDefinition, descriptor: SignalParamDescriptor): string {
        if (!descriptor.affectsOutputs?.length) return '';
        return descriptor.affectsOutputs
            .map((outputKey) => {
                const component = definition.visualComponents?.find((item) => item.key === outputKey);
                return component ? translatedValue(component.labelKey) || humanizeKey(component.key) : humanizeKey(outputKey);
            })
            .join(' · ');
    }

    // Adapts the i18n store to the injected translator the pure formatter expects.
    function translateProblem(key: string, values?: Record<string, string | number>): string {
        return values ? $t(key, {values}) : $t(key);
    }

    interface SignalIssue {
        message: string;
        severity: SignalProblemSeverity;
    }

    function getSignalIssue(signal: SignalConfig): SignalIssue | null {
        const summary = signalSummaries.get(signal.id);
        if (summary?.problem) {
            return {
                message: formatSignalProblem(summary.problem, translateProblem, signalFieldLabel),
                severity: getSignalProblemSeverity(summary.problem),
            };
        }
        if (signal.signalType === 'asset-comparison' && signal.params._conversionFailed) {
            return {
                message: signal.params._conversionError ? String(signal.params._conversionError) : $t('chartSettings.conversionFailed'),
                severity: 'error',
            };
        }
        if (summary && summary.pointCount === 0) {
            return {
                message: $t('chartSettings.noDataAvailable'),
                severity: 'error',
            };
        }
        if (summary?.firstDate && dateStart && summary.firstDate > dateStart) {
            return {
                message: $t('chartSettings.dataMissingBefore', {values: {date: summary.firstDate}}),
                severity: 'warning',
            };
        }
        return null;
    }

    function getSignalCardTone(signal: SignalConfig): 'default' | 'warning' | 'error' {
        const severity = getSignalIssue(signal)?.severity;
        if (severity === 'error') return 'error';
        if (severity === 'warning') return 'warning';
        return 'default';
    }

    // =========================================================================
    // Category dropdowns
    // =========================================================================

    const INDICATOR_GROUP_ORDER: SignalIndicatorGroup[] = ['trend', 'momentum', 'volatility', 'volume', 'risk'];

    function signalDataSubtitle(definition: SignalDefinition): string {
        const fields = new Set(definition.inputPriceFields ?? []);
        const labels = INPUT_FIELD_ORDER.filter((field) => fields.has(field)).map((field) => $t(`signals.dataFields.${field}`));
        return `${$t('signals.dataUsed')}: ${labels.join(', ')}`;
    }

    let indicatorGroups: SignalTreeGroup[] = $derived(
        INDICATOR_GROUP_ORDER.map((groupKey) => {
            const items = signalTypes.filter((definition) => definition.category === 'indicator' && definition.indicatorGroup === groupKey);
            return {
                key: groupKey,
                label: $t(`signals.groups.${groupKey}`),
                subtitle: $t('signals.dataShownPerIndicator'),
                items: items.map((definition) => {
                    const name = getSignalName(definition);
                    const subtitle = getSignalSubtitle(definition);
                    const dataSubtitle = signalDataSubtitle(definition);
                    return {
                        value: definition.type,
                        icon: definition.icon,
                        name,
                        subtitle,
                        dataSubtitle,
                        searchText: `${definition.type} ${definition.backendSignalCode ?? ''} ${name} ${subtitle} ${dataSubtitle}`.toLocaleLowerCase(),
                    };
                }),
            };
        }).filter((group) => group.items.length > 0),
    );

    function flatSignalGroups(category: 'comparison' | 'benchmark'): SignalTreeGroup[] {
        const items = signalTypes
            .filter((definition) => definition.category === category)
            .map((definition) => {
                const name = getSignalName(definition);
                const subtitle = getSignalSubtitle(definition);
                return {
                    value: definition.type,
                    icon: definition.icon,
                    name,
                    subtitle,
                    searchText: `${definition.type} ${name} ${subtitle}`.toLocaleLowerCase(),
                };
            });
        return items.length > 0
            ? [
                  {
                      key: category,
                      label: '',
                      subtitle: '',
                      items,
                  },
              ]
            : [];
    }

    let comparisonGroups = $derived(flatSignalGroups('comparison'));
    let benchmarkGroups = $derived(flatSignalGroups('benchmark'));

    let indicatorSelect = $state('');
    let comparisonSelect = $state('');
    let benchmarkSelect = $state('');

    // =========================================================================
    // Marker/Style constants
    // =========================================================================

    // =========================================================================
    // Signal management
    // =========================================================================

    function emitChange() {
        onchange?.(signals);
    }

    function addSignal(type: string) {
        const definition = getSignalTypeInfo(type);
        if (!definition) return;
        const usedColors = signals.map((s) => s.style.color);
        signals = [...signals, createSignalConfig(definition, signals.length, usedColors)];
        emitChange();
    }

    function removeSignal(id: string) {
        signals = signals.filter((s) => s.id !== id);
        emitChange();
    }

    function handleSignalReorder(newSignals: SignalConfig[]) {
        signals = newSignals;
        emitChange();
    }

    function updateSignalParam(id: string, key: string, value: unknown) {
        signals = signals.map((s) => (s.id === id ? {...s, params: {...s.params, [key]: value}} : s));
        emitChange();
    }

    function updateSignalStyle<K extends keyof SignalStyle>(id: string, key: K, value: SignalStyle[K]) {
        signals = signals.map((s) => (s.id === id ? {...s, style: {...s.style, [key]: value}} : s));
        emitChange();
    }

    function updateSignalComponentStyle(id: string, componentKey: string, style: SignalStyle) {
        signals = signals.map((signal) =>
            signal.id === id
                ? {
                      ...signal,
                      componentStyles: {
                          ...signal.componentStyles,
                          [componentKey]: style,
                      },
                  }
                : signal,
        );
        emitChange();
    }

    function updateSignalPartitionStyle(id: string, partitionKey: string, style: SignalStyle) {
        signals = signals.map((signal) =>
            signal.id === id
                ? {
                      ...signal,
                      partitionStyles: {
                          ...signal.partitionStyles,
                          [partitionKey]: style,
                      },
                  }
                : signal,
        );
        emitChange();
    }

    function resolveDynamicOptions(dynamicKey: string): Array<{value: string; label: string}> {
        if (dynamicKey === 'configuredFxPairs') {
            return availablePairs.map((slug) => ({
                value: slug,
                label: slug.replace('-', '/'),
            }));
        }
        if (dynamicKey === 'configuredAssets') {
            return (availableAssets ?? []).map((a) => ({
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
            syncingPairs = new Set([...syncingPairs].filter((s) => s !== slug));
        }
    }

    /** Set of asset IDs currently syncing (for rotating icon) */
    let syncingAssets = $state<Set<number>>(new Set());

    async function handleSyncAssetWithSpin(assetId: number) {
        syncingAssets = new Set([...syncingAssets, assetId]);
        try {
            await onsyncasset?.(assetId);
        } finally {
            syncingAssets = new Set([...syncingAssets].filter((id) => id !== assetId));
        }
    }

    /** Set of pair slugs already used by other FxPair signals */
    let usedPairSlugs = $derived(new Set(signals.filter((s) => s.signalType === 'fx-pair' && s.params.pairSlug).map((s) => String(s.params.pairSlug))));

    /** Find asset info by id for icon rendering */
    function findAssetInfo(assetId: string) {
        return (availableAssets ?? []).find((a) => String(a.id) === assetId);
    }

    /** Set of asset IDs already used by asset-comparison signals */
    let usedAssetIds = $derived(new Set(signals.filter((s) => s.signalType === 'asset-comparison' && s.params.assetId).map((s) => Number(s.params.assetId))));

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

    {#if backendError}
        <div class="mb-3 flex items-center justify-between gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-800/60 dark:bg-amber-950/30 dark:text-amber-200" data-testid="signal-backend-error">
            <span class="flex items-center gap-1.5">
                <AlertTriangle size={13} />
                {backendError}
            </span>
            {#if onretrybackend}
                <button type="button" class="font-semibold underline underline-offset-2" onclick={onretrybackend}>
                    {$t('common.retry')}
                </button>
            {/if}
        </div>
    {/if}

    <!-- Add signal dropdowns by category -->
    <div class="mb-3">
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {#if indicatorGroups.length > 0}
                <div>
                    <span class="block text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase mb-1">📊 {$t('chartSettings.categories.indicator')}</span>
                    <SignalTreeSelect
                        bind:value={indicatorSelect}
                        groups={indicatorGroups}
                        placeholder={$t('common.select')}
                        testId="signals-indicator-select"
                        onchange={(v) => {
                            addSignal(v);
                            indicatorSelect = '';
                        }}
                    />
                </div>
            {/if}
            {#if comparisonGroups.length > 0}
                <div>
                    <span class="block text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase mb-1">💱 {$t('chartSettings.categories.comparison')}</span>
                    <SignalTreeSelect
                        bind:value={comparisonSelect}
                        groups={comparisonGroups}
                        placeholder={$t('common.select')}
                        testId="signals-comparison-select"
                        flat
                        onchange={(v) => {
                            addSignal(v);
                            comparisonSelect = '';
                        }}
                    />
                </div>
            {/if}
            {#if benchmarkGroups.length > 0}
                <div>
                    <span class="block text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase mb-1">📐 {$t('chartSettings.categories.benchmark')}</span>
                    <SignalTreeSelect
                        bind:value={benchmarkSelect}
                        groups={benchmarkGroups}
                        placeholder={$t('common.select')}
                        testId="signals-benchmark-select"
                        flat
                        onchange={(v) => {
                            addSignal(v);
                            benchmarkSelect = '';
                        }}
                    />
                </div>
            {/if}
        </div>
    </div>

    {#if signals.length === 0}
        <p class="text-xs text-gray-400 dark:text-gray-500 italic mb-3">
            {$t('chartSettings.noSignals')}
        </p>
    {:else}
        <OrderableList items={signals} keyFn={(s) => s.id} onReorder={handleSignalReorder} responsiveGrid minItemWidth="32rem" itemTone={getSignalCardTone}>
            {#snippet children({item: signal})}
                {#if true}
                    {@const typeInfo = getSignalTypeInfo(signal.signalType)}
                    {@const signalName = typeInfo ? getSignalName(typeInfo) : signal.signalType}
                    {@const signalFullName = getSignalFullName(signal.signalType)}
                    {@const signalDescText = getSignalDesc(signal.signalType)}
                    {@const summary = signalSummaries.get(signal.id)}
                    {@const issue = getSignalIssue(signal)}
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
                                    <DocsLink path={typeInfo.docsPath} label={signalDescText || signalName} math />
                                {/if}
                                {#if issue}
                                    <Tooltip text={issue.message} position="top" maxWidth="min(34rem, calc(100vw - 16px))">
                                        {#if issue.severity === 'notice'}
                                            <span class="-my-2 flex h-9 w-9 shrink-0 items-center justify-center text-gray-400 sm:my-0 sm:h-4 sm:w-4">
                                                <Info size={14} class="cursor-help" />
                                            </span>
                                        {:else}
                                            <span class="-my-2 flex h-9 w-9 shrink-0 items-center justify-center sm:my-0 sm:h-4 sm:w-4 {issue.severity === 'error' ? 'text-red-500' : 'text-amber-500'}">
                                                <AlertTriangle size={14} class="cursor-help" />
                                            </span>
                                        {/if}
                                    </Tooltip>
                                {/if}
                            </div>
                            <div class="flex items-center gap-1 flex-shrink-0">
                                <!-- Summary badges (inline in title) -->
                                {#if summary && summary.pointCount > 0}
                                    <Tooltip text={$t('chartSettings.badgePoints', {values: {n: summary.pointCount}})} position="top">
                                        <span class="text-[10px] text-gray-400 dark:text-gray-500 px-1 py-0.5 bg-gray-100 dark:bg-slate-700 rounded cursor-help">
                                            📈{summary.pointCount}
                                        </span>
                                    </Tooltip>
                                {/if}
                                {#if summary}
                                    {#each Object.entries(summary.eventCounts) as [evType, count]}
                                        <Tooltip text={$t(`chartSettings.${EVENT_BADGE_KEY[evType] ?? 'badgePoints'}`, {values: {n: count}})} position="top">
                                            <span class="text-[10px] text-gray-400 dark:text-gray-500 px-1 py-0.5 bg-gray-100 dark:bg-slate-700 rounded cursor-help">
                                                {EVENT_EMOJI[evType] ?? '📊'}{count}
                                            </span>
                                        </Tooltip>
                                    {/each}
                                {/if}
                                <button type="button" class="p-1 rounded text-gray-400 hover:text-red-500 transition-colors" title={$t('chartSettings.removeSignal')} onclick={() => removeSignal(signal.id)}>
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        </div>

                        <!-- Parameters -->
                        {#if typeInfo && typeInfo.paramDescriptors.length > 0}
                            <div class="flex flex-wrap gap-2">
                                {#each typeInfo.paramDescriptors as desc}
                                    {#if typeInfo.source === 'backend'}
                                        <SignalParamControl descriptor={desc} value={signal.params[desc.key]} affectsLabel={signalParamAffectsLabel(typeInfo, desc)} onchange={(value) => updateSignalParam(signal.id, desc.key, value)} />
                                    {:else}
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
                                                        use:numericArrows
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
                                                        <div class="w-44">
                                                            <SearchSelect
                                                                value={currentPairSlug}
                                                                options={resolveDynamicOptions('configuredFxPairs').map((o) => {
                                                                    const parts = o.value.split('-');
                                                                    const isCurrent = o.value === currentPairSlug;
                                                                    const showInverted = isCurrent && Boolean(signal.params._inverted);
                                                                    const base = showInverted ? parts[1] : parts[0];
                                                                    const quote = showInverted ? parts[0] : parts[1];
                                                                    const baseFlag = getCurrencyInfo(base).flag_emoji;
                                                                    const quoteFlag = getCurrencyInfo(quote).flag_emoji;
                                                                    const isUsedElsewhere = !isCurrent && usedPairSlugs.has(o.value);
                                                                    const isMain = !!mainPairSlug && o.value === mainPairSlug;
                                                                    const suffix = isMain ? ' 👑' : isCurrent ? ' ✓' : isUsedElsewhere ? ' 📌' : '';
                                                                    return {value: o.value, label: `${baseFlag} ${base} ↔ ${quoteFlag} ${quote}${suffix}`, searchText: `${base} ${quote}`};
                                                                })}
                                                                placeholder="— {$t('chartSettings.params.currencyPair')}"
                                                                dropdownPosition="auto"
                                                                maxVisibleItems={8}
                                                                inlineSearch={true}
                                                                onchange={(v) => {
                                                                    updateSignalParam(signal.id, desc.key, v);
                                                                    updateSignalParam(signal.id, '_inverted', false);
                                                                }}
                                                            >
                                                                {#snippet item(option)}
                                                                    <span class="flex items-center gap-1 text-xs whitespace-nowrap">{option.label}</span>
                                                                {/snippet}
                                                                {#snippet selectedItem(option)}
                                                                    <span class="flex items-center gap-1 text-xs whitespace-nowrap">{option.label}</span>
                                                                {/snippet}
                                                            </SearchSelect>
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
                                                            <button type="button" class="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-libre-green transition-colors" title={$t('common.detail')} onclick={() => ondetailpair?.(String(signal.params.pairSlug))}>
                                                                <ExternalLink size={12} />
                                                            </button>
                                                        {/if}
                                                    </div>
                                                {:else if desc.dynamicOptionsKey === 'configuredAssets'}
                                                    {@const assetIdStr = getParamString(signal, desc.key)}
                                                    <div class="flex items-center gap-1">
                                                        <div class="w-48">
                                                            <SearchSelect
                                                                value={assetIdStr}
                                                                options={resolveDynamicOptions('configuredAssets').map((o) => {
                                                                    const aid = Number(o.value);
                                                                    const isCurrent = o.value === assetIdStr;
                                                                    const isMain = mainAssetId > 0 && aid === mainAssetId;
                                                                    const isUsedElsewhere = !isCurrent && usedAssetIds.has(aid);
                                                                    const suffix = isMain ? ' 👑' : isCurrent ? ' ✓' : isUsedElsewhere ? ' 📌' : '';
                                                                    return {...o, label: `${o.label}${suffix}`};
                                                                })}
                                                                placeholder="— Select asset"
                                                                dropdownPosition="auto"
                                                                maxVisibleItems={8}
                                                                inlineSearch={true}
                                                                onchange={(v) => updateSignalParam(signal.id, desc.key, v)}
                                                            >
                                                                {#snippet item(option)}
                                                                    {@const info = findAssetInfo(option.value)}
                                                                    <span class="flex items-center gap-1.5 truncate">
                                                                        {#if info?.icon_url}
                                                                            <img src={info.icon_url} alt="" class="w-4 h-4 rounded-full object-cover shrink-0" />
                                                                        {:else if info?.asset_type}
                                                                            <img src={getAssetTypeIconUrl(info.asset_type)} alt="" class="w-4 h-4 object-contain shrink-0" />
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
                                                                        {:else if info?.asset_type}
                                                                            <img src={getAssetTypeIconUrl(info.asset_type)} alt="" class="w-4 h-4 object-contain shrink-0" />
                                                                        {:else}
                                                                            <BarChart3 size={14} class="text-gray-400 shrink-0" />
                                                                        {/if}
                                                                        <span class="text-xs">{option.label}</span>
                                                                    </span>
                                                                {/snippet}
                                                            </SearchSelect>
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
                                                                <RotateCw size={12} class={syncingAssets.has(aid) ? 'animate-spin' : ''} />
                                                            </button>
                                                        {/if}
                                                        {#if ondetailasset && assetIdStr}
                                                            <button type="button" class="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-libre-green transition-colors" title={$t('common.detail')} onclick={() => ondetailasset?.(Number(assetIdStr))}>
                                                                <ExternalLink size={12} />
                                                            </button>
                                                        {/if}
                                                        {#if assetIdStr}
                                                            {@const currencyInfo = findAssetInfo(assetIdStr)}
                                                            {#if currencyInfo?.currency}
                                                                <span class="text-[10px] px-1.5 py-0.5 bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-gray-400 rounded font-mono">
                                                                    {getCurrencyInfo(currencyInfo.currency).flag_emoji}
                                                                    {currencyInfo.currency}
                                                                </span>
                                                                <!-- FX pair controls for comparison signal -->
                                                                {#if displayCurrency && currencyInfo.currency !== displayCurrency}
                                                                    {@const fxBase = currencyInfo.currency < displayCurrency ? currencyInfo.currency : displayCurrency}
                                                                    {@const fxQuote = currencyInfo.currency < displayCurrency ? displayCurrency : currencyInfo.currency}
                                                                    {@const fxSlug = `${fxBase}-${fxQuote}`}
                                                                    {@const fxExists = configuredFxSlugs.includes(fxSlug)}
                                                                    {#if !fxExists && oncreatefxpair}
                                                                        <Tooltip text={$t('assetDetail.fxPairMissing', {values: {base: fxBase, quote: fxQuote}})} position="top">
                                                                            <button type="button" class="p-0.5 rounded text-amber-500 hover:text-amber-600 transition-colors" onclick={() => oncreatefxpair?.(fxSlug)}>
                                                                                <AlertTriangle size={12} />
                                                                            </button>
                                                                        </Tooltip>
                                                                    {:else if fxExists && conversionFailed && onsyncfxpair}
                                                                        <Tooltip text={$t('chartSettings.conversionFailed')} position="top">
                                                                            <button type="button" class="p-0.5 rounded text-amber-500 hover:text-amber-600 transition-colors" onclick={() => onsyncfxpair?.(fxSlug)}>
                                                                                <RotateCw size={11} />
                                                                            </button>
                                                                        </Tooltip>
                                                                    {:else if fxExists}
                                                                        <a href="/fx/{fxSlug}" class="p-0.5 rounded text-gray-400 hover:text-libre-green transition-colors" title="FX {fxSlug.replace('-', '/')}">
                                                                            <Coins size={11} />
                                                                        </a>
                                                                    {/if}
                                                                {/if}
                                                            {/if}
                                                        {/if}
                                                    </div>
                                                {:else}
                                                    {@const opts = desc.options ?? []}
                                                    <div class="w-36">
                                                        <SimpleSelect value={getParamString(signal, desc.key)} options={opts} dropdownPosition="auto" onchange={(v) => updateSignalParam(signal.id, desc.key, v)} />
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
                                    {/if}
                                {/each}
                            </div>
                        {/if}

                        {#if typeInfo?.source === 'backend'}
                            <SignalVisualLegend
                                definition={typeInfo}
                                {signalName}
                                config={signal}
                                oncomponentstylechange={(componentKey, style) => updateSignalComponentStyle(signal.id, componentKey, style)}
                                onpartitionstylechange={(partitionKey, style) => updateSignalPartitionStyle(signal.id, partitionKey, style)}
                            />
                        {/if}

                        <!-- Local signal style strip. Backend components own their individual editors above. -->
                        {#if typeInfo?.source !== 'backend' && signal.signalType !== 'macd'}
                            <div class="pt-1.5 border-t border-gray-100 dark:border-slate-700">
                                <SignalStyleEditor style={signal.style} onstylechange={(key, value) => updateSignalStyle(signal.id, key, value)} hideLineType={typeInfo?.source === 'local' && signal.signalType === 'rsi'} />
                            </div>
                        {/if}

                        <!-- MACD: simplified single color+line style (full MACD popover stays in modal for now) -->
                        {#if typeInfo?.source === 'local' && signal.signalType === 'macd'}
                            <div class="flex items-center gap-1.5 pt-1.5 border-t border-gray-100 dark:border-slate-700">
                                <input type="color" value={signal.style.color} class="w-6 h-6 p-0 border border-gray-200 dark:border-slate-600 rounded cursor-pointer shrink-0" title={$t('chartSettings.macdLineColor')} oninput={(e) => updateSignalStyle(signal.id, 'color', e.currentTarget.value)} />
                                <span class="text-[10px] text-gray-400 dark:text-gray-500">MACD</span>
                                <SignalStyleEditor style={signal.style} onstylechange={(key, value) => updateSignalStyle(signal.id, key, value)} />
                            </div>
                        {/if}
                    </div>
                {/if}
            {/snippet}
        </OrderableList>
    {/if}
</div>
