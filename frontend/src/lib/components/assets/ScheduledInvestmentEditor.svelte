<!--
  ScheduledInvestmentEditor — DataTable-based editor for interest schedules.

  Features:
  - Editable DataTable with Period, Rate %, Maturation Frequency, Day Count
  - Late Interest as permanent special row with toggle on/off
  - Automatic contiguity propagation (no overlaps/gaps by design)
  - CRUD: Add, Delete (with boundary modal), Split, Merge
  - Bulk delete with multi-gap support
  - JSON ↔ form bidirectional serialization
  - Asset Events table (INTEREST payouts, PRICE_ADJUSTMENT write-downs)

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

    interface AssetEventRow {
        id: string;
        date: string;
        type: 'INTEREST' | 'PRICE_ADJUSTMENT';
        value: number;
        currency: string;
        notes: string;
    }

    // These event types are embedded in provider_params JSON and not exposed as
    // top-level OpenAPI schemas, so they cannot be auto-generated via api-sync.
    // Source of truth: backend/app/schemas/prices.py → FAAssetEventPoint.type
    const EVENT_TYPE_OPTIONS = [
        {value: 'INTEREST', labelKey: 'assets.schedule.eventType.INTEREST'},
        {value: 'PRICE_ADJUSTMENT', labelKey: 'assets.schedule.eventType.PRICE_ADJUSTMENT'},
    ];

    // =========================================================================
    // Types
    // =========================================================================

    interface ScheduleRow {
        id: string;
        start_date: string;
        end_date: string;
        annual_rate: number;
        maturation_frequency: string;
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

    // Source of truth: backend/app/schemas/assets.py → InterestType enum
    const INTEREST_TYPE_OPTIONS = [
        {value: 'SIMPLE', label: '📊 Simple'},
        {value: 'COMPOUND', label: '📈 Compound'},
    ];

    // Source of truth: backend/app/schemas/assets.py → DayCountConvention enum
    const DAY_COUNT_OPTIONS = [
        {value: 'ACT/365', label: 'ACT/365'},
        {value: 'ACT/360', label: 'ACT/360'},
        {value: 'ACT/ACT', label: 'ACT/ACT'},
        {value: '30/360', label: '30/360'},
    ];

    // Source of truth: backend/app/schemas/assets.py → MaturationFrequency enum
    const MATURATION_FREQ_OPTIONS = [
        {value: 'DAILY', label: 'Daily'},
        {value: 'WEEKLY', label: 'Weekly'},
        {value: 'MONTHLY', label: 'Monthly'},
        {value: 'QUARTERLY', label: 'Quarterly'},
        {value: 'SEMIANNUAL', label: 'Semiannual'},
        {value: 'ANNUAL', label: 'Annual'},
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

    // Initial Value + Currency + Asset Events state
    let initialValue = $state<number>(10000);
    let currencyValue = $state<string>('EUR');
    let assetEvents = $state<AssetEventRow[]>([]);

    // Global schedule properties (apply to ALL periods)
    let interestType = $state<string>('SIMPLE');
    let dayCount = $state<string>('ACT/365');

    // Sync from prop (only on external changes)
    $effect(() => {
        // Read value to track reactivity
        const v = value;
        if (internalUpdate) {
            internalUpdate = false;
            return;
        }
        rows = deserializeRows(v);
        // initial_value is now a Currency object: {code: string, amount: string|number}
        if (v?.initial_value && typeof v.initial_value === 'object') {
            initialValue = Number(v.initial_value.amount ?? 10000);
            currencyValue = v.initial_value.code ?? 'EUR';
        } else {
            initialValue = v?.initial_value != null ? Number(v.initial_value) : 10000;
            currencyValue = v?.currency ?? 'EUR';
        }
        // Global properties
        interestType = v?.interest_type ?? 'SIMPLE';
        dayCount = v?.day_count ?? 'ACT/365';
        assetEvents = deserializeEvents(v?.asset_events ?? []);
    });

    // Modal state
    let showBoundaryModal = $state(false);
    let boundaryModalMode = $state<'delete' | 'split'>('delete');
    let boundaryModalMin = $state('');
    let boundaryModalMax = $state('');
    let boundaryModalDefault = $state('');
    let pendingActionIndex = $state(-1);
    /** Multi-gap modal state */
    interface PendingGap {
        minDate: string;
        maxDate: string;
        defaultDate: string;
        label?: string;
    }
    let pendingBulkGaps = $state<PendingGap[]>([]);
    /** Full pending bulk delete info (indices + auto-resolved head/tail) */
    let pendingBulkDeleteData = $state<{
        indices: number[];
        headIndices: number[];
        tailIndices: number[];
        middleGroups: { indices: number[]; prevIdx: number; nextIdx: number }[];
    } | null>(null);

    // =========================================================================
    // Derived
    // =========================================================================

    let normalRows = $derived(rows.filter(r => !r.isLate));
    let lateRow = $derived(rows.find(r => r.isLate));

    /** All rows for DataTable: normal periods + late interest (only when enabled) */
    let tableData = $derived.by(() => {
        const result: ScheduleRow[] = [...normalRows];
        if (lateRow?.enabled) result.push(lateRow);
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
            if (false /* always simple */) return false;
        }
        if (lateRow?.enabled) {
            if (lateRow.annual_rate < 0) return false;
            if (lateRow.grace_period_days < 0) return false;
            if (false /* always simple */) return false;
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

    function deserializeRows(val: Record<string, any>): ScheduleRow[] {
        const result: ScheduleRow[] = [];
        const schedule = val?.schedule ?? [];

        for (const p of schedule) {
            result.push({
                id: crypto.randomUUID(),
                start_date: p.start_date,
                end_date: p.end_date,
                annual_rate: Number(p.annual_rate) * 100,
                maturation_frequency: p.maturation_frequency ?? 'DAILY',
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
            maturation_frequency: li?.maturation_frequency ?? 'DAILY',
            isLate: true,
            grace_period_days: li?.grace_period_days ?? 0,
            enabled: !!li,
        });

        return result;
    }

    function deserializeEvents(events: any[]): AssetEventRow[] {
        return events.map((e: any) => ({
            id: crypto.randomUUID(),
            date: e.date ?? todayISO(),
            type: e.type ?? 'INTEREST',
            value: Number(e.value?.amount ?? e.value ?? 0),
            currency: e.value?.code ?? e.currency ?? '',
            notes: e.notes ?? '',
        }));
    }

    function serialize(allRows: ScheduleRow[]): Record<string, any> {
        const schedule = allRows
            .filter(r => !r.isLate)
            .map(r => ({
                start_date: r.start_date,
                end_date: r.end_date,
                annual_rate: (r.annual_rate / 100).toFixed(4),
                maturation_frequency: r.maturation_frequency,
            }));

        const lr = allRows.find(r => r.isLate && r.enabled);
        const late_interest = lr ? {
            annual_rate: (lr.annual_rate / 100).toFixed(4),
            grace_period_days: lr.grace_period_days,
        } : null;

        const serializedEvents = assetEvents.map(e => ({
            date: e.date,
            type: e.type,
            value: {code: e.currency || currencyValue, amount: e.value.toString()},
            notes: e.notes || undefined,
        }));

        return {
            initial_value: {code: currencyValue, amount: initialValue.toString()},
            interest_type: interestType,
            day_count: dayCount,
            schedule,
            late_interest,
            asset_events: serializedEvents,
        };
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
            maturation_frequency: lastPeriod?.maturation_frequency ?? 'DAILY',
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
            pendingBulkGaps = [];
            pendingBulkDeleteData = null;
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
        pendingBulkGaps = [];
        pendingBulkDeleteData = null;
        boundaryModalMode = 'split';
        boundaryModalMin = addDays(period.start_date, 1);
        boundaryModalMax = addDays(period.end_date, -1);
        boundaryModalDefault = midpointDate(period.start_date, period.end_date);
        showBoundaryModal = true;
    }

    function handleBoundaryConfirm(boundaryDate: string): void {
        if (boundaryModalMode === 'delete') {
            confirmDelete(boundaryDate);
        } else {
            confirmSplit(boundaryDate);
        }
    }

    /** Multi-gap confirm from BoundaryDateModal */
    function handleBoundaryConfirmMulti(boundaryDates: string[]): void {
        confirmBulkDeleteMulti(boundaryDates);
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

    /** Group sorted indices into contiguous blocks */
    function groupContiguousIndices(indices: number[]): number[][] {
        if (indices.length === 0) return [];
        const groups: number[][] = [[indices[0]]];
        for (let i = 1; i < indices.length; i++) {
            if (indices[i] === indices[i - 1] + 1) {
                groups[groups.length - 1].push(indices[i]);
            } else {
                groups.push([indices[i]]);
            }
        }
        return groups;
    }

    function handleBulkDelete(): void {
        if (selectedNormalRows.length === 0) return;
        const periods = [...normalRows];
        const indices = selectedNormalRows
            .map(r => periods.findIndex(p => p.id === r.id))
            .filter(i => i >= 0)
            .sort((a, b) => a - b);

        if (indices.length === 0) return;

        // If all rows selected → empty state, no modal needed
        if (indices.length === periods.length) {
            selectedIds = [];
            rebuildAndEmit([]);
            return;
        }

        // Group into contiguous blocks
        const groups = groupContiguousIndices(indices);

        // Classify each group: HEAD (no prev), TAIL (no next), MIDDLE (both)
        const headIndices: number[] = [];
        const tailIndices: number[] = [];
        const middleGroups: { indices: number[]; prevIdx: number; nextIdx: number }[] = [];

        for (const group of groups) {
            const first = group[0];
            const last = group[group.length - 1];
            const hasPrev = first > 0;
            const hasNext = last < periods.length - 1;

            if (hasPrev && hasNext) {
                middleGroups.push({
                    indices: group,
                    prevIdx: first - 1,
                    nextIdx: last + 1,
                });
            } else if (!hasPrev) {
                headIndices.push(...group);
            } else {
                tailIndices.push(...group);
            }
        }

        // If no middle groups → auto-resolve everything without modal
        if (middleGroups.length === 0) {
            // HEAD: expand next survivor backward
            if (headIndices.length > 0) {
                const lastHead = headIndices[headIndices.length - 1];
                const headStart = periods[headIndices[0]].start_date;
                // Find first non-deleted index after the head block
                const nextSurvivor = lastHead + 1;
                if (nextSurvivor < periods.length && !indices.includes(nextSurvivor)) {
                    periods[nextSurvivor].start_date = headStart;
                }
            }
            // TAIL: expand prev survivor forward
            if (tailIndices.length > 0) {
                const firstTail = tailIndices[0];
                const tailEnd = periods[tailIndices[tailIndices.length - 1]].end_date;
                const prevSurvivor = firstTail - 1;
                if (prevSurvivor >= 0 && !indices.includes(prevSurvivor)) {
                    periods[prevSurvivor].end_date = tailEnd;
                }
            }

            // Remove all selected (reverse order)
            for (let i = indices.length - 1; i >= 0; i--) {
                periods.splice(indices[i], 1);
            }
            selectedIds = [];
            rebuildAndEmit(periods);
            return;
        }

        // Build gaps for the modal (one per middle group)
        const gaps: PendingGap[] = middleGroups.map((mg, i) => {
            const blockStart = periods[mg.indices[0]].start_date;
            const blockEnd = periods[mg.indices[mg.indices.length - 1]].end_date;
            return {
                minDate: blockStart,
                maxDate: blockEnd,
                defaultDate: midpointDate(blockStart, blockEnd),
                label: middleGroups.length > 1
                    ? `Gap ${i + 1}: ${blockStart} → ${blockEnd}`
                    : undefined,
            };
        });

        // Store data for confirm
        pendingBulkDeleteData = { indices, headIndices, tailIndices, middleGroups };
        pendingBulkGaps = gaps;
        pendingActionIndex = -1;
        boundaryModalMode = 'delete';

        // If single middle group → use single-gap mode for simplicity
        if (gaps.length === 1) {
            boundaryModalMin = gaps[0].minDate;
            boundaryModalMax = gaps[0].maxDate;
            boundaryModalDefault = gaps[0].defaultDate;
            pendingBulkGaps = []; // use single-gap mode
        }

        showBoundaryModal = true;
    }

    /** Confirm bulk delete with a single boundary (single middle group) */
    function confirmBulkDeleteSingle(boundaryDate: string): void {
        if (!pendingBulkDeleteData) return;
        confirmBulkDeleteMulti([boundaryDate]);
    }

    /** Confirm bulk delete with multiple boundary dates (one per middle group) */
    function confirmBulkDeleteMulti(boundaryDates: string[]): void {
        if (!pendingBulkDeleteData) return;
        const { indices, headIndices, tailIndices, middleGroups } = pendingBulkDeleteData;
        const periods = [...normalRows];

        // Apply HEAD auto-expansion
        if (headIndices.length > 0) {
            const lastHead = headIndices[headIndices.length - 1];
            const headStart = periods[headIndices[0]].start_date;
            const nextSurvivor = lastHead + 1;
            if (nextSurvivor < periods.length && !indices.includes(nextSurvivor)) {
                periods[nextSurvivor].start_date = headStart;
            }
        }

        // Apply TAIL auto-expansion
        if (tailIndices.length > 0) {
            const firstTail = tailIndices[0];
            const tailEnd = periods[tailIndices[tailIndices.length - 1]].end_date;
            const prevSurvivor = firstTail - 1;
            if (prevSurvivor >= 0 && !indices.includes(prevSurvivor)) {
                periods[prevSurvivor].end_date = tailEnd;
            }
        }

        // Apply MIDDLE boundary dates
        for (let i = 0; i < middleGroups.length; i++) {
            const mg = middleGroups[i];
            const boundary = boundaryDates[i];
            periods[mg.prevIdx].end_date = boundary;
            periods[mg.nextIdx].start_date = addDays(boundary, 1);
        }

        // Remove all selected (reverse order to preserve indices)
        for (let i = indices.length - 1; i >= 0; i--) {
            periods.splice(indices[i], 1);
        }

        selectedIds = [];
        pendingBulkDeleteData = null;
        pendingBulkGaps = [];
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
                    disabled: disabled || readonly,
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
            id: 'maturation_frequency',
            header: () => $t('assets.schedule.maturationFrequency'),
            headerTooltip: () => $t('assets.schedule.maturationFrequencyHint'),
            headerTooltipUrl: '/mkdocs/financial-theory/synthetic-benchmarks/#compound-growth',
            type: 'custom',
            sortable: false,
            filterable: false,
            width: 120,
            minWidth: 100,
            cell: (row: ScheduleRow): CellContent => ({
                type: 'editable-select',
                value: row.maturation_frequency,
                options: MATURATION_FREQ_OPTIONS,
                onchange: (v: string) => updateRow(row.id, 'maturation_frequency', v),
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
        if (row.isLate) return 'late-row';
        return '';
    }

    function handleSelectionChange(ids: string[]) {
        // Exclude late interest from selection
        selectedIds = ids.filter(id => id !== 'late-interest');
    }

    // =========================================================================
    // Asset Events CRUD
    // =========================================================================

    function handleAddEvent(): void {
        assetEvents = [...assetEvents, {
            id: crypto.randomUUID(),
            date: todayISO(),
            type: 'INTEREST',
            value: 0,
            currency: currencyValue,
            notes: '',
        }];
        emitChange();
    }

    function handleDeleteEvent(index: number): void {
        assetEvents = assetEvents.filter((_, i) => i !== index);
        emitChange();
    }

    function handleEventFieldChange(index: number, field: keyof AssetEventRow, val: any): void {
        assetEvents = assetEvents.map((e, i) => {
            if (i !== index) return e;
            return {...e, [field]: val};
        });
        emitChange();
    }
</script>

<div class="space-y-3">
    <!-- Initial Value + Currency + Global settings (inline rows) -->
    <div class="flex items-end gap-4 flex-wrap">
        <div class="flex-1 max-w-xs">
            <label for="initial-value" class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                💰 {$t('assets.schedule.initialValue')}
            </label>
            <input
                id="initial-value"
                type="number"
                min="0.01"
                step="100"
                value={initialValue}
                oninput={(e) => {
                    const el = e.currentTarget as HTMLInputElement;
                    initialValue = Number(el.value) || 0;
                    emitChange();
                }}
                disabled={disabled || readonly}
                class="w-full px-3 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                       bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                       focus:outline-none focus:ring-2 focus:ring-libre-green/50
                       disabled:opacity-50"
            />
        </div>
        <div class="w-32">
            <label for="currency-select" class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                💱 {$t('assets.schedule.currency')}
            </label>
            <input
                id="currency-select"
                type="text"
                value={currencyValue}
                maxlength={3}
                oninput={(e) => {
                    const el = e.currentTarget as HTMLInputElement;
                    currencyValue = el.value.toUpperCase();
                    emitChange();
                }}
                disabled={disabled || readonly}
                placeholder="EUR"
                class="w-full px-3 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                       bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                       focus:outline-none focus:ring-2 focus:ring-libre-green/50
                       disabled:opacity-50 uppercase"
            />
        </div>
        <div class="w-40">
            <label for="interest-type-select" class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                📐 {$t('assets.schedule.interestType') || 'Interest Type'}
            </label>
            <select
                id="interest-type-select"
                value={interestType}
                onchange={(e) => {
                    interestType = (e.currentTarget as HTMLSelectElement).value;
                    emitChange();
                }}
                disabled={disabled || readonly}
                class="w-full px-3 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                       bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                       focus:outline-none focus:ring-2 focus:ring-libre-green/50
                       disabled:opacity-50"
            >
                {#each INTEREST_TYPE_OPTIONS as opt}
                    <option value={opt.value}>{opt.label}</option>
                {/each}
            </select>
        </div>
        <div class="w-36">
            <label for="day-count-select" class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                📆 {$t('assets.schedule.dayCount') || 'Day Count'}
            </label>
            <select
                id="day-count-select"
                value={dayCount}
                onchange={(e) => {
                    dayCount = (e.currentTarget as HTMLSelectElement).value;
                    emitChange();
                }}
                disabled={disabled || readonly}
                class="w-full px-3 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                       bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                       focus:outline-none focus:ring-2 focus:ring-libre-green/50
                       disabled:opacity-50"
            >
                {#each DAY_COUNT_OPTIONS as opt}
                    <option value={opt.value}>{opt.label || opt.value}</option>
                {/each}
            </select>
        </div>
    </div>

    <!-- Header: title + bulk toolbar + Add button (all inline) -->
    <div class="flex items-center gap-2 flex-wrap">
        <div class="flex items-center gap-2">
            <CalendarDays size={16} class="text-gray-400"/>
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
                {$t('assets.schedule.title')}
            </span>
        </div>

        <!-- Spacer pushes everything after this to the right -->
        <div class="flex-1"></div>

        <!-- Inline bulk toolbar (shown when rows selected) — right-aligned -->
        {#if selectedIds.length > 0}
            <div class="flex items-center gap-1.5 pr-2 border-r border-gray-200 dark:border-slate-600">
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

        <!-- Add Period (right-most) -->
        {#if !readonly && !disabled}
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
            isRowSelectable={(row) => !row.isLate}
        />
    {/if}

    <!-- Asset Events Section -->
    <div class="space-y-2">
        <div class="flex items-center justify-between">
            <span class="text-xs font-medium text-gray-500 dark:text-gray-400">📋 {$t('assets.schedule.assetEvents')}</span>
            {#if !readonly && !disabled}
                <button
                    type="button"
                    onclick={handleAddEvent}
                    class="flex items-center gap-1 px-2 py-1 text-xs rounded-md
                           border border-gray-200 dark:border-slate-600
                           text-gray-600 dark:text-gray-300 bg-white dark:bg-slate-800
                           hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
                >
                    <Plus size={12}/>
                    <span>{$t('assets.schedule.addEvent')}</span>
                </button>
            {/if}
        </div>
        {#if assetEvents.length > 0}
            <div class="border border-gray-200 dark:border-slate-600 rounded-lg overflow-hidden">
                <table class="w-full text-xs">
                    <thead class="bg-gray-50 dark:bg-slate-800">
                        <tr>
                            <th class="px-2 py-1.5 text-left font-medium text-gray-500 dark:text-gray-400">{$t('common.date')}</th>
                            <th class="px-2 py-1.5 text-left font-medium text-gray-500 dark:text-gray-400">{$t('common.type')}</th>
                            <th class="px-2 py-1.5 text-left font-medium text-gray-500 dark:text-gray-400">{$t('common.value')}</th>
                            <th class="px-2 py-1.5 text-left font-medium text-gray-500 dark:text-gray-400">{$t('common.notes')}</th>
                            <th class="px-2 py-1.5 w-8"></th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each assetEvents as evt, idx}
                            <tr class="border-t border-gray-100 dark:border-slate-700">
                                <td class="px-2 py-1">
                                    <input type="date" value={evt.date}
                                        oninput={(e) => handleEventFieldChange(idx, 'date', (e.currentTarget as HTMLInputElement).value)}
                                        disabled={disabled || readonly}
                                        class="w-full px-1 py-0.5 text-xs border border-gray-200 dark:border-slate-600 rounded
                                               bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                                               disabled:opacity-50"
                                    />
                                </td>
                                <td class="px-2 py-1">
                                    <select value={evt.type}
                                        onchange={(e) => handleEventFieldChange(idx, 'type', (e.currentTarget as HTMLSelectElement).value)}
                                        disabled={disabled || readonly}
                                        class="w-full px-1 py-0.5 text-xs border border-gray-200 dark:border-slate-600 rounded
                                               bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                                               disabled:opacity-50"
                                    >
                                        {#each EVENT_TYPE_OPTIONS as opt}
                                            <option value={opt.value}>{$t(opt.labelKey)}</option>
                                        {/each}
                                    </select>
                                </td>
                                <td class="px-2 py-1">
                                    <input type="number" value={evt.value} step="0.01"
                                        oninput={(e) => handleEventFieldChange(idx, 'value', Number((e.currentTarget as HTMLInputElement).value))}
                                        disabled={disabled || readonly}
                                        class="w-full px-1 py-0.5 text-xs border border-gray-200 dark:border-slate-600 rounded
                                               bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                                               disabled:opacity-50"
                                    />
                                </td>
                                <td class="px-2 py-1">
                                    <input type="text" value={evt.notes} placeholder="optional"
                                        oninput={(e) => handleEventFieldChange(idx, 'notes', (e.currentTarget as HTMLInputElement).value)}
                                        disabled={disabled || readonly}
                                        class="w-full px-1 py-0.5 text-xs border border-gray-200 dark:border-slate-600 rounded
                                               bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                                               disabled:opacity-50"
                                    />
                                </td>
                                <td class="px-2 py-1">
                                    {#if !readonly && !disabled}
                                        <button type="button" onclick={() => handleDeleteEvent(idx)}
                                            class="text-red-400 hover:text-red-600 transition-colors">
                                            <X size={14}/>
                                        </button>
                                    {/if}
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {:else}
            <div class="text-xs text-gray-400 dark:text-gray-500 italic pl-1">
                {$t('assets.schedule.noEvents')}
            </div>
        {/if}
    </div>

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
    gaps={pendingBulkGaps}
    onconfirm={(bd) => {
        if (pendingBulkDeleteData) {
            confirmBulkDeleteSingle(bd);
        } else {
            handleBoundaryConfirm(bd);
        }
    }}
    onconfirmMulti={handleBoundaryConfirmMulti}
    oncancel={() => { showBoundaryModal = false; pendingBulkDeleteData = null; pendingBulkGaps = []; }}
/>

<style>

    :global(.late-row) {
        border-top: 2px dashed rgb(209 213 219);
    }

    :global(.dark .late-row) {
        border-top: 2px dashed rgb(71 85 105);
    }
</style>

