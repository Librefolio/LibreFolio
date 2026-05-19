<!--
  TransactionDeleteModal — Rich delete confirmation for single or paired tx.
  3 layouts: A (standalone), B (paired full), C (paired blocked).
  Plan B — Phase 07, Step 6. Svelte 5 runes, dark mode, data-testid.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Trash2, X, Info, Lock, AlertTriangle, Check} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import TransactionResultBanner from './TransactionResultBanner.svelte';
    import BrokerBadge from '$lib/components/ui/BrokerBadge.svelte';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';
    import {getBrokerInfo, getAllBrokers, getBrokerRole} from '$lib/stores/brokerStore';
    import {getAssetInfo} from '$lib/stores/assetStore';
    import {getTransactionTypeIconUrl} from '$lib/stores/transactionTypeStore';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {getStringBadgeStyle} from '$lib/utils/colors';
    import {formatTxQuantity, formatTxCash} from './txDisplayHelpers';
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

    let {open = $bindable(false), transaction = null, partner = null, partnerInaccessible = false, partnerBrokerName = '', errors = [], errorVariant = 'error', validating = false, validated = false, onConfirm, onValidate, onCancel}: Props = $props();

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

    const fQ = formatTxQuantity;
    const fC = formatTxCash;

    function handleClose() {
        onCancel();
    }

    let giver = $derived(transaction && partner ? (Number(transaction.quantity) < 0 ? transaction : partner) : transaction);
    let receiver = $derived(transaction && partner ? (Number(transaction.quantity) < 0 ? partner : transaction) : transaction);
</script>

<ModalBase {open} maxWidth={layout === 'B' ? 'xl' : 'lg'} onRequestClose={handleClose} testId="tx-delete-modal">
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
            <TransactionResultBanner
                variant={errorVariant}
                title={errorVariant === 'error' ? `⛔ ${$t('transactions.deleteModal.deleteAbortedTitle') || 'Deletion cancelled'}` : `⚠️ ${$t('transactions.deleteModal.validateWarningTitle') || 'Validation issues'}`}
                subtitle={errorVariant === 'error' ? $t('transactions.deleteModal.deleteAbortedDetail') || '' : ''}
                messages={errors}
                testId="tx-delete-modal-errors"
            />
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
                                        <img
                                            src={aIconUrl(transaction.asset_id)}
                                            alt=""
                                            class="w-5 h-5 object-contain"
                                            onerror={(e) => {
                                                (e.currentTarget as HTMLImageElement).style.display = 'none';
                                            }}
                                        />
                                    {/if}
                                    {aName(transaction.asset_id)}
                                </td>
                            </tr>
                            <tr class="border-b border-gray-100 dark:border-gray-700"
                                ><td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.broker')}</td><td class="px-3 py-2"><BrokerBadge broker={bLike(transaction.broker_id)} brokers={brkrs} showRole role={getBrokerRole(transaction.broker_id)} /></td></tr
                            >
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
                                <tr class="border-b border-gray-100 dark:border-gray-700"
                                    ><td class="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">{$t('transactions.table.asset')}</td><td class="px-3 py-2"
                                        ><span class="inline-flex items-center gap-1.5"
                                            >{#if aIconUrl(giver.asset_id)}<img
                                                    src={aIconUrl(giver.asset_id)}
                                                    alt=""
                                                    class="w-4 h-4 object-contain"
                                                    onerror={(e) => {
                                                        (e.currentTarget as HTMLImageElement).style.display = 'none';
                                                    }}
                                                />{/if}{aName(giver.asset_id)}</span
                                        ></td
                                    ><td class="px-3 py-2"
                                        ><span class="inline-flex items-center gap-1.5"
                                            >{#if aIconUrl(receiver.asset_id)}<img
                                                    src={aIconUrl(receiver.asset_id)}
                                                    alt=""
                                                    class="w-4 h-4 object-contain"
                                                    onerror={(e) => {
                                                        (e.currentTarget as HTMLImageElement).style.display = 'none';
                                                    }}
                                                />{/if}{aName(receiver.asset_id)}</span
                                        ></td
                                    ></tr
                                >
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
            <div class="flex items-center gap-2">
                {#if layout !== 'C' && onValidate}
                    {#if validating}
                        <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.validate.validating') || 'Validating...'}</span>
                    {:else}
                        <button
                            type="button"
                            class="inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700"
                            onclick={onValidate}
                            data-testid="tx-delete-validate-now"
                            title={$t('transactions.validate.now') || 'Validate now'}
                        >
                            ⚡ <span class="hidden sm:inline">{$t('transactions.validate.now') || 'Validate now'}</span>
                        </button>
                    {/if}
                    {#if validated && errors.length === 0}
                        <span class="text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-1" data-testid="tx-delete-valid-inline">
                            <Check size={14} />
                            {$t('transactions.validate.deleteOk') || 'Removal allowed'}
                        </span>
                    {/if}
                {/if}
            </div>
            <div class="flex gap-3">
                <button
                    class="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition inline-flex items-center gap-1.5"
                    onclick={handleClose}
                    data-testid="tx-delete-modal-cancel"
                    title={layout === 'C' ? $t('common.close') || 'Close' : $t('common.cancel') || 'Cancel'}
                >
                    <X size={15} />
                    {#if layout === 'C'}
                        <span class="hidden sm:inline">{$t('common.close') || 'Close'}</span>
                    {:else}
                        <span class="hidden sm:inline">{$t('common.cancel') || 'Cancel'}</span>
                    {/if}
                </button>
                {#if layout !== 'C'}
                    <button
                        class="px-4 py-2 text-sm text-white bg-red-600 rounded-lg hover:bg-red-700 transition flex items-center gap-1.5"
                        onclick={onConfirm}
                        data-testid="tx-delete-modal-confirm"
                        title={layout === 'B' ? $t('transactions.deleteModal.deleteBoth') || 'Delete both' : $t('common.delete') || 'Delete'}
                    >
                        <Trash2 size={15} />
                        {#if layout === 'B'}
                            <span class="hidden sm:inline">{$t('transactions.deleteModal.deleteBoth') || 'Delete both'}</span>
                        {:else}
                            <span class="hidden sm:inline">{$t('common.delete') || 'Delete'}</span>
                        {/if}
                    </button>
                {/if}
            </div>
        </div>
    </div>
</ModalBase>
