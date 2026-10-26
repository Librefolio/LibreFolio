<script lang="ts">
    /**
     * FX Rates List Page
     *
     * Displays all configured FX pairs as cards with mini charts.
     * Features: currency filter (SearchSelect), unified date range picker with presets,
     * global abs/% slider toggle, Sync All, Refresh All, Add Pair.
     */
    import {onDestroy, onMount} from 'svelte';
    import {goto} from '$app/navigation';
    import {_} from '$lib/i18n';
    import {get} from 'svelte/store';
    import {zodiosApi} from '$lib/api';
    import {getStart, getEnd, setDateRange, resolveDateSentinel, isMaxSentinel} from '$lib/stores/dateRangeStore.svelte';
    import {ArrowLeftRight, CalendarSync, ChartLine, Coins, Plus, RefreshCw, RotateCw, Settings, Trash2, X} from 'lucide-svelte';
    import FxCard from '$lib/components/fx/FxCard.svelte';
    import type {FxRow} from '$lib/components/fx/FxTable.svelte';
    import FxTable from '$lib/components/fx/FxTable.svelte';
    import FxPairAddModal from '$lib/components/fx/FxPairAddModal.svelte';
    import FxSyncModal from '$lib/components/fx/FxSyncModal.svelte';
    import ChartSettingsModal from '$lib/components/charts/ChartSettingsModal.svelte';
    import {ConfirmModal} from '$lib/components/table';
    import DateRangePicker from '$lib/components/ui/date/DateRangePicker.svelte';
    import ViewModeToggle from '$lib/components/ui/ViewModeToggle.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import DataTableToolbar from '$lib/components/table/DataTableToolbar.svelte';
    import {CurrencySearchSelect} from '$lib/components/ui/select';
    import {type ChartPrimaryView, type ChartSettings, effectiveCalendarReturnWindow, getGlobalSettings, getSettingsForPair, getSettingsVersion, setGlobalSettings, setItemPrimaryView, setPairSettings, setScopePrimaryView} from '$lib/stores/chartSettingsStore.svelte';
    import {CALENDAR_RETURN_INSTANCE_ID, emptyCalendarReturnView, extractCalendarReturnView, type CalendarReturnView} from '$lib/components/charts/priceChartHelpers';
    import {calendarReturnRangeDays, calendarReturnWindowDays} from '$lib/components/charts/calendarReturnWindow';
    import {formatSignalProblem} from '$lib/components/charts/chartSignalsHelpers';
    import {DEFAULT_COMPACT_PLOT_WIDTH_PX} from '$lib/components/charts/timeSeriesAggregation';
    import {buildFxCalendarQuery, estimateFxCalendarDays, fxCalendarRequest, type FxCalendarCardInput, type FxCalendarEntry} from '$lib/utils/reducedFxQuery';
    import {sendBulkBatches} from '$lib/api/bulkBatches';
    import {onPricesCaughtUp} from '$lib/features/price-refresh/onPricesCaughtUp';
    import {comparisonTargetFromStore, ensureComparisonSeries} from '$lib/charts/comparisonSeries';
    import {comparisonTargetIds} from '$lib/utils/reducedPriceQuery';
    import {todayIso} from '$lib/utils/dateOnly';
    import {buildBackendSignalRequestPlan, getLocalSignalDefinitions, mapSignalInstanceResults, SignalResultState, type RenderedSignal, type SignalConfig, type SignalDefinition, type SignalInstanceResult} from '$lib/charts/signals';
    import {fxPointToLineDataPoint, renderBackendResults, renderCalendarPairComparisons, renderLocalSignals, type SignalDataSources} from '$lib/charts/chartSignalRendering';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import {createPairSlug, type FxDataPoint, type FxPairConfig, getFxStore, invalidateAllFxStores, loadFxRatesAndSignalsBulk, removeFxStore} from '$lib/stores/fxStoreRegistry';
    import {bulkRefusalMessage} from '$lib/api/bulkRefusal';
    import {hasStoredPointInRange} from '$lib/utils/sync/syncHelpers';
    import {fetchFxPeriodChanges, PeriodChangesLedger, visiblePeriodColumns, type PeriodDeltas, type PeriodSpec} from '$lib/utils/periodChanges';
    import type {RangeDelta} from '$lib/utils/rangeChange';
    import {isCardInverted} from '$lib/stores/fx/fxCardInversionStore';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {pageBusy} from '$lib/stores/app/pageBusy.svelte';
    import {getCurrencyGraph} from '$lib/stores/currencyGraphStore';
    import {getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {formatProviderText, formatSyncDetail} from '$lib/utils/providerHelpers';
    import {buildFxSyncToast} from '$lib/utils/sync/syncToastHelpers';
    import PageToolbar from '$lib/components/ui/toolbar/PageToolbar.svelte';
    import {gotoDateRange} from '$lib/utils/url/dateRangeUrl';
    import {signalCatalogStore} from '$lib/stores/signalCatalogStore.svelte';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import {onboardingGuide} from '$lib/features/onboarding/onboardingGuide.svelte';
    import {getClientSessionGeneration, isClientSessionCurrent} from '$lib/stores/app/clientSession';
    import type {FxPairSyncCompleteDetail} from '$lib/services/fxCreationSync';

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
    let pageAlive = true;
    onDestroy(() => {
        pageAlive = false;
    });
    let loading = $state(true);
    let error = $state<string | null>(null);

    // Filters
    let filterCurrency1 = $state('');
    let filterCurrency2 = $state('');
    // Date range — global store is source of truth; URL seeds only on fresh page load.
    // dateStart/dateEnd are ALWAYS a concrete, resolved date (sentinels resolved immediately)
    // — used everywhere internally (queries, cache, URLs). displayDateStart is the ONLY
    // thing bound to the picker; it shows the literal "min" sentinel (pending label) until
    // the real earliest date is extracted from a backend response (see fetchAllPairData).
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

    // The view of the FX cards (Y-40): the list's, saved with the chart settings, which the top bar sets for every card; a
    // card's button keeps its own (V-1 a, V-3 a). The FX list opens on absolute rates.
    let globalPrimaryView = $derived.by((): ChartPrimaryView => {
        void getSettingsVersion();
        return getGlobalSettings('fx').primaryView;
    });
    /** The rolling return of each card in that view, and its compared pairs' by signal id (Y-40), by pair. */
    let calendarBySlug = $state(new Map<string, {own: CalendarReturnView; targets: Map<string, CalendarReturnView>}>());
    /** The last request of each card's rolling return: an older answer arriving later is dropped. */
    const calendarRequestOfSlug = new Map<string, number>();
    let calendarRequestSeq = 0;
    let refreshing = $state(false);

    // View mode (grid/list)
    let viewMode = $state<'grid' | 'list'>('grid');
    let fxTableComponent: FxTable | undefined = $state(undefined);
    let selectedFxRows = $state<FxRow[]>([]);
    let syncModalPairs = $state<string[]>([]);

    // Delete (single)
    let deleteDialogOpen = $state(false);
    let deletingPair = $state<{base: string; quote: string; slug: string} | null>(null);
    let deleteLoading = $state(false);

    // Delete (bulk)
    let bulkDeleteDialogOpen = $state(false);
    let deletingPairs = $state<Array<{base: string; quote: string; slug: string}>>([]);
    let bulkDeleteLoading = $state(false);
    let bulkFxDeleteResults = $state<{label: string; success: boolean; detail?: string}[]>([]);

    // Modals
    let addModalOpen = $state(false);
    let fxTourPreview = $state(false);
    let syncModalOpen = $state(false);
    /** The sync dialog's pairs whose shown rates hold a stored row in its range (C-66): the dialog warns that the sync
     * replaces them. */
    let syncModalWithData = $derived.by(() => {
        if (!syncModalOpen) return [];
        const targets = new Set(syncModalPairs);
        const withData: string[] = [];
        for (const p of pairs) {
            const id = `${p.config.base}-${p.config.quote}`;
            if (targets.has(id) && hasStoredPointInRange(getFxStore(p.config.slug).getRange(dateStart, dateEnd).data, syncDateStart, dateEnd)) withData.push(id);
        }
        return withData;
    });
    let settingsModalOpen = $state(false);
    /** Slug of the pair currently being configured via per-card ⚙️ (null = global) */
    let settingsTargetSlug = $state<string | null>(null);
    /** Settings to pass to the modal (global or pair-specific) */
    let settingsForModal = $derived(settingsTargetSlug ? getSettingsForPair(settingsTargetSlug, 'fx') : getGlobalSettings('fx'));
    let settingsAxisContext = $derived.by(() => {
        if (!settingsTargetSlug) return $_('common.preview');
        const pair = pairs.find((item) => item.config.slug === settingsTargetSlug);
        if (!pair) return settingsTargetSlug.replace('-', '/');
        return isCardInverted(settingsTargetSlug) ? `${pair.config.quote}/${pair.config.base}` : `${pair.config.base}/${pair.config.quote}`;
    });
    let signalDefinitions = $state<SignalDefinition[]>([]);
    let signalResultsByPair = $state(new Map<string, SignalInstanceResult[]>());
    let signalCatalogFailed = $state(false);
    let signalRequestFailed = $state(false);
    const signalResultStates = new Map<string, SignalResultState>();
    let signalBackendError = $derived(signalCatalogFailed ? $_('chartSettings.signalCatalogUnavailable') : signalRequestFailed ? $_('chartSettings.signalResultsUnavailable') : null);

    // Asset list for cross-domain signal selection (loaded lazily)
    let availableAssetsList = $state<Array<{id: number; display_name: string; icon_url?: string | null; asset_type?: string | null; currency?: string | null; is_benchmark?: boolean}>>([]);

    // Filter bar adaptive layout is now owned by PageToolbar (shared with dashboard/broker-detail/
    // assets) — see the {#snippet filters}/{#snippet actions} below. Tune live via
    // window.__lfLayouts.fxList.thresholds.<field>.

    /** Mirrors the DateRangePicker's own effective 2-row max-width, so the Currency Filters row
     *  below it can be capped to the SAME pixel value when filtersStacked. MUST start
     *  non-undefined (matches DateRangePicker's own maxWidthTwoRow default, 390) — Svelte
     *  forbids bind:key={undefined} when the child prop has a declared fallback. */
    let pickerMaxWidth = $state<number>(390);

    // =========================================================================
    // Derived
    // =========================================================================

    let signalDefinitionsByType = $derived(new Map(signalDefinitions.map((definition) => [definition.type, definition])));

    // The Δ columns (1D … 5Y): the backend computes them up to the end of the range, both ways, and lists the
    // periods (X-R53). Kept apart from the rate flow. Which answer is kept while several are in flight, the ledger says
    // (X-R60); `periodChangesLoading` copies its `busy`, one-pair requests included.
    let periodSpecs = $state<PeriodSpec[]>([]);
    let periodDeltas = $state<Map<string, {direct: PeriodDeltas; inverse: PeriodDeltas}>>(new Map());
    let periodChangesLoading = $state(false);
    const periodChangesLedger = new PeriodChangesLedger<string>();
    // The Δ over the whole range (the table's Δ Abs and Δ %, the card's), both ways, comes in the same answer (X-R59),
    // kept by a ledger of its own: it belongs to the range's first day too, so a failed request keeps only the values
    // of the same range (`rangeKey`).
    let rangeDeltas = $state<Map<string, {direct: RangeDelta; inverse: RangeDelta}>>(new Map());
    const rangeDeltaLedger = new PeriodChangesLedger<string>();

    /** The identity of a range for the range-Δ ledger: both its days. */
    function rangeKey(start: string, end: string): string {
        return `${start}…${end}`;
    }

    // Which delta periods are visible for the selected date range
    let visiblePeriods = $derived(visiblePeriodColumns(periodSpecs, dateStart, dateEnd));

    // Extract unique currencies from configured pairs for filter dropdown
    let configuredCurrencies = $derived([...new Set(pairs.flatMap((p) => [p.config.base, p.config.quote]))].sort());

    // Allowed currencies for filter 1: if filter 2 is set, only currencies paired with filter 2
    // Exclude the value currently selected in filter 2
    let allowedForFilter1 = $derived((filterCurrency2 ? [...new Set(pairs.filter((p) => p.config.base === filterCurrency2 || p.config.quote === filterCurrency2).flatMap((p) => [p.config.base, p.config.quote]))] : configuredCurrencies).filter((c) => c !== filterCurrency2).sort());

    // Allowed currencies for filter 2: if filter 1 is set, only currencies paired with filter 1
    // Exclude the value currently selected in filter 1
    let allowedForFilter2 = $derived((filterCurrency1 ? [...new Set(pairs.filter((p) => p.config.base === filterCurrency1 || p.config.quote === filterCurrency1).flatMap((p) => [p.config.base, p.config.quote]))] : configuredCurrencies).filter((c) => c !== filterCurrency1).sort());

    // Filtered pairs
    let filteredPairs = $derived(
        pairs.filter((p) => {
            if (!filterCurrency1) return true;
            const fc1 = filterCurrency1.toUpperCase();
            const matchFirst = p.config.base === fc1 || p.config.quote === fc1;
            if (!matchFirst) return false;
            if (!filterCurrency2) return true;
            const fc2 = filterCurrency2.toUpperCase();
            return p.config.base === fc2 || p.config.quote === fc2;
        }),
    );

    // Map to FxRow for table view
    let fxTableRows = $derived<FxRow[]>(
        filteredPairs.map((p) => {
            const changes = periodDeltas.get(`${p.config.base}/${p.config.quote}`);
            const deltas: PeriodDeltas = (isCardInverted(p.config.slug) ? changes?.inverse : changes?.direct) ?? {};
            return {
                slug: p.config.slug,
                base: p.config.base,
                quote: p.config.quote,
                data: p.data,
                manualOnly: p.config.providers.length === 1 && p.config.providers[0].providerCode === 'MANUAL',
                providers: p.config.providers,
                deltas,
                rangeDeltas: rangeDeltas.get(`${p.config.base}/${p.config.quote}`) ?? null,
            };
        }),
    );

    // =========================================================================
    // Lifecycle
    // =========================================================================

    async function loadFxSignalDefinitions(force = false) {
        try {
            signalDefinitions = await signalCatalogStore.load('fx', force);
            signalCatalogFailed = false;
        } catch (catalogError) {
            console.error('Failed to load FX signal catalog:', catalogError);
            signalDefinitions = getLocalSignalDefinitions();
            signalCatalogFailed = true;
        }
    }

    function resultStateForPair(slug: string): SignalResultState {
        let state = signalResultStates.get(slug);
        if (!state) {
            state = new SignalResultState();
            signalResultStates.set(slug, state);
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
        await pageBusy.track('fx-signals-retry', async () => {
            await loadFxSignalDefinitions(true);
            // The rates and the signals only: the Δ columns do not depend on the signals (X-R60).
            await fetchAllPairSeries();
        });
    }

    onMount(async () => {
        // Preload currency graph so provider icons are cached before FxTable renders (E1c fix)
        getCurrencyGraph();
        // The first load holds the page's Refresh button (Y11): the catalog, the pairs, their rates.
        await pageBusy.track('fx-first-load', async () => {
            await loadFxSignalDefinitions();
            await loadPairSources();
        });
        // Load asset list for cross-domain signal selection
        loadAssetList();
        onboardingGuide.maybeStartContextual('fx_page_guide');
    });

    // =========================================================================
    // Data Loading
    // =========================================================================

    async function loadPairSources(propagateError = false) {
        const sessionGeneration = getClientSessionGeneration();
        const current = () => pageAlive && isClientSessionCurrent(sessionGeneration);
        if (!current()) return;
        loading = true;
        error = null;
        try {
            const response = await zodiosApi.list_routes_api_v1_fx_providers_routes_get();
            if (!current()) return;
            const items = response?.items ?? [];

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
                const providerCode = item.is_chain ? 'CHAIN:' + steps.map((s) => s.provider).join('+') : steps[0].provider;
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
            pairs = Array.from(pairMap.values()).map((config) => ({
                config,
                data: getFxStore(config.slug).getAllSorted(),
                // Born already waiting for wave 2, so the card/row draws its own
                // skeleton the instant it appears instead of a bare empty chart.
                loading: true,
            }));
        } catch (e: any) {
            if (!current()) return;
            console.error('Failed to load pair sources:', e);
            error = e?.message || $_('fx.loadFailed');
            if (propagateError) throw e;
        } finally {
            if (current()) loading = false;
        }

        // Wave 2 — rates, signals, "All" resolution — deliberately OUTSIDE the
        // `loading` window: routes and rates are two separate calls, so the page
        // renders as soon as the pairs are known and each card fills in on its
        // own (loading={pair.loading}). fetchAllPairData() owns its own errors
        // and clears `loading` on every path.
        if (current() && !error) await fetchAllPairData(propagateError);
    }

    /**
     * When "All" (MAX) is pending resolution, extract the real earliest date
     * across ALL loaded pairs (global minimum) and update dateStart/
     * displayDateStart. The URL is left untouched — it keeps showing the
     * generic "min"/"max" sentinel (set in handleDateRangeChange) so the
     * "All" selection survives reloads/shares instead of freezing to a
     * specific historical date. No-op once already resolved or if no pair
     * has any rate data yet.
     */
    function resolveMaxStartFromPairs() {
        if (!isMaxPending) return;
        const firstDates = pairs.map((p) => p.data?.[0]?.date).filter((d): d is string => !!d);
        if (firstDates.length === 0) return;
        dateStart = firstDates.reduce((min, d) => (d < min ? d : min));
        displayDateStart = dateStart;
        isMaxPending = false;
    }

    /**
     * Counterpart to resolveMaxStartFromPairs(): re-arm "All" resolution
     * before a forced full reload. Once isMaxPending resolves, dateStart
     * freezes at whatever the earliest stored date was AT THAT TIME — a sync
     * "Tutti" that later reaches further into the past would silently not
     * show, because fetchAllPairData() keeps querying the frozen, narrower
     * dateStart. Widening dateStart back to the anchor and re-arming
     * isMaxPending lets resolveMaxStartFromPairs() pick up the new true
     * earliest date once the fresh (wide) query returns.
     */
    function rearmMaxPendingBeforeReload() {
        if (activePreset !== 'MAX') return;
        isMaxPending = true;
        dateStart = resolveDateSentinel('min');
        displayDateStart = 'min';
    }

    /**
     * Rates and signals (the bulk convert, the cache) and the Δ columns (the backend's period changes), together. The
     * signals' retry, a settings change and an inversion ask only the rates and signals (`fetchAllPairSeries`): the Δ
     * columns come both ways and depend on none of them (X-R60).
     */
    async function fetchAllPairData(propagateError = false, silent = false) {
        await Promise.all([fetchAllPairSeries(propagateError, silent), loadPeriodChanges(silent), fetchCalendarReturns(undefined, silent), fetchComparisonSeries([], silent)]);
    }

    // A price catch-up (the bus's `{kind: 'prices'}`, Y5-1, Z-14b): the rates, the Δ columns, the rolling returns and the compared assets on
    // screen are asked again, in silence — the cards keep their lines, nothing says the page is busy — and outside `pageBusy`: it is not the
    // user's Refresh.
    onMount(() => onPricesCaughtUp(() => (pageAlive ? fetchAllPairData(false, true) : undefined)));

    /** The view a card shows: its own saved one, else the FX list's (Y-40). */
    function cardPrimaryView(slug: string): ChartPrimaryView {
        void getSettingsVersion();
        return getSettingsForPair(slug, 'fx').primaryView;
    }

    /** The top bar (V-3 a): every card takes the view; the cards entering or leaving the rolling return ask it, or drop it. */
    function handleListPrimaryView(view: ChartPrimaryView) {
        const toCalendar = view === 'calendar-return';
        const changed = new Set(pairs.filter((pair) => (cardPrimaryView(pair.config.slug) === 'calendar-return') !== toCalendar).map((pair) => pair.config.slug));
        setScopePrimaryView(view, 'fx');
        if (changed.size > 0) void pageBusy.track('fx-view', () => fetchCalendarReturns(changed));
    }

    /** A card's button (V-1 a): that card keeps the view; entering or leaving the rolling return, it asks it, or drops it. */
    function handleCardPrimaryView(slug: string, view: ChartPrimaryView) {
        const wasCalendar = cardPrimaryView(slug) === 'calendar-return';
        setItemPrimaryView(slug, view, 'fx');
        if (wasCalendar !== (view === 'calendar-return')) void pageBusy.track('fx-view', () => fetchCalendarReturns(new Set([slug])));
    }

    /** The FX pairs a card's `fx-pair` signals compare, the way each shows its pair. */
    function pairTargetsOf(configs: SignalConfig[]): FxCalendarCardInput['pairTargets'] {
        return configs.filter((config) => config.signalType === 'fx-pair' && config.params.pairSlug).map((config) => ({configId: config.id, pairSlug: String(config.params.pairSlug), inverted: Boolean(config.params._inverted)}));
    }

    /** The cards' rolling returns and their compared pairs', by entry, from the answers of a convert request (Y-40). */
    function calendarViewsOf(answers: ReadonlyArray<{batch: {items: readonly FxCalendarEntry[]}; answer: unknown}>) {
        const own = new Map<string, CalendarReturnView>();
        const targets = new Map<string, Map<string, CalendarReturnView>>();
        for (const {batch, answer} of answers) {
            // A request_index is local to the request that carried it: it points into that batch's entries.
            const groups: unknown[] = (answer as {signal_results?: unknown[]})?.signal_results ?? [];
            for (const group of groups) {
                const {request_index: index, signals} = group as {request_index?: number; signals?: unknown};
                const entry = typeof index === 'number' ? batch.items[index] : undefined;
                if (!entry) continue;
                const view = extractCalendarReturnView(signals, CALENDAR_RETURN_INSTANCE_ID);
                if (entry.role === 'card') own.set(entry.cardSlug, view);
                else if (entry.configId) {
                    if (!targets.has(entry.cardSlug)) targets.set(entry.cardSlug, new Map());
                    targets.get(entry.cardSlug)!.set(entry.configId, view);
                }
            }
        }
        return {own, targets};
    }

    /**
     * The rolling return of the cards in that view (Y-40), with their compared pairs', from the backend's sampled
     * conversions (Z-29fx, `utils/reducedFxQuery.ts`); the cards in another view drop theirs. `only` limits it to some cards.
     * The conversions' rates are not the cards' daily rates: they never reach the FX stores.
     */
    async function fetchCalendarReturns(only?: ReadonlySet<string>, silent = false) {
        const sessionGeneration = getClientSessionGeneration();
        const current = () => pageAlive && isClientSessionCurrent(sessionGeneration);
        if (!current()) return;
        const rangeDays = calendarReturnRangeDays(dateStart, dateEnd);
        const next = new Map(calendarBySlug);
        const cards: FxCalendarCardInput[] = [];
        const requestId = ++calendarRequestSeq;
        for (const pair of pairs) {
            const slug = pair.config.slug;
            if (only && !only.has(slug)) continue;
            const settings = getSettingsForPair(slug, 'fx');
            if (settings.primaryView !== 'calendar-return') {
                next.delete(slug);
                continue;
            }
            const windowDays = calendarReturnWindowDays(effectiveCalendarReturnWindow(settings, rangeDays)) ?? 30;
            cards.push({slug, base: pair.config.base, quote: pair.config.quote, inverted: isCardInverted(slug), plotWidthPx: DEFAULT_COMPACT_PLOT_WIDTH_PX, start: dateStart, end: dateEnd, windowDays, pairTargets: pairTargetsOf(settings.signals)});
            calendarRequestOfSlug.set(slug, requestId);
            // While the new return loads, the old one stays on screen. A silent reload (a catch-up) keeps its state as well: the page does not say busy.
            const previous = next.get(slug);
            next.set(slug, {own: {...(previous?.own ?? emptyCalendarReturnView()), state: silent && previous ? previous.own.state : 'loading'}, targets: previous?.targets ?? new Map()});
        }
        calendarBySlug = next;
        if (cards.length === 0) return;

        const settle = (views: ReturnType<typeof calendarViewsOf> | null) => {
            const settled = new Map(calendarBySlug);
            for (const card of cards) {
                const previous = settled.get(card.slug);
                if (!previous || calendarRequestOfSlug.get(card.slug) !== requestId) continue;
                const own = views?.own.get(card.slug);
                settled.set(card.slug, own ? {own, targets: views?.targets.get(card.slug) ?? new Map()} : {own: {...previous.own, state: 'error'}, targets: previous.targets});
            }
            calendarBySlug = settled;
        };
        const today = todayIso();
        try {
            const outcome = await sendBulkBatches(
                buildFxCalendarQuery(cards),
                (entry) => estimateFxCalendarDays(entry, today),
                (batch) => zodiosApi.convert_currency_bulk_api_v1_fx_currencies_convert_post(batch.map((entry) => entry.request)),
                {groupOf: (entry) => entry.group},
            );
            if (!current()) return;
            settle(calendarViewsOf(outcome.answers));
            if (outcome.failed) {
                console.error('Failed to fetch the FX rolling returns:', outcome.error);
                const refusal = bulkRefusalMessage(outcome.error, $_);
                if (refusal !== null) toasts.error(refusal);
            }
        } catch (requestError) {
            if (!current()) return;
            console.error('Failed to fetch the FX rolling returns:', requestError);
            settle(null);
        }
    }

    function translateCalendarProblem(key: string, values?: Record<string, string | number>): string {
        return values ? $_(key, {values}) : $_(key);
    }

    /** A card's rolling return, with the detail's message when the backend has none (V-7 a). */
    function cardCalendarReturn(slug: string) {
        const view = calendarBySlug.get(slug)?.own ?? emptyCalendarReturnView('loading');
        const problemMessage = view.problem ? formatSignalProblem(view.problem, translateCalendarProblem, (field) => $_(`signals.dataFields.${field}`)) : view.state === 'error' ? $_('chartSettings.signalResultsUnavailable') : null;
        return {state: view.state, points: view.points, problemCode: view.problem?.code ?? null, problemMessage};
    }

    /** A card's compared pairs in the rolling-return view (V-5 a): their returns. */
    function cardCalendarOverlays(slug: string): RenderedSignal[] {
        const views = calendarBySlug.get(slug)?.targets;
        return views ? renderCalendarPairComparisons(getSettingsForPair(slug, 'fx').signals, views) : [];
    }

    /** The plot width the settings preview asks its rolling return for (Y-40): about the preview chart's. */
    const CALENDAR_PREVIEW_PLOT_WIDTH_PX = 600;

    /**
     * The rolling return of the settings preview (Y-40). A card's: its pair's over the range on screen, the way the card
     * shows it, with its compared pairs', as the card asks them. The global settings': the synthetic curve the modal hands,
     * through `/signals/preview`, as the other backend signals of that preview.
     */
    async function resolveCalendarPreview(windowDays: number, configs: SignalConfig[], points: LineDataPoint[]): Promise<{points: LineDataPoint[]; overlays: RenderedSignal[]} | null> {
        const slug = settingsTargetSlug;
        if (!slug) {
            if (points.length === 0) return null;
            const response = await zodiosApi.compute_signal_preview_api_v1_signals_preview_post({domain: 'fx', points: points.map((point) => ({date: point.date, value: point.value})), signals: [fxCalendarRequest(windowDays)]});
            const view = extractCalendarReturnView(response.signals ?? [], CALENDAR_RETURN_INSTANCE_ID);
            return view.state === 'ready' || view.state === 'partial' ? {points: view.points, overlays: []} : null;
        }
        const pair = pairs.find((item) => item.config.slug === slug);
        if (!pair) return null;
        const entries = buildFxCalendarQuery([{slug, base: pair.config.base, quote: pair.config.quote, inverted: isCardInverted(slug), plotWidthPx: CALENDAR_PREVIEW_PLOT_WIDTH_PX, start: dateStart, end: dateEnd, windowDays, pairTargets: pairTargetsOf(configs)}]);
        const answer = await zodiosApi.convert_currency_bulk_api_v1_fx_currencies_convert_post(entries.map((entry) => entry.request));
        const views = calendarViewsOf([{batch: {items: entries}, answer}]);
        const own = views.own.get(slug);
        if (!own || (own.state !== 'ready' && own.state !== 'partial')) return null;
        return {points: own.points, overlays: renderCalendarPairComparisons(configs, views.targets.get(slug) ?? new Map())};
    }

    /** The Δ columns of every configured pair up to the end of the range, and each pair's Δ over the range, both ways, from the backend (X-R53, X-R59). */
    async function loadPeriodChanges(silent = false) {
        const sessionGeneration = getClientSessionGeneration();
        const current = () => pageAlive && isClientSessionCurrent(sessionGeneration);
        if (!current() || pairs.length === 0) return;
        const ticket = periodChangesLedger.begin(dateEnd, true);
        const rangeStart = dateStart;
        const rangeTicket = rangeDeltaLedger.begin(rangeKey(rangeStart, ticket.asOf), true);
        if (!silent) periodChangesLoading = periodChangesLedger.busy || rangeDeltaLedger.busy;
        try {
            const result = await fetchFxPeriodChanges(
                pairs.map((pair) => ({base: pair.config.base, quote: pair.config.quote})),
                ticket.asOf,
                rangeStart,
            );
            if (!current()) return;
            const nextRange = rangeDeltaLedger.settle(rangeTicket, rangeDeltas, result.rangeDeltasByPair);
            if (nextRange !== null) rangeDeltas = nextRange;
            const next = periodChangesLedger.settle(ticket, periodDeltas, result.deltasByPair);
            if (next === null) return;
            if (result.periods.length > 0) periodSpecs = result.periods;
            periodDeltas = next;
        } catch (requestError) {
            if (!current()) return;
            // The Δ computed up to the same day stay: only those of another range go (X-R60); the range's Δ, only for the same range.
            const nextRange = rangeDeltaLedger.fail(rangeTicket, rangeDeltas);
            if (nextRange !== null) rangeDeltas = nextRange;
            const next = periodChangesLedger.fail(ticket, periodDeltas);
            if (next === null) return;
            console.error('Failed to fetch FX period changes:', requestError);
            periodDeltas = next;
        } finally {
            periodChangesLedger.end(ticket);
            rangeDeltaLedger.end(rangeTicket);
            periodChangesLoading = periodChangesLedger.busy || rangeDeltaLedger.busy;
        }
    }

    /**
     * One pair's Δ columns and Δ over the range from the backend, merged into the others' (after its sync, or once
     * added). The page stays busy while it is in flight, and a full answer asked before it can no longer overwrite the
     * pair (X-R60).
     */
    async function loadPairPeriodChanges(index: number) {
        const pair = pairs[index];
        if (!pair) return;
        const sessionGeneration = getClientSessionGeneration();
        const current = () => pageAlive && isClientSessionCurrent(sessionGeneration);
        const ticket = periodChangesLedger.begin(dateEnd, false);
        const rangeStart = dateStart;
        const rangeTicket = rangeDeltaLedger.begin(rangeKey(rangeStart, ticket.asOf), false);
        periodChangesLoading = periodChangesLedger.busy || rangeDeltaLedger.busy;
        try {
            const result = await fetchFxPeriodChanges([{base: pair.config.base, quote: pair.config.quote}], ticket.asOf, rangeStart);
            if (!current()) return;
            const nextRange = rangeDeltaLedger.settle(rangeTicket, rangeDeltas, result.rangeDeltasByPair);
            if (nextRange !== null) rangeDeltas = nextRange;
            const next = periodChangesLedger.settle(ticket, periodDeltas, result.deltasByPair);
            if (next === null) return;
            if (result.periods.length > 0) periodSpecs = result.periods;
            periodDeltas = next;
        } catch (requestError) {
            if (current()) console.error(`Failed to fetch the period changes of ${pair.config.slug}:`, requestError);
        } finally {
            periodChangesLedger.end(ticket);
            rangeDeltaLedger.end(rangeTicket);
            periodChangesLoading = periodChangesLedger.busy || rangeDeltaLedger.busy;
        }
    }

    async function fetchAllPairSeries(propagateError = false, silent = false) {
        const sessionGeneration = getClientSessionGeneration();
        const current = () => pageAlive && isClientSessionCurrent(sessionGeneration);
        if (!current() || pairs.length === 0) return;
        void getSettingsVersion();

        const bulkRequests: Array<{
            slug: string;
            start: string;
            end: string;
            signals: ReturnType<typeof buildBackendSignalRequestPlan>['requests'];
            displayedInverted: boolean;
        }> = [];
        const needFetch: Array<{index: number; slug: string}> = [];
        const requestContexts = new Map<
            string,
            {
                configs: SignalConfig[];
                plan: ReturnType<typeof buildBackendSignalRequestPlan>;
                requestVersion: number;
            }
        >();
        const nextSignalResults = new Map(signalResultsByPair);

        for (let i = 0; i < pairs.length; i++) {
            const pair = pairs[i];
            const store = getFxStore(pair.config.slug);
            const configs = getSettingsForPair(pair.config.slug, 'fx').signals;
            const plan = buildBackendSignalRequestPlan(configs, signalDefinitions);
            const state = resultStateForPair(pair.config.slug);
            const requestVersion = state.beginRequest();
            requestContexts.set(pair.config.slug, {
                configs,
                plan,
                requestVersion,
            });

            const needsRates = store.getMissingIntervals(dateStart, dateEnd).length > 0;
            if (!needsRates) {
                // Fast path: already cached — nothing to wait for, so clear the
                // per-card skeleton here too (this branch never reaches the bulk
                // call below, which is the only other place that clears it).
                pairs[i] = {...pair, data: store.getRange(dateStart, dateEnd).data, loading: false};
            } else {
                needFetch.push({index: i, slug: pair.config.slug});
                // A store a catch-up marked stale that still holds points for the range (Y5-1, D3): they go on screen at once and the rates
                // are asked in background, with no skeleton. A silent reload of the range already on screen leaves the card as it is.
                const staleHeld = store.isStale ? store.getRange(dateStart, dateEnd).data : [];
                pairs[i] = staleHeld.length > 0 ? {...pair, data: silent && pair.data.length > 0 ? pair.data : staleHeld, loading: false} : silent ? pair : {...pair, loading: true};
            }

            if (needsRates || plan.requests.length > 0) {
                bulkRequests.push({
                    slug: pair.config.slug,
                    start: dateStart,
                    end: dateEnd,
                    signals: plan.requests,
                    displayedInverted: isCardInverted(pair.config.slug),
                });
            } else {
                const mapped = mapSignalInstanceResults(configs, plan, []);
                if (state.apply(requestVersion, mapped)) {
                    nextSignalResults.set(pair.config.slug, [...state.values()]);
                }
            }
        }

        if (bulkRequests.length === 0) {
            signalResultsByPair = nextSignalResults;
            signalRequestFailed = false;
            resolveMaxStartFromPairs();
            return;
        }

        // One bulk call for every pair needing rates and/or signals, in batches under the backend's caps (Z-27).
        signalRequestFailed = false;
        try {
            const bulkResult = await loadFxRatesAndSignalsBulk(bulkRequests);
            if (!current()) return;
            for (const [slug, context] of requestContexts) {
                const state = resultStateForPair(slug);
                const mapped = mapSignalInstanceResults(context.configs, context.plan, bulkResult.signalsBySlug.get(slug) ?? []);
                if (state.apply(context.requestVersion, mapped)) {
                    nextSignalResults.set(slug, [...state.values()]);
                }
            }
            signalResultsByPair = nextSignalResults;
            pairs = pairs.map((pair) => ({
                ...pair,
                data: bulkResult.dataBySlug.get(pair.config.slug) ?? getFxStore(pair.config.slug).getRange(dateStart, dateEnd).data,
                loading: false,
            }));
            resolveMaxStartFromPairs();
        } catch (requestError) {
            if (!current()) return;
            console.error('Failed to fetch FX rates/signals bulk:', requestError);
            // X-R58: a request the backend refused as too large is said, not left as cards without rates.
            const refusal = bulkRefusalMessage(requestError, $_);
            if (refusal !== null) toasts.error(refusal);
            signalRequestFailed = [...requestContexts.values()].some((context) => context.plan.requests.length > 0);
            // Fallback: update with whatever is cached
            for (const nf of needFetch) {
                const existingData = getFxStore(nf.slug).getRange(dateStart, dateEnd).data;
                pairs[nf.index] = {...pairs[nf.index], data: existingData, loading: false};
            }
            if (propagateError) throw requestError;
        }
    }

    /** One pair's rates and signals, and its Δ columns, together. */
    async function fetchPairData(index: number) {
        await Promise.all([fetchPairSeries(index), loadPairPeriodChanges(index)]);
    }

    async function fetchPairSeries(index: number) {
        const pair = pairs[index];
        if (!pair) return;
        const store = getFxStore(pair.config.slug);
        const configs = getSettingsForPair(pair.config.slug, 'fx').signals;
        const plan = buildBackendSignalRequestPlan(configs, signalDefinitions);
        const state = resultStateForPair(pair.config.slug);
        const requestVersion = state.beginRequest();
        const needsRates = store.getMissingIntervals(dateStart, dateEnd).length > 0;

        if (!needsRates && plan.requests.length === 0) {
            pairs[index] = {...pair, data: store.getRange(dateStart, dateEnd).data};
            const mapped = mapSignalInstanceResults(configs, plan, []);
            if (state.apply(requestVersion, mapped)) {
                signalResultsByPair = new Map(signalResultsByPair).set(pair.config.slug, [...state.values()]);
            }
            return;
        }

        pairs[index] = {...pair, loading: needsRates};

        try {
            const result = await loadFxRatesAndSignalsBulk([
                {
                    slug: pair.config.slug,
                    start: dateStart,
                    end: dateEnd,
                    signals: plan.requests,
                    displayedInverted: isCardInverted(pair.config.slug),
                },
            ]);
            const mapped = mapSignalInstanceResults(configs, plan, result.signalsBySlug.get(pair.config.slug) ?? []);
            if (state.apply(requestVersion, mapped)) {
                signalResultsByPair = new Map(signalResultsByPair).set(pair.config.slug, [...state.values()]);
            }
            pairs[index] = {
                ...pair,
                data: result.dataBySlug.get(pair.config.slug) ?? store.getRange(dateStart, dateEnd).data,
                loading: false,
            };
            signalRequestFailed = false;
        } catch (e: any) {
            signalRequestFailed = plan.requests.length > 0;
            const existingData = store.getRange(dateStart, dateEnd).data;
            pairs[index] = {...pair, data: existingData, loading: false};
            if (e?.response?.status !== 404) {
                console.error(`Failed to fetch data for ${pair.config.slug}:`, e);
            }
            const refusal = bulkRefusalMessage(e, $_);
            if (refusal !== null) toasts.error(refusal);
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
        const shouldReloadBackend = backendRequestFingerprint(settingsForModal.signals) !== backendRequestFingerprint(s.signals);
        const target = settingsTargetSlug;
        // The rolling-return view asks its own data (Y-40): entering it, leaving it, or a window or a pair changed in it.
        const calendarBefore = target ? cardPrimaryView(target) === 'calendar-return' : pairs.some((pair) => cardPrimaryView(pair.config.slug) === 'calendar-return');
        if (target) {
            setPairSettings(target, s);
        } else {
            setGlobalSettings(s, 'fx');
        }
        if (shouldReloadBackend) {
            void pageBusy.track('fx-settings', () => fetchAllPairSeries());
        }
        // A comparison with an asset saved in this window: its series, if the cache lacks them (the window asked them while open).
        void fetchComparisonSeries(comparisonTargetIds(s.signals, 0));
        if (calendarBefore || s.primaryView === 'calendar-return') {
            void pageBusy.track('fx-settings', () => fetchCalendarReturns(target ? new Set([target]) : undefined));
        }
    }

    /** Load asset list for signal settings — lightweight, no chart data needed */
    async function loadAssetList() {
        try {
            const response = await zodiosApi.list_assets_api_v1_assets_query_get({queries: {}});
            const items = response as any[];
            availableAssetsList = items.map((a: any) => ({
                id: a.id,
                display_name: a.display_name,
                icon_url: a.icon_url ?? null,
                asset_type: a.asset_type ?? null,
                currency: a.currency ?? null,
                is_benchmark: a.is_benchmark === true,
            }));
            // The cards' comparisons with an asset need its currency (the key of its cached series): ask them now.
            void fetchComparisonSeries();
        } catch {
            // Non-critical — asset dropdown will just be empty
        }
    }

    // =========================================================================
    // The comparisons with an asset (Y-41)
    // =========================================================================

    /**
     * Bumped when asset series reach the cache: the price stores are not reactive, so what reads them (the cards' signals)
     * reads this too, and draws again.
     */
    let comparisonSeriesVersion = $state(0);
    let comparisonSeriesLoading = $state(0);
    let comparisonSeriesChain: Promise<void> = Promise.resolve();

    /**
     * The daily series of the assets the cards compare (`comparisonSeries.ts`): one request for all of them, only for the
     * cards that have such a comparison, and only for what the cache does not cover (the asset detail page fills the same
     * cache). `extraIds` adds assets the settings window is about to draw. Never throws.
     */
    function fetchComparisonSeries(extraIds: readonly number[] = [], silent = false): Promise<void> {
        // One at a time: a call that follows another finds what it loaded in the cache, and asks nothing twice.
        comparisonSeriesChain = comparisonSeriesChain.then(() => loadComparisonSeries(extraIds, silent));
        return comparisonSeriesChain;
    }

    async function loadComparisonSeries(extraIds: readonly number[], silent: boolean) {
        const sessionGeneration = getClientSessionGeneration();
        const ids = new Set(extraIds);
        for (const pair of pairs) {
            for (const id of comparisonTargetIds(getSettingsForPair(pair.config.slug, 'fx').signals, 0)) ids.add(id);
        }
        const assets = [...ids].flatMap((id) => {
            const asset = availableAssetsList.find((candidate) => candidate.id === id);
            return asset?.currency ? [{id, currency: asset.currency}] : [];
        });
        if (assets.length === 0) return;
        const range = {start: dateStart, end: dateEnd};
        if (!silent) comparisonSeriesLoading++;
        try {
            await ensureComparisonSeries(assets, range);
        } finally {
            if (!silent) comparisonSeriesLoading--;
        }
        if (pageAlive && isClientSessionCurrent(sessionGeneration)) comparisonSeriesVersion++;
    }

    /** An asset the settings window draws and the cache lacks is asked once per range, as the list of assets asks a target (Z-29d). */
    const wantedForPreview = new Set<string>();
    function wantComparisonSeries(assetId: number) {
        const key = `${assetId}|${dateStart}|${dateEnd}`;
        if (wantedForPreview.has(key)) return;
        wantedForPreview.add(key);
        // Read from a derived: the load starts after it, never inside it.
        queueMicrotask(() => void fetchComparisonSeries([assetId]));
    }

    /**
     * Where the cards — and their settings preview — get the series their saved comparisons read (Y-39a, Y-41): an FX
     * pair from the FX stores, straight, each signal turning its pair by its own `_inverted`; an asset from the price
     * cache, its daily series in its own currency (`comparisonSeries.ts`, as the FX detail page draws it). With `readMissing`
     * (the settings window) an asset the cache lacks is asked.
     */
    function signalSourcesFor(readMissing: boolean): SignalDataSources {
        return {
            fxPairData: (pairSlug) =>
                getFxStore(pairSlug)
                    .getAllSorted()
                    .map((point) => fxPointToLineDataPoint(point, false)),
            comparisonTarget: (assetId) => {
                void comparisonSeriesVersion;
                const asset = availableAssetsList.find((candidate) => candidate.id === assetId);
                if (!asset?.currency) return null;
                const target = comparisonTargetFromStore({id: asset.id, currency: asset.currency, display_name: asset.display_name, icon_url: asset.icon_url, asset_type: asset.asset_type});
                if (!target && readMissing) wantComparisonSeries(assetId);
                return target;
            },
        };
    }
    const fxListSignalSources = signalSourcesFor(false);
    const settingsSignalSources = signalSourcesFor(true);

    /**
     * Render overlay signals for a pair. Called by FxCard reactively whenever
     * cardViewMode or inverted changes. Receives absolute chart data (post-inversion).
     */
    function getRenderedSignals(slug: string, absoluteData: LineDataPoint[], vm: 'absolute' | 'percentage'): RenderedSignal[] {
        // Access version to trigger reactivity
        void getSettingsVersion();
        const settings = getSettingsForPair(slug, 'fx');
        if (!settings.signals.length) return [];
        return [...renderLocalSignals(settings.signals, signalDefinitionsByType, absoluteData, vm, fxListSignalSources), ...renderBackendResults(settings.signals, signalResultsByPair.get(slug) ?? [], signalDefinitionsByType, absoluteData, vm, (key) => $_(key))];
    }

    /**
     * Global (filter-bar) mode: compute backend overlay signals live on the
     * modal's synthetic preview curve, so indicators like SMA render in the
     * preview without a real pair. Backend indicators can't run in the browser.
     */
    async function resolveGlobalBackendPreview(configs: SignalConfig[], points: LineDataPoint[], viewMode: 'absolute' | 'percentage'): Promise<RenderedSignal[]> {
        const plan = buildBackendSignalRequestPlan(configs, signalDefinitions);
        if (plan.requests.length === 0 || points.length === 0) return [];
        const response = await zodiosApi.compute_signal_preview_api_v1_signals_preview_post({
            domain: 'fx',
            points: points.map((point) => ({date: point.date, value: point.value})),
            signals: plan.requests,
        });
        const mapped = mapSignalInstanceResults(configs, plan, response.signals ?? []);
        return renderBackendResults(configs, mapped, signalDefinitionsByType, points, viewMode, (key) => $_(key));
    }

    function resolveSettingsBackendPreview(viewMode: 'absolute' | 'percentage'): RenderedSignal[] {
        if (!settingsTargetSlug) return [];
        const pair = pairs.find((item) => item.config.slug === settingsTargetSlug);
        if (!pair?.data.length) return [];
        const inverted = isCardInverted(settingsTargetSlug);
        const absoluteData = pair.data.map((point) => fxPointToLineDataPoint(point, inverted));
        return getRenderedSignals(settingsTargetSlug, absoluteData, viewMode);
    }

    // =========================================================================
    // Actions
    // =========================================================================

    async function handleRefreshAll() {
        refreshing = true;
        try {
            invalidateAllFxStores();
            rearmMaxPendingBeforeReload();
            pairs = pairs.map((p) => ({...p, data: [], loading: true}));
            await pageBusy.track('fx-refresh', () => fetchAllPairData());
        } finally {
            refreshing = false;
        }
    }

    async function handleRefreshPair(detail: {slug: string}) {
        const idx = pairs.findIndex((p) => p.config.slug === detail.slug);
        if (idx < 0) return;
        const store = getFxStore(detail.slug);
        store.invalidateRange(dateStart, dateEnd);
        await fetchPairData(idx);
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
            await zodiosApi.delete_routes_bulk_api_v1_fx_providers_routes_delete([
                {
                    base: deletingPair.base,
                    quote: deletingPair.quote,
                },
            ]);

            // Step 2: Delete all historical rates for this pair
            const deleteResponse = await zodiosApi.delete_rates_endpoint_api_v1_fx_currencies_rate_delete([
                {
                    from: deletingPair.base,
                    to: deletingPair.quote,
                    delete_all: true,
                },
            ]);
            const rateCount = (deleteResponse as any)?.results?.[0]?.deleted_count ?? 0;

            // Step 3: Clean up frontend state
            removeFxStore(deletingPair.slug);
            pairs = pairs.filter((p) => p.config.slug !== deletingPair!.slug);

            // Step 4: Reset currency filters if selected currency no longer exists
            const remaining = new Set(pairs.flatMap((p) => [p.config.base, p.config.quote]));
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
        void pageBusy.track('fx-period', () => fetchAllPairData());
    }

    function handleAddPair() {
        if (onboardingGuide.active?.flow === 'fx_page_guide') {
            onboardingGuide.dismissHost();
        }
        fxTourPreview = false;
        addModalOpen = true;
        onboardingGuide.maybeStartContextual('fx_guide');
    }

    function closeAddPair() {
        addModalOpen = false;
        fxTourPreview = false;
        if (onboardingGuide.active?.flow === 'fx_guide') {
            onboardingGuide.dismissHost({restartAtFirst: true});
        }
    }

    function handleSyncAll() {
        syncModalPairs = pairs.filter((p) => !(p.config.providers.length === 1 && p.config.providers[0].providerCode === 'MANUAL')).map((p) => `${p.config.base}-${p.config.quote}`);
        syncModalOpen = true;
    }

    // =========================================================================
    // Bulk Actions (table selection)
    // =========================================================================

    function handleBulkSyncFx() {
        syncModalPairs = selectedFxRows.filter((r) => !r.manualOnly).map((r) => `${r.base}-${r.quote}`);
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
        const slugs = selectedFxRows.map((r) => r.slug);
        fxTableComponent?.bulkToggleInversion(slugs);
        fxTableComponent?.getTableRef()?.clearSelection();
        selectedFxRows = [];
    }

    async function handleBulkDeleteFx() {
        deletingPairs = selectedFxRows.map((r) => ({base: r.base, quote: r.quote, slug: r.slug}));
        bulkDeleteDialogOpen = true;
    }

    async function confirmBulkDelete() {
        if (deletingPairs.length === 0) return;
        bulkDeleteLoading = true;
        const perPairResults: {label: string; success: boolean; detail?: string}[] = [];
        try {
            for (const pair of deletingPairs) {
                try {
                    await zodiosApi.delete_routes_bulk_api_v1_fx_providers_routes_delete([
                        {
                            base: pair.base,
                            quote: pair.quote,
                        },
                    ]);
                    const deleteResponse = await zodiosApi.delete_rates_endpoint_api_v1_fx_currencies_rate_delete([
                        {
                            from: pair.base,
                            to: pair.quote,
                            delete_all: true,
                        },
                    ]);
                    const rateCount = (deleteResponse as any)?.results?.[0]?.deleted_count ?? 0;
                    removeFxStore(pair.slug);
                    perPairResults.push({
                        label: `${pair.base}/${pair.quote}`,
                        success: true,
                        detail: $_('fx.delete.resultDeleted', {values: {n: rateCount}}),
                    });
                } catch (pairErr: any) {
                    perPairResults.push({
                        label: `${pair.base}/${pair.quote}`,
                        success: false,
                        detail: pairErr?.message || $_('common.error'),
                    });
                }
            }

            const deletedSlugs = new Set(perPairResults.filter((r) => r.success).map((_, i) => deletingPairs[i].slug));
            pairs = pairs.filter((p) => !deletedSlugs.has(p.config.slug));

            // Reset currency filters if selected currency no longer exists
            const remaining = new Set(pairs.flatMap((p) => [p.config.base, p.config.quote]));
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

    async function handleSyncPair(detail: {slug: string; base: string; quote: string}) {
        const {slug} = detail;
        const idx = pairs.findIndex((p) => p.config.slug === slug);
        if (idx < 0) return;
        pairs[idx] = {...pairs[idx], loading: true};
        try {
            const response = await zodiosApi.sync_rates_api_v1_fx_currencies_sync_post({
                pairs: [slug],
                start: syncDateStart,
                end: dateEnd,
            });
            const r = (response as any)?.results?.[0];
            if (r) {
                const t = get(_);
                const toast = buildFxSyncToast(r, slug, t, formatProviderText, formatSyncDetail);
                toasts[toast.variant](toast.message);
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

    async function handlePairCreated() {
        if (!pageAlive) return;
        addModalOpen = false;
        await pageBusy.track('fx-reload', () => loadPairSources());
    }

    async function handlePairCreationSynced(detail: FxPairSyncCompleteDetail) {
        if (!pageAlive || !isClientSessionCurrent(detail.sessionGeneration)) return;
        // Creation refresh has settled; the helper invalidated only the new pairs.
        await loadPairSources(true);
    }

    async function handleSynced() {
        // Don't close modal — let user see the results, they close manually
        // But refresh data in background
        invalidateAllFxStores();
        rearmMaxPendingBeforeReload();
        pairs = pairs.map((p) => ({...p, data: [], loading: true}));
        await fetchAllPairData();
    }

    /**
     * Same two-wave load as the assets page: the pair list first, then rates per pair. See the
     * note there — until this is false, the rates on screen are not the final ones.
     */
    // The cards' rolling returns are a load wave too (Y-40): `data-busy` holds until they are in.
    // The assets the cards compare are one too (Y-41).
    let busy = $derived(loading || periodChangesLoading || comparisonSeriesLoading > 0 || pairs.some((p) => p.loading) || [...calendarBySlug.values()].some((entry) => entry.own.state === 'loading'));
</script>

<div class="space-y-6 text-lf-primary" aria-busy={busy} data-busy={busy ? 'true' : 'false'} data-testid="fx-page">
    <!-- Header: Title left, ViewModeToggle + Add Pair right. Round 14.1 bugfix: `lg:` is a
         VIEWPORT breakpoint (1024px) — wraps unconditionally below that width regardless of
         whether the actual header row has room, the opposite of what "wrap only when space is
         short" means. Plain `flex-wrap` reacts to the row's OWN available width instead (same
         philosophy as PageToolbar's own container-driven tiers, just via native CSS here since
         no JS threshold tuning is needed for a simple 2-block header). -->
    <div class="flex flex-wrap items-start justify-between gap-4">
        <div use:guideAnchor={'fx.page.overview'} data-testid="fx-page-overview-guide-target">
            <h2 class="text-lg font-semibold text-lf-secondary flex items-center gap-2">
                {$_('fx.title')}
                {#if pairs.length > 0}
                    <span data-testid="fx-pair-count-badge" class="text-xs font-mono px-1.5 py-0.5 rounded-full bg-lf-selected text-lf-link">{pairs.length}</span>
                {/if}
            </h2>
            <p class="text-lf-muted text-sm">{$_('fx.subtitle')}</p>
        </div>
        <div class="flex flex-wrap items-center gap-2 justify-end ml-auto">
            {#if viewMode === 'list' && selectedFxRows.length > 0}
                <DataTableToolbar
                    selectedCount={selectedFxRows.length}
                    bulkActions={[
                        {id: 'sync', icon: RotateCw, label: () => $_('common.sync'), onClick: () => handleBulkSyncFx()},
                        {id: 'refresh', icon: RefreshCw, label: () => $_('common.refresh'), onClick: () => handleBulkRefreshFx()},
                        {id: 'invert', icon: ArrowLeftRight, label: () => $_('common.swapDirection'), onClick: () => handleBulkInvertFx()},
                        {id: 'delete', icon: Trash2, label: () => $_('common.delete'), variant: 'danger', onClick: () => handleBulkDeleteFx()},
                    ]}
                    onClearSelection={() => {
                        fxTableComponent?.getTableRef()?.clearSelection();
                        selectedFxRows = [];
                    }}
                />
            {/if}
            <ViewModeToggle bind:mode={viewMode} storageKey="fxViewMode" />
            <button class="flex items-center gap-1.5 px-3 py-2 text-sm bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover transition-colors whitespace-nowrap" data-testid="fx-add-pair-button" use:guideAnchor={'fx.page.add'} onclick={handleAddPair}>
                <Plus size={16} />
                {$_('fx.actions.addPair')}
            </button>
        </div>
    </div>

    <!-- Filter Bar — shared PageToolbar (same component as dashboard/broker-detail/assets),
         so responsive/wrap fixes made there auto-propagate here too.
         oneRow:       [ datepicker  currency ─── actions-2×2 ]  1 row, picker 1-row
         denseRow:     [ datepicker  currency ─── actions-2×2 ]  1 row, picker 2-row
         stackFilters: [ datepicker                     | 4×1  ]  filters+summary stacked,
                       [ currency-filters               | btns ]  actions stay BESIDE (4×1 column)
         oneColumn:    [ datepicker       ]  whole bar now ONE column — actions moved BELOW,
                       [ currency-filters ]  still a labeled 2×2 grid (only position changed)
                       [ actions ── 2×2   ]  (narrowest tier — Round 12 removed iconOnly) -->
    <PageToolbar thresholds={{oneRow: 1120, denseRow: 1030, stackFilters: 560, oneColumn: 400, labelHideActions: 260, labelHideTabs: 370}} testId="fx-controls" filterRowTestId="fx-filter-bar" layoutDebugName="fxList">
        {#snippet filters({layoutMode, filtersStacked})}
            <!-- DateRangePicker. Round 14 bugfix: `contents` (not `flex flex-1 ...`) — see
                 assets/+page.svelte's equivalent wrapper for the full explanation. -->
            <div class="contents" data-testid="fx-date-range-picker">
                <DateRangePicker bind:activePreset bind:end={dateEnd} bind:start={displayDateStart} compact={true} align="start" maxWidthTwoRow={420} {layoutMode} debugName="fxList" onchange={handleDateRangeChange} bind:effectiveMaxWidth={pickerMaxWidth} />
            </div>

            <!-- Currency Filters — always grouped as a pair. shrink-0: never wrapped/squeezed by
                 CSS — the DateRangePicker (above) is the only zone that gives up space when the
                 row is tight (it sheds jolly badges via its own verify+shed loop). Capped to
                 pickerMaxWidth so this row's right edge lines up with the picker's instead of
                 the wider column. Round 14: when filtersStacked, the 2 selects grow (flex-1)
                 to fill the capped width evenly instead of staying at their fixed w-28/w-40 and
                 leaving the extra space as empty justify-around gaps — wide components read
                 better than empty space between small fixed-width controls. -->
            <div class="flex items-center gap-3 shrink-0 {filtersStacked ? 'w-full justify-around' : ''}" style={filtersStacked && pickerMaxWidth ? `max-width: ${pickerMaxWidth}px` : ''} use:guideAnchor={'fx.page.filters'} data-testid="fx-page-filters">
                <div class={filtersStacked ? 'flex-1 min-w-0' : 'w-28 sm:w-40'} data-testid="fx-currency-filter">
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
                <div class="{filtersStacked ? 'flex-1 min-w-0' : 'w-28 sm:w-40'} transition-opacity {filterCurrency1 ? '' : 'opacity-50'}" data-testid="fx-currency-filter">
                    <CurrencySearchSelect allowedCurrencies={allowedForFilter2} bind:value={filterCurrency2} disabled={!filterCurrency1} includeAll={true} maxVisibleItems={6} placeholder={$_('fx.filter.secondCurrency')} />
                </div>
                <!-- Reset filters button -->
                <button
                    class="p-1.5 rounded-md transition-colors {filterCurrency1 ? 'hover:bg-lf-hover text-lf-muted hover:text-lf-danger' : 'text-lf-muted/50 cursor-not-allowed'}"
                    data-testid="fx-reset-filters"
                    disabled={!filterCurrency1}
                    onclick={() => {
                        filterCurrency1 = '';
                        filterCurrency2 = '';
                    }}
                    title={$_('fx.filter.resetFilters')}
                >
                    <X size={16} />
                </button>
            </div>
        {/snippet}

        {#snippet actions({showActionLabels})}
            <!-- Top-left: Abs/% toggle in grid mode, ColumnVisibility in table mode -->
            {#if viewMode === 'list'}
                <ColumnVisibilityToggle tableRef={fxTableComponent?.getTableRef()} showLabel={showActionLabels} />
            {:else}
                <!-- The cards' view (Y-40): absolute, percent, rolling return -->
                <div class="flex rounded-lg border border-lf-subtle overflow-hidden" data-testid="fx-global-view" data-view={globalPrimaryView}>
                    <button
                        class="flex-1 inline-flex items-center justify-center px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {globalPrimaryView === 'absolute' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
                        data-testid="fx-global-view-absolute"
                        aria-pressed={globalPrimaryView === 'absolute'}
                        aria-label={$_('chart.showAbsolute')}
                        title={$_('chart.showAbsolute')}
                        onclick={() => handleListPrimaryView('absolute')}
                    >
                        <ChartLine size={14} />
                    </button>
                    <button
                        class="flex-1 px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {globalPrimaryView === 'percentage' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
                        data-testid="fx-global-view-percentage"
                        aria-pressed={globalPrimaryView === 'percentage'}
                        onclick={() => handleListPrimaryView('percentage')}
                        >%
                    </button>
                    <button
                        class="flex-1 inline-flex items-center justify-center px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {globalPrimaryView === 'calendar-return' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
                        data-testid="fx-global-view-calendar-return"
                        aria-pressed={globalPrimaryView === 'calendar-return'}
                        aria-label={$_('signals.riskRollingReturn.name')}
                        title={$_('signals.riskRollingReturn.name')}
                        onclick={() => handleListPrimaryView('calendar-return')}
                    >
                        <CalendarSync size={14} />
                    </button>
                </div>
            {/if}
            <!-- Settings. The three buttons say what they do in a delayed tooltip (Y5-F1); a click is theirs, so it
                 stops before the tooltip's own click, which would pin the hint over the window it opens. -->
            <Tooltip text={$_('sharedResource.settingsHint')} position="bottom" interactiveChild testId="fx-chart-settings-tooltip">
                <button
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-lf-card border border-lf-subtle rounded-lg hover:bg-lf-hover text-lf-secondary transition-colors"
                    data-testid="fx-chart-settings-button"
                    onclick={(event) => {
                        event.stopPropagation();
                        handleGlobalSettings();
                    }}
                >
                    <Settings size={14} />
                    {#if showActionLabels}<span>{$_('sharedResource.settings')}</span>{/if}
                </button>
            </Tooltip>
            <!-- Sync All -->
            <Tooltip text={$_('sharedResource.syncAllHint')} position="bottom" interactiveChild testId="fx-sync-all-tooltip">
                <button
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-lf-card border border-lf-subtle rounded-lg hover:bg-lf-hover text-lf-secondary transition-colors"
                    data-testid="fx-sync-all-button"
                    use:guideAnchor={'fx.page.sync'}
                    onclick={(event) => {
                        event.stopPropagation();
                        handleSyncAll();
                    }}
                >
                    <RotateCw size={14} />
                    {#if showActionLabels}<span>{$_('sharedResource.syncAll')}</span>{/if}
                </button>
            </Tooltip>
            <!-- Refresh All -->
            <Tooltip text={$_('sharedResource.refreshAllHint')} position="bottom" interactiveChild testId="fx-refresh-tooltip">
                <button
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-lf-card border border-lf-subtle rounded-lg hover:bg-lf-hover text-lf-secondary transition-colors disabled:opacity-50"
                    data-testid="fx-refresh-all-button"
                    data-busy={pageBusy.busy ? 'true' : 'false'}
                    disabled={pageBusy.busy}
                    onclick={(event) => {
                        event.stopPropagation();
                        handleRefreshAll();
                    }}
                >
                    <RefreshCw class={pageBusy.busy ? 'animate-spin' : ''} size={14} />
                    {#if showActionLabels}<span>{$_('sharedResource.refreshAll')}</span>{/if}
                </button>
            </Tooltip>
        {/snippet}
    </PageToolbar>

    <!-- Content -->
    {#if loading}
        <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card p-12 text-center border border-lf-subtle">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-lf-selected rounded-full mb-4">
                <RefreshCw class="text-lf-link animate-spin" size={32} />
            </div>
            <p class="text-lf-muted">{$_('common.loading')}</p>
        </div>
    {:else if error}
        <div class="bg-lf-danger-soft border border-lf-danger-line rounded-xl p-6 text-center">
            <p class="text-lf-danger-on-soft">{error}</p>
            <button class="mt-3 px-4 py-2 text-sm bg-lf-danger-solid text-lf-on-danger-solid rounded-lg hover:bg-lf-danger-hover transition-colors" onclick={() => loadPairSources()}>
                {$_('common.retry')}
            </button>
        </div>
    {:else if filteredPairs.length === 0}
        <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card p-12 text-center border border-lf-subtle">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-amber-100 dark:bg-amber-900/30 rounded-full mb-4">
                <Coins class="text-amber-600 dark:text-amber-400" size={32} />
            </div>
            {#if pairs.length === 0}
                <h3 class="text-lg font-semibold text-lf-secondary mb-2">{$_('fx.empty.noPairsTitle')}</h3>
                <p class="text-lf-muted mb-4">{$_('fx.empty.noPairsDesc')}</p>
                <button class="px-4 py-2 bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover transition-colors" use:guideAnchor={'fx.add'} onclick={handleAddPair}>
                    <Plus size={16} class="inline mr-1" />
                    {$_('fx.empty.addFirstPair')}
                </button>
            {:else}
                <h3 class="text-lg font-semibold text-lf-secondary mb-2">{$_('common.noMatchesTitle')}</h3>
                <p class="text-lf-muted">{$_('fx.empty.noMatchesDesc')}</p>
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
                    rangeDeltas={rangeDeltas.get(`${pair.config.base}/${pair.config.quote}`) ?? null}
                    loading={pair.loading}
                    dateStart={urlDateStart}
                    dateEnd={urlDateEnd}
                    manualOnly={pair.config.providers.length === 1 && pair.config.providers[0].providerCode === 'MANUAL'}
                    primaryView={cardPrimaryView(pair.config.slug)}
                    onprimaryviewchange={handleCardPrimaryView}
                    calendarReturn={cardPrimaryView(pair.config.slug) === 'calendar-return' ? cardCalendarReturn(pair.config.slug) : undefined}
                    calendarOverlaySignals={cardPrimaryView(pair.config.slug) === 'calendar-return' ? cardCalendarOverlays(pair.config.slug) : []}
                    chartSettings={getSettingsForPair(pair.config.slug, 'fx')}
                    renderSignals={(chartData, vm) => getRenderedSignals(pair.config.slug, chartData, vm)}
                    ondelete={handleDeletePair}
                    onrefresh={handleRefreshPair}
                    onsync={handleSyncPair}
                    onsettings={handleCardSettings}
                    oninversionchange={({slug}) => {
                        void fetchAllPairSeries();
                        // The rolling return of a swapped pair is the swapped rate's.
                        if (cardPrimaryView(slug) === 'calendar-return') void fetchCalendarReturns(new Set([slug]));
                    }}
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
            dateStart={urlDateStart}
            dateEnd={urlDateEnd}
            onsync={handleSyncPair}
            onrefresh={handleRefreshPair}
            ondelete={handleDeletePair}
            oninversionchange={() => {
                void fetchAllPairSeries();
                // A pair swapped in the table: the cards in the rolling-return view read the swapped rate's return.
                void fetchCalendarReturns();
            }}
            onselectionchange={(rows) => {
                selectedFxRows = rows;
            }}
        />
    {/if}
</div>

<!-- Delete Confirm Dialog (single) -->
<ConfirmModal
    confirmText={$_('common.delete')}
    danger={true}
    description={$_('fx.deletePairWarning')}
    message={$_('fx.deletePairQuestion', {values: {pair: `${deletingPair?.base ?? ''}/${deletingPair?.quote ?? ''}`}})}
    onCancel={() => {
        deleteDialogOpen = false;
        deletingPair = null;
    }}
    onConfirm={confirmDelete}
    open={deleteDialogOpen}
    title={$_('fx.deletePairTitle')}
/>

<!-- Delete Confirm Dialog (bulk) -->
<ConfirmModal
    confirmText={$_('common.delete')}
    danger={true}
    description={$_('fx.deletePairWarning')}
    items={deletingPairs.map((p) => `${getCurrencyInfo(p.base).flag_emoji} ${p.base} / ${getCurrencyInfo(p.quote).flag_emoji} ${p.quote}`)}
    itemsLabel={`${deletingPairs.length} pairs`}
    message={$_('fx.deletePairQuestion', {values: {pair: `${deletingPairs.length} pairs`}})}
    onCancel={closeBulkFxDeleteDialog}
    onConfirm={confirmBulkDelete}
    open={bulkDeleteDialogOpen}
    results={bulkFxDeleteResults}
    title={$_('fx.deletePairTitle')}
/>

<!-- Add Pair Modal -->
<FxPairAddModal bind:open={addModalOpen} tourPreview={fxTourPreview} onclose={closeAddPair} oncreated={handlePairCreated} onsynced={handlePairCreationSynced} />

<!-- Sync Modal -->
<FxSyncModal bind:open={syncModalOpen} {dateEnd} dateStart={syncDateStart} onclose={() => (syncModalOpen = false)} onsynced={handleSynced} pairs={syncModalPairs} withDataInRange={syncModalWithData} />

<!-- Chart Settings Modal (global or per-card depending on settingsTargetSlug) -->
<ChartSettingsModal
    axisContext={settingsAxisContext}
    axisDomain="fx"
    availableAssets={availableAssetsList}
    availablePairs={pairs.map((p) => `${p.config.base}-${p.config.quote}`)}
    {signalDefinitions}
    {signalBackendError}
    onretrySignalBackend={retryBackendSignals}
    backendPreviewSignalResolver={settingsTargetSlug ? resolveSettingsBackendPreview : undefined}
    backendPreviewLiveResolver={resolveGlobalBackendPreview}
    open={settingsModalOpen}
    mode={settingsTargetSlug ? 'pair' : 'global'}
    onclose={() => {
        settingsModalOpen = false;
        settingsTargetSlug = null;
    }}
    onsave={handleSettingsSave}
    pairData={settingsTargetSlug
        ? pairs
              .find((p) => p.config.slug === settingsTargetSlug)
              ?.data?.map((d) => {
                  const inv = isCardInverted(settingsTargetSlug ?? '');
                  return fxPointToLineDataPoint(d, inv);
              })
        : undefined}
    signalSources={settingsSignalSources}
    settings={settingsForModal}
    calendarRangeDays={calendarReturnRangeDays(dateStart, dateEnd)}
    calendarPreviewResolver={resolveCalendarPreview}
/>
