<!--
  FxSyncModal — Thin wrapper around SyncModalBase for FX pair sync.
  Builds a single SyncSection with FX-specific doSyncFn and resultRow snippet.
-->
<script lang="ts">
    import {zodiosApi} from '$lib/api';
    import {ArrowLeftRight, RotateCw} from 'lucide-svelte';
    import SyncModalBase from '$lib/components/ui/modals/SyncModalBase.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {_ as t} from '$lib/i18n';
    import {get} from 'svelte/store';
    import type {SyncResult, SyncSection} from '$lib/utils/syncHelpers';
    import {formatElapsed, STATUS_COLORS, STATUS_ICONS} from '$lib/utils/syncHelpers';
    import {DEFAULT_PROVIDER_COLOR, formatSyncDetail, getFxProviderIconUrl, parseProviderChain, PROVIDER_COLORS} from '$lib/utils/providerHelpers';
    import {getCurrencyInfo} from '$lib/stores/currencyStore';
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
    title={$t('fx.sync.title') ?? 'Sync FX Rates'}
></SyncModalBase>

{#snippet fxResultRow(pr: SyncResult, syncing: boolean)}
    {@const Icon = STATUS_ICONS[pr.status] ?? STATUS_ICONS.failed}
    {@const pairParts = pr.id.split('-')}
    {@const pairBase = pairParts[0] ?? ''}
    {@const pairQuote = pairParts[1] ?? ''}
    {@const tooltipMsg = (() => {
        let base = `${pr.points_fetched ?? 0}↓ ${pr.points_changed ?? 0}Δ`;
        base += formatSyncDetail(pr, get(t));
        return base;
    })()}
    <div class="flex items-center gap-2 text-xs text-gray-700 dark:text-gray-300 group">
        {#if (pr.status === 'failed' || pr.status === 'partial') && !syncing}
            <Tooltip text={tooltipMsg} position="top">
                <button
                    class="shrink-0 p-0.5 rounded transition-colors
                        {pr.status === 'failed' ? 'hover:bg-red-100 dark:hover:bg-red-900/30 text-red-500' : 'hover:bg-amber-100 dark:hover:bg-amber-900/30 text-amber-500'}"
                    onclick={() => syncModalBase?.handleRetrySingle(pr.id)}
                >
                    <RotateCw size={13} />
                </button>
            </Tooltip>
        {:else if pr.status === 'partial'}
            <Tooltip text={tooltipMsg} position="top">
                <Icon size={14} class="{STATUS_COLORS[pr.status] ?? 'text-gray-400'} shrink-0 cursor-help" />
            </Tooltip>
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
            <span>{pr.points_fetched ?? 0}↓ {pr.points_changed ?? 0}Δ</span>
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
        {/if}
        {#if pr.status === 'failed'}
            {@const fullErr = pr.errors?.join('; ') ?? pr.message ?? ''}
            {@const shortErr = pr.errors?.[0] ?? pr.message ?? 'Failed'}
            <!-- #R4-6: show full error in Tooltip (truncate only clips display). -->
            <Tooltip text={fullErr} position="top" maxWidth="500px">
                <span class="text-red-400 truncate inline-block max-w-[240px] align-middle">{shortErr}</span>
            </Tooltip>
        {/if}
        {#if pr.elapsed_ms}
            <span class="ml-auto text-gray-400 font-mono tabular-nums text-[10px]">{formatElapsed(pr.elapsed_ms)}</span>
        {/if}
    </div>
{/snippet}
