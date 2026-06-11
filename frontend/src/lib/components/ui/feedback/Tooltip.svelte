<script lang="ts">
    /**
     * Tooltip - Instant tooltip with click-outside dismiss
     *
     * Features:
     * - 0ms delay on hover
     * - Also opens on click (for mobile)
     * - Fixed positioning: renders relative to viewport, never clipped by modal/overflow
     * - Auto-positions to avoid viewport overflow
     * - Closes on click outside
     * - Supports plain text, raw HTML, and inline LaTeX ($...$) via KaTeX
     *
     * Svelte 5 runes.
     */
    import type {Snippet} from 'svelte';
    import katex from 'katex';
    import 'katex/dist/katex.min.css';

    interface Props {
        text?: string;
        /** If provided, renders raw HTML instead of plain text */
        html?: string;
        /** When true, processes $...$ inline LaTeX in text/html content via KaTeX */
        math?: boolean;
        position?: 'top' | 'bottom' | 'left' | 'right';
        maxWidth?: string;
        children?: Snippet;
    }

    let {text = '', html = '', math = false, position = 'top', maxWidth = '400px', children}: Props = $props();

    let visible = $state(false);
    let tooltipElement = $state<HTMLDivElement | undefined>(undefined);
    let triggerElement = $state<HTMLDivElement | undefined>(undefined);

    // Fixed position coordinates (viewport-relative)
    let fixedTop = $state(0);
    let fixedLeft = $state(0);

    /** Auto-dismiss timer for mobile (touch) interactions */
    let autoDismissTimer = $state<ReturnType<typeof setTimeout> | null>(null);
    /** Whether the current interaction is touch-based */
    let isTouchInteraction = $state(false);

    function clearAutoDismiss() {
        if (autoDismissTimer) {
            clearTimeout(autoDismissTimer);
            autoDismissTimer = null;
        }
    }

    function startAutoDismiss() {
        clearAutoDismiss();
        autoDismissTimer = setTimeout(() => {
            hide();
        }, 5000);
    }

    function show() {
        visible = true;
        // Defer position calculation to next frame (tooltip must be in DOM first)
        requestAnimationFrame(calculateFixedPosition);
    }

    function hide() {
        visible = false;
        clearAutoDismiss();
        isTouchInteraction = false;
    }

    function toggle(event: MouseEvent) {
        event.stopPropagation();
        if (visible) {
            hide();
        } else {
            show();
        }
    }

    function handleTouchStart(event: TouchEvent) {
        event.stopPropagation();
        isTouchInteraction = true;
        if (visible) {
            hide();
        } else {
            show();
            startAutoDismiss();
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
        if (visible && triggerElement && !triggerElement.contains(event.target as Node) && !tooltipElement?.contains(event.target as Node)) {
            hide();
        }
    }

    /**
     * Portal: move .tooltip-fixed to document.body to escape parent stacking
     * contexts (opacity, z-index, overflow). This prevents parent row opacity
     * from bleeding into the tooltip and ensures z-index is always highest.
     */
    $effect(() => {
        if (tooltipElement) {
            document.body.appendChild(tooltipElement);
            return () => {
                if (tooltipElement?.parentNode === document.body) {
                    tooltipElement.remove();
                }
            };
        }
    });

    /**
     * Calculate tooltip position in fixed (viewport) coordinates.
     * This avoids clipping by parent overflow:hidden/auto (e.g. modals).
     */
    function calculateFixedPosition() {
        if (!tooltipElement || !triggerElement) return;

        const tooltipRect = tooltipElement.getBoundingClientRect();
        const triggerRect = triggerElement.getBoundingClientRect();
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        const gap = 8; // gap between trigger and tooltip
        const pad = 10; // viewport edge padding

        // Determine best position (flip if needed, fall back to top/bottom when horizontal space is insufficient)
        let pos = position;
        switch (position) {
            case 'top':
                if (triggerRect.top - tooltipRect.height - gap < pad) pos = 'bottom';
                break;
            case 'bottom':
                if (triggerRect.bottom + tooltipRect.height + gap > vh - pad) pos = 'top';
                break;
            case 'left':
                if (triggerRect.left - tooltipRect.width - gap < pad) {
                    // Try right first, fall back to bottom if right also doesn't fit
                    if (triggerRect.right + tooltipRect.width + gap <= vw - pad) pos = 'right';
                    else pos = 'bottom';
                }
                break;
            case 'right':
                if (triggerRect.right + tooltipRect.width + gap > vw - pad) {
                    // Try left first, fall back to bottom if left also doesn't fit
                    if (triggerRect.left - tooltipRect.width - gap >= pad) pos = 'left';
                    else pos = 'bottom';
                }
                break;
        }

        // Compute fixed coordinates
        let top = 0;
        let left = 0;
        switch (pos) {
            case 'top':
                top = triggerRect.top - tooltipRect.height - gap;
                left = triggerRect.left + triggerRect.width / 2 - tooltipRect.width / 2;
                break;
            case 'bottom':
                top = triggerRect.bottom + gap;
                left = triggerRect.left + triggerRect.width / 2 - tooltipRect.width / 2;
                break;
            case 'left':
                top = triggerRect.top + triggerRect.height / 2 - tooltipRect.height / 2;
                left = triggerRect.left - tooltipRect.width - gap;
                break;
            case 'right':
                top = triggerRect.top + triggerRect.height / 2 - tooltipRect.height / 2;
                left = triggerRect.right + gap;
                break;
        }

        // Clamp to viewport
        left = Math.max(pad, Math.min(left, vw - tooltipRect.width - pad));
        top = Math.max(pad, Math.min(top, vh - tooltipRect.height - pad));

        fixedTop = top;
        fixedLeft = left;
    }

    /**
     * Replace $...$ inline LaTeX delimiters with KaTeX-rendered HTML.
     * Uses non-greedy matching to handle multiple formulas in one string.
     */
    function renderMathInline(content: string): string {
        return content.replace(/\$([^$]+)\$/g, (_, formula) => {
            try {
                return katex.renderToString(formula, {throwOnError: false, displayMode: false});
            } catch {
                return formula;
            }
        });
    }

    /** Escape HTML entities for safe rendering when using plain text */
    function escapeHtml(str: string): string {
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    /**
     * Compute the final tooltip content as HTML string.
     * Priority: html prop > text prop. If math=true, process LaTeX.
     */
    let renderedContent = $derived.by(() => {
        let content = html || escapeHtml(text);
        if (math) {
            content = renderMathInline(content);
        }
        return content;
    });

    // Register/unregister click-outside listener + scroll-dismiss
    $effect(() => {
        if (visible) {
            document.addEventListener('click', handleClickOutside);
            document.addEventListener('touchstart', handleTouchOutside);
            document.addEventListener('scroll', handleScrollDismiss, {capture: true, passive: true});
            return () => {
                document.removeEventListener('click', handleClickOutside);
                document.removeEventListener('touchstart', handleTouchOutside);
                document.removeEventListener('scroll', handleScrollDismiss, true);
            };
        }
    });

    function handleScrollDismiss() {
        if (visible) hide();
    }

    function handleTouchOutside(event: TouchEvent) {
        if (visible && triggerElement && !triggerElement.contains(event.target as Node)) {
            hide();
        }
    }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
    bind:this={triggerElement}
    class="tooltip-wrapper"
    onclick={(e) => {
        if (!isTouchInteraction) toggle(e);
    }}
    onkeydown={handleKeydown}
    onmouseenter={() => {
        if (!isTouchInteraction) show();
    }}
    onmouseleave={() => {
        if (!isTouchInteraction) hide();
    }}
    ontouchstart={handleTouchStart}
    role="button"
    tabindex="0"
>
    {#if children}
        {@render children()}
    {/if}
</div>

{#if visible}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div bind:this={tooltipElement} class="tooltip-fixed" style="max-width: {maxWidth}; top: {fixedTop}px; left: {fixedLeft}px;" role="tooltip" data-testid="tooltip-content">
        {#if math || html}
            {@html renderedContent}
        {:else}
            {text}
        {/if}
    </div>
{/if}

<style>
    .tooltip-wrapper {
        position: relative;
        display: inline-flex;
        cursor: help;
    }

    /* Fixed-position tooltip: rendered relative to viewport, never clipped by overflow */
    .tooltip-fixed {
        position: fixed;
        z-index: 9999;
        padding: 0.5rem 0.75rem;
        font-size: 0.8125rem;
        line-height: 1.25rem;
        font-weight: 400;
        text-transform: none;
        letter-spacing: normal;
        color: white;
        background-color: #1f2937;
        border-radius: 0.375rem;
        box-shadow:
            0 4px 6px -1px rgb(0 0 0 / 0.1),
            0 2px 4px -2px rgb(0 0 0 / 0.1);
        white-space: pre-line;
        word-wrap: break-word;
        pointer-events: auto;
        min-width: 120px;
        width: max-content;
        max-height: 50vh;
        overflow-y: auto;
        cursor: default;
        user-select: text;
    }

    /* Dark mode tooltip */
    :global(html.dark) .tooltip-fixed {
        background-color: #61666f;
    }

    /* KaTeX inside tooltip needs adjusted styles */
    .tooltip-fixed :global(.katex) {
        color: #93c5fd;
        font-size: 0.9em;
    }
</style>
