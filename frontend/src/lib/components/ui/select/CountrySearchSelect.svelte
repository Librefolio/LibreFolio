<!--
  CountrySearchSelect.svelte - Svelte 5

  Reusable country selection dropdown using SearchSelect.
  Centralizes the country loading logic used by DistributionEditor (geographic).

  Features:
  - Loads countries from the shared countryStore (session-level cache)
  - Flag emoji as icon, ISO3 code + localized name
  - Optional `excludedCountries` filter to hide already-selected countries
  - Searchable by ISO3, ISO2, and localized name
  - Automatically reloads when app language changes (via currentLanguage store)
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import type {CountryInfo} from '$lib/stores/reference/countryStore';
    import {ensureCountriesLoaded, getAllCountries} from '$lib/stores/reference/countryStore';
    import {SearchSelect, type SelectOption} from '$lib/components/ui/select';

    interface Props {
        /** Selected country ISO3 code (bindable) */
        value?: string;
        /** If provided, these ISO3 codes are hidden from the dropdown */
        excludedCountries?: Set<string>;
        /** Custom placeholder text */
        placeholder?: string;
        /** Disable the select */
        disabled?: boolean;
        /** Max items visible in dropdown */
        maxVisibleItems?: number;
        /** Dropdown position */
        dropdownPosition?: 'top' | 'bottom' | 'auto';
        /** Change callback */
        onchange?: (value: string) => void;
        /** Compact mode: single-line display, smaller height to match standard inputs */
        compact?: boolean;
    }

    let {value = $bindable(''), excludedCountries, placeholder = '', disabled = false, maxVisibleItems = 6, dropdownPosition = 'auto', onchange, compact = false}: Props = $props();

    let allCountriesLocal = $state<CountryInfo[]>([]);
    let internalLoading = $state(true);

    // Filter out excluded countries
    let filteredCountries = $derived.by(() => {
        if (excludedCountries && excludedCountries.size > 0) {
            return allCountriesLocal.filter((c) => !excludedCountries!.has(c.iso3));
        }
        return allCountriesLocal;
    });

    // Build SelectOption array — flag emoji as icon, name in searchText
    let countryOptions = $derived.by<SelectOption[]>(() => {
        return filteredCountries.map((c) => ({
            value: c.iso3,
            label: `${c.iso3} — ${c.name}`,
            icon: c.flag_emoji || undefined,
            searchText: `${c.iso3} ${c.iso2} ${c.name}`.trim(),
        }));
    });

    // Load countries when component mounts and reload when language changes
    $effect(() => {
        const lang = $currentLanguage;
        loadCountries(lang);
    });

    async function loadCountries(language: string) {
        internalLoading = true;
        try {
            await ensureCountriesLoaded(language);
            allCountriesLocal = getAllCountries();
        } catch (e) {
            console.error('Failed to load countries:', e);
        } finally {
            internalLoading = false;
        }
    }

    function handleChange(newValue: string) {
        value = newValue;
        onchange?.(newValue);
    }
</script>

<SearchSelect bind:value {compact} {disabled} {dropdownPosition} inlineSearch={true} loading={internalLoading} {maxVisibleItems} onchange={handleChange} options={countryOptions} placeholder={placeholder || $_('assets.distribution.addCountry')}>
    {#snippet item(option)}
        <div class="flex items-center space-x-2 min-w-0">
            {#if option.icon}
                <span class="text-base shrink-0 leading-none">{option.icon}</span>
            {/if}
            <div class="min-w-0">
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {option.value || ''}
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400 truncate" title={option.label}>{option.label}</div>
            </div>
        </div>
    {/snippet}
    {#snippet selectedItem(option)}
        {#if compact}
            <div class="flex items-center gap-1.5 min-w-0">
                {#if option.icon}
                    <span class="text-sm shrink-0 leading-none">{option.icon}</span>
                {/if}
                <span class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{option.value || ''}</span>
            </div>
        {:else}
            <div class="flex items-center space-x-2 min-w-0">
                {#if option.icon}
                    <span class="text-base shrink-0 leading-none">{option.icon}</span>
                {/if}
                <div class="min-w-0">
                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {option.value || ''}
                    </div>
                    <div class="text-xs text-gray-500 dark:text-gray-400 truncate" title={option.label}>{option.label}</div>
                </div>
            </div>
        {/if}
    {/snippet}
</SearchSelect>
