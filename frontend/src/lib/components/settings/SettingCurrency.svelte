<script lang="ts">
    /**
     * SettingCurrency.svelte
     * Currency setting with FuzzySelect and inline actions
     */
    import { createEventDispatcher } from 'svelte';
    import { _ } from '$lib/i18n';
    import { Save, Undo, RotateCcw } from 'lucide-svelte';
    import FuzzySelect, { type SelectOption } from '$lib/components/FuzzySelect.svelte';
    import type { ComponentType } from 'svelte';

    const dispatch = createEventDispatcher<{
        save: void;
        undo: void;
        reset: void;
        change: string;
    }>();

    // Props
    export let value: string;
    export let options: SelectOption[] = [];
    export let label: string;
    export let hint: string = '';
    export let icon: ComponentType | null = null;
    export let isModified: boolean = false;
    export let isNonDefault: boolean = false;
    export let isLocked: boolean = false;
    export let loading: boolean = false;

    function handleChange(event: CustomEvent<{value: string; option: SelectOption}>) {
        value = event.detail.value;
        dispatch('change', value);
    }
</script>

<div class="setting-row flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 py-4 border-b border-gray-100 dark:border-slate-700 last:border-0">
    <!-- Left: Label and hint -->
    <div class="flex-1 min-w-0">
        <div class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-200">
            {#if icon}
                <svelte:component this={icon} size={16} class="mr-2 text-gray-500 dark:text-gray-400"/>
            {/if}
            {label}
        </div>
        {#if hint}
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{hint}</p>
        {/if}
    </div>

    <!-- Right: Actions + FuzzySelect - On mobile, full width aligned right -->
    <div class="flex items-center gap-2 sm:space-x-3 self-end sm:self-auto">
        <!-- Action buttons -->
        {#if !isLocked}
            <div class="flex items-center space-x-1">
                {#if isModified}
                    <button
                        type="button"
                        on:click={() => dispatch('save')}
                        class="p-1.5 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors"
                        title={$_('common.save')}
                    >
                        <Save size={14}/>
                    </button>
                    <button
                        type="button"
                        on:click={() => dispatch('undo')}
                        class="p-1.5 bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
                        title={$_('common.undo')}
                    >
                        <Undo size={14}/>
                    </button>
                {/if}
                {#if isNonDefault && !isModified}
                    <button
                        type="button"
                        on:click={() => dispatch('reset')}
                        class="p-1.5 bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 rounded-lg hover:bg-orange-200 dark:hover:bg-orange-900/50 transition-colors"
                        title={$_('common.reset')}
                    >
                        <RotateCcw size={14}/>
                    </button>
                {/if}
            </div>
        {/if}

        <!-- FuzzySelect for currency - responsive width -->
        <div class="w-48 sm:w-64">
            <FuzzySelect
                bind:value
                {options}
                placeholder={$_('settings.selectCurrency')}
                {loading}
                disabled={isLocked}
                on:change={handleChange}
            />
        </div>
    </div>
</div>
