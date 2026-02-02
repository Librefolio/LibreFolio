<script lang="ts">
    /**
     * SettingsLayout.svelte
     * Responsive layout for settings pages
     * - Desktop: 2-column (sidebar + content)
     * - Mobile: dropdown + content
     */
    import { createEventDispatcher } from 'svelte';
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
</script>

<!-- Mobile: Dropdown category selector -->
<div class="sm:hidden mb-4">
    <label for="mobile-category-select" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
        {$_('settings.category')}
    </label>
    <select
        id="mobile-category-select"
        bind:value={selectedCategory}
        class="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700
               text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-libre-green focus:border-libre-green"
    >
        <option value="">{$_('settings.all')}</option>
        {#each categories as category (category.id)}
            <option value={category.id}>{$_(category.labelKey)}</option>
        {/each}
    </select>
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
        <!-- Header with actions -->
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-4 border-b border-gray-200 dark:border-slate-700">
            <div>
                <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
                {#if description}
                    <p class="text-sm text-gray-500 dark:text-gray-400">{description}</p>
                {/if}
            </div>
            <div class="flex items-center space-x-1">
                {#if !isLocked}
                    <!-- Bulk action buttons when unlocked -->
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
        </div>

        <!-- Content slot -->
        <div class="space-y-4">
            <slot />
        </div>
    </div>
</div>
