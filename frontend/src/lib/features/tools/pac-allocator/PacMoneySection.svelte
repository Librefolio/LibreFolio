<script lang="ts">
    import {t} from '$lib/i18n';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import type {SelectOption} from '$lib/components/ui/select';
    import {AlertTriangle, Check, LoaderCircle, Plus, RefreshCw, Trash2} from 'lucide-svelte';
    import type {PacAllocationSourceCashSource} from './allocationSource';
    import type {PacCashSourceState, PacContributionInput, PacContributionMode, PacMoneyInput} from './editorTypes';

    type CashMode = PacCashSourceState['mode'];
    type MoneyMode = CashMode | PacContributionMode;
    type PacMoneyEditorValue = PacMoneyInput & {monetary_step?: PacContributionInput['monetary_step']};

    interface Props {
        kind: 'cash' | 'contributions';
        title: string;
        description: string;
        mode: MoneyMode;
        values: PacMoneyEditorValue[];
        cashSources?: readonly PacAllocationSourceCashSource[];
        selectedBrokerIds?: readonly number[];
        aggregatedBalances?: readonly PacMoneyInput[];
        sourceLoading?: boolean;
        sourceError?: string | null;
        sourceStale?: boolean;
        disabled?: boolean;
        onmodechange: (mode: MoneyMode) => void;
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
        aggregatedBalances = [],
        sourceLoading = false,
        sourceError = null,
        sourceStale = false,
        disabled = false,
        onmodechange,
        onadd,
        onremove,
        onchange,
        onbrokertoggle = () => {},
        onretry = () => {},
    }: Props = $props();

    let modeOptions = $derived<SelectOption[]>([
        {value: 'not_supplied', label: $t('tools.pacAllocator.cash.notSupplied')},
        {value: 'none', label: $t('tools.pacAllocator.cash.noneContributions')},
        {value: 'custom', label: $t('tools.pacAllocator.cash.enterAmounts')},
    ]);

    function parseContributionMode(value: string): PacContributionMode {
        if (value === 'none' || value === 'custom') return value;
        return 'not_supplied';
    }

    function isSelected(brokerId: number): boolean {
        return selectedBrokerIds.includes(brokerId);
    }
</script>

<article class="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800/60" data-testid={`pac-${kind}`}>
    <div class="grid gap-3 {kind === 'cash' ? '' : 'sm:grid-cols-[minmax(0,1fr)_minmax(12rem,16rem)] sm:items-start'}">
        <div>
            <h3 class="text-base font-semibold text-gray-900 dark:text-white">{title}</h3>
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">{description}</p>
        </div>
        {#if kind === 'cash'}
            <div class="grid grid-cols-2 gap-2 sm:grid-cols-4" role="group" aria-label={title} data-testid="pac-cash-mode">
                <button class="btn {mode === 'not_supplied' ? 'btn-primary' : 'btn-secondary'} justify-center px-2" type="button" aria-pressed={mode === 'not_supplied'} {disabled} onclick={() => onmodechange('not_supplied')} data-testid="pac-cash-mode-not-supplied">
                    {$t('tools.pacAllocator.cash.notSupplied')}
                </button>
                <button class="btn {mode === 'none' ? 'btn-primary' : 'btn-secondary'} justify-center px-2" type="button" aria-pressed={mode === 'none'} {disabled} onclick={() => onmodechange('none')} data-testid="pac-cash-mode-none">
                    {$t('tools.pacAllocator.cash.noneExisting')}
                </button>
                <button class="btn {mode === 'broker_copy' ? 'btn-primary' : 'btn-secondary'} justify-center px-2" type="button" aria-pressed={mode === 'broker_copy'} {disabled} onclick={() => onmodechange('broker_copy')} data-testid="pac-cash-mode-broker-copy">
                    {$t('tools.pacAllocator.cash.fromBrokers', {default: 'From brokers'})}
                </button>
                <button class="btn {mode === 'manual' ? 'btn-primary' : 'btn-secondary'} justify-center px-2" type="button" aria-pressed={mode === 'manual'} {disabled} onclick={() => onmodechange('manual')} data-testid="pac-cash-mode-manual">
                    {$t('tools.pacAllocator.manual')}
                </button>
            </div>
        {:else}
            <SimpleSelect value={mode} options={modeOptions} ariaLabel={title} testId={`pac-${kind}-mode`} matchTriggerWidth dropdownPosition="auto" {disabled} onchange={(value) => onmodechange(parseContributionMode(value))} />
        {/if}
    </div>

    {#if mode === 'not_supplied'}
        <p class="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-950/20 dark:text-amber-200" data-testid={`pac-${kind}-not-supplied`}>{$t('tools.pacAllocator.cash.notSuppliedHint')}</p>
    {:else if mode === 'none'}
        <p class="mt-3 rounded-lg bg-gray-50 px-3 py-2 text-xs text-gray-600 dark:bg-gray-900/60 dark:text-gray-300" data-testid={`pac-${kind}-none`}>
            {kind === 'cash' ? $t('tools.pacAllocator.cash.noneExisting') : $t('tools.pacAllocator.cash.noneContributions')}
        </p>
    {:else if kind === 'cash' && mode === 'broker_copy'}
        <div class="mt-4 space-y-3" data-testid="pac-cash-broker-copy">
            {#if sourceLoading && cashSources.length === 0}
                <div class="flex min-h-24 items-center justify-center gap-2 rounded-xl border border-gray-200 bg-gray-50 text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900/40 dark:text-gray-400" data-testid="pac-cash-sources-loading">
                    <LoaderCircle class="animate-spin" size={18} />
                    <span>{$t('tools.pacAllocator.cash.loadingBrokerCash', {default: 'Loading broker cash balances…'})}</span>
                </div>
            {:else if cashSources.length === 0}
                <div class="rounded-xl border border-dashed border-gray-300 px-4 py-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400" data-testid="pac-cash-sources-empty">
                    {$t('tools.pacAllocator.cash.noOwnerBrokers', {default: 'No OWNER brokers are available. Use manual cash entry instead.'})}
                </div>
            {:else}
                <div class="grid gap-2 sm:grid-cols-2 xl:grid-cols-3" data-testid="pac-cash-sources">
                    {#each cashSources as source (source.brokerId)}
                        {@const selected = isSelected(source.brokerId)}
                        <button
                            type="button"
                            class="relative flex min-h-24 items-start gap-3 rounded-xl border p-3 text-left transition focus:outline-none focus:ring-2 focus:ring-libre-green/50 {selected
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
                                        <span class="block text-[11px] text-gray-500 dark:text-gray-400">{source.ownershipSharePercent}% {$t('tools.pacAllocator.personalShare')}</span>
                                    </span>
                                    <span class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border {selected ? 'border-libre-green bg-libre-green text-white' : 'border-gray-300 text-transparent dark:border-gray-600'}">
                                        <Check size={13} strokeWidth={3} />
                                    </span>
                                </span>
                                <span class="mt-2 flex flex-wrap gap-1.5 text-[11px]">
                                    {#each source.balances as balance (`${source.brokerId}:${balance.currency}`)}
                                        <span class="rounded-full bg-gray-100 px-2 py-0.5 text-gray-700 dark:bg-gray-800 dark:text-gray-200">{balance.currency} {balance.amount}</span>
                                    {:else}
                                        <span class="text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.cash.noNativeBalances', {default: 'No native balances'})}</span>
                                    {/each}
                                </span>
                            </span>
                        </button>
                    {/each}
                </div>
            {/if}

            {#if sourceError}
                <div class="flex items-center justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800 dark:border-red-900/60 dark:bg-red-950/20 dark:text-red-200" role="alert" data-testid="pac-cash-source-error">
                    <span>{sourceError}</span>
                    <button class="btn btn-ghost shrink-0" type="button" onclick={onretry} disabled={sourceLoading} data-testid="pac-cash-source-retry">
                        <RefreshCw class={sourceLoading ? 'animate-spin' : ''} size={14} />
                        <span class="hidden sm:inline">{$t('common.retry')}</span>
                    </button>
                </div>
            {/if}

            <div class="rounded-xl border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-900/50" data-testid="pac-cash-backend-aggregate">
                <div class="flex items-center justify-between gap-3">
                    <span class="text-xs font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300">{$t('tools.pacAllocator.cash.backendAggregate', {default: 'Backend aggregate'})}</span>
                    {#if sourceLoading}
                        <LoaderCircle class="animate-spin text-gray-400" size={15} />
                    {/if}
                </div>
                {#if sourceStale}
                    <p class="mt-2 flex items-start gap-2 text-xs text-amber-800 dark:text-amber-200" data-testid="pac-cash-source-stale">
                        <AlertTriangle class="mt-0.5 shrink-0" size={14} />
                        <span>{$t('tools.pacAllocator.cash.sourceStale', {default: 'Waiting for current broker balances. The previous snapshot will not be submitted.'})}</span>
                    </p>
                {:else}
                    <div class="mt-2 flex flex-wrap gap-2">
                        {#each aggregatedBalances as balance (balance.currency)}
                            <span class="rounded-full bg-white px-2.5 py-1 text-sm font-medium text-gray-800 shadow-sm dark:bg-gray-800 dark:text-gray-100" data-testid={`pac-cash-aggregate-${balance.currency}`}>
                                {balance.currency}
                                {balance.amount}
                            </span>
                        {:else}
                            <span class="text-xs text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.cash.noSelectedBalances', {default: 'No selected broker balance.'})}</span>
                        {/each}
                    </div>
                {/if}
            </div>
        </div>
    {:else}
        <div class="mt-3 space-y-2">
            {#each values as money, index}
                <div class={kind === 'contributions' ? 'grid grid-cols-[minmax(0,1fr)_auto] gap-2 sm:grid-cols-[minmax(8rem,1fr)_minmax(0,2fr)_minmax(0,2fr)_auto]' : 'grid grid-cols-[minmax(8rem,1fr)_minmax(0,2fr)_auto] gap-2'} data-testid={`pac-${kind}-row`}>
                    <div class={kind === 'contributions' ? 'col-start-1 row-start-1 sm:col-auto sm:row-auto' : ''}>
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
                    </div>
                    <div class={kind === 'contributions' ? 'col-start-1 row-start-2 sm:col-auto sm:row-auto' : ''}>
                        <ExactDecimalInput
                            value={money.amount ?? ''}
                            step="0.01"
                            maxIntegerDigits={12}
                            maxFractionDigits={12}
                            placeholder={$t('tools.pacAllocator.cash.amount')}
                            ariaLabel={$t('tools.pacAllocator.cash.amount')}
                            testid={`pac-${kind}-amount-${index}`}
                            {disabled}
                            onchange={(value) => {
                                money.amount = value;
                                onchange();
                            }}
                        />
                    </div>
                    {#if kind === 'contributions'}
                        <div class="col-start-1 row-start-3 sm:col-auto sm:row-auto">
                            <ExactDecimalInput
                                value={money.monetary_step ?? ''}
                                step="0.01"
                                maxIntegerDigits={12}
                                maxFractionDigits={12}
                                placeholder="0.01"
                                ariaLabel={$t('tools.pacAllocator.cash.monetaryStep', {default: 'Monetary step'})}
                                testid={`pac-${kind}-monetary-step-${index}`}
                                {disabled}
                                onchange={(value) => {
                                    money.monetary_step = value;
                                    onchange();
                                }}
                            />
                        </div>
                    {/if}
                    <button
                        class={`btn btn-danger px-2 ${kind === 'contributions' ? 'col-start-2 row-start-1 row-span-3 self-start sm:col-auto sm:row-auto sm:row-span-1 sm:self-auto' : ''}`}
                        type="button"
                        onclick={() => onremove(index)}
                        {disabled}
                        data-testid={`pac-remove-${kind}-${index}`}
                        aria-label={$t('common.remove')}
                    >
                        <Trash2 size={15} />
                    </button>
                </div>
            {/each}
        </div>
        <button class="btn btn-secondary mt-3" type="button" onclick={onadd} disabled={disabled || values.length >= 4} data-testid={`pac-add-${kind}`}>
            <Plus size={14} />
            <span>{$t('tools.pacAllocator.cash.addCurrency')}</span>
        </button>
    {/if}
</article>
