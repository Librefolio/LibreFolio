/**
 * The client cache of the backend's signal answers (N64): the answer the asset page reads from `POST /assets/prices/query`
 * and the signal results the FX page reads for its pair, kept beside the price stores so that a return to a range, a
 * period or a signal set already drawn needs no new request — the way the price cache already spares the prices.
 *
 * An answer is filed under a **key** (the request, canonical: the same request is the same text whatever the order of
 * its properties) together with the **generations** of the stores it was drawn over (`TimeSeriesStore.generation`). It
 * is taken back only while every generation is what it was: a store that was emptied, had a range invalidated or was
 * marked stale by a price catch-up has moved on, and the answer asks again. A mismatch is a miss that drops the entry.
 * The cache is a small LRU (32 entries by default) and keeps its values apart from the caller's: what was given, and what
 * was read, are copies, so no later mutation reaches a cached answer. Two singletons hold the two kinds of answer, and
 * both are emptied when the signed-in account changes: an answer is the previous user's data.
 *
 * Red first: the module does not exist.
 */
import {afterEach, describe, expect, it} from 'vitest';

import type {BackendSignalResult} from '$lib/charts/signals/backendTypes';
import {transitionClientSession} from '$lib/stores/app/clientSession';

import type {ComparisonAssetsLoadResult} from '$lib/charts/loadComparisonData';
import {assetChartAnswers, canonicalCacheKey, clearAssetPageAnswers, comparisonSeriesAnswers, fxSignalAnswers, SignalResultCache, type AssetChartAnswer} from '$lib/stores/signalResultCache';

/** An answer with a shape of its own: nested arrays and objects, so that a shallow copy shows. */
interface Answer {
    items: Array<{id: number; points: number[]}>;
}

function answer(id: number): Answer {
    return {items: [{id, points: [id, id + 1, id + 2]}]};
}

function deepFreeze<T>(value: T): T {
    if (value !== null && typeof value === 'object') {
        for (const inner of Object.values(value)) deepFreeze(inner);
        Object.freeze(value);
    }
    return value;
}

/** The generations of two stores, as a page reads them. */
const G = [4, 9] as const;

afterEach(() => {
    assetChartAnswers.clear();
    comparisonSeriesAnswers.clear();
    fxSignalAnswers.clear();
});

describe('canonicalCacheKey: the same value is the same text, whatever the order of its properties', () => {
    it('sorts the keys of an object at every depth, as JSON text', () => {
        expect(canonicalCacheKey({b: 1, a: {d: [1, 2], c: 'x'}})).toBe('{"a":{"c":"x","d":[1,2]},"b":1}');
    });

    it('gives one text to two objects that differ only in the order of their properties, at any depth', () => {
        const one = {date_range: {start: '2026-01-01', end: '2026-06-30'}, asset_id: 7, signals: [{params: {window_days: 30, mode: 'a'}, instance_id: 'cal'}]};
        const other = {signals: [{instance_id: 'cal', params: {mode: 'a', window_days: 30}}], asset_id: 7, date_range: {end: '2026-06-30', start: '2026-01-01'}};

        expect(canonicalCacheKey(one), 'the key follows the order the properties were written in: the same request would miss the cache').toBe(canonicalCacheKey(other));
    });

    it('keeps the order of an array, and sorts the objects inside it', () => {
        expect(canonicalCacheKey([2, 1])).toBe('[2,1]');
        expect(canonicalCacheKey([2, 1]), 'an array is ordered: [2, 1] is not [1, 2]').not.toBe(canonicalCacheKey([1, 2]));
        expect(
            canonicalCacheKey([
                {b: 1, a: 2},
                {d: 3, c: 4},
            ]),
        ).toBe('[{"a":2,"b":1},{"c":4,"d":3}]');
    });

    it('omits an undefined property, as JSON.stringify does: an absent value and an undefined one are the same request', () => {
        expect(canonicalCacheKey({target_currency: undefined, asset_id: 7})).toBe('{"asset_id":7}');
        expect(canonicalCacheKey({asset_id: 7, nested: {gone: undefined}})).toBe(canonicalCacheKey({asset_id: 7, nested: {}}));
    });

    it('tells apart values that are not the same request: a string and a number, null and a missing property, different values', () => {
        const keys = [canonicalCacheKey({a: 1}), canonicalCacheKey({a: '1'}), canonicalCacheKey({a: null}), canonicalCacheKey({}), canonicalCacheKey({a: 2})];

        expect(new Set(keys).size).toBe(keys.length);
    });

    it('writes a primitive as its JSON text', () => {
        expect(canonicalCacheKey(5)).toBe('5');
        expect(canonicalCacheKey('x')).toBe('"x"');
        expect(canonicalCacheKey(null)).toBe('null');
        expect(canonicalCacheKey([])).toBe('[]');
    });

    it('leaves its argument as it found it', () => {
        const value = {b: {y: 1, x: 2}, a: [{d: 1, c: 2}]};
        const before = structuredClone(value);

        canonicalCacheKey(value);

        expect(value, 'the key sorted the caller’s object in place').toEqual(before);
        expect(Object.keys(value), 'the property order of the caller’s object changed').toEqual(['b', 'a']);
        expect(Object.keys(value.b)).toEqual(['y', 'x']);
    });
});

describe('SignalResultCache: an answer is taken back only while every generation it was drawn over is the same', () => {
    it('answers nothing before anything was set, and size counts no entry', () => {
        const cache = new SignalResultCache<Answer>();

        expect(cache.get('k', G)).toBeNull();
        expect(cache.size).toBe(0);
    });

    it('answers the value that was set when the generations are the same, element by element', () => {
        const cache = new SignalResultCache<Answer>();

        cache.set('k', G, answer(1));

        expect(cache.get('k', G)).toEqual(answer(1));
        expect(cache.get('k', [4, 9]), 'the same numbers in another array are the same generations').toEqual(answer(1));
        expect(cache.size, 'a hit keeps the entry').toBe(1);
    });

    it('keeps the keys apart', () => {
        const cache = new SignalResultCache<Answer>();
        cache.set('a', G, answer(1));
        cache.set('b', G, answer(2));

        expect(cache.get('a', G)).toEqual(answer(1));
        expect(cache.get('b', G)).toEqual(answer(2));
        expect(cache.get('c', G), 'a key never set').toBeNull();
        expect(cache.size, 'a miss on an absent key drops nothing').toBe(2);
    });

    it('is a miss when one generation differs, in either position', () => {
        const first = new SignalResultCache<Answer>();
        first.set('k', G, answer(1));
        expect(first.get('k', [5, 9]), 'the first store moved on').toBeNull();

        const second = new SignalResultCache<Answer>();
        second.set('k', G, answer(1));
        expect(second.get('k', [4, 10]), 'the second store moved on').toBeNull();
    });

    it('is a miss when the same generations come in another order: the position says which store', () => {
        const cache = new SignalResultCache<Answer>();
        cache.set('k', [4, 9], answer(1));

        expect(cache.get('k', [9, 4])).toBeNull();
    });

    it('is a miss when the number of generations differs, either way — a prefix is not a match', () => {
        const longer = new SignalResultCache<Answer>();
        longer.set('k', [4, 9], answer(1));
        expect(longer.get('k', [4]), 'fewer stores than the answer was drawn over').toBeNull();

        const shorter = new SignalResultCache<Answer>();
        shorter.set('k', [4], answer(1));
        expect(shorter.get('k', [4, 9]), 'more stores than the answer was drawn over').toBeNull();
    });

    it('takes no generations for no generations: an answer drawn over no store answers the empty list only', () => {
        const cache = new SignalResultCache<Answer>();
        cache.set('k', [], answer(1));

        expect(cache.get('k', [])).toEqual(answer(1));
        expect(cache.get('k', [4])).toBeNull();
    });

    it('drops the entry on a generation mismatch: size goes down, and the old generations no longer find it', () => {
        const cache = new SignalResultCache<Answer>();
        cache.set('k', G, answer(1));
        cache.set('other', G, answer(2));
        expect(cache.size, 'premise').toBe(2);

        expect(cache.get('k', [5, 9])).toBeNull();

        expect(cache.size, 'a stale entry stays in the cache, taking room from the live ones').toBe(1);
        expect(cache.get('k', G), 'the entry went with the miss: the answer it held was drawn over a state that is gone').toBeNull();
        expect(cache.get('other', G), 'the miss touched its own entry only').toEqual(answer(2));
    });
});

describe('SignalResultCache: set, and the least recently used past maxEntries', () => {
    it('replaces the entry of the same key: its value and its generations, not a second entry', () => {
        const cache = new SignalResultCache<Answer>();
        cache.set('k', [1], answer(1));

        cache.set('k', [2], answer(3));

        expect(cache.size).toBe(1);
        expect(cache.get('k', [2])).toEqual(answer(3));
    });

    it('forgets the old generations of a replaced entry', () => {
        const cache = new SignalResultCache<Answer>();
        cache.set('k', [1], answer(1));
        cache.set('k', [2], answer(3));

        expect(cache.get('k', [1]), 'the replaced entry answered for the generations it had before').toBeNull();
    });

    it('drops the least recently used entry past maxEntries', () => {
        const cache = new SignalResultCache<Answer>(3);
        cache.set('a', G, answer(1));
        cache.set('b', G, answer(2));
        cache.set('c', G, answer(3));

        cache.set('d', G, answer(4));

        expect(cache.size, 'past maxEntries the cache holds maxEntries').toBe(3);
        expect(cache.get('a', G), 'the first set and never read: the least recently used').toBeNull();
        expect(cache.get('b', G)).toEqual(answer(2));
        expect(cache.get('c', G)).toEqual(answer(3));
        expect(cache.get('d', G)).toEqual(answer(4));
    });

    it('makes a hit the most recently used: the entry that was not read goes first', () => {
        const cache = new SignalResultCache<Answer>(3);
        cache.set('a', G, answer(1));
        cache.set('b', G, answer(2));
        cache.set('c', G, answer(3));
        expect(cache.get('a', G), 'premise: a hit').toEqual(answer(1));

        cache.set('d', G, answer(4));

        expect(cache.get('b', G), 'b was the least recently used once a was read: the read did not count').toBeNull();
        expect(cache.get('a', G)).toEqual(answer(1));
        expect(cache.get('c', G)).toEqual(answer(3));
        expect(cache.get('d', G)).toEqual(answer(4));
    });

    it('makes a set of an existing key the most recently used', () => {
        const cache = new SignalResultCache<Answer>(2);
        cache.set('a', G, answer(1));
        cache.set('b', G, answer(2));

        cache.set('a', G, answer(3));
        cache.set('c', G, answer(4));

        expect(cache.size).toBe(2);
        expect(cache.get('b', G), 'b was the least recently used once a was set again: the replacement did not count').toBeNull();
        expect(cache.get('a', G)).toEqual(answer(3));
        expect(cache.get('c', G)).toEqual(answer(4));
    });

    it('holds 32 entries by default: the 33rd set drops the least recently used', () => {
        const cache = new SignalResultCache<Answer>();
        for (let index = 0; index < 32; index += 1) cache.set(`key-${index}`, G, answer(index));
        expect(cache.size, 'premise: 32 entries fit').toBe(32);
        expect(cache.get('key-0', G), 'premise: the first is still there before the 33rd').toEqual(answer(0));

        cache.set('key-32', G, answer(32));

        expect(cache.size).toBe(32);
        expect(cache.get('key-1', G), 'key-0 was read, key-1 is now the least recently used').toBeNull();
        expect(cache.get('key-0', G)).toEqual(answer(0));
        expect(cache.get('key-32', G)).toEqual(answer(32));
    });

    it('holds one entry when maxEntries is 1: each set replaces the one before', () => {
        const cache = new SignalResultCache<Answer>(1);
        cache.set('a', G, answer(1));

        cache.set('b', G, answer(2));

        expect(cache.size).toBe(1);
        expect(cache.get('a', G)).toBeNull();
        expect(cache.get('b', G)).toEqual(answer(2));
    });
});

describe('SignalResultCache: the caller’s values and the cache’s are apart, both ways', () => {
    it('is not changed by a mutation of what set was given, at any depth', () => {
        const cache = new SignalResultCache<Answer>();
        const given = answer(1);
        cache.set('k', G, given);

        given.items[0].points.push(99);
        given.items[0].id = 500;
        given.items.push({id: 2, points: []});

        expect(cache.get('k', G), 'the cache kept the caller’s object: the page drawing from its answer would rewrite the cached one').toEqual(answer(1));
    });

    it('is not changed by a mutation of what get returned, at any depth, and returns a copy every time', () => {
        const cache = new SignalResultCache<Answer>();
        cache.set('k', G, answer(1));

        const read = cache.get('k', G);
        expect(read, 'premise: a hit').not.toBeNull();
        read?.items[0].points.push(99);
        read?.items.push({id: 2, points: []});

        const again = cache.get('k', G);
        expect(again, 'what get returned was the cached object itself: a page that edits its answer would rewrite the cache').toEqual(answer(1));
        expect(again, 'two reads share one object').not.toBe(read);
    });

    it('accepts a frozen value, and what it returns can be changed', () => {
        const cache = new SignalResultCache<Answer>();
        const frozen = deepFreeze(answer(1));

        cache.set('k', G, frozen);
        const read = cache.get('k', G);

        expect(read).toEqual(answer(1));
        expect(() => read?.items[0].points.push(4), 'the copy is frozen as the original was: a page could not use it').not.toThrow();
    });
});

describe('SignalResultCache: clear', () => {
    it('empties the cache, size included, and it takes entries again', () => {
        const cache = new SignalResultCache<Answer>();
        cache.set('a', G, answer(1));
        cache.set('b', G, answer(2));

        cache.clear();

        expect(cache.size).toBe(0);
        expect(cache.get('a', G)).toBeNull();
        expect(cache.get('b', G)).toBeNull();

        cache.set('a', G, answer(3));
        expect(cache.get('a', G)).toEqual(answer(3));
        expect(cache.size).toBe(1);
    });
});

describe('the two singletons of the app', () => {
    const ASSET_ANSWER: AssetChartAnswer = {items: [{asset_id: 7, events: [], signals: [{instance_id: 'sma', signal_code: 'SMA', status: 'ok'}], errors: []}]};
    const FX_ANSWER = [{instance_id: 'sma', signal_code: 'SMA', status: 'ok'}] as unknown as BackendSignalResult[];
    let nextUser = 0;
    /** An account id no other case uses. */
    const freshUser = (): string => `n64-user-${++nextUser}`;

    function fill(): void {
        assetChartAnswers.set('asset-key', G, ASSET_ANSWER);
        fxSignalAnswers.set('fx-key', G, FX_ANSWER);
        expect(assetChartAnswers.size, 'premise: the asset answers hold an entry').toBe(1);
        expect(fxSignalAnswers.size, 'premise: the FX answers hold an entry').toBe(1);
    }

    it('are two caches, each of its own answers', () => {
        assetChartAnswers.set('shared-key', G, ASSET_ANSWER);

        expect(assetChartAnswers).toBeInstanceOf(SignalResultCache);
        expect(fxSignalAnswers).toBeInstanceOf(SignalResultCache);
        expect(fxSignalAnswers, 'one cache for both kinds of answer').not.toBe(assetChartAnswers);
        expect(fxSignalAnswers.get('shared-key', G), 'an FX read found an asset answer').toBeNull();
        expect(assetChartAnswers.get('shared-key', G)).toEqual(ASSET_ANSWER);
    });

    it('both empty when the signed-in account changes: an answer is the previous user’s data', () => {
        transitionClientSession(freshUser()); // an account is known now: the next one is a change, not a first identity
        fill();

        expect(transitionClientSession(freshUser()), 'premise: a real change of account').toBe(true);

        expect(assetChartAnswers.size, 'the next user could read the previous one’s asset answers').toBe(0);
        expect(fxSignalAnswers.size, 'the next user could read the previous one’s FX answers').toBe(0);
        expect(assetChartAnswers.get('asset-key', G)).toBeNull();
        expect(fxSignalAnswers.get('fx-key', G)).toBeNull();
    });

    it('both empty on sign-out as well', () => {
        transitionClientSession(freshUser());
        fill();

        expect(transitionClientSession(null), 'premise: signing out is a change of account').toBe(true);

        expect(assetChartAnswers.size).toBe(0);
        expect(fxSignalAnswers.size).toBe(0);
    });

    it('both stay on a call for the same account: nothing changed', () => {
        const user = freshUser();
        transitionClientSession(user);
        fill();

        expect(transitionClientSession(user), 'premise: the same account is no change').toBe(false);

        expect(assetChartAnswers.get('asset-key', G), 'a same-user call emptied the asset answers: every re-resolved session would ask them all again').toEqual(ASSET_ANSWER);
        expect(fxSignalAnswers.get('fx-key', G), 'a same-user call emptied the FX answers').toEqual(FX_ANSWER);
    });
});

describe('comparisonSeriesAnswers: the comparison peers’ series the asset and FX pages loaded (N64b)', () => {
    const SERIES: ComparisonAssetsLoadResult = {
        items: [{assetId: 7, runtimeParams: {_resolvedData: [{date: '2026-03-02', value: 10}], _conversionFailed: false}, events: [{date: '2026-03-02', type: 'DIVIDEND'}]}],
    };
    let nextUser = 0;
    const freshUser = (): string => `n64b-user-${++nextUser}`;

    it('is a cache of its own, apart from the asset and the FX answers', () => {
        comparisonSeriesAnswers.set('shared-key', G, SERIES);

        expect(comparisonSeriesAnswers).toBeInstanceOf(SignalResultCache);
        expect(comparisonSeriesAnswers).not.toBe(assetChartAnswers);
        expect(comparisonSeriesAnswers).not.toBe(fxSignalAnswers);
        expect(assetChartAnswers.get('shared-key', G)).toBeNull();
        expect(fxSignalAnswers.get('shared-key', G)).toBeNull();
        expect(comparisonSeriesAnswers.get('shared-key', G)).toEqual(SERIES);
    });

    it('keeps and gives back deep copies: no caller can change what another reads later', () => {
        const given = structuredClone(SERIES) as unknown as {items: {runtimeParams: {_resolvedData: {value: number}[]}}[]};
        comparisonSeriesAnswers.set('k', G, given as unknown as ComparisonAssetsLoadResult);
        given.items[0].runtimeParams._resolvedData[0].value = 999; // after the set: must not reach the cache

        const first = comparisonSeriesAnswers.get('k', G) as unknown as typeof given;
        expect(first.items[0].runtimeParams._resolvedData[0].value).toBe(10);
        expect(first).not.toBe(given);
        first.items[0].runtimeParams._resolvedData[0].value = 555; // after the get: must not reach the cache

        expect(comparisonSeriesAnswers.get('k', G)).toEqual(SERIES);
    });

    it('misses with other generations and drops the entry', () => {
        comparisonSeriesAnswers.set('k', G, SERIES);

        expect(comparisonSeriesAnswers.get('k', [4, 10]), 'a store moved on: the series was drawn over other data').toBeNull();
        expect(comparisonSeriesAnswers.size).toBe(0);
        expect(comparisonSeriesAnswers.get('k', G), 'the entry was dropped by the mismatch').toBeNull();
    });

    it('is emptied when the signed-in account changes, and by a sign-out', () => {
        transitionClientSession(freshUser());
        comparisonSeriesAnswers.set('k', G, SERIES);
        expect(transitionClientSession(freshUser()), 'premise: a real change of account').toBe(true);
        expect(comparisonSeriesAnswers.size, 'the next user could read the previous one’s series').toBe(0);

        comparisonSeriesAnswers.set('k', G, SERIES);
        expect(transitionClientSession(null), 'premise: signing out is a change of account').toBe(true);
        expect(comparisonSeriesAnswers.size).toBe(0);
    });

    it('stays on a call for the same account', () => {
        const user = freshUser();
        transitionClientSession(user);
        comparisonSeriesAnswers.set('k', G, SERIES);

        expect(transitionClientSession(user), 'premise: the same account is no change').toBe(false);

        expect(comparisonSeriesAnswers.get('k', G)).toEqual(SERIES);
    });
});

describe('clearAssetPageAnswers: what a sync or a refresh of the asset page empties (N64b)', () => {
    it('empties the asset answers and the comparison series, and leaves the FX answers alone', () => {
        assetChartAnswers.set('asset-key', G, {items: [{asset_id: 7}]});
        comparisonSeriesAnswers.set('comparison-key', G, {items: []});
        const fxAnswer = [{instance_id: 'sma', signal_code: 'SMA', status: 'ok'}] as unknown as BackendSignalResult[];
        fxSignalAnswers.set('fx-key', G, fxAnswer);
        expect(assetChartAnswers.size + comparisonSeriesAnswers.size, 'premise: both asset caches hold an entry').toBe(2);

        clearAssetPageAnswers();

        expect(assetChartAnswers.size).toBe(0);
        expect(comparisonSeriesAnswers.size).toBe(0);
        expect(assetChartAnswers.get('asset-key', G)).toBeNull();
        expect(comparisonSeriesAnswers.get('comparison-key', G)).toBeNull();
        expect(fxSignalAnswers.get('fx-key', G), 'the asset page’s clear reached the FX page’s answers').toEqual(fxAnswer);
    });

    it('takes empty caches without complaint, and the caches take entries again', () => {
        expect(() => clearAssetPageAnswers()).not.toThrow();

        comparisonSeriesAnswers.set('k', G, {items: []});
        expect(comparisonSeriesAnswers.get('k', G)).toEqual({items: []});
    });
});
