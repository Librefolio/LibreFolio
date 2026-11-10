<!--
  PortfolioRiskTab — the Risk tab of the portfolio view.

  Moved whole out of `PortfolioView.svelte` (Y6-7, delivery 2): markup and `data-testid`s are the view's, unchanged.

  The risk scope is the *whole* portfolio — every broker the user owns (F2, as the rest of the Dashboard) — even when a
  broker filter is on, which is what the subtitle announces. Never without `broker_ids`: the backend would widen it to every
  broker the user can see, editor and viewer ones included, so the panel mounts only once the owned brokers are known.
  `summary` follows the filter, so its net worth belongs to a different question: passing it would print one broker's money
  beside every broker's risk.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {RefreshCw} from 'lucide-svelte';
    import RiskLevelsPanel from '$lib/features/risk/levels/RiskLevelsPanel.svelte';
    import type {PortfolioSummary} from '$lib/stores/portfolio/portfolioStore.svelte';

    interface Props {
        testId: string;
        /** A broker's page: the risk of that broker alone (`brokerId`), as the broker is counted whole on the page (MF6-3, D4). */
        broker?: {id: number};
        /** The owned brokers are known and there is at least one: the panel can ask. */
        canAsk: boolean;
        /** The owned brokers are known (possibly none): tells "nothing owned" from "still loading". */
        brokersReady: boolean;
        ownedBrokerIds: number[];
        dateStart: string;
        dateEnd: string;
        targetCurrency: string;
        /** The summary of the brokers the filter keeps: it names the assets held, never the value of the risk scope. */
        summary: PortfolioSummary | null;
        brokerFilterActive: boolean;
        refreshVersion: number;
        /** The panel synced prices or rates: the view reloads its report. */
        onsynced: () => void | Promise<void>;
    }

    let {testId, broker, canAsk, brokersReady, ownedBrokerIds, dateStart, dateEnd, targetCurrency, summary, brokerFilterActive, refreshVersion, onsynced}: Props = $props();
</script>

<div data-testid={testId}>
    {#if broker}
        <!-- Same component as Dashboard, same props, one different scope: that is the whole difference, and it is what makes the two
             pages comparable. `summary` is the one of this broker alone, so its net worth answers this exact scope. The page counts
             the broker whole (`fullShare`), so `wholeBroker` makes the risk scope ask the same: stress impacts and scope value then
             match the net worth printed above. -->
        <RiskLevelsPanel
            scope={{kind: 'portfolio', broker_ids: [broker.id]}}
            {dateStart}
            {dateEnd}
            {targetCurrency}
            assetIds={[...new Set((summary?.holdings ?? []).map((holding) => holding.asset_id))]}
            scopeValue={summary ? parseFloat(summary.net_worth.amount) : null}
            title={$_('risk.brokerTitle')}
            internalSubset={true}
            wholeBroker={true}
            {refreshVersion}
            {onsynced}
        />
    {:else if canAsk}
        <RiskLevelsPanel
            scope={{kind: 'portfolio', broker_ids: ownedBrokerIds}}
            {dateStart}
            {dateEnd}
            {targetCurrency}
            assetIds={[...new Set((summary?.holdings ?? []).map((holding) => holding.asset_id))]}
            scopeValue={brokerFilterActive || !summary ? null : parseFloat(summary.net_worth.amount)}
            title={$_('risk.dashboardTitle')}
            subtitle={brokerFilterActive ? $_('risk.dashboardFullPortfolio') : ''}
            {refreshVersion}
            {onsynced}
        />
    {:else if brokersReady}
        <p class="py-12 text-center text-sm italic text-lf-muted" data-testid="dashboard-risk-no-owned">{$_('common.noData')}</p>
    {:else}
        <!-- Owned brokers still loading (cold load): say so instead of an empty tab. -->
        <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-subtle p-12 text-center" data-testid="dashboard-risk-loading">
            <RefreshCw class="text-lf-link animate-spin mx-auto" size={28} />
        </div>
    {/if}
</div>
