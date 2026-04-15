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
    import {page} from '$app/stores';
    import {goto} from '$app/navigation';
    import {_ as t} from '$lib/i18n';
    import {get} from 'svelte/store';
    import {zodiosApi} from '$lib/api';
    import {goBack} from '$lib/stores/navigationStore';
    import {
        ArrowLeft, ArrowLeftRight, ChevronDown, Coins, ExternalLink, Info, Pencil, RefreshCw, RotateCw,
        Ruler, Settings, TrendingUp, X
    } from 'lucide-svelte';
    import AssetDataEditorSection from '$lib/components/assets/AssetDataEditorSection.svelte';
    import {toasts} from '$lib/stores/toastStore.svelte';
    import PriceChartFull from '$lib/components/charts/PriceChartFull.svelte';
    import type {EventMarker} from '$lib/components/charts/PriceChartFull.svelte';
    import ChartAestheticsSection from '$lib/components/charts/ChartAestheticsSection.svelte';
    import ChartSignalsSection from '$lib/components/charts/ChartSignalsSection.svelte';
    import type {SignalDataSummary} from '$lib/components/charts/ChartSignalsSection.svelte';
    import MeasurePanel from '$lib/components/charts/MeasurePanel.svelte';
    import SectorPieChart from '$lib/components/charts/SectorPieChart.svelte';
    import GeographyMap from '$lib/components/charts/GeographyMap.svelte';
    import AssetModal from '$lib/components/assets/AssetModal.svelte';
    import AssetIcon from '$lib/components/assets/AssetIcon.svelte';
    import AssetPriceSummary from '$lib/components/assets/AssetPriceSummary.svelte';
    import FxPairAddModal from '$lib/components/fx/FxPairAddModal.svelte';
    import PageSyncModal from '$lib/components/ui/PageSyncModal.svelte';
    import DateRangePicker from '$lib/components/ui/DateRangePicker.svelte';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import type {RenderedSignal, SignalConfig} from '$lib/charts/signals';
    import {signalFromConfig} from '$lib/charts/signals';
    import {getSettingsForPair, setPairSettings} from '$lib/stores/chartSettingsStore.svelte';
    import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/currencyStore';
    import {currentLanguage} from '$lib/stores/language';
    import type {ViewMode} from '$lib/components/charts/ChartToolbar.svelte';
    import {createResponsiveLayout} from '$lib/utils/responsiveLayout.svelte';
    import {getFxStore, apiResultToFxDataPoint} from '$lib/stores/fxStoreRegistry';
    import {getAssetTypeIconUrl, buildIdentifiersList} from '$lib/utils/assetTypes';
    import {ensureAssetProvidersCached, getAssetProviderIconUrl, getAssetProviderName} from '$lib/utils/providerHelpers';
    import type {AssetDetail, ProviderAssignmentFlat} from '$lib/types';
    import type {SignalLabelInfo} from '$lib/charts/signalLabel';
    import {buildOverlaySignalInfoMap} from '$lib/charts/signalLabel';
    import {loadComparisonAssetsData} from '$lib/charts/loadComparisonData';
    import {parseDateRangeFromUrl} from '$lib/utils/dateRangeFromUrl';
    import {fetchCurrentPrices} from '$lib/services/livePriceService';
    import {buildAssetSyncToast, buildFxSyncToast} from '$lib/utils/syncToastHelpers';
    import {COLORS} from '$lib/components/charts/lineChartHelpers';

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
    /** Stores either a raw message or an i18n key prefixed with `_i18n:` for reactive translation */
    let error: string | null = $state(null);
    let syncing = $state(false);
    let fxSyncing = $state(false);

    /** Reactively resolved error message — translates i18n keys when language changes */
    let errorMessage = $derived.by(() => {
        if (!error) return null;
        return error.startsWith('_i18n:') ? $t(error.slice(6)) : error;
    });

    // Date range (from query params if present, otherwise default 3M)
    const _initRange = parseDateRangeFromUrl($page.url.searchParams);
    let dateEnd = $state(_initRange.end);
    let dateStart = $state(_initRange.start);
    let activePreset: any = $state(_initRange.hasCustomRange ? null : '3M');

    let viewMode: ViewMode = $state('percentage');
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

    // Data editor state
    let savingEdit = $state(false);
    let editorDirtyCount = $state(0);
    let pendingPreviewSignal: RenderedSignal | null = $state(null);
    let assetDataEditorRef: AssetDataEditorSection | undefined = $state(undefined);

    let overlayDataVersion = $state(0);
    let editModalOpen = $state(false);

    // Edit data — computed on-demand when modal opens (NOT $derived, to avoid effect loops)
    let editDataForModal = $state<ReturnType<typeof buildEditData>>(null);

    // Cross-domain data for signals
    let allConfiguredFxSlugs: string[] = $state([]);
    let allAssets: Array<{ id: number; display_name: string; icon_url?: string | null; asset_type?: string | null; currency?: string }> = $state([]);

    // Classification data (loaded when has_metadata)
    let sectorDistribution: Record<string, number> | null = $state(null);
    let geographicDistribution: Record<string, number> | null = $state(null);
    let classificationLoaded = $state(false);

    // Provider icon for header badge
    let providerIconUrl = $state<string | null>(null);

    // FX pair add modal (opened from FX warning or banner)
    let showFxPairAddModal = $state(false);
    /** Pre-filled slug for FxPairAddModal (e.g. "EUR-RON" from banner) */
    let fxPairCreateSlug = $state('');

    // Live current price (from provider, only when dateEnd = today)
    let currentLivePrice = $state<number | null>(null);
    /** True when live price conversion to displayCurrency failed (pair exists but rate unavailable) */
    let livePriceConversionFailed = $state(false);

    // =========================================================================
    // Derived
    // =========================================================================

    /** True when the chart end date is today (or later) → show live price from provider */
    let isHeadToday = $derived(dateEnd >= new Date().toISOString().slice(0, 10));

    let lineData: LineDataPoint[] = $derived(chartData.map((p: any) => ({
        date: p.date,
        value: Number(p.close ?? 0),
        staleDays: Math.max(
            p.backward_fill_info?.days_back ?? 0,
            p.backward_fill_info?.fx_days_back ?? 0,
        ),
        fxStaleDays: p.backward_fill_info?.fx_days_back ?? 0,
        originalCurrency: p.original_currency ?? undefined,
        originalCurrencyFlag: p.original_currency ? getCurrencyInfo(p.original_currency).flag_emoji : undefined,
        originalValue: p.original_close != null ? Number(p.original_close) : undefined,
    })));

    let isScheduledInvestment = $derived(providerAssignment?.provider_code === 'scheduled_investment');
    let isManualOnly = $derived(!providerAssignment);

    /** First data point date — used for "no data before" banner */
    let firstDataDate = $derived(chartData.length > 0 ? chartData[0].date : null);
    /** True when the selected date range starts before the first available data point */
    let rangeStartsBeforeData = $derived(
        firstDataDate != null && dateStart < firstDataDate
    );

    /** First date with FX-converted data (original_close present) — null if no conversion active */
    let fxFirstConvertedDate = $derived.by(() => {
        if (!displayCurrency || !assetInfo || displayCurrency === assetInfo.currency) return null;
        for (const p of chartData) {
            if (p.original_close != null) return p.date as string;
        }
        return null;
    });

    /** True when conversion is active but earliest chart points lack FX rates */
    let hasFxDataGap = $derived.by(() => {
        if (!displayCurrency || !assetInfo || displayCurrency === assetInfo.currency) return false;
        if (fxConversionMissing) return false; // FX pair doesn't exist at all → different warning
        if (chartData.length === 0) return false;
        // Case 1: first chart point has no conversion but later points do (partial gap)
        if (fxFirstConvertedDate && chartData[0].original_close == null && fxFirstConvertedDate > chartData[0].date) return true;
        // Case 2: FX pair exists but NO chart point has original_close at all (0 rates, or all rates after window)
        // (chartData.length > 0 already guaranteed by the guard above)
        return !fxFirstConvertedDate;
    });

    /** Effective last price: live from provider when head = today, otherwise last chart close */
    let lastPrice = $derived.by(() => {
        if (isHeadToday && currentLivePrice != null) return currentLivePrice;
        if (chartData.length === 0) return null;
        const last = chartData[chartData.length - 1];
        return last?.close != null ? Number(last.close) : null;
    });

    let deltaPercent = $derived.by(() => {
        if (chartData.length < 2 || lastPrice == null) return null;
        const first = Number(chartData[0].close ?? 0);
        if (first === 0) return null;
        return ((lastPrice - first) / first) * 100;
    });

    let deltaAbs = $derived.by(() => {
        if (chartData.length < 2 || lastPrice == null) return null;
        const first = Number(chartData[0].close ?? 0);
        if (first === 0) return null;
        return lastPrice - first;
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

    /**
     * All FX pairs required by the page (main + comparison signals).
     * Each entry has slug, label, forAsset, and status.
     */
    interface RequiredFxPairInfo {
        slug: string;
        label: string;
        forAsset: string;
        forAssetIconUrl?: string | null;
        forAssetType?: string | null;
        status: 'ok' | 'missing' | 'no-data' | 'partial-gap';
        firstDate?: string;
    }

    let requiredFxPairs: RequiredFxPairInfo[] = $derived.by(() => {
        if (!displayCurrency) return [];
        const pairs: RequiredFxPairInfo[] = [];
        const seenSlugs = new Set<string>();

        // Helper to compute canonical slug
        const toSlug = (a: string, b: string) => {
            const [lo, hi] = a < b ? [a, b] : [b, a];
            return `${lo}-${hi}`;
        };

        // Main asset FX pair
        if (assetInfo && displayCurrency !== assetInfo.currency) {
            const slug = toSlug(assetInfo.currency, displayCurrency);
            const missing = !allConfiguredFxSlugs.includes(slug);
            let status: RequiredFxPairInfo['status'];
            if (missing) {
                status = 'missing';
            } else if (!fxFirstConvertedDate && chartData.length > 0) {
                status = 'no-data';
            } else if (hasFxDataGap && fxFirstConvertedDate) {
                status = 'partial-gap';
            } else {
                status = 'ok';
            }
            pairs.push({
                slug,
                label: slug.replace('-', '/'),
                forAsset: assetInfo.display_name,
                forAssetIconUrl: assetInfo.icon_url,
                forAssetType: assetInfo.asset_type,
                status,
                firstDate: fxFirstConvertedDate ?? undefined,
            });
            seenSlugs.add(slug);
        }

        // Comparison signal FX pairs
        for (const cfg of signals) {
            if (cfg.signalType !== 'asset-comparison') continue;
            const targetId = Number(cfg.params.assetId);
            if (!targetId || targetId === data.assetId) continue;
            const targetAsset = allAssets.find(a => a.id === targetId);
            if (!targetAsset?.currency || targetAsset.currency === displayCurrency) continue;
            const slug = toSlug(targetAsset.currency, displayCurrency);
            if (seenSlugs.has(slug)) continue;
            seenSlugs.add(slug);

            const missing = !allConfiguredFxSlugs.includes(slug);
            const convFailed = Boolean(cfg.params._conversionFailed);
            const hasData = Boolean(cfg.params._resolvedData);
            let status: RequiredFxPairInfo['status'];
            if (missing) {
                status = 'missing';
            } else if (convFailed || !hasData) {
                status = 'no-data';
            } else {
                status = 'ok';
            }
            pairs.push({
                slug,
                label: slug.replace('-', '/'),
                forAsset: targetAsset.display_name,
                forAssetIconUrl: targetAsset.icon_url,
                forAssetType: targetAsset.asset_type,
                status,
            });
        }

        return pairs;
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
        ...(pendingPreviewSignal ? [pendingPreviewSignal] : []),
    ]);

    // Signal label info for MeasurePanel and PriceChartFull tooltip
    let mainSignalInfo: SignalLabelInfo = $derived({
        label: assetInfo?.display_name ?? '',
        iconUrl: assetInfo?.icon_url,
        assetType: assetInfo?.asset_type,
        isCrown: true,
        color: COLORS.lineLight,
    });

    let overlaySignalInfoMap = $derived(buildOverlaySignalInfoMap(overlaySignals));

    // Event markers for the chart (own events + comparison asset events)
    let chartEventMarkers: EventMarker[] = $derived.by(() => {
        const markers: EventMarker[] = [];

        // Own asset events
        for (const ev of events) {
            markers.push({
                date: ev.date,
                type: ev.type ?? 'OTHER',
                value: ev.value?.amount != null ? Number(ev.value.amount) : undefined,
                currency: ev.value?.code ?? assetInfo?.currency ?? '',
                notes: ev.notes ?? undefined,
            });
        }

        // Comparison asset events
        for (const [aid, evts] of comparisonEvents) {
            const targetAsset = allAssets.find(a => a.id === aid);
            const label = targetAsset?.display_name ?? `Asset #${aid}`;
            // Find signal color for this comparison asset
            const sigColor = overlaySignals.find(s => s.label === label)?.color;
            for (const ev of evts) {
                markers.push({
                    date: ev.date,
                    type: ev.type ?? 'OTHER',
                    value: ev.value?.amount != null ? Number(ev.value.amount) : undefined,
                    currency: ev.value?.code ?? '',
                    notes: ev.notes ?? undefined,
                    assetLabel: label,
                    signalColor: sigColor,
                });
            }
        }

        return markers;
    });

    // Summary data per signal (point count, event counts, first date) — for ChartSignalsSection
    let signalSummaries: Map<string, SignalDataSummary> = $derived.by(() => {
        void overlayDataVersion; // recompute when overlay data changes (e.g. after sync)
        const result = new Map<string, SignalDataSummary>();
        for (const cfg of signals) {
            if (cfg.signalType === 'asset-comparison') {
                const targetId = Number(cfg.params.assetId);
                if (!targetId) continue;
                const resolvedData = cfg.params._resolvedData as Array<{date: string; value: number}> | undefined;
                const evts = comparisonEvents.get(targetId) ?? [];
                const eventCounts: Record<string, number> = {};
                for (const ev of evts) {
                    const t = ev.type ?? 'OTHER';
                    eventCounts[t] = (eventCounts[t] ?? 0) + 1;
                }
                result.set(cfg.id, {
                    pointCount: resolvedData?.length ?? 0,
                    eventCounts,
                    firstDate: resolvedData && resolvedData.length > 0 ? resolvedData[0].date : null,
                });
            } else if (cfg.signalType === 'fx-pair') {
                const pairSlug = String(cfg.params.pairSlug || '');
                if (!pairSlug) continue;
                try {
                    const store = getFxStore(pairSlug);
                    const storeData = store.getAllSorted();
                    result.set(cfg.id, {
                        pointCount: storeData.length,
                        eventCounts: {},
                        firstDate: storeData.length > 0 ? storeData[0].date : null,
                    });
                } catch {
                    result.set(cfg.id, { pointCount: 0, eventCounts: {}, firstDate: null });
                }
            }
        }
        return result;
    });

    // =========================================================================
    // Lifecycle
    // =========================================================================

    /** Full page reload: fetches all data for the current assetId */
    async function reloadPage() {
        loading = true;
        error = null;
        // Reset state for new asset
        assetInfo = null;
        providerAssignment = null;
        chartData = [];
        events = [];
        comparisonEvents = new Map();
        currentLivePrice = null;
        livePriceConversionFailed = false;
        sectorDistribution = null;
        geographicDistribution = null;
        classificationLoaded = false;
        providerIconUrl = null;

        await Promise.all([
            ensureCurrenciesLoaded(get(currentLanguage)),
            ensureAssetProvidersCached(),
            loadAssetInfo(),
            loadProviderAssignment(),
            loadChartData(),
            loadFxPairSlugs(),
            loadAssetList(),
        ]);
        // Resolve provider icon after data loads (use local ref to avoid TS narrowing)
        const info = assetInfo as AssetDetail | null;
        if (info?.provider_code) {
            providerIconUrl = getAssetProviderIconUrl(info.provider_code);
        }
        // Load classification data if available
        if (info?.has_metadata) {
            await loadClassificationData();
        } else {
            classificationLoaded = true;
        }
        // Load comparison asset data after initial data is ready
        await maybeLoadComparison();
    }

    // Track previous asset id for same-route navigation detection (plain var — not $state)
    let _prevAssetId: number | undefined;

    onMount(() => {
        _prevAssetId = data.assetId;
        reloadPage();
    });

    // Re-load everything when navigating to a different asset (same route pattern)
    $effect(() => {
        const newId = data.assetId;
        if (_prevAssetId !== undefined && newId !== _prevAssetId) {
            _prevAssetId = newId;
            reloadPage();
        }
    });

    $effect(() => {
        const el = filterBarRef;
        if (!el) return;
        layout.attach(el);
        return () => layout.detach();
    });

    // Live current price polling — only when chart head date includes today
    // Re-runs when displayCurrency or assetInfo changes (to reconvert)
    $effect(() => {
        const id = assetInfo?.id;
        const nativeCurrency = assetInfo?.currency;
        const targetCurrency = displayCurrency;
        const fxMissing = fxConversionMissing;
        if (!isHeadToday || !id) {
            currentLivePrice = null;
            livePriceConversionFailed = false;
            return;
        }
        // Fetch immediately, then poll every 30s
        _fetchLivePrice(id, nativeCurrency ?? '', targetCurrency, fxMissing);
        const timer = setInterval(() => _fetchLivePrice(id, nativeCurrency ?? '', targetCurrency, fxMissing), 30_000);
        return () => clearInterval(timer);
    });

    async function _fetchLivePrice(assetId: number, nativeCurrency: string, targetCurrency: string, fxMissing: boolean) {
        try {
            const results = await fetchCurrentPrices([assetId]);
            if (results.length === 0 || results[0].value == null) return;
            const nativeValue = results[0].value;

            // No conversion needed
            if (!targetCurrency || !nativeCurrency || targetCurrency === nativeCurrency || fxMissing) {
                currentLivePrice = nativeValue;
                livePriceConversionFailed = false;
                return;
            }

            // Convert via FX API
            try {
                const today = new Date().toISOString().slice(0, 10);
                const convResponse = await zodiosApi.convert_currency_bulk_api_v1_fx_currencies_convert_post([{
                    from_amount: {code: nativeCurrency, amount: String(nativeValue)},
                    to: targetCurrency,
                    date_range: {start: today, end: today},
                }]);
                const convResults = (convResponse as any)?.results ?? [];
                if (convResults.length > 0 && convResults[0].to_amount?.amount != null) {
                    currentLivePrice = parseFloat(convResults[0].to_amount.amount);
                    livePriceConversionFailed = false;
                } else {
                    // Conversion returned no results — fallback to native
                    currentLivePrice = nativeValue;
                    livePriceConversionFailed = true;
                }
            } catch {
                // FX conversion failed — fallback to native price
                currentLivePrice = nativeValue;
                livePriceConversionFailed = true;
            }
        } catch (e: any) {
            // Non-blocking: keep last known value or chart fallback
        }
    }


    // Reload chart data when displayCurrency changes (currency conversion)
    let prevDisplayCurrency = $state('');
    $effect(() => {
        const cur = displayCurrency;
        if (!cur || !prevDisplayCurrency) {
            // First run or not yet initialized — just track, don't reload
            prevDisplayCurrency = cur;
            return;
        }
        if (cur !== prevDisplayCurrency) {
            prevDisplayCurrency = cur;
            loadChartData().then(() => maybeLoadComparison());
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
                target_currency: (displayCurrency && assetInfo?.currency && displayCurrency !== assetInfo.currency)
                    ? displayCurrency : undefined,
            }]);
            const result = (response as any)?.items?.[0];
            if (result) {
                chartData = result.prices ?? [];
                events = result.events ?? [];
            } else {
                chartData = [];
                events = [];
            }
            // Show "no data" banner when query succeeded but returned empty prices
            if (chartData.length === 0 && !error) {
                error = '_i18n:assetDetail.noData';
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
                currency: a.currency ?? undefined,
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

    /**
     * Load comparison asset data if any comparison signals are configured.
     * Called explicitly from onMount, handleRefresh, handleDateRangeChange, handleSignalsChange.
     */
    async function maybeLoadComparison() {
        const compSignals = signals.filter(s => s.signalType === 'asset-comparison');
        if (compSignals.length === 0 || lineData.length === 0) return;
        try {
            comparisonEvents = await loadComparisonAssetsData(
                compSignals,
                {start: dateStart, end: dateEnd},
                allAssets,
                comparisonEvents,
                data.assetId,
                displayCurrency || undefined,
            );
            overlayDataVersion++;
        } catch (e) { console.error('Failed to load comparison asset data:', e); }
    }


    // =========================================================================
    // Actions
    // =========================================================================


    async function handleRefresh() {
        await loadChartData();
        // Invalidate FX overlay stores so they refetch updated rates
        for (const pair of requiredFxPairs) {
            if (pair.status === 'missing') continue;
            const store = getFxStore(pair.slug);
            store.invalidateAll();
            const parts = pair.slug.split('-');
            try {
                const resp = await zodiosApi.convert_currency_bulk_api_v1_fx_currencies_convert_post([{
                    from_amount: {code: parts[0], amount: 1},
                    to: parts[1],
                    date_range: {start: dateStart, end: dateEnd},
                }]);
                const results = (resp as any)?.results || [];
                const points = results.map((r: any) => apiResultToFxDataPoint(r));
                store.merge(points);
            } catch { /* best effort */ }
        }
        overlayDataVersion++;
        await maybeLoadComparison();
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

    // Page sync modal state
    let showPageSyncModal = $state(false);

    /** Collect all assets and FX pairs for sync-all modal */
    let syncAllAssets = $derived.by(() => {
        const items: Array<{id: number; display_name: string; icon_url?: string | null; asset_type?: string | null; provider_code?: string | null}> = [];
        // Main asset
        if (assetInfo?.provider_code) {
            items.push({id: data.assetId, display_name: assetInfo.display_name, icon_url: assetInfo.icon_url, asset_type: assetInfo.asset_type ?? null, provider_code: assetInfo.provider_code});
        }
        // Comparison assets with provider
        for (const cfg of signals) {
            if (cfg.signalType !== 'asset-comparison') continue;
            const aid = Number(cfg.params.assetId);
            if (!aid || aid === data.assetId) continue;
            const meta = allAssets.find(a => a.id === aid);
            if (meta) {
                items.push({id: aid, display_name: meta.display_name, icon_url: meta.icon_url ?? undefined, asset_type: (meta as any).asset_type ?? null, provider_code: 'unknown'});
            }
        }
        return items;
    });

    let syncAllFxPairs = $derived(
        requiredFxPairs.filter(p => p.status !== 'missing').map(p => p.slug)
    );

    function handleSync() {
        showPageSyncModal = true;
    }

    async function handlePageSyncComplete() {
        await handleRefresh();
        await reloadMetadata();
        await maybeLoadComparison();
        overlayDataVersion++;
    }

    async function handleFxPairCreated({ base, quote, hasRealProvider }: { base: string; quote: string; hasRealProvider: boolean }) {
        const wasForComparison = !!fxPairCreateSlug;
        showFxPairAddModal = false;
        fxPairCreateSlug = '';
        await loadFxPairSlugs();
        // Only update display currency when creating the main asset's FX pair
        if (!wasForComparison) {
            const assetCur = assetInfo?.currency ?? '';
            const newQuote = assetCur === base ? quote : base;
            if (newQuote !== assetCur) {
                displayCurrency = newQuote;
            }
        }
        if (hasRealProvider) {
            toasts.success($t('assetDetail.fxPairCreatedSynced'));
        }
        await handleRefresh();
        await maybeLoadComparison();
        overlayDataVersion++;
    }

    async function handleDateRangeChange(newStart: string, newEnd: string) {
        dateStart = newStart;
        dateEnd = newEnd;
        // Sync URL so browser back/forward preserves the date range
        const url = new URL(window.location.href);
        url.searchParams.set('start', dateStart);
        url.searchParams.set('end', dateEnd);
        history.replaceState(history.state, '', url.toString());
        await loadChartData();
        await maybeLoadComparison();
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
        maybeLoadComparison(); // fire-and-forget: load data for newly added comparison signals
    }

    async function handleSyncAsset(assetId: number) {
        try {
            const response = await zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post([{
                asset_id: assetId,
                date_range: {start: dateStart, end: dateEnd},
            }]);
            const r = (response as any)?.results?.[0];
            const tr = get(t);
            if (r) {
                const toast = buildAssetSyncToast(r, tr('common.sync'));
                toasts[toast.variant](toast.message);
            } else {
                toasts.error(`${tr('common.sync')} — no response`);
            }
        } catch (e: any) {
            toasts.error('Sync failed: ' + (e?.message || 'unknown'));
        }
        // Reload comparison data for the synced asset, then trigger UI update
        await maybeLoadComparison();
        overlayDataVersion++;
    }

    function handleDetailAsset(assetId: number) {
        goto(`/assets/${assetId}?start=${dateStart}&end=${dateEnd}`);
    }

    async function handleSyncPair(slug: string) {
        fxSyncing = true;
        try {
            const syncResponse = await zodiosApi.sync_rates_api_v1_fx_currencies_sync_post({
                pairs: [slug],
                start: dateStart,
                end: dateEnd,
            });
            // Refetch FX data into store after sync (invalidate + reload)
            const store = getFxStore(slug);
            store.invalidateAll();
            const parts = slug.split('-');
            const base = parts[0], quote = parts[1];
            try {
                const response = await zodiosApi.convert_currency_bulk_api_v1_fx_currencies_convert_post([{
                    from_amount: {code: base, amount: 1},
                    to: quote,
                    date_range: {start: dateStart, end: dateEnd},
                }]);
                const results = (response as any)?.results || [];
                const points = results.map((r: any) => apiResultToFxDataPoint(r));
                store.merge(points);
            } catch { /* convert may fail if no data yet */ }
            overlayDataVersion++;
            // Reload asset chart data to apply updated FX conversion
            await loadChartData();
            const tr = get(t);
            const r = (syncResponse as any)?.results?.[0];
            const toast = buildFxSyncToast(r, slug, tr);
            toasts[toast.variant](toast.message);
        } catch (e: any) {
            toasts.error('FX sync failed: ' + (e?.message || 'unknown'));
        } finally {
            fxSyncing = false;
        }
    }

    function handleDetailPair(slug: string) {
        goto(`/fx/${slug}?start=${dateStart}&end=${dateEnd}`);
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
                    {:else}
                        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">
                            ✏️ Manual
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
            <span>⚠️</span> <span>{errorMessage}</span>
            <button class="ml-auto text-xs px-2 py-1 bg-amber-100 dark:bg-amber-900/40 rounded hover:bg-amber-200" onclick={() => error = null}>{$t('common.close')}</button>
        </div>
    {/if}

    <!-- Data availability banner: selected range starts before first data point -->
    {#if rangeStartsBeforeData && !loading && !error && assetInfo}
        {@const startDow = new Date(dateStart + 'T00:00:00').getDay()}
        {@const isWeekendStart = startDow === 0 || startDow === 6}
        <div class="bg-sky-50 dark:bg-sky-900/20 border border-sky-200 dark:border-sky-800 rounded-xl px-4 py-2.5 text-xs text-sky-700 dark:text-sky-400 flex items-center gap-2 flex-wrap">
            <span>📊</span>
            {#if assetInfo.icon_url}
                <img src={assetInfo.icon_url} alt="" class="w-4 h-4 rounded-sm object-contain shrink-0"/>
            {:else if assetInfo.asset_type}
                <img src={getAssetTypeIconUrl(assetInfo.asset_type)} alt="" class="w-4 h-4 object-contain shrink-0"/>
            {/if}
            <span class="font-medium">{assetInfo.display_name}</span>
            <span class="opacity-80">— {$t('assetDetail.dataAvailableFrom', {values: {date: firstDataDate}})}</span>
            {#if isWeekendStart}
                <span class="text-sky-500 dark:text-sky-300 italic">({$t('assetDetail.weekendHint') ?? 'selected start date falls on a weekend — try adjusting'})</span>
            {/if}
        </div>
    {/if}

    <!-- FX pair status banners: one per problematic FX pair (main + comparison) -->
    {#if !loading && !error}
        {#each requiredFxPairs.filter(p => p.status !== 'ok') as pair (pair.slug)}
            {@const parts = pair.slug.split('-')}
            {@const baseFlag = getCurrencyInfo(parts[0]).flag_emoji}
            {@const quoteFlag = getCurrencyInfo(parts[1]).flag_emoji}
            {@const isMissing = pair.status === 'missing'}
            {@const isAmber = isMissing || pair.status === 'no-data'}
            <div class="{isAmber ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-400' : 'bg-sky-50 dark:bg-sky-900/20 border-sky-200 dark:border-sky-800 text-sky-700 dark:text-sky-400'} border rounded-xl px-4 py-2.5 text-xs flex flex-col sm:flex-row items-start sm:items-center gap-2">
                <!-- Left: icon + pair slug + message + asset -->
                <div class="flex items-center gap-2 flex-wrap min-w-0">
                    <Coins size={14} class="shrink-0"/>
                    <span class="font-medium inline-flex items-center gap-1">
                        <span class="emoji-flag">{baseFlag}</span> {parts[0]}
                        <ArrowLeftRight size={10} class="shrink-0"/>
                        <span class="emoji-flag">{quoteFlag}</span> {parts[1]}
                    </span>
                    <span class="opacity-80">—
                        {#if isMissing}
                            {$t('assetDetail.fxPairMissing', {values: {base: parts[0], quote: parts[1]}})}
                        {:else if pair.status === 'no-data'}
                            {$t('assetDetail.fxPairNoRates', {values: {pair: pair.label}})}
                        {:else}
                            {$t('assetDetail.fxDataAvailableFrom', {values: {date: pair.firstDate ?? ''}})}
                        {/if}
                    </span>
                    <span class="inline-flex items-center gap-1 text-[10px] opacity-60">
                        {#if pair.forAssetIconUrl}
                            <img src={pair.forAssetIconUrl} alt="" class="w-3.5 h-3.5 rounded-sm object-contain"/>
                        {:else if pair.forAssetType}
                            <img src={getAssetTypeIconUrl(pair.forAssetType)} alt="" class="w-3.5 h-3.5 object-contain"/>
                        {/if}
                        ({pair.forAsset})
                    </span>
                </div>
                <!-- Right: action buttons (bottom-right in mobile, inline-right in desktop) -->
                <div class="flex items-center gap-1 self-end sm:self-auto sm:ml-auto">
                    {#if isMissing}
                        <button
                            class="inline-flex items-center gap-1 px-2 py-0.5 rounded {isAmber ? 'bg-amber-100 dark:bg-amber-800/40 hover:bg-amber-200 dark:hover:bg-amber-700/40' : 'bg-sky-100 dark:bg-sky-800/40 hover:bg-sky-200 dark:hover:bg-sky-700/40'} transition-colors font-medium"
                            onclick={() => { fxPairCreateSlug = pair.slug; showFxPairAddModal = true; }}
                        >
                            <Coins size={13}/> {$t('assetDetail.addFxPair')}
                        </button>
                    {:else}
                        <a href="/fx/{pair.slug}?start={dateStart}&end={dateEnd}"
                           class="inline-flex items-center gap-1 px-2 py-0.5 rounded {isAmber ? 'bg-amber-100 dark:bg-amber-800/40 hover:bg-amber-200 dark:hover:bg-amber-700/40' : 'bg-sky-100 dark:bg-sky-800/40 hover:bg-sky-200 dark:hover:bg-sky-700/40'} transition-colors">
                            <Coins size={13}/>
                        </a>
                        <button
                            class="inline-flex items-center gap-1 px-2 py-0.5 rounded {isAmber ? 'bg-amber-100 dark:bg-amber-800/40 hover:bg-amber-200 dark:hover:bg-amber-700/40' : 'bg-sky-100 dark:bg-sky-800/40 hover:bg-sky-200 dark:hover:bg-sky-700/40'} transition-colors font-medium"
                            onclick={() => handleSyncPair(pair.slug)}
                        >
                            <RotateCw size={13} class={fxSyncing ? 'animate-spin' : ''}/> {$t('common.sync')}
                        </button>
                    {/if}
                </div>
            </div>
        {/each}
    {/if}

    <!-- ======================================================================= -->
    <!-- Filter bar -->
    <!-- wide:     [ datepicker  price-summary ─── actions-2×2 ]                        -->
    <!-- tablet:   [ datepicker  price-summary ] [ actions-2×2 ]  side by side           -->
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
        <!-- Filters block: wide+tablet = row (side by side), tablet-s = column (stacked), mobile = centered -->
        <div class="flex gap-3 {layout.layoutMode === 'mobile' ? 'flex-col items-center'
             : layout.layoutMode === 'tablet-s' ? 'flex-col items-start flex-1'
             : 'flex-row items-center flex-1'}">
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
                        onAddFxPair={() => { fxPairCreateSlug = ''; showFxPairAddModal = true; }}
                        {livePriceConversionFailed}
                        onsyncfx={fxPairSlug ? () => handleSyncPair(fxPairSlug) : undefined}
                        {fxSyncing}
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
                {$t('common.signals')}
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
                        onsyncpair={handleSyncPair}
                        ondetailpair={handleDetailPair}
                        onsyncasset={handleSyncAsset}
                        ondetailasset={handleDetailAsset}
                        {signalSummaries}
                        {dateStart}
                        {displayCurrency}
                        configuredFxSlugs={allConfiguredFxSlugs}
                        oncreatefxpair={(slug) => { fxPairCreateSlug = slug; showFxPairAddModal = true; }}
                        onsyncfxpair={handleSyncPair}
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
                            title={measureMode ? $t('common.exitMeasure') : $t('common.addMeasure')}
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
                                pendingPreviewSignal = null;
                                if (savedPanelStates) { showAesthetics = savedPanelStates.aesthetics; showMeasures = savedPanelStates.measures; showSignals = savedPanelStates.signals; savedPanelStates = null; }
                            } else {
                                savedPanelStates = {aesthetics: showAesthetics, measures: showMeasures, signals: showSignals};
                                showAesthetics = false; showMeasures = false; showSignals = false; showDataEditor = true;
                            }
                        }}
                            title={showDataEditor ? $t('common.closeEditor') : $t('assetDetail.editData')}
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
                        eventMarkers={chartEventMarkers}
                        {overlaySignalInfoMap}
                        mainIconUrl={assetInfo?.icon_url}
                        mainAssetType={assetInfo?.asset_type}
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
                        staleLabel={$t('chart.tooltip.stale')}
                        fxStaleLabel={$t('chart.tooltip.fxStale')}
                        displayCurrency={displayCurrency !== assetInfo?.currency ? displayCurrency : undefined}
                        displayCurrencyFlag={displayCurrency !== assetInfo?.currency ? getCurrencyInfo(displayCurrency).flag_emoji : undefined}
                        mainCurrency={assetInfo?.currency ?? undefined}
                        mainCurrencyFlag={assetInfo?.currency ? getCurrencyInfo(assetInfo.currency).flag_emoji : undefined}
                        onDblClick={(date) => {
                            if (showDataEditor && assetDataEditorRef) {
                                assetDataEditorRef.scrollToDate(date, 'prices');
                            }
                        }}
                        onEventDblClick={(date) => {
                            if (showDataEditor && assetDataEditorRef) {
                                assetDataEditorRef.scrollToDate(date, 'events');
                            }
                        }}
                />
            </div>
        {:else}
            <div class="h-96 flex items-center justify-center">
                <div class="text-center">
                    {#if isManualOnly}
                        <p class="text-gray-400 dark:text-gray-500 mb-3">{$t('assetDetail.noDataManual')}</p>
                        <div class="flex items-center gap-2 justify-center">
                            <button class="px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors"
                                    onclick={() => {
                                        savedPanelStates = {aesthetics: showAesthetics, measures: showMeasures, signals: showSignals};
                                        showAesthetics = false; showMeasures = false; showSignals = false; showDataEditor = true;
                                    }}>
                                <Pencil class="inline mr-1" size={14}/> {$t('fxDetail.insertManually')}
                            </button>
                            <button class="px-4 py-2 text-sm bg-slate-200 dark:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-500 transition-colors"
                                    onclick={() => { editDataForModal = buildEditData(); editModalOpen = true; }}>
                                {$t('common.edit')}
                            </button>
                        </div>
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
                        onclick={() => { showDataEditor = false; pendingPreviewSignal = null; if (savedPanelStates) { showAesthetics = savedPanelStates.aesthetics; showMeasures = savedPanelStates.measures; showSignals = savedPanelStates.signals; savedPanelStates = null; } }}
                        title={$t('common.closeEditor')}>✕</button>
            </div>
            <div class="px-4 py-4">
                <AssetDataEditorSection
                        bind:this={assetDataEditorRef}
                        assetId={data.assetId}
                        {chartData}
                        {events}
                        bind:saving={savingEdit}
                        bind:dirtyCount={editorDirtyCount}
                        onsave={async (expandedRange) => {
                            showDataEditor = false;
                            pendingPreviewSignal = null;
                            if (savedPanelStates) { showAesthetics = savedPanelStates.aesthetics; showMeasures = savedPanelStates.measures; showSignals = savedPanelStates.signals; savedPanelStates = null; }
                            if (expandedRange) { dateStart = expandedRange.start; dateEnd = expandedRange.end; }
                            await handleRefresh();
                        }}
                        oncancel={() => {
                            showDataEditor = false;
                            pendingPreviewSignal = null;
                            if (savedPanelStates) { showAesthetics = savedPanelStates.aesthetics; showMeasures = savedPanelStates.measures; showSignals = savedPanelStates.signals; savedPanelStates = null; }
                        }}
                        onpendingchange={(sig) => pendingPreviewSignal = sig}
                />
            </div>
        </div>
    {/if}

    <!-- ======================================================================= -->
    <!-- Foldable Panel: Measures -->
    <!-- ======================================================================= -->
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
        <div
                class="flex items-center justify-between px-4 py-2.5 cursor-pointer select-none hover:bg-gray-50 dark:hover:bg-slate-750 transition-colors rounded-t-xl"
                role="button"
                tabindex="0"
                data-testid="asset-detail-measures-toggle"
                onclick={() => showMeasures = !showMeasures}
                onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); showMeasures = !showMeasures; } }}
        >
            <div class="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-200">
                <Ruler class="text-violet-500" size={15}/>
                {$t('common.measures')}
                {#if measureMode}
                    <span class="text-[10px] px-1.5 py-0.5 bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400 rounded-full">{$t('measure.active')}</span>
                {/if}
            </div>
            <div class="flex items-center gap-1.5">
                <button
                        type="button"
                        class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-md
                               bg-violet-50 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400
                               hover:bg-violet-100 dark:hover:bg-violet-900/50
                               transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        disabled={lineData.length < 2}
                        onclick={(e) => { e.stopPropagation(); showMeasures = true; measurePanel?.addMeasureFromChartData(); }}
                        title={$t('common.addMeasure')}
                >
                    <span class="text-sm leading-none">+</span>
                    <span class="hidden sm:inline">{$t('common.addMeasure')}</span>
                </button>
                <ChevronDown class="transition-transform text-gray-400 {showMeasures ? 'rotate-180' : ''}" size={15}/>
            </div>
        </div>
        <div class={showMeasures ? "px-4 pb-4 border-t border-gray-100 dark:border-slate-700 pt-3" : "hidden"} data-testid="asset-detail-measures-panel">
            <MeasurePanel
                    bind:this={measurePanel}
                    chartData={lineData}
                    onmeasuremodechange={(active) => measureMode = active}
                    onmeasureschange={(m) => measureSignals = m}
                    overlaySignals={overlaySignals}
                    {mainSignalInfo}
                    {viewMode}
                    displayCurrency={displayCurrency !== assetInfo?.currency ? displayCurrency : undefined}
                    displayCurrencyFlag={displayCurrency !== assetInfo?.currency ? getCurrencyInfo(displayCurrency).flag_emoji : undefined}
                    mainCurrency={assetInfo?.currency ?? undefined}
                    mainCurrencyFlag={assetInfo?.currency ? getCurrencyInfo(assetInfo.currency).flag_emoji : undefined}
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
                            <h4 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">{$t('common.classification')}</h4>

                            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                {#if geographicDistribution && Object.keys(geographicDistribution).length > 0}
                                    <div class="bg-gray-50 dark:bg-slate-700/30 rounded-lg p-3">
                                        <h5 class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">{$t('common.geoDistribution')}</h5>
                                        <GeographyMap data={geographicDistribution} height="280px" language={$currentLanguage}/>
                                    </div>
                                {/if}

                                {#if sectorDistribution && Object.keys(sectorDistribution).length > 0}
                                    <div class="bg-gray-50 dark:bg-slate-700/30 rounded-lg p-3">
                                        <h5 class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">{$t('common.sectorDistribution')}</h5>
                                        <SectorPieChart data={sectorDistribution} height="280px"/>
                                    </div>
                                {/if}
                            </div>
                        </div>
                    {:else if !classificationLoaded}
                        <div class="text-sm text-gray-500 dark:text-gray-400 italic">
                            {$t('common.classification')} — {$t('common.loading')}...
                        </div>
                    {:else}
                        <p class="text-sm text-gray-400 dark:text-gray-500">{$t('assetDetail.noClassification')}</p>
                    {/if}

                    <!-- Identifiers -->
                    {#if identifiersList.length > 0}
                        <div>
                            <h4 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2">{$t('common.identifiers')}</h4>
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

        <!-- FX Pair Add Modal (opened from FX warning or banner) -->
        {@const createParts = fxPairCreateSlug ? fxPairCreateSlug.split('-') : []}
        {@const createBase = createParts.length === 2 ? createParts[0] : assetInfo.currency}
        {@const createQuote = createParts.length === 2 ? createParts[1] : (displayCurrency !== assetInfo.currency ? displayCurrency : '')}
        <FxPairAddModal
                bind:open={showFxPairAddModal}
                readonlyBase={!fxPairCreateSlug}
                initialBase={createBase}
                initialQuote={createQuote}
                dateStart={dateStart}
                dateEnd={dateEnd}
                oncreated={handleFxPairCreated}
                onclose={() => { showFxPairAddModal = false; fxPairCreateSlug = ''; }}
        />
    {/if}

    <!-- Page Sync Modal (sync all assets + FX pairs) -->
    {#if assetInfo}
        <PageSyncModal
                bind:open={showPageSyncModal}
                {dateStart}
                {dateEnd}
                assets={syncAllAssets}
                fxPairs={syncAllFxPairs}
                onsynced={handlePageSyncComplete}
                onclose={() => showPageSyncModal = false}
        />
    {/if}
</div>

