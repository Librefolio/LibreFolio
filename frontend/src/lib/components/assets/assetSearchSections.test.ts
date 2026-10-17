/**
 * assetSearchSections — pure unit tests (F21, workstream X sub-lot 3).
 *
 * Where a result stands in the asset search. Every provider of `GET /assets/provider` carries a tier
 * (`premium` | `community`, community when missing) and a priority (lower first, 100 when missing); the REST
 * search already answers in that order, the streamed one sends each provider's results as they arrive, so the
 * dropdown orders them with these functions.
 *
 * Two properties carry the decision D-X3 and are pinned on their own: the sort is stable — results of the same
 * rank keep the order they were given in, interleaved or not, never regrouped by provider — and with every
 * provider at its defaults that order is the arrival order, untouched: an instance without a premium provider
 * searches exactly as before.
 *
 * Inputs are deep-frozen, so an in-place sort or write throws (ES modules run in strict mode).
 */
import {describe, expect, it} from 'vitest';
import {DEFAULT_SEARCH_PRIORITY, hasPremium, orderSearchResults, searchRank, splitSearchResults, type RankedProvider} from './assetSearchSections';

/** A result as far as the order is concerned: the provider that returned it, and an id to follow it by. */
interface Result {
    provider_code: string;
    id: string;
}

const result = (provider_code: string, id: string): Result => ({provider_code, id});
const idsOf = (results: readonly Result[]): string[] => results.map((r) => r.id);

/** Freezes `value` and everything inside it, so an in-place write throws (ES modules run in strict mode). */
function deepFreeze<T>(value: T): T {
    if (value !== null && typeof value === 'object') {
        for (const nested of Object.values(value as Record<string, unknown>)) deepFreeze(nested);
        Object.freeze(value);
    }
    return value;
}

/** The providers of these tests, as `GET /assets/provider` may answer them. */
const PROVIDERS = deepFreeze<RankedProvider[]>([
    {code: 'vault', tier: 'premium', priority: 5},
    {code: 'prime', tier: 'premium', priority: 20},
    {code: 'zero', tier: 'premium', priority: 0},
    {code: 'plain_premium', tier: 'premium'},
    {code: 'nought', tier: 'community', priority: 0},
    {code: 'early', tier: 'community', priority: 1},
    {code: 'beta', tier: 'community', priority: 50},
    {code: 'alpha', tier: 'community', priority: 100},
    {code: 'bare'},
    {code: 'nulls', tier: null, priority: null},
    {code: 'late', priority: 300},
]);

describe('DEFAULT_SEARCH_PRIORITY', () => {
    it('is the backend default: 100', () => {
        expect(DEFAULT_SEARCH_PRIORITY).toBe(100);
    });
});

describe('searchRank', () => {
    it.each<[string, [number, number]]>([
        ['vault', [0, 5]],
        ['prime', [0, 20]],
        ['plain_premium', [0, 100]],
        ['early', [1, 1]],
        ['beta', [1, 50]],
        ['alpha', [1, 100]],
        ['bare', [1, 100]],
        ['nulls', [1, 100]],
        ['late', [1, 300]],
    ])('ranks %s at %j: 0 for premium, 1 otherwise, then its priority (100 when it declares none)', (code, rank) => {
        expect(searchRank(code, PROVIDERS)).toStrictEqual(rank);
    });

    it('keeps a priority of 0: the first place, not a missing priority', () => {
        expect(searchRank('zero', PROVIDERS)).toStrictEqual([0, 0]);
        expect(searchRank('nought', PROVIDERS)).toStrictEqual([1, 0]);
    });

    it('ranks a code the list does not know as a community provider at the default priority', () => {
        expect(searchRank('unknown', PROVIDERS)).toStrictEqual([1, 100]);
        expect(searchRank('alpha', [])).toStrictEqual([1, 100]);
    });
});

describe('orderSearchResults', () => {
    it('puts premium first, then lower priority, whatever the order of arrival', () => {
        const arrival = deepFreeze([
            result('late', 'late-1'),
            result('alpha', 'alpha-1'),
            result('prime', 'prime-1'),
            result('early', 'early-1'),
            result('unknown', 'unknown-1'),
            result('beta', 'beta-1'),
            result('vault', 'vault-1'),
            result('nought', 'nought-1'),
            result('zero', 'zero-1'),
            result('plain_premium', 'plain-1'),
        ]);

        expect(idsOf(orderSearchResults(arrival, PROVIDERS))).toEqual([
            'zero-1', // [0, 0]
            'vault-1', // [0, 5]
            'prime-1', // [0, 20]
            'plain-1', // [0, 100]: premium at the default still comes before any community result
            'nought-1', // [1, 0]
            'early-1', // [1, 1]
            'beta-1', // [1, 50]
            'alpha-1', // [1, 100], arrived before the unknown code's
            'unknown-1', // [1, 100]
            'late-1', // [1, 300]
        ]);
    });

    it('is stable: results of the same rank keep the given order, interleaved across providers, never regrouped', () => {
        // bare, alpha, nulls and a code the list does not know all rank [1, 100]: 24 results, mixed as they came.
        const tied = ['bare', 'alpha', 'nulls', 'unknown'];
        const ties = Array.from({length: 24}, (_, i) => result(tied[i % tied.length], `tie-${i}`));
        const arrival = deepFreeze([...ties.slice(0, 12), result('prime', 'prime-1'), ...ties.slice(12), result('beta', 'beta-1')]);

        expect(idsOf(orderSearchResults(arrival, PROVIDERS))).toEqual(['prime-1', 'beta-1', ...idsOf(ties)]);
    });

    it('keeps the results of one provider in the order that provider gave them', () => {
        const arrival = deepFreeze([result('alpha', 'a3'), result('prime', 'p2'), result('alpha', 'a1'), result('prime', 'p9'), result('alpha', 'a2')]);

        expect(idsOf(orderSearchResults(arrival, PROVIDERS))).toEqual(['p2', 'p9', 'a3', 'a1', 'a2']);
    });

    it('with every provider at its defaults, the order is the order of arrival (D-X3)', () => {
        const defaults = deepFreeze<RankedProvider[]>([{code: 'alpha'}, {code: 'beta', tier: 'community', priority: 100}, {code: 'gamma', tier: null, priority: null}]);
        const arrival = deepFreeze([result('beta', 'b1'), result('alpha', 'a1'), result('stray', 's1'), result('gamma', 'g1'), result('alpha', 'a2'), result('beta', 'b2')]);

        expect(orderSearchResults(arrival, defaults)).toStrictEqual(arrival);
    });

    it('with no provider list at all, every result is community at the default: the order of arrival', () => {
        const arrival = deepFreeze([result('prime', 'p1'), result('alpha', 'a1'), result('prime', 'p2')]);

        expect(idsOf(orderSearchResults(arrival, []))).toEqual(['p1', 'a1', 'p2']);
    });

    it('returns a new array and leaves the given one as it was', () => {
        const arrival = deepFreeze([result('alpha', 'a1'), result('prime', 'p1')]);

        const ordered = orderSearchResults(arrival, PROVIDERS);

        expect(ordered).not.toBe(arrival);
        expect(idsOf(ordered)).toEqual(['p1', 'a1']);
        expect(idsOf(arrival)).toEqual(['a1', 'p1']);
    });

    it('returns a new array even when nothing moves, or when there is nothing', () => {
        const single = deepFreeze([result('alpha', 'a1')]);
        expect(orderSearchResults(single, PROVIDERS)).not.toBe(single);

        const none = deepFreeze<Result[]>([]);
        const ordered = orderSearchResults(none, PROVIDERS);
        expect(ordered).toEqual([]);
        expect(ordered).not.toBe(none);
    });

    it('hands back the results whole, every field of theirs intact', () => {
        const results = deepFreeze([
            {provider_code: 'alpha', identifier: 'US0378331005', display_name: 'Apple Inc', currency: 'USD', via_web: false},
            {provider_code: 'prime', identifier: 'US5949181045', display_name: 'Microsoft', currency: null, via_web: true},
        ]);

        expect(orderSearchResults(results, PROVIDERS)).toStrictEqual([results[1], results[0]]);
    });
});

describe('hasPremium', () => {
    it('is true when one of the codes is a premium provider', () => {
        expect(hasPremium(['alpha', 'beta', 'prime'], PROVIDERS)).toBe(true);
        expect(hasPremium(['plain_premium'], PROVIDERS)).toBe(true);
        expect(hasPremium(['zero'], PROVIDERS), 'a premium provider at priority 0 is premium all the same').toBe(true);
    });

    it('is false when none of them is, even with premium providers elsewhere in the list', () => {
        expect(hasPremium(['alpha', 'beta', 'bare', 'nulls', 'early', 'nought', 'late'], PROVIDERS)).toBe(false);
    });

    it('does not take a code the list does not know for a premium one', () => {
        expect(hasPremium(['unknown', 'stray'], PROVIDERS)).toBe(false);
        expect(hasPremium(['prime'], [])).toBe(false);
    });

    it('is false for no code at all', () => {
        expect(hasPremium([], PROVIDERS)).toBe(false);
    });
});

describe('splitSearchResults', () => {
    it('splits the premium results from the others, each side in the given order — no sort of its own', () => {
        // vault ranks before prime and beta before alpha: the split keeps them as given all the same.
        const given = deepFreeze([result('prime', 'p1'), result('alpha', 'a1'), result('vault', 'v1'), result('beta', 'b1'), result('prime', 'p2'), result('early', 'e1')]);

        const {premium, community} = splitSearchResults(given, PROVIDERS);

        expect(idsOf(premium)).toEqual(['p1', 'v1', 'p2']);
        expect(idsOf(community)).toEqual(['a1', 'b1', 'e1']);
        expect(idsOf(given), 'the given list is left as it was').toEqual(['p1', 'a1', 'v1', 'b1', 'p2', 'e1']);
    });

    it('puts a result of a provider the list does not know with the community', () => {
        const given = deepFreeze([result('unknown', 'u1'), result('prime', 'p1'), result('stray', 's1')]);

        const {premium, community} = splitSearchResults(given, PROVIDERS);

        expect(idsOf(premium)).toEqual(['p1']);
        expect(idsOf(community)).toEqual(['u1', 's1']);
    });

    it('without a premium provider, premium is empty and the community side is everything, as given', () => {
        const given = deepFreeze([result('beta', 'b1'), result('alpha', 'a1'), result('bare', 'x1')]);

        expect(splitSearchResults(given, PROVIDERS)).toEqual({premium: [], community: [given[0], given[1], given[2]]});
    });

    it('with nothing to split, both sides are empty', () => {
        expect(splitSearchResults([], PROVIDERS)).toEqual({premium: [], community: []});
    });
});
