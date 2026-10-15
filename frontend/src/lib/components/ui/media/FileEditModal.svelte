<!--
  FileEditModal - Modal for editing file properties before upload (non-image files)

  Features:
  - Rename file before upload
  - Change file extension/format
  - Consistent API with ImageEditModal (same events, same pattern)
  - Fallback modal for files that don't have specialized editors
  - Uses ModalBase for backdrop/keydown/z-index handling
-->
<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import {_} from '$lib/i18n';
    import {Check, FileIcon, Loader2, RefreshCw, X} from 'lucide-svelte';
    import {formatBytes, uploadFile} from '$lib/utils/files/upload';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {uiLocaleStore} from '$lib/stores/app/uiLocale';
    import '$lib/theme/components/media.css';

    // Props
    export let open: boolean = false;
    export let file: File | null = null;
    export let uploadOnComplete: boolean = true;
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
            const uploadedUrl = await uploadFile(renamedFile);

            dispatch('complete', {url: uploadedUrl, file: renamedFile});
        } catch (err) {
            console.error('Upload failed:', err);
            error = err instanceof Error ? err.message : 'Upload failed';
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
                {$_('uploads.editFile') || 'Edit File'}
            </h2>
            <div class="header-actions">
                {#if hasChanges}
                    <button type="button" class="restore-btn" on:click={restoreOriginal} title={$_('common.resetAllChanges') || 'Reset All'}>
                        <RefreshCw size={16} />
                    </button>
                {/if}
                <button type="button" class="close-btn" on:click={requestClose} title={$_('common.close') || 'Close'}>
                    <X size={20} />
                </button>
            </div>
        </div>

        <!-- Body -->
        <div class="modal-body">
            <!-- File name editing - top (consistent with ImageEditModal) -->
            <div class="filename-editor">
                <label class="filename-label" for="file-edit-name">
                    {$_('uploads.fileName') || 'File name'}:
                </label>
                <div class="filename-input-group">
                    <!-- svelte-ignore a11y_autofocus -->
                    <input id="file-edit-name" type="text" class="filename-input" bind:value={editedBaseName} placeholder="file" on:input={handleNameChange} autofocus />
                    <span class="file-extension">{fileExtension}</span>
                </div>
            </div>

            <!-- File info (metadata below) -->
            <div class="file-info-row">
                <span class="info-label">{$_('uploads.fileSize') || 'Size'}:</span>
                <span class="info-value">{formatBytes(file.size, $_, $uiLocaleStore)}</span>
            </div>
            <div class="file-info-row">
                <span class="info-label">{$_('common.type') || 'Type'}:</span>
                <span class="info-value">{file.type || 'unknown'}</span>
            </div>

            <!-- Error -->
            {#if error}
                <div class="error-message">{error}</div>
            {/if}
        </div>

        <!-- Footer -->
        <div class="modal-footer">
            <button type="button" class="btn btn-secondary" on:click={requestClose} disabled={isUploading}>
                {$_('common.cancel') || 'Cancel'}
            </button>
            <button type="button" class="btn btn-primary" on:click={handleConfirm} disabled={isUploading} data-testid="file-edit-confirm">
                {#if isUploading}
                    <Loader2 size={16} class="animate-spin" />
                    {$_('common.uploading') || 'Uploading...'}
                {:else}
                    <Check size={16} />
                    {#if uploadOnComplete}
                        {$_('uploads.renameAndUpload') || 'Rename & Upload'}
                    {:else}
                        {$_('uploads.rename') || 'Rename'}
                    {/if}
                {/if}
            </button>
        </div>
    </ModalBase>
{/if}

<!-- Confirmation dialog (uses ModalBase at higher z-index) -->
<ModalBase maxWidth="max-w-sm" onRequestClose={cancelClose} open={showCloseConfirm} zIndex={zIndex + 10}>
    <div class="confirm-content">
        <div class="confirm-header">
            <span class="confirm-icon">⚠️</span>
            <h3>{$_('common.discardChanges') || 'Discard changes?'}</h3>
        </div>
        <p class="confirm-message">
            {$_('common.discardChangesMessage') || 'You have unsaved changes. Are you sure you want to close?'}
        </p>
        <div class="confirm-actions">
            <button class="btn btn-secondary" on:click={cancelClose}>
                {$_('common.cancel') || 'Cancel'}
            </button>
            <button class="btn btn-warning" on:click={confirmClose}>
                {$_('common.discardAndClose') || 'Discard & Close'}
            </button>
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
        border-bottom: 1px solid var(--lf-cmp-file-edit-divider-border);
    }

    :global(.dark) .modal-header {
        border-bottom-color: var(--lf-cmp-file-edit-divider-border-dark);
    }

    .header-actions {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    .restore-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border-radius: 0.5rem;
        border: none;
        background: var(--lf-cmp-file-edit-restore-btn-bg);
        color: var(--lf-cmp-file-edit-restore-btn-text);
        cursor: pointer;
        transition: all 0.15s;
    }

    .restore-btn:hover {
        background: var(--lf-cmp-file-edit-restore-btn-hover-bg);
        color: var(--lf-cmp-file-edit-restore-btn-hover-text);
    }

    .modal-title {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--lf-cmp-file-edit-title-text);
        margin: 0;
    }

    :global(.dark) .modal-title {
        color: var(--lf-cmp-file-edit-title-text-dark);
    }

    .close-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border-radius: 0.5rem;
        border: none;
        background: transparent;
        color: var(--lf-cmp-file-edit-close-btn-text);
        cursor: pointer;
        transition: all 0.15s;
    }

    .close-btn:hover {
        background: var(--lf-cmp-file-edit-close-btn-hover-bg);
        color: var(--lf-cmp-file-edit-text);
    }

    :global(.dark) .close-btn:hover {
        background: var(--lf-cmp-file-edit-close-btn-hover-bg-dark);
        color: var(--lf-cmp-file-edit-text-dark);
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
        color: var(--lf-cmp-file-edit-muted-text);
        font-weight: 500;
    }

    .info-value {
        color: var(--lf-cmp-file-edit-info-value-text);
        font-family: monospace;
        font-size: 0.75rem;
    }

    :global(.dark) .info-label {
        color: var(--lf-cmp-file-edit-muted-text-dark);
    }

    :global(.dark) .info-value {
        color: var(--lf-cmp-file-edit-info-value-text-dark);
    }

    .filename-editor {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .filename-label {
        font-size: 0.8125rem;
        font-weight: 500;
        color: var(--lf-cmp-file-edit-text);
    }

    :global(.dark) .filename-label {
        color: var(--lf-cmp-file-edit-text-dark);
    }

    .filename-input-group {
        display: flex;
    }

    .filename-input {
        flex: 1;
        padding: 0.5rem 0.75rem;
        font-size: 0.875rem;
        border: 1px solid var(--lf-cmp-file-edit-field-border);
        border-right: none;
        border-radius: 0.375rem 0 0 0.375rem;
        background: var(--lf-cmp-file-edit-field-bg);
        color: var(--lf-cmp-file-edit-field-text);
        outline: none;
        transition: border-color 0.15s;
    }

    .filename-input:focus {
        border-color: var(--lf-cmp-file-edit-field-focus-border);
    }

    :global(.dark) .filename-input {
        background: var(--lf-cmp-file-edit-field-bg-dark);
        border-color: var(--lf-cmp-file-edit-field-border-dark);
        color: var(--lf-cmp-file-edit-field-text-dark);
    }

    :global(.dark) .filename-input:focus {
        border-color: var(--lf-cmp-file-edit-field-focus-border-dark);
    }

    .file-extension {
        display: flex;
        align-items: center;
        padding: 0.5rem 0.75rem;
        font-size: 0.875rem;
        border: 1px solid var(--lf-cmp-file-edit-field-border);
        border-radius: 0 0.375rem 0.375rem 0;
        background: var(--lf-cmp-file-edit-file-extension-bg);
        color: var(--lf-cmp-file-edit-muted-text);
        font-family: monospace;
    }

    :global(.dark) .file-extension {
        background: var(--lf-cmp-file-edit-file-extension-bg-dark);
        border-color: var(--lf-cmp-file-edit-field-border-dark);
        color: var(--lf-cmp-file-edit-muted-text-dark);
    }

    .error-message {
        padding: 0.75rem 1rem;
        background-color: var(--lf-cmp-file-edit-error-message-bg);
        border: 1px solid var(--lf-cmp-file-edit-error-message-border);
        border-radius: 0.5rem;
        color: var(--lf-cmp-file-edit-error-message-text);
        font-size: 0.875rem;
    }

    :global(.dark) .error-message {
        background-color: var(--lf-cmp-file-edit-error-message-bg-dark);
        border-color: var(--lf-cmp-file-edit-error-message-border-dark);
    }

    .modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
        padding: 1rem 1.5rem;
        border-top: 1px solid var(--lf-cmp-file-edit-divider-border);
        background: var(--lf-cmp-file-edit-footer-bg);
    }

    :global(.dark) .modal-footer {
        background: var(--lf-cmp-file-edit-footer-bg-dark);
        border-top-color: var(--lf-cmp-file-edit-divider-border-dark);
    }

    .btn {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        font-size: 0.875rem;
        font-weight: 500;
        border-radius: 0.5rem;
        border: none;
        cursor: pointer;
        transition: all 0.15s;
    }

    .btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .btn-primary {
        background: var(--lf-cmp-file-edit-btn-primary-bg);
        color: var(--lf-cmp-file-edit-on-fill-text);
    }

    .btn-primary:hover:not(:disabled) {
        background: var(--lf-cmp-file-edit-btn-primary-hover-bg);
    }

    :global(.dark) .btn-primary {
        background: var(--lf-cmp-file-edit-btn-primary-bg-dark);
    }

    :global(.dark) .btn-primary:hover:not(:disabled) {
        background: var(--lf-cmp-file-edit-btn-primary-hover-bg-dark);
    }

    .btn-secondary {
        background: var(--lf-cmp-file-edit-btn-secondary-bg);
        color: var(--lf-cmp-file-edit-text);
    }

    .btn-secondary:hover:not(:disabled) {
        background: var(--lf-cmp-file-edit-btn-secondary-hover-bg);
    }

    :global(.dark) .btn-secondary {
        background: var(--lf-cmp-file-edit-btn-secondary-bg-dark);
        color: var(--lf-cmp-file-edit-text-dark);
    }

    :global(.dark) .btn-secondary:hover:not(:disabled) {
        background: var(--lf-cmp-file-edit-btn-secondary-hover-bg-dark);
    }

    :global(.animate-spin) {
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        from {
            transform: rotate(0deg);
        }
        to {
            transform: rotate(360deg);
        }
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
        color: var(--lf-cmp-file-edit-confirm-title-text);
    }

    :global(.dark) .confirm-header h3 {
        color: var(--lf-cmp-file-edit-confirm-title-text-dark);
    }

    .confirm-message {
        color: var(--lf-cmp-file-edit-muted-text);
        margin-bottom: 1.5rem;
        line-height: 1.5;
    }

    :global(.dark) .confirm-message {
        color: var(--lf-cmp-file-edit-muted-text-dark);
    }

    .confirm-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
    }

    .btn-warning {
        background: var(--lf-cmp-file-edit-btn-warning-bg);
        color: var(--lf-cmp-file-edit-on-fill-text);
        border: none;
    }

    .btn-warning:hover {
        background: var(--lf-cmp-file-edit-btn-warning-hover-bg);
    }
</style>
