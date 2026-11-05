<!--
  PortfolioTransactionsTab — the Transactions tab of the portfolio view.

  Moved whole out of `PortfolioView.svelte` (Y6-7, delivery 2): markup and `data-testid`s are the view's, unchanged. The rows
  are the view's `PortfolioTransactions` (they outlive the tab); a double-click on a row opens it read-only in the form modal.

  A broker's page (delivery 3) shares it and adds what is its own, as optional props: a `bar` of buttons above the table (import
  history, «view in Transactions», columns, and for who can write Import / New / the selection's bulk actions) and the row
  callbacks of the table. The page keeps the bulk workspace and its selection: this tab only hands them the table.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';
    import {RefreshCw} from 'lucide-svelte';
    import TransactionFormModal from '$lib/features/transactions/form/TransactionFormModal.svelte';
    import TransactionsTable from '$lib/features/transactions/TransactionsTable.svelte';
    import {resolveFormItemsForView, type FormModalItems} from '$lib/features/transactions/resolveFormItems';
    import type {TXReadItem} from '$lib/features/transactions/types';
    import type {FilterValue} from '$lib/components/table/types';
    import {getBrokerRole} from '$lib/stores/reference/brokerStore';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import type {PortfolioTransactions} from './portfolioTransactions.svelte';

    /** The period the rows keep to: no `start` while «All» is pending. */
    export interface TransactionsBarPeriod {
        start: string | undefined;
        end: string | undefined;
    }

    interface Props {
        transactions: PortfolioTransactions;
        brokers: BrokerLike[];
        testId: string;
        /** The table's own test id, where the page has one (the broker's `broker-transactions`). */
        tableTestId?: string;
        /** The period on screen. */
        period: TransactionsBarPeriod;
        /** The table, for the page's bar (columns, clearing the selection). */
        table?: TransactionsTable | undefined;
        /** Buttons above the table; they are given the period on screen, for a link to the Transactions page. */
        bar?: Snippet<[{table: TransactionsTable | undefined; period: TransactionsBarPeriod}]>;
        /** The rows' actions and checkboxes are hidden (default: read-only). */
        hideActions?: boolean;
        onSelectionChange?: (rows: TXReadItem[]) => void;
        onEditRow?: (row: TXReadItem) => void;
        onCloneRow?: (row: TXReadItem) => void;
        onDeleteRow?: (row: TXReadItem) => void;
        onFiltersChange?: (filters: Record<string, FilterValue>) => void;
    }

    let {transactions, brokers, period, testId, tableTestId, table = $bindable(), bar, hideActions = true, onSelectionChange, onEditRow, onCloneRow, onDeleteRow, onFiltersChange}: Props = $props();

    /** Transaction view modal state (opened from a row's double-click). */
    let viewOpen = $state(false);
    let viewItems = $state<FormModalItems | null>(null);
</script>

<div class="space-y-4" data-testid={testId}>
    {@render bar?.({table, period})}

    <div data-testid={tableTestId}>
        {#if transactions.loading && transactions.mainRows.length === 0}
            <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-subtle p-12 text-center">
                <RefreshCw class="text-lf-link animate-spin mx-auto" size={28} />
            </div>
        {:else}
            <TransactionsTable
                bind:this={table}
                mainRows={transactions.mainRows}
                partnerRows={transactions.partnerRows}
                {brokers}
                eventTooltipMap={transactions.eventTooltipMap}
                currentPage={transactions.currentPage}
                pageSize={transactions.pageSize}
                {hideActions}
                {onSelectionChange}
                {onEditRow}
                {onCloneRow}
                {onDeleteRow}
                {onFiltersChange}
                onPageChange={(page) => (transactions.currentPage = page)}
                onPageSizeChange={(size) => transactions.setPageSize(size)}
                onViewRow={(row) => {
                    viewItems = resolveFormItemsForView(row as TXReadItem, () => undefined, getBrokerRole);
                    viewOpen = true;
                }}
            />
        {/if}
    </div>
</div>

<!-- Transaction view modal — opened from a row's double-click -->
<TransactionFormModal open={viewOpen} mode="view" items={viewItems} onClose={() => (viewOpen = false)} />
