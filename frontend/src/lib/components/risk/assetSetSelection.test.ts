/**
 * @vitest-environment node
 *
 * assetSetSelection — pure unit tests (node env, no jsdom).
 *
 * This module is the answer to a single defect: Asset Global used to open on
 * `assets.filter(active).slice(0, 100)`, which drew a 100×100 matrix nobody
 * asked for and gave no way back. Every rule it now enforces is a decision
 * taken before a component renders — which assets are on the table, what a
 * mass action does to the ruled-out assets parked in the selection, which
 * benchmark the comparison levels measure against and when L3° waits for its
 * verdict — so all of it is asserted here rather than through a page. The "+"
 * picker's own rules (the filter row, its rows, its "select visible" switch)
 * moved with the picker to `ui/select/assetPicker.ts`, and their tests to
 * `ui/select/AssetPickerPanel.test.ts`.
 *
 * Two deliberate choices in the fixtures:
 *
 *  - **Storage and user are injected, except where the defaults are the
 *    subject.** `readPersistedSelection` and `writePersistedSelection` take a
 *    storage object and then a user id, both defaulting to the live page (its
 *    `localStorage`, its session). Everywhere else the tests pass a `Map`-backed
 *    stand-in and an explicit id, so no case can leave state behind for the next
 *    one. The two describes about the defaults set them up and undo them after
 *    every case: one logs a user in; the other also puts a stand-in in the
 *    page's place with `vi.stubGlobal`. A case that merely *relies* on the
 *    default storage tests whichever Node runs it — Node 26's own `localStorage`
 *    answers `undefined` without `--localstorage-file` — and "no storage" then
 *    passes for "no memory".
 *    Forgetting the user is the omission that hides: with no
 *    identity the module keeps no memory — it returns before reading or writing
 *    a selection — so such a case stays green without exercising what its name
 *    claims. Three once did.
 *  - **The storage key is learned, not retyped.** The module does not export
 *    it, and it now depends on the user; the tests discover each user's key by
 *    writing through the module's own writer (`keyUsed()`), so a version bump
 *    of the key does not turn into a test that asserts a string the product no
 *    longer uses. The one key typed out is the legacy one, on purpose: it is a
 *    shipped historical fact the tests must name, not a current choice.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

import {getClientSessionUserId, transitionClientSession} from '$lib/stores/app/clientSession';
import type {RiskBenchmarkState} from '$lib/stores/risk/riskBenchmarkStore.svelte';
import {FALLBACK_SELECTION_SIZE, MAX_SELECTED_ASSETS, applyBulkAction, labBenchmarkId, labL3Waits, readPersistedSelection, resolveInitialSelectionWithSource, writePersistedSelection, type BulkAction, type SelectableAsset, type SelectionSource} from './assetSetSelection';

/** An asset carrying only the fields this module reads. */
function asset(id: number, overrides: Partial<SelectableAsset> = {}): SelectableAsset {
    return {id, active: true, asset_type: 'ETF', currency: 'EUR', ...overrides};
}

/**
 * An asset as the page still receives it: `assetStore` copies the F15
 * `tx_count_own` onto every asset, a field this module stopped reading on 24/09
 * and no longer declares.
 */
function withOwnCount(entry: SelectableAsset, txCountOwn: number): SelectableAsset {
    return Object.assign({}, entry, {tx_count_own: txCountOwn});
}

/** A catalogue of `size` assets with ids 1..size. */
function catalogue(size: number, make: (id: number) => SelectableAsset = asset): SelectableAsset[] {
    return Array.from({length: size}, (_, index) => make(index + 1));
}

const ids = (assets: readonly SelectableAsset[]): number[] => assets.map((entry) => entry.id);
const ascending = (values: readonly number[]): number[] => [...values].sort((left, right) => left - right);

/** Two accounts whose ids share no digit, so a key that carries one cannot carry the other by accident. */
const USER_A = '7';
const USER_B = '8';

/** Retyped on purpose, unlike every other key here: the pre-scoping key is a shipped historical fact the tests must name. */
const LEGACY_STORAGE_KEY = 'assetGlobal.riskSelection.v1';

interface FakeStorage {
    getItem(key: string): string | null;
    setItem(key: string, value: string): void;
    /** Present only on request — see `fakeStorage`. */
    removeItem?(key: string): void;
    /** What is currently held, for the assertions the module's API cannot express. */
    readonly entries: Map<string, string>;
    /** The key the module chose, learned from the module itself. */
    keyUsed(): string;
}

/**
 * A `Map`-backed stand-in for `localStorage`.
 *
 * `removeItem` is opt-in because the module declares it optional: leaving it
 * out by default means every case that does not ask for it also proves that a
 * minimal stand-in still reads and writes.
 */
function fakeStorage({removable = false}: {removable?: boolean} = {}): FakeStorage {
    const entries = new Map<string, string>();
    const storage: FakeStorage = {
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
    if (removable) {
        storage.removeItem = (key: string) => {
            entries.delete(key);
        };
    }
    return storage;
}

/** A storage already holding `raw` under whatever key the module writes to for `user`. */
function storageHolding(raw: string, user: string): FakeStorage {
    const storage = fakeStorage();
    writePersistedSelection([1], storage, user);
    storage.entries.set(storage.keyUsed(), raw);
    return storage;
}

interface RefusingStorage extends Pick<Storage, 'getItem' | 'setItem'> {
    /** How many times each call was attempted. */
    readonly asked: {getItem: number; setItem: number};
}

/**
 * The browser that says no: a locked-down profile, or a full quota.
 *
 * It counts what it is asked, because a refusal the module never reached is
 * not one it survived: without an identity the module returns before it reads
 * or writes a selection, and both refusal cases once stayed green for that
 * reason alone.
 */
function refusingStorage(): RefusingStorage {
    const asked = {getItem: 0, setItem: 0};
    return {
        asked,
        getItem: () => {
            asked.getItem += 1;
            throw new Error('storage access denied');
        },
        setItem: () => {
            asked.setItem += 1;
            throw new Error('quota exceeded');
        },
    };
}

describe('readPersistedSelection', () => {
    it('reads back exactly what the writer stored', () => {
        const storage = fakeStorage();
        writePersistedSelection([7, 3, 5], storage, USER_A);
        expect(readPersistedSelection(storage, USER_A)).toEqual([7, 3, 5]);
    });

    it('has no memory when nothing was ever stored', () => {
        expect(readPersistedSelection(fakeStorage(), USER_A)).toBeNull();
        expect(readPersistedSelection(storageHolding('', USER_A), USER_A)).toBeNull();
    });

    it('has no memory when storage itself is unavailable', () => {
        // Not `undefined`: that would ask for the page's own storage — see the describe on the defaults.
        expect(readPersistedSelection(null, USER_A)).toBeNull();
    });

    it('has no memory when reading throws, instead of breaking the page', () => {
        const storage = refusingStorage();
        expect(readPersistedSelection(storage, USER_A)).toBeNull();
        // Refused, not bypassed: the read really reached the call that throws.
        expect(storage.asked.getItem).toBeGreaterThan(0);
    });

    it('has no memory for malformed JSON', () => {
        expect(readPersistedSelection(storageHolding('{not json', USER_A), USER_A)).toBeNull();
    });

    it('has no memory for a payload that is not an array', () => {
        expect(readPersistedSelection(storageHolding('{"ids":[1,2]}', USER_A), USER_A)).toBeNull();
        expect(readPersistedSelection(storageHolding('"5"', USER_A), USER_A)).toBeNull();
        expect(readPersistedSelection(storageHolding('5', USER_A), USER_A)).toBeNull();
        expect(readPersistedSelection(storageHolding('null', USER_A), USER_A)).toBeNull();
    });

    it('drops the entries that are not asset ids', () => {
        expect(readPersistedSelection(storageHolding('[1,"2",3.5,null,true,4]', USER_A), USER_A)).toEqual([1, 4]);
    });

    it('has no memory when every entry was dropped', () => {
        expect(readPersistedSelection(storageHolding('["a","b"]', USER_A), USER_A)).toBeNull();
    });

    it('has no memory for an empty array', () => {
        // "Nothing selected" is not a preference worth restoring.
        expect(readPersistedSelection(storageHolding('[]', USER_A), USER_A)).toBeNull();
    });
});

describe('writePersistedSelection', () => {
    it('keeps one stable key, overwritten on each save', () => {
        const storage = fakeStorage();
        writePersistedSelection([1, 2], storage, USER_A);
        writePersistedSelection([3], storage, USER_A);
        expect(storage.entries.size).toBe(1);
        expect(readPersistedSelection(storage, USER_A)).toEqual([3]);
    });

    it('never throws when storage refuses the write', () => {
        const storage = refusingStorage();
        expect(() => writePersistedSelection([1, 2], storage, USER_A)).not.toThrow();
        // Refused, not bypassed: the write really reached the call that throws.
        expect(storage.asked.setItem).toBeGreaterThan(0);
    });

    it('does nothing, quietly, when storage is unavailable', () => {
        expect(() => writePersistedSelection([1, 2], null, USER_A)).not.toThrow();
    });

    it('stores an empty selection, which reads back as no memory', () => {
        const storage = fakeStorage();
        writePersistedSelection([1, 2], storage, USER_A);
        // Control: the earlier selection is really there, so the null below is the
        // empty one replacing it — not a write that never happened.
        expect(readPersistedSelection(storage, USER_A)).toEqual([1, 2]);
        writePersistedSelection([], storage, USER_A);
        expect(JSON.parse(storage.entries.get(storage.keyUsed()) ?? 'null')).toEqual([]);
        expect(readPersistedSelection(storage, USER_A)).toBeNull();
    });
});

describe('per-user memory (TL-A)', () => {
    /**
     * Every way of having no identity. `undefined` is not one a caller can
     * inject: a default parameter replaces it with the session's user, so it
     * means "nobody" only while this process has no session — which each case
     * checks rather than assumes.
     */
    const NOBODY = [null, undefined, ''] as const;

    it('gives each user a key of their own, and neither is the legacy key', () => {
        const storageA = fakeStorage();
        const storageB = fakeStorage();
        writePersistedSelection([1], storageA, USER_A);
        writePersistedSelection([1], storageB, USER_B);
        const keyA = storageA.keyUsed();
        const keyB = storageB.keyUsed();

        expect(keyA).not.toBe(keyB);
        // Each key names its own user and not the other one, so `toContain` is
        // about the account rather than a digit that happens to sit in the base.
        expect(keyA).toContain(USER_A);
        expect(keyA).not.toContain(USER_B);
        expect(keyB).toContain(USER_B);
        expect(keyB).not.toContain(USER_A);
        expect([keyA, keyB]).not.toContain(LEGACY_STORAGE_KEY);
    });

    it("never hands one user's selection to another", () => {
        const storage = fakeStorage();
        writePersistedSelection([1, 2], storage, USER_A);
        // Control: the memory exists, for the user who made it.
        expect(readPersistedSelection(storage, USER_A)).toEqual([1, 2]);
        expect(readPersistedSelection(storage, USER_B)).toBeNull();
    });

    it("opens a second user on what they hold, not on the first user's selection", () => {
        const storage = fakeStorage();
        writePersistedSelection([1, 2], storage, USER_A);
        const assets = [asset(1), asset(2), asset(3)];
        const held = [3];
        // Control: in its owner's hands that selection survives the intersection
        // and wins the ladder over the same holdings — so it would win for B as
        // well, were B handed it.
        expect(resolveInitialSelectionWithSource(assets, readPersistedSelection(storage, USER_A), held)).toEqual({ids: [1, 2], source: 'persisted'});
        expect(resolveInitialSelectionWithSource(assets, readPersistedSelection(storage, USER_B), held)).toEqual({ids: [3], source: 'mine'});
    });

    it('never adopts the legacy key, whoever reads', () => {
        const shipped = JSON.stringify([1, 2, 3]);
        for (const user of [USER_A, USER_B]) {
            // Control: the payload is a valid selection — under the user's own key it reads back.
            expect(readPersistedSelection(storageHolding(shipped, user), user)).toEqual([1, 2, 3]);

            // A stand-in that cannot remove, on purpose. The module drops the legacy
            // key before it reads, so with `removeItem` available this null would be
            // owed to the cleanup alone — and would hold even for a key shared by
            // every user. Here the legacy value is still there after the read, so the
            // null can only mean it was never read.
            const storage = fakeStorage();
            storage.entries.set(LEGACY_STORAGE_KEY, shipped);
            expect(readPersistedSelection(storage, user)).toBeNull();
            expect(storage.entries.get(LEGACY_STORAGE_KEY)).toBe(shipped);
        }
    });

    it('removes the legacy key on the way, and nothing else', () => {
        const storage = fakeStorage({removable: true});
        writePersistedSelection([4, 5], storage, USER_A);
        storage.entries.set(LEGACY_STORAGE_KEY, JSON.stringify([1, 2, 3]));

        // The read that does the cleanup still finds the user's own selection: the
        // cleanup took the legacy key, and only that one.
        expect(readPersistedSelection(storage, USER_A)).toEqual([4, 5]);
        expect(storage.entries.has(LEGACY_STORAGE_KEY)).toBe(false);
    });

    it('keeps no memory without an identity, even when another user has one', () => {
        const storage = storageHolding(JSON.stringify([1, 2]), USER_A);
        // Control: there is a memory to leak, and its owner reads it.
        expect(readPersistedSelection(storage, USER_A)).toEqual([1, 2]);

        expect(getClientSessionUserId(), 'an explicit undefined defers to the session, which must have no user here').toBeNull();
        for (const nobody of NOBODY) {
            expect(readPersistedSelection(storage, nobody)).toBeNull();
        }
    });

    it('writes nothing without an identity', () => {
        const storage = storageHolding(JSON.stringify([1, 2]), USER_A);
        const before = new Map(storage.entries);

        expect(getClientSessionUserId(), 'an explicit undefined defers to the session, which must have no user here').toBeNull();
        for (const nobody of NOBODY) {
            writePersistedSelection([9], storage, nobody);
        }
        expect(storage.entries).toEqual(before);

        // Control: the same write, with an identity, does land.
        writePersistedSelection([9], storage, USER_B);
        expect(storage.entries).not.toEqual(before);
    });
});

describe('the session default', () => {
    // The session is a module singleton: a user left logged in here would be
    // inherited by every later case — and would turn TL-A4's "no session in this
    // process" guard red for a reason that has nothing to do with the module.
    afterEach(() => {
        transitionClientSession(null);
    });

    it('reads and writes as the session user when the caller names none', () => {
        // Production call sites pass no user at all, so this default is the path
        // the page actually takes; every other persistence case here injects one.
        const storage = fakeStorage();
        transitionClientSession(USER_A);
        writePersistedSelection([4, 2], storage);
        // Landed under the session user's own key…
        expect(readPersistedSelection(storage, USER_A)).toEqual([4, 2]);
        // …and read back through the same default.
        expect(readPersistedSelection(storage)).toEqual([4, 2]);
        // An explicit `undefined` is the same omission, not an identity of its own.
        expect(readPersistedSelection(storage, undefined)).toEqual([4, 2]);

        // It follows the session, not the first user it happened to see.
        transitionClientSession(USER_B);
        expect(readPersistedSelection(storage)).toBeNull();
        writePersistedSelection([9], storage);
        expect(readPersistedSelection(storage, USER_B)).toEqual([9]);
        expect(readPersistedSelection(storage, USER_A)).toEqual([4, 2]);
    });
});

describe("the page's localStorage, as the default storage", () => {
    // What the production call sites use: no storage and no user passed. Node 26
    // has a `localStorage` of its own — a getter answering `undefined` without
    // `--localstorage-file` — so the page's storage is put in place in every case
    // here, never inherited. Both defaults are undone after every case.
    beforeEach(() => {
        transitionClientSession(USER_A);
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        transitionClientSession(null);
    });

    it('writes to and reads from the page storage when the caller passes none', () => {
        const page = fakeStorage();
        vi.stubGlobal('localStorage', page);
        writePersistedSelection([5, 3]);
        // It really landed there, under the session user's own key…
        expect(page.keyUsed()).toContain(USER_A);
        expect(readPersistedSelection(page, USER_A)).toEqual([5, 3]);
        // …and it reads back through the same default. An explicit `undefined` is the same omission.
        expect(readPersistedSelection()).toEqual([5, 3]);
        expect(readPersistedSelection(undefined, USER_A)).toEqual([5, 3]);
    });

    it('opens on the remembered selection when the ladder reads the storage itself', () => {
        // Called without a memory, the ladder reads the page storage. The id that no
        // longer resolves is dropped there too, and the stored order is kept.
        const page = fakeStorage();
        vi.stubGlobal('localStorage', page);
        writePersistedSelection([13, 404, 11], page, USER_A);
        const assets = [asset(11), asset(12), asset(13)];
        expect(resolveInitialSelectionWithSource(assets)).toEqual({ids: [13, 11], source: 'persisted'});
    });

    it('has no memory, and never throws, when the page has no storage', () => {
        vi.stubGlobal('localStorage', undefined);
        expect(readPersistedSelection()).toBeNull();
        expect(() => writePersistedSelection([1, 2])).not.toThrow();
        expect(resolveInitialSelectionWithSource([asset(1), asset(2)])).toEqual({ids: [1, 2], source: 'fallback'});

        // Control: the same calls, once the page has a storage, do remember.
        vi.stubGlobal('localStorage', fakeStorage());
        writePersistedSelection([1, 2]);
        expect(readPersistedSelection()).toEqual([1, 2]);
    });

    it('has no memory, and never throws, when merely touching the page storage throws', () => {
        // A browser that blocks storage — cookies off, a sandboxed frame — throws on
        // the access itself, before any method is called. `stubGlobal` goes first
        // only to record the original, so `unstubAllGlobals` restores it.
        let touched = 0;
        vi.stubGlobal('localStorage', undefined);
        Object.defineProperty(globalThis, 'localStorage', {
            configurable: true,
            get() {
                touched += 1;
                throw new DOMException('The operation is insecure.', 'SecurityError');
            },
        });
        expect(readPersistedSelection()).toBeNull();
        const afterRead = touched;
        expect(() => writePersistedSelection([1, 2])).not.toThrow();
        // Refused, not bypassed: each call really reached for the page storage.
        expect(afterRead).toBeGreaterThan(0);
        expect(touched).toBeGreaterThan(afterRead);
    });
});

describe('resolveInitialSelectionWithSource (D19)', () => {
    it('opens on the selection the user left behind', () => {
        const assets = [asset(1), asset(2), asset(3)];
        expect(resolveInitialSelectionWithSource(assets, [1, 2])).toEqual({ids: [1, 2], source: 'persisted'});
    });

    it('keeps the persisted order rather than the catalogue order', () => {
        const assets = [asset(3), asset(5), asset(7)];
        expect(resolveInitialSelectionWithSource(assets, [7, 3, 5]).ids).toEqual([7, 3, 5]);
    });

    it('drops a persisted id whose asset no longer exists', () => {
        // An asset can be deleted or merged between two visits. Asking the API
        // for an id that no longer resolves turns a stale preference into an
        // error the user has no way to explain.
        const assets = [asset(1), asset(3)];
        expect(resolveInitialSelectionWithSource(assets, [1, 2, 3, 99]).ids).toEqual([1, 3]);
    });

    it('opens on a remembered asset once, where it was first remembered', () => {
        // A duplicate that reached storage would reach the analysis twice — a scope
        // the backend refuses ("asset_ids must be unique") — and be written back on
        // every visit. The held rung has always deduplicated; this one now does too.
        expect(resolveInitialSelectionWithSource([asset(1), asset(2)], [2, 2, 1])).toEqual({ids: [2, 1], source: 'persisted'});
        // Before the cap, not after: stored twice each, 150 assets still fill the hundred.
        const assets = catalogue(150);
        const twice = ids(assets).flatMap((id) => [id, id]);
        expect(resolveInitialSelectionWithSource(assets, twice).ids).toEqual(ids(assets).slice(0, MAX_SELECTED_ASSETS));
    });

    it('prefers the remembered selection to what is held', () => {
        expect(resolveInitialSelectionWithSource(catalogue(4), [1], [2, 3])).toEqual({ids: [1], source: 'persisted'});
    });

    it('falls through to what is held when no persisted id survives', () => {
        expect(resolveInitialSelectionWithSource(catalogue(3), [404, 405], [2, 3])).toEqual({ids: [2, 3], source: 'mine'});
    });

    it('falls through to what is held when there is no memory at all', () => {
        expect(resolveInitialSelectionWithSource(catalogue(2), null, [2])).toEqual({ids: [2], source: 'mine'});
    });

    it('treats an empty persisted list as no memory', () => {
        expect(resolveInitialSelectionWithSource(catalogue(2), [], [2])).toEqual({ids: [2], source: 'mine'});
    });

    it('drops a held id that is not on the page, and falls back when none is', () => {
        // A holding outside the page's list would reach the analysis with no chip
        // to remove it by. Nothing held on the page is nothing held.
        expect(resolveInitialSelectionWithSource(catalogue(3), null, [404, 2, 405, 3])).toEqual({ids: [2, 3], source: 'mine'});
        expect(resolveInitialSelectionWithSource(catalogue(3), null, [404, 405])).toEqual({ids: [1, 2, 3], source: 'fallback'});
    });

    it('selects an asset held twice once, where it was first held', () => {
        // An asset held in two brokers can come back twice. The held order is kept, not the catalogue's.
        expect(resolveInitialSelectionWithSource(catalogue(3), null, [3, 1, 3, 2, 1])).toEqual({ids: [3, 1, 2], source: 'mine'});
    });

    it('spends the hundred on assets, not on entries, when every asset is held twice', () => {
        // Capping before deduplicating would stop at fifty.
        const assets = catalogue(150);
        const twice = ids(assets).flatMap((id) => [id, id]);
        expect(resolveInitialSelectionWithSource(assets, null, twice).ids).toEqual(ids(assets).slice(0, MAX_SELECTED_ASSETS));
    });

    it('falls back when nothing is held, whether the list is empty or not passed at all', () => {
        const assets = [asset(1, {tx_count: 2}), asset(2, {tx_count: 9})];
        expect(resolveInitialSelectionWithSource(assets, null, [])).toEqual({ids: [2, 1], source: 'fallback'});
        expect(resolveInitialSelectionWithSource(assets, null)).toEqual({ids: [2, 1], source: 'fallback'});
    });

    it('reads nothing into tx_count_own: an asset once traded is not an asset held', () => {
        // The old rung 2 opened on every `tx_count_own > 0`, positions sold years
        // ago included — [1, 3] here. Only `held` counts now, and the fallback ranks
        // by `tx_count` alone: by `tx_count_own` it would read [1, 3, 2].
        const assets = [withOwnCount(asset(1, {tx_count: 1}), 99), withOwnCount(asset(2, {tx_count: 50}), 0), withOwnCount(asset(3, {tx_count: 20}), 7)];
        expect(resolveInitialSelectionWithSource(assets, null)).toEqual({ids: [2, 3, 1], source: 'fallback'});
    });

    it('falls back to a small readable handful when the user holds nothing', () => {
        const result = resolveInitialSelectionWithSource(catalogue(30), null, []);
        expect(result.source).toBe('fallback');
        expect(result.ids).toHaveLength(FALLBACK_SELECTION_SIZE);
    });

    it('ranks the fallback by how much the instrument has been transacted', () => {
        // Not by where the asset sits in the API's array: choosing by position
        // is still choosing, it just hides the arbitrariness behind an index.
        const assets = [asset(1, {tx_count: 2}), asset(2, {tx_count: 90}), asset(3, {tx_count: 40}), asset(4, {tx_count: 7})];
        expect(resolveInitialSelectionWithSource(assets, null).ids).toEqual([2, 3, 4, 1]);
    });

    it('breaks a fallback tie on id, so the handful is stable across reloads', () => {
        const assets = [asset(30, {tx_count: 5}), asset(10, {tx_count: 5}), asset(20, {tx_count: 5})];
        expect(resolveInitialSelectionWithSource(assets, null).ids).toEqual([10, 20, 30]);
    });

    it('ranks an asset with no transaction count as one with none', () => {
        const assets = [asset(1), asset(2, {tx_count: 3}), asset(3, {tx_count: 0})];
        expect(resolveInitialSelectionWithSource(assets, null).ids).toEqual([2, 1, 3]);
    });

    it('takes the most transacted out of a large catalogue, not the first six', () => {
        // Ids ascend while transaction counts ascend with them, so relevance
        // and position point in opposite directions: a positional pick would
        // return 1..6 and fail here.
        const assets = catalogue(500, (id) => asset(id, {tx_count: id}));
        const result = resolveInitialSelectionWithSource(assets, null).ids;
        expect(result).toHaveLength(FALLBACK_SELECTION_SIZE);
        expect(result).toEqual([500, 499, 498, 497, 496, 495]);
    });

    it('ranks without reordering the catalogue it was given', () => {
        // The ranking sorts, and a sort in place would silently reorder the
        // caller's list — the same array the filter row and the table read.
        const assets = [asset(1, {tx_count: 1}), asset(2, {tx_count: 99}), asset(3, {tx_count: 50})];
        const original = ids(assets);
        resolveInitialSelectionWithSource(assets, null);
        expect(ids(assets)).toEqual(original);
    });

    it('excludes inactive assets from that fallback, however transacted they are', () => {
        const assets = [asset(1, {active: false, tx_count: 9999}), asset(2, {tx_count: 3}), asset(3, {active: false}), asset(4, {tx_count: 1})];
        expect(resolveInitialSelectionWithSource(assets, null).ids).toEqual([2, 4]);
    });

    it('treats an asset with no active flag as active', () => {
        const assets = [{id: 1, currency: 'EUR'} as SelectableAsset, asset(2)];
        expect(resolveInitialSelectionWithSource(assets, null).ids).toEqual([1, 2]);
    });

    it('still selects a held asset that has been deactivated', () => {
        // The activity filter belongs to the fallback only: an asset the user
        // holds is on the table whether or not it still trades.
        const assets = [asset(1), asset(2, {active: false})];
        expect(resolveInitialSelectionWithSource(assets, null, [2])).toEqual({ids: [2], source: 'mine'});
    });

    it('still selects a persisted asset that has been deactivated', () => {
        const assets = [asset(1, {active: false}), asset(2)];
        expect(resolveInitialSelectionWithSource(assets, [1]).ids).toEqual([1]);
    });

    it('never opens on a hundred assets: five hundred in the catalogue, a handful on screen', () => {
        // The defect this module exists to prevent, asserted directly.
        const result = resolveInitialSelectionWithSource(catalogue(500), null).ids;
        expect(result).toHaveLength(FALLBACK_SELECTION_SIZE);
        expect(result.length).toBeLessThan(MAX_SELECTED_ASSETS);
    });

    it('caps a large held set at the API limit', () => {
        const assets = catalogue(500);
        expect(resolveInitialSelectionWithSource(assets, null, ids(assets))).toEqual({ids: ids(assets).slice(0, MAX_SELECTED_ASSETS), source: 'mine'});
    });

    it('caps a large persisted selection at the API limit', () => {
        const assets = catalogue(500);
        expect(resolveInitialSelectionWithSource(assets, ids(assets)).ids).toHaveLength(MAX_SELECTED_ASSETS);
    });

    it('selects nothing from an empty catalogue', () => {
        expect(resolveInitialSelectionWithSource([], [1, 2]).ids).toEqual([]);
        expect(resolveInitialSelectionWithSource([], null, [1, 2]).ids).toEqual([]);
        expect(resolveInitialSelectionWithSource([], null).ids).toEqual([]);
    });

    it('answers each rung its own input, held included', () => {
        // One input per rung, each held to the rung it must reach: a ladder that dropped `held` would open the second on the fallback.
        const assets = catalogue(5);
        const inputs: ReadonlyArray<readonly [readonly number[] | null, readonly number[], {ids: number[]; source: SelectionSource}]> = [
            [[4, 2], [1], {ids: [4, 2], source: 'persisted'}],
            [null, [3, 5], {ids: [3, 5], source: 'mine'}],
            [null, [], {ids: [1, 2, 3, 4, 5], source: 'fallback'}],
        ];
        for (const [persisted, held, expected] of inputs) {
            expect(resolveInitialSelectionWithSource(assets, persisted, held)).toEqual(expected);
        }
    });
});

describe('applyBulkAction', () => {
    // The candidates are what an action may bring in: the page's catalogue without
    // the assets Risk's engine rules out for the period. A ruled-out asset already
    // in the selection is *parked* there, as a greyed chip — selected, and never a
    // candidate. Here that is 9.
    const assets = catalogue(9);
    const candidates = (...wanted: number[]): SelectableAsset[] => assets.filter((entry) => wanted.includes(entry.id));

    it('"all" adds every candidate to what was already selected', () => {
        expect(applyBulkAction('all', [1], candidates(2, 3))).toEqual([1, 2, 3]);
    });

    it('"all" keeps a parked asset where it is', () => {
        expect(applyBulkAction('all', [9], candidates(1, 2))).toEqual([9, 1, 2]);
    });

    it('"all" never selects the same asset twice', () => {
        const result = applyBulkAction('all', [1, 2], candidates(1, 2, 3));
        expect(result).toEqual([1, 2, 3]);
        expect(new Set(result).size).toBe(result.length);
    });

    it('"all" with no candidate leaves the selection as it was', () => {
        expect(applyBulkAction('all', [4, 5], [])).toEqual([4, 5]);
    });

    it('"all" truncates at the API limit rather than failing', () => {
        // The one place the hundred is legitimate: the user asked for it.
        const huge = catalogue(150);
        const result = applyBulkAction('all', [], huge);
        expect(result).toHaveLength(MAX_SELECTED_ASSETS);
        expect(result).toEqual(ids(huge).slice(0, MAX_SELECTED_ASSETS));
    });

    it('"none" empties the selection, the parked assets included', () => {
        // "Deselect all" leaving chips behind would be a button that lies.
        expect(applyBulkAction('none', [1, 2, 9], candidates(1, 2))).toEqual([]);
    });

    it('"none" empties the selection even when nothing is a candidate', () => {
        // Not one of these is a candidate, and they still go: "none" is about the
        // selection, not about the list. It used to leave this selection untouched.
        expect(applyBulkAction('none', [1, 2], [])).toEqual([]);
    });

    it('"invert" keeps the parked assets, drops the selected candidates and adds the others', () => {
        const result = applyBulkAction('invert', [1, 9], candidates(1, 2, 3));
        expect(result).toContain(9);
        expect(result).not.toContain(1);
        expect(ascending(result)).toEqual([2, 3, 9]);
    });

    it('"invert" never selects the same asset twice', () => {
        const duplicated = [...candidates(2), ...candidates(2)];
        expect(applyBulkAction('invert', [], duplicated)).toEqual([2]);
    });

    it('"all" and "invert" keep every parked asset at the API limit, and truncate what they add', () => {
        // Five parked assets and 150 candidates: the cap cuts into the candidates
        // brought in, never into what was parked.
        const parked = [201, 202, 203, 204, 205];
        const huge = catalogue(150);
        const expected = [...parked, ...ids(huge).slice(0, MAX_SELECTED_ASSETS - parked.length)];
        for (const action of ['all', 'invert'] as const) {
            expect(applyBulkAction(action, parked, huge), action).toEqual(expected);
        }
    });

    it('no action can hand back more than the API limit', () => {
        const huge = catalogue(300);
        const selected = ids(huge).slice(0, MAX_SELECTED_ASSETS);
        const actions: BulkAction[] = ['all', 'none', 'invert'];
        for (const action of actions) {
            expect(applyBulkAction(action, selected, huge).length).toBeLessThanOrEqual(MAX_SELECTED_ASSETS);
        }
    });

    it('hands back a new array rather than the selection it was given', () => {
        const selected = [1, 2];
        const actions: BulkAction[] = ['all', 'none', 'invert'];
        for (const action of actions) {
            expect(applyBulkAction(action, selected, candidates(2, 3))).not.toBe(selected);
        }
        expect(selected).toEqual([1, 2]);
    });
});

/**
 * labBenchmarkId — the benchmark the lab's comparison levels measure against.
 *
 * A non-null answer is what starts them: the beta and correlation columns, and
 * the benchmark's dot on L3°'s chart, begin only from an id. Two guards keep a
 * wrong id out of the request:
 *
 *  - **The state, pinned on its own.** Risk's shared picker, `BenchmarkSelect`,
 *    publishes `pending` while a stored choice is still being confirmed against
 *    the asset list, `unknown` for a stored id no asset matches, `none` when
 *    nothing is stored and — since D378 — `blocked` for a confirmed choice the
 *    engine cannot measure over the page's period; only `set` is a choice to
 *    measure against, and no other id may reach the request. For the first three
 *    no component test can pin this guard: the picker's `value` stays null until
 *    `set`, so removing it there is an equivalent mutant. Not for `blocked`: the
 *    choice keeps its id, in the trigger and in `value`, so the state is all that
 *    keeps it out of L3°'s request — which `risk-lab.spec.ts` also pins through
 *    the page (benchmark picker (g)). Here every row carries an id the other
 *    guard lets through, and first proves it under `set`.
 *  - **The value.** A confirmed state that comes with no id names no benchmark:
 *    the answer is `null` itself, the one value that starts nothing.
 *
 * 🎯 No longer a guard (D371): the selection. A benchmark the reader also
 * selected is measured against like any other — `asset_set_comparison` 1.1.0
 * accepts it, measures its own volatility and return like the others' and
 * leaves it out of the comparison's items, where its beta and correlation with
 * itself would be 1 by construction; L3° marks those two cells instead. So the
 * call no longer takes the selection at all: there is nothing left to refuse an
 * id with.
 */
describe('labBenchmarkId', () => {
    /** What the reader selected beside the benchmark: the ids the removed third parameter used to refuse. */
    const SELECTED: readonly number[] = [7, 9];

    it.each<[string, number, boolean]>([
        ['outside the selection', 5, false],
        // D371: the ids the old guard refused, wherever they sat in the selection.
        ['that is also the first selected asset', 7, true],
        ['that is also the last selected asset', 9, true],
    ])('measures against a confirmed benchmark %s', (_label, value, selected) => {
        expect(SELECTED.includes(value), 'premise: where the benchmark sits against the selection').toBe(selected);
        expect(labBenchmarkId('set', value)).toBe(value);
    });

    it.each<[string, RiskBenchmarkState, number]>([
        ['the stored choice is still pending confirmation', 'pending', 7],
        ['the stored id matches no asset', 'unknown', 7],
        ['nothing is stored', 'none', 7],
        // D378: confirmed, and kept by the picker with its id, but not measurable over the page's period.
        ['the engine rules the confirmed choice out over the period', 'blocked', 7],
    ])('measures against nothing while %s, however usable the id', (_label, state, value) => {
        // The control: confirmed, this very id would be measured against — the state alone refuses it.
        expect(labBenchmarkId('set', value), 'the same id, confirmed').toBe(value);
        expect(labBenchmarkId(state, value)).toBeNull();
    });

    it('measures against nothing when no id comes with the choice, even once confirmed', () => {
        // `null` itself: `undefined` is not the contract's "no comparison".
        expect(labBenchmarkId('set', null)).toBeNull();
    });
});

/**
 * labL3Waits — whether L3° holds its question back for the eligibility verdicts.
 *
 * D378, the developer's decision of 06/10/2026: a stored benchmark the engine
 * cannot measure over the page's period is not tried — «Non lo prova». The lab
 * hands its picker its own verdicts (`verdicts={eligibilityView}`), and the
 * picker does not wait for them: with the map still empty it says `set`, and
 * `blocked` once the verdict lands. An L3° that asked on `set` would therefore
 * ask with the benchmark, then again without it: the benchmark tried, and the
 * table drawn twice.
 *
 * So L3° waits whenever a benchmark is chosen and the verdict that decides it
 * has not come:
 *
 *  - `pending` waits, as before D378: the choice itself is not confirmed yet,
 *    whatever the verdicts say;
 *  - a chosen benchmark, `set` or `blocked`, waits while the verdicts for the
 *    current question are out, and asks once they have settled — answered, or
 *    failed: a failed question blocks nothing, and an L3° waiting for it would
 *    never ask. `blocked` with the verdicts out happens only on a re-ask — a
 *    new period, a new list — when the old verdict no longer decides: asked
 *    then, L3° would follow a stale verdict and ask again once the new one
 *    lands, so it waits for one question with the new verdict, as `set` does;
 *  - `none` and `unknown` never wait: nothing usable is chosen — nothing
 *    stored, or an id no asset matches — so their question carries no
 *    benchmark (`labBenchmarkId`), and a wait would only hold back figures no
 *    verdict can change.
 */
describe('labL3Waits', () => {
    /**
     * Every state the picker publishes, kept complete by the compiler: a key
     * missing here, or one the type lacks, fails to type-check, so a new state
     * cannot reach the lab without its rows below.
     */
    const STATES: Record<RiskBenchmarkState, true> = {none: true, pending: true, set: true, unknown: true, blocked: true};

    /** [why, state, the verdicts settled]: the pairs where L3° waits. */
    const WAITS: ReadonlyArray<[string, RiskBenchmarkState, boolean]> = [
        ['the stored choice is still being confirmed, the verdicts out', 'pending', false],
        ['the stored choice is still being confirmed, though the verdicts are in', 'pending', true],
        ['a confirmed benchmark has no verdict yet: asked now, it would be tried', 'set', false],
        ['a benchmark blocked on an old verdict awaits the current question: the new verdict decides', 'blocked', false],
    ];

    /** [why, state, the verdicts settled]: the pairs where L3° asks at once. */
    const ASKS: ReadonlyArray<[string, RiskBenchmarkState, boolean]> = [
        ['a confirmed benchmark has its verdict and is still `set`: measurable, or the question failed, which blocks nothing', 'set', true],
        ['the current verdict rules the benchmark out: the question carries none', 'blocked', true],
        ['the stored id matches no asset, the verdicts in', 'unknown', true],
        ['the stored id matches no asset, the verdicts out', 'unknown', false],
        ['nothing is stored, the verdicts in', 'none', true],
        ['nothing is stored, the verdicts out', 'none', false],
    ];

    it.each(WAITS)('L3° waits while %s', (_label, state, settled) => {
        expect(labL3Waits(state, settled)).toBe(true);
    });

    it.each(ASKS)('L3° asks at once when %s', (_label, state, settled) => {
        expect(labL3Waits(state, settled)).toBe(false);
    });

    it('the two tables hold every state the picker publishes, with the verdicts out and in, once each', () => {
        // The tables' own premise: a pair left out of both would be a rule nobody pinned.
        const held = [...WAITS, ...ASKS].map(([, state, settled]) => `${state}/${settled}`).sort();
        const every = (Object.keys(STATES) as RiskBenchmarkState[]).flatMap((state) => [`${state}/false`, `${state}/true`]).sort();
        expect(held).toEqual(every);
    });
});
