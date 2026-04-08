<script lang="ts">
    /**
     * Asset Detail Page — Phase 06 Step 4 Part A
     *
     * Layout:
     * - Header: asset info + back button
     * - Filter bar: DateRangePicker | CurrencySelect | price summary | 2×2 button matrix
     * - Chart: PriceChartFull with overlay signals + event markers
     * - Foldable panels: Aesthetics, Data Editor (placeholder), Measures, Signals
     * - Metadata section (accordion, readonly)
     * - AssetModal for edit
     *
     * Uses Svelte 5 runes. Reference: fx/[pair]/+page.svelte
     */
    import {onMount, tick} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import {get} from 'svelte/store';
    import {zodiosApi} from '$lib/api';
    import {goBack} from '$lib/stores/navigationStore';
    import {
        ArrowLeft, ChevronDown, Construction, ExternalLink, Info, Pencil, RefreshCw, RotateCw,
        Ruler, Settings, TrendingUp, X
    } from 'lucide-svelte';
    import {toasts} from '$lib/stores/toastStore.svelte';
    import PriceChartFull from '$lib/components/charts/PriceChartFull.svelte';
    import ChartAestheticsSection from '$lib/components/charts/ChartAestheticsSection.svelte';
    import ChartSignalsSection from '$lib/components/charts/ChartSignalsSection.svelte';
    import MeasurePanel from '$lib/components/charts/MeasurePanel.svelte';
    import SectorPieChart from '$lib/components/charts/SectorPieChart.svelte';
    import GeographyMap from '$lib/components/charts/GeographyMap.svelte';
    import AssetModal from '$lib/components/assets/AssetModal.svelte';
    import AssetIcon from '$lib/components/assets/AssetIcon.svelte';
    import AssetPriceSummary from '$lib/components/assets/AssetPriceSummary.svelte';
    import FxPairAddModal from '$lib/components/fx/FxPairAddModal.svelte';
    import DateRangePicker from '$lib/components/ui/DateRangePicker.svelte';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import type {RenderedSignal, SignalConfig} from '$lib/charts/signals';
    import {signalFromConfig} from '$lib/charts/signals';
    import {getSettingsForPair, setPairSettings} from '$lib/stores/chartSettingsStore.svelte';
    import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/currencyStore';
    import {currentLanguage} from '$lib/stores/language';
    import type {ViewMode} from '$lib/components/charts/ChartToolbar.svelte';
    import {createResponsiveLayout} from '$lib/utils/responsiveLayout.svelte';
    import {getFxStore} from '$lib/stores/fxStoreRegistry';
    import {getAssetTypeIconUrl, buildIdentifiersList} from '$lib/utils/assetTypes';
    import {ensureAssetProvidersCached, getAssetProviderIconUrl, getAssetProviderName} from '$lib/utils/providerHelpers';
    import type {AssetDetail, ProviderAssignmentFlat} from '$lib/types';

    // =========================================================================
    // Page data
    // =========================================================================

    interface Props {
        data: { assetId: number };
    }

    let {data}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let assetInfo = $state<AssetDetail | null>(null);
    let providerAssignment = $state<ProviderAssignmentFlat | null>(null);
    let chartData: any[] = $state([]);
    let events: any[] = $state([]);
    let comparisonEvents = $state<Map<number, any[]>>(new Map());

    let loading = $state(true);
    let error: string | null = $state(null);
    let syncing = $state(false);

    // Date range (default 3M)
    let dateEnd = $state(new Date().toISOString().slice(0, 10));
    let dateStart = $state((() => {
        const d = new Date();
        d.setMonth(d.getMonth() - 3);
        return d.toISOString().slice(0, 10);
    })());
    let activePreset: any = $state('3M');

    let viewMode: ViewMode = $state('absolute');
    let displayCurrency = $state('');

    // Foldable panels
    let showAesthetics = $state(false);
    let showMeasures = $state(false);
    let showSignals = $state(false);
    let showDataEditor = $state(false);
    let showMetadata = $state(false);

    // Filter bar layout
    let filterBarRef = $state<HTMLDivElement | null>(null);
    const layout = createResponsiveLayout({wide: 1090, tablet: 870, tabletS: 570, labelHide: 380});

    // Chart settings
    let settings = $derived(getSettingsForPair(`asset-${data.assetId}`, 'assets'));
    let signals = $derived<SignalConfig[]>([...settings.signals]);

    // Measure panel
    let measureMode = $state(false);
    let measureSignals: RenderedSignal[] = $state([]);
    let measurePanel: MeasurePanel | undefined = $state(undefined);

    // Editor panel state save/restore
    let savedPanelStates: { aesthetics: boolean; measures: boolean; signals: boolean } | null = $state(null);

    let overlayDataVersion = $state(0);
    let editModalOpen = $state(false);

    // Edit data — computed on-demand when modal opens (NOT $derived, to avoid effect loops)
    let editDataForModal = $state<ReturnType<typeof buildEditData>>(null);

    // Cross-domain data for signals
    let allConfiguredFxSlugs: string[] = $state([]);
    let allAssets: Array<{ id: number; display_name: string; icon_url?: string | null; asset_type?: string | null }> = $state([]);

    // Classification data (loaded when has_metadata)
    let sectorDistribution: Record<string, number> | null = $state(null);
    let geographicDistribution: Record<string, number> | null = $state(null);
    let classificationLoaded = $state(false);

    // Provider icon for header badge
    let providerIconUrl = $state<string | null>(null);

    // FX warning (tooltip-based, no toast)

    // FX pair add modal (opened from FX warning)
    let showFxPairAddModal = $state(false);

    // =========================================================================
    // Derived
    // =========================================================================

    let lineData: LineDataPoint[] = $derived(chartData.map((p: any) => ({
        date: p.date,
        value: Number(p.close ?? 0),
        staleDays: p.backward_fill_info?.days_back ?? 0,
    })));

    let isScheduledInvestment = $derived(providerAssignment?.provider_code === 'scheduled_investment');
    let isManualOnly = $derived(!providerAssignment);

    let lastPrice = $derived.by(() => {
        if (chartData.length === 0) return null;
        const last = chartData[chartData.length - 1];
        return last?.close != null ? Number(last.close) : null;
    });

    let deltaPercent = $derived.by(() => {
        if (chartData.length < 2) return null;
        const first = Number(chartData[0].close ?? 0);
        const last = Number(chartData[chartData.length - 1].close ?? 0);
        if (first === 0) return null;
        return ((last - first) / first) * 100;
    });

    let deltaAbs = $derived.by(() => {
        if (chartData.length < 2) return null;
        const first = Number(chartData[0].close ?? 0);
        const last = Number(chartData[chartData.length - 1].close ?? 0);
        if (first === 0) return null;
        return last - first;
    });

    let currencyFlag = $derived.by(() => {
        if (!assetInfo?.currency) return '';
        return getCurrencyInfo(assetInfo.currency).flag_emoji;
    });

    let userUrl = $derived(assetInfo?.user_url || null);
    let providerExternalUrl = $derived(providerAssignment?.provider_url || null);

    /** True when display currency differs from asset currency and FX pair is not configured */
    let fxConversionMissing = $derived.by(() => {
        if (!assetInfo || !displayCurrency || displayCurrency === assetInfo.currency) return false;
        const a = assetInfo.currency < displayCurrency ? assetInfo.currency : displayCurrency;
        const b = assetInfo.currency < displayCurrency ? displayCurrency : assetInfo.currency;
        const slug = `${a}-${b}`;
        return !allConfiguredFxSlugs.includes(slug);
    });

    /** Canonical FX pair slug (alphabetically ordered) for linking */
    let fxPairSlug = $derived.by(() => {
        if (!assetInfo || !displayCurrency || displayCurrency === assetInfo.currency) return '';
        const a = assetInfo.currency < displayCurrency ? assetInfo.currency : displayCurrency;
        const b = assetInfo.currency < displayCurrency ? displayCurrency : assetInfo.currency;
        return `${a}-${b}`;
    });

    let identifiersList = $derived.by((): [string, string][] => {
        if (!assetInfo) return [];
        return buildIdentifiersList(assetInfo as Record<string, unknown>);
    });

    // Overlay signals
    let overlaySignals: RenderedSignal[] = $derived.by(() => {
        void overlayDataVersion;
        const rendered: RenderedSignal[] = [];
        for (const cfg of signals) {
            const instance = signalFromConfig(cfg);
            if (!instance) continue;

            if (cfg.signalType === 'fx-pair') {
                const pairSlug = String(cfg.params.pairSlug || '');
                if (!pairSlug) continue;
                try {
                    const store = getFxStore(pairSlug);
                    const storeData = store.getAllSorted();
                    if (storeData.length === 0) continue;
                    instance.params._resolvedData = storeData.map(d => ({date: d.date, value: d.rate}));
                } catch { continue; }
            }

            if (cfg.signalType === 'asset-comparison') {
                const targetId = Number(cfg.params.assetId);
                if (!targetId || targetId === data.assetId) continue;
                const targetAsset = allAssets.find(a => a.id === targetId);
                instance.params._assetDisplayName = targetAsset?.display_name ?? `Asset #${targetId}`;
                if (!instance.params._resolvedData) continue;
            }

            const results = instance.renderMulti(lineData, viewMode);
            for (const result of results) {
                if (result.data.length > 0) rendered.push(result);
            }
        }
        return rendered;
    });

    let allOverlaySignals: RenderedSignal[] = $derived([
        ...overlaySignals,
        ...measureSignals,
    ]);

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(async () => {
        await Promise.all([
            ensureCurrenciesLoaded(get(currentLanguage)),
            ensureAssetProvidersCached(),
            loadAssetInfo(),
            loadProviderAssignment(),
            loadChartData(),
            loadFxPairSlugs(),
            loadAssetList(),
        ]);
        // Resolve provider icon after data loads
        if (assetInfo?.provider_code) {
            providerIconUrl = getAssetProviderIconUrl(assetInfo.provider_code);
        }
        // Load classification data if available
        if (assetInfo?.has_metadata) {
            await loadClassificationData();
        } else {
            classificationLoaded = true;
        }
    });

    $effect(() => {
        const el = filterBarRef;
        if (!el) return;
        layout.attach(el);
        return () => layout.detach();
    });

    $effect(() => {
        const compSignals = signals.filter(s => s.signalType === 'asset-comparison');
        if (compSignals.length > 0 && lineData.length > 0) {
            loadComparisonAssetsData(compSignals);
        }
    });


    // =========================================================================
    // Data Loading
    // =========================================================================

    async function loadAssetInfo() {
        try {
            const response = await zodiosApi.get_all_assets_api_v1_assets_all_get();
            const items = response as any[];
            const asset = items.find((a: any) => a.id === data.assetId);
            if (asset) {
                assetInfo = asset as AssetDetail;
                if (!displayCurrency) displayCurrency = asset.currency;
            } else {
                error = `Asset #${data.assetId} not found`;
            }
        } catch (e: any) {
            console.error('Failed to load asset info:', e);
            error = e?.message || 'Failed to load asset info';
        }
    }

    async function loadProviderAssignment() {
        try {
            const response = await zodiosApi.get_provider_assignments_api_v1_assets_provider_assignments_get({
                queries: {asset_ids: [data.assetId]},
            });
            const items = response as any[];
            providerAssignment = items.length > 0 ? (items[0] as ProviderAssignmentFlat) : null;
        } catch (e: any) {
            console.error('Failed to load provider assignment:', e);
        }
    }

    async function loadChartData() {
        loading = true;
        error = null;
        try {
            const response = await zodiosApi.query_prices_bulk_api_v1_assets_prices_query_post([{
                asset_id: data.assetId,
                date_range: {start: dateStart, end: dateEnd},
                include_events: true,
            }]);
            const result = (response as any)?.items?.[0];
            if (result) {
                chartData = result.prices ?? [];
                events = result.events ?? [];
            } else {
                chartData = [];
                events = [];
            }
        } catch (e: any) {
            console.error('Failed to load chart data:', e);
            if (chartData.length === 0) error = e?.message || 'Failed to load prices';
        } finally {
            loading = false;
        }
    }

    async function loadFxPairSlugs() {
        try {
            const response = await zodiosApi.list_routes_api_v1_fx_providers_routes_get();
            const items = (response as any)?.items || [];
            const slugSet = new Set<string>();
            for (const i of items) {
                const b = i.base < i.quote ? i.base : i.quote;
                const q = i.base < i.quote ? i.quote : i.base;
                slugSet.add(`${b}-${q}`);
            }
            allConfiguredFxSlugs = [...slugSet].sort();
        } catch (e) { console.error('Failed to load FX pair slugs:', e); }
    }

    async function loadAssetList() {
        try {
            const response = await zodiosApi.get_all_assets_api_v1_assets_all_get();
            allAssets = (response as any[]).map((a: any) => ({
                id: a.id, display_name: a.display_name,
                icon_url: a.icon_url ?? null, asset_type: a.asset_type ?? null,
            }));
        } catch (e) { console.error('Failed to load asset list:', e); }
    }

    async function loadClassificationData() {
        try {
            const response = await zodiosApi.read_assets_bulk_api_v1_assets_get({
                queries: {asset_ids: [data.assetId]},
            });
            const items = response as any[];
            if (items.length > 0 && items[0].classification_params) {
                const cp = items[0].classification_params;
                sectorDistribution = cp.sector_area?.distribution ?? null;
                geographicDistribution = cp.geographic_area?.distribution ?? null;
            } else {
                // No classification data — reset to null (prevents stale data from previous asset)
                sectorDistribution = null;
                geographicDistribution = null;
            }
        } catch (e) {
            console.error('Failed to load classification data:', e);
            sectorDistribution = null;
            geographicDistribution = null;
        } finally {
            classificationLoaded = true;
        }
    }

    async function loadComparisonAssetsData(compSignals: SignalConfig[]) {
        const idsToLoad = compSignals
            .map(s => Number(s.params.assetId))
            .filter(id => id && id !== data.assetId);
        if (idsToLoad.length === 0) return;
        try {
            const queries = idsToLoad.map(id => ({
                asset_id: id,
                date_range: {start: dateStart, end: dateEnd},
                include_events: true,
            }));
            const response = await zodiosApi.query_prices_bulk_api_v1_assets_prices_query_post(queries);
            const items = (response as any)?.items ?? [];
            const newCompEvents = new Map<number, any[]>(comparisonEvents);
            for (const result of items) {
                const aid = result.asset_id;
                const prices = (result.prices ?? []).map((p: any) => ({date: p.date, value: Number(p.close ?? 0)}));
                for (const cfg of compSignals) {
                    if (Number(cfg.params.assetId) === aid) cfg.params._resolvedData = prices;
                }
                newCompEvents.set(aid, result.events ?? []);
            }
            comparisonEvents = newCompEvents;
            overlayDataVersion++;
        } catch (e) { console.error('Failed to load comparison asset data:', e); }
    }

    // =========================================================================
    // Actions
    // =========================================================================


    async function handleRefresh() {
        await loadChartData();
        overlayDataVersion++;
    }

    async function reloadMetadata() {
        await Promise.all([loadAssetInfo(), loadProviderAssignment()]);
        // Update provider icon if changed
        if (assetInfo?.provider_code) {
            providerIconUrl = getAssetProviderIconUrl(assetInfo.provider_code);
        }
        // Reload classification data if metadata is available (always refresh after sync)
        classificationLoaded = false;
        if (assetInfo?.has_metadata) {
            await loadClassificationData();
        } else {
            sectorDistribution = null;
            geographicDistribution = null;
            classificationLoaded = true;
        }
    }

    async function handleSync() {
        syncing = true;
        try {
            const response = await zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post([{
                asset_id: data.assetId,
                date_range: {start: dateStart, end: dateEnd},
            }]);
            const r = (response as any)?.results?.[0];
            if (r) {
                const tr = get(t);
                if (r.status === 'ok') {
                    toasts.success(`${tr('assetDetail.syncPrices')}: ${r.points_fetched ?? 0}↓ ${r.points_changed ?? 0}Δ`);
                } else if (r.status === 'partial') {
                    toasts.warning(`${tr('assetDetail.syncPrices')} (partial): ${r.points_fetched ?? 0}↓ ${r.points_changed ?? 0}Δ`);
                } else if (r.status === 'skipped') {
                    toasts.info(`${tr('assetDetail.syncPrices')} — skipped`);
                } else {
                    toasts.error(`${tr('assetDetail.syncPrices')} — ${r.message || 'failed'}`);
                }
            }
            await handleRefresh();
            await reloadMetadata();
        } catch (e: any) {
            console.error('Sync failed:', e);
            toasts.error('Sync failed: ' + (e?.message || 'unknown'));
        } finally {
            syncing = false;
        }
    }

    function handleDateRangeChange(newStart: string, newEnd: string) {
        dateStart = newStart;
        dateEnd = newEnd;
        loadChartData();
    }

    function handleMeasureClick(date: string, value: number) {
        measurePanel?.addPoint(date, value);
    }

    function handleAestheticsChange(values: {
        colorByBaseline: boolean; areaFill: boolean; gridLines: boolean;
        staleGradient: boolean; yAxisMode: 'auto' | 'include0' | 'custom';
        yAxisMin: number | undefined; yAxisMax: number | undefined;
    }) {
        setPairSettings(`asset-${data.assetId}`, {...settings, ...values, signals: [...signals]});
    }

    function handleSignalsChange(newSignals: SignalConfig[]) {
        setPairSettings(`asset-${data.assetId}`, {...settings, signals: JSON.parse(JSON.stringify(newSignals))});
    }

    async function handleAssetUpdated() {
        editModalOpen = false;
        await reloadMetadata();
        if (providerAssignment) {
            await handleSync();
        } else {
            await handleRefresh();
        }
    }

    function buildEditData() {
        if (!assetInfo) return null;
        // Build classification_params from loaded data
        const hasClassification = sectorDistribution || geographicDistribution;
        const classification_params = hasClassification ? {
            sector_area: sectorDistribution ? {distribution: sectorDistribution} : null,
            geographic_area: geographicDistribution ? {distribution: geographicDistribution} : null,
        } : null;
        return {
            id: assetInfo.id,
            display_name: assetInfo.display_name,
            currency: assetInfo.currency,
            asset_type: assetInfo.asset_type ?? '',
            icon_url: assetInfo.icon_url,
            active: assetInfo.active,
            classification_params,
            identifier_isin: assetInfo.identifier_isin,
            identifier_ticker: assetInfo.identifier_ticker,
            identifier_cusip: assetInfo.identifier_cusip,
            identifier_sedol: assetInfo.identifier_sedol,
            identifier_figi: assetInfo.identifier_figi,
            identifier_uuid: assetInfo.identifier_uuid,
            identifier_other: assetInfo.identifier_other,
            provider_code: providerAssignment?.provider_code ?? null,
            provider_identifier: providerAssignment?.identifier ?? '',
            provider_identifier_type: providerAssignment?.identifier_type ?? '',
            provider_params: providerAssignment?.provider_params ?? null,
            provider_user_url: assetInfo.user_url ?? '',
            provider_url: providerAssignment?.provider_url ?? null,
        };
    }
</script>

<div class="space-y-4" data-testid="asset-detail-page">
    <!-- ======================================================================= -->
    <!-- Header: asset info + back button -->
    <!-- ======================================================================= -->
    <div class="flex items-center gap-3" data-testid="asset-detail-header">
        <button
                class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-gray-400 transition-colors"
                data-testid="asset-detail-back-btn"
                onclick={() => goBack('/assets')}
                title={$t('assetDetail.backToList')}
        >
            <ArrowLeft size={20}/>
        </button>

        {#if assetInfo}
            <div class="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3" data-testid="asset-detail-info">
                <div class="flex items-center gap-3">
                    <AssetIcon iconUrl={assetInfo.icon_url} assetType={assetInfo.asset_type} altText={assetInfo.display_name} size="md"/>
                    <h2 class="text-xl font-bold text-gray-800 dark:text-gray-100">{assetInfo.display_name}</h2>
                </div>

                <div class="flex items-center gap-2 flex-wrap ml-0 sm:ml-0">
                    {#if assetInfo.asset_type}
                        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300">
                            <img src={getAssetTypeIconUrl(assetInfo.asset_type)} alt="" class="w-3.5 h-3.5"/>
                            {$t(`assets.types.${assetInfo.asset_type}`)}
                        </span>
                    {/if}

                    <span class="text-lg emoji-flag">{currencyFlag}</span>
                    <span class="text-sm font-mono text-gray-500 dark:text-gray-400">{assetInfo.currency}</span>

                    {#if assetInfo.provider_code}
                        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400">
                            {#if providerIconUrl}
                                <img src={providerIconUrl} alt="" class="w-3.5 h-3.5 rounded-sm object-contain" />
                            {/if}
                            {getAssetProviderName(assetInfo.provider_code)}
                        </span>
                    {/if}

                    {#if userUrl}
                        <a
                            href={userUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            class="inline-flex items-center p-1 rounded text-gray-400 hover:text-libre-green transition-colors"
                            title={userUrl}
                        >
                            <ExternalLink size={14}/>
                        </a>
                    {/if}
                </div>
            </div>
        {:else if loading}
            <div class="h-8 w-48 bg-gray-200 dark:bg-slate-700 rounded animate-pulse"></div>
        {/if}
    </div>

    <!-- Error banner -->
    {#if error}
        <div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4 text-sm text-amber-700 dark:text-amber-400 flex items-center gap-2">
            <span>⚠️</span> <span>{error}</span>
            <button class="ml-auto text-xs px-2 py-1 bg-amber-100 dark:bg-amber-900/40 rounded hover:bg-amber-200" onclick={() => error = null}>{$t('common.close')}</button>
        </div>
    {/if}

    <!-- ======================================================================= -->
    <!-- Filter bar -->
    <!-- wide:     [ datepicker  price-summary ─── actions-2×2 ]                        -->
    <!-- tablet:   [ datepicker       ] [ actions-2×2 ]  summary 2-row, beside picker   -->
    <!--           [ price-summary    ] [             ]                                  -->
    <!-- tablet-s: [ datepicker       ] [ actions ]  filters stacked, actions column     -->
    <!--           [ price-summary    ] [ 4×1    ]  to the right                         -->
    <!-- mobile:   [ datepicker       ]  all stacked, actions 1×4 row                   -->
    <!--           [ price-summary    ]                                                  -->
    <!--           [ actions ──── 1×4 ]                                                  -->
    <!-- ======================================================================= -->
    <div
            bind:this={filterBarRef}
            class="flex gap-3 p-4 bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700
               {layout.layoutMode === 'mobile' ? 'flex-col items-center' : 'flex-row items-start justify-between'}"
            data-testid="asset-detail-filter-bar"
    >
        <!-- Filters block: wide = row (side by side), tablet/tablet-s = column (stacked), mobile = centered -->
        <div class="flex gap-3 {layout.layoutMode === 'mobile' ? 'flex-col items-center'
             : layout.layoutMode === 'wide' ? 'flex-row items-center flex-1'
             : 'flex-col items-start flex-1'}">
            <div class="max-w-md">
                <DateRangePicker
                        bind:activePreset
                        bind:end={dateEnd}
                        bind:start={dateStart}
                        compact={true}
                        onchange={handleDateRangeChange}
                />
            </div>

            {#if assetInfo}
                <AssetPriceSummary
                        {lastPrice}
                        {deltaPercent}
                        {deltaAbs}
                        bind:displayCurrency
                        assetCurrency={assetInfo.currency}
                        {fxConversionMissing}
                        {fxPairSlug}
                        layoutMode={layout.layoutMode}
                        onAddFxPair={() => showFxPairAddModal = true}
                />
            {/if}
        </div>

        <!-- Actions: 2×2 grid (wide+tablet), 4×1 column (tablet-s), 1×4 row (mobile) -->
        <div class="flex shrink-0 gap-1.5 self-center
                    {layout.layoutMode === 'mobile' ? 'flex-row items-center justify-center'
                     : layout.layoutMode === 'tablet-s' ? 'flex-col items-stretch'
                     : 'grid grid-cols-2 ml-auto'}">
            <div class="flex rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
                <button
                        class="flex-1 px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {viewMode === 'absolute'
                        ? 'bg-libre-green text-white'
                        : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                        onclick={() => { viewMode = 'absolute'; }}
                >Abs</button>
                <button
                        class="flex-1 px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {viewMode === 'percentage'
                        ? 'bg-libre-green text-white'
                        : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                        onclick={() => { viewMode = 'percentage'; }}
                >%</button>
            </div>
            <button
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                    data-testid="asset-detail-edit-btn"
                    onclick={() => { editDataForModal = buildEditData(); editModalOpen = true; }}
            >
                <Pencil size={14}/>
                {#if layout.showActionLabels}<span>{$t('common.edit')}</span>{/if}
            </button>
            <button
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors
                           {isManualOnly ? 'opacity-50 cursor-not-allowed' : ''}"
                    data-testid="asset-detail-sync-btn"
                    disabled={syncing || isManualOnly}
                    onclick={handleSync}
                    title={isManualOnly ? $t('assetDetail.syncDisabledManual') : ''}
            >
                <RotateCw class={syncing ? 'animate-spin' : ''} size={14}/>
                {#if layout.showActionLabels}<span>{syncing ? $t('common.syncing') : (isScheduledInvestment ? $t('assetDetail.recalculate') : $t('common.sync'))}</span>{/if}
            </button>
            <button
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                    data-testid="asset-detail-refresh-btn"
                    disabled={loading}
                    onclick={handleRefresh}
            >
                <RefreshCw class={loading ? 'animate-spin' : ''} size={14}/>
                {#if layout.showActionLabels}<span>{$t('common.refresh')}</span>{/if}
            </button>
        </div>
    </div>

    <!-- ======================================================================= -->
    <!-- Foldable Panel: Signals (ABOVE chart, replaces old Aesthetics position) -->
    <!-- ======================================================================= -->
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
        <button
                class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors rounded-xl"
                data-testid="asset-detail-signals-toggle"
                onclick={() => showSignals = !showSignals}
        >
            <span class="flex items-center gap-2">
                <TrendingUp class="text-blue-500" size={15}/>
                {$t('assetDetail.signals')}
            </span>
            <ChevronDown class="transition-transform {showSignals ? 'rotate-180' : ''}" size={15}/>
        </button>
        {#if showSignals}
            <div data-testid="asset-detail-signals-panel" class="px-4 pb-4 border-t border-gray-100 dark:border-slate-700 pt-3">
                <ChartSignalsSection
                        signals={[...signals]}
                        availablePairs={allConfiguredFxSlugs}
                        availableAssets={allAssets.filter(a => a.id !== data.assetId)}
                        mainPairSlug={`asset-${data.assetId}`}
                        onchange={handleSignalsChange}
                />
            </div>
        {/if}
    </div>

    <!-- ======================================================================= -->
    <!-- Chart with left toolbar -->
    <!-- ======================================================================= -->
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 p-4" data-testid="asset-detail-chart">
        {#if loading && lineData.length === 0}
            <div class="h-96 flex items-center justify-center">
                <div class="text-center">
                    <RefreshCw size={24} class="animate-spin text-libre-green mx-auto mb-2"/>
                    <p class="text-sm text-gray-500 dark:text-gray-400">{$t('assetDetail.loadingPrices')}</p>
                </div>
            </div>
        {:else if lineData.length > 0}
            <!-- Aesthetics panel (ABOVE chart, shown only when gear is active) -->
            {#if showAesthetics}
                <div data-testid="asset-detail-aesthetics-panel" class="mb-3 pb-3 border-b border-gray-100 dark:border-slate-700 relative">
                    <button
                        class="absolute top-0 right-0 p-1 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-600 transition-colors"
                        onclick={() => showAesthetics = false}
                        title={$t('common.close')}
                    >
                        <X size={16}/>
                    </button>
                    <ChartAestheticsSection
                            colorByBaseline={settings.colorByBaseline}
                            areaFill={settings.areaFill}
                            gridLines={settings.gridLines}
                            staleGradient={settings.staleGradient}
                            yAxisMode={settings.yAxisMode}
                            yAxisMin={settings.yAxisMin}
                            yAxisMax={settings.yAxisMax}
                            onchange={handleAestheticsChange}
                    />
                </div>
            {/if}

            <div class="relative">
                <!-- Right toolbar -->
                <div class="absolute top-0 right-0 z-10 flex items-center gap-1.5">
                    <button
                            data-testid="asset-detail-measure-btn"
                            class="p-1.5 rounded-lg transition-colors {measureMode
                            ? 'bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400 ring-1 ring-violet-300 dark:ring-violet-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                            onclick={async () => {
                            if (measureMode) { measurePanel?.stopMeasureMode(); }
                            else { showMeasures = true; await tick(); measurePanel?.startMeasureMode(); }
                        }}
                            title={measureMode ? $t('assetDetail.exitMeasure') : $t('assetDetail.addMeasure')}
                    >
                        <Ruler size={16}/>
                    </button>
                    <button
                            data-testid="asset-detail-editdata-btn"
                            class="p-1.5 rounded-lg transition-colors {showDataEditor
                            ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400 ring-1 ring-amber-300 dark:ring-amber-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                            onclick={() => {
                            if (showDataEditor) {
                                showDataEditor = false;
                                if (savedPanelStates) { showAesthetics = savedPanelStates.aesthetics; showMeasures = savedPanelStates.measures; showSignals = savedPanelStates.signals; savedPanelStates = null; }
                            } else {
                                savedPanelStates = {aesthetics: showAesthetics, measures: showMeasures, signals: showSignals};
                                showAesthetics = false; showMeasures = false; showSignals = false; showDataEditor = true;
                            }
                        }}
                            title={showDataEditor ? $t('assetDetail.closeEditor') : $t('assetDetail.editData')}
                    >
                        <Pencil size={16}/>
                    </button>
                    <button
                            data-testid="asset-detail-aesthetics-toggle"
                            class="p-1.5 rounded-lg transition-colors {showAesthetics
                            ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400 ring-1 ring-emerald-300 dark:ring-emerald-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                            onclick={() => showAesthetics = !showAesthetics}
                            title={$t('common.aesthetics')}
                    >
                        <Settings size={16}/>
                    </button>
                </div>

                <PriceChartFull
                        data={lineData}
                        currency={displayCurrency}
                        mainSeriesLabel={assetInfo?.display_name ?? ''}
                        chartHeight="400px"
                        overlaySignals={allOverlaySignals}
                        colorByBaseline={settings.colorByBaseline}
                        areaFill={settings.areaFill}
                        showGridLines={settings.gridLines}
                        showGradient={settings.staleGradient}
                        yAxisMode={settings.yAxisMode}
                        yAxisMin={settings.yAxisMin}
                        yAxisMax={settings.yAxisMax}
                        measureMode={measureMode}
                        onMeasureClick={handleMeasureClick}
                        onMeasureHover={(date, value) => measurePanel?.updatePendingEnd(date, value)}
                        hideToolbar={true}
                        externalViewMode={viewMode}
                        editMode={showDataEditor}
                />
            </div>
        {:else}
            <div class="h-96 flex items-center justify-center">
                <div class="text-center">
                    {#if isManualOnly}
                        <p class="text-gray-400 dark:text-gray-500 mb-3">{$t('assetDetail.noDataManual')}</p>
                        <button class="px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors" onclick={() => { editDataForModal = buildEditData(); editModalOpen = true; }}>{$t('common.edit')}</button>
                    {:else if isScheduledInvestment}
                        <p class="text-gray-400 dark:text-gray-500 mb-3">{$t('assetDetail.noDataScheduled')}</p>
                        <button class="px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors" onclick={() => { editDataForModal = buildEditData(); editModalOpen = true; }}>{$t('common.edit')}</button>
                    {:else}
                        <p class="text-gray-400 dark:text-gray-500 mb-3">{$t('assetDetail.noData')}</p>
                        <button class="px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors" onclick={handleSync} disabled={syncing}>{syncing ? $t('common.syncing') : $t('assetDetail.syncPrices')}</button>
                    {/if}
                </div>
            </div>
        {/if}
    </div>

    <!-- ======================================================================= -->
    <!-- Data Editor Placeholder -->
    <!-- ======================================================================= -->
    {#if showDataEditor}
        <div data-testid="asset-detail-editor-panel" class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-amber-200 dark:border-amber-800">
            <div class="flex items-center justify-between px-4 py-3 border-b border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-yellow-900/30 rounded-t-xl">
                <span class="flex items-center gap-2 text-sm font-medium text-amber-700 dark:text-amber-400">
                    <Pencil size={15}/> {$t('assetDetail.editData')}
                </span>
                <button class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                        onclick={() => { showDataEditor = false; if (savedPanelStates) { showAesthetics = savedPanelStates.aesthetics; showMeasures = savedPanelStates.measures; showSignals = savedPanelStates.signals; savedPanelStates = null; } }}
                        title={$t('assetDetail.closeEditor')}>✕</button>
            </div>
            <div class="px-4 py-8 text-center">
                <Construction class="text-amber-400 mx-auto mb-2" size={32}/>
                <p class="text-sm text-gray-500 dark:text-gray-400">{$t('assetDetail.editDataComingSoon')}</p>
            </div>
        </div>
    {/if}

    <!-- ======================================================================= -->
    <!-- Foldable Panel: Measures -->
    <!-- ======================================================================= -->
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
        <button
                class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors rounded-xl"
                data-testid="asset-detail-measures-toggle"
                onclick={() => showMeasures = !showMeasures}
        >
            <span class="flex items-center gap-2">
                <Ruler class="text-violet-500" size={15}/>
                {$t('assetDetail.measures')}
                {#if measureMode}
                    <span class="text-[10px] px-1.5 py-0.5 bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400 rounded-full">{$t('measure.active')}</span>
                {/if}
            </span>
            <ChevronDown class="transition-transform {showMeasures ? 'rotate-180' : ''}" size={15}/>
        </button>
        <div class={showMeasures ? "px-4 pb-4 border-t border-gray-100 dark:border-slate-700 pt-3" : "hidden"} data-testid="asset-detail-measures-panel">
            <MeasurePanel
                    bind:this={measurePanel}
                    chartData={lineData}
                    onmeasuremodechange={(active) => measureMode = active}
                    onmeasureschange={(m) => measureSignals = m}
                    overlaySignals={overlaySignals}
                    pairLabel={assetInfo ? `📊 ${assetInfo.display_name}` : ''}
                    {viewMode}
            />
        </div>
    </div>


    <!-- ======================================================================= -->
    <!-- Foldable Panel: Metadata & Classification -->
    <!-- ======================================================================= -->
    {#if assetInfo}
        <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
            <button
                    class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors rounded-xl"
                    data-testid="asset-detail-metadata-toggle"
                    onclick={() => showMetadata = !showMetadata}
            >
                <span class="flex items-center gap-2">
                    <Info class="text-sky-500" size={15}/>
                    {$t('assetDetail.metadata')}
                </span>
                <ChevronDown class="transition-transform {showMetadata ? 'rotate-180' : ''}" size={15}/>
            </button>
            {#if showMetadata}
                <div data-testid="asset-detail-metadata-panel" class="px-4 pb-4 border-t border-gray-100 dark:border-slate-700 pt-3 space-y-4">
                    <!-- External URLs (provider URL only — user URL is in header) -->
                    {#if providerExternalUrl}
                        <div>
                            <h4 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2">{$t('assets.provider.providerUrl')}</h4>
                            <a href={providerExternalUrl} target="_blank" rel="noopener noreferrer"
                               class="text-sm text-libre-green hover:underline break-all">{providerExternalUrl}</a>
                        </div>
                    {/if}

                    <!-- Classification Charts -->
                    {#if classificationLoaded && (sectorDistribution || geographicDistribution)}
                        <div class="space-y-3">
                            <h4 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">{$t('assetDetail.classification')}</h4>

                            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                {#if geographicDistribution && Object.keys(geographicDistribution).length > 0}
                                    <div class="bg-gray-50 dark:bg-slate-700/30 rounded-lg p-3">
                                        <h5 class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">{$t('assetDetail.geoDistribution')}</h5>
                                        <GeographyMap data={geographicDistribution} height="280px" language={$currentLanguage}/>
                                    </div>
                                {/if}

                                {#if sectorDistribution && Object.keys(sectorDistribution).length > 0}
                                    <div class="bg-gray-50 dark:bg-slate-700/30 rounded-lg p-3">
                                        <h5 class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">{$t('assetDetail.sectorDistribution')}</h5>
                                        <SectorPieChart data={sectorDistribution} height="280px"/>
                                    </div>
                                {/if}
                            </div>
                        </div>
                    {:else if !classificationLoaded}
                        <div class="text-sm text-gray-500 dark:text-gray-400 italic">
                            {$t('assetDetail.classification')} — {$t('common.loading')}...
                        </div>
                    {:else}
                        <p class="text-sm text-gray-400 dark:text-gray-500">{$t('assetDetail.noClassification')}</p>
                    {/if}

                    <!-- Identifiers -->
                    {#if identifiersList.length > 0}
                        <div>
                            <h4 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2">{$t('assetDetail.identifiers')}</h4>
                            <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                                {#each identifiersList as [label, value]}
                                    <div class="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2">
                                        <span class="text-[10px] uppercase text-gray-400 dark:text-gray-500">{label}</span>
                                        <p class="text-sm font-mono text-gray-700 dark:text-gray-200">{value}</p>
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {:else}
                        <p class="text-sm text-gray-400 dark:text-gray-500">{$t('assetDetail.noIdentifiers')}</p>
                    {/if}

                    {#if providerAssignment}
                        <div>
                            <h4 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2">Provider</h4>
                            <div class="flex items-center gap-3 text-sm flex-wrap">
                                <span class="inline-flex items-center gap-1.5 font-medium text-gray-700 dark:text-gray-200">
                                    {#if providerIconUrl}
                                        <img src={providerIconUrl} alt="" class="w-4 h-4 rounded-sm object-contain" />
                                    {/if}
                                    {getAssetProviderName(providerAssignment.provider_code)}
                                </span>
                                <span class="text-gray-400">→</span>
                                <span class="font-mono text-gray-500 dark:text-gray-400">{providerAssignment.identifier} ({providerAssignment.identifier_type})</span>
                                {#if providerAssignment.last_fetch_at}
                                    <span class="text-xs text-gray-400 dark:text-gray-500">
                                        {$t('assets.provider.lastFetch')}: {new Date(String(providerAssignment.last_fetch_at)).toLocaleDateString()}
                                    </span>
                                {:else}
                                    <span class="text-xs text-gray-400 dark:text-gray-500">{$t('assets.provider.neverFetched')}</span>
                                {/if}
                            </div>
                        </div>
                    {/if}

                    <button class="text-xs text-libre-green hover:underline" onclick={() => { editDataForModal = buildEditData(); editModalOpen = true; }}>
                        {$t('assetDetail.editViaModal')} →
                    </button>
                </div>
            {/if}
        </div>
    {/if}

    <!-- ======================================================================= -->
    <!-- AssetModal for editing -->
    <!-- ======================================================================= -->
    {#if assetInfo}
        <AssetModal
                bind:open={editModalOpen}
                editMode={true}
                editData={editDataForModal}
                onupdated={handleAssetUpdated}
                onclose={() => editModalOpen = false}
        />

        <!-- FX Pair Add Modal (opened from FX warning) -->
        <FxPairAddModal
                bind:open={showFxPairAddModal}
                initialBase={assetInfo.currency}
                initialQuote={displayCurrency}
                oncreated={async () => {
                    showFxPairAddModal = false;
                    await loadFxPairSlugs();
                }}
                onclose={() => showFxPairAddModal = false}
        />
    {/if}
</div>

