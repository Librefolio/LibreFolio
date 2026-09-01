/**
 * Changelog (F12) — the repository CHANGELOG.md bundled at build time.
 *
 * Vite's `?raw` import inlines the file contents into the bundle, so the modal
 * works fully offline (the file is parsed once per session, at module load).
 * Chapters are the Keep-a-Changelog `## [x.y.z] - date` sections.
 */

import changelogRaw from '../../../../../CHANGELOG.md?raw';

export interface ChangelogChapter {
    /** Version label as written in the heading, e.g. "1.1.0". */
    version: string;
    /** Date label as written in the heading, e.g. "2026-08-07". */
    date: string;
    /** Markdown body of the chapter (heading excluded). */
    body: string;
}

// The date part is optional: Keep-a-Changelog's canonical `## [Unreleased]`
// heading has none, and dropping it would silently hide upcoming releases.
const CHAPTER_HEADING = /^## \[([^\]]+)\](?:\s*-\s*(.+?))?\s*$/;

/**
 * Split the raw changelog into chapters. The preamble (title, Keep-a-Changelog
 * note) is dropped. Unknown sections (e.g. `## [Unreleased]`) are kept too —
 * the version label is whatever sits between the brackets.
 */
export function parseChangelog(raw: string): ChangelogChapter[] {
    const chapters: ChangelogChapter[] = [];
    let current: ChangelogChapter | null = null;

    for (const line of raw.split('\n')) {
        const match = CHAPTER_HEADING.exec(line);
        if (match) {
            current = {version: match[1], date: match[2] ?? '', body: ''};
            chapters.push(current);
        } else if (current) {
            current.body += line + '\n';
        }
    }

    return chapters.filter((c) => c.body.trim().length > 0 || c.version.toLowerCase() === 'unreleased');
}

/** The bundled chapters (empty when the build shipped no changelog). */
export const changelogChapters: ChangelogChapter[] = parseChangelog(changelogRaw);

/** Canonical remote file — the modal always links here for the live version. */
export const CHANGELOG_REMOTE_URL = 'https://github.com/Librefolio/LibreFolio/blob/main/CHANGELOG.md';
