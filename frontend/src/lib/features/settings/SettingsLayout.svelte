<script lang="ts">
    import type {ComponentType} from 'svelte';
    /**
     * SettingsLayout.svelte
     * Responsive layout for settings pages
     * - Desktop: 2-column (sidebar + content)
     * - Mobile: custom dropdown + content
     * - Every category button publishes a `data-testid` and its selected state as `aria-pressed`
     * - The menu, sidebar and dropdown, is the shared `SettingsCategoryNav` (project 76, S1a)
     */
    import {_} from '$lib/i18n';
    import {Lock, Unlock} from 'lucide-svelte';
    import SettingBulkActions from './SettingBulkActions.svelte';
    import SettingsCategoryNav from './SettingsCategoryNav.svelte';

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

    // Get selected category label for display
    $: selectedCategoryLabel = selectedCategory === '' ? $_('settings.all') : $_(categories.find((c) => c.id === selectedCategory)?.labelKey || 'settings.all');

    // Get selected category icon
    $: selectedCategoryIcon = selectedCategory === '' ? null : categories.find((c) => c.id === selectedCategory)?.icon || null;

    // «All» (id '', test key `all`) and every category, as the shared menu draws them; the labels follow the language
    $: navEntries = [{id: '', testKey: 'all', label: $_('settings.all')}, ...categories.map((category) => ({id: category.id, icon: category.icon, label: $_(category.labelKey)}))];

    function selectCategory(id: string) {
        selectedCategory = id;
    }
</script>

<SettingsCategoryNav entries={navEntries} mode="phone" onselect={selectCategory} selected={selectedCategory} testIdPrefix="settings" triggerIcon={selectedCategoryIcon} triggerLabel={selectedCategoryLabel} />

<div class="flex flex-col sm:flex-row gap-4 sm:gap-6 min-h-[300px] sm:min-h-[400px] text-lf-primary" data-testid="settings-layout" data-busy={isBusy ? 'true' : 'false'} aria-busy={isBusy}>
    <SettingsCategoryNav entries={navEntries} mode="sidebar" onselect={selectCategory} selected={selectedCategory} testIdPrefix="settings" />

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
