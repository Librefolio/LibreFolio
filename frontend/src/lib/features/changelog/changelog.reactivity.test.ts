// @vitest-environment jsdom
/**
 * changelog.ts — the translation cache of `createLocalizedChangelog` is observable (A-CL1): the REAL module, read from
 * effects.
 *
 * What it proves: a reader of `peek()` that saw a language missing is told when a load fills it, whoever started the
 * load. Both windows read the cache so — `ChangelogModal` and `WhatsNewModal` hold
 * `$derived(localizedChangelog.peek(uiLanguage) ?? …)` — and while the cache was a plain `Map`, that `$derived` could not
 * see it fill: a window closed while its translation loaded and reopened after the fill kept a stale `undefined`, «the
 * changelog stuck on loading» (M1 in `ChangelogModal.test.ts`), or the English of a failed load after another consumer
 * had loaded the translation (M2). The cure, commit 5ccb495e5: the cache `merged` is a `SvelteMap`. The component tests
 * drive a faithful fake of this module whose cache is a `SvelteMap` too, so they stay green if `changelog.ts` goes back
 * to `new Map`; this file drives the real `createLocalizedChangelog` and closes that gap. Written for the A-CL1 review:
 * red with `new Map`, green with `SvelteMap`.
 *
 * Why jsdom: under the default `node` environment `svelte/reactivity` is Svelte's server build (`SvelteMap` is
 * `globalThis.Map`), `$derived` is computed once and `$effect` never runs (`$test/runes.svelte`), so no reader could be
 * told anything, whichever map the module holds. jsdom resolves Svelte's client build. The readers are `recordReads`
 * effects (runes cannot be written in a `.test.ts`), and `assertEffectsRun()` fails the file loudly where effects do not
 * run.
 *
 * Why `./changelogSources` is mocked: in jsdom Vite refuses the `?raw` import of the repository's CHANGELOG.md, outside
 * `frontend/` — mocked or not, and with it every module that holds one. The bundled files are imported in
 * `changelogSources.ts` for this reason: replaced by an English text of this file's own and no translation, the real
 * `changelog.ts` loads. The module under test is imported by one statement, so a red run against a copy of it with
 * `new Map` swaps one specifier.
 *
 * The cases:
 *   1. the cure — a reader of `peek('it')` is told when `load('it')` fills the cache, and not before;
 *   2. whoever loads — two independent readers, as the two windows are, both see the fill of one load neither started;
 *   3. a failed load notifies nothing and caches nothing, and the next load, which arrives, tells the reader the failure
 *      left waiting (the module side of M2);
 *   4. English needs no load — `peek('en')` and a language without a translation answer English at once, and an Italian
 *      fill re-runs neither reader; an Italian reader of the same fill is the positive control of that negative.
 *
 * Every case builds its own changelog from this file's data — the English chapters, an Italian file translating one of
 * them, a loader the case answers — so no case shares a cache with another. Each reader records what it was told,
 * spelled `version:language` chapter by chapter, and is asserted exactly. No clock: the loads are answered by the case,
 * and `flushSync()` runs whatever effects a fill scheduled. The Italian sentence is this test's data, not catalogue copy.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';
import {assertEffectsRun, recordReads} from '$test/runes.svelte';
import {createLocalizedChangelog, parseChangelog, type DisplayedChapter, type LocalizedChangelog} from './changelog';

// This file's English changelog: the bundled text the module parses at load, and the English source of every case.
const bundled = vi.hoisted(() => ({
    english: `# Changelog

## [1.1.0] - 2026-09-01

### Added
- a cache the windows can follow

## [1.0.0] - 2026-07-01

### Added
- the first release
`,
}));

// The bundled files, replaced: the English text above and no translation, so the module loads without the `?raw` import
// jsdom refuses.
vi.mock('./changelogSources', () => ({englishChangelog: bundled.english, translationModules: {}}));

const ENGLISH = parseChangelog(bundled.english);

/** An Italian file translating 1.1.0 only, with a content line: the merge keeps a translated chapter only when it has content. */
const ITALIAN_RAW = `# Registro delle modifiche

## [1.1.0] - 2026-09-01

### Aggiunto
- una cache che le finestre possono seguire
`;

/** The English list, spelled: every chapter in English, in the English order. */
const SHOWN_IN_ENGLISH = ['1.1.0:en', '1.0.0:en'];
/** The Italian list, spelled: 1.1.0 translated, 1.0.0 still English. */
const SHOWN_IN_ITALIAN = ['1.1.0:it', '1.0.0:en'];

/** A displayed list spelled chapter by chapter, `version:language of its text`; undefined (still to load) stays undefined. */
function spell(chapters: readonly DisplayedChapter[] | undefined): string[] | undefined {
    return chapters?.map((chapter) => `${chapter.version}:${chapter.lang}`);
}

/** A changelog of this file's English chapters whose one translation, Italian, is fetched by `loader`. */
function italianOnly(loader: () => Promise<string>): LocalizedChangelog {
    return createLocalizedChangelog(ENGLISH, new Map([['it', loader]]));
}

/**
 * The Italian file, held: `loader` is the lazy chunk the module fetches, `fetched` settles once the module has asked for
 * it, and the file arrives only when the case calls `arrive`.
 */
function heldItalianFile() {
    let arrive!: (raw: string) => void;
    let markFetched!: () => void;
    const file = new Promise<string>((resolve) => {
        arrive = resolve;
    });
    const fetched = new Promise<void>((resolve) => {
        markFetched = resolve;
    });
    const loader = vi.fn(() => {
        markFetched();
        return file;
    });
    return {loader, fetched, arrive};
}

/** The effect roots the current case opened: all stopped after it, whatever its outcome. */
const roots: Array<() => void> = [];

/** A reader of `peek(locale)` from inside an effect, as a window's `$derived` reads it: every value it was told, spelled. */
function reader(changelog: LocalizedChangelog, locale: string): Array<string[] | undefined | Error> {
    const reads = recordReads(() => spell(changelog.peek(locale)));
    roots.push(reads.stop);
    return reads.values;
}

beforeAll(() => {
    assertEffectsRun();
});

afterEach(() => {
    for (const stop of roots.splice(0)) stop();
});

describe('createLocalizedChangelog, the real module: its cache tells the readers that saw a language missing (A-CL1)', () => {
    it("the cure: a reader of peek('it') is told when load('it') fills the cache", async () => {
        const file = heldItalianFile();
        const changelog = italianOnly(file.loader);
        const told = reader(changelog, 'it');
        expect(told, 'before any load: the language is missing').toEqual([undefined]);

        const loading = changelog.load('it');
        await file.fetched;
        flushSync();
        expect(told, 'its file asked for and not arrived: nothing to tell yet').toEqual([undefined]);

        file.arrive(ITALIAN_RAW);
        expect(spell(await loading), 'the load resolves to the merged list').toEqual(SHOWN_IN_ITALIAN);
        flushSync();

        expect(told, 'the fill reached the reader that saw the language missing').toEqual([undefined, SHOWN_IN_ITALIAN]);
        expect(spell(changelog.peek('it')), 'peek, read directly, answers the same list').toEqual(SHOWN_IN_ITALIAN);
        expect(file.loader, 'one fetch').toHaveBeenCalledTimes(1);
    });

    it("whoever loads: two independent readers both see the fill of one load('it') started outside either of them", async () => {
        const file = heldItalianFile();
        const changelog = italianOnly(file.loader);
        // Two readers in two effect roots, as the changelog window and the What's new popup each read the cache; the
        // second spells the language as a full locale.
        const first = reader(changelog, 'it');
        const second = reader(changelog, 'it-IT');
        expect(first, "the reader of peek('it'): missing").toEqual([undefined]);
        expect(second, "the reader of peek('it-IT'), the same language: missing").toEqual([undefined]);

        // One load, started here: by neither reader.
        const loading = changelog.load('it');
        file.arrive(ITALIAN_RAW);
        await loading;
        flushSync();

        expect(first, "the reader of peek('it') was told").toEqual([undefined, SHOWN_IN_ITALIAN]);
        expect(second, "the reader of peek('it-IT') was told").toEqual([undefined, SHOWN_IN_ITALIAN]);
        expect(file.loader, 'one fetch for both').toHaveBeenCalledTimes(1);
    });

    it('a failed load notifies nothing and caches nothing; the next load, which arrives, fills the cache and tells the reader', async () => {
        // The Italian file: its first fetch fails (a chunk that did not load), the next one arrives.
        const loader = vi.fn<() => Promise<string>>().mockRejectedValueOnce(new Error('translation chunk failed')).mockResolvedValueOnce(ITALIAN_RAW);
        const changelog = italianOnly(loader);
        const told = reader(changelog, 'it');
        expect(told, 'before any load: the language is missing').toEqual([undefined]);

        expect(spell(await changelog.load('it')), 'a failed load resolves to the English list, as documented').toEqual(SHOWN_IN_ENGLISH);
        flushSync();
        expect(told, 'the failure told the reader nothing').toEqual([undefined]);
        expect(changelog.peek('it'), 'and cached nothing: the language is still missing').toBeUndefined();

        // Asked again — by the window reopened, by another consumer: this time the file arrives.
        expect(spell(await changelog.load('it')), 'the next load resolves to the merged list').toEqual(SHOWN_IN_ITALIAN);
        flushSync();
        expect(told, 'the fill reached the reader the failure left waiting').toEqual([undefined, SHOWN_IN_ITALIAN]);
        expect(spell(changelog.peek('it')), 'peek, read directly, answers the same list').toEqual(SHOWN_IN_ITALIAN);
        expect(loader, 'the failure was not cached: the next load fetched again').toHaveBeenCalledTimes(2);
    });

    it("English needs no load: peek('en') and a language without a translation answer the English list at once, and an Italian fill re-runs neither reader", async () => {
        const file = heldItalianFile();
        const changelog = italianOnly(file.loader);
        const english = reader(changelog, 'en');
        const german = reader(changelog, 'de');
        expect(english, "peek('en'): the English list at once").toEqual([SHOWN_IN_ENGLISH]);
        expect(german, "peek('de'), a language without a translation: the English list at once").toEqual([SHOWN_IN_ENGLISH]);

        // The Italian fill, with its positive control: the same fill does tell a reader of the language it filled, so the
        // silence of the two readers above is theirs — not that of a cache that tells no one.
        const italian = reader(changelog, 'it');
        const loading = changelog.load('it');
        file.arrive(ITALIAN_RAW);
        await loading;
        flushSync();
        expect(italian, 'positive control: the fill told the Italian reader').toEqual([undefined, SHOWN_IN_ITALIAN]);

        expect(english, "the reader of peek('en'): read once, not re-run by the Italian fill").toEqual([SHOWN_IN_ENGLISH]);
        expect(german, "the reader of peek('de'): read once, not re-run by the Italian fill").toEqual([SHOWN_IN_ENGLISH]);
    });
});
