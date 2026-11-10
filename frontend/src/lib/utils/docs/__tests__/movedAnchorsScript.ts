/**
 * Loads `mkdocs_src/docs/javascripts/moved-anchors.js` — a classic browser script outside `src/` and outside the bundle —
 * for the two specs beside it (`movedAnchors.test.ts`, `movedAnchors.dom.test.ts`), the way `searchLanguageScript.ts` loads
 * `search-language.js`: the file is read as text and run as a function body, in THIS context, so whatever `window`,
 * `document` and `location` exist when it runs are the ones it uses. Every call runs the file again, from the text.
 *
 *   - `loadScript()`: with a CommonJS-like `module`, as the script promises («exported through `module.exports` when
 *     `typeof module !== 'undefined'`»). It returns the exports; the script does not touch the page in that host.
 *   - `runAsBrowserScript()`: with NO `module` in scope, as a `<script>` tag runs it: on a page whose address carries a moved
 *     anchor the script calls `location.replace(...)`.
 *
 * `MOVED_ANCHORS_SCRIPT` (an absolute path in the environment) points both at another file: the mutant check runs the specs
 * against copies of the script with one defect each, never against an edited original.
 */
import {readFileSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

/** `frontend/`: this file is `frontend/src/lib/utils/docs/__tests__/`. */
const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '../../../../..');

/** The script under test, as MkDocs publishes it from `docs/javascripts/`. */
export const SCRIPT_PATH = process.env.MOVED_ANCHORS_SCRIPT ?? resolve(FRONTEND, '../mkdocs_src/docs/javascripts/moved-anchors.js');

export type MovedMap = Record<string, Record<string, string>>;

export interface MovedAnchorsExports {
    MOVED_ANCHORS: MovedMap;
    adminPage: (pathname: string) => string | null;
    movedTarget: (pathname: string, hash: string | null | undefined, map: MovedMap, hasAnchor?: (anchor: string) => boolean) => string | null;
}

/** The source text of the script. */
export function scriptSource(): string {
    return readFileSync(SCRIPT_PATH, 'utf8');
}

/** Runs the script once on the current globals; returns what it put on `module.exports`. */
export function loadScript(): MovedAnchorsExports {
    const module: {exports: Record<string, unknown>} = {exports: {}};
    // A function body, not an ES module: `new Function` is the host a `<script>` tag approximates here.
    const run = new Function('module', 'exports', scriptSource());
    run.call(globalThis, module, module.exports);
    return module.exports as unknown as MovedAnchorsExports;
}

/** Runs the script as the browser does, a plain script with no `module`: it reads the address and may redirect. */
export function runAsBrowserScript(): void {
    // `module` is a parameter left undefined: `typeof module` inside the script is `'undefined'`, as on a page.
    const run = new Function('module', scriptSource());
    run.call(globalThis, undefined);
}
