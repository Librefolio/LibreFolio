/**
 * Gate: the PWA title bar has one light/dark colour pair, and every copy of it agrees (colour workstream T, decisions
 * D-T17 and D-T24); and the static copies of the colour roles, in the splash and the offline page, agree with
 * tokens.css (T-4).
 *
 * ## What this protects
 *
 * `<meta name="theme-color">` colours the browser chrome around the app — the window of the installed PWA, the
 * address bar on a phone — and the app rewrites it on every theme so that the chrome continues the green sidebar.
 * Three places write it, and they cannot share a module:
 *
 *   - `src/app.html`, the anti-FOUC inline script: it runs before any bundle is loaded;
 *   - `applyTheme()` in `src/lib/stores/app/themeStore.ts`: every theme switch inside the app;
 *   - `static/offline.html`, the page the service worker serves when the server cannot be reached: a static file with
 *     a script of its own.
 *
 * So the pair is copied by hand, and a copy drifts without anybody seeing it. One did: the dark value was `#156534`,
 * one digit away from the sidebar's `#166534`, in all three copies, until R corrected it (the developer's decision D3,
 * 14/10/2026). Two greens one digit apart do not look different — which is exactly why nobody noticed, and why a test
 * has to. R wrote this gate; T took it over with the designer's round 2, approved whole by the developer (D-T17,
 * 15/10/2026): the sidebar is green in both themes, and the title bar continues it with one colour, `#1b4334`, in both
 * themes (N2). The header, green for a while too (D-T19), is neutral since D-T23; the title bar stays the sidebar's
 * green by decision (D-T24). The copies keep a pair whose two branches are equal, so that a theme of its own stays one
 * edit away, and this gate still reads three pairs.
 *
 * ## The rule, as this file checks it
 *
 *   (a) Each of the three sources picks the colour with exactly one `<theme> === 'dark' ? '<dark>' : '<light>'` ternary
 *       (or its `'light'` mirror) and looks the meta up exactly once. This is the positive control of everything
 *       below: a statement renamed, moved or rewritten in a form the scanner does not read shows here as 0, loudly,
 *       instead of leaving (b) to compare nothing.
 *   (b) The three pairs are one pair, and it is the pair D-T17 settled and D-T24 kept: `#1b4334` in light and in dark,
 *       the green sidebar's (N2).
 *   (c) Before any script has run, the light value is what shows: it is the static `content` of the meta in both
 *       documents, and the `theme_color` of `static/manifest.json`.
 *   (d) The pair is the green sidebar's: `--lf-surface-bar`, the surface of the sidebar, resolved from
 *       `src/lib/theme/tokens.css` in each theme by the module of the colour gates, is the light and the dark value of
 *       the pair (D-T24). This is the drift D3 corrected, seen from the other side: should the sidebar change colour
 *       and the title bar not follow, (b) alone would stay green.
 *   (e) Nothing else writes the meta: no other source under `src`, and no other page or script of `static`, names it.
 *       A fourth copy would sit outside (a)–(b).
 *
 * Colours are compared case-insensitively (`#1B4334` is the same colour) and found by content, never by line, so an
 * unrelated edit above a statement cannot turn the gate red. The static copies of the roles are the business of the
 * last block of this file, (f)–(h), which says what it protects on its own.
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
import {blankCssComments, parseTokens, readTokens, resolveColour, toHex} from '../scripts/theme/theme-roles.mjs';

type Tokens = ReturnType<typeof parseTokens>;
type Rgba = ReturnType<typeof resolveColour>;
type Theme = Parameters<typeof resolveColour>[2];

/** `frontend/`: every path is read, and reported, relative to it. */
const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '..');

const APP_HTML = 'src/app.html';
const THEME_STORE = 'src/lib/stores/app/themeStore.ts';
const OFFLINE_HTML = 'static/offline.html';
const MANIFEST = 'static/manifest.json';
/** For the messages: readTokens() reads this file. */
const TOKENS_CSS = 'src/lib/theme/tokens.css';

/** The three sources that write the meta on every theme. */
const SOURCES = [APP_HTML, THEME_STORE, OFFLINE_HTML];

/** The two documents that paint without the app's stylesheet, and so carry copies of the roles they draw with. */
const MIRRORS = [APP_HTML, OFFLINE_HTML];

const THEMES: readonly Theme[] = ['light', 'dark'];

interface Pair {
    light: string;
    dark: string;
}

/** D-T17's pair (15/10/2026), kept by D-T24: the green sidebar's `#1b4334`, in both themes (N2). Before it, D3's. */
const PAIR: Pair = {light: '#1b4334', dark: '#1b4334'};

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
// Colours, read by the module of the colour gates
// ---------------------------------------------------------------------------

/** At or above this alpha a colour is opaque: a mix of two opaque colours sums its weights in floating point. */
const OPAQUE = 1 - 1e-9;

/** A token expression's colour in a theme, or the reason it cannot be read. */
function colourOf(tokens: Tokens, expression: string, theme: Theme): Rgba | string {
    try {
        return resolveColour(tokens, expression, theme);
    } catch (error) {
        return error instanceof Error ? error.message : String(error);
    }
}

/** A colour as a message shows it — `#rrggbb`, with its alpha when it has one — or why it could not be read. */
const reading = (colour: Rgba | string): string => (typeof colour === 'string' ? `unreadable (${colour.replace(/^tokens\.css: /, '')})` : colour.alpha < OPAQUE ? `${toHex(colour)} at ${Math.round(colour.alpha * 100)}%` : toHex(colour));

// ---------------------------------------------------------------------------
// The gate
// ---------------------------------------------------------------------------

describe('PWA theme-color — one light/dark pair, the same in every copy (T, D-T17 gate)', () => {
    describe('the scanner', () => {
        it('reads the ternary in either orientation and quote style, inside scripts only, and ignores comments', () => {
            const pairs = (file: string, text: string): string[] => pairsIn(file, text).map(({light, dark}) => `light ${light}, dark ${dark}`);
            // Any two hex values would do: these are D3's pair, the one before D-T17, and its drifted dark `#156534`.
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

    it("(b) and it is the pair D-T17 settled and D-T24 kept: #1b4334 in both themes, the green sidebar's (N2)", () => {
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

    it("(d) the pair is the green sidebar's: --lf-surface-bar of tokens.css, resolved in each theme", () => {
        const tokens = readTokens();
        const sidebar = Object.fromEntries(THEMES.map((theme) => [theme, reading(colourOf(tokens, 'var(--lf-surface-bar)', theme))]));
        expect(sidebar, `${TOKENS_CSS}: --lf-surface-bar, the surface of the green sidebar, whose colour the title bar keeps (D-T24) — if the sidebar changes colour, move the title-bar pair with it (all three sources and PAIR), or record why they now differ`).toEqual({
            light: PAIR.light,
            dark: PAIR.dark,
        });
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

// ---------------------------------------------------------------------------
// The static copies of the roles (T-4)
// ---------------------------------------------------------------------------

/*
 * The static copies of the roles: the splash and the offline page (T-4).
 *
 * ## Why the copies exist
 *
 * Two surfaces paint without the app's stylesheet, so the roles of `src/lib/theme/tokens.css` cannot reach them:
 *   - the splash of `src/app.html`, which paints before the app's stylesheet has loaded — that is what it is for;
 *   - `static/offline.html`, which the service worker serves when the server cannot be reached: the app's stylesheet is
 *     exactly what it cannot fetch.
 * So each carries, in its `<style>`, copies of the `--lf-*` roles it draws with — a light block and an `html.dark` one;
 * the splash scopes them to `#app-splash`, so that they never reach the app — and draws everything else through
 * `var()`. A copy drifts the way the title-bar pair did, by hand, one value at a time, in a file the gates of the roles
 * do not read: themeRoles reads the sources of `src`, themeTokens reads tokens.css.
 *
 * ## The rule
 *
 *   (f) Every `--lf-*` the `<style>` of each document declares is, in each theme, the colour tokens.css gives it. The
 *       declarations are read from the leaf rules, comments blanked; a rule whose selector holds `html.dark` is dark,
 *       any other light, and a theme declares each name once — twice, the copy would hang on the order of the rules.
 *       The light copy is the light declarations; the dark copy is the light one overridden by the dark declarations:
 *       `html.dark` adds to `:root`, it does not replace it, so a role the dark block forgets keeps its light value,
 *       and is caught. Both sides are resolved by the module of the colour gates, so a copy compares by colour, not by
 *       text: written out, `color-mix(in oklab, #1b4334 30%, transparent)` is the
 *       `color-mix(in oklab, var(--lf-brand) 30%, transparent)` it copies (alpha within 0.005).
 *   (g) The positive control: both documents declare `--lf-surface-page` in both themes, the offline page at least 15
 *       roles, and every name they copy is a role of tokens.css — a copy of a role that is gone is a stale copy.
 *   (h) No stray literal: outside the `--lf-*` declarations, no value of either `<style>` holds a colour literal — a
 *       hex, or a colour function: `rgb()`, `rgba()`, `hsl()`, `hsla()` and those of CSS Color 4.
 *
 * ## What it cannot see
 *
 *   - colours outside the `<style>`: an inline `style=""`, an SVG attribute, a script — the title-bar pair lives in the
 *     scripts and in the markup, and is (a)–(c)'s business;
 *   - which theme a rule really applies in: the theme comes from the selector alone, so a rule under
 *     `@media (prefers-color-scheme: dark)`, or one on a `.dark` class instead of `html.dark`, is read as light;
 *   - whether the page draws with the roles it copies, or with one it never copied: a `var()` with no copy behind it
 *     falls back, or draws nothing — a browser shows that, this file does not;
 *   - in (h): a CSS colour name (`white`), and a declaration that sits beside a nested rule — the scan reads the values
 *     of the leaf rules only. It skips the selectors on purpose: an id such as `#cafe` is no colour;
 *   - the `background_color` of `static/manifest.json`, which is no copy of a role: the maskable icons, painted edge to
 *     edge in the splash beige, pin it, and `backend/test_scripts/test_utilities/test_pwa_assets.py` checks it — moving
 *     it to `--lf-surface-page` (D-T7) means repainting those icons, a decision still open with the coordinator.
 */

/** The `--lf-*` declarations of a stylesheet, by theme: what a document copies from tokens.css. */
interface Copies {
    /** From the rules whose selector does not hold `html.dark`. */
    light: Map<string, string>;
    /** From the rules whose selector holds `html.dark`: they add to the light copy, they do not replace it. */
    dark: Map<string, string>;
    /** `<theme> <name>` for each name a theme declares more than once: the copy would hang on the order of the rules. */
    twice: string[];
}

/** A selector of the dark theme: it holds `html.dark`. */
const DARK_SELECTOR = /(?<![\w-])html\.dark(?![\w-])/;

/** The `<style>` text of a document: the HTML comments around it blanked, and the CSS comments inside it. */
function styleOf(file: string): string {
    const markup = blank(read(file), /<!--[\s\S]*?-->/g);
    return [...markup.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style\s*>/gi)].map((match) => blankCssComments(match[1])).join('\n');
}

/** The innermost rules of a stylesheet — the blocks that hold no other block — with their prelude, comments blanked. */
function leafRulesOf(css: string): Array<{prelude: string; body: string}> {
    return [...blankCssComments(css).matchAll(/([^{}]*)\{([^{}]*)\}/g)].map((match) => ({prelude: collapse(match[1].split(';').pop() ?? ''), body: match[2]}));
}

/** The declarations of a rule body, in order: the property, and the value with its spaces collapsed. */
function declarationsOf(body: string): Array<{property: string; value: string}> {
    return body.split(';').flatMap((declaration) => {
        const match = /^\s*(-{0,2}[a-z][\w-]*)\s*:([\s\S]*)$/i.exec(declaration);
        return match ? [{property: match[1], value: collapse(match[2])}] : [];
    });
}

/** What a stylesheet copies: the `--lf-*` declarations of its leaf rules, light or dark by their selector. */
function copiesIn(css: string): Copies {
    const copies: Copies = {light: new Map(), dark: new Map(), twice: []};
    for (const rule of leafRulesOf(css)) {
        const theme: Theme = DARK_SELECTOR.test(rule.prelude) ? 'dark' : 'light';
        for (const {property, value} of declarationsOf(rule.body)) {
            if (!property.startsWith('--lf-')) continue;
            if (copies[theme].has(property)) copies.twice.push(`${theme} ${property}`);
            copies[theme].set(property, value);
        }
    }
    return copies;
}

/** Every name a document copies, once, in the order it first declares them. */
const copiedNames = (copies: Copies): string[] => [...new Set([...copies.light.keys(), ...copies.dark.keys()])];

/**
 * The copies as the blocks of tokens.css, for the module's resolver: the light copy is the light block, and the dark
 * block is the light copy overridden by the dark declarations, as `html.dark` adds to `:root` in the page.
 */
const asTokens = (copies: Copies): Tokens => ({light: new Map(copies.light), derived: new Map(), dark: new Map([...copies.light, ...copies.dark]), utilities: new Map()});

/** How far a copy's alpha may stray from its role's: a mix written out and the mix it copies may part in the last bit. */
const ALPHA_TOLERANCE = 0.005;

/** Where a copy is not the colour of its role: `<label> <theme> <name>: copy X ≠ tokens Y`. */
function driftOf(label: string, copies: Copies, tokens: Tokens): string[] {
    const copy = asTokens(copies);
    const out: string[] = [];
    for (const name of copiedNames(copies)) {
        for (const theme of THEMES) {
            const mine = colourOf(copy, `var(${name})`, theme);
            const role = colourOf(tokens, `var(${name})`, theme);
            const same = typeof mine !== 'string' && typeof role !== 'string' && toHex(mine) === toHex(role) && Math.abs(mine.alpha - role.alpha) <= ALPHA_TOLERANCE;
            if (!same) out.push(`${label} ${theme} ${name}: copy ${reading(mine)} ≠ tokens ${reading(role)}`);
        }
    }
    return out;
}

/** A hex colour as the module counts one: not inside a word, not part of a longer run of hex digits. */
const HEX_LITERAL = /(?<![\w&-])#(?:[0-9a-f]{8}|[0-9a-f]{6}|[0-9a-f]{3,4})(?![\w-])/gi;
/** A colour function, CSS 3's and CSS Color 4's, to its first `)`. `color-mix(in oklab, …)` names a space, no colour. */
const COLOUR_FUNCTION = /(?<![\w-])(?:rgba?|hsla?|oklch|oklab|lab|lch|hwb)\([^()]*\)?/gi;

/** The values outside the `--lf-*` declarations: how many were read, and each literal as `<selector> { <property>: <literal> }`. */
function strayLiteralsIn(css: string): {scanned: number; strays: string[]} {
    let scanned = 0;
    const strays: string[] = [];
    for (const rule of leafRulesOf(css)) {
        for (const {property, value} of declarationsOf(rule.body)) {
            if (property.startsWith('--lf-')) continue;
            scanned += 1;
            for (const literal of [...value.matchAll(HEX_LITERAL), ...value.matchAll(COLOUR_FUNCTION)]) strays.push(`${rule.prelude} { ${property}: ${literal[0]} }`);
        }
    }
    return {scanned, strays};
}

/** A tokens.css of three roles, for the positive controls: not the real values, so the controls do not follow them. */
const SAMPLE_TOKENS = `
:root,
html.light,
.light {
    --lf-surface-page: #f0f0f0;
    --lf-focus: #205040;
}

:root,
.light,
.dark {
    --lf-selected: color-mix(in oklab, var(--lf-focus) 12%, transparent);
}

html.dark,
.dark {
    --lf-surface-page: #101010;
    --lf-focus: #409070;
}

@theme inline {
    --color-lf-page: var(--lf-surface-page);
}
`;

/**
 * The `<style>` of a document that copies those roles, with a fault of each kind and the look-alikes beside them: a
 * copy in capitals and a mix written out (both right), a dark copy commented out (so forgotten), a light name declared
 * twice, a stray hex, a stray rgba(), a stray hsl() inside keyframes, an id that looks like hex, a mix of roles.
 */
const SAMPLE_STYLE = `
:root {
    --lf-surface-page: #F0F0F0;
    --lf-focus: #205040;
    --lf-selected: color-mix(in oklab, #205040 12%, transparent);
}
html.dark {
    --lf-surface-page: #101010;
    --lf-selected: color-mix(in oklab, #409070 12%, transparent);
    /* --lf-focus: #409070; */
}
.card {
    --lf-focus: #205040;
    background: var(--lf-surface-page);
    border: 1px solid #ccc;
}
#cafe {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    color: color-mix(in oklab, var(--lf-focus) 50%, transparent);
}
@keyframes glow {
    to {
        outline-color: hsl(150 40% 40%);
    }
}
`;

describe('static copies of the roles — the splash and the offline page paint without the app stylesheet, so they copy its roles (T-4)', () => {
    describe('the reader', () => {
        it('reads the copies by theme, comments blanked, and records a name declared twice in one theme (positive control)', () => {
            const copies = copiesIn(SAMPLE_STYLE);
            expect(Object.fromEntries(copies.light)).toEqual({'--lf-surface-page': '#F0F0F0', '--lf-focus': '#205040', '--lf-selected': 'color-mix(in oklab, #205040 12%, transparent)'});
            expect(Object.fromEntries(copies.dark), 'a copy in a comment is no copy').toEqual({'--lf-surface-page': '#101010', '--lf-selected': 'color-mix(in oklab, #409070 12%, transparent)'});
            expect(copies.twice, '.card is no html.dark rule: its --lf-focus is a second light one').toEqual(['light --lf-focus']);
        });

        it('compares by colour, the dark copy on top of the light one, and catches a role the dark block forgot (positive control)', () => {
            expect(driftOf('sample', copiesIn(SAMPLE_STYLE), parseTokens(SAMPLE_TOKENS)), 'the capitals and the mix written out are the same colours; the forgotten dark focus is the light one').toEqual(['sample dark --lf-focus: copy #205040 ≠ tokens #409070']);
        });

        it('finds a colour literal in a value outside the copies, keyframes included, and none in a selector, a copy or a mix of roles (positive control)', () => {
            expect(strayLiteralsIn(SAMPLE_STYLE).strays).toEqual(['.card { border: #ccc }', '#cafe { box-shadow: rgba(0, 0, 0, 0.2) }', 'to { outline-color: hsl(150 40% 40%) }']);
        });
    });

    it('(f) every role the splash and the offline page copy is the colour tokens.css gives it, in both themes', () => {
        const tokens = readTokens();
        const twice = MIRRORS.flatMap((file) => copiesIn(styleOf(file)).twice.map((entry) => `${file} ${entry}`));
        expect(twice, 'a role declared twice in one theme of a document: its copy depends on the order of the rules — declare it once per theme').toEqual([]);
        const drift = MIRRORS.flatMap((file) => driftOf(file, copiesIn(styleOf(file)), tokens));
        const rule = `A static copy keeps the colour of its role: change it in the same commit as ${TOKENS_CSS}, in both themes. The dark block of a document adds to its light one, so a role the dark block forgets keeps its light value.`;
        expect(drift, ['', rule, '', ...drift, ''].join('\n  ')).toEqual([]);
    });

    it('(g) the copies are there to compare: --lf-surface-page in both themes of both documents, at least 15 roles on the offline page, each a role of tokens.css', () => {
        const tokens = readTokens();
        const known = new Set([...tokens.light.keys(), ...tokens.derived.keys(), ...tokens.dark.keys()]);
        const found = Object.fromEntries(
            MIRRORS.map((file) => {
                const copies = copiesIn(styleOf(file));
                return [file, {page: {light: copies.light.has('--lf-surface-page'), dark: copies.dark.has('--lf-surface-page')}, unknown: copiedNames(copies).filter((name) => !known.has(name))}];
            }),
        );
        expect(
            found,
            `positive control: each document declares the page surface in its light and in its dark rules — a false here is a reader that lost the <style>, not a document with nothing to compare — and copies only roles ${TOKENS_CSS} declares: the copy of a role that is gone is stale`,
        ).toEqual(Object.fromEntries(MIRRORS.map((file) => [file, {page: {light: true, dark: true}, unknown: []}])));
        expect(copiedNames(copiesIn(styleOf(OFFLINE_HTML))).length, `positive control: ${OFFLINE_HTML} draws a whole page from its copies — the card, the toolbar, the menu, the button, the background`).toBeGreaterThanOrEqual(15);
    });

    it('(h) no colour literal outside the copies: the rest of each <style> draws through var()', () => {
        const scans = Object.fromEntries(MIRRORS.map((file) => [file, strayLiteralsIn(styleOf(file))]));
        expect(Object.fromEntries(MIRRORS.map((file) => [file, scans[file].scanned > 0])), 'positive control: the scan reads the declarations of each <style> that are not copies').toEqual(Object.fromEntries(MIRRORS.map((file) => [file, true])));
        const strays = MIRRORS.flatMap((file) => scans[file].strays.map((stray) => `${file}  ${stray}`));
        const rule = 'Outside its --lf-* copies a static page names no colour: copy the role it needs from tokens.css, and draw with var(--lf-…).';
        expect(strays, ['', rule, '', ...strays, ''].join('\n  ')).toEqual([]);
    });
});
