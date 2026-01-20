<script lang="ts">
    /**
     * SettingsLayout.svelte
     * 2-column layout for settings pages (sidebar + content)
     */
    import { createEventDispatcher } from 'svelte';
    import { _ } from '$lib/i18n';
    import type { ComponentType } from 'svelte';

    const dispatch = createEventDispatcher<{
        saveAll: void;
        undoAll: void;
        resetAll: void;
        toggleLock: void;
    }>();

    interface Category {
        id: string;
        icon: ComponentType;
        labelKey: string;
    }

    // Props
    export let categories: Category[] = [];
    export let selectedCategory: string = '';
    export let hasChanges: boolean = false;
    export let hasNonDefaults: boolean = false;
    export let isLocked: boolean = false;
    export let showLock: boolean = false;
    export let title: string = '';
</script>

<div class="settings-layout">
    <!-- Header -->
    <div class="settings-header">
        <h2 class="text-2xl font-semibold text-gray-800 dark:text-gray-100">
            {title}
        </h2>

        <!-- Bulk Actions -->
        <div class="flex items-center gap-2">
            {#if hasChanges}
                <button
                    type="button"
                    on:click={() => dispatch('saveAll')}
                    class="btn btn-primary"
                >
                    {$_('common.saveAll')}
                </button>
                <button
                    type="button"
                    on:click={() => dispatch('undoAll')}
                    class="btn btn-secondary"
                >
                    {$_('common.undoAll')}
                </button>
            {/if}
            {#if hasNonDefaults}
                <button
                    type="button"
                    on:click={() => dispatch('resetAll')}
                    class="btn btn-danger"
                >
                    {$_('common.resetAll')}
                </button>
            {/if}
            {#if showLock}
                <button
                    type="button"
                    on:click={() => dispatch('toggleLock')}
                    class="btn btn-icon"
                    title={isLocked ? $_('settings.unlock') : $_('settings.lock')}
                >
                    {#if isLocked}
                        <!-- Lock icon -->
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                        </svg>
                    {:else}
                        <!-- Unlock icon -->
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                            <path d="M7 11V7a5 5 0 0 1 9.9-1"/>
                        </svg>
                    {/if}
                </button>
            {/if}
        </div>
    </div>

    <!-- Content: 2 columns -->
    <div class="settings-content">
        <!-- Left Sidebar: Categories -->
        {#if categories.length > 0}
            <aside class="settings-sidebar">
                <nav class="space-y-1">
                    <button
                        type="button"
                        on:click={() => selectedCategory = ''}
                        class="category-btn"
                        class:active={selectedCategory === ''}
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="3" width="7" height="7"/>
                            <rect x="14" y="3" width="7" height="7"/>
                            <rect x="14" y="14" width="7" height="7"/>
                            <rect x="3" y="14" width="7" height="7"/>
                        </svg>
                        <span>{$_('settings.all')}</span>
                    </button>

                    {#each categories as category (category.id)}
                        <button
                            type="button"
                            on:click={() => selectedCategory = category.id}
                            class="category-btn"
                            class:active={selectedCategory === category.id}
                        >
                            <svelte:component this={category.icon} size={18} />
                            <span>{$_(category.labelKey)}</span>
                        </button>
                    {/each}
                </nav>
            </aside>
        {/if}

        <!-- Right: Settings Fields -->
        <main class="settings-main">
            <slot />
        </main>
    </div>
</div>

<style>
    .settings-layout {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
        max-width: 1200px;
        margin: 0 auto;
        padding: 1.5rem;
    }

    .settings-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 1rem;
    }

    .settings-content {
        display: grid;
        grid-template-columns: 200px 1fr;
        gap: 2rem;
    }

    @media (max-width: 768px) {
        .settings-content {
            grid-template-columns: 1fr;
        }
    }

    .settings-sidebar {
        position: sticky;
        top: 1rem;
        align-self: start;
    }

    .category-btn {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        width: 100%;
        padding: 0.75rem 1rem;
        border-radius: 0.5rem;
        background: transparent;
        border: none;
        color: #6b7280;
        cursor: pointer;
        transition: all 0.15s ease;
        text-align: left;
    }

    :global(.dark) .category-btn {
        color: #9ca3af;
    }

    .category-btn:hover {
        background: #f3f4f6;
        color: #1a4031;
    }

    :global(.dark) .category-btn:hover {
        background: #334155;
        color: #22c55e;
    }

    .category-btn.active {
        background: #1a4031;
        color: white;
    }

    :global(.dark) .category-btn.active {
        background: #22c55e;
        color: #0f172a;
    }

    .settings-main {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    /* Buttons */
    .btn {
        padding: 0.5rem 1rem;
        border-radius: 0.375rem;
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.15s ease;
        border: 1px solid transparent;
    }

    .btn-primary {
        background: #1a4031;
        color: white;
    }

    .btn-primary:hover {
        background: #173a2c;
    }

    :global(.dark) .btn-primary {
        background: #22c55e;
        color: #0f172a;
    }

    :global(.dark) .btn-primary:hover {
        background: #16a34a;
    }

    .btn-secondary {
        background: #f59e0b;
        color: white;
    }

    .btn-secondary:hover {
        background: #d97706;
    }

    .btn-danger {
        background: #ef4444;
        color: white;
    }

    .btn-danger:hover {
        background: #dc2626;
    }

    .btn-icon {
        background: #f3f4f6;
        padding: 0.5rem;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    :global(.dark) .btn-icon {
        background: #334155;
        color: #f3f4f6;
    }

    .btn-icon:hover {
        background: #e5e7eb;
    }

    :global(.dark) .btn-icon:hover {
        background: #475569;
    }
</style>
