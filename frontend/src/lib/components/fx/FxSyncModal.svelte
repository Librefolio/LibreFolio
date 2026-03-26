<!--
  FxSyncModal — Modal for syncing FX rates with external providers.
  Shows per-pair results after sync completes.
  Features: editable timeout, countdown progress bar, per-pair elapsed time,
  retry failed individually or bulk.
-->
<script lang="ts">
    import {zodiosApi} from '$lib/api';
    import {RefreshCw, Check, X, AlertTriangle, SkipForward, AlertCircle, Clock, Timer, RotateCw, Info} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';
    import {_ as t} from '$lib/i18n';
    import {get} from 'svelte/store';
    import {
        PROVIDER_COLORS, DEFAULT_PROVIDER_COLOR,
        parseProviderChain, getProviderIconUrl, formatSyncDetail,
    } from '$lib/utils/fxSync';

    interface LegDetail {
        provider: string;
        leg: string;
        dates_available: number;
        error?: string | null;
    }

    interface PairResult {
        pair: string;
        status: 'ok' | 'partial' | 'failed' | 'skipped';
        provider_used?: string | null;
        points_fetched?: number;
        points_changed?: number;
        message?: string | null;
        detail?: LegDetail[] | null;
        elapsedMs?: number;
    }

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

    let syncing = $state(false);
    let pairResults = $state<PairResult[]>([]);
    let error = $state<string | null>(null);
    let isTimeout = $state(false);
    /** Dynamic timeout: min 20s, then ~1s per pair to accommodate large configs */
    let timeoutSec = $state(20);
    let elapsedMs = $state(0);
    let countdownInterval: ReturnType<typeof setInterval> | null = null;
    let hasResults = $derived(pairResults.length > 0);
    /** Track previous open state to detect open transitions (closed→open only) */
    let wasOpen = $state(false);

    const statusIcon: Record<string, typeof Check> = {
        ok: Check,
        partial: AlertTriangle,
        failed: AlertCircle,
        skipped: SkipForward,
    };
    const statusColor: Record<string, string> = {
        ok: 'text-emerald-500',
        partial: 'text-amber-500',
        failed: 'text-red-500',
        skipped: 'text-gray-400',
    };

    let remainingSec = $derived(Math.max(0, timeoutSec - Math.floor(elapsedMs / 1000)));
    let progressPct = $derived(Math.min(100, (elapsedMs / (timeoutSec * 1000)) * 100));
    let failedPairs = $derived(pairResults.filter(r => r.status === 'failed' || r.status === 'partial'));
    let successCount = $derived(pairResults.filter(r => r.status === 'ok').length);
    let totalPointsChanged = $derived(pairResults.reduce((sum, r) => sum + (r.points_changed ?? 0), 0));
    let totalPointsFetched = $derived(pairResults.reduce((sum, r) => sum + (r.points_fetched ?? 0), 0));

    // Reset state ONLY when modal transitions from closed → open (not on prop changes)
    $effect(() => {
        const isOpen = open;
        if (isOpen && !wasOpen) {
            pairResults = [];
            error = null;
            isTimeout = false;
            elapsedMs = 0;
            // Dynamic timeout: base 10s + 1s per pair (providers are fetched in parallel,
            // but DB writes and chain computations scale with pair count)
            timeoutSec = Math.max(20, Math.ceil(pairs.length * 1));
        }
        wasOpen = isOpen;
    });

    function startCountdown() {
        elapsedMs = 0;
        const start = Date.now();
        countdownInterval = setInterval(() => {
            elapsedMs = Date.now() - start;
        }, 100);
    }

    function stopCountdown() {
        if (countdownInterval) {
            clearInterval(countdownInterval);
            countdownInterval = null;
        }
    }

    async function doSync(targetPairs: string[]) {
        syncing = true;
        error = null;
        isTimeout = false;
        startCountdown();
        const syncStart = Date.now();
        try {
            const response = await zodiosApi.sync_rates_api_v1_fx_currencies_sync_post(
                {
                    pairs: targetPairs,
                    start: dateStart,
                    end: dateEnd,
                },
                { timeout: timeoutSec * 1000 },
            );
            const r = response as any;
            const elapsed = Date.now() - syncStart;
            const newResults: PairResult[] = (r.results ?? []).map((pr: any) => ({
                ...pr,
                elapsedMs: pr.elapsed_ms ?? elapsed,
            }));

            // Merge: replace results for retried pairs, keep existing for others
            const retriedSlugs = new Set(targetPairs);
            pairResults = [
                ...pairResults.filter(pr => !retriedSlugs.has(pr.pair)),
                ...newResults,
            ];

            onsynced();
        } catch (e: any) {
            const elapsed = Date.now() - syncStart;
            let errMsg: string;
            if (e?.code === 'ECONNABORTED' || e?.message?.includes('timeout')) {
                isTimeout = true;
                errMsg = `Timeout after ${timeoutSec}s`;
                error = `Request timed out after ${timeoutSec}s. Increase the timeout and retry.`;
            } else {
                errMsg = e?.response?.data?.detail || e?.message || 'Sync failed';
                error = errMsg;
            }

            // Generate failed results for all targeted pairs so the retry UI appears
            const failedResults: PairResult[] = targetPairs.map(pair => ({
                pair,
                status: 'failed' as const,
                message: errMsg,
                elapsedMs: elapsed,
            }));
            const retriedSlugs = new Set(targetPairs);
            pairResults = [
                ...pairResults.filter(pr => !retriedSlugs.has(pr.pair)),
                ...failedResults,
            ];
        } finally {
            syncing = false;
            stopCountdown();
        }
    }

    function handleSyncAll() {
        pairResults = [];
        doSync(pairs);
    }

    function handleRetryFailed() {
        doSync(failedPairs.map(r => r.pair));
    }

    function handleRetrySingle(pair: string) {
        doSync([pair]);
    }

    function formatTime(sec: number): string {
        const m = Math.floor(sec / 60);
        const s = sec % 60;
        return m > 0 ? `${m}:${s.toString().padStart(2, '0')}` : `${s}s`;
    }

    function formatElapsed(ms: number): string {
        if (ms < 1000) return `${ms}ms`;
        return `${(ms / 1000).toFixed(1)}s`;
    }

    // Provider colours & helpers imported from $lib/utils/fxSync
    const DEFAULT_PROV_COLOR = DEFAULT_PROVIDER_COLOR;
</script>

<ModalBase {open} onRequestClose={onclose} maxWidth="max-w-md" testId="fx-sync-modal">
    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-slate-700">
        <div class="flex items-center gap-2.5">
            <div class="flex items-center justify-center w-9 h-9 rounded-lg bg-amber-100 dark:bg-amber-900/30">
                <RefreshCw size={18} class="text-amber-600 dark:text-amber-400" />
            </div>
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">
                {$t('fx.sync.title') ?? 'Sync FX Rates'}
            </h2>
        </div>
        <button
            class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            onclick={onclose}
        >
            <X size={18} />
        </button>
    </div>

    <!-- Body -->
    <div class="px-6 py-4 space-y-3">
        <p class="text-sm text-gray-600 dark:text-gray-400">
            {$t('fx.sync.description') ?? 'Synchronize exchange rates from configured providers for the selected date range.'}
        </p>
        <!-- Date range + pairs info -->
        <div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-slate-800 rounded-lg px-3 py-2">
            <span class="font-medium text-gray-700 dark:text-gray-300">{dateStart}</span>
            <span>→</span>
            <span class="font-medium text-gray-700 dark:text-gray-300">{dateEnd}</span>
            <span class="mx-1">·</span>
            <span>{pairs.length} {$t('fx.sync.pairsCount') ?? 'pairs'}</span>
        </div>

        <!-- Timeout setting (always visible when not completed or has failures) -->
        {#if !hasResults || failedPairs.length > 0 || isTimeout}
            <div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                <Timer size={13} class="shrink-0" />
                <span>{$t('fx.sync.timeout') ?? 'Timeout'}:</span>
                <input
                    type="number"
                    min="10"
                    max="600"
                    step="10"
                    bind:value={timeoutSec}
                    disabled={syncing}
                    class="w-16 px-1.5 py-0.5 text-xs text-center rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-300 disabled:opacity-50"
                />
                <span>sec</span>
            </div>
        {/if}

        <!-- Progress bar during sync -->
        {#if syncing}
            <div class="space-y-1.5">
                <div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                    <span class="flex items-center gap-1.5">
                        <Clock size={13} class="animate-pulse" />
                        {$t('fx.syncing') ?? 'Syncing...'}
                    </span>
                    <span class="font-mono tabular-nums">{formatTime(remainingSec)}</span>
                </div>
                <div class="h-1.5 w-full bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
                    <div
                        class="h-full bg-amber-500 rounded-full transition-all duration-100"
                        style="width: {progressPct}%"
                    ></div>
                </div>
            </div>
        {/if}

        {#if error}
            <InfoBanner variant="error" message={error} />
        {/if}

        {#if hasResults}
            <!-- Retry all failed button -->
            {#if failedPairs.length > 1 && !syncing}
                <button
                    class="flex items-center gap-1.5 w-full px-3 py-1.5 text-xs font-medium bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
                    onclick={handleRetryFailed}
                >
                    <SkipForward size={13} />
                    Retry {failedPairs.length} failed
                </button>
            {/if}

            <!-- Per-pair results -->
            <div class="space-y-1.5">
                {#each pairResults as pr (pr.pair)}
                    {@const Icon = statusIcon[pr.status] ?? AlertCircle}
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
                                    onclick={() => handleRetrySingle(pr.pair)}
                                >
                                    <RotateCw size={13} />
                                </button>
                            </Tooltip>
                        {:else if pr.status === 'partial'}
                            <Tooltip text={tooltipMsg} position="top">
                                <Icon size={14} class="{statusColor[pr.status] ?? 'text-gray-400'} shrink-0 cursor-help" />
                            </Tooltip>
                        {:else}
                            <Icon size={14} class="{statusColor[pr.status] ?? 'text-gray-400'} shrink-0" />
                        {/if}
                        <span class="font-medium">{pr.pair.replace('-', '/')}</span>
                        {#if pr.status === 'ok' || pr.status === 'partial'}
                            <span class="text-gray-400">—</span>
                            <span>{pr.points_fetched ?? 0}↓ {pr.points_changed ?? 0}Δ</span>
                            {#if pr.provider_used}
                                {@const chain = parseProviderChain(pr.provider_used)}
                                <span class="flex items-center gap-0.5">
                                    {#each chain as prov, i}
                                        {@const iconUrl = getProviderIconUrl(prov)}
                                        <span class="inline-flex items-center gap-0.5 px-1 py-0.5 text-[9px] font-medium rounded {PROVIDER_COLORS[prov] ?? DEFAULT_PROV_COLOR}" title={prov}>
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
                        {#if pr.status === 'failed' && pr.message}
                            <span class="text-red-400 truncate" title={pr.message}>{pr.message}</span>
                        {/if}
                        {#if pr.elapsedMs}
                            <span class="ml-auto text-gray-400 font-mono tabular-nums text-[10px]">{formatElapsed(pr.elapsedMs)}</span>
                        {/if}
                    </div>
                {/each}
            </div>

            <!-- Summary -->
            <InfoBanner variant={successCount === pairResults.length ? 'success' : successCount > 0 ? 'warning' : 'error'}>
                <span class="text-sm font-medium flex items-center gap-1 flex-wrap">
                    {$t('fx.sync.synced') ?? 'Synced'} {successCount}/{pairResults.length} {$t('fx.sync.pairsCount') ?? 'pairs'}
                    ·
                    <span>{totalPointsFetched}↓</span>
                    <Tooltip text={$t('fx.sync.tooltipFetched')} position="top">
                        <Info size={12} class="text-gray-400 hover:text-libre-green cursor-help transition-colors" />
                    </Tooltip>
                    <span>{totalPointsChanged}Δ</span>
                    <Tooltip text={$t('fx.sync.tooltipChanged')} position="top">
                        <Info size={12} class="text-gray-400 hover:text-libre-green cursor-help transition-colors" />
                    </Tooltip>
                </span>
            </InfoBanner>
        {/if}
    </div>

    <!-- Footer -->
    <div class="flex justify-end gap-2 px-6 py-4 border-t border-gray-100 dark:border-slate-700">
        <button
            class="px-4 py-2 text-sm font-medium bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
            onclick={onclose}
        >
            {hasResults || isTimeout ? ($t('common.close') ?? 'Close') : ($t('common.cancel') ?? 'Cancel')}
        </button>
        {#if !hasResults || failedPairs.length > 0}
            <button
                class="flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50"
                onclick={hasResults && failedPairs.length > 0 ? handleRetryFailed : handleSyncAll}
                disabled={syncing || pairs.length === 0}
            >
                <RefreshCw size={15} class={syncing ? 'animate-spin' : ''} />
                {#if failedPairs.length > 0 && hasResults}
                    {$t('common.retry') ?? 'Retry'} {failedPairs.length} failed
                {:else if syncing}
                    {$t('fx.syncing') ?? 'Syncing...'}
                {:else}
                    {$t('fx.sync.start') ?? 'Start Sync'}
                {/if}
            </button>
        {/if}
    </div>
</ModalBase>
