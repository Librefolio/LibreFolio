/**
 * Gate: every clipboard write goes through `$lib/utils/clipboard.ts` (UI polish C4, M-20).
 *
 * ## What this protects
 *
 * A browser exposes `navigator.clipboard` only in a secure context — HTTPS, or `localhost`. LibreFolio
 * is self-hosted, and a server reached on the LAN by its address over plain HTTP is a normal deployment:
 * there Chromium has no `navigator.clipboard` at all, and a copy button that calls
 * `navigator.clipboard.writeText` directly throws a TypeError and copies nothing. Five copy actions did
 * exactly that, and two more (FilesTable, FileGrid) carried a private copy of the fallback, each with its
 * own idea of when to use it.
 *
 * `writeTextToClipboard` (`$lib/utils/clipboard.ts`) is the one transport: the secure API in a secure
 * context, the legacy readonly textarea + `document.execCommand('copy')` everywhere else and whenever the
 * secure write is refused. Its behaviour is pinned by `clipboard.test.ts`; what this file guards is that
 * the next copy button calls it instead of reaching for the browser API again.
 *
 * ## The rule, as this file checks it
 *
 * Outside `src/lib/utils/clipboard.ts` — the owner, exempt by rule and not by entry — no non-test source
 * under `src` (`.ts`, `.js`, `.svelte`; `*.test.ts`, `*.spec.ts` and their `.js` twins, `__tests__`,
 * `__mocks__` excluded) contains
 *   - an access to `navigator.clipboard`: plain or optional (`navigator.clipboard?.x`,
 *     `navigator?.clipboard`), through `window.` / `globalThis.` / `self.navigator`, computed
 *     (`navigator['clipboard']`), under `as` / `!`, or destructured (`const {clipboard} = navigator`);
 *   - a call to `execCommand` whose first argument is the string `'copy'` — any quote style, any case, on
 *     `document` or bare, optional or computed;
 * unless an entry of `REVIEWED_TRANSPORTS` names the file and the form, with the reason that file keeps
 * a transport of its own.
 *
 * The forms are found on the syntax tree — TypeScript's for `.ts` / `.js`, Svelte's for `.svelte`: its
 * module script, its instance script and every expression of its markup, inline `onclick={…}` handlers
 * included — so a comment or a string that mentions the API is never mistaken for a use of it. Entries
 * are keyed by content (file and form), never by line, so an unrelated edit cannot turn the gate red. An
 * entry that matches nothing is stale and fails the gate, and so does one whose reason is too short to be
 * checked: a list nobody can trust protects nothing.
 *
 * ## Completeness, stated honestly
 *
 * The gate sees the API spelled out. It does not follow a value: `const nav = navigator; nav.clipboard`,
 * `Reflect.get(navigator, 'clipboard')`, a key held in a variable, a command that is not a literal, or
 * `execCommand.call(…)` all pass. Destructuring is seen in a declaration, not in an assignment or a
 * parameter default. `ClipboardEvent.clipboardData.setData` (a copy handler filling its own event) and
 * `execCommand('cut')` are not the transports this rule is about. Every access to `navigator.clipboard`
 * counts, a read included: feature detection belongs to the owner too. And a reviewed entry is not judged:
 * it is a human decision recorded once, and its reason is what a reviewer re-checks when the file behind
 * it changes.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */

import {describe, expect, it} from 'vitest';
import {readdirSync, readFileSync} from 'node:fs';
import {dirname, join, relative, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';
import {parse as parseSvelte} from 'svelte/compiler';

/** `frontend/`: every path is read, and reported, relative to it. */
const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(FRONTEND, 'src');

/** The transport itself: the one file whose job is to touch the browser clipboard API. */
const OWNER = 'src/lib/utils/clipboard.ts';

const CLIPBOARD = 'navigator.clipboard';
const EXEC_COPY = "execCommand('copy')";
type Form = typeof CLIPBOARD | typeof EXEC_COPY;

interface ReviewedTransport {
    file: string;
    form: Form;
    why: string;
}

const AI_EXPORT =
    "AI Export's own writer (defaultAiExportClipboardWriter): it turns every clipboard failure into the typed AiExportClipboardUnavailableError the export UI reports, its tests inject a writer in its place, and where the secure API is missing it falls back to its own readonly textarea + execCommand('copy').";

/** Files that keep a transport of their own, each with the reason. */
const REVIEWED_TRANSPORTS: readonly ReviewedTransport[] = [
    {file: 'src/lib/features/ai-export/aiExportClipboard.ts', form: CLIPBOARD, why: AI_EXPORT},
    {file: 'src/lib/features/ai-export/aiExportClipboard.ts', form: EXEC_COPY, why: AI_EXPORT},
];

interface Hit {
    file: string;
    line: number;
    offset: number;
    form: Form;
}

interface Scan {
    hits: Hit[];
    parseErrors: string[];
}

/** Whether a path (relative to `frontend/`) is app source this gate reads. */
function isScanned(path: string): boolean {
    if (!/\.(svelte|ts|js)$/.test(path) || /\.(test|spec)\.(ts|js)$/.test(path)) return false;
    return !path.split('/').some((segment) => segment === '__tests__' || segment === '__mocks__' || segment === 'node_modules');
}

function sourceFiles(dir: string = SRC, acc: string[] = []): string[] {
    for (const entry of readdirSync(dir, {withFileTypes: true})) {
        const full = join(dir, entry.name);
        if (entry.isDirectory()) {
            sourceFiles(full, acc);
        } else {
            const path = relative(FRONTEND, full).replaceAll('\\', '/');
            if (isScanned(path)) acc.push(path);
        }
    }
    return acc.sort();
}

/** Line starts of a text, for offset → line in O(log n). */
function lineIndex(text: string): (offset: number) => number {
    const starts = [0];
    for (let i = 0; i < text.length; i++) if (text.charCodeAt(i) === 10) starts.push(i + 1);
    return (offset) => {
        let lo = 0;
        let hi = starts.length - 1;
        while (lo < hi) {
            const mid = (lo + hi + 1) >> 1;
            if (starts[mid] <= offset) lo = mid;
            else hi = mid - 1;
        }
        return lo + 1;
    };
}

// --- `.ts` / `.js`: the TypeScript tree ------------------------------------------------------------

/** The expression under parentheses, `!`, `as`, `satisfies` and `<T>`: the value, spelled plainly. */
function tsUnwrap(node: ts.Expression): ts.Expression {
    let inner = node;
    while (ts.isParenthesizedExpression(inner) || ts.isNonNullExpression(inner) || ts.isAsExpression(inner) || ts.isSatisfiesExpression(inner) || ts.isTypeAssertionExpression(inner)) inner = inner.expression;
    return inner;
}

/** A string spelled out in the source: `'x'`, `"x"`, or a backtick literal without `${…}`. */
function tsStaticString(node: ts.Expression | undefined): string | null {
    if (!node) return null;
    const inner = tsUnwrap(node);
    return ts.isStringLiteral(inner) || ts.isNoSubstitutionTemplateLiteral(inner) ? inner.text : null;
}

/** The member an access names: `a.name`, `a?.name`, `a['name']`. */
function tsMemberName(node: ts.Node): string | null {
    if (ts.isPropertyAccessExpression(node)) return node.name.text;
    if (ts.isElementAccessExpression(node)) return tsStaticString(node.argumentExpression);
    return null;
}

/** `navigator` itself, or a member named `navigator`: `window.navigator`, `globalThis.navigator`, `self['navigator']`. */
function tsIsNavigator(node: ts.Expression): boolean {
    const inner = tsUnwrap(node);
    if (ts.isIdentifier(inner)) return inner.text === 'navigator';
    return tsMemberName(inner) === 'navigator';
}

/** The key a destructuring element reads: `{clipboard}`, `{clipboard: c}`, `{'clipboard': c}`, `{['clipboard']: c}`. */
function tsBindingKey(element: ts.BindingElement): string | null {
    if (element.dotDotDotToken) return null;
    const key = element.propertyName ?? element.name;
    if (ts.isIdentifier(key) || ts.isStringLiteral(key)) return key.text;
    if (ts.isComputedPropertyName(key)) return tsStaticString(key.expression);
    return null;
}

/** The transports one node of a TypeScript tree spells. */
function tsForms(node: ts.Node, report: (at: ts.Node, form: Form) => void): void {
    if ((ts.isPropertyAccessExpression(node) || ts.isElementAccessExpression(node)) && tsMemberName(node) === 'clipboard' && tsIsNavigator(node.expression)) report(node, CLIPBOARD);
    if (ts.isCallExpression(node)) {
        const callee = tsUnwrap(node.expression);
        const named = ts.isIdentifier(callee) ? callee.text === 'execCommand' : tsMemberName(callee) === 'execCommand';
        const command = node.arguments.length > 0 ? tsStaticString(node.arguments[0]) : null;
        if (named && command?.toLowerCase() === 'copy') report(node, EXEC_COPY);
    }
    if (ts.isVariableDeclaration(node) && ts.isObjectBindingPattern(node.name) && node.initializer && tsIsNavigator(node.initializer)) {
        for (const element of node.name.elements) if (tsBindingKey(element) === 'clipboard') report(element, CLIPBOARD);
    }
}

/** The transports and parse errors of one `.ts` / `.js` module. */
function scanScript(file: string, text: string): Scan {
    const scan: Scan = {hits: [], parseErrors: []};
    const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, file.endsWith('.js') ? ts.ScriptKind.JS : ts.ScriptKind.TS);
    const lineOf = (offset: number): number => sf.getLineAndCharacterOfPosition(offset).line + 1;
    const diagnostics = (sf as unknown as {parseDiagnostics?: readonly ts.Diagnostic[]}).parseDiagnostics ?? [];
    for (const diagnostic of diagnostics) scan.parseErrors.push(`${file}:${lineOf(diagnostic.start ?? 0)}  ${ts.flattenDiagnosticMessageText(diagnostic.messageText, ' ')}`);
    const report = (at: ts.Node, form: Form): void => {
        const offset = at.getStart(sf);
        scan.hits.push({file, line: lineOf(offset), offset, form});
    };
    const visit = (node: ts.Node): void => {
        tsForms(node, report);
        ts.forEachChild(node, visit);
    };
    visit(sf);
    scan.hits.sort((a, b) => a.offset - b.offset);
    return scan;
}

// --- `.svelte`: Svelte's tree — module script, instance script, markup -----------------------------

/** An ESTree node as Svelte's parser builds it: typed, and placed in the whole file's text. */
type EstreeNode = {type: string; start: number; [key: string]: unknown};

const isEstree = (value: unknown): value is EstreeNode => {
    const node = value as {type?: unknown; start?: unknown} | null;
    return !!node && typeof node === 'object' && typeof node.type === 'string' && typeof node.start === 'number';
};

const ES_WRAPPERS = new Set(['ChainExpression', 'ParenthesizedExpression', 'TSAsExpression', 'TSSatisfiesExpression', 'TSNonNullExpression', 'TSTypeAssertion']);

/** The expression under parentheses, a `?.` chain, `!`, `as`, `satisfies` and `<T>`. */
function esUnwrap(node: unknown): unknown {
    let inner = node;
    while (isEstree(inner) && ES_WRAPPERS.has(inner.type)) inner = inner.expression;
    return inner;
}

/** The name of an `Identifier` node, or null for anything else. */
function esIdentifierName(node: unknown): string | null {
    if (!isEstree(node) || node.type !== 'Identifier') return null;
    const name = node.name;
    return typeof name === 'string' ? name : null;
}

/** A string spelled out in the source: `'x'`, `"x"`, or a backtick literal without `${…}`. */
function esStaticString(node: unknown): string | null {
    const inner = esUnwrap(node);
    if (!isEstree(inner)) return null;
    if (inner.type === 'Literal') {
        const value = inner.value;
        return typeof value === 'string' ? value : null;
    }
    if (inner.type !== 'TemplateLiteral') return null;
    const {expressions, quasis} = inner as unknown as {expressions: unknown[]; quasis: {value: {cooked?: string | null}}[]};
    return expressions.length === 0 && quasis.length === 1 ? (quasis[0].value.cooked ?? null) : null;
}

/** The member a member expression names: `a.name`, `a?.name`, `a['name']`. */
function esMemberName(node: unknown): string | null {
    if (!isEstree(node) || node.type !== 'MemberExpression') return null;
    return node.computed ? esStaticString(node.property) : esIdentifierName(node.property);
}

/** `navigator` itself, or a member named `navigator`: `window.navigator`, `globalThis.navigator`, `self['navigator']`. */
function esIsNavigator(node: unknown): boolean {
    const inner = esUnwrap(node);
    return esIdentifierName(inner) === 'navigator' || esMemberName(inner) === 'navigator';
}

/** The key a destructuring property reads: `{clipboard}`, `{clipboard: c}`, `{'clipboard': c}`, `{['clipboard']: c}`. */
function esPropertyKey(property: unknown): string | null {
    // A RestElement reads no key.
    if (!isEstree(property) || property.type !== 'Property') return null;
    return property.computed ? esStaticString(property.key) : (esIdentifierName(property.key) ?? esStaticString(property.key));
}

/** The transports one node of an ESTree spells — the same forms `tsForms` finds, on Svelte's tree. */
function esForms(node: EstreeNode, report: (at: EstreeNode, form: Form) => void): void {
    if (node.type === 'MemberExpression' && esMemberName(node) === 'clipboard' && esIsNavigator(node.object)) report(node, CLIPBOARD);
    if (node.type === 'CallExpression') {
        const callee = esUnwrap(node.callee);
        const named = (esIdentifierName(callee) ?? esMemberName(callee)) === 'execCommand';
        const args = node.arguments;
        const command = Array.isArray(args) && args.length > 0 ? esStaticString(args[0]) : null;
        if (named && command?.toLowerCase() === 'copy') report(node, EXEC_COPY);
    }
    if (node.type === 'VariableDeclarator') {
        const id = node.id;
        const properties = isEstree(id) && id.type === 'ObjectPattern' ? id.properties : null;
        if (Array.isArray(properties) && esIsNavigator(node.init)) {
            for (const property of properties) if (isEstree(property) && esPropertyKey(property) === 'clipboard') report(property, CLIPBOARD);
        }
    }
}

/**
 * The transports and parse errors of one component, found by Svelte's own parser. Its tree holds the
 * module script, the instance script and the markup — every expression of it, attribute handlers and
 * block tags included — and every node is placed in the whole file's text, so one walk reads all three.
 */
function scanSvelte(file: string, text: string): Scan {
    const scan: Scan = {hits: [], parseErrors: []};
    let ast: unknown;
    try {
        ast = parseSvelte(text, {modern: true});
    } catch (error) {
        scan.parseErrors.push(`${file}  ${(error as Error).message}`);
        return scan;
    }
    const lineAt = lineIndex(text);
    const report = (at: EstreeNode, form: Form): void => {
        scan.hits.push({file, line: lineAt(at.start), offset: at.start, form});
    };
    const seen = new WeakSet<object>();
    const visit = (value: unknown): void => {
        if (!value || typeof value !== 'object' || seen.has(value)) return;
        seen.add(value);
        if (Array.isArray(value)) {
            for (const item of value) visit(item);
            return;
        }
        if (isEstree(value)) esForms(value, report);
        for (const [key, child] of Object.entries(value)) {
            if (key !== 'metadata' && key !== 'parent') visit(child);
        }
    };
    // From the root: module script, instance script, markup — and `<svelte:options>`, whose attributes
    // are expressions too.
    visit(ast);
    scan.hits.sort((a, b) => a.offset - b.offset);
    return scan;
}

/**
 * One scanner per kind of file, and the same one for a real file and a synthetic source: a positive
 * control run on a copy of this logic would test the copy.
 */
const scanSource = (file: string, text: string): Scan => (file.endsWith('.svelte') ? scanSvelte(file, text) : scanScript(file, text));

// --- The verdict's parts ---------------------------------------------------------------------------

/** The owner is exempt by its exact path: a file merely named like it is not the transport. */
const isOwner = (file: string): boolean => file === OWNER;

/** Whether a reviewed entry covers a hit: same file, same form. */
const covers = (entry: ReviewedTransport, hit: Hit): boolean => entry.file === hit.file && entry.form === hit.form;

const flagged = (hits: readonly Hit[], reviewed: readonly ReviewedTransport[]): Hit[] => hits.filter((hit) => !isOwner(hit.file) && !reviewed.some((entry) => covers(entry, hit)));

/** Entries that cover no hit outside the owner — the owner needs no entry, so one naming it is stale too. */
const staleEntries = (hits: readonly Hit[], reviewed: readonly ReviewedTransport[]): ReviewedTransport[] => reviewed.filter((entry) => !hits.some((hit) => !isOwner(hit.file) && covers(entry, hit)));

const unexplainedEntries = (reviewed: readonly ReviewedTransport[]): ReviewedTransport[] => reviewed.filter((entry) => entry.why.trim().length < 40);

/** `line  form` of every transport a synthetic source uses outside the owner and the reviewed entries. */
function caught(file: string, text: string, reviewed: readonly ReviewedTransport[] = []): string[] {
    const scan = scanSource(file, text);
    // A control that does not parse proves nothing: it would be "clean" because it was never read.
    expect(scan.parseErrors).toEqual([]);
    return flagged(scan.hits, reviewed).map((hit) => `${hit.line}  ${hit.form}`);
}

/** Every spelling the rule names, one statement each: each one spells its transport exactly once. */
const FORMS: readonly (readonly [string, Form])[] = [
    ['navigator.clipboard.writeText(text);', CLIPBOARD],
    ['navigator.clipboard?.writeText(text);', CLIPBOARD],
    ['navigator?.clipboard?.writeText(text);', CLIPBOARD],
    ["navigator['clipboard'].writeText(text);", CLIPBOARD],
    ['navigator["clipboard"].writeText(text);', CLIPBOARD],
    ['navigator[`clipboard`].writeText(text);', CLIPBOARD],
    ['window.navigator.clipboard.writeText(text);', CLIPBOARD],
    ['globalThis.navigator.clipboard.writeText(text);', CLIPBOARD],
    ['self.navigator.clipboard.writeText(text);', CLIPBOARD],
    ["window['navigator']?.clipboard.writeText(text);", CLIPBOARD],
    ['(navigator as Navigator).clipboard.writeText(text);', CLIPBOARD],
    ['navigator!.clipboard.writeText(text);', CLIPBOARD],
    ['if (navigator.clipboard && window.isSecureContext) copy();', CLIPBOARD],
    ['const {clipboard} = navigator;', CLIPBOARD],
    ['const {clipboard: board} = window.navigator;', CLIPBOARD],
    ["document.execCommand('copy');", EXEC_COPY],
    ['document.execCommand("copy");', EXEC_COPY],
    ['document.execCommand(`copy`);', EXEC_COPY],
    ["document?.execCommand?.('copy');", EXEC_COPY],
    ["document['execCommand']('copy');", EXEC_COPY],
    ["const ok = document.execCommand('Copy');", EXEC_COPY],
    ["execCommand('copy');", EXEC_COPY],
];

/** What `caught` reports for FORMS laid out one per line from `first`. */
const formsFrom = (first: number): string[] => FORMS.map(([, form], i) => `${first + i}  ${form}`);

describe('Clipboard writes go through $lib/utils/clipboard.ts (C4, M-20 gate)', () => {
    const files = sourceFiles();
    const scans = files.map((file) => scanSource(file, readFileSync(join(FRONTEND, file), 'utf8')));
    const hits = scans.flatMap((scan) => scan.hits);
    const parseErrors = scans.flatMap((scan) => scan.parseErrors);

    it('finds every spelling of the two transports in a module', () => {
        // The positive control of the verdict below: "no direct transport" is also what a scanner that
        // finds nothing would report.
        expect(caught('src/lib/a.ts', FORMS.map(([statement]) => statement).join('\n'))).toEqual(formsFrom(1));
        expect(caught('src/service-worker.js', "navigator.clipboard.writeText(text);\ndocument.execCommand('copy');")).toEqual(['1  navigator.clipboard', "2  execCommand('copy')"]);
    });

    it('finds the same spellings in a component: module script, instance script, markup handler', () => {
        const script = (open: string): string => [open, ...FORMS.map(([statement]) => `    ${statement}`), '</script>'].join('\n');
        expect(caught('src/lib/A.svelte', script('<script lang="ts">'))).toEqual(formsFrom(2));
        expect(caught('src/lib/A.svelte', script('<script module lang="ts">'))).toEqual(formsFrom(2));
        const handlers = ['<script lang="ts"></script>', ...FORMS.map(([statement]) => `<button onclick={() => { ${statement} }}>copy</button>`)].join('\n');
        expect(caught('src/lib/A.svelte', handlers)).toEqual(formsFrom(2));
    });

    it('finds a transport in any expression of the markup', () => {
        // ProviderAssignmentSection's shape: an async inline handler, spread over lines, with a comment.
        const inline = [
            '<script lang="ts"></script>',
            '<button',
            '    type="button"',
            '    onclick={async (e) => {',
            '        e.stopPropagation();',
            '        try {',
            "            await navigator.clipboard.writeText(result.detail ?? '');",
            '        } catch {',
            '            /* navigator.clipboard not available */',
            '        }',
            '    }}',
            '>copy</button>',
        ].join('\n');
        expect(caught('src/lib/A.svelte', inline)).toEqual(['7  navigator.clipboard']);
        const positions = [
            '<script lang="ts"></script>',
            '{#if navigator.clipboard}<p>secure</p>{/if}',
            "{#each items as item (item.id)}{@const ok = document.execCommand('copy')}<p>{ok}</p>{/each}",
            '<svelte:window onkeydown={() => navigator.clipboard.writeText(text)} />',
            '{#snippet copy(text: string)}<button onclick={() => navigator.clipboard.writeText(text)}>copy</button>{/snippet}',
            '{#await navigator.clipboard.readText() then text}<p>{text}</p>{/await}',
        ].join('\n');
        expect(caught('src/lib/A.svelte', positions)).toEqual(['2  navigator.clipboard', "3  execCommand('copy')", '4  navigator.clipboard', '5  navigator.clipboard', '6  navigator.clipboard']);
    });

    it('does not mistake a mention, another command or another clipboard for a transport', () => {
        const module = [
            '// navigator.clipboard.writeText(text) needs a secure context',
            "/* document.execCommand('copy') is the legacy path */",
            "const help = 'navigator.clipboard.writeText(text)';",
            'const legacy = "document.execCommand(\'copy\')";',
            'const doc = `navigator.clipboard`;',
            "document.execCommand('paste');",
            "document.execCommand('insertText', false, text);",
            "const supported = typeof document.execCommand === 'function';",
            'let board: typeof navigator.clipboard | undefined;',
            'editor.clipboard.write(text);',
            "event.clipboardData?.setData('text/plain', text);",
            'const {clipboardData} = event;',
            'const {userAgent} = navigator;',
        ].join('\n');
        expect(caught('src/lib/a.ts', module)).toEqual([]);
        const component = [
            '<script lang="ts">',
            '    // navigator.clipboard.writeText(text)',
            "    /* document.execCommand('copy') */",
            "    const help = 'navigator.clipboard.writeText(text)';",
            '    let board: typeof navigator.clipboard | undefined;',
            "    const supported = typeof document.execCommand === 'function';",
            '</script>',
            "<!-- navigator.clipboard.writeText(x); document.execCommand('copy') -->",
            '<p title="navigator.clipboard.writeText(x)">navigator.clipboard is not used here; document.execCommand(\'copy\') neither</p>',
            "<button onclick={() => document.execCommand('paste')}>{'navigator.clipboard'}</button>",
            '<button onclick={() => editor.clipboard.write(text)}>x</button>',
        ].join('\n');
        expect(caught('src/lib/A.svelte', component)).toEqual([]);
    });

    it('exempts the owner by its exact path, and nothing merely named like it', () => {
        const transport = ['export function copy(text: string) {', '    if (navigator.clipboard?.writeText && window.isSecureContext) return navigator.clipboard.writeText(text);', "    document.execCommand('copy');", '}'].join('\n');
        expect(caught(OWNER, transport)).toEqual([]);
        for (const lookAlike of ['src/lib/utils/myclipboard.ts', 'src/lib/utils/clipboard.ts.bak', 'src/lib/utils/clipboard.svelte.ts', 'src/lib/features/clipboard.ts', 'lib/utils/clipboard.ts']) {
            expect(caught(lookAlike, transport), lookAlike).toEqual(['2  navigator.clipboard', '2  navigator.clipboard', "3  execCommand('copy')"]);
        }
    });

    it('matches a reviewed entry by file and form only, and fails a stale or unexplained one', () => {
        const why = 'a reason long enough to be checked by a reviewer';
        const source = "navigator.clipboard.writeText(text);\ndocument.execCommand('copy');";
        const reviewed: ReviewedTransport[] = [{file: 'src/a.ts', form: CLIPBOARD, why}];
        expect(caught('src/a.ts', source, reviewed)).toEqual(["2  execCommand('copy')"]);
        expect(caught('src/b.ts', source, reviewed)).toEqual(['1  navigator.clipboard', "2  execCommand('copy')"]);

        const synthetic = [...scanSource('src/a.ts', source).hits, ...scanSource(OWNER, source).hits];
        const entries: ReviewedTransport[] = [
            {file: 'src/a.ts', form: CLIPBOARD, why},
            {file: 'src/a.ts', form: EXEC_COPY, why},
            {file: 'src/b.ts', form: CLIPBOARD, why},
            {file: OWNER, form: EXEC_COPY, why},
        ];
        expect(staleEntries(synthetic, entries).map((entry) => `${entry.file}  ${entry.form}`)).toEqual(['src/b.ts  navigator.clipboard', `${OWNER}  execCommand('copy')`]);
        const reasons = ['too short', `   ${'x'.repeat(39)}   `, 'x'.repeat(40)];
        expect(unexplainedEntries(reasons.map((reason) => ({file: 'src/a.ts', form: CLIPBOARD, why: reason}))).map((entry) => entry.why.trim().length)).toEqual([9, 39]);
    });

    it('reports a source it cannot parse, for both kinds of file', () => {
        expect(scanSource('src/a.ts', 'const = ;').parseErrors[0]).toMatch(/^src\/a\.ts:1 {2}\S/);
        expect(scanSource('src/A.svelte', '<script lang="ts">\n    const = ;\n</script>').parseErrors[0]).toMatch(/^src\/A\.svelte {2}\S/);
        expect(scanSource('src/A.svelte', '<div>{#if a}</div>').parseErrors[0]).toMatch(/^src\/A\.svelte {2}\S/);
    });

    it('reads every app source, components and modules alike, and no test file', () => {
        expect(isScanned(OWNER)).toBe(true);
        expect(isScanned('src/lib/features/support/SocialShareModal.svelte')).toBe(true);
        expect(isScanned('src/routes/(app)/dashboard/+page.svelte')).toBe(true);
        expect(isScanned('src/lib/stores/app/toastStore.svelte.ts')).toBe(true);
        expect(isScanned('src/service-worker.js')).toBe(true);
        expect(isScanned('src/lib/utils/clipboard.test.ts')).toBe(false);
        expect(isScanned('src/lib/utils/clipboard.spec.ts')).toBe(false);
        expect(isScanned('src/__tests__/component.ts')).toBe(false);
        expect(isScanned('src/__mocks__/app/environment.ts')).toBe(false);
        expect(isScanned('src/app.css')).toBe(false);
        // 331 components and 328 modules when this gate was written: a walk that reaches the wrong
        // directory, or reads one kind of file only, finds far fewer.
        expect(files.filter((file) => file.endsWith('.svelte')).length).toBeGreaterThan(250);
        expect(files.filter((file) => !file.endsWith('.svelte')).length).toBeGreaterThan(250);
        expect(files).toContain(OWNER);
        expect(files).toContain('src/lib/features/support/SocialShareModal.svelte');
        // The owner spells both transports: a scan that finds nothing there finds nothing anywhere.
        expect(new Set(hits.filter((hit) => hit.file === OWNER).map((hit) => hit.form))).toEqual(new Set([CLIPBOARD, EXEC_COPY]));
    });

    it('parses every source it reads', () => {
        expect(parseErrors, ['', 'These sources could not be parsed, so the gate cannot vouch for them:', '', ...parseErrors, ''].join('\n  ')).toEqual([]);
    });

    it('writes to the clipboard through $lib/utils/clipboard.ts only', () => {
        const offenders = flagged(hits, REVIEWED_TRANSPORTS).map((hit) => `${hit.file}:${hit.line}  ${hit.form}`);
        const rule = `Every clipboard write calls writeTextToClipboard / writeExportToClipboard (${OWNER}), or is an entry of REVIEWED_TRANSPORTS with its reason — C4, M-20.`;

        expect(offenders, ['', rule, `${offenders.length} direct transport(s):`, '', ...offenders, ''].join('\n  ')).toEqual([]);
    });

    it('keeps the reviewed transports current and explained', () => {
        const stale = staleEntries(hits, REVIEWED_TRANSPORTS).map((entry) => `${entry.file}  ${entry.form}`);
        expect(stale, ['', 'Reviewed transports that no longer match any use — delete them:', '', ...stale, ''].join('\n  ')).toEqual([]);
        expect(unexplainedEntries(REVIEWED_TRANSPORTS).map((entry) => `${entry.file}  ${entry.form}`)).toEqual([]);
    });
});
