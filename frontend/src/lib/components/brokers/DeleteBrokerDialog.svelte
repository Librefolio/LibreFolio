<script lang="ts">
    /**
     * DeleteBrokerDialog - Confirmation dialog for broker deletion
     */
    import {createEventDispatcher} from 'svelte';
    import {_} from '$lib/i18n';
    import {AlertTriangle, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';

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
</script>

<ModalBase
    open={isOpen}
    zIndex={60}
    maxWidth="md"
    closeOnEscape={!loading}
    closeOnBackdropClick={!loading}
    onRequestClose={handleCancel}
    testId="delete-broker-dialog"
>
            <!-- Header -->
            <div class="flex items-center justify-between p-4 border-b border-gray-100 dark:border-slate-700">
                <div class="flex items-center space-x-2 text-red-600">
                    <AlertTriangle size={24}/>
                    <h2 class="text-xl font-semibold">{$_('brokers.deleteBroker')}</h2>
                </div>
                <button
                        on:click={handleCancel}
                        disabled={loading}
                        class="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50"
                >
                    <X size={20}/>
                </button>
            </div>

            <!-- Content -->
            <div class="p-4">
                {#if hasTransactions}
                    <p class="text-gray-700 dark:text-gray-300 mb-4">
                        {$_('brokers.confirmDeleteWithTransactions', {values: {count: transactionCount}})}
                    </p>
                    <div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3 text-amber-800 dark:text-amber-300 text-sm">
                        <strong>{brokerName}</strong> has {transactionCount} transaction(s).
                    </div>
                {:else}
                    <p class="text-gray-700 dark:text-gray-300">
                        {$_('brokers.confirmDelete')}
                    </p>
                    <p class="mt-2 font-medium text-gray-800 dark:text-gray-200">{brokerName}</p>
                {/if}
            </div>

            <!-- Actions -->
            <div class="flex items-center justify-end space-x-3 p-4 border-t border-gray-100 dark:border-slate-700">
                <button
                        on:click={handleCancel}
                        disabled={loading}
                        class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                        data-testid="delete-broker-cancel"
                >
                    {$_('common.cancel')}
                </button>
                {#if hasTransactions}
                    <button
                            on:click={() => handleConfirm(true)}
                            disabled={loading}
                            class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                            data-testid="delete-broker-confirm"
                    >
                        {loading ? $_('common.loading') : $_('brokers.forceDelete')}
                    </button>
                {:else}
                    <button
                            on:click={() => handleConfirm(false)}
                            disabled={loading}
                            class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                            data-testid="delete-broker-confirm"
                    >
                        {loading ? $_('common.loading') : $_('common.delete')}
                    </button>
                {/if}
            </div>
</ModalBase>
