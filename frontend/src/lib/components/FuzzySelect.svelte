<script lang="ts" module>
    /**
     * FuzzySelect - A reusable searchable dropdown component
     *
     * Works with any data source that provides items with:
     * - code: unique identifier (e.g., "EUR", "USA")
     * - label: display text (e.g., "Euro", "United States")
     * - icon?: optional emoji or icon (e.g., "€", "🇺🇸")
     */

    export interface SelectOption {
        code: string;
        label: string;
        icon?: string;
    }
</script>

<script lang="ts">
    import {_} from '$lib/i18n';
    import {createEventDispatcher, onMount} from 'svelte';
    import {ChevronDown, Search, X} from 'lucide-svelte';

    const dispatch = createEventDispatcher();

    // Props
    export let value: string = '';
    export let options: SelectOption[] = [];
    export let placeholder: string = 'Search...';
    export let disabled: boolean = false;
    export let loading: boolean = false;
    export let dropdownPosition: 'bottom' | 'top' = 'bottom';

    // Internal state
    let isOpen = false;
    let searchQuery = '';
    let highlightedIndex = 0;
    let inputRef: HTMLInputElement;
    let containerRef: HTMLDivElement;

    // Find selected option
    $: selectedOption = options.find(o => o.code === value);

    // Filter options based on search
    $: filteredOptions = searchQuery.trim() === ''
        ? options
        : options.filter(o =>
            o.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
            o.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (o.icon && o.icon.includes(searchQuery))
        );

    // Reset highlight when filtered options change
    $: if (filteredOptions.length > 0 && highlightedIndex >= filteredOptions.length) {
        highlightedIndex = 0;
    }

    function openDropdown() {
        if (disabled) return;
        isOpen = true;
        searchQuery = '';
        highlightedIndex = 0;
        setTimeout(() => inputRef?.focus(), 10);
    }

    function closeDropdown() {
        isOpen = false;
        searchQuery = '';
    }

    function selectOption(option: SelectOption) {
        value = option.code;
        dispatch('change', {value: option.code, option});
        closeDropdown();
    }

    function handleKeydown(event: KeyboardEvent) {
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
                highlightedIndex = Math.min(highlightedIndex + 1, filteredOptions.length - 1);
                break;
            case 'ArrowUp':
                event.preventDefault();
                highlightedIndex = Math.max(highlightedIndex - 1, 0);
                break;
            case 'Enter':
                event.preventDefault();
                if (filteredOptions[highlightedIndex]) {
                    selectOption(filteredOptions[highlightedIndex]);
                }
                break;
            case 'Escape':
                event.preventDefault();
                closeDropdown();
                break;
        }
    }

    function handleClickOutside(event: MouseEvent) {
        if (containerRef && !containerRef.contains(event.target as Node)) {
            closeDropdown();
        }
    }

    onMount(() => {
        document.addEventListener('click', handleClickOutside);
        return () => document.removeEventListener('click', handleClickOutside);
    });
</script>

<div class="relative" bind:this={containerRef}>
    <!-- Trigger Button -->
    <button
            type="button"
            on:click={openDropdown}
            on:keydown={handleKeydown}
            {disabled}
            class="w-full flex items-center justify-between px-4 py-2.5 border rounded-lg bg-white dark:bg-slate-700
                   transition-all text-left
                   {disabled ? 'bg-gray-100 dark:bg-slate-800 text-gray-400 cursor-not-allowed' : 'dark:border-slate-600 hover:border-gray-400 dark:hover:border-slate-500'}
                   {isOpen ? 'ring-2 ring-libre-green border-libre-green' : ''}"
    >
        {#if selectedOption}
            <div class="flex items-center space-x-2 min-w-0">
                {#if selectedOption.icon && selectedOption.icon !== selectedOption.code}
                    <span class="text-lg shrink-0 w-9 h-9 flex items-center justify-center bg-libre-green/20 text-libre-green rounded-lg font-medium">{selectedOption.icon}</span>
                {/if}
                <div class="min-w-0">
                    <div class="font-medium text-gray-900 dark:text-gray-100">{selectedOption.code}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400 truncate">{selectedOption.label}</div>
                </div>
            </div>
        {:else}
            <span class="text-gray-400">{placeholder}</span>
        {/if}
        <ChevronDown size={18} class="text-gray-400 shrink-0 transition-transform {isOpen ? 'rotate-180' : ''}"/>
    </button>

    <!-- Dropdown -->
    {#if isOpen}
        <div class="absolute z-50 w-full bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg shadow-lg overflow-hidden
                    {dropdownPosition === 'top' ? 'bottom-full mb-1' : 'top-full mt-1'}">
            <!-- Search Input -->
            <div class="p-2 border-b border-gray-100 dark:border-slate-700">
                <div class="relative">
                    <Search size={16} class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"/>
                    <input
                            bind:this={inputRef}
                            bind:value={searchQuery}
                            on:keydown={handleKeydown}
                            type="text"
                            class="w-full pl-9 pr-8 py-2 text-sm border border-gray-200 dark:border-slate-600 dark:bg-slate-700 dark:text-white rounded-lg
                                   focus:outline-none focus:ring-2 focus:ring-libre-green focus:border-libre-green"
                            placeholder={$_('common.search')}
                    />
                    {#if searchQuery}
                        <button
                                on:click={() => searchQuery = ''}
                                class="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600"
                        >
                            <X size={14}/>
                        </button>
                    {/if}
                </div>
            </div>

            <!-- Options List -->
            <div class="max-h-60 overflow-y-auto">
                {#if loading}
                    <div class="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                        {$_('common.loading')}
                    </div>
                {:else if filteredOptions.length === 0}
                    <div class="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                        {$_('common.noData')}
                    </div>
                {:else}
                    {#each filteredOptions as option, index}
                        <button
                                type="button"
                                on:click={() => selectOption(option)}
                                on:mouseenter={() => highlightedIndex = index}
                                class="w-full flex items-center space-x-3 px-4 py-2.5 text-left transition-colors
                                       {index === highlightedIndex ? 'bg-libre-green/10 dark:bg-libre-green/20' : 'hover:bg-gray-50 dark:hover:bg-slate-700'}
                                       {option.code === value ? 'bg-libre-green/5 dark:bg-libre-green/10 font-medium' : ''}"
                        >
                            {#if option.icon && option.icon !== option.code}
                                <span class="text-lg w-9 h-9 flex items-center justify-center bg-libre-green/20 text-libre-green rounded-lg shrink-0 font-medium">{option.icon}</span>
                            {/if}
                            <div class="min-w-0 flex-1">
                                <div class="font-mono text-sm text-gray-700 dark:text-gray-200">{option.code}</div>
                                <div class="text-xs text-gray-500 dark:text-gray-400 truncate">{option.label}</div>
                            </div>
                        </button>
                    {/each}
                {/if}
            </div>
        </div>
    {/if}
</div>

