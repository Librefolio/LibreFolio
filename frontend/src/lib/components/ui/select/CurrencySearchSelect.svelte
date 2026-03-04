<!--
  CurrencySearchSelect.svelte - Svelte 5

  Reusable currency selection dropdown using SearchSelect.
  Centralizes the currency loading logic used across the app.

  Features:
  - Loads currencies from the shared currencyStore (session-level cache)
  - Flag emoji as icon, currency symbol shown inline
  - Optional `allowedCurrencies` filter to restrict visible currencies
  - Optional `includeAll` to add an "All currencies" option at the top
  - Searchable by code, name, and symbol (€, $, £, etc.)
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {ensureCurrenciesLoaded, getAllCurrencies} from '$lib/stores/currencyStore';
    import type {CurrencyInfo} from '$lib/stores/currencyStore';
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
        onchange
    }: Props = $props();

    let allCurrencies = $state<CurrencyInfo[]>([]);
    let internalLoading = $state(true);
    let error = $state<string | null>(null);

    // Filter currencies if allowedCurrencies is provided
    let filteredCurrencies = $derived(
        allowedCurrencies
            ? allCurrencies.filter(c => allowedCurrencies!.includes(c.code))
            : allCurrencies
    );

    // Build SelectOption array — use flag_emoji as icon, symbol + country names in searchText
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

        // Use browser Intl.DisplayNames for localized country names (e.g., "IT" → "Italia")
        let countryNames: Intl.DisplayNames | null = null;
        try {
            countryNames = new Intl.DisplayNames(navigator.language || 'en', {type: 'region'});
        } catch {
            // Fallback: no country name resolution
        }

        for (const c of filteredCurrencies) {
            // Include symbol in searchText so users can search by € $ £ etc.
            const symbolPart = c.symbol && c.symbol !== c.code ? c.symbol : '';
            // Include country codes (ISO-2) and localized country names for search
            const countryCodes = (c.country_codes ?? []).join(' ');
            const countryNamesStr = (c.country_codes ?? [])
                .map(cc => {
                    try { return countryNames?.of(cc) ?? ''; } catch { return ''; }
                })
                .filter(Boolean)
                .join(' ');

            options.push({
                value: c.code,
                label: `${c.code} — ${c.name}`,
                icon: c.flag_emoji || symbolPart || undefined,
                searchText: `${c.code} ${c.name} ${symbolPart} ${countryCodes} ${countryNamesStr}`.trim(),
                data: {symbol: c.symbol},
            });
        }

        return options;
    });

    let isLoading = $derived(internalLoading || externalLoading);

    // Load currencies once via shared store
    $effect(() => {
        loadCurrencies();
    });

    async function loadCurrencies() {
        internalLoading = true;
        error = null;
        try {
            await ensureCurrenciesLoaded();
            allCurrencies = getAllCurrencies();
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

    /** Helper to extract symbol from option data (avoids 'as any' in template) */
    function getSymbol(option: SelectOption): string | undefined {
        const d = option.data as Record<string, unknown> | undefined;
        const sym = d?.symbol as string | undefined;
        return sym && sym !== option.value ? sym : undefined;
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
                <span class="text-base shrink-0 leading-none">{option.icon}</span>
            {/if}
            <div class="min-w-0">
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {option.value || ''}
                    {#if getSymbol(option)}
                        <span class="text-gray-400 ml-0.5 text-xs">{getSymbol(option)}</span>
                    {/if}
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400 truncate" title={option.label}>{option.label}</div>
            </div>
        </div>
    {/snippet}
    {#snippet selectedItem(option)}
        <div class="flex items-center space-x-2 min-w-0">
            {#if option.icon}
                <span class="text-base shrink-0 leading-none">{option.icon}</span>
            {/if}
            <div class="min-w-0">
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {option.value || ''}
                    {#if getSymbol(option)}
                        <span class="text-gray-400 ml-0.5 text-xs">{getSymbol(option)}</span>
                    {/if}
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400 truncate" title={option.label}>{option.label}</div>
            </div>
        </div>
    {/snippet}
</SearchSelect>

