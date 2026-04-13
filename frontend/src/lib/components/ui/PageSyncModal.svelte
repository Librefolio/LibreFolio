<!--
  PageSyncModal — Combined sync modal for asset detail page.
  Fires asset price sync + FX rate sync in parallel, shows results in 2 sections.
  Uses ModalBase directly (not SyncModalBase) because it orchestrates 2 independent syncs.
-->
<script lang="ts">
    import {zodiosApi} from '$lib/api';
    import {RotateCw, RefreshCw} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import {_ as t} from '$lib/i18n';
    import type {SyncResult} from '$lib/utils/syncHelpers';
    import {formatElapsed, STATUS_COLORS, STATUS_ICONS} from '$lib/utils/syncHelpers';
    import {ensureAssetProvidersCached, getAssetProviderIconUrl, DEFAULT_PROVIDER_COLOR, PROVIDER_COLORS} from '$lib/utils/providerHelpers';

    interface AssetSyncItem {
        id: number;
        display_name: string;
        icon_url?: string | null;
        provider_code?: string | null;
    }

    interface Props {
        open: boolean;
        dateStart: string;
        dateEnd: string;
        /** Assets to sync (main + comparison with provider) */
        assets: AssetSyncItem[];
        /** FX pair slugs to sync (only configured ones) */
        fxPairs: string[];
        /** Called after all syncs complete */
        onsynced: () => void;
        onclose: () => void;
    }

    let {
        open = $bindable(),
        dateStart,
        dateEnd,
        assets,
        fxPairs,
        onsynced,
        onclose,
    }: Props = $props();

    let syncing = $state(false);
    let assetResults = $state<SyncResult[]>([]);
    let fxResults = $state<SyncResult[]>([]);
    let done = $state(false);

    // Build asset lookup for rendering
    let assetMap = $derived(new Map(assets.map(a => [a.id.toString(), a])));

    // Ensure provider icons are cached
    $effect(() => { if (open) ensureAssetProvidersCached(); });

    // Auto-start sync when modal opens
    $effect(() => {
        if (open && !syncing && !done) {
            startSync();
        }
    });

    async function startSync() {
        syncing = true;
        assetResults = [];
        fxResults = [];
        done = false;

        const promises: Promise<void>[] = [];

        // Asset sync
        if (assets.length > 0) {
            const assetIds = assets.filter(a => !!a.provider_code).map(a => a.id);
            if (assetIds.length > 0) {
                promises.push(
                    zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post(
                        assetIds.map(id => ({asset_id: id, date_range: {start: dateStart, end: dateEnd}})),
                        {timeout: 120_000},
                    ).then((response: any) => {
                        assetResults = (response.results ?? []).map((ar: any) => ({
                            id: ar.asset_id.toString(),
                            status: ar.status,
                            points_fetched: ar.points_fetched ?? 0,
                            points_changed: ar.points_changed ?? 0,
                            provider_used: ar.provider_used,
                            message: ar.message,
                            errors: ar.errors ?? [],
                            elapsed_ms: ar.elapsed_ms,
                        } satisfies SyncResult));
                    }).catch((e: any) => {
                        assetResults = assetIds.map(id => ({
                            id: id.toString(),
                            status: 'failed' as const,
                            points_fetched: 0,
                            points_changed: 0,
                            errors: [e?.message || 'Unknown error'],
                        }));
                    })
                );
            }
        }

        // FX sync
        if (fxPairs.length > 0) {
            promises.push(
                zodiosApi.sync_rates_api_v1_fx_currencies_sync_post(
                    {pairs: fxPairs, start: dateStart, end: dateEnd},
                    {timeout: 120_000},
                ).then((response: any) => {
                    fxResults = (response.results ?? []).map((pr: any) => ({
                        id: pr.pair,
                        status: pr.status,
                        points_fetched: pr.points_fetched ?? 0,
                        points_changed: pr.points_changed ?? 0,
                        provider_used: pr.provider_used,
                        message: pr.message,
                        errors: pr.errors ?? [],
                        elapsed_ms: pr.elapsed_ms,
                    } satisfies SyncResult));
                }).catch((e: any) => {
                    fxResults = fxPairs.map(slug => ({
                        id: slug,
                        status: 'failed' as const,
                        points_fetched: 0,
                        points_changed: 0,
                        errors: [e?.message || 'Unknown error'],
                    }));
                })
            );
        }

        await Promise.all(promises);
        syncing = false;
        done = true;
    }

    function handleClose() {
        if (done) onsynced();
        open = false;
        // Reset state for next open
        done = false;
        assetResults = [];
        fxResults = [];
        onclose();
    }
</script>

<ModalBase bind:open onRequestClose={handleClose} testId="page-sync-modal">
    <div class="space-y-4 p-5 max-w-lg">
        <!-- Header -->
        <div class="flex items-center gap-3">
            <div class="p-2 rounded-lg bg-amber-100 dark:bg-amber-900/30">
                <RefreshCw size={18} class="text-amber-600 dark:text-amber-400 {syncing ? 'animate-spin' : ''}"/>
            </div>
            <div>
                <h3 class="text-base font-semibold text-gray-800 dark:text-gray-100">{$t('common.sync')}</h3>
                <p class="text-xs text-gray-500 dark:text-gray-400">
                    {assets.length} asset{assets.length !== 1 ? 's' : ''} · {fxPairs.length} FX pair{fxPairs.length !== 1 ? 's' : ''}
                </p>
            </div>
        </div>

        <!-- Date range info -->
        <div class="text-xs text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-slate-800 rounded px-3 py-1.5 font-mono">
            {dateStart} → {dateEnd}
        </div>

        <!-- Asset results section -->
        {#if assets.length > 0}
            <div>
                <h4 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                    📊 Assets ({assetResults.length}/{assets.filter(a => !!a.provider_code).length})
                </h4>
                <div class="space-y-1.5">
                    {#each assetResults as pr (pr.id)}
                        {@const Icon = STATUS_ICONS[pr.status] ?? STATUS_ICONS.failed}
                        {@const asset = assetMap.get(pr.id)}
                        <div class="flex items-center gap-2 text-xs text-gray-700 dark:text-gray-300">
                            <Icon size={14} class="{STATUS_COLORS[pr.status] ?? 'text-gray-400'} shrink-0"/>
                            {#if asset?.icon_url}
                                <img src={asset.icon_url} alt="" class="w-4 h-4 rounded-sm object-contain shrink-0"/>
                            {/if}
                            <span class="font-medium truncate max-w-[140px]" title={asset?.display_name ?? pr.id}>
                                {asset?.display_name ?? `Asset #${pr.id}`}
                            </span>
                            {#if pr.status === 'ok' || pr.status === 'partial'}
                                <span class="text-gray-400">—</span>
                                <span>{pr.points_fetched}↓ {pr.points_changed}Δ</span>
                                {#if pr.provider_used}
                                    {@const iconUrl = getAssetProviderIconUrl(pr.provider_used)}
                                    <span class="inline-flex items-center gap-0.5 px-1 py-0.5 text-[9px] font-medium rounded {PROVIDER_COLORS[pr.provider_used] ?? DEFAULT_PROVIDER_COLOR}">
                                        {#if iconUrl}
                                            <img src={iconUrl} alt={pr.provider_used} class="w-3.5 h-3.5 rounded-sm object-contain"/>
                                        {:else}
                                            {pr.provider_used}
                                        {/if}
                                    </span>
                                {/if}
                            {:else if pr.status === 'failed'}
                                <span class="text-red-400 truncate">{pr.errors?.[0] ?? pr.message ?? 'Failed'}</span>
                            {:else if pr.status === 'skipped'}
                                <span class="text-gray-400 italic truncate">{pr.message ?? 'Skipped'}</span>
                            {/if}
                            {#if pr.elapsed_ms}
                                <span class="ml-auto text-gray-400 font-mono text-[10px]">{formatElapsed(pr.elapsed_ms)}</span>
                            {/if}
                        </div>
                    {/each}
                    {#if syncing && assetResults.length === 0}
                        <div class="flex items-center gap-2 text-xs text-gray-400">
                            <RotateCw size={12} class="animate-spin"/> {$t('common.syncing')}…
                        </div>
                    {/if}
                </div>
            </div>
        {/if}

        <!-- FX results section -->
        {#if fxPairs.length > 0}
            <div>
                <h4 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                    💱 FX Pairs ({fxResults.length}/{fxPairs.length})
                </h4>
                <div class="space-y-1.5">
                    {#each fxResults as pr (pr.id)}
                        {@const Icon = STATUS_ICONS[pr.status] ?? STATUS_ICONS.failed}
                        <div class="flex items-center gap-2 text-xs text-gray-700 dark:text-gray-300">
                            <Icon size={14} class="{STATUS_COLORS[pr.status] ?? 'text-gray-400'} shrink-0"/>
                            <span class="font-medium font-mono">{pr.id.replace('-', '/')}</span>
                            {#if pr.status === 'ok' || pr.status === 'partial'}
                                <span class="text-gray-400">—</span>
                                <span>{pr.points_fetched}↓ {pr.points_changed}Δ</span>
                                {#if pr.provider_used}
                                    <span class="text-[9px] text-gray-400">{pr.provider_used}</span>
                                {/if}
                            {:else if pr.status === 'failed'}
                                <span class="text-red-400 truncate">{pr.errors?.[0] ?? pr.message ?? 'Failed'}</span>
                            {:else if pr.status === 'skipped'}
                                <span class="text-gray-400 italic truncate">{pr.message ?? 'Skipped'}</span>
                            {/if}
                            {#if pr.elapsed_ms}
                                <span class="ml-auto text-gray-400 font-mono text-[10px]">{formatElapsed(pr.elapsed_ms)}</span>
                            {/if}
                        </div>
                    {/each}
                    {#if syncing && fxResults.length === 0}
                        <div class="flex items-center gap-2 text-xs text-gray-400">
                            <RotateCw size={12} class="animate-spin"/> {$t('common.syncing')}…
                        </div>
                    {/if}
                </div>
            </div>
        {/if}

        <!-- Footer -->
        <div class="flex justify-end gap-2 pt-2 border-t border-gray-100 dark:border-slate-700">
            <button
                class="px-4 py-2 text-sm rounded-lg transition-colors
                       {done ? 'bg-libre-green text-white hover:bg-libre-green/90' : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200'}"
                onclick={handleClose}
            >
                {done ? $t('common.close') : $t('common.cancel')}
            </button>
        </div>
    </div>
</ModalBase>

