<!--
  RecentTransactionsPanel — Compact read-only list of recent transactions.

  Displays the last N transactions sorted by date (newest first).
  Used in the Dashboard Home bottom section.

  Note: TransactionsTable requires raw mainRows/partnerRows from store — not suitable
  for a lightweight snapshot. This component directly fetches the last N rows and
  renders a simple table with no CRUD actions, no filters, no pagination.

  Props:
  - limit: Number of transactions to show (default 10)
  - brokerIds: Optional broker filter

  Pattern: Svelte 5 Runes, data-testid, dark mode.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {ensureAssetsLoaded, getAssetInfo} from '$lib/stores/reference/assetStore';
    import {ensureBrokersLoaded, getBrokerInfo} from '$lib/stores/reference/brokerStore';
    import {getTransactionTypeIconUrl} from '$lib/stores/transactions/transactionTypeStore';
    import {getBrokerIconUrlById, ensurePluginIconsLoaded} from '$lib/utils/broker/brokerHelpers';

    // Use the type inferred from the Zodios client to avoid mismatch with the
    // component-side TXReadItem (which is a stricter subset).
    type ApiTXRow = Awaited<ReturnType<typeof zodiosApi.query_transactions_api_v1_transactions_get>>[number];

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Max number of recent transactions to show. */
        limit?: number;
        /** If provided, only show transactions for these broker IDs. */
        brokerIds?: number[];
    }

    let {limit = 10, brokerIds}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let rows: ApiTXRow[] = $state([]);
    let loading = $state(true);
    let error = $state<string | null>(null);

    // =========================================================================
    // Data loading
    // =========================================================================

    onMount(async () => {
        await load();
    });

    async function load() {
        loading = true;
        error = null;
        try {
            // Hydrate reference stores before rendering cell content
            await Promise.all([ensureAssetsLoaded(), ensureBrokersLoaded(), ensurePluginIconsLoaded()]);

            const params: Record<string, unknown> = {limit: limit * 3}; // fetch extra to filter partners
            if (brokerIds && brokerIds.length > 0) params.broker_id = brokerIds[0]; // simple single-broker filter

            const all = await zodiosApi.query_transactions_api_v1_transactions_get(params as never);

            // Sort by date descending, then by id descending as tiebreaker
            const sorted = [...all].sort((a, b) => {
                if (b.date !== a.date) return b.date.localeCompare(a.date);
                return b.id - a.id;
            });

            // Keep only non-partner rows (skip "ghost" partner halves of transfers)
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
    // Helpers
    // =========================================================================

    function assetId(tx: ApiTXRow): number | null | undefined {
        const id = tx.asset_id;
        return Array.isArray(id) ? (id[0] as number | null) : id;
    }

    function brokerId(tx: ApiTXRow): number | null {
        const id = tx.broker_id;
        return Array.isArray(id) ? (id[0] as number | null) : (id ?? null);
    }

    function formatAmount(tx: ApiTXRow): string {
        const cash = Array.isArray(tx.cash) ? tx.cash[0] : tx.cash;
        if (!cash) return '—';
        const amt = Number(cash.amount);
        return `${amt.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} ${cash.code}`;
    }

    /** Quantity sub-label for BUY/SELL: "+X TICKER" or "-X TICKER". */
    function quantityLabel(tx: ApiTXRow): string | null {
        const qty = Array.isArray(tx.quantity) ? (tx.quantity[0] ?? null) : tx.quantity;
        if (qty == null) return null;
        const n = parseFloat(String(qty));
        if (isNaN(n) || n === 0) return null;

        const aId = assetId(tx);
        const info = aId ? getAssetInfo(aId) : null;
        const ticker = info?.identifier_ticker ?? null;
        const sign = n > 0 ? '+' : '';
        return ticker ? `${sign}${n.toFixed(Math.abs(n) < 1 ? 4 : 2)} ${ticker}` : null;
    }

    function quantityClass(tx: ApiTXRow): string {
        const qty = Array.isArray(tx.quantity) ? (tx.quantity[0] ?? null) : tx.quantity;
        if (qty == null) return '';
        const n = parseFloat(String(qty));
        return n > 0 ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400';
    }
</script>

<div class="bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm p-4 flex flex-col" data-testid="recent-transactions">
    <!-- Header -->
    <div class="flex items-center justify-between mb-3">
        <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-200">
            {$_('dashboard.recentTransactions')}
        </h2>
        <a href="/transactions" class="text-xs text-libre-green dark:text-green-400 hover:underline font-medium" data-testid="recent-transactions-see-all">
            {$_('dashboard.seeAllTransactions')}
        </a>
    </div>

    {#if loading}
        <!-- Skeleton rows -->
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
            <table class="w-full text-xs">
                <thead>
                    <tr class="text-gray-400 dark:text-gray-500 border-b border-gray-100 dark:border-slate-700">
                        <th class="text-left pb-2 pr-3 font-medium">{$_('common.date')}</th>
                        <th class="text-left pb-2 pr-3 font-medium">{$_('common.type')}</th>
                        <th class="text-left pb-2 pr-3 font-medium">{$_('common.asset')}</th>
                        <th class="text-left pb-2 pr-3 font-medium">{$_('brokers.title')}</th>
                        <th class="text-right pb-2 font-medium">{$_('common.amount')}</th>
                    </tr>
                </thead>
                <tbody>
                    {#each rows as tx (tx.id)}
                        {@const aId = assetId(tx)}
                        {@const bId = brokerId(tx)}
                        {@const asset = aId ? getAssetInfo(aId) : null}
                        {@const broker = bId ? getBrokerInfo(bId) : null}
                        {@const typeIconUrl = getTransactionTypeIconUrl(typeof tx.type === 'string' ? tx.type : '')}
                        {@const brokerIconUrl = bId ? getBrokerIconUrlById(bId, [broker].filter(Boolean) as any[]) : null}
                        {@const qtyLabel = quantityLabel(tx)}
                        <tr class="border-b border-gray-50 dark:border-slate-700/50 hover:bg-gray-50 dark:hover:bg-slate-700/30 transition-colors" data-testid="recent-tx-row">
                            <td class="py-2 pr-3 text-gray-500 dark:text-gray-400 whitespace-nowrap">
                                {tx.date}
                            </td>
                            <td class="py-2 pr-3">
                                <div class="flex items-center gap-1.5">
                                    {#if typeIconUrl}
                                        <img src={typeIconUrl} alt={typeof tx.type === 'string' ? tx.type : ''} class="w-4 h-4 object-contain" />
                                    {/if}
                                </div>
                            </td>
                            <td class="py-2 pr-3 text-gray-600 dark:text-gray-300 truncate max-w-[100px]">
                                {asset?.display_name ?? (aId ? String(aId) : '—')}
                            </td>
                            <!-- Broker: icon + name -->
                            <td class="py-2 pr-3 max-w-[90px]">
                                <div class="flex items-center gap-1.5 min-w-0">
                                    {#if brokerIconUrl}
                                        <img src={brokerIconUrl} alt="" class="w-4 h-4 rounded-sm object-contain flex-shrink-0" onerror={(e) => { (e.target as HTMLElement).style.display = 'none'; }} />
                                    {/if}
                                    <span class="truncate text-gray-500 dark:text-gray-400">{broker?.name ?? (bId ? String(bId) : '—')}</span>
                                </div>
                            </td>
                            <!-- Amount (neutral color) + optional quantity sub-row -->
                            <td class="py-2 text-right whitespace-nowrap">
                                <div class="text-gray-700 dark:text-gray-200 font-medium">{formatAmount(tx)}</div>
                                {#if qtyLabel}
                                    <div class="text-[10px] {quantityClass(tx)}">{qtyLabel}</div>
                                {/if}
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    {/if}
</div>
