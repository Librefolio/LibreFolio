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
     */
    import {onDestroy, onMount} from 'svelte';
    import katex from 'katex';
    import 'katex/dist/katex.min.css';

    export let text: string = '';
    /** If provided, renders raw HTML instead of plain text */
    export let html: string = '';
    /** When true, processes $...$ inline LaTeX in text/html content via KaTeX */
    export let math: boolean = false;
    export let position: 'top' | 'bottom' | 'left' | 'right' = 'top';
    export let maxWidth: string = '400px';

    let visible = false;
    let tooltipElement: HTMLDivElement;
    let triggerElement: HTMLDivElement;

    // Fixed position coordinates (viewport-relative)
    let fixedTop = 0;
    let fixedLeft = 0;

    function show() {
        visible = true;
        // Defer position calculation to next frame (tooltip must be in DOM first)
        requestAnimationFrame(calculateFixedPosition);
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

        // Determine best position (flip if needed)
        let pos = position;
        switch (position) {
            case 'top':
                if (triggerRect.top - tooltipRect.height - gap < pad) pos = 'bottom';
                break;
            case 'bottom':
                if (triggerRect.bottom + tooltipRect.height + gap > vh - pad) pos = 'top';
                break;
            case 'left':
                if (triggerRect.left - tooltipRect.width - gap < pad) pos = 'right';
                break;
            case 'right':
                if (triggerRect.right + tooltipRect.width + gap > vw - pad) pos = 'left';
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

    /**
     * Compute the final tooltip content as HTML string.
     * Priority: html prop > text prop. If math=true, process LaTeX.
     */
    function getRenderedContent(): string {
        let content = html || escapeHtml(text);
        if (math) {
            content = renderMathInline(content);
        }
        return content;
    }

    /** Escape HTML entities for safe rendering when using plain text */
    function escapeHtml(str: string): string {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    $: renderedContent = getRenderedContent();

    onMount(() => {
        document.addEventListener('click', handleClickOutside);
    });

    onDestroy(() => {
        document.removeEventListener('click', handleClickOutside);
    });
</script>

<div
        bind:this={triggerElement}
        class="tooltip-wrapper"
        on:click={toggle}
        on:keydown={handleKeydown}
        on:mouseenter={show}
        on:mouseleave={hide}
        role="button"
        tabindex="0"
>
    <slot/>
</div>

{#if visible}
    <div
            bind:this={tooltipElement}
            class="tooltip-fixed"
            style="max-width: {maxWidth}; top: {fixedTop}px; left: {fixedLeft}px;"
            role="tooltip"
    >
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
        color: white;
        background-color: #1f2937;
        border-radius: 0.375rem;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        white-space: normal;
        word-wrap: break-word;
        pointer-events: none;
        min-width: 120px;
        width: max-content;
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
