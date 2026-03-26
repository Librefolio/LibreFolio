<!--
  ModalBase - Base modal component that handles common modal behavior

  Features:
  - Backdrop with click-outside-to-close
  - Escape key handling (with stopPropagation for stacked modals)
  - Fade + scale transitions
  - Focus trapping (backdrop gets focus to capture keyboard events)
  - Configurable z-index for modal stacking
  - Dark mode support
  - Slot-based content injection

  Z-index layers:
    50 = first-level modals (default)
    60 = second-level modals (e.g. FileEditModal over BrokerImportFilesModal)
    70 = third-level modals (e.g. ConfirmModal over FileEditModal)
-->
<script lang="ts">
    import {tick} from 'svelte';
    import {fade, scale} from 'svelte/transition';

    // Props
    /** Whether the modal is open */
    export let open: boolean = false;
    /** Z-index level: 50 (default), 60 (stacked), 70 (third-level) */
    export let zIndex: number = 50;
    /** Maximum width: 'sm'|'md'|'lg'|'xl'|'2xl'|'3xl'|'4xl'|'5xl'|'none' or a CSS value */
    export let maxWidth: string = 'lg';
    /** Whether clicking the backdrop closes the modal */
    export let closeOnBackdropClick: boolean = true;
    /** Whether pressing Escape closes the modal */
    export let closeOnEscape: boolean = true;
    /** Called when the user requests to close (backdrop click or Escape) */
    export let onRequestClose: () => void = () => {
    };
    /** Extra CSS class for the modal-content div */
    export let contentClass: string = '';
    /** data-testid for testing */
    export let testId: string = '';
    /** Disable transitions (useful for nested modals) */
    export let noTransition: boolean = false;
    /** Allow content overflow (for dropdowns inside compact modals) */
    export let allowOverflow: boolean = false;

    // Max-width preset map
    const maxWidthMap: Record<string, string> = {
        'sm': '24rem', 'md': '28rem', 'lg': '32rem', 'xl': '36rem',
        '2xl': '42rem', '3xl': '48rem', '4xl': '56rem', '5xl': '64rem',
        'none': 'none',
        // Support legacy class-name format
        'max-w-sm': '24rem', 'max-w-md': '28rem', 'max-w-lg': '32rem', 'max-w-xl': '36rem',
        'max-w-2xl': '42rem', 'max-w-3xl': '48rem', 'max-w-4xl': '56rem', 'max-w-5xl': '64rem',
        'max-w-none': 'none',
    };

    $: maxWidthValue = maxWidthMap[maxWidth] || maxWidth;

    // Ref for backdrop focus
    let backdropEl: HTMLDivElement;
    let hasFocusedOnOpen = false;

    // Focus the backdrop ONCE when modal opens so keyboard events are captured
    $: if (open && backdropEl && !hasFocusedOnOpen) {
        hasFocusedOnOpen = true;
        tick().then(() => backdropEl?.focus());
    }

    // Reset when modal closes
    $: if (!open) {
        hasFocusedOnOpen = false;
    }

    // Track mousedown target to prevent false backdrop clicks during drag
    let mouseDownTarget: EventTarget | null = null;

    function handleBackdropMouseDown(event: MouseEvent) {
        mouseDownTarget = event.target;
    }

    function handleBackdropClick(event: MouseEvent) {
        // Only close if BOTH mousedown and mouseup/click happened on the backdrop
        // This prevents closing when user drags from inside modal to outside
        const clickedOnBackdrop = event.target === event.currentTarget;
        const mouseDownOnBackdrop = mouseDownTarget === event.currentTarget;
        mouseDownTarget = null;

        if (closeOnBackdropClick && clickedOnBackdrop && mouseDownOnBackdrop) {
            onRequestClose();
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (closeOnEscape && event.key === 'Escape') {
            onRequestClose();
        }
    }
</script>

{#if open}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    {#if noTransition}
        <div
                class="modal-backdrop"
                style="z-index: {zIndex};"
                bind:this={backdropEl}
                tabindex="-1"
                on:mousedown={handleBackdropMouseDown}
                on:click={handleBackdropClick}
                on:keydown|stopPropagation={handleKeydown}
                role="dialog"
                aria-modal="true"
                data-testid={testId || undefined}
        >
            <div
                    class="modal-content {contentClass}"
                    style="max-width: {maxWidthValue};{allowOverflow ? ' overflow: visible;' : ''}"
                    on:click|stopPropagation
            >
                <slot/>
            </div>
        </div>
    {:else}
        <div
                class="modal-backdrop"
                style="z-index: {zIndex};"
                bind:this={backdropEl}
                tabindex="-1"
                on:mousedown={handleBackdropMouseDown}
                on:click={handleBackdropClick}
                on:keydown|stopPropagation={handleKeydown}
                role="dialog"
                aria-modal="true"
                data-testid={testId || undefined}
                transition:fade={{ duration: 150 }}
        >
            <div
                    class="modal-content {contentClass}"
                    style="max-width: {maxWidthValue};{allowOverflow ? ' overflow: visible;' : ''}"
                    on:click|stopPropagation
                    transition:scale={{ duration: 200, start: 0.95 }}
            >
                <slot/>
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
        outline: none; /* Remove focus ring on backdrop */
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
