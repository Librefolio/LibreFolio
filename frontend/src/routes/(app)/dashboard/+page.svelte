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
    import {onMount, tick} from 'svelte';
    import {page} from '$app/stores';
    import {_} from '$lib/i18n';
    import {RefreshCw, Brain, Briefcase, TrendingUp, ArrowRightLeft, Wallet} from 'lucide-svelte';
    import {copyAiExport} from '$lib/features/ai-export/aiExportClipboard';
    import {toasts} from '$lib/stores/app/toastStore.svelte';

    import {fetchReport, invalidate, type PortfolioReport, type PortfolioSummary, type PortfolioHistoryPoint, type AllocationHistoryDimensions, type PositionsContribution} from '$lib/stores/portfolio/portfolioStore.svelte';
    import {ensureBrokersLoaded, getAllBrokers} from '$lib/stores/reference/brokerStore';
    import {ensureAssetsLoaded, getAssetInfo} from '$lib/stores/reference/assetStore';
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
    import PositionsPanel from '$lib/components/dashboard/PositionsPanel.svelte';
    import FIFOLotsPanel from '$lib/components/brokers/lots/FIFOLotsPanel.svelte';
    import {DataQualityBanner} from '$lib/components/ui/feedback';
    import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';
    import FxPairAddModal from '$lib/components/fx/FxPairAddModal.svelte';
    import {TransactionFormModal, TransactionsTable, resolveFormItemsForView, loadPartnerRows, loadEventTooltipMap, type FormModalItems} from '$lib/components/transactions';
    import type {TXReadItem, AssetEvent} from '$lib/components/transactions/types';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import {getBrokerRole} from '$lib/stores/reference/brokerStore';
    import {currentLanguage} from '$lib/stores/app/language';
    import {goto} from '$app/navigation';
    import {formatCurrencyAmountHtml} from '$lib/utils/currency/currencyFormat';
    import {zodiosApi} from '$lib/api';
    import {buildTransactionsFiltersUrl} from '../transactions/filterState';

    // =========================================================================
    // State
    // =========================================================================

    let summary = $state<PortfolioSummary | null>(null);
    let history = $state<PortfolioHistoryPoint[]>([]);
    let allocationHistoryFromReport = $state<AllocationHistoryDimensions | null>(null);
    let positionsContribution = $state<PositionsContribution | null>(null);
    let contributionLoading = $state(false);
    let reportLoading = $state(true);
    /** True only on first load when no data exists yet. Once data is loaded, subsequent fetches are "refreshing". */
    let summaryLoading = $derived(reportLoading && !summary);
    let historyLoading = $derived(reportLoading && history.length === 0);
    let syncLoading = $state(false);

    /** AI export state */
    let aiExportLoading = $state(false);
    let aiExportDropdownOpen = $state(false);
    let aiExportTriggerEl = $state<HTMLElement | null>(null);
    let aiExportPanelEl = $state<HTMLDivElement | null>(null);
    let aiExportDropdownPosition = $state({left: 8, top: 8});

    /** Broker IDs selected in the filter (empty = all brokers). */
    let selectedBrokerIds = $state<number[]>([]);
    let allBrokers = $state<BrokerLike[]>([]);

    /** FIFO lots analysis panel (Posizioni tab) — mirrors brokers/[id]/+page.svelte's pattern
     *  but in runes syntax (this file is Svelte 5 runes throughout, unlike the legacy broker
     *  detail page). Scope defaults to ALL accessible brokers when no broker filter is active
     *  (activeBrokerIds undefined = "All Brokers"), so the panel analyzes the same asset across
     *  every broker that holds it — see plan_ui_broker_holdings.md multi-broker evolution. */
    let activeAssetId = $state<number | null>(null);
    $effect(() => {
        const paramAssetId = getAssetPanelAssetId($page.url.searchParams) ?? null;
        if (paramAssetId !== activeAssetId) activeAssetId = paramAssetId;
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

    /** Display currency override — always concrete, defaults to user base currency. */
    let targetCurrency = $state($globalSettings.default_currency || 'EUR');
    let targetCurrencyManuallySet = $state(false);

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
    const displayCurrency = $derived(targetCurrency || baseCurrency);

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

    /** Which broker IDs to pass to the API (undefined = all). */
    const activeBrokerIds = $derived(!allBrokersSelected && selectedBrokerIds.length > 0 ? selectedBrokerIds : undefined);

    /** Whether the filter is "active" (some but not all brokers selected). */
    const brokerFilterActive = $derived(selectedBrokerIds.length > 0 && !allBrokersSelected);

    /** Broker filter trigger label — follows assets-page type-filter pattern (no separate badge). */
    const brokerFilterLabel = $derived(brokerFilterActive ? (selectedBrokerIds.length === 1 ? (allBrokers.find((b) => b.id === selectedBrokerIds[0])?.name ?? String(selectedBrokerIds[0])) : `${$_('brokers.title')} (${selectedBrokerIds.length})`) : $_('dashboard.allBrokers'));

    const dataQualityIssues = $derived<DataQualityIssue[]>((summary?.data_quality as {issues?: DataQualityIssue[]} | undefined)?.issues ?? []);

    /** Tab navigation — mirrors the broker detail page's structure (no "Info" tab
     *  here: there's no portfolio-wide metadata/sharing concept at this level). */
    const DASHBOARD_TAB_IDS = ['panoramica', 'posizioni', 'transazioni'] as const;
    type DashboardTabId = (typeof DASHBOARD_TAB_IDS)[number];
    const DEFAULT_DASHBOARD_TAB: DashboardTabId = 'panoramica';

    function isDashboardTabId(tabId: string): tabId is DashboardTabId {
        return DASHBOARD_TAB_IDS.includes(tabId as DashboardTabId);
    }

    let activeTab = $state<DashboardTabId>(DEFAULT_DASHBOARD_TAB);
    const dashboardTabs = $derived([
        {id: 'panoramica', label: $_('brokers.overview'), icon: Briefcase, testId: 'dashboard-tab-panoramica'},
        {id: 'posizioni', label: $_('brokers.positions'), icon: TrendingUp, testId: 'dashboard-tab-posizioni'},
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

    function handleBannerAction(action: string, target: string | null, _issue: DataQualityIssue) {
        if (action === 'navigate_asset' && target) {
            goto(`/assets/${target}`);
        } else if (action === 'navigate_fx' && target) {
            goto(`/fx/${target}`);
        } else if (action === 'add_fx_pair') {
            // Open modal — use first affected pair as slug hint
            const pairs = _issue.affected_fx_pairs ?? [];
            fxPairCreateSlug = pairs[0] ?? '';
            showFxPairAddModal = true;
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

    async function loadAll(force = false) {
        reportLoading = true;
        try {
            const report = await fetchReport(activeBrokerIds, dateRangeCtl.start || undefined, dateRangeCtl.end || undefined, targetCurrency, force);
            // Cast from the Zodios union types to the concrete types the dashboard expects
            summary = (report?.summary as PortfolioSummary | null | undefined) ?? null;
            history = (report?.history as PortfolioHistoryPoint[] | null | undefined) ?? [];
            allocationHistoryFromReport = (report?.allocation_history as AllocationHistoryDimensions | null | undefined) ?? null;
            // Contribution data comes from the same report when requested
            positionsContribution = (report?.positions_contribution as PositionsContribution | null | undefined) ?? null;
            resolveMaxStartFromHistory();
        } finally {
            reportLoading = false;
        }
    }

    /** Lazy-load contribution data (called when user switches to Contribution view). */
    async function loadContribution() {
        if (positionsContribution || contributionLoading) return;
        contributionLoading = true;
        try {
            // includeHistory/includeAllocationHistory=false: only positions_contribution is read below.
            const report = await fetchReport(activeBrokerIds, dateRangeCtl.start || undefined, dateRangeCtl.end || undefined, targetCurrency, false, true, false, false, false);
            positionsContribution = (report?.positions_contribution as PositionsContribution | null | undefined) ?? null;
        } finally {
            contributionLoading = false;
        }
    }

    // =========================================================================
    // Event handlers
    // =========================================================================

    function toggleBroker(id: number) {
        if (selectedBrokerIds.includes(id)) {
            selectedBrokerIds = selectedBrokerIds.filter((x) => x !== id);
        } else {
            selectedBrokerIds = [...selectedBrokerIds, id];
        }
        scheduleReload();
    }

    /** Fires loadAll after a 2-second quiet period (anti-bounce for rapid clicks). */
    function scheduleReload() {
        if (reloadTimer !== null) clearTimeout(reloadTimer);
        reloadTimer = setTimeout(() => {
            reloadTimer = null;
            void loadAll();
        }, 2000);
    }

    async function handleSync() {
        syncLoading = true;
        invalidate();
        await loadAll(true);
        syncLoading = false;
    }

    async function handleAiExport(mode: 'full' | 'data-only') {
        aiExportDropdownOpen = false;
        aiExportLoading = true;
        try {
            await copyAiExport(
                mode,
                {
                    brokerIds: activeBrokerIds ?? undefined,
                    dateFrom: dateRangeCtl.start || undefined,
                    dateTo: dateRangeCtl.end || undefined,
                    targetCurrency: targetCurrency,
                    locale: $currentLanguage,
                },
                toasts,
                $_,
            );
        } finally {
            aiExportLoading = false;
        }
    }

    async function positionBrokerFilterDropdown() {
        await tick();
        if (!brokerFilterOpen) return;
        brokerFilterDropdownPosition = getFixedDropdownPosition(brokerFilterTriggerEl, brokerFilterPanelEl, 'start');
    }

    async function positionAiExportDropdown() {
        await tick();
        if (!aiExportDropdownOpen) return;
        aiExportDropdownPosition = getFixedDropdownPosition(aiExportTriggerEl, aiExportPanelEl, 'end');
    }

    function updateOpenDropdownPositions() {
        if (brokerFilterOpen) {
            brokerFilterDropdownPosition = getFixedDropdownPosition(brokerFilterTriggerEl, brokerFilterPanelEl, 'start');
        }
        if (aiExportDropdownOpen) {
            aiExportDropdownPosition = getFixedDropdownPosition(aiExportTriggerEl, aiExportPanelEl, 'end');
        }
    }

    function toggleBrokerFilterDropdown() {
        brokerFilterOpen = !brokerFilterOpen;
        if (brokerFilterOpen) void positionBrokerFilterDropdown();
    }

    function toggleAiExportDropdown() {
        aiExportDropdownOpen = !aiExportDropdownOpen;
        if (aiExportDropdownOpen) void positionAiExportDropdown();
    }

    // Outside-click closes broker filter panel and AI export dropdown
    function handleDocumentClick(e: MouseEvent) {
        if (aiExportDropdownOpen) {
            const target = e.target as HTMLElement;
            if (!target.closest?.('[data-ai-export-panel]') && !target.closest?.('[data-testid="ai-export-button"]')) {
                aiExportDropdownOpen = false;
            }
        }
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
        if (!aiExportDropdownOpen) return;
        void positionAiExportDropdown();
    });

    $effect(() => {
        if (!brokerFilterOpen && !aiExportDropdownOpen) return;

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

    onMount(() => {
        document.addEventListener('click', handleDocumentClick);
        void (async () => {
            await Promise.all([ensureBrokersLoaded(), ensureAssetsLoaded()]);
            allBrokers = getAllBrokers();
            await loadAll();
        })();
        return () => document.removeEventListener('click', handleDocumentClick);
    });
</script>

<div class="space-y-4" data-testid="dashboard-page">
    <h1 class="sr-only">{$_('nav.dashboard')}</h1>

    <PageToolbar
        thresholds={{oneRow: 1000, denseRow: 810, stackFilters: 430, oneColumn: 390, noExtraLabel: 410, labelHideActions: 210, labelHideTabs: 370}}
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
                            dropdownPosition="bottom"
                            placeholder={baseCurrency}
                            onchange={() => {
                                targetCurrencyManuallySet = true;
                                void loadAll();
                            }}
                        />
                    </div>
                </div>

                <!-- Broker multi-select panel -->
                <div class="relative">
                    <button
                        bind:this={brokerFilterTriggerEl}
                        class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors whitespace-nowrap
                       {brokerFilterActive ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-700' : 'bg-white dark:bg-slate-700 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-600'}"
                        onclick={toggleBrokerFilterDropdown}
                        data-testid="broker-filter-trigger"
                    >
                        {brokerFilterLabel}
                        <svg class="w-3 h-3 transition-transform {brokerFilterOpen ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
                                    onclick={() => {
                                        selectedBrokerIds = allBrokers.map((b) => b.id);
                                        scheduleReload();
                                    }}>{$_('common.selectAll')}</button
                                >
                                <button
                                    type="button"
                                    class="flex-1 px-2 py-1 text-[11px] font-medium border border-gray-200 dark:border-slate-600 rounded bg-gray-50 dark:bg-slate-900 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
                                    onclick={() => {
                                        selectedBrokerIds = [];
                                        scheduleReload();
                                    }}>{$_('common.clearAll')}</button
                                >
                            </div>
                            <!-- Broker list -->
                            <div class="max-h-52 overflow-y-auto mx-2.5 my-2 space-y-0.5">
                                {#each allBrokers as broker (broker.id)}
                                    {@const isSelected = selectedBrokerIds.includes(broker.id)}
                                    <button
                                        type="button"
                                        class="flex items-center gap-2 w-full px-2 py-1.5 text-left text-[13px] rounded hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors {isSelected ? 'text-blue-700 dark:text-blue-300' : 'text-gray-600 dark:text-gray-300'}"
                                        onclick={() => toggleBroker(broker.id)}
                                        data-testid="broker-filter-item-{broker.id}"
                                    >
                                        <BrokerIcon brokerId={broker.id} iconUrl={broker.icon_url} portalUrl={broker.portal_url} pluginCode={broker.default_import_plugin} altText={broker.name} size={16} />
                                        <span class="flex-1 truncate">{broker.name}</span>
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
            <div class="relative w-full">
                <button
                    bind:this={aiExportTriggerEl}
                    class="flex items-center justify-center gap-2 w-full px-3 py-1.5 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-600 transition-colors disabled:opacity-50"
                    onclick={toggleAiExportDropdown}
                    disabled={aiExportLoading}
                    data-testid="ai-export-button"
                    title={$_('dashboard.aiExport')}
                >
                    <Brain size={14} class={aiExportLoading ? 'animate-pulse' : ''} />
                    {#if showActionLabels}
                        <span>{aiExportLoading ? $_('dashboard.aiExportBuilding') : $_('dashboard.aiExport')}</span>
                    {/if}
                </button>

                {#if aiExportDropdownOpen}
                    <div
                        bind:this={aiExportPanelEl}
                        class="fixed z-50 w-56 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg overflow-hidden"
                        style:left={`${aiExportDropdownPosition.left}px`}
                        style:top={`${aiExportDropdownPosition.top}px`}
                        data-ai-export-panel
                    >
                        <button type="button" class="flex items-center gap-2 w-full px-3 py-2.5 text-left text-[13px] text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors" onclick={() => handleAiExport('full')} data-testid="ai-export-full">
                            <Brain size={14} class="text-purple-500" />
                            {$_('dashboard.aiExportFull')}
                        </button>
                        <button
                            type="button"
                            class="flex items-center gap-2 w-full px-3 py-2.5 text-left text-[13px] text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors border-t border-gray-100 dark:border-slate-700"
                            onclick={() => handleAiExport('data-only')}
                            data-testid="ai-export-data-only"
                        >
                            <svg class="w-3.5 h-3.5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
                            </svg>
                            {$_('dashboard.aiExportDataOnly')}
                        </button>
                    </div>
                {/if}
            </div>

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

    <DataQualityBanner issues={dataQualityIssues} mode="grouped" onaction={handleBannerAction} />

    {#if activeTab === 'panoramica'}
        <div class="space-y-4" data-testid="dashboard-overview-tab">
            <KpiSection {summary} {history} loading={summaryLoading} {displayCurrency} />

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
                    <GrowthChart {history} loading={historyLoading} baseCurrency={displayCurrency} />
                </div>

                <!-- Allocation Panel — 2/5 -->
                <AllocationPanel {summary} loading={summaryLoading} {displayCurrency} brokerIds={activeBrokerIds} currentLanguage={$currentLanguage} allocationHistory={allocationHistoryFromReport} />
            </div>
        </div>
    {:else if activeTab === 'posizioni'}
        <div data-testid="dashboard-positions-tab">
            <PositionsPanel {summary} contribution={positionsContribution} loading={summaryLoading} {contributionLoading} {assetsHref} brokers={allBrokers} onRequestContribution={loadContribution} onAnalyze={openAssetPanel} />
            <FIFOLotsPanel
                open={activeAssetId != null}
                assetId={activeAssetId}
                brokerIds={activeBrokerIds ?? allBrokers.map((b) => b.id)}
                brokers={allBrokers}
                dateFrom={dateRangeCtl.start}
                dateTo={dateRangeCtl.end}
                isAllPeriod={dateRangeCtl.activePreset === 'MAX'}
                currency={activeAssetId != null ? (getAssetInfo(activeAssetId)?.currency ?? displayCurrency) : displayCurrency}
                assetName={activeAssetId != null ? getAssetInfo(activeAssetId)?.display_name : null}
                onClose={closeAssetPanel}
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
    <FxPairAddModal
        bind:open={showFxPairAddModal}
        initialBase={fxParts[0] ?? ''}
        initialQuote={fxParts[1] ?? ''}
        oncreated={() => {
            invalidate();
            loadAll();
        }}
    />
{/if}

<!-- Transaction view modal — opened from the Transazioni tab's row double-click -->
<TransactionFormModal open={txViewOpen} mode="view" items={txViewItems} onClose={() => (txViewOpen = false)} />
