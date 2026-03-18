<script lang="ts">
    /**
     * FX Rates List Page
     *
     * Displays all configured FX pairs as cards with mini charts.
     * Features: currency filter (SearchSelect), unified date range picker with presets,
     * global abs/% slider toggle, Sync All, Refresh All, Add Pair.
     */
    import {onMount} from 'svelte';
    import {goto} from '$app/navigation';
    import {_, locale} from '$lib/i18n';
    import {get} from 'svelte/store';
    import {zodiosApi} from '$lib/api';
    import {Coins, Plus, RefreshCw, RotateCw, Settings} from 'lucide-svelte';
    import FxCard from '$lib/components/fx/FxCard.svelte';
    import FxPairAddModal from '$lib/components/fx/FxPairAddModal.svelte';
    import FxSyncModal from '$lib/components/fx/FxSyncModal.svelte';
    import ChartSettingsModal from '$lib/components/charts/ChartSettingsModal.svelte';
    import {ConfirmModal} from '$lib/components/table';
    import DateRangePicker from '$lib/components/ui/DateRangePicker.svelte';
    import {CurrencySearchSelect} from '$lib/components/ui/select';
    import {
        getGlobalSettings, setGlobalSettings,
        getSettingsForPair, setPairSettings, getSettingsVersion,
        type ChartSettings,
    } from '$lib/stores/chartSettingsStore.svelte';
    import {
        signalFromConfig,
        type RenderedSignal,
    } from '$lib/charts/signals';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import {
        createPairSlug, getFxStore, invalidateAllFxStores, removeFxStore,
        apiResultToFxDataPoint,
        type FxDataPoint, type FxPairConfig
    } from '$lib/stores/fxStoreRegistry';
    import {isCardInverted} from '$lib/stores/fxCardInversionStore';
    import {toasts} from '$lib/stores/toastStore.svelte';

    // =========================================================================
    // Types
    // =========================================================================

    interface FxPairState {
        config: FxPairConfig;
        data: FxDataPoint[];
        loading: boolean;
    }

    // =========================================================================
    // State
    // =========================================================================

    let pairs = $state<FxPairState[]>([]);
    let loading = $state(true);
    let error = $state<string | null>(null);

    // Filters
    let filterCurrency1 = $state('');
    let filterCurrency2 = $state('');
    let dateStart = $state((() => { const d = new Date(); d.setMonth(d.getMonth() - 3); return d.toISOString().slice(0, 10); })());
    let dateEnd = $state(new Date().toISOString().slice(0, 10));
    let activePreset: any = $state('3M');
    let globalViewMode = $state<'absolute' | 'percentage'>('absolute');


    // Delete
    let deleteDialogOpen = $state(false);
    let deletingPair = $state<{base: string; quote: string; slug: string} | null>(null);
    let deleteLoading = $state(false);

    // Modals
    let addModalOpen = $state(false);
    let syncModalOpen = $state(false);
    let settingsModalOpen = $state(false);
    /** Slug of the pair currently being configured via per-card ⚙️ (null = global) */
    let settingsTargetSlug = $state<string | null>(null);
    /** Settings to pass to the modal (global or pair-specific) */
    let settingsForModal = $derived(
        settingsTargetSlug ? getSettingsForPair(settingsTargetSlug) : getGlobalSettings()
    );

    // Filter bar adaptive layout
    let filterBarRef = $state<HTMLDivElement | null>(null);
    /** Layout mode based on measured container width:
     *  - 'wide' (≥950px): filters left + actions 2×2 grid right, all inline
     *  - 'tablet' (≥500px): filters left (wrapping) + actions column right
     *  - 'mobile' (<500px): all stacked vertically, actions row at bottom
     */
    let layoutMode = $state<'wide' | 'tablet' | 'mobile'>('tablet');
    /** Whether action buttons show text labels (≥700px) */
    let showActionLabels = $state(true);

    // =========================================================================
    // Derived
    // =========================================================================

    // Extract unique currencies from configured pairs for filter dropdown
    let configuredCurrencies = $derived([...new Set(pairs.flatMap(p => [p.config.base, p.config.quote]))].sort());

    // Allowed currencies for filter 1: if filter 2 is set, only currencies paired with filter 2
    // Exclude the value currently selected in filter 2
    let allowedForFilter1 = $derived((filterCurrency2
        ? [...new Set(pairs
            .filter(p => p.config.base === filterCurrency2 || p.config.quote === filterCurrency2)
            .flatMap(p => [p.config.base, p.config.quote])
        )]
        : configuredCurrencies
    ).filter(c => c !== filterCurrency2).sort());

    // Allowed currencies for filter 2: if filter 1 is set, only currencies paired with filter 1
    // Exclude the value currently selected in filter 1
    let allowedForFilter2 = $derived((filterCurrency1
        ? [...new Set(pairs
            .filter(p => p.config.base === filterCurrency1 || p.config.quote === filterCurrency1)
            .flatMap(p => [p.config.base, p.config.quote])
        )]
        : configuredCurrencies
    ).filter(c => c !== filterCurrency1).sort());

    // Filtered pairs
    let filteredPairs = $derived(pairs.filter(p => {
        if (!filterCurrency1) return true;
        const fc1 = filterCurrency1.toUpperCase();
        const matchFirst = p.config.base === fc1 || p.config.quote === fc1;
        if (!matchFirst) return false;
        if (!filterCurrency2) return true;
        const fc2 = filterCurrency2.toUpperCase();
        return p.config.base === fc2 || p.config.quote === fc2;
    }));

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(async () => {
        await loadPairSources();
    });

    // ResizeObserver for adaptive filter bar layout.
    // Measures the filter bar itself — its width is always 100% of the parent
    // (block-level flex), so layout changes only affect height, not width.
    //
    // contentRect.width = CSS box-width − padding(32px) − border(2px) = box − 34px
    //
    // User-tuned thresholds (CSS box → contentRect):
    //   wide  ≈ 970px box → 936 contentRect
    //   tablet ≈ 635px box → 601 contentRect
    //   labels ≈ 720px box → 686 contentRect
    $effect(() => {
        const el = filterBarRef;
        if (!el) return;
        const ro = new ResizeObserver(([entry]) => {
            const w = entry.contentRect.width;
            if (w >= 1010) layoutMode = 'wide';
            else if (w >= 610) layoutMode = 'tablet';
            else layoutMode = 'mobile';
            showActionLabels = w >= 690;
        });
        ro.observe(el);
        return () => ro.disconnect();
    });

    // =========================================================================
    // Data Loading
    // =========================================================================


    async function loadPairSources() {
        loading = true;
        error = null;
        try {
            const response = await zodiosApi.list_routes_api_v1_fx_providers_routes_get();
            const items = (response as any)?.items || [];

            // Group by unique pair (base/quote)
            const pairMap = new Map<string, FxPairConfig>();
            for (const item of items) {
                const slug = createPairSlug(item.base, item.quote);
                if (!pairMap.has(slug)) {
                    pairMap.set(slug, {
                        base: item.base < item.quote ? item.base : item.quote,
                        quote: item.base < item.quote ? item.quote : item.base,
                        slug,
                        providers: [],
                    });
                }
                const steps = item.chain_steps ?? [];
                const providerCode = steps.length === 1
                    ? steps[0].provider
                    : 'CHAIN:' + steps.map((s: any) => s.provider).join('+');
                pairMap.get(slug)!.providers.push({
                    providerCode,
                    priority: item.priority,
                    chainSteps: steps,
                });
            }

            // Sort providers by priority
            for (const config of pairMap.values()) {
                config.providers.sort((a, b) => a.priority - b.priority);
            }

            // Initialize pair states
            pairs = Array.from(pairMap.values()).map(config => ({
                config,
                data: getFxStore(config.slug).getAllSorted(),
                loading: false,
            }));

            // Fetch chart data for all pairs
            await fetchAllPairData();
        } catch (e: any) {
            console.error('Failed to load pair sources:', e);
            error = e?.message || 'Failed to load FX pairs';
        } finally {
            loading = false;
        }
    }

    async function fetchAllPairData() {
        const promises = pairs.map((_, idx) => fetchPairData(idx));
        await Promise.allSettled(promises);
    }

    async function fetchPairData(index: number) {
        const pair = pairs[index];
        if (!pair) return;

        const store = getFxStore(pair.config.slug);
        const gaps = store.getMissingIntervals(dateStart, dateEnd);

        if (gaps.length === 0) {
            pairs[index] = {...pair, data: store.getRange(dateStart, dateEnd).data};
            return;
        }

        pairs[index] = {...pair, loading: true};

        try {
            const convertRequests = gaps.map(gap => ({
                from_amount: {code: pair.config.base, amount: 1},
                to: pair.config.quote,
                date_range: {start: gap.start, end: gap.end},
            }));

            const response = await zodiosApi.convert_currency_bulk_api_v1_fx_currencies_convert_post(
                convertRequests
            );

            const results = (response as any)?.results || [];
            const points: FxDataPoint[] = results.map((r: any) => apiResultToFxDataPoint(r));
            store.merge(points);

            pairs[index] = {
                ...pair,
                data: store.getRange(dateStart, dateEnd).data,
                loading: false,
            };
        } catch (e: any) {
            // Gracefully handle 404 (no data available) — show existing data if any
            const existingData = store.getRange(dateStart, dateEnd).data;
            pairs[index] = {...pair, data: existingData, loading: false};
            if (e?.response?.status !== 404) {
                console.error(`Failed to fetch data for ${pair.config.slug}:`, e);
            }
        }
    }

    // =========================================================================
    // Chart Settings Helpers
    // =========================================================================

    function handleCardSettings(detail: {slug: string}) {
        settingsTargetSlug = detail.slug;
        settingsModalOpen = true;
    }

    function handleGlobalSettings() {
        settingsTargetSlug = null;
        settingsModalOpen = true;
    }

    function handleSettingsSave(s: ChartSettings) {
        if (settingsTargetSlug) {
            setPairSettings(settingsTargetSlug, s);
        } else {
            setGlobalSettings(s);
        }
    }

    /**
     * Render overlay signals for a pair. Called by FxCard reactively whenever
     * cardViewMode or inverted changes. Receives absolute chart data (post-inversion).
     */
    function getRenderedSignals(slug: string, absoluteData: LineDataPoint[], vm: 'absolute' | 'percentage'): RenderedSignal[] {
        // Access version to trigger reactivity
        void getSettingsVersion();
        const settings = getSettingsForPair(slug);
        if (!settings.signals.length) return [];
        const rendered: RenderedSignal[] = [];
        for (const cfg of settings.signals) {
            const instance = signalFromConfig(cfg);
            if (!instance) continue;

            // For FxPairSignal: resolve data from the TimeSeriesStore before rendering
            if (cfg.signalType === 'fx-pair') {
                const pairSlug = String(cfg.params.pairSlug || '');
                if (!pairSlug) continue;
                try {
                    const store = getFxStore(pairSlug);
                    const storeData = store.getAllSorted();
                    if (storeData.length === 0) continue;
                    // Inject resolved data as LineDataPoint[]
                    instance.params._resolvedData = storeData.map(d => ({
                        date: d.date,
                        value: d.rate,
                    }));
                } catch {
                    continue; // Store not available for this pair
                }
            }

            const results = instance.renderMulti(absoluteData, vm);
            for (const result of results) {
                if (result.data.length > 0) rendered.push(result);
            }
        }
        return rendered;
    }

    // =========================================================================
    // Actions
    // =========================================================================

    async function handleRefreshAll() {
        invalidateAllFxStores();
        pairs = pairs.map(p => ({...p, data: [], loading: true}));
        await fetchAllPairData();
    }

    async function handleRefreshPair(detail: {slug: string}) {
        const idx = pairs.findIndex(p => p.config.slug === detail.slug);
        if (idx < 0) return;
        const store = getFxStore(detail.slug);
        store.invalidateRange(dateStart, dateEnd);
        await fetchPairData(idx);
    }

    function handleEditPair(detail: {base: string; quote: string; slug: string}) {
        const {slug} = detail;
        goto(`/fx/${slug}`);
    }

    function handleDeletePair(detail: {base: string; quote: string; slug: string}) {
        deletingPair = detail;
        deleteDialogOpen = true;
    }

    async function confirmDelete() {
        if (!deletingPair) return;
        deleteLoading = true;
        try {
            // Step 1: Delete all provider sources for this pair (single item, no priority = delete all)
            await zodiosApi.delete_routes_bulk_api_v1_fx_providers_routes_delete([{
                base: deletingPair.base,
                quote: deletingPair.quote,
            }]);

            // Step 2: Delete all historical rates for this pair
            await zodiosApi.delete_rates_endpoint_api_v1_fx_currencies_rate_delete([{
                from: deletingPair.base,
                to: deletingPair.quote,
                delete_all: true,
            }]);

            // Step 3: Clean up frontend state
            removeFxStore(deletingPair.slug);
            pairs = pairs.filter(p => p.config.slug !== deletingPair!.slug);
            deleteDialogOpen = false;
            deletingPair = null;
        } catch (e: any) {
            console.error('Failed to delete pair:', e);
        } finally {
            deleteLoading = false;
        }
    }

    function handleDateRangeChange(newStart: string, newEnd: string) {
        dateStart = newStart;
        dateEnd = newEnd;
        fetchAllPairData();
    }

    function handleAddPair() {
        addModalOpen = true;
    }

    function handleSyncAll() {
        syncModalOpen = true;
    }

    async function handleSyncPair(detail: {slug: string; base: string; quote: string}) {
        const {slug} = detail;
        const idx = pairs.findIndex(p => p.config.slug === slug);
        if (idx < 0) return;
        pairs[idx] = {...pairs[idx], loading: true};
        try {
            const response = await zodiosApi.sync_rates_api_v1_fx_currencies_sync_post({
                pairs: [slug],
                start: dateStart,
                end: dateEnd,
            });
            const r = (response as any)?.results?.[0];
            if (r) {
                const label = slug.replace('-', '/');
                const t = get(_);
                if (r.status === 'ok') {
                    toasts.success(t('fx.sync.toastOk', {values: {pair: label, fetched: r.points_fetched ?? 0, changed: r.points_changed ?? 0, provider: r.provider_used ?? '?'}}));
                } else if (r.status === 'partial') {
                    let msg = t('fx.sync.toastPartial', {values: {pair: label, fetched: r.points_fetched ?? 0, changed: r.points_changed ?? 0, provider: r.provider_used ?? '?'}});
                    if (r.message) msg += '\n' + r.message;
                    toasts.warning(msg);
                } else if (r.status === 'skipped') {
                    toasts.info(t('fx.sync.toastSkipped', {values: {pair: label}}));
                } else {
                    let msg = t('fx.sync.toastFailed', {values: {pair: label}});
                    if (r.message) msg += '\n' + r.message;
                    toasts.error(msg);
                }
            }
            // After sync, refresh the pair
            const store = getFxStore(slug);
            store.invalidateRange(dateStart, dateEnd);
            await fetchPairData(idx);
        } catch (e: any) {
            toasts.error(get(_)('fx.sync.toastFailed', {values: {pair: slug.replace('-', '/')}}));
            console.error('Sync failed for', slug, e);
            pairs[idx] = {...pairs[idx], loading: false};
        }
    }

    async function handlePairCreated(detail: {base: string; quote: string; hasRealProvider: boolean}) {
        addModalOpen = false;
        // Reload pair sources and fetch data (sync already done by modal)
        await loadPairSources();
        await fetchAllPairData();
    }

    async function handleSynced() {
        // Don't close modal — let user see the results, they close manually
        // But refresh data in background
        invalidateAllFxStores();
        pairs = pairs.map(p => ({...p, data: [], loading: true}));
        await fetchAllPairData();
    }
</script>

<div class="space-y-6" data-testid="fx-page">
    <!-- Header: Title left, + Add Pair right -->
    <div class="flex items-center justify-between">
        <div>
            <h2 class="text-lg font-semibold text-gray-700 dark:text-gray-200 flex items-center gap-2">
                {$_('fx.title')}
                {#if pairs.length > 0}
                    <span class="text-xs font-mono px-1.5 py-0.5 rounded-full bg-libre-green/10 text-libre-green dark:bg-libre-green/20 dark:text-emerald-400">{pairs.length}</span>
                {/if}
            </h2>
            <p class="text-gray-500 dark:text-gray-400 text-sm">{$_('fx.subtitle')}</p>
        </div>
        <button
            class="flex items-center gap-1.5 px-3 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors whitespace-nowrap"
            onclick={handleAddPair}
            data-testid="fx-add-pair-button"
        >
            <Plus size={16} />
            {$_('fx.actions.addPair')}
        </button>
    </div>

    <!-- Filter Bar: 100% programmatic layout — NO flex-wrap, NO CSS-driven wrapping.
         wide:   [ datepicker  currency ─── actions-2×2 ]  all in one row
         tablet: [ datepicker       ] [ actions-2×2 ]      filters stacked, actions grid right
                 [ currency-filters ] [             ]
         mobile: [ datepicker       ]  all stacked centered
                 [ currency-filters ]
                 [ actions-row      ] -->
    <div
        bind:this={filterBarRef}
        class="flex gap-3 p-4 bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700
               {layoutMode === 'mobile' ? 'flex-col items-center' : 'flex-row items-center justify-between'}"
    >
        <!-- Filters block -->
        <div class="flex gap-3 {layoutMode === 'mobile' ? 'flex-col items-center' : layoutMode === 'wide' ? 'flex-row items-center flex-1' : 'flex-col items-center'}">
            <!-- DateRangePicker -->
            <div class="max-w-md">
                <DateRangePicker
                    bind:start={dateStart}
                    bind:end={dateEnd}
                    bind:activePreset
                    compact={true}
                    onchange={handleDateRangeChange}
                />
            </div>

            <!-- Currency Filters — always grouped as a pair -->
            <div class="flex items-center gap-3">
                <div class="w-40">
                    <CurrencySearchSelect
                        bind:value={filterCurrency1}
                        includeAll={true}
                        allowedCurrencies={allowedForFilter1}
                        placeholder={$_('fx.filter.filterCurrency')}
                        maxVisibleItems={6}
                        onchange={(v) => {
                            if (v === '' && filterCurrency2) {
                                filterCurrency1 = filterCurrency2;
                                filterCurrency2 = '';
                            } else {
                                filterCurrency1 = v;
                                if (filterCurrency2 && !allowedForFilter2.includes(filterCurrency2)) {
                                    filterCurrency2 = '';
                                }
                            }
                        }}
                    />
                </div>
                <div class="w-40 transition-opacity {filterCurrency1 ? '' : 'opacity-50'}">
                    <CurrencySearchSelect
                        bind:value={filterCurrency2}
                        includeAll={true}
                        allowedCurrencies={allowedForFilter2}
                        disabled={!filterCurrency1}
                        placeholder={$_('fx.filter.secondCurrency')}
                        maxVisibleItems={6}
                    />
                </div>
            </div>
        </div>

        <!-- Actions: 2×2 grid (wide+tablet), horizontal row (mobile) -->
        <div class="flex shrink-0 gap-1.5
                    {layoutMode === 'mobile' ? 'flex-row justify-center' : 'grid grid-cols-2'}">
            <!-- Abs/% toggle -->
            <div class="flex rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
                <button
                    class="flex-1 px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {globalViewMode === 'absolute'
                        ? 'bg-libre-green text-white'
                        : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                    onclick={() => { globalViewMode = 'absolute'; }}
                >Abs</button>
                <button
                    class="flex-1 px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {globalViewMode === 'percentage'
                        ? 'bg-libre-green text-white'
                        : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                    onclick={() => { globalViewMode = 'percentage'; }}
                >%</button>
            </div>
            <!-- Settings -->
            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                title={$_('fx.actions.settings')}
                onclick={handleGlobalSettings}
            >
                <Settings size={14} />
                {#if showActionLabels}<span>{$_('fx.actions.settings')}</span>{/if}
            </button>
            <!-- Sync All -->
            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                onclick={handleSyncAll}
                title={$_('fx.actions.syncAll')}
            >
                <RotateCw size={14} />
                {#if showActionLabels}<span>{$_('fx.actions.syncAll')}</span>{/if}
            </button>
            <!-- Refresh All -->
            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                onclick={handleRefreshAll}
                title={$_('fx.actions.refreshAll')}
            >
                <RefreshCw size={14} />
                {#if showActionLabels}<span>{$_('fx.actions.refreshAll')}</span>{/if}
            </button>
        </div>
    </div>

    <!-- Content -->
    {#if loading}
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {#each Array(3) as _}
                <div class="bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 p-4 animate-pulse">
                    <div class="h-5 bg-gray-200 dark:bg-slate-700 rounded w-32 mb-3"></div>
                    <div class="h-20 bg-gray-100 dark:bg-slate-700 rounded mb-3"></div>
                    <div class="h-4 bg-gray-100 dark:bg-slate-700 rounded w-20"></div>
                </div>
            {/each}
        </div>
    {:else if error}
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center">
            <p class="text-red-600 dark:text-red-400">{error}</p>
            <button
                class="mt-3 px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                onclick={loadPairSources}
            >
                {$_('common.retry')}
            </button>
        </div>
    {:else if filteredPairs.length === 0}
        <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm p-12 text-center border border-gray-100 dark:border-slate-700">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-amber-100 dark:bg-amber-900/30 rounded-full mb-4">
                <Coins class="text-amber-600 dark:text-amber-400" size={32}/>
            </div>
            {#if pairs.length === 0}
                <h3 class="text-lg font-semibold text-gray-700 dark:text-gray-200 mb-2">{$_('fx.empty.noPairsTitle')}</h3>
                <p class="text-gray-500 dark:text-gray-400 mb-4">{$_('fx.empty.noPairsDesc')}</p>
                <button
                    class="px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors"
                    onclick={handleAddPair}
                >
                    <Plus size={16} class="inline mr-1" />
                    {$_('fx.empty.addFirstPair')}
                </button>
            {:else}
                <h3 class="text-lg font-semibold text-gray-700 dark:text-gray-200 mb-2">{$_('fx.empty.noMatchesTitle')}</h3>
                <p class="text-gray-500 dark:text-gray-400">{$_('fx.empty.noMatchesDesc')}</p>
            {/if}
        </div>
    {:else}
        <!-- Card Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {#each filteredPairs as pair (pair.config.slug)}
                <FxCard
                    base={pair.config.base}
                    quote={pair.config.quote}
                    slug={pair.config.slug}
                    data={pair.data}
                    loading={pair.loading}
                    manualOnly={pair.config.providers.length === 1 && pair.config.providers[0].providerCode === 'MANUAL'}
                    {globalViewMode}
                    chartSettings={getSettingsForPair(pair.config.slug)}
                    renderSignals={(chartData, vm) => getRenderedSignals(pair.config.slug, chartData, vm)}
                    onedit={handleEditPair}
                    ondelete={handleDeletePair}
                    onrefresh={handleRefreshPair}
                    onsync={handleSyncPair}
                    onsettings={handleCardSettings}
                />
            {/each}
        </div>
    {/if}
</div>

<!-- Delete Confirm Dialog -->
<ConfirmModal
    open={deleteDialogOpen}
    title="Delete FX Pair"
    message="Are you sure you want to delete {deletingPair?.base ?? ''}/{deletingPair?.quote ?? ''}? This will remove the provider configuration and all historical exchange rates."
    confirmText="Delete"
    danger={true}
    onConfirm={confirmDelete}
    onCancel={() => { deleteDialogOpen = false; deletingPair = null; }}
/>

<!-- Add Pair Modal -->
<FxPairAddModal
    bind:open={addModalOpen}
    {dateStart}
    {dateEnd}
    oncreated={handlePairCreated}
    onclose={() => addModalOpen = false}
/>

<!-- Sync Modal -->
<FxSyncModal
    bind:open={syncModalOpen}
    {dateStart}
    {dateEnd}
    pairs={pairs
        .filter(p => !(p.config.providers.length === 1 && p.config.providers[0].providerCode === 'MANUAL'))
        .map(p => `${p.config.base}-${p.config.quote}`)}
    onsynced={handleSynced}
    onclose={() => syncModalOpen = false}
/>

<!-- Chart Settings Modal (global or per-card depending on settingsTargetSlug) -->
<ChartSettingsModal
    bind:open={settingsModalOpen}
    settings={settingsForModal}
    mode={settingsTargetSlug ? 'pair' : 'global'}
    availablePairs={pairs.map(p => `${p.config.base}-${p.config.quote}`)}
    pairData={settingsTargetSlug
        ? pairs.find(p => p.config.slug === settingsTargetSlug)?.data?.map(d => {
            const inv = isCardInverted(settingsTargetSlug ?? '');
            const rate = inv && d.rate !== 0 ? 1 / d.rate : d.rate;
            return {date: d.date, value: rate, staleDays: d.backwardFillInfo?.daysBack ?? 0};
        })
        : undefined}
    pairsDataMap={Object.fromEntries(
        pairs
            .filter(p => p.data.length > 0)
            .map(p => {
                const inv = isCardInverted(p.config.slug);
                return [p.config.slug, p.data.map(d => {
                    const rate = inv && d.rate !== 0 ? 1 / d.rate : d.rate;
                    return {date: d.date, value: rate, staleDays: d.backwardFillInfo?.daysBack ?? 0};
                })];
            })
    )}
    onsave={handleSettingsSave}
    onclose={() => { settingsModalOpen = false; settingsTargetSlug = null; }}
/>

