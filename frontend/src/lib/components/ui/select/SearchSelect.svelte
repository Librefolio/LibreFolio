<!--
  SearchSelect.svelte - Svelte 5

  Dropdown select with fuzzy search functionality.
  Supports keyboard navigation and custom item rendering via snippets.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';
    import type {SelectOption} from './types';
    import {ChevronDown, Search, X, Plus} from 'lucide-svelte';
    import {_} from '$lib/i18n';

    interface Props {
        /** Currently selected value */
        value: string;
        /** Available options */
        options: SelectOption[];
        /** Placeholder when no value selected */
        placeholder?: string;
        /** Disable the select */
        disabled?: boolean;
        /** Show loading state */
        loading?: boolean;
        /** Position of dropdown: 'top', 'bottom', or 'auto' (based on available space) */
        dropdownPosition?: 'top' | 'bottom' | 'auto';
        /** Use inline search in trigger (like BrokerSelect) instead of separate search field */
        inlineSearch?: boolean;
        /** Maximum visible items in dropdown (default: 8) */
        maxVisibleItems?: number;
        /** Custom class for container */
        class?: string;
        /** Custom item rendering */
        item?: Snippet<[SelectOption]>;
        /** Custom selected item rendering (for trigger) */
        selectedItem?: Snippet<[SelectOption]>;
        /** Change callback */
        onchange?: (value: string) => void;
        /** Compact mode: smaller trigger padding to match standard inputs */
        compact?: boolean;
        /** W43/W44: Label for the "Create new" sticky footer action.
         *  When set (non-empty), a persistent footer row is rendered at the
         *  bottom of the dropdown. Clicking it fires `onCreateNew`. */
        createLabel?: string;
        /** W43/W44: Callback fired when the "Create new" footer is clicked. */
        onCreateNew?: () => void;
    }

    let {value = $bindable(''), options, placeholder = '', disabled = false, loading = false, dropdownPosition = 'bottom', inlineSearch = false, maxVisibleItems = 8, class: className = '', item, selectedItem, onchange, compact = false, createLabel = '', onCreateNew}: Props = $props();

    // Internal state
    let isOpen = $state(false);
    let searchQuery = $state('');
    let highlightedIndex = $state(0);
    let inputRef: HTMLInputElement | null = $state(null);
    let containerRef: HTMLDivElement | null = $state(null);
    let computedPosition: 'top' | 'bottom' = $state('bottom');
    let dynamicMaxHeight = $state(0);
    /** Timestamp when trigger received focus — used to debounce Enter after advanceFocus */
    let triggerFocusedAt = $state(0);
    /** Fixed dropdown position for portal-like rendering (avoids overflow clipping) */
    let dropdownStyle = $state('');

    // Derived state
    let selectedOption = $derived(options.find((o) => o.value === value));

    /** Detect URL-style icons (e.g. `/icons/foo.png`, `https://…`) so we can
     *  render them as `<img>` instead of leaking the URL string into a
     *  text node (Bugfix-2 §C7). Emoji/short single-char icons stay as text. */
    function looksLikeUrl(s: string | undefined | null): boolean {
        if (!s) return false;
        return s.startsWith('/') || s.startsWith('http://') || s.startsWith('https://') || s.startsWith('data:');
    }
    function hideOnError(e: Event) {
        const img = e.currentTarget as HTMLImageElement | null;
        if (img) img.style.display = 'none';
    }

    // Item height approximation (px per item)
    const ITEM_HEIGHT = 44;

    // Calculate max height based on maxVisibleItems
    let maxDropdownHeight = $derived(maxVisibleItems * ITEM_HEIGHT);

    // Filter options based on search query
    let filteredOptions = $derived(
        searchQuery.trim() === ''
            ? options
            : options.filter((o) => o.value.toLowerCase().includes(searchQuery.toLowerCase()) || o.label.toLowerCase().includes(searchQuery.toLowerCase()) || (o.searchText && o.searchText.toLowerCase().includes(searchQuery.toLowerCase())) || (o.icon && o.icon.includes(searchQuery))),
    );

    // Compute dropdown position and dynamic height based on available space
    function updateDropdownPosition() {
        if (!containerRef) {
            computedPosition = dropdownPosition === 'top' ? 'top' : 'bottom';
            dynamicMaxHeight = maxDropdownHeight;
            dropdownStyle = '';
            return;
        }

        const rect = containerRef.getBoundingClientRect();
        // Bugfix-3 §U15: 80px padding from viewport edges so the dropdown
        // doesn't overlap modal footers (typical footer height ~60px + slack).
        const padding = 80;

        const spaceBelow = window.innerHeight - rect.bottom - padding;
        const spaceAbove = rect.top - padding;

        // Calculate how many items can fit in each direction
        const itemsFitBelow = Math.floor(spaceBelow / ITEM_HEIGHT);
        const itemsFitAbove = Math.floor(spaceAbove / ITEM_HEIGHT);

        // Cap at maxVisibleItems
        const maxBelow = Math.min(itemsFitBelow, maxVisibleItems);
        const maxAbove = Math.min(itemsFitAbove, maxVisibleItems);

        // If explicit position set (not auto), use it
        if (dropdownPosition !== 'auto') {
            computedPosition = dropdownPosition;
            dynamicMaxHeight = (dropdownPosition === 'top' ? maxAbove : maxBelow) * ITEM_HEIGHT;
            // Ensure at least 2 items visible
            dynamicMaxHeight = Math.max(dynamicMaxHeight, ITEM_HEIGHT * 2);
        } else {
            // Auto: choose direction with more space, prefer bottom if equal
            if (maxBelow >= maxAbove || maxBelow >= maxVisibleItems) {
                computedPosition = 'bottom';
                dynamicMaxHeight = Math.max(maxBelow, 2) * ITEM_HEIGHT;
            } else {
                computedPosition = 'top';
                dynamicMaxHeight = Math.max(maxAbove, 2) * ITEM_HEIGHT;
            }
        }

        // Compute fixed position style to escape overflow:hidden containers
        const totalDropdownHeight = dynamicMaxHeight + 50; // account for search bar
        if (computedPosition === 'bottom') {
            dropdownStyle = `position:fixed; top:${rect.bottom + 4}px; left:${rect.left}px; width:${rect.width}px; z-index:9999;`;
        } else {
            dropdownStyle = `position:fixed; bottom:${window.innerHeight - rect.top + 4}px; left:${rect.left}px; width:${rect.width}px; z-index:9999;`;
        }
    }

    // Reset highlight when filtered options change
    $effect(() => {
        if (filteredOptions.length > 0 && highlightedIndex >= filteredOptions.length) {
            highlightedIndex = 0;
        }
    });

    // Close on click outside
    $effect(() => {
        if (!isOpen) return;

        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef && !containerRef.contains(event.target as Node)) {
                closeDropdown();
            }
        };

        document.addEventListener('mousedown', handleClickOutside, true);
        return () => document.removeEventListener('mousedown', handleClickOutside, true);
    });

    // Reposition dropdown on scroll/resize while open
    $effect(() => {
        if (!isOpen) return;

        const reposition = () => updateDropdownPosition();
        window.addEventListener('scroll', reposition, true);
        window.addEventListener('resize', reposition);
        return () => {
            window.removeEventListener('scroll', reposition, true);
            window.removeEventListener('resize', reposition);
        };
    });

    // Focus search input when dropdown opens
    $effect(() => {
        if (isOpen && inputRef) {
            setTimeout(() => inputRef?.focus(), 10);
        }
    });

    function openDropdown() {
        if (disabled) return;
        // Prevent immediate reopen after close (touch event race)
        if (Date.now() - lastClosedAt < 200) return;
        updateDropdownPosition();
        isOpen = true;
        searchQuery = '';
        highlightedIndex = 0;
    }

    /** Timestamp of last close — used to prevent immediate reopen on touch devices */
    let lastClosedAt = 0;

    function closeDropdown() {
        isOpen = false;
        searchQuery = '';
        lastClosedAt = Date.now();
        // Return focus to the trigger so the next click works reliably
        if (containerRef) {
            const trigger = containerRef.querySelector<HTMLElement>('[role="combobox"]');
            trigger?.focus();
        }
    }

    function toggleDropdown() {
        if (disabled) return;
        if (isOpen) {
            closeDropdown();
        } else {
            openDropdown();
        }
    }

    function selectOption(option: SelectOption, advanceFocus = false) {
        if (option.disabled) return;
        value = option.value;
        onchange?.(option.value);
        closeDropdown();
        if (advanceFocus && containerRef) {
            // Move focus to the next focusable element after closing
            setTimeout(() => {
                const all = Array.from(document.querySelectorAll<HTMLElement>('[tabindex]:not([tabindex="-1"]), input:not([disabled]), select:not([disabled]), button:not([disabled]), a[href]')).filter((el) => el.offsetParent !== null);
                const idx = all.indexOf(containerRef!.querySelector<HTMLElement>('[tabindex]') ?? containerRef!);
                if (idx >= 0 && idx + 1 < all.length) {
                    all[idx + 1].focus();
                }
            }, 20);
        }
    }

    function handleTriggerKeydown(event: KeyboardEvent) {
        if (disabled) return;

        if (!isOpen) {
            if (event.key === 'Enter' || event.key === ' ' || event.key === 'ArrowDown') {
                // Don't auto-open on Enter if trigger just received focus and a value is already set
                // (prevents unwanted dropdown after advanceFocus/Tab from another select)
                if (event.key === 'Enter' && value && Date.now() - triggerFocusedAt < 200) {
                    event.preventDefault();
                    return;
                }
                event.preventDefault();
                openDropdown();
            } else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
                // Printable character: open dropdown and start searching
                event.preventDefault();
                openDropdown();
                // Defer setting searchQuery so the input is mounted first
                setTimeout(() => {
                    searchQuery = event.key;
                }, 20);
            }
            return;
        }

        // When open with inlineSearch, handle keyboard navigation here too
        if (inlineSearch) {
            handleSearchKeydown(event);
        }
    }

    function handleSearchKeydown(event: KeyboardEvent) {
        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                highlightedIndex = Math.min(highlightedIndex + 1, filteredOptions.length - 1);
                scrollToHighlighted();
                break;
            case 'ArrowUp':
                event.preventDefault();
                highlightedIndex = Math.max(highlightedIndex - 1, 0);
                scrollToHighlighted();
                break;
            case 'Enter':
                event.preventDefault();
                if (filteredOptions.length > 0) {
                    // Select highlighted or first option
                    const indexToSelect = highlightedIndex >= 0 ? highlightedIndex : 0;
                    if (filteredOptions[indexToSelect]) {
                        selectOption(filteredOptions[indexToSelect], true);
                    }
                }
                break;
            case 'Escape':
                event.preventDefault();
                closeDropdown();
                break;
        }
    }

    // Unique ID for aria-controls
    const listboxId = `searchselect-listbox-${Math.random().toString(36).substring(2, 9)}`;

    function scrollToHighlighted() {
        setTimeout(() => {
            const listEl = containerRef?.querySelector('.options-list');
            const highlightedEl = listEl?.querySelector('.highlighted');
            if (highlightedEl) {
                highlightedEl.scrollIntoView({block: 'nearest'});
            }
        }, 0);
    }
</script>

<div bind:this={containerRef} class="relative {className}">
    <!-- Trigger Button / Inline Search -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        aria-controls={listboxId}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        class="w-full flex items-center justify-between {compact ? 'px-3 py-2 text-sm' : 'px-3 py-2'} border rounded-lg
               transition-all text-left gap-2
               {disabled ? 'bg-gray-100 dark:bg-slate-800 text-gray-400 dark:text-gray-500 cursor-not-allowed opacity-60' : 'bg-white dark:bg-slate-700 dark:border-slate-600 hover:border-gray-400 dark:hover:border-slate-500 cursor-pointer'}
               {isOpen ? 'ring-2 ring-libre-green border-libre-green' : ''}"
        onclick={() => toggleDropdown()}
        onfocus={() => {
            triggerFocusedAt = Date.now();
        }}
        onkeydown={handleTriggerKeydown}
        role="combobox"
        tabindex={disabled ? -1 : 0}
    >
        {#if inlineSearch && isOpen}
            <!-- Inline search mode: show search icon + input in trigger -->
            <Search size={14} class="text-gray-400 shrink-0" />
            <input
                type="text"
                bind:this={inputRef}
                bind:value={searchQuery}
                onkeydown={(e) => {
                    e.stopPropagation();
                    handleSearchKeydown(e);
                }}
                onclick={(e) => e.stopPropagation()}
                class="flex-1 min-w-0 bg-transparent border-none outline-none text-sm text-gray-900 dark:text-gray-100"
                placeholder={$_('common.search')}
            />
        {:else if selectedOption}
            {#if selectedItem}
                <div class="flex-1 min-w-0">
                    {@render selectedItem(selectedOption)}
                </div>
            {:else}
                <div class="flex items-center space-x-2 min-w-0">
                    {#if selectedOption.icon && selectedOption.icon !== selectedOption.value}
                        {#if looksLikeUrl(selectedOption.icon)}
                            <span class="shrink-0 w-9 h-9 flex items-center justify-center bg-libre-green/10 dark:bg-libre-green/20 rounded-lg overflow-hidden">
                                <img src={selectedOption.icon} alt="" class="w-7 h-7 object-contain" onerror={hideOnError} />
                            </span>
                        {:else}
                            <span class="text-lg shrink-0 w-9 h-9 flex items-center justify-center bg-libre-green/20 text-libre-green rounded-lg font-medium emoji-flag">
                                {selectedOption.icon}
                            </span>
                        {/if}
                    {/if}
                    <div class="min-w-0">
                        <div class="font-medium text-gray-900 dark:text-gray-100">{selectedOption.value}</div>
                        <div class="text-xs text-gray-500 dark:text-gray-400 truncate">{selectedOption.label}</div>
                    </div>
                </div>
            {/if}
        {:else}
            <span class="text-gray-400">{placeholder || $_('common.search')}</span>
        {/if}
        <ChevronDown class="text-gray-400 shrink-0 transition-transform {isOpen ? 'rotate-180' : ''}" size={14} />
    </div>

    <!-- Dropdown -->
    {#if isOpen}
        <div class="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg shadow-lg overflow-hidden" style={dropdownStyle}>
            {#if !inlineSearch}
                <div class="p-2 border-b border-gray-100 dark:border-slate-700">
                    <div class="relative">
                        <Search size={16} class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input
                            bind:this={inputRef}
                            bind:value={searchQuery}
                            onkeydown={handleSearchKeydown}
                            type="text"
                            class="w-full pl-9 pr-8 py-2 text-sm border border-gray-200 dark:border-slate-600 dark:bg-slate-700 dark:text-white rounded-lg
                               focus:outline-none focus:ring-2 focus:ring-libre-green focus:border-libre-green"
                            placeholder={$_('common.search')}
                        />
                        {#if searchQuery}
                            <button onclick={() => (searchQuery = '')} class="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600">
                                <X size={14} />
                            </button>
                        {/if}
                    </div>
                </div>
            {/if}

            <!-- Options List -->
            <div class="overflow-y-auto options-list" id={listboxId} role="listbox" style="max-height: {dynamicMaxHeight}px">
                {#if loading}
                    <div class="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                        {$_('common.loading')}
                    </div>
                {:else if filteredOptions.length === 0}
                    <div class="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                        {$_('common.noData')}
                    </div>
                {:else}
                    {#each filteredOptions as option, index (option.value)}
                        <button
                            type="button"
                            onclick={() => selectOption(option)}
                            onmouseenter={() => (highlightedIndex = index)}
                            disabled={option.disabled}
                            data-testid="search-select-option-{option.value}"
                            class="w-full flex items-center space-x-3 px-4 py-2.5 text-left transition-colors
                                   {option.disabled ? 'opacity-50 cursor-not-allowed' : ''}
                                   {index === highlightedIndex ? 'bg-libre-green/30 dark:bg-libre-green dark:text-white highlighted' : 'hover:bg-gray-100 dark:hover:bg-slate-600'}"
                        >
                            {#if item}
                                <div class="flex-1 min-w-0">
                                    {@render item(option)}
                                </div>
                            {:else}
                                {#if option.icon && option.icon !== option.value}
                                    {#if looksLikeUrl(option.icon)}
                                        <span class="shrink-0 w-9 h-9 flex items-center justify-center bg-libre-green/10 dark:bg-libre-green/20 rounded-lg overflow-hidden">
                                            <img src={option.icon} alt="" class="w-7 h-7 object-contain" onerror={hideOnError} />
                                        </span>
                                    {:else}
                                        <span class="text-lg w-9 h-9 flex items-center justify-center bg-libre-green/20 text-libre-green rounded-lg shrink-0 font-medium emoji-flag">
                                            {option.icon}
                                        </span>
                                    {/if}
                                {/if}
                                <div class="min-w-0 flex-1">
                                    <div class="font-mono text-sm text-gray-700 dark:text-gray-200">{option.value}</div>
                                    <div class="text-xs text-gray-500 dark:text-gray-400 truncate">{option.label}</div>
                                </div>
                            {/if}
                        </button>
                    {/each}
                {/if}
            </div>

            <!-- W43/W44: Sticky "Create new" footer -->
            {#if createLabel && onCreateNew}
                <button
                    type="button"
                    class="w-full flex items-center gap-2 px-4 py-2.5 text-left text-sm text-libre-green hover:bg-libre-green/10 dark:hover:bg-libre-green/20 border-t border-gray-100 dark:border-slate-700 transition-colors"
                    onclick={(e) => {
                        e.stopPropagation();
                        closeDropdown();
                        onCreateNew?.();
                    }}
                    data-testid="search-select-create-new"
                >
                    <Plus size={14} class="shrink-0" />
                    <span class="font-medium">{createLabel}</span>
                </button>
            {/if}
        </div>
    {/if}
</div>
