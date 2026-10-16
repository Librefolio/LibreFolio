/**
 * escapeHtml.single.test.ts — C-34: the app has one HTML escaper, `escapeHtml`, and no copy of it.
 *
 * ## What it protects (C-34)
 *
 * `src/lib/utils/core/escapeHtml.ts` is the one function that escapes text for markup built by hand — the ECharts
 * tooltips, the `html` cells, every `{@html}`. It escapes five characters, `& < > " '`, so that its output is safe in an
 * attribute too, whichever quote the call site uses. It replaced thirteen copies in two variants; a new copy is how the
 * defect comes back — `CorrelationHeatmap`'s, which forgets both quotes, is the live case. This gate scans the
 * production sources for an escaper's signature and fails on any outside a short, reasoned allowlist.
 *
 * The signature is `&` mapped to `&amp;`, in three forms: a `.replace(`/`.replaceAll(` call (`/&/g` or `'&'` to
 * `'&amp;'`), a table entry (`{'&': '&amp;'}`, `['&', '&amp;']`), a switch case (`case '&': return '&amp;'`). The
 * decoding direction (`&amp;` → `&`, `src/lib/stores/app/toastStore.svelte.ts:63`) is not an escaper and does not match.
 * Allowed:
 * - `src/lib/utils/core/escapeHtml.ts` — the escaper;
 * - `src/lib/utils/inlineMath.ts` — KaTeX's variant, which keeps the apostrophe because KaTeX reads it as prime
 *   notation (documented in both files);
 * An allowlisted file that no longer holds a copy fails the gate, so the list cannot go stale.
 *
 * ## Why it was red before C-34
 *
 * `src/lib/features/risk/CorrelationHeatmap.svelte` held a local `escapeHtml` that escaped only `& < >` (Y9 removed it), and
 * `TransactionBulkModal.svelte` an inline three-character copy for an `html` cell, allowed here as a temporary entry
 * until its workstream replaced it with `escapeHtml` (`60917185c`).
 *
 * ## How it reads, and what it cannot see
 *
 * Production sources: `src/**` `.ts` and `.svelte`, without `*.test.ts`, `*.spec.ts`, `.d.ts`, `__tests__/`,
 * `__mocks__/` and the generated, gitignored API clients. Comments are blanked before matching, offsets kept so the
 * reported lines are the file's; in a `.svelte` file only the `<script>` blocks are read — markup text holds apostrophes
 * that would derail a string-aware scanner. The blanking is a small lexer that skips strings, templates and regex
 * literals, so `'https://…'` or `/\/\//` is not taken for a comment. The forms are a floor: an escaper written in a
 * markup expression (`{@html s.replace(…)}`), or built without the literal `&amp;`, is not seen. The synthetic controls
 * pin what the scanner reads before the tree is judged.
 *
 * Registered in chart-safety-unit (scripts/test_runner/_frontend_portfolio.py).
 */
import {existsSync, readdirSync, readFileSync} from 'node:fs';
import {basename, dirname, join, relative, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {describe, expect, it} from 'vitest';

// ---------------------------------------------------------------------------
// Where the sources are
// ---------------------------------------------------------------------------

/** `frontend/`: the nearest directory above this file holding `vitest.config.ts` and `src/` — found, not counted, so the file can move. */
function frontendRoot(): string {
    const here = dirname(fileURLToPath(import.meta.url));
    for (let dir = here; ; dir = dirname(dir)) {
        if (existsSync(join(dir, 'vitest.config.ts')) && existsSync(join(dir, 'src'))) return dir;
        if (dirname(dir) === dir) throw new Error(`no frontend/ (vitest.config.ts beside src/) above ${here}`);
    }
}

const FRONTEND = frontendRoot();
const SRC = join(FRONTEND, 'src');

/** Written by `./dev.py api sync` and `frontend/scripts/generate-tools-client.mjs`; gitignored, never hand-written. */
const GENERATED = new Set(['src/lib/api/generated.ts', 'src/lib/api/generated-tools.ts', 'src/lib/api/tool-contract-map.generated.ts']);

/** Whether a path (relative to `frontend/`) is a production source this gate reads. */
function isProductionSource(path: string): boolean {
    if (!/\.(ts|svelte)$/.test(path) || /\.(test|spec)\.ts$/.test(path) || path.endsWith('.d.ts')) return false;
    if (path.split('/').some((segment) => segment === '__tests__' || segment === '__mocks__' || segment === 'node_modules')) return false;
    return !GENERATED.has(path);
}

function sourceFiles(dir: string = SRC, acc: string[] = []): string[] {
    for (const entry of readdirSync(dir, {withFileTypes: true})) {
        const full = join(dir, entry.name);
        if (entry.isDirectory()) sourceFiles(full, acc);
        else if (entry.isFile()) {
            const path = relative(FRONTEND, full).split(sep).join('/');
            if (isProductionSource(path)) acc.push(path);
        }
    }
    return acc.sort();
}

// ---------------------------------------------------------------------------
// Reading code: comments blanked, offsets kept
// ---------------------------------------------------------------------------

/** The role of a character of a script: code, comment, or literal (a string, a template's text, a regex). */
const CODE = 0;
const COMMENT = 1;
const LITERAL = 2;

/** Words after which a `/` opens a regular expression instead of dividing. */
const REGEX_AFTER_WORD = new Set(['return', 'typeof', 'instanceof', 'in', 'of', 'new', 'delete', 'void', 'throw', 'case', 'do', 'else', 'yield', 'await']);
/** Punctuation after which a `/` opens a regular expression instead of dividing. */
const REGEX_AFTER_PUNCTUATION = new Set(['(', ',', '=', ':', '[', '!', '&', '|', '?', '{', '}', ';', '+', '-', '*', '%', '<', '>', '~', '^']);

const isSpace = (code: number): boolean => code <= 32 || code === 0xa0 || code === 0xfeff || code === 0x2028 || code === 0x2029;
const isWord = (code: number): boolean => (code >= 48 && code <= 57) || (code >= 65 && code <= 90) || (code >= 97 && code <= 122) || code === 95 || code === 36 || code > 127;

/** Every character but newlines turned into a space: lengths, offsets and line numbers survive. */
const blank = (text: string): string => text.replace(/[^\n]/g, ' ');

/**
 * The role of every character of a JS/TS script. A small lexer, not a parser: enough to tell a `//` inside
 * `'https://…'`, a template or `/\/\//` from a comment. Whether a `/` opens a regex or divides is guessed from the token
 * before it, the usual heuristic; strings and regexes never span a line, so a wrong guess costs at most one line.
 */
function classify(src: string): Uint8Array {
    const n = src.length;
    const kinds = new Uint8Array(n).fill(CODE);
    const mark = (from: number, to: number, kind: number): void => {
        kinds.fill(kind, from, Math.min(to, n));
    };

    const quoted = (start: number): number => {
        const quote = src[start];
        let i = start + 1;
        while (i < n && src[i] !== quote && src[i] !== '\n') i += src[i] === '\\' ? 2 : 1;
        const end = i < n && src[i] === quote ? i + 1 : Math.min(i, n);
        mark(start, end, LITERAL);
        return end;
    };

    /** A regex literal from `start`, or `start` itself when none closes on its line — then the `/` divides. */
    const regex = (start: number): number => {
        let inClass = false;
        let i = start + 1;
        while (i < n) {
            const c = src[i];
            if (c === '\n' || c === '\r') return start;
            if (c === '\\') {
                if (src[i + 1] === '\n') return start;
                i += 2;
                continue;
            }
            if (c === '/' && !inClass) break;
            if (c === '[') inClass = true;
            else if (c === ']') inClass = false;
            i++;
        }
        if (i >= n) return start;
        i++;
        while (i < n && isWord(src.charCodeAt(i))) i++;
        mark(start, i, LITERAL);
        return i;
    };

    const template = (start: number): number => {
        let segment = start;
        let i = start + 1;
        while (i < n) {
            const c = src[i];
            if (c === '\\') {
                i += 2;
            } else if (c === '`') {
                mark(segment, i + 1, LITERAL);
                return i + 1;
            } else if (c === '$' && src[i + 1] === '{') {
                mark(segment, i + 2, LITERAL);
                const close = code(i + 2, true);
                segment = close;
                i = close + 1;
            } else {
                i++;
            }
        }
        mark(segment, n, LITERAL);
        return n;
    };

    /** Code from `start`; when `nested`, it stops at the `}` closing a `${` and returns that index. */
    function code(start: number, nested: boolean): number {
        let depth = 0;
        let regexAllowed = true;
        let i = start;
        while (i < n) {
            const c = src[i];
            const charCode = src.charCodeAt(i);
            if (c === '/' && src[i + 1] === '/') {
                const eol = src.indexOf('\n', i);
                const end = eol === -1 ? n : eol;
                mark(i, end, COMMENT);
                i = end;
            } else if (c === '/' && src[i + 1] === '*') {
                const close = src.indexOf('*/', i + 2);
                const end = close === -1 ? n : close + 2;
                mark(i, end, COMMENT);
                i = end;
            } else if (c === '/') {
                const end = regexAllowed ? regex(i) : i;
                if (end > i) {
                    i = end;
                    regexAllowed = false;
                } else {
                    i++;
                    regexAllowed = true;
                }
            } else if (c === "'" || c === '"') {
                i = quoted(i);
                regexAllowed = false;
            } else if (c === '`') {
                i = template(i);
                regexAllowed = false;
            } else if (isSpace(charCode)) {
                i++;
            } else if (isWord(charCode)) {
                let j = i + 1;
                while (j < n && isWord(src.charCodeAt(j))) j++;
                regexAllowed = REGEX_AFTER_WORD.has(src.slice(i, j));
                i = j;
            } else {
                if (nested && c === '}') {
                    if (depth === 0) return i;
                    depth--;
                } else if (nested && c === '{') {
                    depth++;
                }
                regexAllowed = REGEX_AFTER_PUNCTUATION.has(c);
                i++;
            }
        }
        return n;
    }

    code(0, false);
    return kinds;
}

/** The `>` that ends the tag opened before `from`, outside quoted attribute values (`generics="A<B>"`); -1 when none. */
function tagEnd(markup: string, from: number): number {
    let quote: string | null = null;
    for (let k = from; k < markup.length; k++) {
        const c = markup[k];
        if (quote) {
            if (c === quote) quote = null;
        } else if (c === '"' || c === "'") {
            quote = c;
        } else if (c === '>') {
            return k;
        }
    }
    return -1;
}

/** Every character outside the `<script>` blocks of a Svelte component blanked, HTML comments first: offsets stay the file's. */
function scriptBlocksOf(markup: string): string {
    const bodies: Array<[number, number]> = [];
    const closing = /<\/script\s*>/gi;
    let i = markup.indexOf('<');
    while (i !== -1) {
        if (markup.startsWith('<!--', i)) {
            const close = markup.indexOf('-->', i + 4);
            if (close === -1) break;
            i = markup.indexOf('<', close + 3);
        } else if (markup.slice(i, i + 7).toLowerCase() === '<script' && /[\s>]/.test(markup.charAt(i + 7))) {
            const open = tagEnd(markup, i + 7);
            if (open === -1) break;
            closing.lastIndex = open + 1;
            const close = closing.exec(markup);
            bodies.push([open + 1, close ? close.index : markup.length]);
            if (!close) break;
            i = markup.indexOf('<', close.index + close[0].length);
        } else {
            i = markup.indexOf('<', i + 1);
        }
    }
    let out = '';
    let last = 0;
    for (const [start, end] of bodies) {
        out += blank(markup.slice(last, start)) + markup.slice(start, end);
        last = end;
    }
    return out + blank(markup.slice(last));
}

/** A source as the scans read it: its scripts with the comments blanked, and the role of each character. */
interface Code {
    text: string;
    kinds: Uint8Array;
}

function codeOf(file: string, source: string): Code {
    const script = file.endsWith('.svelte') ? scriptBlocksOf(source) : source;
    const kinds = classify(script);
    let text = '';
    let start = 0;
    while (start < script.length) {
        const comment = kinds[start] === COMMENT;
        let end = start + 1;
        while (end < script.length && (kinds[end] === COMMENT) === comment) end++;
        text += comment ? blank(script.slice(start, end)) : script.slice(start, end);
        start = end;
    }
    return {text, kinds};
}

/** The 1-based line of `offset` in `text`. */
function lineAt(text: string, offset: number): number {
    let line = 1;
    for (let newline = text.indexOf('\n'); newline !== -1 && newline < offset; newline = text.indexOf('\n', newline + 1)) line++;
    return line;
}

// ---------------------------------------------------------------------------
// The escaper's signature
// ---------------------------------------------------------------------------

/** `&` mapped to `&amp;`, in the three forms a copy takes. The decoding direction (`&amp;` → `&`) matches none. */
const ESCAPER_FORMS: ReadonlyArray<{form: string; pattern: RegExp}> = [
    // `.replace(/&/g, '&amp;')`, `.replaceAll('&', '&amp;')`: the form of every copy the tree has held.
    {form: 'replace call', pattern: /\.replace(?:All)?\(\s*(?:\/&\/[a-z]*|(['"`])&\1)\s*,\s*(['"`])&amp;\2\s*\)/g},
    // `{'&': '&amp;'}`, `['&', '&amp;']`: the table behind `.replace(/[&<>"']/g, (c) => table[c])`.
    {form: 'table entry', pattern: /(['"`])&\1\s*[:,]\s*(['"`])&amp;\2/g},
    // `case '&': return '&amp;'`.
    {form: 'switch case', pattern: /\bcase\s*(['"`])&\1\s*:\s*return\s*(['"`])&amp;\2/g},
];

/** One escaper found: where, and in which form. One per line: a replace call is also a table-shaped pair. */
interface Escaper {
    file: string;
    line: number;
    form: string;
}

/** The escapers of one source, outside comments and — in a component — outside markup. */
function escapersIn(file: string, source: string): Escaper[] {
    const {text} = codeOf(file, source);
    const byLine = new Map<number, Escaper>();
    for (const {form, pattern} of ESCAPER_FORMS) {
        for (const match of text.matchAll(pattern)) {
            const line = lineAt(text, match.index);
            if (!byLine.has(line)) byLine.set(line, {file, line, form});
        }
    }
    return [...byLine.values()].sort((left, right) => left.line - right.line);
}

interface TreeScan {
    /** Every production source read, relative to `frontend/`. */
    files: string[];
    escapers: Escaper[];
}

let treeScan: TreeScan | undefined;

/** The production tree, scanned once per run. Every form holds the literal `&amp;`, so a file without it is not lexed. */
function scanTree(): TreeScan {
    if (!treeScan) {
        const files = sourceFiles();
        const escapers = files.flatMap((file) => {
            const source = readFileSync(join(FRONTEND, file), 'utf8');
            return source.includes('&amp;') ? escapersIn(file, source) : [];
        });
        treeScan = {files, escapers};
    }
    return treeScan;
}

/** The copies allowed to exist, each with its reason. */
const ALLOWED: ReadonlyArray<{entry: string; matches: (path: string) => boolean; why: string}> = [
    {entry: 'src/lib/utils/core/escapeHtml.ts', matches: (path) => path === 'src/lib/utils/core/escapeHtml.ts', why: 'the one escaper'},
    {entry: 'src/lib/utils/inlineMath.ts', matches: (path) => path === 'src/lib/utils/inlineMath.ts', why: "KaTeX's variant: it keeps the apostrophe, which KaTeX reads as prime notation (documented in both files)"},
];

const isAllowed = (file: string): boolean => ALLOWED.some((entry) => entry.matches(file));
const describeEscaper = (found: Escaper): string => `${found.file}:${found.line}`;

// ---------------------------------------------------------------------------
// The synthetic sources of the controls
// ---------------------------------------------------------------------------

/** A TypeScript source: comments that hold the signature, decoders, and five copies behind a string, a regex or a template that holds `//`. */
const SYNTHETIC_TS = [
    "/** A doc comment that holds s.replace(/&/g, '&amp;') is no escaper. */",
    "// s.replaceAll('&', '&amp;') commented out",
    "const url = 'https://example.org'; const one = s.replace(/&/g, '&amp;').replace(/</g, '&lt;');",
    'const two = s.replaceAll(\'&\', "&amp;");',
    "const decoded = s.replace(/&amp;/g, '&').replaceAll('&amp;', '&');",
    "const table = {'&': '&amp;', '<': '&lt;'};",
    "function viaSwitch(c: string): string { switch (c) { case '&': return '&amp;'; default: return c; } }",
    "const re = /https?:\\/\\//; const three = s.replace(/&/g, '&amp;');",
    "const t = `https://${host}/a`; /* s.replace(/&/g, '&amp;') */ const four = s.replace(/&/g, `&amp;`);",
].join('\n');

/** A Svelte component: a copy inside an HTML comment, two real ones in two script blocks around markup with an apostrophe, one in a style comment. */
const SYNTHETIC_SVELTE = [
    "<!-- <script> s.replace(/&/g, '&amp;') </script> in a comment -->",
    '<script lang="ts">',
    "    const one = s.replace(/&/g, '&amp;');",
    '</script>',
    '',
    "<p>Don't s.replace(/&/g, '&amp;') in markup: it is text, not code.</p>",
    '<script module lang="ts">',
    "    export const two = (s: string): string => s.replaceAll('&', '&amp;');",
    '</script>',
    '<style>',
    "    /* s.replace(/&/g, '&amp;') */",
    '</style>',
].join('\n');

// =============================================================================
// C-34 — one escaper
// =============================================================================

describe('C-34 — one HTML escaper: no copy of escapeHtml outside the allowlist (static scan)', {timeout: 60_000}, () => {
    it('control — the forms on TypeScript: every copy found on its own line, comments and decoders not, a // in a string, a regex or a template no comment', () => {
        expect(escapersIn('src/synthetic/escapers.ts', SYNTHETIC_TS).map((found) => `${found.line} ${found.form}`)).toEqual(['3 replace call', '4 replace call', '6 table entry', '7 switch case', '8 replace call', '9 replace call']);
    });

    it('control — the forms in a component: only the <script> blocks are read, an HTML comment holding <script> is not one, markup with an apostrophe does not derail the next block', () => {
        expect(escapersIn('src/synthetic/Escapers.svelte', SYNTHETIC_SVELTE).map((found) => `${found.line} ${found.form}`)).toEqual(['3 replace call', '8 replace call']);
    });

    it('control — the scan reads the production tree: hundreds of sources, components among them, tests not', () => {
        const {files} = scanTree();

        expect(files.length, 'the scan read too few production sources: wrong directory, or a filter too strict').toBeGreaterThanOrEqual(500);
        expect(files.filter((file) => file.endsWith('.svelte')).length, 'the scan read too few Svelte components').toBeGreaterThanOrEqual(100);
        const self = relative(FRONTEND, fileURLToPath(import.meta.url))
            .split(sep)
            .join('/');
        expect(files, 'this test file was read as a production source: the test filter does not work').not.toContain(self);
    });

    it('control — every allowlisted entry still holds a copy: the list cannot go stale', () => {
        const {files, escapers} = scanTree();

        const stale = ALLOWED.filter((entry) => !files.filter(entry.matches).some((file) => escapers.some((found) => found.file === file))).map((entry) => `${entry.entry} — ${entry.why}`);

        expect(stale, 'an allowlisted file no longer holds an escaper (or no longer exists): remove its entry').toEqual([]);
    });

    it('control — the decoding direction is no escaper: the toast store decodes &amp; and is not reported', () => {
        const {files, escapers} = scanTree();
        const decoders = files.filter((file) => basename(file) === 'toastStore.svelte.ts');

        expect(decoders, 'the toast store is not among the scanned sources').toHaveLength(1);
        expect(readFileSync(join(FRONTEND, decoders[0]), 'utf8'), 'the toast store no longer decodes &amp;: this control has lost its subject').toContain('&amp;');
        expect(escapers.filter((found) => found.file === decoders[0]).map(describeEscaper)).toEqual([]);
    });

    it('no HTML escaper outside the allowlist: escape with escapeHtml from $lib/utils/core/escapeHtml', () => {
        const offenders = scanTree()
            .escapers.filter((found) => !isAllowed(found.file))
            .map((found) => `${describeEscaper(found)}  (${found.form})`);

        expect(offenders, 'a copy of the HTML escaper outside src/lib/utils/core/escapeHtml.ts: import escapeHtml instead (paths relative to frontend/)').toEqual([]);
    });
});
