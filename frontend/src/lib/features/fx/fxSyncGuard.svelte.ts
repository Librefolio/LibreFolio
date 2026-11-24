/**
 * One sync per FX pair at a time (81 U35).
 *
 * Testlist 7.2 (23/11): during «Sinc. Tutto», which is long, a 3-month sync of one pair started as well, with no warning;
 * the reader expects the app to say that a sync is already running and to make them wait. Two guards, one error:
 *
 * - **The browser's registry** (here): the pairs this tab is syncing. `guardedFxSync` claims a request's pairs before the
 *   call and lets them go when it ends, whatever the end; a request for a pair already claimed — by another button, another
 *   window, «Sinc. Tutto» — never goes out. «Sinc. Tutto» counts as syncing for every pair it touches: it claims them all.
 * - **The server's 409** (`fx_sync_in_progress`): the pair is syncing in another tab or for another user. It becomes the same
 *   error, with the pairs and the start the server names.
 *
 * Nothing is queued: the wait is the reader's, and the buttons of a syncing pair are off with the reason
 * (`isFxPairSyncing`, reactive, so a button re-reads it by itself).
 */
import {SvelteMap} from 'svelte/reactivity';

/** pair key (alphabetical slug) → the moment this tab started syncing it */
const inFlight = new SvelteMap<string, string>();

/** The pair as the registry keeps it: upper case, alphabetical (`usd-eur` → `EUR-USD`), as the server keeps it. */
export function fxPairKey(slug: string): string {
    const parts = slug.split('-').map((part) => part.trim().toUpperCase());
    return parts.length === 2 ? [...parts].sort().join('-') : slug.trim().toUpperCase();
}

/** Is a sync of this pair running in this tab? Reactive. */
export function isFxPairSyncing(slug: string): boolean {
    return inFlight.has(fxPairKey(slug));
}

/** Which of these pairs are syncing, as keys, in the order asked. Reactive. */
export function fxPairsSyncing(slugs: readonly string[]): string[] {
    return [...new Set(slugs.map(fxPairKey))].filter((key) => inFlight.has(key));
}

/** A pair asked for is already syncing — here, or on the server (another tab, another user). */
export class FxSyncBusyError extends Error {
    constructor(
        /** The busy pairs, as keys (`EUR-USD`). */
        readonly pairs: readonly string[],
        /** When the running sync began, as the server says it; null when the browser's own registry refused. */
        readonly startedAt: string | null,
    ) {
        super(`A sync of ${pairs.join(', ')} is already running`);
        this.name = 'FxSyncBusyError';
    }
}

/** The 409 of `POST /fx/currencies/sync` as a busy error; null for anything else. */
function busyFromConflict(error: unknown): FxSyncBusyError | null {
    const response = (error as {response?: {status?: number; data?: {detail?: unknown}}} | null)?.response;
    const detail = response?.status === 409 ? (response.data?.detail as {code?: unknown; pairs?: unknown} | undefined) : undefined;
    if (detail?.code !== 'fx_sync_in_progress' || !Array.isArray(detail.pairs)) return null;
    const entries = detail.pairs.filter((entry): entry is {pair: string; started_at?: string} => typeof (entry as {pair?: unknown})?.pair === 'string');
    return new FxSyncBusyError(
        entries.map((entry) => fxPairKey(entry.pair)),
        entries[0]?.started_at ?? null,
    );
}

/**
 * The refusal a sync of these pairs would get right now, or null when none is busy. For a handler that keeps state of its own
 * (a spinner, a generation that names the owner of a result): ask first, before touching it, so a refused press never takes
 * the place of the sync that is running.
 */
export function fxSyncBusyFor(pairs: readonly string[]): FxSyncBusyError | null {
    const busy = fxPairsSyncing(pairs);
    return busy.length > 0 ? new FxSyncBusyError(busy, inFlight.get(busy[0]) ?? null) : null;
}

/** The busy error an error is — itself or the server's 409 — or null: what a `catch` asks before it says «failed». */
export function asFxSyncBusy(error: unknown): FxSyncBusyError | null {
    return error instanceof FxSyncBusyError ? error : busyFromConflict(error);
}

/** «A sync of EUR/USD is already running: wait for it to finish.», in the reader's language. */
export function fxSyncBusyText(translate: (key: string, options?: {values?: Record<string, string>}) => string, error: FxSyncBusyError): string {
    return translate('fx.sync.alreadyRunning', {values: {pairs: error.pairs.map((pair) => pair.replace('-', '/')).join(', ')}});
}

/**
 * Run `call`, an FX sync of `pairs`, holding its pairs for as long as it lasts. A request over several pairs is refused whole
 * when one is busy, naming the busy ones, and claims none of the others. The server's 409 ends as the same error.
 */
export async function guardedFxSync<T>(pairs: readonly string[], call: () => Promise<T>): Promise<T> {
    const keys = [...new Set(pairs.map(fxPairKey))];
    const busy = keys.filter((key) => inFlight.has(key));
    if (busy.length > 0) throw new FxSyncBusyError(busy, inFlight.get(busy[0]) ?? null);
    const startedAt = new Date().toISOString();
    for (const key of keys) inFlight.set(key, startedAt);
    try {
        return await call();
    } catch (error) {
        throw busyFromConflict(error) ?? error;
    } finally {
        for (const key of keys) inFlight.delete(key);
    }
}

/** Forget every claim (tests, sign-out). */
export function resetFxSyncGuard(): void {
    inFlight.clear();
}
