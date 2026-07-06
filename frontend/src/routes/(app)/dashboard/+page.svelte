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
    import {onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {RefreshCw, Brain, Briefcase, TrendingUp, ArrowRightLeft, Wallet} from 'lucide-svelte';
    import TabBar from '$lib/components/ui/tabs/TabBar.svelte';
    import {copyAiExport} from '$lib/features/ai-export/aiExportClipboard';
    import {toasts} from '$lib/stores/app/toastStore.svelte';

    import {fetchReport, invalidate, type PortfolioReport, type PortfolioSummary, type PortfolioHistoryPoint, type AllocationHistoryDimensions, type PositionsContribution} from '$lib/stores/portfolio/portfolioStore.svelte';
    import {ensureBrokersLoaded, getAllBrokers} from '$lib/stores/reference/brokerStore';
    import {globalSettings} from '$lib/stores/app/globalSettings';
    import {getStart, getEnd, setDateRange, resolveDateSentinel, isMaxSentinel} from '$lib/stores/dateRangeStore.svelte';
    import {createResponsiveLayout} from '$lib/utils/layout/responsiveLayout.svelte';
    import DateRangePicker from '$lib/components/ui/date/DateRangePicker.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import AllocationPanel from '$lib/components/dashboard/AllocationPanel.svelte';
    import GrowthChart from '$lib/components/dashboard/GrowthChart.svelte';
    import KpiSection from '$lib/components/dashboard/KpiSection.svelte';
    import RecentTransactionsPanel from '$lib/components/dashboard/RecentTransactionsPanel.svelte';
    import PositionsPanel from '$lib/components/dashboard/PositionsPanel.svelte';
    import {DataQualityBanner} from '$lib/components/ui/feedback';
    import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';
    import FxPairAddModal from '$lib/components/fx/FxPairAddModal.svelte';
    import {TransactionFormModal, resolveFormItemsForView, type FormModalItems} from '$lib/components/transactions';
    import type {TXReadItem} from '$lib/components/transactions/types';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import {getBrokerRole} from '$lib/stores/reference/brokerStore';
    import {currentLanguage} from '$lib/stores/app/language';
    import {goto} from '$app/navigation';
    import {formatCurrencyAmountHtml} from '$lib/utils/currency/currencyFormat';

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

    /** Broker IDs selected in the filter (empty = all brokers). */
    let selectedBrokerIds = $state<number[]>([]);
    let allBrokers = $state<BrokerLike[]>([]);

    /** Debounce timer for broker filter changes. */
    let reloadTimer = $state<ReturnType<typeof setTimeout> | null>(null);

    /**
     * Date range — backed by global store (shared with assets/fx pages).
     * dateFrom/dateTo are ALWAYS a concrete, resolved date (sentinels resolved
     * immediately) — used everywhere internally (report queries, AI export).
     * displayDateFrom is the ONLY thing bound to the picker; it shows the
     * literal "min" sentinel (pending label) until the real earliest date is
     * extracted from the loaded portfolio history (see loadAll).
     */
    let dateFrom = $state(resolveDateSentinel(getStart()));
    let dateTo = $state(resolveDateSentinel(getEnd()));
    const initialIsMaxPending = isMaxSentinel(getStart());
    let isMaxPending = $state(initialIsMaxPending);
    // Seeded from the plain `initialIsMaxPending`/`dateFrom`'s initial value above (not from
    // the isMaxPending/dateFrom $state bindings) to avoid a state_referenced_locally warning —
    // displayDateFrom is manually resynced elsewhere and bound bidirectionally to
    // DateRangePicker, so it's intentionally NOT a pure $derived of dateFrom/isMaxPending.
    let displayDateFrom = $state(initialIsMaxPending ? 'min' : resolveDateSentinel(getStart()));
    /** Bound to the picker so the "All" badge stays highlighted regardless of dateFrom/isMaxPending resolving to a concrete date. */
    let activePreset: any = $state(initialIsMaxPending ? 'MAX' : null);

    /**
     * Sentinel-aware values for building "See all" links (assets/transactions).
     * While "All" is the active selection, these stay "min"/"max" (generic)
     * instead of a concrete resolved date, for the lifetime of the selection.
     */
    let urlDateFrom = $derived(activePreset === 'MAX' ? 'min' : dateFrom);
    let urlDateTo = $derived(activePreset === 'MAX' ? 'max' : dateTo);

    /** Display currency override — always concrete, defaults to user base currency. */
    let targetCurrency = $state($globalSettings.default_currency || 'EUR');
    let targetCurrencyManuallySet = $state(false);

    /** Broker filter dropdown open state. */
    let brokerFilterOpen = $state(false);
    let brokerFilterTriggerEl = $state<HTMLButtonElement | null>(null);

    /** Filter bar ref — for ResizeObserver. */
    let filterBarRef = $state<HTMLDivElement | null>(null);

    /** Responsive layout — same utility as assets/fx pages. */
    const layout = createResponsiveLayout({wide: 900, tablet: 660, tabletS: 480, labelHide: 460});

    $effect(() => {
        const el = filterBarRef;
        if (!el) return;
        layout.attach(el);
        return () => layout.detach();
    });

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
    let activeTab = $state('panoramica');
    const dashboardTabs = $derived([
        {id: 'panoramica', label: $_('brokers.overview'), icon: Briefcase, testId: 'dashboard-tab-panoramica'},
        {id: 'posizioni', label: $_('brokers.positions'), icon: TrendingUp, testId: 'dashboard-tab-posizioni'},
        {id: 'transazioni', label: $_('transactions.title'), icon: ArrowRightLeft, testId: 'dashboard-tab-transazioni'},
    ]);

    /** FxPairAddModal state for CTA-driven pair creation */
    let showFxPairAddModal = $state(false);
    let fxPairCreateSlug = $state('');

    /** Transaction view modal state (opened from RecentTransactionsPanel double-click). */
    let txViewOpen = $state(false);
    let txViewItems = $state<FormModalItems | null>(null);

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

    /** URL for "See all" assets link — preserves current date range. */
    const assetsHref = $derived(`/assets?start=${urlDateFrom}&end=${urlDateTo}`);
    const transactionsHref = $derived(`/transactions?start=${urlDateFrom}&end=${urlDateTo}`);

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
     * from the just-loaded portfolio history and update dateFrom/displayDateFrom.
     * No-op once already resolved or if there's no history data yet.
     */
    function resolveMaxStartFromHistory() {
        if (!isMaxPending || history.length === 0) return;
        dateFrom = history[0].date;
        displayDateFrom = dateFrom;
        isMaxPending = false;
    }

    async function loadAll(force = false) {
        reportLoading = true;
        try {
            const report = await fetchReport(activeBrokerIds, dateFrom || undefined, dateTo || undefined, targetCurrency, force);
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
            const report = await fetchReport(activeBrokerIds, dateFrom || undefined, dateTo || undefined, targetCurrency, false, true, false, false, false);
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

    function handleDateChange(from: string, to: string) {
        isMaxPending = isMaxSentinel(from);
        dateFrom = resolveDateSentinel(from);
        dateTo = resolveDateSentinel(to);
        displayDateFrom = isMaxPending ? 'min' : dateFrom;
        setDateRange(from, to);
        void loadAll();
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
                    dateFrom: dateFrom || undefined,
                    dateTo: dateTo || undefined,
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
        if (target.closest?.('[data-broker-filter-panel]') || target === brokerFilterTriggerEl) return;
        brokerFilterOpen = false;
    }

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(() => {
        document.addEventListener('click', handleDocumentClick);
        void (async () => {
            await ensureBrokersLoaded();
            allBrokers = getAllBrokers();
            await loadAll();
        })();
        return () => document.removeEventListener('click', handleDocumentClick);
    });
</script>

<div class="space-y-4" data-testid="dashboard-page">
    <h1 class="sr-only">{$_('nav.dashboard')}</h1>

    <div class="bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 overflow-hidden" data-testid="dashboard-controls">
        <div
            bind:this={filterBarRef}
            class="flex gap-3 p-4
                   {layout.layoutMode === 'mobile' ? 'flex-col items-start' : 'flex-row items-center'}"
            data-testid="dashboard-filter-bar"
        >
            <!-- LEFT: Date range picker (wired to global store) -->
            <DateRangePicker bind:activePreset bind:start={displayDateFrom} bind:end={dateTo} compact={true} onchange={handleDateChange} />

            <!-- CENTER-LEFT: Currency override selector -->
            <div class="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                <span class="whitespace-nowrap">{$_('common.currency')}:</span>
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

            <!-- CENTER: Broker multi-select panel -->
            <div class="relative">
                <button
                    bind:this={brokerFilterTriggerEl}
                    class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors whitespace-nowrap
                       {brokerFilterActive ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-700' : 'bg-white dark:bg-slate-700 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-600'}"
                    onclick={() => (brokerFilterOpen = !brokerFilterOpen)}
                    data-testid="broker-filter-trigger"
                >
                    {brokerFilterLabel}
                    <svg class="w-3 h-3 transition-transform {brokerFilterOpen ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path d="M19 9l-7 7-7-7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
                    </svg>
                </button>

                {#if brokerFilterOpen}
                    <div class="absolute left-0 z-50 mt-1 w-56 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg overflow-hidden" data-broker-filter-panel>
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

            <!-- Spacer -->
            <div class="flex-1"></div>

            <!-- FAR RIGHT: AI Export + Sync buttons -->
            <div class="relative">
                <button
                    bind:this={aiExportTriggerEl}
                    class="flex items-center gap-2 px-3 py-1.5 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-600 transition-colors disabled:opacity-50"
                    onclick={() => (aiExportDropdownOpen = !aiExportDropdownOpen)}
                    disabled={aiExportLoading}
                    data-testid="ai-export-button"
                    title={$_('dashboard.aiExport')}
                >
                    <Brain size={14} class={aiExportLoading ? 'animate-pulse' : ''} />
                    {#if layout.showActionLabels}
                        <span>{aiExportLoading ? $_('dashboard.aiExportBuilding') : $_('dashboard.aiExport')}</span>
                    {/if}
                </button>

                {#if aiExportDropdownOpen}
                    <div class="absolute right-0 z-50 mt-1 w-56 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg overflow-hidden" data-ai-export-panel>
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
                class="flex items-center gap-2 px-3 py-1.5 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-600 transition-colors disabled:opacity-50"
                onclick={handleSync}
                disabled={syncLoading}
                data-testid="sync-button"
                title={$_('dashboard.syncData')}
            >
                <RefreshCw size={14} class={syncLoading ? 'animate-spin' : ''} />
                {#if layout.showActionLabels}
                    <span>{$_('dashboard.syncData')}</span>
                {/if}
            </button>
        </div>
        <TabBar bind:activeTab tabs={dashboardTabs} />
    </div>

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
            <PositionsPanel {summary} contribution={positionsContribution} loading={summaryLoading} {contributionLoading} {assetsHref} brokers={allBrokers} onRequestContribution={loadContribution} />
        </div>
    {:else if activeTab === 'transazioni'}
        <div data-testid="dashboard-transactions-tab">
            <RecentTransactionsPanel
                limit={10}
                brokerIds={activeBrokerIds}
                {transactionsHref}
                onViewRow={(row) => {
                    txViewItems = resolveFormItemsForView(row as TXReadItem, () => undefined, getBrokerRole);
                    txViewOpen = true;
                }}
            />
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

<!-- Transaction view modal — opened from RecentTransactionsPanel double-click -->
<TransactionFormModal open={txViewOpen} mode="view" items={txViewItems} onClose={() => (txViewOpen = false)} />
