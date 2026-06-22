<script lang="ts">
    /**
     * BrokerCard - Display a broker with cash balances and quick actions
     */
    import {createEventDispatcher} from 'svelte';
    import {goto} from '$app/navigation';
    import {_} from '$lib/i18n';
    import {Crown, ExternalLink, Eye, Pencil, Trash2, Wallet} from 'lucide-svelte';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';

    type _DispatchEvents = {
        edit: {id: number};
        delete: {id: number; name: string};
    };
    const dispatch = createEventDispatcher();

    // Props
    export let broker: {
        id: number;
        name: string;
        description?: string | null;
        portal_url?: string | null;
        icon_url?: string | null;
        default_import_plugin?: string | null;
        allow_cash_overdraft: boolean;
        allow_asset_shorting: boolean;
        is_active?: boolean;
        user_role?: string | null;
        cash_balances?: Array<{code: string; amount: number; symbol?: string}>;
        holdings?: Array<{asset_id: number}>;
    };

    // Format currency amount
    function formatAmount(amount: number, code: string): string {
        return new Intl.NumberFormat(undefined, {
            style: 'currency',
            currency: code,
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(amount);
    }

    function handleCardClick() {
        goto(`/brokers/${broker.id}`);
    }

    function handleEdit(event: MouseEvent) {
        event.stopPropagation();
        dispatch('edit', {id: broker.id});
    }

    function handleDelete(event: MouseEvent) {
        event.stopPropagation();
        dispatch('delete', {id: broker.id, name: broker.name});
    }

    function handlePortalClick(event: MouseEvent) {
        event.stopPropagation();
    }
</script>

<div
    class="w-full text-left bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 overflow-hidden cursor-pointer
           transition-all duration-200 hover:shadow-lg hover:border-libre-green/30 hover:bg-libre-green/5 dark:hover:bg-slate-700
           focus:outline-none focus:ring-2 focus:ring-libre-green focus:ring-offset-2"
    class:opacity-60={broker.is_active === false}
    data-testid="broker-card-{broker.id}"
    on:click={handleCardClick}
    on:keydown={(e) => e.key === 'Enter' && handleCardClick()}
    role="button"
    tabindex="0"
>
    <!-- Header -->
    <div class="p-4 border-b border-gray-100 dark:border-slate-700">
        <div class="flex items-start justify-between">
            <div class="flex items-center gap-3 flex-1 min-w-0">
                <!-- Broker Icon -->
                <BrokerIcon altText={broker.name} iconUrl={broker.icon_url} pluginCode={broker.default_import_plugin} portalUrl={broker.portal_url} size="md" />

                <div class="min-w-0">
                    <div class="flex items-center gap-2">
                        {#if broker.user_role}
                            <span
                                class="inline-flex items-center justify-center w-5 h-5 rounded-full flex-shrink-0
                                {broker.user_role === 'OWNER'
                                    ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
                                    : broker.user_role === 'EDITOR'
                                      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                                      : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'}"
                                title={$_(broker.user_role === 'OWNER' ? 'brokers.sharing.roleOwnerShort' : broker.user_role === 'EDITOR' ? 'brokers.sharing.roleEditorShort' : 'brokers.sharing.roleViewerShort')}
                            >
                                {#if broker.user_role === 'OWNER'}<Crown size={11} />{:else if broker.user_role === 'EDITOR'}<Pencil size={11} />{:else}<Eye size={11} />{/if}
                            </span>
                        {/if}
                        <h3 class="text-lg font-semibold text-gray-800 dark:text-gray-100 truncate">{broker.name}</h3>
                    </div>
                    {#if broker.description}
                        <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-1">{broker.description}</p>
                    {/if}
                </div>
            </div>

            <!-- Actions (Edit & Delete only) -->
            <div class="flex items-center space-x-1 ml-2">
                <button class="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors" data-testid="broker-edit-{broker.id}" on:click={handleEdit} title={$_('common.edit')}>
                    <Pencil size={18} />
                </button>
                <button class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors" data-testid="broker-delete-{broker.id}" on:click={handleDelete} title={$_('common.delete')}>
                    <Trash2 size={18} />
                </button>
            </div>
        </div>

        <!-- Portal Link -->
        {#if broker.portal_url}
            <a href={broker.portal_url} target="_blank" rel="noopener noreferrer" on:click={handlePortalClick} class="inline-flex items-center space-x-1 text-sm text-libre-green hover:underline mt-2">
                <span>{$_('brokers.openPortal')}</span>
                <ExternalLink size={14} />
            </a>
        {/if}
    </div>

    <!-- Cash Balances -->
    <div class="p-4">
        <div class="flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400 mb-3">
            <Wallet size={16} />
            <span>{$_('brokers.cashBalances')}</span>
        </div>

        {#if broker.cash_balances && broker.cash_balances.length > 0}
            <div class="grid grid-cols-2 gap-2">
                {#each broker.cash_balances as balance}
                    <div class="flex items-center space-x-2 px-3 py-2 bg-gray-50 dark:bg-slate-700 rounded-lg">
                        {#if balance.symbol && balance.symbol !== balance.code}
                            <span class="text-lg w-6 text-center">{balance.symbol}</span>
                        {/if}
                        <div class="flex-1 min-w-0">
                            <div class="font-medium text-gray-800 dark:text-gray-100 truncate">
                                {formatAmount(balance.amount, balance.code)}
                            </div>
                            <div class="text-xs text-gray-500 dark:text-gray-400">{balance.code}</div>
                        </div>
                    </div>
                {/each}
            </div>
        {:else}
            <p class="text-sm text-gray-400 dark:text-gray-500 italic">{$_('brokers.noCashBalances')}</p>
        {/if}
    </div>

    <!-- Footer Stats -->
    <div class="px-4 py-3 bg-gray-50 dark:bg-slate-700/50 border-t border-gray-100 dark:border-slate-700 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <span>
            {$_('brokers.assets', {values: {n: broker.holdings?.length ?? 0}})}
        </span>
        <span>
            {$_('brokers.currencies', {values: {n: broker.cash_balances?.length ?? 0}})}
        </span>
    </div>
</div>
