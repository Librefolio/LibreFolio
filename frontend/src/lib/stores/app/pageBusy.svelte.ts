/**
 * pageBusy — the «big» requests a page has in flight, which its Refresh button waits for (Y11, developer decision 48 /
 * P3; contract approved 16/10/2026).
 *
 * Each page has one Refresh button in its own top bar. It spins, greyed, while the page's big requests are pending:
 * the ones the page decides to make to (re)build what it shows — the first load, a Refresh, a change of period, scope,
 * filter or tab, the load of a panel (when it opens, when its parameters change, when the page's Refresh reloads it).
 *
 * - **Where `track` / `begin` go: on the trigger, never inside a load function.** The same `loadAll()` or
 *   `loadOverview()` also reloads the page in background (a price catch-up, a stale cache marked by a portfolio
 *   mutation), and a background reload must not spin the button (P3). Wrap the call in the `onMount`, the Refresh
 *   handler, the `$effect` of a period or filter, the opening of a panel — not the function's body, nor a listener of
 *   the portfolio bus.
 * - **Never for** the live-price poller, the actions with an indicator of their own (price and FX sync, the PAC's
 *   «Calcola», the import wizard, a save in a modal), or the small background reads.
 * - **`join` for the loads a panel asks by itself** when its data is missing — the P&L candles, the contribution
 *   (decision N55). With a big request pending (the user's period, currency, scope, Refresh) it takes a token of its
 *   own, so the button also waits for what that request cascades into; on an idle page it runs without one. A
 *   background reload drops that data too, and asking it again must not spin the button (P3).
 * - **A token per request or per chain.** `end` takes it back, well or badly; a token that never comes back is dropped
 *   after its timeout (`PAGE_BUSY_TIMEOUT_MS`, two minutes, or `timeoutMs`), with one console warning naming it. The
 *   request itself is not cancelled: only the button stops waiting for it.
 * - **Scoped to the page.** `reset()` drops every token when the route changes (`onNavigate` in
 *   `routes/(app)/+layout.svelte`) and when the client session ends. A request of the old page that comes back later
 *   ends a token that is no longer there: nothing happens.
 */
import {untrack} from 'svelte';
import {registerClientSessionReset} from '$lib/stores/app/clientSession';

export interface BusyToken {
    readonly id: number;
    readonly label: string;
}

/** Past it the request counts as lost, for the button only: the request itself is not cancelled. */
export const PAGE_BUSY_TIMEOUT_MS = 120_000;

interface BusyOptions {
    /** A positive, finite number of milliseconds; anything else falls back to `PAGE_BUSY_TIMEOUT_MS`. */
    timeoutMs?: number;
}

/** Ids start at 1 and only grow, across ends, timeouts and resets: a token is never confused with another. */
let nextId = 1;
/**
 * The pending tokens, in begin order. Replaced, never mutated, so that every change is one reactive write. The writers
 * read it with `untrack`: `track` is called from the `$effect` of a period or a filter, and that effect must not start
 * depending on the list (it would run again at every token).
 */
let pending = $state.raw<readonly BusyToken[]>([]);
const timers = new Map<number, ReturnType<typeof setTimeout>>();

function timeoutOf(options: BusyOptions | undefined): number {
    const requested = options?.timeoutMs;
    return typeof requested === 'number' && Number.isFinite(requested) && requested > 0 ? requested : PAGE_BUSY_TIMEOUT_MS;
}

/** Takes the token with this id off the list and clears its timer; false when it was not pending. */
function release(id: number): boolean {
    const timer = timers.get(id);
    if (timer !== undefined) {
        clearTimeout(timer);
        timers.delete(id);
    }
    const current = untrack(() => pending);
    if (!current.some((token) => token.id === id)) return false;
    pending = current.filter((token) => token.id !== id);
    return true;
}

function begin(label: string, options?: BusyOptions): BusyToken {
    const token: BusyToken = Object.freeze({id: nextId++, label});
    const timeoutMs = timeoutOf(options);
    pending = [...untrack(() => pending), token];
    timers.set(
        token.id,
        setTimeout(() => {
            timers.delete(token.id);
            if (release(token.id)) console.warn(`[pageBusy] «${label}» still pending after ${timeoutMs} ms: counted as lost for the Refresh button`);
        }, timeoutMs),
    );
    return token;
}

function end(token: BusyToken): void {
    release(token.id);
}

async function track<T>(label: string, work: () => Promise<T>, options?: BusyOptions): Promise<T> {
    const token = begin(label, options);
    try {
        return await work();
    } finally {
        end(token);
    }
}

/**
 * A load that completes what the page is already doing (N55): like `track` while a big request is pending, without a
 * token on an idle page. Decided at the call, on the list read untracked: the panels call it from an `$effect`.
 */
async function join<T>(label: string, work: () => Promise<T>, options?: BusyOptions): Promise<T> {
    if (untrack(() => pending).length === 0) return work();
    return track(label, work, options);
}

function reset(): void {
    for (const timer of timers.values()) clearTimeout(timer);
    timers.clear();
    if (untrack(() => pending).length > 0) pending = [];
}

export const pageBusy = {
    begin,
    end,
    track,
    join,
    reset,
    /** Reactive: at least one big request of this page is pending. */
    get busy(): boolean {
        return pending.length > 0;
    },
    /** The pending labels, in begin order: diagnostics and tests. */
    get labels(): readonly string[] {
        return pending.map((token) => token.label);
    },
};

registerClientSessionReset('pageBusy', reset);
