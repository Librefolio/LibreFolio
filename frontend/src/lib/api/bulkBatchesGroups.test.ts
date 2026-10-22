/**
 * Z-29b (X's requirement): a card's price query item and the items that follow it (`sample_like` its key) go in one
 * request. `POST /assets/prices/query` refuses a `sample_like` whose named item is in another request (422
 * `sample_reference` / `unknown_key`), so `bulkBatches.ts` cuts the list into batches by groups — the item of a card with
 * its comparison targets — never between the members of one, whether it plans the batches or splits one the backend
 * refused for its days. A group's estimate is the sum of its items; one that alone passes the budget goes alone.
 *
 * Red first: `groupOf` is not an option yet, so the plan cuts between the members of a group.
 */
import {AxiosError, AxiosHeaders, type AxiosResponse, type InternalAxiosRequestConfig} from 'axios';
import {describe, expect, it, vi} from 'vitest';

import {BULK_MAX_ITEMS, planBulkBatches, sendBulkBatches} from './bulkBatches';
import type {BulkBatch} from './bulkBatches';

/** An item of a list: its name, its group (the card it belongs to) and its estimated days. */
interface Entry {
    name: string;
    group: string;
    days: number;
}

const entry = (name: string, group: string, days = 10): Entry => ({name, group, days});
const daysOf = (item: Entry) => item.days;
const groupOf = (item: Entry) => item.group;
const namesOf = (batches: BulkBatch<Entry>[]) => batches.map((batch) => ({offset: batch.offset, names: batch.items.map((item) => item.name)}));

const REQUEST = {headers: new AxiosHeaders()} as InternalAxiosRequestConfig;
function daysRefusal(itemDays: number, maxItemDays = 1_000_000): AxiosError {
    const response: AxiosResponse = {
        status: 422,
        statusText: '',
        headers: {'content-type': 'application/json'},
        config: REQUEST,
        request: {},
        data: {detail: {code: 'bulk_too_many_days', message: 'too many days', max_item_days: maxItemDays, item_days: itemDays}},
    };
    return new AxiosError('Request failed with status code 422', AxiosError.ERR_BAD_REQUEST, REQUEST, {}, response);
}

/** Cards with their targets: A (self, a1, a2), B (self), C (self, c1), D (self). */
const LIST = [entry('A', 'A'), entry('a1', 'A'), entry('a2', 'A'), entry('B', 'B'), entry('C', 'C'), entry('c1', 'C'), entry('D', 'D')];

describe('planBulkBatches with groups', () => {
    it('keeps a group in one batch when the budget would cut between its members', () => {
        // Budget 25: A (3 × 10 = 30) alone passes it; then B (10) + C (20) = 30 passes it too: B, then C + D? C(20)+D(10)=30 > 25.
        const batches = planBulkBatches(LIST, daysOf, {maxItemDays: 25, groupOf});

        expect(namesOf(batches)).toEqual([
            {offset: 0, names: ['A', 'a1', 'a2']},
            {offset: 3, names: ['B']},
            {offset: 4, names: ['C', 'c1']},
            {offset: 6, names: ['D']},
        ]);
    });

    it('puts consecutive groups together while they fit, never half of one', () => {
        const batches = planBulkBatches(LIST, daysOf, {maxItemDays: 45, groupOf});

        expect(namesOf(batches)).toEqual([
            {offset: 0, names: ['A', 'a1', 'a2', 'B']},
            {offset: 4, names: ['C', 'c1', 'D']},
        ]);
    });

    it('without groupOf cuts as before, between any two items', () => {
        const batches = planBulkBatches(LIST, daysOf, {maxItemDays: 25});

        expect(namesOf(batches).map((batch) => batch.names.length)).toEqual([2, 2, 2, 1]);
    });

    it('gives a group that alone passes the budget a batch of its own', () => {
        const heavy = [entry('x', 'X', 500), entry('x1', 'X', 500), entry('y', 'Y', 10)];

        expect(namesOf(planBulkBatches(heavy, daysOf, {maxItemDays: 100, groupOf}))).toEqual([
            {offset: 0, names: ['x', 'x1']},
            {offset: 2, names: ['y']},
        ]);
    });

    it('counts a group in items against the item cap: it opens a new batch rather than cross it', () => {
        const items = [...Array.from({length: BULK_MAX_ITEMS - 1}, (_, i) => entry(`s${i}`, `s${i}`, 0)), entry('g', 'G', 0), entry('g1', 'G', 0)];

        const batches = planBulkBatches(items, daysOf, {groupOf});

        expect(batches.map((batch) => batch.items.length)).toEqual([BULK_MAX_ITEMS - 1, 2]);
    });
});

describe('sendBulkBatches with groups', () => {
    it('splits a batch the backend refused for its days between groups, not inside one', async () => {
        const sent: string[][] = [];
        const send = vi.fn(async (items: Entry[]) => {
            sent.push(items.map((item) => item.name));
            if (sent.length === 1) throw daysRefusal(2_000_000);
            return items.length;
        });

        const outcome = await sendBulkBatches(LIST, () => 1, send, {groupOf});

        expect(outcome.failed).toBe(false);
        for (const names of sent.slice(1)) {
            expect(names.includes('a1') === names.includes('A') && names.includes('a2') === names.includes('A'), `A's group is whole in ${names}`).toBe(true);
            expect(names.includes('c1') === names.includes('C'), `C's group is whole in ${names}`).toBe(true);
        }
        expect(sent.slice(1).flat(), 'every item once, in order').toEqual(LIST.map((item) => item.name));
        expect(outcome.answers.map(({batch}) => batch.offset)).toEqual([...outcome.answers.map(({batch}) => batch.offset)].sort((left, right) => left - right));
    });

    it('does not split a group of several items that the backend refuses: the batch fails', async () => {
        const single = [entry('A', 'A'), entry('a1', 'A')];
        const send = vi.fn(async () => {
            throw daysRefusal(5_000_000);
        });

        const outcome = await sendBulkBatches(single, () => 1, send, {groupOf});

        expect(outcome.failed).toBe(true);
        expect(send).toHaveBeenCalledTimes(1);
        expect(outcome.failedBatch?.items.map((item) => item.name)).toEqual(['A', 'a1']);
    });

    it('sends as before without groupOf', async () => {
        const send = vi.fn(async (items: Entry[]) => items.length);

        const outcome = await sendBulkBatches(LIST, () => 1, send);

        expect(send).toHaveBeenCalledTimes(1);
        expect(outcome.answers[0].answer).toBe(LIST.length);
    });
});
