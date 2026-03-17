/**
 * DataTable Components - Generic reusable table system
 *
 * This module exports components for building data tables with:
 * - User-controlled column definitions
 * - Row selection and bulk actions
 * - Sorting, filtering (Excel-style), resizing
 * - Pagination with floating balloon
 * - Persistent preferences
 *
 * @example
 * ```svelte
 * <script>
 *   import { DataTable, type ColumnDef, type RowAction } from '$lib/components/table';
 *   import { Download, Trash2 } from 'lucide-svelte';
 *
 *   const columns: ColumnDef<MyData>[] = [
 *     { id: 'name', header: 'Name', cell: (row) => row.name, type: 'text' },
 *     { id: 'size', header: 'Size', cell: (row) => ({ type: 'size', bytes: row.size }), type: 'number' },
 *   ];
 *
 *   const rowActions: RowAction<MyData>[] = [
 *     { id: 'download', icon: Download, label: 'Download', onClick: (row) => handleDownload(row) },
 *     { id: 'delete', icon: Trash2, label: 'Delete', onClick: (row) => handleDelete(row), variant: 'danger' },
 *   ];
 * </script>
 *
 * <DataTable
 *   data={files}
 *   {columns}
 *   {rowActions}
 *   getRowId={(f) => f.id}
 *   storageKey="myFiles"
 * />
 * ```
 */

// Main component
export {default as DataTable} from './DataTable.svelte';

// Sub-components (for advanced customization)
export {default as DataTablePagination} from './DataTablePagination.svelte';
export {default as DataTableToolbar} from './DataTableToolbar.svelte';
export {default as DataTableColumnFilter} from './DataTableColumnFilter.svelte';
export {default as ColumnVisibilityToggle} from './ColumnVisibilityToggle.svelte';
export {default as ConfirmModal} from '$lib/components/ui/ConfirmModal.svelte';

// Types
export type {
    // Cell content
    CellContent,
    SimpleCellContent,
    IconTextCell,
    BadgeCell,
    DateCell,
    SizeCell,
    LinkCell,
    CustomCell,
    ImageCell,
    // Column definition
    ColumnDef,
    ColumnType,
    EnumOption,
    // Actions
    RowAction,
    BulkAction,
    // Filters
    ColumnFilter,
    FilterValue,
    TextFilter,
    NumberFilter,
    DateFilter,
    EnumFilter,
    // State
    SortState,
    PaginationState,
    VisibilityState,
    ColumnWidthsState,
    SelectionState,
    TablePreferences,
    // Props
    DataTableProps,
} from './types';
