// @vitest-environment jsdom
/**
 * TxBulkBanners — the «possible stock split» banner (W-B87). Component test (Vitest + jsdom).
 *
 * The Bulk editor hands an import's stock splits to this banner as `possibleSplitEntries` (bulkTodos.ts), one per ADJUSTMENT row
 * still waiting for its SPLIT event, and three handlers:
 *
 *   possibleSplitEntries — the rows; none: no banner at all
 *   onSplitCreate(entry) — «create the SPLIT event and link it» of a row
 *   onSplitLink(tempId, eventId) — «link an existing event» of a row, the row named by its tempId
 *   jumpToTodoRow(rowId) — the banner's own «go to the row», already a prop of the banner (it is passed to each row as onGoto)
 *
 * With one entry or more the banner is `tx-bulk-possible-split` (an InfoBanner, warning): a title (key
 * `transactions.bulk.possibleSplit.title`, plural on `n` = how many rows), the explanation (key `...explain`) and one
 * `possible-split-row` per entry, in order. The generic «fields to verify» banner (`tx-bulk-todo-warnings`) is not this one's
 * business: the editor hands it lists already filtered, and this test proves the banner itself neither counts nor lists the
 * split todos when the generic count is 0 — and that the generic banner is still drawn for what is its own.
 *
 * Text. `$lib/i18n` is a key echo (`key(name=value)`), so titles and sentences are proved by their key and the values they
 * were given, never by a translation. Controls by `data-testid`. The inline picker of a row is the shared stand-in
 * `$test/harness/AssetEventPickerStub.svelte` (it answers event 555). The network is the inert Proxy the other transaction
 * component tests use: nothing is fetched for real.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import type {ComponentProps} from 'svelte';
import {readable, writable} from 'svelte/store';
import {fireEvent, render, screen, within} from '$test/component';

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
vi.mock('$lib/features/transactions/events/AssetEventPicker.svelte', async () => ({default: (await import('$test/harness/AssetEventPickerStub.svelte')).default}));

import TxBulkBanners from './TxBulkBanners.svelte';
import type {PossibleSplitEntry} from './bulkTodos';

const PICKED_EVENT_ID = 555;
const KEY = 'transactions.bulk.possibleSplit';

function entryOf(overrides: Partial<PossibleSplitEntry> = {}): PossibleSplitEntry {
    return {
        tempId: 'tmp-a',
        rowId: 'tmp-a',
        rowNumber: '3',
        assetId: 7,
        date: '2022-08-25',
        ticker: 'TSLA',
        addedQuantity: '0.16431924',
        isin: null,
        ratio: null,
        suggestedRatio: null,
        roundingDelta: null,
        heldBefore: null,
        ...overrides,
    };
}

const onSplitCreate = vi.fn<(entry: PossibleSplitEntry) => void>();
const onSplitLink = vi.fn<(tempId: string, eventId: number) => void>();
const jumpToTodoRow = vi.fn<(rowId: string) => void>();

/** Every prop the banners ask for, at its quiet value: nothing to say, nothing open. */
function bannerProps(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        commitFailed: false,
        formError: null,
        fxMarketCache: new Map(),
        issues: [],
        issuesDismissed: false,
        lastDraftKey: '',
        lastIssueDraftKey: '',
        ops: [],
        promoteAllOpen: false,
        promoteBannerSeen: false,
        syncFxLoading: false,
        tableRef: undefined,
        todoBlockersExpanded: false,
        todoWarningsExpanded: true,
        allSuggestions: [],
        balanceIssues: [],
        bannerSuggestions: [],
        fieldIssues: [],
        hasPairedDelete: false,
        hasWacFxIssues: false,
        mergeAllPairs: [],
        resolverCtx: {},
        showIssuesBanner: false,
        todoBlockerEntries: [],
        todoWarningEntries: [],
        todoWarningRowCount: 0,
        visibleOps: [],
        AUTO_VALIDATE_THRESHOLD: 50,
        bulkDisplayText: (_key: string, fallback: string) => fallback,
        getIssueRows: () => [],
        getVisualRowLabel: () => '',
        handleSyncFx: async () => {},
        issueRowsLabel: () => '',
        jumpToIssue: () => {},
        jumpToTodoRow,
        triggerPromoteFromSuggestion: () => {},
        possibleSplitEntries: [],
        onSplitCreate,
        onSplitLink,
        ...overrides,
    };
}

function mountBanners(overrides: Record<string, unknown> = {}) {
    return render(TxBulkBanners, {props: bannerProps(overrides) as unknown as ComponentProps<typeof TxBulkBanners>});
}

beforeEach(() => {
    onSplitCreate.mockReset();
    onSplitLink.mockReset();
    jumpToTodoRow.mockReset();
});

describe('TxBulkBanners — the possible-split banner', () => {
    it('is not drawn when there is no entry', () => {
        mountBanners({possibleSplitEntries: []});

        expect(screen.queryByTestId('tx-bulk-possible-split')).toBeNull();
        expect(screen.queryByTestId('possible-split-row')).toBeNull();
    });

    it('is a warning banner with a title, an explanation and one row, for one entry', () => {
        mountBanners({possibleSplitEntries: [entryOf()]});

        const banner = screen.getByTestId('tx-bulk-possible-split');
        // The banner's testid sits on the InfoBanner's content or on a wrapper around it: either way it is the warning variant.
        expect(banner.closest('[data-testid="info-banner-warning"]') ?? banner.querySelector('[data-testid="info-banner-warning"]'), 'an InfoBanner, warning').not.toBeNull();
        expect(banner.textContent ?? '', 'title, plural on the number of rows').toContain(`${KEY}.title(n=1)`);
        expect(banner.textContent ?? '').toContain(`${KEY}.explain`);
        expect(within(banner).getAllByTestId('possible-split-row')).toHaveLength(1);
    });

    it('counts the rows in its title and draws one row per entry, in order', () => {
        mountBanners({possibleSplitEntries: [entryOf({tempId: 'tmp-a', rowId: 'tmp-a', ticker: 'AAA'}), entryOf({tempId: 'tmp-b', rowId: 'tmp-b-shown', ticker: 'BBB'}), entryOf({tempId: 'tmp-c', rowId: 'tmp-c', ticker: 'CCC'})]});

        const banner = screen.getByTestId('tx-bulk-possible-split');
        expect(banner.textContent ?? '').toContain(`${KEY}.title(n=3)`);
        const rows = within(banner).getAllByTestId('possible-split-row');
        expect(rows.map((row) => row.getAttribute('data-row-id'))).toEqual(['tmp-a', 'tmp-b-shown', 'tmp-c']);
        expect(rows.map((row) => /AAA|BBB|CCC/.exec(row.textContent ?? '')?.[0])).toEqual(['AAA', 'BBB', 'CCC']);
    });

    it("the banner goto is the editor's jumpToTodoRow, called with the visible row", async () => {
        mountBanners({possibleSplitEntries: [entryOf({tempId: 'hidden', rowId: 'shown'})]});

        await fireEvent.click(screen.getByTestId('possible-split-goto'));

        expect(jumpToTodoRow).toHaveBeenCalledExactlyOnceWith('shown');
    });

    it('«create» of a row hands that entry to onSplitCreate', async () => {
        const first = entryOf({tempId: 'tmp-a', rowId: 'tmp-a', ticker: 'AAA'});
        const second = entryOf({tempId: 'tmp-b', rowId: 'tmp-b', ticker: 'BBB', suggestedRatio: '3'});
        mountBanners({possibleSplitEntries: [first, second]});
        const rowOfSecond = screen.getAllByTestId('possible-split-row').find((row) => row.getAttribute('data-row-id') === 'tmp-b')!;

        await fireEvent.click(within(rowOfSecond).getByTestId('possible-split-create'));

        expect(onSplitCreate).toHaveBeenCalledExactlyOnceWith(second);
    });

    it('an event picked on a row is linked to that row, named by its tempId, not by its visible row', async () => {
        mountBanners({possibleSplitEntries: [entryOf({tempId: 'tmp-a', rowId: 'tmp-a'}), entryOf({tempId: 'hidden-half', rowId: 'shown-half'})]});
        const row = screen.getAllByTestId('possible-split-row').find((candidate) => candidate.getAttribute('data-row-id') === 'shown-half')!;

        await fireEvent.click(within(row).getByTestId('possible-split-link'));
        await fireEvent.click(within(row).getByTestId('event-picker-stub-pick'));

        expect(onSplitLink).toHaveBeenCalledExactlyOnceWith('hidden-half', PICKED_EVENT_ID);
        expect(onSplitCreate).not.toHaveBeenCalled();
    });

    it('a row whose asset is not resolved offers neither action, only the line that says why', () => {
        mountBanners({possibleSplitEntries: [entryOf({assetId: null})]});

        expect(screen.queryByTestId('possible-split-create')).toBeNull();
        expect(screen.queryByTestId('possible-split-link')).toBeNull();
        expect(screen.getByTestId('possible-split-asset-needed')).toBeInTheDocument();
    });
});

describe('TxBulkBanners — the generic «fields to verify» banner is not the split banner', () => {
    it('with todoWarningRowCount 0 it is not drawn, whatever the split banner holds', () => {
        mountBanners({possibleSplitEntries: [entryOf()], todoWarningRowCount: 0, todoWarningEntries: []});

        expect(screen.getByTestId('tx-bulk-possible-split')).toBeInTheDocument();
        expect(screen.queryByTestId('tx-bulk-todo-warnings')).toBeNull();
    });

    // Guard, green today: the generic banner is still drawn for what is its own.
    it('guard: is drawn, and lists its own entries, when other rows have warnings and no row waits for a split', () => {
        const generic = {rowId: 'other-row', rowNumber: '9', todo: {field: 'description', severity: 'warning' as const, reasonCode: 'probe_other', message: 'Invented other todo'}};
        mountBanners({possibleSplitEntries: [], todoWarningRowCount: 1, todoWarningEntries: [generic]});

        const warnings = screen.getByTestId('tx-bulk-todo-warnings');
        expect(
            within(warnings)
                .getAllByTestId('tx-bulk-todo-goto')
                .map((goto) => goto.getAttribute('data-row-id')),
        ).toEqual(['other-row']);
        expect(warnings.textContent ?? '', 'its count is the generic one').toContain('importWizard.todoWarningVerifyHint(n=1)');
        expect(screen.queryByTestId('tx-bulk-possible-split')).toBeNull();
    });

    it('both banners side by side: the generic one lists its own rows only, the split one its own', () => {
        const generic = {rowId: 'other-row', rowNumber: '9', todo: {field: 'description', severity: 'warning' as const, reasonCode: 'probe_other', message: 'Invented other todo'}};
        mountBanners({possibleSplitEntries: [entryOf({tempId: 'tmp-a', rowId: 'tmp-a'})], todoWarningRowCount: 1, todoWarningEntries: [generic]});

        const warnings = screen.getByTestId('tx-bulk-todo-warnings');
        expect(
            within(warnings)
                .getAllByTestId('tx-bulk-todo-goto')
                .map((goto) => goto.getAttribute('data-row-id')),
        ).toEqual(['other-row']);
        expect(warnings.textContent ?? '', 'its count is the generic one').toContain('importWizard.todoWarningVerifyHint(n=1)');
        expect(within(screen.getByTestId('tx-bulk-possible-split')).getAllByTestId('possible-split-row')).toHaveLength(1);
    });
});
