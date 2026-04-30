<!--
  TransactionTypeSearchSelect.svelte — Specialized SearchSelect for transaction
  types with PNG icons and translated labels.

  Wraps `SearchSelect` with options derived from `TX_TYPES` (or a subset, e.g.
  `STANDALONE_TX_TYPES` for create-flows). Each option renders the type's PNG
  icon plus the i18n label `transactions.types.{TYPE}`. Used in:

  - `TransactionFormModal` (single-row create/duplicate)
  - `TransactionBulkModal` (cell editor for `type` column in create-many)

  Pattern: Svelte 5 runes, dark mode, `data-testid` for E2E.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import SearchSelect from '$lib/components/ui/select/SearchSelect.svelte';
    import type {SelectOption} from '$lib/components/ui/select/types';
    import {TX_TYPES, getTransactionTypeIconUrl, getTypeRule, type TransactionTypeCode} from '$lib/stores/transactionTypeStore';

    interface Props {
        /** Currently selected type. */
        value: TransactionTypeCode;
        /** Disable the select. */
        disabled?: boolean;
        /** Limit options to the given subset. Default: `STANDALONE_TX_TYPES`
         *  (TRANSFER/FX_CONVERSION require the Promote wizard). Pass
         *  `TX_TYPES` to expose pair types too (e.g. read-only display). */
        types?: ReadonlyArray<TransactionTypeCode>;
        /** Placeholder when no value is selected. */
        placeholder?: string;
        /** Compact trigger (smaller padding, text-xs). */
        compact?: boolean;
        /** Test id for E2E targeting. */
        testid?: string;
        /** Change callback. */
        onchange?: (value: TransactionTypeCode) => void;
    }

    let {value = $bindable('BUY' as TransactionTypeCode), disabled = false, types, placeholder, compact = false, testid = 'tx-type-select', onchange}: Props = $props();

    let optionTypes = $derived<ReadonlyArray<TransactionTypeCode>>(types ?? [...TX_TYPES]);

    let options = $derived<SelectOption[]>(
        optionTypes.map((tt) => {
            const label = $t(`transactions.types.${tt}`) || tt;
            const isPair = getTypeRule(tt).requiresPair;
            return {
                value: tt,
                label: isPair ? `↔ ${label}` : label,
                searchText: `${tt} ${label}`,
                icon: getTransactionTypeIconUrl(tt),
            };
        }),
    );

    function handleChange(v: string) {
        value = v as TransactionTypeCode;
        onchange?.(value);
    }

    // Reference TX_TYPES so dead-code analysis doesn't drop the import (consumers
    // pass `TX_TYPES` via the `types` prop to expose pair types).
    void TX_TYPES;
</script>

<div data-testid={testid}>
    <SearchSelect value={value} {options} {disabled} {placeholder} {compact} onchange={handleChange}>
        {#snippet selectedItem(option)}
            <div class="flex items-center gap-2 min-w-0">
                {#if option.icon}
                    <span class="shrink-0 w-7 h-7 flex items-center justify-center bg-libre-green/10 dark:bg-libre-green/20 rounded overflow-hidden">
                    <img src={option.icon} alt="" class="w-5 h-5 object-contain" onerror={(e) => { const el = e.currentTarget; if (el instanceof HTMLImageElement) el.style.display = 'none'; }} />
                </span>
            {/if}
            <span class="font-medium text-gray-900 dark:text-gray-100 truncate text-sm">{option.label}</span>
        </div>
    {/snippet}
    {#snippet item(option)}
        <div class="flex items-center gap-2 min-w-0">
            {#if option.icon}
                <img src={option.icon} alt="" class="w-4 h-4 object-contain shrink-0" onerror={(e) => { const el = e.currentTarget; if (el instanceof HTMLImageElement) el.style.display = 'none'; }} />
                {/if}
                <span class="truncate text-sm flex-1 min-w-0">{option.label}</span>
                <span class="hidden sm:inline text-[10px] font-mono uppercase opacity-50 shrink-0">{option.value}</span>
            </div>
        {/snippet}
    </SearchSelect>
</div>

