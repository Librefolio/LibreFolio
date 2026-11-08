<!--
  «Restore» on a row of the kept backups (A10, T-15; C9-9 before): a modal of its own, where the list is, with the steps of
  the restore from the backup taken on the server to the restart. The password of a secure backup and the check on a copy
  are drawn here (`RestoreFlowSteps`); the report, the password check of an administrator and the confirmation are the
  report's modal (`RestoreReportModal`), then the overlay of the restart (`RestartOverlay`). The restore card stays for an
  archive from the computer, and for the checks left for later.

  Its own controller, with no storage: a reload forgets the modal, and the check it left shows in the card, to resume or
  discard. A restore that already waits for the next start is said, and nothing is started.

  Closed on a check left for later or dropped, on a refused restart, or by the user: `onClose`, and the card reads its
  state again (`notifyRestoreChanged`). A check that is still running when the modal closes goes on, listed in the card.

  Published state: `data-state` (the controller's), `data-error-code`, `data-busy` on `restore-kept-modal`.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {ArchiveRestore, LoaderCircle, RefreshCw, ShieldAlert, TriangleAlert, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {_} from '$lib/i18n';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {formatDateTime} from '$lib/utils/core/formatDateTime';
    import {verifyRestorePassword} from './backupApi';
    import {RestoreFlowController} from './restoreFlow.svelte';
    import RestoreFlowSteps from './RestoreFlowSteps.svelte';
    import RestoreReportModal from './RestoreReportModal.svelte';
    import RestartOverlay from './RestartOverlay.svelte';
    import {notifyRestoreChanged} from './restoreSignal.svelte';
    import {restoreErrorKey} from './restoreText';

    interface Props {
        /** The kept backup to restore. */
        jobId: string;
        /** When it was made: the modal names it. */
        createdAt: string;
        onClose: () => void;
    }

    let {jobId, createdAt, onClose}: Props = $props();

    const controller = new RestoreFlowController({
        storage: null,
        onEvent: (name, detail) =>
            notify({
                name,
                detail,
                toast: name === 'backup.restore.failed' ? {variant: 'error', message: $_(restoreErrorKey(String(detail.code ?? '')))} : undefined,
            }),
    });

    // The restore of this backup started: from then on, a state with nothing in hand ends the modal.
    let started = $state(false);
    let closed = false;

    async function start() {
        started = true;
        await controller.fromKept(jobId);
    }

    onMount(() => {
        void (async () => {
            await controller.load();
            // A restore confirmed already waits for the next start: said, nothing started (the card offers it).
            if (controller.state === 'idle') await start();
        })();
        return () => controller.dispose();
    });

    function finish() {
        if (closed) return;
        closed = true;
        notifyRestoreChanged();
        onClose();
    }

    // Left for later, dropped, or a restart refused (the restore then waits in the card, which offers it again).
    $effect(() => {
        if (started && (controller.state === 'idle' || controller.state === 'pending')) finish();
    });

    /** The user closes: a secure backup forgets its password step; a check under way goes on, listed in the card. */
    function close() {
        if (controller.state === 'confirming' || controller.state === 'cancelling' || controller.state === 'restarting') return;
        if (controller.state === 'password') controller.cancelPassword();
        if (controller.state === 'uploading') controller.abortUpload();
        finish();
    }

    async function later() {
        await controller.later();
    }

    const working = $derived(controller.state === 'loading' || (controller.state === 'uploading' && controller.totalBytes === 0));
    const alreadyWaiting = $derived(!started && (controller.state === 'pending' || controller.state === 'in_progress'));
</script>

{#if controller.state === 'report' && controller.report}
    <RestoreReportModal
        open
        report={controller.report}
        onConfirm={(ownerUserId) => controller.confirm(ownerUserId)}
        onDrop={() => controller.dropCheck()}
        onLater={() => void later()}
        stageId={controller.stage?.stage_id ?? null}
        onVerify={(username, password) => verifyRestorePassword(controller.stage?.stage_id ?? '', username, password)}
        onClose={() => void later()}
    />
{:else if controller.state !== 'restarting'}
    <ModalBase open maxWidth="lg" onRequestClose={close} testId="restore-kept-modal" labelledBy="restore-kept-title" trapFocus restoreFocus>
        <div class="space-y-4 p-5 text-lf-primary" data-testid="restore-kept" data-state={controller.state} data-error-code={controller.errorCode ?? ''} data-busy={controller.busy ? 'true' : 'false'} aria-busy={controller.busy}>
            <header class="flex items-start justify-between gap-3">
                <div class="flex items-start gap-3">
                    <ArchiveRestore class="mt-0.5 shrink-0 text-lf-secondary" size={22} aria-hidden="true" />
                    <div class="space-y-1">
                        <h2 id="restore-kept-title" class="text-base font-semibold text-lf-primary">{$_('backup.restore.kept.title')}</h2>
                        <p class="text-sm text-lf-secondary" data-testid="restore-kept-backup">{$_('backup.restore.kept.backupOf', {values: {date: formatDateTime(createdAt)}})}</p>
                    </div>
                </div>
                <button
                    class="rounded-lg p-1 text-lf-muted hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus disabled:cursor-not-allowed disabled:opacity-50"
                    type="button"
                    aria-label={$_('common.close')}
                    data-testid="restore-kept-close"
                    disabled={controller.state === 'confirming' || controller.state === 'cancelling'}
                    onclick={close}
                >
                    <X size={18} aria-hidden="true" />
                </button>
            </header>

            <p class="flex items-start gap-2 rounded-lg border border-lf-danger-line bg-lf-danger-soft p-3 text-sm text-lf-danger-on-soft" data-testid="restore-kept-replace-notice">
                <ShieldAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
                <span>{$_('backup.restore.replaceNotice')}</span>
            </p>

            {#if working}
                <p class="flex items-center gap-2 text-sm text-lf-secondary" data-testid="restore-kept-preparing">
                    <LoaderCircle class="animate-spin" size={16} aria-hidden="true" />
                    {$_('backup.restore.kept.preparing')}
                </p>
            {:else if alreadyWaiting}
                <p class="flex items-start gap-2 rounded-lg border border-lf-info-line bg-lf-info-soft p-3 text-sm text-lf-info-on-soft" data-testid="restore-kept-already-waiting">
                    <TriangleAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
                    <span>{$_('backup.restore.kept.alreadyWaiting')}</span>
                </p>
            {:else}
                <RestoreFlowSteps {controller} testIdPrefix="restore-kept" />
            {/if}

            {#if controller.state === 'failed' && controller.errorCode !== null}
                <div class="flex items-start gap-2 rounded-lg border border-lf-danger-line bg-lf-danger-soft p-3 text-sm text-lf-danger-on-soft" role="alert" data-testid="restore-kept-error" data-error-code={controller.errorCode}>
                    <TriangleAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
                    <span>{$_(restoreErrorKey(controller.errorCode), {values: {limit: controller.errorLimitMb ?? ''}})}</span>
                </div>
                <div class="flex flex-wrap items-center gap-2">
                    <button
                        class="inline-flex items-center gap-2 rounded-lg border border-lf-subtle px-4 py-2 text-sm text-lf-secondary hover:bg-lf-neutral focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                        type="button"
                        data-testid="restore-kept-retry"
                        onclick={() => void start()}
                    >
                        <RefreshCw size={16} aria-hidden="true" />
                        {$_('backup.restore.retry')}
                    </button>
                </div>
            {/if}
        </div>
    </ModalBase>
{/if}

{#if controller.state === 'restarting' && controller.outcome !== null}
    <RestartOverlay outcome={controller.outcome} slow={controller.slow} notStopping={controller.notStopping} status={controller.outcomeStatus} unreadableReason={controller.unreadableReason} onBack={() => controller.load()} />
{/if}
