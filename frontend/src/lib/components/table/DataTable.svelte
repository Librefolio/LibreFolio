<!--
  DataTable - Generic reusable table component with all features

  Features:
  - User-defined columns with full control over content
  - Row selection with bulk actions
  - Column sorting, filtering (Excel-style), resizing
  - Sticky header and select/actions columns
  - Pagination with floating balloon
  - Preferences saved to localStorage
  - Dark mode support
-->
<script generics="T" lang="ts">
    import {onDestroy, onMount, untrack} from 'svelte';
    import {t} from '$lib/i18n';
    import {getUserStorageKey} from '$lib/utils/storage';
    import {Ban, Check, Filter} from 'lucide-svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import DataTablePagination from './DataTablePagination.svelte';
    import DataTableColumnHeader from './DataTableColumnHeader.svelte';
    import DataTableCellContent from './DataTableCellContent.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import ContextMenu from '$lib/components/ui/ContextMenu.svelte';
    import type {ContextMenuItem} from '$lib/components/ui/ContextMenu.svelte';
    import type {BulkAction, ColumnDef, ColumnWidthsState, FilterValue, FooterCellContent, FooterCells, PaginationState, RowAction, RowActions, SelectionState, SortState, VisibilityState} from './types';
    import {compareRowsByColumn, matchesColumnFilter, reorderKeepingAbsent, withNewColumns} from './dataTableLogic';
    import {clearTimer} from '$lib/utils/core/clearTimer';

    interface Props {
        data: T[];
        columns: ColumnDef<T>[];
        getRowId: (row: T) => string;
        storageKey: string;
        enableSelection?: boolean;
        selectionMode?: 'multi' | 'single' | 'none';
        selectionColumnWidth?: string;
        /** Pre-selected row IDs when the table mounts. Useful when navigating back to a step. */
        initialSelectedIds?: string[];
        onSelectionChange?: (selectedIds: string[]) => void;
        selectedRowId?: string | null;
        onRowClick?: (row: T) => void;
        onRowDoubleClick?: (row: T) => void;
        enableActions?: boolean;
        actionsColumnWidth?: string;
        actionsLabel?: string;
        rowActions?: RowActions<T>;
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
        /** Tooltip text for non-selectable rows (⊘ icon shown instead of checkbox). */
        disabledRowTooltip?: (row: T) => string | null;
        /** Enable touch long-press (500ms) to toggle row selection (mobile). */
        enableTouchSelection?: boolean;
        /** Whether the actions column is sticky (default: true) */
        stickyActions?: boolean;
        /** Whether the header sticks to the top of the vertical scroll viewport (default: true) */
        stickyHeader?: boolean;
        /** Enable right-click/long-press context menu on rows (default: true) */
        enableContextMenu?: boolean;
        /**
         * Called whenever the sort state changes (column click on a sortable
         * header, or sort cleared). Consumers can use this to synchronize
         * external state (e.g. enabling/disabling row-grouping logic when no
         * sort is active).
         */
        onSortChange?: (state: SortState | null) => void;
        /**
         * Called with the row ids in display order — after "show selected only", the column
         * filters and the sort, across every page — once after mount and again whenever that
         * order changes (not on a page change, a resize, or new data in the same order).
         */
        onRowOrderChange?: (rowIds: string[]) => void;
        /**
         * Called whenever the internal "show selected only" toggle changes.
         * Consumers with external pagination can react to this to adjust
         * their displayed total count.
         */
        onShowSelectedOnlyChange?: (active: boolean) => void;
        /**
         * Optional: full unfiltered dataset for computing filter boundaries
         * (min/max sliders, currency ranges). When provided, filter boundaries
         * use this instead of `data`. Useful when `data` is a pre-paginated
         * slice and boundaries should reflect the whole dataset.
         */
        fullData?: T[];
        /** Called when a column is resized (for syncing across tables) */
        onColumnResize?: (columnId: string, width: number) => void;
        /**
         * Optional: if provided, middle-clicking (aux button) a row opens
         * the returned URL in a new tab. Use for rows that represent navigable
         * entities (e.g. assets, transactions).
         */
        getRowHref?: (row: T) => string | undefined;
        /** When true, show the pagination bar whenever there is at least 1 item,
         *  even if all items fit on the current page. Default: false (hide when
         *  all items fit on the smallest non-zero page size). */
        alwaysShowPagination?: boolean;
        /** Optional aggregate footer. Receives selected rows, or filtered rows when nothing is selected. */
        footerCells?: FooterCells<T>;
    }

    let {
        data,
        columns,
        getRowId,
        storageKey,
        enableSelection = true,
        selectionMode = 'multi',
        selectionColumnWidth = '48px',
        initialSelectedIds,
        onSelectionChange,
        selectedRowId = null,
        onRowClick,
        onRowDoubleClick,
        enableActions = true,
        actionsColumnWidth = '64px',
        actionsLabel,
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
        disabledRowTooltip,
        enableTouchSelection = false,
        stickyActions = true,
        stickyHeader = true,
        enableContextMenu = true,
        onSortChange,
        onRowOrderChange,
        onShowSelectedOnlyChange,
        fullData,
        onColumnResize,
        getRowHref,
        alwaysShowPagination = false,
        footerCells,
    }: Props = $props();

    /** Dataset used for computing filter boundaries (min/max, currency ranges). */
    let boundaryData = $derived(fullData ?? data);

    // Derived: effective selection mode
    let effectiveSelectionMode = $derived(!enableSelection ? 'none' : selectionMode);

    // ============ State ============

    // Helper to get initial page size (avoids warning about capturing props in $state)
    function getInitialPageSize(): number {
        return defaultPageSize;
    }

    // Sorting
    let sortState = $state<SortState | null>(null);

    // Context menu
    let contextMenuRow = $state<T | null>(null);
    let contextMenuPos = $state<{x: number; y: number} | null>(null);
    let contextMenuAnchor = $state<HTMLElement | null>(null);

    // Pagination
    let pagination = $state<PaginationState>({
        pageIndex: 0,
        pageSize: getInitialPageSize(),
    });

    // Column visibility — persist only EXPLICIT user overrides, never the full map. This
    // way a column's dynamic `hiddenByDefault` (which can flip once data loads, e.g. the
    // lots table's net-cost columns that appear only when an asset has FEE/TAX) is always
    // honored as the live default, and a stale persisted value can't keep a should-be-visible
    // column hidden. Reset clears the overrides and re-applies the current dynamic default.
    let columnVisibilityOverrides = $state<VisibilityState>({});
    let columnVisibility = $derived<VisibilityState>(Object.fromEntries(columns.map((c) => [c.id, c.id in columnVisibilityOverrides ? columnVisibilityOverrides[c.id] : !c.hiddenByDefault])));

    // Column widths
    let columnWidths = $state<ColumnWidthsState>({});

    // Column order
    let columnOrder = $state<string[]>([]);

    // Row selection — pre-populate from initialSelectedIds if provided (set synchronously to avoid flicker)
    let rowSelection = $state<SelectionState>({});
    untrack(() => {
        const ids = initialSelectedIds;
        if (ids && ids.length > 0) {
            rowSelection = Object.fromEntries(ids.map((id) => [id, true]));
        }
    });

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
    let pendingRowAction = $state<{action: RowAction<T>; row: T} | null>(null);

    // Resize state
    let resizing = $state<{columnId: string; pointerId: number; startX: number; startWidth: number} | null>(null);

    // Highlighted row (set by navigateToRowId, cleared on user interaction)
    let highlightedRowId = $state<string | null>(null);

    // Long-press touch state for mobile selection toggle (or, when touch selection is
    // disabled, a mobile-friendly equivalent of desktop double-click — there is no
    // natural double-tap affordance on touch devices).
    let touchTimerId = $state<ReturnType<typeof setTimeout> | null>(null);
    // Tracks whether the CURRENT interaction originated from a touch event, so the
    // native context menu can be suppressed specifically for touch-originated
    // long-press (mobile) without affecting genuine desktop mouse right-click.
    let touchActive = false;
    let touchActiveResetTimer: ReturnType<typeof setTimeout> | null = null;

    function handleTouchStart(row: T, e: TouchEvent) {
        touchActive = true;
        if (touchActiveResetTimer != null) {
            clearTimeout(touchActiveResetTimer);
            touchActiveResetTimer = null;
        }
        if (isRowSelectable && !isRowSelectable(row)) return;
        touchTimerId = setTimeout(() => {
            touchTimerId = null;
            if (enableTouchSelection) {
                toggleRowSelection(getRowId(row));
            } else if (onRowDoubleClick) {
                // No selection concept here (e.g. compact/dashboard tables) — long-press
                // opens the same "view" action a desktop double-click would.
                handleRowDoubleClick(row);
            }
        }, 500);
    }

    function resetTouchActiveSoon() {
        // Some mobile browsers fire `contextmenu` right around `touchend`/`touchcancel` —
        // delay clearing the flag briefly so that event can still be detected as
        // touch-originated when it arrives.
        if (touchActiveResetTimer != null) clearTimeout(touchActiveResetTimer);
        touchActiveResetTimer = setTimeout(() => {
            touchActive = false;
            touchActiveResetTimer = null;
        }, 100);
    }

    function handleTouchEnd() {
        if (touchTimerId != null) {
            clearTimeout(touchTimerId);
            touchTimerId = null;
        }
        resetTouchActiveSoon();
    }

    function handleTouchMove() {
        if (touchTimerId != null) {
            clearTimeout(touchTimerId);
            touchTimerId = null;
        }
        resetTouchActiveSoon();
    }

    /** Bound on the root `.datatable-container` so `navigateToRowId` can scope
     *  its DOM lookup to this instance only (Bugfix-4 §C15). */
    let containerEl: HTMLDivElement | null = null;

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
        } catch {}
    }

    // ============ Derived State ============

    // Default column order
    let defaultColumnOrder = $derived(columns.map((c) => c.id));

    // Default column widths
    let defaultColumnWidths = $derived(Object.fromEntries(columns.map((c) => [c.id, c.width ?? 150])));

    // All columns in current order (for toolbar dropdown)
    let orderedColumns = $derived(columnOrder.map((id) => columns.find((c) => c.id === id)).filter((c): c is ColumnDef<T> => c !== undefined));

    // Visible and ordered columns (for table rendering)
    let visibleColumns = $derived(orderedColumns.filter((c) => columnVisibility[c.id] !== false));

    let hasRowActionProvider = $derived(typeof rowActions === 'function' || rowActions.length > 0);
    let showActionsColumn = $derived(enableActions && hasRowActionProvider);
    let resolvedActionsLabel = $derived(actionsLabel ?? $t('table.actions') ?? 'Actions');

    // Filtered data
    let filteredData = $derived.by(() => {
        let result = [...data];

        // Apply "show selected only" filter
        if (showSelectedOnly) {
            result = result.filter((row) => rowSelection[getRowId(row)]);
        }

        // Apply column filters
        for (const [columnId, filterValue] of Object.entries(columnFilters)) {
            if (!filterValue) continue;

            const column = columns.find((c) => c.id === columnId);
            if (!column) continue;

            result = result.filter((row) => matchesColumnFilter(column, row, filterValue));
        }

        return result;
    });

    // Sorted data
    let sortedData = $derived.by(() => {
        if (!sortState || !enableSorting) return filteredData;

        const column = columns.find((c) => c.id === sortState!.columnId);
        if (!column) return filteredData;

        return [...filteredData].sort((a, b) => compareRowsByColumn(column, a, b, sortState!.direction));
    });

    // Paginated data
    let paginatedData = $derived.by(() => {
        if (!enablePagination) return sortedData;
        const start = pagination.pageIndex * pagination.pageSize;
        return sortedData.slice(start, start + pagination.pageSize);
    });

    // Report the display order (every page) when it changes. The last report is a plain variable:
    // it is only compared, never rendered, and must not make this effect depend on itself.
    let lastReportedRowOrder: string | null = null;
    $effect(() => {
        if (!onRowOrderChange) return;
        const rowIds = sortedData.map((row) => getRowId(row));
        const key = JSON.stringify(rowIds);
        if (key === lastReportedRowOrder) return;
        lastReportedRowOrder = key;
        const report = onRowOrderChange;
        untrack(() => report(rowIds));
    });

    // Selected rows
    let selectedRows = $derived(
        Object.keys(rowSelection)
            .filter((id) => rowSelection[id])
            .map((id) => data.find((row) => getRowId(row) === id))
            .filter((r): r is T => r !== undefined),
    );

    let footerSourceRows = $derived(selectedRows.length > 0 ? selectedRows : filteredData);
    let computedFooterCells = $derived.by<Record<string, FooterCellContent>>(() => {
        if (!footerCells) return {};
        return typeof footerCells === 'function' ? footerCells(footerSourceRows, selectedRows, visibleColumns) : footerCells;
    });
    let hasFooterCells = $derived(Object.keys(computedFooterCells).length > 0);

    // Check if all rows on current page are selected
    let isAllPageSelected = $derived.by(() => {
        if (paginatedData.length === 0) return false;
        return paginatedData.every((row) => rowSelection[getRowId(row)]);
    });

    let isSomePageSelected = $derived(paginatedData.some((row) => rowSelection[getRowId(row)]) && !isAllPageSelected);

    // Total pages
    let totalPages = $derived(Math.ceil(filteredData.length / pagination.pageSize));

    // ============ Helper Functions ============

    let headerTooltipLongPressTimer: ReturnType<typeof setTimeout> | null = null;
    let suppressHeaderTooltipClick = false;

    function openHeaderTooltipDoc(url: string) {
        window.open(url, '_blank', 'noopener,noreferrer');
    }

    function handleHeaderTooltipDblClick(event: MouseEvent, url: string) {
        event.preventDefault();
        event.stopPropagation();
        openHeaderTooltipDoc(url);
    }

    function handleHeaderTooltipKeydown(event: KeyboardEvent, url: string) {
        if (event.key !== 'Enter' || !event.shiftKey) return;
        event.preventDefault();
        event.stopPropagation();
        openHeaderTooltipDoc(url);
    }

    function handleHeaderTooltipTouchStart(url: string) {
        suppressHeaderTooltipClick = false;
        headerTooltipLongPressTimer = clearTimer(headerTooltipLongPressTimer);
        headerTooltipLongPressTimer = setTimeout(() => {
            headerTooltipLongPressTimer = null;
            suppressHeaderTooltipClick = true;
            openHeaderTooltipDoc(url);
        }, 500);
    }

    function cancelHeaderTooltipLongPress() {
        headerTooltipLongPressTimer = clearTimer(headerTooltipLongPressTimer);
    }

    function handleHeaderTooltipGestureClick(event: MouseEvent) {
        if (!suppressHeaderTooltipClick) return;
        event.preventDefault();
        event.stopPropagation();
        suppressHeaderTooltipClick = false;
    }

    // ============ Actions ============

    function toggleSort(columnId: string) {
        if (!enableSorting) return;
        const column = columns.find((c) => c.id === columnId);
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
        onSortChange?.(sortState);
    }

    function toggleAllPageRows() {
        const selectableRows = isRowSelectable ? paginatedData.filter((row) => isRowSelectable!(row)) : paginatedData;
        if (isAllPageSelected) {
            // Deselect all on current page
            const newSelection = {...rowSelection};
            selectableRows.forEach((row) => delete newSelection[getRowId(row)]);
            rowSelection = newSelection;
        } else {
            // Select all on current page (clear previous selection)
            const newSelection: SelectionState = {};
            selectableRows.forEach((row) => (newSelection[getRowId(row)] = true));
            rowSelection = newSelection;
        }
        onSelectionChange?.(Object.keys(rowSelection).filter((id) => rowSelection[id]));
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
        onSelectionChange?.(Object.keys(rowSelection).filter((id) => rowSelection[id]));
    }

    // Sync external selectedRowId prop (for single mode controlled by parent)
    $effect(() => {
        if (effectiveSelectionMode === 'single' && selectedRowId !== undefined && selectedRowId !== null) {
            const currentSelected = Object.keys(rowSelection).find((id) => rowSelection[id]);
            if (currentSelected !== selectedRowId) {
                rowSelection = {[selectedRowId]: true};
            }
        }
    });

    // Auto-deactivate "show selected only" when selection becomes empty
    $effect(() => {
        const selectedCount = Object.keys(rowSelection).filter((id) => rowSelection[id]).length;
        if (selectedCount === 0 && showSelectedOnly) {
            showSelectedOnly = false;
        }
    });

    // Notify parent when "show selected only" toggles (for external pagination sync)
    $effect(() => {
        onShowSelectedOnlyChange?.(showSelectedOnly);
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

    function getVisibleRowActions(row: T): RowAction<T>[] {
        const actions = typeof rowActions === 'function' ? rowActions(row) : rowActions;
        return actions.filter((action) => !action.visible || action.visible(row));
    }

    function rowActionsToMenuItems(actions: RowAction<T>[], row: T): ContextMenuItem[] {
        return actions.map((action) => ({
            id: action.id,
            label: typeof action.label === 'function' ? action.label(row) : action.label,
            icon: action.icon,
            variant: action.variant,
            disabled: action.disabled?.(row) ?? false,
            title: typeof action.title === 'function' ? action.title(row) : action.title,
            testid: typeof action.testid === 'function' ? action.testid(row) : action.testid,
            iconClass: action.iconClass?.(row),
            labelClass: typeof action.labelClass === 'function' ? action.labelClass(row) : action.labelClass,
        }));
    }

    function openRowActionsMenu(row: T, button: HTMLButtonElement): void {
        const rect = button.getBoundingClientRect();
        contextMenuRow = row;
        contextMenuAnchor = button;
        contextMenuPos = {x: rect.left, y: rect.bottom + 4};
    }

    function closeContextMenu(): void {
        contextMenuRow = null;
        contextMenuPos = null;
        contextMenuAnchor = null;
    }

    function handleContextMenuAction(actionId: string, row: T): void {
        const action = getVisibleRowActions(row).find((candidate) => candidate.id === actionId);
        closeContextMenu();
        if (action) handleRowAction(action, row);
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
        const current = columnVisibility[columnId] ?? true;
        columnVisibilityOverrides = {...columnVisibilityOverrides, [columnId]: !current};
        saveToStorage(getStorageKey('columnVisibilityOverrides'), columnVisibilityOverrides);
    }

    function resetColumns() {
        columnVisibilityOverrides = {};
        columnWidths = {...defaultColumnWidths};
        columnOrder = [...defaultColumnOrder];
        columnFilters = {};
        saveToStorage(getStorageKey('columnVisibilityOverrides'), {});
        saveToStorage(getStorageKey('columnWidths'), defaultColumnWidths);
        saveToStorage(getStorageKey('columnOrder'), defaultColumnOrder);
    }

    function reorderColumns(newOrder: string[]) {
        // The chooser lists only the columns on screen: a column away now keeps its place after the one it followed (Y-27).
        const order = reorderKeepingAbsent(columnOrder, newOrder, defaultColumnOrder);
        columnOrder = order;
        saveToStorage(getStorageKey('columnOrder'), order);
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
    // A handle answers Pointer Events, so a finger or a pen resizes a column like a mouse (D-Y18). The drag starts from
    // the width the column is drawn at, and the drawn width follows the pointer (C-62): a table that shares its spare
    // width among its columns (`tableLayout="auto"`, or a fixed table narrower than its box) draws a column wider than
    // the width it is given, so the width written is corrected on the cell until the drawn one matches.

    /** The header cell being resized: a plain variable, read only while dragging. */
    let resizeCell: HTMLElement | null = null;

    function startResize(columnId: string, event: PointerEvent) {
        if (event.pointerType === 'mouse' && event.button !== 0) return;
        event.preventDefault();
        event.stopPropagation();
        const handle = event.currentTarget instanceof HTMLElement ? event.currentTarget : null;
        try {
            handle?.setPointerCapture?.(event.pointerId);
        } catch {
            // A pointer the browser no longer tracks: the document listeners below still see its moves.
        }
        resizeCell = handle?.closest('th') ?? null;
        resizing = {
            columnId,
            pointerId: event.pointerId,
            startX: event.clientX,
            startWidth: resizeCell?.getBoundingClientRect().width || columnWidths[columnId] || columns.find((c) => c.id === columnId)?.width || 150,
        };
        document.addEventListener('pointermove', handleResize);
        document.addEventListener('pointerup', stopResize);
        document.addEventListener('pointercancel', stopResize);
    }

    function handleResize(event: PointerEvent) {
        if (!resizing || event.pointerId !== resizing.pointerId) return;
        const {columnId, startWidth, startX} = resizing;
        const col = columns.find((c) => c.id === columnId);
        const minWidth = col?.minWidth ?? 50;
        const maxWidth = col?.maxWidth ?? 600;
        const target = Math.min(maxWidth, Math.max(minWidth, startWidth + event.clientX - startX));
        columnWidths = {...columnWidths, [columnId]: fitDrawnWidth(target, columnWidths[columnId] ?? target, minWidth, maxWidth)};
    }

    /**
     * The width to give the header cell being resized so that it is drawn `target` px wide. The cell is measured after
     * each guess: the first scales the given width by drawn/given, the next ones are secant steps. On a table that draws
     * every column at its given width (fixed, wider than its box) the first guess is exact.
     */
    function fitDrawnWidth(target: number, given: number, minWidth: number, maxWidth: number): number {
        const cell = resizeCell;
        if (!cell) return target;
        const clamp = (width: number) => Math.min(maxWidth, Math.max(minWidth, width));
        const draw = (width: number) => {
            cell.style.width = `${width}px`;
            cell.style.minWidth = `${width}px`;
            return cell.getBoundingClientRect().width;
        };
        let previous = {width: given, drawn: cell.getBoundingClientRect().width};
        let width = clamp(previous.drawn > 0 ? (given * target) / previous.drawn : target);
        for (let step = 0; step < 4; step++) {
            const drawn = draw(width);
            if (Math.abs(drawn - target) < 0.5) break;
            const slope = (drawn - previous.drawn) / (width - previous.width);
            const next = clamp(Number.isFinite(slope) && slope > 0 ? width + (target - drawn) / slope : width + target - drawn);
            previous = {width, drawn};
            if (Math.abs(next - width) < 0.1) break;
            width = next;
        }
        return Math.round(width * 10) / 10;
    }

    function stopResize(event?: PointerEvent) {
        if (event && resizing && event.pointerId !== resizing.pointerId) return;
        if (resizing) {
            const finalWidth = columnWidths[resizing.columnId];
            saveToStorage(getStorageKey('columnWidths'), columnWidths);
            if (finalWidth != null) onColumnResize?.(resizing.columnId, finalWidth);
        }
        endResize();
    }

    function endResize() {
        resizing = null;
        resizeCell = null;
        document.removeEventListener('pointermove', handleResize);
        document.removeEventListener('pointerup', stopResize);
        document.removeEventListener('pointercancel', stopResize);
    }

    /** A column's minimum width: the user's width once they resized it (its width differs from the default), so a table
     *  laid out `auto` keeps it (C-62); otherwise the column's own minimum. */
    function columnMinWidth(column: ColumnDef<T>): number {
        const width = columnWidths[column.id];
        return width != null && width !== defaultColumnWidths[column.id] ? width : column.minWidth || 60;
    }

    // ============ Lifecycle ============

    onMount(() => {
        // Load preferences
        const storedPageSize = loadFromStorage<number>(getStorageKey('pageSize'), defaultPageSize);
        pagination = {...pagination, pageSize: storedPageSize === 0 ? 999999 : storedPageSize};

        // Load only explicit user overrides; effective visibility is derived from the
        // live `hiddenByDefault` default merged with these overrides (see declaration).
        // Every stored override is kept, a column absent now included: the Δ period columns
        // arrive after the first render, and their choice must hold when they do (Y-27).
        const storedOverrides = loadFromStorage<VisibilityState | null>(getStorageKey('columnVisibilityOverrides'), null);
        if (storedOverrides) {
            columnVisibilityOverrides = {...storedOverrides};
        }

        columnWidths = loadFromStorage(getStorageKey('columnWidths'), defaultColumnWidths);
        columnOrder = loadFromStorage(getStorageKey('columnOrder'), defaultColumnOrder);

        // Apply initial filters from URL (if provided)
        if (initialFilters && Object.keys(initialFilters).length > 0) {
            // Map URL keys to column IDs
            const filtersByColumnId: Record<string, FilterValue> = {};
            for (const [urlKey, value] of Object.entries(initialFilters)) {
                // Find column by urlKey or id
                const col = columns.find((c) => (c.urlKey ?? c.id) === urlKey);
                if (col) {
                    filtersByColumnId[col.id] = value;
                }
            }
            columnFilters = filtersByColumnId;
        }
    });

    onDestroy(cancelHeaderTooltipLongPress);
    onDestroy(endResize);

    // Notify parent when filters change (for URL sync)
    $effect(() => {
        // Only call if handler provided and we have some filter activity
        if (onFiltersChange) {
            // Build filters with URL keys
            const filtersWithUrlKeys: Record<string, FilterValue> = {};
            for (const [columnId, value] of Object.entries(columnFilters)) {
                if (!value) continue;
                const col = columns.find((c) => c.id === columnId);
                const urlKey = col?.urlKey ?? columnId;
                filtersWithUrlKeys[urlKey] = value;
            }
            onFiltersChange(filtersWithUrlKeys);
        }
    });

    // Sync column order/widths when columns change dynamically (e.g. the Δ period columns, which
    // arrive once the backend lists them and change with the date range). A column absent now
    // keeps its place, its visibility override and its width, so they hold when it comes back:
    // only a column never seen is added, at its natural place, and nothing is pruned (Y-27).
    // Visibility needs no handling: it is derived from each column's live `hiddenByDefault`
    // plus the user's overrides.
    $effect(() => {
        const nextOrder = withNewColumns(columnOrder, defaultColumnOrder);
        if (nextOrder.length !== columnOrder.length) {
            const newIds = nextOrder.filter((id) => !columnOrder.includes(id));
            columnOrder = nextOrder;
            saveToStorage(getStorageKey('columnOrder'), columnOrder);

            // A width for the new columns only: a column that comes back keeps the one it had.
            const updatedWidths = {...columnWidths};
            for (const id of newIds) {
                if (updatedWidths[id] === undefined) updatedWidths[id] = columns.find((c) => c.id === id)?.width ?? 150;
            }
            columnWidths = updatedWidths;
        }

        // Initial fallback (first mount before localStorage loads)
        if (columnOrder.length === 0) {
            columnOrder = [...defaultColumnOrder];
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
        const index = sortedData.findIndex((row) => getRowId(row) === rowId);
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
        import('svelte')
            .then(({tick}) => tick())
            .then(() => {
                // Bugfix-4 §C15: scope the row lookup to THIS datatable's
                // container so a modal-table navigation doesn't accidentally
                // scroll a different datatable mounted elsewhere on the page.
                const root = containerEl ?? document;
                const rows = root.querySelectorAll('.datatable tbody tr');
                const positionInPage = enablePagination ? index % pagination.pageSize : index;
                const targetRow = rows[positionInPage];
                targetRow?.scrollIntoView({behavior: 'smooth', block: 'center'});
            });
    }

    /** Get ordered columns info for external visibility control */
    export function getColumnsForVisibility(): Array<{id: string; header: string | (() => string); displayName?: string | (() => string); visible: boolean}> {
        return orderedColumns
            .filter((c) => {
                // Hide columns with no visible label (e.g. the checkbox selection column)
                const h = typeof c.header === 'function' ? c.header() : c.header;
                const dn = c.displayName ? (typeof c.displayName === 'function' ? c.displayName() : c.displayName) : undefined;
                return h !== '' || (dn !== undefined && dn !== '');
            })
            .map((c) => ({id: c.id, header: c.header, displayName: c.displayName, visible: columnVisibility[c.id] !== false}));
    }

    /** Toggle a column's visibility (external access) */
    export function toggleColumnVisibilityById(columnId: string) {
        toggleColumnVisibility(columnId);
    }

    /** Set column order (reorder columns) */
    export function setColumnOrder(newOrder: string[]) {
        reorderColumns(newOrder);
    }

    /** Reset column visibility, order and widths to defaults */
    export function resetColumnLayout() {
        resetColumns();
    }

    /** Set width for a specific column (for cross-table sync) */
    export function setColumnWidth(columnId: string, width: number) {
        columnWidths = {...columnWidths, [columnId]: width};
    }

    /** Clear all selected rows (external access) */
    export function clearSelection() {
        clearAllSelection();
    }

    /** Clear all column filters (for external reset). */
    export function clearFilters() {
        columnFilters = {};
        onFiltersChange?.({});
    }

    /** Toggle selection for a specific row by ID (external access, e.g. Picker dblclick). */
    export function toggleRowSelectionById(rowId: string) {
        toggleRowSelection(rowId);
    }

    /** Row IDs currently rendered on the active page (after filters, sort, and pagination). */
    export function getPageRowIds(): string[] {
        return paginatedData.map((row) => getRowId(row));
    }

    /** All matching row IDs in display order, before pagination. */
    export function getSortedRowIds(): string[] {
        return sortedData.map((row) => getRowId(row));
    }
</script>

<div class="datatable-container" bind:this={containerEl}>
    <!-- Table -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="table-wrapper"
        data-testid="dt-scroll"
        onkeydown={() => {
            highlightedRowId = null;
        }}
    >
        <table class="datatable {tableLayout === 'auto' ? 'layout-auto' : ''}">
            <thead class={stickyHeader ? 'sticky-header' : undefined}>
                <tr>
                    <!-- Selection column (multi mode: checkboxes, single mode: no column header) -->
                    {#if effectiveSelectionMode === 'multi'}
                        <th class="th-fixed th-select" style="width: {selectionColumnWidth};" data-testid="dt-select-header">
                            <div class="flex items-center justify-center gap-1">
                                <!-- data-state publishes the tri-state of the header checkbox so it can be
                                     observed without reading the icon's CSS class. -->
                                <button type="button" class="checkbox-btn" data-testid="dt-select-all" data-state={isAllPageSelected ? 'checked' : isSomePageSelected ? 'partial' : 'unchecked'} onclick={toggleAllPageRows}>
                                    {#if isAllPageSelected}
                                        <Check size={16} class="check-icon checked" />
                                    {:else if isSomePageSelected}
                                        <Check size={16} class="check-icon partial" />
                                    {:else}
                                        <span class="check-box"></span>
                                    {/if}
                                </button>
                                <button
                                    type="button"
                                    class="filter-btn"
                                    class:active={showSelectedOnly}
                                    data-testid="dt-show-selected-only"
                                    data-state={showSelectedOnly ? 'on' : 'off'}
                                    onclick={() => {
                                        showSelectedOnly = !showSelectedOnly;
                                    }}
                                    title="Show selected only"
                                >
                                    <Filter size={12} />
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
                            data-testid="dt-header-{column.id}"
                            data-sort={sortDir ?? 'none'}
                            class:sortable={column.sortable !== false && enableSorting}
                            class:th-fixed={column.pinned != null}
                            class:th-pinned-right={column.pinned === 'right'}
                            style="width: {columnWidths[column.id] || column.width || 150}px; min-width: {columnMinWidth(column)}px;{column.pinned === 'left' ? ' left: 0;' : column.pinned === 'right' ? ' right: 0;' : ''}{column.align ? ` text-align: ${column.align};` : ''}"
                        >
                            <DataTableColumnHeader
                                {column}
                                {sortDir}
                                {hasFilter}
                                {enableSorting}
                                {enableColumnFilters}
                                {enableColumnResize}
                                {resizing}
                                {columnFilters}
                                {data}
                                {boundaryData}
                                bind:openFilterColumnId
                                {toggleSort}
                                {applyColumnFilter}
                                {startResize}
                                {handleHeaderTooltipGestureClick}
                                {handleHeaderTooltipDblClick}
                                {handleHeaderTooltipKeydown}
                                {handleHeaderTooltipTouchStart}
                                {cancelHeaderTooltipLongPress}
                            />
                        </th>
                    {/each}

                    <!-- Actions column -->
                    {#if showActionsColumn}
                        <th class="{stickyActions ? 'th-fixed' : ''} th-actions" style="width: {actionsColumnWidth};" data-testid="dt-actions-header">
                            {resolvedActionsLabel}
                        </th>
                    {/if}
                </tr>
            </thead>
            <tbody>
                {#if isLoading}
                    <tr>
                        <td colspan={visibleColumns.length + (effectiveSelectionMode === 'multi' ? 1 : 0) + (showActionsColumn ? 1 : 0)} class="td-loading" data-testid="dt-loading">
                            <div class="loading-spinner"></div>
                            <span>{$t('common.loading') || 'Loading...'}</span>
                        </td>
                    </tr>
                {:else if paginatedData.length === 0}
                    <tr>
                        <td colspan={visibleColumns.length + (effectiveSelectionMode === 'multi' ? 1 : 0) + (showActionsColumn ? 1 : 0)} class="td-empty" data-testid="dt-empty">
                            {emptyMessage || $t('common.noData') || 'No data available'}
                        </td>
                    </tr>
                {:else}
                    {#each paginatedData as row}
                        {@const rowId = getRowId(row)}
                        {@const isSelected = rowSelection[rowId]}
                        {@const visibleRowActions = getVisibleRowActions(row)}
                        <tr
                            data-row-id={rowId}
                            data-selected={isSelected ? 'true' : 'false'}
                            data-highlighted={rowId === highlightedRowId ? 'true' : 'false'}
                            class="{isSelected ? 'selected' : ''} {effectiveSelectionMode === 'single' || onRowClick ? 'clickable' : ''} {rowId === highlightedRowId ? 'highlighted' : ''} {getRowClass?.(row) ?? ''}"
                            style={getRowStyle?.(row) ?? ''}
                            onclick={() => {
                                if (isRowSelectable && !isRowSelectable(row)) return;
                                highlightedRowId = null;
                                handleRowClick(row);
                            }}
                            ondblclick={() => {
                                if (isRowSelectable && !isRowSelectable(row)) return;
                                handleRowDoubleClick(row);
                            }}
                            onauxclick={(e) => {
                                if (e.button === 1 && getRowHref) {
                                    const href = getRowHref(row);
                                    if (href) window.open(href, '_blank');
                                }
                            }}
                            oncontextmenu={(e) => {
                                if (enableContextMenu && visibleRowActions.length > 0) {
                                    e.preventDefault();
                                    contextMenuRow = row;
                                    contextMenuAnchor = null;
                                    contextMenuPos = {x: e.clientX, y: e.clientY};
                                    return;
                                }
                                // No custom context menu configured — still suppress the
                                // browser's native one when this is a touch-originated
                                // long-press we're already handling ourselves (selection
                                // toggle or view-row fallback), so it doesn't pop up over
                                // our own action on mobile. Genuine desktop mouse
                                // right-clicks (touchActive false) are left untouched.
                                if (touchActive && (enableTouchSelection || onRowDoubleClick)) {
                                    e.preventDefault();
                                }
                            }}
                            ontouchstart={(e) => handleTouchStart(row, e)}
                            ontouchend={handleTouchEnd}
                            ontouchmove={handleTouchMove}
                        >
                            <!-- Selection cell (multi mode only - shows checkboxes) -->
                            {#if effectiveSelectionMode === 'multi'}
                                <td class="td-fixed td-select" data-testid="dt-select-cell-{rowId}">
                                    <div class="flex items-center justify-center gap-1">
                                        {#if !isRowSelectable || isRowSelectable(row)}
                                            <button
                                                type="button"
                                                class="checkbox-btn"
                                                data-testid="dt-row-checkbox-{rowId}"
                                                data-state={isSelected ? 'checked' : 'unchecked'}
                                                onclick={(e) => {
                                                    e.stopPropagation();
                                                    toggleRowSelection(rowId);
                                                }}
                                            >
                                                {#if isSelected}
                                                    <Check size={16} class="check-icon checked" />
                                                {:else}
                                                    <span class="check-box"></span>
                                                {/if}
                                            </button>
                                        {:else}
                                            {@const dTooltip = disabledRowTooltip?.(row) ?? null}
                                            {#if dTooltip}
                                                <Tooltip html={dTooltip} position="right" maxWidth="280px">
                                                    <span class="disabled-select-icon"><Ban size={16} /></span>
                                                </Tooltip>
                                            {:else}
                                                <div style="width:28px"></div>
                                            {/if}
                                        {/if}
                                        <!-- Invisible spacer matching filter button width for alignment -->
                                        <div class="invisible" style="width:20px" aria-hidden="true"></div>
                                    </div>
                                </td>
                            {/if}

                            <!-- Data cells -->
                            {#each visibleColumns as column}
                                {@const cellContent = column.cell(row)}
                                <td
                                    class="td-data"
                                    class:td-fixed={column.pinned != null}
                                    class:td-pinned-right={column.pinned === 'right'}
                                    style="{column.pinned === 'left' ? 'left: 0;' : column.pinned === 'right' ? 'right: 0;' : ''}{column.align ? ` text-align: ${column.align};` : ''}"
                                    data-column-id={column.id}
                                >
                                    <DataTableCellContent {cellContent} />
                                </td>
                            {/each}

                            <!-- Actions cell -->
                            {#if showActionsColumn}
                                <td class="{stickyActions ? 'td-fixed' : ''} td-actions" data-testid="dt-actions-cell-{rowId}">
                                    <div class="actions-row">
                                        {#if visibleRowActions.length > 0}
                                            <button
                                                type="button"
                                                class="row-actions-btn"
                                                data-testid="row-actions-{rowId}"
                                                aria-label={resolvedActionsLabel}
                                                title={resolvedActionsLabel}
                                                onclick={(e) => {
                                                    e.preventDefault();
                                                    e.stopPropagation();
                                                    openRowActionsMenu(row, e.currentTarget);
                                                }}
                                            >
                                                ⋮
                                            </button>
                                        {/if}
                                    </div>
                                </td>
                            {/if}
                        </tr>
                    {/each}
                {/if}
            </tbody>
            {#if hasFooterCells && !isLoading && footerSourceRows.length > 0}
                <tfoot>
                    <tr>
                        {#if effectiveSelectionMode === 'multi'}
                            <td class="td-fixed td-select td-footer"></td>
                        {/if}
                        {#each visibleColumns as column}
                            {@const footerContent = computedFooterCells[column.id] ?? ''}
                            <td
                                class="td-data td-footer"
                                data-testid="dt-footer-{column.id}"
                                class:td-fixed={column.pinned != null}
                                class:td-pinned-right={column.pinned === 'right'}
                                style="{column.pinned === 'left' ? 'left: 0;' : column.pinned === 'right' ? 'right: 0;' : ''}{column.align ? ` text-align: ${column.align};` : ''}"
                            >
                                <DataTableCellContent cellContent={footerContent} />
                            </td>
                        {/each}
                        {#if showActionsColumn}
                            <td class="{stickyActions ? 'td-fixed' : ''} td-actions td-footer"></td>
                        {/if}
                    </tr>
                </tfoot>
            {/if}
        </table>
    </div>

    <!-- Pagination - show only when enabled and items exceed smallest page size (or alwaysShowPagination) -->
    {#if enablePagination && filteredData.length > 0 && (alwaysShowPagination || filteredData.length > Math.min(...pageSizeOptions.filter((x) => x > 0)))}
        <DataTablePagination pageIndex={pagination.pageIndex} pageSize={pagination.pageSize} totalItems={filteredData.length} {pageSizeOptions} onPageChange={handlePageChange} onPageSizeChange={handlePageSizeChange} />
    {/if}
</div>

<!-- Context menu for right-click / long-press -->
{#if contextMenuRow != null && contextMenuPos != null}
    {@const cmRow = contextMenuRow}
    <ContextMenu x={contextMenuPos.x} y={contextMenuPos.y} items={rowActionsToMenuItems(getVisibleRowActions(cmRow), cmRow)} anchorEl={contextMenuAnchor} onAction={(id) => handleContextMenuAction(id, cmRow)} onClose={closeContextMenu} />
{/if}

<!-- Confirm modal for bulk actions -->
<ConfirmModal
    danger={pendingBulkAction?.variant === 'danger'}
    items={selectedRows.map((row) => (getRowDisplayName ? getRowDisplayName(row) : String(getRowId(row))))}
    itemsLabel={`${selectedRows.length} ${$t('table.items')}`}
    message={pendingBulkAction?.confirmMessage ? (typeof pendingBulkAction.confirmMessage === 'function' ? pendingBulkAction.confirmMessage(selectedRows.length) : pendingBulkAction.confirmMessage) : `${$t('table.confirmBulkAction')} ${selectedRows.length} ${$t('table.items')}?`}
    onCancel={cancelBulkAction}
    onConfirm={confirmBulkAction}
    open={showDeleteModal}
    title={$t('common.confirm')}
/>

<!-- Confirm modal for single row actions -->
<ConfirmModal
    danger={pendingRowAction?.action.variant === 'danger'}
    items={pendingRowAction ? [getRowDisplayName ? getRowDisplayName(pendingRowAction.row) : String(getRowId(pendingRowAction.row))] : []}
    message={pendingRowAction?.action.confirmMessage ? (typeof pendingRowAction.action.confirmMessage === 'function' ? pendingRowAction.action.confirmMessage(pendingRowAction.row) : pendingRowAction.action.confirmMessage) : $t('common.confirmDelete')}
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
        border: 1px solid var(--lf-border-subtle);
        border-radius: 8px;
        background: var(--lf-surface-card);
    }

    .datatable {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
        background: var(--lf-surface-card);
    }

    .datatable.layout-auto {
        table-layout: auto;
    }

    /* Header */
    thead {
        background: var(--lf-surface-panel);
    }

    th {
        padding: 0.5rem 0.5rem;
        text-align: left;
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--lf-text-muted);
        border-bottom: 1px solid var(--lf-border-subtle);
        white-space: nowrap;
        position: relative;
        text-transform: uppercase;
        letter-spacing: 0.025em;
    }

    thead.sticky-header th {
        position: sticky;
        top: 0;
        z-index: 15;
        background: inherit;
    }

    thead.sticky-header .th-fixed {
        z-index: 25;
        background: var(--lf-surface-panel);
    }

    .th-fixed {
        position: sticky;
        z-index: 10;
        background: var(--lf-surface-panel);
    }

    .th-pinned-right {
        right: 0;
    }

    .td-pinned-right {
        right: 0;
    }

    .th-select {
        left: 0;
        text-align: center;
    }

    .th-actions {
        text-align: center;
        text-transform: none !important;
    }

    .th-actions.th-fixed {
        right: 0;
    }

    .th-data.sortable {
        cursor: pointer;
    }

    .th-data.sortable:hover {
        background: var(--lf-surface-neutral);
        color: var(--lf-text-secondary);
    }

    /* The "show selected only" button of the selection header; the column headers carry their own copy (DataTableColumnHeader.svelte). */
    .filter-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 20px;
        height: 20px;
        border: none;
        border-radius: 4px;
        background: transparent;
        color: var(--lf-text-muted);
        cursor: pointer;
        transition: all 0.15s;
    }

    .filter-btn:hover {
        background: var(--lf-surface-neutral);
        color: var(--lf-text-primary);
    }

    .filter-btn.active {
        background: var(--lf-checked);
        color: var(--lf-on-checked);
    }

    /* Body. A row paints the card and, over it, the tint of its state, `--dt-row-tint`, as one image layer: whatever
       its tint, the row is opaque, so a fixed cell (`background: inherit`) shows what the other cells of its row show
       and hides what scrolls under it. A translucent tint is the selection's: it is composited by the browser, over the
       card, from the role itself. A list that tints its own rows sets `--dt-row-tint`, never the row's background
       (AssetTable). Registered, so that a change of state fades and the highlight pulses. */
    @property --dt-row-tint {
        syntax: '<color>';
        inherits: true;
        initial-value: transparent;
    }

    tbody tr {
        --dt-row-tint: transparent;
        background: linear-gradient(var(--dt-row-tint), var(--dt-row-tint)) var(--lf-surface-card);
        transition: --dt-row-tint 0.15s;
    }

    tfoot tr {
        background: var(--lf-surface-panel);
    }

    .td-footer {
        border-top: 1px solid var(--lf-border-subtle);
        border-bottom: 0;
        font-weight: 700;
        color: var(--lf-text-primary);
    }

    tbody tr:hover {
        --dt-row-tint: var(--lf-surface-hover);
    }

    tbody :global(tr.selected) {
        --dt-row-tint: var(--lf-selected);
    }

    tbody :global(tr.clickable) {
        cursor: pointer;
    }

    tbody :global(tr.clickable):hover {
        --dt-row-tint: color-mix(in oklab, var(--lf-selected) 50%, transparent);
    }

    tbody :global(tr.clickable.selected) {
        --dt-row-tint: var(--lf-selected);
    }

    /* Row whose lot-analysis panel is currently open (F9): the steady selection tint, no pulse (persistent
       state, not a navigation flash) */
    tbody :global(tr.row-analyzed) {
        --dt-row-tint: var(--lf-selected);
    }

    tbody :global(tr.row-analyzed):hover {
        --dt-row-tint: color-mix(in oklab, var(--lf-checked) 20%, transparent);
    }

    @keyframes pulse-highlight {
        0%,
        100% {
            --dt-row-tint: var(--lf-selected);
        }
        50% {
            --dt-row-tint: color-mix(in oklab, var(--lf-checked) 20%, transparent);
        }
    }

    /* Highlighted row (navigateToRowId): the selection tint, pulsing three times on a deeper one. It wins over every
       other state, the pointer included, by coming last at the same specificity: an `!important` beats an animation,
       and stopped this pulse from its introduction (12/07/2026) to 19/10/2026. */
    tbody :global(tr.highlighted),
    tbody :global(tr.highlighted):hover {
        --dt-row-tint: var(--lf-selected);
    }

    tbody :global(tr.highlighted) {
        animation: pulse-highlight 0.6s ease-in-out 3;
    }

    :global(tr.highlighted) td {
        border-bottom-color: color-mix(in oklab, var(--lf-checked) 20%, transparent);
    }

    /* On the selection tint the muted text falls under 4.5:1 (design system, rule 5; TC-15): inside a selected,
       highlighted or analyzed row, a muted caption, a cell's own or one an HtmlCell writes, turns secondary. */
    tbody :global(tr.selected) :global(.text-lf-muted),
    tbody :global(tr.highlighted) :global(.text-lf-muted),
    tbody :global(tr.row-analyzed) :global(.text-lf-muted) {
        color: var(--lf-text-secondary);
    }

    @media (prefers-reduced-motion: reduce) {
        tbody :global(tr.highlighted) {
            animation: none;
        }
    }

    td {
        padding: 0.625rem 0.5rem;
        font-size: 0.875rem;
        color: var(--lf-text-primary);
        border-bottom: 1px solid var(--lf-border-subtle);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 0;
    }

    .td-data {
        word-break: break-word;
    }

    /* Allow SimpleSelect dropdown to overflow outside td */
    td:has(:global(.cell-editable-select-wrapper)) {
        overflow: visible;
    }

    /* Ensure table rows with open SimpleSelect dropdown are on top */
    tbody tr:has(:global(.cell-editable-select-wrapper)) {
        position: relative;
        z-index: 1;
    }

    /* When dropdown is actually open (focus-within), bump z-index above sibling rows */
    tbody tr:focus-within {
        z-index: 10;
    }

    /* The row's two layers, card and tint, so the cell is opaque and the same colour as its row (see «Body»). */
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

    .td-empty,
    .td-loading {
        text-align: center;
        padding: 3rem 2rem;
        color: var(--lf-text-muted);
        background: var(--lf-surface-card);
        height: 230px;
        vertical-align: middle;
    }

    .loading-spinner {
        display: inline-block;
        width: 1.5rem;
        height: 1.5rem;
        border: 2px solid var(--lf-surface-neutral);
        border-top-color: var(--lf-link);
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
    .disabled-select-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        margin: 0 auto;
        color: var(--lf-danger);
        opacity: 0.7;
    }

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
        border: 1px solid var(--lf-border-input);
        border-radius: 3px;
        background: var(--lf-surface-field);
    }

    :global(.check-icon) {
        color: var(--lf-checked);
    }

    :global(.check-icon.checked) {
        color: var(--lf-checked);
    }

    :global(.check-icon.partial) {
        color: var(--lf-text-muted);
    }

    /* Actions */
    .actions-row {
        display: flex;
        justify-content: center;
    }

    .row-actions-btn {
        display: inline-flex;
        height: 1.75rem;
        width: 1.75rem;
        align-items: center;
        justify-content: center;
        border: 0;
        border-radius: 9999px;
        background: transparent;
        color: var(--lf-text-muted);
        cursor: pointer;
        font-size: 1.25rem;
        line-height: 1;
        transition:
            background-color 0.15s,
            color 0.15s;
    }

    .row-actions-btn:hover,
    .row-actions-btn:focus-visible {
        background: var(--lf-surface-neutral);
        color: var(--lf-text-primary);
        outline: none;
    }

    /* Phones: the pinned selection and actions columns scroll with the table, header and cells alike (D-Y17, C-38).
       Each selector is one class more specific than the pin it undoes. A header cell keeps `position: sticky` and its
       `top: 0`, so the header row still sticks inside its scroll area: only the horizontal pin goes. */
    @media (max-width: 768px) {
        .datatable .td-select,
        .datatable .td-actions {
            position: static;
        }
        .datatable .th-select,
        .datatable .th-actions.th-fixed {
            left: auto;
            right: auto;
        }
    }

    /* Row status classes (used via getRowClass prop) */
    /* A deleted row fades its content, never its background (TC-21): a translucent cell let the content scrolling under
       a fixed cell show through. The cell is opaque, the danger tint at the strength the old 0.55 opacity gave it over
       the card; a veil of that background at 45 % over the content fades it as before, and lets the pointer through. */
    :global(tr.row-deleted) td {
        --dt-deleted-bg: color-mix(in srgb, var(--lf-danger-soft) 55%, var(--lf-surface-card));
        background: var(--dt-deleted-bg) !important;
    }

    :global(tr.row-deleted) td:not(.td-fixed) {
        position: relative;
    }

    :global(tr.row-deleted) td::after {
        content: '';
        position: absolute;
        inset: 0;
        background: color-mix(in srgb, var(--dt-deleted-bg) 45%, transparent);
        pointer-events: none;
    }

    /* Phones unpin the selection and actions cells (`position: static`): the veil needs its cell positioned there too. */
    @media (max-width: 768px) {
        :global(tr.row-deleted) td.td-fixed {
            position: relative;
        }
    }

    :global(tr.row-edited) td {
        background: var(--lf-info-soft) !important;
    }

    :global(tr.row-appended) td {
        background: var(--lf-success-soft) !important;
    }

    :global(tr.row-todo-blocker) td {
        background: var(--lf-danger-soft) !important;
    }

    :global(tr.row-stale) td {
        /* The warning tint, deeper with the stale days: --stale-opacity runs 0.04–0.4 (DataEditor), so the row
           reaches the whole tint at 0.4. */
        background: color-mix(in oklab, var(--lf-warning-soft) calc(var(--stale-opacity, 0.04) * 250%), transparent) !important;
    }
</style>
