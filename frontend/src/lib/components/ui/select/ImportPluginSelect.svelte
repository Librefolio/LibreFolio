<script module lang="ts">
    import type {BrimPlugin} from '$lib/types';

    // Module-level cache: shared across all ImportPluginSelect instances
    let cachedPlugins: BrimPlugin[] | null = null;
    let cachePromise: Promise<BrimPlugin[]> | null = null;

    /** Export for other components to reuse the cached plugin list */
    export function getCachedPlugins(): BrimPlugin[] | null {
        return cachedPlugins;
    }

    /** Set cache from external source (e.g. after API call) */
    export function setCachedPlugins(plugins: BrimPlugin[]) {
        cachedPlugins = plugins;
    }
</script>

<script lang="ts">
    /**
     * ImportPluginSelect - Svelte 5
     * Reusable dropdown for selecting import plugins.
     * Uses SearchSelect with broker icons for better UX.
     * Supports filtering by compatible plugins (from BrimFile.compatible_plugins).
     */
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {SearchSelect, type SelectOption} from '$lib/components/ui/select';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';

    interface Props {
        value?: string;
        disabled?: boolean;
        placeholder?: string;
        /** When set, only show these plugins (ordered by priority from backend) */
        compatiblePlugins?: string[];
        /** When true, hides the description paragraph below the select (for use in compact table cells) */
        compact?: boolean;
        onchange?: (value: string) => void;
    }

    let {value = $bindable(''), disabled = false, placeholder = '', compatiblePlugins, compact = false, onchange}: Props = $props();

    let plugins: BrimPlugin[] = $state([]);
    let loading = $state(!cachedPlugins); // Start as not-loading if cache exists
    let error: string | null = $state(null);

    // Filter and order plugins by compatible list
    let filteredPlugins = $derived.by(() => {
        if (!compatiblePlugins || compatiblePlugins.length === 0) return plugins;
        // Preserve order from compatiblePlugins (sorted by priority desc from backend)
        const pluginMap = new Map(plugins.map((p) => [p.code, p]));
        const ordered: BrimPlugin[] = [];
        for (const code of compatiblePlugins) {
            const p = pluginMap.get(code);
            if (p) ordered.push(p);
        }
        return ordered;
    });

    // Convert plugins to SelectOption format with icon_url in data
    let pluginOptions: SelectOption[] = $derived(
        filteredPlugins.map((p) => ({
            value: p.code,
            label: p.name,
            searchText: p.description,
            icon: (p.icon_url as string | null | undefined) || undefined,
            data: p,
        })),
    );

    // Get selected plugin info
    let selectedPlugin = $derived(plugins.find((p) => p.code === value));

    // Load plugins on component initialization — sync path for cache hits
    $effect(() => {
        if (cachedPlugins) {
            plugins = cachedPlugins;
            loading = false;
        } else {
            loadPlugins();
        }
    });

    async function loadPlugins() {
        loading = true;
        error = null;

        try {
            if (!cachePromise) {
                cachePromise = zodiosApi.list_plugins_api_v1_brokers_import_plugins_get().then((r) => (r as BrimPlugin[]) || []);
            }
            const result = await cachePromise;
            cachedPlugins = result;
            plugins = result;
        } catch (e) {
            console.error('Failed to load import plugins:', e);
            error = 'Failed to load plugins';
            cachePromise = null;
        } finally {
            loading = false;
        }
    }

    function getDescription(option: SelectOption): string | undefined {
        return (option.data as BrimPlugin | undefined)?.description;
    }

    function handleChange(newValue: string) {
        value = newValue;
        onchange?.(newValue);
    }
</script>

<div class="import-plugin-select" data-testid="import-plugin-select">
    <SearchSelect bind:value {disabled} inlineSearch={true} {loading} onchange={handleChange} options={pluginOptions} placeholder={placeholder || $_('brokers.selectPlugin')}>
        {#snippet item(option)}
            <div class="flex items-center gap-2">
                <BrokerIcon iconUrl={option.icon} altText={option.label} size="sm" />
                <div class="min-w-0 flex-1">
                    <div class="text-sm font-medium">{option.label}</div>
                    {#if getDescription(option)}
                        <div class="text-xs text-gray-500 truncate">{getDescription(option)}</div>
                    {/if}
                </div>
            </div>
        {/snippet}
        {#snippet selectedItem(option)}
            <div class="flex items-center gap-2">
                <BrokerIcon iconUrl={option.icon} altText={option.label} size="sm" />
                <span class="truncate">{option.label}</span>
            </div>
        {/snippet}
    </SearchSelect>

    {#if !compact}
        {#if loading}
            <p class="text-xs text-gray-400 mt-1">{$_('common.loading')}</p>
        {:else if error}
            <p class="text-xs text-red-500 mt-1">{error}</p>
        {:else if selectedPlugin?.description}
            <p class="text-xs text-gray-500 mt-1">{selectedPlugin.description}</p>
        {/if}
    {/if}
</div>
