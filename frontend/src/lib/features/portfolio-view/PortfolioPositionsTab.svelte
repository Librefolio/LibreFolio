<!--
  PortfolioPositionsTab — the Positions tab of the portfolio view: the positions panel, and the lot detail below it.

  Moved whole out of `PortfolioView.svelte` (Y6-7, delivery 2): markup and `data-testid`s are the view's, unchanged. What the
  report holds comes as `snapshot`; the way the series, the Rolling and the contribution are asked stays the view's, handed
  down as callbacks (the view wraps them in its page-busy keys and reads the controller's state in them).

  The lot detail opens below the positions, as on a broker's page (FB-12b): the chart stays; the panel's ✕ or the browser's
  back closes it.
-->
<script lang="ts">
    import type {ComponentProps} from 'svelte';
    import {currentLanguage} from '$lib/stores/app/language';
    import PositionsPanel from '$lib/features/dashboard/PositionsPanel.svelte';
    import LotsAnalysisPanel from '$lib/features/brokers/lots/LotsAnalysisPanel.svelte';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import type {PortfolioDataState} from './portfolioData';

    type PanelProps = ComponentProps<typeof PositionsPanel>;

    interface Props {
        /** What the data controller holds for the scope on screen. */
        snapshot: PortfolioDataState;
        brokers: BrokerLike[];
        /** The brokers the view shows; undefined while the owned brokers are not known. */
        brokerIds: number[] | undefined;
        /** The owned brokers are known: the lot detail may ask. */
        /** The tab's test id: the Dashboard's and a broker's pages keep their own (`portfolioScopeProfile`). */
        testId: string;
        canAsk: boolean;
        assetsHref: string;
        /** The contribution is asked through this callback; absent until the owned brokers are known (F2). */
        onRequestContribution: PanelProps['onRequestContribution'];
        positionsSeries: PanelProps['positionsSeries'];
        positionsSeriesLoading: PanelProps['positionsSeriesLoading'];
        positionsSeriesFailed: PanelProps['positionsSeriesFailed'];
        onRequestPositionsSeries: PanelProps['onRequestPositionsSeries'];
        positionsRolling: PanelProps['positionsRolling'];
        onRequestPositionsRolling: PanelProps['onRequestPositionsRolling'];
        /** The asset whose lot detail is open (`?asset=`), its name and currency. */
        activeAssetId: number | null;
        activeAsset: {currency?: string | null; display_name?: string | null} | null | undefined;
        displayCurrency: string;
        onAnalyze: (assetId: number) => void;
        onCloseAnalysis: () => void;
        refreshVersion: number;
    }

    let {testId, snapshot, brokers, brokerIds, canAsk, assetsHref, onRequestContribution, positionsSeries, positionsSeriesLoading, positionsSeriesFailed, onRequestPositionsSeries, positionsRolling, onRequestPositionsRolling, activeAssetId, activeAsset, displayCurrency, onAnalyze, onCloseAnalysis, refreshVersion}: Props = $props();

    const summaryLoading = $derived(snapshot.reportLoading && !snapshot.summary);
</script>

<div data-testid={testId}>
    <!-- F2: nothing is asked before the owned brokers are known — the prop arrives with them. -->
    <PositionsPanel
        summary={snapshot.summary}
        contribution={snapshot.positionsContribution}
        loading={summaryLoading}
        contributionLoading={snapshot.contributionLoading}
        {assetsHref}
        {brokers}
        {onRequestContribution}
        {onAnalyze}
        analyzedAssetId={activeAssetId}
        portfolioHistory={snapshot.history}
        {brokerIds}
        currentLanguage={$currentLanguage}
        allocationHistory={snapshot.allocationHistory}
        {positionsSeries}
        {positionsSeriesLoading}
        {positionsSeriesFailed}
        {onRequestPositionsSeries}
        {positionsRolling}
        {onRequestPositionsRolling}
    />
    <LotsAnalysisPanel
        open={activeAssetId != null}
        assetId={activeAssetId}
        brokerIds={brokerIds ?? brokers.map((b) => b.id)}
        {brokers}
        currency={activeAsset?.currency ?? displayCurrency}
        assetName={activeAsset?.display_name ?? null}
        onClose={onCloseAnalysis}
        ready={canAsk}
        {refreshVersion}
    />
</div>
