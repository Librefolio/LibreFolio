/**
 * DataEditor — Barrel Export
 *
 * Generic dual-mode data editor (CSV text ↔ Table) with row-folding,
 * status tracking, and CSV import.
 *
 * @module components/ui/data-editor
 */

export {default as DataEditor} from './DataEditor.svelte';
export {default as DataImportModal} from './DataImportModal.svelte';
export type {ColumnDef, DataRow, GapRow, TableRow, RowStatus} from './DataEditorTypes';
export type {CsvColumnDef, ParsedRow} from './CsvEditor.svelte';
