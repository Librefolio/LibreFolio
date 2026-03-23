<script lang="ts">
    /**
     * BrokerIcon.svelte
     * Unified broker icon component with fallback chain:
     * 1. custom icon_url
     * 2. portal_url favicon
     * 3. default_import_plugin icon (loads from API to get real icon_url)
     * 4. Briefcase fallback
     *
     * Svelte 5 runes.
     */
    import {onMount} from 'svelte';
    import {Briefcase} from 'lucide-svelte';
    import {zodiosApi} from '$lib/api';
    import {debug} from '$lib/debug';

    // Props
    interface Props {
        iconUrl?: string | null;
        portalUrl?: string | null;
        pluginCode?: string | null;
        altText?: string;
        size?: 'sm' | 'md' | 'lg';
    }

    let {
        iconUrl = null,
        portalUrl = null,
        pluginCode = null,
        altText = 'Broker icon',
        size = 'md',
    }: Props = $props();

    // Size mappings
    const sizes = {
        sm: {container: 'w-6 h-6', icon: 16},
        md: {container: 'w-10 h-10', icon: 20},
        lg: {container: 'w-16 h-16', icon: 28}
    };

    // State
    let currentAttempt = $state<'icon' | 'portal' | 'plugin' | 'fallback'>('icon');
    let imgElement = $state<HTMLImageElement | null>(null);
    let imageLoaded = $state(false);
    let currentUrl = $state<string | null>(null);
    let pluginIconUrl = $state<string | null>(null);
    let pluginsLoaded = $state(false);
    let imageKey = $state(0);

    // ============================================================
    // FUNCTIONS (defined BEFORE reactive statements that use them)
    // ============================================================

    function computeUrl(attempt: typeof currentAttempt): string | null {
        switch (attempt) {
            case 'icon':
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
        imageKey++;

        // If new URL is null, skip to next (but wait for plugins if on plugin step)
        if (!currentUrl && currentAttempt !== 'fallback') {
            if (currentAttempt === 'plugin' && !pluginsLoaded) {
                return; // Will be handled when pluginsLoaded becomes true
            }
            moveToNextFallback();
        }
    }

    function resetAttempt() {
        debug.log('BrokerIcon', 'resetAttempt', {iconUrl, portalUrl, pluginCode});
        currentAttempt = 'icon';
        imageLoaded = false;
        currentUrl = computeUrl('icon');

        if (!currentUrl) {
            moveToNextFallback();
        }
    }

    function handleLoad() {
        debug.log('BrokerIcon', 'handleLoad', currentUrl);
        imageLoaded = true;
    }

    function handleError() {
        debug.log('BrokerIcon', 'handleError', currentUrl);
        imageLoaded = false;
        moveToNextFallback();
    }

    // ============================================================
    // LIFECYCLE & REACTIVE STATEMENTS
    // ============================================================

    // Load plugins once on mount
    onMount(async () => {
        debug.log('BrokerIcon', 'onMount', {iconUrl, portalUrl, pluginCode});
        try {
            const plugins = await zodiosApi.list_plugins_api_v1_brokers_import_plugins_get();
            if (Array.isArray(plugins) && pluginCode) {
                const plugin = plugins.find(p => p.code === pluginCode);
                if (plugin?.icon_url) {
                    pluginIconUrl = plugin.icon_url;
                }
            }
        } catch (err) {
            console.error('Failed to load plugins for icon:', err);
        } finally {
            pluginsLoaded = true;
        }
    });

    // Key for props
    let mainPropsKey = $derived(`${iconUrl ?? ''}|${portalUrl ?? ''}|${pluginCode ?? ''}`);

    // Reset when props change
    let prevMainPropsKey = '';
    $effect(() => {
        if (mainPropsKey !== prevMainPropsKey) {
            prevMainPropsKey = mainPropsKey;
            resetAttempt();
        }
    });

    // When plugins load while on plugin attempt
    $effect(() => {
        if (pluginsLoaded && pluginCode && !imageLoaded && currentAttempt === 'plugin') {
            currentUrl = computeUrl('plugin');
            if (currentUrl) {
                imageKey++;
            } else {
                moveToNextFallback();
            }
        }
    });
</script>

<div class="broker-icon {sizes[size].container} rounded-full bg-libre-green/10 dark:bg-libre-green/20 flex items-center justify-center shrink-0 overflow-hidden">
    {#if currentUrl && currentAttempt !== 'fallback'}
        {#key imageKey}
            <img
                    bind:this={imgElement}
                    src={currentUrl}
                    alt={altText}
                    class="w-full h-full object-cover {imageLoaded ? '' : 'opacity-0'}"
                    onload={handleLoad}
                    onerror={handleError}
            />
        {/key}
    {/if}

    {#if !imageLoaded || currentAttempt === 'fallback'}
        <div class="absolute inset-0 flex items-center justify-center">
            <Briefcase size={sizes[size].icon} class="text-libre-green dark:text-green-400"/>
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
