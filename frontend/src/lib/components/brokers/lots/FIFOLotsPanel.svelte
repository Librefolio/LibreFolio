<!--
  FIFOLotsPanel — Inline collapsible panel showing FIFO lot detail for one asset across one or
  more brokers (see plan_ui_broker_holdings.md §1ter/§2 + multi-broker evolution 2026-07-11).
  Lives BELOW PositionsPanel in the same tab (not a modal), driven by the parent's `?asset=<id>`
  query-param state.

  Fetches GET /portfolio/lots itself (openLots/closedLots, each tagged with broker_id) and hands
  them to BubbleLotTimeline + Open/ClosedLotsTable, which color/tag rows by broker.
  AssetWacPriceChart fetches its own data (GET /portfolio/asset-history) and renders one WAC line
  per broker + a combined line when brokerIds.length > 1.

  "Goto & Pulse": a bubble click resolves whether the lot is open or closed (buy_transaction_id is
  a DB-global primary key, never collides across brokers) and calls navigateToRowId() on the
  matching table.
-->
<script lang="ts">
    import {tick} from 'svelte';
    import {slide} from 'svelte/transition';
    import {_} from '$lib/i18n';
    import {X} from 'lucide-svelte';
    import {zodiosApi, schemas} from '$lib/api';
    import type {z} from 'zod';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import BubbleLotTimeline from './BubbleLotTimeline.svelte';
    import AssetWacPriceChart from './AssetWacPriceChart.svelte';
    import OpenLotsTable from './OpenLotsTable.svelte';
    import ClosedLotsTable from './ClosedLotsTable.svelte';

    type OpenLotSchema = z.infer<typeof schemas.OpenLotSchema>;
    type ClosedLotSchema = z.infer<typeof schemas.ClosedLotSchema>;
    type DateRange = {min: string; max: string};
    type FifoLotsQueries = Parameters<typeof zodiosApi.get_fifo_lots_api_v1_portfolio_lots_get>[0]['queries'];

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
    let openLots = $state<OpenLotSchema[]>([]);
    let closedLots = $state<ClosedLotSchema[]>([]);
    let assetHistoryRange = $state<DateRange | null>(null);
    let panelEl: HTMLDivElement | undefined = $state(undefined);

    let openLotsTableRef: OpenLotsTable | undefined = $state(undefined);
    let closedLotsTableRef: ClosedLotsTable | undefined = $state(undefined);

    let fetchVersion = 0;
    let previousScrollOpen = false;
    let previousScrollAssetId: number | null = null;

    let lotsRange = $derived.by((): DateRange | null => {
        let min: string | null = null;
        let max: string | null = null;

        for (const lot of openLots) {
            if (min == null || lot.buy_date < min) min = lot.buy_date;
            if (max == null || lot.buy_date > max) max = lot.buy_date;
        }

        for (const lot of closedLots) {
            if (min == null || lot.buy_date < min) min = lot.buy_date;
            if (max == null || lot.buy_date > max) max = lot.buy_date;
            if (lot.sell_date > max) max = lot.sell_date;
        }

        return min != null && max != null ? {min, max} : null;
    });

    let sharedXAxisRange = $derived.by((): DateRange | null => {
        if (!isAllPeriod) return {min: dateFrom, max: dateTo};
        if (assetHistoryRange == null) return lotsRange;
        if (lotsRange == null) return assetHistoryRange;

        return {
            min: assetHistoryRange.min < lotsRange.min ? assetHistoryRange.min : lotsRange.min,
            max: assetHistoryRange.max > lotsRange.max ? assetHistoryRange.max : lotsRange.max,
        };
    });

    const realBrokerIds = $derived.by((): number[] => Array.from(new Set([...openLots, ...closedLots].map((lot) => lot.broker_id))));

    async function loadLots(currentAssetId: number, currentBrokerIds: number[], asOfDate?: string) {
        const version = ++fetchVersion;
        loading = true;
        error = null;
        try {
            const queries = {
                broker_ids: currentBrokerIds,
                asset_id: currentAssetId,
                ...(asOfDate != null ? {as_of_date: asOfDate} : {}),
            } as FifoLotsQueries & {as_of_date?: string};
            const response = await zodiosApi.get_fifo_lots_api_v1_portfolio_lots_get({
                queries: queries as FifoLotsQueries,
            });
            if (version !== fetchVersion) return; // stale response from a since-superseded open/asset change
            openLots = response.open_lots ?? [];
            closedLots = response.closed_lots ?? [];
        } catch (e) {
            if (version !== fetchVersion) return;
            console.error('Failed to load FIFO lots:', e);
            error = $_('brokers.lots.loadFailed');
            openLots = [];
            closedLots = [];
        } finally {
            if (version === fetchVersion) loading = false;
        }
    }

    // Re-fetch whenever the panel opens for a (new) asset — or the broker scope changes (e.g.
    // Dashboard's broker filter). Closing doesn't clear data eagerly — reopening the same asset
    // shows stale-then-fresh, same pattern as other lazy-loaded tabs on this page (e.g. Transazioni).
    $effect(() => {
        const asOfDate = isAllPeriod ? undefined : dateTo;
        if (open && assetId != null) void loadLots(assetId, brokerIds, asOfDate);
    });

    $effect(() => {
        const isPanelOpen = open && assetId != null;
        const shouldScroll = isPanelOpen && (!previousScrollOpen || assetId !== previousScrollAssetId);

        previousScrollOpen = isPanelOpen;
        previousScrollAssetId = assetId;

        if (!shouldScroll) return;

        void (async () => {
            await tick();
            panelEl?.scrollIntoView({behavior: 'smooth', block: 'start'});
        })();
    });

    /** Bubble click → resolve open vs closed lot → "Goto & Pulse" on the matching table.
     *  buy_transaction_id (and sell_transaction_id) are DB-global primary keys — never collide
     *  across brokers, so no broker disambiguation is needed here even with multiple brokers. */
    function handleLotClick(buyTransactionId: number) {
        const closed = closedLots.find((lot) => lot.buy_transaction_id === buyTransactionId);
        if (closed) {
            closedLotsTableRef?.navigateToRowId(`${closed.buy_transaction_id}-${closed.sell_transaction_id}`);
            return;
        }
        const open_ = openLots.find((lot) => lot.buy_transaction_id === buyTransactionId);
        if (open_) {
            openLotsTableRef?.navigateToRowId(String(open_.buy_transaction_id));
        }
    }
</script>

{#if open && assetId != null}
    <div bind:this={panelEl} class="mt-4 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 overflow-hidden" data-testid="fifo-lots-panel" transition:slide={{duration: 200}}>
        <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-slate-700">
            <h3 class="font-semibold text-gray-700 dark:text-gray-200" data-testid="fifo-lots-panel-title">
                {$_('brokers.lots.detailTitle')}{assetName ? ` — ${assetName}` : ''}
            </h3>
            <button class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:text-gray-200 dark:hover:bg-slate-700 transition-colors" onclick={onClose} data-testid="fifo-lots-panel-close" title={$_('common.close')}>
                <X size={18} />
            </button>
        </div>

        <div class="p-4 space-y-4">
            <AssetWacPriceChart {assetId} brokerIds={realBrokerIds} {brokers} {currency} onRangeComputed={(min, max) => (assetHistoryRange = {min, max})} xAxisRange={sharedXAxisRange} />

            {#if loading}
                <div class="py-8 text-center text-gray-400 dark:text-gray-500 text-sm" data-testid="fifo-lots-panel-loading">{$_('common.loading')}</div>
            {:else if error}
                <div class="py-8 text-center text-red-500 dark:text-red-400 text-sm" data-testid="fifo-lots-panel-error">{error}</div>
            {:else}
                <BubbleLotTimeline {openLots} {closedLots} {currency} {brokers} xAxisRange={sharedXAxisRange} onLotClick={handleLotClick} />

                <div data-testid="fifo-open-lots-section">
                    <OpenLotsTable bind:this={openLotsTableRef} lots={openLots} {currency} {brokers} />
                </div>
                <div data-testid="fifo-closed-lots-section">
                    <ClosedLotsTable bind:this={closedLotsTableRef} lots={closedLots} {currency} {brokers} />
                </div>
            {/if}
        </div>
    </div>
{/if}
