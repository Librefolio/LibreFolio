<!--
  TransactionActionModal.svelte — Rich confirmation for split and promote actions.
  Generalizes confirmations beyond the simple ConfirmModal:
  - mode='split': shows before→after (paired → 2 standalone) preview
  - mode='promote': shows 2 standalone → paired target preview
  Plan D2 Bugfix 2 Step 9 (2026-05-13).
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Unlink, Link2, ArrowRight} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import BrokerBadge from '$lib/components/ui/BrokerBadge.svelte';
    import {getBrokerInfo, getAllBrokers, getBrokerRole} from '$lib/stores/brokerStore';
    import {getTransactionTypeIconUrl} from '$lib/stores/transactionTypeStore';
    import {formatCurrencyAmountPlain} from '$lib/utils/currencyFormat';
    import type {BrokerLike} from '$lib/utils/brokerColors';

    /** Client-side mirror of backend SPLIT_TYPE_MAP. */
    const SPLIT_TYPE_MAP: Record<string, [string, string]> = {
        TRANSFER: ['ADJUSTMENT', 'ADJUSTMENT'],
        CASH_TRANSFER: ['WITHDRAWAL', 'DEPOSIT'],
        FX_CONVERSION: ['WITHDRAWAL', 'DEPOSIT'],
    };

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
    }

    interface Props {
        open: boolean;
        mode: 'split' | 'promote';
        transaction: TXReadItem | null;
        partner?: TXReadItem | null;
        /** For promote mode: target type label. */
        targetTypeLabel?: string;
        /** For promote mode: target type code. */
        targetType?: string;
        loading?: boolean;
        onConfirm: () => void;
        onCancel: () => void;
    }

    let {open, mode, transaction = null, partner = null, targetTypeLabel = '', targetType = '', loading = false, onConfirm, onCancel}: Props = $props();

    let brkrs = $derived(getAllBrokers() as BrokerLike[]);

    function bLike(brokerId: number): BrokerLike {
        return (getBrokerInfo(brokerId) as BrokerLike) ?? ({id: brokerId, name: `#${brokerId}`} as BrokerLike);
    }

    function fC(cash: {code: string; amount: string} | null | undefined): string {
        if (!cash) return '\u2014';
        return formatCurrencyAmountPlain(Number(cash.amount), cash.code, {showSign: true});
    }

    // Split: compute post-split types
    let splitTypes = $derived.by(() => {
        if (mode !== 'split' || !transaction) return null;
        const mapping = SPLIT_TYPE_MAP[transaction.type];
        if (!mapping) return null;
        const [fromType, toType] = mapping;
        // Determine from/to by sign
        const cashAmt = Number(transaction.cash?.amount ?? 0);
        const qty = Number(transaction.quantity ?? 0);
        const isFrom = transaction.type === 'TRANSFER' ? qty < 0 : cashAmt < 0;
        return {
            txType: isFrom ? fromType : toType,
            partnerType: isFrom ? toType : fromType,
        };
    });

    let title = $derived(mode === 'split' ? `✂️ ${$t('transactions.split.confirmTitle') || 'Unlink this pair?'}` : `🔗 ${$t('transactions.actions.promotePair') || 'Promote pair'}`);
    let confirmLabel = $derived(mode === 'split' ? `✂️ ${$t('transactions.split.confirmTitle') || 'Split'}` : `🔗 ${$t('transactions.promote.commit') || 'Promote'}`);
</script>

<ModalBase {open} maxWidth="lg" onRequestClose={onCancel} testId="tx-action-modal">
    <div class="p-6 space-y-4" data-testid="tx-action-modal-content">
        <!-- Header -->
        <div class="flex items-center gap-2 text-lg font-semibold text-gray-800 dark:text-gray-100">
            {#if mode === 'split'}
                <Unlink size={20} class="text-amber-500" />
            {:else}
                <Link2 size={20} class="text-green-600 dark:text-green-400" />
            {/if}
            <span>{title}</span>
        </div>

        {#if transaction}
            {#if mode === 'split'}
                <!-- Split preview: before → after -->
                <p class="text-sm text-gray-600 dark:text-gray-400">
                    {$t('transactions.split.confirmMessage') || 'The 2 transactions will become independent rows.'}
                </p>

                <div class="grid grid-cols-[1fr_auto_1fr] gap-3 items-start">
                    <!-- Before: paired -->
                    <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-3 space-y-2" data-testid="tx-action-before">
                        <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Before</div>
                        <div class="flex items-center gap-2">
                            {#if getTransactionTypeIconUrl(transaction.type)}
                                <img src={getTransactionTypeIconUrl(transaction.type)} alt="" class="w-5 h-5" />
                            {/if}
                            <span class="text-sm font-medium">{$t(`transactions.types.${transaction.type}`) || transaction.type}</span>
                        </div>
                        <div class="text-xs text-gray-500">
                            <div>{transaction.date}</div>
                            <div>{fC(transaction.cash)}</div>
                            <div class="mt-1"><BrokerBadge broker={bLike(transaction.broker_id)} brokers={brkrs} showRole role={getBrokerRole(transaction.broker_id)} /></div>
                        </div>
                        {#if partner}
                            <div class="border-t border-gray-100 dark:border-gray-700 pt-2 mt-2 text-xs text-gray-500">
                                <div class="flex items-center gap-1">
                                    <span>↔</span>
                                    <BrokerBadge broker={bLike(partner.broker_id)} brokers={brkrs} showRole role={getBrokerRole(partner.broker_id)} />
                                </div>
                                <div>{fC(partner.cash)}</div>
                            </div>
                        {/if}
                    </div>

                    <!-- Arrow -->
                    <div class="flex items-center justify-center pt-8">
                        <ArrowRight size={24} class="text-gray-400" />
                    </div>

                    <!-- After: 2 standalone -->
                    <div class="space-y-2" data-testid="tx-action-after">
                        <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">After</div>
                        <!-- TX 1 -->
                        <div class="border border-green-200 dark:border-green-800 bg-green-50/50 dark:bg-green-950/20 rounded-lg p-2">
                            <div class="flex items-center gap-2">
                                {#if splitTypes && getTransactionTypeIconUrl(splitTypes.txType)}
                                    <img src={getTransactionTypeIconUrl(splitTypes.txType)} alt="" class="w-4 h-4" />
                                {/if}
                                <span class="text-xs font-medium">{splitTypes ? ($t(`transactions.types.${splitTypes.txType}`) || splitTypes.txType) : '?'}</span>
                            </div>
                            <div class="text-[11px] text-gray-500 mt-1"><BrokerBadge broker={bLike(transaction.broker_id)} brokers={brkrs} /></div>
                        </div>
                        <!-- TX 2 -->
                        {#if partner}
                            <div class="border border-green-200 dark:border-green-800 bg-green-50/50 dark:bg-green-950/20 rounded-lg p-2">
                                <div class="flex items-center gap-2">
                                    {#if splitTypes && getTransactionTypeIconUrl(splitTypes.partnerType)}
                                        <img src={getTransactionTypeIconUrl(splitTypes.partnerType)} alt="" class="w-4 h-4" />
                                    {/if}
                                    <span class="text-xs font-medium">{splitTypes ? ($t(`transactions.types.${splitTypes.partnerType}`) || splitTypes.partnerType) : '?'}</span>
                                </div>
                                <div class="text-[11px] text-gray-500 mt-1"><BrokerBadge broker={bLike(partner.broker_id)} brokers={brkrs} /></div>
                            </div>
                        {/if}
                    </div>
                </div>
            {:else}
                <!-- Promote preview: 2 standalone → paired target -->
                <div class="grid grid-cols-[1fr_auto_1fr] gap-3 items-start">
                    <!-- TX A -->
                    <div class="border border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/20 rounded-lg p-3 space-y-2" data-testid="tx-action-promote-a">
                        <div class="flex items-center gap-2">
                            {#if getTransactionTypeIconUrl(transaction.type)}
                                <img src={getTransactionTypeIconUrl(transaction.type)} alt="" class="w-5 h-5" />
                            {/if}
                            <span class="text-sm font-medium">{$t(`transactions.types.${transaction.type}`) || transaction.type}</span>
                        </div>
                        <div class="text-xs text-gray-500">
                            <div>{transaction.date}</div>
                            <div>{fC(transaction.cash)}</div>
                            <div class="mt-1"><BrokerBadge broker={bLike(transaction.broker_id)} brokers={brkrs} showRole role={getBrokerRole(transaction.broker_id)} /></div>
                        </div>
                    </div>

                    <!-- Arrow + target -->
                    <div class="flex flex-col items-center justify-center gap-2 pt-4">
                        <ArrowRight size={24} class="text-green-500 rotate-0" />
                        {#if targetType && getTransactionTypeIconUrl(targetType)}
                            <img src={getTransactionTypeIconUrl(targetType)} alt="" class="w-6 h-6" />
                        {/if}
                        <span class="text-xs font-semibold text-green-700 dark:text-green-300">{targetTypeLabel}</span>
                    </div>

                    <!-- TX B -->
                    {#if partner}
                        <div class="border border-pink-200 dark:border-pink-800 bg-pink-50/50 dark:bg-pink-950/20 rounded-lg p-3 space-y-2" data-testid="tx-action-promote-b">
                            <div class="flex items-center gap-2">
                                {#if getTransactionTypeIconUrl(partner.type)}
                                    <img src={getTransactionTypeIconUrl(partner.type)} alt="" class="w-5 h-5" />
                                {/if}
                                <span class="text-sm font-medium">{$t(`transactions.types.${partner.type}`) || partner.type}</span>
                            </div>
                            <div class="text-xs text-gray-500">
                                <div>{partner.date}</div>
                                <div>{fC(partner.cash)}</div>
                                <div class="mt-1"><BrokerBadge broker={bLike(partner.broker_id)} brokers={brkrs} showRole role={getBrokerRole(partner.broker_id)} /></div>
                            </div>
                        </div>
                    {/if}
                </div>

                <p class="text-xs text-gray-500 dark:text-gray-400 flex items-start gap-1.5">
                    <span>⚠️</span>
                    <span>{$t('transactions.promote.atomicWarning') || 'This will DELETE both source rows and CREATE 2 linked rows atomically.'}</span>
                </p>
            {/if}
        {/if}

        <!-- Footer -->
        <div class="flex justify-end gap-3 pt-2">
            <button
                type="button"
                class="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition"
                onclick={onCancel}
                data-testid="tx-action-modal-cancel"
            >
                {$t('common.cancel')}
            </button>
            <button
                type="button"
                class="px-4 py-2 text-sm text-white rounded-lg transition flex items-center gap-1.5 {mode === 'split' ? 'bg-amber-600 hover:bg-amber-700' : 'bg-green-600 hover:bg-green-700'}"
                onclick={onConfirm}
                disabled={loading}
                data-testid="tx-action-modal-confirm"
            >
                {#if mode === 'split'}
                    <Unlink size={15} />
                {:else}
                    <Link2 size={15} />
                {/if}
                <span>{loading ? ($t('common.saving') || 'Saving...') : confirmLabel}</span>
            </button>
        </div>
    </div>
</ModalBase>


