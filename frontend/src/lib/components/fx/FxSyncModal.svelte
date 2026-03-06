<!--
  FxSyncModal — Modal for syncing FX rates with external providers.
  Shows progress and results of the sync operation.

  Converted to Svelte 5 runes. Passes configured currencies to backend
  (fixes bug where backend defaulted to USD,GBP,CHF,JPY).
-->
<script lang="ts">
    import {zodiosApi} from '$lib/api';
    import {RefreshCw, Check, AlertTriangle, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import {_ as t} from '$lib/i18n';

    interface Props {
        /** Whether modal is open */
        open: boolean;
        /** Start date for sync range */
        dateStart: string;
        /** End date for sync range */
        dateEnd: string;
        /** All unique currencies from configured pairs — MUST be passed by parent */
        currencies: string[];
        /** Called after successful sync */
        onsynced: () => void;
        /** Called on close */
        onclose: () => void;
    }

    let {
        open = $bindable(),
        dateStart,
        dateEnd,
        currencies,
        onsynced,
        onclose,
    }: Props = $props();

    let syncing = $state(false);
    let result = $state<{synced: number; currencies: string[]} | null>(null);
    let error = $state<string | null>(null);

    // Reset state when modal opens
    $effect(() => {
        if (open) {
            result = null;
            error = null;
        }
    });

    async function handleSync() {
        syncing = true;
        error = null;
        result = null;
        try {
            const currenciesStr = currencies.join(',');
            const response = await zodiosApi.sync_rates_api_v1_fx_currencies_sync_get({
                queries: {
                    start: dateStart,
                    end: dateEnd,
                    currencies: currenciesStr,
                }
            });
            result = {
                synced: (response as any)?.synced || 0,
                currencies: (response as any)?.currencies || [],
            };
            onsynced();
        } catch (e: any) {
            error = e?.message || 'Sync failed';
        } finally {
            syncing = false;
        }
    }
</script>

<ModalBase {open} onRequestClose={onclose} maxWidth="max-w-md">
    <!-- Header -->
    <div class="flex items-center justify-between pb-3 border-b border-gray-100 dark:border-slate-700">
        <div class="flex items-center gap-2.5">
            <div class="flex items-center justify-center w-9 h-9 rounded-lg bg-amber-100 dark:bg-amber-900/30">
                <RefreshCw size={18} class="text-amber-600 dark:text-amber-400" />
            </div>
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">
                {$t('fx.sync.title') ?? 'Sync FX Rates'}
            </h2>
        </div>
        <button
            class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            onclick={onclose}
        >
            <X size={18} />
        </button>
    </div>

    <!-- Body -->
    <div class="py-4 space-y-3">
        <p class="text-sm text-gray-600 dark:text-gray-400">
            {$t('fx.sync.description') ?? 'Synchronize exchange rates from configured providers for the selected date range.'}
        </p>
        <div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-slate-800 rounded-lg px-3 py-2">
            <span class="font-medium text-gray-700 dark:text-gray-300">{dateStart}</span>
            <span>→</span>
            <span class="font-medium text-gray-700 dark:text-gray-300">{dateEnd}</span>
            <span class="mx-1">·</span>
            <span>{currencies.length} {$t('fx.sync.currenciesCount') ?? 'currencies'}</span>
        </div>

        {#if error}
            <div class="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                <AlertTriangle size={16} class="text-red-500 flex-shrink-0" />
                <span class="text-sm text-red-600 dark:text-red-400">{error}</span>
            </div>
        {/if}

        {#if result}
            <div class="flex items-center gap-2 p-3 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg border border-emerald-200 dark:border-emerald-800">
                <Check size={16} class="text-emerald-500 flex-shrink-0" />
                <div class="text-sm text-emerald-700 dark:text-emerald-400">
                    <span class="font-medium">
                        {$t('fx.sync.synced') ?? 'Synced'} {result.synced} rate{result.synced !== 1 ? 's' : ''}
                    </span>
                    {#if result.currencies.length > 0}
                        <span class="text-emerald-600 dark:text-emerald-500">
                            — {result.currencies.join(', ')}
                        </span>
                    {/if}
                </div>
            </div>
        {/if}
    </div>

    <!-- Footer -->
    <div class="flex justify-end gap-2 pt-3 border-t border-gray-100 dark:border-slate-700">
        <button
            class="px-4 py-2 text-sm font-medium bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
            onclick={onclose}
        >
            {result ? ($t('common.close') ?? 'Close') : ($t('common.cancel') ?? 'Cancel')}
        </button>
        {#if !result}
            <button
                class="flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50"
                onclick={handleSync}
                disabled={syncing || currencies.length === 0}
            >
                <RefreshCw size={15} class={syncing ? 'animate-spin' : ''} />
                {syncing ? ($t('fx.sync.syncing') ?? 'Syncing...') : ($t('fx.sync.start') ?? 'Start Sync')}
            </button>
        {/if}
    </div>
</ModalBase>
