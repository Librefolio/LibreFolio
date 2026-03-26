<script lang="ts">
    /**
     * CashBalanceCard - Display cash balance for a currency with deposit/withdraw actions
     */
    import {createEventDispatcher} from 'svelte';
    import {_} from '$lib/i18n';
    import {ArrowDownLeft, ArrowUpRight} from 'lucide-svelte';

    const dispatch = createEventDispatcher<{
        deposit: { currency: string };
        withdraw: { currency: string };
    }>();

    // Props
    export let code: string;
    export let amount: number;
    export let symbol: string | undefined = undefined;
    export let canEdit: boolean = true;

    // Format amount
    $: formattedAmount = new Intl.NumberFormat(undefined, {
        style: 'currency',
        currency: code,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);

    $: isPositive = amount > 0;
    $: isNegative = amount < 0;
</script>

<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
    <div class="flex items-start justify-between">
        <!-- Currency info -->
        <div class="flex items-center space-x-3">
            {#if symbol && symbol !== code}
                <div class="w-10 h-10 flex items-center justify-center bg-libre-green/10 rounded-lg text-xl">
                    {symbol}
                </div>
            {:else}
                <div class="w-10 h-10 flex items-center justify-center bg-gray-100 rounded-lg text-sm font-bold text-gray-600">
                    {code.slice(0, 2)}
                </div>
            {/if}
            <div>
                <div class="text-sm text-gray-500">{code}</div>
                <div class="text-xl font-semibold {isNegative ? 'text-red-600' : isPositive ? 'text-gray-800' : 'text-gray-500'}">
                    {formattedAmount}
                </div>
            </div>
        </div>

        <!-- Actions -->
        {#if canEdit}
            <div class="flex items-center space-x-1">
                <button
                        class="flex items-center space-x-1 px-3 py-1.5 text-sm text-green-700 bg-green-50 hover:bg-green-100 rounded-lg transition-colors"
                        on:click={() => dispatch('deposit', { currency: code })}
                        title={$_('brokers.deposit')}
                >
                    <ArrowDownLeft size={16}/>
                    <span class="hidden sm:inline">{$_('brokers.deposit')}</span>
                </button>
                <button
                        class="flex items-center space-x-1 px-3 py-1.5 text-sm text-orange-700 bg-orange-50 hover:bg-orange-100 rounded-lg transition-colors"
                        on:click={() => dispatch('withdraw', { currency: code })}
                        title={$_('brokers.withdraw')}
                >
                    <ArrowUpRight size={16}/>
                    <span class="hidden sm:inline">{$_('brokers.withdraw')}</span>
                </button>
            </div>
        {/if}
    </div>
</div>

