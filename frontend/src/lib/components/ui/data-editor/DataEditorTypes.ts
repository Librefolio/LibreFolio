/**
 * DataEditor Types — Shared type definitions for the DataEditor component.
 *
 * Used by DataEditor.svelte, DataImportModal.svelte, and domain-specific wrappers
 * (e.g., FxDataEditorSection.svelte).
 *
 * @module components/ui/DataEditorTypes
 */

/** Status of a row in the DataEditor */
export type RowStatus = 'original' | 'edited' | 'deleted' | 'appended';

/** Definition of a data column (configurable per use-case) */
export interface ColumnDef {
    /** Unique key used in DataRow.values */
    key: string;
    /** Display label for column header */
    label: string;
    /** Data type for input rendering and validation */
    type: 'date' | 'number' | 'string' | 'enum' | 'currency';
    /** Whether the user can edit this column */
    editable: boolean;
    /** Whether a value is required (non-empty) */
    required: boolean;
    /** Number step for type 'number' inputs */
    step?: number;
    /** Minimum value for type 'number' inputs */
    min?: number;
    /** Maximum value for type 'number' inputs */
    max?: number;
    /** Placeholder text for empty cells */
    placeholder?: string;
    /** Options for type 'enum' — value shown in select, label for display, emoji prefix */
    enumOptions?: {value: string; label: string; emoji?: string; tooltip?: string; docsPath?: string}[];
}

/** A single row in the DataEditor */
export interface DataRow {
    /** Unique row identifier (prices: date, events: String(id) or UUID) */
    rowId: string;
    /** ISO date YYYY-MM-DD — always present */
    date: string;
    /** Current editing status */
    status: RowStatus;
    /** Original status when the row was loaded (to detect if it can be reverted) */
    originalStatus: 'original' | 'appended';
    /** Column values keyed by ColumnDef.key */
    values: Record<string, unknown>;
    /** Whether this row is selected for bulk operations */
    selected: boolean;
    /** Whether this row is read-only (e.g., auto-generated events) — can still be deleted */
    readonly?: boolean;
    /** Original values for revert (only set when status transitions from 'original') */
    _originalValues?: Record<string, unknown>;
    /** Number of stale days (backward-fill gap) — 0 or undefined means fresh data */
    staleDays?: number;
}

/** A folded gap placeholder in the table view */
export interface GapRow {
    type: 'gap';
    startDate: string;
    endDate: string;
    dayCount: number;
    expanded: boolean;
}

/** Union type for table rendering */
export type TableRow = (DataRow & {type: 'data'}) | GapRow;
