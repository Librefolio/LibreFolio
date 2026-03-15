<!--
  FxProviderSelect.svelte — Svelte 5

  Unified FX route selection component for currency pair creation/editing.
  Two-part layout:
    1. OrderableList — shows selected routes with drag & drop priority + remove
    2. Collapsible picker — DFS pathfinding with sections + full-text search

  Features:
  - DFS pathfinding for direct and chain conversion routes
  - Provider info bar with icons, tooltips (multilingual), and docs links
  - Direct routes section (1-step)
  - Chain routes organized in collapsible menus by step count
  - Chains sorted by provider count (ascending), then alphabetically
  - Full-text search (AND logic per space-separated token)
  - Provider icons (from icon_url) with initials fallback
  - Currency flag emojis on route items
  - OrderableList for selected route priority (drag & drop)
  - MANUAL provider is never shown (backend-only sentinel)
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {Link, Check, AlertTriangle, Loader2, ArrowRight, Search, X, Plus, Trash2, ChevronDown, ChevronUp, Info} from 'lucide-svelte';
    import {findConversionPaths, getCachedProviders} from '$lib/stores/currencyGraphStore';
    import {getCurrencyInfo} from '$lib/stores/currencyStore';
    import type {ChainStep, ProviderInfo} from '$lib/utils/currencyGraph';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';
    import {getProviderColor, getPriorityBadgeStyle} from '$lib/utils/colors';

    // =========================================================================
    // Types
    // =========================================================================

    /** A selectable route option (1-step or multi-step). */
    export interface RouteOption {
        key: string;
        chainSteps: ChainStep[];
        label: string;
        providers: string[];
        stepCount: number;
        isDirect: boolean;
        searchText: string;
    }

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        baseCurrency?: string;
        quoteCurrency?: string;
        selectedRoutes?: ChainStep[][];
        onSelectionChange?: (routes: ChainStep[][]) => void;
        language?: string;
        disabled?: boolean;
    }

    let {
        baseCurrency = '',
        quoteCurrency = '',
        selectedRoutes = $bindable([]),
        onSelectionChange,
        language = 'en',
        disabled = false,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let loading = $state(false);
    let error = $state<string | null>(null);
    let directRoutes = $state<RouteOption[]>([]);
    let chainRoutes = $state<RouteOption[]>([]);
    let unusableProviders = $state<ProviderInfo[]>([]);
    let selectedKeys = $state<Set<string>>(new Set());
    let searchQuery = $state('');
    /** Whether the "Add route" picker is expanded */
    let pickerOpen = $state(false);
    /** Ordered list of selected route keys (for priority) */
    let orderedSelectedKeys = $state<string[]>([]);
    /** Set of expanded chain group step counts */
    let expandedChainGroups = $state<Set<number>>(new Set());

    // =========================================================================
    // Derived
    // =========================================================================

    let hasCurrencies = $derived(!!baseCurrency && !!quoteCurrency && baseCurrency !== quoteCurrency);
    let hasAnyRoutes = $derived(directRoutes.length > 0 || chainRoutes.length > 0);
    let allRoutes = $derived([...directRoutes, ...chainRoutes]);
    let routeMap = $derived(new Map(allRoutes.map(r => [r.key, r])));

    /** Routes in selection order for OrderableList */
    let orderedSelected = $derived(
        orderedSelectedKeys.map(k => routeMap.get(k)).filter((r): r is RouteOption => !!r)
    );

    /** Provider info map for quick lookup */
    let providerMap = $derived(new Map(getCachedProviders().map(p => [p.code, p])));

    /** All providers used in any route (for the info bar) */
    let usedProviders = $derived.by(() => {
        const usedCodes = new Set<string>();
        for (const route of allRoutes) {
            for (const code of route.providers) {
                usedCodes.add(code);
            }
        }
        const providers = getCachedProviders().filter(p => usedCodes.has(p.code));
        return providers.sort((a, b) => a.code.localeCompare(b.code));
    });

    /** Search tokens (AND logic) */
    let searchTokens = $derived(
        searchQuery.trim().toLowerCase().split(/\s+/).filter(t => t.length > 0)
    );

    function matchesSearch(route: RouteOption): boolean {
        if (searchTokens.length === 0) return true;
        return searchTokens.every(token => route.searchText.includes(token));
    }

    function matchesProviderSearch(prov: ProviderInfo): boolean {
        if (searchTokens.length === 0) return true;
        const text = `${prov.code} ${prov.name}`.toLowerCase();
        return searchTokens.every(token => text.includes(token));
    }

    /** Unselected routes filtered by search */
    let filteredDirect = $derived(directRoutes.filter(r => !selectedKeys.has(r.key) && matchesSearch(r)));

    /** Chain routes sorted: by provider count ascending, then alphabetically by key */
    let sortedChainRoutes = $derived(
        [...chainRoutes].sort((a, b) => {
            if (a.stepCount !== b.stepCount) return a.stepCount - b.stepCount;
            // Within same step count, sort by unique provider count, then alphabetically
            const aUnique = new Set(a.providers).size;
            const bUnique = new Set(b.providers).size;
            if (aUnique !== bUnique) return aUnique - bUnique;
            return a.key.localeCompare(b.key);
        })
    );

    /** Chain routes grouped by stepCount, filtered */
    let chainGroups = $derived.by(() => {
        const filtered = sortedChainRoutes.filter(r => !selectedKeys.has(r.key) && matchesSearch(r));
        const groupMap = new Map<number, RouteOption[]>();
        for (const route of filtered) {
            if (!groupMap.has(route.stepCount)) {
                groupMap.set(route.stepCount, []);
            }
            groupMap.get(route.stepCount)!.push(route);
        }
        return [...groupMap.entries()]
            .sort(([a], [b]) => a - b)
            .map(([stepCount, routes]) => ({stepCount, routes}));
    });

    let filteredUnusable = $derived(unusableProviders.filter(matchesProviderSearch));
    let hasFilteredRoutes = $derived(filteredDirect.length > 0 || chainGroups.length > 0);
    let hasUnselectedRoutes = $derived(allRoutes.some(r => !selectedKeys.has(r.key)));

    // =========================================================================
    // Path computation
    // =========================================================================

    $effect(() => {
        if (hasCurrencies) {
            computeRoutes(baseCurrency, quoteCurrency);
        } else {
            directRoutes = [];
            chainRoutes = [];
            unusableProviders = [];
            selectedKeys = new Set();
            orderedSelectedKeys = [];
            searchQuery = '';
            pickerOpen = false;
            expandedChainGroups = new Set();
        }
    });

    function buildSearchText(path: ChainStep[], providers: ProviderInfo[]): string {
        const parts: string[] = [];
        for (const step of path) {
            parts.push(step.provider);
            const prov = providers.find(p => p.code === step.provider);
            if (prov) parts.push(prov.name);
        }
        const currencyCodes = new Set<string>();
        for (const step of path) {
            currencyCodes.add(step.from);
            currencyCodes.add(step.to);
        }
        for (const code of currencyCodes) {
            const info = getCurrencyInfo(code);
            parts.push(code, info.name, info.flag_emoji, ...info.country_names);
        }
        return parts.join(' ').toLowerCase();
    }

    async function computeRoutes(base: string, quote: string) {
        loading = true;
        error = null;
        try {
            const paths = await findConversionPaths(base, quote, 4, language);
            const providers = getCachedProviders();
            const direct: RouteOption[] = [];
            const chain: RouteOption[] = [];
            const usedProviderCodes = new Set<string>();

            for (const path of paths) {
                const provCodes = path.map(s => s.provider);
                provCodes.forEach(c => usedProviderCodes.add(c));
                const key = path.map(s => `${s.from}-${s.to}:${s.provider}`).join('|');
                const searchText = buildSearchText(path, providers);

                if (path.length === 1) {
                    const provInfo = providers.find(p => p.code === path[0].provider);
                    direct.push({
                        key, chainSteps: path,
                        label: provInfo?.name ?? path[0].provider,
                        providers: provCodes, stepCount: 1, isDirect: true, searchText,
                    });
                } else {
                    const intermediates = path.slice(0, -1).map(s => s.to);
                    const provNames = provCodes.join(' + ');
                    chain.push({
                        key, chainSteps: path,
                        label: `via ${intermediates.join(', ')} (${provNames})`,
                        providers: provCodes, stepCount: path.length, isDirect: false, searchText,
                    });
                }
            }

            directRoutes = direct;
            chainRoutes = chain;
            unusableProviders = providers.filter(
                p => p.code !== 'MANUAL' && !usedProviderCodes.has(p.code)
            );

            // Auto-expand: if direct routes exist they're always visible, so no chain expansion needed.
            // If no direct routes, expand the first chain group only.
            expandedChainGroups = new Set();
            if (direct.length === 0) {
                const groups = getChainGroupStepCounts(chain);
                if (groups.length > 0) {
                    expandedChainGroups = new Set([groups[0]]);
                }
            }
        } catch (e) {
            console.error('Failed to compute conversion routes:', e);
            error = 'Failed to load conversion routes';
        } finally {
            loading = false;
        }
    }

    /** Helper to get sorted step counts from chain routes */
    function getChainGroupStepCounts(chains: RouteOption[]): number[] {
        const counts = new Set<number>();
        for (const route of chains) counts.add(route.stepCount);
        return [...counts].sort((a, b) => a - b);
    }

    // =========================================================================
    // Provider icon helper
    // =========================================================================

    function getProviderIconUrl(code: string): string | null {
        return providerMap.get(code)?.icon_url ?? null;
    }

    function getProviderInitials(code: string): string {
        return code.slice(0, 2).toUpperCase();
    }

    /** Get the provider description for the current language, with 'en' fallback */
    function getProviderDescription(prov: ProviderInfo): string {
        if (prov.description_i18n && Object.keys(prov.description_i18n).length > 0) {
            return prov.description_i18n[language] ?? prov.description_i18n['en'] ?? prov.description ?? '';
        }
        return prov.description ?? '';
    }

    /** Get provider name for a code */
    function getProviderName(code: string): string {
        return providerMap.get(code)?.name ?? code;
    }

    /** Get provider description for a code */
    function getProviderDescByCode(code: string): string {
        const prov = providerMap.get(code);
        return prov ? getProviderDescription(prov) : '';
    }

    // =========================================================================
    // Chain group toggle
    // =========================================================================

    function toggleChainGroup(stepCount: number) {
        const newSet = new Set(expandedChainGroups);
        if (newSet.has(stepCount)) {
            newSet.delete(stepCount);
        } else {
            newSet.add(stepCount);
        }
        expandedChainGroups = newSet;
    }

    // =========================================================================
    // Selection handlers
    // =========================================================================

    function addRoute(route: RouteOption) {
        if (disabled || selectedKeys.has(route.key)) return;
        const newKeys = new Set(selectedKeys);
        newKeys.add(route.key);
        selectedKeys = newKeys;
        orderedSelectedKeys = [...orderedSelectedKeys, route.key];
        emitSelection();
    }

    function removeRoute(key: string) {
        if (disabled) return;
        const newKeys = new Set(selectedKeys);
        newKeys.delete(key);
        selectedKeys = newKeys;
        orderedSelectedKeys = orderedSelectedKeys.filter(k => k !== key);
        emitSelection();
    }

    function handleReorder(newItems: RouteOption[]) {
        orderedSelectedKeys = newItems.map(r => r.key);
        emitSelection();
    }

    function emitSelection() {
        const selected = orderedSelectedKeys
            .map(k => routeMap.get(k))
            .filter((r): r is RouteOption => !!r)
            .map(r => r.chainSteps);
        selectedRoutes = selected;
        onSelectionChange?.(selected);
    }

    function clearSearch() {
        searchQuery = '';
    }

    function routeKey(route: RouteOption): string {
        return route.key;
    }
</script>


<!-- ===================================================================== -->
<!-- COMPONENT TEMPLATE                                                    -->
<!-- ===================================================================== -->

{#if loading}
    <div class="flex items-center justify-center gap-2 py-4 text-xs text-gray-400 dark:text-gray-500">
        <Loader2 size={14} class="animate-spin" />
        <span>{$_('fx.route.loading')}</span>
    </div>
{:else if error}
    <div class="text-xs text-red-500 dark:text-red-400 py-2">{error}</div>
{:else if hasCurrencies}
    <div class="space-y-3 {disabled ? 'opacity-50 pointer-events-none' : ''}" data-testid="fx-route-select">

        <!-- ============================================================= -->
        <!-- SELECTED ROUTES — OrderableList with priority                 -->
        <!-- ============================================================= -->
        {#if orderedSelected.length > 0}
            <OrderableList
                items={orderedSelected}
                keyFn={routeKey}
                onReorder={handleReorder}
                {disabled}
            >
                {#snippet children({ item: route, index })}
                    <div class="flex items-center gap-2 min-w-0">
                        <!-- Route visualization -->
                        {#if route.isDirect}
                            {@const step = route.chainSteps[0]}
                            {@const fromInfo = getCurrencyInfo(step.from)}
                            {@const toInfo = getCurrencyInfo(step.to)}
                            {@const iconUrl = getProviderIconUrl(step.provider)}
                            {@const provColor = getProviderColor(step.provider)}
                            <span class="text-sm flex-shrink-0">{fromInfo.flag_emoji}</span>
                            <span class="font-medium text-[11px] text-gray-600 dark:text-gray-300">{step.from}</span>
                            <span class="relative group/prov inline-flex items-center gap-0.5 px-1 py-0.5 rounded border flex-shrink-0 cursor-help"
                                  style="background: var(--prov-bg); border-color: var(--prov-border); --prov-bg: {provColor.bg}; --prov-border: {provColor.border}"
                                  class:dark-override={true}
                            >
                                <ArrowRight size={10} class="text-gray-400 flex-shrink-0" />
                                {#if iconUrl}
                                    <img src={iconUrl} alt={step.provider} class="w-5 h-5 rounded object-contain p-0.5 flex-shrink-0" />
                                {:else}
                                    <span class="w-5 h-5 flex items-center justify-center rounded text-[8px] font-bold flex-shrink-0">{getProviderInitials(step.provider)}</span>
                                {/if}
                                <ArrowRight size={10} class="text-gray-400 flex-shrink-0" />
                                <span class="provider-tooltip">
                                    <span class="font-semibold">{getProviderName(step.provider)}</span><br/>
                                    {getProviderDescByCode(step.provider)}
                                </span>
                            </span>
                            <span class="text-sm flex-shrink-0">{toInfo.flag_emoji}</span>
                            <span class="font-medium text-[11px] text-gray-600 dark:text-gray-300">{step.to}</span>
                        {:else}
                            <!-- Chain route -->
                            <span class="flex items-center gap-0.5 flex-wrap flex-1 min-w-0">
                                {#each route.chainSteps as step, i}
                                    {@const fromInfo = getCurrencyInfo(step.from)}
                                    {@const toInfo = getCurrencyInfo(step.to)}
                                    {@const iconUrl = getProviderIconUrl(step.provider)}
                                    {@const provColor = getProviderColor(step.provider)}
                                    {#if i === 0}
                                        <span class="text-sm">{fromInfo.flag_emoji}</span>
                                        <span class="font-medium text-[11px] text-gray-600 dark:text-gray-300">{step.from}</span>
                                    {/if}
                                    <span class="relative group/prov inline-flex items-center gap-0.5 px-1 py-0.5 rounded border flex-shrink-0 cursor-help"
                                          style="background: var(--prov-bg); border-color: var(--prov-border); --prov-bg: {provColor.bg}; --prov-border: {provColor.border}"
                                    >
                                        <ArrowRight size={8} class="text-gray-400 flex-shrink-0" />
                                        {#if iconUrl}
                                            <img src={iconUrl} alt={step.provider} class="w-4 h-4 rounded object-contain p-0.5 flex-shrink-0" />
                                        {:else}
                                            <span class="w-4 h-4 flex items-center justify-center rounded text-[7px] font-bold flex-shrink-0">{getProviderInitials(step.provider)}</span>
                                        {/if}
                                        <ArrowRight size={8} class="text-gray-400 flex-shrink-0" />
                                        <span class="provider-tooltip">
                                            <span class="font-semibold">{getProviderName(step.provider)}</span><br/>
                                            {getProviderDescByCode(step.provider)}
                                        </span>
                                    </span>
                                    <span class="text-sm">{toInfo.flag_emoji}</span>
                                    <span class="font-medium text-[11px] text-gray-600 dark:text-gray-300">{step.to}</span>
                                {/each}
                            </span>
                        {/if}
                        <!-- Priority badge (Fibonacci colors) -->
                        <span class="text-[10px] font-mono px-1.5 py-0.5 rounded flex-shrink-0 ml-auto priority-badge"
                              style={getPriorityBadgeStyle(index)}>
                            #{index + 1}
                        </span>
                        <!-- Remove button -->
                        {#if !disabled}
                            <button
                                type="button"
                                class="p-1 rounded-md hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 transition-all flex-shrink-0"
                                onclick={() => removeRoute(route.key)}
                                title="Remove"
                            >
                                <Trash2 size={13} />
                            </button>
                        {/if}
                    </div>
                {/snippet}
            </OrderableList>
        {/if}

        <!-- ============================================================= -->
        <!-- ADD ROUTE — Collapsible picker                                -->
        <!-- ============================================================= -->
        {#if hasAnyRoutes && hasUnselectedRoutes}
            <button
                type="button"
                class="w-full flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border border-dashed transition-colors
                    {pickerOpen
                        ? 'border-libre-green bg-libre-green/5 text-libre-green'
                        : 'border-gray-300 dark:border-slate-600 text-gray-500 dark:text-gray-400 hover:border-libre-green hover:text-libre-green'}"
                onclick={() => { pickerOpen = !pickerOpen; }}
            >
                {#if pickerOpen}
                    <ChevronUp size={14} />
                    {$_('fx.route.hideRoutes')}
                {:else}
                    <Plus size={14} />
                    {$_('fx.route.addRoute')}
                {/if}
            </button>
        {/if}

        {#if pickerOpen && hasUnselectedRoutes}
            <div class="space-y-2 p-3 bg-gray-50/50 dark:bg-slate-800/50 rounded-lg border border-gray-200 dark:border-slate-700">

                <!-- ========================================================= -->
                <!-- PROVIDER INFO BAR — Icons with tooltips + docs links      -->
                <!-- ========================================================= -->
                {#if usedProviders.length > 0}
                    <div class="flex items-center gap-2 pb-2 border-b border-gray-200 dark:border-slate-700">
                        <span class="text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider flex-shrink-0">
                            {$_('fx.route.providersLabel')}
                        </span>
                        <div class="flex items-center gap-1.5 flex-wrap">
                            {#each usedProviders as prov}
                                {@const iconUrl = prov.icon_url}
                                {@const provColor = getProviderColor(prov.code)}
                                {@const description = getProviderDescription(prov)}
                                <a
                                    href={prov.docs_url ?? '/mkdocs/developer/backend/fx/providers_list/'}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    class="group relative inline-flex items-center gap-1 px-1.5 py-1 rounded border transition-all cursor-pointer hover:shadow-sm"
                                    style="background: {provColor.bg}; border-color: {provColor.border}"
                                >
                                    {#if iconUrl}
                                        <img src={iconUrl} alt={prov.code} class="w-4 h-4 rounded object-contain flex-shrink-0" />
                                    {:else}
                                        <span class="w-4 h-4 flex items-center justify-center rounded text-[7px] font-bold flex-shrink-0">{getProviderInitials(prov.code)}</span>
                                    {/if}
                                    <span class="text-[10px] font-semibold text-gray-600 dark:text-gray-300">{prov.code}</span>
                                    <!-- Tooltip on hover -->
                                    <span class="provider-tooltip">
                                        <span class="font-semibold">{prov.name}</span><br/>
                                        {description}
                                    </span>
                                </a>
                            {/each}
                        </div>
                    </div>
                {/if}

                <!-- Search input -->
                <div class="relative">
                    <Search size={13} class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 pointer-events-none" />
                    <input
                        type="text"
                        bind:value={searchQuery}
                        placeholder={$_('fx.route.searchPlaceholder')}
                        class="w-full pl-8 pr-8 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 focus:ring-1 focus:ring-libre-green focus:border-libre-green outline-none transition-colors"
                    />
                    {#if searchQuery}
                        <button
                            class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                            onclick={clearSearch}
                        >
                            <X size={13} />
                        </button>
                    {/if}
                </div>

                <!-- Direct routes -->
                {#if filteredDirect.length > 0}
                    <div class="space-y-1" data-testid="fx-route-direct-section">
                        <h4 class="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
                            <Check size={10} class="text-emerald-500" />
                            {$_('fx.route.directSection')}
                            <span class="ml-1 text-[9px] font-mono px-1 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400">{filteredDirect.length}</span>
                        </h4>
                        {#each filteredDirect as route (route.key)}
                            {@const step = route.chainSteps[0]}
                            {@const fromInfo = getCurrencyInfo(step.from)}
                            {@const toInfo = getCurrencyInfo(step.to)}
                            {@const iconUrl = getProviderIconUrl(step.provider)}
                            {@const provColor = getProviderColor(step.provider)}
                            <button
                                type="button"
                                data-testid="fx-route-direct-{route.providers[0]}"
                                class="w-full text-left px-2.5 py-1.5 rounded-lg border transition-all text-xs border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 hover:border-emerald-300 dark:hover:border-emerald-700 hover:bg-emerald-50/50 dark:hover:bg-emerald-900/10"
                                onclick={() => addRoute(route)}
                            >
                                <span class="flex items-center gap-1.5">
                                    <Plus size={12} class="text-emerald-500 flex-shrink-0" />
                                    <span class="text-sm">{fromInfo.flag_emoji}</span>
                                    <span class="font-medium text-gray-600 dark:text-gray-300 text-[11px]">{step.from}</span>
                                    <span class="relative group/prov inline-flex items-center gap-0.5 px-1 py-0.5 rounded border flex-shrink-0"
                                          style="background: {provColor.bg}; border-color: {provColor.border}">
                                        <ArrowRight size={10} class="text-gray-400 dark:text-gray-500 flex-shrink-0" />
                                        {#if iconUrl}
                                            <img src={iconUrl} alt={step.provider} class="w-5 h-5 rounded object-contain p-0.5 flex-shrink-0" />
                                        {:else}
                                            <span class="w-5 h-5 flex items-center justify-center rounded text-[8px] font-bold flex-shrink-0">{getProviderInitials(step.provider)}</span>
                                        {/if}
                                        <ArrowRight size={10} class="text-gray-400 dark:text-gray-500 flex-shrink-0" />
                                        <span class="provider-tooltip">
                                            <span class="font-semibold">{getProviderName(step.provider)}</span><br/>
                                            {getProviderDescByCode(step.provider)}
                                        </span>
                                    </span>
                                    <span class="text-sm">{toInfo.flag_emoji}</span>
                                    <span class="font-medium text-gray-600 dark:text-gray-300 text-[11px]">{step.to}</span>
                                    <span class="ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 flex-shrink-0">1 step</span>
                                </span>
                            </button>
                        {/each}
                    </div>
                {/if}

                <!-- Chain routes — Collapsible groups by step count -->
                {#each chainGroups as group (group.stepCount)}
                    {@const isExpanded = expandedChainGroups.has(group.stepCount)}
                    <div class="space-y-1" data-testid="fx-route-chain-section-{group.stepCount}">
                        <!-- Collapsible header -->
                        <button
                            type="button"
                            class="w-full flex items-center gap-1.5 text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
                            onclick={() => toggleChainGroup(group.stepCount)}
                        >
                            {#if isExpanded}
                                <ChevronUp size={10} class="text-blue-500 flex-shrink-0" />
                            {:else}
                                <ChevronDown size={10} class="text-blue-500 flex-shrink-0" />
                            {/if}
                            <Link size={10} class="text-blue-500" />
                            {$_('fx.route.chainSection')} — {group.stepCount} {$_('fx.route.steps')}
                            <span class="ml-1 text-[9px] font-mono px-1 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400">{group.routes.length}</span>
                            <!-- Chain risk info icon -->
                            <!-- svelte-ignore a11y_click_events_have_key_events -->
                            <!-- svelte-ignore a11y_no_static_element_interactions -->
                            <span class="relative group/info flex-shrink-0 ml-0.5 cursor-help" onclick={(e) => e.stopPropagation()}>
                                <Info size={10} class="text-blue-400 dark:text-blue-500" />
                                <span class="provider-tooltip">
                                    {$_('fx.route.chainWarning')}
                                </span>
                            </span>
                        </button>

                        <!-- Collapsible content -->
                        {#if isExpanded}
                            {#each group.routes as route (route.key)}
                                <button
                                    type="button"
                                    data-testid="fx-route-chain-{route.stepCount}step-{route.providers.join('-')}"
                                    class="w-full text-left px-2.5 py-1.5 rounded-lg border transition-all text-xs border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 hover:border-blue-300 dark:hover:border-blue-700 hover:bg-blue-50/50 dark:hover:bg-blue-900/10"
                                    onclick={() => addRoute(route)}
                                >
                                    <span class="flex items-center gap-1.5">
                                        <Plus size={12} class="text-blue-500 flex-shrink-0" />
                                        <span class="flex items-center gap-0.5 flex-wrap flex-1 min-w-0">
                                            {#each route.chainSteps as step, i}
                                                {@const fromInfo = getCurrencyInfo(step.from)}
                                                {@const toInfo = getCurrencyInfo(step.to)}
                                                {@const iconUrl = getProviderIconUrl(step.provider)}
                                                {@const provColor = getProviderColor(step.provider)}
                                                {#if i === 0}
                                                    <span class="text-sm">{fromInfo.flag_emoji}</span>
                                                    <span class="font-medium text-[11px] text-gray-600 dark:text-gray-300">{step.from}</span>
                                                {/if}
                                                <span class="relative group/prov inline-flex items-center gap-0.5 px-0.5 py-0.5 rounded border flex-shrink-0"
                                                      style="background: {provColor.bg}; border-color: {provColor.border}">
                                                    <ArrowRight size={8} class="text-gray-400 dark:text-gray-500 flex-shrink-0" />
                                                    {#if iconUrl}
                                                        <img src={iconUrl} alt={step.provider} class="w-4 h-4 rounded object-contain p-0.5 flex-shrink-0" />
                                                    {:else}
                                                        <span class="w-4 h-4 flex items-center justify-center rounded text-[7px] font-bold flex-shrink-0">{getProviderInitials(step.provider)}</span>
                                                    {/if}
                                                    <ArrowRight size={8} class="text-gray-400 dark:text-gray-500 flex-shrink-0" />
                                                    <span class="provider-tooltip">
                                                        <span class="font-semibold">{getProviderName(step.provider)}</span><br/>
                                                        {getProviderDescByCode(step.provider)}
                                                    </span>
                                                </span>
                                                <span class="text-sm">{toInfo.flag_emoji}</span>
                                                <span class="font-medium text-[11px] text-gray-600 dark:text-gray-300">{step.to}</span>
                                            {/each}
                                        </span>
                                        <span class="ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 flex-shrink-0 whitespace-nowrap">
                                            {route.stepCount} {$_('fx.route.steps')}
                                        </span>
                                    </span>
                                </button>
                            {/each}
                        {/if}
                    </div>
                {/each}

                <!-- Unusable providers -->
                {#if filteredUnusable.length > 0}
                    <div class="space-y-1">
                        <h4 class="text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider flex items-center gap-1.5">
                            <AlertTriangle size={10} class="text-gray-400 dark:text-gray-500" />
                            {$_('fx.route.unusableSection')}
                        </h4>
                        <div class="px-2.5 py-1.5 rounded-lg border border-dashed border-gray-200 dark:border-slate-700 bg-gray-50/50 dark:bg-slate-800/50">
                            <div class="flex flex-wrap gap-1.5">
                                {#each filteredUnusable as prov}
                                    <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-gray-100 dark:bg-slate-700 text-gray-400 dark:text-gray-500 line-through">
                                        {prov.code}
                                    </span>
                                {/each}
                            </div>
                            <p class="text-[10px] text-gray-400 dark:text-gray-500 mt-1">
                                {$_('fx.route.unusableHint')}
                            </p>
                        </div>
                    </div>
                {/if}

                <!-- No search results -->
                {#if !hasFilteredRoutes && searchTokens.length > 0}
                    <div class="text-xs text-gray-400 dark:text-gray-500 text-center py-2">
                        {$_('fx.route.noSearchResults')}
                    </div>
                {/if}
            </div>
        {/if}

        <!-- No routes available at all -->
        {#if !hasAnyRoutes && !loading}
            <div class="px-3 py-3 rounded-lg border border-dashed border-amber-300 dark:border-amber-700 bg-amber-50/50 dark:bg-amber-900/10">
                <div class="flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400">
                    <AlertTriangle size={12} />
                    <span>{$_('fx.route.noRoutesAvailable')}</span>
                </div>
            </div>
        {/if}

        <!-- Chain warning banner -->
        {#if orderedSelected.some(r => !r.isDirect)}
            <div class="px-2.5 py-2 rounded-lg bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 text-[10px] text-blue-600 dark:text-blue-400 flex items-start gap-2">
                <Link size={10} class="flex-shrink-0 mt-0.5" />
                <span>{$_('fx.route.chainWarning')}</span>
            </div>
        {/if}
    </div>
{/if}

<style>
    .priority-badge {
        background-color: var(--badge-bg);
        color: var(--badge-text);
    }
    :global(.dark) .priority-badge {
        background-color: var(--badge-dark-bg);
        color: var(--badge-dark-text);
    }
    :global(.dark) [style*="--prov-bg"] {
        background: var(--prov-dark-bg, var(--prov-bg)) !important;
    }

    /* Provider tooltip */
    .provider-tooltip {
        display: none;
        position: absolute;
        bottom: calc(100% + 6px);
        left: 50%;
        transform: translateX(-50%);
        z-index: 50;
        width: max-content;
        max-width: 280px;
        padding: 6px 10px;
        border-radius: 6px;
        font-size: 10px;
        line-height: 1.4;
        white-space: normal;
        text-transform: none;
        letter-spacing: normal;
        font-weight: normal;
        color: white;
        background: rgba(15, 23, 42, 0.95);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        pointer-events: none;
    }
    .provider-tooltip::after {
        content: '';
        position: absolute;
        top: 100%;
        left: 50%;
        transform: translateX(-50%);
        border: 5px solid transparent;
        border-top-color: rgba(15, 23, 42, 0.95);
    }
    a:hover > .provider-tooltip,
    a:focus > .provider-tooltip,
    :global(.group\/prov):hover > .provider-tooltip,
    :global(.group\/info):hover > .provider-tooltip {
        display: block;
    }
</style>

