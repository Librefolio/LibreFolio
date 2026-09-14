<script lang="ts">
    import {t} from '$lib/i18n';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import {currencyStoreVersion, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {Check, Info, Landmark, LoaderCircle, PencilLine, Plus, RefreshCw, Trash2} from 'lucide-svelte';
    import type {PacAllocationSourceCashSource} from './allocationSource';
    import type {PacCashSourceState, PacContributionInput, PacContributionMode, PacMoneyInput} from './editorTypes';

    type CashMode = PacCashSourceState['mode'];
    type MoneyMode = CashMode | PacContributionMode;
    type MoneyEditorValue = PacMoneyInput & {monetary_step?: PacContributionInput['monetary_step']};

    interface Props {
        kind: 'cash' | 'contributions';
        title: string;
        description: string;
        mode: MoneyMode;
        values: MoneyEditorValue[];
        cashSources?: readonly PacAllocationSourceCashSource[];
        selectedBrokerIds?: readonly number[];
        sourceLoading?: boolean;
        sourceError?: string | null;
        sourceStale?: boolean;
        disabled?: boolean;
        maxEntries?: number;
        onmodechange?: (mode: MoneyMode) => void;
        onadd: () => void;
        onremove: (index: number) => void;
        onchange: () => void;
        onbrokertoggle?: (brokerId: number) => void;
        onretry?: () => void;
    }

    let {
        kind,
        title,
        description,
        mode,
        values,
        cashSources = [],
        selectedBrokerIds = [],
        sourceLoading = false,
        sourceError = null,
        sourceStale = false,
        disabled = false,
        maxEntries = 4,
        onmodechange = () => {},
        onadd,
        onremove,
        onchange,
        onbrokertoggle = () => {},
        onretry = () => {},
    }: Props = $props();

    function isSelected(brokerId: number): boolean {
        return selectedBrokerIds.includes(brokerId);
    }

    function displayDecimal(value: string | null | undefined): string {
        return formatDecimalForDisplay(value, {maxFrac: 12}) || '0';
    }

    function currencyFlag(code: string | null | undefined): string {
        void $currencyStoreVersion;
        const flag = getCurrencyInfo(code ?? '').flag_emoji;
        return flag === '🏳️' ? '' : flag;
    }
</script>

<article class="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800/60" data-testid={`pac-${kind}`} data-density="compact">
    <div class="flex flex-wrap items-start justify-between gap-2">
        <div class="min-w-0 flex-1">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-white">{title}</h3>
            <p class="mt-0.5 text-xs leading-5 text-gray-500 dark:text-gray-400">{description}</p>
        </div>
        {#if kind === 'cash'}
            <button
                class="inline-flex min-h-9 shrink-0 items-center justify-center gap-1.5 rounded-md border border-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 transition hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-libre-green/70 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-200 dark:hover:bg-gray-800"
                type="button"
                {disabled}
                onclick={() => onmodechange(mode === 'broker_copy' ? 'manual' : 'broker_copy')}
                data-testid={mode === 'broker_copy' ? 'pac-cash-use-manual' : 'pac-cash-use-brokers'}
            >
                {#if mode === 'broker_copy'}
                    <PencilLine size={14} />
                    {$t('tools.pacAllocator.cash.enterAmounts')}
                {:else}
                    <Landmark size={14} />
                    {$t('tools.pacAllocator.cash.backToBrokers', {default: 'Use Broker reserves'})}
                {/if}
            </button>
        {/if}
    </div>

    {#if kind === 'cash' && mode === 'broker_copy'}
        <div class="mt-3 space-y-2.5" data-testid="pac-cash-broker-copy">
            {#if sourceLoading && cashSources.length === 0}
                <div class="flex min-h-20 items-center justify-center gap-2 rounded-lg border border-gray-200 bg-gray-50 text-xs text-gray-500 dark:border-gray-700 dark:bg-gray-900/40 dark:text-gray-400" data-testid="pac-cash-sources-loading">
                    <LoaderCircle class="animate-spin" size={18} />
                    <span>{$t('tools.pacAllocator.cash.loadingBrokerCash', {default: 'Loading Broker reserves…'})}</span>
                </div>
            {:else if sourceError && cashSources.length === 0}
                <div class="flex items-center justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800 dark:border-red-900/60 dark:bg-red-950/20 dark:text-red-200" role="alert" data-testid="pac-cash-source-error">
                    <span>{sourceError}</span>
                    <Tooltip text={$t('common.retry')} position="top" interactiveChild>
                        <button
                            class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-red-700 transition hover:bg-red-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500/70 disabled:opacity-50 dark:text-red-200 dark:hover:bg-red-900/40"
                            type="button"
                            onclick={onretry}
                            data-testid="pac-cash-source-retry"
                            aria-label={$t('common.retry')}
                        >
                            <RefreshCw size={14} />
                        </button>
                    </Tooltip>
                </div>
            {:else if cashSources.length === 0}
                <div class="rounded-lg border border-dashed border-gray-300 px-3 py-4 text-center text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400" data-testid="pac-cash-sources-empty">
                    {$t('tools.pacAllocator.cash.noOwnerBrokers', {default: 'No OWNER Broker is available. Enter cash manually.'})}
                </div>
            {:else}
                <div class="grid gap-2 sm:grid-cols-2 xl:grid-cols-3" data-testid="pac-cash-sources" aria-busy={sourceLoading}>
                    {#each cashSources as source (source.brokerId)}
                        {@const selected = isSelected(source.brokerId)}
                        <button
                            type="button"
                            class="relative flex min-h-20 items-start gap-2.5 rounded-lg border p-2.5 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-libre-green/60 {selected
                                ? 'border-libre-green bg-libre-green/5 dark:border-green-600 dark:bg-green-950/20'
                                : 'border-gray-200 bg-white hover:border-libre-green/60 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900/40 dark:hover:border-green-700 dark:hover:bg-gray-800'}"
                            aria-pressed={selected}
                            disabled={disabled || sourceLoading}
                            onclick={() => onbrokertoggle(source.brokerId)}
                            data-testid={`pac-cash-broker-${source.brokerId}`}
                        >
                            <BrokerIcon brokerId={source.brokerId} iconUrl={source.brokerIconUrl} portalUrl={source.brokerPortalUrl} pluginCode={source.brokerDefaultImportPlugin} altText={source.brokerName} size="md" />
                            <span class="min-w-0 flex-1">
                                <span class="flex items-start justify-between gap-2">
                                    <span>
                                        <span class="block truncate text-sm font-semibold text-gray-900 dark:text-white">{source.brokerName}</span>
                                        <span class="block text-[11px] text-gray-500 dark:text-gray-400">{displayDecimal(source.ownershipSharePercent)}% {$t('tools.pacAllocator.personalShare')}</span>
                                    </span>
                                    <span class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border {selected ? 'border-libre-green bg-libre-green text-white' : 'border-gray-300 text-transparent dark:border-gray-600'}">
                                        <Check size={13} strokeWidth={3} />
                                    </span>
                                </span>
                                <span class="mt-2 block text-[10px] font-medium text-gray-500 dark:text-gray-400">
                                    {$t('tools.pacAllocator.cash.fullNativeReserve', {default: 'Full native reserve'})}
                                </span>
                                <span class="mt-1 flex flex-wrap gap-1.5 text-[11px]">
                                    {#each source.balances as balance (`${source.brokerId}:${balance.currency}`)}
                                        <span class="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-gray-700 dark:bg-gray-800 dark:text-gray-200">
                                            {#if currencyFlag(balance.currency)}<span class="emoji-flag" aria-hidden="true">{currencyFlag(balance.currency)}</span>{/if}
                                            <span>{balance.currency}</span>
                                            <span class="font-mono">{displayDecimal(balance.amount)}</span>
                                        </span>
                                    {:else}
                                        <span class="text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.cash.noNativeBalances', {default: 'No native reserve'})}</span>
                                    {/each}
                                </span>
                            </span>
                        </button>
                    {/each}
                </div>
            {/if}

            {#if sourceLoading && cashSources.length > 0}
                <p class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400" role="status" data-testid="pac-cash-source-pending">
                    <LoaderCircle class="animate-spin" size={14} />
                    {$t('tools.pacAllocator.cash.refreshingSelection', {default: 'Updating selected native reserves…'})}
                </p>
            {:else if sourceError && !sourceStale}
                <div class="flex items-center justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800 dark:border-red-900/60 dark:bg-red-950/20 dark:text-red-200" role="alert" data-testid="pac-cash-source-error">
                    <span>{sourceError}</span>
                    <Tooltip text={$t('common.retry')} position="top" interactiveChild>
                        <button
                            class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-red-700 transition hover:bg-red-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500/70 disabled:opacity-50 dark:text-red-200 dark:hover:bg-red-900/40"
                            type="button"
                            onclick={onretry}
                            data-testid="pac-cash-source-retry"
                            aria-label={$t('common.retry')}
                        >
                            <RefreshCw size={14} />
                        </button>
                    </Tooltip>
                </div>
            {/if}
        </div>
    {:else if kind === 'contributions' && values.length === 0}
        <div class="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-dashed border-gray-300 bg-gray-50 px-3 py-2.5 dark:border-gray-700 dark:bg-gray-900/40" data-testid="pac-contributions-empty">
            <span class="text-xs text-gray-600 dark:text-gray-300">{$t('tools.pacAllocator.cash.noneContributions')}</span>
            <button
                class="inline-flex min-h-9 items-center justify-center gap-1.5 rounded-md border border-libre-green bg-libre-green px-2.5 py-1 text-xs font-semibold text-white transition hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-libre-green/70 disabled:cursor-not-allowed disabled:opacity-50 dark:text-gray-950"
                type="button"
                onclick={onadd}
                {disabled}
                data-testid="pac-add-contributions"
            >
                <Plus size={14} />
                <span>{$t('tools.pacAllocator.cash.addContribution', {default: 'Add contribution'})}</span>
            </button>
        </div>
    {:else}
        <div class="mt-3 space-y-2">
            {#each values as money, index}
                <div
                    class={kind === 'contributions'
                        ? 'grid grid-cols-[minmax(0,1fr)_auto] gap-2 rounded-lg border border-gray-200 p-2 sm:grid-cols-[minmax(9rem,1.4fr)_minmax(8rem,1fr)_minmax(8rem,1fr)_auto] sm:items-end dark:border-gray-700'
                        : 'grid grid-cols-[minmax(0,1fr)_auto] gap-2 sm:grid-cols-[minmax(9rem,1.4fr)_minmax(8rem,1fr)_auto] sm:items-end'}
                    data-testid={`pac-${kind}-row`}
                >
                    <label class="min-w-0 text-xs font-medium text-gray-600 dark:text-gray-300">
                        <span class="mb-1 block">{$t('tools.pacAllocator.cash.amount')}</span>
                        <ExactDecimalInput
                            value={money.amount ?? ''}
                            step="0.01"
                            maxIntegerDigits={12}
                            maxFractionDigits={12}
                            placeholder="0,00"
                            ariaLabel={$t('tools.pacAllocator.cash.amount')}
                            testid={`pac-${kind}-amount-${index}`}
                            className="min-h-9 !px-2 !py-1.5 text-sm"
                            {disabled}
                            onchange={(value) => {
                                money.amount = value;
                                onchange();
                            }}
                        />
                    </label>
                    <label class="min-w-0 text-xs font-medium text-gray-600 dark:text-gray-300">
                        <span class="mb-1 block">{$t('common.currency')}</span>
                        <CurrencySearchSelect
                            value={money.currency ?? ''}
                            compact
                            testId={`pac-${kind}-currency-${index}`}
                            {disabled}
                            onchange={(value) => {
                                money.currency = value;
                                onchange();
                            }}
                        />
                    </label>
                    {#if kind === 'contributions'}
                        <label class="min-w-0 text-xs font-medium text-gray-600 dark:text-gray-300">
                            <span class="mb-1 inline-flex items-center gap-1">
                                {$t('tools.pacAllocator.cash.monetaryStep', {default: 'Amount increment'})}
                                <Tooltip
                                    text={$t('tools.pacAllocator.cash.monetaryStepHint', {
                                        default: 'Smallest accepted increment for this contribution, for example 0.01 for cents.',
                                    })}
                                    position="top"
                                    maxWidth="280px"
                                >
                                    <button type="button" class="inline-flex text-gray-400 hover:text-gray-600 dark:hover:text-gray-200" aria-label={$t('tools.pacAllocator.cash.monetaryStepHint', {default: 'Smallest accepted increment for this contribution, for example 0.01 for cents.'})}>
                                        <Info size={13} />
                                    </button>
                                </Tooltip>
                            </span>
                            <ExactDecimalInput
                                value={money.monetary_step ?? ''}
                                step="0.01"
                                maxIntegerDigits={12}
                                maxFractionDigits={12}
                                placeholder="0,01"
                                ariaLabel={$t('tools.pacAllocator.cash.monetaryStep', {default: 'Amount increment'})}
                                testid={`pac-${kind}-monetary-step-${index}`}
                                className="min-h-9 !px-2 !py-1.5 text-sm"
                                {disabled}
                                onchange={(value) => {
                                    money.monetary_step = value;
                                    onchange();
                                }}
                            />
                        </label>
                    {/if}
                    <Tooltip text={$t('common.remove')} position="top" interactiveChild wrapperClass="col-start-2 row-start-1 self-start sm:col-auto sm:row-auto sm:self-end">
                        <button
                            class="inline-flex h-9 w-9 items-center justify-center rounded-md text-red-600 transition hover:bg-red-50 hover:text-red-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500/70 disabled:cursor-not-allowed disabled:opacity-50 dark:text-red-400 dark:hover:bg-red-950/30 dark:hover:text-red-300"
                            type="button"
                            onclick={() => onremove(index)}
                            {disabled}
                            data-testid={`pac-remove-${kind}-${index}`}
                            aria-label={$t('common.remove')}
                        >
                            <Trash2 size={15} />
                        </button>
                    </Tooltip>
                </div>
            {/each}
        </div>
        <button
            class="mt-3 inline-flex min-h-9 items-center justify-center gap-1.5 rounded-md border border-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 transition hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-libre-green/70 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-200 dark:hover:bg-gray-800"
            type="button"
            onclick={onadd}
            disabled={disabled || values.length >= maxEntries}
            data-testid={`pac-add-${kind}`}
        >
            <Plus size={14} />
            <span>{kind === 'contributions' ? $t('tools.pacAllocator.cash.addContribution', {default: 'Add contribution'}) : $t('tools.pacAllocator.cash.addCurrency')}</span>
        </button>
    {/if}
</article>
