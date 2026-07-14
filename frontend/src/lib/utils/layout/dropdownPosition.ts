/**
 * dropdownPosition.ts — shared "fixed position, escape overflow-hidden" dropdown placement.
 *
 * PageToolbar's own card wrapper has `overflow-hidden` (rounded-corner clipping) — any
 * hand-rolled dropdown panel positioned `absolute` inside it gets visually clipped the moment
 * it would overflow the card's bounds (Round 14 bug report: assetsList's "Tutti i tipi" panel).
 * `CurrencySearchSelect` (SearchSelect.svelte) already avoids this by computing a `fixed`
 * position from the trigger's `getBoundingClientRect()` instead of relying on `absolute` +
 * an ancestor's positioning context — this module extracts the same technique (previously
 * page-local to dashboard/+page.svelte's broker-filter/AI-export dropdowns) so any other
 * hand-rolled dropdown can reuse it instead of re-deriving the clamping math.
 *
 * Usage: call `getFixedDropdownPosition(triggerEl, panelEl, horizontalAlign)` after the panel
 * opens (and again on window resize/scroll while open) and apply the result as
 * `style:left`/`style:top` on a `class="fixed z-50 ..."` panel (not `absolute`).
 */

export interface DropdownPosition {
    left: number;
    top: number;
}

/** Minimum gap kept between the dropdown panel and the viewport edges. */
export const DROPDOWN_VIEWPORT_MARGIN = 8;
/** Gap between the trigger and the panel (below it, or above when flipped). */
export const DROPDOWN_TRIGGER_GAP = 4;

export function clamp(value: number, min: number, max: number): number {
    return Math.min(Math.max(value, min), max);
}

/**
 * Computes a viewport-clamped `{left, top}` for a `position:fixed` dropdown panel, anchored
 * below (or above, if there isn't room) the given trigger element.
 *
 * @param triggerEl Element the panel is anchored to (its own trigger button).
 * @param panelEl The panel itself (measured for width/height — pass `null` before first
 *   render, a sensible 224px-wide/0-height fallback is used until the panel has a real box).
 * @param horizontalAlign 'start' aligns the panel's left edge with the trigger's left edge;
 *   'end' aligns the panel's right edge with the trigger's right edge.
 */
export function getFixedDropdownPosition(triggerEl: HTMLElement | null, panelEl: HTMLElement | null, horizontalAlign: 'start' | 'end'): DropdownPosition {
    if (!triggerEl) return {left: DROPDOWN_VIEWPORT_MARGIN, top: DROPDOWN_VIEWPORT_MARGIN};

    const triggerRect = triggerEl.getBoundingClientRect();
    const panelRect = panelEl?.getBoundingClientRect();
    const panelWidth = panelRect?.width ?? 224;
    const panelHeight = panelRect?.height ?? 0;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    const minLeft = DROPDOWN_VIEWPORT_MARGIN;
    const maxLeft = Math.max(minLeft, viewportWidth - panelWidth - DROPDOWN_VIEWPORT_MARGIN);
    let left = horizontalAlign === 'end' ? triggerRect.right - panelWidth : triggerRect.left;
    left = clamp(left, minLeft, maxLeft);

    const minTop = DROPDOWN_VIEWPORT_MARGIN;
    const maxTop = Math.max(minTop, viewportHeight - panelHeight - DROPDOWN_VIEWPORT_MARGIN);
    let top = triggerRect.bottom + DROPDOWN_TRIGGER_GAP;
    if (panelHeight > 0 && top + panelHeight > viewportHeight - DROPDOWN_VIEWPORT_MARGIN) {
        top = triggerRect.top - panelHeight - DROPDOWN_TRIGGER_GAP;
    }
    top = clamp(top, minTop, maxTop);

    return {left, top};
}
