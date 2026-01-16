<script lang="ts">
    /**
     * Files Page - Manage static uploads and broker reports
     *
     * Two tabs:
     * 1. Static Resources - User uploaded files (/api/v1/uploads)
     * 2. Broker Reports - BRIM files (/api/v1/brokers/import/files)
     */
    import { onMount } from 'svelte';
    import { t } from '$lib/i18n';
    import { api } from '$lib/api';
    import ImageUploader from '$lib/components/ui/ImageUploader.svelte';
    import LazyImage from '$lib/components/ui/LazyImage.svelte';
    import { Download, Trash2, FileText, Image, File } from 'lucide-svelte';

    type Tab = 'static' | 'brim';

    interface UploadedFile {
        id: string;
        original_name: string;
        stored_name: string;
        content_type: string;
        size_bytes: number;
        uploaded_at: string;
        url: string;
    }

    interface BrimFile {
        file_id: string;
        filename: string;
        status: string;
        uploaded_at: string;
        size_bytes?: number;
    }

    let activeTab: Tab = 'static';
    let staticFiles: UploadedFile[] = [];
    let brimFiles: BrimFile[] = [];
    let loading = true;
    let error: string | null = null;
    let showUploader = false;

    onMount(async () => {
        await loadFiles();
    });

    async function loadFiles() {
        loading = true;
        error = null;

        try {
            if (activeTab === 'static') {
                const response = await api.get('/uploads');
                if (response.ok) {
                    const data = await response.json();
                    staticFiles = data.files || [];
                }
            } else {
                const response = await api.get('/brokers/import/files');
                if (response.ok) {
                    brimFiles = await response.json();
                }
            }
        } catch (e) {
            error = e instanceof Error ? e.message : 'Failed to load files';
        } finally {
            loading = false;
        }
    }

    async function handleUpload(event: CustomEvent<{ file: File; size: string }>) {
        const { file } = event.detail;

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await api.post('/uploads', formData, {
                headers: {} // Let browser set Content-Type with boundary
            });

            if (response.ok) {
                showUploader = false;
                await loadFiles();
            } else {
                const data = await response.json();
                error = data.detail || 'Upload failed';
            }
        } catch (e) {
            error = e instanceof Error ? e.message : 'Upload failed';
        }
    }

    async function deleteFile(fileId: string, isBrim: boolean = false) {
        if (!confirm($t('uploads.deleteConfirm'))) return;

        try {
            const endpoint = isBrim
                ? `/brokers/import/files/${fileId}`
                : `/uploads/${fileId}`;

            const response = await api.delete(endpoint);

            if (response.ok) {
                await loadFiles();
            } else {
                const data = await response.json();
                error = data.detail || 'Delete failed';
            }
        } catch (e) {
            error = e instanceof Error ? e.message : 'Delete failed';
        }
    }

    function formatBytes(bytes: number): string {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
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

    function isImage(contentType: string): boolean {
        return contentType?.startsWith('image/');
    }

    function getFileIcon(contentType: string) {
        if (contentType?.startsWith('image/')) return Image;
        if (contentType?.includes('text') || contentType?.includes('csv')) return FileText;
        return File;
    }

    function switchTab(tab: Tab) {
        activeTab = tab;
        loadFiles();
    }
</script>

<svelte:head>
    <title>{$t('uploads.title')} - LibreFolio</title>
</svelte:head>

<div class="files-page">
    <header class="page-header">
        <h1>{$t('uploads.title')}</h1>

        {#if activeTab === 'static'}
            <button
                class="btn btn-primary"
                on:click={() => showUploader = !showUploader}
            >
                {showUploader ? $t('common.cancel') : $t('uploads.upload')}
            </button>
        {/if}
    </header>

    <!-- Tabs -->
    <div class="tabs">
        <button
            class="tab"
            class:active={activeTab === 'static'}
            on:click={() => switchTab('static')}
        >
            {$t('uploads.staticResources')}
        </button>
        <button
            class="tab"
            class:active={activeTab === 'brim'}
            on:click={() => switchTab('brim')}
        >
            {$t('uploads.brokerReports')}
        </button>
    </div>

    <!-- Upload area (static only) -->
    {#if showUploader && activeTab === 'static'}
        <div class="upload-area">
            <ImageUploader
                on:upload={handleUpload}
                on:error={(e) => error = e.detail.message}
            />
        </div>
    {/if}

    <!-- Error message -->
    {#if error}
        <div class="error-banner">
            {error}
            <button on:click={() => error = null}>×</button>
        </div>
    {/if}

    <!-- Content -->
    <div class="content">
        {#if loading}
            <div class="loading">{$t('common.loading')}</div>
        {:else if activeTab === 'static'}
            <!-- Static Files -->
            {#if staticFiles.length === 0}
                <div class="empty-state">
                    <File size={48} />
                    <p>{$t('uploads.noFiles')}</p>
                </div>
            {:else}
                <div class="file-grid">
                    {#each staticFiles as file}
                        <div class="file-card">
                            <div class="file-preview">
                                {#if isImage(file.content_type)}
                                    <LazyImage
                                        src={file.url}
                                        alt={file.original_name}
                                        placeholder="generic"
                                        width="100%"
                                        height="120px"
                                    />
                                {:else}
                                    <div class="file-icon">
                                        <svelte:component this={getFileIcon(file.content_type)} size={32} />
                                    </div>
                                {/if}
                            </div>

                            <div class="file-info">
                                <span class="file-name" title={file.original_name}>
                                    {file.original_name}
                                </span>
                                <span class="file-meta">
                                    {formatBytes(file.size_bytes)} • {formatDate(file.uploaded_at)}
                                </span>
                            </div>

                            <div class="file-actions">
                                <a
                                    href={file.url}
                                    download={file.original_name}
                                    class="action-btn"
                                    title={$t('uploads.download')}
                                >
                                    <Download size={16} />
                                </a>
                                <button
                                    class="action-btn danger"
                                    on:click={() => deleteFile(file.id)}
                                    title={$t('common.delete')}
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        </div>
                    {/each}
                </div>
            {/if}
        {:else}
            <!-- BRIM Files -->
            {#if brimFiles.length === 0}
                <div class="empty-state">
                    <FileText size={48} />
                    <p>{$t('uploads.noFiles')}</p>
                </div>
            {:else}
                <table class="file-table">
                    <thead>
                        <tr>
                            <th>{$t('uploads.fileName')}</th>
                            <th>Status</th>
                            <th>{$t('uploads.uploadDate')}</th>
                            <th>{$t('uploads.actions')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each brimFiles as file}
                            <tr>
                                <td class="filename-cell">
                                    <FileText size={16} />
                                    {file.filename}
                                </td>
                                <td>
                                    <span class="status-badge status-{file.status}">
                                        {file.status}
                                    </span>
                                </td>
                                <td>{formatDate(file.uploaded_at)}</td>
                                <td>
                                    <button
                                        class="action-btn danger"
                                        on:click={() => deleteFile(file.file_id, true)}
                                        title={$t('common.delete')}
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            {/if}
        {/if}
    </div>
</div>

<style>
    .files-page {
        padding: 1.5rem;
        max-width: 1200px;
        margin: 0 auto;
    }

    .page-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.5rem;
    }

    .page-header h1 {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1f2937;
        margin: 0;
    }

    .btn {
        padding: 0.5rem 1rem;
        border-radius: 0.375rem;
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .btn-primary {
        background-color: #1a4031;
        border: 1px solid #1a4031;
        color: white;
    }

    .btn-primary:hover {
        background-color: #143326;
    }

    .tabs {
        display: flex;
        gap: 0;
        margin-bottom: 1.5rem;
        border-bottom: 1px solid #e5e7eb;
    }

    .tab {
        padding: 0.75rem 1.5rem;
        background: none;
        border: none;
        border-bottom: 2px solid transparent;
        font-size: 0.875rem;
        font-weight: 500;
        color: #6b7280;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .tab:hover {
        color: #1a4031;
    }

    .tab.active {
        color: #1a4031;
        border-bottom-color: #1a4031;
    }

    .upload-area {
        margin-bottom: 1.5rem;
        padding: 1rem;
        background: #f9fafb;
        border-radius: 0.5rem;
    }

    .error-banner {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1rem;
        background-color: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 0.375rem;
        color: #dc2626;
        margin-bottom: 1rem;
    }

    .error-banner button {
        background: none;
        border: none;
        font-size: 1.25rem;
        cursor: pointer;
        color: #dc2626;
    }

    .loading {
        text-align: center;
        padding: 3rem;
        color: #6b7280;
    }

    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 4rem 2rem;
        color: #9ca3af;
    }

    .empty-state p {
        margin-top: 1rem;
    }

    /* File Grid (Static) */
    .file-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 1rem;
    }

    .file-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 0.5rem;
        overflow: hidden;
        transition: box-shadow 0.2s ease;
    }

    .file-card:hover {
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }

    .file-preview {
        height: 120px;
        background: #f3f4f6;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .file-icon {
        color: #9ca3af;
    }

    .file-info {
        padding: 0.75rem;
    }

    .file-name {
        display: block;
        font-size: 0.875rem;
        font-weight: 500;
        color: #1f2937;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .file-meta {
        display: block;
        font-size: 0.75rem;
        color: #6b7280;
        margin-top: 0.25rem;
    }

    .file-actions {
        display: flex;
        gap: 0.5rem;
        padding: 0 0.75rem 0.75rem;
    }

    .action-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border: 1px solid #e5e7eb;
        border-radius: 0.375rem;
        background: white;
        color: #6b7280;
        cursor: pointer;
        transition: all 0.2s ease;
        text-decoration: none;
    }

    .action-btn:hover {
        background: #f3f4f6;
        color: #1f2937;
    }

    .action-btn.danger:hover {
        background: #fef2f2;
        color: #dc2626;
        border-color: #fecaca;
    }

    /* File Table (BRIM) */
    .file-table {
        width: 100%;
        border-collapse: collapse;
    }

    .file-table th,
    .file-table td {
        padding: 0.75rem 1rem;
        text-align: left;
        border-bottom: 1px solid #e5e7eb;
    }

    .file-table th {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        color: #6b7280;
        background: #f9fafb;
    }

    .file-table td {
        font-size: 0.875rem;
        color: #1f2937;
    }

    .filename-cell {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        font-size: 0.75rem;
        font-weight: 500;
        border-radius: 9999px;
    }

    .status-uploaded {
        background: #dbeafe;
        color: #1d4ed8;
    }

    .status-parsed {
        background: #d1fae5;
        color: #059669;
    }

    .status-error {
        background: #fef2f2;
        color: #dc2626;
    }
</style>

