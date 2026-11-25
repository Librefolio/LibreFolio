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
  - Provider initials badges with color-coded backgrounds
  - Currency flag emojis on route items
  - OrderableList for selected route priority (drag & drop)
  - MANUAL provider is never shown (backend-only sentinel)
  - A route through a provider that is not configured is switched off (project 76, N3c): dashed, an amber «settings»
    icon in place of +, reachable; a touch asks the parent to explain (`onneedssetup`), it never adds the route. A
    provider the pair's saved routes already use (`savedProviderCodes`) is never switched off, and a selected route
    through a provider that is not configured shows a yellow triangle that asks the same.
  - The standard buttons (85 BTN-2c): the triangle, the remove, the picker toggle, the search clear and «show more».
    The triangle is never `reason` or `disabled`: its click must reach `onneedssetup`. The route rows and the chain
    headers stay hand-written (rich content: flags, provider marks, badges).
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {AlertTriangle, ArrowLeftRight, Check, ChevronDown, ChevronUp, Info, Link, Loader2, Plus, Search, SlidersHorizontal, Trash2, X} from 'lucide-svelte';
    import {findConversionPaths, fxProvidersVersion, getCachedFxProviders, refreshFxProviderReadiness} from '$lib/stores/currencyGraphStore';
    import {untrack} from 'svelte';
    import {getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import type {ChainStep, ProviderInfo} from '$lib/utils/currency/currencyGraph';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';
    import {getPriorityBadgeStyle, getProviderColor} from '$lib/utils/colors';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import Button from '$lib/components/ui/button/Button.svelte';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';

    /** A provider note's level (`warning_level`): a data limit that can mislead, or a fact worth knowing. */
    type NoteLevel = 'info' | 'warning';
    const NOTE_SIGN: Record<NoteLevel, string> = {info: 'ℹ️', warning: '⚠️'};

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
        /** Slugs of already-configured FX pairs (e.g. ["EUR-USD","GBP-USD"]) for sorting */
        configuredPairSlugs?: string[];
        /**
         * The providers the pair's saved routes already use (project 76, N3c): never switched off, even when not
         * configured — the backend accepts a provider already on the pair (N2). Empty for a new pair.
         */
        savedProviderCodes?: string[];
        /** A provider that is not configured was touched (a switched-off route, a triangle): the parent says why. */
        onneedssetup?: (provider: ProviderInfo) => void;
    }

    let {baseCurrency = '', quoteCurrency = '', selectedRoutes = $bindable([]), onSelectionChange, language = 'en', disabled = false, configuredPairSlugs = [], savedProviderCodes = [], onneedssetup}: Props = $props();

    // N3c: the readiness of the cached providers is read again when the picker mounts (a key saved elsewhere since)
    $effect(() => {
        untrack(() => void refreshFxProviderReadiness());
    });

    /** The providers that are not configured, by code (their list entry says so): read again when the cache moves. */
    let unconfigured = $derived.by(() => {
        void $fxProvidersVersion;
        return new Map(
            getCachedFxProviders()
                .filter((p) => p.configured === false)
                .map((p) => [p.code, p]),
        );
    });
    /** Of those, the ones whose routes are switched off: not already on the pair. */
    let blocked = $derived(new Set([...unconfigured.keys()].filter((code) => !savedProviderCodes.includes(code))));

    /** The first provider of a route that switches it off, or undefined. */
    function blockedBy(route: RouteOption): ProviderInfo | undefined {
        const code = route.providers.find((c) => blocked.has(c));
        return code === undefined ? undefined : unconfigured.get(code);
    }

    /** The first provider of a route that is not configured (switched off or not), or undefined. */
    function unconfiguredOf(route: RouteOption): ProviderInfo | undefined {
        const code = route.providers.find((c) => unconfigured.has(c));
        return code === undefined ? undefined : unconfigured.get(code);
    }

    function setupHint(provider: ProviderInfo): string {
        return $_('pluginSettings.notConfigured.tooltip', {values: {provider: provider.name}});
    }

    // =========================================================================
    // State
    // =========================================================================

    let loading = $state(false);
    let error = $state<string | null>(null);
    // Raw, not deep: the routes are only ever replaced whole, and a deep proxy over tens of thousands of routes (a pair
    // once the wave-1 banks are in) cost seconds at the picker's first read (lane 75, L2b).
    let directRoutes = $state.raw<RouteOption[]>([]);
    let chainRoutes = $state.raw<RouteOption[]>([]);
    let unusableProviders = $state<ProviderInfo[]>([]);
    /** A provider came without its currency list (backend could not read it): «no route» would be a guess, not an answer. */
    let providersUnavailable = $state(false);
    let selectedKeys = $state<Set<string>>(new Set());
    let searchQuery = $state('');
    /** Whether the "Add route" picker is expanded */
    let pickerOpen = $state(false);
    /** Ordered list of selected route keys (for priority) */
    let orderedSelectedKeys = $state<string[]>([]);
    /** Set of expanded chain group step counts */
    let expandedChainGroups = $state<Set<number>>(new Set());

    /**
     * How many chains an open group draws: the first CHAIN_PAGE in today's order, CHAIN_PAGE more per «show more».
     * The search always filters every chain. Developer decision «b1» (lane 75, L2d): drawn whole, the 4-step group of a
     * pair such as NOK→USD (~36 000 chains once the wave-1 banks are in) crashed the browser tab.
     */
    const CHAIN_PAGE = 200;
    /** Chains shown per group after «show more»: every change of the search (cleared included) or of the routes starts over. */
    let shownChains = $state<Record<number, number>>({});

    function chainLimit(stepCount: number): number {
        return shownChains[stepCount] ?? CHAIN_PAGE;
    }

    function showMoreChains(stepCount: number) {
        shownChains = {...shownChains, [stepCount]: chainLimit(stepCount) + CHAIN_PAGE};
    }

    // =========================================================================
    // Derived
    // =========================================================================

    let hasCurrencies = $derived(!!baseCurrency && !!quoteCurrency && baseCurrency !== quoteCurrency);
    let hasAnyRoutes = $derived(directRoutes.length > 0 || chainRoutes.length > 0);
    let allRoutes = $derived([...directRoutes, ...chainRoutes]);
    let routeMap = $derived(new Map(allRoutes.map((r) => [r.key, r])));

    /** Routes in selection order for OrderableList */
    let orderedSelected = $derived(orderedSelectedKeys.map((k) => routeMap.get(k)).filter((r): r is RouteOption => !!r));

    /** Provider info map for quick lookup */
    let providerMap = $derived(new Map(getCachedFxProviders().map((p) => [p.code, p])));

    /** All providers used in any route (for the info bar) */
    let usedProviders = $derived.by(() => {
        const usedCodes = new Set<string>();
        for (const route of allRoutes) {
            for (const code of route.providers) {
                usedCodes.add(code);
            }
        }
        const providers = getCachedFxProviders().filter((p) => usedCodes.has(p.code));
        return providers.sort((a, b) => a.code.localeCompare(b.code));
    });

    /** Search tokens (AND logic) */
    let searchTokens = $derived(
        searchQuery
            .trim()
            .toLowerCase()
            .split(/\s+/)
            .filter((t) => t.length > 0),
    );

    function matchesSearch(route: RouteOption): boolean {
        if (searchTokens.length === 0) return true;
        const text = searchTextOf(route);
        return searchTokens.every((token) => text.includes(token));
    }

    function matchesProviderSearch(prov: ProviderInfo): boolean {
        if (searchTokens.length === 0) return true;
        const text = `${prov.code} ${prov.name}`.toLowerCase();
        return searchTokens.every((token) => text.includes(token));
    }

    /** Unselected routes filtered by search */
    let filteredDirect = $derived(directRoutes.filter((r) => !selectedKeys.has(r.key) && matchesSearch(r)));

    /** Set of configured pair slugs for fast lookup */
    let configuredSet = $derived(new Set(configuredPairSlugs));

    /** Count how many intermediate legs of a route are already configured pairs */
    function countConfiguredLegs(route: RouteOption): number {
        let count = 0;
        for (const step of route.chainSteps) {
            const slug = [step.from, step.to].sort().join('-');
            if (configuredSet.has(slug)) count++;
        }
        return count;
    }

    /** Chain routes sorted: configured-legs desc, then step count asc, then unique providers asc, then key */
    let sortedChainRoutes = $derived(
        [...chainRoutes].sort((a, b) => {
            if (a.stepCount !== b.stepCount) return a.stepCount - b.stepCount;
            // Within same step count, prefer routes with more already-configured intermediate legs
            const aConf = countConfiguredLegs(a);
            const bConf = countConfiguredLegs(b);
            if (aConf !== bConf) return bConf - aConf; // descending: more configured = first
            // Then by unique provider count, then alphabetically
            const aUnique = new Set(a.providers).size;
            const bUnique = new Set(b.providers).size;
            if (aUnique !== bUnique) return aUnique - bUnique;
            return a.key.localeCompare(b.key);
        }),
    );

    /** Chain routes grouped by stepCount, filtered */
    let chainGroups = $derived.by(() => {
        const filtered = sortedChainRoutes.filter((r) => !selectedKeys.has(r.key) && matchesSearch(r));
        const groupMap = new Map<number, RouteOption[]>();
        for (const route of filtered) {
            if (!groupMap.has(route.stepCount)) {
                groupMap.set(route.stepCount, []);
            }
            groupMap.get(route.stepCount)!.push(route);
        }
        return [...groupMap.entries()].sort(([a], [b]) => a - b).map(([stepCount, routes]) => ({stepCount, routes}));
    });

    let filteredUnusable = $derived(unusableProviders.filter(matchesProviderSearch));
    let hasFilteredRoutes = $derived(filteredDirect.length > 0 || chainGroups.length > 0);
    let hasUnselectedRoutes = $derived(allRoutes.some((r) => !selectedKeys.has(r.key)));

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
            const prov = providers.find((p) => p.code === step.provider);
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

    /** Each route's search text, built at the first search, not for every route of every pair (lane 75, L2b: ~60 ms
     * for the ~37 000 routes of a pair once the wave-1 banks are in). Cleared when the routes are recomputed. */
    const searchTexts = new Map<string, string>();

    function searchTextOf(route: RouteOption): string {
        let text = searchTexts.get(route.key);
        if (text === undefined) {
            text = buildSearchText(route.chainSteps, getCachedFxProviders());
            searchTexts.set(route.key, text);
        }
        return text;
    }

    /** The latest route search: an answer that arrives after a newer request is dropped (the search runs in a Web
     * Worker, lane 75 L20b, so a pair changed while it ran can be answered out of order). */
    let routeRequest = 0;

    async function computeRoutes(base: string, quote: string) {
        const request = ++routeRequest;
        loading = true;
        error = null;
        try {
            const paths = await findConversionPaths(base, quote, 4);
            if (request !== routeRequest) return;
            const providers = getCachedFxProviders();
            searchTexts.clear();
            shownChains = {};
            const direct: RouteOption[] = [];
            const chain: RouteOption[] = [];
            const usedProviderCodes = new Set<string>();

            for (const path of paths) {
                const provCodes = path.map((s) => s.provider);
                provCodes.forEach((c) => usedProviderCodes.add(c));
                const key = path.map((s) => `${s.from}-${s.to}:${s.provider}`).join('|');

                if (path.length === 1) {
                    const provInfo = providers.find((p) => p.code === path[0].provider);
                    direct.push({
                        key,
                        chainSteps: path,
                        label: provInfo?.name ?? path[0].provider,
                        providers: provCodes,
                        stepCount: 1,
                        isDirect: true,
                    });
                } else {
                    const intermediates = path.slice(0, -1).map((s) => s.to);
                    const provNames = provCodes.join(' + ');
                    chain.push({
                        key,
                        chainSteps: path,
                        label: `via ${intermediates.join(', ')} (${provNames})`,
                        providers: provCodes,
                        stepCount: path.length,
                        isDirect: false,
                    });
                }
            }

            directRoutes = direct;
            chainRoutes = chain;
            providersUnavailable = providers.some((p) => p.currencies_unavailable);
            unusableProviders = providers.filter((p) => p.code !== 'MANUAL' && !p.currencies_unavailable && !usedProviderCodes.has(p.code));

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
            if (request !== routeRequest) return;
            console.error('Failed to compute conversion routes:', e);
            error = 'Failed to load conversion routes';
        } finally {
            if (request === routeRequest) loading = false;
        }
    }

    /** Helper to get sorted step counts from chain routes */
    function getChainGroupStepCounts(chains: RouteOption[]): number[] {
        const counts = new Set<number>();
        for (const route of chains) counts.add(route.stepCount);
        return [...counts].sort((a, b) => a - b);
    }

    /**
     * Build a direction-agnostic key for a chain: sort each step's currencies
     * alphabetically and sort steps, so both directions produce the same key.
     */
    function normalizeChainKey(steps: ChainStep[]): string {
        return steps
            .map((s) => {
                const [a, b] = [s.from, s.to].sort();
                return `${a}-${b}:${s.provider}`;
            })
            .sort()
            .join('|');
    }

    // Sync internal selectedKeys when selectedRoutes is set externally (e.g., by parent's loadRoutesFromBackend)
    $effect(() => {
        if (allRoutes.length === 0 || selectedRoutes.length === 0) return;

        // Build a normalized-key → route-key lookup from DFS-computed allRoutes
        const normalizedToKey = new Map<string, string>();
        for (const route of allRoutes) {
            normalizedToKey.set(normalizeChainKey(route.chainSteps), route.key);
        }

        // Match each selectedRoute by normalized key (direction-agnostic)
        const matchedKeys: string[] = [];
        for (const route of selectedRoutes) {
            // Try exact key first
            const exactKey = route.map((s) => `${s.from}-${s.to}:${s.provider}`).join('|');
            if (routeMap.has(exactKey) && !selectedKeys.has(exactKey)) {
                matchedKeys.push(exactKey);
                continue;
            }
            // Fallback: direction-agnostic match
            const normKey = normalizeChainKey(route);
            const dfsKey = normalizedToKey.get(normKey);
            if (dfsKey && !selectedKeys.has(dfsKey)) {
                matchedKeys.push(dfsKey);
            }
        }
        if (matchedKeys.length > 0) {
            const newKeys = new Set(selectedKeys);
            for (const k of matchedKeys) newKeys.add(k);
            selectedKeys = newKeys;
            // Preserve existing order + add new at end
            const existing = new Set(orderedSelectedKeys);
            orderedSelectedKeys = [...orderedSelectedKeys, ...matchedKeys.filter((k) => !existing.has(k))];
        }
    });

    // =========================================================================
    // Provider display helpers
    // =========================================================================

    function getProviderInitials(code: string): string {
        return code.slice(0, 2).toUpperCase();
    }

    /** Get FX provider icon URL (or null if not available) */
    function getFxProviderIconUrl(code: string): string | null {
        return providerMap.get(code)?.icon_url ?? null;
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

    /** Get provider warning for the current language, with 'en' fallback. Empty = no warning. */
    function getProviderWarning(code: string): string {
        const prov = providerMap.get(code);
        if (!prov?.warning_i18n || Object.keys(prov.warning_i18n).length === 0) return '';
        return prov.warning_i18n[language] ?? prov.warning_i18n['en'] ?? '';
    }

    /** How serious a provider's note is: 'warning' (⚠️) unless the provider marks it 'info' (ℹ️). */
    function getProviderWarningLevel(code: string): NoteLevel {
        return providerMap.get(code)?.warning_level === 'info' ? 'info' : 'warning';
    }

    /** Collect all unique provider notes for a route (deduplicated), each led by its level's sign. */
    function getRouteWarnings(route: RouteOption): string[] {
        const seen = new Set<string>();
        const warnings: string[] = [];
        for (const code of route.providers) {
            if (seen.has(code)) continue;
            seen.add(code);
            const w = getProviderWarning(code);
            if (w) warnings.push(`${NOTE_SIGN[getProviderWarningLevel(code)]} ${getProviderName(code)}: ${w}`);
        }
        return warnings;
    }

    /** The most serious level among the notes of a route's providers; '' when none has a note. */
    function getRouteWarningLevel(route: RouteOption): NoteLevel | '' {
        const levels = route.providers.filter((code) => getProviderWarning(code)).map(getProviderWarningLevel);
        if (levels.length === 0) return '';
        return levels.includes('warning') ? 'warning' : 'info';
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
        orderedSelectedKeys = orderedSelectedKeys.filter((k) => k !== key);
        emitSelection();
    }

    function handleReorder(newItems: RouteOption[]) {
        orderedSelectedKeys = newItems.map((r) => r.key);
        emitSelection();
    }

    function emitSelection() {
        const selected = orderedSelectedKeys
            .map((k) => routeMap.get(k))
            .filter((r): r is RouteOption => !!r)
            .map((r) => r.chainSteps);
        selectedRoutes = selected;
        onSelectionChange?.(selected);
    }

    function clearSearch() {
        searchQuery = '';
        shownChains = {};
    }

    function routeKey(route: RouteOption): string {
        return route.key;
    }

    // =========================================================================
    // Tooltip HTML builders
    // =========================================================================

    /** Escape HTML entities for safe tooltip content */
    /** Build HTML tooltip for a provider badge */
    function providerTooltipHtml(code: string): string {
        return `<strong>${escapeHtml(getProviderName(code))}</strong><br/>${escapeHtml(getProviderDescByCode(code))}`;
    }

    /** Build HTML tooltip for warning messages list */
    function warningsTooltipHtml(warnings: string[]): string {
        return warnings.map((w) => escapeHtml(w)).join('<br/><br/>');
    }

    /**
     * The providers legend (R1-C of project 67, the developer, 20/11): a plain click on an entry only shows or hides its
     * tooltip, a double click opens the provider's guide. The entry stays a link, so the keyboard (Enter: a click with no
     * pointer, `detail` 0), a click with a modifier key, a middle click and the long press of a phone keep opening it.
     */
    function keepClickForTooltip(event: MouseEvent): void {
        if (event.detail > 0 && event.button === 0 && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) event.preventDefault();
    }

    function openProviderGuide(event: MouseEvent, href: string): void {
        event.preventDefault();
        window.open(href, '_blank', 'noopener,noreferrer');
    }

    /** Build HTML tooltip for provider legend badge (name + desc + optional warning) */
    function legendTooltipHtml(prov: ProviderInfo): string {
        const desc = getProviderDescription(prov);
        const warning = getProviderWarning(prov.code);
        const level = getProviderWarningLevel(prov.code);
        let h = `<strong>${escapeHtml(prov.name)}</strong><br/>${escapeHtml(desc)}`;
        if (warning) h += `<br/><br/><span class="${level === 'info' ? 'text-lf-info-on-inverse' : 'text-lf-warning-on-inverse'}">${escapeHtml(NOTE_SIGN[level])} ${escapeHtml(warning)}</span>`;
        return h;
    }
</script>

<!-- ===================================================================== -->
<!-- COMPONENT TEMPLATE                                                    -->
<!-- ===================================================================== -->

<!-- A provider note's sign: ℹ️ for a fact worth knowing, ⚠️ for a data limit that can mislead -->
{#snippet noteIcon(level: NoteLevel | '', size: number)}
    {#if level === 'info'}
        <Info {size} class="text-lf-info flex-shrink-0" data-testid="fx-route-note-icon" data-level="info" />
    {:else}
        <AlertTriangle {size} class="text-lf-warning flex-shrink-0" data-testid="fx-route-note-icon" data-level="warning" />
    {/if}
{/snippet}

<!-- One provider's mark: its icon when it carries one, else its initials. The legend and every route draw it through this
     piece (81 U34: the legend drew only the initials). `md` = 20 px (a route's own step), `sm` = 16 px (a chain's step and the legend). -->
{#snippet providerMark(code: string, size: 'sm' | 'md')}
    {@const iconUrl = getFxProviderIconUrl(code)}
    {@const box = size === 'md' ? 'w-5 h-5' : 'w-4 h-4'}
    {#if iconUrl}
        <img src={iconUrl} alt={code} class="{box} rounded object-contain p-0.5 flex-shrink-0" />
    {:else}
        <span class="{box} flex items-center justify-center rounded {size === 'md' ? 'text-[8px]' : 'text-[7px]'} font-bold flex-shrink-0">{getProviderInitials(code)}</span>
    {/if}
{/snippet}

{#if loading}
    <div class="flex items-center justify-center gap-2 py-4 text-xs text-lf-muted" data-testid="fx-route-loading">
        <Loader2 size={14} class="animate-spin" />
        <span>{$_('fx.route.loading')}</span>
    </div>
{:else if error}
    <div class="text-xs text-lf-danger py-2" data-testid="fx-route-error">{error}</div>
{:else if hasCurrencies}
    <div class="space-y-3 text-lf-primary {disabled ? 'opacity-50 pointer-events-none' : ''}" data-testid="fx-route-select">
        <!-- ============================================================= -->
        <!-- SELECTED ROUTES — OrderableList with priority                 -->
        <!-- ============================================================= -->
        {#if orderedSelected.length > 0}
            <OrderableList items={orderedSelected} keyFn={routeKey} onReorder={handleReorder} {disabled}>
                {#snippet children({item: route, index})}
                    <div class="flex items-center gap-2 min-w-0" data-testid="fx-route-selected" data-route-key={route.key} data-priority={index + 1} data-warnings={getRouteWarnings(route).length} data-warning-level={getRouteWarningLevel(route)}>
                        <!-- Route visualization -->
                        {#if route.isDirect}
                            {@const step = route.chainSteps[0]}
                            {@const fromInfo = getCurrencyInfo(step.from)}
                            {@const toInfo = getCurrencyInfo(step.to)}
                            {@const provColor = getProviderColor(step.provider)}
                            <span class="text-sm flex-shrink-0 emoji-flag">{fromInfo.flag_emoji}</span>
                            <span class="font-medium text-[11px] text-lf-secondary">{step.from}</span>
                            <Tooltip html={providerTooltipHtml(step.provider)} position="top">
                                <span class="inline-flex items-center gap-0.5 px-1 py-0.5 rounded border flex-shrink-0" style="background: var(--prov-bg); border-color: var(--prov-border); --prov-bg: {provColor.bg}; --prov-border: {provColor.border}">
                                    <ArrowLeftRight size={10} class="text-lf-muted flex-shrink-0" />
                                    {@render providerMark(step.provider, 'md')}
                                    <ArrowLeftRight size={10} class="text-lf-muted flex-shrink-0" />
                                </span>
                            </Tooltip>
                            <span class="text-sm flex-shrink-0 emoji-flag">{toInfo.flag_emoji}</span>
                            <span class="font-medium text-[11px] text-lf-secondary">{step.to}</span>
                        {:else}
                            <!-- Chain route -->
                            <span class="flex items-center gap-0.5 flex-wrap flex-1 min-w-0">
                                {#each route.chainSteps as step, i}
                                    {@const fromInfo = getCurrencyInfo(step.from)}
                                    {@const toInfo = getCurrencyInfo(step.to)}
                                    {@const provColor = getProviderColor(step.provider)}
                                    {#if i === 0}
                                        <span class="text-sm emoji-flag">{fromInfo.flag_emoji}</span>
                                        <span class="font-medium text-[11px] text-lf-secondary">{step.from}</span>
                                    {/if}
                                    <Tooltip html={providerTooltipHtml(step.provider)} position="top">
                                        <span class="inline-flex items-center gap-0.5 px-1 py-0.5 rounded border flex-shrink-0" style="background: var(--prov-bg); border-color: var(--prov-border); --prov-bg: {provColor.bg}; --prov-border: {provColor.border}">
                                            <ArrowLeftRight size={8} class="text-lf-muted flex-shrink-0" />
                                            {@render providerMark(step.provider, 'sm')}
                                            <ArrowLeftRight size={8} class="text-lf-muted flex-shrink-0" />
                                        </span>
                                    </Tooltip>
                                    <span class="text-sm emoji-flag">{toInfo.flag_emoji}</span>
                                    <span class="font-medium text-[11px] text-lf-secondary">{step.to}</span>
                                {/each}
                            </span>
                        {/if}
                        <!-- Priority badge (Fibonacci colors) -->
                        <span class="text-[10px] font-mono px-1.5 py-0.5 rounded flex-shrink-0 ml-auto priority-badge" style={getPriorityBadgeStyle(index)}>
                            #{index + 1}
                        </span>
                        <!-- N3c: a provider of this saved route is not configured: the yellow triangle says why -->
                        {#if unconfiguredOf(route)}
                            {@const needs = unconfiguredOf(route)!}
                            <!-- Never `reason` or `disabled` (76 N3c): the click must reach `onneedssetup`. -->
                            <Button label={setupHint(needs)} icon={AlertTriangle} display="icon" variant="ghost" tone="warning" size="xs" dense onclick={() => onneedssetup?.(needs)} data-testid="fx-route-needs-setup" data-provider={needs.code} />
                        {/if}
                        <!-- Provider warnings triangle -->
                        {#if getRouteWarnings(route).length > 0}
                            <Tooltip html={warningsTooltipHtml(getRouteWarnings(route))} position="top">
                                {@render noteIcon(getRouteWarningLevel(route), 13)}
                            </Tooltip>
                        {/if}
                        <!-- Remove button -->
                        {#if !disabled}
                            <Button label={$_('common.remove')} icon={Trash2} display="icon" variant="ghost" size="xs" dense onclick={() => removeRoute(route.key)} data-testid="fx-route-remove" />
                        {/if}
                    </div>
                {/snippet}
            </OrderableList>
        {/if}

        <!-- ============================================================= -->
        <!-- ADD ROUTE — Collapsible picker                                -->
        <!-- ============================================================= -->
        {#if hasAnyRoutes && hasUnselectedRoutes}
            <!-- A disclosure whose panel this component draws: `aria-expanded` as an attribute (the icon already turns). -->
            <Button
                label={pickerOpen ? $_('fx.route.hideRoutes') : $_('fx.route.addRoute')}
                icon={pickerOpen ? ChevronUp : Plus}
                variant="secondary"
                size="sm"
                dashed
                class="w-full"
                onclick={() => {
                    pickerOpen = !pickerOpen;
                }}
                aria-expanded={pickerOpen ? 'true' : 'false'}
                data-testid="fx-route-picker-toggle"
                data-open={pickerOpen ? 'true' : 'false'}
            />
        {/if}

        {#if pickerOpen && hasUnselectedRoutes}
            <div class="space-y-2 p-3 bg-lf-panel rounded-lg border border-lf-subtle" data-testid="fx-route-picker">
                <!-- ========================================================= -->
                <!-- PROVIDER INFO BAR — Icons with tooltips + docs links      -->
                <!-- ========================================================= -->
                {#if usedProviders.length > 0}
                    <div class="flex items-center gap-2 pb-2 border-b border-lf-subtle">
                        <span class="text-[10px] font-semibold text-lf-muted uppercase tracking-wider flex-shrink-0">
                            {$_('common.providers')}
                        </span>
                        <div class="flex items-center gap-1.5 flex-wrap">
                            {#each usedProviders as prov}
                                {@const provColor = getProviderColor(prov.code)}
                                {@const provWarning = getProviderWarning(prov.code)}
                                {@const guide = prov.docs_url ?? '/mkdocs/user/fx/providers/'}
                                <Tooltip html={legendTooltipHtml(prov)} position="top" interactiveChild openOnFocus>
                                    <a
                                        href={guide}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        data-testid="fx-provider-legend-item"
                                        data-provider={prov.code}
                                        onclick={keepClickForTooltip}
                                        ondblclick={(event) => openProviderGuide(event, guide)}
                                        class="inline-flex items-center gap-1 px-1.5 py-1 rounded border transition-all cursor-pointer hover:shadow-sm"
                                        style="background: {provColor.bg}; border-color: {provColor.border}"
                                    >
                                        {@render providerMark(prov.code, 'sm')}
                                        <span class="text-[10px] font-semibold text-lf-secondary">{prov.code}</span>
                                        {#if provWarning}
                                            {@render noteIcon(getProviderWarningLevel(prov.code), 10)}
                                        {/if}
                                    </a>
                                </Tooltip>
                            {/each}
                        </div>
                    </div>
                {/if}

                <!-- Search input -->
                <div class="relative">
                    <Search size={13} class="absolute left-2.5 top-1/2 -translate-y-1/2 text-lf-muted pointer-events-none" />
                    <input
                        type="text"
                        bind:value={searchQuery}
                        oninput={() => (shownChains = {})}
                        placeholder={$_('fx.route.searchPlaceholder')}
                        class="w-full pl-8 pr-8 py-1.5 text-xs rounded-lg border border-lf-input bg-lf-field text-lf-primary placeholder:text-lf-placeholder hover:border-lf-input-hover focus:ring-1 focus:ring-lf-focus focus:border-lf-focus outline-none transition-colors"
                        data-testid="fx-route-search"
                    />
                    {#if searchQuery}
                        <div class="absolute right-1 top-1/2 -translate-y-1/2">
                            <Button label={$_('common.clear')} icon={X} display="icon" variant="ghost" size="xs" dense onclick={clearSearch} data-testid="fx-route-search-clear" />
                        </div>
                    {/if}
                </div>

                <!-- Direct routes -->
                {#if filteredDirect.length > 0}
                    <div class="space-y-1" data-testid="fx-route-direct-section">
                        <h4 class="text-[10px] font-semibold text-lf-muted uppercase tracking-wider flex items-center gap-1.5">
                            <Check size={10} class="text-lf-success" />
                            {$_('fx.route.directSection')}
                            <span class="ml-1 text-[9px] font-mono px-1 py-0.5 rounded bg-lf-success-soft text-lf-success-on-soft">{filteredDirect.length}</span>
                        </h4>
                        {#each filteredDirect as route (route.key)}
                            {@const step = route.chainSteps[0]}
                            {@const fromInfo = getCurrencyInfo(step.from)}
                            {@const toInfo = getCurrencyInfo(step.to)}
                            {@const provColor = getProviderColor(step.provider)}
                            {@const warnings = getRouteWarnings(route)}
                            {@const off = blockedBy(route)}
                            <button
                                type="button"
                                data-testid="fx-route-direct-{route.providers[0]}"
                                data-route-key={route.key}
                                data-needs-setup={off ? 'true' : 'false'}
                                aria-disabled={off ? 'true' : undefined}
                                title={off ? setupHint(off) : undefined}
                                data-warnings={warnings.length}
                                data-warning-level={getRouteWarningLevel(route)}
                                class="w-full text-left px-2.5 py-1.5 rounded-lg border transition-all text-xs {off ? 'border-dashed border-lf-input bg-lf-card text-lf-muted' : 'border-lf-subtle bg-lf-card hover:border-lf-success-line hover:bg-lf-success-soft/50'}"
                                onclick={() => (off ? onneedssetup?.(off) : addRoute(route))}
                            >
                                <span class="flex items-center gap-1.5 {off ? 'grayscale' : ''}">
                                    {#if off}
                                        <SlidersHorizontal size={12} class="text-lf-warning flex-shrink-0" />
                                    {:else}
                                        <Plus size={12} class="text-lf-success flex-shrink-0" />
                                    {/if}
                                    <span class="text-sm emoji-flag">{fromInfo.flag_emoji}</span>
                                    <span class="font-medium text-lf-secondary text-[11px]">{step.from}</span>
                                    <Tooltip html={providerTooltipHtml(step.provider)} position="top" insideControl>
                                        <span class="inline-flex items-center gap-0.5 px-1 py-0.5 rounded border flex-shrink-0" style="background: {provColor.bg}; border-color: {provColor.border}">
                                            <ArrowLeftRight size={10} class="text-lf-muted flex-shrink-0" />
                                            {@render providerMark(step.provider, 'md')}
                                            <ArrowLeftRight size={10} class="text-lf-muted flex-shrink-0" />
                                        </span>
                                    </Tooltip>
                                    <span class="text-sm emoji-flag">{toInfo.flag_emoji}</span>
                                    <span class="font-medium text-lf-secondary text-[11px]">{step.to}</span>
                                    {#if warnings.length > 0}
                                        <Tooltip html={warningsTooltipHtml(warnings)} position="top" insideControl>
                                            {@render noteIcon(getRouteWarningLevel(route), 11)}
                                        </Tooltip>
                                    {/if}
                                    <span class="ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded bg-lf-success-soft text-lf-success-on-soft flex-shrink-0">1 step</span>
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
                            class="w-full flex items-center gap-1.5 text-[10px] font-semibold text-lf-muted uppercase tracking-wider hover:text-lf-secondary transition-colors"
                            onclick={() => toggleChainGroup(group.stepCount)}
                            aria-expanded={isExpanded}
                            data-testid="fx-route-chain-toggle-{group.stepCount}"
                            data-expanded={isExpanded}
                        >
                            {#if isExpanded}
                                <ChevronUp size={10} class="text-lf-info flex-shrink-0" />
                            {:else}
                                <ChevronDown size={10} class="text-lf-info flex-shrink-0" />
                            {/if}
                            <Link size={10} class="text-lf-info" />
                            {$_('fx.route.chainSection')} — {group.stepCount}
                            {$_('fx.route.steps')}
                            <span class="ml-1 text-[9px] font-mono px-1 py-0.5 rounded bg-lf-info-soft text-lf-info-on-soft">{group.routes.length}</span>
                            <!-- Chain risk info icon -->
                            <Tooltip text={$_('fx.route.chainWarning')} position="top" insideControl>
                                <Info size={10} class="text-lf-info" />
                            </Tooltip>
                        </button>

                        <!-- Collapsible content -->
                        {#if isExpanded}
                            {@const limit = chainLimit(group.stepCount)}
                            {#each group.routes.slice(0, limit) as route (route.key)}
                                {@const warnings = getRouteWarnings(route)}
                                {@const off = blockedBy(route)}
                                <button
                                    type="button"
                                    data-testid="fx-route-chain-{route.stepCount}step-{route.providers.join('-')}"
                                    data-route-key={route.key}
                                    data-needs-setup={off ? 'true' : 'false'}
                                    aria-disabled={off ? 'true' : undefined}
                                    title={off ? setupHint(off) : undefined}
                                    data-warnings={warnings.length}
                                    data-warning-level={getRouteWarningLevel(route)}
                                    class="w-full text-left px-2.5 py-1.5 rounded-lg border transition-all text-xs {off ? 'border-dashed border-lf-input bg-lf-card text-lf-muted' : 'border-lf-subtle bg-lf-card hover:border-lf-info-line hover:bg-lf-info-soft/50'}"
                                    onclick={() => (off ? onneedssetup?.(off) : addRoute(route))}
                                >
                                    <span class="flex items-center gap-1.5 {off ? 'grayscale' : ''}">
                                        {#if off}
                                            <SlidersHorizontal size={12} class="text-lf-warning flex-shrink-0" />
                                        {:else}
                                            <Plus size={12} class="text-lf-info flex-shrink-0" />
                                        {/if}
                                        <span class="flex items-center gap-0.5 flex-wrap flex-1 min-w-0">
                                            {#each route.chainSteps as step, i}
                                                {@const fromInfo = getCurrencyInfo(step.from)}
                                                {@const toInfo = getCurrencyInfo(step.to)}
                                                {@const provColor = getProviderColor(step.provider)}
                                                {#if i === 0}
                                                    <span class="text-sm emoji-flag">{fromInfo.flag_emoji}</span>
                                                    <span class="font-medium text-[11px] text-lf-secondary">{step.from}</span>
                                                {/if}
                                                <Tooltip html={providerTooltipHtml(step.provider)} position="top" insideControl>
                                                    <span class="inline-flex items-center gap-0.5 px-0.5 py-0.5 rounded border flex-shrink-0" style="background: {provColor.bg}; border-color: {provColor.border}">
                                                        <ArrowLeftRight size={8} class="text-lf-muted flex-shrink-0" />
                                                        {@render providerMark(step.provider, 'sm')}
                                                        <ArrowLeftRight size={8} class="text-lf-muted flex-shrink-0" />
                                                    </span>
                                                </Tooltip>
                                                <span class="text-sm emoji-flag">{toInfo.flag_emoji}</span>
                                                <span class="font-medium text-[11px] text-lf-secondary">{step.to}</span>
                                            {/each}
                                        </span>
                                        {#if warnings.length > 0}
                                            <Tooltip html={warningsTooltipHtml(warnings)} position="top" insideControl>
                                                {@render noteIcon(getRouteWarningLevel(route), 11)}
                                            </Tooltip>
                                        {/if}
                                        <span class="ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded bg-lf-info-soft text-lf-info-on-soft flex-shrink-0 whitespace-nowrap">
                                            {route.stepCount}
                                            {$_('fx.route.steps')}
                                        </span>
                                    </span>
                                </button>
                            {/each}
                            {#if group.routes.length > limit}
                                <Button
                                    label={$_('fx.route.showMore', {values: {count: group.routes.length - limit}})}
                                    variant="secondary"
                                    size="sm"
                                    dashed
                                    class="w-full"
                                    onclick={() => showMoreChains(group.stepCount)}
                                    data-testid="fx-route-chain-more-{group.stepCount}"
                                    data-hidden={group.routes.length - limit}
                                />
                            {/if}
                        {/if}
                    </div>
                {/each}

                <!-- Unusable providers -->
                {#if filteredUnusable.length > 0}
                    <div class="space-y-1" data-testid="fx-route-unusable">
                        <h4 class="text-[10px] font-semibold text-lf-muted uppercase tracking-wider flex items-center gap-1.5">
                            <AlertTriangle size={10} class="text-lf-muted" />
                            {$_('fx.route.unusableSection')}
                        </h4>
                        <div class="px-2.5 py-1.5 rounded-lg border border-dashed border-lf-subtle bg-lf-panel/50">
                            <div class="flex flex-wrap gap-1.5">
                                {#each filteredUnusable as prov}
                                    <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-lf-neutral text-lf-muted line-through">
                                        {prov.code}
                                    </span>
                                {/each}
                            </div>
                            <p class="text-[10px] text-lf-muted mt-1">
                                {$_('fx.route.unusableHint')}
                            </p>
                        </div>
                    </div>
                {/if}

                <!-- No search results -->
                {#if !hasFilteredRoutes && searchTokens.length > 0}
                    <div class="text-xs text-lf-muted text-center py-2" data-testid="fx-route-no-results">
                        {$_('fx.route.noSearchResults')}
                    </div>
                {/if}
            </div>
        {/if}

        <!-- No routes available at all -->
        {#if !hasAnyRoutes && !loading}
            <div class="px-3 py-3 rounded-lg border border-dashed border-lf-warning-line bg-lf-warning-soft/50" data-testid={providersUnavailable ? 'fx-route-unavailable' : 'fx-route-none'}>
                <div class="flex items-center gap-2 text-xs text-lf-warning-on-soft">
                    <AlertTriangle size={12} />
                    <span>{$_(providersUnavailable ? 'fx.route.providersUnavailable' : 'fx.route.noRoutesAvailable')}</span>
                </div>
            </div>
        {/if}

        <!-- Chain warning banner -->
        {#if orderedSelected.some((r) => !r.isDirect)}
            <div class="px-2.5 py-2 rounded-lg bg-lf-info-soft border border-lf-info-line text-[10px] text-lf-info-on-soft flex items-start gap-2">
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

    :global(.dark) [style*='--prov-bg'] {
        background: var(--prov-dark-bg, var(--prov-bg)) !important;
    }
</style>
