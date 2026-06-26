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
    import {RefreshCw, PieChart, AreaChart} from 'lucide-svelte';

    import {fetchReport, invalidate, type PortfolioReport, type PortfolioSummary, type PortfolioHistoryPoint, type AllocationHistoryDimensions} from '$lib/stores/portfolio/portfolioStore.svelte';
    import {ensureBrokersLoaded, getAllBrokers} from '$lib/stores/reference/brokerStore';
    import {globalSettings} from '$lib/stores/app/globalSettings';
    import {getStart, getEnd, setDateRange} from '$lib/stores/dateRangeStore.svelte';
    import {getBrokerIconUrlById, ensurePluginIconsLoaded} from '$lib/utils/broker/brokerHelpers';
    import {getBrokerColor} from '$lib/utils/broker/brokerColors';
    import {createResponsiveLayout} from '$lib/utils/layout/responsiveLayout.svelte';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';

    import DateRangePicker from '$lib/components/ui/date/DateRangePicker.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import AllocationPieChart from '$lib/components/charts/AllocationPieChart.svelte';
    import AllocationHistoryChart from '$lib/components/dashboard/AllocationHistoryChart.svelte';
    import GeographyMap from '$lib/components/charts/GeographyMap.svelte';
    import GrowthChart from '$lib/components/dashboard/GrowthChart.svelte';
    import RecentTransactionsPanel from '$lib/components/dashboard/RecentTransactionsPanel.svelte';
    import HoldingsPanel from '$lib/components/dashboard/HoldingsPanel.svelte';
    import {DataQualityBanner} from '$lib/components/ui/feedback';
    import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import KpiMetricBar from '$lib/components/dashboard/KpiMetricBar.svelte';
    import KpiDivergingFlowBar from '$lib/components/dashboard/KpiDivergingFlowBar.svelte';
    import FxPairAddModal from '$lib/components/fx/FxPairAddModal.svelte';
    import {currentLanguage} from '$lib/stores/app/language';
    import {goto} from '$app/navigation';

    // =========================================================================
    // State
    // =========================================================================

    let summary = $state<PortfolioSummary | null>(null);
    let history = $state<PortfolioHistoryPoint[]>([]);
    let allocationHistoryFromReport = $state<AllocationHistoryDimensions | null>(null);
    let reportLoading = $state(true);
    // Keep separate loading flags for GrowthChart skeleton
    let summaryLoading = $derived(reportLoading);
    let historyLoading = $derived(reportLoading);
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

    /** Allocation view mode: Now (pie/map) or History (stacked area). */
    let allocationView = $state<'now' | 'history'>('now');

    /** Allocation history data — derived from report (no separate fetch needed). */
    let allocationHistoryLoading = $derived(reportLoading);

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

    /** Becomes true after ensurePluginIconsLoaded() resolves — forces broker
     *  filter icons to re-render once the plugin icon cache is ready. */
    let pluginIconsReady = $state(false);
    const allBrokers = $derived.by(() => {
        void pluginIconsReady; // Re-run after plugin icon cache is populated
        return getAllBrokers();
    });
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

    /** Safely extract a Currency object from Zodios Optional union type. */
    function safeCurrency(v: any): {code: string; amount: string} | null {
        if (v == null) return null;
        if (Array.isArray(v)) return v[0] ?? null;
        if (typeof v === 'object' && 'amount' in v) return v as {code: string; amount: string};
        return null;
    }

    function formatMoney(code: string | undefined, amount: string | null | undefined, opts?: {signed?: boolean; absolute?: boolean}): string {
        if (amount == null) return '—';
        const num = parseFloat(amount);
        const absolute = opts?.absolute ?? false;
        const rendered = absolute ? Math.abs(num) : num;
        const showSign = opts?.signed ?? false;
        return formatCurrencyAmountPlain(rendered, code ?? displayCurrency, {showSign});
    }

    /** Build tooltip HTML with right-aligned values for breakdown rows. */
    function tooltipRows(description: string, rows: {emoji: string; label: string; value: string}[]): string {
        let html = `<div style="font-size:12px;max-width:300px">${description}`;
        html += `<table style="width:100%;margin-top:6px;border-collapse:collapse">`;
        for (const r of rows) {
            html += `<tr><td style="white-space:nowrap">${r.emoji} ${r.label}</td><td style="text-align:right;padding-left:12px;white-space:nowrap;font-weight:500">${r.value}</td></tr>`;
        }
        html += `</table></div>`;
        return html;
    }

    /** Allocation data for charts — full AllocationEntry[] with amount and emoji. */
    type AllocEntry = {name: string; value: number; amount: number; emoji?: string | null};
    function toAllocEntries(items: any[] | null | undefined): AllocEntry[] {
        if (!items) return [];
        return (items as any[]).flatMap((i) => {
            const v = parseFloat(i?.value ?? '0');
            if (v <= 0) return [];
            return [{name: i.name ?? '', value: v, amount: parseFloat(i?.amount ?? '0'), emoji: i?.emoji ?? null}];
        });
    }
    const allocationByType = $derived(toAllocEntries(summary?.allocation_by_type as any));
    const allocationBySector = $derived(toAllocEntries(summary?.allocation_by_sector as any));
    const allocationByGeo = $derived(toAllocEntries(summary?.allocation_by_geography as any));
    // GeographyMap needs Record<string, number> (weight 0-1) and amounts by ISO A3
    const allocationByGeoMap = $derived(Object.fromEntries(allocationByGeo.map((e) => [e.name, e.value / 100])));
    const allocationByGeoAmounts = $derived(Object.fromEntries(allocationByGeo.filter((e) => e.amount > 0).map((e) => [e.name, e.amount])));
    const geoUnknownPercent = $derived.by(() => {
        const unknown = allocationByGeo.find((e) => e.name === 'Unknown');
        const other = allocationByGeo.find((e) => e.name === 'Other');
        return (unknown ? unknown.value : 0) + (other ? other.value : 0);
    });
    const dataQualityIssues = $derived<DataQualityIssue[]>((summary?.data_quality as {issues?: DataQualityIssue[]} | undefined)?.issues ?? []);

    /** Allocation history data — derived from report, keyed by active tab dimension. */
    const allocationHistoryData = $derived.by(() => {
        if (!allocationHistoryFromReport) return [];
        const dimMap: Record<string, keyof AllocationHistoryDimensions> = {type: 'type', sector: 'sector', geo: 'geography'};
        const dim = dimMap[allocationTab] ?? 'type';
        return (allocationHistoryFromReport as AllocationHistoryDimensions)[dim] ?? [];
    });

    /** FxPairAddModal state for CTA-driven pair creation */
    let showFxPairAddModal = $state(false);
    let fxPairCreateSlug = $state('');

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

    // KPI derived values — Net Worth card
    const netWorthValue = $derived(summary ? formatMoney(summary.net_worth.code, summary.net_worth.amount) : '—');
    const marketValueCur = $derived(summary ? safeCurrency(summary.market_value) : null);
    const marketValueAmt = $derived(marketValueCur ? parseFloat(marketValueCur.amount) : 0);
    const marketValueStr = $derived(marketValueCur ? formatMoney(marketValueCur.code, marketValueCur.amount) : '—');
    const marketValueStartCur = $derived(summary ? safeCurrency(summary.period_market_value_start) : null);
    const marketValueStartAmt = $derived(marketValueStartCur ? parseFloat(marketValueStartCur.amount) : 0);
    const marketValueStartStr = $derived(marketValueStartCur ? formatMoney(marketValueStartCur.code, marketValueStartCur.amount) : '');
    // Purchase Cost (= open_cost_basis: WAC × qty, excludes cash)
    const purchaseCostCur = $derived(summary ? safeCurrency(summary.open_cost_basis) : null);
    const purchaseCostAmt = $derived(purchaseCostCur ? parseFloat(purchaseCostCur.amount) : 0);
    const purchaseCostStr = $derived(purchaseCostCur ? formatMoney(purchaseCostCur.code, purchaseCostCur.amount) : '—');
    // For start-of-period marker, use period_book_value_start as a proxy (open_cost_basis at start is not exposed separately)
    const purchaseCostStartCur = $derived(summary ? safeCurrency(summary.period_book_value_start) : null);
    const purchaseCostStartAmt = $derived(purchaseCostStartCur ? parseFloat(purchaseCostStartCur.amount) : 0);
    const purchaseCostStartStr = $derived(purchaseCostStartCur ? formatMoney(purchaseCostStartCur.code, purchaseCostStartCur.amount) : '');
    const cashAmt = $derived(summary ? parseFloat(summary.cash_total.amount) : 0);
    const cashTotalStr = $derived(summary ? formatMoney(summary.cash_total.code, summary.cash_total.amount) : '—');

    // Cash breakdown from last history point (Capitale + Rendimento, for cash tooltip)
    const lastHistoryPoint = $derived(history.length > 0 ? history[history.length - 1] : null);
    const firstHistoryPoint = $derived(history.length > 0 ? history[0] : null);
    const cashContribAmt = $derived(lastHistoryPoint?.cash_from_contributed_capital != null ? parseFloat(lastHistoryPoint.cash_from_contributed_capital.amount) : null);
    const cashGeneratedAmt = $derived(lastHistoryPoint?.cash_from_generated_returns != null ? parseFloat(lastHistoryPoint.cash_from_generated_returns.amount) : null);
    const cashCurrency = $derived(summary?.cash_total.code ?? 'EUR');
    const cashContribStr = $derived(cashContribAmt != null ? formatMoney(cashCurrency, String(cashContribAmt)) : '—');
    const cashGeneratedStr = $derived(cashGeneratedAmt != null ? formatMoney(cashCurrency, String(cashGeneratedAmt)) : '—');
    // Cash at period start — from first history point
    const cashStartAmt = $derived(firstHistoryPoint?.cash_value != null ? parseFloat(firstHistoryPoint.cash_value.amount) : 0);
    const cashStartStr = $derived(firstHistoryPoint?.cash_value != null ? formatMoney(firstHistoryPoint.cash_value.code, firstHistoryPoint.cash_value.amount) : '');

    // Net Deposited Capital
    const netDepositedCur = $derived(summary ? safeCurrency(summary.net_deposited_capital) : null);
    const netDepositedAmt = $derived(netDepositedCur ? parseFloat(netDepositedCur.amount) : 0);
    const netDepositedStr = $derived(netDepositedCur ? formatMoney(netDepositedCur.code, netDepositedCur.amount, {signed: true}) : '—');
    const totalDepositedCur = $derived(summary ? safeCurrency(summary.total_deposited) : null);
    const totalDepositedStr = $derived(totalDepositedCur ? formatMoney(totalDepositedCur.code, totalDepositedCur.amount, {signed: true}) : '—');
    const totalWithdrawnCur = $derived(summary ? safeCurrency(summary.total_withdrawn) : null);
    const totalWithdrawnStr = $derived(totalWithdrawnCur ? formatMoney(totalWithdrawnCur.code, `-${totalWithdrawnCur.amount}`) : '—');
    const totalDepositedAmt = $derived(totalDepositedCur ? parseFloat(totalDepositedCur.amount) : 0);
    const totalWithdrawnAmt = $derived(totalWithdrawnCur ? parseFloat(totalWithdrawnCur.amount) : 0);
    const netDepositedPositive = $derived(netDepositedAmt >= 0);

    // Net Worth bars — all bars share same scale including NAV hero
    const navHeroAmt = $derived(summary ? parseFloat(summary.net_worth.amount) : 0);
    const nwBarMax = $derived(Math.max(navHeroAmt, marketValueStartAmt, marketValueAmt, purchaseCostAmt, purchaseCostStartAmt, cashAmt, cashStartAmt, totalDepositedAmt, totalWithdrawnAmt) || 1);
    const marketBarPct = $derived((marketValueAmt / nwBarMax) * 100);
    const purchaseCostBarPct = $derived((purchaseCostAmt / nwBarMax) * 100);
    const cashBarPct = $derived((cashAmt / nwBarMax) * 100);
    const depositBarPct = $derived((totalDepositedAmt / nwBarMax) * 100);
    const withdrawBarPct = $derived((totalWithdrawnAmt / nwBarMax) * 100);
    const marketStartMarkerPct = $derived(marketValueStartAmt > 0 ? (marketValueStartAmt / nwBarMax) * 100 : 0);
    const purchaseCostStartMarkerPct = $derived(purchaseCostStartAmt > 0 ? (purchaseCostStartAmt / nwBarMax) * 100 : 0);
    const cashStartMarkerPct = $derived(cashStartAmt > 0 ? (cashStartAmt / nwBarMax) * 100 : 0);
    const marketBarColor = $derived(marketValueAmt >= marketValueStartAmt ? 'bg-green-500 dark:bg-green-400' : 'bg-red-400 dark:bg-red-500');

    // KPI derived values — Period P&L card
    const periodPnlCur = $derived(summary ? safeCurrency(summary.period_pnl) : null);
    const periodPnlStr = $derived(periodPnlCur ? formatMoney(periodPnlCur.code, periodPnlCur.amount, {signed: true}) : '—');
    const periodPnlPositive = $derived(periodPnlCur ? parseFloat(periodPnlCur.amount) >= 0 : undefined);

    // P&L breakdown values
    const uglDeltaCur = $derived(summary ? safeCurrency(summary.period_unrealized_gain_loss_delta) : null);
    const uglDeltaAmt = $derived(uglDeltaCur ? parseFloat(uglDeltaCur.amount) : 0);
    const uglDeltaStr = $derived(uglDeltaCur ? formatMoney(uglDeltaCur.code, uglDeltaCur.amount, {signed: true}) : '—');
    const realizedCur = $derived(summary ? safeCurrency(summary.period_realized_gain_loss) : null);
    const realizedAmt = $derived(realizedCur ? parseFloat(realizedCur.amount) : 0);
    const realizedStr = $derived(realizedCur ? formatMoney(realizedCur.code, realizedCur.amount, {signed: true}) : '—');
    const incomeCur = $derived(summary ? safeCurrency(summary.period_income) : null);
    const incomeAmt = $derived(incomeCur ? parseFloat(incomeCur.amount) : 0);
    const incomeStr = $derived(incomeCur ? formatMoney(incomeCur.code, incomeCur.amount, {signed: true}) : '—');
    const feesCur = $derived(summary ? safeCurrency(summary.period_fees_taxes) : null);
    const feesAmt = $derived(feesCur ? parseFloat(feesCur.amount) : 0);
    const feesStr = $derived(feesCur ? formatMoney(feesCur.code, `-${feesCur.amount}`) : '—');
    const feesOnlyCur = $derived(summary ? safeCurrency(summary.period_fees) : null);
    const feesOnlyStr = $derived(feesOnlyCur ? formatMoney(feesOnlyCur.code, `-${feesOnlyCur.amount}`) : '—');
    const taxesOnlyCur = $derived(summary ? safeCurrency(summary.period_taxes) : null);
    const taxesOnlyStr = $derived(taxesOnlyCur ? formatMoney(taxesOnlyCur.code, `-${taxesOnlyCur.amount}`) : '—');

    // HTML tooltips with right-aligned numbers
    const netDepositedTooltipHtml = $derived(tooltipRows(
        $_('dashboard.netDepositedCapitalTooltip', {values: {deposited: '', withdrawn: ''}}).split('\n')[0],
        [{emoji: '🟢', label: $_('dashboard.totalDeposited'), value: totalDepositedStr}, {emoji: '🔴', label: $_('dashboard.totalWithdrawn'), value: totalWithdrawnStr}]
    ));
    const feesTooltipHtml = $derived(tooltipRows(
        $_('dashboard.feesAndTaxesTooltip', {values: {fees: '', taxes: ''}}).split('\n')[0],
        [{emoji: '🏦', label: $_('dashboard.feesLabel') || 'Commissions', value: feesOnlyStr}, {emoji: '🏛️', label: $_('dashboard.taxesLabel') || 'Taxes', value: taxesOnlyStr}]
    ));
    // Cash tooltip: breakdown into Capitale (contributed) + Rendimento (generated)
    const cashTooltipHtml = $derived((() => {
        if (cashContribAmt == null && cashGeneratedAmt == null) return undefined;
        return tooltipRows($_('dashboard.cashValueTooltip'), [
            {emoji: '💼', label: $_('dashboard.cashFromContributedCapital'), value: cashContribStr},
            {emoji: '🌱', label: $_('dashboard.cashFromGeneratedReturns'), value: cashGeneratedStr},
        ]);
    })());

    // P&L bar normalization
    const pnlBarMax = $derived(Math.max(Math.abs(uglDeltaAmt), Math.abs(realizedAmt), Math.abs(incomeAmt), feesAmt) || 1);
    function pnlBarPct(val: number) { return (Math.abs(val) / pnlBarMax) * 100; }
    function pnlBarColor(val: number) { return val >= 0 ? 'bg-green-500 dark:bg-green-400' : 'bg-red-400 dark:bg-red-500'; }
    function pnlValueColor(val: number) { return val >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'; }

    // KPI derived values — Returns card
    const roiVal = $derived(summary ? parseFloat(summary.simple_roi_percent) * 100 : 0);
    const twrrCumVal = $derived.by(() => { const v = summary ? safeStr(summary.twrr_percent) : null; return v != null ? parseFloat(v) * 100 : 0; });
    const mwrrCumVal = $derived.by(() => { const v = summary ? safeStr(summary.mwrr_cumulative_percent) : null; return v != null ? parseFloat(v) * 100 : 0; });
    const mwrrAnnVal = $derived.by(() => { const v = summary ? safeStr(summary.mwrr_annualized_percent) : null; return v != null ? parseFloat(v) * 100 : 0; });
    const timingEffectVal = $derived(mwrrCumVal - twrrCumVal);
    const timingEffectStr = $derived.by(() => {
        if (!summary) return '—';
        const formatted = Math.abs(timingEffectVal).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
        return `${timingEffectVal >= 0 ? '+' : '-'}${formatted} ${$_('dashboard.pp')}`;
    });
    const timingIntensity = $derived(Math.min(Math.abs(timingEffectVal) / 3, 1));
    const timingLabel = $derived.by(() => {
        if (Math.abs(timingEffectVal) < 0.05) return $_('dashboard.timingNeutral');
        return timingEffectVal > 0 ? $_('dashboard.timingFavorable') : $_('dashboard.timingUnfavorable');
    });
    const roiPct = $derived(summary ? `${roiVal.toFixed(2)}%` : '—');
    const twrrCumPct = $derived(summary ? `${twrrCumVal.toFixed(2)}%` : '—');
    const mwrrCumPct = $derived(summary ? `${mwrrCumVal.toFixed(2)}%` : '—');
    const mwrrAnnPct = $derived(summary ? `${mwrrAnnVal.toFixed(2)}%` : '—');
    const roiIsPositive = $derived(summary ? parseFloat(summary.simple_roi_percent) >= 0 : undefined);

    // Returns bar normalization
    const retBarMax = $derived(Math.max(Math.abs(roiVal), Math.abs(twrrCumVal), Math.abs(mwrrCumVal), Math.abs(mwrrAnnVal)) || 1);
    function retBarPct(val: number) { return (Math.abs(val) / retBarMax) * 100; }
    function retBarColor(val: number) { return val >= 0 ? 'bg-green-500 dark:bg-green-400' : 'bg-red-400 dark:bg-red-500'; }

    /** URL for "See all" assets link — preserves current date range. */
    const assetsHref = $derived(`/assets?start=${dateFrom}&end=${dateTo}`);
    const transactionsHref = $derived(`/transactions?start=${dateFrom}&end=${dateTo}`);

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

    async function loadAll(force = false) {
        // Invalidate allocation history cache whenever filters change
        allocationHistoryCacheKey = null;
        reportLoading = true;
        try {
            const report = await fetchReport(activeBrokerIds, dateFrom || undefined, dateTo || undefined, targetCurrency, force);
            // Cast from the Zodios union types to the concrete types the dashboard expects
            summary = (report?.summary as PortfolioSummary | null | undefined) ?? null;
            history = (report?.history as PortfolioHistoryPoint[] | null | undefined) ?? [];
            allocationHistoryFromReport = (report?.allocation_history as AllocationHistoryDimensions | null | undefined) ?? null;
        } finally {
            reportLoading = false;
        }
    }

    /** Build a cache key that captures all query parameters. */
    function allocHistoryCacheKey(dimension: string) {
        return `${dimension}|${dateFrom ?? ''}|${dateTo ?? ''}|${(activeBrokerIds ?? []).join(',')}|${targetCurrency ?? ''}`;
    }

    let allocationHistoryCacheKey = $state<string | null>(null);

    async function loadAllocationHistory(dimension: string) {
        // Allocation history is included in the report — no additional fetch needed
        // Mark cache key as loaded so subsequent tab switches don't trigger re-fetch
        const dimMap: Record<string, string> = {type: 'type', sector: 'sector', geo: 'geography'};
        const apiDimension = dimMap[dimension] || 'type';
        allocationHistoryCacheKey = allocHistoryCacheKey(apiDimension);
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
        void loadAll();
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
            pluginIconsReady = true;
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
                            {@const dotColor = getBrokerColor(broker.id, allBrokers).bg}
                            {@const isSelected = selectedBrokerIds.includes(broker.id)}
                            <button
                                type="button"
                                class="flex items-center gap-2 w-full px-2 py-1.5 text-left text-[13px] rounded hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors {isSelected ? 'text-blue-700 dark:text-blue-300' : 'text-gray-600 dark:text-gray-300'}"
                                onclick={() => toggleBroker(broker.id)}
                                data-testid="broker-filter-item-{broker.id}"
                            >
                                <!-- Overlay: colored dot underneath, img on top (hidden on error) -->
                                <span class="relative w-4 h-4 flex-shrink-0 flex items-center justify-center">
                                    <span class="absolute inset-0 rounded-sm" style="background: {dotColor}"></span>
                                    {#if iconUrl}
                                        <img
                                            src={iconUrl}
                                            alt=""
                                            class="absolute inset-0 w-4 h-4 rounded-sm object-contain"
                                            referrerpolicy="no-referrer"
                                            onerror={(e) => {
                                                (e.target as HTMLImageElement).style.visibility = 'hidden';
                                            }}
                                        />
                                    {/if}
                                </span>
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

    <DataQualityBanner issues={dataQualityIssues} mode="grouped" onaction={handleBannerAction} />

    <!-- ── KPI Row ── -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="kpi-row">
        <!-- Card 1 — Period P&L -->
        <div class="relative bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm p-5 flex flex-col gap-2 overflow-hidden" data-testid="kpi-period-pnl">
            {#if periodPnlPositive !== undefined}
                <div class="absolute top-0 left-0 right-0 h-0.5 {periodPnlPositive ? 'bg-green-500 dark:bg-green-400' : 'bg-red-500 dark:bg-red-400'}"></div>
            {/if}
            <div class="flex items-center justify-between">
                <p class="text-xs font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500">{$_('dashboard.periodPnl')}</p>
                <DocsLink path="financial-theory/technical-analysis/performance-metrics/period-pnl/" label={$_('dashboard.periodPnl')} size={14} />
            </div>
            {#if summaryLoading}
                <div class="h-7 w-3/4 bg-gray-200 dark:bg-slate-700 rounded animate-pulse"></div>
                <div class="h-3 w-1/2 bg-gray-100 dark:bg-slate-700 rounded animate-pulse mt-2"></div>
            {:else}
                <p class="text-2xl font-bold text-right {periodPnlPositive === true ? 'text-green-700 dark:text-green-400' : periodPnlPositive === false ? 'text-red-700 dark:text-red-400' : 'text-gray-800 dark:text-gray-100'}" data-testid="kpi-value">{periodPnlStr}</p>
                <div class="flex flex-col gap-2 mt-1">
                    <KpiMetricBar label={$_('dashboard.unrealizedDelta')} tooltip={$_('dashboard.unrealizedDeltaTooltip')} value={uglDeltaStr} barPct={pnlBarPct(uglDeltaAmt)} barColor={pnlBarColor(uglDeltaAmt)} valueColor={pnlValueColor(uglDeltaAmt)} />
                    <KpiMetricBar label={$_('dashboard.realizedSales')} tooltip={$_('dashboard.realizedSalesTooltip')} value={realizedStr} barPct={pnlBarPct(realizedAmt)} barColor={pnlBarColor(realizedAmt)} valueColor={pnlValueColor(realizedAmt)} />
                    <KpiMetricBar label={$_('dashboard.income')} tooltip={$_('dashboard.incomeTooltip')} value={incomeStr} barPct={pnlBarPct(incomeAmt)} barColor="bg-green-500 dark:bg-green-400" valueColor="text-green-600 dark:text-green-400" />
                    <KpiMetricBar label={$_('dashboard.feesAndTaxes')} tooltipHtml={feesTooltipHtml} value={feesStr} barPct={pnlBarPct(feesAmt)} barColor="bg-red-400 dark:bg-red-500" valueColor="text-red-600 dark:text-red-400" />
                </div>
                <p class="text-[10px] text-gray-400 dark:text-gray-600 mt-1 italic">{$_('dashboard.cashFlowAdjustedResult')}</p>
            {/if}
        </div>

        <!-- Card 2 — Returns -->
        <div class="relative bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm p-5 flex flex-col gap-2 overflow-hidden" data-testid="kpi-returns">
            {#if roiIsPositive !== undefined}
                <div class="absolute top-0 left-0 right-0 h-0.5 {roiIsPositive ? 'bg-green-500 dark:bg-green-400' : 'bg-red-500 dark:bg-red-400'}"></div>
            {/if}
            <div class="flex items-center justify-between">
                <p class="text-xs font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500">{$_('dashboard.returns')}</p>
                <DocsLink path="financial-theory/technical-analysis/performance-metrics/" label={$_('dashboard.returns')} size={14} />
            </div>
            {#if summaryLoading}
                <div class="h-7 w-3/4 bg-gray-200 dark:bg-slate-700 rounded animate-pulse"></div>
                <div class="h-3 w-1/2 bg-gray-100 dark:bg-slate-700 rounded animate-pulse mt-2"></div>
            {:else}
                <!-- Timing effect hero (no bar) -->
                <div class="flex items-center justify-between">
                    <Tooltip text={$_('dashboard.timingEffectTooltip')} position="top">
                        <div class="flex flex-col cursor-help">
                            <span class="text-[10px] text-gray-400 dark:text-gray-500 uppercase tracking-wide border-b border-dotted border-gray-300 dark:border-gray-600 inline-block">{$_('dashboard.timingEffect')}</span>
                            <span class="text-[10px] italic" style="color: {timingEffectVal >= 0 ? `rgba(22, 163, 74, ${0.4 + timingIntensity * 0.6})` : `rgba(220, 38, 38, ${0.4 + timingIntensity * 0.6})`}">{timingLabel}</span>
                        </div>
                    </Tooltip>
                    <span class="text-2xl font-bold tabular-nums transition-colors" style="color: {timingEffectVal >= 0 ? `rgba(22, 163, 74, ${0.3 + timingIntensity * 0.7})` : `rgba(220, 38, 38, ${0.3 + timingIntensity * 0.7})`}">{timingEffectStr}</span>
                </div>
                <div class="flex flex-col gap-2 mt-1">
                    <KpiMetricBar label={$_('dashboard.roi')} tooltip={$_('dashboard.roiTooltip')} value={roiPct} barPct={retBarPct(roiVal)} barColor={retBarColor(roiVal)} valueColor="font-bold text-gray-800 dark:text-gray-100" />
                    <KpiMetricBar label={$_('dashboard.twrrCum')} tooltip={$_('dashboard.twrrTooltip')} value={twrrCumPct} barPct={retBarPct(twrrCumVal)} barColor={retBarColor(twrrCumVal)} />
                    <KpiMetricBar label={$_('dashboard.mwrrCum')} tooltip={$_('dashboard.mwrrCumTooltip')} value={mwrrCumPct} barPct={retBarPct(mwrrCumVal)} barColor={retBarColor(mwrrCumVal)} />
                    <KpiMetricBar label={$_('dashboard.mwrrAnn')} tooltip={$_('dashboard.mwrrAnnTooltip')} value={mwrrAnnPct} barPct={retBarPct(mwrrAnnVal)} barColor={retBarColor(mwrrAnnVal)} />
                </div>
                <p class="text-[10px] text-gray-400 dark:text-gray-600 mt-1 italic">{$_('dashboard.periodBasedReturns')}</p>
            {/if}
        </div>

        <!-- Card 3 — Net Worth -->
        <div class="relative bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm p-5 flex flex-col gap-2 overflow-hidden" data-testid="kpi-net-worth">
            <div class="flex items-center justify-between">
                <p class="text-xs font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500">{$_('dashboard.netWorth')}</p>
                <DocsLink path="financial-theory/technical-analysis/performance-metrics/nav/" label={$_('dashboard.netWorth')} size={14} />
            </div>
            {#if summaryLoading}
                <div class="h-7 w-3/4 bg-gray-200 dark:bg-slate-700 rounded animate-pulse"></div>
                <div class="h-3 w-1/2 bg-gray-100 dark:bg-slate-700 rounded animate-pulse mt-2"></div>
            {:else}
                <p class="text-2xl font-bold text-gray-800 dark:text-gray-100 text-right" data-testid="kpi-value">{netWorthValue}</p>
                <div class="flex flex-col gap-2 mt-1">
                    <KpiMetricBar label={$_('dashboard.marketValue')} tooltip={$_('dashboard.marketValueTooltip')} value={marketValueStr} barPct={marketBarPct} barColor={marketBarColor} marker={marketStartMarkerPct > 0 ? marketStartMarkerPct : undefined} markerTooltip="{$_('dashboard.marketValueStart')}: {marketValueStartStr}" />
                    <KpiMetricBar label={$_('dashboard.bookValue')} tooltip={$_('dashboard.bookValueTooltip')} value={purchaseCostStr} barPct={purchaseCostBarPct} barColor="bg-blue-500 dark:bg-blue-400" marker={purchaseCostStartMarkerPct > 0 ? purchaseCostStartMarkerPct : undefined} markerTooltip="{$_('dashboard.bookValueStart')}: {purchaseCostStartStr}" />
                    <KpiMetricBar label={$_('dashboard.cashValue')} tooltipHtml={cashTooltipHtml} tooltip={cashTooltipHtml ? undefined : $_('dashboard.cashValueTooltip')} value={cashTotalStr} barPct={cashBarPct} barColor="bg-emerald-500 dark:bg-emerald-400" marker={cashStartMarkerPct > 0 ? cashStartMarkerPct : undefined} markerTooltip="{$_('dashboard.cashValueStart')}: {cashStartStr}" />
                    <KpiDivergingFlowBar
                        label={$_('dashboard.netDepositedCapital')}
                        tooltipHtml={netDepositedTooltipHtml}
                        value={netDepositedStr}
                        depositPct={depositBarPct}
                        withdrawPct={withdrawBarPct}
                        valueColor={netDepositedPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}
                    />
                </div>
                <p class="text-[10px] text-gray-400 dark:text-gray-600 mt-1 italic">{$_('dashboard.periodScopeNote')}</p>
            {/if}
        </div>
    </div>

    <!-- ── Charts Row ── -->
    <div class="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <!-- Growth Chart — 3/5 -->
        <div class="lg:col-span-3">
            <GrowthChart {history} loading={historyLoading} baseCurrency={displayCurrency} />
        </div>

        <!-- Allocation Panel — 2/5 -->
        <div class="lg:col-span-2 bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm p-4 flex flex-col gap-3 min-h-[380px] lg:min-h-0" data-testid="allocation-panel">
            <div class="flex items-center justify-between">
                <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-200">{$_('dashboard.allocation')}</h2>
                <!-- Now / History toggle -->
                <div class="flex rounded-lg overflow-hidden border border-gray-200 dark:border-slate-600 text-xs font-medium">
                    <button
                        class="px-2.5 py-1.5 transition-colors {allocationView === 'now' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                        onclick={() => (allocationView = 'now')}
                        data-testid="allocation-view-now"
                        title={$_('dashboard.now')}
                    ><PieChart size={14} /></button>
                    <button
                        class="px-2.5 py-1.5 transition-colors border-l border-gray-200 dark:border-slate-600 {allocationView === 'history' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                        onclick={() => { allocationView = 'history'; loadAllocationHistory(allocationTab); }}
                        data-testid="allocation-view-history"
                        title={$_('dashboard.history')}
                    ><AreaChart size={14} /></button>
                </div>
            </div>

            <!-- Tab bar -->
            <div class="flex rounded-lg overflow-hidden border border-gray-200 dark:border-slate-600 text-xs font-medium self-start">
                {#each [['type', 'dashboard.typeAllocation'], ['sector', 'dashboard.sectorAllocation'], ['geo', 'dashboard.geoAllocation']] as const as [tab, labelKey]}
                    <button
                        class="px-3 py-1 transition-colors {allocationTab === tab ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'} {tab !== 'type' ? 'border-l border-gray-200 dark:border-slate-600' : ''}"
                        onclick={() => { allocationTab = tab; if (allocationView === 'history') loadAllocationHistory(tab); }}
                        data-testid="allocation-tab-{tab}"
                    >
                        {$_(labelKey)}
                    </button>
                {/each}
            </div>

            <!-- Chart area -->
            {#if summaryLoading || allocationHistoryLoading}
                <div class="flex-1 bg-gray-100 dark:bg-slate-700 rounded animate-pulse"></div>
            {:else if allocationView === 'history'}
                <div class="flex-1 min-h-0">
                    <AllocationHistoryChart data={allocationHistoryData} dimension={allocationTab} height="100%" loading={allocationHistoryLoading} />
                </div>
            {:else if !summary}
                <div class="flex-1 flex items-center justify-center text-sm text-gray-400 dark:text-gray-500">
                    {$_('dashboard.noData')}
                </div>
            {:else if allocationTab === 'type'}
                <div class="flex-1 min-h-0">
                    <AllocationPieChart data={allocationByType} height="100%" mode="type" legendPosition="bottom" currency={displayCurrency} />
                </div>
            {:else if allocationTab === 'sector'}
                <div class="flex-1 min-h-0">
                    <AllocationPieChart data={allocationBySector} height="100%" legendPosition="bottom" currency={displayCurrency} />
                </div>
            {:else}
                <div class="flex-1 min-h-0">
                    <GeographyMap data={allocationByGeoMap} amounts={allocationByGeoAmounts} currency={displayCurrency} height="100%" language={$currentLanguage} />
                </div>
                {#if geoUnknownPercent > 0}
                    <p class="text-xs text-gray-400 dark:text-gray-500 text-center mt-1">
                        {$_('dashboard.geoUnknownNote', {values: {percent: geoUnknownPercent.toFixed(1)}})}
                    </p>
                {/if}
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

<!-- FxPairAddModal — opened from DataQualityBanner CTA -->
{#if showFxPairAddModal}
    {@const fxParts = fxPairCreateSlug.includes('-') ? fxPairCreateSlug.split('-') : fxPairCreateSlug.split('/')}
    <FxPairAddModal bind:open={showFxPairAddModal} initialBase={fxParts[0] ?? ''} initialQuote={fxParts[1] ?? ''} oncreated={() => { invalidate(); loadAll(); }} />
{/if}
