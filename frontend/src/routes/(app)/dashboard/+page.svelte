<!--
  Dashboard Home — Portfolio overview page.

  Layout (from wireframe plan_ui_dashboard.md):
  1. Header row: DateRangePicker | spacer | Broker filter panel | ↻ Sync
  2. KPI row: Net Worth | Gain/Loss | Weighted ROI
  3. Charts row: GrowthChart (3/5) | Allocation tabs (2/5)
  4. Bottom grid: Holdings (left) | Recent Transactions (right)

  Data sources:
  - portfolioStore.fetchSummary() → KPI cards + allocation charts + holdings
  - portfolioStore.fetchHistory() → GrowthChart

  Pattern: Svelte 5 Runes, Tailwind CSS 4, dark mode, data-testid everywhere.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {RefreshCw} from 'lucide-svelte';

    import {fetchSummary, fetchHistory, invalidate, type PortfolioSummary, type PortfolioHistoryPoint} from '$lib/stores/portfolio/portfolioStore.svelte';
    import {ensureBrokersLoaded, getAllBrokers} from '$lib/stores/reference/brokerStore';
    import {globalSettings} from '$lib/stores/app/globalSettings';
    import {getStart, getEnd, setDateRange} from '$lib/stores/dateRangeStore.svelte';
    import {getBrokerIconUrlById, ensurePluginIconsLoaded} from '$lib/utils/broker/brokerHelpers';
    import {createResponsiveLayout} from '$lib/utils/layout/responsiveLayout.svelte';

    import DateRangePicker from '$lib/components/ui/date/DateRangePicker.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import AllocationPieChart from '$lib/components/charts/AllocationPieChart.svelte';
    import GeographyMap from '$lib/components/charts/GeographyMap.svelte';
    import KpiCard from '$lib/components/dashboard/KpiCard.svelte';
    import GrowthChart from '$lib/components/dashboard/GrowthChart.svelte';
    import RecentTransactionsPanel from '$lib/components/dashboard/RecentTransactionsPanel.svelte';
    import HoldingsPanel from '$lib/components/dashboard/HoldingsPanel.svelte';
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

    /** Debounce timer for broker filter changes. */
    let reloadTimer = $state<ReturnType<typeof setTimeout> | null>(null);

    /** Date range — backed by global store (shared with assets/fx pages). */
    let dateFrom = $state(getStart());
    let dateTo = $state(getEnd());

    /** Display currency override — always concrete, defaults to user base currency. */
    let targetCurrency = $state($globalSettings.default_currency || 'EUR');
    let targetCurrencyManuallySet = $state(false);

    /** Broker filter dropdown open state. */
    let brokerFilterOpen = $state(false);
    let brokerFilterTriggerEl = $state<HTMLButtonElement | null>(null);

    /** Filter bar ref — for ResizeObserver. */
    let filterBarRef = $state<HTMLDivElement | null>(null);

    /** Active tab in the allocation panel. */
    let allocationTab = $state<'type' | 'sector' | 'geo'>('type');

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

    const allBrokers = $derived(getAllBrokers());
    const baseCurrency = $derived($globalSettings.default_currency || 'EUR');
    const displayCurrency = $derived(targetCurrency || baseCurrency);

    $effect(() => {
        if (targetCurrencyManuallySet || targetCurrency === baseCurrency) return;
        const hadLoadedData = summary !== null || history.length > 0;
        targetCurrency = baseCurrency;
        if (hadLoadedData) void loadAll(true);
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

    /** Extract a single string from SafeDecimal (may be string | (string|null)[] | null | undefined). */
    function safeStr(v: string | (string | null)[] | null | undefined): string | null {
        if (v == null) return null;
        if (Array.isArray(v)) return v[0] ?? null;
        return v;
    }

    function formatMoney(code: string | undefined, amount: string | null | undefined, opts?: {signed?: boolean; absolute?: boolean}): string {
        if (amount == null) return '—';
        const num = parseFloat(amount);
        const signed = opts?.signed ?? false;
        const absolute = opts?.absolute ?? false;
        const rendered = absolute ? Math.abs(num) : num;
        const sign = signed ? (num >= 0 ? '+' : '-') : '';
        return `${sign}${code ?? displayCurrency} ${rendered.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    }

    /** Allocation data for charts (Record<string, number> where value = 0-1). */
    const allocationByType = $derived(summary ? Object.fromEntries((summary.allocation_by_type ?? []).map((i) => [i.name, parseFloat(i.value) / 100])) : {});
    const allocationBySector = $derived(summary ? Object.fromEntries((summary.allocation_by_sector ?? []).map((i) => [i.name, parseFloat(i.value) / 100])) : {});
    const allocationByGeo = $derived(summary ? Object.fromEntries((summary.allocation_by_geography ?? []).map((i) => [i.name, parseFloat(i.value) / 100])) : {});
    const missingPricesAssets = $derived(summary?.missing_prices_assets ?? []);
    const missingFxPairs = $derived.by(() => {
        const pairs = (summary?.missing_fx_pairs ?? []).map((item) => item.pair);
        return [...new Set(pairs)].sort();
    });

    // KPI formatted values
    const netWorthValue = $derived(summary ? formatMoney(summary.net_worth.code, summary.net_worth.amount) : '—');
    const gainLossValue = $derived(summary ? formatMoney(summary.total_gain_loss.code, summary.total_gain_loss.amount, {signed: true, absolute: true}) : '—');
    const gainLossPercent = $derived(summary ? parseFloat(summary.total_gain_loss_percent) : undefined);
    const roiValue = $derived(summary ? `${(parseFloat(summary.simple_roi_percent) * 100).toFixed(2)}%` : '—');
    const roiSubLabel = $derived.by(() => {
        if (!summary) return '';
        const twrr = safeStr(summary.twrr_percent);
        const mwrr = safeStr(summary.mwrr_percent);
        return `${$_('dashboard.twrr')}: ${twrr != null ? (parseFloat(twrr) * 100).toFixed(2) + '%' : '—'} | ${$_('dashboard.mwrr')}: ${mwrr != null ? (parseFloat(mwrr) * 100).toFixed(2) + '%' : '—'}`;
    });
    const roiIsPositive = $derived(summary ? parseFloat(summary.simple_roi_percent) >= 0 : undefined);

    /** URL for "See all" assets link — preserves current date range. */
    const assetsHref = $derived(`/assets?start=${dateFrom}&end=${dateTo}`);
    const transactionsHref = $derived(`/transactions?start=${dateFrom}&end=${dateTo}`);

    // =========================================================================
    // Loaders
    // =========================================================================

    async function loadSummary(force = false) {
        summaryLoading = true;
        try {
            summary = await fetchSummary(activeBrokerIds, false, targetCurrency, force);
        } finally {
            summaryLoading = false;
        }
    }

    async function loadHistory(force = false) {
        historyLoading = true;
        try {
            history = await fetchHistory(activeBrokerIds, dateFrom || undefined, dateTo || undefined, targetCurrency, force);
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
        dateFrom = from;
        dateTo = to;
        setDateRange(from, to);
        void loadHistory();
    }

    async function handleSync() {
        syncLoading = true;
        invalidate();
        await loadAll(true);
        syncLoading = false;
    }

    // Outside-click closes broker filter panel
    function handleDocumentClick(e: MouseEvent) {
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
            await ensurePluginIconsLoaded();
            await loadAll();
        })();
        return () => document.removeEventListener('click', handleDocumentClick);
    });
</script>

<div class="space-y-4" data-testid="dashboard-page">
    <h1 class="sr-only">{$_('nav.dashboard')}</h1>

    <!-- ── Header row: white card — DateRangePicker | Broker filter | spacer | Sync ── -->
    <div
        bind:this={filterBarRef}
        class="flex gap-3 p-4 bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700
               {layout.layoutMode === 'mobile' ? 'flex-col items-start' : 'flex-row items-center'}"
        data-testid="dashboard-filter-bar"
    >
        <!-- LEFT: Date range picker (wired to global store) -->
        <DateRangePicker bind:start={dateFrom} bind:end={dateTo} compact={true} onchange={handleDateChange} />

        <!-- CENTER-LEFT: Currency override selector -->
        <div class="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
            <span class="whitespace-nowrap">{$_('dashboard.displayCurrency')}:</span>
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
                            {@const iconUrl = getBrokerIconUrlById(broker.id, allBrokers)}
                            {@const isSelected = selectedBrokerIds.includes(broker.id)}
                            <button
                                type="button"
                                class="flex items-center gap-2 w-full px-2 py-1.5 text-left text-[13px] rounded hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors {isSelected ? 'text-blue-700 dark:text-blue-300' : 'text-gray-600 dark:text-gray-300'}"
                                onclick={() => toggleBroker(broker.id)}
                                data-testid="broker-filter-item-{broker.id}"
                            >
                                {#if iconUrl}
                                    <img
                                        src={iconUrl}
                                        alt=""
                                        class="w-4 h-4 rounded-sm object-contain flex-shrink-0"
                                        onerror={(e) => {
                                            (e.target as HTMLElement).style.display = 'none';
                                        }}
                                    />
                                {:else}
                                    <div class="w-4 h-4 rounded-sm bg-gray-100 dark:bg-slate-700 flex-shrink-0"></div>
                                {/if}
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

        <!-- FAR RIGHT: Sync button -->
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

    {#if missingPricesAssets.length > 0}
        <div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4 text-sm text-amber-700 dark:text-amber-400 flex items-start gap-2" data-testid="dashboard-missing-prices-banner">
            <span>⚠️</span>
            <span>
                {$_('dashboard.missingPricesPrefix')}
                <strong>{missingPricesAssets.join(', ')}</strong>.
                {$_('dashboard.missingPricesSuffix')}
            </span>
        </div>
    {/if}

    {#if missingFxPairs.length > 0}
        <div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4 text-sm text-amber-700 dark:text-amber-400 flex items-start gap-2" data-testid="dashboard-missing-fx-banner">
            <span>⚠️</span>
            <span>
                {$_('dashboard.missingFxPrefix')}
                <strong>{missingFxPairs.join(', ')}</strong>.
                {$_('dashboard.missingFxSuffix')}
            </span>
        </div>
    {/if}

    <!-- ── KPI Row ── -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="kpi-row">
        <KpiCard label={$_('dashboard.netWorth')} value={netWorthValue} subLabel={summary ? `${$_('common.cash')}: ${formatMoney(summary.cash_total.code, summary.cash_total.amount)}` : ''} loading={summaryLoading} />
        <KpiCard label={$_('dashboard.gainLoss')} value={gainLossValue} changePercent={gainLossPercent} positive={gainLossPercent !== undefined ? gainLossPercent >= 0 : undefined} loading={summaryLoading} />
        <KpiCard label={$_('dashboard.roiWeighted')} value={roiValue} subLabel={roiSubLabel} positive={roiIsPositive} loading={summaryLoading} />
    </div>

    <!-- ── Charts Row ── -->
    <div class="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <!-- Growth Chart — 3/5 -->
        <div class="lg:col-span-3">
            <GrowthChart {history} loading={historyLoading} baseCurrency={displayCurrency} />
        </div>

        <!-- Allocation Panel — 2/5 -->
        <div class="lg:col-span-2 bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm p-4 flex flex-col gap-3 min-h-[380px] lg:min-h-0" data-testid="allocation-panel">
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
                <div class="flex-1 bg-gray-100 dark:bg-slate-700 rounded animate-pulse"></div>
            {:else if !summary}
                <div class="flex-1 flex items-center justify-center text-sm text-gray-400 dark:text-gray-500">
                    {$_('dashboard.noData')}
                </div>
            {:else if allocationTab === 'type'}
                <div class="flex-1 min-h-0">
                    <AllocationPieChart data={allocationByType} height="100%" mode="type" legendPosition="bottom" />
                </div>
            {:else if allocationTab === 'sector'}
                <div class="flex-1 min-h-0">
                    <AllocationPieChart data={allocationBySector} height="100%" legendPosition="bottom" />
                </div>
            {:else}
                <div class="flex-1 min-h-0">
                    <GeographyMap data={allocationByGeo} height="100%" language={$currentLanguage} />
                </div>
            {/if}
        </div>
    </div>

    <!-- ── Bottom Grid: Holdings | Transactions ── -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- LEFT: Holdings panel -->
        <HoldingsPanel holdings={summary?.holdings ?? []} loading={summaryLoading} {assetsHref} />

        <!-- RIGHT: Recent Transactions -->
        <RecentTransactionsPanel limit={10} brokerIds={activeBrokerIds} {transactionsHref} />
    </div>
</div>
