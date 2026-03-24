<script lang="ts">
    /**
     * Assets List Page — Dual View (Grid / Table)
     *
     * Features:
     * - Search filter (debounced)
     * - Type filter (SimpleSelect)
     * - Currency filter (CurrencySearchSelect)
     * - Active toggle
     * - DateRangePicker for Δ columns (default 3M)
     * - ViewModeToggle (grid/list, per-user localStorage)
     * - Add Asset button (placeholder for Step 3)
     *
     * Svelte 5 runes throughout.
     */
    import {onMount} from 'svelte';
    import {goto} from '$app/navigation';
    import {_ as t} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {BarChart3, Plus, RefreshCw, RotateCw, Search, Settings, Trash2, X} from 'lucide-svelte';
    import AssetCard from '$lib/components/assets/AssetCard.svelte';
    import AssetTable from '$lib/components/assets/AssetTable.svelte';
    import type {AssetRow} from '$lib/components/assets/AssetTable.svelte';
    import ViewModeToggle from '$lib/components/ui/ViewModeToggle.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import DataTableToolbar from '$lib/components/table/DataTableToolbar.svelte';
    import DateRangePicker from '$lib/components/ui/DateRangePicker.svelte';
    import {SimpleSelect, CurrencySearchSelect} from '$lib/components/ui/select';

    // =========================================================================
    // Types
    // =========================================================================

    interface AssetInfo {
        id: number;
        display_name: string;
        currency: string;
        icon_url?: string | null;
        asset_type?: string | null;
        has_provider: boolean;
        active: boolean;
    }

    interface AssetState extends AssetInfo {
        lastPrice: number | null;
        deltaAbs: number | null;
        deltaPercent: number | null;
        chartData: Array<{date: string; value: number; staleDays?: number}>;
        deltas: Record<string, number | null>;
        loadingPrices: boolean;
    }

    // Delta periods for table columns
    const DELTA_PERIODS = [
        { key: '1W', days: 7 },
        { key: '1M', days: 30 },
        { key: '3M', days: 91 },
        { key: '6M', days: 182 },
        { key: '1Y', days: 365 },
        { key: '2Y', days: 730 },
        { key: '3Y', days: 1095 },
        { key: '5Y', days: 1825 },
    ] as const;

    // =========================================================================
    // State
    // =========================================================================

    let assets = $state<AssetState[]>([]);
    let loading = $state(true);
    let error = $state<string | null>(null);
    let assetTableComponent: AssetTable | undefined = $state(undefined);
    let selectedAssetRows = $state<AssetRow[]>([]);

    // Filters
    let searchText = $state('');
    let filterType = $state('');
    let filterCurrency = $state('');
    let filterActiveOnly = $state(true);

    // Date range for Δ columns
    let dateStart = $state((() => { const d = new Date(); d.setMonth(d.getMonth() - 3); return d.toISOString().slice(0, 10); })());
    let dateEnd = $state(new Date().toISOString().slice(0, 10));
    let activePreset: any = $state('3M');

    // View mode
    let viewMode = $state<'grid' | 'list'>('grid');

    // Debounce timer
    let searchTimer: ReturnType<typeof setTimeout> | undefined;

    // =========================================================================
    // Derived
    // =========================================================================

    let typeOptions = $derived([
        {value: '', label: $t('assets.allTypes')},
        {value: 'STOCK', label: 'Stock'},
        {value: 'ETF', label: 'ETF'},
        {value: 'BOND', label: 'Bond'},
        {value: 'CRYPTO', label: 'Crypto'},
        {value: 'FUND', label: 'Fund'},
        {value: 'HOLD', label: 'Hold'},
        {value: 'CROWDFUND_LOAN', label: 'Crowdfund Loan'},
        {value: 'OTHER', label: 'Other'},
    ]);

    // Extract unique currencies from all assets
    let configuredCurrencies = $derived([...new Set(assets.map(a => a.currency))].sort());

    let filteredAssets = $derived(assets.filter(a => {
        if (filterActiveOnly && !a.active) return false;
        if (filterType && a.asset_type !== filterType) return false;
        if (filterCurrency && a.currency !== filterCurrency) return false;
        if (searchText) {
            const q = searchText.toLowerCase();
            if (!a.display_name.toLowerCase().includes(q)) return false;
        }
        return true;
    }));

    // Which delta periods are visible for the selected date range
    let visiblePeriods = $derived(
        DELTA_PERIODS.filter(p => {
            const rangeMs = new Date(dateEnd).getTime() - new Date(dateStart).getTime();
            const rangeDays = rangeMs / (1000 * 60 * 60 * 24);
            return rangeDays >= p.days;
        })
    );

    // Map to AssetRow for table
    let tableRows = $derived<AssetRow[]>(filteredAssets.map(a => ({
        id: a.id,
        display_name: a.display_name,
        currency: a.currency,
        icon_url: a.icon_url,
        asset_type: a.asset_type,
        has_provider: a.has_provider,
        active: a.active,
        lastPrice: a.lastPrice,
        deltaAbs: a.deltaAbs,
        deltaPercent: a.deltaPercent,
        deltas: a.deltas,
    })));

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(async () => {
        await loadAssets();
    });

    // Debounced search
    function handleSearchInput(e: Event) {
        const val = (e.target as HTMLInputElement).value;
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => { searchText = val; }, 300);
    }

    // =========================================================================
    // Helpers
    // =========================================================================

    /**
     * Compute Δ% for a given period from chartData.
     * Pₙ = last data point, P_start = closest point <= (Pₙ - periodDays).
     */
    function computePeriodDelta(
        chartData: Array<{date: string; value: number}>,
        periodDays: number,
    ): number | null {
        if (chartData.length === 0) return null;

        const pn = chartData[chartData.length - 1];
        if (!pn || pn.value === 0) return null;

        const targetDate = new Date(pn.date);
        targetDate.setDate(targetDate.getDate() - periodDays);
        const targetStr = targetDate.toISOString().slice(0, 10);

        // Backward-fill lookup: find closest point <= targetDate
        let startPoint: {date: string; value: number} | null = null;
        for (const point of chartData) {
            if (point.date <= targetStr) {
                startPoint = point;
            } else {
                break;
            }
        }

        if (!startPoint || startPoint.value === 0) return null;
        return ((pn.value - startPoint.value) / startPoint.value) * 100;
    }

    // =========================================================================
    // Data Loading
    // =========================================================================

    async function loadAssets() {
        loading = true;
        error = null;
        try {
            const response = await zodiosApi.list_assets_api_v1_assets_query_get({
                queries: {},
            });
            const items = response as any[];

            assets = items.map((item: any) => ({
                id: item.id,
                display_name: item.display_name,
                currency: item.currency,
                icon_url: item.icon_url ?? null,
                asset_type: item.asset_type ?? null,
                has_provider: item.has_provider ?? false,
                active: item.active ?? true,
                lastPrice: null,
                deltaAbs: null,
                deltaPercent: null,
                chartData: [],
                deltas: {},
                loadingPrices: false,
            }));

            // Fetch price data for all assets via bulk query
            await fetchAllPriceData();
        } catch (e: any) {
            console.error('Failed to load assets:', e);
            error = e?.message || 'Failed to load assets';
        } finally {
            loading = false;
        }
    }

    async function fetchAllPriceData() {
        if (assets.length === 0) return;

        // Mark all as loading
        assets = assets.map(a => ({...a, loadingPrices: true}));

        try {
            // Build bulk query
            const queries = assets.map(a => ({
                asset_id: a.id,
                date_range: { start: dateStart, end: dateEnd },
            }));

            const response = await zodiosApi.query_prices_bulk_api_v1_assets_prices_query_post(queries) as any;
            const items = response.items ?? [];

            // Process results
            const resultMap = new Map<number, any[]>();
            for (const result of items) {
                resultMap.set(result.asset_id, result.prices ?? []);
            }

            assets = assets.map(asset => {
                const prices = resultMap.get(asset.id) ?? [];

                if (prices.length > 0) {
                    const firstPrice = prices[0]?.close != null ? Number(prices[0].close) : null;
                    const lastPrice = prices[prices.length - 1]?.close != null
                        ? Number(prices[prices.length - 1].close) : null;

                    let deltaAbs: number | null = null;
                    let deltaPercent: number | null = null;
                    if (firstPrice !== null && lastPrice !== null && firstPrice !== 0) {
                        deltaAbs = lastPrice - firstPrice;
                        deltaPercent = ((lastPrice - firstPrice) / firstPrice) * 100;
                    }

                    const chartData = prices.map((p: any) => ({
                        date: p.date,
                        value: Number(p.close ?? 0),
                        staleDays: p.backward_fill_info?.days_back ?? 0,
                    }));

                    // Compute multi-period deltas
                    const deltas: Record<string, number | null> = {};
                    for (const period of DELTA_PERIODS) {
                        deltas[period.key] = computePeriodDelta(chartData, period.days);
                    }

                    return {
                        ...asset,
                        lastPrice,
                        deltaAbs,
                        deltaPercent,
                        chartData,
                        deltas,
                        loadingPrices: false,
                    };
                }
                return {...asset, loadingPrices: false, deltas: {}};
            });
        } catch (e: any) {
            console.error('Failed to fetch prices bulk:', e);
            assets = assets.map(a => ({...a, loadingPrices: false, deltas: {}}));
        }
    }

    function handleDateRangeChange(newStart: string, newEnd: string) {
        dateStart = newStart;
        dateEnd = newEnd;
        fetchAllPriceData();
    }

    // =========================================================================
    // Actions
    // =========================================================================

    function handleAddAsset() {
        // Placeholder — Step 3 will add modal
        console.log('Add Asset clicked (placeholder)');
    }

    async function handleSyncAsset(asset: any) {
        // TODO: implement actual sync via POST /assets/prices/refresh
        console.log('Sync Asset clicked:', asset.id);
    }

    async function handleRefreshAsset(_asset: any) {
        // Re-fetch price data from DB for all assets
        await fetchAllPriceData();
    }

    function handleDeleteAsset(asset: any) {
        // Placeholder — Step 3 will add delete confirm
        console.log('Delete Asset clicked:', asset.id);
    }

    // =========================================================================
    // Bulk Actions (table selection)
    // =========================================================================

    async function handleBulkSyncAssets() {
        for (const row of selectedAssetRows) {
            if (row.has_provider) await handleSyncAsset(row);
        }
        assetTableComponent?.getTableRef()?.clearSelection();
        selectedAssetRows = [];
    }

    async function handleBulkRefreshAssets() {
        await fetchAllPriceData();
        assetTableComponent?.getTableRef()?.clearSelection();
        selectedAssetRows = [];
    }

    async function handleBulkDeleteAssets() {
        for (const row of selectedAssetRows) {
            await handleDeleteAsset(row);
        }
    }

    function clearFilters() {
        searchText = '';
        filterType = '';
        filterCurrency = '';
    }

    let hasActiveFilters = $derived(!!searchText || !!filterType || !!filterCurrency);
</script>

<div class="space-y-6" data-testid="assets-page">
    <!-- Header: Title left, ViewModeToggle + Add Asset right -->
    <div class="flex items-center justify-between">
        <div>
            <h2 class="text-lg font-semibold text-gray-700 dark:text-gray-200 flex items-center gap-2">
                {$t('assets.title')}
                {#if assets.length > 0}
                    <span data-testid="assets-count-badge" class="text-xs font-mono px-1.5 py-0.5 rounded-full bg-libre-green/10 text-libre-green dark:bg-libre-green/20 dark:text-emerald-400">{assets.length}</span>
                {/if}
            </h2>
            <p class="text-gray-500 dark:text-gray-400 text-sm">{$t('assets.subtitle')}</p>
        </div>
        <div class="flex items-center gap-2">
            {#if viewMode === 'list' && selectedAssetRows.length > 0}
                <DataTableToolbar
                    selectedCount={selectedAssetRows.length}
                    bulkActions={[
                        { id: 'sync', icon: RotateCw, label: 'Sync', onClick: () => handleBulkSyncAssets() },
                        { id: 'refresh', icon: RefreshCw, label: 'Refresh', onClick: () => handleBulkRefreshAssets() },
                        { id: 'delete', icon: Trash2, label: 'Delete', variant: 'danger', onClick: () => handleBulkDeleteAssets() },
                    ]}
                    onClearSelection={() => { assetTableComponent?.getTableRef()?.clearSelection(); selectedAssetRows = []; }}
                />
            {/if}
            <ViewModeToggle bind:mode={viewMode} storageKey="assetsViewMode" />
            <button
                class="flex items-center gap-1.5 px-3 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors whitespace-nowrap"
                onclick={handleAddAsset}
                data-testid="assets-add-button"
            >
                <Plus size={16} />
                {$t('assets.addAsset')}
            </button>
        </div>
    </div>

    <!-- Filter Bar -->
    <div class="flex flex-wrap gap-3 p-4 bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 items-center">
        <!-- Date Range -->
        <div class="max-w-md" data-testid="assets-date-range">
            <DateRangePicker
                bind:start={dateStart}
                bind:end={dateEnd}
                bind:activePreset
                compact={true}
                onchange={handleDateRangeChange}
            />
        </div>

        <!-- Search -->
        <div class="relative w-48">
            <Search size={14} class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
                type="text"
                value={searchText}
                oninput={handleSearchInput}
                placeholder={$t('assets.searchPlaceholder')}
                class="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 focus:ring-1 focus:ring-libre-green focus:border-libre-green"
                data-testid="assets-search-input"
            />
        </div>

        <!-- Type Filter -->
        <div class="w-40">
            <SimpleSelect
                bind:value={filterType}
                options={typeOptions}
                compact={true}
                testId="assets-type-filter"
            />
        </div>

        <!-- Currency Filter -->
        <div class="w-36">
            <CurrencySearchSelect
                bind:value={filterCurrency}
                includeAll={true}
                allowedCurrencies={configuredCurrencies}
                placeholder={$t('assets.allCurrencies')}
                maxVisibleItems={6}
            />
        </div>

        <!-- Active toggle -->
        <button
            class="px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors whitespace-nowrap
                   {filterActiveOnly
                       ? 'bg-libre-green text-white border-libre-green'
                       : 'bg-white dark:bg-slate-700 text-gray-500 dark:text-gray-400 border-gray-200 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-600'}"
            onclick={() => { filterActiveOnly = !filterActiveOnly; }}
            data-testid="assets-active-toggle"
        >
            {filterActiveOnly ? $t('assets.showActive') : $t('assets.showAll')}
        </button>

        <!-- Reset filters -->
        {#if hasActiveFilters}
            <button
                class="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 hover:text-red-500 dark:text-gray-400 dark:hover:text-red-400 transition-colors"
                onclick={clearFilters}
                title={$t('fx.filter.resetFilters')}
            >
                <X size={16} />
            </button>
        {/if}

        <!-- Spacer to push actions right -->
        <div class="flex-1"></div>

        <!-- Actions 2×2 grid -->
        <div class="flex shrink-0 gap-1.5 grid grid-cols-2">
            <!-- Top-left: ColumnVisibility in table mode, placeholder in grid mode -->
            {#if viewMode === 'list'}
                <ColumnVisibilityToggle tableRef={assetTableComponent?.getTableRef()} showLabel={true} />
            {:else}
                <div></div>
            {/if}
            <!-- Settings -->
            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                onclick={() => { /* TODO: open asset chart settings modal */ }}
                title="Settings"
            >
                <Settings size={14} />
                <span>{$t('fx.actions.settings')}</span>
            </button>
            <!-- Sync All -->
            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                onclick={handleSyncAsset}
                title="Sync all assets with providers"
            >
                <RotateCw size={14} />
                <span>Sync</span>
            </button>
            <!-- Refresh All -->
            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                onclick={() => fetchAllPriceData()}
                title="Refresh all prices from DB"
            >
                <RefreshCw size={14} />
                <span>Refresh</span>
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
                onclick={loadAssets}
            >
                {$t('common.retry')}
            </button>
        </div>
    {:else if filteredAssets.length === 0}
        <!-- Empty state -->
        <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm p-12 text-center border border-gray-100 dark:border-slate-700">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full mb-4">
                <BarChart3 class="text-green-600 dark:text-green-400" size={32} />
            </div>
            {#if assets.length === 0}
                <h3 class="text-lg font-semibold text-gray-700 dark:text-gray-200 mb-2">{$t('assets.empty.noAssets')}</h3>
                <p class="text-gray-500 dark:text-gray-400 mb-4">{$t('assets.empty.noAssetsDesc')}</p>
                <button
                    class="px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors"
                    onclick={handleAddAsset}
                >
                    <Plus size={16} class="inline mr-1" />
                    {$t('assets.addAsset')}
                </button>
            {:else}
                <h3 class="text-lg font-semibold text-gray-700 dark:text-gray-200 mb-2">{$t('assets.empty.noMatchesTitle')}</h3>
                <p class="text-gray-500 dark:text-gray-400">{$t('assets.empty.noMatchesDesc')}</p>
            {/if}
        </div>
    {:else if viewMode === 'grid'}
        <!-- Grid View -->
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {#each filteredAssets as asset (asset.id)}
                <AssetCard
                    asset={{
                        id: asset.id,
                        display_name: asset.display_name,
                        currency: asset.currency,
                        icon_url: asset.icon_url,
                        asset_type: asset.asset_type,
                        has_provider: asset.has_provider,
                        active: asset.active,
                    }}
                    lastPrice={asset.lastPrice}
                    deltaPercent={asset.deltaPercent}
                    deltaAbs={asset.deltaAbs}
                    chartData={asset.chartData}
                    loading={asset.loadingPrices}
                    onsync={handleSyncAsset}
                    onrefresh={handleRefreshAsset}
                    ondelete={handleDeleteAsset}
                />
            {/each}
        </div>
    {:else}
        <!-- Table View -->
        <AssetTable
            bind:this={assetTableComponent}
            data={tableRows}
            loading={false}
            {visiblePeriods}
            onsync={handleSyncAsset}
            onrefresh={handleRefreshAsset}
            ondelete={handleDeleteAsset}
            onselectionchange={(rows) => { selectedAssetRows = rows; }}
        />
    {/if}
</div>

