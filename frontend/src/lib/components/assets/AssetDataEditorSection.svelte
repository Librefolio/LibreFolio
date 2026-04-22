<!--
  AssetDataEditorSection — Orchestrator with 2 tabs (Prices / Events).

  Handles:
  - Two DataEditor instances (Prices + Events) with tab switching
  - Converting chartData[] → price DataRow[], events[] → event DataRow[]
  - API calls for upsert + delete (prices via range, events via individual ID)
  - Dirty tracking across both tabs → unified Save/Cancel bar
  - Chart preview (pending purple overlay for dirty price rows)
  - scrollToDate() API for chart-to-editor navigation

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {Save, X, DollarSign, CalendarClock} from 'lucide-svelte';
    import {untrack} from 'svelte';
    import {zodiosApi} from '$lib/api';
    import DataEditor from '$lib/components/ui/data-editor/DataEditor.svelte';
    import type {ColumnDef, DataRow} from '$lib/components/ui/data-editor/DataEditorTypes';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import type {RenderedSignal} from '$lib/charts/signals';
    import {toasts} from '$lib/stores/toastStore.svelte';
    import PriceDataImportModal from './PriceDataImportModal.svelte';
    import EventDataImportModal from './EventDataImportModal.svelte';
    import {getCurrencyInfo} from '$lib/stores/currencyStore';
    import {_ as t, locale} from '$lib/i18n';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Asset ID */
        assetId: number;
        /** Asset native currency (ISO code, e.g. "USD") — used for the "Prices in {currency} {flag}" tab label */
        currency?: string;
        /** Current price chart data from backend query */
        chartData: any[];
        /** Current events from backend query */
        events: any[];
        /** Whether save is in progress */
        saving?: boolean;
        /** Number of dirty rows across both tabs — exposed for parent */
        dirtyCount?: number;
        /** Called after successful save, with optional expanded date range */
        onsave?: (expandedRange?: {start: string; end: string}) => void;
        /** Called when edit is cancelled */
        oncancel?: () => void;
        /** Dirty price rows emitted as a preview RenderedSignal overlay (purple) */
        onpendingchange?: (previewSignal: RenderedSignal | null) => void;
    }

    let {assetId, currency, chartData, events, saving = $bindable(false), dirtyCount = $bindable(0), onsave, oncancel, onpendingchange}: Props = $props();

    // Currency flag emoji for tab labels (I-bis #3). Empty when currency missing.
    let currencyFlag = $derived(currency ? getCurrencyInfo(currency).flag_emoji : '');

    // =========================================================================
    // Column definitions
    // =========================================================================
    //
    // Post-Blocco I: the `currency` column has been removed from the prices tab.
    // The backend enforces price.currency == asset.currency at write-time (hard
    // reject 400 on mismatch); the frontend no longer sends currency per-point
    // and no longer needs the column visually — asset.currency is shown once in
    // the price summary strip above the chart.

    let priceColumns: ColumnDef[] = $derived([
        {key: 'close', label: $t('dataEditor.col.close'), type: 'number', editable: true, required: true, step: 0.01, min: 0, placeholder: '145.50'},
        {key: 'open', label: $t('dataEditor.col.open'), type: 'number', editable: true, required: false, step: 0.01, min: 0, placeholder: '144.00', erasable: true},
        {key: 'high', label: $t('dataEditor.col.high'), type: 'number', editable: true, required: false, step: 0.01, min: 0, placeholder: '146.20', erasable: true},
        {key: 'low', label: $t('dataEditor.col.low'), type: 'number', editable: true, required: false, step: 0.01, min: 0, placeholder: '143.80', erasable: true},
        {key: 'volume', label: $t('dataEditor.col.volume'), type: 'number', editable: true, required: false, step: 1, min: 0, placeholder: '1500000', erasable: true},
    ]);

    // F.5 — OHLC/volume columns are flagged `erasable: true`. DataEditor renders
    //   ErasableNumberCell which emits the sentinel `-1` on explicit clear (confirm →
    //   backend interprets it as SET NULL in the MERGE upsert). NULL values render as
    //   "not set" italic placeholder. `Delete` key on empty input triggers the same
    //   eraser confirm flow.
    //   i18n keys: `dataEditor.cell.{notSet,clearField,clearFieldConfirm}` (4 langs).

    let eventTypeOptions = $derived([
        {value: 'DIVIDEND', label: $t('assetDetail.eventType.DIVIDEND'), emoji: '💰', tooltip: $t('assetDetail.eventTypeTooltip.DIVIDEND'), docsPath: 'financial-theory/instruments/asset-events/dividend'},
        {value: 'INTEREST', label: $t('assetDetail.eventType.INTEREST'), emoji: '📈', tooltip: $t('assetDetail.eventTypeTooltip.INTEREST'), docsPath: 'financial-theory/instruments/asset-events/interest'},
        {value: 'SPLIT', label: $t('assetDetail.eventType.SPLIT'), emoji: '✂️', tooltip: $t('assetDetail.eventTypeTooltip.SPLIT'), docsPath: 'financial-theory/instruments/asset-events/split'},
        {value: 'PRICE_ADJUSTMENT', label: $t('assetDetail.eventType.PRICE_ADJUSTMENT'), emoji: '📊', tooltip: $t('assetDetail.eventTypeTooltip.PRICE_ADJUSTMENT'), docsPath: 'financial-theory/instruments/asset-events/price-adjustment'},
        {value: 'MATURITY_SETTLEMENT', label: $t('assetDetail.eventType.MATURITY_SETTLEMENT'), emoji: '🏁', tooltip: $t('assetDetail.eventTypeTooltip.MATURITY_SETTLEMENT'), docsPath: 'financial-theory/instruments/asset-events/maturity-settlement'},
    ]);

    let eventColumns: ColumnDef[] = $derived([
        {key: 'currency', label: $t('dataEditor.col.currency'), type: 'currency', editable: true, required: false, placeholder: 'USD'},
        {key: 'type', label: $t('dataEditor.col.type'), type: 'enum', editable: true, required: true, enumOptions: eventTypeOptions},
        {key: 'amount', label: $t('dataEditor.col.amount'), type: 'number', editable: true, required: true, step: 0.01, placeholder: '1.25'},
        {key: 'notes', label: $t('dataEditor.col.notes'), type: 'string', editable: true, required: false, placeholder: 'Q1 payout'},
    ]);

    // =========================================================================
    // State
    // =========================================================================

    let activeTab: 'prices' | 'events' = $state('prices');
    let priceRows: DataRow[] = $state([]);
    let eventRows: DataRow[] = $state([]);
    let priceEditor: DataEditor | undefined = $state(undefined);
    let eventEditor: DataEditor | undefined = $state(undefined);
    let error: string | null = $state(null);

    let prevChartData: any[] | null = null;
    let prevEvents: any[] | null = null;

    // =========================================================================
    // Convert data → DataRow[]
    // =========================================================================

    function chartDataToPriceRows(data: any[]): DataRow[] {
        return data.map((p) => ({
            rowId: p.date,
            date: p.date,
            status: 'original' as const,
            originalStatus: 'original' as const,
            values: {
                currency: p.currency ?? '',
                close: p.close != null ? Number(p.close) : undefined,
                open: p.open != null ? Number(p.open) : undefined,
                high: p.high != null ? Number(p.high) : undefined,
                low: p.low != null ? Number(p.low) : undefined,
                volume: p.volume != null ? Number(p.volume) : undefined,
            },
            selected: false,
            _originalValues: {
                currency: p.currency ?? '',
                close: p.close != null ? Number(p.close) : undefined,
                open: p.open != null ? Number(p.open) : undefined,
                high: p.high != null ? Number(p.high) : undefined,
                low: p.low != null ? Number(p.low) : undefined,
                volume: p.volume != null ? Number(p.volume) : undefined,
            },
            staleDays: p.backward_fill_info?.days_back ?? 0,
        }));
    }

    function eventsToEventRows(evts: any[]): DataRow[] {
        return evts.map((ev) => ({
            // Use "new-<uuid>" for rows without a DB id so parseInt() cannot silently
            // extract leading digits from a raw UUID (e.g. "83959abc-..." → 83959)
            // and send a fake id to the delete endpoint.
            rowId: ev.id != null ? String(ev.id) : `new-${crypto.randomUUID()}`,
            date: ev.date,
            status: 'original' as const,
            originalStatus: 'original' as const,
            values: {
                type: ev.type ?? '',
                amount: ev.value?.amount != null ? Number(ev.value.amount) : undefined,
                currency: ev.value?.code ?? '',
                notes: typeof ev.notes === 'string' ? ev.notes : Array.isArray(ev.notes) ? (ev.notes[0] ?? '') : '',
            },
            selected: false,
            readonly: ev.is_auto === true,
            readonlyReason: ev.is_auto === true ? $t('dataEditor.autoEvent.tooltip') : undefined,
            _originalValues: {
                type: ev.type ?? '',
                amount: ev.value?.amount != null ? Number(ev.value.amount) : undefined,
                currency: ev.value?.code ?? '',
                notes: typeof ev.notes === 'string' ? ev.notes : Array.isArray(ev.notes) ? (ev.notes[0] ?? '') : '',
            },
        }));
    }

    // Initialize/update rows when data changes
    $effect(() => {
        if (chartData !== prevChartData) {
            prevChartData = chartData;
            priceRows = chartDataToPriceRows(chartData);
        }
    });

    $effect(() => {
        if (events !== prevEvents) {
            prevEvents = events;
            eventRows = eventsToEventRows(events);
        }
    });

    // Re-translate readonlyReason on readonly rows whenever the UI language changes.
    // We don't rebuild eventRows from scratch to preserve the user's pending edits/deletes.
    // NOTE: uses `untrack` around the read+write of `eventRows` to prevent the effect
    // from self-triggering (the `.map()` produces a new array reference each run, which
    // would otherwise flag `eventRows` as a dependency and cause `effect_update_depth_exceeded`).
    $effect(() => {
        // Depend on the locale store so this effect re-runs on language switch
        $locale;
        const newReason = $t('dataEditor.autoEvent.tooltip');
        untrack(() => {
            eventRows = eventRows.map((r) => (r.readonly ? {...r, readonlyReason: newReason} : r));
        });
    });

    // =========================================================================
    // Dirty tracking → chart preview
    // =========================================================================

    let priceDirtyCount = $derived(priceRows.filter((r) => r.status !== 'original').length);
    let eventDirtyCount = $derived(eventRows.filter((r) => r.status !== 'original').length);
    let _dirtyCount = $derived(priceDirtyCount + eventDirtyCount);

    $effect(() => {
        dirtyCount = _dirtyCount;
    });

    function handlePriceDataChange(dirtyRows: DataRow[]) {
        // Emit preview signal from dirty price rows (close values)
        const pendingPoints: LineDataPoint[] = dirtyRows
            .filter((r) => r.status === 'edited' || r.status === 'appended')
            .filter((r) => r.values.close !== undefined && r.values.close !== null)
            .map((r) => ({
                date: r.date,
                value: Number(r.values.close),
            }));

        if (pendingPoints.length === 0) {
            onpendingchange?.(null);
            return;
        }

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
        const dirtyPrices = priceRows.filter((r) => r.status !== 'original');
        const dirtyEvents = eventRows.filter((r) => r.status !== 'original');
        if (dirtyPrices.length === 0 && dirtyEvents.length === 0) return;

        saving = true;
        error = null;

        try {
            const parts: string[] = [];

            // ─── PRICES ─────────────────────────────────────
            if (dirtyPrices.length > 0) {
                const upsertPrices = dirtyPrices.filter((r) => r.status === 'edited' || r.status === 'appended');
                const deletePrices = dirtyPrices.filter((r) => r.status === 'deleted');

                // Filter valid upserts (close must be valid)
                // Post-Blocco I: currency is NOT part of the payload anymore — backend
                // derives it from asset.currency and rejects any mismatch defensively.
                const validUpserts = upsertPrices.filter((r) => {
                    const close = Number(r.values.close);
                    return !isNaN(close) && close > 0;
                });
                const invalidCount = upsertPrices.length - validUpserts.length;

                if (validUpserts.length > 0) {
                    // F.5 — sentinel semantics for optional OHLC/volume fields:
                    //   undefined/null → omit (backend preserves existing DB value)
                    //   -1             → send -1 (backend MERGE upsert interprets as SET NULL)
                    //   other number   → send as-is
                    const optionalField = (v: unknown): number | undefined => {
                        if (v === undefined || v === null || v === '') return undefined;
                        const n = Number(v);
                        if (isNaN(n)) return undefined;
                        return n; // includes -1 sentinel
                    };
                    const priceItems = validUpserts.map((r) => ({
                        date: r.date,
                        close: Number(r.values.close),
                        open: optionalField(r.values.open),
                        high: optionalField(r.values.high),
                        low: optionalField(r.values.low),
                        volume: optionalField(r.values.volume),
                    }));
                    await zodiosApi.upsert_prices_bulk_api_v1_assets_prices_post([
                        {
                            asset_id: assetId,
                            prices: priceItems,
                        },
                    ]);
                    parts.push(`${validUpserts.length} prices saved`);
                }

                if (deletePrices.length > 0) {
                    // Merge consecutive dates into ranges
                    const sortedDates = deletePrices.map((r) => r.date).sort();
                    const ranges: Array<{start: string; end?: string}> = [];
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

                    await zodiosApi.delete_prices_bulk_api_v1_assets_prices_delete([
                        {
                            asset_id: assetId,
                            date_ranges: ranges,
                        },
                    ]);
                    parts.push(`${deletePrices.length} prices deleted`);
                }

                if (invalidCount > 0) parts.push(`${invalidCount} skipped (invalid)`);
            }

            // ─── EVENTS ─────────────────────────────────────
            if (dirtyEvents.length > 0) {
                const upsertEvents = dirtyEvents.filter((r) => r.status === 'edited' || r.status === 'appended');
                const deleteEvents = dirtyEvents.filter((r) => r.status === 'deleted');

                if (upsertEvents.length > 0) {
                    const validEvents = upsertEvents.filter((r) => {
                        const amount = Number(r.values.amount);
                        return !isNaN(amount) && r.values.type;
                    });

                    if (validEvents.length > 0) {
                        const eventItems = validEvents.map((r) => ({
                            date: r.date,
                            type: String(r.values.type),
                            value: {
                                code: String(r.values.currency || 'USD'),
                                amount: Number(r.values.amount),
                            },
                            notes: r.values.notes ? String(r.values.notes) : undefined,
                        }));
                        await zodiosApi.upsert_events_bulk_api_v1_assets_events_post([
                            {
                                asset_id: assetId,
                                events: eventItems,
                            },
                        ]);
                        parts.push(`${validEvents.length} events saved`);
                    }
                }

                if (deleteEvents.length > 0) {
                    // Delete events that have a real DB id (not UUID-generated for new rows)
                    const realDeletes = deleteEvents.filter((r) => {
                        const id = parseInt(r.rowId, 10);
                        return !isNaN(id) && id > 0;
                    });
                    if (realDeletes.length > 0) {
                        const idsToDelete = realDeletes.map((r) => parseInt(r.rowId, 10));
                        // Single bulk call; backend returns per-item status (deleted/not_found/in_use).
                        const bulkResp = await zodiosApi.delete_events_bulk_api_v1_assets_events_delete(undefined, {
                            queries: {ids: idsToDelete},
                        });
                        const allResults = bulkResp.results ?? [];

                        const deletedIds = new Set<number>(allResults.filter((r: any) => r.status === 'deleted').map((r: any) => r.event_id));
                        const blocked = allResults.filter((r: any) => r.status === 'in_use');
                        const notFound = allResults.filter((r: any) => r.status === 'not_found');

                        // Remove the deleted rows from the in-memory table so they don't linger.
                        eventRows = eventRows.filter((row) => {
                            const idNum = parseInt(row.rowId, 10);
                            if (isNaN(idNum)) return true;
                            return !deletedIds.has(idNum);
                        });

                        if (deletedIds.size > 0) {
                            parts.push($t('events.deleteSuccess', {values: {count: deletedIds.size}}));
                        }
                        if (blocked.length > 0) {
                            const totalVisible = blocked.reduce((sum: number, b: any) => sum + b.accessible_transactions.length, 0);
                            const totalHidden = blocked.reduce((sum: number, b: any) => sum + (b.hidden_transactions_count || 0), 0);
                            toasts.warning(
                                $t('events.deleteBlocked', {
                                    values: {
                                        count: blocked.length,
                                        accessible: totalVisible,
                                        hidden: totalHidden,
                                    },
                                }),
                            );
                        }
                        if (notFound.length > 0) {
                            toasts.warning(
                                $t('events.deleteNotFound', {
                                    values: {ids: notFound.map((r: any) => r.event_id).join(', ')},
                                }),
                            );
                        }
                    }
                }
            }

            // Only show success toast when there's something to report. Avoids the
            // empty "Asset data:    " toast when an attempted delete was fully blocked
            // by RESTRICT (in_use) — the warning toast already informs the user.
            if (parts.length > 0) {
                toasts.success(`Asset data: ${parts.join(', ')}`);
            }

            // Compute expanded date range from appended price rows
            const appendedPrices = priceRows.filter((r) => r.status === 'appended');
            let expandedRange: {start: string; end: string} | undefined;
            if (appendedPrices.length > 0 && chartData.length > 0) {
                const chartDates = chartData.map((d: any) => d.date).sort();
                const chartStart = chartDates[0];
                const chartEnd = chartDates[chartDates.length - 1];
                const allDates = [...chartDates, ...appendedPrices.map((r) => r.date)].sort();
                const newStart = allDates[0];
                const newEnd = allDates[allDates.length - 1];
                if (newStart < chartStart || newEnd > chartEnd) {
                    expandedRange = {start: newStart, end: newEnd};
                }
            }

            onsave?.(expandedRange);
        } catch (e: any) {
            console.error('Failed to save asset data:', e);
            const msg = e?.message || 'unknown error';
            error = 'Failed to save: ' + msg;
            toasts.error(`Save failed: ${msg}`);
        } finally {
            saving = false;
        }
    }

    function handleCancel() {
        priceRows = chartDataToPriceRows(chartData);
        eventRows = eventsToEventRows(events);
        onpendingchange?.(null);
        oncancel?.();
    }

    // =========================================================================
    // Public API
    // =========================================================================

    /** Scroll to a specific date in the editor, optionally switching tab */
    export function scrollToDate(date: string, tab?: 'prices' | 'events') {
        if (tab && tab !== activeTab) {
            activeTab = tab;
            // Wait for tab to render, then scroll
            setTimeout(() => {
                if (tab === 'prices') {
                    priceEditor?.scrollToDate(date);
                } else {
                    eventEditor?.scrollToDate(date);
                }
            }, 250);
        } else if (activeTab === 'prices') {
            priceEditor?.scrollToDate(date);
        } else {
            eventEditor?.scrollToDate(date);
        }
    }
</script>

<div class="space-y-3">
    <!-- Error banner -->
    {#if error}
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-4 py-2 text-sm text-red-600 dark:text-red-400">
            {error}
        </div>
    {/if}

    <!-- Tab bar -->
    <div class="flex border-b border-gray-200 dark:border-slate-600">
        <button
            class="flex items-center gap-1.5 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px
                       {activeTab === 'prices' ? 'border-libre-green text-libre-green dark:text-emerald-400' : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-slate-500'}"
            onclick={() => (activeTab = 'prices')}
            data-testid="asset-editor-prices-tab"
        >
            <DollarSign size={14} />
            {$t('assetDetail.pricesTab')}
            {#if priceDirtyCount > 0}
                <span class="text-[10px] px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400 rounded-full">
                    {priceDirtyCount}
                </span>
            {/if}
        </button>
        <button
            class="flex items-center gap-1.5 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px
                       {activeTab === 'events' ? 'border-libre-green text-libre-green dark:text-emerald-400' : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-slate-500'}"
            onclick={() => (activeTab = 'events')}
            data-testid="asset-editor-events-tab"
        >
            <CalendarClock size={14} />
            {$t('assetDetail.eventsTab')}
            {#if eventDirtyCount > 0}
                <span class="text-[10px] px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400 rounded-full">
                    {eventDirtyCount}
                </span>
            {/if}
        </button>

        <!-- I-bis #3 — Currency label aligned right: "Prices in USD 🇺🇸" / "Events in USD 🇺🇸" -->
        {#if currency}
            <div class="ml-auto flex items-center gap-1 px-3 py-2 text-xs text-gray-500 dark:text-gray-400" data-testid="asset-editor-currency-label">
                {#if activeTab === 'prices'}
                    {$t('assetDetail.pricesInCurrency', {values: {currency}})}
                {:else}
                    {$t('assetDetail.eventsInCurrency', {values: {currency}})}
                {/if}
                <span class="emoji-flag">{currencyFlag}</span>
            </div>
        {/if}
    </div>

    <!-- Data Editor: Prices -->
    {#if activeTab === 'prices'}
        <DataEditor bind:rows={priceRows} bind:this={priceEditor} columns={priceColumns} onchange={handlePriceDataChange}>
            {#snippet importModal({open, setOpen, onimport})}
                <PriceDataImportModal {open} {currency} {onimport} onclose={() => setOpen(false)} />
            {/snippet}
        </DataEditor>
    {/if}

    <!-- Data Editor: Events -->
    {#if activeTab === 'events'}
        <DataEditor bind:rows={eventRows} bind:this={eventEditor} columns={eventColumns}>
            {#snippet importModal({open, setOpen, onimport})}
                <EventDataImportModal {open} {onimport} onclose={() => setOpen(false)} />
            {/snippet}
        </DataEditor>
    {/if}

    <!-- Save / Cancel bar -->
    <div class="flex items-center justify-end gap-2 px-1">
        <button class="flex items-center gap-1.5 px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 disabled:opacity-50 transition-colors" disabled={saving || _dirtyCount === 0} onclick={handleSave}>
            <Save size={15} />
            {saving ? $t('dataEditor.saving') : $t('dataEditor.save', {values: {count: _dirtyCount}})}
        </button>
        <button class="flex items-center gap-1.5 px-4 py-2 text-sm bg-slate-200 dark:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-500 transition-colors" onclick={handleCancel}>
            <X size={15} />
            {$t('common.cancel')}
        </button>
    </div>
</div>
