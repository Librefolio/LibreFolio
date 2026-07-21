<!--
  CurrencySearchSelect.svelte - Svelte 5

  Reusable currency selection dropdown using SearchSelect.
  Centralizes the currency loading logic used across the app.

  Features:
  - Loads currencies from the shared currencyStore (session-level cache)
  - Flag emoji as icon, currency symbol shown inline
  - Optional `allowedCurrencies` filter to restrict visible currencies
  - Optional `includeAll` to add an "All currencies" option at the top
  - Searchable by code, name, symbol (€, $, £), country codes (US, GB), and country names
  - Automatically reloads when app language changes (via currentLanguage store)
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import type {CurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {ensureCurrenciesLoaded, getAllCurrencies} from '$lib/stores/reference/currencyStore';
    import {ensureFxRoutesLoaded, getConfiguredCurrencySet, fxRoutesVersion} from '$lib/stores/reference/fxRoutesStore';
    import {SearchSelect, type SelectOption} from '$lib/components/ui/select';

    interface Props {
        /** Selected currency code (bindable) */
        value?: string;
        /** If provided, only these currency codes are shown */
        allowedCurrencies?: string[];
        /** If provided, these currency codes are hidden from the dropdown */
        excludedCurrencies?: Set<string>;
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
        /** Compact mode: single-line display, smaller height to match other selects */
        compact?: boolean;
        /** Asset's native currency — when set and differs from value, shows "Original Value" shortcut */
        originalCurrency?: string;
        /** When true, restrict the list to currencies reachable via a configured FX route
         *  (from fxRoutesStore) — used by target/display currency selectors. The current
         *  value and defaultCurrency are always kept visible. */
        configuredOnly?: boolean;
        /** When set and differs from value, shows a "Back to default" shortcut at the top
         *  (e.g. the user's default currency on the dashboard). */
        defaultCurrency?: string;
        /** Label for the "Create forex…" sticky footer action (passed to SearchSelect). */
        createForexLabel?: string;
        /** Callback fired when the "Create forex…" footer action is clicked. */
        onCreateForex?: () => void;
    }

    let {
        value = $bindable(''),
        allowedCurrencies,
        excludedCurrencies,
        includeAll = false,
        placeholder = '',
        disabled = false,
        loading: externalLoading = false,
        maxVisibleItems = 6,
        dropdownPosition = 'auto',
        onchange,
        compact = false,
        originalCurrency,
        configuredOnly = false,
        defaultCurrency,
        createForexLabel = '',
        onCreateForex,
    }: Props = $props();

    let allCurrencies: CurrencyInfo[] = $state([]);
    let internalLoading = $state(true);
    let error: string | null = $state(null);

    // Filter currencies: allowedCurrencies (include list) then excludedCurrencies (exclude set),
    // then — when configuredOnly — restrict to currencies reachable via a configured FX route
    // (always keeping the current value and defaultCurrency visible).
    let filteredCurrencies = $derived.by(() => {
        // Subscribe to routes version so this recomputes when configured routes load/change.
        void $fxRoutesVersion;
        let list = allowedCurrencies ? allCurrencies.filter((c) => allowedCurrencies!.includes(c.code)) : allCurrencies;
        if (excludedCurrencies && excludedCurrencies.size > 0) {
            list = list.filter((c) => !excludedCurrencies!.has(c.code));
        }
        if (configuredOnly) {
            const configured = getConfiguredCurrencySet();
            list = list.filter((c) => configured.has(c.code) || c.code === value || (defaultCurrency && c.code === defaultCurrency));
        }
        return list;
    });

    // Build SelectOption array — use flag_emoji as icon, symbol + country names in searchText
    let currencyOptions = $derived.by<SelectOption[]>(() => {
        const options: SelectOption[] = [];

        if (includeAll) {
            options.push({
                value: '',
                label: $_('common.allCurrencies'),
                icon: '💱',
                searchText: $_('common.allCurrencies'),
            });
        }

        // "Back to default" shortcut — target/display selectors: jump back to the user's default currency
        const showDefaultShortcut = !!(defaultCurrency && value !== defaultCurrency);
        if (showDefaultShortcut) {
            options.push({
                value: defaultCurrency!,
                label: $_('common.backToDefault') + ' (' + defaultCurrency + ')',
                icon: '↩️',
                searchText: $_('common.backToDefault') + ' ' + defaultCurrency,
            });
        }

        // "Original Value" shortcut — visible when converting away from native currency
        const showOriginalShortcut = !!(originalCurrency && value !== originalCurrency);
        if (showOriginalShortcut) {
            options.push({
                value: originalCurrency,
                label: $_('assetDetail.originalValue') + ' (' + originalCurrency + ')',
                icon: '🔙',
                searchText: $_('assetDetail.originalValue') + ' ' + originalCurrency,
            });
        }

        for (const c of filteredCurrencies) {
            // Skip currency already added as a shortcut to avoid duplicate keys
            if (showOriginalShortcut && c.code === originalCurrency) continue;
            if (showDefaultShortcut && c.code === defaultCurrency) continue;
            // Include symbol in searchText so users can search by € $ £ etc.
            const symbolPart = c.symbol && c.symbol !== c.code ? c.symbol : '';
            // Include country codes (ISO-2) for search
            const countryCodes = (c.country_codes ?? []).join(' ');
            // Use localized country names from backend (Babel) — already in the correct language
            const countryNamesStr = (c.country_names ?? []).join(' ');

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

    // Load currencies when component mounts and reload when language changes
    $effect(() => {
        // Subscribe to currentLanguage — triggers reload when language changes
        const lang = $currentLanguage;
        loadCurrencies(lang);
    });

    // Load configured FX routes when the selector is restricted to configured currencies.
    // Also re-runs when the routes cache is invalidated (fxRoutesVersion bumps) so a newly
    // created pair immediately becomes selectable.
    $effect(() => {
        void $fxRoutesVersion;
        if (configuredOnly) void ensureFxRoutesLoaded();
    });

    async function loadCurrencies(language: string) {
        internalLoading = true;
        error = null;
        try {
            await ensureCurrenciesLoaded(language);
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
    {compact}
    createLabel={createForexLabel}
    {disabled}
    {dropdownPosition}
    dropdownMinWidth={240}
    inlineSearch={true}
    loading={isLoading}
    {maxVisibleItems}
    onchange={handleChange}
    onCreateNew={onCreateForex}
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
        {#if compact}
            <!-- Compact: single-line, same height as standard inputs -->
            <div class="flex items-center gap-1.5 min-w-0">
                {#if option.icon}
                    <span class="text-sm shrink-0 leading-none">{option.icon}</span>
                {/if}
                <span class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                    {option.value || ''}{#if getSymbol(option)}&nbsp;<span class="text-gray-400 text-xs">{getSymbol(option)}</span>{/if}
                </span>
            </div>
        {:else}
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
        {/if}
    {/snippet}
</SearchSelect>
