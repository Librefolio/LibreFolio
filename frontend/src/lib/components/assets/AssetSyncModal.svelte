<!--
  AssetSyncModal — Thin wrapper around SyncModalBase for Asset price sync.
  Builds a single SyncSection with Asset-specific doSyncFn and resultRow snippet.
-->
<script lang="ts">
    import {zodiosApi} from '$lib/api';
    import SyncModalBase from '$lib/components/ui/modals/SyncModalBase.svelte';
    import SyncResultRow from '$lib/components/ui/modals/SyncResultRow.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {_ as t} from '$lib/i18n';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {writeExportToClipboard} from '$lib/utils/clipboard';
    import type {SyncResult, SyncSection} from '$lib/utils/sync/syncHelpers';
    import {DEFAULT_PROVIDER_COLOR, ensureAssetProvidersCached, getAssetProviderIconUrl, PROVIDER_COLORS} from '$lib/utils/providerHelpers';
    import {clearTimer} from '$lib/utils/core/clearTimer';

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
    let longPressTimer: ReturnType<typeof setTimeout> | null = null;

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

    async function copyErrorToClipboard(text: string) {
        await writeExportToClipboard(text, toasts, $t('common.copiedToClipboard'));
    }

    function handleTouchStart(text: string) {
        longPressTimer = setTimeout(() => copyErrorToClipboard(text), 500);
    }

    function handleTouchEnd() {
        longPressTimer = clearTimer(longPressTimer);
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
    maxWidth="max-w-3xl"
    {onclose}
    {onsynced}
    {sections}
    testId="asset-sync-modal"
    title={$t('assets.sync.modalTitle') ?? 'Sync Asset Prices'}
></SyncModalBase>

{#snippet resultRow(pr: SyncResult, syncing: boolean)}
    <SyncResultRow identityWidth="max-w-[120px]" onRetry={(id) => syncModalBase?.handleRetrySingle(id)} result={pr} {syncing} {identity} {provider} />
{/snippet}

{#snippet identity(pr: SyncResult)}
    {@const asset = assetMap.get(pr.id)}
    {#if asset?.icon_url}
        <img src={asset.icon_url} alt="" class="w-4 h-4 rounded-sm object-contain shrink-0" />
    {/if}
    <span class="truncate" title={asset?.display_name ?? pr.id}>{asset?.display_name ?? `Asset #${pr.id}`}</span>
{/snippet}

{#snippet provider(code: string)}
    {@const iconUrl = getAssetProviderIconUrl(code)}
    <span class="inline-flex items-center gap-0.5 px-1 py-0.5 text-[9px] font-medium rounded {PROVIDER_COLORS[code] ?? DEFAULT_PROVIDER_COLOR}" title={code}>
        {#if iconUrl}
            <img src={iconUrl} alt={code} class="w-3.5 h-3.5 rounded-sm object-contain" />
        {:else}
            {code}
        {/if}
    </span>
{/snippet}
