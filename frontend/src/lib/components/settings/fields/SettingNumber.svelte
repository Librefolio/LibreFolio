<!--
  SettingNumber.svelte - Svelte 5

  Numeric input setting with inline actions (save, undo, reset).
  Supports int/float types, min/max, step, and unit display.
  Extracts the number input pattern from GlobalSettingsTab.
-->
<script lang="ts">
    import { _ } from '$lib/i18n';
    import { Save, Undo, RotateCcw, AlertCircle } from 'lucide-svelte';
    import type { Component, Snippet } from 'svelte';

    interface Props {
        /** Current value */
        value: number;
        /** Field label */
        label: string;
        /** Value type (int or float) */
        type?: 'int' | 'float';
        /** Minimum value */
        min?: number;
        /** Maximum value */
        max?: number;
        /** Step increment */
        step?: number;
        /** Unit label (e.g., "hours", "MB") */
        unit?: string;
        /** Optional hint text */
        hint?: string;
        /** Optional icon component */
        icon?: Component | null;
        /** Whether field has been modified */
        isModified?: boolean;
        /** Whether value differs from default */
        isNonDefault?: boolean;
        /** Whether field is locked/read-only */
        isLocked?: boolean;
        /** Saving in progress */
        isSaving?: boolean;
        /** Warning threshold - show warning if value exceeds this */
        warningThreshold?: number;
        /** Warning message snippet */
        warningMessage?: Snippet;
        /** Save callback */
        onsave?: () => void;
        /** Undo callback */
        onundo?: () => void;
        /** Reset to default callback */
        onreset?: () => void;
        /** Change callback */
        onchange?: (value: number) => void;
    }

    let {
        value = $bindable(0),
        label,
        type = 'int',
        min,
        max,
        step,
        unit = '',
        hint = '',
        icon = null,
        isModified = false,
        isNonDefault = false,
        isLocked = false,
        isSaving = false,
        warningThreshold,
        warningMessage,
        onsave,
        onundo,
        onreset,
        onchange
    }: Props = $props();

    // Compute effective step
    let effectiveStep = $derived(step ?? (type === 'float' ? 0.01 : 1));

    // Show warning if value exceeds threshold
    let showWarning = $derived(
        warningThreshold !== undefined && value > warningThreshold
    );

    function handleInput(e: Event) {
        const target = e.target as HTMLInputElement;
        const inputVal = target.value.replace(',', '.');
        const newVal = type === 'float' ? parseFloat(inputVal) : parseInt(inputVal, 10);

        if (!isNaN(newVal)) {
            value = newVal;
            onchange?.(newVal);
        }
    }
</script>

<div class="setting-row flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 py-4 border-b border-gray-100 dark:border-slate-700 last:border-0">
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

    <!-- Right: Actions + Input -->
    <div class="flex items-center gap-2 sm:space-x-3 self-end sm:self-auto">
        <!-- Action buttons (only when unlocked and modified/non-default) -->
        {#if !isLocked}
            <div class="flex items-center space-x-1">
                {#if isModified}
                    <button
                        type="button"
                        onclick={() => onsave?.()}
                        disabled={isSaving}
                        class="p-1.5 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50"
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

        <!-- Number input with unit -->
        <div class="flex flex-col items-end space-y-1">
            <div class="flex items-center space-x-2">
                <input
                    type="number"
                    step={effectiveStep}
                    {min}
                    {max}
                    {value}
                    oninput={handleInput}
                    disabled={isLocked}
                    class="w-20 px-3 py-2 border rounded-lg text-sm text-right
                           {isLocked
                               ? 'bg-gray-100 dark:bg-slate-800 text-gray-500 dark:text-gray-400 cursor-not-allowed border-gray-200 dark:border-slate-700'
                               : 'bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 border-gray-300 dark:border-slate-600 focus:ring-2 focus:ring-libre-green focus:border-libre-green'}"
                />
                {#if unit}
                    <span class="text-sm text-gray-500 dark:text-gray-400">{unit}</span>
                {/if}
            </div>

            <!-- Warning message -->
            {#if showWarning && warningMessage}
                <div class="flex items-center text-xs text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/30 px-2 py-1 rounded">
                    <AlertCircle size={12} class="mr-1"/>
                    {@render warningMessage()}
                </div>
            {/if}
        </div>
    </div>
</div>
