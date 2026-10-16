<!--
  FileGrid - Reusable grid view for files

  Used in:
  - files/ page (Static Resources grid view) — with actions (download, copy, delete)
  - AssetPickerModal (Existing tab) — with single selection

  Props control which features are active:
  - mode: 'browse' (files page) | 'select' (asset picker)
  - cardSize: 'compact' (100px, for picker) | 'full' (200px, for files page)
  - showSearch: whether to show the search bar at the top
  - showActions: show download/copy/delete actions on each card (delete and the scope switch only for a file the user
    may manage, can_delete)
  - selectedFileId: for single-selection highlight
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import {formatBytes} from '$lib/utils/files/upload';
    import {formatDateTime} from '$lib/utils/core/formatDateTime';
    import LazyImage from '$lib/components/ui/media/LazyImage.svelte';
    import {Check, Download, Eye, File as FileIcon, FileSpreadsheet, FileText, Image as ImageIcon, Link2, Lock, Search, Trash2, Users, X} from 'lucide-svelte';
    import type {UploadedFile, UploadScope} from '$lib/types';
    import {getPreviewTypeForUploadedFile} from '$lib/utils/files/filePreview';
    import {writeTextToClipboard} from '$lib/utils/clipboard';

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
        /** Called with the scope a file should get: share with everyone, or make personal */
        onscopechange?: (data: {file: UploadedFile; scope: UploadScope}) => void;
    }

    let {files = [], mode = 'browse', cardSize = 'full', showSearch = true, showActions = true, selectedFileId = null, previewSize = '240x240', onselect, ondblselect, ondelete, oncopyLink, onpreview, onscopechange}: Props = $props();

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

    /** Whether the user may delete the file and change its scope; a file without the field keeps today's actions. */
    function canManage(file: UploadedFile): boolean {
        return file.can_delete !== false;
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
                                <Check size={14} class="text-lf-success" />
                            {:else}
                                <Link2 size={14} />
                            {/if}
                        </button>
                        {#if onscopechange && canManage(file)}
                            <button
                                class="action-btn"
                                onclick={(e) => {
                                    e.stopPropagation();
                                    onscopechange?.({file, scope: file.scope === 'common' ? 'personal' : 'common'});
                                }}
                                title={file.scope === 'common' ? $t('uploads.scope.makePersonal') : $t('uploads.scope.share')}
                                aria-label={file.scope === 'common' ? $t('uploads.scope.makePersonal') : $t('uploads.scope.share')}
                                data-testid={`file-grid-scope-${file.id}`}
                                data-scope={file.scope}
                            >
                                {#if file.scope === 'common'}
                                    <Lock size={14} />
                                {:else}
                                    <Users size={14} />
                                {/if}
                            </button>
                        {/if}
                        {#if canManage(file)}
                            <button
                                class="action-btn danger"
                                onclick={(e) => {
                                    e.stopPropagation();
                                    handleDelete(file);
                                }}
                                title={$t('common.delete') || 'Delete'}
                                data-testid={`file-grid-delete-${file.id}`}
                            >
                                <Trash2 size={14} />
                            </button>
                        {/if}
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
        border: 1px solid var(--lf-border-input);
        border-radius: 0.5rem;
        background: var(--lf-surface-field);
        margin-bottom: 0.75rem;
    }

    /* A field's edge: the input border, darker under the pointer (D-T18), the focus colour while its input has the
       focus — the input itself draws no outline. */
    .grid-search:hover {
        border-color: var(--lf-border-input-hover);
    }

    .grid-search:focus-within {
        border-color: var(--lf-focus);
    }

    :global(.grid-search-icon) {
        color: var(--lf-text-muted);
        flex-shrink: 0;
    }

    .grid-search-input {
        flex: 1;
        border: none;
        outline: none;
        background: transparent;
        font-size: 0.875rem;
        color: var(--lf-text-primary);
    }

    .grid-search-input::placeholder {
        color: var(--lf-text-placeholder);
    }

    .grid-search-clear {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 20px;
        height: 20px;
        border: none;
        background: var(--lf-surface-neutral);
        border-radius: 50%;
        color: var(--lf-text-muted);
        cursor: pointer;
    }

    /* Empty state */
    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 2rem;
        color: var(--lf-text-muted);
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
        background: var(--lf-surface-card);
        border: 1px solid var(--lf-border-subtle);
        border-radius: 0.5rem;
        overflow: hidden;
        transition: all 0.2s ease;
    }

    .file-card:hover {
        box-shadow: 0 4px 6px -1px var(--lf-shadow-card);
    }

    /* Selectable mode */
    .file-card.selectable {
        cursor: pointer;
        border-width: 2px;
        border-color: transparent;
    }

    .file-card.selectable:hover {
        border-color: var(--lf-border-input);
    }

    .file-card.selected {
        border-color: var(--lf-checked);
        background: var(--lf-selected);
    }

    /* Preview */
    .file-preview {
        height: 120px;
        background: var(--lf-surface-panel);
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        overflow: hidden;
    }

    .file-preview.compact {
        height: 80px;
    }

    .file-icon-wrapper {
        color: var(--lf-text-muted);
    }

    /* Selected badge */
    .selected-badge {
        position: absolute;
        top: 0.25rem;
        right: 0.25rem;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: var(--lf-checked);
        color: var(--lf-on-checked);
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* Card title */
    .card-title {
        padding: 0.5rem 0.75rem 0;
        font-size: 0.8125rem;
        font-weight: 500;
        color: var(--lf-text-primary);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .card-title.compact {
        padding: 0.25rem 0.375rem 0;
        font-size: 0.6875rem;
    }

    /* Card meta */
    .card-meta {
        padding: 0.125rem 0.75rem 0.5rem;
        font-size: 0.6875rem;
        color: var(--lf-text-muted);
    }

    .card-meta.compact {
        padding: 0 0.375rem 0.25rem;
        font-size: 0.5625rem;
    }

    /* On the selected tint the muted text falls under 4.5:1 (design system, rule 5; TC-15). */
    .file-card.selected .card-meta {
        color: var(--lf-text-secondary);
    }

    /* Card actions */
    .card-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.25rem;
        padding: 0.375rem 0.5rem;
        border-top: 1px solid var(--lf-border-subtle);
    }

    .action-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border: 1px solid var(--lf-border-subtle);
        border-radius: 0.375rem;
        background: var(--lf-surface-card);
        color: var(--lf-text-muted);
        cursor: pointer;
        transition: all 0.2s ease;
        text-decoration: none;
    }

    .action-btn:hover {
        background: var(--lf-surface-hover);
        color: var(--lf-text-primary);
    }

    .action-btn.danger {
        color: var(--lf-danger);
        border-color: var(--lf-danger-line);
    }

    .action-btn.danger:hover {
        background: var(--lf-danger-soft);
        color: var(--lf-danger);
        border-color: var(--lf-danger-line);
    }
</style>
