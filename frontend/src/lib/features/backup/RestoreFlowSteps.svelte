<!--
  The steps of a restore between the archive chosen and its report (lot B5b; shared since A10): the password of a secure
  backup (state `password`), the archive being sent (`uploading`), its check on a copy (`checking`), and a request out
  (`confirming`, `cancelling`). Drawn by the restore card, for an archive uploaded from the computer, and by the modal of a
  kept backup (A10, T-15), each with its own controller.

  `testIdPrefix` names every test id: `restore` in the card (`restore-password-form`, `restore-upload-progress`…), another
  in the modal, so that both can be on the page at once. The password leaves the field as soon as it is submitted.
-->
<script lang="ts">
    import {KeyRound, LoaderCircle, TriangleAlert, X} from 'lucide-svelte';
    import PasswordInput from '$lib/components/ui/input/PasswordInput.svelte';
    import {_} from '$lib/i18n';
    import {formatBytes} from '$lib/utils/files/upload';
    import type {RestorePhase} from './backupApi';
    import type {RestoreFlowController} from './restoreFlow.svelte';
    import {restoreErrorKey} from './restoreText';

    interface Props {
        controller: RestoreFlowController;
        /** The start of every test id and of the password field's id. */
        testIdPrefix?: string;
    }

    let {controller, testIdPrefix = 'restore'}: Props = $props();

    const PHASE_KEYS: Record<RestorePhase, string> = {
        decrypting: 'backup.restore.phase.decrypting',
        checking: 'backup.restore.phase.checking',
        unpacking: 'backup.restore.phase.unpacking',
        upgrading: 'backup.restore.phase.upgrading',
        verifying: 'backup.restore.phase.verifying',
    };

    let restorePassword = $state('');

    const uploadPercent = $derived(controller.totalBytes > 0 ? Math.min(100, Math.round((controller.uploadedBytes / controller.totalBytes) * 100)) : null);
    const checkPercent = $derived.by(() => {
        const stage = controller.stage;
        if (stage === null || stage.total_bytes <= 0) return null;
        return Math.min(100, Math.round((stage.done_bytes / stage.total_bytes) * 100));
    });

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

{#if controller.state === 'password'}
    <form class="space-y-3" data-testid="{testIdPrefix}-password-form" onsubmit={submitPassword} novalidate>
        <p class="flex items-start gap-2 text-sm text-lf-secondary">
            <KeyRound class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
            <span>{$_('backup.restore.password.intro')}</span>
        </p>
        <div class="space-y-2">
            <label class="block text-sm font-medium text-lf-secondary" for="{testIdPrefix}-password">{$_('backup.restore.password.label')}</label>
            <PasswordInput neverSaved bind:value={restorePassword} disabled={controller.submitting} hasError={controller.errorCode !== null} id="{testIdPrefix}-password" name="{testIdPrefix}-password" testId="{testIdPrefix}-password" />
        </div>
        {#if controller.errorCode !== null}
            <p class="flex items-start gap-2 text-sm text-lf-danger" role="alert" data-testid="{testIdPrefix}-password-error" data-error-code={controller.errorCode}>
                <TriangleAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
                <span>{$_(restoreErrorKey(controller.errorCode))}</span>
            </p>
        {/if}
        <div class="flex flex-wrap items-center gap-2">
            <button
                class="inline-flex items-center gap-2 rounded-lg bg-lf-action px-4 py-2 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus disabled:cursor-not-allowed disabled:opacity-50"
                type="submit"
                data-testid="{testIdPrefix}-password-submit"
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
                data-testid="{testIdPrefix}-password-cancel"
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
    <div class="space-y-2" data-testid="{testIdPrefix}-upload-progress">
        {#if controller.totalBytes > 0}
            <!-- C9-7: what the check will take, said before it does: the archive itself, then its opened version. -->
            <p class="text-xs text-lf-muted" data-testid="{testIdPrefix}-space-needed">{$_('backup.restore.spaceNeeded', {values: {size: formatBytes(controller.totalBytes, $_)}})}</p>
        {/if}
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
            data-testid="{testIdPrefix}-cancel-check"
            onclick={() => controller.abortUpload()}
        >
            <X size={16} aria-hidden="true" />
            {$_('backup.restore.cancelUpload')}
        </button>
    </div>
{/if}

{#if controller.state === 'checking'}
    <div class="space-y-2" data-testid="{testIdPrefix}-check-progress" data-phase={controller.stage?.phase ?? ''}>
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
            <p class="text-xs text-lf-muted" data-testid="{testIdPrefix}-drop-requested">{$_('backup.restore.dropWhenDone')}</p>
        {:else}
            <button
                class="inline-flex items-center gap-2 rounded-lg border border-lf-subtle px-4 py-2 text-sm text-lf-secondary hover:bg-lf-neutral focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                type="button"
                data-testid="{testIdPrefix}-cancel-check"
                onclick={() => controller.dropCheck()}
            >
                <X size={16} aria-hidden="true" />
                {$_('backup.restore.cancelCheck')}
            </button>
        {/if}
    </div>
{/if}

{#if controller.state === 'confirming' || controller.state === 'cancelling'}
    <p class="flex items-center gap-2 text-sm text-lf-secondary" data-testid="{testIdPrefix}-working">
        <LoaderCircle class="animate-spin" size={16} aria-hidden="true" />
        {controller.state === 'confirming' ? $_('backup.restore.confirming') : $_('backup.restore.cancelling')}
    </p>
{/if}
