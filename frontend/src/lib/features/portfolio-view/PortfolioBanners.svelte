<!--
  PortfolioBanners — the data-quality banner of the portfolio view and the dialog that adds a pair (Y6-7, delivery 2,
  checkpoint 9e; moved out of `PortfolioView.svelte`, markup and behaviour kept).

  What the buttons do — sync rates, sync prices, the chips to an asset or a pair, the dialog and what follows it — is
  `PortfolioBannerActions`, built by the view: the view reads its `syncLoading` for «busy» and the toolbar's currency
  selector opens the same dialog through it. The banner is shown to every role: it asks no permission of its own.
-->
<script lang="ts">
    import {DataQualityBanner} from '$lib/components/ui/feedback';
    import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';
    import FxPairAddModal from '$lib/features/fx/FxPairAddModal.svelte';
    import type {PortfolioBannerActions} from './portfolioBannerActions.svelte';

    interface Props {
        issues: DataQualityIssue[];
        actions: PortfolioBannerActions;
    }

    let {issues, actions}: Props = $props();

    const fxParts = $derived(actions.fxPairSlug.includes('-') ? actions.fxPairSlug.split('-') : actions.fxPairSlug.split('/'));
</script>

<DataQualityBanner {issues} mode="grouped" onaction={(action, target, issue) => actions.handleAction(action, target, issue)} busyCode={actions.syncingCode} />

<!-- FxPairAddModal — opened from DataQualityBanner CTA (and from the currency selector's «create forex») -->
{#if actions.fxPairModalOpen}
    <FxPairAddModal bind:open={actions.fxPairModalOpen} initialBase={fxParts[0] ?? ''} initialQuote={fxParts[1] ?? ''} oncreated={() => actions.handleFxPairCreated()} onsynced={(detail) => actions.handleFxPairCreationSynced(detail)} />
{/if}
