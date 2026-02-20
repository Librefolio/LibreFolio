<!--
  FileEditModal - Modal for editing file properties before upload (non-image files)

  Features:
  - Rename file before upload
  - Change file extension/format
  - Consistent API with ImageEditModal (same events, same pattern)
  - Fallback modal for files that don't have specialized editors
-->
<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import {_} from '$lib/i18n';
    import {X, Check, Loader2, FileIcon} from 'lucide-svelte';
    import {axiosInstance} from '$lib/api';

    // Props
    export let open: boolean = false;
    export let file: File | null = null;
    export let uploadOnComplete: boolean = true;

    const dispatch = createEventDispatcher<{
        complete: {url: string | null; file: File};
        cancel: void;
        error: {message: string};
    }>();

    // Internal state
    let isUploading = false;
    let error: string | null = null;
    let hasChanges = false;
    let showCloseConfirm = false;

    // File name editing
    let editedBaseName: string = '';
    let fileExtension: string = '';

    // Initialize when file changes
    $: if (file && open) {
        const parts = file.name.split('.');
        if (parts.length > 1) {
            fileExtension = '.' + parts.pop()!;
            editedBaseName = parts.join('.');
        } else {
            editedBaseName = file.name;
            fileExtension = '';
        }
        hasChanges = false;
        showCloseConfirm = false;
        error = null;
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

    function handleBackdropClick(event: MouseEvent) {
        if (event.target === event.currentTarget) {
            requestClose();
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            requestClose();
        }
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
            const renamedFile = new File([file], finalFileName, { type: file.type });

            if (!uploadOnComplete) {
                // Just return the renamed file
                dispatch('complete', {url: null, file: renamedFile});
                return;
            }

            // Upload to backend
            const formData = new FormData();
            formData.append('file', renamedFile);

            const response = await axiosInstance.post('/api/v1/uploads', formData);
            const uploadedUrl = response.data.file?.url || response.data.url;

            if (!uploadedUrl) {
                throw new Error('No URL in upload response');
            }

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

<svelte:window on:keydown={open ? handleKeydown : undefined} />

{#if open && file}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="modal-backdrop" on:click={handleBackdropClick}>
        <div class="modal-content" role="dialog" aria-modal="true" aria-labelledby="file-edit-title">
            <!-- Header -->
            <div class="modal-header">
                <h2 id="file-edit-title" class="modal-title">
                    <FileIcon size={20} />
                    {$_('uploads.editFile') || 'Edit File'}
                </h2>
                <button
                    type="button"
                    class="close-btn"
                    on:click={requestClose}
                    title={$_('common.close') || 'Close'}
                >
                    <X size={20} />
                </button>
            </div>

            <!-- Body -->
            <div class="modal-body">
                <!-- File info -->
                <div class="file-info-row">
                    <span class="info-label">{$_('uploads.fileSize') || 'Size'}:</span>
                    <span class="info-value">{formatSize(file.size)}</span>
                </div>
                <div class="file-info-row">
                    <span class="info-label">{$_('common.type') || 'Type'}:</span>
                    <span class="info-value">{file.type || 'unknown'}</span>
                </div>

                <!-- File name editing -->
                <div class="filename-editor">
                    <label class="filename-label" for="file-edit-name">
                        {$_('uploads.fileName') || 'File name'}:
                    </label>
                    <div class="filename-input-group">
                        <input
                            id="file-edit-name"
                            type="text"
                            class="filename-input"
                            bind:value={editedBaseName}
                            placeholder="file"
                            on:input={handleNameChange}
                        />
                        <span class="file-extension">{fileExtension}</span>
                    </div>
                </div>

                <!-- Error -->
                {#if error}
                    <div class="error-message">{error}</div>
                {/if}
            </div>

            <!-- Footer -->
            <div class="modal-footer">
                <button
                    type="button"
                    class="btn btn-secondary"
                    on:click={requestClose}
                    disabled={isUploading}
                >
                    {$_('common.cancel') || 'Cancel'}
                </button>
                <button
                    type="button"
                    class="btn btn-primary"
                    on:click={handleConfirm}
                    disabled={isUploading}
                >
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
        </div>
    </div>
{/if}

<!-- Confirmation dialog -->
{#if showCloseConfirm}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="confirm-backdrop" on:click|self={cancelClose}>
        <div class="confirm-dialog">
            <div class="confirm-header">
                <span class="confirm-icon">⚠️</span>
                <h3>{$_('uploads.discardChanges') || 'Discard changes?'}</h3>
            </div>
            <p class="confirm-message">
                {$_('uploads.discardChangesMessage') || 'You have unsaved changes. Are you sure you want to close?'}
            </p>
            <div class="confirm-actions">
                <button class="btn btn-secondary" on:click={cancelClose}>
                    {$_('common.cancel') || 'Cancel'}
                </button>
                <button class="btn btn-warning" on:click={confirmClose}>
                    {$_('uploads.discardAndClose') || 'Discard'}
                </button>
            </div>
        </div>
    </div>
{/if}

<script context="module" lang="ts">
    function formatSize(bytes: number): string {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }
</script>

<style>
    .modal-backdrop {
        position: fixed;
        inset: 0;
        z-index: 50;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: rgba(0, 0, 0, 0.6);
        padding: 1rem;
    }

    .modal-content {
        background: white;
        border-radius: 1rem;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
        width: 100%;
        max-width: 460px;
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }

    :global(.dark) .modal-content {
        background: #1f2937;
        border: 1px solid #374151;
    }

    .modal-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1rem 1.5rem;
        border-bottom: 1px solid #e5e7eb;
    }

    :global(.dark) .modal-header {
        border-bottom-color: #374151;
    }

    .modal-title {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 1.125rem;
        font-weight: 600;
        color: #111827;
        margin: 0;
    }

    :global(.dark) .modal-title {
        color: #f3f4f6;
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
        color: #6b7280;
        cursor: pointer;
        transition: all 0.15s;
    }

    .close-btn:hover {
        background: #f3f4f6;
        color: #374151;
    }

    :global(.dark) .close-btn:hover {
        background: #374151;
        color: #d1d5db;
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
        color: #6b7280;
        font-weight: 500;
    }

    .info-value {
        color: #374151;
        font-family: monospace;
        font-size: 0.75rem;
    }

    :global(.dark) .info-label { color: #9ca3af; }
    :global(.dark) .info-value { color: #e5e7eb; }

    .filename-editor {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .filename-label {
        font-size: 0.8125rem;
        font-weight: 500;
        color: #374151;
    }

    :global(.dark) .filename-label { color: #d1d5db; }

    .filename-input-group {
        display: flex;
    }

    .filename-input {
        flex: 1;
        padding: 0.5rem 0.75rem;
        font-size: 0.875rem;
        border: 1px solid #d1d5db;
        border-right: none;
        border-radius: 0.375rem 0 0 0.375rem;
        background: white;
        color: #374151;
        outline: none;
        transition: border-color 0.15s;
    }

    .filename-input:focus { border-color: #1a4031; }

    :global(.dark) .filename-input {
        background: #374151;
        border-color: #4b5563;
        color: #f3f4f6;
    }

    :global(.dark) .filename-input:focus { border-color: #10b981; }

    .file-extension {
        display: flex;
        align-items: center;
        padding: 0.5rem 0.75rem;
        font-size: 0.875rem;
        border: 1px solid #d1d5db;
        border-radius: 0 0.375rem 0.375rem 0;
        background: #f3f4f6;
        color: #6b7280;
        font-family: monospace;
    }

    :global(.dark) .file-extension {
        background: #4b5563;
        border-color: #4b5563;
        color: #9ca3af;
    }

    .error-message {
        padding: 0.75rem 1rem;
        background-color: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 0.5rem;
        color: #dc2626;
        font-size: 0.875rem;
    }

    :global(.dark) .error-message {
        background-color: rgba(220, 38, 38, 0.1);
        border-color: rgba(220, 38, 38, 0.3);
    }

    .modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
        padding: 1rem 1.5rem;
        border-top: 1px solid #e5e7eb;
        background: #f9fafb;
    }

    :global(.dark) .modal-footer {
        background: #111827;
        border-top-color: #374151;
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

    .btn:disabled { opacity: 0.5; cursor: not-allowed; }

    .btn-primary { background: #1a4031; color: white; }
    .btn-primary:hover:not(:disabled) { background: #143326; }
    :global(.dark) .btn-primary { background: #10b981; }
    :global(.dark) .btn-primary:hover:not(:disabled) { background: #059669; }

    .btn-secondary { background: #e5e7eb; color: #374151; }
    .btn-secondary:hover:not(:disabled) { background: #d1d5db; }
    :global(.dark) .btn-secondary { background: #374151; color: #d1d5db; }
    :global(.dark) .btn-secondary:hover:not(:disabled) { background: #4b5563; }

    :global(.animate-spin) { animation: spin 1s linear infinite; }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

    /* Confirmation Dialog */
    .confirm-backdrop {
        position: fixed;
        inset: 0;
        z-index: 100;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: rgba(0, 0, 0, 0.7);
    }

    .confirm-dialog {
        background: white;
        border-radius: 0.75rem;
        padding: 1.5rem;
        max-width: 400px;
        width: 90%;
        box-shadow: 0 25px 50px rgba(0, 0, 0, 0.25);
    }

    :global(.dark) .confirm-dialog {
        background: #1f2937;
        border: 1px solid #374151;
    }

    .confirm-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 0.75rem;
    }

    .confirm-icon { font-size: 1.5rem; }

    .confirm-header h3 {
        margin: 0;
        font-size: 1.125rem;
        font-weight: 600;
        color: #d97706;
    }

    :global(.dark) .confirm-header h3 { color: #fbbf24; }

    .confirm-message {
        color: #6b7280;
        margin-bottom: 1.5rem;
        line-height: 1.5;
    }

    :global(.dark) .confirm-message { color: #9ca3af; }

    .confirm-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
    }

    .btn-warning {
        background: #f59e0b;
        color: white;
        border: none;
    }

    .btn-warning:hover { background: #d97706; }
</style>

