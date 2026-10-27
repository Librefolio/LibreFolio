/**
 * Gate: the frontend computes no financial quantity, except the interactive measures it declares (Y12a, step 2).
 *
 * ## What this protects
 *
 * `backend/app/services/financial_math/` is the one home of LibreFolio's financial calculations (developer decision of
 * 2026-10-11, decision 10). The frontend shows the fields the backend computes — cost, P&L, capital, NAV, returns, FX
 * value, yields — and computes none of them. The only exceptions are the interactive measures, which the user shapes on
 * a chart or a table and so have no backend field to read:
 *   - the measuring tool (R18, `MeasureSignal.ts`): Δ, Δ% and annualized between the two points the user picks;
 *   - the what-if curves of the synthetic benchmarks (R19, `CompoundSignal.ts`, `LinearSignal.ts`, `SineSignal.ts`),
 *     drawn from the parameters the user sets;
 *   - the lot aggregates of developer decision D-MF6(b) (`plan-phase01FinancialMath.prompt.md:381`), over the lots the
 *     user chooses: the footer of the lots table — a table, not a chart — over the rows the user selects, else those the
 *     filters leave visible (`unifiedLotsTableHelpers.ts`, fed by `DataTable.svelte`); the aggregate of the lots
 *     selected in the comparison chart (`lotComparisonChartHelpers.ts`); and the WAC chart's percentage view, its value
 *     series rebased on the first known value (`lotWacPriceChartHelpers.ts`);
 *   - the return chart of the positions the user ticks (Y5-2, #48, `positionsSeries.ts`): the backend's fraction in
 *     «base 100» (a change of unit), and the Dashboard's own history moved to the left edge of the user's window. No
 *     new calculation: a number the backend computed, shifted or re-expressed for the chart.
 *   - the trade amount of the transaction form (W5-9, #47, `txTradeAmount.ts`): the amount from the unit price the user
 *     types, or the unit price from the amount, one product or one quotient on exact decimals (developer decision of
 *     25/10/2026: small sums and products are the frontend's own, a route for a multiplication is not).
 *
 * Each exception must be declared where it lives. The documentation named the four files while the code declared none
 * of them (plan 43, `plan-phase00FinancialMathHome.prompt.md:1494`): this gate was written red against that state, and
 * keeps the declarations and the code in step from then on. The three lot modules joined the list the same way (Y12b,
 * P5): red while they computed their aggregates undeclared. (C) cannot find them — a sum, a weighted average or a
 * rebase raises nothing to 365 — so the list alone holds them to their declaration.
 *
 * The rule lives in `.github/instructions/frontend.instructions.md` («Financial numbers»),
 * `.github/instructions/financial-math.instructions.md` (rule 6) and `mkdocs_src/docs/developer/backend/financial_math.md`
 * (rule 6, which names every declared file).
 *
 * ## The rule, as this file checks it
 *
 * It reads the product sources under `src`: every `.ts` and `.svelte` file but the tests (`*.test.ts`, `*.spec.ts`),
 * anything under `__tests__/` or `__mocks__/`, and the generated API clients (`src/lib/api/generated*.ts`,
 * `*.generated.ts`).
 *
 * (A) Declared → marked. Every file of DECLARED_EXCEPTIONS exists and declares its measure in its leading JSDoc block —
 *     the first `/**` comment of the module, with nothing but whitespace and comments before it. A line of that block
 *     opens with the tag `@financial-math-exception`, followed by the description of the measure: at least 20
 *     characters, up to the next block tag or the end of the block. A tag anywhere else — in a later comment, after
 *     code, mid-line — declares nothing.
 * (B) Marked → declared. No other source contains the string `@financial-math-exception`, in a comment, a string or
 *     code. The tag is not self-service: an exception is added on purpose, by extending DECLARED_EXCEPTIONS.
 * (C) Annualization by exponent only where declared. A power whose exponent holds the number 365 — `Math.pow(base, e)`,
 *     `base ** e`, `x **= e` — appears only in the declared files whose entry says `annualizes: true`: raising a growth
 *     factor to 365/days, or a daily one to 365, annualizes a return, and returns are the backend's
 *     (`financial_math/returns.py`). A declaration is no licence to annualize (Y-29): an exception that annualizes says
 *     so on purpose — today `MeasureSignal` (the ruler's Δ%/yr) and `CompoundSignal` (the compound curve's daily factor)
 *     — and a declared file that does not stays under (C), as the lot modules do: they sum, average and rebase. The
 *     powers are found on the syntax tree — TypeScript's for a module, Svelte's for a component (module script, instance
 *     script and every expression of the markup) — so a comment, a string or a KaTeX formula (`MeasurePanel`'s
 *     `^{\frac{365}{d}}`) is never taken for one, and a base never lends its commas or its 365 to the exponent. 365
 *     counts as a number of its own: `365 / d`, `1 / 365` and `365.25` hold it, `3650` does not.
 * (D) Positive controls. "Nothing undeclared" is also what a scanner that reads nothing would report. Each detector runs
 *     on synthetic sources it must flag and on look-alikes it must not; (C)'s verdict flags a synthetic power in a file
 *     that does not annualize, a declared lot module included, and spares one in each file that does; the walk must
 *     reach both kinds of file; and the scan of the real tree must find the daily factor `CompoundSignal` computes today
 *     (`Math.pow(1 + rate, 1 / 365)`), a power in each file declared to annualize — `MeasureSignal`'s Δ%/yr
 *     (`Math.pow(growth, 365 / days)`) too — and none in the files whose 365 is no exponent (`CellDateRange`'s
 *     `Math.floor(total / 365)`, `ScheduledInvestmentEditor`'s `'ACT/365'`, `LinearSignal`'s `days / 365`). A file
 *     declared to annualize that stops raising to 365 keeps its entry, with `annualizes: false`: it stays declared, and
 *     falls back under (C).
 *
 * ## Adding an exception
 *
 * Only an interactive measure qualifies: a value the user shapes on a chart or a table (the points picked, the
 * parameters set, the lots chosen), which no backend field can hold. Anything else shows the backend's field. To add
 * one, in the same change: the tag and its description in the module's leading JSDoc block, the file in
 * DECLARED_EXCEPTIONS below, and the file named in rule 6 of `financial_math.md`. A tag without an entry fails (B); an
 * entry without a tag fails (A), and so does an entry whose file is gone. Every entry also says whether its measure
 * annualizes (`annualizes`, required): a declaration lets a file compute its measure, not annualize it. An exception
 * that annualizes says so on purpose, `annualizes: true`, and (D) then wants the scan to find its power; a declared file
 * that does not, `annualizes: false`, stays under (C) like any other source. The form is defined for modules: a
 * component (`.svelte`) has no leading JSDoc block, so a measure computed in a component moves into a module — or the
 * form for components is decided first, and taught to this gate.
 *
 * ## Completeness, stated honestly
 *
 * (C) sees the number 365 spelled inside the exponent of `Math.pow` or `**`. It does not follow a value:
 * `const YEAR = 365; Math.pow(1 + r, YEAR / d)`, `const {pow} = Math`, a `.pow()` of another object (a decimal library —
 * none in the frontend today), `Math.exp(Math.log(1 + r) * 365 / d)` and an annualization that is not a power
 * (`r * 365 / d`) all pass; so does every financial quantity computed without annualizing — a P&L, a weight, a rebase.
 * The forms are a floor: when the rule grows, grow them with it. `annualizes: true` is granted to a file, not to a power:
 * a second annualization in `MeasureSignal` or `CompoundSignal` passes. (A) checks that a description is there and long
 * enough, never what it says: a declaration is a human decision recorded once, which a reviewer re-checks when the file
 * changes. Only `.ts` and `.svelte` are read: `src/lib/dev/designer-lab/color.js`, the one `.js` file of `src`, is not.
 *
 * Registered in `chart-safety-unit` (`scripts/test_runner/_frontend_portfolio.py`).
 */

import {describe, expect, it} from 'vitest';
import {existsSync, readdirSync, readFileSync} from 'node:fs';
import {dirname, join, relative, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';
import {parse as parseSvelte} from 'svelte/compiler';

/** `frontend/`: every path is read, and reported, relative to it — the directory the runner starts vitest from. */
const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(FRONTEND, 'src');

/** The declaration's tag. */
const TAG = '@financial-math-exception';

const MEASURE = 'src/lib/charts/signals/MeasureSignal.ts';
const COMPOUND = 'src/lib/charts/signals/CompoundSignal.ts';
const LINEAR = 'src/lib/charts/signals/LinearSignal.ts';
const SINE = 'src/lib/charts/signals/SineSignal.ts';
const LOTS_TABLE = 'src/lib/features/brokers/lots/unifiedLotsTableHelpers.ts';
const LOT_COMPARISON = 'src/lib/features/brokers/lots/lotComparisonChartHelpers.ts';
const LOT_WAC = 'src/lib/features/brokers/lots/lotWacPriceChartHelpers.ts';
const POSITIONS_SERIES = 'src/lib/features/dashboard/positionsSeries.ts';
const TRADE_AMOUNT = 'src/lib/features/transactions/form/txTradeAmount.ts';

interface DeclaredException {
    /** Relative to `frontend/`. */
    file: string;
    /**
     * Whether the measure annualizes by exponent — a change compounded to a year, an annual rate taken to its daily
     * factor — and so may raise to an exponent holding 365 (rule (C)). Required: an exception that annualizes says so on
     * purpose, and a declared file that does not stays under (C) (Y-29).
     */
    annualizes: boolean;
    /** The interactive measure the file computes, as rule 6 of `financial_math.md` counts it. */
    measure: string;
}

/**
 * The files allowed to compute a financial quantity in the browser, one interactive measure each. Extended deliberately,
 * in the change that writes the tag into the file: see «Adding an exception» above.
 */
const DECLARED_EXCEPTIONS: readonly DeclaredException[] = [
    {file: MEASURE, annualizes: true, measure: 'R18, the measuring tool: Δ, Δ% and annualized between the two points the user picks'},
    {file: COMPOUND, annualizes: true, measure: 'R19, a what-if curve: compound growth at the annual rate the user sets'},
    {file: LINEAR, annualizes: false, measure: 'R19, a what-if curve: linear growth at the annual rate the user sets'},
    {file: SINE, annualizes: false, measure: 'R19, a what-if curve: a sine wave of the amplitude and period the user sets'},
    {file: LOTS_TABLE, annualizes: false, measure: 'D-MF6(b), the lots table footer: sums, weighted averages and returns over the rows the user selects, else those left visible'},
    {file: LOT_COMPARISON, annualizes: false, measure: 'D-MF6(b), the lot comparison aggregate: value and return of the lots the user selects'},
    {file: LOT_WAC, annualizes: false, measure: "D-MF6(b), the WAC chart's percentage view: the value series rebased on its first known value"},
    {file: POSITIONS_SERIES, annualizes: false, measure: "Y5-2, the positions return chart: the backend's fraction in base 100, and the Dashboard history moved to the left edge of the window the user picks"},
    {file: TRADE_AMOUNT, annualizes: false, measure: "W5-9 (#47), the transaction form: the trade's amount from the unit price the user types, or the unit price from the amount — one product or one quotient, exact decimals"},
];

const DECLARED_FILES: ReadonlySet<string> = new Set(DECLARED_EXCEPTIONS.map((entry) => entry.file));

/** The files (C) lets raise to an exponent holding 365: those whose entry says the measure annualizes, on purpose. */
const ANNUALIZING_FILES: ReadonlySet<string> = new Set(DECLARED_EXCEPTIONS.filter((entry) => entry.annualizes).map((entry) => entry.file));

/** Real files whose 365 is no exponent — a divisor, a remainder, day-count labels — read by the live control of (D). */
const CELL_DATE_RANGE = 'src/lib/components/assets/CellDateRange.svelte';
const SCHEDULED_INVESTMENT = 'src/lib/components/assets/ScheduledInvestmentEditor.svelte';

/** The shortest description (A) accepts after the tag: a word or two is a placeholder, not a declaration. */
const MIN_DESCRIPTION = 20;

/** 365 as a number of its own: `365 / d`, `1 / 365`, `365.25`, `DAYS_365` — not `3650`, not `1365`. No `g` flag, so `test` keeps no state. */
const YEAR_DAYS = /(?<!\d)365(?!\d)/;

const collapse = (s: string): string => s.trim().replace(/\s+/g, ' ');
const clip = (s: string, max = 160): string => (s.length > max ? `${s.slice(0, max - 1)}…` : s);
const lineAt = (text: string, offset: number): number => text.slice(0, offset).split('\n').length;

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
// (A) The declaration: a block tag of the leading JSDoc block
// ---------------------------------------------------------------------------

/** The tag opening a row of a JSDoc block, and the rest of the row. `(?![\w-])`: `@financial-math-exceptions` is another tag. */
const TAG_ROW = /^@financial-math-exception(?![\w-])(.*)$/;
/** Any block tag opening a row: where the description of the one before it ends. */
const BLOCK_TAG_ROW = /^@[A-Za-z]/;

interface LeadingBlock {
    /** 1-based line of the opening. */
    line: number;
    /** 1-based line of the closing. */
    endLine: number;
    /** One row per line, from the opening's to the closing's: delimiters, the leading `*` and the outer spaces removed. */
    rows: string[];
}

/**
 * The leading JSDoc block of a module: the first comment that opens with two stars, with nothing but whitespace and
 * comments before it. Null when code comes first, or when that comment never closes.
 */
function leadingBlock(text: string): LeadingBlock | null {
    let i = text.charCodeAt(0) === 0xfeff ? 1 : 0;
    for (;;) {
        while (i < text.length && /\s/.test(text[i])) i++;
        if (text.startsWith('//', i)) {
            const newline = text.indexOf('\n', i);
            if (newline < 0) return null;
            i = newline + 1;
        } else if (text.startsWith('/*', i)) {
            const close = text.indexOf('*/', i + 2);
            if (close < 0) return null;
            // An empty `/**/` is a plain comment, not a JSDoc block.
            if (text.startsWith('/**', i) && !text.startsWith('/**/', i)) {
                const rows = text.slice(i + 3, close).split('\n');
                return {line: lineAt(text, i), endLine: lineAt(text, close), rows: rows.map((row) => row.replace(/^\s*\*?/, '').trim())};
            }
            i = close + 2;
        } else {
            return null;
        }
    }
}

interface Declaration {
    block: LeadingBlock | null;
    /** 1-based line of the tag in the leading block, or null when the block holds none. */
    tagLine: number | null;
    /** What follows the tag, up to the next block tag or the end of the block, whitespace collapsed. */
    description: string;
}

/** A module's declaration, read from its leading JSDoc block and nowhere else. */
function readDeclaration(text: string): Declaration {
    const block = leadingBlock(text);
    if (!block) return {block, tagLine: null, description: ''};
    for (let at = 0; at < block.rows.length; at++) {
        const tag = TAG_ROW.exec(block.rows[at]);
        if (!tag) continue;
        const description = [tag[1]];
        for (const row of block.rows.slice(at + 1)) {
            if (BLOCK_TAG_ROW.test(row)) break;
            description.push(row);
        }
        return {block, tagLine: block.line + at, description: collapse(description.join(' '))};
    }
    return {block, tagLine: null, description: ''};
}

/** The 1-based lines of a source that contain the tag, whatever surrounds it: a comment, a string, code. */
const tagLines = (text: string): number[] => text.split('\n').flatMap((row, i) => (row.includes(TAG) ? [i + 1] : []));

/** Why a listed file does not declare its measure, or null when it does. `text` is null when the file does not exist. */
function declarationProblem(file: string, text: string | null): string | null {
    if (text === null) return `${file} is listed in DECLARED_EXCEPTIONS but does not exist: delete the entry, or restore the file.`;
    if (!file.endsWith('.ts')) return `${file} is not a .ts module: the declaration is a block tag of a module's leading JSDoc block, which a component does not have — move the measure into a module, or decide how a component declares it and teach this gate.`;
    const {block, tagLine, description} = readDeclaration(text);
    if (tagLine !== null) {
        if (description.length >= MIN_DESCRIPTION) return null;
        return `${file}:${tagLine}  ${TAG} is followed by «${description}»: describe the measure in ${MIN_DESCRIPTION} characters at least — what it computes in the browser, and why no backend field serves it.`;
    }
    const where = tagLines(text).map((line) => (block && line >= block.line && line <= block.endLine ? `line ${line} (in the leading block, but not as a tag opening its line)` : `line ${line} (outside the leading block)`));
    const elsewhere = where.length > 0 ? ` The string appears at ${where.join(', ')}: only a block tag of the leading block declares the file.` : '';
    if (!block) return `${file} opens with code: it has no leading JSDoc block to carry ${TAG}.${elsewhere}`;
    return `${file}: its leading JSDoc block (lines ${block.line}-${block.endLine}) carries no ${TAG} block tag.${elsewhere}`;
}

// ---------------------------------------------------------------------------
// (B) Every mention of the tag outside the declared files
// ---------------------------------------------------------------------------

/** `file:line` of every mention of the tag in a source the list does not declare. */
function undeclaredTags(sources: Iterable<readonly [string, string]>, declared: ReadonlySet<string>): string[] {
    const found: string[] = [];
    for (const [file, text] of sources) {
        if (declared.has(file)) continue;
        for (const line of tagLines(text)) found.push(`${file}:${line}`);
    }
    return found;
}

// ---------------------------------------------------------------------------
// (C) Powers whose exponent holds 365, found on the syntax tree
// ---------------------------------------------------------------------------

interface Hit {
    file: string;
    line: number;
    offset: number;
    /** The exponent's source, outer parentheses dropped, whitespace collapsed. */
    exponent: string;
    /** The whole power's source, whitespace collapsed: what the verdict prints. */
    expr: string;
}

interface Scan {
    hits: Hit[];
    parseErrors: string[];
}

// --- `.ts`: the TypeScript tree --------------------------------------------------------------------

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

/** The member an access names: `a.name`, `a?.name`, `a['name']`. */
function tsMemberName(node: ts.Node): string | null {
    if (ts.isPropertyAccessExpression(node)) return node.name.text;
    if (ts.isElementAccessExpression(node)) return tsStaticString(node.argumentExpression);
    return null;
}

/** `Math` itself, or a member named `Math`: `globalThis.Math`, `window['Math']`. */
function tsIsMath(node: ts.Expression): boolean {
    const inner = tsUnwrap(node);
    return ts.isIdentifier(inner) ? inner.text === 'Math' : tsMemberName(inner) === 'Math';
}

/** The exponent of the power one node spells — `Math.pow(base, e)`, `base ** e`, `x **= e` — or null. */
function tsExponent(node: ts.Node): ts.Expression | null {
    if (ts.isCallExpression(node)) {
        const callee = tsUnwrap(node.expression);
        const isPow = (ts.isPropertyAccessExpression(callee) || ts.isElementAccessExpression(callee)) && tsMemberName(callee) === 'pow' && tsIsMath(callee.expression);
        return isPow && node.arguments.length > 1 ? node.arguments[1] : null;
    }
    if (ts.isBinaryExpression(node)) {
        const operator = node.operatorToken.kind;
        if (operator === ts.SyntaxKind.AsteriskAsteriskToken || operator === ts.SyntaxKind.AsteriskAsteriskEqualsToken) return node.right;
    }
    return null;
}

/** The powers whose exponent holds 365, and the parse errors, of one module. */
function scanScript(file: string, text: string): Scan {
    const scan: Scan = {hits: [], parseErrors: []};
    const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
    const lineOf = (offset: number): number => sf.getLineAndCharacterOfPosition(offset).line + 1;
    const diagnostics = (sf as unknown as {parseDiagnostics?: readonly ts.Diagnostic[]}).parseDiagnostics ?? [];
    for (const diagnostic of diagnostics) scan.parseErrors.push(`${file}:${lineOf(diagnostic.start ?? 0)}  ${ts.flattenDiagnosticMessageText(diagnostic.messageText, ' ')}`);
    const visit = (node: ts.Node): void => {
        let exponent = tsExponent(node);
        while (exponent && ts.isParenthesizedExpression(exponent)) exponent = exponent.expression;
        const spelled = exponent ? text.slice(exponent.getStart(sf), exponent.end) : '';
        if (YEAR_DAYS.test(spelled)) {
            const offset = node.getStart(sf);
            scan.hits.push({file, line: lineOf(offset), offset, exponent: collapse(spelled), expr: collapse(text.slice(offset, node.end))});
        }
        ts.forEachChild(node, visit);
    };
    visit(sf);
    scan.hits.sort((a, b) => a.offset - b.offset);
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

/** The member a member expression names: `a.name`, `a?.name`, `a['name']`. */
function esMemberName(node: unknown): string | null {
    if (!isEstree(node) || node.type !== 'MemberExpression') return null;
    return node.computed ? esStaticString(node.property) : esIdentifierName(node.property);
}

/** `Math` itself, or a member named `Math`: `globalThis.Math`, `window['Math']`. */
function esIsMath(node: unknown): boolean {
    const inner = esUnwrap(node);
    return esIdentifierName(inner) === 'Math' || esMemberName(inner) === 'Math';
}

/** The exponent of the power one node spells — the three spellings `tsExponent` reads — or null. */
function esExponent(node: EstreeNode): EstreeNode | null {
    if (node.type === 'CallExpression') {
        const callee = esUnwrap(node.callee);
        const exponent: unknown = Array.isArray(node.arguments) ? node.arguments[1] : undefined;
        return isEstree(callee) && esMemberName(callee) === 'pow' && esIsMath(callee.object) && isEstree(exponent) ? exponent : null;
    }
    const right = node.right;
    if ((node.type === 'BinaryExpression' && node.operator === '**') || (node.type === 'AssignmentExpression' && node.operator === '**=')) return isEstree(right) ? right : null;
    return null;
}

/**
 * The powers whose exponent holds 365, and the parse errors, of one component — found by Svelte's own parser, whose
 * tree holds the module script, the instance script and every expression of the markup, each node placed in the whole
 * file's text: one walk reads all three.
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
    const seen = new WeakSet<object>();
    const visit = (value: unknown): void => {
        if (!value || typeof value !== 'object' || seen.has(value)) return;
        seen.add(value);
        if (Array.isArray(value)) {
            for (const item of value) visit(item);
            return;
        }
        if (isEstree(value)) {
            const exponent = esExponent(value);
            const spelled = exponent ? text.slice(exponent.start, exponent.end) : '';
            if (YEAR_DAYS.test(spelled)) scan.hits.push({file, line: lineAt(text, value.start), offset: value.start, exponent: collapse(spelled), expr: collapse(text.slice(value.start, value.end))});
        }
        for (const [key, child] of Object.entries(value)) {
            if (key !== 'metadata' && key !== 'parent') visit(child);
        }
    };
    visit(ast);
    scan.hits.sort((a, b) => a.offset - b.offset);
    return scan;
}

/**
 * One scanner per kind of file, and the same one for a real file and a synthetic source: a positive control run on a
 * copy of this logic would test the copy.
 */
const scanSource = (file: string, text: string): Scan => (file.endsWith('.svelte') ? scanSvelte(file, text) : scanScript(file, text));

/** (C)'s verdict: `file:line  power` of every power whose exponent holds 365, in a file not allowed to raise to one. */
function annualizationOffenders(hits: readonly Hit[], allowedFiles: ReadonlySet<string>): string[] {
    return hits.filter((hit) => !allowedFiles.has(hit.file)).map((hit) => `${hit.file}:${hit.line}  ${clip(hit.expr)}`);
}

/** `line  exponent` of every power a synthetic source raises to an exponent holding 365. */
function caught(file: string, text: string): string[] {
    const scan = scanSource(file, text);
    // A control that does not parse proves nothing: it would be clean because it was never read.
    expect(scan.parseErrors).toEqual([]);
    return scan.hits.map((hit) => `${hit.line}  ${hit.exponent}`);
}

// ---------------------------------------------------------------------------
// Synthetic sources for the controls of (D)
// ---------------------------------------------------------------------------

/** Every spelling (C) must flag, one statement per line from line 1 — the last one spread over four lines. */
const POWERS = [
    'const a = Math.pow(1 + r, 365 / d);',
    'const b = (1 + r) ** (365 / d);',
    'const c = days > 0 ? (Math.pow(1 + deltaPct / 100, 365 / days) - 1) * 100 : 0;',
    'const e = Math.pow(1 + rate, 1 / 365);',
    'const f = Math.pow(g(a, (b + c)) * (1 + h(i, j)), 365 / d);',
    'const k = Math.pow((1 + r), (365.25 / d));',
    "const m = Math['pow'](1 + r, 365 / d);",
    'const n = globalThis.Math.pow?.(1 + r, 365 / d);',
    'const p = (1 + daily) ** 365;',
    'x **= 1 / 365;',
    'const s = `${(1 + r) ** (365 / d)}`;',
    'const t = Math.pow(',
    '    1 + r,',
    '    365 / d,',
    ');',
];

/** What `caught` reports for POWERS laid out from line `first`: the exponent of each statement, read past its base. */
const powersFrom = (first: number): string[] => ['365 / d', '365 / d', '365 / days', '1 / 365', '365 / d', '365.25 / d', '365 / d', '365 / d', '365', '1 / 365', '365 / d', '365 / d'].map((exponent, i) => `${first + i}  ${exponent}`);

/** A 365 that is no exponent, in every place a scanner could mistake it for one: none of these may be flagged. */
const LOOK_ALIKES = [
    'const y = Math.floor(total / 365);',
    'const rem = total % 365;',
    'const t = days / 365;',
    "const dayCount = 'ACT/365';",
    "const options = [{value: 'ACT/365', label: 'ACT/365'}];",
    "const tip = '(1 + Δ%)^{365/d} − 1';",
    '// Annualized: (1 + deltaPct/100)^(365/days) - 1, as %',
    '// const a = Math.pow(1 + r, 365 / d);',
    '/** (1 + r) ** (365 / d) */',
    "const quoted = 'Math.pow(1 + r, 365 / d)';",
    'const doc = `(1 + r) ** (365 / d)`;',
    'const v = Math.pow(total / 365, 2);',
    'const w = Math.pow(f(a, 365), n);',
    'const z = (total / 365) ** 2;',
    'const q = Math.pow(1 + r, 3650 / d);',
    'const daily = Math.pow(dailyFactor, daysDelta);',
    'const one = Math.pow(365);',
    'const m = Math.max(1 + r, 365 / d);',
    'const big = 10n ** BigInt(scale);',
    'const tiny = 10 ** -digits;',
    'let h = 2;',
    'h *= 365;',
];

/** A source wrapped in a component's instance script, one row per line: its first row lands on line 2. */
const inScript = (rows: readonly string[]): string => ['<script lang="ts">', ...rows.map((row) => `    ${row}`), '</script>'].join('\n');

// ---------------------------------------------------------------------------
// The gate
// ---------------------------------------------------------------------------

/** What (A) prints when a listed file does not declare its measure: the form, and where the rule lives. */
const HOW_TO_DECLARE = [
    '',
    'The frontend computes no financial quantity; an interactive measure (the measuring tool, a what-if curve, an aggregate of the lots the user chooses) is the only exception,',
    'and it is declared where it lives (frontend.instructions.md «Financial numbers»; financial-math.instructions.md, rule 6):',
    "a line of the module's leading JSDoc block — its first /** comment, before any code — opens with the tag, then describes the measure:",
    '',
    '    /**',
    '     * …',
    `     * ${TAG} <what it computes in the browser, and why no backend field serves it>`,
    '     */',
    '',
];

describe('Financial math exceptions: the browser computes only the interactive measures it declares (Y12a step 2 gate)', () => {
    const files = sourceFiles();
    const texts = new Map(files.map((file) => [file, readFileSync(join(FRONTEND, file), 'utf8')] as const));
    const textOf = (file: string): string => texts.get(file) ?? '';
    const scans = files.map((file) => scanSource(file, textOf(file)));
    const hits = scans.flatMap((scan) => scan.hits);
    const parseErrors = scans.flatMap((scan) => scan.parseErrors);

    describe('(A) declared → marked', () => {
        for (const entry of DECLARED_EXCEPTIONS) {
            it(`${entry.file} carries ${TAG} in its leading JSDoc block`, () => {
                const path = join(FRONTEND, entry.file);
                const problem = declarationProblem(entry.file, existsSync(path) ? readFileSync(path, 'utf8') : null);
                expect(problem === null ? [] : [problem], [...HOW_TO_DECLARE, `Listed as: ${entry.measure}.`, ''].join('\n  ')).toEqual([]);
            });
        }
    });

    describe('(B) marked → declared', () => {
        it(`no unlisted product source contains ${TAG}`, () => {
            const offenders = undeclaredTags(texts, DECLARED_FILES);
            const rule = [
                `Only the files of DECLARED_EXCEPTIONS (src/financialMathExceptions.gate.test.ts) carry ${TAG}.`,
                'A new exception is added deliberately, by extending DECLARED_EXCEPTIONS in this gate — in the same change as the tag, with the file named in rule 6 of financial_math.md.',
                'Otherwise remove the tag: the frontend computes no financial quantity, it shows the fields the backend computes.',
            ];
            expect(offenders, ['', ...rule, `${offenders.length} unlisted mention(s):`, '', ...offenders, ''].join('\n  ')).toEqual([]);
        });
    });

    describe('(C) annualization by exponent only where declared', () => {
        it('parses every source it reads', () => {
            expect(parseErrors, ['', 'These sources could not be parsed, so (C) cannot vouch for them:', '', ...parseErrors, ''].join('\n  ')).toEqual([]);
        });

        it('raises to an exponent holding 365 only in the files declared to annualize (annualizes: true)', () => {
            const offenders = annualizationOffenders(hits, ANNUALIZING_FILES);
            const rule = [
                'The frontend computes no financial quantity (frontend.instructions.md «Financial numbers»; financial-math.instructions.md, rule 6).',
                "A power whose exponent holds 365 annualizes a return, and returns are the backend's (backend/app/services/financial_math/returns.py): call the field the backend computes instead.",
                'A declaration is no licence to annualize (Y-29): a file of DECLARED_EXCEPTIONS whose entry says annualizes: false stays under this rule, like any other source.',
                `Or, if annualizing is part of an interactive measure (the measuring tool, a what-if curve, an aggregate of the lots the user chooses), say so on purpose: an entry in DECLARED_EXCEPTIONS of src/financialMathExceptions.gate.test.ts with annualizes: true, and ${TAG} in the file's leading JSDoc block.`,
            ];
            expect(offenders, ['', ...rule, `${offenders.length} power(s) outside the files declared to annualize:`, '', ...offenders, ''].join('\n  ')).toEqual([]);
        });
    });

    describe('(D) positive controls', () => {
        it('flags a power whose exponent holds 365, in every spelling, however its base nests', () => {
            // The positive control of (C): "no undeclared power" is also what a scanner that finds none would report.
            expect(caught('src/lib/a.ts', POWERS.join('\n'))).toEqual(powersFrom(1));
        });

        it('flags the same powers in a component: module script, instance script, every markup expression', () => {
            expect(caught('src/lib/A.svelte', inScript(POWERS))).toEqual(powersFrom(2));
            const component = [
                '<script module lang="ts">',
                '    export const DAILY = Math.pow(1 + RATE, 1 / 365);',
                '</script>',
                '',
                '<script lang="ts">',
                '    let annual = $derived((1 + daily) ** 365);',
                "    const dayCount = 'ACT/365';",
                '    // Math.pow(1 + r, 365 / d)',
                '</script>',
                '',
                '<!-- (1 + r) ** (365 / d) -->',
                '<p title="Math.pow(1 + r, 365 / d)">{Math.pow(1 + r, 365 / days)}</p>',
                '{#if open}<span>{(1 + r) ** (1 / 365)} {total / 365} ACT/365</span>{/if}',
                '<button onclick={() => (value **= 1 / 365)}>x</button>',
                '',
                '<style>',
                '    .a {',
                '        order: 365;',
                '    }',
                '</style>',
            ].join('\n');
            expect(caught('src/lib/A.svelte', component)).toEqual(['2  1 / 365', '6  365', '12  365 / days', '13  1 / 365', '14  1 / 365']);
        });

        it('takes no other 365 for an exponent: a divisor, a base, a label, a formula, a comment, 3650', () => {
            expect(caught('src/lib/a.ts', LOOK_ALIKES.join('\n'))).toEqual([]);
            expect(caught('src/lib/A.svelte', inScript(LOOK_ALIKES))).toEqual([]);
        });

        it('flags a power holding 365 in a file that does not annualize, declared or not — a lot module of D-MF6(b) too — and spares MeasureSignal and CompoundSignal', () => {
            // The positive control of (C)'s verdict, on the very set (C) applies: the real tree raises to 365 in no file (C)
            // forbids, so (C) alone would pass as well with a verdict that flags nothing. And a declaration is no licence to
            // annualize: the lot modules sum, average and rebase, so an annualization added to one of them one day is
            // reported like any other. The hits come from the scanner itself, one power per file.
            const powerIn = (file: string, power: string): Hit[] => scanSource(file, `export const x = ${power};`).hits;
            const undeclared = 'src/lib/utils/returns.ts';
            const synthetic = [
                ...powerIn(undeclared, 'Math.pow(growth, 365 / days)'),
                ...powerIn(LOTS_TABLE, 'Math.pow(growth, 365 / days)'),
                ...powerIn(LOT_COMPARISON, '(1 + r) ** (365 / days)'),
                ...powerIn(LOT_WAC, 'Math.pow(1 + rate, 1 / 365)'),
                ...powerIn(MEASURE, 'Math.pow(growth, 365 / days)'),
                ...powerIn(COMPOUND, 'Math.pow(1 + rate, 1 / 365)'),
            ];
            // A verdict on hits the scanner never produced would prove nothing.
            expect(synthetic.map((hit) => hit.file)).toEqual([undeclared, LOTS_TABLE, LOT_COMPARISON, LOT_WAC, MEASURE, COMPOUND]);
            expect(
                annualizationOffenders(synthetic, ANNUALIZING_FILES),
                "Y-29: being declared does not exempt a file from (C). The lot modules of D-MF6(b) sum, average and rebase, they never annualize: a power holding 365 in one of them is an offender like any other. Only MeasureSignal (the ruler's Δ%/yr) and CompoundSignal (the compound curve's daily factor) raise to 365 by design",
            ).toEqual([`${undeclared}:1  Math.pow(growth, 365 / days)`, `${LOTS_TABLE}:1  Math.pow(growth, 365 / days)`, `${LOT_COMPARISON}:1  (1 + r) ** (365 / days)`, `${LOT_WAC}:1  Math.pow(1 + rate, 1 / 365)`]);
        });

        it('reads the declaration in the leading JSDoc block only, as a block tag followed by its description', () => {
            const declared = [
                '/**',
                ' * MeasureSignal — Measurement overlay signal.',
                ' *',
                ' * @financial-math-exception R18, the measuring tool: Δ, Δ% and annualized between',
                ' *   the two points the user picks, computed in the browser.',
                ' *',
                ' * @module charts/signals/MeasureSignal',
                ' */',
                '',
                "import {ChartSignal} from './ChartSignal';",
            ].join('\n');
            expect(readDeclaration(declared)).toMatchObject({tagLine: 4, description: 'R18, the measuring tool: Δ, Δ% and annualized between the two points the user picks, computed in the browser.'});
            expect(declarationProblem('src/lib/a.ts', declared)).toBeNull();
            // On one line, after a line comment: still the leading block.
            const oneLine = "// A note.\n/** @financial-math-exception R19, a what-if curve drawn from the user's parameters. */\nexport const x = 1;";
            expect(readDeclaration(oneLine)).toMatchObject({tagLine: 2, description: "R19, a what-if curve drawn from the user's parameters."});
            expect(declarationProblem('src/lib/a.ts', oneLine)).toBeNull();

            // After code, in a later comment, mid-line, a look-alike tag: none of them declares the file.
            const afterCode = ["import {ChartSignal} from './ChartSignal';", '/**', ' * @financial-math-exception R18, the measuring tool between two picked points.', ' */', 'export class A {}'].join('\n');
            expect(readDeclaration(afterCode).tagLine).toBeNull();
            expect(declarationProblem('src/lib/a.ts', afterCode)).toMatch(/opens with code.*line 3 \(outside the leading block\)/);
            const later = ['/**', ' * A chart signal.', ' */', "import {ChartSignal} from './ChartSignal';", '/** @financial-math-exception R18, the measuring tool between two picked points. */', 'export class A {}'].join('\n');
            expect(readDeclaration(later).tagLine).toBeNull();
            expect(declarationProblem('src/lib/a.ts', later)).toMatch(/block \(lines 1-3\) carries no @financial-math-exception block tag\. The string appears at line 5 \(outside the leading block\)/);
            const midLine = ['/**', ' * This module is a @financial-math-exception: the measuring tool between two picked points.', ' * @financial-math-exceptions R18, the measuring tool between two picked points.', ' */', 'export class A {}'].join('\n');
            expect(readDeclaration(midLine).tagLine).toBeNull();
            expect(declarationProblem('src/lib/a.ts', midLine)).toMatch(/line 2 \(in the leading block, but not as a tag opening its line\), line 3 \(in the leading block/);

            // A tag with no description, or a placeholder: not a declaration.
            const bare = ['/**', ' * @financial-math-exception', ' * @module charts/signals/MeasureSignal', ' */'].join('\n');
            expect(readDeclaration(bare)).toMatchObject({tagLine: 2, description: ''});
            expect(declarationProblem('src/lib/a.ts', bare)).toMatch(/^src\/lib\/a\.ts:2 {2}@financial-math-exception is followed by «»/);
            expect(declarationProblem('src/lib/a.ts', '/** @financial-math-exception R18 */')).toMatch(/followed by «R18»/);

            // A component has no leading JSDoc block; a listed file that is gone declares nothing.
            expect(declarationProblem('src/lib/A.svelte', '<script lang="ts">\n    /** @financial-math-exception R18, the measuring tool between two picked points. */\n</script>')).toMatch(/is not a \.ts module/);
            expect(declarationProblem('src/lib/gone.ts', null)).toMatch(/does not exist/);
        });

        it('flags the tag in an unlisted source, wherever it stands, and spares a listed one', () => {
            const sources: (readonly [string, string])[] = [
                [MEASURE, '/**\n * @financial-math-exception R18, the measuring tool between two picked points.\n */'],
                ['src/lib/utils/returns.ts', 'export const r = 1;\n// @financial-math-exception borrowed from MeasureSignal'],
                ['src/lib/components/A.svelte', '<p title="@financial-math-exception">x</p>'],
                ['src/lib/utils/plain.ts', 'export const financialMathException = 1;'],
            ];
            expect(undeclaredTags(sources, DECLARED_FILES)).toEqual(['src/lib/utils/returns.ts:2', 'src/lib/components/A.svelte:1']);
        });

        it('reads every product source, components and modules alike, and no test, mock or generated client', () => {
            const read = [MEASURE, CELL_DATE_RANGE, 'src/lib/stores/app/toastStore.svelte.ts', 'src/routes/(app)/dashboard/+page.svelte', 'src/lib/api/zodios-client.ts'];
            const skipped = [
                'src/financialMathExceptions.gate.test.ts',
                'src/lib/charts/signals/MeasureSignal.spec.ts',
                'src/__tests__/component.ts',
                'src/__mocks__/$app/environment.ts',
                'src/lib/charts/signals/__tests__/fixtures.ts',
                'src/lib/api/generated.ts',
                'src/lib/api/generated-tools.ts',
                'src/lib/api/tool-contract-map.generated.ts',
                'src/lib/dev/designer-lab/color.js',
                'src/app.css',
            ];
            expect(read.filter((path) => !isScanned(path))).toEqual([]);
            expect(skipped.filter((path) => isScanned(path))).toEqual([]);
            // 384 components and 405 modules when this gate was written: a walk that reaches the wrong directory, or
            // reads one kind of file only, finds far fewer.
            expect(files.filter((file) => file.endsWith('.svelte')).length).toBeGreaterThan(300);
            expect(files.filter((file) => file.endsWith('.ts')).length).toBeGreaterThan(300);
            expect(files).toEqual(expect.arrayContaining([...DECLARED_FILES, CELL_DATE_RANGE, SCHEDULED_INVESTMENT]));
            expect(files.filter((file) => file.startsWith('src/lib/api/generated'))).toEqual([]);
        });

        it('finds the power CompoundSignal computes today, and none in the real files whose 365 is no exponent', () => {
            // Presence: CompoundSignal draws its curve with a daily factor (1 + rate)^(1/365), so the scan of the real tree
            // must see it. MeasureSignal's power is held by the next control, with every file declared to annualize.
            expect(
                hits.some((hit) => hit.file === COMPOUND),
                `${COMPOUND} raises to an exponent holding 365 today: if it stopped, anchor this control on another known power, and ask whether the file still needs its exception`,
            ).toBe(true);
            // Absence, behind a presence barrier: each file is read and holds a 365, and none of its 365s is an exponent.
            for (const file of [CELL_DATE_RANGE, SCHEDULED_INVESTMENT, LINEAR]) {
                expect(YEAR_DAYS.test(textOf(file)), `${file} is read and holds a 365`).toBe(true);
                expect(
                    hits.filter((hit) => hit.file === file).map((hit) => `${hit.line}  ${hit.expr}`),
                    `${file}: its 365 is a divisor, a remainder or a label, never an exponent`,
                ).toEqual([]);
            }
        });

        it('finds a power in each file declared to annualize, MeasureSignal and CompoundSignal alike', () => {
            // Non-vacuity of (C), which asserts that every power of the real tree lies in ANNUALIZING_FILES. A scan that saw
            // no power would pass (C) all the same; and a file declared to annualize that no longer does would hold a licence
            // for the next annualization added to it — Y-29 again. So each file declared to annualize must show its power:
            // MeasureSignal's Δ%/yr, `Math.pow(growth, 365 / days)`, as well as CompoundSignal's daily factor.
            const annualizing = [...ANNUALIZING_FILES];
            expect(annualizing, "MeasureSignal (the ruler's Δ%/yr) and CompoundSignal (the compound curve's daily factor) annualize by design: their entries say annualizes: true").toEqual(expect.arrayContaining([MEASURE, COMPOUND]));
            expect(
                annualizing.filter((file) => !hits.some((hit) => hit.file === file)),
                'declared to annualize (annualizes: true), yet the scan finds no power holding 365 there: a file that stopped annualizing says annualizes: false — it stays declared, and falls back under (C); otherwise the scan no longer sees its power',
            ).toEqual([]);
        });
    });
});
