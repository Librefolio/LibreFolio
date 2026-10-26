<!--
  Dashboard Home — Portfolio overview page.

  Layout (from wireframe plan_ui_dashboard.md):
  1. Header row: DateRangePicker | spacer | Broker filter panel | ↻ Sync
  2. KPI row: Net Worth | Gain/Loss | Weighted ROI
  3. Charts row: GrowthChart (3/5) | Allocation tabs (2/5)
  4. Bottom grid: Holdings (left) | Recent Transactions (right)

  Data source: portfolioStore.fetchReport() → single POST /portfolio/report
  (summary + history + allocation_history in one engine run)

  Pattern: Svelte 5 Runes, Tailwind CSS 4, dark mode, data-testid everywhere.
-->
<script lang="ts">
    import {onDestroy, onMount, tick, untrack} from 'svelte';
    import {page} from '$app/stores';
    import {_} from '$lib/i18n';
    import {ArrowLeft, RefreshCw, Briefcase, TrendingUp, ArrowRightLeft, Wallet, Shield} from 'lucide-svelte';
    import AiExportMenu from '$lib/features/ai-export/AiExportMenu.svelte';
    import {prepareAiExport, type PreparedAiExport} from '$lib/features/ai-export/aiExportClipboard';
    import type {AiExportOptionsSelection} from '$lib/features/ai-export/aiExportOptions';
    import {aiExportCatalogLoader, emptyAiExportCompatibility, type AiExportCatalogCompatibilityResult} from '$lib/features/ai-export/catalog/compatibility';
    import {buildAiExportMenuLabels, getAiExportErrorMessage, getAiExportSuccessMessages} from '$lib/features/ai-export/ui';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {buildAssetSyncToast, buildFxSyncToast} from '$lib/utils/sync/syncToastHelpers';
    import {buildMissingFxRatesSyncRequest} from '$lib/utils/sync/syncRange';
    import {fxPairHtml} from '$lib/utils/providerHelpers';
    import {extractErrorMessage} from '$lib/utils/trySave';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';

    import {
        fetchReport,
        invalidate,
        peekReport,
        portfolioError,
        type ReportOptions,
        type PortfolioReport,
        type PortfolioSummary,
        type PortfolioHistoryPoint,
        type PortfolioRange,
        type PortfolioMwrrLinePoint,
        type AllocationHistoryDimensions,
        type PositionsContribution,
        type PortfolioBrokerPnlHistory,
        type PortfolioPnlCandleSeries,
        type PortfolioIncomeHistorySeries,
        type PortfolioCostHistorySeries,
        type PortfolioDepositHistorySeries,
        type PortfolioAcquisitionFundingSeries,
    } from '$lib/stores/portfolio/portfolioStore.svelte';
    import {ensureBrokersLoaded, getAllBrokers, getOwnedBrokers} from '$lib/stores/reference/brokerStore';
    import {registerPortfolioMutationListener, requestPortfolioRefresh} from '$lib/stores/portfolio/portfolioMutation';
    import {createLazyReportRetry} from '$lib/stores/portfolio/lazyReportRetry.svelte';
    import {pageBusy} from '$lib/stores/app/pageBusy.svelte';
    import {readDashboardView, writeDashboardView} from '$lib/features/dashboard/dashboardViewStore';
    import {setTweenHydration} from '$lib/components/ui/TweenedValue.svelte';
    import {ensureAssetsLoaded, getAssetInfo, assetStoreVersion} from '$lib/stores/reference/assetStore';
    import {getAssetPanelAssetId, buildAssetPanelUrl} from '$lib/utils/broker/assetPanelUrl';
    import {buildTabUrl, getResolvedTabParam} from '$lib/utils/url/tabUrl';
    import {defaultDisplayCurrency} from '$lib/stores/app/settings';
    import {createDateRangeController} from '$lib/features/dashboard/dateRangeController.svelte';
    import PageToolbar from '$lib/components/ui/toolbar/PageToolbar.svelte';
    import {getFixedDropdownPosition} from '$lib/utils/layout/dropdownPosition';
    import DateRangePicker from '$lib/components/ui/date/DateRangePicker.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import AllocationPanel from '$lib/features/dashboard/AllocationPanel.svelte';
    import GrowthChart from '$lib/features/dashboard/GrowthChart.svelte';
    import KpiSection from '$lib/features/dashboard/KpiSection.svelte';
    import RiskLevelsPanel from '$lib/features/risk/levels/RiskLevelsPanel.svelte';
    import PositionsPanel from '$lib/features/dashboard/PositionsPanel.svelte';
    import {createPositionsSeriesController, type PositionsSeriesScope} from '$lib/features/dashboard/positionsSeriesController';
    import LotsAnalysisPanel from '$lib/features/brokers/lots/LotsAnalysisPanel.svelte';
    import {DataQualityBanner} from '$lib/components/ui/feedback';
    import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';
    import FxPairAddModal from '$lib/components/fx/FxPairAddModal.svelte';
    import {invalidateFxRoutes} from '$lib/stores/reference/fxRoutesStore';
    import {getClientSessionGeneration, isClientSessionCurrent} from '$lib/stores/app/clientSession';
    import {classifyFxSyncOutcome, formatFxSyncResult, FX_SYNC_TIMEOUT_MS, type FxPairSyncCompleteDetail, type FxSyncResponse} from '$lib/services/fxCreationSync';
    import TransactionFormModal from '$lib/features/transactions/form/TransactionFormModal.svelte';
    import TransactionsTable from '$lib/features/transactions/TransactionsTable.svelte';
    import {resolveFormItemsForView, type FormModalItems} from '$lib/features/transactions/resolveFormItems';
    import {loadPartnerRows, loadEventTooltipMap} from '$lib/features/transactions/loadTransactionRows';
    import type {TXReadItem, AssetEvent} from '$lib/features/transactions/types';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import BrokerIcon from '$lib/components/ui/display/BrokerIcon.svelte';
    import {getBrokerRole} from '$lib/stores/reference/brokerStore';
    import {getRoleIcon, getRoleIconColor} from '$lib/utils/broker/brokerRoleHelpers';
    import {currentLanguage} from '$lib/stores/app/language';
    import {goto} from '$app/navigation';
    import {formatCurrencyAmountHtml} from '$lib/utils/currency/currencyFormat';
    import {zodiosApi} from '$lib/api';
    import {buildTransactionsFiltersUrl} from '../transactions/filterState';

    const DISABLED_AI_EXPORT_COMPATIBILITY = emptyAiExportCompatibility();

    // =========================================================================
    // State
    // =========================================================================

    let summary = $state<PortfolioSummary | null>(null);
    let history = $state<PortfolioHistoryPoint[]>([]);
    /** The days the report's step series cover, and the history's MWRR as true points (D-P4). */
    let historyRange = $state<PortfolioRange | null>(null);
    let mwrrLine = $state<PortfolioMwrrLinePoint[]>([]);
    let brokerPnlHistory = $state<PortfolioBrokerPnlHistory[]>([]);
    let pnlCandles = $state<PortfolioPnlCandleSeries | null>(null);
    let pnlCandlesLoading = $state(false);
    let incomeHistory = $state<PortfolioIncomeHistorySeries | undefined>(undefined);
    let costHistory = $state<PortfolioCostHistorySeries | undefined>(undefined);
    let depositHistory = $state<PortfolioDepositHistorySeries | undefined>(undefined);
    let acquisitionFunding = $state<PortfolioAcquisitionFundingSeries | undefined>(undefined);
    let allocationHistoryFromReport = $state<AllocationHistoryDimensions | null>(null);
    let positionsContribution = $state<PositionsContribution | null>(null);
    let contributionLoading = $state(false);
    /** A contribution already on screen is being refreshed in background: busy, but no skeleton. */
    let contributionRefreshing = $state(false);
    /** The same refresh after a price catch-up (Z-18): it guards against a second request like `contributionRefreshing`,
     *  but the root's `aria-busy` does not read it. Never rendered, so not reactive. */
    let contributionInBackground = false;
    let reportLoading = $state(true);
    /** True only on first load when no data exists yet. Once data is loaded, subsequent fetches are "refreshing". */
    let summaryLoading = $derived(reportLoading && !summary);
    let historyLoading = $derived(reportLoading && history.length === 0);
    let syncLoading = $state(false);
    let syncingCode = $state<string | null>(null);

    /** The currency and broker filter the user left (E3): they last the session, so a return asks
     *  the key it left and the cache can serve it. */
    const restoredView = readDashboardView();
    /** The owned brokers, when the broker list is already in memory (any in-app return): the restored
     *  scope can then be read from the cache before the first render. On a cold load the list arrives
     *  in onMount, and nothing is asked before it (F2). */
    const knownOwnedBrokers: BrokerLike[] | null = getAllBrokers().length > 0 ? getOwnedBrokers() : null;

    /** Broker IDs selected in the filter (empty = all brokers). */
    let selectedBrokerIds = $state<number[]>(knownOwnedBrokers ? restoredView.brokerIds.filter((id) => knownOwnedBrokers.some((broker) => broker.id === id)) : restoredView.brokerIds);
    let allBrokers = $state<BrokerLike[]>(knownOwnedBrokers ?? []);
    /** F2: the owned brokers are known. Until then nothing is asked: a request without them would be
     *  widened by the backend to every broker the user can see, viewer and editor ones included. */
    let brokersReady = $state(knownOwnedBrokers !== null);
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

    // The lot detail takes the place of the portfolio view (#48): opening it is a step of the browser's history, so «back»
    // (or «← Portfolio») returns to the portfolio.
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
    let reloadTimer = $state<ReturnType<typeof setTimeout> | null>(null);

    /**
     * Date range — backed by global store (shared with assets/fx pages) via the
     * shared dateRangeController (owns the seed/display/isMaxPending bookkeeping
     * that used to be duplicated per-page — see dateRangeController.svelte.ts).
     */
    const dateRangeCtl = createDateRangeController(() => void pageBusy.track('dashboard-period', () => loadAll()));

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
    let appliedCurrency = $state(initialCurrency);
    let targetCurrencyManuallySet = $state(restoredView.targetCurrency !== null);

    /** Broker filter dropdown open state. */
    let brokerFilterOpen = $state(false);
    let brokerFilterTriggerEl = $state<HTMLButtonElement | null>(null);
    let brokerFilterPanelEl = $state<HTMLDivElement | null>(null);

    /** Mirrors the DateRangePicker's own effective 2-row max-width, so the Currency+Broker row
     *  below it can be capped to the SAME pixel value when filtersStacked — otherwise it
     *  stretches to the full (wider) filters column instead of matching the picker's box.
     *  MUST start non-undefined (matches DateRangePicker's own maxWidthTwoRow default, 390) —
     *  Svelte forbids bind:key={undefined} when the child prop has a declared fallback. */
    let pickerMaxWidth = $state<number>(390);
    let brokerFilterDropdownPosition = $state({left: 8, top: 8});

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
        if (hadLoadedData && !reportLoading) void pageBusy.track('dashboard-currency', () => loadAll(true));
    });

    /**
     * True when the selection covers all brokers — treated same as "no filter"
     * so that selecting all is equivalent to deselecting all.
     */
    const allBrokersSelected = $derived(selectedBrokerIds.length > 0 && selectedBrokerIds.length >= allBrokers.length);

    /** Owned broker IDs (F2: the dashboard only aggregates brokers the user owns,
     *  scaled by share; a 0% share behaves like editor/viewer and is excluded). */
    const ownedBrokerIds = $derived(allBrokers.map((b) => b.id));

    /** F2: a request may leave only with an explicit owned scope. Without one the backend would
     *  widen it to every broker the user can see; a user who owns nothing is asked nothing. */
    const canAsk = $derived(brokersReady && ownedBrokerIds.length > 0);

    /** Which broker IDs to pass to the API — always the explicit owned set, so the
     *  backend never falls back to "every accessible broker" for the dashboard. */
    const activeBrokerIds = $derived(!allBrokersSelected && selectedBrokerIds.length > 0 ? selectedBrokerIds : ownedBrokerIds.length > 0 ? ownedBrokerIds : undefined);

    /** GrowthChart P&L broker overlay (G1a) caller policy per plan §4.1: request
     *  broker_pnl_history only when the effective scope has ≥2 brokers — a single
     *  broker's line would be identical to the total and the payload is unneeded. */
    const effectiveBrokerCount = $derived((activeBrokerIds ?? ownedBrokerIds).length);
    const wantsBrokerPnlHistory = $derived(effectiveBrokerCount >= 2);

    /** AI export state — dropdown open/position handled internally by AiExportMenu. */
    let aiExportCompatibility = $state<AiExportCatalogCompatibilityResult>(DISABLED_AI_EXPORT_COMPATIBILITY);
    let aiExportCatalogLoading = $state(true);
    let aiExportCatalogFailed = $state(false);
    let aiExportLabels = $derived(buildAiExportMenuLabels($_, aiExportCompatibility, $_('dashboard.aiExport')));

    /** Whether the filter is "active" (some but not all brokers selected). */
    const brokerFilterActive = $derived(selectedBrokerIds.length > 0 && !allBrokersSelected);

    /** Broker filter trigger label — follows assets-page type-filter pattern (no separate badge). */
    const brokerFilterLabel = $derived(brokerFilterActive ? (selectedBrokerIds.length === 1 ? (allBrokers.find((b) => b.id === selectedBrokerIds[0])?.name ?? String(selectedBrokerIds[0])) : `${$_('brokers.title')} (${selectedBrokerIds.length})`) : $_('dashboard.allBrokers'));

    const dataQualityIssues = $derived<DataQualityIssue[]>((summary?.data_quality as {issues?: DataQualityIssue[]} | undefined)?.issues ?? []);

    /** Tab navigation — mirrors the broker detail page's structure (no "Info" tab
     *  here: there's no portfolio-wide metadata/sharing concept at this level). */
    const DASHBOARD_TAB_IDS = ['panoramica', 'posizioni', 'rischio', 'transazioni'] as const;
    type DashboardTabId = (typeof DASHBOARD_TAB_IDS)[number];
    const DEFAULT_DASHBOARD_TAB: DashboardTabId = 'panoramica';

    function isDashboardTabId(tabId: string): tabId is DashboardTabId {
        return DASHBOARD_TAB_IDS.includes(tabId as DashboardTabId);
    }

    // Read at init too, so a return to another tab does not first mount the overview and tear it down.
    let activeTab = $state<DashboardTabId>(getResolvedTabParam($page.url.searchParams, DASHBOARD_TAB_IDS, DEFAULT_DASHBOARD_TAB));
    const dashboardTabs = $derived([
        {id: 'panoramica', label: $_('brokers.overview'), icon: Briefcase, testId: 'dashboard-tab-panoramica'},
        {id: 'posizioni', label: $_('brokers.positions'), icon: TrendingUp, testId: 'dashboard-tab-posizioni'},
        {id: 'rischio', label: $_('risk.title'), icon: Shield, testId: 'dashboard-tab-risk'},
        {id: 'transazioni', label: $_('transactions.title'), icon: ArrowRightLeft, testId: 'dashboard-tab-transazioni'},
    ]);

    $effect(() => {
        activeTab = getResolvedTabParam($page.url.searchParams, DASHBOARD_TAB_IDS, DEFAULT_DASHBOARD_TAB);
    });

    function handleTabChange(tabId: string) {
        if (!isDashboardTabId(tabId)) return;
        activeTab = tabId;
        void goto(buildTabUrl($page.url, tabId), {replaceState: true, noScroll: true});
    }

    /** FxPairAddModal state for CTA-driven pair creation */
    let showFxPairAddModal = $state(false);
    let pageAlive = true;
    // Y-24: a failed candles or contribution request is asked again at most three times, 2, 4 and 8 s later, then not
    // until the scope changes or the user's Refresh (`handleSync`); before, it was asked again at once, without end.
    const candlesRetry = createLazyReportRetry();
    const contributionRetry = createLazyReportRetry();
    onDestroy(() => {
        pageAlive = false;
        candlesRetry.dispose();
        contributionRetry.dispose();
    });
    let fxPairCreateSlug = $state('');

    /** Transaction view modal state (opened from the Transazioni tab's row double-click). */
    let txViewOpen = $state(false);
    let txViewItems = $state<FormModalItems | null>(null);

    /** Transazioni tab — filtered by the SAME broker filter + date range as the rest of the
     *  dashboard (not just "recent 10" regardless of period), with real pagination via
     *  TransactionsTable's built-in DataTablePagination. Lazy-loaded/reloaded whenever the
     *  tab is active and the broker/date filter key changes (mirrors RecentTransactionsPanel's
     *  previous key-based reload pattern, now also keyed on the date range). */
    let txMainRows = $state<TXReadItem[]>([]);
    let txPartnerRows = $state<TXReadItem[]>([]);
    let txEventTooltipMap = $state<Map<number, AssetEvent>>(new Map());
    let txLoading = $state(false);
    let txCurrentPage = $state(1);
    let lastTxLoadKey = $state('');

    $effect(() => {
        if (activeTab !== 'transazioni') return;
        const key = `${dateRangeCtl.start}|${dateRangeCtl.end}|${activeBrokerIds ? [...activeBrokerIds].sort((a, b) => a - b).join(',') : 'all'}`;
        if (key !== lastTxLoadKey) {
            lastTxLoadKey = key;
            txCurrentPage = 1;
            void pageBusy.track('dashboard-transactions', loadTransactions);
        }
    });

    async function loadTransactions() {
        // F2: nothing owned → the dashboard (including this tab) shows nothing.
        if (ownedBrokerIds.length === 0) {
            txMainRows = [];
            txPartnerRows = [];
            return;
        }
        txLoading = true;
        try {
            // Server-side filter: date range always applied; broker_id per-broker (the endpoint
            // only accepts a single broker_id) when a subset is selected, omitted for "all".
            const fetchForBroker = async (brokerId?: number): Promise<TXReadItem[]> => {
                const queries: Record<string, unknown> = {};
                if (brokerId != null) queries.broker_id = brokerId;
                if (dateRangeCtl.start) queries.date_start = dateRangeCtl.start;
                if (dateRangeCtl.end) queries.date_end = dateRangeCtl.end;
                return (await zodiosApi.query_transactions_api_v1_transactions_get({queries})) as TXReadItem[];
            };

            const all = activeBrokerIds && activeBrokerIds.length > 0 ? Array.from(new Map((await Promise.all(activeBrokerIds.map((id) => fetchForBroker(id)))).flat().map((tx) => [tx.id, tx])).values()) : await fetchForBroker(undefined);

            txMainRows = all;
            const [partner, tooltipMap] = await Promise.all([loadPartnerRows(txMainRows), loadEventTooltipMap(txMainRows)]);
            txPartnerRows = partner;
            txEventTooltipMap = tooltipMap;
        } finally {
            txLoading = false;
        }
    }

    /**
     * «Sync rates» on MISSING_FX_RATES. A date is missing only when no rate exists on or
     * before it, so the missing dates precede the pair's first stored rate and a sync of the
     * period on screen never reaches them: the request targets the dates the issue carries,
     * a week either side, never past today (`buildMissingFxRatesSyncRequest`).
     *
     * The outcome is told once the report is reloaded, because only then is it known whether
     * the dates are covered: when the provider returned nothing for them, the toast says so
     * instead of reporting a success the banner would contradict.
     */
    async function syncMissingFxRates(issue: DataQualityIssue) {
        const request = buildMissingFxRatesSyncRequest(issue);
        if (!request) return;
        const sessionGeneration = getClientSessionGeneration();
        const current = () => pageAlive && isClientSessionCurrent(sessionGeneration);
        const coversRequestedPair = (candidate: DataQualityIssue) => (buildMissingFxRatesSyncRequest(candidate)?.pairs ?? []).some((slug) => request.pairs.includes(slug));
        syncLoading = true;
        syncingCode = issue.code;
        toasts.info($_('fx.sync.inProgress'));
        try {
            let response: FxSyncResponse | undefined;
            let transportError: string | undefined;
            try {
                response = await zodiosApi.sync_rates_api_v1_fx_currencies_sync_post(request, {timeout: FX_SYNC_TIMEOUT_MS});
            } catch (error) {
                transportError = extractErrorMessage(error, $_('prices.sync.failedDefault'));
            }
            if (!current()) return;
            const {requestedResults, operationErrors, outcome, variant: outcomeVariant} = classifyFxSyncOutcome(request.pairs, response, transportError);

            // No reload after a transport error: the backend may still be writing those rates.
            let remaining: DataQualityIssue | undefined;
            let stillMissing: boolean | null = null;
            if (!transportError) {
                invalidateFxRoutes();
                invalidate();
                // The open lots and risk panels ask again too, as after «Aggiorna»: new rates change their figures.
                refreshVersion += 1;
                try {
                    await loadAll(true, true);
                    remaining = dataQualityIssues.find((candidate) => candidate.cta_action === 'sync_fx_pair' && coversRequestedPair(candidate));
                    stillMissing = remaining !== undefined;
                } catch {
                    stillMissing = null;
                }
                if (!current()) return;
            }

            const tr = (key: string, opts?: any) => $_(key, opts);
            const pairOptions = {outerFlags: true, linkToDetail: true};
            let variant = outcomeVariant;
            let message = transportError
                ? request.pairs.map((slug) => buildFxSyncToast({status: 'failed', message: escapeHtml(transportError)}, slug, tr, undefined, undefined, pairOptions).message).join('\n\n')
                : requestedResults.map((result, index) => formatFxSyncResult(result, request.pairs[index]).message).join('\n\n');
            if (operationErrors.length > 0) message += `\n${operationErrors.map(escapeHtml).join('; ')}`;
            if (remaining && (outcome === 'ok' || outcome === 'partial')) {
                const params = remaining.message_params ?? {};
                const stillMissingPairs = (buildMissingFxRatesSyncRequest(remaining)?.pairs ?? []).filter((slug) => request.pairs.includes(slug));
                message += `\n\n${$_('dataQuality.missingFxRatesAfterSync', {
                    values: {
                        pairs: stillMissingPairs.map((slug) => fxPairHtml(slug, pairOptions)).join(', '),
                        date_from: escapeHtml(String(params.date_from ?? '')),
                        date_to: escapeHtml(String(params.date_to ?? '')),
                        dates_count: params.dates_count ?? '',
                    },
                })}`;
                if (variant === 'success') variant = 'warning';
            }
            notify({
                name: 'fx.rates.synced',
                detail: {origin: 'dashboard-banner', pairs: request.pairs, start: request.start, end: request.end, outcome, stillMissing},
                toast: {variant, message},
            });
        } finally {
            syncLoading = false;
            syncingCode = null;
        }
    }

    async function handleBannerAction(action: string, target: string | null, _issue: DataQualityIssue) {
        if (action === 'navigate_asset' && target) {
            goto(`/assets/${target}`);
        } else if (action === 'navigate_fx' && target) {
            goto(`/fx/${target}`);
        } else if (action === 'add_fx_pair') {
            // The banner has one chip per missing pair: the dialog opens on the pair of the chip pressed.
            fxPairCreateSlug = target ?? '';
            showFxPairAddModal = true;
        } else if (action === 'sync_fx_pair') {
            await syncMissingFxRates(_issue);
        } else if (action === 'sync_asset_prices') {
            // STALE_PRICE: re-sync the flagged provider assets from the day after their last
            // stored price ('resume', the rule every auto-sync uses) up to the dashboard's end
            // date, then reload the report (the banner clears once the prices are fresh).
            const assetIds = _issue.affected_asset_ids ?? [];
            if (assetIds.length === 0) return;
            const assetNames = _issue.affected_asset_names ?? [];
            const tr = (key: string, opts?: any) => $_(key, opts);
            syncLoading = true;
            syncingCode = _issue.code;
            try {
                const response = await zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post(
                    assetIds.map((asset_id) => ({asset_id, date_range: {start: 'resume', end: dateRangeCtl.end}})),
                    {timeout: 120 * 1000},
                );
                for (const result of ((response as any)?.results ?? []) as any[]) {
                    const name = assetNames[assetIds.indexOf(result?.asset_id)] ?? `#${result?.asset_id}`;
                    const toast = buildAssetSyncToast(result, escapeHtml(name), tr);
                    toasts[toast.variant](toast.message);
                }
                invalidate();
                // The open lots and risk panels ask again too, as after «Aggiorna»: new prices change their figures.
                refreshVersion += 1;
                await loadAll(true);
            } catch (e: any) {
                toasts.error(`${$_('common.sync')} — ${e?.message || $_('prices.sync.failedDefault')}`);
            } finally {
                syncLoading = false;
                syncingCode = null;
            }
        }
    }

    /** URL for "See all" links — preserves current date range (assets) and, for
     *  transactions, ALSO the broker filter (single broker_id / multi broker_ids),
     *  via the SAME filter map + URL builder /transactions itself uses. */
    const assetsHref = $derived(`/assets?start=${urlDateFrom}&end=${urlDateTo}`);
    const transactionsHref = $derived(
        buildTransactionsFiltersUrl({
            date_start: dateRangeCtl.start || undefined,
            date_end: dateRangeCtl.end || undefined,
            broker_id: activeBrokerIds && activeBrokerIds.length === 1 ? activeBrokerIds[0] : undefined,
            broker_ids: activeBrokerIds && activeBrokerIds.length > 1 ? activeBrokerIds : undefined,
        }),
    );

    // =========================================================================
    // Loaders
    // =========================================================================

    async function loadSummary(force = false) {
        // No-op: summary is loaded as part of loadAll via fetchReport
        void force;
    }

    async function loadHistory(force = false) {
        // No-op: history is loaded as part of loadAll via fetchReport
        void force;
    }

    /**
     * When "All" (MAX) is pending resolution, extract the real earliest date
     * from the just-loaded portfolio history via the shared date controller.
     * No-op once already resolved or if there's no history data yet.
     */
    function resolveMaxStartFromHistory() {
        dateRangeCtl.markMaxResolved(history.length > 0 ? history[0].date : null);
    }

    /** What `loadAll` asks on top of the defaults: the main report, without contribution or candles. */
    function mainReportOptions(): ReportOptions {
        return {includeBrokerPnlHistory: wantsBrokerPnlHistory, includeIncomeHistory: true, includeCostHistory: true, includeDepositHistory: true, includeAcquisitionFunding: true};
    }

    /** The report on screen: a page that finds the same cached report again leaves its charts alone. */
    let shownReport: PortfolioReport | null = null;

    function applyReport(report: PortfolioReport | null, requested: string) {
        shownReport = report;
        // Cast from the Zodios union types to the concrete types the dashboard expects
        summary = (report?.summary as PortfolioSummary | null | undefined) ?? null;
        history = (report?.history as PortfolioHistoryPoint[] | null | undefined) ?? [];
        historyRange = (report?.range as PortfolioRange | null | undefined) ?? null;
        mwrrLine = (report?.mwrr_line as PortfolioMwrrLinePoint[] | null | undefined) ?? [];
        brokerPnlHistory = (report?.broker_pnl_history as PortfolioBrokerPnlHistory[] | null | undefined) ?? [];
        // Always reassigned (defaulting to null since loadAll() never requests candles):
        // this is also what invalidates a stale candle series from a prior broker/date-range
        // scope. loadPnlCandles() re-fetches lazily once GrowthChart notices pnlCandles==null
        // again while still in the candles submode.
        pnlCandles = (report?.pnl_candles as PortfolioPnlCandleSeries | null | undefined) ?? null;
        // Eager (unlike pnlCandles): requested on every ordinary load per plan §4.1's
        // sparse-payload policy, so this is always fresh — no separate lazy loader needed.
        incomeHistory = (report?.income_history as PortfolioIncomeHistorySeries | null | undefined) ?? undefined;
        costHistory = (report?.cost_history as PortfolioCostHistorySeries | null | undefined) ?? undefined;
        depositHistory = (report?.deposit_history as PortfolioDepositHistorySeries | null | undefined) ?? undefined;
        acquisitionFunding = (report?.acquisition_funding as PortfolioAcquisitionFundingSeries | null | undefined) ?? undefined;
        allocationHistoryFromReport = (report?.allocation_history as AllocationHistoryDimensions | null | undefined) ?? null;
        resolveMaxStartFromHistory();
        appliedCurrency = requested;
    }

    let shownContribution: PortfolioReport['positions_contribution'] = null;

    function setContribution(report: PortfolioReport | null) {
        const contribution = report?.positions_contribution ?? null;
        if (contribution === shownContribution) return;
        shownContribution = contribution;
        positionsContribution = (contribution as PositionsContribution | null | undefined) ?? null;
    }

    /** The contribution of the scope on screen as the cache holds it (null: never asked, PositionsPanel
     *  asks when its Performance view needs it). Returns whether the cached one is stale. */
    function showCachedContribution(): boolean {
        const cached = peekReport(activeBrokerIds, dateRangeCtl.start || undefined, dateRangeCtl.end || undefined, targetCurrency, true, false, false, false);
        setContribution(cached?.report ?? null);
        return cached?.stale === true;
    }

    /**
     * Page cache (E1): the report of the scope on screen comes from the cache at once — stale or
     * not — and only a stale or missing one is asked again, in background: the figures stay up and
     * move to the fresh values when they land. A refresh that fails keeps them, with a toast.
     * With `background` (after a price catch-up, Z-18) the page does not say it is busy either: neither
     * `reportLoading` nor `contributionRefreshing` turns on, so the root's `aria-busy` stays off.
     */
    let loadSeq = 0;

    async function loadAll(force = false, propagateError = false, {background = false}: {background?: boolean} = {}) {
        const sessionGeneration = getClientSessionGeneration();
        const current = () => pageAlive && isClientSessionCurrent(sessionGeneration);
        if (!current() || !brokersReady) return;
        if (!canAsk) {
            reportLoading = false;
            return;
        }
        const load = ++loadSeq;
        const requested = targetCurrency;
        const brokerIds = activeBrokerIds;
        const start = dateRangeCtl.start || undefined;
        const end = dateRangeCtl.end || undefined;
        const options = mainReportOptions();

        const cached = peekReport(brokerIds, start, end, requested, false, false, true, true, options);
        if (cached && cached.report !== shownReport) applyReport(cached.report, requested);
        const request = !cached || cached.stale || force ? fetchReport(brokerIds, start, end, requested, force, undefined, undefined, undefined, undefined, options) : null;
        if (showCachedContribution()) void loadContribution({background});
        if (!request) {
            reportLoading = false;
            return;
        }

        if (!background) reportLoading = true;
        try {
            const report = await request;
            if (!current() || load !== loadSeq) return;
            if (report) {
                if (report !== shownReport) applyReport(report, requested);
            } else if (propagateError) {
                throw new Error($_('common.error'));
            } else if (cached) {
                toasts.error(`${$_('common.refresh')} — ${escapeHtml(portfolioError() ?? $_('common.error'))}`);
            } else {
                applyReport(null, requested);
            }
        } finally {
            if (current() && load === loadSeq) reportLoading = false;
        }
    }

    function hydrateFromCache() {
        if (!brokersReady || ownedBrokerIds.length === 0) return;
        const cached = peekReport(activeBrokerIds, dateRangeCtl.start || undefined, dateRangeCtl.end || undefined, targetCurrency, false, false, true, true, mainReportOptions());
        if (!cached) return;
        applyReport(cached.report, targetCurrency);
        showCachedContribution();
    }

    async function handleFxPairCreated() {
        if (!pageAlive) return;
        invalidateFxRoutes();
        invalidate();
        await pageBusy.track('dashboard-reload', () => loadAll(true));
    }

    async function handleFxPairCreationSynced(detail: FxPairSyncCompleteDetail) {
        if (!pageAlive || !isClientSessionCurrent(detail.sessionGeneration)) return;
        // The sync interceptor marks portfolio/risk caches stale at commit time, when it wrote something.
        await loadAll(true, true);
    }

    /** The scope of a lazy report section: brokers, period and currency. An answer of another scope is not applied, and a failure counts for its own scope only (Y-24). */
    function reportScope(): string {
        return `${activeBrokerIds?.join(',')}|${dateRangeCtl.start}|${dateRangeCtl.end}|${targetCurrency}`;
    }

    /**
     * The contribution of the scope on screen: asked by PositionsPanel when its Performance view has
     * none, and by `loadAll` when the cached one is stale — then in background, with the cached rows
     * kept on screen (`contributionRefreshing`, not the skeleton of `contributionLoading`). With `background`
     * (after a price catch-up, Z-18), `contributionInBackground` instead, which the root's `aria-busy` does not read.
     */
    async function loadContribution({background = false}: {background?: boolean} = {}) {
        const askedScope = reportScope();
        if (!canAsk || contributionLoading || contributionRefreshing || contributionInBackground || !contributionRetry.canAsk(askedScope)) return;
        const requested = targetCurrency;
        const brokerIds = activeBrokerIds;
        const start = dateRangeCtl.start || undefined;
        const end = dateRangeCtl.end || undefined;
        const cached = peekReport(brokerIds, start, end, requested, true, false, false, false);
        if (cached && !cached.stale) {
            setContribution(cached.report);
            return;
        }
        if (cached && background) contributionInBackground = true;
        else if (cached) contributionRefreshing = true;
        else contributionLoading = true;
        try {
            // includeHistory/includeAllocationHistory=false: only positions_contribution is read below.
            const report = await fetchReport(brokerIds, start, end, requested, false, true, false, false, false);
            if (!pageAlive || reportScope() !== askedScope) return;
            // The outcome is recorded before the flags fall back in `finally`: the effect they wake reads it (Y-24).
            if (report) {
                contributionRetry.succeeded(askedScope);
                setContribution(report);
                appliedCurrency = requested;
            } else {
                contributionRetry.failed(askedScope);
                if (!cached) setContribution(null);
            }
        } finally {
            contributionLoading = false;
            contributionRefreshing = false;
            contributionInBackground = false;
        }
    }

    /**
     * The per-position return chart (Y5-2): the lines of the positions the user ticked, asked for the scope on screen —
     * its brokers, period and currency — and asked again when the scope or `refreshVersion` moves.
     */
    const positionsSeriesCtl = createPositionsSeriesController();
    const positionsSeriesScope = $derived<PositionsSeriesScope>({
        brokerIds: activeBrokerIds,
        start: dateRangeCtl.start || undefined,
        end: dateRangeCtl.end || undefined,
        currency: targetCurrency,
        ready: canAsk,
        version: refreshVersion,
    });
    $effect(() => {
        const scope = positionsSeriesScope;
        untrack(() => positionsSeriesCtl.sync(scope));
    });
    onDestroy(() => positionsSeriesCtl.dispose());

    /** Lazy-load the synthetic P&L candle series (G1b — called by GrowthChart's
     *  onRequestPnlCandles when the user first activates the candles submode; caller
     *  policy per plan §4.1: "expensive OHLC work stays off ordinary reports").
     *  The guard's reads run synchronously inside GrowthChart's effect, so they are its
     *  dependencies: `canAsk` turning true is what makes a saved Candles view on a fresh
     *  page ask again once the brokers are known (Y-16), and `candlesRetry.canAsk` is what
     *  asks again 2, 4 and 8 s after a failure (Y-24). Keep them before the first await. */
    async function loadPnlCandles() {
        const askedScope = reportScope();
        if (!canAsk || pnlCandles || pnlCandlesLoading || !candlesRetry.canAsk(askedScope)) return;
        pnlCandlesLoading = true;
        const requested = targetCurrency;
        try {
            // includeHistory/includeAllocationHistory/includeContribution/includeBreakdown=false:
            // only pnl_candles is read below.
            const report = await fetchReport(activeBrokerIds, dateRangeCtl.start || undefined, dateRangeCtl.end || undefined, requested, false, false, false, false, false, {includePnlCandles: true});
            // An answer of another scope is not this one's: the scope on screen asks for its own.
            if (!pageAlive || reportScope() !== askedScope) return;
            if (report) candlesRetry.succeeded(askedScope);
            else candlesRetry.failed(askedScope);
            pnlCandles = (report?.pnl_candles as PortfolioPnlCandleSeries | null | undefined) ?? null;
        } finally {
            pnlCandlesLoading = false;
        }
    }

    // =========================================================================
    // Event handlers
    // =========================================================================

    function selectBrokers(ids: number[]) {
        selectedBrokerIds = ids;
        writeDashboardView({brokerIds: ids});
        scheduleReload();
    }

    function toggleBroker(id: number) {
        selectBrokers(selectedBrokerIds.includes(id) ? selectedBrokerIds.filter((x) => x !== id) : [...selectedBrokerIds, id]);
    }

    /** Fires loadAll after a 2-second quiet period (anti-bounce for rapid clicks). */
    function scheduleReload() {
        if (reloadTimer !== null) clearTimeout(reloadTimer);
        reloadTimer = setTimeout(() => {
            reloadTimer = null;
            void pageBusy.track('dashboard-scope', () => loadAll());
        }, 2000);
    }

    /** «Aggiorna» (E4): report, contribution, risk and lots are all asked again; what is on screen stays meanwhile. */
    async function handleSync() {
        syncLoading = true;
        // The user's Refresh: the lazy sections may be asked again whatever failed before (Y-24).
        candlesRetry.reset();
        contributionRetry.reset();
        requestPortfolioRefresh();
        refreshVersion += 1;
        try {
            await pageBusy.track('dashboard-refresh', () => loadAll(true));
        } finally {
            syncLoading = false;
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
        registerPortfolioMutationListener('dashboard:prices', (signal) => {
            if (signal.kind === 'prices') queueMicrotask(reloadAfterPriceCatchUp);
        }),
    );

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
        // F2: a portfolio export without the owned scope would be widened by the backend to every
        // broker the user can see. The trigger is disabled until then; this guards the call itself.
        if (!canAsk) return Promise.reject(new Error('Owned brokers are not loaded'));
        return prepareAiExport({
            context: {
                domain: 'portfolio',
                snapshotAsOf: dateRangeCtl.end,
                targetCurrency,
                brokerIds: activeBrokerIds,
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

    async function positionBrokerFilterDropdown() {
        await tick();
        if (!brokerFilterOpen) return;
        brokerFilterDropdownPosition = getFixedDropdownPosition(brokerFilterTriggerEl, brokerFilterPanelEl, 'start');
    }

    function updateOpenDropdownPositions() {
        if (brokerFilterOpen) {
            brokerFilterDropdownPosition = getFixedDropdownPosition(brokerFilterTriggerEl, brokerFilterPanelEl, 'start');
        }
    }

    function toggleBrokerFilterDropdown() {
        brokerFilterOpen = !brokerFilterOpen;
        if (brokerFilterOpen) void positionBrokerFilterDropdown();
    }

    // Outside-click closes the broker filter panel (AI export dropdown handles its own outside-click internally)
    function handleDocumentClick(e: MouseEvent) {
        if (!brokerFilterOpen) return;
        const target = e.target as HTMLElement;
        if (target.closest?.('[data-broker-filter-panel]') || target.closest?.('[data-testid="broker-filter-trigger"]')) return;
        brokerFilterOpen = false;
    }

    $effect(() => {
        if (!brokerFilterOpen) return;
        void positionBrokerFilterDropdown();
    });

    $effect(() => {
        if (!brokerFilterOpen) return;

        const handleViewportChange = () => updateOpenDropdownPositions();
        window.addEventListener('resize', handleViewportChange);
        window.addEventListener('scroll', handleViewportChange, true);

        return () => {
            window.removeEventListener('resize', handleViewportChange);
            window.removeEventListener('scroll', handleViewportChange, true);
        };
    });

    // =========================================================================
    // Lifecycle
    // =========================================================================

    // Figures already known when a card mounts — served from the cache on a return, or kept from an
    // earlier load on a tab switch — appear at their value instead of counting up from 0. The Risk
    // panel sets its own context for its cards, which come from the risk cache, not from this report.
    setTweenHydration(() => summary !== null);
    hydrateFromCache();

    onMount(() => {
        document.addEventListener('click', handleDocumentClick);
        void loadAiExportCompatibility();
        // The first load holds the Refresh button (Y11), from the reference lists to the report.
        void pageBusy.track('dashboard-first-load', async () => {
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
            if (allBrokers.length > 0) {
                await loadAll();
            } else {
                reportLoading = false;
            }
        });
        return () => document.removeEventListener('click', handleDocumentClick);
    });
</script>

<div
    class="space-y-4 text-lf-primary"
    data-testid="dashboard-page"
    use:guideAnchor={'page.dashboard'}
    aria-busy={reportLoading || contributionLoading || contributionRefreshing || syncLoading}
    data-busy={reportLoading || contributionLoading || contributionRefreshing || syncLoading ? 'true' : 'false'}
>
    <h1 class="sr-only">{$_('nav.dashboard')}</h1>

    <PageToolbar
        thresholds={{oneRow: 1000, denseRow: 990, stackFilters: 510, oneColumn: 390, noExtraLabel: 410, labelHideActions: 210, labelHideTabs: 460}}
        tabs={dashboardTabs}
        {activeTab}
        ontabchange={handleTabChange}
        testId="dashboard-controls"
        filterRowTestId="dashboard-filter-bar"
        layoutDebugName="dashboard"
    >
        {#snippet filters({layoutMode, filtersStacked, showExtraLabels})}
            <!-- Date range picker (wired to global store via the shared dateRangeController) -->
            <DateRangePicker bind:activePreset={dateRangeCtl.activePreset} bind:start={dateRangeCtl.displayStart} bind:end={dateRangeCtl.end} compact={true} align="start" {layoutMode} debugName="dashboard" onchange={dateRangeCtl.onDateRangeChange} bind:effectiveMaxWidth={pickerMaxWidth} />

            <!-- Currency override + Broker multi-select — share one justified row when the
                 filters+summary zone stacks (stackFilters/oneColumn — see filtersStacked
                 in PageToolbar), not each its own stacked full-width row; inline naturally
                 otherwise, same as before (unconditional w-full here would fight
                 DateRangePicker for row space in oneRow/denseRow mode). Capped to
                 pickerMaxWidth (mirrors the picker's own 2-row max-width) so this row's right
                 edge lines up with the picker's instead of stretching to the wider column. -->
            <div class="flex items-center gap-3 {filtersStacked ? 'w-full justify-around' : ''}" style={filtersStacked && pickerMaxWidth ? `max-width: ${pickerMaxWidth}px` : ''}>
                <!-- Currency override selector -->
                <div class="flex items-center gap-1.5 text-xs text-lf-muted">
                    <!-- Round 13: "Valuta:" is an extra/decorative label — the select itself
                         (flag + code) already conveys enough at very narrow widths, so it hides
                         first via the independent noExtraLabel threshold, well before labelHide*
                         would ever strip anything else on this row. -->
                    {#if showExtraLabels}<span class="whitespace-nowrap">{$_('common.currency')}:</span>{/if}
                    <div class="w-28">
                        <CurrencySearchSelect
                            bind:value={targetCurrency}
                            compact={true}
                            configuredOnly={true}
                            testId="dashboard-target-currency"
                            defaultCurrency={baseCurrency}
                            createForexLabel={$_('common.createForex')}
                            dropdownPosition="bottom"
                            placeholder={baseCurrency}
                            onCreateForex={() => {
                                // Prefill base = user default currency, quote left for the user to pick
                                fxPairCreateSlug = baseCurrency ? `${baseCurrency}-` : '';
                                showFxPairAddModal = true;
                            }}
                            onchange={() => {
                                targetCurrencyManuallySet = true;
                                writeDashboardView({targetCurrency});
                                void pageBusy.track('dashboard-currency', () => loadAll());
                            }}
                        />
                    </div>
                </div>

                <!-- Broker multi-select panel. With one broker selected the label is that
                     broker's name, of any length: the trigger shrinks and truncates it
                     instead of pushing out of the bar (the full name stays in the DOM). -->
                <div class="relative min-w-0">
                    <button
                        bind:this={brokerFilterTriggerEl}
                        class="flex items-center gap-1.5 min-w-0 max-w-full px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors whitespace-nowrap
                       {brokerFilterActive ? 'bg-lf-selected text-lf-link border-lf-focus' : 'bg-lf-card text-lf-secondary border-lf-input hover:bg-lf-hover'}"
                        onclick={toggleBrokerFilterDropdown}
                        data-testid="broker-filter-trigger"
                    >
                        <span class="truncate">{brokerFilterLabel}</span>
                        <svg class="w-3 h-3 shrink-0 transition-transform {brokerFilterOpen ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path d="M19 9l-7 7-7-7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
                        </svg>
                    </button>

                    {#if brokerFilterOpen}
                        <div
                            bind:this={brokerFilterPanelEl}
                            class="fixed z-50 w-56 bg-lf-card border border-lf-raised rounded-lg shadow-lg shadow-lf-shadow overflow-hidden"
                            style:left={`${brokerFilterDropdownPosition.left}px`}
                            style:top={`${brokerFilterDropdownPosition.top}px`}
                            data-broker-filter-panel
                        >
                            <!-- Select All / Deselect All -->
                            <div class="flex gap-2 px-2.5 py-2 border-b border-lf-subtle">
                                <button type="button" class="flex-1 px-2 py-1 text-[11px] font-medium border border-lf-subtle rounded bg-lf-panel text-lf-secondary hover:bg-lf-neutral transition-colors" onclick={() => selectBrokers(allBrokers.map((b) => b.id))}>{$_('common.selectAll')}</button>
                                <button type="button" class="flex-1 px-2 py-1 text-[11px] font-medium border border-lf-subtle rounded bg-lf-panel text-lf-secondary hover:bg-lf-neutral transition-colors" onclick={() => selectBrokers([])}>{$_('common.clearAll')}</button>
                            </div>
                            <!-- Broker list -->
                            <div class="max-h-52 overflow-y-auto mx-2.5 my-2 space-y-0.5">
                                {#each allBrokers as broker (broker.id)}
                                    {@const isSelected = selectedBrokerIds.includes(broker.id)}
                                    {@const role = getBrokerRole(broker.id)}
                                    {@const RoleIcon = role ? getRoleIcon(role) : null}
                                    <button
                                        type="button"
                                        class="flex items-center gap-2 w-full px-2 py-1.5 text-left text-[13px] rounded hover:bg-lf-hover transition-colors {isSelected ? 'text-lf-link' : 'text-lf-secondary'}"
                                        onclick={() => toggleBroker(broker.id)}
                                        data-testid="broker-filter-item-{broker.id}"
                                    >
                                        <BrokerIcon brokerId={broker.id} iconUrl={broker.icon_url} portalUrl={broker.portal_url} pluginCode={broker.default_import_plugin} altText={broker.name} size={16} />
                                        <span class="flex-1 truncate">{broker.name}</span>
                                        {#if RoleIcon}
                                            <RoleIcon size={14} class={getRoleIconColor(role)} />
                                        {/if}
                                        {#if isSelected}
                                            <svg class="w-3.5 h-3.5 text-lf-link flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
                                            </svg>
                                        {/if}
                                    </button>
                                {/each}
                            </div>
                        </div>
                    {/if}
                </div>
            </div>
        {/snippet}

        {#snippet actions({showActionLabels})}
            <!-- AI Export -->
            <AiExportMenu
                domain="portfolio"
                compatibility={aiExportCompatibility}
                memoryKey="portfolio"
                defaultSelectionId="portfolio.pac_planning"
                disabled={aiExportCatalogLoading || aiExportCatalogFailed || !canAsk}
                labels={aiExportLabels}
                showLabel={showActionLabels}
                onprepare={handleAiExport}
                oncopied={handleAiExportCopied}
                onerror={(error) => toasts.error(getAiExportErrorMessage($_, error))}
            />

            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 bg-lf-card border border-lf-subtle rounded-lg text-xs font-medium text-lf-secondary hover:bg-lf-hover transition-colors disabled:opacity-50"
                onclick={handleSync}
                disabled={pageBusy.busy}
                data-busy={pageBusy.busy ? 'true' : 'false'}
                data-testid="sync-button"
                title={$_('dashboard.syncData')}
            >
                <RefreshCw size={14} class={pageBusy.busy ? 'animate-spin' : ''} />
                {#if showActionLabels}
                    <span>{$_('dashboard.syncData')}</span>
                {/if}
            </button>
        {/snippet}
    </PageToolbar>

    <DataQualityBanner issues={dataQualityIssues} mode="grouped" onaction={handleBannerAction} busyCode={syncingCode} />

    {#if activeTab === 'panoramica'}
        <div class="space-y-4" data-testid="dashboard-overview-tab">
            <KpiSection {summary} {history} loading={summaryLoading} displayCurrency={appliedCurrency} />

            <!-- Cash Balances — same position as broker detail (right after the KPIs), using
                 summary.cash_balances which already aggregates by currency across all brokers
                 in scope (all accessible brokers, or the broker-filter subset if active). -->
            <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-subtle p-4" data-testid="dashboard-cash-balances">
                <div class="flex items-center space-x-2 text-lf-secondary mb-4">
                    <Wallet size={20} />
                    <h2 class="font-semibold">{$_('brokers.cashBalances')}</h2>
                </div>

                {#if summary?.cash_balances && summary.cash_balances.length > 0}
                    <div class="flex flex-wrap gap-2">
                        {#each [...summary.cash_balances].sort((a, b) => parseFloat(b.amount) - parseFloat(a.amount)) as balance}
                            <span class="inline-flex items-center px-3 py-1.5 bg-lf-panel rounded-lg text-sm font-medium text-lf-primary">
                                {@html formatCurrencyAmountHtml(parseFloat(balance.amount), balance.code)}
                            </span>
                        {/each}
                    </div>
                {:else}
                    <p class="text-lf-muted text-sm italic py-4 text-center">{$_('brokers.noCashBalances')}</p>
                {/if}
            </div>

            <!-- ── Charts Row ── -->
            <div class="grid grid-cols-1 lg:grid-cols-5 gap-4">
                <!-- Growth Chart — 3/5 -->
                <div class="lg:col-span-3">
                    <GrowthChart {history} range={historyRange} {mwrrLine} {brokerPnlHistory} {pnlCandles} onRequestPnlCandles={() => void pageBusy.join('dashboard-pnl-candles', loadPnlCandles)} {incomeHistory} {costHistory} {depositHistory} {acquisitionFunding} loading={historyLoading} baseCurrency={appliedCurrency} />
                </div>

                <!-- Allocation Panel — 2/5 -->
                <AllocationPanel {summary} loading={summaryLoading} displayCurrency={appliedCurrency} brokerIds={activeBrokerIds} currentLanguage={$currentLanguage} allocationHistory={allocationHistoryFromReport} />
            </div>
        </div>
    {:else if activeTab === 'posizioni'}
        <div data-testid="dashboard-positions-tab">
            {#if activeAssetId != null}
                <!-- «Lot detail» takes the place of the portfolio view; «← Portfolio» (or the browser's back) returns to it (#48). -->
                <div class="mb-3">
                    <button type="button" class="inline-flex items-center gap-1.5 rounded-lg border border-lf-subtle bg-lf-card px-2.5 py-1.5 text-xs font-medium text-lf-secondary transition-colors hover:bg-lf-hover" onclick={closeAssetPanel} data-testid="positions-back-to-portfolio">
                        <ArrowLeft size={14} />
                        {$_('dashboard.backToPortfolio')}
                    </button>
                </div>
                <LotsAnalysisPanel
                    open={true}
                    assetId={activeAssetId}
                    brokerIds={activeBrokerIds ?? allBrokers.map((b) => b.id)}
                    brokers={allBrokers}
                    currency={activeAsset?.currency ?? appliedCurrency}
                    assetName={activeAsset?.display_name ?? null}
                    onClose={closeAssetPanel}
                    ready={canAsk}
                    {refreshVersion}
                />
            {:else}
                <!-- F2: nothing is asked before the owned brokers are known — the prop arrives with them. -->
                <PositionsPanel
                    {summary}
                    contribution={positionsContribution}
                    loading={summaryLoading}
                    {contributionLoading}
                    {assetsHref}
                    brokers={allBrokers}
                    onRequestContribution={canAsk ? () => void pageBusy.join('dashboard-contribution', loadContribution) : undefined}
                    onAnalyze={openAssetPanel}
                    analyzedAssetId={activeAssetId}
                    portfolioHistory={history}
                    positionsSeries={$positionsSeriesCtl.response}
                    positionsSeriesLoading={$positionsSeriesCtl.loading}
                    positionsSeriesFailed={$positionsSeriesCtl.failed}
                    onRequestPositionsSeries={(keys) => positionsSeriesCtl.request(keys, positionsSeriesScope)}
                />
            {/if}
        </div>
    {:else if activeTab === 'rischio'}
        <div data-testid="dashboard-risk-tab">
            <!-- The risk scope is the *whole* portfolio — every broker the user owns (F2,
                 as the rest of the Dashboard) — even when a broker filter is on, which is
                 what the subtitle announces. Never without `broker_ids`: the backend would
                 widen it to every broker the user can see, editor and viewer ones included,
                 so the panel mounts only once the owned brokers are known. `summary` follows
                 the filter, so its net worth belongs to a different question: passing it
                 would print one broker's money beside every broker's risk. -->
            {#if canAsk}
                <RiskLevelsPanel
                    scope={{kind: 'portfolio', broker_ids: ownedBrokerIds}}
                    dateStart={dateRangeCtl.start}
                    dateEnd={dateRangeCtl.end}
                    targetCurrency={appliedCurrency}
                    assetIds={[...new Set((summary?.holdings ?? []).map((holding) => holding.asset_id))]}
                    scopeValue={brokerFilterActive || !summary ? null : parseFloat(summary.net_worth.amount)}
                    title={$_('risk.dashboardTitle')}
                    subtitle={brokerFilterActive ? $_('risk.dashboardFullPortfolio') : ''}
                    {refreshVersion}
                    onsynced={async () => {
                        invalidate();
                        await loadAll(true);
                    }}
                />
            {:else if brokersReady}
                <p class="py-12 text-center text-sm italic text-lf-muted" data-testid="dashboard-risk-no-owned">{$_('common.noData')}</p>
            {:else}
                <!-- Owned brokers still loading (cold load): say so instead of an empty tab. -->
                <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-subtle p-12 text-center" data-testid="dashboard-risk-loading">
                    <RefreshCw class="text-lf-link animate-spin mx-auto" size={28} />
                </div>
            {/if}
        </div>
    {:else if activeTab === 'transazioni'}
        <div data-testid="dashboard-transactions-tab">
            {#if txLoading && txMainRows.length === 0}
                <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-subtle p-12 text-center">
                    <RefreshCw class="text-lf-link animate-spin mx-auto" size={28} />
                </div>
            {:else}
                <TransactionsTable
                    mainRows={txMainRows}
                    partnerRows={txPartnerRows}
                    brokers={allBrokers}
                    eventTooltipMap={txEventTooltipMap}
                    currentPage={txCurrentPage}
                    hideActions={true}
                    onPageChange={(page) => (txCurrentPage = page)}
                    onViewRow={(row) => {
                        txViewItems = resolveFormItemsForView(row as TXReadItem, () => undefined, getBrokerRole);
                        txViewOpen = true;
                    }}
                />
            {/if}
        </div>
    {/if}
</div>

<!-- FxPairAddModal — opened from DataQualityBanner CTA -->
{#if showFxPairAddModal}
    {@const fxParts = fxPairCreateSlug.includes('-') ? fxPairCreateSlug.split('-') : fxPairCreateSlug.split('/')}
    <FxPairAddModal bind:open={showFxPairAddModal} initialBase={fxParts[0] ?? ''} initialQuote={fxParts[1] ?? ''} oncreated={handleFxPairCreated} onsynced={handleFxPairCreationSynced} />
{/if}

<!-- Transaction view modal — opened from the Transazioni tab's row double-click -->
<TransactionFormModal open={txViewOpen} mode="view" items={txViewItems} onClose={() => (txViewOpen = false)} />
