<!--
  SettingToggle.svelte — Svelte 5

  Boolean toggle setting with inline actions (save, undo, reset).
  Follows same API as SettingSelect for consistency.
  Reusable in GlobalSettingsTab and future UserSettingsTab.
-->
<script lang="ts">
    import type {Component} from 'svelte';
    import SettingActions from './SettingActions.svelte';

    interface Props {
        value: boolean;
        label: string;
        hint?: string;
        icon?: Component | null;
        isModified?: boolean;
        isNonDefault?: boolean;
        isLocked?: boolean;
        isSaving?: boolean;
        /** Placeholder mode: control stays visible but read-only regardless of the page lock. */
        disabled?: boolean;
        /** Small badge rendered next to the label (e.g. "Coming soon" for placeholders). */
        badge?: string;
        onsave?: () => void;
        onundo?: () => void;
        onreset?: () => void;
        onchange?: (value: boolean) => void;
    }

    let {value = $bindable(false), label, hint = '', icon = null, isModified = false, isNonDefault = false, isLocked = false, isSaving = false, disabled = false, badge = '', onsave, onundo, onreset, onchange}: Props = $props();

    let effectiveLocked = $derived(isLocked || disabled);

    function toggle() {
        if (effectiveLocked) return;
        value = !value;
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
            {#if badge}
                <span data-testid="setting-badge" class="ml-2 shrink-0 text-[10px] px-1.5 py-0.5 rounded font-medium uppercase tracking-wide bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                    {badge}
                </span>
            {/if}
        </div>
        {#if hint}
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{hint}</p>
        {/if}
    </div>

    <!-- Right: Actions + Toggle -->
    <div class="flex items-center gap-2 sm:space-x-3 self-end sm:self-auto min-h-[32px]">
        <SettingActions {isModified} {isNonDefault} isLocked={effectiveLocked} {isSaving} {onsave} {onundo} {onreset} />

        <!-- Toggle switch -->
        <button
            type="button"
            disabled={effectiveLocked}
            role="switch"
            aria-checked={value}
            aria-label="Toggle {label}"
            data-testid="setting-toggle-switch"
            onclick={toggle}
            class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                {value ? 'bg-libre-green' : 'bg-gray-300 dark:bg-slate-600'}
                {effectiveLocked ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}"
        >
            <span
                class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                    {value ? 'translate-x-6' : 'translate-x-1'}"
            ></span>
        </button>
        <span class="text-sm text-gray-600 dark:text-gray-400 w-10">
            {value ? 'ON' : 'OFF'}
        </span>
    </div>
</div>
