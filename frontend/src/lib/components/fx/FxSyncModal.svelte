<!--
  FxSyncModal — Modal for syncing FX rates with external providers.
  Shows progress and results of the sync operation.
-->
<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import {zodiosApi} from '$lib/api';
    import {RotateCcw, Check, AlertTriangle} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';

    export let open: boolean = false;
    export let dateStart: string = '';
    export let dateEnd: string = '';

    const dispatch = createEventDispatcher<{
        synced: void;
        close: void;
    }>();

    let syncing = false;
    let result: {synced: number; currencies: string[]} | null = null;
    let error: string | null = null;

    $: if (open) {
        result = null;
        error = null;
    }

    async function handleSync() {
        syncing = true;
        error = null;
        result = null;
        try {
            const response = await zodiosApi.sync_rates_api_v1_fx_currencies_sync_get({
                queries: {start: dateStart, end: dateEnd}
            });
            result = {
                synced: (response as any)?.synced || 0,
                currencies: (response as any)?.currencies || [],
            };
            dispatch('synced');
        } catch (e: any) {
            error = e?.message || 'Sync failed';
        } finally {
            syncing = false;
        }
    }

    function handleClose() {
        dispatch('close');
    }
</script>

<ModalBase {open} onRequestClose={handleClose} maxWidth="md">
    <div class="space-y-4">
        <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">Sync FX Rates</h2>
        <p class="text-sm text-gray-600 dark:text-gray-400">
            Synchronize exchange rates from configured providers for the date range
            <strong>{dateStart}</strong> to <strong>{dateEnd}</strong>.
        </p>

        {#if error}
            <div class="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                <AlertTriangle size={16} class="text-red-500 flex-shrink-0" />
                <span class="text-sm text-red-600 dark:text-red-400">{error}</span>
            </div>
        {/if}

        {#if result}
            <div class="flex items-center gap-2 p-3 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg border border-emerald-200 dark:border-emerald-800">
                <Check size={16} class="text-emerald-500 flex-shrink-0" />
                <span class="text-sm text-emerald-700 dark:text-emerald-400">
                    Synced {result.synced} rate{result.synced !== 1 ? 's' : ''} for {result.currencies.join(', ')}
                </span>
            </div>
        {/if}

        <div class="flex justify-end gap-2 pt-2 border-t border-gray-100 dark:border-slate-700">
            <button class="px-4 py-2 text-sm bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300"
                on:click={handleClose}>
                {result ? 'Close' : 'Cancel'}
            </button>
            {#if !result}
                <button class="flex items-center gap-1.5 px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 disabled:opacity-50"
                    on:click={handleSync} disabled={syncing}>
                    <RotateCcw size={15} class={syncing ? 'animate-spin' : ''} />
                    {syncing ? 'Syncing...' : 'Start Sync'}
                </button>
            {/if}
        </div>
    </div>
</ModalBase>
