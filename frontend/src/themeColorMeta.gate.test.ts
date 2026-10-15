/**
 * Gate: the PWA title bar has one light/dark colour pair, and every copy of it agrees (colour workstream R, D3).
 *
 * ## What this protects
 *
 * `<meta name="theme-color">` colours the browser chrome around the app — the window of the installed PWA, the
 * address bar on a phone — and the app rewrites it on every theme so that the chrome continues the sidebar. Three
 * places write it, and they cannot share a module:
 *
 *   - `src/app.html`, the anti-FOUC inline script: it runs before any bundle is loaded;
 *   - `applyTheme()` in `src/lib/stores/app/themeStore.ts`: every theme switch inside the app;
 *   - `static/offline.html`, the page the service worker serves when the server cannot be reached: a static file with
 *     a script of its own.
 *
 * So the pair is copied by hand, and a copy drifts without anybody seeing it. One did: the dark value was `#156534`,
 * one digit away from the sidebar's `#166534`, in all three copies, until R corrected it (the developer's decision D3,
 * 14/10/2026). Two greens one digit apart do not look different — which is exactly why nobody noticed, and why a test
 * has to.
 *
 * ## The rule, as this file checks it
 *
 *   (a) Each of the three sources picks the colour with exactly one `<theme> === 'dark' ? '<dark>' : '<light>'` ternary
 *       (or its `'light'` mirror) and looks the meta up exactly once. This is the positive control of everything
 *       below: a statement renamed, moved or rewritten in a form the scanner does not read shows here as 0, loudly,
 *       instead of leaving (b) to compare nothing.
 *   (b) The three pairs are one pair, and it is the pair D3 settled: light `#1a4031`, dark `#166534`.
 *   (c) Before any script has run, the light value is what shows: it is the static `content` of the meta in both
 *       documents, and the `theme_color` of `static/manifest.json`.
 *   (d) The pair is the sidebar's, as the comments beside it in `app.html` and `themeStore.ts` say: light is
 *       `--color-libre-green` in the `@theme` of `src/app.css`, dark is the background of `html.dark .bg-libre-green`
 *       (the sidebar is drawn with `bg-libre-green`). This is the drift D3 corrected, seen from the other side: should
 *       the sidebar change colour and the title bar not follow, (b) alone would stay green.
 *   (e) Nothing else writes the meta: no other source under `src`, and no other page or script of `static`, names it.
 *       A fourth copy would sit outside (a)–(b).
 *
 * Colours are compared case-insensitively (`#1A4031` is the same colour) and found by content, never by line, so an
 * unrelated edit above a statement cannot turn the gate red.
 *
 * ## What it cannot see
 *
 * It reads source text, not a browser: what the chrome finally shows is not observed here. The scanner knows the
 * ternary on a string `'dark'` / `'light'` choosing between two hex literals; a pair written another way (a lookup
 * table, two variables) is not recognised — and then (a) fails, which is the point. (e) finds the meta by its name,
 * `theme-color`, in code outside comments, so a name assembled at run time would pass it; and comment blanking is the
 * floor: a `//` inside a string swallows the rest of its line.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */

import {describe, expect, it} from 'vitest';
import {readdirSync, readFileSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

/** `frontend/`: every path is read, and reported, relative to it. */
const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '..');

const APP_HTML = 'src/app.html';
const THEME_STORE = 'src/lib/stores/app/themeStore.ts';
const OFFLINE_HTML = 'static/offline.html';
const MANIFEST = 'static/manifest.json';
const APP_CSS = 'src/app.css';

/** The three sources that write the meta on every theme. */
const SOURCES = [APP_HTML, THEME_STORE, OFFLINE_HTML];

interface Pair {
    light: string;
    dark: string;
}

/** The pair D3 settled on (14/10/2026): the sidebar's two greens. */
const PAIR: Pair = {light: '#1a4031', dark: '#166534'};

// ---------------------------------------------------------------------------
// Reading
// ---------------------------------------------------------------------------

const read = (path: string): string => readFileSync(join(FRONTEND, path), 'utf8');
const lineAt = (text: string, offset: number): number => text.slice(0, offset).split('\n').length;
const collapse = (s: string): string => s.trim().replace(/\s+/g, ' ');
const isMarkup = (file: string): boolean => file.endsWith('.html') || file.endsWith('.svelte');

/** Replace every match with spaces, keeping newlines: offsets and line numbers survive the blanking. */
function blank(text: string, pattern: RegExp): string {
    return text.replace(pattern, (found) => found.replace(/[^\n]/g, ' '));
}

const blankCssComments = (css: string): string => blank(css, /\/\*[\s\S]*?\*\//g);
/** `//` counts as a comment only when it does not follow `:` — `https://` stays code. */
const blankJsComments = (js: string): string => blank(blank(js, /\/\*[\s\S]*?\*\//g), /(?<![:\\])\/\/[^\n]*/g);

/** A file with its comments blanked the way the file type means them: markup, scripts and styles each by their own syntax. */
function codeOf(file: string, text: string): string {
    if (!isMarkup(file)) return blankJsComments(text);
    let out = blank(text, /<!--[\s\S]*?-->/g);
    out = out.replace(/(<script\b[^>]*>)([\s\S]*?)(<\/script\s*>)/gi, (_m, open: string, body: string, close: string) => open + blankJsComments(body) + close);
    out = out.replace(/(<style\b[^>]*>)([\s\S]*?)(<\/style\s*>)/gi, (_m, open: string, body: string, close: string) => open + blankCssComments(body) + close);
    return out;
}

/** The script code of a file: all of a `.ts`, only the `<script>` bodies of markup — everything else blanked. */
function scriptOf(file: string, text: string): string {
    const code = codeOf(file, text);
    if (!isMarkup(file)) return code;
    let out = '';
    let last = 0;
    for (const match of code.matchAll(/(<script\b[^>]*>)([\s\S]*?)<\/script\s*>/gi)) {
        const bodyStart = match.index + match[1].length;
        out += code.slice(last, bodyStart).replace(/[^\n]/g, ' ') + match[2];
        last = bodyStart + match[2].length;
    }
    return out + code.slice(last).replace(/[^\n]/g, ' ');
}

/** The markup of a document only: comments blanked, and the bodies of its scripts and styles too. */
function markupOf(file: string, text: string): string {
    return codeOf(file, text).replace(/(<(script|style)\b[^>]*>)([\s\S]*?)(<\/\2\s*>)/gi, (_m, open: string, _tag: string, body: string, close: string) => open + body.replace(/[^\n]/g, ' ') + close);
}

// ---------------------------------------------------------------------------
// What the scanner reads
// ---------------------------------------------------------------------------

/** `<subject> === 'dark' ? '<hex>' : '<hex>'`, or the `'light'` mirror; `==` or `===`, either quote style. */
const PAIR_TERNARY = /[\w$.]+\s*===?\s*(['"])(dark|light)\1\s*\?\s*(['"])(#[0-9a-f]{3,8})\3\s*:\s*(['"])(#[0-9a-f]{3,8})\5/gi;

/** The meta's name as code writes it — not the `--theme-color` custom property of the image cropper. */
const META_NAME = /(?<![\w-])theme-color(?![\w-])/gi;

interface FoundPair extends Pair {
    file: string;
    line: number;
}

/** Every dark/light pair the script code of a file picks a colour with, hex digits in lower case. */
function pairsIn(file: string, text: string): FoundPair[] {
    const code = scriptOf(file, text);
    return [...code.matchAll(PAIR_TERNARY)].map((match) => {
        const [first, second] = [match[4].toLowerCase(), match[6].toLowerCase()];
        const darkFirst = match[2].toLowerCase() === 'dark';
        return {file, line: lineAt(code, match.index), light: darkFirst ? second : first, dark: darkFirst ? first : second};
    });
}

/** The single pair of a source; more or fewer is (a)'s failure, reported here with the same words. */
function theOnePairOf(file: string): FoundPair {
    const found = pairsIn(file, read(file));
    if (found.length !== 1) throw new Error(`${file}: expected exactly one dark/light pair, found ${found.length} — see (a)`);
    return found[0];
}

const describePair = (pair: FoundPair): string => `${pair.file}:${pair.line}  light ${pair.light}, dark ${pair.dark}`;

/** The `content` of every `<meta name="theme-color">` in the markup of a document, lower case; comments and scripts ignored. */
function staticMetaContentsIn(file: string, text: string): string[] {
    const contents: string[] = [];
    for (const tag of markupOf(file, text).matchAll(/<meta\b[^>]*>/gi)) {
        const attrs: Record<string, string> = {};
        for (const attr of tag[0].matchAll(/([\w-]+)\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/g)) attrs[attr[1].toLowerCase()] = attr[2].replace(/^(['"])([\s\S]*)\1$/, '$2');
        if ((attrs.name ?? '').toLowerCase() === 'theme-color') contents.push((attrs.content ?? '').trim().toLowerCase());
    }
    return contents;
}

/** The innermost rules of a stylesheet — the blocks that hold no other block — with their prelude, comments blanked. */
function leafRulesOf(css: string): Array<{prelude: string; body: string}> {
    return [...blankCssComments(css).matchAll(/([^{}]*)\{([^{}]*)\}/g)].map((match) => ({prelude: collapse(match[1].split(';').pop() ?? ''), body: match[2]}));
}

/** The values a rule body gives `prop`, `!important` dropped, lower case. */
function valuesOf(body: string, prop: string): string[] {
    return body.split(';').flatMap((declaration) => {
        const match = /^\s*([\w-]+)\s*:([\s\S]*)$/.exec(declaration);
        return match && match[1].toLowerCase() === prop ? [collapse(match[2].replace(/!\s*important\s*$/i, '')).toLowerCase()] : [];
    });
}

/** The sidebar's two greens as a stylesheet declares them: `--color-libre-green` in `@theme`, and the background `html.dark .bg-libre-green` forces. */
function sidebarGreensIn(css: string): {light: string[]; dark: string[]} {
    const rules = leafRulesOf(css);
    return {
        light: rules.filter((rule) => /^@theme\b/.test(rule.prelude)).flatMap((rule) => valuesOf(rule.body, '--color-libre-green')),
        dark: rules.filter((rule) => rule.prelude === 'html.dark .bg-libre-green').flatMap((rule) => valuesOf(rule.body, 'background-color')),
    };
}

/** Whether a path (relative to `frontend/`) is shipped code this gate reads: no test, no mock. */
function isScanned(path: string): boolean {
    if (!/\.(ts|js|svelte|html)$/.test(path) || /\.(test|spec)\.(ts|js)$/.test(path)) return false;
    return !path.split('/').some((segment) => segment === '__tests__' || segment === '__mocks__' || segment === 'node_modules');
}

function walk(dir: string, recursive: boolean, acc: string[] = []): string[] {
    for (const entry of readdirSync(join(FRONTEND, dir), {withFileTypes: true})) {
        const path = `${dir}/${entry.name}`;
        if (entry.isDirectory()) {
            if (recursive) walk(path, true, acc);
        } else if (isScanned(path)) acc.push(path);
    }
    return acc;
}

/** Everything `src` ships, plus the pages and scripts at the top of `static` (the offline page, the service worker). */
const scannedFiles = (): string[] => [...walk('src', true), ...walk('static', false)];

// ---------------------------------------------------------------------------
// The gate
// ---------------------------------------------------------------------------

describe('PWA theme-color — one light/dark pair, the same in every copy (R, D3 gate)', () => {
    describe('the scanner', () => {
        it('reads the ternary in either orientation and quote style, inside scripts only, and ignores comments', () => {
            const pairs = (file: string, text: string): string[] => pairsIn(file, text).map(({light, dark}) => `light ${light}, dark ${dark}`);
            const D3 = 'light #1a4031, dark #166534';

            expect(pairs('a.ts', "const themeColor = resolved === 'dark' ? '#166534' : '#1a4031';")).toEqual([D3]);
            expect(pairs('a.ts', 'const c = mode == "light" ? "#1A4031" : "#166534";')).toEqual([D3]);
            expect(pairs('a.html', "<script>\n    if (meta) meta.setAttribute('content', theme === 'dark' ? '#166534' : '#1a4031');\n</script>")).toEqual([D3]);

            // Look-alikes: a pair in a comment of any kind, or in markup outside a script, writes nothing.
            expect(pairs('a.ts', "// theme === 'dark' ? '#156534' : '#1a4031'\n/* theme === 'dark' ? '#156534' : '#1a4031' */")).toEqual([]);
            expect(pairs('a.html', "<!-- <script>x = theme === 'dark' ? '#156534' : '#1a4031';</script> -->\n<p>theme === 'dark' ? '#156534' : '#1a4031'</p>")).toEqual([]);
            expect(pairs('a.html', "<script>\n    // meta.setAttribute('content', theme === 'dark' ? '#156534' : '#1a4031');\n</script>")).toEqual([]);
        });

        it('reads the static meta whatever its attribute order, and not when it is commented out', () => {
            expect(staticMetaContentsIn('a.html', '<meta content="#1A4031" name="theme-color" />\n<!-- <meta name="theme-color" content="#156534" /> -->\n<meta name="viewport" content="width=device-width" />')).toEqual(['#1a4031']);
        });

        it("finds the sidebar's two greens in a stylesheet: comments, nesting and look-alike selectors aside", () => {
            const css = [
                "@import 'x';",
                '/* html.dark .bg-libre-green { background-color: #000; } */',
                '@theme {',
                '    --color-libre-green: #1A4031;',
                '}',
                '@media (min-width: 1px) {',
                '    p { color: red; }',
                '}',
                'html.dark .bg-libre-green-soft { background-color: #000; }',
                'html.dark .bg-libre-green {',
                '    background-color: #166534 !important;',
                '}',
            ].join('\n');
            expect(sidebarGreensIn(css)).toEqual({light: ['#1a4031'], dark: ['#166534']});
        });
    });

    it('(a) each source picks the colour with exactly one dark/light pair and looks the meta up exactly once', () => {
        const found = Object.fromEntries(
            SOURCES.map((file) => {
                const text = read(file);
                return [file, {pairs: pairsIn(file, text).length, lookups: [...scriptOf(file, text).matchAll(META_NAME)].length}];
            }),
        );
        expect(found, 'a statement renamed, moved or rewritten in a form this scanner does not read shows here as 0: teach the scanner its new form').toEqual(Object.fromEntries(SOURCES.map((file) => [file, {pairs: 1, lookups: 1}])));
    });

    it('(b) the three sources write one pair — the splash, the app and the offline page colour the title bar alike', () => {
        const pairs = SOURCES.map(theOnePairOf);
        const distinct = new Set(pairs.map(({light, dark}) => `light ${light}, dark ${dark}`));
        expect([...distinct], ['', 'The copies of the title-bar pair disagree:', ...pairs.map(describePair), ''].join('\n  ')).toHaveLength(1);
    });

    it('(b) and it is the pair D3 settled: light #1a4031, dark #166534', () => {
        const pairs = Object.fromEntries(
            SOURCES.map((file) => {
                const {light, dark} = theOnePairOf(file);
                return [file, {light, dark}];
            }),
        );
        expect(pairs).toEqual(Object.fromEntries(SOURCES.map((file) => [file, PAIR])));
    });

    it("(c) before any script runs the light value shows: both documents' static meta and the manifest's theme_color", () => {
        const manifest = JSON.parse(read(MANIFEST)) as {theme_color?: unknown};
        expect({
            [APP_HTML]: staticMetaContentsIn(APP_HTML, read(APP_HTML)),
            [OFFLINE_HTML]: staticMetaContentsIn(OFFLINE_HTML, read(OFFLINE_HTML)),
            [MANIFEST]: [String(manifest.theme_color ?? '').toLowerCase()],
        }).toEqual({[APP_HTML]: [PAIR.light], [OFFLINE_HTML]: [PAIR.light], [MANIFEST]: [PAIR.light]});
    });

    it("(d) the pair is the sidebar's: --color-libre-green of @theme in light, html.dark .bg-libre-green in dark", () => {
        expect(sidebarGreensIn(read(APP_CSS)), `${APP_CSS}: the sidebar's two greens, read once each — if the sidebar moved, move the title-bar pair with it (all three sources and PAIR), or record why they now differ`).toEqual({light: [PAIR.light], dark: [PAIR.dark]});
    });

    describe('(e) nothing else writes the meta', () => {
        it('the walk reads every component, store and document of the app, and no test', () => {
            const files = scannedFiles();
            expect(files).toEqual(expect.arrayContaining([...SOURCES, 'static/sw.js', 'src/lib/components/layout/Sidebar.svelte']));
            expect(files).not.toContain('src/themeColorMeta.gate.test.ts');
            expect(files.filter((file) => file.endsWith('.svelte')).length, 'the walk reaches the components').toBeGreaterThan(100);
        });

        it('the name theme-color appears, outside comments, in the code of the three sources only', () => {
            const writers = scannedFiles().filter((file) => [...codeOf(file, read(file)).matchAll(META_NAME)].length > 0);
            expect(writers.sort(), 'a new writer of the title-bar colour: route it through the three sources, or add it to SOURCES so (a)–(b) read it too').toEqual([...SOURCES].sort());
        });
    });
});
