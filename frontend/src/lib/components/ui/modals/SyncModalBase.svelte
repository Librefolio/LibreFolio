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
    import {onDestroy} from 'svelte';
    import {Clock, Info, RefreshCw, SkipForward, Timer, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {_ as t} from '$lib/i18n';
    import type {SyncResult, SyncSection} from '$lib/utils/sync/syncHelpers';
    import {formatTime} from '$lib/utils/sync/syncHelpers';

    import {numericArrows} from '$lib/actions/numericArrows';
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
        /** Max width token passed to ModalBase (default max-w-md) */
        maxWidth?: string;
    }

    let {
        open = $bindable(),
        dateStart,
        dateEnd,
        title,
        description,
        testId,
        headerIcon: HeaderIcon = RefreshCw,
        headerIconBg = 'bg-amber-100 dark:bg-amber-900/30',
        headerIconColor = 'text-amber-600 dark:text-amber-400',
        sections,
        onsynced,
        onclose,
        zIndex = 50,
        maxWidth = 'max-w-md',
    }: Props = $props();

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
    /** Increments on every open: identifies the run the user is watching. */
    let session = $state(0);

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
    /** True when there are failures and every one is a soft (partial) failure — used to soften the retry-all accent to amber. */
    let allFailuresPartial = $derived(failedItems.length > 0 && failedItems.every((r) => r.status === 'partial'));
    let successCount = $derived(allResults.filter((r) => r.status === 'ok').length);
    let totalPointsFetched = $derived(allResults.reduce((sum, r) => sum + (r.points_fetched ?? 0), 0));
    let totalPointsChanged = $derived(allResults.reduce((sum, r) => sum + (r.points_changed ?? 0), 0));

    // =========================================================================
    // Effects
    // =========================================================================

    // Reset on open, tidy up on close
    $effect(() => {
        const isOpen = open;
        if (isOpen && !wasOpen) {
            // A new session, and the number is what makes it one. Closing does
            // not cancel the request — that is deliberate: the backend keeps
            // working through the providers and the timeout here is the user's
            // patience, not the server's. But a response from the run the user
            // walked away from must not land in the run they are looking at
            // now, and it used to: the reset cleared the results and left
            // `syncing` alone, so the modal reopened busy, showing the previous
            // request's progress bar, and that request's results then merged
            // into the new session.
            session += 1;
            sectionResults = new Map();
            error = null;
            isTimeout = false;
            elapsedMs = 0;
            syncing = false;
            stopCountdown();
            timeoutSec = Math.max(20, itemCount);
        } else if (!isOpen && wasOpen) {
            // The ticker is the one thing that must stop when the user walks
            // away, and it is the one thing the session guard cannot stop: the
            // `finally` of the abandoned run only runs its cleanup when its
            // epoch is still current, which by then it is not. Without this the
            // interval outlives the run — and where the parent unmounts the
            // modal behind an `{#if}` (TransactionFormModal does), it outlives
            // the component too, writing to a `$state` nobody will ever read
            // again, ten times a second, for the life of the page.
            stopCountdown();
        }
        wasOpen = isOpen;
    });

    // The `{#if}` case again: an unmount is a close the effect never sees.
    onDestroy(stopCountdown);

    /** True while `epoch` is still the session the user is looking at. */
    function current(epoch: number): boolean {
        return epoch === session && open;
    }

    // =========================================================================
    // Countdown
    // =========================================================================

    function startCountdown() {
        // Never leave a previous ticker behind: the reference is single, so a
        // second start without a stop loses the first one for good.
        stopCountdown();
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
    async function doSyncSection(section: SyncSection, ids: string[], epoch: number): Promise<SyncResult[]> {
        try {
            return await section.doSyncFn(ids);
        } catch (e: any) {
            let errMsg: string;
            if (e?.code === 'ECONNABORTED' || e?.message?.includes('timeout')) {
                errMsg = `Timeout after ${timeoutSec}s`;
                // The banner and the timeout flag belong to a session on screen.
                if (current(epoch)) {
                    isTimeout = true;
                    error = `Request timed out after ${timeoutSec}s. Increase the timeout and retry.`;
                }
            } else {
                errMsg = e?.response?.data?.detail || e?.message || 'Sync failed';
                if (current(epoch)) error = errMsg;
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

    /**
     * Fold a section's answer into what is already on screen.
     *
     * The rule this enforces: **an item that was asked about never leaves the
     * list without an outcome.** The previous version removed every requested
     * id and appended whatever came back, which is right when the answer covers
     * the question and destructive when it does not — a retry answered with
     * `[]` deleted the very failures it was meant to repair, taking their retry
     * button with them, and an initial sync that reported on one of two ids left
     * the second with no row at all while the summary read "1/1" in green.
     *
     * So: rows nobody answered about are kept as they were, and a requested id
     * that has never been reported on gets a row saying exactly that. Silence is
     * an outcome, and it is not a success.
     */
    function mergeResults(sectionId: string, newResults: SyncResult[], requestedIds: Set<string>) {
        const existing = sectionResults.get(sectionId) ?? [];
        const answered = new Set(newResults.map((r) => r.id));

        // Replaced only where there is something to replace them with.
        const kept = existing.filter((r) => !answered.has(r.id));

        const known = new Set([...kept.map((r) => r.id), ...answered]);
        const unreported: SyncResult[] = [...requestedIds]
            .filter((id) => !known.has(id))
            .map((id) => ({
                id,
                status: 'failed' as const,
                points_fetched: 0,
                points_changed: 0,
                message: $t('prices.sync.noReport') ?? 'The server did not report on this item',
            }));

        const merged = [...kept, ...newResults, ...unreported];
        // Trigger reactivity by creating a new Map
        const updated = new Map(sectionResults);
        updated.set(sectionId, merged);
        sectionResults = updated;
    }

    /** Sync all sections in parallel */
    async function handleSyncAll() {
        const epoch = session;
        syncing = true;
        error = null;
        isTimeout = false;
        sectionResults = new Map();
        startCountdown();

        try {
            await Promise.all(
                activeSections.map(async (section) => {
                    const results = await doSyncSection(section, section.targetIds, epoch);
                    if (current(epoch)) mergeResults(section.id, results, new Set(section.targetIds));
                }),
            );
            // `onsynced` makes the parent reload. Firing it for a session the
            // user has closed reloads a page on behalf of a modal that is no
            // longer on screen.
            if (current(epoch)) onsynced();
        } finally {
            if (current(epoch)) {
                syncing = false;
                stopCountdown();
            }
        }
    }

    /** Retry all failed items across all sections */
    async function handleRetryFailed() {
        const epoch = session;
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
                    const results = await doSyncSection(section, ids, epoch);
                    if (current(epoch)) mergeResults(sectionId, results, new Set(ids));
                }),
            );
            if (current(epoch)) onsynced();
        } finally {
            if (current(epoch)) {
                syncing = false;
                stopCountdown();
            }
        }
    }

    /** Retry a single item (called from result row snippet) */
    export async function handleRetrySingle(id: string) {
        // The markup hides the retry button while `syncing`, which is enough for
        // a finger — ~100 ms apart, the second press lands on nothing. It is not
        // enough for the same tick: two calls before the DOM flushes both get
        // through and the server is asked twice for the same id. The affordance
        // being invisible is not the same as the action being impossible.
        if (syncing) return;

        const section = findSectionForId(id);
        if (!section) return;

        const epoch = session;
        syncing = true;
        error = null;
        // Cleared here too, and it was not: the flag chooses the footer's label,
        // so a successful single-row retry left the modal claiming it had timed
        // out while showing a success.
        isTimeout = false;
        startCountdown();

        try {
            const results = await doSyncSection(section, [id], epoch);
            if (current(epoch)) {
                mergeResults(section.id, results, new Set([id]));
                onsynced();
            }
        } finally {
            if (current(epoch)) {
                syncing = false;
                stopCountdown();
            }
        }
    }
</script>

<ModalBase {maxWidth} onRequestClose={onclose} {open} {testId} {zIndex}>
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
        <button class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors" data-testid="sync-modal-dismiss" onclick={onclose}>
            <X size={18} />
        </button>
    </div>

    <!-- Body. `data-timeout` publishes the one piece of state that is otherwise
         only legible as a translated footer label ("Close" instead of "Cancel"):
         the last attempt died on a timeout rather than on an ordinary failure. -->
    <div class="px-6 py-4 space-y-3 flex-1 min-h-0 overflow-y-auto" data-busy={syncing ? 'true' : 'false'} data-testid="sync-modal-body" data-timeout={isTimeout ? 'true' : 'false'}>
        <p class="text-sm text-gray-600 dark:text-gray-400">
            {description}
        </p>
        <!-- Date range + count info. The visible tally is `countLabel`, which is
             assembled from translated nouns ("2 pairs · 3 assets"); the two
             counts are republished here as numbers so the scope of the sync is
             machine-readable in every language. -->
        <div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-slate-800 rounded-lg px-3 py-2" data-item-count={itemCount} data-section-count={activeSections.length} data-testid="sync-modal-count">
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
                <input
                    type="number"
                    use:numericArrows
                    min="10"
                    max="600"
                    step="10"
                    bind:value={timeoutSec}
                    disabled={syncing}
                    data-testid="sync-modal-timeout"
                    class="w-16 px-1.5 py-0.5 text-xs text-center rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-300 disabled:opacity-50"
                />
                <span>sec</span>
            </div>
        {/if}

        <!-- Progress bar during sync. `data-remaining` is the countdown in
             seconds; `formatTime` renders it as "1:05" or "45s", which is a
             format, not a number a test can compare against. -->
        {#if syncing}
            <div class="space-y-1.5" data-remaining={remainingSec} data-testid="sync-modal-progress">
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
                <button
                    class="flex items-center gap-1.5 w-full px-3 py-1.5 text-xs font-medium rounded-lg transition-colors
                        {allFailuresPartial ? 'bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 hover:bg-amber-100 dark:hover:bg-amber-900/30' : 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30'}"
                    data-testid="sync-modal-retry-failed"
                    onclick={handleRetryFailed}
                >
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
                <!-- One group per section. The wrapper carries the section
                     identity so results stay attributable to the section that
                     produced them (the <h4> above only renders when there are
                     two or more sections, and its counts are a translated
                     title plus a fraction). -->
                <div class="space-y-1.5" data-result-count={sResults.length} data-section-id={section.id} data-target-count={section.targetIds.length} data-testid="sync-section">
                    {#each sResults as item (item.id)}
                        {@render section.resultRow(item, syncing)}
                    {/each}
                    {#if syncing && sResults.length === 0}
                        <div class="flex items-center gap-2 text-xs text-gray-400" data-testid="sync-section-pending">
                            <RefreshCw size={12} class="animate-spin" />
                            {$t('common.syncing') ?? 'Syncing'}…
                        </div>
                    {/if}
                </div>
            {/each}

            <!-- Summary. This is where the sync says how it went: the modal
                 reports in place instead of raising a toast, so this banner is
                 the outcome, and `data-testid` makes it addressable as such.
                 The five tallies are republished as attributes because the
                 rendered line interleaves them with a translated verb and the
                 ↓/Δ glyphs, so the numbers themselves are otherwise only
                 reachable by parsing a sentence that changes with the locale. -->
            <div data-changed={totalPointsChanged} data-failed={failedItems.length} data-fetched={totalPointsFetched} data-success={successCount} data-testid="sync-modal-results" data-total={allResults.length}>
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
            </div>
        {/if}
    </div>

    <!-- Footer -->
    <div class="flex justify-end gap-2 px-6 py-4 border-t border-gray-100 dark:border-slate-700">
        <button class="px-4 py-2 text-sm font-medium bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors" data-testid="sync-modal-close" onclick={onclose}>
            {hasResults || isTimeout ? ($t('common.close') ?? 'Close') : ($t('common.cancel') ?? 'Cancel')}
        </button>
        {#if !hasResults || failedItems.length > 0}
            <button
                class="flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50"
                data-busy={syncing}
                data-testid="sync-modal-start"
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
