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
    /** The `pageBusy` key of the load: `dashboard-transactions` (default) or `broker-transactions`. */
    busyKey?: string;
    /** The rows and their partner legs are in: the bulk workspace of a page that writes reads them from its store (FB-17). */
    onLoaded?: (mainRows: TXReadItem[], partnerRows: TXReadItem[]) => void;
}

export class PortfolioTransactions {
    mainRows = $state<TXReadItem[]>([]);
    partnerRows = $state<TXReadItem[]>([]);
    eventTooltipMap = $state<Map<number, AssetEvent>>(new Map());
    loading = $state(false);
    currentPage = $state(1);
    pageSize = $state(50);
    private lastKey = $state('');

    constructor(private readonly inputs: PortfolioTransactionsInputs) {}

    /** Loads the rows when `active` and the key moved since the last load. */
    sync(active: boolean): void {
        if (!active) return;
        const brokerIds = this.inputs.brokerIds();
        const brokersKey = brokerIds ? [...brokerIds].sort((a, b) => a - b).join(',') : 'all';
        const {historyStart, end} = this.inputs.period();
        const key = `${historyStart}|${end}|${brokersKey}`;
        if (key !== this.lastKey) {
            this.lastKey = key;
            this.currentPage = 1;
            void pageBusy.track(this.inputs.busyKey ?? 'dashboard-transactions', () => this.load());
        }
    }

    /** The table's page size changed: back to page 1. */
    setPageSize(size: number): void {
        this.pageSize = size;
        this.currentPage = 1;
    }

    /** Asks the rows again, when the tab was opened before (the page's Refresh, a save of the bulk workspace). The rows on screen stay until the new ones land. */
    async reload(): Promise<void> {
        if (this.lastKey === '') return;
        await this.load();
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
                const queries: Record<string, unknown> = {};
                if (brokerId != null) queries.broker_id = brokerId;
                const period = this.inputs.period();
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
            this.inputs.onLoaded?.(this.mainRows, this.partnerRows);
        } finally {
            this.loading = false;
        }
    }
}
