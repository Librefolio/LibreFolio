/**
 * @vitest-environment node
 *
 * Warning translator sites — a gate over the source, not a test of behaviour.
 *
 * A backend risk warning reaches the screen through one of three helpers, and each takes the
 * translator as its second argument: `warningSentence(warning, $t)`, `resultReasons(results, $t)`
 * and `partialNotice(results, $t, labels)`. Called without it, each still answers — with the
 * backend's English sentence, verbatim (`warningSentence`) — so a section that forgets `$t` is
 * right in English, green in every English test, and English to an Italian reader. That is what
 * the asset-set laboratory shipped: its correlation, replay and comparison sections called
 * `resultReasons` with one argument while the Dashboard's levels passed `$t`.
 *
 * The rule the gate protects: **every call to one of the three from a component passes a
 * translator.** It enumerates, it does not judge — whether the second argument is the *right*
 * translator is a review question; that there is one, and that it is not a literal `undefined`,
 * is the gate's.
 *
 * **How it reads the source: through the Svelte compiler's own parser.** A call is a
 * `CallExpression` of the AST, in the script or in a template expression, never a line of text.
 * So a comment, a string or the name in prose is not a call, an aliased import
 * (`import {resultReasons as reasonsOf}`) is followed, and a member call
 * (`levels.resultReasons(...)`) is caught. The inline controls below prove each of these on
 * sources written here, through the very function the real files go through.
 *
 * **Scope: every `.svelte` file under `src/`** — a superset of `lib/components/risk`, where the
 * three are called today, so a section mounted anywhere else is covered the day it appears.
 * `.ts` modules are not scanned, on purpose: the translator is a store read in a component's
 * reactive scope (`translateErrorCode` says why a module is handed it rather than reading it), so
 * a module can only forward its caller's — `partialNotice` and `resultReasons` forward theirs —
 * and the call that decides is always a component's.
 *
 * **The forms are a floor.** A fourth helper that words warnings joins `FORMS` in the change that
 * introduces it; otherwise this gate reports green about a question it stopped asking.
 */
import {describe, expect, it} from 'vitest';
import {readdirSync, readFileSync, statSync} from 'node:fs';
import {join, relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {parse} from 'svelte/compiler';

/** The helpers that turn a backend warning into a sentence; each takes the translator second. */
const FORMS = ['warningSentence', 'resultReasons', 'partialNotice'] as const;
type Form = (typeof FORMS)[number];

/** `src/`, found from this file rather than from the working directory the runner happens to use. */
const SRC = fileURLToPath(new URL('../../../', import.meta.url));

interface Call {
    file: string;
    line: number;
    form: Form;
    /** The call's source, whitespace collapsed, cut to a readable length. */
    snippet: string;
    translated: boolean;
}

type Node = Record<string, unknown> & {type: string; start?: number; end?: number};

function isForm(name: unknown): name is Form {
    return typeof name === 'string' && (FORMS as readonly string[]).includes(name);
}

function isNode(value: unknown): value is Node {
    return value !== null && typeof value === 'object' && typeof (value as {type?: unknown}).type === 'string';
}

/** Every AST node under `root`, depth first. The seen-set guards against a shared or cyclic reference. */
function* nodes(root: unknown, seen: WeakSet<object> = new WeakSet()): Generator<Node> {
    if (root === null || typeof root !== 'object' || seen.has(root)) return;
    seen.add(root);
    if (isNode(root)) yield root;
    for (const child of Array.isArray(root) ? root : Object.values(root)) yield* nodes(child, seen);
}

/** Which helper a callee names: directly, through an import alias, or as a member of a namespace. */
function calleeForm(callee: unknown, aliases: ReadonlyMap<string, Form>): Form | null {
    if (!isNode(callee)) return null;
    if (callee.type === 'Identifier') return aliases.get(callee.name as string) ?? null;
    if (callee.type !== 'MemberExpression') return null;
    const property = callee.property;
    if (!isNode(property)) return null;
    const name = callee.computed ? (property.type === 'Literal' ? property.value : null) : property.type === 'Identifier' ? property.name : null;
    return isForm(name) ? name : null;
}

/** A second argument that is there, is not a spread, and is not an explicit nothing. */
function passesTranslator(args: unknown): boolean {
    const second = Array.isArray(args) ? args[1] : undefined;
    if (!isNode(second) || second.type === 'SpreadElement') return false;
    if (second.type === 'Identifier' && second.name === 'undefined') return false;
    if (second.type === 'Literal' && second.value === null) return false;
    return !(second.type === 'UnaryExpression' && second.operator === 'void');
}

function collapse(text: string): string {
    const flat = text.replace(/\s+/g, ' ').trim();
    return flat.length > 110 ? `${flat.slice(0, 109)}…` : flat;
}

/**
 * The calls to the three helpers in one component's source.
 *
 * A function of its own so that an inline control goes through exactly the code a real file goes
 * through: a control that ran on a copy of this logic would test the copy.
 */
function callsIn(file: string, source: string): Call[] {
    const ast = parse(source, {modern: true});
    const aliases = new Map<string, Form>(FORMS.map((form) => [form, form]));
    for (const node of nodes(ast)) {
        if (node.type !== 'ImportSpecifier' || !isNode(node.imported) || !isNode(node.local)) continue;
        const imported = node.imported.type === 'Identifier' ? node.imported.name : node.imported.value;
        if (isForm(imported)) aliases.set(node.local.name as string, imported);
    }
    const found: Array<{start: number; call: Call}> = [];
    for (const node of nodes(ast)) {
        if (node.type !== 'CallExpression') continue;
        const form = calleeForm(node.callee, aliases);
        if (form === null || node.start === undefined || node.end === undefined) continue;
        found.push({start: node.start, call: {file, line: source.slice(0, node.start).split('\n').length, form, snippet: collapse(source.slice(node.start, node.end)), translated: passesTranslator(node.arguments)}});
    }
    // In source order: the AST lists the markup before the script.
    return found.sort((left, right) => left.start - right.start).map(({call}) => call);
}

function svelteFiles(dir: string, acc: string[] = []): string[] {
    for (const entry of readdirSync(dir)) {
        const full = join(dir, entry);
        if (statSync(full).isDirectory()) {
            // Test harnesses are not product: they may call a helper however a test needs.
            if (entry === 'node_modules' || entry === '__tests__' || entry === '__mocks__') continue;
            svelteFiles(full, acc);
        } else if (entry.endsWith('.svelte')) {
            acc.push(full);
        }
    }
    return acc;
}

interface Scan {
    scanned: number;
    calls: Call[];
    /** Files that name a helper but that the parser refused: reported, never skipped. */
    unreadable: string[];
}

function scan(): Scan {
    const files = svelteFiles(SRC);
    const calls: Call[] = [];
    const unreadable: string[] = [];
    for (const full of files) {
        const source = readFileSync(full, 'utf8');
        // A file that names none of the three cannot call one: an alias names the original in
        // its import, a namespace call names it after the dot. Only these few are parsed.
        if (!FORMS.some((form) => source.includes(form))) continue;
        const file = relative(SRC, full).replaceAll('\\', '/');
        try {
            calls.push(...callsIn(file, source));
        } catch (error) {
            unreadable.push(`${file}: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    return {scanned: files.length, calls, unreadable};
}

/** One line per call, stated the way a reader fixes it. */
const untranslatedLine = (call: Call): string => `${call.file}:${call.line} — ${call.snippet}`;

/** A compact view of what a control found: the helper, its line, and whether it passed a translator. */
const shape = (calls: readonly Call[]) => calls.map(({form, line, translated}) => ({form, line, translated}));

describe('warning translator sites — the detector itself', () => {
    it('reports a call without a translator, in the script and in the markup, and not one that passes it', () => {
        const source = [
            '<script lang="ts">',
            "    import {partialNotice} from './levels/partialNotice';",
            "    import {resultReasons, warningSentence} from './levels/levelHelpers';",
            '    let {results, warning} = $props();',
            '    let bare = $derived(resultReasons(results));',
            '    let translated = $derived(resultReasons(results, $t));',
            '    let notice = $derived(partialNotice(results));',
            '    let explicitlyNone = $derived(resultReasons(results, undefined));',
            '</script>',
            '<p>{warningSentence(warning)}</p>',
            '<p>{warningSentence(warning, $t)}</p>',
        ].join('\n');

        expect(shape(callsIn('Inline.svelte', source))).toEqual([
            {form: 'resultReasons', line: 5, translated: false},
            {form: 'resultReasons', line: 6, translated: true},
            {form: 'partialNotice', line: 7, translated: false},
            {form: 'resultReasons', line: 8, translated: false},
            {form: 'warningSentence', line: 10, translated: false},
            {form: 'warningSentence', line: 11, translated: true},
        ]);
    });

    it('follows an aliased import and catches a member call', () => {
        const source = [
            '<script lang="ts">',
            "    import {resultReasons as reasonsOf} from './levels/levelHelpers';",
            "    import * as levels from './levels/levelHelpers';",
            '    let {results} = $props();',
            '    let aliased = $derived(reasonsOf(results));',
            '    let member = $derived(levels.resultReasons(results));',
            '</script>',
        ].join('\n');

        expect(shape(callsIn('Inline.svelte', source))).toEqual([
            {form: 'resultReasons', line: 5, translated: false},
            {form: 'resultReasons', line: 6, translated: false},
        ]);
    });

    it('is not fooled by the name in a comment, a string or the text of the page', () => {
        const source = [
            '<script lang="ts">',
            '    // resultReasons(results) would print the backend sentence',
            '    /* warningSentence(warning) likewise */',
            "    const hint = 'pass $t: never resultReasons(results)';",
            '</script>',
            '<!-- partialNotice(results) is the notice above the levels -->',
            '<p>resultReasons(results) in prose</p>',
        ].join('\n');

        expect(callsIn('Inline.svelte', source)).toEqual([]);
    });
});

describe('warning translator sites — the source tree', () => {
    it('reads the tree and finds the call sites it is known to have', () => {
        const {scanned, calls, unreadable} = scan();
        // Barriers: the walk reached the components, and every file naming a helper was parsed.
        expect(scanned, `the walk from ${SRC} found almost no component: it reads the wrong directory`).toBeGreaterThan(100);
        expect(unreadable, 'a component that names a helper could not be parsed: its calls would go unchecked').toEqual([]);
        // Keyed by file and helper, never by line: an unrelated edit must not move this control.
        expect([...new Set(calls.map((call) => `${call.file} · ${call.form}`))]).toEqual(
            expect.arrayContaining([
                'lib/components/risk/RiskResultFrame.svelte · warningSentence',
                'lib/components/risk/levels/RiskLevelsPanel.svelte · partialNotice',
                'lib/components/risk/levels/RiskLevelsPanel.svelte · resultReasons',
                'lib/components/risk/AssetSetRiskPanel.svelte · partialNotice',
                'lib/components/risk/AssetSetReplaySection.svelte · resultReasons',
            ]),
        );
        // Control: the translated sites are recognised as translated, so the next assertion is not
        // red for every call alike.
        expect(
            calls.filter((call) => call.file === 'lib/components/risk/levels/RiskLevelsPanel.svelte').every((call) => call.translated),
            'the Dashboard levels pass $t: the detector no longer recognises a translator',
        ).toBe(true);
    });

    it('every warning a component words goes through the translator, as on the Dashboard', () => {
        const untranslated = scan().calls.filter((call) => !call.translated);
        expect(untranslated.map(untranslatedLine), "these calls word backend warnings without the reader's language: pass $t as the second argument").toEqual([]);
    });
});
