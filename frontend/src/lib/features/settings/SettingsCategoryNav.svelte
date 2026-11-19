<!--
  SettingsCategoryNav (project 76, lot S1a): the category menu of a settings page, written once for every page that has
  one — Settings › Global settings, Settings › Preferences (`SettingsLayout`) and, from S1b, Settings › Plugins.

  A page renders it twice, as before the extraction: `mode="phone"` above its content (the «Category» dropdown, `sm:hidden`)
  and `mode="sidebar"` as the first column of its row (`hidden sm:block`). The page keeps the selection, the entries and
  their labels; this component only draws them and reports a choice through `onselect`.

  What every button publishes: `{testIdPrefix}-category-{key}` in the sidebar, `{testIdPrefix}-mobile-category-{key}` in
  the open dropdown, `{testIdPrefix}-mobile-category-trigger` and `{testIdPrefix}-mobile-category-menu`; its selected
  state as `aria-pressed`. `key` is the entry's `testKey`, else its `id` (Preferences' «All» has the id '' and the key
  `all`). The classes are the ones the two copies had, moved as they were. Colours are roles only.

  The Plugins menu (S1b) adds a count after the label (`data-count`, muted unless selected; a whole entry at 0 muted)
  and an amber dot for «something to configure», the look of `TabBar`'s dot, named by `dotLabel` (screen readers, title).
-->
<script lang="ts">
    import type {Component, ComponentType} from 'svelte';

    /** A lucide icon: a legacy component (`ComponentType`, as `SettingsLayout`'s categories declare it) or a Svelte 5 one. */
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- lucide-svelte's icons are legacy components
    type NavIcon = ComponentType | Component<any>;
    import {ChevronDown, ChevronRight} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {isOutsideClick} from '$lib/utils/core/clickOutside';

    export interface SettingsCategoryEntry {
        /** What `selected` holds when this entry is chosen. */
        id: string;
        /** The end of its test ids; `id` when absent. */
        testKey?: string;
        /** None for «All». */
        icon?: NavIcon | null;
        label: string;
        /** Shown after the label, and published as `data-count` (the Plugins menu, S1b); none on the other pages. */
        count?: number;
        /** Something in it needs attention: an amber dot, named for screen readers by `dotLabel`. */
        dot?: boolean;
    }

    interface Props {
        mode: 'phone' | 'sidebar';
        /** «All» first, then the categories, in order. */
        entries: SettingsCategoryEntry[];
        selected: string;
        onselect: (id: string) => void;
        testIdPrefix: string;
        /** The phone trigger's text and icon: each page decides what an unknown selection shows. */
        triggerLabel?: string;
        triggerIcon?: NavIcon | null;
        /** What the dot means, for screen readers. */
        dotLabel?: string;
    }

    let {mode, entries, selected, onselect, testIdPrefix, triggerLabel = '', triggerIcon = null, dotLabel = ''}: Props = $props();

    let showDropdown = $state(false);
    let dropdownRef: HTMLDivElement | null = $state(null);

    const keyOf = (entry: SettingsCategoryEntry): string => entry.testKey ?? entry.id;

    function choose(id: string): void {
        showDropdown = false;
        onselect(id);
    }

    // The phone dropdown closes on a click anywhere outside its own block; the listener lives as long as the block
    $effect(() => {
        if (mode !== 'phone') return;
        const handleClickOutside = (event: MouseEvent): void => {
            if (isOutsideClick(event.target, (el) => !dropdownRef || dropdownRef.contains(el))) showDropdown = false;
        };
        document.addEventListener('click', handleClickOutside);
        return () => document.removeEventListener('click', handleClickOutside);
    });
</script>

{#if mode === 'phone'}
    <!-- Mobile: Custom dropdown category selector -->
    <div bind:this={dropdownRef} class="sm:hidden mb-4 text-lf-primary">
        <span class="block text-sm font-medium text-lf-secondary mb-2">
            {$_('settings.category')}
        </span>
        <div class="relative">
            <button
                class="w-full flex items-center justify-between px-4 py-3 border border-lf-input
                       rounded-lg bg-lf-field text-lf-primary hover:border-lf-input-hover text-sm
                       focus:ring-2 focus:ring-lf-focus focus:border-lf-focus transition-all"
                onclick={() => (showDropdown = !showDropdown)}
                type="button"
                data-testid="{testIdPrefix}-mobile-category-trigger"
            >
                <span class="flex items-center gap-2">
                    {#if triggerIcon}
                        {@const TriggerIcon = triggerIcon}
                        <TriggerIcon size={16} class="text-lf-muted" />
                    {/if}
                    {triggerLabel}
                </span>
                <ChevronDown class="text-lf-muted transition-transform {showDropdown ? 'rotate-180' : ''}" size={18} />
            </button>

            {#if showDropdown}
                <div
                    class="absolute top-full left-0 right-0 mt-1 bg-lf-card border border-lf-raised
                            rounded-lg shadow-lg shadow-lf-shadow overflow-hidden z-50"
                    data-testid="{testIdPrefix}-mobile-category-menu"
                >
                    {#each entries as entry (entry.id)}
                        <button
                            type="button"
                            onclick={() => choose(entry.id)}
                            data-testid="{testIdPrefix}-mobile-category-{keyOf(entry)}"
                            data-count={entry.count}
                            aria-pressed={selected === entry.id ? 'true' : 'false'}
                            class="w-full flex items-center gap-3 px-4 py-3 text-sm text-left transition-colors
                                   {selected === entry.id ? 'bg-lf-selected text-lf-link font-medium' : 'text-lf-secondary hover:bg-lf-hover'}"
                        >
                            {#if entry.icon}
                                {@const Icon = entry.icon}
                                <Icon size={16} class={selected === entry.id ? 'text-lf-link' : 'text-lf-muted'} />
                            {/if}
                            <span class="flex-1">{entry.label}</span>
                            {#if entry.dot}
                                <span class="size-2 shrink-0 rounded-full bg-lf-warning" data-testid="{testIdPrefix}-mobile-category-dot" title={dotLabel}><span class="sr-only">{dotLabel}</span></span>
                            {/if}
                            {#if entry.count !== undefined}
                                <span class="text-xs tabular-nums {selected === entry.id ? '' : 'text-lf-muted'}">{entry.count}</span>
                            {/if}
                            {#if selected === entry.id}
                                <ChevronRight size={16} />
                            {/if}
                        </button>
                    {/each}
                </div>
            {/if}
        </div>
    </div>
{:else}
    <!-- Desktop: Left sidebar category navigation (hidden on mobile) -->
    <div class="hidden sm:block w-48 flex-shrink-0">
        <nav class="space-y-1">
            {#each entries as entry (entry.id)}
                <button
                    type="button"
                    onclick={() => onselect(entry.id)}
                    data-testid="{testIdPrefix}-category-{keyOf(entry)}"
                    data-count={entry.count}
                    aria-pressed={selected === entry.id ? 'true' : 'false'}
                    class="w-full flex items-center px-3 py-2 text-sm rounded-lg transition-colors
                        {selected === entry.id ? 'bg-lf-checked text-lf-on-checked' : entry.count === 0 ? 'text-lf-muted hover:bg-lf-hover' : 'text-lf-secondary hover:bg-lf-hover'}"
                >
                    {#if entry.icon}
                        {@const Icon = entry.icon}
                        <Icon size={16} class="mr-2" />
                    {/if}
                    <span class="flex-1 text-left">{entry.label}</span>
                    {#if entry.dot}
                        <span class="ml-1.5 size-2 shrink-0 rounded-full bg-lf-warning" data-testid="{testIdPrefix}-category-dot" title={dotLabel}><span class="sr-only">{dotLabel}</span></span>
                    {/if}
                    {#if entry.count !== undefined}
                        <span class="ml-2 text-xs tabular-nums {selected === entry.id ? '' : 'text-lf-muted'}">{entry.count}</span>
                    {/if}
                    {#if selected === entry.id}
                        <ChevronRight size={16} />
                    {/if}
                </button>
            {/each}
        </nav>
    </div>
{/if}
