<script lang="ts">
    import {_} from '$lib/i18n';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import type {SelectOption} from '$lib/components/ui/select';
    import {Plus, Trash2} from 'lucide-svelte';
    import type {PacMoneyInput} from './editorTypes';

    type MoneyMode = 'not_supplied' | 'none' | 'custom';

    interface Props {
        kind: 'cash' | 'contributions';
        title: string;
        description: string;
        mode: MoneyMode;
        values: PacMoneyInput[];
        disabled?: boolean;
        onmodechange: (mode: MoneyMode) => void;
        onadd: () => void;
        onremove: (index: number) => void;
        onchange: () => void;
    }

    let {kind, title, description, mode, values = $bindable(), disabled = false, onmodechange, onadd, onremove, onchange}: Props = $props();

    let modeOptions = $derived<SelectOption[]>([
        {value: 'not_supplied', label: $_('tools.pacAllocator.cash.notSupplied')},
        {value: 'none', label: kind === 'cash' ? $_('tools.pacAllocator.cash.noneExisting') : $_('tools.pacAllocator.cash.noneContributions')},
        {value: 'custom', label: $_('tools.pacAllocator.cash.enterAmounts')},
    ]);

    function parseMode(value: string): MoneyMode {
        if (value === 'none' || value === 'custom') return value;
        return 'not_supplied';
    }
</script>

<article class="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800/60" data-testid={`pac-${kind}`}>
    <div class="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(12rem,16rem)] sm:items-start">
        <div>
            <h3 class="text-base font-semibold text-gray-900 dark:text-white">{title}</h3>
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">{description}</p>
        </div>
        <SimpleSelect value={mode} options={modeOptions} ariaLabel={title} testId={`pac-${kind}-mode`} matchTriggerWidth dropdownPosition="auto" {disabled} onchange={(value) => onmodechange(parseMode(value))} />
    </div>

    {#if mode === 'not_supplied'}
        <p class="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-950/20 dark:text-amber-200" data-testid={`pac-${kind}-not-supplied`}>{$_('tools.pacAllocator.cash.notSuppliedHint')}</p>
    {:else if mode === 'none'}
        <p class="mt-3 rounded-lg bg-gray-50 px-3 py-2 text-xs text-gray-600 dark:bg-gray-900/60 dark:text-gray-300" data-testid={`pac-${kind}-none`}>
            {kind === 'cash' ? $_('tools.pacAllocator.cash.noneExisting') : $_('tools.pacAllocator.cash.noneContributions')}
        </p>
    {:else}
        <div class="mt-3 space-y-2">
            {#each values as money, index}
                <div class="grid grid-cols-[minmax(8rem,1fr)_minmax(0,2fr)_auto] gap-2" data-testid={`pac-${kind}-row`}>
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
                    <ExactDecimalInput
                        value={money.amount ?? ''}
                        step="0.01"
                        maxIntegerDigits={12}
                        maxFractionDigits={12}
                        placeholder={$_('tools.pacAllocator.cash.amount')}
                        ariaLabel={$_('tools.pacAllocator.cash.amount')}
                        testid={`pac-${kind}-amount-${index}`}
                        {disabled}
                        onchange={(value) => {
                            money.amount = value;
                            onchange();
                        }}
                    />
                    <button class="btn btn-danger px-2" type="button" onclick={() => onremove(index)} {disabled} data-testid={`pac-remove-${kind}-${index}`} aria-label={$_('common.remove')}>
                        <Trash2 size={15} />
                    </button>
                </div>
            {/each}
        </div>
        <button class="btn btn-secondary mt-3" type="button" onclick={onadd} disabled={disabled || values.length >= 4} data-testid={`pac-add-${kind}`}>
            <Plus size={14} />
            <span>{$_('tools.pacAllocator.cash.addCurrency')}</span>
        </button>
    {/if}
</article>
