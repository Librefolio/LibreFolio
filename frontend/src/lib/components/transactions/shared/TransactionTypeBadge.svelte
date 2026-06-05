<!--
  TransactionTypeBadge.svelte — Small badge showing TX type icon + i18n label.

  Renders a PNG icon (from `frontend/static/icons/transactions/`) plus the
  translated label `transactions.types.{TYPE}`. Optional `compact` mode shows
  just the icon (with title tooltip).

  Pattern: Svelte 5 runes, dark mode, `data-testid="tx-type-badge-{TYPE}"`.

  Used by: TransactionsTable, TransactionStagingModal, future BRIM staging.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {getTransactionTypeIconUrl} from '$lib/stores/transactionTypeStore';

    interface Props {
        /** Transaction type code (e.g. 'BUY', 'FX_CONVERSION'). */
        type: string;
        /** Compact mode: icon only with tooltip. */
        compact?: boolean;
        /** Optional extra class on the wrapper. */
        class?: string;
    }

    let {type, compact = false, class: className = ''}: Props = $props();

    let label = $derived($t(`transactions.types.${type}`) || type);
    let iconUrl = $derived(getTransactionTypeIconUrl(type));

    /**
     * Per-type background hue. Values chosen for high contrast in light/dark
     * mode; kept inline (not in transactionTypes.ts) because they are purely
     * presentational.
     */
    const TYPE_COLORS: Record<string, string> = {
        BUY: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400',
        SELL: 'bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-400',
        DIVIDEND: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400',
        INTEREST: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400',
        DEPOSIT: 'bg-sky-100 dark:bg-sky-900/30 text-sky-700 dark:text-sky-400',
        WITHDRAWAL: 'bg-slate-100 dark:bg-slate-700/40 text-slate-700 dark:text-slate-300',
        FEE: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400',
        TAX: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
        TRANSFER: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400',
        FX_CONVERSION: 'bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-400',
        ADJUSTMENT: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300',
    };
    let colorClass = $derived(TYPE_COLORS[type] ?? 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400');

    function hideOnError(e: Event) {
        const img = e.currentTarget as HTMLImageElement | null;
        if (img) img.style.display = 'none';
    }
</script>

{#if compact}
    <span class={`inline-flex items-center justify-center w-6 h-6 rounded ${colorClass} ${className}`} title={label} data-testid={`tx-type-badge-${type}`}>
        <img src={iconUrl} alt={label} class="w-4 h-4 object-contain" onerror={hideOnError} />
    </span>
{:else}
    <span class={`inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded ${colorClass} ${className}`} data-testid={`tx-type-badge-${type}`}>
        <img src={iconUrl} alt="" class="w-3.5 h-3.5 object-contain shrink-0" onerror={hideOnError} />
        <span>{label}</span>
    </span>
{/if}
