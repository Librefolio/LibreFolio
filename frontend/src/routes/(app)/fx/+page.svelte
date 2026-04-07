<script lang="ts">
    /**
     * FX Rates List Page
     *
     * Displays all configured FX pairs as cards with mini charts.
     * Features: currency filter (SearchSelect), unified date range picker with presets,
     * global abs/% slider toggle, Sync All, Refresh All, Add Pair.
     */
    import {onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {get} from 'svelte/store';
    import {zodiosApi} from '$lib/api';
    import {ArrowLeftRight, Coins, Plus, RefreshCw, RotateCw, Settings, Trash2, X} from 'lucide-svelte';
    import FxCard from '$lib/components/fx/FxCard.svelte';
    import type {FxRow} from '$lib/components/fx/FxTable.svelte';
    import FxTable from '$lib/components/fx/FxTable.svelte';
    import FxPairAddModal from '$lib/components/fx/FxPairAddModal.svelte';
    import FxSyncModal from '$lib/components/fx/FxSyncModal.svelte';
    import ChartSettingsModal from '$lib/components/charts/ChartSettingsModal.svelte';
    import {ConfirmModal} from '$lib/components/table';
    import DateRangePicker from '$lib/components/ui/DateRangePicker.svelte';
    import ViewModeToggle from '$lib/components/ui/ViewModeToggle.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import DataTableToolbar from '$lib/components/table/DataTableToolbar.svelte';
    import {CurrencySearchSelect} from '$lib/components/ui/select';
    import {type ChartSettings, getGlobalSettings, getSettingsForPair, getSettingsVersion, setGlobalSettings, setPairSettings,} from '$lib/stores/chartSettingsStore.svelte';
    import {type RenderedSignal, signalFromConfig,} from '$lib/charts/signals';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import {apiResultToFxDataPoint, createPairSlug, type FxDataPoint, type FxPairConfig, getFxStore, invalidateAllFxStores, removeFxStore} from '$lib/stores/fxStoreRegistry';
    import {isCardInverted} from '$lib/stores/fxCardInversionStore';
    import {toasts} from '$lib/stores/toastStore.svelte';
    import {getCurrencyGraph} from '$lib/stores/currencyGraphStore';
    import {getCurrencyInfo} from '$lib/stores/currencyStore';
    import {formatProviderText, formatSyncDetail} from '$lib/utils/providerHelpers';
    import {createResponsiveLayout} from '$lib/utils/responsiveLayout.svelte';

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
    let dateStart = $state((() => {
        const d = new Date();
        d.setMonth(d.getMonth() - 3);
        return d.toISOString().slice(0, 10);
    })());
    let dateEnd = $state(new Date().toISOString().slice(0, 10));
    let activePreset: any = $state('3M');
    let globalViewMode = $state<'absolute' | 'percentage'>('absolute');
    let refreshing = $state(false);

    // View mode (grid/list)
    let viewMode = $state<'grid' | 'list'>('grid');
    let fxTableComponent: FxTable | undefined = $state(undefined);
    let selectedFxRows = $state<FxRow[]>([]);
    let syncModalPairs = $state<string[]>([]);


    // Delete (single)
    let deleteDialogOpen = $state(false);
    let deletingPair = $state<{ base: string; quote: string; slug: string } | null>(null);
    let deleteLoading = $state(false);

    // Delete (bulk)
    let bulkDeleteDialogOpen = $state(false);
    let deletingPairs = $state<Array<{ base: string; quote: string; slug: string }>>([]);
    let bulkDeleteLoading = $state(false);
    let bulkFxDeleteResults = $state<{ label: string; success: boolean; detail?: string }[]>([]);

    // Modals
    let addModalOpen = $state(false);
    let syncModalOpen = $state(false);
    let settingsModalOpen = $state(false);
    /** Slug of the pair currently being configured via per-card ⚙️ (null = global) */
    let settingsTargetSlug = $state<string | null>(null);
    /** Settings to pass to the modal (global or pair-specific) */
    let settingsForModal = $derived(
        settingsTargetSlug ? getSettingsForPair(settingsTargetSlug, 'fx') : getGlobalSettings('fx')
    );

    // Asset list for cross-domain signal selection (loaded lazily)
    let availableAssetsList = $state<Array<{id: number, display_name: string, icon_url?: string | null, asset_type?: string | null}>>([]);

    // Filter bar adaptive layout (shared helper)
    let filterBarRef = $state<HTMLDivElement | null>(null);
    const fxLayout = createResponsiveLayout({wide: 1030, tablet: 700, tabletS: 530, labelHide: 460});
    let layoutMode = $derived(fxLayout.layoutMode);
    let showActionLabels = $derived(fxLayout.showActionLabels);

    // =========================================================================
    // Derived
    // =========================================================================

    // Delta periods for table columns
    const DELTA_PERIODS = [
        {key: '1W', days: 7},
        {key: '1M', days: 30},
        {key: '3M', days: 91},
        {key: '6M', days: 182},
        {key: '1Y', days: 365},
        {key: '2Y', days: 730},
        {key: '3Y', days: 1095},
        {key: '5Y', days: 1825},
    ] as const;

    // Which delta periods are visible for the selected date range
    let visiblePeriods = $derived(
        DELTA_PERIODS.filter(p => {
            const rangeMs = new Date(dateEnd).getTime() - new Date(dateStart).getTime();
            const rangeDays = rangeMs / (1000 * 60 * 60 * 24);
            return rangeDays >= p.days;
        })
    );

    function computePeriodDelta(data: FxDataPoint[], periodDays: number, inverted: boolean): number | null {
        if (data.length < 2) return null;
        const lastPoint = data[data.length - 1];
        const targetDate = new Date(lastPoint.date);
        targetDate.setDate(targetDate.getDate() - periodDays);
        const targetStr = targetDate.toISOString().slice(0, 10);
        // Find closest point at or before target date (backward-fill)
        let refPoint: FxDataPoint | null = null;
        for (let i = data.length - 1; i >= 0; i--) {
            if (data[i].date <= targetStr) {
                refPoint = data[i];
                break;
            }
        }
        if (!refPoint || refPoint.rate === 0 || lastPoint.rate === 0) return null;
        const refVal = inverted ? 1 / refPoint.rate : refPoint.rate;
        const lastVal = inverted ? 1 / lastPoint.rate : lastPoint.rate;
        return ((lastVal - refVal) / refVal) * 100;
    }

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

    // Map to FxRow for table view
    let fxTableRows = $derived<FxRow[]>(filteredPairs.map(p => {
        const inv = isCardInverted(p.config.slug);
        const deltas: Record<string, number | null> = {};
        for (const period of visiblePeriods) {
            deltas[period.key] = computePeriodDelta(p.data, period.days, inv);
        }
        return {
            slug: p.config.slug,
            base: p.config.base,
            quote: p.config.quote,
            data: p.data,
            manualOnly: p.config.providers.length === 1 && p.config.providers[0].providerCode === 'MANUAL',
            providers: p.config.providers,
            deltas,
        };
    }));

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(async () => {
        // Preload currency graph so provider icons are cached before FxTable renders (E1c fix)
        getCurrencyGraph();
        await loadPairSources();
        // Load asset list for cross-domain signal selection
        loadAssetList();
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
    // ResizeObserver for adaptive filter bar layout
    $effect(() => {
        const el = filterBarRef;
        if (!el) return;
        fxLayout.attach(el);
        return () => fxLayout.detach();
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

    function handleCardSettings(detail: { slug: string }) {
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
            setGlobalSettings(s, 'fx');
        }
    }

    /** Load asset list for signal settings — lightweight, no chart data needed */
    async function loadAssetList() {
        try {
            const response = await zodiosApi.list_assets_api_v1_assets_query_get({ queries: {} });
            const items = response as any[];
            availableAssetsList = items.map((a: any) => ({
                id: a.id,
                display_name: a.display_name,
                icon_url: a.icon_url ?? null,
                asset_type: a.asset_type ?? null,
            }));
        } catch {
            // Non-critical — asset dropdown will just be empty
        }
    }

    /**
     * Render overlay signals for a pair. Called by FxCard reactively whenever
     * cardViewMode or inverted changes. Receives absolute chart data (post-inversion).
     */
    function getRenderedSignals(slug: string, absoluteData: LineDataPoint[], vm: 'absolute' | 'percentage'): RenderedSignal[] {
        // Access version to trigger reactivity
        void getSettingsVersion();
        const settings = getSettingsForPair(slug, 'fx');
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

            // AssetComparisonSignal: graceful skip — asset data not available in FX view
            // Full resolution requires async loading, will be implemented in Parte A
            if (cfg.signalType === 'asset-comparison') {
                continue;
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
        refreshing = true;
        try {
            invalidateAllFxStores();
            pairs = pairs.map(p => ({...p, data: [], loading: true}));
            await fetchAllPairData();
        } finally {
            refreshing = false;
        }
    }

    async function handleRefreshPair(detail: { slug: string }) {
        const idx = pairs.findIndex(p => p.config.slug === detail.slug);
        if (idx < 0) return;
        const store = getFxStore(detail.slug);
        store.invalidateRange(dateStart, dateEnd);
        await fetchPairData(idx);
    }

    function handleDeletePair(detail: { base: string; quote: string; slug: string }) {
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
            const deleteResponse = await zodiosApi.delete_rates_endpoint_api_v1_fx_currencies_rate_delete([{
                from: deletingPair.base,
                to: deletingPair.quote,
                delete_all: true,
            }]);
            const rateCount = (deleteResponse as any)?.results?.[0]?.deleted_count ?? 0;

            // Step 3: Clean up frontend state
            removeFxStore(deletingPair.slug);
            pairs = pairs.filter(p => p.config.slug !== deletingPair!.slug);

            // Step 4: Reset currency filters if selected currency no longer exists
            const remaining = new Set(pairs.flatMap(p => [p.config.base, p.config.quote]));
            if (filterCurrency1 && !remaining.has(filterCurrency1)) filterCurrency1 = '';
            if (filterCurrency2 && !remaining.has(filterCurrency2)) filterCurrency2 = '';

            const pairLabel = deletingPair.slug.replace('-', '/');
            toasts.success($_('fx.delete.toastOk', {values: {pair: pairLabel, count: rateCount}}));

            deleteDialogOpen = false;
            deletingPair = null;
        } catch (e: any) {
            console.error('Failed to delete pair:', e);
            toasts.error($_('fx.delete.toastFailed', {values: {pair: deletingPair?.slug?.replace('-', '/') ?? ''}}));
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
        syncModalPairs = pairs
            .filter(p => !(p.config.providers.length === 1 && p.config.providers[0].providerCode === 'MANUAL'))
            .map(p => `${p.config.base}-${p.config.quote}`);
        syncModalOpen = true;
    }

    // =========================================================================
    // Bulk Actions (table selection)
    // =========================================================================

    function handleBulkSyncFx() {
        syncModalPairs = selectedFxRows
            .filter(r => !r.manualOnly)
            .map(r => `${r.base}-${r.quote}`);
        syncModalOpen = true;
    }

    async function handleBulkRefreshFx() {
        for (const row of selectedFxRows) {
            await handleRefreshPair({slug: row.slug});
        }
        fxTableComponent?.getTableRef()?.clearSelection();
        selectedFxRows = [];
    }

    function handleBulkInvertFx() {
        const slugs = selectedFxRows.map(r => r.slug);
        fxTableComponent?.bulkToggleInversion(slugs);
        fxTableComponent?.getTableRef()?.clearSelection();
        selectedFxRows = [];
    }

    async function handleBulkDeleteFx() {
        deletingPairs = selectedFxRows.map(r => ({base: r.base, quote: r.quote, slug: r.slug}));
        bulkDeleteDialogOpen = true;
    }

    async function confirmBulkDelete() {
        if (deletingPairs.length === 0) return;
        bulkDeleteLoading = true;
        const perPairResults: { label: string; success: boolean; detail?: string }[] = [];
        try {
            for (const pair of deletingPairs) {
                try {
                    await zodiosApi.delete_routes_bulk_api_v1_fx_providers_routes_delete([{
                        base: pair.base,
                        quote: pair.quote,
                    }]);
                    const deleteResponse = await zodiosApi.delete_rates_endpoint_api_v1_fx_currencies_rate_delete([{
                        from: pair.base,
                        to: pair.quote,
                        delete_all: true,
                    }]);
                    const rateCount = (deleteResponse as any)?.results?.[0]?.deleted_count ?? 0;
                    removeFxStore(pair.slug);
                    perPairResults.push({
                        label: `${pair.base}/${pair.quote}`,
                        success: true,
                        detail: $_('fx.delete.resultDeleted', {values: {count: rateCount}}),
                    });
                } catch (pairErr: any) {
                    perPairResults.push({
                        label: `${pair.base}/${pair.quote}`,
                        success: false,
                        detail: pairErr?.message || 'Error',
                    });
                }
            }

            const deletedSlugs = new Set(
                perPairResults.filter(r => r.success).map((_, i) => deletingPairs[i].slug)
            );
            pairs = pairs.filter(p => !deletedSlugs.has(p.config.slug));

            // Reset currency filters if selected currency no longer exists
            const remaining = new Set(pairs.flatMap(p => [p.config.base, p.config.quote]));
            if (filterCurrency1 && !remaining.has(filterCurrency1)) filterCurrency1 = '';
            if (filterCurrency2 && !remaining.has(filterCurrency2)) filterCurrency2 = '';

            bulkFxDeleteResults = perPairResults;
        } catch (e: any) {
            console.error('Failed to bulk delete pairs:', e);
        } finally {
            bulkDeleteLoading = false;
        }
    }

    function closeBulkFxDeleteDialog() {
        bulkDeleteDialogOpen = false;
        bulkFxDeleteResults = [];
        deletingPairs = [];
        fxTableComponent?.getTableRef()?.clearSelection();
        selectedFxRows = [];
    }

    async function handleSyncPair(detail: { slug: string; base: string; quote: string }) {
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
                    toasts.success(t('fx.sync.toastOk', {
                        values: {
                            pair: label,
                            fetched: r.points_fetched ?? 0,
                            changed: r.points_changed ?? 0,
                            provider: formatProviderText(r.provider_used)
                        }
                    }));
                } else if (r.status === 'partial') {
                    let msg = t('fx.sync.toastPartial', {
                        values: {
                            pair: label,
                            fetched: r.points_fetched ?? 0,
                            changed: r.points_changed ?? 0,
                            provider: formatProviderText(r.provider_used)
                        }
                    });
                    msg += formatSyncDetail(r, t);
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

    async function handlePairCreated(detail: { base: string; quote: string; hasRealProvider: boolean }) {
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
    <!-- Header: Title left, ViewModeToggle + Add Pair right -->
    <div class="flex items-center justify-between">
        <div>
            <h2 class="text-lg font-semibold text-gray-700 dark:text-gray-200 flex items-center gap-2">
                {$_('fx.title')}
                {#if pairs.length > 0}
                    <span data-testid="fx-pair-count-badge"
                          class="text-xs font-mono px-1.5 py-0.5 rounded-full bg-libre-green/10 text-libre-green dark:bg-libre-green/20 dark:text-emerald-400">{pairs.length}</span>
                {/if}
            </h2>
            <p class="text-gray-500 dark:text-gray-400 text-sm">{$_('fx.subtitle')}</p>
        </div>
        <div class="flex items-center gap-2">
            {#if viewMode === 'list' && selectedFxRows.length > 0}
                <DataTableToolbar
                        selectedCount={selectedFxRows.length}
                        bulkActions={[
                        { id: 'sync', icon: RotateCw, label: () => $_('common.sync'), onClick: () => handleBulkSyncFx() },
                        { id: 'refresh', icon: RefreshCw, label: () => $_('common.refresh'), onClick: () => handleBulkRefreshFx() },
                        { id: 'invert', icon: ArrowLeftRight, label: () => $_('common.swapDirection'), onClick: () => handleBulkInvertFx() },
                        { id: 'delete', icon: Trash2, label: () => $_('common.delete'), variant: 'danger', onClick: () => handleBulkDeleteFx() },
                    ]}
                        onClearSelection={() => { fxTableComponent?.getTableRef()?.clearSelection(); selectedFxRows = []; }}
                />
            {/if}
            <ViewModeToggle bind:mode={viewMode} storageKey="fxViewMode"/>
            <button
                    class="flex items-center gap-1.5 px-3 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors whitespace-nowrap"
                    data-testid="fx-add-pair-button"
                    onclick={handleAddPair}
            >
                <Plus size={16}/>
                {$_('fx.actions.addPair')}
            </button>
        </div>
    </div>

    <!-- Filter Bar: 100% programmatic layout — NO flex-wrap, NO CSS-driven wrapping.
         wide:     [ datepicker  currency ─── actions-2×2 ]  all in one row
         tablet:   [ datepicker       ] [ actions-2×2 ]      filters stacked, actions grid right
                   [ currency-filters ] [             ]
         tablet-s: [ datepicker                     | col  ]
                   [ currency-filters               | btns ]
         mobile:   [ datepicker       ]  all stacked centered
                   [ currency-filters ]
                   [ actions-row      ] -->
    <div
            bind:this={filterBarRef}
            class="flex gap-3 p-4 bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700
               {layoutMode === 'mobile' ? 'flex-col items-center'
                : layoutMode === 'tablet-s' ? 'flex-row items-start justify-between'
                : 'flex-row items-center justify-between'}"
    >
        <!-- Filters block -->
        <div class="flex gap-3
                    {layoutMode === 'mobile' ? 'flex-col items-center'
                     : layoutMode === 'tablet-s' ? 'flex-col items-start flex-1'
                     : layoutMode === 'wide' ? 'flex-row items-center flex-1'
                     : 'flex-col items-center'}"
        >
            <!-- DateRangePicker -->
            <div class="max-w-md" data-testid="fx-date-range-picker">
                <DateRangePicker
                        bind:activePreset
                        bind:end={dateEnd}
                        bind:start={dateStart}
                        compact={true}
                        onchange={handleDateRangeChange}
                />
            </div>

            <!-- Currency Filters — always grouped as a pair -->
            <div class="flex items-center gap-3">
                <div class="w-40" data-testid="fx-currency-filter">
                    <CurrencySearchSelect
                            allowedCurrencies={allowedForFilter1}
                            bind:value={filterCurrency1}
                            includeAll={true}
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
                            placeholder={$_('fx.filter.filterCurrency')}
                    />
                </div>
                <div class="w-40 transition-opacity {filterCurrency1 ? '' : 'opacity-50'}" data-testid="fx-currency-filter">
                    <CurrencySearchSelect
                            allowedCurrencies={allowedForFilter2}
                            bind:value={filterCurrency2}
                            disabled={!filterCurrency1}
                            includeAll={true}
                            maxVisibleItems={6}
                            placeholder={$_('fx.filter.secondCurrency')}
                    />
                </div>
                <!-- Reset filters button -->
                <button
                        class="p-1.5 rounded-md transition-colors {filterCurrency1
                        ? 'hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 hover:text-red-500 dark:text-gray-400 dark:hover:text-red-400'
                        : 'text-gray-300 dark:text-gray-600 cursor-not-allowed'}"
                        data-testid="fx-reset-filters"
                        disabled={!filterCurrency1}
                        onclick={() => { filterCurrency1 = ''; filterCurrency2 = ''; }}
                        title={$_('fx.filter.resetFilters')}
                >
                    <X size={16}/>
                </button>
            </div>
        </div>

        <!-- Actions: 2×2 grid (wide+tablet), column (tablet-s), horizontal row (mobile) -->
        <div class="flex shrink-0 gap-1.5
                    {layoutMode === 'mobile' ? 'flex-row justify-center'
                     : layoutMode === 'tablet-s' ? 'flex-col'
                     : 'grid grid-cols-2'}"
        >
            <!-- Top-left: Abs/% toggle in grid mode, ColumnVisibility in table mode -->
            {#if viewMode === 'list'}
                <ColumnVisibilityToggle tableRef={fxTableComponent?.getTableRef()} showLabel={showActionLabels}/>
            {:else}
                <div class="flex rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
                    <button
                            class="flex-1 px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {globalViewMode === 'absolute'
                            ? 'bg-libre-green text-white'
                            : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                            onclick={() => { globalViewMode = 'absolute'; }}
                    >Abs
                    </button>
                    <button
                            class="flex-1 px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {globalViewMode === 'percentage'
                            ? 'bg-libre-green text-white'
                            : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                            onclick={() => { globalViewMode = 'percentage'; }}
                    >%
                    </button>
                </div>
            {/if}
            <!-- Settings -->
            <button
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                    data-testid="fx-chart-settings-button"
                    onclick={handleGlobalSettings}
            >
                <Settings size={14}/>
                {#if showActionLabels}<span>{$_('sharedResource.settings')}</span>{/if}
            </button>
            <!-- Sync All -->
            <button
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                    data-testid="fx-sync-all-button"
                    onclick={handleSyncAll}
            >
                <RotateCw size={14}/>
                {#if showActionLabels}<span>{$_('sharedResource.syncAll')}</span>{/if}
            </button>
            <!-- Refresh All -->
            <button
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                    data-testid="fx-refresh-all-button"
                    onclick={handleRefreshAll}
            >
                <RefreshCw class={refreshing ? 'animate-spin' : ''} size={14}/>
                {#if showActionLabels}<span>{$_('sharedResource.refreshAll')}</span>{/if}
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
                    <Plus size={16} class="inline mr-1"/>
                    {$_('fx.empty.addFirstPair')}
                </button>
            {:else}
                <h3 class="text-lg font-semibold text-gray-700 dark:text-gray-200 mb-2">{$_('fx.empty.noMatchesTitle')}</h3>
                <p class="text-gray-500 dark:text-gray-400">{$_('fx.empty.noMatchesDesc')}</p>
            {/if}
        </div>
    {:else if viewMode === 'grid'}
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
                        chartSettings={getSettingsForPair(pair.config.slug, 'fx')}
                        renderSignals={(chartData, vm) => getRenderedSignals(pair.config.slug, chartData, vm)}
                        ondelete={handleDeletePair}
                        onrefresh={handleRefreshPair}
                        onsync={handleSyncPair}
                        onsettings={handleCardSettings}
                />
            {/each}
        </div>
    {:else}
        <!-- Table View -->
        <FxTable
                bind:this={fxTableComponent}
                data={fxTableRows}
                loading={false}
                {visiblePeriods}
                onsync={handleSyncPair}
                onrefresh={handleRefreshPair}
                ondelete={handleDeletePair}
                onselectionchange={(rows) => { selectedFxRows = rows; }}
        />
    {/if}
</div>

<!-- Delete Confirm Dialog (single) -->
<ConfirmModal
        confirmText={$_('common.delete')}
        danger={true}
        description={$_('fx.deletePairWarning')}
        message={$_('fx.deletePairQuestion', {values: {pair: `${deletingPair?.base ?? ''}/${deletingPair?.quote ?? ''}`}})}
        onCancel={() => { deleteDialogOpen = false; deletingPair = null; }}
        onConfirm={confirmDelete}
        open={deleteDialogOpen}
        title={$_('fx.deletePairTitle')}
/>

<!-- Delete Confirm Dialog (bulk) -->
<ConfirmModal
        confirmText={$_('common.delete')}
        danger={true}
        description={$_('fx.deletePairWarning')}
        items={deletingPairs.map(p => `${getCurrencyInfo(p.base).flag_emoji} ${p.base} / ${getCurrencyInfo(p.quote).flag_emoji} ${p.quote}`)}
        itemsLabel={`${deletingPairs.length} pairs`}
        message={$_('fx.deletePairQuestion', {values: {pair: `${deletingPairs.length} pairs`}})}
        onCancel={closeBulkFxDeleteDialog}
        onConfirm={confirmBulkDelete}
        open={bulkDeleteDialogOpen}
        results={bulkFxDeleteResults}
        title={$_('fx.deletePairTitle')}
/>

<!-- Add Pair Modal -->
<FxPairAddModal
        bind:open={addModalOpen}
        {dateEnd}
        {dateStart}
        onclose={() => addModalOpen = false}
        oncreated={handlePairCreated}
/>

<!-- Sync Modal -->
<FxSyncModal
        bind:open={syncModalOpen}
        {dateEnd}
        {dateStart}
        onclose={() => syncModalOpen = false}
        onsynced={handleSynced}
        pairs={syncModalPairs}
/>

<!-- Chart Settings Modal (global or per-card depending on settingsTargetSlug) -->
<ChartSettingsModal
        availableAssets={availableAssetsList}
        availablePairs={pairs.map(p => `${p.config.base}-${p.config.quote}`)}
        bind:open={settingsModalOpen}
        mode={settingsTargetSlug ? 'pair' : 'global'}
        onclose={() => { settingsModalOpen = false; settingsTargetSlug = null; }}
        onsave={handleSettingsSave}
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
        settings={settingsForModal}
/>

