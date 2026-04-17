<!--
  ProviderComparisonModal — Shows differences between local and provider data.

  Used by AssetModal when "Ask Provider" detects conflicts.
  Allows user to selectively accept/reject provider values.

  Features:
  - Dynamic section grouping via DIFF_FIELD_SECTIONS config
  - Uniform card layout for all field types (string + distribution)
  - Arrow centered between value boxes
  - Select All / Deselect All
  - Apply Selected (count/total)

  Adding a new field: just add it to DIFF_FIELD_SECTIONS array.

  Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import {X} from 'lucide-svelte';
    import {sectorI18nKey} from '$lib/utils/assetTypes';

    // =========================================================================
    // Types
    // =========================================================================

    export interface DiffItem {
        field: string; // "currency", "identifier_isin", "sector_area", etc.
        label: string; // Localized label
        type: 'string' | 'distribution';
        currentValue: any;
        providerValue: any;
        selected: boolean; // Checkbox state
    }

    // =========================================================================
    // Section Configuration — drives grouping and order
    // =========================================================================

    /**
     * Configuration for field grouping in the comparison modal.
     * Order matches the AssetModal layout. Each section has an i18n title key
     * and a list of field names/prefixes. Fields not matching any section
     * go into an "Other" fallback group.
     *
     * To add a new field: just add its name to the appropriate section.
     */
    const DIFF_FIELD_SECTIONS: Array<{
        titleKey: string;
        fields: string[];
        matchPrefix?: boolean;
    }> = [
        {
            titleKey: 'common.identifiers',
            fields: ['identifier_'],
            matchPrefix: true,
        },
        {
            titleKey: 'assets.modal.assetDetails',
            fields: ['display_name', 'asset_type', 'currency'],
        },
        {
            titleKey: 'common.classification',
            fields: ['short_description', 'sector_area', 'geographic_area'],
        },
    ];

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        open?: boolean;
        differences: DiffItem[];
        onapply?: (selectedFields: string[]) => void;
        oncancel?: () => void;
    }

    let {open = $bindable(false), differences = [], onapply, oncancel}: Props = $props();

    // =========================================================================
    // State — local copy for checkbox management
    // =========================================================================

    let items = $state<DiffItem[]>([]);

    // Sync from props when modal opens
    $effect(() => {
        if (open && differences.length > 0) {
            items = differences.map((d) => ({...d, selected: true}));
        }
    });

    // =========================================================================
    // Derived
    // =========================================================================

    let selectedCount = $derived(items.filter((i) => i.selected).length);
    let totalCount = $derived(items.length);

    /** Group items by section, preserving config order */
    let groupedItems = $derived.by(() => {
        const groups: Array<{title: string; items: Array<{item: DiffItem; index: number}>}> = [];
        const used = new Set<number>();

        for (const section of DIFF_FIELD_SECTIONS) {
            const sectionItems: Array<{item: DiffItem; index: number}> = [];
            items.forEach((item, idx) => {
                const match = section.matchPrefix ? section.fields.some((p) => item.field.startsWith(p)) : section.fields.includes(item.field);
                if (match && !used.has(idx)) {
                    sectionItems.push({item, index: idx});
                    used.add(idx);
                }
            });
            if (sectionItems.length > 0) {
                groups.push({title: $t(section.titleKey), items: sectionItems});
            }
        }

        // Fallback: any unmatched fields go into "Other"
        const remaining = items.map((item, idx) => ({item, index: idx})).filter(({index: idx}) => !used.has(idx));
        if (remaining.length > 0) {
            groups.push({title: 'Other', items: remaining});
        }

        return groups;
    });

    // =========================================================================
    // Actions
    // =========================================================================

    function selectAll() {
        items = items.map((i) => ({...i, selected: true}));
    }

    function deselectAll() {
        items = items.map((i) => ({...i, selected: false}));
    }

    function toggleItem(index: number) {
        items = items.map((item, i) => (i === index ? {...item, selected: !item.selected} : item));
    }

    function handleApply() {
        const selectedFields = items.filter((i) => i.selected).map((i) => i.field);
        onapply?.(selectedFields);
        open = false;
    }

    function handleCancel() {
        oncancel?.();
        open = false;
    }

    // =========================================================================
    // Helpers
    // =========================================================================

    function formatDistribution(dist: Record<string, number> | null | undefined): Array<{key: string; pct: string}> {
        if (!dist) return [];
        return Object.entries(dist)
            .sort(([, a], [, b]) => (b as number) - (a as number))
            .map(([key, val]) => ({
                key,
                pct: ((val as number) * 100).toFixed(2) + '%',
            }));
    }

    function truncate(val: any, max: number = 50): string {
        if (val === null || val === undefined) return '—';
        const s = String(val);
        return s.length > max ? s.slice(0, max) + '…' : s;
    }

    /** Format a distribution key with i18n for sector fields */
    function formatDistKey(key: string, field: string): string {
        if (field === 'sector_area') {
            const i18nKey = `sectors.${sectorI18nKey(key)}`;
            const localized = $t(i18nKey);
            return localized !== i18nKey ? localized : key;
        }
        return key;
    }
</script>

<ModalBase {open} maxWidth="2xl" onRequestClose={handleCancel} zIndex={70}>
    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-slate-700">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {$t('assets.comparison.title')}
        </h2>
        <button type="button" onclick={handleCancel} class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
            <X size={20} />
        </button>
    </div>

    <!-- Body -->
    <div class="px-6 py-4 space-y-3 max-h-[60vh] overflow-y-auto">
        <p class="text-sm text-gray-600 dark:text-gray-400">
            {$t('assets.comparison.description')}
        </p>

        <!-- Grouped items — uniform card layout for all types -->
        {#each groupedItems as group}
            <!-- Section header -->
            <div class="text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider pt-2">
                {group.title}
            </div>

            {#each group.items as { item, index }}
                <div class="border border-gray-200 dark:border-slate-700 rounded-lg p-3">
                    <!-- Checkbox + label -->
                    <label class="flex items-center gap-2 cursor-pointer">
                        <input type="checkbox" checked={item.selected} onchange={() => toggleItem(index)} class="rounded border-gray-300 dark:border-slate-600 text-libre-green focus:ring-libre-green/50" />
                        <span class="text-sm font-medium text-gray-700 dark:text-gray-300">{item.label}</span>
                    </label>

                    <!-- Values grid: Current → Provider -->
                    <div class="grid grid-cols-[1fr_auto_1fr] gap-2 mt-2 items-center">
                        <!-- Current box -->
                        <div class="bg-gray-50 dark:bg-slate-800 rounded p-2">
                            <span class="text-[10px] uppercase text-gray-400 block mb-0.5">
                                {$t('assets.comparison.currentValue')}
                            </span>
                            {#if item.type === 'distribution'}
                                <div class="text-xs space-y-0.5">
                                    {#each formatDistribution(item.currentValue?.distribution ?? item.currentValue) as entry}
                                        <div class="flex justify-between">
                                            <span class="text-gray-600 dark:text-gray-400">{formatDistKey(entry.key, item.field)}</span>
                                            <span class="font-mono text-gray-700 dark:text-gray-300">{entry.pct}</span>
                                        </div>
                                    {:else}
                                        <span class="text-gray-400 italic">—</span>
                                    {/each}
                                </div>
                            {:else}
                                <div class="text-xs font-mono text-gray-600 dark:text-gray-400">{truncate(item.currentValue)}</div>
                            {/if}
                        </div>

                        <!-- Arrow (perfectly centered between boxes) -->
                        <div class="text-gray-400 dark:text-gray-500 text-lg font-light">→</div>

                        <!-- Provider box -->
                        <div class="bg-green-50 dark:bg-green-900/20 rounded p-2">
                            <span class="text-[10px] uppercase text-gray-400 block mb-0.5">
                                {$t('assets.comparison.providerValue')}
                            </span>
                            {#if item.type === 'distribution'}
                                <div class="text-xs space-y-0.5">
                                    {#each formatDistribution(item.providerValue?.distribution ?? item.providerValue) as entry}
                                        <div class="flex justify-between">
                                            <span class="text-gray-600 dark:text-gray-400">{formatDistKey(entry.key, item.field)}</span>
                                            <span class="font-mono text-libre-green dark:text-green-400">{entry.pct}</span>
                                        </div>
                                    {:else}
                                        <span class="text-gray-400 italic">—</span>
                                    {/each}
                                </div>
                            {:else}
                                <div class="text-xs font-mono text-libre-green dark:text-green-400">{truncate(item.providerValue)}</div>
                            {/if}
                        </div>
                    </div>
                </div>
            {/each}
        {/each}

        <!-- Select All / Deselect All -->
        <div class="flex items-center gap-3 pt-2">
            <button type="button" onclick={selectAll} class="text-xs text-libre-green hover:text-libre-green/80 font-medium transition-colors">
                {$t('assets.comparison.selectAll')}
            </button>
            <button type="button" onclick={deselectAll} class="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 font-medium transition-colors">
                {$t('assets.comparison.deselectAll')}
            </button>
        </div>
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-slate-700">
        <button type="button" onclick={handleCancel} class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors">
            {$t('common.cancel')}
        </button>
        <button type="button" onclick={handleApply} disabled={selectedCount === 0} class="px-4 py-2 text-sm font-medium text-white bg-libre-green rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
            ✅ {$t('assets.comparison.applySelected', {values: {count: selectedCount, total: totalCount}})}
        </button>
    </div>
</ModalBase>
