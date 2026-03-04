<!--
  CurrencySearchSelect.svelte - Svelte 5

  Reusable currency selection dropdown using SearchSelect.
  Centralizes the currency loading logic used across the app.

  Features:
  - Loads currencies from the utilities API
  - Optional `allowedCurrencies` filter to restrict visible currencies
  - Optional `includeAll` to add an "All currencies" option at the top
  - Currency symbol as icon in each option
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {SearchSelect, type SelectOption} from '$lib/components/ui/select';

    interface Props {
        /** Selected currency code (bindable) */
        value?: string;
        /** If provided, only these currency codes are shown */
        allowedCurrencies?: string[];
        /** If true, adds "All currencies" as first option with value '' */
        includeAll?: boolean;
        /** Custom placeholder text */
        placeholder?: string;
        /** Disable the select */
        disabled?: boolean;
        /** Loading state override (combined with internal loading) */
        loading?: boolean;
        /** Max items visible in dropdown */
        maxVisibleItems?: number;
        /** Dropdown position */
        dropdownPosition?: 'top' | 'bottom' | 'auto';
        /** Compact mode — smaller icons and text for use in modals/tight spaces */
        compact?: boolean;
        /** Change callback */
        onchange?: (value: string) => void;
    }

    let {
        value = $bindable(''),
        allowedCurrencies,
        includeAll = false,
        placeholder = '',
        disabled = false,
        loading: externalLoading = false,
        maxVisibleItems = 6,
        dropdownPosition = 'auto',
        compact = false,
        onchange
    }: Props = $props();

    interface CurrencyItem {
        code: string;
        name: string;
        symbol?: string;
    }

    let allCurrencies = $state<CurrencyItem[]>([]);
    let internalLoading = $state(true);
    let error = $state<string | null>(null);

    // Filter currencies if allowedCurrencies is provided
    let filteredCurrencies = $derived(
        allowedCurrencies
            ? allCurrencies.filter(c => allowedCurrencies!.includes(c.code))
            : allCurrencies
    );

    // Build SelectOption array
    let currencyOptions = $derived.by<SelectOption[]>(() => {
        const options: SelectOption[] = [];

        if (includeAll) {
            options.push({
                value: '',
                label: $_('fx.filter.allCurrencies'),
                icon: '💱',
                searchText: $_('fx.filter.allCurrencies'),
            });
        }

        for (const c of filteredCurrencies) {
            options.push({
                value: c.code,
                label: `${c.code} — ${c.name}`,
                icon: c.symbol && c.symbol !== c.code ? c.symbol : undefined,
                searchText: `${c.code} ${c.name}`,
            });
        }

        return options;
    });

    let isLoading = $derived(internalLoading || externalLoading);

    // Load currencies once on mount
    $effect(() => {
        loadCurrencies();
    });

    async function loadCurrencies() {
        internalLoading = true;
        error = null;
        try {
            const response = await zodiosApi.list_currencies_api_v1_utilities_currencies_get();
            allCurrencies = (response.items ?? []).map((c: any) => ({
                code: c.code,
                name: c.name,
                symbol: c.symbol,
            }));
        } catch (e) {
            console.error('Failed to load currencies:', e);
            error = 'Failed to load currencies';
        } finally {
            internalLoading = false;
        }
    }

    function handleChange(newValue: string) {
        value = newValue;
        onchange?.(newValue);
    }
</script>

<SearchSelect
    bind:value
    {disabled}
    {dropdownPosition}
    inlineSearch={true}
    loading={isLoading}
    {maxVisibleItems}
    onchange={handleChange}
    options={currencyOptions}
    placeholder={placeholder || $_('fx.filter.filterCurrency')}
>
    {#snippet item(option)}
        <div class="flex items-center space-x-2 min-w-0">
            {#if option.icon}
                <span class="{compact ? 'text-sm w-6 h-6' : 'text-lg w-9 h-9'} shrink-0 flex items-center justify-center bg-libre-green/20 text-libre-green rounded-lg font-medium">
                    {option.icon}
                </span>
            {/if}
            <div class="min-w-0">
                <div class="{compact ? 'text-sm' : ''} font-medium text-gray-900 dark:text-gray-100">{option.value || ''}</div>
                <div class="text-xs text-gray-500 dark:text-gray-400 truncate">{option.label}</div>
            </div>
        </div>
    {/snippet}
    {#snippet selectedItem(option)}
        <div class="flex items-center space-x-2 min-w-0">
            {#if option.icon}
                <span class="{compact ? 'text-sm w-6 h-6' : 'text-lg w-9 h-9'} shrink-0 flex items-center justify-center bg-libre-green/20 text-libre-green rounded-lg font-medium">
                    {option.icon}
                </span>
            {/if}
            <div class="min-w-0">
                <div class="{compact ? 'text-sm' : ''} font-medium text-gray-900 dark:text-gray-100">{option.value || ''}</div>
                <div class="text-xs text-gray-500 dark:text-gray-400 truncate">{option.label}</div>
            </div>
        </div>
    {/snippet}
</SearchSelect>

