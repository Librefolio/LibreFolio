<!--
  KpiSection — Dashboard KPI row with Period P&L, Returns, Net Worth.

  Extracted from dashboard/+page.svelte as behavior-preserving refactor.
  Keep markup/data-testid/i18n/colors identical for safe reuse.
-->
<script lang="ts">
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {_} from '$lib/i18n';
    import type {PortfolioSummary, PortfolioHistoryPoint} from '$lib/stores/portfolio/portfolioStore.svelte';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import {formatPercent} from '$lib/utils/core/formatPercent';

    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import TweenedValue from '$lib/components/ui/TweenedValue.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import KpiMetricBar from '$lib/components/ui/display/KpiMetricBar.svelte';
    import KpiDivergingFlowBar from '$lib/components/ui/display/KpiDivergingFlowBar.svelte';
    import {safeString} from '$lib/types';
    import {formatFixed} from '$lib/utils/core/formatFixed';
    import {SIGN_BAR, SIGN_TEXT} from '$lib/theme/toneClasses';

    interface Props {
        summary: PortfolioSummary | null;
        history: PortfolioHistoryPoint[];
        loading: boolean;
        displayCurrency: string;
    }

    let {summary, history, loading, displayCurrency}: Props = $props();

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

    function tooltipRows(description: string, rows: {emoji: string; label: string; value: string; testid?: string}[]): string {
        let html = `<div style="font-size:12px;max-width:300px">${escapeHtml(description)}`;
        html += `<table style="width:100%;margin-top:6px;border-collapse:collapse">`;
        for (const r of rows) {
            const testid = r.testid ? ` data-testid="${escapeHtml(r.testid)}"` : '';
            html += `<tr${testid}><td style="white-space:nowrap">${r.emoji} ${r.label}</td><td style="text-align:right;padding-left:12px;white-space:nowrap;font-weight:500">${r.value}</td></tr>`;
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

    /** The day's change of the Total P&L, from the calendar day before (`pnl_change_1d`, R17): the backend's, never the history's. */
    const pnlDeltaDay = $derived.by(() => {
        const change = summary ? safeCurrency(summary.pnl_change_1d) : null;
        if (!change) return null;
        const amount = parseFloat(change.amount);
        return Number.isFinite(amount) ? amount : null;
    });
    /** Direction of the day's change, published as `data-direction`; the colour agrees (up and flat green, down red). */
    const pnlDeltaDayDirection = $derived(pnlDeltaDay == null ? undefined : pnlDeltaDay > 0 ? 'up' : pnlDeltaDay < 0 ? 'down' : 'flat');

    /** Card 2: the day change as a share of yesterday's NAV (`pnl_change_1d_vs_nav_percent`). */
    const pnlDeltaDayPct = $derived(summary ? returnPct(summary.pnl_change_1d_vs_nav_percent) : null);

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
    /** Card 1: the day change as a share of yesterday's total P&L (`pnl_change_1d_vs_total_pnl_percent`). */
    const pnlDeltaDayVsPrevTotalPct = $derived(summary ? returnPct(summary.pnl_change_1d_vs_total_pnl_percent) : null);
    // Absolute (since-inception) ROI next to the absolute total P&L in Card 3 —
    // period ROI (simple_roi_percent) belongs to Card 2's period-based returns only.
    const absRoiPct = $derived.by(() => {
        if (!summary) return null;
        const roi = parseFloat(summary.total_gain_loss_percent);
        if (!Number.isFinite(roi)) return null;
        return roi * 100;
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
    const marketBarColor = $derived(marketValueAmt >= marketValueStartAmt ? SIGN_BAR.kpi.gain : SIGN_BAR.kpi.loss);

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
    // Rows and their order come from the backend and add up to the bar's figure: never add, drop or sort one.
    const unrealizedDeltaTooltipHtml = $derived.by(() => {
        const rows = summary?.period_unrealized_breakdown ?? [];
        if (rows.length === 0) return undefined;
        return tooltipRows(
            $_('dashboard.unrealizedDeltaTooltip'),
            rows.map((row) => {
                const delta = safeCurrency(row.period_delta);
                const currency = row.asset_currency;
                let emoji = '📈';
                let label = $_('dashboard.unrealizedAssetEffect', {values: {currency}});
                if (row.kind === 'fx') {
                    emoji = '💱';
                    label = $_('dashboard.unrealizedFxEffect', {values: {from: currency, to: delta?.code ?? displayCurrency}});
                } else if (row.kind === 'unsplit') {
                    emoji = '❔';
                    label = $_('dashboard.unrealizedUnsplit', {values: {currency}});
                }
                return {emoji, label: escapeHtml(label), value: formatMoney(delta?.code, delta?.amount, {signed: true}), testid: `kpi-unrealized-breakdown-${row.kind}-${currency}`};
            }),
        );
    });

    const pnlBarMax = $derived(Math.max(Math.abs(uglDeltaAmt), Math.abs(realizedAmt), Math.abs(incomeAmt), Math.abs(feesAmt)) || 1);
    function pnlBarPct(val: number) {
        return (Math.abs(val) / pnlBarMax) * 100;
    }
    function pnlBarColor(val: number) {
        return val >= 0 ? SIGN_BAR.kpi.gain : SIGN_BAR.kpi.loss;
    }
    function pnlValueColor(val: number) {
        return val >= 0 ? SIGN_TEXT.kpi.gain : SIGN_TEXT.kpi.loss;
    }

    const roiVal = $derived(summary ? parseFloat(summary.simple_roi_percent) * 100 : 0);
    /** A return in percent, or null when the backend could not compute it (the field is optional and nullable). */
    function returnPct(raw: unknown): number | null {
        const text = safeString(raw);
        if (text == null) return null;
        const pct = parseFloat(text) * 100;
        return Number.isFinite(pct) ? pct : null;
    }
    const twrrCumVal = $derived(summary ? returnPct(summary.twrr_percent) : null);
    const mwrrCumVal = $derived(summary ? returnPct(summary.mwrr_cumulative_percent) : null);
    const mwrrAnnVal = $derived(summary ? returnPct(summary.mwrr_annualized_percent) : null);
    // The timing effect is the backend's (`timing_effect_percent`, null when either return is missing), in percentage points.
    const timingEffectVal = $derived(summary ? returnPct(summary.timing_effect_percent) : null);
    /**
     * Its reading, published as `data-direction`: neutral within ±0.05 pp, favourable above, unfavourable below. The
     * colour agrees, with the sign classes of the other KPIs (round 3, §1.7): green and red, grey when neutral.
     */
    const timingDirection = $derived(timingEffectVal == null ? undefined : Math.abs(timingEffectVal) < 0.05 ? 'neutral' : timingEffectVal > 0 ? 'favorable' : 'unfavorable');
    const timingLabel = $derived(timingDirection === 'neutral' ? $_('dashboard.timingNeutral') : timingDirection === 'favorable' ? $_('dashboard.timingFavorable') : timingDirection === 'unfavorable' ? $_('dashboard.timingUnfavorable') : '');
    const timingValueTone = $derived(timingDirection === 'favorable' ? SIGN_TEXT.headline.gain : timingDirection === 'unfavorable' ? SIGN_TEXT.headline.loss : timingDirection === 'neutral' ? SIGN_TEXT.headline.neutral : 'text-lf-muted');
    const timingLabelTone = $derived(timingDirection === 'favorable' ? SIGN_TEXT.kpi.gain : timingDirection === 'unfavorable' ? SIGN_TEXT.kpi.loss : 'text-lf-muted');
    const roiPct = $derived(summary ? formatPercent(roiVal, {signed: false}) : '—');
    const twrrCumPct = $derived(twrrCumVal != null ? formatPercent(twrrCumVal, {signed: false}) : '—');
    const mwrrCumPct = $derived(mwrrCumVal != null ? formatPercent(mwrrCumVal, {signed: false}) : '—');
    const mwrrAnnPct = $derived(mwrrAnnVal != null ? formatPercent(mwrrAnnVal, {signed: false}) : '—');
    const roiIsPositive = $derived(summary ? parseFloat(summary.simple_roi_percent) >= 0 : undefined);

    const retBarMax = $derived(Math.max(Math.abs(roiVal), Math.abs(twrrCumVal ?? 0), Math.abs(mwrrCumVal ?? 0), Math.abs(mwrrAnnVal ?? 0)) || 1);
    function retBarPct(val: number) {
        return (Math.abs(val) / retBarMax) * 100;
    }
    function retBarColor(val: number) {
        return val >= 0 ? SIGN_BAR.kpi.gain : SIGN_BAR.kpi.loss;
    }

    const fmtMoney = (v: number) => formatCurrencyAmountPlain(v, displayCurrency, {showSign: true});
    const fmtMoneyUnsigned = (v: number) => formatCurrencyAmountPlain(v, displayCurrency, {showSign: false});
    const fmtPct = (v: number) => formatPercent(v, {signed: false});
</script>

<div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-lf-primary" data-testid="kpi-row">
    <!-- Card 1 — Period P&L -->
    <div class="relative @container bg-lf-card rounded-xl border border-lf-subtle shadow-sm shadow-lf-shadow-card p-5 flex flex-col gap-2 overflow-hidden" data-testid="kpi-period-pnl">
        {#if periodPnlPositive !== undefined}
            <div class="absolute top-0 left-0 right-0 h-0.5 {periodPnlPositive ? SIGN_BAR.accent.gain : SIGN_BAR.accent.loss}"></div>
        {/if}
        <div class="flex items-center justify-between">
            <p class="text-xs font-medium uppercase tracking-wide text-lf-muted">{$_('dashboard.periodPnl')}</p>
            <DocsLink path="user/dashboard/kpi-cards/#card-1-period-pl" label={$_('dashboard.periodPnl')} size={14} />
        </div>
        <div class="relative">
            {#if loading}
                <div class="absolute inset-0 z-10 flex flex-col gap-2">
                    <div class="h-7 w-3/4 bg-lf-neutral rounded animate-pulse"></div>
                    <div class="h-3 w-1/2 bg-lf-panel rounded animate-pulse"></div>
                </div>
            {/if}
            <div class:invisible={loading}>
                <p class="text-[clamp(0.95rem,8cqw,1.5rem)] font-bold text-right tabular-nums transition-colors duration-300 {periodPnlPositive === true ? SIGN_TEXT.headline.gain : periodPnlPositive === false ? SIGN_TEXT.headline.loss : SIGN_TEXT.headline.neutral}" data-testid="kpi-value">
                    <TweenedValue value={periodPnlAmt} format={(v) => formatCurrencyAmountPlain(v, displayCurrency, {showSign: true})} />
                </p>
                {#if pnlDeltaDay != null}
                    <p class="text-xs text-right tabular-nums transition-colors duration-300 {pnlDeltaDay >= 0 ? SIGN_TEXT.portfolio.gain : SIGN_TEXT.portfolio.loss}" data-testid="kpi-pnl-delta-day" data-direction={pnlDeltaDayDirection}>
                        <TweenedValue value={pnlDeltaDay} format={fmtMoney} />
                        {#if pnlDeltaDayVsPrevTotalPct != null}
                            <span> (<span data-testid="kpi-pnl-delta-day-pct">{formatPercent(pnlDeltaDayVsPrevTotalPct)}</span>)</span>
                        {/if}
                    </p>
                {/if}
                <div class="flex flex-col gap-2 mt-1">
                    <KpiMetricBar
                        testid="kpi-unrealized-delta"
                        label={$_('dashboard.unrealizedDelta')}
                        tooltipHtml={unrealizedDeltaTooltipHtml}
                        tooltip={unrealizedDeltaTooltipHtml ? undefined : $_('dashboard.unrealizedDeltaTooltip')}
                        value={uglDeltaStr}
                        numericValue={uglDeltaAmt}
                        formatValue={fmtMoney}
                        barPct={pnlBarPct(uglDeltaAmt)}
                        barColor={pnlBarColor(uglDeltaAmt)}
                        valueColor={pnlValueColor(uglDeltaAmt)}
                    />
                    <KpiMetricBar label={$_('dashboard.realizedSales')} tooltip={$_('dashboard.realizedSalesTooltip')} value={realizedStr} numericValue={realizedAmt} formatValue={fmtMoney} barPct={pnlBarPct(realizedAmt)} barColor={pnlBarColor(realizedAmt)} valueColor={pnlValueColor(realizedAmt)} />
                    <KpiMetricBar label={$_('dashboard.income')} tooltip={$_('dashboard.incomeTooltip')} value={incomeStr} numericValue={incomeAmt} formatValue={fmtMoney} barPct={pnlBarPct(incomeAmt)} barColor={SIGN_BAR.kpi.gain} valueColor={SIGN_TEXT.kpi.gain} />
                    <KpiMetricBar label={$_('dashboard.feesAndTaxes')} tooltipHtml={feesTooltipHtml} value={feesStr} numericValue={feesAmt} formatValue={fmtMoney} barPct={pnlBarPct(feesAmt)} barColor={SIGN_BAR.kpi.loss} valueColor={SIGN_TEXT.kpi.loss} />
                </div>
                <p class="text-[10px] text-lf-muted mt-1 italic">{$_('dashboard.cashFlowAdjustedResult')}</p>
            </div>
        </div>
    </div>

    <!-- Card 2 — Returns -->
    <div class="relative @container bg-lf-card rounded-xl border border-lf-subtle shadow-sm shadow-lf-shadow-card p-5 flex flex-col gap-2 overflow-hidden" data-testid="kpi-returns">
        {#if roiIsPositive !== undefined}
            <div class="absolute top-0 left-0 right-0 h-0.5 {roiIsPositive ? SIGN_BAR.accent.gain : SIGN_BAR.accent.loss}"></div>
        {/if}
        <div class="flex items-center justify-between">
            <p class="text-xs font-medium uppercase tracking-wide text-lf-muted">{$_('dashboard.returns')}</p>
            <DocsLink path="user/dashboard/kpi-cards/#card-2-returns" label={$_('dashboard.returns')} size={14} />
        </div>
        {#if loading}
            <div class="h-7 w-3/4 bg-lf-neutral rounded animate-pulse"></div>
            <div class="h-3 w-1/2 bg-lf-panel rounded animate-pulse mt-2"></div>
        {:else}
            <!-- Timing effect hero (no bar) -->
            <div class="flex items-center justify-between">
                <Tooltip text={$_('dashboard.timingEffectTooltip')} position="top">
                    <div class="flex flex-col cursor-help">
                        <span class="text-[10px] text-lf-muted uppercase tracking-wide border-b border-dotted border-lf-input inline-block">{$_('dashboard.timingEffect')}</span>
                        <span class="text-[10px] italic {timingLabelTone}" data-testid="kpi-timing-effect-label" data-direction={timingDirection}>{timingLabel}</span>
                    </div>
                </Tooltip>
                <span class="text-[clamp(0.95rem,8cqw,1.5rem)] font-bold tabular-nums transition-colors {timingValueTone}" data-testid="kpi-timing-effect-value" data-direction={timingDirection}>
                    {#if timingEffectVal == null}—{:else}<TweenedValue value={timingEffectVal} format={(v) => `${formatFixed(v, 2, {signed: true})} ${$_('dashboard.pp')}`} />{/if}
                </span>
            </div>
            {#if pnlDeltaDayPct != null}
                <p class="text-xs text-right {pnlDeltaDay != null && pnlDeltaDay >= 0 ? SIGN_TEXT.portfolio.gain : SIGN_TEXT.portfolio.loss}" data-testid="kpi-returns-delta-pct" data-direction={pnlDeltaDayDirection}>{formatPercent(pnlDeltaDayPct)}</p>
            {/if}
            <div class="flex flex-col gap-2 mt-1">
                <KpiMetricBar testid="kpi-return-roi" label={$_('dashboard.roi')} tooltip={$_('dashboard.roiTooltip')} value={roiPct} numericValue={roiVal} formatValue={fmtPct} barPct={retBarPct(roiVal)} barColor={retBarColor(roiVal)} valueColor="font-bold text-lf-primary" />
                <KpiMetricBar testid="kpi-return-twrr-cum" label={$_('dashboard.twrrCum')} tooltip={$_('dashboard.twrrTooltip')} value={twrrCumPct} numericValue={twrrCumVal ?? undefined} formatValue={fmtPct} barPct={retBarPct(twrrCumVal ?? 0)} barColor={retBarColor(twrrCumVal ?? 0)} />
                <KpiMetricBar testid="kpi-return-mwrr-cum" label={$_('dashboard.mwrrCum')} tooltip={$_('dashboard.mwrrCumTooltip')} value={mwrrCumPct} numericValue={mwrrCumVal ?? undefined} formatValue={fmtPct} barPct={retBarPct(mwrrCumVal ?? 0)} barColor={retBarColor(mwrrCumVal ?? 0)} />
                <KpiMetricBar testid="kpi-return-mwrr-ann" label={$_('dashboard.mwrrAnn')} tooltip={$_('dashboard.mwrrAnnTooltip')} value={mwrrAnnPct} numericValue={mwrrAnnVal ?? undefined} formatValue={fmtPct} barPct={retBarPct(mwrrAnnVal ?? 0)} barColor={retBarColor(mwrrAnnVal ?? 0)} />
            </div>
            <p class="text-[10px] text-lf-muted mt-1 italic">{$_('dashboard.periodBasedReturns')}</p>
        {/if}
    </div>

    <!-- Card 3 — Net Worth -->
    <div class="relative @container bg-lf-card rounded-xl border border-lf-subtle shadow-sm shadow-lf-shadow-card p-5 flex flex-col gap-2 overflow-hidden" data-testid="kpi-net-worth">
        <div class="flex items-center justify-between">
            <Tooltip text={$_('dashboard.netWorthTooltip')} position="top">
                <p class="text-xs font-medium uppercase tracking-wide text-lf-muted">{$_('dashboard.netWorth')}</p>
            </Tooltip>
            <DocsLink path="user/dashboard/kpi-cards/#card-3-net-worth" label={$_('dashboard.netWorth')} size={14} />
        </div>
        {#if loading}
            <div class="h-7 w-3/4 bg-lf-neutral rounded animate-pulse"></div>
            <div class="h-3 w-1/2 bg-lf-panel rounded animate-pulse mt-2"></div>
        {:else}
            <p class="text-[clamp(0.95rem,8cqw,1.5rem)] font-bold text-lf-primary text-right tabular-nums" data-testid="kpi-value">
                <TweenedValue value={navHeroAmt} format={(v) => formatCurrencyAmountPlain(v, displayCurrency, {showSign: false})} />
            </p>
            {#if totalPnlAmt != null}
                <p class="text-xs text-right tabular-nums transition-colors duration-300 {totalPnlAmt >= 0 ? SIGN_TEXT.portfolio.gain : SIGN_TEXT.portfolio.loss}" data-testid="kpi-total-pnl-delta">
                    <TweenedValue value={totalPnlAmt} format={fmtMoney} />
                    {#if absRoiPct != null}
                        <span> ({formatPercent(absRoiPct)})</span>
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
                    barColor="bg-lf-cat-etf"
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
                    barColor="bg-lf-cat-liquidity"
                    marker={cashStartMarkerPct > 0 ? cashStartMarkerPct : undefined}
                    markerTooltip="{$_('dashboard.cashValueStart')}: {cashStartStr}"
                />
                <KpiDivergingFlowBar label={$_('dashboard.netDepositedCapital')} tooltipHtml={netDepositedTooltipHtml} value={netDepositedStr} depositPct={depositBarPct} withdrawPct={withdrawBarPct} valueColor={netDepositedPositive ? SIGN_TEXT.kpi.gain : SIGN_TEXT.kpi.loss} />
            </div>
            <p class="text-[10px] text-lf-muted mt-1 italic">{$_('dashboard.periodScopeNote')}</p>
        {/if}
    </div>
</div>
