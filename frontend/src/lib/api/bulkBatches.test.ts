/**
 * Bulk request batches (lot Z-27, decisions D1–D4 of 17/10) — `src/lib/api/bulkBatches.ts`.
 *
 * Since Z-25 the backend caps one bulk request: `POST /api/v1/assets/prices/query` and `POST /api/v1/fx/currencies/convert`
 * refuse more than `MAX_BULK_ITEMS` items (1,000; 422 `bulk_too_many_items`) and more than `MAX_BULK_ITEM_DAYS`
 * item-days (1,000,000 since R13-SEC9-2; 422 `bulk_too_many_days`; `backend/app/utils/date_range_limits.py`). The asset
 * list and the FX list send their whole list in one request, so past either cap a list loads nothing. The helper pinned
 * here plans a list into batches and sends them:
 *
 *   - D1 — the caps as constants with a margin: 1,000 items and 800,000 estimated item-days (80 % of the backend's
 *     1,000,000). A batch the backend still refuses for its days is split by the numbers of the refusal —
 *     max(2, ceil(item_days / max_item_days) + 1) consecutive parts — and sent again, at most `BULK_SPLIT_MAX_DEPTH`
 *     levels deep;
 *   - D2 — one batch at a time: the next send starts only once the previous one settled;
 *   - one batch when everything fits: the common case keeps today's single request.
 *
 * `bulkRangeDays` estimates a range the way the backend cuts it (X-R55): the end at tomorrow, the start at most 100 years
 * before that end.
 *
 * Only the first case writes the values of the caps. Every other case derives its sizes from the constants the module
 * exports (`BULK_MAX_ITEMS`, `BULK_ITEM_DAYS_BUDGET`, `BULK_SPLIT_MAX_DEPTH`, `BULK_RANGE_SPAN_DAYS`), so a later change
 * of a cap moves them with it; where a case only holds for some values, it checks that premise first. A pure module in
 * the default `node` environment: no network and no clock — `today` is an argument, and every `send` is a fake the test
 * answers.
 *
 * Red first: until the module exists the file fails at its import.
 */
import {AxiosError, AxiosHeaders, type AxiosResponse, type InternalAxiosRequestConfig} from 'axios';
import {describe, expect, it, vi} from 'vitest';
import {BULK_ITEM_DAYS_BUDGET, BULK_MAX_ITEMS, BULK_RANGE_SPAN_DAYS, BULK_SIGNAL_MARGIN_DAYS, BULK_SPLIT_MAX_DEPTH, bulkRangeDays, bulkTooManyDaysOf, planBulkBatches, sendBulkBatches} from './bulkBatches';
import type {BulkBatch, BulkOutcome} from './bulkBatches';

// =============================================================================
//  Fakes and readers
// =============================================================================

/**
 * The backend's own figure, the `max_item_days` its 422 carries: 1,000,000 since R13-SEC9-2. Not a web-app constant —
 * the split reads it from the refusal, so the cases below hold whatever its value; it only keeps the fakes realistic.
 */
const BACKEND_MAX_ITEM_DAYS = 1_000_000;

const REQUEST = {headers: new AxiosHeaders()} as InternalAxiosRequestConfig;

/** A refusal as the generated client raises it: the raw AxiosError its response interceptor passes on (`zodios-client.ts`). */
function axiosRefusal(status: number, data: unknown): AxiosError {
    const response: AxiosResponse = {status, statusText: '', headers: {'content-type': 'application/json'}, config: REQUEST, request: {}, data};
    return new AxiosError(`Request failed with status code ${status}`, status < 500 ? AxiosError.ERR_BAD_REQUEST : AxiosError.ERR_BAD_RESPONSE, REQUEST, {}, response);
}

/** The 422 of a request over the item-days budget, worded as the backend words it (`bulk_too_many_days_detail`; the FX count is «at least»). */
function daysRefusal(itemDays: number, maxItemDays = BACKEND_MAX_ITEM_DAYS): AxiosError {
    return axiosRefusal(422, {detail: {code: 'bulk_too_many_days', message: `A bulk request may build at most ${maxItemDays} per-day points, and this one would build at least ${itemDays}`, max_item_days: maxItemDays, item_days: itemDays}});
}

/** The 422 of a request over the item cap (`bulk_too_many_items_detail`); the web app's cap is the backend's own. */
function itemsRefusal(items: number, maxItems = BULK_MAX_ITEMS): AxiosError {
    return axiosRefusal(422, {detail: {code: 'bulk_too_many_items', message: `A bulk request may hold at most ${maxItems} items, not ${items}`, max_items: maxItems, items}});
}

interface Deferred<T> {
    promise: Promise<T>;
    resolve: (value: T) => void;
    reject: (reason: unknown) => void;
}

function deferred<T>(): Deferred<T> {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((settle, fail) => {
        resolve = settle;
        reject = fail;
    });
    return {promise, resolve, reject};
}

/**
 * A `send` that answers at once: every call is recorded (a copy of its items, in call order) and answered
 * `answer:<items>`, unless `refuse` returns a rejection for that call — calls are numbered from 1.
 */
function answeringSend<T>(refuse: (call: number, items: readonly T[]) => unknown = () => undefined) {
    const sent: T[][] = [];
    const send = vi.fn(async (items: T[]): Promise<string> => {
        sent.push([...items]);
        const refusal = refuse(sent.length, items);
        if (refusal !== undefined) throw refusal;
        return `answer:${items.join(',')}`;
    });
    return {send, sent};
}

/** A `send` the test holds: each call is recorded with a reply settled by hand; `sent(n)` settles once n calls went out. */
function heldSend<T>() {
    const calls: Array<{items: T[]; reply: Deferred<string>}> = [];
    const waiting: Array<{count: number; release: () => void}> = [];
    const send = vi.fn((items: T[]): Promise<string> => {
        const reply = deferred<string>();
        calls.push({items: [...items], reply});
        for (const waiter of waiting) if (calls.length >= waiter.count) waiter.release();
        return reply.promise;
    });
    const sent = (count: number) => new Promise<void>((release) => (calls.length >= count ? release() : waiting.push({count, release})));
    return {send, calls, sent};
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

/**
 * One turn of the event loop: every microtask already queued, and every one those queue, has run — whatever the helper
 * could do without the pending send settling has been done. The barrier an absence needs; not a bet on the clock: the
 * turn ends when the queue is empty, however fast the machine.
 */
function drainMicrotasks(): Promise<void> {
    return new Promise((resolve) => setImmediate(resolve));
}

/** A batch as the two things a caller reads: where it starts in the list, and its items. */
function shapeOf<T>(batch: BulkBatch<T>): {offset: number; items: T[]} {
    return {offset: batch.offset, items: [...batch.items]};
}

/** The answers of an outcome, each with the shape of its batch. */
function answersOf<T, R>(outcome: BulkOutcome<T, R>): Array<{offset: number; items: T[]; answer: R}> {
    return outcome.answers.map(({batch, answer}) => ({...shapeOf(batch), answer}));
}

const range = (n: number): number[] => Array.from({length: n}, (_, i) => i);

/** An item with its estimated days, named so that a plan reads as lists of names. */
const named = (name: string, days: number) => ({name, days});
const daysOf = (item: {days: number}) => item.days;
const namesOf = (batches: BulkBatch<{name: string}>[]) => batches.map((batch) => ({offset: batch.offset, names: batch.items.map((item) => item.name)}));

// =============================================================================
//  The caps
// =============================================================================

describe('the caps of the web app (D1)', () => {
    it('are the backend’s, with the margin of D1 on the item-days', () => {
        expect(BULK_MAX_ITEMS, 'the backend’s MAX_BULK_ITEMS: 1,000 items per request').toBe(1_000);
        expect(BULK_ITEM_DAYS_BUDGET, '80 % of the backend’s MAX_BULK_ITEM_DAYS (1,000,000 since R13-SEC9-2): the estimate sees neither the first stored price nor the real warm-up').toBe(800_000);
        expect(BULK_SIGNAL_MARGIN_DAYS, 'the estimated warm-up of an item with signals').toBe(400);
        expect(BULK_SPLIT_MAX_DEPTH, 'the levels of splitting after bulk_too_many_days refusals').toBe(4);
        expect(BULK_RANGE_SPAN_DAYS, 'the backend’s 100-year span (X-R55)').toBe(36_525);
    });
});

// =============================================================================
//  bulkRangeDays — the days of a range as the backend cuts it
// =============================================================================

describe('bulkRangeDays', () => {
    /** A day after every range of the plain cases: none of them reaches the cut. */
    const LATER = '2026-10-17';
    /** The «today» of the cut cases: a parameter, deliberately not the machine's date. */
    const TODAY = '2024-06-15';
    /** `iso` moved by `days`, in UTC: the test's own calendar arithmetic, independent of the module's. */
    const shift = (iso: string, days: number): string => new Date(Date.parse(`${iso}T00:00:00Z`) + days * 86_400_000).toISOString().slice(0, 10);
    /** The first day the span keeps before 2025-12-31: 1926-01-01 with 36,525 days. */
    const FLOOR = shift('2025-12-31', -(BULK_RANGE_SPAN_DAYS - 1));

    it.each([
        ['a month', '2024-01-01', '2024-01-31', 31],
        ['February of a leap year', '2024-02-01', '2024-03-01', 30],
        ['February of a common year', '2023-02-01', '2023-03-01', 29],
        ['one day', '2024-02-29', '2024-02-29', 1],
        ['«All» from 2000 to the end of 2025', '2000-01-01', '2025-12-31', 9_497],
    ])('counts %s with both ends included', (_label, start, end, days) => {
        expect(bulkRangeDays(start, end, LATER)).toBe(days);
    });

    it.each([
        ['null', null],
        ['undefined', undefined],
    ])('reads an end of %s as the start: one day', (_label, end) => {
        expect(bulkRangeDays('2024-03-01', end, LATER)).toBe(1);
    });

    it.each([
        ['an end far ahead stops at tomorrow', '2024-06-01', '2024-12-31', 16],
        ['an end on tomorrow is kept', '2024-06-01', '2024-06-16', 16],
        ['an end on today is kept', '2024-06-01', '2024-06-15', 15],
        ['a single day on tomorrow counts', '2024-06-16', null, 1],
    ])('cuts the end at tomorrow, the last day the backend serves: %s', (_label, start, end, days) => {
        expect(bulkRangeDays(start, end, TODAY)).toBe(days);
    });

    it.each([
        ['the whole span: kept', FLOOR, BULK_RANGE_SPAN_DAYS],
        ['one day more: the start is raised', shift(FLOOR, -1), BULK_RANGE_SPAN_DAYS],
        ['from the year 1: the start is raised', '0001-01-01', BULK_RANGE_SPAN_DAYS],
        ['one day less: untouched', shift(FLOOR, 1), BULK_RANGE_SPAN_DAYS - 1],
    ])('counts at most the span back from the end — %s', (_label, start, days) => {
        expect(bulkRangeDays(start, '2025-12-31', LATER)).toBe(days);
    });

    it('counts the span back from the cut end, not from the end asked', () => {
        // The cut end is 2024-06-16, and 1950-01-01 → 2024-06-16 is 27,196 days. Counted back from the end asked,
        // 2099-12-31, the floor would fall after 1950 and the range would count fewer.
        expect(BULK_RANGE_SPAN_DAYS, 'premise: 27,196 days fit the span').toBeGreaterThan(27_196);
        expect(shift('2099-12-31', -(BULK_RANGE_SPAN_DAYS - 1)) > '1950-01-01', 'premise: from the end asked, the floor would cut 1950-01-01').toBe(true);
        expect(bulkRangeDays('1950-01-01', '2099-12-31', TODAY)).toBe(27_196);
        expect(bulkRangeDays('1800-01-01', '2099-12-31', TODAY)).toBe(BULK_RANGE_SPAN_DAYS);
    });

    it.each([
        ['a start after its end', '2024-02-01', '2024-01-01', LATER],
        ['a single day after tomorrow', '2024-06-17', null, TODAY],
        ['a range entirely after tomorrow', '2025-01-01', '2025-12-31', TODAY],
    ])('answers 0 for %s', (_label, start, end, today) => {
        expect(bulkRangeDays(start, end, today)).toBe(0);
    });
});

// =============================================================================
//  planBulkBatches — consecutive batches under the two caps
// =============================================================================

describe('planBulkBatches', () => {
    const one = () => 1;

    it('plans nothing for no items', () => {
        expect(planBulkBatches([], one)).toEqual([]);
    });

    it('keeps a list that fits in one batch: today’s single request', () => {
        const pairs = ['CHF-EUR', 'EUR-USD', 'GBP-USD'];
        expect(planBulkBatches(pairs, one).map(shapeOf)).toEqual([{offset: 0, items: pairs}]);
    });

    it('hands back the caller’s own items, in their order', () => {
        const items = [named('a', 1), named('b', 1), named('c', 1)];
        const [batch] = planBulkBatches(items, daysOf);
        expect(batch.items).toHaveLength(3);
        batch.items.forEach((planned, i) => expect(planned).toBe(items[i]));
    });

    it('holds the item cap in one batch and opens a second one item past it — the backend refuses past its cap', () => {
        expect(planBulkBatches(range(BULK_MAX_ITEMS), one).map((batch) => [batch.offset, batch.items.length])).toEqual([[0, BULK_MAX_ITEMS]]);
        const batches = planBulkBatches(range(BULK_MAX_ITEMS + 1), one);
        expect(batches.map((batch) => [batch.offset, batch.items.length])).toEqual([
            [0, BULK_MAX_ITEMS],
            [BULK_MAX_ITEMS, 1],
        ]);
        expect([...batches[1].items]).toEqual([BULK_MAX_ITEMS]);
    });

    it('fills the item-days budget to the day, and opens a new batch past it', () => {
        const half = Math.floor(BULK_ITEM_DAYS_BUDGET / 2);
        const rest = BULK_ITEM_DAYS_BUDGET - half;
        expect(planBulkBatches([half, rest], (days) => days).map(shapeOf), 'exactly the budget: one batch').toEqual([{offset: 0, items: [half, rest]}]);
        expect(planBulkBatches([half, rest + 1], (days) => days).map(shapeOf), 'one day past it: two').toEqual([
            {offset: 0, items: [half]},
            {offset: 1, items: [rest + 1]},
        ]);
    });

    it('splits greedily and in order: an item never moves to an earlier batch with room for it', () => {
        // e (1 day) would fit beside a (4 days): a plan that packed tighter would reorder the list.
        const items = [named('a', 4), named('b', 3), named('c', 2), named('d', 5), named('e', 1)];
        expect(namesOf(planBulkBatches(items, daysOf, {maxItemDays: 6}))).toEqual([
            {offset: 0, names: ['a']},
            {offset: 1, names: ['b', 'c']},
            {offset: 3, names: ['d', 'e']},
        ]);
    });

    it('gives an item whose estimate alone passes the budget a batch of its own', () => {
        expect(namesOf(planBulkBatches([named('a', 1), named('huge', 10), named('b', 1), named('c', 1)], daysOf, {maxItemDays: 5}))).toEqual([
            {offset: 0, names: ['a']},
            {offset: 1, names: ['huge']},
            {offset: 2, names: ['b', 'c']},
        ]);
        expect(namesOf(planBulkBatches([named('huge', 10), named('a', 1)], daysOf, {maxItemDays: 5})), 'first in the list as well').toEqual([
            {offset: 0, names: ['huge']},
            {offset: 1, names: ['a']},
        ]);
    });

    it('closes a batch at whichever limit it reaches first', () => {
        expect(planBulkBatches(range(5), one, {maxItems: 3, maxItemDays: 100}).map(shapeOf), 'the items').toEqual([
            {offset: 0, items: [0, 1, 2]},
            {offset: 3, items: [3, 4]},
        ]);
        expect(planBulkBatches(range(5), one, {maxItems: 100, maxItemDays: 2}).map(shapeOf), 'the days').toEqual([
            {offset: 0, items: [0, 1]},
            {offset: 2, items: [2, 3]},
            {offset: 4, items: [4]},
        ]);
    });

    it('keeps the default of the limit it is not given', () => {
        const half = Math.floor(BULK_ITEM_DAYS_BUDGET / 2);
        const pastHalf = BULK_ITEM_DAYS_BUDGET - half + 1;
        expect(planBulkBatches([half, pastHalf, 1], (days) => days, {maxItems: 2}).map(shapeOf), 'maxItems alone: the days budget still applies').toEqual([
            {offset: 0, items: [half]},
            {offset: 1, items: [pastHalf, 1]},
        ]);
        expect(
            planBulkBatches(range(BULK_MAX_ITEMS + 1), () => 0, {maxItemDays: 10}).map((batch) => [batch.offset, batch.items.length]),
            'maxItemDays alone: the item cap still applies',
        ).toEqual([
            [0, BULK_MAX_ITEMS],
            [BULK_MAX_ITEMS, 1],
        ]);
    });

    it('leaves the list it is given as it was', () => {
        const items = Object.freeze([named('a', 4), named('b', 3), named('c', 2)]);
        planBulkBatches(items, daysOf, {maxItemDays: 5});
        expect(items.map((item) => item.name)).toEqual(['a', 'b', 'c']);
    });
});

// =============================================================================
//  bulkTooManyDaysOf — the numbers of a bulk_too_many_days refusal
// =============================================================================

describe('bulkTooManyDaysOf', () => {
    const over = BACKEND_MAX_ITEM_DAYS + 1;

    it('reads the two numbers of the 422 as the generated client raises it', () => {
        expect(bulkTooManyDaysOf(daysRefusal(3 * BACKEND_MAX_ITEM_DAYS + 7))).toEqual({itemDays: 3 * BACKEND_MAX_ITEM_DAYS + 7, maxItemDays: BACKEND_MAX_ITEM_DAYS});
    });

    it('reads them from any axios-like error: a response with its status and data', () => {
        const error = Object.assign(new Error('Request failed with status code 422'), {
            response: {status: 422, data: {detail: {code: 'bulk_too_many_days', message: `A bulk request may build at most ${BACKEND_MAX_ITEM_DAYS} per-day points, and this one would build ${over}`, max_item_days: BACKEND_MAX_ITEM_DAYS, item_days: over}}},
        });
        expect(bulkTooManyDaysOf(error)).toEqual({itemDays: over, maxItemDays: BACKEND_MAX_ITEM_DAYS});
    });

    const codedDetail = {code: 'bulk_too_many_days', message: `A bulk request may build at most ${BACKEND_MAX_ITEM_DAYS} per-day points`, max_item_days: BACKEND_MAX_ITEM_DAYS, item_days: over};

    it.each<[string, unknown]>([
        ['the item cap’s 422, bulk_too_many_items', itemsRefusal(BULK_MAX_ITEMS + 1)],
        ['the same coded detail on a 400', axiosRefusal(400, {detail: codedDetail})],
        ['the same coded detail on a 500', axiosRefusal(500, {detail: codedDetail})],
        ['a 422 whose detail is a string', axiosRefusal(422, {detail: 'At most 5 distinct as_of dates'})],
        ['a 422 of request validation, a list of issues', axiosRefusal(422, {detail: [{type: 'missing', loc: ['body', 0, 'to'], msg: 'Field required'}]})],
        ['a 422 without a body', axiosRefusal(422, undefined)],
        ['a coded 422 whose numbers are strings', axiosRefusal(422, {detail: {...codedDetail, max_item_days: String(BACKEND_MAX_ITEM_DAYS), item_days: String(over)}})],
        ['a coded 422 without max_item_days', axiosRefusal(422, {detail: {code: 'bulk_too_many_days', item_days: over}})],
        ['a request that reached no server', new AxiosError('Network Error', AxiosError.ERR_NETWORK, REQUEST, {})],
        ['a plain Error', new Error('bulk_too_many_days')],
        ['null', null],
        ['undefined', undefined],
        ['the code as a bare string', 'bulk_too_many_days'],
        ['a bare status', 422],
    ])('answers null for %s', (_label, error) => {
        expect(bulkTooManyDaysOf(error)).toBeNull();
    });
});

// =============================================================================
//  sendBulkBatches — one batch at a time, split after a days refusal
// =============================================================================

describe('sendBulkBatches', () => {
    it('sends nothing for no items', async () => {
        const {send} = answeringSend<number>();

        const outcome = await sendBulkBatches([], () => 1, send);

        expect(send).not.toHaveBeenCalled();
        expect(outcome).toEqual({answers: [], failed: false});
        expect(outcome.error).toBeUndefined();
        expect(outcome.failedBatch).toBeUndefined();
    });

    it('sends a list that fits as one request, as today', async () => {
        const {send, sent} = answeringSend<string>();

        const outcome = await sendBulkBatches(['a', 'b', 'c'], () => 1, send);

        expect(sent).toEqual([['a', 'b', 'c']]);
        expect(answersOf(outcome)).toEqual([{offset: 0, items: ['a', 'b', 'c'], answer: 'answer:a,b,c'}]);
        expect(outcome.failed).toBe(false);
    });

    it('plans with the caps when it is given no limits', async () => {
        const {send, sent} = answeringSend<number>();
        const outcome = await sendBulkBatches(range(BULK_MAX_ITEMS + 1), () => 1, send);
        expect(
            sent.map((items) => items.length),
            'one item past the item cap: two requests',
        ).toEqual([BULK_MAX_ITEMS, 1]);
        expect(outcome.answers.map(({batch}) => batch.offset)).toEqual([0, BULK_MAX_ITEMS]);

        const half = Math.floor(BULK_ITEM_DAYS_BUDGET / 2);
        const days = answeringSend<number>();
        await sendBulkBatches([half, BULK_ITEM_DAYS_BUDGET - half + 1], (estimate) => estimate, days.send);
        expect(days.sent, 'one day past the item-days budget: two requests').toEqual([[half], [BULK_ITEM_DAYS_BUDGET - half + 1]]);
    });

    it('sends the planned batches in order and keeps each answer with its batch', async () => {
        const {send, sent} = answeringSend<number>();

        const outcome = await sendBulkBatches(range(5), () => 1, send, {maxItems: 2});

        expect(sent).toEqual([[0, 1], [2, 3], [4]]);
        expect(answersOf(outcome)).toEqual([
            {offset: 0, items: [0, 1], answer: 'answer:0,1'},
            {offset: 2, items: [2, 3], answer: 'answer:2,3'},
            {offset: 4, items: [4], answer: 'answer:4'},
        ]);
        expect(outcome.failed).toBe(false);
    });

    it('plans with the days budget it is given', async () => {
        const {send, sent} = answeringSend<number>();

        await sendBulkBatches([3, 3, 3], (days) => days, send, {maxItemDays: 6});

        expect(sent).toEqual([[3, 3], [3]]);
    });

    it('waits for each batch to settle before it sends the next (D2)', async () => {
        const held = heldSend<number>();
        const sending = sendBulkBatches(range(3), () => 1, held.send, {maxItems: 1});

        await within(held.sent(1), 'the first batch was never sent');
        await drainMicrotasks();
        expect(
            held.calls.map(({items}) => items),
            'a second batch went out while the first was pending: D2 sends one at a time',
        ).toEqual([[0]]);

        held.calls[0].reply.resolve('first');
        await within(held.sent(2), 'the second batch was never sent once the first answered');
        await drainMicrotasks();
        expect(
            held.calls.map(({items}) => items),
            'the third batch went out while the second was pending',
        ).toEqual([[0], [1]]);

        held.calls[1].reply.resolve('second');
        await within(held.sent(3), 'the third batch was never sent once the second answered');
        held.calls[2].reply.resolve('third');

        const outcome = await within(sending, 'the outcome never settled after the last answer');
        expect(answersOf(outcome)).toEqual([
            {offset: 0, items: [0], answer: 'first'},
            {offset: 1, items: [1], answer: 'second'},
            {offset: 2, items: [2], answer: 'third'},
        ]);
    });

    describe('after a bulk_too_many_days refusal (the safety net of D1)', () => {
        it.each([
            {itemDays: BACKEND_MAX_ITEM_DAYS + 1, parts: 3, label: 'just over the budget'},
            {itemDays: 2 * BACKEND_MAX_ITEM_DAYS, parts: 3, label: 'exactly twice the budget'},
            {itemDays: 2 * BACKEND_MAX_ITEM_DAYS + 1, parts: 4, label: 'just over twice'},
            {itemDays: 4.5 * BACKEND_MAX_ITEM_DAYS, parts: 6, label: 'four and a half times'},
        ])('splits a batch refused for $itemDays item-days into $parts consecutive parts — $label', async ({itemDays, parts}) => {
            const {send, sent} = answeringSend<number>((call) => (call === 1 ? daysRefusal(itemDays) : undefined));

            const outcome = await sendBulkBatches(range(12), () => 1, send);

            const size = 12 / parts;
            const expected = range(parts).map((part) => range(size).map((i) => part * size + i));
            expect(sent, 'the refused batch, then its parts — max(2, ceil(item_days / max_item_days) + 1) — in order').toEqual([range(12), ...expected]);
            expect(answersOf(outcome)).toEqual(expected.map((items) => ({offset: items[0], items, answer: `answer:${items.join(',')}`})));
            expect(outcome.failed).toBe(false);
        });

        it('reads the parts from the refusal’s own numbers, not from the web app’s budget', async () => {
            expect(Math.ceil((2 * BACKEND_MAX_ITEM_DAYS) / BULK_ITEM_DAYS_BUDGET) + 1, 'premise: the web app’s budget would ask for another number of parts').not.toBe(3);
            const {send, sent} = answeringSend<number>((call) => (call === 1 ? daysRefusal(2 * BACKEND_MAX_ITEM_DAYS) : undefined));

            await sendBulkBatches(range(12), () => 1, send);

            expect(
                sent.slice(1).map((part) => part.length),
                'twice the max_item_days of the refusal: max(2, 2 + 1) = 3 parts',
            ).toEqual([4, 4, 4]);
        });

        it('splits into near-equal consecutive parts when the count does not divide', async () => {
            const {send, sent} = answeringSend<number>((call) => (call === 1 ? daysRefusal(2 * BACKEND_MAX_ITEM_DAYS) : undefined));

            const outcome = await sendBulkBatches(range(10), () => 1, send);

            const parts = sent.slice(1);
            expect(parts, 'three parts').toHaveLength(3);
            expect(parts.flat(), 'consecutive, in order, every item once').toEqual(range(10));
            const sizes = parts.map((part) => part.length);
            expect(Math.max(...sizes) - Math.min(...sizes), `near-equal sizes, not ${sizes.join(' + ')}`).toBeLessThanOrEqual(1);
            expect(
                outcome.answers.map(({batch}) => batch.offset),
                'each part starts where the previous one ended',
            ).toEqual([0, sizes[0], sizes[0] + sizes[1]]);
        });

        it('never makes more parts than items', async () => {
            // Ten times the refusal's budget asks for 11 parts; two items make two.
            const {send, sent} = answeringSend<string>((call) => (call === 1 ? daysRefusal(10 * BACKEND_MAX_ITEM_DAYS) : undefined));

            const outcome = await sendBulkBatches(['a', 'b'], () => 1, send);

            expect(sent).toEqual([['a', 'b'], ['a'], ['b']]);
            expect(answersOf(outcome)).toEqual([
                {offset: 0, items: ['a'], answer: 'answer:a'},
                {offset: 1, items: ['b'], answer: 'answer:b'},
            ]);
        });

        it('never makes fewer than two parts', async () => {
            // Numbers that ask for one part would only send the same request again.
            const {send, sent} = answeringSend<number>((call) => (call === 1 ? daysRefusal(0) : undefined));

            await sendBulkBatches(range(4), () => 1, send);

            expect(sent).toEqual([range(4), [0, 1], [2, 3]]);
        });

        it('counts the offsets of the parts from the refused batch', async () => {
            const {send, sent} = answeringSend<number>((call) => (call === 2 ? daysRefusal(2 * BACKEND_MAX_ITEM_DAYS) : undefined));

            const outcome = await sendBulkBatches(range(12), () => 1, send, {maxItems: 6});

            expect(sent).toEqual([
                [0, 1, 2, 3, 4, 5],
                [6, 7, 8, 9, 10, 11],
                [6, 7],
                [8, 9],
                [10, 11],
            ]);
            expect(answersOf(outcome), 'in item order, each with its own offset in the list').toEqual([
                {offset: 0, items: [0, 1, 2, 3, 4, 5], answer: 'answer:0,1,2,3,4,5'},
                {offset: 6, items: [6, 7], answer: 'answer:6,7'},
                {offset: 8, items: [8, 9], answer: 'answer:8,9'},
                {offset: 10, items: [10, 11], answer: 'answer:10,11'},
            ]);
        });

        it('sends the parts one at a time too (D2)', async () => {
            const held = heldSend<number>();
            const sending = sendBulkBatches(range(6), () => 1, held.send);

            await within(held.sent(1), 'the batch was never sent');
            held.calls[0].reply.reject(daysRefusal(2 * BACKEND_MAX_ITEM_DAYS));
            await within(held.sent(2), 'the first part was never sent after the refusal');
            await drainMicrotasks();
            expect(
                held.calls.map(({items}) => items),
                'a second part went out while the first was pending',
            ).toEqual([range(6), [0, 1]]);

            held.calls[1].reply.resolve('first part');
            await within(held.sent(3), 'the second part was never sent once the first answered');
            await drainMicrotasks();
            expect(held.calls.map(({items}) => items)).toEqual([range(6), [0, 1], [2, 3]]);

            held.calls[2].reply.resolve('second part');
            await within(held.sent(4), 'the third part was never sent once the second answered');
            held.calls[3].reply.resolve('third part');

            const outcome = await within(sending, 'the outcome never settled after the last answer');
            expect(outcome.answers.map(({answer}) => answer)).toEqual(['first part', 'second part', 'third part']);
        });

        it('splits a part refused again, then carries on in order', async () => {
            const {send, sent} = answeringSend<number>((call) => (call <= 2 ? daysRefusal(BACKEND_MAX_ITEM_DAYS + 1) : undefined));

            const outcome = await sendBulkBatches(range(9), () => 1, send);

            expect(sent).toEqual([range(9), [0, 1, 2], [0], [1], [2], [3, 4, 5], [6, 7, 8]]);
            expect(outcome.answers.map(({batch}) => shapeOf(batch))).toEqual([
                {offset: 0, items: [0]},
                {offset: 1, items: [1]},
                {offset: 2, items: [2]},
                {offset: 3, items: [3, 4, 5]},
                {offset: 6, items: [6, 7, 8]},
            ]);
            expect(outcome.failed).toBe(false);
        });

        it('fails with the refusal when a batch of one item is refused: nothing is left to split', async () => {
            const refusal = daysRefusal(BACKEND_MAX_ITEM_DAYS + 1);
            const {send, sent} = answeringSend<string>(() => refusal);

            const outcome = await sendBulkBatches(['alone'], () => 1, send);

            expect(sent).toEqual([['alone']]);
            expect(outcome.failed).toBe(true);
            expect(outcome.error).toBe(refusal);
            expect(shapeOf(outcome.failedBatch!)).toEqual({offset: 0, items: ['alone']});
            expect(outcome.answers).toEqual([]);
        });

        it('fails on a part of one item refused again, and sends nothing after it', async () => {
            const first = daysRefusal(10 * BACKEND_MAX_ITEM_DAYS);
            const again = daysRefusal(BACKEND_MAX_ITEM_DAYS + 1);
            const {send, sent} = answeringSend<string>((call) => (call === 1 ? first : again));

            const outcome = await sendBulkBatches(['a', 'b'], () => 1, send);

            expect(sent, 'b is never sent').toEqual([['a', 'b'], ['a']]);
            expect(outcome.failed).toBe(true);
            expect(outcome.error, 'the refusal that could not be split').toBe(again);
            expect(shapeOf(outcome.failedBatch!)).toEqual({offset: 0, items: ['a']});
            expect(outcome.answers).toEqual([]);
        });

        // 27 items refused every time, three parts each: every row stops on its depth with items left, never on a batch
        // of one — so a depth read one level off sends one more batch and fails elsewhere.
        it.each([
            {maxDepth: 0, sizes: [27], failedItems: range(27), label: 'maxDepth 0: the first refusal fails, nothing is split'},
            {maxDepth: 1, sizes: [27, 9], failedItems: range(9), label: 'maxDepth 1: a part refused again fails'},
            {maxDepth: 2, sizes: [27, 9, 3], failedItems: [0, 1, 2], label: 'maxDepth 2: a part of a part refused again fails'},
        ])('fails with the last refusal once the depth is spent — $label', async ({maxDepth, sizes, failedItems}) => {
            const refusals: unknown[] = [];
            const {send, sent} = answeringSend<number>(() => {
                const refusal = daysRefusal(BACKEND_MAX_ITEM_DAYS + 1);
                refusals.push(refusal);
                return refusal;
            });

            const outcome = await sendBulkBatches(range(27), () => 1, send, {maxDepth});

            expect(
                sent.map((items) => items.length),
                'down the first path, then nothing more',
            ).toEqual(sizes);
            expect(outcome.failed).toBe(true);
            expect(outcome.error, 'the last refusal').toBe(refusals[refusals.length - 1]);
            expect(shapeOf(outcome.failedBatch!)).toEqual({offset: 0, items: failedItems});
            expect(outcome.answers).toEqual([]);
        });

        it('splits at most BULK_SPLIT_MAX_DEPTH levels deep by default', async () => {
            // 3^(depth + 1) items refused every time, three parts each — 243 → 81 → 27 → 9 → 3 at a depth of 4. The batch
            // of three at the last level fails with items left: the depth stops it, not a batch of one.
            const sizes = range(BULK_SPLIT_MAX_DEPTH + 1).map((level) => 3 ** (BULK_SPLIT_MAX_DEPTH + 1 - level));
            expect(sizes[0], 'premise: the items are one planned batch').toBeLessThanOrEqual(BULK_MAX_ITEMS);
            const refusals: unknown[] = [];
            const {send, sent} = answeringSend<number>(() => {
                const refusal = daysRefusal(BACKEND_MAX_ITEM_DAYS + 1);
                refusals.push(refusal);
                return refusal;
            });

            const outcome = await sendBulkBatches(range(sizes[0]), () => 1, send);

            expect(sent.map((items) => items.length)).toEqual(sizes);
            expect(outcome.failed).toBe(true);
            expect(outcome.error).toBe(refusals[refusals.length - 1]);
            expect(shapeOf(outcome.failedBatch!)).toEqual({offset: 0, items: [0, 1, 2]});
            expect(outcome.answers).toEqual([]);
        });
    });

    describe('after any other failure', () => {
        it.each<[string, () => unknown]>([
            ['a 500', () => axiosRefusal(500, {detail: 'Internal Server Error'})],
            ['the item cap’s 422, bulk_too_many_items: the plan’s job, never split', () => itemsRefusal(BULK_MAX_ITEMS + 1)],
            ['a 422 whose detail is a string', () => axiosRefusal(422, {detail: 'Invalid date range'})],
            ['a request that reached no server', () => new AxiosError('Network Error', AxiosError.ERR_NETWORK, REQUEST, {})],
            ['a plain Error', () => new Error('boom')],
            ['a rejection that is not an Error', () => 'boom'],
        ])('stops at %s: the batches answered before are kept, nothing more is sent', async (_label, raise) => {
            const failure = raise();
            const {send, sent} = answeringSend<number>((call) => (call === 2 ? failure : undefined));

            const outcome = await sendBulkBatches(range(6), () => 1, send, {maxItems: 2});

            expect(sent, 'the third batch is never sent').toEqual([
                [0, 1],
                [2, 3],
            ]);
            expect(outcome.failed).toBe(true);
            expect(outcome.error).toBe(failure);
            expect(shapeOf(outcome.failedBatch!)).toEqual({offset: 2, items: [2, 3]});
            expect(answersOf(outcome)).toEqual([{offset: 0, items: [0, 1], answer: 'answer:0,1'}]);
        });

        it('keeps the parts answered before a failure that comes after a split', async () => {
            const boom = axiosRefusal(500, {detail: 'Internal Server Error'});
            const {send, sent} = answeringSend<number>((call) => (call === 1 ? daysRefusal(2 * BACKEND_MAX_ITEM_DAYS) : call === 3 ? boom : undefined));

            const outcome = await sendBulkBatches(range(6), () => 1, send);

            expect(sent, 'the third part is never sent').toEqual([range(6), [0, 1], [2, 3]]);
            expect(outcome.failed).toBe(true);
            expect(outcome.error).toBe(boom);
            expect(shapeOf(outcome.failedBatch!)).toEqual({offset: 2, items: [2, 3]});
            expect(answersOf(outcome)).toEqual([{offset: 0, items: [0, 1], answer: 'answer:0,1'}]);
        });
    });
});
