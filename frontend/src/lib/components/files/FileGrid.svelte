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
    import {t} from '$lib/i18n';
    import {formatBytes} from '$lib/utils/files/upload';
    import {formatDateTime} from '$lib/utils/core/formatDateTime';
    import LazyImage from '$lib/components/ui/media/LazyImage.svelte';
    import {Check, Download, Eye, File as FileIcon, FileSpreadsheet, FileText, Image as ImageIcon, Link2, Search, Trash2, X} from 'lucide-svelte';
    import type {UploadedFile} from '$lib/types';
    import {getPreviewTypeForUploadedFile} from '$lib/utils/files/filePreview';
    import {writeTextToClipboard} from '$lib/utils/clipboard';
    import '$lib/theme/components/files.css';

    interface Props {
        /** Files to display */
        files?: UploadedFile[];
        /** Grid mode: 'browse' for files page, 'select' for picker */
        mode?: 'browse' | 'select';
        /** Card size: 'compact' for picker (100px min), 'full' for files page (200px min) */
        cardSize?: 'compact' | 'full';
        /** Show search bar above grid */
        showSearch?: boolean;
        /** Show action buttons on cards (download, copy link, delete) */
        showActions?: boolean;
        /** Currently selected file ID (for select mode) */
        selectedFileId?: string | null;
        /** Preview size for images (WxH) */
        previewSize?: string;
        /** Called when a file card is clicked */
        onselect?: (data: {file: UploadedFile}) => void;
        /** Called when a file card is double-clicked */
        ondblselect?: (data: {file: UploadedFile}) => void;
        /** Called when delete is requested */
        ondelete?: (data: {id: string}) => void;
        /** Called when copy link is requested */
        oncopyLink?: (data: {file: UploadedFile}) => void;
        /** Called when preview is requested */
        onpreview?: (data: {file: UploadedFile}) => void;
    }

    let {files = [], mode = 'browse', cardSize = 'full', showSearch = true, showActions = true, selectedFileId = null, previewSize = '240x240', onselect, ondblselect, ondelete, oncopyLink, onpreview}: Props = $props();

    // Internal state
    let searchQuery = $state('');
    let copiedFileId: string | null = $state(null);

    // Filtered files
    const filteredFiles = $derived(searchQuery ? files.filter((f) => f.original_name.toLowerCase().includes(searchQuery.toLowerCase())) : files);

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
        return formatDateTime(dateStr);
    }

    function getPreviewUrl(file: UploadedFile, size: string): string {
        return `${file.url}?img_preview=${size}`;
    }

    function canPreview(file: UploadedFile): boolean {
        return getPreviewTypeForUploadedFile(file) !== null;
    }

    function handleCardClick(file: UploadedFile) {
        onselect?.({file});
    }

    function handleCardDblClick(file: UploadedFile) {
        if (mode === 'browse' && canPreview(file)) {
            onpreview?.({file});
            return;
        }
        ondblselect?.({file});
    }

    async function handleCopyLink(file: UploadedFile) {
        oncopyLink?.({file});
        const fullUrl = `${window.location.origin}${file.url}`;
        try {
            await writeTextToClipboard(fullUrl);
        } catch {
            return;
        }
        copiedFileId = file.id;
        setTimeout(() => {
            copiedFileId = null;
        }, 2000);
    }

    function handleDelete(file: UploadedFile) {
        ondelete?.({id: file.id});
    }
</script>

<!-- Search bar -->
{#if showSearch}
    <div class="grid-search">
        <Search size={16} class="grid-search-icon" />
        <input type="text" class="grid-search-input" placeholder={$t('common.search') || 'Search...'} bind:value={searchQuery} />
        {#if searchQuery}
            <button class="grid-search-clear" onclick={() => (searchQuery = '')}>
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
        {#each filteredFiles as file (file.id)}
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="file-card" class:selectable={mode === 'select'} class:selected={selectedFileId === file.id} onclick={() => handleCardClick(file)} ondblclick={() => handleCardDblClick(file)}>
                <div class="file-preview" class:compact={cardSize === 'compact'}>
                    {#if isImage(file.mime_type)}
                        <LazyImage fileId={file.id} previewUrl={getPreviewUrl(file, cardSize === 'compact' ? '120x120' : previewSize)} alt={file.original_name} placeholder="generic" width="100%" height={cardSize === 'compact' ? '80px' : '120px'} />
                    {:else}
                        {@const FileIcon = getFileIcon(file.mime_type, file.original_name)}
                        <div class="file-icon-wrapper">
                            <FileIcon size={cardSize === 'compact' ? 24 : 32} />
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
                    <span data-testid={`file-grid-size-${file.id}`}>{formatBytes(file.size_bytes, $t)}</span>
                    {#if mode === 'browse'}
                        • {formatDate(file.uploaded_at)}{/if}
                </div>

                <!-- Actions (browse mode only) -->
                {#if showActions && mode === 'browse'}
                    <div class="card-actions">
                        <a href={`${file.url}?download=true`} download={file.original_name} class="action-btn" title={$t('uploads.download') || 'Download'} onclick={(e) => e.stopPropagation()}>
                            <Download size={14} />
                        </a>
                        {#if canPreview(file)}
                            <button
                                class="action-btn"
                                onclick={(e) => {
                                    e.stopPropagation();
                                    onpreview?.({file});
                                }}
                                title={$t('common.preview') || 'Preview'}
                                data-testid={`file-grid-preview-${file.id}`}
                            >
                                <Eye size={14} />
                            </button>
                        {/if}
                        <button
                            class="action-btn"
                            onclick={(e) => {
                                e.stopPropagation();
                                handleCopyLink(file);
                            }}
                            title={$t('uploads.copyLink') || 'Copy Link'}
                        >
                            {#if copiedFileId === file.id}
                                <Check size={14} class="text-green-500" />
                            {:else}
                                <Link2 size={14} />
                            {/if}
                        </button>
                        <button
                            class="action-btn danger"
                            onclick={(e) => {
                                e.stopPropagation();
                                handleDelete(file);
                            }}
                            title={$t('common.delete') || 'Delete'}
                        >
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
        border: 1px solid var(--lf-cmp-file-grid-border);
        border-radius: 0.5rem;
        background: var(--lf-cmp-file-grid-surface-bg);
        margin-bottom: 0.75rem;
    }

    :global(.dark) .grid-search {
        background: var(--lf-cmp-file-grid-surface-bg-dark);
        border-color: var(--lf-cmp-file-grid-border-dark);
    }

    :global(.grid-search-icon) {
        color: var(--lf-cmp-file-grid-faint-text);
        flex-shrink: 0;
    }

    .grid-search-input {
        flex: 1;
        border: none;
        outline: none;
        background: transparent;
        font-size: 0.875rem;
        color: var(--lf-cmp-file-grid-search-input-text);
    }

    :global(.dark) .grid-search-input {
        color: var(--lf-cmp-file-grid-search-input-text-dark);
    }

    .grid-search-clear {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 20px;
        height: 20px;
        border: none;
        background: var(--lf-cmp-file-grid-search-clear-bg);
        border-radius: 50%;
        color: var(--lf-cmp-file-grid-muted-text);
        cursor: pointer;
    }

    :global(.dark) .grid-search-clear {
        background: var(--lf-cmp-file-grid-search-clear-bg-dark);
        color: var(--lf-cmp-file-grid-muted-text-dark);
    }

    /* Empty state */
    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 2rem;
        color: var(--lf-cmp-file-grid-faint-text);
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
        background: var(--lf-cmp-file-grid-surface-bg);
        border: 1px solid var(--lf-cmp-file-grid-border);
        border-radius: 0.5rem;
        overflow: hidden;
        transition: all 0.2s ease;
    }

    :global(.dark) .file-card {
        background: var(--lf-cmp-file-grid-surface-bg-dark);
        border-color: var(--lf-cmp-file-grid-border-dark);
    }

    .file-card:hover {
        box-shadow: 0 4px 6px -1px var(--lf-cmp-file-grid-file-card-hover-shadow);
    }

    :global(.dark) .file-card:hover {
        box-shadow: 0 4px 6px -1px var(--lf-cmp-file-grid-file-card-hover-shadow-dark);
    }

    /* Selectable mode */
    .file-card.selectable {
        cursor: pointer;
        border-width: 2px;
        border-color: transparent;
    }

    .file-card.selectable:hover {
        border-color: var(--lf-cmp-file-grid-file-card-selectable-hover-border);
    }

    :global(.dark) .file-card.selectable:hover {
        border-color: var(--lf-cmp-file-grid-file-card-selectable-hover-border-dark);
    }

    .file-card.selected {
        border-color: var(--lf-cmp-file-grid-file-card-selected-border);
        background: var(--lf-cmp-file-grid-file-card-selected-bg);
    }

    :global(.dark) .file-card.selected {
        border-color: var(--lf-cmp-file-grid-file-card-selected-border-dark);
        background: var(--lf-cmp-file-grid-file-card-selected-bg-dark);
    }

    /* Preview */
    .file-preview {
        height: 120px;
        background: var(--lf-cmp-file-grid-file-preview-bg);
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
        background: var(--lf-cmp-file-grid-file-preview-bg-dark);
    }

    .file-icon-wrapper {
        color: var(--lf-cmp-file-grid-faint-text);
    }

    /* Selected badge */
    .selected-badge {
        position: absolute;
        top: 0.25rem;
        right: 0.25rem;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: var(--lf-cmp-file-grid-selected-badge-bg);
        color: var(--lf-cmp-file-grid-selected-badge-text);
        display: flex;
        align-items: center;
        justify-content: center;
    }

    :global(.dark) .selected-badge {
        background: var(--lf-cmp-file-grid-selected-badge-bg-dark);
    }

    /* Card title */
    .card-title {
        padding: 0.5rem 0.75rem 0;
        font-size: 0.8125rem;
        font-weight: 500;
        color: var(--lf-cmp-file-grid-strong-text);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .card-title.compact {
        padding: 0.25rem 0.375rem 0;
        font-size: 0.6875rem;
    }

    :global(.dark) .card-title {
        color: var(--lf-cmp-file-grid-strong-text-dark);
    }

    /* Card meta */
    .card-meta {
        padding: 0.125rem 0.75rem 0.5rem;
        font-size: 0.6875rem;
        color: var(--lf-cmp-file-grid-muted-text);
    }

    .card-meta.compact {
        padding: 0 0.375rem 0.25rem;
        font-size: 0.5625rem;
    }

    :global(.dark) .card-meta {
        color: var(--lf-cmp-file-grid-muted-text-dark);
    }

    /* Card actions */
    .card-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.25rem;
        padding: 0.375rem 0.5rem;
        border-top: 1px solid var(--lf-cmp-file-grid-card-actions-border);
    }

    :global(.dark) .card-actions {
        border-top-color: var(--lf-cmp-file-grid-card-actions-border-dark);
    }

    .action-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border: 1px solid var(--lf-cmp-file-grid-action-btn-border);
        border-radius: 0.375rem;
        background: var(--lf-cmp-file-grid-action-btn-bg);
        color: var(--lf-cmp-file-grid-muted-text);
        cursor: pointer;
        transition: all 0.2s ease;
        text-decoration: none;
    }

    :global(.dark) .action-btn {
        background: var(--lf-cmp-file-grid-action-btn-bg-dark);
        border-color: var(--lf-cmp-file-grid-action-btn-border-dark);
        color: var(--lf-cmp-file-grid-muted-text-dark);
    }

    .action-btn:hover {
        background: var(--lf-cmp-file-grid-action-btn-hover-bg);
        color: var(--lf-cmp-file-grid-strong-text);
    }

    :global(.dark) .action-btn:hover {
        background: var(--lf-cmp-file-grid-action-btn-hover-bg-dark);
        color: var(--lf-cmp-file-grid-strong-text-dark);
    }

    .action-btn.danger {
        color: var(--lf-cmp-file-grid-action-btn-danger-text);
        border-color: var(--lf-cmp-file-grid-action-btn-danger-border);
    }

    :global(.dark) .action-btn.danger {
        color: var(--lf-cmp-file-grid-action-btn-danger-text-dark);
        border-color: var(--lf-cmp-file-grid-action-btn-danger-border-dark);
    }

    .action-btn.danger:hover {
        background: var(--lf-cmp-file-grid-action-btn-danger-hover-bg);
        color: var(--lf-cmp-file-grid-action-btn-danger-text);
        border-color: var(--lf-cmp-file-grid-action-btn-danger-hover-border);
    }

    :global(.dark) .action-btn.danger:hover {
        background: var(--lf-cmp-file-grid-action-btn-danger-hover-bg-dark);
        color: var(--lf-cmp-file-grid-action-btn-danger-text-dark);
        border-color: var(--lf-cmp-file-grid-action-btn-danger-hover-border-dark);
    }
</style>
