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
 * M-23 adds French spacing (the section at the end): the French chapters are
 * typeset with the rules of the docs' MkDocs hook `mkdocs_src/hooks/fr_typography.py`,
 * on their Markdown and never inside code or URLs; every other text as written.
 *
 * Node env: pure string logic, no DOM. The real translated files are read here
 * through the module's lazy glob (jsdom refuses `?raw` imports from the repo root).
 */

import {readdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {describe, expect, it, vi} from 'vitest';
import {parseChangelog, splitSections, changelogChapters, CHANGELOG_REMOTE_URL, baseLanguage, mergeChapters, translationLoaders, createLocalizedChangelog, changelogTranslationLoaders, localizedChangelog, typesetFrench, typesetFrenchMarkdown, type ChangelogChapter} from './changelog';

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

// =========================================================================
// M-23 — French spacing: the docs' typography hook, applied to the changelog
// =========================================================================

/**
 * French keeps a sign with the word before it: a no-break space before `:` `;` `?` `!` and `%`, inside « », and
 * between the groups of a number. The French docs get it at build time from the MkDocs hook
 * `mkdocs_src/hooks/fr_typography.py` (`typeset()`, on the rendered HTML). The modal renders CHANGELOG.fr.md without
 * MkDocs, so changelog.ts typesets the French chapters itself, with the same rules, on their Markdown, before
 * parseChangelog. The translated files keep their plain spaces.
 *
 * `typesetFrench` is the hook's `typeset` on a run of text: its cases are the `typeset()` cases of
 * backend/test_scripts/test_utilities/test_docs_fr_typography.py, ported one for one (same inputs, outputs and ids);
 * the HTML-walker, TOC and navigation cases stay there. `typesetFrenchMarkdown` applies it to the prose of a Markdown
 * text. `createLocalizedChangelog` shows the French chapters typeset, and every other text as written.
 *
 * Expected texts spell their spaces with NBSP and NNBSP, and the assertions compare `spelled` values, so a failure
 * prints {NBSP}, {NNBSP} or {U+XXXX} where a space is not the plain one.
 */

const NBSP = '\u00a0'; // before the colon, inside « »
const NNBSP = '\u202f'; // before ; ? ! %, a currency symbol after a number, between thousand groups

const SPACE_NAMES = new Map([
    [NBSP, '{NBSP}'],
    [NNBSP, '{NNBSP}'],
]);

/**
 * `value` with every whitespace but the space and the newline spelled out in each string it holds, arrays and
 * objects walked: {NBSP}, {NNBSP}, any other as {U+XXXX}. One to one on these fixtures (none holds a spelled name),
 * so two spelled values are equal exactly when the values are.
 */
function spelled(value: unknown): unknown {
    if (typeof value === 'string') return value.replace(/[^\S \n]/g, (space) => SPACE_NAMES.get(space) ?? `{U+${(space.codePointAt(0) ?? 0).toString(16).toUpperCase().padStart(4, '0')}}`);
    if (Array.isArray(value)) return value.map((item) => spelled(item));
    if (value !== null && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, spelled(item)]));
    return value;
}

/** Code fences, kept out of the template literals they would end. */
const [TICKS, TICKS4, TICKS5, TILDES] = ['```', '````', '`````', '~~~'];

describe('typesetFrench (M-23): the rules of the hook, each with its exact code point', () => {
    it.each([
        {id: 'a-space', text: 'Remarque : texte', expected: `Remarque${NBSP}: texte`},
        {id: 'several-spaces', text: 'Remarque   : texte', expected: `Remarque${NBSP}: texte`},
        {id: 'a-newline', text: 'Remarque\n: texte', expected: `Remarque${NBSP}: texte`},
        {id: 'mixed-whitespace', text: 'Remarque \t\r\n : texte', expected: `Remarque${NBSP}: texte`},
        {id: 'at-the-end-of-the-text', text: 'Texte :', expected: `Texte${NBSP}:`},
        {id: 'at-the-start-of-the-text', text: ' : le texte', expected: `${NBSP}: le texte`},
    ])('whitespace before a colon becomes U+00A0 — $id', ({text, expected}) => {
        expect(spelled(typesetFrench(text))).toBe(spelled(expected));
    });

    it.each([
        {id: 'semicolon', text: 'Prix ; quantité', expected: `Prix${NNBSP}; quantité`},
        {id: 'question-mark', text: 'Vraiment ?', expected: `Vraiment${NNBSP}?`},
        {id: 'exclamation-mark', text: 'Attention !', expected: `Attention${NNBSP}!`},
        {id: 'question-then-exclamation-mark', text: 'Vraiment ?!', expected: `Vraiment${NNBSP}?!`},
        {id: 'one-after-the-other', text: 'Quoi ? ! ;', expected: `Quoi${NNBSP}?${NNBSP}!${NNBSP};`},
        {id: 'spaces-and-a-newline', text: 'Vraiment  \n ?', expected: `Vraiment${NNBSP}?`},
        {id: 'at-the-start-of-the-text', text: ' ? suite', expected: `${NNBSP}? suite`},
    ])('whitespace before a semicolon, a question or an exclamation mark becomes U+202F — $id', ({text, expected}) => {
        expect(spelled(typesetFrench(text))).toBe(spelled(expected));
    });

    it.each([
        {id: 'after-a-number', text: '50 %', expected: `50${NNBSP}%`},
        {id: 'after-a-decimal', text: 'un taux de 12,5 % par an', expected: `un taux de 12,5${NNBSP}% par an`},
        {id: 'after-a-word', text: 'cent %', expected: `cent${NNBSP}%`},
        {id: 'a-newline-and-spaces', text: '50\n  %', expected: `50${NNBSP}%`},
        {id: 'at-the-start-of-the-text', text: ' % des parts', expected: `${NNBSP}% des parts`},
    ])('whitespace before a percent sign becomes U+202F, whatever stands before it — $id', ({text, expected}) => {
        expect(spelled(typesetFrench(text))).toBe(spelled(expected));
    });

    it.each([
        {id: 'euro', text: '10 €', expected: `10${NNBSP}€`},
        {id: 'dollar', text: '10 $', expected: `10${NNBSP}$`},
        {id: 'pound', text: '10 £', expected: `10${NNBSP}£`},
        {id: 'yen', text: '10 ¥', expected: `10${NNBSP}¥`},
        {id: 'after-a-decimal-several-spaces', text: '1 234,56  $', expected: `1${NNBSP}234,56${NNBSP}$`},
    ])('whitespace before a currency symbol after a digit becomes U+202F — $id', ({text, expected}) => {
        expect(spelled(typesetFrench(text))).toBe(spelled(expected));
    });

    it.each([
        {id: 'a-space', text: '« Bonjour »', expected: `«${NBSP}Bonjour${NBSP}»`},
        {id: 'several-spaces', text: '«   Bonjour   »', expected: `«${NBSP}Bonjour${NBSP}»`},
        {id: 'a-newline', text: '«\nBonjour\n»', expected: `«${NBSP}Bonjour${NBSP}»`},
    ])('whitespace inside guillemets becomes U+00A0 — $id', ({text, expected}) => {
        expect(spelled(typesetFrench(text))).toBe(spelled(expected));
    });

    it.each([
        {id: 'two-groups', text: '28 398', expected: `28${NNBSP}398`},
        {id: 'three-groups', text: '1 000 000', expected: `1${NNBSP}000${NNBSP}000`},
        {id: 'three-digit-head', text: '999 999 lignes', expected: `999${NNBSP}999 lignes`},
        {id: 'two-numbers', text: 'de 10 000 à 20 000', expected: `de 10${NNBSP}000 à 20${NNBSP}000`},
        {id: 'before-a-currency', text: 'vaut 28 398 €', expected: `vaut 28${NNBSP}398${NNBSP}€`},
        {id: 'signed-in-brackets', text: '(-1 000)', expected: `(-1${NNBSP}000)`},
    ])('the space between thousand groups becomes U+202F — $id', ({text, expected}) => {
        expect(spelled(typesetFrench(text))).toBe(spelled(expected));
    });

    it.each([
        {id: 'closing-bracket', text: '(vraiment ?)', expected: `(vraiment${NNBSP}?)`},
        {id: 'closing-square-bracket', text: '[sic !]', expected: `[sic${NNBSP}!]`},
        {id: 'closing-guillemet', text: '« Quoi ?»', expected: `«${NBSP}Quoi${NNBSP}?»`},
        {id: 'closing-curly-quote', text: '“Vraiment ?”', expected: `“Vraiment${NNBSP}?”`},
        {id: 'straight-double-quote', text: '"Non !"', expected: `"Non${NNBSP}!"`},
        {id: 'straight-single-quote', text: "'Oui ?'", expected: `'Oui${NNBSP}?'`},
        {id: 'comma', text: 'Quoi ?, dit-il', expected: `Quoi${NNBSP}?, dit-il`},
        {id: 'ellipsis', text: 'Ah !…', expected: `Ah${NNBSP}!…`},
        {id: 'named-entity', text: 'Quoi ?&nbsp;Oui', expected: `Quoi${NNBSP}?&nbsp;Oui`},
        {id: 'numeric-entity', text: 'Prix :&#160;10', expected: `Prix${NBSP}:&#160;10`},
    ])('a sign followed by closing punctuation or an entity counts — $id', ({text, expected}) => {
        expect(spelled(typesetFrench(text))).toBe(spelled(expected));
    });
});

describe('typesetFrench (M-23): what the hook leaves alone', () => {
    it.each([
        {id: 'english-colon', text: 'Next: Select'},
        {id: 'ratio', text: '16:9'},
        {id: 'url', text: 'https://example.org/a:b'},
        {id: 'guillemets', text: '«sans»'},
        {id: 'question-exclamation-semicolon', text: 'Quoi? Attention! a;b'},
        {id: 'percent-and-currency', text: '50% et 10€'},
        {id: 'number', text: '28398 lignes'},
    ])('no space is inserted — $id', ({text}) => {
        expect(spelled(typesetFrench(text))).toBe(spelled(text));
    });

    it.each([
        {id: 'colon-before-a-letter', text: 'a :b'},
        {id: 'colon-before-a-digit', text: 'ratio 16 :9'},
        {id: 'question-mark-before-a-letter', text: 'le paramètre ?lang=fr'},
        {id: 'exclamation-mark-before-a-letter', text: 'color: red !important'},
        {id: 'semicolon-before-a-letter', text: 'x ;y'},
    ])('a sign followed by anything else is not a sign — $id', ({text}) => {
        expect(spelled(typesetFrench(text))).toBe(spelled(text));
    });

    it.each([
        {id: 'nbsp-entity-before-a-colon', text: 'Remarque&nbsp;: texte'},
        {id: 'entities-before-and-inside', text: 'Quoi&#8239;? «&nbsp;x&nbsp;»'},
        {id: 'already-non-breaking', text: `Remarque${NBSP}: Quoi${NNBSP}? «${NBSP}x${NBSP}» 28${NNBSP}398`},
        {id: 'a-thin-space-is-not-plain-whitespace', text: 'Remarque\u2009: texte'},
    ])('entities and spaces that are not plain whitespace are left alone — $id', ({text}) => {
        expect(spelled(typesetFrench(text))).toBe(spelled(text));
    });

    it.each([
        {id: 'a-percent-sign-inside-a-url-is-left-alone', text: 'Voir https://example.org/r%C3%A9sum%C3%A9?q=50%25&x=1 pour 50 %', expected: `Voir https://example.org/r%C3%A9sum%C3%A9?q=50%25&x=1 pour 50${NNBSP}%`},
        {id: 'a-currency-symbol-not-after-a-digit-is-left-alone', text: 'en € ou en $, 10 €', expected: `en € ou en $, 10${NNBSP}€`},
        {id: 'a-year-is-not-joined-to-the-number-after-it', text: 'en 2024 120 000 lignes', expected: `en 2024 120${NNBSP}000 lignes`},
        {id: 'a-decimal-tail-is-left-alone', text: '1 000,50', expected: `1${NNBSP}000,50`},
        {id: 'a-second-grouping-style-is-left-alone', text: '1 000.500', expected: '1 000.500'},
    ])('$id', ({text, expected}) => {
        expect(spelled(typesetFrench(text))).toBe(spelled(expected));
    });
});

/**
 * Markdown shaped like a chapter of CHANGELOG.fr.md: a heading, nested list items, emphasis, code holding
 * placeholders, a fenced block, a quote and a table.
 */
const FRENCH_MARKDOWN = `### ✨ Ajouté : nouveautés

- **Choisissez l'indice de référence là où il est utilisé.** En haut de *Combien chacun a-t-il payé pour son risque ?* ; il peut être l'un des actifs.
  - Sous-point : \`a : b ; c ?\` puis 28 398 € ; 12,5 % de plus !
- La carte *Mot de passe oublié ?* affiche des commandes : \`docker compose exec librefolio python dev.py user reset <username> <new_password>\` pour Docker.

${TICKS}
x : y ; « z » 1 000 €
${TICKS}

> Remarque : « important » ?

| Colonne : A | Valeur ? |
| --- | --- |
| Prix | 1 234,56 $ |
`;

/** FRENCH_MARKDOWN typeset by hand. */
const FRENCH_MARKDOWN_TYPESET = `### ✨ Ajouté${NBSP}: nouveautés

- **Choisissez l'indice de référence là où il est utilisé.** En haut de *Combien chacun a-t-il payé pour son risque${NNBSP}?*${NNBSP}; il peut être l'un des actifs.
  - Sous-point${NBSP}: \`a : b ; c ?\` puis 28${NNBSP}398${NNBSP}€${NNBSP}; 12,5${NNBSP}% de plus${NNBSP}!
- La carte *Mot de passe oublié${NNBSP}?* affiche des commandes${NBSP}: \`docker compose exec librefolio python dev.py user reset <username> <new_password>\` pour Docker.

${TICKS}
x : y ; « z » 1 000 €
${TICKS}

> Remarque${NBSP}: «${NBSP}important${NBSP}»${NNBSP}?

| Colonne${NBSP}: A | Valeur${NNBSP}? |
| --- | --- |
| Prix | 1${NNBSP}234,56${NNBSP}$ |
`;

describe('typesetFrenchMarkdown (M-23): the rules of the hook on the prose of a Markdown text', () => {
    it('typesets the prose of every block of a chapter — heading, list items, quote, table — and leaves its code as written; a second pass changes nothing', () => {
        const once = typesetFrenchMarkdown(FRENCH_MARKDOWN);

        expect(spelled(once)).toBe(spelled(FRENCH_MARKDOWN_TYPESET));
        expect(spelled(typesetFrenchMarkdown(once)), 'a second pass').toBe(spelled(once));
    });

    // The hook's runs of text end at a tag; in Markdown an emphasis or code marker, a link or a tag ends them.
    it.each([
        {id: 'italic-question-mark', text: '*Mot de passe oublié ?*', expected: `*Mot de passe oublié${NNBSP}?*`},
        {id: 'bold-colon', text: '**Total :**', expected: `**Total${NBSP}:**`},
        {id: 'underscore-exclamation-mark', text: '_Vraiment !_', expected: `_Vraiment${NNBSP}!_`},
        {id: 'strikethrough-semicolon', text: '~~Obsolète ;~~', expected: `~~Obsolète${NNBSP};~~`},
        {id: 'code-span', text: 'Lancez :`ls`', expected: `Lancez${NBSP}:\`ls\``},
        {id: 'link', text: 'Voir :[la page](https://ex.org/)', expected: `Voir${NBSP}:[la page](https://ex.org/)`},
        {id: 'tag', text: 'Attention !<br>la suite', expected: `Attention${NNBSP}!<br>la suite`},
    ])('a sign followed by a marker counts, as if it ended the text — $id', ({text, expected}) => {
        expect(spelled(typesetFrenchMarkdown(text))).toBe(spelled(expected));
    });

    it.each([
        {id: 'guillemets-around-code', text: '« `code` »', expected: `«${NBSP}\`code\`${NBSP}»`},
        {id: 'colon-after-code', text: 'Texte `x` :', expected: `Texte \`x\`${NBSP}:`},
        {id: 'percent-after-bold', text: '**50** %', expected: `**50**${NNBSP}%`},
        {id: 'colon-after-bold', text: '**Remarque** : le texte', expected: `**Remarque**${NBSP}: le texte`},
        {id: 'semicolon-after-code', text: '`./dev.py` ; puis', expected: `\`./dev.py\`${NNBSP}; puis`},
        {id: 'colon-after-a-link', text: "[l'aide](https://ex.org/aide) : voir", expected: `[l'aide](https://ex.org/aide)${NBSP}: voir`},
        {id: 'guillemets-around-a-link', text: '« [la page](https://ex.org/) »', expected: `«${NBSP}[la page](https://ex.org/)${NBSP}»`},
        {id: 'colon-after-kbd', text: '<kbd>Ctrl</kbd> + <kbd>S</kbd> : enregistrer', expected: `<kbd>Ctrl</kbd> + <kbd>S</kbd>${NBSP}: enregistrer`},
    ])('the rules apply across code, emphasis, links and tags, as the hook applies them across tags — $id', ({text, expected}) => {
        expect(spelled(typesetFrenchMarkdown(text))).toBe(spelled(expected));
    });

    // The text of a link is visible in HTML, so the hook typesets it; the alt text of an image is an attribute, so it does not.
    it('the text of a link is prose, typeset; the alt text of an image is not', () => {
        expect(spelled(typesetFrenchMarkdown('[Mot de passe oublié ?](https://ex.org/reset), [« Total : 10 € »](https://ex.org/total) et ![« Total : 10 € »](https://ex.org/total.png)'))).toBe(
            spelled(`[Mot de passe oublié${NNBSP}?](https://ex.org/reset), [«${NBSP}Total${NBSP}: 10${NNBSP}€${NBSP}»](https://ex.org/total) et ![« Total : 10 € »](https://ex.org/total.png)`),
        );
    });
});

describe('typesetFrenchMarkdown (M-23): what it leaves byte for byte', () => {
    it.each([
        {id: 'backticks', text: `Avant :\n\n${TICKS}\nx : y ; z ? « a » 1 000 €\n${TICKS}\n\nAprès !`, expected: `Avant${NBSP}:\n\n${TICKS}\nx : y ; z ? « a » 1 000 €\n${TICKS}\n\nAprès${NNBSP}!`},
        {id: 'tildes', text: `Avant :\n\n${TILDES}\nx : y ; z ? « a » 1 000 €\n${TILDES}\n\nAprès !`, expected: `Avant${NBSP}:\n\n${TILDES}\nx : y ; z ? « a » 1 000 €\n${TILDES}\n\nAprès${NNBSP}!`},
        {id: 'its-fence-lines-info-string-included', text: `${TICKS}python title="Exemple : code ?"\nprint("Total : 50 %")  # vraiment ?\n${TICKS}\nFin :`, expected: `${TICKS}python title="Exemple : code ?"\nprint("Total : 50 %")  # vraiment ?\n${TICKS}\nFin${NBSP}:`},
        {id: 'indented-by-three-spaces', text: `- Étape :\n\n   ${TICKS}\n   a : b\n   ${TICKS}\n\nFin :`, expected: `- Étape${NBSP}:\n\n   ${TICKS}\n   a : b\n   ${TICKS}\n\nFin${NBSP}:`},
        // A fence line may follow any indent: in a nested list item it sits 4 spaces in, and marked renders it as code.
        {id: 'indented-by-four-spaces-in-a-nested-list-item', text: `- Étape :\n  - Sous-étape :\n\n    ${TICKS}\n    a : b ; « c » 1 000 €\n    ${TICKS}\n\nFin !`, expected: `- Étape${NBSP}:\n  - Sous-étape${NBSP}:\n\n    ${TICKS}\n    a : b ; « c » 1 000 €\n    ${TICKS}\n\nFin${NNBSP}!`},
        {id: 'a-shorter-fence-does-not-close-it', text: `${TICKS4}\n${TICKS}\na : b\n${TICKS}\n${TICKS4}\nFin :`, expected: `${TICKS4}\n${TICKS}\na : b\n${TICKS}\n${TICKS4}\nFin${NBSP}:`},
        {id: 'a-fence-of-the-other-character-does-not-close-it', text: `${TICKS}\na : b\n${TILDES}\nc : d\n${TICKS}\nFin :`, expected: `${TICKS}\na : b\n${TILDES}\nc : d\n${TICKS}\nFin${NBSP}:`},
        {id: 'a-longer-fence-closes-it', text: `${TICKS}\na : b\n${TICKS5}\nFin :`, expected: `${TICKS}\na : b\n${TICKS5}\nFin${NBSP}:`},
        {id: 'unclosed-it-runs-to-the-end', text: `Avant :\n\n${TICKS}\na : b\n\nc ; d ?`, expected: `Avant${NBSP}:\n\n${TICKS}\na : b\n\nc ; d ?`},
    ])('a fenced code block, its fence lines included — $id', ({text, expected}) => {
        expect(spelled(typesetFrenchMarkdown(text))).toBe(spelled(expected));
    });

    it.each([
        {id: 'single-backticks', text: 'Tapez `a : b ; c ? « d » 1 000 €` puis validez :', expected: `Tapez \`a : b ; c ? « d » 1 000 €\` puis validez${NBSP}:`},
        // Both below tell a run of N closed by a run of exactly N from backticks paired as they come, which would
        // leave ` : ok` and ` : b` outside any span.
        {id: 'double-backticks-around-single-ones', text: 'Tapez ``echo `date` : ok`` puis validez :', expected: 'Tapez ``echo `date` : ok`` puis validez' + NBSP + ':'},
        {id: 'closed-by-a-run-of-exactly-as-many', text: 'Tapez `a``` : b` ici :', expected: 'Tapez `a``` : b` ici' + NBSP + ':'},
        {id: 'an-unmatched-run-is-literal-text', text: 'Un ` isolé : voilà', expected: `Un \` isolé${NBSP}: voilà`},
        {id: 'a-span-after-an-unmatched-run', text: '``a `b : c` d :', expected: '``a `b : c` d' + NBSP + ':'},
        // A span never crosses into the next bullet: paired across the line break, the backtick of the first line
        // would swallow `Texte :` of the second.
        {id: 'never-into-the-next-bullet-line', text: '- Un accent grave ` isolé\n- Texte : voir `code`', expected: `- Un accent grave \` isolé\n- Texte${NBSP}: voir \`code\``},
    ])('an inline code span — $id', ({text, expected}) => {
        expect(spelled(typesetFrenchMarkdown(text))).toBe(spelled(expected));
    });

    it.each([
        {id: 'a-destination-and-its-title', text: 'Voir [ici](https://ex.org/a?b=1 "Voir : là") ; merci !', expected: `Voir [ici](https://ex.org/a?b=1 "Voir : là")${NNBSP}; merci${NNBSP}!`},
        {id: 'nested-parentheses', text: 'Voir [l\'espace](https://fr.wikipedia.org/wiki/Espace_(typographie) "Espace : typo") : ici', expected: `Voir [l'espace](https://fr.wikipedia.org/wiki/Espace_(typographie) "Espace : typo")${NBSP}: ici`},
        {id: 'an-angle-bracket-destination', text: 'Voir [ici](<https://ex.org/a b : c> "Titre ?") !', expected: `Voir [ici](<https://ex.org/a b : c> "Titre ?")${NNBSP}!`},
        {id: 'a-single-quoted-title', text: "Voir [ici](https://ex.org 'Titre : x') ?", expected: `Voir [ici](https://ex.org 'Titre : x')${NNBSP}?`},
        {id: 'a-parenthesized-title', text: 'Voir [ici](https://ex.org (Titre : x)) ?', expected: `Voir [ici](https://ex.org (Titre : x))${NNBSP}?`},
    ])('a link destination, with its title — $id', ({text, expected}) => {
        expect(spelled(typesetFrenchMarkdown(text))).toBe(spelled(expected));
    });

    // The whole image, as the hook leaves the <img> tag whole: its alt text and title are attributes in HTML. So the
    // ! that opens it is no sign, and the space before it stays plain.
    it.each([
        {id: 'its-alt-text-and-title', text: 'Légende : ![Graphique : 28 398 € ; « x » ?](https://ex.org/g.png "Titre : image") ici !', expected: `Légende${NBSP}: ![Graphique : 28 398 € ; « x » ?](https://ex.org/g.png "Titre : image") ici${NNBSP}!`},
        {id: 'after-a-word', text: 'Regardez ![le logo](https://ex.org/logo.png)', expected: 'Regardez ![le logo](https://ex.org/logo.png)'},
        {id: 'after-an-exclamation-mark', text: 'Bravo ! ![le logo](https://ex.org/logo.png)', expected: `Bravo${NNBSP}! ![le logo](https://ex.org/logo.png)`},
        {id: 'after-a-colon', text: 'Le logo : ![le logo](https://ex.org/logo.png)', expected: `Le logo${NBSP}: ![le logo](https://ex.org/logo.png)`},
    ])('an image, whole — alt text, destination and title — and the ! that opens it is not a sign — $id', ({text, expected}) => {
        expect(spelled(typesetFrenchMarkdown(text))).toBe(spelled(expected));
    });

    it.each([
        {id: 'a-url-and-a-quoted-title', text: 'Voir [la page][aide] :\n\n[aide]: https://ex.org/aide?x=1 "Aide : page ?"\n', expected: `Voir [la page][aide]${NBSP}:\n\n[aide]: https://ex.org/aide?x=1 "Aide : page ?"\n`},
        {id: 'an-angle-bracket-url-and-a-parenthesized-title', text: 'Texte !\n\n[aide]: <https://ex.org/a b> (Aide : « page »)\n\nFin ?', expected: `Texte${NNBSP}!\n\n[aide]: <https://ex.org/a b> (Aide : « page »)\n\nFin${NNBSP}?`},
    ])('a reference definition, the whole line — $id', ({text, expected}) => {
        expect(spelled(typesetFrenchMarkdown(text))).toBe(spelled(expected));
    });

    it('autolinks', () => {
        expect(spelled(typesetFrenchMarkdown('Écrivez-nous : <mailto:equipe@librefolio.org> ou voyez <https://librefolio.org/a?b=1&c=2> !'))).toBe(spelled(`Écrivez-nous${NBSP}: <mailto:equipe@librefolio.org> ou voyez <https://librefolio.org/a?b=1&c=2>${NNBSP}!`));
    });

    it.each([
        {id: 'a-title-attribute', text: '<abbr title="Taux annuel : 3 %">TAEG</abbr> : 3 %', expected: `<abbr title="Taux annuel : 3 %">TAEG</abbr>${NBSP}: 3${NNBSP}%`},
        {id: 'alt-and-title-attributes', text: '<img alt="Graphique : 28 398 € ; « x »" src="g.png" title="Titre : 50 %"> Légende : ici', expected: `<img alt="Graphique : 28 398 € ; « x »" src="g.png" title="Titre : 50 %"> Légende${NBSP}: ici`},
        {id: 'href-and-title-attributes', text: '<a href="https://example.org/aide?x=1&amp;y=2#a:b" title="Aide : page ?">l\'aide :</a>', expected: `<a href="https://example.org/aide?x=1&amp;y=2#a:b" title="Aide : page ?">l'aide${NBSP}:</a>`},
        {id: 'code-content', text: '<code>a : b ; c ?</code> Texte :', expected: `<code>a : b ; c ?</code> Texte${NBSP}:`},
        {id: 'kbd-content', text: "Appuyez sur <kbd>Ctrl + ?</kbd> : l'aide s'ouvre", expected: `Appuyez sur <kbd>Ctrl + ?</kbd>${NBSP}: l'aide s'ouvre`},
        {id: 'samp-content', text: '<samp>Total : 50 %</samp> ; ok', expected: `<samp>Total : 50 %</samp>${NNBSP}; ok`},
        {id: 'var-content', text: '<var>x ; y</var> !', expected: `<var>x ; y</var>${NNBSP}!`},
        {id: 'text-before-between-and-after', text: 'Avant : <code>a : b</code> entre : <kbd>Ctrl</kbd> + <kbd>S</kbd> : après !', expected: `Avant${NBSP}: <code>a : b</code> entre${NBSP}: <kbd>Ctrl</kbd> + <kbd>S</kbd>${NBSP}: après${NNBSP}!`},
    ])('a raw HTML tag with its attributes, and the content of code, kbd, samp and var on its line — $id', ({text, expected}) => {
        expect(spelled(typesetFrenchMarkdown(text))).toBe(spelled(expected));
    });

    it.each([
        {id: 'https', text: 'Voir https://ex.org/a?b=1&c=2#x:y : la page', expected: `Voir https://ex.org/a?b=1&c=2#x:y${NBSP}: la page`},
        {id: 'www', text: 'Le site www.librefolio.org/fr ; ou bien', expected: `Le site www.librefolio.org/fr${NNBSP}; ou bien`},
        {id: 'http-holding-markers', text: 'Avez-vous vu http://ex.org/a_(b)_c*d ?', expected: `Avez-vous vu http://ex.org/a_(b)_c*d${NNBSP}?`},
    ])('a bare URL, up to the next whitespace — $id', ({text, expected}) => {
        expect(spelled(typesetFrenchMarkdown(text))).toBe(spelled(expected));
    });

    it.each([
        {id: 'code', kept: '`a : b`'},
        {id: 'a-fenced-block', kept: `${TICKS}\nx : y\n${TICKS}`},
        {id: 'a-link-destination-with-a-title', kept: '[ici](https://ex.org/a?b=1 "Voir : là")'},
        {id: 'an-image-alt-text-included', kept: '![Graphique : 28 398 € ; « x » ?](https://ex.org/g.png "Titre : image")'},
        {id: 'a-reference-definition', kept: '[ici]: https://ex.org/a?b=1 "Voir : là"'},
        {id: 'an-autolink', kept: '<https://ex.org/a?b=1&c=2>'},
        {id: 'a-bare-url', kept: 'https://ex.org/a?b=1&c=2#d:e'},
        {id: 'a-chapter-heading', kept: '## [1.2.0] - 2026-10-12'},
        {id: 'a-section-heading', kept: '### 🐛 Corrigé'},
    ])('$id stays byte for byte between typeset paragraphs', ({kept}) => {
        const out = typesetFrenchMarkdown(`Avant :\n\n${kept}\n\nAprès !`);

        expect(spelled(out.split('\n\n')[1]), 'the protected part').toBe(spelled(kept));
        expect(spelled(out)).toBe(spelled(`Avant${NBSP}:\n\n${kept}\n\nAprès${NNBSP}!`));
    });

    it.each([
        {id: 'an-english-sentence', text: 'Fixed: the import no longer fails; really? Yes! 50% of 10,000 rows, see `a: b`, **Total:** and *why?*'},
        {id: 'an-empty-text', text: ''},
    ])('a text with no plain space before a sign comes back as it was — $id', ({text}) => {
        expect(spelled(typesetFrenchMarkdown(text))).toBe(spelled(text));
    });
});

/**
 * English source of the M-23 integration tests. Its 1.2.0 quotes French labels with their plain spaces, and the
 * French file leaves that chapter out: the French UI shows it in English, as written.
 */
const M23_ENGLISH_RAW = `# Changelog

## [1.3.0] - 2026-10-12

### 🐛 Fixed
- the forgotten-password card shows working commands

## [1.2.0] - 2026-09-07

### 🔄 Changed
- the French labels « Total : 1 000 € » and « Vraiment ? » are quoted as written ; 50 % of them

## [1.1.0] - 2026-07-01

### ✨ Added
- a feature
`;

const M23_ENGLISH = parseChangelog(M23_ENGLISH_RAW);

/**
 * The French file of the M-23 integration tests, with the plain spaces the translations keep: 1.3.0 and 1.1.0, not
 * 1.2.0. In 1.3.0 every text the modal shows has something to typeset — the intro, a section title and body, a
 * subsection title and body — and its heading carries another date than the English one.
 */
const M23_FRENCH_RAW = `# Journal des modifications

Préambule : ignoré.

## [1.3.0] - 2026-10-13

Une version de correctifs : lisez la suite !

### 🐛 Corrigé : divers
- La carte *Mot de passe oublié ?* affiche des commandes qui fonctionnent : \`./dev.py user reset\` ; voir \`a : b\`.

#### 💰 Coût d'achat et « P&L »
- **Total** : 28 398 € ; 12,5 % de plus ?

## [1.1.0] - 2026-07-01

### ✨ Ajouté
- une fonctionnalité « utile » !
`;

/** M23_FRENCH_RAW typeset by hand: the text the French UI must show. */
const M23_FRENCH_TYPESET = `# Journal des modifications

Préambule${NBSP}: ignoré.

## [1.3.0] - 2026-10-13

Une version de correctifs${NBSP}: lisez la suite${NNBSP}!

### 🐛 Corrigé${NBSP}: divers
- La carte *Mot de passe oublié${NNBSP}?* affiche des commandes qui fonctionnent${NBSP}: \`./dev.py user reset\`${NNBSP}; voir \`a : b\`.

#### 💰 Coût d'achat et «${NBSP}P&L${NBSP}»
- **Total**${NBSP}: 28${NNBSP}398${NNBSP}€${NNBSP}; 12,5${NNBSP}% de plus${NNBSP}?

## [1.1.0] - 2026-07-01

### ✨ Ajouté
- une fonctionnalité «${NBSP}utile${NBSP}»${NNBSP}!
`;

/** What the UI in `lang` shows when its file is `raw`: 1.3.0 and 1.1.0 from `raw` under the English version and date, 1.2.0 in English. */
function shownFrom(raw: string, lang: string) {
    const translated = (version: string) => {
        const {body, sections} = chapterOf(raw, version);
        return {...chapterOf(M23_ENGLISH_RAW, version), body, sections, lang};
    };
    return [translated('1.3.0'), {...chapterOf(M23_ENGLISH_RAW, '1.2.0'), lang: 'en'}, translated('1.1.0')];
}

/** Every text of a chapter the modal shows, with where it sits: the body, then each section's title and body, then its subsections'. */
function textsOf(chapter: ChangelogChapter): Array<[string, string]> {
    const texts: Array<[string, string]> = [['body', chapter.body]];
    chapter.sections.forEach((section, i) => {
        if (section.title !== null) texts.push([`sections[${i}].title`, section.title]);
        texts.push([`sections[${i}].body`, section.body]);
        section.subsections.forEach((sub, j) => texts.push([`sections[${i}].subsections[${j}].title`, sub.title], [`sections[${i}].subsections[${j}].body`, sub.body]));
    });
    return texts;
}

describe('createLocalizedChangelog (M-23): the French chapters typeset, every other text as written', () => {
    it.each(['fr', 'fr-FR', 'FR-ca'])('load(%s) shows every chapter of the French file typeset — body, section and subsection titles and bodies — under the English version and date', async (locale) => {
        // Fixture: every text of the French 1.3.0 has something to typeset, so none can pass by being left alone.
        const plain = textsOf(chapterOf(M23_FRENCH_RAW, '1.3.0'));
        const typeset = textsOf(chapterOf(M23_FRENCH_TYPESET, '1.3.0'));
        expect(
            plain.map(([where]) => where),
            'fixture: the texts of the French 1.3.0',
        ).toEqual(['body', 'sections[0].body', 'sections[1].title', 'sections[1].body', 'sections[1].subsections[0].title', 'sections[1].subsections[0].body']);
        expect(
            typeset.map(([where]) => where),
            'fixture: the typeset 1.3.0 has the shape of the plain one',
        ).toEqual(plain.map(([where]) => where));
        plain.forEach(([where, text], i) => expect(typeset[i][1], `fixture: 1.3.0 ${where} has nothing to typeset`).not.toBe(text));
        expect(chapterOf(M23_FRENCH_RAW, '1.3.0').date, 'fixture: the French heading carries another date').not.toBe(chapterOf(M23_ENGLISH_RAW, '1.3.0').date);
        const loader = vi.fn(async () => M23_FRENCH_RAW);
        const changelog = createLocalizedChangelog(M23_ENGLISH, new Map([['fr', loader]]));

        const shown = await changelog.load(locale);

        expect(spelled(shown)).toEqual(spelled(shownFrom(M23_FRENCH_TYPESET, 'fr')));
        expect(
            shown.map(({version, date}) => ({version, date})),
            'version and date come from CHANGELOG.md',
        ).toEqual(M23_ENGLISH.map(({version, date}) => ({version, date})));
        expect(loader).toHaveBeenCalledTimes(1);
    });

    it('a chapter the French file leaves out is shown in English as written, marked en, beside the typeset French ones', async () => {
        const fallback = chapterOf(M23_ENGLISH_RAW, '1.2.0');
        expect(fallback.body, 'fixture: the English 1.2.0 holds spaces French typography would change').toContain('« Total : 1 000 € »');
        const changelog = createLocalizedChangelog(M23_ENGLISH, new Map([['fr', async () => M23_FRENCH_RAW]]));

        const shown = await changelog.load('fr');

        expect(spelled(shown.find((chapter) => chapter.version === '1.2.0'))).toEqual(spelled({...fallback, lang: 'en'}));
        expect(spelled(shown.filter((chapter) => chapter.lang === 'fr')), 'the chapters the French file translates').toEqual(spelled(shownFrom(M23_FRENCH_TYPESET, 'fr').filter((chapter) => chapter.lang === 'fr')));
    });

    it('the same file as Italian or Spanish, and English, are shown as written: French alone is typeset', async () => {
        // One text under three languages, each through its own loader: the language is the only difference.
        const changelog = createLocalizedChangelog(M23_ENGLISH, new Map(['fr', 'it', 'es'].map((lang) => [lang, async () => M23_FRENCH_RAW] as const)));

        expect(spelled(await changelog.load('it')), 'it').toEqual(spelled(shownFrom(M23_FRENCH_RAW, 'it')));
        expect(spelled(await changelog.load('es')), 'es').toEqual(spelled(shownFrom(M23_FRENCH_RAW, 'es')));
        expect(spelled(await changelog.load('en')), 'en').toEqual(spelled(M23_ENGLISH.map((chapter) => ({...chapter, lang: 'en'}))));
        expect(spelled(await changelog.load('fr')), 'fr: the same file, typeset').toEqual(spelled(shownFrom(M23_FRENCH_TYPESET, 'fr')));
    });

    it('pure: the French loader and the text it returned, and the English chapters, are left as they came — only what is shown is typeset', async () => {
        const english = structuredClone(M23_ENGLISH);
        const before = structuredClone(english);
        const loader = vi.fn(async () => M23_FRENCH_RAW);
        const loaders = new Map([['fr', loader]]);
        const changelog = createLocalizedChangelog(english, loaders);

        const shown = await changelog.load('fr');

        expect(spelled(shown), 'what is shown').toEqual(spelled(shownFrom(M23_FRENCH_TYPESET, 'fr')));
        expect([...loaders], 'the loaders given').toEqual([['fr', loader]]);
        await expect(loader.mock.results[0]?.value, 'the text the loader returned').resolves.toBe(M23_FRENCH_RAW);
        expect(english, 'the English chapters given').toEqual(before);
    });

    it('the cache: after the load, peek answers fr, fr-FR and FR-ca with the same typeset chapters, and the file is not loaded again', async () => {
        const loader = vi.fn(async () => M23_FRENCH_RAW);
        const changelog = createLocalizedChangelog(M23_ENGLISH, new Map([['fr', loader]]));

        const shown = await changelog.load('fr');

        for (const locale of ['fr', 'fr-FR', 'FR-ca']) expect(spelled(changelog.peek(locale)), `peek(${locale})`).toEqual(spelled(shownFrom(M23_FRENCH_TYPESET, 'fr')));
        expect(changelog.peek('fr')).toEqual(shown);
        await expect(changelog.load('FR-ca')).resolves.toEqual(shown);
        expect(loader).toHaveBeenCalledTimes(1);
    });
});
