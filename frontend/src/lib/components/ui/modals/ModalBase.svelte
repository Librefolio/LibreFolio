<!--
  ModalBase - Base modal component that handles common modal behavior

  Features:
  - Backdrop with click-outside-to-close
  - Escape key handling (with stopPropagation for stacked modals)
  - Fade + scale transitions
  - Focus trapping (backdrop gets focus to capture keyboard events)
  - Configurable z-index for modal stacking
  - Dark mode support
  - Snippet-based content injection (Svelte 5)

  Z-index layers:
    50 = first-level modals (default)
    60 = second-level modals (e.g. FileEditModal over BrokerImportFilesModal)
    70 = third-level modals (e.g. ConfirmModal over FileEditModal)
-->
<script lang="ts">
    import {browser} from '$app/environment';
    import {fade, scale} from 'svelte/transition';
    import type {Snippet} from 'svelte';

    interface Props {
        /** Whether the modal is open */
        open?: boolean;
        /** Z-index level: 50 (default), 60 (stacked), 70 (third-level) */
        zIndex?: number;
        /** Maximum width: 'sm'|'md'|'lg'|'xl'|'2xl'|'3xl'|'4xl'|'5xl'|'none' or a CSS value */
        maxWidth?: string;
        /** Whether clicking the backdrop closes the modal */
        closeOnBackdropClick?: boolean;
        /** Whether pressing Escape closes the modal */
        closeOnEscape?: boolean;
        /** Called when the user requests to close (backdrop click or Escape) */
        onRequestClose?: () => void;
        /** Extra CSS class for the modal-content div */
        contentClass?: string;
        /** data-testid for testing */
        testId?: string;
        /** Disable transitions (useful for nested modals) */
        noTransition?: boolean;
        /** Allow content overflow (for dropdowns inside compact modals) */
        allowOverflow?: boolean;
        /** Content snippet */
        children?: Snippet;
    }

    let {open = false, zIndex = 50, maxWidth = 'lg', closeOnBackdropClick = true, closeOnEscape = true, onRequestClose = () => {}, contentClass = '', testId = '', noTransition = false, allowOverflow = false, children}: Props = $props();

    // Max-width preset map
    const maxWidthMap: Record<string, string> = {
        sm: '24rem',
        md: '28rem',
        lg: '32rem',
        xl: '36rem',
        '2xl': '42rem',
        '3xl': '48rem',
        '4xl': '56rem',
        '5xl': '64rem',
        '6xl': '72rem',
        none: 'none',
        'max-w-sm': '24rem',
        'max-w-md': '28rem',
        'max-w-lg': '32rem',
        'max-w-xl': '36rem',
        'max-w-2xl': '42rem',
        'max-w-3xl': '48rem',
        'max-w-4xl': '56rem',
        'max-w-5xl': '64rem',
        'max-w-6xl': '72rem',
        'max-w-none': 'none',
    };

    let maxWidthValue = $derived(maxWidthMap[maxWidth] || maxWidth);

    // Ref for backdrop focus
    let backdropEl = $state<HTMLDivElement | undefined>(undefined);
    let hasFocusedOnOpen = $state(false);
    let bodyScrollLocked = false;

    // Focus the backdrop ONCE when modal opens so keyboard events are captured
    $effect(() => {
        if (open && backdropEl && !hasFocusedOnOpen) {
            hasFocusedOnOpen = true;
            requestAnimationFrame(() => backdropEl?.focus());
        }
    });

    // Reset when modal closes
    $effect(() => {
        if (!open) {
            hasFocusedOnOpen = false;
        }
    });

    $effect(() => {
        if (!browser) return;

        if (open) {
            lockBodyScroll();
        } else {
            unlockBodyScroll();
        }

        return () => {
            unlockBodyScroll();
        };
    });

    // Track mousedown target to prevent false backdrop clicks during drag
    let mouseDownTarget: EventTarget | null = null;

    function handleBackdropMouseDown(event: MouseEvent) {
        mouseDownTarget = event.target;
    }

    function handleBackdropClick(event: MouseEvent) {
        const clickedOnBackdrop = event.target === event.currentTarget;
        const mouseDownOnBackdrop = mouseDownTarget === event.currentTarget;
        mouseDownTarget = null;

        if (closeOnBackdropClick && clickedOnBackdrop && mouseDownOnBackdrop) {
            onRequestClose();
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (closeOnEscape && event.key === 'Escape') {
            event.stopPropagation();
            onRequestClose();
        }
    }

    function stopPropagation(event: MouseEvent) {
        event.stopPropagation();
    }

    function lockBodyScroll() {
        if (bodyScrollLocked) return;

        const body = document.body;
        const html = document.documentElement;
        const currentCount = Number(body.dataset.modalScrollLockCount || '0');

        if (currentCount === 0) {
            body.dataset.modalPrevOverflow = body.style.overflow;
            html.dataset.modalPrevOverflow = html.style.overflow;
            body.style.overflow = 'hidden';
            html.style.overflow = 'hidden';
        }

        body.dataset.modalScrollLockCount = String(currentCount + 1);
        bodyScrollLocked = true;
    }

    function unlockBodyScroll() {
        if (!bodyScrollLocked) return;

        const body = document.body;
        const html = document.documentElement;
        const currentCount = Math.max(Number(body.dataset.modalScrollLockCount || '1') - 1, 0);

        if (currentCount === 0) {
            body.style.overflow = body.dataset.modalPrevOverflow || '';
            html.style.overflow = html.dataset.modalPrevOverflow || '';
            delete body.dataset.modalScrollLockCount;
            delete body.dataset.modalPrevOverflow;
            delete html.dataset.modalPrevOverflow;
        } else {
            body.dataset.modalScrollLockCount = String(currentCount);
        }

        bodyScrollLocked = false;
    }
</script>

{#if open}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    {#if noTransition}
        <div class="modal-backdrop" style="z-index: {zIndex};" bind:this={backdropEl} tabindex="-1" onmousedown={handleBackdropMouseDown} onclick={handleBackdropClick} onkeydown={handleKeydown} role="dialog" aria-modal="true" data-testid={testId || undefined}>
            <div class="modal-content {contentClass}" style="max-width: {maxWidthValue};{allowOverflow ? ' overflow: visible;' : ''}" onclick={stopPropagation}>
                {#if children}{@render children()}{/if}
            </div>
        </div>
    {:else}
        <div class="modal-backdrop" style="z-index: {zIndex};" bind:this={backdropEl} tabindex="-1" onmousedown={handleBackdropMouseDown} onclick={handleBackdropClick} onkeydown={handleKeydown} role="dialog" aria-modal="true" data-testid={testId || undefined} transition:fade={{duration: 150}}>
            <div class="modal-content {contentClass}" style="max-width: {maxWidthValue};{allowOverflow ? ' overflow: visible;' : ''}" onclick={stopPropagation} transition:scale={{duration: 200, start: 0.95}}>
                {#if children}{@render children()}{/if}
            </div>
        </div>
    {/if}
{/if}

<style>
    .modal-backdrop {
        position: fixed;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: rgba(0, 0, 0, 0.5);
        padding: 1rem;
        outline: none;
    }

    .modal-content {
        background: white;
        border-radius: 0.75rem;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
        width: 100%;
        max-height: 90vh;
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }

    :global(.dark) .modal-content {
        background: #1e293b;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
    }
</style>
