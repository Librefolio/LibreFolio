<!--
  RecentTransactionsPanel — Compact read-only list of recent transactions.

  Wraps TransactionsTable in compact mode for the Dashboard Home bottom section.
  Reuses all TransactionsTable rendering (icons, formatters, colors, dark mode)
  with hidden columns and no CRUD actions.

  Columns shown: Date, Type, Quantity, Cash, Asset, Broker.
  Hidden: Links, Tags, ID, Description.

  Props:
  - limit: Number of transactions to show (default 10)
  - brokerIds: Optional broker filter
  - transactionsHref: Pre-built href for "See all" link
  - onViewRow: Callback when a row is double-clicked

  Pattern: Svelte 5 Runes, data-testid, dark mode.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {ensureAssetsLoaded} from '$lib/stores/reference/assetStore';
    import {ensureBrokersLoaded, getAllBrokers} from '$lib/stores/reference/brokerStore';
    import {ensurePluginIconsLoaded} from '$lib/utils/broker/brokerHelpers';
    import TransactionsTable from '$lib/components/transactions/TransactionsTable.svelte';
    import type {TXReadItem} from '$lib/components/transactions/types';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Max number of recent transactions to show. */
        limit?: number;
        /** If provided, only show transactions for these broker IDs. */
        brokerIds?: number[];
        /** Pre-built href for "See all" link (includes date range params). */
        transactionsHref?: string;
        /** Callback when a row is activated (double-click / long-press). */
        onViewRow?: (row: TXReadItem) => void;
    }

    let {limit = 10, brokerIds, transactionsHref = '/transactions', onViewRow}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let rows: TXReadItem[] = $state([]);
    let loading = $state(true);
    let error: string | null = $state(null);
    let lastLoadKey = $state('');

    // =========================================================================
    // Data loading
    // =========================================================================

    onMount(async () => {
        await Promise.all([ensureAssetsLoaded(), ensureBrokersLoaded(), ensurePluginIconsLoaded()]);
    });

    $effect(() => {
        const key = `${limit}|${brokerIds ? [...brokerIds].sort((a, b) => a - b).join(',') : 'all'}`;
        if (key !== lastLoadKey) {
            lastLoadKey = key;
            void load();
        }
    });

    async function load() {
        loading = true;
        error = null;
        try {
            const fetchForBroker = async (brokerId?: number): Promise<TXReadItem[]> => {
                const params: Record<string, unknown> = {limit: limit * 3};
                if (brokerId != null) params.broker_id = brokerId;
                return (await zodiosApi.query_transactions_api_v1_transactions_get(params as never)) as TXReadItem[];
            };

            const all =
                brokerIds && brokerIds.length > 1
                    ? Array.from(new Map((await Promise.all(brokerIds.map((id) => fetchForBroker(id)))).flat().map((tx) => [tx.id, tx])).values())
                    : await fetchForBroker(brokerIds?.[0]);

            const sorted = [...all].sort((a, b) => {
                if (b.date !== a.date) return b.date.localeCompare(a.date);
                return b.id - a.id;
            });

            // Keep only non-partner rows (skip ghost partner halves of transfers)
            const partnerIds = new Set(sorted.map((tx) => tx.related_transaction_id).filter(Boolean));
            const mainRows = sorted.filter((tx) => !partnerIds.has(tx.id));

            rows = mainRows.slice(0, limit);
        } catch (err) {
            error = err instanceof Error ? err.message : String(err);
        } finally {
            loading = false;
        }
    }

    // =========================================================================
    // Derived
    // =========================================================================

    let brokers = $derived(getAllBrokers() as BrokerLike[]);

    const HIDDEN_COLUMNS = ['links', 'tags', 'id', 'description'];

    function handleRowDoubleClick(row: TXReadItem) {
        onViewRow?.(row);
    }
</script>

<div class="bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm p-4 flex flex-col" data-testid="recent-transactions">
    <!-- Header -->
    <div class="flex items-center justify-between mb-3">
        <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-200">
            {$_('dashboard.recentTransactions')}
        </h2>
        <a href={transactionsHref} class="text-xs text-libre-green dark:text-green-400 hover:underline font-medium" data-testid="recent-transactions-see-all">
            {$_('dashboard.seeAllTransactions')}
        </a>
    </div>

    {#if loading}
        <div class="space-y-2 flex-1">
            {#each {length: 4} as _}
                <div class="h-10 bg-gray-100 dark:bg-slate-700 rounded animate-pulse"></div>
            {/each}
        </div>
    {:else if error}
        <p class="text-sm text-red-500 dark:text-red-400 py-4 text-center">{error}</p>
    {:else if rows.length === 0}
        <p class="text-sm text-gray-400 dark:text-gray-500 py-4 text-center flex-1 flex items-center justify-center">
            {$_('dashboard.noData')}
        </p>
    {:else}
        <div class="overflow-x-auto flex-1">
            <TransactionsTable
                mainRows={rows}
                partnerRows={[]}
                {brokers}
                eventTooltipMap={new Map()}
                pageSize={limit}
                compact={true}
                hiddenColumns={HIDDEN_COLUMNS}
                storageKeyOverride="dashboard-recent-tx"
                onRowDoubleClickOverride={handleRowDoubleClick}
            />
        </div>
    {/if}
</div>
