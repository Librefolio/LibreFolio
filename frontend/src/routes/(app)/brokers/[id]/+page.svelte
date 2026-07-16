<script lang="ts">
    /**
     * Broker Detail Page — header + overview/positions/transactions tabs
     */
    import {get} from 'svelte/store';
    import {onMount} from 'svelte';
    import {page} from '$app/stores';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {goBack} from '$lib/stores/app/navigationStore';
    import {globalSettings} from '$lib/stores/app/globalSettings';
    import {currentLanguage} from '$lib/stores/app/language';
    import {getEnd, getStart, isMaxSentinel, resolveDateSentinel, setDateRange} from '$lib/stores/dateRangeStore.svelte';
    import {ArrowLeft, ArrowRightLeft, Briefcase, Crown, ExternalLink, Eye, FileText, Info, Pencil, Plus, RefreshCw, Share2, TrendingUp, Upload, Users, Wallet} from 'lucide-svelte';
    import BrokerModal from '$lib/components/brokers/BrokerModal.svelte';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import BrokerImportFilesModal from '$lib/components/brokers/BrokerImportFilesModal.svelte';
    import BrokerSharingPanel from '$lib/components/brokers/BrokerSharingPanel.svelte';
    import FIFOLotsPanel from '$lib/components/brokers/lots/FIFOLotsPanel.svelte';
    import KpiSection from '$lib/components/dashboard/KpiSection.svelte';
    import AllocationPanel from '$lib/components/dashboard/AllocationPanel.svelte';
    import GrowthChart from '$lib/components/dashboard/GrowthChart.svelte';
    import PositionsPanel from '$lib/components/dashboard/PositionsPanel.svelte';
    import DateRangePicker from '$lib/components/ui/date/DateRangePicker.svelte';
    import PageToolbar from '$lib/components/ui/toolbar/PageToolbar.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import {TransactionFormModal, TransactionsTable, TransactionBulkModal, resolveFormItemsForView, loadPartnerRows, loadEventTooltipMap, type FormModalItems} from '$lib/components/transactions';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import type {TXReadItem, AssetEvent} from '$lib/components/transactions/types';
    import {fetchReport, invalidate, type AllocationHistoryDimensions, type PortfolioHistoryPoint, type PortfolioSummary, type PositionsContribution} from '$lib/stores/portfolio/portfolioStore.svelte';
    import {ensureBrokersLoaded, getAllBrokers, getBrokerRole, brokerStoreVersion} from '$lib/stores/reference/brokerStore';
    import {ensureAssetsLoaded, getAssetInfo} from '$lib/stores/reference/assetStore';
    import {getAssetPanelAssetId, buildAssetPanelUrl} from '$lib/utils/broker/assetPanelUrl';
    import {buildTabUrl, getResolvedTabParam} from '$lib/utils/url/tabUrl';
    import {goto} from '$app/navigation';
    import type {BrokerSummary} from '$lib/types';
    import {parseCurrencyAmount, safeCurrency, safeString} from '$lib/types';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import {formatCurrencyAmountHtml} from '$lib/utils/currency/currencyFormat';
    import {copyAiExport} from '$lib/features/ai-export/aiExportClipboard';
    import AiExportMenu from '$lib/features/ai-export/AiExportMenu.svelte';
    import {PORTFOLIO_PROMPT_CATALOG, type PromptId} from '$lib/features/ai-export/promptCatalog';
    import {toasts} from '$lib/stores/app/toastStore.svelte';

    export let data: {brokerId: number};

    let broker: BrokerSummary | null = null;
    let loading = true;
    let reportLoading = true;
    let error: string | null = null;

    let portfolioSummary: PortfolioSummary | null = null;
    let portfolioHistory: PortfolioHistoryPoint[] = [];
    let allocationHistoryFromReport: AllocationHistoryDimensions | null = null;
    let positionsContribution: PositionsContribution | null = null;
    let contributionLoading = false;

    let editModalOpen = false;
    let importFilesModalOpen = false;
    let txViewOpen = false;
    let txViewItems: FormModalItems | null = null;

    /** Bulk workspace (create / import) — same engine as /transactions, pre-populated
     *  with this page's broker (still editable, never skips a step). */
    let bulkOpen = false;
    let bulkIntent: import('$lib/components/transactions/modals/TransactionBulkModal.svelte').WorkspaceIntent | undefined = undefined;

    function openImportTransactions() {
        bulkIntent = {action: 'import'};
        bulkOpen = true;
    }

    function openNewTransaction() {
        bulkIntent = {action: 'create'};
        bulkOpen = true;
    }

    /** AI export state — dropdown open/position handled internally by AiExportMenu */
    let aiExportLoading = false;
    $: aiExportEntries = PORTFOLIO_PROMPT_CATALOG.map((p) => ({id: p.id, label: $_(p.labelKey), description: $_(p.descriptionKey)}));

    // Transactions tab — full paginated history (not just "recent 10").
    let txMainRows: TXReadItem[] = [];
    let txPartnerRows: TXReadItem[] = [];
    let txEventTooltipMap: Map<number, AssetEvent> = new Map();
    let txLoading = false;
    let txLoaded = false;
    let txCurrentPage = 1;
    let txTableComponent: TransactionsTable | undefined;

    const BROKER_TAB_IDS = ['panoramica', 'posizioni', 'transazioni', 'info'] as const;
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

    let targetCurrency = get(globalSettings).default_currency || 'EUR';
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
    $: baseCurrency = $globalSettings.default_currency || 'EUR';
    $: if (!targetCurrencyManuallySet && targetCurrency !== baseCurrency) {
        const hadLoadedData = portfolioSummary !== null || portfolioHistory.length > 0;
        targetCurrency = baseCurrency;
        // Guard with !reportLoading: see brokers/+page.svelte for the race this avoids.
        if (hadLoadedData && !reportLoading) void loadOverview(true);
    }

    $: brokerTabs = [
        {id: 'panoramica', label: $_('brokers.overview'), icon: Briefcase, testId: 'broker-tab-panoramica'},
        {id: 'posizioni', label: $_('brokers.positions'), icon: TrendingUp, testId: 'broker-tab-posizioni'},
        {id: 'transazioni', label: $_('transactions.title'), icon: ArrowRightLeft, testId: 'broker-tab-transazioni'},
        {id: 'info', label: $_('brokers.info'), icon: Info, testId: 'broker-tab-info'},
    ];

    async function handleAiExport(promptId: PromptId) {
        if (!broker) return;
        aiExportLoading = true;
        try {
            await copyAiExport(
                promptId,
                {
                    brokerIds: [broker.id],
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

    onMount(() => {
        void Promise.all([loadBroker(), loadOverview(), ensureBrokersLoaded(), ensureAssetsLoaded()]);
    });

    async function loadBroker() {
        loading = true;
        error = null;

        try {
            broker = (await zodiosApi.get_broker_summary_api_v1_brokers__broker_id__summary_get({params: {broker_id: data.brokerId}})) as BrokerSummary;
        } catch (e) {
            console.error('Failed to load broker:', e);
            error = $_('brokers.loadFailed');
        } finally {
            loading = false;
        }
    }

    async function loadOverview(force = false) {
        reportLoading = true;
        try {
            const report = await fetchReport([data.brokerId], dateFrom || undefined, dateTo || undefined, targetCurrency, force);
            portfolioSummary = (report?.summary as PortfolioSummary | null | undefined) ?? null;
            portfolioHistory = (report?.history as PortfolioHistoryPoint[] | null | undefined) ?? [];
            allocationHistoryFromReport = (report?.allocation_history as AllocationHistoryDimensions | null | undefined) ?? null;
            positionsContribution = (report?.positions_contribution as PositionsContribution | null | undefined) ?? null;
            resolveMaxStartFromHistory();
        } finally {
            reportLoading = false;
        }
    }

    async function loadContribution() {
        if (!broker || positionsContribution || contributionLoading) return;
        contributionLoading = true;
        try {
            // includeHistory/includeAllocationHistory=false: only positions_contribution is read below.
            const report = await fetchReport([broker.id], dateFrom || undefined, dateTo || undefined, targetCurrency, false, true, false, false, false);
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
        void loadTransactions();
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
        void loadOverview();
    }

    async function handleRefresh() {
        invalidate();
        await Promise.all([loadBroker(), loadOverview(true)]);
        if (txLoaded) await loadTransactions(true);
    }

    async function handleUpdated() {
        await loadBroker();
    }

    async function handleRequestAllocationHistory() {
        await loadOverview();
    }

    function formatDate(dateStr: unknown): string {
        const str = safeString(dateStr);
        if (!str) return '-';
        return new Date(str).toLocaleDateString(undefined, {
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

    function formatSharePercentage(value: number | string | (string | null)[] | null | undefined): string {
        return (Math.round(toNumber(value) * 10000) / 100).toFixed(1);
    }
</script>

<div class="space-y-6" data-testid="broker-detail-page">
    <div class="flex items-center space-x-4">
        <button class="p-2 text-gray-500 hover:text-libre-green hover:bg-libre-green/10 rounded-lg transition-colors" data-testid="broker-back-button" on:click={handleBack} title={$_('common.back')}>
            <ArrowLeft size={20} />
        </button>

        {#if broker}
            <BrokerIcon brokerId={broker.id} iconUrl={safeString(broker.icon_url)} portalUrl={safeString(broker.portal_url)} pluginCode={safeString(broker.default_import_plugin)} altText={broker.name} size="lg" />

            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                    {#if safeString(broker.user_role)}
                        {@const role = safeString(broker.user_role)}
                        <span
                            class="inline-flex items-center gap-1 px-2 py-1 rounded-full flex-shrink-0
                            {role === 'OWNER' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' : role === 'EDITOR' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'}"
                            title={$_(role === 'OWNER' ? 'brokers.sharing.roleOwnerShort' : role === 'EDITOR' ? 'brokers.sharing.roleEditorShort' : 'brokers.sharing.roleViewerShort')}
                            data-testid="broker-quota-badge"
                        >
                            {#if broker.user_share_percentage != null}
                                <span class="text-xs font-medium">{formatSharePercentage(broker.user_share_percentage)}%</span>
                            {/if}
                            {#if role === 'OWNER'}<Crown size={13} />{:else if role === 'EDITOR'}<Pencil size={13} />{:else}<Eye size={13} />{/if}
                        </span>
                    {/if}
                    <h1 class="text-2xl font-bold text-gray-800 dark:text-gray-100 truncate" data-testid="broker-name">{broker.name}</h1>
                </div>
                {#if broker.description}
                    <p class="text-gray-500 dark:text-gray-400 text-sm truncate" data-testid="broker-description">{broker.description}</p>
                {/if}
            </div>

            {#if safeString(broker.portal_url)}
                <a href={safeString(broker.portal_url)} target="_blank" rel="noopener noreferrer" class="flex items-center justify-center p-2 text-gray-500 hover:text-libre-green hover:bg-libre-green/10 rounded-lg transition-colors flex-shrink-0" title={$_('brokers.openPortal')}>
                    <ExternalLink size={20} />
                </a>
            {/if}
        {:else if !error}
            <div class="flex-1">
                <div class="h-8 w-48 bg-gray-200 rounded animate-pulse"></div>
            </div>
        {/if}
    </div>

    {#if loading && !broker}
        <div class="bg-white rounded-xl shadow-sm p-12 text-center border border-gray-100">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-libre-green/10 rounded-full mb-4">
                <RefreshCw class="text-libre-green animate-spin" size={32} />
            </div>
            <p class="text-gray-500">{$_('common.loading')}</p>
        </div>
    {:else if error}
        <div class="bg-white rounded-xl shadow-sm p-12 text-center border border-red-100">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
                <Briefcase class="text-red-600" size={32} />
            </div>
            <h3 class="text-lg font-semibold text-gray-700 mb-2">{$_('common.error')}</h3>
            <p class="text-gray-500 mb-4">{error}</p>
            <button on:click={handleRefresh} class="px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors">
                {$_('common.retry')}
            </button>
        </div>
    {:else if broker}
        <!-- Page-global controls: date range + currency + tabs — persist across ALL tabs
             (previously the date-range picker only rendered inside the Panoramica tab's
             content, so it disappeared on Posizioni/Transazioni even though those tabs
             depend on the same date-scoped data). -->
        <PageToolbar
            thresholds={{oneRow: 1000, denseRow: 800, stackFilters: 470, oneColumn: 430, labelHideActions: 270, labelHideTabs: 370}}
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
                <div class="flex items-center justify-around gap-1.5 text-xs text-gray-500 dark:text-gray-400 {filtersStacked ? 'w-full' : ''}" style={filtersStacked && pickerMaxWidth ? `max-width: ${pickerMaxWidth}px` : ''}>
                    <div class="flex items-center gap-1.5">
                        <span class="whitespace-nowrap">{$_('common.currency')}:</span>
                        <div class="w-28">
                            <CurrencySearchSelect
                                bind:value={targetCurrency}
                                compact={true}
                                dropdownPosition="bottom"
                                placeholder={baseCurrency}
                                onchange={() => {
                                    targetCurrencyManuallySet = true;
                                    void loadOverview();
                                }}
                            />
                        </div>
                    </div>
                </div>
            {/snippet}

            {#snippet actions({showActionLabels})}
                {#if canEdit}
                    <button
                        on:click={handleEdit}
                        class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                        data-testid="broker-edit-button"
                    >
                        <Pencil size={14} />
                        {#if showActionLabels}<span>{$_('common.edit')}</span>{/if}
                    </button>
                {/if}
                <button
                    on:click={() => handleTabChange('info')}
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                    data-testid="broker-share-button"
                    title={$_('brokers.sharing.title')}
                >
                    <Share2 size={14} />
                    {#if showActionLabels}<span>{$_('brokers.sharing.title')}</span>{/if}
                </button>
                <button
                    on:click={handleRefresh}
                    disabled={loading || reportLoading}
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors disabled:opacity-50"
                    title={$_('dashboard.syncData')}
                    data-testid="broker-refresh"
                >
                    <RefreshCw size={14} class={loading || reportLoading ? 'animate-spin' : ''} />
                    {#if showActionLabels}<span>{$_('dashboard.syncData')}</span>{/if}
                </button>

                <!-- AI Export — reuses the same copyAiExport() utility as the dashboard, scoped to this single broker. -->
                <AiExportMenu entries={aiExportEntries} loading={aiExportLoading} triggerLabel={$_('dashboard.aiExport')} loadingLabel={$_('dashboard.aiExportBuilding')} showLabel={showActionLabels} onselect={(id) => handleAiExport(id as PromptId)} />
            {/snippet}
        </PageToolbar>

        {#if activeTab === 'panoramica'}
            <div class="space-y-4" data-testid="broker-overview-tab">
                <KpiSection summary={portfolioSummary} history={portfolioHistory} loading={reportLoading && !portfolioSummary} displayCurrency={targetCurrency || baseCurrency} />

                <!-- Cash Balances — moved up right below the KPIs so the "economic position"
                     (NAV + Gain/Loss + Cash by currency) is visible together at a glance. -->
                <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 p-4" data-testid="broker-cash-balances">
                    <div class="flex items-center space-x-2 text-gray-700 dark:text-gray-200 mb-4">
                        <Wallet size={20} />
                        <h2 class="font-semibold">{$_('brokers.cashBalances')}</h2>
                    </div>

                    {#if broker.cash_balances && broker.cash_balances.length > 0}
                        <div class="flex flex-wrap gap-2">
                            {#each [...broker.cash_balances].sort((a, b) => parseCurrencyAmount(b.amount) - parseCurrencyAmount(a.amount)) as balance}
                                <span class="inline-flex items-center px-3 py-1.5 bg-gray-50 dark:bg-slate-700 rounded-lg text-sm font-medium text-gray-800 dark:text-gray-100">
                                    {@html formatCurrencyAmountHtml(parseCurrencyAmount(balance.amount), balance.code)}
                                </span>
                            {/each}
                        </div>
                    {:else}
                        <p class="text-gray-400 dark:text-gray-500 text-sm italic py-4 text-center">{$_('brokers.noCashBalances')}</p>
                    {/if}
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-5 gap-4">
                    <div class="lg:col-span-3">
                        <GrowthChart history={portfolioHistory} loading={reportLoading && portfolioHistory.length === 0} baseCurrency={targetCurrency || baseCurrency} />
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
                <PositionsPanel summary={portfolioSummary} contribution={positionsContribution} loading={reportLoading && !portfolioSummary} {contributionLoading} assetsHref="/assets" brokers={panelBrokers} onRequestContribution={loadContribution} onAnalyze={openAssetPanel} />
                <FIFOLotsPanel
                    open={activeAssetId != null}
                    assetId={activeAssetId}
                    brokerIds={[broker.id]}
                    brokers={panelBrokers}
                    {dateFrom}
                    {dateTo}
                    isAllPeriod={isMaxPending}
                    currency={activeAssetId != null ? (getAssetInfo(activeAssetId)?.currency ?? baseCurrency) : baseCurrency}
                    assetName={activeAssetId != null ? getAssetInfo(activeAssetId)?.display_name : null}
                    onClose={closeAssetPanel}
                />
            </div>
        {:else if activeTab === 'transazioni'}
            <div class="space-y-4" data-testid="broker-transactions-tab">
                <div class="flex flex-wrap items-center justify-between gap-2" data-testid="broker-transactions-actions">
                    <button
                        class="flex items-center justify-center gap-1 px-2.5 py-1.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-all"
                        on:click={() => (importFilesModalOpen = true)}
                        data-testid="broker-show-import-history"
                    >
                        <FileText size={15} />
                        <span class="hidden sm:inline">{$_('brokers.showImportHistory')}</span>
                    </button>
                    <div class="flex items-center gap-2">
                        <ColumnVisibilityToggle tableRef={txTableComponent?.getTableRef()} />
                        {#if canEdit}
                            <button
                                class="flex items-center justify-center gap-1 px-2.5 py-1.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-all"
                                on:click={openImportTransactions}
                                data-testid="broker-import-transactions"
                            >
                                <Upload size={15} />
                                <span class="hidden sm:inline">{$_('common.import')}</span>
                            </button>
                            <button class="flex items-center justify-center gap-1 px-2.5 py-1.5 text-xs bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-all" on:click={openNewTransaction} data-testid="broker-new-transaction">
                                <Plus size={15} />
                                <span class="hidden sm:inline">{$_('transactions.addTransaction')}</span>
                            </button>
                        {/if}
                    </div>
                </div>

                <div data-testid="broker-transactions">
                    {#if txLoading && !txLoaded}
                        <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 p-12 text-center">
                            <RefreshCw class="text-libre-green animate-spin mx-auto" size={28} />
                        </div>
                    {:else}
                        <TransactionsTable
                            bind:this={txTableComponent}
                            mainRows={txMainRows}
                            partnerRows={txPartnerRows}
                            brokers={allBrokersForTable}
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
            </div>
        {:else if activeTab === 'info'}
            <div class="grid grid-cols-1 xl:grid-cols-2 gap-4" data-testid="broker-info-tab">
                <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 p-4" data-testid="broker-metadata">
                    <h3 class="font-semibold text-gray-700 dark:text-gray-200 mb-3">{$_('brokers.metadata')}</h3>
                    <div class="space-y-2 text-sm">
                        <div class="flex justify-between">
                            <span class="text-gray-500 dark:text-gray-400">{$_('brokers.isActive')}</span>
                            <span class="font-medium {broker.is_active ? 'text-green-600' : 'text-red-500'}">
                                {broker.is_active ? '✓ Active' : '✗ Closed'}
                            </span>
                        </div>
                        {#if safeString(broker.opened_at)}
                            <div class="flex justify-between">
                                <span class="text-gray-500 dark:text-gray-400">{$_('brokers.openedAt')}</span>
                                <span class="text-gray-700 dark:text-gray-200">{formatDate(broker.opened_at)}</span>
                            </div>
                        {/if}
                        <div class="flex justify-between">
                            <span class="text-gray-500 dark:text-gray-400">{$_('brokers.allowOverdraft')}</span>
                            <span class="font-medium {broker.allow_cash_overdraft ? 'text-green-600' : 'text-gray-400'}">
                                {broker.allow_cash_overdraft ? '✓' : '✗'}
                            </span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-500 dark:text-gray-400">{$_('brokers.allowShorting')}</span>
                            <span class="font-medium {broker.allow_asset_shorting ? 'text-green-600' : 'text-gray-400'}">
                                {broker.allow_asset_shorting ? '✓' : '✗'}
                            </span>
                        </div>
                        <div class="flex justify-between border-t border-gray-100 dark:border-slate-700 pt-2 mt-2">
                            <span class="text-gray-500 dark:text-gray-400">{$_('brokers.createdInSystem')}</span>
                            <span class="text-gray-700 dark:text-gray-200">{formatDate(broker.created_at)}</span>
                        </div>
                    </div>

                    {#if broker.total_value_base_currency}
                        {@const totalValue = safeCurrency(broker.total_value_base_currency)}
                        {#if totalValue}
                            <div class="mt-4 pt-4 border-t border-gray-100 dark:border-slate-700">
                                <div class="text-sm text-gray-500 dark:text-gray-400">{$_('common.totalValue')}</div>
                                <div class="text-2xl font-bold text-libre-green">
                                    {@html formatCurrencyAmountHtml(parseCurrencyAmount(totalValue.amount), totalValue.code)}
                                </div>
                            </div>
                        {/if}
                    {/if}
                </div>

                <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 p-4" data-testid="broker-sharing-section">
                    <h3 class="font-semibold text-gray-700 dark:text-gray-200 mb-3 flex items-center gap-2">
                        <Users size={18} class="text-libre-green" />
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
