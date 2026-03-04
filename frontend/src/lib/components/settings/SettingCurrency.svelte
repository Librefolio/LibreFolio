<script lang="ts">
    /**
     * SettingCurrency.svelte - Svelte 5
     * Currency setting with CurrencySearchSelect and inline actions.
     * CurrencySearchSelect handles its own data loading from the API.
     */
    import {_} from '$lib/i18n';
    import {RotateCcw, Save, Undo} from 'lucide-svelte';
    import {CurrencySearchSelect} from '$lib/components/ui/select';
    import type {Component} from 'svelte';

    interface Props {
        value: string;
        /** @deprecated — CurrencySearchSelect loads its own options. Kept for backward compat. */
        options?: any[];
        label: string;
        hint?: string;
        icon?: Component | null;
        isModified?: boolean;
        isNonDefault?: boolean;
        isLocked?: boolean;
        /** @deprecated — CurrencySearchSelect manages its own loading state. */
        loading?: boolean;
        testId?: string;
        onsave?: () => void;
        onundo?: () => void;
        onreset?: () => void;
        onchange?: (value: string) => void;
    }

    let {
        value = $bindable(''),
        options,
        label,
        hint = '',
        icon = null,
        isModified = false,
        isNonDefault = false,
        isLocked = false,
        loading = false,
        testId = '',
        onsave,
        onundo,
        onreset,
        onchange
    }: Props = $props();

    function handleChange(newValue: string) {
        value = newValue;
        onchange?.(newValue);
    }
</script>

<div
        class="setting-row flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 py-4 border-b border-gray-100 dark:border-slate-700 last:border-0"
        data-testid={testId || undefined}
>
    <!-- Left: Label and hint -->
    <div class="flex-1 min-w-0">
        <div class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-200">
            {#if icon}
                {@const Icon = icon}
                <Icon size={16} class="mr-2 text-gray-500 dark:text-gray-400"/>
            {/if}
            {label}
        </div>
        {#if hint}
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{hint}</p>
        {/if}
    </div>

    <!-- Right: Actions + SearchSelect - On mobile, full width aligned right -->
    <div class="flex items-center gap-2 sm:space-x-3 self-end sm:self-auto">
        <!-- Action buttons -->
        {#if !isLocked}
            <div class="flex items-center space-x-1">
                {#if isModified}
                    <button
                            type="button"
                            onclick={() => onsave?.()}
                            class="p-1.5 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors"
                            title={$_('common.save')}
                    >
                        <Save size={14}/>
                    </button>
                    <button
                            type="button"
                            onclick={() => onundo?.()}
                            class="p-1.5 bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
                            title={$_('common.undo')}
                    >
                        <Undo size={14}/>
                    </button>
                {/if}
                {#if isNonDefault && !isModified}
                    <button
                            type="button"
                            onclick={() => onreset?.()}
                            class="p-1.5 bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 rounded-lg hover:bg-orange-200 dark:hover:bg-orange-900/50 transition-colors"
                            title={$_('common.reset')}
                    >
                        <RotateCcw size={14}/>
                    </button>
                {/if}
            </div>
        {/if}

        <!-- CurrencySearchSelect — loads its own data from API -->
        <div class="w-48 sm:w-64">
            <CurrencySearchSelect
                    bind:value
                    disabled={isLocked}
                    onchange={handleChange}
                    placeholder={$_('settings.selectCurrency')}
                    compact={true}
            />
        </div>
    </div>
</div>
