<!--
  FxSyncModal — Modal for syncing FX rates with external providers.
  Shows progress and results of the sync operation.

  Accepts configured pairs (e.g. ['EUR-GBP', 'EUR-USD']) and extracts
  unique currencies for the backend API call. Displays pair count and
  pair names for user clarity.
-->
<script lang="ts">
    import {zodiosApi} from '$lib/api';
    import {RefreshCw, Check, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import {_ as t} from '$lib/i18n';

    interface Props {
        /** Whether modal is open */
        open: boolean;
        /** Start date for sync range */
        dateStart: string;
        /** End date for sync range */
        dateEnd: string;
        /** Configured pair slugs, e.g. ['EUR-GBP', 'EUR-USD'] */
        pairs: string[];
        /** Called after successful sync */
        onsynced: () => void;
        /** Called on close */
        onclose: () => void;
    }

    let {
        open = $bindable(),
        dateStart,
        dateEnd,
        pairs,
        onsynced,
        onclose,
    }: Props = $props();

    // Derive unique currencies from pairs for the backend API
    let currencies = $derived([...new Set(pairs.flatMap(p => p.split('-')))].sort());

    let syncing = $state(false);
    let result = $state<{synced: number; currencies: string[]} | null>(null);
    let error = $state<string | null>(null);

    // Map synced currencies back to pairs for display
    let syncedPairs = $derived.by(() => {
        if (!result) return [];
        const syncedSet = new Set(result.currencies);
        return pairs.filter(slug => {
            const [base, quote] = slug.split('-');
            return syncedSet.has(base) || syncedSet.has(quote);
        });
    });

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
    <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-slate-700">
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
    <div class="px-6 py-4 space-y-3">
        <p class="text-sm text-gray-600 dark:text-gray-400">
            {$t('fx.sync.description') ?? 'Synchronize exchange rates from configured providers for the selected date range.'}
        </p>
        <div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-slate-800 rounded-lg px-3 py-2">
            <span class="font-medium text-gray-700 dark:text-gray-300">{dateStart}</span>
            <span>→</span>
            <span class="font-medium text-gray-700 dark:text-gray-300">{dateEnd}</span>
            <span class="mx-1">·</span>
            <span>{pairs.length} {$t('fx.sync.pairsCount') ?? 'pairs'}</span>
        </div>

        {#if error}
            <InfoBanner variant="error">
                <span class="text-sm">{error}</span>
            </InfoBanner>
        {/if}

        {#if result}
            <InfoBanner variant="success">
                <div class="text-sm">
                    <span class="font-medium">
                        {$t('fx.sync.synced') ?? 'Synced'} {result.synced} rate{result.synced !== 1 ? 's' : ''}
                    </span>
                    {#if syncedPairs.length > 0}
                        <span class="opacity-80">
                            — {syncedPairs.map(s => s.replace('-', '/')).join(', ')}
                        </span>
                    {/if}
                </div>
            </InfoBanner>
        {/if}
    </div>

    <!-- Footer -->
    <div class="flex justify-end gap-2 px-6 py-4 border-t border-gray-100 dark:border-slate-700">
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
                disabled={syncing || pairs.length === 0}
            >
                <RefreshCw size={15} class={syncing ? 'animate-spin' : ''} />
                {syncing ? ($t('fx.sync.syncing') ?? 'Syncing...') : ($t('fx.sync.start') ?? 'Start Sync')}
            </button>
        {/if}
    </div>
</ModalBase>
