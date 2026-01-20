<script lang="ts">
    /**
     * SettingField.svelte
     * Base component for a single setting field with actions
     */
    import { createEventDispatcher } from 'svelte';
    import { _ } from '$lib/i18n';
    import type { ComponentType } from 'svelte';

    const dispatch = createEventDispatcher<{
        save: void;
        undo: void;
        reset: void;
    }>();

    // Props
    export let label: string;
    export let hint: string = '';
    export let icon: ComponentType | null = null;
    export let isModified: boolean = false;
    export let isLocked: boolean = false;
    export let showActions: boolean = true;
    export let readonly: boolean = false;
</script>

<div class="setting-field" class:locked={isLocked} class:readonly>
    <!-- Label Row -->
    <div class="flex items-start justify-between mb-2">
        <div class="flex items-center gap-2 flex-1">
            {#if icon}
                <svelte:component this={icon} size={18} class="text-gray-500 dark:text-gray-400 flex-shrink-0" />
            {/if}
            <div class="text-sm font-medium text-gray-700 dark:text-gray-200">
                {label}
            </div>
        </div>

        <!-- Actions (only if modified and not readonly) -->
        {#if showActions && isModified && !isLocked && !readonly}
            <div class="flex items-center gap-1">
                <button
                    type="button"
                    on:click={() => dispatch('save')}
                    class="action-btn save"
                    title={$_('common.save')}
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="20 6 9 17 4 12"/>
                    </svg>
                </button>
                <button
                    type="button"
                    on:click={() => dispatch('undo')}
                    class="action-btn undo"
                    title={$_('common.undo')}
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 7v6h6"/>
                        <path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"/>
                    </svg>
                </button>
                <button
                    type="button"
                    on:click={() => dispatch('reset')}
                    class="action-btn reset"
                    title={$_('common.reset')}
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
                        <path d="M3 3v5h5"/>
                    </svg>
                </button>
            </div>
        {/if}
    </div>

    <!-- Hint -->
    {#if hint}
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">{hint}</p>
    {/if}

    <!-- Content Slot -->
    <div class="setting-content">
        <slot />
    </div>
</div>

<style>
    .setting-field {
        padding: 1rem;
        background: #f9fafb;
        border-radius: 0.5rem;
        transition: all 0.2s ease;
    }

    :global(.dark) .setting-field {
        background: #1e293b;
    }

    .setting-field.locked {
        opacity: 0.6;
        pointer-events: none;
    }

    .setting-field.readonly {
        opacity: 0.8;
    }

    .action-btn {
        padding: 0.25rem 0.5rem;
        border-radius: 0.375rem;
        border: 1px solid transparent;
        transition: all 0.15s ease;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .action-btn.save {
        background: #22c55e;
        color: white;
    }

    .action-btn.save:hover {
        background: #16a34a;
    }

    .action-btn.undo {
        background: #f59e0b;
        color: white;
    }

    .action-btn.undo:hover {
        background: #d97706;
    }

    .action-btn.reset {
        background: #ef4444;
        color: white;
    }

    .action-btn.reset:hover {
        background: #dc2626;
    }

    .setting-content {
        position: relative;
    }
</style>
