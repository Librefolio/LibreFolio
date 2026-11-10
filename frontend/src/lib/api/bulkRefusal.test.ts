/**
 * The sentence of a bulk request refused as too large (lot X-R58) — `src/lib/api/bulkRefusal.ts`.
 *
 * Since Z-25 `POST /api/v1/assets/prices/query` and `POST /api/v1/fx/currencies/convert` refuse a request past the
 * backend's caps with a 422 whose `detail` is coded (`backend/app/utils/date_range_limits.py`):
 *
 *   - `{code: 'bulk_too_many_items', message, max_items, items}`;
 *   - `{code: 'bulk_too_many_days', message, max_item_days, item_days}` — for the FX convert `item_days` may be a lower
 *     bound: the conversions are counted one by one, and the count stops once past the budget.
 *
 * The lists send those requests through `sendBulkBatches` (Z-27), which splits a batch refused for its days and fails on
 * what it cannot split. Until X-R58 the failure reached the user as nothing at all: the pages only logged it, and the
 * cards stayed without values. `bulkRefusalMessage(error, t)` is the sentence they show instead, in an error toast:
 *
 *   - refused for its items → `t('common.bulkRefusal.tooManyItems', {values: {max: max_items, count: items}})`;
 *   - refused for its days → `t('common.bulkRefusal.tooManyDays', {values: {max: max_item_days}})`, and no count: for
 *     the FX convert it may be a bound, not the request's total;
 *   - anything else → null, and `t` is not called: every other failure stays as the page handles it.
 *
 * A refusal is read from whatever carries it — the raw AxiosError the generated client passes on (`zodios-client.ts`),
 * or any axios-like object with a `response` — and each code needs its own two numbers, finite, with a cap above zero.
 * Every near miss gives null: another status, another code, a missing, non-numeric, non-finite or non-positive number, a
 * detail that is not a coded object, no response, no object at all. So does a code naming a property every object
 * inherits (`constructor`, `toString`…): a table of sentences indexed by the code would find one there.
 *
 * A pure module in the default `node` environment: `t` is a recording fake, and every error is built here.
 *
 * Red first: until the module exists the file fails at its import.
 */
import {AxiosError, AxiosHeaders, type AxiosResponse, type InternalAxiosRequestConfig} from 'axios';
import {describe, expect, it, vi} from 'vitest';
import {bulkRefusalMessage} from './bulkRefusal';

// =============================================================================
//  Fakes
// =============================================================================

/** The catalogue's sentence for a request refused for its items. */
const ITEMS_KEY = 'common.bulkRefusal.tooManyItems';
/** The catalogue's sentence for a request refused for its days. */
const DAYS_KEY = 'common.bulkRefusal.tooManyDays';

const REQUEST = {headers: new AxiosHeaders()} as InternalAxiosRequestConfig;

/** A failed response as the generated client raises it: the raw AxiosError its response interceptor passes on (`zodios-client.ts`). */
function axiosRefusal(status: number, data: unknown): AxiosError {
    const response: AxiosResponse = {status, statusText: '', headers: {'content-type': 'application/json'}, config: REQUEST, request: {}, data};
    return new AxiosError(`Request failed with status code ${status}`, status < 500 ? AxiosError.ERR_BAD_REQUEST : AxiosError.ERR_BAD_RESPONSE, REQUEST, {}, response);
}

/** The same failure on any axios-like object: a `response` with its status and data, nothing else. */
function axiosLike(status: number, data: unknown): {response: {status: number; data: unknown}} {
    return {response: {status, data}};
}

/** The `detail` of the item cap's 422, worded as the backend words it (`bulk_too_many_items_detail`). */
function itemsDetail(items: number, maxItems: number): Record<string, unknown> {
    return {code: 'bulk_too_many_items', message: `A bulk request may hold at most ${maxItems} items, not ${items}`, max_items: maxItems, items};
}

/** The `detail` of the item-days budget's 422 (`bulk_too_many_days_detail`): the FX convert's count is «at least». */
function daysDetail(itemDays: number, maxItemDays: number, atLeast = false): Record<string, unknown> {
    return {code: 'bulk_too_many_days', message: `A bulk request may build at most ${maxItemDays} per-day points, and this one would build ${atLeast ? 'at least ' : ''}${itemDays}`, max_item_days: maxItemDays, item_days: itemDays};
}

/** `detail` without `key`: a refusal missing one of its fields. */
function without(detail: Record<string, unknown>, key: string): Record<string, unknown> {
    const copy = {...detail};
    delete copy[key];
    return copy;
}

/**
 * A `t` that records every call and answers each with a sentence of its own, numbered: what the function returns can be
 * told apart from any other string. Its options are typed as wide as a call can pass them.
 */
function recordingT() {
    let answered = 0;
    return vi.fn((key: string, _options?: unknown): string => `sentence ${++answered} for ${key}`);
}

/** The refusals the near misses below are made from: realistic numbers, the FX wording for the days. */
const ITEMS = itemsDetail(1_001, 1_000);
const DAYS = daysDetail(1_234_567, 1_000_000, true);

// =============================================================================
//  bulkRefusalMessage
// =============================================================================

describe('bulkRefusalMessage', () => {
    describe('a request refused for its items (bulk_too_many_items)', () => {
        it('asks the catalogue once for the items sentence, with the cap and the count, and returns its answer as it is', () => {
            const t = recordingT();
            const sentence = bulkRefusalMessage(axiosRefusal(422, {detail: itemsDetail(1_001, 1_000)}), t);
            expect(t.mock.calls, 'one call: the items sentence, with max_items as max and items as count').toStrictEqual([[ITEMS_KEY, {values: {max: 1_000, count: 1_001}}]]);
            expect(sentence, 'the catalogue’s answer, unchanged').toBe(`sentence 1 for ${ITEMS_KEY}`);
        });

        it('reads it from any axios-like error, with the numbers that refusal carries', () => {
            const t = recordingT();
            const sentence = bulkRefusalMessage(axiosLike(422, {detail: itemsDetail(73_456, 2_500)}), t);
            expect(t.mock.calls).toStrictEqual([[ITEMS_KEY, {values: {max: 2_500, count: 73_456}}]]);
            expect(sentence).toBe(`sentence 1 for ${ITEMS_KEY}`);
        });
    });

    describe('a request refused for its days (bulk_too_many_days)', () => {
        it('asks the catalogue once for the days sentence, with the budget alone — the FX count may be a bound — and returns its answer as it is', () => {
            const t = recordingT();
            const sentence = bulkRefusalMessage(axiosRefusal(422, {detail: daysDetail(1_234_567, 1_000_000, true)}), t);
            expect(t.mock.calls, 'one call: the days sentence, with max_item_days as max and no count at all').toStrictEqual([[DAYS_KEY, {values: {max: 1_000_000}}]]);
            expect(sentence, 'the catalogue’s answer, unchanged').toBe(`sentence 1 for ${DAYS_KEY}`);
        });

        it('reads it from any axios-like error, with the budget that refusal carries — and still no count, even the asset query’s exact one', () => {
            const t = recordingT();
            const sentence = bulkRefusalMessage(axiosLike(422, {detail: daysDetail(4_000_001, 3_000_000)}), t);
            expect(t.mock.calls).toStrictEqual([[DAYS_KEY, {values: {max: 3_000_000}}]]);
            expect(sentence).toBe(`sentence 1 for ${DAYS_KEY}`);
        });
    });

    describe('anything else', () => {
        const NEAR_MISSES: Array<[string, unknown]> = [
            // Another status, the same coded details.
            ['the items refusal’s detail on a 400', axiosRefusal(400, {detail: ITEMS})],
            ['the items refusal’s detail on a 413', axiosRefusal(413, {detail: ITEMS})],
            ['the days refusal’s detail on a 500', axiosRefusal(500, {detail: DAYS})],
            ['the days refusal’s detail on an axios-like 500', axiosLike(500, {detail: DAYS})],
            ['the items refusal’s detail on a response without a status', {response: {data: {detail: ITEMS}}}],
            // Another code.
            ['the period changes’ own 422, period_changes_too_many_days', axiosRefusal(422, {detail: {code: 'period_changes_too_many_days', message: 'A fixed-period changes request may value at most 5 distinct as_of days, not 6', field: 'as_of', max_days: 5, days: 6}})],
            ['another code carrying every number of both refusals', axiosRefusal(422, {detail: {code: 'bulk_too_many_writes', max_items: 1_000, items: 1_001, max_item_days: 1_000_000, item_days: 1_234_567}})],
            ['the items code in capitals', axiosRefusal(422, {detail: {...ITEMS, code: 'BULK_TOO_MANY_ITEMS'}})],
            ['the items refusal without a code', axiosRefusal(422, {detail: without(ITEMS, 'code')})],
            ['the days refusal with a numeric code', axiosRefusal(422, {detail: {...DAYS, code: 422}})],
            // A number missing: each code reads its own two.
            ['the items refusal without items', axiosRefusal(422, {detail: without(ITEMS, 'items')})],
            ['the items refusal without max_items', axiosRefusal(422, {detail: without(ITEMS, 'max_items')})],
            ['the days refusal without item_days', axiosRefusal(422, {detail: without(DAYS, 'item_days')})],
            ['the days refusal without max_item_days', axiosRefusal(422, {detail: without(DAYS, 'max_item_days')})],
            ['the items code with the numbers of the days refusal', axiosRefusal(422, {detail: {code: 'bulk_too_many_items', max_item_days: 1_000_000, item_days: 1_234_567}})],
            ['the days code with the numbers of the items refusal', axiosRefusal(422, {detail: {code: 'bulk_too_many_days', max_items: 1_000, items: 1_001}})],
            // A number that is not one.
            ['the items refusal’s max_items as a string', axiosRefusal(422, {detail: {...ITEMS, max_items: '1000'}})],
            ['the items refusal’s items as a string', axiosRefusal(422, {detail: {...ITEMS, items: '1001'}})],
            ['the days refusal’s max_item_days as a string', axiosRefusal(422, {detail: {...DAYS, max_item_days: '1000000'}})],
            ['the days refusal’s item_days as a string', axiosRefusal(422, {detail: {...DAYS, item_days: '1234567'}})],
            ['the items refusal’s items null', axiosRefusal(422, {detail: {...ITEMS, items: null}})],
            ['the days refusal’s max_item_days null', axiosRefusal(422, {detail: {...DAYS, max_item_days: null}})],
            // A number that is not finite.
            ['the items refusal’s max_items Infinity', axiosRefusal(422, {detail: {...ITEMS, max_items: Infinity}})],
            ['the items refusal’s items Infinity', axiosRefusal(422, {detail: {...ITEMS, items: Infinity}})],
            ['the items refusal’s items NaN', axiosRefusal(422, {detail: {...ITEMS, items: NaN}})],
            ['the days refusal’s max_item_days Infinity', axiosRefusal(422, {detail: {...DAYS, max_item_days: Infinity}})],
            ['the days refusal’s max_item_days NaN', axiosRefusal(422, {detail: {...DAYS, max_item_days: NaN}})],
            ['the days refusal’s item_days Infinity', axiosRefusal(422, {detail: {...DAYS, item_days: Infinity}})],
            ['the days refusal’s item_days NaN', axiosRefusal(422, {detail: {...DAYS, item_days: NaN}})],
            // A cap that is not above zero.
            ['the items refusal with max_items 0', axiosRefusal(422, {detail: {...ITEMS, max_items: 0}})],
            ['the items refusal with a negative max_items', axiosRefusal(422, {detail: {...ITEMS, max_items: -1_000}})],
            ['the days refusal with max_item_days 0', axiosRefusal(422, {detail: {...DAYS, max_item_days: 0}})],
            ['the days refusal with a negative max_item_days', axiosRefusal(422, {detail: {...DAYS, max_item_days: -1}})],
            // A detail that is not a coded object.
            ['a 422 whose detail is a string', axiosRefusal(422, {detail: 'A bulk request may hold at most 1000 items, not 1001'})],
            ['a 422 of request validation, a list of issues', axiosRefusal(422, {detail: [{type: 'too_long', loc: ['body'], msg: 'List should have at most 1000 items after validation, not 1001'}]})],
            ['a 422 whose detail is null', axiosRefusal(422, {detail: null})],
            ['a 422 whose body is the items detail itself, unwrapped', axiosRefusal(422, ITEMS)],
            ['a 422 whose body is text', axiosRefusal(422, 'Unprocessable Entity')],
            ['a 422 without a body', axiosRefusal(422, undefined)],
            // No response.
            ['a request that reached no server', new AxiosError('Network Error', AxiosError.ERR_NETWORK, REQUEST, {})],
            ['an axios-like error whose response is null', {response: null}],
            ['a plain Error naming the code', new Error('bulk_too_many_items')],
            ['an empty object', {}],
            ['null', null],
            ['undefined', undefined],
            // No object at all.
            ['the code as a bare string', 'bulk_too_many_items'],
            ['a bare status', 422],
            ['true', true],
        ];

        it.each(NEAR_MISSES)('answers null for %s, and asks the catalogue nothing', (_label, error) => {
            const t = recordingT();
            expect(bulkRefusalMessage(error, t)).toBeNull();
            expect(t).not.toHaveBeenCalled();
        });

        /** Every number of both refusals, valid: under `code` alone the detail decides nothing else. */
        const everyNumber = (code: string): Record<string, unknown> => ({code, message: 'A bulk request may hold at most 1000 items, not 1001', max_items: 1_000, items: 1_001, max_item_days: 1_000_000, item_days: 1_234_567});

        it.each(['constructor', 'toString', 'valueOf', 'hasOwnProperty', '__proto__'])('answers null for the code %s — a property every object inherits — though the detail carries every number of both refusals', (code) => {
            const t = recordingT();
            expect(bulkRefusalMessage(axiosRefusal(422, {detail: everyNumber(code)}), t)).toBeNull();
            expect(t).not.toHaveBeenCalled();
        });

        it.each<[string, string, Record<string, number>]>([
            ['bulk_too_many_items', ITEMS_KEY, {max: 1_000, count: 1_001}],
            ['bulk_too_many_days', DAYS_KEY, {max: 1_000_000}],
        ])('control: the same detail under %s gives that refusal’s sentence — the code alone decided the nulls above', (code, key, values) => {
            const t = recordingT();
            expect(bulkRefusalMessage(axiosRefusal(422, {detail: everyNumber(code)}), t)).toBe(`sentence 1 for ${key}`);
            expect(t.mock.calls).toStrictEqual([[key, {values}]]);
        });
    });
});
