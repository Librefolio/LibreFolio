/**
 * lotsAnalysisStore — the FIFO lots analysis gets a session cache (page cache, phase 1, decision E5).
 *
 * Today `LotsAnalysisPanel` asks `POST /portfolio/lots/analysis` on every mount and every change of its
 * broker list: on the developer's path (Dashboard → Positions → «Analizza lotti» → asset → ‹ back) the
 * same analysis was asked three times on return. The store follows the rule of the page cache:
 *
 *   - one key per question — the user, the asset, the brokers, the currency, the analyses and the
 *     selected lots, the three lists in any order;
 *   - a fresh answer is served without asking, identical questions in flight share one request, a
 *     forced fetch («Aggiorna») asks again;
 *   - a portfolio mutation, or `requestPortfolioRefresh()`, marks the answers stale and keeps them:
 *     `peekLotsAnalysis(body)` still returns them, `{response, stale: true}`, so the panel shows them
 *     while the next fetch asks again and stores the fresh one;
 *   - a failed fetch rejects — the panel decides what a failure means — and the previous answer stays;
 *   - a session change forgets everything, and two users never share an entry.
 *
 * Red first: `lotsAnalysisStore.svelte.ts` does not exist yet. The module is loaded by a computed
 * specifier so that its absence fails each case with the contract in the message, rather than the
 * whole file at import, and so that the type check does not depend on the module landing first.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const lotsApi = vi.hoisted(() => vi.fn());

vi.mock('$lib/api', () => ({
    zodiosApi: {
        get_lots_analysis_api_v1_portfolio_lots_analysis_post: lotsApi,
    },
}));

import {transitionClientSession} from '$lib/stores/app/clientSession';
import * as portfolioMutation from '$lib/stores/portfolio/portfolioMutation';
import {notifyPortfolioMutation} from '$lib/stores/portfolio/portfolioMutation';

const STORE_MODULE = './lotsAnalysisStore.svelte';

interface LotsBody {
    asset_id: number;
    broker_ids?: number[];
    target_currency: string;
    requested_analyses: string[];
    selected_lot_ids?: number[];
}

interface LotsStore {
    fetchLotsAnalysis: (body: LotsBody, force?: boolean) => Promise<unknown>;
    peekLotsAnalysis: (body: LotsBody) => {response: unknown; stale: boolean} | null;
}

async function loadStore(): Promise<LotsStore> {
    let module: Record<string, unknown>;
    try {
        module = (await import(/* @vite-ignore */ STORE_MODULE)) as Record<string, unknown>;
    } catch (error) {
        throw new Error(`src/lib/stores/portfolio/lotsAnalysisStore.svelte.ts does not exist yet: the lots panel has no cache, so every return to the Dashboard asks for the analysis again (${String(error)})`);
    }
    for (const name of ['fetchLotsAnalysis', 'peekLotsAnalysis']) {
        expect(typeof module[name], `lotsAnalysisStore exports no ${name}()`).toBe('function');
    }
    return module as unknown as LotsStore;
}

/** What `LotsAnalysisPanel.loadMain` asks. */
const MAIN: LotsBody = {
    asset_id: 6,
    broker_ids: [1, 5],
    target_currency: 'EUR',
    requested_analyses: ['LOT_SUMMARY', 'GANTT_TOPOLOGY', 'EVENT_HISTORY', 'PRICE_HISTORY', 'BROKER_WAC_HISTORY', 'CUMULATIVE_WAC_HISTORY', 'INCOME_EVENTS'],
};

/** What `LotsAnalysisPanel.loadSelectionHistories` asks. */
const SELECTION: LotsBody = {
    asset_id: 6,
    broker_ids: [1, 5],
    target_currency: 'EUR',
    selected_lot_ids: [11, 12],
    requested_analyses: ['VALUE_HISTORY', 'RETURN_HISTORY'],
};

function answer(marker: string) {
    return {asset_id: 6, target_currency: 'EUR', quote_base_quantity: 1, calculation_status: 'OK', marker, lots: [{lot_id: 11}, {lot_id: 12}]};
}

/** The question a body asks, with its three unordered lists sorted. */
function question(body: LotsBody) {
    const sorted = <T>(values: readonly T[] | undefined) => (values === undefined ? undefined : [...values].sort());
    return {...body, broker_ids: sorted(body.broker_ids), requested_analyses: sorted(body.requested_analyses), selected_lot_ids: sorted(body.selected_lot_ids)};
}

function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void} {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((settle) => {
        resolve = settle;
    });
    return {promise, resolve};
}

const MUTATION = ['POST', '/api/v1/transactions/commit'] as const;

let nextUser = 700;

describe('lotsAnalysisStore (page cache, phase 1)', () => {
    beforeEach(() => {
        lotsApi.mockReset();
        // A fresh account per case: a session change clears the store, and the key carries the user.
        transitionClientSession(null);
        transitionClientSession(++nextUser);
    });

    it('asks the generated client with the question, serves it again from the cache, and asks again when forced', async () => {
        const store = await loadStore();
        lotsApi.mockResolvedValueOnce(answer('first'));

        expect(store.peekLotsAnalysis(MAIN), 'nothing was asked yet').toBeNull();
        expect(await store.fetchLotsAnalysis(MAIN)).toMatchObject(answer('first'));
        expect(lotsApi).toHaveBeenCalledTimes(1);
        expect(question(lotsApi.mock.calls[0][0] as LotsBody), 'the request is not the question the panel asked').toEqual(question(MAIN));

        expect(await store.fetchLotsAnalysis({...MAIN})).toMatchObject(answer('first'));
        expect(lotsApi, 'a fresh answer was asked again').toHaveBeenCalledTimes(1);
        expect(store.peekLotsAnalysis(MAIN)).toMatchObject({response: answer('first'), stale: false});

        lotsApi.mockResolvedValueOnce(answer('forced'));
        expect(await store.fetchLotsAnalysis(MAIN, true), '«Aggiorna» forces: the answer is asked again').toMatchObject(answer('forced'));
        expect(lotsApi).toHaveBeenCalledTimes(2);
        expect(store.peekLotsAnalysis(MAIN)).toMatchObject({response: answer('forced'), stale: false});
    });

    it('shares one key between bodies that differ only in the order of broker_ids, requested_analyses or selected_lot_ids, and no other', async () => {
        const store = await loadStore();
        lotsApi.mockResolvedValue(answer('selection'));
        await store.fetchLotsAnalysis(SELECTION);

        const reordered = {...SELECTION, broker_ids: [5, 1], requested_analyses: ['RETURN_HISTORY', 'VALUE_HISTORY'], selected_lot_ids: [12, 11]};
        expect(store.peekLotsAnalysis(reordered), 'the order of the lists made a new key').toMatchObject({response: answer('selection'), stale: false});
        await store.fetchLotsAnalysis(reordered);
        expect(lotsApi, 'the same question in another order was asked again').toHaveBeenCalledTimes(1);

        const others: LotsBody[] = [
            {...SELECTION, asset_id: 7},
            {...SELECTION, broker_ids: [1]},
            {...SELECTION, target_currency: 'USD'},
            {...SELECTION, selected_lot_ids: [11]},
            {...SELECTION, requested_analyses: ['VALUE_HISTORY']},
        ];
        for (const other of others) {
            expect(store.peekLotsAnalysis(other), `${JSON.stringify(other)} shares the key of another question`).toBeNull();
            await store.fetchLotsAnalysis(other);
        }
        expect(lotsApi, 'two different questions shared one cached answer').toHaveBeenCalledTimes(1 + others.length);
    });

    it('shares one request between identical questions asked at once', async () => {
        const store = await loadStore();
        const pending = deferred<unknown>();
        lotsApi.mockImplementationOnce(() => pending.promise);

        const first = store.fetchLotsAnalysis(MAIN);
        const second = store.fetchLotsAnalysis({...MAIN, broker_ids: [5, 1]});
        pending.resolve(answer('shared'));

        expect(await first).toMatchObject(answer('shared'));
        expect(await second).toMatchObject(answer('shared'));
        expect(lotsApi, 'a question asked while the same one was in flight sent a request of its own').toHaveBeenCalledTimes(1);
    });

    it('marks the answers stale on a portfolio mutation and keeps them; the next fetch asks again, once, and stores the fresh answer', async () => {
        const store = await loadStore();
        lotsApi.mockResolvedValueOnce(answer('old'));
        await store.fetchLotsAnalysis(MAIN);

        notifyPortfolioMutation(...MUTATION);
        expect(store.peekLotsAnalysis(MAIN), 'a portfolio mutation threw the analysis away, or did not mark it stale').toMatchObject({response: answer('old'), stale: true});
        expect(lotsApi, 'a mark must not ask anything by itself').toHaveBeenCalledTimes(1);

        const fresh = deferred<unknown>();
        lotsApi.mockImplementationOnce(() => fresh.promise);
        const refreshing = store.fetchLotsAnalysis(MAIN);
        const joining = store.fetchLotsAnalysis(MAIN);
        await vi.waitFor(() => expect(lotsApi, 'a stale answer was not asked again').toHaveBeenCalledTimes(2));
        expect(store.peekLotsAnalysis(MAIN), 'the old answer is what the panel shows while the refresh is in flight').toMatchObject({response: answer('old'), stale: true});

        fresh.resolve(answer('new'));
        expect(await refreshing).toMatchObject(answer('new'));
        expect(await joining).toMatchObject(answer('new'));
        expect(lotsApi, 'two callers of one stale question sent two requests').toHaveBeenCalledTimes(2);
        expect(store.peekLotsAnalysis(MAIN)).toMatchObject({response: answer('new'), stale: false});
    });

    it('marks the answers stale on requestPortfolioRefresh() as well', async () => {
        const store = await loadStore();
        const requestPortfolioRefresh = (portfolioMutation as unknown as {requestPortfolioRefresh?: () => void}).requestPortfolioRefresh;
        expect(typeof requestPortfolioRefresh, 'portfolioMutation exports no requestPortfolioRefresh(): «Aggiorna» cannot reach the lots').toBe('function');
        lotsApi.mockResolvedValueOnce(answer('old'));
        await store.fetchLotsAnalysis(SELECTION);

        requestPortfolioRefresh!();

        expect(store.peekLotsAnalysis(SELECTION), '«Aggiorna» did not mark the lots analysis stale, or threw it away').toMatchObject({response: answer('old'), stale: true});
    });

    it('rejects when the refresh fails, keeps the previous answer stale, and asks again next time', async () => {
        const store = await loadStore();
        lotsApi.mockResolvedValueOnce(answer('old'));
        await store.fetchLotsAnalysis(MAIN);
        notifyPortfolioMutation(...MUTATION);

        const failure = new Error('synthetic: lots engine unreachable');
        lotsApi.mockRejectedValueOnce(failure);
        await expect(store.fetchLotsAnalysis(MAIN), 'a failed request must reach the panel, which decides what it means').rejects.toBe(failure);
        expect(store.peekLotsAnalysis(MAIN), 'a failed refresh emptied the cache: the panel would trade the old lots for an error').toMatchObject({response: answer('old'), stale: true});

        lotsApi.mockResolvedValueOnce(answer('recovered'));
        expect(await store.fetchLotsAnalysis(MAIN), 'the failure was remembered: the same question did not ask again').toMatchObject(answer('recovered'));
        expect(lotsApi).toHaveBeenCalledTimes(3);
    });

    it('forgets everything on a session change: the next account, and the same one back, find nothing', async () => {
        const store = await loadStore();
        const userId = nextUser;
        lotsApi.mockResolvedValueOnce(answer(`user ${userId}`));
        await store.fetchLotsAnalysis(MAIN);

        transitionClientSession(null);
        expect(store.peekLotsAnalysis(MAIN)).toBeNull();
        transitionClientSession(++nextUser);
        expect(store.peekLotsAnalysis(MAIN), 'another account read an analysis it never asked for').toBeNull();
        lotsApi.mockResolvedValueOnce(answer(`user ${nextUser}`));
        expect(await store.fetchLotsAnalysis(MAIN)).toMatchObject(answer(`user ${nextUser}`));
        expect(lotsApi).toHaveBeenCalledTimes(2);

        transitionClientSession(null);
        transitionClientSession(userId);
        expect(store.peekLotsAnalysis(MAIN), 'a logout only marked the analysis stale: a session change must forget it').toBeNull();
    });
});

/**
 * The first identity resolution moves the session without running any resetter (see
 * `clientSession.transition`): a page reloaded on the Dashboard can ask before `/auth/me` answers.
 * Only the key keeps that answer from the account that resolves next. Module state of its own.
 */
describe('lotsAnalysisStore — first identity resolution', () => {
    it('keys every answer by the session user, so an answer asked before the identity resolved is not served to the account', async () => {
        vi.resetModules();
        lotsApi.mockReset();
        const {transitionClientSession: freshTransition} = await import('$lib/stores/app/clientSession');
        const store = await loadStore();

        lotsApi.mockResolvedValueOnce(answer('anonymous'));
        await store.fetchLotsAnalysis(MAIN);
        expect(store.peekLotsAnalysis(MAIN), 'precondition: the answer is cached').toMatchObject({stale: false});

        freshTransition(801);

        expect(store.peekLotsAnalysis(MAIN), 'the key does not carry the session user: an answer asked for nobody is served to the account').toBeNull();
        lotsApi.mockResolvedValueOnce(answer('user 801'));
        expect(await store.fetchLotsAnalysis(MAIN)).toMatchObject(answer('user 801'));
        expect(lotsApi).toHaveBeenCalledTimes(2);
    });
});
