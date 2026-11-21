<script lang="ts">
    import AssetIcon from '$lib/features/assets/AssetIcon.svelte';
    import MarqueeName from './MarqueeName.svelte';
    import NowLine, {type NowLineContent} from './NowLine.svelte';

    interface Props {
        label: string;
        iconUrl?: string | null;
        assetType?: string | null;
        /** «Now» under the name, in the targets table while its column is hidden (G5-1 of project 67). */
        now?: NowLineContent | null;
    }

    let {label, iconUrl = null, assetType = null, now = null}: Props = $props();
</script>

<span class="flex min-w-0 items-center gap-2">
    <AssetIcon {iconUrl} {assetType} altText="" size="sm" />
    {#if now}
        <span class="flex min-w-0 flex-col">
            <MarqueeName text={label} />
            <NowLine {now} />
        </span>
    {:else}
        <MarqueeName text={label} />
    {/if}
</span>
