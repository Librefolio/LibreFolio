<!--
  BannerFxPairDialog — the dialog that adds a pair, opened by a banner's «add pair» chip (and by the currency selector's
  «create forex»), on the state of a `PortfolioBannerActions`. Moved out of `PortfolioBanners.svelte` so the lots panel's
  banner (project 69, L4) opens the same dialog on its own actions.
-->
<script lang="ts">
    import FxPairAddModal from '$lib/features/fx/FxPairAddModal.svelte';
    import type {PortfolioBannerActions} from './portfolioBannerActions.svelte';

    interface Props {
        actions: PortfolioBannerActions;
    }

    let {actions}: Props = $props();

    const fxParts = $derived(actions.fxPairSlug.includes('-') ? actions.fxPairSlug.split('-') : actions.fxPairSlug.split('/'));
</script>

{#if actions.fxPairModalOpen}
    <FxPairAddModal bind:open={actions.fxPairModalOpen} initialBase={fxParts[0] ?? ''} initialQuote={fxParts[1] ?? ''} oncreated={() => actions.handleFxPairCreated()} onsynced={(detail) => actions.handleFxPairCreationSynced(detail)} />
{/if}
