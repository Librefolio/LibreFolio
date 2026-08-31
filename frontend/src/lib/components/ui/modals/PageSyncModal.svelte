<!--
  PageSyncModal — Combined sync modal for asset detail page.
  Fires asset price sync + FX rate sync in parallel via SyncModalBase sections.
-->
<script lang="ts">
    import {zodiosApi} from '$lib/api';
    import {ArrowLeftRight} from 'lucide-svelte';
    import SyncModalBase from '$lib/components/ui/modals/SyncModalBase.svelte';
    import SyncResultRow from '$lib/components/ui/modals/SyncResultRow.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {_ as t} from '$lib/i18n';
    import type {SyncResult, SyncSection} from '$lib/utils/sync/syncHelpers';
    import {DEFAULT_PROVIDER_COLOR, ensureAssetProvidersCached, getAssetProviderIconUrl, getFxProviderIconUrl, parseProviderChain, PROVIDER_COLORS} from '$lib/utils/providerHelpers';
    import {getCurrencyGraph} from '$lib/stores/currencyGraphStore';
    import {getCurrencyInfo} from '$lib/stores/reference/currencyStore';

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
    <SyncResultRow onRetry={(id) => syncModalBase?.handleRetrySingle(id)} result={pr} {syncing} identity={assetIdentity} provider={assetProvider} />
{/snippet}

{#snippet assetIdentity(pr: SyncResult)}
    {@const asset = assetMap.get(pr.id)}
    {#if asset?.icon_url}
        <img src={asset.icon_url} alt="" class="w-4 h-4 rounded-sm object-contain shrink-0" />
    {:else if asset?.asset_type}
        <img src={getAssetTypeIconUrl(asset.asset_type)} alt="" class="w-4 h-4 object-contain shrink-0" />
    {/if}
    <span class="truncate" title={asset?.display_name ?? pr.id}>{asset?.display_name ?? `Asset #${pr.id}`}</span>
{/snippet}

{#snippet assetProvider(code: string)}
    {@const iconUrl = getAssetProviderIconUrl(code)}
    <span class="inline-flex items-center gap-0.5 px-1 py-0.5 text-[9px] font-medium rounded {PROVIDER_COLORS[code] ?? DEFAULT_PROVIDER_COLOR}" title={code}>
        {#if iconUrl}
            <img src={iconUrl} alt={code} class="w-3.5 h-3.5 rounded-sm object-contain" />
        {:else}
            {code}
        {/if}
    </span>
{/snippet}

<!-- FX result row snippet -->
{#snippet fxResultRow(pr: SyncResult, syncing: boolean)}
    <SyncResultRow countIcon={null} identityWidth="max-w-none" onRetry={(id) => syncModalBase?.handleRetrySingle(id)} result={pr} {syncing} identity={fxIdentity} provider={fxProvider} />
{/snippet}

{#snippet fxIdentity(pr: SyncResult)}
    {@const parts = pr.id.split('-')}
    {@const pairBase = parts[0] ?? ''}
    {@const pairQuote = parts[1] ?? ''}
    <span class="inline-flex items-center gap-0.5 whitespace-nowrap">
        <span class="emoji-flag">{getCurrencyInfo(pairBase).flag_emoji}</span>
        {pairBase}
        <ArrowLeftRight size={10} class="shrink-0 text-gray-400" />
        <span class="emoji-flag">{getCurrencyInfo(pairQuote).flag_emoji}</span>
        {pairQuote}
    </span>
{/snippet}

{#snippet fxProvider(code: string)}
    {@const chain = parseProviderChain(code)}
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
{/snippet}
