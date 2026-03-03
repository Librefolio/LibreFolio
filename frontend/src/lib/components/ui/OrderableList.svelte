<!--
  OrderableList — Reusable drag-and-drop orderable list component.

  Features:
  - HTML5 Drag & Drop API on desktop (drag handle + visual feedback)
  - Arrow buttons for mobile (below md breakpoint)
  - Snippet-based item rendering (consumer defines how each item looks)
  - GripVertical drag handle
  - Visual feedback: green left border during drag-over
  - Emits reordered items via callback

  Used by: FxProviderConfig, DataTableToolbar (future), etc.
-->
<script lang="ts" generics="T">
    import {GripVertical, ChevronUp, ChevronDown} from 'lucide-svelte';
    import type {Snippet} from 'svelte';

    // =========================================================================
    // Types
    // =========================================================================

    interface Props {
        /** Items to display in orderable list */
        items: T[];
        /** Function to extract unique key from item */
        keyFn: (item: T) => string;
        /** Called when items are reordered */
        onReorder: (newItems: T[]) => void;
        /** Disable reordering */
        disabled?: boolean;
        /** Snippet to render each item's content (between handle and arrows) */
        children: Snippet<[{ item: T; index: number }]>;
    }

    let {
        items = [],
        keyFn,
        onReorder,
        disabled = false,
        children,
    }: Props = $props();

    // =========================================================================
    // Drag & Drop State
    // =========================================================================

    let dragIndex: number | null = $state(null);
    let dragOverIndex: number | null = $state(null);

    // =========================================================================
    // Drag & Drop Handlers (Desktop)
    // =========================================================================

    function handleDragStart(index: number) {
        if (disabled) return;
        dragIndex = index;
    }

    function handleDragOver(e: DragEvent, index: number) {
        if (disabled || dragIndex === null) return;
        e.preventDefault();
        dragOverIndex = index;
    }

    function handleDragLeave() {
        dragOverIndex = null;
    }

    function handleDrop(index: number) {
        if (disabled || dragIndex === null || dragIndex === index) {
            dragIndex = null;
            dragOverIndex = null;
            return;
        }

        const newItems = [...items];
        const [removed] = newItems.splice(dragIndex, 1);
        newItems.splice(index, 0, removed);
        onReorder(newItems);

        dragIndex = null;
        dragOverIndex = null;
    }

    function handleDragEnd() {
        dragIndex = null;
        dragOverIndex = null;
    }

    // =========================================================================
    // Arrow Handlers (Mobile)
    // =========================================================================

    function moveUp(index: number) {
        if (disabled || index <= 0) return;
        const newItems = [...items];
        [newItems[index - 1], newItems[index]] = [newItems[index], newItems[index - 1]];
        onReorder(newItems);
    }

    function moveDown(index: number) {
        if (disabled || index >= items.length - 1) return;
        const newItems = [...items];
        [newItems[index], newItems[index + 1]] = [newItems[index + 1], newItems[index]];
        onReorder(newItems);
    }
</script>

<div class="space-y-1">
    {#each items as item, index (keyFn(item))}
        <div
            class="flex items-center gap-2 p-2 rounded-lg border transition-all duration-150
                {dragOverIndex === index && dragIndex !== index
                    ? 'border-l-4 border-l-libre-green border-y-gray-200 dark:border-y-slate-600 border-r-gray-200 dark:border-r-slate-600 bg-green-50/50 dark:bg-green-900/10'
                    : 'border-gray-200 dark:border-slate-600'}
                {dragIndex === index ? 'opacity-50' : ''}
                {disabled ? 'opacity-60' : ''}"
            draggable={!disabled}
            ondragstart={() => handleDragStart(index)}
            ondragover={(e: DragEvent) => handleDragOver(e, index)}
            ondragleave={handleDragLeave}
            ondrop={() => handleDrop(index)}
            ondragend={handleDragEnd}
            role="listitem"
        >
            <!-- Drag handle (visible on md+) -->
            {#if !disabled}
                <div class="hidden md:flex cursor-grab active:cursor-grabbing text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">
                    <GripVertical size={16} />
                </div>
            {/if}

            <!-- Item content (rendered by parent snippet) -->
            <div class="flex-1 min-w-0">
                {@render children({ item, index })}
            </div>

            <!-- Arrow buttons (visible below md) -->
            {#if !disabled}
                <div class="flex flex-col md:hidden gap-0.5">
                    <button
                        type="button"
                        class="p-0.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed"
                        disabled={index === 0}
                        onclick={() => moveUp(index)}
                        title="Move up"
                    >
                        <ChevronUp size={14} />
                    </button>
                    <button
                        type="button"
                        class="p-0.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed"
                        disabled={index === items.length - 1}
                        onclick={() => moveDown(index)}
                        title="Move down"
                    >
                        <ChevronDown size={14} />
                    </button>
                </div>
            {/if}
        </div>
    {/each}
</div>

