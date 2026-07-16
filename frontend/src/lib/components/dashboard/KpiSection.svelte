<!--
  KpiSection — Dashboard KPI row with Period P&L, Returns, Net Worth.

  Extracted from dashboard/+page.svelte as behavior-preserving refactor.
  Keep markup/data-testid/i18n/colors identical for safe reuse.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import type {PortfolioSummary, PortfolioHistoryPoint} from '$lib/stores/portfolio/portfolioStore.svelte';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';

    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import TweenedValue from '$lib/components/ui/TweenedValue.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import KpiMetricBar from '$lib/components/dashboard/KpiMetricBar.svelte';
    import KpiDivergingFlowBar from '$lib/components/dashboard/KpiDivergingFlowBar.svelte';

    interface Props {
        summary: PortfolioSummary | null;
        history: PortfolioHistoryPoint[];
        loading: boolean;
        displayCurrency: string;
    }

    let {summary, history, loading, displayCurrency}: Props = $props();

    function safeStr(v: string | (string | null)[] | null | undefined): string | null {
        if (v == null) return null;
        if (Array.isArray(v)) return v[0] ?? null;
        return v;
    }

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

    function tooltipRows(description: string, rows: {emoji: string; label: string; value: string}[]): string {
        let html = `<div style="font-size:12px;max-width:300px">${description}`;
        html += `<table style="width:100%;margin-top:6px;border-collapse:collapse">`;
        for (const r of rows) {
            html += `<tr><td style="white-space:nowrap">${r.emoji} ${r.label}</td><td style="text-align:right;padding-left:12px;white-space:nowrap;font-weight:500">${r.value}</td></tr>`;
        }
        html += `</table></div>`;
        return html;
    }

    const marketValueCur = $derived(summary ? safeCurrency(summary.market_value) : null);
    const marketValueAmt = $derived(marketValueCur ? parseFloat(marketValueCur.amount) : 0);
    const marketValueStr = $derived(marketValueCur ? formatMoney(marketValueCur.code, marketValueCur.amount) : '—');
    const marketValueStartCur = $derived(summary ? safeCurrency(summary.period_market_value_start) : null);
    const marketValueStartAmt = $derived(marketValueStartCur ? parseFloat(marketValueStartCur.amount) : 0);
    const marketValueStartStr = $derived(marketValueStartCur ? formatMoney(marketValueStartCur.code, marketValueStartCur.amount) : '');

    const purchaseCostCur = $derived(summary ? safeCurrency(summary.open_cost_basis) : null);
    const purchaseCostAmt = $derived(purchaseCostCur ? parseFloat(purchaseCostCur.amount) : 0);
    const purchaseCostStr = $derived(purchaseCostCur ? formatMoney(purchaseCostCur.code, purchaseCostCur.amount) : '—');
    const purchaseCostStartCur = $derived(summary ? safeCurrency(summary.period_book_value_start) : null);
    const purchaseCostStartAmt = $derived(purchaseCostStartCur ? parseFloat(purchaseCostStartCur.amount) : 0);
    const purchaseCostStartStr = $derived(purchaseCostStartCur ? formatMoney(purchaseCostStartCur.code, purchaseCostStartCur.amount) : '');
    const cashAmt = $derived(summary ? parseFloat(summary.cash_total.amount) : 0);
    const cashTotalStr = $derived(summary ? formatMoney(summary.cash_total.code, summary.cash_total.amount) : '—');

    const lastHistoryPoint = $derived(history.length > 0 ? history[history.length - 1] : null);
    const firstHistoryPoint = $derived(history.length > 0 ? history[0] : null);
    const prevHistoryPoint = $derived(history.length > 1 ? history[history.length - 2] : null);

    const pnlDeltaDay = $derived.by(() => {
        if (!lastHistoryPoint || !prevHistoryPoint) return null;
        const last = parseFloat(lastHistoryPoint.total_pnl.amount);
        const prev = parseFloat(prevHistoryPoint.total_pnl.amount);
        return last - prev;
    });
    const pnlDeltaDayPct = $derived.by(() => {
        if (!lastHistoryPoint || !prevHistoryPoint) return null;
        const prevNav = parseFloat(prevHistoryPoint.nav_value.amount);
        if (prevNav === 0 || pnlDeltaDay == null) return null;
        return ((pnlDeltaDay / prevNav) * 100).toFixed(2);
    });
    const periodPnlDeltaDayPct = $derived.by(() => {
        if (!firstHistoryPoint || !prevHistoryPoint || firstHistoryPoint === prevHistoryPoint || pnlDeltaDay == null) return null;
        const firstTotalPnl = parseFloat(firstHistoryPoint.total_pnl.amount);
        const prevTotalPnl = parseFloat(prevHistoryPoint.total_pnl.amount);
        const periodPnlYesterday = prevTotalPnl - firstTotalPnl;
        if (!Number.isFinite(periodPnlYesterday) || Math.abs(periodPnlYesterday) < 0.01) return null;
        return ((pnlDeltaDay / periodPnlYesterday) * 100).toFixed(2);
    });

    const cashContribAmt = $derived(lastHistoryPoint?.cash_from_contributed_capital != null ? parseFloat(lastHistoryPoint.cash_from_contributed_capital.amount) : null);
    const cashGeneratedAmt = $derived(lastHistoryPoint?.cash_from_generated_returns != null ? parseFloat(lastHistoryPoint.cash_from_generated_returns.amount) : null);
    const cashCurrency = $derived(summary?.cash_total.code ?? 'EUR');
    const cashContribStr = $derived(cashContribAmt != null ? formatMoney(cashCurrency, String(cashContribAmt)) : '—');
    const cashGeneratedStr = $derived(cashGeneratedAmt != null ? formatMoney(cashCurrency, String(cashGeneratedAmt)) : '—');
    const cashStartAmt = $derived(firstHistoryPoint?.cash_value != null ? parseFloat(firstHistoryPoint.cash_value.amount) : 0);
    const cashStartStr = $derived(firstHistoryPoint?.cash_value != null ? formatMoney(firstHistoryPoint.cash_value.code, firstHistoryPoint.cash_value.amount) : '');

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

    const navHeroAmt = $derived(summary ? parseFloat(summary.net_worth.amount) : 0);
    const totalPnlCur = $derived(summary ? safeCurrency(summary.total_gain_loss) : null);
    const totalPnlAmt = $derived.by(() => {
        if (!totalPnlCur) return null;
        const amount = parseFloat(totalPnlCur.amount);
        return Number.isFinite(amount) ? amount : null;
    });
    const totalPnlDeltaPct = $derived.by(() => {
        if (!prevHistoryPoint || pnlDeltaDay == null) return null;
        const prevTotalPnl = parseFloat(prevHistoryPoint.total_pnl.amount);
        if (!Number.isFinite(prevTotalPnl) || Math.abs(prevTotalPnl) < 0.01) return null;
        return ((pnlDeltaDay / prevTotalPnl) * 100).toFixed(2);
    });
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

    const periodPnlCur = $derived(summary ? safeCurrency(summary.period_pnl) : null);
    const periodPnlAmt = $derived(periodPnlCur ? parseFloat(periodPnlCur.amount) : 0);
    const periodPnlPositive = $derived(periodPnlCur ? parseFloat(periodPnlCur.amount) >= 0 : undefined);

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
    // Backend returns period_fees_taxes as a positive magnitude (see schema docstring); negate for display.
    const feesAmt = $derived(feesCur ? -parseFloat(feesCur.amount) : 0);
    const feesStr = $derived(feesCur ? formatMoney(feesCur.code, `-${feesCur.amount}`) : '—');
    const feesOnlyCur = $derived(summary ? safeCurrency(summary.period_fees) : null);
    const feesOnlyStr = $derived(feesOnlyCur ? formatMoney(feesOnlyCur.code, `-${feesOnlyCur.amount}`) : '—');
    const taxesOnlyCur = $derived(summary ? safeCurrency(summary.period_taxes) : null);
    const taxesOnlyStr = $derived(taxesOnlyCur ? formatMoney(taxesOnlyCur.code, `-${taxesOnlyCur.amount}`) : '—');

    const netDepositedTooltipHtml = $derived(
        tooltipRows($_('dashboard.netDepositedCapitalTooltip', {values: {deposited: '', withdrawn: ''}}).split('\n')[0], [
            {emoji: '🟢', label: $_('dashboard.totalDeposited'), value: totalDepositedStr},
            {emoji: '🔴', label: $_('dashboard.totalWithdrawn'), value: totalWithdrawnStr},
        ]),
    );
    const feesTooltipHtml = $derived(
        tooltipRows($_('dashboard.feesAndTaxesTooltip', {values: {fees: '', taxes: ''}}).split('\n')[0], [
            {emoji: '🏦', label: $_('dashboard.feesLabel') || 'Commissions', value: feesOnlyStr},
            {emoji: '🏛️', label: $_('dashboard.taxesLabel') || 'Taxes', value: taxesOnlyStr},
        ]),
    );
    const cashTooltipHtml = $derived(
        (() => {
            if (cashContribAmt == null && cashGeneratedAmt == null) return undefined;
            return tooltipRows($_('dashboard.cashValueTooltip'), [
                {emoji: '💼', label: $_('dashboard.cashFromContributedCapital'), value: cashContribStr},
                {emoji: '🌱', label: $_('dashboard.cashFromGeneratedReturns'), value: cashGeneratedStr},
            ]);
        })(),
    );

    const pnlBarMax = $derived(Math.max(Math.abs(uglDeltaAmt), Math.abs(realizedAmt), Math.abs(incomeAmt), Math.abs(feesAmt)) || 1);
    function pnlBarPct(val: number) {
        return (Math.abs(val) / pnlBarMax) * 100;
    }
    function pnlBarColor(val: number) {
        return val >= 0 ? 'bg-green-500 dark:bg-green-400' : 'bg-red-400 dark:bg-red-500';
    }
    function pnlValueColor(val: number) {
        return val >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';
    }

    const roiVal = $derived(summary ? parseFloat(summary.simple_roi_percent) * 100 : 0);
    const twrrCumVal = $derived.by(() => {
        const v = summary ? safeStr(summary.twrr_percent) : null;
        return v != null ? parseFloat(v) * 100 : 0;
    });
    const mwrrCumVal = $derived.by(() => {
        const v = summary ? safeStr(summary.mwrr_cumulative_percent) : null;
        return v != null ? parseFloat(v) * 100 : 0;
    });
    const mwrrAnnVal = $derived.by(() => {
        const v = summary ? safeStr(summary.mwrr_annualized_percent) : null;
        return v != null ? parseFloat(v) * 100 : 0;
    });
    const timingEffectVal = $derived(mwrrCumVal - twrrCumVal);
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

    const retBarMax = $derived(Math.max(Math.abs(roiVal), Math.abs(twrrCumVal), Math.abs(mwrrCumVal), Math.abs(mwrrAnnVal)) || 1);
    function retBarPct(val: number) {
        return (Math.abs(val) / retBarMax) * 100;
    }
    function retBarColor(val: number) {
        return val >= 0 ? 'bg-green-500 dark:bg-green-400' : 'bg-red-400 dark:bg-red-500';
    }

    const fmtMoney = (v: number) => formatCurrencyAmountPlain(v, displayCurrency, {showSign: true});
    const fmtMoneyUnsigned = (v: number) => formatCurrencyAmountPlain(v, displayCurrency, {showSign: false});
    const fmtPct = (v: number) => `${v.toFixed(2)}%`;
</script>

<div class="grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="kpi-row">
    <!-- Card 1 — Period P&L -->
    <div class="relative @container bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm p-5 flex flex-col gap-2 overflow-hidden" data-testid="kpi-period-pnl">
        {#if periodPnlPositive !== undefined}
            <div class="absolute top-0 left-0 right-0 h-0.5 {periodPnlPositive ? 'bg-green-500 dark:bg-green-400' : 'bg-red-500 dark:bg-red-400'}"></div>
        {/if}
        <div class="flex items-center justify-between">
            <p class="text-xs font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500">{$_('dashboard.periodPnl')}</p>
            <DocsLink path="user/dashboard/kpi-cards/#card-1-period-pl" label={$_('dashboard.periodPnl')} size={14} />
        </div>
        <div class="relative">
            {#if loading}
                <div class="absolute inset-0 z-10 flex flex-col gap-2">
                    <div class="h-7 w-3/4 bg-gray-200 dark:bg-slate-700 rounded animate-pulse"></div>
                    <div class="h-3 w-1/2 bg-gray-100 dark:bg-slate-700 rounded animate-pulse"></div>
                </div>
            {/if}
            <div class:invisible={loading}>
                <p
                    class="text-[clamp(0.95rem,8cqw,1.5rem)] font-bold text-right tabular-nums transition-colors duration-300 {periodPnlPositive === true ? 'text-green-700 dark:text-green-400' : periodPnlPositive === false ? 'text-red-700 dark:text-red-400' : 'text-gray-800 dark:text-gray-100'}"
                    data-testid="kpi-value"
                >
                    <TweenedValue value={periodPnlAmt} format={(v) => formatCurrencyAmountPlain(v, displayCurrency, {showSign: true})} />
                </p>
                {#if pnlDeltaDay != null}
                    <p class="text-xs text-right tabular-nums transition-colors duration-300 {pnlDeltaDay >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400'}" data-testid="kpi-pnl-delta-day">
                        <TweenedValue value={pnlDeltaDay} format={fmtMoney} />
                        {#if periodPnlDeltaDayPct != null}
                            <span> ({pnlDeltaDay >= 0 ? '+' : ''}{periodPnlDeltaDayPct}%)</span>
                        {/if}
                    </p>
                {/if}
                <div class="flex flex-col gap-2 mt-1">
                    <KpiMetricBar
                        label={$_('dashboard.unrealizedDelta')}
                        tooltip={$_('dashboard.unrealizedDeltaTooltip')}
                        value={uglDeltaStr}
                        numericValue={uglDeltaAmt}
                        formatValue={fmtMoney}
                        barPct={pnlBarPct(uglDeltaAmt)}
                        barColor={pnlBarColor(uglDeltaAmt)}
                        valueColor={pnlValueColor(uglDeltaAmt)}
                    />
                    <KpiMetricBar label={$_('dashboard.realizedSales')} tooltip={$_('dashboard.realizedSalesTooltip')} value={realizedStr} numericValue={realizedAmt} formatValue={fmtMoney} barPct={pnlBarPct(realizedAmt)} barColor={pnlBarColor(realizedAmt)} valueColor={pnlValueColor(realizedAmt)} />
                    <KpiMetricBar label={$_('dashboard.income')} tooltip={$_('dashboard.incomeTooltip')} value={incomeStr} numericValue={incomeAmt} formatValue={fmtMoney} barPct={pnlBarPct(incomeAmt)} barColor="bg-green-500 dark:bg-green-400" valueColor="text-green-600 dark:text-green-400" />
                    <KpiMetricBar label={$_('dashboard.feesAndTaxes')} tooltipHtml={feesTooltipHtml} value={feesStr} numericValue={feesAmt} formatValue={fmtMoney} barPct={pnlBarPct(feesAmt)} barColor="bg-red-400 dark:bg-red-500" valueColor="text-red-600 dark:text-red-400" />
                </div>
                <p class="text-[10px] text-gray-400 dark:text-gray-600 mt-1 italic">{$_('dashboard.cashFlowAdjustedResult')}</p>
            </div>
        </div>
    </div>

    <!-- Card 2 — Returns -->
    <div class="relative @container bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm p-5 flex flex-col gap-2 overflow-hidden" data-testid="kpi-returns">
        {#if roiIsPositive !== undefined}
            <div class="absolute top-0 left-0 right-0 h-0.5 {roiIsPositive ? 'bg-green-500 dark:bg-green-400' : 'bg-red-500 dark:bg-red-400'}"></div>
        {/if}
        <div class="flex items-center justify-between">
            <p class="text-xs font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500">{$_('dashboard.returns')}</p>
            <DocsLink path="user/dashboard/kpi-cards/#card-2-returns" label={$_('dashboard.returns')} size={14} />
        </div>
        {#if loading}
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
                <span class="text-[clamp(0.95rem,8cqw,1.5rem)] font-bold tabular-nums transition-colors" style="color: {timingEffectVal >= 0 ? `rgba(22, 163, 74, ${0.3 + timingIntensity * 0.7})` : `rgba(220, 38, 38, ${0.3 + timingIntensity * 0.7})`}">
                    <TweenedValue value={timingEffectVal} format={(v) => `${v >= 0 ? '+' : '-'}${Math.abs(v).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} ${$_('dashboard.pp')}`} />
                </span>
            </div>
            {#if pnlDeltaDayPct}
                <p class="text-xs text-right {pnlDeltaDay != null && pnlDeltaDay >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400'}" data-testid="kpi-returns-delta-pct">{pnlDeltaDay != null && pnlDeltaDay >= 0 ? '+' : ''}{pnlDeltaDayPct}%</p>
            {/if}
            <div class="flex flex-col gap-2 mt-1">
                <KpiMetricBar label={$_('dashboard.roi')} tooltip={$_('dashboard.roiTooltip')} value={roiPct} numericValue={roiVal} formatValue={fmtPct} barPct={retBarPct(roiVal)} barColor={retBarColor(roiVal)} valueColor="font-bold text-gray-800 dark:text-gray-100" />
                <KpiMetricBar label={$_('dashboard.twrrCum')} tooltip={$_('dashboard.twrrTooltip')} value={twrrCumPct} numericValue={twrrCumVal} formatValue={fmtPct} barPct={retBarPct(twrrCumVal)} barColor={retBarColor(twrrCumVal)} />
                <KpiMetricBar label={$_('dashboard.mwrrCum')} tooltip={$_('dashboard.mwrrCumTooltip')} value={mwrrCumPct} numericValue={mwrrCumVal} formatValue={fmtPct} barPct={retBarPct(mwrrCumVal)} barColor={retBarColor(mwrrCumVal)} />
                <KpiMetricBar label={$_('dashboard.mwrrAnn')} tooltip={$_('dashboard.mwrrAnnTooltip')} value={mwrrAnnPct} numericValue={mwrrAnnVal} formatValue={fmtPct} barPct={retBarPct(mwrrAnnVal)} barColor={retBarColor(mwrrAnnVal)} />
            </div>
            <p class="text-[10px] text-gray-400 dark:text-gray-600 mt-1 italic">{$_('dashboard.periodBasedReturns')}</p>
        {/if}
    </div>

    <!-- Card 3 — Net Worth -->
    <div class="relative @container bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm p-5 flex flex-col gap-2 overflow-hidden" data-testid="kpi-net-worth">
        <div class="flex items-center justify-between">
            <p class="text-xs font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500">{$_('dashboard.netWorth')}</p>
            <DocsLink path="user/dashboard/kpi-cards/#card-3-net-worth" label={$_('dashboard.netWorth')} size={14} />
        </div>
        {#if loading}
            <div class="h-7 w-3/4 bg-gray-200 dark:bg-slate-700 rounded animate-pulse"></div>
            <div class="h-3 w-1/2 bg-gray-100 dark:bg-slate-700 rounded animate-pulse mt-2"></div>
        {:else}
            <p class="text-[clamp(0.95rem,8cqw,1.5rem)] font-bold text-gray-800 dark:text-gray-100 text-right tabular-nums" data-testid="kpi-value">
                <TweenedValue value={navHeroAmt} format={(v) => formatCurrencyAmountPlain(v, displayCurrency, {showSign: false})} />
            </p>
            {#if totalPnlAmt != null}
                <p class="text-xs text-right tabular-nums transition-colors duration-300 {totalPnlAmt >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400'}" data-testid="kpi-total-pnl-delta">
                    <TweenedValue value={totalPnlAmt} format={fmtMoney} />
                    {#if totalPnlDeltaPct != null}
                        <span> ({pnlDeltaDay != null && pnlDeltaDay >= 0 ? '+' : ''}{totalPnlDeltaPct}%)</span>
                    {/if}
                </p>
            {/if}
            <div class="flex flex-col gap-2 mt-1">
                <KpiMetricBar
                    label={$_('dashboard.marketValue')}
                    tooltip={$_('dashboard.marketValueTooltip')}
                    value={marketValueStr}
                    numericValue={marketValueAmt}
                    formatValue={fmtMoneyUnsigned}
                    barPct={marketBarPct}
                    barColor={marketBarColor}
                    marker={marketStartMarkerPct > 0 ? marketStartMarkerPct : undefined}
                    markerTooltip="{$_('dashboard.marketValueStart')}: {marketValueStartStr}"
                />
                <KpiMetricBar
                    label={$_('dashboard.bookValue')}
                    tooltip={$_('dashboard.bookValueTooltip')}
                    value={purchaseCostStr}
                    numericValue={purchaseCostAmt}
                    formatValue={fmtMoneyUnsigned}
                    barPct={purchaseCostBarPct}
                    barColor="bg-blue-500 dark:bg-blue-400"
                    marker={purchaseCostStartMarkerPct > 0 ? purchaseCostStartMarkerPct : undefined}
                    markerTooltip="{$_('dashboard.bookValueStart')}: {purchaseCostStartStr}"
                />
                <KpiMetricBar
                    label={$_('dashboard.cashValue')}
                    tooltipHtml={cashTooltipHtml}
                    tooltip={cashTooltipHtml ? undefined : $_('dashboard.cashValueTooltip')}
                    value={cashTotalStr}
                    numericValue={cashAmt}
                    formatValue={fmtMoneyUnsigned}
                    barPct={cashBarPct}
                    barColor="bg-emerald-500 dark:bg-emerald-400"
                    marker={cashStartMarkerPct > 0 ? cashStartMarkerPct : undefined}
                    markerTooltip="{$_('dashboard.cashValueStart')}: {cashStartStr}"
                />
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
