/**
 * rewardValue.ts (project 79, STK-2a): the value on receipt the transaction form suggests for a REWARD.
 *
 * - `rewardValueFromPoints(points, date, quoteBase)`: the last point dated on or before `date` with a positive close and a
 *   currency, per unit (the close divided by a quote base above 1); `null` when there is none. Pure.
 * - `fetchRewardValue(assetId, date, quoteBase)`: one price query for [date, date], the item of `assetId` read through
 *   the function above; `null` without that item or when the call fails.
 *
 * Node env. `$lib/api` is mocked with only the one call the module makes (same pattern as comparisonSeries.test.ts).
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: {
        query_prices_bulk_api_v1_assets_prices_query_post: vi.fn(),
    },
}));

import {zodiosApi} from '$lib/api';
import {fetchRewardValue, rewardValueFromPoints, type RewardPricePoint} from './rewardValue';

const query = vi.mocked(zodiosApi.query_prices_bulk_api_v1_assets_prices_query_post);

const DAY = '2024-03-10';

const point = (date: string, close: RewardPricePoint['close'], currency: RewardPricePoint['currency'] = 'EUR'): RewardPricePoint => ({date, close, currency});

describe('rewardValueFromPoints — the close of the day, or the last one before it', () => {
    it('a close on the reward day is the suggestion, in its currency, dated that day', () => {
        expect(rewardValueFromPoints([point('2024-03-08', '10'), point(DAY, '12.5')], DAY, 1)).toEqual({code: 'EUR', amount: '12.5', priceDate: DAY});
    });

    it('without a close on the day, the last earlier one: its own date travels with it', () => {
        expect(rewardValueFromPoints([point('2024-03-07', '9'), point('2024-03-08', '10')], DAY, 1)).toEqual({code: 'EUR', amount: '10', priceDate: '2024-03-08'});
    });

    it('a point after the reward day is never read, even when it is the only later one', () => {
        expect(rewardValueFromPoints([point('2024-03-09', '11'), point('2024-03-11', '99')], DAY, 1)).toEqual({code: 'EUR', amount: '11', priceDate: '2024-03-09'});
        expect(rewardValueFromPoints([point('2024-03-11', '99')], DAY, 1), 'only a later point: no suggestion').toBeNull();
    });

    it('the order of the points does not matter: the latest date on or before the day wins', () => {
        expect(rewardValueFromPoints([point(DAY, '12'), point('2024-03-01', '5'), point('2024-03-08', '10')], DAY, 1)).toEqual({code: 'EUR', amount: '12', priceDate: DAY});
    });

    it.each([
        ['zero', '0'],
        ['zero with decimals', '0.000000'],
        ['negative', '-3'],
        ['blank', '   '],
        ['empty', ''],
        ['null', null],
        ['undefined', undefined],
        ['not a number', 'n/a'],
    ] as const)('a %s close is no price: the last valid earlier close is used', (_label, close) => {
        expect(rewardValueFromPoints([point('2024-03-08', '10'), point(DAY, close)], DAY, 1)).toEqual({code: 'EUR', amount: '10', priceDate: '2024-03-08'});
    });

    it.each([
        ['null', null],
        ['undefined', undefined],
        ['empty', ''],
    ] as const)('a close with a %s currency is no price: the last earlier close with one is used', (_label, currency) => {
        // A literal, not `point()`: its default currency would turn `undefined` into EUR.
        const withoutCurrency: RewardPricePoint = {date: DAY, close: '12', currency};
        expect(rewardValueFromPoints([point('2024-03-08', '10', 'USD'), withoutCurrency], DAY, 1)).toEqual({code: 'USD', amount: '10', priceDate: '2024-03-08'});
    });

    it('a numeric close is read as its decimal text', () => {
        expect(rewardValueFromPoints([point(DAY, 12.5)], DAY, 1)).toEqual({code: 'EUR', amount: '12.5', priceDate: DAY});
    });

    it('a close with blanks around it is trimmed', () => {
        expect(rewardValueFromPoints([point(DAY, ' 12.5 ')], DAY, 1)?.amount).toBe('12.5');
    });

    it('a quote base of 100 (a bond quoted per 100) divides the close: the value is per unit', () => {
        expect(rewardValueFromPoints([point(DAY, '98.5')], DAY, 100)).toEqual({code: 'EUR', amount: '0.985', priceDate: DAY});
        expect(rewardValueFromPoints([point(DAY, '101.25')], DAY, 100)?.amount).toBe('1.0125');
    });

    it.each([
        ['1', 1],
        ['null', null],
        ['undefined', undefined],
        ['0', 0],
        ['negative', -100],
    ] as const)('a quote base of %s leaves the close as it is', (_label, base) => {
        expect(rewardValueFromPoints([point(DAY, '98.5')], DAY, base)?.amount).toBe('98.5');
    });

    it('no points, or none valid: null — no value is ever invented', () => {
        expect(rewardValueFromPoints([], DAY, 1)).toBeNull();
        expect(rewardValueFromPoints([point(DAY, '0'), point('2024-03-08', '5', null), point('2024-03-11', '7')], DAY, 1)).toBeNull();
    });
});

describe('fetchRewardValue — one price query for the reward day', () => {
    beforeEach(() => {
        query.mockReset();
    });

    it('asks the prices of that asset for [date, date], prices only, in one call', async () => {
        query.mockResolvedValue({items: [{asset_id: 42, prices: [point(DAY, '12.5')]}]} as never);

        await fetchRewardValue(42, DAY, 1);

        expect(query).toHaveBeenCalledTimes(1);
        expect(query.mock.calls[0][0]).toEqual([{asset_id: 42, date_range: {start: DAY, end: DAY}, include_price: true, include_events: false}]);
    });

    it('reads the item of the asked asset, wherever it sits in the answer', async () => {
        query.mockResolvedValue({
            items: [
                {asset_id: 41, prices: [point(DAY, '99', 'USD')]},
                {asset_id: 42, prices: [point('2024-03-08', '12.5', 'EUR')]},
            ],
        } as never);

        expect(await fetchRewardValue(42, DAY, 1)).toEqual({code: 'EUR', amount: '12.5', priceDate: '2024-03-08'});
    });

    it('passes the quote base on: a close per 100 becomes a value per unit', async () => {
        query.mockResolvedValue({items: [{asset_id: 42, prices: [point(DAY, '98.5')]}]} as never);

        expect((await fetchRewardValue(42, DAY, 100))?.amount).toBe('0.985');
    });

    it('null when the answer holds no item for the asset, or an item without prices', async () => {
        query.mockResolvedValueOnce({items: [{asset_id: 41, prices: [point(DAY, '99')]}]} as never);
        expect(await fetchRewardValue(42, DAY, 1), 'another asset only').toBeNull();

        query.mockResolvedValueOnce({items: []} as never);
        expect(await fetchRewardValue(42, DAY, 1), 'no items').toBeNull();

        query.mockResolvedValueOnce({items: [{asset_id: 42}]} as never);
        expect(await fetchRewardValue(42, DAY, 1), 'an item without prices').toBeNull();

        query.mockResolvedValueOnce({} as never);
        expect(await fetchRewardValue(42, DAY, 1), 'an answer without items').toBeNull();
    });

    it('null, never a throw, when the call fails', async () => {
        query.mockRejectedValue(new Error('network down'));

        await expect(fetchRewardValue(42, DAY, 1)).resolves.toBeNull();
        expect(query).toHaveBeenCalledTimes(1);
    });
});
