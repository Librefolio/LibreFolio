<!--
  FxDataEditorSection — FX-specific wrapper around the generic DataEditor.

  Handles:
  - Converting FxDataPoint[] ↔ DataRow[] (with 'rate' column)
  - API calls for upsert (edited + appended) and delete
  - Dirty tracking → chart preview (pending orange points)
  - scrollToDate() API for chart-to-editor navigation

  Replaces FxEditSection.svelte.
  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {Save, X} from 'lucide-svelte';
    import {zodiosApi} from '$lib/api';
    import DataEditor from '$lib/components/ui/data-editor/DataEditor.svelte';
    import type {ColumnDef, DataRow} from '$lib/components/ui/data-editor/DataEditorTypes';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import type {FxDataPoint} from '$lib/stores/fxStoreRegistry';
    import type {RenderedSignal} from '$lib/charts/signals';
    import {toasts} from '$lib/stores/toastStore.svelte';
    import FxDataImportModal from './FxDataImportModal.svelte';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Base currency code */
        base: string;
        /** Quote currency code */
        quote: string;
        /** Current chart data from TimeSeriesStore */
        chartData: FxDataPoint[];
        /** Whether save is in progress */
        saving?: boolean;
        /** Number of dirty (modified) rows — exposed for parent to read */
        dirtyCount?: number;
        /** Called after successful save, with optional expanded date range */
        onsave?: (expandedRange?: { start: string; end: string }) => void;
        /** Called when edit is cancelled */
        oncancel?: () => void;
        /** Dirty rows emitted as a preview RenderedSignal overlay (purple) */
        onpendingchange?: (previewSignal: RenderedSignal | null) => void;
    }

    let {
        base,
        quote,
        chartData,
        saving = $bindable(false),
        dirtyCount = $bindable(0),
        onsave,
        oncancel,
        onpendingchange,
    }: Props = $props();

    // =========================================================================
    // Column definition for FX (single 'rate' column)
    // =========================================================================

    const fxColumns: ColumnDef[] = [
        {
            key: 'rate',
            label: 'Rate',
            type: 'number',
            editable: true,
            required: true,
            step: 0.0001,
            min: 0,
            placeholder: '1.0823',
        },
    ];

    // =========================================================================
    // State
    // =========================================================================

    let dataEditor: DataEditor | undefined = $state(undefined);
    let rows: DataRow[] = $state([]);
    let error: string | null = $state(null);
    let prevChartData: FxDataPoint[] | null = null;

    // =========================================================================
    // Convert FxDataPoint[] → DataRow[]
    // =========================================================================

    function chartDataToRows(data: FxDataPoint[]): DataRow[] {
        return data.map(dp => ({
            rowId: dp.date,
            date: dp.date,
            status: 'original' as const,
            originalStatus: 'original' as const,
            values: {rate: dp.rate},
            selected: false,
            _originalValues: {rate: dp.rate},
            staleDays: dp.backwardFillInfo?.daysBack ?? 0,
        }));
    }

    // Initialize rows from chartData — only when chartData actually changes (referential)
    $effect(() => {
        if (chartData !== prevChartData) {
            prevChartData = chartData;
            rows = chartDataToRows(chartData);
        }
    });

    // =========================================================================
    // Dirty tracking → chart preview
    // =========================================================================

    function handleDataChange(dirtyRows: DataRow[]) {
        // Convert edited/appended rows to a RenderedSignal overlay for chart preview
        const pendingPoints: LineDataPoint[] = dirtyRows
            .filter(r => r.status === 'edited' || r.status === 'appended')
            .filter(r => r.values.rate !== undefined && r.values.rate !== null)
            .map(r => ({
                date: r.date,
                value: Number(r.values.rate),
            }));

        if (pendingPoints.length === 0) {
            onpendingchange?.(null);
            return;
        }

        // Build a RenderedSignal overlay (purple preview line)
        const previewSignal: RenderedSignal = {
            id: '__preview__',
            label: 'Preview',
            data: pendingPoints.sort((a, b) => a.date.localeCompare(b.date)),
            color: '#a855f7',
            lineWidth: 3,
            lineType: 'solid',
            markerStart: null,
            markerEnd: null,
            yAxisIndex: 0,
        };

        onpendingchange?.(previewSignal);
    }

    // =========================================================================
    // Save & Cancel
    // =========================================================================

    async function handleSave() {
        const dirty = rows.filter(r => r.status !== 'original');
        if (dirty.length === 0) return;

        saving = true;
        error = null;

        try {
            // Upsert edited + appended rows
            const upsertRows = dirty.filter(r => r.status === 'edited' || r.status === 'appended');

            // Validate: filter out rows with invalid rate (undefined, NaN, <= 0)
            const validUpserts = upsertRows.filter(r => {
                const rate = Number(r.values.rate);
                return !isNaN(rate) && rate > 0;
            });
            const invalidCount = upsertRows.length - validUpserts.length;

            // Delete rows marked as deleted
            const deleteRows = dirty.filter(r => r.status === 'deleted');

            // If all upserts invalid and no deletes, show error
            if (invalidCount > 0 && validUpserts.length === 0 && deleteRows.length === 0) {
                error = `${invalidCount} row(s) have invalid rate values. Rate must be strictly greater than zero (0 is not allowed).`;
                saving = false;
                return;
            }

            let upsertedCount = 0;
            let deletedCount = 0;

            if (validUpserts.length > 0) {
                // Normalize base/quote to alphabetical order (backend convention)
                const baseNorm = base < quote ? base : quote;
                const quoteNorm = base < quote ? quote : base;
                const isInverted = base > quote;

                const rateItems = validUpserts.map(r => ({
                    base: baseNorm,
                    quote: quoteNorm,
                    date: r.date,
                    rate: isInverted ? 1 / Number(r.values.rate) : Number(r.values.rate),
                }));
                await zodiosApi.upsert_rates_endpoint_api_v1_fx_currencies_rate_post(rateItems);
                upsertedCount = validUpserts.length;
            }

            if (deleteRows.length > 0) {
                // Merge consecutive dates into ranges for fewer API items
                const baseNormDel = base < quote ? base : quote;
                const quoteNormDel = base < quote ? quote : base;
                const sortedDates = deleteRows.map(dr => dr.date).sort();
                const ranges: Array<{ start: string; end?: string }> = [];
                let rangeStart = sortedDates[0];
                let rangeEnd = sortedDates[0];
                for (let i = 1; i < sortedDates.length; i++) {
                    const prev = new Date(rangeEnd);
                    const curr = new Date(sortedDates[i]);
                    const diffDays = (curr.getTime() - prev.getTime()) / (1000 * 60 * 60 * 24);
                    if (diffDays <= 1) {
                        rangeEnd = sortedDates[i];
                    } else {
                        ranges.push(rangeStart === rangeEnd ? {start: rangeStart} : {start: rangeStart, end: rangeEnd});
                        rangeStart = sortedDates[i];
                        rangeEnd = sortedDates[i];
                    }
                }
                ranges.push(rangeStart === rangeEnd ? {start: rangeStart} : {start: rangeStart, end: rangeEnd});

                const deleteItems = ranges.map(r => ({
                    from: baseNormDel,
                    to: quoteNormDel,
                    date_range: r,
                }));
                await zodiosApi.delete_rates_endpoint_api_v1_fx_currencies_rate_delete(deleteItems);
                deletedCount = deleteRows.length;
            }

            // Toast success
            const parts: string[] = [];
            if (upsertedCount > 0) parts.push(`${upsertedCount} saved`);
            if (deletedCount > 0) parts.push(`${deletedCount} deleted`);
            if (invalidCount > 0) parts.push(`${invalidCount} skipped (invalid)`);
            toasts.success(`FX rates: ${parts.join(', ')}`);

            // Compute expanded date range if appended rows fall outside current chart range
            const appendedRows = dirty.filter(r => r.status === 'appended');
            let expandedRange: { start: string; end: string } | undefined;
            if (appendedRows.length > 0 && chartData.length > 0) {
                const chartDates = chartData.map(d => d.date).sort();
                const chartStart = chartDates[0];
                const chartEnd = chartDates[chartDates.length - 1];
                const allDates = [...chartDates, ...appendedRows.map(r => r.date)].sort();
                const newStart = allDates[0];
                const newEnd = allDates[allDates.length - 1];
                if (newStart < chartStart || newEnd > chartEnd) {
                    expandedRange = {start: newStart, end: newEnd};
                }
            }

            onsave?.(expandedRange);
        } catch (e: any) {
            console.error('Failed to save rates:', e);
            const msg = e?.message || 'unknown error';
            error = 'Failed to save: ' + msg;
            toasts.error(`FX save failed: ${msg}`);
        } finally {
            saving = false;
        }
    }

    function handleCancel() {
        // Reset rows from original chart data
        rows = chartDataToRows(chartData);
        onpendingchange?.(null);
        oncancel?.();
    }

    // =========================================================================
    // Public API
    // =========================================================================

    /** Scroll to a specific date in the editor */
    export function scrollToDate(date: string) {
        dataEditor?.scrollToDate(date);
    }

    // =========================================================================
    // Derived
    // =========================================================================

    let _dirtyCount = $derived(rows.filter(r => r.status !== 'original').length);

    // Sync internal dirty count to bindable prop
    $effect(() => {
        dirtyCount = _dirtyCount;
    });
</script>

<div class="space-y-3">
    <!-- Error banner -->
    {#if error}
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-4 py-2 text-sm text-red-600 dark:text-red-400">
            {error}
        </div>
    {/if}

    <!-- Data Editor -->
    <DataEditor
            bind:rows
            bind:this={dataEditor}
            columns={fxColumns}
            onchange={handleDataChange}
    >
        {#snippet importModal({open, setOpen, onimport})}
            <FxDataImportModal
                    {open}
                    displayBase={base}
                    displayQuote={quote}
                    onimport={(rows, direction) => {
                        // Handle inversion if needed
                        const needsInversion = direction.from === quote && direction.to === base;
                        const mapped = rows.map(r => ({
                            ...r,
                            values: {
                                ...r.values,
                                rate: needsInversion ? 1 / Number(r.values.rate) : Number(r.values.rate),
                            },
                        }));
                        onimport(mapped);
                    }}
                    onclose={() => setOpen(false)}
            />
        {/snippet}
    </DataEditor>

    <!-- Save / Cancel bar -->
    <div class="flex items-center justify-end gap-2 px-1">
        <button
                class="flex items-center gap-1.5 px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 disabled:opacity-50 transition-colors"
                disabled={saving || _dirtyCount === 0}
                onclick={handleSave}
        >
            <Save size={15}/> {saving ? 'Saving...' : `Save (${_dirtyCount})`}
        </button>
        <button
                class="flex items-center gap-1.5 px-4 py-2 text-sm bg-slate-200 dark:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-500 transition-colors"
                onclick={handleCancel}
        >
            <X size={15}/>
            Cancel
        </button>

    </div>
</div>


