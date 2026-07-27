<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import SearchSelect from '$lib/components/ui/select/SearchSelect.svelte';
    import type {SelectOption} from '$lib/components/ui/select/types';
    import {assetStoreVersion, ensureAssetsLoaded, getAllAssets} from '$lib/stores/reference/assetStore';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';

    interface Props {
        value: unknown;
        onchange: (value: number) => void;
    }

    let {value, onchange}: Props = $props();
    let loading = $state(false);
    let loadFailed = $state(false);
    let loadStarted = false;

    let options: SelectOption[] = $derived.by(() => {
        $assetStoreVersion;
        return getAllAssets()
            .map((asset) => ({
                value: String(asset.id),
                label: asset.display_name,
                searchText: [asset.display_name, asset.currency, asset.identifier_ticker, asset.identifier_isin, asset.identifier_other].filter(Boolean).join(' '),
                icon: asset.icon_url ?? getAssetTypeIconUrl(asset.asset_type),
                badge: asset.currency,
            }))
            .sort((left, right) => left.label.localeCompare(right.label));
    });

    $effect(() => {
        if (loadStarted) return;
        loadStarted = true;
        loading = true;
        void ensureAssetsLoaded()
            .catch(() => {
                loadFailed = true;
            })
            .finally(() => {
                loading = false;
            });
    });

    function selectedValue(): string {
        return typeof value === 'number' && Number.isInteger(value) ? String(value) : '';
    }

    function handleChange(selected: string): void {
        const assetId = Number(selected);
        if (Number.isInteger(assetId) && assetId > 0) onchange(assetId);
    }
</script>

<div class="w-64" data-testid="signal-comparison-asset-control">
    <SearchSelect value={selectedValue()} {options} {loading} compact inlineSearch dropdownPosition="auto" dropdownMinWidth={280} placeholder={$t('signals.comparisonAsset.placeholder')} testId="signal-comparison-asset-select" onchange={handleChange} />
    {#if loadFailed}
        <p class="mt-1 text-[10px] text-red-500" data-testid="signal-comparison-asset-error">
            {$t('signals.comparisonAsset.loadError')}
        </p>
    {/if}
</div>
