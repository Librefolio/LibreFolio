// @vitest-environment jsdom
/**
 * The FX sync guard (81 U35): one sync per pair at a time.
 *
 * Testlist 7.2 (23/11): during «Sinc. Tutto» a 3-month sync of one pair started as well, with no warning. The browser's
 * registry says it before the request goes out; the server's 409 (`fx_sync_in_progress`) says it when another tab or user is
 * syncing the pair. Both end as one error, `FxSyncBusyError`, which the callers say in the reader's language.
 *
 * Pinned:
 * - a pair is «syncing» from the moment its sync is claimed to the moment it ends, whatever the end;
 * - a second sync of a pair that is syncing never calls the API, and throws `FxSyncBusyError` naming the pair;
 * - the two spellings of a pair (`USD-EUR`, `EUR-USD`) are one pair;
 * - a request touching several pairs, one busy, is refused whole and claims none of the others («Sinc. Tutto»);
 * - different pairs sync together;
 * - the server's 409 becomes the same error, with the pairs and the start it names; any other error passes through;
 * - the error says itself through one catalogue key, with the pairs as «EUR/USD».
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

import {setupI18n} from '$test/component';
import {get} from 'svelte/store';
import {_} from '$lib/i18n';

import {asFxSyncBusy, FxSyncBusyError, fxPairsSyncing, fxSyncBusyFor, fxSyncBusyText, guardedFxSync, isFxPairSyncing, resetFxSyncGuard} from './fxSyncGuard.svelte';

beforeAll(async () => {
    await setupI18n('en');
});

afterEach(() => {
    resetFxSyncGuard();
});

/** A call that ends when the test says so. */
function pending<T>() {
    let resolve!: (value: T) => void;
    let reject!: (error: unknown) => void;
    const promise = new Promise<T>((ok, no) => {
        resolve = ok;
        reject = no;
    });
    return {promise, resolve, reject};
}

/** The shape axios gives a 409 of the sync route. */
function conflict(pairs: Array<{pair: string; started_at: string}>) {
    return Object.assign(new Error('Request failed with status code 409'), {isAxiosError: true, response: {status: 409, data: {detail: {code: 'fx_sync_in_progress', pairs}}}});
}

describe('guardedFxSync', () => {
    it('holds the pair while its sync runs and lets it go when it ends', async () => {
        const call = pending<string>();
        const sync = guardedFxSync(['EUR-USD'], () => call.promise);
        expect(isFxPairSyncing('EUR-USD')).toBe(true);
        call.resolve('done');
        await expect(sync).resolves.toBe('done');
        expect(isFxPairSyncing('EUR-USD')).toBe(false);
    });

    it('lets the pair go when the sync fails', async () => {
        const call = pending<string>();
        const sync = guardedFxSync(['EUR-USD'], () => call.promise);
        call.reject(new Error('network'));
        await expect(sync).rejects.toThrow('network');
        expect(isFxPairSyncing('EUR-USD')).toBe(false);
    });

    it('refuses a second sync of a pair that is syncing, without calling the API', async () => {
        const first = pending<string>();
        const running = guardedFxSync(['EUR-USD'], () => first.promise);
        const second = vi.fn(async () => 'second');

        const refused = guardedFxSync(['EUR-USD'], second);

        await expect(refused).rejects.toBeInstanceOf(FxSyncBusyError);
        expect(second).not.toHaveBeenCalled();
        await refused.catch((error: FxSyncBusyError) => expect(error.pairs).toEqual(['EUR-USD']));
        first.resolve('done');
        await running;
    });

    it('takes the two spellings of a pair for one pair', async () => {
        const first = pending<string>();
        const running = guardedFxSync(['EUR-USD'], () => first.promise);
        expect(isFxPairSyncing('USD-EUR')).toBe(true);
        await expect(guardedFxSync(['USD-EUR'], async () => 'x')).rejects.toBeInstanceOf(FxSyncBusyError);
        first.resolve('done');
        await running;
    });

    it('lets different pairs sync together', async () => {
        const one = pending<string>();
        const other = pending<string>();
        const first = guardedFxSync(['EUR-USD'], () => one.promise);
        const second = guardedFxSync(['EUR-GBP'], () => other.promise);
        expect(fxPairsSyncing(['EUR-USD', 'EUR-GBP', 'CHF-EUR'])).toEqual(['EUR-USD', 'EUR-GBP']);
        one.resolve('a');
        other.resolve('b');
        await expect(Promise.all([first, second])).resolves.toEqual(['a', 'b']);
    });

    it('refuses a request over several pairs whole when one is busy, and claims none of the others', async () => {
        const busy = pending<string>();
        const running = guardedFxSync(['EUR-USD'], () => busy.promise);

        const all = guardedFxSync(['EUR-GBP', 'EUR-USD', 'CHF-EUR'], async () => 'all');
        await expect(all).rejects.toBeInstanceOf(FxSyncBusyError);
        await all.catch((error: FxSyncBusyError) => expect(error.pairs).toEqual(['EUR-USD']));

        expect(isFxPairSyncing('EUR-GBP')).toBe(false);
        expect(isFxPairSyncing('CHF-EUR')).toBe(false);
        busy.resolve('done');
        await running;
    });

    it('turns the server’s 409 into the same error, with the pairs and the start it names', async () => {
        const error = conflict([{pair: 'EUR-USD', started_at: '2026-11-24T10:00:00+00:00'}]);

        const refused = guardedFxSync(['EUR-USD'], async () => {
            throw error;
        });

        await expect(refused).rejects.toBeInstanceOf(FxSyncBusyError);
        await refused.catch((busy: FxSyncBusyError) => {
            expect(busy.pairs).toEqual(['EUR-USD']);
            expect(busy.startedAt).toBe('2026-11-24T10:00:00+00:00');
        });
        expect(isFxPairSyncing('EUR-USD'), 'a refused sync still holds the pair').toBe(false);
    });

    it('lets any other error through unchanged', async () => {
        const failure = Object.assign(new Error('boom'), {isAxiosError: true, response: {status: 500, data: {detail: 'x'}}});
        await expect(
            guardedFxSync(['EUR-USD'], async () => {
                throw failure;
            }),
        ).rejects.toBe(failure);
    });
});

describe('fxSyncBusyFor', () => {
    it('names the busy pairs of a request before it starts, and is null when none is busy', async () => {
        expect(fxSyncBusyFor(['EUR-USD'])).toBeNull();
        const running = pending<string>();
        const sync = guardedFxSync(['EUR-USD'], () => running.promise);
        expect(fxSyncBusyFor(['USD-EUR', 'EUR-GBP'])?.pairs).toEqual(['EUR-USD']);
        expect(fxSyncBusyFor(['EUR-GBP'])).toBeNull();
        running.resolve('done');
        await sync;
        expect(fxSyncBusyFor(['EUR-USD'])).toBeNull();
    });
});

describe('asFxSyncBusy and fxSyncBusyText', () => {
    it('recognises the error itself and a bare 409 of the route, and nothing else', () => {
        const own = new FxSyncBusyError(['EUR-USD'], null);
        expect(asFxSyncBusy(own)).toBe(own);
        expect(asFxSyncBusy(conflict([{pair: 'EUR-GBP', started_at: '2026-11-24T10:00:00+00:00'}]))?.pairs).toEqual(['EUR-GBP']);
        expect(asFxSyncBusy(new Error('boom'))).toBeNull();
        expect(asFxSyncBusy(null)).toBeNull();
    });

    it('says the pairs as «EUR/USD» through the catalogue', () => {
        const text = fxSyncBusyText(get(_), new FxSyncBusyError(['EUR-USD', 'EUR-GBP'], null));
        expect(text).toContain('EUR/USD');
        expect(text).toContain('EUR/GBP');
        expect(text).not.toContain('fx.sync.alreadyRunning');
    });
});
