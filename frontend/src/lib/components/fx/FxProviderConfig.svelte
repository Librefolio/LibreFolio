<!--
  FxProviderConfig — Provider configuration panel for a currency pair.

  Shows the list of configured providers with priority badges,
  allows add/delete/reorder via OrderableList, and has save/cancel when changed.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {Plus, Trash2, Save, Undo2} from 'lucide-svelte';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';

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

    interface Props {
        providers?: ProviderEntry[];
        availableProviders?: AvailableProvider[];
        readonly?: boolean;
        onSave?: (providers: ProviderEntry[]) => void;
        onAddProvider?: (detail: {providerCode: string; priority: number}) => void;
        onRemoveProvider?: (detail: {providerCode: string}) => void;
    }

    let {
        providers = $bindable([]),
        availableProviders = [],
        readonly: isReadonly = false,
        onSave,
        onAddProvider,
        onRemoveProvider,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let addingProvider = $state(false);
    let newProviderCode = $state('');
    let hasChanges = $state(false);
    let originalOrder: string[] = $state([]);

    // Track original order for change detection
    $effect(() => {
        originalOrder = providers.map(p => p.providerCode);
        hasChanges = false;
    });

    // =========================================================================
    // Derived
    // =========================================================================

    let usedCodes = $derived(new Set(providers.map(p => p.providerCode)));
    let unusedProviders = $derived(availableProviders.filter(p => !usedCodes.has(p.code)));

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleReorder(newItems: ProviderEntry[]) {
        // Update priorities based on new order
        providers = newItems.map((item, idx) => ({
            ...item,
            priority: idx + 1,
        }));
        // Detect if order changed
        const currentOrder = providers.map(p => p.providerCode);
        hasChanges = JSON.stringify(currentOrder) !== JSON.stringify(originalOrder);
    }

    function handleAdd() {
        if (!newProviderCode) return;
        const nextPriority = providers.length > 0 ? Math.max(...providers.map(p => p.priority)) + 1 : 1;
        onAddProvider?.({providerCode: newProviderCode, priority: nextPriority});
        newProviderCode = '';
        addingProvider = false;
    }

    function handleRemove(code: string) {
        onRemoveProvider?.({providerCode: code});
    }

    function handleSave() {
        onSave?.(providers);
        originalOrder = providers.map(p => p.providerCode);
        hasChanges = false;
    }

    function handleRevert() {
        // Re-sort providers back to original order
        const orderMap = new Map(originalOrder.map((code, idx) => [code, idx]));
        providers = [...providers].sort((a, b) =>
            (orderMap.get(a.providerCode) ?? 999) - (orderMap.get(b.providerCode) ?? 999)
        ).map((p, idx) => ({...p, priority: idx + 1}));
        hasChanges = false;
    }

    function getProviderName(code: string): string {
        return availableProviders.find(p => p.code === code)?.name || code;
    }

    function providerKey(prov: ProviderEntry): string {
        return prov.providerCode;
    }
</script>

<div class="space-y-3">
    <div class="flex items-center justify-between">
        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-200">Provider Configuration</h3>
        <div class="flex items-center gap-2">
            {#if hasChanges && !isReadonly}
                <button
                    class="flex items-center gap-1 text-xs px-2 py-1 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors"
                    onclick={handleSave}
                >
                    <Save size={12} />
                    Save Order
                </button>
                <button
                    class="flex items-center gap-1 text-xs px-2 py-1 bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-slate-500 transition-colors"
                    onclick={handleRevert}
                >
                    <Undo2 size={12} />
                    Revert
                </button>
            {/if}
            {#if !isReadonly && unusedProviders.length > 0}
                <button
                    class="flex items-center gap-1 text-xs text-libre-green hover:text-libre-green/80 transition-colors"
                    onclick={() => addingProvider = !addingProvider}
                >
                    <Plus size={14} />
                    Add Provider
                </button>
            {/if}
        </div>
    </div>

    <!-- Provider list (orderable) -->
    {#if providers.length === 0}
        <p class="text-sm text-gray-400 dark:text-gray-500 py-2">No providers configured for this pair.</p>
    {:else}
        <OrderableList
            items={providers}
            keyFn={providerKey}
            onReorder={handleReorder}
            disabled={isReadonly}
        >
            {#snippet children({ item, index })}
                <div class="flex items-center gap-2">
                    <span class="font-medium text-sm text-gray-700 dark:text-gray-200 truncate">
                        {getProviderName(item.providerCode)}
                    </span>
                    <span class="text-xs font-mono px-2 py-0.5 rounded flex-shrink-0
                        {index === 0
                            ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400'
                            : 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400'}">
                        Priority {index + 1}{index === 0 ? ` (${$_('fx.provider.primary')})` : ` (${$_('fx.provider.fallback')})`}
                    </span>
                    {#if !isReadonly}
                        <button
                            class="p-1 rounded-md opacity-0 group-hover:opacity-100 hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 transition-all ml-auto"
                            onclick={() => handleRemove(item.providerCode)}
                            title="Remove provider"
                        >
                            <Trash2 size={14} />
                        </button>
                    {/if}
                </div>
            {/snippet}
        </OrderableList>
    {/if}

    <!-- Add provider form -->
    {#if addingProvider && !isReadonly}
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
                onclick={handleAdd}
                disabled={!newProviderCode}
            >
                Add
            </button>
            <button
                class="px-3 py-1.5 text-sm bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-slate-500 transition-colors"
                onclick={() => { addingProvider = false; newProviderCode = ''; }}
            >
                Cancel
            </button>
        </div>
    {/if}

    <!-- Intermediate Route placeholder -->
    <div class="p-3 bg-gray-50 dark:bg-slate-700/30 rounded-lg border border-dashed border-gray-300 dark:border-slate-600">
        <div class="flex items-center gap-2 text-sm text-gray-400 dark:text-gray-500">
            <span>🔒</span>
            <span>{$_('fx.addPair.intermediateRouteComingSoon')}</span>
        </div>
    </div>
</div>

