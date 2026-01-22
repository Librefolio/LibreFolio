<!--
  FilesTableAdvanced - Tabella files avanzata con TanStack Table v8

  Features:
  - Sorting per colonna
  - Pagination floating con navigazione pagine
  - Column visibility con icone occhio e riordinamento
  - Row selection (solo pagina corrente)
  - Colonne ridimensionabili con handle visibile
  - Colonne fisse: select e actions
  - Traduzione status BRIM
-->
<script lang="ts">
    import { onMount } from 'svelte';
    import {
        createSvelteTable,
        getCoreRowModel,
        getSortedRowModel,
        getPaginationRowModel,
        createColumnHelper,
        type SortingState,
        type PaginationState,
        type VisibilityState,
        type RowSelectionState,
    } from '$lib/tanstack-table';
    import { t } from '$lib/i18n';
    import {
        Download, Trash2, FileText, Image, File as FileIcon, FileSpreadsheet,
        ChevronUp, ChevronDown, ChevronsUpDown, ChevronLeft, ChevronRight,
        Eye, EyeOff, RotateCcw, GripVertical, Check, Search, X
    } from 'lucide-svelte';

    // Types
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

    type FileData = UploadedFile | BrimFile;

    // Props
    interface Props {
        files: FileData[];
        type: 'static' | 'brim';
        onDelete: (id: string) => void;
        storageKey?: string;
    }

    let { files, type, onDelete, storageKey = 'filesTable' }: Props = $props();

    // Storage helpers
    function getStorageKey(suffix: string): string {
        return `${storageKey}_${type}_${suffix}`;
    }

    function loadFromStorage<T>(key: string, defaultValue: T): T {
        if (typeof window === 'undefined') return defaultValue;
        try {
            const stored = localStorage.getItem(key);
            return stored ? JSON.parse(stored) : defaultValue;
        } catch {
            return defaultValue;
        }
    }

    function saveToStorage(key: string, value: unknown): void {
        if (typeof window === 'undefined') return;
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch {}
    }

    // Format helpers
    function formatBytes(bytes: number | undefined): string {
        if (!bytes || bytes === 0) return '-';
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

    function getFileIcon(file: FileData) {
        if (type === 'static') {
            const f = file as UploadedFile;
            if (f.content_type?.startsWith('image/')) return Image;
            if (f.content_type?.includes('csv') || f.original_name?.endsWith('.csv')) return FileSpreadsheet;
            if (f.content_type?.includes('text') || f.content_type?.includes('json')) return FileText;
        } else {
            const f = file as BrimFile;
            const ext = f.filename.split('.').pop()?.toLowerCase();
            if (ext === 'csv') return FileSpreadsheet;
            if (ext === 'json' || ext === 'txt') return FileText;
        }
        return FileIcon;
    }

    function getFileName(file: FileData): string {
        return type === 'static' ? (file as UploadedFile).original_name : (file as BrimFile).filename;
    }

    function getFileId(file: FileData): string {
        return type === 'static' ? (file as UploadedFile).id : (file as BrimFile).file_id;
    }

    function getDownloadUrl(file: FileData): string {
        if (type === 'static') {
            return `${(file as UploadedFile).url}?download=true`;
        }
        return `/api/v1/brokers/import/files/${(file as BrimFile).file_id}/download`;
    }

    function getFileSize(file: FileData): number {
        return type === 'static' ? (file as UploadedFile).size_bytes : ((file as BrimFile).size_bytes || 0);
    }

    function translateStatus(status: string): string {
        const key = `fileStatus.${status}`;
        const translated = $t(key);
        return translated !== key ? translated : status.charAt(0).toUpperCase() + status.slice(1);
    }

    function getBrimStatus(file: FileData): string {
        return (file as BrimFile).status || '';
    }

    // Table state
    let sorting = $state<SortingState>([]);
    let rowSelection = $state<RowSelectionState>({});

    const PAGE_SIZE_OPTIONS = [10, 25, 50, 100, 0];

    let pagination = $state<PaginationState>({
        pageIndex: 0,
        pageSize: 10,
    });

    // Column visibility and order
    const defaultColumnVisibility: VisibilityState = {
        filename: true,
        status: true,
        size: true,
        date: true,
    };
    let columnVisibility = $state<VisibilityState>({ ...defaultColumnVisibility });

    // Default column order based on type (computed at init)
    function getDefaultColumnOrder(): string[] {
        return type === 'brim'
            ? ['filename', 'status', 'size', 'date']
            : ['filename', 'size', 'date'];
    }
    let columnOrder = $state<string[]>(getDefaultColumnOrder());

    // Column widths
    const defaultColumnWidths: Record<string, number> = {
        filename: 250,
        status: 100,
        size: 100,
        date: 150,
    };
    let columnWidths = $state<Record<string, number>>({ ...defaultColumnWidths });

    // UI state
    let showColumnDropdown = $state(false);
    let pageInputValue = $state('1');
    let searchQuery = $state('');

    // Delete confirmation modal
    let showDeleteModal = $state(false);
    let filesToDelete = $state<FileData[]>([]);
    let showFileList = $state(false);

    // Go to page modal
    let showGotoModal = $state(false);
    let gotoPageInput = $state('');

    // Filtered files based on search (reactive)
    let filteredFiles = $derived.by(() => {
        if (!searchQuery.trim()) return files;
        const query = searchQuery.toLowerCase();
        return files.filter(file => {
            const name = getFileName(file).toLowerCase();
            return name.includes(query);
        });
    });

    // Column definitions for dropdown
    function getAllColumnDefs() {
        const defs = [
            { id: 'filename', label: () => $t('uploads.fileName') },
        ];
        if (type === 'brim') {
            defs.push({ id: 'status', label: () => 'Status' });
        }
        defs.push(
            { id: 'size', label: () => $t('uploads.fileSize') },
            { id: 'date', label: () => $t('uploads.uploadDate') },
        );
        return defs;
    }

    // TanStack Table setup
    const columnHelper = createColumnHelper<FileData>();

    function getColumns() {
        const cols: any[] = [
            columnHelper.display({
                id: 'select',
                header: () => '',
                cell: () => '',
                enableSorting: false,
            }),
            columnHelper.accessor((row) => getFileName(row), {
                id: 'filename',
                header: () => $t('uploads.fileName'),
                cell: (info) => info.getValue(),
                enableSorting: true,
            }),
        ];

        if (type === 'brim') {
            cols.push(
                columnHelper.accessor((row) => getBrimStatus(row), {
                    id: 'status',
                    header: () => 'Status',
                    cell: (info) => info.getValue(),
                    enableSorting: true,
                })
            );
        }

        cols.push(
            columnHelper.accessor((row) => getFileSize(row), {
                id: 'size',
                header: () => $t('uploads.fileSize'),
                cell: (info) => formatBytes(info.getValue() as number),
                enableSorting: true,
            }),
            columnHelper.accessor((row) => row.uploaded_at, {
                id: 'date',
                header: () => $t('uploads.uploadDate'),
                cell: (info) => formatDate(info.getValue() as string),
                enableSorting: true,
            }),
            columnHelper.display({
                id: 'actions',
                header: () => $t('uploads.actions'),
                enableSorting: false,
            })
        );

        return cols;
    }

    const table = createSvelteTable({
        get data() { return filteredFiles; },
        get columns() { return getColumns(); },
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        enableRowSelection: true,
        onSortingChange: (updater) => {
            sorting = typeof updater === 'function' ? updater(sorting) : updater;
        },
        onPaginationChange: (updater) => {
            pagination = typeof updater === 'function' ? updater(pagination) : updater;
            // Clear selection when page changes
            rowSelection = {};
        },
        onRowSelectionChange: (updater) => {
            rowSelection = typeof updater === 'function' ? updater(rowSelection) : updater;
        },
        state: {
            get sorting() { return sorting; },
            get pagination() { return pagination; },
            get rowSelection() { return rowSelection; },
            get columnVisibility() { return columnVisibility; },
        },
    });

    // Selection helpers - only current page
    function toggleAllPageRows() {
        const paginatedFiles = getPaginatedFiles();
        const startIndex = pagination.pageIndex * pagination.pageSize;
        const pageRowIds = paginatedFiles.map((_, i) => String(startIndex + i));
        const allPageSelected = pageRowIds.every(id => rowSelection[id]);

        if (allPageSelected) {
            // Deselect all on page
            const newSelection = { ...rowSelection };
            pageRowIds.forEach(id => delete newSelection[id]);
            rowSelection = newSelection;
        } else {
            // Select all on page (replace any previous selection)
            const newSelection: RowSelectionState = {};
            pageRowIds.forEach(id => newSelection[id] = true);
            rowSelection = newSelection;
        }
    }

    function isAllPageSelected(): boolean {
        const paginatedFiles = getPaginatedFiles();
        if (paginatedFiles.length === 0) return false;
        const startIndex = pagination.pageIndex * pagination.pageSize;
        return paginatedFiles.every((_, i) => rowSelection[String(startIndex + i)]);
    }

    function isSomePageSelected(): boolean {
        const paginatedFiles = getPaginatedFiles();
        const startIndex = pagination.pageIndex * pagination.pageSize;
        const someSelected = paginatedFiles.some((_, i) => rowSelection[String(startIndex + i)]);
        return someSelected && !isAllPageSelected();
    }

    function getSelectedFiles(): FileData[] {
        // Get all selected files using row IDs (which are indices into filteredFiles)
        const selectedIds = Object.keys(rowSelection).filter(k => rowSelection[k]);
        return selectedIds.map(id => {
            const rowIndex = parseInt(id, 10);
            return filteredFiles[rowIndex];
        }).filter(Boolean);
    }

    function getSelectedCount(): number {
        return Object.keys(rowSelection).filter(k => rowSelection[k]).length;
    }

    // Delete confirmation
    function requestDelete(filesToDel: FileData[]) {
        if (filesToDel.length === 0) return;
        filesToDelete = filesToDel;
        showDeleteModal = true;
    }

    function confirmDelete() {
        filesToDelete.forEach(file => onDelete(getFileId(file)));
        rowSelection = {};
        filesToDelete = [];
        showDeleteModal = false;
    }

    function cancelDelete() {
        filesToDelete = [];
        showDeleteModal = false;
        showFileList = false;
    }

    // Bulk actions
    function handleBulkDelete() {
        const selectedFiles = getSelectedFiles();
        if (selectedFiles.length === 0) return;
        requestDelete(selectedFiles);
    }

    function handleSingleDelete(file: FileData) {
        requestDelete([file]);
    }

    function handleBulkDownload() {
        const selectedFiles = getSelectedFiles();
        if (selectedFiles.length === 0) return;

        // Download each file
        selectedFiles.forEach((file, index) => {
            // Stagger downloads to avoid browser blocking
            setTimeout(() => {
                const link = document.createElement('a');
                link.href = getDownloadUrl(file);
                link.download = getFileName(file);
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }, index * 200);
        });
    }

    // Page size change
    function handlePageSizeChange(size: number) {
        const actualSize = size === 0 ? 999999 : size;
        pagination = { pageIndex: 0, pageSize: actualSize };
        // Keep selection when changing page size
        saveToStorage(getStorageKey('pageSize'), size);
    }

    // Pagination helpers
    function getPageNumbers(): (number | 'ellipsis')[] {
        const currentPage = pagination.pageIndex + 1;
        const totalPages = getTotalPages();

        if (totalPages <= 5) {
            return Array.from({ length: totalPages }, (_, i) => i + 1);
        }

        const pages: (number | 'ellipsis')[] = [];

        // Always show first page
        pages.push(1);

        // Calculate range around current
        const start = Math.max(2, currentPage - 1);
        const end = Math.min(totalPages - 1, currentPage + 1);

        if (start > 2) pages.push('ellipsis');

        for (let i = start; i <= end; i++) {
            pages.push(i);
        }

        if (end < totalPages - 1) pages.push('ellipsis');

        // Always show last page
        if (totalPages > 1) pages.push(totalPages);

        return pages;
    }

    function goToPage(pageNum: number) {
        const totalPages = getTotalPages();
        if (pageNum >= 1 && pageNum <= totalPages) {
            pagination = { ...pagination, pageIndex: pageNum - 1 };
        }
    }

    function nextPage() {
        if (canNextPage()) {
            pagination = { ...pagination, pageIndex: pagination.pageIndex + 1 };
        }
    }

    function prevPage() {
        if (canPrevPage()) {
            pagination = { ...pagination, pageIndex: pagination.pageIndex - 1 };
        }
    }

    function getTotalPages(): number {
        return Math.ceil(filteredFiles.length / pagination.pageSize);
    }

    function canNextPage(): boolean {
        return pagination.pageIndex < getTotalPages() - 1;
    }

    function canPrevPage(): boolean {
        return pagination.pageIndex > 0;
    }

    // Get paginated rows
    function getPaginatedFiles(): FileData[] {
        const start = pagination.pageIndex * pagination.pageSize;
        const end = start + pagination.pageSize;
        return filteredFiles.slice(start, end);
    }

    function handlePageInput() {
        const pageNum = parseInt(pageInputValue, 10);
        if (!isNaN(pageNum)) {
            goToPage(pageNum);
        }
        pageInputValue = String(pagination.pageIndex + 1);
    }

    function openGotoModal() {
        gotoPageInput = '';
        showGotoModal = true;
    }

    function handleGotoSubmit() {
        const pageNum = parseInt(gotoPageInput, 10);
        if (!isNaN(pageNum)) {
            goToPage(pageNum);
        }
        showGotoModal = false;
        gotoPageInput = '';
    }

    // Column visibility
    function toggleColumnVisibility(columnId: string) {
        const newVisibility = { ...columnVisibility, [columnId]: !columnVisibility[columnId] };
        columnVisibility = newVisibility;
        saveToStorage(getStorageKey('columnVisibility'), newVisibility);
    }

    function resetColumnsToDefault() {
        columnVisibility = { ...defaultColumnVisibility };
        columnWidths = { ...defaultColumnWidths };
        columnOrder = getDefaultColumnOrder();
        saveToStorage(getStorageKey('columnVisibility'), defaultColumnVisibility);
        saveToStorage(getStorageKey('columnWidths'), defaultColumnWidths);
        saveToStorage(getStorageKey('columnOrder'), getDefaultColumnOrder());
        showColumnDropdown = false;
    }

    // Column resize
    let resizing = $state<{ columnId: string; startX: number; startWidth: number } | null>(null);

    function startResize(columnId: string, event: MouseEvent) {
        event.preventDefault();
        event.stopPropagation();
        resizing = {
            columnId,
            startX: event.clientX,
            startWidth: columnWidths[columnId] || defaultColumnWidths[columnId] || 100,
        };
        document.addEventListener('mousemove', handleResize);
        document.addEventListener('mouseup', stopResize);
    }

    function handleResize(event: MouseEvent) {
        if (!resizing) return;
        const diff = event.clientX - resizing.startX;
        const newWidth = Math.max(60, resizing.startWidth + diff);
        columnWidths = { ...columnWidths, [resizing.columnId]: newWidth };
    }

    function stopResize() {
        if (resizing) {
            saveToStorage(getStorageKey('columnWidths'), columnWidths);
        }
        resizing = null;
        document.removeEventListener('mousemove', handleResize);
        document.removeEventListener('mouseup', stopResize);
    }

    // Dropdown close on outside click
    function handleClickOutside(event: MouseEvent) {
        const target = event.target as HTMLElement;
        if (!target.closest('.column-dropdown-container')) {
            showColumnDropdown = false;
        }
    }

    // Sync page input with actual page
    $effect(() => {
        pageInputValue = String(pagination.pageIndex + 1);
    });

    // Check column visibility
    function isColumnVisible(columnId: string): boolean {
        return columnVisibility[columnId] !== false;
    }

    function getDisplayPageSize(): number {
        return pagination.pageSize >= 999999 ? 0 : pagination.pageSize;
    }

    // Get ordered visible columns
    function getOrderedVisibleColumns(): string[] {
        return columnOrder.filter(id => isColumnVisible(id));
    }

    onMount(() => {
        // Load preferences
        const storedPageSize = loadFromStorage<number>(getStorageKey('pageSize'), 10);
        const currentPageSize = Number(storedPageSize);
        if (currentPageSize !== pagination.pageSize) {
            pagination = { ...pagination, pageSize: currentPageSize === 0 ? 999999 : currentPageSize };
        }

        const storedVisibility = loadFromStorage(getStorageKey('columnVisibility'), defaultColumnVisibility);
        columnVisibility = storedVisibility;

        const storedWidths = loadFromStorage(getStorageKey('columnWidths'), defaultColumnWidths);
        columnWidths = storedWidths;

        const storedOrder = loadFromStorage(getStorageKey('columnOrder'), getDefaultColumnOrder());
        columnOrder = storedOrder;

        document.addEventListener('click', handleClickOutside);
        return () => {
            document.removeEventListener('click', handleClickOutside);
        };
    });
</script>

<div class="files-table-container">
    <!-- Toolbar -->
    <div class="table-toolbar">
        <div class="toolbar-left">
            <!-- Search box - sempre visibile a sinistra -->
            <div class="search-box">
                <Search size={16} class="search-icon" />
                <input
                    type="text"
                    class="search-input"
                    placeholder={$t('common.search') || 'Search...'}
                    bind:value={searchQuery}
                />
                {#if searchQuery}
                    <button
                        type="button"
                        class="search-clear"
                        onclick={() => searchQuery = ''}
                    >
                        <X size={14} />
                    </button>
                {/if}
            </div>
        </div>
        <div class="toolbar-right">
            <!-- Selection info e bulk actions -->
            {#if getSelectedCount() > 0}
                <span class="selected-count">
                    {getSelectedCount()} {$t('table.selected') || 'selected'}
                </span>
                <div class="bulk-actions">
                    <button
                        type="button"
                        class="bulk-btn"
                        onclick={handleBulkDownload}
                        title={$t('uploads.download')}
                    >
                        <Download size={16} />
                    </button>
                    <button
                        type="button"
                        class="bulk-btn danger"
                        onclick={handleBulkDelete}
                        title={$t('common.delete')}
                    >
                        <Trash2 size={16} />
                    </button>
                </div>
            {/if}
            <div class="column-dropdown-container">
                <button
                    type="button"
                    class="toolbar-btn"
                    onclick={() => showColumnDropdown = !showColumnDropdown}
                    title={$t('table.showColumns')}
                >
                    <Eye size={16} />
                </button>
                {#if showColumnDropdown}
                    <div class="column-dropdown">
                        <div class="dropdown-header">
                            {$t('table.showColumns')}
                        </div>
                        <div class="dropdown-content">
                            {#each getAllColumnDefs() as col}
                                <button
                                    type="button"
                                    class="column-option"
                                    onclick={(e) => {
                                        e.stopPropagation();
                                        toggleColumnVisibility(col.id);
                                    }}
                                >
                                    <span class="col-visibility-icon">
                                        {#if isColumnVisible(col.id)}
                                            <Eye size={16} />
                                        {:else}
                                            <EyeOff size={16} />
                                        {/if}
                                    </span>
                                    <span class="col-name">{col.label()}</span>
                                    <span class="col-drag">
                                        <GripVertical size={14} />
                                    </span>
                                </button>
                            {/each}
                        </div>
                        <button
                            type="button"
                            class="reset-btn"
                            onclick={resetColumnsToDefault}
                        >
                            <RotateCcw size={14} />
                            <span>Reset</span>
                        </button>
                    </div>
                {/if}
            </div>
        </div>
    </div>

    <!-- Table -->
    <div class="table-wrapper">
        <table class="files-table">
            <thead>
                <tr>
                    <!-- Fixed: Selection header -->
                    <th class="th-fixed th-select">
                        <button
                            type="button"
                            class="checkbox-btn"
                            onclick={toggleAllPageRows}
                            title={isAllPageSelected() ? 'Deselect page' : 'Select page'}
                        >
                            {#if isAllPageSelected()}
                                <Check size={16} class="check-icon checked" />
                            {:else if isSomePageSelected()}
                                <Check size={16} class="check-icon partial" />
                            {:else}
                                <span class="check-box"></span>
                            {/if}
                        </button>
                    </th>

                    <!-- Dynamic columns -->
                    {#each getOrderedVisibleColumns() as columnId}
                        {@const column = table.getColumn(columnId)}
                        {#if column}
                            <th
                                class="th-{columnId}"
                                class:sortable={column.getCanSort()}
                                style="width: {columnWidths[columnId] || defaultColumnWidths[columnId]}px;"
                            >
                                <div class="header-content">
                                    <button
                                        type="button"
                                        class="header-sort-btn"
                                        onclick={() => column.getCanSort() && column.toggleSorting()}
                                        disabled={!column.getCanSort()}
                                    >
                                        <span class="header-text">
                                            {#if columnId === 'filename'}
                                                {$t('uploads.fileName')}
                                            {:else if columnId === 'status'}
                                                Status
                                            {:else if columnId === 'size'}
                                                {$t('uploads.fileSize')}
                                            {:else if columnId === 'date'}
                                                {$t('uploads.uploadDate')}
                                            {/if}
                                        </span>
                                        {#if column.getCanSort()}
                                            {@const sorted = column.getIsSorted()}
                                            <span class="sort-icon">
                                                {#if sorted === 'asc'}
                                                    <ChevronUp size={14} />
                                                {:else if sorted === 'desc'}
                                                    <ChevronDown size={14} />
                                                {:else}
                                                    <ChevronsUpDown size={14} />
                                                {/if}
                                            </span>
                                        {/if}
                                    </button>
                                    <!-- Resize handle -->
                                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                                    <span
                                        class="resize-handle"
                                        class:resizing={resizing?.columnId === columnId}
                                        onmousedown={(e) => startResize(columnId, e)}
                                    ></span>
                                </div>
                            </th>
                        {/if}
                    {/each}

                    <!-- Fixed: Actions header -->
                    <th class="th-fixed th-actions">
                        {$t('uploads.actions')}
                    </th>
                </tr>
            </thead>
            <tbody>
                {#each getPaginatedFiles() as file, rowIndex}
                    {@const rowId = String(pagination.pageIndex * pagination.pageSize + rowIndex)}
                    {@const FileIconComponent = getFileIcon(file)}
                    {@const isSelected = rowSelection[rowId]}
                    <tr class:selected={isSelected}>
                        <!-- Fixed: Selection cell -->
                        <td class="td-fixed td-select">
                            <button
                                type="button"
                                class="checkbox-btn"
                                onclick={() => {
                                    const newSelection = { ...rowSelection };
                                    if (newSelection[rowId]) {
                                        delete newSelection[rowId];
                                    } else {
                                        newSelection[rowId] = true;
                                    }
                                    rowSelection = newSelection;
                                }}
                            >
                                {#if isSelected}
                                    <Check size={16} class="check-icon checked" />
                                {:else}
                                    <span class="check-box"></span>
                                {/if}
                            </button>
                        </td>

                        <!-- Dynamic columns -->
                        {#each getOrderedVisibleColumns() as columnId}
                            {#if columnId === 'filename'}
                                <td class="td-filename" style="width: {columnWidths['filename'] || defaultColumnWidths['filename']}px;">
                                    <div class="filename-cell">
                                        <FileIconComponent size={18} class="file-icon" />
                                        <span class="filename-text" title={getFileName(file)}>
                                            {getFileName(file)}
                                        </span>
                                    </div>
                                </td>
                            {:else if columnId === 'status' && type === 'brim'}
                                {@const status = getBrimStatus(file)}
                                <td class="td-status" style="width: {columnWidths['status'] || defaultColumnWidths['status']}px;">
                                    <span class="status-badge status-{status}">
                                        {translateStatus(status)}
                                    </span>
                                </td>
                            {:else if columnId === 'size'}
                                <td class="td-size" style="width: {columnWidths['size'] || defaultColumnWidths['size']}px;">
                                    {formatBytes(getFileSize(file))}
                                </td>
                            {:else if columnId === 'date'}
                                <td class="td-date" style="width: {columnWidths['date'] || defaultColumnWidths['date']}px;">
                                    {formatDate(file.uploaded_at)}
                                </td>
                            {/if}
                        {/each}

                        <!-- Fixed: Actions cell -->
                        <td class="td-fixed td-actions">
                            <div class="action-buttons">
                                <a
                                    href={getDownloadUrl(file)}
                                    download={getFileName(file)}
                                    class="action-btn"
                                    title={$t('uploads.download')}
                                >
                                    <Download size={16} />
                                </a>
                                <button
                                    type="button"
                                    class="action-btn danger"
                                    onclick={() => handleSingleDelete(file)}
                                    title={$t('common.delete')}
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        </td>
                    </tr>
                {:else}
                    <tr>
                        <td colspan="100" class="empty-row">
                            {$t('table.noResults')}
                        </td>
                    </tr>
                {/each}
            </tbody>
        </table>
    </div>

    <!-- Floating Pagination -->
    <div class="pagination-float">
        <div class="pagination-inner">
            <!-- Page size -->
            <select
                class="page-size-select"
                onchange={(e) => {
                    const target = e.target;
                    if (target instanceof HTMLSelectElement) {
                        handlePageSizeChange(parseInt(target.value, 10));
                    }
                }}
            >
                {#each PAGE_SIZE_OPTIONS as size}
                    <option value={size} selected={size === getDisplayPageSize()}>
                        {size === 0 ? '∞' : size}
                    </option>
                {/each}
            </select>

            <!-- Navigation -->
            <div class="page-nav">
                <button
                    type="button"
                    class="page-btn nav"
                    disabled={!canPrevPage()}
                    onclick={prevPage}
                    title={$t('table.previousPage')}
                >
                    <ChevronLeft size={16} />
                </button>

                <!-- Page numbers -->
                {#each getPageNumbers() as pageNum}
                    {#if pageNum === 'ellipsis'}
                        <span class="page-ellipsis">...</span>
                    {:else if typeof pageNum === 'number'}
                        {@const pageNumber = pageNum}
                        {@const isCurrent = pageNumber === pagination.pageIndex + 1}
                        {#if isCurrent}
                            <input
                                type="number"
                                class="page-input"
                                min="1"
                                max={getTotalPages()}
                                bind:value={pageInputValue}
                                onkeydown={(e) => e.key === 'Enter' && handlePageInput()}
                                onblur={handlePageInput}
                            />
                        {:else}
                            <button
                                type="button"
                                class="page-btn num"
                                onclick={() => goToPage(pageNumber)}
                            >
                                {pageNumber}
                            </button>
                        {/if}
                    {/if}
                {/each}

                <button
                    type="button"
                    class="page-btn nav"
                    disabled={!canNextPage()}
                    onclick={nextPage}
                    title={$t('table.nextPage')}
                >
                    <ChevronRight size={16} />
                </button>
            </div>
        </div>
    </div>
</div>

<!-- Delete Confirmation Modal -->
{#if showDeleteModal}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="modal-overlay" onclick={cancelDelete} onkeydown={(e) => e.key === 'Escape' && cancelDelete()}>
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <div class="modal-content" onclick={(e) => e.stopPropagation()}>
            <div class="modal-header">
                <Trash2 size={24} class="modal-icon danger" />
                <h3>{$t('common.confirmDelete') || 'Confirm Delete'}</h3>
            </div>
            <div class="modal-body">
                {#if filesToDelete.length === 1}
                    <p>{$t('uploads.deleteConfirmSingle')}</p>
                    <p class="file-name-preview">{getFileName(filesToDelete[0])}</p>
                {:else}
                    <p>{$t('uploads.deleteConfirmMultiple')}</p>
                    <div class="file-count-container">
                        <span class="file-count">{filesToDelete.length} {$t('uploads.files')}</span>
                        <button
                            type="button"
                            class="toggle-list-btn"
                            onclick={() => showFileList = !showFileList}
                        >
                            {showFileList ? $t('uploads.hideFileList') : $t('uploads.showFileList')}
                            <ChevronDown size={14} class="chevron {showFileList ? 'rotated' : ''}" />
                        </button>
                    </div>
                    {#if showFileList}
                        <ul class="file-list">
                            {#each filesToDelete as file}
                                <li>{getFileName(file)}</li>
                            {/each}
                        </ul>
                    {/if}
                {/if}
            </div>
            <div class="modal-footer">
                <button type="button" class="btn-cancel" onclick={cancelDelete}>
                    {$t('common.cancel')}
                </button>
                <button type="button" class="btn-delete" onclick={confirmDelete}>
                    <Trash2 size={16} />
                    {$t('common.delete')}
                </button>
            </div>
        </div>
    </div>
{/if}

<style>
    .files-table-container {
        width: 100%;
        display: flex;
        flex-direction: column;
        position: relative;
    }

    /* Toolbar */
    .table-toolbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem 0;
        gap: 1rem;
        min-height: 40px;
    }

    .toolbar-left, .toolbar-right {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .selected-count {
        font-size: 0.875rem;
        color: #3b82f6;
        font-weight: 500;
    }

    .bulk-actions {
        display: flex;
        gap: 0.25rem;
    }

    /* Search box */
    .search-box {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.375rem 0.75rem;
        border: 1px solid #e5e7eb;
        border-radius: 0.375rem;
        background: white;
        min-width: 200px;
    }

    :global(.dark) .search-box {
        background: #374151;
        border-color: #4b5563;
    }

    .search-box :global(.search-icon) {
        color: #9ca3af;
        flex-shrink: 0;
    }

    .search-input {
        flex: 1;
        border: none;
        background: transparent;
        font-size: 0.875rem;
        color: #1f2937;
        outline: none;
        min-width: 0;
    }

    :global(.dark) .search-input {
        color: #f3f4f6;
    }

    .search-input::placeholder {
        color: #9ca3af;
    }

    .search-clear {
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
        flex-shrink: 0;
    }

    .search-clear:hover {
        background: #d1d5db;
        color: #1f2937;
    }

    :global(.dark) .search-clear {
        background: #4b5563;
        color: #9ca3af;
    }

    :global(.dark) .search-clear:hover {
        background: #6b7280;
        color: #f3f4f6;
    }

    .bulk-btn {
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
        transition: all 0.15s;
    }

    .bulk-btn:hover {
        background: #f3f4f6;
        color: #1f2937;
    }

    .bulk-btn.danger {
        color: #dc2626;
        border-color: #fecaca;
    }

    .bulk-btn.danger:hover {
        background: #fef2f2;
    }

    :global(.dark) .bulk-btn {
        background: #374151;
        border-color: #4b5563;
        color: #9ca3af;
    }

    :global(.dark) .bulk-btn:hover {
        background: #4b5563;
        color: #f3f4f6;
    }

    :global(.dark) .bulk-btn.danger {
        color: #f87171;
        border-color: rgba(220, 38, 38, 0.3);
    }

    .toolbar-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        border: 1px solid #e5e7eb;
        border-radius: 0.375rem;
        background: white;
        color: #6b7280;
        cursor: pointer;
        transition: all 0.15s;
    }

    .toolbar-btn:hover {
        background: #f3f4f6;
        color: #1f2937;
    }

    :global(.dark) .toolbar-btn {
        background: #374151;
        border-color: #4b5563;
        color: #9ca3af;
    }

    :global(.dark) .toolbar-btn:hover {
        background: #4b5563;
        color: #f3f4f6;
    }

    /* Column dropdown */
    .column-dropdown-container {
        position: relative;
    }

    .column-dropdown {
        position: absolute;
        top: 100%;
        right: 0;
        margin-top: 0.25rem;
        min-width: 220px;
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 0.5rem;
        box-shadow: 0 10px 25px -5px rgb(0 0 0 / 0.1);
        z-index: 50;
        overflow: hidden;
    }

    :global(.dark) .column-dropdown {
        background: #1f2937;
        border-color: #374151;
    }

    .dropdown-header {
        padding: 0.75rem 1rem;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        color: #6b7280;
        border-bottom: 1px solid #e5e7eb;
    }

    :global(.dark) .dropdown-header {
        border-bottom-color: #374151;
        color: #9ca3af;
    }

    .dropdown-content {
        padding: 0.25rem 0;
    }

    .column-option {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        width: 100%;
        padding: 0.5rem 1rem;
        border: none;
        background: none;
        cursor: pointer;
        font-size: 0.875rem;
        color: #1f2937;
        text-align: left;
    }

    .column-option:hover {
        background: #f3f4f6;
    }

    :global(.dark) .column-option {
        color: #f3f4f6;
    }

    :global(.dark) .column-option:hover {
        background: #374151;
    }

    .col-visibility-icon {
        color: #6b7280;
        flex-shrink: 0;
    }

    .col-name {
        flex: 1;
    }

    .col-drag {
        color: #9ca3af;
        opacity: 0.5;
    }

    .reset-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        width: 100%;
        padding: 0.75rem 1rem;
        border: none;
        border-top: 1px solid #e5e7eb;
        background: #f9fafb;
        color: #6b7280;
        font-size: 0.75rem;
        cursor: pointer;
    }

    .reset-btn:hover {
        background: #f3f4f6;
        color: #1f2937;
    }

    :global(.dark) .reset-btn {
        background: #111827;
        border-top-color: #374151;
        color: #9ca3af;
    }

    :global(.dark) .reset-btn:hover {
        background: #1f2937;
        color: #f3f4f6;
    }

    /* Table */
    .table-wrapper {
        overflow-x: auto;
        border: 1px solid #e5e7eb;
        border-radius: 0.5rem;
    }

    :global(.dark) .table-wrapper {
        border-color: #374151;
    }

    .files-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: auto;
    }

    .files-table th {
        padding: 0.625rem 0.5rem;
        text-align: left;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        color: #6b7280;
        background: #f9fafb;
        border-bottom: 1px solid #e5e7eb;
        white-space: nowrap;
        position: relative;
    }

    :global(.dark) .files-table th {
        background: #1f2937;
        color: #9ca3af;
        border-bottom-color: #374151;
    }

    /* Fixed columns */
    .th-fixed, .td-fixed {
        z-index: 1;
        background: inherit;
    }

    .th-select, .td-select {
        position: sticky;
        left: 0;
        width: 44px !important;
        min-width: 44px !important;
        max-width: 44px !important;
        text-align: center;
        padding: 0.5rem !important;
    }

    .th-actions, .td-actions {
        width: 80px !important;
        min-width: 80px !important;
        max-width: 80px !important;
        text-align: center;
    }

    /* Actions sticky only on desktop */
    @media (min-width: 768px) {
        .th-actions, .td-actions {
            position: sticky;
            right: 0;
        }
    }

    .th-select {
        background: #f9fafb;
    }

    .td-select {
        background: white;
    }

    :global(.dark) .th-select {
        background: #1f2937;
    }

    :global(.dark) .td-select {
        background: #111827;
    }

    tr.selected .td-select {
        background: #eff6ff;
    }

    :global(.dark) tr.selected .td-select {
        background: rgba(59, 130, 246, 0.15);
    }

    /* Checkbox */
    .checkbox-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        border: none;
        background: none;
        cursor: pointer;
        padding: 0;
        margin: 0 auto;
    }

    .check-box {
        width: 16px;
        height: 16px;
        border: 2px solid #d1d5db;
        border-radius: 3px;
        background: white;
    }

    :global(.dark) .check-box {
        border-color: #4b5563;
        background: #374151;
    }

    .checkbox-btn:hover .check-box {
        border-color: #3b82f6;
    }

    :global(.check-icon) {
        color: #3b82f6;
    }

    :global(.check-icon.partial) {
        opacity: 0.5;
    }

    /* Header content */
    .header-content {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.25rem;
    }

    .header-sort-btn {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        background: none;
        border: none;
        font: inherit;
        color: inherit;
        text-transform: inherit;
        cursor: pointer;
        padding: 0;
    }

    .header-sort-btn:disabled {
        cursor: default;
    }

    .header-sort-btn:not(:disabled):hover {
        color: #1f2937;
    }

    :global(.dark) .header-sort-btn:not(:disabled):hover {
        color: #f3f4f6;
    }

    .sort-icon {
        color: #9ca3af;
    }

    /* Resize handle */
    .resize-handle {
        position: absolute;
        right: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        cursor: col-resize;
        background: #e5e7eb;
        opacity: 0;
        transition: opacity 0.15s;
    }

    th:hover .resize-handle,
    .resize-handle.resizing {
        opacity: 1;
    }

    .resize-handle:hover,
    .resize-handle.resizing {
        background: #3b82f6;
    }

    :global(.dark) .resize-handle {
        background: #4b5563;
    }

    /* Table cells */
    .files-table td {
        padding: 0.625rem 0.5rem;
        font-size: 0.875rem;
        color: #1f2937;
        border-bottom: 1px solid #e5e7eb;
        vertical-align: middle;
        overflow: hidden;
        text-overflow: ellipsis;
        background: white;
    }

    :global(.dark) .files-table td {
        color: #f3f4f6;
        border-bottom-color: #374151;
        background: #111827;
    }

    .files-table tbody tr:last-child td {
        border-bottom: none;
    }

    .files-table tbody tr:hover td {
        background: #f9fafb;
    }

    :global(.dark) .files-table tbody tr:hover td {
        background: #1f2937;
    }

    .files-table tbody tr.selected td {
        background: #eff6ff;
    }

    :global(.dark) .files-table tbody tr.selected td {
        background: rgba(59, 130, 246, 0.15);
    }

    /* Filename cell */
    .filename-cell {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        min-width: 0;
    }

    .filename-cell :global(.file-icon) {
        flex-shrink: 0;
        color: #6b7280;
    }

    :global(.dark) .filename-cell :global(.file-icon) {
        color: #9ca3af;
    }

    .filename-text {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* Size and date */
    .td-size, .td-date {
        white-space: nowrap;
        color: #6b7280;
    }

    :global(.dark) .td-size, :global(.dark) .td-date {
        color: #9ca3af;
    }

    /* Actions */
    .action-buttons {
        display: flex;
        justify-content: center;
        gap: 0.25rem;
    }

    .action-btn {
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
        transition: all 0.15s;
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

    .action-btn.danger:hover {
        background: #fef2f2;
    }

    :global(.dark) .action-btn.danger {
        color: #f87171;
        border-color: rgba(220, 38, 38, 0.3);
    }

    :global(.dark) .action-btn.danger:hover {
        background: rgba(220, 38, 38, 0.2);
    }

    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.125rem 0.5rem;
        font-size: 0.75rem;
        font-weight: 500;
        border-radius: 9999px;
    }

    .status-uploaded {
        background: #dbeafe;
        color: #1d4ed8;
    }

    :global(.dark) .status-uploaded {
        background: rgba(59, 130, 246, 0.2);
        color: #93c5fd;
    }

    .status-parsed, .status-imported {
        background: #d1fae5;
        color: #059669;
    }

    :global(.dark) .status-parsed, :global(.dark) .status-imported {
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

    .empty-row {
        text-align: center;
        padding: 2rem !important;
        color: #6b7280;
    }

    :global(.dark) .empty-row {
        color: #9ca3af;
    }

    /* Floating Pagination */
    .pagination-float {
        position: sticky;
        bottom: 1.5rem;
        left: 0;
        right: 0;
        display: flex;
        justify-content: center;
        z-index: 40;
        pointer-events: none;
        margin-top: 1rem;
    }

    .pagination-inner {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.5rem 0.75rem;
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 9999px;
        box-shadow: 0 4px 12px rgb(0 0 0 / 0.15);
        pointer-events: auto;
    }

    :global(.dark) .pagination-inner {
        background: #1f2937;
        border-color: #374151;
    }

    .page-size-select {
        padding: 0.25rem 0.5rem;
        border: 1px solid #e5e7eb;
        border-radius: 0.375rem;
        background: white;
        color: #1f2937;
        font-size: 0.875rem;
        cursor: pointer;
        min-width: 50px;
    }

    :global(.dark) .page-size-select {
        background: #374151;
        border-color: #4b5563;
        color: #f3f4f6;
    }

    .page-nav {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    .page-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        border: none;
        background: none;
        color: #6b7280;
        cursor: pointer;
        transition: all 0.15s;
    }

    .page-btn.nav {
        width: 28px;
        height: 28px;
        border-radius: 0.25rem;
    }

    .page-btn.num {
        min-width: 28px;
        height: 28px;
        padding: 0 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.875rem;
    }

    .page-btn:hover:not(:disabled) {
        background: #f3f4f6;
        color: #1f2937;
    }

    :global(.dark) .page-btn:hover:not(:disabled) {
        background: #374151;
        color: #f3f4f6;
    }

    .page-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
    }

    .page-ellipsis {
        color: #9ca3af;
        padding: 0 0.25rem;
        font-size: 0.875rem;
    }

    .page-input {
        width: 40px;
        height: 28px;
        padding: 0 0.25rem;
        border: 1px solid #3b82f6;
        border-radius: 0.25rem;
        background: #eff6ff;
        color: #1d4ed8;
        font-size: 0.875rem;
        text-align: center;
        font-weight: 500;
    }

    :global(.dark) .page-input {
        background: rgba(59, 130, 246, 0.2);
        border-color: #3b82f6;
        color: #93c5fd;
    }

    .page-input::-webkit-inner-spin-button,
    .page-input::-webkit-outer-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }

    /* Delete Confirmation Modal */
    .modal-overlay {
        position: absolute;
        inset: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 100;
        min-height: 300px;
    }

    .modal-content {
        background: white;
        border-radius: 0.75rem;
        box-shadow: 0 25px 50px -12px rgb(0 0 0 / 0.25);
        max-width: 400px;
        width: 90%;
    }

    :global(.dark) .modal-content {
        background: #1f2937;
    }

    .modal-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1.25rem 1.5rem;
        border-bottom: 1px solid #e5e7eb;
    }

    :global(.dark) .modal-header {
        border-bottom-color: #374151;
    }

    .modal-header h3 {
        font-size: 1.125rem;
        font-weight: 600;
        color: #1f2937;
        margin: 0;
    }

    :global(.dark) .modal-header h3 {
        color: #f3f4f6;
    }

    .modal-header :global(.modal-icon.danger) {
        color: #dc2626;
    }

    .modal-body {
        padding: 1.25rem 1.5rem;
    }

    .modal-body p {
        margin: 0 0 0.5rem 0;
        color: #4b5563;
    }

    :global(.dark) .modal-body p {
        color: #9ca3af;
    }

    .file-name-preview {
        font-weight: 500;
        color: #1f2937 !important;
        word-break: break-all;
    }

    :global(.dark) .file-name-preview {
        color: #f3f4f6 !important;
    }

    .file-count-container {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .file-count {
        font-weight: 600;
        color: #dc2626 !important;
    }

    .toggle-list-btn {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        background: none;
        border: none;
        color: #3b82f6;
        font-size: 0.75rem;
        cursor: pointer;
        padding: 0;
    }

    .toggle-list-btn:hover {
        text-decoration: underline;
    }

    .toggle-list-btn :global(.chevron) {
        transition: transform 0.2s;
    }

    .toggle-list-btn :global(.chevron.rotated) {
        transform: rotate(180deg);
    }

    .file-list {
        margin: 0.75rem 0 0 0;
        padding: 0.5rem;
        background: #f3f4f6;
        border-radius: 0.375rem;
        max-height: 150px;
        overflow-y: auto;
        list-style: none;
    }

    :global(.dark) .file-list {
        background: #374151;
    }

    .file-list li {
        font-size: 0.75rem;
        color: #4b5563;
        padding: 0.25rem 0;
        border-bottom: 1px solid #e5e7eb;
        word-break: break-all;
    }

    .file-list li:last-child {
        border-bottom: none;
    }

    :global(.dark) .file-list li {
        color: #9ca3af;
        border-bottom-color: #4b5563;
    }

    .modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
        padding: 1rem 1.5rem;
        border-top: 1px solid #e5e7eb;
        border-radius: 0 0 0.75rem 0.75rem;
    }

    :global(.dark) .modal-footer {
        border-top-color: #374151;
    }

    .btn-cancel {
        padding: 0.5rem 1rem;
        border: 1px solid #e5e7eb;
        border-radius: 0.375rem;
        background: white;
        color: #4b5563;
        font-size: 0.875rem;
        cursor: pointer;
    }

    .btn-cancel:hover {
        background: #f3f4f6;
    }

    :global(.dark) .btn-cancel {
        background: #374151;
        border-color: #4b5563;
        color: #9ca3af;
    }

    :global(.dark) .btn-cancel:hover {
        background: #4b5563;
    }

    .btn-delete {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        border: none;
        border-radius: 0.375rem;
        background: #dc2626;
        color: white;
        font-size: 0.875rem;
        cursor: pointer;
    }

    .btn-delete:hover {
        background: #b91c1c;
    }
</style>
