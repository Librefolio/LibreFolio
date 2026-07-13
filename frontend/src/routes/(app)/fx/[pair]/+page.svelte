<script lang="ts">
    /**
     * FX Pair Detail Page — Redesigned v2
     *
     * Layout:
     * - Header: pair info + invert
     * - Filter bar: 3-column (DateRangePicker | pair summary | 2×2 button matrix)
     * - Chart: PriceChartFull (unified 2-grid with dataZoom) + edit/measure buttons overlay
     * - Foldable panels: Aesthetics (above chart area), Measures, Signals (below chart)
     * - Data Editor: shown via edit button on chart
     * - Provider Config: via modal (not inline panel)
     *
     * Uses Svelte 5 runes. Replaces old FxEditSection with FxDataEditorSection.
     */
    import {onMount, tick} from 'svelte';
    import {goto} from '$app/navigation';
    import {page} from '$app/stores';
    import {_ as t} from '$lib/i18n';
    import {get} from 'svelte/store';
    import {zodiosApi} from '$lib/api';
    import {goBack} from '$lib/stores/app/navigationStore';
    import {ArrowLeft, ArrowLeftRight, ChevronDown, Pencil, RefreshCw, RotateCw, Ruler, Settings, TrendingUp, Wrench, X} from 'lucide-svelte';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import PageSyncModal from '$lib/components/ui/modals/PageSyncModal.svelte';
    import {DataQualityBanner} from '$lib/components/ui/feedback';
    import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';
    import PriceChartFull from '$lib/components/charts/PriceChartFull.svelte';
    import type {EventMarker} from '$lib/components/charts/PriceChartFull.svelte';
    import ChartAestheticsSection from '$lib/components/charts/ChartAestheticsSection.svelte';
    import ChartSignalsSection from '$lib/components/charts/ChartSignalsSection.svelte';
    import type {SignalDataSummary} from '$lib/components/charts/ChartSignalsSection.svelte';
    import MeasurePanel from '$lib/components/charts/MeasurePanel.svelte';
    import FxDataEditorSection from '$lib/components/fx/FxDataEditorSection.svelte';
    import FxPairAddModal from '$lib/components/fx/FxPairAddModal.svelte';
    import FxPriceSummary from '$lib/components/fx/FxPriceSummary.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import DateRangePicker from '$lib/components/ui/date/DateRangePicker.svelte';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import type {RenderedSignal, SignalConfig} from '$lib/charts/signals';
    import {signalFromConfig} from '$lib/charts/signals';
    import {getSettingsForPair, setPairSettings} from '$lib/stores/chartSettingsStore.svelte';
    import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {currentLanguage} from '$lib/stores/app/language';
    import type {ViewMode} from '$lib/components/charts/ChartToolbar.svelte';
    import {ensureFxRangeLoaded, type FxDataPoint, getFxStore} from '$lib/stores/fxStoreRegistry';
    import {setCardInverted} from '$lib/stores/fx/fxCardInversionStore';
    import {formatProviderText, formatSyncDetail} from '$lib/utils/providerHelpers';
    import type {LayoutMode} from '$lib/utils/layout/responsiveLayout.svelte';
    import PageToolbar from '$lib/components/ui/toolbar/PageToolbar.svelte';
    import {replaceHistoryDateRange} from '$lib/utils/url/dateRangeUrl';
    import type {SignalLabelInfo} from '$lib/charts/signalLabel';
    import {buildOverlaySignalInfoMap} from '$lib/charts/signalLabel';
    import {loadComparisonAssetsData} from '$lib/charts/loadComparisonData';
    import {getStart, getEnd, setDateRange, resolveDateSentinel, isMaxSentinel} from '$lib/stores/dateRangeStore.svelte';
    import {buildAssetSyncToast, buildFxSyncToast} from '$lib/utils/sync/syncToastHelpers';
    import {COLORS} from '$lib/components/charts/lineChartHelpers';

    // =========================================================================
    // Page data
    // =========================================================================

    interface Props {
        data: {
            urlBase: string;
            urlQuote: string;
            canonicalBase: string;
            canonicalQuote: string;
            canonicalSlug: string;
            inverted: boolean;
        };
    }

    let {data}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let chartData: FxDataPoint[] = $state([]);
    let loading = $state(true);
    /** Stores either a raw message or an i18n key prefixed with `_i18n:` for reactive translation */
    let error: string | null = $state(null);
    let syncing = $state(false);

    /** Reactively resolved error message — translates i18n keys when language changes */
    let errorMessage = $derived.by(() => {
        if (!error) return null;
        return error.startsWith('_i18n:') ? $t(error.slice(6)) : error;
    });

    // Confirm modal for swap while editing
    let showSwapConfirm = $state(false);

    // Date range — global store is source of truth
    let dateEnd = $state(resolveDateSentinel(getEnd()));
    const initialStart = getStart();
    let dateStart = $state(resolveDateSentinel(initialStart));
    // Whether "All" (MAX) is the active semantic choice and its real earliest date
    // hasn't been resolved yet from backend data (survives navigation via the store).
    const initialIsMaxPending = isMaxSentinel(initialStart);
    let isMaxPending = $state(initialIsMaxPending);
    // Bound to the picker's `start` — shows the literal "min" sentinel (pending
    // label) while isMaxPending, otherwise mirrors the resolved dateStart.
    // Seeded from the plain `initialIsMaxPending`/`initialStart` above (not from the
    // dateStart/isMaxPending $state bindings) to avoid a state_referenced_locally warning —
    // displayDateStart is manually resynced elsewhere and bound bidirectionally to
    // DateRangePicker, so it's intentionally NOT a pure $derived of dateStart/isMaxPending.
    let displayDateStart = $state(initialIsMaxPending ? 'min' : resolveDateSentinel(initialStart));
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

    // View mode (abs/%) — controlled by the page, not by chart toolbar
    let viewMode: ViewMode = $state('percentage');

    // Provider config
    let providers: Array<{providerCode: string; priority: number; chainSteps?: Array<{from: string; to: string; provider: string}>}> = $state([]);
    let availableProviders: Array<{code: string; name: string}> = $state([]);

    // Foldable panels
    let showAesthetics = $state(false);
    let showMeasures = $state(false);
    let showSignals = $state(false);
    let showDataEditor = $state(false);

    // Provider config modal
    let showProviderModal = $state(false);

    // Filter bar layout is now owned by PageToolbar (shared with dashboard/broker-detail/assets)
    // — layoutMode is bound out (see bind:layoutMode below) for the one usage elsewhere on this
    // page (editor tip text). Tune live via window.__lfLayouts.fxDetail.thresholds.<field>.
    let pageLayoutMode = $state<LayoutMode>('denseRow');

    // Chart settings (from store) — keyed by canonical slug (not URL direction)
    let settings = $derived(getSettingsForPair(data.canonicalSlug, 'fx'));
    let signals = $derived<SignalConfig[]>([...settings.signals]);

    // Measure panel
    let measureMode = $state(false);
    let measureSignals: RenderedSignal[] = $state([]);
    let measurePanel: MeasurePanel | undefined = $state(undefined);

    // Data editor
    let pendingPreviewSignal: RenderedSignal | null = $state(null);
    let savingEdit = $state(false);
    let fxDataEditorRef: FxDataEditorSection | undefined = $state(undefined);
    let editorDirtyCount = $state(0);

    // All configured FX pair slugs (from backend, for FxPair signal dropdown)
    let allConfiguredSlugs: string[] = $state([]);

    // All assets (for asset comparison signals in ChartSignalsSection)
    let allAssets: Array<{id: number; display_name: string; icon_url?: string | null; asset_type?: string | null}> = $state([]);

    // Comparison events (asset-comparison signals)
    let comparisonEvents = $state<Map<number, any[]>>(new Map());

    // Panel states before edit mode (to restore when exiting)
    let savedPanelStates: {aesthetics: boolean; measures: boolean; signals: boolean} | null = $state(null);

    /** Incremented to force overlay signals recomputation after store data changes */
    let overlayDataVersion = $state(0);

    // Page sync modal state
    let showPageSyncModal = $state(false);

    /** All FX pairs to sync: main pair + overlay FX pair signals */
    let syncAllFxPairs = $derived.by(() => {
        const slugs = new Set<string>();
        slugs.add(data.canonicalSlug);
        for (const cfg of signals) {
            if (cfg.signalType === 'fx-pair') {
                const pairSlug = String(cfg.params.pairSlug || '');
                if (pairSlug) slugs.add(pairSlug);
            }
        }
        return Array.from(slugs);
    });

    /** All assets to sync from comparison signals */
    let syncAllAssets = $derived.by(() => {
        const items: Array<{id: number; display_name: string; icon_url?: string | null; asset_type?: string | null; provider_code?: string | null}> = [];
        const seenIds = new Set<number>();
        for (const cfg of signals) {
            if (cfg.signalType !== 'asset-comparison') continue;
            const aid = Number(cfg.params.assetId);
            if (!aid || seenIds.has(aid)) continue;
            seenIds.add(aid);
            const meta = allAssets.find((a) => a.id === aid);
            if (meta) {
                items.push({id: aid, display_name: meta.display_name, icon_url: meta.icon_url ?? undefined, asset_type: meta.asset_type ?? null, provider_code: 'unknown'});
            }
        }
        return items;
    });

    // =========================================================================
    // Derived
    // =========================================================================

    let inverted = $derived(data.inverted);
    let displayBase = $derived(data.urlBase);
    let displayQuote = $derived(data.urlQuote);

    let lastRate = $derived.by(() => {
        if (chartData.length === 0) return null;
        const last = chartData[chartData.length - 1];
        return inverted && last.rate !== 0 ? 1 / last.rate : last.rate;
    });

    let deltaPercent = $derived.by(() => {
        if (chartData.length < 2) return null;
        const first = chartData[0].rate;
        const last = chartData[chartData.length - 1].rate;
        if (first === 0) return null;
        const pct = ((last - first) / first) * 100;
        return inverted ? -pct : pct;
    });

    let lineData: LineDataPoint[] = $derived(
        chartData.map((d) => ({
            date: d.date,
            value: inverted && d.rate !== 0 ? 1 / d.rate : d.rate,
            staleDays: d.backwardFillInfo?.daysBack ?? 0,
        })),
    );

    /** First data point date — used for "no data before" banner */
    let firstDataDate = $derived(chartData.length > 0 ? chartData[0].date : null);
    /** True when the selected date range starts before the first available data point */
    let rangeStartsBeforeData = $derived(firstDataDate != null && dateStart < firstDataDate);

    /** Build DataQualityIssue[] for the unified banner */
    let fxDetailIssues: DataQualityIssue[] = $derived.by(() => {
        const issues: DataQualityIssue[] = [];
        if (rangeStartsBeforeData && !loading && !error) {
            issues.push({
                domain: 'forex',
                code: 'RANGE_BEFORE_FIRST_DATA',
                severity: 'info',
                message_i18n_key: 'dataQuality.rangeBeforeData',
                message_params: {date: firstDataDate ?? ''},
                affected_fx_pairs: [data.canonicalSlug],
            });
        }
        return issues;
    });

    // True when no real provider is configured (MANUAL sentinel is already filtered out)
    let isManualOnly = $derived(providers.length === 0);

    // Computed overlay signals from settings
    let overlaySignals: RenderedSignal[] = $derived.by(() => {
        void overlayDataVersion; // trigger recomputation when overlay data changes
        const rendered: RenderedSignal[] = [];
        for (const cfg of signals) {
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
                    instance.params._resolvedData = storeData.map((d) => ({
                        date: d.date,
                        value: d.rate,
                    }));
                } catch {
                    continue; // Store not available for this pair
                }
            }

            // For AssetComparisonSignal: resolve data injected by loadComparisonAssetsData
            if (cfg.signalType === 'asset-comparison') {
                const targetId = Number(cfg.params.assetId);
                if (!targetId) continue;
                const targetAsset = allAssets.find((a) => a.id === targetId);
                instance.params._assetDisplayName = targetAsset?.display_name ?? `Asset #${targetId}`;
                instance.params._assetIconUrl = targetAsset?.icon_url ?? null;
                instance.params._assetType = targetAsset?.asset_type ?? null;
                if (!instance.params._resolvedData) continue;
            }

            const results = instance.renderMulti(lineData, viewMode);
            for (const result of results) {
                if (result.data.length > 0) rendered.push(result);
            }
        }
        return rendered;
    });

    /** Combined overlay signals: computed from settings + measure signals */
    let allOverlaySignals: RenderedSignal[] = $derived([...overlaySignals, ...measureSignals, ...(pendingPreviewSignal ? [pendingPreviewSignal] : [])]);

    // Trigger flag re-evaluation when currencies finish loading
    let flagVersion = $state(0);
    let baseFlag = $derived.by(() => {
        void flagVersion;
        return getCurrencyInfo(displayBase).flag_emoji;
    });
    let quoteFlag = $derived.by(() => {
        void flagVersion;
        return getCurrencyInfo(displayQuote).flag_emoji;
    });

    // Signal label info for MeasurePanel and PriceChartFull tooltip
    let mainSignalInfo: SignalLabelInfo = $derived({
        label: `${baseFlag} ${displayBase} → ${quoteFlag} ${displayQuote}`,
        isCrown: true,
        color: COLORS.lineLight,
    });

    let overlaySignalInfoMap = $derived(buildOverlaySignalInfoMap(overlaySignals));

    // Event markers for the chart (comparison asset events — FX pairs don't have own events)
    let chartEventMarkers: EventMarker[] = $derived.by(() => {
        const markers: EventMarker[] = [];
        for (const [aid, evts] of comparisonEvents) {
            const targetAsset = allAssets.find((a) => a.id === aid);
            const label = targetAsset?.display_name ?? `Asset #${aid}`;
            const sigColor = overlaySignals.find((s) => s.label === label)?.color;
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
                    result.set(cfg.id, {pointCount: 0, eventCounts: {}, firstDate: null});
                }
            }
        }
        return result;
    });

    // Provider config: build editRoutes for the modal
    let editRoutes = $derived.by(() => {
        return providers.map((p) => p.chainSteps ?? [{from: data.canonicalBase, to: data.canonicalQuote, provider: p.providerCode}]);
    });

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(async () => {
        // Persist the inversion state from the URL so FxCard reflects it on back-navigation
        setCardInverted(data.canonicalSlug, data.inverted);

        await Promise.all([ensureCurrenciesLoaded(get(currentLanguage)), loadChartData(), loadProviders(), loadAvailableProviders(), loadAssetList()]);
        // Force flag reactivity after currencies load
        flagVersion++;
        // Load comparison asset data after initial data is ready
        await maybeLoadComparison();
    });

    // =========================================================================
    // Data Loading (same as before, unchanged logic)
    // =========================================================================

    /**
     * When "All" (MAX) is pending resolution, extract the real earliest date
     * from just-loaded chart data and update dateStart/displayDateStart.
     * The URL is left untouched — it keeps showing the generic "min"/"max"
     * sentinel (set in handleDateRangeChange) so the "All" selection survives
     * reloads/shares instead of freezing to a specific historical date.
     * No-op once already resolved or if there's no data yet.
     */
    function resolveMaxStartFromChartData() {
        if (!isMaxPending || chartData.length === 0) return;
        dateStart = chartData[0].date;
        displayDateStart = dateStart;
        isMaxPending = false;
    }

    /**
     * Counterpart to resolveMaxStartFromChartData(): re-arm "All" resolution
     * before a forced full reload. Once isMaxPending resolves, dateStart
     * freezes at whatever the earliest stored date was AT THAT TIME — a sync
     * "Tutti" that later reaches further into the past would silently not
     * show, because the query itself never asks for it again (it keeps using
     * the frozen, narrower dateStart). Widening dateStart back to the anchor
     * and re-arming isMaxPending lets resolveMaxStartFromChartData() pick up
     * the new true earliest date once the fresh (wide) query returns.
     */
    function rearmMaxPendingBeforeReload() {
        if (activePreset !== 'MAX') return;
        isMaxPending = true;
        dateStart = resolveDateSentinel('min');
        displayDateStart = 'min';
    }

    async function loadChartData() {
        error = null;

        // Fast path: data fully cached — update without showing loading state
        const store = getFxStore(data.canonicalSlug);
        if (store.getMissingIntervals(dateStart, dateEnd).length === 0) {
            chartData = store.getRange(dateStart, dateEnd).data;
            if (chartData.length === 0) error = '_i18n:fxDetail.noData';
            resolveMaxStartFromChartData();
            return;
        }

        loading = true;
        try {
            chartData = await ensureFxRangeLoaded(data.canonicalSlug, dateStart, dateEnd);
            if (chartData.length === 0 && !error) {
                error = '_i18n:fxDetail.noData';
            }
            resolveMaxStartFromChartData();
        } catch (e: any) {
            const existingData = getFxStore(data.canonicalSlug).getRange(dateStart, dateEnd).data;
            if (existingData.length > 0) {
                chartData = existingData;
            } else if (e?.response?.status === 404) {
                chartData = [];
                getFxStore(data.canonicalSlug).invalidateRange(dateStart, dateEnd);
                error = '_i18n:fxDetail.noData';
            } else {
                console.error('Failed to load chart data:', e);
                chartData = [];
                error = e?.message || 'Failed to load rates';
            }
        } finally {
            loading = false;
        }
    }

    async function loadProviders() {
        try {
            const response = await zodiosApi.list_routes_api_v1_fx_providers_routes_get();
            const items = (response as any)?.items || [];

            // Extract ALL unique configured pair slugs (for FxPair signal dropdown)
            const slugSet = new Set<string>();
            for (const i of items) {
                const b = i.base < i.quote ? i.base : i.quote;
                const q = i.base < i.quote ? i.quote : i.base;
                slugSet.add(`${b}-${q}`);
            }
            allConfiguredSlugs = [...slugSet].sort();

            // Filter routes for current pair only
            providers = items
                .filter((i: any) => ((i.base === data.canonicalBase && i.quote === data.canonicalQuote) || (i.base === data.canonicalQuote && i.quote === data.canonicalBase)) && !(i.chain_steps?.length === 1 && i.chain_steps[0].provider === 'MANUAL'))
                .sort((a: any, b: any) => a.priority - b.priority)
                .map((i: any) => {
                    const steps = i.chain_steps ?? [];
                    return {
                        providerCode: steps.length === 1 ? steps[0].provider : 'CHAIN:' + steps.map((s: any) => s.provider).join('+'),
                        priority: i.priority,
                        chainSteps: steps,
                    };
                });
        } catch (e) {
            console.error('Failed to load providers:', e);
        }
    }

    async function loadAvailableProviders() {
        try {
            const response = await zodiosApi.list_providers_api_v1_fx_providers_get();
            availableProviders = (response as any[]).map((p: any) => ({code: p.code, name: p.name}));
        } catch (e) {
            console.error('Failed to load available providers:', e);
        }
    }

    async function loadAssetList() {
        try {
            const response = await zodiosApi.get_all_assets_api_v1_assets_all_get();
            allAssets = (response as any[]).map((a: any) => ({
                id: a.id,
                display_name: a.display_name,
                icon_url: a.icon_url ?? null,
                asset_type: a.asset_type ?? null,
            }));
        } catch (e) {
            console.error('Failed to load asset list:', e);
        }
    }

    /**
     * Load comparison asset data if any comparison signals are configured.
     * Called explicitly from onMount, handleRefresh, handleDateRangeChange, handleSignalsChange.
     */
    async function maybeLoadComparison() {
        const compSignals = signals.filter((s) => s.signalType === 'asset-comparison');
        if (compSignals.length === 0 || lineData.length === 0) return;
        try {
            comparisonEvents = await loadComparisonAssetsData(compSignals, {start: dateStart, end: dateEnd}, allAssets, comparisonEvents);
            overlayDataVersion++;
        } catch (e) {
            console.error('Failed to load comparison asset data:', e);
        }
    }

    // =========================================================================
    // Actions
    // =========================================================================

    async function handleRefresh() {
        rearmMaxPendingBeforeReload();
        const store = getFxStore(data.canonicalSlug);
        store.invalidateRange(dateStart, dateEnd);
        await loadChartData();
        // Also invalidate overlay pair stores so comparison signals refresh
        for (const cfg of signals) {
            if (cfg.signalType === 'fx-pair') {
                const pairSlug = String(cfg.params.pairSlug || '');
                if (pairSlug && pairSlug !== data.canonicalSlug) {
                    getFxStore(pairSlug).invalidateRange(dateStart, dateEnd);
                    await ensureFxRangeLoaded(pairSlug, dateStart, dateEnd);
                }
            }
        }
        overlayDataVersion++;
        await maybeLoadComparison();
    }

    function handleSync() {
        showPageSyncModal = true;
    }

    async function handlePageSyncComplete() {
        await handleRefresh();
        await maybeLoadComparison();
        overlayDataVersion++;
    }

    async function handleDateRangeChange(newStart: string, newEnd: string) {
        isMaxPending = isMaxSentinel(newStart);
        dateStart = resolveDateSentinel(newStart);
        dateEnd = resolveDateSentinel(newEnd);
        displayDateStart = isMaxPending ? 'min' : dateStart;
        setDateRange(newStart, newEnd);
        // Sync URL for shareability. Keep the generic "min"/"max" sentinel when
        // "All" is selected (instead of a concrete resolved date) so the URL
        // stays meaningful across reloads/shares and the "All" badge doesn't
        // look stuck on a specific historical date.
        replaceHistoryDateRange(newStart, newEnd);
        await loadChartData();
        await maybeLoadComparison();
    }

    function handleMeasureClick(date: string, value: number) {
        measurePanel?.addPoint(date, value);
    }

    function handleAestheticsChange(values: {colorByBaseline: boolean; areaFill: boolean; gridLines: boolean; staleGradient: boolean; yAxisMode: 'auto' | 'include0' | 'custom'; yAxisMin: number | undefined; yAxisMax: number | undefined}) {
        setPairSettings(data.canonicalSlug, {...settings, ...values, signals: [...signals]});
    }

    function handleSignalsChange(newSignals: SignalConfig[]) {
        setPairSettings(data.canonicalSlug, {...settings, signals: JSON.parse(JSON.stringify(newSignals))});
        maybeLoadComparison(); // fire-and-forget: load data for newly added comparison signals
    }

    async function handleSyncPair(slug: string) {
        try {
            syncing = true;
            const response = await zodiosApi.sync_rates_api_v1_fx_currencies_sync_post({
                pairs: [slug],
                start: syncDateStart,
                end: dateEnd,
            });
            const r = (response as any)?.results?.[0];
            if (r) {
                const tr = get(t);
                const toast = buildFxSyncToast(r, slug, tr, formatProviderText, formatSyncDetail);
                toasts[toast.variant](toast.message);
            }
            // Invalidate store + refresh if it's our pair, also reload overlay data
            getFxStore(slug).invalidateRange(dateStart, dateEnd);
            if (slug === data.canonicalSlug) {
                await handleRefresh();
            } else {
                // Overlay pair: re-fetch data from DB so the chart updates
                await ensureFxRangeLoaded(slug, dateStart, dateEnd);
                overlayDataVersion++;
            }
        } catch (e: any) {
            toasts.error('Sync failed: ' + (e?.message || 'unknown'));
        } finally {
            syncing = false;
        }
    }

    function handleDetailPair(slug: string) {
        goto(`/fx/${slug}?start=${urlDateStart}&end=${urlDateEnd}`);
    }

    async function handleSyncAsset(assetId: number) {
        try {
            const response = await zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post([
                {
                    asset_id: assetId,
                    date_range: {start: syncDateStart, end: dateEnd},
                },
            ]);
            const r = (response as any)?.results?.[0];
            const tr = get(t);
            if (r) {
                const toast = buildAssetSyncToast(r, tr('common.sync'), tr);
                toasts[toast.variant](toast.message);
            } else {
                toasts.error(`${tr('common.sync')} — ${tr('prices.sync.noResponse')}`);
            }
        } catch (e: any) {
            toasts.error('Sync failed: ' + (e?.message || 'unknown'));
        }
        // Reload comparison data for the synced asset
        await maybeLoadComparison();
    }

    function handleDetailAsset(assetId: number) {
        goto(`/assets/${assetId}?start=${urlDateStart}&end=${urlDateEnd}`);
    }

    /** Handle provider modal save — reload providers */
    async function handleProviderModalCreated(_detail: {base: string; quote: string; hasRealProvider: boolean}) {
        await loadProviders();
        showProviderModal = false;
    }

    // =========================================================================
    // Swap direction (Step 8+9)
    // =========================================================================

    function doSwap() {
        // Exit edit mode if active
        if (showDataEditor) {
            showDataEditor = false;
            pendingPreviewSignal = null;
            if (savedPanelStates) {
                showAesthetics = savedPanelStates.aesthetics;
                showMeasures = savedPanelStates.measures;
                showSignals = savedPanelStates.signals;
                savedPanelStates = null;
            }
        }
        // Persist inversion state so FxCard shows the same direction on back-navigation
        setCardInverted(data.canonicalSlug, !inverted);
        goto(`/fx/${displayQuote}-${displayBase}`, {replaceState: true});
    }

    function handleSwapDirection() {
        if (!showDataEditor || editorDirtyCount === 0) {
            doSwap();
        } else {
            showSwapConfirm = true;
        }
    }
</script>

<div class="space-y-4" data-testid="fx-detail-page">
    <!-- ======================================================================= -->
    <!-- Header: pair info + back button -->
    <!-- ======================================================================= -->
    <div class="flex items-center gap-3" data-testid="fx-detail-header">
        <button class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-gray-400 transition-colors" data-testid="fx-detail-back-btn" onclick={() => goBack('/fx')} title={$t('fxDetail.backToList')}>
            <ArrowLeft size={20} />
        </button>
        <div class="flex items-center gap-2" data-testid="fx-detail-pair-label">
            <span class="text-2xl">{baseFlag}</span>
            <h2 class="text-xl font-bold text-gray-800 dark:text-gray-100">{displayBase}</h2>
            <span class="text-gray-400 dark:text-gray-500 text-lg">→</span>
            <span class="text-2xl">{quoteFlag}</span>
            <h2 class="text-xl font-bold text-gray-800 dark:text-gray-100">{displayQuote}</h2>
            <button class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors" data-testid="fx-detail-swap-btn" onclick={handleSwapDirection} title={$t('common.swapDirection')}>
                <ArrowLeftRight size={16} />
            </button>
        </div>
    </div>

    <!-- Error banner (not data-quality — dismissible runtime error) -->
    {#if error}
        <div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4 text-sm text-amber-700 dark:text-amber-400 flex items-center gap-2">
            <span>⚠️</span> <span>{errorMessage}</span>
            <button class="ml-auto text-xs px-2 py-1 bg-amber-100 dark:bg-amber-900/40 rounded hover:bg-amber-200" onclick={() => (error = null)}>{$t('common.close')}</button>
        </div>
    {/if}

    <!-- Unified data quality banners -->
    <DataQualityBanner issues={fxDetailIssues} mode="flat" />

    <!-- ======================================================================= -->
    <!-- Filter bar — shared PageToolbar (same component as dashboard/broker-detail/assets),
         so responsive/wrap fixes made there auto-propagate here too. -->
    <!-- oneRow:       [ datepicker  pair-info ─── actions-2×2 ]  1 row, picker 1-row       -->
    <!-- denseRow:     [ datepicker  pair-info ─── actions-2×2 ]  1 row, picker 2-row       -->
    <!-- stackFilters: [ datepicker       ] [ actions ]  filters+summary stacked, actions   -->
    <!--               [ pair-info        ] [ 2×2     ]  stay BESIDE (2×2)                  -->
    <!-- oneColumn:    [ datepicker       ]  whole bar now ONE column — actions moved       -->
    <!--               [ pair-info        ]  BELOW, still a labeled 2×2 grid (only          -->
    <!--               [ actions ── 2×2   ]  position changed)                              -->
    <!-- iconOnly:     [ datepicker       ]  everything stacked, actions icon-only centered -->
    <!--               [ pair-info        ]  row                                            -->
    <!--               [ actions ─ icons  ]                                                 -->
    <!-- ======================================================================= -->
    <PageToolbar thresholds={{oneRow: 790, denseRow: 620, stackFilters: 520, oneColumn: 420, iconOnly: 330, labelHide: 330}} filterRowTestId="fx-detail-filter-bar" layoutDebugName="fxDetail" bind:layoutMode={pageLayoutMode}>
        {#snippet filters()}
            <div class="flex flex-1 self-stretch min-w-0">
                <DateRangePicker bind:activePreset bind:end={dateEnd} bind:start={displayDateStart} compact={true} align="start" layoutMode={pageLayoutMode} debugName="fxDetail" onchange={handleDateRangeChange} />
            </div>
        {/snippet}

        {#snippet summary({layoutMode})}
            <!-- Pair Summary (rate + delta) -->
            <FxPriceSummary {lastRate} {deltaPercent} {layoutMode} />
        {/snippet}

        {#snippet actions({showActionLabels})}
            <!-- Row 1, Col 1: Abs/% segmented toggle -->
            <div class="flex rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
                <button
                    class="flex-1 px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {viewMode === 'absolute' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                    onclick={() => {
                        viewMode = 'absolute';
                    }}
                    >Abs
                </button>
                <button
                    class="flex-1 px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {viewMode === 'percentage' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                    onclick={() => {
                        viewMode = 'percentage';
                    }}
                    >%
                </button>
            </div>
            <!-- Row 1, Col 2: Providers -->
            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                data-testid="fx-detail-provider-btn"
                onclick={() => (showProviderModal = true)}
            >
                <Wrench size={14} />
                {#if showActionLabels}<span>{$t('common.providers')}</span>{/if}
            </button>
            <!-- Row 2, Col 1: Sync -->
            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors
                           {isManualOnly ? 'opacity-50 cursor-not-allowed' : ''}"
                data-testid="fx-detail-sync-btn"
                disabled={isManualOnly}
                onclick={handleSync}
                title={isManualOnly ? $t('fxDetail.syncDisabledManual') : ''}
            >
                <RotateCw size={14} />
                {#if showActionLabels}<span>{$t('common.sync')}</span>{/if}
            </button>
            <!-- Row 2, Col 2: Refresh -->
            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                data-testid="fx-detail-refresh-btn"
                disabled={loading}
                onclick={handleRefresh}
            >
                <RefreshCw class={loading ? 'animate-spin' : ''} size={14} />
                {#if showActionLabels}<span>{$t('common.refresh')}</span>{/if}
            </button>
        {/snippet}
    </PageToolbar>

    <!-- ======================================================================= -->
    <!-- Foldable Panel: Signals (ABOVE chart, replaces old Aesthetics position) -->
    <!-- ======================================================================= -->
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
        <button class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors rounded-xl" data-testid="fx-detail-signals-toggle" onclick={() => (showSignals = !showSignals)}>
            <span class="flex items-center gap-2">
                <TrendingUp class="text-blue-500" size={15} />
                {$t('common.signals')}
            </span>
            <ChevronDown class="transition-transform {showSignals ? 'rotate-180' : ''}" size={15} />
        </button>
        {#if showSignals}
            <div data-testid="fx-detail-signals-panel" class="px-4 pb-4 border-t border-gray-100 dark:border-slate-700 pt-3">
                <ChartSignalsSection
                    signals={[...signals]}
                    availablePairs={allConfiguredSlugs}
                    availableAssets={allAssets}
                    mainPairSlug={data.canonicalSlug}
                    onchange={handleSignalsChange}
                    onsyncpair={handleSyncPair}
                    ondetailpair={handleDetailPair}
                    onsyncasset={handleSyncAsset}
                    ondetailasset={handleDetailAsset}
                    {signalSummaries}
                    {dateStart}
                />
            </div>
        {/if}
    </div>

    <!-- ======================================================================= -->
    <!-- Chart with left toolbar -->
    <!-- ======================================================================= -->
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 p-4" data-testid="fx-detail-chart">
        {#if loading && lineData.length === 0}
            <div class="h-96 flex items-center justify-center">
                <div class="text-center">
                    <RefreshCw size={24} class="animate-spin text-libre-green mx-auto mb-2" />
                    <p class="text-sm text-gray-500 dark:text-gray-400">{$t('fxDetail.loadingRates')}</p>
                </div>
            </div>
        {:else if lineData.length > 0}
            <!-- Aesthetics panel (ABOVE chart, shown only when gear is active) -->
            {#if showAesthetics}
                <div data-testid="fx-detail-aesthetics-panel" class="mb-3 pb-3 border-b border-gray-100 dark:border-slate-700 relative">
                    <button class="absolute top-0 right-0 p-1 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-600 transition-colors" onclick={() => (showAesthetics = false)} title={$t('common.close')}>
                        <X size={16} />
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
                        data-testid="fx-detail-measure-btn"
                        class="p-1.5 rounded-lg transition-colors {measureMode
                            ? 'bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400 ring-1 ring-violet-300 dark:ring-violet-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                        onclick={async () => {
                            if (measureMode) {
                                measurePanel?.stopMeasureMode();
                            } else {
                                showMeasures = true;
                                await tick();
                                measurePanel?.startMeasureMode();
                            }
                        }}
                        title={measureMode ? $t('common.exitMeasure') : $t('common.addMeasure')}
                    >
                        <Ruler size={16} />
                    </button>
                    <button
                        data-testid="fx-detail-edit-btn"
                        class="p-1.5 rounded-lg transition-colors {showDataEditor
                            ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400 ring-1 ring-amber-300 dark:ring-amber-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                        onclick={() => {
                            if (showDataEditor) {
                                showDataEditor = false;
                                pendingPreviewSignal = null;
                                if (savedPanelStates) {
                                    showAesthetics = savedPanelStates.aesthetics;
                                    showMeasures = savedPanelStates.measures;
                                    showSignals = savedPanelStates.signals;
                                    savedPanelStates = null;
                                }
                            } else {
                                savedPanelStates = {aesthetics: showAesthetics, measures: showMeasures, signals: showSignals};
                                showAesthetics = false;
                                showMeasures = false;
                                showSignals = false;
                                showDataEditor = true;
                            }
                        }}
                        title={showDataEditor ? $t('common.closeEditor') : $t('fxDetail.editRates')}
                    >
                        <Pencil size={16} />
                    </button>
                    <button
                        data-testid="fx-detail-aesthetics-toggle"
                        class="p-1.5 rounded-lg transition-colors {showAesthetics
                            ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400 ring-1 ring-emerald-300 dark:ring-emerald-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                        onclick={() => (showAesthetics = !showAesthetics)}
                        title={$t('common.aesthetics')}
                    >
                        <Settings size={16} />
                    </button>
                </div>

                <PriceChartFull
                    data={lineData}
                    currency={displayQuote}
                    mainSeriesLabel={`${baseFlag} ${displayBase} → ${quoteFlag} ${displayQuote}`}
                    chartHeight="400px"
                    overlaySignals={allOverlaySignals}
                    eventMarkers={chartEventMarkers}
                    {overlaySignalInfoMap}
                    colorByBaseline={settings.colorByBaseline}
                    areaFill={settings.areaFill}
                    showGridLines={settings.gridLines}
                    showGradient={settings.staleGradient}
                    yAxisMode={settings.yAxisMode}
                    yAxisMin={settings.yAxisMin}
                    yAxisMax={settings.yAxisMax}
                    {measureMode}
                    onMeasureClick={handleMeasureClick}
                    onMeasureHover={(date, value) => measurePanel?.updatePendingEnd(date, value)}
                    hideToolbar={true}
                    disableCandlestick={true}
                    externalViewMode={viewMode}
                    editMode={showDataEditor}
                    onPointClick={(date, _value) => fxDataEditorRef?.scrollToDate(date)}
                    staleLabel={$t('chart.tooltip.stale')}
                    fxStaleLabel={$t('chart.tooltip.fxStale')}
                />
            </div>
        {:else}
            <div class="h-96 flex items-center justify-center">
                <div class="text-center">
                    {#if isManualOnly}
                        <p class="text-gray-400 dark:text-gray-500 mb-3">
                            {$t('fxDetail.noDataManual')}
                        </p>
                        <button
                            class="px-4 py-2 text-sm bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition-colors"
                            onclick={() => {
                                showDataEditor = true;
                            }}
                        >
                            {$t('fxDetail.insertManually')}
                        </button>
                    {:else}
                        <p class="text-gray-400 dark:text-gray-500 mb-3">{$t('fxDetail.noData')}</p>
                        <div class="flex items-center gap-2 justify-center">
                            <button class="px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors" onclick={handleSync}>
                                {$t('fxDetail.syncRates')}
                            </button>
                            <button
                                class="px-4 py-2 text-sm bg-slate-200 dark:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-500 transition-colors"
                                data-testid="fx-detail-add-rates-manually"
                                onclick={() => {
                                    showDataEditor = true;
                                }}
                            >
                                <Pencil class="inline mr-1" size={14} />
                                {$t('fxDetail.insertManually')}
                            </button>
                        </div>
                    {/if}
                </div>
            </div>
        {/if}
    </div>

    <!-- ======================================================================= -->
    <!-- Data Editor (shown only when toggled via pencil button) -->
    <!-- ======================================================================= -->
    {#if showDataEditor}
        <div data-testid="fx-detail-editor-panel" class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-amber-200 dark:border-amber-800">
            <div class="flex items-center justify-between px-4 py-3 border-b border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-yellow-900/30 rounded-t-xl">
                <span class="flex items-center gap-2 text-sm font-medium text-amber-700 dark:text-amber-400">
                    <Pencil size={15} />
                    {$t('fxDetail.editRates')}
                </span>
                <button
                    class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                    onclick={() => {
                        showDataEditor = false;
                        pendingPreviewSignal = null;
                        if (savedPanelStates) {
                            showAesthetics = savedPanelStates.aesthetics;
                            showMeasures = savedPanelStates.measures;
                            showSignals = savedPanelStates.signals;
                            savedPanelStates = null;
                        }
                    }}
                    title={$t('common.closeEditor')}
                    >✕
                </button>
            </div>
            <p class="px-4 pt-2 text-xs text-amber-700/70 dark:text-amber-400/70">
                💡 {pageLayoutMode === 'oneColumn' || pageLayoutMode === 'iconOnly' ? $t('fxDetail.editorTipMobile') : $t('fxDetail.editorTipDesktop')}
            </p>
            <div class="px-4 pb-4 pt-3">
                <FxDataEditorSection
                    bind:this={fxDataEditorRef}
                    base={displayBase}
                    quote={displayQuote}
                    {chartData}
                    bind:saving={savingEdit}
                    bind:dirtyCount={editorDirtyCount}
                    onsave={async (expandedRange) => {
                        if (expandedRange) {
                            dateStart = expandedRange.start;
                            dateEnd = expandedRange.end;
                            displayDateStart = isMaxPending ? 'min' : dateStart;
                            activePreset = null;
                        }
                        await handleRefresh();
                        showDataEditor = false;
                        if (savedPanelStates) {
                            showAesthetics = savedPanelStates.aesthetics;
                            showMeasures = savedPanelStates.measures;
                            showSignals = savedPanelStates.signals;
                            savedPanelStates = null;
                        }
                    }}
                    oncancel={() => {
                        showDataEditor = false;
                        pendingPreviewSignal = null;
                        if (savedPanelStates) {
                            showAesthetics = savedPanelStates.aesthetics;
                            showMeasures = savedPanelStates.measures;
                            showSignals = savedPanelStates.signals;
                            savedPanelStates = null;
                        }
                    }}
                    onpendingchange={(signal) => (pendingPreviewSignal = signal)}
                />
            </div>
        </div>
    {/if}

    <!-- ======================================================================= -->
    <!-- Foldable Panel: Measures (below DataEditor, above Signals) -->
    <!-- ======================================================================= -->
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
        <div class="flex items-center justify-between px-4 py-2.5">
            <button class="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-200 hover:text-gray-900 dark:hover:text-white transition-colors" data-testid="fx-detail-measures-toggle" onclick={() => (showMeasures = !showMeasures)}>
                <Ruler class="text-violet-500" size={15} />
                {$t('common.measures')}
                {#if measureMode}
                    <span class="text-[10px] px-1.5 py-0.5 bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400 rounded-full">{$t('measure.active')}</span>
                {/if}
                <ChevronDown class="transition-transform {showMeasures ? 'rotate-180' : ''}" size={15} />
            </button>
            <button
                type="button"
                class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-md
                           bg-violet-50 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400
                           hover:bg-violet-100 dark:hover:bg-violet-900/50
                           transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={lineData.length < 2}
                onclick={(e) => {
                    e.stopPropagation();
                    showMeasures = true;
                    measurePanel?.addMeasureFromChartData();
                }}
                title={$t('common.addMeasure')}
            >
                <span class="text-sm leading-none">+</span>
            </button>
        </div>
        <!-- Single MeasurePanel instance — always mounted, hidden via CSS to preserve state -->
        <div class={showMeasures ? 'px-4 pb-4 border-t border-gray-100 dark:border-slate-700 pt-3' : 'hidden'} data-testid="fx-detail-measures-panel">
            <MeasurePanel bind:this={measurePanel} chartData={lineData} onmeasuremodechange={(active) => (measureMode = active)} onmeasureschange={(m) => (measureSignals = m)} {overlaySignals} {mainSignalInfo} {viewMode} />
        </div>
    </div>

    <!-- ======================================================================= -->
    <!-- Provider Configuration Modal (reuses FxPairAddModal in editMode) -->
    <!-- ======================================================================= -->
    <div data-testid="fx-detail-provider-modal">
        <FxPairAddModal bind:open={showProviderModal} {dateEnd} {dateStart} editBase={data.canonicalBase} editMode={true} editQuote={data.canonicalQuote} {editRoutes} onclose={() => (showProviderModal = false)} oncreated={handleProviderModalCreated} />
    </div>

    <!-- Confirm modal for swap direction while editing -->
    <ConfirmModal
        cancelText={$t('common.cancel')}
        confirmText={$t('common.continue')}
        message={$t('fxDetail.swapConfirmMessage')}
        onCancel={() => (showSwapConfirm = false)}
        onConfirm={() => {
            showSwapConfirm = false;
            doSwap();
        }}
        open={showSwapConfirm}
        title={$t('fxDetail.swapConfirmTitle')}
        warning={true}
    />

    <!-- Page Sync Modal (sync all FX pairs + assets present on page) -->
    <PageSyncModal bind:open={showPageSyncModal} dateStart={syncDateStart} {dateEnd} assets={syncAllAssets} fxPairs={syncAllFxPairs} onsynced={handlePageSyncComplete} onclose={() => (showPageSyncModal = false)} />
</div>
