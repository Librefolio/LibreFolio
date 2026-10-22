<!--
  The restore card: upload an archive, check it on a copy, read the report, confirm, then restart the server so that its
  next start applies the restore (lot B5b).

  Self-contained, like the backup card above it. Published state: `data-state` (the controller's), `data-error-code`,
  `data-busy`. Events: `backup.restore.*` (`restoreFlow.svelte.ts`); a failure also raises an error toast.

  A secure backup (an .lfbk, lot B4) asks for its password before it is sent (state `password`); a wrong password asks
  again, and the file is not sent again. The password leaves the field as soon as it is submitted.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {ArchiveRestore, FileArchive, KeyRound, LoaderCircle, RefreshCw, RotateCcw, ShieldAlert, TriangleAlert, Upload, X} from 'lucide-svelte';
    import PasswordInput from '$lib/components/ui/input/PasswordInput.svelte';
    import {_} from '$lib/i18n';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {formatDateTime} from '$lib/utils/core/formatDateTime';
    import {formatBytes} from '$lib/utils/files/upload';
    import type {RestorePhase} from './backupApi';
    import {RestoreFlowController} from './restoreFlow.svelte';
    import RestoreReportModal from './RestoreReportModal.svelte';
    import RestartOverlay from './RestartOverlay.svelte';
    import {restoreErrorKey, restoreReasonKey, restoreWaitingKey} from './restoreText';

    const PHASE_KEYS: Record<RestorePhase, string> = {
        decrypting: 'backup.restore.phase.decrypting',
        checking: 'backup.restore.phase.checking',
        unpacking: 'backup.restore.phase.unpacking',
        upgrading: 'backup.restore.phase.upgrading',
        verifying: 'backup.restore.phase.verifying',
    };

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
    let restorePassword = $state('');

    onMount(() => {
        void controller.load();
        return () => controller.dispose();
    });

    // A new report opens the modal.
    $effect(() => {
        if (controller.state === 'report') reportOpen = true;
    });

    const uploadPercent = $derived(controller.totalBytes > 0 ? Math.min(100, Math.round((controller.uploadedBytes / controller.totalBytes) * 100)) : null);
    const checkPercent = $derived.by(() => {
        const stage = controller.stage;
        if (stage === null || stage.total_bytes <= 0) return null;
        return Math.min(100, Math.round((stage.done_bytes / stage.total_bytes) * 100));
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

    function submitPassword(event: SubmitEvent) {
        event.preventDefault();
        const typed = restorePassword;
        restorePassword = '';
        void controller.submitPassword(typed);
    }

    function cancelPassword() {
        restorePassword = '';
        controller.cancelPassword();
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

    {#if lastResult}
        <div class="flex items-start gap-2 rounded-lg border border-lf-warning-line bg-lf-warning-soft p-3 text-sm text-lf-warning-on-soft" data-testid="restore-last-result" data-result={lastResult.state} data-reason={lastResult.reason ?? ''}>
            <TriangleAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
            <span>{$_('backup.restore.last.rolledBack', {values: {date: formatDateTime(lastResult.finished_at ?? ''), reason: $_(restoreReasonKey(lastResult.reason))}})}</span>
        </div>
    {/if}

    {#if controller.state === 'password'}
        <form class="space-y-3" data-testid="restore-password-form" onsubmit={submitPassword} novalidate>
            <p class="flex items-start gap-2 text-sm text-lf-secondary">
                <KeyRound class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
                <span>{$_('backup.restore.password.intro')}</span>
            </p>
            <div class="space-y-2">
                <label class="block text-sm font-medium text-lf-secondary" for="restore-password">{$_('backup.restore.password.label')}</label>
                <PasswordInput autocomplete="off" bind:value={restorePassword} disabled={controller.submitting} hasError={controller.errorCode !== null} id="restore-password" name="restore-password" testId="restore-password" />
            </div>
            {#if controller.errorCode !== null}
                <p class="flex items-start gap-2 text-sm text-lf-danger" role="alert" data-testid="restore-password-error" data-error-code={controller.errorCode}>
                    <TriangleAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
                    <span>{$_(restoreErrorKey(controller.errorCode))}</span>
                </p>
            {/if}
            <div class="flex flex-wrap items-center gap-2">
                <button
                    class="inline-flex items-center gap-2 rounded-lg bg-lf-action px-4 py-2 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus disabled:cursor-not-allowed disabled:opacity-50"
                    type="submit"
                    data-testid="restore-password-submit"
                    disabled={restorePassword === '' || controller.submitting}
                >
                    {#if controller.submitting}
                        <LoaderCircle class="animate-spin" size={16} aria-hidden="true" />
                    {:else}
                        <KeyRound size={16} aria-hidden="true" />
                    {/if}
                    {$_('backup.restore.password.submit')}
                </button>
                <button
                    class="inline-flex items-center gap-2 rounded-lg border border-lf-subtle px-4 py-2 text-sm text-lf-secondary hover:bg-lf-neutral focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus disabled:cursor-not-allowed disabled:opacity-50"
                    type="button"
                    data-testid="restore-password-cancel"
                    disabled={controller.submitting}
                    onclick={cancelPassword}
                >
                    <X size={16} aria-hidden="true" />
                    {$_('backup.restore.password.cancel')}
                </button>
            </div>
        </form>
    {/if}

    {#if controller.state === 'uploading'}
        <div class="space-y-2" data-testid="restore-upload-progress">
            <div class="flex flex-wrap items-center justify-between gap-2 text-sm">
                <span class="flex items-center gap-2 text-lf-secondary">
                    <LoaderCircle class="animate-spin" size={16} aria-hidden="true" />
                    {$_('backup.restore.uploading')}
                </span>
                <span class="tabular-nums text-lf-muted">{$_('backup.restore.progress', {values: {done: formatBytes(controller.uploadedBytes, $_), total: formatBytes(controller.totalBytes, $_)}})}</span>
            </div>
            <div class="h-2 overflow-hidden rounded-full bg-lf-neutral" role="progressbar" aria-label={$_('backup.restore.uploading')} aria-valuemin={0} aria-valuemax={100} aria-valuenow={uploadPercent ?? undefined}>
                <div class="h-full rounded-full bg-lf-checked transition-[width] duration-300" style:width="{uploadPercent ?? 0}%"></div>
            </div>
            <button
                class="inline-flex items-center gap-2 rounded-lg border border-lf-subtle px-4 py-2 text-sm text-lf-secondary hover:bg-lf-neutral focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                type="button"
                data-testid="restore-cancel-check"
                onclick={() => controller.abortUpload()}
            >
                <X size={16} aria-hidden="true" />
                {$_('backup.restore.cancelUpload')}
            </button>
        </div>
    {/if}

    {#if controller.state === 'checking'}
        <div class="space-y-2" data-testid="restore-check-progress" data-phase={controller.stage?.phase ?? ''}>
            <div class="flex flex-wrap items-center justify-between gap-2 text-sm">
                <span class="flex items-center gap-2 text-lf-secondary">
                    <LoaderCircle class="animate-spin" size={16} aria-hidden="true" />
                    {controller.stage?.phase ? $_(PHASE_KEYS[controller.stage.phase]) : $_('backup.restore.phase.checking')}
                </span>
                {#if controller.stage && checkPercent !== null}
                    <span class="tabular-nums text-lf-muted">{$_('backup.restore.progress', {values: {done: formatBytes(controller.stage.done_bytes, $_), total: formatBytes(controller.stage.total_bytes, $_)}})}</span>
                {/if}
            </div>
            <div class="h-2 overflow-hidden rounded-full bg-lf-neutral" role="progressbar" aria-label={$_('backup.restore.phase.checking')} aria-valuemin={0} aria-valuemax={100} aria-valuenow={checkPercent ?? undefined}>
                {#if checkPercent === null}
                    <div class="h-full w-1/3 animate-pulse rounded-full bg-lf-checked"></div>
                {:else}
                    <div class="h-full rounded-full bg-lf-checked transition-[width] duration-300" style:width="{checkPercent}%"></div>
                {/if}
            </div>
            {#if controller.dropRequested}
                <p class="text-xs text-lf-muted" data-testid="restore-drop-requested">{$_('backup.restore.dropWhenDone')}</p>
            {:else}
                <button
                    class="inline-flex items-center gap-2 rounded-lg border border-lf-subtle px-4 py-2 text-sm text-lf-secondary hover:bg-lf-neutral focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                    type="button"
                    data-testid="restore-cancel-check"
                    onclick={() => controller.dropCheck()}
                >
                    <X size={16} aria-hidden="true" />
                    {$_('backup.restore.cancelCheck')}
                </button>
            {/if}
        </div>
    {/if}

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
        <RestoreReportModal open={reportOpen} report={controller.report} busy={false} onConfirm={() => controller.confirm()} onDrop={() => controller.dropCheck()} onClose={() => (reportOpen = false)} />
    {/if}

    {#if controller.state === 'confirming' || controller.state === 'cancelling'}
        <p class="flex items-center gap-2 text-sm text-lf-secondary" data-testid="restore-working">
            <LoaderCircle class="animate-spin" size={16} aria-hidden="true" />
            {controller.state === 'confirming' ? $_('backup.restore.confirming') : $_('backup.restore.cancelling')}
        </p>
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
