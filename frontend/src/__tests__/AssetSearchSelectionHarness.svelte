<script lang="ts">
    import type {ComponentProps} from 'svelte';
    import type AssetSearchAutocomplete from '$lib/components/assets/AssetSearchAutocomplete.svelte';

    type Props = ComponentProps<typeof AssetSearchAutocomplete>;
    type SearchResult = Parameters<NonNullable<Props['onselect']>>[0];

    let {onselect, disabled = false}: Props = $props();

    // Only the search boundary is synthetic. AssetModal owns everything this
    // callback starts: configuration, automatic verification and metadata.
    const selectedResult: SearchResult = {
        identifier: 'SYN-ATLAS',
        identifier_type: 'TICKER',
        display_name: 'Offline Atlas security',
        provider_code: 'lifecycle_atlas',
        currency: 'USD',
        asset_type: 'STOCK',
        provider_params: {note: 'search note'},
        provider_url: 'https://atlas.provider.invalid/security/SYN-ATLAS',
    };
</script>

<button type="button" data-testid="asset-search-offline-select" {disabled} onclick={() => onselect?.(selectedResult)}> Select synthetic offline asset </button>
