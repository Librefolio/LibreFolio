/**
 * currencyStore.suggestCurrency — the client of `GET /api/v1/utilities/currencies/suggest` (lot E-19b1, workstream E).
 *
 * The currency picker shows a stored value that is no ISO 4217 code with a hint, and asks the backend what the value
 * stands for through the store: `suggestCurrency(value)`, a new export of `$lib/stores/reference/currencyStore`.
 *
 * The contract under test:
 *   - it calls `zodiosApi.suggest_currency_api_v1_utilities_currencies_suggest_get({queries: {value}})`, the value as
 *     given, and resolves to `{canonical, suggestion, candidates}` as the backend answered them (CSS-01, CSS-02);
 *   - at most one request per value: two calls with the same value, one after the other or at the same time, make one
 *     request and resolve to the same answer; another value makes its own (CSS-03, CSS-04, CSS-05);
 *   - on an API error it resolves to `{canonical: false, suggestion: null, candidates: []}`, never throws, and does not
 *     cache the failure: a later call asks again, and its success is then cached (CSS-06, CSS-07);
 *   - the operation it calls is the generated client's own: the same alias, on `GET /api/v1/utilities/currencies/suggest`,
 *     with a query parameter `value` (CSS-08; red until the client is generated again, `./dev.py api sync`).
 *
 * `$lib/api` is mocked as the other store tests mock it (`sectorStore.test.ts`, `securityChecksApi.test.ts`): its
 * `zodiosApi` answers the suggestion's operation with a `vi.fn` each case drives, and any other operation rejects,
 * loudly. The store keeps module state (its cache), so every case loads a fresh copy (`vi.resetModules()` and a dynamic
 * import), and `suggestCurrency` is looked up on it when the case runs: until E-19b1 each case fails on its own, naming
 * what is missing, and the type check does not depend on the export landing first.
 *
 * Red today (marked `// red until E-19b1`): the store exports no `suggestCurrency`, and the generated client has no
 * such operation. Pure: the node environment, no request leaves the process.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {api as generatedClient} from '$lib/api/generated';

/** What `suggestCurrency(value)` resolves to. */
type Suggestion = {canonical: boolean; suggestion: string | null; candidates: string[]};
type SuggestCurrency = (value: string) => Promise<Suggestion>;

const mocks = vi.hoisted(() => ({
    operation: 'suggest_currency_api_v1_utilities_currencies_suggest_get',
    suggest: vi.fn().mockName('zodiosApi.suggest_currency_api_v1_utilities_currencies_suggest_get'),
}));

vi.mock('$lib/api', () => {
    const zodiosApi = new Proxy(
        {},
        {
            get(_target, operation) {
                if (typeof operation !== 'string' || operation === 'then') return undefined;
                if (operation === mocks.operation) return mocks.suggest;
                return vi.fn(async () => {
                    throw new Error(`suggestCurrency() reached zodiosApi.${operation}: it may only ask ${mocks.operation}`);
                });
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}, schemas: {}};
});

// --- Fixtures ---------------------------------------------------------------------------------------------------------

const SUGGESTS_EUR: Suggestion = {canonical: false, suggestion: 'EUR', candidates: ['EUR']};
const CANONICAL_EUR: Suggestion = {canonical: true, suggestion: 'EUR', candidates: ['EUR']};
const AMBIGUOUS: Suggestion = {canonical: false, suggestion: null, candidates: ['VED', 'VES']};
const UNKNOWN: Suggestion = {canonical: false, suggestion: null, candidates: []};
/** What a failed request resolves to. */
const FALLBACK: Suggestion = {canonical: false, suggestion: null, candidates: []};

/** A failure as the generated client raises it. */
function apiError(): Error {
    return Object.assign(new Error('Request failed with status code 503'), {isAxiosError: true, response: {status: 503, data: {detail: 'unavailable'}}});
}

/** A promise the test settles by hand: a request still in flight. */
function deferred<T>() {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((settle) => {
        resolve = settle;
    });
    return {promise, resolve};
}

/** `suggestCurrency` of a fresh copy of the store (an empty cache), or the case fails naming what is missing. */
async function freshSuggestCurrency(): Promise<SuggestCurrency> {
    vi.resetModules();
    const store = (await import('./currencyStore')) as unknown as Record<string, unknown>;
    const suggestCurrency = store.suggestCurrency;
    if (typeof suggestCurrency !== 'function') {
        throw new Error('red until E-19b1: $lib/stores/reference/currencyStore exports no suggestCurrency(value) yet');
    }
    return suggestCurrency as SuggestCurrency;
}

beforeEach(() => {
    mocks.suggest.mockReset();
});

afterEach(() => {
    vi.restoreAllMocks();
});

// =====================================================================================================================
describe('suggestCurrency — the request and the answer', () => {
    // red until E-19b1
    it('CSS-01: asks the suggestion operation once, with {queries: {value}}, and resolves to canonical, suggestion and candidates as answered', async () => {
        const suggestCurrency = await freshSuggestCurrency();
        mocks.suggest.mockResolvedValueOnce({...SUGGESTS_EUR});

        const answer = await suggestCurrency('978');

        expect(mocks.suggest).toHaveBeenCalledTimes(1);
        expect(mocks.suggest).toHaveBeenCalledWith(expect.objectContaining({queries: {value: '978'}}));
        expect(answer).toEqual(SUGGESTS_EUR);
    });

    // red until E-19b1
    it.each<[string, Suggestion]>([
        ['EUR', CANONICAL_EUR],
        ['Bolívar Soberano', AMBIGUOUS],
        ['BTC', UNKNOWN],
    ])('CSS-02: %s — the value travels as given, and the answer comes back as the backend gave it', async (value, answered) => {
        const suggestCurrency = await freshSuggestCurrency();
        mocks.suggest.mockResolvedValueOnce({...answered, candidates: [...answered.candidates]});

        const answer = await suggestCurrency(value);

        expect(mocks.suggest).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({queries: {value}}));
        expect(answer).toEqual(answered);
    });
});

// =====================================================================================================================
describe('suggestCurrency — at most one request per value', () => {
    // red until E-19b1
    it('CSS-03: two calls with the same value, one after the other, make one request and give the same answer', async () => {
        const suggestCurrency = await freshSuggestCurrency();
        mocks.suggest.mockResolvedValue({...SUGGESTS_EUR});

        const first = await suggestCurrency('978');
        const second = await suggestCurrency('978');

        expect(mocks.suggest).toHaveBeenCalledTimes(1);
        expect([first, second]).toEqual([SUGGESTS_EUR, SUGGESTS_EUR]);
    });

    // red until E-19b1
    it('CSS-04: two calls with the same value while the first is in flight make one request, and both resolve to its answer', async () => {
        const suggestCurrency = await freshSuggestCurrency();
        const inFlight = deferred<Suggestion>();
        mocks.suggest.mockReturnValue(inFlight.promise);

        const first = suggestCurrency('978');
        const second = suggestCurrency('978');
        inFlight.resolve({...SUGGESTS_EUR});

        await expect(Promise.all([first, second])).resolves.toEqual([SUGGESTS_EUR, SUGGESTS_EUR]);
        expect(mocks.suggest).toHaveBeenCalledTimes(1);
    });

    // red until E-19b1
    it('CSS-05: another value makes a request of its own, with its own value', async () => {
        const suggestCurrency = await freshSuggestCurrency();
        mocks.suggest.mockImplementation(async ({queries}: {queries: {value: string}}) => (queries.value === '978' ? {...SUGGESTS_EUR} : {...AMBIGUOUS, candidates: [...AMBIGUOUS.candidates]}));

        await expect(suggestCurrency('978')).resolves.toEqual(SUGGESTS_EUR);
        await expect(suggestCurrency('Bolívar Soberano')).resolves.toEqual(AMBIGUOUS);
        await expect(suggestCurrency('978')).resolves.toEqual(SUGGESTS_EUR);

        expect(mocks.suggest.mock.calls.map(([options]) => (options as {queries: {value: string}}).queries.value)).toEqual(['978', 'Bolívar Soberano']);
    });
});

// =====================================================================================================================
describe('suggestCurrency — a failed request', () => {
    // red until E-19b1
    it('CSS-06: resolves to {canonical: false, suggestion: null, candidates: []}, without throwing', async () => {
        const suggestCurrency = await freshSuggestCurrency();
        vi.spyOn(console, 'error').mockImplementation(() => {});
        mocks.suggest.mockRejectedValueOnce(apiError());

        await expect(suggestCurrency('978')).resolves.toEqual(FALLBACK);
        expect(mocks.suggest).toHaveBeenCalledTimes(1);
    });

    // red until E-19b1
    it('CSS-07: the failure is not cached: a later call asks again, and the success it gets is then cached', async () => {
        const suggestCurrency = await freshSuggestCurrency();
        vi.spyOn(console, 'error').mockImplementation(() => {});
        mocks.suggest.mockRejectedValueOnce(apiError()).mockResolvedValueOnce({...SUGGESTS_EUR});

        await expect(suggestCurrency('978')).resolves.toEqual(FALLBACK);
        await expect(suggestCurrency('978'), 'the retry gets the answer').resolves.toEqual(SUGGESTS_EUR);
        await expect(suggestCurrency('978'), 'the answer is now cached').resolves.toEqual(SUGGESTS_EUR);

        expect(mocks.suggest).toHaveBeenCalledTimes(2);
    });
});

// =====================================================================================================================
describe('the operation suggestCurrency calls', () => {
    // red until E-19b1 (until the client is generated again: ./dev.py api sync)
    it('CSS-08: the generated client has suggest_currency_api_v1_utilities_currencies_suggest_get, on GET /api/v1/utilities/currencies/suggest, with a query parameter value', () => {
        const route = generatedClient.api.find((endpoint) => endpoint.alias === mocks.operation);

        expect(route, `generated.ts has no operation ${mocks.operation}: run ./dev.py api sync`).toBeDefined();
        expect([route?.method, route?.path]).toEqual(['get', '/api/v1/utilities/currencies/suggest']);
        const parameters = ((route as {parameters?: unknown} | undefined)?.parameters ?? []) as ReadonlyArray<{name: string; type: string}>;
        expect(parameters.map(({name, type}) => `${type}:${name}`)).toContain('Query:value');
    });
});
