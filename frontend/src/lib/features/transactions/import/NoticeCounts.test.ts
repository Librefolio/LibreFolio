// @vitest-environment jsdom
/**
 * NoticeCounts — a parse's notices as two numbers, the warnings and the notes (lot B-51). Component test
 * (Vitest + jsdom).
 *
 * Step 3 of the import wizard counted a BRIM plugin's blue notes as amber warnings: one number, «⚠️ 1» for a Fineco file
 * whose only notice is a note. The cure shows two numbers wherever the step counts notices — the results column, through
 * `noticeCountsCell` (`importNotices.test.ts`), and the stats tile (`AnalyzeStep.test.ts`) — and both draw them with this
 * component. Its contract (plan 04, B-51):
 *
 *   props `warnings` and `notes` (numbers), `size` ('sm' | 'lg', 'sm' when absent);
 *   root `notice-counts` — data-warnings and data-notes: the two numbers, as strings;
 *   inside it, exactly two `notice-count`, in reading order: data-severity="warning" first, then data-severity="info";
 *     each with data-count (its number) and data-zero ("true" when the count is 0, else "false");
 *     its text shows its number; its icon is one <svg>, aria-hidden="true" — decoration: the number is what is read.
 *   The size changes how big, never what: every case runs at the default size, at 'sm' and at 'lg'.
 *
 * The colours are the design system's (a count in its role's colour, a zero muted) and are not read here: data-zero is
 * the contract that says which state a count is in. Nothing reads translated text either: a count's text is only
 * searched for the number the test passed in, as a whole number (a 0 that is not the 0 of a 10).
 *
 * Written red-first, before `NoticeCounts.svelte` exists: it is loaded lazily through `import.meta.glob` in a
 * `beforeAll` with its own budget (a component's first transform is cold), so every case fails on its own, naming the
 * missing component, instead of the whole file failing at collection.
 *
 * Registered in `scripts/test_runner/_frontend_transaction.py`, in the Vitest list of `front_tx_unit` (action
 * `front-transaction tx-unit`).
 *
 * Plan: `LibreFolio_developer_journal/Release_2/Phase_1/04_importTransactions/plan-phase01ImportTransactions.prompt.md`,
 * section «B-51».
 */
import {beforeAll, describe, expect, it} from 'vitest';
import type {Component} from 'svelte';
import {render, setupI18n} from '$test/component';

// ---------------------------------------------------------------------------
// Loading the component under test
// ---------------------------------------------------------------------------

// A lazy glob rather than a literal import: the component does not exist yet, and a missing file must fail each case on
// its own, naming it, instead of failing the whole file at collection.
const COUNTS_MODULES = import.meta.glob<{default: Component<Record<string, unknown>>}>('./NoticeCounts.svelte');

let loaded: {NoticeCounts: Component<Record<string, unknown>>} | {error: unknown} | undefined;

beforeAll(async () => {
    try {
        const load = COUNTS_MODULES['./NoticeCounts.svelte'];
        if (!load) throw new Error('NoticeCounts.svelte cannot be found next to this test (src/lib/features/transactions/import/)');
        loaded = {NoticeCounts: (await load()).default};
    } catch (error) {
        loaded = {error};
    }
}, 60_000);

beforeAll(async () => {
    // A count may name itself for screen readers: the i18n store must be up before the first mount.
    await setupI18n();
});

function noticeCounts(): Component<Record<string, unknown>> {
    if (loaded === undefined) throw new Error('the component under test was never loaded: its beforeAll did not run');
    if ('error' in loaded) {
        const {error} = loaded;
        throw new Error(error instanceof Error ? error.message : String(error), {cause: error});
    }
    return loaded.NoticeCounts;
}

// ---------------------------------------------------------------------------
// Mounting and reading
// ---------------------------------------------------------------------------

/** The one element with this testid and these data attributes; anything else fails with what was there. */
function the(testId: string, attributes: Record<string, string> = {}, scope: ParentNode = document): HTMLElement {
    const selector = `[data-testid="${testId}"]${Object.entries(attributes)
        .map(([name, value]) => `[data-${name}="${value}"]`)
        .join('')}`;
    const found = [...scope.querySelectorAll<HTMLElement>(selector)];
    if (found.length !== 1) {
        const present = [...scope.querySelectorAll<HTMLElement>(`[data-testid="${testId}"]`)].map((el) => ({...el.dataset}));
        throw new Error(`expected exactly one ${selector}, found ${found.length}; the ${testId} elements present: ${JSON.stringify(present)}`);
    }
    return found[0];
}

function all(testId: string, scope: ParentNode = document): HTMLElement[] {
    return [...scope.querySelectorAll<HTMLElement>(`[data-testid="${testId}"]`)];
}

/** Text as a reader sees it: whitespace runs collapsed. */
function text(el: Element): string {
    return (el.textContent ?? '').replace(/\s+/g, ' ').trim();
}

/** The number as a whole: a 0 that is not the 0 of a 10, a 2 that is not the 2 of a 12. */
function wholeNumber(n: number): RegExp {
    return new RegExp(`(?<!\\d)${n}(?!\\d)`);
}

/** Mount the counts and return their root, read once it is there. */
function mount(warnings: number, notes: number, sizeProps: Record<string, unknown>): HTMLElement {
    render(noticeCounts(), {warnings, notes, ...sizeProps});
    return the('notice-counts');
}

/** The count of one kind, inside the root. */
function countOf(root: HTMLElement, severity: 'warning' | 'info'): HTMLElement {
    return the('notice-count', {severity}, root);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

/** (warnings, notes): both non-zero, a zero warning count beside notes (the Fineco shape), and nothing at all. */
const CASES: readonly [warnings: number, notes: number][] = [
    [2, 1],
    [0, 3],
    [0, 0],
];

const SIZES: readonly [label: string, sizeProps: Record<string, unknown>][] = [
    ['at the default size', {}],
    ["at size 'sm'", {size: 'sm'}],
    ["at size 'lg'", {size: 'lg'}],
];

describe.each(SIZES)('NoticeCounts %s — the same contract', (_size, sizeProps) => {
    it.each(CASES)('warnings %i, notes %i: the root carries both numbers', (warnings, notes) => {
        const root = mount(warnings, notes, sizeProps);

        expect(root).toHaveAttribute('data-warnings', String(warnings));
        expect(root).toHaveAttribute('data-notes', String(notes));
    });

    it.each(CASES)('warnings %i, notes %i: two counts, the warnings first, each with its number and its zero flag', (warnings, notes) => {
        const root = mount(warnings, notes, sizeProps);

        const counts = all('notice-count', root).map((count) => ({severity: count.dataset.severity, count: count.dataset.count, zero: count.dataset.zero}));
        expect(counts).toEqual([
            {severity: 'warning', count: String(warnings), zero: String(warnings === 0)},
            {severity: 'info', count: String(notes), zero: String(notes === 0)},
        ]);
        expect(all('notice-count'), 'no count outside the root').toHaveLength(2);
    });

    it.each(CASES)('warnings %i, notes %i: each count shows its number', (warnings, notes) => {
        const root = mount(warnings, notes, sizeProps);

        expect(text(countOf(root, 'warning')), 'the warning count').toMatch(wholeNumber(warnings));
        expect(text(countOf(root, 'info')), 'the note count').toMatch(wholeNumber(notes));
    });

    it.each(CASES)('warnings %i, notes %i: each count has one icon, an <svg> hidden from screen readers', (warnings, notes) => {
        const root = mount(warnings, notes, sizeProps);

        for (const severity of ['warning', 'info'] as const) {
            const icons = [...countOf(root, severity).querySelectorAll('svg')];
            expect(icons, `the ${severity} count: one icon`).toHaveLength(1);
            expect(icons[0], `the ${severity} count: its icon is decoration`).toHaveAttribute('aria-hidden', 'true');
        }
    });
});
