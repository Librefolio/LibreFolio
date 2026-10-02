/**
 * Gate: every `{@html}` sink renders sanitised or reviewed HTML (workstream K, step 13, item 0).
 *
 * ## What this protects
 *
 * `{@html X}` is where a string becomes markup. `htmlInterpolation.gate.test.ts` guards the strings
 * built by hand — a user or provider text field interpolated into a template must be escaped at the
 * source. But a sink can also be fed from further away: a toast message assembled by an i18n call, a
 * tooltip handed its HTML as a prop, a validation message resolved from a backend error. Escaping at
 * every source is a promise nobody can check from the sink, so the sinks whose input is mixed markup
 * of mixed origin go through `sanitizeHtml(…)` (`$lib/utils/core/sanitizeHtml.ts`, DOMPurify), and the
 * rest are named here, one by one, with the reason they are safe without it.
 *
 * ## The rule, as this file checks it
 *
 * Every `{@html X}` in a non-test `.svelte` file under `src` is either
 *   - a call to `sanitizeHtml(…)` — the whole expression, nothing around it; or
 *   - an entry of `REVIEWED_SINKS`: a file, an expression and a reason. The expression is the sink's
 *     whitespace-collapsed source, or a call pattern `name(…)` that stands for any call to `name` in that
 *     file — used only for functions that escape their own input, so any argument is fine.
 *
 * Entries are keyed by content, never by line, so an unrelated edit above a sink cannot turn the gate
 * red. An entry that no longer matches any sink is stale and fails the gate, and so does an entry whose
 * reason is too short to be checked: a list nobody can trust protects nothing.
 *
 * ## Completeness, stated honestly
 *
 * The gate sees `{@html}` in `.svelte` markup — every sink the app has today. It does not see
 * `innerHTML`/`outerHTML`/`insertAdjacentHTML` assignments in scripts, nor HTML handed to a library
 * that renders it (an ECharts tooltip formatter): grow the forms with the rule. It does not judge a
 * reviewed entry either: an entry is a human decision recorded once, and the reason is what a reviewer
 * re-checks when the code behind it changes.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */

import {describe, expect, it} from 'vitest';
import {readdirSync, readFileSync} from 'node:fs';
import {dirname, join, relative, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {parse as parseSvelte} from 'svelte/compiler';

/** `frontend/`: paths are reported relative to it, the directory the runner and `vitest run` start from. */
const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(FRONTEND, 'src');

/** The one sanitiser accepted at a sink. */
const SANITIZER = 'sanitizeHtml';

interface ReviewedSink {
    file: string;
    /** The sink's expression, whitespace collapsed — or `name(…)`: any call to `name` in this file. */
    expr: string;
    why: string;
}

const COLUMN_DEFS = 'Column-definition HTML: its producers escape at the source, which htmlInterpolation.gate.test.ts enforces; sanitising every cell of every table on each render is too costly for what it would add.';
const CURRENCY_HTML = 'Formats a number and a currency: the code and the symbol go through escapeHtml inside the formatter (currencyFormat.ts), the flag comes from the currency reference data.';
const TX_CELL_BUILDERS = 'Built by the transaction cell builders, which escape user text at the source — htmlInterpolation.gate.test.ts enforces it on their templates.';

/** Sinks reviewed and kept without `sanitizeHtml`, each with the reason it is safe. */
const REVIEWED_SINKS: readonly ReviewedSink[] = [
    {file: 'src/lib/components/table/DataTable.svelte', expr: 'cellContent.html', why: COLUMN_DEFS},
    {file: 'src/lib/components/table/DataTable.svelte', expr: 'footerContent.html', why: COLUMN_DEFS},
    {file: 'src/lib/components/table/DataTable.svelte', expr: 'getColumnHeaderHtml(column)', why: COLUMN_DEFS},
    {file: 'src/lib/components/ui/display/CurrencyAmount.svelte', expr: 'formatCurrencyAmountHtml(…)', why: CURRENCY_HTML},
    {file: 'src/routes/(app)/dashboard/+page.svelte', expr: 'formatCurrencyAmountHtml(…)', why: CURRENCY_HTML},
    {file: 'src/lib/components/transactions/wac/WacPreviewSection.svelte', expr: 'formatCurrencyCodeHtml(…)', why: CURRENCY_HTML},
    {file: 'src/lib/components/transactions/modals/TransactionBulkModal.svelte', expr: 'formatCurrencyCodeHtml(…)', why: CURRENCY_HTML},
    {file: 'src/lib/components/table/DataTableColumnFilter.svelte', expr: 'formatCurrencyCodeHtml(…)', why: CURRENCY_HTML},
    {
        file: 'src/lib/components/layout/ChangelogModal.svelte',
        expr: 'renderHighlighted(…)',
        why: 'NOT an escape: marked renders the bundled CHANGELOG.md (a ?raw import resolved at build time — repository content, never user or provider data) and its output is not sanitised. The search needle is only regex-escaped to match; it is never inserted, <mark> wraps text already there.',
    },
    {file: 'src/lib/components/files/FilePreviewModal.svelte', expr: 'renderedMarkdown', why: 'DOMPurify-sanitised marked output; the KaTeX pass that follows renders the text content of $$…$$ paragraphs, and KaTeX escapes its input (trust off).'},
    {file: 'src/lib/components/charts/SignalOptionContent.svelte', expr: 'renderedSubtitle', why: 'renderInlineMathText(subtitle): the server signal-catalog subtitle is escaped by escapeHtml before KaTeX renders its $…$ spans.'},
    {
        file: 'src/lib/components/assets/PriceDataImportModal.svelte',
        expr: `$t('import.csv.separatorHint', {values: {sep: '<code class="bg-white/30 dark:bg-slate-700/50 px-1 rounded">;</code>'}})`,
        why: 'A static i18n message with a static <code> value: nothing in it comes from a user, a file or a provider.',
    },
    {file: 'src/lib/components/transactions/cells/TxLinksCell.svelte', expr: 'eventHtml', why: TX_CELL_BUILDERS},
    {file: 'src/lib/components/transactions/cells/TxLinksCell.svelte', expr: 'linkHtml', why: TX_CELL_BUILDERS},
    {file: 'src/lib/components/transactions/cells/TxTooltipCell.svelte', expr: 'html', why: TX_CELL_BUILDERS},
    {file: 'src/lib/components/transactions/modals/TransactionCompareModal.svelte', expr: 'cell.display', why: TX_CELL_BUILDERS},
];

interface Sink {
    file: string;
    line: number;
    /** The expression, whitespace collapsed. */
    expr: string;
    /** The callee's source when the expression is a call, for `name(…)` entries. */
    callee: string | null;
    sanitized: boolean;
}

interface Scan {
    sinks: Sink[];
    parseErrors: string[];
}

type EstreeNode = {type: string; start: number; end: number; [key: string]: unknown};

const collapse = (s: string): string => s.trim().replace(/\s+/g, ' ');

/** Whether a path (relative to `frontend/`) is a component this gate reads. */
function isScanned(path: string): boolean {
    if (!path.endsWith('.svelte')) return false;
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

/**
 * The `{@html}` sinks of one component, found by Svelte's own parser: a sink quoted in a comment, a
 * string or a `<script>` is not a sink, and one nested in any block is. A function of its own so that
 * a synthetic source goes through exactly the code a real file goes through.
 */
function scanSinks(file: string, text: string): Scan {
    const scan: Scan = {sinks: [], parseErrors: []};
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
        const node = value as {type?: unknown; start?: number; expression?: EstreeNode};
        if (node.type === 'HtmlTag' && node.expression) {
            const expression = node.expression;
            const callee = expression.type === 'CallExpression' ? (expression.callee as EstreeNode) : null;
            scan.sinks.push({
                file,
                line: text.slice(0, node.start).split('\n').length,
                expr: collapse(text.slice(expression.start, expression.end)),
                callee: callee ? collapse(text.slice(callee.start, callee.end)) : null,
                sanitized: !!callee && callee.type === 'Identifier' && callee.name === SANITIZER,
            });
        }
        for (const [key, child] of Object.entries(value)) {
            if (key !== 'metadata' && key !== 'parent') visit(child);
        }
    };
    visit((ast as {fragment: unknown}).fragment);
    return scan;
}

/** Whether a reviewed entry covers a sink: same file, and the same expression or a call to the named function. */
function covers(entry: ReviewedSink, sink: Sink): boolean {
    if (entry.file !== sink.file) return false;
    if (entry.expr.endsWith('(…)')) return sink.callee === entry.expr.slice(0, -'(…)'.length);
    return entry.expr === sink.expr;
}

const flagged = (sinks: readonly Sink[], reviewed: readonly ReviewedSink[]): Sink[] => sinks.filter((sink) => !sink.sanitized && !reviewed.some((entry) => covers(entry, sink)));
/** `line  expr` of every sink a synthetic source leaves unsanitised and unreviewed. */
const caught = (file: string, text: string, reviewed: readonly ReviewedSink[] = []): string[] => flagged(scanSinks(file, text).sinks, reviewed).map((sink) => `${sink.line}  ${sink.expr}`);

describe('{@html} renders sanitised or reviewed HTML only (K step 13, item 0 gate)', () => {
    const files = sourceFiles();
    const scans = files.map((file) => scanSinks(file, readFileSync(join(FRONTEND, file), 'utf8')));
    const sinks = scans.flatMap((scan) => scan.sinks);
    const parseErrors = scans.flatMap((scan) => scan.parseErrors);

    it('finds a sink wherever the markup puts it, and nowhere else', () => {
        // The positive control of the verdict below: "every sink is sanitised" is also what a scanner
        // that finds no sink would report.
        expect(caught('a.svelte', '<p>{@html toast.message}</p>')).toEqual(['1  toast.message']);
        const nested = ['{#if a}', '    {#each items as item (item.id)}', '        <Comp>{@html item.html}</Comp>', '    {:else}', '        {#await p then v}{@html v}{/await}', '    {/each}', '{/if}', '{#snippet s(x)}<b>{@html render(x)}</b>{/snippet}'].join('\n');
        expect(caught('a.svelte', nested)).toEqual(['3  item.html', '5  v', '8  render(x)']);
        // Quoted, commented or in a script: text, not a sink.
        expect(caught('a.svelte', '<script lang="ts">\n    const s = "{@html x}";\n</script>\n<!-- {@html y} -->\n<p>{"{@html z}"}</p>')).toEqual([]);
    });

    it('accepts sanitizeHtml(…) as the whole expression, and nothing that merely contains it', () => {
        expect(caught('a.svelte', '{@html sanitizeHtml(toast.message)}')).toEqual([]);
        expect(caught('a.svelte', '{@html cond ? sanitizeHtml(a) : b}\n{@html sanitizeHtml(a) + b}\n{@html utils.sanitizeHtml(a)}')).toEqual(['1  cond ? sanitizeHtml(a) : b', '2  sanitizeHtml(a) + b', '3  utils.sanitizeHtml(a)']);
    });

    it('matches a reviewed entry by exact expression, or by callee for a `name(…)` entry, in its own file only', () => {
        const reviewed: ReviewedSink[] = [
            {file: 'a.svelte', expr: 'cell.html', why: 'a reason long enough to be checked'},
            {file: 'a.svelte', expr: 'formatCode(…)', why: 'a reason long enough to be checked'},
        ];
        expect(caught('a.svelte', '{@html cell.html}\n{@html formatCode(x.code)}\n{@html formatCode(y)}', reviewed)).toEqual([]);
        expect(caught('a.svelte', '{@html cell.html.trim()}\n{@html other.formatCode(x)}', reviewed)).toEqual(['1  cell.html.trim()', '2  other.formatCode(x)']);
        expect(caught('b.svelte', '{@html cell.html}', reviewed)).toEqual(['1  cell.html']);
    });

    it('reads every component of the app, and no test harness', () => {
        expect(isScanned('src/lib/components/ui/feedback/ToastContainer.svelte')).toBe(true);
        expect(isScanned('src/routes/(app)/dashboard/+page.svelte')).toBe(true);
        expect(isScanned('src/__tests__/harness/AppLayoutGateHarness.svelte')).toBe(false);
        expect(isScanned('src/lib/utils/core/escapeHtml.ts')).toBe(false);
        // 42 sinks in 19 components when this gate was written, 10 of them in DataTable: a walk that
        // reaches the wrong directory, or a traversal that stops at the first element, finds far fewer.
        expect(sinks.length).toBeGreaterThan(35);
        expect(sinks.filter((sink) => sink.file === 'src/lib/components/table/DataTable.svelte').length).toBeGreaterThanOrEqual(10);
        expect(sinks.map((sink) => sink.file)).toContain('src/lib/components/ui/feedback/ToastContainer.svelte');
    });

    it('parses every component it reads', () => {
        expect(parseErrors, ['', 'These components could not be parsed, so the gate cannot vouch for them:', '', ...parseErrors, ''].join('\n  ')).toEqual([]);
    });

    it('renders every {@html} through sanitizeHtml or a reviewed entry', () => {
        const offenders = flagged(sinks, REVIEWED_SINKS).map((sink) => `${sink.file}:${sink.line}  {@html ${sink.expr}}`);
        const rule = 'Every {@html} renders sanitizeHtml(…) ($lib/utils/core/sanitizeHtml.ts) or an entry of REVIEWED_SINKS with its reason — K step 13, item 0.';

        expect(offenders, ['', rule, `${offenders.length} unsanitised sink(s):`, '', ...offenders, ''].join('\n  ')).toEqual([]);
    });

    it('keeps the reviewed sinks current and explained', () => {
        const stale = REVIEWED_SINKS.filter((entry) => !sinks.some((sink) => covers(entry, sink))).map((entry) => `${entry.file}  ${entry.expr}`);
        expect(stale, ['', 'Reviewed sinks that no longer match any {@html} — delete them:', '', ...stale, ''].join('\n  ')).toEqual([]);
        expect(REVIEWED_SINKS.filter((entry) => entry.why.trim().length < 40).map((entry) => `${entry.file}  ${entry.expr}`)).toEqual([]);
    });
});
