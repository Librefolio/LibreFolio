<script lang="ts">
    import type {ComponentType} from 'svelte';
    /**
     * SettingTheme.svelte
     * Theme setting with radio buttons and inline actions
     */
    import {_} from '$lib/i18n';
    import SettingActions from './SettingActions.svelte';

    // Props
    export let value: 'light' | 'dark' | 'auto' = 'auto';
    export let label: string;
    export let hint: string = '';
    export let icon: ComponentType | null = null;
    export let isModified: boolean = false;
    export let isNonDefault: boolean = false;
    export let isLocked: boolean = false;
    export let isSaving: boolean = false;
    /** Render without the standalone row padding/border — for embedding inside a padded card container. */
    export let embedded: boolean = false;
    export let onsave: (() => void) | undefined = undefined;
    export let onundo: (() => void) | undefined = undefined;
    export let onreset: (() => void) | undefined = undefined;
    export let onchange: ((value: 'light' | 'dark' | 'auto') => void) | undefined = undefined;

    const themeOptions: Array<{value: 'light' | 'dark' | 'auto'; labelKey: string}> = [
        {value: 'light', labelKey: 'settings.themeLight'},
        {value: 'dark', labelKey: 'settings.themeDark'},
        {value: 'auto', labelKey: 'settings.themeAuto'},
    ];

    function selectTheme(theme: 'light' | 'dark' | 'auto') {
        if (isLocked) return;
        value = theme;
        onchange?.(value);
    }
</script>

<div class="setting-row flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 text-lf-primary {embedded ? '' : 'py-4 border-b border-lf-subtle last:border-0'}">
    <!-- Left: Label and hint -->
    <div class="flex-1 min-w-0">
        <div class="flex items-center text-sm font-medium text-lf-secondary">
            {#if icon}
                <svelte:component this={icon} size={16} class="mr-2 text-lf-muted" />
            {/if}
            {label}
        </div>
        {#if hint}
            <p class="text-xs text-lf-muted mt-1">{hint}</p>
        {/if}
    </div>

    <!-- Right: Actions + Radio buttons - On mobile, full width aligned right -->
    <div class="flex items-center gap-2 sm:space-x-3 self-end sm:self-auto">
        <SettingActions {isModified} {isNonDefault} {isLocked} {isSaving} {onsave} {onundo} {onreset} />

        <!-- Radio buttons - wrap on mobile if needed -->
        <div class="flex flex-wrap gap-2">
            {#each themeOptions as option}
                <button
                    type="button"
                    data-testid="setting-theme-option-{option.value}"
                    aria-pressed={value === option.value ? 'true' : 'false'}
                    on:click={() => selectTheme(option.value)}
                    disabled={isLocked}
                    class="px-3 sm:px-4 py-2 text-sm border rounded-lg transition-all
                        {value === option.value ? 'border-lf-checked bg-lf-selected text-lf-link' : 'border-lf-input text-lf-secondary hover:border-lf-input-hover'}
                        {isLocked ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}"
                >
                    {$_(option.labelKey)}
                </button>
            {/each}
        </div>
    </div>
</div>
