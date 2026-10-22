/**
 * Gate: a chart's saved signals are drawn through one renderer, `lib/charts/chartSignalRendering.ts` (lots Y-39a, Y-42).
 *
 * ## What this protects
 *
 * Drawing a saved signal starts with `signalFromConfig(config)`: the registry rebuilds the signal from its config, the
 * page injects what it draws against — an FX pair's rates, a comparison's target — and calls `renderMulti`. Until Y-39a
 * that loop was written five times: the asset list and the FX list (`getRenderedSignals`, their cards), the settings
 * preview (`ChartSettingsModal`'s `renderLocalPreview`) and the two detail pages. The copies drifted: the preview named a
 * comparison «Asset #id» where the card named it after its target, drew a comparison with the chart's own asset where
 * the card skipped it, and turned an FX pair by its card where the card let the signal's own `_inverted` turn it. Each
 * copy is one more place the next rule has to reach. Y-39a moved the loop of the lists and the preview into
 * `lib/charts/chartSignalRendering.ts`, and Y-42 moved the two detail pages after them, handing the module their data
 * through `detailPageSignalSources(…)` (`lib/charts/chartPageSignals.ts`); this gate keeps the loop there: another copy
 * is red the day it is written.
 *
 * ## The rule, as this file checks it
 *
 *   - A call of `signalFromConfig(` — by its name, or through a namespace (`signals.signalFromConfig(`) — appears only in
 *     `lib/charts/chartSignalRendering.ts` and in the files of KNOWN_COPIES. Its declaration in
 *     `lib/charts/signals/registry.ts` is no call. `signalFromConfig` imported or re-exported under another name
 *     (`signalFromConfig as rebuild`) counts as a call: under another name, its calls are out of the gate's sight.
 *   - KNOWN_COPIES only shrinks, and Y-42 emptied it: it named the two detail pages, which adopted the module in that lot.
 *     The list stays empty — a new copy of the loop does not join it, it renders through the module. The machinery stays:
 *     an entry whose file no longer calls `signalFromConfig(` fails until it is removed, so a copy once gone cannot come
 *     back unnoticed. It is proven on synthetic known copies (SYNTHETIC_COPIES), passed to the checks explicitly, and on
 *     a real detail page standing in for one.
 *   - The scan reads something: the walk reaches the components, the registry, the module and the two detail pages; the
 *     registry declares `signalFromConfig` exactly once, where the scanner sees it; and the module exists and draws
 *     through `signalFromConfig(` — «no call outside the module» is also what a scanner matching nothing would report.
 *
 * Every check is a pure function of a `{path: text}` tree, read as the walk reads `src`: it is run first on synthetic
 * trees that break the rule once — the proof that it can fail — then on the files of `src`, and last on those files
 * mutated in memory: the module's own text copied elsewhere, a detail page with a call injected, a detail page standing
 * in for a known copy. Comments are blanked before anything is matched; the blanking keeps offsets, so the lines in the
 * messages are the files' own. Findings are judged by file, never by line.
 *
 * ## What it cannot see
 *
 *   - A signal rebuilt without the registry: `new LinearSignal(…)`, or `createSignal(…)` with the config's values copied
 *     in by hand. The forms are a floor: grow them with the rule.
 *   - `signalFromConfig` reached through a destructured alias (`const {signalFromConfig: rebuild} = signals`), or kept in
 *     a variable and called through it.
 *   - Comment blanking is a floor too: a `//` inside a string swallows the rest of its line. Blanking only removes text,
 *     so it can hide a call, never invent one; a string that spells a call out is reported as one.
 *
 * The walk reads every `.svelte`, `.ts` and `.js` file under `src` but the tests — every `*.test.ts`, this file among
 * them, and anything under a `__tests__/` or `__mocks__/` directory — and never enters `node_modules`.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`), beside the other
 * gates.
 */

import {describe, expect, it} from 'vitest';
import {readdirSync, readFileSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

/** `frontend/`: every path is read, and reported, relative to it. */
const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '..');

/** The one renderer of saved signals (Y-39a). */
const MODULE = 'src/lib/charts/chartSignalRendering.ts';

/** Where `signalFromConfig` is declared: its declaration is no call, and the control that the scanner reads its name. */
const REGISTRY = 'src/lib/charts/signals/registry.ts';

/** The two detail pages: the last copies of the loop, adopted in Y-42. The walk must reach them, and the checks bite on them. */
const DETAIL_PAGES = ['src/routes/(app)/assets/[id]/+page.svelte', 'src/routes/(app)/fx/[pair]/+page.svelte'] as const;

/** What every offender is told. */
const RULE = 'render saved signals through lib/charts/chartSignalRendering.ts';

interface KnownCopy {
    file: string;
    why: string;
}

/**
 * The copies of the loop that may remain for now, each with its reason. The list only shrinks: an entry whose file no
 * longer calls `signalFromConfig(` fails the gate until it is removed. Y-42 moved the two detail pages onto the module
 * and emptied it, so it stays empty: a new copy renders through `lib/charts/chartSignalRendering.ts`.
 */
const KNOWN_COPIES: readonly KnownCopy[] = [];

/** The types the walk reads: every one that can hold a script. */
const SCANNED = /\.(svelte|ts|js)$/;

/** Files by path, relative to `frontend/`: the files of `src`, or a synthetic tree. */
type Tree = Record<string, string>;

// ---------------------------------------------------------------------------
// Reading
// ---------------------------------------------------------------------------

const lineAt = (text: string, offset: number): number => text.slice(0, offset).split('\n').length;
const collapse = (s: string): string => s.trim().replace(/\s+/g, ' ');

/** Replace every match with spaces, keeping newlines: offsets and line numbers survive the blanking. */
function blank(text: string, pattern: RegExp): string {
    return text.replace(pattern, (found) => found.replace(/[^\n]/g, ' '));
}

const blankCssComments = (css: string): string => blank(css, /\/\*[\s\S]*?\*\//g);
/** `//` counts as a comment only when it does not follow `:` — `https://` stays code. */
const blankJsComments = (js: string): string => blank(blank(js, /\/\*[\s\S]*?\*\//g), /(?<![:\\])\/\/[^\n]*/g);

/** A file with its comments blanked the way its type means them: a script as JS; a component as HTML, its scripts and styles each by their own syntax. */
function codeOf(file: string, text: string): string {
    if (!file.endsWith('.svelte')) return blankJsComments(text);
    let out = blank(text, /<!--[\s\S]*?-->/g);
    out = out.replace(/(<script\b[^>]*>)([\s\S]*?)(<\/script\s*>)/gi, (_m, open: string, body: string, close: string) => open + blankJsComments(body) + close);
    out = out.replace(/(<style\b[^>]*>)([\s\S]*?)(<\/style\s*>)/gi, (_m, open: string, body: string, close: string) => open + blankCssComments(body) + close);
    return out;
}

/** The code around an offset, on its own line, for a message. */
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

/** A call of `signalFromConfig`, by its name or through a namespace — never a longer name ending in it — spaces and line breaks allowed before the parenthesis. */
const CALL = /(?<![\w$])signalFromConfig\s*\(/g;

/** What precedes a match that is its declaration (`function signalFromConfig(`), not a call. */
const DECLARATION = /\bfunction\s*\*?\s*$/;

/** `signalFromConfig as <name>`: imported or re-exported under another name. */
const ALIAS = /(?<![\w$])signalFromConfig\s+as\s+([\w$]+)/g;

interface Site {
    file: string;
    line: number;
    kind: 'call' | 'alias';
    excerpt: string;
}

interface Audit {
    /** Every file of the tree the scan reads (`isScanned`), sorted. */
    files: string[];
    /** Every call of `signalFromConfig(`, and every alias of it, outside comments. */
    sites: Site[];
    /** The lines of `registry.ts` that declare `signalFromConfig`. */
    registryDeclarations: number[];
}

/** Whether a path (relative to `frontend/`) is code this gate reads: a type that can hold a script, and neither a test (`*.test.ts`, anything under `__tests__/` or `__mocks__/`) nor a dependency. */
function isScanned(path: string): boolean {
    if (!SCANNED.test(path) || path.endsWith('.test.ts')) return false;
    return !path.split('/').some((segment) => segment === '__tests__' || segment === '__mocks__' || segment === 'node_modules');
}

/** What a tree holds, read as the walk reads `src`: a path `isScanned` refuses is dropped first. */
function audit(tree: Tree): Audit {
    const files = Object.keys(tree).filter(isScanned).sort();
    const result: Audit = {files, sites: [], registryDeclarations: []};
    for (const file of files) {
        const code = codeOf(file, tree[file]);
        for (const match of code.matchAll(CALL)) {
            if (DECLARATION.test(code.slice(Math.max(0, match.index - 40), match.index))) {
                if (file === REGISTRY) result.registryDeclarations.push(lineAt(code, match.index));
                continue;
            }
            result.sites.push({file, line: lineAt(code, match.index), kind: 'call', excerpt: excerptAt(code, match.index)});
        }
        for (const match of code.matchAll(ALIAS)) {
            if (match[1] === 'signalFromConfig') continue;
            result.sites.push({file, line: lineAt(code, match.index), kind: 'alias', excerpt: excerptAt(code, match.index)});
        }
    }
    return result;
}

// ---------------------------------------------------------------------------
// The checks: pure functions of an audit
// ---------------------------------------------------------------------------

const isAllowed = (file: string, copies: readonly KnownCopy[]): boolean => file === MODULE || copies.some((copy) => copy.file === file);

/** Every call, and every alias, outside the module and the known copies. */
function offenders({sites}: Audit, copies: readonly KnownCopy[] = KNOWN_COPIES): string[] {
    return sites.filter((site) => !isAllowed(site.file, copies)).map((site) => `${site.file}:${site.line}  ${site.excerpt}  → ${site.kind === 'alias' ? 'signalFromConfig under another name hides its calls from this gate: ' : ''}${RULE}`);
}

/** The known copies that no longer call `signalFromConfig(`: the list only shrinks. */
function staleCopies({sites}: Audit, copies: readonly KnownCopy[] = KNOWN_COPIES): string[] {
    return copies.filter((copy) => !sites.some((site) => site.file === copy.file && site.kind === 'call')).map((copy) => `${copy.file}  no longer calls signalFromConfig( — remove it from KNOWN_COPIES: the list only shrinks`);
}

/** Whatever would let the rule pass by reading nothing. */
function emptyScans({files, registryDeclarations}: Audit): string[] {
    const problems: string[] = [];
    if (!files.includes(REGISTRY)) problems.push(`${REGISTRY}  not found: where signalFromConfig is declared`);
    else if (registryDeclarations.length !== 1) problems.push(`${REGISTRY}  the scanner finds ${registryDeclarations.length} declarations of signalFromConfig there, expected exactly 1 — if it is declared another way now, teach the scanner the new form`);
    if (!files.some((file) => file.endsWith('.svelte'))) problems.push('no .svelte file: the walk does not reach the components');
    return problems;
}

/** The module, read: it exists, and draws through the registry (the contract's rule 2: `signalFromConfig(config)`). */
function moduleProblems({files, sites}: Audit): string[] {
    if (!files.includes(MODULE)) return [`${MODULE}  not found: the one renderer of saved signals does not exist`];
    if (!sites.some((site) => site.file === MODULE && site.kind === 'call')) return [`${MODULE}  never calls signalFromConfig(: the renderer rebuilds saved signals through the registry`];
    return [];
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

/** The `file:line` a message starts with. */
const placeIn = (message: string): string => message.split('  ')[0];

// ---------------------------------------------------------------------------
// Synthetic trees
// ---------------------------------------------------------------------------

const PAGE = 'src/routes/(app)/somewhere/+page.svelte';

/** The registry as it is written: a comment quoting a call, then the declaration. */
const REGISTRY_TEXT = [
    '/**',
    ' * Recreate a signal instance from a serialized config: `signalFromConfig(config)`.',
    ' */',
    'export function signalFromConfig(config: SignalConfig): ChartSignal | null {',
    '    const Cls = SIGNAL_REGISTRY.get(config.signalType);',
    '    return Cls ? new Cls(config.id, config.style, config.params) : null;',
    '}',
].join('\n');

/** The module, drawing through the registry. */
const MODULE_TEXT = ["import {signalFromConfig} from './signals/registry';", '', 'export function renderLocalSignal(config, baseData, viewMode, sources) {', '    const instance = signalFromConfig(config);', '    return instance ? instance.renderMulti(baseData, viewMode) : [];', '}'].join('\n');

/** A component that draws saved signals itself, as the detail pages do today. */
const COPY_TEXT = ['<script lang="ts">', "    import {signalFromConfig} from '$lib/charts/signals';", '    let overlaySignals = $derived(configs.flatMap((cfg) => signalFromConfig(cfg)?.renderMulti(data, viewMode) ?? []));', '</script>', '', '<PriceChartFull {data} {overlaySignals} />'].join('\n');

/** A tree without one of its files. */
const without = (tree: Tree, path: string): Tree => Object.fromEntries(Object.entries(tree).filter(([file]) => file !== path));

/**
 * Two synthetic known copies: KNOWN_COPIES is empty, so the allowance and the staleness checks are proven on these. The
 * synthetic checks below pass them to `offenders` and `staleCopies` explicitly — never through the default, the real list.
 */
const SYNTHETIC_COPIES: readonly KnownCopy[] = [
    {
        file: 'src/routes/(app)/synthetic-old/+page.svelte',
        why: 'A synthetic page that still draws its saved signals with a loop of its own: what the allowance and the staleness checks are proven on.',
    },
    {
        file: 'src/routes/(app)/synthetic-older/+page.svelte',
        why: 'A second synthetic page with a loop of its own: the one whose file the staleness check finds gone.',
    },
];

/** A tree that keeps the rule: the registry, the module, the two synthetic known copies and a page that only imports the module. */
const CLEAN: Tree = {
    [REGISTRY]: REGISTRY_TEXT,
    [MODULE]: MODULE_TEXT,
    [SYNTHETIC_COPIES[0].file]: COPY_TEXT,
    [SYNTHETIC_COPIES[1].file]: COPY_TEXT,
    [PAGE]: ['<script lang="ts">', "    import {renderLocalSignals} from '$lib/charts/chartSignalRendering';", '</script>', '', '<p>{renderLocalSignals.name}</p>'].join('\n'),
};

describe('Saved signals are drawn through lib/charts/chartSignalRendering.ts only (Y-39a gate)', () => {
    describe('the scanner, on synthetic trees', () => {
        it('a tree that keeps the rule passes every check', () => {
            const result = audit(CLEAN);

            expect({offenders: offenders(result, SYNTHETIC_COPIES), stale: staleCopies(result, SYNTHETIC_COPIES), empty: emptyScans(result), module: moduleProblems(result)}).toEqual({offenders: [], stale: [], empty: [], module: []});
        });

        it('finds a call wherever the code puts it — in a script, in the markup, through a namespace, across a line break — and names the file and the rule', () => {
            const page = [
                '<script lang="ts">',
                "    import * as signals from '$lib/charts/signals';",
                '    const one = signalFromConfig(cfg);',
                '    const two = signals.signalFromConfig(cfg);',
                '    const three = signalFromConfig',
                '        (cfg);',
                '</script>',
                '',
                '<p>{signalFromConfig(cfg)?.getLabel()}</p>',
            ].join('\n');

            const found = offenders(audit({...CLEAN, [PAGE]: page}), SYNTHETIC_COPIES);

            expect(found.map(placeIn)).toEqual([`${PAGE}:3`, `${PAGE}:4`, `${PAGE}:5`, `${PAGE}:9`]);
            expect(found.every((message) => message.endsWith(`→ ${RULE}`))).toBe(true);
        });

        it('reads no call in a comment, an import, a longer name or the declaration', () => {
            const helper = 'src/lib/charts/somewhereHelper.ts';
            const text = [
                "import {signalFromConfig, type SignalConfig} from '$lib/charts/signals';",
                '// const old = signalFromConfig(cfg);',
                '/* signalFromConfig(cfg) */',
                '/**',
                ' * Rebuilt by `signalFromConfig(config)` — see the registry.',
                ' */',
                'const a = _signalFromConfig(cfg) ?? $signalFromConfig(cfg);',
                'const b = signalFromConfigCache(cfg);',
                "const url = 'https://example.org/signalFromConfig';",
                'export {signalFromConfig};',
            ].join('\n');
            const markup = ['<!-- signalFromConfig(cfg) -->', '<script lang="ts">', '    // signalFromConfig(cfg)', '</script>'].join('\n');

            expect(offenders(audit({...CLEAN, [helper]: text, [PAGE]: markup}), SYNTHETIC_COPIES)).toEqual([]);
            // The declaration is no call, in the registry or in a copy of it.
            expect(offenders(audit({...CLEAN, [helper]: REGISTRY_TEXT}), SYNTHETIC_COPIES)).toEqual([]);
        });

        it('counts signalFromConfig under another name as a call', () => {
            const text = ["import {signalFromConfig as rebuild} from '$lib/charts/signals';", 'const one = rebuild(cfg);'].join('\n');

            const found = offenders(audit({...CLEAN, 'src/lib/charts/somewhereHelper.ts': text}), SYNTHETIC_COPIES);

            expect(found.map(placeIn)).toEqual(['src/lib/charts/somewhereHelper.ts:1']);
            expect(found[0]).toContain('under another name');
        });

        it('allows the module and the known copies only: a copy of a known copy anywhere else is an offender', () => {
            const elsewhere = 'src/lib/components/charts/SomewhereCard.svelte';

            expect(offenders(audit({...CLEAN, [elsewhere]: COPY_TEXT}), SYNTHETIC_COPIES).map(placeIn)).toEqual([`${elsewhere}:3`]);
            expect(offenders(audit({...CLEAN, [elsewhere]: MODULE_TEXT}), SYNTHETIC_COPIES).map(placeIn)).toEqual([`${elsewhere}:4`]);
        });

        it('a known copy that no longer calls signalFromConfig( is stale — and so is one whose file is gone', () => {
            const adopted = audit({...CLEAN, [SYNTHETIC_COPIES[0].file]: ['<script lang="ts">', "    import {renderLocalSignals} from '$lib/charts/chartSignalRendering';", '</script>'].join('\n')});

            expect(staleCopies(adopted, SYNTHETIC_COPIES).map(placeIn)).toEqual([SYNTHETIC_COPIES[0].file]);
            expect(staleCopies(audit(without(CLEAN, SYNTHETIC_COPIES[1].file)), SYNTHETIC_COPIES).map(placeIn)).toEqual([SYNTHETIC_COPIES[1].file]);
            // An alias alone keeps no copy alive: it is no call.
            const aliased = audit({...CLEAN, [SYNTHETIC_COPIES[0].file]: "import {signalFromConfig as rebuild} from '$lib/charts/signals';"});
            expect(staleCopies(aliased, SYNTHETIC_COPIES).map(placeIn)).toEqual([SYNTHETIC_COPIES[0].file]);
        });

        it('fails a scan that reads nothing: no registry, a registry declaring it twice or not at all, no component', () => {
            const twice = `${REGISTRY_TEXT}\n${REGISTRY_TEXT}`;

            expect(emptyScans(audit(without(CLEAN, REGISTRY)))).toHaveLength(1);
            expect(emptyScans(audit({...CLEAN, [REGISTRY]: twice}))).toHaveLength(1);
            expect(emptyScans(audit({...CLEAN, [REGISTRY]: '// export function signalFromConfig(config) {}'}))).toHaveLength(1);
            expect(emptyScans(audit({[REGISTRY]: REGISTRY_TEXT, [MODULE]: MODULE_TEXT}))).toEqual(['no .svelte file: the walk does not reach the components']);
        });

        it('fails a module that is missing, or that never calls signalFromConfig(', () => {
            expect(moduleProblems(audit(without(CLEAN, MODULE))).map(placeIn)).toEqual([MODULE]);
            expect(moduleProblems(audit({...CLEAN, [MODULE]: '// signalFromConfig(config)\nexport const renderLocalSignal = () => [];'})).map(placeIn)).toEqual([MODULE]);
        });

        it('reads no test, harness or mock', () => {
            expect(isScanned(MODULE)).toBe(true);
            expect(isScanned('src/routes/(app)/assets/+page.svelte')).toBe(true);
            expect(isScanned('src/lib/charts/__tests__/chartSignalRendering.test.ts')).toBe(false);
            expect(isScanned('src/signalRendering.gate.test.ts')).toBe(false);
            expect(isScanned('src/lib/components/charts/__tests__/Recorder.svelte')).toBe(false);
            expect(isScanned('src/__mocks__/$app/stores.ts')).toBe(false);
            expect(offenders(audit({...CLEAN, 'src/lib/components/charts/ChartSettingsModal.test.ts': 'const instance = signalFromConfig(cfg);'}), SYNTHETIC_COPIES)).toEqual([]);
        });

        it('the synthetic known copies are explained and name each file once, as a real known copy must', () => {
            expect(SYNTHETIC_COPIES.filter((copy) => copy.why.trim().length < 40).map((copy) => copy.file)).toEqual([]);
            expect(new Set(SYNTHETIC_COPIES.map((copy) => copy.file)).size).toBe(SYNTHETIC_COPIES.length);
        });
    });

    describe('the files of src', () => {
        it('the walk reads every component and script of src — and no test or mock', () => {
            const files = Object.keys(srcTree());

            expect(files.filter((file) => file.endsWith('.svelte')).length, 'the walk reaches the components').toBeGreaterThan(100);
            expect(files, 'the registry, the module and the two detail pages').toEqual(expect.arrayContaining([REGISTRY, MODULE, ...DETAIL_PAGES]));
            const unwanted = files.filter((file) => file.endsWith('.test.ts') || file.includes('/__tests__/') || file.includes('/__mocks__/') || file.includes('/node_modules/'));
            expect(unwanted, 'tests and mocks are not opened at all: they may call signalFromConfig( in any form, and none of them is the app').toEqual([]);
        });

        it('the scan reads what the rule needs: the registry declares signalFromConfig once, where the scanner sees it', () => {
            expect(emptyScans(srcAudit()), 'the scan reads nothing the rule needs: fix the walk or the patterns — never relax this, the rule passes on an empty scan').toEqual([]);
        });

        it('signalFromConfig( is called only in lib/charts/chartSignalRendering.ts and in the known copies', () => {
            const found = offenders(srcAudit());

            expect(found, ['', `Saved signals are drawn in one place: ${RULE} (Y-39a, Y-42). ${found.length} call(s) outside it:`, '', ...found, ''].join('\n  ')).toEqual([]);
        });

        it('KNOWN_COPIES only shrinks: every known copy still calls signalFromConfig(', () => {
            expect(staleCopies(srcAudit())).toEqual([]);
        });

        it('lib/charts/chartSignalRendering.ts exists and draws through signalFromConfig(', () => {
            expect(moduleProblems(srcAudit()), 'the one renderer of saved signals is missing, or rebuilds no signal through the registry: «no call outside the module» says nothing until it does').toEqual([]);
        });

        it('KNOWN_COPIES is empty: the list only shrinks, and Y-42 emptied it', () => {
            expect(
                KNOWN_COPIES.map((copy) => copy.file),
                `KNOWN_COPIES only shrinks, and Y-42 emptied it: a copy of the loop does not join the list — ${RULE}`,
            ).toEqual([]);
        });

        it('KNOWN_COPIES is explained, and names each file once', () => {
            expect(KNOWN_COPIES.filter((copy) => copy.why.trim().length < 40).map((copy) => copy.file)).toEqual([]);
            expect(new Set(KNOWN_COPIES.map((copy) => copy.file)).size).toBe(KNOWN_COPIES.length);
        });

        describe('the checks bite on these very files: one mutation each, in memory, turns them red', () => {
            /** A call of the registry's function, as a page that rebuilds a signal itself writes it, put at the head of the page's script. */
            const injectCall = (text: string): string => text.replace(/(<script\b[^>]*>)/, '$1\n    const injected = signalFromConfig(cfg);');

            /** The files of `src` a mutation starts from: the registry and the module, and — for a detail page — the page. */
            function base(...pages: string[]): Tree {
                const tree = srcTree();
                const files = [REGISTRY, MODULE, ...pages];
                const missing = files.filter((file) => !tree[file]);
                if (missing.length) throw new Error(`${missing.join(', ')} is not read by the walk`);
                return Object.fromEntries(files.map((file) => [file, tree[file]]));
            }

            it('the module, and the registry, keep the rule on their own — and the module’s real text, copied to another path, is an offender', () => {
                const start = base();
                const moduleText = start[MODULE];
                expect({offenders: offenders(audit(start), []), stale: staleCopies(audit(start), [])}, 'the files the mutation starts from keep the rule on their own').toEqual({offenders: [], stale: []});

                const elsewhere = 'src/routes/(app)/somewhere/+page.svelte';
                const copied = offenders(audit({...start, [elsewhere]: moduleText}), []);

                expect(copied.length, 'the module’s text copied elsewhere').toBeGreaterThan(0);
                expect(copied.every((message) => message.startsWith(`${elsewhere}:`))).toBe(true);
            });

            it.each(DETAIL_PAGES)('%s, with one signalFromConfig(cfg) call injected, is an offender — and is none without it', (page) => {
                const start = base(page);
                expect({offenders: offenders(audit(start), []), stale: staleCopies(audit(start), [])}, `${page} keeps the rule on its own: it calls signalFromConfig( — render saved signals through the module`).toEqual({offenders: [], stale: []});

                const injected = injectCall(start[page]);
                expect(injected, 'the mutation applies').not.toBe(start[page]);
                const found = offenders(audit({...start, [page]: injected}), []);

                expect(found.map(placeIn), 'one injected call, one offender').toHaveLength(1);
                expect(found[0].startsWith(`${page}:`)).toBe(true);
            });

            it.each(DETAIL_PAGES)('%s, standing in for a known copy, is stale — and is not once a call is injected', (page) => {
                const start = base(page);
                const copies: readonly KnownCopy[] = [{file: page, why: 'A real detail page standing in for a known copy: the staleness check is proven on a real file, not only on a synthetic one.'}];

                expect(staleCopies(audit(start), copies).map(placeIn), `${page} calls signalFromConfig( — it has not adopted the module`).toEqual([page]);
                expect(staleCopies(audit({...start, [page]: injectCall(start[page])}), copies), 'a copy that calls signalFromConfig( is alive: the check is not stale on everything').toEqual([]);
            });
        });
    });
});
