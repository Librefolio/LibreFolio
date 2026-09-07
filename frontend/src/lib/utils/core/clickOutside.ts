/**
 * The "was this click outside my surface?" test, with the one guard that only
 * two of nine copies had.
 *
 * Nine components each wrote their own `handleClickOutside`. Reading the bodies
 * rather than the names, they diverged on three axes:
 *
 * 1. **What counts as "inside".** Five asked `ref.contains(target)` (a bound
 *    element); four asked `target.closest(selector)` (a class/role marker,
 *    because their surface is portalled out of the component's own subtree and a
 *    `contains` on the local ref would miss it). These are two *expressions* of
 *    one question — "is the click on something I own?" — so this helper takes
 *    that question as a predicate the caller supplies. It is not two functions.
 *
 * 2. **Whether the target is still attached.** Only `SingleDatePicker` and
 *    `DateRangePicker` guarded `if (!target.isConnected) return;`. Their comment
 *    explains why: a nested `SimpleSelect`/`CurrencySearchSelect` removes the
 *    clicked <option> from the DOM on `mousedown`, *before* the `click` fires, so
 *    by the time the outside-handler runs the target is detached and every
 *    `contains`/`closest` says "outside" — closing the very picker the user was
 *    operating. The other seven lacked the guard and were one nested dropdown
 *    away from the same spurious close. That guard is a copy that had it right,
 *    so it is now everyone's: a detached target is treated as *not* an outside
 *    click. Connected targets — the overwhelming majority — are unaffected.
 *
 * 3. **Which event, and when.** `click` vs `mousedown`, capture vs bubble,
 *    synchronous vs `setTimeout`-deferred, gated on open-state or always-on.
 *    That is deliberately *not* folded in here. `mousedown` closes before the
 *    click reaches its target and `click` closes after — a behavioural choice a
 *    dropdown makes on purpose (it changes what happens when you click straight
 *    from one dropdown onto another). Hiding it behind a default would bury a
 *    real decision, so each component keeps its own listener registration and
 *    only delegates the *detection* to this function.
 *
 * Escape handling (two date pickers, via `<svelte:window onkeydown>`), the
 * column filter's `.filter-btn`/`[role]` skips, and the tooltip's separate
 * asymmetric touch handler are all left where they are — they are not the
 * click-outside test, they are neighbouring concerns.
 *
 * @param target  The event target (`event.target`); anything that is not an
 *                attached `Element` is treated as "not an outside click".
 * @param isInside Predicate answering "is this element part of my surface?".
 *                Return `true` to keep open. Written by the caller so the
 *                contains-vs-closest choice stays visible at the call site.
 * @returns `true` when the click should be treated as outside (i.e. close).
 */
export function isOutsideClick(target: EventTarget | null, isInside: (el: Element) => boolean): boolean {
    const el = target instanceof Element ? target : null;
    // Not an element, or detached before we ran (case 2, promoted to all):
    // do not treat as an outside click.
    if (!el || !el.isConnected) return false;
    return !isInside(el);
}
