<!--
  TxChargesActionModal.svelte — the rich confirmation of the linked charges (project 66, lot F6), sibling of
  TransactionActionModal (split and promote, which keep their hand-drawn tables).
  - mode='link' (Z): one parent and N charges chosen in the table's selection → «Link».
  - mode='unlink' (66 TL-9): the linked charges chosen in the table's selection, with no parent column (a parent may not be
    in the page's list): a row «Linked to» names each one's parent by its `#id` → «Unlink».
  - mode='deleteParent' (V1): one or more parents whose charges are not all deleted → «Cancel · Keep the charges ·
    Delete all (N)»; the choice goes to the Bulk. The Bulk opens it too (66 F7-c2), with new charges (id 0) among them.
  «Before» is a DataTable with one column per transaction (positional ids `c0…`, nothing tied to a transaction id is
  stored) and a minimum width per column: on a phone the table pans sideways.
  Every row is named by one reference (`txRowRef`, 66 F7-d): `#123` for a saved one; for a new one the caller's
  (`parentRefs`/`chargeRefs`: the Bulk passes its row labels), or «new».
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Link2, Trash2, Unlink} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import BrokerBadge from '$lib/components/ui/display/BrokerBadge.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import {getBrokerInfo, getAccessibleBrokers} from '$lib/stores/reference/brokerStore';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import {formatTxQuantity, formatTxCash} from './txDisplayHelpers';
    import type {TXReadItem} from './types';
    import {txRowRef} from './chargeLinkRules';

    interface Props {
        open: boolean;
        mode: 'link' | 'unlink' | 'deleteParent';
        parents: TXReadItem[];
        charges: TXReadItem[];
        loading?: boolean;
        /** Link and unlink mode: the user confirms. */
        onConfirm?: () => void;
        /** Delete mode: keep the charges (unlinked) or delete them too. */
        onChoose?: (choice: 'keep' | 'all') => void;
        /**
         * Delete mode: the rows that stay unlinked with «Keep the charges» and the rows «Delete all» deletes, as the
         * caller's intent counts them (`deleteIntent`). A mixed selection differs from parents + charges: a selected
         * charge is deleted anyway, an unrelated selected row is deleted too. Absent: parents + all their charges.
         */
        counts?: {keep: number; all: number};
        onCancel: () => void;
        /** Stacking level: above the Bulk when the Bulk opens it (66 F7-c2). */
        zIndex?: number;
        /** How the caller names each parent and charge, in the same order (66 F7-d: the Bulk names a new row by its
         *  label). Absent or empty at an index: `#id`, or «new» for a row not saved yet. */
        parentRefs?: (string | null)[];
        chargeRefs?: (string | null)[];
    }

    let {open, mode, parents, charges, loading = false, onConfirm, onChoose, counts, onCancel, zIndex = 50, parentRefs, chargeRefs}: Props = $props();

    type Field = 'date' | 'type' | 'cash' | 'quantity' | 'broker' | 'parent';
    interface FieldRow {
        field: Field;
    }
    const FIELDS: FieldRow[] = [{field: 'date'}, {field: 'type'}, {field: 'cash'}, {field: 'quantity'}, {field: 'broker'}];
    let fieldRows = $derived<FieldRow[]>(mode === 'unlink' ? [...FIELDS, {field: 'parent'}] : FIELDS);

    /** The one reference of a row (`txRowRef`): the caller's label for a new row, `#id` for a saved one. */
    const refOf = (tx: TXReadItem, given: string | null | undefined): string => (tx.id > 0 ? txRowRef(tx.id, null, $t) : given || txRowRef(null, null, $t));

    /** Each parent followed by its charges; a charge of no listed parent (link mode) after them, in order. Grouped by
     *  object, never by id: in the Bulk two new charges both have id 0 (66 F7-c2). Each with its reference. */
    let columnsTx = $derived.by(() => {
        const out: {tx: TXReadItem; ref: string}[] = [];
        const placed = new Set<number>();
        parents.forEach((p, pi) => {
            out.push({tx: p, ref: refOf(p, parentRefs?.[pi])});
            charges.forEach((c, ci) => {
                if (c.parent_transaction_id === p.id && !placed.has(ci)) {
                    out.push({tx: c, ref: refOf(c, chargeRefs?.[ci])});
                    placed.add(ci);
                }
            });
        });
        charges.forEach((c, ci) => {
            if (!placed.has(ci)) out.push({tx: c, ref: refOf(c, chargeRefs?.[ci])});
        });
        return out;
    });

    let brokers = $derived(getAccessibleBrokers() as BrokerLike[]);
    const brokerOf = (id: number): BrokerLike => (getBrokerInfo(id) as BrokerLike) ?? ({id, name: `#${id}`} as BrokerLike);
    const typeLabel = (type: string): string => $t(`transactions.types.${type}`) || type;

    function fieldLabel(field: Field): string {
        if (field === 'date') return $t('common.date') || 'Date';
        if (field === 'type') return $t('common.type') || 'Type';
        if (field === 'cash') return $t('transactions.table.cash') || 'Amount';
        if (field === 'quantity') return $t('transactions.table.quantity') || 'Qty';
        if (field === 'parent') return $t('transactions.form.parent.title') || 'Linked to';
        return $t('transactions.table.broker') || 'Broker';
    }

    let columns = $derived.by((): ColumnDef<FieldRow>[] => [
        {id: 'field', header: '', type: 'text', width: 110, minWidth: 90, sortable: false, filterable: false, resizable: false, cell: (r) => fieldLabel(r.field)},
        ...columnsTx.map(
            ({tx, ref}, i): ColumnDef<FieldRow> => ({
                id: `c${i}`,
                // A transaction not saved yet (the Bulk's new rows, 66 F7-c2) has no #id: its label, or «new» (66 F7-d).
                header: tx.id > 0 ? `TX ${ref}` : ref,
                type: 'text',
                width: 150,
                minWidth: 130,
                sortable: false,
                filterable: false,
                resizable: false,
                cell: (r) => {
                    if (r.field === 'date') return tx.date;
                    if (r.field === 'type') return typeLabel(tx.type);
                    if (r.field === 'cash') return formatTxCash(tx.cash);
                    if (r.field === 'quantity') return formatTxQuantity(tx.quantity);
                    if (r.field === 'parent') return txRowRef(tx.parent_transaction_id, null, $t);
                    return {type: 'custom', component: BrokerBadge, props: {broker: brokerOf(tx.broker_id), brokers}};
                },
            }),
        ),
    ]);

    let total = $derived(columnsTx.length);
    let chargeCount = $derived(columnsTx.length - parents.length);
    let keepCount = $derived(counts?.keep ?? chargeCount);
    let allCount = $derived(counts?.all ?? total);
    let firstParent = $derived(parents[0] ?? null);
    let firstParentRef = $derived(firstParent ? refOf(firstParent, parentRefs?.[0]) : '');

    let title = $derived.by(() => {
        if (mode === 'link') return $t('transactions.chargesLink.title') || 'Link the charges';
        if (mode === 'unlink') return $t('transactions.bulk.unlinkSelected') || 'Unlink the charges';
        if (parents.length > 1) return $t('transactions.chargesDelete.titleMany', {values: {n: parents.length}}) || `Delete ${parents.length} transactions with charges?`;
        return firstParent ? $t('transactions.chargesDelete.title', {values: {type: typeLabel(firstParent.type), ref: firstParentRef}}) || `Delete ${typeLabel(firstParent.type)} ${firstParentRef}?` : '';
    });
</script>

<ModalBase {open} maxWidth="xl" onRequestClose={onCancel} testId="tx-charges-modal" {zIndex}>
    <div class="flex flex-col max-h-[80vh]" data-testid="tx-charges-modal-content" data-mode={mode}>
        <div class="p-6 pb-3 border-b border-lf-subtle shrink-0">
            <div class="flex items-center gap-2 text-lg font-semibold text-lf-primary">
                {#if mode === 'link'}
                    <Link2 size={20} class="text-lf-success" />
                {:else if mode === 'unlink'}
                    <Unlink size={20} class="text-lf-warning" />
                {:else}
                    <Trash2 size={20} class="text-lf-danger" />
                {/if}
                <span>{title}</span>
            </div>
        </div>

        <div class="p-6 py-4 space-y-4 overflow-y-auto flex-1 min-h-0">
            {#if mode === 'link' && firstParent}
                <p class="text-sm text-lf-secondary">
                    {$t('transactions.chargesLink.subtitle', {values: {n: total, type: typeLabel(firstParent.type)}}) || `${total} separate rows → 1 ${typeLabel(firstParent.type)} with its charges`}
                </p>
            {:else if firstParent}
                <p class="text-sm text-lf-secondary">
                    {$t('transactions.chargesDelete.lead', {values: {n: chargeCount}}) || `${chargeCount} linked charges`}
                </p>
            {/if}

            <div class="text-xs font-semibold text-lf-muted uppercase tracking-wide">{$t('common.before') || 'Before'}</div>
            <div class="border border-lf-subtle rounded-lg" data-testid="tx-charges-modal-table">
                <DataTable
                    data={fieldRows}
                    {columns}
                    getRowId={(r) => r.field}
                    storageKey="txChargesModal"
                    selectionMode="none"
                    enableSelection={false}
                    enableActions={false}
                    enableSorting={false}
                    enableColumnFilters={false}
                    enableColumnResize={false}
                    enablePagination={false}
                    enableColumnVisibility={false}
                    enableContextMenu={false}
                />
            </div>

            {#if mode === 'link' && firstParent}
                <div class="rounded-lg border border-lf-success-line bg-lf-success-soft p-3 text-sm text-lf-success-on-soft" data-testid="tx-charges-modal-target">
                    {$t('transactions.chargesLink.target', {values: {type: typeLabel(firstParent.type), ref: firstParentRef, n: chargeCount}}) || `${typeLabel(firstParent.type)} ${firstParentRef} with ${chargeCount} linked charges`}
                </div>
                <p class="text-xs text-lf-muted flex items-start gap-1.5">
                    <span>⚠️</span>
                    <span>{$t('transactions.chargesLink.note') || 'The charges stay transactions of their own: only the link changes.'}</span>
                </p>
            {:else if mode === 'unlink'}
                <div class="rounded-lg border border-lf-warning-line bg-lf-warning-soft p-3 text-sm text-lf-warning-on-soft" data-testid="tx-charges-modal-target">
                    {$t('transactions.chargesUnlink.target', {values: {n: chargeCount}}) || `${chargeCount} charges no longer linked: each stays a transaction of its own`}
                </div>
                <p class="text-xs text-lf-muted flex items-start gap-1.5">
                    <span>⚠️</span>
                    <span>{$t('transactions.chargesLink.note') || 'The charges stay transactions of their own: only the link changes.'}</span>
                </p>
            {:else if mode === 'deleteParent'}
                <div class="text-xs font-semibold text-lf-muted uppercase tracking-wide">{$t('common.after') || 'After'}</div>
                <ul class="space-y-1 text-sm text-lf-secondary">
                    <li data-testid="tx-charges-modal-keep-after">
                        <span class="font-medium text-lf-primary">{$t('transactions.chargesDelete.keep') || 'Keep the charges'}</span>: {$t('transactions.chargesDelete.keepAfter', {values: {n: keepCount}}) || 'the charges stay, as rows of their own no longer linked'}
                    </li>
                    <li data-testid="tx-charges-modal-all-after"><span class="font-medium text-lf-primary">{$t('transactions.chargesDelete.allShort') || 'Delete all'}</span>: {$t('transactions.chargesDelete.allAfter', {values: {n: allCount}}) || `none of the ${allCount} rows stays`}</li>
                </ul>
            {/if}
        </div>

        <div class="p-6 pt-3 border-t border-lf-subtle shrink-0">
            {#if mode !== 'deleteParent'}
                <div class="flex justify-end gap-3">
                    <button type="button" class="px-4 py-2 text-sm text-lf-secondary bg-lf-panel rounded-lg hover:bg-lf-neutral transition" onclick={onCancel} data-testid="tx-charges-modal-cancel">
                        {$t('common.cancel')}
                    </button>
                    <button
                        type="button"
                        class="px-4 py-2 text-sm text-lf-on-status rounded-lg transition flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed {mode === 'unlink' ? 'bg-lf-warning hover:bg-lf-warning-hover' : 'bg-lf-success hover:bg-lf-success-hover'}"
                        onclick={() => !loading && onConfirm?.()}
                        disabled={loading}
                        data-testid="tx-charges-modal-confirm"
                    >
                        {#if mode === 'unlink'}
                            <Unlink size={15} />
                        {:else}
                            <Link2 size={15} />
                        {/if}
                        <span>{loading ? $t('common.saving') || 'Saving...' : mode === 'unlink' ? $t('transactions.form.charges.unlink') || 'Unlink' : $t('transactions.chargesLink.confirm') || 'Link'}</span>
                    </button>
                </div>
            {:else}
                <div class="flex flex-col gap-2 sm:flex-row sm:justify-end sm:gap-3">
                    <button type="button" class="w-full sm:w-auto px-4 py-2 text-sm text-lf-secondary bg-lf-panel rounded-lg hover:bg-lf-neutral transition" onclick={onCancel} data-testid="tx-charges-modal-cancel">
                        {$t('common.cancel')}
                    </button>
                    <button
                        type="button"
                        class="w-full sm:w-auto px-4 py-2 text-sm text-lf-primary bg-lf-card border border-lf-input rounded-lg hover:bg-lf-hover transition disabled:opacity-50 disabled:cursor-not-allowed"
                        onclick={() => !loading && onChoose?.('keep')}
                        disabled={loading}
                        data-testid="tx-charges-modal-keep"
                    >
                        {$t('transactions.chargesDelete.keep') || 'Keep the charges'}
                    </button>
                    <button
                        type="button"
                        class="w-full sm:w-auto px-4 py-2 text-sm bg-lf-danger-solid hover:bg-lf-danger-hover text-lf-on-danger-solid rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
                        onclick={() => !loading && onChoose?.('all')}
                        disabled={loading}
                        data-testid="tx-charges-modal-all"
                    >
                        {$t('transactions.chargesDelete.all', {values: {n: allCount}}) || `Delete all (${allCount})`}
                    </button>
                </div>
            {/if}
        </div>
    </div>
</ModalBase>
