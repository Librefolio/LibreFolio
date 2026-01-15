<script lang="ts">
    /**
     * BrokerCard - Display a broker with cash balances and quick actions
     */
    import {createEventDispatcher} from 'svelte';
    import {goto} from '$app/navigation';
    import {_} from '$lib/i18n';
    import {Briefcase, ExternalLink, Pencil, Trash2, Wallet} from 'lucide-svelte';

    const dispatch = createEventDispatcher<{
        edit: { id: number };
        delete: { id: number; name: string };
    }>();

    // Props
    export let broker: {
        id: number;
        name: string;
        description?: string | null;
        portal_url?: string | null;
        icon_url?: string | null;
        allow_cash_overdraft: boolean;
        allow_asset_shorting: boolean;
        is_active?: boolean;
        cash_balances?: Array<{ code: string; amount: number; symbol?: string }>;
        holdings?: Array<{ asset_id: number }>;
    };

    // Format currency amount
    function formatAmount(amount: number, code: string): string {
        return new Intl.NumberFormat(undefined, {
            style: 'currency',
            currency: code,
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount);
    }

    // Get broker icon (custom or favicon from portal)
    function getBrokerIcon(): string | null {
        if (broker.icon_url) return broker.icon_url;
        if (broker.portal_url) {
            try {
                const url = new URL(broker.portal_url);
                return `${url.origin}/favicon.ico`;
            } catch {
                return null;
            }
        }
        return null;
    }

    $: brokerIcon = getBrokerIcon();

    // Track if icon failed to load
    let iconFailed = false;

    function handleIconError() {
        iconFailed = true;
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
    role="button"
    tabindex="0"
    on:click={handleCardClick}
    on:keydown={(e) => e.key === 'Enter' && handleCardClick()}
    class="w-full text-left bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden cursor-pointer
           transition-all duration-200 hover:shadow-lg hover:border-libre-green/30 hover:bg-libre-green/5
           focus:outline-none focus:ring-2 focus:ring-libre-green focus:ring-offset-2"
    class:opacity-60={broker.is_active === false}
>
    <!-- Header -->
    <div class="p-4 border-b border-gray-100">
        <div class="flex items-start justify-between">
            <div class="flex items-center gap-3 flex-1 min-w-0">
                <!-- Broker Icon with fallback -->
                <div class="w-10 h-10 rounded-full bg-libre-green/10 flex items-center justify-center shrink-0 overflow-hidden">
                    {#if brokerIcon && !iconFailed}
                        <img
                            src={brokerIcon}
                            alt=""
                            class="w-full h-full object-cover"
                            on:error={handleIconError}
                        />
                    {:else}
                        <!-- Fallback: show briefcase icon or first letter -->
                        <Briefcase size={20} class="text-libre-green" />
                    {/if}
                </div>

                <div class="min-w-0">
                    <h3 class="text-lg font-semibold text-gray-800 truncate">{broker.name}</h3>
                    {#if broker.description}
                        <p class="text-sm text-gray-500 mt-0.5 line-clamp-1">{broker.description}</p>
                    {/if}
                </div>
            </div>

            <!-- Actions (Edit & Delete only) -->
            <div class="flex items-center space-x-1 ml-2">
                <button
                        on:click={handleEdit}
                        class="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title={$_('common.edit')}
                >
                    <Pencil size={18}/>
                </button>
                <button
                        on:click={handleDelete}
                        class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title={$_('common.delete')}
                >
                    <Trash2 size={18}/>
                </button>
            </div>
        </div>

        <!-- Portal Link -->
        {#if broker.portal_url}
            <a
                    href={broker.portal_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    on:click={handlePortalClick}
                    class="inline-flex items-center space-x-1 text-sm text-libre-green hover:underline mt-2"
            >
                <span>{$_('brokers.openPortal')}</span>
                <ExternalLink size={14}/>
            </a>
        {/if}
    </div>

    <!-- Cash Balances -->
    <div class="p-4">
        <div class="flex items-center space-x-2 text-sm text-gray-500 mb-3">
            <Wallet size={16}/>
            <span>{$_('brokers.cashBalances')}</span>
        </div>

        {#if broker.cash_balances && broker.cash_balances.length > 0}
            <div class="grid grid-cols-2 gap-2">
                {#each broker.cash_balances as balance}
                    <div class="flex items-center space-x-2 px-3 py-2 bg-gray-50 rounded-lg">
                        {#if balance.symbol && balance.symbol !== balance.code}
                            <span class="text-lg w-6 text-center">{balance.symbol}</span>
                        {/if}
                        <div class="flex-1 min-w-0">
                            <div class="font-medium text-gray-800 truncate">
                                {formatAmount(balance.amount, balance.code)}
                            </div>
                            <div class="text-xs text-gray-500">{balance.code}</div>
                        </div>
                    </div>
                {/each}
            </div>
        {:else}
            <p class="text-sm text-gray-400 italic">{$_('brokers.noCashBalances')}</p>
        {/if}
    </div>

    <!-- Footer Stats -->
    <div class="px-4 py-3 bg-gray-50 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
        <span>
            {$_('brokers.assets', {values: {count: broker.holdings?.length ?? 0}})}
        </span>
        <span>
            {$_('brokers.currencies', {values: {count: broker.cash_balances?.length ?? 0}})}
        </span>
    </div>
</div>
