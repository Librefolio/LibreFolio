<!--
  The space bar of the Files page (lot FB-29), for administrators: how much room the instance takes.

  With a limit, the space used against it; without one, LibreFolio's parts (database, uploaded files, broker reports,
  backups, the rest) against the disk, the other files of the disk in grey and the free space empty; with neither, the
  parts against LibreFolio's own folder. The limit is a setting of the administrator, unless the hosting provider sets
  it, which locks the field; it sits in the closed «Advanced» panel under the bar (K-2).

  Self-contained: reads when it mounts and again whenever the backup list changes (`backupListSignal`, which the Files
  page also nudges on its Refresh), so the bar follows the backups that come and go.

  Published state: `data-state` (`loading`, `ready`, `error`), `data-mode` (`limit`, `volume`, `data`), `data-busy`.
  Event: `storage.limit.saved`.
-->
<script lang="ts">
    import {tick, untrack} from 'svelte';
    import {HardDrive, LoaderCircle, Lock, RefreshCw, TriangleAlert} from 'lucide-svelte';
    import {backupFailureCode, getInstanceStorage, saveStorageLimit, storageLimitSaveCode, type InstanceStorage} from '$lib/features/backup/backupApi';
    import {backupListSignal} from '$lib/features/backup/backupList.svelte';
    import {_} from '$lib/i18n';
    import {notify} from '$lib/stores/app/notify.svelte';
    import FoldPanel from '$lib/components/ui/display/FoldPanel.svelte';
    import LinkedStackedBar from '$lib/components/ui/display/LinkedStackedBar.svelte';
    import type {LinkedSegment} from '$lib/components/ui/display/linkedStackedBar';
    import {formatBytes} from '$lib/utils/files/upload';
    import {storageBarModel, type StorageSegmentId} from './storageBar';

    // The fill of each part: a role of the design system, never a colour written by hand.
    const FILL: Record<StorageSegmentId | 'free', string> = {
        database: 'bg-lf-brand',
        uploads: 'bg-lf-info',
        brokerReports: 'bg-lf-success',
        backups: 'bg-lf-warning',
        dataOther: 'bg-lf-checked',
        disk: 'bg-lf-neutral',
        free: 'bg-transparent',
    };

    interface Props {
        /** Open the «Advanced» panel of the limit and bring it into view once the bar is drawn (C9-1, `/files?storage=limit`). */
        openAdvanced?: boolean;
    }

    let {openAdvanced = false}: Props = $props();

    let advancedOpen = $state(false);
    let advancedRoot = $state<HTMLDivElement | undefined>(undefined);
    let advancedShown = false;

    let usage = $state<InstanceStorage | null>(null);
    let failed = $state(false);
    let errorCode = $state('');
    let reading = $state(0);
    // Only the answer of the latest read counts.
    let latestRead = 0;

    const model = $derived(usage === null ? null : storageBarModel(usage));
    const barState = $derived(failed ? 'error' : usage === null ? 'loading' : 'ready');

    async function load() {
        const read = ++latestRead;
        reading += 1;
        try {
            const answer = await getInstanceStorage();
            if (read !== latestRead) return;
            usage = answer;
            failed = false;
            errorCode = '';
            limitText = String(answer.limit_mb ?? 0);
        } catch (error) {
            if (read !== latestRead) return;
            failed = true;
            errorCode = backupFailureCode(error);
        } finally {
            reading -= 1;
        }
    }

    // The first read, and one more at every change of the signal.
    $effect(() => {
        void backupListSignal.version;
        untrack(() => void load());
    });

    // C9-1: asked from an «Open the settings» link: the panel opens, once, as soon as it is drawn, and comes into view.
    $effect(() => {
        if (!openAdvanced || advancedShown || advancedRoot === undefined) return;
        advancedShown = true;
        advancedOpen = true;
        void tick().then(() => advancedRoot?.scrollIntoView?.({block: 'center'}));
    });

    // --- The limit ---------------------------------------------------------------------------------------------------
    type LimitState = 'idle' | 'saving' | 'saved' | 'error';
    let limitText = $state('0');
    let limitState = $state<LimitState>('idle');
    let limitErrorCode = $state('');

    const typedLimit = $derived(/^\d+$/.test(limitText.trim()) ? Number.parseInt(limitText.trim(), 10) : null);
    const limitInForce = $derived(usage?.limit_mb ?? 0);
    const locked = $derived(usage?.limit_locked === true);
    const canSave = $derived(usage !== null && !locked && limitState !== 'saving' && typedLimit !== null && typedLimit !== limitInForce);

    function limitEdited() {
        if (limitState === 'saved') limitState = 'idle';
    }

    async function saveLimit() {
        if (!canSave || typedLimit === null) return;
        const limitMb = typedLimit;
        limitState = 'saving';
        limitErrorCode = '';
        try {
            await saveStorageLimit(limitMb);
        } catch (error) {
            limitErrorCode = storageLimitSaveCode(error);
            limitState = 'error';
            return;
        }
        limitState = 'saved';
        notify({name: 'storage.limit.saved', detail: {limit_mb: limitMb}, toast: {variant: 'success', message: $_('storage.limit.saved')}});
        await load();
    }

    function size(bytes: number): string {
        return formatBytes(bytes, $_);
    }

    const TEST_IDS = {
        bar: 'storage-bar-track',
        segment: (id: string) => `storage-segment-${id}`,
        item: (id: string) => `storage-legend-${id}`,
    };

    /** The parts of the data, then the free space when the bar has a total to measure it against. */
    const barSegments = $derived.by((): LinkedSegment[] => {
        if (model === null) return [];
        const parts = model.segments.map((segment) => ({id: segment.id, percent: segment.percent, fill: FILL[segment.id], attrs: {'data-bytes': segment.bytes}}));
        return model.mode === 'data' ? parts : [...parts, {id: 'free', percent: model.freePercent, fill: FILL.free, attrs: {'data-bytes': model.freeBytes}}];
    });

    const summary = $derived.by(() => {
        if (model === null || usage === null) return '';
        if (model.mode === 'limit') return $_('storage.summary.limit', {values: {used: size(model.usedBytes), limit: size((usage.limit_mb ?? 0) * 1024 * 1024)}});
        if (model.mode === 'volume') return $_('storage.summary.volume', {values: {used: size(usage.data_bytes), total: size(model.totalBytes)}});
        return $_('storage.summary.data', {values: {used: size(usage.data_bytes)}});
    });

    const fieldClass = 'w-32 rounded-lg border border-lf-input bg-lf-field px-3 py-1.5 text-lf-primary hover:border-lf-input-hover focus:border-lf-focus focus:outline-none focus:ring-1 focus:ring-lf-focus disabled:cursor-not-allowed disabled:opacity-50';
</script>

<section class="mb-4 space-y-3 rounded-xl border border-lf-subtle bg-lf-panel p-4 text-lf-primary" data-testid="storage-bar" data-state={barState} data-mode={model?.mode ?? ''} data-busy={reading > 0 ? 'true' : 'false'} aria-busy={reading > 0}>
    <header class="flex items-center gap-2">
        <HardDrive class="shrink-0 text-lf-secondary" size={18} aria-hidden="true" />
        <h2 class="text-sm font-semibold text-lf-primary">{$_('storage.title')}</h2>
        {#if reading > 0}
            <LoaderCircle class="animate-spin text-lf-muted" size={14} aria-hidden="true" />
        {/if}
    </header>

    {#if barState === 'error'}
        <div class="flex flex-wrap items-center gap-3 rounded-lg border border-lf-danger-line bg-lf-danger-soft p-3 text-sm text-lf-danger-on-soft" role="alert" data-testid="storage-error" data-error-code={errorCode}>
            <TriangleAlert class="shrink-0" size={16} aria-hidden="true" />
            <span class="min-w-0 flex-1">{$_('storage.errors.load')}</span>
            <button
                class="inline-flex items-center gap-2 rounded-lg border border-lf-subtle px-3 py-1.5 text-sm text-lf-secondary hover:bg-lf-neutral focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                type="button"
                data-testid="storage-retry"
                onclick={() => void load()}
            >
                <RefreshCw size={14} aria-hidden="true" />
                {$_('storage.retry')}
            </button>
        </div>
    {:else if model !== null && usage !== null}
        <!-- Pointing at a part of the bar lights its legend row, and the other way round (the planner's timing bar does the same). -->
        <LinkedStackedBar
            segments={barSegments}
            barClass="flex h-3 w-full overflow-hidden rounded-full border border-lf-subtle bg-lf-field"
            barLabel={summary}
            marker={model.limitPercent === null ? null : {percent: model.limitPercent, label: $_('storage.limit.marker', {values: {limit: size((usage.limit_mb ?? 0) * 1024 * 1024)}})}}
            legendClass="grid gap-x-6 gap-y-1 text-xs text-lf-secondary sm:grid-cols-2 lg:grid-cols-3"
            itemClass="rounded-md px-1 py-0.5"
            testIds={TEST_IDS}
        >
            {#snippet between()}
                <p class="text-sm text-lf-secondary" data-testid="storage-summary">{summary}</p>
            {/snippet}
            {#snippet row(segment)}
                <span class="min-w-0 flex-1">{$_(`storage.parts.${segment.id}`)}</span>
                <span class="tabular-nums text-lf-primary">{size(Number(segment.attrs?.['data-bytes'] ?? 0))}</span>
            {/snippet}
        </LinkedStackedBar>

        {#if model.overLimit}
            <p class="flex items-start gap-2 rounded-lg border border-lf-warning-line bg-lf-warning-soft p-3 text-sm text-lf-warning-on-soft" data-testid="storage-over-limit">
                <TriangleAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
                <span>{$_('storage.overLimit')}</span>
            </p>
        {/if}

        <div bind:this={advancedRoot}>
            <FoldPanel title={$_('storage.advanced.title')} testId="storage-advanced" bind:open={advancedOpen}>
                <div class="flex flex-wrap items-end gap-3">
                    <div class="space-y-1">
                        <label class="block text-sm font-medium text-lf-secondary" for="storage-limit-mb">{$_('storage.limit.label')}</label>
                        <input class={fieldClass} id="storage-limit-mb" data-testid="storage-limit-mb" type="number" inputmode="numeric" min="0" step="1" value={limitText} disabled={locked} oninput={(event) => ((limitText = event.currentTarget.value), limitEdited())} />
                    </div>
                    <button
                        class="inline-flex items-center gap-2 rounded-lg bg-lf-action px-4 py-2 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus disabled:cursor-not-allowed disabled:opacity-50"
                        type="button"
                        data-testid="storage-limit-save"
                        disabled={!canSave}
                        onclick={() => void saveLimit()}
                    >
                        {#if limitState === 'saving'}
                            <LoaderCircle class="animate-spin" size={16} aria-hidden="true" />
                        {/if}
                        {$_('storage.limit.save')}
                    </button>
                </div>
                <p class="text-xs text-lf-muted">{$_('storage.limit.hint')}</p>
                {#if locked}
                    <p class="flex items-center gap-2 text-xs text-lf-secondary" data-testid="storage-limit-locked">
                        <Lock size={14} aria-hidden="true" />
                        {$_('storage.limit.locked')}
                    </p>
                {/if}
                {#if limitState === 'error'}
                    <p class="flex items-center gap-2 text-sm text-lf-danger-on-soft" role="alert" data-testid="storage-limit-error" data-error-code={limitErrorCode}>
                        <TriangleAlert class="shrink-0" size={16} aria-hidden="true" />
                        {$_(`storage.limit.errors.${limitErrorCode}`)}
                    </p>
                {/if}
            </FoldPanel>
        </div>
    {/if}
</section>
