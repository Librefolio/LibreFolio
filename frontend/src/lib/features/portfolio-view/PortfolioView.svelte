<!--
  PortfolioView — the body of the Dashboard and of a broker's page (Y6-7, deliveries 2 and 3).

  One page, two users, told apart by `scope`: `{kind: 'portfolio'}` (the user's own share of every broker they own, optionally
  filtered — the Dashboard) and `{kind: 'broker', brokerId}` (that one broker, counted whole, as the page of the broker is).
  What the two do not share — `data-testid`s, `pageBusy` keys, guide anchors, toolbar thresholds, the broker filter, the
  banner, what the Transactions tab follows — is `portfolioScopeProfile`; what is the broker's own (its header, the Info tab,
  the buttons that write, their modals) arrives as snippets from the page that mounts this one.

  Data: the report, the contribution and the candles are the data controller's (`createPortfolioData`); the toolbar, the banner
  and the four tabs are shared components of this folder.

  Pattern: Svelte 5 Runes, Tailwind CSS 4, dark mode, data-testid everywhere.
-->
<script lang="ts">
    import {onDestroy, onMount, untrack, type ComponentProps, type Snippet} from 'svelte';
    import {page} from '$app/stores';
    import {_} from '$lib/i18n';
    import type {AiExportRequestContext} from '$lib/features/ai-export/aiExportClipboard';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';

    import {invalidate, portfolioError} from '$lib/stores/portfolio/portfolioStore.svelte';
    import {brokerStoreVersion, ensureBrokersLoaded, getAllBrokers, getOwnedBrokers} from '$lib/stores/reference/brokerStore';
    import {registerPortfolioMutationListener, requestPortfolioRefresh} from '$lib/stores/portfolio/portfolioMutation';
    import {pageBusy} from '$lib/stores/app/pageBusy.svelte';
    import {createScopeReloadDebounce} from './scopeReloadDebounce';
    import {readDashboardView, writeDashboardView} from '$lib/features/dashboard/dashboardViewStore';
    import {setTweenHydration} from '$lib/components/ui/TweenedValue.svelte';
    import {ensureAssetsLoaded, getAssetInfo, assetStoreVersion} from '$lib/stores/reference/assetStore';
    import {getAssetPanelAssetId, buildAssetPanelUrl} from '$lib/utils/broker/assetPanelUrl';
    import {buildTabUrl, getResolvedTabParam} from '$lib/utils/url/tabUrl';
    import {defaultDisplayCurrency} from '$lib/stores/app/settings';
    import {createDateRangeController} from '$lib/features/dashboard/dateRangeController.svelte';
    import {calendarReturnWindowDays, type CalendarReturnWindowSelection} from '$lib/components/charts/calendarReturnWindow';
    import {rollingAutoPreset} from '$lib/features/dashboard/positionsRolling';
    import {createPortfolioData} from './portfolioData';
    import PortfolioToolbar from './PortfolioToolbar.svelte';
    import PortfolioBanners from './PortfolioBanners.svelte';
    import {PortfolioBannerActions} from './portfolioBannerActions.svelte';
    import PortfolioOverviewTab from './PortfolioOverviewTab.svelte';
    import PortfolioPositionsTab from './PortfolioPositionsTab.svelte';
    import PortfolioRiskTab from './PortfolioRiskTab.svelte';
    import PortfolioTransactionsTab from './PortfolioTransactionsTab.svelte';
    import {busyKey as profileBusyKey, DEFAULT_PORTFOLIO_TAB, portfolioScopeProfile, tabsForProfile, type PortfolioScopeTestIds, type PortfolioTabId, type PortfolioViewScope} from './portfolioScopeProfile';
    import type TransactionsTable from '$lib/features/transactions/TransactionsTable.svelte';
    import type {TXReadItem} from '$lib/features/transactions/types';
    import type {FilterValue} from '$lib/components/table/types';
    import {PortfolioTransactions} from './portfolioTransactions.svelte';
    import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';
    import {staleFxIssue, type StaleFxPairLike} from '$lib/features/dashboard/staleFxIssue';
    import {todayIso} from '$lib/utils/dateOnly';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import {goto} from '$app/navigation';

    interface TransactionsWriter {
        hideActions: boolean;
        onSelectionChange: (rows: TXReadItem[]) => void;
        onEditRow: (row: TXReadItem) => void;
        onCloneRow: (row: TXReadItem) => void;
        onDeleteRow: (row: TXReadItem) => void;
        onFiltersChange: (filters: Record<string, FilterValue>) => void;
        /** The rows and their partner legs are loaded: the bulk workspace reads the originals of a selected row from there (FB-17). */
        onLoaded: (mainRows: TXReadItem[], partnerRows: TXReadItem[]) => void;
    }

    interface Props {
        scope?: PortfolioViewScope;
        /** A broker's page: the broker, once the page has loaded it (null before). */
        broker?: BrokerLike | null;
        /** The page shows `gate` (its loading or its error) instead of the toolbar and the tabs: the report is asked all the same. */
        gated?: boolean;
        /** A broker's page: what it asks besides the report (its own broker summary) — held with the first load, asked again by Refresh and after a sync. */
        extraLoad?: () => Promise<unknown>;
        /** The first load (the page's and the report's) is over. */
        onFirstLoaded?: () => void;
        /** What stands above the toolbar: a broker's identity. */
        header?: Snippet;
        gate?: Snippet;
        /** The page's own buttons, first among the toolbar's actions (a broker's Edit and Share). */
        actionsBefore?: Snippet<[{showActionLabels: boolean}]>;
        /** The Info tab (a broker's only). */
        infoTab?: Snippet;
        /** Buttons above the Transactions table, and the table's own callbacks, for a page that writes. */
        transactionsBar?: Snippet<[{table: TransactionsTable | undefined; period: {start: string | undefined; end: string | undefined}}]>;
        transactionsWriter?: TransactionsWriter;
        transactionsTable?: TransactionsTable | undefined;
    }

    let {scope = {kind: 'portfolio'}, broker = null, gated = false, extraLoad, onFirstLoaded, header, gate, actionsBefore, infoTab, transactionsBar, transactionsWriter, transactionsTable = $bindable()}: Props = $props();

    // A page keeps its scope for its whole life (a broker's page remounts for another broker).
    const profile = portfolioScopeProfile(untrack(() => scope));
    const brokerScopeId = untrack(() => (scope.kind === 'broker' ? scope.brokerId : null));
    const isBrokerScope = brokerScopeId !== null;
    const testIds: PortfolioScopeTestIds = profile.testIds;
    const busy = (name: string) => profileBusyKey(profile, name);

    // =========================================================================
    // State
    // =========================================================================

    // The window of the positions chart's Rolling view (F-2): null until the user picks one, which is the automatic window of the period.
    let rollingSelection = $state<CalendarReturnWindowSelection | null>(null);

    // The report, the contribution and the candles of the scope on screen, and the way they are asked, are the
    // portfolio data controller's (Y6-7): this page gives it its scope and reads what it shows. A store, so that
    // `$data` is followed by the lazy loaders' wrappers below.
    const data = createPortfolioData({
        scope: () => ({brokerIds: activeBrokerIds, start: dateRangeCtl.historyStart, end: dateRangeCtl.end || undefined, currency: targetCurrency, fullShare: profile.fullShare}),
        canAsk: () => canAsk,
        brokersKnown: () => brokersReady,
        // A broker's page asks its report at once and waits for the broker only for the per-position chart.
        positionsReady: () => (isBrokerScope ? broker !== null : canAsk),
        alive: () => pageAlive,
        wantsBrokerPnlHistory: () => wantsBrokerPnlHistory,
        rollingPeriod: () => ({start: dateRangeCtl.start, end: dateRangeCtl.end || undefined}),
        rollingWindow: () => (rollingSelection ? (calendarReturnWindowDays(rollingSelection) ?? undefined) : undefined),
        onFirstDay: (day) => dateRangeCtl.markMaxResolved(day),
        onRefreshFailed: () => toasts.error(`${$_('common.refresh')} — ${escapeHtml(portfolioError() ?? $_('common.error'))}`),
        failureMessage: () => $_('common.error'),
        initialLoading: true,
    });
    const summary = $derived($data.summary);
    const history = $derived($data.history);
    const contributionLoading = $derived($data.contributionLoading);
    /** A contribution already on screen is being refreshed in background: busy, but no skeleton. */
    const contributionRefreshing = $derived($data.contributionRefreshing);
    const reportLoading = $derived($data.reportLoading);
    /** «Aggiorna» is running (the banner's own syncs are `banners.syncLoading`). */
    let refreshing = $state(false);

    /** The currency and broker filter the user left (E3): they last the session, so a return asks
     *  the key it left and the cache can serve it. */
    const restoredView = isBrokerScope ? {brokerIds: [] as number[], targetCurrency: null} : readDashboardView();
    /** The owned brokers, when the broker list is already in memory (any in-app return): the restored
     *  scope can then be read from the cache before the first render. On a cold load the list arrives
     *  in onMount, and nothing is asked before it (F2). */
    const knownOwnedBrokers: BrokerLike[] | null = !isBrokerScope && getAllBrokers().length > 0 ? getOwnedBrokers() : null;

    /** Broker IDs selected in the filter (empty = all brokers). */
    let selectedBrokerIds = $state<number[]>(knownOwnedBrokers ? restoredView.brokerIds.filter((id) => knownOwnedBrokers.some((broker) => broker.id === id)) : restoredView.brokerIds);
    let allBrokers = $state<BrokerLike[]>(knownOwnedBrokers ?? []);
    /** F2: the owned brokers are known. Until then nothing is asked: a request without them would be
     *  widened by the backend to every broker the user can see, viewer and editor ones included. */
    let brokersReady = $state(isBrokerScope || knownOwnedBrokers !== null);
    /** Bumped by «Aggiorna»: the risk levels and the lots panel ask again too (E4). */
    let refreshVersion = $state(0);

    /** FIFO lots analysis panel (Posizioni tab) — mirrors brokers/[id]/+page.svelte's pattern
     *  but in runes syntax (this file is Svelte 5 runes throughout, unlike the legacy broker
     *  detail page). Scope defaults to ALL accessible brokers when no broker filter is active
     *  (activeBrokerIds undefined = "All Brokers"), so the panel analyzes the same asset across
     *  every broker that holds it — see plan_ui_broker_holdings.md multi-broker evolution. */
    let activeAssetId = $state<number | null>(getAssetPanelAssetId($page.url.searchParams) ?? null);
    $effect(() => {
        const paramAssetId = getAssetPanelAssetId($page.url.searchParams) ?? null;
        if (paramAssetId !== activeAssetId) activeAssetId = paramAssetId;
    });

    /** Reactive asset info for the open panel. Reading `$assetStoreVersion` re-evaluates once the async
     * asset cache resolves, so on a hard reload (F5) the title/currency fill in when the store loads
     * instead of staying stale (getAssetInfo alone is not reactive to the cache). */
    const activeAsset = $derived.by(() => {
        void $assetStoreVersion;
        return activeAssetId != null ? getAssetInfo(activeAssetId) : undefined;
    });

    /** Whether the lot detail on screen was opened by a step of this page (not by a reload on its URL): going back then undoes it. */
    let assetPanelOpenedHere = false;

    // The lot detail opens below the positions (#48, FB-12b): opening it is a step of the browser's history, so «back»
    // (or the panel's ✕) closes it.
    function openAssetPanel(assetId: number) {
        assetPanelOpenedHere = true;
        void goto(buildAssetPanelUrl($page.url, assetId), {noScroll: true});
    }

    function closeAssetPanel() {
        if (assetPanelOpenedHere) {
            assetPanelOpenedHere = false;
            window.history.back();
            return;
        }
        void goto(buildAssetPanelUrl($page.url, null), {replaceState: true, noScroll: true});
    }

    /** Debounce timer for broker filter changes. */

    /**
     * Date range — backed by global store (shared with assets/fx pages) via the
     * shared dateRangeController (owns the seed/display/isMaxPending bookkeeping
     * that used to be duplicated per-page — see dateRangeController.svelte.ts).
     */
    const dateRangeCtl = createDateRangeController(() => void pageBusy.track(busy('period'), () => loadAll()));
    // The preset the automatic window is, for the controls to show it picked: the same period the request is asked for.
    const rollingAutoPresetKey = $derived(rollingAutoPreset(dateRangeCtl.start, dateRangeCtl.end || ''));

    /**
     * Sentinel-aware values for building "See all" links (assets/transactions).
     * While "All" is the active selection, these stay "min"/"max" (generic)
     * instead of a concrete resolved date, for the lifetime of the selection.
     */
    let urlDateFrom = $derived(dateRangeCtl.activePreset === 'MAX' ? 'min' : dateRangeCtl.start);
    let urlDateTo = $derived(dateRangeCtl.activePreset === 'MAX' ? 'max' : dateRangeCtl.end);

    /** Display currency override — always concrete, defaults to user base currency (or the one the user left). */
    const initialCurrency = restoredView.targetCurrency ?? $defaultDisplayCurrency;
    let targetCurrency = $state(initialCurrency);
    /** The currency of the figures on screen: the one the last answer was asked in (the one the user left, before the first). */
    const appliedCurrency = $derived($data.appliedCurrency ?? initialCurrency);
    let targetCurrencyManuallySet = $state(restoredView.targetCurrency !== null);

    // =========================================================================
    // Derived
    // =========================================================================

    const baseCurrency = $derived($defaultDisplayCurrency);

    $effect(() => {
        if (targetCurrencyManuallySet || targetCurrency === baseCurrency) return;
        const hadLoadedData = summary !== null || history.length > 0;
        targetCurrency = baseCurrency;
        // Guard: don't stack a second overlapping loadAll() if one triggered by onMount
        // (or a prior currency change) is still in flight — avoids duplicate concurrent
        // fetches racing to reassign summary/history while the user may be interacting
        // with the page (e.g. clicking a card whose click depends on stable DOM state).
        if (hadLoadedData && !reportLoading) void pageBusy.track(busy('currency'), () => loadAll(true));
    });

    /**
     * True when the selection covers all brokers — treated same as "no filter"
     * so that selecting all is equivalent to deselecting all.
     */
    const allBrokersSelected = $derived(selectedBrokerIds.length > 0 && selectedBrokerIds.length >= allBrokers.length);

    /** Owned broker IDs (F2: the dashboard only aggregates brokers the user owns,
     *  scaled by share; a 0% share behaves like editor/viewer and is excluded). */
    const ownedBrokerIds = $derived(isBrokerScope ? [brokerScopeId] : allBrokers.map((b) => b.id));

    /** F2: a request may leave only with an explicit owned scope. Without one the backend would
     *  widen it to every broker the user can see; a user who owns nothing is asked nothing. */
    const canAsk = $derived(brokersReady && ownedBrokerIds.length > 0);

    /** The brokers the panels name: the one of a broker's page, the owned ones on the Dashboard. */
    const panelBrokers = $derived<BrokerLike[]>(isBrokerScope ? (broker ? [broker] : []) : allBrokers);
    /** The brokers the Transactions table names: a broker's page also names the other leg's broker of a paired transaction. */
    const transactionsBrokers = $derived.by<BrokerLike[]>(() => {
        if (!isBrokerScope) return allBrokers;
        void $brokerStoreVersion;
        return getAllBrokers();
    });

    /** Which broker IDs to pass to the API — always the explicit owned set, so the
     *  backend never falls back to "every accessible broker" for the dashboard. */
    const activeBrokerIds = $derived(!allBrokersSelected && selectedBrokerIds.length > 0 ? selectedBrokerIds : ownedBrokerIds.length > 0 ? ownedBrokerIds : undefined);

    /** GrowthChart P&L broker overlay (G1a) caller policy per plan §4.1: request
     *  broker_pnl_history only when the effective scope has ≥2 brokers — a single
     *  broker's line would be identical to the total and the payload is unneeded. */
    const effectiveBrokerCount = $derived((activeBrokerIds ?? ownedBrokerIds).length);
    const wantsBrokerPnlHistory = $derived(effectiveBrokerCount >= 2);

    /** Whether the filter is "active" (some but not all brokers selected). */
    const brokerFilterActive = $derived(selectedBrokerIds.length > 0 && !allBrokersSelected);

    // The report's own issues, plus one row for the exchange rates it read from an old stored row (`stale_fx_pairs`): the
    // report lists them but raises no issue, so the row is built here (developer question 18, 28/10).
    const dataQualityIssues = $derived.by<DataQualityIssue[]>(() => {
        const quality = summary?.data_quality as {issues?: DataQualityIssue[]; stale_fx_pairs?: StaleFxPairLike[]} | undefined;
        const staleFx = staleFxIssue(quality?.stale_fx_pairs, todayIso());
        return [...(quality?.issues ?? []), ...(staleFx ? [staleFx] : [])];
    });

    /** Tab navigation: the profile lists the tabs (a broker's has «Info» too). */
    const TAB_IDS = profile.tabs.map((tab) => tab.id);

    function isTabId(tabId: string): tabId is PortfolioTabId {
        return (TAB_IDS as string[]).includes(tabId);
    }

    // Read at init too, so a return to another tab does not first mount the overview and tear it down.
    let activeTab = $state<PortfolioTabId>(getResolvedTabParam($page.url.searchParams, TAB_IDS, DEFAULT_PORTFOLIO_TAB));
    const tabLabels: Record<PortfolioTabId, () => string> = {
        panoramica: () => $_('brokers.overview'),
        posizioni: () => $_('brokers.positions'),
        rischio: () => $_('risk.title'),
        transazioni: () => $_('transactions.title'),
        info: () => $_('brokers.info'),
    };
    const viewTabs = $derived(tabsForProfile(profile, (id) => tabLabels[id]()));

    $effect(() => {
        activeTab = getResolvedTabParam($page.url.searchParams, TAB_IDS, DEFAULT_PORTFOLIO_TAB);
    });

    function handleTabChange(tabId: string) {
        if (!isTabId(tabId)) return;
        activeTab = tabId;
        void goto(buildTabUrl($page.url, tabId), {replaceState: true, noScroll: true});
    }

    let pageAlive = true;
    onDestroy(() => {
        pageAlive = false;
        scopeReload.dispose();
        data.dispose();
    });

    /** The Transazioni tab's rows: kept here, not in the tab, so leaving the tab and coming back asks nothing again. */
    const txCtl = new PortfolioTransactions({
        ownedBrokerIds: () => ownedBrokerIds,
        brokerIds: () => activeBrokerIds,
        period: () => ({historyStart: dateRangeCtl.historyStart, start: dateRangeCtl.start, end: dateRangeCtl.end, isMaxPending: dateRangeCtl.isMaxPending}),
        busyKey: busy('transactions'),
        onLoaded: (mainRows, partnerRows) => transactionsWriter?.onLoaded(mainRows, partnerRows),
    });
    $effect(() => {
        txCtl.sync(activeTab === 'transazioni');
    });

    /** The banner's buttons (sync rates, sync prices, the chips) and the pair dialog, which the currency selector opens too. */
    const banners = new PortfolioBannerActions({
        issues: () => dataQualityIssues,
        staleFxPairs: () => (summary?.data_quality as {stale_fx_pairs?: StaleFxPairLike[]} | undefined)?.stale_fx_pairs,
        periodEnd: () => dateRangeCtl.end,
        alive: () => pageAlive,
        busyKey: busy('reload'),
        reload: (force, propagateError) => loadAll(force, propagateError),
        onDataChanged: () => (refreshVersion += 1),
        translate: (key, options) => $_(key, options as never),
    });

    /** URL of the «See all» link of the positions: it keeps the date range on screen. */
    const assetsHref = $derived(`/assets?start=${urlDateFrom}&end=${urlDateTo}`);
    // =========================================================================
    // Loaders
    // =========================================================================

    /** The main report of the scope on screen, from the cache at once and asked again when stale (E1); see the controller. */
    function loadAll(force = false, propagateError = false, options: {background?: boolean} = {}) {
        return data.loadAll(force, propagateError, options);
    }

    function hydrateFromCache() {
        data.hydrateFromCache();
    }

    /**
     * The contribution of the scope on screen: asked by PositionsPanel when its Performance view has none, and by `loadAll`
     * when the cached one is stale. The flags are read here through `$data`, so the panel's effect that calls this wakes when
     * a request ends (the controller's own reads of its store register nothing).
     */
    function loadContribution(options: {background?: boolean} = {}) {
        void [$data.contributionLoading, $data.contributionRefreshing];
        return data.loadContribution(options);
    }

    /** Lazy-load the synthetic P&L candle series (G1b), called by GrowthChart when the user first activates the candles submode.
     *  `$data` is read here for GrowthChart's effect to depend on: the candles on screen and the request on its way
     *  (Y-16: `canAsk` turning true asks again once the brokers are known; Y-24: the retry falls due). */
    function loadPnlCandles() {
        void [$data.pnlCandles, $data.pnlCandlesLoading];
        return data.loadPnlCandles();
    }

    /**
     * The per-position return chart (Y5-2): the lines of the positions the user ticked, asked for the scope on screen —
     * its brokers, period and currency — and asked again when the scope or `refreshVersion` moves. Its Rolling view (FB-15)
     * follows the same period.
     */
    $effect(() => {
        data.syncPositions(refreshVersion);
    });
    const positionsSeriesCtl = data.positionsSeries;
    const positionsRollingCtl = data.positionsRolling;

    // =========================================================================
    // Event handlers
    // =========================================================================

    function selectBrokers(ids: number[]) {
        selectedBrokerIds = ids;
        writeDashboardView({brokerIds: ids});
        scheduleReload();
    }

    /** Fires loadAll after a 2-second quiet period (anti-bounce for rapid clicks); the page is busy for the whole wait (K-18). */
    const scopeReload = createScopeReloadDebounce({delayMs: 2000, waitLabel: busy('scope-pending'), reloadLabel: busy('scope'), reload: () => loadAll()});
    const scheduleReload = () => scopeReload.schedule();

    /** «Aggiorna» (E4): report, contribution, risk and lots are all asked again; what is on screen stays meanwhile. A broker's page asks its own summary and, once its Transactions were opened, their rows too. */
    export async function refresh() {
        await handleSync();
    }

    async function handleSync() {
        refreshing = true;
        // The user's Refresh: the lazy sections may be asked again whatever failed before (Y-24).
        data.resetRetries();
        requestPortfolioRefresh();
        refreshVersion += 1;
        try {
            await pageBusy.track(busy('refresh'), async () => {
                await Promise.all([extraLoad?.(), loadAll(true)]);
                await txCtl.reload();
            });
        } finally {
            refreshing = false;
        }
    }

    /**
     * The server caught up on prices and updated something (Z5, Z-13): the stale report is asked again in background,
     * without force, and the figures stay until the new ones land. `refreshVersion` and `requestPortfolioRefresh()` are
     * the user's Refresh (Y11): the risk and lots panels keep their stale answers until they next load. Nor does the
     * page say it is busy (Z-18): a screen reader would announce «busy» for a simple price refresh. Run after the
     * dispatch, so every store has marked its answers stale first.
     */
    function reloadAfterPriceCatchUp() {
        if (!pageAlive) return;
        void loadAll(false, false, {background: true});
    }
    onMount(() =>
        registerPortfolioMutationListener(`${busy('view')}:${brokerScopeId ?? 'all'}:prices`, (signal) => {
            if (signal.kind === 'prices') queueMicrotask(reloadAfterPriceCatchUp);
        }),
    );

    /** The toolbar's AI Export: which export it is, and the request's context (the broker filter and period on screen). */
    const aiExport = {
        ...profile.aiExport,
        get disabled() {
            return isBrokerScope ? broker?.id !== brokerScopeId : !canAsk;
        },
        context: (): AiExportRequestContext => {
            if (isBrokerScope) {
                if (!broker || broker.id !== brokerScopeId) throw new Error('Broker is not loaded');
                return {domain: 'broker', brokerId: broker.id, snapshotAsOf: dateRangeCtl.end, targetCurrency};
            }
            // F2: a portfolio export without the owned scope would be widened by the backend to every
            // broker the user can see. The trigger is disabled until then; this guards the call itself.
            if (!canAsk) throw new Error('Owned brokers are not loaded');
            return {domain: 'portfolio', snapshotAsOf: dateRangeCtl.end, targetCurrency, brokerIds: activeBrokerIds};
        },
    } as ComponentProps<typeof PortfolioToolbar>['aiExport'];

    /** The user picked a currency in the toolbar. */
    function handleCurrencyChange() {
        targetCurrencyManuallySet = true;
        if (!isBrokerScope) writeDashboardView({targetCurrency});
        void pageBusy.track(busy('currency'), () => loadAll());
    }

    /** The risk panel synced prices or rates: the report is asked again, and a broker's page asks its summary too. */
    async function handleRiskSynced() {
        invalidate();
        await Promise.all([extraLoad?.(), loadAll(true)]);
    }

    // =========================================================================
    // Lifecycle
    // =========================================================================

    // Figures already known when a card mounts — served from the cache on a return, or kept from an
    // earlier load on a tab switch — appear at their value instead of counting up from 0. The Risk
    // panel sets its own context for its cards, which come from the risk cache, not from this report.
    setTweenHydration(() => summary !== null);
    hydrateFromCache();

    onMount(() => {
        void (async () => {
            // The first load holds the Refresh button (Y11), from the reference lists to the report.
            await pageBusy.track(busy('first-load'), async () => {
                if (isBrokerScope) {
                    // A broker's page asks its report at once, beside its own broker and the two lists.
                    await Promise.all([extraLoad?.(), loadAll(), ensureBrokersLoaded(), ensureAssetsLoaded()]);
                    return;
                }
                await Promise.all([ensureBrokersLoaded(), ensureAssetsLoaded()]);
                if (!pageAlive) return;
                // F2: dashboard scope = owned brokers only (share > 0). A user who owns
                // nothing (viewer/editor elsewhere, or fresh install) gets an empty
                // dashboard — no fetch, so viewer/editor data never leaks into totals.
                allBrokers = getOwnedBrokers();
                const kept = selectedBrokerIds.filter((id) => allBrokers.some((broker) => broker.id === id));
                if (kept.length !== selectedBrokerIds.length) {
                    selectedBrokerIds = kept;
                    writeDashboardView({brokerIds: kept});
                }
                brokersReady = true;
                // A user who owns nothing is asked nothing: `loadAll` only stops the page from being busy.
                await loadAll();
            });
            if (pageAlive) onFirstLoaded?.();
        })();
    });
</script>

<div
    class="{profile.rootSpacing} text-lf-primary"
    data-testid={testIds.root}
    use:guideAnchor={profile.rootGuideAnchor ?? []}
    aria-busy={reportLoading || contributionLoading || contributionRefreshing || refreshing || banners.syncLoading}
    data-busy={reportLoading || contributionLoading || contributionRefreshing || refreshing || banners.syncLoading ? 'true' : 'false'}
    data-live-updates={$data.liveState}
>
    {#if isBrokerScope}
        {@render header?.()}
    {:else}
        <h1 class="sr-only">{$_('nav.dashboard')}</h1>
    {/if}

    {#if gated}
        {@render gate?.()}
    {:else}
        <PortfolioToolbar
            {profile}
            tabs={viewTabs}
            {activeTab}
            ontabchange={handleTabChange}
            {dateRangeCtl}
            bind:targetCurrency
            {baseCurrency}
            oncurrencychange={handleCurrencyChange}
            oncreateforex={(slug) => banners.openFxPairModal(slug)}
            brokers={allBrokers}
            {selectedBrokerIds}
            {brokerFilterActive}
            onselectbrokers={selectBrokers}
            liveState={$data.liveState}
            {aiExport}
            onrefresh={handleSync}
            {actionsBefore}
        />

        <!-- The banner is shown to every role, a viewer's included: its buttons sync shared prices and rates, not the broker. -->
        <PortfolioBanners issues={dataQualityIssues} actions={banners} />

        {#if activeTab === 'panoramica'}
            <PortfolioOverviewTab snapshot={$data} displayCurrency={appliedCurrency} brokerIds={activeBrokerIds} {testIds} onRequestPnlCandles={() => void pageBusy.join(busy('pnl-candles'), loadPnlCandles)} />
        {:else if activeTab === 'posizioni'}
            <PortfolioPositionsTab
                testId={testIds.positionsTab}
                snapshot={$data}
                brokers={panelBrokers}
                brokerIds={activeBrokerIds}
                {canAsk}
                {assetsHref}
                onRequestContribution={canAsk ? () => void pageBusy.join(busy('contribution'), loadContribution) : undefined}
                positionsSeries={$positionsSeriesCtl.response}
                positionsSeriesLoading={$positionsSeriesCtl.loading}
                positionsSeriesFailed={$positionsSeriesCtl.failed}
                onRequestPositionsSeries={(keys) => positionsSeriesCtl.request(keys, data.positionsSeriesScope(refreshVersion))}
                positionsRolling={$positionsRollingCtl}
                onRequestPositionsRolling={(assetIds) => positionsRollingCtl.request(assetIds, data.positionsRollingScope(refreshVersion))}
                {rollingSelection}
                rollingAutoPreset={rollingAutoPresetKey}
                onRollingSelectionChange={(selection) => (rollingSelection = selection)}
                {activeAssetId}
                {activeAsset}
                displayCurrency={appliedCurrency}
                onAnalyze={openAssetPanel}
                onCloseAnalysis={closeAssetPanel}
                {refreshVersion}
            />
        {:else if activeTab === 'rischio'}
            <PortfolioRiskTab
                testId={testIds.riskTab}
                broker={isBrokerScope ? {id: brokerScopeId} : undefined}
                {canAsk}
                {brokersReady}
                {ownedBrokerIds}
                dateStart={dateRangeCtl.start}
                dateEnd={dateRangeCtl.end}
                targetCurrency={appliedCurrency}
                {summary}
                {brokerFilterActive}
                {refreshVersion}
                onsynced={handleRiskSynced}
            />
        {:else if activeTab === 'transazioni'}
            <PortfolioTransactionsTab
                transactions={txCtl}
                brokers={transactionsBrokers}
                testId={testIds.transactionsTab}
                tableTestId={isBrokerScope ? 'broker-transactions' : undefined}
                bind:table={transactionsTable}
                bar={transactionsBar}
                period={{start: dateRangeCtl.isMaxPending ? undefined : dateRangeCtl.start, end: dateRangeCtl.end || undefined}}
                hideActions={transactionsWriter?.hideActions ?? true}
                onSelectionChange={transactionsWriter?.onSelectionChange}
                onEditRow={transactionsWriter?.onEditRow}
                onCloneRow={transactionsWriter?.onCloneRow}
                onDeleteRow={transactionsWriter?.onDeleteRow}
                onFiltersChange={transactionsWriter?.onFiltersChange}
            />
        {:else if activeTab === 'info'}
            {@render infoTab?.()}
        {/if}
    {/if}
</div>
