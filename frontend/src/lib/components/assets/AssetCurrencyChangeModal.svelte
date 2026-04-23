<!--
  AssetCurrencyChangeModal.svelte - Destructive-confirm modal for currency change (I.6).

  Opens when PATCH /assets returns a per-item result with the structured blocker
  message "CURRENCY_CHANGE_BLOCKED_BY_PRICES|count=N|oldest=...|newest=...|from=X|to=Y".

  Flow:
  1. Show count + date range + from/to currencies.
  2. Offer 2 export buttons (CSV / JSON) for pre-wipe backup.
  3. On "Delete & Change" confirm:
     a. DELETE /assets/prices  (range oldest..newest)
     b. PATCH /assets           (now succeeds - no prices remain)
     c. POST /assets/prices/sync (if provider assigned) with same oldest..today range
  4. Each step shows a progress toast; failure surfaces error toast.

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {AlertTriangle, Download, X} from 'lucide-svelte';
    import {get} from 'svelte/store';
    import {zodiosApi} from '$lib/api';
    import {toasts} from '$lib/stores/toastStore.svelte';
    import {_ as t} from '$lib/i18n';
    import {buildAssetSyncToast} from '$lib/utils/syncToastHelpers';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';

    interface BlockerInfo {
        assetId: number;
        count: number;
        oldest: string;
        newest: string;
        from: string;
        to: string;
    }

    interface Props {
        /** Modal open flag (bindable). */
        open: boolean;
        /** Parsed blocker info from the PATCH 409 message. */
        blocker: BlockerInfo | null;
        /**
         * Serialized payload that PATCH attempted (minus currency override already in `blocker.to`).
         * The modal re-submits this via a full PATCH after wipe, with `currency=blocker.to`.
         */
        patchPayload: Record<string, unknown> | null;
        /** Provider code on the asset (or null): if set, auto-sync is triggered after patch. */
        providerAssigned: boolean;
        /** Called after the full wipe/patch/sync chain succeeds. */
        onconfirmed?: () => void;
        /** Called when the user cancels the destructive flow. */
        oncanceled?: () => void;
    }

    let {open = $bindable(), blocker, patchPayload, providerAssigned, onconfirmed, oncanceled}: Props = $props();

    let inProgress = $state(false);
    /**
     * I-bis #12 — inline progress step instead of 3 transient toasts.
     * null = idle, otherwise shows next to the confirm button.
     */
    let progressStep = $state<null | 'delete' | 'patch' | 'sync'>(null);

    function exportPrices(format: 'csv' | 'json') {
        if (!blocker) return;
        // Cookie-based auth: a plain link with Content-Disposition is enough.
        const url = `/api/v1/assets/prices/${blocker.assetId}/export?format=${format}`;
        window.open(url, '_blank');
    }

    async function handleConfirm() {
        if (!blocker || !patchPayload) return;
        inProgress = true;
        progressStep = null;
        const tr = get(t);

        try {
            // Step 1: delete all prices in the range (inline spinner, no toast)
            progressStep = 'delete';
            await zodiosApi.delete_prices_bulk_api_v1_assets_prices_delete([
                {
                    asset_id: blocker.assetId,
                    date_ranges: [{start: blocker.oldest, end: blocker.newest}],
                },
            ]);
            // Toast #1 — delete success
            toasts.success(tr('assetDetail.currencyChange.deleteSuccess', {values: {count: blocker.count}}));

            // Step 2: retry PATCH (now succeeds because no prices remain)
            progressStep = 'patch';
            await zodiosApi.patch_assets_bulk_api_v1_assets_patch([patchPayload] as any);
            // Toast #2 — currency change success (always fired when delete+patch
            // succeed). The separate sync toast below reports its own outcome.
            toasts.success(tr('assetDetail.currencyChange.changedTo', {values: {from: blocker.from, to: blocker.to}}));

            // Step 3: auto-sync from provider using original oldest date as start
            if (providerAssigned) {
                progressStep = 'sync';
                const today = new Date().toISOString().slice(0, 10);
                try {
                    const syncResponse: any = await zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post([
                        {
                            asset_id: blocker.assetId,
                            date_range: {start: blocker.oldest, end: today},
                        },
                    ]);
                    // Toast #3 — unified sync outcome (ok / noChanges / partial / skipped / error).
                    // This surfaces the real provider error (e.g. "Currency mismatch ...")
                    // via result.message, instead of a generic "sync failed, retry manually".
                    const r = syncResponse?.results?.[0];
                    if (r) {
                        const toast = buildAssetSyncToast(r, tr('common.sync'), tr);
                        toasts[toast.variant](toast.message);
                    } else {
                        toasts.error(`${tr('common.sync')} — ${tr('prices.sync.noResponse')}`);
                    }
                } catch (syncErr: any) {
                    // Network / HTTP error on sync — surface the detail so the user
                    // knows why (e.g. backend 400 "Currency mismatch for asset...").
                    console.error('Post-wipe auto-sync failed:', syncErr);
                    const detail = syncErr?.response?.data?.detail || syncErr?.message || 'unknown error';
                    toasts.error(`${tr('common.sync')}: ${detail}`);
                }
            }

            open = false;
            onconfirmed?.();
        } catch (err: any) {
            console.error('Currency change flow failed:', err);
            const msg = err?.response?.data?.detail || err?.message || 'unknown error';
            toasts.error(`${$t('assetDetail.currencyChange.failed')}: ${msg}`);
        } finally {
            inProgress = false;
            progressStep = null;
        }
    }

    function handleCancel() {
        if (inProgress) return;
        open = false;
        oncanceled?.();
    }
</script>

{#if open && blocker}
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" role="dialog" aria-modal="true" aria-labelledby="currency-change-title">
        <div class="bg-white dark:bg-slate-800 rounded-xl shadow-2xl border-2 border-red-300 dark:border-red-700 max-w-lg w-full mx-4 overflow-hidden">
            <!-- Header -->
            <div class="flex items-center gap-3 px-5 py-4 bg-red-50 dark:bg-red-900/30 border-b border-red-200 dark:border-red-800">
                <AlertTriangle class="text-red-600 dark:text-red-400 flex-shrink-0" size={22} />
                <h2 id="currency-change-title" class="text-base font-semibold text-red-700 dark:text-red-300">
                    {$t('assetDetail.currencyChange.title')}
                </h2>
                <button type="button" class="ml-auto p-1 rounded text-red-500 hover:bg-red-100 dark:hover:bg-red-900/50 transition-colors disabled:opacity-50" onclick={handleCancel} disabled={inProgress} aria-label={$t('common.cancel')}>
                    <X size={18} />
                </button>
            </div>

            <!-- Body -->
            <div class="px-5 py-4 space-y-4 text-sm">
                <p class="text-gray-700 dark:text-gray-200">
                    {$t('assetDetail.currencyChange.body', {
                        values: {
                            from: blocker.from,
                            to: blocker.to,
                            count: blocker.count,
                            oldest: blocker.oldest,
                            today: new Date().toISOString().slice(0, 10),
                        },
                    })}
                </p>

                {#if providerAssigned}
                    <InfoBanner variant="info">
                        {$t('assetDetail.currencyChange.autoSyncInfo', {values: {from: blocker.oldest}})}
                    </InfoBanner>
                {:else}
                    <InfoBanner variant="warning">
                        {$t('assetDetail.currencyChange.noProviderInfo')}
                    </InfoBanner>
                {/if}

                <!-- Backup section -->
                <div class="rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/40 p-3">
                    <div class="text-xs font-semibold text-slate-600 dark:text-slate-400 mb-2">
                        {$t('assetDetail.currencyChange.backupTitle')}
                    </div>
                    <div class="flex gap-2 flex-wrap">
                        <button
                            type="button"
                            class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded hover:bg-slate-100 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 transition-colors"
                            onclick={() => exportPrices('csv')}
                            disabled={inProgress}
                        >
                            <Download size={13} />
                            {$t('assetDetail.currencyChange.exportCsv')}
                        </button>
                        <button
                            type="button"
                            class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded hover:bg-slate-100 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 transition-colors"
                            onclick={() => exportPrices('json')}
                            disabled={inProgress}
                        >
                            <Download size={13} />
                            {$t('assetDetail.currencyChange.exportJson')}
                        </button>
                    </div>
                </div>
            </div>

            <!-- Footer -->
            <div class="flex justify-end gap-2 px-5 py-3 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/30">
                {#if inProgress && progressStep}
                    <!-- I-bis #12 — inline progress step (replaces the 3 progress toasts) -->
                    <span class="mr-auto flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300" data-testid="currency-change-progress-step">
                        <span class="inline-block h-3 w-3 rounded-full border-2 border-slate-400 border-t-transparent animate-spin"></span>
                        {#if progressStep === 'delete'}
                            {$t('assetDetail.currencyChange.progressDelete', {values: {count: blocker.count}})}
                        {:else if progressStep === 'patch'}
                            {$t('assetDetail.currencyChange.progressPatch')}
                        {:else if progressStep === 'sync'}
                            {$t('assetDetail.currencyChange.progressSync', {values: {from: blocker.oldest}})}
                        {/if}
                    </span>
                {/if}
                <button type="button" class="px-4 py-2 text-sm bg-slate-200 dark:bg-slate-600 text-slate-700 dark:text-slate-200 rounded hover:bg-slate-300 dark:hover:bg-slate-500 transition-colors disabled:opacity-50" onclick={handleCancel} disabled={inProgress}>
                    {$t('common.cancel')}
                </button>
                <button type="button" class="px-4 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed" onclick={handleConfirm} disabled={inProgress} data-testid="currency-change-confirm">
                    {inProgress ? $t('assetDetail.currencyChange.working') : $t('assetDetail.currencyChange.confirm')}
                </button>
            </div>
        </div>
    </div>
{/if}
