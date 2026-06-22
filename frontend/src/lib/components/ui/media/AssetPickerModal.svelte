<!--
  AssetPickerModal - Modal for selecting an image asset

  Three modes:
  1. URL - Enter a URL directly
  2. Existing - Browse existing uploaded files (grid/table)
  3. Upload - Upload a new file (opens ImageEditModal for images)

  Returns the selected URL or uploaded file URL.
-->
<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {File as FileIcon, FolderOpen, Image as ImageIcon, LayoutGrid, Link, List, Search, Upload, X} from 'lucide-svelte';
    import LazyImage from './LazyImage.svelte';
    import FileGrid from '$lib/components/files/FileGrid.svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import type {ColumnDef} from '$lib/components/table';
    import {DataTable} from '$lib/components/table';
    import type {UploadedFile} from '$lib/types';

    // Props
    export let open: boolean = false;
    export let title: string = '';
    /** Filter to only show images in the existing tab */
    export let filterImages: boolean = true;
    /** Pre-populate URL input with existing value */
    export let initialUrl: string = '';
    /** Show circular preview overlay (for avatars/icons) */
    export let circularPreview: boolean = false;

    type _DispatchEvents = {
        select: {url: string};
        cancel: void;
    };
    const dispatch = createEventDispatcher();

    type TabType = 'url' | 'existing' | 'upload';

    // State
    let activeTab: TabType = 'existing';
    let urlInput: string = '';
    let urlValid: boolean = false;

    // Existing files state
    let existingFiles: UploadedFile[] = [];
    let loadingFiles: boolean = false;
    let selectedFile: UploadedFile | null = null;
    let existingViewMode: 'grid' | 'list' = 'grid';
    let searchQuery: string = '';

    // Upload state
    let uploadInput: HTMLInputElement;
    let lastTabBeforeUpload: TabType = 'existing';

    // Computed
    $: filteredFiles = searchQuery ? existingFiles.filter((f) => f.original_name.toLowerCase().includes(searchQuery.toLowerCase())) : existingFiles;

    $: modalTitle = title || $_('uploads.selectAsset') || 'Select Image';

    // Validate URL - accept absolute URLs, relative paths, and any non-empty trimmed input
    $: {
        const trimmed = urlInput.trim();
        if (trimmed.length === 0) {
            urlValid = false;
        } else if (trimmed.startsWith('/') || trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
            urlValid = true;
        } else {
            try {
                new URL(trimmed);
                urlValid = true;
            } catch {
                // Accept any non-empty string as a potential path/URL
                urlValid = trimmed.length > 0;
            }
        }
    }

    // Load files when tab is 'existing' and modal is open
    $: if (open && activeTab === 'existing' && existingFiles.length === 0) {
        loadExistingFiles();
    }

    // Reset on open
    $: if (open) {
        selectedFile = null;
        searchQuery = '';
        // Set URL input and tab based on initialUrl
        urlInput = initialUrl || '';
        if (initialUrl) {
            // Has existing URL → go to URL tab
            activeTab = 'url';
        } else {
            // No existing URL → go to existing files tab
            activeTab = 'existing';
        }
    }

    async function loadExistingFiles() {
        loadingFiles = true;
        try {
            const data = await zodiosApi.list_files_api_v1_uploads_get();
            let files = (data.items || []) as UploadedFile[];
            // Filter to images if required
            if (filterImages) {
                files = files.filter((f) => f.mime_type?.startsWith('image/'));
            }
            existingFiles = files;
        } catch (e) {
            console.error('Failed to load files:', e);
        } finally {
            loadingFiles = false;
        }
    }

    function selectExistingFile(file: UploadedFile) {
        selectedFile = file;
    }

    function confirmSelection() {
        if (activeTab === 'url') {
            if (urlValid) {
                dispatch('select', {url: urlInput});
                close();
            } else if (!urlInput && initialUrl) {
                // User cleared the URL → dispatch empty to remove image
                dispatch('select', {url: ''});
                close();
            }
        } else if (activeTab === 'existing' && selectedFile) {
            dispatch('select', {url: selectedFile.url});
            close();
        }
    }

    function handleUploadClick() {
        uploadInput?.click();
    }

    async function handleFileSelected(event: Event) {
        const input = event.target as HTMLInputElement;
        if (!input.files || input.files.length === 0) return;

        const file = input.files[0];
        input.value = ''; // Reset input

        // Remember which tab was active before upload
        lastTabBeforeUpload = activeTab;

        // Dispatch upload event with the file - parent handles ImageEditModal
        // Do NOT dispatch 'select' with '__upload__' - that contaminates the URL
        // Do NOT close the picker - parent will hide it temporarily
        (dispatch as any)('upload', {file});
    }

    function close() {
        open = false;
        dispatch('cancel');
    }

    function isImage(mime: string): boolean {
        return mime?.startsWith('image/') ?? false;
    }

    /** Get thumbnail URL for an image file using backend preview endpoint */
    function getPreviewUrl(file: UploadedFile, size: string = '80x80'): string {
        return `${file.url}?img_preview=${size}`;
    }

    // DataTable columns for list view
    const listColumns: ColumnDef<UploadedFile>[] = [
        {
            id: 'filename',
            header: () => $_('uploads.fileName') || 'Name',
            cell: (row) => {
                if (isImage(row.mime_type)) {
                    return {
                        type: 'image' as const,
                        src: `${row.url}?img_preview=48x48`,
                        alt: row.original_name,
                        text: row.original_name,
                        fallbackIcon: ImageIcon,
                        size: 32,
                    };
                }
                return {
                    type: 'icon-text' as const,
                    icon: FileIcon,
                    text: row.original_name,
                };
            },
            type: 'text',
            width: 250,
            getValue: (row) => row.original_name,
        },
        {
            id: 'size',
            header: () => $_('uploads.size') || 'Size',
            cell: (row) => ({type: 'size' as const, bytes: row.size_bytes}),
            type: 'size',
            width: 90,
            getValue: (row) => row.size_bytes,
        },
        {
            id: 'type',
            header: () => $_('common.type') || 'Type',
            cell: (row) => row.mime_type || '-',
            type: 'text',
            width: 120,
            getValue: (row) => row.mime_type || '',
        },
    ];

    function handleRowClick(row: UploadedFile) {
        selectedFile = row;
    }

    function handleRowDoubleClick(row: UploadedFile) {
        selectedFile = row;
        confirmSelection();
    }
</script>

<ModalBase maxWidth="600px" onRequestClose={close} {open} zIndex={50}>
    <div aria-modal="true" class="picker-modal-inner" data-testid="asset-picker-modal" role="dialog" tabindex="-1">
        <!-- Header -->
        <div class="picker-header">
            <h2 class="picker-title">{modalTitle}</h2>
            <button class="close-btn" on:click={close} type="button">
                <X size={20} />
            </button>
        </div>

        <!-- Tabs -->
        <div class="picker-tabs">
            <button class="tab-btn" class:active={activeTab === 'existing'} data-testid="asset-picker-existing-tab" on:click={() => (activeTab = 'existing')} type="button">
                <FolderOpen size={14} />
                {$_('uploads.existingFiles') || 'Existing'}
            </button>
            <button class="tab-btn" class:active={activeTab === 'url'} data-testid="asset-picker-url-tab" on:click={() => (activeTab = 'url')} type="button">
                <Link size={14} />
                {$_('uploads.fromUrl') || 'URL'}
            </button>
            <button class="tab-btn" class:active={activeTab === 'upload'} data-testid="asset-picker-upload-tab" on:click={handleUploadClick} type="button">
                <Upload size={14} />
                {$_('uploads.upload') || 'Upload'}
            </button>
            <input accept="image/*" bind:this={uploadInput} class="hidden-input" on:change={handleFileSelected} type="file" />
        </div>

        <!-- Body -->
        <div class="picker-body">
            {#if activeTab === 'url'}
                <!-- URL Input -->
                <div class="url-section">
                    <label class="url-label" for="asset-url-input">{$_('uploads.imageUrl') || 'Image URL'}</label>
                    <div style="display:flex; gap:0.5rem; align-items:center;">
                        <input type="url" id="asset-url-input" class="url-input" style="flex:1;" bind:value={urlInput} placeholder="https://example.com/image.png" />
                        {#if urlInput}
                            <button
                                type="button"
                                class="btn btn-secondary"
                                style="white-space:nowrap; padding:0.375rem 0.75rem; font-size:0.8125rem; color:#dc2626;"
                                on:click={() => {
                                    urlInput = '';
                                }}
                            >
                                <X size={14} />
                            </button>
                        {/if}
                    </div>
                    <p class="url-hint">{$_('uploads.urlHint') || 'Enter a remote URL or a local path from Files'}</p>
                    {#if urlInput && urlValid}
                        <div class="url-preview" class:circular={circularPreview}>
                            <div class="url-preview-img-wrapper">
                                <LazyImage src={urlInput} alt="Preview" placeholder="generic" width="100%" height="auto" />
                                {#if circularPreview}
                                    <div class="url-preview-circle-overlay"></div>
                                {/if}
                            </div>
                        </div>
                    {/if}
                </div>
            {:else if activeTab === 'existing'}
                <!-- Existing files browser -->
                <div class="existing-section">
                    <!-- Toolbar: search + view toggle -->
                    <div class="existing-toolbar">
                        <div class="search-box">
                            <Search size={14} />
                            <input type="text" class="search-input" bind:value={searchQuery} placeholder={$_('common.search') || 'Search...'} data-testid="asset-picker-search" />
                            {#if searchQuery}
                                <button type="button" class="search-clear" on:click={() => (searchQuery = '')}>
                                    <X size={12} />
                                </button>
                            {/if}
                        </div>
                        <div class="view-toggle">
                            <button type="button" class="toggle-btn" class:active={existingViewMode === 'grid'} on:click={() => (existingViewMode = 'grid')}>
                                <LayoutGrid size={14} />
                            </button>
                            <button type="button" class="toggle-btn" class:active={existingViewMode === 'list'} on:click={() => (existingViewMode = 'list')}>
                                <List size={14} />
                            </button>
                        </div>
                    </div>

                    <!-- File browser -->
                    {#if loadingFiles}
                        <div class="empty-state">{$_('common.loading') || 'Loading...'}</div>
                    {:else if filteredFiles.length === 0}
                        <div class="empty-state">
                            {searchQuery ? $_('common.noResults') || 'No results' : $_('uploads.noFiles') || 'No files'}
                        </div>
                    {:else if existingViewMode === 'grid'}
                        <FileGrid files={filteredFiles} mode="select" cardSize="compact" showSearch={false} showActions={false} selectedFileId={selectedFile?.id || null} previewSize="120x120" onselect={(e) => selectExistingFile(e.file)} ondblselect={() => confirmSelection()} />
                    {:else}
                        <!-- List/table view using DataTable -->
                        <div class="list-table-wrapper">
                            <DataTable
                                data={filteredFiles}
                                columns={listColumns}
                                getRowId={(row) => row.id}
                                storageKey="asset-picker-list"
                                enableSelection={true}
                                selectionMode="single"
                                selectedRowId={selectedFile?.id || null}
                                onRowClick={handleRowClick}
                                onRowDoubleClick={handleRowDoubleClick}
                                enableActions={false}
                                enableSorting={true}
                                enableColumnFilters={false}
                                enableColumnResize={false}
                                enablePagination={false}
                                enableColumnVisibility={false}
                                emptyMessage={searchQuery ? $_('common.noResults') || 'No results' : $_('uploads.noFiles') || 'No files'}
                                isLoading={loadingFiles}
                            />
                        </div>
                    {/if}
                </div>
            {/if}
        </div>

        <!-- Footer -->
        <div class="picker-footer">
            <button class="btn btn-secondary" on:click={close} type="button">
                {$_('common.cancel') || 'Cancel'}
            </button>
            <button class="btn btn-primary" data-testid="asset-picker-confirm" disabled={(activeTab === 'url' && !urlValid && !(initialUrl && !urlInput)) || (activeTab === 'existing' && !selectedFile)} on:click={confirmSelection} type="button">
                {$_('uploads.useSelected') || 'Use Selected'}
            </button>
        </div>
    </div>
</ModalBase>

<style>
    /* Backdrop handled by ModalBase */
    .picker-modal-inner {
        display: flex;
        flex-direction: column;
        max-height: 80vh;
        overflow: hidden;
    }

    /* Header */
    .picker-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem 1rem;
        border-bottom: 1px solid #e5e7eb;
    }

    :global(.dark) .picker-header {
        border-bottom-color: #374151;
    }

    .picker-title {
        font-size: 1rem;
        font-weight: 600;
        margin: 0;
        color: #1f2937;
    }

    :global(.dark) .picker-title {
        color: #f3f4f6;
    }

    .close-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border: none;
        border-radius: 0.375rem;
        background: transparent;
        color: #6b7280;
        cursor: pointer;
    }

    .close-btn:hover {
        background: #f3f4f6;
        color: #1f2937;
    }

    :global(.dark) .close-btn:hover {
        background: #374151;
        color: #f3f4f6;
    }

    /* Tabs */
    .picker-tabs {
        display: flex;
        gap: 0;
        border-bottom: 1px solid #e5e7eb;
        padding: 0 0.5rem;
    }

    :global(.dark) .picker-tabs {
        border-bottom-color: #374151;
    }

    .tab-btn {
        display: flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.5rem 0.75rem;
        font-size: 0.8125rem;
        font-weight: 500;
        border: none;
        border-bottom: 2px solid transparent;
        background: transparent;
        color: #6b7280;
        cursor: pointer;
        transition: all 0.15s;
    }

    .tab-btn:hover {
        color: #1f2937;
    }

    .tab-btn.active {
        color: #1a4031;
        border-bottom-color: #1a4031;
    }

    :global(.dark) .tab-btn {
        color: #9ca3af;
    }

    :global(.dark) .tab-btn:hover {
        color: #f3f4f6;
    }

    :global(.dark) .tab-btn.active {
        color: #10b981;
        border-bottom-color: #10b981;
    }

    .hidden-input {
        display: none;
    }

    /* Body */
    .picker-body {
        flex: 1;
        overflow-y: auto;
        padding: 0.75rem;
        min-height: 300px;
    }

    /* URL tab */
    .url-section {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .url-label {
        font-size: 0.75rem;
        font-weight: 500;
        color: #6b7280;
    }

    :global(.dark) .url-label {
        color: #9ca3af;
    }

    .url-input {
        padding: 0.5rem 0.75rem;
        border: 1px solid #d1d5db;
        border-radius: 0.375rem;
        font-size: 0.8125rem;
        outline: none;
        background: white;
        color: #1f2937;
    }

    .url-input:focus {
        border-color: #1a4031;
    }

    :global(.dark) .url-input {
        background: #374151;
        border-color: #4b5563;
        color: #f3f4f6;
    }

    :global(.dark) .url-input:focus {
        border-color: #10b981;
    }

    .url-preview {
        border: 1px solid #e5e7eb;
        border-radius: 0.5rem;
        overflow: hidden;
        max-height: 250px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #f9fafb;
    }

    :global(.dark) .url-preview {
        border-color: #374151;
        background: #1a2332;
    }

    .url-preview-img-wrapper {
        position: relative;
        width: 100%;
        max-height: 250px;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
    }

    /* Force the LazyImage container to center and respect max-height */
    .url-preview-img-wrapper :global(.lazy-image-container) {
        max-height: 250px;
        width: auto !important;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .url-preview-img-wrapper :global(img) {
        max-height: 250px;
        width: auto;
        max-width: 100%;
        object-fit: contain;
        display: block;
    }

    .url-preview-circle-overlay {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        pointer-events: none;
    }

    /* Circle cutout: shows original image inside, dark overlay outside.
       Uses a percentage of the container so it scales with image size. */
    .url-preview-circle-overlay::before {
        content: '';
        width: min(100%, 200px);
        aspect-ratio: 1;
        border-radius: 50%;
        box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.5);
        border: 2px solid rgba(255, 255, 255, 0.6);
        flex-shrink: 0;
    }

    .url-hint {
        font-size: 0.6875rem;
        color: #9ca3af;
        margin-top: 0.25rem;
        font-style: italic;
    }

    :global(.dark) .url-hint {
        color: #6b7280;
    }

    /* Existing tab */
    .existing-section {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .existing-toolbar {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .search-box {
        flex: 1;
        display: flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.375rem 0.5rem;
        border: 1px solid #e5e7eb;
        border-radius: 0.375rem;
        background: white;
        color: #9ca3af;
    }

    :global(.dark) .search-box {
        background: #374151;
        border-color: #4b5563;
    }

    .search-input {
        flex: 1;
        border: none;
        outline: none;
        background: transparent;
        font-size: 0.8125rem;
        color: #374151;
    }

    :global(.dark) .search-input {
        color: #f3f4f6;
    }

    .search-clear {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 16px;
        height: 16px;
        border: none;
        background: #e5e7eb;
        border-radius: 50%;
        color: #6b7280;
        cursor: pointer;
    }

    :global(.dark) .search-clear {
        background: #4b5563;
        color: #9ca3af;
    }

    .view-toggle {
        display: flex;
        gap: 0.125rem;
    }

    .toggle-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border: 1px solid #e5e7eb;
        border-radius: 0.25rem;
        background: white;
        color: #6b7280;
        cursor: pointer;
    }

    .toggle-btn:hover {
        background: #f3f4f6;
    }

    .toggle-btn.active {
        background: #1a4031;
        color: white;
        border-color: #1a4031;
    }

    :global(.dark) .toggle-btn {
        background: #374151;
        border-color: #4b5563;
        color: #9ca3af;
    }

    :global(.dark) .toggle-btn.active {
        background: #10b981;
        border-color: #10b981;
        color: white;
    }

    .empty-state {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 2rem;
        color: #9ca3af;
        font-size: 0.875rem;
    }

    /* Grid view — now handled by FileGrid component */

    /* List view (DataTable) */
    .list-table-wrapper {
        max-height: 320px;
        overflow-y: auto;
        border: 1px solid #e5e7eb;
        border-radius: 0.375rem;
    }

    :global(.dark) .list-table-wrapper {
        border-color: #374151;
    }

    /* Make DataTable compact inside picker */
    .list-table-wrapper :global(.table-container) {
        max-height: none !important;
    }

    .list-table-wrapper :global(.table-header) {
        display: none;
    }

    /* Footer */
    .picker-footer {
        display: flex;
        justify-content: flex-end;
        gap: 0.5rem;
        padding: 0.75rem 1rem;
        border-top: 1px solid #e5e7eb;
    }

    :global(.dark) .picker-footer {
        border-top-color: #374151;
    }

    .btn {
        display: inline-flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.375rem 0.875rem;
        font-size: 0.8125rem;
        font-weight: 500;
        border-radius: 0.375rem;
        border: none;
        cursor: pointer;
        transition: all 0.15s;
    }

    .btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .btn-primary {
        background: #1a4031;
        color: white;
    }

    .btn-primary:hover:not(:disabled) {
        background: #143326;
    }

    :global(.dark) .btn-primary {
        background: #10b981;
    }

    :global(.dark) .btn-primary:hover:not(:disabled) {
        background: #059669;
    }

    .btn-secondary {
        background: #e5e7eb;
        color: #374151;
    }

    .btn-secondary:hover:not(:disabled) {
        background: #d1d5db;
    }

    :global(.dark) .btn-secondary {
        background: #374151;
        color: #d1d5db;
    }

    :global(.dark) .btn-secondary:hover:not(:disabled) {
        background: #4b5563;
    }
</style>
