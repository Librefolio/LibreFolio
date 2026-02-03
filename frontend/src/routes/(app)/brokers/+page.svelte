<script lang="ts">
    import {onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {Briefcase, Plus, RefreshCw} from 'lucide-svelte';
    import BrokerCard from '$lib/components/brokers/BrokerCard.svelte';
    import BrokerModal from '$lib/components/brokers/BrokerModal.svelte';
    import DeleteBrokerDialog from '$lib/components/brokers/DeleteBrokerDialog.svelte';
    import type {Broker, BrokerSummary} from '$lib/types';

    // State
    let brokers: Broker[] = [];
    let loading = true;
    let error: string | null = null;

    // Modal state
    let modalOpen = false;
    let modalMode: 'create' | 'edit' = 'create';
    let editingBrokerId: number | null = null;
    let editingBrokerData: Partial<Broker> = {};

    // Delete dialog state
    let deleteDialogOpen = false;
    let deletingBroker: { id: number; name: string } | null = null;
    let deletingTransactionCount = 0;
    let deleteLoading = false;

    // Load brokers on mount
    onMount(async () => {
        await loadBrokers();
    });

    async function loadBrokers() {
        loading = true;
        error = null;
        try {
            // Load all brokers with their summaries
            const basicBrokers = await zodiosApi.list_brokers_api_v1_brokers_get();

            // For each broker, get the summary to get cash_balances and holdings
            const summaries = await Promise.all(
                basicBrokers.map(b => zodiosApi.get_broker_summary_api_v1_brokers__broker_id__summary_get({params: {broker_id: b.id}}).catch(() => null))
            );

            brokers = basicBrokers.map((b, i) => {
                const summary = summaries[i];
                return {
                    ...b,
                    cash_balances: summary?.cash_balances ?? [],
                    holdings: summary?.holdings ?? []
                } as Broker;
            });
        } catch (e) {
            console.error('Failed to load brokers:', e);
            error = 'Failed to load brokers';
        } finally {
            loading = false;
        }
    }

    function openCreateModal() {
        modalMode = 'create';
        editingBrokerId = null;
        editingBrokerData = {};
        modalOpen = true;
    }

    function handleEdit(event: CustomEvent<{ id: number }>) {
        const broker = brokers.find(b => b.id === event.detail.id);
        if (broker) {
            modalMode = 'edit';
            editingBrokerId = broker.id;
            editingBrokerData = {
                name: broker.name,
                description: broker.description,
                portal_url: broker.portal_url,
                icon_url: broker.icon_url,
                default_import_plugin: broker.default_import_plugin,
                allow_cash_overdraft: broker.allow_cash_overdraft,
                allow_asset_shorting: broker.allow_asset_shorting,
                is_active: broker.is_active,
                opened_at: broker.opened_at
            };
            modalOpen = true;
        }
    }

    function handleDelete(event: CustomEvent<{ id: number; name: string }>) {
        deletingBroker = event.detail;
        deletingTransactionCount = 0; // We'd need an API call to get actual count
        deleteDialogOpen = true;
    }

    async function confirmDelete(event: CustomEvent<{ force: boolean }>) {
        if (!deletingBroker) return;

        deleteLoading = true;
        try {
            await zodiosApi.delete_brokers_api_v1_brokers_delete(undefined, {queries: {ids: [deletingBroker.id], force: event.detail.force}});
            deleteDialogOpen = false;
            deletingBroker = null;
            await loadBrokers();
        } catch (e) {
            console.error('Failed to delete broker:', e);
        } finally {
            deleteLoading = false;
        }
    }

    function handleModalClose() {
        modalOpen = false;
    }

    async function handleCreated() {
        await loadBrokers();
    }

    async function handleUpdated() {
        await loadBrokers();
    }
</script>

<div class="space-y-6" data-testid="brokers-page">
    <!-- Header with actions -->
    <div class="flex items-center justify-between">
        <div>
            <h2 class="text-lg font-semibold text-gray-700">{$_('brokers.title')}</h2>
            <p class="text-gray-500 text-sm">{$_('brokers.subtitle')}</p>
        </div>
        <div class="flex items-center space-x-2">
            <button
                    on:click={loadBrokers}
                    disabled={loading}
                    data-testid="brokers-refresh"
                    class="p-2 text-gray-500 hover:text-libre-green hover:bg-libre-green/10 rounded-lg transition-colors disabled:opacity-50"
                    title="Refresh"
            >
                <RefreshCw size={18} class={loading ? 'animate-spin' : ''}/>
            </button>
            <button
                    on:click={openCreateModal}
                    data-testid="add-broker-button"
                    class="flex items-center justify-center gap-2 px-3 sm:px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-all"
            >
                <Plus size={18}/>
                <span class="hidden sm:inline">{$_('brokers.addBroker')}</span>
            </button>
        </div>
    </div>

    <!-- Content -->
    {#if loading && brokers.length === 0}
        <!-- Loading state -->
        <div class="bg-white rounded-xl shadow-sm p-12 text-center border border-gray-100">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-libre-green/10 rounded-full mb-4">
                <RefreshCw class="text-libre-green animate-spin" size={32}/>
            </div>
            <p class="text-gray-500">{$_('common.loading')}</p>
        </div>
    {:else if error}
        <!-- Error state -->
        <div class="bg-white rounded-xl shadow-sm p-12 text-center border border-red-100">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
                <Briefcase class="text-red-600" size={32}/>
            </div>
            <h3 class="text-lg font-semibold text-gray-700 mb-2">{$_('common.error')}</h3>
            <p class="text-gray-500 mb-4">{error}</p>
            <button
                    on:click={loadBrokers}
                    class="px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors"
            >
                {$_('error.tryAgain')}
            </button>
        </div>
    {:else if brokers.length === 0}
        <!-- Empty state -->
        <div class="bg-white rounded-xl shadow-sm p-12 text-center border border-gray-100">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
                <Briefcase class="text-blue-600" size={32}/>
            </div>
            <h3 class="text-lg font-semibold text-gray-700 mb-2">{$_('brokers.noBrokers')}</h3>
            <p class="text-gray-500 mb-4">{$_('brokers.noBrokersMessage')}</p>
            <button
                    on:click={openCreateModal}
                    class="inline-flex items-center space-x-2 px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-all"
            >
                <Plus size={18}/>
                <span>{$_('brokers.addBroker')}</span>
            </button>
        </div>
    {:else}
        <!-- Broker grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {#each brokers as broker (broker.id)}
                <BrokerCard
                        {broker}
                        on:edit={handleEdit}
                        on:delete={handleDelete}
                />
            {/each}
        </div>
    {/if}
</div>

<!-- Add/Edit Modal -->
<BrokerModal
        isOpen={modalOpen}
        mode={modalMode}
        brokerId={editingBrokerId}
        initialData={editingBrokerData}
        on:close={handleModalClose}
        on:created={handleCreated}
        on:updated={handleUpdated}
/>

<!-- Delete Confirmation Dialog -->
<DeleteBrokerDialog
        isOpen={deleteDialogOpen}
        brokerName={deletingBroker?.name ?? ''}
        transactionCount={deletingTransactionCount}
        loading={deleteLoading}
        on:confirm={confirmDelete}
        on:cancel={() => { deleteDialogOpen = false; deletingBroker = null; }}
/>
