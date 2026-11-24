/**
 * rewardValue.ts (project 79, STK-2a, aligned by STK-4b): the value on receipt of a REWARD, read from the backend's one
 * reader, `POST /assets/prices/reward-values`.
 *
 * - `fetchRewardValues(requests)`: the requests in batches of `REWARD_VALUES_BATCH` (1 000, the backend's `MAX_BULK_ITEMS`),
 *   each item `{asset_id, date}`, the answers in the order asked; FILLED with a value → a suggestion `{code, amount,
 *   priceDate = the reward's own day}`, any other answer (a FILLED without a value included) → no suggestion. `null` when
 *   any batch fails: nothing partial is handed on. An empty list asks nothing.
 * - `fetchRewardValue(assetId, date)`: one item, its suggestion or `null` (no close that day, no history, a failed read).
 *
 * The rule itself (the close of that very day, ÷ the quote base) is the backend's: nothing is divided or chosen here.
 *
 * Node env. `$lib/api` is mocked with only the one call the module makes.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: {
        query_reward_values_api_v1_assets_prices_reward_values_post: vi.fn(),
    },
}));

import {zodiosApi} from '$lib/api';
import {REWARD_VALUES_BATCH, fetchRewardValue, fetchRewardValues, type RewardValueRequest} from './rewardValue';

const query = vi.mocked(zodiosApi.query_reward_values_api_v1_assets_prices_reward_values_post);

const DAY = '2024-03-10';

type Raw = {asset_id: number; date: string; status: 'FILLED' | 'NO_PRICE_THAT_DAY' | 'NO_HISTORY'; value?: {code: string; amount: string | number} | null};

const filled = (assetId: number, date: string, amount: string | number, code = 'EUR'): Raw => ({asset_id: assetId, date, status: 'FILLED', value: {code, amount}});
const noPrice = (assetId: number, date: string): Raw => ({asset_id: assetId, date, status: 'NO_PRICE_THAT_DAY', value: null});
const noHistory = (assetId: number, date: string): Raw => ({asset_id: assetId, date, status: 'NO_HISTORY', value: null});

/** The backend as a double: each item answered by `answer`, in the order sent. */
function answerEach(answer: (item: {asset_id: number; date: string}) => Raw) {
    query.mockImplementation((async (body: Array<{asset_id: number; date: string}>) => ({items: body.map(answer)})) as never);
}

/** The day `n` days after 2024-01-01, ISO: distinct days for long request lists. */
function dayN(n: number): string {
    return new Date(Date.UTC(2024, 0, 1 + n)).toISOString().slice(0, 10);
}

beforeEach(() => {
    query.mockReset();
});

describe('fetchRewardValues — the backend reader, in batches', () => {
    it('the batch size is the backend cap, 1 000', () => {
        expect(REWARD_VALUES_BATCH).toBe(1000);
    });

    it('asks every item as {asset_id, date}, in one call, in the order given', async () => {
        query.mockResolvedValue({items: [filled(42, DAY, '12.5'), noPrice(7, '2024-03-11')]} as never);

        await fetchRewardValues([
            {assetId: 42, date: DAY},
            {assetId: 7, date: '2024-03-11'},
        ]);

        expect(query).toHaveBeenCalledTimes(1);
        expect(query.mock.calls[0][0]).toEqual([
            {asset_id: 42, date: DAY},
            {asset_id: 7, date: '2024-03-11'},
        ]);
    });

    it('FILLED → a suggestion in the price currency, dated the reward day; the other statuses → none', async () => {
        query.mockResolvedValue({items: [filled(42, DAY, '0.985', 'USD'), noPrice(42, '2024-03-11'), noHistory(9, DAY)]} as never);

        const answers = await fetchRewardValues([
            {assetId: 42, date: DAY},
            {assetId: 42, date: '2024-03-11'},
            {assetId: 9, date: DAY},
        ]);

        expect(answers).toEqual([
            {assetId: 42, date: DAY, status: 'FILLED', suggestion: {code: 'USD', amount: '0.985', priceDate: DAY}},
            {assetId: 42, date: '2024-03-11', status: 'NO_PRICE_THAT_DAY', suggestion: null},
            {assetId: 9, date: DAY, status: 'NO_HISTORY', suggestion: null},
        ]);
    });

    it('the amount is taken as the backend gives it: never divided, a number read as its text', async () => {
        query.mockResolvedValue({items: [filled(42, DAY, '98.5'), filled(43, DAY, 61.25)]} as never);

        const answers = await fetchRewardValues([
            {assetId: 42, date: DAY},
            {assetId: 43, date: DAY},
        ]);

        expect(answers?.map((answer) => answer.suggestion?.amount)).toEqual(['98.5', '61.25']);
    });

    it('a FILLED answer without a value is no value: NO_PRICE_THAT_DAY, no suggestion', async () => {
        query.mockResolvedValue({items: [{asset_id: 42, date: DAY, status: 'FILLED', value: null}]} as never);

        expect(await fetchRewardValues([{assetId: 42, date: DAY}])).toEqual([{assetId: 42, date: DAY, status: 'NO_PRICE_THAT_DAY', suggestion: null}]);
    });

    it('an answer without items is an empty list', async () => {
        query.mockResolvedValue({} as never);

        expect(await fetchRewardValues([{assetId: 42, date: DAY}])).toEqual([]);
    });

    it('no request, no call', async () => {
        expect(await fetchRewardValues([])).toEqual([]);
        expect(query).not.toHaveBeenCalled();
    });

    it('above 1 000 items: several calls of at most 1 000, the answers in the order asked', async () => {
        const total = 2 * REWARD_VALUES_BATCH + 1;
        const requests: RewardValueRequest[] = Array.from({length: total}, (_, n) => ({assetId: 100 + (n % 3), date: dayN(n)}));
        // Odd days have a close of the day's index, even days none: the order is checked item by item
        answerEach((item) => {
            const n = requests.findIndex((request) => request.assetId === item.asset_id && request.date === item.date);
            return n % 2 === 1 ? filled(item.asset_id, item.date, String(n)) : noPrice(item.asset_id, item.date);
        });

        const answers = await fetchRewardValues(requests);

        expect(query).toHaveBeenCalledTimes(3);
        expect(query.mock.calls.map((call) => (call[0] as unknown[]).length)).toEqual([1000, 1000, 1]);
        expect(query.mock.calls.flatMap((call) => call[0] as Array<{asset_id: number; date: string}>)).toEqual(requests.map((r) => ({asset_id: r.assetId, date: r.date})));
        expect(answers).toHaveLength(total);
        answers!.forEach((answer, n) => {
            expect(answer.assetId, `answer ${n}`).toBe(requests[n].assetId);
            expect(answer.date, `answer ${n}`).toBe(requests[n].date);
            expect(answer.suggestion?.amount ?? null, `answer ${n}`).toBe(n % 2 === 1 ? String(n) : null);
        });
    });

    it('exactly 1 000 items: one call', async () => {
        const requests: RewardValueRequest[] = Array.from({length: REWARD_VALUES_BATCH}, (_, n) => ({assetId: 1, date: dayN(n)}));
        answerEach((item) => noHistory(item.asset_id, item.date));

        expect(await fetchRewardValues(requests)).toHaveLength(REWARD_VALUES_BATCH);
        expect(query).toHaveBeenCalledTimes(1);
    });

    it('a failed call is null, never a throw', async () => {
        query.mockRejectedValue(new Error('network down'));

        await expect(fetchRewardValues([{assetId: 42, date: DAY}])).resolves.toBeNull();
        expect(query).toHaveBeenCalledTimes(1);
    });

    it('a failure in a later batch is null for the whole list: nothing partial is handed on', async () => {
        const requests: RewardValueRequest[] = Array.from({length: REWARD_VALUES_BATCH + 5}, (_, n) => ({assetId: 1, date: dayN(n)}));
        query.mockImplementationOnce((async (body: Array<{asset_id: number; date: string}>) => ({items: body.map((item) => filled(item.asset_id, item.date, '1'))})) as never);
        query.mockRejectedValueOnce(new Error('second batch failed'));

        await expect(fetchRewardValues(requests)).resolves.toBeNull();
        expect(query).toHaveBeenCalledTimes(2);
    });
});

describe('fetchRewardValue — one reward', () => {
    it('asks one item and returns its suggestion, dated the reward day', async () => {
        query.mockResolvedValue({items: [filled(42, DAY, '61.25', 'USD')]} as never);

        expect(await fetchRewardValue(42, DAY)).toEqual({code: 'USD', amount: '61.25', priceDate: DAY});
        expect(query).toHaveBeenCalledTimes(1);
        expect(query.mock.calls[0][0]).toEqual([{asset_id: 42, date: DAY}]);
    });

    it.each([
        ['no close that day', noPrice(42, DAY)],
        ['no history', noHistory(42, DAY)],
    ] as const)('%s: null — no value is ever invented', async (_label, raw) => {
        query.mockResolvedValue({items: [raw]} as never);

        expect(await fetchRewardValue(42, DAY)).toBeNull();
    });

    it('an answer for another asset or another day fills nothing', async () => {
        query.mockResolvedValueOnce({items: [filled(41, DAY, '99')]} as never);
        expect(await fetchRewardValue(42, DAY), 'another asset').toBeNull();

        query.mockResolvedValueOnce({items: [filled(42, '2024-03-09', '99')]} as never);
        expect(await fetchRewardValue(42, DAY), 'another day').toBeNull();

        query.mockResolvedValueOnce({items: []} as never);
        expect(await fetchRewardValue(42, DAY), 'no item').toBeNull();
    });

    it('null, never a throw, when the call fails', async () => {
        query.mockRejectedValue(new Error('network down'));

        await expect(fetchRewardValue(42, DAY)).resolves.toBeNull();
    });
});
