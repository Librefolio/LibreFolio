<!--
  SettingToggle.svelte — Svelte 5

  Boolean toggle setting with inline actions (save, undo, reset).
  Follows same API as SettingSelect for consistency.
  Reusable in GlobalSettingsTab and future UserSettingsTab.
-->
<script lang="ts">
    import type {Component} from 'svelte';
    import SettingActions from './SettingActions.svelte';
    import Switch from '$lib/components/ui/input/Switch.svelte';

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

<div class="setting-row flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 py-4 border-b border-lf-subtle text-lf-primary last:border-0">
    <!-- Left: Label and hint -->
    <div class="flex-1 min-w-0">
        <div class="flex items-center text-sm font-medium text-lf-secondary">
            {#if icon}
                {@const Icon = icon}
                <Icon size={16} class="mr-2 text-lf-muted" />
            {/if}
            {label}
            {#if badge}
                <span data-testid="setting-badge" class="ml-2 shrink-0 text-[10px] px-1.5 py-0.5 rounded font-medium uppercase tracking-wide bg-lf-warning-soft text-lf-warning-on-soft">
                    {badge}
                </span>
            {/if}
        </div>
        {#if hint}
            <p class="text-xs text-lf-muted mt-1">{hint}</p>
        {/if}
    </div>

    <!-- Right: Actions + Toggle -->
    <div class="flex items-center gap-2 sm:space-x-3 self-end sm:self-auto min-h-[32px]">
        <SettingActions {isModified} {isNonDefault} isLocked={effectiveLocked} {isSaving} {onsave} {onundo} {onreset} />

        <!-- Toggle switch -->
        <Switch checked={value} disabled={effectiveLocked} label="Toggle {label}" testId="setting-toggle-switch" onchange={toggle} />
        <span class="text-sm text-lf-secondary w-10">
            {value ? 'ON' : 'OFF'}
        </span>
    </div>
</div>
