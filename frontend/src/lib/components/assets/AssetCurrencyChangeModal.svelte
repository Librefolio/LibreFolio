<!--
  AssetCurrencyChangeModal.svelte — Destructive-confirm modal for currency change
  (I.6 + R3-3 Policy D).

  Opens when PATCH /assets returns a per-item result with the structured blocker
  token:
    "CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA|prices=N|events_manual=M|
     events_provider=K|linked_tx=L|oldest=...|newest=...|from=X|to=Y"

  Policy D (symmetric wipe + linked-tx disconnect):
  1. Show a summary of everything that will be deleted/disconnected:
     N prices (oldest..newest range) + M manual events + K provider events
     + L linked transactions that will be DISCONNECTED (but NOT deleted).
  2. Offer export buttons (CSV / JSON) for both prices and events so the
     user can keep a local snapshot before destruction.
  3. On "Delete & Change" confirm:
     a. POST /assets/{id}/market-data/wipe  (single atomic step: wipe prices
        + wipe events + SET asset_event_id=NULL on linked transactions +
        cache invalidate).
     b. PATCH /assets                        (now succeeds — no residual
        market data blocks the change).
     c. POST /assets/prices/sync             (if provider assigned; repopulates
        the series in the new currency).

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {AlertTriangle, Download, X} from 'lucide-svelte';
    import {get} from 'svelte/store';
    import {zodiosApi} from '$lib/api';
    import {downloadAssetBackup, type BackupFormat, type BackupKind} from '$lib/api/backupDownload';
    import {toasts} from '$lib/stores/toastStore.svelte';
    import {_ as t} from '$lib/i18n';
    import {buildAssetSyncToast} from '$lib/utils/syncToastHelpers';
    import {extractErrorMessage} from '$lib/utils/trySave';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';

    interface BlockerInfo {
        assetId: number;
        /** Number of rows in price_history for this asset. */
        prices: number;
        /** Manual events (provider_assignment_id IS NULL). */
        eventsManual: number;
        /** Auto-generated events (provider_assignment_id IS NOT NULL). */
        eventsProvider: number;
        /** Transactions still linked to one of the events (will be disconnected, not deleted). */
        linkedTx: number;
        /** Oldest date in price_history (empty if no prices). */
        oldest: string;
        /** Newest date in price_history (empty if no prices). */
        newest: string;
        /** Current currency (e.g. "USD"). */
        from: string;
        /** Target currency (e.g. "EUR"). */
        to: string;
    }

    interface Props {
        open: boolean;
        blocker: BlockerInfo | null;
        patchPayload: Record<string, unknown> | null;
        providerAssigned: boolean;
        onconfirmed?: () => void;
        oncanceled?: () => void;
    }

    let {open = $bindable(), blocker, patchPayload, providerAssigned, onconfirmed, oncanceled}: Props = $props();

    let inProgress = $state(false);
    /** Inline progress step (replaces the old 3-toast progress chain, I-bis #12). */
    let progressStep = $state<null | 'wipe' | 'patch' | 'sync'>(null);

    /** Total events count (manual + provider) — convenient for the copy in the body. */
    const totalEvents = $derived(blocker ? blocker.eventsManual + blocker.eventsProvider : 0);

    async function exportBackup(kind: BackupKind, format: BackupFormat) {
        if (!blocker) return;
        // Uses the shared axiosInstance (cookie auth + 401 interceptor +
        // Accept-Language) instead of a raw ``window.open`` so every request
        // flows through the same pipeline as the rest of the Zodios client.
        // The backend picks the filename via ``Content-Disposition`` — we
        // just surface any HTTP error as a toast.
        try {
            await downloadAssetBackup(blocker.assetId, kind, format);
        } catch (err: unknown) {
            // I-bis #22 — use centralised ``extractErrorMessage`` so FastAPI
            // ``detail`` (string / object / Pydantic array) surfaces uniformly.
            const detail = extractErrorMessage(err, 'unknown error');
            console.error(`[backup] ${kind}/${format}`, detail, err);
            toasts.error(`${$t('assetDetail.currencyChange.backupTitle')}: ${detail}`);
        }
    }

    async function handleConfirm() {
        if (!blocker || !patchPayload) return;
        inProgress = true;
        progressStep = null;
        const tr = get(t);

        try {
            // Step 1: single atomic wipe (prices + events + linked-tx disconnect).
            progressStep = 'wipe';
            await zodiosApi.wipe_market_data_api_v1_assets__asset_id__market_data_wipe_post(undefined, {
                params: {asset_id: blocker.assetId},
            });
            toasts.success(
                tr('assetDetail.currencyChange.wipeSuccess', {
                    values: {
                        prices: blocker.prices,
                        events: totalEvents,
                        linkedTx: blocker.linkedTx,
                    },
                }),
            );

            // Step 2: retry PATCH (now succeeds — no residual market data).
            progressStep = 'patch';
            await zodiosApi.patch_assets_bulk_api_v1_assets_patch([patchPayload] as any);
            toasts.success(tr('assetDetail.currencyChange.changedTo', {values: {from: blocker.from, to: blocker.to}}));

            // Step 3: auto-sync (only if provider assigned AND we had prices to begin with).
            if (providerAssigned && blocker.oldest) {
                progressStep = 'sync';
                const today = new Date().toISOString().slice(0, 10);
                try {
                    const syncResponse: any = await zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post([
                        {
                            asset_id: blocker.assetId,
                            date_range: {start: blocker.oldest, end: today},
                        },
                    ]);
                    const r = syncResponse?.results?.[0];
                    if (r) {
                        const toast = buildAssetSyncToast(r, tr('common.sync'), tr);
                        toasts[toast.variant](toast.message);
                    } else {
                        toasts.error(`${tr('common.sync')} — ${tr('prices.sync.noResponse')}`);
                    }
                } catch (syncErr: unknown) {
                    // I-bis #22 — unified error extraction; the modal does
                    // NOT close on sync failure (the PATCH itself succeeded).
                    const detail = extractErrorMessage(syncErr, 'unknown error');
                    console.error('[currency-change] post-wipe auto-sync failed', detail, syncErr);
                    toasts.error(`${tr('common.sync')}: ${detail}`);
                }
            }

            open = false;
            onconfirmed?.();
        } catch (err: unknown) {
            // I-bis #22 — wipe or PATCH failed: keep the modal open so the
            // user can retry or cancel; surface the detail via toast.
            const msg = extractErrorMessage(err, 'unknown error');
            console.error('[currency-change] flow failed', msg, err);
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
                    {$t('assetDetail.currencyChange.title', {values: {from: blocker.from, to: blocker.to}})}
                </h2>
                <button type="button" class="ml-auto p-1 rounded text-red-500 hover:bg-red-100 dark:hover:bg-red-900/50 transition-colors disabled:opacity-50" onclick={handleCancel} disabled={inProgress} aria-label={$t('common.cancel')}>
                    <X size={18} />
                </button>
            </div>

            <!-- Body -->
            <div class="px-5 py-4 space-y-4 text-sm">
                <p class="text-gray-700 dark:text-gray-200">
                    {$t('assetDetail.currencyChange.bodyIntro')}
                </p>
                <p class="text-red-700 dark:text-red-300 font-medium">
                    {$t('assetDetail.currencyChange.bodyCaveat')}
                </p>

                <!-- What will be wiped / disconnected (R3-3 Policy D) -->
                <ul class="text-xs text-slate-700 dark:text-slate-300 bg-red-50/60 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-md p-3 space-y-1 list-disc list-inside">
                    {#if blocker.prices > 0}
                        <li>{$t('assetDetail.currencyChange.summaryPrices', {values: {count: blocker.prices, oldest: blocker.oldest, newest: blocker.newest}})}</li>
                    {/if}
                    {#if blocker.eventsManual + blocker.eventsProvider > 0}
                        <li>
                            {$t('assetDetail.currencyChange.summaryEvents', {
                                values: {manual: blocker.eventsManual, provider: blocker.eventsProvider},
                            })}
                        </li>
                    {/if}
                    {#if blocker.linkedTx > 0}
                        <li class="font-medium text-red-700 dark:text-red-300">
                            {$t('assetDetail.currencyChange.summaryLinkedTx', {values: {count: blocker.linkedTx}})}
                        </li>
                    {/if}
                </ul>

                {#if providerAssigned && blocker.oldest}
                    <InfoBanner variant="info">
                        {$t('assetDetail.currencyChange.autoSyncInfo', {values: {from: blocker.oldest}})}
                    </InfoBanner>
                {:else if !providerAssigned}
                    <InfoBanner variant="warning">
                        {$t('assetDetail.currencyChange.noProviderInfo')}
                    </InfoBanner>
                {/if}

                <!-- Backup section — R3-3b: prices + events -->
                <div class="rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/40 p-3">
                    <div class="text-xs font-semibold text-slate-600 dark:text-slate-400 mb-2">
                        {$t('assetDetail.currencyChange.backupTitle')}
                    </div>
                    <div class="flex gap-2 flex-wrap">
                        {#if blocker.prices > 0}
                            <button
                                type="button"
                                class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded hover:bg-slate-100 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 transition-colors"
                                onclick={() => exportBackup('prices', 'csv')}
                                disabled={inProgress}
                            >
                                <Download size={13} />
                                {$t('assetDetail.currencyChange.exportPricesCsv')}
                            </button>
                            <button
                                type="button"
                                class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded hover:bg-slate-100 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 transition-colors"
                                onclick={() => exportBackup('prices', 'json')}
                                disabled={inProgress}
                            >
                                <Download size={13} />
                                {$t('assetDetail.currencyChange.exportPricesJson')}
                            </button>
                        {/if}
                        {#if totalEvents > 0}
                            <button
                                type="button"
                                class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded hover:bg-slate-100 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 transition-colors"
                                onclick={() => exportBackup('events', 'csv')}
                                disabled={inProgress}
                            >
                                <Download size={13} />
                                {$t('assetDetail.currencyChange.exportEventsCsv')}
                            </button>
                            <button
                                type="button"
                                class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded hover:bg-slate-100 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 transition-colors"
                                onclick={() => exportBackup('events', 'json')}
                                disabled={inProgress}
                            >
                                <Download size={13} />
                                {$t('assetDetail.currencyChange.exportEventsJson')}
                            </button>
                        {/if}
                    </div>
                </div>
            </div>

            <!-- Footer -->
            <div class="flex justify-end gap-2 px-5 py-3 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/30">
                {#if inProgress && progressStep}
                    <span class="mr-auto flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300" data-testid="currency-change-progress-step">
                        <span class="inline-block h-3 w-3 rounded-full border-2 border-slate-400 border-t-transparent animate-spin"></span>
                        {#if progressStep === 'wipe'}
                            {$t('assetDetail.currencyChange.progressWipe', {values: {prices: blocker.prices, events: totalEvents, linkedTx: blocker.linkedTx}})}
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
