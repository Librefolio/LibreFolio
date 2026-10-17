/**
 * Gate: the Designer Lab stays out of the app's bundles (workstream L).
 *
 * ## What this protects
 *
 * The Lab is debug-only tooling. A release build must carry none of it: the route answers 404 from a stub, and every
 * other path to the Lab sits behind `if (__LF_DESIGNER_LAB__)`, a Vite `define` that is `false` in release, so
 * Rollup drops the branch and the chunk behind it. The Vite plugin backs this up at build time (a release output
 * carrying the marker `lf-designer-lab` fails the build); this gate says *where* the rule broke, before any build.
 *
 * ## The rule, as this file checks it
 *
 * (a) Outside `src/lib/dev/designer-lab/` and `src/routes/designer-lab/`, the only reference to the Lab is the dynamic
 *     import of `$lib/dev/designer-lab/client` in `src/routes/+layout.svelte`, inside `if (__LF_DESIGNER_LAB__)`.
 *     Type-only references are erased and allowed (`import type`, `import('…').T`, anything in a `.d.ts`); an import
 *     whose specifiers are all `type` is not, because `verbatimModuleSyntax` keeps it as `import {} from '…'`.
 * (b) `virtual:lf-color-catalog` (the whole catalogue) is imported by the Lab page component only, and
 *     `virtual:lf-testid-index` by the picker's `picker/describe.ts` only.
 * (c) `client.ts`, which every page of a debug build loads, reaches `engine/` and `picker/` only through `import()`:
 *     nothing it imports statically, directly or transitively, lives there.
 * (d) The route files of `src/routes/designer-lab/` are compiled into every build: they reach the Lab only through a
 *     guarded `import()` too.
 *
 * A reference is found on the syntax tree — TypeScript's for `.ts`/`.js`, Svelte's for `.svelte` (both scripts and
 * the markup) — in every form that brings a module into a bundle: `import`, `export … from`, `import()` (a template
 * with `${…}` read as the glob Vite makes of it) and `import.meta.glob`. A specifier is followed through `$lib/`,
 * relative paths and `/` (the project root); a glob counts when its static part is inside the Lab, or above it with a
 * pattern that can descend into it.
 *
 * ## Completeness, stated honestly
 *
 * The forms are a floor: `require()`, `new URL(…, import.meta.url)` and a specifier held in a variable are not seen
 * (Vite cannot bundle the last one either). Only files that name `designer-lab`, `virtual:lf-`, `import.meta.glob` or
 * a template `import()` are parsed for (a), (b) and (d): any reference the gate can see names one of them. The
 * controls below run synthetic violations through the same scanner, and the real sites the rule allows must still be
 * found, so a scanner that sees nothing fails here instead of passing.
 */

import {describe, expect, it} from 'vitest';
import {existsSync, readdirSync, readFileSync, statSync} from 'node:fs';
import {dirname, join, posix, relative, resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';
import {parse as parseSvelte} from 'svelte/compiler';

/** `frontend/`: every path is read, and reported, relative to it. */
const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '../../../..');
const SRC = join(FRONTEND, 'src');

const LAB_LIB = 'src/lib/dev/designer-lab/';
const LAB_ROUTE = 'src/routes/designer-lab/';
const LAB_DIRS = [LAB_LIB, LAB_ROUTE];
const GUARD = '__LF_DESIGNER_LAB__';
const CATALOG_ID = 'virtual:lf-color-catalog';
const INDEX_ID = 'virtual:lf-testid-index';
const CLIENT = `${LAB_LIB}client.ts`;
const ENGINE = `${LAB_LIB}engine/`;
const PICKER = `${LAB_LIB}picker/`;

/** The one way into the Lab from the app. */
const LAYOUT_SITE = {file: 'src/routes/+layout.svelte', specifier: '$lib/dev/designer-lab/client'};

/** Who may import each virtual module, and why. */
const VIRTUAL_IMPORTERS: Record<string, {files: string[]; why: string}> = {
    [CATALOG_ID]: {files: [`${LAB_LIB}DesignerLab.svelte`], why: 'the whole colour catalogue: only the Lab page loads it, and passes it down as a prop'},
    [INDEX_ID]: {files: [`${PICKER}describe.ts`], why: 'the test-id index the picker needs in the app tab: it must arrive with the picker chunk, never with the client'},
};

/** A file can only refer to the Lab if it names one of these (see «Completeness»). */
const MAY_REFER = /designer-lab|virtual:lf-|import\.meta\.glob|import\s*\(\s*`/;

type Kind = 'static' | 'export' | 'dynamic' | 'glob' | 'type';

interface Reference {
    file: string;
    line: number;
    /** As written; a template's `${…}` as `*`. */
    specifier: string;
    kind: Kind;
    /** Inside the consequent of `if (__LF_DESIGNER_LAB__)`. */
    guarded: boolean;
}

interface Scan {
    refs: Reference[];
    errors: string[];
}

const RUNTIME: ReadonlySet<Kind> = new Set(['static', 'export', 'dynamic', 'glob']);

/** Non-test sources under `src`, `frontend/`-relative. */
function sourceFiles(dir: string = SRC, acc: string[] = []): string[] {
    for (const entry of readdirSync(dir, {withFileTypes: true})) {
        const full = join(dir, entry.name);
        const path = relative(FRONTEND, full).split(sep).join('/');
        if (entry.isDirectory()) {
            if (!['node_modules', '__tests__', '__mocks__'].includes(entry.name)) sourceFiles(full, acc);
        } else if (/\.(svelte|ts|js)$/.test(path) && !/\.(test|spec)\.(ts|js)$/.test(path)) acc.push(path);
    }
    return acc.sort();
}

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

// --- `.ts` / `.js` / `.d.ts`: the TypeScript tree --------------------------------------------------------------

function tsPattern(node: ts.Expression | undefined): string | null {
    if (!node) return null;
    if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) return node.text;
    if (ts.isTemplateExpression(node)) return node.head.text + node.templateSpans.map((span) => `*${span.literal.text}`).join('');
    return null;
}

function tsPatterns(node: ts.Expression | undefined): string[] {
    if (node && ts.isArrayLiteralExpression(node)) return node.elements.map((e) => tsPattern(e)).filter((p): p is string => p !== null);
    const one = tsPattern(node);
    return one === null ? [] : [one];
}

const tsIsImportMetaGlob = (callee: ts.Expression): boolean => ts.isPropertyAccessExpression(callee) && ['glob', 'globEager'].includes(callee.name.text) && ts.isMetaProperty(callee.expression) && callee.expression.keywordToken === ts.SyntaxKind.ImportKeyword;

function tsIsGuard(expression: ts.Expression): boolean {
    let e = expression;
    while (ts.isParenthesizedExpression(e)) e = e.expression;
    return ts.isIdentifier(e) && e.text === GUARD;
}

/** Whether the node sits in the `then` branch of `if (__LF_DESIGNER_LAB__)`. */
function tsGuarded(node: ts.Node): boolean {
    for (let child: ts.Node = node, parent = node.parent; parent; child = parent, parent = parent.parent) {
        if (ts.isIfStatement(parent) && parent.thenStatement === child && tsIsGuard(parent.expression)) return true;
    }
    return false;
}

function scanScript(file: string, text: string): Scan {
    const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, file.endsWith('.js') ? ts.ScriptKind.JS : ts.ScriptKind.TS);
    const declarations = file.endsWith('.d.ts');
    const refs: Reference[] = [];
    const add = (node: ts.Node, specifier: string, kind: Kind) => refs.push({file, line: sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1, specifier, kind: declarations ? 'type' : kind, guarded: tsGuarded(node)});
    const visit = (node: ts.Node): void => {
        if (ts.isImportDeclaration(node) && ts.isStringLiteral(node.moduleSpecifier)) add(node, node.moduleSpecifier.text, node.importClause?.isTypeOnly ? 'type' : 'static');
        else if (ts.isExportDeclaration(node) && node.moduleSpecifier && ts.isStringLiteral(node.moduleSpecifier)) add(node, node.moduleSpecifier.text, node.isTypeOnly ? 'type' : 'export');
        else if (ts.isImportTypeNode(node) && ts.isLiteralTypeNode(node.argument) && ts.isStringLiteral(node.argument.literal)) add(node, node.argument.literal.text, 'type');
        else if (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword) {
            const specifier = tsPattern(node.arguments[0]);
            if (specifier !== null) add(node, specifier, 'dynamic');
        } else if (ts.isCallExpression(node) && tsIsImportMetaGlob(node.expression)) for (const pattern of tsPatterns(node.arguments[0])) add(node, pattern, 'glob');
        ts.forEachChild(node, visit);
    };
    visit(sf);
    const diagnostics = (sf as unknown as {parseDiagnostics?: readonly ts.Diagnostic[]}).parseDiagnostics ?? [];
    return {refs, errors: diagnostics.map((d) => `${file}: ${ts.flattenDiagnosticMessageText(d.messageText, ' ')}`)};
}

// --- `.svelte`: Svelte's tree — module script, instance script, markup -------------------------------------------

type EsNode = {type: string; start: number; [key: string]: unknown};

const isEs = (value: unknown): value is EsNode => {
    const node = value as {type?: unknown; start?: unknown} | null;
    return !!node && typeof node === 'object' && typeof node.type === 'string' && typeof node.start === 'number';
};

function esPattern(node: unknown): string | null {
    if (!isEs(node)) return null;
    if (node.type === 'Literal') {
        const value = node.value;
        return typeof value === 'string' ? value : null;
    }
    if (node.type !== 'TemplateLiteral') return null;
    return (node.quasis as {value: {cooked?: string | null; raw: string}}[]).map((q) => q.value.cooked ?? q.value.raw).join('*');
}

function esPatterns(node: unknown): string[] {
    if (isEs(node) && node.type === 'ArrayExpression') return (node.elements as unknown[]).map(esPattern).filter((p): p is string => p !== null);
    const one = esPattern(node);
    return one === null ? [] : [one];
}

function esIsImportMetaGlob(callee: unknown): boolean {
    if (!isEs(callee) || callee.type !== 'MemberExpression') return false;
    const object = callee.object;
    const property = callee.property;
    return isEs(object) && object.type === 'MetaProperty' && isEs(property) && ['glob', 'globEager'].includes(String(property.name));
}

/** Whether the node sits in the consequent of `if (__LF_DESIGNER_LAB__)`; `ancestors` are its own, outermost first. */
function esGuarded(ancestors: EsNode[], node: EsNode): boolean {
    for (let i = ancestors.length - 1; i >= 0; i--) {
        const parent = ancestors[i];
        const child = ancestors[i + 1] ?? node;
        const test = parent.test;
        if (parent.type === 'IfStatement' && parent.consequent === child && isEs(test) && test.type === 'Identifier' && test.name === GUARD) return true;
    }
    return false;
}

function scanComponent(file: string, text: string): Scan {
    let ast: unknown;
    try {
        ast = parseSvelte(text, {modern: true});
    } catch (error) {
        return {refs: [], errors: [`${file}: ${(error as Error).message}`]};
    }
    const lineAt = lineIndex(text);
    const refs: Reference[] = [];
    const ancestors: EsNode[] = [];
    const seen = new WeakSet<object>();
    const add = (node: EsNode, specifier: string, kind: Kind) => refs.push({file, line: lineAt(node.start), specifier, kind, guarded: esGuarded(ancestors, node)});
    const visit = (value: unknown): void => {
        if (!value || typeof value !== 'object' || seen.has(value)) return;
        seen.add(value);
        if (Array.isArray(value)) {
            for (const item of value) visit(item);
            return;
        }
        const node = isEs(value) ? value : null;
        if (node) {
            const one = (kind: Kind) => {
                const specifier = esPattern(node.source);
                if (specifier !== null) add(node, specifier, kind);
            };
            if (node.type === 'ImportDeclaration') one(node.importKind === 'type' ? 'type' : 'static');
            else if ((node.type === 'ExportNamedDeclaration' || node.type === 'ExportAllDeclaration') && node.source) one(node.exportKind === 'type' ? 'type' : 'export');
            else if (node.type === 'ImportExpression') one('dynamic');
            else if (node.type === 'CallExpression' && esIsImportMetaGlob(node.callee)) for (const pattern of esPatterns((node.arguments as unknown[])[0])) add(node, pattern, 'glob');
            ancestors.push(node);
        }
        for (const [key, child] of Object.entries(value)) if (key !== 'metadata' && key !== 'parent') visit(child);
        if (node) ancestors.pop();
    };
    visit(ast);
    return {refs, errors: []};
}

/** One scanner for a real file and a synthetic source alike: a control run on a copy of this logic would test the copy. */
const scanSource = (file: string, text: string): Scan => (file.endsWith('.svelte') ? scanComponent(file, text) : scanScript(file, text));

// --- Where a specifier leads ---------------------------------------------------------------------------------

/** The `frontend/`-relative path a specifier names, or null for a package or a virtual module. */
function targetOf(file: string, specifier: string): string | null {
    if (specifier === '$lib' || specifier.startsWith('$lib/')) return posix.join('src/lib', specifier.slice('$lib'.length));
    if (specifier.startsWith('.')) return posix.join(posix.dirname(file), specifier);
    if (specifier.startsWith('/')) return posix.normalize(specifier.slice(1));
    return null;
}

const absolute = (rel: string) => resolve(FRONTEND, rel);
const within = (path: string, dir: string) => path === dir || path.startsWith(dir + sep);

/** Whether a specifier, or a glob pattern, can reach a file under `dir` (`frontend/`-relative). */
function reaches(file: string, specifier: string, dir: string): boolean {
    const d = absolute(dir);
    const wild = specifier.search(/[*?[{]/);
    if (wild === -1) {
        const target = targetOf(file, specifier);
        return target !== null && within(absolute(target), d);
    }
    const head = specifier.slice(0, specifier.lastIndexOf('/', wild) + 1);
    const rest = specifier.slice(head.length);
    const base = targetOf(file, head || './');
    if (base === null) return false;
    const b = absolute(base);
    return within(b, d) || (d.startsWith(b + sep) && (rest.includes('/') || rest.includes('**')));
}

const reachesLab = (ref: Reference) => LAB_DIRS.some((dir) => reaches(ref.file, ref.specifier, dir));
const inLab = (file: string) => LAB_DIRS.some((dir) => file.startsWith(dir));

const describeRef = (ref: Reference) => `${ref.file}:${ref.line}  ${ref.kind} '${ref.specifier}'${ref.kind === 'dynamic' && !ref.guarded ? ` (not inside \`if (${GUARD})\`)` : ''}`;

// --- The verdicts --------------------------------------------------------------------------------------------

/** (a) References from outside the Lab that are neither erased nor the one guarded import of the layout. */
function outsideViolations(refs: Reference[]): string[] {
    const allowed = (ref: Reference) => ref.kind === 'type' || (ref.kind === 'dynamic' && ref.guarded && ref.file === LAYOUT_SITE.file && ref.specifier === LAYOUT_SITE.specifier);
    return refs.filter((ref) => !inLab(ref.file) && reachesLab(ref) && !allowed(ref)).map(describeRef);
}

/** (b) Imports of a virtual module by a file not registered for it. */
function virtualViolations(refs: Reference[]): string[] {
    return refs.filter((ref) => ref.kind !== 'type' && ref.specifier in VIRTUAL_IMPORTERS && !VIRTUAL_IMPORTERS[ref.specifier].files.includes(ref.file)).map(describeRef);
}

/** (d) References of a route file into the Lab's library that are not a guarded `import()`. */
function routeViolations(refs: Reference[]): string[] {
    return refs.filter((ref) => RUNTIME.has(ref.kind) && reaches(ref.file, ref.specifier, LAB_LIB) && !(ref.kind === 'dynamic' && ref.guarded)).map(describeRef);
}

/** The file a relative or `$lib` specifier loads, as the bundler would find it, or null. */
function resolveFile(from: string, specifier: string): string | null {
    const target = targetOf(from, specifier);
    if (target === null) return null;
    for (const candidate of [target, `${target}.ts`, `${target}.js`, `${target}/index.ts`, `${target}/index.js`]) {
        if (existsSync(absolute(candidate)) && statSync(absolute(candidate)).isFile()) return candidate;
    }
    return null;
}

const readSource = (file: string) => readFileSync(absolute(file), 'utf8');

/** Everything `entry` loads without `import()`: the files of its static closure, and every static edge between them. */
function staticClosure(entry: string, read: (file: string) => string = readSource): {files: string[]; edges: string[]} {
    const files = [entry];
    const edges: string[] = [];
    for (let i = 0; i < files.length; i++) {
        const from = files[i];
        for (const ref of scanSource(from, read(from)).refs) {
            if (ref.kind !== 'static' && ref.kind !== 'export') continue;
            const target = ref.specifier.startsWith('virtual:') ? ref.specifier : resolveFile(from, ref.specifier);
            // A package is outside the question.
            if (target === null) continue;
            edges.push(`${from} → ${target}`);
            if (!target.startsWith('virtual:') && !files.includes(target)) files.push(target);
        }
    }
    return {files, edges};
}

/** (c) Where the client's static closure crosses into the engines, the picker, or a virtual module. */
function clientViolations(closure: {files: string[]; edges: string[]}): string[] {
    const onDemand = (path: string) => path.startsWith(ENGINE) || path.startsWith(PICKER) || path.startsWith('virtual:');
    return closure.edges.filter((edge) => {
        const [from, to] = edge.split(' → ');
        return onDemand(to) && !onDemand(from);
    });
}

let tree: Scan | null = null;

/** The references of every source that can name the Lab, scanned once for the whole file. */
function scanTree(): Scan {
    if (tree) return tree;
    const refs: Reference[] = [];
    const errors: string[] = [];
    for (const file of sourceFiles()) {
        const text = readSource(file);
        if (!MAY_REFER.test(text)) continue;
        const scan = scanSource(file, text);
        refs.push(...scan.refs);
        errors.push(...scan.errors);
    }
    tree = {refs, errors};
    return tree;
}

const RULE_A = `The Designer Lab must stay out of release bundles. Outside ${LAB_LIB} and ${LAB_ROUTE}, reach it only through \`if (${GUARD}) import('${LAYOUT_SITE.specifier}')\` in ${LAYOUT_SITE.file}, or with a type-only reference (\`import type\`, which is erased — \`import {type X}\` is not). Move the code into the Lab, or load it from the client. Found:`;

describe('designer-lab imports — the scanner', () => {
    it('parses every source it reads', () => {
        expect(scanTree().errors).toEqual([]);
    });

    it.each([
        ['a static import', 'src/routes/(app)/fake/+page.svelte', '<script lang="ts">\n    import {start} from \'$lib/dev/designer-lab/client\';\n</script>'],
        ['an import whose specifiers are all types', 'src/lib/fake.ts', "import {type LabHook} from '$lib/dev/designer-lab/types';"],
        ['a re-export through a relative path', 'src/lib/stores/fake.ts', "export {start} from '../dev/designer-lab/client';"],
        ['an unguarded import()', 'src/routes/+layout.svelte', '<script lang="ts">\n    import(\'$lib/dev/designer-lab/client\');\n</script>'],
        ['an import() in the else branch', 'src/routes/+layout.svelte', '<script lang="ts">\n    if (__LF_DESIGNER_LAB__) {\n    } else import(\'$lib/dev/designer-lab/client\');\n</script>'],
        ['a guarded import() at another site', 'src/routes/(app)/+layout.svelte', '<script lang="ts">\n    if (__LF_DESIGNER_LAB__) import(\'$lib/dev/designer-lab/client\');\n</script>'],
        ['an import() in the markup', 'src/routes/(app)/fake/+page.svelte', "{#await import('$lib/dev/designer-lab/DesignerLab.svelte') then lab}<p>{String(lab)}</p>{/await}"],
        ['an import() under `{#if}` in the markup, which a release build keeps', 'src/routes/(app)/fake/+page.svelte', "{#if __LF_DESIGNER_LAB__}{#await import('$lib/dev/designer-lab/DesignerLab.svelte') then lab}<p>{String(lab)}</p>{/await}{/if}"],
        ['an import() of a template', 'src/lib/fake.ts', 'export const load = (name: string) => import(`$lib/dev/designer-lab/${name}.ts`);'],
        ['a glob that descends into the Lab', 'src/lib/fake.ts', "export const all = import.meta.glob('./dev/**/*.ts');"],
        ['a glob inside the Lab', 'src/lib/fake.ts', "export const all = import.meta.glob(['./other/*.ts', '$lib/dev/designer-lab/*.ts']);"],
    ])('flags %s', (_label, file, text) => {
        expect(MAY_REFER.test(text)).toBe(true);
        expect(outsideViolations(scanSource(file, text).refs)).toHaveLength(1);
    });

    it.each([
        ['the guarded import() of the layout', LAYOUT_SITE.file, '<script lang="ts">\n    if (__LF_DESIGNER_LAB__) import(\'$lib/dev/designer-lab/client\').then((lab) => lab.start());\n</script>'],
        ['an import type', 'src/lib/fake.ts', "import type {LabHook} from '$lib/dev/designer-lab/types';"],
        ['a declaration file', 'src/fake.d.ts', "declare global {\n    interface Window {\n        lab?: import('$lib/dev/designer-lab/types').LabHook;\n    }\n}\nexport {};"],
        ['a glob that cannot descend into the Lab', 'src/lib/features/changelog/changelog.ts', "export const all = import.meta.glob('../../../../../CHANGELOG.[a-z][a-z].md', {query: '?raw'});"],
        ['a folder that only shares a prefix', 'src/lib/fake.ts', "import {x} from '$lib/dev/designer-lab-notes/x';"],
    ])('accepts %s', (_label, file, text) => {
        expect(outsideViolations(scanSource(file, text).refs)).toEqual([]);
    });
});

describe('designer-lab imports — (a) the app reaches the Lab only through the guarded client import', () => {
    it('finds no other reference from outside the Lab', () => {
        expect(outsideViolations(scanTree().refs), `${RULE_A}\n`).toEqual([]);
    });

    it('still finds the guarded import of the layout and the type references of app.d.ts', () => {
        const refs = scanTree().refs;
        const site = refs.filter((r) => r.file === LAYOUT_SITE.file && r.specifier === LAYOUT_SITE.specifier);
        expect(
            site.map((r) => [r.kind, r.guarded]),
            `${LAYOUT_SITE.file} no longer imports ${LAYOUT_SITE.specifier}: if the client moved, update LAYOUT_SITE (and the Lab's docs)`,
        ).toEqual([['dynamic', true]]);
        expect(refs.some((r) => r.file === 'src/app.d.ts' && r.kind === 'type' && reachesLab(r))).toBe(true);
    });
});

describe('designer-lab imports — (b) the virtual modules', () => {
    it.each(Object.entries(VIRTUAL_IMPORTERS))('imports %s only where it is registered, and there still', (id, {files, why}) => {
        const importers = [
            ...new Set(
                scanTree()
                    .refs.filter((r) => r.specifier === id && r.kind !== 'type')
                    .map((r) => r.file),
            ),
        ].sort();
        expect(importers, `${id} is ${why}. Importers allowed: ${files.join(', ')}.`).toEqual(files);
    });

    it('flags an import by any other file, the client included', () => {
        expect(virtualViolations(scanSource(CLIENT, "import catalog from 'virtual:lf-color-catalog';").refs)).toHaveLength(1);
        expect(virtualViolations(scanSource(`${LAB_LIB}ColorEditor.svelte`, '<script lang="ts">\n    import index from \'virtual:lf-testid-index\';\n</script>').refs)).toHaveLength(1);
        expect(virtualViolations(scanSource(`${LAB_LIB}DesignerLab.svelte`, '<script lang="ts">\n    import catalog from \'virtual:lf-color-catalog\';\n</script>').refs)).toEqual([]);
    });
});

describe('designer-lab imports — (c) the client loads the engines and the picker on demand', () => {
    const message = `${CLIENT} is loaded by every page of a debug build: it must reach ${ENGINE} and ${PICKER} only through import(), directly and through what it imports. Static edges found:`;

    it('imports nothing of the engines or the picker statically, directly or transitively', () => {
        const closure = staticClosure(CLIENT);
        expect(clientViolations(closure), `${message}\n${closure.edges.join('\n')}`).toEqual([]);
        expect(closure.files).toContain(`${LAB_LIB}store.ts`);
    });

    it('still loads both of them, dynamically', () => {
        const dynamic = scanSource(CLIENT, readSource(CLIENT)).refs.filter((r) => r.kind === 'dynamic');
        expect(dynamic.some((r) => reaches(r.file, r.specifier, ENGINE))).toBe(true);
        expect(dynamic.some((r) => reaches(r.file, r.specifier, PICKER))).toBe(true);
    });

    it('flags a static import of an engine, also one that arrives through another module', () => {
        const direct = staticClosure(CLIENT, (file) => (file === CLIENT ? "import {applyState} from './engine';" : readSource(file)));
        expect(clientViolations(direct)).toEqual([`${CLIENT} → ${ENGINE}index.ts`]);
        const store = `${LAB_LIB}store.ts`;
        const transitive = staticClosure(CLIENT, (file) => (file === store ? `${readSource(store)}\nexport {follow} from './picker/overlay';` : readSource(file)));
        expect(clientViolations(transitive)).toEqual([`${store} → ${PICKER}overlay.ts`]);
    });
});

describe('designer-lab imports — (d) the route, compiled into every build', () => {
    const routeFiles = () => sourceFiles().filter((file) => file.startsWith(LAB_ROUTE) && /\/\+[^/]+$/.test(file));

    it('reaches the Lab only through a guarded import()', () => {
        const files = routeFiles();
        expect(files).toContain(`${LAB_ROUTE}+page.ts`);
        const refs = files.flatMap((file) => scanSource(file, readSource(file)).refs);
        expect(routeViolations(refs), `The route files of ${LAB_ROUTE} are in every build: they may load ${LAB_LIB} only inside \`if (${GUARD})\` with import(). Found:\n`).toEqual([]);
        expect(refs.some((r) => r.kind === 'dynamic' && r.guarded && reaches(r.file, r.specifier, LAB_LIB))).toBe(true);
    });

    it('flags a static import of the Lab in a route file', () => {
        const text = '<script lang="ts">\n    import Lab from \'$lib/dev/designer-lab/DesignerLab.svelte\';\n</script>\n<Lab />';
        expect(routeViolations(scanSource(`${LAB_ROUTE}+page.svelte`, text).refs)).toHaveLength(1);
    });
});
