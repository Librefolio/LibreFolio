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
  - A stored value that is no currency of the list (`978`, `EURO`: what an earlier version saved as written, E-19b1)
    stays in the field, with a warning and the ISO code it stands for (`currency-non-iso-hint`); it is never offered
    as a choice
-->
<script lang="ts">
    import {untrack} from 'svelte';
    import {AlertTriangle} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import type {CurrencyInfo, CurrencySuggestion} from '$lib/stores/reference/currencyStore';
    import {ensureCurrenciesLoaded, getAllCurrencies, suggestCurrency} from '$lib/stores/reference/currencyStore';
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
        /** Stable selector forwarded to SearchSelect. */
        testId?: string;
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
        testId,
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

    // A stored value that is no currency of the list (E-19b1): `978` or `EURO`, which an earlier version saved as
    // written. Judged against the whole list, never the filtered one (an ISO code a filter hides is no such value), and
    // only once the list has loaded: an empty list is a failed load, not a verdict on every value.
    let unknownValue = $derived(!internalLoading && allCurrencies.length > 0 && !!value && !allCurrencies.some((c) => c.code === value));
    /** The value the suggestion was asked for, and its answer (null while it is on its way). */
    let suggestionFor = $state('');
    let suggestionInfo: CurrencySuggestion | null = $state(null);

    $effect(() => {
        if (!unknownValue) return;
        const asked = value;
        if (asked === untrack(() => suggestionFor)) return;
        suggestionFor = asked;
        suggestionInfo = null;
        void askSuggestion(asked).then((info) => {
            if (untrack(() => suggestionFor) === asked) suggestionInfo = info;
        });
    });

    /** The store never rejects; a caller's double might: a failure reads as "no suggestion". */
    async function askSuggestion(asked: string): Promise<CurrencySuggestion> {
        try {
            return await suggestCurrency(asked);
        } catch {
            return {canonical: false, suggestion: null, candidates: []};
        }
    }

    /** What the field says of a stored value that is no ISO code: the code it stands for, the codes it may, or neither. */
    let nonIsoText = $derived.by(() => {
        const info = suggestionInfo;
        if (info?.suggestion) return $_('common.nonIsoCurrency.suggestion', {values: {value, suggestion: info.suggestion}});
        if (info && info.candidates.length > 1) return $_('common.nonIsoCurrency.candidates', {values: {value, candidates: info.candidates.join(', ')}});
        return $_('common.nonIsoCurrency.unknown', {values: {value}});
    });

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

        // The stored value that is no currency of the list: shown in the field, never a choice (E-19b1). Until the
        // suggestion answers, and when it calls the value canonical (an ISO code the list lacks), it is shown as it is.
        if (unknownValue) {
            const nonIso = suggestionInfo !== null && !suggestionInfo.canonical;
            options.push({
                value,
                label: nonIso ? nonIsoText : '',
                disabled: true,
                searchText: value,
                data: {nonIso, suggestion: (nonIso && suggestionInfo?.suggestion) || ''},
            });
        }

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

    /** The stored value that is no ISO code (E-19b1), and the code it stands for ('' when none or several). */
    function nonIsoOf(option: SelectOption): {nonIso: boolean; suggestion: string} {
        const d = option.data as Record<string, unknown> | undefined;
        return {nonIso: d?.nonIso === true, suggestion: typeof d?.suggestion === 'string' ? d.suggestion : ''};
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
    {testId}
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
                <div class="text-sm font-medium text-lf-primary">
                    {option.value || ''}
                    {#if getSymbol(option)}
                        <span class="text-lf-muted ml-0.5 text-xs">{getSymbol(option)}</span>
                    {/if}
                </div>
                <div class="text-xs text-lf-muted truncate" title={option.label}>{option.label}</div>
            </div>
        </div>
    {/snippet}
    {#snippet selectedItem(option)}
        {#if nonIsoOf(option).nonIso}
            <!-- A stored value that is no ISO code (E-19b1): the value, a warning, and what it stands for -->
            {#if compact}
                <div class="flex items-center gap-1.5 min-w-0" title={option.label}>
                    <AlertTriangle class="shrink-0 text-lf-warning" size={14} aria-hidden="true" />
                    <span class="text-sm font-medium text-lf-primary truncate">{option.value}</span>
                    <span class="sr-only" data-testid="currency-non-iso-hint" data-suggestion={nonIsoOf(option).suggestion}>{option.label}</span>
                </div>
            {:else}
                <div class="flex items-center space-x-2 min-w-0">
                    <AlertTriangle class="shrink-0 text-lf-warning" size={16} aria-hidden="true" />
                    <div class="min-w-0">
                        <div class="text-sm font-medium text-lf-primary">{option.value}</div>
                        <div class="text-xs text-lf-warning truncate" title={option.label} data-testid="currency-non-iso-hint" data-suggestion={nonIsoOf(option).suggestion}>
                            {option.label}
                        </div>
                    </div>
                </div>
            {/if}
        {:else if compact}
            <!-- Compact: single-line, same height as standard inputs -->
            <div class="flex items-center gap-1.5 min-w-0">
                {#if option.icon}
                    <span class="text-sm shrink-0 leading-none">{option.icon}</span>
                {/if}
                <span class="text-sm font-medium text-lf-primary truncate">
                    {option.value || ''}{#if getSymbol(option)}&nbsp;<span class="text-lf-muted text-xs">{getSymbol(option)}</span>{/if}
                </span>
            </div>
        {:else}
            <div class="flex items-center space-x-2 min-w-0">
                {#if option.icon}
                    <span class="text-base shrink-0 leading-none">{option.icon}</span>
                {/if}
                <div class="min-w-0">
                    <div class="text-sm font-medium text-lf-primary">
                        {option.value || ''}
                        {#if getSymbol(option)}
                            <span class="text-lf-muted ml-0.5 text-xs">{getSymbol(option)}</span>
                        {/if}
                    </div>
                    <div class="text-xs text-lf-muted truncate" title={option.label}>{option.label}</div>
                </div>
            </div>
        {/if}
    {/snippet}
</SearchSelect>
