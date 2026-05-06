<!--
  TransactionPickerModal — Select existing DB transactions to add to BulkModal.

  Reuses TransactionsTable with pickerMode=true. Receives `mainRows` from parent
  (zero additional fetch). Filters out IDs already in the BulkModal via excludeIds.

  Plan B — Phase 07, Step 8.
  Svelte 5 runes, dark mode, data-testid.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Search, X, Plus} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import TransactionsTable from './TransactionsTable.svelte';
    import type {BrokerLike} from '$lib/utils/brokerColors';

    interface TXReadItem {
        id: number;
        broker_id: number;
        asset_id?: number | null;
        type: string;
        date: string;
        quantity: string;
        cash?: {code: string; amount: string} | null;
        related_transaction_id?: number | null;
        tags?: string[] | null;
        description?: string | null;
        cost_basis_override?: string | null;
        asset_event_id?: number | null;
        created_at?: string;
        updated_at?: string;
    }

    interface Props {
        open: boolean;
        mainRows: TXReadItem[];
        partnerRows: TXReadItem[];
        brokers: BrokerLike[];
        /** IDs already in BulkModal — hidden from picker */
        excludeIds: Set<number>;
        onAdd: (rows: TXReadItem[]) => void;
        onClose: () => void;
    }

    let {
        open = $bindable(false),
        mainRows = [],
        partnerRows = [],
        brokers = [],
        excludeIds = new Set(),
        onAdd,
        onClose,
    }: Props = $props();

    let selectedRows = $state<TXReadItem[]>([]);

    /** Filtered rows: exclude IDs already in BulkModal */
    let filteredMain = $derived(mainRows.filter((r) => !excludeIds.has(r.id)));
    let filteredPartners = $derived(partnerRows.filter((r) => !excludeIds.has(r.id)));

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
                const partner =
                    mainRows.find((r) => r.id === row.related_transaction_id) ??
                    partnerRows.find((r) => r.id === row.related_transaction_id);
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
                mainRows={filteredMain as any[]}
                partnerRows={filteredPartners as any[]}
                {brokers}
                eventTooltipMap={emptyEventMap}
                pageSize={20}
                onSelectionChange={handleSelectionChange}
            />
        </div>

        <!-- Info + Footer -->
        <div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between gap-4">
            <p class="text-xs text-gray-500 dark:text-gray-400">
                {$t('transactions.picker.pairedNote') || 'Selecting a paired transaction auto-adds its partner.'}
            </p>
            <div class="flex gap-3">
                <button
                    class="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition"
                    onclick={handleClose}
                    data-testid="tx-picker-cancel"
                >
                    {$t('common.cancel') || 'Cancel'}
                </button>
                <button
                    class="px-4 py-2 text-sm text-white bg-libre-green rounded-lg hover:bg-libre-green/90 transition flex items-center gap-1.5 disabled:opacity-50"
                    disabled={selectedRows.length === 0}
                    onclick={handleAdd}
                    data-testid="tx-picker-add"
                >
                    <Plus size={15} />
                    {$t('transactions.picker.addN', {values: {n: selectedRows.length}}) || `Add ${selectedRows.length} selected`}
                </button>
            </div>
        </div>
    </div>
</ModalBase>

