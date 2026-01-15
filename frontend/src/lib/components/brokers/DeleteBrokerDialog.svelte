<script lang="ts">
    /**
     * DeleteBrokerDialog - Confirmation dialog for broker deletion
     */
    import {createEventDispatcher} from 'svelte';
    import {_} from '$lib/i18n';
    import {AlertTriangle, X} from 'lucide-svelte';

    const dispatch = createEventDispatcher<{
        confirm: { force: boolean };
        cancel: void;
    }>();

    // Props
    export let isOpen = false;
    export let brokerName = '';
    export let transactionCount = 0;
    export let loading = false;

    $: hasTransactions = transactionCount > 0;

    function handleConfirm(force: boolean) {
        dispatch('confirm', {force});
    }

    function handleCancel() {
        if (!loading) {
            dispatch('cancel');
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape' && !loading) {
            handleCancel();
        }
    }
</script>

{#if isOpen}
    <!-- Backdrop -->
    <div
            class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
            on:click={handleCancel}
            on:keydown={handleKeydown}
            role="dialog"
            aria-modal="true"
            tabindex="-1"
    >
        <!-- Modal -->
        <div
                class="bg-white rounded-2xl shadow-xl w-full max-w-md"
                role="dialog"
                tabindex="-1"
                on:click|stopPropagation
                on:click|stopPropagation
                on:keydown|stopPropagation
        >
            <!-- Header -->
            <div class="flex items-center justify-between p-4 border-b border-gray-100">
                <div class="flex items-center space-x-2 text-red-600">
                    <AlertTriangle size={24}/>
                    <h2 class="text-xl font-semibold">{$_('brokers.deleteBroker')}</h2>
                </div>
                <button
                        on:click={handleCancel}
                        disabled={loading}
                        class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
                >
                    <X size={20}/>
                </button>
            </div>

            <!-- Content -->
            <div class="p-4">
                {#if hasTransactions}
                    <p class="text-gray-700 mb-4">
                        {$_('brokers.confirmDeleteWithTransactions', {values: {count: transactionCount}})}
                    </p>
                    <div class="bg-amber-50 border border-amber-200 rounded-lg p-3 text-amber-800 text-sm">
                        <strong>{brokerName}</strong> has {transactionCount} transaction(s).
                    </div>
                {:else}
                    <p class="text-gray-700">
                        {$_('brokers.confirmDelete')}
                    </p>
                    <p class="mt-2 font-medium text-gray-800">{brokerName}</p>
                {/if}
            </div>

            <!-- Actions -->
            <div class="flex items-center justify-end space-x-3 p-4 border-t border-gray-100">
                <button
                        on:click={handleCancel}
                        disabled={loading}
                        class="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                >
                    {$_('common.cancel')}
                </button>
                {#if hasTransactions}
                    <button
                            on:click={() => handleConfirm(true)}
                            disabled={loading}
                            class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                    >
                        {loading ? $_('common.loading') : $_('brokers.forceDelete')}
                    </button>
                {:else}
                    <button
                            on:click={() => handleConfirm(false)}
                            disabled={loading}
                            class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                    >
                        {loading ? $_('common.loading') : $_('common.delete')}
                    </button>
                {/if}
            </div>
        </div>
    </div>
{/if}

