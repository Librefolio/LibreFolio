<!--
  DataEditor — Generic dual-mode data editor (CSV text ↔ DataTable) with status tracking.

  Features:
  - Dual view: CSV text (via CsvEditor) and interactive DataTable
  - Row status tracking: original, edited, deleted, appended
  - DataTable: sorting, pagination, column filters, editable cells, row actions
  - Bulk operations: select multiple rows + mark as deleted
  - Import CSV via DataImportModal
  - Add row (today's date)
  - Configurable columns via ColumnDef[]
  - Dirty row emission for save/preview
  - Async CSV conversion (chunked to avoid long-running handlers)

  Uses Svelte 5 runes ($state, $derived, $props, $effect).
-->
<script lang="ts">
    import {tick} from 'svelte';
    import {Plus, Upload, Trash2, Undo2} from 'lucide-svelte';
    import CsvEditor from '$lib/components/fx/CsvEditor.svelte';
    import type {ParsedRow} from '$lib/components/fx/CsvEditor.svelte';
    import DataImportModal from './DataImportModal.svelte';
    import type {ColumnDef, DataRow} from './DataEditorTypes';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef as DTColumnDef, RowAction as DTRowAction} from '$lib/components/table/types';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Configurable data columns (e.g., [{key:'rate',...}] for FX) */
        columns: ColumnDef[];
        /** All rows (bindable) */
        rows?: DataRow[];
        /** Current view mode */
        viewMode?: 'text' | 'table';
        /** Read-only mode */
        readonly?: boolean;
        /** Base currency for CSV header */
        baseCurrency?: string;
        /** Quote currency for CSV header */
        quoteCurrency?: string;
        /** Emits only dirty rows (status !== 'original') */
        onchange?: (dirtyRows: DataRow[]) => void;
        /** Emits when view mode changes */
        onviewmodechange?: (mode: 'text' | 'table') => void;
    }

    let {
        columns,
        rows = $bindable([]),
        viewMode = $bindable('table'),
        readonly: isReadonly = false,
        baseCurrency = '',
        quoteCurrency = '',
        onchange,
        onviewmodechange,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let csvEditor: CsvEditor | undefined = $state(undefined);
    let csvValue = $state('');
    let importModalOpen = $state(false);
    let csvConverting = $state(false);

    // =========================================================================
    // Derived
    // =========================================================================

    let csvHeader = $derived(
        baseCurrency && quoteCurrency
            ? `date;${baseCurrency.toLowerCase()};${quoteCurrency.toLowerCase()};base2quote`
            : `date;base;quote;base2quote`
    );

    /** Dirty rows for emission */
    let dirtyRows = $derived(rows.filter(r => r.status !== 'original'));

    /** Counts for toolbar */
    let modifiedCount = $derived(rows.filter(r => r.status === 'edited').length);
    let deletedCount = $derived(rows.filter(r => r.status === 'deleted').length);
    let appendedCount = $derived(rows.filter(r => r.status === 'appended').length);

    /** Can switch to table view? (no CSV errors or duplicates) */
    let canSwitchToTable = $state(true);
    let switchBlockReason = $state('');

    /** Sorted rows for DataTable display */
    let sortedRows = $derived(
        [...rows].sort((a, b) => a.date.localeCompare(b.date))
    );

    // =========================================================================
    // DataTable Column Definitions
    // =========================================================================

    /** Get abbreviated weekday for a date string */
    function weekday(dateStr: string): string {
        try {
            const d = new Date(dateStr + 'T00:00:00Z');
            return d.toLocaleDateString('en-US', {weekday: 'short', timeZone: 'UTC'});
        } catch {
            return '';
        }
    }

    /** Row background class based on status */
    function rowBgClass(row: DataRow): string {
        switch (row.status) {
            case 'edited': return 'row-edited';
            case 'deleted': return 'row-deleted';
            case 'appended': return 'row-appended';
            default: return '';
        }
    }

    let dtColumns: DTColumnDef<DataRow>[] = $derived.by(() => {
        const cols: DTColumnDef<DataRow>[] = [
            {
                id: 'date',
                header: 'Date',
                type: 'text',
                cell: (r) => ({
                    type: 'html',
                    html: `<span class="font-mono text-xs">${r.date} <span class="ml-1 text-gray-400 dark:text-gray-500 text-[10px]">${weekday(r.date)}</span></span>`,
                }),
                getValue: (r) => r.date,
                sortable: true,
                filterable: false,
                width: 160,
            },
        ];

        // Add data columns (e.g., 'rate')
        for (const col of columns) {
            if (col.editable && !isReadonly) {
                cols.push({
                    id: col.key,
                    header: col.label,
                    type: 'number',
                    cell: (r) => ({
                        type: 'editable-number',
                        value: r.values[col.key] !== undefined && r.values[col.key] !== null ? Number(r.values[col.key]) : null,
                        step: col.step ?? 0.0001,
                        placeholder: col.placeholder ?? '',
                        onchange: (newValue) => handleCellEditByDate(r.date, col.key, newValue),
                    }),
                    getValue: (r) => Number(r.values[col.key] ?? 0),
                    sortable: true,
                    filterable: false,
                    width: 140,
                });
            } else {
                cols.push({
                    id: col.key,
                    header: col.label,
                    type: 'number',
                    cell: (r) => ({
                        type: 'html',
                        html: `<span class="text-xs font-mono text-gray-600 dark:text-gray-400">${r.values[col.key] ?? '—'}</span>`,
                    }),
                    getValue: (r) => Number(r.values[col.key] ?? 0),
                    sortable: true,
                    filterable: false,
                    width: 140,
                });
            }
        }

        // Status column (hidden by default via column visibility)
        cols.push({
            id: 'status',
            header: 'Status',
            type: 'enum',
            enumOptions: [
                {value: 'original', label: 'Original'},
                {value: 'edited', label: 'Edited'},
                {value: 'deleted', label: 'Deleted'},
                {value: 'appended', label: 'New'},
            ],
            cell: (r) => ({
                type: 'badge',
                text: r.status === 'appended' ? 'New' : r.status.charAt(0).toUpperCase() + r.status.slice(1),
                variant: r.status === 'original' ? 'default' : r.status === 'edited' ? 'info' : r.status === 'deleted' ? 'error' : 'success',
            }),
            getValue: (r) => r.status,
            sortable: true,
            filterable: true,
            width: 100,
        });

        return cols;
    });

    /** Row actions for DataTable */
    let dtRowActions: DTRowAction<DataRow>[] = $derived.by(() => {
        if (isReadonly) return [];
        return [
            {
                id: 'delete',
                icon: Trash2,
                label: 'Delete',
                variant: 'danger' as const,
                onClick: (row) => handleStatusChangeByDate(row.date, 'deleted'),
                visible: (row) => row.status !== 'deleted',
            },
            {
                id: 'revert',
                icon: Undo2,
                label: 'Revert',
                variant: 'default' as const,
                onClick: (row) => handleStatusChangeByDate(row.date, 'revert'),
                visible: (row) => row.status === 'deleted' || row.status === 'edited' || row.status === 'appended',
            },
        ];
    });

    // =========================================================================
    // Sync CSV ↔ Rows
    // =========================================================================

    /** Convert rows to CSV text — async chunked to avoid long-running handlers */
    async function rowsToCsvAsync(): Promise<string> {
        const header = baseCurrency && quoteCurrency
            ? `date;${baseCurrency};${quoteCurrency};base2quote`
            : `date;base;quote;base2quote`;

        const activeRows = rows
            .filter(r => r.status !== 'deleted')
            .sort((a, b) => a.date.localeCompare(b.date));

        const CHUNK_SIZE = 500;
        const lines: string[] = [header];

        for (let i = 0; i < activeRows.length; i += CHUNK_SIZE) {
            const chunk = activeRows.slice(i, i + CHUNK_SIZE);
            const chunkLines = chunk.map(r => {
                const firstCol = columns[0];
                const val = r.values[firstCol?.key ?? 'rate'] ?? '';
                return `${r.date};${baseCurrency || 'BASE'};${quoteCurrency || 'QUOTE'};${val}`;
            });
            lines.push(...chunkLines);

            // Yield to the event loop between chunks
            if (i + CHUNK_SIZE < activeRows.length) {
                await new Promise(resolve => setTimeout(resolve, 0));
            }
        }

        return lines.join('\n');
    }

    /** Synchronous fallback for small datasets */
    function rowsToCsv(): string {
        const header = baseCurrency && quoteCurrency
            ? `date;${baseCurrency};${quoteCurrency};base2quote`
            : `date;base;quote;base2quote`;

        const dataLines = rows
            .filter(r => r.status !== 'deleted')
            .sort((a, b) => a.date.localeCompare(b.date))
            .map(r => {
                const firstCol = columns[0];
                const val = r.values[firstCol?.key ?? 'rate'] ?? '';
                return `${r.date};${baseCurrency || 'BASE'};${quoteCurrency || 'QUOTE'};${val}`;
            });

        return [header, ...dataLines].join('\n');
    }

    /** Convert CSV parsed rows to DataRow[] */
    function csvToRows(parsedRows: ParsedRow[]): DataRow[] {
        return parsedRows.map(pr => {
            const existing = rows.find(r => r.date === pr.date);
            const firstCol = columns[0];

            if (existing && existing.originalStatus === 'original') {
                const oldVal = existing.values[firstCol?.key ?? 'rate'];
                const newVal = pr.value;
                const isChanged = Number(oldVal) !== newVal;

                return {
                    ...existing,
                    status: isChanged ? 'edited' as const : 'original' as const,
                    values: {...existing.values, [firstCol?.key ?? 'rate']: newVal},
                    selected: false,
                };
            }

            return {
                date: pr.date,
                status: 'appended' as const,
                originalStatus: 'appended' as const,
                values: {[firstCol?.key ?? 'rate']: pr.value},
                selected: false,
            };
        });
    }

    // =========================================================================
    // View Mode Switching
    // =========================================================================

    async function switchToText() {
        csvConverting = true;
        await tick();
        try {
            // Use async chunked conversion for large datasets
            if (rows.length > 1000) {
                csvValue = await rowsToCsvAsync();
            } else {
                csvValue = rowsToCsv();
            }
        } finally {
            csvConverting = false;
        }
        viewMode = 'text';
        onviewmodechange?.('text');
    }

    function switchToTable() {
        if (!canSwitchToTable) return;
        viewMode = 'table';
        onviewmodechange?.('table');
    }

    function handleCsvValidChange(validRows: ParsedRow[], errors: number, duplicates: boolean) {
        canSwitchToTable = errors === 0 && !duplicates;
        if (errors > 0) {
            switchBlockReason = 'Fix validation errors before switching to table view';
        } else if (duplicates) {
            switchBlockReason = 'Fix duplicate dates before switching to table view';
        } else {
            switchBlockReason = '';
        }

        if (viewMode === 'text' && errors === 0 && !duplicates) {
            rows = csvToRows(validRows);
            emitDirty();
        }
    }

    // =========================================================================
    // Table Edit Handlers
    // =========================================================================

    function handleCellEditByDate(date: string, colKey: string, newValue: unknown) {
        const rowIdx = rows.findIndex(r => r.date === date);
        if (rowIdx < 0 || isReadonly) return;

        const row = rows[rowIdx];
        const oldValues = {...row.values};
        row.values[colKey] = newValue;

        if (row.originalStatus === 'original' && row.status !== 'deleted') {
            if (!row._originalValues) {
                row._originalValues = oldValues;
            }
            const allMatch = columns.every(c => {
                const orig = row._originalValues?.[c.key];
                const curr = row.values[c.key];
                return String(orig ?? '') === String(curr ?? '');
            });
            row.status = allMatch ? 'original' : 'edited';
        }

        rows = [...rows];
        emitDirty();
    }

    function handleStatusChangeByDate(date: string, newStatus: string) {
        const rowIdx = rows.findIndex(r => r.date === date);
        if (rowIdx < 0 || isReadonly) return;

        const row = rows[rowIdx];

        if (newStatus === 'deleted') {
            row.status = 'deleted';
        } else if (newStatus === 'revert') {
            if (row.originalStatus === 'original') {
                row.status = 'original';
                if (row._originalValues) {
                    row.values = {...row._originalValues};
                }
            } else if (row.originalStatus === 'appended') {
                rows = rows.filter((_, i) => i !== rowIdx);
                emitDirty();
                return;
            }
        }

        rows = [...rows];
        emitDirty();
    }

    function handleAddRow() {
        const today = new Date().toISOString().slice(0, 10);
        const newRow: DataRow = {
            date: today,
            status: 'appended',
            originalStatus: 'appended',
            values: Object.fromEntries(columns.map(c => [c.key, undefined])),
            selected: false,
        };
        rows = [...rows, newRow];
        emitDirty();
    }

    // =========================================================================
    // Bulk selection handler (for DataTable selection)
    // =========================================================================

    function handleBulkDelete(selectedIds: string[]) {
        for (const date of selectedIds) {
            const row = rows.find(r => r.date === date);
            if (row && row.status !== 'deleted') {
                row.status = 'deleted';
            }
        }
        rows = [...rows];
        emitDirty();
    }

    // =========================================================================
    // Import
    // =========================================================================

    function handleImport(importedRows: ParsedRow[]) {
        const firstCol = columns[0];
        for (const pr of importedRows) {
            const existingIdx = rows.findIndex(r => r.date === pr.date);
            if (existingIdx >= 0) {
                const existing = rows[existingIdx];
                if (existing.originalStatus === 'original') {
                    if (!existing._originalValues) {
                        existing._originalValues = {...existing.values};
                    }
                    existing.values[firstCol?.key ?? 'rate'] = pr.value;
                    existing.status = 'edited';
                } else {
                    existing.values[firstCol?.key ?? 'rate'] = pr.value;
                }
            } else {
                rows.push({
                    date: pr.date,
                    status: 'appended',
                    originalStatus: 'appended',
                    values: {[firstCol?.key ?? 'rate']: pr.value},
                    selected: false,
                });
            }
        }
        rows = [...rows];
        emitDirty();
    }

    // =========================================================================
    // Emit
    // =========================================================================

    function emitDirty() {
        onchange?.(dirtyRows);
    }

    // =========================================================================
    // Public API
    // =========================================================================

    /** Scroll to a specific date in the table or CSV view */
    export function scrollToDate(date: string) {
        if (viewMode === 'text' && csvEditor) {
            const csvLines = csvValue.split('\n');
            const lineIdx = csvLines.findIndex(l => l.startsWith(date));
            if (lineIdx >= 0) {
                csvEditor.scrollToLine(lineIdx + 1);
            }
        } else {
            tick().then(() => {
                const el = document.querySelector(`[data-date="${date}"]`);
                el?.scrollIntoView({behavior: 'smooth', block: 'center'});
            });
        }
    }
</script>

<!-- ========================================================================= -->
<!-- Toolbar -->
<!-- ========================================================================= -->

<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
    <div class="flex flex-wrap items-center justify-between gap-2 px-4 py-2 border-b border-gray-100 dark:border-slate-700">
        <!-- Left: View toggle + actions -->
        <div class="flex items-center gap-2">
            <!-- Segmented toggle: CSV / Table -->
            <div class="flex rounded-lg overflow-hidden border border-gray-200 dark:border-slate-600">
                <button
                    class="px-3 py-1.5 text-xs font-medium transition-colors
                        {viewMode === 'text'
                            ? 'bg-libre-green text-white'
                            : 'bg-white dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-600'}"
                    onclick={switchToText}
                    disabled={csvConverting}
                >
                    {#if csvConverting}
                        <span class="inline-flex items-center gap-1">
                            <svg class="animate-spin h-3 w-3" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" opacity="0.25"/><path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                            CSV
                        </span>
                    {:else}
                        CSV
                    {/if}
                </button>
                <button
                    class="px-3 py-1.5 text-xs font-medium transition-colors
                        {viewMode === 'table'
                            ? 'bg-libre-green text-white'
                            : canSwitchToTable
                                ? 'bg-white dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-600'
                                : 'bg-gray-100 dark:bg-slate-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'}"
                    onclick={switchToTable}
                    disabled={!canSwitchToTable}
                    title={canSwitchToTable ? '' : switchBlockReason}
                >Table</button>
            </div>

            {#if !isReadonly}
                <button
                    class="flex items-center gap-1 px-2.5 py-1.5 text-xs bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                    onclick={() => importModalOpen = true}
                >
                    <Upload size={13} /> Import CSV
                </button>

                {#if viewMode === 'table'}
                    <button
                        class="flex items-center gap-1 px-2.5 py-1.5 text-xs bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                        onclick={handleAddRow}
                    >
                        <Plus size={13} /> Add Row
                    </button>
                {/if}
            {/if}
        </div>

        <!-- Right: Counters -->
        <div class="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
            {#if modifiedCount > 0}
                <span class="text-blue-600 dark:text-blue-400">{modifiedCount} modified</span>
            {/if}
            {#if deletedCount > 0}
                <span class="text-red-600 dark:text-red-400">{deletedCount} deleted</span>
            {/if}
            {#if appendedCount > 0}
                <span class="text-emerald-600 dark:text-emerald-400">{appendedCount} new</span>
            {/if}
        </div>
    </div>

    <!-- ========================================================================= -->
    <!-- Content Area -->
    <!-- ========================================================================= -->

    <div class="max-h-[500px] overflow-y-auto">
        {#if viewMode === 'text'}
            <!-- CSV Text View -->
            <div class="p-2">
                <CsvEditor
                    bind:this={csvEditor}
                    bind:value={csvValue}
                    header={csvHeader}
                    readonly={isReadonly}
                    onvalidchange={handleCsvValidChange}
                    minHeight="300px"
                    placeholder="Paste CSV data here or use Import CSV..."
                />
            </div>
        {:else}
            <!-- DataTable View -->
            <DataTable
                data={sortedRows}
                columns={dtColumns}
                getRowId={(r) => r.date}
                storageKey="data-editor"
                enableSelection={!isReadonly}
                enableActions={!isReadonly}
                rowActions={dtRowActions}
                enableSorting={true}
                enableColumnFilters={true}
                enableColumnVisibility={true}
                enableColumnResize={true}
                enablePagination={true}
                defaultPageSize={50}
                pageSizeOptions={[25, 50, 100, 0]}
                getRowClass={rowBgClass}
                emptyMessage="No data. Use 'Add Row' or 'Import CSV' to add data."
            />
        {/if}
    </div>
</div>

<!-- Import Modal -->
<DataImportModal
    bind:open={importModalOpen}
    header={csvHeader}
    onimport={handleImport}
/>

<style>
    :global(.row-edited) {
        background-color: rgba(59, 130, 246, 0.05) !important;
    }
    :global(.row-deleted) {
        background-color: rgba(239, 68, 68, 0.05) !important;
        text-decoration: line-through;
        opacity: 0.6;
    }
    :global(.row-appended) {
        background-color: rgba(16, 185, 129, 0.05) !important;
    }
    :global(.dark .row-edited) {
        background-color: rgba(59, 130, 246, 0.1) !important;
    }
    :global(.dark .row-deleted) {
        background-color: rgba(239, 68, 68, 0.1) !important;
    }
    :global(.dark .row-appended) {
        background-color: rgba(16, 185, 129, 0.1) !important;
    }
</style>
