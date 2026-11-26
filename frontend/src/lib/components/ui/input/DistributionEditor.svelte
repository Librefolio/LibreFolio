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
    import type {Snippet} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import {RefreshCw, X as XIcon, Plus, Scale, Trash2, Upload} from 'lucide-svelte';
    import Button from '$lib/components/ui/button/Button.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {BulkAction, ColumnDef, RowAction} from '$lib/components/table/types';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import {currentLanguage} from '$lib/stores/app/language';
    import type {CountryInfo} from '$lib/stores/reference/countryStore';
    import {ensureCountriesLoaded, getAllCountries} from '$lib/stores/reference/countryStore';
    import {getSectorKeysList, sectorI18nKey} from '$lib/utils/assetTypes';
    import {ensureSectorsLoaded, getSectorEmoji} from '$lib/stores/reference/sectorStore';
    import {CountrySearchSelect, SectorSearchSelect} from '$lib/components/ui/select';
    import {generateUUID} from '$lib/utils/core/uuid';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import DistributionDataImportModal from '$lib/features/assets/DistributionDataImportModal.svelte';

    // =========================================================================
    // Types
    // =========================================================================

    interface DistEntry {
        id: string;
        key: string;
        weight: number; // 0-100 display range
    }

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        kind: 'sector' | 'geographic';
        value?: Record<string, number>;
        readonly?: boolean;
        disabled?: boolean;
        onchange?: (value: Record<string, number>) => void;
        /** Optional per-section Ask Provider; `hasProvider` false keeps the button off with its reason (D5). */
        hasProvider?: boolean;
        askingProvider?: boolean;
        onAskProvider?: () => void;
        /** The ask button's word and name; «Chiedi al Provider» when absent (the profile asks its sources, E10c3). */
        askLabel?: string;
        zIndex?: number;
    }

    let {kind, value = $bindable({}), readonly: isReadonly = false, disabled = false, onchange, hasProvider = false, askingProvider = false, onAskProvider, askLabel, zIndex = 80}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let entries: DistEntry[] = $state([]);
    let countries: CountryInfo[] = $state([]);
    let addingEntry = $state(false);
    let skipNextSync = false;
    let showDeleteConfirm = $state(false);
    let pendingDeleteIds: string[] = $state([]);
    let showImportModal = $state(false);

    // Sync from prop value → internal entries (only on external changes)
    $effect(() => {
        if (skipNextSync) {
            skipNextSync = false;
            return;
        }
        if (value) {
            entries = Object.entries(value)
                .map(([key, w]) => ({id: generateUUID(), key, weight: Number(w) * 100}))
                .sort((a, b) => {
                    if (a.key === 'Other' && b.key !== 'Other') return 1;
                    if (b.key === 'Other' && a.key !== 'Other') return -1;
                    return b.weight - a.weight;
                });
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

    // Load sectors from backend for sector mode
    $effect(() => {
        if (kind === 'sector') {
            ensureSectorsLoaded();
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
    let isValid = $derived(Math.abs(totalPercent - 100) < 0.005);

    /** The ticked rows still in the table (a deleted row leaves the selection with it): the head's selection mode. */
    let tickedIds = $state<string[]>([]);
    let selecting = $derived(tickedIds.some((id) => entries.some((entry) => entry.id === id)));
    let isExcess = $derived(totalPercent > 100.005);
    let isMissing = $derived(totalPercent < 99.995 && entries.length > 0);
    let maxWeight = $derived(Math.max(...entries.map((e) => e.weight), 1));

    let validBarClass = $derived(isValid ? 'bg-lf-success' : isExcess ? 'bg-lf-danger' : 'bg-lf-warning');

    /** Sector select options (all keys, with i18n labels) */
    let allSectorOptions = $derived(
        getSectorKeysList().map((key) => {
            const i18nKey = `sectors.${sectorI18nKey(key)}`;
            const localized = $t(i18nKey);
            return {
                value: key,
                label: `${getSectorEmoji(key)} ${localized === i18nKey ? key : localized}`.trim(),
            };
        }),
    );

    /** Country select options (all countries, including 'Other' from backend) */
    let allCountryOptions = $derived(countries.map((c) => ({value: c.iso3, label: `${c.flag_emoji || ''} ${c.iso3} — ${c.name}`.trim()})));

    /** Already-used keys for exclusion in "Add" logic */
    let usedKeys = $derived(new Set(entries.map((e) => e.key)));

    function normalizedLookup(items: Array<[string, string]>): Map<string, string> {
        return new Map(items.map(([input, canonical]) => [input.trim().toLocaleLowerCase(), canonical]));
    }

    let importNameLookup = $derived.by(() => {
        if (kind === 'geographic') {
            return normalizedLookup(
                countries.flatMap((country) => [
                    [country.iso2, country.iso3],
                    [country.iso3, country.iso3],
                    [country.name, country.iso3],
                ]),
            );
        }
        return normalizedLookup(
            getSectorKeysList().flatMap((key) => {
                const i18nKey = `sectors.${sectorI18nKey(key)}`;
                const localized = $t(i18nKey);
                return localized === i18nKey
                    ? [[key, key]]
                    : [
                          [key, key],
                          [localized, key],
                      ];
            }),
        );
    });

    // =========================================================================
    // Actions
    // =========================================================================

    function emitChange() {
        const result: Record<string, number> = {};
        for (const e of entries) {
            result[e.key] = Number((e.weight / 100).toFixed(4));
        }
        skipNextSync = true;
        value = result;
        onchange?.(result);
    }

    function importDistribution(distribution: Record<string, number>) {
        skipNextSync = true;
        value = distribution;
        entries = Object.entries(distribution)
            .map(([key, weight]) => ({id: generateUUID(), key, weight: weight * 100}))
            .sort((a, b) => b.weight - a.weight);
        onchange?.(distribution);
    }

    function updateWeight(id: string, newVal: number) {
        entries = entries.map((e) => (e.id === id ? {...e, weight: Math.max(0, newVal)} : e));
        emitChange();
    }

    function updateKey(id: string, newKey: string) {
        entries = entries.map((e) => (e.id === id ? {...e, key: newKey} : e));
        emitChange();
    }

    function removeEntry(id: string) {
        entries = entries.filter((e) => e.id !== id);
        emitChange();
    }

    async function addEntry() {
        // Reference data is loaded asynchronously: clicking before it arrives used to
        // produce an entry with an empty key, which the parent then dropped in silence.
        // Awaiting fixes the key but not the timing — the click handler returns before
        // the row exists, so a Save pressed straight after the click still saves
        // nothing. `addingEntry` is what makes that window visible instead of silent.
        addingEntry = true;
        try {
            if (kind === 'geographic' && countries.length === 0) {
                await loadCountries($currentLanguage);
            }
            let defaultKey = '';
            if (kind === 'sector') {
                defaultKey = getSectorKeysList().find((k) => !usedKeys.has(k)) ?? '';
            } else {
                const firstUnused = countries.find((c) => !usedKeys.has(c.iso3));
                defaultKey = firstUnused?.iso3 ?? '';
            }
            if (!defaultKey) return;
            const remaining = Math.max(0, Math.round((100 - totalPercent) * 100) / 100);
            entries = [...entries, {id: generateUUID(), key: defaultKey, weight: remaining}];
            emitChange();
        } finally {
            addingEntry = false;
        }
    }

    /** Balance a single entry: assign all deficit/excess to this row */
    function balanceEntry(id: string) {
        const delta = 100 - totalPercent;
        entries = entries.map((e) => (e.id === id ? {...e, weight: Math.max(0, Math.min(100, e.weight + delta))} : e));
        emitChange();
    }

    /** Weighted balance on selected rows: distribute delta proportionally to pre-existing weights */
    function balanceSelected(ids: string[]) {
        const delta = 100 - totalPercent;
        if (Math.abs(delta) < 0.005) return;
        const selectedSet = new Set(ids);
        const selectedEntries = entries.filter((e) => selectedSet.has(e.id));
        if (selectedEntries.length === 0) return;

        const totalSelectedWeight = selectedEntries.reduce((s, e) => s + e.weight, 0);

        entries = entries.map((e) => {
            if (!selectedSet.has(e.id)) return e;
            let share: number;
            if (totalSelectedWeight > 0) {
                share = delta * (e.weight / totalSelectedWeight);
            } else {
                // All selected have weight 0: distribute equally
                share = delta / selectedEntries.length;
            }
            return {...e, weight: Math.max(0, Number((e.weight + share).toFixed(2)))};
        });
        emitChange();
    }

    /** Bulk delete with confirmation */
    function handleBulkDelete(ids: string[]) {
        pendingDeleteIds = [...ids];
        showDeleteConfirm = true;
    }

    function confirmBulkDelete() {
        const deleteSet = new Set(pendingDeleteIds);
        entries = entries.filter((e) => !deleteSet.has(e.id));
        pendingDeleteIds = [];
        showDeleteConfirm = false;
        emitChange();
    }

    function formatLabel(key: string): string {
        if (kind === 'sector') {
            const i18nKey = `sectors.${sectorI18nKey(key)}`;
            const localized = $t(i18nKey);
            return localized !== i18nKey ? localized : key;
        }
        // Geographic: handle 'Other' specially, otherwise show flag + iso3
        if (key === 'Other') return `🏳️ Other`;
        const c = countries.find((c) => c.iso3 === key);
        if (c) return `${c.flag_emoji || ''} ${c.iso3}`.trim();
        return key;
    }

    // =========================================================================
    // DataTable columns
    // =========================================================================

    let dtColumns = $derived.by<ColumnDef<DistEntry>[]>(() => {
        const cols: ColumnDef<DistEntry>[] = [];

        // Key / Name column — SearchSelect when not readonly
        cols.push({
            id: 'key',
            header: () => (kind === 'sector' ? $t('common.sectorDistribution') : $t('common.geoDistribution')),
            type: 'custom' as const,
            cell: (row) => {
                if (isReadonly || disabled) {
                    return {type: 'html' as const, html: `<span class="text-xs">${formatLabel(row.key)}</span>`};
                }
                if (kind === 'geographic') {
                    const excluded = new Set([...usedKeys].filter((k) => k !== row.key));
                    return {
                        type: 'custom' as const,
                        component: CountrySearchSelect,
                        props: {
                            value: row.key,
                            excludedCountries: excluded,
                            maxVisibleItems: 5,
                            dropdownPosition: 'auto' as const,
                            compact: true,
                            onchange: (v: string) => updateKey(row.id, v),
                        },
                    };
                }
                // Sector
                const excluded = new Set([...usedKeys].filter((k) => k !== row.key));
                return {
                    type: 'custom' as const,
                    component: SectorSearchSelect,
                    props: {
                        value: row.key,
                        excludedSectors: excluded,
                        maxVisibleItems: 5,
                        dropdownPosition: 'auto' as const,
                        compact: true,
                        onchange: (v: string) => updateKey(row.id, v),
                    },
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
                html: `<div data-testid="distribution-entry-${kind}-${escapeHtml(row.key)}" data-weight="${row.weight}" class="h-3 bg-lf-neutral rounded-full overflow-hidden"><div class="h-full rounded-full transition-all ${validBarClass}" style="width: ${Math.min(100, (row.weight / maxWeight) * 100)}%"></div></div>`,
            }),
            sortable: false,
            filterable: false,
            width: 120,
        });

        // Weight column
        cols.push({
            id: 'weight',
            header: () => $t('assets.distribution.weightPercent'),
            type: 'number',
            cell: (row) => {
                if (isReadonly || disabled) {
                    return formatPercent(row.weight, {signed: false, suffix: ''});
                }
                return {
                    type: 'editable-number' as const,
                    value: Number(row.weight.toFixed(2)),
                    step: 0.01,
                    min: 0,
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

    let rowActions: RowAction<DistEntry>[] = $derived(
        isReadonly || disabled
            ? []
            : [
                  {
                      id: 'balance',
                      icon: Scale,
                      label: () => $t('assets.distribution.balanceRow'),
                      onClick: (row) => balanceEntry(row.id),
                      // At a total of 100 there is nothing to balance: not offered (77 SEL-M, Q-SEL-17)
                      visible: () => !isValid,
                  },
                  {
                      id: 'delete',
                      icon: XIcon,
                      label: () => $t('common.remove'),
                      variant: 'danger',
                      onClick: (row) => removeEntry(row.id),
                  },
              ],
    );

    /**
     * The selection bar's actions (77 SEL-D2), each on the ticked rows with their number. «Balance» spreads what is
     * missing over them; at a total of 100 there is nothing to spread, so it is not offered (Q-SEL-17).
     */
    const bulkActions: BulkAction<DistEntry>[] = [
        {
            id: 'balance',
            icon: Scale,
            label: () => $t('assets.distribution.balance'),
            onClick: (rows) => balanceSelected(rows.map((row) => row.id)),
            pointless: () => isValid,
        },
        {
            id: 'delete',
            icon: Trash2,
            label: () => $t('common.delete'),
            variant: 'danger',
            onClick: (rows) => handleBulkDelete(rows.map((row) => row.id)),
        },
    ];
</script>

<!-- The section head (77 SEL-D2): the title, the table's selection bar, the section's own buttons. The table draws it and
     hands it the bar; with no row (or read-only, where nothing can be ticked) it is drawn here with an empty bar. -->
{#snippet head(bar: Snippet)}
    <!-- 77 SEL-D2: the section's buttons are the standard `xs` Button (85 BTN-2d); beside the compact bar their words may
         break on two lines (`wrap`, C17), 14 px each, so the head stays 32 px when rows are ticked; below `sm` they show
         the icon alone. -->
    <!-- 77 SEL-D2 (a): in a narrow head, while rows are ticked, the bar takes the title's place. The title is only visually
         hidden (CSS below): a screen reader finds the same heading, and the table's first column repeats it in view. -->
    <div class="mb-1 flex min-h-8 items-center justify-between gap-2" class:selecting data-selecting={selecting ? 'true' : 'false'} data-testid="distribution-head-{kind}">
        <div class="dist-title text-xs font-medium text-lf-muted uppercase" data-testid="distribution-title-{kind}">
            {kind === 'sector' ? $t('common.sectorDistribution') : $t('common.geoDistribution')}
        </div>
        <div class="flex min-w-0 items-center gap-1.5">
            {@render bar()}
            {#if !isReadonly && !disabled}
                <Button variant="ghost" size="xs" wrap icon={Upload} display="auto" hideWordBelow="sm" label={$t('dataEditor.importCsv')} onclick={() => (showImportModal = true)} data-testid="distribution-import-{kind}" />
                <Button
                    variant="ghost"
                    size="xs"
                    wrap
                    icon={Plus}
                    display="auto"
                    hideWordBelow="sm"
                    label={kind === 'sector' ? $t('assets.distribution.addSector') : $t('assets.distribution.addCountry')}
                    busy={addingEntry}
                    onclick={addEntry}
                    data-busy={addingEntry}
                    data-testid="distribution-add-{kind}"
                />
            {/if}
            {#if !isReadonly && !disabled && onAskProvider}
                <!-- Off while nothing can be asked (D5): the reason says why at the first tap, click or Tab. -->
                <Button
                    variant="ghost"
                    size="xs"
                    wrap
                    icon={RefreshCw}
                    display="auto"
                    hideWordBelow="sm"
                    label={askLabel ?? $t('assets.identifiers.askProvider')}
                    busy={askingProvider}
                    reason={hasProvider ? undefined : $t('assets.distribution.askNoSource')}
                    reasonCode="no-source"
                    onclick={onAskProvider}
                    data-testid="distribution-ask-provider-{kind}"
                />
            {/if}
        </div>
    </div>
{/snippet}

{#snippet noBar()}{/snippet}

<div class="space-y-1 text-lf-primary" data-testid="distribution-editor-{kind}">
    <!-- DataTable -->
    {#if entries.length > 0}
        <DataTable
            data={entries}
            columns={dtColumns}
            getRowId={(r) => r.id}
            storageKey="dist-editor-{kind}"
            enableSelection={!isReadonly && !disabled}
            {bulkActions}
            selectionPanel={true}
            selectionHead={head}
            onSelectionChange={(ids) => (tickedIds = ids)}
            enablePagination={true}
            defaultPageSize={5}
            pageSizeOptions={[5, 10, 25, 0]}
            enableColumnFilters={false}
            enableSorting={true}
            enableColumnResize={false}
            enableColumnVisibility={false}
            enableActions={!isReadonly && !disabled}
            actionsColumnWidth="64px"
            {rowActions}
            tableLayout="auto"
        />

        <!-- Total badge -->
        <div class="flex items-center justify-end gap-1.5 text-xs font-medium pt-1">
            <span class="text-lf-muted">{$t('assets.distribution.total')}:</span>
            <span data-testid="distribution-total-{kind}" data-state={isValid ? 'valid' : isExcess ? 'excess' : 'missing'} class="{isValid ? 'text-lf-success' : isExcess ? 'text-lf-danger' : 'text-lf-warning'} font-mono">
                {formatPercent(totalPercent, {signed: false})}
            </span>
            {#if isValid}
                <span class="text-lf-success">✅</span>
            {:else if isExcess}
                <span class="text-lf-danger">⚠ ({formatPercent(totalPercent - 100)} {$t('assets.distribution.excess')})</span>
            {:else if isMissing}
                <span class="text-lf-warning">⚠ ({formatPercent(100 - totalPercent, {signed: false})} {$t('assets.distribution.missing')})</span>
            {/if}
        </div>
    {:else if isReadonly || disabled}
        {@render head(noBar)}
        <div class="text-xs text-lf-muted italic py-2">—</div>
    {:else}
        {@render head(noBar)}
        <div class="text-xs text-lf-muted italic py-2">{$t('assets.distribution.emptyHint')}</div>
    {/if}
</div>

<ConfirmModal
    open={showDeleteConfirm}
    title={$t('assets.distribution.deleteSelected')}
    message={$t('assets.distribution.deleteConfirmMessage', {values: {n: pendingDeleteIds.length}})}
    confirmText={$t('common.delete')}
    warning={true}
    onConfirm={confirmBulkDelete}
    onCancel={() => {
        showDeleteConfirm = false;
        pendingDeleteIds = [];
    }}
    {zIndex}
/>

<DistributionDataImportModal bind:open={showImportModal} title="{kind === 'sector' ? $t('common.sectorDistribution') : $t('common.geoDistribution')} — {$t('dataEditor.importCsv')}" resolveName={(raw) => importNameLookup.get(raw.trim().toLocaleLowerCase()) ?? null} onimport={importDistribution} />

<style>
    /* 77 SEL-D2 (a): below 40rem of head (the `dt-head` container of the selection panel) the title, the compact bar and
       the section's three buttons do not fit one line: measured in four languages, the sectors' head is 453 px at 1440
       and 517 px at 640 (too narrow), 645 px at 768 (enough). */
    @container dt-head (max-width: 39.98rem) {
        .selecting .dist-title {
            position: absolute;
            width: 1px;
            height: 1px;
            margin: -1px;
            padding: 0;
            overflow: hidden;
            clip: rect(0 0 0 0);
            border: 0;
            white-space: nowrap;
        }
    }
</style>
