// @vitest-environment jsdom
/**
 * TxBulkBanners — the «fill from price history» banner (project 79, STK-4b). Component test (Vitest + jsdom).
 *
 * The Bulk editor hands the banner the number of rows still waiting for a value on receipt (`rewardFillPending`: an open
 * `reward_value` todo and no value), whether a fill is running (`rewardFillRunning`) and the last outcome
 * (`rewardFillResult`: counts and `failed`). The contract:
 *
 *   - nothing pending and no outcome: no banner;
 *   - the banner `tx-bulk-reward-fill` is an info InfoBanner publishing `data-pending` (the rows) and `data-state`
 *     (`idle` | `running`); while rows are pending it says how many and offers `tx-bulk-reward-fill-button`, which calls
 *     `onRewardFill` and is disabled while a fill runs (its label then the «running» one);
 *   - an outcome is `tx-bulk-reward-fill-result` with `data-filled`, `data-no-price`, `data-no-history`, `data-failed`, worded
 *     by the `result` key with those counts, or the `failed` key; it stays shown once nothing is pending any more.
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

const KEY = 'transactions.bulk.rewardFill';
const jumpToTodoRow = vi.fn<(rowId: string) => void>();
const onRewardFill = vi.fn<() => void>();

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
    onRewardFill.mockReset();
});

const RESULT = {filled: 3, noPrice: 1, noHistory: 2, failed: false};

describe('TxBulkBanners — the «fill from price history» banner', () => {
    it('is not drawn with nothing pending and no outcome', () => {
        mountBanners({rewardFillPending: 0, rewardFillResult: null, onRewardFill});
        expect(screen.queryByTestId('tx-bulk-reward-fill')).toBeNull();
    });

    it('is not drawn when the props are left out', () => {
        mountBanners();
        expect(screen.queryByTestId('tx-bulk-reward-fill')).toBeNull();
    });

    it('with rows pending: an info banner with their count, idle, and the button', () => {
        mountBanners({rewardFillPending: 2, onRewardFill});

        const banner = screen.getByTestId('tx-bulk-reward-fill');
        expect(banner.closest('[data-testid="info-banner-info"]'), 'an InfoBanner, info').not.toBeNull();
        expect(banner).toHaveAttribute('data-pending', '2');
        expect(banner).toHaveAttribute('data-state', 'idle');
        expect(banner.textContent ?? '').toContain(`${KEY}.pending(n=2)`);
        const button = within(banner).getByTestId('tx-bulk-reward-fill-button');
        expect(button).toBeEnabled();
        expect(button.textContent?.trim()).toBe(`${KEY}.button`);
        expect(within(banner).queryByTestId('tx-bulk-reward-fill-result'), 'no outcome yet').toBeNull();
    });

    it('the button calls onRewardFill, once per click', async () => {
        mountBanners({rewardFillPending: 1, onRewardFill});

        await fireEvent.click(screen.getByTestId('tx-bulk-reward-fill-button'));

        expect(onRewardFill).toHaveBeenCalledTimes(1);
    });

    // Only `disabled` is asserted: a synthetic click in jsdom reaches Svelte's delegated handler even on a disabled button,
    // which a browser never dispatches; the editor also ignores a second fill while one runs (fillRewardsFromHistory).
    it('while a fill runs: data-state running, the button disabled with the running label', () => {
        mountBanners({rewardFillPending: 2, rewardFillRunning: true, onRewardFill});

        const banner = screen.getByTestId('tx-bulk-reward-fill');
        expect(banner).toHaveAttribute('data-state', 'running');
        const button = within(banner).getByTestId('tx-bulk-reward-fill-button');
        expect(button).toBeDisabled();
        expect(button.textContent?.trim()).toBe(`${KEY}.running`);
    });

    it('an outcome publishes its counts and is worded by the result key', () => {
        mountBanners({rewardFillPending: 3, rewardFillResult: RESULT, onRewardFill});

        const result = screen.getByTestId('tx-bulk-reward-fill-result');
        expect(result).toHaveAttribute('data-filled', '3');
        expect(result).toHaveAttribute('data-no-price', '1');
        expect(result).toHaveAttribute('data-no-history', '2');
        expect(result).toHaveAttribute('data-failed', 'false');
        expect(result.textContent?.trim()).toBe(`${KEY}.result(filled=3, noHistory=2, noPrice=1)`);
        expect(screen.getByTestId('tx-bulk-reward-fill-button'), 'rows still pending: the button stays').toBeInTheDocument();
    });

    it('with nothing pending any more the outcome stays, without the button', () => {
        mountBanners({rewardFillPending: 0, rewardFillResult: {filled: 2, noPrice: 0, noHistory: 0, failed: false}, onRewardFill});

        const banner = screen.getByTestId('tx-bulk-reward-fill');
        expect(banner).toHaveAttribute('data-pending', '0');
        expect(within(banner).getByTestId('tx-bulk-reward-fill-result')).toHaveAttribute('data-filled', '2');
        expect(within(banner).queryByTestId('tx-bulk-reward-fill-button')).toBeNull();
        expect(banner.textContent ?? '').not.toContain(`${KEY}.pending`);
    });

    it('a failed read is worded by the failed key and says so in data-failed', () => {
        mountBanners({rewardFillPending: 2, rewardFillResult: {filled: 0, noPrice: 0, noHistory: 0, failed: true}, onRewardFill});

        const result = screen.getByTestId('tx-bulk-reward-fill-result');
        expect(result).toHaveAttribute('data-failed', 'true');
        expect(result.textContent?.trim()).toBe(`${KEY}.failed`);
    });
});
