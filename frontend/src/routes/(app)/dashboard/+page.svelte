<!--
  Dashboard Home — Portfolio overview page.

  Layout (from wireframe plan_ui_dashboard.md):
  1. Header row: Broker filter | [↻] Sync | DateRangePicker
  2. KPI row: Net Worth | Gain/Loss | Weighted ROI
  3. Charts row: GrowthChart (3/5) | Allocation tabs (2/5)
  4. Recent Transactions

  Data sources:
  - portfolioStore.fetchSummary() → KPI cards + allocation charts
  - portfolioStore.fetchHistory() → GrowthChart

  Pattern: Svelte 5 Runes, Tailwind CSS 4, dark mode, data-testid everywhere.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {RefreshCw, ChevronDown, Check} from 'lucide-svelte';

    import {fetchSummary, fetchHistory, invalidate, portfolioIsLoading, type PortfolioSummary, type PortfolioHistoryPoint} from '$lib/stores/portfolio/portfolioStore.svelte';
    import {ensureBrokersLoaded, getAllBrokers} from '$lib/stores/reference/brokerStore';
    import {globalSettings} from '$lib/stores/app/globalSettings';

    import DateRangePicker from '$lib/components/ui/date/DateRangePicker.svelte';
    import BaseDropdown from '$lib/components/ui/select/BaseDropdown.svelte';
    import SectorPieChart from '$lib/components/charts/SectorPieChart.svelte';
    import GeographyMap from '$lib/components/charts/GeographyMap.svelte';
    import KpiCard from '$lib/components/dashboard/KpiCard.svelte';
    import GrowthChart from '$lib/components/dashboard/GrowthChart.svelte';
    import RecentTransactionsPanel from '$lib/components/dashboard/RecentTransactionsPanel.svelte';
    import {currentLanguage} from '$lib/stores/app/language';

    // =========================================================================
    // State
    // =========================================================================

    let summary = $state<PortfolioSummary | null>(null);
    let history = $state<PortfolioHistoryPoint[]>([]);
    let summaryLoading = $state(true);
    let historyLoading = $state(true);
    let syncLoading = $state(false);

    /** Broker IDs selected in the filter (empty = all brokers). */
    let selectedBrokerIds = $state<number[]>([]);

    /** Date range for history / KPI filtering. */
    let dateFrom = $state('');
    let dateTo = $state('');

    /** Active tab in the allocation panel. */
    let allocationTab = $state<'type' | 'sector' | 'geo'>('type');

    // =========================================================================
    // Derived
    // =========================================================================

    const allBrokers = $derived(getAllBrokers());
    const baseCurrency = $derived($globalSettings.default_currency || 'EUR');

    /** Which broker IDs to pass to the API (null = all). */
    const activeBrokerIds = $derived(selectedBrokerIds.length > 0 ? selectedBrokerIds : undefined);

    /** Broker filter label. */
    const brokerFilterLabel = $derived(selectedBrokerIds.length === 0 ? $_('dashboard.allBrokers') : selectedBrokerIds.length === 1 ? (allBrokers.find((b) => b.id === selectedBrokerIds[0])?.name ?? String(selectedBrokerIds[0])) : `${$_('dashboard.filterBrokers')} (${selectedBrokerIds.length})`);

    /** Extract a single string from SafeDecimal (may be string | (string|null)[] | null | undefined). */
    function safeStr(v: string | (string | null)[] | null | undefined): string | null {
        if (v == null) return null;
        if (Array.isArray(v)) return v[0] ?? null;
        return v;
    }

    /** Allocation data for charts (Record<string, number> where value = 0-1). */
    const allocationByType = $derived(summary ? Object.fromEntries((summary.allocation_by_type ?? []).map((i) => [i.name, parseFloat(i.value) / 100])) : {});
    const allocationBySector = $derived(summary ? Object.fromEntries((summary.allocation_by_sector ?? []).map((i) => [i.name, parseFloat(i.value) / 100])) : {});
    const allocationByGeo = $derived(summary ? Object.fromEntries((summary.allocation_by_geography ?? []).map((i) => [i.name, parseFloat(i.value) / 100])) : {});

    // KPI formatted values
    const netWorthValue = $derived(summary ? `${baseCurrency} ${parseFloat(summary.net_worth).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : '—');
    const gainLossValue = $derived(summary ? `${parseFloat(summary.total_gain_loss) >= 0 ? '+' : ''}${baseCurrency} ${Math.abs(parseFloat(summary.total_gain_loss)).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : '—');
    const gainLossPercent = $derived(summary ? parseFloat(summary.total_gain_loss_percent) : undefined);
    const roiValue = $derived(summary ? `${(parseFloat(summary.simple_roi_percent) * 100).toFixed(2)}%` : '—');
    const roiSubLabel = $derived.by(() => {
        if (!summary) return '';
        const twrr = safeStr(summary.twrr_percent);
        const mwrr = safeStr(summary.mwrr_percent);
        return `${$_('dashboard.twrr')}: ${twrr != null ? (parseFloat(twrr) * 100).toFixed(2) + '%' : '—'} | ${$_('dashboard.mwrr')}: ${mwrr != null ? (parseFloat(mwrr) * 100).toFixed(2) + '%' : '—'}`;
    });
    const roiIsPositive = $derived(summary ? parseFloat(summary.simple_roi_percent) >= 0 : undefined);

    // =========================================================================
    // Loaders
    // =========================================================================

    async function loadSummary(force = false) {
        summaryLoading = true;
        try {
            summary = await fetchSummary(activeBrokerIds, false, force);
        } finally {
            summaryLoading = false;
        }
    }

    async function loadHistory(force = false) {
        historyLoading = true;
        try {
            history = await fetchHistory(activeBrokerIds, dateFrom || undefined, dateTo || undefined, force);
        } finally {
            historyLoading = false;
        }
    }

    async function loadAll(force = false) {
        await Promise.all([loadSummary(force), loadHistory(force)]);
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
        void loadAll();
    }

    function clearBrokerFilter() {
        selectedBrokerIds = [];
        void loadAll();
    }

    function handleDateChange(from: string, to: string) {
        dateFrom = from;
        dateTo = to;
        void loadHistory();
    }

    async function handleSync() {
        syncLoading = true;
        invalidate();
        await loadAll(true);
        syncLoading = false;
    }

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(async () => {
        await ensureBrokersLoaded();
        await loadAll();
    });
</script>

<div class="space-y-4" data-testid="dashboard-page">
    <h1 class="sr-only">{$_('nav.dashboard')}</h1>

    <!-- ── Header row: Broker filter | Sync | DateRangePicker ── -->
    <div class="flex flex-wrap items-center gap-3">
        <!-- Broker multi-select popover via BaseDropdown -->
        <BaseDropdown>
            {#snippet trigger({isOpen})}
                <button class="flex items-center gap-2 px-3 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors shadow-sm" data-testid="broker-filter-trigger">
                    <span class="truncate max-w-[160px]">{brokerFilterLabel}</span>
                    <ChevronDown size={14} class="flex-shrink-0 text-gray-400 transition-transform {isOpen ? 'rotate-180' : ''}" />
                </button>
            {/snippet}
            {#snippet content({close})}
                <div class="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg min-w-[200px] py-1 z-50" data-testid="broker-filter-dropdown">
                    <!-- All brokers option -->
                    <button
                        class="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
                        onclick={() => {
                            clearBrokerFilter();
                            close();
                        }}
                    >
                        <span class="w-4 h-4 flex-shrink-0 flex items-center justify-center">
                            {#if selectedBrokerIds.length === 0}
                                <Check size={14} class="text-libre-green" />
                            {/if}
                        </span>
                        <span class="text-gray-700 dark:text-gray-200">{$_('dashboard.allBrokers')}</span>
                    </button>
                    <div class="my-1 border-t border-gray-100 dark:border-slate-700"></div>
                    {#each allBrokers as broker (broker.id)}
                        <button class="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors" onclick={() => toggleBroker(broker.id)}>
                            <span class="w-4 h-4 flex-shrink-0 flex items-center justify-center">
                                {#if selectedBrokerIds.includes(broker.id)}
                                    <Check size={14} class="text-libre-green" />
                                {/if}
                            </span>
                            <span class="text-gray-700 dark:text-gray-200 truncate">{broker.name}</span>
                        </button>
                    {/each}
                </div>
            {/snippet}
        </BaseDropdown>

        <!-- Sync button -->
        <button
            class="flex items-center gap-2 px-3 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors shadow-sm disabled:opacity-50"
            onclick={handleSync}
            disabled={syncLoading}
            data-testid="sync-button"
            title={$_('dashboard.syncData')}
        >
            <RefreshCw size={14} class={syncLoading ? 'animate-spin' : ''} />
            <span class="hidden sm:inline">{$_('dashboard.syncData')}</span>
        </button>

        <!-- Date range picker (history range) -->
        <div class="ml-auto">
            <DateRangePicker bind:start={dateFrom} bind:end={dateTo} compact={true} onchange={handleDateChange} />
        </div>
    </div>

    <!-- ── KPI Row ── -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="kpi-row">
        <KpiCard label={$_('dashboard.netWorth')} value={netWorthValue} subLabel={summary ? `${$_('common.cash')}: ${baseCurrency} ${parseFloat(summary.cash_total).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : ''} loading={summaryLoading} />
        <KpiCard label={$_('dashboard.gainLoss')} value={gainLossValue} changePercent={gainLossPercent} positive={gainLossPercent !== undefined ? gainLossPercent >= 0 : undefined} loading={summaryLoading} />
        <KpiCard label={$_('dashboard.roiWeighted')} value={roiValue} subLabel={roiSubLabel} positive={roiIsPositive} loading={summaryLoading} />
    </div>

    <!-- ── Charts Row ── -->
    <div class="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <!-- Growth Chart — 3/5 -->
        <div class="lg:col-span-3">
            <GrowthChart {history} loading={historyLoading} {baseCurrency} />
        </div>

        <!-- Allocation Panel — 2/5 -->
        <div class="lg:col-span-2 bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm p-4 flex flex-col gap-3" data-testid="allocation-panel">
            <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-200">{$_('dashboard.allocation')}</h2>

            <!-- Tab bar -->
            <div class="flex rounded-lg overflow-hidden border border-gray-200 dark:border-slate-600 text-xs font-medium self-start">
                {#each [['type', 'dashboard.typeAllocation'], ['sector', 'dashboard.sectorAllocation'], ['geo', 'dashboard.geoAllocation']] as const as [tab, labelKey]}
                    <button
                        class="px-3 py-1 transition-colors {allocationTab === tab ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'} {tab !== 'type' ? 'border-l border-gray-200 dark:border-slate-600' : ''}"
                        onclick={() => (allocationTab = tab)}
                        data-testid="allocation-tab-{tab}"
                    >
                        {$_(labelKey)}
                    </button>
                {/each}
            </div>

            <!-- Chart area -->
            {#if summaryLoading}
                <div class="flex-1 min-h-[220px] bg-gray-100 dark:bg-slate-700 rounded animate-pulse"></div>
            {:else if !summary}
                <div class="flex-1 min-h-[220px] flex items-center justify-center text-sm text-gray-400 dark:text-gray-500">
                    {$_('dashboard.noData')}
                </div>
            {:else if allocationTab === 'type'}
                <SectorPieChart data={allocationByType} height="220px" />
            {:else if allocationTab === 'sector'}
                <SectorPieChart data={allocationBySector} height="220px" />
            {:else}
                <GeographyMap data={allocationByGeo} height="220px" language={$currentLanguage} />
            {/if}
        </div>
    </div>

    <!-- ── Recent Transactions ── -->
    <RecentTransactionsPanel limit={10} brokerIds={activeBrokerIds} />
</div>
