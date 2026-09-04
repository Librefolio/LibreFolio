<!--
  FxSyncModal — Thin wrapper around SyncModalBase for FX pair sync.
  Builds a single SyncSection with FX-specific doSyncFn and resultRow snippet.
-->
<script lang="ts">
    import {zodiosApi} from '$lib/api';
    import {ArrowLeftRight} from 'lucide-svelte';
    import SyncModalBase from '$lib/components/ui/modals/SyncModalBase.svelte';
    import SyncResultRow from '$lib/components/ui/modals/SyncResultRow.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {_ as t} from '$lib/i18n';
    import {get} from 'svelte/store';
    import type {SyncResult, SyncSection} from '$lib/utils/sync/syncHelpers';
    import {DEFAULT_PROVIDER_COLOR, formatSyncDetail, getFxProviderIconUrl, parseProviderChain, PROVIDER_COLORS} from '$lib/utils/providerHelpers';
    import {getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {getCurrencyGraph} from '$lib/stores/currencyGraphStore';

    interface Props {
        open: boolean;
        dateStart: string;
        dateEnd: string;
        pairs: string[];
        onsynced: () => void;
        onclose: () => void;
        /** z-index for stacking above other modals */
        zIndex?: number;
    }

    let {open = $bindable(), dateStart, dateEnd, pairs, onsynced, onclose, zIndex = 50}: Props = $props();

    let syncModalBase: SyncModalBase | undefined = $state(undefined);

    // Ensure FX provider icons are cached when modal opens
    $effect(() => {
        if (open) getCurrencyGraph();
    });

    async function doSyncFn(targetIds: string[]): Promise<SyncResult[]> {
        const response = await zodiosApi.sync_rates_api_v1_fx_currencies_sync_post(
            {
                pairs: targetIds,
                start: dateStart,
                end: dateEnd,
            },
            {timeout: 120 * 1000},
        );
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

    let sections: SyncSection[] = $derived([
        {
            id: 'fx',
            title: `💱 ${$t('fx.sync.pairsCount') ?? 'FX Pairs'}`,
            doSyncFn,
            targetIds: pairs,
            resultRow: fxResultRow,
            countLabel: $t('fx.sync.pairsCount') ?? 'pairs',
        },
    ]);
</script>

<SyncModalBase
    bind:open
    bind:this={syncModalBase}
    {dateEnd}
    {dateStart}
    description={$t('fx.sync.description') ?? 'Synchronize exchange rates from configured providers for the selected date range.'}
    {onclose}
    {onsynced}
    {sections}
    {zIndex}
    testId="fx-sync-modal"
    title={$t('common.syncFxRates') ?? 'Sync FX Rates'}
></SyncModalBase>

{#snippet fxResultRow(pr: SyncResult, syncing: boolean)}
    {@const tooltipMsg = `${pr.points_fetched ?? 0}↓ ${pr.points_changed ?? 0}Δ` + formatSyncDetail(pr, get(t))}
    <SyncResultRow countIcon={null} identityWidth="max-w-none" onRetry={(id) => syncModalBase?.handleRetrySingle(id)} result={pr} statusTooltip={tooltipMsg} {syncing} {identity} {provider} />
{/snippet}

{#snippet identity(pr: SyncResult)}
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

{#snippet provider(code: string)}
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
