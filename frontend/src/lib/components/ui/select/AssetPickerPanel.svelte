<!--
  AssetPickerPanel — picks **portfolio assets**: instruments out of the user's asset catalogue. Not to
  be confused with `ui/media/AssetPickerModal.svelte`, which picks an image file.

  Two modes, one panel: a search, the type and currency filters (`CheckMenu`), and rows with the
  asset's icon, its name, its type and its currency. Never an amount: a picker chooses instruments,
  and some pages that mount it show no money at all.

  - `mode="multi"`, the Asset Global lab's «+»: rows are checked, and one press adds them all
    (`onadd`). The assets already `selected` are left out; `room` caps how many can be added. The
    caller hands in its own `trigger`.
  - `mode="single"`, a drop-in for `SearchSelect` (and for what `AssetSelect` adds to it): the same
    test ids (`{testId}`, `{testId}-trigger`, `{testId}-search`, `search-select-option-{id}`,
    `search-select-header-__section:{key}`), the same search (`filterOptions`), the same
    keyboard (`stepSelectable`). One click chooses and closes (the developer's decision of
    05/10/2026).

  Risk's verdicts (`verdicts`) are read, never computed: an ineligible asset is listed read-only, with
  its reasons, under `blockedLabel`; one with a warning can be chosen and shows ⚠. In single mode the
  current value is never dropped: the trigger shows it whatever its verdict or the filters, and the
  list marks it current, in the blocked section if it is ineligible.

  The panel keeps the caller's order (`assetSelectOrder` is `AssetSelect`'s, for a caller that wants
  it). Its own test ids all start with `testId`, so two pickers on a page never share one.
-->
<script lang="ts">
    import {untrack, type Snippet} from 'svelte';
    import {AlertTriangle, Check, ChevronDown, Coins, Layers, Lock, Search, X} from 'lucide-svelte';

    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import {currencyStoreVersion, ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';

    import {applyFilters, assetSearchText, pickerRows, toggleVisibleRows, visibleRowsAllChecked, type PickerAsset, type PickerSection, type PickerVerdict, type SelectionFilters} from './assetPicker';
    import CheckMenu, {type CheckMenuItem} from './CheckMenu.svelte';
    import {filterOptions, firstSelectable, isSelectable, stepSelectable} from './optionFilter';
    import SelectPopover from './SelectPopover.svelte';
    import type {SelectOption} from './types';

    interface Props {
        mode: 'single' | 'multi';
        /** The catalogue, in the order to show it: the panel never sorts. */
        assets: readonly PickerAsset[];
        /** Risk's verdicts, worded. An asset missing from the map is selectable. */
        verdicts?: ReadonlyMap<number, PickerVerdict>;
        /** Title of the read-only section of the ineligible assets: the caller's words. */
        blockedLabel: string;
        /** What a query matches besides the name. Default: the asset's codes (`assetSearchText`). */
        searchText?: (asset: PickerAsset) => string;
        /** Prefix of every test id, and in single mode the root's own. */
        testId: string;
        /** The control that opens the panel. Required in multi mode; single mode draws a select box. */
        trigger?: Snippet<[{open: boolean; toggle: () => void}]>;
        /** Multi: the assets already chosen, left out of the list. */
        selected?: readonly number[];
        /** Multi: how many more assets can be added. */
        room?: number;
        /** Multi: the note shown once no room is left: the caller's words. */
        fullLabel?: string;
        /** Multi: the assets checked, in the order they were checked. */
        onadd?: (assetIds: number[]) => void;
        /** Single: the current choice. */
        value?: number | null;
        /** Single: a new choice. */
        onchange?: (assetId: number) => void;
        /** Single: titled groups, as `AssetSelect` has them. */
        sections?: readonly PickerSection[];
        /** Single: title of the assets no section claimed, shown only under a titled section. */
        restLabel?: string;
        placeholder?: string;
        loading?: boolean;
        disabled?: boolean;
        /** Single: the dropdown's side and minimum width, as `SearchSelect`'s. */
        dropdownPosition?: 'top' | 'bottom' | 'auto';
        dropdownMinWidth?: number;
    }

    let {
        mode,
        assets,
        verdicts,
        blockedLabel,
        searchText,
        testId,
        trigger: customTrigger,
        selected = [],
        room = Number.POSITIVE_INFINITY,
        fullLabel = '',
        onadd,
        value = $bindable(null),
        onchange,
        sections,
        restLabel,
        placeholder = '',
        loading = false,
        disabled = false,
        dropdownPosition = 'auto',
        dropdownMinWidth = 280,
    }: Props = $props();

    let open = $state(false);
    let query = $state('');
    let checked = $state<number[]>([]);
    /** Kept across openings: the menus show them, so a filter never hides assets unseen. */
    let filters = $state<SelectionFilters>({types: [], currencies: []});
    let searchInput = $state<HTMLInputElement>();
    let triggerRef = $state<HTMLDivElement>();
    let listRef = $state<HTMLDivElement>();
    let highlightedIndex = $state(0);
    /** When the trigger got the focus: an Enter right after a Tab into a filled select must not open it. */
    let triggerFocusedAt = 0;
    /** When the dropdown last closed: a touch's late click must not open it again. */
    let lastClosedAt = 0;

    const listboxId = `asset-picker-listbox-${Math.random().toString(36).substring(2, 9)}`;

    let filtersActive = $derived(filters.types.length > 0 || filters.currencies.length > 0);

    function verdictOf(assetId: number): PickerVerdict | undefined {
        return verdicts?.get(assetId);
    }

    function blocked(asset: PickerAsset): boolean {
        return verdictOf(asset.id)?.level === 'ineligible';
    }

    /** Multi matches every word against one text, so the name joins it there; single matches the name on its own. */
    function searchTextOf(asset: PickerAsset): string {
        if (searchText) return searchText(asset);
        return mode === 'multi' ? `${asset.display_name} ${assetSearchText(asset)}` : assetSearchText(asset);
    }

    function typeLabel(type: string | null | undefined): string {
        const key = type || 'OTHER';
        return $t(`assets.types.${key}`) || key;
    }

    /** `AssetSelect`'s rule: the asset's own icon, else its type's, else none. */
    function iconOf(asset: PickerAsset): string | undefined {
        return asset.icon_url || (asset.asset_type ? getAssetTypeIconUrl(asset.asset_type) : undefined);
    }

    /** The asset an option was built from. */
    function assetOf(option: SelectOption): PickerAsset {
        return option.data as PickerAsset;
    }

    function rowText(asset: PickerAsset): string {
        return asset.identifier_ticker ? `${asset.identifier_ticker} · ${asset.display_name}` : asset.display_name;
    }

    function hideBrokenIcon(event: Event): void {
        (event.currentTarget as HTMLImageElement).style.visibility = 'hidden';
    }

    /**
     * The values each filter offers come from the **whole** catalogue, never from the filtered list:
     * an option derived from what survives the filter vanishes the moment it is applied, and can no
     * longer be switched off (`problems/datatable-filter-options-disappear`).
     *
     * The counts say how many assets each value would still bring in — not chosen yet, and not ruled
     * out — because that is the question the list answers. A value whose assets are all in reads 0,
     * and stays in the menu.
     */
    let addable = $derived(assets.filter((asset) => !(mode === 'multi' && selected.includes(asset.id)) && !blocked(asset)));

    function countBy(read: (asset: PickerAsset) => string): Map<string, number> {
        const counts = new Map<string, number>();
        for (const asset of addable) counts.set(read(asset), (counts.get(read(asset)) ?? 0) + 1);
        return counts;
    }

    let typeItems = $derived.by((): CheckMenuItem[] => {
        const counts = countBy((asset) => asset.asset_type || 'OTHER');
        const values = [...new Set(assets.map((asset) => asset.asset_type || 'OTHER'))];
        return values.map((item) => ({value: item, label: typeLabel(item), iconUrl: getAssetTypeIconUrl(item), count: counts.get(item) ?? 0})).sort((left, right) => left.label.localeCompare(right.label));
    });

    let currencyItems = $derived.by((): CheckMenuItem[] => {
        void $currencyStoreVersion;
        const counts = countBy((asset) => asset.currency);
        const values = [...new Set(assets.map((asset) => asset.currency))].sort();
        return values.map((item) => ({value: item, label: item, glyph: getCurrencyInfo(item).flag_emoji, count: counts.get(item) ?? 0}));
    });

    /** The currency menu shows flags, which live in the currency cache. */
    $effect(() => {
        void ensureCurrenciesLoaded($currentLanguage);
    });

    function toggleFilter(kind: 'types' | 'currencies', item: string): void {
        const current = filters[kind];
        const next = current.includes(item) ? current.filter((entry) => entry !== item) : [...current, item];
        // Like the search, a filter narrows what is shown, not what was checked: "Add N" still counts them.
        filters = {...filters, [kind]: next};
    }

    function clearFilters(): void {
        filters = {types: [], currencies: []};
    }

    // ─── multi ────────────────────────────────────────────────────────────────────────────────

    let matching = $derived(mode === 'multi' ? pickerRows(applyFilters(assets, filters), selected, query, searchTextOf) : []);
    let rows = $derived(matching.filter((asset) => !blocked(asset)));
    let blockedRows = $derived(matching.filter((asset) => blocked(asset)));
    let visibleIds = $derived(rows.map((asset) => asset.id));
    let allChecked = $derived(visibleRowsAllChecked(checked, visibleIds, room));
    let full = $derived(checked.length >= room);

    function toggleRow(assetId: number): void {
        if (checked.includes(assetId)) checked = checked.filter((id) => id !== assetId);
        else if (!full) checked = [...checked, assetId];
    }

    function confirm(): void {
        if (checked.length === 0) return;
        onadd?.(checked);
        open = false;
    }

    // ─── single ───────────────────────────────────────────────────────────────────────────────

    function toOption(asset: PickerAsset, isBlocked: boolean): SelectOption {
        return {value: String(asset.id), label: asset.display_name, searchText: searchTextOf(asset), icon: iconOf(asset), disabled: isBlocked, data: asset};
    }

    /** `AssetSelect`'s sections: each asset joins the first section that takes it; empty sections print no title; the rest is titled only under a titled section. */
    function sectioned(options: SelectOption[]): SelectOption[] {
        if (!sections || sections.length === 0) return options;
        const buckets = new Map<string, SelectOption[]>(sections.map((section) => [section.key, []]));
        const unclaimed: SelectOption[] = [];
        for (const option of options) {
            const section = sections.find((candidate) => candidate.match(assetOf(option)));
            if (section) buckets.get(section.key)!.push(option);
            else unclaimed.push(option);
        }
        const out: SelectOption[] = [];
        for (const section of sections) {
            const members = buckets.get(section.key)!;
            if (members.length === 0) continue;
            out.push({value: `__section:${section.key}`, label: section.label, header: true});
            out.push(...members);
        }
        if (unclaimed.length > 0) {
            if (restLabel && out.length > 0) out.push({value: '__section:__rest', label: restLabel, header: true});
            out.push(...unclaimed);
        }
        return out;
    }

    let filtered = $derived(mode === 'single' ? applyFilters(assets, filters) : []);
    /** The options the keyboard walks: every asset that can be chosen, by section. */
    let listed = $derived(filterOptions(sectioned(filtered.filter((asset) => !blocked(asset)).map((asset) => toOption(asset, false))), query));
    /** The ruled-out assets, searched like the others, listed apart and disabled. */
    let listedBlocked = $derived(
        filterOptions(
            filtered.filter((asset) => blocked(asset)).map((asset) => toOption(asset, true)),
            query,
        ),
    );
    /** The current value, read from the whole catalogue: neither a verdict nor a filter hides it here. */
    let current = $derived(value === null ? undefined : assets.find((asset) => asset.id === value));

    function openSingle(): void {
        if (disabled) return;
        // A touch's late click right after a close must not reopen it.
        if (Date.now() - lastClosedAt < 200) return;
        open = true;
    }

    function closeSingle(): void {
        open = false;
        lastClosedAt = Date.now();
        triggerRef?.focus();
    }

    function toggleSingle(): void {
        if (disabled) return;
        if (open) closeSingle();
        else openSingle();
    }

    function choose(option: SelectOption, advanceFocus = false): void {
        if (!isSelectable(option)) return;
        const assetId = Number(option.value);
        value = assetId;
        onchange?.(assetId);
        closeSingle();
        if (advanceFocus) {
            // As SearchSelect: an Enter moves on to the next field, so a form can be filled from the keyboard.
            setTimeout(() => {
                if (!triggerRef) return;
                const all = Array.from(document.querySelectorAll<HTMLElement>('[tabindex]:not([tabindex="-1"]), input:not([disabled]), select:not([disabled]), button:not([disabled]), a[href]')).filter((element) => element.offsetParent !== null);
                const index = all.indexOf(triggerRef);
                if (index >= 0 && index + 1 < all.length) all[index + 1].focus();
            }, 20);
        }
    }

    function handleTriggerKeydown(event: KeyboardEvent): void {
        if (disabled || open) return;
        if (event.key === 'Enter' || event.key === ' ' || event.key === 'ArrowDown') {
            event.preventDefault();
            // A Tab that lands on a filled select, then Enter, moves on rather than reopening it.
            if (event.key === 'Enter' && value !== null && Date.now() - triggerFocusedAt < 200) return;
            openSingle();
        } else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
            // A printable key opens the list and starts the search with it, once the search box is there.
            event.preventDefault();
            openSingle();
            const typed = event.key;
            setTimeout(() => {
                query = typed;
            }, 20);
        }
    }

    function scrollToHighlighted(): void {
        setTimeout(() => listRef?.querySelector('[data-highlighted="true"]')?.scrollIntoView({block: 'nearest'}), 0);
    }

    function handleSearchKeydown(event: KeyboardEvent): void {
        if (mode === 'multi') {
            if (event.key === 'Enter') confirm();
            return;
        }
        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                highlightedIndex = stepSelectable(listed, highlightedIndex, 1);
                scrollToHighlighted();
                break;
            case 'ArrowUp':
                event.preventDefault();
                highlightedIndex = stepSelectable(listed, highlightedIndex, -1);
                scrollToHighlighted();
                break;
            case 'Enter': {
                event.preventDefault();
                const index = isSelectable(listed[highlightedIndex]) ? highlightedIndex : firstSelectable(listed);
                if (index !== -1) choose(listed[index], true);
                break;
            }
            case 'Escape':
                event.preventDefault();
                closeSingle();
                break;
        }
    }

    // ─── both ─────────────────────────────────────────────────────────────────────────────────

    /** Every opening starts with an empty search and nothing checked: a half-made choice from the last visit is not this one. */
    $effect(() => {
        if (!open) return;
        untrack(() => {
            query = '';
            checked = [];
            highlightedIndex = Math.max(firstSelectable(listed), 0);
        });
        setTimeout(() => searchInput?.focus(), 0);
    });

    /** A new query is a new question: the highlight — the row Enter picks — goes back to the best match, at the top. */
    let lastQuery = '';
    $effect(() => {
        const typed = query;
        if (typed === lastQuery) return;
        lastQuery = typed;
        untrack(() => {
            highlightedIndex = Math.max(firstSelectable(listed), 0);
            if (listRef) listRef.scrollTop = 0;
        });
    });

    /** A filter can take the highlighted row away: the highlight moves to one that is there. */
    $effect(() => {
        if (listed.length === 0 || isSelectable(listed[highlightedIndex])) return;
        const next = firstSelectable(listed);
        if (next !== -1 && next !== highlightedIndex) highlightedIndex = next;
    });
</script>

{#snippet searchBox(placeholderText: string)}
    <div class="relative">
        <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
        <input
            bind:this={searchInput}
            bind:value={query}
            type="text"
            class="w-full rounded-md border border-gray-200 bg-white py-1.5 pl-8 pr-2 text-sm text-gray-700 placeholder-gray-400 focus:border-libre-green focus:ring-1 focus:ring-libre-green dark:border-slate-600 dark:bg-slate-700 dark:text-gray-200"
            placeholder={placeholderText}
            onkeydown={handleSearchKeydown}
            data-testid="{testId}-search"
        />
    </div>
{/snippet}

{#snippet filterMenus()}
    <div class="mt-2 flex flex-wrap items-center gap-2" data-testid="{testId}-filters">
        <CheckMenu label={$t('assetPicker.filters.type')} icon={Layers} items={typeItems} selected={filters.types} ontoggle={(item) => toggleFilter('types', item)} onclear={() => (filters = {...filters, types: []})} clearLabel={$t('assetPicker.filters.clear')} testId="{testId}-filter-type" />
        <CheckMenu
            label={$t('assetPicker.filters.currency')}
            icon={Coins}
            items={currencyItems}
            selected={filters.currencies}
            ontoggle={(item) => toggleFilter('currencies', item)}
            onclear={() => (filters = {...filters, currencies: []})}
            clearLabel={$t('assetPicker.filters.clear')}
            testId="{testId}-filter-currency"
        />
        {#if filtersActive}
            <button type="button" class="ml-auto inline-flex items-center gap-0.5 text-[11px] text-libre-green hover:underline" onclick={clearFilters} data-testid="{testId}-filters-clear">
                <X size={11} />
                {$t('assetPicker.filters.clear')}
            </button>
        {/if}
    </div>
{/snippet}

{#snippet warningMark(asset: PickerAsset, verdict: PickerVerdict | undefined)}
    {#if verdict?.level === 'warning'}
        <Tooltip text={verdict.texts.join(' · ')} position="left" interactiveChild>
            <span class="inline-flex text-amber-500" data-testid="{testId}-warning-{asset.id}"><AlertTriangle size={13} /></span>
        </Tooltip>
    {/if}
{/snippet}

{#if mode === 'multi'}
    <SelectPopover bind:open testId="{testId}-panel" panelClass="w-96">
        {#snippet trigger(popover)}
            {@render customTrigger?.(popover)}
        {/snippet}

        {#snippet children({close})}
            <div class="border-b border-gray-100 p-2 dark:border-slate-700">
                {@render searchBox($t('assets.searchPlaceholder'))}
                {@render filterMenus()}
            </div>

            <div class="max-h-80 overflow-y-auto">
                {#if rows.length > 0}
                    <div class="flex items-center justify-between px-3 pt-2 text-[11px] text-gray-500 dark:text-gray-400">
                        <button
                            type="button"
                            class="text-libre-green hover:underline disabled:opacity-40 disabled:hover:no-underline"
                            disabled={allChecked && !visibleIds.some((id) => checked.includes(id))}
                            onclick={() => (checked = toggleVisibleRows(checked, visibleIds, room))}
                            data-testid="{testId}-toggle-visible"
                        >
                            {allChecked ? $t('assetPicker.deselectVisible') : $t('assetPicker.selectVisible')}
                        </button>
                        <span class="tabular-nums">{rows.length}</span>
                    </div>
                    <div class="p-1" role="listbox" aria-multiselectable="true">
                        {#each rows as asset (asset.id)}
                            {@const on = checked.includes(asset.id)}
                            {@const verdict = verdictOf(asset.id)}
                            <button
                                type="button"
                                role="option"
                                aria-selected={on}
                                class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[13px] text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 dark:text-gray-200 dark:hover:bg-slate-700"
                                disabled={!on && full}
                                onclick={() => toggleRow(asset.id)}
                                data-testid="{testId}-option-{asset.id}"
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
                                {@render warningMark(asset, verdict)}
                                <span class="shrink-0 text-[10px] text-gray-400 dark:text-gray-500">{typeLabel(asset.asset_type)}</span>
                                <span class="w-8 shrink-0 text-right font-mono text-[10px] text-gray-500 dark:text-gray-400">{asset.currency}</span>
                            </button>
                        {/each}
                    </div>
                {/if}

                {#if blockedRows.length > 0}
                    <p class="flex items-center justify-between border-t border-gray-100 px-3 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wide text-gray-400 dark:border-slate-700 dark:text-gray-500">
                        <span>{blockedLabel}</span>
                        <span class="tabular-nums">{blockedRows.length}</span>
                    </p>
                    <ul class="p-1 pt-0" data-testid="{testId}-blocked">
                        {#each blockedRows as asset (asset.id)}
                            {@const verdict = verdictOf(asset.id)}
                            <li class="flex items-start gap-2 rounded-md px-2 py-1.5 text-[13px] text-gray-400 dark:text-gray-500" data-testid="{testId}-option-{asset.id}" data-level="ineligible" data-reasons={verdict?.codes.join(' ') ?? ''}>
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

                {#if rows.length === 0 && blockedRows.length === 0}
                    <p class="px-3 py-4 text-center text-xs text-gray-400 dark:text-gray-500" data-testid="{testId}-empty">
                        {query.trim() || filtersActive ? $t('common.noResults') : $t('assetPicker.allSelected')}
                    </p>
                {/if}
            </div>

            {#if full && room > 0}
                <p class="px-3 pb-1 pt-1 text-[11px] text-amber-600 dark:text-amber-400">{fullLabel}</p>
            {/if}

            <div class="flex items-center justify-end gap-2 border-t border-gray-100 p-2 dark:border-slate-700">
                <button type="button" class="rounded-md px-2.5 py-1 text-xs text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-slate-700" onclick={close}>{$t('common.cancel')}</button>
                <button type="button" class="rounded-md bg-libre-green px-2.5 py-1 text-xs font-medium text-white hover:bg-libre-green/90 disabled:opacity-40" disabled={checked.length === 0} onclick={confirm} data-testid="{testId}-confirm">
                    {$t('assetPicker.confirm', {values: {count: checked.length}})}
                </button>
            </div>
        {/snippet}
    </SelectPopover>
{:else}
    <div class="relative w-full" data-testid={testId}>
        <SelectPopover bind:open rootClass="relative block w-full" testId="{testId}-panel" placement={{position: dropdownPosition, minWidth: dropdownMinWidth}}>
            {#snippet trigger(popover)}
                {#if customTrigger}
                    {@render customTrigger(popover)}
                {:else}
                    <!-- SearchSelect's compact box at a fixed height: one line with a value and without, so the field never grows when a value arrives. -->
                    <div
                        bind:this={triggerRef}
                        role="combobox"
                        tabindex={disabled ? -1 : 0}
                        aria-controls={listboxId}
                        aria-expanded={open}
                        aria-haspopup="listbox"
                        aria-disabled={disabled}
                        data-disabled={disabled ? 'true' : 'false'}
                        class="flex h-[38px] w-full items-center justify-between gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-all
                               {disabled ? 'cursor-not-allowed bg-gray-100 text-gray-400 opacity-60 dark:bg-slate-800 dark:text-gray-500' : 'cursor-pointer bg-white hover:border-gray-400 dark:border-slate-600 dark:bg-slate-700 dark:hover:border-slate-500'}
                               {open ? 'border-libre-green ring-2 ring-libre-green' : ''}"
                        onclick={toggleSingle}
                        onfocus={() => (triggerFocusedAt = Date.now())}
                        onkeydown={handleTriggerKeydown}
                        data-testid="{testId}-trigger"
                    >
                        {#if current}
                            {@const icon = iconOf(current)}
                            <div class="flex min-w-0 items-center gap-2">
                                {#if icon}
                                    <img src={icon} alt="" class="h-4 w-4 shrink-0 rounded-sm object-contain" onerror={hideBrokenIcon} />
                                {/if}
                                <span class="truncate text-sm text-gray-900 dark:text-gray-100">{rowText(current)}</span>
                                {#if current.active === false}
                                    <span data-testid="asset-select-selected-inactive-badge" class="shrink-0 rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-500 dark:bg-slate-700 dark:text-gray-400">{$t('assets.edit.status.inactive')}</span>
                                {/if}
                            </div>
                        {:else}
                            <span class="text-gray-400">{placeholder || $t('common.select')}</span>
                        {/if}
                        <ChevronDown class="shrink-0 text-gray-400 transition-transform {open ? 'rotate-180' : ''}" size={14} />
                    </div>
                {/if}
            {/snippet}

            {#snippet children()}
                <div class="shrink-0 border-b border-gray-100 p-2 dark:border-slate-700">
                    {@render searchBox($t('common.search'))}
                    {@render filterMenus()}
                </div>

                <div bind:this={listRef} class="min-h-0 flex-1 overflow-y-auto p-1" id={listboxId} role="listbox" aria-busy={loading}>
                    {#if loading}
                        <div class="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">{$t('common.loading')}</div>
                    {:else}
                        {#each listed as option, index (option.value)}
                            {#if option.header}
                                <div class="px-3 pb-1 pt-2.5 text-[11px] font-semibold uppercase tracking-wide text-gray-400 select-none dark:text-gray-500" role="presentation" data-testid="search-select-header-{option.value}">
                                    {option.label}
                                </div>
                            {:else}
                                {@const asset = assetOf(option)}
                                {@const verdict = verdictOf(asset.id)}
                                {@const icon = iconOf(asset)}
                                <button
                                    type="button"
                                    role="option"
                                    aria-selected={asset.id === value}
                                    class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[13px] text-gray-700 transition-colors dark:text-gray-200 {index === highlightedIndex
                                        ? 'bg-libre-green/30 dark:bg-libre-green dark:text-white'
                                        : 'hover:bg-gray-50 dark:hover:bg-slate-700'}"
                                    onclick={() => choose(option)}
                                    onmouseenter={() => (highlightedIndex = index)}
                                    data-testid="search-select-option-{option.value}"
                                    data-highlighted={index === highlightedIndex}
                                    data-level={verdict?.level ?? 'unknown'}
                                    data-reasons={verdict?.codes.join(' ') ?? ''}
                                >
                                    <span class="flex h-4 w-4 shrink-0 items-center justify-center text-libre-green">
                                        {#if asset.id === value}<Check size={12} />{/if}
                                    </span>
                                    {#if icon}
                                        <img src={icon} alt="" class="h-4 w-4 shrink-0 rounded-sm object-contain" onerror={hideBrokenIcon} />
                                    {/if}
                                    <span use:scrollOnOverflow class="{overflowScrollTextClass} min-w-0 flex-1 {asset.active === false ? 'opacity-60' : ''}">{rowText(asset)}</span>
                                    {#if asset.active === false}
                                        <span data-testid="asset-select-inactive-badge" class="shrink-0 rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-500 dark:bg-slate-700 dark:text-gray-400">{$t('assets.edit.status.inactive')}</span>
                                    {/if}
                                    {@render warningMark(asset, verdict)}
                                    <span class="shrink-0 text-[10px] text-gray-400 dark:text-gray-500">{typeLabel(asset.asset_type)}</span>
                                    <span class="w-8 shrink-0 text-right font-mono text-[10px] text-gray-500 dark:text-gray-400">{asset.currency}</span>
                                </button>
                            {/if}
                        {/each}

                        {#if listedBlocked.length > 0}
                            <div class="mt-1 border-t border-gray-100 pt-1 dark:border-slate-700" role="group" aria-label={blockedLabel} data-testid="{testId}-blocked">
                                <p class="px-2 pb-1 pt-1.5 text-[10px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">{blockedLabel}</p>
                                {#each listedBlocked as option (option.value)}
                                    {@const asset = assetOf(option)}
                                    {@const verdict = verdictOf(asset.id)}
                                    {@const icon = iconOf(asset)}
                                    <button
                                        type="button"
                                        role="option"
                                        disabled
                                        aria-disabled="true"
                                        aria-selected={asset.id === value}
                                        class="flex w-full cursor-not-allowed items-start gap-2 rounded-md px-2 py-1.5 text-left text-[13px] text-gray-400 dark:text-gray-500"
                                        data-testid="search-select-option-{option.value}"
                                        data-highlighted="false"
                                        data-level="ineligible"
                                        data-reasons={verdict?.codes.join(' ') ?? ''}
                                    >
                                        <Lock size={14} class="mt-0.5 shrink-0" />
                                        {#if icon}
                                            <img src={icon} alt="" class="mt-0.5 h-4 w-4 shrink-0 object-contain opacity-60" onerror={hideBrokenIcon} />
                                        {/if}
                                        <span class="min-w-0 flex-1">
                                            <span use:scrollOnOverflow class="{overflowScrollTextClass} block">{rowText(asset)}</span>
                                            <span class="block text-[11px] leading-snug text-amber-600 dark:text-amber-400">{verdict?.texts.join(' · ')}</span>
                                        </span>
                                    </button>
                                {/each}
                            </div>
                        {/if}

                        {#if listed.length === 0 && listedBlocked.length === 0}
                            <p class="px-3 py-4 text-center text-xs text-gray-400 dark:text-gray-500" data-testid="{testId}-empty">{$t('common.noResults')}</p>
                        {/if}
                    {/if}
                </div>
            {/snippet}
        </SelectPopover>
    </div>
{/if}
