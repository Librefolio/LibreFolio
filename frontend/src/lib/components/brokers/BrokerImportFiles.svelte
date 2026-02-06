<script lang="ts">
    /**
     * BrokerImportFiles - Shows BRIM files for a specific broker
     * Used in broker detail page
     */
    import {onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {axiosInstance, zodiosApi} from '$lib/api';
    import {FileText, FileUp, RefreshCw, Trash2} from 'lucide-svelte';
    import ConfirmModal from '$lib/components/table/ConfirmModal.svelte';
    import type {BrimFile} from '$lib/types';

    // Props
    interface Props {
        brokerId: number;
    }

    let {brokerId}: Props = $props();

    // State
    let files = $state<BrimFile[]>([]);
    let loading = $state(true);
    let error = $state<string | null>(null);
    let uploading = $state(false);

    // Delete confirmation modal state
    let showDeleteConfirm = $state(false);
    let pendingDeleteFileId = $state<string | null>(null);
    let pendingDeleteFileName = $state<string>('');

    // File input ref
    let fileInputRef: HTMLInputElement;

    onMount(async () => {
        await loadFiles();
    });

    async function loadFiles() {
        loading = true;
        error = null;
        try {
            const response = await zodiosApi.list_files_api_v1_brokers_import_files_get({
                queries: {broker_ids: [brokerId]}
            });
            // API returns array directly
            files = response as BrimFile[];
        } catch (e) {
            console.error('Failed to load files:', e);
            error = $_('files.loadFailed');
        } finally {
            loading = false;
        }
    }

    async function handleUpload(event: Event) {
        const input = event.target as HTMLInputElement;
        const file = input.files?.[0];
        if (!file) return;

        uploading = true;
        error = null;

        try {
            const formData = new FormData();
            formData.append('file', file);
            // Use axios directly - Zodios doesn't handle FormData correctly
            await axiosInstance.post(`/api/v1/brokers/import/upload?broker_id=${brokerId}`, formData);

            await loadFiles();
        } catch (e) {
            console.error('Upload failed:', e);
            error = e instanceof Error ? e.message : $_('files.uploadFailed');
        } finally {
            uploading = false;
            // Reset input
            if (input) input.value = '';
        }
    }

    async function handleDelete(fileId: string) {
        // Find file name for confirmation message
        const file = files.find(f => f.file_id === fileId);
        pendingDeleteFileId = fileId;
        pendingDeleteFileName = file?.filename ?? '';
        showDeleteConfirm = true;
    }

    async function confirmDelete() {
        if (!pendingDeleteFileId) return;

        try {
            await zodiosApi.delete_file_api_v1_brokers_import_files__file_id__delete(undefined, {
                params: {file_id: pendingDeleteFileId}
            });
            await loadFiles();
        } catch (e) {
            console.error('Delete failed:', e);
            error = $_('files.deleteFailed');
        } finally {
            showDeleteConfirm = false;
            pendingDeleteFileId = null;
            pendingDeleteFileName = '';
        }
    }

    function cancelDelete() {
        showDeleteConfirm = false;
        pendingDeleteFileId = null;
        pendingDeleteFileName = '';
    }

    function formatDate(dateStr: string): string {
        return new Date(dateStr).toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function formatBytes(bytes: number | undefined): string {
        if (!bytes) return '-';
        if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
        if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${bytes} B`;
    }

    function getStatusClass(status: string): string {
        switch (status) {
            case 'uploaded':
                return 'bg-blue-100 text-blue-800';
            case 'parsed':
                return 'bg-yellow-100 text-yellow-800';
            case 'committed':
                return 'bg-green-100 text-green-800';
            case 'error':
                return 'bg-red-100 text-red-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    }
</script>

<div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
    <div class="flex items-center justify-between mb-4">
        <div class="flex items-center space-x-2 text-gray-700">
            <FileUp size={20}/>
            <h2 class="font-semibold">{$_('brokers.importFiles')}</h2>
        </div>
        <div class="flex items-center space-x-2">
            <button
                    class="p-1.5 text-gray-500 hover:text-libre-green hover:bg-libre-green/10 rounded transition-colors disabled:opacity-50"
                    disabled={loading}
                    onclick={loadFiles}
                    title="Refresh"
            >
                <RefreshCw class={loading ? 'animate-spin' : ''} size={16}/>
            </button>
            <label class="cursor-pointer">
                <input
                        accept=".csv,.xlsx,.xls"
                        bind:this={fileInputRef}
                        class="hidden"
                        disabled={uploading}
                        onchange={handleUpload}
                        type="file"
                />
                <span class="flex items-center space-x-1 px-3 py-1.5 bg-libre-green text-white text-sm rounded-lg hover:bg-libre-green/90 transition-colors {uploading ? 'opacity-50 cursor-wait' : ''}">
                    {#if uploading}
                        <RefreshCw size={14} class="animate-spin"/>
                        <span>{$_('common.uploading')}</span>
                    {:else}
                        <FileUp size={14}/>
                        <span>{$_('uploads.upload')}</span>
                    {/if}
                </span>
            </label>
        </div>
    </div>

    {#if error}
        <div class="text-red-600 text-sm mb-3 p-2 bg-red-50 rounded">{error}</div>
    {/if}

    {#if loading && files.length === 0}
        <div class="flex items-center justify-center py-8 text-gray-400">
            <RefreshCw size={24} class="animate-spin"/>
        </div>
    {:else if files.length === 0}
        <div class="text-center py-8">
            <FileText size={32} class="mx-auto text-gray-300 mb-2"/>
            <p class="text-gray-400 text-sm">{$_('brokers.noImportFiles')}</p>
            <p class="text-gray-400 text-xs mt-1">{$_('brokers.uploadHint')}</p>
        </div>
    {:else}
        <div class="space-y-2 max-h-64 overflow-y-auto">
            {#each files as file}
                <div class="flex items-center justify-between p-2 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors group">
                    <div class="flex items-center space-x-3 min-w-0 flex-1">
                        <FileText size={18} class="text-gray-400 flex-shrink-0"/>
                        <div class="min-w-0">
                            <p class="text-sm font-medium text-gray-700 truncate">{file.filename}</p>
                            <div class="flex items-center space-x-2 text-xs text-gray-500">
                                <span>{formatDate(file.uploaded_at)}</span>
                                <span>•</span>
                                <span>{formatBytes(file.size_bytes)}</span>
                                <span class="px-1.5 py-0.5 rounded text-xs {getStatusClass(file.status)}">
                                    {file.status}
                                </span>
                            </div>
                        </div>
                    </div>
                    <button
                            onclick={() => handleDelete(file.file_id)}
                            class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors opacity-0 group-hover:opacity-100"
                            title={$_('common.delete')}
                    >
                        <Trash2 size={14}/>
                    </button>
                </div>
            {/each}
        </div>
        <a
                href="/files?tab=brim&broker={brokerId}"
                class="block mt-3 text-center text-sm text-libre-green hover:underline"
        >
            {$_('brokers.manageFiles')} →
        </a>
    {/if}
</div>

<!-- Delete Confirmation Modal -->
<ConfirmModal
        confirmText={$_('common.delete')}
        danger={true}
        items={pendingDeleteFileName ? [pendingDeleteFileName] : undefined}
        itemsLabel={$_('uploads.filesToDelete')}
        message={$_('uploads.deleteConfirm')}
        onCancel={cancelDelete}
        onConfirm={confirmDelete}
        open={showDeleteConfirm}
        title={$_('common.confirmDelete')}
/>

