// @vitest-environment jsdom
/**
 * AnalyzeStep — the notices tile of step 3's summary counts the warnings and the notes apart (lot B-51). Component test
 * (Vitest + jsdom).
 *
 * Under the results of step 3 the summary had one tile for a BRIM plugin's notices: «N warnings», amber when N > 0, N
 * being every notice — the blue notes (`info`) included. A Fineco file whose only notice is a note read «1 warning».
 * The cure (plan 04, B-51): the wizard's `parseAggregateStats()` gives `totalWarnings` (the warnings alone) and
 * `totalNotes`, and the tile draws the two with NoticeCounts. Pinned here:
 *
 *   the tile `import-wizard-stat-notices` holds one `notice-counts`, data-warnings = totalWarnings and data-notes =
 *     totalNotes; inside it the warning count and the note count, each with its data-count and data-zero (the rest of
 *     NoticeCounts' contract is `NoticeCounts.test.ts`'s). Two cases: (0, 1) — the Fineco case, one note and no warning:
 *     the warning count is a zero, data-zero="true" — and (3, 2);
 *   the tile belongs to the summary, which shows only once a file has been analysed: with `parseHasSuccess` false there
 *     is no tile (guard: true before B-51 too, read after a barrier that the step itself is mounted).
 *
 * The step is mounted alone, with the wizard's props reduced to the minimum: no results (a table with one inert column
 * and no row — DataTable never settles with no column at all, see ONE_COLUMN) and a `parseAggregateStats` returning
 * fixed totals. The wizard's own sums are not under test here, only what the step draws from them. Nothing reads
 * translated text nor a CSS class: testids, data attributes and the numbers passed in.
 *
 * The step is loaded once, in a `beforeAll` with its own budget (its first transform is cold); a load failure fails each
 * case on its own, saying so. Every API method is inert: the results table reaches the auth store (user-scoped storage
 * keys), which imports the API client; nothing here calls it.
 *
 * Registered in `scripts/test_runner/_frontend_transaction.py`, in the Vitest list of `front_tx_unit` (action
 * `front-transaction tx-unit`).
 *
 * Plan: `LibreFolio_developer_journal/Release_2/Phase_1/04_importTransactions/plan-phase01ImportTransactions.prompt.md`,
 * section «B-51».
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import type {Component} from 'svelte';

vi.mock('$lib/api', async () => {
    const generated = await vi.importActual<{schemas: unknown}>('$lib/api/generated');
    const inert = new Proxy(
        {},
        {
            get(_target, property) {
                if (typeof property !== 'string' || property === 'then') return undefined;
                return vi.fn(async () => undefined);
            },
        },
    );
    class ApiError extends Error {}
    return {zodiosApi: inert, axiosInstance: inert, ApiError, schemas: generated.schemas};
});

import {render, screen, setupI18n} from '$test/component';

// ---------------------------------------------------------------------------
// Loading the component under test
// ---------------------------------------------------------------------------

// A lazy glob rather than a literal import: the first transform of the step is cold, and here it runs in a hook with
// its own budget instead of inside the first test's.
const STEP_MODULES = import.meta.glob<{default: Component<Record<string, unknown>>}>('./AnalyzeStep.svelte');

let loaded: {AnalyzeStep: Component<Record<string, unknown>>} | {error: unknown} | undefined;

beforeAll(async () => {
    try {
        const load = STEP_MODULES['./AnalyzeStep.svelte'];
        if (!load) throw new Error('AnalyzeStep.svelte cannot be found next to this test');
        loaded = {AnalyzeStep: (await load()).default};
    } catch (error) {
        loaded = {error};
    }
}, 60_000);

beforeAll(async () => {
    await setupI18n();
});

function analyzeStep(): Component<Record<string, unknown>> {
    if (loaded === undefined) throw new Error('the component under test was never loaded: its beforeAll did not run');
    if ('error' in loaded) {
        const {error} = loaded;
        throw new Error(error instanceof Error ? error.message : String(error), {cause: error});
    }
    return loaded.AnalyzeStep;
}

// ---------------------------------------------------------------------------
// Fixtures: the wizard's props, reduced to the minimum
// ---------------------------------------------------------------------------

/** What the wizard's `parseAggregateStats()` returns: one file analysed, nothing else to say but the notice totals. */
function stats(totalWarnings: number, totalNotes: number) {
    return {totalTx: 0, doneFileCount: 1, uniqueAssets: 0, unresolvedCount: 0, totalWarnings, totalNotes, totalIssues: 0, totalTodos: 0, todoBlockers: 0, likelyDuplicates: 0};
}

/**
 * One inert column for the results table, which renders no row here. With none, DataTable never settles: its
 * column-order effect («initial fallback», for an empty order) writes a fresh `[]` and `{}` on every run when there is
 * no column at all — Svelte's effect_update_depth_exceeded. The wizard always has columns; the table is not under test.
 */
const ONE_COLUMN = [{id: 'probeFileName', header: 'probe', cell: (row: {fileName: string}) => row.fileName, type: 'text'}];

/** One file analysed, the parse over: the props of the wizard, `overrides` on top. */
function stepProps(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        parseResults: [],
        step3Columns: ONE_COLUMN,
        step3RowActions: [],
        parseHasSuccess: true,
        parseDone: true,
        usingCachedResults: false,
        candidatesRefreshing: false,
        duplicateRecheckRunning: false,
        parseCompletedCount: 1,
        parseTotalCount: 1,
        parseFailures: [],
        parseHasErrors: false,
        parseState: 'ok',
        showAggregateDetail: false,
        parseAggregateStats: () => stats(0, 0),
        handleReparse: vi.fn(),
        openParseDetail: vi.fn(),
        ...overrides,
    };
}

// ---------------------------------------------------------------------------
// Mounting and reading
// ---------------------------------------------------------------------------

/** Mount the step; returns its root once it is there. */
async function mountStep(overrides: Record<string, unknown> = {}): Promise<HTMLElement> {
    render(analyzeStep(), stepProps(overrides));
    return screen.findByTestId('import-wizard-step3');
}

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

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

/** (label, totalWarnings, totalNotes). */
const TOTALS: readonly [label: string, warnings: number, notes: number][] = [
    ['the Fineco case — one note, no warning', 0, 1],
    ['three warnings and two notes', 3, 2],
];

describe('AnalyzeStep — B-51: the notices tile counts the warnings and the notes apart', () => {
    it('with a file analysed and the parse over, the summary is there: view all and re-analyse (guard: true before B-51 too)', async () => {
        await mountStep();

        the('import-wizard-view-all');
        the('import-wizard-reparse');
    });

    it.each(TOTALS)('%s: the tile holds one notice-counts carrying both totals', async (_label, warnings, notes) => {
        await mountStep({parseAggregateStats: () => stats(warnings, notes)});

        const tile = the('import-wizard-stat-notices');
        const counts = the('notice-counts', {}, tile);
        expect(counts).toHaveAttribute('data-warnings', String(warnings));
        expect(counts).toHaveAttribute('data-notes', String(notes));
    });

    it.each(TOTALS)('%s: the warning count and the note count, each with its number and its zero flag', async (_label, warnings, notes) => {
        await mountStep({parseAggregateStats: () => stats(warnings, notes)});

        const tile = the('import-wizard-stat-notices');
        const warningCount = the('notice-count', {severity: 'warning'}, tile);
        expect(warningCount).toHaveAttribute('data-count', String(warnings));
        expect(warningCount, 'no warning is a zero, not a warning').toHaveAttribute('data-zero', String(warnings === 0));
        const noteCount = the('notice-count', {severity: 'info'}, tile);
        expect(noteCount).toHaveAttribute('data-count', String(notes));
        expect(noteCount).toHaveAttribute('data-zero', String(notes === 0));
    });

    it('no file analysed: no summary, so no notices tile (guard: true before B-51 too)', async () => {
        const step = await mountStep({parseHasSuccess: false, parseState: 'error', parseAggregateStats: () => stats(3, 2)});

        expect(step, 'presence barrier: the step is drawn, in the state it was given').toHaveAttribute('data-parse-state', 'error');
        expect(all('import-wizard-stat-notices')).toHaveLength(0);
        expect(all('notice-counts')).toHaveLength(0);
        expect(all('import-wizard-view-all'), 'the summary as a whole is absent').toHaveLength(0);
    });
});
