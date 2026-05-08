<!--
  TransactionDeleteModal — Rich delete confirmation for single or paired tx.
  3 layouts: A (standalone), B (paired full), C (paired blocked).
  Plan B — Phase 07, Step 6. Svelte 5 runes, dark mode, data-testid.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Trash2, X, Info, AlertTriangle, Lock, Check} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import BrokerBadge from '$lib/components/ui/BrokerBadge.svelte';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';
    import {getBrokerInfo, getAllBrokers, getBrokerRole} from '$lib/stores/brokerStore';
    import {getAssetInfo} from '$lib/stores/assetStore';
    import {getTransactionTypeIconUrl} from '$lib/stores/transactionTypeStore';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {formatCurrencyAmountPlain} from '$lib/utils/currencyFormat';
    import {getStringBadgeStyle} from '$lib/utils/colors';
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
    }

    interface Props {
        open: boolean;
        transaction: TXReadItem | null;
        partner?: TXReadItem | null;
        partnerInaccessible?: boolean;
        partnerBrokerName?: string;
        /** B23: resolved error messages from committed:false response. */
        errors?: string[];
        /** 'warning' = validate issues (yellow), 'error' = commit failed (red). */
        errorVariant?: 'warning' | 'error';
        /** True while a validate/commit is in progress. */
        validating?: boolean;
        /** True when last validation succeeded (no errors). */
        validated?: boolean;
        onConfirm: () => void;
        onValidate?: () => void;
        onCancel: () => void;
    }

    let {
        open = $bindable(false),
        transaction = null,
        partner = null,
        partnerInaccessible = false,
        partnerBrokerName = '',
        errors = [],
        errorVariant = 'error',
        validating = false,
        validated = false,
        onConfirm,
        onValidate,
        onCancel,
    }: Props = $props();

    let brkrs = $derived(getAllBrokers() as BrokerLike[]);
    let isPaired = $derived(transaction?.related_transaction_id != null);
    let isBlocked = $derived(isPaired && (partnerInaccessible || (!partner && transaction?.related_transaction_id != null)));
    let layout = $derived<'A' | 'B' | 'C'>(!isPaired ? 'A' : isBlocked ? 'C' : 'B');

    function aName(id: number | null | undefined): string {
        if (!id) return '\u2014';
        return getAssetInfo(id)?.display_name ?? `#${id}`;
    }

    function aIconUrl(id: number | null | undefined): string | null {
        if (!id) return null;
        const info = getAssetInfo(id);
        return info?.icon_url ?? getAssetTypeIconUrl(info?.asset_type) ?? null;
    }

    function bLike(brokerId: number): BrokerLike {
        return (getBrokerInfo(brokerId) as BrokerLike) ?? ({id: brokerId, name: `#${brokerId}`} as BrokerLike);
    }

    function fQ(qty: string): string {
        const n = Number(qty);
        const a = n < 0 ? '\uD83D\uDCC9' : n > 0 ? '\uD83D\uDCC8' : '';
        return `${n.toLocaleString(undefined, {maximumFractionDigits: 6})} ${a}`;
    }

    function fC(cash: {code: string; amount: string} | null | undefined): string {
        if (!cash) return '\u2014';
        return formatCurrencyAmountPlain(Number(cash.amount), cash.code, {showSign: true});
    }

    function handleClose() {
        onCancel();
    }

    let giver = $derived(
        transaction && partner
            ? (Number(transaction.quantity) < 0 ? transaction : partner)
            : transaction,
    );
    let receiver = $derived(
        transaction && partner
            ? (Number(transaction.quantity) < 0 ? partner : transaction)
            : transaction,
    );
</script>

<ModalBase {open} maxWidth="lg" onRequestClose={handleClose} testId="tx-delete-modal">
    <div class="p-6 space-y-4" data-testid="tx-delete-modal-content">
        <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-gray-800 dark:text-gray-100 flex items-center gap-2">
                <Trash2 size={20} class="text-red-500" />
                {#if layout === 'A'}
                    {$t('transactions.deleteModal.titleStandalone') || 'Delete transaction'}
                {:else}
                    {$t('transactions.deleteModal.titleLinked') || 'Delete linked transaction'}
                {/if}
            </h3>
            <button class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" onclick={handleClose} data-testid="tx-delete-modal-close">
                <X size={20} />
            </button>
        </div>

        {#if errors.length > 0}
            {#if errorVariant === 'error'}
                <div class="flex flex-col gap-1 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded p-3" data-testid="tx-delete-modal-errors">
                    <div class="flex items-center gap-2 font-semibold">
                        <AlertTriangle size={16} class="flex-shrink-0" />
                        <span>⛔ {$t('transactions.deleteModal.deleteAbortedTitle') || 'Deletion cancelled'}</span>
                    </div>
                    <p class="text-xs opacity-80 ml-6">{$t('transactions.deleteModal.deleteAbortedDetail') || 'The operation was rolled back because it would violate balance rules:'}</p>
                    <div class="ml-6">
                        {#each errors as err}
                            <p>{@html err}</p>
                        {/each}
                    </div>
                </div>
            {:else}
                <div class="flex flex-col gap-1 text-sm text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 rounded p-3" data-testid="tx-delete-modal-errors">
                    <div class="flex items-center gap-2 font-semibold">
                        <AlertTriangle size={16} class="flex-shrink-0" />
                        <span>⚠️ {$t('transactions.deleteModal.validateWarningTitle') || 'Validation issues'}</span>
                    </div>
                    <div class="ml-6">
                        {#each errors as err}
                            <p>{@html err}</p>
                        {/each}
                    </div>
                </div>
            {/if}
        {:else if validated}
            <div class="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 rounded p-3" data-testid="tx-delete-modal-valid">
                <Check size={16} class="flex-shrink-0" />
                <span>{$t('transactions.deleteModal.canBeDeleted') || 'This transaction can be deleted safely.'}</span>
            </div>
        {/if}

        {#if transaction}
            {#if layout === 'A'}
                <div class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden" data-testid="tx-delete-details">
                    <table class="w-full text-sm">
                        <tbody>
                            <tr class="border-b border-gray-100 dark:border-gray-700"><td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400 w-28">{$t('transactions.table.date')}</td><td class="px-3 py-2">{transaction.date}</td></tr>
                            <tr class="border-b border-gray-100 dark:border-gray-700">
                                <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.type')}</td>
                                <td class="px-3 py-2 flex items-center gap-2">
                                    {#if getTransactionTypeIconUrl(transaction.type)}
                                        <img src={getTransactionTypeIconUrl(transaction.type)} alt="" class="w-5 h-5" />
                                    {/if}
                                    {$t(`transactions.types.${transaction.type}`) || transaction.type}
                                </td>
                            </tr>
                            <tr class="border-b border-gray-100 dark:border-gray-700"><td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.quantity')}</td><td class="px-3 py-2">{fQ(transaction.quantity)}</td></tr>
                            <tr class="border-b border-gray-100 dark:border-gray-700"><td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.cash')}</td><td class="px-3 py-2">{fC(transaction.cash)}</td></tr>
                            <tr class="border-b border-gray-100 dark:border-gray-700">
                                <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.asset')}</td>
                                <td class="px-3 py-2 flex items-center gap-2">
                                    {#if aIconUrl(transaction.asset_id)}
                                        <img src={aIconUrl(transaction.asset_id)} alt="" class="w-5 h-5 object-contain" onerror={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />
                                    {/if}
                                    {aName(transaction.asset_id)}
                                </td>
                            </tr>
                            <tr class="border-b border-gray-100 dark:border-gray-700"><td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.broker')}</td><td class="px-3 py-2"><BrokerBadge broker={bLike(transaction.broker_id)} brokers={brkrs} showRole role={getBrokerRole(transaction.broker_id)} /></td></tr>
                            {#if transaction.tags?.length}
                                <tr class="border-b border-gray-100 dark:border-gray-700">
                                    <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.tags')}</td>
                                    <td class="px-3 py-2 flex gap-1 flex-wrap">
                                        {#each transaction.tags as tag}<span class="px-1.5 py-0.5 text-xs rounded" style={getStringBadgeStyle(tag)}>{tag}</span>{/each}
                                    </td>
                                </tr>
                            {/if}
                            {#if transaction.description}
                                <tr>
                                    <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.description')}</td>
                                    <td class="px-3 py-2">
                                        <Tooltip text={transaction.description} position="top" maxWidth="360px">
                                            <span class="truncate block max-w-[250px]">{transaction.description}</span>
                                        </Tooltip>
                                    </td>
                                </tr>
                            {/if}
                        </tbody>
                    </table>
                </div>

            {:else if layout === 'B'}
                <p class="text-sm text-gray-600 dark:text-gray-400">{$t('transactions.deleteModal.pairedIntro') || 'Both transactions in this pair will be deleted.'}</p>
                {#if giver && receiver}
                    <div class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden" data-testid="tx-delete-paired-details">
                        <table class="w-full text-sm">
                            <thead>
                                <tr class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                                    <th class="px-3 py-2 text-left text-gray-500 dark:text-gray-400 font-medium w-24"></th>
                                    <th class="px-3 py-2 text-left text-gray-500 dark:text-gray-400 font-medium">{$t('transactions.deleteModal.from') || 'From'}</th>
                                    <th class="px-3 py-2 text-left text-gray-500 dark:text-gray-400 font-medium">{$t('transactions.deleteModal.to') || 'To'}</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr class="border-b border-gray-100 dark:border-gray-700"><td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.date')}</td><td class="px-3 py-2">{giver.date}</td><td class="px-3 py-2">{receiver.date}</td></tr>
                                <tr class="border-b border-gray-100 dark:border-gray-700"><td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.asset')}</td><td class="px-3 py-2"><span class="inline-flex items-center gap-1.5">{#if aIconUrl(giver.asset_id)}<img src={aIconUrl(giver.asset_id)} alt="" class="w-4 h-4 object-contain" onerror={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />{/if}{aName(giver.asset_id)}</span></td><td class="px-3 py-2"><span class="inline-flex items-center gap-1.5">{#if aIconUrl(receiver.asset_id)}<img src={aIconUrl(receiver.asset_id)} alt="" class="w-4 h-4 object-contain" onerror={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />{/if}{aName(receiver.asset_id)}</span></td></tr>
                                <tr class="border-b border-gray-100 dark:border-gray-700"><td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.quantity')}</td><td class="px-3 py-2">{fQ(giver.quantity)}</td><td class="px-3 py-2">{fQ(receiver.quantity)}</td></tr>
                                <tr class="border-b border-gray-100 dark:border-gray-700">
                                    <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.broker')}</td>
                                    <td class="px-3 py-2"><BrokerBadge broker={bLike(giver.broker_id)} brokers={brkrs} showRole role={getBrokerRole(giver.broker_id)} /></td>
                                    <td class="px-3 py-2"><BrokerBadge broker={bLike(receiver.broker_id)} brokers={brkrs} showRole role={getBrokerRole(receiver.broker_id)} /></td>
                                </tr>
                                <tr><td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.cash')}</td><td class="px-3 py-2">{fC(giver.cash)}</td><td class="px-3 py-2">{fC(receiver.cash)}</td></tr>
                            </tbody>
                        </table>
                    </div>
                {/if}
                <div class="flex items-start gap-2 text-xs text-gray-500 dark:text-gray-400">
                    <Info size={14} class="mt-0.5 flex-shrink-0" />
                    <span>{$t('transactions.deleteModal.splitHint') || 'To delete only one side, first use Split to unlink the pair.'}</span>
                </div>

            {:else}
                <p class="text-sm text-gray-600 dark:text-gray-400">{$t('transactions.deleteModal.linkedInfo') || 'This transaction is part of a linked pair.'}</p>
                <div class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden" data-testid="tx-delete-blocked-details">
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
                                <td class="px-3 py-2 text-gray-400">&mdash;</td>
                            </tr>
                            <tr class="border-b border-gray-100 dark:border-gray-700">
                                <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.asset')}</td>
                                <td class="px-3 py-2">{aName(transaction.asset_id)}</td>
                                <td class="px-3 py-2 text-center" rowspan="3">
                                    <div class="flex flex-col items-center justify-center gap-1 text-gray-400 dark:text-gray-500 py-4">
                                        <Lock size={24} class="text-red-400" />
                                        <span class="text-xs font-medium">{$t('transactions.deleteModal.brokerLabel') || 'Broker'}</span>
                                        <span class="text-xs">&laquo;{partnerBrokerName || '?'}&raquo;</span>
                                        <span class="text-xs">{$t('transactions.deleteModal.notAccessible') || 'not accessible'}</span>
                                    </div>
                                </td>
                            </tr>
                            <tr class="border-b border-gray-100 dark:border-gray-700">
                                <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.quantity')}</td>
                                <td class="px-3 py-2">{fQ(transaction.quantity)}</td>
                            </tr>
                            <tr>
                                <td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.broker')}</td>
                                <td class="px-3 py-2"><BrokerBadge broker={bLike(transaction.broker_id)} brokers={brkrs} showRole role={getBrokerRole(transaction.broker_id)} /></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="flex items-start gap-2 text-sm text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 rounded p-3">
                    <AlertTriangle size={16} class="mt-0.5 flex-shrink-0" />
                    <span>
                        {$t('transactions.deleteModal.blockedMessage') || 'Cannot delete: you need Editor access on both brokers to delete a linked pair.'}
                        {#if partnerBrokerName}
                            {' '}{$t('transactions.deleteModal.contactOwner') || 'Contact the owner of'} &laquo;{partnerBrokerName}&raquo; {$t('transactions.deleteModal.forAccess') || 'for access.'}
                        {/if}
                    </span>
                </div>
            {/if}
        {/if}

        <div class="flex justify-between items-center gap-3 pt-2">
            <div>
                {#if layout !== 'C' && onValidate}
                    {#if validating}
                        <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.validate.validating') || 'Validating...'}</span>
                    {:else}
                        <button type="button" class="inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={onValidate} data-testid="tx-delete-validate-now">
                            ⚡ {$t('transactions.validate.now') || 'Validate now'}
                        </button>
                    {/if}
                {/if}
            </div>
            <div class="flex gap-3">
            <button class="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition" onclick={handleClose} data-testid="tx-delete-modal-cancel">
                {#if layout === 'C'}
                    {$t('common.close') || 'Close'}
                {:else}
                    {$t('common.cancel') || 'Cancel'}
                {/if}
            </button>
            {#if layout !== 'C'}
                <button class="px-4 py-2 text-sm text-white bg-red-600 rounded-lg hover:bg-red-700 transition flex items-center gap-1.5" onclick={onConfirm} data-testid="tx-delete-modal-confirm">
                    <Trash2 size={15} />
                    {#if layout === 'B'}
                        {$t('transactions.deleteModal.deleteBoth') || 'Delete both'}
                    {:else}
                        {$t('common.delete') || 'Delete'}
                    {/if}
                </button>
            {/if}
            </div>
        </div>
    </div>
</ModalBase>

