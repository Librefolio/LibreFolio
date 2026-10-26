<script lang="ts">
    /**
     * Broker Detail Page — header + overview/positions/transactions tabs
     */
    import {get} from 'svelte/store';
    import {onDestroy, onMount} from 'svelte';
    import {page} from '$app/stores';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {goBack} from '$lib/stores/app/navigationStore';
    import {defaultDisplayCurrency} from '$lib/stores/app/settings';
    import {currentLanguage} from '$lib/stores/app/language';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import {getEnd, getStart, isMaxSentinel, resolveDateSentinel, setDateRange} from '$lib/stores/dateRangeStore.svelte';
    import {todayIso} from '$lib/utils/dateOnly';
    import {ArrowLeft, ArrowRightLeft, Briefcase, Crown, ExternalLink, Eye, FileText, Info, Pencil, Plus, RefreshCw, Share2, Shield, TrendingUp, Upload, Users, Wallet} from 'lucide-svelte';
    import BrokerModal from '$lib/features/brokers/BrokerModal.svelte';
    import BrokerIcon from '$lib/components/ui/display/BrokerIcon.svelte';
    import BrokerImportFilesModal from '$lib/features/brokers/BrokerImportFilesModal.svelte';
    import BrokerSharingPanel from '$lib/features/brokers/BrokerSharingPanel.svelte';
    import LotsAnalysisPanel from '$lib/features/brokers/lots/LotsAnalysisPanel.svelte';
    import KpiSection from '$lib/features/dashboard/KpiSection.svelte';
    import AllocationPanel from '$lib/features/dashboard/AllocationPanel.svelte';
    import GrowthChart from '$lib/features/dashboard/GrowthChart.svelte';
    import PositionsPanel from '$lib/features/dashboard/PositionsPanel.svelte';
    import {createPositionsSeriesController, type PositionsSeriesScope} from '$lib/features/dashboard/positionsSeriesController';
    import RiskLevelsPanel from '$lib/features/risk/levels/RiskLevelsPanel.svelte';
    import DateRangePicker from '$lib/components/ui/date/DateRangePicker.svelte';
    import PageToolbar from '$lib/components/ui/toolbar/PageToolbar.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import TransactionFormModal from '$lib/features/transactions/form/TransactionFormModal.svelte';
    import TransactionsTable from '$lib/features/transactions/TransactionsTable.svelte';
    import TransactionBulkModal from '$lib/features/transactions/bulk/TransactionBulkModal.svelte';
    import {resolveFormItemsForView, type FormModalItems} from '$lib/features/transactions/resolveFormItems';
    import {loadPartnerRows, loadEventTooltipMap} from '$lib/features/transactions/loadTransactionRows';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import type {TXReadItem, AssetEvent} from '$lib/features/transactions/types';
    import type {FilterValue} from '$lib/components/table/types';
    import {buildTransactionsFiltersUrl, applyTransactionColumnFilters} from '../../transactions/filterState';
    import {
        fetchReport,
        invalidate,
        peekReport,
        portfolioError,
        type PortfolioReport,
        type AllocationHistoryDimensions,
        type PortfolioHistoryPoint,
        type PortfolioRange,
        type PortfolioMwrrLinePoint,
        type PortfolioSummary,
        type PositionsContribution,
        type PortfolioIncomeHistorySeries,
        type PortfolioCostHistorySeries,
        type PortfolioDepositHistorySeries,
        type PortfolioAcquisitionFundingSeries,
        type PortfolioPnlCandleSeries,
    } from '$lib/stores/portfolio/portfolioStore.svelte';
    import {ensureBrokersLoaded, getAllBrokers, getBrokerRole, brokerStoreVersion} from '$lib/stores/reference/brokerStore';
    import {ensureAssetsLoaded, getAssetInfo, assetStoreVersion} from '$lib/stores/reference/assetStore';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import {onboardingGuide} from '$lib/features/onboarding/onboardingGuide.svelte';
    import {getAssetPanelAssetId, buildAssetPanelUrl} from '$lib/utils/broker/assetPanelUrl';
    import {buildTabUrl, getResolvedTabParam} from '$lib/utils/url/tabUrl';
    import {goto} from '$app/navigation';
    import type {BrokerSummary} from '$lib/types';
    import {parseCurrencyAmount, safeCurrency, safeString} from '$lib/types';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import CurrencyAmount from '$lib/components/ui/display/CurrencyAmount.svelte';
    import AiExportMenu from '$lib/features/ai-export/AiExportMenu.svelte';
    import {prepareAiExport, type PreparedAiExport} from '$lib/features/ai-export/aiExportClipboard';
    import type {AiExportOptionsSelection} from '$lib/features/ai-export/aiExportOptions';
    import {aiExportCatalogLoader, emptyAiExportCompatibility, type AiExportCatalogCompatibilityResult} from '$lib/features/ai-export/catalog/compatibility';
    import {buildAiExportMenuLabels, getAiExportErrorMessage, getAiExportSuccessMessages} from '$lib/features/ai-export/ui';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {registerPortfolioMutationListener, requestPortfolioRefresh} from '$lib/stores/portfolio/portfolioMutation';
    import {createLazyReportRetry} from '$lib/stores/portfolio/lazyReportRetry.svelte';
    import {pageBusy} from '$lib/stores/app/pageBusy.svelte';
    import {setTweenHydration} from '$lib/components/ui/TweenedValue.svelte';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {uiLocaleStore} from '$lib/stores/app/uiLocale';

    const DISABLED_AI_EXPORT_COMPATIBILITY = emptyAiExportCompatibility();

    export let data: {brokerId: number};

    let broker: BrokerSummary | null = null;
    let loading = true;
    let reportLoading = true;
    let error: string | null = null;

    let portfolioSummary: PortfolioSummary | null = null;
    let portfolioHistory: PortfolioHistoryPoint[] = [];
    /** The days the report's step series cover, and the history's MWRR as true points (D-P4). */
    let reportRange: PortfolioRange | null = null;
    let mwrrLine: PortfolioMwrrLinePoint[] = [];
    let incomeHistory: PortfolioIncomeHistorySeries | undefined = undefined;
    let costHistory: PortfolioCostHistorySeries | undefined = undefined;
    let depositHistory: PortfolioDepositHistorySeries | undefined = undefined;
    let acquisitionFunding: PortfolioAcquisitionFundingSeries | undefined = undefined;
    // G1b — lazy, unlike the income family above: the OHLC composition is expensive, so it
    // is fetched only when the user first opens the candles submode (plan §4.1 caller policy).
    let pnlCandles: PortfolioPnlCandleSeries | null = null;
    let pnlCandlesLoading = false;
    let allocationHistoryFromReport: AllocationHistoryDimensions | null = null;
    let positionsContribution: PositionsContribution | null = null;
    let contributionLoading = false;
    // Y-24: a failed candles or contribution request is asked again at most three times, 2, 4 and 8 s later, then not
    // until the scope changes or the user's Refresh (`handleRefresh`). Before, the contribution was asked again at
    // once, without end, and the candles never again.
    const candlesRetry = createLazyReportRetry();
    const contributionRetry = createLazyReportRetry();
    // The per-position return chart (Y5-2): the lines of the positions ticked, asked for this broker, period and currency,
    // and asked again when one of them or `refreshVersion` moves.
    const positionsSeriesCtl = createPositionsSeriesController();
    onDestroy(() => {
        candlesRetry.dispose();
        contributionRetry.dispose();
        positionsSeriesCtl.dispose();
    });
    // The candles' loading flag must be a signal, as on the Dashboard: the loader's guard reads it inside GrowthChart's
    // effect, which has to wake when a request ends — to ask for the scope on screen once an old scope's answer was
    // dropped, or to wait for the retry after a failure (Y-24). The legacy compiler makes a `let` a signal only when a
    // reactive statement or the template reads it.
    $: void pnlCandlesLoading;
    let positionsSeriesScope: PositionsSeriesScope;
    $: positionsSeriesScope = {brokerIds: [data.brokerId], start: dateFrom || undefined, end: dateTo || undefined, currency: targetCurrency || baseCurrency, ready: broker !== null, version: refreshVersion};
    $: positionsSeriesCtl.sync(positionsSeriesScope);

    /** The scope of a lazy report section: this broker, the period and the currency. An answer of another scope is not applied, and a failure counts for its own scope only (Y-24). */
    function reportScope(): string {
        return `${data.brokerId}|${dateFrom}|${dateTo}|${targetCurrency}`;
    }

    let editModalOpen = false;
    let importFilesModalOpen = false;
    let txViewOpen = false;
    let txViewItems: FormModalItems | null = null;

    /** Bulk workspace (create / import) — same engine as /transactions, pre-populated
     *  with this page's broker (still editable, never skips a step). */
    let bulkOpen = false;
    let bulkIntent: import('$lib/features/transactions/bulk/TransactionBulkModal.svelte').WorkspaceIntent | undefined = undefined;

    function openImportTransactions() {
        bulkIntent = {action: 'import'};
        bulkOpen = true;
    }

    function openNewTransaction() {
        bulkIntent = {action: 'create'};
        bulkOpen = true;
    }

    /** AI export state — dropdown open/position handled internally by AiExportMenu. */
    let aiExportCompatibility: AiExportCatalogCompatibilityResult = DISABLED_AI_EXPORT_COMPATIBILITY;
    let aiExportCatalogLoading = true;
    let aiExportCatalogFailed = false;
    let aiExportLabels = buildAiExportMenuLabels($_, aiExportCompatibility, $_('dashboard.aiExport'));

    // Transactions tab — full paginated history (not just "recent 10").
    let txMainRows: TXReadItem[] = [];
    let txPartnerRows: TXReadItem[] = [];
    let txEventTooltipMap: Map<number, AssetEvent> = new Map();
    let txLoading = false;
    let txLoaded = false;
    let txCurrentPage = 1;
    let txPageSize = 50;
    let txTableComponent: TransactionsTable | undefined;
    let txColumnFilters: Record<string, FilterValue> = {};

    /** Deep-link to the full Transactions page pre-filtered by this broker plus
     *  whatever header column filters are currently active in the embedded table.
     *  The broker-detail transactions tab loads by broker only (it ignores the
     *  toolbar date range), so only broker + column filters are carried over.
     *  Navigating via a plain link registers on the nav stack, so browser Back
     *  returns to this exact broker view (see navigationStore.goBack). */
    $: transactionsPageUrl = broker ? buildTransactionsFiltersUrl({...(applyTransactionColumnFilters({}, txColumnFilters) ?? {}), broker_id: broker.id}) : '/transactions';

    const BROKER_TAB_IDS = ['panoramica', 'posizioni', 'rischio', 'transazioni', 'info'] as const;
    type BrokerTabId = (typeof BROKER_TAB_IDS)[number];
    const DEFAULT_BROKER_TAB: BrokerTabId = 'panoramica';

    function isBrokerTabId(tabId: string): tabId is BrokerTabId {
        return BROKER_TAB_IDS.includes(tabId as BrokerTabId);
    }

    let activeTab: BrokerTabId = DEFAULT_BROKER_TAB;
    let brokerTabs = [];
    let panelBrokers: BrokerLike[] = [];
    let allBrokersForTable: BrokerLike[] = [];
    $: allBrokersForTable = ($brokerStoreVersion, getAllBrokers());
    let sharingHasChanges = false; // bound from BrokerSharingPanel (Info tab), for future use (e.g. unsaved-changes guard)

    /** FIFO lots analysis panel (Posizioni tab) — state mirrors `?asset=<id>` in the URL so it's
     *  bookmarkable/shareable and survives browser back/forward (see plan_ui_broker_holdings.md
     *  §1ter/§2). Opened by a single click on a row/tile/bar via PositionsPanel's onAnalyze;
     *  double-click still navigates to asset detail, unchanged. */
    let activeAssetId: number | null = null;
    $: {
        const paramAssetId = getAssetPanelAssetId($page.url.searchParams);
        if ((paramAssetId ?? null) !== activeAssetId) activeAssetId = paramAssetId ?? null;
    }
    $: activeTab = getResolvedTabParam($page.url.searchParams, BROKER_TAB_IDS, DEFAULT_BROKER_TAB);

    /** Reactive asset info for the open panel. Depending on `$assetStoreVersion` re-evaluates once the
     *  async asset cache resolves, so on a hard reload (F5) the title/currency fill in instead of
     *  staying stale (getAssetInfo alone is not reactive to the cache). */
    $: activeAsset = activeAssetId != null && $assetStoreVersion != null ? getAssetInfo(activeAssetId) : undefined;

    function openAssetPanel(assetId: number) {
        void goto(buildAssetPanelUrl($page.url, assetId), {replaceState: true, noScroll: true});
    }

    function closeAssetPanel() {
        void goto(buildAssetPanelUrl($page.url, null), {replaceState: true, noScroll: true});
    }

    function handleTabChange(tabId: string) {
        if (!isBrokerTabId(tabId)) return;
        activeTab = tabId;
        void goto(buildTabUrl($page.url, tabId), {replaceState: true, noScroll: true});
    }

    const initialStart = getStart();
    const initialEnd = getEnd();
    let isMaxPending = isMaxSentinel(initialStart);
    let dateFrom = resolveDateSentinel(initialStart);
    let dateTo = resolveDateSentinel(initialEnd);
    let displayDateFrom = isMaxPending ? 'min' : dateFrom;
    let activePreset: any = isMaxPending ? 'MAX' : null;

    let targetCurrency = get(defaultDisplayCurrency);
    let targetCurrencyManuallySet = false;

    let canEdit = false;
    $: canEdit = broker ? ['OWNER', 'EDITOR'].includes(safeString(broker.user_role) || '') : false;

    /** Mirrors the DateRangePicker's own effective 2-row max-width, so the single-item Center
     *  row below it can be capped to the SAME pixel value when filtersStacked. MUST start
     *  non-undefined (matches DateRangePicker's own maxWidthTwoRow default, 390) — Svelte
     *  forbids bind:key={undefined} when the child prop has a declared fallback. */
    let pickerMaxWidth: number = 390;
    $: panelBrokers = broker
        ? [
              {
                  id: broker.id,
                  name: broker.name,
                  icon_url: safeString(broker.icon_url),
                  portal_url: safeString(broker.portal_url),
                  default_import_plugin: safeString(broker.default_import_plugin),
              },
          ]
        : [];

    let baseCurrency = 'EUR';
    $: baseCurrency = $defaultDisplayCurrency;
    $: if (!targetCurrencyManuallySet && targetCurrency !== baseCurrency) {
        const hadLoadedData = portfolioSummary !== null || portfolioHistory.length > 0;
        targetCurrency = baseCurrency;
        // Guard with !reportLoading: see brokers/+page.svelte for the race this avoids.
        if (hadLoadedData && !reportLoading) void pageBusy.track('broker-currency', () => loadOverview(true));
    }

    $: aiExportLabels = buildAiExportMenuLabels($_, aiExportCompatibility, $_('dashboard.aiExport'));

    $: brokerTabs = [
        {id: 'panoramica', label: $_('brokers.overview'), icon: Briefcase, testId: 'broker-tab-panoramica', guideAnchor: 'broker.detail.overview'},
        {id: 'posizioni', label: $_('brokers.positions'), icon: TrendingUp, testId: 'broker-tab-posizioni', guideAnchor: 'broker.detail.positions'},
        {id: 'rischio', label: $_('risk.title'), icon: Shield, testId: 'broker-tab-risk'},
        {id: 'transazioni', label: $_('transactions.title'), icon: ArrowRightLeft, testId: 'broker-tab-transazioni', guideAnchor: 'broker.detail.transactions'},
        {id: 'info', label: $_('brokers.info'), icon: Info, testId: 'broker-tab-info', guideAnchor: 'broker.detail.info'},
    ];

    async function loadAiExportCompatibility() {
        aiExportCatalogLoading = true;
        try {
            aiExportCompatibility = await aiExportCatalogLoader.load();
            aiExportCatalogFailed = false;
        } catch {
            aiExportCatalogFailed = true;
            toasts.error($_('aiExport.catalogUnavailable'));
        } finally {
            aiExportCatalogLoading = false;
        }
    }

    function handleAiExport(options: AiExportOptionsSelection): Promise<PreparedAiExport> {
        const loadedBroker = broker;
        if (!loadedBroker || loadedBroker.id !== data.brokerId) return Promise.reject(new Error('Broker is not loaded'));
        return prepareAiExport({
            context: {
                domain: 'broker',
                brokerId: loadedBroker.id,
                snapshotAsOf: dateTo,
                targetCurrency,
            },
            options,
            compatibility: aiExportCompatibility,
            translate: (key) => $_(key),
        });
    }

    function handleAiExportCopied(result: PreparedAiExport) {
        const messages = getAiExportSuccessMessages($_, result);
        toasts.success(messages.copied);
        toasts.info(messages.privacyNotice);
    }

    onMount(async () => {
        void loadAiExportCompatibility();
        // The first load holds the page's Refresh button (Y11).
        await pageBusy.track('broker-first-load', () => Promise.all([loadBroker(), loadOverview(), ensureBrokersLoaded(), ensureAssetsLoaded()]));
        if (broker) onboardingGuide.maybeStartContextual('broker_detail_guide');
    });

    async function loadBroker() {
        loading = true;
        error = null;

        try {
            // The cash and holdings of the user's today: a transaction dated later counts in none of them (W-B5)
            broker = (await zodiosApi.get_broker_summary_api_v1_brokers__broker_id__summary_get({params: {broker_id: data.brokerId}, queries: {as_of: todayIso()}})) as BrokerSummary;
        } catch (e) {
            console.error('Failed to load broker:', e);
            error = $_('brokers.loadFailed');
        } finally {
            loading = false;
        }
    }

    /** Bumped by «Aggiorna»: the risk levels and the lots panel ask again too (E4). */
    let refreshVersion = 0;
    // Figures already known when a card mounts appear at their value instead of counting up from 0;
    // the Risk panel sets its own context for its cards.
    setTweenHydration(() => portfolioSummary !== null);

    /**
     * Page cache (E1): the overview of the scope on screen comes from the cache at once — stale or
     * not — and only a stale or missing one is asked again; a refresh that fails keeps it, with a toast.
     */
    async function loadOverview(force = false) {
        const options = {includeIncomeHistory: true, includeCostHistory: true, includeDepositHistory: true, includeAcquisitionFunding: true};
        const cached = peekReport([data.brokerId], dateFrom || undefined, dateTo || undefined, targetCurrency, false, false, true, true, options);
        if (cached) applyOverview(cached.report);
        if (cached && !cached.stale && !force) {
            reportLoading = false;
            return;
        }
        reportLoading = true;
        try {
            const report = await fetchReport([data.brokerId], dateFrom || undefined, dateTo || undefined, targetCurrency, force, undefined, undefined, undefined, undefined, options);
            if (report || !cached) applyOverview(report);
            else toasts.error(`${$_('common.refresh')} — ${escapeHtml(portfolioError() ?? $_('common.error'))}`);
        } finally {
            reportLoading = false;
        }
    }

    function applyOverview(report: PortfolioReport | null) {
        portfolioSummary = (report?.summary as PortfolioSummary | null | undefined) ?? null;
        portfolioHistory = (report?.history as PortfolioHistoryPoint[] | null | undefined) ?? [];
        reportRange = (report?.range as PortfolioRange | null | undefined) ?? null;
        mwrrLine = (report?.mwrr_line as PortfolioMwrrLinePoint[] | null | undefined) ?? [];
        // Eager per plan §4.1's sparse-payload caller policy ("Dashboard/Broker overview true").
        incomeHistory = (report?.income_history as PortfolioIncomeHistorySeries | null | undefined) ?? undefined;
        costHistory = (report?.cost_history as PortfolioCostHistorySeries | null | undefined) ?? undefined;
        depositHistory = (report?.deposit_history as PortfolioDepositHistorySeries | null | undefined) ?? undefined;
        acquisitionFunding = (report?.acquisition_funding as PortfolioAcquisitionFundingSeries | null | undefined) ?? undefined;
        allocationHistoryFromReport = (report?.allocation_history as AllocationHistoryDimensions | null | undefined) ?? null;
        positionsContribution = (report?.positions_contribution as PositionsContribution | null | undefined) ?? null;
        // Scope, currency or date range may have changed, so any previously fetched
        // candle series is stale. Nulling it lets GrowthChart ask again on its next
        // candles activation instead of rendering the old window's OHLC.
        pnlCandles = null;
        resolveMaxStartFromHistory();
    }

    /**
     * G1b lazy candle fetch, scoped to THIS broker.
     *
     * Deliberately not the Dashboard's loader: that one requests the currently selected
     * portfolio scope, so reusing it here would paint whole-portfolio OHLC under a single
     * broker's heading — a wrong number, which is worse than the empty plot this replaces
     * because an empty plot is visible and a wrong number is not.
     *
     * `brokerPnlHistory` stays unpassed on purpose: plan §3.3 says "one broker or Broker
     * detail: total candle only", and the per-broker overlay is exactly what must not appear.
     */
    async function loadPnlCandles() {
        // Read before the first await, and `canAsk` before the other guards: GrowthChart's effect depends on all of them,
        // so a request ending or a retry falling due wakes it (Y-24).
        const askedScope = reportScope();
        const allowed = candlesRetry.canAsk(askedScope);
        if (pnlCandles || pnlCandlesLoading || !allowed) return;
        pnlCandlesLoading = true;
        try {
            // Only pnl_candles is read, so every other section is switched off.
            const report = await fetchReport([data.brokerId], dateFrom || undefined, dateTo || undefined, targetCurrency, false, false, false, false, false, {includePnlCandles: true});
            // An answer of another scope is not this one's: the scope on screen asks for its own.
            if (reportScope() !== askedScope) return;
            if (report) candlesRetry.succeeded(askedScope);
            else candlesRetry.failed(askedScope);
            pnlCandles = (report?.pnl_candles as PortfolioPnlCandleSeries | null | undefined) ?? null;
        } finally {
            pnlCandlesLoading = false;
        }
    }

    async function loadContribution() {
        const askedScope = reportScope();
        const allowed = contributionRetry.canAsk(askedScope);
        if (!broker || positionsContribution || contributionLoading || !allowed) return;
        contributionLoading = true;
        try {
            // includeHistory/includeAllocationHistory=false: only positions_contribution is read below.
            const report = await fetchReport([broker.id], dateFrom || undefined, dateTo || undefined, targetCurrency, false, true, false, false, false);
            if (reportScope() !== askedScope) return;
            // The outcome is recorded before `finally` lets the flag go: the effect it wakes reads it (Y-24).
            if (report) contributionRetry.succeeded(askedScope);
            else contributionRetry.failed(askedScope);
            positionsContribution = (report?.positions_contribution as PositionsContribution | null | undefined) ?? null;
        } finally {
            contributionLoading = false;
        }
    }

    /** Full transaction history for this broker, paginated client-side by
     *  `<TransactionsTable>` — loaded lazily on first visit to the
     *  Transazioni tab (not upfront, since a prolific broker could have a
     *  large history). The broker filter is applied server-side (immediate,
     *  in the query itself) — `loadPartnerRows`/`loadEventTooltipMap` are
     *  shared helpers (not internal to `TransactionsTable`, which is a pure
     *  presentational component and never fetches on its own): they cover
     *  paired transactions (e.g. FX conversion, transfer) whose other leg
     *  sits on a different broker and would otherwise be missing from this
     *  broker-filtered set. */
    async function loadTransactions(force = false) {
        if (!broker || (txLoaded && !force)) return;
        txLoading = true;
        try {
            const main = (await zodiosApi.query_transactions_api_v1_transactions_get({queries: {broker_id: broker.id}})) as TXReadItem[];
            txMainRows = main ?? [];
            const [partner, tooltipMap] = await Promise.all([loadPartnerRows(txMainRows), loadEventTooltipMap(txMainRows)]);
            txPartnerRows = partner;
            txEventTooltipMap = tooltipMap;
            txLoaded = true;
        } catch (e) {
            console.error('Failed to load transactions:', e);
        } finally {
            txLoading = false;
        }
    }

    // Lazy-load the full transaction history the first time the Transazioni tab is opened.
    $: if (activeTab === 'transazioni' && broker && !txLoaded && !txLoading) {
        void pageBusy.track('broker-transactions', () => loadTransactions());
    }

    function resolveMaxStartFromHistory() {
        if (!isMaxPending || portfolioHistory.length === 0) return;
        dateFrom = portfolioHistory[0].date;
        displayDateFrom = dateFrom;
        isMaxPending = false;
    }

    function handleBack() {
        goBack('/brokers');
    }

    function handleEdit() {
        editModalOpen = true;
    }

    function handleDateChange(from: string, to: string) {
        isMaxPending = isMaxSentinel(from);
        dateFrom = resolveDateSentinel(from);
        dateTo = resolveDateSentinel(to);
        displayDateFrom = isMaxPending ? 'min' : dateFrom;
        setDateRange(from, to);
        void pageBusy.track('broker-period', () => loadOverview());
    }

    async function handleRefresh() {
        // The user's Refresh: the lazy sections may be asked again whatever failed before (Y-24).
        candlesRetry.reset();
        contributionRetry.reset();
        requestPortfolioRefresh();
        refreshVersion += 1;
        await pageBusy.track('broker-refresh', async () => {
            await Promise.all([loadBroker(), loadOverview(true)]);
            if (txLoaded) await loadTransactions(true);
        });
    }

    /**
     * The server caught up on prices and updated something (Z5, Z-13): the stale overview is asked again in
     * background, without force, and the figures stay until the new ones land. `refreshVersion` and
     * `requestPortfolioRefresh()` are the user's Refresh (Y11): the risk and lots panels keep their stale answers until
     * they next load. Run after the dispatch, so every store has marked its answers stale first.
     */
    function reloadAfterPriceCatchUp() {
        void loadOverview();
    }
    onMount(() =>
        registerPortfolioMutationListener(`broker-page:${data.brokerId}:prices`, (signal) => {
            if (signal.kind === 'prices') queueMicrotask(reloadAfterPriceCatchUp);
        }),
    );

    async function handleUpdated() {
        await pageBusy.track('broker-reload', loadBroker);
    }

    async function handleRequestAllocationHistory() {
        await pageBusy.track('broker-allocation-history', () => loadOverview());
    }

    // In the interface locale (M-18): the template passes `$uiLocaleStore`, read there so it is tracked.
    function formatDate(dateStr: unknown, locale: string): string {
        const str = safeString(dateStr);
        if (!str) return '-';
        return new Date(str).toLocaleDateString(locale, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
    }

    function toNumber(value: number | string | (string | null)[] | null | undefined): number {
        if (Array.isArray(value)) return value[0] ? Number(value[0]) : 0;
        if (typeof value === 'number') return value;
        if (typeof value === 'string') return Number(value);
        return 0;
    }

    function formatSharePercentage(value: number | string | (string | null)[] | null | undefined, locale: string): string {
        return formatPercent(Math.round(toNumber(value) * 10000) / 100, {signed: false, digits: 1, locale});
    }
</script>

<div class="space-y-6 text-lf-primary" data-testid="broker-detail-page">
    <div class="flex items-center space-x-4" use:guideAnchor={'broker.detail.header'} data-testid="broker-detail-header">
        <button class="p-2 text-lf-muted hover:text-lf-link hover:bg-lf-selected rounded-lg transition-colors" data-testid="broker-back-button" on:click={handleBack} title={$_('common.back')}>
            <ArrowLeft size={20} />
        </button>

        {#if broker}
            <BrokerIcon brokerId={broker.id} iconUrl={safeString(broker.icon_url)} portalUrl={safeString(broker.portal_url)} pluginCode={safeString(broker.default_import_plugin)} altText={broker.name} size="lg" />

            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                    {#if safeString(broker.user_role)}
                        {@const role = safeString(broker.user_role)}
                        <!-- colour: closest role, to review: broker role badge (owner amber, editor blue, viewer grey) on warning, info and neutral tints -->
                        <span
                            class="inline-flex items-center gap-1 px-2 py-1 rounded-full flex-shrink-0
                            {role === 'OWNER' ? 'bg-lf-warning-soft text-lf-warning-on-soft' : role === 'EDITOR' ? 'bg-lf-info-soft text-lf-info-on-soft' : 'bg-lf-neutral text-lf-secondary'}"
                            title={$_(role === 'OWNER' ? 'brokers.sharing.roleOwnerShort' : role === 'EDITOR' ? 'brokers.sharing.roleEditorShort' : 'brokers.sharing.roleViewerShort')}
                            data-testid="broker-quota-badge"
                        >
                            {#if broker.user_share_percentage != null}
                                <span class="text-xs font-medium">{formatSharePercentage(broker.user_share_percentage, $uiLocaleStore)}</span>
                            {/if}
                            {#if role === 'OWNER'}<Crown size={13} />{:else if role === 'EDITOR'}<Pencil size={13} />{:else}<Eye size={13} />{/if}
                        </span>
                    {/if}
                    <h1 class="text-2xl font-bold text-lf-primary truncate" data-testid="broker-name">{broker.name}</h1>
                </div>
                {#if broker.description}
                    <p class="text-lf-muted text-sm truncate" data-testid="broker-description">{broker.description}</p>
                {/if}
            </div>

            {#if safeString(broker.portal_url)}
                <a href={safeString(broker.portal_url)} target="_blank" rel="noopener noreferrer" class="flex items-center justify-center p-2 text-lf-muted hover:text-lf-link hover:bg-lf-selected rounded-lg transition-colors flex-shrink-0" title={$_('brokers.openPortal')}>
                    <ExternalLink size={20} />
                </a>
            {/if}
        {:else if !error}
            <div class="flex-1">
                <div class="h-8 w-48 bg-lf-neutral rounded animate-pulse"></div>
            </div>
        {/if}
    </div>

    {#if loading && !broker}
        <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card p-12 text-center border border-lf-subtle">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-lf-selected rounded-full mb-4">
                <RefreshCw class="text-lf-link animate-spin" size={32} />
            </div>
            <p class="text-lf-muted">{$_('common.loading')}</p>
        </div>
    {:else if error}
        <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card p-12 text-center border border-lf-danger-line">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-lf-danger-soft rounded-full mb-4">
                <Briefcase class="text-lf-danger" size={32} />
            </div>
            <h3 class="text-lg font-semibold text-lf-secondary mb-2">{$_('common.error')}</h3>
            <p class="text-lf-muted mb-4">{error}</p>
            <button on:click={handleRefresh} class="px-4 py-2 bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover transition-colors">
                {$_('common.retry')}
            </button>
        </div>
    {:else if broker}
        <!-- Page-global controls: date range + currency + tabs — persist across ALL tabs
             (previously the date-range picker only rendered inside the Panoramica tab's
             content, so it disappeared on Posizioni/Transazioni even though those tabs
             depend on the same date-scoped data). -->
        <PageToolbar
            thresholds={{oneRow: 1000, denseRow: 840, stackFilters: 530, oneColumn: 430, labelHideActions: 270, labelHideTabs: 660}}
            tabs={brokerTabs}
            {activeTab}
            ontabchange={handleTabChange}
            testId="broker-controls"
            filterRowTestId="broker-overview-controls"
            layoutDebugName="brokerDetail"
        >
            {#snippet filters({layoutMode, filtersStacked})}
                <DateRangePicker bind:activePreset bind:start={displayDateFrom} bind:end={dateTo} compact={true} align="start" maxWidthTwoRow={470} {layoutMode} debugName="brokerDetail" onchange={handleDateChange} bind:effectiveMaxWidth={pickerMaxWidth} />

                <!-- Single-item row — no second control to spread against, so just center it
                     once it's stretched to the DateRangePicker's width (stackFilters/oneColumn —
                     see filtersStacked in PageToolbar). Un-stretched otherwise, this
                     justify-around is a no-op (natural content width, already centered visually
                     by the parent's items-center in row mode) — same visual result as
                     justify-center for a single item, kept as justify-around for consistency:
                     it's the standard justification for every capped Centro row (Round 13),
                     regardless of how many elements it holds. Capped to pickerMaxWidth so this
                     row's right edge lines up with the picker's instead of the wider column.
                     Round 13 bugfix: label + selector MUST share one wrapper div — they're a
                     single semantic unit ("Valuta: [selector]"), not two independent items to
                     spread apart. Without the wrapper, justify-around treats them as 2 separate
                     flex children and splits them apart with a wide gap in between (same mistake
                     dashboard's equivalent row never had — compare its currency-override block). -->
                <div class="flex items-center justify-around gap-1.5 text-xs text-lf-muted {filtersStacked ? 'w-full' : ''}" style={filtersStacked && pickerMaxWidth ? `max-width: ${pickerMaxWidth}px` : ''}>
                    <div class="flex items-center gap-1.5">
                        <span class="whitespace-nowrap">{$_('common.currency')}:</span>
                        <div class="w-28">
                            <CurrencySearchSelect
                                bind:value={targetCurrency}
                                compact={true}
                                testId="broker-detail-target-currency"
                                dropdownPosition="bottom"
                                placeholder={baseCurrency}
                                onchange={() => {
                                    targetCurrencyManuallySet = true;
                                    void pageBusy.track('broker-currency', () => loadOverview());
                                }}
                            />
                        </div>
                    </div>
                </div>
            {/snippet}

            {#snippet actions({showActionLabels})}
                {#if canEdit}
                    <button on:click={handleEdit} class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-lf-card border border-lf-subtle rounded-lg hover:bg-lf-hover text-lf-secondary transition-colors" data-testid="broker-edit-button">
                        <Pencil size={14} />
                        {#if showActionLabels}<span>{$_('common.edit')}</span>{/if}
                    </button>
                {/if}
                <button
                    on:click={() => handleTabChange('info')}
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-lf-card border border-lf-subtle rounded-lg hover:bg-lf-hover text-lf-secondary transition-colors"
                    data-testid="broker-share-button"
                    title={$_('brokers.sharing.title')}
                >
                    <Share2 size={14} />
                    {#if showActionLabels}<span>{$_('brokers.sharing.title')}</span>{/if}
                </button>
                <button
                    on:click={handleRefresh}
                    disabled={pageBusy.busy}
                    data-busy={pageBusy.busy ? 'true' : 'false'}
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-lf-card border border-lf-subtle rounded-lg hover:bg-lf-hover text-lf-secondary transition-colors disabled:opacity-50"
                    title={$_('dashboard.syncData')}
                    data-testid="broker-refresh"
                >
                    <RefreshCw size={14} class={pageBusy.busy ? 'animate-spin' : ''} />
                    {#if showActionLabels}<span>{$_('dashboard.syncData')}</span>{/if}
                </button>

                <AiExportMenu
                    domain="broker"
                    compatibility={aiExportCompatibility}
                    memoryKey={`broker:${data.brokerId}`}
                    defaultSelectionId="broker.review"
                    disabled={aiExportCatalogLoading || aiExportCatalogFailed || broker?.id !== data.brokerId}
                    labels={aiExportLabels}
                    showLabel={showActionLabels}
                    onprepare={handleAiExport}
                    oncopied={handleAiExportCopied}
                    onerror={(error) => toasts.error(getAiExportErrorMessage($_, error))}
                />
            {/snippet}
        </PageToolbar>

        {#if activeTab === 'panoramica'}
            <div class="space-y-4" data-testid="broker-overview-tab">
                <KpiSection summary={portfolioSummary} history={portfolioHistory} loading={reportLoading && !portfolioSummary} displayCurrency={targetCurrency || baseCurrency} />

                <!-- Cash Balances — moved up right below the KPIs so the "economic position"
                     (NAV + Gain/Loss + Cash by currency) is visible together at a glance. -->
                <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-subtle p-4" data-testid="broker-cash-balances">
                    <div class="flex items-center space-x-2 text-lf-secondary mb-4">
                        <Wallet size={20} />
                        <h2 class="font-semibold">{$_('brokers.cashBalances')}</h2>
                    </div>

                    {#if broker.cash_balances && broker.cash_balances.length > 0}
                        <div class="flex flex-wrap gap-2">
                            {#each [...broker.cash_balances].sort((a, b) => parseCurrencyAmount(b.amount) - parseCurrencyAmount(a.amount)) as balance}
                                <span class="inline-flex items-center px-3 py-1.5 bg-lf-panel rounded-lg text-sm font-medium text-lf-primary">
                                    <CurrencyAmount amount={parseCurrencyAmount(balance.amount)} code={balance.code} />
                                </span>
                            {/each}
                        </div>
                    {:else}
                        <p class="text-lf-muted text-sm italic py-4 text-center">{$_('brokers.noCashBalances')}</p>
                    {/if}
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-5 gap-4">
                    <div class="lg:col-span-3">
                        <GrowthChart
                            history={portfolioHistory}
                            range={reportRange}
                            {mwrrLine}
                            {pnlCandles}
                            onRequestPnlCandles={() => void pageBusy.join('broker-pnl-candles', loadPnlCandles)}
                            {incomeHistory}
                            {costHistory}
                            {depositHistory}
                            {acquisitionFunding}
                            loading={reportLoading && portfolioHistory.length === 0}
                            baseCurrency={targetCurrency || baseCurrency}
                        />
                    </div>
                    <AllocationPanel
                        summary={portfolioSummary}
                        loading={reportLoading && !portfolioSummary}
                        displayCurrency={targetCurrency || baseCurrency}
                        brokerIds={[broker.id]}
                        currentLanguage={$currentLanguage}
                        allocationHistory={allocationHistoryFromReport}
                        onRequestAllocationHistory={handleRequestAllocationHistory}
                    />
                </div>
            </div>
        {:else if activeTab === 'posizioni'}
            <div data-testid="broker-holdings">
                <PositionsPanel
                    summary={portfolioSummary}
                    contribution={positionsContribution}
                    loading={reportLoading && !portfolioSummary}
                    {contributionLoading}
                    assetsHref="/assets"
                    brokers={panelBrokers}
                    onRequestContribution={() => void pageBusy.join('broker-contribution', loadContribution)}
                    onAnalyze={openAssetPanel}
                    analyzedAssetId={activeAssetId}
                    {portfolioHistory}
                    positionsSeries={$positionsSeriesCtl.response}
                    positionsSeriesLoading={$positionsSeriesCtl.loading}
                    positionsSeriesFailed={$positionsSeriesCtl.failed}
                    onRequestPositionsSeries={(keys) => positionsSeriesCtl.request(keys, positionsSeriesScope)}
                />
                <LotsAnalysisPanel open={activeAssetId != null} assetId={activeAssetId} brokerIds={[broker.id]} brokers={panelBrokers} currency={activeAsset?.currency ?? baseCurrency} assetName={activeAsset?.display_name ?? null} onClose={closeAssetPanel} {refreshVersion} />
            </div>
        {:else if activeTab === 'rischio'}
            <div data-testid="broker-risk-tab">
                <!-- Same component as Dashboard, same props, one different scope:
                     that is the whole difference, and it is what makes the two
                     pages comparable. `portfolioSummary` here is fetched for this
                     broker alone, so its net worth answers this exact scope. -->
                <RiskLevelsPanel
                    scope={{kind: 'portfolio', broker_ids: [broker.id]}}
                    dateStart={dateFrom}
                    dateEnd={dateTo}
                    targetCurrency={targetCurrency || baseCurrency}
                    assetIds={[...new Set((portfolioSummary?.holdings ?? []).map((holding) => holding.asset_id))]}
                    scopeValue={portfolioSummary ? parseFloat(portfolioSummary.net_worth.amount) : null}
                    title={$_('risk.brokerTitle')}
                    internalSubset={true}
                    {refreshVersion}
                    onsynced={async () => {
                        invalidate();
                        await Promise.all([loadBroker(), loadOverview(true)]);
                    }}
                />
            </div>
        {:else if activeTab === 'transazioni'}
            <div class="space-y-4" data-testid="broker-transactions-tab">
                <div class="flex flex-wrap items-center justify-between gap-2" data-testid="broker-transactions-actions">
                    <div class="flex items-center gap-2">
                        <button class="flex items-center justify-center gap-1 px-2.5 py-1.5 text-xs bg-lf-panel text-lf-secondary rounded-lg hover:bg-lf-neutral transition-all" on:click={() => (importFilesModalOpen = true)} data-testid="broker-show-import-history">
                            <FileText size={15} />
                            <span class="hidden sm:inline">{$_('brokers.showImportHistory')}</span>
                        </button>
                        <a href={transactionsPageUrl} class="flex items-center justify-center gap-1 px-2.5 py-1.5 text-xs bg-lf-panel text-lf-secondary rounded-lg hover:bg-lf-neutral transition-all" title={$_('brokers.viewInTransactionsHint')} data-testid="broker-view-in-transactions">
                            <ArrowRightLeft size={15} />
                            <span class="hidden sm:inline">{$_('brokers.viewInTransactions')}</span>
                        </a>
                    </div>
                    <div class="flex items-center gap-2">
                        <ColumnVisibilityToggle tableRef={txTableComponent?.getTableRef()} />
                        {#if canEdit}
                            <button class="flex items-center justify-center gap-1 px-2.5 py-1.5 text-xs bg-lf-panel text-lf-secondary rounded-lg hover:bg-lf-neutral transition-all" on:click={openImportTransactions} data-testid="broker-import-transactions">
                                <Upload size={15} />
                                <span class="hidden sm:inline">{$_('common.import')}</span>
                            </button>
                            <button class="flex items-center justify-center gap-1 px-2.5 py-1.5 text-xs bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover transition-all" on:click={openNewTransaction} data-testid="broker-new-transaction">
                                <Plus size={15} />
                                <span class="hidden sm:inline">{$_('transactions.addTransaction')}</span>
                            </button>
                        {/if}
                    </div>
                </div>

                <div data-testid="broker-transactions">
                    {#if txLoading && !txLoaded}
                        <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-subtle p-12 text-center">
                            <RefreshCw class="text-lf-link animate-spin mx-auto" size={28} />
                        </div>
                    {:else}
                        <TransactionsTable
                            bind:this={txTableComponent}
                            mainRows={txMainRows}
                            partnerRows={txPartnerRows}
                            brokers={allBrokersForTable}
                            eventTooltipMap={txEventTooltipMap}
                            currentPage={txCurrentPage}
                            pageSize={txPageSize}
                            hideActions={true}
                            onFiltersChange={(f) => (txColumnFilters = f)}
                            onPageChange={(page) => (txCurrentPage = page)}
                            onPageSizeChange={(size) => {
                                txPageSize = size;
                                txCurrentPage = 1;
                            }}
                            onViewRow={(row) => {
                                txViewItems = resolveFormItemsForView(row as TXReadItem, () => undefined, getBrokerRole);
                                txViewOpen = true;
                            }}
                        />
                    {/if}
                </div>
            </div>
        {:else if activeTab === 'info'}
            <div class="grid grid-cols-1 xl:grid-cols-2 gap-4" data-testid="broker-info-tab">
                <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-subtle p-4" data-testid="broker-metadata">
                    <h3 class="font-semibold text-lf-secondary mb-3">{$_('brokers.metadata')}</h3>
                    <div class="space-y-2 text-sm">
                        <div class="flex justify-between">
                            <span class="text-lf-muted">{$_('brokers.isActive')}</span>
                            <span class="font-medium {broker.is_active ? 'text-lf-success' : 'text-lf-danger'}">
                                {broker.is_active ? '✓ Active' : '✗ Closed'}
                            </span>
                        </div>
                        {#if safeString(broker.opened_at)}
                            <div class="flex justify-between">
                                <span class="text-lf-muted">{$_('brokers.openedAt')}</span>
                                <span class="text-lf-secondary">{formatDate(broker.opened_at, $uiLocaleStore)}</span>
                            </div>
                        {/if}
                        <div class="flex justify-between">
                            <span class="text-lf-muted">{$_('brokers.allowOverdraft')}</span>
                            <span class="font-medium {broker.allow_cash_overdraft ? 'text-lf-success' : 'text-lf-muted'}">
                                {broker.allow_cash_overdraft ? '✓' : '✗'}
                            </span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-lf-muted">{$_('brokers.allowShorting')}</span>
                            <span class="font-medium {broker.allow_asset_shorting ? 'text-lf-success' : 'text-lf-muted'}">
                                {broker.allow_asset_shorting ? '✓' : '✗'}
                            </span>
                        </div>
                        <div class="flex justify-between border-t border-lf-subtle pt-2 mt-2">
                            <span class="text-lf-muted">{$_('brokers.createdInSystem')}</span>
                            <span class="text-lf-secondary">{formatDate(broker.created_at, $uiLocaleStore)}</span>
                        </div>
                    </div>

                    {#if broker.total_value_base_currency}
                        {@const totalValue = safeCurrency(broker.total_value_base_currency)}
                        {#if totalValue}
                            <div class="mt-4 pt-4 border-t border-lf-subtle">
                                <div class="text-sm text-lf-muted">{$_('common.totalValue')}</div>
                                <div class="text-2xl font-bold text-lf-link">
                                    <CurrencyAmount amount={parseCurrencyAmount(totalValue.amount)} code={totalValue.code} />
                                </div>
                            </div>
                        {/if}
                    {/if}
                </div>

                <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-subtle p-4" data-testid="broker-sharing-section">
                    <h3 class="font-semibold text-lf-secondary mb-3 flex items-center gap-2">
                        <Users size={18} class="text-lf-link" />
                        {$_('brokers.sharing.title')}
                    </h3>
                    <BrokerSharingPanel brokerId={broker.id} readOnly={safeString(broker.user_role) !== 'OWNER'} onChanged={handleUpdated} bind:hasChanges={sharingHasChanges} />
                </div>
            </div>
        {/if}
    {/if}
</div>

{#if broker}
    <BrokerModal
        isOpen={editModalOpen}
        mode="edit"
        brokerId={broker.id}
        initialData={{
            name: broker.name,
            description: safeString(broker.description),
            portal_url: safeString(broker.portal_url),
            icon_url: safeString(broker.icon_url),
            default_import_plugin: safeString(broker.default_import_plugin),
            allow_cash_overdraft: broker.allow_cash_overdraft,
            allow_asset_shorting: broker.allow_asset_shorting,
            is_active: broker.is_active,
            opened_at: safeString(broker.opened_at),
        }}
        onclose={() => (editModalOpen = false)}
        onupdated={handleUpdated}
    />

    <TransactionFormModal open={txViewOpen} mode="view" items={txViewItems} onClose={() => (txViewOpen = false)} />

    <TransactionBulkModal
        open={bulkOpen}
        intent={bulkIntent}
        defaultBrokerId={broker.id}
        onClose={() => {
            bulkOpen = false;
            bulkIntent = undefined;
        }}
        onCommitted={handleRefresh}
    />

    <BrokerImportFilesModal open={importFilesModalOpen} brokerId={broker.id} brokerName={broker.name} onClose={() => (importFilesModalOpen = false)} />
{/if}
