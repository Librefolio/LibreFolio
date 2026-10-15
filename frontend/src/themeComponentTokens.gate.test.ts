/**
 * Gate: every component colour token is defined once, in its area file, and loaded by every component that reads it
 * (colour workstream R, R-3).
 *
 * ## What this protects
 *
 * R-3 moved the colour literals of the components' `<style>` blocks into CSS custom properties, pixel-identical: one
 * name per role, `--lf-cmp-<component>-<role>`, and a `-dark` twin for what a `:global(.dark)` rule paints. They are
 * defined in the area files of `src/lib/theme/components/` (`table`, `media`, `files`, `dialogs` today), each one
 * `:root { … }` block, and read by the components as `var(--lf-cmp-…)`. A component loads the file of the tokens it
 * reads with a side-effect import in its `<script>`:
 *
 *     import '$lib/theme/components/table.css';
 *
 * That line is what makes Vite ship the `:root` block with the component's chunk. Nothing else ties a read to its
 * definition, and every way the two come apart is silent — no compiler, type-checker or linter says a word:
 *
 *   - a misspelt or deleted name leaves a `var()` with nothing behind it, and the declaration is dropped at
 *     computed-value time: the property falls back to its inherited or initial value — the parent's text colour, a
 *     transparent background, a border in the text colour or no border at all;
 *   - a component that reads a token without importing its file renders right whenever another component has already
 *     loaded that file, and wrong on the first screen that loads it alone: invisible at type-check, visible only on
 *     screen, and only on some screens;
 *   - a token defined twice is settled by load order, silently, and the order moves with the chunks;
 *   - a definition nobody reads is a colour the designer will tune (phase B) while nothing on screen changes;
 *   - a definition anywhere else — a component's `<style>`, a `style:` directive, a script — is a second source of
 *     truth, and not where the designer will look for it.
 *
 * ## The rule, as this file checks it
 *
 *   (a) Every `var(--lf-cmp-<name>` in a `.svelte` — in its `<style>`, in a `style="…"` attribute, in a script string, as
 *       the fallback of another `var()` — names a token defined exactly once across the area files, and names it whole:
 *       a name assembled at run time (`var(--lf-cmp-badge-{variant})`) cannot be checked, so it fails.
 *   (b) Every `.svelte` that reads a token imports the area file that defines it, in one of its `<script>` blocks, in the
 *       side-effect form above: the `$lib/…` specifier with no query (`?inline` and `?url` load nothing), not commented
 *       out, not dynamic, not bound to a name. The failure names the line to add. There is no exemption: the Designer
 *       Lab, which may read tokens without importing their files, is not read at all — see the walk, below.
 *   (c) No token is defined twice, in one file or across files, and every token defined is read by a `.svelte`: export
 *       only what is used.
 *   (d) Each area file is a pure token file: once comments are removed, exactly one `:root { … }` whose body is nothing
 *       but `--lf-cmp-[a-z0-9-]+: <value>;` declarations. And outside the area files the code the walk reads names a
 *       token in one form only, the read (a) checks. A definition anywhere else (a component's `<style>` or `style`
 *       attribute, a `style:` directive, a script's `setProperty`, `app.css`), a read outside a component (a script
 *       module, `app.html`), an alias inside an area file, any other mention: each is reported with its place and its
 *       kind, because (a)–(c) would not see it.
 *   (e) The scan reads something, and nothing it must not: the walk reaches the components and opens no test and no
 *       Designer Lab file, at least one area file exists, each defines at least one token, and at least one component
 *       reads one. Every check above also passes on a scanner that reads the wrong directory, or whose patterns match
 *       nothing.
 *
 * Every check is a pure function of a `{path: text}` tree, read as the walk reads `src`: a path the walk would not open
 * is dropped from a synthetic tree too. The scanner is first run on synthetic trees that break each rule once — the
 * proof that each check can fail — and then on the files of `src`. Everything is found by content, never by line: line
 * numbers appear in the messages only.
 *
 * ## What it cannot see
 *
 * It reads source text, not a browser: that a token is loaded is inferred from the import, not observed. (b) asks every
 * reader for its own import, even where another component on the same screen loads the file anyway — on purpose, since
 * which components share a chunk moves with the router. The reverse is not asked: an import with no read behind it
 * costs a few bytes and goes unreported.
 *
 * Values are not judged: that a value is a colour, that it is the colour the literal was before R-3 (pixel identity is
 * R-3's own verification), that two tokens hold the same one. Nor is the choice of token: a `-dark` twin read outside a
 * `.dark` rule, a light token read inside one, a component reading another component's tokens — all pass.
 *
 * The forms are a floor. A name spelt with a CSS escape, or assembled across strings (`'--lf-' + 'cmp-…'`), is no
 * mention at all. Comment blanking is a floor too: a `//` inside a script string swallows the rest of its line, a `/*`
 * inside a regular-expression literal everything up to the next comment end. Blanking only removes text, so it can
 * hide a mention, never invent one. Stylesheets that do not live under `src` (`static/`, a CDN) are not read.
 *
 * The walk reads every `.svelte`, `.ts`, `.js`, `.mjs`, `.cjs`, `.css` and `.html` under `src` but two groups, which it
 * does not even open — nor does it enter `node_modules`:
 *
 *   - the tests: every `*.test.ts` (this file among them: its synthetic cases are made of the very forms (d) rejects),
 *     and everything under a `__tests__/` or `__mocks__/` directory, harnesses and fixtures included. These are the
 *     patterns the sibling gates skip, and the ones `vitest.config.ts` keeps out of coverage. A test is not a reader the
 *     app ships, and it may well check a token by value, `getComputedStyle(…).getPropertyValue('--lf-cmp-…')`, in a
 *     form (d) would report;
 *   - the Designer Lab, `src/lib/dev/designer-lab/` and `src/routes/designer-lab/`, matched as path prefixes (absent
 *     from some checkouts). D7, a developer decision of R, exempts the paths of L, the Lab's workstream, entirely: the
 *     Lab reads, composes and overrides colours live, by value, as its job, and its `getPropertyValue` and
 *     `setProperty` would be strays for (d) the day its code lands. Its third path, `frontend/scripts/designer-lab/`,
 *     lies outside `src` and is not read anyway.
 *
 * So a token named by a test or by the Lab is invisible here, on purpose: a misspelt read there, a definition, a
 * `setProperty`, a missing import — none is reported. Nor does a read there count for (c): a token that only a test or
 * the Lab reads is, for this gate, a token no component reads.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */

import {describe, expect, it} from 'vitest';
import {readdirSync, readFileSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

/** `frontend/`: every path is read, and reported, relative to it. */
const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '..');

/** Where tokens are defined: every `.css` directly in this directory is an area file. */
const AREA_DIR = 'src/lib/theme/components';

/** The Designer Lab (D7), matched as path prefixes: the walk does not read it at all. It reads, composes and overrides colours live, by value — its job, and every form (b) and (d) reject. */
const DESIGNER_LAB = ['src/lib/dev/designer-lab/', 'src/routes/designer-lab/'];

/** The types the walk reads: every one that can define or read a custom property. */
const SCANNED = /\.(svelte|ts|js|mjs|cjs|css|html)$/;

/** Files by path, relative to `frontend/`: the files of `src`, or a synthetic tree. */
type Tree = Record<string, string>;

// ---------------------------------------------------------------------------
// Reading
// ---------------------------------------------------------------------------

const lineAt = (text: string, offset: number): number => text.slice(0, offset).split('\n').length;
const collapse = (s: string): string => s.trim().replace(/\s+/g, ' ');
const isMarkup = (file: string): boolean => file.endsWith('.html') || file.endsWith('.svelte');

/** `lineAt` for a text read many times: its line starts found in one pass, then each line by binary search. */
function lineFinder(text: string): (offset: number) => number {
    const starts = [0];
    for (let newline = text.indexOf('\n'); newline !== -1; newline = text.indexOf('\n', newline + 1)) starts.push(newline + 1);
    return (offset) => {
        let low = 0;
        let high = starts.length - 1;
        while (low < high) {
            const middle = (low + high + 1) >> 1;
            if (starts[middle] <= offset) low = middle;
            else high = middle - 1;
        }
        return low + 1;
    };
}

/** Replace every match with spaces, keeping newlines: offsets and line numbers survive the blanking. */
function blank(text: string, pattern: RegExp): string {
    return text.replace(pattern, (found) => found.replace(/[^\n]/g, ' '));
}

const blankCssComments = (css: string): string => blank(css, /\/\*[\s\S]*?\*\//g);
/** `//` counts as a comment only when it does not follow `:` — `https://` stays code. */
const blankJsComments = (js: string): string => blank(blank(js, /\/\*[\s\S]*?\*\//g), /(?<![:\\])\/\/[^\n]*/g);

/** A file with its comments blanked the way its type means them: a stylesheet as CSS, a script as JS, markup as HTML — and the scripts and styles of markup each by their own syntax. */
function codeOf(file: string, text: string): string {
    if (file.endsWith('.css')) return blankCssComments(text);
    if (!isMarkup(file)) return blankJsComments(text);
    let out = blank(text, /<!--[\s\S]*?-->/g);
    out = out.replace(/(<script\b[^>]*>)([\s\S]*?)(<\/script\s*>)/gi, (_m, open: string, body: string, close: string) => open + blankJsComments(body) + close);
    out = out.replace(/(<style\b[^>]*>)([\s\S]*?)(<\/style\s*>)/gi, (_m, open: string, body: string, close: string) => open + blankCssComments(body) + close);
    return out;
}

/** The code around an offset, on its own line, for a message: enough to recognise the declaration, never a whole minified line. */
function excerptAt(code: string, offset: number): string {
    const start = code.lastIndexOf('\n', offset - 1) + 1;
    const newline = code.indexOf('\n', offset);
    const end = newline === -1 ? code.length : newline;
    const from = Math.max(start, offset - 60);
    const to = Math.min(end, offset + 90);
    return `${from > start ? '…' : ''}${collapse(code.slice(from, to))}${to < end ? '…' : ''}`;
}

// ---------------------------------------------------------------------------
// What the scanner reads
// ---------------------------------------------------------------------------

const isArea = (file: string): boolean => file.startsWith(`${AREA_DIR}/`) && file.endsWith('.css') && !file.slice(AREA_DIR.length + 1).includes('/');
const isComponent = (file: string): boolean => file.endsWith('.svelte');
const isDesignerLab = (file: string): boolean => DESIGNER_LAB.some((prefix) => file.startsWith(prefix));

/** Whether a path (relative to `frontend/`) is code this gate reads: a type that can define or read a custom property, and neither a test (`*.test.ts`, anything under `__tests__/` or `__mocks__/`), a dependency, nor the Designer Lab. The walk opens nothing else, and `audit` drops anything else from a synthetic tree. */
function isScanned(path: string): boolean {
    if (!SCANNED.test(path) || path.endsWith('.test.ts')) return false;
    if (path.split('/').some((segment) => segment === '__tests__' || segment === '__mocks__' || segment === 'node_modules')) return false;
    return !isDesignerLab(path);
}

/** The specifier a component imports an area file by: `src/lib/…` is `$lib/…`. */
const specifierOf = (area: string): string => `$lib/${area.slice('src/lib/'.length)}`;

/** The statement (b) asks a component to add. */
const importOf = (area: string): string => `import '${specifierOf(area)}';`;

/** A component token wherever code names one: the prefix, and as much of a name as follows it. */
const MENTION = /(?<![\w-])--lf-cmp-[\w-]*/g;

/**
 * How code names a token:
 *   - `var`: `var(--lf-cmp-…` — the read, the one form (a)–(c) check;
 *   - `definition`: `--lf-cmp-…:` (a declaration, in a stylesheet, a `style` attribute or a string), `style:--lf-cmp-…`
 *     (a Svelte directive), `setProperty('--lf-cmp-…'` (a script);
 *   - `other`: anything else — `getPropertyValue('--lf-cmp-…')`, a bare name in a string.
 */
type Kind = 'var' | 'definition' | 'other';

interface Mention {
    file: string;
    line: number;
    name: string;
    kind: Kind;
    /** Whether a read ends where its name does — a `)`, or the `,` of a fallback, next — instead of running on into an interpolation or a concatenation. Always true for the other kinds. */
    whole: boolean;
    excerpt: string;
}

function kindOf(before: string, after: string): Kind {
    if (/var\(\s*$/.test(before)) return 'var';
    if (/^\s*:/.test(after) || /style:$/.test(before) || /setProperty\(\s*['"`]$/.test(before)) return 'definition';
    return 'other';
}

/** Every mention of a component token in the code of a file, comments aside. */
function mentionsIn(file: string, text: string): Mention[] {
    const code = codeOf(file, text);
    const lineOf = lineFinder(code);
    return [...code.matchAll(MENTION)].map((match) => {
        const name = match[0];
        const before = code.slice(Math.max(0, match.index - 40), match.index);
        const after = code.slice(match.index + name.length, match.index + name.length + 40);
        const kind = kindOf(before, after);
        return {file, line: lineOf(match.index), name, kind, whole: kind !== 'var' || /^\s*[),]/.test(after), excerpt: excerptAt(code, match.index)};
    });
}

/** `import '<specifier>';` — the side-effect form: nothing between `import` and the quote, nothing after it but the `;`. One statement per line, as Prettier writes them: `[ \t]`, never `\s`, so that a long blank run is not rescanned from each of its lines. */
const SIDE_EFFECT_IMPORT = /(?:^|;)[ \t]*import[ \t]*(['"])([^'"\n]+)\1[ \t]*(?=;|$)/gm;

/** The specifiers a component imports for their side effect, read in the code of its scripts — instance and module alike — and nowhere else. */
function sideEffectImportsIn(file: string, text: string): Set<string> {
    const scripts = [...codeOf(file, text).matchAll(/<script\b[^>]*>([\s\S]*?)<\/script\s*>/gi)].map((match) => match[1]).join('\n');
    return new Set([...scripts.matchAll(SIDE_EFFECT_IMPORT)].map((match) => match[2]));
}

/** One `--lf-cmp-<name>: <value>;` at the cursor. A value may hold quoted strings and parentheses three deep, so the `;` of `url("data:…;…")` does not end it. */
const DECLARATION = /\s*(--lf-cmp-[a-z0-9-]+)\s*:((?:"[^"]*"|'[^']*'|\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\)|[^;{}()"'])*);/y;

/** What an area file holds instead of a single `:root` block, for the message. */
function shapeOf(code: string): string {
    const blocks = [...code.matchAll(/([^{};]*)\{/g)].map((match) => collapse(match[1]));
    if (blocks.length === 0) return 'no block at all';
    if (blocks.length === 1 && blocks[0] === ':root') return `text outside it: \`${collapse(code.replace(/:root\s*\{[^{}]*\}/, ' '))}\``;
    return `${blocks.length} blocks: ${blocks.map((block) => `\`${block}\``).join(', ')}`;
}

/** (d) Whatever keeps an area file from being one `:root { … }` of token declarations, each with its place. */
function impuritiesOf(file: string, css: string): string[] {
    const code = blankCssComments(css);
    const root = /^\s*:root\s*\{([^{}]*)\}\s*$/.exec(code);
    if (!root) return [`${file}  is not one \`:root { … }\` block alone — ${shapeOf(code)}`];
    const body = root[1];
    const bodyAt = code.indexOf('{') + 1;
    const problems: string[] = [];
    let cursor = 0;
    while (/\S/.test(body.slice(cursor))) {
        DECLARATION.lastIndex = cursor;
        const declaration = DECLARATION.exec(body);
        if (declaration && /\S/.test(declaration[2])) {
            cursor = DECLARATION.lastIndex;
            continue;
        }
        const start = cursor + body.slice(cursor).search(/\S/);
        const semicolon = body.indexOf(';', start);
        const end = semicolon === -1 ? body.length : semicolon + 1;
        problems.push(`${file}:${lineAt(code, bodyAt + start)}  \`${collapse(body.slice(start, end))}\``);
        cursor = end;
    }
    return problems;
}

// ---------------------------------------------------------------------------
// The checks: pure functions of a tree
// ---------------------------------------------------------------------------

interface Audit {
    /** Every file of the tree the scan reads (`isScanned`), sorted. */
    files: string[];
    /** Every `.css` directly in `AREA_DIR`. */
    areas: string[];
    /** Every `--lf-cmp-…:` of an area file, inside its `:root` or not: (d) judges the shape, (a) and (c) need the names. */
    definitions: Mention[];
    /** Every `var(--lf-cmp-…` of a `.svelte`. */
    reads: Mention[];
    /** Every other mention: a definition outside the area files, a read outside the components, anything else. */
    strays: Mention[];
    /** (d) Whatever keeps an area file from being one `:root` of declarations. */
    impurities: string[];
    /** The side-effect imports of every component that reads a token. */
    imports: Map<string, Set<string>>;
}

/** What a tree holds, read as the walk reads `src`: a path `isScanned` refuses is dropped first, so a synthetic tree is judged as the files of `src` are. */
function audit(tree: Tree): Audit {
    const files = Object.keys(tree).filter(isScanned).sort();
    const result: Audit = {files, areas: files.filter(isArea), definitions: [], reads: [], strays: [], impurities: [], imports: new Map()};
    for (const file of files) {
        for (const mention of mentionsIn(file, tree[file])) {
            if (isArea(file) && mention.kind === 'definition') result.definitions.push(mention);
            else if (isComponent(file) && mention.kind === 'var') result.reads.push(mention);
            else result.strays.push(mention);
        }
        if (isArea(file)) result.impurities.push(...impuritiesOf(file, tree[file]));
    }
    for (const file of new Set(result.reads.map((read) => read.file))) result.imports.set(file, sideEffectImportsIn(file, tree[file]));
    return result;
}

const placeOf = (mention: Mention): string => `${mention.file}:${mention.line}`;

function definitionsByName(definitions: Mention[]): Map<string, Mention[]> {
    const byName = new Map<string, Mention[]>();
    for (const definition of definitions) byName.set(definition.name, [...(byName.get(definition.name) ?? []), definition]);
    return byName;
}

/** (a) Every read that does not name, whole, a token defined exactly once. */
function unresolvedReads({definitions, reads}: Audit): string[] {
    const byName = definitionsByName(definitions);
    return reads.flatMap((read) => {
        if (!read.whole) return [`${placeOf(read)}  ${read.excerpt}  → the name runs on into code this gate cannot read`];
        const found = byName.get(read.name) ?? [];
        if (found.length === 1) return [];
        return [`${placeOf(read)}  ${read.name}  → ${found.length === 0 ? 'defined nowhere' : `defined ${found.length} times (${found.map(placeOf).join(', ')})`}`];
    });
}

/** (b) Every component that reads tokens of an area file it does not import, with the line to add. Reads (a) rejects are left to (a). */
function missingImports({definitions, reads, imports}: Audit): string[] {
    const byName = definitionsByName(definitions);
    const needs = new Map<string, Map<string, Set<string>>>();
    for (const read of reads) {
        const found = byName.get(read.name);
        if (!read.whole || !found || found.length !== 1) continue;
        const areas = needs.get(read.file) ?? new Map<string, Set<string>>();
        areas.set(found[0].file, (areas.get(found[0].file) ?? new Set<string>()).add(read.name));
        needs.set(read.file, areas);
    }
    const missing: string[] = [];
    for (const [file, areas] of needs) {
        for (const [area, names] of areas) {
            if (imports.get(file)?.has(specifierOf(area))) continue;
            const listed = names.size > 3 ? `${[...names].slice(0, 3).join(', ')} and ${names.size - 3} more` : [...names].join(', ');
            missing.push(`${file}  reads ${listed} from ${area} → add to its <script>: ${importOf(area)}`);
        }
    }
    return missing;
}

/** (c) Every token defined more than once, with all its places. */
function duplicateDefinitions({definitions}: Audit): string[] {
    return [...definitionsByName(definitions)].filter(([, found]) => found.length > 1).map(([name, found]) => `${name}  defined at ${found.map(placeOf).join(', ')}`);
}

/** (c) Every definition no component reads. */
function unusedDefinitions({definitions, reads}: Audit): string[] {
    const read = new Set(reads.filter((mention) => mention.whole).map((mention) => mention.name));
    return definitions.filter((definition) => !read.has(definition.name)).map((definition) => `${placeOf(definition)}  ${definition.name}`);
}

/** (d) What a stray mention is, and so what to do with it. */
function strayReason({file, kind}: Mention): string {
    if (isArea(file)) return kind === 'var' ? 'an alias: an area file defines tokens, it does not read them' : 'neither a definition nor a read';
    if (kind === 'definition') return 'a definition outside the area files: move it into the area file of its component';
    if (kind === 'var') return 'a read outside a component: (a)–(c) cannot check its name or its import';
    return 'a form this gate does not read';
}

/** (d) Every mention in a form (a)–(c) do not read. */
function strayMentions({strays}: Audit): string[] {
    return strays.map((mention) => `${placeOf(mention)}  ${mention.excerpt}  → ${strayReason(mention)}`);
}

/** (e) Whatever would let (a)–(d) pass by reading nothing. */
function emptyScans({areas, definitions, reads}: Audit): string[] {
    const problems: string[] = [];
    if (areas.length === 0) problems.push(`no area file: no .css directly in ${AREA_DIR}`);
    for (const area of areas) if (!definitions.some((definition) => definition.file === area)) problems.push(`${area}  defines no token`);
    if (reads.length === 0) problems.push('no component reads a token');
    return problems;
}

// ---------------------------------------------------------------------------
// The files of src
// ---------------------------------------------------------------------------

/** Every file under `dir` the scan reads (`isScanned`): no other file is opened, and `node_modules` is not even entered. */
function walk(dir: string, acc: string[] = []): string[] {
    for (const entry of readdirSync(join(FRONTEND, dir), {withFileTypes: true})) {
        const path = `${dir}/${entry.name}`;
        if (entry.isDirectory()) {
            if (entry.name !== 'node_modules') walk(path, acc);
        } else if (isScanned(path)) acc.push(path);
    }
    return acc;
}

let srcTreeCache: Tree | undefined;
let srcAuditCache: Audit | undefined;

/** The files of `src`, read once for every test below. */
function srcTree(): Tree {
    srcTreeCache ??= Object.fromEntries(walk('src').map((file) => [file, readFileSync(join(FRONTEND, file), 'utf8')]));
    return srcTreeCache;
}

/** The audit of the files of `src`, computed once. */
function srcAudit(): Audit {
    srcAuditCache ??= audit(srcTree());
    return srcAuditCache;
}

// ---------------------------------------------------------------------------
// Synthetic trees: one clean, then each rule broken once
// ---------------------------------------------------------------------------

const TABLE_CSS = `${AREA_DIR}/table.css`;
const MEDIA_CSS = `${AREA_DIR}/media.css`;
const DATA_TABLE = 'src/lib/components/table/DataTable.svelte';
const TABLE_IMPORT = "    import '$lib/theme/components/table.css';";

/** An area file as R-3 writes them: a header comment, then one `:root` of declarations with comments among them. */
const areaFile = (...declarations: string[]): string => ['/*', ' * Data tables.', ' */', ':root {', '    /* DataTable.svelte */', ...declarations.map((declaration) => `    ${declaration}`), '}', ''].join('\n');

/**
 * One area file of three tokens, and one component that reads them in every form R-3 left — a `style` attribute, a
 * rule, the fallback of another `var()`, a `.dark` rule — and names a fourth only in comments. Around them, a script
 * whose comments name tokens, and an `app.css` and an `app.html` that name none.
 */
function cleanTree(): Tree {
    return {
        [TABLE_CSS]: areaFile('--lf-cmp-datatable-border: #e2e8f0;', '--lf-cmp-datatable-border-dark: #334155; /* slate-700 */', '--lf-cmp-datatable-badge-bg: #f1f5f9;'),
        [DATA_TABLE]: [
            '<script lang="ts">',
            "    import {t} from '$lib/i18n';",
            TABLE_IMPORT,
            '</script>',
            '',
            '<!-- var(--lf-cmp-datatable-gone): a comment reads nothing -->',
            '<div class="t" style="color: var(--lf-cmp-datatable-border)"></div>',
            '',
            '<style>',
            '    /* var(--lf-cmp-datatable-gone) */',
            '    .t {',
            '        border: 1px solid var( --lf-cmp-datatable-border );',
            '        background: var(--broker-bg, var(--lf-cmp-datatable-badge-bg));',
            '    }',
            '    :global(.dark) .t {',
            '        border-color: var(--lf-cmp-datatable-border-dark);',
            '    }',
            '</style>',
            '',
        ].join('\n'),
        'src/lib/theme/drawnColors.ts': ['/** Colours drawn where a `var(--lf-cmp-*)` token cannot reach. */', "export const ROW_BG = 'rgba(251, 191, 36, 0.35)'; // was --lf-cmp-datatable-row-bg: a canvas", ''].join('\n'),
        'src/app.css': ':root {\n    --color-libre-green: #1a4031;\n}\n',
        'src/app.html': '<!doctype html>\n<html lang="en">\n    <head>%sveltekit.head%</head>\n</html>\n',
    };
}

/** The clean tree with edits to one file; an edit that does not apply is a broken case, and throws. */
function withEdits(path: string, ...edits: Array<[string, string]>): Tree {
    const tree = cleanTree();
    for (const [from, to] of edits) {
        if (!tree[path].includes(from)) throw new Error(`synthetic edit: ${path} has no \`${from}\``);
        tree[path] = tree[path].replace(from, to);
    }
    return tree;
}

/** The clean tree with one file replaced, or added. */
const withFile = (path: string, text: string): Tree => ({...cleanTree(), [path]: text});

type Verdict = Record<'a' | 'b' | 'c' | 'd' | 'e', string[]>;

/** What each check says about a tree: one list per check, all five empty when the tree keeps the rule. */
function verdictOf(tree: Tree): Verdict {
    const result = audit(tree);
    return {a: unresolvedReads(result), b: missingImports(result), c: [...duplicateDefinitions(result), ...unusedDefinitions(result)], d: [...result.impurities, ...strayMentions(result)], e: emptyScans(result)};
}

const CLEAN: Verdict = {a: [], b: [], c: [], d: [], e: []};

/** What (b) says of the clean component once its import is gone. */
const MISSING_TABLE_IMPORT = `${DATA_TABLE}  reads --lf-cmp-datatable-border, --lf-cmp-datatable-badge-bg, --lf-cmp-datatable-border-dark from ${TABLE_CSS} → add to its <script>: import '$lib/theme/components/table.css';`;

/**
 * A component naming tokens the way a test harness or the Designer Lab may: definitions in a `setProperty`, a `style`
 * attribute and a rule, a `getPropertyValue`, a read of a defined token without the import of its file, and a read of a
 * name defined nowhere. Where the scan reads it, it fails (a), (b) and (d).
 */
const ANY_FORM_SVELTE = [
    '<script lang="ts">',
    '    let el: HTMLElement;',
    "    const paint = () => el.style.setProperty('--lf-cmp-datatable-border', 'red');",
    "    const now = () => getComputedStyle(el).getPropertyValue('--lf-cmp-datatable-border');",
    '</script>',
    '',
    '<div bind:this={el} style="--lf-cmp-datatable-badge-bg: blue; color: var(--lf-cmp-datatable-border)"></div>',
    '',
    '<style>',
    '    div {',
    '        --lf-cmp-datatable-border-dark: #000;',
    '        color: var(--lf-cmp-lab-preview);',
    '    }',
    '</style>',
    '',
].join('\n');

/** The same forms in a script, as a test writes them: a `setProperty`, a `getPropertyValue`, a definition and a read in a string. Where the scan reads it, each one fails (d). */
const ANY_FORM_TS = [
    "import {expect, it} from 'vitest';",
    '',
    "it('paints the table border', () => {",
    "    document.documentElement.style.setProperty('--lf-cmp-datatable-border', 'red');",
    "    expect(getComputedStyle(document.documentElement).getPropertyValue('--lf-cmp-datatable-border')).toBe('red');",
    "    document.head.innerHTML = '<style>:root { --lf-cmp-datatable-badge-bg: blue; } p { color: var(--lf-cmp-lab-preview); }</style>';",
    '});',
    '',
].join('\n');

// ---------------------------------------------------------------------------
// The gate
// ---------------------------------------------------------------------------

describe('Component colour tokens — defined once in their area file, loaded by every component that reads them (R, R-3 gate)', () => {
    describe('the scanner, on synthetic trees', () => {
        it('passes a clean tree, and reads every form a component uses — a style attribute, a rule, a fallback, a .dark rule — and no comment', () => {
            const tree = cleanTree();
            expect(verdictOf(tree)).toEqual(CLEAN);
            const {definitions, reads, strays, imports} = audit(tree);
            expect(definitions.map(({line, name}) => `${line} ${name}`)).toEqual(['6 --lf-cmp-datatable-border', '7 --lf-cmp-datatable-border-dark', '8 --lf-cmp-datatable-badge-bg']);
            expect(reads.map(({line, name}) => `${line} ${name}`)).toEqual(['7 --lf-cmp-datatable-border', '12 --lf-cmp-datatable-border', '13 --lf-cmp-datatable-badge-bg', '16 --lf-cmp-datatable-border-dark']);
            expect(strays).toEqual([]);
            expect([...(imports.get(DATA_TABLE) ?? [])], 'a named import is not a side-effect import').toEqual(['$lib/theme/components/table.css']);
        });

        it('(a) fails a read of a name defined nowhere, or twice, and a name that runs on into code it cannot read', () => {
            expect(verdictOf(withEdits(DATA_TABLE, ['var(--lf-cmp-datatable-badge-bg)', 'var(--lf-cmp-datatable-badge-bgg)'])).a).toEqual([`${DATA_TABLE}:13  --lf-cmp-datatable-badge-bgg  → defined nowhere`]);

            const twice = withEdits(TABLE_CSS, ['--lf-cmp-datatable-badge-bg: #f1f5f9;', '--lf-cmp-datatable-badge-bg: #f1f5f9;\n    --lf-cmp-datatable-badge-bg: #e2e8f0;']);
            expect(verdictOf(twice).a).toEqual([`${DATA_TABLE}:13  --lf-cmp-datatable-badge-bg  → defined 2 times (${TABLE_CSS}:8, ${TABLE_CSS}:9)`]);

            const markup = withEdits(DATA_TABLE, ['style="color: var(--lf-cmp-datatable-border)"', 'style="color: var(--lf-cmp-datatable-{part})"']);
            expect(verdictOf(markup).a).toEqual([`${DATA_TABLE}:7  <div class="t" style="color: var(--lf-cmp-datatable-{part})"></div>  → the name runs on into code this gate cannot read`]);

            // A name assembled in a script fails even when the part the scanner sees is a real token.
            const template = withEdits(DATA_TABLE, [TABLE_IMPORT, `${TABLE_IMPORT}\n    const edge = (side: string) => \`var(--lf-cmp-datatable-border\${side})\`;`]);
            expect(verdictOf(template).a).toEqual([expect.stringMatching(/^src\/lib\/components\/table\/DataTable\.svelte:4 .* → the name runs on into code this gate cannot read$/)]);
            const concatenated = withEdits(DATA_TABLE, [TABLE_IMPORT, `${TABLE_IMPORT}\n    const badge = (part: string) => 'var(--lf-cmp-datatable-' + part + ')';`]);
            expect(verdictOf(concatenated).a).toEqual([expect.stringMatching(/^src\/lib\/components\/table\/DataTable\.svelte:4 .* → the name runs on into code this gate cannot read$/)]);
        });

        it('(b) fails a component that reads a token without the side-effect import of its file, and names the line to add', () => {
            const notImports = [
                '',
                "    // import '$lib/theme/components/table.css';",
                "    /* import '$lib/theme/components/table.css'; */",
                "    import '$lib/theme/components/table.css?inline';",
                "    import '$lib/theme/components/table.css?url';",
                "    import '../../theme/components/table.css';",
                "    import tableCss from '$lib/theme/components/table.css';",
                "    import('$lib/theme/components/table.css');",
                '    const note = "import \'$lib/theme/components/table.css\'";',
                "    import '$lib/theme/components/media.css';",
            ];
            for (const line of notImports) expect(verdictOf(withEdits(DATA_TABLE, [TABLE_IMPORT, line])).b, line || '(no import at all)').toEqual([MISSING_TABLE_IMPORT]);

            // The statement in markup is text, not an import.
            expect(verdictOf(withEdits(DATA_TABLE, [TABLE_IMPORT, ''], ['<div class="t"', `<pre>\n${TABLE_IMPORT}\n</pre>\n<div class="t"`])).b).toEqual([MISSING_TABLE_IMPORT]);

            // Either script imports for the module, in either quote style, with or without the semicolon.
            expect(verdictOf(withEdits(DATA_TABLE, [TABLE_IMPORT, ''], ['<script lang="ts">', `<script module lang="ts">\n${TABLE_IMPORT}\n</script>\n\n<script lang="ts">`]))).toEqual(CLEAN);
            expect(verdictOf(withEdits(DATA_TABLE, [TABLE_IMPORT, ''], ['<script lang="ts">', `<script context="module">\n${TABLE_IMPORT}\n</script>\n\n<script lang="ts">`]))).toEqual(CLEAN);
            expect(verdictOf(withEdits(DATA_TABLE, [TABLE_IMPORT, '    import "$lib/theme/components/table.css"']))).toEqual(CLEAN);
        });

        it('(c) fails a token defined twice — in one file or across two — and one that only comments read', () => {
            const twiceInFile = withEdits(TABLE_CSS, ['--lf-cmp-datatable-badge-bg: #f1f5f9;', '--lf-cmp-datatable-badge-bg: #f1f5f9;\n    --lf-cmp-datatable-badge-bg: #e2e8f0;']);
            expect(verdictOf(twiceInFile).c).toEqual([`--lf-cmp-datatable-badge-bg  defined at ${TABLE_CSS}:8, ${TABLE_CSS}:9`]);

            const acrossFiles = {...cleanTree(), [MEDIA_CSS]: areaFile('--lf-cmp-datatable-border: #e5e7eb;')};
            expect(verdictOf(acrossFiles).c).toEqual([`--lf-cmp-datatable-border  defined at ${MEDIA_CSS}:6, ${TABLE_CSS}:6`]);

            const commentsOnly = withEdits(TABLE_CSS, ['--lf-cmp-datatable-badge-bg: #f1f5f9;', '--lf-cmp-datatable-badge-bg: #f1f5f9;\n    --lf-cmp-datatable-gone: #000;']);
            expect(verdictOf(commentsOnly).c).toEqual([`${TABLE_CSS}:9  --lf-cmp-datatable-gone`]);
        });

        it('(d) fails an area file that is anything but one :root block of token declarations', () => {
            const values = areaFile('--lf-cmp-datatable-border: #e2e8f0;', '--lf-cmp-datatable-mark: url("data:image/svg+xml;utf8,<svg/>");', '--lf-cmp-datatable-mix: color-mix(in srgb, var(--lf-surface, rgb(0 0 0)) 50%, transparent);');
            expect(impuritiesOf(TABLE_CSS, values), 'a value may hold a quoted ; and parentheses three deep').toEqual([]);

            const declarations = areaFile('--lf-cmp-datatable-border: #e2e8f0;', 'color: red;', '--lf-cmp-DataTable-x: #fff;', '--lf-cmp-datatable-empty: ;', '--lf-cmp-datatable-last: #000');
            expect(impuritiesOf(TABLE_CSS, declarations)).toEqual([`${TABLE_CSS}:7  \`color: red;\``, `${TABLE_CSS}:8  \`--lf-cmp-DataTable-x: #fff;\``, `${TABLE_CSS}:9  \`--lf-cmp-datatable-empty: ;\``, `${TABLE_CSS}:10  \`--lf-cmp-datatable-last: #000\``]);

            const shape = (text: string): string[] => impuritiesOf(TABLE_CSS, text);
            const one = areaFile('--lf-cmp-datatable-border: #e2e8f0;');
            expect(shape(`${one}.dark :root {\n    --lf-cmp-datatable-border: #334155;\n}\n`)).toEqual([`${TABLE_CSS}  is not one \`:root { … }\` block alone — 2 blocks: \`:root\`, \`.dark :root\``]);
            expect(shape(`${one}.t {\n    color: var(--lf-cmp-datatable-border);\n}\n`)).toEqual([`${TABLE_CSS}  is not one \`:root { … }\` block alone — 2 blocks: \`:root\`, \`.t\``]);
            expect(shape('@media (prefers-contrast: more) {\n    :root {\n        --lf-cmp-datatable-border: #000;\n    }\n}\n')).toEqual([`${TABLE_CSS}  is not one \`:root { … }\` block alone — 2 blocks: \`@media (prefers-contrast: more)\`, \`:root\``]);
            expect(shape(`@import 'x.css';\n${one}`)).toEqual([`${TABLE_CSS}  is not one \`:root { … }\` block alone — text outside it: \`@import 'x.css';\``]);
            expect(shape('/* only a header */\n')).toEqual([`${TABLE_CSS}  is not one \`:root { … }\` block alone — no block at all`]);

            // Through the audit: an impure area file is a (d) failure of the whole tree, and its definitions still count for (a) and (c).
            const impure = verdictOf(withFile(TABLE_CSS, `${cleanTree()[TABLE_CSS]}.dark :root {\n    --lf-cmp-datatable-border-dark: #334155;\n}\n`));
            expect(impure.d).toEqual([`${TABLE_CSS}  is not one \`:root { … }\` block alone — 2 blocks: \`:root\`, \`.dark :root\``]);
            expect(impure.c).toEqual([`--lf-cmp-datatable-border-dark  defined at ${TABLE_CSS}:7, ${TABLE_CSS}:11`]);
        });

        it('(d) fails a token named anywhere else, or in any other form: a local definition, a directive, a script, app.css, app.html, an alias', () => {
            const tree: Tree = {
                ...cleanTree(),
                [TABLE_CSS]: areaFile('--lf-cmp-datatable-border: #e2e8f0;', '--lf-cmp-datatable-border-dark: #334155;', '--lf-cmp-datatable-badge-bg: var(--lf-cmp-datatable-border);'),
                'src/lib/components/table/Local.svelte': [
                    '<script lang="ts">',
                    TABLE_IMPORT,
                    '    let el: HTMLElement;',
                    "    $effect(() => el.style.setProperty('--lf-cmp-datatable-border', 'red'));",
                    "    const now = () => getComputedStyle(el).getPropertyValue('--lf-cmp-datatable-border');",
                    '</script>',
                    '',
                    '<div bind:this={el} style:--lf-cmp-datatable-border="red" style="--lf-cmp-datatable-badge-bg: blue; color: var(--lf-cmp-datatable-border)"></div>',
                    '',
                    '<style>',
                    '    div {',
                    '        --lf-cmp-datatable-border-dark: #000;',
                    '        color: var(--lf-cmp-datatable-border-dark);',
                    '    }',
                    '</style>',
                    '',
                ].join('\n'),
                'src/lib/utils/tokenColor.ts': "export const BORDER = 'var(--lf-cmp-datatable-border)';\n",
                'src/app.css': ':root {\n    --color-libre-green: #1a4031;\n    --lf-cmp-datatable-border: red;\n}\n',
                'src/app.html': '<style>\n    body { color: var(--lf-cmp-datatable-border); }\n</style>\n',
            };
            const LOCAL = 'src/lib/components/table/Local.svelte';
            const definition = 'a definition outside the area files: move it into the area file of its component';
            const outsideRead = 'a read outside a component: (a)–(c) cannot check its name or its import';
            expect(audit(tree).strays.map((mention) => `${placeOf(mention)} ${strayReason(mention)}`)).toEqual([
                `src/app.css:3 ${definition}`,
                `src/app.html:2 ${outsideRead}`,
                `${LOCAL}:4 ${definition}`,
                `${LOCAL}:5 a form this gate does not read`,
                `${LOCAL}:8 ${definition}`,
                `${LOCAL}:8 ${definition}`,
                `${LOCAL}:12 ${definition}`,
                `${TABLE_CSS}:8 an alias: an area file defines tokens, it does not read them`,
                `src/lib/utils/tokenColor.ts:1 ${outsideRead}`,
            ]);
            expect(verdictOf(tree).d).toContain(`src/lib/utils/tokenColor.ts:1  export const BORDER = 'var(--lf-cmp-datatable-border)';  → ${outsideRead}`);
            expect(impuritiesOf(TABLE_CSS, tree[TABLE_CSS]), 'the alias is a well-formed declaration: the stray check is what catches it').toEqual([]);
        });

        it('(e) fails a scan that reads nothing — on which every other check passes', () => {
            expect(verdictOf({})).toEqual({...CLEAN, e: [`no area file: no .css directly in ${AREA_DIR}`, 'no component reads a token']});
            expect(verdictOf({...cleanTree(), [MEDIA_CSS]: ':root {\n}\n'}).e).toEqual([`${MEDIA_CSS}  defines no token`]);
        });

        it('(e) skips by path every test, mock and Designer Lab file — and nothing that merely resembles one', () => {
            const expected: Record<string, boolean> = {
                // Tests, mocks and the Lab: never opened.
                'src/themeComponentTokens.gate.test.ts': false,
                'src/lib/components/table/DataTable.test.ts': false,
                'src/lib/utils/core/__tests__/escapeHtml.test.ts': false,
                'src/__tests__/harness/TooltipProbe.svelte': false,
                'src/__tests__/palettes.ts': false,
                'src/__mocks__/$app/navigation.ts': false,
                'src/routes/designer-lab/+page.svelte': false,
                'src/lib/dev/designer-lab/TokenSwatch.svelte': false,
                'src/lib/dev/designer-lab/lab.css': false,
                // The app — the component beside its test, a runes module — and the near misses of the Lab's prefixes: a sibling directory, the parent, the name elsewhere.
                [DATA_TABLE]: true,
                [TABLE_CSS]: true,
                'src/app.css': true,
                'src/app.html': true,
                'src/lib/theme/drawnColors.ts': true,
                'src/lib/stores/app/notify.svelte.ts': true,
                'src/routes/designer-lab-old/+page.svelte': true,
                'src/lib/dev/TokenSwatch.svelte': true,
                'src/lib/designer-lab/TokenSwatch.svelte': true,
            };
            expect(Object.fromEntries(Object.keys(expected).map((path) => [path, isScanned(path)]))).toEqual(expected);
        });

        it('(e) a test or a Designer Lab file may name tokens in any form, and every check stays green — the same text anywhere else turns red', () => {
            const exempt: Tree = {
                'src/routes/designer-lab/+page.svelte': ANY_FORM_SVELTE,
                'src/lib/dev/designer-lab/liveTokens.ts': ANY_FORM_TS,
                'src/lib/components/table/DataTable.test.ts': ANY_FORM_TS,
                'src/__tests__/harness/TokenProbe.svelte': ANY_FORM_SVELTE,
                'src/__mocks__/$app/environment.ts': ANY_FORM_TS,
            };
            for (const [path, text] of Object.entries(exempt)) expect(verdictOf(withFile(path, text)), path).toEqual(CLEAN);
            expect(audit({...cleanTree(), ...exempt}).files, 'not one of them is read, and every other file is').toEqual(Object.keys(cleanTree()).sort());

            // The control: the same text where the scan reads it, every form reported — in a component by (a), (b) and (d), in a script by (d) alone, its var() included.
            const failing = (verdict: Verdict): string[] => Object.keys(verdict).filter((check) => verdict[check as keyof Verdict].length > 0);
            const strayForms = (tree: Tree): string[] => audit(tree).strays.map((mention) => `${placeOf(mention)} ${mention.kind}`);

            const component = 'src/lib/components/table/TokenProbe.svelte';
            const inComponent = verdictOf(withFile(component, ANY_FORM_SVELTE));
            expect(failing(inComponent)).toEqual(['a', 'b', 'd']);
            expect(inComponent.a).toEqual([`${component}:12  --lf-cmp-lab-preview  → defined nowhere`]);
            expect(inComponent.b).toEqual([`${component}  reads --lf-cmp-datatable-border from ${TABLE_CSS} → add to its <script>: ${importOf(TABLE_CSS)}`]);
            expect(strayForms(withFile(component, ANY_FORM_SVELTE))).toEqual([`${component}:3 definition`, `${component}:4 other`, `${component}:7 definition`, `${component}:11 definition`]);

            const script = 'src/lib/theme/tokenProbe.ts';
            expect(failing(verdictOf(withFile(script, ANY_FORM_TS)))).toEqual(['d']);
            expect(strayForms(withFile(script, ANY_FORM_TS))).toEqual([`${script}:4 definition`, `${script}:5 other`, `${script}:6 definition`, `${script}:6 var`]);

            // Not read, so not counted either: a token only the Lab reads is, for (c), a token no component reads.
            const labOnly: Tree = {
                ...withEdits(TABLE_CSS, ['--lf-cmp-datatable-badge-bg: #f1f5f9;', '--lf-cmp-datatable-badge-bg: #f1f5f9;\n    --lf-cmp-datatable-lab-only: #000;']),
                'src/routes/designer-lab/+page.svelte': '<div style="color: var(--lf-cmp-datatable-lab-only)"></div>\n',
            };
            expect(verdictOf(labOnly)).toEqual({...CLEAN, c: [`${TABLE_CSS}:9  --lf-cmp-datatable-lab-only`]});
        });
    });

    describe('the files of src', () => {
        it('(e) the walk reads every component, stylesheet and script of src — and no test, mock or Designer Lab file', () => {
            // The files the walk opened: srcAudit().files could not tell, since audit drops these paths again.
            const files = Object.keys(srcTree());
            expect(files.filter(isComponent).length, 'the walk reaches the components').toBeGreaterThan(100);
            expect(files, 'the stylesheet and the document of the app are read').toEqual(expect.arrayContaining(['src/app.css', 'src/app.html']));
            const unwanted = files.filter((file) => file.endsWith('.test.ts') || file.includes('/__tests__/') || file.includes('/__mocks__/') || isDesignerLab(file));
            expect(unwanted, 'tests, mocks and the Designer Lab are not opened at all: they may name tokens in any form, and none of them is the app').toEqual([]);
        });

        it('(e) the scan finds area files, every one defining tokens, and components reading them', () => {
            expect(emptyScans(srcAudit()), 'the scan reads nothing (a)–(d) need: fix the walk or the patterns — never relax this, every other check passes on an empty scan').toEqual([]);
        });

        it('(a) every token a component reads is defined exactly once, and named whole', () => {
            expect(unresolvedReads(srcAudit()), 'a component reads a token not defined exactly once: define it in the area file of its component, or correct the name — and spell out whole a name assembled at run time').toEqual([]);
        });

        it('(b) every component imports the area file of every token it reads', () => {
            expect(missingImports(srcAudit()), 'a component reads tokens of an area file it does not import: on any screen where no other component has loaded that file, the property is unset — add the line shown to its <script>').toEqual([]);
        });

        it('(c) no token is defined twice', () => {
            expect(duplicateDefinitions(srcAudit()), 'a token defined twice is settled by load order: keep one definition, in the area file of the component it is named after').toEqual([]);
        });

        it('(c) every token defined is read by a component', () => {
            expect(unusedDefinitions(srcAudit()), 'a token no component reads: delete its definition (export only what is used), or read it where it was meant to be read').toEqual([]);
        });

        it('(d) every area file is one :root block of token declarations, and nothing else', () => {
            expect(srcAudit().impurities, 'an area file holds one :root { … } of `--lf-cmp-<component>-<role>: <value>;` declarations and comments, nothing else: rules belong in the components, values here').toEqual([]);
        });

        it("(d) outside the area files, code names a token only as a component's var() read", () => {
            expect(strayMentions(srcAudit()), 'a token named in a form (a)–(c) do not read: define tokens only in the area files, read them only as var(--lf-cmp-…) in a .svelte — or teach this gate the new form, with the rule it serves').toEqual([]);
        });

        it('every check bites on these very files: one mutation each, in memory, turns it red', () => {
            const {reads, definitions} = srcAudit();
            const read = reads.find((mention) => definitions.some((found) => found.name === mention.name));
            const definition = definitions.find((mention) => mention.name === read?.name);
            if (!read || !definition) throw new Error('no component reads a defined token — see (e)');
            const area = definition.file;

            // The area files, their readers and app.css: every other file the walk reads names no token (the test above), so it cannot change a verdict — re-reading it for each mutation would only cost time. Tests and the Designer Lab need no place here: the walk never opens them.
            const readers = new Set(reads.map((mention) => mention.file));
            const tree = Object.fromEntries(Object.entries(srcTree()).filter(([path]) => isArea(path) || readers.has(path) || path === 'src/app.css'));
            expect(verdictOf(tree), 'the files the mutations start from keep the rule on their own').toEqual(CLEAN);
            const mutated = (path: string, text: string): Verdict => {
                expect(text, `the mutation of ${path} applies`).not.toBe(tree[path]);
                return verdictOf({...tree, [path]: text});
            };
            const declaration = new RegExp(`(?<![\\w-])${read.name}\\s*:[^;]*;`);

            const renamed = mutated(
                area,
                tree[area].replace(declaration, (found) => found.replace(read.name, `${read.name}-gone`)),
            );
            expect(renamed.a, '(a) its definition renamed away').toContain(`${placeOf(read)}  ${read.name}  → defined nowhere`);

            const withoutImport = tree[read.file]
                .split('\n')
                .filter((line) => !line.includes(`'${specifierOf(area)}'`))
                .join('\n');
            const unimported = mutated(read.file, withoutImport);
            expect(
                unimported.b.map((entry) => entry.replace(/ reads .* from /, ' reads … from ')),
                '(b) its import dropped',
            ).toEqual([`${read.file}  reads … from ${area} → add to its <script>: ${importOf(area)}`]);

            const twice = mutated(
                area,
                tree[area].replace(declaration, (found) => `${found}\n    ${found}`),
            );
            expect(twice.c, '(c) its definition repeated').toEqual([`${read.name}  defined at ${placeOf(definition)}, ${area}:${definition.line + 1}`]);

            const rule = mutated(area, `${tree[area]}\n.gate-probe {\n    color: var(${read.name});\n}\n`);
            expect(rule.d, '(d) a rule in its area file').toEqual([`${area}  is not one \`:root { … }\` block alone — 2 blocks: \`:root\`, \`.gate-probe\``, expect.stringContaining('→ an alias: an area file defines tokens, it does not read them')]);

            const elsewhere = mutated('src/app.css', `${tree['src/app.css']}\n:root {\n    ${read.name}: red;\n}\n`);
            expect(elsewhere.d, '(d) a definition in app.css').toEqual([expect.stringMatching(/^src\/app\.css:\d+ .* → a definition outside the area files: move it into the area file of its component$/)]);
        });
    });
});
