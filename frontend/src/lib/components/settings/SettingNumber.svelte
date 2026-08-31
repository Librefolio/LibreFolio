<!--
  SettingNumber.svelte — Svelte 5

  Numeric input setting with inline actions (save, undo, reset).
  Supports int/float types, min/max, step, and unit display.
  Follows same API as SettingSelect/SettingToggle for consistency.
  Reusable in GlobalSettingsTab and future UserSettingsTab.
-->
<script lang="ts">
    import {AlertCircle} from 'lucide-svelte';
    import type {Component} from 'svelte';

    import {numericArrows} from '$lib/actions/numericArrows';
    import SettingActions from './SettingActions.svelte';
    interface Props {
        value: string;
        label: string;
        hint?: string;
        icon?: Component | null;
        type?: 'int' | 'float';
        min?: number;
        max?: number;
        step?: number;
        unit?: string;
        /** Warning threshold — show warning if numeric value exceeds this */
        warnAbove?: number;
        warnMessage?: string;
        isModified?: boolean;
        isNonDefault?: boolean;
        isLocked?: boolean;
        isSaving?: boolean;
        onsave?: () => void;
        onundo?: () => void;
        onreset?: () => void;
        onchange?: (value: string) => void;
    }

    let {value = $bindable('0'), label, hint = '', icon = null, type = 'int', min = 0, max, step, unit = '', warnAbove, warnMessage = '', isModified = false, isNonDefault = false, isLocked = false, isSaving = false, onsave, onundo, onreset, onchange}: Props = $props();

    let effectiveStep = $derived(step ?? (type === 'float' ? 0.01 : 1));
    let numericValue = $derived(parseFloat(value) || 0);
    let showWarning = $derived(warnAbove !== undefined && numericValue > warnAbove);

    function handleInput(e: Event) {
        const target = e.target as HTMLInputElement;
        value = target.value;
        onchange?.(value);
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

    <!-- Right: Actions + Input -->
    <div class="flex items-center gap-2 sm:space-x-3 self-end sm:self-auto min-h-[32px]">
        <SettingActions {isModified} {isNonDefault} {isLocked} {isSaving} {onsave} {onundo} {onreset} />

        <!-- Number input with optional unit -->
        <div class="flex flex-col items-end space-y-1">
            <div class="flex items-center space-x-2">
                <input
                    type="number"
                    use:numericArrows
                    step={effectiveStep}
                    {min}
                    {max}
                    {value}
                    oninput={handleInput}
                    disabled={isLocked}
                    class="w-20 px-3 py-2 border rounded-lg text-sm text-right
                        {isLocked
                        ? 'bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-gray-400 cursor-not-allowed border-gray-200 dark:border-slate-600'
                        : 'bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 border-gray-300 dark:border-slate-600 focus:ring-2 focus:ring-libre-green focus:border-libre-green'}"
                />
                {#if unit}
                    <span class="text-sm text-gray-500 dark:text-gray-400">{unit}</span>
                {/if}
            </div>
            <!-- Warning -->
            {#if showWarning && warnMessage}
                <div class="flex items-center text-xs text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20 px-2 py-1 rounded">
                    <AlertCircle size={12} class="mr-1 flex-shrink-0" />
                    <span>{warnMessage}</span>
                </div>
            {/if}
        </div>
    </div>
</div>
