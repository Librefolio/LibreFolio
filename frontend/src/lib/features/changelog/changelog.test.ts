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
import {parseChangelog, changelogChapters, CHANGELOG_REMOTE_URL} from './changelog';

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
