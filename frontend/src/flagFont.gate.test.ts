/**
 * Gate: one global font rule for flags, and no emoji font ahead of the text font (K step 12b).
 *
 * ## What this protects
 *
 * The developer's decision of 2026-09-29 (plan step 12, section b): flags — the regional indicators
 * U+1F1E6–1F1FF — get ONE global font, `'LF Flags'`, placed first in every stack the app sets. On an
 * Apple device that face resolves to the system Apple Color Emoji through `local()`; everywhere else
 * it downloads the one self-hosted Noto subset that holds the flags. Every other emoji stays the
 * system's, and no emoji font may ever come before the text font (Inter, or the monospace font) for
 * text characters such as digits, `#` and `*` — the Noto subset 2 covers exactly those, so the family
 * name `'Noto Color Emoji'` must never lead a stack.
 *
 * The contract, as this file checks it:
 *
 *   (a) `static/lf-flags.css` — tracked, outside the gitignored `static/fonts/` — holds exactly one
 *       `@font-face`: family `'LF Flags'`; `src:` `local('Apple Color Emoji')`, `local('AppleColorEmoji')`,
 *       `local('Noto Color Emoji')`, `local('NotoColorEmoji')`, then
 *       `url('/fonts/noto-color-emoji/noto-color-emoji.0.woff2') format('woff2')`, in this order;
 *       `unicode-range: U+1F1E6-1F1FF` and nothing else.
 *   (b) `src/app.html` and `static/offline.html` link `/lf-flags.css` and no longer link the generated
 *       `noto-color-emoji.css` — and no stylesheet of the app references it any other way.
 *   (c) `src/app.css`: `html`, `@theme --font-sans` and `.emoji-flag` are `'LF Flags', Inter, system-ui,
 *       sans-serif`; `@theme --font-mono` is `'LF Flags'` + Tailwind's monospace stack; no component
 *       overrides the font-family of `.emoji-flag` (TransactionsTable's local rule is gone).
 *       `static/offline.html`: every font-family stack starts with `'LF Flags'` and its `.emoji-flag`
 *       equals the app's.
 *   (d) No source of the app — `src` (CSS, `<style>` blocks, inline style strings, scripts) and
 *       `static/offline.html` — names Apple Color Emoji, Noto Color Emoji, Segoe UI Emoji or Segoe UI
 *       Symbol outside a comment. Those names live only as `local()` sources of `static/lf-flags.css`,
 *       which is why that one file is not scanned.
 *
 * Plus the D-b3 guard: when the generated `static/fonts/noto-color-emoji/noto-color-emoji.css` is
 * present, its `noto-color-emoji.0.woff2` face is the flags range — the file `lf-flags.css` points at
 * — and every file it references exists.
 *
 * ## How it reads, and what it cannot see
 *
 * (a)–(c) parse the CSS (comments blanked, braces nested — `@theme`, `:global { }`) and compare
 * normalised family lists, so quoting and spacing are free. (d) enumerates no form at all: after the
 * comments are blanked it reports every mention of the four names, whatever the syntax around it, so a
 * form nobody thought of (`ctx.font`, an ECharts `fontFamily`, a template string) cannot slip through.
 * The comment blanking is the floor: a `//` inside a string swallows the rest of its line, so a
 * mention written after one on the same line would be missed. The file is not a browser: what a stack
 * resolves to on a real device is `e2e/fx/fx-flag-font.spec.ts`, which reads it through CDP.
 *
 * Registered in `front_fx_unit` (`scripts/test_runner/_frontend_fx.py`).
 */

import {describe, expect, it} from 'vitest';
import {existsSync, readdirSync, readFileSync} from 'node:fs';
import {dirname, join, relative, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

/** `frontend/`: every path is reported relative to it. */
const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(FRONTEND, 'src');

const APP_CSS = 'src/app.css';
const APP_HTML = 'src/app.html';
const OFFLINE_HTML = 'static/offline.html';
const LF_FLAGS_CSS = 'static/lf-flags.css';
const GENERATED_NOTO_CSS = 'static/fonts/noto-color-emoji/noto-color-emoji.css';

/** Written by `./dev.py api sync` and `frontend/scripts/generate-tools-client.mjs`; gitignored, never hand-written. */
const GENERATED = new Set(['src/lib/api/generated.ts', 'src/lib/api/generated-tools.ts', 'src/lib/api/tool-contract-map.generated.ts']);

const FLAG_FACE = 'LF Flags';
const FLAGS_RANGE = 'U+1F1E6-1F1FF';
const FLAGS_FILE = '/fonts/noto-color-emoji/noto-color-emoji.0.woff2';
const EXPECTED_SRC = ['local(Apple Color Emoji)', 'local(AppleColorEmoji)', 'local(Noto Color Emoji)', 'local(NotoColorEmoji)', `url(${FLAGS_FILE}) format(woff2)`];
const SANS_STACK = [FLAG_FACE, 'Inter', 'system-ui', 'sans-serif'];
const MONO_STACK = [FLAG_FACE, 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'Liberation Mono', 'Courier New', 'monospace'];

/** The four emoji families no stack may name. `\s*` so the PostScript spellings (`AppleColorEmoji`) are caught too; a hyphenated path (`noto-color-emoji`) is not a family name and is not. */
const EMOJI_FAMILY = /apple\s*color\s*emoji|noto\s*color\s*emoji|segoe\s*ui\s*emoji|segoe\s*ui\s*symbol/gi;
const NOTO_STYLESHEET = /noto-color-emoji\.css/g;

// ---------------------------------------------------------------------------
// Reading
// ---------------------------------------------------------------------------

const collapse = (s: string): string => s.trim().replace(/\s+/g, ' ');
const read = (path: string): string => readFileSync(join(FRONTEND, path), 'utf8');
const lineAt = (text: string, offset: number): number => text.slice(0, offset).split('\n').length;

/** Replace every match with spaces, keeping newlines: offsets and line numbers survive the blanking. */
function blank(text: string, pattern: RegExp): string {
    return text.replace(pattern, (found) => found.replace(/[^\n]/g, ' '));
}

const blankCssComments = (css: string): string => blank(css, /\/\*[\s\S]*?\*\//g);
/** `//` counts as a comment only when it does not follow `:` — `https://` stays code. */
const blankJsComments = (js: string): string => blank(blank(js, /\/\*[\s\S]*?\*\//g), /(?<![:\\])\/\/[^\n]*/g);

/** Comments blanked the way the file type means them: HTML comments in markup, JS comments in scripts, CSS comments in styles. */
function codeOf(file: string, text: string): string {
    if (file.endsWith('.css')) return blankCssComments(text);
    if (file.endsWith('.ts') || file.endsWith('.js')) return blankJsComments(text);
    let out = blank(text, /<!--[\s\S]*?-->/g);
    out = out.replace(/(<script\b[^>]*>)([\s\S]*?)(<\/script\s*>)/g, (_m, open: string, body: string, close: string) => open + blankJsComments(body) + close);
    out = out.replace(/(<style\b[^>]*>)([\s\S]*?)(<\/style\s*>)/g, (_m, open: string, body: string, close: string) => open + blankCssComments(body) + close);
    return out;
}

/** Only the `<style>` blocks of a markup file, everything else blanked: CSS offsets stay file offsets. */
function styleBlocksOf(markup: string): string {
    let out = '';
    let last = 0;
    for (const match of markup.matchAll(/(<style\b[^>]*>)([\s\S]*?)<\/style\s*>/g)) {
        const bodyStart = match.index + match[1].length;
        out += markup.slice(last, bodyStart).replace(/[^\n]/g, ' ') + match[2];
        last = bodyStart + match[2].length;
    }
    return out + markup.slice(last).replace(/[^\n]/g, ' ');
}

// ---------------------------------------------------------------------------
// A small CSS reader: nested blocks, declarations, quoted strings and parentheses respected
// ---------------------------------------------------------------------------

interface Declaration {
    prop: string;
    value: string;
    offset: number;
}

interface CssRule {
    prelude: string;
    declarations: Declaration[];
    children: CssRule[];
    offset: number;
    /** The preludes of the enclosing blocks, outermost first. */
    parents: string[];
}

function parseCss(css: string): CssRule {
    const text = blankCssComments(css);
    const root: CssRule = {prelude: '', declarations: [], children: [], offset: 0, parents: []};
    const stack: CssRule[] = [root];
    let start = 0;
    let quote: string | null = null;
    let depth = 0;
    const top = (): CssRule => stack[stack.length - 1];
    const statement = (end: number) => {
        const raw = text.slice(start, end);
        const lead = raw.length - raw.trimStart().length;
        const match = /^(--[\w-]+|[a-zA-Z-]+)\s*:([\s\S]*)$/.exec(raw.trim());
        if (match) top().declarations.push({prop: match[1].toLowerCase(), value: collapse(match[2]), offset: start + lead});
    };
    for (let i = 0; i < text.length; i++) {
        const c = text[i];
        if (quote) {
            if (c === '\\') i++;
            else if (c === quote) quote = null;
            continue;
        }
        if (c === '"' || c === "'") quote = c;
        else if (c === '(') depth++;
        else if (c === ')') depth = Math.max(0, depth - 1);
        else if (depth > 0) continue;
        else if (c === '{') {
            const raw = text.slice(start, i);
            const rule: CssRule = {prelude: collapse(raw), declarations: [], children: [], offset: start + raw.length - raw.trimStart().length, parents: [...top().parents, top().prelude].filter(Boolean)};
            top().children.push(rule);
            stack.push(rule);
            start = i + 1;
        } else if (c === ';' || c === '}') {
            statement(i);
            if (c === '}' && stack.length > 1) stack.pop();
            start = i + 1;
        }
    }
    statement(text.length);
    return root;
}

function allRules(rule: CssRule, acc: CssRule[] = []): CssRule[] {
    for (const child of rule.children) {
        acc.push(child);
        allRules(child, acc);
    }
    return acc;
}

/** Split on the commas that are not inside quotes or parentheses. */
function splitTopLevel(value: string): string[] {
    const parts: string[] = [];
    let current = '';
    let quote: string | null = null;
    let depth = 0;
    for (const c of value) {
        if (quote) {
            current += c;
            if (c === quote) quote = null;
            continue;
        }
        if (c === '"' || c === "'") quote = c;
        else if (c === '(') depth++;
        else if (c === ')') depth--;
        else if (c === ',' && depth === 0) {
            parts.push(current.trim());
            current = '';
            continue;
        }
        current += c;
    }
    if (current.trim()) parts.push(current.trim());
    return parts;
}

const unquote = (s: string): string => collapse(s.trim().replace(/^(['"])([\s\S]*)\1$/, '$2'));

/** A font-family value as the list of its families, quotes and `!important` gone. */
const familyList = (value: string): string[] => splitTopLevel(value.replace(/!\s*important\s*$/i, '')).map(unquote);

/** One `src:` source, normalised: `local(Name)` or `url(/absolute/path) format(fmt)`, the url resolved against `/lf-flags.css`. */
function normalizeSource(source: string): string {
    const local = /^local\(\s*(['"]?)([\s\S]*?)\1\s*\)$/i.exec(source.trim());
    if (local) return `local(${collapse(local[2])})`;
    const url = /^url\(\s*(['"]?)([\s\S]*?)\1\s*\)\s*(?:format\(\s*(['"]?)([\s\S]*?)\3\s*\))?$/i.exec(source.trim());
    if (url) {
        const path = new URL(url[2], 'http://lane.invalid/lf-flags.css').pathname;
        return url[4] ? `url(${path}) format(${url[4]})` : `url(${path})`;
    }
    return collapse(source);
}

const declarationsOf = (rules: CssRule[], prop: string): Declaration[] => rules.flatMap((rule) => rule.declarations.filter((d) => d.prop === prop));

/** The `<link>` elements of a markup file, comments ignored: `{rel, href}` pairs. */
function linksOf(markup: string): Array<{rel: string; href: string}> {
    const links: Array<{rel: string; href: string}> = [];
    for (const tag of blank(markup, /<!--[\s\S]*?-->/g).matchAll(/<link\b[^>]*>/gi)) {
        const attrs: Record<string, string> = {};
        for (const attr of tag[0].matchAll(/([\w-]+)\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/g)) attrs[attr[1].toLowerCase()] = attr[2].replace(/^(['"])([\s\S]*)\1$/, '$2');
        links.push({rel: (attrs.rel ?? '').toLowerCase(), href: attrs.href ?? ''});
    }
    return links;
}

const pathOf = (href: string): string => new URL(href, 'http://lane.invalid/').pathname;

// ---------------------------------------------------------------------------
// The (d) scan: every mention of a forbidden family, whatever the form
// ---------------------------------------------------------------------------

interface Mention {
    file: string;
    line: number;
    name: string;
    snippet: string;
}

/**
 * The mentions of `pattern` in one source file, outside comments. A function of its own so that the
 * synthetic sources of the positive control go through exactly the code the real files go through.
 */
function mentionsIn(file: string, text: string, pattern: RegExp): Mention[] {
    const code = codeOf(file, text);
    const lines = text.split('\n');
    return [...code.matchAll(pattern)].map((match) => {
        const line = lineAt(code, match.index);
        return {file, line, name: match[0], snippet: collapse(lines[line - 1]).slice(0, 160)};
    });
}

const describeMention = (m: Mention): string => `${m.file}:${m.line}  «${m.name}»  ${m.snippet}`;

/** Whether a path (relative to `frontend/`) is app source this gate reads. */
function isScanned(path: string): boolean {
    if (!/\.(css|svelte|ts|js|html)$/.test(path) || /\.(test|spec)\.(ts|js)$/.test(path)) return false;
    if (path.split('/').some((segment) => segment === '__tests__' || segment === '__mocks__' || segment === 'node_modules')) return false;
    return !GENERATED.has(path);
}

function sourceFiles(dir: string = SRC, acc: string[] = []): string[] {
    for (const entry of readdirSync(dir, {withFileTypes: true})) {
        const full = join(dir, entry.name);
        if (entry.isDirectory()) sourceFiles(full, acc);
        else {
            const path = relative(FRONTEND, full).replaceAll('\\', '/');
            if (isScanned(path)) acc.push(path);
        }
    }
    return acc;
}

/** `src` plus the offline page: the documents whose stacks the decision governs. `static/lf-flags.css` is where the names are allowed to live. */
const scannedFiles = (): string[] => [...sourceFiles(), OFFLINE_HTML];

// ---------------------------------------------------------------------------
// The gate
// ---------------------------------------------------------------------------

describe('flag font — one global rule for flags, no emoji font ahead of text (K step 12b gate)', () => {
    describe('(a) static/lf-flags.css', () => {
        it("declares exactly one 'LF Flags' face: Apple local names, Noto local names, then the self-hosted flags subset — flags range only", () => {
            expect(existsSync(join(FRONTEND, LF_FLAGS_CSS)), `${LF_FLAGS_CSS} must exist: the tracked home of the 'LF Flags' face (static/fonts/ is gitignored)`).toBe(true);

            const faces = allRules(parseCss(read(LF_FLAGS_CSS))).filter((rule) => rule.prelude.toLowerCase() === '@font-face');
            expect(faces, `${LF_FLAGS_CSS} must hold exactly one @font-face`).toHaveLength(1);
            const [face] = faces;
            const descriptor = (prop: string): string[] => face.declarations.filter((d) => d.prop === prop).map((d) => d.value);

            expect(descriptor('font-family').map(unquote), "the face is named 'LF Flags'").toEqual([FLAG_FACE]);
            expect(
                descriptor('src').map((value) => splitTopLevel(value).map(normalizeSource)),
                'src: the two Apple names, the two Noto names, then the flags subset — in this order',
            ).toEqual([EXPECTED_SRC]);
            expect(
                descriptor('unicode-range').map((value) => value.toUpperCase().replace(/\s+/g, '')),
                'unicode-range: the regional indicators and nothing else',
            ).toEqual([FLAGS_RANGE]);
        });
    });

    describe('(b) the documents link the flag face, not the Noto stylesheet', () => {
        for (const doc of [APP_HTML, OFFLINE_HTML]) {
            it(`${doc} links /lf-flags.css and no longer links noto-color-emoji.css`, () => {
                const links = linksOf(read(doc));
                expect(
                    links.filter((link) => link.rel.split(/\s+/).includes('stylesheet') && pathOf(link.href) === '/lf-flags.css'),
                    `${doc} must link /lf-flags.css as a stylesheet — links found: ${JSON.stringify(links)}`,
                ).toHaveLength(1);
                expect(
                    links.filter((link) => link.href.includes('noto-color-emoji')).map((link) => link.href),
                    `${doc} must not link the generated Noto stylesheet: it declares 'Noto Color Emoji' over digits, # and *`,
                ).toEqual([]);
            });
        }

        it('no stylesheet of the app references noto-color-emoji.css any other way (link, @import, url)', () => {
            const references = scannedFiles().flatMap((file) => mentionsIn(file, read(file), NOTO_STYLESHEET));
            expect(references.map(describeMention), ['', 'Remove these references to the generated Noto stylesheet:', ...references.map(describeMention), ''].join('\n  ')).toEqual([]);
        });
    });

    describe('(c) the stacks put LF Flags first, then the text font', () => {
        const appCss = allRules(parseCss(read(APP_CSS)));

        it("app.css: html font-family is 'LF Flags', Inter, system-ui, sans-serif", () => {
            const stacks = declarationsOf(
                appCss.filter((rule) => rule.prelude === 'html'),
                'font-family',
            ).map((d) => familyList(d.value));
            expect(stacks.length, 'the html rule with a font-family is found in app.css').toBeGreaterThan(0);
            expect(stacks, 'every html font-family of app.css').toEqual(stacks.map(() => SANS_STACK));
        });

        it("app.css: @theme defines --font-sans and --font-mono with 'LF Flags' first", () => {
            const theme = appCss.filter((rule) => /^@theme\b/.test(rule.prelude));
            expect(declarationsOf(theme, '--color-libre-green'), 'positive control: the @theme block of app.css is read').toHaveLength(1);
            expect(
                declarationsOf(theme, '--font-sans').map((d) => familyList(d.value)),
                "@theme --font-sans: 'LF Flags' then the text stack (Tailwind's default ends with the four emoji families)",
            ).toEqual([SANS_STACK]);
            expect(
                declarationsOf(theme, '--font-mono').map((d) => familyList(d.value)),
                "@theme --font-mono: 'LF Flags' then Tailwind's monospace stack",
            ).toEqual([MONO_STACK]);
        });

        it("app.css: .emoji-flag is 'LF Flags', Inter, system-ui, sans-serif", () => {
            const stacks = declarationsOf(
                appCss.filter((rule) => rule.prelude === '.emoji-flag'),
                'font-family',
            ).map((d) => familyList(d.value));
            expect(stacks.length, 'the .emoji-flag rule with a font-family is found in app.css').toBeGreaterThan(0);
            expect(stacks, 'every .emoji-flag font-family of app.css').toEqual(stacks.map(() => SANS_STACK));
        });

        it('no component overrides the font-family of .emoji-flag: the global rule is the only one', () => {
            const overrides: string[] = [];
            for (const file of sourceFiles().filter((f) => f.endsWith('.css') || f.endsWith('.svelte'))) {
                const text = read(file);
                const css = file.endsWith('.css') ? text : styleBlocksOf(text);
                for (const rule of allRules(parseCss(css))) {
                    if (!/\.emoji-flag(?![\w-])/.test(rule.prelude)) continue;
                    if (file === APP_CSS && rule.prelude === '.emoji-flag' && rule.parents.length === 0) continue;
                    for (const d of rule.declarations.filter((decl) => decl.prop === 'font-family' || decl.prop === 'font')) {
                        overrides.push(`${file}:${lineAt(css, d.offset)}  ${rule.prelude} { ${d.prop}: ${d.value} }`);
                    }
                }
            }
            expect(overrides, ['', "Only app.css's .emoji-flag may set the flag font. Remove these local rules (a line-height may stay):", ...overrides, ''].join('\n  ')).toEqual([]);
        });

        it("offline.html: every font-family stack starts with 'LF Flags' and .emoji-flag equals the app's", () => {
            const text = read(OFFLINE_HTML);
            const css = styleBlocksOf(text);
            const rules = allRules(parseCss(css));
            const sites = [
                ...rules.flatMap((rule) => rule.declarations.filter((d) => d.prop === 'font-family').map((d) => ({where: `${OFFLINE_HTML}:${lineAt(css, d.offset)} ${rule.prelude}`, stack: familyList(d.value)}))),
                ...[...codeOf(OFFLINE_HTML, text).matchAll(/\sstyle\s*=\s*(["'])([\s\S]*?)\1/g)].flatMap((attr) =>
                    attr[2]
                        .split(';')
                        .map((decl) => /^\s*font-family\s*:([\s\S]*)$/i.exec(decl))
                        .filter((m): m is RegExpExecArray => m !== null)
                        .map((m) => ({where: `${OFFLINE_HTML}:${lineAt(text, attr.index)} style=""`, stack: familyList(m[1])})),
                ),
            ];
            expect(sites.length, 'positive control: the font-family stacks of offline.html are found').toBeGreaterThan(0);

            const notFirst = sites.filter((site) => site.stack[0] !== FLAG_FACE).map((site) => `${site.where}: ${site.stack.join(', ')}`);
            expect(notFirst, ['', "offline.html: these stacks do not start with 'LF Flags':", ...notFirst, ''].join('\n  ')).toEqual([]);

            const emojiFlag = declarationsOf(
                rules.filter((rule) => rule.prelude === '.emoji-flag'),
                'font-family',
            ).map((d) => familyList(d.value));
            expect(emojiFlag, "offline.html .emoji-flag equals app.css's: 'LF Flags', Inter, system-ui, sans-serif").toEqual([SANS_STACK]);
        });
    });

    describe('(d) no emoji font is named anywhere a stack can live', () => {
        const caught = (file: string, text: string): string[] => mentionsIn(file, text, EMOJI_FAMILY).map((m) => `${m.name} @${m.line}`);

        it('catches a mention in every form, and ignores comments and file paths', () => {
            // The positive control of the verdict below: "no mention" is also what a scanner whose
            // pattern matched nothing would report.
            expect(caught('a.css', ".x {\n    font-family: 'Apple Color Emoji', sans-serif;\n}")).toEqual(['Apple Color Emoji @2']);
            expect(caught('a.svelte', '<style>\n    :global {\n        .tx .emoji-flag { font-family: "Noto Color Emoji"; }\n    }\n</style>')).toEqual(['Noto Color Emoji @3']);
            expect(caught('a.svelte', '<span style="font-family: Segoe UI Emoji">x</span>')).toEqual(['Segoe UI Emoji @1']);
            expect(caught('a.ts', "el.style.fontFamily = 'Segoe UI Symbol, sans-serif';")).toEqual(['Segoe UI Symbol @1']);
            expect(caught('a.ts', "ctx.font = '12px AppleColorEmoji';\nconst o = {textStyle: {fontFamily: 'NotoColorEmoji'}};")).toEqual(['AppleColorEmoji @1', 'NotoColorEmoji @2']);
            expect(caught('a.ts', 'const html = `<span style="font-family:\'Apple Color Emoji\'">${flag}</span>`;')).toEqual(['Apple Color Emoji @1']);
            expect(caught('a.html', '<style>\n    body { font: 12px/1 "apple color emoji"; }\n</style>')).toEqual(['apple color emoji @2']);

            // Look-alikes: comments of every kind, and the font's file paths.
            expect(caught('a.css', '/* Apple Color Emoji used to come first */\n.x { font-family: Inter; }')).toEqual([]);
            expect(caught('a.svelte', '<!-- Noto Color Emoji -->\n<script>\n    // Segoe UI Emoji has no flags\n    /* Segoe UI Symbol */\n</script>\n<style>\n    /* Apple Color Emoji */\n</style>')).toEqual([]);
            expect(caught('a.ts', "// Apple Color Emoji\nconst path = '/fonts/noto-color-emoji/noto-color-emoji.0.woff2';\nconst url = 'https://example.org/'; /* Noto Color Emoji */")).toEqual([]);
        });

        it('reads every stylesheet, component, script and document of the app, and no test or generated client', () => {
            const files = scannedFiles();
            expect(files).toEqual(expect.arrayContaining([APP_CSS, APP_HTML, OFFLINE_HTML, 'src/lib/components/transactions/TransactionsTable.svelte', 'src/lib/utils/currency/currencyFormat.ts', 'src/routes/(app)/dashboard/+page.svelte']));
            expect(files).not.toContain('src/flagFont.gate.test.ts');
            expect(files).not.toContain(LF_FLAGS_CSS);
            expect(files.filter((file) => file.endsWith('.svelte')).length, 'the walk reaches the components').toBeGreaterThan(100);
        });

        it('names Apple Color Emoji, Noto Color Emoji, Segoe UI Emoji or Segoe UI Symbol nowhere outside static/lf-flags.css', () => {
            const mentions = scannedFiles().flatMap((file) => mentionsIn(file, read(file), EMOJI_FAMILY));
            const rule = "An emoji family in a stack either leads it (and draws digits, # and *) or trails it (and is dead weight): flags come from 'LF Flags' only.";
            expect(mentions.map(describeMention), ['', rule, 'Remove these mentions:', ...mentions.map(describeMention), ''].join('\n  ')).toEqual([]);
        });
    });

    describe('D-b3: the generated Noto cache serves the flags as subset 0', () => {
        it.skipIf(!existsSync(join(FRONTEND, GENERATED_NOTO_CSS)))('noto-color-emoji.0.woff2 is the flags range, and every file the generated CSS references exists', () => {
            const dir = dirname(GENERATED_NOTO_CSS);
            const faces = allRules(parseCss(read(GENERATED_NOTO_CSS)))
                .filter((rule) => rule.prelude.toLowerCase() === '@font-face')
                .map((rule) => ({
                    files: declarationsOf([rule], 'src').flatMap((d) => [...d.value.matchAll(/url\(\s*(['"]?)([^'")]+)\1\s*\)/g)].map((m) => m[2].replace(/^\.\//, ''))),
                    range: declarationsOf([rule], 'unicode-range')
                        .map((d) => d.value.toLowerCase().replace(/\s+/g, ''))
                        .join(','),
                }));
            expect(faces.length, `positive control: the faces of ${GENERATED_NOTO_CSS} are read`).toBeGreaterThan(0);

            const flagsFace = faces.filter((face) => face.files.includes('noto-color-emoji.0.woff2'));
            expect(
                flagsFace.map((face) => face.range),
                `${GENERATED_NOTO_CSS}: the face of noto-color-emoji.0.woff2 — the file static/lf-flags.css points at — must be the flags range`,
            ).toEqual([FLAGS_RANGE.toLowerCase()]);

            const missing = faces.flatMap((face) => face.files).filter((file) => !existsSync(join(FRONTEND, dir, file)));
            expect(missing, `every file ${GENERATED_NOTO_CSS} references exists in ${dir}`).toEqual([]);
        });
    });
});
