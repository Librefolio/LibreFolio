// @vitest-environment jsdom
/**
 * ReviewStep — the «possible stock split» note of the import wizard's last step (W-B87). Component test (Vitest + jsdom).
 *
 * An importer enters a stock split as an incoming ADJUSTMENT and attaches a todo `{field: 'asset_event_id', reasonCode:
 * 'possible_split'}` to it. The wizard's review step cannot link the SPLIT event yet — the Bulk editor, the next screen, does —
 * so the review says it will: when a row that is going to be imported (`selected`) still carries such a todo, `ReviewStep`
 * draws an InfoBanner, variant info, `import-review-possible-split-note`, worded by `importWizard.reviewPossibleSplitNote`,
 * plural on `n` = the number of such rows. No such row: no banner. A row left out of the import, or a todo with another
 * reason on the same field, does not count; a row with several split todos is one row.
 *
 * The step is a controlled component: everything comes in as props, `step4Rows` (the `MergedTx` rows of the review, whose
 * `todos` carry `reasonCode`) being the one this test varies. The rest is quiet (nothing to resolve, no issues). Text:
 * `$lib/i18n` is a key echo (`key(name=value)`), so the note is proved by its key and the number it was given, never by a
 * translation. The table (and its column toggle) is a stand-in, `$test/harness/DataTableStub.svelte`: only the note is looked at.
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
vi.mock('$lib/components/table/DataTable.svelte', async () => ({default: (await import('$test/harness/DataTableStub.svelte')).default}));
vi.mock('$lib/components/table/ColumnVisibilityToggle.svelte', async () => ({default: (await import('$test/harness/DataTableStub.svelte')).default}));

import ReviewStep from './ReviewStep.svelte';
import type {MergedTx} from './importTypes';

const NOTE = 'importWizard.reviewPossibleSplitNote';

type Todo = MergedTx['todos'][number];

function todo(field: string, reasonCode: string): Todo {
    return {field, severity: 'warning', reasonCode, message: `Invented ${reasonCode}`};
}

const SPLIT_TODO = todo('asset_event_id', 'possible_split');

/** One review row, as the wizard builds it: an incoming ADJUSTMENT, selected unless said otherwise. */
function row(index: number, overrides: Partial<MergedTx> = {}): MergedTx {
    return {
        index,
        sourceFileId: 'file-1',
        tx: {broker_id: 1, type: 'ADJUSTMENT', date: '2022-08-25', asset_id: -1, quantity: '0.16431924', tags: [], description: `Invented split ${index}`} as MergedTx['tx'],
        selected: true,
        duplicateStatus: 'unique',
        dupMatches: [],
        todos: [],
        ...overrides,
    } as MergedTx;
}

/** Every prop of the step at its quiet value. */
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

afterEach(() => {
    cleanup();
});

describe('ReviewStep — the possible-split note', () => {
    it('is not drawn when no row carries the todo', () => {
        mountReview([row(0), row(1, {todos: [todo('cost_basis_override', 'corporate_action')]})]);

        expect(screen.getByTestId('import-wizard-step4'), 'premise: the review is on screen').toBeInTheDocument();
        expect(screen.queryByTestId('import-review-possible-split-note')).toBeNull();
    });

    it('is not drawn for no rows at all', () => {
        mountReview([]);

        expect(screen.getByTestId('import-wizard-step4')).toBeInTheDocument();
        expect(screen.queryByTestId('import-review-possible-split-note')).toBeNull();
    });

    it('is an info banner worded by its key, with n = 1, for one selected row with the todo', () => {
        mountReview([row(0, {todos: [SPLIT_TODO]})]);

        const note = screen.getByTestId('import-review-possible-split-note');
        // The note's testid sits on the InfoBanner's content or on a wrapper around it: either way the banner is the info variant.
        expect(note.closest('[data-testid="info-banner-info"]') ?? note.querySelector('[data-testid="info-banner-info"]'), 'an InfoBanner, variant info').not.toBeNull();
        expect(note.textContent ?? '').toContain(`${NOTE}(n=1)`);
    });

    it('counts rows: two selected rows with the todo give n = 2, a row with two split todos is one', () => {
        mountReview([row(0, {todos: [SPLIT_TODO]}), row(1, {todos: [SPLIT_TODO, SPLIT_TODO]}), row(2)]);

        expect(screen.getByTestId('import-review-possible-split-note').textContent ?? '').toContain(`${NOTE}(n=2)`);
    });

    it('does not count a row left out of the import', () => {
        mountReview([row(0, {todos: [SPLIT_TODO], selected: false})]);

        expect(screen.queryByTestId('import-review-possible-split-note'), 'a row that is not imported has no split to link').toBeNull();
    });

    it('counts only the selected rows when some are left out', () => {
        mountReview([row(0, {todos: [SPLIT_TODO]}), row(1, {todos: [SPLIT_TODO], selected: false})]);

        expect(screen.getByTestId('import-review-possible-split-note').textContent ?? '').toContain(`${NOTE}(n=1)`);
    });

    it('does not count another todo on the same field, nor the same reason on another field', () => {
        mountReview([row(0, {todos: [todo('asset_event_id', 'something_else')]}), row(1, {todos: [todo('cost_basis_override', 'possible_split')]})]);

        expect(screen.queryByTestId('import-review-possible-split-note')).toBeNull();
    });
});
