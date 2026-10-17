/**
 * livePriceService — the live prices of the Assets pages, and the outcome a live poll hands back to its poller (Z1;
 * Z7c-1, decision 34, D-Z7-1, D-Z7-2; X-R64).
 *
 * The contract under test:
 *   - `toLivePriceResult(raw)` maps one item of `POST /api/v1/assets/prices/current` (`FACurrentPriceItem`) into exactly
 *     seven keys: `asset_id` → `assetId`; `value` parsed (`parseFloat`), else null; `currency`, else ''; `source`,
 *     `error` and `error_code` (→ `errorCode`), else null; `retry_after` (→ `retryAfter`) when it is a finite number,
 *     else null;
 *   - `fetchCurrentPrices(ids)` posts the ids, as they are, to that path through `axiosInstance` of `$lib/api`, and maps
 *     every item with `toLivePriceResult`, in the order answered; `[]` asks nothing and answers `[]`; an answer without
 *     `results` is `[]`; a refusal reaches the caller as axios raised it — the page hands it to `livePollFailure`. At most
 *     1,000 ids a request (lot X-R64: since R13-SEC9-1 the endpoint refuses more than the backend's `MAX_BULK_ITEMS`,
 *     1,000, with a 422 `bulk_too_many_items`): a longer list goes as consecutive requests in its order, each sent once
 *     the one before answered (Z-27's `sendBulkBatches`), their items mapped batch after batch, as if one request had
 *     answered; up to 1,000 ids go as one request, as before. A refusal stops the sending — no request after it, no
 *     partial result — and reaches the caller unchanged, its `Retry-After` included;
 *   - `livePollOutcome(results, now)`: `{ok: true}` — no `notBefore` key — unless every result is `RATE_LIMITED`; then
 *     `{ok: true, notBefore: now + min(retryAfter) × 1000}` when every one of them carries a finite `retryAfter ≥ 0`,
 *     else `{ok: false}`, so that the poller doubles its wait. With providers of both kinds the list goes on: the
 *     backend calls none of the paused ones, so a poll costs little;
 *   - `livePollFailure(error, now)`: always `ok: false`; a `notBefore` only for a 429 or a 503 whose `Retry-After` is
 *     usable — delta-seconds, also with a fraction, → `now + s × 1000`; an HTTP-date still ahead → that instant — read
 *     with `AxiosHeaders.get` (any casing) or from a plain object under `retry-after`. Anything else is `{ok: false}`;
 *   - `computeDirection(current, previous)`, which no other test covers.
 *
 * Transport. `$lib/api` is mocked with an axios instance of its own, so the service runs on real axios — the body
 * serialized, the answer settled, the `AxiosError` raised, the response headers turned into `AxiosHeaders` — and each
 * test fakes only the adapter. Before every test an adapter is installed that records the request and refuses it: no
 * test can reach a network, and a request nobody expected is seen.
 *
 * Time. `now` is injected wherever it is a parameter, as one fixed instant; the default (`Date.now()`) has one case per
 * function, on a spied clock.
 *
 * Red today (X-R64): LPS-14 and LPS-16 — the service posts every id in one request, where they expect two; LPS-15, one
 * request for exactly 1,000 ids, is their guard, green today.
 *
 * Node environment: nothing here renders.
 */
import {AxiosError, AxiosHeaders, type AxiosAdapter, type AxiosResponse, type InternalAxiosRequestConfig} from 'axios';
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', async () => {
    const {default: axios} = await import('axios');
    return {axiosInstance: axios.create()};
});

import {axiosInstance} from '$lib/api';
import {computeDirection, fetchCurrentPrices, livePollFailure, livePollOutcome, toLivePriceResult, type LivePriceDirection, type LivePriceResult} from './livePriceService';

/** A fixed instant, Friday 16/10/2026 04:00:00 UTC: every expected `notBefore` is an offset from it. */
const NOW = Date.UTC(2026, 9, 16, 4, 0, 0);
const PATH = '/api/v1/assets/prices/current';

/** An HTTP-date (IMF-fixdate), as a server writes it in `Retry-After`. */
function httpDate(at: number): string {
    return new Date(at).toUTCString();
}

/** One item as the endpoint answers it for an asset whose provider answered. */
function quoted(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {asset_id: 7, value: '142.50', currency: 'USD', as_of_date: '2026-10-16', source: 'provider:yfinance', error: null, error_code: null, retry_after: null, ...overrides};
}

/** One item as the endpoint answers it while the provider is paused: HTTP 200, the last stored price, RATE_LIMITED, the seconds left (X5, D-Z7-2). */
function paused(assetId: number, retryAfter: unknown): Record<string, unknown> {
    return {asset_id: assetId, value: '98.32', currency: 'EUR', as_of_date: '2026-10-15', source: 'db:last_known', error: null, error_code: 'RATE_LIMITED', retry_after: retryAfter};
}

/** A result as the service hands it to the page. */
function result(overrides: Partial<LivePriceResult> = {}): LivePriceResult {
    return {assetId: 1, value: 100, currency: 'EUR', source: 'provider:yfinance', error: null, errorCode: null, retryAfter: null, ...overrides};
}

/** A result whose provider is paused. */
function pausedResult(assetId: number, retryAfter: number | null): LivePriceResult {
    return result({assetId, value: 98.32, source: 'db:last_known', errorCode: 'RATE_LIMITED', retryAfter});
}

/** The config axios attaches to an error raised outside a request. */
const REQUEST = {headers: new AxiosHeaders()} as InternalAxiosRequestConfig;

/** What axios rejects with when the server answers `status` (lib/core/settle.js): an AxiosError carrying the response. */
function refusal(status: number, headers: AxiosResponse['headers'], config: InternalAxiosRequestConfig = REQUEST, data: unknown = {detail: 'refused'}): AxiosError {
    const response: AxiosResponse = {status, statusText: '', headers, config, request: {}, data};
    return new AxiosError(`Request failed with status code ${status}`, status < 500 ? AxiosError.ERR_BAD_REQUEST : AxiosError.ERR_BAD_RESPONSE, config, {}, response);
}

/** The requests the fake transport received. */
const received: InternalAxiosRequestConfig[] = [];

/** The server answers `status` with `data` and these headers, settled as axios's own adapters settle it: a 2xx resolves, anything else rejects. */
function serverAnswers(status: number, data: unknown, headers: Record<string, string> = {}): void {
    const adapter: AxiosAdapter = async (config) => {
        received.push(config);
        const all = {'content-type': 'application/json', ...headers};
        if (status >= 200 && status < 300) return {status, statusText: 'OK', headers: all, config, request: {}, data};
        throw refusal(status, all, config, data);
    };
    axiosInstance.defaults.adapter = adapter;
}

/** No server answers: the request fails before any response. */
function noServer(): void {
    const adapter: AxiosAdapter = async (config) => {
        received.push(config);
        throw new AxiosError('Network Error', AxiosError.ERR_NETWORK, config, {});
    };
    axiosInstance.defaults.adapter = adapter;
}

/** `count` asset ids in a list's order, which is not theirs: `count` down to 1, so a request out of order, or a list sorted on the way, shows. */
function assetIds(count: number): number[] {
    return Array.from({length: count}, (_, index) => count - index);
}

/**
 * The server answers each request from its own body, as the endpoint does: one item per id, in the order sent, asset `n`
 * quoted at `n.5` USD. With `refuse`, the request numbered `refuse.request` (from 1, in the order received) is refused
 * instead, with that status and those headers, settled as axios's own adapters settle it. `raised` holds what the server
 * raised: the very errors a caller must see.
 */
function serverAnswersEach(refuse?: {request: number; status: number; headers: Record<string, string>; data: unknown}): {raised: unknown[]} {
    const raised: unknown[] = [];
    const adapter: AxiosAdapter = async (config) => {
        received.push(config);
        if (refuse !== undefined && received.length === refuse.request) {
            const error = refusal(refuse.status, {'content-type': 'application/json', ...refuse.headers}, config, refuse.data);
            raised.push(error);
            throw error;
        }
        const ids = JSON.parse(String(config.data)) as number[];
        const data = {results: ids.map((id) => quoted({asset_id: id, value: `${id}.5`})), success_count: ids.length, errors: []};
        return {status: 200, statusText: 'OK', headers: {'content-type': 'application/json'}, config, request: {}, data};
    };
    axiosInstance.defaults.adapter = adapter;
    return {raised};
}

/** The result of asset `n` as `serverAnswersEach` quotes it, once mapped. */
function quotedResult(assetId: number): LivePriceResult {
    return result({assetId, value: assetId + 0.5, currency: 'USD'});
}

/** The requests received, in order: each as `method url` and the number of ids it carried. */
function requestsReceived(): Array<{request: string; ids: number}> {
    return received.map((config) => ({request: `${config.method} ${config.url}`, ids: (JSON.parse(String(config.data)) as unknown[]).length}));
}

/** Every id the requests carried, the requests joined in the order received. */
function idsReceived(): number[] {
    return received.flatMap((config) => JSON.parse(String(config.data)) as number[]);
}

beforeEach(() => {
    received.length = 0;
    const unexpected: AxiosAdapter = async (config) => {
        received.push(config);
        throw new Error(`no transport was faked for ${config.method} ${config.url}`);
    };
    axiosInstance.defaults.adapter = unexpected;
});

afterEach(() => {
    vi.restoreAllMocks();
});

// =====================================================================================================================
describe('toLivePriceResult — one item of the API as the page reads it', () => {
    it('LPS-01: a price a provider answered — every field, the two of the pause null', () => {
        expect(toLivePriceResult(quoted())).toStrictEqual({assetId: 7, value: 142.5, currency: 'USD', source: 'provider:yfinance', error: null, errorCode: null, retryAfter: null});
    });

    it('LPS-02: a paused provider — the last stored price, RATE_LIMITED and the seconds of the pause', () => {
        expect(toLivePriceResult(paused(3, 300))).toStrictEqual({assetId: 3, value: 98.32, currency: 'EUR', source: 'db:last_known', error: null, errorCode: 'RATE_LIMITED', retryAfter: 300});
    });

    it('LPS-03: what an item leaves out — no value, no currency, no source, no error, no pause', () => {
        expect(toLivePriceResult({asset_id: 9})).toStrictEqual({assetId: 9, value: null, currency: '', source: null, error: null, errorCode: null, retryAfter: null});
    });

    it('LPS-04: what an item sends as null — a paused provider with no stored price', () => {
        const item = {asset_id: 9, value: null, currency: null, as_of_date: null, source: null, error: 'No price data available', error_code: 'RATE_LIMITED', retry_after: null};
        expect(toLivePriceResult(item)).toStrictEqual({assetId: 9, value: null, currency: '', source: null, error: 'No price data available', errorCode: 'RATE_LIMITED', retryAfter: null});
    });

    it('LPS-05: a price of zero is a price', () => {
        expect(toLivePriceResult(quoted({value: '0'})).value).toBe(0);
    });

    it.each<[string, unknown, number | null]>([
        ['a whole number', 300, 300],
        ['a fraction', 12.5, 12.5],
        ['zero', 0, 0],
        ['null', null, null],
        ['NaN', Number.NaN, null],
        ['Infinity', Number.POSITIVE_INFINITY, null],
    ])('LPS-06: retry_after %s → retryAfter', (_label, retryAfter, expected) => {
        expect(toLivePriceResult(paused(3, retryAfter)).retryAfter).toBe(expected);
    });

    it('LPS-07: retry_after absent → retryAfter null', () => {
        expect(toLivePriceResult({asset_id: 3, value: '98.32', currency: 'EUR', source: 'db:last_known', error_code: 'RATE_LIMITED'}).retryAfter).toBeNull();
    });
});

// =====================================================================================================================
describe('fetchCurrentPrices — POST /api/v1/assets/prices/current through axios, only the transport faked', () => {
    it('LPS-10: posts the ids as they are, and maps every item in the order answered, the fields of the pause included', async () => {
        serverAnswers(200, {results: [quoted({asset_id: 4}), paused(2, 300)], success_count: 2, errors: []});

        await expect(fetchCurrentPrices([4, 2])).resolves.toStrictEqual([
            {assetId: 4, value: 142.5, currency: 'USD', source: 'provider:yfinance', error: null, errorCode: null, retryAfter: null},
            {assetId: 2, value: 98.32, currency: 'EUR', source: 'db:last_known', error: null, errorCode: 'RATE_LIMITED', retryAfter: 300},
        ]);
        expect(received.map(({method, url}) => `${method} ${url}`)).toEqual([`post ${PATH}`]);
        expect(JSON.parse(String(received[0].data))).toEqual([4, 2]);
    });

    it('LPS-11: asks nothing for no asset', async () => {
        await expect(fetchCurrentPrices([])).resolves.toEqual([]);
        expect(received).toHaveLength(0);
    });

    it('LPS-12: an answer without results is no result', async () => {
        serverAnswers(200, {success_count: 0});

        await expect(fetchCurrentPrices([1])).resolves.toEqual([]);
    });

    it('LPS-13: lets a refusal through as axios raised it, for the page to read', async () => {
        serverAnswers(429, {detail: 'Too Many Requests'}, {'retry-after': '120'});

        const refused = await fetchCurrentPrices([1]).then(
            () => null,
            (error: unknown) => error,
        );
        expect(refused).toBeInstanceOf(AxiosError);
        expect((refused as AxiosError).response?.status).toBe(429);
    });

    it('LPS-14: posts 1,001 ids as two requests, 1,000 then 1, in the order given, and maps the results of both in that order', async () => {
        const ids = assetIds(1_001);
        serverAnswersEach();

        const results = await fetchCurrentPrices(ids);

        expect(requestsReceived(), 'at most 1,000 ids a request: the endpoint refuses one more (422 bulk_too_many_items, R13-SEC9-1)').toEqual([
            {request: `post ${PATH}`, ids: 1_000},
            {request: `post ${PATH}`, ids: 1},
        ]);
        expect(idsReceived(), 'consecutive requests: the ids as they are, each once, in the order given').toEqual(ids);
        expect(results, 'every item mapped, batch after batch, as if one request had answered').toStrictEqual(ids.map(quotedResult));
    });

    it('LPS-15: posts exactly 1,000 ids as one request, as before (a guard, green today)', async () => {
        const ids = assetIds(1_000);
        serverAnswersEach();

        await expect(fetchCurrentPrices(ids)).resolves.toStrictEqual(ids.map(quotedResult));
        expect(requestsReceived(), 'the endpoint takes 1,000 ids').toEqual([{request: `post ${PATH}`, ids: 1_000}]);
        expect(idsReceived()).toEqual(ids);
    });

    it('LPS-16: a refusal of the second request — a 429 with Retry-After — reaches the caller unchanged: the first request went, none after it', async () => {
        const ids = assetIds(2_500);
        const server = serverAnswersEach({request: 2, status: 429, headers: {'retry-after': '120'}, data: {detail: 'Too Many Requests'}});

        const refused = await fetchCurrentPrices(ids).then(
            () => null,
            (error: unknown) => error,
        );

        expect(requestsReceived(), 'the first request answered, the second refused, the third never sent').toEqual([
            {request: `post ${PATH}`, ids: 1_000},
            {request: `post ${PATH}`, ids: 1_000},
        ]);
        expect(refused, 'the very error axios raised for the second request: no partial result, nothing wrapped').toBe(server.raised[0]);
        expect((refused as AxiosError).response?.status).toBe(429);
        expect(livePollFailure(refused, NOW), 'its Retry-After, still read by the live poller').toStrictEqual({ok: false, notBefore: NOW + 120_000});
    });
});

// =====================================================================================================================
describe('livePollOutcome — a notBefore only when every asset asked about is paused', () => {
    it('LPS-20: no result → {ok: true}, with no notBefore key', () => {
        expect(livePollOutcome([], NOW)).toStrictEqual({ok: true});
    });

    it.each<{label: string; results: LivePriceResult[]}>([
        {label: 'one price', results: [result()]},
        {label: 'a paused provider beside one that answered', results: [pausedResult(1, 300), result({assetId: 2})]},
        {label: 'a paused provider beside an asset with no price at all', results: [pausedResult(1, 300), result({assetId: 2, value: null, currency: '', source: null, error: 'No price data available'})]},
        {label: 'a paused provider beside another error code', results: [pausedResult(1, 300), result({assetId: 2, value: null, error: 'Provider failed', errorCode: 'PROVIDER_ERROR'})]},
    ])('LPS-21: $label → {ok: true}: the list goes on', ({results}) => {
        expect(livePollOutcome(results, NOW)).toStrictEqual({ok: true});
    });

    it.each<{label: string; results: LivePriceResult[]; notBefore: number}>([
        {label: 'one asset paused for 300 s', results: [pausedResult(1, 300)], notBefore: NOW + 300_000},
        {label: 'the shortest of three pauses', results: [pausedResult(1, 300), pausedResult(2, 120.5), pausedResult(3, 600)], notBefore: NOW + 120_500},
        {label: 'a pause that ends now', results: [pausedResult(1, 0), pausedResult(2, 60)], notBefore: NOW},
        {label: 'an asset paused with no stored price', results: [result({assetId: 1, value: null, currency: '', source: null, error: 'No price data available', errorCode: 'RATE_LIMITED', retryAfter: 90})], notBefore: NOW + 90_000},
    ])('LPS-22: every asset RATE_LIMITED, $label → {ok: true, notBefore: now + the shortest pause}', ({results, notBefore}) => {
        expect(livePollOutcome(results, NOW)).toStrictEqual({ok: true, notBefore});
    });

    it.each<{label: string; results: LivePriceResult[]}>([
        {label: 'one of them without retryAfter', results: [pausedResult(1, 300), pausedResult(2, null)]},
        {label: 'a negative retryAfter', results: [pausedResult(1, -1)]},
        {label: 'a NaN retryAfter', results: [pausedResult(1, Number.NaN)]},
        {label: 'an infinite retryAfter', results: [pausedResult(1, Number.POSITIVE_INFINITY), pausedResult(2, 300)]},
    ])('LPS-23: every asset RATE_LIMITED but $label → {ok: false}: the poller doubles its wait', ({results}) => {
        expect(livePollOutcome(results, NOW)).toStrictEqual({ok: false});
    });

    it('LPS-24: takes Date.now() when now is not given', () => {
        vi.spyOn(Date, 'now').mockReturnValue(NOW);

        expect(livePollOutcome([pausedResult(1, 300)])).toStrictEqual({ok: true, notBefore: NOW + 300_000});
    });
});

// =====================================================================================================================
describe('livePollFailure — never a success; a notBefore only from a usable Retry-After on a 429 or a 503', () => {
    /** Every form of `Retry-After` the contract names, and the notBefore it gives at NOW. */
    const RETRY_AFTER: Array<{label: string; value: string; notBefore: number | null}> = [
        {label: 'delta-seconds', value: '120', notBefore: NOW + 120_000},
        {label: 'delta-seconds with a fraction (lenient)', value: '1.5', notBefore: NOW + 1_500},
        {label: 'zero seconds', value: '0', notBefore: NOW},
        {label: 'an HTTP-date five minutes ahead', value: httpDate(NOW + 300_000), notBefore: NOW + 300_000},
        {label: 'an HTTP-date in the past', value: httpDate(NOW - 60_000), notBefore: null},
        {label: 'negative seconds', value: '-5', notBefore: null},
        {label: 'garbage', value: 'soon', notBefore: null},
    ];

    function outcomeFor(notBefore: number | null) {
        return notBefore === null ? {ok: false} : {ok: false, notBefore};
    }

    it.each(RETRY_AFTER)('LPS-30: 429 with Retry-After $label, read through AxiosHeaders in any casing', ({value, notBefore}) => {
        expect(livePollFailure(refusal(429, new AxiosHeaders({'Retry-After': value})), NOW)).toStrictEqual(outcomeFor(notBefore));
    });

    it.each(RETRY_AFTER)('LPS-31: 503 with Retry-After $label, read from a plain object under retry-after', ({value, notBefore}) => {
        expect(livePollFailure(refusal(503, {'retry-after': value}), NOW)).toStrictEqual(outcomeFor(notBefore));
    });

    it.each([500, 502, 504, 400, 404])('LPS-32: %i with a usable Retry-After → {ok: false}: only a 429 or a 503 speaks of a pause', (status) => {
        expect(livePollFailure(refusal(status, new AxiosHeaders({'Retry-After': '120'})), NOW)).toStrictEqual({ok: false});
        expect(livePollFailure(refusal(status, {'retry-after': '120'}), NOW)).toStrictEqual({ok: false});
    });

    it.each([429, 503])('LPS-33: %i without Retry-After → {ok: false}', (status) => {
        expect(livePollFailure(refusal(status, new AxiosHeaders()), NOW)).toStrictEqual({ok: false});
        expect(livePollFailure(refusal(status, {}), NOW)).toStrictEqual({ok: false});
    });

    it('LPS-34: a request that got no answer → {ok: false}', () => {
        expect(livePollFailure(new AxiosError('Network Error', AxiosError.ERR_NETWORK, REQUEST, {}), NOW)).toStrictEqual({ok: false});
        expect(livePollFailure(new AxiosError('timeout of 30000ms exceeded', AxiosError.ECONNABORTED, REQUEST, {}), NOW)).toStrictEqual({ok: false});
    });

    it.each<[string, unknown]>([
        ['an Error', new Error('boom')],
        ['a string', 'boom'],
        ['a number', 429],
        ['null', null],
        ['undefined', undefined],
        ['an object with a status but no response', {status: 429, headers: {'retry-after': '120'}}],
        ['a response without headers', {response: {status: 429}}],
    ])('LPS-35: %s → {ok: false}, without throwing', (_label, error) => {
        expect(livePollFailure(error, NOW)).toStrictEqual({ok: false});
    });

    it('LPS-36: takes Date.now() when now is not given', () => {
        vi.spyOn(Date, 'now').mockReturnValue(NOW);

        expect(livePollFailure(refusal(429, new AxiosHeaders({'Retry-After': '120'})))).toStrictEqual({ok: false, notBefore: NOW + 120_000});
    });
});

// =====================================================================================================================
describe('the two pages, through axios: what a live poll answers becomes the outcome its poller reads', () => {
    /** What the asset list's `fetchLivePrices` does with one poll: its results, or its refusal, into an outcome. */
    function listPoll(ids: number[]) {
        return fetchCurrentPrices(ids).then(
            (results) => livePollOutcome(results, NOW),
            (error: unknown) => livePollFailure(error, NOW),
        );
    }

    it('LPS-40: every asset paused for 300 s → {ok: true, notBefore: now + 300 s}', async () => {
        serverAnswers(200, {results: [paused(1, 300), paused(2, 300)], success_count: 2, errors: []});

        await expect(listPoll([1, 2])).resolves.toStrictEqual({ok: true, notBefore: NOW + 300_000});
    });

    it('LPS-41: one asset paused, one answered → {ok: true}', async () => {
        serverAnswers(200, {results: [paused(1, 300), quoted({asset_id: 2})], success_count: 2, errors: []});

        await expect(listPoll([1, 2])).resolves.toStrictEqual({ok: true});
    });

    it('LPS-42: a 429 with Retry-After: 120 → {ok: false, notBefore: now + 120 s}', async () => {
        serverAnswers(429, {detail: 'Too Many Requests'}, {'retry-after': '120'});

        await expect(listPoll([1])).resolves.toStrictEqual({ok: false, notBefore: NOW + 120_000});
    });

    it('LPS-43: a 503 with a Retry-After date five minutes ahead → that instant', async () => {
        serverAnswers(503, {detail: 'Service Unavailable'}, {'retry-after': httpDate(NOW + 300_000)});

        await expect(listPoll([1])).resolves.toStrictEqual({ok: false, notBefore: NOW + 300_000});
    });

    it('LPS-44: a 500, even with a Retry-After → {ok: false}', async () => {
        serverAnswers(500, {detail: 'Internal Server Error'}, {'retry-after': '120'});

        await expect(listPoll([1])).resolves.toStrictEqual({ok: false});
    });

    it('LPS-45: no answer at all → {ok: false}', async () => {
        noServer();

        await expect(listPoll([1])).resolves.toStrictEqual({ok: false});
    });

    it('LPS-46: the asset page reads its one item the same way — paused → its notBefore; no item → {ok: true}', () => {
        expect(livePollOutcome([toLivePriceResult(paused(5, 45))], NOW)).toStrictEqual({ok: true, notBefore: NOW + 45_000});
        expect(livePollOutcome([toLivePriceResult(quoted({asset_id: 5}))], NOW)).toStrictEqual({ok: true});
        expect(livePollOutcome([], NOW)).toStrictEqual({ok: true});
    });
});

// =====================================================================================================================
describe('computeDirection — the tick of a live price against the previous one', () => {
    it.each<[number | null, number | null, LivePriceDirection]>([
        [101, 100, 'up'],
        [99, 100, 'down'],
        [100, 100, 'neutral'],
        [0, 1, 'down'],
        [1, 0, 'up'],
        [100, null, 'neutral'],
        [null, 100, 'neutral'],
        [null, null, 'neutral'],
    ])('LPS-50: %s against a previous %s → %s', (current, previous, direction) => {
        expect(computeDirection(current, previous)).toBe(direction);
    });
});
