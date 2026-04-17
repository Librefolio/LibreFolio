<!--
  FileGrid - Reusable grid view for files

  Used in:
  - files/ page (Static Resources grid view) — with actions (download, copy, delete)
  - AssetPickerModal (Existing tab) — with single selection

  Props control which features are active:
  - mode: 'browse' (files page) | 'select' (asset picker)
  - cardSize: 'compact' (100px, for picker) | 'full' (200px, for files page)
  - showSearch: whether to show the search bar at the top
  - showActions: show download/copy/delete actions on each card
  - selectedFileId: for single-selection highlight
-->
<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import {t} from '$lib/i18n';
    import {formatBytes} from '$lib/utils/upload';
    import LazyImage from '$lib/components/ui/media/LazyImage.svelte';
    import {Check, Download, File as FileIcon, FileSpreadsheet, FileText, Image as ImageIcon, Link2, Search, Trash2, X} from 'lucide-svelte';
    import type {UploadedFile} from '$lib/types';

    // Props
    /** Files to display */
    export let files: UploadedFile[] = [];
    /** Grid mode: 'browse' for files page, 'select' for picker */
    export let mode: 'browse' | 'select' = 'browse';
    /** Card size: 'compact' for picker (100px min), 'full' for files page (200px min) */
    export let cardSize: 'compact' | 'full' = 'full';
    /** Show search bar above grid */
    export let showSearch: boolean = true;
    /** Show action buttons on cards (download, copy link, delete) */
    export let showActions: boolean = true;
    /** Currently selected file ID (for select mode) */
    export let selectedFileId: string | null = null;
    /** Preview size for images (WxH) */
    export let previewSize: string = '240x240';

    const dispatch = createEventDispatcher<{
        select: {file: UploadedFile};
        dblselect: {file: UploadedFile};
        delete: {id: string};
        copyLink: {file: UploadedFile};
    }>();

    // Internal state
    let searchQuery = '';
    let copiedFileId: string | null = null;

    // Filtered files
    $: filteredFiles = searchQuery ? files.filter((f) => f.original_name.toLowerCase().includes(searchQuery.toLowerCase())) : files;

    // Helpers
    function isImage(contentType: string): boolean {
        return contentType?.startsWith('image/');
    }

    function getFileIcon(contentType: string, filename?: string) {
        if (contentType?.startsWith('image/')) return ImageIcon;
        if (contentType?.includes('csv') || filename?.endsWith('.csv')) return FileSpreadsheet;
        if (contentType?.includes('text') || contentType?.includes('json')) return FileText;
        return FileIcon;
    }

    function formatDate(dateStr: string): string {
        return new Date(dateStr).toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    }

    function getPreviewUrl(file: UploadedFile, size: string): string {
        return `${file.url}?img_preview=${size}`;
    }

    function handleCardClick(file: UploadedFile) {
        dispatch('select', {file});
    }

    function handleCardDblClick(file: UploadedFile) {
        dispatch('dblselect', {file});
    }

    async function handleCopyLink(file: UploadedFile) {
        dispatch('copyLink', {file});
        const fullUrl = `${window.location.origin}${file.url}`;
        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(fullUrl);
            } else {
                const ta = document.createElement('textarea');
                ta.value = fullUrl;
                ta.style.position = 'fixed';
                ta.style.left = '-9999px';
                document.body.appendChild(ta);
                ta.focus();
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
            }
            copiedFileId = file.id;
            setTimeout(() => {
                copiedFileId = null;
            }, 2000);
        } catch {
            /* ignore */
        }
    }

    function handleDelete(file: UploadedFile) {
        dispatch('delete', {id: file.id});
    }
</script>

<!-- Search bar -->
{#if showSearch}
    <div class="grid-search">
        <Search size={16} class="grid-search-icon" />
        <input type="text" class="grid-search-input" placeholder={$t('common.search') || 'Search...'} bind:value={searchQuery} />
        {#if searchQuery}
            <button class="grid-search-clear" on:click={() => (searchQuery = '')}>
                <X size={14} />
            </button>
        {/if}
    </div>
{/if}

<!-- Empty state -->
{#if filteredFiles.length === 0}
    <div class="empty-state">
        <Search size={32} />
        <p>{searchQuery ? $t('common.noResults') || 'No results' : $t('uploads.noFiles') || 'No files'}</p>
    </div>
{:else}
    <!-- Grid -->
    <div class="file-grid" class:compact={cardSize === 'compact'}>
        {#each filteredFiles as file}
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="file-card" class:selectable={mode === 'select'} class:selected={selectedFileId === file.id} on:click={() => handleCardClick(file)} on:dblclick={() => handleCardDblClick(file)}>
                <div class="file-preview" class:compact={cardSize === 'compact'}>
                    {#if isImage(file.mime_type)}
                        <LazyImage src={getPreviewUrl(file, cardSize === 'compact' ? '120x120' : previewSize)} alt={file.original_name} placeholder="generic" width="100%" height={cardSize === 'compact' ? '80px' : '120px'} />
                    {:else}
                        <div class="file-icon-wrapper">
                            <svelte:component this={getFileIcon(file.mime_type, file.original_name)} size={cardSize === 'compact' ? 24 : 32} />
                        </div>
                    {/if}
                    <!-- Selected badge (select mode only) -->
                    {#if mode === 'select' && selectedFileId === file.id}
                        <div class="selected-badge">
                            <Check size={14} />
                        </div>
                    {/if}
                </div>

                <!-- Title -->
                <div class="card-title" class:compact={cardSize === 'compact'} title={file.original_name}>
                    {file.original_name}
                </div>

                <!-- Meta -->
                <div class="card-meta" class:compact={cardSize === 'compact'}>
                    {formatBytes(file.size_bytes)}
                    {#if mode === 'browse'}
                        • {formatDate(file.uploaded_at)}{/if}
                </div>

                <!-- Actions (browse mode only) -->
                {#if showActions && mode === 'browse'}
                    <div class="card-actions">
                        <a href={`${file.url}?download=true`} download={file.original_name} class="action-btn" title={$t('uploads.download') || 'Download'} on:click|stopPropagation>
                            <Download size={14} />
                        </a>
                        <button class="action-btn" on:click|stopPropagation={() => handleCopyLink(file)} title={$t('uploads.copyLink') || 'Copy Link'}>
                            {#if copiedFileId === file.id}
                                <Check size={14} class="text-green-500" />
                            {:else}
                                <Link2 size={14} />
                            {/if}
                        </button>
                        <button class="action-btn danger" on:click|stopPropagation={() => handleDelete(file)} title={$t('common.delete') || 'Delete'}>
                            <Trash2 size={14} />
                        </button>
                    </div>
                {/if}
            </div>
        {/each}
    </div>
{/if}

<style>
    /* Search bar */
    .grid-search {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0.75rem;
        border: 1px solid #e5e7eb;
        border-radius: 0.5rem;
        background: white;
        margin-bottom: 0.75rem;
    }

    :global(.dark) .grid-search {
        background: #1f2937;
        border-color: #374151;
    }

    :global(.grid-search-icon) {
        color: #9ca3af;
        flex-shrink: 0;
    }

    .grid-search-input {
        flex: 1;
        border: none;
        outline: none;
        background: transparent;
        font-size: 0.875rem;
        color: #374151;
    }

    :global(.dark) .grid-search-input {
        color: #f3f4f6;
    }

    .grid-search-clear {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 20px;
        height: 20px;
        border: none;
        background: #e5e7eb;
        border-radius: 50%;
        color: #6b7280;
        cursor: pointer;
    }

    :global(.dark) .grid-search-clear {
        background: #374151;
        color: #9ca3af;
    }

    /* Empty state */
    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 2rem;
        color: #9ca3af;
        text-align: center;
    }

    .empty-state p {
        margin-top: 0.75rem;
    }

    /* Grid */
    .file-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 1rem;
    }

    .file-grid.compact {
        grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
        gap: 0.5rem;
    }

    /* Card */
    .file-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 0.5rem;
        overflow: hidden;
        transition: all 0.2s ease;
    }

    :global(.dark) .file-card {
        background: #1f2937;
        border-color: #374151;
    }

    .file-card:hover {
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }

    :global(.dark) .file-card:hover {
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.3);
    }

    /* Selectable mode */
    .file-card.selectable {
        cursor: pointer;
        border-width: 2px;
        border-color: transparent;
    }

    .file-card.selectable:hover {
        border-color: #d1d5db;
    }

    :global(.dark) .file-card.selectable:hover {
        border-color: #4b5563;
    }

    .file-card.selected {
        border-color: #1a4031;
        background: #f0fdf4;
    }

    :global(.dark) .file-card.selected {
        border-color: #10b981;
        background: rgba(16, 185, 129, 0.1);
    }

    /* Preview */
    .file-preview {
        height: 120px;
        background: #f3f4f6;
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        overflow: hidden;
    }

    .file-preview.compact {
        height: 80px;
    }

    :global(.dark) .file-preview {
        background: #374151;
    }

    .file-icon-wrapper {
        color: #9ca3af;
    }

    /* Selected badge */
    .selected-badge {
        position: absolute;
        top: 0.25rem;
        right: 0.25rem;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: #1a4031;
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    :global(.dark) .selected-badge {
        background: #10b981;
    }

    /* Card title */
    .card-title {
        padding: 0.5rem 0.75rem 0;
        font-size: 0.8125rem;
        font-weight: 500;
        color: #1f2937;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .card-title.compact {
        padding: 0.25rem 0.375rem 0;
        font-size: 0.6875rem;
    }

    :global(.dark) .card-title {
        color: #f3f4f6;
    }

    /* Card meta */
    .card-meta {
        padding: 0.125rem 0.75rem 0.5rem;
        font-size: 0.6875rem;
        color: #6b7280;
    }

    .card-meta.compact {
        padding: 0 0.375rem 0.25rem;
        font-size: 0.5625rem;
    }

    :global(.dark) .card-meta {
        color: #9ca3af;
    }

    /* Card actions */
    .card-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.25rem;
        padding: 0.375rem 0.5rem;
        border-top: 1px solid #f3f4f6;
    }

    :global(.dark) .card-actions {
        border-top-color: #374151;
    }

    .action-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
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

    .action-btn.danger {
        color: #dc2626;
        border-color: #fecaca;
    }

    :global(.dark) .action-btn.danger {
        color: #fca5a5;
        border-color: rgba(220, 38, 38, 0.3);
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
</style>
