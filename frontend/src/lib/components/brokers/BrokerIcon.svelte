<script lang="ts">
    /**
     * BrokerIcon.svelte
     * Unified broker icon component with fallback chain:
     * 1. custom icon_url
     * 2. portal_url favicon
     * 3. default_import_plugin icon (loads from API to get real icon_url)
     * 4. Briefcase fallback
     */
    import { onMount } from 'svelte';
    import { Briefcase } from 'lucide-svelte';
    import { api } from '$lib/api';

    // Props
    export let iconUrl: string | null | undefined = null;
    export let portalUrl: string | null | undefined = null;
    export let pluginCode: string | null | undefined = null;
    export let altText: string = 'Broker icon';
    export let size: 'sm' | 'md' | 'lg' = 'md';

    // Size mappings
    const sizes = {
        sm: { container: 'w-6 h-6', icon: 16 },
        md: { container: 'w-10 h-10', icon: 20 },
        lg: { container: 'w-16 h-16', icon: 28 }
    };

    // State
    let currentAttempt: 'icon' | 'portal' | 'plugin' | 'fallback' = 'icon';
    let imgElement: HTMLImageElement | null = null;
    let imageLoaded = false;
    let currentUrl: string | null = null;
    let pluginIconUrl: string | null = null;
    let pluginsLoaded = false;

    // Load plugins once on mount
    onMount(async () => {
        try {
            const plugins = await api.get('/brokers/import/plugins');
            if (Array.isArray(plugins)) {
                // Find the plugin icon_url if we have a pluginCode
                if (pluginCode) {
                    const plugin = plugins.find(p => p.code === pluginCode);
                    if (plugin?.icon_url) {
                        pluginIconUrl = plugin.icon_url;
                    }
                }
            }
        } catch (err) {
            console.error('Failed to load plugins for icon:', err);
        } finally {
            pluginsLoaded = true;
        }
    });

    // When props or plugins change, restart from beginning
    // Use a reactive statement that compares actual string values
    $: propsKey = `${iconUrl ?? ''}|${portalUrl ?? ''}|${pluginCode ?? ''}|${pluginsLoaded}`;

    // Track previous key to detect changes
    let prevPropsKey = '';

    $: if (propsKey !== prevPropsKey) {
        prevPropsKey = propsKey;
        resetAttempt();
    }

    function resetAttempt() {
        currentAttempt = 'icon';
        imageLoaded = false;
        currentUrl = computeUrl('icon');

        // If first URL is null/empty, immediately try next fallbacks
        if (!currentUrl) {
            moveToNextFallback();
        }
    }

    // Key to force img re-render when URL changes synchronously
    let imageKey = 0;

    function computeUrl(attempt: typeof currentAttempt): string | null {
        switch (attempt) {
            case 'icon':
                // Treat empty string as null
                return (iconUrl && iconUrl.trim()) ? iconUrl : null;
            case 'portal':
                if (portalUrl && portalUrl.trim()) {
                    try {
                        const url = new URL(portalUrl);
                        return `${url.origin}/favicon.ico`;
                    } catch {
                        return null;
                    }
                }
                return null;
            case 'plugin':
                // Use the icon_url from plugin API response
                return pluginIconUrl;
            case 'fallback':
                return null;
        }
    }

    function moveToNextFallback() {
        imageLoaded = false;

        switch (currentAttempt) {
            case 'icon':
                currentAttempt = 'portal';
                break;
            case 'portal':
                currentAttempt = 'plugin';
                break;
            case 'plugin':
                currentAttempt = 'fallback';
                break;
            default:
                currentAttempt = 'fallback';
        }

        currentUrl = computeUrl(currentAttempt);
        imageKey++; // Force img element to re-mount with new src

        // If new URL is null, skip to next
        if (!currentUrl && currentAttempt !== 'fallback') {
            moveToNextFallback();
        }
    }

    function handleLoad() {
        imageLoaded = true;
    }

    function handleError() {
        imageLoaded = false;
        moveToNextFallback();
    }
</script>

<div class="broker-icon {sizes[size].container} rounded-full bg-libre-green/10 dark:bg-libre-green/20 flex items-center justify-center shrink-0 overflow-hidden">
    {#if currentUrl && currentAttempt !== 'fallback'}
        {#key imageKey}
            <img
                bind:this={imgElement}
                src={currentUrl}
                alt={altText}
                class="w-full h-full object-cover"
                class:opacity-0={!imageLoaded}
                on:load={handleLoad}
                on:error={handleError}
            />
        {/key}
    {/if}

    {#if !imageLoaded || currentAttempt === 'fallback'}
        <!-- Fallback: Briefcase icon (shown while loading or as final fallback) -->
        <div class="absolute inset-0 flex items-center justify-center">
            <Briefcase size={sizes[size].icon} class="text-libre-green dark:text-green-400" />
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
