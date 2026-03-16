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
        /** Called after successful save */
        onsave?: () => void;
        /** Called when edit is cancelled */
        oncancel?: () => void;
        /** Dirty rows emitted for chart preview (pending orange points) */
        onpendingchange?: (pendingPoints: LineDataPoint[]) => void;
    }

    let {
        base,
        quote,
        chartData,
        saving = $bindable(false),
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
            placeholder: '1.0823',
        },
    ];

    // =========================================================================
    // State
    // =========================================================================

    let dataEditor: DataEditor | undefined = $state(undefined);
    let rows: DataRow[] = $state([]);
    let error: string | null = $state(null);

    // =========================================================================
    // Convert FxDataPoint[] → DataRow[]
    // =========================================================================

    function chartDataToRows(data: FxDataPoint[]): DataRow[] {
        return data.map(dp => ({
            date: dp.date,
            status: 'original' as const,
            originalStatus: 'original' as const,
            values: {rate: dp.rate},
            selected: false,
            _originalValues: {rate: dp.rate},
        }));
    }

    // Initialize rows from chartData
    $effect(() => {
        rows = chartDataToRows(chartData);
    });

    // =========================================================================
    // Dirty tracking → chart preview
    // =========================================================================

    function handleDataChange(dirtyRows: DataRow[]) {
        // Convert edited/appended rows to LineDataPoint[] for chart overlay
        const pendingPoints: LineDataPoint[] = dirtyRows
            .filter(r => r.status === 'edited' || r.status === 'appended')
            .filter(r => r.values.rate !== undefined && r.values.rate !== null)
            .map(r => ({
                date: r.date,
                value: Number(r.values.rate),
            }));

        onpendingchange?.(pendingPoints);
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
            if (upsertRows.length > 0) {
                // Normalize base/quote to alphabetical order (backend convention)
                const baseNorm = base < quote ? base : quote;
                const quoteNorm = base < quote ? quote : base;
                const isInverted = base > quote;

                const rateItems = upsertRows.map(r => ({
                    base: baseNorm,
                    quote: quoteNorm,
                    date: r.date,
                    rate: isInverted ? 1 / Number(r.values.rate) : Number(r.values.rate),
                }));
                await zodiosApi.upsert_rates_endpoint_api_v1_fx_currencies_rate_post(rateItems);
            }

            // Delete rows marked as deleted
            const deleteRows = dirty.filter(r => r.status === 'deleted');
            if (deleteRows.length > 0) {
                // Group all date ranges and send in one call
                const deleteItems = [{
                    from: base < quote ? base : quote,
                    to: base < quote ? quote : base,
                    date_range: deleteRows.map(dr => ({start: dr.date})),
                }];
                await zodiosApi.delete_rates_endpoint_api_v1_fx_currencies_rate_delete(deleteItems);
            }

            onsave?.();
        } catch (e: any) {
            console.error('Failed to save rates:', e);
            error = 'Failed to save: ' + (e?.message || 'unknown error');
        } finally {
            saving = false;
        }
    }

    function handleCancel() {
        // Reset rows from original chart data
        rows = chartDataToRows(chartData);
        onpendingchange?.([]);
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

    let dirtyCount = $derived(rows.filter(r => r.status !== 'original').length);
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
        bind:this={dataEditor}
        columns={fxColumns}
        bind:rows
        baseCurrency={base}
        quoteCurrency={quote}
        onchange={handleDataChange}
    />

    <!-- Save / Cancel bar -->
    <div class="flex items-center justify-end gap-2 px-1">
        <button
            class="flex items-center gap-1.5 px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 disabled:opacity-50 transition-colors"
            onclick={handleSave}
            disabled={saving || dirtyCount === 0}
        >
            <Save size={15} /> {saving ? 'Saving...' : `Save (${dirtyCount})`}
        </button>
        <button
            class="flex items-center gap-1.5 px-4 py-2 text-sm bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-slate-500 transition-colors"
            onclick={handleCancel}
        >
            <X size={15} /> Cancel
        </button>
    </div>
</div>


