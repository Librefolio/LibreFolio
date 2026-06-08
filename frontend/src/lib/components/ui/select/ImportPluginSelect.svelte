<script lang="ts">
    /**
     * ImportPluginSelect - Svelte 5
     * Reusable dropdown for selecting import plugins.
     * Uses SearchSelect with broker icons for better UX.
     */
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {SearchSelect, type SelectOption} from '$lib/components/ui/select';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import type {BrimPlugin} from '$lib/types';

    // Module-level cache: shared across all ImportPluginSelect instances
    let cachedPlugins: BrimPlugin[] | null = null;
    let cachePromise: Promise<BrimPlugin[]> | null = null;

    interface Props {
        value?: string;
        disabled?: boolean;
        placeholder?: string;
        onchange?: (value: string) => void;
    }

    let {value = $bindable(''), disabled = false, placeholder = '', onchange}: Props = $props();

    let plugins = $state<BrimPlugin[]>([]);
    let loading = $state(true);
    let error = $state<string | null>(null);

    // Convert plugins to SelectOption format with icon_url in data
    let pluginOptions = $derived<SelectOption[]>(
        plugins.map((p) => ({
            value: p.code,
            label: p.name,
            searchText: p.description,
            // Generator quirk: nullable fields get typed as (string | null) | Array<string | null>.
            // At runtime the backend only ever produces (string | null).
            icon: (p.icon_url as string | null | undefined) || undefined,
            data: p,
        })),
    );

    // Get selected plugin info
    let selectedPlugin = $derived(plugins.find((p) => p.code === value));

    // Load plugins on component initialization
    $effect(() => {
        loadPlugins();
    });

    async function loadPlugins() {
        if (cachedPlugins) {
            plugins = cachedPlugins;
            loading = false;
            return;
        }
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

    {#if loading}
        <p class="text-xs text-gray-400 mt-1">{$_('common.loading')}</p>
    {:else if error}
        <p class="text-xs text-red-500 mt-1">{error}</p>
    {:else if selectedPlugin?.description}
        <p class="text-xs text-gray-500 mt-1">{selectedPlugin.description}</p>
    {/if}
</div>
