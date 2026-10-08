/**
 * Guard: the gallery's dashboard fixture still matches the API schema (workstream M, round R12).
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
 *   a guard that checks nothing reports.
 *
 * ## What it does not
 *
 * It reads the committed file as is: `gallery.spec.ts` shifts its `YYYY-MM-DD` dates before serving
 * it, which changes no key and no type. Whether the dashboard draws valid data correctly is the
 * gallery's question, not this one.
 *
 * ## When it goes red
 *
 * Rule 12 — a captured fixture that fails the schema is a STOP, not an edit. Ask the developer for a
 * fresh capture, normalize it with `./dev.py mkdocs normalize-dashboard-fixture`, and never edit the
 * fixture by hand. The failure message says the same.
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
