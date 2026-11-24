<!--
  ContextMenu.svelte — Floating context menu for right-click / long-press actions.

  Positioned at absolute {x, y} pixel coordinates. Auto-adjusts to stay within
  the viewport. Closes on click-outside, Escape, Tab, or action click.

  77 SEL-M (Q-SEL-11, Q-SEL-12): an item that makes sense but is blocked carries its reason (`blocked`). It is
  `aria-disabled`, not natively disabled, so it keeps the focus, the tap and the click that open the reason in the shared
  Tooltip, placed against the whole menu and never over its items; its own click runs nothing and leaves the menu open.
  The keyboard follows the WAI-ARIA menu: the focus goes to the first item when the menu opens, ↑ ↓ Home End move
  through every item (the blocked ones too), Enter and Space run, Escape and Tab close and give the focus back to the
  element that opened the menu. An item is never off without a reason: there is no `disabled` (SEL-M part 2).

  Used by DataTable for row-level context menus. Can also be used standalone.
-->
<script lang="ts">
    import {flushSync, onMount} from 'svelte';
    import type {Component} from 'svelte';
    import {Info} from 'lucide-svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';

    export interface ContextMenuItem {
        type?: 'action' | 'separator';
        id?: string;
        label?: string;
        icon?: Component;
        variant?: 'default' | 'danger';
        /** Why the item is blocked: then it is off, reachable, and says why (77 SEL-M). `hint` is the text the user reads,
         *  `reason` a stable code for tests and logs (as `data-disabled-reason` of the selection bar). */
        blocked?: {hint: string; reason: string};
        title?: string;
        testid?: string;
        iconClass?: string;
        labelClass?: string;
    }

    interface Props {
        x: number;
        y: number;
        items: ContextMenuItem[];
        onAction: (id: string) => void;
        onClose: () => void;
        anchorEl?: HTMLElement | null;
    }

    let {x, y, items, onAction, onClose, anchorEl = null}: Props = $props();

    let menuEl: HTMLDivElement | undefined = $state();
    let measured = $state(false);
    let flipX = $state(false);
    let flipY = $state(false);
    let currentX = $state(0);
    let currentY = $state(0);

    let adjustedX = $derived(flipX ? Math.max(0, currentX - (menuEl?.offsetWidth ?? 0)) : currentX);
    let adjustedY = $derived(flipY ? Math.max(0, currentY - (menuEl?.offsetHeight ?? 0)) : currentY);

    /** The element that had the focus when the menu opened: the ⋮, or what a right-click left focused. */
    let previousFocus: HTMLElement | null = null;
    /** Whether the menu is driven by the keyboard: opened from a keyboard-focused trigger, or moved with a key since. The
     *  reason of a blocked item opens on focus only then: a pointer has its own path (hover, tap, click). */
    let keyboardNav = $state(false);
    const menuId = `context-menu-${Math.random().toString(36).slice(2, 8)}`;

    /** The items the focus can rest on: every action, the blocked ones too. */
    function focusableItems(): HTMLButtonElement[] {
        return menuEl ? [...menuEl.querySelectorAll<HTMLButtonElement>('[role="menuitem"]')] : [];
    }

    function focusItem(index: number): void {
        const items = focusableItems();
        if (items.length === 0) return;
        items[(index + items.length) % items.length].focus();
    }

    function giveFocusBack(): void {
        const target = anchorEl ?? previousFocus;
        if (target?.isConnected) target.focus();
    }

    function handleMenuKeyDown(event: KeyboardEvent): void {
        const items = focusableItems();
        const current = items.indexOf(document.activeElement as HTMLButtonElement);
        const moves: Partial<Record<string, () => number>> = {
            ArrowDown: () => current + 1,
            ArrowUp: () => (current < 0 ? items.length - 1 : current - 1),
            Home: () => 0,
            End: () => items.length - 1,
        };
        const move = moves[event.key];
        // The keys the menu handles are its own: a table, a grid or a modal under it must not act on them too
        if (move || event.key === 'Tab' || event.key === 'Enter' || event.key === ' ') event.stopPropagation();
        if (move) {
            event.preventDefault();
            if (!keyboardNav) {
                // The item's Tooltip must know the keyboard drives before the focus lands on it
                keyboardNav = true;
                flushSync();
            }
            focusItem(move());
            return;
        }
        if (event.key === 'Tab') {
            event.preventDefault();
            giveFocusBack();
            onClose();
        }
    }

    function isFocusVisible(element: Element | null): boolean {
        try {
            return !!element?.matches(':focus-visible');
        } catch {
            return false;
        }
    }

    onMount(() => {
        if (!menuEl) return;
        previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
        keyboardNav = isFocusVisible(previousFocus);
        focusItem(0);
        currentX = x;
        currentY = y;
        let anchorOffsetX = 0;
        let anchorOffsetY = 0;
        let pendingAnchorFrame: number | null = null;

        function updateViewportPlacement(nextX = currentX, nextY = currentY) {
            if (!menuEl) return;
            const rect = menuEl.getBoundingClientRect();
            flipX = nextX + rect.width > window.innerWidth;
            flipY = nextY + rect.height > window.innerHeight;
            measured = true;
        }

        function scheduleAnchorSync() {
            if (!anchorEl || pendingAnchorFrame != null) return;
            pendingAnchorFrame = requestAnimationFrame(() => {
                pendingAnchorFrame = null;
                syncToAnchor();
            });
        }

        function syncToAnchor() {
            if (!anchorEl) {
                updateViewportPlacement();
                return;
            }
            if (!anchorEl.isConnected) {
                onClose();
                return;
            }
            const rect = anchorEl.getBoundingClientRect();
            const fullyOffscreen = rect.bottom <= 0 || rect.top >= window.innerHeight || rect.right <= 0 || rect.left >= window.innerWidth;
            if (rect.width <= 0 || rect.height <= 0 || fullyOffscreen) {
                onClose();
                return;
            }
            const nextX = rect.left + anchorOffsetX;
            const nextY = rect.top + anchorOffsetY;
            currentX = nextX;
            currentY = nextY;
            updateViewportPlacement(nextX, nextY);
        }

        if (anchorEl) {
            const anchorRect = anchorEl.getBoundingClientRect();
            anchorOffsetX = x - anchorRect.left;
            anchorOffsetY = y - anchorRect.top;
            syncToAnchor();
        } else {
            updateViewportPlacement();
        }

        // Close on click outside. The reason of a blocked item lives in the Tooltip, outside the menu: a touch on it is
        // still the menu's.
        function handlePointerDown(e: PointerEvent) {
            const target = e.target as Element | null;
            if (menuEl && !menuEl.contains(target) && !target?.closest?.('[role="tooltip"]')) {
                onClose();
            }
        }
        // Close on Escape. The menu is the top layer: it consumes the key, so a modal under it
        // (ModalBase closes on the same Escape bubbling up) stays open — one Escape, one layer.
        function handleKeyDown(e: KeyboardEvent) {
            if (e.key === 'Escape') {
                e.preventDefault();
                e.stopPropagation();
                giveFocusBack();
                onClose();
            }
        }
        function handleScroll() {
            scheduleAnchorSync();
        }
        function handleResize() {
            if (anchorEl) scheduleAnchorSync();
            else updateViewportPlacement();
        }
        window.addEventListener('pointerdown', handlePointerDown, true);
        window.addEventListener('keydown', handleKeyDown, true);
        if (anchorEl) {
            window.addEventListener('scroll', handleScroll, true);
            window.addEventListener('resize', handleResize);
        }
        return () => {
            window.removeEventListener('pointerdown', handlePointerDown, true);
            window.removeEventListener('keydown', handleKeyDown, true);
            if (anchorEl) {
                window.removeEventListener('scroll', handleScroll, true);
                window.removeEventListener('resize', handleResize);
            }
            if (pendingAnchorFrame != null) {
                cancelAnimationFrame(pendingAnchorFrame);
            }
        };
    });
</script>

<!-- svelte-ignore a11y_interactive_supports_focus -->
<div bind:this={menuEl} role="menu" tabindex="-1" class="context-menu" style="left:{adjustedX}px;top:{adjustedY}px" data-testid="context-menu" onkeydown={handleMenuKeyDown}>
    {#each items as item, index}
        {#if item.type === 'separator'}
            <hr class="context-separator" />
        {:else if item.blocked}
            <!-- Off, with its reason (77 SEL-M): reachable; the click opens the reason (it reaches the Tooltip) and runs
                 nothing. The reason is also in the item's description, for a screen reader. -->
            <Tooltip text={item.blocked.hint} position="right" maxWidth="320px" interactiveChild wrapperClass="w-full" anchor={menuEl} openOnFocus={keyboardNav}>
                <button type="button" role="menuitem" tabindex="-1" class="context-item blocked" aria-disabled="true" aria-describedby="{menuId}-reason-{index}" data-disabled-reason={item.blocked.reason} data-testid={item.testid ?? `context-menu-action-${item.id}`}>
                    {#if item.icon}
                        {@const Icon = item.icon}
                        <Icon size={16} class={item.iconClass ?? ''} />
                    {/if}
                    <span class={item.labelClass ?? ''}>{item.label ?? ''}</span>
                    <Info size={14} class="ml-auto shrink-0" aria-hidden="true" />
                    <span id="{menuId}-reason-{index}" class="sr-only">{item.blocked.hint}</span>
                </button>
            </Tooltip>
        {:else if item.title}
            <Tooltip text={item.title} position="right" maxWidth="320px" interactiveChild wrapperClass="w-full">
                <button
                    type="button"
                    role="menuitem"
                    tabindex="-1"
                    class="context-item {item.variant === 'danger' ? 'danger' : ''}"
                    data-testid={item.testid ?? `context-menu-action-${item.id}`}
                    title={item.title}
                    onclick={(e) => {
                        e.stopPropagation();
                        if (item.id) {
                            // The focus goes back where it was before the action runs: a dialog the action opens takes it from
                            // there, and closing it brings the user back to the ⋮ (WAI-ARIA menu)
                            giveFocusBack();
                            onAction(item.id);
                        }
                    }}
                >
                    {#if item.icon}
                        {@const Icon = item.icon}
                        <Icon size={16} class={item.iconClass ?? ''} />
                    {/if}
                    <span class={item.labelClass ?? ''}>{item.label ?? ''}</span>
                </button>
            </Tooltip>
        {:else}
            <button
                type="button"
                role="menuitem"
                tabindex="-1"
                class="context-item {item.variant === 'danger' ? 'danger' : ''}"
                data-testid={item.testid ?? `context-menu-action-${item.id}`}
                onclick={(e) => {
                    e.stopPropagation();
                    if (item.id) {
                        giveFocusBack();
                        onAction(item.id);
                    }
                }}
            >
                {#if item.icon}
                    {@const Icon = item.icon}
                    <Icon size={16} class={item.iconClass ?? ''} />
                {/if}
                <span class={item.labelClass ?? ''}>{item.label ?? ''}</span>
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
        background: var(--lf-surface-card);
        border: 1px solid var(--lf-border-raised);
        border-radius: 0.5rem;
        box-shadow:
            0 10px 25px -5px var(--lf-shadow-raised),
            0 4px 6px -2px var(--lf-shadow-raised);
        padding: 0.25rem 0;
        overflow: hidden;
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
        color: var(--lf-text-primary);
        cursor: pointer;
        text-align: left;
        transition: background-color 0.1s;
    }
    .context-item:hover {
        background: var(--lf-surface-hover);
    }
    /* Blocked with its reason (77 SEL-M): the label is muted, the ⓘ says there is a reason; no hover of an action. */
    .context-item.blocked {
        color: var(--lf-text-muted);
        cursor: help;
    }
    .context-item.blocked:hover {
        background: none;
    }
    .context-item:focus-visible {
        outline: 2px solid var(--lf-focus);
        outline-offset: -2px;
    }
    .context-item.danger {
        color: var(--lf-danger);
    }
    .context-item.danger:hover {
        background: var(--lf-danger-soft);
    }
    .context-separator {
        margin: 0.25rem 0;
        border: none;
        border-top: 1px solid var(--lf-border-subtle);
    }
</style>
