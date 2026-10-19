/**
 * Changelog (F12) — the repository CHANGELOG.md bundled at build time, and its
 * translations.
 *
 * Vite's `?raw` import inlines the English file into the bundle, so the modal
 * works fully offline (the file is parsed once per session, at module load).
 * The bundled files are imported in `changelogSources.ts`, which a jsdom test
 * can replace (A-CL1).
 * Chapters are the Keep-a-Changelog `## [x.y.z] - date` sections.
 *
 * Translations sit beside it as `CHANGELOG.<xx>.md`: the same chapters with the
 * same `## [x.y.z] - date` lines, a chapter not translated yet simply absent.
 * Each file is a lazy chunk, fetched the first time the modal opens in that
 * language, and merged with the English file chapter by chapter.
 *
 * French chapters are shown with French spacing (M-23): the rules the French
 * docs get from `mkdocs_src/hooks/fr_typography.py` at build time, applied here
 * to the prose of the Markdown before it is cut into chapters. Code, link
 * destinations, images, HTML and URLs keep their text, and `CHANGELOG.fr.md`
 * keeps its plain spaces, as the translation pipeline writes them.
 */

import {SvelteMap} from 'svelte/reactivity';
import {englishChangelog, translationModules} from './changelogSources';

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
export const changelogChapters: ChangelogChapter[] = parseChangelog(englishChangelog);

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

// =============================================================================
// French typography (M-23): the rules of mkdocs_src/hooks/fr_typography.py
// =============================================================================

const NBSP = '\u00a0';
const NNBSP = '\u202f';

const SPACE = '[ \\t\\r\\n]+';
// What may follow a sign for its space to be typeset: whitespace, the end of the text, closing punctuation or an entity.
const AFTER_SIGN = '(?=[\\s)\\]}»”"\'.,;:?!…&]|$)';
// In Markdown an emphasis, code, link or tag marker stands where the hook's HTML has a tag: a sign before one ends its text.
const AFTER_SIGN_IN_MARKDOWN = '(?=[\\s)\\]}»”"\'.,;:?!…&*_~`\\[<]|$)';

function typesettingRules(afterSign: string): Array<[RegExp, string]> {
    return [
        [new RegExp(`${SPACE}(?=:${afterSign})`, 'gu'), NBSP],
        [new RegExp(`${SPACE}(?=[;?!]${afterSign})`, 'gu'), NNBSP],
        [new RegExp(`${SPACE}(?=%)`, 'gu'), NNBSP],
        [new RegExp(`(?<=\\p{Nd})${SPACE}(?=[€$£¥])`, 'gu'), NNBSP],
        [new RegExp(`(?<=«)${SPACE}`, 'gu'), NBSP],
        [new RegExp(`${SPACE}(?=»)`, 'gu'), NBSP],
    ];
}

const TEXT_RULES = typesettingRules(AFTER_SIGN);
const MARKDOWN_RULES = typesettingRules(AFTER_SIGN_IN_MARKDOWN);
const THOUSANDS = /(?<![\p{L}\p{N}_.,#&])\p{Nd}{1,3}(?: \p{Nd}{3})+(?![\p{L}\p{N}_]|[.,]\p{Nd}{3})/gu;

function applyRules(text: string, rules: Array<[RegExp, string]>): string {
    for (const [pattern, space] of rules) text = text.replace(pattern, space);
    return text.replace(THOUSANDS, (group) => group.replaceAll(' ', NNBSP));
}

/**
 * French spacing in a run of text, as `mkdocs_src/hooks/fr_typography.py` sets it in the French docs: the whitespace
 * before `:` and inside « » becomes a no-break space; the whitespace before `;` `?` `!` `%`, between a number and its
 * currency and between thousand groups becomes a narrow one. It only replaces whitespace that is there.
 */
export function typesetFrench(text: string): string {
    return applyRules(text, TEXT_RULES);
}

const FENCE_OPEN = /^\s*(`{3,}|~{3,})/;
const FENCE_CLOSE = /^\s*(`{3,}|~{3,})\s*$/;
const BLOCK_START = /^\s*(?:[-*+]\s|\d+[.)]\s|#{1,6}\s|>)/;
const REFERENCE_DEFINITION = / {0,3}\[[^\]\n]+\]:[ \t]*\S[^\n]*/y;
const COMMENT = /<!--[\s\S]*?-->/y;
const AUTOLINK = /<[A-Za-z][A-Za-z0-9+.-]{1,31}:[^\s<>]*>|<[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*>/y;
const TAG = /<(\/?)([A-Za-z][A-Za-z0-9-]*)(?:\s[^<>]*)?>/y;
const BARE_URL = /(?:https?:\/\/|www\.)[^\s<]*/y;
// Elements whose content is code or not prose, skipped as the hook skips them.
const OPAQUE_ELEMENTS = new Set(['code', 'pre', 'kbd', 'samp', 'var', 'svg', 'math', 'script', 'style', 'textarea']);

function execAt(pattern: RegExp, text: string, at: number): RegExpExecArray | null {
    pattern.lastIndex = at;
    return pattern.exec(text);
}

/** Where the Markdown block holding `at` ends: before a blank line or a line that opens another block (an item, a heading, a quote). */
function blockEnd(text: string, at: number): number {
    let end = text.indexOf('\n', at);
    while (end !== -1) {
        const next = text.indexOf('\n', end + 1);
        const line = text.slice(end + 1, next === -1 ? text.length : next);
        if (!line.trim() || BLOCK_START.test(line)) return end;
        end = next;
    }
    return text.length;
}

/** The end of the inline code span opened by the backtick run at `at`, or -1 when the run is literal text. */
function codeSpanEnd(text: string, at: number): number {
    let open = at;
    while (text[open] === '`') open++;
    const length = open - at;
    const limit = blockEnd(text, at);
    for (let from = open; from < limit; ) {
        const start = text.indexOf('`', from);
        if (start === -1 || start >= limit) return -1;
        let end = start;
        while (text[end] === '`') end++;
        if (end - start === length) return end;
        from = end;
    }
    return -1;
}

/** The end of the `]` closing the `[` at `open`, nested brackets included; -1 when it does not close in its block. */
function labelEnd(text: string, open: number): number {
    const limit = blockEnd(text, open);
    let depth = 0;
    for (let i = open; i < limit; i++) {
        if (text[i] === '\\') i++;
        else if (text[i] === '[') depth++;
        else if (text[i] === ']' && --depth === 0) return i + 1;
    }
    return -1;
}

/** The end of the `(...)` opened at `open`: a link's destination and title, nested parentheses, `<...>` and quoted titles included; -1 when it does not close in its block. */
function destinationEnd(text: string, open: number): number {
    const limit = blockEnd(text, open);
    let depth = 0;
    for (let i = open; i < limit; i++) {
        const ch = text[i];
        if (ch === '\\') {
            i++;
        } else if (ch === '<' && i === open + 1) {
            const close = text.indexOf('>', i);
            if (close !== -1 && close < limit) i = close;
        } else if ((ch === '"' || ch === "'") && /\s/.test(text[i - 1])) {
            const close = text.indexOf(ch, i + 1);
            if (close !== -1 && close < limit) i = close;
        } else if (ch === '(') {
            depth++;
        } else if (ch === ')' && --depth === 0) {
            return i + 1;
        }
    }
    return -1;
}

/** The end of the HTML at `at` to keep as it is (a comment, an autolink, a tag; with an opaque element's content), or -1. */
function htmlEnd(text: string, at: number): number {
    const simple = execAt(COMMENT, text, at) ?? execAt(AUTOLINK, text, at);
    if (simple) return at + simple[0].length;
    const tag = execAt(TAG, text, at);
    if (!tag) return -1;
    let end = at + tag[0].length;
    const name = tag[2].toLowerCase();
    if (!tag[1] && !tag[0].endsWith('/>') && OPAQUE_ELEMENTS.has(name)) {
        const close = new RegExp(`</${name}\\s*>`, 'i').exec(text.slice(end));
        if (close) end += close.index + close[0].length;
    }
    return end;
}

/** `typesetFrench` on Markdown with no fence: code spans, link destinations, images, autolinks, HTML and URLs stay as they are. */
function typesetProse(text: string): string {
    let out = '';
    let run = '';
    let i = 0;
    const keepUntil = (end: number) => {
        out += applyRules(run, MARKDOWN_RULES) + text.slice(i, end);
        run = '';
        i = end;
    };
    while (i < text.length) {
        const ch = text[i];
        const reference = i === 0 || text[i - 1] === '\n' ? execAt(REFERENCE_DEFINITION, text, i) : null;
        let end = -1;
        if (reference) end = i + reference[0].length;
        else if (ch === '`') end = codeSpanEnd(text, i);
        else if (ch === '!' && text[i + 1] === '[') {
            const label = labelEnd(text, i + 1);
            end = label !== -1 && text[label] === '(' ? destinationEnd(text, label) : -1;
            if (end === -1) end = i + 1; // a lone "![": its "!" is not a sign
        } else if (ch === '<') end = htmlEnd(text, i);
        else if ((ch === 'h' || ch === 'w') && (i === 0 || /[\s(*_~]/.test(text[i - 1]))) {
            const url = execAt(BARE_URL, text, i);
            if (url) end = i + url[0].length;
        }
        if (end !== -1) {
            keepUntil(end);
        } else if (ch === ']' && text[i + 1] === '(' && destinationEnd(text, i + 1) !== -1) {
            run += ch;
            i++;
            keepUntil(destinationEnd(text, i));
        } else if (ch === '\\' && i + 1 < text.length) {
            run += text.slice(i, i + 2);
            i += 2;
        } else if (ch === '`') {
            while (text[i] === '`') run += text[i++];
        } else {
            run += ch;
            i++;
        }
    }
    keepUntil(text.length);
    return out;
}

/**
 * French spacing on the prose of a Markdown text (`typesetFrench`), as the French docs get it from the hook at build
 * time: fenced code, code spans, link destinations, images, autolinks, HTML and URLs stay byte for byte, and an
 * emphasis, code, link or tag marker ends a run of text as a tag does in the hook's HTML.
 */
export function typesetFrenchMarkdown(markdown: string): string {
    const out: string[] = [];
    let prose: string[] = [];
    let fence: {char: string; length: number} | null = null;
    const flush = () => {
        if (prose.length > 0) out.push(typesetProse(prose.join('\n')));
        prose = [];
    };
    for (const line of markdown.split('\n')) {
        if (fence) {
            out.push(line);
            const close = FENCE_CLOSE.exec(line);
            if (close && close[1][0] === fence.char && close[1].length >= fence.length) fence = null;
            continue;
        }
        const open = FENCE_OPEN.exec(line);
        // A backtick fence's info string holds no backtick: "``` x ```" on one line is a code span.
        if (open && !(open[1][0] === '`' && line.slice(open[0].length).includes('`'))) {
            flush();
            out.push(line);
            fence = {char: open[1][0], length: open[1].length};
            continue;
        }
        prose.push(line);
    }
    flush();
    return out.join('\n');
}

/** The typography a translation gets before it is cut into chapters, by language: French alone has one. */
const TYPESETTERS: ReadonlyMap<string, (markdown: string) => string> = new Map([['fr', typesetFrenchMarkdown]]);

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
     *  translation, the merge once that language has loaded; undefined while it still has to load.
     *  Reactive: read in a `$derived` or an effect, it follows the load that fills it, whoever started it. */
    peek(locale: string | null | undefined): DisplayedChapter[] | undefined;
    /** Loads the language's translation once, merges and caches it. Never rejects: a failed load
     *  resolves to English and is not cached, so the next call tries again. */
    load(locale: string | null | undefined): Promise<DisplayedChapter[]>;
}

export function createLocalizedChangelog(english: readonly ChangelogChapter[], loaders: ReadonlyMap<string, () => Promise<string>>): LocalizedChangelog {
    const englishOnly = english.map(inEnglish);
    // A SvelteMap, so a window waiting for a language sees the load that fills it, its own or another's (A-CL1).
    const merged = new SvelteMap<string, DisplayedChapter[]>();
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
                    const typeset = TYPESETTERS.get(language);
                    const chapters = mergeChapters(english, parseChangelog(typeset ? typeset(raw) : raw), language);
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
export const changelogTranslationLoaders = translationLoaders(translationModules);

/** The app's changelog: the bundled English chapters and their bundled translations. */
export const localizedChangelog = createLocalizedChangelog(changelogChapters, changelogTranslationLoaders);
