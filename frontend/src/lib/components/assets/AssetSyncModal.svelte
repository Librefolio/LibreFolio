<!--
  AssetSyncModal — Thin wrapper around SyncModalBase for Asset price sync.
  Builds a single SyncSection with Asset-specific doSyncFn and resultRow snippet.
-->
<script lang="ts">
    import {zodiosApi} from '$lib/api';
    import {CalendarClock, DollarSign, RotateCw} from 'lucide-svelte';
    import SyncModalBase from '$lib/components/ui/SyncModalBase.svelte';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';
    import {_ as t} from '$lib/i18n';
    import type {SyncResult, SyncSection} from '$lib/utils/syncHelpers';
    import {formatElapsed, STATUS_COLORS, STATUS_ICONS} from '$lib/utils/syncHelpers';
    import {DEFAULT_PROVIDER_COLOR, ensureAssetProvidersCached, getAssetProviderIconUrl, PROVIDER_COLORS} from '$lib/utils/providerHelpers';

    interface AssetSyncItem {
        id: number;
        display_name: string;
        asset_type?: string | null;
        icon_url?: string | null;
        provider_code?: string | null;
    }

    interface Props {
        open: boolean;
        dateStart: string;
        dateEnd: string;
        assets: AssetSyncItem[];
        onsynced: () => void;
        onclose: () => void;
    }

    let {open = $bindable(), dateStart, dateEnd, assets, onsynced, onclose}: Props = $props();

    let syncModalBase: SyncModalBase | undefined = $state(undefined);

    // Build a lookup for quick name/icon resolution from asset id
    let assetMap = $derived(new Map(assets.map((a) => [a.id.toString(), a])));

    // Ensure asset provider icons are cached when modal opens
    $effect(() => {
        if (open) ensureAssetProvidersCached();
    });

    async function doSyncFn(targetIds: string[]): Promise<SyncResult[]> {
        const items = targetIds.map((id) => ({
            asset_id: parseInt(id),
            date_range: {start: dateStart, end: dateEnd},
        }));
        const response = await zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post(items, {timeout: 120 * 1000});
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

    let targetIds = $derived(assets.filter((a) => !!a.provider_code).map((a) => a.id.toString()));

    let sections: SyncSection[] = $derived([
        {
            id: 'assets',
            title: `📊 ${$t('assets.sync.assetsCount') ?? 'Assets'}`,
            doSyncFn,
            targetIds,
            resultRow,
            countLabel: $t('assets.sync.assetsCount') ?? 'assets',
        },
    ]);
</script>

<SyncModalBase
    bind:open
    bind:this={syncModalBase}
    {dateEnd}
    {dateStart}
    description={$t('assets.sync.modalDescription') ?? 'Synchronize prices from configured providers for the selected date range.'}
    {onclose}
    {onsynced}
    {sections}
    testId="asset-sync-modal"
    title={$t('assets.sync.modalTitle') ?? 'Sync Asset Prices'}
></SyncModalBase>

{#snippet resultRow(pr: SyncResult, syncing: boolean)}
    {@const Icon = STATUS_ICONS[pr.status] ?? STATUS_ICONS.failed}
    {@const asset = assetMap.get(pr.id)}
    <div class="flex items-center gap-2 text-xs text-gray-700 dark:text-gray-300 group">
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

        <!-- Asset icon (small) -->
        {#if asset?.icon_url}
            <img src={asset.icon_url} alt="" class="w-4 h-4 rounded-sm object-contain shrink-0" />
        {/if}

        <!-- Asset name -->
        <span class="font-medium truncate max-w-[120px]" title={asset?.display_name ?? pr.id}>
            {asset?.display_name ?? `Asset #${pr.id}`}
        </span>

        {#if pr.status === 'ok' || pr.status === 'partial'}
            <span class="text-gray-400">—</span>
            <span class="inline-flex items-center gap-0.5"><DollarSign size={13} class="text-gray-400 shrink-0" />{pr.points_fetched ?? 0}↓ {pr.points_changed ?? 0}Δ</span>
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
        {/if}

        {#if pr.status === 'skipped' && pr.message}
            <span class="text-gray-400 italic truncate">{pr.message}</span>
        {/if}

        {#if pr.status === 'failed'}
            {@const fullErr = pr.errors?.join('; ') ?? pr.message ?? ''}
            {@const shortErr = pr.errors?.[0] ?? pr.message ?? 'Failed'}
            <!-- #R4-6: Tooltip exposes the full (possibly long) error text that
                 otherwise gets visually clipped by the truncate class inside a
                 narrow flex row. `position="top"` + `maxWidth="500px"` gives a
                 readable popover even for multi-error sync payloads. -->
            <Tooltip text={fullErr} position="top" maxWidth="500px">
                <span class="text-red-400 truncate inline-block max-w-[240px] align-middle">{shortErr}</span>
            </Tooltip>
        {/if}

        {#if pr.elapsed_ms}
            <span class="ml-auto text-gray-400 font-mono tabular-nums text-[10px]">{formatElapsed(pr.elapsed_ms)}</span>
        {/if}
    </div>
{/snippet}
