/**
 * How a view on screen asks again for what it shows once the server has caught up on prices (lot Y5-1; plan phase01SleepWake
 * «Z-14b + Z-15»).
 *
 * The portfolio bus says `{kind: 'prices'}` (`notifyPricesCaughtUp()`, from `priceRefresh.ts`) when a catch-up updated something;
 * every cache marks its answers stale on it (`TimeSeriesStore.markStale()`, `riskStore`, `lotsAnalysisStore`…), and a view that
 * listens reads them again. A view calls `onPricesCaughtUp(reload)` in its lifecycle and keeps the function it returns to stop.
 *
 * Never `refreshVersion` nor `requestPortfolioRefresh()`: those are the user's «Aggiorna», which spins the page's icon and says
 * the page is busy. A catch-up reload is not a load the user asked for: the figures stay on screen, nothing says busy
 * (decision of Z-18), and the reload goes through the view's own request code, outside `pageBusy`.
 *
 * @module features/price-refresh/onPricesCaughtUp
 */

import {registerPortfolioMutationListener} from '$lib/stores/portfolio/portfolioMutation';

/** One key per call: a page may hold several views that listen (the risk controllers of a list, a detail). */
let nextListener = 0;

/**
 * Call `reload` once for every `{kind: 'prices'}` of the bus, after the dispatch (a microtask), so that every cache has already
 * marked its answers stale and the reload finds them stale. Any other signal is ignored. A `reload` that throws or rejects is
 * logged, never rethrown: the view's own request code reports its failures, and one view must not stop another's reload.
 *
 * @returns the function that stops the listening (harmless to call twice).
 */
export function onPricesCaughtUp(reload: () => void | Promise<void>): () => void {
    const run = () => {
        try {
            void Promise.resolve(reload()).catch((error: unknown) => console.error('[onPricesCaughtUp] reload failed', error));
        } catch (error) {
            console.error('[onPricesCaughtUp] reload failed', error);
        }
    };
    return registerPortfolioMutationListener(`prices-caught-up:${++nextListener}`, (signal) => {
        if (signal.kind === 'prices') queueMicrotask(run);
    });
}
