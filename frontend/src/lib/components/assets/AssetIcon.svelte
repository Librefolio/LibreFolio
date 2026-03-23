<!--
  AssetIcon — Asset type icon with fallback chain.
  1. Custom icon_url (img)
  2. Lucide icon by asset_type
  3. Fallback BarChart3

  Svelte 5 runes, dark mode.
  Used by: AssetCard, AssetTable
-->
<script lang="ts">
    import {
        BarChart3, TrendingUp, Globe, FileText, Bitcoin,
        Landmark, PiggyBank, Handshake, HelpCircle,
    } from 'lucide-svelte';

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
        sm: {container: 'w-6 h-6', icon: 14},
        md: {container: 'w-10 h-10', icon: 20},
        lg: {container: 'w-16 h-16', icon: 28},
    };

    // Map asset_type to Lucide component
    const typeIconMap: Record<string, any> = {
        STOCK: TrendingUp,
        ETF: Globe,
        BOND: FileText,
        CRYPTO: Bitcoin,
        FUND: Landmark,
        HOLD: PiggyBank,
        CROWDFUND_LOAN: Handshake,
        OTHER: HelpCircle,
    };

    let imgFailed = $state(false);

    let showImg = $derived(!!iconUrl && !imgFailed);
    let FallbackIcon = $derived(
        assetType && typeIconMap[assetType] ? typeIconMap[assetType] : BarChart3
    );

    // Reset imgFailed when iconUrl changes
    $effect(() => {
        void iconUrl;
        imgFailed = false;
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
    {:else}
        <FallbackIcon size={sizes[size].icon} class="text-libre-green dark:text-green-400" />
    {/if}
</div>

<style>
    .asset-icon {
        position: relative;
    }
</style>


