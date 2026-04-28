<!--
  PromotePairWizardModal.svelte — 3-step wizard to promote a DEPOSIT/WITHDRAWAL
  pair into TRANSFER or FX_CONVERSION.

  Replaces the legacy `TransferPromoteModal` (Part 4 §Step 9). The big
  difference vs the legacy modal: the user can **choose** the two transactions
  themselves, picking from three sources per slot:

  1. "In bulk modal" — when the wizard is opened FROM the bulk modal, lists
     the current `draftRows` filtered to {DEPOSIT, WITHDRAWAL}.
  2. "Saved transactions" — `GET /transactions?only_unlinked=true&types=…`
     (already on the backend); enforces BrokerUserAccess server-side.
  3. "Create new" — opens `TransactionFormModal` mode='create' as a stacked
     modal (zIndex 60). On save, the new transaction id populates the slot.

  Steps:
    Step 1: pick FROM (giver) and TO (receiver)
    Step 2: choose new_type (TRANSFER/FX_CONVERSION) — radios greyed-out per
            broker/currency rule
    Step 3: type-specific fields (TRANSFER: asset+quantity+cost_basis_override;
            FX_CONVERSION: summary + implied rate)

  Commit: `POST /transactions/transfers/promote`. On rolled_back=true the
  wizard stays open with a persistent banner.
-->
<script lang="ts">
    import {untrack} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import {ChevronLeft, ChevronRight, X, AlertTriangle, Plus} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import AssetSelect from '$lib/components/ui/select/AssetSelect.svelte';
    import TransactionFormModal from './TransactionFormModal.svelte';
    import {zodiosApi} from '$lib/api';
    import {ensureBrokersLoaded, getAllBrokers, brokerStoreVersion, type BrokerInfo} from '$lib/stores/brokerStore';
    import {saveWithRetry} from '$lib/utils/saveWithRetry';

    // =========================================================================
    // Types
    // =========================================================================

    export interface TXReadItem {
        id: number;
        broker_id: number;
        type: string;
        date: string;
        cash?: {code: string; amount: string} | null;
        related_transaction_id?: number | null;
    }

    /**
     * Bulk-context drafts as supplied by the parent BulkModal. Each entry must
     * already have an id (i.e. status === 'original' or already-committed).
     * Brand-new drafts (status === 'new') are NOT promotable since they don't
     * exist in the DB yet.
     */
    export interface BulkDraftLike {
        id?: number;
        broker_id: number;
        type: string;
        date: string;
        cash?: {code: string; amount: string} | null;
    }

    type SlotSource = 'bulk' | 'saved' | 'new';

    interface Props {
        open: boolean;
        /** Saved txs from the parent (mainRows) — pre-loaded. */
        savedTransactions?: TXReadItem[];
        /** Drafts of the bulk modal when this wizard was opened from there. */
        bulkContext?: BulkDraftLike[] | null;
        /** Pre-seed slots when the user already selected a pair on the page. */
        seedFrom?: TXReadItem | null;
        seedTo?: TXReadItem | null;
        onClose: () => void;
        onCommitted?: (resp: {new_from_tx_id?: number | null; new_to_tx_id?: number | null}) => void;
    }

    let {open, savedTransactions = [], bulkContext = null, seedFrom = null, seedTo = null, onClose, onCommitted}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let step = $state<1 | 2 | 3>(1);
    let fromTx = $state<TXReadItem | null>(null);
    let toTx = $state<TXReadItem | null>(null);
    let fromSource = $state<SlotSource>('saved');
    let toSource = $state<SlotSource>('saved');
    let newType = $state<'TRANSFER' | 'FX_CONVERSION'>('TRANSFER');
    let assetId = $state<number | null>(null);
    let quantity = $state<string>('');
    let costBasisOverride = $state<string>('');
    let committing = $state(false);
    let formError = $state<string | null>(null);

    // Search filters per slot.
    let fromSearch = $state('');
    let toSearch = $state('');

    // Stack-modal state for "Create new".
    let stackedFormOpen = $state(false);
    let stackedFormSlot = $state<'from' | 'to'>('from');
    let stackedFormForcedBroker = $state<number | null>(null);

    // Reset on open.
    $effect(() => {
        if (!open) return;
        const sf = seedFrom;
        const st = seedTo;
        const bulk = bulkContext;
        untrack(() => {
            step = 1;
            fromTx = sf;
            toTx = st;
            fromSource = bulk ? 'bulk' : 'saved';
            toSource = bulk ? 'bulk' : 'saved';
            assetId = null;
            quantity = '';
            costBasisOverride = '';
            formError = null;
            fromSearch = '';
            toSearch = '';
        });
        void ensureBrokersLoaded();
    });

    let brokers = $derived.by<BrokerInfo[]>(() => {
        void $brokerStoreVersion;
        return getAllBrokers();
    });

    function brokerName(id: number): string {
        return brokers.find((b) => b.id === id)?.name ?? `#${id}`;
    }

    // =========================================================================
    // Eligibility (Step 2 rules)
    // =========================================================================

    let sameBroker = $derived(!!fromTx && !!toTx && fromTx.broker_id === toTx.broker_id);
    let sameCurrency = $derived(!!fromTx?.cash && !!toTx?.cash && fromTx.cash.code === toTx.cash.code);
    let canTransfer = $derived(!!fromTx && !!toTx && !sameBroker && sameCurrency);
    let canFx = $derived(!!fromTx && !!toTx && sameBroker && !sameCurrency);

    let transferReason = $derived.by(() => {
        if (canTransfer) return $t('transactions.promote.eligibleTransfer');
        if (sameBroker && !sameCurrency) return $t('transactions.promote.reasonSameBroker');
        if (!sameBroker && !sameCurrency) return $t('transactions.promote.reasonBothDiffer');
        return $t('transactions.promote.reasonSameCurrencyAndBroker');
    });
    let fxReason = $derived.by(() => {
        if (canFx) return $t('transactions.promote.eligibleFx');
        if (!sameBroker && sameCurrency) return $t('transactions.promote.reasonDiffBrokers');
        if (!sameBroker && !sameCurrency) return $t('transactions.promote.reasonBothDiffer');
        return $t('transactions.promote.reasonSameCurrencyAndBroker');
    });

    // =========================================================================
    // Slot candidates per source
    // =========================================================================

    function filterByQuery(txs: TXReadItem[], q: string): TXReadItem[] {
        if (!q.trim()) return txs;
        const lc = q.toLowerCase();
        return txs.filter((tx) => {
            return (
                String(tx.id).includes(lc) ||
                tx.date.includes(lc) ||
                brokerName(tx.broker_id).toLowerCase().includes(lc) ||
                (tx.cash?.amount ?? '').includes(lc) ||
                (tx.cash?.code ?? '').toLowerCase().includes(lc)
            );
        });
    }

    /** Saved transactions usable as FROM (WITHDRAWAL) and TO (DEPOSIT). */
    let savedFromCandidates = $derived(savedTransactions.filter((tx) => tx.type === 'WITHDRAWAL' && tx.related_transaction_id == null));
    let savedToCandidates = $derived(savedTransactions.filter((tx) => tx.type === 'DEPOSIT' && tx.related_transaction_id == null));

    /** Bulk-modal drafts usable — only those that already have an id. */
    let bulkFromCandidates = $derived.by<TXReadItem[]>(() => {
        if (!bulkContext) return [];
        return bulkContext.filter((d) => d.id != null && d.type === 'WITHDRAWAL').map((d) => ({id: d.id as number, broker_id: d.broker_id, type: d.type, date: d.date, cash: d.cash}));
    });
    let bulkToCandidates = $derived.by<TXReadItem[]>(() => {
        if (!bulkContext) return [];
        return bulkContext.filter((d) => d.id != null && d.type === 'DEPOSIT').map((d) => ({id: d.id as number, broker_id: d.broker_id, type: d.type, date: d.date, cash: d.cash}));
    });

    // =========================================================================
    // Slot picker
    // =========================================================================

    function pickFrom(tx: TXReadItem) {
        fromTx = tx;
    }
    function pickTo(tx: TXReadItem) {
        toTx = tx;
    }

    function openCreateNew(slot: 'from' | 'to') {
        stackedFormSlot = slot;
        // If the other slot is already chosen, suggest its broker.
        if (slot === 'from') {
            stackedFormForcedBroker = toTx?.broker_id ?? null;
        } else {
            stackedFormForcedBroker = fromTx?.broker_id ?? null;
        }
        stackedFormOpen = true;
    }

    async function handleCreatedFromForm(resp: {transaction_id?: number | null}) {
        const newId = resp.transaction_id;
        if (!newId) return;
        // Fetch the just-created tx from the server (single-item ?ids=).
        try {
            const list = (await zodiosApi.query_transactions_api_v1_transactions_get({queries: {ids: [newId]}} as never)) as TXReadItem[];
            const created = list?.[0];
            if (!created) return;
            if (stackedFormSlot === 'from') fromTx = created;
            else toTx = created;
        } catch {
            // Best-effort; user can re-pick from "Saved" tab.
        }
    }

    // =========================================================================
    // Commit
    // =========================================================================

    async function commit() {
        if (!fromTx || !toTx || committing) return;
        committing = true;
        formError = null;
        try {
            const payload: Record<string, unknown> = {
                from_tx_id: fromTx.id,
                to_tx_id: toTx.id,
                new_type: newType,
            };
            if (newType === 'TRANSFER') {
                if (assetId != null) payload.asset_id = assetId;
                if (quantity.trim()) payload.quantity = quantity.trim();
                if (costBasisOverride.trim()) payload.cost_basis_override = costBasisOverride.trim();
            }
            const result = await saveWithRetry(() => zodiosApi.promote_transfer_api_v1_transactions_transfers_promote_post(payload as never), {fallback: $t('transactions.promote.failed'), toast: false});
            if (result.status === 'error') {
                formError = result.message;
                return;
            }
            const resp = result.data as {rolled_back?: boolean; errors?: string[]; new_from_tx_id?: number | null; new_to_tx_id?: number | null};
            if (resp.rolled_back) {
                formError = (resp.errors?.[0] ?? $t('transactions.promote.rolledBack')) as string;
                return;
            }
            onCommitted?.({new_from_tx_id: resp.new_from_tx_id, new_to_tx_id: resp.new_to_tx_id});
            onClose();
        } finally {
            committing = false;
        }
    }

    // =========================================================================
    // Step navigation
    // =========================================================================

    let canGoNextStep1 = $derived(!!fromTx && !!toTx);
    let canGoNextStep2 = $derived((newType === 'TRANSFER' && canTransfer) || (newType === 'FX_CONVERSION' && canFx));

    function next() {
        if (step === 1 && canGoNextStep1) {
            // Auto-select default new_type when entering step 2.
            if (canTransfer) newType = 'TRANSFER';
            else if (canFx) newType = 'FX_CONVERSION';
            step = 2;
        } else if (step === 2 && canGoNextStep2) {
            step = 3;
        }
    }
    function back() {
        if (step === 3) step = 2;
        else if (step === 2) step = 1;
    }

    function setNewType(v: 'TRANSFER' | 'FX_CONVERSION') {
        newType = v;
    }
    function onNewTypeChange(e: Event) {
        setNewType((e.currentTarget as HTMLInputElement).value as 'TRANSFER' | 'FX_CONVERSION');
    }
    function onQuantityInput(e: Event) {
        quantity = (e.currentTarget as HTMLInputElement).value;
    }
    function onCostBasisInput(e: Event) {
        costBasisOverride = (e.currentTarget as HTMLInputElement).value;
    }
</script>

<ModalBase {open} maxWidth="3xl" onRequestClose={onClose} testId="tx-promote-wizard">
    <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <h2 class="text-base font-semibold text-gray-800 dark:text-gray-100" data-testid="tx-promote-title">
            ⚡ {$t('transactions.promote.title')} — {$t('transactions.promote.stepN', {values: {n: step, total: 3}})}
        </h2>
        <button class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700" onclick={onClose} data-testid="tx-promote-close" aria-label="Close">
            <X size={18} />
        </button>
    </div>

    {#if formError}
        <div class="p-3 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800" data-testid="tx-promote-error">
            <p class="text-xs text-red-800 dark:text-red-200 font-semibold mb-1">⛔ {$t('transactions.promote.rolledBackTitle')}</p>
            <p class="text-xs text-red-700 dark:text-red-300">{formError}</p>
        </div>
    {/if}

    <div class="p-4 max-h-[70vh] overflow-y-auto" data-testid="tx-promote-body">
        <!-- ========== STEP 1: pair picker ========== -->
        {#if step === 1}
            <div class="space-y-4" data-testid="tx-promote-step1">
                <!-- FROM slot -->
                <fieldset class="border border-gray-200 dark:border-gray-700 rounded p-3">
                    <legend class="text-xs font-semibold text-gray-700 dark:text-gray-300 px-1">{$t('transactions.promote.fromSlot')}</legend>
                    <div class="flex flex-wrap gap-3 text-xs mb-2">
                        {#if bulkContext}
                            <label><input type="radio" bind:group={fromSource} value="bulk" data-testid="tx-promote-slot-from-source-bulk" /> {$t('transactions.promote.sourceBulk')}</label>
                        {/if}
                        <label><input type="radio" bind:group={fromSource} value="saved" data-testid="tx-promote-slot-from-source-saved" /> {$t('transactions.promote.sourceSaved')}</label>
                        <label><input type="radio" bind:group={fromSource} value="new" data-testid="tx-promote-slot-from-source-new" /> {$t('transactions.promote.sourceNew')}</label>
                    </div>
                    {#if fromSource === 'new'}
                        <button type="button" class="inline-flex items-center gap-1 px-2 py-1 text-xs rounded border border-dashed border-libre-green text-libre-green hover:bg-libre-green/10" onclick={() => openCreateNew('from')} data-testid="tx-promote-create-new-from">
                            <Plus size={12} /> {$t('transactions.promote.createNew')}
                        </button>
                        {#if fromTx}
                            <p class="mt-2 text-xs text-emerald-600">✓ #{fromTx.id} {fromTx.type} {brokerName(fromTx.broker_id)} {fromTx.cash?.amount ?? ''} {fromTx.cash?.code ?? ''}</p>
                        {/if}
                    {:else}
                        {@const candidates = fromSource === 'bulk' ? bulkFromCandidates : savedFromCandidates}
                        {@const filtered = filterByQuery(candidates, fromSearch)}
                        <input type="text" class="w-full px-2 py-1 text-xs bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded mb-2" placeholder={$t('transactions.promote.searchPlaceholder')} bind:value={fromSearch} data-testid="tx-promote-from-search" />
                        <ul class="max-h-40 overflow-y-auto text-xs space-y-0.5" data-testid="tx-promote-from-list">
                            {#each filtered as tx}
                                <li>
                                    <button type="button" class="w-full text-left px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700" class:bg-libre-green={fromTx?.id === tx.id} class:text-white={fromTx?.id === tx.id} onclick={() => pickFrom(tx)}>
                                        #{tx.id} · {tx.type} · {brokerName(tx.broker_id)} · {tx.date} · {tx.cash?.amount ?? '—'} {tx.cash?.code ?? ''}
                                    </button>
                                </li>
                            {:else}
                                <li class="text-gray-400 italic px-2 py-1">{$t('transactions.promote.noCandidates')}</li>
                            {/each}
                        </ul>
                    {/if}
                </fieldset>

                <!-- TO slot -->
                <fieldset class="border border-gray-200 dark:border-gray-700 rounded p-3">
                    <legend class="text-xs font-semibold text-gray-700 dark:text-gray-300 px-1">{$t('transactions.promote.toSlot')}</legend>
                    <div class="flex flex-wrap gap-3 text-xs mb-2">
                        {#if bulkContext}
                            <label><input type="radio" bind:group={toSource} value="bulk" data-testid="tx-promote-slot-to-source-bulk" /> {$t('transactions.promote.sourceBulk')}</label>
                        {/if}
                        <label><input type="radio" bind:group={toSource} value="saved" data-testid="tx-promote-slot-to-source-saved" /> {$t('transactions.promote.sourceSaved')}</label>
                        <label><input type="radio" bind:group={toSource} value="new" data-testid="tx-promote-slot-to-source-new" /> {$t('transactions.promote.sourceNew')}</label>
                    </div>
                    {#if toSource === 'new'}
                        <button type="button" class="inline-flex items-center gap-1 px-2 py-1 text-xs rounded border border-dashed border-libre-green text-libre-green hover:bg-libre-green/10" onclick={() => openCreateNew('to')} data-testid="tx-promote-create-new-to">
                            <Plus size={12} /> {$t('transactions.promote.createNew')}
                        </button>
                        {#if toTx}
                            <p class="mt-2 text-xs text-emerald-600">✓ #{toTx.id} {toTx.type} {brokerName(toTx.broker_id)} {toTx.cash?.amount ?? ''} {toTx.cash?.code ?? ''}</p>
                        {/if}
                    {:else}
                        {@const candidates = toSource === 'bulk' ? bulkToCandidates : savedToCandidates}
                        {@const filtered = filterByQuery(candidates, toSearch)}
                        <input type="text" class="w-full px-2 py-1 text-xs bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded mb-2" placeholder={$t('transactions.promote.searchPlaceholder')} bind:value={toSearch} data-testid="tx-promote-to-search" />
                        <ul class="max-h-40 overflow-y-auto text-xs space-y-0.5" data-testid="tx-promote-to-list">
                            {#each filtered as tx}
                                <li>
                                    <button type="button" class="w-full text-left px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700" class:bg-libre-green={toTx?.id === tx.id} class:text-white={toTx?.id === tx.id} onclick={() => pickTo(tx)}>
                                        #{tx.id} · {tx.type} · {brokerName(tx.broker_id)} · {tx.date} · {tx.cash?.amount ?? '—'} {tx.cash?.code ?? ''}
                                    </button>
                                </li>
                            {:else}
                                <li class="text-gray-400 italic px-2 py-1">{$t('transactions.promote.noCandidates')}</li>
                            {/each}
                        </ul>
                    {/if}
                </fieldset>

                <p class="text-[10px] text-gray-400 italic">⚠ {$t('transactions.promote.brokerAccessHint')}</p>
            </div>
        {/if}

        <!-- ========== STEP 2: choose new_type ========== -->
        {#if step === 2}
            <div class="space-y-3" data-testid="tx-promote-step2">
                <p class="text-xs text-gray-600 dark:text-gray-400">{$t('transactions.promote.selectedPair')}</p>
                {#if fromTx}
                    <p class="text-xs">FROM #{fromTx.id} {fromTx.type} · {brokerName(fromTx.broker_id)} · {fromTx.cash?.amount ?? '—'} {fromTx.cash?.code ?? ''}</p>
                {/if}
                {#if toTx}
                    <p class="text-xs">TO #{toTx.id} {toTx.type} · {brokerName(toTx.broker_id)} · {toTx.cash?.amount ?? '—'} {toTx.cash?.code ?? ''}</p>
                {/if}
                <hr class="border-gray-200 dark:border-gray-700" />
                <p class="text-xs font-semibold">{$t('transactions.promote.promoteTo')}</p>
                <label class="flex items-start gap-2 text-xs" class:opacity-50={!canTransfer}>
                    <input type="radio" name="new-type" value="TRANSFER" checked={newType === 'TRANSFER'} disabled={!canTransfer} onchange={onNewTypeChange} data-testid="tx-promote-type-transfer" />
                    <span>
                        🔄 <strong>TRANSFER</strong> — <span class="text-gray-500">{transferReason}</span>
                    </span>
                </label>
                <label class="flex items-start gap-2 text-xs" class:opacity-50={!canFx}>
                    <input type="radio" name="new-type" value="FX_CONVERSION" checked={newType === 'FX_CONVERSION'} disabled={!canFx} onchange={onNewTypeChange} data-testid="tx-promote-type-fx" />
                    <span>
                        💱 <strong>FX_CONVERSION</strong> — <span class="text-gray-500">{fxReason}</span>
                    </span>
                </label>
            </div>
        {/if}

        <!-- ========== STEP 3: type-specific fields ========== -->
        {#if step === 3}
            <div class="space-y-3" data-testid="tx-promote-step3">
                {#if newType === 'TRANSFER'}
                    <div class="flex flex-col gap-1">
                        <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.promote.assetMoved')} *</span>
                        <AssetSelect bind:value={assetId} testid="tx-promote-asset" />
                    </div>
                    <label class="flex flex-col gap-1">
                        <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.table.quantity')} *</span>
                        <input type="text" inputmode="decimal" class="px-2 py-1.5 text-xs bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded" value={quantity} oninput={onQuantityInput} data-testid="tx-promote-quantity" />
                    </label>
                    <details class="border border-gray-200 dark:border-gray-700 rounded">
                        <summary class="text-xs font-semibold text-gray-700 dark:text-gray-300 px-3 py-2 cursor-pointer">{$t('transactions.form.sectionAdvanced')}</summary>
                        <div class="p-3">
                            <label class="flex flex-col gap-1">
                                <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.form.costBasis')}</span>
                                <input type="text" inputmode="decimal" class="px-2 py-1.5 text-xs bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded" placeholder="auto" value={costBasisOverride} oninput={onCostBasisInput} data-testid="tx-promote-cost-basis" />
                            </label>
                        </div>
                    </details>
                {:else}
                    <p class="text-xs text-gray-600 dark:text-gray-400">{$t('transactions.promote.fxNoFields')}</p>
                    {#if fromTx?.cash && toTx?.cash}
                        {@const fromAmt = parseFloat(fromTx.cash.amount)}
                        {@const toAmt = parseFloat(toTx.cash.amount)}
                        {@const rate = fromAmt && toAmt ? Math.abs(toAmt / fromAmt) : null}
                        {#if rate}
                            <p class="text-xs">{$t('transactions.promote.impliedRate')}: 1 {fromTx.cash.code} = {rate.toFixed(4)} {toTx.cash.code}</p>
                        {/if}
                    {/if}
                {/if}
                <div class="flex items-start gap-2 p-3 bg-amber-50 dark:bg-amber-900/20 rounded">
                    <AlertTriangle class="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" size={14} />
                    <p class="text-[11px] text-amber-800 dark:text-amber-200">{$t('transactions.promote.atomicWarning')}</p>
                </div>
            </div>
        {/if}
    </div>

    <div class="flex items-center justify-end gap-2 p-3 border-t border-gray-200 dark:border-gray-700">
        {#if step > 1}
            <button type="button" class="inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700" onclick={back} data-testid="tx-promote-back">
                <ChevronLeft size={12} /> {$t('common.back')}
            </button>
        {/if}
        <button type="button" class="px-4 py-1.5 text-xs rounded text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600" onclick={onClose} data-testid="tx-promote-cancel">{$t('common.cancel')}</button>
        {#if step < 3}
            <button type="button" class="inline-flex items-center gap-1 px-4 py-1.5 text-xs rounded text-white bg-libre-green hover:bg-libre-green/90 disabled:opacity-50" disabled={(step === 1 && !canGoNextStep1) || (step === 2 && !canGoNextStep2)} onclick={next} data-testid="tx-promote-next">
                {$t('common.next')} <ChevronRight size={12} />
            </button>
        {:else}
            <button type="button" class="px-4 py-1.5 text-xs rounded text-white bg-libre-green hover:bg-libre-green/90 disabled:opacity-50" disabled={committing || (newType === 'TRANSFER' && (assetId == null || !quantity.trim()))} onclick={commit} data-testid="tx-promote-commit">
                {committing ? $t('common.saving') : $t('transactions.promote.commit')}
            </button>
        {/if}
    </div>
</ModalBase>

<!-- Stack-modal: Create new transaction (zIndex 60 keeps it above the wizard) -->
<TransactionFormModal
    open={stackedFormOpen}
    mode="create"
    forcedBroker={stackedFormForcedBroker}
    onClose={() => (stackedFormOpen = false)}
    onCommitted={(resp) => {
        stackedFormOpen = false;
        void handleCreatedFromForm(resp);
    }}
/>

