/**
 * @vitest-environment node
 *
 * assetSetSelection — pure unit tests (node env, no jsdom).
 *
 * This module is the answer to a single defect: Asset Global used to open on
 * `assets.filter(active).slice(0, 100)`, which drew a 100×100 matrix nobody
 * asked for and gave no way back. Every rule it now enforces is a decision
 * taken before a component renders — which assets are on the table, what the
 * filter row means when it is empty, what a mass action does to a selection the
 * filter is currently hiding — so all of it is asserted here rather than
 * through a page.
 *
 * Two deliberate choices in the fixtures:
 *
 *  - **Storage is always injected.** `readPersistedSelection` and
 *    `writePersistedSelection` take a storage object as their last parameter;
 *    the tests pass a `Map`-backed stand-in and never touch a global
 *    `localStorage`, so no case can leave state behind for the next one and the
 *    file is order-independent by construction.
 *  - **The storage key is learned, not retyped.** The module does not export
 *    it; the tests discover it by writing through the module's own writer, so a
 *    version bump of the key does not turn into a test that asserts a string
 *    the product no longer uses.
 */
import {describe, expect, it} from 'vitest';

import {EMPTY_FILTERS, FALLBACK_SELECTION_SIZE, MAX_SELECTED_ASSETS, applyBulkAction, applyFilters, ownedAssetIds, readPersistedSelection, resolveInitialSelection, writePersistedSelection, type BulkAction, type SelectableAsset} from './assetSetSelection';

/** An asset carrying only the fields this module reads. Not owned by default. */
function asset(id: number, overrides: Partial<SelectableAsset> = {}): SelectableAsset {
    return {id, active: true, asset_type: 'ETF', currency: 'EUR', tx_count_own: 0, ...overrides};
}

/** An asset the user has transacted on — what "mine" means on this page. */
function ownedAsset(id: number, overrides: Partial<SelectableAsset> = {}): SelectableAsset {
    return asset(id, {tx_count_own: 4, ...overrides});
}

/** A catalogue of `size` assets with ids 1..size. */
function catalogue(size: number, make: (id: number) => SelectableAsset = asset): SelectableAsset[] {
    return Array.from({length: size}, (_, index) => make(index + 1));
}

const ids = (assets: readonly SelectableAsset[]): number[] => assets.map((entry) => entry.id);
const ascending = (values: readonly number[]): number[] => [...values].sort((left, right) => left - right);

interface FakeStorage {
    getItem(key: string): string | null;
    setItem(key: string, value: string): void;
    /** What is currently held, for the assertions the module's API cannot express. */
    readonly entries: Map<string, string>;
    /** The key the module chose, learned from the module itself. */
    keyUsed(): string;
}

function fakeStorage(): FakeStorage {
    const entries = new Map<string, string>();
    return {
        entries,
        getItem: (key: string) => entries.get(key) ?? null,
        setItem: (key: string, value: string) => {
            entries.set(key, value);
        },
        keyUsed: () => {
            const keys = [...entries.keys()];
            if (keys.length !== 1) throw new Error(`expected exactly one stored key, found ${keys.length}`);
            return keys[0];
        },
    };
}

/** A storage already holding `raw` under whatever key the module writes to. */
function storageHolding(raw: string): FakeStorage {
    const storage = fakeStorage();
    writePersistedSelection([1], storage);
    storage.entries.set(storage.keyUsed(), raw);
    return storage;
}

/** The browser that says no: a locked-down profile, or a full quota. */
function refusingStorage(): Pick<Storage, 'getItem' | 'setItem'> {
    return {
        getItem: () => {
            throw new Error('storage access denied');
        },
        setItem: () => {
            throw new Error('quota exceeded');
        },
    };
}

describe('ownedAssetIds', () => {
    it('keeps the assets the user has actually transacted on', () => {
        const assets = [asset(1), ownedAsset(2), asset(3), ownedAsset(4)];
        expect(ownedAssetIds(assets)).toEqual([2, 4]);
    });

    it('treats an absent or zero counter as not owned', () => {
        const assets = [asset(1, {tx_count_own: 0}), {id: 2, currency: 'EUR'} as SelectableAsset, ownedAsset(3, {tx_count_own: 1})];
        expect(ownedAssetIds(assets)).toEqual([3]);
    });

    it('owns nothing in an empty catalogue', () => {
        expect(ownedAssetIds([])).toEqual([]);
    });
});

describe('readPersistedSelection', () => {
    it('reads back exactly what the writer stored', () => {
        const storage = fakeStorage();
        writePersistedSelection([7, 3, 5], storage);
        expect(readPersistedSelection(storage)).toEqual([7, 3, 5]);
    });

    it('has no memory when nothing was ever stored', () => {
        expect(readPersistedSelection(fakeStorage())).toBeNull();
        expect(readPersistedSelection(storageHolding(''))).toBeNull();
    });

    it('has no memory when storage itself is unavailable', () => {
        expect(readPersistedSelection(null)).toBeNull();
        expect(readPersistedSelection(undefined)).toBeNull();
    });

    it('has no memory when reading throws, instead of breaking the page', () => {
        expect(readPersistedSelection(refusingStorage())).toBeNull();
    });

    it('has no memory for malformed JSON', () => {
        expect(readPersistedSelection(storageHolding('{not json'))).toBeNull();
    });

    it('has no memory for a payload that is not an array', () => {
        expect(readPersistedSelection(storageHolding('{"ids":[1,2]}'))).toBeNull();
        expect(readPersistedSelection(storageHolding('"5"'))).toBeNull();
        expect(readPersistedSelection(storageHolding('5'))).toBeNull();
        expect(readPersistedSelection(storageHolding('null'))).toBeNull();
    });

    it('drops the entries that are not asset ids', () => {
        expect(readPersistedSelection(storageHolding('[1,"2",3.5,null,true,4]'))).toEqual([1, 4]);
    });

    it('has no memory when every entry was dropped', () => {
        expect(readPersistedSelection(storageHolding('["a","b"]'))).toBeNull();
    });

    it('has no memory for an empty array', () => {
        // "Nothing selected" is not a preference worth restoring.
        expect(readPersistedSelection(storageHolding('[]'))).toBeNull();
    });
});

describe('writePersistedSelection', () => {
    it('keeps one stable key, overwritten on each save', () => {
        const storage = fakeStorage();
        writePersistedSelection([1, 2], storage);
        writePersistedSelection([3], storage);
        expect(storage.entries.size).toBe(1);
        expect(readPersistedSelection(storage)).toEqual([3]);
    });

    it('never throws when storage refuses the write', () => {
        expect(() => writePersistedSelection([1, 2], refusingStorage())).not.toThrow();
    });

    it('does nothing, quietly, when storage is unavailable', () => {
        expect(() => writePersistedSelection([1, 2], null)).not.toThrow();
        expect(() => writePersistedSelection([1, 2], undefined)).not.toThrow();
    });

    it('stores an empty selection, which reads back as no memory', () => {
        const storage = fakeStorage();
        writePersistedSelection([1, 2], storage);
        writePersistedSelection([], storage);
        expect(readPersistedSelection(storage)).toBeNull();
    });
});

describe('resolveInitialSelection (D19)', () => {
    it('opens on the selection the user left behind', () => {
        const assets = [asset(1), asset(2), ownedAsset(3)];
        expect(resolveInitialSelection(assets, [1, 2])).toEqual([1, 2]);
    });

    it('keeps the persisted order rather than the catalogue order', () => {
        const assets = [asset(3), asset(5), asset(7)];
        expect(resolveInitialSelection(assets, [7, 3, 5])).toEqual([7, 3, 5]);
    });

    it('drops a persisted id whose asset no longer exists', () => {
        // An asset can be deleted or merged between two visits. Asking the API
        // for an id that no longer resolves turns a stale preference into an
        // error the user has no way to explain.
        const assets = [asset(1), asset(3)];
        expect(resolveInitialSelection(assets, [1, 2, 3, 99])).toEqual([1, 3]);
    });

    it('falls through to the owned assets when no persisted id survives', () => {
        const assets = [asset(1), ownedAsset(2), ownedAsset(3)];
        expect(resolveInitialSelection(assets, [404, 405])).toEqual([2, 3]);
    });

    it('falls through to the owned assets when there is no memory at all', () => {
        const assets = [asset(1), ownedAsset(2)];
        expect(resolveInitialSelection(assets, null)).toEqual([2]);
    });

    it('treats an empty persisted list as no memory', () => {
        const assets = [asset(1), ownedAsset(2)];
        expect(resolveInitialSelection(assets, [])).toEqual([2]);
    });

    it('falls back to a small readable handful when the user owns nothing', () => {
        const assets = catalogue(30);
        expect(resolveInitialSelection(assets, null)).toHaveLength(FALLBACK_SELECTION_SIZE);
    });

    it('ranks the fallback by how much the instrument has been transacted', () => {
        // Not by where the asset sits in the API's array: choosing by position
        // is still choosing, it just hides the arbitrariness behind an index.
        const assets = [asset(1, {tx_count: 2}), asset(2, {tx_count: 90}), asset(3, {tx_count: 40}), asset(4, {tx_count: 7})];
        expect(resolveInitialSelection(assets, null)).toEqual([2, 3, 4, 1]);
    });

    it('breaks a fallback tie on id, so the handful is stable across reloads', () => {
        const assets = [asset(30, {tx_count: 5}), asset(10, {tx_count: 5}), asset(20, {tx_count: 5})];
        expect(resolveInitialSelection(assets, null)).toEqual([10, 20, 30]);
    });

    it('ranks an asset with no transaction count as one with none', () => {
        const assets = [asset(1), asset(2, {tx_count: 3}), asset(3, {tx_count: 0})];
        expect(resolveInitialSelection(assets, null)).toEqual([2, 1, 3]);
    });

    it('takes the most transacted out of a large catalogue, not the first six', () => {
        // Ids ascend while transaction counts ascend with them, so relevance
        // and position point in opposite directions: a positional pick would
        // return 1..6 and fail here.
        const assets = catalogue(500, (id) => asset(id, {tx_count: id}));
        const result = resolveInitialSelection(assets, null);
        expect(result).toHaveLength(FALLBACK_SELECTION_SIZE);
        expect(result).toEqual([500, 499, 498, 497, 496, 495]);
    });

    it('ranks without reordering the catalogue it was given', () => {
        // The ranking sorts, and a sort in place would silently reorder the
        // caller's list — the same array the filter row and the table read.
        const assets = [asset(1, {tx_count: 1}), asset(2, {tx_count: 99}), asset(3, {tx_count: 50})];
        const original = ids(assets);
        resolveInitialSelection(assets, null);
        expect(ids(assets)).toEqual(original);
    });

    it('excludes inactive assets from that fallback, however transacted they are', () => {
        const assets = [asset(1, {active: false, tx_count: 9999}), asset(2, {tx_count: 3}), asset(3, {active: false}), asset(4, {tx_count: 1})];
        expect(resolveInitialSelection(assets, null)).toEqual([2, 4]);
    });

    it('treats an asset with no active flag as active', () => {
        const assets = [{id: 1, currency: 'EUR'} as SelectableAsset, asset(2)];
        expect(resolveInitialSelection(assets, null)).toEqual([1, 2]);
    });

    it('still selects an owned asset that has been deactivated', () => {
        // The activity filter belongs to the fallback only: an asset the user
        // holds is on the table whether or not it still trades.
        const assets = [asset(1), ownedAsset(2, {active: false})];
        expect(resolveInitialSelection(assets, null)).toEqual([2]);
    });

    it('still selects a persisted asset that has been deactivated', () => {
        const assets = [asset(1, {active: false}), asset(2)];
        expect(resolveInitialSelection(assets, [1])).toEqual([1]);
    });

    it('never opens on a hundred assets: five hundred in the catalogue, a handful on screen', () => {
        // The defect this module exists to prevent, asserted directly.
        const result = resolveInitialSelection(catalogue(500), null);
        expect(result).toHaveLength(FALLBACK_SELECTION_SIZE);
        expect(result.length).toBeLessThan(MAX_SELECTED_ASSETS);
    });

    it('caps a large owned set at the API limit', () => {
        const allOwned = catalogue(500, (id) => ownedAsset(id));
        expect(resolveInitialSelection(allOwned, null)).toHaveLength(MAX_SELECTED_ASSETS);
    });

    it('caps a large persisted selection at the API limit', () => {
        const assets = catalogue(500);
        expect(resolveInitialSelection(assets, ids(assets))).toHaveLength(MAX_SELECTED_ASSETS);
    });

    it('selects nothing from an empty catalogue', () => {
        expect(resolveInitialSelection([], [1, 2])).toEqual([]);
        expect(resolveInitialSelection([], null)).toEqual([]);
    });

    it('never returns an id that is not in the catalogue, even when it reads storage itself', () => {
        // Called without the second argument, the module reaches for its own
        // storage seam. Whatever that seam finds — a real memory, nothing, or a
        // refusal — the result stays inside what exists and inside the cap.
        const assets = [asset(11), ownedAsset(12), asset(13)];
        const available = new Set(ids(assets));
        const result = resolveInitialSelection(assets);
        expect(result.every((id) => available.has(id))).toBe(true);
        expect(result.length).toBeLessThanOrEqual(MAX_SELECTED_ASSETS);
        expect(result.length).toBeGreaterThan(0);
    });
});

describe('applyFilters', () => {
    const assets = [asset(1, {asset_type: 'ETF', currency: 'EUR'}), asset(2, {asset_type: 'STOCK', currency: 'USD'}), asset(3, {asset_type: 'ETF', currency: 'USD'}), asset(4, {asset_type: null, currency: 'EUR'})];

    it('shows everything when no criterion is set', () => {
        // An empty filter row is unconstrained, not empty. A page that opens
        // blank makes the user guess what they did wrong.
        expect(ids(applyFilters(assets, EMPTY_FILTERS))).toEqual(ids(assets));
    });

    it('narrows by type', () => {
        expect(ids(applyFilters(assets, {types: ['ETF'], currencies: []}))).toEqual([1, 3]);
    });

    it('narrows by currency', () => {
        expect(ids(applyFilters(assets, {types: [], currencies: ['USD']}))).toEqual([2, 3]);
    });

    it('accepts several values for one criterion', () => {
        expect(ids(applyFilters(assets, {types: ['ETF', 'STOCK'], currencies: []}))).toEqual([1, 2, 3]);
    });

    it('composes type and currency with AND', () => {
        expect(ids(applyFilters(assets, {types: ['ETF'], currencies: ['USD']}))).toEqual([3]);
    });

    it('matches an asset with no type under OTHER', () => {
        expect(ids(applyFilters(assets, {types: ['OTHER'], currencies: []}))).toEqual([4]);
        const untyped = [{id: 9, currency: 'EUR'} as SelectableAsset];
        expect(ids(applyFilters(untyped, {types: ['OTHER'], currencies: []}))).toEqual([9]);
    });

    it('matches an asset whose type is an empty string under OTHER', () => {
        // `||`, not `??`: an empty string is as unclassified as a null one, and
        // under `??` the asset would match no criterion at all — it would
        // vanish the moment any type filter was switched on, unreachable.
        const blank = [asset(9, {asset_type: ''})];
        expect(ids(applyFilters(blank, {types: ['OTHER'], currencies: []}))).toEqual([9]);
        expect(ids(applyFilters(blank, EMPTY_FILTERS))).toEqual([9]);
    });

    it('returns nothing when a criterion that was really set matches nothing', () => {
        expect(applyFilters(assets, {types: ['CRYPTO'], currencies: []})).toEqual([]);
    });

    it('leaves the catalogue it was given untouched', () => {
        const original = [...assets];
        const filtered = applyFilters(assets, {types: ['ETF'], currencies: []});
        expect(assets).toEqual(original);
        expect(filtered).not.toBe(assets);
    });
});

describe('applyBulkAction', () => {
    const assets = catalogue(9);
    const visible = (...wanted: number[]): SelectableAsset[] => assets.filter((entry) => wanted.includes(entry.id));

    it('"all" adds every visible candidate to what was already selected', () => {
        expect(applyBulkAction('all', [1], visible(2, 3), assets)).toEqual([1, 2, 3]);
    });

    it('"all" keeps a selection made outside the current filter', () => {
        expect(applyBulkAction('all', [9], visible(1, 2), assets)).toContain(9);
    });

    it('"all" never selects the same asset twice', () => {
        const result = applyBulkAction('all', [1, 2], visible(1, 2, 3), assets);
        expect(result).toEqual([1, 2, 3]);
        expect(new Set(result).size).toBe(result.length);
    });

    it('"all" with nothing visible leaves the selection as it was', () => {
        expect(applyBulkAction('all', [4, 5], [], assets)).toEqual([4, 5]);
    });

    it('"all" truncates at the API limit rather than failing', () => {
        // The one place the hundred is legitimate: the user asked for it.
        const huge = catalogue(150);
        const result = applyBulkAction('all', [], huge, huge);
        expect(result).toHaveLength(MAX_SELECTED_ASSETS);
        expect(result).toEqual(ids(huge).slice(0, MAX_SELECTED_ASSETS));
    });

    it('"none" clears only what the filter is showing', () => {
        // The mirror of "all": a button that reached past the active filter
        // would undo the filter without saying so.
        expect(applyBulkAction('none', [1, 2, 5], visible(1, 2), assets)).toEqual([5]);
    });

    it('"none" with nothing visible leaves the selection untouched', () => {
        expect(applyBulkAction('none', [1, 2], [], assets)).toEqual([1, 2]);
    });

    it('"none" on an unfiltered catalogue clears everything', () => {
        expect(applyBulkAction('none', [1, 2, 5], assets, assets)).toEqual([]);
    });

    it('"invert" keeps the off-filter selection, drops the visible selected and adds the visible unselected', () => {
        const result = applyBulkAction('invert', [1, 9], visible(1, 2, 3), assets);
        expect(result).toContain(9);
        expect(result).not.toContain(1);
        expect(ascending(result)).toEqual([2, 3, 9]);
    });

    it('"invert" never selects the same asset twice', () => {
        const duplicated = [...visible(2), ...visible(2)];
        expect(applyBulkAction('invert', [], duplicated, assets)).toEqual([2]);
    });

    it('"invert" truncates at the API limit', () => {
        const huge = catalogue(250);
        const selected = ids(huge).slice(0, MAX_SELECTED_ASSETS);
        const result = applyBulkAction('invert', selected, huge.slice(MAX_SELECTED_ASSETS), huge);
        expect(result).toHaveLength(MAX_SELECTED_ASSETS);
    });

    it('"mine" ignores the filter and returns the owned set', () => {
        const mixed = [asset(1), ownedAsset(2), asset(3), ownedAsset(4)];
        expect(applyBulkAction('mine', [], [mixed[0]], mixed)).toEqual([2, 4]);
    });

    it('"mine" is a reset: it discards a selection outside the user holdings', () => {
        const mixed = [asset(1), ownedAsset(2)];
        expect(applyBulkAction('mine', [1, 7], mixed, mixed)).toEqual([2]);
    });

    it('"mine" truncates at the API limit', () => {
        const huge = catalogue(500, (id) => ownedAsset(id));
        expect(applyBulkAction('mine', [], [], huge)).toHaveLength(MAX_SELECTED_ASSETS);
    });

    it('no action can hand back more than the API limit', () => {
        const huge = catalogue(300, (id) => ownedAsset(id));
        const selected = ids(huge).slice(0, MAX_SELECTED_ASSETS);
        const actions: BulkAction[] = ['all', 'none', 'invert', 'mine'];
        for (const action of actions) {
            expect(applyBulkAction(action, selected, huge, huge).length).toBeLessThanOrEqual(MAX_SELECTED_ASSETS);
        }
    });

    it('hands back a new array rather than the selection it was given', () => {
        const selected = [1, 2];
        const actions: BulkAction[] = ['all', 'none', 'invert', 'mine'];
        for (const action of actions) {
            expect(applyBulkAction(action, selected, visible(2, 3), assets)).not.toBe(selected);
        }
        expect(selected).toEqual([1, 2]);
    });
});
