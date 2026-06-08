<!--
  BrokerImportFilesModal - Modal for managing BRIM files of a specific broker

  Features:
  - Shows BRIM files for a single broker using DataTable
  - Upload new files (auto-assigned to this broker)
  - Delete files with confirmation
  - Link to full files page with broker filter
  - Confirmation when closing with pending uploads
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {axiosInstance, zodiosApi} from '$lib/api';
    import {trySave} from '$lib/utils/trySave';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {ExternalLink, FileUp, RefreshCw, Trash2, X} from 'lucide-svelte';
    import {fade} from 'svelte/transition';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import FilesTable from '$lib/components/files/FilesTable.svelte';
    import FilePreviewModal from '$lib/components/files/FilePreviewModal.svelte';
    import FileUploader from '$lib/components/ui/media/FileUploader.svelte';
    import {FileEditModal} from '$lib/components/ui/media';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import SelectionBar from '$lib/components/table/SelectionBar.svelte';
    import type {BrimFile, FilePreviewResponse} from '$lib/types';
    import {fetchFilePreview, getFilePreviewError} from '$lib/utils/files/filePreview';

    interface Props {
        /** Whether the modal is open */
        open: boolean;
        /** Broker ID to show files for */
        brokerId: number;
        /** Broker name for display */
        brokerName: string;
        /** Called when modal is closed */
        onClose: () => void;
    }

    let {open, brokerId, brokerName, onClose}: Props = $props();

    // State
    let files = $state<BrimFile[]>([]);
    let loading = $state(true);
    let error = $state<string | null>(null);
    let uploading = $state(false);
    let showUploader = $state(false);

    // Pending files tracking for close confirmation
    let pendingFiles = $state<globalThis.File[]>([]);
    let showCloseConfirm = $state(false);

    // #R6-7 (Batch 4.d-part3) — Bulk delete confirmation gating.
    let confirmBulkDeleteOpen = $state(false);
    let pendingBulkDeleteIds = $state<string[]>([]);

    // File edit (rename) state
    let editingFile = $state<File | null>(null);
    let editingFileIndex = $state<number>(-1);
    let showFileEdit = $state(false);

    // FilesTable ref + selection tracking
    let filesTableRef: FilesTable | undefined = $state(undefined);
    let selectedFileIds = $state<string[]>([]);

    // BRIM preview modal state
    let showPreviewModal = $state(false);
    let previewLoading = $state(false);
    let previewError = $state<string | null>(null);
    let previewData = $state<FilePreviewResponse | null>(null);
    let previewFileId = $state<string | null>(null);
    let previewRequestToken = 0;

    // Load files when modal opens or brokerId changes
    $effect(() => {
        if (open && brokerId) {
            loadFiles();
            // Reset state when opening
            showUploader = false;
            pendingFiles = [];
            error = null;
        } else if (!open) {
            closePreviewModal();
        }
    });

    async function loadFiles() {
        loading = true;
        error = null;
        try {
            const response = await zodiosApi.list_files_api_v1_brokers_import_files_get({
                queries: {broker_ids: [brokerId]},
            });
            files = response as BrimFile[];
        } catch (e) {
            console.error('Failed to load files:', e);
            error = $_('brokers.loadFailed');
        } finally {
            loading = false;
        }
    }

    function handleFileChange(event: CustomEvent<{files: globalThis.File[]}>) {
        pendingFiles = event.detail.files;
    }

    async function handleUpload(event: CustomEvent<{files: globalThis.File[]}>) {
        const uploadFiles = event.detail.files;
        if (!uploadFiles.length) return;

        uploading = true;
        error = null;

        // I-bis #22 (Batch 4.d-part2) — break-at-first-error preserves the
        // existing UX (user sees the offending file name, can remove it and
        // retry). ``toast: false`` because the error is rendered inline in
        // the banner above the file list.
        for (const file of uploadFiles) {
            const formData = new FormData();
            formData.append('file', file);
            const result = await trySave(
                // Use axios directly - Zodios doesn't handle FormData correctly
                () => axiosInstance.post(`/api/v1/brokers/import/upload?broker_id=${brokerId}`, formData),
                {toast: false, fallback: $_('uploads.uploadFailed'), prefix: file.name},
            );
            if (result.status === 'error') {
                error = result.message;
                uploading = false;
                return;
            }
        }

        showUploader = false;
        pendingFiles = [];
        await loadFiles();
        uploading = false;
        // #R6-6 (Batch 4.d-part3) — success toast for batch uploads (aligned
        // with the evolved app-wide save pattern). Errors remain inline in the
        // banner (persistent, dismissible).
        toasts.success($_('uploads.uploadBatchSucceeded', {values: {count: uploadFiles.length}}));
    }

    async function handleDelete(fileId: string) {
        // I-bis #22 (Batch 4.d-part2) — unified error path.
        const result = await trySave(
            () =>
                zodiosApi.delete_file_api_v1_brokers_import_files__file_id__delete(undefined, {
                    params: {file_id: fileId},
                }),
            {toast: false, fallback: $_('uploads.deleteFailed')},
        );
        if (result.status === 'error') {
            error = result.message;
            return;
        }
        await loadFiles();
        // #R6-6 (Batch 4.d-part3) — success toast for single-file delete.
        toasts.success($_('uploads.deleteSucceeded'));
    }

    async function handleDeleteMultiple(fileIds: string[]) {
        // I-bis #22 (Batch 4.d-part2) — collect-all error policy: continue
        // the loop even after a failure, reload the list on completion, and
        // report a summary count. More informative than break-at-first when
        // the user selected multiple files.
        let failedCount = 0;
        let lastMessage = '';
        for (const fileId of fileIds) {
            const result = await trySave(
                () =>
                    zodiosApi.delete_file_api_v1_brokers_import_files__file_id__delete(undefined, {
                        params: {file_id: fileId},
                    }),
                {toast: false, fallback: $_('uploads.deleteFailed')},
            );
            if (result.status === 'error') {
                failedCount++;
                lastMessage = result.message;
            }
        }
        await loadFiles();
        if (failedCount > 0) {
            // Prefer the summary key when more than one failed; for a single
            // failure in a multi-selection the concrete message is clearer.
            error = failedCount === 1 ? lastMessage : $_('uploads.deleteFailedSome', {values: {count: failedCount}});
        } else {
            // #R6-6 (Batch 4.d-part3) — success toast for bulk delete.
            toasts.success($_('uploads.deleteBatchSucceeded', {values: {count: fileIds.length}}));
        }
    }

    // File rename handlers
    function handleEditFile(event: CustomEvent<{file: File; index: number}>) {
        editingFile = event.detail.file;
        editingFileIndex = event.detail.index;
        showFileEdit = true;
    }

    function handleFileEditComplete(event: CustomEvent<{url: string | null; file: File}>) {
        const {file: renamedFile} = event.detail;
        // Replace file in pending list with renamed version
        if (editingFileIndex >= 0 && editingFileIndex < pendingFiles.length) {
            pendingFiles[editingFileIndex] = renamedFile;
            pendingFiles = [...pendingFiles]; // Trigger reactivity
        }
        showFileEdit = false;
        editingFile = null;
    }

    function tryClose() {
        if (pendingFiles.length > 0) {
            showCloseConfirm = true;
        } else {
            onClose();
        }
    }

    function confirmClose() {
        showCloseConfirm = false;
        pendingFiles = [];
        showUploader = false;
        onClose();
    }

    function cancelClose() {
        showCloseConfirm = false;
    }

    // #R6-7 (Batch 4.d-part3) — Bulk delete confirmation gating.
    // Centralised entry point used by both the SelectionBar action and the
    // FilesTable internal ``onDeleteMultiple`` callback, so a single
    // destructive ConfirmModal protects every bulk-delete path.
    function requestBulkDelete(ids: string[]) {
        if (ids.length === 0) return;
        pendingBulkDeleteIds = [...ids];
        confirmBulkDeleteOpen = true;
    }

    async function confirmBulkDelete() {
        const ids = pendingBulkDeleteIds;
        confirmBulkDeleteOpen = false;
        pendingBulkDeleteIds = [];
        await handleDeleteMultiple(ids);
        filesTableRef?.clearSelection();
    }

    function cancelBulkDelete() {
        confirmBulkDeleteOpen = false;
        pendingBulkDeleteIds = [];
    }

    async function openPreview(file: BrimFile) {
        previewFileId = file.file_id;
        showPreviewModal = true;
        previewData = null;
        previewError = null;
        await loadPreview();
    }

    async function loadPreview(sheetName?: string) {
        if (!previewFileId) return;

        const token = ++previewRequestToken;
        previewLoading = true;
        previewError = null;

        try {
            const response = await fetchFilePreview({source: 'brim', fileId: previewFileId}, sheetName);
            if (token === previewRequestToken) {
                previewData = response;
            }
        } catch (error) {
            if (token === previewRequestToken) {
                previewData = null;
                previewError = getFilePreviewError(error, 'Preview failed');
            }
        } finally {
            if (token === previewRequestToken) {
                previewLoading = false;
            }
        }
    }

    async function handlePreviewSheetChange(sheetName: string) {
        if (!sheetName) return;
        await loadPreview(sheetName);
    }

    function closePreviewModal() {
        previewRequestToken += 1;
        showPreviewModal = false;
        previewLoading = false;
        previewError = null;
        previewData = null;
        previewFileId = null;
    }
</script>

<ModalBase maxWidth="900px" onRequestClose={tryClose} {open} testId="import-files-modal" zIndex={50}>
    <!-- Header with title and link -->
    <div class="modal-header">
        <div class="flex items-center gap-2">
            <FileUp class="text-libre-green" size={20} />
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">
                {$_('brokers.importFiles')} - {brokerName}
            </h2>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
            <SelectionBar
                actions={[
                    {
                        id: 'delete',
                        icon: Trash2,
                        label: () => $_('common.delete'),
                        variant: 'danger',
                        onClick: () => {
                            requestBulkDelete(selectedFileIds);
                        },
                    },
                ]}
                onClearSelection={() => filesTableRef?.clearSelection()}
                selectedCount={selectedFileIds.length}
            />
            <ColumnVisibilityToggle tableRef={filesTableRef?.getTableRef()} />
            <a class="manage-link" href="/files?tab=brim&broker={brokerId}">
                <ExternalLink size={14} />
                {$_('brokers.manageFiles')}
            </a>
            <button class="close-btn" onclick={tryClose} title={$_('common.close')}>
                <X size={20} />
            </button>
        </div>
    </div>

    <!-- Upload Area (collapsible) -->
    {#if showUploader && !uploading}
        <div class="upload-area" transition:fade={{duration: 150}}>
            <FileUploader on:upload={handleUpload} on:change={handleFileChange} on:editFile={handleEditFile} on:error={(e) => (error = e.detail.message)} multiple={true} accept=".csv,.xlsx,.xls" />
        </div>
    {:else if uploading}
        <div class="upload-area" transition:fade={{duration: 150}}>
            <div class="flex items-center justify-center gap-2 py-8 text-gray-500">
                <RefreshCw size={20} class="animate-spin" />
                <span>{$_('common.uploading')}...</span>
            </div>
        </div>
    {/if}

    <!-- Error Message -->
    <InfoBanner dismissible message={error} ondismiss={() => (error = '')} variant="error" />

    <!-- Content -->
    <div class="modal-body">
        {#if loading && files.length === 0}
            <div class="loading-state">
                <RefreshCw size={32} class="animate-spin text-gray-400" />
                <p class="text-gray-500 mt-2">{$_('common.loading')}</p>
            </div>
        {:else if files.length === 0}
            <div class="empty-state">
                <FileUp size={48} class="text-gray-300 dark:text-gray-600" />
                <p class="text-gray-500 dark:text-gray-400 mt-2">{$_('brokers.noImportFiles')}</p>
                <p class="text-gray-400 dark:text-gray-500 text-sm mt-1">{$_('brokers.uploadHint')}</p>
            </div>
        {:else}
            <FilesTable bind:this={filesTableRef} {files} type="brim" onDelete={handleDelete} onDeleteMultiple={requestBulkDelete} onPreview={(file) => openPreview(file as BrimFile)} showBrokerColumn={false} onSelectionChange={(ids) => (selectedFileIds = ids)} />
        {/if}
    </div>

    <!-- Footer with actions -->
    <div class="modal-footer">
        <div class="footer-actions">
            <button class="btn btn-ghost" disabled={loading} onclick={loadFiles} title={$_('common.refresh')}>
                <RefreshCw class={loading ? 'animate-spin' : ''} size={16} />
                {$_('common.refresh')}
            </button>
            <button class="btn {showUploader ? 'btn-secondary' : 'btn-primary'}" disabled={uploading} onclick={() => (showUploader = !showUploader)}>
                <FileUp size={16} />
                {showUploader ? $_('common.close') : $_('uploads.upload')}
            </button>
        </div>
    </div>
</ModalBase>

<FilePreviewModal open={showPreviewModal} preview={previewData} loading={previewLoading} error={previewError} onRequestClose={closePreviewModal} onSheetChange={handlePreviewSheetChange} zIndex={60} />

<!-- File Rename Modal (for BRIM files) -->
{#if editingFile}
    <FileEditModal
        file={editingFile}
        open={showFileEdit}
        uploadOnComplete={false}
        on:complete={handleFileEditComplete}
        on:cancel={() => {
            showFileEdit = false;
            editingFile = null;
        }}
    />
{/if}

<!-- Close Confirmation Modal (warning style, not danger) -->
<ConfirmModal
    confirmText={$_('common.discard')}
    danger={false}
    items={pendingFiles.map((f) => f.name)}
    itemsLabel={$_('uploads.filesToUpload')}
    message={$_('uploads.pendingUploadsMessage')}
    onCancel={cancelClose}
    onConfirm={confirmClose}
    open={showCloseConfirm}
    title={$_('uploads.pendingUploads')}
/>

<!-- #R6-7 (Batch 4.d-part3) — Bulk delete destructive confirm. -->
<ConfirmModal confirmText={$_('common.delete')} danger={true} message={$_('uploads.confirmBulkDelete.message', {values: {count: pendingBulkDeleteIds.length}})} onCancel={cancelBulkDelete} onConfirm={confirmBulkDelete} open={confirmBulkDeleteOpen} title={$_('uploads.confirmBulkDelete.title')} />

<style>
    /* Backdrop and modal-content styles handled by ModalBase */

    .modal-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1rem 1.5rem;
        border-bottom: 1px solid #e5e7eb;
        flex-shrink: 0;
    }

    :global(.dark) .modal-header {
        border-bottom-color: #374151;
    }

    .close-btn {
        padding: 0.5rem;
        border-radius: 0.5rem;
        color: #6b7280;
        transition: all 0.15s;
    }

    .close-btn:hover {
        background-color: #f3f4f6;
        color: #374151;
    }

    :global(.dark) .close-btn:hover {
        background-color: #374151;
        color: #d1d5db;
    }

    .btn {
        display: inline-flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.5rem 1rem;
        font-size: 0.875rem;
        font-weight: 500;
        border-radius: 0.5rem;
        transition: all 0.15s;
    }

    .btn-primary {
        background-color: #1a4031;
        color: white;
    }

    .btn-primary:hover {
        background-color: #143326;
    }

    .btn-secondary {
        background-color: #6b7280;
        color: white;
    }

    .btn-secondary:hover {
        background-color: #4b5563;
    }

    .btn-ghost {
        color: #6b7280;
    }

    .btn-ghost:hover {
        background-color: #f3f4f6;
        color: #374151;
    }

    :global(.dark) .btn-ghost:hover {
        background-color: #374151;
        color: #d1d5db;
    }

    .btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .upload-area {
        padding: 1rem 1.5rem;
        border-bottom: 1px solid #e5e7eb;
        background-color: #f9fafb;
        flex-shrink: 0;
        max-height: 250px;
        overflow-y: auto;
    }

    :global(.dark) .upload-area {
        background-color: #111827;
        border-bottom-color: #374151;
    }

    .modal-body {
        flex: 1;
        overflow-y: auto;
        padding: 1rem 1.5rem;
        min-height: 0; /* Required for flex child to scroll properly */
    }

    .loading-state,
    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 3rem;
        text-align: center;
    }

    .modal-footer {
        display: flex;
        justify-content: flex-end;
        padding: 0.75rem 1.5rem;
        border-top: 1px solid #e5e7eb;
        background-color: #f9fafb;
        flex-shrink: 0;
    }

    :global(.dark) .modal-footer {
        background-color: #111827;
        border-top-color: #374151;
    }

    .footer-actions {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .manage-link {
        display: inline-flex;
        align-items: center;
        gap: 0.375rem;
        font-size: 0.875rem;
        color: #1a4031;
        text-decoration: none;
        transition: all 0.15s;
    }

    .manage-link:hover {
        text-decoration: underline;
    }

    :global(.dark) .manage-link {
        color: #10b981;
    }
</style>
