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
 * Image thumbnail cell - shows preview with fallback to icon
 */
export interface ImageCell {
    type: 'image';
    /** Image source URL (use ?img_preview= for thumbnails) */
    src: string;
    /** Alt text */
    alt: string;
    /** Optional text displayed next to the image */
    text?: string;
    /** Fallback icon component (shown if image fails to load) */
    fallbackIcon?: AnyComponent;
    /** Size in pixels (default: 32) */
    size?: number;
    /** Whether to show as circle (default: false) */
    circle?: boolean;
}

/**
 * Editable number cell — renders an inline <input type="number">.
 * Used by DataEditor for rate editing, etc.
 */
export interface EditableNumberCell {
    type: 'editable-number';
    /** Current value (null = empty) */
    value: number | null;
    /** Step for input increment (default: 1) */
    step?: number;
    /** Minimum allowed value */
    min?: number;
    /** Maximum allowed value */
    max?: number;
    /** Placeholder text when value is null */
    placeholder?: string;
    /** Callback when value changes (blur or Enter) */
    onchange: (newValue: number | null) => void;
}

/**
 * Editable text cell — renders an inline <input type="text">.
 * Used for identifier values, names, etc.
 */
export interface EditableTextCell {
    type: 'editable-text';
    /** Current value */
    value: string;
    /** Placeholder text when value is empty */
    placeholder?: string;
    /** Max length */
    maxLength?: number;
    /** Callback when value changes (blur or Enter) */
    onchange: (newValue: string) => void;
}

/**
 * HTML snippet cell — renders raw HTML content.
 * Used for colored values (pos/neg formatting), inline badges, etc.
 */
export interface HtmlCell {
    type: 'html';
    html: string;
    /**
     * Optional tooltip wrapper. When provided, the HTML content is rendered
     * inside a <Tooltip> from `$lib/components/ui/Tooltip.svelte` (instant
     * hover, click on mobile, viewport-aware positioning, KaTeX-capable).
     * Prefer this over the native HTML `title` attribute for any non-trivial
     * explanatory text — it integrates with the design system and is testable.
     */
    tooltip?: {
        text: string;
        position?: 'top' | 'bottom' | 'left' | 'right';
        maxWidth?: string;
    };
}

/**
 * Editable select cell — renders an inline <select> dropdown.
 * Used for identifier type, sector/country selection in distribution editors, etc.
 */
export interface EditableSelectCell {
    type: 'editable-select';
    /** Current selected value */
    value: string;
    /** Available options */
    options: Array<{value: string; label: string}>;
    /** Callback when selection changes */
    onchange: (newValue: string) => void;
}

/**
 * Editable checkbox cell — renders an inline checkbox toggle.
 * Used for boolean flags like generate_interest in schedule editors.
 */
export interface EditableCheckboxCell {
    type: 'editable-checkbox';
    /** Current checked state */
    value: boolean;
    /** Callback when checkbox changes */
    onchange: (newValue: boolean) => void;
}

/**
 * All possible cell content types
 */
export type CellContent = SimpleCellContent | IconTextCell | BadgeCell | DateCell | SizeCell | LinkCell | CustomCell | ImageCell | EditableNumberCell | EditableTextCell | HtmlCell | EditableSelectCell | EditableCheckboxCell;

// ============ Column Definition Types ============

/**
 * Column data type - determines filter UI and sorting behavior
 e * - 'size' is special for byte sizes with logarithmic slider
 */
export type ColumnType = 'text' | 'number' | 'date' | 'enum' | 'multi-enum' | 'size' | 'currency-stack' | 'custom';

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

    /**
     * For `currency-stack` columns: extract the currency code + amount of a
     * row. Returns `null` when the cell has no currency value (filter excludes
     * the row by default unless the filter list is empty).
     */
    getCurrencyValue?: (row: T) => {code: string; amount: number} | null;

    /**
     * For `multi-enum` columns: extract the array of values associated with
     * a row (e.g. tags). When the row has none, return `[]`. Filter logic:
     * row passes if `selected` is empty OR ∃ overlap with the row's array.
     */
    getMultiValue?: (row: T) => string[];

    /** URL parameter key for deep-linking filters (default: column id) */
    urlKey?: string;

    /** If true, column is hidden by default (user can toggle via column visibility) */
    hiddenByDefault?: boolean;

    /** Optional tooltip text shown on hover over the header (info icon) */
    headerTooltip?: string | (() => string);

    /** Optional URL — clicking the info icon navigates to this documentation page */
    headerTooltipUrl?: string | (() => string);
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

    /** Label - string, i18n function, or row-derived (used as button title attr) */
    label: string | (() => string) | ((row: T) => string);

    /** Click handler */
    onClick: (row: T) => void | Promise<void>;

    /** Visual variant */
    variant?: 'default' | 'danger';

    /** Conditionally show/hide action */
    visible?: (row: T) => boolean;

    /** Disable action conditionally */
    disabled?: (row: T) => boolean;

    /** Dynamic CSS class for the icon (e.g. 'animate-spin' when loading) */
    iconClass?: (row: T) => string;

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
export type FilterValue = TextFilter | NumberFilter | DateFilter | EnumFilter | MultiEnumFilter | SizeFilter | CurrencyStackFilter;

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

/**
 * Multi-select enum filter — same semantics as EnumFilter but the popover UI
 * is a checkbox checklist with a search-box (no select-all/clear-all chips).
 * Used when the option set is dynamic (e.g. tags derived from currently
 * loaded rows). Filter logic: row passes if `selected` is empty or any of
 * its values intersects the row's value set.
 */
export interface MultiEnumFilter {
    type: 'multi-enum';
    selected: string[];
}

/**
 * Currency-stack filter — a stack of {currency, min?, max?} ranges OR-ed
 * together. Designed for cells that carry both a currency code and an amount
 * (e.g. Transactions `cash`, FX rates, Asset prices). The column must declare
 * `getCurrencyValue: (row) => { code, amount } | null` for filtering to work.
 * Filter logic: row passes if `items` is empty OR ∃ item whose code matches
 * the row's currency code AND the row amount is within `[min, max]`.
 */
export interface CurrencyStackFilter {
    type: 'currency-stack';
    items: Array<{code: string; min?: number; max?: number}>;
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

    /**
     * Selection mode:
     * - 'multi': checkbox multi-select (default when enableSelection=true)
     * - 'single': click row to select one at a time, no checkboxes
     * - 'none': no selection (same as enableSelection=false)
     */
    selectionMode?: 'multi' | 'single' | 'none';

    /** Selection column width (default: '5%') — only used in 'multi' mode */
    selectionColumnWidth?: string;

    /** Called when selection changes (multi: array of IDs, single: array with 0 or 1 ID) */
    onSelectionChange?: (selectedIds: string[]) => void;

    /** Currently selected row ID (for single mode, controlled from parent) */
    selectedRowId?: string | null;

    /** Called when a row is clicked (any mode) */
    onRowClick?: (row: T) => void;

    /** Called when a row is double-clicked */
    onRowDoubleClick?: (row: T) => void;

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
