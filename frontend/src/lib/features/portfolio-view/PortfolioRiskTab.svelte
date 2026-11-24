<!--
  PortfolioRiskTab — the Risk tab of the portfolio view.

  Moved whole out of `PortfolioView.svelte` (Y6-7, delivery 2): markup and `data-testid`s are the view's, unchanged.

  The risk scope is the one of the summary on screen (`brokerIds`): every broker the user owns (F2, as the rest of the
  Dashboard), or the subset a broker filter keeps — a filter narrows the risk as it narrows every other tab (RSK-F, the
  developer, 24/11/2026: «i filtri se ci sono vanno rispettati»). Those are the brokers of the report on screen, not of the
  filter: the report lands after the filter's debounce, and until then the summary's net worth and holdings are still the old
  scope's, so the panel asks the same scope its money comes from. Never without `broker_ids`: the backend would widen it to
  every broker the user can see, editor and viewer ones included, so the panel mounts only once the owned brokers are known,
  and an empty set falls back to them.
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
        /** The brokers of the summary on screen (the last report's), the owned ones or the filter's subset; null before the first. */
        brokerIds: number[] | null;
        dateStart: string;
        dateEnd: string;
        targetCurrency: string;
        /** The summary of `brokerIds`: the assets held and the value of the risk scope. */
        summary: PortfolioSummary | null;
        refreshVersion: number;
        /** The panel synced prices or rates: the view reloads its report. */
        onsynced: () => void | Promise<void>;
    }

    let {testId, broker, canAsk, brokersReady, ownedBrokerIds, brokerIds, dateStart, dateEnd, targetCurrency, summary, refreshVersion, onsynced}: Props = $props();

    const scopeBrokerIds = $derived(brokerIds && brokerIds.length > 0 ? brokerIds : ownedBrokerIds);
    /** A subset of the owned brokers (a broker filter): the header says the risk is the one of that subset. */
    const subset = $derived.by(() => {
        const owned = new Set(ownedBrokerIds);
        const asked = new Set(scopeBrokerIds);
        return asked.size !== owned.size || [...asked].some((id) => !owned.has(id));
    });
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
            scope={{kind: 'portfolio', broker_ids: scopeBrokerIds}}
            {dateStart}
            {dateEnd}
            {targetCurrency}
            assetIds={[...new Set((summary?.holdings ?? []).map((holding) => holding.asset_id))]}
            scopeValue={summary ? parseFloat(summary.net_worth.amount) : null}
            title={$_('risk.dashboardTitle')}
            internalSubset={subset}
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
