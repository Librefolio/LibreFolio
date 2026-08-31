<script lang="ts">
    /**
     * SettingSelect.svelte - Svelte 5
     * Select dropdown setting with inline actions (like GlobalSettingsTab)
     * Uses SimpleSelect for better mobile support
     */
    import {_} from '$lib/i18n';
    import {type SelectOption, SimpleSelect} from '$lib/components/ui/select';
    import type {Component} from 'svelte';
    import SettingActions from './SettingActions.svelte';

    interface Props {
        value: string;
        options?: SelectOption[];
        label: string;
        hint?: string;
        icon?: Component | null;
        isModified?: boolean;
        isNonDefault?: boolean;
        isLocked?: boolean;
        isSaving?: boolean;
        loading?: boolean;
        onsave?: () => void;
        onundo?: () => void;
        onreset?: () => void;
        onchange?: (value: string) => void;
    }

    let {value = $bindable(''), options = [], label, hint = '', icon = null, isModified = false, isNonDefault = false, isLocked = false, isSaving = false, loading = false, onsave, onundo, onreset, onchange}: Props = $props();

    function handleChange(newValue: string) {
        value = newValue;
        onchange?.(newValue);
    }
</script>

<div class="setting-row flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 py-4 border-b border-gray-100 dark:border-slate-700 last:border-0">
    <!-- Left: Label and hint -->
    <div class="flex-1 min-w-0">
        <div class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-200">
            {#if icon}
                {@const Icon = icon}
                <Icon size={16} class="mr-2 text-gray-500 dark:text-gray-400" />
            {/if}
            {label}
        </div>
        {#if hint}
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{hint}</p>
        {/if}
    </div>

    <!-- Right: Actions + Select - On mobile, full width aligned right -->
    <div class="flex items-center gap-2 sm:space-x-3 self-end sm:self-auto">
        <SettingActions {isModified} {isNonDefault} {isLocked} {isSaving} {onsave} {onundo} {onreset} />

        <!-- SimpleSelect dropdown - responsive width -->
        <div class="w-40 sm:w-48">
            <SimpleSelect bind:value disabled={isLocked} {loading} onchange={handleChange} {options} placeholder={$_('common.select')} />
        </div>
    </div>
</div>
