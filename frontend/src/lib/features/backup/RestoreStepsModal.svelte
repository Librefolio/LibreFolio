<!--
  The window of a restore before its report (A10, T-15): a title, the reminder that a restore replaces the data of every
  user, then the steps (`RestoreFlowSteps`: the password of a secure backup, the archive sent, its check). The developer
  wanted every restore in a window: the restore card opens this one for an archive from the computer, the modal of a kept
  backup for a row of the list; the report then opens in its own window (`RestoreReportModal`).

  The steps' test ids start with `testIdPrefix`; the window is `<testIdPrefix>-steps-modal`. What goes under the steps
  (a message, a refusal) is the caller's `children`.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';
    import {ArchiveRestore, ShieldAlert, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {_} from '$lib/i18n';
    import type {RestoreFlowController} from './restoreFlow.svelte';
    import RestoreFlowSteps from './RestoreFlowSteps.svelte';

    interface Props {
        controller: RestoreFlowController;
        title: string;
        /** Under the title: which archive. */
        subtitle?: string | null;
        testIdPrefix: string;
        /** The steps are replaced by `children` (a wait before the first step, a restore already waiting). */
        hideSteps?: boolean;
        onClose: () => void;
        children?: Snippet;
    }

    let {controller, title, subtitle = null, testIdPrefix, hideSteps = false, onClose, children}: Props = $props();

    // A request out (a confirmation, a drop) is not left half-way.
    const locked = $derived(controller.state === 'confirming' || controller.state === 'cancelling');

    function requestClose() {
        if (!locked) onClose();
    }
</script>

<ModalBase open maxWidth="lg" onRequestClose={requestClose} testId="{testIdPrefix}-steps-modal" labelledBy="{testIdPrefix}-steps-title" trapFocus restoreFocus>
    <div class="space-y-4 p-5 text-lf-primary">
        <header class="flex items-start justify-between gap-3">
            <div class="flex items-start gap-3">
                <ArchiveRestore class="mt-0.5 shrink-0 text-lf-secondary" size={22} aria-hidden="true" />
                <div class="min-w-0 space-y-1">
                    <h2 id="{testIdPrefix}-steps-title" class="text-base font-semibold text-lf-primary">{title}</h2>
                    {#if subtitle}
                        <p class="break-words text-sm text-lf-secondary" data-testid="{testIdPrefix}-steps-subtitle">{subtitle}</p>
                    {/if}
                </div>
            </div>
            <button
                class="rounded-lg p-1 text-lf-muted hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus disabled:cursor-not-allowed disabled:opacity-50"
                type="button"
                aria-label={$_('common.close')}
                data-testid="{testIdPrefix}-close"
                disabled={locked}
                onclick={requestClose}
            >
                <X size={18} aria-hidden="true" />
            </button>
        </header>

        <p class="flex items-start gap-2 rounded-lg border border-lf-danger-line bg-lf-danger-soft p-3 text-sm text-lf-danger-on-soft" data-testid="{testIdPrefix}-replace-notice">
            <ShieldAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
            <span>{$_('backup.restore.replaceNotice')}</span>
        </p>

        {#if !hideSteps}
            <RestoreFlowSteps {controller} {testIdPrefix} />
        {/if}
        {@render children?.()}
    </div>
</ModalBase>
