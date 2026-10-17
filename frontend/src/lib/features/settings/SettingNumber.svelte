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

<div class="setting-row flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 text-lf-primary py-4 border-b border-lf-subtle last:border-0">
    <!-- Left: Label and hint -->
    <div class="flex-1 min-w-0">
        <div class="flex items-center text-sm font-medium text-lf-secondary">
            {#if icon}
                {@const Icon = icon}
                <Icon size={16} class="mr-2 text-lf-muted" />
            {/if}
            {label}
        </div>
        {#if hint}
            <p class="text-xs text-lf-muted mt-1">{hint}</p>
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
                        {isLocked ? 'bg-lf-panel text-lf-muted cursor-not-allowed border-lf-subtle' : 'bg-lf-field text-lf-primary border-lf-input hover:border-lf-input-hover focus:ring-2 focus:ring-lf-focus focus:border-lf-focus'}"
                />
                {#if unit}
                    <span class="text-sm text-lf-muted">{unit}</span>
                {/if}
            </div>
            <!-- Warning -->
            {#if showWarning && warnMessage}
                <div class="flex items-center text-xs text-lf-warning-on-soft bg-lf-warning-soft px-2 py-1 rounded">
                    <AlertCircle size={12} class="mr-1 flex-shrink-0" />
                    <span>{warnMessage}</span>
                </div>
            {/if}
        </div>
    </div>
</div>
