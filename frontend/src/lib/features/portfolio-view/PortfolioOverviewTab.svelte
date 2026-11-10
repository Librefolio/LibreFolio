<!--
  PortfolioOverviewTab — the Overview tab of the portfolio view: KPIs, cash balances, the growth chart and the allocation.

  Moved whole out of `PortfolioView.svelte` (Y6-7, delivery 2): markup and `data-testid`s are the view's, unchanged.
  It shows what the data controller holds (`snapshot`) and owns no request: the candles are asked through `onRequestPnlCandles`,
  which the view wraps in its page-busy key and reads the snapshot in, so the chart's effect depends on the candles on screen.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {Wallet} from 'lucide-svelte';
    import {currentLanguage} from '$lib/stores/app/language';
    import {formatCurrencyAmountHtml} from '$lib/utils/currency/currencyFormat';
    import AllocationPanel from '$lib/features/dashboard/AllocationPanel.svelte';
    import GrowthChart from '$lib/features/dashboard/GrowthChart.svelte';
    import KpiSection from '$lib/features/dashboard/KpiSection.svelte';
    import type {PortfolioDataState} from './portfolioData';

    interface Props {
        /** What the data controller holds for the scope on screen. */
        snapshot: PortfolioDataState;
        /** The currency the figures are in (the one the last answer was asked in). */
        displayCurrency: string;
        /** The brokers the allocation is for. */
        brokerIds: number[] | undefined;
        /** The chart asks for the synthetic P&L candles when the user first opens that submode. */
        onRequestPnlCandles: () => void;
        /** The tab's test ids: the Dashboard's and a broker's pages keep their own (`portfolioScopeProfile`). */
        testIds: {overviewTab: string; cashBalances: string; cashBalance: string};
    }

    let {snapshot, displayCurrency, brokerIds, onRequestPnlCandles, testIds}: Props = $props();

    const summaryLoading = $derived(snapshot.reportLoading && !snapshot.summary);
    const historyLoading = $derived(snapshot.reportLoading && snapshot.history.length === 0);
</script>

<div class="space-y-4" data-testid={testIds.overviewTab}>
    <KpiSection summary={snapshot.summary} history={snapshot.history} loading={summaryLoading} {displayCurrency} />

    <!-- Cash Balances — same position as broker detail (right after the KPIs), using
         summary.cash_balances which already aggregates by currency across all brokers
         in scope (all accessible brokers, or the broker-filter subset if active). -->
    <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-subtle p-4" data-testid={testIds.cashBalances}>
        <div class="flex items-center space-x-2 text-lf-secondary mb-4">
            <Wallet size={20} />
            <h2 class="font-semibold">{$_('brokers.cashBalances')}</h2>
        </div>

        {#if snapshot.summary?.cash_balances && snapshot.summary.cash_balances.length > 0}
            <div class="flex flex-wrap gap-2">
                {#each [...snapshot.summary.cash_balances].sort((a, b) => parseFloat(b.amount) - parseFloat(a.amount)) as balance}
                    <span class="inline-flex items-center px-3 py-1.5 bg-lf-panel rounded-lg text-sm font-medium text-lf-primary" data-testid={testIds.cashBalance}>
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
            <GrowthChart
                history={snapshot.history}
                range={snapshot.range}
                mwrrLine={snapshot.mwrrLine}
                brokerPnlHistory={snapshot.brokerPnlHistory}
                pnlCandles={snapshot.pnlCandles}
                {onRequestPnlCandles}
                incomeHistory={snapshot.incomeHistory}
                costHistory={snapshot.costHistory}
                depositHistory={snapshot.depositHistory}
                acquisitionFunding={snapshot.acquisitionFunding}
                loading={historyLoading}
                pnlCandlesLoading={snapshot.pnlCandlesLoading}
                baseCurrency={displayCurrency}
            />
        </div>

        <!-- Allocation Panel — 2/5 -->
        <AllocationPanel summary={snapshot.summary} loading={summaryLoading} {displayCurrency} {brokerIds} currentLanguage={$currentLanguage} allocationHistory={snapshot.allocationHistory} />
    </div>
</div>
