<script lang="ts">
    import AssetIcon from '$lib/components/assets/AssetIcon.svelte';
    import MarqueeName from './MarqueeName.svelte';

    interface Props {
        label: string;
        iconUrl?: string | null;
        assetType?: string | null;
    }

    let {label, iconUrl = null, assetType = null}: Props = $props();
</script>

<span class="flex min-w-0 items-center gap-2">
    <AssetIcon {iconUrl} {assetType} altText="" size="sm" />
    <MarqueeName text={label} />
</span>
