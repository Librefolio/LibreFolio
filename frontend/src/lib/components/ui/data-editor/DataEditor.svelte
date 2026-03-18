<!--
  DataEditor — Table-only data editor with status tracking.

  Features:
  - Row status tracking: original, edited, deleted, appended
  - DataTable: sorting, pagination, column filters, editable cells, row actions
  - Bulk operations: select multiple rows + mark as deleted
  - Import CSV via DataImportModal
  - Add row (today's date)
  - Configurable columns via ColumnDef[]
  - Dirty row emission for save/preview

  Uses Svelte 5 runes ($state, $derived, $props, $effect).
-->
<script lang="ts">
    import {tick} from 'svelte';
    import {Plus, Upload, Trash2, Undo2} from 'lucide-svelte';
    import type {ParsedRow} from '$lib/components/fx/CsvEditor.svelte';
    import DataImportModal from './DataImportModal.svelte';
    import type {ColumnDef, DataRow} from './DataEditorTypes';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import type {ColumnDef as DTColumnDef, RowAction as DTRowAction} from '$lib/components/table/types';
    import SingleDatePicker from '$lib/components/ui/SingleDatePicker.svelte';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Configurable data columns (e.g., [{key:'rate',...}] for FX) */
        columns: ColumnDef[];
        /** All rows (bindable) */
        rows?: DataRow[];
        /** Read-only mode */
        readonly?: boolean;
        /** Base currency for CSV header */
        baseCurrency?: string;
        /** Quote currency for CSV header */
        quoteCurrency?: string;
        /** Emits only dirty rows (status !== 'original') */
        onchange?: (dirtyRows: DataRow[]) => void;
    }

    let {
        columns,
        rows = $bindable([]),
        readonly: isReadonly = false,
        baseCurrency = '',
        quoteCurrency = '',
        onchange,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let importModalOpen = $state(false);
    let dataTableRef: DataTable<DataRow> | undefined = $state(undefined);
    let selectedIds = $state<string[]>([]);

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
            default: return (row.staleDays && row.staleDays > 0) ? 'row-stale' : '';
        }
    }

    /** Stale opacity: more stale days = more opaque yellow, capped at 0.4 */
    function staleOpacity(days: number): number {
        return Math.min(0.4, days * 0.04);
    }

    /** Row inline style for dynamic stale opacity */
    function rowStyleFn(row: DataRow): string {
        if (row.status === 'original' && row.staleDays && row.staleDays > 0) {
            return `--stale-opacity: ${staleOpacity(row.staleDays)}`;
        }
        return '';
    }

    /** Set of all existing dates for duplicate prevention */
    let existingDates = $derived(new Set(rows.map(r => r.date)));

    let dtColumns: DTColumnDef<DataRow>[] = $derived.by(() => {
        const cols: DTColumnDef<DataRow>[] = [
            {
                id: 'date',
                header: 'Date',
                type: 'date',
                cell: (r) => {
                    // Editable date for appended rows
                    if (r.status === 'appended' && !isReadonly) {
                        // disabledDates: all dates except this row's current date
                        const disabled = new Set(existingDates);
                        disabled.delete(r.date);
                        return {
                            type: 'custom',
                            component: SingleDatePicker,
                            props: {
                                value: r.date,
                                label: '',
                                compact: true,
                                disabledDates: disabled,
                                onchange: (newDate: string) => handleDateChange(r.date, newDate),
                            },
                        };
                    }
                    const wd = weekday(r.date);
                    const stale = r.staleDays && r.staleDays > 0 ? r.staleDays : 0;
                    if (stale > 0) {
                        return {
                            type: 'html',
                            html: `<span class="font-mono text-xs">${r.date} <span class="ml-1 text-gray-400 dark:text-gray-500 text-[10px]">${wd}</span> <span class="ml-1 text-[10px] text-amber-600 dark:text-amber-400" title="${stale} days stale">⚠️ ${stale}d</span></span>`,
                        };
                    }
                    return {
                        type: 'html',
                        html: `<span class="font-mono text-xs">${r.date} <span class="ml-1 text-gray-400 dark:text-gray-500 text-[10px]">${wd}</span></span>`,
                    };
                },
                getValue: (r) => r.date,
                sortable: true,
                filterable: true,
                width: 180,
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
                    filterable: true,
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
                    filterable: true,
                    width: 140,
                });
            }
        }

        // Status column (hidden by default via column visibility)
        cols.push({
            id: 'status',
            header: 'Status',
            type: 'enum',
            hiddenByDefault: true,
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
    // Table Edit Handlers
    // =========================================================================

    /** Change the date of an appended row (via SingleDatePicker) */
    function handleDateChange(oldDate: string, newDate: string) {
        if (oldDate === newDate) return;
        // Prevent duplicate dates
        if (rows.some(r => r.date === newDate && r.date !== oldDate)) return;
        const row = rows.find(r => r.date === oldDate && r.status === 'appended');
        if (!row) return;
        row.date = newDate;
        rows = [...rows];
        emitDirty();
    }

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
        // Calculate date: 1 day after the latest date in the dataset
        const existingDates = new Set(rows.map(r => r.date));
        const todayStr = new Date().toISOString().slice(0, 10);
        let newDate: string;
        if (rows.length > 0) {
            const sortedDates = [...existingDates].sort();
            const lastDate = sortedDates[sortedDates.length - 1];
            const d = new Date(lastDate + 'T00:00:00Z');
            d.setUTCDate(d.getUTCDate() + 1);
            newDate = d.toISOString().slice(0, 10);
            // Skip over existing dates
            while (existingDates.has(newDate)) {
                const d2 = new Date(newDate + 'T00:00:00Z');
                d2.setUTCDate(d2.getUTCDate() + 1);
                newDate = d2.toISOString().slice(0, 10);
            }
            // Cap to today: future dates cause sync errors ("End date cannot be in the future")
            if (newDate > todayStr) {
                newDate = todayStr;
                // If today is already occupied, search backwards for first free date
                while (existingDates.has(newDate)) {
                    const d3 = new Date(newDate + 'T00:00:00Z');
                    d3.setUTCDate(d3.getUTCDate() - 1);
                    newDate = d3.toISOString().slice(0, 10);
                }
            }
        } else {
            newDate = todayStr;
        }
        const newRow: DataRow = {
            date: newDate,
            status: 'appended',
            originalStatus: 'appended',
            values: Object.fromEntries(columns.map(c => [c.key, undefined])),
            selected: false,
        };
        rows = [...rows, newRow];
        emitDirty();
        // Navigate to the page containing the new row + scroll into view
        tick().then(() => {
            dataTableRef?.navigateToRowId(newRow.date);
        });
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

    /** Scroll to a specific date in the table */
    export function scrollToDate(date: string) {
        dataTableRef?.navigateToRowId(date);
    }
</script>

<!-- ========================================================================= -->
<!-- Toolbar -->
<!-- ========================================================================= -->

<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
    <div class="flex flex-wrap items-center justify-between gap-2 px-4 py-2 border-b border-gray-100 dark:border-slate-700">
        <!-- Left: actions -->
        <div class="flex items-center gap-2">
            {#if !isReadonly}
                <button
                    class="flex items-center gap-1 px-2.5 py-1.5 text-xs bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                    onclick={() => importModalOpen = true}
                >
                    <Upload size={13} /> Import CSV
                </button>
                <button
                    class="flex items-center gap-1 px-2.5 py-1.5 text-xs bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                    onclick={handleAddRow}
                >
                    <Plus size={13} /> Add Row
                </button>
            {/if}
        </div>

        <!-- Right: Selection bar + Counters + Column visibility -->
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
            {#if selectedIds.length > 0}
                <button
                    type="button"
                    class="flex items-center gap-1.5 px-2 py-1 rounded-md bg-libre-green/10 text-libre-green dark:bg-emerald-400/10 dark:text-emerald-400 font-medium hover:bg-libre-green/20 dark:hover:bg-emerald-400/20 transition-colors"
                    onclick={() => { dataTableRef?.clearSelection(); selectedIds = []; }}
                    title="Clear selection"
                >
                    {selectedIds.length} selected <span class="opacity-60">×</span>
                </button>
                <button
                    type="button"
                    class="flex items-center justify-center w-7 h-7 rounded-md bg-red-50 dark:bg-red-900/20 text-red-500 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors"
                    onclick={() => { handleBulkDelete(selectedIds); dataTableRef?.clearSelection(); selectedIds = []; }}
                    title="Delete selected"
                >
                    <Trash2 size={14} />
                </button>
            {/if}
            <ColumnVisibilityToggle tableRef={dataTableRef} />
        </div>
    </div>

    <!-- ========================================================================= -->
    <!-- Content Area — Table only -->
    <!-- ========================================================================= -->

    <div class="max-h-[500px] overflow-y-auto">
        <DataTable
            bind:this={dataTableRef}
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
            defaultPageSize={10}
            pageSizeOptions={[10, 25, 50, 100, 0]}
            getRowClass={rowBgClass}
            getRowStyle={rowStyleFn}
            emptyMessage="No data. Use 'Add Row' or 'Import CSV' to add data."
            showToolbar={false}
            onSelectionChange={(ids) => selectedIds = ids}
        />
    </div>
</div>

<!-- Import Modal -->
<DataImportModal
    bind:open={importModalOpen}
    header={csvHeader}
    onimport={handleImport}
/>

