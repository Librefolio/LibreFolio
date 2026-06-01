/**
 * Unit tests for fxStoreRegistry — ensureFxRangeLoaded helper.
 *
 * Tests the gap-detection + bulk fetch + merge + return flow.
 * zodiosApi is mocked so no real network calls are made.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

// vi.mock is hoisted by Vitest — the factory runs before any imports below
vi.mock('$lib/api', () => ({
    zodiosApi: {
        convert_currency_bulk_api_v1_fx_currencies_convert_post: vi.fn(),
    },
}));

import {zodiosApi} from '$lib/api';
import {ensureFxRangeLoaded, getFxStore, getRegisteredPairs, removeFxStore} from '../fxStoreRegistry';

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
