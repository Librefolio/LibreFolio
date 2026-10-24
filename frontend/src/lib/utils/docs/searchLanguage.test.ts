/**
 * searchLanguage.test.ts — the pure half of `mkdocs_src/docs/javascripts/search-language.js` (DOC-2, route B).
 *
 * Material downloads ONE `search/search_index.json` for the four languages of the documentation. The build splits it
 * into `search_index.<lang>.json` (`hooks/search_language_split.py`, tested by `test_docs_search_split.py`), and this
 * classic script — loaded in the head, BEFORE Material's bundle — wraps `XMLHttpRequest.prototype.open` (what Material
 * 9.7.7 loads the index with; the browser reports `xmlhttprequest`) and `fetch`, so the page asks for its own language's
 * file. This file pins what needs no browser:
 *
 *   - `currentLanguage(lang)`: the primary subtag of `<html lang>` when it is `en`, `it`, `fr` or `es`, else `en`;
 *   - `searchIndexUrl(url, lang, allLanguages)`: a URL whose PATH ends in `/search/search_index.json` — any base,
 *     relative or absolute, a query string kept — becomes `…/search/search_index.<lang>.json` in the same folder; every
 *     other URL, and the already rewritten one, comes back as it was; with «all languages» nothing changes;
 *   - `LABELS`: the toggle's text in the four languages, none empty, no two alike;
 *   - the file itself: a classic script with no dependency (no `import`, `export` or `require`), which exports through
 *     `module.exports` only when `module` exists, and loads in a host with no `window` at all (node) without throwing.
 *
 * The XHR and `fetch` wrappers and the toggle need a DOM: `searchLanguage.dom.test.ts`.
 *
 * The script is outside `src/` and is not a module: `__tests__/searchLanguageScript.ts` reads it as text and runs it.
 *
 * Red today: `search-language.js` does not exist yet, so every case below is red (the contract is written first).
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */
import {describe, expect, it} from 'vitest';
import {loadScript, scriptSource, type DocsLanguage} from './__tests__/searchLanguageScript';

const LANGUAGES: DocsLanguage[] = ['en', 'it', 'fr', 'es'];

const FULL = 'https://x/mkdocs/search/search_index.json';

describe('currentLanguage', () => {
    const {currentLanguage} = loadScript();

    it.each([
        ['en', 'en'],
        ['it', 'it'],
        ['fr', 'fr'],
        ['es', 'es'],
        ['it-IT', 'it'],
        ['fr-CA', 'fr'],
        ['es-419', 'es'],
        ['en-GB', 'en'],
    ])('%s → %s', (lang, expected) => {
        expect(currentLanguage(lang)).toBe(expected);
    });

    it.each(['de', 'pt-BR', 'xx', 'ita', 'italian', 'itx', 'e', '', 'zh-Hans'])('a language the site does not have (%j) → en', (lang) => {
        expect(currentLanguage(lang)).toBe('en');
    });

    it('no language at all (a page without lang) → en', () => {
        expect(currentLanguage(undefined)).toBe('en');
        expect(currentLanguage(null)).toBe('en');
    });
});

describe('LABELS', () => {
    const {LABELS} = loadScript();

    it('has the four languages, and only them', () => {
        expect(Object.keys(LABELS).sort()).toEqual([...LANGUAGES].sort());
    });

    it('each label is a non-empty text', () => {
        for (const lang of LANGUAGES) {
            expect(typeof LABELS[lang], lang).toBe('string');
            expect(LABELS[lang].trim().length, lang).toBeGreaterThan(0);
        }
    });

    it('no two languages share a label: an Italian page with the English button is the case this avoids', () => {
        expect(new Set(LANGUAGES.map((lang) => LABELS[lang])).size).toBe(4);
    });
});

describe('searchIndexUrl — the index URL is redirected to the language file', () => {
    const {searchIndexUrl} = loadScript();

    it.each(LANGUAGES)('an absolute URL, in %s', (lang) => {
        expect(searchIndexUrl(FULL, lang, false)).toBe(`https://x/mkdocs/search/search_index.${lang}.json`);
    });

    it.each([
        ['a relative path with ..', '../search/search_index.json', '../search/search_index.it.json'],
        ['a relative path', 'search/search_index.json', 'search/search_index.it.json'],
        ['a relative path with ./', './search/search_index.json', './search/search_index.it.json'],
        ['an absolute path', '/search/search_index.json', '/search/search_index.it.json'],
        ['an absolute path with a base folder', '/mkdocs/search/search_index.json', '/mkdocs/search/search_index.it.json'],
        ['an absolute URL at the origin root', 'https://x/search/search_index.json', 'https://x/search/search_index.it.json'],
        ['a nested base', 'https://x/a/b/c/search/search_index.json', 'https://x/a/b/c/search/search_index.it.json'],
        ['a port', 'http://localhost:6181/mkdocs/it/../search/search_index.json', 'http://localhost:6181/mkdocs/it/../search/search_index.it.json'],
    ])('%s', (_label, url, expected) => {
        expect(searchIndexUrl(url, 'it', false)).toBe(expected);
    });

    it('a query string is kept', () => {
        expect(searchIndexUrl('/search/search_index.json?v=1', 'fr', false)).toBe('/search/search_index.fr.json?v=1');
        expect(searchIndexUrl(`${FULL}?a=1&b=2`, 'es', false)).toBe('https://x/mkdocs/search/search_index.es.json?a=1&b=2');
    });

    it('«all languages»: nothing changes, whatever the URL', () => {
        for (const url of [FULL, '../search/search_index.json', '/search/search_index.json?v=1']) {
            expect(searchIndexUrl(url, 'it', true)).toBe(url);
        }
    });

    it.each([
        ['a URL already rewritten', '/search/search_index.it.json'],
        ['another file of the folder', 'https://x/mkdocs/search/other.json'],
        ['the index name without the search folder', '/search_index.json'],
        ['a folder that only ends like search', 'https://x/mkdocs/xsearch/search_index.json'],
        ['a longer file name', '/search/search_index.json.bak'],
        ['a path that goes on after the file', '/search/search_index.json/more'],
        ['the pattern only in the query', '/foo?u=/search/search_index.json'],
        ['the pattern only in the fragment', '/foo#/search/search_index.json'],
        ['Material’s worker', 'https://x/mkdocs/assets/javascripts/workers/search.js'],
        ['a page', 'https://x/mkdocs/it/'],
        ['the app’s own API', '/api/v1/assets'],
        ['the empty string', ''],
    ])('%s is left untouched', (_label, url) => {
        expect(searchIndexUrl(url, 'it', false)).toBe(url);
    });
});

describe('search-language.js as a file', () => {
    it('is a classic script with no dependency: no import, export or require', () => {
        const source = scriptSource();
        expect(source).not.toMatch(/^\s*import\s[^(]/m);
        expect(source).not.toMatch(/^\s*export\s/m);
        expect(source).not.toMatch(/\brequire\s*\(/);
    });

    it('exports through module.exports only when `module` exists', () => {
        expect(scriptSource()).toMatch(/typeof\s+module\s*!==\s*['"]undefined['"]/);
    });

    it('loads in a host with no window, no document and no storage (node) without throwing', () => {
        expect(typeof window).toBe('undefined');
        expect(typeof document).toBe('undefined');
        expect(() => loadScript()).not.toThrow();
    });

    it('exports the two installers: installXhrRewriter (the one Material needs) and installFetchRewriter', () => {
        const exported = loadScript() as unknown as Record<string, unknown>;
        expect(typeof exported.installXhrRewriter).toBe('function');
        expect(typeof exported.installFetchRewriter).toBe('function');
    });

    it('installXhrRewriter in a host with no XMLHttpRequest (node) does not throw', () => {
        expect(typeof XMLHttpRequest).toBe('undefined');
        const exported = loadScript() as unknown as {installXhrRewriter: () => void};
        expect(() => exported.installXhrRewriter()).not.toThrow();
    });

    it('exports the three names the contract gives', () => {
        const exported = loadScript();
        expect(typeof exported.searchIndexUrl).toBe('function');
        expect(typeof exported.currentLanguage).toBe('function');
        expect(typeof exported.LABELS).toBe('object');
    });

    it('does not touch fetch when there is no window to wrap', () => {
        const before = globalThis.fetch;
        loadScript();
        expect(globalThis.fetch).toBe(before);
    });
});
