<script lang="ts">
    /**
     * SettingsLayout.svelte
     * Responsive layout for settings pages
     * - Desktop: 2-column (sidebar + content)
     * - Mobile: custom dropdown + content
     */
    import { createEventDispatcher, onMount, onDestroy } from 'svelte';
    import { _ } from '$lib/i18n';
    import { ChevronRight, ChevronDown, Save, Undo, RotateCcw, Lock, Unlock } from 'lucide-svelte';
    import type { ComponentType } from 'svelte';

    const dispatch = createEventDispatcher<{
        saveAll: void;
        undoAll: void;
        resetAll: void;
        toggleLock: void;
    }>();

    interface Category {
        id: string;
        icon: ComponentType;
        labelKey: string;
    }

    // Props
    export let categories: Category[] = [];
    export let selectedCategory: string = '';
    export let hasChanges: boolean = false;
    export let hasNonDefaults: boolean = false;
    export let isLocked: boolean = false;
    export let showLock: boolean = false;
    export let title: string = '';
    export let description: string = '';

    // Mobile dropdown state
    let showDropdown = false;
    let dropdownRef: HTMLDivElement | null = null;

    // Get selected category label for display
    $: selectedCategoryLabel = selectedCategory === ''
        ? $_('settings.all')
        : $_(categories.find(c => c.id === selectedCategory)?.labelKey || 'settings.all');

    // Get selected category icon
    $: selectedCategoryIcon = selectedCategory === ''
        ? null
        : categories.find(c => c.id === selectedCategory)?.icon || null;

    function toggleDropdown() {
        showDropdown = !showDropdown;
    }

    function selectCategory(id: string) {
        selectedCategory = id;
        showDropdown = false;
    }

    // Close dropdown on click outside
    function handleClickOutside(event: MouseEvent) {
        if (dropdownRef && !dropdownRef.contains(event.target as Node)) {
            showDropdown = false;
        }
    }

    onMount(() => {
        document.addEventListener('click', handleClickOutside);
    });

    onDestroy(() => {
        document.removeEventListener('click', handleClickOutside);
    });
</script>

<!-- Mobile: Custom dropdown category selector -->
<div class="sm:hidden mb-4" bind:this={dropdownRef}>
    <span class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
        {$_('settings.category')}
    </span>
    <div class="relative">
        <button
            type="button"
            on:click={toggleDropdown}
            class="w-full flex items-center justify-between px-4 py-3 border border-gray-300 dark:border-slate-600
                   rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 text-sm
                   focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-all"
        >
            <span class="flex items-center gap-2">
                {#if selectedCategoryIcon}
                    <svelte:component this={selectedCategoryIcon} size={16} class="text-gray-500 dark:text-gray-400"/>
                {/if}
                {selectedCategoryLabel}
            </span>
            <ChevronDown size={18} class="text-gray-400 transition-transform {showDropdown ? 'rotate-180' : ''}"/>
        </button>

        {#if showDropdown}
            <div class="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-slate-800 border border-gray-200
                        dark:border-slate-600 rounded-lg shadow-lg overflow-hidden z-50">
                <!-- All Settings option -->
                <button
                    type="button"
                    on:click={() => selectCategory('')}
                    class="w-full flex items-center gap-3 px-4 py-3 text-sm text-left transition-colors
                           {selectedCategory === ''
                               ? 'bg-libre-green/10 text-libre-green font-medium'
                               : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                >
                    <span class="flex-1">{$_('settings.all')}</span>
                    {#if selectedCategory === ''}
                        <ChevronRight size={16}/>
                    {/if}
                </button>

                <!-- Category options -->
                {#each categories as category (category.id)}
                    <button
                        type="button"
                        on:click={() => selectCategory(category.id)}
                        class="w-full flex items-center gap-3 px-4 py-3 text-sm text-left transition-colors
                               {selectedCategory === category.id
                                   ? 'bg-libre-green/10 text-libre-green font-medium'
                                   : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                    >
                        <svelte:component this={category.icon} size={16} class="{selectedCategory === category.id ? 'text-libre-green' : 'text-gray-400'}"/>
                        <span class="flex-1">{$_(category.labelKey)}</span>
                        {#if selectedCategory === category.id}
                            <ChevronRight size={16}/>
                        {/if}
                    </button>
                {/each}
            </div>
        {/if}
    </div>
</div>

<div class="flex flex-col sm:flex-row gap-4 sm:gap-6 min-h-[300px] sm:min-h-[400px]">
    <!-- Desktop: Left sidebar category navigation (hidden on mobile) -->
    <div class="hidden sm:block w-48 flex-shrink-0">
        <nav class="space-y-1">
            <!-- All categories button -->
            <button
                type="button"
                on:click={() => selectedCategory = ''}
                class="w-full flex items-center px-3 py-2 text-sm rounded-lg transition-colors
                    {selectedCategory === ''
                        ? 'bg-libre-green text-white'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700'}"
            >
                <span class="flex-1 text-left">{$_('settings.all')}</span>
                {#if selectedCategory === ''}
                    <ChevronRight size={16}/>
                {/if}
            </button>

            {#each categories as category (category.id)}
                <button
                    type="button"
                    on:click={() => selectedCategory = category.id}
                    class="w-full flex items-center px-3 py-2 text-sm rounded-lg transition-colors
                        {selectedCategory === category.id
                            ? 'bg-libre-green text-white'
                            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700'}"
                >
                    <svelte:component this={category.icon} size={16} class="mr-2"/>
                    <span class="flex-1 text-left">{$_(category.labelKey)}</span>
                    {#if selectedCategory === category.id}
                        <ChevronRight size={16}/>
                    {/if}
                </button>
            {/each}
        </nav>
    </div>

    <!-- Right side: Settings content -->
    <div class="flex-1 space-y-4">
        <!-- Header with actions - Title and icons on same row, description below -->
        <div class="pb-4 border-b border-gray-200 dark:border-slate-700">
            <div class="flex items-center justify-between gap-2 mb-1 min-h-[36px]">
                <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h3>

                <!-- Action buttons - inline with title -->
                {#if showLock || hasChanges || hasNonDefaults}
                    <div class="flex items-center gap-1 flex-shrink-0">
                        {#if !isLocked}
                            {#if hasChanges}
                                <button
                                    type="button"
                                    on:click={() => dispatch('saveAll')}
                                    class="p-2 rounded-lg transition-all bg-libre-green text-white hover:bg-libre-green/90"
                                    title={$_('common.saveAll')}
                                >
                                    <Save size={18}/>
                                </button>
                                <button
                                    type="button"
                                    on:click={() => dispatch('undoAll')}
                                    class="p-2 rounded-lg transition-all bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600"
                                    title={$_('common.undoAll')}
                                >
                                    <Undo size={18}/>
                                </button>
                            {/if}
                            {#if hasNonDefaults}
                                <button
                                    type="button"
                                    on:click={() => dispatch('resetAll')}
                                    class="p-2 rounded-lg transition-all bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 hover:bg-orange-200 dark:hover:bg-orange-900/50"
                                    title={$_('common.resetAll')}
                                >
                                    <RotateCcw size={18}/>
                                </button>
                            {/if}
                        {/if}
                        {#if showLock}
                            <button
                                type="button"
                                on:click={() => dispatch('toggleLock')}
                                class="p-2 rounded-lg transition-all {isLocked
                                    ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50'
                                    : 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-900/50'}"
                                title={isLocked ? $_('settings.unlock') : $_('settings.lock')}
                            >
                                {#if isLocked}
                                    <Lock size={18}/>
                                {:else}
                                    <Unlock size={18}/>
                                {/if}
                            </button>
                        {/if}
                    </div>
                {/if}
            </div>
            {#if description}
                <p class="text-sm text-gray-500 dark:text-gray-400">{description}</p>
            {/if}
        </div>

        <!-- Content slot -->
        <div class="space-y-4">
            <slot />
        </div>
    </div>
</div>
