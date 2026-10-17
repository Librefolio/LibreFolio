<!--
  Over the whole page while the server restarts to apply a restore (lot B5b). Developer decision P8: once the restore is
  kept, no message, and the page goes to the sign-in page (`restoreNavigation`); when it did not go through, this screen
  says so, with the reason.
-->
<script lang="ts">
    import {LoaderCircle, TriangleAlert} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {_} from '$lib/i18n';
    import type {RestoreStatus} from './backupApi';
    import type {RestartOutcome} from './restoreFlow.svelte';
    import {restoreReasonKey, restoreWaitingKey} from './restoreText';

    interface Props {
        outcome: RestartOutcome;
        /** The server has been away for a while: say how to start it again. */
        slow?: boolean;
        /** The server never stopped, and the restore still waits (B-16): say how to restart it, and offer the way back. */
        notStopping?: boolean;
        /** The status read once the server came back: its `reason` (rolled back) or `waiting` (not applied). */
        status?: RestoreStatus | null;
        /** Back to the Backup tab, with the status read again. */
        onBack: () => void;
    }

    let {outcome, slow = false, notStopping = false, status = null, onBack}: Props = $props();

    const reason = $derived(status?.reason ?? null);
    const waiting = $derived(status?.waiting ?? null);

    const failed = $derived(outcome === 'rolled_back' || outcome === 'still_pending');
</script>

<ModalBase open zIndex={80} maxWidth="md" closeOnBackdropClick={false} closeOnEscape={false} labelledBy="restart-overlay-title" trapFocus>
    <div class="space-y-4 p-5 text-lf-primary" data-testid="restart-overlay" data-outcome={outcome} data-slow={slow ? 'true' : 'false'} data-not-stopping={notStopping ? 'true' : 'false'} data-reason={reason ?? ''} data-waiting={waiting ?? ''}>
        {#if failed}
            <h2 id="restart-overlay-title" class="flex items-center gap-2 text-base font-semibold">
                <TriangleAlert class="shrink-0 text-lf-warning" size={20} aria-hidden="true" />
                {$_('backup.restore.restart.failedTitle')}
            </h2>
            <p class="text-sm text-lf-secondary" data-testid="restart-detail">
                {outcome === 'rolled_back' ? $_('backup.restore.restart.rolledBack', {values: {reason: $_(restoreReasonKey(reason))}}) : $_('backup.restore.restart.stillPending', {values: {waiting: $_(restoreWaitingKey(waiting))}})}
            </p>
            <button class="inline-flex items-center gap-2 rounded-lg border border-lf-subtle px-4 py-2 text-sm text-lf-secondary hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus" type="button" data-testid="restart-back" onclick={onBack}>
                {$_('backup.restore.restart.back')}
            </button>
        {:else}
            <!-- Waiting, or kept: the page is on its way to the sign-in page, with no message of success. -->
            <h2 id="restart-overlay-title" class="flex items-center gap-2 text-base font-semibold">
                <LoaderCircle class="shrink-0 animate-spin text-lf-secondary" size={20} aria-hidden="true" />
                {$_('backup.restore.restart.waitingTitle')}
            </h2>
            <p class="text-sm text-lf-secondary">{$_('backup.restore.restart.waiting')}</p>
            {#if slow}
                <p class="flex items-start gap-2 rounded-lg border border-lf-warning-line bg-lf-warning-soft p-3 text-sm text-lf-warning-on-soft" data-testid="restart-slow">
                    <TriangleAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
                    <span>{$_('backup.restore.restart.slow')}</span>
                </p>
            {/if}
            {#if notStopping}
                <p class="flex items-start gap-2 rounded-lg border border-lf-warning-line bg-lf-warning-soft p-3 text-sm text-lf-warning-on-soft" data-testid="restart-not-stopped">
                    <TriangleAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
                    <span>{$_('backup.restore.restart.notStopped')}</span>
                </p>
                <button class="inline-flex items-center gap-2 rounded-lg border border-lf-subtle px-4 py-2 text-sm text-lf-secondary hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus" type="button" data-testid="restart-back" onclick={onBack}>
                    {$_('backup.restore.restart.back')}
                </button>
            {/if}
        {/if}
    </div>
</ModalBase>
