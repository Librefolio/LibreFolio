<!--
  The restore card: upload an archive, check it on a copy, read the report, confirm, then restart the server so that its
  next start applies the restore (lot B5b).

  Self-contained, like the backup card above it. Published state: `data-state` (the controller's), `data-error-code`,
  `data-busy`. Events: `backup.restore.*` (`restoreFlow.svelte.ts`); a failure also raises an error toast.

  A secure backup (an .lfbk, lot B4) asks for its password before it is sent (state `password`); a wrong password asks
  again, and the file is not sent again. Those steps are drawn by `RestoreFlowSteps`, shared with the modal that restores a
  kept backup (A10, T-15): «Restore» on a row of the kept backups opens that modal, and the card only lists the checks
  waiting for a decision, to resume or discard.
-->
<script lang="ts">
    import {onMount, untrack} from 'svelte';
    import {ArchiveRestore, FileArchive, LoaderCircle, RefreshCw, RotateCcw, ShieldAlert, TriangleAlert, Upload, X} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {formatDateTime} from '$lib/utils/core/formatDateTime';
    import {RestoreFlowController} from './restoreFlow.svelte';
    import RestoreReportModal from './RestoreReportModal.svelte';
    import RestartOverlay from './RestartOverlay.svelte';
    import {verifyRestorePassword} from './backupApi';
    import {restoreSignal} from './restoreSignal.svelte';
    import RestoreFlowSteps from './RestoreFlowSteps.svelte';
    import {restoreErrorKey, restoreReasonKey, restoreWaitingKey} from './restoreText';

    const controller = new RestoreFlowController({
        onEvent: (name, detail) =>
            notify({
                name,
                detail,
                // Every other step shows on the card or the overlay; a failure is said.
                toast: name === 'backup.restore.failed' ? {variant: 'error', message: $_(restoreErrorKey(String(detail.code ?? '')))} : undefined,
            }),
    });

    let fileInput = $state<HTMLInputElement | null>(null);
    let reportOpen = $state(true);

    onMount(() => {
        void controller.load();
        return () => controller.dispose();
    });

    // A10 (T-15): a kept backup is restored in its own modal; when it leaves a check for later, drops it or ends, the card
    // reads its state again, to list what waits for a decision.
    $effect(() => {
        if (restoreSignal.version === 0) return;
        untrack(() => {
            if (controller.state === 'idle' || controller.state === 'failed') void controller.load();
        });
    });

    // A new report opens the modal.
    $effect(() => {
        if (controller.state === 'report') reportOpen = true;
    });

    // Developer decision P8: a restore kept says nothing (the data shows it); one rolled back says why.
    const lastResult = $derived(controller.state === 'idle' && controller.status?.state === 'rolled_back' ? controller.status : null);

    function chooseFile() {
        fileInput?.click();
    }

    function fileChosen(event: Event) {
        const input = event.currentTarget as HTMLInputElement;
        const file = input.files?.[0];
        input.value = '';
        if (file) void controller.upload(file);
    }
</script>

<section class="space-y-4 rounded-xl border border-lf-subtle bg-lf-panel p-4 text-lf-primary sm:p-5" data-testid="restore-card" data-state={controller.state} data-error-code={controller.errorCode ?? ''} data-busy={controller.busy ? 'true' : 'false'} aria-busy={controller.busy}>
    <header class="flex items-start gap-3">
        <ArchiveRestore class="mt-0.5 shrink-0 text-lf-secondary" size={22} aria-hidden="true" />
        <div class="space-y-1">
            <h3 class="text-base font-semibold text-lf-primary">{$_('backup.restore.title')}</h3>
            <p class="text-sm text-lf-secondary">{$_('backup.restore.description')}</p>
        </div>
    </header>

    <p class="flex items-start gap-2 rounded-lg border border-lf-danger-line bg-lf-danger-soft p-3 text-sm text-lf-danger-on-soft" data-testid="restore-replace-notice">
        <ShieldAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
        <span>{$_('backup.restore.replaceNotice')}</span>
    </p>

    {#if controller.state === 'loading'}
        <p class="flex items-center gap-2 text-sm text-lf-secondary" data-testid="restore-loading">
            <LoaderCircle class="animate-spin" size={16} aria-hidden="true" />
            {$_('backup.restore.loading')}
        </p>
    {/if}

    {#if controller.state === 'idle' && controller.waiting.length > 0}
        <!-- C9-6: a check left for later, from this tab or another device: resume its report, or discard its archive. -->
        <ul class="space-y-2" data-testid="restore-waiting">
            {#each controller.waiting as held (held.stage_id)}
                <li
                    class="flex flex-wrap items-center gap-3 rounded-lg border border-lf-info-line bg-lf-info-soft p-3 text-sm text-lf-info-on-soft"
                    data-testid="restore-waiting-check"
                    data-stage-id={held.stage_id}
                    data-status={held.status}
                    data-restorable={held.restorable === null ? '' : String(held.restorable)}
                >
                    <FileArchive class="shrink-0" size={16} aria-hidden="true" />
                    <span class="min-w-0 flex-1">
                        {held.status === 'running' ? $_('backup.restore.held.running') : $_('backup.restore.held.until', {values: {date: formatDateTime(String(held.expires_at ?? ''))}})}
                    </span>
                    <button
                        class="inline-flex items-center gap-1.5 rounded-lg bg-lf-action px-3 py-1.5 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                        type="button"
                        data-testid="restore-waiting-resume"
                        onclick={() => void controller.resume(held.stage_id)}
                    >
                        {$_('backup.restore.held.resume')}
                    </button>
                    <button
                        class="inline-flex items-center gap-1.5 rounded-lg border border-lf-subtle bg-lf-card px-3 py-1.5 text-sm text-lf-secondary hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                        type="button"
                        data-testid="restore-waiting-discard"
                        onclick={() => void controller.discard(held.stage_id)}
                    >
                        <X size={14} aria-hidden="true" />
                        {$_('backup.restore.held.discard')}
                    </button>
                </li>
            {/each}
        </ul>
    {/if}

    {#if lastResult}
        <div class="flex items-start gap-2 rounded-lg border border-lf-warning-line bg-lf-warning-soft p-3 text-sm text-lf-warning-on-soft" data-testid="restore-last-result" data-result={lastResult.state} data-reason={lastResult.reason ?? ''}>
            <TriangleAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
            <span>{$_('backup.restore.last.rolledBack', {values: {date: formatDateTime(lastResult.finished_at ?? ''), reason: $_(restoreReasonKey(lastResult.reason))}})}</span>
        </div>
    {/if}

    <RestoreFlowSteps {controller} />

    {#if controller.state === 'report' && controller.report}
        <div class="flex flex-wrap items-center gap-2" data-testid="restore-report-ready" data-restorable={controller.report.restorable ? 'true' : 'false'}>
            <button
                class="inline-flex items-center gap-2 rounded-lg bg-lf-action px-4 py-2 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                type="button"
                data-testid="restore-open-report"
                onclick={() => (reportOpen = true)}
            >
                <FileArchive size={16} aria-hidden="true" />
                {$_('backup.restore.openReport')}
            </button>
        </div>
        <RestoreReportModal
            open={reportOpen}
            report={controller.report}
            busy={false}
            onConfirm={(ownerUserId) => controller.confirm(ownerUserId)}
            onDrop={() => controller.dropCheck()}
            onLater={() => void controller.later()}
            stageId={controller.stage?.stage_id ?? null}
            onVerify={(username, password) => verifyRestorePassword(controller.stage?.stage_id ?? '', username, password)}
            onClose={() => (reportOpen = false)}
        />
    {/if}

    {#if controller.state === 'pending' && controller.status}
        {@const pending = controller.status}
        <div class="space-y-3 rounded-lg border border-lf-info-line bg-lf-info-soft p-3 text-sm text-lf-info-on-soft" data-testid="restore-pending" data-waiting={pending.waiting ?? ''}>
            <p class="font-medium">{$_('backup.restore.pending.title')}</p>
            <p>
                {$_('backup.restore.pending.details', {
                    values: {
                        backupDate: formatDateTime(pending.backup_created_at ?? ''),
                        version: pending.backup_app_version ?? '',
                        who: pending.confirmed_by ?? '',
                        date: formatDateTime(pending.confirmed_at ?? ''),
                    },
                })}
            </p>
            {#if pending.waiting}
                <p class="flex items-start gap-2" data-testid="restore-waiting">
                    <TriangleAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
                    <span>{$_(restoreWaitingKey(pending.waiting))}</span>
                </p>
            {/if}
            <p>{$_('backup.restore.pending.restartHint')}</p>
            <div class="flex flex-wrap items-center gap-2">
                <button
                    class="inline-flex items-center gap-2 rounded-lg bg-lf-danger-solid px-4 py-2 text-sm font-medium text-lf-on-danger-solid hover:bg-lf-danger-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                    type="button"
                    data-testid="restore-restart"
                    onclick={() => controller.restartNow()}
                >
                    <RotateCcw size={16} aria-hidden="true" />
                    {$_('backup.restore.pending.restart')}
                </button>
                <button
                    class="inline-flex items-center gap-2 rounded-lg border border-lf-subtle bg-lf-card px-4 py-2 text-sm text-lf-secondary hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                    type="button"
                    data-testid="restore-cancel-pending"
                    onclick={() => controller.cancelPending()}
                >
                    <X size={16} aria-hidden="true" />
                    {$_('backup.restore.pending.cancel')}
                </button>
            </div>
        </div>
    {/if}

    {#if controller.state === 'in_progress'}
        <p class="flex items-center gap-2 text-sm text-lf-secondary" data-testid="restore-in-progress">
            <LoaderCircle class="animate-spin" size={16} aria-hidden="true" />
            {$_('backup.restore.inProgress')}
        </p>
    {/if}

    <!-- A refusal, or a restart or a cancel request that failed: the restore then stays confirmed, in the block above. -->
    {#if (controller.state === 'failed' || controller.state === 'pending') && controller.errorCode !== null}
        <div class="flex items-start gap-2 rounded-lg border border-lf-danger-line bg-lf-danger-soft p-3 text-sm text-lf-danger-on-soft" role="alert" data-testid="restore-error" data-error-code={controller.errorCode}>
            <TriangleAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
            <span>{$_(restoreErrorKey(controller.errorCode), {values: {limit: controller.errorLimitMb ?? ''}})}</span>
        </div>
    {/if}

    {#if controller.state === 'idle' || controller.state === 'failed'}
        <div class="flex flex-wrap items-center gap-2">
            <input bind:this={fileInput} class="hidden" type="file" accept=".zip,.lfbk,application/zip,application/octet-stream" data-testid="restore-file-input" onchange={fileChosen} />
            <button
                class="inline-flex items-center gap-2 rounded-lg bg-lf-action px-4 py-2 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                type="button"
                data-testid="restore-choose"
                onclick={chooseFile}
            >
                <Upload size={16} aria-hidden="true" />
                {$_('backup.restore.choose')}
            </button>
            {#if controller.state === 'failed'}
                <button
                    class="inline-flex items-center gap-2 rounded-lg border border-lf-subtle px-4 py-2 text-sm text-lf-secondary hover:bg-lf-neutral focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                    type="button"
                    data-testid="restore-retry"
                    onclick={() => controller.retry()}
                >
                    <RefreshCw size={16} aria-hidden="true" />
                    {$_('backup.restore.retry')}
                </button>
            {/if}
        </div>
        {#if controller.limitMb !== null && controller.limitMb > 0}
            <p class="text-xs text-lf-muted" data-testid="restore-limit" data-limit-mb={controller.limitMb}>{$_('backup.restore.limit', {values: {limit: controller.limitMb}})}</p>
        {/if}
    {/if}
</section>

{#if controller.state === 'restarting' && controller.outcome !== null}
    <RestartOverlay outcome={controller.outcome} slow={controller.slow} notStopping={controller.notStopping} status={controller.outcomeStatus} unreadableReason={controller.unreadableReason} onBack={() => controller.load()} />
{/if}
