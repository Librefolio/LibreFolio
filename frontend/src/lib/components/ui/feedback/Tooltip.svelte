<script lang="ts">
    /**
     * Tooltip - hover-delayed tooltip with click-outside dismiss
     *
     * Features:
     * - Delayed open on plain hover (`showDelayMs`, default 500ms — T2: the
     *   pointer must rest on the trigger; instant hover tooltips flash under
     *   the cursor while the user is just crossing the page). Click/tap and
     *   keyboard open instantly instead — intent there is explicit, a delay
     *   would only be latency. Stays open indefinitely while the pointer remains
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
    import {escapeHtml, renderInlineMath} from '$lib/utils/inlineMath';
    import {sanitizeHtml} from '$lib/utils/core/sanitizeHtml';
    import {isOutsideClick} from '$lib/utils/core/clickOutside';

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
        /** Child owns native interaction semantics (for example, a button or link). */
        interactiveChild?: boolean;
        /**
         * The trigger is a part of a larger control — a badge or an icon inside a row button, an option (85 BTN-0c,
         * D16): the click belongs to that control. The wrapper is a plain `<span>` that opens on a mouse rest only: no
         * pin on click, no `stopPropagation`, no tab stop, no touch handling. Without it, a click on the part stopped
         * at the wrapper and the control never acted (a route of `FxProviderSelect` was not added).
         */
        insideControl?: boolean;
        /** Delay before a plain-hover open (T2). Click/tap/keyboard always open
         *  instantly. Pass 0 to restore the pre-T2 instant hover. */
        showDelayMs?: number;
        /** `data-testid` on the trigger wrapper, for tests that need to address this tooltip. */
        testId?: string;
        /** Open at once when the keyboard brings the focus inside the trigger, close when it leaves (77 SEL-D2: an
         *  icon-only button names itself through its tooltip, to the keyboard as to the pointer). A focus a click
         *  gives is not a keyboard focus: the pointer has its own path. */
        openOnFocus?: boolean;
        /** Asked at the moment of opening, by every path, with the trigger: `false` opens nothing (77 SEL-D2: the name of
         *  an icon whose word is in view beside it would only repeat it). Absent: always. */
        showIf?: (trigger: HTMLElement) => boolean;
        /** The box the tooltip is placed against, when it is not the trigger (77 SEL-M: the reason of a disabled item of a
         *  row menu goes against the whole menu). Beside it, right then left, level with the trigger; with no room on
         *  either side, above it, else below it: never over it. Absent: the trigger, as always. */
        anchor?: HTMLElement | null;
        /** External-target mode (85 BTN-0, the standard button): the element the tooltip belongs to, owned by someone
         *  else. No wrapper is rendered and no gesture is read here: `open` decides, the owner (`pressable`) reads the
         *  gestures and closes it. Drawing, placement, portal and scroll-following stay the ones of the wrapper mode. */
        trigger?: HTMLElement | null;
        /** External-target mode: whether the tooltip shows. */
        open?: boolean;
        /** External-target mode: the pointer entered or left the tooltip body (the owner keeps it open meanwhile). */
        onbodypointer?: (inside: boolean) => void;
        children?: Snippet;
    }

    let {text = '', html = '', math = false, position = 'top', maxWidth = '400px', wrapperClass = '', interactiveChild = false, insideControl = false, showDelayMs = 500, testId = '', openOnFocus = false, showIf, anchor = null, trigger, open = false, onbodypointer, children}: Props = $props();

    let visible = $state(false);
    let tooltipElement: HTMLDivElement | undefined = $state(undefined);
    let triggerElement: HTMLElement | undefined = $state(undefined);
    /** The tooltip of an element owned by someone else (`trigger` given): no wrapper, `open` decides. */
    let external = $derived(trigger !== undefined);

    $effect(() => {
        if (!external) return;
        triggerElement = trigger ?? undefined;
        visible = open && !!trigger;
    });

    // External mode: the content or the side can change while open (a reason replaced, the finger's side): place again.
    $effect(() => {
        if (!external || !visible) return;
        void renderedContent;
        void position;
        schedulePositionUpdate();
    });

    // Fixed position coordinates (viewport-relative)
    let fixedTop = $state(0);
    let fixedLeft = $state(0);
    let pendingPositionFrame: number | null = null;

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
    const PINNED_LEAVE_GRACE_MS = 30000;
    /** Near-instant delay for plain hover — bridges the gap between trigger
     *  and tooltip elements when the pointer moves from one to the other,
     *  without introducing a perceptible "stays open" timer. */
    const HOVER_LEAVE_BRIDGE_MS = 150;

    /** True once the dismissal listeners are actually attached.
     *
     *  They are attached by an `$effect`, which runs *after* the tooltip is in
     *  the DOM — so between "visible" and "dismissable" there is a window where
     *  a click outside hits nobody. A user does not notice: they cannot click
     *  faster than a frame. A test can, and did: `tooltip-component.spec.ts`
     *  clicked as soon as the element was visible and failed roughly one run in
     *  four under load, because a missed dismissal does not merely delay the
     *  close — it leaves the tooltip pinned for `PINNED_LEAVE_GRACE_MS`, thirty
     *  seconds.
     *
     *  Published as `data-dismissable` so the state can be waited on instead of
     *  guessed at. */
    let listenersAttached = $state(false);

    /** Single pending-hide timer, shared by both the pinned grace period and
     *  the plain-hover bridge delay — always cancelled on re-entry.
     *
     *  The timer handles are plain variables, not `$state`: nothing renders
     *  them, and a teardown reads `$state` as it was before its latest write
     *  unless an effect flush has run since — the destroy cleanup below saw
     *  `null` and left the pending timer running after the tooltip was gone. */
    let pendingHideTimer: ReturnType<typeof setTimeout> | null = null;
    /** Pending hover-open timer (T2) — cancelled when the pointer leaves before
     *  the delay elapses, and by any explicit open/close path. */
    let pendingShowTimer: ReturnType<typeof setTimeout> | null = null;

    function clearPendingHide() {
        if (pendingHideTimer) {
            clearTimeout(pendingHideTimer);
            pendingHideTimer = null;
        }
    }

    function clearPendingShow() {
        if (pendingShowTimer) {
            clearTimeout(pendingShowTimer);
            pendingShowTimer = null;
        }
    }

    function scheduleHide(delayMs: number) {
        clearPendingHide();
        pendingHideTimer = setTimeout(() => {
            hide();
        }, delayMs);
    }

    function show() {
        clearPendingShow();
        if (showIf && triggerElement && !showIf(triggerElement)) return;
        visible = true;
        schedulePositionUpdate();
    }

    function hide() {
        visible = false;
        pinned = false;
        clearPendingHide();
        clearPendingShow();
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

    /** Pointer entered trigger OR tooltip body — cancel any scheduled hide.
     *  A closed tooltip opens after `showDelayMs` (T2): the pointer must rest,
     *  so tooltips don't flash while the user crosses the page. Re-entry into
     *  an already-open tooltip (trigger → body) is instant. */
    function handlePointerEnter() {
        if (isTouchInteraction) return;
        clearPendingHide();
        if (visible || pendingShowTimer) return;
        if (showDelayMs <= 0) {
            show();
            return;
        }
        pendingShowTimer = setTimeout(() => {
            pendingShowTimer = null;
            show();
        }, showDelayMs);
    }

    /** Pointer left trigger OR tooltip body. Pinned tooltips get a multi-
     *  second grace period (real dismiss only after contact stays lost);
     *  plain-hover tooltips get a near-instant bridge delay so moving the
     *  mouse across the small gap between trigger and tooltip doesn't close
     *  it, while still closing promptly once genuinely done hovering. A
     *  pending hover-open (T2) is simply cancelled — the pointer is gone. */
    function handlePointerLeave() {
        if (isTouchInteraction) return;
        clearPendingShow();
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

    /** The pointer went down inside the trigger: the focus that follows is the click's, not the keyboard's. */
    let pointerFocus = false;

    function handlePointerDown() {
        pointerFocus = true;
    }

    /** A browser gives a click's focus on the press, before the release: past the release the flag means nothing (and a
     *  browser that does not focus a clicked button, as Safari, would leave it set for the next keyboard focus). */
    function handlePointerRelease() {
        pointerFocus = false;
    }

    function handleFocusIn() {
        const fromPointer = pointerFocus;
        pointerFocus = false;
        if (!openOnFocus || fromPointer) return;
        clearPendingHide();
        show();
    }

    function handleFocusOut(event: FocusEvent) {
        if (triggerElement && event.relatedTarget instanceof Node && triggerElement.contains(event.relatedTarget)) return;
        pointerFocus = false;
        if (!openOnFocus || pinned) return;
        hide();
    }

    function handleClickOutside(event: MouseEvent) {
        if (visible && isOutsideClick(event.target, (el) => !triggerElement || triggerElement.contains(el) || (tooltipElement?.contains(el) ?? false))) {
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

    // Cancel every pending callback on destroy so a removed tooltip can't fire
    // later. The position frame too: destroyed before its first re-render, the
    // tooltip never ran the listeners effect whose teardown cancels it.
    $effect(() => () => {
        clearPendingShow();
        clearPendingHide();
        if (pendingPositionFrame !== null) {
            cancelAnimationFrame(pendingPositionFrame);
            pendingPositionFrame = null;
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

        if (anchor) {
            placeAgainst(anchor.getBoundingClientRect(), triggerRect, tooltipRect, vw, vh, gap, pad);
            return;
        }

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

    /** Beside the anchor (the asked side first, then the other), level with the trigger; else above it, else below. */
    function placeAgainst(anchorRect: DOMRect, triggerRect: DOMRect, tooltipRect: DOMRect, vw: number, vh: number, gap: number, pad: number) {
        const fitsRight = anchorRect.right + gap + tooltipRect.width <= vw - pad;
        const fitsLeft = anchorRect.left - gap - tooltipRect.width >= pad;
        const sides = position === 'left' ? ['left', 'right'] : ['right', 'left'];
        const side = sides.find((candidate) => (candidate === 'right' ? fitsRight : fitsLeft));
        let top: number;
        let left: number;
        if (side) {
            left = side === 'right' ? anchorRect.right + gap : anchorRect.left - gap - tooltipRect.width;
            top = triggerRect.top + triggerRect.height / 2 - tooltipRect.height / 2;
        } else {
            const above = anchorRect.top - gap - tooltipRect.height >= pad;
            top = above ? anchorRect.top - gap - tooltipRect.height : anchorRect.bottom + gap;
            left = anchorRect.left + anchorRect.width / 2 - tooltipRect.width / 2;
        }
        fixedLeft = Math.max(pad, Math.min(left, vw - tooltipRect.width - pad));
        fixedTop = Math.max(pad, Math.min(top, vh - tooltipRect.height - pad));
    }

    function schedulePositionUpdate() {
        if (pendingPositionFrame !== null) cancelAnimationFrame(pendingPositionFrame);
        pendingPositionFrame = requestAnimationFrame(() => {
            pendingPositionFrame = null;
            calculateFixedPosition();
        });
    }

    /**
     * Compute the final tooltip content as HTML string.
     * Priority: html prop > text prop. If math=true, process LaTeX.
     */
    let renderedContent = $derived.by(() => {
        let content = html || escapeHtml(text);
        if (math) {
            content = renderInlineMath(content);
        }
        return content;
    });

    // Keep fixed coordinates aligned while nested panels or the page scroll.
    $effect(() => {
        if (visible) {
            // External mode: the owner dismisses it; only the placement is followed here. `data-dismissable` stays true:
            // the owner (`pressable`) attaches its outside and Escape listeners in the same call that sets `open`.
            const dismissable = !external;
            if (dismissable) {
                document.addEventListener('click', handleClickOutside);
                document.addEventListener('touchstart', handleTouchOutside);
            }
            document.addEventListener('scroll', schedulePositionUpdate, {capture: true, passive: true});
            window.addEventListener('resize', schedulePositionUpdate);
            listenersAttached = true;
            return () => {
                listenersAttached = false;
                if (dismissable) {
                    document.removeEventListener('click', handleClickOutside);
                    document.removeEventListener('touchstart', handleTouchOutside);
                }
                document.removeEventListener('scroll', schedulePositionUpdate, true);
                window.removeEventListener('resize', schedulePositionUpdate);
                if (pendingPositionFrame !== null) {
                    cancelAnimationFrame(pendingPositionFrame);
                    pendingPositionFrame = null;
                }
            };
        }
    });

    function handleTouchOutside(event: TouchEvent) {
        if (visible && triggerElement && !triggerElement.contains(event.target as Node)) {
            hide();
        }
    }
</script>

{#if external}
    <!-- External-target mode: the trigger lives elsewhere (pressable); nothing to wrap. -->
{:else if insideControl}
    <!-- A part of a larger control: hover names it, every other gesture is the control's. -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <span bind:this={triggerElement} class="tooltip-wrapper inside-control {wrapperClass}" data-testid={testId || undefined} onmouseenter={handlePointerEnter} onmouseleave={handlePointerLeave}>
        {#if children}
            {@render children()}
        {/if}
    </span>
{:else if interactiveChild}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        bind:this={triggerElement}
        class="tooltip-wrapper {wrapperClass}"
        data-testid={testId || undefined}
        onclick={(e) => {
            if (!isTouchInteraction) toggle(e);
        }}
        onfocusin={handleFocusIn}
        onpointerdown={handlePointerDown}
        onpointerup={handlePointerRelease}
        onpointercancel={handlePointerRelease}
        onfocusout={handleFocusOut}
        onmouseenter={handlePointerEnter}
        onmouseleave={handlePointerLeave}
        ontouchstart={handleTouchStart}
        ontouchend={handleTouchEnd}
    >
        {#if children}
            {@render children()}
        {/if}
    </div>
{:else}
    <div
        bind:this={triggerElement}
        class="tooltip-wrapper {wrapperClass}"
        data-testid={testId || undefined}
        onclick={(e) => {
            if (!isTouchInteraction) toggle(e);
        }}
        onkeydown={handleKeydown}
        onfocusin={handleFocusIn}
        onpointerdown={handlePointerDown}
        onpointerup={handlePointerRelease}
        onpointercancel={handlePointerRelease}
        onfocusout={handleFocusOut}
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
{/if}

{#if visible}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        bind:this={tooltipElement}
        class="tooltip-fixed"
        class:compact={external}
        style="max-width: min({maxWidth}, calc(100vw - 20px)); top: {fixedTop}px; left: {fixedLeft}px;"
        role="tooltip"
        data-testid="tooltip-content"
        data-dismissable={listenersAttached ? 'true' : 'false'}
        onmouseenter={() => (external ? onbodypointer?.(true) : handlePointerEnter())}
        onmouseleave={() => (external ? onbodypointer?.(false) : handlePointerLeave())}
    >
        {#if math || html}
            {@html sanitizeHtml(renderedContent)}
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

    /* The part of a control takes the control's cursor: a click on it is the control's. */
    .tooltip-wrapper.inside-control {
        cursor: inherit;
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
        color: var(--lf-text-on-inverse);
        background-color: var(--lf-surface-inverse);
        border-radius: 0.375rem;
        box-shadow:
            0 4px 6px -1px var(--lf-shadow-raised),
            0 2px 4px -2px var(--lf-shadow-raised);
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

    @media (max-width: 640px) {
        .tooltip-fixed {
            min-width: min(18rem, calc(100vw - 20px));
            padding: 0.75rem 0.875rem;
            font-size: 0.875rem;
            line-height: 1.35rem;
        }
    }

    /* External mode (85, the name of a standard button): a name is a word or two, so the box fits it. The minimum
       width above serves the long help texts of the information tooltips on a phone; on a button's name it drew a
       288 px box around «Edit». Two classes win over the phone rule whatever the order. */
    .tooltip-fixed.compact {
        min-width: 0;
        padding: 0.375rem 0.625rem;
    }

    /* The inverted surface (Q10): dark in the light theme, light in the dark theme — the role follows the theme by
       itself. Content written for it uses the -on-inverse roles (the other theme's colours). */

    /* KaTeX inside tooltip needs adjusted styles */
    .tooltip-fixed :global(.katex) {
        color: var(--lf-info-on-inverse);
        font-size: 0.9em;
    }
</style>
