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
    import {txStoreAddExtras} from '$lib/features/transactions/txStore.svelte';
    import type {BulkAction, FilterValue} from '$lib/components/table/types';
    import {canEditBroker, canEditPaired, getBrokerRole} from '$lib/stores/reference/brokerStore';
    import {zodiosApi} from '$lib/api';
    import {_} from '$lib/i18n';
    import {notify} from '$lib/stores/app/notify.svelte';
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
        /**
         * 77 SEL-B: the bulk actions of the table's selection panel. Absent, the rows have no checkboxes: nothing would act
         * on a selection (the dashboard's tab, a broker the reader cannot edit).
         */
        selectionActions?: BulkAction<TXReadItem>[];
    }

    let {transactions, brokers, period, testId, tableTestId, table = $bindable(), bar, hideActions = true, onSelectionChange, onEditRow, onCloneRow, onDeleteRow, onFiltersChange, selectionActions}: Props = $props();

    /** Transaction view modal state (opened from a row's double-click). */
    let viewOpen = $state(false);
    let viewItems = $state<FormModalItems | null>(null);
    /** Project 66 (F3): the transaction the user came from with «Open», highlighted in the form. */
    let viewHighlightId = $state<number | null>(null);

    /**
     * 66 TL-1b: the view's pencil, as on the Transactions page. Only where the tab edits (a writer's `onEditRow`, actions
     * shown) and for who can edit the row's broker, both brokers for a pair: the pencil closes the view and opens the row
     * in edit, as «Edit» on the row does.
     */
    const viewRow = $derived(viewItems?.[0] && 'id' in viewItems[0] ? (viewItems[0] as TXReadItem) : null);
    const viewCanEdit = $derived.by(() => {
        if (!viewRow) return false;
        if (viewRow.related_transaction_id == null) return canEditBroker(viewRow.broker_id);
        return viewRow.partner_broker_id != null && canEditPaired(viewRow.broker_id, viewRow.partner_broker_id);
    });

    function switchViewToEdit() {
        const row = viewRow;
        viewOpen = false;
        viewHighlightId = null;
        if (!row) return;
        // A row reached with «Open» may be outside the list the tab loaded (a parent before the period): the bulk workspace
        // reads the originals from the store, as `chargesDeleteFlow` adds them.
        txStoreAddExtras([row]);
        onEditRow?.(row);
    }

    /** «Open» in the form (F3): the same modal shows that transaction, read-only, fetched by id. */
    async function openFromForm(id: number) {
        const from = viewItems?.[0] && 'id' in viewItems[0] ? (viewItems[0] as TXReadItem).id : null;
        let row: TXReadItem | undefined;
        try {
            const rows = (await zodiosApi.query_transactions_api_v1_transactions_get({queries: {ids: [id]}} as never)) as TXReadItem[];
            row = (rows ?? []).find((candidate) => candidate.id === id);
        } catch {
            row = undefined; // told below: the form stays on the transaction it shows
        }
        // A late answer: the modal was closed, or it shows another transaction by now.
        const shown = viewItems?.[0] && 'id' in viewItems[0] ? (viewItems[0] as TXReadItem).id : null;
        if (!viewOpen || shown !== from) return;
        if (!row) {
            notify({name: 'tx.form.open.failed', detail: {id}, toast: {variant: 'error', message: $_('transactions.form.openFailed')}});
            return;
        }
        viewHighlightId = from;
        viewItems = resolveFormItemsForView(row, () => undefined, getBrokerRole);
    }
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
                {selectionActions}
                selectable={selectionActions !== undefined}
                onPageChange={(page) => (transactions.currentPage = page)}
                onPageSizeChange={(size) => transactions.setPageSize(size)}
                onViewRow={(row) => {
                    viewHighlightId = null;
                    viewItems = resolveFormItemsForView(row as TXReadItem, () => undefined, getBrokerRole);
                    viewOpen = true;
                }}
            />
        {/if}
    </div>
</div>

<!-- Transaction view modal — opened from a row's double-click -->
<TransactionFormModal open={viewOpen} mode="view" items={viewItems} canEdit={viewCanEdit} onClose={() => (viewOpen = false)} onOpenTransaction={openFromForm} highlightTxId={viewHighlightId} onSwitchToEdit={onEditRow && !hideActions ? switchViewToEdit : undefined} />
