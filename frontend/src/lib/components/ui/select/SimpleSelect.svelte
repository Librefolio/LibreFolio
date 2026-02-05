<!--
  SimpleSelect.svelte - Svelte 5

  Simple dropdown select without search functionality.
  Supports keyboard navigation and custom item rendering via snippets.
-->
<script lang="ts">
    import type { Snippet } from 'svelte';
    import type { SelectOption } from './types';
    import { ChevronDown, Check } from 'lucide-svelte';
    import { _ } from '$lib/i18n';

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
        dropdownPosition?: 'top' | 'bottom';
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
        onchange
    }: Props = $props();

    // Internal state
    let isOpen = $state(false);
    let highlightedIndex = $state(-1);
    let containerRef = $state<HTMLDivElement | null>(null);

    // Derived state
    let selectedOption = $derived(options.find(o => o.value === value));

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

<div class="relative {className}" bind:this={containerRef} data-testid={testId}>
    <!-- Trigger Button -->
    <button
        type="button"
        onclick={toggleDropdown}
        onkeydown={handleKeydown}
        {disabled}
        data-testid={testId ? `${testId}-button` : undefined}
        class="w-full flex items-center justify-between px-3 py-2 border rounded-lg text-sm transition-all text-left
               {disabled || loading
                   ? 'bg-gray-100 dark:bg-slate-800 text-gray-500 dark:text-gray-400 cursor-not-allowed border-gray-200 dark:border-slate-700'
                   : 'bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 border-gray-300 dark:border-slate-600 hover:border-gray-400 dark:hover:border-slate-500'}
               {isOpen ? 'ring-2 ring-libre-green border-libre-green' : ''}"
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
        <ChevronDown
            size={16}
            class="ml-2 flex-shrink-0 text-gray-400 transition-transform {isOpen ? 'rotate-180' : ''}"
        />
    </button>

    <!-- Dropdown Menu -->
    {#if isOpen}
        <div
            class="absolute z-50 w-full bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700
                   rounded-lg shadow-lg max-h-60 overflow-y-auto
                   {dropdownPosition === 'top' ? 'bottom-full mb-1' : 'top-full mt-1'}"
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
