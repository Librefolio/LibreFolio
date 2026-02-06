/**
 * DataTable Types
 *
 * Generic type definitions for the reusable DataTable component.
 * These types allow full control over columns, actions, and behavior.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyComponent = any;

// ============ Cell Content Types ============

/**
 * Simple cell content types
 */
export type SimpleCellContent = string | number;

/**
 * Icon with text cell
 */
export interface IconTextCell {
    type: 'icon-text';
    icon: AnyComponent;
    text: string;
    iconClass?: string;
}

/**
 * Badge/chip cell
 */
export interface BadgeCell {
    type: 'badge';
    text: string;
    variant: 'default' | 'success' | 'warning' | 'error' | 'info';
    /** Custom style for CSS variables (e.g., for broker colors) */
    customStyle?: string;
}

/**
 * Date cell with optional format
 */
export interface DateCell {
    type: 'date';
    value: Date | string;
    format?: 'date' | 'datetime' | 'time' | 'relative';
}

/**
 * File size cell (auto-formatted)
 */
export interface SizeCell {
    type: 'size';
    bytes: number;
}

/**
 * Link cell
 */
export interface LinkCell {
    type: 'link';
    text: string;
    href: string;
    external?: boolean;
}

/**
 * Custom component cell
 */
export interface CustomCell {
    type: 'custom';
    component: AnyComponent;
    props: Record<string, unknown>;
}

/**
 * All possible cell content types
 */
export type CellContent =
    | SimpleCellContent
    | IconTextCell
    | BadgeCell
    | DateCell
    | SizeCell
    | LinkCell
    | CustomCell;

// ============ Column Definition Types ============

/**
 * Column data type - determines filter UI and sorting behavior
 e * - 'size' is special for byte sizes with logarithmic slider
 */
export type ColumnType = 'text' | 'number' | 'date' | 'enum' | 'size' | 'custom';

/**
 * Enum option for enum-type columns
 */
export interface EnumOption {
    value: string;
    label: string;
}

/**
 * Column definition for DataTable
 *
 * @typeParam T - The row data type
 */
export interface ColumnDef<T> {
    /** Unique column identifier */
    id: string;

    /** Column header - string or function for i18n */
    header: string | (() => string);

    /** Cell content renderer */
    cell: (row: T) => CellContent;

    /** Data type for sorting and filtering */
    type: ColumnType;

    /** For enum type: available options */
    enumOptions?: EnumOption[];

    /** Enable/disable sorting (default: true) */
    sortable?: boolean;

    /** Enable/disable filtering (default: true) */
    filterable?: boolean;

    /** Enable/disable resize (default: true) */
    resizable?: boolean;

    /** Initial width in pixels */
    width?: number;

    /** Minimum width in pixels */
    minWidth?: number;

    /** Maximum width in pixels */
    maxWidth?: number;

    /** Custom sort function (optional) */
    sortFn?: (a: T, b: T) => number;

    /** Get raw value for sorting/filtering (if different from cell render) */
    getValue?: (row: T) => unknown;

    /** URL parameter key for deep-linking filters (default: column id) */
    urlKey?: string;
}

// ============ Action Types ============

/**
 * Action for a single row
 *
 * @typeParam T - The row data type
 */
export interface RowAction<T> {
    /** Unique action identifier */
    id: string;

    /** Icon component */
    icon: AnyComponent;

    /** Label - string or function for i18n */
    label: string | (() => string);

    /** Click handler */
    onClick: (row: T) => void | Promise<void>;

    /** Visual variant */
    variant?: 'default' | 'danger';

    /** Conditionally show/hide action */
    visible?: (row: T) => boolean;

    /** Disable action conditionally */
    disabled?: (row: T) => boolean;

    /** Require confirmation modal before action */
    requireConfirm?: boolean;

    /** Confirmation message - string or function */
    confirmMessage?: string | ((row: T) => string);
}

/**
 * Bulk action for multiple selected rows
 *
 * @typeParam T - The row data type
 */
export interface BulkAction<T> {
    /** Unique action identifier */
    id: string;

    /** Icon component */
    icon: AnyComponent;

    /** Label - string or function for i18n */
    label: string | (() => string);

    /** Click handler with array of selected rows */
    onClick: (rows: T[]) => void | Promise<void>;

    /** Visual variant */
    variant?: 'default' | 'danger';

    /** Show confirmation modal before action */
    requireConfirm?: boolean;

    /** Confirmation message - string or function with count */
    confirmMessage?: string | ((count: number) => string);

    /** Minimum selection required to enable */
    minSelection?: number;
}

// ============ Filter Types ============

/**
 * Filter value union type
 */
export type FilterValue = TextFilter | NumberFilter | DateFilter | EnumFilter | SizeFilter;

/**
 * Active filter state for a column
 */
export interface ColumnFilter {
    columnId: string;
    type: ColumnType;
    value: FilterValue;
}

export interface TextFilter {
    type: 'text';
    value: string;
    matchMode: 'contains' | 'startsWith' | 'endsWith' | 'equals';
}

export interface NumberFilter {
    type: 'number';
    min?: number;
    max?: number;
}

export interface DateFilter {
    type: 'date';
    from?: string;
    to?: string;
}

export interface EnumFilter {
    type: 'enum';
    selected: string[];
}

export interface SizeFilter {
    type: 'size';
    minBytes?: number;
    maxBytes?: number;
}

// ============ DataTable Props ============

/**
 * Main DataTable component props
 *
 * @typeParam T - The row data type
 */
export interface DataTableProps<T> {
    /** Table data */
    data: T[];

    /** Column definitions - user controls content and behavior */
    columns: ColumnDef<T>[];

    /** Get unique ID from row (for selection tracking) */
    getRowId: (row: T) => string;

    /** LocalStorage key for persisting preferences */
    storageKey: string;

    // Selection
    /** Enable row selection (default: true) */
    enableSelection?: boolean;

    /** Selection column width (default: '5%') */
    selectionColumnWidth?: string;

    /** Called when selection changes */
    onSelectionChange?: (selectedIds: string[]) => void;

    // Actions
    /** Enable actions column (default: true) */
    enableActions?: boolean;

    /** Actions column width (default: '10%') */
    actionsColumnWidth?: string;

    /** Row actions - passed by user */
    rowActions?: RowAction<T>[];

    /** Bulk actions for multi-selection */
    bulkActions?: BulkAction<T>[];

    // Features
    /** Enable sorting (default: true) */
    enableSorting?: boolean;

    /** Enable per-column filters (default: true) */
    enableColumnFilters?: boolean;

    /** Enable column resize (default: true) */
    enableColumnResize?: boolean;

    /** Enable column reorder drag-drop (default: false, future) */
    enableColumnReorder?: boolean;

    /** Enable pagination (default: true) */
    enablePagination?: boolean;

    /** Enable column visibility toggle (default: true) */
    enableColumnVisibility?: boolean;

    // Pagination
    /** Default page size (default: 10) */
    defaultPageSize?: number;

    /** Page size options (default: [10, 25, 50, 100, 0]) 0 = all */
    pageSizeOptions?: number[];

    // Messages
    /** Message when no data */
    emptyMessage?: string;

    /** Message while loading */
    loadingMessage?: string;

    /** Loading state */
    isLoading?: boolean;
}

// ============ State Types ============

/**
 * Sorting state
 */
export interface SortState {
    columnId: string;
    direction: 'asc' | 'desc';
}

/**
 * Pagination state
 */
export interface PaginationState {
    pageIndex: number;
    pageSize: number;
}

/**
 * Column visibility state (columnId -> visible)
 */
export type VisibilityState = Record<string, boolean>;

/**
 * Column widths state (columnId -> width in px)
 */
export type ColumnWidthsState = Record<string, number>;

/**
 * Row selection state (rowId -> selected)
 */
export type SelectionState = Record<string, boolean>;

/**
 * Full table preferences state (for localStorage)
 */
export interface TablePreferences {
    columnVisibility: VisibilityState;
    columnWidths: ColumnWidthsState;
    columnOrder: string[];
    pageSize: number;
}
