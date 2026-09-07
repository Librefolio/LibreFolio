/**
 * clearTimer — cancel a pending timeout and forget its handle, in one place.
 *
 * The idiom `if (t) { clearTimeout(t); t = null; }` recurs wherever a component
 * arms a long-press / deferred action on touch and has to tear it down when the
 * touch ends. Written out it is three lines of ceremony around one intent:
 * "there is no timer any more". Callers assign the result back to their handle:
 *
 *   longPressTimer = clearTimer(longPressTimer);
 *
 * Returns `null` so the handle is cleared in the same expression. A `null`
 * (or already-elapsed) handle is a no-op. This is intentionally the *plain*
 * cancel: sites that also reset extra state (a start position, an "active" flag)
 * keep doing that themselves — only the timeout bookkeeping is shared.
 */
export function clearTimer(timer: ReturnType<typeof setTimeout> | null): null {
    if (timer) clearTimeout(timer);
    return null;
}
