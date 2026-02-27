<script lang="ts">
    /**
     * CashTransactionModal - Modal for cash deposit or withdrawal
     */
    import {createEventDispatcher, onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {X} from 'lucide-svelte';
    import {SearchSelect, type SelectOption} from '$lib/components/ui/select';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';

    const dispatch = createEventDispatcher<{
        close: void;
        success: void;
    }>();

    // Props
    export let isOpen = false;
    export let type: 'DEPOSIT' | 'WITHDRAWAL' = 'DEPOSIT';
    export let brokerId: number;
    export let initialCurrency: string = 'EUR';

    // Form state
    let amount = 0;
    let currency = initialCurrency;
    let date = new Date().toISOString().split('T')[0];
    let description = '';
    let loading = false;
    let error: string | null = null;

    // Currency options
    let currencyOptions: SelectOption[] = [];
    let loadingCurrencies = true;

    // Reset form when modal opens
    $: if (isOpen) {
        amount = 0;
        currency = initialCurrency;
        date = new Date().toISOString().split('T')[0];
        description = '';
        error = null;
    }

    // Load currencies on mount
    onMount(async () => {
        try {
            const response = await zodiosApi.list_currencies_api_v1_utilities_currencies_get();

            currencyOptions = (response.items || []).map((c: any) => ({
                value: c.code,
                label: c.name,
                icon: c.symbol && c.symbol !== c.code ? c.symbol : undefined
            }));
        } catch (e) {
            console.error('Failed to load currencies:', e);
        } finally {
            loadingCurrencies = false;
        }
    });

    $: isValid = amount > 0 && currency.length === 3 && date;

    async function handleSubmit() {
        if (!isValid || loading) return;

        loading = true;
        error = null;

        try {
            // Create transaction - use cash object for cash movement
            // DEPOSIT: cash.amount > 0, WITHDRAWAL: cash.amount < 0
            const cashAmount = type === 'DEPOSIT' ? amount : -amount;
            await zodiosApi.create_transactions_api_v1_transactions_post([{
                broker_id: brokerId,
                type: type,
                date: date,
                cash: {
                    code: currency,
                    amount: cashAmount
                },
                description: description || undefined
            }]);

            dispatch('success');
            dispatch('close');
        } catch (e) {
            console.error('Failed to create transaction:', e);
            error = 'Failed to create transaction';
        } finally {
            loading = false;
        }
    }

    function handleClose() {
        if (!loading) {
            dispatch('close');
        }
    }
</script>

<ModalBase
    open={isOpen}
    zIndex={50}
    maxWidth="md"
    closeOnEscape={!loading}
    closeOnBackdropClick={!loading}
    onRequestClose={handleClose}
>
            <!-- Header -->
            <div class="flex items-center justify-between p-4 border-b border-gray-100 dark:border-slate-700">
                <h2 class="text-xl font-semibold text-gray-800 dark:text-gray-100">
                    {type === 'DEPOSIT' ? $_('brokers.deposit') : $_('brokers.withdraw')}
                </h2>
                <button
                        on:click={handleClose}
                        disabled={loading}
                        class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
                >
                    <X size={20}/>
                </button>
            </div>

            <!-- Error -->
            <ErrorBanner message={error} className="mx-4 mt-4" on:dismiss={() => error = ''} />

            <!-- Form -->
            <form on:submit|preventDefault={handleSubmit} class="p-4 space-y-4">
                <!-- Amount -->
                <div>
                    <label for="cash-amount" class="block text-sm font-medium text-gray-700 mb-1">
                        {$_('brokers.amount')} *
                    </label>
                    <input
                            id="cash-amount"
                            type="number"
                            step="0.01"
                            min="0.01"
                            bind:value={amount}
                            required
                            class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green"
                    />
                </div>

                <!-- Currency -->
                <div>
                    <span class="block text-sm font-medium text-gray-700 mb-1">
                        Currency *
                    </span>
                    <SearchSelect
                            bind:value={currency}
                            options={currencyOptions}
                            placeholder={$_('settings.selectCurrency')}
                            loading={loadingCurrencies}
                    />
                </div>

                <!-- Date -->
                <div>
                    <label for="cash-date" class="block text-sm font-medium text-gray-700 mb-1">
                        Date *
                    </label>
                    <input
                            id="cash-date"
                            type="date"
                            bind:value={date}
                            required
                            class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green"
                    />
                </div>

                <!-- Description -->
                <div>
                    <label for="cash-description" class="block text-sm font-medium text-gray-700 mb-1">
                        {$_('brokers.description')}
                    </label>
                    <textarea
                            id="cash-description"
                            bind:value={description}
                            rows="2"
                            class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green resize-none"
                    ></textarea>
                </div>

                <!-- Actions -->
                <div class="flex items-center justify-end space-x-3 pt-2">
                    <button
                            type="button"
                            on:click={handleClose}
                            disabled={loading}
                            class="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        {$_('common.cancel')}
                    </button>
                    <button
                            type="submit"
                            disabled={!isValid || loading}
                            class="px-4 py-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                                   {type === 'DEPOSIT' ? 'bg-green-600 hover:bg-green-700 text-white' : 'bg-orange-600 hover:bg-orange-700 text-white'}"
                    >
                        {loading ? $_('common.loading') : (type === 'DEPOSIT' ? $_('brokers.deposit') : $_('brokers.withdraw'))}
                    </button>
                </div>
            </form>
</ModalBase>

