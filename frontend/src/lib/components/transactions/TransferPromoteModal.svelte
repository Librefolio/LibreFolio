<!--
  TransferPromoteModal.svelte — promote a DEPOSIT/WITHDRAWAL pair into TRANSFER
  or FX_CONVERSION.

  Step 9 of plan-phase07-transaction-Part4.prompt.md.

  Trigger (from `+page.svelte` SelectionBar): exactly 2 selected rows that
  match `1 DEPOSIT + 1 WITHDRAWAL` with `related_transaction_id == null` on
  both. The caller already validated the trigger preconditions; this modal
  guides the type choice and (for TRANSFER) the asset + quantity.

  Pattern: Svelte 5 runes, dark mode, `data-testid` everywhere.
  Backend: `POST /transactions/transfers/promote`.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {AlertTriangle, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import AssetSelect from '$lib/components/ui/select/AssetSelect.svelte';
    import {zodiosApi} from '$lib/api';
    import type {BrokerLike} from '$lib/utils/brokerColors';

    // =========================================================================
    // Types
    // =========================================================================

    export interface TXReadItem {
        id: number;
        broker_id: number;
        type: string;
        date: string;
        cash?: {code: string; amount: string} | null;
    }

    interface Props {
        open: boolean;
        rowA: TXReadItem | null;
        rowB: TXReadItem | null;
        brokers: BrokerLike[];
        onClose: () => void;
        onCommitted?: (resp: {new_from_tx_id?: number | null; new_to_tx_id?: number | null}) => void;
    }

    let {open, rowA, rowB, brokers, onClose, onCommitted}: Props = $props();

    // =========================================================================
    // Pair analysis
    // =========================================================================

    /** "From" = WITHDRAWAL (cash out). "To" = DEPOSIT (cash in). */
    let fromTx = $derived.by<TXReadItem | null>(() => {
        if (!rowA || !rowB) return null;
        if (rowA.type === 'WITHDRAWAL') return rowA;
        if (rowB.type === 'WITHDRAWAL') return rowB;
        return rowA;
    });
    let toTx = $derived.by<TXReadItem | null>(() => {
        if (!rowA || !rowB) return null;
        if (fromTx?.id === rowA.id) return rowB;
        return rowA;
    });

    let sameBroker = $derived(!!fromTx && !!toTx && fromTx.broker_id === toTx.broker_id);
    let sameCurrency = $derived(!!fromTx?.cash && !!toTx?.cash && fromTx.cash.code === toTx.cash.code);

    /** TRANSFER eligible: distinct brokers + same currency. */
    let canTransfer = $derived(!!fromTx && !!toTx && !sameBroker && sameCurrency);
    /** FX_CONVERSION eligible: same broker + distinct currencies. */
    let canFx = $derived(!!fromTx && !!toTx && sameBroker && !sameCurrency);

    // =========================================================================
    // State
    // =========================================================================

    let step = $state<1 | 2>(1);
    let newType = $state<'TRANSFER' | 'FX_CONVERSION'>('TRANSFER');
    let assetId = $state<number | null>(null);
    let quantity = $state<string>('');
    let costBasisOverride = $state<string>('');
    let committing = $state(false);
    let rolledBack = $state<{errors: string[]} | null>(null);

    $effect(() => {
        if (!open) return;
        // Pick the eligible default; prefer TRANSFER when both possible (rare).
        if (canTransfer) newType = 'TRANSFER';
        else if (canFx) newType = 'FX_CONVERSION';
        step = 1;
        assetId = null;
        quantity = '';
        costBasisOverride = '';
        rolledBack = null;
    });

    // =========================================================================
    // Helpers
    // =========================================================================

    function brokerName(id: number): string {
        return brokers.find((b) => b.id === id)?.name ?? `#${id}`;
    }

    function fmtCash(tx: TXReadItem | null): string {
        if (!tx?.cash) return '—';
        const n = Number(tx.cash.amount);
        if (!Number.isFinite(n)) return tx.cash.amount;
        const sign = n > 0 ? '+' : n < 0 ? '−' : '';
        const abs = Math.abs(n).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
        return `${sign}${abs} ${tx.cash.code}`;
    }

    function impliedRate(): string | null {
        if (!fromTx?.cash || !toTx?.cash) return null;
        const out = Math.abs(Number(fromTx.cash.amount));
        const into = Math.abs(Number(toTx.cash.amount));
        if (!out || !into) return null;
        const rate = into / out;
        return `1 ${fromTx.cash.code} = ${rate.toFixed(4)} ${toTx.cash.code}`;
    }

    let promoteDisabled = $derived(committing || (newType === 'TRANSFER' && (assetId == null || !quantity || quantity === '0')));

    // =========================================================================
    // Commit
    // =========================================================================

    async function commit() {
        if (!fromTx || !toTx) return;
        committing = true;
        rolledBack = null;
        try {
            const body: Record<string, unknown> = {
                from_tx_id: fromTx.id,
                to_tx_id: toTx.id,
                new_type: newType,
            };
            if (newType === 'TRANSFER') {
                body.asset_id = assetId;
                body.quantity = quantity;
                if (costBasisOverride) body.cost_basis_override = costBasisOverride;
            }
            const res = (await zodiosApi.promote_transfer_api_v1_transactions_transfers_promote_post(body as never)) as {
                rolled_back: boolean;
                errors?: string[];
                new_from_tx_id?: number | null;
                new_to_tx_id?: number | null;
            };
            if (res.rolled_back) {
                rolledBack = {errors: res.errors ?? []};
            } else {
                onCommitted?.({new_from_tx_id: res.new_from_tx_id, new_to_tx_id: res.new_to_tx_id});
                onClose();
            }
        } catch (e) {
            rolledBack = {errors: [e instanceof Error ? e.message : String(e)]};
        } finally {
            committing = false;
        }
    }
</script>

<ModalBase {open} maxWidth="2xl" onRequestClose={onClose} testId="tx-promote-modal">
    <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <h2 class="text-base font-semibold text-gray-800 dark:text-gray-100" data-testid="tx-promote-title">
            ⚡ {step === 1 ? 'Promote cash pair' : `Promote → ${newType === 'TRANSFER' ? '🔄 TRANSFER' : '💱 FX_CONVERSION'}`}
        </h2>
        <button class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700" onclick={onClose} data-testid="tx-promote-close" aria-label="Close">
            <X size={18} />
        </button>
    </div>

    <div class="p-4 space-y-4">
        <!-- Pair summary -->
        <div class="text-xs space-y-1 bg-gray-50 dark:bg-gray-800/60 p-3 rounded border border-gray-200 dark:border-gray-700" data-testid="tx-promote-pair">
            <div>
                <strong>From</strong>: {brokerName(fromTx?.broker_id ?? 0)} #{fromTx?.id} ({fromTx?.type}) · {fromTx?.date} · {fmtCash(fromTx)}
            </div>
            <div>
                <strong>To</strong>: {brokerName(toTx?.broker_id ?? 0)} #{toTx?.id} ({toTx?.type}) · {toTx?.date} · {fmtCash(toTx)}
            </div>
        </div>

        {#if step === 1}
            <div class="space-y-2 text-xs">
                <p class="text-gray-700 dark:text-gray-200 font-medium">Promote to:</p>
                <label class="flex items-start gap-2 p-2 rounded border border-transparent {canTransfer ? 'cursor-pointer hover:border-libre-green' : 'opacity-50 cursor-not-allowed'}">
                    <input type="radio" name="tx-promote-type" disabled={!canTransfer} checked={newType === 'TRANSFER'} onchange={() => (newType = 'TRANSFER')} data-testid="tx-promote-type-TRANSFER" />
                    <div>
                        <div class="font-medium">🔄 TRANSFER</div>
                        <div class="text-gray-500">Same currency, different brokers (asset move).</div>
                        {#if !canTransfer}
                            <div class="text-amber-600 dark:text-amber-400 text-[10px] mt-1">
                                Greyed out: {sameBroker ? 'brokers are equal' : ''}
                                {!sameCurrency ? '· currencies differ' : ''}
                            </div>
                        {/if}
                    </div>
                </label>
                <label class="flex items-start gap-2 p-2 rounded border border-transparent {canFx ? 'cursor-pointer hover:border-libre-green' : 'opacity-50 cursor-not-allowed'}">
                    <input type="radio" name="tx-promote-type" disabled={!canFx} checked={newType === 'FX_CONVERSION'} onchange={() => (newType = 'FX_CONVERSION')} data-testid="tx-promote-type-FX_CONVERSION" />
                    <div>
                        <div class="font-medium">💱 FX_CONVERSION</div>
                        <div class="text-gray-500">Same broker, different currencies (currency exchange).</div>
                        {#if !canFx}
                            <div class="text-amber-600 dark:text-amber-400 text-[10px] mt-1">
                                Greyed out: {!sameBroker ? 'brokers differ' : ''}
                                {sameCurrency ? '· currencies are equal' : ''}
                            </div>
                        {/if}
                    </div>
                </label>
            </div>
        {:else if newType === 'TRANSFER'}
            <div class="space-y-3 text-xs">
                <div class="flex items-center gap-3">
                    <span class="w-32 text-gray-700 dark:text-gray-200">Asset moved <span class="text-red-500">*</span></span>
                    <div class="flex-1">
                        <AssetSelect bind:value={assetId} testid="tx-promote-asset" placeholder="Select asset…" compact={true} />
                    </div>
                </div>
                <div class="flex items-center gap-3">
                    <span class="w-32 text-gray-700 dark:text-gray-200">Quantity <span class="text-red-500">*</span></span>
                    <input type="text" bind:value={quantity} placeholder="0.000" class="flex-1 px-2 py-1 border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-800" data-testid="tx-promote-quantity" />
                </div>
                <details class="text-xs">
                    <summary class="cursor-pointer text-gray-600 dark:text-gray-300">Advanced</summary>
                    <div class="flex items-center gap-3 mt-2 ml-3">
                        <span class="w-28 text-gray-700 dark:text-gray-200">Cost basis override</span>
                        <input type="text" bind:value={costBasisOverride} placeholder="auto" class="flex-1 px-2 py-1 border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-800" data-testid="tx-promote-cost-basis" />
                    </div>
                </details>
            </div>
        {:else}
            <div class="space-y-2 text-xs" data-testid="tx-promote-fx-summary">
                <p class="text-gray-700 dark:text-gray-200">Same broker ({brokerName(fromTx?.broker_id ?? 0)}), distinct currencies — auto-detected.</p>
                {#if impliedRate()}
                    <p class="text-gray-600 dark:text-gray-300">Implied rate: <span class="font-mono">{impliedRate()}</span></p>
                {/if}
                <p class="text-gray-500">No additional fields required.</p>
            </div>
        {/if}

        <div class="text-[11px] text-amber-700 dark:text-amber-400 flex items-start gap-2 p-2 rounded bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
            <AlertTriangle size={14} class="shrink-0 mt-0.5" />
            <span>This will DELETE #{fromTx?.id}/#{toTx?.id} and CREATE 2 new linked rows atomically. On rollback nothing is changed.</span>
        </div>

        {#if rolledBack}
            <div class="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-xs text-red-800 dark:text-red-200" data-testid="tx-promote-rollback">
                <strong>⛔ Promote rolled back — nothing was changed.</strong>
                <ul class="mt-1 ml-5 list-disc">
                    {#each rolledBack.errors as err}
                        <li>{err}</li>
                    {/each}
                </ul>
            </div>
        {/if}
    </div>

    <div class="flex items-center justify-end gap-2 p-3 border-t border-gray-200 dark:border-gray-700">
        {#if step === 2}
            <button class="px-3 py-1.5 text-xs rounded text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700" onclick={() => (step = 1)} data-testid="tx-promote-back">◂ Back</button>
        {/if}
        <button class="px-4 py-1.5 text-xs rounded text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600" onclick={onClose} data-testid="tx-promote-cancel">Cancel</button>
        {#if step === 1}
            <button class="px-4 py-1.5 text-xs rounded text-white bg-libre-green hover:bg-libre-green/90 disabled:opacity-50" disabled={!canTransfer && !canFx} onclick={() => (step = 2)} data-testid="tx-promote-next"> Next ▸ </button>
        {:else}
            <button class="px-4 py-1.5 text-xs rounded text-white bg-libre-green hover:bg-libre-green/90 disabled:opacity-50" disabled={promoteDisabled} onclick={commit} data-testid="tx-promote-commit">
                {committing ? '…promoting' : 'Promote ▸'}
            </button>
        {/if}
    </div>
</ModalBase>
