/**
 * Documentation search by language (lot DOC-2).
 *
 * MkDocs builds one search index for every language of the site, 10 MB that a visitor downloads whole and that mixes the
 * four versions of each page. `hooks/search_language_split.py` writes one index per language after the build
 * (`search/search_index.<lang>.json`); this script makes Material ask for the one of the page's language, and puts a
 * checkbox in the search dialog, «search the other languages too», that asks for the full index instead.
 *
 * Material 9.7.7 loads the index with `XMLHttpRequest` (the browser lists it as `xmlhttprequest`, not `fetch`), so both
 * `XMLHttpRequest.prototype.open` and `fetch` are wrapped: a Material that moves to `fetch` keeps working.
 *
 * It must run BEFORE Material's bundle, which starts loading the index as soon as it loads: `overrides/main.html` loads
 * it from `<head>`. No dependency; every access to a storage is in a `try`, and without one the page shows its own language
 * only.
 */
(function (root) {
    'use strict';

    var LANGUAGES = ['en', 'it', 'fr', 'es'];
    var ALL_LANGUAGES_KEY = 'lf-docs-search-all-languages';
    var QUERY_KEY = 'lf-docs-search-query';
    var INDEX_PATH = /(^|\/)search\/search_index\.json$/;

    /** The label of the checkbox, in the language of the page. */
    var LABELS = {
        en: 'Search the other languages too',
        it: 'Cerca anche nelle altre lingue',
        fr: 'Chercher aussi dans les autres langues',
        es: 'Buscar también en los otros idiomas',
    };

    /** The language of the page: the primary subtag of `<html lang>` when the site has it, English otherwise. */
    function currentLanguage(lang) {
        var primary = String(lang || '')
            .toLowerCase()
            .split(/[-_]/)[0];
        return LANGUAGES.indexOf(primary) >= 0 ? primary : 'en';
    }

    /**
     * Where Material's request for the index goes: the language's own file, in the same folder, unless every language is
     * wanted. Any other address, and the query string or hash of the index's, come back as they were.
     */
    function searchIndexUrl(url, lang, allLanguages) {
        var text = String(url);
        if (allLanguages) return text;
        var parts = /^([^?#]*)([\s\S]*)$/.exec(text);
        if (!INDEX_PATH.test(parts[1])) return text;
        return parts[1].replace(/search_index\.json$/, 'search_index.' + currentLanguage(lang) + '.json') + parts[2];
    }

    function readStorage(storage, key) {
        try {
            return storage ? storage.getItem(key) : null;
        } catch (e) {
            return null;
        }
    }

    function writeStorage(storage, key, value) {
        try {
            if (!storage) return;
            if (value === null) storage.removeItem(key);
            else storage.setItem(key, value);
        } catch (e) {
            /* no storage: the choice lasts until the page is left */
        }
    }

    function storageOf(kind) {
        try {
            return root[kind];
        } catch (e) {
            return undefined;
        }
    }

    function wantsAllLanguages() {
        return readStorage(storageOf('localStorage'), ALL_LANGUAGES_KEY) === '1';
    }

    /** The address a request for the index goes to, for the page's language and the stored preference. */
    function addressFor(from) {
        return searchIndexUrl(from, root.document && root.document.documentElement.lang, wantsAllLanguages());
    }

    /** Wrap `fetch`: the request for the full index asks for the page's language instead. Installed once. */
    function installFetchRewriter() {
        if (typeof root.fetch !== 'function' || root.fetch.lfSearchLanguage) return;
        var original = root.fetch;
        var rewriter = function (input, init) {
            var isRequest = typeof Request !== 'undefined' && input instanceof Request;
            var from = isRequest ? input.url : String(input);
            var to = addressFor(from);
            if (to !== from) input = isRequest ? new Request(to, input) : to;
            return original.call(this, input, init);
        };
        rewriter.lfSearchLanguage = true;
        root.fetch = rewriter;
    }

    /** Wrap `XMLHttpRequest.prototype.open` (what Material uses): same rule, the other arguments pass through. Installed once. */
    function installXhrRewriter() {
        var Xhr = root.XMLHttpRequest;
        if (typeof Xhr !== 'function' || !Xhr.prototype || typeof Xhr.prototype.open !== 'function' || Xhr.prototype.open.lfSearchLanguage) return;
        var original = Xhr.prototype.open;
        var open = function (method, url) {
            var args = Array.prototype.slice.call(arguments);
            if (args.length >= 2) {
                var from = String(url);
                var to = addressFor(from);
                if (to !== from) args[1] = to;
            }
            return original.apply(this, args);
        };
        open.lfSearchLanguage = true;
        Xhr.prototype.open = open;
    }

    function searchInput() {
        return root.document.querySelector('input[data-md-component="search-query"]');
    }

    /** The checkbox, first in the result area of Material's search dialog (Material rewrites the meta line and the list, not it). */
    function addToggle() {
        var doc = root.document;
        var results = doc.querySelector('[data-md-component="search-result"]');
        if (!results || results.querySelector('.lf-search-language')) return;
        var label = doc.createElement('label');
        label.className = 'lf-search-language';
        var box = doc.createElement('input');
        box.type = 'checkbox';
        box.checked = wantsAllLanguages();
        box.setAttribute('data-testid', 'docs-search-all-languages');
        var text = doc.createElement('span');
        text.textContent = LABELS[currentLanguage(doc.documentElement.lang)];
        label.appendChild(box);
        label.appendChild(text);
        results.insertBefore(label, results.firstChild);
        box.addEventListener('change', function () {
            writeStorage(storageOf('localStorage'), ALL_LANGUAGES_KEY, box.checked ? '1' : null);
            var input = searchInput();
            // Material prepares its search once per page: the page loads again, and the query is put back
            writeStorage(storageOf('sessionStorage'), QUERY_KEY, input ? input.value : '');
            root.location.reload();
        });
    }

    /** After the reload of the checkbox: open the search again with what the user had typed. */
    function reopenSearch() {
        var session = storageOf('sessionStorage');
        var query = readStorage(session, QUERY_KEY);
        if (query === null) return;
        writeStorage(session, QUERY_KEY, null);
        var doc = root.document;
        var toggle = doc.getElementById('__search');
        var input = searchInput();
        if (!toggle || !input) return;
        toggle.checked = true;
        toggle.dispatchEvent(new Event('change', {bubbles: true}));
        if (query !== '') {
            input.value = query;
            input.dispatchEvent(new Event('input', {bubbles: true}));
        }
        input.focus();
    }

    function start() {
        installFetchRewriter();
        installXhrRewriter();
        if (!root.document) return;
        var ready = function () {
            addToggle();
            // Material mounts its components once its own scripts have run
            root.setTimeout(reopenSearch, 0);
        };
        if (root.document.readyState === 'loading') root.document.addEventListener('DOMContentLoaded', ready);
        else ready();
    }

    var api = {LANGUAGES: LANGUAGES, LABELS: LABELS, currentLanguage: currentLanguage, searchIndexUrl: searchIndexUrl, installFetchRewriter: installFetchRewriter, installXhrRewriter: installXhrRewriter};
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    else start();
})(typeof window !== 'undefined' ? window : globalThis);
