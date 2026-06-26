<script lang="ts">
    /**
     * BrokerIcon.svelte
     * Unified broker icon component. Fallback chain (invariant):
     *   1. custom icon_url
     *   2. portal_url/favicon.ico
     *   3. default_import_plugin icon (async, shared cache)
     *   4. Initial letter (or Briefcase if no altText)
     *
     * All chain logic lives in brokerIconChain.svelte.ts — do not duplicate.
     * Svelte 5 runes.
     */
    import {Briefcase} from 'lucide-svelte';
    import {createBrokerIconChain} from '$lib/utils/broker/brokerIconChain.svelte';

    // Props
    interface Props {
        iconUrl?: string | null;
        portalUrl?: string | null;
        pluginCode?: string | null;
        altText?: string;
        size?: 'sm' | 'md' | 'lg';
    }

    let {iconUrl = null, portalUrl = null, pluginCode = null, altText = 'Broker icon', size = 'md'}: Props = $props();

    // Size mappings
    const sizes = {
        sm: {container: 'w-6 h-6', icon: 16},
        md: {container: 'w-10 h-10', icon: 20},
        lg: {container: 'w-16 h-16', icon: 28},
    };

    // Shared reactive fallback chain
    const chain = createBrokerIconChain(() => ({
        icon_url: iconUrl,
        portal_url: portalUrl,
        default_import_plugin: pluginCode,
    }));
</script>

<div class="broker-icon {sizes[size].container} rounded-full bg-libre-green/10 dark:bg-libre-green/20 flex items-center justify-center shrink-0 overflow-hidden">
    {#if chain.currentDisplayUrl}
        {#key chain.currentDisplayUrl}
            <img src={chain.currentDisplayUrl} alt={altText} class="w-full h-full object-cover {chain.imageLoaded ? '' : 'opacity-0'}" onload={chain.handleLoad} onerror={chain.handleError} referrerpolicy="no-referrer" />
        {/key}
    {/if}

    {#if !chain.imageLoaded || !chain.currentDisplayUrl}
        <div class="absolute inset-0 flex items-center justify-center">
            {#if altText.trim()}
                <span class="text-xs font-bold text-libre-green dark:text-green-400 uppercase select-none">
                    {altText.trim().charAt(0)}
                </span>
            {:else}
                <Briefcase size={sizes[size].icon} class="text-libre-green dark:text-green-400" />
            {/if}
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
