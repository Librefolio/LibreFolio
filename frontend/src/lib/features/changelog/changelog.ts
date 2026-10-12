/**
 * Changelog (F12) — the repository CHANGELOG.md bundled at build time, and its
 * translations.
 *
 * Vite's `?raw` import inlines the English file into the bundle, so the modal
 * works fully offline (the file is parsed once per session, at module load).
 * Chapters are the Keep-a-Changelog `## [x.y.z] - date` sections.
 *
 * Translations sit beside it as `CHANGELOG.<xx>.md`: the same chapters with the
 * same `## [x.y.z] - date` lines, a chapter not translated yet simply absent.
 * Each file is a lazy chunk, fetched the first time the modal opens in that
 * language, and merged with the English file chapter by chapter.
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

/** A chapter as the modal shows it: the English source or its translation. */
export interface DisplayedChapter extends ChangelogChapter {
    /** Language of the text shown: the interface language when translated, `en` otherwise. */
    lang: string;
}

const SOURCE_LANGUAGE = 'en';

/** Base language of an interface locale, lower-cased: `it-IT` → `it`; none → `en`. */
export function baseLanguage(locale: string | null | undefined): string {
    return (locale ?? '').trim().toLowerCase().split(/[-_]/)[0] || SOURCE_LANGUAGE;
}

function inEnglish(chapter: ChangelogChapter): DisplayedChapter {
    return {...chapter, lang: SOURCE_LANGUAGE};
}

/**
 * One chapter per English chapter, in English order, keyed by version (the text
 * between the brackets). A translated chapter with content replaces the English
 * text; version and date always come from the English chapter, so a translated
 * heading with another date still counts (the translation validator reports the
 * drift). A translated chapter with no English counterpart is ignored.
 */
export function mergeChapters(english: readonly ChangelogChapter[], translated: readonly ChangelogChapter[], lang: string): DisplayedChapter[] {
    if (lang === SOURCE_LANGUAGE) return english.map(inEnglish);
    const byVersion = new Map<string, ChangelogChapter>();
    for (const chapter of translated) {
        if (chapter.sections.length > 0 && !byVersion.has(chapter.version)) byVersion.set(chapter.version, chapter);
    }
    return english.map((chapter) => {
        const translation = byVersion.get(chapter.version);
        return translation ? {version: chapter.version, date: chapter.date, body: translation.body, sections: translation.sections, lang} : inEnglish(chapter);
    });
}

const TRANSLATION_FILE = /(?:^|\/)CHANGELOG\.([a-z]{2})\.md$/;

/** Loader per language, from an `import.meta.glob` record of `CHANGELOG.<xx>.md` files. */
export function translationLoaders(modules: Record<string, () => Promise<string>>): Map<string, () => Promise<string>> {
    const loaders = new Map<string, () => Promise<string>>();
    for (const [path, loader] of Object.entries(modules)) {
        const language = TRANSLATION_FILE.exec(path)?.[1];
        if (language && language !== SOURCE_LANGUAGE) loaders.set(language, loader);
    }
    return loaders;
}

export interface LocalizedChangelog {
    /** The chapters for a locale when they need no wait: English for `en` or a language with no
     *  translation, the merge once that language has loaded; undefined while it still has to load. */
    peek(locale: string | null | undefined): DisplayedChapter[] | undefined;
    /** Loads the language's translation once, merges and caches it. Never rejects: a failed load
     *  resolves to English and is not cached, so the next call tries again. */
    load(locale: string | null | undefined): Promise<DisplayedChapter[]>;
}

export function createLocalizedChangelog(english: readonly ChangelogChapter[], loaders: ReadonlyMap<string, () => Promise<string>>): LocalizedChangelog {
    const englishOnly = english.map(inEnglish);
    const merged = new Map<string, DisplayedChapter[]>();
    const pending = new Map<string, Promise<DisplayedChapter[]>>();

    function peek(locale: string | null | undefined): DisplayedChapter[] | undefined {
        const language = baseLanguage(locale);
        if (language === SOURCE_LANGUAGE || !loaders.has(language)) return englishOnly;
        return merged.get(language);
    }

    function load(locale: string | null | undefined): Promise<DisplayedChapter[]> {
        const language = baseLanguage(locale);
        const ready = peek(language);
        if (ready) return Promise.resolve(ready);
        let request = pending.get(language);
        if (!request) {
            const loader = loaders.get(language) as () => Promise<string>;
            request = Promise.resolve()
                .then(loader)
                .then((raw) => {
                    const chapters = mergeChapters(english, parseChangelog(raw), language);
                    merged.set(language, chapters);
                    return chapters;
                })
                .catch(() => englishOnly)
                .finally(() => pending.delete(language));
            pending.set(language, request);
        }
        return request;
    }

    return {peek, load};
}

/** The translated changelogs bundled with the build: `CHANGELOG.<xx>.md` beside CHANGELOG.md, one lazy chunk each. */
export const changelogTranslationLoaders = translationLoaders(import.meta.glob<string>('../../../../../CHANGELOG.[a-z][a-z].md', {query: '?raw', import: 'default'}));

/** The app's changelog: the bundled English chapters and their bundled translations. */
export const localizedChangelog = createLocalizedChangelog(changelogChapters, changelogTranslationLoaders);
