/**
 * whatsNew.ts — which chapters «What's new since your last version» shows (workstream A, lot C-54).
 *
 * After an update, the first visit of an account shows the chapters of the bundled CHANGELOG.md released since the
 * version that account last saw. The backend says which, in the user payload of the login and of `GET /auth/me`:
 * `whats_new: {since: string | null, release: string} | null`. `whatsNewChapters(chapters, whatsNew)` turns it into the
 * chapters to show, generic over the chapter type so that the modal can pass the displayed (localized) chapters too.
 *
 * The contract under test (approved by the coordinator, 17/10):
 *   - WN-01: the module sits next to this test and exports `whatsNewChapters` as a function;
 *   - WN-02: `null` or `undefined` → `[]`, nothing to show;
 *   - WN-03: `since` null (an account from before the feature) → only the chapter(s) equal to `release`;
 *   - WN-04: otherwise the chapters with `since < version ≤ release`: `release` included, `since` excluded, whether or
 *     not either bound is itself a chapter;
 *   - WN-05: never an `Unreleased` chapter, in any case, not even when `release` reads «Unreleased»;
 *   - WN-06: a chapter whose version does not parse is skipped;
 *   - WN-07: `since ≥ release` (nothing new, or a downgrade) → `[]`;
 *   - WN-08: versions compare like `compareVersions` of update-check/updateCheck.ts — `v1.2.1` equals `1.2.1`, and a
 *     git-describe version (`1.2.1-3-g0a1b2c3`) compares as its base release —, on the bounds and on the chapters;
 *   - WN-09: the input order is kept (the changelog is newest first): no sorting, and the input untouched;
 *   - WN-10: generic — a displayed chapter comes back with its own fields (its `lang`);
 *   - WN-11: on the real bundled CHANGELOG.md, its newest released version as `release` and the next one as `since`
 *     give exactly that chapter (and so does `since` null).
 * Every case that expects `[]` also gets something from the same chapters, so a rule that always answers `[]` passes
 * none of them.
 *
 * Node env: pure logic. The chapters are synthetic, newest first like the file, except in WN-11, which reads the
 * real `changelogChapters` (node can load the `?raw` import of the repository's CHANGELOG.md; jsdom refuses it).
 * `$lib/api` is a client that throws on any request: the rule asks nothing of the server, even if it reaches
 * `compareVersions` through updateCheck.ts.
 *
 * Written red-first, before `whatsNew.ts` exists: the module is loaded lazily through a glob (the pattern of
 * `instance/profile.test.ts`), so every case fails on its own, naming the missing module.
 */
import {describe, expect, it, vi} from 'vitest';
import {changelogChapters, type ChangelogChapter} from './changelog';

// The rule sends nothing: a request through the generated client fails the case instead of reaching a server.
vi.mock('$lib/api', () => {
    const zodiosApi = new Proxy(
        {},
        {
            get: (_target, alias) =>
                typeof alias !== 'string' || alias === 'then'
                    ? undefined
                    : () => {
                          throw new Error(`whatsNew.test: a request went through zodiosApi.${alias}`);
                      },
        },
    );
    return {zodiosApi, schemas: {}, axiosInstance: {}, ApiError: class ApiError extends Error {}};
});

// ---------------------------------------------------------------------------
// The module under test
// ---------------------------------------------------------------------------

/** What the backend sends in the user payload: `null` when there is nothing to show. */
interface WhatsNewInfo {
    since: string | null;
    release: string;
}

interface WhatsNewModule {
    whatsNewChapters<T extends ChangelogChapter>(chapters: readonly T[], whatsNew: WhatsNewInfo | null | undefined): T[];
}

// A lazy glob rather than a literal import: the module does not exist yet, and a missing file must fail each case on its
// own, naming it, instead of failing the whole file at collection.
const WHATS_NEW_MODULES = import.meta.glob<Partial<WhatsNewModule>>('./whatsNew.ts');

async function importWhatsNew(): Promise<WhatsNewModule> {
    const load = WHATS_NEW_MODULES['./whatsNew.ts'];
    if (!load) throw new Error('whatsNew.ts cannot be found next to this test (src/lib/features/changelog/): it should export whatsNewChapters(chapters, whatsNew)');
    const mod = await load();
    if (typeof mod.whatsNewChapters !== 'function') throw new Error('whatsNew.ts does not export whatsNewChapters as a function');
    return mod as WhatsNewModule;
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function chapter(version: string, date = '2026-01-01'): ChangelogChapter {
    const body = `- what changed in ${version}\n`;
    return {version, date, body, sections: [{title: null, body, subsections: []}]};
}

/** A changelog as the file writes it: newest first, the upcoming chapter on top. */
const CHANGELOG: readonly ChangelogChapter[] = [chapter('Unreleased', ''), chapter('1.3.0', '2026-12-01'), chapter('1.2.1', '2026-10-15'), chapter('1.2.0', '2026-10-14'), chapter('1.1.0', '2026-09-07'), chapter('1.0.1', '2026-07-21'), chapter('1.0.0', '2026-07-20')];

/** A range the fixture has chapters for: the positive control of every case that expects nothing. */
const SOME_RANGE: WhatsNewInfo = {since: '1.1.0', release: '1.2.1'};

function versions(chapters: readonly ChangelogChapter[]): string[] {
    return chapters.map((c) => c.version);
}

// ---------------------------------------------------------------------------
// The cases
// ---------------------------------------------------------------------------

describe('whatsNew.ts — the module', () => {
    it('WN-01: exports whatsNewChapters(chapters, whatsNew) as a function', async () => {
        const {whatsNewChapters} = await importWhatsNew();

        expect(typeof whatsNewChapters).toBe('function');
    });
});

describe('whatsNewChapters — nothing to show', () => {
    it.each([
        ['null', null],
        ['undefined', undefined],
    ] as const)('WN-02: whatsNew %s → []', async (_label, whatsNew) => {
        const {whatsNewChapters} = await importWhatsNew();

        expect(whatsNewChapters(CHANGELOG, whatsNew)).toEqual([]);
        expect(versions(whatsNewChapters(CHANGELOG, SOME_RANGE)), 'control: the same chapters have something to show for a real range').toEqual(['1.2.1', '1.2.0']);
    });

    it.each([
        [{since: '1.2.1', release: '1.2.1'}, 'nothing released since the last version seen'],
        [{since: '1.3.0', release: '1.2.0'}, 'a downgrade'],
        [{since: '2.0.0', release: '1.0.0'}, 'a downgrade across a major'],
    ])('WN-07: %o (%s) → []', async (whatsNew) => {
        const {whatsNewChapters} = await importWhatsNew();

        expect(whatsNewChapters(CHANGELOG, whatsNew)).toEqual([]);
        expect(versions(whatsNewChapters(CHANGELOG, SOME_RANGE)), 'control: the same chapters have something to show for a real range').toEqual(['1.2.1', '1.2.0']);
    });
});

describe('whatsNewChapters — an account from before the feature (since null)', () => {
    it.each([
        ['1.2.1', ['1.2.1']],
        ['1.3.0', ['1.3.0']],
        ['1.0.0', ['1.0.0']],
    ])('WN-03: since null, release %s → only that chapter', async (release, expected) => {
        const {whatsNewChapters} = await importWhatsNew();

        expect(versions(whatsNewChapters(CHANGELOG, {since: null, release}))).toEqual(expected);
    });

    it('WN-03: since null, a release the changelog has no chapter for → []', async () => {
        const {whatsNewChapters} = await importWhatsNew();

        expect(whatsNewChapters(CHANGELOG, {since: null, release: '1.2.5'})).toEqual([]);
        expect(versions(whatsNewChapters(CHANGELOG, {since: null, release: '1.2.1'})), 'control: a release with a chapter').toEqual(['1.2.1']);
    });
});

describe('whatsNewChapters — the chapters released since the last version seen', () => {
    it.each([
        [{since: '1.1.0', release: '1.2.1'}, ['1.2.1', '1.2.0']],
        [{since: '1.2.0', release: '1.2.1'}, ['1.2.1']],
        [{since: '1.0.1', release: '1.1.0'}, ['1.1.0']],
        [{since: '1.0.0', release: '1.3.0'}, ['1.3.0', '1.2.1', '1.2.0', '1.1.0', '1.0.1']],
    ])('WN-04: %o → since excluded, release included: %o', async (whatsNew, expected) => {
        const {whatsNewChapters} = await importWhatsNew();

        expect(versions(whatsNewChapters(CHANGELOG, whatsNew))).toEqual(expected);
    });

    it.each([
        [{since: '1.1.5', release: '1.2.5'}, ['1.2.1', '1.2.0']],
        [{since: '0.9.0', release: '1.0.5'}, ['1.0.1', '1.0.0']],
        [{since: '1.2.0', release: '1.2.9'}, ['1.2.1']],
    ])('WN-04: bounds that are not chapters themselves: %o → %o', async (whatsNew, expected) => {
        const {whatsNewChapters} = await importWhatsNew();

        expect(versions(whatsNewChapters(CHANGELOG, whatsNew))).toEqual(expected);
    });
});

describe('whatsNewChapters — what is never shown', () => {
    it('WN-05: an Unreleased chapter, whatever its case, never — not even when the release reads «Unreleased»', async () => {
        const {whatsNewChapters} = await importWhatsNew();
        const upcoming = [chapter('Unreleased', ''), chapter('unreleased', ''), chapter('UNRELEASED', ''), ...CHANGELOG.slice(1)];

        expect(versions(whatsNewChapters(upcoming, {since: '1.2.1', release: '99.0.0'})), 'the only released chapter above 1.2.1 is 1.3.0').toEqual(['1.3.0']);
        expect(whatsNewChapters(upcoming, {since: null, release: 'Unreleased'})).toEqual([]);
        expect(whatsNewChapters(upcoming, {since: null, release: 'unreleased'})).toEqual([]);
    });

    it('WN-06: a chapter whose version does not parse is skipped', async () => {
        const {whatsNewChapters} = await importWhatsNew();
        const odd = [chapter('Next', ''), chapter('1.3.0'), chapter('2.x'), chapter('1.2.1'), chapter('latest'), chapter('1.2.0'), chapter('1.1.0')];

        expect(versions(whatsNewChapters(odd, {since: '1.1.0', release: '9.0.0'}))).toEqual(['1.3.0', '1.2.1', '1.2.0']);
        expect(whatsNewChapters(odd, {since: null, release: '2.x'}), 'a chapter that does not parse is skipped even when it reads like the release').toEqual([]);
        expect(versions(whatsNewChapters(odd, {since: null, release: '1.2.1'})), 'control: a release that parses').toEqual(['1.2.1']);
    });
});

describe('whatsNewChapters — versions compare like compareVersions', () => {
    it.each([
        ['a v prefix on the release', {since: null, release: 'v1.2.1'}, ['1.2.1']],
        ['a v prefix on both bounds', {since: 'v1.1.0', release: 'v1.2.1'}, ['1.2.1', '1.2.0']],
        ['a git-describe release', {since: null, release: '1.2.1-3-g0a1b2c3'}, ['1.2.1']],
        ['git-describe bounds', {since: '1.1.0-7-gdeadbee', release: 'v1.2.1-3-g0a1b2c3'}, ['1.2.1', '1.2.0']],
        ['a since built after the release', {since: '1.2.1-2-gabcdef0', release: '1.2.1'}, []],
    ])('WN-08: %s — %o → %o', async (_label, whatsNew, expected) => {
        const {whatsNewChapters} = await importWhatsNew();

        expect(versions(whatsNewChapters(CHANGELOG, whatsNew))).toEqual(expected);
    });

    it('WN-08: a v prefix on the chapters themselves compares by the release it names', async () => {
        const {whatsNewChapters} = await importWhatsNew();
        const prefixed = [chapter('v1.2.1'), chapter('v1.2.0'), chapter('1.1.0')];

        expect(versions(whatsNewChapters(prefixed, {since: '1.1.0', release: '1.2.1'}))).toEqual(['v1.2.1', 'v1.2.0']);
        expect(versions(whatsNewChapters(prefixed, {since: null, release: '1.2.1'}))).toEqual(['v1.2.1']);
    });
});

describe('whatsNewChapters — order and identity', () => {
    it('WN-09: keeps the order of its input, and leaves the input untouched', async () => {
        const {whatsNewChapters} = await importWhatsNew();
        const oldestFirst = [...CHANGELOG].reverse();
        const before = structuredClone(oldestFirst);

        expect(versions(whatsNewChapters(CHANGELOG, {since: '1.0.0', release: '1.2.1'})), 'newest first, as the changelog is').toEqual(['1.2.1', '1.2.0', '1.1.0', '1.0.1']);
        expect(versions(whatsNewChapters(oldestFirst, {since: '1.0.0', release: '1.2.1'})), 'the order it was given, not a sorted one').toEqual(['1.0.1', '1.1.0', '1.2.0', '1.2.1']);
        expect(oldestFirst, 'the input is untouched').toEqual(before);
    });

    it('WN-10: generic — a displayed chapter comes back with its own fields', async () => {
        const {whatsNewChapters} = await importWhatsNew();
        const displayed = CHANGELOG.map((c, i) => ({...c, lang: i % 2 === 0 ? 'it' : 'en'}));

        const shown = whatsNewChapters(displayed, SOME_RANGE);

        expect(shown).toEqual(displayed.filter((c) => c.version === '1.2.1' || c.version === '1.2.0'));
        expect(shown.map((c) => c.lang)).toEqual(['it', 'en']);
    });
});

describe('whatsNewChapters — the bundled CHANGELOG.md', () => {
    /** A released chapter heading: a plain x.y.z, as every released chapter of the file is written. */
    const RELEASED = /^\d+\.\d+\.\d+$/;

    function isNewer(a: string, b: string): boolean {
        const [pa, pb] = [a, b].map((v) => v.split('.').map(Number));
        for (let i = 0; i < 3; i++) if (pa[i] !== pb[i]) return pa[i] > pb[i];
        return false;
    }

    it('WN-11: its newest released version as release and the next one as since → exactly that chapter', async () => {
        const {whatsNewChapters} = await importWhatsNew();
        const released = changelogChapters.filter((c) => RELEASED.test(c.version));
        expect(released.length, 'premise: the bundled changelog has at least two released chapters').toBeGreaterThanOrEqual(2);
        const [newest, previous] = released;
        expect(isNewer(newest.version, previous.version), `premise: the file is newest first (${newest.version} above ${previous.version})`).toBe(true);

        expect(whatsNewChapters(changelogChapters, {since: previous.version, release: newest.version})).toEqual([newest]);
        expect(whatsNewChapters(changelogChapters, {since: null, release: newest.version}), 'an account from before the feature sees the same chapter').toEqual([newest]);
    });
});
