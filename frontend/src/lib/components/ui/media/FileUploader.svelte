<!--
  FileUploader - Generic drag & drop file upload component

  Features:
  - Drag & drop + file browser
  - Multiple file upload support
  - Validates against blocked extensions (executables/scripts)
  - Progress indicator
-->
<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import {t} from '$lib/i18n';
    import {AlertTriangle, File as FileIcon, ImageIcon, Pencil, RefreshCw, Upload, X} from 'lucide-svelte';
    import {isImageFile} from '$lib/utils/files/imageCrop';
    import {formatBytes} from '$lib/utils/files/upload';
    import {uiLocaleStore} from '$lib/stores/app/uiLocale';
    import '$lib/theme/components/media.css';

    export let maxSizeMB: number = 10;
    export let multiple: boolean = true;
    export let accept: string = ''; // e.g. ".csv,.xlsx,.xls" or "image/*"
    /** Hide the built-in Clear/Upload action buttons (let parent handle those) */
    export let hideActions: boolean = false;

    // Blocked extensions (same as backend)
    const BLOCKED_EXTENSIONS = new Set(['.exe', '.dll', '.so', '.dylib', '.bat', '.cmd', '.ps1', '.vbs', '.vbe', '.sh', '.bash', '.csh', '.zsh', '.py', '.pyc', '.pyo', '.pl', '.pm', '.rb', '.php', '.php3', '.php4', '.php5', '.phtml', '.js', '.mjs', '.cjs', '.jar', '.class', '.com', '.scr', '.pif']);

    type _DispatchEvents = {
        upload: {files: File[]};
        error: {message: string};
        change: {files: File[]}; // Emitted when files are selected/changed
        editImage: {file: File; index: number}; // Emitted when user wants to edit an image
        editFile: {file: File; index: number}; // Emitted when user wants to edit a non-image file
    };
    const dispatch = createEventDispatcher();

    let isDragging = false;
    let selectedFiles: File[] = [];
    let originalFiles: Record<number, File> = {}; // Store original files for restore (object for reactivity)
    let editedIndices: number[] = []; // Track which files have been edited (array for reactivity)
    let fileInput: HTMLInputElement;
    let errors: string[] = [];

    function getFileExtension(filename: string): string {
        const idx = filename.lastIndexOf('.');
        return idx >= 0 ? filename.slice(idx).toLowerCase() : '';
    }

    function validateFile(file: File): string | null {
        // Check extension
        const ext = getFileExtension(file.name);
        if (BLOCKED_EXTENSIONS.has(ext)) {
            return `File type "${ext}" is not allowed (executable/script)`;
        }

        // Check size
        if (file.size > maxSizeMB * 1024 * 1024) {
            return `File "${file.name}" is too large. Max: ${maxSizeMB}MB`;
        }

        return null;
    }

    function handleDragOver(event: DragEvent) {
        event.preventDefault();
        isDragging = true;
    }

    function handleDragLeave() {
        isDragging = false;
    }

    function handleDrop(event: DragEvent) {
        event.preventDefault();
        isDragging = false;

        const files = event.dataTransfer?.files;
        if (files && files.length > 0) {
            handleFiles(Array.from(files));
        }
    }

    function handleFileSelect(event: Event) {
        const input = event.target as HTMLInputElement;
        if (input.files && input.files.length > 0) {
            handleFiles(Array.from(input.files));
        }
        // Reset input to allow re-selecting same file
        input.value = '';
    }

    function handleFiles(files: File[]) {
        errors = [];
        const validFiles: File[] = [];

        for (const file of files) {
            const error = validateFile(file);
            if (error) {
                errors.push(error);
            } else {
                validFiles.push(file);
            }
        }

        if (validFiles.length > 0) {
            if (multiple) {
                selectedFiles = [...selectedFiles, ...validFiles];
            } else {
                selectedFiles = [validFiles[0]];
            }
            // Notify that files have changed
            dispatch('change', {files: selectedFiles});
        }

        if (errors.length > 0) {
            dispatch('error', {message: errors.join('\n')});
        }
    }

    function removeFile(index: number) {
        selectedFiles = selectedFiles.filter((_, i) => i !== index);
        dispatch('change', {files: selectedFiles});
    }

    function clearAll() {
        selectedFiles = [];
        errors = [];
        dispatch('change', {files: selectedFiles});
    }

    function uploadFiles() {
        if (selectedFiles.length > 0) {
            dispatch('upload', {files: selectedFiles});
            selectedFiles = [];
        }
    }

    function openFileBrowser() {
        fileInput?.click();
    }

    function editImage(file: File, index: number) {
        dispatch('editImage', {file, index});
    }

    function editFile(file: File, index: number) {
        dispatch('editFile', {file, index});
    }

    // Public method to clear all files (used by parent to externally reset)
    export function clearFiles() {
        clearAll();
    }

    // Public method to replace a file at a specific index (used after crop)
    export function replaceFile(index: number, newFile: File) {
        if (index >= 0 && index < selectedFiles.length) {
            // Save original file for restore (only if not already edited)
            if (!(index in originalFiles)) {
                originalFiles = {...originalFiles, [index]: selectedFiles[index]};
            }
            // Mark as edited - create new array to trigger reactivity
            if (!editedIndices.includes(index)) {
                editedIndices = [...editedIndices, index];
            }

            // Replace file in selectedFiles
            selectedFiles = [...selectedFiles.slice(0, index), newFile, ...selectedFiles.slice(index + 1)];
            dispatch('change', {files: selectedFiles});
        }
    }

    // Restore a file to its original state
    function restoreFile(index: number) {
        const original = originalFiles[index];
        if (original) {
            selectedFiles = [...selectedFiles.slice(0, index), original, ...selectedFiles.slice(index + 1)];
            // Remove from originalFiles
            const {[index]: _, ...rest} = originalFiles;
            originalFiles = rest;
            // Remove from editedIndices
            editedIndices = editedIndices.filter((i) => i !== index);
            dispatch('change', {files: selectedFiles});
        }
    }

    // Check if a file has been edited
    function isEdited(index: number): boolean {
        return editedIndices.includes(index);
    }
</script>

<div class="file-uploader" data-testid="file-uploader">
    <!-- Drop zone -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="drop-zone"
        class:dragging={isDragging}
        class:has-files={selectedFiles.length > 0}
        data-testid="file-drop-zone"
        on:click={openFileBrowser}
        on:dragleave={handleDragLeave}
        on:dragover={handleDragOver}
        on:drop={handleDrop}
        on:keydown={(e) => e.key === 'Enter' && openFileBrowser()}
        role="button"
        tabindex="0"
    >
        <input accept={accept || undefined} bind:this={fileInput} data-testid="file-input" hidden {multiple} on:change={handleFileSelect} type="file" />

        {#if selectedFiles.length === 0}
            <Upload size={32} class="upload-icon" />
            <p class="drop-text">{$t('uploads.dropOrClick')}</p>
            <p class="drop-hint">
                {$t('common.max') || 'Max'}: {maxSizeMB}MB
                {#if multiple}
                    • {$t('common.multipleFiles')}{/if}
            </p>
        {:else}
            <div class="selected-files">
                {#each selectedFiles as file, index (file.name + index)}
                    <div class="file-item" class:edited={editedIndices.includes(index)}>
                        {#if isImageFile(file)}
                            <ImageIcon size={16} class="file-icon image" />
                        {:else}
                            <FileIcon size={16} class="file-icon" />
                        {/if}
                        <span class="file-name">{file.name}</span>
                        {#if editedIndices.includes(index)}
                            <button type="button" class="restore-btn" on:click|stopPropagation={() => restoreFile(index)} title={$t('common.restore') || 'Restore original'} data-testid="file-restore-btn">
                                <RefreshCw size={14} />
                            </button>
                        {/if}
                        {#if isImageFile(file)}
                            <button type="button" class="edit-btn" on:click|stopPropagation={() => editImage(file, index)} title={$t('common.edit') || 'Edit'} data-testid="file-edit-btn">
                                <Pencil size={14} />
                            </button>
                        {:else}
                            <button type="button" class="edit-btn" on:click|stopPropagation={() => editFile(file, index)} title={$t('uploads.rename') || 'Rename'} data-testid="file-edit-btn">
                                <Pencil size={14} />
                            </button>
                        {/if}
                        <span class="file-size">{formatBytes(file.size, $t, $uiLocaleStore)}</span>
                        <button type="button" class="remove-btn" on:click|stopPropagation={() => removeFile(index)} title={$t('common.remove') || 'Remove'}>
                            <X size={14} />
                        </button>
                    </div>
                {/each}
            </div>
        {/if}
    </div>

    <!-- Errors -->
    {#if errors.length > 0}
        <div class="errors">
            <AlertTriangle size={16} />
            <div class="error-list">
                {#each errors as error}
                    <p>{error}</p>
                {/each}
            </div>
        </div>
    {/if}

    <!-- Actions -->
    {#if selectedFiles.length > 0 && !hideActions}
        <div class="actions">
            <button type="button" class="btn btn-secondary" on:click={clearAll} data-testid="file-clear">
                {$t('common.clear') || 'Clear'}
            </button>
            <button type="button" class="btn btn-primary" on:click={uploadFiles} data-testid="file-upload-submit">
                <Upload size={16} />
                {$t('uploads.upload')} ({selectedFiles.length})
            </button>
        </div>
    {/if}
</div>

<style>
    .file-uploader {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .drop-zone {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 150px;
        padding: 1.5rem;
        border: 2px dashed var(--lf-border-input);
        border-radius: 8px;
        background: var(--lf-surface-panel);
        cursor: pointer;
        transition: all 0.2s;
    }

    .drop-zone:hover,
    .drop-zone.dragging {
        border-color: var(--lf-focus);
        background: var(--lf-surface-hover);
    }

    .drop-zone.dragging {
        background: var(--lf-selected);
    }

    .drop-zone.has-files {
        align-items: stretch;
        padding: 1rem;
    }

    :global(.upload-icon) {
        color: var(--lf-text-muted);
        margin-bottom: 0.5rem;
    }

    .drop-text {
        font-size: 0.9375rem;
        font-weight: 500;
        color: var(--lf-text-secondary);
        margin: 0;
    }

    .drop-hint {
        font-size: 0.75rem;
        color: var(--lf-text-muted);
        margin: 0.25rem 0 0;
    }

    /* On the selected tint the muted text falls under 4.5:1 (rule 5, TC-15): the hint reads secondary while dragging. */
    .drop-zone.dragging .drop-hint {
        color: var(--lf-text-secondary);
    }

    .selected-files {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        width: 100%;
    }

    .file-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0.75rem;
        background: var(--lf-surface-card);
        border: 1px solid var(--lf-border-subtle);
        border-radius: 6px;
    }

    .file-item :global(svg) {
        color: var(--lf-text-muted);
        flex-shrink: 0;
    }

    .file-item :global(svg.image) {
        color: var(--lf-cmp-file-uploader-image-icon-text);
    }

    :global(.dark) .file-item :global(svg.image) {
        color: var(--lf-cmp-file-uploader-image-icon-text-dark);
    }

    .file-name {
        flex: 1;
        font-size: 0.8125rem;
        color: var(--lf-text-primary);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .file-size {
        font-size: 0.75rem;
        color: var(--lf-text-muted);
        flex-shrink: 0;
    }

    /* Edited file indicator */
    .file-item.edited {
        border-color: var(--lf-info);
        background: var(--lf-info-soft);
    }

    .edit-btn,
    .remove-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        border: none;
        border-radius: 4px;
        background: transparent;
        color: var(--lf-text-muted);
        cursor: pointer;
        transition: all 0.15s;
    }

    .restore-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        border: none;
        border-radius: 4px;
        background: transparent;
        color: var(--lf-warning);
        cursor: pointer;
        transition: all 0.15s;
    }

    .edit-btn:hover {
        background: var(--lf-info-soft);
        color: var(--lf-info);
    }

    .remove-btn:hover {
        background: var(--lf-danger-soft);
        color: var(--lf-danger);
    }

    .restore-btn:hover {
        background: var(--lf-warning-soft);
        color: var(--lf-warning);
    }

    .errors {
        display: flex;
        gap: 0.5rem;
        padding: 0.75rem;
        background: var(--lf-danger-soft);
        border: 1px solid var(--lf-danger-line);
        border-radius: 6px;
        color: var(--lf-danger-on-soft);
    }

    .error-list {
        flex: 1;
    }

    .error-list p {
        margin: 0;
        font-size: 0.8125rem;
    }

    .error-list p + p {
        margin-top: 0.25rem;
    }

    .actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.5rem;
    }

    .btn {
        display: flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.5rem 1rem;
        font-size: 0.875rem;
        font-weight: 500;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.15s;
    }

    .btn-secondary {
        background: var(--lf-surface-card);
        color: var(--lf-text-secondary);
        box-shadow: inset 0 0 0 1px var(--lf-border-subtle);
    }

    .btn-secondary:hover {
        background: var(--lf-surface-hover);
        color: var(--lf-text-primary);
    }

    .btn-primary {
        background: var(--lf-action);
        color: var(--lf-on-action);
    }

    .btn-primary:hover {
        background: var(--lf-action-hover);
    }
</style>
