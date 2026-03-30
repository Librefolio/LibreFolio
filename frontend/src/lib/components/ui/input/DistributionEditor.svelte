<!--
  DistributionEditor — Editable distribution table for sector or geographic allocations.

  Uses DataTable for consistent table rendering.

  Props:
  - kind: 'sector' | 'geographic'
  - value: Record<string, number> (0-1 range, bindable)
  - readonly/disabled
  - onchange callback
  - onAskProvider callback (optional, for per-section Ask Provider)

  Features:
  - Inline editing of weight percentages (displayed 0-100, stored 0-1)
  - Key column as inline select (sector or country)
  - Visual bar proportional to weight
  - Add/remove entries via DataTable row actions
  - Total validation (100% = green, else warning)
  - Sector names localized via i18n
  - Country names with flag emoji from countryStore
  - Sorting enabled by key and weight

  Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {RefreshCw, Loader2, X as XIcon, Plus} from 'lucide-svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef, RowAction} from '$lib/components/table/types';
    import {currentLanguage} from '$lib/stores/language';
    import type {CountryInfo} from '$lib/stores/countryStore';
    import {ensureCountriesLoaded, getAllCountries} from '$lib/stores/countryStore';

    // =========================================================================
    // Types
    // =========================================================================

    interface DistEntry {
        id: string;
        key: string;
        weight: number; // 0-100 display range
    }

    /** Predefined sector keys (matching i18n `sectors.*` keys) */
    const SECTOR_KEYS = [
        'Industrials', 'Technology', 'Financials', 'ConsumerDiscretionary',
        'HealthCare', 'RealEstate', 'BasicMaterials', 'Energy',
        'ConsumerStaples', 'Telecommunication', 'Utilities', 'Other',
    ] as const;

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        kind: 'sector' | 'geographic';
        value?: Record<string, number>;
        readonly?: boolean;
        disabled?: boolean;
        onchange?: (value: Record<string, number>) => void;
        /** Optional per-section Ask Provider */
        hasProvider?: boolean;
        askingProvider?: boolean;
        onAskProvider?: () => void;
    }

    let {
        kind,
        value = $bindable({}),
        readonly: isReadonly = false,
        disabled = false,
        onchange,
        hasProvider = false,
        askingProvider = false,
        onAskProvider,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let entries = $state<DistEntry[]>([]);
    let countries = $state<CountryInfo[]>([]);

    // Sync from prop value → internal entries
    $effect(() => {
        if (value) {
            entries = Object.entries(value)
                .map(([key, w]) => ({id: crypto.randomUUID(), key, weight: Number(w) * 100}))
                .sort((a, b) => b.weight - a.weight);
        } else {
            entries = [];
        }
    });

    // Load countries for geographic mode
    $effect(() => {
        if (kind === 'geographic') {
            const lang = $currentLanguage;
            loadCountries(lang);
        }
    });

    async function loadCountries(language: string) {
        try {
            await ensureCountriesLoaded(language);
            countries = getAllCountries();
        } catch (e) {
            console.error('Failed to load countries:', e);
        }
    }

    // =========================================================================
    // Derived
    // =========================================================================

    let totalPercent = $derived(entries.reduce((sum, e) => sum + e.weight, 0));
    let isValid = $derived(Math.abs(totalPercent - 100) < 0.05);
    let isExcess = $derived(totalPercent > 100.05);
    let isMissing = $derived(totalPercent < 99.95 && entries.length > 0);
    let maxWeight = $derived(Math.max(...entries.map(e => e.weight), 1));

    let validBarClass = $derived(isValid ? 'bg-libre-green' : isExcess ? 'bg-red-400' : 'bg-amber-400');

    /** Sector select options (all keys, with i18n labels) */
    let allSectorOptions = $derived(
        SECTOR_KEYS.map(k => ({value: k, label: $t(`sectors.${k}`) || k}))
    );

    /** Country select options (all countries, with flag + name) */
    let allCountryOptions = $derived(
        countries.map(c => ({value: c.iso3, label: `${c.flag_emoji || ''} ${c.iso3} — ${c.name}`.trim()}))
    );

    /** Already-used keys for exclusion in "Add" logic */
    let usedKeys = $derived(new Set(entries.map(e => e.key)));

    // =========================================================================
    // Actions
    // =========================================================================

    function emitChange() {
        const result: Record<string, number> = {};
        for (const e of entries) {
            result[e.key] = Number((e.weight / 100).toFixed(4));
        }
        value = result;
        onchange?.(result);
    }

    function updateWeight(id: string, newVal: number) {
        entries = entries.map(e => e.id === id ? {...e, weight: Math.max(0, Math.min(100, newVal))} : e);
        emitChange();
    }

    function updateKey(id: string, newKey: string) {
        entries = entries.map(e => e.id === id ? {...e, key: newKey} : e);
        emitChange();
    }

    function removeEntry(id: string) {
        entries = entries.filter(e => e.id !== id);
        emitChange();
    }

    function addEntry() {
        let defaultKey = '';
        if (kind === 'sector') {
            defaultKey = SECTOR_KEYS.find(k => !usedKeys.has(k)) ?? '';
        } else {
            const firstUnused = countries.find(c => !usedKeys.has(c.iso3));
            defaultKey = firstUnused?.iso3 ?? '';
        }
        entries = [...entries, {id: crypto.randomUUID(), key: defaultKey, weight: 100}];
        emitChange();
    }

    function formatLabel(key: string): string {
        if (kind === 'sector') {
            const localized = $t(`sectors.${key}`);
            return localized !== `sectors.${key}` ? localized : key;
        }
        // Geographic: show flag + name
        const c = countries.find(c => c.iso3 === key);
        if (c) return `${c.flag_emoji || ''} ${c.iso3}`.trim();
        return key;
    }

    // =========================================================================
    // DataTable columns
    // =========================================================================

    let dtColumns = $derived.by<ColumnDef<DistEntry>[]>(() => {
        const cols: ColumnDef<DistEntry>[] = [];

        // Key / Name column — editable select when not readonly
        cols.push({
            id: 'key',
            header: () => kind === 'sector' ? $t('assets.modal.sectorDistribution') : $t('assets.modal.geographicDistribution'),
            type: 'custom' as const,
            cell: (row) => {
                if (isReadonly || disabled) {
                    return {type: 'html' as const, html: `<span class="text-xs">${formatLabel(row.key)}</span>`};
                }
                const options = kind === 'sector' ? allSectorOptions : allCountryOptions;
                return {
                    type: 'editable-select' as const,
                    value: row.key,
                    options,
                    onchange: (newVal: string) => updateKey(row.id, newVal),
                };
            },
            sortable: true,
            filterable: false,
            width: kind === 'geographic' ? 200 : 180,
        });

        // Bar column
        cols.push({
            id: 'bar',
            header: '',
            type: 'custom',
            cell: (row) => ({
                type: 'html' as const,
                html: `<div class="h-3 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden"><div class="h-full rounded-full transition-all ${validBarClass}" style="width: ${Math.min(100, (row.weight / maxWeight) * 100)}%"></div></div>`,
            }),
            sortable: false,
            filterable: false,
            width: 120,
        });

        // Weight column
        cols.push({
            id: 'weight',
            header: 'Weight %',
            type: 'number',
            cell: (row) => {
                if (isReadonly || disabled) {
                    return row.weight.toFixed(2);
                }
                return {
                    type: 'editable-number' as const,
                    value: Number(row.weight.toFixed(2)),
                    step: 0.01,
                    min: 0,
                    max: 100,
                    placeholder: '0.00',
                    onchange: (newVal: number | null) => updateWeight(row.id, newVal ?? 0),
                };
            },
            sortable: true,
            filterable: false,
            width: 90,
        });

        return cols;
    });

    let rowActions = $derived<RowAction<DistEntry>[]>(
        isReadonly || disabled ? [] : [
            {
                id: 'delete',
                icon: XIcon,
                label: 'Remove',
                variant: 'danger',
                onClick: (row) => removeEntry(row.id),
            },
        ]
    );
</script>

<div class="space-y-1">
    <!-- Section header with +Add and Ask Provider buttons -->
    <div class="flex items-center justify-between mb-1">
        <div class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
            {kind === 'sector' ? $t('assets.modal.sectorDistribution') : $t('assets.modal.geographicDistribution')}
        </div>
        <div class="flex items-center gap-1.5">
            {#if !isReadonly && !disabled}
                <button type="button" onclick={addEntry}
                        class="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium rounded text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                        title={kind === 'sector' ? $t('assets.distribution.addSector') : $t('assets.distribution.addCountry')}>
                    <Plus size={10}/>
                    {kind === 'sector' ? $t('assets.distribution.addSector') : $t('assets.distribution.addCountry')}
                </button>
            {/if}
            {#if !isReadonly && !disabled && onAskProvider}
                <button
                        type="button"
                        onclick={onAskProvider}
                        disabled={!hasProvider || askingProvider}
                        class="flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded
                               text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200
                               disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                        title={$t('assets.identifiers.askProvider')}
                >
                    {#if askingProvider}
                        <Loader2 size={10} class="animate-spin"/>
                    {:else}
                        <RefreshCw size={10}/>
                    {/if}
                    <span>{$t('assets.identifiers.askProvider')}</span>
                </button>
            {/if}
        </div>
    </div>

    <!-- DataTable -->
    {#if entries.length > 0}
        <DataTable
                data={entries}
                columns={dtColumns}
                getRowId={(r) => r.id}
                storageKey="dist-editor-{kind}"
                enableSelection={false}
                enablePagination={false}
                enableColumnFilters={false}
                enableSorting={true}
                enableColumnResize={false}
                enableColumnVisibility={false}
                enableActions={!isReadonly && !disabled}
                actionsColumnWidth="40px"
                rowActions={rowActions}
                tableLayout="auto"
        />

        <!-- Total badge -->
        <div class="flex items-center justify-end gap-1.5 text-xs font-medium pt-1">
            <span class="text-gray-500 dark:text-gray-400">{$t('assets.distribution.total')}:</span>
            <span class="{isValid ? 'text-green-600 dark:text-green-400' : isExcess ? 'text-red-500' : 'text-amber-500'} font-mono">
                {totalPercent.toFixed(2)}%
            </span>
            {#if isValid}
                <span class="text-green-500">✅</span>
            {:else if isExcess}
                <span class="text-red-500">⚠ (+{(totalPercent - 100).toFixed(2)}% {$t('assets.distribution.excess')})</span>
            {:else if isMissing}
                <span class="text-amber-500">⚠ ({(100 - totalPercent).toFixed(2)}% {$t('assets.distribution.missing')})</span>
            {/if}
        </div>
    {:else if isReadonly || disabled}
        <div class="text-xs text-gray-400 italic py-2">—</div>
    {/if}
</div>

