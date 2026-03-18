<!--
  SimpleSelect.svelte - Svelte 5

  Simple dropdown select without search functionality.
  Supports keyboard navigation and custom item rendering via snippets.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';
    import type {SelectOption} from './types';
    import {Check, ChevronDown} from 'lucide-svelte';
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
        /** Position of dropdown */
        dropdownPosition?: 'top' | 'bottom' | 'auto';
        /** Custom class for container */
        class?: string;
        /** Test ID for E2E testing (adds -button suffix to trigger) */
        testId?: string;
        /** Custom item rendering */
        item?: Snippet<[SelectOption]>;
        /** Custom selected item rendering (for trigger) */
        selectedItem?: Snippet<[SelectOption]>;
        /** Change callback */
        onchange?: (value: string) => void;
        /** Compact mode: smaller padding, text-xs, thinner border */
        compact?: boolean;
        /** Show chevron icon in trigger button (default: true) */
        showChevron?: boolean;
    }

    let {
        value = $bindable(''),
        options,
        placeholder = '',
        disabled = false,
        loading = false,
        dropdownPosition = 'bottom',
        class: className = '',
        testId,
        item,
        selectedItem,
        onchange,
        compact = false,
        showChevron = true,
    }: Props = $props();

    // Internal state
    let isOpen = $state(false);
    let highlightedIndex = $state(-1);
    let containerRef = $state<HTMLDivElement | null>(null);
    let computedPosition = $state<'top' | 'bottom'>('bottom');
    let dropdownMaxHeight = $state<string>('15rem');

    // Derived state
    let selectedOption = $derived(options.find(o => o.value === value));

    // Compute dropdown position when opening
    function updateDropdownPosition() {
        if (dropdownPosition !== 'auto' || !containerRef) {
            computedPosition = dropdownPosition === 'top' ? 'top' : 'bottom';
            dropdownMaxHeight = '15rem';
            return;
        }
        const rect = containerRef.getBoundingClientRect();
        const padding = 20;

        // Walk up to find the closest scrollable parent
        let scrollParent = containerRef.parentElement;
        let parentBottom = window.innerHeight;
        let parentTop = 0;
        while (scrollParent) {
            const style = getComputedStyle(scrollParent);
            if (style.overflowY === 'auto' || style.overflowY === 'scroll') {
                const pRect = scrollParent.getBoundingClientRect();
                parentBottom = pRect.bottom;
                parentTop = pRect.top;
                break;
            }
            scrollParent = scrollParent.parentElement;
        }

        const spaceBelow = parentBottom - rect.bottom - padding;
        const spaceAbove = rect.top - parentTop - padding;
        computedPosition = (spaceBelow < 200 && spaceAbove > spaceBelow) ? 'top' : 'bottom';
        // Limit dropdown height to actual available space (min 120px, max 240px)
        const available = computedPosition === 'top' ? spaceAbove : spaceBelow;
        dropdownMaxHeight = `${Math.max(120, Math.min(240, available))}px`;
    }

    // Reset highlight when options change
    $effect(() => {
        if (options) {
            highlightedIndex = -1;
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

    function openDropdown() {
        if (disabled || loading) return;
        updateDropdownPosition();
        isOpen = true;
        highlightedIndex = -1;
    }

    function closeDropdown() {
        isOpen = false;
        highlightedIndex = -1;
    }

    function toggleDropdown() {
        if (isOpen) {
            closeDropdown();
        } else {
            openDropdown();
        }
    }

    function selectOption(option: SelectOption) {
        if (option.disabled) return;
        value = option.value;
        onchange?.(option.value);
        closeDropdown();
    }

    function handleKeydown(event: KeyboardEvent) {
        if (disabled || loading) return;

        if (!isOpen) {
            if (event.key === 'Enter' || event.key === ' ' || event.key === 'ArrowDown') {
                event.preventDefault();
                openDropdown();
            }
            return;
        }

        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                highlightedIndex = Math.min(highlightedIndex + 1, options.length - 1);
                break;
            case 'ArrowUp':
                event.preventDefault();
                highlightedIndex = Math.max(highlightedIndex - 1, 0);
                break;
            case 'Enter':
                event.preventDefault();
                if (highlightedIndex >= 0 && options[highlightedIndex]) {
                    selectOption(options[highlightedIndex]);
                }
                break;
            case 'Escape':
                event.preventDefault();
                closeDropdown();
                break;
        }
    }
</script>

<div bind:this={containerRef} class="relative {className}" data-testid={testId}>
    <!-- Trigger Button -->
    <button
            class="w-full flex items-center justify-between {compact ? 'px-1.5 py-0.5 text-xs' : 'px-3 py-2 text-sm'} border rounded-lg transition-all text-left
               {disabled || loading
                   ? 'bg-gray-100 dark:bg-slate-800 text-gray-500 dark:text-gray-400 cursor-not-allowed border-gray-200 dark:border-slate-700'
                   : 'bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 border-gray-300 dark:border-slate-600 hover:border-gray-400 dark:hover:border-slate-500'}
               {isOpen ? 'ring-2 ring-libre-green border-libre-green' : ''}"
            data-testid={testId ? `${testId}-button` : undefined}
            {disabled}
            onclick={toggleDropdown}
            onkeydown={handleKeydown}
            type="button"
    >
        {#if selectedOption}
            {#if selectedItem}
                {@render selectedItem(selectedOption)}
            {:else if selectedOption.icon}
                <span class="truncate">{selectedOption.icon} {selectedOption.label}</span>
            {:else}
                <span class="truncate">{selectedOption.label}</span>
            {/if}
        {:else}
            <span class="text-gray-400">{placeholder || $_('common.select')}</span>
        {/if}
        {#if showChevron}
            <ChevronDown
                    class="ml-2 flex-shrink-0 text-gray-400 transition-transform {isOpen ? 'rotate-180' : ''}"
                    size={compact ? 12 : 16}
            />
        {/if}
    </button>

    <!-- Dropdown Menu -->
    {#if isOpen}
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
                class="absolute z-50 w-max min-w-full bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700
                   rounded-lg shadow-lg max-h-60 overflow-y-auto
                   {computedPosition === 'top' ? 'bottom-full mb-1' : 'top-full mt-1'}"
                style:max-height={dropdownMaxHeight}
                onwheel={(e) => e.stopPropagation()}
                ontouchmove={(e) => e.stopPropagation()}
        >
            {#if loading}
                <div class="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                    {$_('common.loading')}
                </div>
            {:else if options.length === 0}
                <div class="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                    {$_('common.noData')}
                </div>
            {:else}
                {#each options as option, index (option.value)}
                    <button
                            type="button"
                            role="menuitem"
                            onclick={() => selectOption(option)}
                            onmouseenter={() => highlightedIndex = index}
                            disabled={option.disabled}
                            class="w-full flex items-center justify-between px-3 py-2 text-sm text-left transition-colors
                               {option.disabled ? 'opacity-50 cursor-not-allowed' : ''}
                               {index === highlightedIndex ? 'bg-libre-green/10 dark:bg-libre-green/20' : 'hover:bg-gray-50 dark:hover:bg-slate-700'}
                               {value === option.value ? 'bg-libre-green/5 dark:bg-libre-green/10 text-libre-green dark:text-green-400' : 'text-gray-900 dark:text-gray-100'}"
                    >
                        {#if item}
                            <div class="flex-1 min-w-0">
                                {@render item(option)}
                            </div>
                        {:else if option.icon}
                            <span class="truncate">{option.icon} {option.label}</span>
                        {:else}
                            <span class="truncate">{option.label}</span>
                        {/if}
                        {#if value === option.value}
                            <Check size={16} class="ml-2 flex-shrink-0 text-libre-green dark:text-green-400"/>
                        {/if}
                    </button>
                {/each}
            {/if}
        </div>
    {/if}
</div>
