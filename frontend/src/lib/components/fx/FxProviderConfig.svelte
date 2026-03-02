<!--
  FxProviderConfig — Provider configuration panel for a currency pair.

  Shows the list of configured providers with priority badges,
  allows add/delete/reorder, and has the "Intermediate Route" placeholder.
-->
<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import {_} from '$lib/i18n';
    import {GripVertical, Plus, Trash2} from 'lucide-svelte';

    // =========================================================================
    // Types
    // =========================================================================

    interface ProviderEntry {
        providerCode: string;
        priority: number;
    }

    interface AvailableProvider {
        code: string;
        name: string;
    }

    // =========================================================================
    // Props
    // =========================================================================

    export let providers: ProviderEntry[] = [];
    export let availableProviders: AvailableProvider[] = [];
    export let readonly: boolean = false;

    const dispatch = createEventDispatcher<{
        save: ProviderEntry[];
        addProvider: {providerCode: string; priority: number};
        removeProvider: {providerCode: string};
    }>();

    // =========================================================================
    // State
    // =========================================================================

    let addingProvider = false;
    let newProviderCode = '';

    // =========================================================================
    // Derived
    // =========================================================================

    $: usedCodes = new Set(providers.map(p => p.providerCode));
    $: unusedProviders = availableProviders.filter(p => !usedCodes.has(p.code));

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleAdd() {
        if (!newProviderCode) return;
        const nextPriority = providers.length > 0 ? Math.max(...providers.map(p => p.priority)) + 1 : 1;
        dispatch('addProvider', {providerCode: newProviderCode, priority: nextPriority});
        newProviderCode = '';
        addingProvider = false;
    }

    function handleRemove(code: string) {
        dispatch('removeProvider', {providerCode: code});
    }

    function getProviderName(code: string): string {
        return availableProviders.find(p => p.code === code)?.name || code;
    }
</script>

<div class="space-y-3">
    <div class="flex items-center justify-between">
        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-200">Provider Configuration</h3>
        {#if !readonly && unusedProviders.length > 0}
            <button
                class="flex items-center gap-1 text-xs text-libre-green hover:text-libre-green/80 transition-colors"
                on:click={() => addingProvider = !addingProvider}
            >
                <Plus size={14} />
                Add Provider
            </button>
        {/if}
    </div>

    <!-- Provider list -->
    {#if providers.length === 0}
        <p class="text-sm text-gray-400 dark:text-gray-500 py-2">No providers configured for this pair.</p>
    {:else}
        <div class="space-y-2">
            {#each providers as prov, i}
                <div class="flex items-center gap-3 p-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg group">
                    <!-- Drag handle (visual only for now) -->
                    <div class="text-gray-300 dark:text-gray-600 cursor-grab">
                        <GripVertical size={16} />
                    </div>

                    <!-- Provider info -->
                    <div class="flex items-center gap-2 flex-1 min-w-0">
                        <span class="font-medium text-sm text-gray-700 dark:text-gray-200 truncate">
                            {getProviderName(prov.providerCode)}
                        </span>
                        <span class="text-xs font-mono px-2 py-0.5 rounded flex-shrink-0
                            {i === 0
                                ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400'
                                : 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400'}">
                            Priority {prov.priority}{i === 0 ? ' (Primary)' : ' (Fallback)'}
                        </span>
                    </div>

                    <!-- Delete button -->
                    {#if !readonly}
                        <button
                            class="p-1 rounded-md opacity-0 group-hover:opacity-100 hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 transition-all"
                            on:click={() => handleRemove(prov.providerCode)}
                            title="Remove provider"
                        >
                            <Trash2 size={14} />
                        </button>
                    {/if}
                </div>
            {/each}
        </div>
    {/if}

    <!-- Add provider form -->
    {#if addingProvider && !readonly}
        <div class="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-900/10 rounded-lg border border-blue-200 dark:border-blue-800">
            <select
                bind:value={newProviderCode}
                class="flex-1 text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 px-2.5 py-1.5 focus:ring-1 focus:ring-libre-green"
            >
                <option value="">Select provider...</option>
                {#each unusedProviders as prov}
                    <option value={prov.code}>{prov.name} ({prov.code})</option>
                {/each}
            </select>
            <button
                class="px-3 py-1.5 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50"
                on:click={handleAdd}
                disabled={!newProviderCode}
            >
                Add
            </button>
            <button
                class="px-3 py-1.5 text-sm bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-slate-500 transition-colors"
                on:click={() => { addingProvider = false; newProviderCode = ''; }}
            >
                Cancel
            </button>
        </div>
    {/if}

    <!-- Intermediate Route placeholder -->
    <div class="p-3 bg-gray-50 dark:bg-slate-700/30 rounded-lg border border-dashed border-gray-300 dark:border-slate-600">
        <div class="flex items-center gap-2 text-sm text-gray-400 dark:text-gray-500">
            <span>🔒</span>
            <span>Intermediate Route (e.g., USD → EUR → RON) — Coming Soon</span>
        </div>
    </div>
</div>

