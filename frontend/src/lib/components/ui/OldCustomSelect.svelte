<script lang="ts" module>
    /**
     * @deprecated Use SimpleSelect from '$lib/components/ui/select' instead.
     * This component will be removed in a future version.
     *
     * CustomSelect.svelte
     * A simple custom dropdown select that works well on mobile.
     * For complex selects with search, use SimpleSelect instead.
     */
    export interface SelectOption {
        code: string;
        label: string;
        icon?: string;
    }
</script>

<script lang="ts">
    import { createEventDispatcher, onMount, onDestroy } from 'svelte';
    import { ChevronDown, Check } from 'lucide-svelte';

    const dispatch = createEventDispatcher<{
        change: { value: string; option: SelectOption };
    }>();


    // Props
    export let value: string;
    export let options: SelectOption[] = [];
    export let placeholder: string = 'Select...';
    export let disabled: boolean = false;
    export let loading: boolean = false;

    // State
    let isOpen = false;
    let dropdownRef: HTMLDivElement;

    // Find selected option
    $: selectedOption = options.find(o => o.code === value);
    $: displayText = selectedOption
        ? (selectedOption.icon ? `${selectedOption.icon} ${selectedOption.label}` : selectedOption.label)
        : placeholder;

    function toggleDropdown() {
        if (!disabled && !loading) {
            isOpen = !isOpen;
        }
    }

    function selectOption(option: SelectOption) {
        value = option.code;
        isOpen = false;
        dispatch('change', { value: option.code, option });
    }

    function handleClickOutside(event: MouseEvent) {
        if (dropdownRef && !dropdownRef.contains(event.target as Node)) {
            isOpen = false;
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            isOpen = false;
        }
    }

    onMount(() => {
        document.addEventListener('click', handleClickOutside);
        document.addEventListener('keydown', handleKeydown);
    });

    onDestroy(() => {
        document.removeEventListener('click', handleClickOutside);
        document.removeEventListener('keydown', handleKeydown);
    });
</script>

<div class="relative" bind:this={dropdownRef}>
    <!-- Trigger button -->
    <button
        type="button"
        on:click={toggleDropdown}
        {disabled}
        class="w-full flex items-center justify-between px-3 py-2 border rounded-lg text-sm transition-all
               {disabled || loading
                   ? 'bg-gray-100 dark:bg-slate-800 text-gray-500 dark:text-gray-400 cursor-not-allowed border-gray-200 dark:border-slate-700'
                   : 'bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 border-gray-300 dark:border-slate-600 hover:border-gray-400 dark:hover:border-slate-500'}
               {isOpen ? 'ring-2 ring-libre-green border-libre-green' : ''}"
    >
        <span class="truncate">{displayText}</span>
        <ChevronDown
            size={16}
            class="ml-2 flex-shrink-0 text-gray-400 transition-transform {isOpen ? 'rotate-180' : ''}"
        />
    </button>

    <!-- Dropdown menu -->
    {#if isOpen}
        <div
            class="absolute z-50 mt-1 w-full bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700
                   rounded-lg shadow-lg max-h-60 overflow-y-auto"
        >
            {#each options as option (option.code)}
                <button
                    type="button"
                    on:click={() => selectOption(option)}
                    class="w-full flex items-center justify-between px-3 py-2 text-sm text-left
                           hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors
                           {value === option.code ? 'bg-libre-green/10 text-libre-green dark:text-green-400' : 'text-gray-900 dark:text-gray-100'}"
                >
                    <span class="truncate">
                        {#if option.icon}
                            {option.icon}
                        {/if}
                        {option.label}
                    </span>
                    {#if value === option.code}
                        <Check size={16} class="ml-2 flex-shrink-0 text-libre-green dark:text-green-400"/>
                    {/if}
                </button>
            {/each}
        </div>
    {/if}
</div>
