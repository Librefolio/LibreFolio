/**
 * DataTable Types
 *
 * Generic type definitions for the reusable DataTable component.
 * These types allow full control over columns, actions, and behavior.
 */
import type {ContextMenuItem} from '$lib/components/ui/ContextMenu.svelte';

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
 * Editable number cell — renders a text input that accepts "," or "." as the
 * decimal separator and steps with the arrow keys.
 * Used by DataEditor for rate editing, etc.
 */
export interface EditableNumberCell {
    type: 'editable-number';
    /** Current value (null = empty) */
    value: number | null;
    /** Arrow-key increment (default: 1). 'any' means the arrows step by 1 while
     *  typing stays free of any step constraint. */
    step?: number | 'any';
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
    /** A fixed unit drawn beside the field, inside the cell («%», «years»): plan 68, E10c3 */
    unit?: string;
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
     * inside a <Tooltip> from `$lib/components/ui/feedback/Tooltip.svelte` (instant
     * hover, click on mobile, viewport-aware positioning, KaTeX-capable).
     * Prefer this over the native HTML `title` attribute for any non-trivial
     * explanatory text — it integrates with the design system and is testable.
     */
    tooltip?: {
        text?: string;
        /** Rich HTML tooltip content (mutually exclusive with text) */
        html?: string;
        position?: 'top' | 'bottom' | 'left' | 'right';
        maxWidth?: string;
    };
    /** Optional click handler. When provided, the cell content is wrapped in a button. */
    onClick?: () => void;
    /** Optional test id for clickable HTML cells. */
    testId?: string;
}

/**
 * Editable select cell — renders the project's `SimpleSelect` inline (`DataTableCellContent.svelte`), never a native
 * `<select>`: a choice inside a table cell follows the selector rule (M5). For a selector with search or another shape,
 * use a `custom` cell with the project's component, as `TargetInputCell` does.
 * Used for identifier type, sector/country selection in distribution editors, etc.
 */
export interface EditableSelectCell {
    type: 'editable-select';
    /** Current selected value */
    value: string;
    /** Available options */
    options: Array<{value: string; label: string}>;
    /** Text shown while no option is chosen (plan 68, E10c2) */
    placeholder?: string;
    /** Stable selector: the select gets `<testId>`, each option `<testId>-option-<value>` (plan 68, E10c2) */
    testId?: string;
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
    /** Disable toggling and render in a muted state. */
    disabled?: boolean;
    /** Callback when checkbox changes */
    onchange: (newValue: boolean) => void;
}

/**
 * Editable date cell (plan 68, E10a) — the app's `SingleDatePicker` (typed or picked from its calendar, in the app's
 * language; never a native date input). The value is an ISO date (`yyyy-mm-dd`); future dates are allowed. Used by the
 * asset profile (maturity, inception date…).
 */
export interface EditableDateCell {
    type: 'editable-date';
    /** Current value, ISO `yyyy-mm-dd` (null = empty) */
    value: string | null;
    /** Callback with the date chosen, or null when the field is cleared */
    onchange: (newValue: string | null) => void;
}

/**
 * Editable amount cell (plan 68, E10a) — a decimal number and its currency, side by side. The number is typed as text
 * and handed over as decimal TEXT (`"55173000000"`, `"0.0000001"`), never a float, so an amount stays exact.
 */
export interface EditableAmountCell {
    type: 'editable-amount';
    /** Current amount as decimal text (null = empty) */
    amount: string | null;
    /** Current currency code (null = none chosen) */
    currency: string | null;
    /** The currencies offered */
    currencies: Array<{value: string; label: string}>;
    /** Placeholder of the number when empty */
    placeholder?: string;
    /** Accessible names of the number and of the currency choice */
    ariaLabel?: string;
    currencyAriaLabel?: string;
    /** Callback on blur, Enter or a currency picked: the amount (null when emptied) and the currency */
    onchange: (newValue: {amount: string | null; currency: string | null}) => void;
}

/**
 * All possible cell content types
 */
export type CellContent = SimpleCellContent | IconTextCell | BadgeCell | DateCell | SizeCell | LinkCell | CustomCell | ImageCell | EditableNumberCell | EditableTextCell | HtmlCell | EditableSelectCell | EditableCheckboxCell | EditableDateCell | EditableAmountCell;

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
    /** Optional icon URL rendered beside the label in filter dropdowns */
    iconUrl?: string;
    /** Optional ordered icon fallback chain for filter dropdowns */
    iconCandidates?: string[];
    /** Fallback colored dot (CSS color) shown when iconUrl is absent */
    dotColor?: string;
    /** Optional count of rows matching this value (computed by DataTable, shown in filter UI) */
    count?: number;
    /** Extra text searched in the filter search box (e.g. ticker + ISIN) — not displayed in UI */
    searchText?: string;
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
     * For `currency-stack` columns: pre-computed list of available currency
     * codes from the full dataset (provided by parent). When present, DataTable
     * uses this instead of dynamically computing from the current visible rows.
     */
    currencyOptions?: string[];

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

    /** Optional tooltip text shown on hover over the header label; the info icon appears only with `headerTooltipUrl` */
    headerTooltip?: string | (() => string);

    /** Optional URL — clicking the info icon navigates to this documentation page */
    headerTooltipUrl?: string | (() => string);

    /** How the documentation trigger opens its URL. Default: direct link. */
    headerTooltipLinkMode?: 'direct' | 'gesture';

    /** For number columns: force integer-only filter (step=1, round slider). Default: false. */
    integerOnly?: boolean;

    /** Pin column to left or right edge (sticky positioning). Default: undefined (not pinned). */
    pinned?: 'left' | 'right';

    /** Cell and header text alignment. Default: 'left'. */
    align?: 'left' | 'center' | 'right';

    /**
     * Optional HTML content for the column header cell.
     * When provided, rendered with {@html} instead of plain `header` text.
     * Useful for responsive show/hide via Tailwind classes (e.g. `hidden sm:inline`).
     * The `header` field is still required (used as fallback in ColumnVisibility dropdown).
     */
    headerHtml?: string | (() => string);

    /**
     * Display name used in ColumnVisibilityToggle dropdown and other UI that lists columns.
     * Falls back to `header` when not set.
     * Set this when `header` is intentionally empty (icon-only or pinned status columns)
     * to keep the dropdown readable. Columns where both header and displayName resolve to ''
     * are hidden from the visibility dropdown entirely.
     */
    displayName?: string | (() => string);
}

export type FooterCellContent = SimpleCellContent | HtmlCell;

export type FooterCells<T> = Record<string, FooterCellContent> | ((rows: T[], selectedRows: T[], visibleColumns: ColumnDef<T>[]) => Record<string, FooterCellContent>);

// ============ Action Types ============

/**
 * Action for a single row
 *
 * @typeParam T - The row data type
 */
export interface RowAction<T> extends Omit<ContextMenuItem, 'id' | 'label' | 'blocked' | 'title' | 'testid' | 'iconClass' | 'labelClass'> {
    /** Unique action identifier */
    id: string;

    /** Icon component */
    icon: AnyComponent;

    /** Menu label - string, i18n function, or row-derived */
    label: string | (() => string) | ((row: T) => string);

    /** Click handler */
    onClick: (row: T) => void | Promise<void>;

    /** Conditionally show/hide action */
    visible?: (row: T) => boolean;

    /**
     * Why the action is blocked on this row, or null when it is not (77 SEL-M, Q-SEL-12): then it is off, reachable, and
     * the row menu says why. An action that makes no sense on a row is not off: it is hidden, with `visible`.
     */
    blocked?: (row: T) => SelectionActionBlock | null;

    /** Dynamic CSS class for the icon (e.g. 'animate-spin' when loading) */
    iconClass?: (row: T) => string;

    /** Optional tooltip/title text, static or row-derived */
    title?: string | ((row: T) => string);

    /** Optional data-testid, static or row-derived */
    testid?: string | ((row: T) => string);

    /** Optional CSS class for the label, static or row-derived */
    labelClass?: string | ((row: T) => string);

    /** Require confirmation modal before action */
    requireConfirm?: boolean;

    /** Confirmation message - string or function */
    confirmMessage?: string | ((row: T) => string);
}

export type RowActions<T> = RowAction<T>[] | ((row: T) => RowAction<T>[]);

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

    /** The confirmation's button, when «Confirm» is too generic for it (81 U21: «Download»). */
    confirmText?: string | (() => string);

    /** Minimum number of rows the action must take, under which it is hidden (the rows it can take, `appliesTo`). */
    minSelection?: number;

    /** The button's test id, when a table keeps one of its own (77 SEL-E: the Bulk's). Absent: `toolbar-action-<id>`. */
    testid?: string;

    // ---- The rule of the selection panel (plan 77, SEL-A; `resolveSelectionAction`) ----

    /** The word shown where the bar has little room, when it is shorter than the label (the label stays its name). */
    shortLabel?: string | (() => string);

    /** The main action of the bar: drawn solid. */
    primary?: boolean;

    /** CSS class applied to the icon (e.g. 'animate-spin' while it runs). */
    iconClass?: string;

    /** Whether the action can take this row. Absent: every selected row. It acts on those rows only, and shows their number. */
    appliesTo?: (row: T) => boolean;

    /** Whether, on the rows it would take, the action makes no sense here (Q-SEL-17: Balance at 100 %): then it is hidden. */
    pointless?: (rows: T[]) => boolean;

    /**
     * Why the action is blocked on the rows it would take, or null when it is not: then it is off, and the hint says why
     * (Q-SEL-9, 66 F7-a). An action is never off without a reason: the type asks for both.
     */
    blocked?: (rows: T[]) => SelectionActionBlock | null;
}

/** Why a bulk action is off: the words the reader sees, and a code tests read (`data-disabled-reason`). */
export interface SelectionActionBlock {
    hint: string | (() => string);
    reason: string;
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

    /** Actions column width (default: '64px') */
    actionsColumnWidth?: string;

    /** Accessible label for the native row-actions kebab button. Defaults to table.actions. */
    actionsLabel?: string;

    /** Row actions - array or row-derived callback. Rendered by DataTable as a kebab menu. */
    rowActions?: RowActions<T>;

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

    /** Optional aggregate footer. Receives selected rows, or filtered rows when nothing is selected. */
    footerCells?: FooterCells<T>;
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
