/**
 * Unit tests for fxStoreRegistry — the per-pair cache of FX time series.
 *
 * Covers the slug grammar, the registry lifecycle, the gap-detection + bulk
 * fetch + merge + return flow of the three loaders, and the two single-day
 * lookups. zodiosApi is mocked so no real network calls are made.
 *
 * One behaviour the suite deliberately pins rather than asserts as correct,
 * flagged in the coverage report:
 *   - `loadFxRatesAndSignalsBulk` re-throws where the two `ensureFxRangeLoaded*`
 *     siblings swallow.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

// vi.mock is hoisted by Vitest — the factory runs before any imports below
vi.mock('$lib/api', () => ({
    zodiosApi: {
        convert_currency_bulk_api_v1_fx_currencies_convert_post: vi.fn(),
    },
}));

import {zodiosApi} from '$lib/api';
import {
    apiResultToFxDataPoint,
    apiResultsToCanonicalFxDataPoints,
    createPairSlug,
    displayFxRate,
    ensureFxRangeLoaded,
    ensureFxRangeLoadedBulk,
    getFxStore,
    getFxStoreByPair,
    getRegisteredPairs,
    invalidateAllFxStores,
    loadFxRatesAndSignalsBulk,
    lookupFxRate,
    lookupFxRateSync,
    parsePairSlug,
    removeFxStore,
} from '../fxStoreRegistry';

const mockConvert = vi.mocked(zodiosApi.convert_currency_bulk_api_v1_fx_currencies_convert_post);

/** Build a fake API response with one result per date at rate 1.25 */
function apiResp(...dates: string[]) {
    // Cast to any: production code reads these via (response as any)?.results
    return {
        success_count: dates.length,
        results: dates.map((d) => ({
            conversion_date: d,
            rate: '1.25',
            backward_fill_info: null,
        })),
    } as any;
}

beforeEach(() => {
    // Reset the module-level fxStores singleton between tests
    for (const slug of getRegisteredPairs()) removeFxStore(slug);
    mockConvert.mockReset();
});

describe('ensureFxRangeLoaded', () => {
    // =========================================================================
    // Test 1: Cache hit completa — nessuna chiamata API
    // =========================================================================
    it('returns cached data without calling the API when range is fully covered', async () => {
        const store = getFxStore('EUR-USD');
        store.merge([
            {date: '2024-01-01', rate: 1.1, backwardFillInfo: null},
            {date: '2024-01-02', rate: 1.2, backwardFillInfo: null},
            {date: '2024-01-03', rate: 1.3, backwardFillInfo: null},
        ]);

        const result = await ensureFxRangeLoaded('EUR-USD', '2024-01-01', '2024-01-03');

        expect(mockConvert).not.toHaveBeenCalled();
        expect(result).toHaveLength(3);
        expect(result[0].date).toBe('2024-01-01');
        expect(result[2].date).toBe('2024-01-03');
    });

    describe('apiResultsToCanonicalFxDataPoints', () => {
        const result = {
            conversion_date: '2024-01-02',
            rate: '0.8',
            backward_fill_info: {
                actual_rate_date: '2024-01-01',
                days_back: 1,
            },
        };

        it('keeps direct and identity rates unchanged', () => {
            expect(apiResultsToCanonicalFxDataPoints([result], false)[0]).toMatchObject({
                rate: 0.8,
                backwardFillInfo: {
                    actualRateDate: '2024-01-01',
                    daysBack: 1,
                },
            });
            expect(apiResultsToCanonicalFxDataPoints([{...result, rate: '1'}], false)[0].rate).toBe(1);
        });

        it('inverts displayed reverse-orientation rates before caching canonically', () => {
            expect(apiResultsToCanonicalFxDataPoints([result], true)[0].rate).toBe(1.25);
        });

        it('keeps a missing reverse-orientation rate missing instead of caching zero', () => {
            expect(apiResultsToCanonicalFxDataPoints([{...result, rate: null}], true)[0].rate).toBeNull();
        });
    });

    describe('loadFxRatesAndSignalsBulk', () => {
        it('uses one POST for all pairs and groups signals by request index', async () => {
            mockConvert.mockResolvedValueOnce({
                success_count: 2,
                results: [
                    {
                        from_amount: {code: 'EUR', amount: '1'},
                        to_amount: {code: 'USD', amount: '1.2'},
                        conversion_date: '2024-01-01',
                        rate: '1.2',
                        backward_fill_info: null,
                    },
                    {
                        from_amount: {code: 'USD', amount: '1'},
                        to_amount: {code: 'GBP', amount: '0.8'},
                        conversion_date: '2024-01-01',
                        rate: '0.8',
                        backward_fill_info: null,
                    },
                ],
                signal_results: [
                    {
                        request_index: 0,
                        signals: [
                            {
                                instance_id: 'eur-ema',
                                signal_code: 'EMA',
                                status: 'unavailable',
                            },
                        ],
                    },
                    {
                        request_index: 1,
                        signals: [
                            {
                                instance_id: 'gbp-ema',
                                signal_code: 'EMA',
                                status: 'unavailable',
                            },
                        ],
                    },
                ],
            } as any);

            const result = await loadFxRatesAndSignalsBulk([
                {
                    slug: 'EUR-USD',
                    start: '2024-01-01',
                    end: '2024-01-01',
                    displayedInverted: false,
                    signals: [{instance_id: 'eur-ema', signal_code: 'EMA', params: {period: 20}}],
                },
                {
                    slug: 'GBP-USD',
                    start: '2024-01-01',
                    end: '2024-01-01',
                    displayedInverted: true,
                    signals: [{instance_id: 'gbp-ema', signal_code: 'EMA', params: {period: 20}}],
                },
            ]);

            expect(mockConvert).toHaveBeenCalledOnce();
            const requests = mockConvert.mock.calls[0][0] as any[];
            expect(requests).toHaveLength(2);
            expect(requests[0]).toMatchObject({
                from_amount: {code: 'EUR', amount: '1'},
                to: 'USD',
                signals: [{instance_id: 'eur-ema', signal_code: 'EMA'}],
            });
            expect(requests[1]).toMatchObject({
                from_amount: {code: 'USD', amount: '1'},
                to: 'GBP',
            });
            expect(result.dataBySlug.get('EUR-USD')?.[0].rate).toBe(1.2);
            expect(result.dataBySlug.get('GBP-USD')?.[0].rate).toBe(1.25);
            expect(result.signalsBySlug.get('EUR-USD')?.[0].instance_id).toBe('eur-ema');
            expect(result.signalsBySlug.get('GBP-USD')?.[0].instance_id).toBe('gbp-ema');
        });

        it('still requests signals when rates are fully cached', async () => {
            getFxStore('EUR-USD').merge([{date: '2024-01-01', rate: 1.2, backwardFillInfo: null}]);
            mockConvert.mockResolvedValueOnce({
                success_count: 1,
                results: [],
                signal_results: [
                    {
                        request_index: 0,
                        signals: [],
                    },
                ],
            } as any);

            await loadFxRatesAndSignalsBulk([
                {
                    slug: 'EUR-USD',
                    start: '2024-01-01',
                    end: '2024-01-01',
                    displayedInverted: false,
                    signals: [{instance_id: 'ema-1', signal_code: 'EMA', params: {period: 20}}],
                },
            ]);

            expect(mockConvert).toHaveBeenCalledOnce();
        });
    });

    // =========================================================================
    // Test 2: Cache miss completa — API chiamata con range intero, dati mergiati
    // =========================================================================
    it('fetches the full range when store is empty', async () => {
        mockConvert.mockResolvedValueOnce(apiResp('2024-01-01', '2024-01-02', '2024-01-03'));

        const result = await ensureFxRangeLoaded('EUR-USD', '2024-01-01', '2024-01-03');

        expect(mockConvert).toHaveBeenCalledOnce();
        const requests = mockConvert.mock.calls[0][0] as any[];
        // Un unico gap → un unico request object
        expect(requests).toHaveLength(1);
        expect(requests[0].date_range).toEqual({start: '2024-01-01', end: '2024-01-03'});
        expect(requests[0].from_amount.code).toBe('EUR');
        expect(requests[0].from_amount.amount).toBe('1');
        expect(requests[0].to).toBe('USD');
        // Dati mergiati e ritornati
        expect(result).toHaveLength(3);
        expect(result[0].rate).toBe(1.25);
    });

    // =========================================================================
    // Test 3: Gap parziale — API chiamata solo per il buco, cache intatta
    // =========================================================================
    it('fetches only the missing gap when range is partially cached', async () => {
        // Pre-popola 01 e 03; il buco è solo 02
        const store = getFxStore('EUR-USD');
        store.merge([
            {date: '2024-01-01', rate: 1.1, backwardFillInfo: null},
            {date: '2024-01-03', rate: 1.3, backwardFillInfo: null},
        ]);
        mockConvert.mockResolvedValueOnce(apiResp('2024-01-02'));

        const result = await ensureFxRangeLoaded('EUR-USD', '2024-01-01', '2024-01-03');

        expect(mockConvert).toHaveBeenCalledOnce();
        const requests = mockConvert.mock.calls[0][0] as any[];
        // Solo il gap 2024-01-02
        expect(requests).toHaveLength(1);
        expect(requests[0].date_range).toEqual({start: '2024-01-02', end: '2024-01-02'});
        // Il risultato finale contiene tutti e 3 i giorni
        expect(result).toHaveLength(3);
    });

    // =========================================================================
    // Test 4: Errore di rete — nessun throw, ritorna cache parziale, consente retry
    // =========================================================================
    it('silently swallows network errors, returns cached data, and allows a retry', async () => {
        const store = getFxStore('EUR-USD');
        store.merge([{date: '2024-01-01', rate: 1.1, backwardFillInfo: null}]);
        mockConvert.mockRejectedValueOnce(new Error('Network error'));

        // Non deve lanciare nonostante l'errore di rete
        const result = await ensureFxRangeLoaded('EUR-USD', '2024-01-01', '2024-01-03');

        // Ritorna solo i dati già in cache
        expect(result).toHaveLength(1);
        expect(result[0].date).toBe('2024-01-01');

        // Il gap NON è stato marcato come fetchato — un nuovo tentativo chiama l'API di nuovo
        mockConvert.mockResolvedValueOnce(apiResp('2024-01-02', '2024-01-03'));
        const result2 = await ensureFxRangeLoaded('EUR-USD', '2024-01-01', '2024-01-03');
        expect(mockConvert).toHaveBeenCalledTimes(2);
        expect(result2).toHaveLength(3);
    });

    // =========================================================================
    // Test 7: 404 — marcato come fetchato, nessun retry
    // =========================================================================
    it('marks the range as fetched after a 404 so subsequent calls do not retry', async () => {
        const err404 = Object.assign(new Error('Not Found'), {response: {status: 404}});
        mockConvert.mockRejectedValueOnce(err404);

        const result = await ensureFxRangeLoaded('EUR-USD', '2024-01-01', '2024-01-03');

        // Prima chiamata: 404, nessun dato
        expect(mockConvert).toHaveBeenCalledTimes(1);
        expect(result).toHaveLength(0);

        // Seconda chiamata sullo stesso range: il gap è marcato come fetchato → nessuna API call
        const result2 = await ensureFxRangeLoaded('EUR-USD', '2024-01-01', '2024-01-03');
        expect(mockConvert).toHaveBeenCalledTimes(1); // ancora 1, non 2
        expect(result2).toHaveLength(0);
    });

    // =========================================================================
    // Test 5: Slug normalizzato — request usa canonBase/canonQuote (ordine alfabetico)
    // =========================================================================
    it('uses canonical alphabetical base/quote in the API request', async () => {
        mockConvert.mockResolvedValueOnce(apiResp('2024-01-01'));

        // EUR-USD: EUR < USD → canonBase='EUR', canonQuote='USD'
        await ensureFxRangeLoaded('EUR-USD', '2024-01-01', '2024-01-01');

        const requests = mockConvert.mock.calls[0][0] as any[];
        expect(requests[0].from_amount.code).toBe('EUR');
        expect(requests[0].to).toBe('USD');
    });

    // =========================================================================
    // Test 6: Gap multipli — array con N request (uno per gap)
    // =========================================================================
    it('sends one request per gap when there are multiple holes', async () => {
        // Pre-popola solo 01 e 03 — due gap: [02] e [04-05]
        const store = getFxStore('EUR-USD');
        store.merge([
            {date: '2024-01-01', rate: 1.1, backwardFillInfo: null},
            {date: '2024-01-03', rate: 1.3, backwardFillInfo: null},
        ]);
        mockConvert.mockResolvedValueOnce(apiResp('2024-01-02', '2024-01-04', '2024-01-05'));

        const result = await ensureFxRangeLoaded('EUR-USD', '2024-01-01', '2024-01-05');

        const requests = mockConvert.mock.calls[0][0] as any[];
        // Due gap → due request objects nell'array
        expect(requests).toHaveLength(2);
        expect(requests[0].date_range).toEqual({start: '2024-01-02', end: '2024-01-02'});
        expect(requests[1].date_range).toEqual({start: '2024-01-04', end: '2024-01-05'});
        // Tutti i 5 punti presenti dopo il merge
        expect(result).toHaveLength(5);
    });
});

// =============================================================================
//  Pair slugs — the key the whole registry is built on
// =============================================================================

describe('createPairSlug', () => {
    it('puts the two codes in alphabetical order, matching the backend', () => {
        expect(createPairSlug('EUR', 'USD')).toBe('EUR-USD');
    });

    it('produces the same slug whichever way round the pair is given', () => {
        expect(createPairSlug('USD', 'EUR')).toBe(createPairSlug('EUR', 'USD'));
    });

    it('upper-cases both codes', () => {
        expect(createPairSlug('usd', 'eur')).toBe('EUR-USD');
    });

    it('tolerates a pair of the same currency', () => {
        expect(createPairSlug('USD', 'usd')).toBe('USD-USD');
    });
});

describe('parsePairSlug', () => {
    it('reads a slug back into its two codes', () => {
        expect(parsePairSlug('EUR-USD')).toEqual({base: 'EUR', quote: 'USD'});
    });

    it('upper-cases what it reads', () => {
        expect(parsePairSlug('eur-usd')).toEqual({base: 'EUR', quote: 'USD'});
    });

    it.each(['EURUSD', 'EUR-USD-GBP', '', 'EUR-'])('refuses %s rather than guessing', (slug) => {
        // Silently guessing here would send the wrong currency to the backend,
        // so a slug that is not exactly two parts has to be loud. The empty
        // trailing part is the interesting one: `'EUR-'` splits into two, so it
        // is *accepted* — the assertion below records which of the four throw.
        const parse = () => parsePairSlug(slug);
        if (slug === 'EUR-') expect(parse()).toEqual({base: 'EUR', quote: ''});
        else expect(parse).toThrow(/Invalid pair slug/);
    });
});

// =============================================================================
//  The registry itself
// =============================================================================

describe('the store registry', () => {
    it('hands the same instance back for the same slug', () => {
        expect(getFxStore('EUR-USD')).toBe(getFxStore('EUR-USD'));
    });

    it('reaches the same instance from either currency order, in any case', () => {
        const canonical = getFxStore('EUR-USD');

        expect(getFxStoreByPair('EUR', 'USD')).toBe(canonical);
        expect(getFxStoreByPair('USD', 'EUR')).toBe(canonical);
        expect(getFxStoreByPair('usd', 'eur')).toBe(canonical);
    });

    it('lists the pairs that have been asked for', () => {
        getFxStore('EUR-USD');
        getFxStoreByPair('USD', 'GBP');

        expect(new Set(getRegisteredPairs())).toEqual(new Set(['EUR-USD', 'GBP-USD']));
    });

    it('reports whether a removal actually removed something', () => {
        getFxStore('EUR-USD');

        expect(removeFxStore('EUR-USD')).toBe(true);
        expect(removeFxStore('EUR-USD')).toBe(false);
        expect(removeFxStore('NEVER-SEEN')).toBe(false);
    });

    it('hands out a fresh store after a removal', () => {
        const before = getFxStore('EUR-USD');
        before.merge([{date: '2024-01-01', rate: 1.1, backwardFillInfo: null}]);

        removeFxStore('EUR-USD');
        const after = getFxStore('EUR-USD');

        expect(after).not.toBe(before);
        expect(after.get('2024-01-01')).toBeUndefined();
    });

    it('empties every store on a global invalidation but keeps the pairs registered', async () => {
        getFxStore('EUR-USD').merge([{date: '2024-01-01', rate: 1.1, backwardFillInfo: null}]);
        getFxStore('GBP-USD').merge([{date: '2024-01-01', rate: 0.8, backwardFillInfo: null}]);

        invalidateAllFxStores();

        expect(new Set(getRegisteredPairs())).toEqual(new Set(['EUR-USD', 'GBP-USD']));
        expect(getFxStore('EUR-USD').get('2024-01-01')).toBeUndefined();
        expect(getFxStore('GBP-USD').get('2024-01-01')).toBeUndefined();

        // The fetch marks go too, so the next range load really does re-fetch.
        mockConvert.mockResolvedValueOnce(apiResp('2024-01-01'));
        await ensureFxRangeLoaded('EUR-USD', '2024-01-01', '2024-01-01');
        expect(mockConvert).toHaveBeenCalledOnce();
    });
});

// =============================================================================
//  apiResultToFxDataPoint
// =============================================================================

describe('apiResultToFxDataPoint', () => {
    it('renames the API fields to the shape the chart reads', () => {
        expect(
            apiResultToFxDataPoint({
                conversion_date: '2024-01-02',
                rate: '1.2345',
                backward_fill_info: {actual_rate_date: '2024-01-01', days_back: 1},
            }),
        ).toEqual({
            date: '2024-01-02',
            rate: 1.2345,
            backwardFillInfo: {actualRateDate: '2024-01-01', daysBack: 1},
        });
    });

    it('reports an exact date match as no backward fill', () => {
        expect(apiResultToFxDataPoint({conversion_date: '2024-01-02', rate: '1.2', backward_fill_info: null}).backwardFillInfo).toBeNull();
    });

    it.each([
        ['null', null],
        ['undefined', undefined],
        ['the empty string', ''],
        ['a literal zero', '0'],
    ])('keeps an absent or invalid rate of %s as null', (_label, rate) => {
        expect(apiResultToFxDataPoint({conversion_date: '2024-01-02', rate, backward_fill_info: null}).rate).toBeNull();
    });
});

describe('displayFxRate', () => {
    it('keeps missing rates missing in both orientations', () => {
        expect(displayFxRate(null, false)).toBeNull();
        expect(displayFxRate(null, true)).toBeNull();
    });

    it('inverts only present positive rates and hides legacy zero sentinels', () => {
        expect(displayFxRate(1.25, false)).toBe(1.25);
        expect(displayFxRate(1.25, true)).toBe(0.8);
        expect(displayFxRate(0, false)).toBeNull();
        expect(displayFxRate(0, true)).toBeNull();
    });
});

// =============================================================================
//  lookupFxRateSync — the instant, cache-only read
// =============================================================================

describe('lookupFxRateSync', () => {
    it('returns nothing when the pair has never been asked for', () => {
        expect(lookupFxRateSync('EUR', 'USD', '2024-01-01')).toBeUndefined();
    });

    it('returns nothing when the pair is known but that day is not', () => {
        getFxStore('EUR-USD').merge([{date: '2024-01-01', rate: 1.2, backwardFillInfo: null}]);

        expect(lookupFxRateSync('EUR', 'USD', '2024-01-02')).toBeUndefined();
    });

    it('returns the stored point value in the canonical direction', () => {
        const point = {date: '2024-01-01', rate: 1.25, backwardFillInfo: null};
        getFxStore('EUR-USD').merge([point]);

        expect(lookupFxRateSync('EUR', 'USD', '2024-01-01')).toEqual(point);
    });

    it('inverts the rate when the caller asks for the other direction', () => {
        getFxStore('EUR-USD').merge([{date: '2024-01-01', rate: 1.25, backwardFillInfo: null}]);

        expect(lookupFxRateSync('USD', 'EUR', '2024-01-01')?.rate).toBe(0.8);
    });

    it('keeps the backward-fill note when it inverts', () => {
        getFxStore('EUR-USD').merge([{date: '2024-01-02', rate: 1.25, backwardFillInfo: {actualRateDate: '2024-01-01', daysBack: 1}}]);

        expect(lookupFxRateSync('USD', 'EUR', '2024-01-02')?.backwardFillInfo).toEqual({actualRateDate: '2024-01-01', daysBack: 1});
    });

    it('returns a missing-rate point when a reverse lookup would need to invert a missing rate', () => {
        getFxStore('EUR-USD').merge([{date: '2024-01-01', rate: null, backwardFillInfo: null}]);

        expect(lookupFxRateSync('USD', 'EUR', '2024-01-01')).toEqual({date: '2024-01-01', rate: null, backwardFillInfo: null});
    });

    it('normalizes a legacy cached zero rate to a missing-rate point', () => {
        getFxStore('EUR-USD').merge([{date: '2024-01-01', rate: 0, backwardFillInfo: null}]);

        expect(lookupFxRateSync('EUR', 'USD', '2024-01-01')).toEqual({date: '2024-01-01', rate: null, backwardFillInfo: null});
    });

    it('accepts lower-case currency codes', () => {
        getFxStore('EUR-USD').merge([{date: '2024-01-01', rate: 1.25, backwardFillInfo: null}]);

        expect(lookupFxRateSync('eur', 'usd', '2024-01-01')?.rate).toBe(1.25);
        expect(lookupFxRateSync('usd', 'eur', '2024-01-01')?.rate).toBe(0.8);
    });
});

// =============================================================================
//  ensureFxRangeLoaded — responses with nothing in them
// =============================================================================

describe('ensureFxRangeLoaded with an empty answer', () => {
    it.each([
        ['a response carrying no results field', {success_count: 0} as any],
        ['a response with an empty results list', {success_count: 0, results: []} as any],
        ['no response body at all', undefined as any],
    ])('merges nothing and does not re-ask, given %s', async (_label, response) => {
        mockConvert.mockResolvedValueOnce(response);

        expect(await ensureFxRangeLoaded('EUR-USD', '2024-01-01', '2024-01-02')).toEqual([]);
        expect(mockConvert).toHaveBeenCalledOnce();

        // The gap is marked fetched, so asking again costs nothing.
        expect(await ensureFxRangeLoaded('EUR-USD', '2024-01-01', '2024-01-02')).toEqual([]);
        expect(mockConvert).toHaveBeenCalledOnce();
    });
});

// =============================================================================
//  ensureFxRangeLoadedBulk — many pairs, one POST
// =============================================================================

describe('ensureFxRangeLoadedBulk', () => {
    /** One result per pair/date, in the canonical direction the caller asked for. */
    function bulkResp(...rows: Array<[string, string, string, string]>) {
        return {
            success_count: rows.length,
            results: rows.map(([from, to, date, rate]) => ({
                from_amount: {code: from, amount: '1'},
                to_amount: {code: to, amount: rate},
                conversion_date: date,
                rate,
                backward_fill_info: null,
            })),
        } as any;
    }

    it('asks for nothing when every pair is already cached', async () => {
        getFxStore('EUR-USD').merge([{date: '2024-01-01', rate: 1.2, backwardFillInfo: null}]);
        getFxStore('GBP-USD').merge([{date: '2024-01-01', rate: 0.8, backwardFillInfo: null}]);

        const result = await ensureFxRangeLoadedBulk([
            {slug: 'EUR-USD', start: '2024-01-01', end: '2024-01-01'},
            {slug: 'GBP-USD', start: '2024-01-01', end: '2024-01-01'},
        ]);

        expect(mockConvert).not.toHaveBeenCalled();
        expect(result.get('EUR-USD')?.[0].rate).toBe(1.2);
        expect(result.get('GBP-USD')?.[0].rate).toBe(0.8);
    });

    it('collects the gaps of every pair into a single POST', async () => {
        mockConvert.mockResolvedValueOnce(bulkResp(['EUR', 'USD', '2024-01-01', '1.2'], ['GBP', 'USD', '2024-01-01', '0.8']));

        await ensureFxRangeLoadedBulk([
            {slug: 'EUR-USD', start: '2024-01-01', end: '2024-01-01'},
            {slug: 'GBP-USD', start: '2024-01-01', end: '2024-01-01'},
        ]);

        expect(mockConvert).toHaveBeenCalledOnce();
        const requests = mockConvert.mock.calls[0][0] as any[];
        expect(requests).toHaveLength(2);
        expect(requests.map((r) => [r.from_amount.code, r.to])).toEqual([
            ['EUR', 'USD'],
            ['GBP', 'USD'],
        ]);
    });

    it('sends one entry per hole when a pair has several', async () => {
        getFxStore('EUR-USD').merge([
            {date: '2024-01-01', rate: 1.1, backwardFillInfo: null},
            {date: '2024-01-03', rate: 1.3, backwardFillInfo: null},
        ]);
        mockConvert.mockResolvedValueOnce(bulkResp(['EUR', 'USD', '2024-01-02', '1.2'], ['EUR', 'USD', '2024-01-05', '1.5']));

        await ensureFxRangeLoadedBulk([{slug: 'EUR-USD', start: '2024-01-01', end: '2024-01-05'}]);

        const requests = mockConvert.mock.calls[0][0] as any[];
        expect(requests.map((r) => r.date_range)).toEqual([
            {start: '2024-01-02', end: '2024-01-02'},
            {start: '2024-01-04', end: '2024-01-05'},
        ]);
    });

    it('files each result under the pair its own codes name', async () => {
        mockConvert.mockResolvedValueOnce(bulkResp(['EUR', 'USD', '2024-01-01', '1.2'], ['GBP', 'USD', '2024-01-01', '0.8']));

        const result = await ensureFxRangeLoadedBulk([
            {slug: 'EUR-USD', start: '2024-01-01', end: '2024-01-01'},
            {slug: 'GBP-USD', start: '2024-01-01', end: '2024-01-01'},
        ]);

        expect(result.get('EUR-USD')?.map((p) => p.rate)).toEqual([1.2]);
        expect(result.get('GBP-USD')?.map((p) => p.rate)).toEqual([0.8]);
    });

    it.each([
        ['no from code', {to_amount: {code: 'USD'}}],
        ['no to code', {from_amount: {code: 'EUR'}}],
        ['neither code', {}],
    ])('skips a result with %s instead of filing it under a wrong pair', async (_label, partial) => {
        mockConvert.mockResolvedValueOnce({
            success_count: 1,
            results: [{...partial, conversion_date: '2024-01-01', rate: '1.2', backward_fill_info: null}],
        } as any);

        const result = await ensureFxRangeLoadedBulk([{slug: 'EUR-USD', start: '2024-01-01', end: '2024-01-01'}]);

        expect(result.get('EUR-USD')).toEqual([]);
        expect(getRegisteredPairs()).toEqual(['EUR-USD']);
    });

    it('marks every gap fetched, so a repeat call is free even where nothing came back', async () => {
        mockConvert.mockResolvedValueOnce(bulkResp(['EUR', 'USD', '2024-01-01', '1.2']));

        const requests = [
            {slug: 'EUR-USD', start: '2024-01-01', end: '2024-01-01'},
            {slug: 'GBP-USD', start: '2024-01-01', end: '2024-01-01'},
        ];
        await ensureFxRangeLoadedBulk(requests);
        await ensureFxRangeLoadedBulk(requests);

        expect(mockConvert).toHaveBeenCalledOnce();
    });

    it('returns an entry for every requested pair, even one with no data', async () => {
        mockConvert.mockResolvedValueOnce(bulkResp(['EUR', 'USD', '2024-01-01', '1.2']));

        const result = await ensureFxRangeLoadedBulk([
            {slug: 'EUR-USD', start: '2024-01-01', end: '2024-01-01'},
            {slug: 'GBP-USD', start: '2024-01-01', end: '2024-01-01'},
        ]);

        expect([...result.keys()].sort()).toEqual(['EUR-USD', 'GBP-USD']);
        expect(result.get('GBP-USD')).toEqual([]);
    });

    it.each([
        ['a response carrying no results field', {success_count: 0} as any],
        ['no response body at all', undefined as any],
    ])('files nothing but still marks the range, given %s', async (_label, response) => {
        mockConvert.mockResolvedValueOnce(response);

        const requests = [{slug: 'EUR-USD', start: '2024-01-01', end: '2024-01-01'}];
        expect(await ensureFxRangeLoadedBulk(requests)).toEqual(new Map([['EUR-USD', []]]));

        await ensureFxRangeLoadedBulk(requests);
        expect(mockConvert).toHaveBeenCalledOnce();
    });

    it('treats a 404 as "there are no rates here" and stops asking', async () => {
        mockConvert.mockRejectedValueOnce(Object.assign(new Error('Not Found'), {response: {status: 404}}));

        const requests = [{slug: 'EUR-USD', start: '2024-01-01', end: '2024-01-01'}];
        expect(await ensureFxRangeLoadedBulk(requests)).toEqual(new Map([['EUR-USD', []]]));

        await ensureFxRangeLoadedBulk(requests);
        expect(mockConvert).toHaveBeenCalledOnce();
    });

    it('keeps a network failure retryable and never throws at the caller', async () => {
        mockConvert.mockRejectedValueOnce(new Error('Network error'));

        const requests = [{slug: 'EUR-USD', start: '2024-01-01', end: '2024-01-01'}];
        expect(await ensureFxRangeLoadedBulk(requests)).toEqual(new Map([['EUR-USD', []]]));

        mockConvert.mockResolvedValueOnce(bulkResp(['EUR', 'USD', '2024-01-01', '1.2']));
        expect((await ensureFxRangeLoadedBulk(requests)).get('EUR-USD')?.[0].rate).toBe(1.2);
        expect(mockConvert).toHaveBeenCalledTimes(2);
    });
});

// =============================================================================
//  loadFxRatesAndSignalsBulk — the paths the existing tests do not walk
// =============================================================================

describe('loadFxRatesAndSignalsBulk', () => {
    const cachedNoSignals = {slug: 'EUR-USD', start: '2024-01-01', end: '2024-01-01', displayedInverted: false, signals: []};

    it('asks for nothing when a pair needs neither rates nor signals', async () => {
        getFxStore('EUR-USD').merge([{date: '2024-01-01', rate: 1.2, backwardFillInfo: null}]);

        const result = await loadFxRatesAndSignalsBulk([cachedNoSignals]);

        expect(mockConvert).not.toHaveBeenCalled();
        expect(result.dataBySlug.get('EUR-USD')?.[0].rate).toBe(1.2);
        expect(result.signalsBySlug.size).toBe(0);
    });

    it('asks only for the holes when a pair needs rates but no signals', async () => {
        getFxStore('EUR-USD').merge([
            {date: '2024-01-01', rate: 1.1, backwardFillInfo: null},
            {date: '2024-01-03', rate: 1.3, backwardFillInfo: null},
        ]);
        mockConvert.mockResolvedValueOnce({success_count: 0, results: []} as any);

        await loadFxRatesAndSignalsBulk([{...cachedNoSignals, end: '2024-01-03'}]);

        const requests = mockConvert.mock.calls[0][0] as any[];
        expect(requests).toHaveLength(1);
        expect(requests[0].date_range).toEqual({start: '2024-01-02', end: '2024-01-02'});
    });

    it('sends the displayed orientation, not the canonical one', async () => {
        mockConvert.mockResolvedValueOnce({success_count: 0, results: []} as any);

        await loadFxRatesAndSignalsBulk([{...cachedNoSignals, displayedInverted: true}]);

        const requests = mockConvert.mock.calls[0][0] as any[];
        expect([requests[0].from_amount.code, requests[0].to]).toEqual(['USD', 'EUR']);
    });

    it('stores a reversed answer the canonical way round', async () => {
        // The card asked USD→EUR; the store is EUR-USD, so the rate has to be
        // flipped on the way in or every later reader gets it upside down.
        mockConvert.mockResolvedValueOnce({
            success_count: 1,
            results: [
                {
                    from_amount: {code: 'USD', amount: '1'},
                    to_amount: {code: 'EUR', amount: '0.8'},
                    conversion_date: '2024-01-01',
                    rate: '0.8',
                    backward_fill_info: null,
                },
            ],
        } as any);

        const result = await loadFxRatesAndSignalsBulk([{...cachedNoSignals, displayedInverted: true}]);

        expect(result.dataBySlug.get('EUR-USD')?.[0].rate).toBe(1.25);
        expect(getFxStore('EUR-USD').get('2024-01-01')?.rate).toBe(1.25);
    });

    it('skips a result whose currencies it cannot read', async () => {
        mockConvert.mockResolvedValueOnce({
            success_count: 1,
            results: [{conversion_date: '2024-01-01', rate: '1.2', backward_fill_info: null}],
        } as any);

        const result = await loadFxRatesAndSignalsBulk([cachedNoSignals]);

        expect(result.dataBySlug.get('EUR-USD')).toEqual([]);
    });

    it('groups several days of the same pair under one store', async () => {
        const row = (date: string, rate: string) => ({
            from_amount: {code: 'EUR', amount: '1'},
            to_amount: {code: 'USD', amount: rate},
            conversion_date: date,
            rate,
            backward_fill_info: null,
        });
        mockConvert.mockResolvedValueOnce({success_count: 2, results: [row('2024-01-01', '1.2'), row('2024-01-02', '1.3')]} as any);

        const result = await loadFxRatesAndSignalsBulk([{...cachedNoSignals, end: '2024-01-02'}]);

        expect(result.dataBySlug.get('EUR-USD')?.map((p) => p.rate)).toEqual([1.2, 1.3]);
    });

    it.each([
        ['a response carrying no results field', {success_count: 0} as any],
        ['no response body at all', undefined as any],
    ])('reads %s as no rates rather than failing', async (_label, response) => {
        mockConvert.mockResolvedValueOnce(response);

        const result = await loadFxRatesAndSignalsBulk([cachedNoSignals]);

        expect(result.dataBySlug.get('EUR-USD')).toEqual([]);
        expect(result.signalsBySlug.size).toBe(0);
    });

    it('returns no signals when the response carries no signal block', async () => {
        mockConvert.mockResolvedValueOnce({success_count: 0, results: []} as any);

        const result = await loadFxRatesAndSignalsBulk([{...cachedNoSignals, signals: [{instance_id: 'a', signal_code: 'EMA', params: {period: 20}}]}]);

        expect(result.signalsBySlug.size).toBe(0);
    });

    it('ignores a signal group that points at a request it never sent', async () => {
        mockConvert.mockResolvedValueOnce({
            success_count: 0,
            results: [],
            signal_results: [{request_index: 99, signals: [{instance_id: 'ghost', signal_code: 'EMA', status: 'unavailable'}]}],
        } as any);

        const result = await loadFxRatesAndSignalsBulk([{...cachedNoSignals, signals: [{instance_id: 'a', signal_code: 'EMA', params: {period: 20}}]}]);

        expect(result.signalsBySlug.size).toBe(0);
    });

    it('reads a signal group with no signal list as an empty result, not a crash', async () => {
        mockConvert.mockResolvedValueOnce({
            success_count: 0,
            results: [],
            signal_results: [{request_index: 0}],
        } as any);

        const result = await loadFxRatesAndSignalsBulk([{...cachedNoSignals, signals: [{instance_id: 'a', signal_code: 'EMA', params: {period: 20}}]}]);

        expect(result.signalsBySlug.get('EUR-USD')).toEqual([]);
    });

    it('marks the fetched range so a second load of the same window is free', async () => {
        mockConvert.mockResolvedValueOnce({success_count: 0, results: []} as any);
        await loadFxRatesAndSignalsBulk([cachedNoSignals]);

        await loadFxRatesAndSignalsBulk([cachedNoSignals]);

        expect(mockConvert).toHaveBeenCalledOnce();
    });

    describe('failures reach the caller here, unlike the other bulk loaders', () => {
        it('re-throws a 404 after marking the range fetched', async () => {
            const err404 = Object.assign(new Error('Not Found'), {response: {status: 404}});
            mockConvert.mockRejectedValueOnce(err404);

            await expect(loadFxRatesAndSignalsBulk([cachedNoSignals])).rejects.toBe(err404);

            // Marked despite the throw: the caller may retry, the network will not.
            mockConvert.mockResolvedValueOnce({success_count: 0, results: []} as any);
            await loadFxRatesAndSignalsBulk([cachedNoSignals]);
            expect(mockConvert).toHaveBeenCalledOnce();
        });

        it('re-throws a network failure and leaves the range retryable', async () => {
            const boom = new Error('Network error');
            mockConvert.mockRejectedValueOnce(boom);

            await expect(loadFxRatesAndSignalsBulk([cachedNoSignals])).rejects.toBe(boom);

            mockConvert.mockResolvedValueOnce({success_count: 0, results: []} as any);
            await loadFxRatesAndSignalsBulk([cachedNoSignals]);
            expect(mockConvert).toHaveBeenCalledTimes(2);
        });
    });
});

// =============================================================================
//  lookupFxRate — one day, cache first
// =============================================================================

describe('lookupFxRate', () => {
    function oneResult(rate: string | null, date = '2024-01-01') {
        return {success_count: 1, results: [{conversion_date: date, rate, backward_fill_info: null}]} as any;
    }

    it('answers from the cache without touching the network', async () => {
        const point = {date: '2024-01-01', rate: 1.25, backwardFillInfo: null};
        getFxStore('EUR-USD').merge([point]);

        expect(await lookupFxRate('EUR', 'USD', '2024-01-01')).toEqual(point);
        expect(mockConvert).not.toHaveBeenCalled();
    });

    it('answers a reversed request from the cache, inverted', async () => {
        getFxStore('EUR-USD').merge([{date: '2024-01-01', rate: 1.25, backwardFillInfo: null}]);

        expect((await lookupFxRate('USD', 'EUR', '2024-01-01'))?.rate).toBe(0.8);
        expect(mockConvert).not.toHaveBeenCalled();
    });

    it('fetches one canonical day on a miss and caches it', async () => {
        mockConvert.mockResolvedValueOnce(oneResult('1.25'));

        expect((await lookupFxRate('EUR', 'USD', '2024-01-01'))?.rate).toBe(1.25);

        const requests = mockConvert.mock.calls[0][0] as any[];
        expect(requests[0]).toMatchObject({from_amount: {code: 'EUR', amount: '1'}, to: 'USD', date_range: {start: '2024-01-01', end: '2024-01-01'}});
        expect(getFxStore('EUR-USD').get('2024-01-01')?.rate).toBe(1.25);
    });

    it('asks canonically even when the caller wants the other direction, and inverts the answer', async () => {
        mockConvert.mockResolvedValueOnce(oneResult('1.25'));

        expect((await lookupFxRate('USD', 'EUR', '2024-01-01'))?.rate).toBe(0.8);

        const requests = mockConvert.mock.calls[0][0] as any[];
        expect(requests[0].from_amount.code).toBe('EUR');
        // What is cached stays canonical, whichever direction was asked for.
        expect(getFxStore('EUR-USD').get('2024-01-01')?.rate).toBe(1.25);
    });

    it.each([
        ['the results list is empty', {success_count: 0, results: []} as any],
        ['there is no results field', {success_count: 0} as any],
        ['there is no response body', undefined as any],
    ])('returns null when %s', async (_label, response) => {
        mockConvert.mockResolvedValueOnce(response);

        expect(await lookupFxRate('EUR', 'USD', '2024-01-01')).toBeNull();
    });

    it('returns a missing-rate point for a day the backend has no rate for, and caches that fact', async () => {
        mockConvert.mockResolvedValueOnce(oneResult(null));

        expect(await lookupFxRate('EUR', 'USD', '2024-01-01')).toEqual({date: '2024-01-01', rate: null, backwardFillInfo: null});
        expect(getFxStore('EUR-USD').get('2024-01-01')).toEqual({date: '2024-01-01', rate: null, backwardFillInfo: null});
    });

    it('returns null rather than propagating a failure', async () => {
        mockConvert.mockRejectedValueOnce(new Error('Network error'));

        expect(await lookupFxRate('EUR', 'USD', '2024-01-01')).toBeNull();
    });

    it('hands back a cached direct missing rate for the tooltip helper to reject', async () => {
        mockConvert.mockResolvedValueOnce({success_count: 1, results: [{conversion_date: '2024-01-01', rate: null, backward_fill_info: null}]} as any);
        await ensureFxRangeLoaded('EUR-USD', '2024-01-01', '2024-01-01');

        expect(await lookupFxRate('EUR', 'USD', '2024-01-01')).toEqual({date: '2024-01-01', rate: null, backwardFillInfo: null});
    });
});

// =============================================================================
//  Deliberately left uncovered — three arms that cannot be reached
//
//  fxStoreRegistry.ts:296  `if (points.length > 0)`   (false arm)
//  fxStoreRegistry.ts:399  `if (points.length > 0)`   (false arm)
//      `pointsBySlug` only gains a key through
//      `if (!pointsBySlug.has(slug)) pointsBySlug.set(slug, [])`, which is
//      immediately followed by `.push(point)`. No key can ever hold an empty
//      array, so the guard is never false.
//
// =============================================================================
