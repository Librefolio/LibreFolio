<!--
  SettingToggle.svelte - Svelte 5

  Boolean toggle setting with inline actions (save, undo, reset).
  Extracts the toggle pattern from GlobalSettingsTab for reuse.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {RotateCcw, Save, Undo} from 'lucide-svelte';
    import type {Component} from 'svelte';

    interface Props {
        /** Current value as boolean */
        value: boolean;
        /** Field label */
        label: string;
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
        /** Save callback */
        onsave?: () => void;
        /** Undo callback */
        onundo?: () => void;
        /** Reset to default callback */
        onreset?: () => void;
        /** Change callback */
        onchange?: (value: boolean) => void;
    }

    let {
        value = $bindable(false),
        label,
        hint = '',
        icon = null,
        isModified = false,
        isNonDefault = false,
        isLocked = false,
        isSaving = false,
        onsave,
        onundo,
        onreset,
        onchange
    }: Props = $props();

    function toggle() {
        if (isLocked) return;
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
                <Icon size={16} class="mr-2 text-gray-500 dark:text-gray-400"/>
            {/if}
            {label}
        </div>
        {#if hint}
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{hint}</p>
        {/if}
    </div>

    <!-- Right: Actions + Toggle -->
    <div class="flex items-center gap-2 sm:space-x-3 self-end sm:self-auto min-h-[32px]">
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

        <!-- Toggle Switch -->
        <button
                aria-label="Toggle {label}"
                class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                   {value ? 'bg-libre-green' : 'bg-gray-300 dark:bg-slate-600'}
                   {isLocked ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}"
                disabled={isLocked}
                onclick={toggle}
                type="button"
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
