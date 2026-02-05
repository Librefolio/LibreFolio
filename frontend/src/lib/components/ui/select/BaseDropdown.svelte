<!--
  BaseDropdown.svelte - Svelte 5

  Pure dropdown logic component: open/close, click outside, keyboard navigation.
  Used as base for SimpleSelect and SearchSelect.
-->
<script lang="ts">
    import type { Snippet } from 'svelte';

    interface Props {
        /** Disable the dropdown */
        disabled?: boolean;
        /** Position of dropdown (top/bottom/auto) */
        dropdownPosition?: 'top' | 'bottom' | 'auto';
        /** Trigger content */
        trigger: Snippet<[{ isOpen: boolean }]>;
        /** Dropdown content */
        content: Snippet<[{ close: () => void }]>;
        /** Custom class for container */
        class?: string;
    }

    let { disabled = false, dropdownPosition = 'bottom', trigger, content, class: className = '' }: Props = $props();

    // Internal state
    let isOpen = $state(false);
    let containerRef = $state<HTMLDivElement | null>(null);

    // Close on click outside
    $effect(() => {
        if (!isOpen) return;

        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef && !containerRef.contains(event.target as Node)) {
                close();
            }
        };

        // Use mousedown for better UX (catches clicks before focus changes)
        document.addEventListener('mousedown', handleClickOutside, true);
        return () => document.removeEventListener('mousedown', handleClickOutside, true);
    });

    // Close on Escape key
    $effect(() => {
        if (!isOpen) return;

        const handleKeydown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                close();
            }
        };

        document.addEventListener('keydown', handleKeydown);
        return () => document.removeEventListener('keydown', handleKeydown);
    });

    export function open() {
        if (!disabled) {
            isOpen = true;
        }
    }

    export function close() {
        isOpen = false;
    }

    export function toggle() {
        if (isOpen) {
            close();
        } else {
            open();
        }
    }

    function handleTriggerClick() {
        if (!disabled) {
            toggle();
        }
    }

    function handleTriggerKeydown(event: KeyboardEvent) {
        if (disabled) return;

        if (event.key === 'Enter' || event.key === ' ' || event.key === 'ArrowDown') {
            event.preventDefault();
            if (!isOpen) {
                open();
            }
        }
    }
</script>

<div class="relative {className}" bind:this={containerRef}>
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        onclick={handleTriggerClick}
        onkeydown={handleTriggerKeydown}
        role="button"
        tabindex={disabled ? -1 : 0}
        class:cursor-not-allowed={disabled}
        class:opacity-50={disabled}
    >
        {@render trigger({ isOpen })}
    </div>

    {#if isOpen}
        <div
            class="absolute z-50 w-full bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg shadow-lg overflow-hidden
                   {dropdownPosition === 'top' ? 'bottom-full mb-1' : 'top-full mt-1'}"
            role="listbox"
        >
            {@render content({ close })}
        </div>
    {/if}
</div>
