<!--
  SyncModalBase — Generic sync modal for both FX and Asset sync.
  Provides the common structure: header, date range bar, timeout setting,
  progress bar with countdown, result list via snippet, retry logic, summary.
  Specializations (FxSyncModal, AssetSyncModal) define doSyncFn and resultRow snippet.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';
    import {Clock, Info, RefreshCw, SkipForward, Timer, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';
    import {_ as t} from '$lib/i18n';
    import type {SyncResult} from '$lib/utils/syncHelpers';
    import {formatTime} from '$lib/utils/syncHelpers';

    interface Props {
        open: boolean;
        dateStart: string;
        dateEnd: string;
        itemCount: number;
        title: string;
        description: string;
        countLabel: string;
        testId: string;
        /** Icon component for the header badge */
        headerIcon?: typeof RefreshCw;
        /** Color classes for the header badge background */
        headerIconBg?: string;
        /** Color classes for the header badge icon */
        headerIconColor?: string;
        /** Callback to perform the actual sync — returns results */
        doSyncFn: (targetIds: string[]) => Promise<SyncResult[]>;
        /** All target IDs to sync */
        targetIds: string[];
        /** Snippet for rendering each result row (specialization-specific) */
        resultRow: Snippet<[SyncResult, boolean]>;
        onsynced: () => void;
        onclose: () => void;
    }

    let {
        open = $bindable(),
        dateStart,
        dateEnd,
        itemCount,
        title,
        description,
        countLabel,
        testId,
        headerIcon: HeaderIcon = RefreshCw,
        headerIconBg = 'bg-amber-100 dark:bg-amber-900/30',
        headerIconColor = 'text-amber-600 dark:text-amber-400',
        doSyncFn,
        targetIds,
        resultRow,
        onsynced,
        onclose,
    }: Props = $props();

    let syncing = $state(false);
    let results = $state<SyncResult[]>([]);
    let error = $state<string | null>(null);
    let isTimeout = $state(false);
    let timeoutSec = $state(20);
    let elapsedMs = $state(0);
    let countdownInterval: ReturnType<typeof setInterval> | null = null;
    let hasResults = $derived(results.length > 0);
    let wasOpen = $state(false);

    let remainingSec = $derived(Math.max(0, timeoutSec - Math.floor(elapsedMs / 1000)));
    let progressPct = $derived(Math.min(100, (elapsedMs / (timeoutSec * 1000)) * 100));
    let failedItems = $derived(results.filter(r => r.status === 'failed' || r.status === 'partial'));
    let successCount = $derived(results.filter(r => r.status === 'ok').length);
    let totalPointsFetched = $derived(results.reduce((sum, r) => sum + (r.points_fetched ?? 0), 0));
    let totalPointsChanged = $derived(results.reduce((sum, r) => sum + (r.points_changed ?? 0), 0));

    // Reset state on open transition
    $effect(() => {
        const isOpen = open;
        if (isOpen && !wasOpen) {
            results = [];
            error = null;
            isTimeout = false;
            elapsedMs = 0;
            timeoutSec = Math.max(20, Math.ceil(itemCount * 1));
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

    async function doSync(ids: string[]) {
        syncing = true;
        error = null;
        isTimeout = false;
        startCountdown();
        try {
            const newResults = await doSyncFn(ids);
            // Merge: replace results for retried ids, keep existing for others
            const retriedIds = new Set(ids);
            results = [
                ...results.filter(r => !retriedIds.has(r.id)),
                ...newResults,
            ];
            onsynced();
        } catch (e: any) {
            const elapsed = Date.now();
            let errMsg: string;
            if (e?.code === 'ECONNABORTED' || e?.message?.includes('timeout')) {
                isTimeout = true;
                errMsg = `Timeout after ${timeoutSec}s`;
                error = `Request timed out after ${timeoutSec}s. Increase the timeout and retry.`;
            } else {
                errMsg = e?.response?.data?.detail || e?.message || 'Sync failed';
                error = errMsg;
            }
            // Generate failed results for all targeted IDs
            const failedResults: SyncResult[] = ids.map(id => ({
                id,
                status: 'failed' as const,
                points_fetched: 0,
                points_changed: 0,
                message: errMsg,
            }));
            const retriedIds = new Set(ids);
            results = [
                ...results.filter(r => !retriedIds.has(r.id)),
                ...failedResults,
            ];
        } finally {
            syncing = false;
            stopCountdown();
        }
    }

    function handleSyncAll() {
        results = [];
        doSync(targetIds);
    }

    function handleRetryFailed() {
        doSync(failedItems.map(r => r.id));
    }

    export function handleRetrySingle(id: string) {
        doSync([id]);
    }
</script>

<ModalBase maxWidth="max-w-md" onRequestClose={onclose} {open} testId={testId}>
    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-slate-700">
        <div class="flex items-center gap-2.5">
            <div class="flex items-center justify-center w-9 h-9 rounded-lg {headerIconBg}">
                <HeaderIcon class={headerIconColor} size={18}/>
            </div>
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">
                {title}
            </h2>
        </div>
        <button
                class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                onclick={onclose}
        >
            <X size={18}/>
        </button>
    </div>

    <!-- Body -->
    <div class="px-6 py-4 space-y-3">
        <p class="text-sm text-gray-600 dark:text-gray-400">
            {description}
        </p>
        <!-- Date range + count info -->
        <div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-slate-800 rounded-lg px-3 py-2">
            <span class="font-medium text-gray-700 dark:text-gray-300">{dateStart}</span>
            <span>→</span>
            <span class="font-medium text-gray-700 dark:text-gray-300">{dateEnd}</span>
            <span class="mx-1">·</span>
            <span>{itemCount} {countLabel}</span>
        </div>

        <!-- Timeout setting -->
        {#if !hasResults || failedItems.length > 0 || isTimeout}
            <div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                <Timer size={13} class="shrink-0"/>
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
                        <Clock size={13} class="animate-pulse"/>
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
            <InfoBanner variant="error" message={error}/>
        {/if}

        {#if hasResults}
            <!-- Retry all failed button -->
            {#if failedItems.length > 1 && !syncing}
                <button
                        class="flex items-center gap-1.5 w-full px-3 py-1.5 text-xs font-medium bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
                        onclick={handleRetryFailed}
                >
                    <SkipForward size={13}/>
                    Retry {failedItems.length} failed
                </button>
            {/if}

            <!-- Per-item results (delegated to snippet) -->
            <div class="space-y-1.5">
                {#each results as item (item.id)}
                    {@render resultRow(item, syncing)}
                {/each}
            </div>

            <!-- Summary -->
            <InfoBanner variant={successCount === results.length ? 'success' : successCount > 0 ? 'warning' : 'error'}>
                <span class="text-sm font-medium flex items-center gap-1 flex-wrap">
                    {$t('fx.sync.synced') ?? 'Synced'} {successCount}/{results.length} {countLabel}
                    ·
                    <span>{totalPointsFetched}↓</span>
                    <Tooltip text={$t('fx.sync.tooltipFetched')} position="top">
                        <Info size={12} class="text-gray-400 hover:text-libre-green cursor-help transition-colors"/>
                    </Tooltip>
                    <span>{totalPointsChanged}Δ</span>
                    <Tooltip text={$t('fx.sync.tooltipChanged')} position="top">
                        <Info size={12} class="text-gray-400 hover:text-libre-green cursor-help transition-colors"/>
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
        {#if !hasResults || failedItems.length > 0}
            <button
                    class="flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50"
                    onclick={hasResults && failedItems.length > 0 ? handleRetryFailed : handleSyncAll}
                    disabled={syncing || itemCount === 0}
            >
                <RefreshCw size={15} class={syncing ? 'animate-spin' : ''}/>
                {#if failedItems.length > 0 && hasResults}
                    {$t('common.retry') ?? 'Retry'} {failedItems.length} failed
                {:else if syncing}
                    {$t('fx.syncing') ?? 'Syncing...'}
                {:else}
                    {$t('fx.sync.start') ?? 'Start Sync'}
                {/if}
            </button>
        {/if}
    </div>
</ModalBase>

