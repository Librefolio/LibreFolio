<!--
  PageSyncModal — Combined sync modal for asset detail page.
  Fires asset price sync + FX rate sync in parallel via SyncModalBase sections.
-->
<script lang="ts">
    import {zodiosApi} from '$lib/api';
    import {ArrowLeftRight, CalendarClock, DollarSign, RotateCw} from 'lucide-svelte';
    import SyncModalBase from '$lib/components/ui/modals/SyncModalBase.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {_ as t} from '$lib/i18n';
    import type {SyncResult, SyncSection} from '$lib/utils/syncHelpers';
    import {formatElapsed, STATUS_COLORS, STATUS_ICONS} from '$lib/utils/syncHelpers';
    import {DEFAULT_PROVIDER_COLOR, ensureAssetProvidersCached, getAssetProviderIconUrl, getFxProviderIconUrl, parseProviderChain, PROVIDER_COLORS} from '$lib/utils/providerHelpers';
    import {getCurrencyGraph} from '$lib/stores/currencyGraphStore';
    import {getCurrencyInfo} from '$lib/stores/currencyStore';

    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';

    interface AssetSyncItem {
        id: number;
        display_name: string;
        icon_url?: string | null;
        asset_type?: string | null;
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

    let {open = $bindable(), dateStart, dateEnd, assets, fxPairs, onsynced, onclose}: Props = $props();

    let syncModalBase: SyncModalBase | undefined = $state(undefined);

    // Build asset lookup for rendering
    let assetMap = $derived(new Map(assets.map((a) => [a.id.toString(), a])));

    // Ensure provider icons are cached
    $effect(() => {
        if (open) {
            ensureAssetProvidersCached();
            getCurrencyGraph();
        }
    });

    // =========================================================================
    // Asset sync function
    // =========================================================================

    async function doAssetSync(targetIds: string[]): Promise<SyncResult[]> {
        const items = targetIds.map((id) => ({
            asset_id: parseInt(id),
            date_range: {start: dateStart, end: dateEnd},
        }));
        const response = await zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post(items, {timeout: 120_000});
        const r = response as any;
        return (r.results ?? []).map(
            (ar: any) =>
                ({
                    id: ar.asset_id.toString(),
                    status: ar.status,
                    points_fetched: ar.points_fetched ?? 0,
                    points_changed: ar.points_changed ?? 0,
                    provider_used: ar.provider_used,
                    message: ar.message,
                    errors: ar.errors ?? [],
                    elapsed_ms: ar.elapsed_ms,
                    inserted_count: ar.inserted_count,
                    updated_count: ar.updated_count,
                    events_fetched: ar.events_fetched,
                    events_changed: ar.events_changed,
                }) satisfies SyncResult,
        );
    }

    // =========================================================================
    // FX sync function
    // =========================================================================

    async function doFxSync(targetIds: string[]): Promise<SyncResult[]> {
        const response = await zodiosApi.sync_rates_api_v1_fx_currencies_sync_post({pairs: targetIds, start: dateStart, end: dateEnd}, {timeout: 120_000});
        const r = response as any;
        return (r.results ?? []).map(
            (pr: any) =>
                ({
                    id: pr.pair,
                    status: pr.status,
                    points_fetched: pr.points_fetched ?? 0,
                    points_changed: pr.points_changed ?? 0,
                    provider_used: pr.provider_used,
                    message: pr.message,
                    errors: pr.errors ?? [],
                    elapsed_ms: pr.elapsed_ms,
                    detail: pr.detail,
                }) satisfies SyncResult,
        );
    }

    // =========================================================================
    // Sections
    // =========================================================================

    let assetTargetIds = $derived(assets.filter((a) => !!a.provider_code).map((a) => a.id.toString()));

    let sections: SyncSection[] = $derived([
        {
            id: 'assets',
            title: `📊 ${$t('assets.sync.assetsCount') ?? 'Assets'}`,
            doSyncFn: doAssetSync,
            targetIds: assetTargetIds,
            resultRow: assetResultRow,
            countLabel: $t('assets.sync.assetsCount') ?? 'assets',
        },
        {
            id: 'fx',
            title: `💱 ${$t('fx.sync.pairsCount') ?? 'FX Pairs'}`,
            doSyncFn: doFxSync,
            targetIds: fxPairs,
            resultRow: fxResultRow,
            countLabel: $t('fx.sync.pairsCount') ?? 'pairs',
        },
    ]);
</script>

<SyncModalBase bind:open bind:this={syncModalBase} {dateEnd} {dateStart} description={$t('assetDetail.pageSyncDescription') ?? 'Synchronize asset prices and FX rates for this page.'} {onclose} {onsynced} {sections} testId="page-sync-modal" title={$t('common.sync') ?? 'Sync'}></SyncModalBase>

<!-- Asset result row snippet -->
{#snippet assetResultRow(pr: SyncResult, syncing: boolean)}
    {@const Icon = STATUS_ICONS[pr.status] ?? STATUS_ICONS.failed}
    {@const asset = assetMap.get(pr.id)}
    <div class="flex items-center gap-2 text-xs text-gray-700 dark:text-gray-300">
        {#if (pr.status === 'failed' || pr.status === 'partial') && !syncing}
            <button
                class="shrink-0 p-0.5 rounded transition-colors
                    {pr.status === 'failed' ? 'hover:bg-red-100 dark:hover:bg-red-900/30 text-red-500' : 'hover:bg-amber-100 dark:hover:bg-amber-900/30 text-amber-500'}"
                onclick={() => syncModalBase?.handleRetrySingle(pr.id)}
            >
                <RotateCw size={13} />
            </button>
        {:else}
            <Icon size={14} class="{STATUS_COLORS[pr.status] ?? 'text-gray-400'} shrink-0" />
        {/if}
        {#if asset?.icon_url}
            <img src={asset.icon_url} alt="" class="w-4 h-4 rounded-sm object-contain shrink-0" />
        {:else if asset?.asset_type}
            <img src={getAssetTypeIconUrl(asset.asset_type)} alt="" class="w-4 h-4 object-contain shrink-0" />
        {/if}
        <span class="font-medium truncate max-w-[140px]" title={asset?.display_name ?? pr.id}>
            {asset?.display_name ?? `Asset #${pr.id}`}
        </span>
        {#if pr.status === 'ok' || pr.status === 'partial'}
            <span class="text-gray-400">—</span>
            <span class="inline-flex items-center gap-0.5"><DollarSign size={13} class="text-gray-400 shrink-0" />{pr.points_fetched}↓ {pr.points_changed}Δ</span>
            {#if (pr.events_fetched ?? 0) > 0}
                <span class="text-gray-400">·</span>
                <span class="inline-flex items-center gap-0.5"><CalendarClock size={13} class="text-gray-400 shrink-0" />{pr.events_fetched}↓ {pr.events_changed ?? 0}Δ</span>
            {/if}
            {#if pr.provider_used}
                {@const iconUrl = getAssetProviderIconUrl(pr.provider_used)}
                <span class="inline-flex items-center gap-0.5 px-1 py-0.5 text-[9px] font-medium rounded {PROVIDER_COLORS[pr.provider_used] ?? DEFAULT_PROVIDER_COLOR}" title={pr.provider_used}>
                    {#if iconUrl}
                        <img src={iconUrl} alt={pr.provider_used} class="w-3.5 h-3.5 rounded-sm object-contain" />
                    {:else}
                        {pr.provider_used}
                    {/if}
                </span>
            {/if}
        {:else if pr.status === 'failed'}
            {@const fullErr = pr.errors?.join('; ') ?? pr.message ?? ''}
            {@const shortErr = pr.errors?.[0] ?? pr.message ?? 'Failed'}
            <!-- #R4-6: Tooltip reveals the full error that truncate clips. -->
            <Tooltip text={fullErr} position="top" maxWidth="500px">
                <span class="text-red-400 truncate inline-block max-w-[240px] align-middle">{shortErr}</span>
            </Tooltip>
        {:else if pr.status === 'skipped'}
            <span class="text-gray-400 italic truncate">{pr.message ?? 'Skipped'}</span>
        {/if}
        {#if pr.elapsed_ms}
            <span class="ml-auto text-gray-400 font-mono text-[10px]">{formatElapsed(pr.elapsed_ms)}</span>
        {/if}
    </div>
{/snippet}

<!-- FX result row snippet -->
{#snippet fxResultRow(pr: SyncResult, syncing: boolean)}
    {@const Icon = STATUS_ICONS[pr.status] ?? STATUS_ICONS.failed}
    {@const pairParts = pr.id.split('-')}
    {@const pairBase = pairParts[0] ?? ''}
    {@const pairQuote = pairParts[1] ?? ''}
    <div class="flex items-center gap-2 text-xs text-gray-700 dark:text-gray-300">
        {#if (pr.status === 'failed' || pr.status === 'partial') && !syncing}
            <button
                class="shrink-0 p-0.5 rounded transition-colors
                    {pr.status === 'failed' ? 'hover:bg-red-100 dark:hover:bg-red-900/30 text-red-500' : 'hover:bg-amber-100 dark:hover:bg-amber-900/30 text-amber-500'}"
                onclick={() => syncModalBase?.handleRetrySingle(pr.id)}
            >
                <RotateCw size={13} />
            </button>
        {:else}
            <Icon size={14} class="{STATUS_COLORS[pr.status] ?? 'text-gray-400'} shrink-0" />
        {/if}
        <span class="font-medium inline-flex items-center gap-0.5">
            <span class="emoji-flag">{getCurrencyInfo(pairBase).flag_emoji}</span>
            {pairBase}
            <ArrowLeftRight size={10} class="shrink-0 text-gray-400" />
            <span class="emoji-flag">{getCurrencyInfo(pairQuote).flag_emoji}</span>
            {pairQuote}
        </span>
        {#if pr.status === 'ok' || pr.status === 'partial'}
            <span class="text-gray-400">—</span>
            <span>{pr.points_fetched}↓ {pr.points_changed}Δ</span>
            {#if pr.provider_used}
                {@const chain = parseProviderChain(pr.provider_used)}
                <span class="flex items-center gap-0.5">
                    {#each chain as prov, i}
                        {@const iconUrl = getFxProviderIconUrl(prov)}
                        <span class="inline-flex items-center gap-0.5 px-1 py-0.5 text-[9px] font-medium rounded {PROVIDER_COLORS[prov] ?? DEFAULT_PROVIDER_COLOR}" title={prov}>
                            {#if iconUrl}
                                <img src={iconUrl} alt={prov} class="w-3.5 h-3.5 rounded-sm object-contain" />
                            {:else}
                                {prov}
                            {/if}
                        </span>
                        {#if i < chain.length - 1}
                            <span class="text-gray-400 text-[8px]">→</span>
                        {/if}
                    {/each}
                </span>
            {/if}
        {:else if pr.status === 'failed'}
            {@const fullErr = pr.errors?.join('; ') ?? pr.message ?? ''}
            {@const shortErr = pr.errors?.[0] ?? pr.message ?? 'Failed'}
            <!-- #R4-6: Tooltip reveals the full error that truncate clips. -->
            <Tooltip text={fullErr} position="top" maxWidth="500px">
                <span class="text-red-400 truncate inline-block max-w-[240px] align-middle">{shortErr}</span>
            </Tooltip>
        {:else if pr.status === 'skipped'}
            <span class="text-gray-400 italic truncate">{pr.message ?? 'Skipped'}</span>
        {/if}
        {#if pr.elapsed_ms}
            <span class="ml-auto text-gray-400 font-mono text-[10px]">{formatElapsed(pr.elapsed_ms)}</span>
        {/if}
    </div>
{/snippet}
