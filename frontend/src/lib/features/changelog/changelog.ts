/**
 * Changelog (F12) — the repository CHANGELOG.md bundled at build time.
 *
 * Vite's `?raw` import inlines the file contents into the bundle, so the modal
 * works fully offline (the file is parsed once per session, at module load).
 * Chapters are the Keep-a-Changelog `## [x.y.z] - date` sections.
 */

import changelogRaw from '../../../../../CHANGELOG.md?raw';

export interface ChangelogSubsection {
    /** `####`-level heading text. */
    title: string;
    /** Markdown body of the subsection (heading excluded). */
    body: string;
}

export interface ChangelogSection {
    /** Sub-heading text (null = intro block before the first `###`). */
    title: string | null;
    /** Markdown body of the section (heading excluded). */
    body: string;
    /** `####`-level sub-sub-sections, individually foldable (round-4 F12). */
    subsections: ChangelogSubsection[];
}

export interface ChangelogChapter {
    /** Version label as written in the heading, e.g. "1.1.0". */
    version: string;
    /** Date label as written in the heading, e.g. "2026-08-07". */
    date: string;
    /** Markdown body of the chapter (heading excluded). */
    body: string;
    /** `###`-level sub-sections, foldable in the modal (round-3 F12). */
    sections: ChangelogSection[];
}

// The date part is optional: Keep-a-Changelog's canonical `## [Unreleased]`
// heading has none, and dropping it would silently hide upcoming releases.
const CHAPTER_HEADING = /^## \[([^\]]+)\](?:\s*-\s*(.+?))?\s*$/;

const SECTION_HEADING = /^###\s+(.+?)\s*$/;
// #### (and deeper) — checked before ### since `#### x` also matches /###+/.
const SUBSECTION_HEADING = /^#{4,6}\s+(.+?)\s*$/;

/** Split a chapter body into `###` sections, each with `####` subsections.
 *  Content before the first `###` becomes a title-less intro section;
 *  `####` before any `###` attaches to the intro section. */
export function splitSections(body: string): ChangelogSection[] {
    const sections: ChangelogSection[] = [];
    let current: ChangelogSection | null = null;
    let currentSub: ChangelogSubsection | null = null;

    for (const line of body.split('\n')) {
        const subMatch = SUBSECTION_HEADING.exec(line);
        const secMatch = SECTION_HEADING.exec(line);
        if (subMatch) {
            // #### inside a section (or the intro) → new subsection
            if (!current) {
                current = {title: null, body: '', subsections: []};
                sections.push(current);
            }
            currentSub = {title: subMatch[1], body: ''};
            current.subsections.push(currentSub);
        } else if (secMatch) {
            current = {title: secMatch[1], body: '', subsections: []};
            sections.push(current);
            currentSub = null;
        } else if (currentSub) {
            currentSub.body += line + '\n';
        } else if (current) {
            current.body += line + '\n';
        } else if (line.trim().length > 0) {
            // preamble lines before the first ### (skip pure leading blank runs)
            current = {title: null, body: '', subsections: []};
            sections.push(current);
            current.body += line + '\n';
        }
    }

    return sections.map((s) => ({...s, subsections: s.subsections.filter((sub) => sub.body.trim().length > 0)})).filter((s) => s.body.trim().length > 0 || s.subsections.length > 0);
}

/**
 * Split the raw changelog into chapters. The preamble (title, Keep-a-Changelog
 * note) is dropped. Unknown sections (e.g. `## [Unreleased]`) are kept too —
 * the version label is whatever sits between the brackets.
 */
export function parseChangelog(raw: string): ChangelogChapter[] {
    const chapters: Array<Omit<ChangelogChapter, 'sections'>> = [];
    let current: Omit<ChangelogChapter, 'sections'> | null = null;

    for (const line of raw.split('\n')) {
        const match = CHAPTER_HEADING.exec(line);
        if (match) {
            current = {version: match[1], date: match[2] ?? '', body: ''};
            chapters.push(current);
        } else if (current) {
            current.body += line + '\n';
        }
    }

    return chapters.filter((c) => c.body.trim().length > 0 || c.version.toLowerCase() === 'unreleased').map((c) => ({...c, sections: splitSections(c.body)}));
}

/** The bundled chapters (empty when the build shipped no changelog). */
export const changelogChapters: ChangelogChapter[] = parseChangelog(changelogRaw);

/** Canonical remote file — the modal always links here for the live version. */
export const CHANGELOG_REMOTE_URL = 'https://github.com/Librefolio/LibreFolio/blob/main/CHANGELOG.md';
