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
    import { Download, Trash2, FileText, Image, File as FileIcon, FileSpreadsheet, Eye, List, LayoutGrid } from 'lucide-svelte';

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
                const data = await api.get<{ files: UploadedFile[] }>('/uploads');
                staticFiles = data.files || [];
            } else {
                brimFiles = await api.get<BrimFile[]>('/brokers/import/files');
            }
        } catch (e) {
            error = e instanceof Error ? e.message : 'Failed to load files';
        } finally {
            loading = false;
        }
    }

    async function handleUpload(event: CustomEvent<{ file: globalThis.File; size: string }>) {
        const { file } = event.detail;

        try {
            const formData = new FormData();
            formData.append('file', file);

            await api.post('/uploads', formData, {
                headers: {} // Let browser set Content-Type with boundary
            });

            showUploader = false;
            await loadFiles();
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

            await api.delete(endpoint);
            await loadFiles();
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

    function getFileIcon(contentType: string, filename?: string) {
        if (contentType?.startsWith('image/')) return Image;
        if (contentType?.includes('csv') || filename?.endsWith('.csv')) return FileSpreadsheet;
        if (contentType?.includes('text') || contentType?.includes('json')) return FileText;
        return FileIcon;
    }

    // Get appropriate icon for BRIM files based on extension
    function getBrimFileIcon(filename: string) {
        const ext = filename.split('.').pop()?.toLowerCase();
        if (ext === 'csv') return FileSpreadsheet;
        if (ext === 'json' || ext === 'txt') return FileText;
        return FileIcon;
    }

    // View mode: 'grid' or 'list'
    let viewMode: 'grid' | 'list' = 'grid';

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

        <div class="header-actions">
            <!-- View mode toggle (only for static tab) -->
            {#if activeTab === 'static' && staticFiles.length > 0}
                <div class="view-toggle">
                    <button
                        class="view-btn"
                        class:active={viewMode === 'grid'}
                        on:click={() => viewMode = 'grid'}
                        title="Grid view"
                    >
                        <LayoutGrid size={18} />
                    </button>
                    <button
                        class="view-btn"
                        class:active={viewMode === 'list'}
                        on:click={() => viewMode = 'list'}
                        title="List view"
                    >
                        <List size={18} />
                    </button>
                </div>
            {/if}

            {#if activeTab === 'static'}
                <button
                    class="btn btn-primary"
                    on:click={() => showUploader = !showUploader}
                >
                    {showUploader ? $t('common.cancel') : $t('uploads.upload')}
                </button>
            {/if}
        </div>
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
                    <FileIcon size={48} />
                    <p>{$t('uploads.noFiles')}</p>
                </div>
            {:else if viewMode === 'grid'}
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
                                        <svelte:component this={getFileIcon(file.content_type, file.original_name)} size={32} />
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
            {:else}
                <!-- List View -->
                <div class="file-table-wrapper">
                    <table class="file-table">
                        <thead>
                            <tr>
                                <th class="th-name">{$t('uploads.fileName')}</th>
                                <th class="th-size">{$t('uploads.fileSize')}</th>
                                <th class="th-date">{$t('uploads.uploadDate')}</th>
                                <th class="th-actions">{$t('uploads.actions')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each staticFiles as file}
                                <tr>
                                    <td>
                                        <div class="filename-cell">
                                            <svelte:component this={getFileIcon(file.content_type, file.original_name)} size={18} class="file-type-icon" />
                                            <span class="filename-text" title={file.original_name}>{file.original_name}</span>
                                        </div>
                                    </td>
                                    <td class="size-cell">{formatBytes(file.size_bytes)}</td>
                                    <td class="date-cell">{formatDate(file.uploaded_at)}</td>
                                    <td class="actions-cell">
                                        <div class="action-buttons">
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
                                    </td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
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
                <div class="file-table-wrapper">
                    <table class="file-table">
                        <thead>
                            <tr>
                                <th class="th-name">{$t('uploads.fileName')}</th>
                                <th class="th-status">Status</th>
                                <th class="th-size">{$t('uploads.fileSize')}</th>
                                <th class="th-date">{$t('uploads.uploadDate')}</th>
                                <th class="th-actions">{$t('uploads.actions')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each brimFiles as file}
                                <tr>
                                    <td>
                                        <div class="filename-cell">
                                            <svelte:component this={getBrimFileIcon(file.filename)} size={18} class="file-type-icon" />
                                            <span class="filename-text" title={file.filename}>{file.filename}</span>
                                        </div>
                                    </td>
                                    <td>
                                        <span class="status-badge status-{file.status}">
                                            {file.status}
                                        </span>
                                    </td>
                                    <td class="size-cell">{file.size_bytes ? formatBytes(file.size_bytes) : '-'}</td>
                                    <td class="date-cell">{formatDate(file.uploaded_at)}</td>
                                    <td class="actions-cell">
                                        <div class="action-buttons">
                                            <a
                                                href={`/api/v1/brokers/import/files/${file.file_id}/download`}
                                                download={file.filename}
                                                class="action-btn"
                                                title={$t('uploads.download')}
                                            >
                                                <Download size={16} />
                                            </a>
                                            <button
                                                class="action-btn danger"
                                                on:click={() => deleteFile(file.file_id, true)}
                                                title={$t('common.delete')}
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </div>
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

    :global(.dark) .page-header h1 {
        color: #f3f4f6;
    }

    .header-actions {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .view-toggle {
        display: flex;
        border: 1px solid #e5e7eb;
        border-radius: 0.5rem;
        overflow: hidden;
    }

    :global(.dark) .view-toggle {
        border-color: #4b5563;
    }

    .view-btn {
        padding: 0.5rem;
        background: white;
        border: none;
        color: #6b7280;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    :global(.dark) .view-btn {
        background: #374151;
        color: #9ca3af;
    }

    .view-btn:hover {
        background: #f3f4f6;
        color: #1f2937;
    }

    :global(.dark) .view-btn:hover {
        background: #4b5563;
        color: #f3f4f6;
    }

    .view-btn.active {
        background: #1a4031;
        color: white;
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

    :global(.dark) .tabs {
        border-bottom-color: #4b5563;
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

    :global(.dark) .tab {
        color: #9ca3af;
    }

    .tab:hover {
        color: #1a4031;
    }

    :global(.dark) .tab:hover {
        color: #10b981;
    }

    .tab.active {
        color: #1a4031;
        border-bottom-color: #1a4031;
    }

    :global(.dark) .tab.active {
        color: #10b981;
        border-bottom-color: #10b981;
    }

    .upload-area {
        margin-bottom: 1.5rem;
        padding: 1rem;
        background: #f9fafb;
        border-radius: 0.5rem;
    }

    :global(.dark) .upload-area {
        background: #374151;
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

    :global(.dark) .error-banner {
        background-color: rgba(220, 38, 38, 0.1);
        border-color: rgba(220, 38, 38, 0.3);
        color: #fca5a5;
    }

    .error-banner button {
        background: none;
        border: none;
        font-size: 1.25rem;
        cursor: pointer;
        color: inherit;
    }

    .loading {
        text-align: center;
        padding: 3rem;
        color: #6b7280;
    }

    :global(.dark) .loading {
        color: #9ca3af;
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

    :global(.dark) .file-card {
        background: #1f2937;
        border-color: #374151;
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

    :global(.dark) .file-preview {
        background: #374151;
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

    :global(.dark) .file-name {
        color: #f3f4f6;
    }

    .file-meta {
        display: block;
        font-size: 0.75rem;
        color: #6b7280;
        margin-top: 0.25rem;
    }

    :global(.dark) .file-meta {
        color: #9ca3af;
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

    :global(.dark) .action-btn {
        background: #374151;
        border-color: #4b5563;
        color: #9ca3af;
    }

    .action-btn:hover {
        background: #f3f4f6;
        color: #1f2937;
    }

    :global(.dark) .action-btn:hover {
        background: #4b5563;
        color: #f3f4f6;
    }

    .action-btn.danger:hover {
        background: #fef2f2;
        color: #dc2626;
        border-color: #fecaca;
    }

    :global(.dark) .action-btn.danger:hover {
        background: rgba(220, 38, 38, 0.2);
        color: #fca5a5;
        border-color: rgba(220, 38, 38, 0.4);
    }

    /* File Table */
    .file-table-wrapper {
        overflow-x: auto;
        border: 1px solid #e5e7eb;
        border-radius: 0.5rem;
    }

    :global(.dark) .file-table-wrapper {
        border-color: #374151;
    }

    .file-table {
        width: 100%;
        border-collapse: collapse;
        min-width: 600px;
    }

    .file-table th,
    .file-table td {
        padding: 0.75rem 1rem;
        text-align: left;
    }

    .file-table th {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        color: #6b7280;
        background: #f9fafb;
        border-bottom: 1px solid #e5e7eb;
        white-space: nowrap;
    }

    :global(.dark) .file-table th {
        background: #1f2937;
        color: #9ca3af;
        border-bottom-color: #374151;
    }

    .file-table td {
        font-size: 0.875rem;
        color: #1f2937;
        border-bottom: 1px solid #e5e7eb;
        vertical-align: middle;
    }

    :global(.dark) .file-table td {
        color: #f3f4f6;
        border-bottom-color: #374151;
    }

    .file-table tbody tr:last-child td {
        border-bottom: none;
    }

    .file-table tbody tr:hover {
        background: #f9fafb;
    }

    :global(.dark) .file-table tbody tr:hover {
        background: #374151;
    }

    /* Column widths */
    .th-name { width: 40%; min-width: 200px; }
    .th-status { width: 100px; }
    .th-size { width: 100px; }
    .th-date { width: 150px; }
    .th-actions { width: 100px; text-align: center; }

    .filename-cell {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .filename-cell :global(.file-type-icon) {
        flex-shrink: 0;
        color: #6b7280;
    }

    :global(.dark) .filename-cell :global(.file-type-icon) {
        color: #9ca3af;
    }

    .filename-text {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        min-width: 0;
    }

    .size-cell, .date-cell {
        white-space: nowrap;
        color: #6b7280;
    }

    :global(.dark) .size-cell, :global(.dark) .date-cell {
        color: #9ca3af;
    }

    .actions-cell {
        text-align: center;
    }

    .action-buttons {
        display: flex;
        justify-content: center;
        gap: 0.5rem;
    }

    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        font-size: 0.75rem;
        font-weight: 500;
        border-radius: 9999px;
        text-transform: capitalize;
    }

    .status-uploaded {
        background: #dbeafe;
        color: #1d4ed8;
    }

    :global(.dark) .status-uploaded {
        background: rgba(59, 130, 246, 0.2);
        color: #93c5fd;
    }

    .status-imported, .status-parsed {
        background: #d1fae5;
        color: #059669;
    }

    :global(.dark) .status-imported, :global(.dark) .status-parsed {
        background: rgba(16, 185, 129, 0.2);
        color: #6ee7b7;
    }

    .status-failed, .status-error {
        background: #fef2f2;
        color: #dc2626;
    }

    :global(.dark) .status-failed, :global(.dark) .status-error {
        background: rgba(220, 38, 38, 0.2);
        color: #fca5a5;
    }
</style>

