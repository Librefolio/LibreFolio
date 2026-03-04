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
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {Coins, Plus, RefreshCw, RotateCcw, Settings} from 'lucide-svelte';
    import FxCard from '$lib/components/fx/FxCard.svelte';
    import FxPairAddModal from '$lib/components/fx/FxPairAddModal.svelte';
    import FxSyncModal from '$lib/components/fx/FxSyncModal.svelte';
    import {ConfirmModal} from '$lib/components/table';
    import DateRangePicker from '$lib/components/ui/DateRangePicker.svelte';
    import {CurrencySearchSelect} from '$lib/components/ui/select';
    import {
        createPairSlug, getFxStore, invalidateAllFxStores, removeFxStore,
        apiResultToFxDataPoint,
        type FxDataPoint, type FxPairConfig
    } from '$lib/stores/fxStoreRegistry';

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

    let pairs: FxPairState[] = [];
    let loading = true;
    let error: string | null = null;

    // Filters
    let filterCurrency1 = '';
    let filterCurrency2 = '';
    let dateStart = (() => { const d = new Date(); d.setMonth(d.getMonth() - 3); return d.toISOString().slice(0, 10); })();
    let dateEnd = new Date().toISOString().slice(0, 10);
    let activePreset: any = '3M';
    let globalViewMode: 'absolute' | 'percentage' = 'absolute';


    // Delete
    let deleteDialogOpen = false;
    let deletingPair: {base: string; quote: string; slug: string} | null = null;
    let deleteAlsoRates = false;
    let deleteLoading = false;

    // Modals
    let addModalOpen = false;
    let syncModalOpen = false;

    // =========================================================================
    // Derived
    // =========================================================================

    // Extract unique currencies from configured pairs for filter dropdown
    $: configuredCurrencies = [...new Set(pairs.flatMap(p => [p.config.base, p.config.quote]))].sort();

    // Filtered pairs
    $: filteredPairs = pairs.filter(p => {
        if (!filterCurrency1) return true;
        const fc1 = filterCurrency1.toUpperCase();
        const matchFirst = p.config.base === fc1 || p.config.quote === fc1;
        if (!matchFirst) return false;
        if (!filterCurrency2) return true;
        const fc2 = filterCurrency2.toUpperCase();
        return p.config.base === fc2 || p.config.quote === fc2;
    });

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(async () => {
        await loadPairSources();
    });

    // =========================================================================
    // Data Loading
    // =========================================================================


    async function loadPairSources() {
        loading = true;
        error = null;
        try {
            const response = await zodiosApi.list_pair_sources_api_v1_fx_providers_pair_sources_get();
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
                pairMap.get(slug)!.providers.push({
                    providerCode: item.provider_code,
                    priority: item.priority,
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
    // Actions
    // =========================================================================

    async function handleRefreshAll() {
        invalidateAllFxStores();
        pairs = pairs.map(p => ({...p, data: [], loading: true}));
        await fetchAllPairData();
    }

    async function handleRefreshPair(event: CustomEvent<{slug: string}>) {
        const idx = pairs.findIndex(p => p.config.slug === event.detail.slug);
        if (idx < 0) return;
        const store = getFxStore(event.detail.slug);
        store.invalidateRange(dateStart, dateEnd);
        await fetchPairData(idx);
    }

    function handleEditPair(event: CustomEvent<{base: string; quote: string; slug: string}>) {
        // Navigate to detail page via client-side routing
        const {slug} = event.detail;
        goto(`/fx/${slug}`);
    }

    function handleDeletePair(event: CustomEvent<{base: string; quote: string; slug: string}>) {
        deletingPair = event.detail;
        deleteAlsoRates = false;
        deleteDialogOpen = true;
    }

    async function confirmDelete() {
        if (!deletingPair) return;
        deleteLoading = true;
        try {
            const pair = pairs.find(p => p.config.slug === deletingPair!.slug);
            if (pair) {
                const deleteItems = pair.config.providers.map(() => ({
                    base: pair.config.base,
                    quote: pair.config.quote,
                }));
                await zodiosApi.delete_pair_sources_bulk_api_v1_fx_providers_pair_sources_delete(deleteItems);
            }

            if (deleteAlsoRates) {
                console.log('TODO: delete historical rates for', deletingPair.slug);
            }

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

    async function handleSyncPair(event: CustomEvent<{slug: string; base: string; quote: string}>) {
        const {slug, base, quote} = event.detail;
        const idx = pairs.findIndex(p => p.config.slug === slug);
        if (idx < 0) return;
        pairs[idx] = {...pairs[idx], loading: true};
        try {
            await zodiosApi.sync_rates_api_v1_fx_currencies_sync_get({
                queries: {
                    start: dateStart,
                    end: dateEnd,
                    currencies: `${base},${quote}`,
                }
            });
            // After sync, refresh the pair
            const store = getFxStore(slug);
            store.invalidateRange(dateStart, dateEnd);
            await fetchPairData(idx);
        } catch (e: any) {
            console.error('Sync failed for', slug, e);
            pairs[idx] = {...pairs[idx], loading: false};
        }
    }

    async function handlePairCreated() {
        addModalOpen = false;
        await loadPairSources();
    }

    async function handleSynced() {
        syncModalOpen = false;
        await handleRefreshAll();
    }
</script>

<div class="space-y-6">
    <!-- Header: Title left, + Add Pair right -->
    <div class="flex items-center justify-between">
        <div>
            <h2 class="text-lg font-semibold text-gray-700 dark:text-gray-200">{$_('fx.title')}</h2>
            <p class="text-gray-500 dark:text-gray-400 text-sm">{$_('fx.subtitle')}</p>
        </div>
        <button
            class="flex items-center gap-1.5 px-3 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors whitespace-nowrap"
            onclick={handleAddPair}
        >
            <Plus size={16} />
            {$_('fx.actions.addPair')}
        </button>
    </div>

    <!-- Filter Bar: 3-column grid on desktop (left|center|right), stacked centered on mobile -->
    <div class="grid grid-cols-1 lg:grid-cols-[auto_1fr_auto] items-center gap-3 p-4 bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700">
        <!-- Section 1: DateRangePicker — left on desktop, centered on mobile -->
        <div class="flex justify-center lg:justify-start">
            <DateRangePicker
                bind:start={dateStart}
                bind:end={dateEnd}
                bind:activePreset
                compact={true}
                onchange={handleDateRangeChange}
            />
        </div>

        <!-- Section 2: Currency filters — centered always, side by side -->
        <div class="flex justify-center">
            <div class="flex flex-row items-center gap-2">
                <div class="w-40">
                    <CurrencySearchSelect
                        bind:value={filterCurrency1}
                        includeAll={true}
                        allowedCurrencies={configuredCurrencies}
                        placeholder={$_('fx.filter.filterCurrency')}
                        maxVisibleItems={6}
                        onchange={(v) => { filterCurrency1 = v; filterCurrency2 = ''; }}
                    />
                </div>
                {#if filterCurrency1}
                    <div class="w-40">
                        <CurrencySearchSelect
                            bind:value={filterCurrency2}
                            includeAll={true}
                            allowedCurrencies={configuredCurrencies}
                            placeholder={$_('fx.filter.secondCurrency')}
                            maxVisibleItems={6}
                        />
                    </div>
                {/if}
            </div>
        </div>

        <!-- Section 3: Actions — right on desktop, centered on mobile -->
        <div class="flex justify-center lg:justify-end">
            <div class="grid grid-cols-2 gap-1.5">
                <!-- Row 1: Abs/% toggle + Settings gear -->
                <div class="flex rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden w-full">
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
                <button
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                    title={$_('fx.actions.settings')}
                >
                    <Settings size={14} />
                    <span class="hidden xl:inline">{$_('fx.actions.settings')}</span>
                </button>

                <!-- Row 2: Sync All + Refresh All -->
                <button
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                    onclick={handleSyncAll}
                    title={$_('fx.actions.syncAll')}
                >
                    <RotateCcw size={14} />
                    <span class="hidden xl:inline">{$_('fx.actions.syncAll')}</span>
                </button>
                <button
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                    onclick={handleRefreshAll}
                    title={$_('fx.actions.refreshAll')}
                >
                    <RefreshCw size={14} />
                    <span class="hidden xl:inline">{$_('fx.actions.refreshAll')}</span>
                </button>
            </div>
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
                    on:edit={handleEditPair}
                    on:delete={handleDeletePair}
                    on:refresh={handleRefreshPair}
                    on:sync={handleSyncPair}
                />
            {/each}
        </div>
    {/if}
</div>

<!-- Delete Confirm Dialog -->
<ConfirmModal
    open={deleteDialogOpen}
    title="Delete FX Pair"
    message="Are you sure you want to delete {deletingPair?.base ?? ''}/{deletingPair?.quote ?? ''}? This will remove the provider configuration."
    confirmText="Delete"
    danger={true}
    onConfirm={confirmDelete}
    onCancel={() => { deleteDialogOpen = false; deletingPair = null; }}
/>

<!-- Add Pair Modal -->
<FxPairAddModal
    bind:open={addModalOpen}
    oncreated={handlePairCreated}
    onclose={() => addModalOpen = false}
/>

<!-- Sync Modal -->
<FxSyncModal
    bind:open={syncModalOpen}
    {dateStart}
    {dateEnd}
    on:synced={handleSynced}
    on:close={() => syncModalOpen = false}
/>
