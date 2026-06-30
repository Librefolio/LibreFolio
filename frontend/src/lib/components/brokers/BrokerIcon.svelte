<script lang="ts">
    /**
     * BrokerIcon.svelte
     * Unified broker icon component. Fallback chain (invariant):
     *   1. custom icon_url
     *   2. portal_url/favicon.ico
     *   3. default_import_plugin icon (async, shared cache)
     *   4. System briefcase icon
     *
     * All chain logic lives in brokerIconChain.svelte.ts — do not duplicate.
     * Svelte 5 runes.
     */
    import {Briefcase} from 'lucide-svelte';
    import {ensureBrokerIconFieldsLoaded} from '$lib/stores/reference/brokerStore';
    import {createBrokerIconChain} from '$lib/utils/broker/brokerIconChain.svelte';
    import {normalizeBrokerIconField} from '$lib/utils/broker/brokerHelpers';

    // Props
    interface Props {
        brokerId?: number | null;
        iconUrl?: string | null;
        portalUrl?: string | null;
        pluginCode?: string | null;
        altText?: string;
        size?: 'sm' | 'md' | 'lg' | number;
    }

    let {brokerId = null, iconUrl = null, portalUrl = null, pluginCode = null, altText = 'Broker icon', size = 'md'}: Props = $props();

    // Size mappings
    const presetSizes = {
        sm: {container: 24, icon: 16},
        md: {container: 40, icon: 20},
        lg: {container: 64, icon: 28},
    };
    let sizeConfig = $derived.by(() => {
        if (typeof size === 'number') {
            return {container: size, icon: Math.max(12, Math.round(size * 0.6))};
        }
        return presetSizes[size];
    });

    // Shared reactive fallback chain
    const chain = createBrokerIconChain(() => ({
        icon_url: iconUrl,
        portal_url: portalUrl,
        default_import_plugin: pluginCode,
    }));

    $effect(() => {
        if (brokerId == null || brokerId <= 0) return;
        if (normalizeBrokerIconField(iconUrl) || normalizeBrokerIconField(portalUrl) || normalizeBrokerIconField(pluginCode)) {
            return;
        }
        void ensureBrokerIconFieldsLoaded(brokerId);
    });
</script>

<div class="broker-icon rounded-full bg-libre-green/10 dark:bg-libre-green/20 flex items-center justify-center shrink-0 overflow-hidden" style="width:{sizeConfig.container}px;height:{sizeConfig.container}px">
    {#if chain.currentDisplayUrl}
        {#key chain.currentDisplayUrl}
            <img src={chain.currentDisplayUrl} alt={altText} class="w-full h-full object-contain {chain.imageLoaded ? '' : 'opacity-0'}" onload={chain.handleLoad} onerror={chain.handleError} referrerpolicy="no-referrer" />
        {/key}
    {/if}

    {#if !chain.imageLoaded || !chain.currentDisplayUrl}
        <div class="absolute inset-0 flex items-center justify-center">
            <Briefcase size={sizeConfig.icon} class="text-libre-green dark:text-green-400" />
        </div>
    {/if}
</div>

<style>
    .broker-icon {
        position: relative;
    }

    img {
        transition: opacity 0.2s ease-in-out;
    }
</style>
