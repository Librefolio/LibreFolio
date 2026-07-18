<!--
  LotsAnalysisPanel — Orchestrator for the FifoLotEngine-based lots UI (Fase 3 migration).

  Drop-in successor to FIFOLotsPanel.svelte: same external Props contract, so call sites
  only need an import + tag swap. Internally it wires 5 independently-built components
  (LotGanttChart, LotWacPriceChart, UnifiedLotsTable, LotCustodyModal, LotComparisonChart)
  around a single bulk fetch of POST /portfolio/lots/analysis.

  Fetch strategy (two tiers, per plan v2 §13 "il frontend non effettua autonomamente ...
  calcoli WAC"):
  - Main fetch (asset/broker/date-range change): LOT_SUMMARY + GANTT_TOPOLOGY +
    EVENT_HISTORY + PRICE_HISTORY + BROKER_WAC_HISTORY + CUMULATIVE_WAC_HISTORY, with
    NO selected_lot_ids (service defaults to "all lots" — see
    LotsAnalysisService._resolve_selected_lot_ids). EVENT_HISTORY (superset of the old
    CUSTODY_HISTORY subset) feeds both the WAC chart's transaction markers and the
    Custody modal's full chronology (refinement v1 §5 / modal spec). PRICE_HISTORY +
    BROKER_WAC_HISTORY + CUMULATIVE_WAC_HISTORY feed the WAC/price chart.
  - Selection fetch (effectiveSelectionIds change): VALUE_HISTORY + RETURN_HISTORY scoped to
    the effective lot set. Per plan v3 §13 an empty selectedLotIds means "all visible lots"
    (effectiveSelectionIds), so the comparison chart shows the whole visible set by default and
    narrows only on an explicit selection.

  Gantt <-> WAC chart zoom/pan stay bidirectionally synced (sharedZoomStart/End), matching
  the old panel's pattern. The comparison chart takes only an *initial* xAxisRange (plan
  §16: "possiede zoom indipendente") — no live sync back into it.

  Aperti/Tutti lot filter (refinement v1 §11) is lifted here from LotGanttChart so
  UnifiedLotsTable shows the same lot set (visibleLots below); the toggle control still
  renders inside LotGanttChart.
-->
<script lang="ts">
    import {tick} from 'svelte';
    import {slide} from 'svelte/transition';
    import {goto} from '$app/navigation';
    import {_} from '$lib/i18n';
    import {ExternalLink, X} from 'lucide-svelte';
    import {zodiosApi, schemas} from '$lib/api';
    import type {z} from 'zod';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import LotGanttChart from './LotGanttChart.svelte';
    import LotWacPriceChart from './LotWacPriceChart.svelte';
    import UnifiedLotsTable from './UnifiedLotsTable.svelte';
    import LotCustodyModal from './LotCustodyModal.svelte';
    import LotComparisonChart from './LotComparisonChart.svelte';
    import type {LotIncomeEvent} from './LotComparisonChart.svelte';
    import DataQualityBanner, {type DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';

    type LotSummarySchema = z.infer<typeof schemas.LotSummarySchema>;
    type GanttSegmentSchema = z.infer<typeof schemas.GanttSegmentSchema>;
    type LotTimelineEventSchema = z.infer<typeof schemas.LotTimelineEventSchema>;
    type LotValueHistoryPoint = z.infer<typeof schemas.LotValueHistoryPoint>;
    type LotReturnHistoryPoint = z.infer<typeof schemas.LotReturnHistoryPoint>;
    type LotPriceHistoryPoint = z.infer<typeof schemas.LotPriceHistoryPoint>;
    type BrokerWACHistoryPoint = z.infer<typeof schemas.BrokerWACHistoryPoint>;
    type CumulativeWACHistoryPoint = z.infer<typeof schemas.CumulativeWACHistoryPoint>;
    type DateRange = {min: string; max: string};

    /**
     * The generated Zodios client produces a redundant union for every
     * Optional[List[X]] response field: `(X[] | null) | (X[] | null)[]`
     * (openapi-zod-client artifact, pre-existing, unrelated to this feature —
     * see fifo-lot-engine-v2-implementation-log.md §3.1). The API never
     * actually returns the doubled-array branch. `value` is typed `unknown`
     * and T is always passed explicitly at the call site (`asArray<Foo>(...)`)
     * to avoid fighting TS's structural inference over that redundant union.
     */
    function asArray<T>(value: unknown): T[] {
        if (!value || !Array.isArray(value)) return [];
        if (value.length > 0 && Array.isArray(value[0])) {
            return (value as unknown[][]).flatMap((item) => (item ?? []) as T[]);
        }
        return value as T[];
    }

    /** Same generator artifact as asArray(), for single-object Optional[X] fields. */
    function asObject<T>(value: unknown): T | null {
        if (!value) return null;
        return Array.isArray(value) ? ((value[0] ?? null) as T | null) : (value as T);
    }

    interface Props {
        open: boolean;
        assetId: number | null;
        brokerIds: number[];
        brokers: ReadonlyArray<BrokerLike>;
        currency: string;
        dateFrom: string;
        dateTo: string;
        isAllPeriod: boolean;
        assetName?: string | null;
        onClose: () => void;
    }

    let {open, assetId, brokerIds, brokers, currency, dateFrom, dateTo, isAllPeriod, assetName = null, onClose}: Props = $props();

    let loading = $state(false);
    let error = $state<string | null>(null);

    let lots = $state<LotSummarySchema[]>([]);
    let ganttSegments = $state<GanttSegmentSchema[]>([]);
    let lotEvents = $state<LotTimelineEventSchema[]>([]);
    let priceHistory = $state<LotPriceHistoryPoint[]>([]);
    let brokerWacHistory = $state<BrokerWACHistoryPoint[]>([]);
    let cumulativeWacHistory = $state<CumulativeWACHistoryPoint[]>([]);
    let incomeEvents = $state<LotIncomeEvent[]>([]);
    let quoteBaseQuantity = $state<number>(1);
    let dataQualityIssues = $state<DataQualityIssue[]>([]);
    let computedRange = $state<DateRange | null>(null);

    let selectedLotIds = $state<number[]>([]);
    let valueHistory = $state<LotValueHistoryPoint[]>([]);
    let returnHistory = $state<LotReturnHistoryPoint[]>([]);
    let selectionLoading = $state(false);

    let modalOpen = $state(false);
    let modalLot = $state<LotSummarySchema | null>(null);

    let panelEl: HTMLDivElement | undefined = $state(undefined);
    let sharedZoomStart = $state<number | null>(null);
    let sharedZoomEnd = $state<number | null>(null);

    let ganttRef: LotGanttChart | undefined = $state(undefined);
    let tableRef: UnifiedLotsTable | undefined = $state(undefined);

    let fetchVersion = 0;
    let selectionFetchVersion = 0;

    /** Shared "Aperti | Chiusi" lot filter (plan §11 + round-3): two independent on/off buckets like
     * the Aggregato/Per-lotto value toggle — "both on" (default) and "both off" both mean "show every
     * lot"; a single bucket narrows to just open or just closed. The UI control lives inside
     * LotGanttChart, but the resulting lot set (visibleLots) is shared with UnifiedLotsTable, the
     * WAC/price bubbles and the comparison chart so every consumer stays consistent. "Aperti" mirrors
     * FifoEngineResult's OPEN state tag / open_quantity>0 (includes partially-closed lots); "Chiusi" is
     * every fully-closed lot. Each consumer still does its own range-intersection filtering. */
    let lotStateFilter = $state<{open: boolean; closed: boolean}>({open: true, closed: true});

    /** Vita e custodia view (plan v3 §8): the compact hierarchical Gantt (Timeline). */

    function lotIsOpenish(lot: LotSummarySchema): boolean {
        return Number.parseFloat(lot.open_quantity) > 0 || (lot.states ?? []).includes('OPEN');
    }

    let visibleLots = $derived.by((): LotSummarySchema[] => {
        const bothSame = lotStateFilter.open === lotStateFilter.closed;
        const showOpen = bothSame || lotStateFilter.open;
        const showClosed = bothSame || lotStateFilter.closed;
        return lots.filter((lot) => (lotIsOpenish(lot) ? showOpen : showClosed));
    });

    let selectedLots = $derived.by((): LotSummarySchema[] => {
        const selected = new Set(selectedLotIds);
        return lots.filter((lot) => selected.has(lot.lot_id));
    });

    /** Implicit selection (plan v3 §13): an empty selectedLotIds means "all visible lots", NOT "none".
     * These effective derivations drive every consumer that must honor that semantics — the selection
     * value/return fetch, the comparison chart, the bubble Performance view and the table footer — so
     * that with no explicit selection the user still sees data for the whole visible lot set. An
     * explicit (non-empty) selection narrows down to exactly those lots. */
    let effectiveSelectionIds = $derived.by((): number[] => (selectedLotIds.length > 0 ? selectedLotIds : visibleLots.map((lot) => lot.lot_id)));

    let effectiveSelectedLots = $derived.by((): LotSummarySchema[] => (selectedLotIds.length > 0 ? selectedLots : visibleLots));

    let xAxisRange = $derived.by((): DateRange | null => {
        if (!isAllPeriod) return {min: dateFrom, max: dateTo};
        return computedRange;
    });

    function handleZoomChange(start: number, end: number) {
        sharedZoomStart = start;
        sharedZoomEnd = end;
    }

    async function loadMain(currentAssetId: number, currentBrokerIds: number[]) {
        const version = ++fetchVersion;
        loading = true;
        error = null;
        try {
            const body = {
                asset_id: currentAssetId,
                broker_ids: currentBrokerIds.length > 0 ? currentBrokerIds : undefined,
                date_range: isAllPeriod ? undefined : {start: dateFrom, end: dateTo},
                target_currency: currency,
                requested_analyses: ['LOT_SUMMARY', 'GANTT_TOPOLOGY', 'EVENT_HISTORY', 'PRICE_HISTORY', 'BROKER_WAC_HISTORY', 'CUMULATIVE_WAC_HISTORY', 'INCOME_EVENTS'] as const,
            };
            const response = await zodiosApi.get_lots_analysis_api_v1_portfolio_lots_analysis_post(body);
            if (version !== fetchVersion) return; // stale response from a since-superseded open/asset change

            lots = asArray<LotSummarySchema>(response.lots);
            ganttSegments = asArray<GanttSegmentSchema>(response.gantt_segments);
            // EVENT_HISTORY is a superset of the old CUSTODY_HISTORY filter (backend computes the
            // full per-lot event list unconditionally either way — see lots_analysis_service.py
            // _build_lot_event_rows/_CUSTODY_KINDS) — fetching it once here feeds both the WAC
            // chart's transaction markers and the Custody modal's full chronology, no double fetch.
            lotEvents = asArray<LotTimelineEventSchema>(response.lot_events);
            priceHistory = asArray<LotPriceHistoryPoint>(response.price_history);
            brokerWacHistory = asArray<BrokerWACHistoryPoint>(response.broker_wac_history);
            cumulativeWacHistory = asArray<CumulativeWACHistoryPoint>(response.cumulative_wac_history);
            const rawQbq = Number(response.quote_base_quantity);
            quoteBaseQuantity = Number.isFinite(rawQbq) && rawQbq > 0 ? rawQbq : 1;
            incomeEvents = asArray<{type: 'DIVIDEND' | 'INTEREST'; date: string; broker_id?: number | null; amount: string; lot_ids?: number[]}>(response.income_events).map((event) => ({
                type: event.type,
                date: event.date,
                broker_id: event.broker_id ?? null,
                amount: event.amount,
                lot_ids: event.lot_ids ?? [],
            }));
            dataQualityIssues = asArray<DataQualityIssue>(asObject<{issues?: unknown}>(response.data_quality)?.issues);

            const metadata = response.calculation_metadata;
            const computedFrom = asObject<string>(metadata?.computed_date_from);
            const computedTo = asObject<string>(response.calculation_metadata?.computed_date_to);
            computedRange = computedFrom && computedTo ? {min: computedFrom, max: computedTo} : null;

            // Prune a selection that no longer resolves to a real lot (e.g. asset/broker change).
            const validIds = new Set(lots.map((lot) => lot.lot_id));
            selectedLotIds = selectedLotIds.filter((id) => validIds.has(id));
        } catch (e) {
            if (version !== fetchVersion) return;
            console.error('Failed to load lots analysis:', e);
            error = $_('brokers.lots.loadFailed');
            lots = [];
            ganttSegments = [];
            lotEvents = [];
            priceHistory = [];
            brokerWacHistory = [];
            cumulativeWacHistory = [];
            dataQualityIssues = [];
            incomeEvents = [];
            quoteBaseQuantity = 1;
        } finally {
            if (version === fetchVersion) loading = false;
        }
    }

    async function loadSelectionHistories(currentAssetId: number, currentBrokerIds: number[], ids: number[]) {
        const version = ++selectionFetchVersion;
        if (ids.length === 0) {
            valueHistory = [];
            returnHistory = [];
            return;
        }
        selectionLoading = true;
        try {
            const body = {
                asset_id: currentAssetId,
                broker_ids: currentBrokerIds.length > 0 ? currentBrokerIds : undefined,
                date_range: isAllPeriod ? undefined : {start: dateFrom, end: dateTo},
                target_currency: currency,
                selected_lot_ids: ids,
                requested_analyses: ['VALUE_HISTORY', 'RETURN_HISTORY'] as const,
            };
            const response = await zodiosApi.get_lots_analysis_api_v1_portfolio_lots_analysis_post(body);
            if (version !== selectionFetchVersion) return;
            valueHistory = asArray<LotValueHistoryPoint>(response.value_history);
            returnHistory = asArray<LotReturnHistoryPoint>(response.return_history);
        } catch (e) {
            if (version !== selectionFetchVersion) return;
            console.error('Failed to load selected-lot histories:', e);
            valueHistory = [];
            returnHistory = [];
        } finally {
            if (version === selectionFetchVersion) selectionLoading = false;
        }
    }

    function waitForStableRect(el: HTMLElement, maxFrames = 180): Promise<void> {
        return new Promise((resolve) => {
            let lastRect: DOMRect | null = null;
            let stableFrames = 0;
            let frame = 0;

            function check() {
                frame++;
                const rect = el.getBoundingClientRect();
                const same = lastRect !== null && rect.top === lastRect.top && rect.left === lastRect.left && rect.width === lastRect.width && rect.height === lastRect.height;
                stableFrames = same ? stableFrames + 1 : 0;
                lastRect = rect;

                if (stableFrames >= 2 || frame >= maxFrames) {
                    resolve();
                    return;
                }
                requestAnimationFrame(check);
            }

            requestAnimationFrame(check);
        });
    }

    let scrollRequestVersion = 0;
    let previousScrollOpen = false;
    let previousScrollAssetId: number | null = null;

    async function scrollPanelIntoViewWhenStable(requestVersion: number) {
        await tick();
        const el = panelEl;
        if (!el || requestVersion !== scrollRequestVersion || !(open && assetId != null)) return;
        await waitForStableRect(el);
        if (!panelEl || requestVersion !== scrollRequestVersion || !(open && assetId != null)) return;
        panelEl.scrollIntoView({behavior: 'smooth', block: 'start'});
    }

    $effect(() => {
        if (open && assetId != null) void loadMain(assetId, brokerIds);
    });

    $effect(() => {
        if (open && assetId != null) void loadSelectionHistories(assetId, brokerIds, effectiveSelectionIds);
    });

    $effect(() => {
        const isPanelOpen = open && assetId != null;
        const shouldScroll = isPanelOpen && (!previousScrollOpen || assetId !== previousScrollAssetId);
        previousScrollOpen = isPanelOpen;
        previousScrollAssetId = assetId;
        if (!shouldScroll) return;

        selectedLotIds = [];
        sharedZoomStart = null;
        sharedZoomEnd = null;
        computedRange = null;

        const requestVersion = ++scrollRequestVersion;
        void scrollPanelIntoViewWhenStable(requestVersion);
    });

    function handleSelectionChange(ids: number[]) {
        selectedLotIds = ids;
    }

    function handleCustodyCellClick(lot: LotSummarySchema) {
        modalLot = lot;
        modalOpen = true;
    }

    function handleGotoTransaction(transactionId: number) {
        modalOpen = false;
        void goto(`/transactions?highlight=${transactionId}`);
    }

    /** Context menu "Go to opening transaction" — same navigation as the modal footer button,
     * just resolved directly from the row's lot without requiring the modal to be open first. */
    function handleGotoOpeningTransaction(lot: LotSummarySchema) {
        handleGotoTransaction(lot.opening_transaction_id);
    }

    /** Reveal a lot before pulsing it in the Gantt: if the current Aperti|Chiusi filter hides it,
     * turn its bucket back on (mirrors the pre-round-3 auto-switch to "Tutti"). */
    function ensureLotVisible(lotId: number) {
        if (visibleLots.some((lot) => lot.lot_id === lotId)) return;
        const lot = lots.find((item) => item.lot_id === lotId);
        if (!lot) return;
        if (lotIsOpenish(lot)) lotStateFilter = {...lotStateFilter, open: true};
        else lotStateFilter = {...lotStateFilter, closed: true};
    }

    /** "Row -> lane" (table double-click, and now also the row context menu's "Go to lot in
     * Gantt" action) — scroll+pulse the matching Gantt lane. */
    function handleTableRowDoubleClick(lotId: number) {
        ensureLotVisible(lotId);
        ganttRef?.pulseLot(lotId);
    }

    /** "Lane -> row" (Gantt double-click) — scroll+pulse the matching table row. */
    function handleGanttRowDoubleClick(lotId: number) {
        tableRef?.navigateToRowId(String(lotId));
    }

    /** First-chart event double-click (plan v3 §9): BUY -> the created lot; SELL/TRANSFER/SPLIT/ADJUSTMENT
     * -> every lot/fragment touched by the same (or paired) transaction. Selects them and pulses the
     * first involved lane in the Gantt. */
    function handleEventDoubleClick(event: LotTimelineEventSchema) {
        const txId = event.transaction_id;
        const relatedId = event.related_transaction_id ?? null;
        const involved = lotEvents.filter((row) => row.transaction_id === txId || (relatedId != null && row.transaction_id === relatedId) || (row.related_transaction_id != null && row.related_transaction_id === txId));
        const lotIds = Array.from(new Set<number>([event.lot_id, ...involved.map((row) => row.lot_id)]));
        if (lotIds.length === 0) return;
        selectedLotIds = lotIds;
        void (async () => {
            await tick();
            ensureLotVisible(lotIds[0]);
            ganttRef?.pulseLot(lotIds[0]);
        })();
    }

    function handleDataQualityAction(_action: string, _target: string | null, _issue: DataQualityIssue) {
        // No CTA navigation defined yet for FIFO lots issues (reference-price fallback etc.
        // are informational-only) — placeholder kept so DataQualityBanner's contract is honored.
    }
</script>

{#if open && assetId != null}
    <div bind:this={panelEl} class="mt-4 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 overflow-hidden" data-testid="lots-analysis-panel" transition:slide={{duration: 200}}>
        <div class="flex items-center justify-between gap-3 px-4 py-3 border-b border-gray-100 dark:border-slate-700">
            <h3 class="min-w-0 font-semibold text-gray-700 dark:text-gray-200" data-testid="lots-analysis-panel-title">
                {$_('brokers.lots.detailTitle')}
                {#if assetName}
                    —
                    {assetName}
                {/if}
            </h3>
            <div class="flex shrink-0 items-center gap-1">
                <button
                    aria-label={$_('brokers.lots.viewAsset')}
                    class="p-1.5 rounded-lg text-gray-400 hover:text-libre-green hover:bg-gray-100 dark:hover:text-emerald-400 dark:hover:bg-slate-700 transition-colors"
                    onclick={() => goto(`/assets/${assetId}`)}
                    data-testid="lots-analysis-panel-asset-link"
                    title={$_('brokers.lots.viewAsset')}
                >
                    <ExternalLink size={16} />
                </button>
                <button class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:text-gray-200 dark:hover:bg-slate-700 transition-colors" onclick={onClose} data-testid="lots-analysis-panel-close" title={$_('common.close')}>
                    <X size={18} />
                </button>
            </div>
        </div>

        <div class="p-4 space-y-4">
            {#if dataQualityIssues.length > 0}
                <DataQualityBanner issues={dataQualityIssues} mode="flat" onaction={handleDataQualityAction} />
            {/if}

            {#if error}
                <div class="py-8 text-center text-red-500 dark:text-red-400 text-sm" data-testid="lots-analysis-panel-error">{error}</div>
            {:else if loading}
                <div class="flex flex-col gap-4" aria-hidden="true" data-testid="lots-analysis-panel-loading">
                    <div class="rounded-lg border border-gray-200/80 bg-gray-50/80 p-4 dark:border-slate-700 dark:bg-slate-900/30">
                        <div class="mb-3 h-5 w-40 animate-pulse rounded bg-gray-200 dark:bg-slate-700"></div>
                        <div class="h-72 w-full animate-pulse rounded bg-gray-200 dark:bg-slate-700"></div>
                    </div>
                    <div class="rounded-xl border border-gray-100 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
                        <div class="mx-auto mb-3 h-5 w-24 animate-pulse rounded bg-gray-200 dark:bg-slate-700"></div>
                        <div class="h-80 w-full animate-pulse rounded bg-gray-100 dark:bg-slate-700"></div>
                    </div>
                </div>
            {:else}
                <LotWacPriceChart
                    lots={visibleLots}
                    {selectedLotIds}
                    {brokerWacHistory}
                    {cumulativeWacHistory}
                    {priceHistory}
                    {lotEvents}
                    {incomeEvents}
                    {brokers}
                    {currency}
                    quoteBaseQuantity={quoteBaseQuantity}
                    {xAxisRange}
                    onZoomChange={handleZoomChange}
                    externalZoomStart={sharedZoomStart}
                    externalZoomEnd={sharedZoomEnd}
                    onEventDoubleClick={handleEventDoubleClick}
                    onSelectionChange={handleSelectionChange}
                />

                <LotGanttChart
                    bind:this={ganttRef}
                    lots={visibleLots}
                    segments={ganttSegments}
                    events={lotEvents}
                    {brokers}
                    {currency}
                    {selectedLotIds}
                    onSelectionChange={handleSelectionChange}
                    {xAxisRange}
                    onZoomChange={handleZoomChange}
                    externalZoomStart={sharedZoomStart}
                    externalZoomEnd={sharedZoomEnd}
                    onRowDoubleClick={handleGanttRowDoubleClick}
                    openSelected={lotStateFilter.open}
                    closedSelected={lotStateFilter.closed}
                    onToggleOpen={() => (lotStateFilter = {...lotStateFilter, open: !lotStateFilter.open})}
                    onToggleClosed={() => (lotStateFilter = {...lotStateFilter, closed: !lotStateFilter.closed})}
                />

                <UnifiedLotsTable
                    bind:this={tableRef}
                    lots={visibleLots}
                    {currency}
                    {brokers}
                    {selectedLotIds}
                    onSelectionChange={handleSelectionChange}
                    onCustodyCellClick={handleCustodyCellClick}
                    onViewGanttLot={handleTableRowDoubleClick}
                    onGotoOpeningTransaction={handleGotoOpeningTransaction}
                    onRowDoubleClick={handleTableRowDoubleClick}
                />

                <LotComparisonChart selectedLots={effectiveSelectedLots} {valueHistory} {returnHistory} {incomeEvents} {brokers} {currency} {xAxisRange} />
            {/if}
        </div>
    </div>

    <LotCustodyModal open={modalOpen} lot={modalLot} history={lotEvents.filter((event) => event.lot_id === modalLot?.lot_id)} {brokers} {currency} onClose={() => (modalOpen = false)} onGotoTransaction={handleGotoTransaction} />
{/if}
