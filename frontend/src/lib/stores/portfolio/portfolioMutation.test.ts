import {describe, expect, it, onTestFinished, vi} from 'vitest';

import * as portfolioMutation from './portfolioMutation';
import {isPortfolioAffectingMutation, notifyPortfolioMutation, registerPortfolioMutationListener} from './portfolioMutation';

describe('portfolio mutation classification', () => {
    it.each([
        ['POST', '/api/v1/transactions/commit'],
        ['POST', '/api/v1/brokers'],
        ['PATCH', '/api/v1/brokers/42'],
        ['PUT', '/api/v1/brokers/42/access'],
        ['PATCH', '/api/v1/assets'],
        ['POST', '/api/v1/assets/42/market-data/wipe'],
        ['POST', '/api/v1/assets/prices/current'],
        ['POST', '/api/v1/assets/prices/sync'],
        ['DELETE', '/api/v1/assets/events'],
        ['POST', '/api/v1/fx/currencies/sync'],
        ['DELETE', '/api/v1/fx/providers/routes'],
    ])('invalidates after %s %s', (method, path) => {
        expect(isPortfolioAffectingMutation(method, path)).toBe(true);
    });

    it.each([
        ['GET', '/api/v1/transactions'],
        ['POST', '/api/v1/transactions/validate'],
        ['POST', '/api/v1/portfolio/report'],
        ['POST', '/api/v1/assets/prices/query'],
        ['POST', '/api/v1/assets/events/query'],
        ['POST', '/api/v1/assets/provider/probe'],
        ['POST', '/api/v1/fx/currencies/convert'],
        ['POST', '/api/v1/auth/login'],
    ])('preserves cache after read-only %s %s', (method, path) => {
        expect(isPortfolioAffectingMutation(method, path)).toBe(false);
    });
});

/**
 * Page cache, phase 1 (R2 / N, decision E2 and the missing writes): the classifier also reads
 * the response body, because a sync is a write only when its answer says it wrote something.
 *
 * Red first. Today `isPortfolioAffectingMutation(method, url)` looks at the method and the path
 * only, so a sync that changed nothing still marks every Dashboard and Risk answer as old, and
 * the three real writes below (a merge, «become viewer», «leave the broker») mark nothing.
 *
 * The bodies are shaped as the backend answers (`FABulkRefreshResponse`, `FXSyncBulkResponse`,
 * `FAAssetMergeResponse` in the generated client). A body that is missing or unreadable counts
 * as a write: guessing "nothing changed" would keep a stale Dashboard on screen with no way to
 * notice it, guessing "something changed" only costs one refresh.
 *
 * The third argument is typed here because the signature in the tree still takes two.
 */
type Classify = (method: string | undefined, url: string | undefined, data?: unknown) => boolean;
type Notify = (method: string | undefined, url: string | undefined, data?: unknown) => void;

const classify = isPortfolioAffectingMutation as Classify;
const notify = notifyPortfolioMutation as Notify;

/** One asset of a bulk price sync, as `FARefreshResult` carries it. */
function assetSyncResult(assetId: number, pointsChanged: number, eventsChanged: number) {
    return {
        asset_id: assetId,
        status: 'ok',
        provider_used: 'mockprov',
        points_fetched: 20,
        points_changed: pointsChanged,
        inserted_count: pointsChanged,
        updated_count: 0,
        events_fetched: 2,
        events_changed: eventsChanged,
        errors: [],
        changed_points: null,
    };
}

/** A bulk price sync answer (`FABulkRefreshResponse`). */
function assetSyncAnswer(results: object[]) {
    return {results, success_count: results.length, errors: [], date_range: {start: '2026-09-01', end: '2026-10-06'}, total_points_changed: 0};
}

/** One pair of a bulk FX sync, as `FXSyncPairResult` carries it. */
function fxSyncResult(pair: string, pointsChanged: number) {
    return {pair, status: 'ok', provider_used: 'ECB', points_fetched: 20, points_changed: pointsChanged, errors: []};
}

/** A bulk FX sync answer (`FXSyncBulkResponse`), with or without its total. */
function fxSyncAnswer(results: Array<ReturnType<typeof fxSyncResult>>, total?: number) {
    const answer: Record<string, unknown> = {results, success_count: results.length, errors: [], date_range: {start: '2026-09-01', end: '2026-10-06'}};
    if (total !== undefined) answer.total_points_changed = total;
    return answer;
}

/** A merge answer (`FAAssetMergeResponse`). */
function mergeAnswer(dryRun: boolean) {
    return {success: true, source_asset_id: 42, target_asset_id: 7, dry_run: dryRun, preview: {transactions: 3, prices: 120, identifiers_added: []}, message: ''};
}

describe('portfolio mutation classification reads the response (page cache, phase 1)', () => {
    it('counts an asset price sync as a change only when one of its assets changed a point or an event', () => {
        const SYNC = '/api/v1/assets/prices/sync';
        const nothingWritten = assetSyncAnswer([assetSyncResult(1, 0, 0), assetSyncResult(2, 0, 0)]);
        const missingEvents = assetSyncAnswer([{asset_id: 3, status: 'ok', points_fetched: 5, points_changed: 0}]);

        expect(classify('POST', SYNC, nothingWritten), 'a price sync that changed no point and no event still marks the Dashboard and Risk answers as old').toBe(false);
        expect(classify('POST', SYNC, missingEvents), 'a result without events_changed and with zero points changed is still "nothing written"').toBe(false);
        expect(classify('POST', SYNC, assetSyncAnswer([assetSyncResult(1, 0, 0), assetSyncResult(2, 3, 0)])), 'one asset with changed points is a change').toBe(true);
        expect(classify('POST', SYNC, assetSyncAnswer([assetSyncResult(1, 0, 2)])), 'changed events (dividends, splits) are a change too').toBe(true);
    });

    it('counts an FX sync as a change only when it changed a rate, reading the total or else the per-pair counts', () => {
        const SYNC = '/api/v1/fx/currencies/sync';

        expect(classify('POST', SYNC, fxSyncAnswer([fxSyncResult('EUR-USD', 0), fxSyncResult('EUR-GBP', 0)], 0)), 'an FX sync that changed no rate still marks the Dashboard and Risk answers as old').toBe(false);
        expect(classify('POST', SYNC, fxSyncAnswer([fxSyncResult('EUR-USD', 0), fxSyncResult('EUR-GBP', 0)])), 'without total_points_changed, the per-pair counts decide: all zero is no change').toBe(false);
        expect(classify('POST', SYNC, fxSyncAnswer([fxSyncResult('EUR-USD', 0), fxSyncResult('EUR-GBP', 5)], 5)), 'a total above zero is a change').toBe(true);
        expect(classify('POST', SYNC, fxSyncAnswer([fxSyncResult('EUR-USD', 0), fxSyncResult('EUR-GBP', 4)])), 'without the total, one pair with changed points is a change').toBe(true);
    });

    it('keeps counting as a change a sync answer it cannot read, and today’s live price whatever it answers', () => {
        // Guards of what stays, asserted beside the new rule so they cannot pass on their own: today
        // every sync is a change, and a body the classifier cannot read must stay one (the safe
        // default). The live price of today stays a trigger whatever its answer (E1, the developer's
        // decision): the asset page polls it and it writes today's candle; what changes is the effect
        // — the answers are marked old and refreshed in background instead of thrown away.
        for (const path of ['/api/v1/assets/prices/sync', '/api/v1/fx/currencies/sync']) {
            for (const body of [undefined, null, 'ok', 42]) {
                expect(classify('POST', path, body), `POST ${path} with ${JSON.stringify(body) ?? 'no body'} must count as a change`).toBe(true);
            }
        }
        expect(classify('POST', '/api/v1/assets/prices/current', {results: [{asset_id: 6, value: '101.5', currency: 'USD', as_of_date: '2026-10-06', source: 'provider:mockprov'}], success_count: 1, errors: []})).toBe(true);
        expect(classify('POST', '/api/v1/assets/prices/current', {results: [{asset_id: 6, value: null, error: 'no quote'}], success_count: 0, errors: []})).toBe(true);
        // …and the new reading is in force, or the rows above prove nothing new.
        expect(classify('POST', '/api/v1/assets/prices/sync', assetSyncAnswer([assetSyncResult(1, 0, 0)])), 'the classifier does not read the sync answer yet').toBe(false);
    });

    it('counts an asset merge as a change unless it was a dry run', () => {
        const MERGE = '/api/v1/assets/merge';

        expect(classify('POST', MERGE, mergeAnswer(false)), 'a merge moves transactions from one asset to another, and the Dashboard and Risk keep the old split').toBe(true);
        expect(classify('POST', MERGE, undefined), 'a merge whose answer is missing must count as a change').toBe(true);
        expect(classify('POST', MERGE, mergeAnswer(true)), 'a dry run (the preview of the confirmation dialog) writes nothing').toBe(false);
    });

    it.each([['PATCH'], ['DELETE']])('counts %s /brokers/{id}/access/me (become viewer, leave the broker) as a change', (method) => {
        expect(classify(method, '/api/v1/brokers/7/access/me'), `${method} /brokers/7/access/me changes the share the Dashboard scales by`).toBe(true);
    });
});

describe('portfolio mutation listeners (page cache, phase 1)', () => {
    function listen(name: string) {
        const listener = vi.fn();
        const stop = registerPortfolioMutationListener(`portfolioMutation.test:${name}`, listener);
        onTestFinished(stop);
        return listener;
    }

    it('forwards the response to the classifier and tells listeners the kind of signal', () => {
        const listener = listen('forward');

        notify('POST', '/api/v1/assets/prices/sync', assetSyncAnswer([assetSyncResult(1, 0, 0)]));
        expect(listener, 'notifyPortfolioMutation does not hand the response to the classifier: a sync that wrote nothing reached the listeners').not.toHaveBeenCalled();

        notify('post', 'http://librefolio.local/api/v1/assets/prices/sync?x=1', assetSyncAnswer([assetSyncResult(1, 2, 0)]));
        expect(listener).toHaveBeenCalledTimes(1);
        expect(listener.mock.calls[0][0], 'a listener must be able to tell a mutation from a requested refresh').toMatchObject({method: 'POST', path: '/api/v1/assets/prices/sync', kind: 'mutation'});
    });

    it('requestPortfolioRefresh() calls every listener once with kind "refresh"', () => {
        const requestPortfolioRefresh = (portfolioMutation as unknown as {requestPortfolioRefresh?: () => void}).requestPortfolioRefresh;
        expect(typeof requestPortfolioRefresh, 'portfolioMutation exports no requestPortfolioRefresh(): «Aggiorna» has no way to mark report, risk and lots old at once').toBe('function');
        const first = listen('refresh-a');
        const second = listen('refresh-b');

        requestPortfolioRefresh!();

        expect(first).toHaveBeenCalledTimes(1);
        expect(second).toHaveBeenCalledTimes(1);
        expect(first.mock.calls[0][0]).toMatchObject({kind: 'refresh'});
        expect(second.mock.calls[0][0]).toMatchObject({kind: 'refresh'});
    });
});

/**
 * The price catch-up signal (workstream Z, lot Z-13).
 *
 * When the server has caught up on prices and updated something, `priceRefresh` (lot Z5) tells the portfolio views.
 * Until now it sent «Aggiorna»'s `{kind: 'refresh'}`: the caches turned stale, but no page on screen could tell that
 * signal from the one its own «Aggiorna» sends, so the open Dashboard kept the old figures until reloaded. The bus gets
 * a signal of its own, `notifyPricesCaughtUp()` → `{kind: 'prices'}`, dispatched like the others: to every listener,
 * once, a listener that throws keeping none of the others from hearing it. `requestPortfolioRefresh()` stays
 * `{kind: 'refresh'}`, and a write stays `{kind: 'mutation', …}`.
 *
 * Red first: `notifyPricesCaughtUp` is not exported yet. It is read by name from the module, so its absence fails each
 * case below with the contract in the message — not the whole file at import — and the type check of this file does
 * not depend on the export landing first.
 */
describe('the price catch-up signal (Z-13)', () => {
    function listen(name: string) {
        const listener = vi.fn();
        const stop = registerPortfolioMutationListener(`portfolioMutation.test:prices:${name}`, listener);
        onTestFinished(stop);
        return {listener, stop};
    }

    function pricesSignal(): () => void {
        const notifyPricesCaughtUp = (portfolioMutation as unknown as {notifyPricesCaughtUp?: () => void}).notifyPricesCaughtUp;
        expect(typeof notifyPricesCaughtUp, 'portfolioMutation exports no notifyPricesCaughtUp(): the end of a price catch-up can only send «Aggiorna»’s signal, and no page on screen can tell it apart to reload').toBe('function');
        return notifyPricesCaughtUp!;
    }

    function refreshSignal(): () => void {
        const requestPortfolioRefresh = (portfolioMutation as unknown as {requestPortfolioRefresh?: () => void}).requestPortfolioRefresh;
        expect(typeof requestPortfolioRefresh, 'portfolioMutation no longer exports requestPortfolioRefresh(): «Aggiorna» lost its signal').toBe('function');
        return requestPortfolioRefresh!;
    }

    it('notifyPricesCaughtUp() calls every listener once with exactly {kind: "prices"}', () => {
        const notifyPricesCaughtUp = pricesSignal();
        const first = listen('every-a').listener;
        const second = listen('every-b').listener;

        notifyPricesCaughtUp();

        expect(first).toHaveBeenCalledTimes(1);
        expect(second).toHaveBeenCalledTimes(1);
        expect(first.mock.calls[0][0], 'the price catch-up must arrive as {kind: "prices"} and nothing else: the pages reload on that kind, the stores mark stale on any').toEqual({kind: 'prices'});
        expect(second.mock.calls[0][0]).toEqual({kind: 'prices'});
    });

    it('keeps the three signals apart: «Aggiorna» stays refresh, the catch-up is prices, a write stays mutation', () => {
        const notifyPricesCaughtUp = pricesSignal();
        const requestPortfolioRefresh = refreshSignal();
        const {listener} = listen('kinds');

        requestPortfolioRefresh();
        notifyPricesCaughtUp();
        notify('POST', '/api/v1/transactions/commit');

        expect(
            listener.mock.calls.map(([signal]) => signal),
            'a page that reloads on the price catch-up must not reload on «Aggiorna» (which reloads by itself, forced) nor on a write: the three kinds must stay distinct',
        ).toEqual([{kind: 'refresh'}, {kind: 'prices'}, {kind: 'mutation', method: 'POST', path: '/api/v1/transactions/commit'}]);
    });

    it('a listener that throws on the price catch-up keeps none of the others from hearing it, and is reported', () => {
        const notifyPricesCaughtUp = pricesSignal();
        const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
        onTestFinished(() => consoleError.mockRestore());
        const before = listen('throws-before').listener;
        const failing = listen('throws').listener;
        failing.mockImplementation(() => {
            throw new Error('synthetic: a page listener failed');
        });
        const after = listen('throws-after').listener;

        expect(() => notifyPricesCaughtUp(), 'a failing listener made the signal throw: priceRefresh would end its check with an error').not.toThrow();

        expect(before).toHaveBeenCalledTimes(1);
        expect(failing).toHaveBeenCalledTimes(1);
        expect(after, 'a listener registered after the failing one never heard the price catch-up').toHaveBeenCalledTimes(1);
        expect(after.mock.calls[0][0]).toEqual({kind: 'prices'});
        expect(consoleError, 'the failure was swallowed without a trace').toHaveBeenCalled();
    });

    it('a listener removed before the signal does not hear it (a page destroyed before the catch-up ends)', () => {
        const notifyPricesCaughtUp = pricesSignal();
        const kept = listen('kept').listener;
        const removed = listen('removed');

        removed.stop();
        notifyPricesCaughtUp();

        expect(removed.listener, 'a removed listener still heard the price catch-up: a destroyed page would reload').not.toHaveBeenCalled();
        expect(kept, 'premise: the signal was sent').toHaveBeenCalledTimes(1);
    });
});

/**
 * The Δ columns' read (workstream X, lot X-R53, MF-P2).
 *
 * The Assets and FX lists stop computing their fixed-period changes (1D … 5Y) in the browser and ask the backend for
 * them on every load: `POST /assets/prices/period-changes` and `POST /fx/currencies/period-changes`. Both are reads — a
 * POST only because a bulk body does not fit in a query string — so neither may reach the listeners: counted as a
 * write, every visit to the Assets list would mark the Dashboard, Risk and lots answers stale and have them refreshed in
 * background, after a request that changed nothing.
 *
 * Red first: every POST under `/api/v1/assets/prices` but `/query` and `/sync` is a write today, so the asset read is
 * one, whatever its answer. The rest are guards, green before and after: the FX read already falls through every rule,
 * `/query` stays a read, and the writes under `/api/v1/assets/prices` stay writes — the exception must not widen into the
 * prefix rule.
 */
describe('the period changes are reads, not writes (X-R53)', () => {
    /** An answer of `POST /assets/prices/period-changes` (`FAPeriodChangesResponse`): one asset. */
    const assetAnswer = {items: [{asset_id: 6, as_of: '2026-10-16', currency: 'USD', periods: [{key: '1D', days: 1, change_ratio: '0.0125'}], errors: []}]};
    /** An answer of `POST /fx/currencies/period-changes` (`FXPeriodChangesResponse`): one pair. */
    const fxAnswer = {items: [{base: 'EUR', quote: 'USD', as_of: '2026-10-16', periods: [{key: '1D', days: 1, change_ratio: '0.0125', inverse_change_ratio: '-0.0123'}], errors: []}]};

    it.each([
        ['POST', '/api/v1/assets/prices/period-changes'],
        ['post', 'http://librefolio.local/api/v1/assets/prices/period-changes?x=1'],
        ['POST', '/api/v1/assets/prices/period-changes/'],
    ])('%s %s — the Assets list’s Δ columns — is not a portfolio mutation', (method, url) => {
        expect(classify(method, url, assetAnswer), `${method} ${url} reads the Δ columns of the Assets list: as a write, every visit to the list marks the Dashboard, Risk and lots answers stale`).toBe(false);
        expect(classify(method, url), 'nor without its answer: a read is a read whatever it answered').toBe(false);
    });

    it('no listener hears the Δ columns being read, while a write still reaches them', () => {
        const listener = vi.fn();
        onTestFinished(registerPortfolioMutationListener('portfolioMutation.test:period-changes', listener));

        notify('POST', '/api/v1/assets/prices/period-changes', assetAnswer);
        notify('POST', '/api/v1/fx/currencies/period-changes', fxAnswer);
        expect(listener, 'reading the Δ columns reached the listeners: every list load would refresh the Dashboard, Risk and lots answers').not.toHaveBeenCalled();

        // The control: the same listener hears a write of the same family, so the silence above is the rule's.
        notify('POST', '/api/v1/assets/prices', {results: [], success_count: 0, errors: []});
        expect(listener, 'premise: the listener is live').toHaveBeenCalledTimes(1);
        expect(listener.mock.calls[0][0]).toMatchObject({kind: 'mutation', method: 'POST', path: '/api/v1/assets/prices'});
    });

    it('guards: the FX read is no write either, /query stays a read, the writes under /api/v1/assets/prices stay writes', () => {
        expect(classify('POST', '/api/v1/fx/currencies/period-changes', fxAnswer), 'the FX list’s Δ columns').toBe(false);
        expect(classify('POST', '/api/v1/assets/prices/query'), 'the price read of the lists and the charts').toBe(false);
        expect(classify('POST', '/api/v1/assets/prices'), 'storing prices (the data editor’s save)').toBe(true);
        expect(classify('DELETE', '/api/v1/assets/prices'), 'deleting prices').toBe(true);
        expect(classify('POST', '/api/v1/assets/prices/current'), 'today’s live price, which writes today’s candle (E1)').toBe(true);
    });
});
