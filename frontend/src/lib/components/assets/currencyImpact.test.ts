/**
 * currencyImpact — unit tests (Vitest, node). Workstream X, lot X5-3 (N68, developer decision 19/10/2026).
 *
 * Why. Changing an asset's currency is no longer blocked. `PATCH /assets/patch` always succeeds and, in the same call,
 * deletes the asset's prices and every event that is not a SPLIT, and disconnects the transactions linked to a deleted
 * event; the SPLIT events, and the transactions linked to them, are kept. So the asset modal asks the server's dry run
 * first, `GET /assets/{id}/market-data/summary` (zodios alias `market_data_summary_api_v1_assets__asset_id__market_data_summary_get`),
 * and tells the user how much goes before it is done. This module is the modal's half: it asks, and decides whether there
 * is anything to say. It replaces `currencyBlocker.ts`, which parsed the pipe-delimited token the old blocked PATCH
 * answered with (that token and the 409 no longer exist).
 *
 * Contract.
 *   - `loadCurrencyChangeImpact(assetId, from, to)` calls the alias ONCE, with `{params: {asset_id}}`, and answers
 *     `{assetId, from, to, prices, eventsManual, eventsProvider, splitsKept, linkedTx, oldest, newest}` from the server's
 *     `{prices, events_manual, events_provider, splits_kept, linked_tx, oldest, newest, dry_run}`. A count that is missing,
 *     negative, not a number or not finite is 0; a date that is null, missing or not a string is the empty string. Unlike
 *     the provider dialog's dry run (`providerImpact.ts`: advice, never a gate) THIS ONE IS A GATE: when the request fails
 *     the promise REJECTS (with the request's own error), so the save does not go on blind.
 *   - `hasSomethingToLose(impact)` is `prices + eventsManual + eventsProvider + linkedTx > 0`. `splitsKept` alone is not a
 *     loss: the splits stay, it is only information for the dialog.
 *
 * How. The API facade is replaced (offline, nothing is requested). No text is read: the module returns numbers and dates.
 *
 * Expected. Red before the cure, by absence: `currencyImpact.ts` does not exist, so the file fails to load.
 * Registered in `scripts/test_runner/_frontend_utility.py` (Vitest list of `front_utility_unit`, action `core-unit`),
 * in the place `currencyBlocker.test.ts` had.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const mocks = vi.hoisted(() => ({
    api: {market_data_summary_api_v1_assets__asset_id__market_data_summary_get: vi.fn()},
}));
vi.mock('$lib/api', () => ({zodiosApi: mocks.api}));

import {hasSomethingToLose, loadCurrencyChangeImpact, type CurrencyChangeImpact} from './currencyImpact';

const ASSET = 8101;
const summaryCall = mocks.api.market_data_summary_api_v1_assets__asset_id__market_data_summary_get;

/** The server's dry-run answer, every field a test does not name at its default. */
function summary(over: Record<string, unknown> = {}) {
    return {prices: 12, events_manual: 2, events_provider: 3, splits_kept: 1, linked_tx: 4, oldest: '2020-01-02', newest: '2024-05-06', dry_run: true, ...over};
}

/** An impact as the dialog receives it, for the predicate's cases. */
function impactOf(over: Partial<CurrencyChangeImpact> = {}): CurrencyChangeImpact {
    return {assetId: ASSET, from: 'USD', to: 'EUR', prices: 0, eventsManual: 0, eventsProvider: 0, splitsKept: 0, linkedTx: 0, oldest: '', newest: '', ...over};
}

beforeEach(() => {
    summaryCall.mockReset();
});

describe('loadCurrencyChangeImpact — the dry run', () => {
    it('asks the summary operation once, for that asset, with path params and nothing else', async () => {
        summaryCall.mockResolvedValue(summary());

        await loadCurrencyChangeImpact(ASSET, 'USD', 'EUR');

        expect(summaryCall).toHaveBeenCalledTimes(1);
        expect(summaryCall).toHaveBeenCalledWith({params: {asset_id: ASSET}});
    });

    it('maps the counts and dates to camelCase and carries the asset and both currencies from the caller', async () => {
        // Every count distinct, so a swapped pair reads otherwise.
        summaryCall.mockResolvedValue(summary({prices: 11, events_manual: 22, events_provider: 33, splits_kept: 44, linked_tx: 55, oldest: '2019-03-04', newest: '2025-06-07'}));

        const impact = await loadCurrencyChangeImpact(ASSET, 'USD', 'EUR');

        expect(impact).toEqual({assetId: ASSET, from: 'USD', to: 'EUR', prices: 11, eventsManual: 22, eventsProvider: 33, splitsKept: 44, linkedTx: 55, oldest: '2019-03-04', newest: '2025-06-07'});
    });

    it('an empty asset: every count 0 and both dates the empty string', async () => {
        summaryCall.mockResolvedValue(summary({prices: 0, events_manual: 0, events_provider: 0, splits_kept: 0, linked_tx: 0, oldest: null, newest: null}));

        const impact = await loadCurrencyChangeImpact(ASSET, 'USD', 'EUR');

        expect(impact).toMatchObject({prices: 0, eventsManual: 0, eventsProvider: 0, splitsKept: 0, linkedTx: 0, oldest: '', newest: ''});
    });

    it.each<[string, Record<string, unknown>]>([
        ['missing', {}],
        ['null', {prices: null, events_manual: null, events_provider: null, splits_kept: null, linked_tx: null}],
        ['negative', {prices: -3, events_manual: -1, events_provider: -2, splits_kept: -4, linked_tx: -5}],
        ['not numbers', {prices: 'many', events_manual: {}, events_provider: [], splits_kept: 'x', linked_tx: 'n/a'}],
        ['not finite', {prices: Number.NaN, events_manual: Number.POSITIVE_INFINITY, events_provider: Number.NEGATIVE_INFINITY, splits_kept: Number.NaN, linked_tx: Number.NaN}],
    ])('counts that are %s are 0 — never NaN, never negative', async (_label, counts) => {
        // `summary` is not spread: the keys must be missing, not defaulted.
        summaryCall.mockResolvedValue({oldest: '2020-01-02', newest: '2024-05-06', dry_run: true, ...counts});

        const impact = await loadCurrencyChangeImpact(ASSET, 'USD', 'EUR');

        expect(impact).toMatchObject({prices: 0, eventsManual: 0, eventsProvider: 0, splitsKept: 0, linkedTx: 0});
    });

    it.each<[string, unknown]>([
        ['null', null],
        ['missing', undefined],
        ['a number', 20240102],
        ['an object', {year: 2024}],
    ])('a date that is %s is the empty string — never "null", never [object Object]', async (_label, date) => {
        summaryCall.mockResolvedValue(summary({oldest: date, newest: date}));

        const impact = await loadCurrencyChangeImpact(ASSET, 'USD', 'EUR');

        expect(impact.oldest).toBe('');
        expect(impact.newest).toBe('');
    });

    it.each<[string, unknown]>([
        ['undefined', undefined],
        ['null', null],
        ['a string', 'ok'],
        ['a list', []],
    ])('an answer that is %s reads as an empty asset (all 0, dates empty), not as a failure', async (_label, answer) => {
        summaryCall.mockResolvedValue(answer);

        const impact = await loadCurrencyChangeImpact(ASSET, 'USD', 'EUR');

        expect(impact).toEqual(impactOf());
    });

    it('is a GATE: a failed request rejects with the request’s own error — nothing is swallowed into an empty impact', async () => {
        const failure = Object.assign(new Error('Network Error'), {response: {status: 500}});
        summaryCall.mockRejectedValue(failure);

        await expect(loadCurrencyChangeImpact(ASSET, 'USD', 'EUR')).rejects.toBe(failure);
    });

    it('a 404 or a 422 rejects too (the save must not go on without knowing what it deletes)', async () => {
        for (const status of [404, 422]) {
            summaryCall.mockRejectedValueOnce(Object.assign(new Error(`status ${status}`), {response: {status}}));
            await expect(loadCurrencyChangeImpact(ASSET, 'USD', 'EUR')).rejects.toMatchObject({response: {status}});
        }
    });
});

describe('hasSomethingToLose', () => {
    it('is false for an empty impact', () => {
        expect(hasSomethingToLose(impactOf())).toBe(false);
    });

    it.each<[string, Partial<CurrencyChangeImpact>]>([
        ['prices', {prices: 1}],
        ['manual events', {eventsManual: 1}],
        ['provider events', {eventsProvider: 1}],
        ['linked transactions', {linkedTx: 1}],
    ])('is true when only %s are there', (_label, over) => {
        expect(hasSomethingToLose(impactOf(over))).toBe(true);
    });

    it('is false when only kept splits are there: they stay, they are information and no loss', () => {
        expect(hasSomethingToLose(impactOf({splitsKept: 3}))).toBe(false);
    });

    it('is true when something is lost and splits are kept as well', () => {
        expect(hasSomethingToLose(impactOf({splitsKept: 2, eventsManual: 1}))).toBe(true);
    });

    it('does not read the dates: a range with no count is no loss', () => {
        expect(hasSomethingToLose(impactOf({oldest: '2020-01-01', newest: '2024-01-01'}))).toBe(false);
    });
});
