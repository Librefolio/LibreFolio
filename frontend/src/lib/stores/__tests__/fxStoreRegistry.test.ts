/**
 * Unit tests for fxStoreRegistry — the per-pair cache of FX time series.
 *
 * Covers the slug grammar, the registry lifecycle, the gap-detection + bulk
 * fetch + merge + return flow of the three loaders, and the two single-day
 * lookups. zodiosApi is mocked so no real network calls are made.
 *
 * The last block (Z-14): the registry listens to the portfolio bus from its
 * import, and a price catch-up (`notifyPricesCaughtUp()`, `{kind: 'prices'}`)
 * makes every cached pair stale — for the three loaders and for
 * `lookupFxRate`, never for `lookupFxRateSync`. It is driven through the real
 * bus, never through a helper exported for the test (N58).
 *
 * In the `loadFxRatesAndSignalsBulk` block, the cases of Z-27: a list past the
 * backend's bulk caps (1,000 items; 1,000,000 item-days since R13-SEC9-2 —
 * Z-25) goes in batches planned by `$lib/api/bulkBatches`, sent one after the
 * other, applied all at the end, each batch's signal groups read through its
 * own entries. Their sizes follow the caps that module exports. That module is
 * the real one, with `sendBulkBatches` passed through a spy so one case can
 * read the estimate the loader gives it.
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

// Z-27: the real batching helper, with `sendBulkBatches` passed through a spy so that one case can read the estimate
// the loader hands it; the plan, the sends and the splits stay the real ones. Until the module exists nothing imports
// it but that case, which fails at its import.
vi.mock('$lib/api/bulkBatches', async (importOriginal) => {
    const real = await importOriginal<typeof import('$lib/api/bulkBatches')>();
    return {...real, sendBulkBatches: vi.fn(real.sendBulkBatches)};
});

import {zodiosApi} from '$lib/api';
import {notifyPortfolioMutation, notifyPricesCaughtUp, requestPortfolioRefresh} from '$lib/stores/portfolio/portfolioMutation';
import * as registry from '../fxStoreRegistry';
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
import type {FxRatesAndSignalsBulkRequest, FxRatesAndSignalsBulkResult} from '../fxStoreRegistry';

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

// One home for financial math: the backend (X-R59, decision N80). The FX table’s Δ Abs and Δ %, the FX card’s Δ and the
// pair page’s summary read the change over the range from `POST /fx/currencies/period-changes` — `range_change`, both
// orientations — through `utils/rangeChange.ts`: the registry no longer derives it from the first and last rates it cached.
// Bug B1’s rule (an inverted pair changes by first ÷ last − 1, never by the negated direct change) is the backend’s
// `inverse_change_ratio` now, read and never derived (`utils/__tests__/rangeChange.test.ts`). The displayed rate stays here.
//
// Red today: displayFxDelta is exported.
describe('the Δ over the range is the backend’s, not the registry’s (X-R59)', () => {
    it('exports no displayFxDelta', () => {
        expect('displayFxDelta' in registry, 'the change over the range is the backend’s range_change: fxStoreRegistry still offers its own computation of it').toBe(false);
        expect(typeof registry.displayFxRate, 'control: the module is read, and the displayed rate stays').toBe('function');
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

    // =========================================================================
    //  A list past the bulk caps goes in batches (Z-27, decisions D1–D4 of 17/10)
    //
    //  Since Z-25 `POST /fx/currencies/convert` refuses more than `MAX_BULK_ITEMS` items (1,000; 422
    //  `bulk_too_many_items`) and more than `MAX_BULK_ITEM_DAYS` item-days (1,000,000 since R13-SEC9-2; 422
    //  `bulk_too_many_days`), and the FX list sent every entry in one POST: past either cap it loaded nothing. The
    //  loader sends its entries through `sendBulkBatches` (`$lib/api/bulkBatches`): batches planned under
    //  `BULK_MAX_ITEMS` entries and `BULK_ITEM_DAYS_BUDGET` estimated item-days (80 % of the backend's) — an entry
    //  estimated at the days of its range (`bulkRangeDays`), doubled plus `BULK_SIGNAL_MARGIN_DAYS` of warm-up when it
    //  has signals — sent one after the other, a batch refused for its days split and sent again. D3, all at the end:
    //  once every batch settled the points are merged, the signal groups of each batch are read through that batch's
    //  own entries (`request_index` counts from 0 in every POST), and the entries of the batches that answered are
    //  marked fetched; after a failure a 404 marks the entries of the request that got it, nothing further is sent,
    //  and the error is re-thrown. With one batch the load is today's, which every case above keeps pinning.
    //
    //  Every size here is derived from the caps the module exports, read when a case runs (`caps()`): a later change
    //  of the budget moves the cases with it. The fake backend answers each POST from its own body and numbers its
    //  signal groups from 0, as the real one does (`backend/app/api/v1/fx/currencies.py`). The first case reaches its
    //  batches through the item-days budget with «All» from 2000: it is the slow one of the file — the loader walks
    //  every day of every range in the stores, before and after the POSTs — and its size grows with the budget. The
    //  failure cases reach a second batch through the item cap with two-day ranges, which cost nothing. The estimate
    //  itself is read from the call to `sendBulkBatches` (passed through a spy, see the top of the file).
    //  A card's store is read on two days: its last day holds the answered point («merged»); its first day holds
    //  none, so only a fetched mark keeps it out of the missing intervals («fetched»).
    //
    //  Red first: until the module exists every case fails at the import of its caps; once it exists, they fail on
    //  the loader's single POST until the loader sends its entries through it.
    // =========================================================================
    describe('in batches under the bulk caps (Z-27)', () => {
        const TWO_DAYS = {start: '2024-01-01', end: '2024-01-02'};
        /** «All» from 2000: 9,497 days, both ends included. */
        const ALL = {start: '2000-01-01', end: '2025-12-31'};
        const ALL_DAYS = 9_497;
        /** What the backend's 422 says it allows (`max_item_days`): 1,000,000 since R13-SEC9-2. The split reads it from the refusal. */
        const BACKEND_MAX_ITEM_DAYS = 1_000_000;

        /** The caps of `$lib/api/bulkBatches`, read from the module when a case runs: every size below follows them. */
        async function caps(): Promise<{maxItems: number; budget: number; margin: number}> {
            const bulk = await import('$lib/api/bulkBatches');
            return {maxItems: bulk.BULK_MAX_ITEMS, budget: bulk.BULK_ITEM_DAYS_BUDGET, margin: bulk.BULK_SIGNAL_MARGIN_DAYS};
        }

        /** The item cap, for the cases that reach a second batch through it: two-day cards without signals never fill the item-days budget first. */
        async function itemCap(): Promise<number> {
            const {maxItems, budget} = await caps();
            expect(maxItems * 2, 'premise: a full batch of two-day cards stays under the item-days budget').toBeLessThanOrEqual(budget);
            return maxItems;
        }

        /** The n-th of 17,576 distinct codes, all before USD (AAA, AAB, …): `<code>-USD` is a canonical slug. */
        function code(n: number): string {
            const letter = (k: number) => String.fromCharCode(65 + (k % 26));
            return letter(Math.floor(n / 676)) + letter(Math.floor(n / 26)) + letter(n);
        }

        /** `n` cards in list order, each its own pair over `range`; with signals, one EMA whose instance id names the pair. */
        function cards(n: number, range: {start: string; end: string}, withSignals: boolean): FxRatesAndSignalsBulkRequest[] {
            return Array.from({length: n}, (_, i) => {
                const slug = `${code(i)}-USD`;
                return {slug, ...range, displayedInverted: false, signals: withSignals ? [{instance_id: `ema-${slug}`, signal_code: 'EMA', params: {period: 20}}] : []};
            });
        }

        /**
         * The backend's answer to one POST, built from its own body: a point on the last day of each item's range, and
         * for each item with signals a group numbered by the item's position IN THIS POST, echoing that item's signals.
         */
        function answerOf(body: any[]) {
            return {
                success_count: body.length,
                results: body.map((item) => ({from_amount: {code: item.from_amount.code, amount: '1'}, to_amount: {code: item.to, amount: '1.25'}, conversion_date: item.date_range.end, rate: '1.25', backward_fill_info: null})),
                signal_results: body.flatMap((item, requestIndex) =>
                    item.signals?.length > 0
                        ? [
                              {
                                  request_index: requestIndex,
                                  from_currency: item.from_amount.code,
                                  to_currency: item.to,
                                  date_range: item.date_range,
                                  signals: item.signals.map((signal: any) => ({instance_id: signal.instance_id, signal_code: signal.signal_code, status: 'unavailable'})),
                              },
                          ]
                        : [],
                ),
            } as any;
        }

        /** How many entries each POST carried, in call order. */
        const postSizes = () => mockConvert.mock.calls.map(([body]) => (body as unknown[]).length);

        /** The instance ids a load returned for a pair, joined; `nothing` when no group reached it. */
        function signalIdsOf(signalsBySlug: FxRatesAndSignalsBulkResult['signalsBySlug'], slug: string): string {
            const signals = signalsBySlug.get(slug);
            return signals ? signals.map((signal) => signal.instance_id).join() : 'nothing';
        }

        /** What the load left in the cards' stores, counted: `merged+fetched`, `fetched` (no point: a 404), `merged`, or `untouched`. */
        function tally(list: FxRatesAndSignalsBulkRequest[]): Record<string, number> {
            const counts: Record<string, number> = {};
            for (const card of list) {
                const store = getFxStore(card.slug);
                const merged = store.get(card.end) !== undefined;
                const fetched = store.getMissingIntervals(card.start, card.start).length === 0;
                const state = merged && fetched ? 'merged+fetched' : merged ? 'merged' : fetched ? 'fetched' : 'untouched';
                counts[state] = (counts[state] ?? 0) + 1;
            }
            return counts;
        }

        function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void} {
            let resolve!: (value: T) => void;
            const promise = new Promise<T>((settle) => {
                resolve = settle;
            });
            return {promise, resolve};
        }

        /** `promise`, or a failure naming what never came: a red fails fast and says why, instead of at the test timeout. */
        async function within<T>(promise: Promise<T>, what: string, ms = 3_000): Promise<T> {
            let timer: ReturnType<typeof setTimeout> | undefined;
            const deadline = new Promise<never>((_resolve, reject) => {
                timer = setTimeout(() => reject(new Error(`${what} — nothing within ${ms} ms`)), ms);
            });
            try {
                return await Promise.race([promise, deadline]);
            } finally {
                clearTimeout(timer);
            }
        }

        function settled<T>(promise: Promise<T>): Promise<PromiseSettledResult<T>> {
            return Promise.allSettled([promise]).then(([outcome]) => outcome);
        }

        it('splits a list past the item-days budget into consecutive POSTs and gives every pair its own signals', {timeout: 60_000}, async () => {
            const {maxItems, budget, margin} = await caps();
            // An «All» card with a signal is estimated at 2 × 9,497 + the warm-up margin — the daily items, and the
            // signal items with their warm-up: 19,394 item-days at 400. `perBatch` of them fill the budget (41 at
            // 800,000): two full batches and one card more make three POSTs.
            const perBatch = Math.floor(budget / (2 * ALL_DAYS + margin));
            expect(perBatch, 'premise: an «All» card fits the budget').toBeGreaterThan(0);
            expect(perBatch, 'premise: the budget closes these batches, not the item cap').toBeLessThan(maxItems);
            const list = cards(2 * perBatch + 1, ALL, true);
            mockConvert.mockImplementation(async (body) => answerOf(body as any[]));

            const result = await within(loadFxRatesAndSignalsBulk(list), 'the load never settled', 30_000);

            expect(
                postSizes(),
                `${list.length} cards with a signal over «All» go as ${perBatch} + ${perBatch} + 1 POSTs, planned under the budget of ${budget} (Z-27): in one POST they are about ${list.length * (2 * ALL_DAYS + margin)} item-days, where the backend refuses past its MAX_BULK_ITEM_DAYS (422 bulk_too_many_days, Z-25)`,
            ).toEqual([perBatch, perBatch, 1]);
            expect(
                mockConvert.mock.calls.flatMap(([body]) => (body as any[]).map((item) => `${item.from_amount.code}-${item.to} ${item.date_range.start}..${item.date_range.end} ${item.signals[0]?.instance_id}`)),
                'consecutive batches, in list order, every entry whole',
            ).toEqual(list.map((card) => `${card.slug} ${card.start}..${card.end} ema-${card.slug}`));
            const misfiled = list.filter((card) => signalIdsOf(result.signalsBySlug, card.slug) !== `ema-${card.slug}`).map((card) => `${card.slug} got ${signalIdsOf(result.signalsBySlug, card.slug)}`);
            expect(misfiled, 'request_index counts from 0 in every POST: the groups of a batch are read through that batch’s own entries — or the groups of the later batches land on the first cards, and their own cards get none').toEqual([]);
            expect(tally(list), 'every pair: its point merged, its range marked fetched').toEqual({'merged+fetched': list.length});
        });

        it('estimates an entry at the days of its range as the backend cuts it — doubled, plus the warm-up margin, when it has signals (D1)', async () => {
            // 2026-10-17 at noon on the machine's calendar: `todayIso()` is 2026-10-17, the backend's last day 2026-10-18.
            vi.useFakeTimers({toFake: ['Date']});
            vi.setSystemTime(new Date(2026, 9, 17, 12));
            try {
                const {sendBulkBatches, BULK_SIGNAL_MARGIN_DAYS} = await import('$lib/api/bulkBatches');
                const spied = vi.mocked(sendBulkBatches);
                spied.mockClear();
                mockConvert.mockImplementation(async (body) => answerOf(body as any[]));

                await within(
                    loadFxRatesAndSignalsBulk([
                        {slug: 'AAA-USD', ...ALL, displayedInverted: false, signals: [{instance_id: 'ema-AAA-USD', signal_code: 'EMA', params: {period: 20}}]},
                        {slug: 'AAB-USD', ...ALL, displayedInverted: false, signals: []},
                        {slug: 'AAC-USD', start: '2026-10-01', end: '2026-12-31', displayedInverted: false, signals: []},
                    ]),
                    'the load never settled',
                );

                expect(spied, 'the loader sends its entries through sendBulkBatches').toHaveBeenCalledOnce();
                const [items, estimate] = spied.mock.calls[0];
                expect(
                    items.map((item) => estimate(item)),
                    '«All» from 2000 with a signal: 2 × 9,497 + the margin (the daily items, the signal items and their warm-up); without: 9,497; a range past tomorrow: cut there, 18 days',
                ).toEqual([2 * ALL_DAYS + BULK_SIGNAL_MARGIN_DAYS, ALL_DAYS, 18]);
            } finally {
                vi.useRealTimers();
            }
        });

        it('merges nothing of an answered batch while the next one is pending (D3: all at the end)', {timeout: 15_000}, async () => {
            const maxItems = await itemCap();
            const list = cards(maxItems + 1, TWO_DAYS, false);
            const secondSent = deferred<unknown[]>();
            const secondAnswer = deferred<unknown>();
            mockConvert
                .mockImplementationOnce(async (body) => answerOf(body as any[]))
                .mockImplementationOnce((body) => {
                    secondSent.resolve(body as unknown[]);
                    return secondAnswer.promise as any;
                });

            const loading = settled(loadFxRatesAndSignalsBulk(list));
            const secondBody = await within(secondSent.promise, `the second POST never went out: ${list.length} cards in one POST pass the backend’s ${maxItems}-item cap (422 bulk_too_many_items, Z-25)`);

            expect(postSizes(), `${maxItems} cards, then the last one`).toEqual([maxItems, 1]);
            expect(tally(list.slice(0, maxItems)), 'D3: the first batch has answered, but nothing of it reaches the stores before every batch settled').toEqual({untouched: maxItems});

            secondAnswer.resolve(answerOf(secondBody as any[]));
            const outcome = await within(loading, 'the load never settled once the second POST answered');

            expect(outcome.status).toBe('fulfilled');
            expect(tally(list), 'once every batch settled: every pair merged and marked fetched').toEqual({'merged+fetched': list.length});
        });

        it('keeps the batch answered before a 500, sends nothing after it, and re-throws the 500', {timeout: 15_000}, async () => {
            const maxItems = await itemCap();
            const list = cards(2 * maxItems + 1, TWO_DAYS, false);
            const boom = Object.assign(new Error('Request failed with status code 500'), {response: {status: 500, data: {detail: 'Internal Server Error'}}});
            mockConvert
                .mockImplementationOnce(async (body) => answerOf(body as any[]))
                .mockRejectedValueOnce(boom)
                // Would answer a third POST: there must be none.
                .mockImplementation(async (body) => answerOf(body as any[]));

            const outcome = await within(settled(loadFxRatesAndSignalsBulk(list)), 'the load never settled');

            expect(postSizes(), `batches of ${maxItems}, ${maxItems} and 1, and none after the one that failed: ${list.length} cards in one POST pass the backend’s ${maxItems}-item cap (422 bulk_too_many_items, Z-25)`).toEqual([maxItems, maxItems]);
            expect(outcome.status, 'the 500 reaches the caller, as today').toBe('rejected');
            expect((outcome as PromiseRejectedResult).reason).toBe(boom);
            expect(tally(list.slice(0, maxItems)), 'the batch that answered: merged and marked fetched').toEqual({'merged+fetched': maxItems});
            expect(tally(list.slice(maxItems, 2 * maxItems)), 'the batch of the 500: nothing merged, nothing marked — the next load asks again').toEqual({untouched: maxItems});
            expect(tally(list.slice(2 * maxItems)), 'the batch never sent: neither merged nor marked').toEqual({untouched: 1});
        });

        it('marks the batch that got a 404 fetched, keeps the batch before it, sends nothing after it, and re-throws the 404', {timeout: 15_000}, async () => {
            const maxItems = await itemCap();
            const list = cards(2 * maxItems + 1, TWO_DAYS, false);
            const err404 = Object.assign(new Error('Not Found'), {response: {status: 404}});
            mockConvert
                .mockImplementationOnce(async (body) => answerOf(body as any[]))
                .mockRejectedValueOnce(err404)
                // Would answer a third POST: there must be none.
                .mockImplementation(async (body) => answerOf(body as any[]));

            const outcome = await within(settled(loadFxRatesAndSignalsBulk(list)), 'the load never settled');

            expect(postSizes(), `batches of ${maxItems}, ${maxItems} and 1, and none after the one that failed: ${list.length} cards in one POST pass the backend’s ${maxItems}-item cap (422 bulk_too_many_items, Z-25)`).toEqual([maxItems, maxItems]);
            expect(outcome.status, 'the 404 reaches the caller, as today').toBe('rejected');
            expect((outcome as PromiseRejectedResult).reason).toBe(err404);
            expect(tally(list.slice(0, maxItems)), 'the batch that answered: merged and marked fetched').toEqual({'merged+fetched': maxItems});
            expect(tally(list.slice(maxItems, 2 * maxItems)), 'today’s 404 rule, applied to the request that got it: no rates there, and the next load does not ask again').toEqual({fetched: maxItems});
            expect(tally(list.slice(2 * maxItems)), 'the batch never sent: neither merged nor marked').toEqual({untouched: 1});
        });

        it('splits a batch the backend refuses for its days, and still loads every pair with its own signals', {timeout: 15_000}, async () => {
            const {maxItems, budget, margin} = await caps();
            const list = cards(6, TWO_DAYS, true);
            expect(list.length * (2 * 2 + margin), 'premise: six two-day cards with a signal are planned as one batch').toBeLessThanOrEqual(budget);
            expect(list.length, 'premise: … under the item cap as well').toBeLessThanOrEqual(maxItems);
            // The estimate cannot see every warm-up, so the backend may count more than was planned. Its 422 says by
            // how much: one item-day past its budget asks for max(2, ceil(item_days / max_item_days) + 1) = 3 parts of 2.
            const refusal = Object.assign(new Error('Request failed with status code 422'), {
                response: {
                    status: 422,
                    data: {detail: {code: 'bulk_too_many_days', message: `A bulk request may build at most ${BACKEND_MAX_ITEM_DAYS} per-day points, and this one would build at least ${BACKEND_MAX_ITEM_DAYS + 1}`, max_item_days: BACKEND_MAX_ITEM_DAYS, item_days: BACKEND_MAX_ITEM_DAYS + 1}},
                },
            });
            mockConvert.mockRejectedValueOnce(refusal).mockImplementation(async (body) => answerOf(body as any[]));

            const outcome = await within(settled(loadFxRatesAndSignalsBulk(list)), 'the load never settled');

            expect(outcome.status, 'the FX list gave up on the backend’s 422 bulk_too_many_days instead of splitting the batch (Z-27)').toBe('fulfilled');
            expect(postSizes(), 'the refused POST of 6, then its 3 parts').toEqual([6, 2, 2, 2]);
            const {signalsBySlug} = (outcome as PromiseFulfilledResult<FxRatesAndSignalsBulkResult>).value;
            expect(
                list.map((card) => `${card.slug} ${signalIdsOf(signalsBySlug, card.slug)}`),
                'every part numbers its groups from 0: each pair still gets its own signals',
            ).toEqual(list.map((card) => `${card.slug} ema-${card.slug}`));
            expect(tally(list), 'every pair: its point merged, its range marked fetched').toEqual({'merged+fetched': 6});
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
//  A price catch-up makes every cached pair stale (Z-14)
//
//  The answers fill backward the days without a rate, so a loaded range holds a
//  point for every day and was never asked again in the session — not even
//  after the server caught up on rates. The registry listens to the portfolio
//  bus from its import (`registerPortfolioMutationListener('fxStoreRegistry',
//  …)`): on `{kind: 'prices'}` — `notifyPricesCaughtUp()` — it marks every
//  pair's store stale. The three loaders then ask a range loaded before again,
//  each for the whole of it in one interval although every day has a point,
//  and `lookupFxRate` takes a stale point for a miss: one request for its day,
//  then that day is fresh. `lookupFxRateSync` stays a pure cache read.
//  `{kind: 'mutation'}` — the live poll's `POST /assets/prices/current`, a
//  commit — and `{kind: 'refresh'}` («Aggiorna») change nothing.
//
//  With backend signals `loadFxRatesAndSignalsBulk` asks the full range every
//  time already: only its path without signals is under test here.
//
//  Isolation: the `beforeEach` at the top removes every registered pair, and a
//  store's stale state goes with it. Red first: until the listener exists the
//  signal reaches nobody, and the range comes from the cache again.
// =============================================================================

describe('fxStoreRegistry after a price catch-up (Z-14)', () => {
    const START = '2026-01-01';
    const END = '2026-01-05';
    const DAYS = ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05'] as const;

    /** One result per day for `base`→`quote` at `rate`, with the codes the bulk loaders file it by: every day answered, as the backward fill does. */
    function ratesAt(base: string, quote: string, rate: string, days: readonly string[] = DAYS) {
        return days.map((date) => ({from_amount: {code: base, amount: '1'}, to_amount: {code: quote, amount: rate}, conversion_date: date, rate, backward_fill_info: null}));
    }

    function converted(...results: Array<ReturnType<typeof ratesAt>[number]>) {
        return {success_count: results.length, results} as any;
    }

    /** A range of `slug` loaded the way a page leaves it: a point for every day, the range marked fetched. */
    function loaded(slug: string, rate = 1.1): void {
        const store = getFxStore(slug);
        store.merge(DAYS.map((date) => ({date, rate, backwardFillInfo: null})));
        store.markFetched(START, END);
    }

    it('ensureFxRangeLoaded asks a range loaded before the catch-up again — one interval, the whole range, though every day has a point — then serves it from the cache', async () => {
        mockConvert.mockResolvedValueOnce(converted(...ratesAt('EUR', 'USD', '1.10')));
        await ensureFxRangeLoaded('EUR-USD', START, END);
        await ensureFxRangeLoaded('EUR-USD', START, END);
        expect(mockConvert, 'premise: a loaded range is served from the cache').toHaveBeenCalledOnce();
        expect(getFxStore('EUR-USD').size, 'premise: the store holds a point for every day').toBe(DAYS.length);

        notifyPricesCaughtUp();
        expect(mockConvert, 'the mark must not ask anything by itself').toHaveBeenCalledOnce();

        mockConvert.mockResolvedValueOnce(converted(...ratesAt('EUR', 'USD', '1.20')));
        const fresh = await ensureFxRangeLoaded('EUR-USD', START, END);

        expect(mockConvert, 'after a price catch-up the FX range loaded before came from the cache again: its backward-filled days hide the rates the server caught up on (Z-14)').toHaveBeenCalledTimes(2);
        const requests = mockConvert.mock.calls[1][0] as any[];
        expect(
            requests.map((request) => request.date_range),
            'one interval, the whole range: the points of the stale range do not make holes of their own',
        ).toEqual([{start: START, end: END}]);
        expect(requests[0]).toMatchObject({from_amount: {code: 'EUR', amount: '1'}, to: 'USD'});
        expect(
            fresh.map((point) => point.rate),
            'the fresh rates replace the stale ones',
        ).toEqual([1.2, 1.2, 1.2, 1.2, 1.2]);

        await ensureFxRangeLoaded('EUR-USD', START, END);
        expect(mockConvert, 'the fresh answer marks the range fetched: one catch-up, one question').toHaveBeenCalledTimes(2);
    });

    it('ensureFxRangeLoadedBulk asks every pair loaded before the catch-up again, in one POST, each for its whole range — then nothing', async () => {
        const requests = [
            {slug: 'EUR-USD', start: START, end: END},
            {slug: 'GBP-USD', start: START, end: END},
        ];
        mockConvert.mockResolvedValueOnce(converted(...ratesAt('EUR', 'USD', '1.10'), ...ratesAt('GBP', 'USD', '1.30')));
        await ensureFxRangeLoadedBulk(requests);
        await ensureFxRangeLoadedBulk(requests);
        expect(mockConvert, 'premise: two loaded ranges are served from the cache').toHaveBeenCalledOnce();

        notifyPricesCaughtUp();
        mockConvert.mockResolvedValueOnce(converted(...ratesAt('EUR', 'USD', '1.20'), ...ratesAt('GBP', 'USD', '1.40')));
        const fresh = await ensureFxRangeLoadedBulk(requests);

        expect(mockConvert, 'after a price catch-up the bulk loader served the pairs loaded before from the cache again (Z-14)').toHaveBeenCalledTimes(2);
        expect(
            (mockConvert.mock.calls[1][0] as any[]).map((request) => [request.from_amount.code, request.to, request.date_range]),
            'one POST, one interval per pair, each its whole range',
        ).toEqual([
            ['EUR', 'USD', {start: START, end: END}],
            ['GBP', 'USD', {start: START, end: END}],
        ]);
        expect(fresh.get('EUR-USD')?.map((point) => point.rate)).toEqual([1.2, 1.2, 1.2, 1.2, 1.2]);
        expect(fresh.get('GBP-USD')?.map((point) => point.rate)).toEqual([1.4, 1.4, 1.4, 1.4, 1.4]);

        await ensureFxRangeLoadedBulk(requests);
        expect(mockConvert, 'the fresh answer marks both ranges fetched').toHaveBeenCalledTimes(2);
    });

    it('loadFxRatesAndSignalsBulk without signals asks a range loaded before the catch-up again — then nothing', async () => {
        const card = {slug: 'EUR-USD', start: START, end: END, displayedInverted: false, signals: []};
        mockConvert.mockResolvedValueOnce(converted(...ratesAt('EUR', 'USD', '1.10')));
        await loadFxRatesAndSignalsBulk([card]);
        await loadFxRatesAndSignalsBulk([card]);
        expect(mockConvert, 'premise: without signals a loaded range is served from the cache').toHaveBeenCalledOnce();

        notifyPricesCaughtUp();
        mockConvert.mockResolvedValueOnce(converted(...ratesAt('EUR', 'USD', '1.20')));
        const fresh = await loadFxRatesAndSignalsBulk([card]);

        expect(mockConvert, 'after a price catch-up the FX cards’ loader served the range loaded before from the cache again (Z-14)').toHaveBeenCalledTimes(2);
        expect(
            (mockConvert.mock.calls[1][0] as any[]).map((request) => request.date_range),
            'one interval, the whole range',
        ).toEqual([{start: START, end: END}]);
        expect(fresh.dataBySlug.get('EUR-USD')?.map((point) => point.rate)).toEqual([1.2, 1.2, 1.2, 1.2, 1.2]);

        await loadFxRatesAndSignalsBulk([card]);
        expect(mockConvert, 'the fresh answer marks the range fetched').toHaveBeenCalledTimes(2);
    });

    it('lookupFxRate takes a point the catch-up made stale for a miss: it asks that day once, answers the fresh point the way round it was asked, and asks nothing the next time', async () => {
        const store = getFxStore('EUR-USD');
        store.merge([
            {date: '2026-01-02', rate: 1.25, backwardFillInfo: {actualRateDate: '2026-01-01', daysBack: 1}},
            {date: '2026-01-03', rate: 1.25, backwardFillInfo: {actualRateDate: '2026-01-01', daysBack: 2}},
        ]);
        store.markFetched('2026-01-02', '2026-01-03');
        expect((await lookupFxRate('USD', 'EUR', '2026-01-02'))?.rate, 'premise: before any catch-up a cached point answers, inverted').toBe(0.8);
        expect(mockConvert, 'premise: … without a request').not.toHaveBeenCalled();

        notifyPricesCaughtUp();
        mockConvert.mockResolvedValueOnce({success_count: 1, results: [{conversion_date: '2026-01-02', rate: '1.6', backward_fill_info: null}]} as any);
        const fresh = await lookupFxRate('USD', 'EUR', '2026-01-02');

        expect(mockConvert, 'after a price catch-up the lookup answered from a stale point: a transaction modal compares an exchange with the market rate of before the catch-up (Z-14)').toHaveBeenCalledOnce();
        expect((mockConvert.mock.calls[0][0] as any[])[0], 'one canonical day').toMatchObject({from_amount: {code: 'EUR', amount: '1'}, to: 'USD', date_range: {start: '2026-01-02', end: '2026-01-02'}});
        expect(fresh?.date).toBe('2026-01-02');
        expect(fresh?.rate, 'the fresh rate, inverted for USD→EUR as before').toBeCloseTo(1 / 1.6, 12);
        expect(fresh?.backwardFillInfo, 'the fresh point, not the stale one').toBeNull();
        expect(store.get('2026-01-02')?.rate, 'stored the canonical way round').toBe(1.6);

        expect((await lookupFxRate('EUR', 'USD', '2026-01-02'))?.rate).toBe(1.6);
        expect(mockConvert, 'the day was marked fetched: its next lookup asks nothing').toHaveBeenCalledOnce();

        mockConvert.mockResolvedValueOnce({success_count: 1, results: [{conversion_date: '2026-01-03', rate: '1.6', backward_fill_info: null}]} as any);
        expect((await lookupFxRate('EUR', 'USD', '2026-01-03'))?.rate, 'another stale day of the pair').toBe(1.6);
        expect(mockConvert, 'a lookup makes its own day fresh, not the whole pair: the other stale day is still a miss').toHaveBeenCalledTimes(2);
    });

    it('lookupFxRateSync stays a pure cache read: a stale point is still returned, and nothing is asked', async () => {
        const point = {date: '2026-01-02', rate: 1.25, backwardFillInfo: null};
        getFxStore('EUR-USD').merge([point]);
        getFxStore('EUR-USD').markFetched('2026-01-02', '2026-01-02');

        notifyPricesCaughtUp();

        expect(lookupFxRateSync('EUR', 'USD', '2026-01-02'), 'the sync read of a stale point').toEqual(point);
        expect(lookupFxRateSync('USD', 'EUR', '2026-01-02')?.rate).toBe(0.8);
        expect(mockConvert, 'a sync read never asks').not.toHaveBeenCalled();

        // The control: the point read above was a stale one — a range load of its day asks again.
        mockConvert.mockResolvedValueOnce(converted(...ratesAt('EUR', 'USD', '1.60', ['2026-01-02'])));
        await ensureFxRangeLoaded('EUR-USD', '2026-01-02', '2026-01-02');
        expect(mockConvert, 'the control: the catch-up did not make the point stale, so the sync read above proves nothing (Z-14)').toHaveBeenCalledOnce();
    });

    it('changes nothing on a portfolio mutation or «Aggiorna»: the loaders and the lookup answer from the cache until a price catch-up', async () => {
        loaded('EUR-USD');
        const range = {slug: 'EUR-USD', start: START, end: END};

        // The live poll's write (every 30 s on an asset page that reaches today), a commit, and «Aggiorna».
        notifyPortfolioMutation('POST', '/api/v1/assets/prices/current', {results: [], success_count: 0, errors: []});
        notifyPortfolioMutation('POST', '/api/v1/transactions/commit');
        requestPortfolioRefresh();

        await ensureFxRangeLoaded('EUR-USD', START, END);
        await ensureFxRangeLoadedBulk([range]);
        await loadFxRatesAndSignalsBulk([{...range, displayedInverted: false, signals: []}]);
        expect((await lookupFxRate('EUR', 'USD', '2026-01-03'))?.rate).toBe(1.1);
        expect(mockConvert, 'a portfolio mutation or «Aggiorna» made the FX cache stale: the live poll alone would ask every chart again every 30 s').not.toHaveBeenCalled();

        // The control, in the same store: the catch-up does reach it, so the silence above is the listener's choice.
        notifyPricesCaughtUp();
        mockConvert.mockResolvedValueOnce(converted(...ratesAt('EUR', 'USD', '1.20')));
        await ensureFxRangeLoaded('EUR-USD', START, END);
        expect(mockConvert, 'the control: a price catch-up did not make the range stale either, so the silence above proves nothing (Z-14)').toHaveBeenCalledOnce();
    });
});

// =============================================================================
//  Deliberately left uncovered — two arms that cannot be reached
//
//  ensureFxRangeLoadedBulk    `if (points.length > 0)`   (false arm)
//  loadFxRatesAndSignalsBulk  `if (points.length > 0)`   (false arm)
//      `pointsBySlug` only gains a key through
//      `if (!pointsBySlug.has(slug)) pointsBySlug.set(slug, [])`, which is
//      immediately followed by `.push(point)`. No key can ever hold an empty
//      array, so the guard is never false.
//
// =============================================================================
