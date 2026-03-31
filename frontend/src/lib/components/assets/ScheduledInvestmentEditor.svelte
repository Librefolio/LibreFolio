<!--
  ScheduledInvestmentEditor — DataTable-based editor for interest schedules.

  Features:
  - Editable DataTable with Period, Rate %, Compounding, Comp. Freq., Day Count
  - Late Interest as permanent special row with toggle on/off
  - Automatic contiguity propagation (no overlaps/gaps by design)
  - CRUD: Add, Delete (with boundary modal), Split, Merge
  - Bulk delete with multi-gap support
  - JSON ↔ form bidirectional serialization

  Props:
  - value: Record<string, any> (provider_params JSON, bindable)
  - onchange: (newParams: Record<string, any>) => void
  - disabled / readonly

  Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Plus, Scissors, X, Link2, Trash2, CalendarDays} from 'lucide-svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef, RowAction, CellContent} from '$lib/components/table/types';
    import CellDateRange from './CellDateRange.svelte';
    import BoundaryDateModal from './BoundaryDateModal.svelte';

    // =========================================================================
    // Types
    // =========================================================================

    interface ScheduleRow {
        id: string;
        start_date: string;
        end_date: string;
        annual_rate: number;
        compounding: 'SIMPLE' | 'COMPOUND';
        compound_frequency: string | null;
        day_count: string;
        isLate: boolean;
        grace_period_days: number;
        enabled: boolean;
    }

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        value?: Record<string, any>;
        onchange?: (newParams: Record<string, any>) => void;
        disabled?: boolean;
        readonly?: boolean;
    }

    let {value = {}, onchange, disabled = false, readonly = false}: Props = $props();

    // =========================================================================
    // Constants
    // =========================================================================

    const COMPOUNDING_OPTIONS = [
        {value: 'SIMPLE', label: 'Simple'},
        {value: 'COMPOUND', label: 'Compound'},
    ];

    const COMPOUND_FREQ_OPTIONS = [
        {value: 'DAILY', label: 'Daily'},
        {value: 'MONTHLY', label: 'Monthly'},
        {value: 'QUARTERLY', label: 'Quarterly'},
        {value: 'SEMIANNUAL', label: 'Semiannual'},
        {value: 'ANNUAL', label: 'Annual'},
        {value: 'CONTINUOUS', label: 'Continuous'},
    ];

    const DAY_COUNT_OPTIONS = [
        {value: 'ACT/365', label: 'ACT/365'},
        {value: 'ACT/360', label: 'ACT/360'},
        {value: 'ACT/ACT', label: 'ACT/ACT'},
        {value: '30/360', label: '30/360'},
    ];

    // =========================================================================
    // Date Helpers
    // =========================================================================

    function addDays(isoDate: string, days: number): string {
        const d = new Date(isoDate + 'T00:00:00');
        d.setDate(d.getDate() + days);
        return d.toISOString().slice(0, 10);
    }

    function addMonths(isoDate: string, months: number): string {
        const d = new Date(isoDate + 'T00:00:00');
        d.setMonth(d.getMonth() + months);
        return d.toISOString().slice(0, 10);
    }

    function daysBetween(start: string, end: string): number {
        const s = new Date(start + 'T00:00:00');
        const e = new Date(end + 'T00:00:00');
        return Math.round((e.getTime() - s.getTime()) / (1000 * 60 * 60 * 24));
    }

    function todayISO(): string {
        return new Date().toISOString().slice(0, 10);
    }

    function midpointDate(start: string, end: string): string {
        const days = daysBetween(start, end);
        return addDays(start, Math.floor(days / 2));
    }

    // =========================================================================
    // State
    // =========================================================================

    let rows = $state<ScheduleRow[]>([]);
    let selectedIds = $state<string[]>([]);
    let internalUpdate = false;

    // Sync from prop (only on external changes)
    $effect(() => {
        // Read value to track reactivity
        const v = value;
        if (internalUpdate) {
            internalUpdate = false;
            return;
        }
        rows = deserialize(v);
    });

    // Modal state
    let showBoundaryModal = $state(false);
    let boundaryModalMode = $state<'delete' | 'split'>('delete');
    let boundaryModalMin = $state('');
    let boundaryModalMax = $state('');
    let boundaryModalDefault = $state('');
    let pendingActionIndex = $state(-1);
    let pendingBulkDeleteIndices = $state<number[]>([]);

    // =========================================================================
    // Derived
    // =========================================================================

    let normalRows = $derived(rows.filter(r => !r.isLate));
    let lateRow = $derived(rows.find(r => r.isLate));

    /** All rows for DataTable: normal periods + late interest */
    let tableData = $derived.by(() => {
        const result: ScheduleRow[] = [...normalRows];
        if (lateRow) result.push(lateRow);
        return result;
    });

    let selectedNormalRows = $derived(
        normalRows.filter(r => selectedIds.includes(r.id))
    );

    let selectedNormalIndices = $derived(
        selectedNormalRows
            .map(r => normalRows.findIndex(p => p.id === r.id))
            .filter(i => i >= 0)
            .sort((a, b) => a - b)
    );

    let areSelectedContiguous = $derived.by(() => {
        if (selectedNormalIndices.length < 2) return false;
        for (let i = 1; i < selectedNormalIndices.length; i++) {
            if (selectedNormalIndices[i] !== selectedNormalIndices[i - 1] + 1) return false;
        }
        return true;
    });

    let isFormValid = $derived.by(() => {
        if (normalRows.length === 0) return false;
        for (const p of normalRows) {
            if (p.annual_rate < 0) return false;
            if (p.compounding === 'COMPOUND' && !p.compound_frequency) return false;
        }
        if (lateRow?.enabled) {
            if (lateRow.annual_rate < 0) return false;
            if (lateRow.grace_period_days < 0) return false;
            if (lateRow.compounding === 'COMPOUND' && !lateRow.compound_frequency) return false;
        }
        return true;
    });

    /** Status banner info */
    let statusBanner = $derived.by(() => {
        if (normalRows.length === 0) return {icon: '📅', text: $t('assets.schedule.empty'), ok: false};
        const first = normalRows[0];
        const last = normalRows[normalRows.length - 1];
        const days = daysBetween(first.start_date, last.end_date);
        let text = `${normalRows.length} ${$t('assets.schedule.periods')}, ${$t('assets.schedule.contiguous')} — ${first.start_date} → ${last.end_date} (${days} ${$t('assets.schedule.days')})`;
        if (lateRow?.enabled) text += ' + late interest';
        return {icon: '✅', text, ok: isFormValid};
    });

    // =========================================================================
    // Serialization
    // =========================================================================

    function deserialize(val: Record<string, any>): ScheduleRow[] {
        const result: ScheduleRow[] = [];
        const schedule = val?.schedule ?? [];

        for (const p of schedule) {
            result.push({
                id: crypto.randomUUID(),
                start_date: p.start_date,
                end_date: p.end_date,
                annual_rate: Number(p.annual_rate) * 100,
                compounding: p.compounding ?? 'SIMPLE',
                compound_frequency: p.compound_frequency ?? null,
                day_count: p.day_count ?? 'ACT/365',
                isLate: false,
                grace_period_days: 0,
                enabled: true,
            });
        }

        // Late interest — always present
        const li = val?.late_interest;
        result.push({
            id: 'late-interest',
            start_date: result.length > 0 ? addDays(result[result.length - 1].end_date, 1) : '',
            end_date: '',
            annual_rate: li ? Number(li.annual_rate) * 100 : 12,
            compounding: li?.compounding ?? 'SIMPLE',
            compound_frequency: li?.compound_frequency ?? null,
            day_count: li?.day_count ?? 'ACT/365',
            isLate: true,
            grace_period_days: li?.grace_period_days ?? 0,
            enabled: !!li,
        });

        return result;
    }

    function serialize(allRows: ScheduleRow[]): Record<string, any> {
        const schedule = allRows
            .filter(r => !r.isLate)
            .map(r => ({
                start_date: r.start_date,
                end_date: r.end_date,
                annual_rate: (r.annual_rate / 100).toFixed(4),
                compounding: r.compounding,
                compound_frequency: r.compounding === 'COMPOUND' ? r.compound_frequency : undefined,
                day_count: r.day_count,
            }));

        const lr = allRows.find(r => r.isLate && r.enabled);
        const late_interest = lr ? {
            annual_rate: (lr.annual_rate / 100).toFixed(4),
            grace_period_days: lr.grace_period_days,
            compounding: lr.compounding,
            compound_frequency: lr.compounding === 'COMPOUND' ? lr.compound_frequency : undefined,
            day_count: lr.day_count,
        } : null;

        return {schedule, late_interest};
    }

    function emitChange() {
        internalUpdate = true;
        onchange?.(serialize(rows));
    }

    // =========================================================================
    // Contiguity Propagation
    // =========================================================================

    function propagateStartBackward(periods: ScheduleRow[], targetIndex: number, newStartOfNext: string): void {
        const newEndForTarget = addDays(newStartOfNext, -1);
        while (targetIndex >= 0) {
            const target = periods[targetIndex];
            if (newEndForTarget >= target.start_date) {
                target.end_date = newEndForTarget;
                return;
            }
            periods.splice(targetIndex, 1);
            targetIndex--;
        }
    }

    function propagateEndForward(periods: ScheduleRow[], targetIndex: number, newEndOfPrev: string): void {
        const newStartForTarget = addDays(newEndOfPrev, 1);
        while (targetIndex < periods.length) {
            const target = periods[targetIndex];
            if (newStartForTarget <= target.end_date) {
                target.start_date = newStartForTarget;
                return;
            }
            periods.splice(targetIndex, 1);
        }
    }

    function handleRangeChange(rowIndex: number, newStart: string, newEnd: string): void {
        const periods = rows.filter(r => !r.isLate);
        const row = periods[rowIndex];
        if (!row) return;
        if (newEnd < newStart) return;

        const oldStart = row.start_date;
        const oldEnd = row.end_date;

        // Left propagation
        if (newStart !== oldStart) {
            if (rowIndex === 0) {
                row.start_date = newStart;
            } else {
                const prev = periods[rowIndex - 1];
                const newPrevEnd = addDays(newStart, -1);
                if (newPrevEnd < prev.start_date) {
                    propagateStartBackward(periods, rowIndex - 1, newStart);
                } else {
                    prev.end_date = newPrevEnd;
                }
                row.start_date = newStart;
            }
        }

        // Right propagation
        if (newEnd !== oldEnd) {
            // Recompute rowIndex since propagation may have removed rows
            const currentIdx = periods.indexOf(row);
            if (currentIdx === periods.length - 1) {
                row.end_date = newEnd;
            } else {
                const next = periods[currentIdx + 1];
                const newNextStart = addDays(newEnd, 1);
                if (newNextStart > next.end_date) {
                    propagateEndForward(periods, currentIdx + 1, newEnd);
                } else {
                    next.start_date = newNextStart;
                }
                row.end_date = newEnd;
            }
        }

        // Rebuild rows: updated normals + late
        const late = rows.find(r => r.isLate);
        rows = [...periods, ...(late ? [late] : [])];
        emitChange();
    }

    // =========================================================================
    // CRUD Operations
    // =========================================================================

    function handleAddPeriod(): void {
        const periods = normalRows;
        let newStart: string;
        let newEnd: string;

        if (periods.length === 0) {
            newStart = todayISO();
            newEnd = addMonths(newStart, 1);
        } else {
            const lastEnd = periods[periods.length - 1].end_date;
            newStart = addDays(lastEnd, 1);
            newEnd = addMonths(newStart, 1);
        }

        const lastPeriod = periods.length > 0 ? periods[periods.length - 1] : null;
        const newRow: ScheduleRow = {
            id: crypto.randomUUID(),
            start_date: newStart,
            end_date: newEnd,
            annual_rate: lastPeriod?.annual_rate ?? 5.00,
            compounding: lastPeriod?.compounding ?? 'SIMPLE',
            compound_frequency: lastPeriod?.compound_frequency ?? null,
            day_count: lastPeriod?.day_count ?? 'ACT/365',
            isLate: false,
            grace_period_days: 0,
            enabled: true,
        };

        const late = rows.find(r => r.isLate);
        rows = [...normalRows, newRow, ...(late ? [late] : [])];
        emitChange();
    }

    function handleDelete(rowIndex: number): void {
        const periods = [...normalRows];
        const toDelete = periods[rowIndex];
        if (!toDelete) return;

        if (periods.length === 1) {
            periods.splice(rowIndex, 1);
            rebuildAndEmit(periods);
            return;
        }

        const hasPrev = rowIndex > 0;
        const hasNext = rowIndex < periods.length - 1;

        if (hasPrev && hasNext) {
            // Middle: open boundary modal
            pendingActionIndex = rowIndex;
            pendingBulkDeleteIndices = [];
            boundaryModalMode = 'delete';
            boundaryModalMin = toDelete.start_date;
            boundaryModalMax = toDelete.end_date;
            boundaryModalDefault = midpointDate(toDelete.start_date, toDelete.end_date);
            showBoundaryModal = true;
            return;
        }

        if (hasPrev && !hasNext) {
            periods[rowIndex - 1].end_date = toDelete.end_date;
        } else if (!hasPrev && hasNext) {
            periods[rowIndex + 1].start_date = toDelete.start_date;
        }

        periods.splice(rowIndex, 1);
        rebuildAndEmit(periods);
    }

    function handleSplitRequest(rowIndex: number): void {
        const period = normalRows[rowIndex];
        if (!period) return;
        const days = daysBetween(period.start_date, period.end_date);
        if (days <= 1) return;

        pendingActionIndex = rowIndex;
        pendingBulkDeleteIndices = [];
        boundaryModalMode = 'split';
        boundaryModalMin = addDays(period.start_date, 1);
        boundaryModalMax = addDays(period.end_date, -1);
        boundaryModalDefault = midpointDate(period.start_date, period.end_date);
        showBoundaryModal = true;
    }

    function handleBoundaryConfirm(boundaryDate: string): void {
        if (boundaryModalMode === 'delete') {
            if (pendingBulkDeleteIndices.length > 0) {
                // Bulk delete
                confirmBulkDelete(boundaryDate);
            } else {
                confirmDelete(boundaryDate);
            }
        } else {
            confirmSplit(boundaryDate);
        }
    }

    function confirmDelete(boundaryDate: string): void {
        const periods = [...normalRows];
        const idx = pendingActionIndex;
        if (idx <= 0 || idx >= periods.length - 1) return;

        periods[idx - 1].end_date = boundaryDate;
        periods[idx + 1].start_date = addDays(boundaryDate, 1);
        periods.splice(idx, 1);
        rebuildAndEmit(periods);
    }

    function confirmSplit(boundaryDate: string): void {
        const periods = [...normalRows];
        const idx = pendingActionIndex;
        const original = periods[idx];
        if (!original) return;

        const row1: ScheduleRow = {
            ...original,
            id: crypto.randomUUID(),
            end_date: boundaryDate,
        };
        const row2: ScheduleRow = {
            ...original,
            id: crypto.randomUUID(),
            start_date: addDays(boundaryDate, 1),
        };

        periods.splice(idx, 1, row1, row2);
        rebuildAndEmit(periods);
    }

    function handleMerge(): void {
        if (!areSelectedContiguous || selectedNormalIndices.length < 2) return;
        const periods = [...normalRows];
        const indices = selectedNormalIndices;
        const first = periods[indices[0]];
        const last = periods[indices[indices.length - 1]];

        const merged: ScheduleRow = {
            ...first,
            id: crypto.randomUUID(),
            end_date: last.end_date,
        };

        periods.splice(indices[0], indices.length, merged);
        selectedIds = [];
        rebuildAndEmit(periods);
    }

    function handleBulkDelete(): void {
        if (selectedNormalRows.length === 0) return;
        const periods = [...normalRows];
        const indices = selectedNormalRows
            .map(r => periods.findIndex(p => p.id === r.id))
            .filter(i => i >= 0)
            .sort((a, b) => a - b);

        if (indices.length === 0) return;

        // If all rows selected → empty state
        if (indices.length === periods.length) {
            selectedIds = [];
            rebuildAndEmit([]);
            return;
        }

        const firstIdx = indices[0];
        const lastIdx = indices[indices.length - 1];
        const blockStart = periods[firstIdx].start_date;
        const blockEnd = periods[lastIdx].end_date;
        const hasPrev = firstIdx > 0;
        const hasNext = lastIdx < periods.length - 1;

        if (hasPrev && hasNext) {
            // Middle block → boundary modal
            pendingActionIndex = -1;
            pendingBulkDeleteIndices = indices;
            boundaryModalMode = 'delete';
            boundaryModalMin = blockStart;
            boundaryModalMax = blockEnd;
            boundaryModalDefault = midpointDate(blockStart, blockEnd);
            showBoundaryModal = true;
            return;
        }

        if (hasPrev) {
            periods[firstIdx - 1].end_date = blockEnd;
        } else if (hasNext) {
            periods[lastIdx + 1].start_date = blockStart;
        }

        for (let i = indices.length - 1; i >= 0; i--) {
            periods.splice(indices[i], 1);
        }

        selectedIds = [];
        rebuildAndEmit(periods);
    }

    function confirmBulkDelete(boundaryDate: string): void {
        const periods = [...normalRows];
        const indices = pendingBulkDeleteIndices;
        if (indices.length === 0) return;

        const firstIdx = indices[0];
        const lastIdx = indices[indices.length - 1];

        periods[firstIdx - 1].end_date = boundaryDate;
        periods[lastIdx + 1].start_date = addDays(boundaryDate, 1);

        for (let i = indices.length - 1; i >= 0; i--) {
            periods.splice(indices[i], 1);
        }

        selectedIds = [];
        rebuildAndEmit(periods);
    }

    function rebuildAndEmit(periods: ScheduleRow[]): void {
        const late = rows.find(r => r.isLate);
        rows = [...periods, ...(late ? [late] : [])];
        emitChange();
    }

    // =========================================================================
    // Row Field Handlers
    // =========================================================================

    function updateRow(id: string, field: keyof ScheduleRow, val: any): void {
        rows = rows.map(r => {
            if (r.id !== id) return r;
            const updated = {...r, [field]: val};
            // Clear compound_frequency when switching to SIMPLE
            if (field === 'compounding' && val === 'SIMPLE') {
                updated.compound_frequency = null;
            }
            return updated;
        });
        emitChange();
    }

    function toggleLateInterest(): void {
        rows = rows.map(r => {
            if (!r.isLate) return r;
            return {...r, enabled: !r.enabled};
        });
        emitChange();
    }

    // =========================================================================
    // DataTable Configuration
    // =========================================================================

    let columns = $derived<ColumnDef<ScheduleRow>[]>([
        {
            id: 'period',
            header: () => $t('assets.schedule.period'),
            headerTooltip: () => $t('assets.schedule.periodHint'),
            type: 'custom',
            sortable: false,
            filterable: false,
            width: 220,
            minWidth: 180,
            cell: (row: ScheduleRow): CellContent => ({
                type: 'custom',
                component: CellDateRange,
                props: {
                    start: row.start_date,
                    end: row.end_date,
                    disabled: disabled || readonly || (row.isLate && true),
                    isLateInterest: row.isLate,
                    graceDays: row.grace_period_days,
                    onchange: (s: string, e: string) => {
                        if (row.isLate) return;
                        const idx = normalRows.findIndex(r => r.id === row.id);
                        if (idx >= 0) handleRangeChange(idx, s, e);
                    },
                    onGraceDaysChange: (days: number) => {
                        if (row.isLate) updateRow(row.id, 'grace_period_days', days);
                    },
                },
            }),
        },
        {
            id: 'rate',
            header: () => $t('assets.schedule.rate'),
            headerTooltip: () => $t('assets.schedule.rateHint'),
            headerTooltipUrl: '/mkdocs/financial-theory/synthetic-benchmarks/#compound-growth',
            type: 'custom',
            sortable: false,
            filterable: false,
            width: 90,
            minWidth: 80,
            cell: (row: ScheduleRow): CellContent => ({
                type: 'editable-number',
                value: row.annual_rate,
                step: 0.01,
                min: 0,
                placeholder: '0.00',
                onchange: (v: number | null) => updateRow(row.id, 'annual_rate', v ?? 0),
            }),
        },
        {
            id: 'compounding',
            header: () => $t('assets.schedule.compounding'),
            headerTooltip: () => $t('assets.schedule.compoundingHint'),
            headerTooltipUrl: '/mkdocs/financial-theory/synthetic-benchmarks/#compound-growth',
            type: 'custom',
            sortable: false,
            filterable: false,
            width: 120,
            minWidth: 100,
            cell: (row: ScheduleRow): CellContent => ({
                type: 'editable-select',
                value: row.compounding,
                options: COMPOUNDING_OPTIONS,
                onchange: (v: string) => updateRow(row.id, 'compounding', v),
            }),
        },
        {
            id: 'compound_frequency',
            header: () => $t('assets.schedule.compFreq'),
            headerTooltip: () => $t('assets.schedule.freqHint'),
            headerTooltipUrl: '/mkdocs/financial-theory/synthetic-benchmarks/#compound-growth',
            type: 'custom',
            sortable: false,
            filterable: false,
            width: 130,
            minWidth: 100,
            cell: (row: ScheduleRow): CellContent => {
                if (row.compounding === 'SIMPLE') {
                    return '—';
                }
                return {
                    type: 'editable-select',
                    value: row.compound_frequency ?? '',
                    options: COMPOUND_FREQ_OPTIONS,
                    onchange: (v: string) => updateRow(row.id, 'compound_frequency', v || null),
                };
            },
        },
        {
            id: 'day_count',
            header: () => $t('assets.schedule.dayCount'),
            headerTooltip: () => $t('assets.schedule.dayCountHint'),
            headerTooltipUrl: '/mkdocs/financial-theory/day-count/',
            type: 'custom',
            sortable: false,
            filterable: false,
            width: 100,
            minWidth: 80,
            cell: (row: ScheduleRow): CellContent => ({
                type: 'editable-select',
                value: row.day_count,
                options: DAY_COUNT_OPTIONS,
                onchange: (v: string) => updateRow(row.id, 'day_count', v),
            }),
        },
    ]);

    let rowActions = $derived<RowAction<ScheduleRow>[]>([
        {
            id: 'split',
            icon: Scissors,
            label: () => $t('assets.schedule.split'),
            visible: (row) => !row.isLate,
            disabled: (row) => disabled || readonly || daysBetween(row.start_date, row.end_date) <= 1,
            onClick: (row) => {
                const idx = normalRows.findIndex(r => r.id === row.id);
                if (idx >= 0) handleSplitRequest(idx);
            },
        },
        {
            id: 'delete',
            icon: X,
            label: () => $t('common.delete'),
            variant: 'danger',
            visible: (row) => !row.isLate,
            disabled: () => disabled || readonly,
            onClick: (row) => {
                const idx = normalRows.findIndex(r => r.id === row.id);
                if (idx >= 0) handleDelete(idx);
            },
        },
    ]);

    /** Bulk actions for DataTableToolbar */
    let bulkActions = $derived([
        {
            id: 'merge',
            icon: Link2,
            label: () => $t('assets.schedule.merge'),
            onClick: () => handleMerge(),
            disabled: !areSelectedContiguous,
        },
        {
            id: 'delete',
            icon: Trash2,
            label: () => $t('assets.schedule.deleteSelected'),
            variant: 'danger' as const,
            onClick: () => handleBulkDelete(),
        },
    ]);

    function getRowId(row: ScheduleRow): string {
        return row.id;
    }

    function getRowClass(row: ScheduleRow): string {
        if (row.isLate && !row.enabled) return 'late-row-disabled';
        if (row.isLate) return 'late-row';
        return '';
    }

    function handleSelectionChange(ids: string[]) {
        // Exclude late interest from selection
        selectedIds = ids.filter(id => id !== 'late-interest');
    }
</script>

<div class="space-y-3">
    <!-- Header: title + bulk toolbar + Add button (all inline) -->
    <div class="flex items-center gap-2 flex-wrap">
        <div class="flex items-center gap-2">
            <CalendarDays size={16} class="text-gray-400"/>
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
                {$t('assets.schedule.title')}
            </span>
        </div>

        <!-- Inline bulk toolbar (shown when rows selected) -->
        {#if selectedIds.length > 0}
            <div class="flex items-center gap-1.5 ml-2 pl-2 border-l border-gray-200 dark:border-slate-600">
                <button
                    type="button"
                    class="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-md
                           bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300
                           hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
                    onclick={() => { selectedIds = []; }}
                    title={$t('table.clearSelection') || 'Clear selection'}
                >
                    <span>{selectedIds.length}</span>
                    <span class="hidden sm:inline">{$t('common.selected')}</span>
                    <span class="text-gray-400">×</span>
                </button>
                {#each bulkActions as action}
                    <button
                        type="button"
                        onclick={action.onClick}
                        disabled={action.disabled}
                        title={typeof action.label === 'function' ? action.label() : action.label}
                        class="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-md transition-colors
                               disabled:opacity-40 disabled:cursor-not-allowed
                               {action.variant === 'danger'
                                   ? 'text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20'
                                   : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700'}"
                    >
                        <action.icon size={14}/>
                        <span class="hidden sm:inline">
                            {typeof action.label === 'function' ? action.label() : action.label}
                        </span>
                    </button>
                {/each}
            </div>
        {/if}

        <!-- Spacer + Add Period (pushed right) -->
        {#if !readonly && !disabled}
            <div class="flex-1"></div>
            <button
                type="button"
                onclick={handleAddPeriod}
                class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg
                       border border-gray-200 dark:border-slate-600
                       text-gray-600 dark:text-gray-300 bg-white dark:bg-slate-800
                       hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
            >
                <Plus size={14}/>
                <span class="hidden sm:inline">{$t('assets.schedule.addPeriod')}</span>
            </button>
        {/if}
    </div>


    <!-- DataTable or Empty State -->
    {#if normalRows.length === 0 && (!lateRow || !lateRow.enabled)}
        <!-- Empty state -->
        <div class="p-8 border border-dashed border-gray-300 dark:border-slate-600 rounded-xl text-center space-y-3">
            <div class="text-3xl">📅</div>
            <div class="text-sm text-gray-500 dark:text-gray-400">
                {$t('assets.schedule.emptyTitle')}
            </div>
            <p class="text-xs text-gray-400 dark:text-gray-500">
                {$t('assets.schedule.emptyHint')}
            </p>
            {#if !readonly && !disabled}
                <button
                    type="button"
                    onclick={handleAddPeriod}
                    class="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg
                           bg-libre-green text-white hover:bg-libre-green-dark transition-colors"
                >
                    <Plus size={14}/>
                    {$t('assets.schedule.addFirstPeriod')}
                </button>
            {/if}
        </div>
    {:else}
        <DataTable
            data={tableData}
            columns={columns}
            {getRowId}
            storageKey="schedule-editor"
            enableSelection={!readonly && !disabled}
            selectionMode="multi"
            onSelectionChange={handleSelectionChange}
            enableActions={!readonly && !disabled}
            rowActions={rowActions}
            enableSorting={false}
            enableColumnFilters={false}
            enableColumnResize={true}
            enableColumnVisibility={false}
            enablePagination={false}
            getRowClass={getRowClass}
            tableLayout="auto"
        />
    {/if}

    <!-- Late interest toggle (always visible if lateRow exists and there are normal periods) -->
    {#if lateRow && normalRows.length > 0}
        <div class="flex items-center justify-end gap-2 text-xs text-gray-500 dark:text-gray-400">
            <span>⚡ {$t('assets.schedule.lateInterest')}</span>
            <button
                type="button"
                onclick={toggleLateInterest}
                disabled={disabled || readonly}
                aria-label="Toggle late interest"
                class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors
                       {lateRow.enabled ? 'bg-libre-green' : 'bg-gray-300 dark:bg-slate-600'}
                       disabled:opacity-50 disabled:cursor-not-allowed"
            >
                <span class="inline-block h-3.5 w-3.5 rounded-full bg-white shadow-sm transition-transform
                             {lateRow.enabled ? 'translate-x-[18px]' : 'translate-x-[3px]'}"></span>
            </button>
        </div>
    {/if}

    <!-- Status banner -->
    <div class="flex items-center gap-2 text-xs {statusBanner.ok ? 'text-green-600 dark:text-green-400' : 'text-gray-400 dark:text-gray-500'}">
        <span>{statusBanner.icon}</span>
        <span>{statusBanner.text}</span>
    </div>
</div>

<!-- Boundary Date Modal -->
<BoundaryDateModal
    bind:open={showBoundaryModal}
    mode={boundaryModalMode}
    minDate={boundaryModalMin}
    maxDate={boundaryModalMax}
    defaultDate={boundaryModalDefault}
    onconfirm={handleBoundaryConfirm}
    oncancel={() => { showBoundaryModal = false; }}
/>

<style>
    :global(.late-row-disabled) {
        opacity: 0.4;
        background-color: rgb(249 250 251) !important;
    }

    :global(.dark .late-row-disabled) {
        background-color: rgb(15 23 42 / 0.5) !important;
    }

    :global(.late-row) {
        border-top: 2px dashed rgb(209 213 219);
    }

    :global(.dark .late-row) {
        border-top: 2px dashed rgb(71 85 105);
    }
</style>

