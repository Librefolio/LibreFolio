// @vitest-environment jsdom
//
// The docblock above is load-bearing: the wrapper reads `document.documentElement.lang` and `localStorage`, wraps
// `window.fetch`, and the toggle is built inside a page's DOM. jsdom provides all of it; no real navigation happens —
// `location` is replaced by a stub that only counts calls to `reload`.
/**
 * searchLanguage.dom.test.ts — the browser half of `mkdocs_src/docs/javascripts/search-language.js` (DOC-2, route B).
 *
 * The contract (`H-DOC2-analisi.md`, route B, with the facts read off Material 9.7.7's built page):
 *
 *   - **The `XMLHttpRequest` wrapper.** Material 9.7.7 loads the index with `XMLHttpRequest` (the browser reports
 *     `initiatorType: xmlhttprequest`), NOT `fetch`: the wrapper that matters in production is the one on
 *     `XMLHttpRequest.prototype.open` (`installXhrRewriter`, installed once, marker `open.lfSearchLanguage`). `open(method,
 *     url, async, user, password)`: the `url` argument — a string, absolute or relative, or a `URL` — gets the same rule as
 *     `fetch`; the method and every other argument reach the original `open` exactly as given; every other URL, the
 *     preference «all languages», storage that throws, and a page with no `XMLHttpRequest` at all behave as below.
 *     `fetch` is wrapped too, so a Material that moves to it keeps working.
 *   - **The `fetch` wrapper.** Loaded in the head before Material's bundle, the script replaces `window.fetch` as well. A request
 *     whose URL path ends in `/search/search_index.json` goes to `/search/search_index.<lang>.json` of the same folder,
 *     `<lang>` being the primary subtag of `<html lang>` when it is `en`, `it`, `fr` or `es`, else `en`. Material calls
 *     `fetch(new URL("search/search_index.json", base))` — a `URL` object — so the wrapper takes a string, a `URL` and a
 *     `Request`; every other argument, and the answer, pass through untouched; every other request is not touched at all.
 *     The preference «all languages» (`localStorage['lf-docs-search-all-languages'] === '1'`) leaves the request alone.
 *     Storage that throws means no preference: the current language only.
 *   - **The toggle.** Once the DOM is ready, a `<label class="lf-search-language"><input type="checkbox"
 *     data-testid="docs-search-all-languages"> <span>LABEL</span></label>` is the FIRST child of
 *     `.md-search-result[data-md-component="search-result"]` (before `.md-search-result__meta`: Material rewrites the
 *     meta's text and the list, not their siblings), inserted once, its text `LABELS[lang]`. It is checked when the
 *     preference is set. Changing it stores (`'1'`) or removes the preference, keeps the typed query in `sessionStorage`
 *     (`lf-docs-search-query`) and reloads: Material's worker indexes once per page.
 *   - **After the reload.** A stored query reopens the search — `#__search` (Material's toggle checkbox) checked, the
 *     `input[data-md-component="search-query"]` filled and an `input` event dispatched on it — and is cleared.
 *   - **No storage, no search.** A blocked storage never throws out of a handler; a page without the search dialog gets
 *     no toggle and no error.
 *
 * Storage: jsdom under this Node build exposes no usable `localStorage` (Node: «localStorage is not available because
 * --localstorage-file was not provided»), as `zodios-client.test.ts` already found. The tests own an in-memory stand-in on
 * `window` and `globalThis`, which can be told to throw; `sessionStorage` is jsdom's own.
 *
 * Waiting: the DOM is ready when the test says so (a `DOMContentLoaded` it dispatches, bubbling like the browser's);
 * what the script may do later (a reopening after `load`, a timer) is read with `expect.poll`, never with the clock.
 * The script is run again for every test, as a plain `<script>` (no `module`, `runAsBrowserScript`), on globals the test has
 * just arranged; the listeners it leaves on the shared
 * jsdom `window` and `document` are taken off after each test.
 *
 * Red today: `search-language.js` does not exist yet, so every case below is red.
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {loadScript, runAsBrowserScript, type DocsLanguage} from './__tests__/searchLanguageScript';

const PREF_KEY = 'lf-docs-search-all-languages';
const QUERY_KEY = 'lf-docs-search-query';
const TOGGLE = '[data-testid="docs-search-all-languages"]';
const LANGUAGES: DocsLanguage[] = ['en', 'it', 'fr', 'es'];

/** The part of Material's built search the script relies on: the dialog's toggle, the query field, the result area. */
const SEARCH_DOM = `
<input class="md-toggle" data-md-toggle="search" type="checkbox" id="__search" autocomplete="off">
<div class="md-search" data-md-component="search" role="dialog">
  <div class="md-search__inner" role="search">
    <form class="md-search__form" name="search">
      <input type="text" class="md-search__input" name="query" data-md-component="search-query">
    </form>
    <div class="md-search__output">
      <div class="md-search__scrollwrap" tabindex="0" data-md-scrollfix>
        <div class="md-search-result" data-md-component="search-result">
          <div class="md-search-result__meta">Type to start searching</div>
          <ol class="md-search-result__list" role="presentation"></ol>
        </div>
      </div>
    </div>
  </div>
</div>`;

/** An in-memory `localStorage` that can be told to throw, per operation, as a blocked or full storage does. */
class MemoryStorage {
    data = new Map<string, string>();
    failGet = false;
    failSet = false;
    failRemove = false;
    getItem(key: string): string | null {
        if (this.failGet) throw new DOMException('denied', 'SecurityError');
        return this.data.has(key) ? this.data.get(key)! : null;
    }
    setItem(key: string, value: string): void {
        if (this.failSet) throw new DOMException('quota', 'QuotaExceededError');
        this.data.set(key, String(value));
    }
    removeItem(key: string): void {
        if (this.failRemove) throw new DOMException('denied', 'SecurityError');
        this.data.delete(key);
    }
    clear(): void {
        this.data.clear();
    }
}

let local: MemoryStorage;
/** What `localStorage` was on each target before the stand-in: its own descriptor, `undefined` where it had none. */
let storageBefore: Array<{target: object; descriptor: PropertyDescriptor | undefined}>;

function standInStorage(value: unknown): void {
    for (const {target} of storageBefore) Object.defineProperty(target, 'localStorage', {value, configurable: true, writable: true});
}

let reloadStub: ReturnType<typeof vi.fn>;
let innerFetch: ReturnType<typeof vi.fn>;
let answer: Response;
let registered: Array<[EventTarget, string, EventListenerOrEventListenerObject]>;

beforeEach(() => {
    local = new MemoryStorage();
    storageBefore = [globalThis, window].map((target) => ({target, descriptor: Object.getOwnPropertyDescriptor(target, 'localStorage')}));
    standInStorage(local);
    reloadStub = vi.fn();
    vi.stubGlobal('location', {reload: reloadStub, href: 'http://localhost:3000/'});
    answer = new Response('{}');
    innerFetch = vi.fn(async () => answer);
    vi.stubGlobal('fetch', innerFetch);
    window.sessionStorage.clear();
    document.body.innerHTML = '';
    document.documentElement.lang = 'it';

    // Record every listener the script puts on the shared window and document, to take them off afterwards.
    registered = [];
    for (const target of [window, document] as EventTarget[]) {
        const original = target.addEventListener.bind(target);
        vi.spyOn(target, 'addEventListener').mockImplementation(((type: string, listener: EventListenerOrEventListenerObject, opts?: unknown) => {
            registered.push([target, type, listener]);
            original(type, listener, opts as never);
        }) as never);
    }
});

afterEach(() => {
    for (const [target, type, listener] of registered) target.removeEventListener(type, listener);
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    for (const {target, descriptor} of storageBefore) {
        if (descriptor) Object.defineProperty(target, 'localStorage', descriptor);
        else Reflect.deleteProperty(target, 'localStorage');
    }
    window.sessionStorage.clear();
    document.body.innerHTML = '';
    document.documentElement.removeAttribute('lang');
});

/** The URL a call of the wrapped `fetch` handed to the real one, as a string whatever it was given as. */
function forwardedUrl(call = 0): string {
    const first = innerFetch.mock.calls[call][0] as string | URL | Request;
    return typeof first === 'string' ? first : first instanceof URL ? first.href : first.url;
}

/** The browser's `DOMContentLoaded`: on the document, bubbling to the window. */
function domReady(): void {
    document.dispatchEvent(new Event('DOMContentLoaded', {bubbles: true}));
}

function toggles(): HTMLInputElement[] {
    return Array.from(document.querySelectorAll<HTMLInputElement>(TOGGLE));
}

/** Material's page, the script loaded in the head as it is, the DOM ready. */
function openPage(lang = 'it', before: () => void = () => {}): void {
    document.documentElement.lang = lang;
    document.body.innerHTML = SEARCH_DOM;
    before();
    runAsBrowserScript();
    domReady();
}

describe('the fetch wrapper', () => {
    function install(lang = 'it'): void {
        document.documentElement.lang = lang;
        runAsBrowserScript();
    }

    it('replaces window.fetch', () => {
        install();
        expect(window.fetch).not.toBe(innerFetch);
        expect(typeof window.fetch).toBe('function');
    });

    it.each([
        ['an absolute URL string', 'https://x/mkdocs/search/search_index.json', 'https://x/mkdocs/search/search_index.it.json'],
        ['a relative path with ..', '../search/search_index.json', '../search/search_index.it.json'],
        ['an absolute path with a query string', '/search/search_index.json?v=1', '/search/search_index.it.json?v=1'],
        ['a bare relative path', 'search/search_index.json', 'search/search_index.it.json'],
    ])('%s → the page’s language file', async (_label, url, expected) => {
        install('it');
        await window.fetch(url);
        expect(innerFetch).toHaveBeenCalledTimes(1);
        expect(forwardedUrl()).toBe(expected);
    });

    it('takes a URL object, as Material calls it: new URL("search/search_index.json", base)', async () => {
        install('it');
        await window.fetch(new URL('search/search_index.json', 'https://x/mkdocs/it/'));
        expect(forwardedUrl()).toBe('https://x/mkdocs/it/search/search_index.it.json');
    });

    it('takes a Request', async () => {
        install('fr');
        await window.fetch(new Request('https://x/mkdocs/search/search_index.json'));
        expect(forwardedUrl()).toBe('https://x/mkdocs/search/search_index.fr.json');
    });

    it.each([
        ['en', 'en'],
        ['it', 'it'],
        ['fr', 'fr'],
        ['es', 'es'],
        ['fr-CA', 'fr'],
        ['it-IT', 'it'],
        ['de', 'en'],
        ['', 'en'],
    ])('<html lang="%s"> → the %s index', async (lang, file) => {
        install(lang);
        await window.fetch('https://x/mkdocs/search/search_index.json');
        expect(forwardedUrl()).toBe(`https://x/mkdocs/search/search_index.${file}.json`);
    });

    it('every argument after the URL, and the answer, pass through untouched', async () => {
        install('it');
        const init = {cache: 'no-store', headers: {'x-test': '1'}} as RequestInit;
        const result = await window.fetch('https://x/mkdocs/search/search_index.json', init);
        expect(innerFetch.mock.calls[0][1]).toBe(init);
        expect(result).toBe(answer);
    });

    it.each([
        ['another file of the search folder', 'https://x/mkdocs/search/other.json'],
        ['a page', 'https://x/mkdocs/it/'],
        ['the language file itself', '/search/search_index.it.json'],
        ['the app’s API', '/api/v1/assets?x=1'],
        ['Material’s worker', '/mkdocs/assets/javascripts/workers/search.js'],
    ])('%s is not touched: same URL, same init, same answer', async (_label, url) => {
        install('it');
        const init = {method: 'GET'} as RequestInit;
        const result = await window.fetch(url, init);
        expect(innerFetch).toHaveBeenCalledTimes(1);
        expect(innerFetch.mock.calls[0][0]).toBe(url);
        expect(innerFetch.mock.calls[0][1]).toBe(init);
        expect(result).toBe(answer);
    });

    it('another request given as a Request object is handed on as the same object', async () => {
        install('it');
        const request = new Request('https://x/mkdocs/it/');
        await window.fetch(request);
        expect(innerFetch.mock.calls[0][0]).toBe(request);
    });

    it('with the preference «all languages» (1) the index request is untouched', async () => {
        window.localStorage.setItem(PREF_KEY, '1');
        install('it');
        await window.fetch('https://x/mkdocs/search/search_index.json');
        expect(forwardedUrl()).toBe('https://x/mkdocs/search/search_index.json');
    });

    it('with the preference all, a URL object is untouched too', async () => {
        window.localStorage.setItem(PREF_KEY, '1');
        install('fr');
        const url = new URL('search/search_index.json', 'https://x/mkdocs/fr/');
        await window.fetch(url);
        expect(forwardedUrl()).toBe('https://x/mkdocs/fr/search/search_index.json');
    });

    it.each(['0', '', 'true', 'yes'])('a stored value that is not 1 (%j) is not «all languages»', async (value) => {
        window.localStorage.setItem(PREF_KEY, value);
        install('it');
        await window.fetch('https://x/mkdocs/search/search_index.json');
        expect(forwardedUrl()).toBe('https://x/mkdocs/search/search_index.it.json');
    });

    it('storage whose getItem throws: no preference, the current language only', async () => {
        local.failGet = true;
        install('it');
        await window.fetch('https://x/mkdocs/search/search_index.json');
        expect(forwardedUrl()).toBe('https://x/mkdocs/search/search_index.it.json');
    });

    it('storage that cannot even be reached (the accessor throws): the same', async () => {
        for (const {target} of storageBefore) {
            Object.defineProperty(target, 'localStorage', {
                configurable: true,
                get() {
                    throw new DOMException('denied', 'SecurityError');
                },
            });
        }
        install('es');
        await window.fetch('https://x/mkdocs/search/search_index.json');
        expect(forwardedUrl()).toBe('https://x/mkdocs/search/search_index.es.json');
    });
});

describe('the XMLHttpRequest wrapper (what Material 9.7.7 really uses)', () => {
    const INDEX = 'https://x/mkdocs/search/search_index.json';
    let proto: typeof XMLHttpRequest.prototype;
    let realOpen: typeof XMLHttpRequest.prototype.open;
    let innerOpen: ReturnType<typeof vi.fn>;
    let openedOn: unknown[];

    beforeEach(() => {
        proto = XMLHttpRequest.prototype;
        realOpen = proto.open;
        openedOn = [];
        // The original `open` is a stub: nothing is ever sent, and what reaches it is what the wrapper forwarded.
        innerOpen = vi.fn(function (this: unknown) {
            openedOn.push(this);
        });
        proto.open = innerOpen as never;
    });

    afterEach(() => {
        proto.open = realOpen;
    });

    function install(lang = 'it'): void {
        document.documentElement.lang = lang;
        runAsBrowserScript();
    }

    function open(...args: unknown[]): XMLHttpRequest {
        const xhr = new XMLHttpRequest();
        (xhr.open as (...a: unknown[]) => void)(...args);
        return xhr;
    }

    /** The arguments the original `open` received on its `call`-th call, exactly as many as were passed. */
    function forwarded(call = 0): unknown[] {
        return innerOpen.mock.calls[call];
    }

    it('replaces XMLHttpRequest.prototype.open, with its marker', () => {
        install();
        expect(proto.open).not.toBe(innerOpen);
        expect(typeof proto.open).toBe('function');
        expect((proto.open as unknown as {lfSearchLanguage?: boolean}).lfSearchLanguage).toBe(true);
    });

    it.each([
        ['an absolute URL string', INDEX, 'https://x/mkdocs/search/search_index.it.json'],
        ['a relative path with ..', '../search/search_index.json', '../search/search_index.it.json'],
        ['a bare relative path', 'search/search_index.json', 'search/search_index.it.json'],
        ['an absolute path with a query string', '/search/search_index.json?v=1', '/search/search_index.it.json?v=1'],
    ])('%s → the page’s language file', (_label, url, expected) => {
        install('it');
        open('GET', url);
        expect(innerOpen).toHaveBeenCalledTimes(1);
        expect(forwarded()).toEqual(['GET', expected]);
    });

    it('takes a URL object, as a caller may give it: the original gets the language file as a string', () => {
        install('it');
        open('GET', new URL('search/search_index.json', 'https://x/mkdocs/it/'));
        expect(forwarded()).toHaveLength(2);
        expect(forwarded()[0]).toBe('GET');
        expect(String(forwarded()[1])).toBe('https://x/mkdocs/it/search/search_index.it.json');
    });

    it.each([
        ['en', 'en'],
        ['it', 'it'],
        ['fr', 'fr'],
        ['es', 'es'],
        ['fr-CA', 'fr'],
        ['it-IT', 'it'],
        ['de', 'en'],
        ['', 'en'],
    ])('<html lang="%s"> → the %s index, for the three forms', (lang, file) => {
        install(lang);
        open('GET', INDEX);
        open('GET', '../search/search_index.json');
        open('GET', new URL('search/search_index.json', 'https://x/mkdocs/'));
        expect(innerOpen).toHaveBeenCalledTimes(3);
        expect(String(forwarded(0)[1])).toBe(`https://x/mkdocs/search/search_index.${file}.json`);
        expect(String(forwarded(1)[1])).toBe(`../search/search_index.${file}.json`);
        expect(String(forwarded(2)[1])).toBe(`https://x/mkdocs/search/search_index.${file}.json`);
    });

    it('the method and the extra arguments (async, user, password) reach the original exactly', () => {
        install('it');
        open('POST', INDEX, false, 'someone', 's3cret');
        expect(forwarded()).toEqual(['POST', 'https://x/mkdocs/search/search_index.it.json', false, 'someone', 's3cret']);
        expect(forwarded()).toHaveLength(5);
    });

    it('async=true and no credentials: exactly three arguments, none added', () => {
        install('it');
        open('GET', INDEX, true);
        expect(forwarded()).toEqual(['GET', 'https://x/mkdocs/search/search_index.it.json', true]);
        expect(forwarded()).toHaveLength(3);
    });

    it('with no extra argument the original gets exactly two: nothing is padded with undefined', () => {
        install('it');
        open('GET', INDEX);
        expect(forwarded()).toHaveLength(2);
    });

    it('the original runs on the request that was opened (this), and its answer is handed back', () => {
        install('it');
        innerOpen.mockImplementationOnce(function (this: unknown) {
            openedOn.push(this);
            return 'from-original';
        });
        const xhr = new XMLHttpRequest();
        const result = (xhr.open as (...a: unknown[]) => unknown)('GET', INDEX);
        expect(openedOn).toEqual([xhr]);
        expect(result).toBe('from-original');
    });

    it('a call with only the method does not throw and reaches the original as it is', () => {
        install('it');
        expect(() => open('GET')).not.toThrow();
        expect(forwarded()).toEqual(['GET']);
    });

    it.each([
        ['another file of the search folder', 'https://x/mkdocs/search/other.json'],
        ['a page', 'https://x/mkdocs/it/'],
        ['the language file itself (already rewritten)', '/search/search_index.it.json'],
        ['the app’s API', '/api/v1/assets?x=1'],
        ['a script of the site', '/mkdocs/assets/x.js'],
        ['Material’s worker', '/mkdocs/assets/javascripts/workers/search.js'],
    ])('%s is not touched: same method, same URL, same extra arguments', (_label, url) => {
        install('it');
        open('GET', url, true, 'u', 'p');
        expect(forwarded()).toEqual(['GET', url, true, 'u', 'p']);
    });

    it('another URL given as a URL object reaches the original unchanged', () => {
        install('it');
        const url = new URL('https://x/mkdocs/assets/x.js');
        open('GET', url);
        expect(String(forwarded()[1])).toBe('https://x/mkdocs/assets/x.js');
    });

    it('with the preference «all languages» (1) the index request is untouched, in the three forms', () => {
        window.localStorage.setItem(PREF_KEY, '1');
        install('it');
        open('GET', INDEX, true, 'u', 'p');
        open('GET', '../search/search_index.json');
        open('GET', new URL('search/search_index.json', 'https://x/mkdocs/fr/'));
        expect(forwarded(0)).toEqual(['GET', INDEX, true, 'u', 'p']);
        expect(forwarded(1)).toEqual(['GET', '../search/search_index.json']);
        expect(String(forwarded(2)[1])).toBe('https://x/mkdocs/fr/search/search_index.json');
    });

    it.each(['0', '', 'true', 'yes'])('a stored value that is not 1 (%j) is not «all languages»', (value) => {
        window.localStorage.setItem(PREF_KEY, value);
        install('it');
        open('GET', INDEX);
        expect(forwarded()).toEqual(['GET', 'https://x/mkdocs/search/search_index.it.json']);
    });

    it('storage whose getItem throws: no preference, the current language only', () => {
        local.failGet = true;
        install('it');
        open('GET', INDEX);
        expect(forwarded()).toEqual(['GET', 'https://x/mkdocs/search/search_index.it.json']);
    });

    it('storage that cannot even be reached (the accessor throws): the same', () => {
        for (const {target} of storageBefore) {
            Object.defineProperty(target, 'localStorage', {
                configurable: true,
                get() {
                    throw new DOMException('denied', 'SecurityError');
                },
            });
        }
        install('es');
        open('GET', INDEX);
        expect(forwarded()).toEqual(['GET', 'https://x/mkdocs/search/search_index.es.json']);
    });

    it('installXhrRewriter is installed once: a second call leaves the first wrapper in place and the original runs once per open', () => {
        document.documentElement.lang = 'it';
        const {installXhrRewriter} = loadScript() as unknown as {installXhrRewriter: () => void};
        installXhrRewriter();
        const first = proto.open;
        expect(first).not.toBe(innerOpen);
        installXhrRewriter();
        installXhrRewriter();
        // a second wrapper would be a new function around the first
        expect(proto.open).toBe(first);
        open('GET', INDEX);
        expect(innerOpen).toHaveBeenCalledTimes(1);
        expect(forwarded()).toEqual(['GET', 'https://x/mkdocs/search/search_index.it.json']);
    });

    it('running the script again on a page that already has the wrapper does not wrap it again', () => {
        install('it');
        const first = proto.open;
        runAsBrowserScript();
        expect(proto.open).toBe(first);
        open('GET', INDEX);
        expect(innerOpen).toHaveBeenCalledTimes(1);
    });

    it('the wrapper follows the page’s language at the time of the call, not at install', () => {
        install('it');
        document.documentElement.lang = 'fr';
        open('GET', INDEX);
        expect(forwarded()).toEqual(['GET', 'https://x/mkdocs/search/search_index.fr.json']);
    });

    it('a page with no XMLHttpRequest global: installXhrRewriter does not throw and wraps nothing', () => {
        document.documentElement.lang = 'it';
        const {installXhrRewriter} = loadScript() as unknown as {installXhrRewriter: () => void};
        vi.stubGlobal('XMLHttpRequest', undefined);
        expect(() => installXhrRewriter()).not.toThrow();
        expect(proto.open).toBe(innerOpen);
    });

    it('a page with no XMLHttpRequest global: the whole script still starts, fetch is wrapped and the toggle is built', () => {
        vi.stubGlobal('XMLHttpRequest', undefined);
        expect(() => openPage('it')).not.toThrow();
        expect(window.fetch).not.toBe(innerFetch);
        expect(toggles()).toHaveLength(1);
    });

    it('a real XMLHttpRequest of jsdom: open with the index URL reaches the original with the rewritten URL, nothing is sent', () => {
        install('fr');
        const xhr = new XMLHttpRequest();
        xhr.open('GET', 'http://localhost:3000/mkdocs/search/search_index.json');
        expect(innerOpen).toHaveBeenCalledTimes(1);
        expect(forwarded()).toEqual(['GET', 'http://localhost:3000/mkdocs/search/search_index.fr.json']);
        expect(openedOn).toEqual([xhr]);
        // the stub opened nothing: the request is still in its initial state
        expect(xhr.readyState).toBe(XMLHttpRequest.UNSENT);
    });

    it('runAsBrowserScript installs the XHR wrapper together with the fetch one', () => {
        install('es');
        expect((proto.open as unknown as {lfSearchLanguage?: boolean}).lfSearchLanguage).toBe(true);
        expect((window.fetch as unknown as {lfSearchLanguage?: boolean}).lfSearchLanguage).toBe(true);
    });
});

describe('the toggle', () => {
    it('is one checkbox with the test id, in a label of class lf-search-language', () => {
        openPage('it');
        const found = toggles();
        expect(found).toHaveLength(1);
        expect(found[0].type).toBe('checkbox');
        const label = found[0].closest('label');
        expect(label).not.toBeNull();
        expect(label!.classList.contains('lf-search-language')).toBe(true);
    });

    it('is the FIRST child of the search result area, before the meta line', () => {
        openPage('it');
        const result = document.querySelector('.md-search-result[data-md-component="search-result"]')!;
        const label = toggles()[0].closest('label');
        expect(result.firstElementChild).toBe(label);
        expect(label!.nextElementSibling?.classList.contains('md-search-result__meta')).toBe(true);
    });

    it.each(LANGUAGES)('its text is the label of the page’s language (%s)', async (lang) => {
        openPage(lang);
        const {LABELS} = loadScript();
        const label = toggles()[0].closest('label')!;
        expect(label.textContent!.trim()).toBe(LABELS[lang]);
        expect(label.querySelector('span')?.textContent).toBe(LABELS[lang]);
    });

    it('a language the site does not have gets the English label', () => {
        openPage('de');
        const {LABELS} = loadScript();
        expect(toggles()[0].closest('label')!.textContent!.trim()).toBe(LABELS.en);
    });

    it('is unchecked by default', () => {
        openPage('it');
        expect(toggles()[0].checked).toBe(false);
    });

    it('is checked when the preference «all languages» is stored', () => {
        openPage('it', () => window.localStorage.setItem(PREF_KEY, '1'));
        expect(toggles()[0].checked).toBe(true);
    });

    it('is inserted once, however many times the DOM is announced ready', () => {
        openPage('it');
        domReady();
        domReady();
        window.dispatchEvent(new Event('load'));
        expect(toggles()).toHaveLength(1);
        expect(document.querySelectorAll('label.lf-search-language')).toHaveLength(1);
    });

    it('checking it stores the preference, keeps the typed query and reloads', () => {
        openPage('it');
        document.querySelector<HTMLInputElement>('input[data-md-component="search-query"]')!.value = 'backup';
        toggles()[0].click();
        expect(window.localStorage.getItem(PREF_KEY)).toBe('1');
        expect(window.sessionStorage.getItem(QUERY_KEY)).toBe('backup');
        expect(reloadStub).toHaveBeenCalledTimes(1);
    });

    it('unchecking it removes the preference, keeps the typed query and reloads', () => {
        openPage('it', () => window.localStorage.setItem(PREF_KEY, '1'));
        document.querySelector<HTMLInputElement>('input[data-md-component="search-query"]')!.value = 'sharpe';
        toggles()[0].click();
        expect(window.localStorage.getItem(PREF_KEY)).toBeNull();
        expect(window.sessionStorage.getItem(QUERY_KEY)).toBe('sharpe');
        expect(reloadStub).toHaveBeenCalledTimes(1);
    });

    it('does not reload before anyone changes it', () => {
        openPage('it');
        expect(reloadStub).not.toHaveBeenCalled();
    });

    it('a stored query reopens the search: the dialog checked, the field filled, an input event, the query cleared', async () => {
        const inputs: string[] = [];
        openPage('it', () => {
            window.sessionStorage.setItem(QUERY_KEY, 'backup');
            document.querySelector('input[data-md-component="search-query"]')!.addEventListener('input', (event) => inputs.push((event.target as HTMLInputElement).value));
        });
        // The reopening may wait for the page's `load`: announce it too, as the browser would.
        window.dispatchEvent(new Event('load'));
        const field = document.querySelector<HTMLInputElement>('input[data-md-component="search-query"]')!;
        await expect.poll(() => document.querySelector<HTMLInputElement>('#__search')!.checked, {message: 'Material’s search dialog is open again'}).toBe(true);
        await expect.poll(() => field.value, {message: 'the typed query is back in the field'}).toBe('backup');
        await expect.poll(() => inputs, {message: 'Material is told through an input event carrying the query'}).toContain('backup');
        await expect.poll(() => window.sessionStorage.getItem(QUERY_KEY), {message: 'the stored query is spent'}).toBeNull();
    });

    it('with no stored query the search stays closed and the field empty', async () => {
        openPage('it');
        window.dispatchEvent(new Event('load'));
        // A presence barrier first, so the absence below is not just a script that has not run.
        expect(toggles()).toHaveLength(1);
        await expect.poll(() => document.querySelector<HTMLInputElement>('#__search')!.checked).toBe(false);
        expect(document.querySelector<HTMLInputElement>('input[data-md-component="search-query"]')!.value).toBe('');
    });

    it('a blocked storage never throws out of the change handler', () => {
        const errors: unknown[] = [];
        const onError = (event: ErrorEvent) => errors.push(event.error ?? event.message);
        window.addEventListener('error', onError);
        try {
            openPage('it');
            local.failSet = true;
            local.failRemove = true;
            vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
                throw new DOMException('quota', 'QuotaExceededError');
            });
            toggles()[0].click();
            toggles()[0].click();
        } finally {
            window.removeEventListener('error', onError);
        }
        expect(errors).toEqual([]);
    });

    it('a blocked storage at load: the toggle is still there, unchecked, and nothing throws', () => {
        local.failGet = true;
        expect(() => openPage('it')).not.toThrow();
        expect(toggles()).toHaveLength(1);
        expect(toggles()[0].checked).toBe(false);
    });

    it('a page without the search dialog gets no toggle and no error', () => {
        document.documentElement.lang = 'it';
        document.body.innerHTML = '<main><p>not a Material page</p></main>';
        runAsBrowserScript();
        expect(() => domReady()).not.toThrow();
        expect(toggles()).toHaveLength(0);
    });
});
