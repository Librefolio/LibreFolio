<!--
  AssetSearchAutocomplete — Debounced search across multiple providers.

  Features:
  - Input debounced (300ms)
  - Provider checkbox row (from GET /assets/provider, only supports_search=true)
  - Dropdown results with provider_url link
  - Loading, empty, error states
  - A provider that must be configured first (NOT_CONFIGURED) says so, with «Configure» (CP11)
  - The legend of 👑 (the fund's own currency) when a result shows it
  - Premium sources first (F21): when a premium provider took part in the search, its results come in a Premium
    section, and the others in a closed community section that warns before it shows them; otherwise the list is as
    before, ordered by the providers' priority (assetSearchSections.ts)
  - «Can't find it? Let us know» after every search (P20): a report of the search, sent from the user's own client
    through the instance's support address (assetSearchReport.ts)
  - Event onselect(result)
  Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {untrack} from 'svelte';
    import {zodiosApi} from '$lib/api';
    import {AlertTriangle, ChevronDown, ChevronRight, ExternalLink, Loader2, Search} from 'lucide-svelte';
    import AssetIcon from './AssetIcon.svelte';
    import {ensureAssetProvidersCached, getAssetProviderIconUrl} from '$lib/utils/providerHelpers';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {isOutsideClick} from '$lib/utils/core/clickOutside';
    import PluginSettingsModal from '$lib/features/plugin-settings/PluginSettingsModal.svelte';
    import {instanceConfig} from '$lib/features/instance/instanceConfig.svelte';
    import {selfHostedConfirmed} from '$lib/features/instance/profile';
    import {currentLanguage} from '$lib/stores/app/language';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {writeTextToClipboard} from '$lib/utils/clipboard';
    import {APP_VERSION} from '$lib/version';
    import {hasPremium, orderSearchResults, splitSearchResults, type ProviderTier} from './assetSearchSections';
    import {buildSearchReport, reportHref, supportChannel, type ProviderOutcome, type SearchReportContext, type SupportChannel} from './assetSearchReport';

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
        /** The provider's quote base suggestion for this line (Z-32 d), handed to `onselect`. */
        quote_base_suggestion?: {quantity: number; quote_currency?: string | null} | null;
        via_web?: boolean;
    }

    interface ProviderInfo {
        code: string;
        name: string;
        supports_search: boolean;
        icon_url?: string | null;
        /** F21: the effective tier and priority, as GET /assets/provider answers them. */
        tier?: ProviderTier | null;
        priority?: number | null;
    }

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        onselect?: (result: SearchResult) => void;
        disabled?: boolean;
        /** Pre-fill the search input on mount (e.g. from BRIM extracted symbol/name). */
        initialQuery?: string;
        /** When true, hides the "Search Online" section title (caller renders it externally). */
        hideTitle?: boolean;
        /**
         * Extra search terms (e.g. ISIN + all candidate names extracted from a broker
         * report). Forwarded as `hints` to the backend; used only by the link-finder
         * fallback to build a specific query when a provider's on-site search finds
         * nothing (e.g. a fund whose bare ISIN surfaces several sibling share classes).
         */
        hints?: string[];
        /** What the caller's form already holds (currency, type, identifiers), for the report of a search (P20). */
        reportContext?: SearchReportContext | null;
    }

    let {onselect, disabled = false, initialQuery = '', hideTitle = false, hints = [], reportContext = null}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let query = $state(untrack(() => initialQuery));
    let results: SearchResult[] = $state([]);
    let loading = $state(false);
    let error: string | null = $state(null);
    let providers: ProviderInfo[] = $state([]);
    let selectedProviders: Set<string> = $state(new Set());
    let providersLoaded = $state(false);
    let showResults = $state(false);
    let debounceTimer: ReturnType<typeof setTimeout> | undefined;
    /** Monotonic search ID to ignore stale responses */
    let searchId = 0;
    /** Last initialQuery auto-searched, so the auto-trigger fires once per query (even on 0 results) */
    let lastAutoSearchedQuery: string | null = null;

    // A query typed before the provider list has arrived used to vanish in
    // silence: executeSearch() bailed on an empty selectedProviders and the
    // debounce had already fired, so nothing ever retried — the box just looked
    // dead. Hold the query and run it the moment providers land.
    let pendingQuery = $state<string | null>(null);
    /** Controller of the in-flight streamed request, aborted when a newer search starts */
    let activeController: AbortController | null = null;
    /** The providers of the last search that did not search because a required setting has no value (NOT_CONFIGURED). */
    let notConfigured = $state<string[]>([]);
    /** The provider whose settings «Configure» opened; null when the dialog is closed. */
    let configuring = $state<string | null>(null);
    /** The query and the providers of the last search that ran, and what each provider answered: the report (P20). */
    let searchedQuery = $state<string | null>(null);
    let searchedCodes = $state<string[]>([]);
    let outcomes = $state<Record<string, ProviderOutcome>>({});
    /** The community section opened by the user (F21). Never persisted: the choice holds for this asset only. */
    let communityOpen = $state(false);

    // =========================================================================
    // Derived
    // =========================================================================

    let searchableProviders = $derived(providers.filter((p) => p.supports_search));
    let hasResults = $derived(results.length > 0);
    // F21: premium first, then lower priority; with every provider at its defaults, the order of arrival (D-X3).
    let orderedResults = $derived(orderSearchResults(results, providers));
    // The sections only when a premium provider took part in the search: otherwise the list is as before.
    let grouped = $derived(hasPremium(searchedCodes, providers));
    // A slice each of orderedResults, which puts every premium result first: indices run on across the two sections.
    let sections = $derived(splitSearchResults(orderedResults, providers));
    let visibleResults = $derived(grouped && !communityOpen ? sections.premium : orderedResults);
    // 👑 marks a fund's own currency among its currency rows (justETF): a legend says so when a result shows it.
    let crownShown = $derived(visibleResults.some((r) => r.display_name.includes('👑')));
    // Rank among web-resolved (link-finder) results only, in display order. 0 = native result
    // (no badge). Web results are ordered best-first by the finder, so #1 is the most likely match.
    let webRanks = $derived.by(() => {
        let n = 0;
        return orderedResults.map((r) => (r.via_web ? ++n : 0));
    });

    // P20: the report of the last search, once it has finished. A provider that never answered (a timeout) has no
    // outcome: «no answer». Listed in the order of the provider toggles.
    /** The tooltip of «Let us know», by channel: literal keys, so that the i18n audit sees each one. */
    const REPORT_VIA_KEY: Record<SupportChannel['kind'], string> = {
        mailto: 'assets.search.reportVia.mailto',
        page: 'assets.search.reportVia.page',
        github: 'assets.search.reportVia.github',
    };
    // The generated type of a nullable string with a description also admits an array (a quirk of the client
    // generator); the response's validator accepts only a string or null. N61: the public GitHub issue only on a
    // self-hosted instance whose configuration was read; on a managed one, or when it could not be read, a missing
    // support address means no report link at all.
    let channel = $derived.by(() => {
        const configured = instanceConfig.config.support_url;
        const githubFallback = selfHostedConfirmed();
        return supportChannel(typeof configured === 'string' ? configured : null, {githubFallback});
    });
    let report = $derived.by(() => {
        if (searchedQuery === null) return null;
        const queried = searchableProviders.filter((p) => searchedCodes.includes(p.code));
        return buildSearchReport({
            query: searchedQuery,
            providers: queried.map((p): ProviderOutcome => outcomes[p.code] ?? {code: p.code, status: 'no_answer'}),
            context: reportContext,
            appVersion: APP_VERSION,
            profile: instanceConfig.config.profile,
            language: $currentLanguage,
        });
    });
    let reportLink = $derived(report && channel ? reportHref(channel, report) : null);
    // Between the sections when they show, at the bottom of the dropdown otherwise; never while a search runs.
    let reportPlacement = $derived(report === null || channel === null || loading ? null : grouped && hasResults && !error ? 'sections' : 'bottom');

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
    // Guard on the query value (not on results/loading): a delisted asset returns 0
    // results, and depending on results.length would re-fire this effect forever.
    $effect(() => {
        if (providersLoaded && initialQuery.trim().length > 0) {
            if (untrack(() => lastAutoSearchedQuery) !== initialQuery) {
                lastAutoSearchedQuery = initialQuery;
                executeSearch(initialQuery);
            }
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
            // Finished, badly. Still mark it: a query held back waiting for
            // providers must not spin forever on a list that will never come.
            providersLoaded = true;
        }
    }

    // Run the query that was typed while the providers were still in flight.
    $effect(() => {
        if (!providersLoaded || pendingQuery === null) return;
        const q = untrack(() => pendingQuery);
        pendingQuery = null;
        if (q) executeSearch(q);
    });

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
            // No query, no search to report: focusing the empty box opens nothing.
            searchedQuery = null;
            return;
        }
        debounceTimer = setTimeout(() => executeSearch(val), 300);
    }

    /** Track per-provider status for streaming search */
    let providersDone = $state(0);
    let providersTotal = $state(0);

    // Interactive search must never hang; cap the whole streamed request so a slow or
    // stuck provider resolves to an empty result instead of an endless spinner.
    const SEARCH_TIMEOUT_MS = 30000;

    async function executeSearch(q: string) {
        if (q.trim().length === 0) return;

        if (!providersLoaded) {
            // Providers still in flight. Open the dropdown in its searching
            // state and let the effect above re-run this once they land, so the
            // user sees the search happening instead of nothing at all.
            pendingQuery = q;
            showResults = true;
            loading = true;
            return;
        }
        if (selectedProviders.size === 0) {
            // Nothing to search against — clear the spinner so the dropdown can
            // fall through to "no results" instead of spinning forever.
            loading = false;
            return;
        }

        // Increment search ID and capture it for this request
        const mySearchId = ++searchId;

        // Abort any previous in-flight streamed request so rapid/identical searches don't
        // pile up (a stale stream would otherwise keep running until the server closes it).
        activeController?.abort();

        loading = true;
        error = null;
        showResults = true;
        results = [];
        notConfigured = [];
        providersDone = 0;
        providersTotal = selectedProviders.size;
        searchedQuery = q;
        searchedCodes = [...selectedProviders];
        outcomes = {};

        const providerCodes = [...selectedProviders].join(',');

        // Extra terms (ISIN + candidate names) for the backend link-finder fallback.
        // Deduped case-insensitively; the query itself is always included server-side.
        const seenHints = new Set<string>();
        const hintsParam = (hints ?? [])
            .map((h) => (h ?? '').trim())
            .filter((h) => {
                const key = h.toLowerCase();
                if (h.length === 0 || seenHints.has(key)) return false;
                seenHints.add(key);
                return true;
            })
            .map((h) => `&hints=${encodeURIComponent(h)}`)
            .join('');

        const controller = new AbortController();
        activeController = controller;
        let timedOut = false;
        const timeoutId = setTimeout(() => {
            timedOut = true;
            controller.abort();
        }, SEARCH_TIMEOUT_MS);

        try {
            // Try SSE streaming first
            const response = await fetch(`/api/v1/assets/provider/search/stream?q=${encodeURIComponent(q)}&providers=${encodeURIComponent(providerCodes)}${hintsParam}`, {signal: controller.signal});

            if (!response.ok || !response.body) {
                throw new Error('SSE not available');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let streamDone = false;

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
                                quote_base_suggestion: r.quote_base_suggestion ?? null,
                                via_web: r.via_web ?? false,
                            }));
                            results = [...results, ...newItems];
                            const answered = typeof event.provider_code === 'string' ? event.provider_code : newItems[0]?.provider_code;
                            if (answered) recordResults(answered, newItems.length);
                        } else if (event.event === 'provider_error') {
                            providersDone++;
                            if (typeof event.provider_code === 'string') outcomes = {...outcomes, [event.provider_code]: {code: event.provider_code, status: 'error', errorCode: typeof event.error_code === 'string' ? event.error_code : null}};
                            if (event.error_code === 'NOT_CONFIGURED' && typeof event.provider_code === 'string' && !notConfigured.includes(event.provider_code)) {
                                notConfigured = [...notConfigured, event.provider_code];
                            }
                        } else if (event.event === 'done') {
                            // Terminal event: stop now instead of waiting for the HTTP
                            // stream to physically close (a slow provider or a buffering
                            // proxy could otherwise keep it open indefinitely).
                            streamDone = true;
                        }
                    } catch {
                        /* skip malformed SSE lines */
                    }
                }

                if (streamDone) {
                    void reader.cancel();
                    break;
                }
            }

            if (mySearchId === searchId) {
                loading = false;
            }
        } catch (streamErr) {
            if (mySearchId !== searchId) return;

            // Timed out / aborted: surface an empty result with a clear message instead of
            // spinning forever. Don't fall back to REST — it would hang the same way.
            if (timedOut || (streamErr instanceof DOMException && streamErr.name === 'AbortError')) {
                results = [];
                error = $t('assets.search.timeout');
                loading = false;
                return;
            }

            // Fallback to REST endpoint (SSE genuinely unavailable)
            try {
                const response = (await zodiosApi.search_assets_via_providers_api_v1_assets_provider_search_get({
                    queries: {q, providers: providerCodes},
                })) as any;

                if (mySearchId !== searchId) return;

                notConfigured = Array.isArray(response?.providers_not_configured) ? [...new Set<string>(response.providers_not_configured.filter((code: unknown) => typeof code === 'string'))] : [];
                results = (response?.results ?? []).map((r: any) => ({
                    identifier: r.identifier,
                    identifier_type: r.identifier_type,
                    display_name: r.display_name,
                    provider_code: r.provider_code,
                    currency: r.currency,
                    asset_type: r.asset_type,
                    provider_url: r.provider_url,
                    provider_params: r.provider_params,
                    quote_base_suggestion: r.quote_base_suggestion ?? null,
                    via_web: r.via_web ?? false,
                }));
                outcomes = restOutcomes(response, results, notConfigured);
            } catch (e: any) {
                if (mySearchId !== searchId) return;
                console.error('Search failed:', e);
                // X-R31: the technical error stays in the console; the dropdown says it in the user's language
                error = $t('assets.search.failed');
                results = [];
            } finally {
                if (mySearchId === searchId) {
                    loading = false;
                }
            }
        } finally {
            clearTimeout(timeoutId);
            if (activeController === controller) activeController = null;
        }
    }

    function providerName(code: string): string {
        return providers.find((p) => p.code === code)?.name ?? code;
    }

    /** A provider of the streamed search answered `count` results (P20: its outcome in the report). */
    function recordResults(code: string, count: number) {
        const previous = outcomes[code];
        outcomes = {...outcomes, [code]: {code, status: 'results', count: (previous?.status === 'results' ? previous.count : 0) + count}};
    }

    /** What each provider answered to the REST search, from its lists: not configured, failed, or its results. */
    function restOutcomes(response: any, found: SearchResult[], notConfiguredCodes: string[]): Record<string, ProviderOutcome> {
        const failed = new Set<unknown>(Array.isArray(response?.providers_with_errors) ? response.providers_with_errors : []);
        const queried: unknown[] = Array.isArray(response?.providers_queried) ? response.providers_queried : [];
        const next: Record<string, ProviderOutcome> = {};
        for (const code of queried) {
            if (typeof code !== 'string') continue;
            if (notConfiguredCodes.includes(code)) next[code] = {code, status: 'error', errorCode: 'NOT_CONFIGURED'};
            else if (failed.has(code)) next[code] = {code, status: 'error', errorCode: null};
            else next[code] = {code, status: 'results', count: found.filter((r) => r.provider_code === code).length};
        }
        return next;
    }

    /** P20, a support page: it opens in a new tab with the report in its address (N61-form), and the report also goes to the
     * clipboard, for a page that does not read it. */
    function reportClicked() {
        if (channel?.kind !== 'page' || report === null) return;
        // The write starts inside the click, before anything is awaited (writeTextToClipboard). It may throw at once.
        let copied: Promise<void>;
        try {
            copied = writeTextToClipboard(report.body);
        } catch (refusal) {
            copied = Promise.reject(refusal);
        }
        void copied.then(
            () => notify({name: 'assets.search.report.copied', detail: {channel: 'page'}, toast: {variant: 'success', message: $t('assets.search.reportCopied')}}),
            () => notify({name: 'assets.search.report.copyFailed', detail: {channel: 'page'}, toast: {variant: 'warning', message: $t('assets.search.reportCopyFailed')}}),
        );
    }

    /** After a save in «Configure»: search again, so the provider now configured answers. */
    function configured() {
        if (query.trim().length > 0) executeSearch(query);
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
        // A finished search reopens too, even an empty or failed one: its report row (P20) must stay reachable.
        if (results.length > 0 || loading || searchedQuery !== null) {
            showResults = true;
        }
    }

    function handleClickOutside(e: MouseEvent) {
        if (isOutsideClick(e.target, (el) => !!el.closest('[data-search-autocomplete]'))) {
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
    <!-- Section label (hidden when parent renders it externally) -->
    {#if !hideTitle}
        <div class="flex items-center gap-2 text-xs font-semibold text-lf-muted uppercase tracking-wider">
            <Search size={12} />
            <span>{$t('assets.modal.searchOnline')}</span>
        </div>
    {/if}

    <!-- Search input -->
    <div class="relative">
        <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
            {#if loading}
                <Loader2 size={16} class="text-lf-muted animate-spin" />
            {:else}
                <Search size={16} class="text-lf-muted" />
            {/if}
        </div>
        <input
            type="text"
            value={query}
            oninput={handleInput}
            onfocusin={handleFocusIn}
            placeholder={$t('assets.search.placeholder')}
            {disabled}
            class="w-full pl-10 pr-4 py-2 text-sm border border-lf-input hover:border-lf-input-hover rounded-lg
                       bg-lf-field text-lf-primary
                       placeholder:text-lf-placeholder
                       focus:outline-none focus:ring-2 focus:ring-lf-focus/50 focus:border-lf-focus
                       disabled:opacity-50 disabled:cursor-not-allowed"
        />
    </div>

    <!-- Provider badge toggles -->
    {#if searchableProviders.length > 0}
        <div class="flex items-center gap-2 flex-wrap">
            <span class="text-xs text-lf-muted">{$t('common.providers')}:</span>
            {#each searchableProviders as prov}
                <button
                    type="button"
                    onclick={() => toggleProvider(prov.code)}
                    data-testid="asset-search-provider-{prov.code}"
                    data-selected={selectedProviders.has(prov.code)}
                    class="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full border transition-all
                               {selectedProviders.has(prov.code) ? 'bg-lf-selected border-lf-focus/40 text-lf-link' : 'bg-lf-panel/50 border-lf-subtle text-lf-muted opacity-60'}"
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
            data-testid="asset-search-results"
            data-state={loading ? 'searching' : error ? 'error' : hasResults ? 'results' : 'empty'}
            class="border border-lf-raised rounded-lg bg-lf-card
                    shadow-lg shadow-lf-shadow max-h-60 overflow-y-auto"
        >
            {#each notConfigured as code (code)}
                <div class="flex flex-wrap items-center justify-between gap-2 border-b border-lf-warning-line bg-lf-warning-soft px-3 py-2 text-xs text-lf-warning-on-soft" data-provider={code} data-testid="asset-search-not-configured">
                    <span>{$t('assets.search.notConfigured', {values: {provider: providerName(code)}})}</span>
                    <button class="rounded-md border border-lf-warning-line bg-lf-card px-2 py-0.5 text-xs font-medium text-lf-primary hover:bg-lf-hover" data-testid="asset-search-configure" onclick={() => (configuring = code)} type="button">
                        {$t('pluginSettings.configure')}
                    </button>
                </div>
            {/each}
            {#if loading && results.length === 0}
                <div class="flex items-center justify-center gap-2 py-4 text-sm text-lf-muted">
                    <Loader2 size={16} class="animate-spin" />
                    <span>{$t('assets.search.searching')}{providersDone > 0 && providersTotal > 0 ? ` (${providersDone}/${providersTotal})` : ''}</span>
                </div>
            {:else if error}
                <div class="py-4 px-4 text-sm text-lf-danger text-center">
                    {error}
                </div>
            {:else if !hasResults && !loading}
                <div class="py-4 text-sm text-lf-muted text-center">
                    {$t('common.noResults')}
                </div>
            {:else}
                <!-- Loading banner (streaming partial results) -->
                {#if loading}
                    <div class="flex items-center gap-2 px-3 py-1.5 text-xs text-lf-muted bg-lf-panel border-b border-lf-subtle">
                        <Loader2 size={12} class="animate-spin" />
                        <span>{$t('assets.search.searching')} ({providersDone}/{providersTotal})</span>
                    </div>
                {/if}
                {#if grouped}
                    <!-- F21: a premium provider took part in the search. -->
                    <div data-testid="asset-search-premium-section">
                        <div class="flex items-center gap-2 border-b border-lf-subtle bg-lf-panel px-3 py-1.5">
                            <span class="inline-flex items-center rounded-full border border-lf-info-line bg-lf-info-soft px-2 py-0.5 text-xs font-semibold text-lf-info-on-soft" data-testid="asset-search-premium-badge">{$t('assets.search.premiumBadge')}</span>
                        </div>
                        {#each sections.premium as result, i}
                            {@render resultRow(result, i)}
                        {/each}
                        {#if sections.premium.length === 0 && !loading}
                            <p class="px-3 py-2 text-xs text-lf-muted" data-testid="asset-search-premium-empty">{$t('assets.search.premiumEmpty')}</p>
                        {/if}
                    </div>
                    {#if reportPlacement === 'sections' && channel}
                        {@render reportRow(channel)}
                    {/if}
                    {#if sections.community.length > 0}
                        <button
                            type="button"
                            class="flex w-full items-center gap-1.5 border-t border-lf-subtle px-3 py-2 text-left text-xs font-medium text-lf-secondary transition-colors hover:bg-lf-hover"
                            aria-expanded={communityOpen}
                            data-count={sections.community.length}
                            data-testid="asset-search-community-toggle"
                            onclick={() => (communityOpen = !communityOpen)}
                        >
                            {#if communityOpen}
                                <ChevronDown size={14} class="shrink-0" />
                            {:else}
                                <ChevronRight size={14} class="shrink-0" />
                            {/if}
                            <span>{$t('assets.search.communitySection', {values: {count: sections.community.length}})}</span>
                        </button>
                        {#if communityOpen}
                            <p class="flex items-start gap-1.5 border-y border-lf-warning-line bg-lf-warning-soft px-3 py-2 text-xs text-lf-warning-on-soft" data-testid="asset-search-community-warning">
                                <AlertTriangle size={12} class="mt-0.5 shrink-0" />
                                <span>{$t('assets.search.communityWarning')}</span>
                            </p>
                            {#each sections.community as result, j}
                                {@render resultRow(result, sections.premium.length + j)}
                            {/each}
                        {/if}
                    {/if}
                {:else}
                    {#each orderedResults as result, i}
                        {@render resultRow(result, i)}
                    {/each}
                {/if}
                {#if crownShown}
                    <p class="border-t border-lf-subtle px-3 py-1.5 text-xs text-lf-muted" data-testid="asset-search-crown-legend">{$t('assets.search.crownLegend')}</p>
                {/if}
            {/if}
            {#if reportPlacement === 'bottom' && channel}
                {@render reportRow(channel)}
            {/if}
        </div>
    {/if}
</div>

{#snippet resultRow(result: SearchResult, i: number)}
    <button
        type="button"
        data-testid="asset-search-result-{i}"
        data-identifier={result.identifier}
        data-provider={result.provider_code}
        class="w-full flex items-start sm:items-center gap-3 px-3 py-2.5 text-left hover:bg-lf-hover transition-colors border-b border-lf-subtle last:border-b-0"
        onclick={() => selectResult(result)}
    >
        <!-- Icon placeholder -->
        <AssetIcon assetType={result.asset_type} iconUrl={null} altText={result.display_name} size="sm" />

        <!-- Info -->
        <div class="flex-1 min-w-0">
            <div class="flex items-center gap-1.5 text-sm font-medium text-lf-primary min-w-0">
                <span class="truncate">{result.display_name}</span>
            </div>
            <div class="flex flex-nowrap items-center gap-1 text-xs text-lf-muted overflow-x-auto [&>*]:shrink-0">
                {#if webRanks[i] > 0}
                    <span class="font-mono text-lf-muted shrink-0" title={$t('assets.search.rankHint')}>
                        <span class="sm:hidden">Web#{webRanks[i]}</span>
                        <span class="hidden sm:inline">WebSearch#{webRanks[i]}</span>
                    </span>
                    <span class="mx-0.5">·</span>
                {/if}
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
                        <span class="text-lf-muted">{result.provider_code}</span>
                    </span>
                {/if}
            </div>
        </div>

        <!-- Provider URL link -->
        {#if result.provider_url}
            <a href={result.provider_url} target="_blank" rel="noopener noreferrer" class="shrink-0 p-1 text-lf-muted hover:text-lf-link transition-colors" onclick={(e) => e.stopPropagation()} title="Open provider page">
                <ExternalLink size={14} />
            </a>
        {/if}
    </button>
{/snippet}

{#snippet reportRow(channel: SupportChannel)}
    <!-- P20: «Can't find it? Let us know», the report of this search through the instance's support address. -->
    <div class="flex flex-wrap items-center gap-x-1.5 gap-y-0.5 border-t border-lf-subtle px-3 py-2 text-xs text-lf-muted" data-testid="asset-search-report-row">
        <span>{$t('assets.search.reportQuestion')}</span>
        <a
            href={reportLink}
            target={channel.kind === 'mailto' ? undefined : '_blank'}
            rel={channel.kind === 'mailto' ? undefined : 'noopener noreferrer'}
            title={$t(REPORT_VIA_KEY[channel.kind])}
            class="font-medium text-lf-link underline underline-offset-2 hover:opacity-80"
            data-channel={channel.kind}
            data-testid="asset-search-report"
            onclick={reportClicked}>{$t('assets.search.reportAction')}</a
        >
    </div>
{/snippet}

{#if configuring !== null}
    <!-- «Configure» (CP11): the provider's settings; a save searches again. -->
    <PluginSettingsModal family="asset" onClose={() => (configuring = null)} onSaved={configured} open={true} pluginCode={configuring} pluginName={providerName(configuring)} />
{/if}
