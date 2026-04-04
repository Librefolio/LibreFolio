<!--
  DataTable - Generic reusable table component with all features

  Features:
  - User-defined columns with full control over content
  - Row selection with bulk actions
  - Column sorting, filtering (Excel-style), resizing
  - Sticky select/actions columns
  - Pagination with floating balloon
  - Preferences saved to localStorage
  - Dark mode support
-->
<script generics="T" lang="ts">
    import {onMount} from 'svelte';
    import {t} from '$lib/i18n';
    import {formatBytes} from '$lib/utils/upload';
    import {getUserStorageKey} from '$lib/utils/storage';
    import {Check, ChevronDown, ChevronsUpDown, ChevronUp, ExternalLink, Filter, ImageIcon, Info} from 'lucide-svelte';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';
    import DataTablePagination from './DataTablePagination.svelte';
    import DataTableColumnFilter from './DataTableColumnFilter.svelte';
    import ConfirmModal from '$lib/components/ui/ConfirmModal.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import type {BulkAction, CellContent, ColumnDef, ColumnWidthsState, FilterValue, PaginationState, RowAction, SelectionState, SortState, VisibilityState} from './types';

    interface Props {
        data: T[];
        columns: ColumnDef<T>[];
        getRowId: (row: T) => string;
        storageKey: string;
        enableSelection?: boolean;
        selectionMode?: 'multi' | 'single' | 'none';
        selectionColumnWidth?: string;
        onSelectionChange?: (selectedIds: string[]) => void;
        selectedRowId?: string | null;
        onRowClick?: (row: T) => void;
        onRowDoubleClick?: (row: T) => void;
        enableActions?: boolean;
        actionsColumnWidth?: string;
        rowActions?: RowAction<T>[];
        bulkActions?: BulkAction<T>[];
        enableSorting?: boolean;
        enableColumnFilters?: boolean;
        enableColumnResize?: boolean;
        enablePagination?: boolean;
        enableColumnVisibility?: boolean;
        defaultPageSize?: number;
        pageSizeOptions?: number[];
        emptyMessage?: string;
        isLoading?: boolean;
        getRowDisplayName?: (row: T) => string;
        /** Called when column filters change (for URL sync) */
        onFiltersChange?: (filters: Record<string, FilterValue>) => void;
        /** Initial filters to apply (from URL params) */
        initialFilters?: Record<string, FilterValue>;
        /** Optional function to add CSS classes to a row based on its data */
        getRowClass?: (row: T) => string;
        /** Optional function to add inline styles to a row (e.g. CSS custom properties) */
        getRowStyle?: (row: T) => string;
        /** Table layout mode: 'fixed' (default) or 'auto' (columns expand to fill space) */
        tableLayout?: 'fixed' | 'auto';
        /** Optional predicate: if returns false, row checkbox is hidden and row is excluded from bulk select */
        isRowSelectable?: (row: T) => boolean;
    }

    let {
        data,
        columns,
        getRowId,
        storageKey,
        enableSelection = true,
        selectionMode = 'multi',
        selectionColumnWidth = '48px',
        onSelectionChange,
        selectedRowId = null,
        onRowClick,
        onRowDoubleClick,
        enableActions = true,
        actionsColumnWidth = '100px',
        rowActions = [],
        bulkActions = [],
        enableSorting = true,
        enableColumnFilters = true,
        enableColumnResize = true,
        enablePagination = true,
        enableColumnVisibility = true,
        defaultPageSize = 10,
        pageSizeOptions = [10, 25, 50, 100, 0],
        emptyMessage,
        isLoading = false,
        getRowDisplayName,
        onFiltersChange,
        initialFilters,
        getRowClass,
        getRowStyle,
        tableLayout = 'fixed',
        isRowSelectable,
    }: Props = $props();

    // Derived: effective selection mode
    let effectiveSelectionMode = $derived(
        !enableSelection ? 'none' : selectionMode
    );

    // ============ State ============

    // Helper to get initial page size (avoids warning about capturing props in $state)
    function getInitialPageSize(): number {
        return defaultPageSize;
    }

    // Sorting
    let sortState = $state<SortState | null>(null);

    // Pagination
    let pagination = $state<PaginationState>({
        pageIndex: 0,
        pageSize: getInitialPageSize(),
    });

    // Column visibility
    let columnVisibility = $state<VisibilityState>({});

    // Column widths
    let columnWidths = $state<ColumnWidthsState>({});

    // Column order
    let columnOrder = $state<string[]>([]);

    // Row selection
    let rowSelection = $state<SelectionState>({});

    // Show selected only filter
    let showSelectedOnly = $state(false);

    // Column filters
    let columnFilters = $state<Record<string, FilterValue>>({});

    // UI state
    let openFilterColumnId = $state<string | null>(null);

    // Delete confirmation modal
    let showDeleteModal = $state(false);
    let pendingBulkAction = $state<BulkAction<T> | null>(null);

    // Row action confirmation modal
    let showRowActionModal = $state(false);
    let pendingRowAction = $state<{ action: RowAction<T>; row: T } | null>(null);

    // Resize state
    let resizing = $state<{ columnId: string; startX: number; startWidth: number } | null>(null);

    // Highlighted row (set by navigateToRowId, cleared on user interaction)
    let highlightedRowId = $state<string | null>(null);

    // Filter button refs (for fixed-position popover)
    let filterBtnRefs = $state<Record<string, HTMLButtonElement | null>>({});

    // ============ Storage Helpers ============

    function getStorageKey(suffix: string): string {
        return getUserStorageKey(`dataTable_${storageKey}_${suffix}`);
    }

    function loadFromStorage<V>(key: string, defaultValue: V): V {
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
        } catch {
        }
    }

    // ============ Derived State ============

    // Default column order
    let defaultColumnOrder = $derived(columns.map(c => c.id));

    // Default column visibility (respects hiddenByDefault)
    let defaultColumnVisibility = $derived(
        Object.fromEntries(columns.map(c => [c.id, !c.hiddenByDefault]))
    );

    // Default column widths
    let defaultColumnWidths = $derived(
        Object.fromEntries(columns.map(c => [c.id, c.width ?? 150]))
    );

    // All columns in current order (for toolbar dropdown)
    let orderedColumns = $derived(
        columnOrder
            .map(id => columns.find(c => c.id === id))
            .filter((c): c is ColumnDef<T> => c !== undefined)
    );

    // Visible and ordered columns (for table rendering)
    let visibleColumns = $derived(
        orderedColumns.filter(c => columnVisibility[c.id] !== false)
    );

    // Filtered data
    let filteredData = $derived.by(() => {
        let result = [...data];

        // Apply "show selected only" filter
        if (showSelectedOnly) {
            result = result.filter(row => rowSelection[getRowId(row)]);
        }

        // Apply column filters
        for (const [columnId, filterValue] of Object.entries(columnFilters)) {
            if (!filterValue) continue;

            const column = columns.find(c => c.id === columnId);
            if (!column) continue;

            result = result.filter(row => {
                const getValue = column.getValue ?? column.cell;
                const cellValue = getValue(row);
                const rawValue = typeof cellValue === 'object' && cellValue !== null && 'type' in cellValue
                    ? String(cellValue)
                    : cellValue;

                if (filterValue.type === 'text') {
                    const str = String(rawValue).toLowerCase();
                    const search = filterValue.value.toLowerCase();
                    switch (filterValue.matchMode) {
                        case 'contains':
                            return str.includes(search);
                        case 'startsWith':
                            return str.startsWith(search);
                        case 'endsWith':
                            return str.endsWith(search);
                        case 'equals':
                            return str === search;
                    }
                } else if (filterValue.type === 'number') {
                    const num = Number(rawValue);
                    if (filterValue.min !== undefined && num < filterValue.min) return false;
                    if (filterValue.max !== undefined && num > filterValue.max) return false;
                    return true;
                } else if (filterValue.type === 'size') {
                    // Size filter - rawValue should be bytes (from SizeCell)
                    const bytes = typeof rawValue === 'object' && rawValue !== null && 'type' in rawValue && (rawValue as unknown as { type: string }).type === 'size'
                        ? (rawValue as unknown as { bytes: number }).bytes
                        : Number(rawValue);
                    if (filterValue.minBytes !== undefined && bytes < filterValue.minBytes) return false;
                    if (filterValue.maxBytes !== undefined && bytes > filterValue.maxBytes) return false;
                    return true;
                } else if (filterValue.type === 'date') {
                    const dateStr = typeof rawValue === 'object' && rawValue !== null && 'type' in rawValue && (rawValue as unknown as { type: string }).type === 'date'
                        ? String((rawValue as unknown as { value: Date | string }).value)
                        : String(rawValue);
                    const date = new Date(dateStr);
                    if (filterValue.from && date < new Date(filterValue.from)) return false;
                    if (filterValue.to && date > new Date(filterValue.to)) return false;
                    return true;
                } else if (filterValue.type === 'enum') {
                    return filterValue.selected.includes(String(rawValue));
                }
                return true;
            });
        }

        return result;
    });

    // Sorted data
    let sortedData = $derived.by(() => {
        if (!sortState || !enableSorting) return filteredData;

        const column = columns.find(c => c.id === sortState!.columnId);
        if (!column) return filteredData;

        return [...filteredData].sort((a, b) => {
            const getValue = column.getValue ?? column.cell;
            const aVal = getValue(a);
            const bVal = getValue(b);

            // Extract raw value if it's a CellContent object
            const aRaw = typeof aVal === 'object' && aVal !== null && 'type' in aVal ? extractRawValue(aVal as CellContent) : aVal;
            const bRaw = typeof bVal === 'object' && bVal !== null && 'type' in bVal ? extractRawValue(bVal as CellContent) : bVal;

            let comparison = 0;
            if (typeof aRaw === 'number' && typeof bRaw === 'number') {
                comparison = aRaw - bRaw;
            } else if (aRaw instanceof Date && bRaw instanceof Date) {
                comparison = aRaw.getTime() - bRaw.getTime();
            } else {
                comparison = String(aRaw).localeCompare(String(bRaw));
            }

            return sortState!.direction === 'asc' ? comparison : -comparison;
        });
    });

    // Paginated data
    let paginatedData = $derived.by(() => {
        if (!enablePagination) return sortedData;
        const start = pagination.pageIndex * pagination.pageSize;
        return sortedData.slice(start, start + pagination.pageSize);
    });

    // Selected rows
    let selectedRows = $derived(
        Object.keys(rowSelection)
            .filter(id => rowSelection[id])
            .map(id => data.find(row => getRowId(row) === id))
            .filter((r): r is T => r !== undefined)
    );

    // Check if all rows on current page are selected
    let isAllPageSelected = $derived.by(() => {
        if (paginatedData.length === 0) return false;
        return paginatedData.every(row => rowSelection[getRowId(row)]);
    });

    let isSomePageSelected = $derived(
        paginatedData.some(row => rowSelection[getRowId(row)]) && !isAllPageSelected
    );

    // Total pages
    let totalPages = $derived(Math.ceil(filteredData.length / pagination.pageSize));

    // ============ Helper Functions ============

    function extractRawValue(cell: CellContent): unknown {
        if (typeof cell !== 'object' || cell === null) return cell;
        if (!('type' in cell)) return cell;

        switch (cell.type) {
            case 'icon-text':
                return cell.text;
            case 'badge':
                return cell.text;
            case 'date':
                return new Date(cell.value);
            case 'size':
                return cell.bytes;
            case 'link':
                return cell.text;
            case 'editable-number':
                return cell.value;
            case 'editable-text':
                return cell.value;
            case 'editable-select':
                return cell.value;
            case 'editable-checkbox':
                return cell.value;
            case 'html':
                // Strip HTML tags for sorting
                return cell.html.replace(/<[^>]*>/g, '');
            default:
                return String(cell);
        }
    }

    // Calculate min/max values for a column (used for number/size filters)
    function getColumnMinMax(column: ColumnDef<T>): { min: number; max: number } {
        let min = Infinity;
        let max = -Infinity;

        for (const row of data) {
            const getValue = column.getValue ?? column.cell;
            const cellValue = getValue(row);
            let numValue: number;

            if (typeof cellValue === 'object' && cellValue !== null && 'type' in cellValue) {
                const typed = cellValue as unknown as { type: string; bytes?: number };
                if (typed.type === 'size' && typeof typed.bytes === 'number') {
                    numValue = typed.bytes;
                } else {
                    numValue = Number(extractRawValue(cellValue as CellContent));
                }
            } else {
                numValue = Number(cellValue);
            }

            if (!isNaN(numValue) && isFinite(numValue)) {
                min = Math.min(min, numValue);
                max = Math.max(max, numValue);
            }
        }

        // If no valid values, use sensible defaults
        if (min === Infinity) min = 0;
        if (max === -Infinity) max = min + 1;

        // Ensure min < max
        if (min >= max) max = min + 1;

        return {min, max};
    }


    function formatDate(value: Date | string, format?: string): string {
        const date = value instanceof Date ? value : new Date(value);
        if (format === 'time') {
            return date.toLocaleTimeString();
        } else if (format === 'datetime') {
            return date.toLocaleString(undefined, {
                year: 'numeric', month: 'short', day: 'numeric',
                hour: '2-digit', minute: '2-digit'
            });
        } else if (format === 'relative') {
            const now = new Date();
            const diff = now.getTime() - date.getTime();
            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            if (days === 0) return $t('date.today') || 'Today';
            if (days === 1) return $t('date.yesterday') || 'Yesterday';
            if (days < 7) return `${days}d ago`;
            return date.toLocaleDateString();
        }
        return date.toLocaleDateString(undefined, {year: 'numeric', month: 'short', day: 'numeric'});
    }

    function getColumnLabel(col: ColumnDef<T>): string {
        return typeof col.header === 'function' ? col.header() : col.header;
    }

    function getColumnTooltip(col: ColumnDef<T>): string | null {
        if (!col.headerTooltip) return null;
        return typeof col.headerTooltip === 'function' ? col.headerTooltip() : col.headerTooltip;
    }

    function getColumnTooltipUrl(col: ColumnDef<T>): string | null {
        if (!col.headerTooltipUrl) return null;
        return typeof col.headerTooltipUrl === 'function' ? col.headerTooltipUrl() : col.headerTooltipUrl;
    }

    /** Handle image load error — hide image and show fallback */
    function handleImageError(e: Event) {
        const img = e.currentTarget as HTMLImageElement;
        img.style.display = 'none';
        img.nextElementSibling?.classList.remove('hidden');
    }

    // ============ Actions ============

    function toggleSort(columnId: string) {
        if (!enableSorting) return;
        const column = columns.find(c => c.id === columnId);
        if (!column || column.sortable === false) return;

        if (sortState?.columnId === columnId) {
            if (sortState.direction === 'asc') {
                sortState = {columnId, direction: 'desc'};
            } else {
                sortState = null;
            }
        } else {
            sortState = {columnId, direction: 'asc'};
        }
    }

    function toggleAllPageRows() {
        const selectableRows = isRowSelectable
            ? paginatedData.filter(row => isRowSelectable!(row))
            : paginatedData;
        if (isAllPageSelected) {
            // Deselect all on current page
            const newSelection = {...rowSelection};
            selectableRows.forEach(row => delete newSelection[getRowId(row)]);
            rowSelection = newSelection;
        } else {
            // Select all on current page (clear previous selection)
            const newSelection: SelectionState = {};
            selectableRows.forEach(row => newSelection[getRowId(row)] = true);
            rowSelection = newSelection;
        }
        onSelectionChange?.(Object.keys(rowSelection).filter(id => rowSelection[id]));
    }

    function toggleRowSelection(rowId: string) {
        if (effectiveSelectionMode === 'single') {
            // Single select: toggle or replace
            const wasSelected = rowSelection[rowId];
            rowSelection = wasSelected ? {} : {[rowId]: true};
        } else {
            // Multi select: toggle individual
            const newSelection = {...rowSelection};
            if (newSelection[rowId]) {
                delete newSelection[rowId];
            } else {
                newSelection[rowId] = true;
            }
            rowSelection = newSelection;
        }
        onSelectionChange?.(Object.keys(rowSelection).filter(id => rowSelection[id]));
    }

    // Sync external selectedRowId prop (for single mode controlled by parent)
    $effect(() => {
        if (effectiveSelectionMode === 'single' && selectedRowId !== undefined && selectedRowId !== null) {
            const currentSelected = Object.keys(rowSelection).find(id => rowSelection[id]);
            if (currentSelected !== selectedRowId) {
                rowSelection = {[selectedRowId]: true};
            }
        }
    });

    // Auto-deactivate "show selected only" when selection becomes empty
    $effect(() => {
        const selectedCount = Object.keys(rowSelection).filter(id => rowSelection[id]).length;
        if (selectedCount === 0 && showSelectedOnly) {
            showSelectedOnly = false;
        }
    });

    function handleRowClick(row: T) {
        if (effectiveSelectionMode === 'single') {
            toggleRowSelection(getRowId(row));
        }
        onRowClick?.(row);
    }

    function handleRowDoubleClick(row: T) {
        onRowDoubleClick?.(row);
    }

    function clearAllSelection() {
        rowSelection = {};
        onSelectionChange?.([]);
    }

    function handleBulkAction(action: BulkAction<T>) {
        if (action.requireConfirm) {
            pendingBulkAction = action;
            showDeleteModal = true;
        } else {
            action.onClick(selectedRows);
        }
    }

    function confirmBulkAction() {
        if (pendingBulkAction) {
            pendingBulkAction.onClick(selectedRows);
            rowSelection = {};
            onSelectionChange?.([]);
        }
        showDeleteModal = false;
        pendingBulkAction = null;
    }

    function cancelBulkAction() {
        showDeleteModal = false;
        pendingBulkAction = null;
    }

    // Row action handlers
    function handleRowAction(action: RowAction<T>, row: T) {
        if (action.requireConfirm) {
            pendingRowAction = {action, row};
            showRowActionModal = true;
        } else {
            action.onClick(row);
        }
    }

    function confirmRowAction() {
        if (pendingRowAction) {
            pendingRowAction.action.onClick(pendingRowAction.row);
        }
        showRowActionModal = false;
        pendingRowAction = null;
    }

    function cancelRowAction() {
        showRowActionModal = false;
        pendingRowAction = null;
    }

    function handlePageChange(pageIndex: number) {
        pagination = {...pagination, pageIndex};
    }

    function handlePageSizeChange(pageSize: number) {
        pagination = {pageIndex: 0, pageSize};
        saveToStorage(getStorageKey('pageSize'), pageSize >= 999999 ? 0 : pageSize);
    }

    function toggleColumnVisibility(columnId: string) {
        columnVisibility = {...columnVisibility, [columnId]: !columnVisibility[columnId]};
        saveToStorage(getStorageKey('columnVisibility'), columnVisibility);
    }

    function resetColumns() {
        columnVisibility = {...defaultColumnVisibility};
        columnWidths = {...defaultColumnWidths};
        columnOrder = [...defaultColumnOrder];
        columnFilters = {};
        saveToStorage(getStorageKey('columnVisibility'), defaultColumnVisibility);
        saveToStorage(getStorageKey('columnWidths'), defaultColumnWidths);
        saveToStorage(getStorageKey('columnOrder'), defaultColumnOrder);
    }

    function reorderColumns(newOrder: string[]) {
        columnOrder = newOrder;
        saveToStorage(getStorageKey('columnOrder'), newOrder);
    }

    function applyColumnFilter(columnId: string, filter: FilterValue | null) {
        if (filter) {
            columnFilters = {...columnFilters, [columnId]: filter};
        } else {
            const {[columnId]: _, ...rest} = columnFilters;
            columnFilters = rest;
        }
        // Don't close the filter popover here - let the user close it manually
        // or by clicking outside
        pagination = {...pagination, pageIndex: 0};
    }

    // ============ Resize ============

    function startResize(columnId: string, event: MouseEvent) {
        event.preventDefault();
        event.stopPropagation();
        resizing = {
            columnId,
            startX: event.clientX,
            startWidth: columnWidths[columnId] || columns.find(c => c.id === columnId)?.width || 150,
        };
        document.addEventListener('mousemove', handleResize);
        document.addEventListener('mouseup', stopResize);
    }

    function handleResize(event: MouseEvent) {
        if (!resizing) return;
        const col = columns.find(c => c.id === resizing!.columnId);
        const minWidth = col?.minWidth ?? 50;
        const maxWidth = col?.maxWidth ?? 600;
        const diff = event.clientX - resizing.startX;
        const newWidth = Math.min(maxWidth, Math.max(minWidth, resizing.startWidth + diff));
        columnWidths = {...columnWidths, [resizing.columnId]: newWidth};
    }

    function stopResize() {
        if (resizing) {
            saveToStorage(getStorageKey('columnWidths'), columnWidths);
        }
        resizing = null;
        document.removeEventListener('mousemove', handleResize);
        document.removeEventListener('mouseup', stopResize);
    }

    // ============ Lifecycle ============

    onMount(() => {
        // Load preferences
        const storedPageSize = loadFromStorage<number>(getStorageKey('pageSize'), defaultPageSize);
        pagination = {...pagination, pageSize: storedPageSize === 0 ? 999999 : storedPageSize};

        const storedVisibility = loadFromStorage<VisibilityState | null>(getStorageKey('columnVisibility'), null);
        if (storedVisibility) {
            // Merge: apply stored state, but force hiddenByDefault for columns not previously known
            const merged = {...defaultColumnVisibility};
            for (const [id, visible] of Object.entries(storedVisibility)) {
                if (id in merged) merged[id] = visible;
            }
            // Force-hide columns with hiddenByDefault that weren't in the stored state
            for (const col of columns) {
                if (col.hiddenByDefault && !(col.id in storedVisibility)) {
                    merged[col.id] = false;
                }
            }
            columnVisibility = merged;
        } else {
            columnVisibility = {...defaultColumnVisibility};
        }

        columnWidths = loadFromStorage(getStorageKey('columnWidths'), defaultColumnWidths);
        columnOrder = loadFromStorage(getStorageKey('columnOrder'), defaultColumnOrder);

        // Apply initial filters from URL (if provided)
        if (initialFilters && Object.keys(initialFilters).length > 0) {
            // Map URL keys to column IDs
            const filtersByColumnId: Record<string, FilterValue> = {};
            for (const [urlKey, value] of Object.entries(initialFilters)) {
                // Find column by urlKey or id
                const col = columns.find(c => (c.urlKey ?? c.id) === urlKey);
                if (col) {
                    filtersByColumnId[col.id] = value;
                }
            }
            columnFilters = filtersByColumnId;
        }
    });

    // Notify parent when filters change (for URL sync)
    $effect(() => {
        // Only call if handler provided and we have some filter activity
        if (onFiltersChange) {
            // Build filters with URL keys
            const filtersWithUrlKeys: Record<string, FilterValue> = {};
            for (const [columnId, value] of Object.entries(columnFilters)) {
                if (!value) continue;
                const col = columns.find(c => c.id === columnId);
                const urlKey = col?.urlKey ?? columnId;
                filtersWithUrlKeys[urlKey] = value;
            }
            onFiltersChange(filtersWithUrlKeys);
        }
    });

    // Sync column order/visibility/widths when columns change dynamically
    // (e.g. delta period columns added/removed when date range changes)
    $effect(() => {
        const currentIds = new Set(columns.map(c => c.id));
        const orderedIds = new Set(columnOrder);

        // Detect new columns (not in current order)
        const newIds = columns.filter(c => !orderedIds.has(c.id)).map(c => c.id);
        // Remove stale columns (no longer in definition)
        const filtered = columnOrder.filter(id => currentIds.has(id));

        if (newIds.length > 0 || filtered.length !== columnOrder.length) {
            // Insert new columns at their correct position based on the columns array order
            // (not appended at end). This ensures delta columns stay grouped and ordered.
            for (const newId of newIds) {
                const colIndex = columns.findIndex(c => c.id === newId);
                // Find the last column in filtered that precedes newId in columns order
                let insertAfterIdx = -1;
                for (let i = 0; i < filtered.length; i++) {
                    const existingColIdx = columns.findIndex(c => c.id === filtered[i]);
                    if (existingColIdx !== -1 && existingColIdx < colIndex) insertAfterIdx = i;
                }
                filtered.splice(insertAfterIdx + 1, 0, newId);
            }
            columnOrder = filtered;
            saveToStorage(getStorageKey('columnOrder'), columnOrder);

            // Set visibility for new columns (respect hiddenByDefault)
            const updatedVisibility = {...columnVisibility};
            for (const id of newIds) {
                const col = columns.find(c => c.id === id);
                updatedVisibility[id] = col ? !col.hiddenByDefault : true;
            }
            // Remove stale visibility entries
            for (const id of Object.keys(updatedVisibility)) {
                if (!currentIds.has(id)) delete updatedVisibility[id];
            }
            columnVisibility = updatedVisibility;
            saveToStorage(getStorageKey('columnVisibility'), columnVisibility);

            // Update widths for new columns
            const updatedWidths = {...columnWidths};
            for (const id of newIds) {
                const col = columns.find(c => c.id === id);
                updatedWidths[id] = col?.width ?? 150;
            }
            for (const id of Object.keys(updatedWidths)) {
                if (!currentIds.has(id)) delete updatedWidths[id];
            }
            columnWidths = updatedWidths;
        }

        // Initial fallback (first mount before localStorage loads)
        if (columnOrder.length === 0) {
            columnOrder = [...defaultColumnOrder];
        }
        if (Object.keys(columnVisibility).length === 0) {
            columnVisibility = {...defaultColumnVisibility};
        }
        if (Object.keys(columnWidths).length === 0) {
            columnWidths = {...defaultColumnWidths};
        }
    });

    // ============ Public API ============

    /**
     * Navigate to the page containing the row with the given ID, then scroll it into view.
     * Reusable: called from DataEditor's "Add Row", chart point click, etc.
     */
    export function navigateToRowId(rowId: string) {
        const index = sortedData.findIndex(row => getRowId(row) === rowId);
        if (index < 0) return;
        if (enablePagination) {
            const targetPage = Math.floor(index / pagination.pageSize);
            if (pagination.pageIndex !== targetPage) {
                pagination = {...pagination, pageIndex: targetPage};
            }
        }
        // Set highlight — will be cleared on user interaction
        highlightedRowId = rowId;
        // After pagination update, scroll to the row
        import('svelte').then(({tick}) => tick()).then(() => {
            // Find the row in the visible table by scanning for matching row ID
            const rows = document.querySelectorAll('.datatable tbody tr');
            const positionInPage = enablePagination ? index % pagination.pageSize : index;
            const targetRow = rows[positionInPage];
            targetRow?.scrollIntoView({behavior: 'smooth', block: 'center'});
        });
    }

    /** Get ordered columns info for external visibility control */
    export function getColumnsForVisibility(): Array<{ id: string; header: string | (() => string); visible: boolean }> {
        return orderedColumns.map(c => ({id: c.id, header: c.header, visible: columnVisibility[c.id] !== false}));
    }

    /** Toggle a column's visibility (external access) */
    export function toggleColumnVisibilityById(columnId: string) {
        toggleColumnVisibility(columnId);
    }

    /** Get ordered column IDs */
    export function getColumnOrder(): string[] {
        return [...columnOrder];
    }

    /** Set column order (reorder columns) */
    export function setColumnOrder(newOrder: string[]) {
        reorderColumns(newOrder);
    }

    /** Reset column visibility, order and widths to defaults */
    export function resetColumnLayout() {
        resetColumns();
    }

    /** Clear all selected rows (external access) */
    export function clearSelection() {
        clearAllSelection();
    }

    /** Get currently selected rows (for external toolbar) */
    export function getSelectedRows(): T[] {
        return selectedRows;
    }

    /** Execute a bulk action by ID (triggers confirm modal if required) */
    export function executeBulkAction(actionId: string) {
        const action = bulkActions.find(a => a.id === actionId);
        if (action) handleBulkAction(action);
    }
</script>

<div class="datatable-container">
    <!-- Table -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="table-wrapper" onkeydown={() => { highlightedRowId = null; }}>
        <table class="datatable {tableLayout === 'auto' ? 'layout-auto' : ''}">
            <thead>
            <tr>
                <!-- Selection column (multi mode: checkboxes, single mode: no column header) -->
                {#if effectiveSelectionMode === 'multi'}
                    <th class="th-fixed th-select" style="width: {selectionColumnWidth};">
                        <div class="flex items-center gap-1">
                            <button type="button" class="checkbox-btn" onclick={toggleAllPageRows}>
                                {#if isAllPageSelected}
                                    <Check size={16} class="check-icon checked"/>
                                {:else if isSomePageSelected}
                                    <Check size={16} class="check-icon partial"/>
                                {:else}
                                    <span class="check-box"></span>
                                {/if}
                            </button>
                            <button
                                    type="button"
                                    class="filter-btn"
                                    class:active={showSelectedOnly}
                                    onclick={() => { showSelectedOnly = !showSelectedOnly; }}
                                    title="Show selected only"
                            >
                                <Filter size={12}/>
                            </button>
                        </div>
                    </th>
                {/if}

                <!-- Data columns -->
                {#each visibleColumns as column}
                    {@const isSorted = sortState?.columnId === column.id}
                    {@const sortDir = isSorted ? sortState?.direction : null}
                    {@const hasFilter = columnFilters[column.id] !== undefined}
                    <th
                            class="th-data"
                            class:sortable={column.sortable !== false && enableSorting}
                            style="width: {columnWidths[column.id] || column.width || 150}px; min-width: {column.minWidth || 60}px;"
                    >
                        <div class="header-content">
                            <button
                                    type="button"
                                    class="header-sort-btn"
                                    onclick={() => toggleSort(column.id)}
                                    disabled={column.sortable === false || !enableSorting}
                            >
                                <span class="header-text">{getColumnLabel(column)}</span>
                                {#if column.sortable !== false && enableSorting}
										<span class="sort-icon">
											{#if sortDir === 'asc'}
												<ChevronUp size={14}/>
											{:else if sortDir === 'desc'}
												<ChevronDown size={14}/>
											{:else}
												<ChevronsUpDown size={14}/>
											{/if}
										</span>
                                {/if}
                            </button>

                            <!-- Header tooltip (info icon) -->
                            {#if getColumnTooltip(column)}
                                {@const tooltipText = getColumnTooltip(column) ?? ''}
                                {@const tooltipUrl = getColumnTooltipUrl(column)}
                                <Tooltip text={tooltipText} position="bottom" math={tooltipText.includes('$')}>
                                    {#if tooltipUrl}
                                        <a href={tooltipUrl} target="_blank" rel="noopener noreferrer"
                                           class="header-tooltip-icon header-tooltip-link"
                                           onclick={(e) => e.stopPropagation()}>
                                            <Info size={12}/>
                                        </a>
                                    {:else}
                                        <span class="header-tooltip-icon">
                                            <Info size={12}/>
                                        </span>
                                    {/if}
                                </Tooltip>
                            {/if}

                            <!-- Filter button -->
                            {#if column.filterable !== false && enableColumnFilters}
                                <button
                                        bind:this={filterBtnRefs[column.id]}
                                        type="button"
                                        class="filter-btn"
                                        class:active={hasFilter}
                                        onclick={() => openFilterColumnId = openFilterColumnId === column.id ? null : column.id}
                                >
                                    <Filter size={12}/>
                                </button>
                            {/if}

                            <!-- Resize handle -->
                            {#if column.resizable !== false && enableColumnResize}
                                <!-- svelte-ignore a11y_no_static_element_interactions -->
                                <span
                                        class="resize-handle"
                                        class:resizing={resizing?.columnId === column.id}
                                        onmousedown={(e) => startResize(column.id, e)}
                                ></span>
                            {/if}

                            <!-- Filter popover -->
                            {#if openFilterColumnId === column.id}
                                {@const minMax = (column.type === 'number' || column.type === 'size') ? getColumnMinMax(column) : {min: 0, max: 100}}
                                <DataTableColumnFilter
                                        type={column.type}
                                        enumOptions={column.enumOptions}
                                        numberMin={minMax.min}
                                        numberMax={minMax.max}
                                        initialValue={columnFilters[column.id]}
                                        onApply={(filter) => applyColumnFilter(column.id, filter)}
                                        onClose={() => openFilterColumnId = null}
                                        anchorElement={filterBtnRefs[column.id] ?? null}
                                />
                            {/if}
                        </div>
                    </th>
                {/each}

                <!-- Actions column -->
                {#if enableActions && rowActions.length > 0}
                    <th class="th-fixed th-actions" style="width: {actionsColumnWidth};">
                        {$t('table.actions') || 'Actions'}
                    </th>
                {/if}
            </tr>
            </thead>
            <tbody>
            {#if isLoading}
                <tr>
                    <td
                            colspan={visibleColumns.length + (effectiveSelectionMode === 'multi' ? 1 : 0) + (enableActions ? 1 : 0)}
                            class="td-loading"
                    >
                        <div class="loading-spinner"></div>
                        <span>{$t('common.loading') || 'Loading...'}</span>
                    </td>
                </tr>
            {:else if paginatedData.length === 0}
                <tr>
                    <td
                            colspan={visibleColumns.length + (effectiveSelectionMode === 'multi' ? 1 : 0) + (enableActions ? 1 : 0)}
                            class="td-empty"
                    >
                        {emptyMessage || $t('common.noData') || 'No data available'}
                    </td>
                </tr>
            {:else}
                {#each paginatedData as row}
                    {@const rowId = getRowId(row)}
                    {@const isSelected = rowSelection[rowId]}
                    <tr class="{isSelected ? 'selected' : ''} {effectiveSelectionMode === 'single' || onRowClick ? 'clickable' : ''} {rowId === highlightedRowId ? 'highlighted' : ''} {getRowClass?.(row) ?? ''}"
                        style={getRowStyle?.(row) ?? ''}
                        onclick={() => { if (isRowSelectable && !isRowSelectable(row)) return; highlightedRowId = null; handleRowClick(row); }}
                        ondblclick={() => { if (isRowSelectable && !isRowSelectable(row)) return; handleRowDoubleClick(row); }}
                    >
                        <!-- Selection cell (multi mode only - shows checkboxes) -->
                        {#if effectiveSelectionMode === 'multi'}
                            <td class="td-fixed td-select">
                                {#if !isRowSelectable || isRowSelectable(row)}
                                <button
                                        type="button"
                                        class="checkbox-btn"
                                        onclick={(e) => { e.stopPropagation(); toggleRowSelection(rowId); }}
                                >
                                    {#if isSelected}
                                        <Check size={16} class="check-icon checked"/>
                                    {:else}
                                        <span class="check-box"></span>
                                    {/if}
                                </button>
                                {:else}
                                <div style="width:28px"></div>
                                {/if}
                            </td>
                        {/if}

                        <!-- Data cells -->
                        {#each visibleColumns as column}
                            {@const cellContent = column.cell(row)}
                            <td class="td-data">
                                {#if typeof cellContent === 'string' || typeof cellContent === 'number'}
                                    {cellContent}
                                {:else if cellContent && typeof cellContent === 'object' && 'type' in cellContent}
                                    {#if cellContent.type === 'icon-text'}
                                        <div class="cell-icon-text">
                                            <div class="cell-icon-box">
                                                <cellContent.icon size={16} class={cellContent.iconClass || ''}/>
                                            </div>
                                            <span>{cellContent.text}</span>
                                        </div>
                                    {:else if cellContent.type === 'badge'}
											<span
                                                    class="cell-badge {cellContent.variant}"
                                                    class:custom-style={cellContent.customStyle}
                                                    style={cellContent.customStyle || undefined}
                                            >{cellContent.text}</span>
                                    {:else if cellContent.type === 'date'}
                                        {formatDate(cellContent.value, cellContent.format)}
                                    {:else if cellContent.type === 'size'}
                                        {formatBytes(cellContent.bytes)}
                                    {:else if cellContent.type === 'link'}
                                        <a
                                                href={cellContent.href}
                                                class="cell-link"
                                                target={cellContent.external ? '_blank' : undefined}
                                                rel={cellContent.external ? 'noopener noreferrer' : undefined}
                                        >
                                            {cellContent.text}
                                            {#if cellContent.external}
                                                <ExternalLink size={12}/>
                                            {/if}
                                        </a>
                                    {:else if cellContent.type === 'custom'}
                                        {@const CustomComponent = cellContent.component}
                                        <CustomComponent {...cellContent.props}/>
                                    {:else if cellContent.type === 'image'}
                                        <div class="cell-image-text">
                                            <div class="cell-image" class:circle={cellContent.circle}
                                                 style="width:{cellContent.size || 32}px;height:{cellContent.size || 32}px;">
                                                <img
                                                        src={cellContent.src}
                                                        alt={cellContent.alt}
                                                        width={cellContent.size || 32}
                                                        height={cellContent.size || 32}
                                                        loading="lazy"
                                                        onerror={handleImageError}
                                                />
                                                <span class="image-fallback hidden">
                                                    {#if cellContent.fallbackIcon}
                                                        {@const FallbackIcon = cellContent.fallbackIcon}
                                                        <FallbackIcon size={cellContent.size ? cellContent.size * 0.6 : 20}/>
                                                    {:else}
                                                        <ImageIcon size={cellContent.size ? cellContent.size * 0.6 : 20}/>
                                                    {/if}
                                                </span>
                                            </div>
                                            {#if cellContent.text}
                                                <span class="cell-image-label">{cellContent.text}</span>
                                            {/if}
                                        </div>
                                    {:else if cellContent.type === 'editable-number'}
                                        <input
                                                type="number"
                                                class="cell-editable-number"
                                                value={cellContent.value ?? ''}
                                                step={cellContent.step ?? 1}
                                                min={cellContent.min}
                                                max={cellContent.max}
                                                placeholder={cellContent.placeholder ?? ''}
                                                oninput={(e) => {
                                                const raw = e.currentTarget.value;
                                                if (raw === '') { cellContent.onchange(null); return; }
                                                let num = Number(raw);
                                                if (cellContent.min !== undefined && num < cellContent.min) num = cellContent.min;
                                                if (cellContent.max !== undefined && num > cellContent.max) num = cellContent.max;
                                                cellContent.onchange(num);
                                            }}
                                                onblur={(e) => {
                                                const raw = e.currentTarget.value;
                                                if (raw === '') { cellContent.onchange(null); return; }
                                                let num = Number(raw);
                                                if (cellContent.min !== undefined && num < cellContent.min) {
                                                    num = cellContent.min;
                                                    e.currentTarget.value = String(num);
                                                }
                                                if (cellContent.max !== undefined && num > cellContent.max) {
                                                    num = cellContent.max;
                                                    e.currentTarget.value = String(num);
                                                }
                                                cellContent.onchange(num);
                                            }}
                                                onkeydown={(e) => {
                                                if (e.key === 'Enter') e.currentTarget.blur();
                                            }}
                                                onclick={(e) => e.stopPropagation()}
                                        />
                                    {:else if cellContent.type === 'editable-text'}
                                        <input
                                                type="text"
                                                class="cell-editable-text"
                                                value={cellContent.value}
                                                placeholder={cellContent.placeholder ?? ''}
                                                maxlength={cellContent.maxLength}
                                                onblur={(e) => cellContent.onchange(e.currentTarget.value)}
                                                onkeydown={(e) => {
                                                if (e.key === 'Enter') e.currentTarget.blur();
                                            }}
                                                onclick={(e) => e.stopPropagation()}
                                        />
                                    {:else if cellContent.type === 'editable-select'}
                                        <!-- svelte-ignore a11y_click_events_have_key_events -->
                                        <!-- svelte-ignore a11y_no_static_element_interactions -->
                                        <div class="cell-editable-select-wrapper" onclick={(e) => e.stopPropagation()}>
                                            <SimpleSelect
                                                    value={cellContent.value}
                                                    options={cellContent.options}
                                                    compact
                                                    showChevron={false}
                                                    dropdownPosition="auto"
                                                    onchange={(v) => cellContent.onchange(v)}
                                            />
                                        </div>
                                    {:else if cellContent.type === 'editable-checkbox'}
                                        <!-- svelte-ignore a11y_click_events_have_key_events -->
                                        <!-- svelte-ignore a11y_no_static_element_interactions -->
                                        <div class="cell-checkbox-wrapper flex justify-center" onclick={(e) => e.stopPropagation()}>
                                            <button
                                                    type="button"
                                                    onclick={() => cellContent.onchange(!cellContent.value)}
                                                    aria-label="Toggle"
                                                    class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors
                                                           {cellContent.value ? 'bg-emerald-500' : 'bg-gray-300 dark:bg-slate-600'}
                                                           cursor-pointer"
                                                    aria-pressed={cellContent.value}
                                            >
                                                <span class="inline-block h-3.5 w-3.5 rounded-full bg-white shadow-sm transition-transform
                                                             {cellContent.value ? 'translate-x-[18px]' : 'translate-x-[3px]'}"></span>
                                            </button>
                                        </div>
                                    {:else if cellContent.type === 'html'}
                                        {@html cellContent.html}
                                    {/if}
                                {/if}
                            </td>
                        {/each}

                        <!-- Actions cell -->
                        {#if enableActions && rowActions.length > 0}
                            <td class="td-fixed td-actions">
                                <div class="actions-row">
                                    {#each rowActions as action}
                                        {#if !action.visible || action.visible(row)}
                                            <button
                                                    type="button"
                                                    class="action-btn"
                                                    class:danger={action.variant === 'danger'}
                                                    disabled={action.disabled?.(row)}
                                                    onclick={(e) => { e.stopPropagation(); handleRowAction(action, row); }}
                                                    title={typeof action.label === 'function' ? action.label() : action.label}
                                            >
                                                <action.icon size={16} class={action.iconClass?.(row) ?? ''}/>
                                            </button>
                                        {/if}
                                    {/each}
                                </div>
                            </td>
                        {/if}
                    </tr>
                {/each}
            {/if}
            </tbody>
        </table>
    </div>

    <!-- Pagination - show only when enabled and items exceed smallest page size -->
    {#if enablePagination && filteredData.length > 0 && filteredData.length > Math.min(...pageSizeOptions.filter(x => x > 0))}
        <DataTablePagination
                pageIndex={pagination.pageIndex}
                pageSize={pagination.pageSize}
                totalItems={filteredData.length}
                {pageSizeOptions}
                onPageChange={handlePageChange}
                onPageSizeChange={handlePageSizeChange}
        />
    {/if}
</div>

<!-- Confirm modal for bulk actions -->
<ConfirmModal
        danger={pendingBulkAction?.variant === 'danger'}
        items={selectedRows.map(row => getRowDisplayName ? getRowDisplayName(row) : String(getRowId(row)))}
        itemsLabel={`${selectedRows.length} ${$t('table.items')}`}
        message={pendingBulkAction?.confirmMessage
		? (typeof pendingBulkAction.confirmMessage === 'function'
			? pendingBulkAction.confirmMessage(selectedRows.length)
			: pendingBulkAction.confirmMessage)
		: `${$t('table.confirmBulkAction')} ${selectedRows.length} ${$t('table.items')}?`}
        onCancel={cancelBulkAction}
        onConfirm={confirmBulkAction}
        open={showDeleteModal}
        title={$t('common.confirm')}
/>

<!-- Confirm modal for single row actions -->
<ConfirmModal
        danger={pendingRowAction?.action.variant === 'danger'}
        items={pendingRowAction ? [getRowDisplayName ? getRowDisplayName(pendingRowAction.row) : String(getRowId(pendingRowAction.row))] : []}
        message={pendingRowAction?.action.confirmMessage
		? (typeof pendingRowAction.action.confirmMessage === 'function'
			? pendingRowAction.action.confirmMessage(pendingRowAction.row)
			: pendingRowAction.action.confirmMessage)
		: $t('common.confirmDelete')}
        onCancel={cancelRowAction}
        onConfirm={confirmRowAction}
        open={showRowActionModal}
        title={$t('common.confirm')}
/>

<style>
    .datatable-container {
        width: 100%;
        position: relative;
    }

    .table-wrapper {
        overflow-x: auto;
        overflow-y: visible;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        background: white;
    }

    :global(.dark) .table-wrapper {
        border-color: #334155;
        background: #0f172a;
    }

    .datatable {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
        background: white;
    }

    .datatable.layout-auto {
        table-layout: auto;
    }

    :global(.dark) .datatable {
        background: #0f172a;
    }

    /* Header */
    thead {
        background: #f8fafc;
    }

    :global(.dark) thead {
        background: #1e293b;
    }

    th {
        padding: 0.5rem 0.5rem;
        text-align: left;
        font-size: 0.75rem;
        font-weight: 600;
        color: #64748b;
        border-bottom: 1px solid #e2e8f0;
        white-space: nowrap;
        position: relative;
        text-transform: uppercase;
        letter-spacing: 0.025em;
    }

    :global(.dark) th {
        color: #94a3b8;
        border-bottom-color: #334155;
    }

    .th-fixed {
        position: sticky;
        z-index: 10;
        background: #f8fafc;
    }

    :global(.dark) .th-fixed {
        background: #1e293b;
    }

    .th-select {
        left: 0;
        text-align: center;
    }

    .th-actions {
        right: 0;
        text-align: center;
        text-transform: none !important;
    }

    .th-data.sortable {
        cursor: pointer;
    }

    .th-data.sortable:hover {
        background: #f1f5f9;
    }

    :global(.dark) .th-data.sortable:hover {
        background: #334155;
    }

    .header-content {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    .header-sort-btn {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        background: none;
        border: none;
        padding: 0;
        color: inherit;
        font: inherit;
        cursor: pointer;
    }

    .header-sort-btn:disabled {
        cursor: default;
    }

    .sort-icon {
        display: flex;
        color: #94a3b8;
    }

    .header-tooltip-icon {
        display: flex;
        align-items: center;
        color: #94a3b8;
        cursor: pointer;
        flex-shrink: 0;
    }

    :global(.dark) .header-tooltip-icon {
        color: #64748b;
    }

    .header-tooltip-link {
        text-decoration: none;
        transition: color 0.15s;
    }

    .header-tooltip-link:hover {
        color: #1a4031;
    }

    :global(.dark) .header-tooltip-link:hover {
        color: #4ade80;
    }

    .filter-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 20px;
        height: 20px;
        border: none;
        border-radius: 4px;
        background: transparent;
        color: #94a3b8;
        cursor: pointer;
        transition: all 0.15s;
    }

    .filter-btn:hover {
        background: #e2e8f0;
        color: #475569;
    }

    .filter-btn.active {
        background: #1a4031;
        color: white;
    }

    :global(.dark) .filter-btn:hover {
        background: #475569;
        color: #f1f5f9;
    }

    :global(.dark) .filter-btn.active {
        background: #4ade80;
        color: #0f172a;
    }

    .resize-handle {
        position: absolute;
        right: 0;
        top: 0;
        bottom: 0;
        width: 6px;
        background: transparent;
        cursor: col-resize;
        opacity: 0;
        transition: opacity 0.15s;
        z-index: 5;
    }

    th:hover .resize-handle {
        opacity: 1;
        background: #cbd5e1;
    }

    .resize-handle.resizing, .resize-handle:active {
        opacity: 1;
        background: #1a4031;
    }

    :global(.dark) th:hover .resize-handle {
        background: #475569;
    }

    :global(.dark) .resize-handle.resizing {
        background: #4ade80;
    }

    /* Body */
    tbody tr {
        background: white;
        transition: background 0.15s;
    }

    :global(.dark) tbody tr {
        background: #0f172a;
    }

    tbody tr:hover {
        background: #f8fafc;
    }

    :global(.dark) tbody tr:hover {
        background: #1e293b;
    }

    tbody :global(tr.selected) {
        background: #eff6ff;
    }

    :global(.dark) tbody :global(tr.selected) {
        background: #1e3a5f;
    }

    tbody :global(tr.clickable) {
        cursor: pointer;
    }

    tbody :global(tr.clickable):hover {
        background: #f0fdf4;
    }

    :global(.dark) tbody :global(tr.clickable):hover {
        background: #1a2e35;
    }

    tbody :global(tr.clickable.selected) {
        background: #dcfce7;
    }

    :global(.dark) tbody :global(tr.clickable.selected) {
        background: #14532d;
    }

    /* Highlighted row (navigateToRowId) — purple, highest priority */
    tbody :global(tr.highlighted) {
        background: #f3e8ff !important;
    }

    tbody :global(tr.highlighted):hover {
        background: #f3e8ff !important;
    }

    :global(.dark) tbody :global(tr.highlighted) {
        background: rgba(147, 51, 234, 0.25) !important;
    }

    :global(.dark) tbody :global(tr.highlighted):hover {
        background: rgba(147, 51, 234, 0.25) !important;
    }

    :global(tr.highlighted) td {
        border-bottom-color: #e9d5ff;
    }

    :global(.dark) :global(tr.highlighted) td {
        border-bottom-color: #7e22ce;
    }

    td {
        padding: 0.625rem 0.5rem;
        font-size: 0.875rem;
        color: #475569;
        border-bottom: 1px solid #f1f5f9;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 0;
    }

    :global(.dark) td {
        color: #e2e8f0;
        border-bottom-color: #1e293b;
    }

    .td-data {
        word-break: break-word;
    }

    /* Allow SimpleSelect dropdown to overflow outside td */
    td:has(.cell-editable-select-wrapper) {
        overflow: visible;
    }

    /* Ensure table rows with open SimpleSelect dropdown are on top */
    tbody tr:has(.cell-editable-select-wrapper) {
        position: relative;
        z-index: 1;
    }

    /* When dropdown is actually open (focus-within), bump z-index above sibling rows */
    tbody tr:focus-within {
        z-index: 10;
    }

    .td-fixed {
        position: sticky;
        z-index: 5;
        background: inherit;
    }

    .td-select {
        left: 0;
        text-align: center;
        max-width: none;
    }

    .td-actions {
        right: 0;
        max-width: none;
        white-space: normal;
    }

    .td-empty, .td-loading {
        text-align: center;
        padding: 3rem 2rem;
        color: #94a3b8;
        background: white;
        height: 230px;
        vertical-align: middle;
    }

    /* Image cell */
    .cell-image-text {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        min-width: 0;
    }

    .cell-image-label {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        min-width: 0;
        text-align: left;
    }

    .cell-image {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        border-radius: 0.25rem;
        background: #f1f5f9;
        flex-shrink: 0;
        /* Fixed size ensures text labels align in a column */
        min-width: 32px;
    }

    .cell-image.circle {
        border-radius: 50%;
    }

    .cell-image img {
        object-fit: cover;
        display: block;
    }

    .cell-image .image-fallback {
        display: flex;
        align-items: center;
        justify-content: center;
        color: #94a3b8;
    }

    .cell-image :global(.hidden) {
        display: none !important;
    }

    :global(.dark) .cell-image {
        background: #334155;
    }

    :global(.dark) .cell-image .image-fallback {
        color: #64748b;
    }

    :global(.dark) .td-empty, :global(.dark) .td-loading {
        background: #0f172a;
    }

    .loading-spinner {
        display: inline-block;
        width: 1.5rem;
        height: 1.5rem;
        border: 2px solid #e2e8f0;
        border-top-color: #1a4031;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
        margin-bottom: 0.5rem;
    }

    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }

    /* Checkbox */
    .checkbox-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        border: none;
        border-radius: 4px;
        background: transparent;
        cursor: pointer;
        margin: 0 auto;
    }

    .check-box {
        display: block;
        width: 16px;
        height: 16px;
        border: 1px solid #cbd5e1;
        border-radius: 3px;
        background: white;
    }

    :global(.dark) .check-box {
        background: #0f172a;
        border-color: #475569;
    }

    :global(.check-icon) {
        color: #1a4031;
    }

    :global(.check-icon.checked) {
        color: #1a4031;
    }

    :global(.check-icon.partial) {
        color: #94a3b8;
    }

    :global(.dark) :global(.check-icon.checked) {
        color: #4ade80;
    }

    /* Cell content types */
    .cell-icon-text {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        min-width: 0;
    }

    .cell-icon-text :global(svg) {
        flex-shrink: 0;
    }

    /* Fixed-size box for icon, matches .cell-image dimensions for column alignment */
    .cell-icon-box {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        width: 32px;
        height: 32px;
        min-width: 32px;
        color: #94a3b8;
    }

    :global(.dark) .cell-icon-box {
        color: #64748b;
    }

    .cell-icon-text span {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        min-width: 0;
        text-align: left;
    }

    .cell-badge {
        display: inline-block;
        padding: 0.125rem 0.5rem;
        font-size: 0.75rem;
        font-weight: 500;
        border-radius: 9999px;
    }

    .cell-badge.default {
        background: #f1f5f9;
        color: #475569;
    }

    .cell-badge.success {
        background: #dcfce7;
        color: #166534;
    }

    .cell-badge.warning {
        background: #fef3c7;
        color: #92400e;
    }

    .cell-badge.error {
        background: #fee2e2;
        color: #991b1b;
    }

    .cell-badge.info {
        background: #dbeafe;
        color: #1e40af;
    }

    :global(.dark) .cell-badge.default {
        background: #334155;
        color: #e2e8f0;
    }

    :global(.dark) .cell-badge.success {
        background: #14532d;
        color: #86efac;
    }

    :global(.dark) .cell-badge.warning {
        background: #78350f;
        color: #fde68a;
    }

    :global(.dark) .cell-badge.error {
        background: #7f1d1d;
        color: #fecaca;
    }

    :global(.dark) .cell-badge.info {
        background: #1e3a8a;
        color: #bfdbfe;
    }

    /* Custom styled badge (e.g., broker colors) */
    .cell-badge.custom-style {
        background: var(--broker-bg, #f1f5f9);
        color: var(--broker-text, #475569);
    }

    :global(.dark) .cell-badge.custom-style {
        background: var(--broker-dark-bg, #334155);
        color: var(--broker-dark-text, #e2e8f0);
    }

    .cell-link {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        color: #1a4031;
        text-decoration: none;
    }

    .cell-link:hover {
        text-decoration: underline;
    }

    :global(.dark) .cell-link {
        color: #4ade80;
    }

    /* Actions */
    .actions-row {
        display: flex;
        justify-content: center;
        gap: 0.375rem;
    }

    .action-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        background: #f8fafc;
        color: #64748b;
        cursor: pointer;
        transition: all 0.15s;
    }

    .action-btn:hover {
        background: #f1f5f9;
        border-color: #cbd5e1;
        color: #0f172a;
    }

    .action-btn.danger {
        color: #dc2626;
        border-color: #fecaca;
        background: #fef2f2;
    }

    .action-btn.danger:hover {
        background: #fee2e2;
        border-color: #fca5a5;
        color: #b91c1c;
    }

    .action-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
    }

    :global(.dark) .action-btn {
        background: #1e293b;
        border-color: #334155;
        color: #cbd5e1;
    }

    :global(.dark) .action-btn:hover {
        background: #334155;
        border-color: #475569;
        color: #f8fafc;
    }

    :global(.dark) .action-btn.danger {
        color: #f87171;
        border-color: #7f1d1d;
        background: #450a0a;
    }

    :global(.dark) .action-btn.danger:hover {
        background: #7f1d1d;
        border-color: #991b1b;
    }

    /* Responsive: hide sticky actions on mobile */
    @media (max-width: 768px) {
        .th-actions, .td-actions {
            position: static;
        }
    }

    /* Editable number cell */
    .cell-editable-number {
        width: 100%;
        max-width: 120px;
        padding: 0.25rem 0.375rem;
        font-size: 0.8125rem;
        font-family: ui-monospace, monospace;
        border: 1px solid #e2e8f0;
        border-radius: 4px;
        background: white;
        color: #1e293b;
        outline: none;
        transition: border-color 0.15s;
    }

    .cell-editable-number:focus {
        border-color: #1a4031;
        box-shadow: 0 0 0 1px #1a403140;
    }

    :global(.dark) .cell-editable-number {
        background: #0f172a;
        border-color: #475569;
        color: #e2e8f0;
    }

    :global(.dark) .cell-editable-number:focus {
        border-color: #4ade80;
        box-shadow: 0 0 0 1px #4ade8040;
    }

    /* Editable text cell */
    .cell-editable-text {
        width: 100%;
        padding: 0.25rem 0.375rem;
        font-size: 0.8125rem;
        border: 1px solid #e2e8f0;
        border-radius: 4px;
        background: white;
        color: #1e293b;
        outline: none;
        transition: border-color 0.15s;
    }

    .cell-editable-text:focus {
        border-color: #1a4031;
        box-shadow: 0 0 0 1px #1a403140;
    }

    :global(.dark) .cell-editable-text {
        background: #0f172a;
        border-color: #475569;
        color: #e2e8f0;
    }

    :global(.dark) .cell-editable-text:focus {
        border-color: #4ade80;
        box-shadow: 0 0 0 1px #4ade8040;
    }

    /* Editable select cell (SimpleSelect wrapper) */
    .cell-editable-select-wrapper {
        width: 100%;
        position: relative;
        /* No z-index here: avoids creating a stacking context that would
           trap the fixed-positioned dropdown below the sticky actions column */
    }

    /* When the dropdown is actually open (focus-within on the row),
       the row z-index bump in tbody tr:focus-within handles visibility */

    /* Row status classes (used via getRowClass prop) */
    :global(tr.row-deleted) td {
        background: rgba(239, 68, 68, 0.06) !important;
        opacity: 0.55;
    }

    :global(.dark) :global(tr.row-deleted) td {
        background: rgba(239, 68, 68, 0.20) !important;
        opacity: 0.55;
    }

    :global(tr.row-edited) td {
        background: rgba(59, 130, 246, 0.06) !important;
    }

    :global(.dark) :global(tr.row-edited) td {
        background: rgba(59, 130, 246, 0.20) !important;
    }

    :global(tr.row-appended) td {
        background: rgba(16, 185, 129, 0.06) !important;
    }

    :global(.dark) :global(tr.row-appended) td {
        background: rgba(16, 185, 129, 0.20) !important;
    }

    :global(tr.row-stale) td {
        background: rgba(245, 158, 11, var(--stale-opacity, 0.04)) !important;
    }

    :global(.dark) :global(tr.row-stale) td {
        background: rgba(245, 158, 11, var(--stale-opacity, 0.08)) !important;
    }
</style>
