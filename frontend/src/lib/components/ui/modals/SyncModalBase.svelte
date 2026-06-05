<!--
  SyncModalBase — Generic multi-section sync modal.
  Provides the common structure: header, date range bar, timeout setting,
  progress bar with countdown, per-section result lists via snippets,
  retry logic (single item + all-failed), and aggregated summary.

  Specializations (FxSyncModal, AssetSyncModal, PageSyncAllModal) build
  SyncSection[] and pass them here. Each section has its own doSyncFn
  and resultRow snippet. Sections with empty targetIds are hidden.
  All sections are synced in parallel with a unified countdown.

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {Clock, Info, RefreshCw, SkipForward, Timer, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {_ as t} from '$lib/i18n';
    import type {SyncResult, SyncSection} from '$lib/utils/syncHelpers';
    import {formatTime} from '$lib/utils/syncHelpers';

    interface Props {
        open: boolean;
        dateStart: string;
        dateEnd: string;
        title: string;
        description: string;
        testId: string;
        /** Icon component for the header badge */
        headerIcon?: typeof RefreshCw;
        /** Color classes for the header badge background */
        headerIconBg?: string;
        /** Color classes for the header badge icon */
        headerIconColor?: string;
        /** Sync sections — each rendered as a titled group with its own results */
        sections: SyncSection[];
        onsynced: () => void;
        onclose: () => void;
        /** z-index for stacking above other modals (default 50) */
        zIndex?: number;
    }

    let {open = $bindable(), dateStart, dateEnd, title, description, testId, headerIcon: HeaderIcon = RefreshCw, headerIconBg = 'bg-amber-100 dark:bg-amber-900/30', headerIconColor = 'text-amber-600 dark:text-amber-400', sections, onsynced, onclose, zIndex = 50}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let syncing = $state(false);
    /** Results keyed by section id */
    let sectionResults = $state<Map<string, SyncResult[]>>(new Map());
    let error = $state<string | null>(null);
    let isTimeout = $state(false);
    let timeoutSec = $state(20);
    let elapsedMs = $state(0);
    let countdownInterval: ReturnType<typeof setInterval> | null = null;
    let wasOpen = $state(false);

    // =========================================================================
    // Derived
    // =========================================================================

    /** Only sections with items to sync */
    let activeSections = $derived(sections.filter((s) => s.targetIds.length > 0));

    /** Total item count across all sections */
    let itemCount = $derived(activeSections.reduce((sum, s) => sum + s.targetIds.length, 0));

    /** Count label combining all section labels */
    let countLabel = $derived(activeSections.map((s) => `${s.targetIds.length} ${s.countLabel}`).join(' · '));

    /** All results flattened */
    let allResults = $derived(Array.from(sectionResults.values()).flat());

    let hasResults = $derived(allResults.length > 0);
    let remainingSec = $derived(Math.max(0, timeoutSec - Math.floor(elapsedMs / 1000)));
    let progressPct = $derived(Math.min(100, (elapsedMs / (timeoutSec * 1000)) * 100));
    let failedItems = $derived(allResults.filter((r) => r.status === 'failed' || r.status === 'partial'));
    let successCount = $derived(allResults.filter((r) => r.status === 'ok').length);
    let totalPointsFetched = $derived(allResults.reduce((sum, r) => sum + (r.points_fetched ?? 0), 0));
    let totalPointsChanged = $derived(allResults.reduce((sum, r) => sum + (r.points_changed ?? 0), 0));

    // =========================================================================
    // Effects
    // =========================================================================

    // Reset state on open transition
    $effect(() => {
        const isOpen = open;
        if (isOpen && !wasOpen) {
            sectionResults = new Map();
            error = null;
            isTimeout = false;
            elapsedMs = 0;
            timeoutSec = Math.max(20, itemCount);
        }
        wasOpen = isOpen;
    });

    // =========================================================================
    // Countdown
    // =========================================================================

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

    // =========================================================================
    // Sync logic
    // =========================================================================

    /** Find which section owns a given result ID */
    function findSectionForId(id: string): SyncSection | undefined {
        return activeSections.find((s) => s.targetIds.includes(id));
    }

    /** Sync specific IDs within a single section */
    async function doSyncSection(section: SyncSection, ids: string[]): Promise<SyncResult[]> {
        try {
            return await section.doSyncFn(ids);
        } catch (e: any) {
            let errMsg: string;
            if (e?.code === 'ECONNABORTED' || e?.message?.includes('timeout')) {
                isTimeout = true;
                errMsg = `Timeout after ${timeoutSec}s`;
                error = `Request timed out after ${timeoutSec}s. Increase the timeout and retry.`;
            } else {
                errMsg = e?.response?.data?.detail || e?.message || 'Sync failed';
                error = errMsg;
            }
            return ids.map((id) => ({
                id,
                status: 'failed' as const,
                points_fetched: 0,
                points_changed: 0,
                message: errMsg,
            }));
        }
    }

    /** Merge new results into sectionResults for a given section */
    function mergeResults(sectionId: string, newResults: SyncResult[], retriedIds: Set<string>) {
        const existing = sectionResults.get(sectionId) ?? [];
        const merged = [...existing.filter((r) => !retriedIds.has(r.id)), ...newResults];
        // Trigger reactivity by creating a new Map
        const updated = new Map(sectionResults);
        updated.set(sectionId, merged);
        sectionResults = updated;
    }

    /** Sync all sections in parallel */
    async function handleSyncAll() {
        syncing = true;
        error = null;
        isTimeout = false;
        sectionResults = new Map();
        startCountdown();

        try {
            await Promise.all(
                activeSections.map(async (section) => {
                    const results = await doSyncSection(section, section.targetIds);
                    mergeResults(section.id, results, new Set(section.targetIds));
                }),
            );
            onsynced();
        } finally {
            syncing = false;
            stopCountdown();
        }
    }

    /** Retry all failed items across all sections */
    async function handleRetryFailed() {
        syncing = true;
        error = null;
        isTimeout = false;
        startCountdown();

        try {
            // Group failed items by section
            const failedBySection = new Map<string, string[]>();
            for (const r of failedItems) {
                const section = findSectionForId(r.id);
                if (!section) continue;
                const list = failedBySection.get(section.id) ?? [];
                list.push(r.id);
                failedBySection.set(section.id, list);
            }

            await Promise.all(
                Array.from(failedBySection.entries()).map(async ([sectionId, ids]) => {
                    const section = activeSections.find((s) => s.id === sectionId);
                    if (!section) return;
                    const results = await doSyncSection(section, ids);
                    mergeResults(sectionId, results, new Set(ids));
                }),
            );
            onsynced();
        } finally {
            syncing = false;
            stopCountdown();
        }
    }

    /** Retry a single item (called from result row snippet) */
    export async function handleRetrySingle(id: string) {
        const section = findSectionForId(id);
        if (!section) return;

        syncing = true;
        error = null;
        startCountdown();

        try {
            const results = await doSyncSection(section, [id]);
            mergeResults(section.id, results, new Set([id]));
            onsynced();
        } finally {
            syncing = false;
            stopCountdown();
        }
    }
</script>

<ModalBase maxWidth="max-w-md" onRequestClose={onclose} {open} {testId} {zIndex}>
    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-slate-700">
        <div class="flex items-center gap-2.5">
            <div class="flex items-center justify-center w-9 h-9 rounded-lg {headerIconBg}">
                <HeaderIcon class={headerIconColor} size={18} />
            </div>
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">
                {title}
            </h2>
        </div>
        <button class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors" onclick={onclose}>
            <X size={18} />
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
            <span>{countLabel}</span>
        </div>

        <!-- Timeout setting -->
        {#if !hasResults || failedItems.length > 0 || isTimeout}
            <div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                <Timer size={13} class="shrink-0" />
                <span>{$t('fx.sync.timeout') ?? 'Timeout'}:</span>
                <input type="number" min="10" max="600" step="10" bind:value={timeoutSec} disabled={syncing} class="w-16 px-1.5 py-0.5 text-xs text-center rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-300 disabled:opacity-50" />
                <span>sec</span>
            </div>
        {/if}

        <!-- Progress bar during sync -->
        {#if syncing}
            <div class="space-y-1.5">
                <div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                    <span class="flex items-center gap-1.5">
                        <Clock size={13} class="animate-pulse" />
                        {$t('common.syncing') ?? 'Syncing...'}
                    </span>
                    <span class="font-mono tabular-nums">{formatTime(remainingSec)}</span>
                </div>
                <div class="h-1.5 w-full bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
                    <div class="h-full bg-amber-500 rounded-full transition-all duration-100" style="width: {progressPct}%"></div>
                </div>
            </div>
        {/if}

        {#if error}
            <InfoBanner variant="error" message={error} />
        {/if}

        {#if hasResults}
            <!-- Retry all failed button -->
            {#if failedItems.length > 1 && !syncing}
                <button class="flex items-center gap-1.5 w-full px-3 py-1.5 text-xs font-medium bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors" onclick={handleRetryFailed}>
                    <SkipForward size={13} />
                    Retry {failedItems.length} failed
                </button>
            {/if}

            <!-- Per-section results -->
            {#each activeSections as section (section.id)}
                {@const sResults = sectionResults.get(section.id) ?? []}
                {#if activeSections.length > 1}
                    <h4 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mt-2">
                        {section.title} ({sResults.length}/{section.targetIds.length})
                    </h4>
                {/if}
                <div class="space-y-1.5">
                    {#each sResults as item (item.id)}
                        {@render section.resultRow(item, syncing)}
                    {/each}
                    {#if syncing && sResults.length === 0}
                        <div class="flex items-center gap-2 text-xs text-gray-400">
                            <RefreshCw size={12} class="animate-spin" />
                            {$t('common.syncing') ?? 'Syncing'}…
                        </div>
                    {/if}
                </div>
            {/each}

            <!-- Summary -->
            <InfoBanner variant={successCount === allResults.length ? 'success' : successCount > 0 ? 'warning' : 'error'}>
                <span class="text-sm font-medium flex items-center gap-1 flex-wrap">
                    {$t('fx.sync.synced') ?? 'Synced'}
                    {successCount}/{allResults.length}
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
        <button class="px-4 py-2 text-sm font-medium bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors" onclick={onclose}>
            {hasResults || isTimeout ? ($t('common.close') ?? 'Close') : ($t('common.cancel') ?? 'Cancel')}
        </button>
        {#if !hasResults || failedItems.length > 0}
            <button
                class="flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50"
                onclick={hasResults && failedItems.length > 0 ? handleRetryFailed : handleSyncAll}
                disabled={syncing || itemCount === 0}
            >
                <RefreshCw size={15} class={syncing ? 'animate-spin' : ''} />
                {#if failedItems.length > 0 && hasResults}
                    {$t('common.retry') ?? 'Retry'} {failedItems.length} failed
                {:else if syncing}
                    {$t('common.syncing') ?? 'Syncing...'}
                {:else}
                    {$t('fx.sync.start') ?? 'Start Sync'}
                {/if}
            </button>
        {/if}
    </div>
</ModalBase>
