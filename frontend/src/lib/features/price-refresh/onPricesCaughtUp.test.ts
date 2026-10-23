/**
 * onPricesCaughtUp — a view on screen asks again for what it shows when the server has caught up on prices (lot Y5-1, plan
 * phase01SleepWake «Z-14b + Z-15»).
 *
 * The portfolio bus says `{kind: 'prices'}` (`notifyPricesCaughtUp()`) once a catch-up updated something, after which every
 * cache marks what it holds stale. Only the Dashboard and the broker page reloaded on it, each with its own listener; the
 * price pages, the risk panels and the lots panel stayed behind until the user navigated. The helper is the one way a view
 * listens, so that they all do the same thing: the contract.
 *
 * 1. `onPricesCaughtUp(reload)` calls `reload` once per `{kind: 'prices'}` and for no other signal: not for `mutation`, not
 *    for `refresh` — the user's «Aggiorna» is the page's own refresh, and a page that answered it twice would spin its icon.
 * 2. It calls `reload` AFTER the dispatch: in a microtask, so that every cache's own listener has already marked its answers
 *    stale and the reload reads them as stale. Called inline, the reload would read a cache still held fresh.
 * 3. Two calls are two listeners: a page with several panels (the risk controllers of a list, a detail) reloads each of them.
 * 4. The function it returns stops the listening: nothing after it, however many signals; calling it twice is harmless.
 * 5. A `reload` that throws, or whose promise rejects, never reaches the bus or leaves an unhandled rejection: the caller's
 *    own request code reports its failures, and one view failing must not stop another's reload.
 *
 * Plain TypeScript: the node environment, the real bus.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

import {notifyPortfolioMutation, notifyPricesCaughtUp, requestPortfolioRefresh} from '$lib/stores/portfolio/portfolioMutation';

import {onPricesCaughtUp} from './onPricesCaughtUp';

const stops: Array<() => void> = [];
function listen(reload: () => void | Promise<void>): () => void {
    const stop = onPricesCaughtUp(reload);
    stops.push(stop);
    return stop;
}

afterEach(() => {
    while (stops.length > 0) stops.pop()!();
    vi.restoreAllMocks();
});

/** Let the microtasks the helper queued run. */
const settled = () => new Promise<void>((resolve) => setTimeout(resolve, 0));

describe('onPricesCaughtUp', () => {
    it('reloads once per catch-up that updated something', async () => {
        const reload = vi.fn();
        listen(reload);

        notifyPricesCaughtUp();
        await settled();
        notifyPricesCaughtUp();
        await settled();

        expect(reload).toHaveBeenCalledTimes(2);
    });

    it('ignores every other signal of the bus: a mutation, the user’s Refresh', async () => {
        const reload = vi.fn();
        listen(reload);

        requestPortfolioRefresh();
        notifyPortfolioMutation('POST', '/api/v1/transactions', {});
        await settled();

        expect(reload).not.toHaveBeenCalled();
    });

    it('reloads after the dispatch, not inside it: a cache that marks itself stale on the same signal is stale by then', async () => {
        const order: string[] = [];
        const reload = vi.fn(() => void order.push('reload'));
        listen(reload);
        // A cache listening after the view (the bus keeps listeners in registration order, and a store imported later is after).
        const {registerPortfolioMutationListener} = await import('$lib/stores/portfolio/portfolioMutation');
        const stopCache = registerPortfolioMutationListener('test:cache', (signal) => {
            if (signal.kind === 'prices') order.push('cache marks stale');
        });
        stops.push(stopCache);

        notifyPricesCaughtUp();
        expect(reload, 'not called inline').not.toHaveBeenCalled();
        await settled();

        expect(order).toEqual(['cache marks stale', 'reload']);
    });

    it('gives each call its own listener: two views, two reloads', async () => {
        const first = vi.fn();
        const second = vi.fn();
        listen(first);
        listen(second);

        notifyPricesCaughtUp();
        await settled();

        expect([first.mock.calls.length, second.mock.calls.length]).toEqual([1, 1]);
    });

    it('stops listening when the returned function is called, and calling it again is harmless', async () => {
        const reload = vi.fn();
        const stop = listen(reload);

        stop();
        stop();
        notifyPricesCaughtUp();
        await settled();

        expect(reload).not.toHaveBeenCalled();
    });

    it('stops only its own listener', async () => {
        const stopped = vi.fn();
        const kept = vi.fn();
        const stop = listen(stopped);
        listen(kept);

        stop();
        notifyPricesCaughtUp();
        await settled();

        expect([stopped.mock.calls.length, kept.mock.calls.length]).toEqual([0, 1]);
    });

    it('swallows a reload that throws or rejects, and the others still reload', async () => {
        const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
        const unhandled = vi.fn();
        process.on('unhandledRejection', unhandled);
        const after = vi.fn();
        listen(() => {
            throw new Error('sync failure');
        });
        listen(() => Promise.reject(new Error('async failure')));
        listen(after);

        notifyPricesCaughtUp();
        await settled();
        await settled();
        process.off('unhandledRejection', unhandled);

        expect(after).toHaveBeenCalledTimes(1);
        expect(unhandled).not.toHaveBeenCalled();
        expect(consoleError).toHaveBeenCalled();
    });
});
