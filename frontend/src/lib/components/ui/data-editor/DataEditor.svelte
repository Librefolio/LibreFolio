<!--
  DataEditor — Generic dual-mode data editor (CSV text ↔ Table) with row-folding and status tracking.

  Features:
  - Dual view: CSV text (via CsvEditor) and interactive table
  - Row status tracking: original, edited, deleted, appended
  - Row folding: gaps > 2 days are collapsed with expandable placeholders
  - Bulk operations: select multiple rows + mark as deleted
  - Import CSV via DataImportModal
  - Add row (today's date)
  - Configurable columns via ColumnDef[]
  - Dirty row emission for save/preview

  Uses Svelte 5 runes ($state, $derived, $props, $effect).
-->
<script lang="ts">
    import {tick} from 'svelte';
    import {Plus, Upload, Trash2, CalendarSearch, Undo2} from 'lucide-svelte';
    import CsvEditor from '$lib/components/fx/CsvEditor.svelte';
    import type {ParsedRow} from '$lib/components/fx/CsvEditor.svelte';
    import DataImportModal from './DataImportModal.svelte';
    import type {ColumnDef, DataRow, GapRow, TableRow} from './DataEditorTypes';

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
    // Constants
    // =========================================================================

    /** Gap threshold in days — gaps larger than this are folded */
    const GAP_THRESHOLD_DAYS = 2;

    // =========================================================================
    // State
    // =========================================================================

    let csvEditor: CsvEditor | undefined = $state(undefined);
    let csvValue = $state('');
    let importModalOpen = $state(false);
    let selectAll = $state(false);

    // Track expanded gaps by their startDate
    let expandedGaps = $state(new Set<string>());

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

    /** Selected count */
    let selectedCount = $derived(rows.filter(r => r.selected).length);

    /** Can switch to table view? (no CSV errors or duplicates) */
    let canSwitchToTable = $state(true);
    let switchBlockReason = $state('');

    /** Table rows with gap folding */
    let tableRows: TableRow[] = $derived.by(() => {
        const result: TableRow[] = [];
        const sortedRows = [...rows].sort((a, b) => a.date.localeCompare(b.date));

        for (let i = 0; i < sortedRows.length; i++) {
            const row = sortedRows[i];

            // Check for gap before this row (except first row)
            if (i > 0) {
                const prevDate = new Date(sortedRows[i - 1].date + 'T00:00:00Z');
                const currDate = new Date(row.date + 'T00:00:00Z');
                const diffDays = Math.round((currDate.getTime() - prevDate.getTime()) / (1000 * 60 * 60 * 24));

                if (diffDays > GAP_THRESHOLD_DAYS) {
                    const gapKey = sortedRows[i - 1].date;
                    const isExpanded = expandedGaps.has(gapKey);

                    if (isExpanded) {
                        // Generate empty editable rows for the gap
                        const gapDate = new Date(prevDate);
                        for (let d = 1; d < diffDays; d++) {
                            gapDate.setUTCDate(gapDate.getUTCDate() + 1);
                            const isoDate = gapDate.toISOString().slice(0, 10);
                            // Skip if a row already exists for this date
                            if (!sortedRows.find(r => r.date === isoDate)) {
                                const gapRow: DataRow = {
                                    date: isoDate,
                                    status: 'appended',
                                    originalStatus: 'appended',
                                    values: Object.fromEntries(columns.map(c => [c.key, undefined])),
                                    selected: false,
                                };
                                result.push({...gapRow, type: 'data'});
                            }
                        }
                    } else {
                        result.push({
                            type: 'gap',
                            startDate: sortedRows[i - 1].date,
                            endDate: row.date,
                            dayCount: diffDays - 1,
                            expanded: false,
                        } satisfies GapRow);
                    }
                }
            }

            result.push({...row, type: 'data'});
        }

        return result;
    });

    // =========================================================================
    // Sync CSV ↔ Rows
    // =========================================================================

    /** Convert rows to CSV text */
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
            // Check if this date exists in current rows
            const existing = rows.find(r => r.date === pr.date);
            const firstCol = columns[0];

            if (existing && existing.originalStatus === 'original') {
                // Existing original row — mark as edited if value changed
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

    function switchToText() {
        csvValue = rowsToCsv();
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

        // Sync CSV changes back to rows when in text mode
        if (viewMode === 'text' && errors === 0 && !duplicates) {
            rows = csvToRows(validRows);
            emitDirty();
        }
    }

    // =========================================================================
    // Table Edit Handlers
    // =========================================================================

    function handleCellEdit(rowIndex: number, colKey: string, newValue: unknown) {
        const row = rows[rowIndex];
        if (!row || isReadonly) return;

        const oldValues = {...row.values};
        row.values[colKey] = newValue;

        if (row.originalStatus === 'original' && row.status !== 'deleted') {
            // Check if value differs from original
            const hasOriginal = row._originalValues !== undefined;
            if (!hasOriginal) {
                row._originalValues = oldValues;
            }

            // Compare with original
            const originalVal = row._originalValues?.[colKey];
            const allMatch = columns.every(c => {
                const orig = row._originalValues?.[c.key];
                const curr = row.values[c.key];
                return String(orig ?? '') === String(curr ?? '');
            });

            row.status = allMatch ? 'original' : 'edited';
        }

        rows = [...rows]; // Trigger reactivity
        emitDirty();
    }

    function handleStatusChange(rowIndex: number, newStatus: string) {
        const row = rows[rowIndex];
        if (!row || isReadonly) return;

        if (newStatus === 'deleted') {
            row.status = 'deleted';
        } else if (newStatus === 'revert') {
            if (row.originalStatus === 'original') {
                row.status = 'original';
                if (row._originalValues) {
                    row.values = {...row._originalValues};
                }
            } else if (row.originalStatus === 'appended') {
                // Remove appended row entirely
                rows = rows.filter((_, i) => i !== rowIndex);
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

    function handleMarkSelectedDeleted() {
        for (const row of rows) {
            if (row.selected) {
                row.status = 'deleted';
                row.selected = false;
            }
        }
        selectAll = false;
        rows = [...rows];
        emitDirty();
    }

    function handleToggleSelectAll() {
        selectAll = !selectAll;
        for (const row of rows) {
            if (row.status !== 'deleted') {
                row.selected = selectAll;
            }
        }
        rows = [...rows];
    }

    function handleToggleGap(gapStartDate: string) {
        const newSet = new Set(expandedGaps);
        if (newSet.has(gapStartDate)) {
            newSet.delete(gapStartDate);
        } else {
            newSet.add(gapStartDate);
        }
        expandedGaps = newSet;
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
    // Helpers
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
            case 'edited': return 'bg-blue-50 dark:bg-blue-900/15';
            case 'deleted': return 'bg-red-50 dark:bg-red-900/15 line-through opacity-60';
            case 'appended': return 'bg-emerald-50 dark:bg-emerald-900/15';
            default: return '';
        }
    }

    /** Status badge color */
    function statusBadge(status: string): {text: string; color: string} {
        switch (status) {
            case 'original': return {text: 'Original', color: 'text-gray-500 dark:text-gray-400'};
            case 'edited': return {text: 'Edited', color: 'text-blue-600 dark:text-blue-400'};
            case 'deleted': return {text: 'Deleted', color: 'text-red-600 dark:text-red-400'};
            case 'appended': return {text: 'New', color: 'text-emerald-600 dark:text-emerald-400'};
            default: return {text: status, color: 'text-gray-500'};
        }
    }

    /** Available status options based on current row state */
    function getStatusOptions(row: DataRow): Array<{value: string; label: string}> {
        const opts: Array<{value: string; label: string}> = [];
        if (row.status === 'deleted') {
            opts.push({value: 'revert', label: '↩ Revert'});
        } else {
            opts.push({value: 'deleted', label: '🗑 Delete'});
            if (row.status === 'edited' || row.status === 'appended') {
                opts.push({value: 'revert', label: '↩ Revert'});
            }
        }
        return opts;
    }

    // =========================================================================
    // Public API
    // =========================================================================

    /** Scroll to a specific date in the table or CSV view */
    export function scrollToDate(date: string) {
        if (viewMode === 'text' && csvEditor) {
            // Find line number for this date in CSV
            const csvLines = csvValue.split('\n');
            const lineIdx = csvLines.findIndex(l => l.startsWith(date));
            if (lineIdx >= 0) {
                csvEditor.scrollToLine(lineIdx + 1);
            }
        } else {
            // Table view — scroll element into view
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
                >CSV</button>
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

                    {#if selectedCount > 0}
                        <button
                            class="flex items-center gap-1 px-2.5 py-1.5 text-xs bg-red-100 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/30 transition-colors"
                            onclick={handleMarkSelectedDeleted}
                        >
                            <Trash2 size={13} /> Delete ({selectedCount})
                        </button>
                    {/if}
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
            <!-- Table View -->
            <table class="w-full text-sm">
                <thead class="sticky top-0 z-10 bg-gray-50 dark:bg-slate-700/50 border-b border-gray-200 dark:border-slate-600">
                    <tr>
                        {#if !isReadonly}
                            <th class="w-8 px-2 py-2">
                                <input
                                    type="checkbox"
                                    checked={selectAll}
                                    onchange={handleToggleSelectAll}
                                    class="rounded border-gray-300 dark:border-slate-600 text-libre-green focus:ring-libre-green/50"
                                />
                            </th>
                        {/if}
                        <th class="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wide">Date</th>
                        {#each columns as col}
                            <th class="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wide">{col.label}</th>
                        {/each}
                        <th class="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wide w-24">Status</th>
                        {#if !isReadonly}
                            <th class="w-10 px-2 py-2"></th>
                        {/if}
                    </tr>
                </thead>
                <tbody>
                    {#each tableRows as tableRow (tableRow.type === 'gap' ? `gap-${tableRow.startDate}` : tableRow.date)}
                        {#if tableRow.type === 'gap'}
                            <!-- Gap row (folded) -->
                            <tr class="bg-gray-50/50 dark:bg-slate-700/20">
                                {#if !isReadonly}<td></td>{/if}
                                <td
                                    colspan={columns.length + 2 + (isReadonly ? 0 : 1)}
                                    class="px-3 py-1.5 text-center cursor-pointer hover:bg-gray-100 dark:hover:bg-slate-700/40 transition-colors"
                                    role="button"
                                    tabindex="0"
                                    onclick={() => handleToggleGap(tableRow.startDate)}
                                    onkeydown={(e) => { if (e.key === 'Enter') handleToggleGap(tableRow.startDate); }}
                                >
                                    <span class="text-xs text-gray-400 dark:text-gray-500 font-mono">
                                        ⋯ {tableRow.dayCount} day{tableRow.dayCount !== 1 ? 's' : ''} gap ({tableRow.startDate} → {tableRow.endDate})
                                    </span>
                                </td>
                            </tr>
                        {:else}
                            <!-- Data row -->
                            {@const rowIdx = rows.findIndex(r => r.date === tableRow.date)}
                            <tr
                                class="border-b border-gray-100 dark:border-slate-700/50 {rowBgClass(tableRow)} hover:bg-gray-50/50 dark:hover:bg-slate-700/20 transition-colors"
                                data-date={tableRow.date}
                            >
                                {#if !isReadonly}
                                    <td class="w-8 px-2 py-1.5">
                                        <input
                                            type="checkbox"
                                            checked={tableRow.selected}
                                            disabled={tableRow.status === 'deleted'}
                                            onchange={() => { if (rowIdx >= 0) { rows[rowIdx].selected = !rows[rowIdx].selected; rows = [...rows]; }}}
                                            class="rounded border-gray-300 dark:border-slate-600 text-libre-green focus:ring-libre-green/50"
                                        />
                                    </td>
                                {/if}

                                <!-- Date cell -->
                                <td class="px-3 py-1.5 font-mono text-xs text-gray-700 dark:text-gray-300 whitespace-nowrap">
                                    {tableRow.date}
                                    <span class="ml-1 text-gray-400 dark:text-gray-500 text-[10px]">{weekday(tableRow.date)}</span>
                                </td>

                                <!-- Data columns -->
                                {#each columns as col}
                                    <td class="px-3 py-1.5">
                                        {#if col.editable && !isReadonly && tableRow.status !== 'deleted'}
                                            <input
                                                type={col.type === 'number' ? 'number' : 'text'}
                                                value={tableRow.values[col.key] ?? ''}
                                                step={col.step ?? 'any'}
                                                placeholder={col.placeholder ?? ''}
                                                oninput={(e) => {
                                                    const target = e.currentTarget;
                                                    const val = col.type === 'number' ? (target.value ? parseFloat(target.value) : undefined) : target.value;
                                                    if (rowIdx >= 0) handleCellEdit(rowIdx, col.key, val);
                                                }}
                                                class="w-full px-2 py-0.5 text-xs font-mono border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-300 focus:ring-1 focus:ring-libre-green/50 focus:border-libre-green"
                                            />
                                        {:else}
                                            <span class="text-xs font-mono text-gray-600 dark:text-gray-400">
                                                {tableRow.values[col.key] ?? '—'}
                                            </span>
                                        {/if}
                                    </td>
                                {/each}

                                <!-- Status cell -->
                                <td class="px-3 py-1.5">
                                    <span class="text-xs font-medium {statusBadge(tableRow.status).color}">{statusBadge(tableRow.status).text}</span>
                                </td>

                                <!-- Actions cell -->
                                {#if !isReadonly}
                                    <td class="w-10 px-2 py-1.5">
                                        {#if tableRow.status === 'deleted'}
                                            <button
                                                class="p-1 text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 rounded transition-colors"
                                                title="Revert"
                                                onclick={() => { if (rowIdx >= 0) handleStatusChange(rowIdx, 'revert'); }}
                                            >
                                                <Undo2 size={14} />
                                            </button>
                                        {:else}
                                            <button
                                                class="p-1 text-gray-400 hover:text-red-500 dark:hover:text-red-400 rounded transition-colors"
                                                title="Delete"
                                                onclick={() => { if (rowIdx >= 0) handleStatusChange(rowIdx, 'deleted'); }}
                                            >
                                                <Trash2 size={14} />
                                            </button>
                                        {/if}
                                    </td>
                                {/if}
                            </tr>
                        {/if}
                    {/each}

                    {#if rows.length === 0}
                        <tr>
                            <td
                                colspan={columns.length + 3}
                                class="px-4 py-8 text-center text-sm text-gray-400 dark:text-gray-500"
                            >
                                No data. Use "Add Row" or "Import CSV" to add data.
                            </td>
                        </tr>
                    {/if}
                </tbody>
            </table>
        {/if}
    </div>
</div>

<!-- Import Modal -->
<DataImportModal
    bind:open={importModalOpen}
    header={csvHeader}
    onimport={handleImport}
/>




