<!--
  TransactionPickerModal — Select existing DB transactions to add to BulkModal.

  Reuses TransactionsTable with pickerMode=true. Reads all transactions from
  txStore (single source of truth) instead of receiving mainRows/partnerRows
  via props. Filters out IDs already in the BulkModal via excludeIds.

  Plan B — Phase 07, Step 8.
  Plan C — txStore migration (Step 2).
  Svelte 5 runes, dark mode, data-testid.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Search, X, Plus} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import TransactionsTable from './TransactionsTable.svelte';
    import type {BrokerLike} from '$lib/utils/brokerColors';
    import {canEditBroker, getBrokerRole, getBrokerInfo, getAllBrokers} from '$lib/stores/brokerStore';
    import {getBrokerIconUrlById} from '$lib/utils/brokerHelpers';
    import {getRoleSvgHtml} from '$lib/utils/brokerRoleHelpers';
    import {txStoreGetAll, txStoreGet, type TXReadItem} from '$lib/stores/txStore.svelte';

    interface Props {
        open: boolean;
        /** IDs already in BulkModal — hidden from picker */
        excludeIds: Set<number>;
        onAdd: (rows: TXReadItem[]) => void;
        onClose: () => void;
    }

    let {
        open = $bindable(false),
        excludeIds = new Set(),
        onAdd,
        onClose,
    }: Props = $props();

    let selectedRows = $state<TXReadItem[]>([]);
    let pickerPage = $state(1);
    let pickerPageSize = $state(20);

    /** Read all transactions from txStore — reactive via Svelte 5 fine-grained tracking. */
    let allRows = $derived(txStoreGetAll());

    /** Brokers from store (for TransactionsTable compatibility). */
    let brokers = $derived(getAllBrokers() as BrokerLike[]);

    /** Filtered rows: exclude IDs already in BulkModal */
    let filteredMain = $derived(allRows.filter((r) => !excludeIds.has(r.id)));
    /** Partners not needed separately since txStore merges main+partners. */
    let filteredPartners = $derived<TXReadItem[]>([]);

    /** IDs of rows on non-editable brokers (VIEWER / no role). */
    let disabledIds = $derived.by(() => {
        const disabled = new Set<number>();
        const all = [...filteredMain, ...filteredPartners];
        const lookup = new Map(all.map((r) => [r.id, r]));
        for (const r of all) {
            if (disabled.has(r.id)) continue;
            if (r.related_transaction_id != null) {
                // Paired: both halves disabled if either broker is non-editable
                const partner = lookup.get(r.related_transaction_id);
                const partnerBrokerId = partner?.broker_id;
                if (!canEditBroker(r.broker_id) || (partnerBrokerId != null && !canEditBroker(partnerBrokerId))) {
                    disabled.add(r.id);
                    if (partner) disabled.add(partner.id);
                }
            } else {
                // Standalone: disabled if broker is VIEWER or null role
                if (!canEditBroker(r.broker_id)) {
                    disabled.add(r.id);
                }
            }
        }
        return disabled;
    });

    /** Tooltip for disabled rows — shows broker icon + name + role SVG + required role. */
    function disabledTooltipFn(brokerId: number): string {
        const broker = brokers.find((b) => b.id === brokerId);
        const brokerFromStore = getBrokerInfo(brokerId);
        const bName = broker?.name ?? brokerFromStore?.name ?? `#${brokerId}`;
        const iconUrl = getBrokerIconUrlById(brokerId, brokers);
        const currentRole = getBrokerRole(brokerId);
        const roleLabelCurrent = currentRole ? currentRole.charAt(0) + currentRole.slice(1).toLowerCase() : 'None';
        const brokerIconHtml = iconUrl
            ? `<img src="${iconUrl}" width="14" height="14" style="display:inline;vertical-align:middle;border-radius:3px;margin-right:3px" alt="" onerror="this.style.display='none'">`
            : '';
        const currentRoleSvg = getRoleSvgHtml(currentRole);
        const requiredRoleSvg = getRoleSvgHtml('EDITOR');
        return `${brokerIconHtml}<strong>${bName}</strong> ${currentRoleSvg} ${roleLabelCurrent}<br>${$t('transactions.picker.requiredRole') || 'required'} ${requiredRoleSvg} Editor`;
    }

    /** TableRef for dblclick toggle selection. */
    let tableRef: TransactionsTable | undefined = $state(undefined);

    /** Double-click on selectable row → toggle selection via DataTable internal state. */
    function handleRowDoubleClick(row: TXReadItem) {
        if (disabledIds.has(row.id)) return;
        tableRef?.toggleSelectionByTxId(row.id);
    }

    /** Empty event tooltip map — picker doesn't need event tooltips */
    let emptyEventMap = $derived(new Map());

    function handleSelectionChange(rows: TXReadItem[]) {
        selectedRows = rows;
    }

    function handleAdd() {
        if (selectedRows.length === 0) return;

        // Auto-include partners of selected paired transactions
        const toAdd: TXReadItem[] = [...selectedRows];
        const addedIds = new Set(toAdd.map((r) => r.id));

        for (const row of selectedRows) {
            if (row.related_transaction_id != null && !addedIds.has(row.related_transaction_id)) {
                const partner = txStoreGet(row.related_transaction_id);
                if (partner && !excludeIds.has(partner.id)) {
                    toAdd.push(partner);
                    addedIds.add(partner.id);
                }
            }
        }

        onAdd(toAdd);
        selectedRows = [];
    }

    function handleClose() {
        selectedRows = [];
        onClose();
    }
</script>

<ModalBase {open} maxWidth="5xl" onRequestClose={handleClose} testId="tx-picker-modal">
    <div class="flex flex-col max-h-[80vh]" data-testid="tx-picker-content">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 class="text-lg font-semibold text-gray-800 dark:text-gray-100 flex items-center gap-2">
                <Search size={20} />
                {$t('transactions.picker.title') || 'Select transactions to add'}
            </h3>
            <button class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" onclick={handleClose} data-testid="tx-picker-close">
                <X size={20} />
            </button>
        </div>

        <!-- Table -->
        <div class="flex-1 overflow-auto px-6 py-4">
            <TransactionsTable
                bind:this={tableRef}
                mainRows={filteredMain as any[]}
                partnerRows={filteredPartners as any[]}
                {brokers}
                eventTooltipMap={emptyEventMap}
                currentPage={pickerPage}
                pageSize={pickerPageSize}
                onPageChange={(p) => (pickerPage = p)}
                onPageSizeChange={(s) => { pickerPageSize = s; pickerPage = 1; }}
                onSelectionChange={handleSelectionChange}
                {disabledIds}
                disabledRowTooltipFn={disabledTooltipFn}
                onRowDoubleClickOverride={handleRowDoubleClick}
                enableTouchSelection={true}
                hideActions={true}
            />
        </div>

        <!-- Info + Footer -->
        <div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between gap-4">
            <p class="text-xs text-gray-500 dark:text-gray-400">
                {$t('transactions.picker.pairedNote') || 'Selecting a paired transaction auto-adds its partner.'}
            </p>
            <div class="flex gap-3">
                <button
                    class="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition inline-flex items-center gap-1.5"
                    onclick={handleClose}
                    data-testid="tx-picker-cancel"
                    title={$t('common.cancel') || 'Cancel'}
                >
                    <X size={15} />
                    <span class="hidden sm:inline">{$t('common.cancel') || 'Cancel'}</span>
                </button>
                <button
                    class="px-4 py-2 text-sm text-white bg-libre-green rounded-lg hover:bg-libre-green/90 transition flex items-center gap-1.5 disabled:opacity-50"
                    disabled={selectedRows.length === 0}
                    onclick={handleAdd}
                    data-testid="tx-picker-add"
                    title={$t('transactions.picker.addN', {values: {n: selectedRows.length}}) || `Add ${selectedRows.length} selected`}
                >
                    <Plus size={15} />
                    <span class="hidden sm:inline">{$t('transactions.picker.addN', {values: {n: selectedRows.length}}) || `Add ${selectedRows.length} selected`}</span>
                </button>
            </div>
        </div>
    </div>
</ModalBase>

