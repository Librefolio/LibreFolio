<!--
  DataExportModal — the small dialog of the data editors' «Export» button (FB-30).

  The user picks CSV or JSON; the caller downloads the file (`onexport(format)`). A download that fails keeps the dialog
  open with an error, so the user can try again; while it runs, Export cannot be pressed twice.

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {Download} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import Button from '$lib/components/ui/button/Button.svelte';
    import CloseButton from '$lib/components/ui/button/CloseButton.svelte';
    import type {BackupFormat} from '$lib/api/backupDownload';
    import {extractErrorMessage} from '$lib/utils/trySave';

    interface Props {
        open?: boolean;
        /** What is exported, as the dialog names it («Export prices») */
        title: string;
        /** Downloads the file in the chosen format; a rejection keeps the dialog open */
        onexport: (format: BackupFormat) => Promise<void>;
        onclose?: () => void;
    }

    let {open = false, title, onexport, onclose}: Props = $props();

    let format: BackupFormat = $state('csv');
    let busy = $state(false);
    let error: string | null = $state(null);

    // A dialog opened again starts from CSV, without the last error
    $effect(() => {
        if (open) {
            format = 'csv';
            error = null;
        }
    });

    async function confirm() {
        if (busy) return;
        busy = true;
        error = null;
        try {
            await onexport(format);
            onclose?.();
        } catch (e) {
            console.error('Data export failed:', e);
            error = extractErrorMessage(e, $t('common.unknownError'));
        } finally {
            busy = false;
        }
    }

    const formats: BackupFormat[] = ['csv', 'json'];
</script>

<ModalBase maxWidth="md" onRequestClose={() => onclose?.()} {open} testId="data-export-modal">
    <div class="flex items-center justify-between p-4 border-b border-lf-subtle">
        <h2 class="text-lg font-semibold text-lf-primary">{title}</h2>
        <CloseButton size="sm" onclick={() => onclose?.()} data-testid="data-export-close" />
    </div>

    <div class="p-4 space-y-3">
        <p class="text-sm text-lf-secondary">{$t('dataEditor.exportChoose')}</p>
        <div class="flex gap-4" role="radiogroup" aria-label={$t('dataEditor.exportChoose')}>
            {#each formats as option (option)}
                <label class="flex items-center gap-2 text-sm text-lf-primary cursor-pointer">
                    <input checked={format === option} data-testid="data-export-format-{option}" name="data-export-format" onchange={() => (format = option)} type="radio" value={option} />
                    <span class="font-mono uppercase">{option}</span>
                </label>
            {/each}
        </div>
        {#if error}
            <p class="text-sm text-lf-danger" data-testid="data-export-error">{error}</p>
        {/if}
    </div>

    <div class="flex items-center justify-end gap-2 p-4 border-t border-lf-subtle">
        <Button label={$t('common.cancel')} variant="secondary" onclick={() => onclose?.()} data-testid="data-export-cancel" />
        <Button label={$t('dataEditor.exportAction')} icon={Download} variant="primary" {busy} onclick={confirm} data-testid="data-export-confirm" />
    </div>
</ModalBase>
