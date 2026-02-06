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
    import {ExternalLink, FileUp, RefreshCw, X} from 'lucide-svelte';
    import {fade, scale} from 'svelte/transition';
    import FilesTable from '$lib/components/files/FilesTable.svelte';
    import FileUploader from '$lib/components/ui/media/FileUploader.svelte';
    import ConfirmModal from '$lib/components/table/ConfirmModal.svelte';
    import type {BrimFile} from '$lib/types';

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

    // Load files when modal opens or brokerId changes
    $effect(() => {
        if (open && brokerId) {
            loadFiles();
            // Reset state when opening
            showUploader = false;
            pendingFiles = [];
            error = null;
        }
    });

    async function loadFiles() {
        loading = true;
        error = null;
        try {
            const response = await zodiosApi.list_files_api_v1_brokers_import_files_get({
                queries: {broker_ids: [brokerId]}
            });
            files = response as BrimFile[];
        } catch (e) {
            console.error('Failed to load files:', e);
            error = $_('brokers.loadFailed');
        } finally {
            loading = false;
        }
    }

    function handleFileChange(event: CustomEvent<{ files: globalThis.File[] }>) {
        pendingFiles = event.detail.files;
    }

    async function handleUpload(event: CustomEvent<{ files: globalThis.File[] }>) {
        const uploadFiles = event.detail.files;
        if (!uploadFiles.length) return;

        uploading = true;
        error = null;

        try {
            for (const file of uploadFiles) {
                const formData = new FormData();
                formData.append('file', file);
                // Use axios directly - Zodios doesn't handle FormData correctly
                await axiosInstance.post(`/api/v1/brokers/import/upload?broker_id=${brokerId}`, formData);
            }

            showUploader = false;
            pendingFiles = [];
            await loadFiles();
        } catch (e) {
            console.error('Upload failed:', e);
            error = e instanceof Error ? e.message : $_('uploads.uploadFailed');
        } finally {
            uploading = false;
        }
    }

    async function handleDelete(fileId: string) {
        try {
            await zodiosApi.delete_file_api_v1_brokers_import_files__file_id__delete(undefined, {
                params: {file_id: fileId}
            });
            await loadFiles();
        } catch (e) {
            console.error('Delete failed:', e);
            error = $_('uploads.deleteFailed');
        }
    }

    async function handleDeleteMultiple(fileIds: string[]) {
        try {
            for (const fileId of fileIds) {
                await zodiosApi.delete_file_api_v1_brokers_import_files__file_id__delete(undefined, {
                    params: {file_id: fileId}
                });
            }
            await loadFiles();
        } catch (e) {
            console.error('Delete failed:', e);
            error = $_('uploads.deleteFailed');
        }
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

    function handleBackdropClick(event: MouseEvent) {
        if (event.target === event.currentTarget) {
            tryClose();
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            tryClose();
        }
    }
</script>

<svelte:window onkeydown={handleKeydown}/>

{#if open}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
            class="modal-backdrop"
            data-testid="import-files-modal"
            onclick={handleBackdropClick}
            transition:fade={{ duration: 150 }}
    >
        <div
                class="modal-content"
                transition:scale={{ duration: 200, start: 0.95 }}
                onclick={(e) => e.stopPropagation()}
        >
            <!-- Header with title and link -->
            <div class="modal-header">
                <div class="flex items-center gap-2">
                    <FileUp size={20} class="text-libre-green"/>
                    <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">
                        {$_('brokers.importFiles')} - {brokerName}
                    </h2>
                </div>
                <div class="flex items-center gap-3">
                    <a
                            href="/files?tab=brim&broker={brokerId}"
                            class="manage-link"
                    >
                        <ExternalLink size={14}/>
                        {$_('brokers.manageFiles')}
                    </a>
                    <button
                            class="close-btn"
                            onclick={tryClose}
                            title={$_('common.close')}
                    >
                        <X size={20}/>
                    </button>
                </div>
            </div>

            <!-- Upload Area (collapsible) -->
            {#if showUploader && !uploading}
                <div class="upload-area" transition:fade={{ duration: 150 }}>
                    <FileUploader
                            on:upload={handleUpload}
                            on:change={handleFileChange}
                            on:error={(e) => error = e.detail.message}
                            multiple={true}
                            accept=".csv,.xlsx,.xls"
                    />
                </div>
            {:else if uploading}
                <div class="upload-area" transition:fade={{ duration: 150 }}>
                    <div class="flex items-center justify-center gap-2 py-8 text-gray-500">
                        <RefreshCw size={20} class="animate-spin"/>
                        <span>{$_('common.uploading')}...</span>
                    </div>
                </div>
            {/if}

            <!-- Error Message -->
            {#if error}
                <div class="error-message">
                    {error}
                </div>
            {/if}

            <!-- Content -->
            <div class="modal-body">
                {#if loading && files.length === 0}
                    <div class="loading-state">
                        <RefreshCw size={32} class="animate-spin text-gray-400"/>
                        <p class="text-gray-500 mt-2">{$_('common.loading')}</p>
                    </div>
                {:else if files.length === 0}
                    <div class="empty-state">
                        <FileUp size={48} class="text-gray-300 dark:text-gray-600"/>
                        <p class="text-gray-500 dark:text-gray-400 mt-2">{$_('brokers.noImportFiles')}</p>
                        <p class="text-gray-400 dark:text-gray-500 text-sm mt-1">{$_('brokers.uploadHint')}</p>
                    </div>
                {:else}
                    <FilesTable
                            {files}
                            type="brim"
                            onDelete={handleDelete}
                            onDeleteMultiple={handleDeleteMultiple}
                            showBrokerColumn={false}
                    />
                {/if}
            </div>

            <!-- Footer with actions -->
            <div class="modal-footer">
                <div class="footer-actions">
                    <button
                            class="btn btn-ghost"
                            onclick={loadFiles}
                            disabled={loading}
                            title={$_('common.refresh')}
                    >
                        <RefreshCw size={16} class={loading ? 'animate-spin' : ''}/>
                        {$_('common.refresh')}
                    </button>
                    <button
                            class="btn {showUploader ? 'btn-secondary' : 'btn-primary'}"
                            onclick={() => showUploader = !showUploader}
                            disabled={uploading}
                    >
                        <FileUp size={16}/>
                        {showUploader ? $_('common.close') : $_('uploads.upload')}
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}

<!-- Close Confirmation Modal (warning style, not danger) -->
<ConfirmModal
        confirmText={$_('common.discard')}
        danger={false}
        items={pendingFiles.map(f => f.name)}
        itemsLabel={$_('uploads.filesToUpload')}
        message={$_('uploads.pendingUploadsMessage')}
        onCancel={cancelClose}
        onConfirm={confirmClose}
        open={showCloseConfirm}
        title={$_('uploads.pendingUploads')}
/>

<style>
    .modal-backdrop {
        position: fixed;
        inset: 0;
        z-index: 50;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: rgba(0, 0, 0, 0.5);
        padding: 1rem;
    }

    .modal-content {
        background: white;
        border-radius: 1rem;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
        width: 100%;
        max-width: 900px;
        max-height: 85vh;
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
    }

    :global(.dark) .upload-area {
        background-color: #111827;
        border-bottom-color: #374151;
    }

    .error-message {
        margin: 0.75rem 1.5rem;
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

    .modal-body {
        flex: 1;
        overflow: auto;
        padding: 1rem 1.5rem;
        min-height: 300px;
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
