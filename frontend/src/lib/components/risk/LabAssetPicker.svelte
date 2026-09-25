<!--
  LabAssetPicker — the "+" of the laboratory's selection card.

  It replaces a fixed single-choice select that took one asset per round trip:
  open, search, click, and the list closed again. Here the list stays open, rows
  are checked, and one press adds them all.

  It lists the page's own assets that are not selected yet. The type and
  currency filters live here, above the list they narrow: on the card they also
  narrowed the quick actions, so "select all" silently meant "select what the
  filter you forgot about lets through".

  Risk's eligibility engine decides which assets the analysis can use in the
  period (`eligibility.ts`). An asset it rules out is listed read-only, in a
  section of its own, with the engine's reasons; one it admits with a warning
  can be checked, and shows the warning. An asset with no verdict is selectable.

  The rows carry a name, a type and a currency, and nothing else: this page shows
  no money (`asset-global-page-shows-no-money`).
-->
<script lang="ts">
    import {AlertTriangle, Check, Coins, Layers, Lock, Plus, Search, X} from 'lucide-svelte';

    import {_ as t} from '$lib/i18n';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {currentLanguage} from '$lib/stores/app/language';
    import {currencyStoreVersion, ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import LabCheckMenu, {type CheckMenuItem} from './LabCheckMenu.svelte';
    import LabPopover from './LabPopover.svelte';
    import {applyFilters, pickerRows, toggleVisibleRows, visibleRowsAllChecked, type SelectionFilters} from './assetSetSelection';
    import {nameOrder} from './correlationHelpers';
    import type {EligibilityView} from './eligibility';

    interface PickerAsset {
        id: number;
        display_name: string;
        currency: string;
        icon_url?: string | null;
        asset_type?: string | null;
    }

    interface Props {
        /** The page's whole catalogue. */
        assets: readonly PickerAsset[];
        selected: readonly number[];
        /** How many more assets the selection can take. */
        room: number;
        /** Risk's verdicts, worded. An asset missing from the map is selectable. */
        eligibility: ReadonlyMap<number, EligibilityView>;
        onadd: (assetIds: number[]) => void;
    }

    let {assets, selected, room, eligibility, onadd}: Props = $props();

    let open = $state(false);
    let query = $state('');
    let checked = $state<number[]>([]);
    /** Kept across openings: the chips above the list show them, so a filter never hides assets unseen. */
    let filters = $state<SelectionFilters>({types: [], currencies: []});
    let searchInput = $state<HTMLInputElement>();

    let filtersActive = $derived(filters.types.length > 0 || filters.currencies.length > 0);

    /**
     * The values each filter offers come from the **whole** catalogue, never from
     * the filtered list: an option derived from what survives the filter vanishes
     * the moment it is applied, and can no longer be switched off
     * (`problems/datatable-filter-options-disappear`).
     *
     * The counts beside them are another matter: they say how many assets each
     * value would still **add** — not selected yet, and not ruled out for the
     * period — because that is the question the "+" answers. A value whose assets
     * are all in already reads 0, and stays in the menu.
     */
    let addable = $derived(assets.filter((asset) => !selected.includes(asset.id) && eligibility.get(asset.id)?.level !== 'ineligible'));

    function countBy(read: (asset: PickerAsset) => string): Map<string, number> {
        const counts = new Map<string, number>();
        for (const asset of addable) counts.set(read(asset), (counts.get(read(asset)) ?? 0) + 1);
        return counts;
    }

    let typeItems = $derived.by((): CheckMenuItem[] => {
        const counts = countBy((asset) => asset.asset_type || 'OTHER');
        const values = [...new Set(assets.map((asset) => asset.asset_type || 'OTHER'))];
        return values.map((value) => ({value, label: typeLabel(value), iconUrl: getAssetTypeIconUrl(value), count: counts.get(value) ?? 0})).sort((left, right) => left.label.localeCompare(right.label));
    });

    let currencyItems = $derived.by((): CheckMenuItem[] => {
        void $currencyStoreVersion;
        const counts = countBy((asset) => asset.currency);
        const values = [...new Set(assets.map((asset) => asset.currency))].sort();
        return values.map((value) => ({value, label: value, glyph: getCurrencyInfo(value).flag_emoji, count: counts.get(value) ?? 0}));
    });

    let byId = $derived(new Map(assets.map((asset) => [asset.id, asset])));
    let ordered = $derived(
        nameOrder(
            assets.map((asset) => asset.id),
            (assetId) => byId.get(assetId)?.display_name ?? '',
        )
            .map((assetId) => byId.get(assetId))
            .filter((asset): asset is PickerAsset => asset !== undefined),
    );
    let matching = $derived(pickerRows(applyFilters(ordered, filters), selected, query, (asset) => `${asset.display_name} ${asset.currency} ${typeLabel(asset.asset_type)}`));
    let rows = $derived(matching.filter((asset) => eligibility.get(asset.id)?.level !== 'ineligible'));
    let blocked = $derived(matching.filter((asset) => eligibility.get(asset.id)?.level === 'ineligible'));
    let visibleIds = $derived(rows.map((asset) => asset.id));
    let allChecked = $derived(visibleRowsAllChecked(checked, visibleIds, room));
    let full = $derived(checked.length >= room);

    /** The currency chips show flags, which live in the currency cache. */
    $effect(() => {
        void ensureCurrenciesLoaded($currentLanguage);
    });

    /** Every opening starts with an empty search and nothing checked: a half-made choice from the last visit is not this one. */
    $effect(() => {
        if (!open) return;
        query = '';
        checked = [];
        queueMicrotask(() => searchInput?.focus());
    });

    function typeLabel(type: string | null | undefined): string {
        const key = type || 'OTHER';
        return $t(`assets.types.${key}`) || key;
    }

    function toggleFilter(kind: 'types' | 'currencies', value: string): void {
        const current = filters[kind];
        const next = current.includes(value) ? current.filter((entry) => entry !== value) : [...current, value];
        // Like the search, a filter narrows what is shown, not what was checked: "Add N" still counts them.
        filters = {...filters, [kind]: next};
    }

    function clearFilters(): void {
        filters = {types: [], currencies: []};
    }

    function toggleRow(assetId: number): void {
        if (checked.includes(assetId)) checked = checked.filter((id) => id !== assetId);
        else if (!full) checked = [...checked, assetId];
    }

    function confirm(close: () => void): void {
        if (checked.length === 0) return;
        onadd(checked);
        close();
    }

    function hideBrokenIcon(event: Event): void {
        (event.currentTarget as HTMLImageElement).style.visibility = 'hidden';
    }
</script>

<LabPopover bind:open testId="risk-asset-add-panel" panelClass="w-96">
    {#snippet trigger({toggle})}
        <Tooltip text={room > 0 ? $t('risk.assetSet.addAsset') : $t('risk.assetSet.maxAssets')} position="top" interactiveChild>
            <button
                type="button"
                class="inline-flex h-7 items-center gap-1 rounded-full border border-dashed border-gray-300 px-2.5 text-xs font-medium text-gray-500 transition-colors hover:border-libre-green hover:text-libre-green disabled:opacity-40 disabled:hover:border-gray-300 disabled:hover:text-gray-500 dark:border-slate-500 dark:text-gray-400"
                onclick={(event) => {
                    // Not up to the Tooltip wrapper: its click would pin the hint over the list.
                    event.stopPropagation();
                    toggle();
                }}
                disabled={room <= 0}
                aria-label={$t('risk.assetSet.addAsset')}
                data-testid="risk-asset-add-button"
            >
                <Plus size={14} />
            </button>
        </Tooltip>
    {/snippet}

    {#snippet children({close})}
        <div class="border-b border-gray-100 p-2 dark:border-slate-700">
            <div class="relative">
                <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
                <input
                    bind:this={searchInput}
                    bind:value={query}
                    type="text"
                    class="w-full rounded-md border border-gray-200 bg-white py-1.5 pl-8 pr-2 text-sm text-gray-700 placeholder-gray-400 focus:border-libre-green focus:ring-1 focus:ring-libre-green dark:border-slate-600 dark:bg-slate-700 dark:text-gray-200"
                    placeholder={$t('assets.searchPlaceholder')}
                    onkeydown={(event) => {
                        if (event.key === 'Enter') confirm(close);
                    }}
                    data-testid="risk-asset-add-search"
                />
            </div>

            <div class="mt-2 flex flex-wrap items-center gap-2" data-testid="risk-asset-set-filters">
                <LabCheckMenu
                    label={$t('risk.assetSet.filters.type')}
                    icon={Layers}
                    items={typeItems}
                    selected={filters.types}
                    ontoggle={(value) => toggleFilter('types', value)}
                    onclear={() => (filters = {...filters, types: []})}
                    clearLabel={$t('risk.assetSet.filters.clear')}
                    testId="risk-filter-type"
                    optionTestId={(value) => `risk-filter-type-${value}`}
                />
                <LabCheckMenu
                    label={$t('risk.assetSet.filters.currency')}
                    icon={Coins}
                    items={currencyItems}
                    selected={filters.currencies}
                    ontoggle={(value) => toggleFilter('currencies', value)}
                    onclear={() => (filters = {...filters, currencies: []})}
                    clearLabel={$t('risk.assetSet.filters.clear')}
                    testId="risk-filter-currency"
                    optionTestId={(value) => `risk-filter-currency-${value}`}
                />
                {#if filtersActive}
                    <button type="button" class="ml-auto inline-flex items-center gap-0.5 text-[11px] text-libre-green hover:underline" onclick={clearFilters} data-testid="risk-filters-clear">
                        <X size={11} />
                        {$t('risk.assetSet.filters.clear')}
                    </button>
                {/if}
            </div>
        </div>

        <div class="max-h-80 overflow-y-auto">
            {#if rows.length > 0}
                <div class="flex items-center justify-between px-3 pt-2 text-[11px] text-gray-500 dark:text-gray-400">
                    <button
                        type="button"
                        class="text-libre-green hover:underline disabled:opacity-40 disabled:hover:no-underline"
                        disabled={allChecked && !visibleIds.some((id) => checked.includes(id))}
                        onclick={() => (checked = toggleVisibleRows(checked, visibleIds, room))}
                        data-testid="risk-asset-add-toggle-visible"
                    >
                        {allChecked ? $t('risk.assetSet.picker.deselectVisible') : $t('risk.assetSet.picker.selectVisible')}
                    </button>
                    <span class="tabular-nums">{rows.length}</span>
                </div>
                <div class="p-1" role="listbox" aria-multiselectable="true">
                    {#each rows as asset (asset.id)}
                        {@const on = checked.includes(asset.id)}
                        {@const verdict = eligibility.get(asset.id)}
                        <button
                            type="button"
                            role="option"
                            aria-selected={on}
                            class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[13px] text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 dark:text-gray-200 dark:hover:bg-slate-700"
                            disabled={!on && full}
                            onclick={() => toggleRow(asset.id)}
                            data-testid="risk-asset-add-option-{asset.id}"
                            data-level={verdict?.level ?? 'unknown'}
                            data-reasons={verdict?.codes.join(' ') ?? ''}
                        >
                            <span
                                class="flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border transition-colors {on
                                    ? 'border-libre-green bg-libre-green text-white dark:border-emerald-400 dark:bg-emerald-400 dark:text-slate-900'
                                    : 'border-gray-300 bg-white dark:border-slate-500 dark:bg-slate-900'}"
                            >
                                {#if on}<Check size={12} />{/if}
                            </span>
                            <img src={asset.icon_url || getAssetTypeIconUrl(asset.asset_type)} alt="" class="h-4 w-4 shrink-0 object-contain" onerror={hideBrokenIcon} />
                            <span use:scrollOnOverflow class="{overflowScrollTextClass} min-w-0 flex-1">{asset.display_name}</span>
                            {#if verdict?.level === 'warning'}
                                <Tooltip text={verdict.texts.join(' · ')} position="left" interactiveChild>
                                    <span class="inline-flex text-amber-500" data-testid="risk-asset-add-warning-{asset.id}"><AlertTriangle size={13} /></span>
                                </Tooltip>
                            {/if}
                            <span class="shrink-0 text-[10px] text-gray-400 dark:text-gray-500">{typeLabel(asset.asset_type)}</span>
                            <span class="w-8 shrink-0 text-right font-mono text-[10px] text-gray-500 dark:text-gray-400">{asset.currency}</span>
                        </button>
                    {/each}
                </div>
            {/if}

            {#if blocked.length > 0}
                <p class="flex items-center justify-between border-t border-gray-100 px-3 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wide text-gray-400 dark:border-slate-700 dark:text-gray-500">
                    <span>{$t('risk.assetSet.picker.notAnalysable')}</span>
                    <span class="tabular-nums">{blocked.length}</span>
                </p>
                <ul class="p-1 pt-0" data-testid="risk-asset-add-blocked">
                    {#each blocked as asset (asset.id)}
                        {@const verdict = eligibility.get(asset.id)}
                        <li class="flex items-start gap-2 rounded-md px-2 py-1.5 text-[13px] text-gray-400 dark:text-gray-500" data-testid="risk-asset-add-option-{asset.id}" data-level="ineligible" data-reasons={verdict?.codes.join(' ') ?? ''}>
                            <Lock size={14} class="mt-0.5 shrink-0" />
                            <img src={asset.icon_url || getAssetTypeIconUrl(asset.asset_type)} alt="" class="mt-0.5 h-4 w-4 shrink-0 object-contain opacity-60" onerror={hideBrokenIcon} />
                            <span class="min-w-0 flex-1">
                                <span use:scrollOnOverflow class="{overflowScrollTextClass} block">{asset.display_name}</span>
                                <span class="block text-[11px] leading-snug text-amber-600 dark:text-amber-400">{verdict?.texts.join(' · ')}</span>
                            </span>
                        </li>
                    {/each}
                </ul>
            {/if}

            {#if rows.length === 0 && blocked.length === 0}
                <p class="px-3 py-4 text-center text-xs text-gray-400 dark:text-gray-500" data-testid="risk-asset-add-empty">
                    {query.trim() || filtersActive ? $t('common.noResults') : $t('risk.assetSet.picker.allSelected')}
                </p>
            {/if}
        </div>

        {#if full && room > 0}
            <p class="px-3 pb-1 pt-1 text-[11px] text-amber-600 dark:text-amber-400">{$t('risk.assetSet.maxAssets')}</p>
        {/if}

        <div class="flex items-center justify-end gap-2 border-t border-gray-100 p-2 dark:border-slate-700">
            <button type="button" class="rounded-md px-2.5 py-1 text-xs text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-slate-700" onclick={close}>{$t('common.cancel')}</button>
            <button type="button" class="rounded-md bg-libre-green px-2.5 py-1 text-xs font-medium text-white hover:bg-libre-green/90 disabled:opacity-40" disabled={checked.length === 0} onclick={() => confirm(close)} data-testid="risk-asset-add-confirm">
                {$t('risk.assetSet.picker.confirm', {values: {count: checked.length}})}
            </button>
        </div>
    {/snippet}
</LabPopover>
