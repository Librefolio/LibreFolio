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
    import {zodiosApi, axiosInstance} from '$lib/api';
    import {BarChart3, Check, Plus, RefreshCw, RotateCw, Search, Settings, Trash2, X} from 'lucide-svelte';
    import AssetCard from '$lib/components/assets/AssetCard.svelte';
    import type {AssetRow} from '$lib/components/assets/AssetTable.svelte';
    import AssetTable from '$lib/components/assets/AssetTable.svelte';
    import {fetchCurrentPrices, computeDirection} from '$lib/services/livePriceService';
    import type {LivePriceDirection} from '$lib/services/livePriceService';
    import AssetSyncModal from '$lib/components/assets/AssetSyncModal.svelte';
    import AssetModal from '$lib/components/assets/AssetModal.svelte';
    import {invalidateAfterMutation} from '$lib/stores/reference/assetStore';
    import ViewModeToggle from '$lib/components/ui/ViewModeToggle.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import DataTableToolbar from '$lib/components/table/DataTableToolbar.svelte';
    import DateRangePicker from '$lib/components/ui/date/DateRangePicker.svelte';
    import ChartSettingsModal from '$lib/components/charts/ChartSettingsModal.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import type {ChartSettings} from '$lib/stores/chartSettingsStore.svelte';
    import {getGlobalSettings, getSettingsForPair, getSettingsVersion, setGlobalSettings, setPairSettings} from '$lib/stores/chartSettingsStore.svelte';
    import {CurrencySearchSelect} from '$lib/components/ui/select';
    import {getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import PageToolbar from '$lib/components/ui/toolbar/PageToolbar.svelte';
    import {gotoDateRange} from '$lib/utils/url/dateRangeUrl';
    import {type RenderedSignal, signalFromConfig} from '$lib/charts/signals';
    import {getStart, getEnd, setDateRange, resolveDateSentinel, isMaxSentinel} from '$lib/stores/dateRangeStore.svelte';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import {createPairSlug, ensureFxRangeLoaded, getFxStore} from '$lib/stores/fxStoreRegistry';
    import {getAssetPriceStore, invalidateAssetPriceStore} from '$lib/stores/assetPriceStoreRegistry';
    import {computeDerivedPriceState, computePeriodDelta, DELTA_PERIODS} from '$lib/utils/assetPriceDerived';
    import {processPriceItemsInParallel} from '$lib/workers/priceProcessingPool';
    import type {ProcessedAssetResult} from '$lib/workers/priceProcessing.worker';

    // =========================================================================
    // Types
    // =========================================================================

    interface AssetInfo {
        id: number;
        display_name: string;
        currency: string;
        icon_url?: string | null;
        asset_type?: string | null;
        provider_code?: string | null;
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

    // =========================================================================
    // State
    // =========================================================================

    let assets = $state<AssetState[]>([]);
    let loading = $state(true);
    let refreshing = $state(false);
    let error = $state<string | null>(null);
    let assetTableComponent: AssetTable | undefined = $state(undefined);
    let selectedAssetRows = $state<AssetRow[]>([]);
    /** Set of asset IDs currently syncing (for per-card/row rotating icon) */
    let syncingAssetIds = $state<Set<number>>(new Set());

    /** Live prices from bulk current-price endpoint (asset_id → {value, direction}) */
    let livePriceMap = $state<Map<number, {value: number; direction: LivePriceDirection}>>(new Map());

    // Delete dialog (single)
    let deleteDialogOpen = $state(false);
    let deletingAsset: AssetRow | null = $state(null);
    let deleteLoading = $state(false);

    // Bulk delete confirmation dialog
    let bulkDeleteDialogOpen = $state(false);
    let deletingAssets = $state<AssetRow[]>([]);
    let bulkDeleteResults = $state<{label: string; success: boolean; detail?: string}[]>([]);

    // Sync modal
    let syncModalOpen = $state(false);
    let syncModalAssets = $state<AssetInfo[]>([]);

    // Asset modal (create/edit)
    let assetModalOpen = $state(false);
    let assetModalEditMode = $state(false);
    let assetModalEditData = $state<any>(null);

    // Filters
    let searchText = $state('');
    let filterTypes = $state<Set<string>>(new Set());
    let filterCurrencies = $state<Set<string>>(new Set());
    // Tri-state active filter: two independent toggles for Active / Inactive.
    // Intuitive semantics (both selected OR both deselected = no filter):
    //   - [✓Active ✗Inactive] → only active
    //   - [✗Active ✓Inactive] → only inactive
    //   - [✓Active ✓Inactive] → show all (both)
    //   - [✗Active ✗Inactive] → show all (both)
    // Default: only active (legacy behaviour).
    let filterShowActive = $state(true);
    let filterShowInactive = $state(false);

    // Date range — global store is source of truth; URL seeds only on fresh page load.
    // dateStart/dateEnd are ALWAYS a concrete, resolved date (sentinels resolved immediately)
    // — used everywhere internally (queries, cache, URLs). displayDateStart is the ONLY
    // thing bound to the picker; it shows the literal "min" sentinel (pending label) until
    // the real earliest date is extracted from a backend response (see fetchAllPriceData).
    let dateStart = $state(resolveDateSentinel(getStart()));
    let dateEnd = $state(resolveDateSentinel(getEnd()));
    const initialIsMaxPending = isMaxSentinel(getStart());
    let isMaxPending = $state(initialIsMaxPending);
    // Seeded from the plain `initialIsMaxPending`/`dateStart`'s initial value above (not from
    // the isMaxPending/dateStart $state bindings) to avoid a state_referenced_locally warning —
    // displayDateStart is manually resynced elsewhere and bound bidirectionally to
    // DateRangePicker, so it's intentionally NOT a pure $derived of dateStart/isMaxPending.
    let displayDateStart = $state(initialIsMaxPending ? 'min' : resolveDateSentinel(getStart()));
    let activePreset: any = $state(initialIsMaxPending ? 'MAX' : null);

    /**
     * Sentinel-aware values for building URLs (own history + cross-page nav
     * links). While "All" is the active selection, these stay "min"/"max"
     * (generic) instead of a concrete resolved date, for the lifetime of the
     * selection — not just until the real date is resolved.
     */
    let urlDateStart = $derived(activePreset === 'MAX' ? 'min' : dateStart);
    let urlDateEnd = $derived(activePreset === 'MAX' ? 'max' : dateEnd);
    let syncDateStart = $derived(activePreset === 'MAX' ? 'min' : dateStart);

    /** True when the date range ends today (or later) → show live prices from providers */
    let isHeadToday = $derived(dateEnd >= new Date().toISOString().slice(0, 10));

    // View mode
    let viewMode = $state<'grid' | 'list'>('grid');

    // Grid delta display mode: absolute or percentage (E3)
    let globalViewMode = $state<'percentage' | 'absolute'>('percentage');

    // Asset type → icon PNG filename mapping (used in type filter dropdown)
    const TYPE_ICON_MAP: Record<string, string> = {
        STOCK: 'stock',
        ETF: 'etf',
        BOND: 'bond',
        CRYPTO: 'crypto',
        FUND: 'fund',
        HOLD: 'hold',
        CROWDFUND: 'crowdfunding',
        INDEX: 'index',
        OTHER: 'other',
    };
    const ALL_ASSET_TYPES = ['STOCK', 'ETF', 'BOND', 'CRYPTO', 'FUND', 'HOLD', 'CROWDFUND', 'INDEX', 'OTHER'] as const;

    // Count assets per type (for E5b badge in type filter dropdown)
    let typeCounts = $derived(
        assets.reduce(
            (acc, a) => {
                const t = a.asset_type ?? 'OTHER';
                acc[t] = (acc[t] ?? 0) + 1;
                return acc;
            },
            {} as Record<string, number>,
        ),
    );
    // Only show types that have at least 1 asset
    let availableTypes = $derived(ALL_ASSET_TYPES.filter((t) => (typeCounts[t] ?? 0) > 0));

    // Debounce timer
    let searchTimer: ReturnType<typeof setTimeout> | undefined;

    // Filter bar adaptive layout is now owned by PageToolbar (shared with dashboard/broker-detail)
    // — see the {#snippet filters}/{#snippet actions} below for layoutMode/filtersStacked/
    // showActionLabels usage. Tune live via window.__lfLayouts.assetsList.thresholds.<field>.

    // Type filter dropdown
    let typeFilterOpen = $state(false);
    let typeFilterTriggerEl = $state<HTMLButtonElement | null>(null);

    // Chart settings modal (D4)
    let settingsModalOpen = $state(false);
    let settingsTargetId = $state<string | null>(null);
    let settingsForModal = $derived(settingsTargetId ? getSettingsForPair(`asset-${settingsTargetId}`, 'assets') : getGlobalSettings('assets'));

    // FX pair slugs for cross-domain signal selection (loaded lazily)
    let fxPairSlugs = $state<string[]>([]);

    // =========================================================================
    // Derived
    // =========================================================================

    // Extract unique currencies from all assets
    let configuredCurrencies = $derived([...new Set(assets.map((a) => a.currency))].sort());

    let filteredAssets = $derived(
        assets.filter((a) => {
            // Tri-state active filter: if both toggles match (both on or both off),
            // no filter is applied. Otherwise keep only the state matching the
            // single selected toggle.
            const bothSameState = filterShowActive === filterShowInactive;
            if (!bothSameState) {
                if (filterShowActive && !a.active) return false;
                if (filterShowInactive && a.active) return false;
            }
            if (filterTypes.size > 0 && !filterTypes.has(a.asset_type ?? '')) return false;
            if (filterCurrencies.size > 0 && !filterCurrencies.has(a.currency)) return false;
            if (searchText) {
                const q = searchText.toLowerCase();
                if (!a.display_name.toLowerCase().includes(q)) return false;
            }
            return true;
        }),
    );

    // Which delta periods are visible for the selected date range
    let visiblePeriods = $derived(
        DELTA_PERIODS.filter((p) => {
            const rangeMs = new Date(dateEnd).getTime() - new Date(dateStart).getTime();
            const rangeDays = rangeMs / (1000 * 60 * 60 * 24);
            return rangeDays >= p.days;
        }),
    );

    // Map to AssetRow for table
    let tableRows = $derived<AssetRow[]>(
        filteredAssets.map((a) => ({
            id: a.id,
            display_name: a.display_name,
            currency: a.currency,
            icon_url: a.icon_url,
            asset_type: a.asset_type,
            provider_code: a.provider_code,
            active: a.active,
            lastPrice: a.lastPrice,
            deltaAbs: a.deltaAbs,
            deltaPercent: a.deltaPercent,
            deltas: a.deltas,
        })),
    );

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(async () => {
        await loadAssets();
        // Load FX pair slugs for cross-domain signal selection in settings modal
        loadFxPairSlugs();
    });

    // Live price polling — only active when dateEnd includes today
    $effect(() => {
        if (!isHeadToday || assets.length === 0) {
            livePriceMap = new Map();
            return;
        }
        fetchLivePrices();
        const id = setInterval(fetchLivePrices, 30_000);
        return () => clearInterval(id);
    });

    // Close type filter dropdown on outside click
    $effect(() => {
        if (!typeFilterOpen) return;

        function handleClick(e: MouseEvent) {
            const target = e.target as HTMLElement;
            if (typeFilterTriggerEl?.contains(target)) return;
            if (target.closest?.('[data-type-filter-panel]')) return;
            typeFilterOpen = false;
        }

        window.addEventListener('click', handleClick, true);
        return () => window.removeEventListener('click', handleClick, true);
    });

    // Debounced search
    function handleSearchInput(e: Event) {
        const val = (e.target as HTMLInputElement).value;
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
            searchText = val;
        }, 300);
    }

    // =========================================================================
    // Helpers
    // =========================================================================

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
                quote_base_quantity: item.quote_base_quantity ?? 1,
                provider_code: item.provider_code ?? null,
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

    /**
     * When "All" (MAX) is pending resolution, extract the real earliest date
     * across ALL loaded assets (global minimum) and update dateStart/
     * displayDateStart. The URL is left untouched — it keeps showing the
     * generic "min"/"max" sentinel (set in handleDateRangeChange) so the
     * "All" selection survives reloads/shares instead of freezing to a
     * specific historical date. No-op once already resolved or if no asset
     * has any price data yet.
     */
    function resolveMaxStartFromAssets() {
        if (!isMaxPending) return;
        const firstDates = assets.map((a) => a.chartData?.[0]?.date).filter((d): d is string => !!d);
        if (firstDates.length === 0) return;
        dateStart = firstDates.reduce((min, d) => (d < min ? d : min));
        displayDateStart = dateStart;
        isMaxPending = false;
    }

    /**
     * Counterpart to resolveMaxStartFromAssets(): re-arm "All" resolution
     * before a forced full reload. Once isMaxPending resolves, dateStart
     * freezes at whatever the earliest stored date was AT THAT TIME — a sync
     * "Tutti" that later reaches further into the past would silently not
     * show, because fetchAllPriceData() keeps querying the frozen, narrower
     * dateStart. Widening dateStart back to the anchor and re-arming
     * isMaxPending lets resolveMaxStartFromAssets() pick up the new true
     * earliest date once the fresh (wide) query returns.
     */
    function rearmMaxPendingBeforeReload() {
        if (activePreset !== 'MAX') return;
        isMaxPending = true;
        dateStart = resolveDateSentinel('min');
        displayDateStart = 'min';
    }

    async function fetchAllPriceData() {
        if (assets.length === 0) return;

        // Split into cached (no gaps) and need-fetch (have gaps)
        const cached: Map<number, any[]> = new Map();
        const needFetch: AssetState[] = [];
        for (const asset of assets) {
            const store = getAssetPriceStore(asset.id, asset.currency);
            const gaps = store.getMissingIntervals(dateStart, dateEnd);
            if (gaps.length === 0) {
                const rangeData = store.getRange(dateStart, dateEnd).data;
                cached.set(
                    asset.id,
                    rangeData.map((p) => ({
                        date: p.date,
                        close: p.close,
                        open: p.open,
                        high: p.high,
                        low: p.low,
                        volume: p.volume,
                        currency: p.currency,
                        backward_fill_info: p.backwardFillInfo ? {days_back: p.backwardFillInfo.daysBack} : null,
                    })),
                );
            } else {
                needFetch.push(asset);
            }
        }

        // If all cached — update instantly, no loading indicators
        if (needFetch.length === 0) {
            assets = assets.map((asset) => buildAssetStateFromPrices(asset, cached.get(asset.id) ?? []));
            resolveMaxStartFromAssets();
            return;
        }

        refreshing = true;
        assets = assets.map((a) => ({...a, loadingPrices: needFetch.some((nf) => nf.id === a.id)}));

        try {
            // Bulk query only assets with gaps — SAME single request as before (the
            // backend runs one SQL query for all requested assets; splitting this into
            // several smaller requests would lose that optimization, so it stays as one
            // call). Use axiosInstance directly (bypassing Zodios' automatic response
            // validation) so the raw, not-yet-validated body can be handed to the shared
            // worker pool: validating + computing derived state for every asset in one
            // synchronous main-thread block was what monopolized the thread long enough
            // to delay click/navigation handling on large "ALL date range" loads.
            const queries = needFetch.map((a) => ({
                asset_id: a.id,
                date_range: {start: dateStart, end: dateEnd},
            }));

            const rawResponse = await axiosInstance.post('/api/v1/assets/prices/query', queries);
            const rawItems: unknown[] = rawResponse.data?.items ?? [];

            const {results, invalidItemErrors} = await processPriceItemsInParallel(rawItems);
            if (invalidItemErrors.length > 0) {
                console.error('Some price-query items failed validation:', invalidItemErrors);
            }

            // Populate caches (cheap: just Map.set calls) and build a per-asset lookup
            // of the already-computed derived UI state (last price, deltas, chart data).
            const derivedByAssetId = new Map<number, ProcessedAssetResult>();
            for (const result of results) {
                derivedByAssetId.set(result.assetId, result);
                const asset = needFetch.find((a) => a.id === result.assetId);
                if (asset && result.mappedPoints.length > 0) {
                    const store = getAssetPriceStore(asset.id, asset.currency);
                    store.merge(result.mappedPoints);
                    store.markFetched(dateStart, dateEnd);
                }
            }

            // Merge cached + fresh results
            assets = assets.map((asset) => {
                if (cached.has(asset.id)) {
                    return buildAssetStateFromPrices(asset, cached.get(asset.id) ?? []);
                }
                const processed = derivedByAssetId.get(asset.id);
                if (processed) {
                    return {...asset, ...processed.derived, loadingPrices: false};
                }
                return {...asset, loadingPrices: false, deltas: {}};
            });
            resolveMaxStartFromAssets();
        } catch (e: any) {
            console.error('Failed to fetch prices bulk:', e);
            // For cached assets, still use cached data; for others, clear loading
            assets = assets.map((a) => {
                const cachedPrices = cached.get(a.id);
                if (cachedPrices) return buildAssetStateFromPrices(a, cachedPrices);
                return {...a, loadingPrices: false, deltas: {}};
            });
        } finally {
            refreshing = false;
        }
    }

    function buildAssetStateFromPrices(asset: AssetState, prices: any[]): AssetState {
        // Empty prices: preserve whatever chart/delta data the asset already had (e.g. a
        // stale-but-valid previous fetch) — only reset loadingPrices/deltas, matching the
        // pre-extraction behavior exactly (do NOT wipe lastPrice/chartData to null/empty).
        if (prices.length === 0) {
            return {...asset, loadingPrices: false, deltas: {}};
        }
        return {
            ...asset,
            ...computeDerivedPriceState(prices),
            loadingPrices: false,
        };
    }

    function handleDateRangeChange(newStart: string, newEnd: string) {
        isMaxPending = isMaxSentinel(newStart);
        dateStart = resolveDateSentinel(newStart);
        dateEnd = resolveDateSentinel(newEnd);
        displayDateStart = isMaxPending ? 'min' : dateStart;
        setDateRange(newStart, newEnd);
        // Sync URL for shareability + navigationStore tracking. Keep the generic
        // "min"/"max" sentinel when "All" is selected (instead of a concrete
        // resolved date) so the URL stays meaningful across reloads/shares and
        // the "All" badge doesn't look stuck on a specific historical date.
        gotoDateRange(newStart, newEnd);
        fetchAllPriceData();
    }

    /** Fetch live current prices for all assets (fire-and-forget, non-blocking). */
    async function fetchLivePrices() {
        if (assets.length === 0) return;
        try {
            const ids = assets.map((a) => a.id);
            const results = await fetchCurrentPrices(ids);
            const newMap = new Map<number, {value: number; direction: LivePriceDirection}>();
            for (const r of results) {
                if (r.value != null) {
                    const prev = livePriceMap.get(r.assetId)?.value ?? null;
                    newMap.set(r.assetId, {
                        value: r.value,
                        direction: computeDirection(r.value, prev),
                    });
                }
            }
            livePriceMap = newMap;
        } catch (e: any) {
            console.warn('[Assets] fetchLivePrices error (non-critical):', e?.message);
        }
    }

    // =========================================================================
    // Actions
    // =========================================================================

    function handleAddAsset() {
        assetModalEditMode = false;
        assetModalEditData = null;
        assetModalOpen = true;
    }

    function handleEditAsset(asset: any) {
        assetModalEditMode = true;
        assetModalEditData = {
            id: asset.id,
            display_name: asset.display_name,
            currency: asset.currency,
            asset_type: asset.asset_type ?? 'STOCK',
            icon_url: asset.icon_url,
            quote_base_quantity: asset.quote_base_quantity ?? 1,
            active: asset.active,
            provider_code: asset.provider_code,
        };
        assetModalOpen = true;
    }

    async function handleSyncAsset(asset: any) {
        syncingAssetIds = new Set([...syncingAssetIds, asset.id]);
        try {
            const response = await zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post([
                {
                    asset_id: asset.id,
                    date_range: {start: syncDateStart, end: dateEnd},
                },
            ]);
            const r = (response as any)?.results?.[0];
            if (r && (!r.errors || r.errors.length === 0)) {
                const fetched = r.points_fetched ?? 0;
                const inserted = r.inserted_count ?? 0;
                const updated = r.updated_count ?? 0;
                const changed = inserted + updated;
                toasts.success(
                    $t('assets.sync.toastOk', {
                        values: {name: asset.display_name, fetched, changed},
                    }),
                );
            } else {
                toasts.error(
                    $t('assets.sync.toastFailed', {
                        values: {name: asset.display_name},
                    }) + (r?.errors?.[0] ? ': ' + r.errors[0] : ''),
                );
            }
            invalidateAssetPriceStore(asset.id);
            rearmMaxPendingBeforeReload();
            await fetchAllPriceData();
        } catch (e: any) {
            toasts.error(
                $t('assets.sync.toastFailed', {
                    values: {name: asset.display_name},
                }) +
                    ': ' +
                    (e?.message || 'unknown'),
            );
        } finally {
            syncingAssetIds = new Set([...syncingAssetIds].filter((id) => id !== asset.id));
        }
    }

    /** Open sync modal for all assets that have a provider */
    function handleSyncAllAssets() {
        syncModalAssets = assets.filter((a) => !!a.provider_code);
        syncModalOpen = true;
    }

    async function handleRefreshAsset(asset: any) {
        invalidateAssetPriceStore(asset.id);
        rearmMaxPendingBeforeReload();
        await fetchAllPriceData();
    }

    function handleDeleteAsset(asset: any) {
        deletingAsset = asset;
        deleteDialogOpen = true;
    }

    async function confirmDeleteAsset() {
        if (!deletingAsset) return;
        deleteLoading = true;
        try {
            const response = await zodiosApi.delete_assets_bulk_api_v1_assets_delete(undefined, {
                queries: {asset_ids: [deletingAsset.id]},
            });
            const r = (response as any)?.results?.[0];
            if (r?.success) {
                // Evict from the shared cache so other pages (transactions
                // cell, LiveTicker) drop the deleted asset without a reload.
                invalidateAfterMutation(deletingAsset.id);
                assets = assets.filter((a) => a.id !== deletingAsset!.id);
                toasts.success($t('assets.delete.toastOk', {values: {name: deletingAsset!.display_name}}));
            } else if (r?.error_code === 'HAS_TRANSACTIONS') {
                toasts.error($t('assets.delete.hasTransactions', {values: {name: deletingAsset!.display_name}}));
            } else {
                toasts.error(r?.message || $t('assets.delete.toastFailed', {values: {name: deletingAsset!.display_name}}));
            }
        } catch (e: any) {
            toasts.error($t('assets.delete.toastFailed', {values: {name: deletingAsset!.display_name}}));
        } finally {
            deleteLoading = false;
            deleteDialogOpen = false;
            deletingAsset = null;
        }
    }

    // =========================================================================
    // Bulk Actions (table selection)
    // =========================================================================

    function handleBulkSyncAssets() {
        syncModalAssets = selectedAssetRows.filter((r) => !!r.provider_code);
        syncModalOpen = true;
    }

    async function handleBulkRefreshAssets() {
        for (const a of assets) invalidateAssetPriceStore(a.id);
        rearmMaxPendingBeforeReload();
        await fetchAllPriceData();
        assetTableComponent?.getTableRef()?.clearSelection();
        selectedAssetRows = [];
    }

    function handleBulkDeleteAssets() {
        deletingAssets = [...selectedAssetRows];
        bulkDeleteDialogOpen = true;
    }

    async function confirmBulkDeleteAssets() {
        const ids = deletingAssets.map((r) => r.id);
        if (ids.length === 0) return;
        try {
            const response = await zodiosApi.delete_assets_bulk_api_v1_assets_delete(undefined, {
                queries: {asset_ids: ids},
            });
            const res = response as any;
            const succeeded = res.results?.filter((r: any) => r.success).map((r: any) => r.asset_id) ?? [];
            // Evict each successfully-deleted asset from the shared cache.
            if (succeeded.length > 0) invalidateAfterMutation(succeeded);
            assets = assets.filter((a) => !succeeded.includes(a.id));

            // Populate results for the ConfirmModal
            bulkDeleteResults = (res.results ?? []).map((r: any) => ({
                label: r.display_name || `Asset #${r.asset_id}`,
                success: r.success,
                detail: r.success ? $t('assets.delete.resultDeleted') : r.error_code === 'HAS_TRANSACTIONS' ? $t('assets.delete.resultHasTransactions') : r.message || 'Error',
            }));
        } catch (e: any) {
            toasts.error('Delete failed: ' + (e?.message || 'unknown'));
            bulkDeleteDialogOpen = false;
            deletingAssets = [];
            assetTableComponent?.getTableRef()?.clearSelection();
            selectedAssetRows = [];
        }
    }

    function closeBulkDeleteDialog() {
        // Show summary toast on close
        const successes = bulkDeleteResults.filter((r) => r.success).length;
        const failures = bulkDeleteResults.filter((r) => !r.success).length;
        if (successes > 0) {
            toasts.success($t('assets.delete.bulkOk', {values: {count: successes}}));
        }
        if (failures > 0) {
            toasts.warning($t('assets.delete.bulkPartial', {values: {failed: failures}}));
        }
        bulkDeleteDialogOpen = false;
        bulkDeleteResults = [];
        deletingAssets = [];
        assetTableComponent?.getTableRef()?.clearSelection();
        selectedAssetRows = [];
    }

    function handleGlobalSettings() {
        settingsTargetId = null;
        settingsModalOpen = true;
    }

    function handleSettingsSave(s: ChartSettings) {
        if (settingsTargetId) {
            setPairSettings(`asset-${settingsTargetId}`, s);
        } else {
            setGlobalSettings(s, 'assets');
        }
    }

    function handleCardSettings(asset: {id: number}) {
        settingsTargetId = String(asset.id);
        settingsModalOpen = true;
    }

    /** Load FX pair slugs and their rate data for cross-domain signal resolution */
    async function loadFxPairSlugs() {
        try {
            const response = await zodiosApi.list_routes_api_v1_fx_providers_routes_get();
            const items = (response as any)?.items || [];
            const slugSet = new Set<string>();
            for (const item of items) {
                slugSet.add(createPairSlug(item.base, item.quote));
            }
            fxPairSlugs = [...slugSet].sort();
            // Load FX rate data into stores for signal rendering on cards + preview
            await loadFxRateData();
        } catch {
            // Non-critical — FX pair dropdown will just be empty
        }
    }

    /** Fetch FX rate data for all configured pairs (populates FxStores) */
    async function loadFxRateData() {
        const promises = fxPairSlugs.map(async (slug) => {
            await ensureFxRangeLoaded(slug, dateStart, dateEnd);
        });
        await Promise.allSettled(promises);
    }

    /** Build pairsDataMap from FX stores for ChartSettingsModal preview */
    function buildPairsDataMap(): Record<string, LineDataPoint[]> {
        const entries: Array<[string, LineDataPoint[]]> = [];
        for (const slug of fxPairSlugs) {
            try {
                const store = getFxStore(slug);
                const data = store.getAllSorted();
                if (data.length === 0) continue;
                entries.push([slug, data.map((d) => ({date: d.date, value: d.rate, staleDays: d.backwardFillInfo?.daysBack ?? 0}))]);
            } catch {
                /* skip */
            }
        }
        return Object.fromEntries(entries);
    }

    /**
     * Render overlay signals for an asset card. Called by AssetCard reactively
     * whenever cardViewMode changes. Receives absolute chart data.
     */
    function getRenderedSignals(assetId: number, absoluteData: LineDataPoint[], vm: 'absolute' | 'percentage'): RenderedSignal[] {
        void getSettingsVersion();
        const settings = getSettingsForPair(`asset-${assetId}`, 'assets');
        if (!settings.signals.length) return [];
        const rendered: RenderedSignal[] = [];
        for (const cfg of settings.signals) {
            const instance = signalFromConfig(cfg);
            if (!instance) continue;

            // Resolve FxPairSignal data from FX stores
            if (cfg.signalType === 'fx-pair') {
                const pairSlug = String(cfg.params.pairSlug || '');
                if (!pairSlug) continue;
                try {
                    const store = getFxStore(pairSlug);
                    const storeData = store.getAllSorted();
                    if (storeData.length === 0) continue;
                    instance.params._resolvedData = storeData.map((d) => ({
                        date: d.date,
                        value: d.rate,
                    }));
                } catch {
                    continue;
                }
            }

            // Resolve AssetComparisonSignal data from local assets array
            if (cfg.signalType === 'asset-comparison') {
                const targetId = Number(cfg.params.assetId);
                if (!targetId || targetId === assetId) continue;
                const targetAsset = assets.find((a) => a.id === targetId);
                if (!targetAsset?.chartData?.length) continue;
                instance.params._resolvedData = targetAsset.chartData;
                instance.params._assetDisplayName = targetAsset.display_name;
            }

            const results = instance.renderMulti(absoluteData, vm);
            for (const result of results) {
                if (result.data.length > 0) rendered.push(result);
            }
        }
        return rendered;
    }

    function clearFilters() {
        searchText = '';
        filterTypes = new Set();
        filterCurrencies = new Set();
    }

    let hasActiveFilters = $derived(!!searchText || filterTypes.size > 0 || filterCurrencies.size > 0);
</script>

<div class="space-y-6" data-testid="assets-page">
    <!-- Header: Title left, ViewModeToggle + Add Asset right -->
    <div class="flex items-center justify-between">
        <div>
            <h2 class="text-lg font-semibold text-gray-700 dark:text-gray-200 flex items-center gap-2">
                {$t('common.assets')}
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
                        {id: 'sync', icon: RotateCw, label: () => $t('common.sync'), onClick: () => handleBulkSyncAssets()},
                        {id: 'refresh', icon: RefreshCw, label: () => $t('common.refresh'), onClick: () => handleBulkRefreshAssets()},
                        {id: 'delete', icon: Trash2, label: () => $t('common.delete'), variant: 'danger', onClick: () => handleBulkDeleteAssets()},
                    ]}
                    onClearSelection={() => {
                        assetTableComponent?.getTableRef()?.clearSelection();
                        selectedAssetRows = [];
                    }}
                />
            {/if}
            <!-- Currency filter badges — Opzione γ (D10+D11) -->
            {#if filterCurrencies.size > 0 && selectedAssetRows.length === 0}
                <div class="flex items-center gap-1.5 flex-wrap">
                    {#each [...filterCurrencies] as currency}
                        <span
                            class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium
                                     bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300
                                     border border-amber-200 dark:border-amber-700 rounded-full"
                        >
                            {getCurrencyInfo(currency).flag_emoji}
                            {currency}
                            <button
                                class="hover:text-red-500 transition-colors"
                                onclick={(e) => {
                                    e.stopPropagation();
                                    filterCurrencies = new Set([...filterCurrencies].filter((c) => c !== currency));
                                }}>×</button
                            >
                        </span>
                    {/each}
                </div>
            {/if}
            <ViewModeToggle bind:mode={viewMode} storageKey="assetsViewMode" />
            <button class="flex items-center gap-1.5 px-3 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors whitespace-nowrap" data-testid="assets-add-button" onclick={handleAddAsset}>
                <Plus size={16} />
                {$t('assets.modal.title')}
            </button>
        </div>
    </div>

    <!-- Filter Bar — shared PageToolbar (same component as dashboard/broker-detail), so
         responsive/wrap fixes made there (jolly badge shedding, currency/broker no-wrap, ...)
         auto-propagate here instead of being hand-copied per page.
         oneRow:       [ datepicker | search active type currency × | 2×2 ]
         denseRow:     [ datepicker                     | 2×2 ]
                      [ search active type currency ×  |     ]
         stackFilters: [ datepicker                     | col  ]
                      [ search active type currency ×  | btns ]
         mobile:       [ datepicker ][ search ][ active type × ][ currency ][ btns ] -->
    <PageToolbar thresholds={{oneRow: 1340, denseRow: 1060, stackFilters: 500, actionsColumn: 410, iconOnly: 330, labelHide: 330}} testId="assets-controls" filterRowTestId="assets-filter-bar" layoutDebugName="assetsList">
        {#snippet filters({layoutMode, filtersStacked})}
            <!-- DateRangePicker -->
            <div class="flex flex-1 self-stretch min-w-0" data-testid="assets-date-range">
                <DateRangePicker bind:activePreset bind:end={dateEnd} bind:start={displayDateStart} compact={true} align="start" {layoutMode} debugName="assetsList" onchange={handleDateRangeChange} />
            </div>

            <!-- Filters 2×2 block (denseRow+stackFilters) / inline (oneRow) / stacked (mobile+iconOnly) -->
            <div class="flex gap-2 {layoutMode === 'oneRow' ? 'flex-row items-center flex-wrap' : filtersStacked ? 'flex-col items-center' : 'flex-col'}">
                <!-- Row 1: Search + Active -->
                <div class="flex items-center gap-2">
                    <!-- Search -->
                    <div class="relative w-44">
                        <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
                        <input
                            class="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 focus:ring-1 focus:ring-libre-green focus:border-libre-green"
                            data-testid="assets-search-input"
                            oninput={handleSearchInput}
                            placeholder={$t('assets.searchPlaceholder')}
                            type="text"
                            value={searchText}
                        />
                    </div>

                    <!-- Tri-state Active/Inactive segmented toggle (I-bis #20).
                         Both pressed OR both unpressed → show all (None filter server-side,
                         no filter client-side). Only-one pressed → filter to that state. -->
                    <div class="inline-flex rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden" data-testid="assets-active-filter">
                        <button
                            type="button"
                            class="px-3 py-1.5 text-xs font-medium border-r border-gray-200 dark:border-slate-600 transition-colors whitespace-nowrap
                                   {filterShowActive ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-700 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-600'}"
                            data-testid="assets-active-toggle"
                            aria-pressed={filterShowActive}
                            onclick={() => (filterShowActive = !filterShowActive)}
                        >
                            {$t('assets.showActive')}
                        </button>
                        <button
                            type="button"
                            class="px-3 py-1.5 text-xs font-medium transition-colors whitespace-nowrap
                                   {filterShowInactive ? 'bg-amber-500 text-white' : 'bg-white dark:bg-slate-700 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-600'}"
                            data-testid="assets-inactive-toggle"
                            aria-pressed={filterShowInactive}
                            onclick={() => (filterShowInactive = !filterShowInactive)}
                        >
                            {$t('assets.showInactive')}
                        </button>
                    </div>
                </div>

                <!-- Row 2: Type multi-select + Currency dropdown + Reset -->
                <div class="flex items-center gap-2">
                    <!-- Type multi-checkbox dropdown (D9) -->
                    <div class="relative">
                        <button
                            bind:this={typeFilterTriggerEl}
                            class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors whitespace-nowrap
                                   {filterTypes.size > 0
                                ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-700'
                                : 'bg-white dark:bg-slate-700 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-600'}"
                            data-testid="assets-type-filter"
                            onclick={() => {
                                typeFilterOpen = !typeFilterOpen;
                            }}
                        >
                            {#if filterTypes.size > 0}
                                {$t('common.type')} ({filterTypes.size})
                            {:else}
                                {$t('assets.allTypes')}
                            {/if}
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path d="M19 9l-7 7-7-7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
                            </svg>
                        </button>

                        {#if typeFilterOpen}
                            <!-- svelte-ignore a11y_interactive_supports_focus -->
                            <div
                                class="absolute z-50 mt-1 w-56 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg overflow-hidden"
                                onclick={(e) => e.stopPropagation()}
                                onkeydown={(e) => {
                                    if (e.key === 'Escape') typeFilterOpen = false;
                                }}
                                role="listbox"
                                tabindex="0"
                                data-type-filter-panel
                            >
                                <!-- Select All / Clear All buttons -->
                                <div class="flex gap-2 px-2.5 py-2 border-b border-gray-100 dark:border-slate-700">
                                    <button
                                        type="button"
                                        class="flex-1 px-2 py-1 text-[11px] font-medium border border-gray-200 dark:border-slate-600 rounded bg-gray-50 dark:bg-slate-900 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-900 dark:hover:text-gray-200 transition-colors"
                                        onclick={() => {
                                            filterTypes = new Set(availableTypes);
                                        }}>{$t('common.selectAll')}</button
                                    >
                                    <button
                                        type="button"
                                        class="flex-1 px-2 py-1 text-[11px] font-medium border border-gray-200 dark:border-slate-600 rounded bg-gray-50 dark:bg-slate-900 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-900 dark:hover:text-gray-200 transition-colors"
                                        onclick={() => {
                                            filterTypes = new Set();
                                        }}>{$t('common.clearAll')}</button
                                    >
                                </div>
                                <!-- Option list -->
                                <div class="max-h-52 overflow-y-auto border border-gray-100 dark:border-slate-700 mx-2.5 my-2 rounded-md">
                                    {#each availableTypes as typeVal}
                                        <button
                                            type="button"
                                            class="flex items-center gap-2 w-full px-2 py-1.5 text-left text-[13px] text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors cursor-pointer"
                                            onclick={() => {
                                                const next = new Set(filterTypes);
                                                if (next.has(typeVal)) next.delete(typeVal);
                                                else next.add(typeVal);
                                                filterTypes = next;
                                            }}
                                        >
                                            <span
                                                class="flex items-center justify-center w-4 h-4 rounded-sm border transition-colors shrink-0
                                                         {filterTypes.has(typeVal) ? 'bg-libre-green border-libre-green text-white dark:bg-emerald-400 dark:border-emerald-400 dark:text-slate-900' : 'bg-white dark:bg-slate-900 border-gray-300 dark:border-slate-500'}"
                                            >
                                                {#if filterTypes.has(typeVal)}
                                                    <Check size={12} />
                                                {/if}
                                            </span>
                                            <img src="/icons/asset-types/{TYPE_ICON_MAP[typeVal] ?? 'other'}.png" alt="" class="w-4 h-4 object-contain shrink-0" />
                                            <span class="flex-1">{$t(`assets.types.${typeVal}`) || typeVal}</span>
                                            <span class="text-[10px] font-mono text-gray-400 dark:text-gray-500 tabular-nums">{typeCounts[typeVal] ?? 0}</span>
                                        </button>
                                    {/each}
                                </div>
                            </div>
                        {/if}
                    </div>

                    <!-- Currency Filter (D10 — CurrencySearchSelect, adds to Set) -->
                    <div class="w-36">
                        <CurrencySearchSelect
                            allowedCurrencies={configuredCurrencies}
                            includeAll={true}
                            maxVisibleItems={6}
                            onchange={(v) => {
                                if (v && !filterCurrencies.has(v)) {
                                    filterCurrencies = new Set([...filterCurrencies, v]);
                                }
                            }}
                            placeholder={$t('common.allCurrencies')}
                            value=""
                        />
                    </div>

                    <!-- Reset filters -->
                    {#if hasActiveFilters}
                        <button class="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 hover:text-red-500 dark:text-gray-400 dark:hover:text-red-400 transition-colors" onclick={clearFilters} title={$t('fx.filter.resetFilters')}>
                            <X size={16} />
                        </button>
                    {/if}
                </div>
            </div>
        {/snippet}

        {#snippet actions({showActionLabels})}
            <!-- Top-left: ColumnVisibility in table mode, Abs/% toggle in grid mode -->
            {#if viewMode === 'list'}
                <ColumnVisibilityToggle tableRef={assetTableComponent?.getTableRef()} showLabel={showActionLabels} />
            {:else}
                <div class="flex rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
                    <button
                        class="flex-1 px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {globalViewMode === 'absolute' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                        onclick={() => {
                            globalViewMode = 'absolute';
                        }}
                        >Abs
                    </button>
                    <button
                        class="flex-1 px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {globalViewMode === 'percentage' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                        onclick={() => {
                            globalViewMode = 'percentage';
                        }}
                        >%
                    </button>
                </div>
            {/if}
            <!-- Settings -->
            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                onclick={handleGlobalSettings}
            >
                <Settings size={14} />
                {#if showActionLabels}<span>{$t('sharedResource.settings')}</span>{/if}
            </button>
            <!-- Sync All -->
            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                onclick={handleSyncAllAssets}
            >
                <RotateCw size={14} />
                {#if showActionLabels}<span>{$t('sharedResource.syncAll')}</span>{/if}
            </button>
            <!-- Refresh All -->
            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                onclick={() => {
                    for (const a of assets) invalidateAssetPriceStore(a.id);
                    rearmMaxPendingBeforeReload();
                    fetchAllPriceData();
                }}
            >
                <RefreshCw class={refreshing ? 'animate-spin' : ''} size={14} />
                {#if showActionLabels}<span>{$t('sharedResource.refreshAll')}</span>{/if}
            </button>
        {/snippet}
    </PageToolbar>

    <!-- Content -->
    {#if loading}
        <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm p-12 text-center border border-gray-100 dark:border-slate-700">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-libre-green/10 rounded-full mb-4">
                <RefreshCw class="text-libre-green animate-spin" size={32} />
            </div>
            <p class="text-gray-500 dark:text-gray-400">{$t('common.loading')}</p>
        </div>
    {:else if error}
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center">
            <p class="text-red-600 dark:text-red-400">{error}</p>
            <button class="mt-3 px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors" onclick={loadAssets}>
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
                <button class="px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors" onclick={handleAddAsset}>
                    <Plus size={16} class="inline mr-1" />
                    {$t('assets.modal.title')}
                </button>
            {:else}
                <h3 class="text-lg font-semibold text-gray-700 dark:text-gray-200 mb-2">{$t('common.noMatchesTitle')}</h3>
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
                        provider_code: asset.provider_code,
                        active: asset.active,
                    }}
                    livePrice={livePriceMap.get(asset.id)?.value ?? asset.lastPrice ?? null}
                    livePriceDirection={livePriceMap.get(asset.id)?.direction ?? 'neutral'}
                    deltaPercent={asset.deltaPercent}
                    deltaAbs={asset.deltaAbs}
                    dateStart={urlDateStart}
                    dateEnd={urlDateEnd}
                    chartSettings={getSettingsForPair(`asset-${asset.id}`, 'assets')}
                    renderSignals={(chartData, vm) => getRenderedSignals(asset.id, chartData, vm)}
                    chartData={asset.chartData}
                    loading={asset.loadingPrices}
                    syncing={syncingAssetIds.has(asset.id)}
                    onsync={handleSyncAsset}
                    onrefresh={handleRefreshAsset}
                    ondelete={handleDeleteAsset}
                    onsettings={handleCardSettings}
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
            {livePriceMap}
            dateStart={urlDateStart}
            dateEnd={urlDateEnd}
            onsync={handleSyncAsset}
            onrefresh={handleRefreshAsset}
            ondelete={handleDeleteAsset}
            onselectionchange={(rows) => {
                selectedAssetRows = rows;
            }}
        />
    {/if}
</div>

<!-- Chart Settings Modal (D4) -->
<ChartSettingsModal
    open={settingsModalOpen}
    mode={settingsTargetId ? 'pair' : 'global'}
    onclose={() => {
        settingsModalOpen = false;
        settingsTargetId = null;
    }}
    onsave={handleSettingsSave}
    settings={settingsForModal}
    pairData={settingsTargetId ? assets.find((a) => a.id === Number(settingsTargetId))?.chartData : undefined}
    availablePairs={fxPairSlugs}
    availableAssets={assets.map((a) => ({id: a.id, display_name: a.display_name, icon_url: a.icon_url, asset_type: a.asset_type}))}
    assetsDataMap={Object.fromEntries(assets.filter((a) => a.chartData.length > 0).map((a) => [String(a.id), a.chartData]))}
    pairsDataMap={buildPairsDataMap()}
/>

<!-- Delete Asset Confirm Dialog (single) -->
<ConfirmModal
    confirmText={$t('common.delete')}
    danger={true}
    description={$t('assets.delete.confirmWarning')}
    message={$t('assets.delete.confirmQuestion', {values: {name: deletingAsset?.display_name ?? ''}})}
    onCancel={() => {
        deleteDialogOpen = false;
        deletingAsset = null;
    }}
    onConfirm={confirmDeleteAsset}
    open={deleteDialogOpen}
    title={$t('common.confirmDelete')}
/>

<!-- Bulk Delete Confirm Dialog -->
<ConfirmModal
    confirmText={$t('common.delete')}
    danger={true}
    items={deletingAssets.map((a) => a.display_name)}
    itemsLabel={`${deletingAssets.length} assets`}
    message={$t('assets.delete.bulkConfirmMessage', {values: {count: deletingAssets.length}})}
    onCancel={closeBulkDeleteDialog}
    onConfirm={confirmBulkDeleteAssets}
    open={bulkDeleteDialogOpen}
    results={bulkDeleteResults}
    title={$t('common.confirmDelete')}
/>

<!-- Asset Sync Modal -->
<AssetSyncModal
    assets={syncModalAssets}
    bind:open={syncModalOpen}
    {dateEnd}
    dateStart={syncDateStart}
    onclose={() => {
        syncModalOpen = false;
    }}
    onsynced={() => {
        for (const a of assets) invalidateAssetPriceStore(a.id);
        rearmMaxPendingBeforeReload();
        fetchAllPriceData();
    }}
/>

<!-- Asset Create/Edit Modal -->
<AssetModal
    bind:open={assetModalOpen}
    editMode={assetModalEditMode}
    editData={assetModalEditData}
    oncreated={async (assetId) => {
        await loadAssets();
        // Auto-sync the newly created asset to fetch initial price data
        const newAsset = assets.find((a) => a.id === assetId);
        if (newAsset?.provider_code) {
            await handleSyncAsset(newAsset);
        }
    }}
    onupdated={() => loadAssets()}
    onclose={() => {
        assetModalOpen = false;
    }}
/>
