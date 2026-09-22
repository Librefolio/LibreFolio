<script lang="ts">
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import {_ as t} from '$lib/i18n';

    /**
     * The beta notice, and *what* it declares provisional.
     *
     * One component, two claims, because two surfaces are in beta for unrelated
     * reasons and a single sentence cannot be true of both:
     *
     *   subsystem  → Asset Detail, parked whole by decision (`03` §5). Nothing
     *                about that page is being asserted finished.
     *   simulation → the modelled rung of L4, the only part of the four levels
     *                that has not left beta, held back by a recorded defect.
     *
     * `subsystem` is the default deliberately. The caller that needs it — Asset
     * Detail — is outside this redesign and must keep meaning exactly what it
     * meant before; a default of `simulation` would have changed that page's
     * claim silently, from a component it does not own and never edited.
     *
     * ⚠️ The e2e suites assert this banner's *presence*, never its text, because
     * the text is translated. So a wrong sentence here stays green: the sense is
     * only checked by reading it.
     */
    interface Props {
        scope?: 'subsystem' | 'simulation';
    }

    let {scope = 'subsystem'}: Props = $props();

    let keyPrefix = $derived(scope === 'simulation' ? 'risk.betaBanner.simulation' : 'risk.betaBanner');
</script>

<div data-testid="risk-beta-banner" data-scope={scope}>
    <InfoBanner variant="info">
        <span class="font-semibold">{$t(`${keyPrefix}.title`)}</span>
        <span class="ml-1">{$t(`${keyPrefix}.description`)}</span>
    </InfoBanner>
</div>
