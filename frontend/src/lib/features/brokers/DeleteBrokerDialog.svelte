<script lang="ts">
    /**
     * DeleteBrokerDialog - Confirmation dialog for broker deletion
     */
    import {createEventDispatcher} from 'svelte';
    import {_} from '$lib/i18n';
    import {AlertTriangle, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';

    type DispatchEvents = {
        confirm: {force: boolean};
        cancel: void;
        viewTransactions: void;
    };
    const dispatch = createEventDispatcher<DispatchEvents>();

    // Props
    export let isOpen = false;
    export let brokerName = '';
    export let transactionCount = 0;
    export let blocked = false;
    export let loading = false;

    $: isBlocked = blocked && transactionCount > 0;

    function handleConfirm(force: boolean) {
        dispatch('confirm', {force});
    }

    function handleCancel() {
        if (!loading) {
            dispatch('cancel');
        }
    }

    function handleViewTransactions() {
        if (!loading) {
            dispatch('viewTransactions');
        }
    }
</script>

<ModalBase closeOnBackdropClick={!loading} closeOnEscape={!loading} maxWidth="md" onRequestClose={handleCancel} open={isOpen} testId="delete-broker-dialog" zIndex={60}>
    <!-- Header -->
    <div class="flex items-center justify-between p-4 border-b border-lf-subtle">
        <div class="flex items-center space-x-2 text-lf-danger">
            <AlertTriangle size={24} />
            <h2 class="text-xl font-semibold">{isBlocked ? $_('brokers.deleteBlockedTitle') : $_('brokers.deleteBroker')}</h2>
        </div>
        <button class="p-2 text-lf-muted hover:text-lf-secondary hover:bg-lf-hover rounded-lg transition-colors disabled:opacity-50" disabled={loading} on:click={handleCancel}>
            <X size={20} />
        </button>
    </div>

    <!-- Content -->
    <div class="p-4">
        {#if isBlocked}
            <p class="text-lf-secondary mb-4">
                {$_('brokers.deleteBlockedMessage', {values: {count: transactionCount}})}
            </p>
            <InfoBanner variant="warning" showIcon={false}>
                <span class="text-sm">{$_('brokers.confirmDeleteWithTransactions', {values: {n: transactionCount}})}</span>
            </InfoBanner>
        {:else}
            <p class="text-lf-secondary">
                {$_('brokers.confirmDelete')}
            </p>
            <p class="mt-2 font-medium text-lf-primary">{brokerName}</p>
        {/if}
    </div>

    <!-- Actions -->
    <div class="flex items-center justify-end space-x-3 p-4 border-t border-lf-subtle">
        <button class="px-4 py-2 text-lf-secondary hover:bg-lf-hover rounded-lg transition-colors" data-testid="delete-broker-cancel" disabled={loading} on:click={handleCancel}>
            {$_('common.cancel')}
        </button>
        {#if isBlocked}
            <button class="px-4 py-2 text-lf-link hover:bg-lf-hover rounded-lg transition-colors disabled:opacity-50" data-testid="delete-broker-view-transactions" disabled={loading} on:click={handleViewTransactions}>
                {$_('brokers.goToTransactions')}
            </button>
            <button on:click={() => handleConfirm(true)} disabled={loading} class="px-4 py-2 bg-lf-danger-solid text-lf-on-danger-solid rounded-lg hover:bg-lf-danger-hover transition-colors disabled:opacity-50" data-testid="delete-broker-force-delete">
                {loading ? $_('common.loading') : $_('brokers.forceCascadeDelete')}
            </button>
        {:else}
            <button on:click={() => handleConfirm(false)} disabled={loading} class="px-4 py-2 bg-lf-danger-solid text-lf-on-danger-solid rounded-lg hover:bg-lf-danger-hover transition-colors disabled:opacity-50" data-testid="delete-broker-confirm">
                {loading ? $_('common.loading') : $_('common.delete')}
            </button>
        {/if}
    </div>
</ModalBase>
