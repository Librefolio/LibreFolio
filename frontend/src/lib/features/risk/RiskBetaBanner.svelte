<script lang="ts">
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import {_ as t} from '$lib/i18n';

    /**
     * The beta notice of the old Asset Detail risk tab, parked whole by decision (`03` §5):
     * nothing about that page is asserted finished. Its only callers are that tab's
     * (`AssetRiskScenariosView`, `RiskAnalysisPanel`); it goes with them when the Asset
     * Detail moves to the four levels (RN-17). The simulation's own claim went when it left
     * beta (RN-06, Q6 of 16/11/2026), and with it this component's `scope`.
     *
     * ⚠️ The e2e suites assert this banner's *presence*, never its text, because
     * the text is translated. So a wrong sentence here stays green: the sense is
     * only checked by reading it.
     */
</script>

<div data-testid="risk-beta-banner">
    <InfoBanner variant="info">
        <span class="font-semibold">{$t('risk.betaBanner.title')}</span>
        <span class="ml-1">{$t('risk.betaBanner.description')}</span>
    </InfoBanner>
</div>
