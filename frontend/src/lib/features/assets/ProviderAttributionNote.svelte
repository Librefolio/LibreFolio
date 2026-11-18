<!--
  ProviderAttributionNote — the line a provider's terms ask to show with its prices (project 76, P4).

  CoinGecko's terms: every price it gives is shown with «Powered by CoinGecko», prominent, linked to its site. This
  note draws that line once per such provider among the assets of a screen — never once per row — and nothing at all
  when none is there: whoever has no crypto never sees it. The providers come straight (`providerCodes`, the asset
  page) or through the assets shown (`assetIds`, read from the asset store: the Dashboard's positions carry no
  provider). The attribution comes from the provider list (`GET /assets/provider`); the brand phrase is shown as the
  provider writes it, in every language.

  Its text is `text-xs` in the secondary text role, above the terms' 10 px floor and «prominent», never in a tooltip.
  The link leaves the app in a new tab.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {assetProvidersVersion, ensureAssetProvidersCached, getAssetProviderAttribution} from '$lib/utils/providerHelpers';
    import {assetStoreVersion, ensureAssetsLoaded, getAssetInfo} from '$lib/stores/reference/assetStore';
    import {attributionsFor} from './providerAttribution';

    interface Props {
        /** The providers of the prices on screen (the assets' `provider_code`), repeats allowed. */
        providerCodes?: readonly (string | null | undefined)[];
        /** The assets on screen, when the screen knows only their ids: their providers come from the asset store. */
        assetIds?: readonly number[];
        /** Where the line sits in its row. */
        align?: 'start' | 'center' | 'end';
        testId?: string;
        /** Spacing classes for the line where it sits (padding, margins): none drawn when there is no line. */
        extraClass?: string;
    }

    let {providerCodes = [], assetIds = [], align = 'start', testId = 'provider-attribution-note', extraClass = ''}: Props = $props();

    const lines = $derived.by(() => {
        // Both caches may land after the first draw: their versions make the line appear then
        void $assetProvidersVersion;
        void $assetStoreVersion;
        const codes = [...providerCodes, ...assetIds.map((id) => getAssetInfo(id)?.provider_code)];
        return attributionsFor(codes, getAssetProviderAttribution);
    });

    const alignClass = $derived(align === 'center' ? 'justify-center text-center' : align === 'end' ? 'justify-end text-right' : 'justify-start');

    onMount(() => {
        void ensureAssetProvidersCached();
    });

    // The ids may come after the first draw (a saved view's positions): the asset store loads when there are some
    $effect(() => {
        if (assetIds.length > 0) void ensureAssetsLoaded();
    });
</script>

{#if lines.length > 0}
    <p class="flex flex-wrap gap-x-2 text-xs text-lf-secondary {alignClass} {extraClass}" data-testid={testId} data-providers={lines.map((line) => line.code).join(',')}>
        {#each lines as line (line.code)}
            <a href={line.url} target="_blank" rel="noopener noreferrer" class="text-lf-secondary hover:text-lf-link hover:underline focus-visible:outline-lf-focus" data-testid="provider-attribution-link" data-provider={line.code}>{line.text}</a>
        {/each}
    </p>
{/if}
