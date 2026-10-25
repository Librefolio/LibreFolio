// @vitest-environment jsdom
/**
 * ReviewStep — the «date before 1900» note of the import wizard's last step (D-P4, W5-10). Component test (Vitest + jsdom).
 *
 * The merge (`importMerge.ts`) puts a warning todo `{field: 'date', reasonCode: 'date_before_1900'}` on every row dated
 * before 1900. The review step shows `import-review-pre-floor-note` (an InfoBanner, warning) with `data-count` = the
 * number of SELECTED rows that carry it, worded by `importWizard.reviewPreFloorNote` (n = the same number); none: no note.
 * A row left out of the import does not count, another todo on `date` does not count, a row with the todo twice is one.
 * The rows that carry the todo are tinted through `getRowClass`: the table is a stand-in that publishes what the step
 * answers per row (`data-row-class`), compared between rows, never named.
 *
 * Text: `$lib/i18n` is a key echo (`key(name=value)`), so the note is proved by its key and number.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import type {ComponentProps} from 'svelte';
import {readable, writable} from 'svelte/store';
import {cleanup, render, screen} from '$test/component';

vi.mock('$lib/i18n', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/i18n')>();
    const shown = (key: string, options?: {values?: Record<string, unknown>}) => {
        const values = options?.values;
        if (!values) return key;
        const listed = Object.keys(values)
            .sort()
            .map((name) => `${name}=${String(values[name])}`);
        return `${key}(${listed.join(', ')})`;
    };
    const translator = readable(shown);
    return {...actual, _: translator, t: translator, locale: writable('en')};
});
vi.mock('$lib/api', () => {
    const cache = new Map<string, ReturnType<typeof vi.fn>>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_t, prop: string) {
                if (!cache.has(prop))
                    cache.set(
                        prop,
                        vi.fn(async () => undefined),
                    );
                return cache.get(prop);
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});
vi.mock('$lib/components/table/DataTable.svelte', async () => ({default: (await import('$test/harness/DataTableRowClassStub.svelte')).default}));
vi.mock('$lib/components/table/ColumnVisibilityToggle.svelte', async () => ({default: (await import('$test/harness/DataTableStub.svelte')).default}));

import ReviewStep from './ReviewStep.svelte';
import type {MergedTx} from './importTypes';
import {withPreFloorDateTodo} from '$lib/features/transactions/preFloorDate';

const NOTE = 'importWizard.reviewPreFloorNote';

type Todo = MergedTx['todos'][number];

function todo(field: string, reasonCode: string): Todo {
    return {field, severity: 'warning', reasonCode, message: `Invented ${reasonCode}`};
}

/** The todo the merge puts on a row dated before 1900, built by the real helper. */
const PRE_FLOOR_TODO = withPreFloorDateTodo([], '1850-05-01')[0];

function row(index: number, overrides: Partial<MergedTx> = {}): MergedTx {
    return {
        index,
        sourceFileId: 'file-1',
        tx: {broker_id: 1, type: 'BUY', date: '2024-03-10', asset_id: 5, quantity: '1', tags: [], description: `Invented row ${index}`} as MergedTx['tx'],
        selected: true,
        duplicateStatus: 'unique',
        dupMatches: [],
        todos: [],
        ...overrides,
    } as MergedTx;
}

function stepProps(step4Rows: MergedTx[]): Record<string, unknown> {
    const selected = step4Rows.filter((r) => r.selected).length;
    return {
        assetResolutions: [],
        autoFixingBrokerId: null,
        candidatesRefreshing: false,
        duplicateRecheckError: null,
        duplicateRecheckRunning: false,
        importPreparing: false,
        inspectAssetLoading: false,
        recheckingOpenings: false,
        showBeforeHistory: false,
        step4ShowResolveSection: true,
        step4TableRef: undefined,
        brokerOpeningIssues: [],
        step4BeforeHistoryCount: 0,
        step4BeforeOpeningCount: 0,
        step4Columns: [],
        step4DeselectDbDup: 0,
        step4DeselectPendingDup: 0,
        step4HasDeselectReasons: false,
        step4MissingAssetCount: 0,
        step4Rows,
        step4SelectedCount: selected,
        step4SelectedDuplicateCount: 0,
        step4TotalCount: step4Rows.length,
        step4UnresolvedCount: 0,
        autoFixBrokerOpening: vi.fn(),
        clearResolution: vi.fn(),
        confidenceBadgeClass: () => '',
        openAssetInspector: vi.fn(),
        openBrokerOpeningEditById: vi.fn(),
        openMergeFromCard: vi.fn(),
        recheckOpenings: vi.fn(),
        resolveAssetManual: vi.fn(),
        startCreateAsset: vi.fn(),
        step4DeselectAll: vi.fn(),
        step4SelectAll: vi.fn(),
        step4SelectVisible: vi.fn(),
    };
}

function mountReview(rows: MergedTx[]) {
    return render(ReviewStep, {props: stepProps(rows) as unknown as ComponentProps<typeof ReviewStep>});
}

/** What the step answers to `getRowClass` for each row, in the order of the rows. */
const rowClasses = (): Array<string | null> => screen.queryAllByTestId('data-table-row-stub').map((stub) => stub.getAttribute('data-row-class'));

afterEach(() => {
    cleanup();
});

describe('ReviewStep — the date-before-1900 note', () => {
    it('is not drawn when no row carries the todo, nor for no rows', () => {
        mountReview([row(0), row(1, {todos: [todo('date', 'something_else')]})]);
        expect(screen.getByTestId('import-wizard-step4'), 'premise: the review is on screen').toBeInTheDocument();
        expect(screen.queryByTestId('import-review-pre-floor-note')).toBeNull();
        cleanup();

        mountReview([]);
        expect(screen.getByTestId('import-wizard-step4')).toBeInTheDocument();
        expect(screen.queryByTestId('import-review-pre-floor-note')).toBeNull();
    });

    it('is a warning banner worded by its key, with n = 1 and data-count 1, for one selected row with the todo', () => {
        mountReview([row(0, {todos: [PRE_FLOOR_TODO]})]);

        const note = screen.getByTestId('import-review-pre-floor-note');
        expect(note).toHaveAttribute('data-count', '1');
        expect(note.querySelector('[data-testid="info-banner-warning"]') ?? note.closest('[data-testid="info-banner-warning"]'), 'an InfoBanner, warning').not.toBeNull();
        expect(note.textContent ?? '').toContain(`${NOTE}(n=1)`);
    });

    it('counts rows: two selected rows give 2, a row with the todo twice is one', () => {
        mountReview([row(0, {todos: [PRE_FLOOR_TODO]}), row(1, {todos: [PRE_FLOOR_TODO, PRE_FLOOR_TODO]}), row(2)]);

        const note = screen.getByTestId('import-review-pre-floor-note');
        expect(note).toHaveAttribute('data-count', '2');
        expect(note.textContent ?? '').toContain(`${NOTE}(n=2)`);
    });

    it('does not count a row left out of the import, and counts only the selected ones when some are left out', () => {
        mountReview([row(0, {todos: [PRE_FLOOR_TODO], selected: false})]);
        expect(screen.queryByTestId('import-review-pre-floor-note'), 'a row that is not imported asks nothing').toBeNull();
        cleanup();

        mountReview([row(0, {todos: [PRE_FLOOR_TODO]}), row(1, {todos: [PRE_FLOOR_TODO], selected: false})]);
        expect(screen.getByTestId('import-review-pre-floor-note')).toHaveAttribute('data-count', '1');
    });

    it('does not count another todo on the date, nor the same reason on another field', () => {
        mountReview([row(0, {todos: [todo('date', 'something_else')]}), row(1, {todos: [todo('quantity', 'date_before_1900')]})]);
        expect(screen.queryByTestId('import-review-pre-floor-note')).toBeNull();
    });

    it('does not draw the possible-split note for it: the two notes are independent', () => {
        mountReview([row(0, {todos: [PRE_FLOOR_TODO]})]);
        expect(screen.getByTestId('import-review-pre-floor-note')).toBeInTheDocument();
        expect(screen.queryByTestId('import-review-possible-split-note')).toBeNull();
    });
});

describe('ReviewStep — the rows dated before 1900 are tinted', () => {
    it('a row with the todo gets another row class than a plain one; two plain rows get the same', () => {
        mountReview([row(0), row(1, {todos: [PRE_FLOOR_TODO]}), row(2)]);

        const [plain, tinted, plainAgain] = rowClasses();
        expect(rowClasses(), 'premise: the stub holds the three rows').toHaveLength(3);
        expect(plain).toBe(plainAgain);
        expect(tinted).not.toBe(plain);
    });

    it('the tint follows the todo, not the selection: a left-out row with the todo is tinted too, and differs from a plain left-out one', () => {
        mountReview([row(0, {selected: false}), row(1, {selected: false, todos: [PRE_FLOOR_TODO]})]);

        const [plainOut, tintedOut] = rowClasses();
        expect(tintedOut).not.toBe(plainOut);
    });

    it('another todo does not tint', () => {
        mountReview([row(0), row(1, {todos: [todo('date', 'something_else')]})]);

        const [plain, other] = rowClasses();
        expect(other).toBe(plain);
    });
});
