<!--
  OrderableList — Reusable drag-and-drop orderable list component.

  Features:
  - HTML5 Drag & Drop API on desktop (drag handle + visual feedback)
  - Arrow buttons for mobile (below md breakpoint)
  - Snippet-based item rendering (consumer defines how each item looks)
  - GripVertical drag handle
  - Visual feedback: green left border during drag-over
  - Optional equal-width responsive grid driven by container width
  - Optional warning tone per item
  - Emits reordered items via callback

  Used by: FxProviderSelect, ColumnVisibilityToggle, ChartSignalsSection, ImportWizardModal.
-->
<script generics="T" lang="ts">
    import {ChevronDown, ChevronUp, GripVertical} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import Button from '$lib/components/ui/button/Button.svelte';
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
        /** Use compact padding (py-1 px-2 instead of p-2) for use in tight spaces like dropdowns */
        compact?: boolean;
        /** Switch from a vertical list to an equal-width grid when the container has room */
        responsiveGrid?: boolean;
        /** Minimum grid item width before another column is added */
        minItemWidth?: string;
        /** Optional visual tone for individual items */
        /** 'selected': the item the user has opened, on the focus role (plan 68, E7b3) */
        itemTone?: (item: T, index: number) => 'default' | 'warning' | 'error' | 'selected';
        /** Snippet to render each item's content (between handle and arrows) */
        children: Snippet<[{item: T; index: number}]>;
    }

    let {items = [], keyFn, onReorder, disabled = false, compact = false, responsiveGrid = false, minItemWidth = '32rem', itemTone, children}: Props = $props();

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

<div class={responsiveGrid ? 'grid gap-2' : 'space-y-1'} style={responsiveGrid ? `grid-template-columns: repeat(auto-fill, minmax(min(100%, ${minItemWidth}), 1fr));` : undefined} role="list">
    {#each items as item, index (keyFn(item))}
        {@const tone = itemTone?.(item, index) ?? 'default'}
        <div
            class="flex items-center gap-2 {compact ? 'py-1 px-2' : 'p-2'} rounded-lg border transition-all duration-150
                {dragOverIndex === index && dragIndex !== index
                ? 'border-l-4 border-l-lf-focus border-y-lf-subtle border-r-lf-subtle bg-lf-selected'
                : tone === 'error'
                  ? 'border-lf-danger-line bg-lf-danger-soft'
                  : tone === 'warning'
                    ? 'border-lf-warning-line bg-lf-warning-soft'
                    : tone === 'selected'
                      ? 'border-lf-focus'
                      : 'border-lf-subtle'}
                {dragIndex === index ? 'opacity-50' : ''}
                {disabled ? 'opacity-60' : ''}"
            data-tone={tone}
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
                <div class="hidden md:flex cursor-grab active:cursor-grabbing text-lf-muted hover:text-lf-secondary">
                    <GripVertical size={16} />
                </div>
            {/if}

            <!-- Item content (rendered by parent snippet) -->
            <div class="flex-1 min-w-0">
                {@render children({item, index})}
            </div>

            <!-- Arrow buttons (visible below md) -->
            {#if !disabled}
                <div class="flex flex-col md:hidden gap-0.5">
                    <!-- Stacked neighbours (85 BTN-2a): `dense`, a 24 px target, so the two never cover each other; the name
                         «Move up» / «Move down» in the user's language (D12), reachable even while an arrow is off. -->
                    <Button label={$_('common.moveUp')} icon={ChevronUp} display="icon" variant="ghost" size="xs" dense disabled={index === 0} onclick={() => moveUp(index)} />
                    <Button label={$_('common.moveDown')} icon={ChevronDown} display="icon" variant="ghost" size="xs" dense disabled={index === items.length - 1} onclick={() => moveDown(index)} />
                </div>
            {/if}
        </div>
    {/each}
</div>
