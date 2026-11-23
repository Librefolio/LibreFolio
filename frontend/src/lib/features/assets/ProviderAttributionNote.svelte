<!--
  ProviderAttributionNote — the line a provider's terms ask for (project 76, P4 and TL42).

  CoinGecko's terms ask for «Powered by CoinGecko», linked to its site. By the developer's decision (TL42, 23/11/2026)
  it lives on CoinGecko's own pages only: its card in Settings › Plugins (this note) and its user-guide page. The screens
  that show its prices carry none: the asset shows CoinGecko's icon, and its page links to the coin on coingecko.com.
  The note draws one line per named provider that has an attribution, and nothing for one that has none. The
  attribution comes from the provider list (`GET /assets/provider`); the brand phrase is shown as the provider writes
  it, in every language.

  Its text is `text-xs` in the secondary text role, above the terms' 10 px floor, never in a tooltip. The link leaves
  the app in a new tab.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {assetProvidersVersion, ensureAssetProvidersCached, getAssetProviderAttribution} from '$lib/utils/providerHelpers';
    import {attributionsFor} from './providerAttribution';

    interface Props {
        /** The providers named (a plugin card's own code), repeats allowed. */
        providerCodes?: readonly (string | null | undefined)[];
        testId?: string;
    }

    let {providerCodes = [], testId = 'provider-attribution-note'}: Props = $props();

    const lines = $derived.by(() => {
        // The provider list may land after the first draw: its version makes the line appear then
        void $assetProvidersVersion;
        return attributionsFor(providerCodes, getAssetProviderAttribution);
    });

    onMount(() => {
        void ensureAssetProvidersCached();
    });
</script>

{#if lines.length > 0}
    <p class="flex flex-wrap justify-start gap-x-2 text-xs text-lf-secondary" data-testid={testId} data-providers={lines.map((line) => line.code).join(',')}>
        {#each lines as line (line.code)}
            <a href={line.url} target="_blank" rel="noopener noreferrer" class="text-lf-secondary hover:text-lf-link hover:underline focus-visible:outline-lf-focus" data-testid="provider-attribution-link" data-provider={line.code}>{line.text}</a>
        {/each}
    </p>
{/if}
