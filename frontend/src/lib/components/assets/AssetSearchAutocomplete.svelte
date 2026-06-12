<!--
  AssetSearchAutocomplete — Debounced search across multiple providers.

  Features:
  - Input debounced (300ms)
  - Provider checkbox row (from GET /assets/provider, only supports_search=true)
  - Dropdown results with provider_url link
  - Loading, empty, error states
  - Event onselect(result)
  Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {untrack} from 'svelte';
    import {zodiosApi} from '$lib/api';
    import {ExternalLink, Loader2, Search} from 'lucide-svelte';
    import AssetIcon from './AssetIcon.svelte';
    import {ensureAssetProvidersCached, getAssetProviderIconUrl} from '$lib/utils/providerHelpers';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';

    // =========================================================================
    // Types
    // =========================================================================

    interface SearchResult {
        identifier: string;
        identifier_type: string;
        display_name: string;
        provider_code: string;
        currency?: string | null;
        asset_type?: string | null;
        provider_url?: string | null;
        provider_params?: Record<string, any> | null;
    }

    interface ProviderInfo {
        code: string;
        name: string;
        supports_search: boolean;
        icon_url?: string | null;
    }

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        onselect?: (result: SearchResult) => void;
        disabled?: boolean;
        /** Pre-fill the search input on mount (e.g. from BRIM extracted symbol/name). */
        initialQuery?: string;
    }

    let {onselect, disabled = false, initialQuery = ''}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let query = $state(untrack(() => initialQuery));
    let results = $state<SearchResult[]>([]);
    let loading = $state(false);
    let error = $state<string | null>(null);
    let providers = $state<ProviderInfo[]>([]);
    let selectedProviders = $state<Set<string>>(new Set());
    let providersLoaded = $state(false);
    let showResults = $state(false);
    let debounceTimer: ReturnType<typeof setTimeout> | undefined;
    /** Monotonic search ID to ignore stale responses */
    let searchId = 0;

    // =========================================================================
    // Derived
    // =========================================================================

    let searchableProviders = $derived(providers.filter((p) => p.supports_search));
    let hasResults = $derived(results.length > 0);

    // =========================================================================
    // Lifecycle — Load providers
    // =========================================================================

    $effect(() => {
        if (!providersLoaded) {
            loadProviders();
            ensureAssetProvidersCached();
        }
    });

    // If initialQuery was provided, auto-trigger search after providers load.
    $effect(() => {
        if (providersLoaded && initialQuery.trim().length > 0 && results.length === 0 && !loading) {
            executeSearch(initialQuery);
        }
    });

    async function loadProviders() {
        try {
            const response = (await zodiosApi.list_providers_api_v1_assets_provider_get()) as any;
            const items: ProviderInfo[] = (Array.isArray(response) ? response : []).filter((p: ProviderInfo) => p.code !== 'mockprov');
            providers = items;
            // Select all searchable providers by default
            selectedProviders = new Set(items.filter((p) => p.supports_search).map((p) => p.code));
            providersLoaded = true;
        } catch (e: any) {
            console.error('Failed to load providers:', e);
        }
    }

    // =========================================================================
    // Search
    // =========================================================================

    function handleInput(e: Event) {
        const val = (e.target as HTMLInputElement).value;
        query = val;
        clearTimeout(debounceTimer);
        if (val.trim().length === 0) {
            results = [];
            showResults = false;
            return;
        }
        debounceTimer = setTimeout(() => executeSearch(val), 300);
    }

    /** Track per-provider status for streaming search */
    let providersDone = $state(0);
    let providersTotal = $state(0);

    async function executeSearch(q: string) {
        if (q.trim().length === 0 || selectedProviders.size === 0) return;

        // Increment search ID and capture it for this request
        const mySearchId = ++searchId;

        loading = true;
        error = null;
        showResults = true;
        results = [];
        providersDone = 0;
        providersTotal = selectedProviders.size;

        const providerCodes = [...selectedProviders].join(',');

        try {
            // Try SSE streaming first
            const response = await fetch(`/api/v1/assets/provider/search/stream?q=${encodeURIComponent(q)}&providers=${encodeURIComponent(providerCodes)}`);

            if (!response.ok || !response.body) {
                throw new Error('SSE not available');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const {done, value} = await reader.read();
                if (done) break;
                if (mySearchId !== searchId) {
                    reader.cancel();
                    return;
                }

                buffer += decoder.decode(value, {stream: true});

                // Parse SSE events from buffer
                const lines = buffer.split('\n');
                buffer = lines.pop() ?? ''; // Keep incomplete line in buffer

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    try {
                        const event = JSON.parse(line.slice(6));
                        if (event.event === 'provider_results') {
                            providersDone++;
                            const newItems: SearchResult[] = (event.results ?? []).map((r: any) => ({
                                identifier: r.identifier,
                                identifier_type: r.identifier_type,
                                display_name: r.display_name,
                                provider_code: r.provider_code,
                                currency: r.currency,
                                asset_type: r.asset_type,
                                provider_url: r.provider_url,
                                provider_params: r.provider_params,
                            }));
                            results = [...results, ...newItems];
                        } else if (event.event === 'provider_error') {
                            providersDone++;
                        } else if (event.event === 'done') {
                            // Final event
                        }
                    } catch {
                        /* skip malformed SSE lines */
                    }
                }
            }

            if (mySearchId === searchId) {
                loading = false;
            }
        } catch {
            // Fallback to REST endpoint
            if (mySearchId !== searchId) return;
            try {
                const response = (await zodiosApi.search_assets_via_providers_api_v1_assets_provider_search_get({
                    queries: {q, providers: providerCodes},
                })) as any;

                if (mySearchId !== searchId) return;

                results = (response?.results ?? []).map((r: any) => ({
                    identifier: r.identifier,
                    identifier_type: r.identifier_type,
                    display_name: r.display_name,
                    provider_code: r.provider_code,
                    currency: r.currency,
                    asset_type: r.asset_type,
                    provider_url: r.provider_url,
                }));
            } catch (e: any) {
                if (mySearchId !== searchId) return;
                console.error('Search failed:', e);
                error = e?.message || 'Search failed';
                results = [];
            } finally {
                if (mySearchId === searchId) {
                    loading = false;
                }
            }
        }
    }

    function selectResult(result: SearchResult) {
        showResults = false;
        onselect?.(result);
    }

    function toggleProvider(code: string) {
        const next = new Set(selectedProviders);
        if (next.has(code)) next.delete(code);
        else next.add(code);
        selectedProviders = next;
        // Re-search if query is active
        if (query.trim().length > 0) {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => executeSearch(query), 100);
        }
    }

    function handleFocusIn() {
        if (results.length > 0 || loading) {
            showResults = true;
        }
    }

    function handleClickOutside(e: MouseEvent) {
        const target = e.target as HTMLElement;
        if (!target.closest('[data-search-autocomplete]')) {
            showResults = false;
        }
    }

    // Close on outside click
    $effect(() => {
        if (showResults) {
            window.addEventListener('click', handleClickOutside, true);
            return () => window.removeEventListener('click', handleClickOutside, true);
        }
    });
</script>

<div class="space-y-2" data-search-autocomplete>
    <!-- Section label -->
    <div class="flex items-center gap-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
        <Search size={12} />
        <span>{$t('assets.modal.searchOnline')}</span>
    </div>

    <!-- Search input -->
    <div class="relative">
        <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
            {#if loading}
                <Loader2 size={16} class="text-gray-400 animate-spin" />
            {:else}
                <Search size={16} class="text-gray-400" />
            {/if}
        </div>
        <input
            type="text"
            value={query}
            oninput={handleInput}
            onfocusin={handleFocusIn}
            placeholder={$t('assets.search.placeholder')}
            {disabled}
            class="w-full pl-10 pr-4 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                       bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                       placeholder-gray-400 dark:placeholder-gray-500
                       focus:outline-none focus:ring-2 focus:ring-libre-green/50 focus:border-libre-green
                       disabled:opacity-50 disabled:cursor-not-allowed"
        />
    </div>

    <!-- Provider badge toggles -->
    {#if searchableProviders.length > 0}
        <div class="flex items-center gap-2 flex-wrap">
            <span class="text-xs text-gray-500 dark:text-gray-400">{$t('assets.search.providers')}:</span>
            {#each searchableProviders as prov}
                <button
                    type="button"
                    onclick={() => toggleProvider(prov.code)}
                    class="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full border transition-all
                               {selectedProviders.has(prov.code) ? 'bg-libre-green/15 dark:bg-libre-green/25 border-libre-green/40 text-libre-green dark:text-green-400' : 'bg-gray-100/50 dark:bg-slate-700/50 border-gray-200 dark:border-slate-600 text-gray-400 dark:text-gray-500 opacity-60'}"
                >
                    {#if prov.icon_url}
                        <img src={prov.icon_url} alt="" class="w-3.5 h-3.5 rounded-sm object-contain {selectedProviders.has(prov.code) ? '' : 'grayscale opacity-50'}" />
                    {/if}
                    <span>{prov.name}</span>
                </button>
            {/each}
        </div>
    {/if}

    <!-- Results dropdown -->
    {#if showResults}
        <div
            class="border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800
                    shadow-lg max-h-60 overflow-y-auto"
        >
            {#if loading && results.length === 0}
                <div class="flex items-center justify-center gap-2 py-4 text-sm text-gray-500 dark:text-gray-400">
                    <Loader2 size={16} class="animate-spin" />
                    <span>{$t('assets.search.searching')}{providersDone > 0 && providersTotal > 0 ? ` (${providersDone}/${providersTotal})` : ''}</span>
                </div>
            {:else if error}
                <div class="py-4 px-4 text-sm text-red-500 dark:text-red-400 text-center">
                    {error}
                </div>
            {:else if !hasResults && !loading}
                <div class="py-4 text-sm text-gray-500 dark:text-gray-400 text-center">
                    {$t('common.noResults')}
                </div>
            {:else}
                <!-- Loading banner (streaming partial results) -->
                {#if loading}
                    <div class="flex items-center gap-2 px-3 py-1.5 text-xs text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-slate-800/50 border-b border-gray-100 dark:border-slate-700">
                        <Loader2 size={12} class="animate-spin" />
                        <span>{$t('assets.search.searching')} ({providersDone}/{providersTotal})</span>
                    </div>
                {/if}
                {#each results as result}
                    <button type="button" class="w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors border-b border-gray-100 dark:border-slate-700 last:border-b-0" onclick={() => selectResult(result)}>
                        <!-- Icon placeholder -->
                        <AssetIcon assetType={result.asset_type} iconUrl={null} altText={result.display_name} size="sm" />

                        <!-- Info -->
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center gap-1.5 text-sm font-medium text-gray-900 dark:text-gray-100 min-w-0">
                                <span class="truncate">{result.display_name}</span>
                            </div>
                            <div class="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                                <span class="font-mono">{result.identifier}</span>
                                {#if result.currency}
                                    <span class="mx-0.5">·</span>
                                    <span>{result.currency}</span>
                                {/if}
                                {#if result.asset_type}
                                    <span class="mx-0.5">·</span>
                                    <span class="inline-flex items-center gap-0.5">
                                        <img src={getAssetTypeIconUrl(result.asset_type)} alt="" class="w-3 h-3 object-contain" />
                                        <span>{$t('assets.types.' + (result.asset_type ?? 'OTHER').toUpperCase())}</span>
                                    </span>
                                {/if}
                                {#if getAssetProviderIconUrl(result.provider_code)}
                                    <span class="mx-0.5">·</span>
                                    <span class="inline-flex items-center gap-1 shrink-0">
                                        <img src={getAssetProviderIconUrl(result.provider_code)} alt={result.provider_code} class="w-3.5 h-3.5 rounded-sm object-contain" title={result.provider_code} />
                                        <span class="text-gray-400 dark:text-gray-500">{result.provider_code}</span>
                                    </span>
                                {/if}
                            </div>
                        </div>

                        <!-- Provider URL link -->
                        {#if result.provider_url}
                            <a href={result.provider_url} target="_blank" rel="noopener noreferrer" class="shrink-0 p-1 text-gray-400 hover:text-libre-green transition-colors" onclick={(e) => e.stopPropagation()} title="Open provider page">
                                <ExternalLink size={14} />
                            </a>
                        {/if}
                    </button>
                {/each}
            {/if}
        </div>
    {/if}
</div>
