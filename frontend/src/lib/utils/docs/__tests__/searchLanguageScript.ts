/**
 * Loads `mkdocs_src/docs/javascripts/search-language.js` — a classic browser script outside `src/` and outside the
 * bundle — for the two specs beside it (`searchLanguage.test.ts`, `searchLanguage.dom.test.ts`).
 *
 * The file is read as text and run as a function body, in THIS context: whatever `window`, `document`, `localStorage` and
 * `fetch` exist when it runs are the ones it uses, a node host without them included. Every call runs the file again,
 * from the text, so each test gets a script of its own on the globals it has just arranged. Two ways to run it:
 *
 *   - `loadScript()`: with a CommonJS-like `module`, as the contract promises («the pure functions are exported through
 *     `module.exports` when `typeof module !== 'undefined'`»). It returns the exports. Whether a script in that host also
 *     wires itself to the page is the script's business: the specs do not read it either way.
 *   - `runAsBrowserScript()`: with NO `module` in scope, as a `<script>` tag runs it: the script wraps `window.fetch` and
 *     `XMLHttpRequest.prototype.open` (Material 9.7.7 loads the index with XHR) and wires the toggle. This is what the page
 *     does, and what the XHR, `fetch` and toggle specs observe.
 */
import {readFileSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

/** `frontend/`: this file is `frontend/src/lib/utils/docs/__tests__/`. */
const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '../../../../..');

/** The script under test, as MkDocs publishes it from `docs/javascripts/`. */
export const SCRIPT_PATH = resolve(FRONTEND, '../mkdocs_src/docs/javascripts/search-language.js');

/** The four languages of the documentation, the default first. */
export type DocsLanguage = 'en' | 'it' | 'fr' | 'es';

export interface SearchLanguageExports {
    searchIndexUrl: (url: string, lang: string, allLanguages: boolean) => string;
    currentLanguage: (lang: string | null | undefined) => DocsLanguage;
    LABELS: Record<DocsLanguage, string>;
    installFetchRewriter: () => void;
    installXhrRewriter: () => void;
}

/** The source text of the script. */
export function scriptSource(): string {
    return readFileSync(SCRIPT_PATH, 'utf8');
}

/** Runs the script once on the current globals; returns what it put on `module.exports`. */
export function loadScript(): SearchLanguageExports {
    const module: {exports: Record<string, unknown>} = {exports: {}};
    // A function body, not an ES module: `new Function` is the host a `<script>` tag approximates here.
    const run = new Function('module', 'exports', scriptSource());
    run.call(globalThis, module, module.exports);
    return module.exports as unknown as SearchLanguageExports;
}

/** Runs the script as the browser does, a plain script with no `module`: it installs its `fetch` and XHR wrappers and its toggle. */
export function runAsBrowserScript(): void {
    // `module` is a parameter left undefined: `typeof module` inside the script is `'undefined'`, as on a page.
    const run = new Function('module', scriptSource());
    run.call(globalThis, undefined);
}
