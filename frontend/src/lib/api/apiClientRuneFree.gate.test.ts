/**
 * Gate: the API client and the AI Export probe load no Svelte-runes module (workstream Z, Z-20, N-Z20-3).
 *
 * ## What this protects
 *
 * The AI Export probe renders a prompt outside the browser, to check it is byte for byte the one the app renders:
 * `scripts/run-ai-export-render-prompt-probe.mjs` starts a bare Vite server — `$lib` aliased, `$app/environment` and
 * `$app/navigation` stubbed — and evaluates `scripts/ai-export-render-prompt-probe.ts` with `ssrLoadModule`. A rune
 * means something only to Svelte's compiler: without `@sveltejs/vite-plugin-svelte` a module-level `$state(…)` throws
 * `rune_outside_svelte` as soon as its module is evaluated, and the probe dies with it. The probe needs the API client
 * (`$lib/api`) for its schemas, so whatever the client imports statically, the probe evaluates too. Z-20 takes the
 * Svelte plugin out of the bridge (N-Z20-4): from then on one rune module statically reachable from either entry breaks
 * the probe.
 *
 * When this gate was written two were, both through `src/lib/api/zodios-client.ts`: `instanceBlock.svelte.ts`, whose
 * `markBlocked()` the error interceptor calls on a 423 (N-Z20-2 moves the state into the plain `instanceBlockState.ts`,
 * and the client imports that instead), and `instanceNotices.svelte.ts`, through the default notice sink of
 * `priceRefresh.ts` (N-Z20-1 loads it with `import()` on the first notice).
 *
 * ## The rule, as this file checks it
 *
 * From each entry — `src/lib/api/index.ts` and `scripts/ai-export-render-prompt-probe.ts` — follow every static runtime
 * import: `import … from '…'`, `import '…'`, `export … from '…'`. No module reached may be one Svelte compiles: a
 * `.svelte` component, or a module whose name carries `.svelte.` and ends in `.ts` or `.js` (vite-plugin-svelte's own
 * filters). A failure lists each one as the chain of static imports that reaches it from the entry. A case of its own
 * (H's guard) checks that `src/lib/api/zodios-client.ts` imports none directly.
 *
 * - Erased, so not followed: `import type …`, `export type … from '…'`, and a type written `import('…')`. Not erased:
 *   an import whose specifiers are all `type` (`import {type X} from '…'`) — `.svelte-kit/tsconfig.json` sets
 *   `verbatimModuleSyntax`, which keeps it as `import {} from '…'`, and that evaluates the module; `export {type X}
 *   from '…'` likewise.
 * - Not followed, by design: a dynamic `import()`, which loads its module only when it runs — N-Z20-1's lazy load is
 *   one; packages and `node:` builtins, outside the question; `$app/*`, which the bridge stubs.
 * - Resolved as Vite resolves it there: `$lib/` is `src/lib/`, `./` and `../` are relative to the importer, `/` is
 *   `frontend/`; the path itself when it is a file, then a `.js` read as the `.ts` it is compiled from, then Vite's
 *   default extensions (`.mjs`, `.js`, `.mts`, `.ts`, `.jsx`, `.tsx`, `.json`), then the same after `/index` — so
 *   `….svelte` reaches `….svelte.ts`. A local specifier that resolves to nothing is a blind spot: it fails the gate
 *   instead of being skipped.
 *
 * Imports are read on TypeScript's syntax tree, top-level declarations only (an `import` inside `declare module` is
 * ambient), so a comment or a string that names a module is never taken for an import of it.
 *
 * ## Completeness, stated honestly
 *
 * The forms are a floor. `require()`, `import.meta.glob`, `new URL(…, import.meta.url)` and a specifier held in a
 * variable are not followed. A dynamic `import()` is not followed on purpose, and that is also a hole: a top-level
 * `await import('….svelte')` evaluates its module at once, and the gate lets it pass. A `.svelte` component is reported
 * where it is reached and not read further: what it imports sits behind a violation already. The question is asked by
 * file name, not by content — a plain `.ts` cannot hold a rune Svelte would compile, and a `.svelte.ts` that holds none
 * is reported anyway (renaming it is cheap). Only the bridge's alias (`$lib`) is resolved: an import through another
 * one fails the bridge before any rune could. The controls below run synthetic graphs, written to a temporary
 * directory, through the same scanner; and the scanner started at `src/lib/features/email/verificationApi.ts` — which
 * imports `instanceBlock.svelte` itself, and keeps doing so — must report it: a scanner that sees nothing fails here
 * instead of passing.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */

import {afterAll, beforeAll, describe, expect, it} from 'vitest';
import {existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {dirname, join, posix, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';

/** `frontend/`: the real graphs are read, and reported, relative to it. */
const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');

const API_ENTRY = 'src/lib/api/index.ts';
const PROBE_ENTRY = 'scripts/ai-export-render-prompt-probe.ts';
const ENTRIES = [API_ENTRY, PROBE_ENTRY];
const CLIENT = 'src/lib/api/zodios-client.ts';
/** The real-site control: it imports the block's reactive face itself, for `isInstanceBlockedError`, and keeps doing so after Z-20. */
const CONTROL_SITE = 'src/lib/features/email/verificationApi.ts';
const CONTROL_RUNE = 'src/lib/features/instance/instanceBlock.svelte.ts';

/** What Svelte compiles, so what may hold a rune: a component, or a module with the infix `.svelte.` ending in `.ts` or `.js` (vite-plugin-svelte's filters). */
const SVELTE_COMPILED = /\.svelte$|\.svelte\.(?:[^./]+\.)*[jt]s$/;
/** Read and followed; anything else reached — a component, JSON — is not read. */
const SCRIPT = /\.[cm]?[jt]s$/;
/** Vite's default `resolve.extensions`: the bridge sets none. */
const EXTENSIONS = ['.mjs', '.js', '.mts', '.ts', '.jsx', '.tsx', '.json'];

type Kind = 'static' | 'export' | 'type' | 'dynamic';

interface Reference {
    line: number;
    /** As written, a query (`?raw`) included. */
    specifier: string;
    kind: Kind;
}

interface Scan {
    refs: Reference[];
    errors: string[];
}

/** The module references of one source: its top-level `import` and `export … from` declarations, every `import()`, and every type written `import('…')`. */
function scanModule(file: string, text: string): Scan {
    const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, false, /\.[cm]?js$/.test(file) ? ts.ScriptKind.JS : ts.ScriptKind.TS);
    const refs: Reference[] = [];
    const add = (node: ts.Node, specifier: string, kind: Kind) => refs.push({line: sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1, specifier, kind});
    for (const statement of sf.statements) {
        if (ts.isImportDeclaration(statement) && ts.isStringLiteral(statement.moduleSpecifier)) {
            // `import type …` is erased; `import {type X} …` is not: verbatimModuleSyntax keeps it as `import {} from …`.
            add(statement, statement.moduleSpecifier.text, statement.importClause?.phaseModifier === ts.SyntaxKind.TypeKeyword ? 'type' : 'static');
        } else if (ts.isExportDeclaration(statement) && statement.moduleSpecifier && ts.isStringLiteral(statement.moduleSpecifier)) {
            add(statement, statement.moduleSpecifier.text, statement.isTypeOnly ? 'type' : 'export');
        }
    }
    const visit = (node: ts.Node): void => {
        if (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword) {
            const argument = node.arguments[0];
            if (argument !== undefined && (ts.isStringLiteral(argument) || ts.isNoSubstitutionTemplateLiteral(argument))) add(node, argument.text, 'dynamic');
        } else if (ts.isImportTypeNode(node) && ts.isLiteralTypeNode(node.argument) && ts.isStringLiteral(node.argument.literal)) {
            add(node, node.argument.literal.text, 'type');
        }
        ts.forEachChild(node, visit);
    };
    visit(sf);
    refs.sort((a, b) => a.line - b.line);
    const diagnostics = (sf as unknown as {parseDiagnostics?: readonly ts.Diagnostic[]}).parseDiagnostics ?? [];
    return {refs, errors: diagnostics.map((d) => `${file}: ${ts.flattenDiagnosticMessageText(d.messageText, ' ')}`)};
}

const scans = new Map<string, Scan>();

/** The scan of a file, root-relative, read once per run. */
function scanFile(root: string, file: string): Scan {
    const path = join(root, file);
    let scan = scans.get(path);
    if (scan === undefined) {
        scan = scanModule(file, readFileSync(path, 'utf8'));
        scans.set(path, scan);
    }
    return scan;
}

const isFile = (path: string): boolean => existsSync(path) && statSync(path).isFile();

/**
 * Where a specifier leads, root-relative: `null` when it is not followed (a package, a `node:` builtin, `$app/*`, a
 * virtual module), `undefined` when it is local and names no file — a blind spot.
 */
function resolveSpecifier(root: string, from: string, specifier: string): string | null | undefined {
    const bare = specifier.split('?')[0];
    let target: string;
    if (bare === '$lib' || bare.startsWith('$lib/')) target = posix.join('src/lib', bare.slice('$lib'.length));
    else if (bare.startsWith('.')) target = posix.join(posix.dirname(from), bare);
    else if (bare.startsWith('/')) target = posix.normalize(bare.slice(1));
    else return null;
    const candidates = [target];
    // A TypeScript import may name the `.js` its `.ts` compiles to.
    const compiled = /\.([cm]?)js$/.exec(target);
    if (compiled) candidates.push(`${target.slice(0, -compiled[0].length)}.${compiled[1]}ts`);
    candidates.push(...EXTENSIONS.map((extension) => `${target}${extension}`), ...EXTENSIONS.map((extension) => `${target}/index${extension}`));
    return candidates.find((candidate) => isFile(join(root, candidate)));
}

interface Graph {
    /** Every module reached, breadth first, with the chain of static imports that first reached it, the entry first. */
    chains: Map<string, string[]>;
    /** Local specifiers that name no file, as `file:line 'specifier'`: parts of the graph the gate would not see. */
    unresolved: string[];
    /** Parse errors of the sources read. */
    errors: string[];
}

/** The static runtime closure of `entry` under `root`: what `ssrLoadModule(entry)` evaluates before any `import()` runs. */
function staticGraph(root: string, entry: string): Graph {
    const chains = new Map<string, string[]>([[entry, [entry]]]);
    const unresolved: string[] = [];
    const errors: string[] = [];
    const queue = [entry];
    for (let index = 0; index < queue.length; index++) {
        const from = queue[index];
        if (!SCRIPT.test(from)) continue;
        const scan = scanFile(root, from);
        errors.push(...scan.errors);
        for (const ref of scan.refs) {
            if (ref.kind !== 'static' && ref.kind !== 'export') continue;
            const target = resolveSpecifier(root, from, ref.specifier);
            if (target === null) continue;
            if (target === undefined) {
                unresolved.push(`${from}:${ref.line} '${ref.specifier}'`);
                continue;
            }
            if (chains.has(target)) continue;
            chains.set(target, [...(chains.get(from) ?? [from]), target]);
            queue.push(target);
        }
    }
    return {chains, unresolved, errors};
}

/** The modules Svelte compiles among those reached, each as the chain of static imports that reaches it. */
const svelteChains = (graph: Graph): string[] => [...graph.chains].filter(([file]) => SVELTE_COMPILED.test(file)).map(([, chain]) => chain.join(' → '));

/** The modules `file` imports statically, resolved. */
const directImports = (root: string, file: string): string[] =>
    scanFile(root, file)
        .refs.filter((ref) => ref.kind === 'static' || ref.kind === 'export')
        .map((ref) => resolveSpecifier(root, file, ref.specifier))
        .filter((target): target is string => typeof target === 'string');

/** The static imports of `file` that Svelte compiles, as `file:line 'specifier' → module`. */
function directSvelteImports(root: string, file: string): string[] {
    const found: string[] = [];
    for (const ref of scanFile(root, file).refs) {
        if (ref.kind !== 'static' && ref.kind !== 'export') continue;
        const target = resolveSpecifier(root, file, ref.specifier);
        if (typeof target === 'string' && SVELTE_COMPILED.test(target)) found.push(`${file}:${ref.line} '${ref.specifier}' → ${target}`);
    }
    return found;
}

const RULE = `The AI Export probe evaluates this graph with Vite's ssrLoadModule and no Svelte compiler (scripts/run-ai-export-render-prompt-probe.mjs): there a module-level rune throws rune_outside_svelte. Neither ${API_ENTRY} nor ${PROBE_ENTRY} may reach a .svelte component or a .svelte.ts/.svelte.js module through static imports. Move what the graph needs into a plain module (instanceBlockState.ts holds the instance block), or load the rune module with import() where it is used (priceRefresh loads instanceNotices.svelte on its first notice). Each line is one such module, as the chain of static imports that reaches it:`;

const CLIENT_RULE = `${CLIENT} must import no .svelte or .svelte.ts module directly (H's guard): it marks a blocked instance through the plain instanceBlockState.ts, and instanceBlock.svelte.ts stays the reactive face the (app) layout reads. Found:`;

describe('rune-free imports — the API client and the AI Export probe (Z-20)', () => {
    it.each(ENTRIES)('%s reaches no module Svelte compiles through static imports', (entry) => {
        expect(svelteChains(staticGraph(FRONTEND, entry)), `${RULE}\n`).toEqual([]);
    });

    it.each(ENTRIES)('%s: every local import names a file and every source parses — no blind spot', (entry) => {
        const graph = staticGraph(FRONTEND, entry);
        expect(graph.unresolved, 'These local imports name no file the gate can find, so it cannot see past them (src/lib/api/generated.ts is generated: `./dev.py api sync`). Fix the import, or the resolution of this gate:\n').toEqual([]);
        expect(graph.errors).toEqual([]);
    });

    it('zodios-client.ts imports no module Svelte compiles directly (H’s guard)', () => {
        expect(directImports(FRONTEND, CLIENT), 'premise: the scan of the client finds its imports').toContain('src/lib/features/price-refresh/priceRefresh.ts');
        expect(directSvelteImports(FRONTEND, CLIENT), `${CLIENT_RULE}\n`).toEqual([]);
    });

    it('still walks what the bridge loads: the client and the modules of its interceptors, the probe and its renderer', () => {
        expect([...staticGraph(FRONTEND, API_ENTRY).chains.keys()]).toEqual(expect.arrayContaining([CLIENT, 'src/lib/api/generated.ts', 'src/lib/features/price-refresh/priceRefresh.ts', 'src/lib/features/live-updates/activityTracker.ts']));
        // `markdown.ts` is reached only through `export * from './markdown'` in serialization/index.ts.
        expect([...staticGraph(FRONTEND, PROBE_ENTRY).chains.keys()]).toEqual(expect.arrayContaining([API_ENTRY, CLIENT, 'src/lib/features/ai-export/serialization/index.ts', 'src/lib/features/ai-export/serialization/markdown.ts', 'src/lib/features/ai-export/templates/promptRenderer.ts']));
    });

    it('reports the rune module a real site imports: verificationApi.ts → instanceBlock.svelte.ts', () => {
        expect(
            svelteChains(staticGraph(FRONTEND, CONTROL_SITE)),
            `${CONTROL_SITE} imports ${CONTROL_RUNE} (isInstanceBlockedError, re-exported by the face): the scanner must report it. If that import has moved to instanceBlockState.ts, choose another real site that imports a .svelte.ts module`,
        ).toContain(`${CONTROL_SITE} → ${CONTROL_RUNE}`);
    });
});

/** Synthetic graphs, root-relative: written to a temporary directory, and scanned exactly as the real ones. */
const SYNTHETIC: Record<string, string> = {
    'src/lib/runes/counter.svelte.ts': 'let count = $state(0);\n\nexport type Counter = {readonly value: number};\nexport const counter: Counter = {\n    get value() {\n        return count;\n    },\n};\n',
    'src/lib/runes/Badge.svelte': '<script lang="ts">\n    let shown = $state(true);\n</script>\n\n{#if shown}<span>!</span>{/if}\n',
    'src/lib/plain/hop2.ts': "export {counter} from '../runes/counter.svelte';\n",
    'src/lib/plain/hop1.ts': "import {counter} from './hop2';\n\nexport const read = (): number => counter.value;\n",
    'src/lib/plain/state.ts': 'export const state = {blocked: false};\n',
    'src/entries/direct.ts': "import {counter} from '$lib/runes/counter.svelte';\n\nexport const read = (): number => counter.value;\n",
    'src/entries/twoHops.ts': "import {read} from '$lib/plain/hop1';\n\nexport {read};\n",
    'src/entries/typeSpecifiers.ts': "import {type Counter} from '$lib/runes/counter.svelte';\n\nexport const none: Counter | null = null;\n",
    'src/entries/sideEffect.ts': "import '../lib/runes/counter.svelte.js';\n",
    'src/entries/component.ts': "import Badge from '$lib/runes/Badge.svelte';\n\nexport {Badge};\n",
    'src/entries/typeOnly.ts': "import type {Counter} from '$lib/runes/counter.svelte';\nexport type {Counter as Again} from '../lib/runes/counter.svelte';\nexport type Lazy = typeof import('$lib/runes/counter.svelte');\n\nexport const none: Counter | null = null;\n",
    'src/entries/dynamic.ts': "export const load = async (): Promise<number> => (await import('$lib/runes/counter.svelte')).counter.value;\n",
    'src/entries/packages.ts': "import {writable} from 'svelte/store';\nimport {nothing} from 'lf-no-such-package';\nimport {goto} from '$app/navigation';\nimport {state} from '$lib/plain/state';\n\nexport const all = [writable, nothing, goto, state];\n",
    'src/entries/missing.ts': "import {gone} from './gone';\n\nexport {gone};\n",
};

describe('rune-free imports — the scanner, on synthetic graphs', () => {
    let root = '';

    beforeAll(() => {
        root = mkdtempSync(join(tmpdir(), 'lf-rune-free-gate-'));
        for (const [file, text] of Object.entries(SYNTHETIC)) {
            mkdirSync(dirname(join(root, file)), {recursive: true});
            writeFileSync(join(root, file), text);
        }
    });

    afterAll(() => {
        if (root) rmSync(root, {recursive: true, force: true});
    });

    it.each<[string, string, string[]]>([
        ['a static import of a .svelte.ts module', 'src/entries/direct.ts', ['src/entries/direct.ts → src/lib/runes/counter.svelte.ts']],
        ['the same module two hops away, through an import and an export … from', 'src/entries/twoHops.ts', ['src/entries/twoHops.ts → src/lib/plain/hop1.ts → src/lib/plain/hop2.ts → src/lib/runes/counter.svelte.ts']],
        ['an import whose specifiers are all type, which verbatimModuleSyntax keeps as import {} from', 'src/entries/typeSpecifiers.ts', ['src/entries/typeSpecifiers.ts → src/lib/runes/counter.svelte.ts']],
        ['a side-effect import naming the .js of a .svelte.ts', 'src/entries/sideEffect.ts', ['src/entries/sideEffect.ts → src/lib/runes/counter.svelte.ts']],
        ['a .svelte component, reached as such', 'src/entries/component.ts', ['src/entries/component.ts → src/lib/runes/Badge.svelte']],
    ])('reports %s', (_label, entry, expected) => {
        expect(svelteChains(staticGraph(root, entry))).toEqual(expected);
    });

    it('does not follow import type, export type … from, or a type written import(): it sees them, and they are erased', () => {
        const entry = 'src/entries/typeOnly.ts';
        expect(scanFile(root, entry).refs.map((ref) => ref.kind)).toEqual(['type', 'type', 'type']);
        expect(svelteChains(staticGraph(root, entry))).toEqual([]);
    });

    it('does not follow a dynamic import(): it sees it, and leaves it lazy', () => {
        const entry = 'src/entries/dynamic.ts';
        expect(scanFile(root, entry).refs).toEqual([{line: 1, specifier: '$lib/runes/counter.svelte', kind: 'dynamic'}]);
        expect(svelteChains(staticGraph(root, entry))).toEqual([]);
    });

    it('does not follow a package — an unresolvable one included — or $app/*, and none of them is a blind spot', () => {
        const graph = staticGraph(root, 'src/entries/packages.ts');
        expect([...graph.chains.keys()], 'only the local import is followed').toEqual(['src/entries/packages.ts', 'src/lib/plain/state.ts']);
        expect(graph.unresolved).toEqual([]);
    });

    it('reports a local import that names no file as a blind spot, instead of skipping it', () => {
        const graph = staticGraph(root, 'src/entries/missing.ts');
        expect(graph.unresolved).toEqual(["src/entries/missing.ts:1 './gone'"]);
        expect(svelteChains(graph)).toEqual([]);
    });
});
