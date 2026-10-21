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
    import {onDestroy, onMount, tick} from 'svelte';
    import {goto} from '$app/navigation';
    import {page} from '$app/stores';
    import {_ as t} from '$lib/i18n';
    import {zodiosApi, axiosInstance} from '$lib/api';
    import {BarChart3, CalendarSync, Check, Network, Plus, RefreshCw, RotateCw, Search, Settings, Trash2, X} from 'lucide-svelte';
    import AssetCard from '$lib/components/assets/AssetCard.svelte';
    import type {AssetRow} from '$lib/components/assets/AssetTable.svelte';
    import AssetTable from '$lib/components/assets/AssetTable.svelte';
    import AssetBrowseOrder from '$lib/components/assets/AssetBrowseOrder.svelte';
    import {fetchCurrentPrices, computeDirection, livePollFailure, livePollOutcome} from '$lib/services/livePriceService';
    import type {LivePriceDirection} from '$lib/services/livePriceService';
    import {startActivePolling, type ActivePolling, type ActivePollingState} from '$lib/features/live-updates/activePolling';
    import {ASSET_LIST_LIVE_INTERVAL_MS} from '$lib/features/live-updates/cadence';
    import LiveUpdatesStatus from '$lib/features/live-updates/LiveUpdatesStatus.svelte';
    import AssetSyncModal from '$lib/components/assets/AssetSyncModal.svelte';
    import AssetModal from '$lib/components/assets/AssetModal.svelte';
    import {entityDetailLinkHtml} from '$lib/utils/core/entityLink';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {loadAssetEditData, type AssetEditData} from '$lib/components/assets/assetEditData';
    import {getClientSessionGeneration, isClientSessionCurrent} from '$lib/stores/app/clientSession';
    import {extractErrorMessage} from '$lib/utils/trySave';
    import AssetMergeModal from '$lib/components/assets/AssetMergeModal.svelte';
    import {invalidateAfterMutation} from '$lib/stores/reference/assetStore';
    import ViewModeToggle from '$lib/components/ui/ViewModeToggle.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import DataTableToolbar from '$lib/components/table/DataTableToolbar.svelte';
    import DateRangePicker from '$lib/components/ui/date/DateRangePicker.svelte';
    import ChartSettingsModal from '$lib/components/charts/ChartSettingsModal.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {pageBusy} from '$lib/stores/app/pageBusy.svelte';
    import {hasStoredRowBehindSample, type AssetCreateSyncResult} from '$lib/utils/sync/syncHelpers';
    import type {ChartPrimaryView, ChartSettings} from '$lib/stores/chartSettingsStore.svelte';
    import {effectiveCalendarReturnWindow, getGlobalSettings, getSettingsForPair, getSettingsVersion, setGlobalSettings, setItemPrimaryView, setPairSettings, setScopePrimaryView} from '$lib/stores/chartSettingsStore.svelte';
    import {CALENDAR_RETURN_INSTANCE_ID, CALENDAR_RETURN_SIGNAL_CODE, emptyCalendarReturnView, extractCalendarReturnView, type CalendarReturnView} from '$lib/components/charts/priceChartHelpers';
    import {calendarReturnRangeDays, calendarReturnWindowDays} from '$lib/components/charts/calendarReturnWindow';
    import {formatSignalProblem} from '$lib/components/charts/chartSignalsHelpers';
    import {CurrencySearchSelect} from '$lib/components/ui/select';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import {onboardingGuide} from '$lib/features/onboarding/onboardingGuide.svelte';
    import {getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import PageToolbar from '$lib/components/ui/toolbar/PageToolbar.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import AssetSetRiskPanel from '$lib/features/risk/AssetSetRiskPanel.svelte';
    import {getFixedDropdownPosition} from '$lib/utils/layout/dropdownPosition';
    import {gotoDateRange} from '$lib/utils/url/dateRangeUrl';
    import {todayIso} from '$lib/utils/dateOnly';
    import {buildBackendSignalRequestPlan, getLocalSignalDefinitions, mapSignalInstanceResults, SignalResultState, type RenderedSignal, type SignalConfig, type SignalDefinition, type SignalInstanceResult} from '$lib/charts/signals';
    import {fxPointToLineDataPoint, renderBackendResults, renderCalendarComparisons, renderLocalSignals, type SignalDataSources} from '$lib/charts/chartSignalRendering';
    import {getStart, getEnd, setDateRange, resolveDateSentinel, isMaxSentinel} from '$lib/stores/dateRangeStore.svelte';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import {createPairSlug, ensureFxRangeLoaded, getFxStore} from '$lib/stores/fxStoreRegistry';
    import {invalidateAssetPriceStore} from '$lib/stores/assetPriceStoreRegistry';
    import {reducedPrices, type ReducedEntry} from '$lib/stores/reducedPriceCache';
    import type {DerivedBase} from '$lib/utils/assetPriceDerived';
    import {buildReducedQuery, cardsOfAnotherStep, comparisonTargetFrom, comparisonTargetIds, estimateEntryDays, signalBaseData, type CardQueryInput} from '$lib/utils/reducedPriceQuery';
    import {DEFAULT_COMPACT_PLOT_WIDTH_PX, compactMaxPoints, type ChartResolution} from '$lib/components/charts/timeSeriesAggregation';
    import {fetchAssetPeriodChanges, PeriodChangesLedger, visiblePeriodColumns, type PeriodDeltas, type PeriodSpec} from '$lib/utils/periodChanges';
    import type {RangeDelta} from '$lib/utils/rangeChange';
    import {processPriceItemsInParallel} from '$lib/workers/priceProcessingPool';
    import {sendBulkBatches} from '$lib/api/bulkBatches';
    import {bulkRefusalMessage} from '$lib/api/bulkRefusal';
    import type {ProcessedAssetResult} from '$lib/workers/priceProcessing.worker';
    import {signalCatalogStore} from '$lib/stores/signalCatalogStore.svelte';
    import {defaultDisplayCurrency} from '$lib/stores/app/settings';
    import {matchesAssetLifecycle, orderAssetsByLifecycle} from '$lib/components/assets/assetLifecycle';
    import {buildTabUrl, getResolvedTabParam} from '$lib/utils/url/tabUrl';
    import {buildTransactionsFiltersUrl} from '../transactions/filterState';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';

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
        quote_base_quantity?: number | null;
        tx_count?: number;
        /** A positive quantity is held **now** in a broker the user owns (Risk, `FAinfoResponse`). */
        held_by_me?: boolean;
        /** A positive quantity is held **now** in a broker the user does not own. */
        held_by_others?: boolean;
    }

    interface AssetState extends AssetInfo {
        lastPrice: number | null;
        /** The card's series, as the backend sampled it for the card's plot (Z-29b): one point a day, a week or a month. */
        chartData: Array<{date: string; value: number; staleDays?: number}>;
        /** The step of `chartData`: `daily`, or `weekly` or `monthly` when the card's plot is narrower than its days. */
        resolution?: ChartResolution;
        /** The point on the fill's first day (`sample_bounds.first`, else the first price): the base of the percentage view and of the line's colour. */
        base?: DerivedBase | null;
        loadingPrices: boolean;
    }

    // =========================================================================
    // State
    // =========================================================================

    let assets = $state<AssetState[]>([]);
    let loading = $state(true);
    let refreshing = $state(false);
    let error = $state<string | null>(null);
    // F15 round-2 — one AssetTable per usage panel (own / others / watched).
    // Column layout is mirrored live across the three; pagination stays independent.
    let assetTableRefs: Record<string, AssetTable | undefined> = $state({});
    let panelSelections: Record<string, AssetRow[]> = $state({});
    let selectedAssetRows = $derived(Object.values(panelSelections).flat());

    /** Mirror a live column resize onto the sibling tables. */
    function mirrorColumnResize(sourcePanel: string, columnId: string, width: number) {
        for (const pid of ['own', 'others', 'analysis']) {
            if (pid !== sourcePanel) assetTableRefs[pid]?.getTableRef()?.setColumnWidth(columnId, width);
        }
    }

    function clearAllTableSelections() {
        for (const ref of Object.values(assetTableRefs)) ref?.getTableRef()?.clearSelection();
        panelSelections = {};
    }
    /** Set of asset IDs currently syncing (for per-card/row rotating icon) */
    let syncingAssetIds = $state<Set<number>>(new Set());

    /** Live prices from bulk current-price endpoint (asset_id → {value, direction}) */
    let livePriceMap = $state<Map<number, {value: number; direction: LivePriceDirection}>>(new Map());
    /** The live poll of the list, while the range ends today and the list is not empty (F26). */
    let livePoller: ActivePolling | null = null;
    /** Its state, for the page root (`data-live-updates`) and the «Updates paused» pill. */
    let liveUpdatesState = $state<ActivePollingState>('stopped');

    // Delete dialog (single)
    let deleteDialogOpen = $state(false);
    let deletingAsset: AssetRow | null = $state(null);
    let mergeModalOpen = $state(false);
    let mergingAsset: AssetRow | null = $state(null);
    let deleteLoading = $state(false);
    let singleDeleteResults = $state<{label: string; success: boolean; detail?: string; action?: {href: string; label: string; testId?: string}}[]>([]);

    // Bulk delete confirmation dialog
    let bulkDeleteDialogOpen = $state(false);
    let deletingAssets = $state<AssetRow[]>([]);
    let bulkDeleteResults = $state<{label: string; success: boolean; detail?: string; action?: {href: string; label: string; testId?: string}}[]>([]);

    // Sync modal
    let syncModalOpen = $state(false);
    let syncModalAssets = $state<AssetInfo[]>([]);

    // Asset modal (create/edit)
    let assetModalOpen = $state(false);
    let assetTourPreview = $state(false);
    let assetModalEditMode = $state(false);
    let assetModalEditData = $state<AssetEditData | null>(null);
    let assetEditLoading = $state(false);
    let assetEditRequest = 0;
    onDestroy(() => {
        assetEditRequest += 1;
        clearTimeout(widthReloadTimer);
    });

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
    /** Mirrors the DateRangePicker's own effective 2-row max-width, so the Center filters block
     *  below it can be capped to the SAME pixel value when filtersStacked (matches the
     *  established dashboard/brokerDetail/fxList "giustificata" pattern). MUST start
     *  non-undefined (390 = DateRangePicker's own maxWidthTwoRow default) — Svelte forbids
     *  bind:key={undefined} when the child prop has a declared fallback. */
    let pickerMaxWidth = $state<number>(390);

    /**
     * Sentinel-aware values for building URLs (own history + cross-page nav
     * links). While "All" is the active selection, these stay "min"/"max"
     * (generic) instead of a concrete resolved date, for the lifetime of the
     * selection — not just until the real date is resolved.
     */
    let urlDateStart = $derived(activePreset === 'MAX' ? 'min' : dateStart);
    let urlDateEnd = $derived(activePreset === 'MAX' ? 'max' : dateEnd);
    let syncDateStart = $derived(activePreset === 'MAX' ? 'min' : dateStart);
    /** The sync dialog's assets whose shown prices hold a stored row in its range (C-66): the dialog warns that the sync
     * replaces them. The prices shown are a weekly or monthly sample on a wide range (Z-29b), so it reads the row behind each point. */
    let syncModalWithData = $derived(
        syncModalOpen
            ? syncModalAssets
                  .filter((a) =>
                      hasStoredRowBehindSample(
                          (assets.find((shown) => shown.id === a.id)?.chartData ?? []).map((point) => ({date: point.date, staleDays: point.staleDays ?? 0})),
                          syncDateStart,
                          dateEnd,
                      ),
                  )
                  .map((a) => a.id)
            : [],
    );

    /** True when the date range ends today (or later) → show live prices from providers. Today on the user's calendar,
     *  like `dateEnd`: the UTC date is already tomorrow in the evening west of Greenwich (Z-3). */
    let isHeadToday = $derived(dateEnd >= todayIso());

    // View mode
    let viewMode = $state<'grid' | 'list'>('grid');

    const ASSET_TAB_IDS = ['assets', 'correlation'] as const;
    type AssetTabId = (typeof ASSET_TAB_IDS)[number];
    let activeTab = $state<AssetTabId>('assets');
    /**
     * The lab, when the correlation tab mounts it. The toolbar's sync and reload act
     * on its selection there (`openSync`, `reload`), and `labCanSync` keeps the sync
     * off while the selection has nothing to sync.
     */
    let labPanel = $state<ReturnType<typeof AssetSetRiskPanel>>();
    let labCanSync = $state(false);
    let assetTabs = $derived([
        {id: 'assets', label: $t('risk.assetSet.assetsTab'), icon: BarChart3, testId: 'assets-tab-list'},
        {id: 'correlation', label: $t('risk.assetSet.correlationTab'), icon: Network, testId: 'assets-tab-correlation'},
    ]);

    $effect(() => {
        activeTab = getResolvedTabParam($page.url.searchParams, ASSET_TAB_IDS, 'assets');
    });

    function handleAssetTabChange(tabId: string): void {
        if (!ASSET_TAB_IDS.includes(tabId as AssetTabId)) return;
        activeTab = tabId as AssetTabId;
        void goto(buildTabUrl($page.url, tabId), {replaceState: true, noScroll: true});
    }

    // The view of the grid's cards (Y-40): the list's, saved with the chart settings, which the top bar sets for every card;
    // a card's button keeps its own (V-1 a, V-3 a).
    let globalPrimaryView = $derived.by((): ChartPrimaryView => {
        void getSettingsVersion();
        return getGlobalSettings('assets').primaryView;
    });
    /** The rolling return of each card in the rolling-return view, and its comparisons' (Y-40), by card. */
    let calendarByCard = $state(new Map<number, {own: CalendarReturnView; targets: Map<number, CalendarReturnView>}>());

    // Asset type → icon: getAssetTypeIconUrl() is the single source. The local
    // TYPE_ICON_MAP that used to live here knew nine types, so every value added to
    // ALL_ASSET_TYPES below would have been drawn as other.png in this very dropdown.
    const ALL_ASSET_TYPES = ['STOCK', 'ETF', 'BOND', 'CRYPTO', 'FUND', 'CROWDFUND', 'HOLD', 'COMMODITY', 'REAL_ESTATE', 'INDEX', 'OTHER', 'ETF_STOCK', 'ETF_BOND', 'ETF_COMMODITY', 'ETF_REAL_ESTATE', 'ETF_CRYPTO', 'ETF_MONETARY', 'CROWDFUND_REAL_ESTATE'] as const;

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

    // Type filter dropdown. Round 14 bugfix: the panel is `position:fixed` (computed via
    // getFixedDropdownPosition) instead of `absolute` — PageToolbar's own card wrapper has
    // `overflow-hidden`, which was clipping this panel whenever it would visually overflow the
    // card's rounded-corner bounds. Same technique dashboard's broker-filter/AI-export
    // dropdowns already use.
    let typeFilterOpen = $state(false);
    let typeFilterTriggerEl = $state<HTMLButtonElement | null>(null);
    let typeFilterPanelEl = $state<HTMLDivElement | null>(null);
    let typeFilterDropdownPosition = $state({left: 8, top: 8});

    // Chart settings modal (D4)
    let settingsModalOpen = $state(false);
    let settingsTargetId = $state<string | null>(null);
    let settingsForModal = $derived(settingsTargetId ? getSettingsForPair(`asset-${settingsTargetId}`, 'assets') : getGlobalSettings('assets'));
    let signalDefinitions = $state<SignalDefinition[]>([]);
    let signalResultsByAsset = $state(new Map<number, SignalInstanceResult[]>());
    let signalCatalogFailed = $state(false);
    let signalRequestFailed = $state(false);
    const signalResultStates = new Map<number, SignalResultState>();
    /**
     * The comparison targets of each card, sampled like the card (Z-29b), by `<card>|<target>`: what its comparison
     * signals draw, with the target's own point on the day the comparison starts as the percentage base.
     */
    let targetSamples = $state(new Map<string, ReducedEntry>());
    /** The plot width each card reported (`AssetCard`'s `onplotwidth`), in pixels; what its `max_points` is sized by. */
    const plotWidths = new Map<number, number>();
    let signalBackendError = $derived(signalCatalogFailed ? $t('chartSettings.signalCatalogUnavailable') : signalRequestFailed ? $t('chartSettings.signalResultsUnavailable') : null);

    // FX pair slugs for cross-domain signal selection (loaded lazily)
    let fxPairSlugs = $state<string[]>([]);

    // =========================================================================
    // Derived
    // =========================================================================

    let signalDefinitionsByType = $derived(new Map(signalDefinitions.map((definition) => [definition.type, definition])));

    // Extract unique currencies from all assets
    let configuredCurrencies = $derived([...new Set(assets.map((a) => a.currency))].sort());

    let filteredAssets = $derived(
        orderAssetsByLifecycle(
            assets.filter((a) => {
                if (!matchesAssetLifecycle(a.active, filterShowActive, filterShowInactive)) return false;
                if (filterTypes.size > 0 && !filterTypes.has(a.asset_type ?? '')) return false;
                if (filterCurrencies.size > 0 && !filterCurrencies.has(a.currency)) return false;
                if (searchText) {
                    const q = searchText.toLowerCase();
                    if (!a.display_name.toLowerCase().includes(q)) return false;
                }
                return true;
            }),
        ),
    );

    // The Δ columns (1D … 5Y): the backend computes them up to the end of the range and lists the periods (X-R53).
    // Kept apart from the price flow, so a price refresh never wipes them. Which answer is kept while several are in
    // flight, the ledger says (X-R60); `periodChangesLoading` copies its `busy`.
    let periodSpecs = $state<PeriodSpec[]>([]);
    let periodDeltas = $state<Map<number, PeriodDeltas>>(new Map());
    let periodChangesLoading = $state(false);
    const periodChangesLedger = new PeriodChangesLedger<number>();
    // The cards' Δ over the whole range comes in the same answer (X-R59), kept by a ledger of its own: it belongs to the
    // range's first day too, so a failed request keeps only the values of the same range (`rangeKey`).
    let rangeDeltas = $state<Map<number, RangeDelta>>(new Map());
    const rangeDeltaLedger = new PeriodChangesLedger<number>();

    /** The identity of a range for the range-Δ ledger: both its days. */
    function rangeKey(start: string, end: string): string {
        return `${start}…${end}`;
    }

    // Which delta periods are visible for the selected date range
    let visiblePeriods = $derived(visiblePeriodColumns(periodSpecs, dateStart, dateEnd));

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
            quote_base_quantity: a.quote_base_quantity,
            lastPrice: a.lastPrice,
            deltas: periodDeltas.get(a.id) ?? {},
            txCount: a.tx_count ?? 0,
            txScope: assetScope(a),
        })),
    );

    // =========================================================================
    // F15 — usage panels: "yours", "other users'", "watched". This grouping is
    // unrelated to the active/inactive lifecycle flags above.
    //
    // Since the developer's decision of 24/09 (Risk, time ②) the panels read what
    // is held **now**, not who ever traded: `tx_count_own > 0` kept a position sold
    // years ago among "yours". An asset you no longer hold moves to "other users'"
    // when someone else holds it now, and to "watched" otherwise. The flags come
    // from the asset list (`held_by_me`, `held_by_others`).
    // =========================================================================
    type AssetScope = 'own' | 'others' | 'analysis';

    function assetScope(a: {held_by_me?: boolean; held_by_others?: boolean}): AssetScope {
        if (a.held_by_me) return 'own';
        if (a.held_by_others) return 'others';
        return 'analysis';
    }

    let ownAssets = $derived(filteredAssets.filter((a) => assetScope(a) === 'own'));
    let otherAssets = $derived(filteredAssets.filter((a) => assetScope(a) === 'others'));
    let analysisAssets = $derived(filteredAssets.filter((a) => assetScope(a) === 'analysis'));
    let assetPanels = $derived([
        {id: 'own' as const, items: ownAssets},
        {id: 'others' as const, items: otherAssets},
        {id: 'analysis' as const, items: analysisAssets},
    ]);

    // =========================================================================
    // Lifecycle
    // =========================================================================

    async function loadAssetSignalDefinitions(force = false) {
        try {
            signalDefinitions = await signalCatalogStore.load('asset', force);
            signalCatalogFailed = false;
        } catch (catalogError) {
            console.error('Failed to load Asset signal catalog:', catalogError);
            signalDefinitions = getLocalSignalDefinitions();
            signalCatalogFailed = true;
        }
    }

    function resultStateForAsset(assetId: number): SignalResultState {
        let state = signalResultStates.get(assetId);
        if (!state) {
            state = new SignalResultState();
            signalResultStates.set(assetId, state);
        }
        return state;
    }

    function backendRequestFingerprint(configs: SignalConfig[]): string {
        return JSON.stringify(
            buildBackendSignalRequestPlan(configs, signalDefinitions)
                .requests.map((request) => `${request.signal_code}:${JSON.stringify(request.params ?? {})}`)
                .sort(),
        );
    }

    async function retryBackendSignals() {
        await pageBusy.track('assets-signals-retry', async () => {
            await loadAssetSignalDefinitions(true);
            // The prices and the signals only: the Δ columns do not depend on the signals (X-R60).
            await fetchPriceSeries();
        });
    }

    onMount(async () => {
        // The first load holds the page's Refresh button (Y11); the live poll never does (P3).
        await pageBusy.track('assets-first-load', async () => {
            await loadAssetSignalDefinitions();
            await loadAssets();
        });
        // Load FX pair slugs for cross-domain signal selection in settings modal
        loadFxPairSlugs();
        onboardingGuide.maybeStartContextual('asset_page_guide');
    });

    /**
     * The set of assets the live poll asks about, as a stable key.
     *
     * The poll's effect used to read `assets` itself — directly, and through the
     * synchronous head of `fetchLivePrices` — so it re-ran on every reassignment of
     * the list. `fetchAllPriceData` reassigns it up to four times per refresh, and
     * every re-run fired an immediate `POST /assets/prices/current`: a write of
     * today's prices, and a portfolio mutation that drops every report and risk
     * answer in flight (`portfolioMutation.ts`). A string compares by value, so this
     * stays put while the ids do, and the effect re-runs only when the set of assets
     * really changes.
     */
    let liveAssetIdsKey = $derived(
        assets
            .map((asset) => asset.id)
            .sort((left, right) => left - right)
            .join(','),
    );

    /**
     * One live poll, now — for the refreshes a user asks for. The poll used to
     * re-fire on those as a side effect of the reassignments above; keeping that
     * immediacy is deliberate, and it costs one write per click instead of four.
     * The cadence restarts from it, so a refresh is never followed by a tick a
     * few seconds later. No poller, no poll: the range does not end today, or
     * the list is empty.
     */
    function refreshLivePricesNow(): void {
        livePoller?.pollNow();
    }

    // Live price polling — while the date range ends today, every minute, and only
    // while someone uses the page: hidden tab or two minutes without input pause it,
    // and it resumes by itself (F26, decision 31).
    $effect(() => {
        if (!isHeadToday || liveAssetIdsKey === '') {
            livePriceMap = new Map();
            liveUpdatesState = 'stopped';
            return;
        }
        // The poller calls `fetchLivePrices` from a timer, never inside this effect: its
        // synchronous head reads `assets`, which would subscribe the effect to the whole
        // list again (see `liveAssetIdsKey`).
        const poller = startActivePolling({
            run: fetchLivePrices,
            intervalMs: ASSET_LIST_LIVE_INTERVAL_MS,
            onstatechange: (state) => (liveUpdatesState = state),
        });
        livePoller = poller;
        return () => {
            poller.stop();
            if (livePoller === poller) livePoller = null;
        };
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

    async function positionTypeFilterDropdown() {
        await tick();
        if (!typeFilterOpen) return;
        typeFilterDropdownPosition = getFixedDropdownPosition(typeFilterTriggerEl, typeFilterPanelEl, 'start');
    }

    function toggleTypeFilterDropdown() {
        typeFilterOpen = !typeFilterOpen;
        if (typeFilterOpen) void positionTypeFilterDropdown();
    }

    // Recompute the fixed position while open (initial open + any resize/scroll) — same
    // pattern as dashboard's broker-filter/AI-export dropdowns.
    $effect(() => {
        if (!typeFilterOpen) return;
        void positionTypeFilterDropdown();
    });

    $effect(() => {
        if (!typeFilterOpen) return;

        const handleViewportChange = () => void positionTypeFilterDropdown();
        window.addEventListener('resize', handleViewportChange);
        window.addEventListener('scroll', handleViewportChange, true);

        return () => {
            window.removeEventListener('resize', handleViewportChange);
            window.removeEventListener('scroll', handleViewportChange, true);
        };
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
                tx_count: item.tx_count ?? 0,
                held_by_me: item.held_by_me ?? false,
                held_by_others: item.held_by_others ?? false,
                lastPrice: null,
                chartData: [],
                // Born already waiting for wave 2, so the row draws its own
                // skeleton the instant it appears instead of a bare empty cell.
                loadingPrices: true,
            }));
        } catch (e: any) {
            console.error('Failed to load assets:', e);
            error = e?.message || 'Failed to load assets';
        } finally {
            loading = false;
        }

        // Wave 2 — prices, signals, "All" resolution — deliberately OUTSIDE the
        // `loading` window. The list and the prices are two separate calls, so
        // there is no reason to hold the whole page behind a spinner until both
        // are back: rows render at once and fill in per-row (loading=
        // {asset.loadingPrices}). fetchAllPriceData() owns its own errors and
        // clears loadingPrices on every path, so nothing here can strand a row.
        // `data-busy` (loading, any loadingPrices, the period changes in flight)
        // stays the single signal for "both waves finished".
        if (!error) await fetchAllPriceData();
    }

    /**
     * When "All" (MAX) is pending resolution, extract the real earliest date
     * across ALL loaded assets (global minimum) and update dateStart/
     * displayDateStart. The URL is left untouched — it keeps showing the
     * generic "min"/"max" sentinel (set in handleDateRangeChange) so the
     * "All" selection survives reloads/shares instead of freezing to a
     * specific historical date. No-op once already resolved or if no asset
     * has any price data yet. The earliest date of an asset is the first day of its fill (`base`):
     * on a sampled series its first point is the end of the first bucket (Z-29b).
     */
    /** An asset's prices changed (a sync, a refresh, a merge): the daily cache and the cards' sampled one forget it. */
    function invalidateAssetPrices(assetId: number) {
        invalidateAssetPriceStore(assetId);
        reducedPrices.invalidateAsset(assetId);
    }

    function resolveMaxStartFromAssets() {
        if (!isMaxPending) return;
        const firstDates = assets.map((a) => a.base?.date ?? a.chartData?.[0]?.date).filter((d): d is string => !!d);
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

    /**
     * Prices and signals (the price query, the cache) and the Δ columns (the backend's period changes), together. The
     * signals' retry and a settings change ask only the prices and signals (`fetchPriceSeries`): the Δ columns depend
     * on neither (X-R60).
     */
    async function fetchAllPriceData() {
        if (assets.length === 0) return;
        await Promise.all([fetchPriceSeries(), loadPeriodChanges()]);
    }

    /** The Δ columns of every listed asset up to the end of the range, and each card's Δ over the range, from the backend (X-R53, X-R59). */
    async function loadPeriodChanges() {
        const ticket = periodChangesLedger.begin(dateEnd, true);
        const rangeStart = dateStart;
        const rangeTicket = rangeDeltaLedger.begin(rangeKey(rangeStart, ticket.asOf), true);
        periodChangesLoading = periodChangesLedger.busy || rangeDeltaLedger.busy;
        try {
            const result = await fetchAssetPeriodChanges(
                assets.map((asset) => asset.id),
                ticket.asOf,
                rangeStart,
            );
            const nextRange = rangeDeltaLedger.settle(rangeTicket, rangeDeltas, result.rangeDeltaByAssetId);
            if (nextRange !== null) rangeDeltas = nextRange;
            const next = periodChangesLedger.settle(ticket, periodDeltas, result.deltasByAssetId);
            if (next === null) return;
            if (result.periods.length > 0) periodSpecs = result.periods;
            periodDeltas = next;
        } catch (e: any) {
            // The Δ computed up to the same day stay: only those of another range go (X-R60); the cards' Δ, only for the same range.
            const nextRange = rangeDeltaLedger.fail(rangeTicket, rangeDeltas);
            if (nextRange !== null) rangeDeltas = nextRange;
            const next = periodChangesLedger.fail(ticket, periodDeltas);
            if (next === null) return;
            console.error('Failed to fetch period changes:', e);
            periodDeltas = next;
        } finally {
            periodChangesLedger.end(ticket);
            rangeDeltaLedger.end(rangeTicket);
            periodChangesLoading = periodChangesLedger.busy || rangeDeltaLedger.busy;
        }
    }

    /**
     * The point of an asset's card on screen from a series the backend sampled for it (or none: what the card already drew
     * stays, a stale-but-valid previous read included, and only its loading flag clears).
     */
    function assetWithEntry(asset: AssetState, entry: ReducedEntry | null): AssetState {
        if (!entry || entry.derived.chartData.length === 0) return {...asset, loadingPrices: false};
        return {...asset, ...entry.derived, resolution: entry.resolution, loadingPrices: false};
    }

    /**
     * The rolling return a card in that view asks (Y-40): over the window in force for the range on screen — the one chosen,
     * else the largest preset that fits it.
     */
    function calendarReturnRequest(settings: ChartSettings, start: string, end: string) {
        const windowDays = calendarReturnWindowDays(effectiveCalendarReturnWindow(settings, calendarReturnRangeDays(start, end))) ?? 30;
        return {instance_id: CALENDAR_RETURN_INSTANCE_ID, signal_code: CALENDAR_RETURN_SIGNAL_CODE, params: {window_days: windowDays}};
    }

    /** The view a card shows: its own saved one, else the list's (Y-40). */
    function cardPrimaryView(assetId: number): ChartPrimaryView {
        void getSettingsVersion();
        return getSettingsForPair(`asset-${assetId}`, 'assets').primaryView;
    }

    /** The top bar (V-3 a): every card takes the view; the cards that enter or leave the rolling return ask their data again. */
    function handleListPrimaryView(view: ChartPrimaryView) {
        const toCalendar = view === 'calendar-return';
        const changed = assets.filter((asset) => (cardPrimaryView(asset.id) === 'calendar-return') !== toCalendar).map((asset) => asset.id);
        setScopePrimaryView(view, 'assets');
        if (changed.length > 0) void pageBusy.track('assets-view', () => fetchPriceSeries(new Set(changed)));
    }

    /** A card's button (V-1 a): that card keeps the view; entering or leaving the rolling return, it asks its data again. */
    function handleCardPrimaryView(assetId: number, view: ChartPrimaryView) {
        const wasCalendar = cardPrimaryView(assetId) === 'calendar-return';
        setItemPrimaryView(`asset-${assetId}`, view, 'assets');
        if (wasCalendar !== (view === 'calendar-return')) void pageBusy.track('assets-view', () => fetchPriceSeries(new Set([assetId])));
    }

    function translateCalendarProblem(key: string, values?: Record<string, string | number>): string {
        return values ? $t(key, {values}) : $t(key);
    }

    /** A card's rolling return, with the detail's message when the backend has none (V-7 a). */
    function cardCalendarReturn(assetId: number) {
        const view = calendarByCard.get(assetId)?.own ?? emptyCalendarReturnView('loading');
        const problemMessage = view.problem ? formatSignalProblem(view.problem, translateCalendarProblem, (field) => $t(`signals.dataFields.${field}`)) : view.state === 'error' ? $t('chartSettings.signalResultsUnavailable') : null;
        return {state: view.state, points: view.points, problemCode: view.problem?.code ?? null, problemMessage};
    }

    /** A card's comparisons in the rolling-return view: their targets' returns (V-5 a), drawn as the detail draws them. */
    function cardCalendarOverlays(assetId: number): RenderedSignal[] {
        const views = calendarByCard.get(assetId)?.targets;
        if (!views) return [];
        const target = (id: number) => {
            const asset = assets.find((item) => item.id === id);
            return asset ? {displayName: asset.display_name, iconUrl: asset.icon_url, assetType: asset.asset_type} : null;
        };
        return renderCalendarComparisons(getSettingsForPair(`asset-${assetId}`, 'assets').signals, views, target, (id) => $t('chartSettings.signals.assetFallback', {values: {id: String(id)}}), assetId);
    }

    /**
     * The prices and backend signals of the cards (Z-29b). Each card asks for the series its plot takes, one point a day, a
     * week or a month (`max_points` from its measured width; `utils/reducedPriceQuery.ts`), and each comparison target for
     * the same buckets (`sample_like`). Only what the reduced cache (`stores/reducedPriceCache.ts`) does not hold, or holds
     * for another step or stale, is asked; the answers go to the cache and the cards draw them as they are. `only` limits it
     * to some cards: a settings change reloads its own card, a width that changes the step its own.
     */
    async function fetchPriceSeries(only?: ReadonlySet<number>) {
        if (assets.length === 0) return;
        void getSettingsVersion();

        const wanted = only ? assets.filter((asset) => only.has(asset.id)) : assets;
        if (wanted.length === 0) return;
        const wantedIds = new Set(wanted.map((asset) => asset.id));
        const listedIds = new Set(assets.map((asset) => asset.id));
        // The range the answers belong to: the page may move on while the request is in flight.
        const rangeStart = dateStart;
        const rangeEnd = dateEnd;

        const cards: CardQueryInput[] = [];
        const cached = new Map<number, ReducedEntry>();
        const needFetchIds = new Set<number>();
        const requestContexts = new Map<
            number,
            {
                configs: SignalConfig[];
                plan: ReturnType<typeof buildBackendSignalRequestPlan>;
                requestVersion: number;
            }
        >();
        const nextSignalResults = new Map(signalResultsByAsset);
        const nextTargetSamples = new Map(targetSamples);
        /** The cards in the rolling-return view (Y-40): each asks its return, and its comparisons' on its buckets. */
        const calendarCards = new Set<number>();

        for (const asset of wanted) {
            const settings = getSettingsForPair(`asset-${asset.id}`, 'assets');
            const calendarRequest = settings.primaryView === 'calendar-return' ? calendarReturnRequest(settings, rangeStart, rangeEnd) : null;
            if (calendarRequest) calendarCards.add(asset.id);
            // V-5 a: in the rolling-return view the comparisons are the only signals; the others stay saved and are not asked.
            const configs = calendarRequest ? [] : settings.signals;
            const plan = buildBackendSignalRequestPlan(configs, signalDefinitions);
            const state = resultStateForAsset(asset.id);
            const requestVersion = state.beginRequest();
            requestContexts.set(asset.id, {configs, plan, requestVersion});

            const plotWidthPx = plotWidths.get(asset.id) ?? DEFAULT_COMPACT_PLOT_WIDTH_PX;
            const own = reducedPrices.getCard(asset.id, rangeStart, rangeEnd, compactMaxPoints(plotWidthPx));
            const needsPrice = own === null || own.stale;
            if (own) cached.set(asset.id, own);
            if (needsPrice) needFetchIds.add(asset.id);

            const targetIds = comparisonTargetIds(settings.signals, asset.id).filter((id) => listedIds.has(id));
            const prefix = `${asset.id}|`;
            for (const key of [...nextTargetSamples.keys()]) {
                if (key.startsWith(prefix) && !targetIds.includes(Number(key.slice(prefix.length)))) nextTargetSamples.delete(key);
            }
            const targets = targetIds.map((assetId) => {
                const sample = own ? reducedPrices.getTarget(assetId, asset.id, rangeStart, rangeEnd, own.resolution) : null;
                if (sample) nextTargetSamples.set(`${asset.id}|${assetId}`, sample);
                return {assetId, needsRead: needsPrice || sample === null || sample.stale};
            });
            cards.push({
                assetId: asset.id,
                plotWidthPx,
                start: rangeStart,
                end: rangeEnd,
                needsPrice,
                signals: calendarRequest ? [calendarRequest] : plan.requests,
                targets,
                // The comparisons' returns in the card's currency, as the detail page asks them.
                ...(calendarRequest ? {calendar: {signals: [calendarRequest], targetCurrency: asset.currency}} : {}),
            });
        }

        // The cards leaving the rolling-return view drop their returns; those in it keep theirs on screen while the new ones load.
        const nextCalendar = new Map(calendarByCard);
        for (const asset of wanted) {
            const previous = nextCalendar.get(asset.id);
            if (!calendarCards.has(asset.id)) nextCalendar.delete(asset.id);
            else nextCalendar.set(asset.id, {own: {...(previous?.own ?? emptyCalendarReturnView()), state: 'loading'}, targets: previous?.targets ?? new Map()});
        }
        calendarByCard = nextCalendar;

        const entries = buildReducedQuery(cards);
        const sentCardIds = new Set(entries.map((entry) => entry.cardId));
        // A card with nothing to ask has no backend signals either: its signal results are emptied, as for a card without any.
        for (const [assetId, context] of requestContexts) {
            if (sentCardIds.has(assetId)) continue;
            const state = resultStateForAsset(assetId);
            const mapped = mapSignalInstanceResults(context.configs, context.plan, []);
            if (state.apply(context.requestVersion, mapped)) {
                nextSignalResults.set(assetId, [...state.values()]);
            }
        }

        // If everything is cached and no backend signals are selected, update instantly.
        if (entries.length === 0) {
            assets = assets.map((asset) => (wantedIds.has(asset.id) ? assetWithEntry(asset, cached.get(asset.id) ?? null) : asset));
            signalResultsByAsset = nextSignalResults;
            targetSamples = nextTargetSamples;
            signalRequestFailed = false;
            resolveMaxStartFromAssets();
            return;
        }

        refreshing = true;
        signalRequestFailed = false;
        assets = assets.map((a) => (wantedIds.has(a.id) ? {...a, loadingPrices: needFetchIds.has(a.id)} : a));

        try {
            // One request for the cards with something to ask while it stays under the backend's caps: the backend then runs
            // one SQL query for all of them. A larger list is split into batches (lot Z-27, `lib/api/bulkBatches.ts`) cut
            // between cards, never between a card and its targets (they name its `key`), sent one after the other and applied
            // together at the end. Each batch uses axiosInstance directly (bypassing Zodios' automatic response validation)
            // so its raw, not-yet-validated body can be handed to the shared worker pool: validating + computing derived
            // state for every asset in one synchronous main-thread block was what monopolized the thread long enough to
            // delay click/navigation handling on large "ALL date range" loads.
            const today = todayIso();
            const outcome = await sendBulkBatches(
                entries,
                (entry) => estimateEntryDays(entry, today),
                async (batch) => {
                    const rawResponse = await axiosInstance.post(
                        '/api/v1/assets/prices/query',
                        batch.map((entry) => entry.item),
                    );
                    const rawItems: unknown[] = rawResponse.data?.items ?? [];
                    return processPriceItemsInParallel(rawItems);
                },
                {groupOf: (entry) => entry.group},
            );
            const invalidItemErrors = outcome.answers.flatMap(({answer}) => answer.invalidItemErrors);
            if (invalidItemErrors.length > 0) {
                console.error('Some price-query items failed validation:', invalidItemErrors);
            }
            // The cards of a batch that got no answer are left as the catch below leaves them:
            // their cache kept, their signals untouched and reported as failed.
            const answeredCardIds = new Set(outcome.answers.flatMap(({batch}) => batch.items.map((entry) => entry.cardId)));
            const unansweredCardIds = new Set([...sentCardIds].filter((assetId) => !answeredCardIds.has(assetId)));
            if (outcome.failed) {
                console.error('Failed to fetch prices bulk:', outcome.error);
                // X-R58: a request the backend refused as too large is said, not left as cards without prices.
                const refusal = bulkRefusalMessage(outcome.error, $t);
                if (refusal !== null) toasts.error(refusal);
            }
            const sentContexts = [...requestContexts].filter(([assetId]) => sentCardIds.has(assetId));
            const anySignals = sentContexts.some(([, context]) => context.plan.requests.length > 0);
            const unansweredSignals = sentContexts.some(([assetId, context]) => unansweredCardIds.has(assetId) && context.plan.requests.length > 0);
            signalRequestFailed = (invalidItemErrors.length > 0 && anySignals) || unansweredSignals;

            // Put what was read into the cache (cheap: Map.set calls); a result is tied to its entry by its position in the batch.
            const read = new Map<number, ReducedEntry>();
            const signalsByCard = new Map<number, ProcessedAssetResult['signals']>();
            const calendarTargets = new Map<number, Map<number, CalendarReturnView>>();
            for (const {batch, answer} of outcome.answers) {
                for (const result of answer.results) {
                    const entry = batch.items[result.requestIndex];
                    if (!entry) continue;
                    if (entry.role === 'target' && calendarCards.has(entry.cardId)) {
                        // A comparison's return, asked without prices: its sample in the cache is not touched.
                        if (!calendarTargets.has(entry.cardId)) calendarTargets.set(entry.cardId, new Map());
                        calendarTargets.get(entry.cardId)!.set(entry.targetId!, extractCalendarReturnView(result.signals, CALENDAR_RETURN_INSTANCE_ID));
                        continue;
                    }
                    if (entry.role === 'target') {
                        nextTargetSamples.set(`${entry.cardId}|${entry.targetId}`, reducedPrices.putTarget(entry.targetId!, entry.cardId, rangeStart, rangeEnd, {resolution: result.resolution, derived: result.derived}));
                        continue;
                    }
                    signalsByCard.set(entry.cardId, result.signals);
                    // An item without prices (its signals only, or a step for its targets) has no series to keep.
                    if (entry.item.include_price) read.set(entry.cardId, reducedPrices.putCard(entry.cardId, rangeStart, rangeEnd, {resolution: result.resolution, derived: result.derived}));
                }
            }

            for (const [assetId, context] of sentContexts) {
                if (unansweredCardIds.has(assetId)) continue;
                const state = resultStateForAsset(assetId);
                const mapped = mapSignalInstanceResults(context.configs, context.plan, signalsByCard.get(assetId) ?? []);
                if (state.apply(context.requestVersion, mapped)) {
                    nextSignalResults.set(assetId, [...state.values()]);
                }
            }
            signalResultsByAsset = nextSignalResults;
            targetSamples = nextTargetSamples;
            const answeredCalendar = new Map(calendarByCard);
            for (const assetId of calendarCards) {
                const previous = answeredCalendar.get(assetId);
                if (!previous) continue;
                answeredCalendar.set(assetId, unansweredCardIds.has(assetId) ? {own: {...previous.own, state: 'error'}, targets: previous.targets} : {own: extractCalendarReturnView(signalsByCard.get(assetId) ?? [], CALENDAR_RETURN_INSTANCE_ID), targets: calendarTargets.get(assetId) ?? new Map()});
            }
            calendarByCard = answeredCalendar;

            // The series read now, else the cached one (a card that asked only for its targets or signals).
            assets = assets.map((asset) => (wantedIds.has(asset.id) ? assetWithEntry(asset, read.get(asset.id) ?? cached.get(asset.id) ?? null) : asset));
            // As before a failure: «All» resolves only from a complete load, never from part of it.
            if (!outcome.failed) resolveMaxStartFromAssets();
        } catch (e: any) {
            console.error('Failed to fetch prices bulk:', e);
            signalRequestFailed = [...requestContexts.values()].some((context) => context.plan.requests.length > 0);
            const failedCalendar = new Map(calendarByCard);
            for (const assetId of calendarCards) {
                const previous = failedCalendar.get(assetId);
                if (previous) failedCalendar.set(assetId, {own: {...previous.own, state: 'error'}, targets: previous.targets});
            }
            calendarByCard = failedCalendar;
            // For cached assets, still use cached data; for others, clear loading
            assets = assets.map((a) => (wantedIds.has(a.id) ? assetWithEntry(a, cached.get(a.id) ?? null) : a));
        } finally {
            refreshing = false;
            // A card measured while this was in flight asked for its width then: look again.
            scheduleWidthReload([...plotWidths.keys()]);
        }
    }

    // =========================================================================
    // The cards' widths (Z-29b)
    // =========================================================================

    let widthReloadTimer: ReturnType<typeof setTimeout> | undefined;
    const widthReloadIds = new Set<number>();
    /** The width and range each card was last reloaded for: a card is read again once for a width, however its answer reads. */
    const widthReloaded = new Map<number, string>();

    /** A card's plot was measured or changed width: remember it, and look at whether its series still fits. */
    function handlePlotWidth(assetId: number, plotWidthPx: number) {
        if (plotWidths.get(assetId) === plotWidthPx) return;
        plotWidths.set(assetId, plotWidthPx);
        scheduleWidthReload([assetId]);
    }

    /** Debounced: a resize drag fires many measures, and only the width it settles on matters (MF n2). */
    function scheduleWidthReload(assetIds: Iterable<number>) {
        for (const id of assetIds) widthReloadIds.add(id);
        clearTimeout(widthReloadTimer);
        widthReloadTimer = setTimeout(reloadCardsOfAnotherStep, 250);
    }

    /**
     * The cards whose width now asks another step than the series they hold are read again, each from the backend: a
     * weekly sample is never re-aggregated into months, nor turned back into days (MF n2). A width that keeps the step reads
     * nothing, and a card still loading is left to the read in flight (it looks again when it ends).
     */
    function reloadCardsOfAnotherStep() {
        const candidates = [...widthReloadIds];
        widthReloadIds.clear();
        if (loading || refreshing) {
            for (const id of candidates) widthReloadIds.add(id);
            return;
        }
        const changed = cardsOfAnotherStep(candidates, (id) => {
            const asset = assets.find((item) => item.id === id);
            const width = plotWidths.get(id);
            return {
                settled: asset !== undefined && !asset.loadingPrices && asset.chartData.length > 0,
                plotWidthPx: width,
                holds: (maxPoints) => reducedPrices.getCard(id, dateStart, dateEnd, maxPoints) !== null,
                reloadedForWidth: widthReloaded.get(id) === `${width}|${dateStart}|${dateEnd}`,
            };
        });
        for (const id of changed) widthReloaded.set(id, `${plotWidths.get(id)}|${dateStart}|${dateEnd}`);
        if (changed.length > 0) void fetchPriceSeries(new Set(changed));
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
        void pageBusy.track('assets-period', () => fetchAllPriceData());
    }

    /** Fetch live current prices for all assets (fire-and-forget, non-blocking); the outcome spaces the next poll (Z7). */
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
            return livePollOutcome(results);
        } catch (e: any) {
            console.warn('[Assets] fetchLivePrices error (non-critical):', e?.message);
            return livePollFailure(e);
        }
    }

    // =========================================================================
    // Actions
    // =========================================================================

    function openAssetCreate() {
        assetEditRequest += 1;
        assetEditLoading = false;
        assetModalEditMode = false;
        assetModalEditData = null;
        assetModalOpen = true;
    }

    function handleAddAsset() {
        if (onboardingGuide.active?.flow === 'asset_page_guide') {
            onboardingGuide.dismissHost();
        }
        assetTourPreview = false;
        openAssetCreate();
        onboardingGuide.maybeStartContextual('asset_guide');
    }

    async function handleEditAsset(asset: {id: number}) {
        const request = ++assetEditRequest;
        const session = getClientSessionGeneration();
        assetEditLoading = true;
        try {
            const data = await loadAssetEditData(asset.id);
            if (request !== assetEditRequest || !isClientSessionCurrent(session)) return;
            assetModalEditMode = true;
            assetModalEditData = data;
            assetModalOpen = true;
        } catch (error: unknown) {
            if (request === assetEditRequest && isClientSessionCurrent(session)) toasts.error(extractErrorMessage(error, $t('common.errorOccurred')));
        } finally {
            if (request === assetEditRequest) assetEditLoading = false;
        }
    }

    /** The toast of one asset's sync: the points fetched and changed, or the failure with its first error. */
    function reportSyncResult(asset: any, r: AssetCreateSyncResult | null | undefined, linkCreatedAsset = false) {
        if (r && (!r.errors || r.errors.length === 0)) {
            const fetched = r.points_fetched ?? 0;
            const changed = (r.inserted_count ?? 0) + (r.updated_count ?? 0);
            toasts.success(
                $t('assets.sync.toastOk', {
                    values: {name: linkCreatedAsset ? entityDetailLinkHtml({kind: 'asset', id: asset.id}, asset.display_name) : escapeHtml(asset.display_name), fetched, changed},
                }),
            );
        } else {
            toasts.error(
                $t('assets.sync.toastFailed', {
                    values: {name: asset.display_name},
                }) + (r?.errors?.[0] ? ': ' + r.errors[0] : ''),
            );
        }
    }

    /** A new asset is listed at once; with a provider, its card shows the one sync AssetModal runs for it (O-20). */
    async function handleAssetCreated(assetId: number, detail?: {syncing: boolean}) {
        if (detail?.syncing) syncingAssetIds = new Set([...syncingAssetIds, assetId]);
        // A reload after the user's own write: it holds the page's Refresh button (Y11). The sync that follows has
        // the card's indicator, and the reload after it (`handleCreatedAssetSynced`) does not hold the button (P3).
        await pageBusy.track('assets-reload', () => loadAssets());
    }

    /** The one sync of a new asset ended (AssetModal, O-20): its toast, then the price data again. */
    async function handleCreatedAssetSynced(assetId: number, result: AssetCreateSyncResult | null) {
        try {
            if (!assets.some((a) => a.id === assetId)) await loadAssets();
            const created = assets.find((a) => a.id === assetId);
            if (created) reportSyncResult(created, result, true);
            invalidateAssetPrices(assetId);
            rearmMaxPendingBeforeReload();
            await fetchAllPriceData();
        } finally {
            syncingAssetIds = new Set([...syncingAssetIds].filter((id) => id !== assetId));
        }
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
            reportSyncResult(asset, (response as any)?.results?.[0]);
            invalidateAssetPrices(asset.id);
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
        invalidateAssetPrices(asset.id);
        rearmMaxPendingBeforeReload();
        await fetchAllPriceData();
    }

    /** The confirmation's row for an asset its transactions keep, with the link to them (X-R18). */
    function blockedDeleteResult(asset: {id: number; display_name: string}, count: number, label?: string) {
        return {
            label: label || asset.display_name,
            success: false,
            detail: `${$t('assets.delete.resultHasTransactions')} (${count})`,
            action: {
                href: buildTransactionsFiltersUrl({asset_id: asset.id}),
                label: $t('transactions.title'),
                testId: 'asset-delete-transactions-link',
            },
        };
    }

    function handleDeleteAsset(asset: any) {
        deletingAsset = asset;
        // X-R18: the list row already counts the asset's transactions (every broker), and any refuses the delete:
        // the confirmation opens already blocked, with the link, instead of asking for what cannot happen. A card
        // hands over a slimmer object, so the row is found by id. At 0 it asks, and the backend still decides.
        const txCount = assets.find((row) => row.id === asset.id)?.tx_count ?? 0;
        singleDeleteResults = txCount > 0 ? [blockedDeleteResult(asset, txCount)] : [];
        deleteDialogOpen = true;
    }

    function handleMergeAsset(asset: any) {
        mergingAsset = asset;
        mergeModalOpen = true;
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
                // cell, dashboard) drop the deleted asset without a reload.
                invalidateAfterMutation(deletingAsset.id);
                assets = assets.filter((a) => a.id !== deletingAsset!.id);
                toasts.success($t('assets.delete.toastOk', {values: {name: deletingAsset!.display_name}}));
                deleteDialogOpen = false;
                deletingAsset = null;
            } else if (r?.error_code === 'HAS_TRANSACTIONS') {
                singleDeleteResults = [blockedDeleteResult(deletingAsset, Number(r.transaction_count ?? 0), r.display_name)];
                toasts.error($t('assets.delete.hasTransactions', {values: {name: deletingAsset!.display_name}}));
            } else {
                toasts.error(r?.message || $t('assets.delete.toastFailed', {values: {name: deletingAsset!.display_name}}));
                deleteDialogOpen = false;
                deletingAsset = null;
            }
        } catch (e: any) {
            toasts.error($t('assets.delete.toastFailed', {values: {name: deletingAsset!.display_name}}));
            deleteDialogOpen = false;
            deletingAsset = null;
        } finally {
            deleteLoading = false;
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
        for (const a of assets) invalidateAssetPrices(a.id);
        rearmMaxPendingBeforeReload();
        await pageBusy.track('assets-bulk-refresh', () => fetchAllPriceData());
        clearAllTableSelections();
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
            bulkDeleteResults = (res.results ?? []).map((r: any) => {
                const blocked = r.error_code === 'HAS_TRANSACTIONS';
                return {
                    label: r.display_name || `Asset #${r.asset_id}`,
                    success: r.success,
                    detail: r.success ? $t('assets.delete.resultDeleted') : blocked ? `${$t('assets.delete.resultHasTransactions')} (${Number(r.transaction_count ?? 0)})` : r.message || 'Error',
                    action: blocked
                        ? {
                              href: buildTransactionsFiltersUrl({asset_id: r.asset_id}),
                              label: $t('transactions.title'),
                              testId: `asset-bulk-delete-transactions-${r.asset_id}`,
                          }
                        : undefined,
                };
            });
        } catch (e: any) {
            toasts.error('Delete failed: ' + (e?.message || 'unknown'));
            bulkDeleteDialogOpen = false;
            deletingAssets = [];
            clearAllTableSelections();
        }
    }

    function closeBulkDeleteDialog() {
        // Show summary toast on close
        const successes = bulkDeleteResults.filter((r) => r.success).length;
        const failures = bulkDeleteResults.filter((r) => !r.success).length;
        if (successes > 0) {
            toasts.success($t('assets.delete.bulkOk', {values: {n: successes}}));
        }
        if (failures > 0) {
            toasts.warning($t('assets.delete.bulkPartial', {values: {failed: failures}}));
        }
        bulkDeleteDialogOpen = false;
        bulkDeleteResults = [];
        deletingAssets = [];
        clearAllTableSelections();
    }

    function handleGlobalSettings() {
        settingsTargetId = null;
        settingsModalOpen = true;
    }

    /** The assets the comparison signals of `configs` draw: a card asks the backend for each, sampled like itself (Z-29b). */
    function comparisonFingerprint(configs: SignalConfig[], selfAssetId: number): string {
        return comparisonTargetIds(configs, selfAssetId).join(',');
    }

    function handleSettingsSave(s: ChartSettings) {
        const targetCardId = settingsTargetId ? Number(settingsTargetId) : null;
        const shouldReloadBackend = backendRequestFingerprint(settingsForModal.signals) !== backendRequestFingerprint(s.signals);
        // A saved comparison with another asset asks for that asset's sample on the card's buckets.
        const shouldReloadTargets =
            targetCardId !== null
                ? comparisonFingerprint(settingsForModal.signals, targetCardId) !== comparisonFingerprint(s.signals, targetCardId)
                : assets.some((asset) => comparisonFingerprint(getSettingsForPair(`asset-${asset.id}`, 'assets').signals, asset.id) !== comparisonFingerprint(s.signals, asset.id));
        const calendarBefore = targetCardId !== null ? cardPrimaryView(targetCardId) === 'calendar-return' : assets.some((asset) => cardPrimaryView(asset.id) === 'calendar-return');
        if (settingsTargetId) {
            setPairSettings(`asset-${settingsTargetId}`, s);
        } else {
            setGlobalSettings(s, 'assets');
        }
        // The rolling-return view asks its own data (Y-40): entering it, leaving it, or a window changed in it reloads.
        const shouldReloadCalendar = calendarBefore || s.primaryView === 'calendar-return';
        if (shouldReloadBackend || shouldReloadTargets || shouldReloadCalendar) {
            // A card's own settings reload that card; only the global ones reload them all (Q-Z29-2).
            const only = targetCardId !== null ? new Set([targetCardId]) : undefined;
            void pageBusy.track('assets-settings', () => fetchPriceSeries(only));
        }
    }

    /** The plot width the settings preview asks its rolling return for (Y-40): about the preview chart's. */
    const CALENDAR_PREVIEW_PLOT_WIDTH_PX = 600;

    /**
     * The rolling return of the settings preview (Y-40). A card's: its own return over the range on screen, and its
     * comparisons', as the card asks them. The global settings': the synthetic curve the modal hands, through
     * `/signals/preview`, as the other backend signals of that preview.
     */
    async function resolveCalendarPreview(windowDays: number, configs: SignalConfig[], points: LineDataPoint[]): Promise<{points: LineDataPoint[]; overlays: RenderedSignal[]} | null> {
        const request = {instance_id: CALENDAR_RETURN_INSTANCE_ID, signal_code: CALENDAR_RETURN_SIGNAL_CODE, params: {window_days: windowDays}};
        const cardId = settingsTargetId ? Number(settingsTargetId) : null;
        if (cardId === null) {
            if (points.length === 0) return null;
            const response = await zodiosApi.compute_signal_preview_api_v1_signals_preview_post({domain: 'asset', points: points.map((point) => ({date: point.date, value: point.value})), signals: [request]});
            const view = extractCalendarReturnView(response.signals ?? [], CALENDAR_RETURN_INSTANCE_ID);
            return view.state === 'ready' || view.state === 'partial' ? {points: view.points, overlays: []} : null;
        }
        const card = assets.find((asset) => asset.id === cardId);
        if (!card) return null;
        const targets = comparisonTargetIds(configs, cardId).filter((assetId) => assets.some((asset) => asset.id === assetId));
        const entries = buildReducedQuery([
            {
                assetId: cardId,
                plotWidthPx: CALENDAR_PREVIEW_PLOT_WIDTH_PX,
                start: dateStart,
                end: dateEnd,
                needsPrice: false,
                signals: [request],
                targets: targets.map((assetId) => ({assetId, needsRead: false})),
                calendar: {signals: [request], targetCurrency: card.currency},
            },
        ]);
        const response = await axiosInstance.post(
            '/api/v1/assets/prices/query',
            entries.map((entry) => entry.item),
        );
        // The answer's items come in the request's order.
        const items: unknown[] = Array.isArray(response.data?.items) ? response.data.items : [];
        const signalsOf = (index: number): unknown => {
            const item = items[index];
            return typeof item === 'object' && item !== null ? (item as {signals?: unknown}).signals : undefined;
        };
        const own = extractCalendarReturnView(signalsOf(0), CALENDAR_RETURN_INSTANCE_ID);
        if (own.state !== 'ready' && own.state !== 'partial') return null;
        const views = new Map(entries.slice(1).map((entry, index) => [entry.targetId!, extractCalendarReturnView(signalsOf(index + 1), CALENDAR_RETURN_INSTANCE_ID)]));
        const target = (id: number) => {
            const asset = assets.find((item) => item.id === id);
            return asset ? {displayName: asset.display_name, iconUrl: asset.icon_url, assetType: asset.asset_type} : null;
        };
        return {points: own.points, overlays: renderCalendarComparisons(configs, views, target, (id) => $t('chartSettings.signals.assetFallback', {values: {id: String(id)}}), cardId)};
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

    /**
     * Where the cards — and their settings preview — get the series their FX pair and comparison signals read (Y-39a):
     * the pairs from the FX stores, straight; the comparison targets sampled like the card (Z-29b), or, before they are
     * read, from the cards of the list when both are daily. A card never draws a comparison with its own asset.
     */
    function signalSourcesFor(selfAssetId: number | null): SignalDataSources {
        return {
            fxPairData: (pairSlug) =>
                getFxStore(pairSlug)
                    .getAllSorted()
                    .map((point) => fxPointToLineDataPoint(point, false)),
            comparisonTarget: (assetId) => {
                const target = assets.find((asset) => asset.id === assetId);
                if (!target) return null;
                const names = {displayName: target.display_name, iconUrl: target.icon_url, assetType: target.asset_type};
                // The target sampled like the card (Z-29b): its dates are the card's, and its percentage base the day it starts.
                const sample = selfAssetId === null ? undefined : targetSamples.get(`${selfAssetId}|${assetId}`);
                if (sample) return comparisonTargetFrom(sample, names);
                // Not read yet: its own series, only where it has the card's dates, both daily (the preview of the global settings has none).
                const self = selfAssetId === null ? undefined : assets.find((asset) => asset.id === selfAssetId);
                if ((self?.resolution ?? 'daily') !== 'daily' || (target.resolution ?? 'daily') !== 'daily' || !target.chartData.length) return null;
                return {data: target.chartData, ...names};
            },
            selfAssetId,
        };
    }

    /** The settings preview reads the series as the cards do: in a card's settings, with that card's own sources. */
    let settingsSignalSources = $derived(signalSourcesFor(settingsTargetId ? Number(settingsTargetId) : null));

    /**
     * Global (filter-bar) mode: compute backend overlay signals live on the
     * modal's synthetic preview curve, so indicators like SMA render in the
     * preview without a real asset. Backend indicators can't run in the browser.
     */
    async function resolveGlobalBackendPreview(configs: SignalConfig[], points: LineDataPoint[], viewMode: 'absolute' | 'percentage'): Promise<RenderedSignal[]> {
        const plan = buildBackendSignalRequestPlan(configs, signalDefinitions);
        if (plan.requests.length === 0 || points.length === 0) return [];
        const response = await zodiosApi.compute_signal_preview_api_v1_signals_preview_post({
            domain: 'asset',
            points: points.map((point) => ({date: point.date, value: point.value})),
            signals: plan.requests,
        });
        const mapped = mapSignalInstanceResults(configs, plan, response.signals ?? []);
        return renderBackendResults(configs, mapped, signalDefinitionsByType, points, viewMode, (key) => $t(key));
    }

    function resolveSettingsBackendPreview(viewMode: 'absolute' | 'percentage'): RenderedSignal[] {
        if (!settingsTargetId) return [];
        const asset = assets.find((item) => item.id === Number(settingsTargetId));
        if (!asset?.chartData.length) return [];
        return getRenderedSignals(asset.id, asset.chartData, viewMode);
    }

    /**
     * Render overlay signals for an asset card. Called by AssetCard reactively
     * whenever cardViewMode changes. Receives absolute chart data.
     */
    function getRenderedSignals(assetId: number, absoluteData: LineDataPoint[], vm: 'absolute' | 'percentage'): RenderedSignal[] {
        void getSettingsVersion();
        const settings = getSettingsForPair(`asset-${assetId}`, 'assets');
        if (!settings.signals.length) return [];
        const asset = assets.find((item) => item.id === assetId);
        // The backend signals measure a percentage from the first point they are given: a sampled card gives the point on the first day (MF n3).
        const backendBase = signalBaseData(absoluteData, asset?.base, asset?.resolution);
        return [...renderLocalSignals(settings.signals, signalDefinitionsByType, absoluteData, vm, signalSourcesFor(assetId)), ...renderBackendResults(settings.signals, signalResultsByAsset.get(assetId) ?? [], signalDefinitionsByType, backendBase, vm, (key) => $t(key))];
    }

    function clearFilters() {
        searchText = '';
        filterTypes = new Set();
        filterCurrencies = new Set();
    }

    let hasActiveFilters = $derived(!!searchText || filterTypes.size > 0 || filterCurrencies.size > 0);

    /**
     * The page renders in two waves: the asset list arrives first, then each row fetches its
     * own prices. Until both are done the numbers on screen are placeholders, and nothing in
     * the DOM said so — the only way to know was to wait and hope. Exposed here so the state
     * is readable by assistive tech (`aria-busy`) and by anything else that needs to know
     * whether what it is looking at is final.
     */
    // The cards' rolling returns are a load wave too (Y-40): `data-busy` holds until they are in.
    let busy = $derived(loading || assetEditLoading || periodChangesLoading || assets.some((a) => a.loadingPrices) || [...calendarByCard.values()].some((entry) => entry.own.state === 'loading'));
</script>

<div class="space-y-6 text-lf-primary" aria-busy={busy} data-busy={busy ? 'true' : 'false'} data-live-updates={liveUpdatesState} data-testid="assets-page">
    <!-- Header: Title left, ViewModeToggle + Add Asset right. Round 14.1 bugfix: `lg:` is a
         VIEWPORT breakpoint (1024px) — wraps unconditionally below that width regardless of
         whether the actual header row has room. Plain `flex-wrap` reacts to the row's OWN
         available width instead (see fx/+page.svelte's equivalent header for the full note). -->
    <div class="flex flex-wrap items-start justify-between gap-4">
        <div use:guideAnchor={'asset.page.overview'} data-testid="asset-page-overview-guide-target">
            <!-- The pill sits beside the heading, not inside it: a status is not part of the title. -->
            <div class="flex flex-wrap items-center gap-2">
                <h2 class="text-lg font-semibold text-lf-secondary flex items-center gap-2">
                    {$t('common.assets')}
                    {#if assets.length > 0}
                        <span data-testid="assets-count-badge" class="text-xs font-mono px-1.5 py-0.5 rounded-full bg-lf-selected text-lf-link">{assets.length}</span>
                    {/if}
                </h2>
                <LiveUpdatesStatus state={liveUpdatesState} />
            </div>
            <p class="text-lf-muted text-sm">{$t('assets.subtitle')}</p>
        </div>
        <div class="flex flex-wrap items-center gap-2 justify-end ml-auto">
            {#if viewMode === 'list' && selectedAssetRows.length > 0}
                <DataTableToolbar
                    selectedCount={selectedAssetRows.length}
                    bulkActions={[
                        {id: 'sync', icon: RotateCw, label: () => $t('common.sync'), onClick: () => handleBulkSyncAssets()},
                        {id: 'refresh', icon: RefreshCw, label: () => $t('common.refresh'), onClick: () => handleBulkRefreshAssets()},
                        {id: 'delete', icon: Trash2, label: () => $t('common.delete'), variant: 'danger', onClick: () => handleBulkDeleteAssets()},
                    ]}
                    onClearSelection={() => {
                        clearAllTableSelections();
                    }}
                />
            {/if}
            <!-- Currency filter badges — Opzione γ (D10+D11) -->
            {#if filterCurrencies.size > 0 && selectedAssetRows.length === 0}
                <div class="flex items-center gap-1.5 flex-wrap">
                    {#each [...filterCurrencies] as currency}
                        <span
                            class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium
                                     bg-lf-warning-soft text-lf-warning-on-soft
                                     border border-lf-warning-line rounded-full"
                        >
                            {getCurrencyInfo(currency).flag_emoji}
                            {currency}
                            <button
                                class="hover:text-lf-danger transition-colors"
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
            <button class="flex items-center gap-1.5 px-3 py-2 text-sm bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover transition-colors whitespace-nowrap" data-testid="assets-add-button" use:guideAnchor={'asset.page.add'} onclick={handleAddAsset}>
                <Plus size={16} />
                {$t('assets.modal.title')}
            </button>
        </div>
    </div>

    <!-- Filter Bar — shared PageToolbar (same component as dashboard/broker-detail), so
         responsive/wrap fixes made there (jolly badge shedding, currency/broker no-wrap, ...)
         auto-propagate here instead of being hand-copied per page.
         oneRow:       [ datepicker | search active currency type × | 2×2 ]
         denseRow:     [ datepicker                     | 2×2 ]
                      [ search active currency type ×  |     ]
         stackFilters: [ datepicker                     | col  ]
                      [ search active currency type ×  | btns ]
         oneColumn:    [ datepicker ] [ search active × ] [ currency type ] [ 2×2 btns, now BELOW ] -->
    <PageToolbar thresholds={{oneRow: 1340, denseRow: 1020, stackFilters: 520, oneColumn: 400, labelHideActions: 250, labelHideTabs: 370}} tabs={assetTabs} {activeTab} ontabchange={handleAssetTabChange} testId="assets-controls" filterRowTestId="assets-filter-bar" layoutDebugName="assetsList">
        {#snippet filters({layoutMode, filtersStacked})}
            <!-- In oneColumn (phones) the four filters share each row instead of keeping their
                 176/160 px: two of them no longer fit side by side below a ~314 px bar. -->
            {@const filterWidthClass = layoutMode === 'oneColumn' ? 'flex-1 min-w-0' : 'w-44 min-w-[160px]'}
            <!-- The Active/Inactive pill never goes below its two labels: where half the row is
                 too narrow for them (Spanish below ~370 px, English and French at 320–330 px), it
                 takes its own width and Search gives up the rest. -->
            {@const pillWidthClass = layoutMode === 'oneColumn' ? 'flex-1 min-w-max' : 'w-44 min-w-[160px]'}
            <!-- DateRangePicker. Round 14 bugfix: this wrapper is `contents` (exits the box
                 model — data-testid stays queryable, it's just a DOM attribute) rather than
                 `flex flex-1 ...` — DateRangePicker's own root ALREADY self-applies
                 `grow`+`self-stretch`+`max-width:{effectiveMaxWidth}px` when `align="start"`
                 (see DateRangePicker.svelte). An extra `flex-1` wrapper with NO cap of its own
                 grows past the picker's actual (capped) rendered width, leaving an invisible
                 gap that pushed the Center content sibling further right than intended
                 (denseRow bug report — most visible there since the picker's own 2-row content
                 doesn't grow to fill space the way oneRow's jolly-badge-fill does). -->
            <div class="contents" data-testid="assets-date-range">
                <DateRangePicker bind:activePreset bind:end={dateEnd} bind:start={displayDateStart} compact={true} align="start" maxWidthTwoRow={410} {layoutMode} debugName="assetsList" onchange={handleDateRangeChange} bind:effectiveMaxWidth={pickerMaxWidth} />
            </div>

            <!-- Filters 2×2 block, BESIDE the picker (denseRow only) / inline (oneRow) /
                 stacked+justified BELOW the picker (stackFilters+oneColumn — start-aligned,
                 capped to the picker's own width via pickerMaxWidth, matching the
                 dashboard/brokerDetail/fxList "giustificata" pattern). Round 13: each ROW
                 individually needs its own w-full+justify-around too — the OUTER wrapper's cap
                 alone doesn't distribute space to children that don't ALSO stretch to it.
                 Hidden on the correlation tab (F-3b): every filter here narrows
                 `filteredAssets`, which only the grid reads — the lab gets the whole list
                 and keeps its own filters inside its "+". Shown there, they did nothing. -->
            {#if activeTab !== 'correlation'}
                <div
                    class="flex gap-2 {layoutMode === 'oneRow' ? 'flex-row items-center flex-wrap' : filtersStacked ? 'flex-col items-start w-full' : 'flex-col'}"
                    style={filtersStacked && pickerMaxWidth ? `max-width: ${pickerMaxWidth}px` : ''}
                    use:guideAnchor={'asset.page.filters'}
                    data-testid="asset-page-filters"
                >
                    <!-- Row 1: Search + Active -->
                    <div class="flex items-center gap-2 {filtersStacked ? 'w-full justify-around' : ''}">
                        <!-- Search — Round 14: min-w bumped (was a flat w-44/176px that felt too
                             cramped) so it stays comfortably readable even under pressure. -->
                        <div class="relative {filterWidthClass}">
                            <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 text-lf-muted" size={14} />
                            <input
                                class="w-full pl-8 pr-3 py-1.5 text-sm border border-lf-input rounded-lg bg-lf-field text-lf-primary placeholder:text-lf-placeholder hover:border-lf-input-hover focus:ring-1 focus:ring-lf-focus focus:border-lf-focus"
                                data-testid="assets-search-input"
                                oninput={handleSearchInput}
                                placeholder={$t('assets.searchPlaceholder')}
                                type="text"
                                value={searchText}
                            />
                        </div>

                        <!-- Tri-state Active/Inactive segmented toggle (I-bis #20).
                             Both pressed OR both unpressed → show all (None filter server-side,
                             no filter client-side). Only-one pressed → filter to that state.
                             Round 15: fixed w-44 (matches Search above and the Currency filter
                             below, once swapped) + flex-1 buttons so the pill splits evenly and
                             lines up as a column with Row 2 in every language. On phones
                             (oneColumn) it shares the row with Search and keeps that column only
                             while its labels fit half the row (lot 51, R-1). -->
                        <div class="flex {pillWidthClass} rounded-lg border border-lf-subtle overflow-hidden" data-testid="assets-active-filter">
                            <button
                                type="button"
                                class="flex-1 px-3 py-1.5 text-xs font-medium border-r border-lf-subtle transition-colors whitespace-nowrap
                                       {filterShowActive ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
                                data-testid="assets-active-toggle"
                                aria-pressed={filterShowActive}
                                onclick={() => (filterShowActive = !filterShowActive)}
                            >
                                {$t('assets.showActive')}
                            </button>
                            <button
                                type="button"
                                class="flex-1 px-3 py-1.5 text-xs font-medium transition-colors whitespace-nowrap
                                       {filterShowInactive ? 'bg-lf-warning text-lf-on-status' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
                                data-testid="assets-inactive-toggle"
                                aria-pressed={filterShowInactive}
                                onclick={() => (filterShowInactive = !filterShowInactive)}
                            >
                                {$t('assets.showInactive')}
                            </button>
                        </div>
                    </div>

                    <!-- Row 2: Currency dropdown + Type multi-select + Reset. Round 15: swapped
                         order (Currency first, Type second) and both given the SAME explicit
                         widths as their Row 1 counterparts (w-44, matching Search then Toggle
                         above) so the two rows line up as a clean 2-column grid instead of
                         drifting out of alignment. -->
                    <div class="flex items-center gap-2 {filtersStacked ? 'w-full justify-around' : ''}">
                        <!-- Currency Filter (D10 — CurrencySearchSelect, adds to Set). w-44
                             matches Search above (was w-36) so column 1 lines up across rows. -->
                        <div class={filterWidthClass}>
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

                        <!-- Type multi-checkbox dropdown (D9). w-44 on the wrapper matches the
                             Active/Inactive toggle above (was content-sized min-w-0) — but a
                             <button>'s own width:auto does NOT fill a plain block parent the way a
                             <div> does (unlike e.g. the Search <input> above, which already needs
                             its own explicit w-full for the same reason) — w-full here makes the
                             VISIBLE button (border/background) actually reach the wrapper's 176px,
                             not just the invisible wrapper box. justify-between then spreads the
                             label/chevron across that width instead of leaving them bunched left. -->
                        <div class="relative {filterWidthClass}">
                            <button
                                bind:this={typeFilterTriggerEl}
                                class="flex items-center justify-between gap-1.5 w-full px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors min-w-0
                                       {filterTypes.size > 0 ? 'bg-lf-info-soft text-lf-info-on-soft border-lf-info-line' : 'bg-lf-card text-lf-secondary border-lf-subtle hover:bg-lf-hover'}"
                                data-testid="assets-type-filter"
                                onclick={toggleTypeFilterDropdown}
                            >
                                <span class="truncate">
                                    {#if filterTypes.size > 0}
                                        {$t('common.type')} ({filterTypes.size})
                                    {:else}
                                        {$t('assets.allTypes')}
                                    {/if}
                                </span>
                                <svg class="w-3 h-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path d="M19 9l-7 7-7-7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
                                </svg>
                            </button>

                            {#if typeFilterOpen}
                                <!-- svelte-ignore a11y_interactive_supports_focus -->
                                <div
                                    bind:this={typeFilterPanelEl}
                                    class="fixed z-50 w-56 bg-lf-card border border-lf-raised rounded-lg shadow-lg shadow-lf-shadow overflow-hidden"
                                    style:left={`${typeFilterDropdownPosition.left}px`}
                                    style:top={`${typeFilterDropdownPosition.top}px`}
                                    onclick={(e) => e.stopPropagation()}
                                    onkeydown={(e) => {
                                        if (e.key === 'Escape') typeFilterOpen = false;
                                    }}
                                    role="listbox"
                                    tabindex="0"
                                    data-type-filter-panel
                                >
                                    <!-- Select All / Clear All buttons -->
                                    <div class="flex gap-2 px-2.5 py-2 border-b border-lf-subtle">
                                        <button
                                            type="button"
                                            class="flex-1 px-2 py-1 text-[11px] font-medium border border-lf-subtle rounded bg-lf-panel text-lf-secondary hover:bg-lf-neutral hover:text-lf-primary transition-colors"
                                            onclick={() => {
                                                filterTypes = new Set(availableTypes);
                                            }}>{$t('common.selectAll')}</button
                                        >
                                        <button
                                            type="button"
                                            class="flex-1 px-2 py-1 text-[11px] font-medium border border-lf-subtle rounded bg-lf-panel text-lf-secondary hover:bg-lf-neutral hover:text-lf-primary transition-colors"
                                            onclick={() => {
                                                filterTypes = new Set();
                                            }}>{$t('common.clearAll')}</button
                                        >
                                    </div>
                                    <!-- Option list -->
                                    <div class="max-h-52 overflow-y-auto border border-lf-subtle mx-2.5 my-2 rounded-md">
                                        {#each availableTypes as typeVal}
                                            <!-- The per-type testid is the only handle a test has on these rows: the
                                                 row carries a shared icon (the six ETF subtypes all draw etf.png by
                                                 design) and a translated label, so neither identifies a type. Same
                                                 convention as column-visibility-item-{id} and provider-option-{code}. -->
                                            <button
                                                type="button"
                                                data-testid="assets-type-filter-option-{typeVal}"
                                                class="flex items-center gap-2 w-full px-2 py-1.5 text-left text-[13px] text-lf-secondary hover:bg-lf-hover transition-colors cursor-pointer"
                                                onclick={() => {
                                                    const next = new Set(filterTypes);
                                                    if (next.has(typeVal)) next.delete(typeVal);
                                                    else next.add(typeVal);
                                                    filterTypes = next;
                                                }}
                                            >
                                                <span
                                                    class="flex items-center justify-center w-4 h-4 rounded-sm border transition-colors shrink-0
                                                             {filterTypes.has(typeVal) ? 'bg-lf-checked border-lf-checked text-lf-on-checked' : 'bg-lf-field border-lf-input'}"
                                                >
                                                    {#if filterTypes.has(typeVal)}
                                                        <Check size={12} />
                                                    {/if}
                                                </span>
                                                <img src={getAssetTypeIconUrl(typeVal)} alt="" class="w-4 h-4 object-contain shrink-0" />
                                                <span class="flex-1">{$t(`assets.types.${typeVal}`) || typeVal}</span>
                                                <span class="text-[10px] font-mono text-lf-muted tabular-nums">{typeCounts[typeVal] ?? 0}</span>
                                            </button>
                                        {/each}
                                    </div>
                                </div>
                            {/if}
                        </div>

                        <!-- Reset filters -->
                        {#if hasActiveFilters}
                            <button class="p-1.5 rounded-md hover:bg-lf-hover text-lf-muted hover:text-lf-danger transition-colors" onclick={clearFilters} title={$t('fx.filter.resetFilters')}>
                                <X size={16} />
                            </button>
                        {/if}
                    </div>
                </div>
            {/if}
        {/snippet}

        {#snippet actions({showActionLabels})}
            {#if activeTab === 'correlation'}
                <!-- F-3b (V1) — on the correlation tab the toolbar serves the lab. Abs/% and the
                     chart settings drive the grid's cards, which this tab does not show, so they
                     leave; the sync and the reload act on the lab's selection. The sync is the
                     lab's own modal (prices and the rates that convert them), opened from here so
                     the page has one sync button instead of two side by side. -->
                <Tooltip text={$t('risk.assetSet.syncSelectionHint')} position="bottom" interactiveChild>
                    <button
                        class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-lf-card border border-lf-subtle rounded-lg hover:bg-lf-hover text-lf-secondary transition-colors disabled:opacity-50 disabled:hover:bg-lf-card"
                        onclick={(event) => {
                            // Not up to the Tooltip wrapper: its click pins the hint for thirty
                            // seconds, which would float over the modal this button opens.
                            event.stopPropagation();
                            labPanel?.openSync();
                        }}
                        disabled={!labPanel || !labCanSync}
                        data-testid="risk-sync-button"
                        use:guideAnchor={'asset.page.sync'}
                    >
                        <RotateCw size={14} />
                        {#if showActionLabels}<span>{$t('sharedResource.syncSelection')}</span>{/if}
                    </button>
                </Tooltip>
                <Tooltip text={$t('risk.assetSet.reloadHint')} position="bottom" interactiveChild>
                    <button
                        class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-lf-card border border-lf-subtle rounded-lg hover:bg-lf-hover text-lf-secondary transition-colors disabled:opacity-50 disabled:hover:bg-lf-card"
                        onclick={(event) => {
                            event.stopPropagation();
                            labPanel?.reload();
                        }}
                        disabled={!labPanel || pageBusy.busy}
                        data-busy={pageBusy.busy ? 'true' : 'false'}
                        data-testid="risk-reload-button"
                    >
                        <RefreshCw class={pageBusy.busy ? 'animate-spin' : ''} size={14} />
                        {#if showActionLabels}<span>{$t('sharedResource.refreshAll')}</span>{/if}
                    </button>
                </Tooltip>
            {:else}
                <!-- Top-left: ColumnVisibility in table mode, Abs/% toggle in grid mode -->
                {#if viewMode === 'list'}
                    <ColumnVisibilityToggle tableRef={assetTableRefs['own']?.getTableRef()} additionalTableRefs={[assetTableRefs['others']?.getTableRef(), assetTableRefs['analysis']?.getTableRef()].filter((r) => r != null)} showLabel={showActionLabels} />
                {:else}
                    <!-- The cards' view (Y-40): absolute, percent, rolling return -->
                    <div class="flex rounded-lg border border-lf-subtle overflow-hidden" data-testid="assets-global-view" data-view={globalPrimaryView}>
                        <button
                            type="button"
                            class="flex-1 px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {globalPrimaryView === 'absolute' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
                            data-testid="assets-global-view-absolute"
                            aria-pressed={globalPrimaryView === 'absolute'}
                            onclick={() => handleListPrimaryView('absolute')}
                            >Abs
                        </button>
                        <button
                            type="button"
                            class="flex-1 px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {globalPrimaryView === 'percentage' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
                            data-testid="assets-global-view-percentage"
                            aria-pressed={globalPrimaryView === 'percentage'}
                            onclick={() => handleListPrimaryView('percentage')}
                            >%
                        </button>
                        <button
                            type="button"
                            class="flex-1 inline-flex items-center justify-center px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {globalPrimaryView === 'calendar-return' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
                            data-testid="assets-global-view-calendar-return"
                            aria-pressed={globalPrimaryView === 'calendar-return'}
                            aria-label={$t('signals.riskRollingReturn.name')}
                            title={$t('signals.riskRollingReturn.name')}
                            onclick={() => handleListPrimaryView('calendar-return')}
                        >
                            <CalendarSync size={14} />
                        </button>
                    </div>
                {/if}
                <!-- Settings -->
                <button class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-lf-card border border-lf-subtle rounded-lg hover:bg-lf-hover text-lf-secondary transition-colors" onclick={handleGlobalSettings} data-testid="assets-chart-settings-button">
                    <Settings size={14} />
                    {#if showActionLabels}<span>{$t('sharedResource.settings')}</span>{/if}
                </button>
                <!-- Sync All -->
                <button
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-lf-card border border-lf-subtle rounded-lg hover:bg-lf-hover text-lf-secondary transition-colors"
                    onclick={handleSyncAllAssets}
                    data-testid="assets-sync-all-button"
                    use:guideAnchor={'asset.page.sync'}
                >
                    <RotateCw size={14} />
                    {#if showActionLabels}<span>{$t('sharedResource.syncAll')}</span>{/if}
                </button>
                <!-- Refresh All -->
                <button
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-lf-card border border-lf-subtle rounded-lg hover:bg-lf-hover text-lf-secondary transition-colors disabled:opacity-50"
                    data-testid="assets-refresh-button"
                    data-busy={pageBusy.busy ? 'true' : 'false'}
                    disabled={pageBusy.busy}
                    onclick={() => {
                        for (const a of assets) invalidateAssetPrices(a.id);
                        rearmMaxPendingBeforeReload();
                        void pageBusy.track('assets-refresh', () => fetchAllPriceData());
                        refreshLivePricesNow();
                    }}
                >
                    <RefreshCw class={pageBusy.busy ? 'animate-spin' : ''} size={14} />
                    {#if showActionLabels}<span>{$t('sharedResource.refreshAll')}</span>{/if}
                </button>
            {/if}
        {/snippet}
    </PageToolbar>

    <!-- Content -->
    {#if activeTab === 'correlation'}
        {#if loading}
            <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card p-12 text-center border border-lf-subtle">
                <RefreshCw class="text-lf-link animate-spin mx-auto" size={32} />
            </div>
        {:else if error}
            <div class="bg-lf-danger-soft border border-lf-danger-line rounded-xl p-6 text-center">
                <p class="text-lf-danger-on-soft">{error}</p>
            </div>
        {:else}
            <AssetSetRiskPanel
                bind:this={labPanel}
                bind:canSync={labCanSync}
                onfitperiod={(range) => {
                    // A period set by code must switch the preset of the picker off by hand:
                    // activePreset is bound to it, and would keep the old badge lit.
                    activePreset = null;
                    handleDateRangeChange(range.start, range.end);
                }}
                {assets}
                {dateStart}
                {dateEnd}
                targetCurrency={$defaultDisplayCurrency}
                onsynced={async () => {
                    for (const asset of assets) invalidateAssetPrices(asset.id);
                    rearmMaxPendingBeforeReload();
                    await fetchAllPriceData();
                }}
            />
        {/if}
    {:else if loading}
        <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card p-12 text-center border border-lf-subtle">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-lf-selected rounded-full mb-4">
                <RefreshCw class="text-lf-link animate-spin" size={32} />
            </div>
            <p class="text-lf-muted">{$t('common.loading')}</p>
        </div>
    {:else if error}
        <div class="bg-lf-danger-soft border border-lf-danger-line rounded-xl p-6 text-center">
            <p class="text-lf-danger-on-soft">{error}</p>
            <button class="mt-3 px-4 py-2 text-sm bg-lf-danger-solid text-lf-on-danger-solid rounded-lg hover:bg-lf-danger-hover transition-colors" onclick={loadAssets}>
                {$t('common.retry')}
            </button>
        </div>
    {:else if filteredAssets.length === 0}
        <!-- Empty state -->
        <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card p-12 text-center border border-lf-subtle">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-lf-selected rounded-full mb-4">
                <BarChart3 class="text-lf-link" size={32} />
            </div>
            {#if assets.length === 0}
                <h3 class="text-lg font-semibold text-lf-secondary mb-2">{$t('assets.empty.noAssets')}</h3>
                <p class="text-lf-muted mb-4">{$t('assets.empty.noAssetsDesc')}</p>
                <button class="px-4 py-2 bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover transition-colors" use:guideAnchor={'assets.add'} onclick={handleAddAsset}>
                    <Plus size={16} class="inline mr-1" />
                    {$t('assets.modal.title')}
                </button>
            {:else}
                <h3 class="text-lg font-semibold text-lf-secondary mb-2">{$t('common.noMatchesTitle')}</h3>
                <p class="text-lf-muted">{$t('assets.empty.noMatchesDesc')}</p>
            {/if}
        </div>
    {:else if viewMode === 'grid'}
        <!-- Grid View — F15: three usage panels (yours / other users' / under analysis) -->
        <div class="space-y-6">
            {#each assetPanels as panel (panel.id)}
                {#if panel.items.length > 0}
                    <section data-testid="assets-panel-{panel.id}">
                        <header class="mb-2 px-1">
                            <h2 class="text-sm font-semibold text-lf-secondary">
                                {$t(`assets.panels.${panel.id}`)} <span class="text-lf-muted font-normal">({panel.items.length})</span>
                            </h2>
                            <p class="text-[11px] text-lf-muted">{$t(`assets.panels.${panel.id}Hint`)}</p>
                        </header>
                        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                            {#each panel.items as asset (asset.id)}
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
                                    txCount={asset.tx_count ?? 0}
                                    livePrice={livePriceMap.get(asset.id)?.value ?? asset.lastPrice ?? null}
                                    livePriceDirection={livePriceMap.get(asset.id)?.direction ?? 'neutral'}
                                    deltaPercent={rangeDeltas.get(asset.id)?.pct ?? null}
                                    deltaAbs={rangeDeltas.get(asset.id)?.abs ?? null}
                                    dateStart={urlDateStart}
                                    dateEnd={urlDateEnd}
                                    primaryView={cardPrimaryView(asset.id)}
                                    onprimaryviewchange={handleCardPrimaryView}
                                    calendarReturn={cardPrimaryView(asset.id) === 'calendar-return' ? cardCalendarReturn(asset.id) : undefined}
                                    calendarOverlaySignals={cardPrimaryView(asset.id) === 'calendar-return' ? cardCalendarOverlays(asset.id) : []}
                                    chartSettings={getSettingsForPair(`asset-${asset.id}`, 'assets')}
                                    renderSignals={(chartData, vm) => getRenderedSignals(asset.id, chartData, vm)}
                                    chartData={asset.chartData}
                                    baseValue={asset.base?.value ?? null}
                                    onplotwidth={handlePlotWidth}
                                    loading={asset.loadingPrices}
                                    syncing={syncingAssetIds.has(asset.id)}
                                    onsync={handleSyncAsset}
                                    onrefresh={handleRefreshAsset}
                                    ondelete={handleDeleteAsset}
                                    onmerge={handleMergeAsset}
                                    onsettings={handleCardSettings}
                                />
                            {/each}
                        </div>
                    </section>
                {/if}
            {/each}
        </div>
    {:else}
        <!-- Table View — F15 round-2: three stacked tables (yours / other users' /
             watched). Column widths, order and visibility stay in sync across the
             three (width via mirrorColumnResize, order/visibility via the toggle's
             additionalTableRefs); pagination is independent per table. -->
        <div class="space-y-6">
            {#each assetPanels as panel (panel.id)}
                {#if panel.items.length > 0}
                    <section data-testid="assets-table-panel-{panel.id}">
                        <header class="mb-2 px-1">
                            <h2 class="text-sm font-semibold text-lf-secondary">
                                {$t(`assets.panels.${panel.id}`)} <span class="text-lf-muted font-normal">({panel.items.length})</span>
                            </h2>
                            <p class="text-[11px] text-lf-muted">{$t(`assets.panels.${panel.id}Hint`)}</p>
                        </header>
                        <AssetTable
                            bind:this={assetTableRefs[panel.id]}
                            data={tableRows.filter((r) => r.txScope === panel.id)}
                            loading={false}
                            {visiblePeriods}
                            {livePriceMap}
                            dateStart={urlDateStart}
                            dateEnd={urlDateEnd}
                            storageKey="assetsTable-{panel.id}"
                            browseSegment={panel.id}
                            onsync={handleSyncAsset}
                            onrefresh={handleRefreshAsset}
                            ondelete={handleDeleteAsset}
                            onmerge={handleMergeAsset}
                            onColumnResize={(colId, w) => mirrorColumnResize(panel.id, colId, w)}
                            onselectionchange={(rows) => {
                                panelSelections = {...panelSelections, [panel.id]: rows};
                            }}
                        />
                    </section>
                {/if}
            {/each}
        </div>
    {/if}
</div>

<AssetBrowseOrder view={viewMode} panels={assetPanels} />
<!-- Chart Settings Modal (D4) -->
<ChartSettingsModal
    axisContext={settingsTargetId ? (assets.find((asset) => asset.id === Number(settingsTargetId))?.currency ?? '—') : $t('common.preview')}
    axisDomain="asset"
    open={settingsModalOpen}
    mode={settingsTargetId ? 'pair' : 'global'}
    {signalDefinitions}
    {signalBackendError}
    onretrySignalBackend={retryBackendSignals}
    backendPreviewSignalResolver={settingsTargetId ? resolveSettingsBackendPreview : undefined}
    backendPreviewLiveResolver={resolveGlobalBackendPreview}
    onclose={() => {
        settingsModalOpen = false;
        settingsTargetId = null;
    }}
    onsave={handleSettingsSave}
    settings={settingsForModal}
    pairData={settingsTargetId ? assets.find((a) => a.id === Number(settingsTargetId))?.chartData : undefined}
    availablePairs={fxPairSlugs}
    availableAssets={assets.map((a) => ({id: a.id, display_name: a.display_name, icon_url: a.icon_url, asset_type: a.asset_type}))}
    signalSources={settingsSignalSources}
    calendarRangeDays={calendarReturnRangeDays(dateStart, dateEnd)}
    calendarPreviewResolver={resolveCalendarPreview}
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
        singleDeleteResults = [];
    }}
    onConfirm={confirmDeleteAsset}
    open={deleteDialogOpen}
    results={singleDeleteResults}
    testId="asset-delete-confirm"
    title={$t('common.confirmDelete')}
/>

<!-- Bulk Delete Confirm Dialog -->
<ConfirmModal
    confirmText={$t('common.delete')}
    danger={true}
    items={deletingAssets.map((a) => a.display_name)}
    itemsLabel={$t('assets.delete.itemsLabel', {values: {count: deletingAssets.length}})}
    message={$t('assets.delete.bulkConfirmMessage', {values: {n: deletingAssets.length}})}
    onCancel={closeBulkDeleteDialog}
    onConfirm={confirmBulkDeleteAssets}
    open={bulkDeleteDialogOpen}
    results={bulkDeleteResults}
    testId="asset-bulk-delete-confirm"
    title={$t('common.confirmDelete')}
/>

<!-- Asset Sync Modal -->
<AssetSyncModal
    assets={syncModalAssets}
    bind:open={syncModalOpen}
    {dateEnd}
    dateStart={syncDateStart}
    withDataInRange={syncModalWithData}
    onclose={() => {
        syncModalOpen = false;
    }}
    onsynced={() => {
        for (const a of assets) invalidateAssetPrices(a.id);
        rearmMaxPendingBeforeReload();
        fetchAllPriceData();
        refreshLivePricesNow();
    }}
/>

<!-- Asset Create/Edit Modal -->
<AssetModal
    bind:open={assetModalOpen}
    tourPreview={assetTourPreview}
    editMode={assetModalEditMode}
    editData={assetModalEditData}
    linkCreatedAsset
    oncreated={handleAssetCreated}
    onsynced={handleCreatedAssetSynced}
    onupdated={() => void pageBusy.track('assets-reload', () => loadAssets())}
    onclose={() => {
        assetModalOpen = false;
        assetTourPreview = false;
        if (onboardingGuide.active?.flow === 'asset_guide') {
            onboardingGuide.dismissHost({restartAtFirst: true});
        }
    }}
/>

<!-- Asset Merge Modal (P3 · WS-E) -->
<AssetMergeModal
    bind:open={mergeModalOpen}
    sourceAsset={mergingAsset ? {id: mergingAsset.id, display_name: mergingAsset.display_name} : null}
    onmerged={async () => {
        if (mergingAsset) invalidateAfterMutation(mergingAsset.id);
        await pageBusy.track('assets-reload', () => loadAssets());
    }}
    onclose={() => {
        mergeModalOpen = false;
        mergingAsset = null;
    }}
/>
