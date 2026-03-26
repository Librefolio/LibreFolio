<!--
  FxSyncModal — Thin wrapper around SyncModalBase for FX pair sync.
  Defines doSyncFn (calls zodios sync endpoint) and resultRow snippet
  with FX-specific rendering (flags, chain providers, per-leg detail).
-->
<script lang="ts">
    import {zodiosApi} from '$lib/api';
    import {RotateCw} from 'lucide-svelte';
    import SyncModalBase from '$lib/components/ui/SyncModalBase.svelte';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';
    import {_ as t} from '$lib/i18n';
    import {get} from 'svelte/store';
    import type {SyncResult} from '$lib/utils/syncHelpers';
    import {STATUS_ICONS, STATUS_COLORS, formatElapsed} from '$lib/utils/syncHelpers';
    import {
        PROVIDER_COLORS, DEFAULT_PROVIDER_COLOR,
        parseProviderChain, getProviderIconUrl, formatSyncDetail,
    } from '$lib/utils/providerHelpers';

    interface Props {
        open: boolean;
        dateStart: string;
        dateEnd: string;
        pairs: string[];
        onsynced: () => void;
        onclose: () => void;
    }

    let {
        open = $bindable(),
        dateStart,
        dateEnd,
        pairs,
        onsynced,
        onclose,
    }: Props = $props();

    let syncModalBase: SyncModalBase | undefined = $state(undefined);

    async function doSyncFn(targetIds: string[]): Promise<SyncResult[]> {
        const response = await zodiosApi.sync_rates_api_v1_fx_currencies_sync_post(
            {
                pairs: targetIds,
                start: dateStart,
                end: dateEnd,
            },
            { timeout: 120 * 1000 },
        );
        const r = response as any;
        return (r.results ?? []).map((pr: any) => ({
            id: pr.pair,
            status: pr.status,
            points_fetched: pr.points_fetched ?? 0,
            points_changed: pr.points_changed ?? 0,
            provider_used: pr.provider_used,
            message: pr.message,
            errors: pr.errors ?? [],
            elapsed_ms: pr.elapsed_ms,
            detail: pr.detail,
        } satisfies SyncResult));
    }
</script>

<SyncModalBase
    bind:this={syncModalBase}
    bind:open
    {dateStart}
    {dateEnd}
    itemCount={pairs.length}
    title={$t('fx.sync.title') ?? 'Sync FX Rates'}
    description={$t('fx.sync.description') ?? 'Synchronize exchange rates from configured providers for the selected date range.'}
    countLabel={$t('fx.sync.pairsCount') ?? 'pairs'}
    testId="fx-sync-modal"
    {doSyncFn}
    targetIds={pairs}
    {onsynced}
    {onclose}
>
    {#snippet resultRow(pr: SyncResult, syncing: boolean)}
        {@const Icon = STATUS_ICONS[pr.status] ?? STATUS_ICONS.failed}
        {@const tooltipMsg = (() => {
            let base = `${(pr.points_fetched ?? 0)}↓ ${(pr.points_changed ?? 0)}Δ`;
            base += formatSyncDetail(pr, get(t));
            return base;
        })()}
        <div class="flex items-center gap-2 text-xs text-gray-700 dark:text-gray-300 group">
            {#if (pr.status === 'failed' || pr.status === 'partial') && !syncing}
                <Tooltip text={tooltipMsg} position="top">
                    <button
                        class="shrink-0 p-0.5 rounded transition-colors
                            {pr.status === 'failed'
                                ? 'hover:bg-red-100 dark:hover:bg-red-900/30 text-red-500'
                                : 'hover:bg-amber-100 dark:hover:bg-amber-900/30 text-amber-500'}"
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
            <span class="font-medium">{pr.id.replace('-', '/')}</span>
            {#if pr.status === 'ok' || pr.status === 'partial'}
                <span class="text-gray-400">—</span>
                <span>{pr.points_fetched ?? 0}↓ {pr.points_changed ?? 0}Δ</span>
                {#if pr.provider_used}
                    {@const chain = parseProviderChain(pr.provider_used)}
                    <span class="flex items-center gap-0.5">
                        {#each chain as prov, i}
                            {@const iconUrl = getProviderIconUrl(prov)}
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
                <span class="text-red-400 truncate" title={pr.errors?.join('; ') ?? pr.message ?? ''}>{pr.errors?.[0] ?? pr.message ?? 'Failed'}</span>
            {/if}
            {#if pr.elapsed_ms}
                <span class="ml-auto text-gray-400 font-mono tabular-nums text-[10px]">{formatElapsed(pr.elapsed_ms)}</span>
            {/if}
        </div>
    {/snippet}
</SyncModalBase>
