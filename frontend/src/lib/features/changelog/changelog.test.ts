/**
 * changelog.ts — parseChangelog unit tests (F12).
 *
 * The ChangelogModal renders the bundled CHANGELOG.md split into chapters:
 * Keep-a-Changelog `## [x.y.z] - date` sections. The parsing rules that matter:
 * the preamble (title, links, notes before the first chapter) is dropped, the
 * `Unreleased` chapter is kept even when empty, and empty *numbered* chapters
 * are dropped. `changelogChapters` itself parses the repo's real CHANGELOG.md
 * at module load — the last test pins that the shipped file actually parses.
 *
 * Lot CL (the localized CHANGELOG, frontend part) adds the second half of the
 * file: translations ship beside the English file as `CHANGELOG.<lang>.md`, one
 * lazily loaded chunk per language. The English file decides which chapters
 * exist and in which order; a translated chapter with content replaces the text
 * of the English chapter with the same version (the text between the brackets),
 * the version and the date always stay English, and every displayed chapter says
 * which language its text is in (`lang`). Pinned here: `baseLanguage`,
 * `mergeChapters`, `translationLoaders`, `createLocalizedChangelog` (fake loaders:
 * one load per language, a cache, and a failure that falls back to English
 * without being cached), and a guard on the real `CHANGELOG.<lang>.md` files —
 * vacuous while none exists, and still green when they land.
 *
 * Node env: pure string logic, no DOM. The real translated files are read here
 * through the module's lazy glob (jsdom refuses `?raw` imports from the repo root).
 */

import {readdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {describe, expect, it, vi} from 'vitest';
import {parseChangelog, splitSections, changelogChapters, CHANGELOG_REMOTE_URL, baseLanguage, mergeChapters, translationLoaders, createLocalizedChangelog, changelogTranslationLoaders, localizedChangelog, type ChangelogChapter} from './changelog';

const SAMPLE = `# Changelog

All notable changes to this project. Preamble noise.

## [Unreleased]

### Added
- something not yet released

## [1.2.0] - 2026-08-07

### Fixed
- a bug

## [1.1.0] - 2026-07-01

### Added
- a feature
- another one
`;

describe('parseChangelog (F12)', () => {
    it('splits chapters on `## [version] - date` headings, keeping version, date and body', () => {
        const chapters = parseChangelog(SAMPLE);

        const v120 = chapters.find((c) => c.version === '1.2.0');
        const v110 = chapters.find((c) => c.version === '1.1.0');
        expect(v120?.date).toBe('2026-08-07');
        expect(v110?.date).toBe('2026-07-01');
        expect(v120?.body).toContain('a bug');
        expect(v110?.body).toContain('another one');
        // The heading itself is not part of the body.
        expect(v120?.body).not.toContain('## [1.2.0]');
    });

    it('drops the preamble before the first chapter', () => {
        const chapters = parseChangelog(SAMPLE);

        expect(chapters.every((c) => !c.body.includes('Preamble noise'))).toBe(true);
        expect(chapters.some((c) => c.version === 'Changelog')).toBe(false);
    });

    it('keeps an Unreleased chapter with a date suffix even when its body is empty', () => {
        const raw = `# Changelog\n\n## [Unreleased] - 2026-09-01\n\n## [1.0.0] - 2026-01-01\n\n- shipped\n`;
        const chapters = parseChangelog(raw);

        const unreleased = chapters.find((c) => c.version.toLowerCase() === 'unreleased');
        expect(unreleased, 'Unreleased chapter dropped').toBeDefined();
    });

    // KNOWN GAP (reported, not fixed by the test batch): the module docstring says
    // unknown sections "e.g. `## [Unreleased]`" are kept, and the repo pledges Keep
    // Regression guard for the bug found during the feedback-consolidation batch:
    // Keep-a-Changelog's canonical `## [Unreleased]` heading has NO date, and the
    // original CHAPTER_HEADING required ` - <date>`, silently dropping it. The
    // heading regex now admits the bare form.
    it('keeps the canonical Keep-a-Changelog `## [Unreleased]` (no date)', () => {
        const raw = `# Changelog\n\n## [Unreleased]\n\n- coming soon\n\n## [1.0.0] - 2026-01-01\n\n- shipped\n`;
        const chapters = parseChangelog(raw);

        const unreleased = chapters.find((c) => c.version.toLowerCase() === 'unreleased');
        expect(unreleased, 'Unreleased chapter dropped').toBeDefined();
        expect(unreleased?.body).toContain('coming soon');
    });

    it('drops numbered chapters with an empty body', () => {
        const raw = `## [2.0.0] - 2026-02-02\n\n## [1.0.0] - 2026-01-01\n\n- shipped\n`;
        const chapters = parseChangelog(raw);

        expect(chapters.some((c) => c.version === '2.0.0')).toBe(false);
        expect(chapters.some((c) => c.version === '1.0.0')).toBe(true);
    });

    it('keeps chapters in document order (newest first as written)', () => {
        const chapters = parseChangelog(SAMPLE);
        const versions = chapters.map((c) => c.version);

        expect(versions.indexOf('Unreleased')).toBeLessThan(versions.indexOf('1.2.0'));
        expect(versions.indexOf('1.2.0')).toBeLessThan(versions.indexOf('1.1.0'));
    });

    it('returns [] for input without any chapter heading', () => {
        expect(parseChangelog('# Just a title\n\nsome text\n')).toEqual([]);
        expect(parseChangelog('')).toEqual([]);
    });

    it('populates `sections` on every chapter, and content partitions into (sub)section bodies', () => {
        const chapters = parseChangelog(SAMPLE);

        for (const chapter of chapters) {
            expect(Array.isArray(chapter.sections)).toBe(true);
            // Sections partition the body: no content line may sit outside a
            // section or one of its subsections (round-4: #### content lives in
            // the subsection's body, not the section's).
            const rebuilt = chapter.sections.map((s) => s.body + s.subsections.map((sub) => sub.body).join('')).join('');
            for (const line of chapter.body.split('\n')) {
                if (/^#{3,6}\s/.test(line)) continue; // headings become (sub)section titles
                if (line.trim().length === 0) continue; // inter-block blanks are formatting
                expect(rebuilt).toContain(line.trim());
            }
        }
        // The sample has ### sections in every chapter, so at least one titled section exists.
        expect(chapters.some((c) => c.sections.some((s) => s.title !== null))).toBe(true);
    });
});

describe('splitSections (round-3 F12)', () => {
    it('puts content before the first ### into a title-less intro section', () => {
        const sections = splitSections('Intro paragraph about the release.\n\n### Added\n- a feature\n');

        expect(sections).toHaveLength(2);
        expect(sections[0].title).toBeNull();
        expect(sections[0].body).toContain('Intro paragraph');
        expect(sections[1].title).toBe('Added');
        expect(sections[1].body).toContain('a feature');
        // The heading line itself is not part of the body.
        expect(sections[1].body).not.toContain('### Added');
    });

    it('splits multiple ### sections in order', () => {
        const body = '### Added\n- a\n\n### Fixed\n- b\n\n### Changed\n- c\n';
        const sections = splitSections(body);

        expect(sections.map((s) => s.title)).toEqual(['Added', 'Fixed', 'Changed']);
        expect(sections[1].body).toContain('- b');
        expect(sections[1].body).not.toContain('- a');
    });

    it('drops a section whose body is empty', () => {
        const body = '### Added\n- a\n\n### Empty\n\n### Fixed\n- b\n';
        const sections = splitSections(body);

        expect(sections.map((s) => s.title)).toEqual(['Added', 'Fixed']);
    });

    it('a body with no ### at all is a single intro section', () => {
        const sections = splitSections('Just prose.\nMore prose.\n');

        expect(sections).toHaveLength(1);
        expect(sections[0].title).toBeNull();
        expect(sections[0].body).toContain('Just prose.');
    });

    it('leading blank lines do not conjure an empty intro section', () => {
        const sections = splitSections('\n\n\n### Added\n- a\n');

        expect(sections).toHaveLength(1);
        expect(sections[0].title).toBe('Added');
    });

    it('an empty or heading-only body yields no sections', () => {
        expect(splitSections('')).toEqual([]);
        expect(splitSections('\n\n  \n')).toEqual([]);
        expect(splitSections('### OnlyAHeading\n')).toEqual([]);
    });

    // ---- round 4: #### subsections ----------------------------------------

    it('attaches #### subsections to the current ### section, headings excluded from bodies', () => {
        const sections = splitSections('### Added\n- a\n\n#### Deep dive\nDetails here.\n');

        expect(sections).toHaveLength(1);
        expect(sections[0].title).toBe('Added');
        expect(sections[0].body).toContain('- a');
        expect(sections[0].body).not.toContain('Details here'); // #### content lives in the subsection
        expect(sections[0].subsections).toHaveLength(1);
        expect(sections[0].subsections[0].title).toBe('Deep dive');
        expect(sections[0].subsections[0].body).toContain('Details here.');
        expect(sections[0].subsections[0].body).not.toContain('####');
    });

    it('a #### before any ### attaches to the intro section', () => {
        const sections = splitSections('Opening prose.\n\n#### Early note\nSub detail.\n');

        expect(sections).toHaveLength(1);
        expect(sections[0].title).toBeNull();
        expect(sections[0].body).toContain('Opening prose.');
        expect(sections[0].subsections).toHaveLength(1);
        expect(sections[0].subsections[0].title).toBe('Early note');
        expect(sections[0].subsections[0].body).toContain('Sub detail.');
    });

    it('a #### line is not mistaken for a ### section', () => {
        const sections = splitSections('#### Not a section\nSub body.\n');

        expect(sections.some((s) => s.title === 'Not a section')).toBe(false);
        expect(sections[0].subsections[0].title).toBe('Not a section');
    });

    it('drops a #### whose body is empty', () => {
        const sections = splitSections('### Added\n- a\n\n#### Empty\n\n#### Real\nSub body.\n');

        expect(sections[0].subsections.map((s) => s.title)).toEqual(['Real']);
    });

    it('keeps a ### section whose own body is empty when it has subsections', () => {
        const sections = splitSections('### Added\n#### Only sub\nSub body.\n');

        expect(sections).toHaveLength(1);
        expect(sections[0].title).toBe('Added');
        expect(sections[0].body.trim()).toBe('');
        expect(sections[0].subsections).toHaveLength(1);
    });

    it('drops the ### section too when its only #### is empty', () => {
        const sections = splitSections('### Real\n- a\n\n### Hollow\n#### Also hollow\n');

        expect(sections.map((s) => s.title)).toEqual(['Real']);
    });

    it('deeper headings (##### and beyond, up to 6) count as subsections', () => {
        const sections = splitSections('### Added\n- a\n\n##### Deeper\nDeep body.\n');

        expect(sections[0].subsections.map((s) => s.title)).toEqual(['Deeper']);
    });
});

describe('the bundled changelog (F12)', () => {
    it('parses the repo CHANGELOG.md: newest chapter first, every release dated', () => {
        // The modal renders this list: an unparsable shipped file means an empty
        // modal in production, which is exactly the failure this test exists to
        // catch before release.
        expect(changelogChapters.length).toBeGreaterThan(0);

        // The top chapter takes either shape: Keep-a-Changelog's undated
        // `## [Unreleased]`, or — while a release is being prepared — that
        // release's own `## [x.y.z] - date` chapter with an indicative date. So an
        // Unreleased chapter is optional, but there is at most one, it comes
        // first and it carries no date.
        const isUnreleased = (version: string) => version.toLowerCase() === 'unreleased';
        const unreleased = changelogChapters.filter((c) => isUnreleased(c.version));
        expect(unreleased.length, 'more than one Unreleased chapter').toBeLessThanOrEqual(1);
        for (const chapter of unreleased) {
            expect(changelogChapters.indexOf(chapter), 'Unreleased is not the first chapter').toBe(0);
            expect(chapter.date, 'Unreleased carries a date').toBe('');
        }

        // Every other chapter is a release: a plain X.Y.Z version (SemVer's
        // version core, so no leading zeros) and a YYYY-MM-DD date...
        const releases = changelogChapters.filter((c) => !isUnreleased(c.version));
        expect(releases.length, 'no release chapter').toBeGreaterThan(0);
        for (const {version, date} of releases) {
            expect(version, 'release version is not X.Y.Z').toMatch(/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/);
            expect(date, `release ${version} has no YYYY-MM-DD date`).toMatch(/^\d{4}-\d{2}-\d{2}$/);
        }

        // ...listed newest first, strictly, so a mistyped or misplaced chapter
        // breaks the order. Compared numerically part by part: 1.10.0 > 1.9.0.
        const compareSemver = (a: string, b: string) => {
            const [x, y] = [a, b].map((v) => v.split('.').map(Number));
            return x[0] - y[0] || x[1] - y[1] || x[2] - y[2];
        };
        for (let i = 1; i < releases.length; i++) {
            const [above, below] = [releases[i - 1].version, releases[i].version];
            expect(compareSemver(above, below), `${above} is listed above ${below} but is not newer`).toBeGreaterThan(0);
        }
    });

    it('points the remote link at the repository CHANGELOG.md', () => {
        expect(CHANGELOG_REMOTE_URL).toBe('https://github.com/Librefolio/LibreFolio/blob/main/CHANGELOG.md');
    });
});

// =========================================================================
// CL — the localized CHANGELOG: merge, loaders, cache, bundled translations
// =========================================================================

/**
 * English source of the CL tests, parsed by the real parser as the module does:
 * an Unreleased chapter WITH content (so it can be translated), then two releases.
 */
const ENGLISH_RAW = `# Changelog

## [Unreleased]

### Added
- an upcoming thing

## [1.2.0] - 2026-08-07

### Fixed
- a bug

## [1.1.0] - 2026-07-01

### Added
- a feature
`;

const ENGLISH = parseChangelog(ENGLISH_RAW);
const ENGLISH_VERSIONS = ['Unreleased', '1.2.0', '1.1.0'];

/**
 * An Italian file translating 1.2.0 only, behind a preamble of its own (dropped
 * like the English one). The Italian sentences are this test's data, not
 * catalogue copy.
 */
const ITALIAN_RAW = `# Registro delle modifiche

Preambolo tradotto.

## [1.2.0] - 2026-08-07

### Corretto
- un difetto
`;

/** The chapter of a version in a raw changelog — the CL fixtures name each one they use. */
function chapterOf(raw: string, version: string): ChangelogChapter {
    const chapter = parseChangelog(raw).find((c) => c.version === version);
    if (!chapter) throw new Error(`fixture has no [${version}] chapter`);
    return chapter;
}

/** The English chapters as displayed: the same chapters, each marked `en`. */
function shownInEnglish() {
    return ENGLISH.map((chapter) => ({...chapter, lang: 'en'}));
}

/** What the Italian UI shows for ENGLISH_RAW + ITALIAN_RAW: 1.2.0 in Italian under the English heading, the rest English. */
function shownInItalian() {
    const translated = chapterOf(ITALIAN_RAW, '1.2.0');
    return [
        {...chapterOf(ENGLISH_RAW, 'Unreleased'), lang: 'en'},
        {...chapterOf(ENGLISH_RAW, '1.2.0'), body: translated.body, sections: translated.sections, lang: 'it'},
        {...chapterOf(ENGLISH_RAW, '1.1.0'), lang: 'en'},
    ];
}

function deferred<T>() {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((resolvePromise) => {
        resolve = resolvePromise;
    });
    return {promise, resolve};
}

describe('baseLanguage (CL)', () => {
    it.each([
        ['it', 'it'],
        ['it-IT', 'it'],
        ['IT', 'it'],
        ['es', 'es'],
        ['en-US', 'en'],
        ['FR-ca', 'fr'],
    ])('%s → %s', (locale, expected) => {
        expect(baseLanguage(locale)).toBe(expected);
    });

    it.each([
        {locale: null, label: 'null'},
        {locale: undefined, label: 'undefined'},
        {locale: '', label: 'an empty string'},
    ])('$label → en (the English fallback)', ({locale}) => {
        expect(baseLanguage(locale)).toBe('en');
    });
});

describe('mergeChapters (CL)', () => {
    it('a translated chapter replaces the English body and sections, under the English version and date, marked with the language', () => {
        expect(
            ENGLISH.map((c) => c.version),
            'fixture: the CL English source',
        ).toEqual(ENGLISH_VERSIONS);
        const translated = chapterOf(ITALIAN_RAW, '1.2.0');

        const shown = mergeChapters(ENGLISH, parseChangelog(ITALIAN_RAW), 'it');

        expect(shown.find((c) => c.version === '1.2.0')).toEqual({version: '1.2.0', date: '2026-08-07', body: translated.body, sections: translated.sections, lang: 'it'});
    });

    it('a chapter the translation does not carry stays English, marked en — one displayed chapter per English chapter', () => {
        const shown = mergeChapters(ENGLISH, parseChangelog(ITALIAN_RAW), 'it');

        expect(shown).toEqual(shownInItalian());
        expect(shown.find((c) => c.version === 'Unreleased')).toEqual({...chapterOf(ENGLISH_RAW, 'Unreleased'), lang: 'en'});
        expect(shown.find((c) => c.version === '1.1.0')).toEqual({...chapterOf(ENGLISH_RAW, '1.1.0'), lang: 'en'});
    });

    it('matches the undated `## [Unreleased]` chapter by its version', () => {
        const raw = '## [Unreleased]\n\n### Aggiunto\n- una cosa in arrivo\n';
        const translated = chapterOf(raw, 'Unreleased');

        const shown = mergeChapters(ENGLISH, parseChangelog(raw), 'it');

        expect(shown.map((c) => c.version)).toEqual(ENGLISH_VERSIONS);
        expect(shown.find((c) => c.version === 'Unreleased')).toEqual({version: 'Unreleased', date: '', body: translated.body, sections: translated.sections, lang: 'it'});
    });

    it('a translated heading with another date still translates the chapter, under the English date (tolerant by decision)', () => {
        const raw = '## [1.2.0] - 2026-08-09\n\n### Corretto\n- un difetto\n';
        const translated = chapterOf(raw, '1.2.0');
        expect(translated.date, 'fixture: the translated heading carries another date').not.toBe(chapterOf(ENGLISH_RAW, '1.2.0').date);

        const shown = mergeChapters(ENGLISH, parseChangelog(raw), 'it');

        expect(shown.find((c) => c.version === '1.2.0')).toEqual({version: '1.2.0', date: '2026-08-07', body: translated.body, sections: translated.sections, lang: 'it'});
    });

    it('ignores a translated chapter with no English counterpart', () => {
        const raw = '## [9.9.9] - 2030-01-01\n\n### Aggiunto\n- dal futuro\n\n## [1.1.0] - 2026-07-01\n\n### Aggiunto\n- una funzionalità\n';

        const shown = mergeChapters(ENGLISH, parseChangelog(raw), 'it');

        expect(shown.map((c) => [c.version, c.lang])).toEqual([
            ['Unreleased', 'en'],
            ['1.2.0', 'en'],
            ['1.1.0', 'it'],
        ]);
        expect(shown.some((c) => c.body.includes('dal futuro'))).toBe(false);
    });

    it('a translated chapter without any section counts as missing: the empty Unreleased, a heading-only release', () => {
        const raw = '## [Unreleased]\n\n## [1.2.0] - 2026-08-07\n\n### Corretto\n\n## [1.1.0] - 2026-07-01\n\n### Aggiunto\n- una funzionalità\n';
        const translated = parseChangelog(raw);
        // Precondition: the parser keeps both chapters, and neither has a section.
        expect(translated.find((c) => c.version === 'Unreleased')?.sections).toEqual([]);
        expect(translated.find((c) => c.version === '1.2.0')?.sections).toEqual([]);

        const shown = mergeChapters(ENGLISH, translated, 'it');

        expect(shown).toEqual([
            {...chapterOf(ENGLISH_RAW, 'Unreleased'), lang: 'en'},
            {...chapterOf(ENGLISH_RAW, '1.2.0'), lang: 'en'},
            {...chapterOf(ENGLISH_RAW, '1.1.0'), body: chapterOf(raw, '1.1.0').body, sections: chapterOf(raw, '1.1.0').sections, lang: 'it'},
        ]);
    });

    it('keeps the English order when the translation lists its chapters in another one', () => {
        const raw = '## [1.1.0] - 2026-07-01\n\n### Aggiunto\n- una funzionalità\n\n## [1.2.0] - 2026-08-07\n\n### Corretto\n- un difetto\n';

        const shown = mergeChapters(ENGLISH, parseChangelog(raw), 'it');

        expect(shown.map((c) => [c.version, c.lang])).toEqual([
            ['Unreleased', 'en'],
            ['1.2.0', 'it'],
            ['1.1.0', 'it'],
        ]);
        expect(shown.find((c) => c.version === '1.2.0')?.body).toBe(chapterOf(raw, '1.2.0').body);
        expect(shown.find((c) => c.version === '1.1.0')?.body).toBe(chapterOf(raw, '1.1.0').body);
    });

    it('in English the translation is ignored: every chapter English, marked en', () => {
        const raw = '## [1.2.0] - 2026-08-07\n\n### Fixed\n- some other text\n';

        expect(mergeChapters(ENGLISH, parseChangelog(raw), 'en')).toEqual(shownInEnglish());
    });

    it('a version the translation repeats takes its first chapter', () => {
        const raw = '## [1.2.0] - 2026-08-07\n\n### Corretto\n- la prima traduzione\n\n## [1.2.0] - 2026-08-07\n\n### Corretto\n- la seconda traduzione\n';
        const [first, second] = parseChangelog(raw);
        expect([first.body, second.body], 'fixture: two different chapters for one version').toEqual([expect.stringContaining('la prima'), expect.stringContaining('la seconda')]);

        const shown = mergeChapters(ENGLISH, parseChangelog(raw), 'it');

        expect(shown.map((c) => c.version)).toEqual(ENGLISH_VERSIONS);
        expect(shown.find((c) => c.version === '1.2.0')).toEqual({...chapterOf(ENGLISH_RAW, '1.2.0'), body: first.body, sections: first.sections, lang: 'it'});
    });

    it('leaves both inputs untouched', () => {
        const english = structuredClone(ENGLISH);
        const translated = parseChangelog(ITALIAN_RAW);
        const before = structuredClone({english, translated});

        mergeChapters(english, translated, 'it');

        expect({english, translated}).toEqual(before);
    });
});

describe('translationLoaders (CL)', () => {
    it('maps the glob keys ending in CHANGELOG.<two lower-case letters>.md to their language, ignoring English and every other name', async () => {
        const italian = vi.fn(async () => ITALIAN_RAW);
        const french = vi.fn(async () => '## [1.2.0] - 2026-08-07\n\n### Corrigé\n- un bogue\n');
        const ignored = vi.fn(async () => ENGLISH_RAW);

        const loaders = translationLoaders({
            '../../../../../CHANGELOG.it.md': italian,
            '../../../../../CHANGELOG.fr.md': french,
            '../../../../../CHANGELOG.en.md': ignored,
            '../../../../../CHANGELOG.md': ignored,
            '../../../../../CHANGELOG.original.md': ignored,
            '../../../../../CHANGELOG.IT.md': ignored,
        });

        expect(loaders).toBeInstanceOf(Map);
        expect([...loaders.keys()].sort()).toEqual(['fr', 'it']);
        // Mapping fetches nothing: a translation is downloaded only when its language asks for it.
        expect(italian).not.toHaveBeenCalled();
        expect(french).not.toHaveBeenCalled();

        await expect(loaders.get('it')?.()).resolves.toBe(ITALIAN_RAW);
        await expect(loaders.get('fr')?.()).resolves.toContain('Corrigé');
        expect(italian).toHaveBeenCalledTimes(1);
        expect(french).toHaveBeenCalledTimes(1);
        expect(ignored).not.toHaveBeenCalled();
    });

    it('an empty glob (no translated file yet) maps no language', () => {
        expect(translationLoaders({}).size).toBe(0);
    });
});

describe('createLocalizedChangelog (CL)', () => {
    /** A localized changelog over the CL English source whose only translation is Italian, served by `loader`. */
    function italianOnly(loader: () => Promise<string>) {
        return createLocalizedChangelog(ENGLISH, new Map([['it', loader]]));
    }

    it('English, no locale and a language without a file give the English list at once, and load nothing', async () => {
        const loader = vi.fn(async () => ITALIAN_RAW);
        const changelog = italianOnly(loader);

        for (const locale of ['en', 'en-GB', null, undefined, '', 'de', 'fr']) {
            expect(changelog.peek(locale), `peek(${String(locale)})`).toEqual(shownInEnglish());
            await expect(changelog.load(locale), `load(${String(locale)})`).resolves.toEqual(shownInEnglish());
        }
        expect(loader).not.toHaveBeenCalled();
    });

    it('a translated language peeks undefined until its file has loaded — and peeking loads nothing', () => {
        const loader = vi.fn(async () => ITALIAN_RAW);
        const changelog = italianOnly(loader);

        expect(changelog.peek('it')).toBeUndefined();
        expect(changelog.peek('it-IT')).toBeUndefined();
        expect(loader).not.toHaveBeenCalled();
    });

    it('load parses and merges the file of the language, and peek then answers from the cache', async () => {
        const loader = vi.fn(async () => ITALIAN_RAW);
        const changelog = italianOnly(loader);

        await expect(changelog.load('it')).resolves.toEqual(shownInItalian());

        expect(changelog.peek('it')).toEqual(shownInItalian());
        expect(loader).toHaveBeenCalledTimes(1);
    });

    it('two concurrent loads share one loader call, and later loads reuse the cache', async () => {
        const text = deferred<string>();
        const loader = vi.fn(() => text.promise);
        const changelog = italianOnly(loader);

        const first = changelog.load('it');
        const second = changelog.load('it-IT');
        text.resolve(ITALIAN_RAW);

        await expect(Promise.all([first, second])).resolves.toEqual([shownInItalian(), shownInItalian()]);
        await expect(changelog.load('it')).resolves.toEqual(shownInItalian());
        expect(loader).toHaveBeenCalledTimes(1);
    });

    it('a failing loader resolves to the English list — never a rejection — caches nothing, and the next load calls it again', async () => {
        const loader = vi.fn<() => Promise<string>>().mockRejectedValueOnce(new Error('translation chunk failed')).mockResolvedValueOnce(ITALIAN_RAW);
        const changelog = italianOnly(loader);

        await expect(changelog.load('it')).resolves.toEqual(shownInEnglish());
        expect(changelog.peek('it'), 'a failure must not be cached').toBeUndefined();

        await expect(changelog.load('it')).resolves.toEqual(shownInItalian());
        expect(loader).toHaveBeenCalledTimes(2);
        expect(changelog.peek('it')).toEqual(shownInItalian());
    });

    it('normalizes the locale: it-IT loads the it file, and the cache answers it, IT and it-CH', async () => {
        const loader = vi.fn(async () => ITALIAN_RAW);
        const changelog = italianOnly(loader);

        await expect(changelog.load('it-IT')).resolves.toEqual(shownInItalian());

        expect(loader).toHaveBeenCalledTimes(1);
        for (const locale of ['it', 'IT', 'it-CH']) expect(changelog.peek(locale), locale).toEqual(shownInItalian());
    });
});

// The guard on the real translated files. Today there is none, so the loops below
// are empty — but the first test is their positive control: an empty loader map
// beside a CHANGELOG.<lang>.md on disk (a glob reading the wrong directory) is red
// there instead of a guard that passes because it read nothing. Only versions are
// compared, never heading lines: the dates belong to CHANGELOG.md.
describe('the bundled translations (CL)', () => {
    it('the module loads exactly the CHANGELOG.<lang>.md files of the repository root', () => {
        const repoRoot = fileURLToPath(new URL('../../../../../', import.meta.url));
        const onDisk = readdirSync(repoRoot)
            .flatMap((name) => /^CHANGELOG\.([a-z]{2})\.md$/.exec(name)?.[1] ?? [])
            .filter((lang) => lang !== 'en')
            .sort();

        expect(changelogTranslationLoaders).toBeInstanceOf(Map);
        expect([...changelogTranslationLoaders.keys()].sort()).toEqual(onDisk);
    });

    it('every bundled translation: known versions only, in English order, never a copy of the English text', async () => {
        const englishIndex = new Map(changelogChapters.map((chapter, index) => [chapter.version, index]));

        for (const [lang, loader] of changelogTranslationLoaders) {
            const file = `CHANGELOG.${lang}.md`;
            expect(lang, `${file}: a language is two lower-case letters`).toMatch(/^[a-z]{2}$/);
            expect(lang, `${file}: English is CHANGELOG.md itself`).not.toBe('en');

            let previous = -1;
            for (const chapter of parseChangelog(await loader())) {
                const index = englishIndex.get(chapter.version) ?? -1;
                expect(index, `${file}: [${chapter.version}] has no chapter in CHANGELOG.md`).toBeGreaterThanOrEqual(0);
                expect(index, `${file}: [${chapter.version}] breaks the English order, or repeats a version`).toBeGreaterThan(previous);
                previous = index;
                // A chapter without a section is shown in English anyway: nothing to compare.
                if (chapter.sections.length > 0) {
                    expect(chapter.body.trim(), `${file}: [${chapter.version}] is the English text, not a translation`).not.toBe(changelogChapters[index].body.trim());
                }
            }
        }
    });

    it('localizedChangelog serves the bundled chapters: English at once, and per bundled language one chapter per English chapter', async () => {
        const englishShown = changelogChapters.map((chapter) => ({...chapter, lang: 'en'}));
        expect(localizedChangelog.peek('en')).toEqual(englishShown);
        for (const lang of ['it', 'fr', 'es'].filter((candidate) => !changelogTranslationLoaders.has(candidate))) {
            expect(localizedChangelog.peek(lang), `no CHANGELOG.${lang}.md: English at once`).toEqual(englishShown);
        }

        for (const [lang, loader] of changelogTranslationLoaders) {
            // The chapters the file translates, by the merge rule: per version the first
            // chapter counts, and only when it has a section.
            const firstByVersion = new Map<string, ChangelogChapter>();
            for (const chapter of parseChangelog(await loader())) if (!firstByVersion.has(chapter.version)) firstByVersion.set(chapter.version, chapter);
            const translatedVersions = changelogChapters.filter((chapter) => (firstByVersion.get(chapter.version)?.sections.length ?? 0) > 0).map((chapter) => chapter.version);

            const shown = await localizedChangelog.load(lang);

            expect(
                shown.map(({version, date}) => ({version, date})),
                `${lang}: versions and dates come from CHANGELOG.md`,
            ).toEqual(changelogChapters.map(({version, date}) => ({version, date})));
            expect(
                shown.filter((chapter) => chapter.lang === lang).map((chapter) => chapter.version),
                `${lang}: the chapters shown in ${lang}`,
            ).toEqual(translatedVersions);
            expect(
                shown.filter((chapter) => chapter.lang !== lang && chapter.lang !== 'en'),
                `${lang}: a chapter is in ${lang} or in English`,
            ).toEqual([]);
            expect(localizedChangelog.peek(lang), `${lang}: cached after the load`).toEqual(shown);
        }
    });
});
