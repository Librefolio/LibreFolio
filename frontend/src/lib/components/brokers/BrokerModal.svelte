<script lang="ts">
    /**
     * BrokerModal - Modal wrapper for broker create/edit form
     */
    import {createEventDispatcher} from 'svelte';
    import {_} from '$lib/i18n';
    import {X} from 'lucide-svelte';
    import BrokerForm from './BrokerForm.svelte';

    const dispatch = createEventDispatcher<{
        close: void;
        created: { id: number };
        updated: { id: number };
    }>();

    // Props
    export let isOpen = false;
    export let mode: 'create' | 'edit' = 'create';
    export let brokerId: number | null = null;
    export let initialData: {
        name?: string;
        description?: string | null;
        portal_url?: string | null;
        icon_url?: string | null;
        default_import_plugin?: string | null;
        allow_cash_overdraft?: boolean;
        allow_asset_shorting?: boolean;
        is_active?: boolean;
        opened_at?: string | null;
    } = {};

    import {api} from '$lib/api';

    let loading = false;
    let error: string | null = null;
    let formTouched = false;

    // Track if form has been modified
    function handleFormChange() {
        formTouched = true;
    }

    async function handleSubmit(event: CustomEvent<{
        name: string;
        description?: string;
        portal_url?: string;
        icon_url?: string;
        default_import_plugin?: string;
        allow_cash_overdraft: boolean;
        allow_asset_shorting: boolean;
        is_active: boolean;
        opened_at?: string;
        initial_balances?: Array<{ code: string; amount: number }>;
    }>) {
        loading = true;
        error = null;

        try {
            if (mode === 'create') {
                // Create broker
                const response = await api.post<{
                    total: number;
                    succeeded: number;
                    failed: number;
                    results: Array<{ success: boolean; broker_id?: number; error?: string }>
                }>('/brokers', [event.detail]);

                if (response.results[0]?.success && response.results[0].broker_id) {
                    formTouched = false;
                    dispatch('created', {id: response.results[0].broker_id});
                    dispatch('close');
                } else {
                    error = response.results[0]?.error ?? $_('brokers.createFailed');
                }
            } else if (brokerId) {
                // Update broker
                await api.patch(`/brokers/${brokerId}`, {
                    name: event.detail.name,
                    description: event.detail.description,
                    portal_url: event.detail.portal_url,
                    icon_url: event.detail.icon_url,
                    default_import_plugin: event.detail.default_import_plugin,
                    allow_cash_overdraft: event.detail.allow_cash_overdraft,
                    allow_asset_shorting: event.detail.allow_asset_shorting,
                    is_active: event.detail.is_active,
                    opened_at: event.detail.opened_at
                });

                formTouched = false;
                dispatch('updated', {id: brokerId});
                dispatch('close');
            }
        } catch (e) {
            console.error('Broker operation failed:', e);
            error = mode === 'create' ? $_('brokers.createFailed') : $_('brokers.updateFailed');
        } finally {
            loading = false;
        }
    }

    function handleClose() {
        if (loading) return;

        if (formTouched) {
            if (confirm($_('brokers.unsavedChanges'))) {
                formTouched = false;
                dispatch('close');
            }
        } else {
            dispatch('close');
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape' && !loading) {
            handleClose();
        }
    }
</script>

{#if isOpen}
    <!-- Backdrop -->
    <div
            class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
            on:click={handleClose}
            on:keydown={handleKeydown}
            role="dialog"
            aria-modal="true"
            tabindex="-1"
    >
        <!-- Modal -->
        <div
                class="bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] flex flex-col"
                role="dialog"
                tabindex="-1"
                on:click|stopPropagation
                on:keydown|stopPropagation
                on:input={handleFormChange}
        >
            <!-- Header (sticky top) -->
            <div class="flex items-center justify-between p-4 border-b border-gray-100 dark:border-slate-700 shrink-0">
                <h2 class="text-xl font-semibold text-gray-800 dark:text-gray-100">
                    {mode === 'create' ? $_('brokers.addBroker') : $_('brokers.editBroker')}
                </h2>
                <button
                        on:click={handleClose}
                        disabled={loading}
                        class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50"
                >
                    <X size={20}/>
                </button>
            </div>

            <!-- Error message -->
            {#if error}
                <div class="mx-4 mt-4 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm shrink-0">
                    {error}
                </div>
            {/if}

            <!-- Form (scrollable area with sticky footer inside) -->
            <div class="overflow-y-auto flex-1 min-h-0 scrollbar-hidden">
                <div class="p-4 pb-0">
                    <BrokerForm
                            {mode}
                            {initialData}
                            {loading}
                            on:submit={handleSubmit}
                            on:cancel={handleClose}
                    />
                </div>
            </div>
        </div>
    </div>
{/if}
