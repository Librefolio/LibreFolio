<!--
  PortfolioTransactionsTab — the Transactions tab of the portfolio view.

  Moved whole out of `PortfolioView.svelte` (Y6-7, delivery 2): markup and `data-testid`s are the view's, unchanged. The rows
  are the view's `PortfolioTransactions` (they outlive the tab); a double-click on a row opens it read-only in the form modal.
-->
<script lang="ts">
    import {RefreshCw} from 'lucide-svelte';
    import TransactionFormModal from '$lib/features/transactions/form/TransactionFormModal.svelte';
    import TransactionsTable from '$lib/features/transactions/TransactionsTable.svelte';
    import {resolveFormItemsForView, type FormModalItems} from '$lib/features/transactions/resolveFormItems';
    import type {TXReadItem} from '$lib/features/transactions/types';
    import {getBrokerRole} from '$lib/stores/reference/brokerStore';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import type {PortfolioTransactions} from './portfolioTransactions.svelte';

    interface Props {
        transactions: PortfolioTransactions;
        brokers: BrokerLike[];
    }

    let {transactions, brokers}: Props = $props();

    /** Transaction view modal state (opened from a row's double-click). */
    let viewOpen = $state(false);
    let viewItems = $state<FormModalItems | null>(null);
</script>

<div data-testid="dashboard-transactions-tab">
    {#if transactions.loading && transactions.mainRows.length === 0}
        <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-subtle p-12 text-center">
            <RefreshCw class="text-lf-link animate-spin mx-auto" size={28} />
        </div>
    {:else}
        <TransactionsTable
            mainRows={transactions.mainRows}
            partnerRows={transactions.partnerRows}
            {brokers}
            eventTooltipMap={transactions.eventTooltipMap}
            currentPage={transactions.currentPage}
            hideActions={true}
            onPageChange={(page) => (transactions.currentPage = page)}
            onViewRow={(row) => {
                viewItems = resolveFormItemsForView(row as TXReadItem, () => undefined, getBrokerRole);
                viewOpen = true;
            }}
        />
    {/if}
</div>

<!-- Transaction view modal — opened from a row's double-click -->
<TransactionFormModal open={viewOpen} mode="view" items={viewItems} onClose={() => (viewOpen = false)} />
