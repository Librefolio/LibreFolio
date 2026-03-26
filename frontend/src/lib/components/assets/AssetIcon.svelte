<!--
  AssetIcon — Asset type icon with fallback chain.
  1. Custom icon_url (img)
  2. PNG icon by asset_type (from /icons/asset-types/)
  3. Fallback BarChart3 (Lucide SVG)

  Svelte 5 runes, dark mode.
  Used by: AssetCard, AssetTable
-->
<script lang="ts">
    import {BarChart3} from 'lucide-svelte';

    interface Props {
        /** Custom icon URL (highest priority) */
        iconUrl?: string | null;
        /** Asset type for preset icon mapping */
        assetType?: string | null;
        /** Alt text for img */
        altText?: string;
        /** Icon size */
        size?: 'sm' | 'md' | 'lg';
    }

    let {iconUrl, assetType, altText = 'Asset', size = 'md'}: Props = $props();

    const sizes = {
        sm: {container: 'w-6 h-6', icon: 14, imgClass: 'w-5 h-5'},
        md: {container: 'w-10 h-10', icon: 20, imgClass: 'w-7 h-7'},
        lg: {container: 'w-16 h-16', icon: 28, imgClass: 'w-12 h-12'},
    };

    // Map asset_type to PNG filename (same icons used in AssetTable)
    const ASSET_TYPE_PNG_MAP: Record<string, string> = {
        STOCK: 'stock', ETF: 'etf', BOND: 'bond', CRYPTO: 'crypto',
        FUND: 'fund', HOLD: 'hold', CROWDFUND_LOAN: 'crowdfunding', OTHER: 'other',
    };

    let imgFailed = $state(false);
    let pngFailed = $state(false);

    let showImg = $derived(!!iconUrl && !imgFailed);
    let pngSrc = $derived(
        assetType && ASSET_TYPE_PNG_MAP[assetType]
            ? `/icons/asset-types/${ASSET_TYPE_PNG_MAP[assetType]}.png`
            : null
    );
    let showPng = $derived(!showImg && !!pngSrc && !pngFailed);

    // Reset imgFailed when iconUrl changes
    $effect(() => {
        void iconUrl;
        imgFailed = false;
    });

    // Reset pngFailed when assetType changes
    $effect(() => {
        void assetType;
        pngFailed = false;
    });
</script>

<div class="asset-icon {sizes[size].container} rounded-full bg-libre-green/10 dark:bg-libre-green/20 flex items-center justify-center shrink-0 overflow-hidden">
    {#if showImg}
        <img
                src={iconUrl}
                alt={altText}
                class="w-full h-full object-cover"
                onload={() => {}}
                onerror={() => { imgFailed = true; }}
        />
    {:else if showPng}
        <img
                src={pngSrc}
                alt={altText}
                class="{sizes[size].imgClass} object-contain"
                onerror={() => { pngFailed = true; }}
        />
    {:else}
        <BarChart3 size={sizes[size].icon} class="text-libre-green dark:text-green-400"/>
    {/if}
</div>

<style>
    .asset-icon {
        position: relative;
    }
</style>

