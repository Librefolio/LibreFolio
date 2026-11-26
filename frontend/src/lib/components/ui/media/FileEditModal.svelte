<!--
  FileEditModal - Modal for editing file properties before upload (non-image files)

  Features:
  - Rename file before upload
  - Change file extension/format
  - Consistent API with ImageEditModal (same events, same pattern)
  - Fallback modal for files that don't have specialized editors
  - Uses ModalBase for backdrop/keydown/z-index handling
  - The standard buttons (85 BTN-2b): the ✕ is `CloseButton`, the reset an amber ghost icon, the confirm `busy` while it
    uploads (the spinner and «Uploading…» are the Button's own)
-->
<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import {_} from '$lib/i18n';
    import {Check, FileIcon, RefreshCw} from 'lucide-svelte';
    import {formatBytes, uploadFile} from '$lib/utils/files/upload';
    import StorageLimitRefusal from '$lib/components/ui/feedback/StorageLimitRefusal.svelte';
    import {storageLimitNumbersOfError, type StorageLimitNumbers} from '$lib/utils/files/storageLimit';
    import type {UploadScope} from '$lib/types';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import Button from '$lib/components/ui/button/Button.svelte';
    import CloseButton from '$lib/components/ui/button/CloseButton.svelte';
    import {uiLocaleStore} from '$lib/stores/app/uiLocale';

    // Props
    export let open: boolean = false;
    export let file: File | null = null;
    export let uploadOnComplete: boolean = true;
    /** Who sees the renamed file once uploaded: the Files page passes personal; without it the backend decides */
    export let scope: UploadScope | undefined = undefined;
    /** Z-index for modal stacking (default 60 = second-level modal) */
    export let zIndex: number = 60;

    type _DispatchEvents = {
        complete: {url: string | null; file: File};
        cancel: void;
        error: {message: string};
    };
    const dispatch = createEventDispatcher();

    // Internal state
    let isUploading = false;
    let error: string | null = null;
    /** C9-1: the space limit refused the upload: said here, in the dialog, with what to do. */
    let refusal: StorageLimitNumbers | null = null;
    let hasChanges = false;
    let showCloseConfirm = false;

    // File name editing
    let editedBaseName: string = '';
    let fileExtension: string = '';
    let originalBaseName: string = ''; // For restore
    let initializedForFile: File | null = null; // Track which file we've initialized for

    // Initialize when file changes (not on every re-render)
    $: if (file && open && file !== initializedForFile) {
        initializedForFile = file;
        const parts = file.name.split('.');
        if (parts.length > 1) {
            fileExtension = '.' + parts.pop()!;
            editedBaseName = parts.join('.');
        } else {
            editedBaseName = file.name;
            fileExtension = '';
        }
        originalBaseName = editedBaseName;
        hasChanges = false;
        showCloseConfirm = false;
        error = null;
        refusal = null;
    }

    // Reset tracking when modal closes
    $: if (!open) {
        initializedForFile = null;
    }

    function restoreOriginal() {
        editedBaseName = originalBaseName;
        hasChanges = false;
    }

    function handleCancel() {
        dispatch('cancel');
    }

    function requestClose() {
        if (hasChanges) {
            showCloseConfirm = true;
        } else {
            handleCancel();
        }
    }

    function confirmClose() {
        showCloseConfirm = false;
        handleCancel();
    }

    function cancelClose() {
        showCloseConfirm = false;
    }

    function handleNameChange() {
        hasChanges = true;
    }

    async function handleConfirm() {
        if (!file) return;

        isUploading = true;
        error = null;
        refusal = null;

        try {
            const finalFileName = `${editedBaseName || 'file'}${fileExtension}`;

            // Create renamed file
            const renamedFile = new File([file], finalFileName, {type: file.type});

            if (!uploadOnComplete) {
                // Just return the renamed file
                dispatch('complete', {url: null, file: renamedFile});
                return;
            }

            // Upload to backend
            const uploadedUrl = await uploadFile(renamedFile, undefined, scope);

            dispatch('complete', {url: uploadedUrl, file: renamedFile});
        } catch (err) {
            console.error('Upload failed:', err);
            error = err instanceof Error ? err.message : $_('uploads.uploadFailed');
            refusal = storageLimitNumbersOfError(err);
            dispatch('error', {message: error});
        } finally {
            isUploading = false;
        }
    }
</script>

{#if file}
    <ModalBase {open} {zIndex} maxWidth="max-w-md" onRequestClose={requestClose}>
        <!-- Header -->
        <div class="modal-header" data-testid="file-edit-modal">
            <h2 class="modal-title">
                <FileIcon size={20} />
                {$_('uploads.editFile')}
            </h2>
            <div class="header-actions">
                {#if hasChanges}
                    <Button label={$_('common.resetAllChanges')} icon={RefreshCw} display="icon" variant="ghost" tone="warning" onclick={restoreOriginal} data-testid="file-edit-reset" />
                {/if}
                <CloseButton onclick={requestClose} data-testid="file-edit-close" />
            </div>
        </div>

        <!-- Body -->
        <div class="modal-body">
            <!-- File name editing - top (consistent with ImageEditModal) -->
            <div class="filename-editor">
                <label class="filename-label" for="file-edit-name">
                    {$_('uploads.fileName')}:
                </label>
                <div class="filename-input-group">
                    <!-- svelte-ignore a11y_autofocus -->
                    <input id="file-edit-name" type="text" class="filename-input" bind:value={editedBaseName} placeholder="file" on:input={handleNameChange} autofocus />
                    <span class="file-extension">{fileExtension}</span>
                </div>
            </div>

            <!-- File info (metadata below) -->
            <div class="file-info-row">
                <span class="info-label">{$_('uploads.fileSize')}:</span>
                <span class="info-value">{formatBytes(file.size, $_, $uiLocaleStore)}</span>
            </div>
            <div class="file-info-row">
                <span class="info-label">{$_('common.type')}:</span>
                <span class="info-value">{file.type || 'unknown'}</span>
            </div>

            <!-- Error -->
            {#if refusal}
                <StorageLimitRefusal numbers={refusal} />
            {:else if error}
                <div class="error-message">{error}</div>
            {/if}
        </div>

        <!-- Footer -->
        <div class="modal-footer">
            <Button label={$_('common.cancel')} variant="secondary" disabled={isUploading} onclick={requestClose} data-testid="file-edit-cancel" />
            <Button label={$_(uploadOnComplete ? 'uploads.renameAndUpload' : 'uploads.rename')} icon={Check} variant="primary" busy={isUploading} busyLabel={$_('common.uploading')} onclick={handleConfirm} data-testid="file-edit-confirm" />
        </div>
    </ModalBase>
{/if}

<!-- Confirmation dialog (uses ModalBase at higher z-index) -->
<ModalBase maxWidth="max-w-sm" onRequestClose={cancelClose} open={showCloseConfirm} zIndex={zIndex + 10}>
    <div class="confirm-content">
        <div class="confirm-header">
            <span class="confirm-icon">⚠️</span>
            <h3>{$_('common.discardChanges')}</h3>
        </div>
        <p class="confirm-message">
            {$_('common.discardChangesMessage')}
        </p>
        <div class="confirm-actions">
            <Button label={$_('common.cancel')} variant="secondary" onclick={cancelClose} data-testid="file-edit-discard-cancel" />
            <Button label={$_('common.discardAndClose')} variant="warning" onclick={confirmClose} data-testid="file-edit-discard-confirm" />
        </div>
    </div>
</ModalBase>

<style>
    /* No backdrop/modal-content styles needed — handled by ModalBase */

    .modal-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1rem 1.5rem;
        border-bottom: 1px solid var(--lf-border-subtle);
    }

    .header-actions {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    .modal-title {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--lf-text-primary);
        margin: 0;
    }

    .modal-body {
        padding: 1.5rem;
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .file-info-row {
        display: flex;
        justify-content: space-between;
        font-size: 0.8125rem;
    }

    .info-label {
        color: var(--lf-text-muted);
        font-weight: 500;
    }

    .info-value {
        color: var(--lf-text-secondary);
        font-family: monospace;
        font-size: 0.75rem;
    }

    .filename-editor {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .filename-label {
        font-size: 0.8125rem;
        font-weight: 500;
        color: var(--lf-text-secondary);
    }

    .filename-input-group {
        display: flex;
    }

    .filename-input {
        flex: 1;
        padding: 0.5rem 0.75rem;
        font-size: 0.875rem;
        border: 1px solid var(--lf-border-input);
        border-right: none;
        border-radius: 0.375rem 0 0 0.375rem;
        background: var(--lf-surface-field);
        color: var(--lf-text-primary);
        outline: none;
        transition: border-color 0.15s;
    }

    .filename-input::placeholder {
        color: var(--lf-text-placeholder);
    }

    .filename-input:focus {
        border-color: var(--lf-focus);
    }

    .file-extension {
        display: flex;
        align-items: center;
        padding: 0.5rem 0.75rem;
        font-size: 0.875rem;
        border: 1px solid var(--lf-border-input);
        border-radius: 0 0.375rem 0.375rem 0;
        background: var(--lf-surface-panel);
        color: var(--lf-text-muted);
        font-family: monospace;
    }

    .error-message {
        padding: 0.75rem 1rem;
        background-color: var(--lf-danger-soft);
        border: 1px solid var(--lf-danger-line);
        border-radius: 0.5rem;
        color: var(--lf-danger-on-soft);
        font-size: 0.875rem;
    }

    .modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
        padding: 1rem 1.5rem;
        border-top: 1px solid var(--lf-border-subtle);
        background: var(--lf-surface-panel);
    }

    /* Confirmation Dialog Content */
    .confirm-content {
        padding: 1.5rem;
    }

    .confirm-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 0.75rem;
    }

    .confirm-icon {
        font-size: 1.5rem;
    }

    .confirm-header h3 {
        margin: 0;
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--lf-warning);
    }

    .confirm-message {
        color: var(--lf-text-muted);
        margin-bottom: 1.5rem;
        line-height: 1.5;
    }

    .confirm-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
    }
</style>
