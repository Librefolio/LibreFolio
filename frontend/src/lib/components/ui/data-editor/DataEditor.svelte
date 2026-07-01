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
    import type {Snippet} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import {Plus, Trash2, Undo2, Upload, Eye, EyeOff} from 'lucide-svelte';
    import type {ParsedRow} from './CsvEditor.svelte';
    import type {ColumnDef, DataRow} from './DataEditorTypes';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import type {ColumnDef as DTColumnDef, RowAction as DTRowAction} from '$lib/components/table/types';
    import SingleDatePicker from '$lib/components/ui/date/SingleDatePicker.svelte';
    import {CurrencySearchSelect} from '$lib/components/ui/select';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import ErasableNumberCell from './ErasableNumberCell.svelte';

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
        /** Snippet that renders the import modal. Receives {open, onimport} props via callback. */
        importModal?: Snippet<[{open: boolean; setOpen: (v: boolean) => void; onimport: (rows: ParsedRow[]) => void}]>;
        /** Emits only dirty rows (status !== 'original') */
        onchange?: (dirtyRows: DataRow[]) => void;
        /**
         * E.7 — default values applied to newly appended rows (via the "+" button).
         * Example: `{currency: 'USD'}` pre-fills the currency column for new price rows.
         * Keys not present in ColumnDef are ignored.
         */
        defaultRowValues?: Record<string, unknown>;
    }

    let {columns, rows = $bindable([]), readonly: isReadonly = false, importModal, onchange, defaultRowValues = {}}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let importModalOpen = $state(false);
    let dataTableRef: DataTable<DataRow> | undefined = $state(undefined);
    let selectedIds: string[] = $state([]);
    let hideStale = $state(false);

    // =========================================================================
    // Derived
    // =========================================================================

    /** Whether any rows have stale days (to decide if toggle should be shown) */
    let hasStaleRows = $derived(rows.some((r) => r.staleDays && r.staleDays > 0 && r.status === 'original'));

    /** Dirty rows for emission */
    let dirtyRows = $derived(rows.filter((r) => r.status !== 'original'));

    /** Counts for toolbar */
    let modifiedCount = $derived(rows.filter((r) => r.status === 'edited').length);
    let deletedCount = $derived(rows.filter((r) => r.status === 'deleted').length);
    let appendedCount = $derived(rows.filter((r) => r.status === 'appended').length);
    let staleCount = $derived(rows.filter((r) => r.staleDays && r.staleDays > 0 && r.status === 'original').length);

    /** Sorted and optionally filtered rows for DataTable display */
    let sortedRows = $derived.by(() => {
        let filtered = [...rows];
        if (hideStale) {
            filtered = filtered.filter((r) => !(r.staleDays && r.staleDays > 0 && r.status === 'original'));
        }
        return filtered.sort((a, b) => a.date.localeCompare(b.date));
    });

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
            case 'edited':
                return 'row-edited';
            case 'deleted':
                return 'row-deleted';
            case 'appended':
                return 'row-appended';
            default:
                return row.staleDays && row.staleDays > 0 ? 'row-stale' : '';
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
    let existingDates = $derived(new Set(rows.map((r) => r.date)));

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
                if (col.type === 'number') {
                    cols.push({
                        id: col.key,
                        header: col.label,
                        type: 'number',
                        cell: (r) => {
                            if (r.readonly) {
                                const val = r.values[col.key];
                                const display = val != null ? Number(val).toLocaleString(undefined, {maximumFractionDigits: 4}) : '—';
                                return {
                                    type: 'html',
                                    html: `<span class="text-xs font-mono text-gray-600 dark:text-gray-400">${display}</span>`,
                                };
                            }
                            // F.5 — erasable columns use the ErasableNumberCell with sentinel -1 semantics.
                            if (col.erasable) {
                                const raw = r.values[col.key];
                                const numVal = raw === undefined || raw === null ? null : Number(raw);
                                return {
                                    type: 'custom',
                                    component: ErasableNumberCell,
                                    props: {
                                        value: numVal,
                                        step: col.step ?? 0.0001,
                                        min: col.min,
                                        placeholder: col.placeholder ?? '',
                                        onchange: (newValue: number | null) => handleCellEditByRowId(r.rowId, col.key, newValue),
                                    },
                                };
                            }
                            return {
                                type: 'editable-number',
                                value: r.values[col.key] !== undefined && r.values[col.key] !== null ? Number(r.values[col.key]) : null,
                                step: col.step ?? 0.0001,
                                min: col.min,
                                max: col.max,
                                placeholder: col.placeholder ?? '',
                                onchange: (newValue) => handleCellEditByRowId(r.rowId, col.key, newValue),
                            };
                        },
                        getValue: (r) => Number(r.values[col.key] ?? 0),
                        sortable: true,
                        filterable: true,
                        width: 140,
                    });
                } else if (col.type === 'string') {
                    cols.push({
                        id: col.key,
                        header: col.label,
                        type: 'text',
                        cell: (r) => {
                            if (r.readonly) {
                                return {
                                    type: 'html',
                                    html: `<span class="text-xs text-gray-600 dark:text-gray-400">${r.values[col.key] ?? '—'}</span>`,
                                };
                            }
                            return {
                                type: 'editable-text',
                                value: String(r.values[col.key] ?? ''),
                                placeholder: col.placeholder ?? '',
                                onchange: (newValue) => handleCellEditByRowId(r.rowId, col.key, newValue),
                            };
                        },
                        getValue: (r) => String(r.values[col.key] ?? ''),
                        sortable: true,
                        filterable: true,
                        width: 140,
                    });
                } else if (col.type === 'enum' && col.enumOptions) {
                    const options = col.enumOptions;
                    cols.push({
                        id: col.key,
                        header: col.label,
                        type: 'enum',
                        enumOptions: options.map((o) => ({value: o.value, label: `${o.emoji ? o.emoji + ' ' : ''}${o.label}`})),
                        cell: (r) => {
                            // Build a small "🔒" badge appended to the readonly label when the row
                            // has a `readonlyReason` (e.g. auto-generated events). The actual
                            // explanatory text is shown via the proper Tooltip component (see
                            // DataTable HtmlCell.tooltip), not via the native HTML title attribute.
                            const readonlyBadge = r.readonlyReason ? ` <span class="ml-1 inline-flex items-center align-middle opacity-70 cursor-help">🔒</span>` : '';
                            const tooltipMeta = r.readonlyReason ? {text: r.readonlyReason, position: 'top' as const, maxWidth: '360px'} : undefined;
                            if (r.readonly) {
                                const opt = options.find((o) => o.value === r.values[col.key]);
                                if (opt?.tooltip) {
                                    const lang = typeof localStorage !== 'undefined' ? (localStorage.getItem('librefolio-locale') ?? 'en') : 'en';
                                    const prefix = lang !== 'en' ? `${lang}/` : '';
                                    const docsUrl = opt.docsPath ? `/mkdocs/${prefix}${opt.docsPath}/` : '';
                                    return {
                                        type: 'html',
                                        html: `<span class="text-xs text-gray-600 dark:text-gray-400">${opt.emoji ? `<span class="cursor-help" title="${opt.tooltip}">${opt.emoji}</span> ` : ''}${docsUrl ? `<a href="${docsUrl}" target="_blank" rel="noopener noreferrer" class="hover:underline">${opt.label}</a>` : opt.label}${readonlyBadge}</span>`,
                                        tooltip: tooltipMeta,
                                    };
                                }
                                const label = opt ? `${opt.emoji ? opt.emoji + ' ' : ''}${opt.label}` : String(r.values[col.key] ?? '—');
                                return {
                                    type: 'html',
                                    html: `<span class="text-xs text-gray-600 dark:text-gray-400">${label}${readonlyBadge}</span>`,
                                    tooltip: tooltipMeta,
                                };
                            }
                            return {
                                type: 'editable-select',
                                value: String(r.values[col.key] ?? ''),
                                options: options.map((o) => ({value: o.value, label: `${o.emoji ? o.emoji + ' ' : ''}${o.label}`})),
                                onchange: (newValue) => handleCellEditByRowId(r.rowId, col.key, newValue),
                            };
                        },
                        getValue: (r) => String(r.values[col.key] ?? ''),
                        sortable: true,
                        filterable: true,
                        width: 180,
                    });
                } else if (col.type === 'currency') {
                    cols.push({
                        id: col.key,
                        header: col.label,
                        type: 'text',
                        cell: (r) => {
                            if (r.readonly) {
                                return {
                                    type: 'html',
                                    html: `<span class="text-xs text-gray-600 dark:text-gray-400">${r.values[col.key] ?? '—'}</span>`,
                                };
                            }
                            return {
                                type: 'custom',
                                component: CurrencySearchSelect,
                                props: {
                                    value: String(r.values[col.key] ?? ''),
                                    compact: true,
                                    placeholder: col.placeholder ?? 'USD',
                                    onchange: (newValue: string) => handleCellEditByRowId(r.rowId, col.key, newValue),
                                },
                            };
                        },
                        getValue: (r) => String(r.values[col.key] ?? ''),
                        sortable: true,
                        filterable: true,
                        width: 150,
                    });
                }
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
                onClick: (row) => handleStatusChangeByRowId(row.rowId, 'deleted'),
                visible: (row) => row.status !== 'deleted',
            },
            {
                id: 'revert',
                icon: Undo2,
                label: 'Revert',
                variant: 'default' as const,
                onClick: (row) => handleStatusChangeByRowId(row.rowId, 'revert'),
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
        if (rows.some((r) => r.date === newDate && r.date !== oldDate)) return;
        const row = rows.find((r) => r.date === oldDate && r.status === 'appended');
        if (!row) return;
        row.date = newDate;
        row.rowId = newDate; // keep rowId synced for price rows
        rows = [...rows];
        emitDirty();
    }

    function handleCellEditByRowId(rowId: string, colKey: string, newValue: unknown) {
        const rowIdx = rows.findIndex((r) => r.rowId === rowId);
        if (rowIdx < 0 || isReadonly) return;

        const row = rows[rowIdx];
        if (row.readonly) return; // readonly rows cannot be edited
        const oldValues = {...row.values};
        row.values[colKey] = newValue;

        if (row.originalStatus === 'original' && row.status !== 'deleted') {
            if (!row._originalValues) {
                row._originalValues = oldValues;
            }
            const allMatch = columns.every((c) => {
                const orig = row._originalValues?.[c.key];
                const curr = row.values[c.key];
                return String(orig ?? '') === String(curr ?? '');
            });
            row.status = allMatch ? 'original' : 'edited';
        }

        rows = [...rows];
        emitDirty();
    }

    function handleStatusChangeByRowId(rowId: string, newStatus: string) {
        const rowIdx = rows.findIndex((r) => r.rowId === rowId);
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
        const existingDates = new Set(rows.map((r) => r.date));
        const todayStr = new Date().toISOString().slice(0, 10);
        let newDate: string;
        if (rows.length > 0) {
            const sortedDates = [...existingDates].sort();
            const lastDate = sortedDates[sortedDates.length - 1];
            const d = new Date(lastDate + 'T00:00:00Z');
            d.setUTCDate(d.getUTCDate() + 1);
            newDate = d.toISOString().slice(0, 10);
            while (existingDates.has(newDate)) {
                const d2 = new Date(newDate + 'T00:00:00Z');
                d2.setUTCDate(d2.getUTCDate() + 1);
                newDate = d2.toISOString().slice(0, 10);
            }
            if (newDate > todayStr) {
                newDate = todayStr;
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
            rowId: newDate,
            date: newDate,
            status: 'appended',
            originalStatus: 'appended',
            values: Object.fromEntries(columns.map((c) => [c.key, defaultRowValues[c.key] ?? undefined])),
            selected: false,
        };
        rows = [...rows, newRow];
        emitDirty();
        // Navigate to the page containing the new row + scroll into view
        tick().then(() => {
            dataTableRef?.navigateToRowId(newRow.rowId);
        });
    }

    // =========================================================================
    // Bulk selection handler (for DataTable selection)
    // =========================================================================

    function handleBulkDelete(selectedIds: string[]) {
        for (const rowId of selectedIds) {
            const row = rows.find((r) => r.rowId === rowId);
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
        for (const pr of importedRows) {
            const existingIdx = rows.findIndex((r) => r.date === pr.date);
            if (existingIdx >= 0) {
                const existing = rows[existingIdx];
                if (existing.readonly) continue; // skip readonly rows
                if (existing.originalStatus === 'original') {
                    if (!existing._originalValues) {
                        existing._originalValues = {...existing.values};
                    }
                    // Merge imported values into existing row
                    for (const [k, v] of Object.entries(pr.values)) {
                        if (v !== null && v !== undefined) {
                            existing.values[k] = v;
                        }
                    }
                    existing.status = 'edited';
                } else {
                    for (const [k, v] of Object.entries(pr.values)) {
                        if (v !== null && v !== undefined) {
                            existing.values[k] = v;
                        }
                    }
                }
            } else {
                rows.push({
                    rowId: pr.date,
                    date: pr.date,
                    status: 'appended',
                    originalStatus: 'appended',
                    values: {...pr.values},
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

    /** Scroll to a specific date in the table (finds by rowId first, then by date field) */
    export function scrollToDate(date: string) {
        // Try direct rowId match first (works for prices where rowId = date)
        const directMatch = rows.find((r) => r.rowId === date);
        if (directMatch) {
            dataTableRef?.navigateToRowId(date);
            return;
        }
        // Fallback: find first row with matching date (for events where rowId = numeric id)
        const dateMatch = rows.find((r) => r.date === date);
        if (dateMatch) {
            dataTableRef?.navigateToRowId(dateMatch.rowId);
        }
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
                    onclick={() => (importModalOpen = true)}
                    data-testid="fx-data-import-btn"
                >
                    <Upload size={13} />
                    {$t('dataEditor.importCsv')}
                </button>
                <button
                    class="flex items-center gap-1 px-2.5 py-1.5 text-xs bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                    onclick={handleAddRow}
                    data-testid="fx-data-add-row-btn"
                >
                    <Plus size={13} />
                    {$t('common.addRow')}
                </button>
            {/if}
        </div>

        <!-- Right: Selection bar + Counters + Stale toggle + Column visibility -->
        <div class="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
            {#if hasStaleRows}
                <div class="flex items-center gap-1.5" data-testid="data-editor-stale-toggle">
                    <Tooltip text={$t('dataEditor.staleTooltip')} position="bottom" maxWidth="220px">
                        <span class="text-[10px] text-amber-600 dark:text-amber-400 cursor-help">⚠️ {staleCount}</span>
                    </Tooltip>
                    <!-- Horizontal switch lever -->
                    <button
                        class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none
                                   {hideStale ? 'bg-amber-500 dark:bg-amber-600' : 'bg-gray-300 dark:bg-slate-600'}"
                        onclick={() => (hideStale = !hideStale)}
                        role="switch"
                        aria-checked={hideStale}
                        aria-label={hideStale ? `Show ${staleCount} stale rows` : `Hide ${staleCount} stale rows`}
                    >
                        <span
                            class="inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow-sm transition-transform
                                     {hideStale ? 'translate-x-4.5' : 'translate-x-0.5'}"
                        ></span>
                    </button>
                </div>
            {/if}
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
                    onclick={() => {
                        dataTableRef?.clearSelection();
                        selectedIds = [];
                    }}
                    title={$t('common.clearSelection')}
                >
                    {selectedIds.length}
                    {$t('common.selected')} <span class="opacity-60">×</span>
                </button>
                <button
                    type="button"
                    class="flex items-center justify-center w-7 h-7 rounded-md bg-red-50 dark:bg-red-900/20 text-red-500 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors"
                    onclick={() => {
                        handleBulkDelete(selectedIds);
                        dataTableRef?.clearSelection();
                        selectedIds = [];
                    }}
                    title={$t('common.deleteSelected')}
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
            columns={dtColumns}
            data={sortedRows}
            defaultPageSize={10}
            emptyMessage={$t('dataEditor.emptyMessage')}
            enableActions={!isReadonly}
            enableColumnFilters={true}
            enableColumnResize={true}
            enableColumnVisibility={true}
            enablePagination={true}
            enableSelection={!isReadonly}
            enableSorting={true}
            getRowClass={rowBgClass}
            getRowId={(r) => r.rowId}
            getRowStyle={rowStyleFn}
            onSelectionChange={(ids) => (selectedIds = ids)}
            pageSizeOptions={[10, 25, 50, 100, 0]}
            rowActions={dtRowActions}
            storageKey="data-editor"
        />
    </div>
</div>

<!-- Import Modal (injected via snippet) -->
{#if importModal}
    {@render importModal({open: importModalOpen, setOpen: (v) => (importModalOpen = v), onimport: handleImport})}
{/if}
