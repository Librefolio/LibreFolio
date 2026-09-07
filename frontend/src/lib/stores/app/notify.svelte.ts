/**
 * Application events — the machine-readable half of a notification.
 *
 * A toast tells the user what happened. This tells everything else: tests,
 * diagnostics, and whoever is reading the console. The two are not
 * alternatives, they are two halves of one notification — which is why
 * `toast` is a *field* here rather than a separate call.
 *
 * Why a retained buffer and not a console line
 * --------------------------------------------
 * A console message is an *edge*: whoever wants it must be listening before it
 * fires. A test that clicks and then starts listening has already lost it —
 * and that is exactly the failure mode we are removing from the suite (passes
 * with one worker, fails with four). The ring buffer is a *state*: arriving
 * late costs nothing.
 *
 * It also cannot be `debug.log` alone. `debug` is compiled out of production
 * builds (`DEBUG_ENABLED = VITE_DEBUG === 'true' || import.meta.env.DEV`) and
 * the E2E suite runs against a production build, so a debug line does not exist
 * in the binary under test.
 *
 * Cost: one array of at most RING_CAP small objects. It ships, deliberately —
 * a rolling record of what the app just did is worth having when a user
 * reports something odd.
 *
 * Naming contract
 * ---------------
 * `name` is a stable identifier and is NEVER translated: it is the contract
 * with the machine. Use `area.thing.past-tense` — `asset.saved`,
 * `tx.import.committed`, `fx.rates.synced`. `detail` carries structured
 * values; the toast message stays free-form (and localised) for humans, so a
 * test must assert on `name`/`detail` or on the toast *variant*, never on the
 * toast text.
 */

import {toasts, type ToastVariant} from '$lib/stores/app/toastStore.svelte';

export interface AppEvent {
    /** Monotonic, per page load. Lets a reader ask "anything new since?". */
    seq: number;
    /** Stable, untranslated identifier. */
    name: string;
    /** Structured payload. Keep it small and serialisable. */
    detail?: Record<string, unknown>;
    /** Epoch ms. */
    at: number;
}

export interface NotifyOptions {
    name: string;
    detail?: Record<string, unknown>;
    /**
     * Present only when the user is owed a message. The rule: a toast is owed
     * when the outcome is not already visible, or is irreversible, or is
     * partial. Everything else is a silent event.
     */
    toast?: {variant: ToastVariant; message: string; duration?: number};
}

/** Enough to cover a user's last few interactions, small enough to ignore. */
const RING_CAP = 100;

let seq = 0;
/**
 * Mutated in place — never reassigned. `window.__lf.events` holds this exact
 * reference, so replacing the array would silently detach every reader.
 */
const ring: AppEvent[] = [];

export function notify(opts: NotifyOptions): AppEvent {
    seq += 1;
    const event: AppEvent = {seq, name: opts.name, detail: opts.detail, at: Date.now()};

    ring.push(event);
    while (ring.length > RING_CAP) ring.shift();

    // toasts.show() already mirrors the message to debug[level] with the HTML
    // stripped, so the human-readable half needs nothing extra here.
    if (opts.toast) {
        toasts.show(opts.toast.variant, opts.toast.message, opts.toast.duration);
    }

    return event;
}

// Published for E2E. Reading a state cannot race; listening for an edge can.
if (typeof window !== 'undefined') {
    const w = window as unknown as {__lf?: Record<string, unknown>};
    w.__lf = w.__lf ?? {};
    w.__lf.events = ring;
    w.__lf.seq = () => seq;
}
