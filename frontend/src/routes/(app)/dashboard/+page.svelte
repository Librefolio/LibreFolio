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
    import {RefreshCw, Briefcase, TrendingUp, ArrowRightLeft, Wallet, Shield} from 'lucide-svelte';
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
    import {requestPortfolioRefresh} from '$lib/stores/portfolio/portfolioMutation';
    import {readDashboardView, writeDashboardView} from '$lib/stores/portfolio/dashboardViewStore';
    import {setTweenHydration} from '$lib/components/ui/TweenedValue.svelte';
    import {ensureAssetsLoaded, getAssetInfo, assetStoreVersion} from '$lib/stores/reference/assetStore';
    import {getAssetPanelAssetId, buildAssetPanelUrl} from '$lib/utils/broker/assetPanelUrl';
    import {buildTabUrl, getResolvedTabParam} from '$lib/utils/url/tabUrl';
    import {globalSettings} from '$lib/stores/app/globalSettings';
    import {createDateRangeController} from '$lib/stores/dateRangeController.svelte';
    import PageToolbar from '$lib/components/ui/toolbar/PageToolbar.svelte';
    import {getFixedDropdownPosition} from '$lib/utils/layout/dropdownPosition';
    import DateRangePicker from '$lib/components/ui/date/DateRangePicker.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import AllocationPanel from '$lib/components/dashboard/AllocationPanel.svelte';
    import GrowthChart from '$lib/components/dashboard/GrowthChart.svelte';
    import KpiSection from '$lib/components/dashboard/KpiSection.svelte';
    import RiskLevelsPanel from '$lib/components/risk/levels/RiskLevelsPanel.svelte';
    import PositionsPanel from '$lib/components/dashboard/PositionsPanel.svelte';
    import LotsAnalysisPanel from '$lib/components/brokers/lots/LotsAnalysisPanel.svelte';
    import {DataQualityBanner} from '$lib/components/ui/feedback';
    import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';
    import FxPairAddModal from '$lib/components/fx/FxPairAddModal.svelte';
    import {invalidateFxRoutes} from '$lib/stores/reference/fxRoutesStore';
    import {getClientSessionGeneration, isClientSessionCurrent} from '$lib/stores/app/clientSession';
    import {classifyFxSyncOutcome, formatFxSyncResult, FX_SYNC_TIMEOUT_MS, type FxPairSyncCompleteDetail, type FxSyncResponse} from '$lib/services/fxCreationSync';
    import {TransactionFormModal, TransactionsTable, resolveFormItemsForView, loadPartnerRows, loadEventTooltipMap, type FormModalItems} from '$lib/components/transactions';
    import type {TXReadItem, AssetEvent} from '$lib/components/transactions/types';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
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

    function openAssetPanel(assetId: number) {
        void goto(buildAssetPanelUrl($page.url, assetId), {replaceState: true, noScroll: true});
    }

    function closeAssetPanel() {
        void goto(buildAssetPanelUrl($page.url, null), {replaceState: true, noScroll: true});
    }

    /** Debounce timer for broker filter changes. */
    let reloadTimer = $state<ReturnType<typeof setTimeout> | null>(null);

    /**
     * Date range — backed by global store (shared with assets/fx pages) via the
     * shared dateRangeController (owns the seed/display/isMaxPending bookkeeping
     * that used to be duplicated per-page — see dateRangeController.svelte.ts).
     */
    const dateRangeCtl = createDateRangeController(() => void loadAll());

    /**
     * Sentinel-aware values for building "See all" links (assets/transactions).
     * While "All" is the active selection, these stay "min"/"max" (generic)
     * instead of a concrete resolved date, for the lifetime of the selection.
     */
    let urlDateFrom = $derived(dateRangeCtl.activePreset === 'MAX' ? 'min' : dateRangeCtl.start);
    let urlDateTo = $derived(dateRangeCtl.activePreset === 'MAX' ? 'max' : dateRangeCtl.end);

    /** Display currency override — always concrete, defaults to user base currency (or the one the user left). */
    const initialCurrency = restoredView.targetCurrency ?? ($globalSettings.default_currency || 'EUR');
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

    const baseCurrency = $derived($globalSettings.default_currency || 'EUR');

    $effect(() => {
        if (targetCurrencyManuallySet || targetCurrency === baseCurrency) return;
        const hadLoadedData = summary !== null || history.length > 0;
        targetCurrency = baseCurrency;
        // Guard: don't stack a second overlapping loadAll() if one triggered by onMount
        // (or a prior currency change) is still in flight — avoids duplicate concurrent
        // fetches racing to reassign summary/history while the user may be interacting
        // with the page (e.g. clicking a card whose click depends on stable DOM state).
        if (hadLoadedData && !reportLoading) void loadAll(true);
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
    onDestroy(() => {
        pageAlive = false;
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
            void loadTransactions();
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
            // Open modal — use first affected pair as slug hint
            const pairs = _issue.affected_fx_pairs ?? [];
            fxPairCreateSlug = pairs[0] ?? '';
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
     */
    let loadSeq = 0;

    async function loadAll(force = false, propagateError = false) {
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
        if (showCachedContribution()) void loadContribution();
        if (!request) {
            reportLoading = false;
            return;
        }

        reportLoading = true;
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
        await loadAll(true);
    }

    async function handleFxPairCreationSynced(detail: FxPairSyncCompleteDetail) {
        if (!pageAlive || !isClientSessionCurrent(detail.sessionGeneration)) return;
        // The sync interceptor marks portfolio/risk caches stale at commit time, when it wrote something.
        await loadAll(true, true);
    }

    /**
     * The contribution of the scope on screen: asked by PositionsPanel when its Performance view has
     * none, and by `loadAll` when the cached one is stale — then in background, with the cached rows
     * kept on screen (`contributionRefreshing`, not the skeleton of `contributionLoading`).
     */
    async function loadContribution() {
        if (!canAsk || contributionLoading || contributionRefreshing) return;
        const requested = targetCurrency;
        const brokerIds = activeBrokerIds;
        const start = dateRangeCtl.start || undefined;
        const end = dateRangeCtl.end || undefined;
        const scope = () => `${activeBrokerIds?.join(',')}|${dateRangeCtl.start}|${dateRangeCtl.end}|${targetCurrency}`;
        const askedScope = scope();
        const cached = peekReport(brokerIds, start, end, requested, true, false, false, false);
        if (cached && !cached.stale) {
            setContribution(cached.report);
            return;
        }
        if (cached) contributionRefreshing = true;
        else contributionLoading = true;
        try {
            // includeHistory/includeAllocationHistory=false: only positions_contribution is read below.
            const report = await fetchReport(brokerIds, start, end, requested, false, true, false, false, false);
            if (!pageAlive || scope() !== askedScope) return;
            if (report) {
                setContribution(report);
                appliedCurrency = requested;
            } else if (!cached) {
                setContribution(null);
            }
        } finally {
            contributionLoading = false;
            contributionRefreshing = false;
        }
    }

    /** Lazy-load the synthetic P&L candle series (G1b — called by GrowthChart's
     *  onRequestPnlCandles when the user first activates the candles submode; caller
     *  policy per plan §4.1: "expensive OHLC work stays off ordinary reports"). */
    async function loadPnlCandles() {
        if (!canAsk || pnlCandles || pnlCandlesLoading) return;
        pnlCandlesLoading = true;
        const requested = targetCurrency;
        try {
            // includeHistory/includeAllocationHistory/includeContribution/includeBreakdown=false:
            // only pnl_candles is read below.
            const report = await fetchReport(activeBrokerIds, dateRangeCtl.start || undefined, dateRangeCtl.end || undefined, requested, false, false, false, false, false, {includePnlCandles: true});
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
            void loadAll();
        }, 2000);
    }

    /** «Aggiorna» (E4): report, contribution, risk and lots are all asked again; what is on screen stays meanwhile. */
    async function handleSync() {
        syncLoading = true;
        requestPortfolioRefresh();
        refreshVersion += 1;
        try {
            await loadAll(true);
        } finally {
            syncLoading = false;
        }
    }

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
    // tab is left out until its panel says so itself (its cards come from the risk cache, not from
    // this report).
    setTweenHydration(() => summary !== null && activeTab !== 'rischio');
    hydrateFromCache();

    onMount(() => {
        document.addEventListener('click', handleDocumentClick);
        void loadAiExportCompatibility();
        void (async () => {
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
        })();
        return () => document.removeEventListener('click', handleDocumentClick);
    });
</script>

<div class="space-y-4" data-testid="dashboard-page" use:guideAnchor={'page.dashboard'} aria-busy={reportLoading || contributionLoading || contributionRefreshing || syncLoading} data-busy={reportLoading || contributionLoading || contributionRefreshing || syncLoading ? 'true' : 'false'}>
    <h1 class="sr-only">{$_('nav.dashboard')}</h1>

    <PageToolbar
        thresholds={{oneRow: 1000, denseRow: 950, stackFilters: 510, oneColumn: 390, noExtraLabel: 410, labelHideActions: 210, labelHideTabs: 460}}
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
                <div class="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
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
                                void loadAll();
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
                       {brokerFilterActive ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-700' : 'bg-white dark:bg-slate-700 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-600'}"
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
                            class="fixed z-50 w-56 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg overflow-hidden"
                            style:left={`${brokerFilterDropdownPosition.left}px`}
                            style:top={`${brokerFilterDropdownPosition.top}px`}
                            data-broker-filter-panel
                        >
                            <!-- Select All / Deselect All -->
                            <div class="flex gap-2 px-2.5 py-2 border-b border-gray-100 dark:border-slate-700">
                                <button
                                    type="button"
                                    class="flex-1 px-2 py-1 text-[11px] font-medium border border-gray-200 dark:border-slate-600 rounded bg-gray-50 dark:bg-slate-900 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
                                    onclick={() => selectBrokers(allBrokers.map((b) => b.id))}>{$_('common.selectAll')}</button
                                >
                                <button
                                    type="button"
                                    class="flex-1 px-2 py-1 text-[11px] font-medium border border-gray-200 dark:border-slate-600 rounded bg-gray-50 dark:bg-slate-900 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
                                    onclick={() => selectBrokers([])}>{$_('common.clearAll')}</button
                                >
                            </div>
                            <!-- Broker list -->
                            <div class="max-h-52 overflow-y-auto mx-2.5 my-2 space-y-0.5">
                                {#each allBrokers as broker (broker.id)}
                                    {@const isSelected = selectedBrokerIds.includes(broker.id)}
                                    {@const role = getBrokerRole(broker.id)}
                                    {@const RoleIcon = role ? getRoleIcon(role) : null}
                                    <button
                                        type="button"
                                        class="flex items-center gap-2 w-full px-2 py-1.5 text-left text-[13px] rounded hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors {isSelected ? 'text-blue-700 dark:text-blue-300' : 'text-gray-600 dark:text-gray-300'}"
                                        onclick={() => toggleBroker(broker.id)}
                                        data-testid="broker-filter-item-{broker.id}"
                                    >
                                        <BrokerIcon brokerId={broker.id} iconUrl={broker.icon_url} portalUrl={broker.portal_url} pluginCode={broker.default_import_plugin} altText={broker.name} size={16} />
                                        <span class="flex-1 truncate">{broker.name}</span>
                                        {#if RoleIcon}
                                            <RoleIcon size={14} class={getRoleIconColor(role)} />
                                        {/if}
                                        {#if isSelected}
                                            <svg class="w-3.5 h-3.5 text-blue-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
                disabled={aiExportCatalogLoading || aiExportCatalogFailed}
                labels={aiExportLabels}
                showLabel={showActionLabels}
                onprepare={handleAiExport}
                oncopied={handleAiExportCopied}
                onerror={(error) => toasts.error(getAiExportErrorMessage($_, error))}
            />

            <button
                class="flex items-center justify-center gap-2 px-3 py-1.5 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-600 transition-colors disabled:opacity-50"
                onclick={handleSync}
                disabled={syncLoading}
                data-testid="sync-button"
                title={$_('dashboard.syncData')}
            >
                <RefreshCw size={14} class={syncLoading ? 'animate-spin' : ''} />
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
            <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 p-4" data-testid="dashboard-cash-balances">
                <div class="flex items-center space-x-2 text-gray-700 dark:text-gray-200 mb-4">
                    <Wallet size={20} />
                    <h2 class="font-semibold">{$_('brokers.cashBalances')}</h2>
                </div>

                {#if summary?.cash_balances && summary.cash_balances.length > 0}
                    <div class="flex flex-wrap gap-2">
                        {#each [...summary.cash_balances].sort((a, b) => parseFloat(b.amount) - parseFloat(a.amount)) as balance}
                            <span class="inline-flex items-center px-3 py-1.5 bg-gray-50 dark:bg-slate-700 rounded-lg text-sm font-medium text-gray-800 dark:text-gray-100">
                                {@html formatCurrencyAmountHtml(parseFloat(balance.amount), balance.code)}
                            </span>
                        {/each}
                    </div>
                {:else}
                    <p class="text-gray-400 dark:text-gray-500 text-sm italic py-4 text-center">{$_('brokers.noCashBalances')}</p>
                {/if}
            </div>

            <!-- ── Charts Row ── -->
            <div class="grid grid-cols-1 lg:grid-cols-5 gap-4">
                <!-- Growth Chart — 3/5 -->
                <div class="lg:col-span-3">
                    <GrowthChart {history} {brokerPnlHistory} {pnlCandles} onRequestPnlCandles={loadPnlCandles} {incomeHistory} {costHistory} {depositHistory} {acquisitionFunding} loading={historyLoading} baseCurrency={appliedCurrency} />
                </div>

                <!-- Allocation Panel — 2/5 -->
                <AllocationPanel {summary} loading={summaryLoading} displayCurrency={appliedCurrency} brokerIds={activeBrokerIds} currentLanguage={$currentLanguage} allocationHistory={allocationHistoryFromReport} />
            </div>
        </div>
    {:else if activeTab === 'posizioni'}
        <div data-testid="dashboard-positions-tab">
            <!-- F2: nothing is asked before the owned brokers are known — the prop arrives with them. -->
            <PositionsPanel {summary} contribution={positionsContribution} loading={summaryLoading} {contributionLoading} {assetsHref} brokers={allBrokers} onRequestContribution={canAsk ? loadContribution : undefined} onAnalyze={openAssetPanel} analyzedAssetId={activeAssetId} />
            <LotsAnalysisPanel
                open={activeAssetId != null}
                assetId={activeAssetId}
                brokerIds={activeBrokerIds ?? allBrokers.map((b) => b.id)}
                brokers={allBrokers}
                currency={activeAsset?.currency ?? appliedCurrency}
                assetName={activeAsset?.display_name ?? null}
                onClose={closeAssetPanel}
                ready={canAsk}
                {refreshVersion}
            />
        </div>
    {:else if activeTab === 'rischio'}
        <div data-testid="dashboard-risk-tab">
            <!-- The risk scope is the *whole* portfolio even when a broker filter
                 is on, which is what the subtitle announces. `summary` follows the
                 filter, so its net worth belongs to a different question: passing
                 it would print one broker's money beside every broker's risk. -->
            <RiskLevelsPanel
                scope={{kind: 'portfolio'}}
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
        </div>
    {:else if activeTab === 'transazioni'}
        <div data-testid="dashboard-transactions-tab">
            {#if txLoading && txMainRows.length === 0}
                <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 p-12 text-center">
                    <RefreshCw class="text-libre-green animate-spin mx-auto" size={28} />
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
