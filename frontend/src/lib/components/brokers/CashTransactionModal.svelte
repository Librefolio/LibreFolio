<script lang="ts">
    /**
     * CashTransactionModal - Modal for cash deposit or withdrawal
     */
    import {createEventDispatcher, onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/language';
    import {zodiosApi} from '$lib/api';
    import {X} from 'lucide-svelte';
    import {SearchSelect, type SelectOption} from '$lib/components/ui/select';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import {trySave} from '$lib/utils/trySave';

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
            const response = await zodiosApi.list_currencies_api_v1_utilities_currencies_get({
                queries: {language: $currentLanguage},
            });

            currencyOptions = (response.items || []).map((c: any) => ({
                value: c.code,
                label: c.name,
                icon: c.symbol && c.symbol !== c.code ? c.symbol : undefined,
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

        // I-bis #22 — route through ``trySave`` so HTTP failures
        // surface via a toast + keep the modal open with ``error`` banner,
        // instead of closing on success only and swallowing errors to console.
        const cashAmount = type === 'DEPOSIT' ? amount : -amount;
        const result = await trySave(
            () =>
                zodiosApi.commit_transactions_api_v1_transactions_commit_post({
                    creates: [
                        {
                            broker_id: brokerId,
                            type: type,
                            date: date,
                            cash: {
                                code: currency,
                                amount: cashAmount,
                            },
                            description: description || undefined,
                        },
                    ],
                } as never),
            {fallback: $_('brokers.cashTransactionFailed', {default: 'Failed to create transaction'})},
        );
        loading = false;
        if (result.status === 'error') {
            error = result.message;
            return;
        }
        dispatch('success');
        dispatch('close');
    }

    function handleClose() {
        if (!loading) {
            dispatch('close');
        }
    }
</script>

<ModalBase closeOnBackdropClick={!loading} closeOnEscape={!loading} maxWidth="md" onRequestClose={handleClose} open={isOpen} zIndex={50}>
    <!-- Header -->
    <div class="flex items-center justify-between p-4 border-b border-gray-100 dark:border-slate-700">
        <h2 class="text-xl font-semibold text-gray-800 dark:text-gray-100">
            {type === 'DEPOSIT' ? $_('brokers.deposit') : $_('brokers.withdraw')}
        </h2>
        <button class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50" disabled={loading} on:click={handleClose}>
            <X size={20} />
        </button>
    </div>

    <!-- Error -->
    <InfoBanner class="mx-4 mt-4" dismissible message={error} ondismiss={() => (error = '')} variant="error" />

    <!-- Form -->
    <form class="p-4 space-y-4" on:submit|preventDefault={handleSubmit}>
        <!-- Amount -->
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="cash-amount">
                {$_('brokers.amount')} *
            </label>
            <input bind:value={amount} class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green" id="cash-amount" min="0.01" required step="0.01" type="number" />
        </div>

        <!-- Currency -->
        <div>
            <span class="block text-sm font-medium text-gray-700 mb-1"> Currency * </span>
            <SearchSelect bind:value={currency} loading={loadingCurrencies} options={currencyOptions} placeholder={$_('settings.selectCurrency')} />
        </div>

        <!-- Date -->
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="cash-date"> Date * </label>
            <input bind:value={date} class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green" id="cash-date" required type="date" />
        </div>

        <!-- Description -->
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="cash-description">
                {$_('brokers.description')}
            </label>
            <textarea bind:value={description} class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green resize-none" id="cash-description" rows="2"></textarea>
        </div>

        <!-- Actions -->
        <div class="flex items-center justify-end space-x-3 pt-2">
            <button class="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors" disabled={loading} on:click={handleClose} type="button">
                {$_('common.cancel')}
            </button>
            <button
                class="px-4 py-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                                   {type === 'DEPOSIT' ? 'bg-green-600 hover:bg-green-700 text-white' : 'bg-orange-600 hover:bg-orange-700 text-white'}"
                disabled={!isValid || loading}
                type="submit"
            >
                {loading ? $_('common.loading') : type === 'DEPOSIT' ? $_('brokers.deposit') : $_('brokers.withdraw')}
            </button>
        </div>
    </form>
</ModalBase>
