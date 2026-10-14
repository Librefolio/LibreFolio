/**
 * Guard: the gallery's dashboard fixture still matches the API schema (workstream M, round R12), and
 * its anonymization scaled money only (workstream I, lot I-M30).
 *
 * ## What this protects
 *
 * `e2e/dashboard-report.json` is the mocked response of `POST /api/v1/portfolio/report` that
 * `setupDashboardMockReport` in `e2e/gallery.spec.ts` serves to the dashboard shots. The client
 * validates every response with Zod (`zodios-client.ts`, `validate: 'response'`): a fixture that no
 * longer matches the schema is rejected whole, the dashboard renders without data, and the gallery
 * goes on capturing it. That is what happened from 09-11: `summary.holdings[*].yield_on_cost` became
 * required, the fixture lacked it, and several shots were taken of an empty dashboard. The gallery
 * needs about 1.2 h to get there; this file says it in seconds.
 *
 * The snapshot is anonymized by `scripts/normalize_dashboard_fixture.py`, which scales every field
 * whose name looks like money until the net worth is 50 000. A share, a yield on cost and a price
 * change carry such a name without being money: scaled, they still parse, and the dashboard draws
 * allocations that do not add up to 100 % and yields and daily moves multiplied by the factor.
 *
 * ## What it checks
 *
 * - that `POST /api/v1/portfolio/report` is validated with `schemas.PortfolioReportResponse`, so the
 *   schema parsed here is the one zodios applies at runtime;
 * - that the fixture parses with it. A failure lists issue codes and key paths only — never a value,
 *   nor Zod's message, which can quote one: the fixture is a real user snapshot, scaled;
 * - that what survives validation still holds the sections the gallery relies on — `history`,
 *   `summary.holdings`, `allocation_history` — as counts above zero, never as sizes, so a capture of
 *   another size still passes. Counted after parsing because zodios hands the page the parsed value:
 *   a section the schema no longer knows is stripped, and the shots built on it go empty;
 * - two negative controls on an in-memory deep copy: without `yield_on_cost` on one holding, or
 *   without `summary.net_worth`, the verdict turns red. Without them, "it parses" would also be what
 *   a guard that checks nothing reports;
 * - that the figures that are not money keep, in the raw file, the relation the backend writes them
 *   with (lot I-M30, plan 54): every allocation list — `summary.allocation_by_*`, each day of
 *   `allocation_history.*` — that is neither empty nor worth zero sums to 100 within 0.005 per item;
 *   every available `yield_on_cost.value` is `gross_income_per_unit.amount / wac_per_unit` within a
 *   millionth; every `price_change_1d` at market price is, times 100, `gain_loss_change_1d_percent`
 *   in magnitude within 0.0101. A failure names the family and counts, never a figure;
 * - one negative control per relation, on a deep copy first rewritten to hold it, so that each check
 *   is also proven green on the real shapes: one summary list scaled by 0.9, one yield on cost
 *   doubled, one price change a point off its percent, and the verdict turns red.
 *
 * ## What it does not
 *
 * It reads the committed file as is: `gallery.spec.ts` shifts its `YYYY-MM-DD` dates before serving
 * it, which changes no key and no type. Whether the dashboard draws valid data correctly is the
 * gallery's question, not this one.
 *
 * ## When it goes red
 *
 * - The schema test: Rule 12 — a captured fixture that fails the schema is a STOP, not an edit. Ask
 *   the developer for a fresh capture, normalize it with `./dev.py mkdocs normalize-dashboard-fixture`,
 *   and never edit the fixture by hand.
 * - A relation test: the normalizer scaled a field that is not money. Fix the path exceptions in
 *   `scripts/normalize_dashboard_fixture.py`, then normalize a fresh capture with it; never edit the
 *   fixture by hand (plan 54, on approval, recomputed only these derived figures from the fixture's
 *   own amounts with the backend's formulas).
 *
 * Each failure message says the same.
 */

import {readFileSync} from 'node:fs';

import {describe, expect, it} from 'vitest';
import type {ZodIssue} from 'zod';

import {api, schemas} from '$lib/api/generated';

/** Read from disk, the way `gallery.spec.ts` reads it. */
const FIXTURE = new URL('../../../e2e/dashboard-report.json', import.meta.url);

/** What the gallery dashboard shots draw from. `allocation_history` once per tab the gallery shoots: type, sector, geography. */
const GALLERY_SECTIONS = [['history'], ['summary', 'holdings'], ['allocation_history', 'type'], ['allocation_history', 'sector'], ['allocation_history', 'geography']] as const;

const WHAT_TO_DO = [
    'Rule 12 — a captured fixture that fails the schema is a STOP, not an edit:',
    '  1. ask the developer for a fresh capture of the dashboard report (POST /api/v1/portfolio/report) from a real backend;',
    '  2. normalize it before committing: ./dev.py mkdocs normalize-dashboard-fixture (--dry-run first; if its invariants fail on the new schema, fix the script, not the fixture);',
    '  3. never edit, trim or "sanitize" e2e/dashboard-report.json by hand: a patched snapshot shows a portfolio that never existed, and the shots built on it stay green.',
];

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value);

/** The node at `path`, or `undefined` from the first missing step on. */
function nodeAt(root: unknown, path: readonly string[]): unknown {
    let node = root;
    for (const key of path) node = isRecord(node) ? node[key] : undefined;
    return node;
}

/** Length of the array at `path`; 0 when it is missing or not an array. */
function countAt(root: unknown, path: readonly string[]): number {
    const node = nodeAt(root, path);
    return Array.isArray(node) ? node.length : 0;
}

/**
 * Array indices print as `[*]`, so N holdings failing alike make one line. A key that is not an
 * identifier would be data (a record keyed by a name or a date), so it is masked too.
 */
function keyPath(path: ReadonlyArray<string | number>): string {
    if (path.length === 0) return '(root)';
    return path
        .map((segment) => (typeof segment === 'number' ? '[*]' : `.${/^[A-Za-z_]\w*$/.test(segment) ? segment : '<key>'}`))
        .join('')
        .replace(/^\./, '');
}

/**
 * One line per distinct issue — its code and its key path, never the value nor Zod's message, which
 * can quote it — with a count when it repeats. An `invalid_union` is followed, indented, by what its
 * branches found, since the cause lives there; a branch that only rejected the value's own type
 * (`null` against an object) is the alternative that did not apply, and is left out.
 */
function describeIssues(issues: readonly ZodIssue[], depth = 0): string[] {
    const blocks = new Map<string, {lines: string[]; count: number}>();
    for (const issue of issues) {
        const lines = [`${'  '.repeat(depth)}${issue.code} at ${keyPath(issue.path)}`];
        if (issue.code === 'invalid_union') {
            const branches = issue.unionErrors.map((branch) => branch.issues);
            const telling = branches.filter((found) => !found.every((inner) => inner.code === 'invalid_type' && inner.path.length === issue.path.length));
            lines.push(...describeIssues((telling.length > 0 ? telling : branches).flat(), depth + 1));
        }
        const key = lines.join('\n');
        const block = blocks.get(key);
        if (block) block.count += 1;
        else blocks.set(key, {lines, count: 1});
    }
    return [...blocks.values()].flatMap(({lines, count}) => lines.map((line, index) => (index === 0 && count > 1 ? `${line} (×${count})` : line)));
}

/** The guard's verdict on one report: what zodios would hand the page, and the problems as codes and key paths (none when it parses). */
function check(report: unknown) {
    const parsed = schemas.PortfolioReportResponse.safeParse(report);
    return {parsed, problems: parsed.success ? [] : describeIssues(parsed.error.issues)};
}

/** The dimensions the dashboard allocates by: `summary.allocation_by_<dim>` and `allocation_history.<dim>`. */
const DIMENSIONS = ['type', 'sector', 'geography'] as const;

const NOT_MONEY_SCALED = [
    'The normalizer scaled a figure that is not money (lot I-M30, plan 54): scripts/normalize_dashboard_fixture.py multiplies every field whose name looks like money, and the allocation shares, yield_on_cost.value and price_change_1d all carry such a name.',
    '  1. fix the path exceptions in scripts/normalize_dashboard_fixture.py, so that these figures are never scaled and its invariants refuse a fixture that breaks them;',
    "  2. ask the developer for a fresh capture and normalize it with the fixed script: ./dev.py mkdocs normalize-dashboard-fixture (--dry-run first). Plan 54, on approval, instead recomputed only these derived figures from the fixture's own amounts with the backend's formulas;",
    '  3. never edit e2e/dashboard-report.json by hand: a patched snapshot shows a portfolio that never existed, and the shots built on it stay green.',
];

/** A figure as a number: a number as it is, a decimal string parsed, anything else NaN, which fails every comparison below. */
function toNumber(value: unknown): number {
    if (typeof value === 'number') return value;
    return typeof value === 'string' && value.trim() !== '' ? Number(value) : Number.NaN;
}

/** The sum of `key` over a list; NaN as soon as one item has no figure there. */
function sumOf(items: readonly unknown[], key: string): number {
    return items.reduce<number>((total, item) => total + toNumber(nodeAt(item, [key])), 0);
}

/**
 * One allocation list. The backend writes each share as `amount / total * 100`, quantized to 2 decimals, and emits every
 * item, so the shares sum to 100 within 0.005 per item. An empty list, or one worth zero (to a millionth, the float sum
 * of amounts that cancel), has no share to sum.
 */
function shareVerdict(items: unknown): 'ok' | 'skip' | 'off' {
    if (!Array.isArray(items)) return 'off';
    if (items.length === 0) return 'skip';
    const shares = sumOf(items, 'value');
    const amounts = sumOf(items, 'amount');
    if (!Number.isFinite(shares) || !Number.isFinite(amounts)) return 'off';
    if (Math.abs(amounts) < 1e-6) return 'skip';
    return Math.abs(shares - 100) <= 0.005 * items.length + 1e-9 ? 'ok' : 'off';
}

/** Every allocation list: the three of the summary, then each day of the three histories. */
function allocationLists(report: unknown): unknown[] {
    const lists: unknown[] = DIMENSIONS.map((dim) => nodeAt(report, ['summary', `allocation_by_${dim}`]));
    for (const dim of DIMENSIONS) {
        const days = nodeAt(report, ['allocation_history', dim]);
        if (Array.isArray(days)) for (const day of days) lists.push(nodeAt(day, ['components']));
    }
    return lists;
}

/** Allocation lists whose shares do not sum to 100: one line per family, with counts, never a figure. */
function shareProblems(report: unknown): string[] {
    const problems: string[] = [];
    for (const dim of DIMENSIONS) {
        const list = nodeAt(report, ['summary', `allocation_by_${dim}`]);
        if (!Array.isArray(list)) problems.push(`summary.allocation_by_${dim}: missing`);
        else if (shareVerdict(list) === 'off') problems.push(`summary.allocation_by_${dim}: does not sum to 100`);
    }
    for (const dim of DIMENSIONS) {
        const days = nodeAt(report, ['allocation_history', dim]);
        if (!Array.isArray(days)) {
            problems.push(`allocation_history.${dim}: missing`);
            continue;
        }
        const off = days.filter((day) => shareVerdict(nodeAt(day, ['components'])) === 'off').length;
        if (off > 0) problems.push(`allocation_history.${dim}: ${off} of ${days.length} days do not sum to 100`);
    }
    return problems;
}

/** The holdings of the summary, or `undefined` when it has no list of them. */
function holdingsOf(report: unknown): Record<string, unknown>[] | undefined {
    const holdings = nodeAt(report, ['summary', 'holdings']);
    return Array.isArray(holdings) ? holdings.filter(isRecord) : undefined;
}

const isAvailableYieldOnCost = (holding: Record<string, unknown>): boolean => nodeAt(holding, ['yield_on_cost', 'status']) === 'available';

/** What an available yield on cost is: `gross_income_per_unit.amount / wac_per_unit`, unquantized; NaN when a term is missing. */
function expectedYieldOnCost(holding: Record<string, unknown>): number {
    return toNumber(nodeAt(holding, ['yield_on_cost', 'provenance', 'gross_income_per_unit', 'amount'])) / toNumber(holding.wac_per_unit);
}

/** Available yields on cost farther than a millionth from gross income per unit over WAC: one line, with counts, never a figure. */
function yieldOnCostProblems(report: unknown): string[] {
    const holdings = holdingsOf(report);
    if (!holdings) return ['summary.holdings: missing'];
    const available = holdings.filter(isAvailableYieldOnCost);
    const off = available.filter((holding) => {
        const expected = expectedYieldOnCost(holding);
        return !(Number.isFinite(expected) && Math.abs(toNumber(nodeAt(holding, ['yield_on_cost', 'value'])) - expected) <= 1e-6 * Math.abs(expected));
    }).length;
    return off > 0 ? [`summary.holdings[*].yield_on_cost: ${off} of ${available.length} available values differ from gross_income_per_unit / wac_per_unit`] : [];
}

/** A holding whose price change can be compared with its percent: valued at market price, with both figures. */
const isComparedPriceChange = (holding: Record<string, unknown>): boolean => holding.valuation_source === 'MARKET_PRICE' && holding.price_change_1d != null && holding.gain_loss_change_1d_percent != null;

/**
 * Market-price changes that are not a hundredth of `gain_loss_change_1d_percent`, compared in magnitude (a short
 * position gains when the price falls) within two roundings of 0.005: one line, with counts, never a figure.
 */
function priceChange1dProblems(report: unknown): string[] {
    const holdings = holdingsOf(report);
    if (!holdings) return ['summary.holdings: missing'];
    const compared = holdings.filter(isComparedPriceChange);
    const off = compared.filter((holding) => !(Math.abs(Math.abs(toNumber(holding.price_change_1d) * 100) - Math.abs(toNumber(holding.gain_loss_change_1d_percent))) <= 0.0101)).length;
    return off > 0 ? [`summary.holdings[*].price_change_1d: ${off} of ${compared.length} market-price changes differ from gain_loss_change_1d_percent / 100`] : [];
}

/** The failure message of a relation test: the problems, as family and counts, then what to do. */
function relationMessage(what: string, problems: readonly string[]): string {
    return ['', `e2e/dashboard-report.json: ${what}. As family and count (values left out on purpose: the fixture is a real user snapshot):`, ...problems.map((line) => `    ${line}`), '', ...NOT_MONEY_SCALED, ''].join('\n');
}

describe('e2e/dashboard-report.json — the gallery dashboard fixture against the API schema', () => {
    const fixture: unknown = JSON.parse(readFileSync(FIXTURE, 'utf8'));
    const committed = check(fixture);

    it('is checked against the schema zodios applies to POST /api/v1/portfolio/report', () => {
        const route = api.api.find((endpoint) => endpoint.method === 'post' && endpoint.path === '/api/v1/portfolio/report');

        expect(route?.response === schemas.PortfolioReportResponse, 'POST /api/v1/portfolio/report is gone from the generated client, or no longer validated with schemas.PortfolioReportResponse: point this guard at the schema the route uses now, or it checks one the app never applies.').toBe(true);
    });

    it('parses with schemas.PortfolioReportResponse', () => {
        const message = [
            '',
            'e2e/dashboard-report.json no longer matches schemas.PortfolioReportResponse: zodios rejects the whole mocked report, and every gallery dashboard shot is captured on an empty dashboard.',
            'Issues, as code at key path (values left out on purpose: the fixture is a real user snapshot):',
            ...committed.problems.map((line) => `    ${line}`),
            '',
            ...WHAT_TO_DO,
            '',
        ].join('\n');

        expect(committed.problems, message).toEqual([]);
    });

    it('still holds, once parsed, the sections the gallery dashboard shots draw from', () => {
        if (!committed.parsed.success) throw new Error('e2e/dashboard-report.json does not parse (see the test above): what it holds is moot until it does.');
        const report = committed.parsed.data;
        const empty = GALLERY_SECTIONS.filter((path) => countAt(report, path) === 0).map((path) => path.join('.'));
        const message = ['', 'e2e/dashboard-report.json parses, but these sections are missing or empty once validated — the gallery shots built on them would be captured empty:', ...empty.map((section) => `    ${section}`), '', ...WHAT_TO_DO, ''].join('\n');

        expect(empty, message).toEqual([]);
    });

    it('goes red without yield_on_cost on one holding — the 09-11 drift, replayed in memory', () => {
        const copy = structuredClone(fixture);
        const holdings = nodeAt(copy, ['summary', 'holdings']);
        const holding = Array.isArray(holdings) ? holdings.find((candidate) => isRecord(candidate) && 'yield_on_cost' in candidate) : undefined;
        // A control that removes nothing proves nothing.
        if (!isRecord(holding)) throw new Error('negative control: no holding in the fixture carries yield_on_cost, so there is nothing to remove');
        delete holding.yield_on_cost;

        expect(check(copy).problems).toEqual(['invalid_union at summary', '  invalid_type at summary.holdings[*].yield_on_cost']);
    });

    it('goes red without summary.net_worth', () => {
        const copy = structuredClone(fixture);
        const summary = nodeAt(copy, ['summary']);
        if (!isRecord(summary) || !('net_worth' in summary)) throw new Error('negative control: the fixture has no summary.net_worth to remove');
        delete summary.net_worth;

        expect(check(copy).problems).toEqual(['invalid_union at summary', '  invalid_type at summary.net_worth']);
    });
});

describe('e2e/dashboard-report.json — anonymized by scaling its money, and nothing else (lot I-M30)', () => {
    const fixture: unknown = JSON.parse(readFileSync(FIXTURE, 'utf8'));

    it('keeps every allocation list summing to 100: a share is not money', () => {
        const problems = shareProblems(fixture);

        expect(problems, relationMessage('allocation shares that no longer sum to 100', problems)).toEqual([]);
    });

    it('keeps every available yield on cost equal to gross income per unit over WAC: a yield is not money', () => {
        const problems = yieldOnCostProblems(fixture);

        expect(problems, relationMessage('available yields on cost that are no longer gross_income_per_unit / wac_per_unit', problems)).toEqual([]);
    });

    it('keeps every market-price change a hundredth of its daily percent: a price change is not money', () => {
        const problems = priceChange1dProblems(fixture);

        expect(problems, relationMessage('market-price changes that no longer match gain_loss_change_1d_percent', problems)).toEqual([]);
    });

    it('accepts every allocation list rewritten from its amounts, and refuses one summary list scaled by 0.9', () => {
        const copy = structuredClone(fixture);
        for (const list of allocationLists(copy)) {
            if (!Array.isArray(list) || shareVerdict(list) === 'skip') continue;
            const total = sumOf(list, 'amount');
            for (const item of list) if (isRecord(item)) item.value = ((toNumber(item.amount) / total) * 100).toFixed(2);
        }
        expect(shareProblems(copy), 'every list rewritten as the backend writes it must pass: the check is wrong on the real shapes').toEqual([]);

        const dim = DIMENSIONS.find((candidate) => shareVerdict(nodeAt(copy, ['summary', `allocation_by_${candidate}`])) === 'ok');
        const list = dim === undefined ? undefined : nodeAt(copy, ['summary', `allocation_by_${dim}`]);
        // A control that mutates nothing proves nothing.
        if (dim === undefined || !Array.isArray(list)) throw new Error('negative control: no summary allocation list is both non-empty and worth more than zero, so there is nothing to mutate');
        for (const item of list) if (isRecord(item)) item.value = String(toNumber(item.value) * 0.9);
        const problems = shareProblems(copy);

        expect(problems).toEqual([`summary.allocation_by_${dim}: does not sum to 100`]);
        expect(problems.filter((line) => /\d\.\d/.test(line))).toEqual([]);
    });

    it('accepts every available yield on cost rewritten as gross over WAC, and refuses one doubled', () => {
        const copy = structuredClone(fixture);
        const available = (holdingsOf(copy) ?? []).filter(isAvailableYieldOnCost);
        for (const holding of available) {
            const yieldOnCost = holding.yield_on_cost;
            if (isRecord(yieldOnCost)) yieldOnCost.value = String(expectedYieldOnCost(holding));
        }
        expect(yieldOnCostProblems(copy), 'every available value rewritten as the backend computes it must pass: the check is wrong on the real shapes').toEqual([]);

        const target = available.find((holding) => Number.isFinite(expectedYieldOnCost(holding)) && expectedYieldOnCost(holding) !== 0);
        const yieldOnCost = target?.yield_on_cost;
        // A control that mutates nothing proves nothing.
        if (target === undefined || !isRecord(yieldOnCost)) throw new Error('negative control: no available yield on cost has a finite, nonzero gross income over WAC, so there is nothing to double');
        yieldOnCost.value = String(2 * expectedYieldOnCost(target));
        const problems = yieldOnCostProblems(copy);

        expect(problems).toEqual([`summary.holdings[*].yield_on_cost: 1 of ${available.length} available values differ from gross_income_per_unit / wac_per_unit`]);
        expect(problems.filter((line) => /\d\.\d/.test(line))).toEqual([]);
    });

    it('accepts every market-price change rewritten as a hundredth of its percent, and refuses one a point off', () => {
        const copy = structuredClone(fixture);
        const compared = (holdingsOf(copy) ?? []).filter(isComparedPriceChange);
        for (const holding of compared) holding.price_change_1d = String(toNumber(holding.gain_loss_change_1d_percent) / 100);
        expect(priceChange1dProblems(copy), 'every compared change rewritten as a hundredth of its percent must pass: the check is wrong on the real shapes').toEqual([]);

        const target = compared[0];
        // A control that mutates nothing proves nothing.
        if (target === undefined) throw new Error('negative control: no holding at market price carries both price_change_1d and gain_loss_change_1d_percent, so there is nothing to mutate');
        target.price_change_1d = String(Math.abs(toNumber(target.gain_loss_change_1d_percent)) / 100 + 0.01);
        const problems = priceChange1dProblems(copy);

        expect(problems).toEqual([`summary.holdings[*].price_change_1d: 1 of ${compared.length} market-price changes differ from gain_loss_change_1d_percent / 100`]);
        expect(problems.filter((line) => /\d\.\d/.test(line))).toEqual([]);
    });
});
