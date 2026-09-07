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
 * Node env: pure string logic, no DOM.
 */

import {describe, expect, it} from 'vitest';
import {parseChangelog, splitSections, changelogChapters, CHANGELOG_REMOTE_URL} from './changelog';

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
    it('parses the repo CHANGELOG.md into at least one dated chapter', () => {
        // The modal renders this list: an unparsable shipped file means an empty
        // modal in production, which is exactly the failure this test exists to
        // catch before release.
        expect(changelogChapters.length).toBeGreaterThan(0);
        expect(changelogChapters.every((c) => c.version.length > 0 && c.date.length > 0)).toBe(true);
    });

    it('points the remote link at the repository CHANGELOG.md', () => {
        expect(CHANGELOG_REMOTE_URL).toBe('https://github.com/Librefolio/LibreFolio/blob/main/CHANGELOG.md');
    });
});
