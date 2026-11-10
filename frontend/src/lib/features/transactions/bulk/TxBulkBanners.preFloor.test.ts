// @vitest-environment jsdom
/**
 * TxBulkBanners — the «date before 1900» banner (D-P4, W5-10). Component test (Vitest + jsdom).
 *
 * The Bulk editor hands the rows dated before 1900 (`preFloorEntries`, built by `preFloorEntries()` in
 * `preFloorDate.ts`) to the banner: none, no banner; otherwise `tx-bulk-pre-floor` (`data-count` = the rows) with one
 * `tx-bulk-pre-floor-row` per entry, in order, carrying `data-row-id` (the row to show) and `data-date`. Clicking a
 * line is the editor's `jumpToTodoRow` with that row. The banner is not the generic «fields to verify» banner.
 *
 * Text: `$lib/i18n` is a key echo, so a line is proved by its key and values. Controls by `data-testid`.
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

import TxBulkBanners from './TxBulkBanners.svelte';
import type {PreFloorEntry} from '$lib/features/transactions/preFloorDate';

const KEY = 'transactions.bulk.preFloorDate';
const jumpToTodoRow = vi.fn<(rowId: string) => void>();

function entryOf(overrides: Partial<PreFloorEntry> = {}): PreFloorEntry {
    return {tempId: 'tmp-a', rowId: 'tmp-a', rowNumber: '3', date: '1850-05-01', ...overrides};
}

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
        onSplitCreate: () => {},
        onSplitLink: () => {},
        ...overrides,
    };
}

function mountBanners(overrides: Record<string, unknown> = {}) {
    return render(TxBulkBanners, {props: bannerProps(overrides) as unknown as ComponentProps<typeof TxBulkBanners>});
}

beforeEach(() => {
    jumpToTodoRow.mockReset();
});

describe('TxBulkBanners — the date-before-1900 banner', () => {
    it('is not drawn when there is no entry', () => {
        mountBanners({preFloorEntries: []});
        expect(screen.queryByTestId('tx-bulk-pre-floor')).toBeNull();
        expect(screen.queryByTestId('tx-bulk-pre-floor-row')).toBeNull();
    });

    it('is not drawn when the prop is left out', () => {
        const props = bannerProps();
        delete props.preFloorEntries;
        render(TxBulkBanners, {props: props as unknown as ComponentProps<typeof TxBulkBanners>});
        expect(screen.queryByTestId('tx-bulk-pre-floor')).toBeNull();
    });

    it('is a warning banner with its count and one line for one entry', () => {
        mountBanners({preFloorEntries: [entryOf()]});

        const banner = screen.getByTestId('tx-bulk-pre-floor');
        expect(banner.closest('[data-testid="info-banner-warning"]'), 'an InfoBanner, warning').not.toBeNull();
        expect(banner).toHaveAttribute('data-count', '1');
        expect(banner.textContent ?? '').toContain(`${KEY}.message(n=1)`);
        expect(within(banner).getAllByTestId('tx-bulk-pre-floor-row')).toHaveLength(1);
    });

    it('draws one line per entry, in order, with the row to show and the date as attributes and the row and date as values of the line', () => {
        mountBanners({
            preFloorEntries: [entryOf({tempId: 'tmp-a', rowId: 'tmp-a', rowNumber: '2', date: '1850-05-01'}), entryOf({tempId: 'tmp-b', rowId: 'pair-shown', rowNumber: '5', date: '1024-03-10'}), entryOf({tempId: 'tmp-c', rowId: 'tmp-c', rowNumber: '9', date: '1899-12-31'})],
        });

        const banner = screen.getByTestId('tx-bulk-pre-floor');
        expect(banner).toHaveAttribute('data-count', '3');
        expect(banner.textContent ?? '').toContain(`${KEY}.message(n=3)`);
        const rows = within(banner).getAllByTestId('tx-bulk-pre-floor-row');
        expect(rows.map((row) => row.getAttribute('data-row-id'))).toEqual(['tmp-a', 'pair-shown', 'tmp-c']);
        expect(rows.map((row) => row.getAttribute('data-date'))).toEqual(['1850-05-01', '1024-03-10', '1899-12-31']);
        expect(rows.map((row) => row.textContent ?? '')).toEqual([`${KEY}.row(date=1850-05-01, row=2)`, `${KEY}.row(date=1024-03-10, row=5)`, `${KEY}.row(date=1899-12-31, row=9)`]);
    });

    it("clicking a line calls the editor's jumpToTodoRow with that line's row, once", async () => {
        mountBanners({preFloorEntries: [entryOf({tempId: 'tmp-a', rowId: 'tmp-a'}), entryOf({tempId: 'hidden', rowId: 'shown', date: '1851-01-01'})]});
        const line = screen.getAllByTestId('tx-bulk-pre-floor-row').find((row) => row.getAttribute('data-date') === '1851-01-01')!;

        await fireEvent.click(line);

        expect(jumpToTodoRow).toHaveBeenCalledExactlyOnceWith('shown');
    });

    it('is not the generic «fields to verify» banner: both side by side, each with its own rows', () => {
        const generic = {rowId: 'other-row', rowNumber: '9', todo: {field: 'description', severity: 'warning' as const, reasonCode: 'probe_other', message: 'Invented other todo'}};
        mountBanners({preFloorEntries: [entryOf()], todoWarningRowCount: 1, todoWarningEntries: [generic]});

        expect(within(screen.getByTestId('tx-bulk-pre-floor')).getAllByTestId('tx-bulk-pre-floor-row')).toHaveLength(1);
        expect(
            within(screen.getByTestId('tx-bulk-todo-warnings'))
                .getAllByTestId('tx-bulk-todo-goto')
                .map((goto) => goto.getAttribute('data-row-id')),
        ).toEqual(['other-row']);
    });

    it('with no generic warnings (todoWarningRowCount 0) the generic banner is not drawn beside it', () => {
        mountBanners({preFloorEntries: [entryOf()], todoWarningRowCount: 0});
        expect(screen.getByTestId('tx-bulk-pre-floor')).toBeInTheDocument();
        expect(screen.queryByTestId('tx-bulk-todo-warnings')).toBeNull();
    });
});
