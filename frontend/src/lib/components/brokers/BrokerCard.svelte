<script lang="ts">
    /**
     * BrokerCard - Display a broker with cash balances and quick actions
     */
    import {createEventDispatcher} from 'svelte';
    import {_} from '$lib/i18n';
    import {formatCurrencyAmountHtml} from '$lib/utils/currency/currencyFormat';
    import {Crown, ExternalLink, Eye, Pencil, Share2, Trash2, Wallet} from 'lucide-svelte';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';

    type BrokerBreakdownCard = {
        broker_id: number;
        net_worth: {code: string; amount: number | string};
        gain_loss: {code: string; amount: number | string};
        gain_loss_percent: string;
        cash_balances?: Array<{code: string; amount: number | string}>;
    };

    type _DispatchEvents = {
        edit: {id: number};
        delete: {id: number; name: string};
        share: {id: number};
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
        user_share_percentage?: number | string | null;
    };
    export let summary: BrokerBreakdownCard | null = null;
    export let assetCount = 0;
    export let targetCurrency = 'EUR';

    function toNumber(value: number | string | null | undefined): number {
        if (typeof value === 'number') return value;
        if (typeof value === 'string') return Number(value);
        return 0;
    }

    function handleEdit(event: MouseEvent) {
        event.preventDefault();
        event.stopPropagation();
        dispatch('edit', {id: broker.id});
    }

    function handleDelete(event: MouseEvent) {
        event.preventDefault();
        event.stopPropagation();
        dispatch('delete', {id: broker.id, name: broker.name});
    }

    function handleShare(event: MouseEvent) {
        event.preventDefault();
        event.stopPropagation();
        dispatch('share', {id: broker.id});
    }

    function handleOpenPortal(event: MouseEvent) {
        event.preventDefault();
        event.stopPropagation();
        if (broker.portal_url) window.open(broker.portal_url, '_blank', 'noopener,noreferrer');
    }
</script>

<a
    href="/brokers/{broker.id}"
    class="block w-full text-left bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 overflow-hidden cursor-pointer
           transition-all duration-200 hover:shadow-lg hover:border-libre-green/30 hover:bg-libre-green/5 dark:hover:bg-slate-700
           focus:outline-none focus:ring-2 focus:ring-libre-green focus:ring-offset-2"
    class:opacity-60={broker.is_active === false}
    data-testid="broker-card-{broker.id}"
>
    <!-- Header -->
    <div class="p-4 border-b border-gray-100 dark:border-slate-700">
        <div class="flex items-start justify-between">
            <div class="flex items-center gap-3 flex-1 min-w-0">
                <!-- Broker Icon -->
                <BrokerIcon brokerId={broker.id} altText={broker.name} iconUrl={broker.icon_url} pluginCode={broker.default_import_plugin} portalUrl={broker.portal_url} size="md" />

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
                        <h3 use:scrollOnOverflow class="{overflowScrollTextClass} text-lg font-semibold text-gray-800 dark:text-gray-100" title={broker.name}>{broker.name}</h3>
                    </div>
                    {#if broker.description}
                        <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-1">{broker.description}</p>
                    {/if}
                </div>
            </div>

            <!-- Actions -->
            <div class="flex items-center space-x-1 ml-2">
                <button class="p-2 text-gray-400 hover:text-libre-green hover:bg-libre-green/10 rounded-lg transition-colors" data-testid="broker-share-{broker.id}" on:click={handleShare} title={$_('brokers.sharing.title')}>
                    <Share2 size={18} />
                </button>
                <button class="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors" data-testid="broker-edit-{broker.id}" on:click={handleEdit} title={$_('common.edit')}>
                    <Pencil size={18} />
                </button>
                <button class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors" data-testid="broker-delete-{broker.id}" on:click={handleDelete} title={$_('common.delete')}>
                    <Trash2 size={18} />
                </button>
                {#if broker.portal_url}
                    <button type="button" class="p-2 text-gray-400 hover:text-libre-green hover:bg-libre-green/10 rounded-lg transition-colors" data-testid="broker-portal-{broker.id}" on:click={handleOpenPortal} title={$_('brokers.openPortal')} aria-label={$_('brokers.openPortal')}>
                        <ExternalLink size={18} />
                    </button>
                {:else}
                    <span class="p-2 text-gray-300 dark:text-gray-600 rounded-lg" aria-hidden="true">
                        <ExternalLink size={18} />
                    </span>
                {/if}
            </div>
        </div>
    </div>

    <!-- Cash Balances -->
    <div class="p-4">
        <div class="space-y-1.5 mb-4 text-sm">
            <div class="flex items-center justify-between gap-3">
                <span class="text-gray-500 dark:text-gray-400">{$_('brokers.nav')}</span>
                <span class="font-medium text-gray-800 dark:text-gray-100">
                    {#if summary}
                        {@html formatCurrencyAmountHtml(toNumber(summary.net_worth.amount), summary.net_worth.code)}
                    {:else}
                        —
                    {/if}
                </span>
            </div>
            <div class="flex items-center justify-between gap-3">
                <span class="text-gray-500 dark:text-gray-400">{$_('brokers.gainLoss')}</span>
                <span class="font-medium {summary && toNumber(summary.gain_loss.amount) < 0 ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'}">
                    {#if summary}
                        {@html formatCurrencyAmountHtml(toNumber(summary.gain_loss.amount), targetCurrency, {showSign: true})}
                        <span class="ml-1 text-xs">({(toNumber(summary.gain_loss_percent) * 100).toFixed(2)}%)</span>
                    {:else}
                        <span class="text-gray-800 dark:text-gray-100">—</span>
                    {/if}
                </span>
            </div>
        </div>

        <div class="flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400 mb-3">
            <Wallet size={16} />
            <span>{$_('brokers.cashBalances')}</span>
        </div>

        {#if summary?.cash_balances && summary.cash_balances.length > 0}
            <div class="flex flex-wrap gap-2">
                {#each [...summary.cash_balances].sort((a, b) => toNumber(b.amount) - toNumber(a.amount)) as balance}
                    <span class="inline-flex items-center px-3 py-1.5 bg-gray-50 dark:bg-slate-700 rounded-lg text-sm font-medium text-gray-800 dark:text-gray-100">
                        {@html formatCurrencyAmountHtml(toNumber(balance.amount), balance.code)}
                    </span>
                {/each}
            </div>
        {:else}
            <p class="text-sm text-gray-400 dark:text-gray-500 italic">{$_('brokers.noCashBalances')}</p>
        {/if}
    </div>

    <!-- Footer Stats -->
    <div class="px-4 py-3 bg-gray-50 dark:bg-slate-700/50 border-t border-gray-100 dark:border-slate-700 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <span>
            {$_('brokers.assets', {values: {n: assetCount}})}
        </span>
        <span>
            {$_('brokers.currencies', {values: {n: summary?.cash_balances?.length ?? 0}})}
        </span>
    </div>
</a>
