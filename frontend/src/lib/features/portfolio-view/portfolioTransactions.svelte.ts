/**
 * The Transactions tab's rows of the portfolio view (Y6-7, delivery 2) — moved whole out of `PortfolioView.svelte`.
 *
 * Filtered by the SAME broker filter and date range as the rest of the view (not "the recent 10" whatever the period), with
 * real pagination through `TransactionsTable`'s own. The rows are loaded when the tab is active and the broker/date key
 * changes; they live here, not in the tab component, so leaving the tab and coming back with the same key asks nothing again.
 *
 * `sync(active)` is called from an effect of the view, as the old inline effect was: what it reads on the way (the key's
 * parts, and what the load reads before its first await) is what that effect depends on.
 */
import {zodiosApi} from '$lib/api';
import {pageBusy} from '$lib/stores/app/pageBusy.svelte';
import {loadPartnerRows, loadEventTooltipMap} from '$lib/features/transactions/loadTransactionRows';
import type {TXReadItem, AssetEvent} from '$lib/features/transactions/types';

export interface PortfolioTransactionsInputs {
    /** The brokers the user owns: nothing owned → nothing to show (F2). */
    ownedBrokerIds: () => number[];
    /** The brokers the view shows; undefined asks every broker. */
    brokerIds: () => number[] | undefined;
    period: () => {historyStart: string; start: string; end: string; isMaxPending: boolean};
}

export class PortfolioTransactions {
    mainRows = $state<TXReadItem[]>([]);
    partnerRows = $state<TXReadItem[]>([]);
    eventTooltipMap = $state<Map<number, AssetEvent>>(new Map());
    loading = $state(false);
    currentPage = $state(1);
    private lastKey = $state('');

    constructor(private readonly inputs: PortfolioTransactionsInputs) {}

    /** Loads the rows when `active` and the key moved since the last load. */
    sync(active: boolean): void {
        if (!active) return;
        const {historyStart, end} = this.inputs.period();
        const brokerIds = this.inputs.brokerIds();
        const key = `${historyStart}|${end}|${brokerIds ? [...brokerIds].sort((a, b) => a - b).join(',') : 'all'}`;
        if (key !== this.lastKey) {
            this.lastKey = key;
            this.currentPage = 1;
            void pageBusy.track('dashboard-transactions', () => this.load());
        }
    }

    private async load(): Promise<void> {
        // F2: nothing owned → the view (including this tab) shows nothing.
        if (this.inputs.ownedBrokerIds().length === 0) {
            this.mainRows = [];
            this.partnerRows = [];
            return;
        }
        this.loading = true;
        try {
            // Server-side filter: date range always applied; broker_id per-broker (the endpoint
            // only accepts a single broker_id) when a subset is selected, omitted for "all".
            const fetchForBroker = async (brokerId?: number): Promise<TXReadItem[]> => {
                const period = this.inputs.period();
                const queries: Record<string, unknown> = {};
                if (brokerId != null) queries.broker_id = brokerId;
                if (!period.isMaxPending) queries.date_start = period.start;
                if (period.end) queries.date_end = period.end;
                return (await zodiosApi.query_transactions_api_v1_transactions_get({queries})) as TXReadItem[];
            };

            const brokerIds = this.inputs.brokerIds();
            const all = brokerIds && brokerIds.length > 0 ? Array.from(new Map((await Promise.all(brokerIds.map((id) => fetchForBroker(id)))).flat().map((tx) => [tx.id, tx])).values()) : await fetchForBroker(undefined);

            this.mainRows = all;
            const [partner, tooltipMap] = await Promise.all([loadPartnerRows(this.mainRows), loadEventTooltipMap(this.mainRows)]);
            this.partnerRows = partner;
            this.eventTooltipMap = tooltipMap;
        } finally {
            this.loading = false;
        }
    }
}
