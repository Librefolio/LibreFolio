<!--
  SectorSearchSelect.svelte - Svelte 5

  Reusable sector selection dropdown using SearchSelect.
  Centralizes the sector loading logic used by DistributionEditor (sector).

  Features:
  - Loads sectors from the shared sectorStore (session-level cache)
  - Localized sector names via i18n
  - Optional `excludedSectors` filter to hide already-selected sectors
  - Searchable by sector key and localized name
  - Includes "Other" from backend (include_other: true)
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {ensureSectorsLoaded} from '$lib/stores/reference/sectorStore';
    import {getSectorKeysList, sectorI18nKey} from '$lib/utils/assetTypes';
    import {SearchSelect, type SelectOption} from '$lib/components/ui/select';

    interface Props {
        /** Selected sector key (bindable) */
        value?: string;
        /** If provided, these sector keys are hidden from the dropdown */
        excludedSectors?: Set<string>;
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

    let {value = $bindable(''), excludedSectors, placeholder = '', disabled = false, maxVisibleItems = 6, dropdownPosition = 'auto', onchange, compact = false}: Props = $props();

    let sectorsLoaded = $state(false);

    // Load sectors on mount
    $effect(() => {
        loadSectors();
    });

    async function loadSectors() {
        try {
            await ensureSectorsLoaded();
            sectorsLoaded = true;
        } catch (e) {
            console.error('Failed to load sectors:', e);
        }
    }

    // Build options from sector keys
    let allSectorKeys = $derived(sectorsLoaded ? getSectorKeysList() : getSectorKeysList());

    // Filter out excluded sectors
    let filteredKeys = $derived.by(() => {
        if (excludedSectors && excludedSectors.size > 0) {
            return allSectorKeys.filter((k) => !excludedSectors!.has(k));
        }
        return allSectorKeys;
    });

    // Build SelectOption array — sector name localized, searchable by key + name
    let sectorOptions = $derived.by<SelectOption[]>(() => {
        return filteredKeys.map((k) => {
            const i18nKey = `sectors.${sectorI18nKey(k)}`;
            const localized = $t(i18nKey);
            const label = localized !== i18nKey ? localized : k;
            return {
                value: k,
                label,
                searchText: `${k} ${label}`.trim(),
            };
        });
    });

    function handleChange(newValue: string) {
        value = newValue;
        onchange?.(newValue);
    }
</script>

<SearchSelect bind:value {compact} {disabled} {dropdownPosition} inlineSearch={true} loading={!sectorsLoaded} {maxVisibleItems} onchange={handleChange} options={sectorOptions} placeholder={placeholder || $t('assets.distribution.addSector')}>
    {#snippet item(option)}
        <div class="flex items-center min-w-0">
            <div class="min-w-0">
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate" title={option.label}>
                    {option.label}
                </div>
            </div>
        </div>
    {/snippet}
    {#snippet selectedItem(option)}
        {#if compact}
            <div class="flex items-center min-w-0">
                <span class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{option.label}</span>
            </div>
        {:else}
            <div class="flex items-center min-w-0">
                <div class="min-w-0">
                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate" title={option.label}>
                        {option.label}
                    </div>
                </div>
            </div>
        {/if}
    {/snippet}
</SearchSelect>
