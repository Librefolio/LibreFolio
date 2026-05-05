<!--
  ContextMenu.svelte — Floating context menu for right-click / long-press actions.

  Positioned at absolute {x, y} pixel coordinates. Auto-adjusts to stay within
  the viewport. Closes on click-outside, Escape, or action click.

  Used by DataTable for row-level context menus. Can also be used standalone.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import type {Component} from 'svelte';

    export interface ContextMenuItem {
        type?: 'action' | 'separator';
        id?: string;
        label?: string;
        icon?: Component;
        variant?: 'default' | 'danger';
        disabled?: boolean;
    }

    interface Props {
        x: number;
        y: number;
        items: ContextMenuItem[];
        onAction: (id: string) => void;
        onClose: () => void;
    }

    let {x, y, items, onAction, onClose}: Props = $props();

    let menuEl: HTMLDivElement | undefined = $state();
    let measured = $state(false);
    let flipX = $state(false);
    let flipY = $state(false);

    let adjustedX = $derived(flipX ? Math.max(0, x - (menuEl?.offsetWidth ?? 0)) : x);
    let adjustedY = $derived(flipY ? Math.max(0, y - (menuEl?.offsetHeight ?? 0)) : y);

    onMount(() => {
        if (!menuEl) return;
        const rect = menuEl.getBoundingClientRect();
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        flipX = x + rect.width > vw;
        flipY = y + rect.height > vh;
        measured = true;

        // Close on click outside
        function handlePointerDown(e: PointerEvent) {
            if (menuEl && !menuEl.contains(e.target as Node)) {
                onClose();
            }
        }
        // Close on Escape
        function handleKeyDown(e: KeyboardEvent) {
            if (e.key === 'Escape') {
                e.preventDefault();
                onClose();
            }
        }
        window.addEventListener('pointerdown', handlePointerDown, true);
        window.addEventListener('keydown', handleKeyDown, true);
        return () => {
            window.removeEventListener('pointerdown', handlePointerDown, true);
            window.removeEventListener('keydown', handleKeyDown, true);
        };
    });
</script>

<div
    bind:this={menuEl}
    role="menu"
    class="context-menu"
    style="left:{adjustedX}px;top:{adjustedY}px"
    data-testid="context-menu"
>
    {#each items as item}
        {#if item.type === 'separator'}
            <hr class="context-separator" />
        {:else}
            <button
                type="button"
                role="menuitem"
                class="context-item {item.variant === 'danger' ? 'danger' : ''}"
                disabled={item.disabled}
                data-testid="context-menu-action-{item.id}"
                onclick={(e) => {
                    e.stopPropagation();
                    if (!item.disabled && item.id) {
                        onAction(item.id);
                    }
                }}
            >
                {#if item.icon}
                    {@const Icon = item.icon}
                    <Icon size={16} />
                {/if}
                <span>{item.label ?? ''}</span>
            </button>
        {/if}
    {/each}
</div>

<style>
    .context-menu {
        position: fixed;
        z-index: 9999;
        min-width: 180px;
        max-width: 280px;
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
        box-shadow: 0 10px 25px -5px rgb(0 0 0 / 0.1), 0 4px 6px -2px rgb(0 0 0 / 0.05);
        padding: 0.25rem 0;
        overflow: hidden;
    }
    :global(.dark) .context-menu {
        background: #1e293b;
        border-color: #334155;
        box-shadow: 0 10px 25px -5px rgb(0 0 0 / 0.4), 0 4px 6px -2px rgb(0 0 0 / 0.2);
    }
    .context-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        width: 100%;
        padding: 0.5rem 0.75rem;
        border: none;
        background: none;
        font-size: 0.8125rem;
        color: #334155;
        cursor: pointer;
        text-align: left;
        transition: background-color 0.1s;
    }
    :global(.dark) .context-item {
        color: #e2e8f0;
    }
    .context-item:hover:not(:disabled) {
        background: #f1f5f9;
    }
    :global(.dark) .context-item:hover:not(:disabled) {
        background: #334155;
    }
    .context-item:disabled {
        opacity: 0.4;
        cursor: default;
    }
    .context-item.danger {
        color: #dc2626;
    }
    :global(.dark) .context-item.danger {
        color: #f87171;
    }
    .context-item.danger:hover:not(:disabled) {
        background: #fef2f2;
    }
    :global(.dark) .context-item.danger:hover:not(:disabled) {
        background: #450a0a;
    }
    .context-separator {
        margin: 0.25rem 0;
        border: none;
        border-top: 1px solid #e2e8f0;
    }
    :global(.dark) .context-separator {
        border-top-color: #334155;
    }
</style>

