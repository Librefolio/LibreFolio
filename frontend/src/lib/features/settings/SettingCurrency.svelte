<script lang="ts">
    /**
     * SettingCurrency.svelte - Svelte 5
     * Currency setting with CurrencySearchSelect and inline actions.
     * CurrencySearchSelect handles its own data loading from the API.
     */
    import {_} from '$lib/i18n';
    import {CurrencySearchSelect} from '$lib/components/ui/select';
    import type {Component} from 'svelte';
    import SettingActions from './SettingActions.svelte';

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
        isSaving?: boolean;
        /** @deprecated — CurrencySearchSelect manages its own loading state. */
        loading?: boolean;
        testId?: string;
        /** Render without the standalone row padding/border — for embedding inside a padded card container. */
        embedded?: boolean;
        onsave?: () => void;
        onundo?: () => void;
        onreset?: () => void;
        onchange?: (value: string) => void;
    }

    let {value = $bindable(''), options, label, hint = '', icon = null, isModified = false, isNonDefault = false, isLocked = false, isSaving = false, loading = false, testId = '', embedded = false, onsave, onundo, onreset, onchange}: Props = $props();

    function handleChange(newValue: string) {
        value = newValue;
        onchange?.(newValue);
    }
</script>

<div class="setting-row flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 text-lf-primary {embedded ? '' : 'py-4 border-b border-lf-subtle last:border-0'}" data-testid={testId || undefined}>
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

    <!-- Right: Actions + SearchSelect - On mobile, full width aligned right -->
    <div class="flex items-center gap-2 sm:space-x-3 self-end sm:self-auto">
        <SettingActions {isModified} {isNonDefault} {isLocked} {isSaving} {onsave} {onundo} {onreset} />

        <!-- CurrencySearchSelect — loads its own data from API -->
        <div class="w-48 sm:w-64">
            <CurrencySearchSelect bind:value disabled={isLocked} onchange={handleChange} placeholder={$_('settings.selectCurrency')} />
        </div>
    </div>
</div>
