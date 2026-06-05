<!--
  TransactionActionModal.svelte — Rich confirmation for split and promote actions.
  Uses tabular layout (From/To columns) matching TransactionDeleteModal style.
  - mode='split': shows BEFORE (paired) → AFTER (2 standalone) preview
  - mode='promote': shows 2 standalone → paired target preview
  Plan D2 Bugfix 3 Step 4 — tabular redesign (2026-05-14).
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Unlink, Link2, ArrowDown} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import BrokerBadge from '$lib/components/ui/display/BrokerBadge.svelte';
    import {getBrokerInfo, getAllBrokers, getBrokerRole} from '$lib/stores/reference/brokerStore';
    import {getTransactionTypeIconUrl} from '$lib/stores/transactions/transactionTypeStore';
    import {getStringBadgeStyle} from '$lib/utils/colors';
    import {formatTxQuantity, formatTxCash} from '../shared/txDisplayHelpers';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';

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

    const fQ = formatTxQuantity;
    const fC = formatTxCash;

    function typeLabel(typeCode: string): string {
        return $t(`transactions.types.${typeCode}`) || typeCode;
    }

    // Split: compute post-split types
    let splitTypes = $derived.by(() => {
        if (mode !== 'split' || !transaction) return null;
        const mapping = SPLIT_TYPE_MAP[transaction.type];
        if (!mapping) return null;
        const [fromType, toType] = mapping;
        const cashAmt = Number(transaction.cash?.amount ?? 0);
        const qty = Number(transaction.quantity ?? 0);
        const isFrom = transaction.type === 'TRANSFER' ? qty < 0 : cashAmt < 0;
        return {
            txType: isFrom ? fromType : toType,
            partnerType: isFrom ? toType : fromType,
        };
    });

    let title = $derived(mode === 'split' ? `✂️ ${$t('transactions.split.confirmTitle') || 'Unlink this pair?'}` : `🔗 ${$t('transactions.actions.promotePair') || 'Link as pair'}`);
    let confirmLabel = $derived(mode === 'split' ? `✂️ ${$t('transactions.split.confirmTitle') || 'Split'}` : `🔗 ${$t('transactions.promote.commit') || 'Promote'}`);
    let borderColor = $derived('border-gray-200 dark:border-gray-700');
</script>

<ModalBase {open} maxWidth="xl" onRequestClose={onCancel} testId="tx-action-modal">
    <div class="flex flex-col max-h-[80vh]" data-testid="tx-action-modal-content">
        <!-- Sticky Header -->
        <div class="p-6 pb-3 border-b border-gray-200 dark:border-gray-700 shrink-0">
            <div class="flex items-center gap-2 text-lg font-semibold text-gray-800 dark:text-gray-100">
                {#if mode === 'split'}
                    <Unlink size={20} class="text-amber-500" />
                {:else}
                    <Link2 size={20} class="text-green-600 dark:text-green-400" />
                {/if}
                <span>{title}</span>
            </div>
        </div>

        <!-- Scrollable Body -->
        <div class="p-6 py-4 space-y-4 overflow-y-auto flex-1 min-h-0">
            {#if transaction}
                {#if mode === 'split'}
                    <!-- Split: BEFORE (paired) → AFTER (2 standalone) -->
                    <p class="text-sm text-gray-600 dark:text-gray-400">
                        {$t('transactions.split.confirmMessage') || 'The 2 transactions will become independent rows.'}
                    </p>

                    <!-- BEFORE table -->
                    <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">{$t('common.before') || 'Before'} ({$t('transactions.split.paired') || 'paired'})</div>
                    <div class="border {borderColor} rounded-lg overflow-hidden" data-testid="tx-action-before">
                        <table class="w-full text-sm">
                            <thead>
                                <tr class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                                    <th class="px-3 py-2 text-left text-gray-500 dark:text-gray-400 font-medium w-24"></th>
                                    <th class="px-3 py-2 text-left text-gray-500 dark:text-gray-400 font-medium">{$t('transactions.deleteModal.from') || 'From'}</th>
                                    <th class="px-3 py-2 text-left text-gray-500 dark:text-gray-400 font-medium">{$t('transactions.deleteModal.to') || 'To'}</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr class="border-b border-gray-100 dark:border-gray-700">
                                    <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.date')}</td>
                                    <td class="px-3 py-2">{transaction.date}</td>
                                    <td class="px-3 py-2">{partner?.date ?? '—'}</td>
                                </tr>
                                <tr class="border-b border-gray-100 dark:border-gray-700">
                                    <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.type')}</td>
                                    <td class="px-3 py-2">
                                        <span class="inline-flex items-center gap-2">
                                            {#if getTransactionTypeIconUrl(transaction.type)}
                                                <img src={getTransactionTypeIconUrl(transaction.type)} alt="" class="w-5 h-5 object-contain shrink-0" />
                                            {/if}
                                            {typeLabel(transaction.type)}
                                        </span>
                                    </td>
                                    <td class="px-3 py-2">
                                        <span class="inline-flex items-center gap-2">
                                            {#if partner && getTransactionTypeIconUrl(partner.type)}
                                                <img src={getTransactionTypeIconUrl(partner.type)} alt="" class="w-5 h-5 object-contain shrink-0" />
                                            {/if}
                                            {partner ? typeLabel(partner.type) : typeLabel(transaction.type)}
                                        </span>
                                    </td>
                                </tr>
                                <tr class="border-b border-gray-100 dark:border-gray-700">
                                    <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.quantity')}</td>
                                    <td class="px-3 py-2">{fQ(transaction.quantity)}</td>
                                    <td class="px-3 py-2">{fQ(partner?.quantity)}</td>
                                </tr>
                                <tr class="border-b border-gray-100 dark:border-gray-700">
                                    <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.cash')}</td>
                                    <td class="px-3 py-2">{fC(transaction.cash)}</td>
                                    <td class="px-3 py-2">{fC(partner?.cash)}</td>
                                </tr>
                                <tr class="border-b border-gray-100 dark:border-gray-700">
                                    <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.broker')}</td>
                                    <td class="px-3 py-2"><BrokerBadge broker={bLike(transaction.broker_id)} brokers={brkrs} /></td>
                                    <td class="px-3 py-2"
                                        >{#if partner}<BrokerBadge broker={bLike(partner.broker_id)} brokers={brkrs} />{:else}—{/if}</td
                                    >
                                </tr>
                                {#if transaction.tags?.length || partner?.tags?.length}
                                    <tr class="border-b border-gray-100 dark:border-gray-700">
                                        <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">Tags</td>
                                        <td class="px-3 py-2"
                                            ><span class="flex flex-wrap gap-1"
                                                >{#each transaction.tags ?? [] as tag}<span class="action-tag-badge inline-block px-1.5 py-0.5 text-[10px] rounded" style={getStringBadgeStyle(tag)}>{tag}</span>{/each}{#if !transaction.tags?.length}—{/if}</span
                                            ></td
                                        >
                                        <td class="px-3 py-2"
                                            ><span class="flex flex-wrap gap-1"
                                                >{#each partner?.tags ?? [] as tag}<span class="action-tag-badge inline-block px-1.5 py-0.5 text-[10px] rounded" style={getStringBadgeStyle(tag)}>{tag}</span>{/each}{#if !partner?.tags?.length}—{/if}</span
                                            ></td
                                        >
                                    </tr>
                                {/if}
                                {#if transaction.description || partner?.description}
                                    <tr>
                                        <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">Desc</td>
                                        <td class="px-3 py-2 text-xs truncate max-w-[160px]">{transaction.description ?? '—'}</td>
                                        <td class="px-3 py-2 text-xs truncate max-w-[160px]">{partner?.description ?? '—'}</td>
                                    </tr>
                                {/if}
                            </tbody>
                        </table>
                    </div>

                    <!-- Arrow down -->
                    <div class="flex justify-center"><ArrowDown size={20} class="text-gray-400" /></div>

                    <!-- AFTER table -->
                    <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">{$t('common.after') || 'After'} (2 {$t('transactions.split.standalone') || 'standalone'})</div>
                    <div class="border {borderColor} rounded-lg overflow-hidden" data-testid="tx-action-after">
                        <table class="w-full text-sm">
                            <thead>
                                <tr class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                                    <th class="px-3 py-2 text-left text-gray-500 dark:text-gray-400 font-medium w-24"></th>
                                    <th class="px-3 py-2 text-left text-gray-500 dark:text-gray-400 font-medium">TX #{transaction.id}</th>
                                    <th class="px-3 py-2 text-left text-gray-500 dark:text-gray-400 font-medium">TX #{partner?.id ?? '?'}</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr class="border-b border-gray-100 dark:border-gray-700">
                                    <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.date')}</td>
                                    <td class="px-3 py-2">{transaction.date}</td>
                                    <td class="px-3 py-2">{partner?.date ?? '—'}</td>
                                </tr>
                                <tr class="border-b border-gray-100 dark:border-gray-700">
                                    <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.type')}</td>
                                    <td class="px-3 py-2 flex items-center gap-2">
                                        {#if splitTypes && getTransactionTypeIconUrl(splitTypes.txType)}
                                            <img src={getTransactionTypeIconUrl(splitTypes.txType)} alt="" class="w-4 h-4 object-contain shrink-0" />
                                        {/if}
                                        {splitTypes ? typeLabel(splitTypes.txType) : '?'}
                                    </td>
                                    <td class="px-3 py-2">
                                        <span class="inline-flex items-center gap-2">
                                            {#if splitTypes && getTransactionTypeIconUrl(splitTypes.partnerType)}
                                                <img src={getTransactionTypeIconUrl(splitTypes.partnerType)} alt="" class="w-4 h-4 object-contain shrink-0" />
                                            {/if}
                                            {splitTypes ? typeLabel(splitTypes.partnerType) : '?'}
                                        </span>
                                    </td>
                                </tr>
                                <tr class="border-b border-gray-100 dark:border-gray-700">
                                    <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.quantity')}</td>
                                    <td class="px-3 py-2">{fQ(transaction.quantity)}</td>
                                    <td class="px-3 py-2">{fQ(partner?.quantity)}</td>
                                </tr>
                                <tr class="border-b border-gray-100 dark:border-gray-700">
                                    <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.cash')}</td>
                                    <td class="px-3 py-2">{fC(transaction.cash)}</td>
                                    <td class="px-3 py-2">{fC(partner?.cash)}</td>
                                </tr>
                                <tr class="border-b border-gray-100 dark:border-gray-700">
                                    <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.broker')}</td>
                                    <td class="px-3 py-2"><BrokerBadge broker={bLike(transaction.broker_id)} brokers={brkrs} /></td>
                                    <td class="px-3 py-2"
                                        >{#if partner}<BrokerBadge broker={bLike(partner.broker_id)} brokers={brkrs} />{:else}—{/if}</td
                                    >
                                </tr>
                                {#if transaction.tags?.length || partner?.tags?.length}
                                    <tr class="border-b border-gray-100 dark:border-gray-700">
                                        <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">Tags</td>
                                        <td class="px-3 py-2"
                                            ><span class="flex flex-wrap gap-1"
                                                >{#each transaction.tags ?? [] as tag}<span class="action-tag-badge inline-block px-1.5 py-0.5 text-[10px] rounded" style={getStringBadgeStyle(tag)}>{tag}</span>{/each}{#if !transaction.tags?.length}—{/if}</span
                                            ></td
                                        >
                                        <td class="px-3 py-2"
                                            ><span class="flex flex-wrap gap-1"
                                                >{#each partner?.tags ?? [] as tag}<span class="action-tag-badge inline-block px-1.5 py-0.5 text-[10px] rounded" style={getStringBadgeStyle(tag)}>{tag}</span>{/each}{#if !partner?.tags?.length}—{/if}</span
                                            ></td
                                        >
                                    </tr>
                                {/if}
                                {#if transaction.description || partner?.description}
                                    <tr>
                                        <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">Desc</td>
                                        <td class="px-3 py-2 text-xs truncate max-w-[160px]">{transaction.description ?? '—'}</td>
                                        <td class="px-3 py-2 text-xs truncate max-w-[160px]">{partner?.description ?? '—'}</td>
                                    </tr>
                                {/if}
                            </tbody>
                        </table>
                    </div>
                {:else}
                    <!-- Promote: 2 standalone → paired target -->
                    <p class="text-sm text-gray-600 dark:text-gray-400">
                        {$t('transactions.promote.promoteSubtitle') || '2 standalone → 1 paired'}
                    </p>

                    <!-- Source table -->
                    <div class="border {borderColor} rounded-lg overflow-hidden" data-testid="tx-action-promote-source">
                        <table class="w-full text-sm">
                            <thead>
                                <tr class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                                    <th class="px-3 py-2 text-left text-gray-500 dark:text-gray-400 font-medium w-24"></th>
                                    <th class="px-3 py-2 text-left text-gray-500 dark:text-gray-400 font-medium">TX #{transaction.id}</th>
                                    <th class="px-3 py-2 text-left text-gray-500 dark:text-gray-400 font-medium">TX #{partner?.id ?? '?'}</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr class="border-b border-gray-100 dark:border-gray-700">
                                    <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.date')}</td>
                                    <td class="px-3 py-2">{transaction.date}</td>
                                    <td class="px-3 py-2">{partner?.date ?? '—'}</td>
                                </tr>
                                <tr class="border-b border-gray-100 dark:border-gray-700">
                                    <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.type')}</td>
                                    <td class="px-3 py-2 flex items-center gap-2">
                                        {#if getTransactionTypeIconUrl(transaction.type)}
                                            <img src={getTransactionTypeIconUrl(transaction.type)} alt="" class="w-5 h-5 object-contain shrink-0" />
                                        {/if}
                                        {typeLabel(transaction.type)}
                                    </td>
                                    <td class="px-3 py-2">
                                        {#if partner}
                                            <span class="inline-flex items-center gap-2">
                                                {#if getTransactionTypeIconUrl(partner.type)}
                                                    <img src={getTransactionTypeIconUrl(partner.type)} alt="" class="w-5 h-5 object-contain shrink-0" />
                                                {/if}
                                                {typeLabel(partner.type)}
                                            </span>
                                        {:else}—{/if}
                                    </td>
                                </tr>
                                <tr class="border-b border-gray-100 dark:border-gray-700">
                                    <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.cash')}</td>
                                    <td class="px-3 py-2">{fC(transaction.cash)}</td>
                                    <td class="px-3 py-2">{fC(partner?.cash)}</td>
                                </tr>
                                <tr class="border-b border-gray-100 dark:border-gray-700">
                                    <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.quantity')}</td>
                                    <td class="px-3 py-2">{fQ(transaction.quantity)}</td>
                                    <td class="px-3 py-2">{fQ(partner?.quantity)}</td>
                                </tr>
                                <tr class="border-b border-gray-100 dark:border-gray-700">
                                    <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.broker')}</td>
                                    <td class="px-3 py-2"><BrokerBadge broker={bLike(transaction.broker_id)} brokers={brkrs} /></td>
                                    <td class="px-3 py-2"
                                        >{#if partner}<BrokerBadge broker={bLike(partner.broker_id)} brokers={brkrs} />{:else}—{/if}</td
                                    >
                                </tr>
                                {#if transaction.tags?.length || partner?.tags?.length}
                                    <tr class="border-b border-gray-100 dark:border-gray-700">
                                        <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">Tags</td>
                                        <td class="px-3 py-2"
                                            ><span class="flex flex-wrap gap-1"
                                                >{#each transaction.tags ?? [] as tag}<span class="action-tag-badge inline-block px-1.5 py-0.5 text-[10px] rounded" style={getStringBadgeStyle(tag)}>{tag}</span>{/each}{#if !transaction.tags?.length}—{/if}</span
                                            ></td
                                        >
                                        <td class="px-3 py-2"
                                            ><span class="flex flex-wrap gap-1"
                                                >{#each partner?.tags ?? [] as tag}<span class="action-tag-badge inline-block px-1.5 py-0.5 text-[10px] rounded" style={getStringBadgeStyle(tag)}>{tag}</span>{/each}{#if !partner?.tags?.length}—{/if}</span
                                            ></td
                                        >
                                    </tr>
                                {/if}
                                {#if transaction.description || partner?.description}
                                    <tr>
                                        <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">Desc</td>
                                        <td class="px-3 py-2 text-xs truncate max-w-[160px]">{transaction.description ?? '—'}</td>
                                        <td class="px-3 py-2 text-xs truncate max-w-[160px]">{partner?.description ?? '—'}</td>
                                    </tr>
                                {/if}
                            </tbody>
                        </table>
                    </div>

                    <!-- Arrow down -->
                    <div class="flex justify-center"><ArrowDown size={20} class="text-gray-400" /></div>

                    <!-- Target -->
                    <div class="border {borderColor} rounded-lg overflow-hidden" data-testid="tx-action-promote-target">
                        <table class="w-full text-sm">
                            <tbody>
                                <tr>
                                    <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400 w-24">{$t('transactions.promote.target') || 'Target'}</td>
                                    <td class="px-3 py-2 flex items-center gap-2">
                                        {#if targetType && getTransactionTypeIconUrl(targetType)}
                                            <img src={getTransactionTypeIconUrl(targetType)} alt="" class="w-5 h-5 object-contain shrink-0" />
                                        {/if}
                                        <span class="font-semibold text-green-700 dark:text-green-300">{targetTypeLabel}</span>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                    <p class="text-xs text-gray-500 dark:text-gray-400 flex items-start gap-1.5">
                        <span>⚠️</span>
                        <span>{$t('transactions.promote.atomicWarning') || 'Both source rows will be re-typed atomically.'}</span>
                    </p>
                {/if}
            {/if}
        </div>

        <!-- Sticky Footer -->
        <div class="p-6 pt-3 border-t border-gray-200 dark:border-gray-700 shrink-0">
            <div class="flex justify-end gap-3">
                <button type="button" class="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition" onclick={onCancel} data-testid="tx-action-modal-cancel">
                    {$t('common.cancel')}
                </button>
                <button type="button" class="px-4 py-2 text-sm text-white rounded-lg transition flex items-center gap-1.5 {mode === 'split' ? 'bg-amber-600 hover:bg-amber-700' : 'bg-green-600 hover:bg-green-700'}" onclick={onConfirm} disabled={loading} data-testid="tx-action-modal-confirm">
                    {#if mode === 'split'}
                        <Unlink size={15} />
                    {:else}
                        <Link2 size={15} />
                    {/if}
                    <span>{loading ? $t('common.saving') || 'Saving...' : confirmLabel}</span>
                </button>
            </div>
        </div>
    </div>
</ModalBase>

<style>
    .action-tag-badge {
        background: var(--badge-bg, #e2e8f0);
        color: var(--badge-text, #334155);
    }
    :global(html.dark) .action-tag-badge {
        background: var(--badge-dark-bg, #334155);
        color: var(--badge-dark-text, #e2e8f0);
    }
</style>
