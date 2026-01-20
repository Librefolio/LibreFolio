<script lang="ts">
    /**
     * Tooltip - Instant tooltip with click-outside dismiss
     *
     * Features:
     * - 0ms delay on hover
     * - Also opens on click (for mobile)
     * - Auto-positions to avoid viewport overflow
     * - Closes on click outside
     */
    import { onMount, onDestroy } from 'svelte';

    export let text: string;
    export let position: 'top' | 'bottom' | 'left' | 'right' = 'top';
    export let maxWidth: string = '400px';

    let visible = false;
    let tooltipElement: HTMLDivElement;
    let triggerElement: HTMLDivElement;
    let actualPosition = position;

    function show() {
        visible = true;
        // Defer position calculation to next frame
        requestAnimationFrame(calculatePosition);
    }

    function hide() {
        visible = false;
    }

    function toggle(event: MouseEvent) {
        event.stopPropagation();
        if (visible) {
            hide();
        } else {
            show();
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            if (visible) {
                hide();
            } else {
                show();
            }
        }
    }

    function handleClickOutside(event: MouseEvent) {
        if (visible && triggerElement && !triggerElement.contains(event.target as Node)) {
            hide();
        }
    }

    function calculatePosition() {
        if (!tooltipElement || !triggerElement) return;

        const tooltipRect = tooltipElement.getBoundingClientRect();
        const triggerRect = triggerElement.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const padding = 10;

        // Start with preferred position
        actualPosition = position;

        // Check if tooltip fits
        switch (position) {
            case 'top':
                if (triggerRect.top - tooltipRect.height < padding) {
                    actualPosition = 'bottom';
                }
                break;
            case 'bottom':
                if (triggerRect.bottom + tooltipRect.height > viewportHeight - padding) {
                    actualPosition = 'top';
                }
                break;
            case 'left':
                if (triggerRect.left - tooltipRect.width < padding) {
                    actualPosition = 'right';
                }
                break;
            case 'right':
                if (triggerRect.right + tooltipRect.width > viewportWidth - padding) {
                    actualPosition = 'left';
                }
                break;
        }
    }

    onMount(() => {
        document.addEventListener('click', handleClickOutside);
    });

    onDestroy(() => {
        document.removeEventListener('click', handleClickOutside);
    });
</script>

<div
    class="tooltip-wrapper"
    bind:this={triggerElement}
    on:mouseenter={show}
    on:mouseleave={hide}
    on:click={toggle}
    on:keydown={handleKeydown}
    role="button"
    tabindex="0"
>
    <slot />

    {#if visible}
        <div
            bind:this={tooltipElement}
            class="tooltip tooltip-{actualPosition}"
            style="max-width: {maxWidth};"
            role="tooltip"
        >
            {text}
            <div class="tooltip-arrow"></div>
        </div>
    {/if}
</div>

<style>
    .tooltip-wrapper {
        position: relative;
        display: inline-flex;
        cursor: help;
    }

    .tooltip {
        position: absolute;
        z-index: 50;
        padding: 0.5rem 0.75rem;
        font-size: 0.875rem;
        line-height: 1.25rem;
        color: white;
        background-color: #1f2937;
        border-radius: 0.375rem;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        white-space: normal;
        word-wrap: break-word;
        pointer-events: none;
        min-width: 180px;
        width: max-content;
    }

    /* Dark mode tooltip */
    :global(html.dark) .tooltip {
        background-color: #61666f;
    }

    .tooltip-arrow {
        position: absolute;
        width: 8px;
        height: 8px;
        background-color: #1f2937;
        transform: rotate(45deg);
    }

    /* Dark mode arrow */
    :global(html.dark) .tooltip-arrow {
        background-color: #61666f;
    }

    /* Position: Top */
    .tooltip-top {
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        margin-bottom: 8px;
    }

    .tooltip-top .tooltip-arrow {
        bottom: -4px;
        left: 50%;
        transform: translateX(-50%) rotate(45deg);
    }

    /* Position: Bottom */
    .tooltip-bottom {
        top: 100%;
        left: 50%;
        transform: translateX(-50%);
        margin-top: 8px;
    }

    .tooltip-bottom .tooltip-arrow {
        top: -4px;
        left: 50%;
        transform: translateX(-50%) rotate(45deg);
    }

    /* Position: Left */
    .tooltip-left {
        right: 100%;
        top: 50%;
        transform: translateY(-50%);
        margin-right: 8px;
    }

    .tooltip-left .tooltip-arrow {
        right: -4px;
        top: 50%;
        transform: translateY(-50%) rotate(45deg);
    }

    /* Position: Right */
    .tooltip-right {
        left: 100%;
        top: 50%;
        transform: translateY(-50%);
        margin-left: 8px;
    }

    .tooltip-right .tooltip-arrow {
        left: -4px;
        top: 50%;
        transform: translateY(-50%) rotate(45deg);
    }
</style>

