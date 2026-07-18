<script lang="ts">
    /**
     * Tooltip - Instant tooltip with click-outside dismiss
     *
     * Features:
     * - 0ms delay on hover; stays open indefinitely while the pointer remains
     *   over the trigger OR the tooltip body itself (no fixed disappear timer
     *   while genuinely hovered — see bug note below)
     * - Also opens on click/tap ("pinned"): stays open indefinitely while
     *   hovered, and only starts a multi-second grace-dismiss timer once the
     *   pointer actually leaves (mouse) or contact ends (touch)
     * - Fixed positioning: renders relative to viewport, never clipped by modal/overflow
     * - Auto-positions to avoid viewport overflow
     * - Closes on click outside
     * - Supports plain text, raw HTML, and inline LaTeX ($...$) via KaTeX
     *
     * Bug fixed: previously, a fixed 5s auto-dismiss timer started as soon as
     * a click/tap opened the tooltip, regardless of continued pointer contact
     * — so a tooltip opened via a touch-classified interaction (confirmed via
     * live repro with a touch-enabled browser context: a tap made the
     * tooltip vanish at exactly t=5s even though "contact" was ongoing)
     * disappeared while the user was still trying to read it. Fixed by
     * deferring the grace timer to the moment contact actually ends
     * (mouseleave from both trigger+tooltip, or touchend), and by giving the
     * tooltip body its own mouseenter/mouseleave handlers so moving the
     * pointer from the trigger into the tooltip content (e.g. to select
     * text) no longer closes it either.
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
        /** Extra classes for the trigger wrapper (e.g. `min-w-0` to allow shrinking/truncating inside a flex row) */
        wrapperClass?: string;
        children?: Snippet;
    }

    let {text = '', html = '', math = false, position = 'top', maxWidth = '400px', wrapperClass = '', children}: Props = $props();

    let visible = $state(false);
    let tooltipElement: HTMLDivElement | undefined = $state(undefined);
    let triggerElement: HTMLDivElement | undefined = $state(undefined);

    // Fixed position coordinates (viewport-relative)
    let fixedTop = $state(0);
    let fixedLeft = $state(0);

    /** True once opened via click/tap ("pinned") rather than plain hover.
     *  Pinned tooltips stay open indefinitely while the pointer remains over
     *  the trigger or the tooltip body; only once contact ends does a grace
     *  timer start (see PINNED_LEAVE_GRACE_MS). Plain-hover tooltips use a
     *  much shorter bridge delay instead, just enough to cross the visual
     *  gap between trigger and tooltip without flicker. */
    let pinned = $state(false);
    /** Whether the current interaction is touch-based */
    let isTouchInteraction = $state(false);

    /** Grace period after a *pinned* tooltip loses contact (mouse leaves both
     *  trigger and tooltip, or a touch ends) before it auto-dismisses. */
    const PINNED_LEAVE_GRACE_MS = 5000;
    /** Near-instant delay for plain hover — bridges the gap between trigger
     *  and tooltip elements when the pointer moves from one to the other,
     *  without introducing a perceptible "stays open" timer. */
    const HOVER_LEAVE_BRIDGE_MS = 150;

    /** Single pending-hide timer, shared by both the pinned grace period and
     *  the plain-hover bridge delay — always cancelled on re-entry. */
    let pendingHideTimer: ReturnType<typeof setTimeout> | null = $state(null);

    function clearPendingHide() {
        if (pendingHideTimer) {
            clearTimeout(pendingHideTimer);
            pendingHideTimer = null;
        }
    }

    function scheduleHide(delayMs: number) {
        clearPendingHide();
        pendingHideTimer = setTimeout(() => {
            hide();
        }, delayMs);
    }

    function show() {
        visible = true;
        // Defer position calculation to next frame (tooltip must be in DOM first)
        requestAnimationFrame(calculateFixedPosition);
    }

    function hide() {
        visible = false;
        pinned = false;
        clearPendingHide();
        isTouchInteraction = false;
    }

    function toggle(event: MouseEvent) {
        event.stopPropagation();
        // A click while it's already open-but-not-pinned (i.e. shown purely
        // via hover, which on desktop always precedes a click on the same
        // element) means "pin it open", not "close it" — only a click while
        // ALREADY pinned acts as an explicit close.
        if (visible && pinned) {
            hide();
        } else {
            clearPendingHide();
            show();
            pinned = true;
        }
    }

    /** Pointer entered trigger OR tooltip body — cancel any scheduled hide
     *  and ensure it's shown (covers both plain hover and re-entry into a
     *  pinned tooltip before its grace period elapses). */
    function handlePointerEnter() {
        if (isTouchInteraction) return;
        clearPendingHide();
        if (!visible) show();
    }

    /** Pointer left trigger OR tooltip body. Pinned tooltips get a multi-
     *  second grace period (real dismiss only after contact stays lost);
     *  plain-hover tooltips get a near-instant bridge delay so moving the
     *  mouse across the small gap between trigger and tooltip doesn't close
     *  it, while still closing promptly once genuinely done hovering. */
    function handlePointerLeave() {
        if (isTouchInteraction) return;
        scheduleHide(pinned ? PINNED_LEAVE_GRACE_MS : HOVER_LEAVE_BRIDGE_MS);
    }

    function handleTouchStart(event: TouchEvent) {
        event.stopPropagation();
        isTouchInteraction = true;
        clearPendingHide();
        if (visible) {
            hide();
        } else {
            show();
            pinned = true;
            // No timer here — deferred to handleTouchEnd so the tooltip
            // doesn't vanish while contact is still active (the original
            // bug: a fixed timer fired regardless of continued contact).
        }
    }

    /** Touch contact ended — start the pinned grace period now (mirrors
     *  mouse's handlePointerLeave, since touch has no hover to lean on). */
    function handleTouchEnd() {
        if (isTouchInteraction && visible && pinned) {
            scheduleHide(PINNED_LEAVE_GRACE_MS);
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            // Same "pin, don't close" rule as toggle() — see its comment.
            if (visible && pinned) {
                hide();
            } else {
                clearPendingHide();
                show();
                pinned = true;
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
    class="tooltip-wrapper {wrapperClass}"
    onclick={(e) => {
        if (!isTouchInteraction) toggle(e);
    }}
    onkeydown={handleKeydown}
    onmouseenter={handlePointerEnter}
    onmouseleave={handlePointerLeave}
    ontouchstart={handleTouchStart}
    ontouchend={handleTouchEnd}
    role="button"
    tabindex="0"
>
    {#if children}
        {@render children()}
    {/if}
</div>

{#if visible}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        bind:this={tooltipElement}
        class="tooltip-fixed"
        style="max-width: min({maxWidth}, calc(100vw - 20px)); top: {fixedTop}px; left: {fixedLeft}px;"
        role="tooltip"
        data-testid="tooltip-content"
        onmouseenter={handlePointerEnter}
        onmouseleave={handlePointerLeave}
    >
        {#if math || html}
            {@html renderedContent}
        {:else}
            <span style="white-space: pre-line">{text}</span>
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
