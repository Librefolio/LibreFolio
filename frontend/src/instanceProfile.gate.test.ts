/**
 * Gate: the instance profile is compared in one place, `$lib/features/instance/profile` (workstream A, H-nit: one helper
 * for the confirmed-profile rule).
 *
 * ## What this protects
 *
 * `instanceConfig` (`$lib/features/instance/instanceConfig.svelte`) holds `DEFAULT_INSTANCE_CONFIG` until the server
 * answers `GET /api/v1/system/instance`, and whenever it cannot — and the defaults say `profile: 'selfhosted'`. So
 * `instanceConfig.config.profile === 'selfhosted'` is already true before the answer, while the request is in flight, and
 * after a request that failed before any answer: on a managed instance a donation would flash, a release probe would
 * reach GitHub. What the app may act on is the answer, `instanceConfig.loaded && profile === …`. That rule was written by
 * hand six times in five files — four self-hosted comparisons, two managed ones (`ForgotPasswordCard`) — each free to
 * forget `loaded`; it now lives in `selfHostedConfirmed()` and `managedConfirmed()` (`src/lib/features/instance/profile.ts`,
 * pinned by `profile.test.ts`), and this gate keeps that file the only place there is. A comparison written anywhere else
 * is a copy of the rule — right or wrong the day it is written, and one more place to find the day the rule changes.
 *
 * ## The rule, as this file checks it
 *
 * No product source but `profile.ts` compares the profile with `'selfhosted'` or `'managed'`. A comparison is
 *   - `===`, `!==`, `==` or `!=` between the profile and the literal, in either order; or a `case` of a `switch` on the
 *     profile;
 *   - the profile: a member named `profile` — `x.profile`, `x?.profile`, `x['profile']` — or a variable named `profile`,
 *     so that `const {profile} = instanceConfig.config` hides nothing;
 *   - the literal: `'…'`, `"…"`, or a backtick literal without a substitution; either operand may sit under parentheses,
 *     `!`, `as` or `satisfies`.
 * Comparisons are found on the syntax tree — TypeScript's for a module, Svelte's for a component (module script, instance
 * script and every expression of the markup) — so a comment, a string, a type or an object literal never counts as one
 * (`DEFAULT_INSTANCE_CONFIG`'s `profile: 'selfhosted'`, the store's `// 'selfhosted' | 'managed'`), and a comparison
 * spread over several lines does. The literals are the values of `InstanceConfig['profile']`, tied to the generated
 * client's type: a profile added there fails type-checking here until the gate learns it.
 *
 * It reads the product sources under `src`: every `.ts` and `.svelte` file but the tests (`*.test.ts`, `*.spec.ts`),
 * anything under `__tests__/` or `__mocks__/`, and the generated API clients (`src/lib/api/generated*.ts`,
 * `*.generated.ts`) — the walk of `financialMathExceptions.gate.test.ts`. `profile.ts` is read too: exempt from the rule,
 * it is the live positive control.
 *
 * Positive controls: "nothing compares" is also what a scanner that reads nothing would report. Every form runs through
 * the scanner the real files go through, flagged where it must be and spared where it must not; the verdict flags a
 * comparison in any file but `profile.ts`, and spares `profile.ts` as the approved design writes it; the walk reaches both
 * kinds of file; and the real `profile.ts`, the one place allowed to compare, must show the scanner a comparison with each
 * profile.
 *
 * ## What it cannot see
 *
 * Its forms are a floor. It does not follow a value: an alias (`const p = instanceConfig.config.profile; p === 'managed'`),
 * a constant holding the literal (`profile === MANAGED`), a lookup keyed by the profile (`LABELS[cfg.profile]`),
 * `['managed'].includes(cfg.profile)` and `Object.is(cfg.profile, 'managed')` all pass. Nor does it judge what a
 * comparison is for: any comparison of the profile with one of its values is a copy of the rule, and the fix is a helper —
 * a new one in `profile.ts` if neither says what the site needs. When the rule grows (a third profile, another field read
 * the same way), grow the forms with it. Only `.ts` and `.svelte` are read.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */

import {describe, expect, it} from 'vitest';
import {readdirSync, readFileSync} from 'node:fs';
import {dirname, join, relative, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';
import {parse as parseSvelte} from 'svelte/compiler';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';

/** `frontend/`: every path is read, and reported, relative to it — the directory the runner starts vitest from. */
const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(FRONTEND, 'src');

/** The one place allowed to compare the profile: the helpers every other source calls. */
const PROFILE_HELPERS = 'src/lib/features/instance/profile.ts';
/** The specifier the sources import them by. */
const PROFILE_SPECIFIER = '$lib/features/instance/profile';

/** The member, or the variable, that holds the profile. */
const PROFILE_FIELD = 'profile';

/**
 * The helper that says «the server answered, and said this profile», for each value of `InstanceConfig['profile']`: a
 * profile added to the generated client fails type-checking here until the gate learns it.
 */
const HELPERS: Record<InstanceConfig['profile'], string> = {selfhosted: 'selfHostedConfirmed()', managed: 'managedConfirmed()'};

type Profile = keyof typeof HELPERS;

/** The literals a comparison of the profile is made with. */
const PROFILES = Object.keys(HELPERS) as Profile[];

/** The store: it spells the profile with both its values — `DEFAULT_INSTANCE_CONFIG`, a usage comment — and compares neither. */
const STORE = 'src/lib/features/instance/instanceConfig.svelte.ts';

const DONATIONS = 'src/lib/features/support/donations.svelte.ts';
const UPDATE_CHECK = 'src/lib/features/update-check/updateCheck.ts';
const FORGOT_PASSWORD = 'src/lib/features/auth/ForgotPasswordCard.svelte';
/** The files of the six comparisons this gate was written red against: they call the helpers since, and the walk must still reach them. */
const CALLERS = ['src/lib/components/assets/AssetSearchAutocomplete.svelte', 'src/lib/components/layout/ChangelogModal.svelte', FORGOT_PASSWORD, DONATIONS, UPDATE_CHECK];

const collapse = (s: string): string => s.trim().replace(/\s+/g, ' ');
const clip = (s: string, max = 160): string => (s.length > max ? `${s.slice(0, max - 1)}…` : s);
const lineAt = (text: string, offset: number): number => text.slice(0, offset).split('\n').length;
const asProfile = (value: string | null): Profile | null => (value !== null && (PROFILES as string[]).includes(value) ? (value as Profile) : null);

// ---------------------------------------------------------------------------
// The sources
// ---------------------------------------------------------------------------

/** Whether a path (relative to `frontend/`) is a product source this gate reads. */
function isScanned(path: string): boolean {
    if (!/\.(ts|svelte)$/.test(path) || /\.(test|spec)\.ts$/.test(path)) return false;
    // The generated API clients: written by `./dev.py api sync` and `scripts/generate-tools-client.mjs`, never by hand.
    if (/^src\/lib\/api\/generated[^/]*\.ts$/.test(path) || path.endsWith('.generated.ts')) return false;
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

// ---------------------------------------------------------------------------
// The comparisons, found on the syntax tree
// ---------------------------------------------------------------------------

interface Comparison {
    file: string;
    line: number;
    offset: number;
    /** The literal the profile is compared with. */
    profile: Profile;
    /** `!==` or `!=`: the site wants the negation of the helper. */
    negated: boolean;
    /** The comparison's source, whitespace collapsed: what the verdict prints. */
    expr: string;
}

interface Scan {
    comparisons: Comparison[];
    parseErrors: string[];
}

// --- `.ts`: the TypeScript tree --------------------------------------------------------------------

/** The equality operators, each with whether it negates. */
const TS_EQUALITY: ReadonlyMap<ts.SyntaxKind, boolean> = new Map([
    [ts.SyntaxKind.EqualsEqualsEqualsToken, false],
    [ts.SyntaxKind.EqualsEqualsToken, false],
    [ts.SyntaxKind.ExclamationEqualsEqualsToken, true],
    [ts.SyntaxKind.ExclamationEqualsToken, true],
]);

/** The expression under parentheses, `!`, `as`, `satisfies` and `<T>`: the value, spelled plainly. */
function tsUnwrap(node: ts.Expression): ts.Expression {
    let inner = node;
    while (ts.isParenthesizedExpression(inner) || ts.isNonNullExpression(inner) || ts.isAsExpression(inner) || ts.isSatisfiesExpression(inner) || ts.isTypeAssertionExpression(inner)) inner = inner.expression;
    return inner;
}

/** A string spelled out in the source: `'x'`, `"x"`, or a backtick literal without a substitution. */
function tsStaticString(node: ts.Expression): string | null {
    const inner = tsUnwrap(node);
    return ts.isStringLiteral(inner) || ts.isNoSubstitutionTemplateLiteral(inner) ? inner.text : null;
}

/** Whether an expression holds the profile: a member named `profile` — `a.profile`, `a?.profile`, `a['profile']` — or a variable of that name. */
function tsIsProfile(node: ts.Expression): boolean {
    const inner = tsUnwrap(node);
    if (ts.isIdentifier(inner)) return inner.text === PROFILE_FIELD;
    if (ts.isPropertyAccessExpression(inner)) return inner.name.text === PROFILE_FIELD;
    if (ts.isElementAccessExpression(inner)) return tsStaticString(inner.argumentExpression) === PROFILE_FIELD;
    return false;
}

/** The profile two operands compare the profile with, in either order — or null when they are not the profile and one of its values. */
function tsCompared(left: ts.Expression, right: ts.Expression): Profile | null {
    if (tsIsProfile(left)) return asProfile(tsStaticString(right));
    if (tsIsProfile(right)) return asProfile(tsStaticString(left));
    return null;
}

/** The comparisons of the profile, and the parse errors, of one module. */
function scanScript(file: string, text: string): Scan {
    const scan: Scan = {comparisons: [], parseErrors: []};
    const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
    const lineOf = (offset: number): number => sf.getLineAndCharacterOfPosition(offset).line + 1;
    const spelled = (node: ts.Node): string => collapse(text.slice(node.getStart(sf), node.end));
    const diagnostics = (sf as unknown as {parseDiagnostics?: readonly ts.Diagnostic[]}).parseDiagnostics ?? [];
    for (const diagnostic of diagnostics) scan.parseErrors.push(`${file}:${lineOf(diagnostic.start ?? 0)}  ${ts.flattenDiagnosticMessageText(diagnostic.messageText, ' ')}`);
    const record = (offset: number, profile: Profile, negated: boolean, expr: string): void => {
        scan.comparisons.push({file, line: lineOf(offset), offset, profile, negated, expr});
    };
    const visit = (node: ts.Node): void => {
        if (ts.isBinaryExpression(node)) {
            const negated = TS_EQUALITY.get(node.operatorToken.kind);
            const profile = negated === undefined ? null : tsCompared(node.left, node.right);
            if (profile) record(node.getStart(sf), profile, negated === true, spelled(node));
        } else if (ts.isSwitchStatement(node) && tsIsProfile(node.expression)) {
            for (const clause of node.caseBlock.clauses) {
                if (!ts.isCaseClause(clause)) continue;
                const profile = asProfile(tsStaticString(clause.expression));
                if (profile) record(clause.getStart(sf), profile, false, `switch (${spelled(node.expression)}) { case ${spelled(clause.expression)} }`);
            }
        }
        ts.forEachChild(node, visit);
    };
    visit(sf);
    scan.comparisons.sort((a, b) => a.offset - b.offset);
    return scan;
}

// --- `.svelte`: Svelte's tree — module script, instance script, markup -----------------------------

/** An ESTree node as Svelte's parser builds it: typed, and placed in the whole file's text. */
type EstreeNode = {type: string; start: number; end: number; [key: string]: unknown};

const isEstree = (value: unknown): value is EstreeNode => {
    const node = value as {type?: unknown; start?: unknown; end?: unknown} | null;
    return !!node && typeof node === 'object' && typeof node.type === 'string' && typeof node.start === 'number' && typeof node.end === 'number';
};

const ES_WRAPPERS = new Set(['ChainExpression', 'ParenthesizedExpression', 'TSAsExpression', 'TSSatisfiesExpression', 'TSNonNullExpression', 'TSTypeAssertion']);

/** The equality operators, each with whether it negates. */
const ES_EQUALITY: ReadonlyMap<string, boolean> = new Map([
    ['===', false],
    ['==', false],
    ['!==', true],
    ['!=', true],
]);

/** The expression under parentheses, a `?.` chain, `!`, `as`, `satisfies` and `<T>`. */
function esUnwrap(node: unknown): unknown {
    let inner = node;
    while (isEstree(inner) && ES_WRAPPERS.has(inner.type)) inner = inner.expression;
    return inner;
}

/** A string spelled out in the source: `'x'`, `"x"`, or a backtick literal without a substitution. */
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

/** Whether an expression holds the profile: a member named `profile` — `a.profile`, `a?.profile`, `a['profile']` — or a variable of that name. */
function esIsProfile(node: unknown): boolean {
    const inner = esUnwrap(node);
    if (!isEstree(inner)) return false;
    if (inner.type === 'Identifier') return inner.name === PROFILE_FIELD;
    if (inner.type !== 'MemberExpression') return false;
    const property = inner.property;
    if (inner.computed) return esStaticString(property) === PROFILE_FIELD;
    return isEstree(property) && property.type === 'Identifier' && property.name === PROFILE_FIELD;
}

/** The profile two operands compare the profile with, in either order — or null when they are not the profile and one of its values. */
function esCompared(left: unknown, right: unknown): Profile | null {
    if (esIsProfile(left)) return asProfile(esStaticString(right));
    if (esIsProfile(right)) return asProfile(esStaticString(left));
    return null;
}

/**
 * The comparisons of the profile, and the parse errors, of one component — found by Svelte's own parser, whose tree holds
 * the module script, the instance script and every expression of the markup, each node placed in the whole file's text:
 * one walk reads all three.
 */
function scanSvelte(file: string, text: string): Scan {
    const scan: Scan = {comparisons: [], parseErrors: []};
    let ast: unknown;
    try {
        ast = parseSvelte(text, {modern: true});
    } catch (error) {
        scan.parseErrors.push(`${file}  ${(error as Error).message}`);
        return scan;
    }
    const spelled = (node: EstreeNode): string => collapse(text.slice(node.start, node.end));
    const record = (offset: number, profile: Profile, negated: boolean, expr: string): void => {
        scan.comparisons.push({file, line: lineAt(text, offset), offset, profile, negated, expr});
    };
    const seen = new WeakSet<object>();
    const visit = (value: unknown): void => {
        if (!value || typeof value !== 'object' || seen.has(value)) return;
        seen.add(value);
        if (Array.isArray(value)) {
            for (const item of value) visit(item);
            return;
        }
        if (isEstree(value) && value.type === 'BinaryExpression') {
            const negated = ES_EQUALITY.get(String(value.operator));
            const profile = negated === undefined ? null : esCompared(value.left, value.right);
            if (profile) record(value.start, profile, negated === true, spelled(value));
        } else if (isEstree(value) && value.type === 'SwitchStatement') {
            const discriminant = value.discriminant;
            const clauses: unknown[] = Array.isArray(value.cases) ? value.cases : [];
            for (const clause of isEstree(discriminant) && esIsProfile(discriminant) ? clauses : []) {
                const test: unknown = isEstree(clause) ? clause.test : null;
                const profile = asProfile(esStaticString(test));
                if (profile && isEstree(clause) && isEstree(test) && isEstree(discriminant)) record(clause.start, profile, false, `switch (${spelled(discriminant)}) { case ${spelled(test)} }`);
            }
        }
        for (const [key, child] of Object.entries(value)) {
            if (key !== 'metadata' && key !== 'parent') visit(child);
        }
    };
    visit(ast);
    scan.comparisons.sort((a, b) => a.offset - b.offset);
    return scan;
}

/**
 * One scanner per kind of file, and the same one for a real file and a synthetic source: a positive control run on a
 * copy of this logic would test the copy.
 */
const scanSource = (file: string, text: string): Scan => (file.endsWith('.svelte') ? scanSvelte(file, text) : scanScript(file, text));

/** The verdict: `file:line  comparison  → helper` of every comparison outside `profile.ts`, the one place allowed to make it. */
function offenders(comparisons: readonly Comparison[]): string[] {
    return comparisons.filter((comparison) => comparison.file !== PROFILE_HELPERS).map((comparison) => `${comparison.file}:${comparison.line}  ${clip(comparison.expr)}  → ${comparison.negated ? '!' : ''}${HELPERS[comparison.profile]}`);
}

/** `line  comparison` of every comparison a synthetic source makes. */
function caught(file: string, text: string): string[] {
    const scan = scanSource(file, text);
    // A control that does not parse proves nothing: it would be clean because it was never read.
    expect(scan.parseErrors).toEqual([]);
    return scan.comparisons.map((comparison) => `${comparison.line}  ${comparison.expr}`);
}

// ---------------------------------------------------------------------------
// Synthetic sources for the controls
// ---------------------------------------------------------------------------

/** Every spelling the gate must flag, one statement per line from line 1 — the last two spread over several lines. */
const COMPARISONS = [
    "const a = x.config.profile === 'selfhosted';",
    "const b = 'managed' !== cfg.profile;",
    'const c = x.config.profile == "managed";',
    'const d = "selfhosted" != instanceConfig.config.profile;',
    "const e = instanceConfig.loaded && instanceConfig.config.profile === 'selfhosted';",
    "const f = x?.config?.profile === 'managed';",
    "const g = x.config['profile'] !== 'selfhosted';",
    'const h = cfg.profile === `managed`;',
    "const i = (cfg.profile as string) === 'managed';",
    "const j = cfg.profile! === ('selfhosted');",
    "const k = ({profile}: InstanceConfig): boolean => profile === 'managed';",
    'if (',
    '    instanceConfig.config.profile ===',
    "    'selfhosted'",
    ') show();',
    'switch (instanceConfig.config.profile) {',
    "    case 'managed':",
    '        break;',
    '}',
];

/** The comparisons COMPARISONS makes, each with the row it starts on (0-based): one per statement, the `switch` at its `case`. */
const COMPARED: ReadonlyArray<readonly [number, string]> = [
    [0, "x.config.profile === 'selfhosted'"],
    [1, "'managed' !== cfg.profile"],
    [2, 'x.config.profile == "managed"'],
    [3, '"selfhosted" != instanceConfig.config.profile'],
    [4, "instanceConfig.config.profile === 'selfhosted'"],
    [5, "x?.config?.profile === 'managed'"],
    [6, "x.config['profile'] !== 'selfhosted'"],
    [7, 'cfg.profile === `managed`'],
    [8, "(cfg.profile as string) === 'managed'"],
    [9, "cfg.profile! === ('selfhosted')"],
    [10, "profile === 'managed'"],
    [12, "instanceConfig.config.profile === 'selfhosted'"],
    [16, "switch (instanceConfig.config.profile) { case 'managed' }"],
];

/** What `caught` reports for COMPARISONS laid out from line `first`. */
const comparisonsFrom = (first: number): string[] => COMPARED.map(([row, expr]) => `${first + row}  ${expr}`);

/** The profile and its values written as anything but a comparison of the two: none of these may be flagged. */
const LOOK_ALIKES = [
    "export const DEFAULT_INSTANCE_CONFIG: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};",
    'const report = buildSearchReport({query, profile: instanceConfig.config.profile, language});',
    'lines.push(`LibreFolio ${input.appVersion}, ${input.profile}, language ${input.language}`);',
    "instanceConfig.config.profile; // 'selfhosted' | 'managed'",
    '/**',
    ' * Usage:',
    " *   instanceConfig.config.profile; // 'selfhosted' | 'managed'",
    " *   if (instanceConfig.loaded && instanceConfig.config.profile === 'managed') …",
    ' */',
    "// return instanceConfig.loaded && instanceConfig.config.profile === 'selfhosted';",
    'const quoted = "instanceConfig.config.profile === \'managed\'";',
    "const label = $_('settings.profile.managed');",
    "type Narrowed = {profile: 'selfhosted' | 'managed'};",
    "type IsManaged<T> = T extends {profile: 'managed'} ? true : false;",
    "cfg.profile = 'managed';",
    "const mode = accounts.registration_mode === 'managed';",
    "const kind = cfg.profile.kind === 'managed';",
    "const many = cfg.profiles === 'managed';",
    "const first = profile === 'first_with_range';",
    'const same = a.profile === b.profile;',
    'const confirmed = selfHostedConfirmed() || !managedConfirmed();',
];

/** A source wrapped in a component's instance script, one row per line: its first row lands on line 2. */
const inScript = (rows: readonly string[]): string => ['<script lang="ts">', ...rows.map((row) => `    ${row}`), '</script>'].join('\n');

/** `profile.ts` as the approved design writes it: the one place allowed to make both comparisons of the rule. */
const APPROVED_HELPERS = [
    "import {instanceConfig} from '$lib/features/instance/instanceConfig.svelte';",
    '',
    'export function selfHostedConfirmed(): boolean {',
    "    return instanceConfig.loaded && instanceConfig.config.profile === 'selfhosted';",
    '}',
    '',
    'export function managedConfirmed(): boolean {',
    "    return instanceConfig.loaded && instanceConfig.config.profile === 'managed';",
    '}',
].join('\n');

// ---------------------------------------------------------------------------
// The gate
// ---------------------------------------------------------------------------

describe('The instance profile is compared in profile.ts only (H-nit gate)', () => {
    const files = sourceFiles();
    const texts = new Map(files.map((file) => [file, readFileSync(join(FRONTEND, file), 'utf8')] as const));
    const scans = files.map((file) => scanSource(file, texts.get(file) ?? ''));
    const comparisons = scans.flatMap((scan) => scan.comparisons);
    const parseErrors = scans.flatMap((scan) => scan.parseErrors);

    describe('the rule', () => {
        it('parses every source it reads', () => {
            expect(parseErrors, ['', 'These sources could not be parsed, so the gate cannot vouch for them:', '', ...parseErrors, ''].join('\n  ')).toEqual([]);
        });

        it('compares the profile with its values nowhere but profile.ts', () => {
            const found = offenders(comparisons);
            const rule = [
                `The instance profile is compared in one place: ${PROFILE_HELPERS}.`,
                "Until the server answers, and whenever it cannot, the store holds DEFAULT_INSTANCE_CONFIG, which says profile: 'selfhosted': a comparison alone is already true before the answer, while the request is in flight and after a failed one.",
                "What holds is «the server confirmed it» — instanceConfig.loaded && profile === '…' — and it has one home.",
                `Use selfHostedConfirmed() / managedConfirmed() from ${PROFILE_SPECIFIER} instead (or add to profile.ts the helper the site needs).`,
            ];
            expect(found, ['', ...rule, `${found.length} comparison(s) outside it:`, '', ...found, ''].join('\n  ')).toEqual([]);
        });
    });

    describe('positive controls', () => {
        it('flags a comparison of the profile with either value, in every spelling and either order', () => {
            // The positive control of the verdict: "no comparison outside profile.ts" is also what a scanner that finds none would report.
            expect(caught('src/lib/a.ts', COMPARISONS.join('\n'))).toEqual(comparisonsFrom(1));
        });

        it('flags the same comparisons in a component: module script, instance script, every markup expression', () => {
            expect(caught('src/lib/A.svelte', inScript(COMPARISONS))).toEqual(comparisonsFrom(2));
            const component = [
                '<script module lang="ts">',
                "    export const isManaged = (cfg: InstanceConfig): boolean => cfg.profile === 'managed';",
                '</script>',
                '',
                '<script lang="ts">',
                "    let githubFallback = $derived(instanceConfig.loaded && instanceConfig.config.profile === 'selfhosted');",
                "    const DEFAULTS = {profile: 'selfhosted'};",
                "    // instanceConfig.config.profile === 'managed'",
                '</script>',
                '',
                "<!-- {#if instanceConfig.config.profile === 'managed'} -->",
                "{#if instanceConfig.loaded && instanceConfig.config.profile === 'managed'}<p>ask</p>{/if}",
                '{#if email}<p>a</p>{:else if (instanceConfig.loaded && instanceConfig.config.profile === "managed") || failed}<p>b</p>{/if}',
                "<button class:hidden={cfg.profile !== 'selfhosted'} title=\"profile === 'managed'\" data-profile={cfg.profile}>{report.profile}</button>",
                '<p>{`${input.profile}`} {DEFAULTS.profile}</p>',
            ].join('\n');
            expect(caught('src/lib/A.svelte', component)).toEqual(["2  cfg.profile === 'managed'", "6  instanceConfig.config.profile === 'selfhosted'", "12  instanceConfig.config.profile === 'managed'", '13  instanceConfig.config.profile === "managed"', "14  cfg.profile !== 'selfhosted'"]);
        });

        it('takes nothing else for a comparison: an object literal, a value, a template, a comment, a string, a type, another field or value', () => {
            expect(caught('src/lib/a.ts', LOOK_ALIKES.join('\n'))).toEqual([]);
            expect(caught('src/lib/A.svelte', inScript(LOOK_ALIKES))).toEqual([]);
        });

        it('spares profile.ts as approved, flags a comparison in any other file, and names the helper that replaces it', () => {
            // The positive control of the verdict itself: once the helpers are in, the real tree compares nowhere but
            // profile.ts, so the verdict would pass as well with a filter that drops everything. The comparisons come from
            // the scanner; a file named like the helpers' is no exemption. And profile.ts as the approved design writes it
            // shows the scanner both comparisons: what the live control below asks of the real file.
            const comparisonsIn = (file: string, source: string): Comparison[] => scanSource(file, source).comparisons;
            const helpers = comparisonsIn(PROFILE_HELPERS, APPROVED_HELPERS);
            expect(helpers.map((comparison) => `${comparison.line}  ${comparison.profile}`)).toEqual(['4  selfhosted', '8  managed']);
            const lookAlike = 'src/lib/features/instance/profile.svelte.ts';
            const synthetic = [
                ...helpers,
                ...comparisonsIn(DONATIONS, "export function donationsVisible(): boolean {\n    return instanceConfig.loaded && instanceConfig.config.profile === 'selfhosted';\n}"),
                ...comparisonsIn(UPDATE_CHECK, "export function probe(): null | void {\n    if (!instanceConfig.loaded || instanceConfig.config.profile !== 'selfhosted') return null;\n}"),
                ...comparisonsIn(FORGOT_PASSWORD, "{#if instanceConfig.loaded && instanceConfig.config.profile === 'managed'}<p>ask</p>{/if}"),
                ...comparisonsIn(lookAlike, "export const managed = (): boolean => instanceConfig.config.profile === 'managed';"),
            ];
            expect(
                synthetic.map((comparison) => comparison.file),
                'a verdict on comparisons the scanner never produced would prove nothing',
            ).toEqual([PROFILE_HELPERS, PROFILE_HELPERS, DONATIONS, UPDATE_CHECK, FORGOT_PASSWORD, lookAlike]);
            expect(offenders(synthetic)).toEqual([
                "src/lib/features/support/donations.svelte.ts:2  instanceConfig.config.profile === 'selfhosted'  → selfHostedConfirmed()",
                "src/lib/features/update-check/updateCheck.ts:2  instanceConfig.config.profile !== 'selfhosted'  → !selfHostedConfirmed()",
                "src/lib/features/auth/ForgotPasswordCard.svelte:1  instanceConfig.config.profile === 'managed'  → managedConfirmed()",
                "src/lib/features/instance/profile.svelte.ts:1  instanceConfig.config.profile === 'managed'  → managedConfirmed()",
            ]);
        });

        it('reads every product source, components and modules alike, and no test, mock or generated client', () => {
            const read = [PROFILE_HELPERS, STORE, ...CALLERS, 'src/routes/(app)/+layout.svelte', 'src/app.d.ts'];
            const skipped = [
                'src/instanceProfile.gate.test.ts',
                'src/lib/features/instance/profile.test.ts',
                'src/lib/features/instance/instanceConfig.test.ts',
                'src/lib/features/instance/profile.spec.ts',
                'src/__tests__/runes.svelte.ts',
                'src/__tests__/harness/AppLayoutGateHarness.svelte',
                'src/__mocks__/$app/environment.ts',
                'src/lib/api/generated.ts',
                'src/lib/api/generated-tools.ts',
                'src/lib/api/tool-contract-map.generated.ts',
                'src/lib/dev/designer-lab/color.js',
                'src/app.css',
            ];
            expect(read.filter((path) => !isScanned(path))).toEqual([]);
            expect(skipped.filter((path) => isScanned(path))).toEqual([]);
            // 400 components and 427 modules when this gate was written: a walk that reaches the wrong directory, or reads
            // one kind of file only, finds far fewer.
            expect(files.filter((file) => file.endsWith('.svelte')).length).toBeGreaterThan(300);
            expect(files.filter((file) => file.endsWith('.ts')).length).toBeGreaterThan(300);
            expect(files).toEqual(expect.arrayContaining([STORE, ...CALLERS]));
            expect(files.filter((file) => file.startsWith('src/lib/api/generated'))).toEqual([]);
            // Absence behind a presence barrier: the store is read and spells the profile with a value, which is no comparison.
            expect(texts.get(STORE)).toMatch(/\bprofile:\s*'selfhosted'/);
            expect(comparisons.filter((comparison) => comparison.file === STORE).map((comparison) => `${comparison.line}  ${comparison.expr}`)).toEqual([]);
        });

        it('finds a comparison with each profile in profile.ts, the one place allowed to make them', () => {
            // Non-vacuity of the verdict once the helpers are in: the real tree then compares nowhere else, and a scanner that
            // saw nothing at all would pass it the same. profile.ts must show the scanner both comparisons of the rule.
            expect(files.includes(PROFILE_HELPERS), `${PROFILE_HELPERS} not found: the home of selfHostedConfirmed() and managedConfirmed() (${PROFILE_SPECIFIER}), and the positive control of this gate`).toBe(true);
            const compared = [...new Set(comparisons.filter((comparison) => comparison.file === PROFILE_HELPERS).map((comparison) => comparison.profile))].sort();
            const why = `${PROFILE_HELPERS} compares the profile with each of its values (loaded && profile === '…'), and the scanner must see it: if the helpers now compare another way, teach the gate the new form — or it no longer sees the comparisons it forbids`;
            expect(compared, why).toEqual([...PROFILES].sort());
        });
    });
});
