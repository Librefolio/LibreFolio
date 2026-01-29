<script lang="ts">
    /**
     * Broker Detail Page - Shows broker info, cash balances, holdings, and recent transactions
     */
    import {onMount} from 'svelte';
    import {goto} from '$app/navigation';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {
        ArrowLeft,
        Briefcase,
        ExternalLink,
        Pencil,
        RefreshCw,
        Wallet,
        TrendingUp,
        ArrowRightLeft
    } from 'lucide-svelte';
    import CashBalanceCard from '$lib/components/brokers/CashBalanceCard.svelte';
    import CashTransactionModal from '$lib/components/brokers/CashTransactionModal.svelte';
    import BrokerModal from '$lib/components/brokers/BrokerModal.svelte';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import BrokerImportFiles from '$lib/components/brokers/BrokerImportFiles.svelte';
    import type {BrokerSummary, Transaction} from '$lib/types';
    import {safeString, safeCurrency, parseCurrencyAmount} from '$lib/types';

    // Page data
    export let data: { brokerId: number };

    // State
    let broker: BrokerSummary | null = null;
    let transactions: Transaction[] = [];
    let loading = true;
    let error: string | null = null;

    // Modal states
    let editModalOpen = false;
    let cashModalOpen = false;
    let cashModalType: 'DEPOSIT' | 'WITHDRAWAL' = 'DEPOSIT';
    let cashModalCurrency = 'EUR';

    onMount(async () => {
        await loadBroker();
    });

    async function loadBroker() {
        loading = true;
        error = null;

        try {
            broker = await zodiosApi.get_broker_summary_api_v1_brokers__broker_id__summary_get({params: {broker_id: data.brokerId}}) as BrokerSummary;

            // Load recent transactions
            try {
                const txResponse = await zodiosApi.query_transactions_api_v1_transactions_get({queries: {broker_id: data.brokerId, limit: 10}});
                transactions = txResponse as Transaction[];
            } catch {
                transactions = [];
            }
        } catch (e) {
            console.error('Failed to load broker:', e);
            error = $_('brokers.loadFailed');
        } finally {
            loading = false;
        }
    }

    function handleBack() {
        goto('/brokers');
    }

    function handleEdit() {
        editModalOpen = true;
    }

    function handleDeposit(event: CustomEvent<{ currency: string }>) {
        cashModalType = 'DEPOSIT';
        cashModalCurrency = event.detail.currency;
        cashModalOpen = true;
    }

    function handleWithdraw(event: CustomEvent<{ currency: string }>) {
        cashModalType = 'WITHDRAWAL';
        cashModalCurrency = event.detail.currency;
        cashModalOpen = true;
    }

    function handleNewDeposit() {
        cashModalType = 'DEPOSIT';
        cashModalCurrency = broker?.cash_balances?.[0]?.code ?? 'EUR';
        cashModalOpen = true;
    }

    async function handleCashSuccess() {
        await loadBroker();
    }

    async function handleUpdated() {
        await loadBroker();
    }

    // Format currency - accepts string amount (from API) or number
    function formatCurrency(amount: string | number, code: string): string {
        const numAmount = typeof amount === 'string' ? parseFloat(amount) || 0 : amount;
        return new Intl.NumberFormat(undefined, {
            style: 'currency',
            currency: code,
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(numAmount);
    }

    // Format date - handles string or array union type from generated types
    function formatDate(dateStr: unknown): string {
        const str = safeString(dateStr);
        if (!str) return '-';
        return new Date(str).toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    // Transaction type badge color
    function getTypeBadgeClass(type: string): string {
        switch (type) {
            case 'BUY':
                return 'bg-green-100 text-green-800';
            case 'SELL':
                return 'bg-red-100 text-red-800';
            case 'DEPOSIT':
                return 'bg-blue-100 text-blue-800';
            case 'WITHDRAWAL':
                return 'bg-orange-100 text-orange-800';
            case 'DIVIDEND':
                return 'bg-purple-100 text-purple-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    }

</script>

<div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center space-x-4">
        <button
                on:click={handleBack}
                class="p-2 text-gray-500 hover:text-libre-green hover:bg-libre-green/10 rounded-lg transition-colors"
                title={$_('common.back')}
        >
            <ArrowLeft size={20}/>
        </button>

        {#if broker}
            <!-- Broker Icon -->
            <BrokerIcon
                iconUrl={safeString(broker.icon_url)}
                portalUrl={safeString(broker.portal_url)}
                pluginCode={safeString(broker.default_import_plugin)}
                altText={broker.name}
                size="lg"
            />

            <div class="flex-1 min-w-0">
                <h1 class="text-2xl font-bold text-gray-800 dark:text-gray-100 truncate">{broker.name}</h1>
                {#if broker.description}
                    <p class="text-gray-500 dark:text-gray-400 text-sm truncate">{broker.description}</p>
                {/if}
            </div>

            <div class="flex items-center space-x-2">
                {#if safeString(broker.portal_url)}
                    <a
                            href={safeString(broker.portal_url)}
                            target="_blank"
                            rel="noopener noreferrer"
                            class="p-2 text-gray-500 hover:text-libre-green hover:bg-libre-green/10 rounded-lg transition-colors"
                            title={$_('brokers.openPortal')}
                    >
                        <ExternalLink size={20}/>
                    </a>
                {/if}
                <button
                        on:click={loadBroker}
                        disabled={loading}
                        class="p-2 text-gray-500 hover:text-libre-green hover:bg-libre-green/10 rounded-lg transition-colors disabled:opacity-50"
                        title="Refresh"
                >
                    <RefreshCw size={20} class={loading ? 'animate-spin' : ''}/>
                </button>
                <button
                        on:click={handleEdit}
                        class="flex items-center space-x-2 px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors"
                >
                    <Pencil size={18}/>
                    <span>{$_('common.edit')}</span>
                </button>
            </div>
        {:else if !error}
            <div class="flex-1">
                <div class="h-8 w-48 bg-gray-200 rounded animate-pulse"></div>
            </div>
        {/if}
    </div>

    {#if loading && !broker}
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
                    on:click={loadBroker}
                    class="px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors"
            >
                {$_('error.tryAgain')}
            </button>
        </div>
    {:else if broker}
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Left Column: Cash Balances -->
            <div class="lg:col-span-2 space-y-4">
                <!-- Cash Balances Section -->
                <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                    <div class="flex items-center justify-between mb-4">
                        <div class="flex items-center space-x-2 text-gray-700">
                            <Wallet size={20}/>
                            <h2 class="font-semibold">{$_('brokers.cashBalances')}</h2>
                        </div>
                        <button
                                on:click={handleNewDeposit}
                                class="text-sm text-libre-green hover:underline"
                        >
                            + {$_('brokers.deposit')}
                        </button>
                    </div>

                    {#if broker.cash_balances && broker.cash_balances.length > 0}
                        <div class="space-y-3">
                            {#each broker.cash_balances as balance}
                                <CashBalanceCard
                                        code={balance.code}
                                        amount={parseCurrencyAmount(balance.amount)}
                                        on:deposit={handleDeposit}
                                        on:withdraw={handleWithdraw}
                                />
                            {/each}
                        </div>
                    {:else}
                        <p class="text-gray-400 text-sm italic py-4 text-center">{$_('brokers.noCashBalances')}</p>
                    {/if}
                </div>

                <!-- Holdings Section -->
                <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                    <div class="flex items-center space-x-2 text-gray-700 mb-4">
                        <TrendingUp size={20}/>
                        <h2 class="font-semibold">{$_('brokers.holdings')}</h2>
                    </div>

                    {#if broker.holdings && broker.holdings.length > 0}
                        <div class="overflow-x-auto">
                            <table class="w-full text-sm">
                                <thead>
                                <tr class="text-left text-gray-500 border-b">
                                    <th class="pb-2 font-medium">Asset</th>
                                    <th class="pb-2 font-medium text-right">Quantity</th>
                                    <th class="pb-2 font-medium text-right">Cost</th>
                                    <th class="pb-2 font-medium text-right">Value</th>
                                    <th class="pb-2 font-medium text-right">P&L</th>
                                </tr>
                                </thead>
                                <tbody>
                                {#each broker.holdings as holding}
                                    {@const totalCost = safeCurrency(holding.total_cost)}
                                    {@const currentValue = safeCurrency(holding.current_value)}
                                    {@const pnl = safeCurrency(holding.unrealized_pnl)}
                                    <tr class="border-b border-gray-50 hover:bg-gray-50">
                                        <td class="py-2 font-medium text-gray-800">{holding.asset_name}</td>
                                        <td class="py-2 text-right text-gray-600">{holding.quantity.toLocaleString()}</td>
                                        <td class="py-2 text-right text-gray-600">
                                            {#if totalCost}
                                                {formatCurrency(totalCost.amount, totalCost.code)}
                                            {:else}
                                                <span class="text-gray-400">-</span>
                                            {/if}
                                        </td>
                                        <td class="py-2 text-right text-gray-600">
                                            {#if currentValue}
                                                {formatCurrency(currentValue.amount, currentValue.code)}
                                            {:else}
                                                <span class="text-gray-400">-</span>
                                            {/if}
                                        </td>
                                        <td class="py-2 text-right">
                                            {#if pnl}
                                                {@const pnlNum = parseCurrencyAmount(pnl.amount)}
                                                <span class="{pnlNum >= 0 ? 'text-green-600' : 'text-red-600'}">
                                                    {pnlNum >= 0 ? '+' : ''}{formatCurrency(pnl.amount, pnl.code)}
                                                </span>
                                            {:else}
                                                <span class="text-gray-400">-</span>
                                            {/if}
                                        </td>
                                    </tr>
                                {/each}
                                </tbody>
                            </table>
                        </div>
                    {:else}
                        <p class="text-gray-400 text-sm italic py-4 text-center">{$_('brokers.noHoldings')}</p>
                    {/if}
                </div>

                <!-- Import Files Section -->
                <BrokerImportFiles brokerId={data.brokerId} />
            </div>

            <!-- Right Column: Info & Recent Transactions -->
            <div class="space-y-4">
                <!-- Broker Info Card -->
                <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                    <h3 class="font-semibold text-gray-700 mb-3">Broker Info</h3>
                    <div class="space-y-2 text-sm">
                        <div class="flex justify-between">
                            <span class="text-gray-500">{$_('brokers.isActive')}</span>
                            <span class="font-medium {broker.is_active ? 'text-green-600' : 'text-red-500'}">
                                {broker.is_active ? '✓ Active' : '✗ Closed'}
                            </span>
                        </div>
                        {#if safeString(broker.opened_at)}
                            <div class="flex justify-between">
                                <span class="text-gray-500">{$_('brokers.openedAt')}</span>
                                <span class="text-gray-700">{formatDate(broker.opened_at)}</span>
                            </div>
                        {/if}
                        <div class="flex justify-between">
                            <span class="text-gray-500">{$_('brokers.allowOverdraft')}</span>
                            <span class="font-medium {broker.allow_cash_overdraft ? 'text-green-600' : 'text-gray-400'}">
                                {broker.allow_cash_overdraft ? '✓' : '✗'}
                            </span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-500">{$_('brokers.allowShorting')}</span>
                            <span class="font-medium {broker.allow_asset_shorting ? 'text-green-600' : 'text-gray-400'}">
                                {broker.allow_asset_shorting ? '✓' : '✗'}
                            </span>
                        </div>
                        <div class="flex justify-between border-t border-gray-100 pt-2 mt-2">
                            <span class="text-gray-500">Created in System</span>
                            <span class="text-gray-700">{formatDate(broker.created_at)}</span>
                        </div>
                    </div>

                    {#if broker.total_value_base_currency}
                        {@const totalValue = safeCurrency(broker.total_value_base_currency)}
                        {#if totalValue}
                            <div class="mt-4 pt-4 border-t border-gray-100">
                                <div class="text-sm text-gray-500">{$_('brokers.totalValue')}</div>
                                <div class="text-2xl font-bold text-libre-green">
                                    {formatCurrency(totalValue.amount, totalValue.code)}
                                </div>
                            </div>
                        {/if}
                    {/if}
                </div>

                <!-- Recent Transactions -->
                <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                    <div class="flex items-center space-x-2 text-gray-700 mb-3">
                        <ArrowRightLeft size={18}/>
                        <h3 class="font-semibold">{$_('brokers.recentTransactions')}</h3>
                    </div>

                    {#if transactions.length > 0}
                        <div class="space-y-2">
                            {#each transactions as tx}
                                {@const cashValue = safeCurrency(tx.cash)}
                                <div class="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                                    <div>
                                        <span class="inline-block px-2 py-0.5 text-xs rounded {getTypeBadgeClass(tx.type)}">
                                            {tx.type}
                                        </span>
                                        <span class="text-xs text-gray-500 ml-2">{formatDate(tx.date)}</span>
                                    </div>
                                    {#if cashValue}
                                        <span class="font-medium text-gray-800">
                                            {formatCurrency(cashValue.amount, cashValue.code)}
                                        </span>
                                    {:else}
                                        <span class="text-gray-400">-</span>
                                    {/if}
                                </div>
                            {/each}
                        </div>
                        <a
                                href="/transactions?broker_id={broker.id}"
                                class="block mt-3 text-center text-sm text-libre-green hover:underline"
                        >
                            {$_('brokers.viewAllTransactions')} →
                        </a>
                    {:else}
                        <p class="text-gray-400 text-sm italic py-4 text-center">{$_('brokers.noTransactions')}</p>
                    {/if}
                </div>
            </div>
        </div>
    {/if}
</div>

<!-- Edit Modal -->
{#if broker}
    <BrokerModal
            isOpen={editModalOpen}
            mode="edit"
            brokerId={broker.id}
            initialData={{
                name: broker.name,
                description: safeString(broker.description),
                portal_url: safeString(broker.portal_url),
                icon_url: safeString(broker.icon_url),
                default_import_plugin: safeString(broker.default_import_plugin),
                allow_cash_overdraft: broker.allow_cash_overdraft,
                allow_asset_shorting: broker.allow_asset_shorting,
                is_active: broker.is_active,
                opened_at: safeString(broker.opened_at)
            }}
            on:close={() => editModalOpen = false}
            on:updated={handleUpdated}
    />

    <!-- Cash Transaction Modal -->
    <CashTransactionModal
            isOpen={cashModalOpen}
            type={cashModalType}
            brokerId={broker.id}
            initialCurrency={cashModalCurrency}
            on:close={() => cashModalOpen = false}
            on:success={handleCashSuccess}
    />
{/if}
