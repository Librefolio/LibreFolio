<script lang="ts">
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import {_ as t} from '$lib/i18n';
</script>

<div data-testid="risk-beta-banner">
    <InfoBanner variant="info">
        <span class="font-semibold">{$t('risk.betaBanner.title')}</span>
        <span class="ml-1">{$t('risk.betaBanner.description')}</span>
    </InfoBanner>
</div>
