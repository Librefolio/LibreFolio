<!--
  EventReconciliationModal.svelte — «Relink events» (lot X5-3: N68; the table, the filters and the creation of FB-19).

  Lists the transactions that could link an asset event and have none (a currency change deletes an asset's events, so the
  transactions linked to them lose the link; a dividend booked before its event was synced has none either), with what the
  server found for each (`GET /transactions/event-reconciliation`, read by `eventReconciliation.ts`), in the project's
  `DataTable`: asset, broker, day, the event (its emoji and its name in the interface language) and the status. Its column
  filters narrow the list by asset or broker, and «Link every row» acts on the rows the filters leave.
    - `unique`: exactly one event of the same asset the SAME DAY, of the corresponding type → «Link» (one row), «Link
      selected» or «Link every row»;
    - `none`: no event that day → «Create event» (one row) or «Create events» (the selected rows): the dialog
      `EventReconciliationCreateModal.svelte` creates what they miss, and the rows then have an event to link;
    - `several`: more than one event that day → never guessed, the user picks it in the transaction.
  Nothing is linked on its own. A link is the commit the app already uses (`updates: [{id, asset_event_id}]`, atomic: any
  refusal links nothing and the rows stay).

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {Link2, Plus, X} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import SelectionBar from '$lib/components/table/SelectionBar.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import {getAssetInfo, assetStoreVersion} from '$lib/stores/reference/assetStore';
    import {getBrokerInfo, brokerStoreVersion} from '$lib/stores/reference/brokerStore';
    import {formatDay} from '$lib/utils/core/formatAxisDate';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {ensureTypesLoaded, getEventTypeEmoji, typesVersion} from '$lib/features/transactions/transactionTypeStore';
    import EventReconciliationCreateModal from './EventReconciliationCreateModal.svelte';
    import {eventTypeToShow, linkReconciliation, loadEventReconciliation, uniqueRows, type ReconciliationFilters, type ReconciliationRow} from './eventReconciliation';

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
    /** The rows as the list was read: the filters' options come from them, not from the rows that are left, so that a filter set on an
     * asset or broker whose rows were all linked can still be taken off. */
    let optionRows = $state<ReconciliationRow[]>([]);
    let loading = $state(false);
    let loadFailed = $state(false);
    let linkFailed = $state(false);
    /** Transaction ids whose link is on its way, or `'all'`: no second commit meanwhile. */
    let linking = $state<ReadonlySet<number | 'all'>>(new Set());
    /** Bumped on every load, so an answer that arrives after a close or a newer load is ignored. */
    let generation = 0;

    /** The rows the column filters leave, in display order (`null` before the table reports): «Link every row» acts on them. */
    let displayedIds = $state<string[] | null>(null);
    let displayedRows = $derived(displayedIds === null ? rows : rows.filter((row) => displayedIds!.includes(String(row.transactionId))));
    let unique = $derived(uniqueRows(displayedRows));
    let busy = $derived(linking.size > 0);
    /** The selected rows (their transaction ids) and the table, to clear its selection. */
    let selectedIds = $state<string[]>([]);
    let tableRef: DataTable<ReconciliationRow> | undefined = $state(undefined);
    let selectedRows = $derived(rows.filter((row) => selectedIds.includes(String(row.transactionId))));
    /** The rows the creation dialog is open for (none: closed). */
    let creating = $state<ReconciliationRow[] | null>(null);
    /** What a bulk action found nothing to act on, said once. */
    let notice = $state<'nothingToLink' | 'nothingToCreate' | null>(null);

    async function load() {
        const mine = ++generation;
        loading = true;
        loadFailed = false;
        linkFailed = false;
        try {
            const loaded = await loadEventReconciliation(filters);
            if (mine !== generation) return;
            rows = loaded;
            optionRows = loaded;
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
        if (open) {
            // The events' emojis come from the types the server lists: asked here too, for a page that has not
            ensureTypesLoaded().catch((error) => console.warn('[event-reconciliation] the event types could not be read: the emoji stay generic', error));
            void load();
        } else {
            generation++;
            rows = [];
            optionRows = [];
            loading = false;
            loadFailed = false;
            linkFailed = false;
            displayedIds = null;
            selectedIds = [];
            creating = null;
            notice = null;
        }
    });

    /** Link `toLink` in one commit; on success they leave the list. */
    async function link(toLink: ReconciliationRow[], key: number | 'all') {
        if (busy || toLink.length === 0) return;
        linking = new Set([key]);
        linkFailed = false;
        notice = null;
        try {
            const outcome = await linkReconciliation(toLink);
            if (!outcome.linked) {
                linkFailed = true;
                return;
            }
            const done = new Set(toLink.map((row) => row.transactionId));
            rows = rows.filter((row) => !done.has(row.transactionId));
            tableRef?.clearSelection();
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

    /** The broker's name when the shared cache has it, else its id. */
    function brokerName(brokerId: number): string {
        void $brokerStoreVersion;
        return getBrokerInfo(brokerId)?.name ?? `#${brokerId}`;
    }

    /** The event a row is about, as the interface names it: its emoji and its name. An adjustment with no event yet may become a split or a price adjustment: the transaction's own name. */
    function eventName(row: ReconciliationRow): {code: string; emoji: string; label: string} {
        void $typesVersion;
        const type = eventTypeToShow(row);
        if (type !== null) return {code: type, emoji: getEventTypeEmoji(type), label: $t(`assetDetail.eventType.${type}`) || type};
        return {code: row.type, emoji: getEventTypeEmoji('PRICE_ADJUSTMENT'), label: $t(`transactions.types.${row.type}`) || row.type};
    }

    /** The label of a button-looking cell: the DataTable draws its HTML as a button. */
    const cellButton = (label: string) => `<span class="inline-block px-3 py-1.5 text-xs rounded-lg bg-lf-action text-lf-on-action hover:bg-lf-action-hover transition-all">${escapeHtml(label)}</span>`;

    function distinct<T>(values: T[]): T[] {
        return [...new Set(values)];
    }

    let columns = $derived<ColumnDef<ReconciliationRow>[]>([
        {
            id: 'asset',
            header: () => $t('transactions.reconcile.colAsset'),
            type: 'enum',
            getValue: (row) => String(row.assetId),
            enumOptions: distinct(optionRows.map((row) => row.assetId)).map((id) => ({value: String(id), label: assetName(id)})),
            cell: (row) => assetName(row.assetId),
        },
        {
            id: 'broker',
            header: () => $t('transactions.reconcile.colBroker'),
            type: 'enum',
            getValue: (row) => String(row.brokerId),
            enumOptions: distinct(optionRows.map((row) => row.brokerId)).map((id) => ({value: String(id), label: brokerName(id)})),
            cell: (row) => brokerName(row.brokerId),
        },
        {
            id: 'date',
            header: () => $t('common.date'),
            type: 'date',
            getValue: (row) => row.date,
            cell: (row) => formatDay(row.date),
        },
        {
            id: 'event',
            header: () => $t('transactions.reconcile.colEvent'),
            type: 'enum',
            getValue: (row) => eventName(row).code,
            enumOptions: distinct(optionRows.map((row) => eventName(row).code)).map((code) => {
                const named = eventName(optionRows.find((row) => eventName(row).code === code)!);
                return {value: code, label: `${named.emoji} ${named.label}`};
            }),
            cell: (row) => {
                const named = eventName(row);
                return {type: 'html', html: `<span data-event-type="${escapeHtml(named.code)}">${escapeHtml(named.emoji)} ${escapeHtml(named.label)}</span>`};
            },
        },
        {
            id: 'status',
            header: () => $t('transactions.reconcile.colStatus'),
            type: 'enum',
            getValue: (row) => row.status,
            enumOptions: (['unique', 'none', 'several'] as const).map((status) => ({value: status, label: $t(`transactions.reconcile.status.${status}`)})),
            cell: (row) => {
                const text = row.status === 'unique' ? $t('transactions.reconcile.statusUnique') : row.status === 'several' ? $t('transactions.reconcile.statusSeveral', {values: {n: row.candidates.length}}) : $t('transactions.reconcile.statusNone');
                const tone = row.status === 'unique' ? 'text-lf-success' : 'text-lf-warning';
                return {
                    type: 'html',
                    html: `<span class="${tone}" data-testid="event-reconciliation-row-${row.transactionId}" data-status="${row.status}" data-candidate-count="${row.candidates.length}">${escapeHtml(text)}</span>`,
                };
            },
        },
        {
            id: 'action',
            header: '',
            displayName: () => $t('transactions.reconcile.colAction'),
            type: 'text',
            sortable: false,
            filterable: false,
            cell: (row) => {
                if (row.status === 'unique') return {type: 'html', html: cellButton($t('transactions.reconcile.link')), onClick: () => void link([row], row.transactionId), testId: `event-reconciliation-link-${row.transactionId}`};
                if (row.status === 'none') return {type: 'html', html: cellButton($t('transactions.reconcile.createOne')), onClick: () => openCreate([row]), testId: `event-reconciliation-create-${row.transactionId}`};
                return '';
            },
        },
    ]);

    /** Open the creation dialog for the rows that miss their event (the `none` ones). */
    function openCreate(candidates: ReconciliationRow[]) {
        const missing = candidates.filter((row) => row.status === 'none');
        if (missing.length === 0) {
            notice = 'nothingToCreate';
            return;
        }
        notice = null;
        creating = missing;
    }

    /** The events were created: read the list again, where those rows now have an event. */
    async function created() {
        creating = null;
        tableRef?.clearSelection();
        await load();
    }

    /** The selection's actions, on the rows selected now. */
    let selectionActions = $derived([
        {
            id: 'link',
            icon: Link2,
            label: () => $t('transactions.reconcile.linkSelected'),
            onClick: () => {
                const ready = uniqueRows(selectedRows);
                if (ready.length === 0) notice = 'nothingToLink';
                else void link(ready, 'all');
            },
        },
        {id: 'create', icon: Plus, label: () => $t('transactions.reconcile.createSelected'), onClick: () => openCreate(selectedRows)},
    ]);
</script>

{#if open}
    <ModalBase {open} {zIndex} maxWidth="5xl" onRequestClose={close} testId="event-reconciliation-modal" labelledBy="event-reconciliation-title">
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
                {#if notice}
                    <p class="text-lf-warning" data-testid="event-reconciliation-notice">{notice === 'nothingToLink' ? $t('transactions.reconcile.nothingToLink') : $t('transactions.reconcile.nothingToCreate')}</p>
                {/if}
                <div class="flex items-center gap-2 min-h-8">
                    <SelectionBar actions={selectionActions} selectedCount={selectedIds.length} onClearSelection={() => tableRef?.clearSelection()} />
                </div>
                <div data-testid="event-reconciliation-table">
                    <DataTable
                        bind:this={tableRef}
                        data={rows}
                        {columns}
                        getRowId={(row) => String(row.transactionId)}
                        storageKey="event-reconciliation"
                        enableSelection={true}
                        selectionMode="multi"
                        onSelectionChange={(ids) => (selectedIds = ids)}
                        enableActions={false}
                        enableSorting={true}
                        enableColumnFilters={true}
                        enableColumnResize={false}
                        enablePagination={rows.length > 25}
                        enableColumnVisibility={false}
                        defaultPageSize={25}
                        tableLayout="auto"
                        onRowOrderChange={(ids) => (displayedIds = ids)}
                    />
                </div>
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

    <EventReconciliationCreateModal open={creating !== null} rows={creating ?? []} zIndex={zIndex + 10} onclose={() => (creating = null)} oncreated={created} />
{/if}
