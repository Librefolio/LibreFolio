<!--
  TreeSelect.svelte — Svelte 5

  Two-level searchable select: groups that open and close, items inside them, a search box that
  crosses both levels, and a full keyboard model (↑ ↓ Home End Enter → ← Escape).

  Born as `charts/SignalTreeSelect.svelte` and generalized here by decision D-K1 (workstream K,
  R15): the mechanics moved verbatim, and the four things that tied it to signals became props
  whose defaults are the signals' own behaviour —

    1. content   → the `item` snippet (and optional `groupLabel`), instead of SignalOptionContent;
    2. test ids  → `testIdPrefix`: rows are `${prefix}-option-{value}` / `${prefix}-group-{key}`;
    3. model     → a group may be `inline`: its items sit at the root, with no group row;
    4. trigger   → `showSelected` + `selectedItem`: a form field shows its value, while the
                   signals picker is an *action* picker that always shows its placeholder.

  `charts/SignalTreeSelect.svelte` is now a thin adapter over this component, and
  `SignalTreeSelect.test.ts` pins that nothing changed for the signals panel and for
  `e2e/gallery.spec.ts`, which relies on the first group opening by itself (`defaultExpanded`).
-->
<script generics="T extends TreeSelectItem" lang="ts">
    import type {Snippet} from 'svelte';
    import {ChevronDown, ChevronRight, Search, X} from 'lucide-svelte';

    import {_ as t} from '$lib/i18n';
    import type {TreeSelectGroup, TreeSelectItem} from './treeSelect';

    type NavigationEntry =
        | {
              kind: 'group';
              id: string;
              group: TreeSelectGroup<T>;
          }
        | {
              kind: 'item';
              id: string;
              item: T;
          };

    interface Props {
        value?: string;
        groups: TreeSelectGroup<T>[];
        placeholder?: string;
        testId?: string;
        flat?: boolean;
        onchange?: (value: string) => void;
        /** Row content. */
        item: Snippet<[T]>;
        /** Group row content (label and subtitle). The chevron and the count badge stay the component's. */
        groupLabel?: Snippet<[TreeSelectGroup<T>]>;
        /** Trigger content for the selected item; used only with `showSelected`. */
        selectedItem?: Snippet<[T]>;
        /** Show the selected item on the closed trigger (a form field) instead of the placeholder (an action picker). */
        showSelected?: boolean;
        /** Row test ids: `${testIdPrefix}-option-{value}` and `${testIdPrefix}-group-{key}`. */
        testIdPrefix?: string;
        searchPlaceholder?: string;
        noMatchesText?: string;
        /** Which group opens by itself: the first one, the one holding the value, or none. */
        defaultExpanded?: 'first' | 'selected' | 'none';
        /** Lower bound of the dropdown width, in px; the dropdown never shrinks below the trigger. */
        minDropdownWidth?: number;
        /** Border of the closed trigger. The signals panel's strong border is the default; a form field matches its neighbours. */
        triggerBorderClass?: string;
    }

    let {
        value = $bindable(''),
        groups,
        placeholder = '',
        testId,
        flat = false,
        onchange,
        item: itemContent,
        groupLabel,
        selectedItem,
        showSelected = false,
        testIdPrefix = 'tree-select',
        searchPlaceholder,
        noMatchesText,
        defaultExpanded = 'first',
        minDropdownWidth = 390,
        triggerBorderClass = 'border-gray-900 dark:border-slate-600',
    }: Props = $props();
    let isOpen = $state(false);
    let query = $state('');
    let expanded = $state(new Set<string>());
    let containerRef = $state<HTMLDivElement | null>(null);
    let inputRef = $state<HTMLInputElement | null>(null);
    let dropdownStyle = $state('');
    let activeIndex = $state(-1);
    const instanceSuffix = Math.random().toString(36).slice(2, 9);
    let treeId = $derived(`${testIdPrefix}-${instanceSuffix}`);

    // `searchText` is matched as given: callers pass it lower-cased, as the signals panel always has.
    let normalizedQuery = $derived(query.trim().toLocaleLowerCase());
    let visibleGroups = $derived(
        groups
            .map((group) => ({
                ...group,
                items: normalizedQuery ? group.items.filter((item) => item.searchText.includes(normalizedQuery)) : group.items,
            }))
            .filter((group) => group.items.length > 0),
    );
    let visibleItems = $derived(visibleGroups.flatMap((group) => group.items));
    let selectedEntry = $derived(showSelected && value ? (groups.flatMap((group) => group.items).find((item) => item.value === value) ?? null) : null);
    let navigationEntries = $derived.by<NavigationEntry[]>(() => {
        if (flat || normalizedQuery) {
            return visibleItems.map((item) => ({
                kind: 'item',
                id: itemNavigationId(item.value),
                item,
            }));
        }

        const entries: NavigationEntry[] = [];
        for (const group of visibleGroups) {
            if (!group.inline) {
                entries.push({
                    kind: 'group',
                    id: groupNavigationId(group.key),
                    group,
                });
            }
            if (group.inline || expanded.has(group.key)) {
                entries.push(
                    ...group.items.map((item) => ({
                        kind: 'item' as const,
                        id: itemNavigationId(item.value),
                        item,
                    })),
                );
            }
        }
        return entries;
    });
    let activeEntry = $derived(isOpen ? (navigationEntries[activeIndex] ?? navigationEntries[0] ?? null) : null);

    function groupNavigationId(groupKey: string): string {
        return `${treeId}-group-${groupKey}`;
    }

    function itemNavigationId(itemValue: string): string {
        return `${treeId}-item-${itemValue}`;
    }

    function scrollActiveEntryIntoView() {
        const entry = navigationEntries[activeIndex];
        if (!entry) return;
        setTimeout(() => document.getElementById(entry.id)?.scrollIntoView({block: 'nearest'}), 0);
    }

    function setActiveIndex(index: number) {
        if (navigationEntries.length === 0) {
            activeIndex = -1;
            return;
        }
        activeIndex = ((index % navigationEntries.length) + navigationEntries.length) % navigationEntries.length;
        scrollActiveEntryIntoView();
    }

    function activateEntry(id: string) {
        const index = navigationEntries.findIndex((entry) => entry.id === id);
        if (index >= 0) activeIndex = index;
    }

    function updatePosition() {
        if (!containerRef) return;
        const rect = containerRef.getBoundingClientRect();
        const width = Math.min(Math.max(rect.width, minDropdownWidth), window.innerWidth - 16);
        const left = Math.max(8, Math.min(rect.left, window.innerWidth - width - 8));
        const spaceBelow = window.innerHeight - rect.bottom - 16;
        const openAbove = spaceBelow < 360 && rect.top > spaceBelow;
        dropdownStyle = openAbove ? `position:fixed; bottom:${window.innerHeight - rect.top + 4}px; left:${left}px; width:${width}px; z-index:9999;` : `position:fixed; top:${rect.bottom + 4}px; left:${left}px; width:${width}px; z-index:9999;`;
    }

    /** The collapsible group that should open by itself, or null. */
    function groupToExpandOnOpen(): string | null {
        if (flat) return null;
        if (defaultExpanded === 'first') {
            if (expanded.size !== 0) return null;
            return groups.find((group) => !group.inline)?.key ?? null;
        }
        if (defaultExpanded === 'selected' && value) {
            return groups.find((group) => !group.inline && group.items.some((item) => item.value === value))?.key ?? null;
        }
        return null;
    }

    function open(fromEnd = false) {
        updatePosition();
        isOpen = true;
        query = '';
        const toExpand = groupToExpandOnOpen();
        if (toExpand !== null && !expanded.has(toExpand)) expanded = new Set([...expanded, toExpand]);
        setTimeout(() => {
            const selectedIndex = selectedEntry ? navigationEntries.findIndex((entry) => entry.kind === 'item' && entry.item.value === selectedEntry.value) : -1;
            setActiveIndex(fromEnd ? navigationEntries.length - 1 : selectedIndex >= 0 ? selectedIndex : 0);
            inputRef?.focus();
        }, 0);
    }

    function close() {
        isOpen = false;
        query = '';
        activeIndex = -1;
    }

    function toggle() {
        if (isOpen) close();
        else open();
    }

    function toggleGroup(groupKey: string) {
        const next = new Set(expanded);
        if (next.has(groupKey)) next.delete(groupKey);
        else next.add(groupKey);
        expanded = next;
    }

    function select(item: T) {
        value = item.value;
        onchange?.(item.value);
        close();
    }

    function handleKeydown(event: KeyboardEvent) {
        switch (event.key) {
            case 'Escape':
                event.preventDefault();
                close();
                break;
            case 'ArrowDown':
                event.preventDefault();
                setActiveIndex(activeIndex + 1);
                break;
            case 'ArrowUp':
                event.preventDefault();
                setActiveIndex(activeIndex - 1);
                break;
            case 'Home':
                event.preventDefault();
                setActiveIndex(0);
                break;
            case 'End':
                event.preventDefault();
                setActiveIndex(navigationEntries.length - 1);
                break;
            case 'Enter':
                event.preventDefault();
                if (activeEntry?.kind === 'group') toggleGroup(activeEntry.group.key);
                else if (activeEntry?.kind === 'item') select(activeEntry.item);
                break;
            case 'ArrowRight':
                if (activeEntry?.kind === 'group' && !expanded.has(activeEntry.group.key)) {
                    event.preventDefault();
                    toggleGroup(activeEntry.group.key);
                }
                break;
            case 'ArrowLeft':
                if (activeEntry?.kind === 'group' && expanded.has(activeEntry.group.key)) {
                    event.preventDefault();
                    toggleGroup(activeEntry.group.key);
                }
                break;
        }
    }

    $effect(() => {
        if (!isOpen) return;
        const handleOutside = (event: MouseEvent) => {
            if (!containerRef?.contains(event.target as Node)) close();
        };
        const reposition = () => updatePosition();
        document.addEventListener('mousedown', handleOutside, true);
        window.addEventListener('resize', reposition);
        window.addEventListener('scroll', reposition, true);
        return () => {
            document.removeEventListener('mousedown', handleOutside, true);
            window.removeEventListener('resize', reposition);
            window.removeEventListener('scroll', reposition, true);
        };
    });
</script>

{#snippet option(item: T)}
    {@const navigationId = itemNavigationId(item.value)}
    {@const isActive = activeEntry?.id === navigationId}
    <button
        type="button"
        id={navigationId}
        role={flat ? 'option' : 'treeitem'}
        aria-selected={isActive}
        tabindex="-1"
        class="w-full px-4 py-2 text-left transition-colors
            {isActive ? 'bg-libre-green/15 dark:bg-libre-green/25' : 'hover:bg-libre-green/10 dark:hover:bg-libre-green/20'}"
        onclick={() => select(item)}
        onmouseenter={() => activateEntry(navigationId)}
        data-testid="{testIdPrefix}-option-{item.value}"
    >
        {@render itemContent(item)}
    </button>
{/snippet}

<div bind:this={containerRef} class="relative" data-testid={testId}>
    <div
        aria-expanded={isOpen}
        aria-haspopup={flat ? 'listbox' : 'tree'}
        aria-controls={treeId}
        aria-activedescendant={activeEntry?.id}
        class="flex w-full cursor-pointer items-center justify-between gap-2 rounded-lg border px-3 py-2 text-left transition-all
            bg-white text-sm text-gray-900 hover:border-gray-600 dark:bg-slate-700 dark:text-gray-100 dark:hover:border-slate-500
            {isOpen ? 'border-libre-green ring-2 ring-libre-green dark:border-libre-green' : triggerBorderClass}"
        onclick={toggle}
        onkeydown={(event) => {
            if (!isOpen && (event.key === 'Enter' || event.key === ' ' || event.key === 'ArrowDown' || event.key === 'ArrowUp' || event.key.length === 1)) {
                event.preventDefault();
                open(event.key === 'ArrowUp');
                if (event.key.length === 1) setTimeout(() => (query = event.key), 0);
            } else {
                handleKeydown(event);
            }
        }}
        role="combobox"
        tabindex="0"
        data-testid={testId ? `${testId}-button` : undefined}
    >
        {#if isOpen}
            <Search size={14} class="shrink-0 text-gray-400" />
            <input
                bind:this={inputRef}
                bind:value={query}
                aria-controls={treeId}
                aria-activedescendant={activeEntry?.id}
                class="min-w-0 flex-1 border-none bg-transparent text-sm outline-none placeholder:text-gray-400"
                placeholder={searchPlaceholder ?? $t('common.search')}
                onclick={(event) => event.stopPropagation()}
                oninput={() => setTimeout(() => setActiveIndex(0), 0)}
                onkeydown={(event) => {
                    event.stopPropagation();
                    handleKeydown(event);
                }}
            />
            {#if query}
                <button
                    type="button"
                    class="shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                    aria-label={$t('common.clear')}
                    onclick={(event) => {
                        event.stopPropagation();
                        query = '';
                        setTimeout(() => setActiveIndex(0), 0);
                        inputRef?.focus();
                    }}
                >
                    <X size={14} />
                </button>
            {/if}
        {:else if selectedEntry && selectedItem}
            <div class="min-w-0 flex-1">
                {@render selectedItem(selectedEntry)}
            </div>
            <ChevronDown size={14} class="shrink-0 text-gray-400" />
        {:else}
            <span class="text-gray-400">{placeholder || $t('common.select')}</span>
            <ChevronDown size={14} class="shrink-0 text-gray-400" />
        {/if}
    </div>

    {#if isOpen}
        <div class="max-h-[420px] overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-800" id={treeId} style={dropdownStyle} role={flat ? 'listbox' : 'tree'}>
            {#if visibleGroups.length === 0}
                <div class="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                    {noMatchesText ?? $t('common.noData')}
                </div>
            {:else if flat}
                <div class="py-1" role="group">
                    {#each visibleItems as item (item.value)}
                        {@render option(item)}
                    {/each}
                </div>
            {:else}
                {#each visibleGroups as group (group.key)}
                    {#if group.inline}
                        <div class="border-b border-gray-100 py-1 last:border-b-0 dark:border-slate-700">
                            {#each group.items as item (item.value)}
                                {@render option(item)}
                            {/each}
                        </div>
                    {:else}
                        {@const groupOpen = normalizedQuery !== '' || expanded.has(group.key)}
                        {@const navigationId = groupNavigationId(group.key)}
                        {@const isActive = activeEntry?.id === navigationId}
                        <div class="border-b border-gray-100 last:border-b-0 dark:border-slate-700">
                            <button
                                type="button"
                                id={navigationId}
                                role="treeitem"
                                tabindex="-1"
                                aria-selected={isActive}
                                class="flex w-full items-start gap-2 px-3 py-2.5 text-left transition-colors
                                    {isActive ? 'bg-libre-green/10 dark:bg-libre-green/20' : 'hover:bg-gray-50 dark:hover:bg-slate-700'}"
                                aria-expanded={groupOpen}
                                onclick={() => toggleGroup(group.key)}
                                onmouseenter={() => activateEntry(navigationId)}
                                data-testid="{testIdPrefix}-group-{group.key}"
                            >
                                {#if groupOpen}
                                    <ChevronDown size={15} class="mt-0.5 shrink-0 text-gray-400" />
                                {:else}
                                    <ChevronRight size={15} class="mt-0.5 shrink-0 text-gray-400" />
                                {/if}
                                {#if groupLabel}
                                    {@render groupLabel(group)}
                                {:else}
                                    <span class="min-w-0">
                                        <span class="block text-xs font-semibold uppercase tracking-wide text-gray-700 dark:text-gray-200">{group.label}</span>
                                        <span class="block text-[10px] leading-4 text-gray-400 dark:text-gray-500">{group.subtitle}</span>
                                    </span>
                                {/if}
                                <span class="ml-auto rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500 dark:bg-slate-700 dark:text-gray-400">{group.items.length}</span>
                            </button>
                            {#if groupOpen}
                                <div class="pb-1" role="group">
                                    {#each group.items as item (item.value)}
                                        {@render option(item)}
                                    {/each}
                                </div>
                            {/if}
                        </div>
                    {/if}
                {/each}
            {/if}
        </div>
    {/if}
</div>
