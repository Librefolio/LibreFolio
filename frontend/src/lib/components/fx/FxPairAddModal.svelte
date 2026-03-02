<!--
  FxPairAddModal — Modal to add a new currency pair with provider configuration.
-->
<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import {zodiosApi} from '$lib/api';
    import {Plus, Trash2, GripVertical} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';

    export let open: boolean = false;

    const dispatch = createEventDispatcher<{
        created: void;
        close: void;
    }>();

    // State
    let baseCurrency = '';
    let quoteCurrency = '';
    let providerEntries: Array<{code: string; priority: number}> = [];
    let saving = false;
    let error: string | null = null;

    // Available providers
    let availableProviders: Array<{code: string; name: string}> = [];
    let newProviderCode = '';

    $: usedCodes = new Set(providerEntries.map(p => p.code));
    $: unusedProviders = availableProviders.filter(p => !usedCodes.has(p.code));
    $: isValid = baseCurrency.length === 3 && quoteCurrency.length === 3
        && baseCurrency !== quoteCurrency && providerEntries.length > 0;

    $: if (open) loadProviders();

    async function loadProviders() {
        try {
            const response = await zodiosApi.list_providers_api_v1_fx_providers_get();
            availableProviders = (response as any[]).map((p: any) => ({code: p.code, name: p.name}));
        } catch (e) {
            console.error('Failed to load providers:', e);
        }
    }

    function addProvider() {
        if (!newProviderCode) return;
        const nextPriority = providerEntries.length > 0
            ? Math.max(...providerEntries.map(p => p.priority)) + 1 : 1;
        providerEntries = [...providerEntries, {code: newProviderCode, priority: nextPriority}];
        newProviderCode = '';
    }

    function removeProvider(code: string) {
        providerEntries = providerEntries.filter(p => p.code !== code);
        // Re-number priorities
        providerEntries = providerEntries.map((p, i) => ({...p, priority: i + 1}));
    }

    function getProviderName(code: string): string {
        return availableProviders.find(p => p.code === code)?.name || code;
    }

    async function handleSave() {
        if (!isValid) return;
        saving = true;
        error = null;

        // Normalize alphabetical order
        const base = baseCurrency.toUpperCase() < quoteCurrency.toUpperCase()
            ? baseCurrency.toUpperCase() : quoteCurrency.toUpperCase();
        const quote = baseCurrency.toUpperCase() < quoteCurrency.toUpperCase()
            ? quoteCurrency.toUpperCase() : baseCurrency.toUpperCase();

        try {
            const items = providerEntries.map(p => ({
                base, quote,
                provider_code: p.code,
                priority: p.priority,
            }));
            await zodiosApi.create_pair_sources_bulk_api_v1_fx_providers_pair_sources_post(items);
            dispatch('created');
            handleClose();
        } catch (e: any) {
            error = e?.message || 'Failed to create pair';
        } finally {
            saving = false;
        }
    }

    function handleClose() {
        baseCurrency = '';
        quoteCurrency = '';
        providerEntries = [];
        error = null;
        dispatch('close');
    }
</script>

<ModalBase {open} onRequestClose={handleClose} maxWidth="lg">
    <div class="space-y-4">
        <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">Add New Currency Pair</h2>
        {#if error}
            <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-sm text-red-600 dark:text-red-400">
                {error}
            </div>
        {/if}

        <!-- Currency selection -->
        <div class="flex items-center gap-3">
            <div class="flex-1">
                <!-- svelte-ignore a11y_label_has_associated_control -->
                <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Base Currency
                    <input type="text" bind:value={baseCurrency} placeholder="EUR" maxlength="3"
                        class="mt-1 block w-full px-3 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 uppercase focus:ring-1 focus:ring-libre-green" />
                </label>
            </div>
            <span class="text-gray-400 dark:text-gray-500 text-lg mt-4">→</span>
            <div class="flex-1">
                <!-- svelte-ignore a11y_label_has_associated_control -->
                <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Quote Currency
                    <input type="text" bind:value={quoteCurrency} placeholder="USD" maxlength="3"
                        class="mt-1 block w-full px-3 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 uppercase focus:ring-1 focus:ring-libre-green" />
                </label>
            </div>
        </div>

        <!-- Provider configuration -->
        <div>
            <h4 class="text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Provider Priority</h4>
            {#if providerEntries.length > 0}
                <div class="space-y-2 mb-3">
                    {#each providerEntries as prov, i}
                        <div class="flex items-center gap-2 p-2 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
                            <GripVertical size={14} class="text-gray-300 dark:text-gray-600" />
                            <span class="flex-1 text-sm text-gray-700 dark:text-gray-200">{getProviderName(prov.code)}</span>
                            <span class="text-xs font-mono px-1.5 py-0.5 rounded {i === 0 ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400' : 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400'}">
                                Priority {prov.priority}
                            </span>
                            <button class="p-1 text-gray-400 hover:text-red-500" on:click={() => removeProvider(prov.code)}>
                                <Trash2 size={14} />
                            </button>
                        </div>
                    {/each}
                </div>
            {/if}

            {#if unusedProviders.length > 0}
                <div class="flex items-center gap-2">
                    <select bind:value={newProviderCode}
                        class="flex-1 text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 px-2.5 py-1.5">
                        <option value="">Add Provider...</option>
                        {#each unusedProviders as prov}
                            <option value={prov.code}>{prov.name} ({prov.code})</option>
                        {/each}
                    </select>
                    <button class="p-1.5 text-libre-green hover:bg-libre-green/10 rounded-lg" on:click={addProvider} disabled={!newProviderCode}>
                        <Plus size={16} />
                    </button>
                </div>
            {/if}
        </div>

        <!-- Actions -->
        <div class="flex justify-end gap-2 pt-2 border-t border-gray-100 dark:border-slate-700">
            <button class="px-4 py-2 text-sm bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-slate-500"
                on:click={handleClose}>
                Cancel
            </button>
            <button class="px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 disabled:opacity-50"
                on:click={handleSave} disabled={!isValid || saving}>
                {saving ? 'Saving...' : 'Save Configuration'}
            </button>
        </div>
    </div>
</ModalBase>
