// @vitest-environment jsdom
//
// The docblock above is load-bearing: the store's readers are tracked through `createSubscriber`, and under the default
// `node` environment `$effect` never runs, so "the reader runs again" would pass on a reader that never ran at all
// (`$test/runes.svelte`; `assertEffectsRun` turns that into a message).
/**
 * sectorStore — the session cache of GET /utilities/sectors (DV; the developer, 15/10/2026: no emoji written in the
 * frontend, «se la andasse a prendere dal backend per essere centralizzati»).
 *
 * What is pinned:
 *
 * - **Before the list arrives a key has no emoji**: `''`, never a guess — for a sector, a bucket or an unknown key
 *   alike; no keys; version 0. Reading does not load.
 * - **After it**: the emoji of every sector and of the two allocation buckets, as the backend lists them; the backend's
 *   `fallback_emoji` for a key it lists nowhere; `getSectorKeys()` the sectors alone, in the backend's order — the
 *   buckets never reach a select; the version bumped once.
 * - **The names `Object.prototype` holds are keys like any other** (regression): `constructor`, `toString`,
 *   `hasOwnProperty` and `__proto__` read `''` before the load and the fallback after it. The store kept its emoji in a
 *   plain object, which answered them with what the prototype holds — a function, an object; it keeps them in a `Map`.
 * - **One request**, whoever asks: concurrent callers share it, and once loaded no call asks again.
 * - **A failed load** leaves the store as it was — no emoji, not even the fallback, which is the backend's to give —
 *   logs the error, and the next call tries again.
 * - **Reactivity**: a reader inside an effect runs again when the list arrives, every reader of every kind; a failed
 *   load runs none of them again, the retry that succeeds does.
 *
 * `$lib/api` is mocked: the endpoint's answer is the whole input, owned by each case and shaped as the backend's
 * `SectorListResponse` (`items`, `buckets`, `fallback_emoji`). The store keeps module state, so every case loads a
 * fresh copy (`vi.resetModules()` and a dynamic import) — with `svelte` and the rune harness taken from the same fresh
 * registry, so the store's subscriber and the test's effects share one runtime.
 *
 * @module stores/reference/sectorStore.test
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

const {listSectors} = vi.hoisted(() => ({listSectors: vi.fn()}));

vi.mock('$lib/api', () => ({
    zodiosApi: {list_sectors_api_v1_utilities_sectors_get: listSectors},
}));

/**
 * The endpoint's answer: sectors with the backend's glyphs (`SECTOR_EMOJI`, `backend/app/utils/asset/sector.py`), the
 * two buckets, and a fallback. The fallback here is a glyph listed nowhere else — the backend's is `❓`, the same as
 * Unknown's — so a fallback on screen cannot be mistaken for a listed key's emoji.
 */
const ANSWER = {
    items: [
        {key: 'Industrials', emoji: '🏭'},
        {key: 'Technology', emoji: '💻'},
        {key: 'Health Care', emoji: '🏥'},
        {key: 'Other', emoji: '📦'},
    ],
    buckets: [
        {key: 'Liquidity', emoji: '💰'},
        {key: 'Unknown', emoji: '❓'},
    ],
    fallback_emoji: '🔣',
};
const LISTED = [...ANSWER.items, ...ANSWER.buckets];

/** A fresh store, and the svelte runtime and rune harness of the same registry. */
async function fresh() {
    vi.resetModules();
    const store = await import('./sectorStore');
    const {flushSync} = await import('svelte');
    const runes = await import('$test/runes.svelte');
    return {store, flushSync, runes};
}

/** A promise the test settles by hand: a request still in flight. */
function deferred<T>() {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((settle) => {
        resolve = settle;
    });
    return {promise, resolve};
}

/** The names `Object.prototype` holds: a lookup in a plain object answers each with a function or an object, never nothing. */
const PROTOTYPE_NAMES: readonly string[] = ['constructor', 'toString', 'hasOwnProperty', '__proto__'];

/** What `read` answers for `key`, written `key → "value"`, or `key → [object Function]` when it is no string: one red names every leak. */
function answered(read: (key: string) => unknown, key: string): string {
    const value = read(key);
    return `${key} → ${typeof value === 'string' ? JSON.stringify(value) : Object.prototype.toString.call(value)}`;
}

beforeEach(() => {
    listSectors.mockReset();
});

afterEach(() => {
    vi.restoreAllMocks();
});

describe('sectorStore — before the list arrives', () => {
    it('has no emoji for any key — a sector, a bucket, an unknown key — no keys, version 0; and reading does not load', async () => {
        const {store} = await fresh();

        for (const key of ['Technology', 'Liquidity', 'Unknown', 'Quantum Computing']) expect(store.getSectorEmoji(key), key).toBe('');
        expect(store.getSectorKeys()).toEqual([]);
        expect(store.sectorEmojiVersion()).toBe(0);
        expect(listSectors, 'a read asks the backend nothing').not.toHaveBeenCalled();
    });
});

describe('sectorStore — after the load', () => {
    it('asks GET /utilities/sectors with Other included, and answers every sector and both buckets as the backend wrote them', async () => {
        const {store} = await fresh();
        listSectors.mockResolvedValue(ANSWER);

        await store.ensureSectorsLoaded();

        expect(listSectors).toHaveBeenCalledTimes(1);
        expect(listSectors).toHaveBeenCalledWith({queries: {include_other: true}});
        expect(Object.fromEntries(LISTED.map(({key}) => [key, store.getSectorEmoji(key)]))).toEqual(Object.fromEntries(LISTED.map(({key, emoji}) => [key, emoji])));
        expect(store.sectorEmojiVersion(), 'bumped once').toBe(1);
    });

    it("answers the backend's fallback for a key it lists nowhere — never another key's emoji", async () => {
        const {store} = await fresh();
        listSectors.mockResolvedValue(ANSWER);
        await store.ensureSectorsLoaded();

        expect(
            LISTED.map(({emoji}) => emoji),
            'barrier: the fallback is no listed emoji',
        ).not.toContain(ANSWER.fallback_emoji);
        for (const key of ['Quantum Computing', 'Government Bonds', '']) expect(store.getSectorEmoji(key), JSON.stringify(key)).toBe(ANSWER.fallback_emoji);
    });

    it('lists the sectors alone, in the order the backend lists them: the buckets never reach a select', async () => {
        const {store} = await fresh();
        listSectors.mockResolvedValue(ANSWER);
        await store.ensureSectorsLoaded();

        expect(store.getSectorKeys()).toEqual(ANSWER.items.map(({key}) => key));
        expect(store.getSectorEmoji('Liquidity'), 'barrier: the buckets were read, for their emoji').toBe('💰');
    });
});

describe('sectorStore — the names Object.prototype holds are keys like any other (regression)', () => {
    it("answers constructor, toString, hasOwnProperty and __proto__ with '' before the load and with the backend's fallback after it — never a function or an object", async () => {
        const {store} = await fresh();
        listSectors.mockResolvedValue(ANSWER);
        expect(
            LISTED.filter(({key}) => PROTOTYPE_NAMES.includes(key)),
            'premise: the backend lists none of these names, so the fallback is what they must read',
        ).toEqual([]);

        const before = PROTOTYPE_NAMES.map((key) => answered(store.getSectorEmoji, key));
        expect(listSectors, 'premise: read before any load').not.toHaveBeenCalled();
        expect(before, 'before the load, a name of Object.prototype reads what the prototype holds instead of nothing').toEqual(PROTOTYPE_NAMES.map((key) => `${key} → ""`));

        await store.ensureSectorsLoaded();
        expect(store.getSectorEmoji('Technology'), 'barrier: the list landed, and a listed key reads its own emoji').toBe('💻');
        expect(
            LISTED.map(({emoji}) => emoji),
            'barrier: the fallback is no listed emoji',
        ).not.toContain(ANSWER.fallback_emoji);

        const after = PROTOTYPE_NAMES.map((key) => answered(store.getSectorEmoji, key));
        expect(after, 'after the load, a name of Object.prototype reads what the prototype holds instead of the fallback').toEqual(PROTOTYPE_NAMES.map((key) => `${key} → ${JSON.stringify(ANSWER.fallback_emoji)}`));
    });
});

describe('sectorStore — one request', () => {
    it('shares one request among concurrent callers, answers nothing while it is in flight, and asks no more once loaded', async () => {
        const {store} = await fresh();
        const answer = deferred<typeof ANSWER>();
        listSectors.mockReturnValue(answer.promise);

        const first = store.ensureSectorsLoaded();
        const second = store.ensureSectorsLoaded();
        expect(listSectors, 'two callers, one request').toHaveBeenCalledTimes(1);
        expect(store.getSectorEmoji('Technology'), 'in flight is not loaded').toBe('');

        answer.resolve(ANSWER);
        await Promise.all([first, second]);
        expect(store.getSectorEmoji('Technology')).toBe('💻');

        await store.ensureSectorsLoaded();
        expect(listSectors, 'loaded: the cache answers').toHaveBeenCalledTimes(1);
        expect(store.sectorEmojiVersion(), 'one load, one bump').toBe(1);
    });
});

describe('sectorStore — a failed load', () => {
    it('logs the error, leaves no emoji and not even the fallback, and lets the next call try again', async () => {
        const {store} = await fresh();
        const failure = new Error('network down');
        listSectors.mockRejectedValueOnce(failure).mockResolvedValueOnce(ANSWER);
        const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

        await expect(store.ensureSectorsLoaded(), 'the failure is not thrown at the caller').resolves.toBeUndefined();
        expect(consoleError).toHaveBeenCalledWith('Failed to load sectors:', failure);
        expect(store.getSectorEmoji('Technology')).toBe('');
        expect(store.getSectorEmoji('Quantum Computing'), 'the fallback is the backend’s: unknown until a load succeeds').toBe('');
        expect(store.getSectorKeys()).toEqual([]);
        expect(store.sectorEmojiVersion()).toBe(0);

        await store.ensureSectorsLoaded();
        expect(listSectors, 'the next call asks again').toHaveBeenCalledTimes(2);
        expect(store.getSectorEmoji('Technology')).toBe('💻');
        expect(store.sectorEmojiVersion()).toBe(1);
    });
});

describe('sectorStore — reactivity: a reader inside an effect runs again when the list arrives', () => {
    it('runs every reader again — getSectorEmoji, sectorEmojiVersion, getSectorKeys — once the load lands', async () => {
        const {store, flushSync, runes} = await fresh();
        runes.assertEffectsRun();
        listSectors.mockResolvedValue(ANSWER);

        const emoji = runes.recordReads(() => store.getSectorEmoji('Technology'));
        const version = runes.recordReads(() => store.sectorEmojiVersion());
        const keys = runes.recordReads(() => [...store.getSectorKeys()]);
        try {
            expect([emoji.values, version.values, keys.values], 'each reader ran once, before the load').toEqual([[''], [0], [[]]]);

            await store.ensureSectorsLoaded();
            flushSync();

            expect(emoji.values).toEqual(['', '💻']);
            expect(version.values).toEqual([0, 1]);
            expect(keys.values).toEqual([[], ANSWER.items.map(({key}) => key)]);
        } finally {
            for (const recorder of [emoji, version, keys]) recorder.stop();
        }
    });

    it('runs no reader again after a failed load; the retry that succeeds does', async () => {
        const {store, flushSync, runes} = await fresh();
        runes.assertEffectsRun();
        listSectors.mockRejectedValueOnce(new Error('network down')).mockResolvedValueOnce(ANSWER);
        vi.spyOn(console, 'error').mockImplementation(() => {});

        const version = runes.recordReads(() => store.sectorEmojiVersion());
        try {
            await store.ensureSectorsLoaded();
            flushSync();
            expect(version.values, 'failed: nothing to read again').toEqual([0]);

            await store.ensureSectorsLoaded();
            flushSync();
            expect(version.values, 'the same reader, alive: the retry that lands runs it again').toEqual([0, 1]);
        } finally {
            version.stop();
        }
    });
});
