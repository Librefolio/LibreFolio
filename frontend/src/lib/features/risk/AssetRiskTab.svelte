<script lang="ts">
    /**
     * The Asset Detail's «Risk and scenarios» tab: an x-ray of the asset (RN-17; the developer, 12/11/2026: «un xray di
     * quell'asset»). The levels panel of the Dashboard, mounted on the asset — it keeps only the levels that have meaning
     * on one asset (`RiskLevelsPanel`, scope `asset`) — with two things the asset needs and a portfolio does not:
     *
     *  - **the money on your position (Q17 A1)**: when you own the asset, the amounts are on your position today, the
     *    value the backend's portfolio report gives for it (grouped by asset, your share, the page's currency), read once
     *    here and handed to the levels; one sentence says which value. Not owned, or the read failed: no amount at all;
     *  - **prices from the plan (Q20 a)**: on a scheduled investment, a HOLD or a crowdfunding asset the «prices» are
     *    built from a plan, so volatility and VaR only say the plan is regular — a note says so above the levels.
     */
    import {untrack} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import RiskLevelsPanel from './levels/RiskLevelsPanel.svelte';
    import {formatCurrencyAmount} from './riskAnalysisHelpers';
    import {loadAssetPositionValue, pricesFromPlan} from './assetRiskTabRules';

    interface Props {
        assetId: number;
        assetType: string | null | undefined;
        /** The asset's provider generates its series from parameters (a scheduled investment). */
        parametricPrices: boolean;
        dateStart: string;
        dateEnd: string;
        targetCurrency: string;
        refreshVersion?: number;
        onsynced?: () => void | Promise<void>;
    }

    let {assetId, assetType, parametricPrices, dateStart, dateEnd, targetCurrency, refreshVersion = 0, onsynced}: Props = $props();

    /** Your position's value, or `null`: not owned, not valued, or not read. */
    let positionValue = $state<number | null>(null);
    /** Where the read of the position stands, published for whoever waits on it (the E2E): an absent sentence is final only once `ready`. */
    let positionState = $state<'loading' | 'ready'>('loading');
    let planPrices = $derived(pricesFromPlan(assetType, parametricPrices));

    $effect(() => {
        const id = assetId;
        const currency = targetCurrency;
        void refreshVersion;
        let current = true;
        untrack(() => {
            positionValue = null;
            positionState = 'loading';
            loadAssetPositionValue(id, currency)
                .then((value) => {
                    if (current) positionValue = value;
                })
                .catch(() => {
                    // A failed read shows no amount — never a guess. The API client logs the failure (H-60).
                    if (current) positionValue = null;
                })
                .finally(() => {
                    if (current) positionState = 'ready';
                });
        });
        return () => {
            current = false;
        };
    });
</script>

<div class="space-y-3" data-testid="asset-risk-tab" data-position={positionState}>
    {#if planPrices}
        <p class="rounded-lg border border-lf-info-line bg-lf-info-soft px-3 py-2 text-xs text-lf-info-on-soft" data-testid="asset-risk-plan-prices">{$t('risk.assetDetail.planPrices')}</p>
    {/if}
    {#if positionValue !== null}
        <p class="text-xs text-lf-muted" data-testid="asset-risk-position">{$t('risk.assetDetail.positionNote', {values: {amount: formatCurrencyAmount(String(positionValue), targetCurrency)}})}</p>
    {/if}
    {#key assetId}
        <!-- A new asset on the same route starts a new panel: its simulation and scenario tools never carry over. -->
        <RiskLevelsPanel scope={{kind: 'asset', asset_id: assetId}} {dateStart} {dateEnd} {targetCurrency} assetIds={[assetId]} scopeValue={positionValue} {refreshVersion} {onsynced} />
    {/key}
</div>
