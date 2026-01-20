<script lang="ts">
    /**
     * ImportPluginSelect - Reusable dropdown for selecting import plugins
     *
     * Loads available plugins from the API and displays them in a select.
     * Can be used in broker forms and transaction import forms.
     */
    import {onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {api} from '$lib/api';

    // Props
    export let value: string = '';
    export let disabled: boolean = false;
    export let placeholder: string = '';

    // Plugin data
    interface ImportPlugin {
        id: string;
        name: string;
        description: string;
        icon?: string;
    }

    let plugins: ImportPlugin[] = [];
    let loading = true;
    let error: string | null = null;

    // Load plugins on mount
    onMount(async () => {
        await loadPlugins();
    });

    async function loadPlugins() {
        loading = true;
        error = null;

        try {
            const response = await api.get<{
                plugins: ImportPlugin[];
            }>('/brokers/import/plugins');

            plugins = response.plugins || [];
        } catch (e) {
            console.error('Failed to load import plugins:', e);
            error = 'Failed to load plugins';
        } finally {
            loading = false;
        }
    }

    // Get selected plugin info
    $: selectedPlugin = plugins.find(p => p.id === value);
</script>

<div class="import-plugin-select">
    <select
            bind:value
            {disabled}
            class="w-full px-3 py-2 border rounded-lg
                   focus:ring-2 focus:ring-libre-green focus:border-libre-green
                   transition-colors disabled:opacity-50 disabled:bg-gray-100"
    >
        <option value="">{placeholder || $_('brokers.selectPlugin')}</option>
        {#each plugins as plugin}
            <option value={plugin.id}>{plugin.name}</option>
        {/each}
    </select>

    {#if loading}
        <p class="text-xs text-gray-400 mt-1">{$_('common.loading')}</p>
    {:else if error}
        <p class="text-xs text-red-500 mt-1">{error}</p>
    {:else if selectedPlugin?.description}
        <p class="text-xs text-gray-500 mt-1">{selectedPlugin.description}</p>
    {/if}
</div>

