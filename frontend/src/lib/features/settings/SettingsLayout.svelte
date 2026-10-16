<script lang="ts">
    import type {ComponentType} from 'svelte';
    import {isOutsideClick} from '$lib/utils/core/clickOutside';
    /**
     * SettingsLayout.svelte
     * Responsive layout for settings pages
     * - Desktop: 2-column (sidebar + content)
     * - Mobile: custom dropdown + content
     * - Every category button publishes a `data-testid` and its selected state as `aria-pressed`
     */
    import {onDestroy, onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {ChevronDown, ChevronRight, Lock, Unlock} from 'lucide-svelte';
    import SettingBulkActions from './SettingBulkActions.svelte';

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
    export let isSaving: boolean = false;
    export let onsaveAll: (() => void) | undefined = undefined;
    export let onundoAll: (() => void) | undefined = undefined;
    export let onresetAll: (() => void) | undefined = undefined;
    export let ontoggleLock: (() => void) | undefined = undefined;
    /** Publishes "an async operation is in flight" — a load or a save — on the
     *  layout root as `data-busy`, the attribute `waitForSettled()` reads. Both
     *  a test and a screen reader can then read the state directly instead of
     *  inferring it from a disabled button somewhere else in the tree. */
    export let isBusy: boolean = false;

    // Mobile dropdown state
    let showDropdown = false;
    let dropdownRef: HTMLDivElement | null = null;

    // Get selected category label for display
    $: selectedCategoryLabel = selectedCategory === '' ? $_('settings.all') : $_(categories.find((c) => c.id === selectedCategory)?.labelKey || 'settings.all');

    // Get selected category icon
    $: selectedCategoryIcon = selectedCategory === '' ? null : categories.find((c) => c.id === selectedCategory)?.icon || null;

    function toggleDropdown() {
        showDropdown = !showDropdown;
    }

    function selectCategory(id: string) {
        selectedCategory = id;
        showDropdown = false;
    }

    // Close dropdown on click outside
    function handleClickOutside(event: MouseEvent) {
        if (isOutsideClick(event.target, (el) => !dropdownRef || dropdownRef.contains(el))) {
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
<div bind:this={dropdownRef} class="sm:hidden mb-4 text-lf-primary">
    <span class="block text-sm font-medium text-lf-secondary mb-2">
        {$_('settings.category')}
    </span>
    <div class="relative">
        <button
            class="w-full flex items-center justify-between px-4 py-3 border border-lf-input
                   rounded-lg bg-lf-field text-lf-primary hover:border-lf-input-hover text-sm
                   focus:ring-2 focus:ring-lf-focus focus:border-lf-focus transition-all"
            on:click={toggleDropdown}
            type="button"
            data-testid="settings-mobile-category-trigger"
        >
            <span class="flex items-center gap-2">
                {#if selectedCategoryIcon}
                    <svelte:component this={selectedCategoryIcon} size={16} class="text-lf-muted" />
                {/if}
                {selectedCategoryLabel}
            </span>
            <ChevronDown class="text-lf-muted transition-transform {showDropdown ? 'rotate-180' : ''}" size={18} />
        </button>

        {#if showDropdown}
            <div
                class="absolute top-full left-0 right-0 mt-1 bg-lf-card border border-lf-raised
                        rounded-lg shadow-lg shadow-lf-shadow overflow-hidden z-50"
            >
                <!-- All Settings option -->
                <button
                    type="button"
                    on:click={() => selectCategory('')}
                    data-testid="settings-mobile-category-all"
                    aria-pressed={selectedCategory === '' ? 'true' : 'false'}
                    class="w-full flex items-center gap-3 px-4 py-3 text-sm text-left transition-colors
                           {selectedCategory === '' ? 'bg-lf-selected text-lf-link font-medium' : 'text-lf-secondary hover:bg-lf-hover'}"
                >
                    <span class="flex-1">{$_('settings.all')}</span>
                    {#if selectedCategory === ''}
                        <ChevronRight size={16} />
                    {/if}
                </button>

                <!-- Category options -->
                {#each categories as category (category.id)}
                    <button
                        type="button"
                        on:click={() => selectCategory(category.id)}
                        data-testid="settings-mobile-category-{category.id}"
                        aria-pressed={selectedCategory === category.id ? 'true' : 'false'}
                        class="w-full flex items-center gap-3 px-4 py-3 text-sm text-left transition-colors
                               {selectedCategory === category.id ? 'bg-lf-selected text-lf-link font-medium' : 'text-lf-secondary hover:bg-lf-hover'}"
                    >
                        <svelte:component this={category.icon} size={16} class={selectedCategory === category.id ? 'text-lf-link' : 'text-lf-muted'} />
                        <span class="flex-1">{$_(category.labelKey)}</span>
                        {#if selectedCategory === category.id}
                            <ChevronRight size={16} />
                        {/if}
                    </button>
                {/each}
            </div>
        {/if}
    </div>
</div>

<div class="flex flex-col sm:flex-row gap-4 sm:gap-6 min-h-[300px] sm:min-h-[400px] text-lf-primary" data-testid="settings-layout" data-busy={isBusy ? 'true' : 'false'} aria-busy={isBusy}>
    <!-- Desktop: Left sidebar category navigation (hidden on mobile) -->
    <div class="hidden sm:block w-48 flex-shrink-0">
        <nav class="space-y-1">
            <!-- All categories button -->
            <button
                class="w-full flex items-center px-3 py-2 text-sm rounded-lg transition-colors
                    {selectedCategory === '' ? 'bg-lf-checked text-lf-on-checked' : 'text-lf-secondary hover:bg-lf-hover'}"
                on:click={() => (selectedCategory = '')}
                type="button"
                data-testid="settings-category-all"
                aria-pressed={selectedCategory === '' ? 'true' : 'false'}
            >
                <span class="flex-1 text-left">{$_('settings.all')}</span>
                {#if selectedCategory === ''}
                    <ChevronRight size={16} />
                {/if}
            </button>

            {#each categories as category (category.id)}
                <button
                    type="button"
                    on:click={() => (selectedCategory = category.id)}
                    data-testid="settings-category-{category.id}"
                    aria-pressed={selectedCategory === category.id ? 'true' : 'false'}
                    class="w-full flex items-center px-3 py-2 text-sm rounded-lg transition-colors
                        {selectedCategory === category.id ? 'bg-lf-checked text-lf-on-checked' : 'text-lf-secondary hover:bg-lf-hover'}"
                >
                    <svelte:component this={category.icon} size={16} class="mr-2" />
                    <span class="flex-1 text-left">{$_(category.labelKey)}</span>
                    {#if selectedCategory === category.id}
                        <ChevronRight size={16} />
                    {/if}
                </button>
            {/each}
        </nav>
    </div>

    <!-- Right side: Settings content -->
    <div class="flex-1 space-y-4">
        <!-- Header with actions - Title and icons on same row, description below -->
        <div class="pb-4 border-b border-lf-subtle">
            <div class="flex items-center justify-between gap-2 mb-1 min-h-[36px]">
                <h3 class="text-lg font-semibold text-lf-primary">{title}</h3>

                <!-- Action buttons - inline with title -->
                {#if showLock || hasChanges || hasNonDefaults}
                    <div class="flex items-center gap-1 flex-shrink-0">
                        <SettingBulkActions {hasChanges} {hasNonDefaults} {isLocked} {isSaving} {onsaveAll} {onundoAll} {onresetAll} />
                        {#if showLock}
                            <button
                                type="button"
                                on:click={() => ontoggleLock?.()}
                                class="p-2 rounded-lg transition-all {isLocked ? 'bg-lf-danger-soft text-lf-danger hover:bg-lf-danger-line' : 'bg-lf-success-soft text-lf-success hover:bg-lf-success-line'}"
                                title={isLocked ? $_('settings.unlock') : $_('settings.lock')}
                            >
                                {#if isLocked}
                                    <Lock size={18} />
                                {:else}
                                    <Unlock size={18} />
                                {/if}
                            </button>
                        {/if}
                    </div>
                {/if}
            </div>
            {#if description}
                <p class="text-sm text-lf-muted">{description}</p>
            {/if}
        </div>

        <!-- Content slot -->
        <div class="space-y-4">
            <slot />
        </div>
    </div>
</div>
