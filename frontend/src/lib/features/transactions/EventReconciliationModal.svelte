<!--
  EventReconciliationModal.svelte — «Relink events» (lot X5-3: N68).

  Lists the transactions that could link an asset event and have none (a currency change deletes an asset's events, so the
  transactions linked to them lose the link; a dividend booked before its event was synced has none either), with what the
  server found for each (`GET /transactions/event-reconciliation`, read by `eventReconciliation.ts`):
    - `unique`: exactly one event of the same asset the SAME DAY, of the corresponding type → «Link» (one row) or «Link every row»;
    - `none`: no event that day;
    - `several`: more than one event that day → never guessed, the user picks it in the transaction.
  Nothing is linked on its own. A link is the commit the app already uses (`updates: [{id, asset_event_id}]`, atomic: any
  refusal links nothing and the rows stay).

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {Link2, X} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {getAssetInfo, assetStoreVersion} from '$lib/stores/reference/assetStore';
    import {formatDay} from '$lib/utils/core/formatAxisDate';
    import {linkReconciliation, loadEventReconciliation, uniqueRows, type ReconciliationFilters, type ReconciliationRow} from './eventReconciliation';

    interface Props {
        open: boolean;
        /** Only the transactions of this broker / asset (none: everything the user may link). */
        filters?: ReconciliationFilters;
        zIndex?: number;
        onclose?: () => void;
        /** Called after rows were linked, so the page can reload its transactions. */
        onlinked?: () => void;
    }

    let {open = $bindable(), filters, zIndex = 50, onclose, onlinked}: Props = $props();

    let rows = $state<ReconciliationRow[]>([]);
    let loading = $state(false);
    let loadFailed = $state(false);
    let linkFailed = $state(false);
    /** Transaction ids whose link is on its way, or `'all'`: no second commit meanwhile. */
    let linking = $state<ReadonlySet<number | 'all'>>(new Set());
    /** Bumped on every load, so an answer that arrives after a close or a newer load is ignored. */
    let generation = 0;

    let unique = $derived(uniqueRows(rows));
    let busy = $derived(linking.size > 0);

    async function load() {
        const mine = ++generation;
        loading = true;
        loadFailed = false;
        linkFailed = false;
        try {
            const loaded = await loadEventReconciliation(filters);
            if (mine !== generation) return;
            rows = loaded;
        } catch (error) {
            if (mine !== generation) return;
            console.error('[event-reconciliation] could not read the transactions without an event', error);
            rows = [];
            loadFailed = true;
        } finally {
            if (mine === generation) loading = false;
        }
    }

    // Open → read the list; closed → forget it (a reopening starts from the server's answer).
    $effect(() => {
        if (open) void load();
        else {
            generation++;
            rows = [];
            loading = false;
            loadFailed = false;
            linkFailed = false;
        }
    });

    /** Link `toLink` in one commit; on success they leave the list. */
    async function link(toLink: ReconciliationRow[], key: number | 'all') {
        if (busy || toLink.length === 0) return;
        linking = new Set([key]);
        linkFailed = false;
        try {
            const outcome = await linkReconciliation(toLink);
            if (!outcome.linked) {
                linkFailed = true;
                return;
            }
            const done = new Set(toLink.map((row) => row.transactionId));
            rows = rows.filter((row) => !done.has(row.transactionId));
            onlinked?.();
        } finally {
            linking = new Set();
        }
    }

    function close() {
        open = false;
        onclose?.();
    }

    /** The asset's name when the shared cache has it, else its id. */
    function assetName(assetId: number): string {
        void $assetStoreVersion;
        return getAssetInfo(assetId)?.display_name ?? `#${assetId}`;
    }
</script>

{#if open}
    <ModalBase {open} {zIndex} maxWidth="3xl" onRequestClose={close} testId="event-reconciliation-modal" labelledBy="event-reconciliation-title">
        <div class="flex items-center gap-3 px-5 py-4 border-b border-lf-subtle">
            <Link2 class="text-lf-link flex-shrink-0" size={20} />
            <h2 id="event-reconciliation-title" class="text-base font-semibold text-lf-primary">{$t('transactions.reconcile.title')}</h2>
            <button type="button" class="ml-auto p-1 rounded text-lf-muted hover:bg-lf-hover transition-colors" onclick={close} aria-label={$t('transactions.reconcile.close')} data-testid="event-reconciliation-close">
                <X size={18} />
            </button>
        </div>

        <div class="px-5 py-4 space-y-3 text-sm overflow-y-auto">
            <p class="text-lf-secondary">{$t('transactions.reconcile.intro')}</p>

            {#if loading}
                <p class="text-lf-muted" data-testid="event-reconciliation-loading">{$t('transactions.reconcile.loading')}</p>
            {:else if loadFailed}
                <p class="text-lf-danger" data-testid="event-reconciliation-error">{$t('transactions.reconcile.loadError')}</p>
            {:else if rows.length === 0}
                <p class="text-lf-muted" data-testid="event-reconciliation-empty">{$t('transactions.reconcile.empty')}</p>
            {:else}
                {#if linkFailed}
                    <p class="text-lf-danger" data-testid="event-reconciliation-error">{$t('transactions.reconcile.linkError')}</p>
                {/if}
                <ul class="divide-y divide-lf-subtle border border-lf-subtle rounded-md">
                    {#each rows as row (row.transactionId)}
                        <li class="flex items-center gap-3 px-3 py-2" data-testid="event-reconciliation-row-{row.transactionId}" data-status={row.status} data-candidate-count={row.candidates.length}>
                            <div class="min-w-0 flex-1">
                                <div class="truncate text-lf-primary">{assetName(row.assetId)}</div>
                                <div class="text-xs text-lf-muted">{formatDay(row.date)} · {row.type}</div>
                                <div class="text-xs {row.status === 'unique' ? 'text-lf-success' : 'text-lf-warning'}">
                                    {#if row.status === 'unique'}
                                        {$t('transactions.reconcile.statusUnique')}
                                    {:else if row.status === 'several'}
                                        {$t('transactions.reconcile.statusSeveral', {values: {n: row.candidates.length}})}
                                    {:else}
                                        {$t('transactions.reconcile.statusNone')}
                                    {/if}
                                </div>
                            </div>
                            {#if row.status === 'unique'}
                                <button
                                    type="button"
                                    class="px-3 py-1.5 text-xs rounded-lg bg-lf-action text-lf-on-action hover:bg-lf-action-hover transition-all disabled:opacity-50"
                                    disabled={busy}
                                    onclick={() => link([row], row.transactionId)}
                                    data-testid="event-reconciliation-link-{row.transactionId}"
                                >
                                    {$t('transactions.reconcile.link')}
                                </button>
                            {/if}
                        </li>
                    {/each}
                </ul>
            {/if}
        </div>

        <div class="flex justify-end gap-2 px-5 py-3 border-t border-lf-subtle bg-lf-panel">
            {#if unique.length > 0}
                <button type="button" class="px-4 py-2 text-sm rounded-lg bg-lf-action text-lf-on-action hover:bg-lf-action-hover transition-all disabled:opacity-50" disabled={busy} onclick={() => link(unique, 'all')} data-testid="event-reconciliation-link-all">
                    {$t('transactions.reconcile.linkAll')}
                </button>
            {/if}
        </div>
    </ModalBase>
{/if}
