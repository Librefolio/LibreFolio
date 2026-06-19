<script lang="ts">
    /**
     * BrokerIcon.svelte
     * Unified broker icon component with fallback chain:
     * 1. custom icon_url
     * 2. portal_url favicon
     * 3. default_import_plugin icon (loads from API reactively)
     * 4. Briefcase fallback
     *
     * Svelte 5 runes — pure $derived approach (no imperative state machine).
     */
    import {Briefcase} from 'lucide-svelte';
    import {zodiosApi} from '$lib/api';

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

    // ============================================================
    // REACTIVE PLUGIN LOADING (replaces onMount)
    // ============================================================

    let pluginIconUrl = $state<string | null>(null);

    $effect(() => {
        const code = pluginCode;
        if (!code) {
            pluginIconUrl = null;
            return;
        }
        loadPluginIcon(code);
    });

    async function loadPluginIcon(code: string) {
        try {
            const plugins = await zodiosApi.list_plugins_api_v1_brokers_import_plugins_get();
            const plugin = plugins.find((p) => p.code === code);
            // Generator quirk: nullable fields get typed as (string | null) | Array<string | null>.
            // At runtime the backend only ever produces (string | null).
            const rawIcon = plugin?.icon_url as string | null | undefined;
            pluginIconUrl = rawIcon ?? null;
        } catch {
            pluginIconUrl = null;
        }
    }

    // ============================================================
    // DECLARATIVE FALLBACK CHAIN
    // ============================================================

    /** Ordered list of candidate URLs derived from props + pluginIconUrl */
    let candidateUrls = $derived.by(() => {
        const urls: string[] = [];
        if (iconUrl?.trim()) urls.push(iconUrl);
        if (portalUrl?.trim()) {
            try {
                urls.push(new URL(portalUrl).origin + '/favicon.ico');
            } catch {}
        }
        if (pluginIconUrl) urls.push(pluginIconUrl);
        return urls;
    });

    /** Set of URLs that failed to load — updated only by handleError() */
    let failedUrls = $state(new Set<string>());

    /** First non-failed URL in the candidate chain, or null for Briefcase fallback */
    let currentDisplayUrl = $derived(candidateUrls.find((u) => !failedUrls.has(u)) ?? null);

    /** Props key — reset failedUrls when props change */
    let mainPropsKey = $derived(`${iconUrl ?? ''}|${portalUrl ?? ''}|${pluginCode ?? ''}`);

    let prevPropsKey = '';
    $effect(() => {
        const key = mainPropsKey;
        if (key !== prevPropsKey) {
            prevPropsKey = key;
            failedUrls = new Set();
        }
    });

    // ============================================================
    // IMAGE HANDLERS
    // ============================================================

    let imageLoaded = $state(false);

    // Reset imageLoaded when display URL changes
    let prevDisplayUrl = '';
    $effect(() => {
        const url = currentDisplayUrl ?? '';
        if (url !== prevDisplayUrl) {
            prevDisplayUrl = url;
            // Data URIs are decoded inline — treat as already loaded to avoid
            // the onload race condition when many items render simultaneously.
            imageLoaded = url.startsWith('data:');
        }
    });

    function handleLoad() {
        imageLoaded = true;
    }

    function handleError() {
        if (currentDisplayUrl) {
            failedUrls = new Set([...failedUrls, currentDisplayUrl]);
        }
        imageLoaded = false;
    }
</script>

<div class="broker-icon {sizes[size].container} rounded-full bg-libre-green/10 dark:bg-libre-green/20 flex items-center justify-center shrink-0 overflow-hidden">
    {#if currentDisplayUrl}
        {#key currentDisplayUrl}
            <img src={currentDisplayUrl} alt={altText} class="w-full h-full object-cover {imageLoaded ? '' : 'opacity-0'}" onload={handleLoad} onerror={handleError} />
        {/key}
    {/if}

    {#if !imageLoaded || !currentDisplayUrl}
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
