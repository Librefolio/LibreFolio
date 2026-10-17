/**
 * The sentence of a write the server refused (lot X-R46, release 1.3, workstream X) — `src/lib/api/writeRefusal.ts`.
 *
 * Both data editors — the rates of a pair (`FxDataEditorSection.svelte`) and the prices of an asset
 * (`AssetDataEditorSection.svelte`) — answer a refused save with Axios's own `e.message`, «Request failed with status
 * code 422», and count every row they sent as saved, the refused ones included. The server says more, with codes:
 *
 *   - 422 `{code: 'date_out_of_range', message, params: {min, max}, items, count}` (X-R65, `date_out_of_range_detail` in
 *     `backend/app/utils/date_range_limits.py`): the items are `{asset_id, dates}` for prices and `{index, date}` for
 *     rates, at most 10 of each; `count` is every date refused;
 *   - 422 `{code: 'price_currency_mismatch', message, items: [{asset_id, expected, found, dates}], count}` (X-R71,
 *     `price_currency_mismatch_detail` in `backend/app/services/assets/price_store.py`), with the same caps;
 *   - 422 `{code: 'bulk_too_many_items', message, max_items, items}` (MF-SEC9a, `bulk_too_many_items_detail` in
 *     `backend/app/utils/date_range_limits.py`): a write of rates, and the deletions of either editor, take at most
 *     10 000 items (`MAX_BULK_WRITE_ITEMS`), and an FX CSV import can hold more; and 422 `bulk_too_many_days` (Z-25), a
 *     read's refusal for too many daily values, which a write never meets;
 *   - 400 `{code: 'fx_rates_refused', message, rejected: [{index, date, reason}]}` when every rate is refused (X-R46;
 *     until now a string detail, «All rates failed: …», which stays as its `message`);
 *   - and, on a 200, the rows refused one by one, `{date, reason}` (`FAPriceRejection`, `FXRateRejection`, X-R46).
 *
 * The contract under test:
 *
 *   - `writeRefusalMessage(error, t, dateLabel?)`: one sentence per coded refusal, null for anything else, and then `t`
 *     is not called. `date_out_of_range` → `common.writeRefusal.dateOutOfRange` with `{count, min, max, dates}`;
 *     `price_currency_mismatch` → `common.writeRefusal.currencyMismatch` with `{count, expected, found, dates}`,
 *     `expected` the first item's, `found` every item's currencies once each, first seen first; `bulk_too_many_items`
 *     → `common.writeRefusal.tooManyItems` with `{max: max_items, count: items}`, a save's own sentence, no longer
 *     `bulkRefusalMessage`'s — X-R58's `common.bulkRefusal.tooManyItems`, «Some values could not be loaded…», is a
 *     read's, and the docs-writer found it on a refused FX import; `bulk_too_many_days` → still the very string
 *     `bulkRefusalMessage` gives; `fx_rates_refused` → `rejectedMessage` of its rows. Each code is read on its own
 *     status, as in `bulkRefusal.ts`. A non-finite `count`, a missing bound, `items` that are not a list, no date to
 *     name → null; so does a `bulk_too_many_items` whose `items` is not a finite number, or whose `max_items` is not a
 *     finite number above 0.
 *   - `rejectedMessage(rejected, t, dateLabel?)`: null for no row, else `common.writeRefusal.notSaved` with
 *     `{count, items}`; a row reads «<date> (<reason>)», the reason `common.writeRefusal.reason.<reason>` for one of
 *     `REJECTION_REASONS` and `common.writeRefusal.reason.other` for any other.
 *   - `saveErrorText(error, t, dateLabel?)`: that sentence, else `extractErrorMessage(error, t('common.unknownError'))`
 *     (`utils/trySave.ts`) — the server's own text whenever the error carries one, never Axios's generic message.
 *   - A list shows at most 5 entries, in the order given, joined by «, », then a space and `common.writeRefusal.more`
 *     with `n` the entries not shown: for a refusal with a `count`, `count` minus those shown, since the backend lists at
 *     most 10 dates per item. Every date and bound goes through `dateLabel`, the ISO date itself by default (as in
 *     `eventSaveErrorMessage`).
 *   - `REJECTION_REASONS` is exactly the backend's reasons — a literal here: the schemas that will declare them do not
 *     exist yet.
 *
 * A pure module in the default `node` environment. `t` is a fake that answers the key and the values it was given as
 * JSON — names sorted, so the order the module builds them in does not matter — and a sentence inside another (the
 * «more», a reason) shows nested in its values: every assertion reads what was asked of the catalogue, never its text.
 * Every error is built here, shaped as the backend sends it.
 *
 * Red first: before X-R46 `./writeRefusal` did not exist, and the file failed at its import. Red again until the
 * module gives `bulk_too_many_items` a save's own sentence: the three cases that expect
 * `common.writeRefusal.tooManyItems` got X-R58's.
 */
import {AxiosError, AxiosHeaders, type AxiosResponse, type InternalAxiosRequestConfig} from 'axios';
import {describe, expect, it, vi} from 'vitest';
import {extractErrorMessage} from '$lib/utils/trySave';
import {bulkRefusalMessage} from './bulkRefusal';
import {REJECTION_REASONS, rejectedMessage, saveErrorText, writeRefusalMessage, type Rejection} from './writeRefusal';

// =============================================================================
//  The backend's reasons
// =============================================================================

/**
 * Why the backend refuses one row of a write (X-R46), as its schemas will declare them: `FAPriceRejection.reason` in
 * `backend/app/schemas/prices.py`, `FXRateRejection.reason` in `backend/app/schemas/fx.py` — neither exists yet. A
 * literal on purpose: when the backend gains a reason, this list and `REJECTION_REASONS` change together, with the
 * reason's sentence in the four catalogues; until then the new reason reads as «other».
 */
const BACKEND_REJECTION_REASONS = [
    // FAPriceRejection.reason — backend/app/schemas/prices.py
    'ohlc_inconsistent',
    'date_out_of_range',
    'value_not_storable',
    // FXRateRejection.reason — backend/app/schemas/fx.py
    'same_currency',
    'rate_not_storable',
    'invalid_rate',
    'internal_error',
];

// =============================================================================
//  Fakes
// =============================================================================

type Values = Record<string, string | number>;

const OUT_OF_RANGE_KEY = 'common.writeRefusal.dateOutOfRange';
const MISMATCH_KEY = 'common.writeRefusal.currencyMismatch';
/** A save refused for its items: a sentence of its own. */
const TOO_MANY_ITEMS_KEY = 'common.writeRefusal.tooManyItems';
/** X-R58's sentence for a read refused for its items, «Some values could not be loaded…»: never a save's. */
const READ_TOO_MANY_ITEMS_KEY = 'common.bulkRefusal.tooManyItems';
const NOT_SAVED_KEY = 'common.writeRefusal.notSaved';
const MORE_KEY = 'common.writeRefusal.more';
const REASON_KEY_PREFIX = 'common.writeRefusal.reason.';
const UNKNOWN_ERROR_KEY = 'common.unknownError';

/** What the fake `t` answers: the key, then its values as JSON with the names sorted; the key alone when it has none. */
function answer(key: string, values?: Values): string {
    const names = Object.keys(values ?? {}).sort();
    return names.length > 0 ? `${key} ${JSON.stringify(values, names)}` : key;
}

/** A stand-in for svelte-i18n's `$t`: it records every call and answers what it was asked (`answer`), never catalogue text. */
function fakeT() {
    return vi.fn((key: string, options?: {values?: Values}): string => answer(key, options?.values));
}

/** The «and n more» after a cut list, as `fakeT` answers it. */
const more = (n: number): string => answer(MORE_KEY, {n});

/** The sentence of a reason, as `fakeT` answers it. */
const reasonText = (reason: string): string => answer(`${REASON_KEY_PREFIX}${reason}`);

/** A refused row as a list shows it: its date as written (`dateLabel`'s answer, or the ISO date), then its reason's sentence in brackets. */
const refusedRow = (shownDate: string, reason: string): string => `${shownDate} (${reasonText(reason)})`;

/** The caller's way of writing a date: visible in the sentence, so a date or a bound that skipped it shows. */
const dateLabel = (iso: string): string => `D<${iso}>`;

/** Axios's own text for a refused request: what the editors show today, and what nobody must read when the server said more. */
const GENERIC_422 = 'Request failed with status code 422';

const REQUEST = {headers: new AxiosHeaders()} as InternalAxiosRequestConfig;

/** A failed response as the generated client raises it: the raw AxiosError its response interceptor passes on (`zodios-client.ts`). */
function axiosRefusal(status: number, data: unknown): AxiosError {
    const response: AxiosResponse = {status, statusText: '', headers: {'content-type': 'application/json'}, config: REQUEST, request: {}, data};
    return new AxiosError(`Request failed with status code ${status}`, status < 500 ? AxiosError.ERR_BAD_REQUEST : AxiosError.ERR_BAD_RESPONSE, REQUEST, {}, response);
}

/** The same failure on any axios-like object: Axios's generic message, and a `response` with its status and data. */
function axiosLike(status: number, data: unknown): {message: string; response: {status: number; data: unknown}} {
    return {message: `Request failed with status code ${status}`, response: {status, data}};
}

/** `detail` without `key`: a refusal missing one of its fields. */
function without(detail: Record<string, unknown>, key: string): Record<string, unknown> {
    const copy = {...detail};
    delete copy[key];
    return copy;
}

/** `n` consecutive days of `month` (`YYYY-MM`), from the 1st. */
function days(month: string, n: number): string[] {
    return Array.from({length: n}, (_, i) => `${month}-${String(i + 1).padStart(2, '0')}`);
}

/** The items a rates write is refused with for `dates`: `{index, date}`, indexed in order. */
function rateItems(dates: string[]): Array<{index: number; date: string}> {
    return dates.map((date, index) => ({index, date}));
}

// =============================================================================
//  The refusals, as the backend words them
// =============================================================================

/** The bounds of a stored date (`stored_date_bounds()`): 1900-01-01, and the server's tomorrow. */
const MIN = '1900-01-01';
const MAX = '2026-10-18';

/** The 422 for dates outside the bounds (`date_out_of_range_detail`): the prices' items `{asset_id, dates}`, the rates' `{index, date}`. */
function outOfRange(items: unknown[], count: number): Record<string, unknown> {
    return {code: 'date_out_of_range', message: `Dates must lie between ${MIN} and ${MAX}: ${count} ${count === 1 ? 'does' : 'do'} not`, params: {min: MIN, max: MAX}, items, count};
}

/** The 422 for prices in a currency other than their asset's (`price_currency_mismatch_detail`, X-R71). */
function currencyMismatch(items: unknown[], count: number): Record<string, unknown> {
    return {code: 'price_currency_mismatch', message: `Prices must be in their asset's currency: ${count} are not`, items, count};
}

/** The backend's text when every rate of a write failed: the string `detail` until X-R46, the coded refusal's `message` after. */
const ALL_RATES_FAILED = 'All rates failed: Rate 0: Base and quote must be different (got EUR); Rate 1: Failed: internal error';

/** The 400 for a rates write whose every rate was refused (X-R46): the same text, and the rows refused with their reasons. */
function ratesRefused(rejected: unknown[]): Record<string, unknown> {
    return {code: 'fx_rates_refused', message: ALL_RATES_FAILED, rejected};
}

/** The 422 of a write too large (`bulk_too_many_items_detail`, MF-SEC9a), worded as the backend words it. */
function tooManyItems(items: number, maxItems: number): Record<string, unknown> {
    return {code: 'bulk_too_many_items', message: `A bulk request may hold at most ${maxItems} items, not ${items}`, max_items: maxItems, items};
}

/** An FX CSV import of 10 001 rates: a write takes at most 10 000 items (`MAX_BULK_WRITE_ITEMS`). */
const BULK_ITEMS = tooManyItems(10_001, 10_000);
/** The 422 of a read that would build too many daily values (`bulk_too_many_days_detail`, Z-25): a write never meets it. */
const BULK_DAYS = {code: 'bulk_too_many_days', message: 'A bulk request may build at most 1000000 per-day points, and this one would build 1234567', max_item_days: 1_000_000, item_days: 1_234_567};

/** The 500 of `POST /assets/prices` for an error nobody foresaw: the answer never echoes it (MF-SEC9a). */
const PRICES_INTERNAL_ERROR = 'Internal error while saving prices';

/** A 422 of request validation: a date nobody can read, typed into the prices editor. */
const VALIDATION_ISSUES = [{type: 'date_from_datetime_parsing', loc: ['body', 0, 'prices', 0, 'date'], msg: 'Input should be a valid date or datetime, month value is outside expected range of 1-12', input: '2026-13-01'}];

/** A refusal of the events, the other half of the asset editor: coded under `error_code`, read by `eventSaveErrorMessage`. */
const EVENT_REFUSAL = {error_code: 'EVENT_KEY_CONFLICT', message: 'An INTEREST event already exists on 2026-03-15', params: {asset_id: 7, item_index: 0, date: '2026-03-15', type: 'INTEREST'}};

/** The sentence the events branch of `AssetDataEditorSection.handleSave()` throws, already translated by `eventSaveErrorMessage`. */
const EVENT_SENTENCE = 'An «Interest» event on 2026-03-15 already exists: change its date or its type';

/** The refusals the near misses are made from: one date each. */
const PRICES_OUT_OF_RANGE = outOfRange([{asset_id: 7, dates: ['2062-03-05']}], 1);
const MISMATCH = currencyMismatch([{asset_id: 7, expected: 'EUR', found: ['USD'], dates: ['2026-01-05']}], 1);
const RATES_REFUSED = ratesRefused([{index: 0, date: '2026-01-05', reason: 'same_currency'}]);

// =============================================================================
//  writeRefusalMessage
// =============================================================================

describe('writeRefusalMessage', () => {
    describe('dates out of range (422 date_out_of_range)', () => {
        it('prices: the dates of every asset, flattened in order, each through dateLabel — and the bounds through dateLabel too', () => {
            const t = fakeT();
            const error = axiosRefusal(422, {
                detail: outOfRange(
                    [
                        {asset_id: 7, dates: ['2062-03-05', '2062-03-06']},
                        {asset_id: 9, dates: ['1899-12-31']},
                    ],
                    3,
                ),
            });
            expect(writeRefusalMessage(error, t, dateLabel)).toBe(answer(OUT_OF_RANGE_KEY, {count: 3, min: 'D<1900-01-01>', max: 'D<2026-10-18>', dates: 'D<2062-03-05>, D<2062-03-06>, D<1899-12-31>'}));
        });

        it('rates: the date of every item, {index, date}', () => {
            const t = fakeT();
            const error = axiosRefusal(422, {
                detail: outOfRange(
                    [
                        {index: 0, date: '2062-01-02'},
                        {index: 3, date: '0001-01-01'},
                    ],
                    2,
                ),
            });
            expect(writeRefusalMessage(error, t, dateLabel)).toBe(answer(OUT_OF_RANGE_KEY, {count: 2, min: 'D<1900-01-01>', max: 'D<2026-10-18>', dates: 'D<2062-01-02>, D<0001-01-01>'}));
        });

        it('keeps the order the server gave — neither by date nor by index', () => {
            const t = fakeT();
            const error = axiosRefusal(422, {
                detail: outOfRange(
                    [
                        {index: 4, date: '2062-05-01'},
                        {index: 1, date: '1899-12-31'},
                        {index: 2, date: '2062-01-01'},
                    ],
                    3,
                ),
            });
            expect(writeRefusalMessage(error, t, dateLabel)).toBe(answer(OUT_OF_RANGE_KEY, {count: 3, min: 'D<1900-01-01>', max: 'D<2026-10-18>', dates: 'D<2062-05-01>, D<1899-12-31>, D<2062-01-01>'}));
        });

        it('shows five dates at most, across the assets, then «more» with the dates not shown', () => {
            const t = fakeT();
            const error = axiosRefusal(422, {
                detail: outOfRange(
                    [
                        {asset_id: 7, dates: ['2062-01-05', '2062-01-06', '2062-01-07']},
                        {asset_id: 9, dates: ['2062-02-02', '2062-02-03', '2062-02-04', '2062-02-05']},
                    ],
                    7,
                ),
            });
            expect(writeRefusalMessage(error, t, dateLabel)).toBe(answer(OUT_OF_RANGE_KEY, {count: 7, min: 'D<1900-01-01>', max: 'D<2026-10-18>', dates: `D<2062-01-05>, D<2062-01-06>, D<2062-01-07>, D<2062-02-02>, D<2062-02-03> ${more(2)}`}));
        });

        it('counts the dates not shown from count, not from the list: the backend lists at most 10 dates per asset', () => {
            const t = fakeT();
            const error = axiosRefusal(422, {detail: outOfRange([{asset_id: 7, dates: days('2062-03', 10)}], 23)});
            expect(writeRefusalMessage(error, t, dateLabel)).toBe(answer(OUT_OF_RANGE_KEY, {count: 23, min: 'D<1900-01-01>', max: 'D<2026-10-18>', dates: `D<2062-03-01>, D<2062-03-02>, D<2062-03-03>, D<2062-03-04>, D<2062-03-05> ${more(18)}`}));
        });

        it.each<[number, string]>([
            [5, 'D<2062-03-01>, D<2062-03-02>, D<2062-03-03>, D<2062-03-04>, D<2062-03-05>'],
            [6, `D<2062-03-01>, D<2062-03-02>, D<2062-03-03>, D<2062-03-04>, D<2062-03-05> ${more(1)}`],
        ])('%i dates: the cut falls after the fifth', (n, dates) => {
            const t = fakeT();
            const error = axiosRefusal(422, {detail: outOfRange(rateItems(days('2062-03', n)), n)});
            expect(writeRefusalMessage(error, t, dateLabel)).toBe(answer(OUT_OF_RANGE_KEY, {count: n, min: 'D<1900-01-01>', max: 'D<2026-10-18>', dates}));
        });

        it('without dateLabel: the dates and the bounds as the server wrote them, ISO', () => {
            const t = fakeT();
            const error = axiosRefusal(422, {
                detail: outOfRange(
                    [
                        {asset_id: 7, dates: ['2062-03-05']},
                        {asset_id: 9, dates: ['1899-12-31']},
                    ],
                    2,
                ),
            });
            expect(writeRefusalMessage(error, t)).toBe(answer(OUT_OF_RANGE_KEY, {count: 2, min: '1900-01-01', max: '2026-10-18', dates: '2062-03-05, 1899-12-31'}));
        });

        it('reads it from any axios-like error', () => {
            const t = fakeT();
            const error = axiosLike(422, {detail: outOfRange([{index: 0, date: '2062-01-02'}], 1)});
            expect(writeRefusalMessage(error, t, dateLabel)).toBe(answer(OUT_OF_RANGE_KEY, {count: 1, min: 'D<1900-01-01>', max: 'D<2026-10-18>', dates: 'D<2062-01-02>'}));
        });
    });

    describe('prices in another currency (422 price_currency_mismatch)', () => {
        it('the first item’s currency as expected, every currency found once, first seen first, and every date in order through dateLabel', () => {
            const t = fakeT();
            const error = axiosRefusal(422, {
                detail: currencyMismatch(
                    [
                        {asset_id: 7, expected: 'EUR', found: ['USD', 'GBP'], dates: ['2026-01-05', '2026-01-06']},
                        {asset_id: 9, expected: 'CHF', found: ['GBP', 'USD', 'JPY'], dates: ['2026-02-02']},
                    ],
                    3,
                ),
            });
            expect(writeRefusalMessage(error, t, dateLabel)).toBe(answer(MISMATCH_KEY, {count: 3, expected: 'EUR', found: 'USD, GBP, JPY', dates: 'D<2026-01-05>, D<2026-01-06>, D<2026-02-02>'}));
        });

        it('shows five dates at most, across the items, then «more» with the dates not shown', () => {
            const t = fakeT();
            const error = axiosRefusal(422, {
                detail: currencyMismatch(
                    [
                        {asset_id: 7, expected: 'EUR', found: ['USD'], dates: ['2026-01-05', '2026-01-06', '2026-01-07']},
                        {asset_id: 9, expected: 'EUR', found: ['USD'], dates: ['2026-02-02', '2026-02-03', '2026-02-04']},
                    ],
                    6,
                ),
            });
            expect(writeRefusalMessage(error, t, dateLabel)).toBe(answer(MISMATCH_KEY, {count: 6, expected: 'EUR', found: 'USD', dates: `D<2026-01-05>, D<2026-01-06>, D<2026-01-07>, D<2026-02-02>, D<2026-02-03> ${more(1)}`}));
        });

        it('counts the dates not shown from count, as for the dates out of range: the backend lists at most 10 dates per item', () => {
            const t = fakeT();
            const error = axiosRefusal(422, {detail: currencyMismatch([{asset_id: 7, expected: 'EUR', found: ['USD'], dates: days('2026-01', 10)}], 14)});
            expect(writeRefusalMessage(error, t, dateLabel)).toBe(answer(MISMATCH_KEY, {count: 14, expected: 'EUR', found: 'USD', dates: `D<2026-01-01>, D<2026-01-02>, D<2026-01-03>, D<2026-01-04>, D<2026-01-05> ${more(9)}`}));
        });

        it('without dateLabel: the dates as the server wrote them, ISO', () => {
            const t = fakeT();
            const error = axiosRefusal(422, {detail: currencyMismatch([{asset_id: 7, expected: 'EUR', found: ['USD'], dates: ['2026-01-05', '2026-01-06']}], 2)});
            expect(writeRefusalMessage(error, t)).toBe(answer(MISMATCH_KEY, {count: 2, expected: 'EUR', found: 'USD', dates: '2026-01-05, 2026-01-06'}));
        });
    });

    describe('a write too large (422 bulk_too_many_items): a save’s own sentence, no longer X-R58’s', () => {
        it('asks the catalogue once, for common.writeRefusal.tooManyItems with max_items as max and items as count, and returns its answer as it is — never X-R58’s sentence, which is a read’s', () => {
            const t = fakeT();
            const sentence = writeRefusalMessage(axiosRefusal(422, {detail: BULK_ITEMS}), t, dateLabel);
            expect(
                t.mock.calls.map(([key]) => key),
                'never X-R58’s «Some values could not be loaded…»: a save loads nothing',
            ).not.toContain(READ_TOO_MANY_ITEMS_KEY);
            expect(t.mock.calls, 'one call: the save’s sentence, with max_items as max and items as count').toStrictEqual([[TOO_MANY_ITEMS_KEY, {values: {max: 10_000, count: 10_001}}]]);
            expect(sentence, 'the catalogue’s answer, unchanged').toBe(answer(TOO_MANY_ITEMS_KEY, {max: 10_000, count: 10_001}));
        });

        it('reads it from any axios-like error, with the numbers that refusal carries', () => {
            const t = fakeT();
            const sentence = writeRefusalMessage(axiosLike(422, {detail: tooManyItems(73_456, 2_500)}), t, dateLabel);
            expect(t.mock.calls).toStrictEqual([[TOO_MANY_ITEMS_KEY, {values: {max: 2_500, count: 73_456}}]]);
            expect(sentence).toBe(answer(TOO_MANY_ITEMS_KEY, {max: 2_500, count: 73_456}));
        });

        it('a detail that also carries the numbers of the days refusal: still the save’s sentence — the code decides', () => {
            const t = fakeT();
            const error = axiosRefusal(422, {detail: {...BULK_ITEMS, max_item_days: 1_000_000, item_days: 1_234_567}});
            expect(writeRefusalMessage(error, t, dateLabel)).toBe(answer(TOO_MANY_ITEMS_KEY, {max: 10_000, count: 10_001}));
        });

        const ITEMS_NEAR_MISSES: Array<[string, unknown]> = [
            // A number missing.
            ['without items', axiosRefusal(422, {detail: without(BULK_ITEMS, 'items')})],
            ['without max_items', axiosRefusal(422, {detail: without(BULK_ITEMS, 'max_items')})],
            ['with the days refusal’s numbers instead of its own', axiosRefusal(422, {detail: {code: 'bulk_too_many_items', max_item_days: 1_000_000, item_days: 1_234_567}})],
            // A number that is not one.
            ['with max_items as a string', axiosRefusal(422, {detail: {...BULK_ITEMS, max_items: '10000'}})],
            ['with items as a string', axiosRefusal(422, {detail: {...BULK_ITEMS, items: '10001'}})],
            ['with max_items null', axiosRefusal(422, {detail: {...BULK_ITEMS, max_items: null}})],
            ['with items null', axiosRefusal(422, {detail: {...BULK_ITEMS, items: null}})],
            ['with items a list, as the dates refusals carry them', axiosRefusal(422, {detail: {...BULK_ITEMS, items: [{index: 0, date: '2062-01-02'}]}})],
            // A number that is not finite.
            ['with max_items Infinity', axiosRefusal(422, {detail: {...BULK_ITEMS, max_items: Infinity}})],
            ['with max_items NaN', axiosRefusal(422, {detail: {...BULK_ITEMS, max_items: NaN}})],
            ['with items Infinity', axiosRefusal(422, {detail: {...BULK_ITEMS, items: Infinity}})],
            ['with items -Infinity', axiosRefusal(422, {detail: {...BULK_ITEMS, items: -Infinity}})],
            ['with items NaN', axiosRefusal(422, {detail: {...BULK_ITEMS, items: NaN}})],
            // A cap that is not above zero.
            ['with max_items 0', axiosRefusal(422, {detail: {...BULK_ITEMS, max_items: 0}})],
            ['with a negative max_items', axiosRefusal(422, {detail: {...BULK_ITEMS, max_items: -10_000}})],
            // Another status: each code is read on its own.
            ['on a 400', axiosRefusal(400, {detail: BULK_ITEMS})],
            ['on a 413', axiosRefusal(413, {detail: BULK_ITEMS})],
        ];

        it.each(ITEMS_NEAR_MISSES)('answers null for the items refusal %s, and asks the catalogue nothing', (_label, error) => {
            const t = fakeT();
            expect(writeRefusalMessage(error, t, dateLabel)).toBeNull();
            expect(t).not.toHaveBeenCalled();
        });
    });

    describe('a request too large for its days (422 bulk_too_many_days): still the sentence bulkRefusal.ts writes — a write never meets it, the delegation stays', () => {
        it('the very sentence bulkRefusalMessage gives', () => {
            const t = fakeT();
            const error = axiosRefusal(422, {detail: BULK_DAYS});
            const sentence = bulkRefusalMessage(error, t);
            expect(sentence, 'precondition: a refusal bulkRefusalMessage reads').not.toBeNull();
            expect(writeRefusalMessage(error, t, dateLabel)).toBe(sentence);
        });

        it('a detail that also carries the numbers of the items refusal: still that sentence — the code decides', () => {
            const error = axiosRefusal(422, {detail: {...BULK_DAYS, max_items: 10_000, items: 10_001}});
            const sentence = bulkRefusalMessage(error, fakeT());
            expect(sentence, 'precondition: a refusal bulkRefusalMessage reads').not.toBeNull();
            expect(writeRefusalMessage(error, fakeT(), dateLabel)).toBe(sentence);
        });

        it.each<[string, unknown]>([
            ['with a budget of 0', axiosRefusal(422, {detail: {...BULK_DAYS, max_item_days: 0}})],
            ['without item_days', axiosRefusal(422, {detail: without(BULK_DAYS, 'item_days')})],
            ['on a 400', axiosRefusal(400, {detail: BULK_DAYS})],
        ])('and null where bulkRefusalMessage gives null: the days refusal %s', (_label, error) => {
            const t = fakeT();
            expect(bulkRefusalMessage(error, t), 'precondition: a near miss bulkRefusalMessage refuses').toBeNull();
            expect(writeRefusalMessage(error, t, dateLabel)).toBeNull();
            expect(t).not.toHaveBeenCalled();
        });
    });

    describe('every rate refused (400 fx_rates_refused)', () => {
        const ROWS = [
            {index: 0, date: '2026-01-05', reason: 'same_currency'},
            {index: 2, date: '2026-01-07', reason: 'rate_not_storable'},
            {index: 3, date: '2026-01-08', reason: 'a_reason_this_build_does_not_know'},
        ];

        it('the sentence rejectedMessage gives for its rows, their dates through dateLabel', () => {
            const t = fakeT();
            const message = writeRefusalMessage(axiosRefusal(400, {detail: ratesRefused(ROWS)}), t, dateLabel);
            expect(message).toBe(answer(NOT_SAVED_KEY, {count: 3, items: `${refusedRow('D<2026-01-05>', 'same_currency')}, ${refusedRow('D<2026-01-07>', 'rate_not_storable')}, ${refusedRow('D<2026-01-08>', 'other')}`}));
            expect(message).toBe(rejectedMessage(ROWS, t, dateLabel));
        });

        it('without dateLabel: the dates as the server wrote them, ISO', () => {
            const t = fakeT();
            const message = writeRefusalMessage(axiosRefusal(400, {detail: ratesRefused(ROWS)}), t);
            expect(message).toBe(answer(NOT_SAVED_KEY, {count: 3, items: `${refusedRow('2026-01-05', 'same_currency')}, ${refusedRow('2026-01-07', 'rate_not_storable')}, ${refusedRow('2026-01-08', 'other')}`}));
            expect(message).toBe(rejectedMessage(ROWS, t));
        });

        it('reads it from any axios-like error', () => {
            const t = fakeT();
            expect(writeRefusalMessage(axiosLike(400, {detail: ratesRefused(ROWS)}), t, dateLabel)).toBe(rejectedMessage(ROWS, t, dateLabel));
        });
    });

    describe('anything else: null', () => {
        const NEAR_MISSES: Array<[string, unknown]> = [
            // Another status, the same coded details.
            ['the dates refusal on a 400', axiosRefusal(400, {detail: PRICES_OUT_OF_RANGE})],
            ['the dates refusal on a 500', axiosRefusal(500, {detail: PRICES_OUT_OF_RANGE})],
            ['the currency refusal on a 400', axiosRefusal(400, {detail: MISMATCH})],
            ['the rates refusal on a 422', axiosRefusal(422, {detail: RATES_REFUSED})],
            ['the rates refusal on a 500', axiosRefusal(500, {detail: RATES_REFUSED})],
            ['the dates refusal on a response without a status', {response: {data: {detail: PRICES_OUT_OF_RANGE}}}],
            // Another code.
            ['the period changes’ own 422, period_changes_too_many_days', axiosRefusal(422, {detail: {code: 'period_changes_too_many_days', message: 'A fixed-period changes request may value at most 5 distinct as_of days, not 6', field: 'as_of', max_days: 5, days: 6}})],
            ['a refusal of the events, coded under error_code', axiosRefusal(400, {detail: EVENT_REFUSAL})],
            ['the dates code in capitals', axiosRefusal(422, {detail: {...PRICES_OUT_OF_RANGE, code: 'DATE_OUT_OF_RANGE'}})],
            ['the dates refusal without a code', axiosRefusal(422, {detail: without(PRICES_OUT_OF_RANGE, 'code')})],
            ['the currency refusal with a numeric code', axiosRefusal(422, {detail: {...MISMATCH, code: 422}})],
            ['the rates refusal without a code', axiosRefusal(400, {detail: without(RATES_REFUSED, 'code')})],
            // A count that is not a finite number.
            ['the dates refusal without count', axiosRefusal(422, {detail: without(PRICES_OUT_OF_RANGE, 'count')})],
            ['the dates refusal’s count NaN', axiosRefusal(422, {detail: {...PRICES_OUT_OF_RANGE, count: NaN}})],
            ['the dates refusal’s count Infinity', axiosRefusal(422, {detail: {...PRICES_OUT_OF_RANGE, count: Infinity}})],
            ['the dates refusal’s count as a string', axiosRefusal(422, {detail: {...PRICES_OUT_OF_RANGE, count: '1'}})],
            ['the dates refusal’s count null', axiosRefusal(422, {detail: {...PRICES_OUT_OF_RANGE, count: null}})],
            ['the currency refusal without count', axiosRefusal(422, {detail: without(MISMATCH, 'count')})],
            ['the currency refusal’s count NaN', axiosRefusal(422, {detail: {...MISMATCH, count: NaN}})],
            ['the currency refusal’s count -Infinity', axiosRefusal(422, {detail: {...MISMATCH, count: -Infinity}})],
            ['the currency refusal’s count as a string', axiosRefusal(422, {detail: {...MISMATCH, count: '1'}})],
            // A bound missing.
            ['the dates refusal without params', axiosRefusal(422, {detail: without(PRICES_OUT_OF_RANGE, 'params')})],
            ['the dates refusal with params null', axiosRefusal(422, {detail: {...PRICES_OUT_OF_RANGE, params: null}})],
            ['the dates refusal without params.min', axiosRefusal(422, {detail: {...PRICES_OUT_OF_RANGE, params: {max: MAX}}})],
            ['the dates refusal without params.max', axiosRefusal(422, {detail: {...PRICES_OUT_OF_RANGE, params: {min: MIN}}})],
            // Items that are not a list.
            ['the dates refusal without items', axiosRefusal(422, {detail: without(PRICES_OUT_OF_RANGE, 'items')})],
            ['the dates refusal’s items one object, not a list', axiosRefusal(422, {detail: {...PRICES_OUT_OF_RANGE, items: {asset_id: 7, dates: ['2062-03-05']}}})],
            ['the dates refusal’s items a string', axiosRefusal(422, {detail: {...PRICES_OUT_OF_RANGE, items: '2062-03-05'}})],
            ['the dates refusal’s items null', axiosRefusal(422, {detail: {...PRICES_OUT_OF_RANGE, items: null}})],
            ['the currency refusal without items', axiosRefusal(422, {detail: without(MISMATCH, 'items')})],
            ['the currency refusal’s items one object, not a list', axiosRefusal(422, {detail: {...MISMATCH, items: {asset_id: 7, expected: 'EUR', found: ['USD'], dates: ['2026-01-05']}}})],
            ['the rates refusal without rejected', axiosRefusal(400, {detail: without(RATES_REFUSED, 'rejected')})],
            ['the rates refusal’s rejected one object, not a list', axiosRefusal(400, {detail: {...RATES_REFUSED, rejected: {index: 0, date: '2026-01-05', reason: 'same_currency'}}})],
            // No date to name.
            ['the dates refusal with no item', axiosRefusal(422, {detail: outOfRange([], 0)})],
            [
                'the dates refusal whose items list no date',
                axiosRefusal(422, {
                    detail: outOfRange(
                        [
                            {asset_id: 7, dates: []},
                            {asset_id: 9, dates: []},
                        ],
                        2,
                    ),
                }),
            ],
            ['the currency refusal with no item', axiosRefusal(422, {detail: currencyMismatch([], 0)})],
            ['the currency refusal whose item lists no date', axiosRefusal(422, {detail: currencyMismatch([{asset_id: 7, expected: 'EUR', found: ['USD'], dates: []}], 1)})],
            ['the rates refusal with no row', axiosRefusal(400, {detail: ratesRefused([])})],
            // A detail that is not a coded object.
            ['a 400 whose detail is the string «All rates failed: …»', axiosRefusal(400, {detail: ALL_RATES_FAILED})],
            ['a 500 whose detail is «Internal error while saving prices»', axiosRefusal(500, {detail: PRICES_INTERNAL_ERROR})],
            ['a 422 of request validation, a list of issues', axiosRefusal(422, {detail: VALIDATION_ISSUES})],
            ['a 422 whose detail is null', axiosRefusal(422, {detail: null})],
            ['a 422 whose body is the dates detail itself, unwrapped', axiosRefusal(422, PRICES_OUT_OF_RANGE)],
            ['a 422 whose body is text', axiosRefusal(422, 'Unprocessable Entity')],
            ['a 422 without a body', axiosRefusal(422, undefined)],
            // No response.
            ['a request that reached no server', new AxiosError('Network Error', AxiosError.ERR_NETWORK, REQUEST, {})],
            ['an axios-like error whose response is null', {response: null}],
            ['a plain Error naming the code', new Error('date_out_of_range')],
            ['the sentence the events branch throws, already translated', new Error(EVENT_SENTENCE)],
            ['an empty object', {}],
            ['null', null],
            ['undefined', undefined],
            // No object at all.
            ['the code as a bare string', 'date_out_of_range'],
            ['a bare status', 422],
        ];

        it.each(NEAR_MISSES)('answers null for %s, and asks the catalogue nothing', (_label, error) => {
            const t = fakeT();
            expect(writeRefusalMessage(error, t, dateLabel)).toBeNull();
            expect(t).not.toHaveBeenCalled();
        });

        /** Every field of the three refusals this module reads, all valid: under `code` alone the detail decides nothing else. */
        const everyField = (code: string): Record<string, unknown> => ({
            code,
            message: 'A refusal',
            params: {min: MIN, max: MAX},
            items: [{asset_id: 7, expected: 'EUR', found: ['USD'], dates: ['2062-03-05']}],
            count: 1,
            rejected: [{index: 0, date: '2062-03-05', reason: 'same_currency'}],
        });

        it.each(['constructor', 'toString', 'valueOf', 'hasOwnProperty', '__proto__'])('answers null for the code %s — a property every object inherits — on a 422 and on a 400, though the detail carries every field', (code) => {
            const t = fakeT();
            expect(writeRefusalMessage(axiosRefusal(422, {detail: everyField(code)}), t, dateLabel)).toBeNull();
            expect(writeRefusalMessage(axiosRefusal(400, {detail: everyField(code)}), t, dateLabel)).toBeNull();
            expect(t).not.toHaveBeenCalled();
        });

        it.each<[string, number, string]>([
            ['date_out_of_range', 422, answer(OUT_OF_RANGE_KEY, {count: 1, min: 'D<1900-01-01>', max: 'D<2026-10-18>', dates: 'D<2062-03-05>'})],
            ['price_currency_mismatch', 422, answer(MISMATCH_KEY, {count: 1, expected: 'EUR', found: 'USD', dates: 'D<2062-03-05>'})],
            ['fx_rates_refused', 400, answer(NOT_SAVED_KEY, {count: 1, items: refusedRow('D<2062-03-05>', 'same_currency')})],
        ])('control: the same detail under %s, on a %i, gives that refusal’s sentence — the code alone decided the nulls above', (code, status, sentence) => {
            expect(writeRefusalMessage(axiosRefusal(status, {detail: everyField(code)}), fakeT(), dateLabel)).toBe(sentence);
        });
    });
});

// =============================================================================
//  rejectedMessage
// =============================================================================

describe('rejectedMessage', () => {
    it('answers null for no row, and asks the catalogue nothing', () => {
        const t = fakeT();
        expect(rejectedMessage([], t, dateLabel)).toBeNull();
        expect(t).not.toHaveBeenCalled();
    });

    it('one row: a count of 1, and the row as its date through dateLabel, then its reason’s sentence in brackets', () => {
        const t = fakeT();
        expect(rejectedMessage([{date: '2026-01-05', reason: 'ohlc_inconsistent'}], t, dateLabel)).toBe(answer(NOT_SAVED_KEY, {count: 1, items: 'D<2026-01-05> (common.writeRefusal.reason.ohlc_inconsistent)'}));
    });

    it.each(BACKEND_REJECTION_REASONS)('the backend’s reason %s reads as its own sentence, common.writeRefusal.reason.%s', (reason) => {
        const t = fakeT();
        expect(rejectedMessage([{date: '2026-01-05', reason}], t, dateLabel)).toBe(answer(NOT_SAVED_KEY, {count: 1, items: refusedRow('D<2026-01-05>', reason)}));
    });

    it.each(['quota_exceeded', 'OHLC_INCONSISTENT', '', 'constructor', 'toString', '__proto__'])('a reason this build does not know, %j, reads as common.writeRefusal.reason.other', (reason) => {
        const t = fakeT();
        expect(rejectedMessage([{date: '2026-01-05', reason}], t, dateLabel)).toBe(answer(NOT_SAVED_KEY, {count: 1, items: refusedRow('D<2026-01-05>', 'other')}));
    });

    it('several rows: each with its own reason, in the order given — not sorted — and the list itself left as it was', () => {
        const t = fakeT();
        const rejected: readonly Rejection[] = Object.freeze([
            {date: '2026-03-02', reason: 'value_not_storable'},
            {date: '2026-01-15', reason: 'ohlc_inconsistent'},
            {date: '2026-02-01', reason: 'a_reason_this_build_does_not_know'},
        ]);
        expect(rejectedMessage(rejected, t, dateLabel)).toBe(answer(NOT_SAVED_KEY, {count: 3, items: `${refusedRow('D<2026-03-02>', 'value_not_storable')}, ${refusedRow('D<2026-01-15>', 'ohlc_inconsistent')}, ${refusedRow('D<2026-02-01>', 'other')}`}));
    });

    it('shows five rows at most, then «more» with the rows not shown; the count is every row', () => {
        const t = fakeT();
        const rejected = days('2026-01', 7).map((date) => ({date, reason: 'ohlc_inconsistent'}));
        const row = (date: string): string => refusedRow(`D<${date}>`, 'ohlc_inconsistent');
        expect(rejectedMessage(rejected, t, dateLabel)).toBe(answer(NOT_SAVED_KEY, {count: 7, items: `${row('2026-01-01')}, ${row('2026-01-02')}, ${row('2026-01-03')}, ${row('2026-01-04')}, ${row('2026-01-05')} ${more(2)}`}));
    });

    it.each<[number, string]>([
        [5, ''],
        [6, ` ${more(1)}`],
    ])('%i rows: the cut falls after the fifth', (n, tail) => {
        const t = fakeT();
        const rejected = days('2026-01', n).map((date) => ({date, reason: 'value_not_storable'}));
        const shown = days('2026-01', 5)
            .map((date) => refusedRow(`D<${date}>`, 'value_not_storable'))
            .join(', ');
        expect(rejectedMessage(rejected, t, dateLabel)).toBe(answer(NOT_SAVED_KEY, {count: n, items: `${shown}${tail}`}));
    });

    it('without dateLabel: the dates as given, ISO', () => {
        const t = fakeT();
        const rejected: Rejection[] = [
            {date: '2026-01-05', reason: 'same_currency'},
            {date: '2026-01-06', reason: 'invalid_rate'},
        ];
        expect(rejectedMessage(rejected, t)).toBe(answer(NOT_SAVED_KEY, {count: 2, items: `${refusedRow('2026-01-05', 'same_currency')}, ${refusedRow('2026-01-06', 'invalid_rate')}`}));
    });
});

// =============================================================================
//  saveErrorText
// =============================================================================

describe('saveErrorText', () => {
    describe('a coded refusal: the sentence writeRefusalMessage gives', () => {
        const REFUSALS: Array<[string, unknown]> = [
            ['the prices’ dates out of range (422)', axiosRefusal(422, {detail: outOfRange([{asset_id: 7, dates: ['2062-03-05', '2062-03-06']}], 2)})],
            ['the rates’ dates out of range (422)', axiosRefusal(422, {detail: outOfRange([{index: 2, date: '2062-01-02'}], 1)})],
            ['prices in another currency (422)', axiosRefusal(422, {detail: MISMATCH})],
            ['a write too large (422 bulk_too_many_items)', axiosRefusal(422, {detail: BULK_ITEMS})],
            ['every rate refused (400 fx_rates_refused)', axiosRefusal(400, {detail: RATES_REFUSED})],
            ['the prices’ dates out of range, on an axios-like error', axiosLike(422, {detail: PRICES_OUT_OF_RANGE})],
        ];

        it.each(REFUSALS)('%s, with dateLabel passed on', (_label, error) => {
            const t = fakeT();
            const sentence = writeRefusalMessage(error, t, dateLabel);
            expect(sentence, 'precondition: a refusal writeRefusalMessage reads').not.toBeNull();
            expect(saveErrorText(error, t, dateLabel)).toBe(sentence);
        });

        it('without dateLabel: ISO dates and bounds', () => {
            const t = fakeT();
            expect(saveErrorText(axiosRefusal(422, {detail: PRICES_OUT_OF_RANGE}), t)).toBe(answer(OUT_OF_RANGE_KEY, {count: 1, min: '1900-01-01', max: '2026-10-18', dates: '2062-03-05'}));
        });
    });

    describe('anything else: extractErrorMessage, with t(common.unknownError) as its fallback', () => {
        it('a 400 whose detail is the string «All rates failed: …»: that string', () => {
            expect(saveErrorText(axiosRefusal(400, {detail: ALL_RATES_FAILED}), fakeT(), dateLabel)).toBe(ALL_RATES_FAILED);
        });

        it('a 400 fx_rates_refused with no row to name: its message, the same «All rates failed: …»', () => {
            expect(saveErrorText(axiosRefusal(400, {detail: ratesRefused([])}), fakeT(), dateLabel)).toBe(ALL_RATES_FAILED);
        });

        it('a 500 «Internal error while saving prices»: that string', () => {
            expect(saveErrorText(axiosRefusal(500, {detail: PRICES_INTERNAL_ERROR}), fakeT(), dateLabel)).toBe(PRICES_INTERNAL_ERROR);
        });

        it('the sentence the events branch throws, translated already, in a plain Error: its message as it is', () => {
            expect(saveErrorText(new Error(EVENT_SENTENCE), fakeT(), dateLabel)).toBe(EVENT_SENTENCE);
        });

        it.each<[string, unknown]>([
            ['null', null],
            ['undefined', undefined],
            ['an Error with no message', new Error('')],
            ['an empty object', {}],
        ])('%s, which says nothing: t(common.unknownError)', (_label, error) => {
            expect(saveErrorText(error, fakeT(), dateLabel)).toBe(answer(UNKNOWN_ERROR_KEY));
        });

        it('the fallback is what t answers for common.unknownError, not the key', () => {
            const t = vi.fn((key: string, options?: {values?: Values}): string => (key === UNKNOWN_ERROR_KEY ? 'the catalogue’s own sentence' : answer(key, options?.values)));
            expect(saveErrorText(null, t, dateLabel)).toBe('the catalogue’s own sentence');
        });

        it.each<[string, unknown]>([
            ['a request that reached no server', new AxiosError('Network Error', AxiosError.ERR_NETWORK, REQUEST, {})],
            ['a 409 whose detail is a string', axiosRefusal(409, {detail: 'A rate was written meanwhile'})],
            ['a 400 whose detail says it under error', axiosRefusal(400, {detail: {error: 'The pair is not configured'}})],
            ['a refusal of the events, coded under error_code', axiosRefusal(400, {detail: EVENT_REFUSAL})],
            ['a 422 of request validation', axiosRefusal(422, {detail: VALIDATION_ISSUES})],
            ['a 502 with its status text and no body', {message: 'Request failed with status code 502', response: {status: 502, statusText: 'Bad Gateway', data: undefined}}],
            ['the dates refusal on a 400, which this module does not read', axiosRefusal(400, {detail: PRICES_OUT_OF_RANGE})],
        ])('%s: the text extractErrorMessage gives', (_label, error) => {
            expect(saveErrorText(error, fakeT(), dateLabel)).toBe(extractErrorMessage(error, answer(UNKNOWN_ERROR_KEY)));
        });
    });

    describe('never Axios’s generic «Request failed with status code 422» when the error carries a detail', () => {
        const DETAILS: Array<[string, unknown, string]> = [
            ['a refusal this module reads: its sentence', PRICES_OUT_OF_RANGE, answer(OUT_OF_RANGE_KEY, {count: 1, min: 'D<1900-01-01>', max: 'D<2026-10-18>', dates: 'D<2062-03-05>'})],
            ['a refusal under a code this build does not know: its message', {code: 'price_rows_locked', message: 'The prices of asset 7 are locked until 2026-10-19'}, 'The prices of asset 7 are locked until 2026-10-19'],
            ['a refusal this module cannot read, its items not a list: its message', {...MISMATCH, items: 'USD'}, "Prices must be in their asset's currency: 1 are not"],
            ['a string: the string', 'The close of 2026-01-05 must be above 0', 'The close of 2026-01-05 must be above 0'],
        ];
        const PINS: Array<[string, unknown, string]> = DETAILS.flatMap(
            ([label, detail, text]): Array<[string, unknown, string]> => [
                [`an AxiosError, ${label}`, axiosRefusal(422, {detail}), text],
                [`an axios-like object, ${label}`, axiosLike(422, {detail}), text],
            ],
        );

        it.each(PINS)('%s', (_label, error, text) => {
            expect((error as {message: unknown}).message, 'precondition: Axios’s generic message is on the error, to be lost').toBe(GENERIC_422);
            const shown = saveErrorText(error, fakeT(), dateLabel);
            expect(shown).toBe(text);
            expect(shown).not.toContain('Request failed with status code');
        });

        it('a list of validation issues: their text, as extractErrorMessage sums it up', () => {
            const error = axiosRefusal(422, {detail: VALIDATION_ISSUES});
            expect(error.message, 'precondition: Axios’s generic message is on the error, to be lost').toBe(GENERIC_422);
            const shown = saveErrorText(error, fakeT(), dateLabel);
            expect(shown).toContain('month value is outside expected range of 1-12');
            expect(shown).not.toContain('Request failed with status code');
        });
    });
});

// =============================================================================
//  REJECTION_REASONS
// =============================================================================

describe('REJECTION_REASONS', () => {
    it('is exactly the reasons the backend writes, FAPriceRejection.reason and FXRateRejection.reason: none missing, none extra, none twice', () => {
        expect([...REJECTION_REASONS].sort()).toStrictEqual([...BACKEND_REJECTION_REASONS].sort());
    });
});
