/**
 * FB-15 — the rolling return of the ticked positions, the third view of the positions chart (Abs / % / Rolling).
 *
 * The chart compares positions by the percent their asset's PRICE moved over a window that rolls along the period (the backend's
 * `ASSET_CALENDAR_ROLLING_RETURN` signal, the one the Assets cards and pages draw), so assets of different sizes can be read side by side.
 * It is per asset, not per position: two brokers holding the same asset have the same line.
 *
 * What is pinned: the request (window, period), the line a view becomes, and the controller (asks once, keeps the newest answer, says
 * when it fails).
 */
import {describe, expect, it, vi} from 'vitest';
import {CALENDAR_RETURN_INSTANCE_ID, CALENDAR_RETURN_SIGNAL_CODE, emptyCalendarReturnView, type CalendarReturnView} from '$lib/components/charts/priceChartHelpers';
import {buildRollingQuery, createPositionsRollingController, rollingLine, rollingAutoPreset, rollingScopeKey, rollingWindowDays, type RollingScope} from './positionsRolling';

const SCOPE: RollingScope = {start: '2026-01-01', end: '2026-10-29', ready: true};

/** What the signal sends for an asset: one series of dated points, each with the provenance the reader checks. */
function item(assetId: number, points: Array<[string, number | null]>) {
    return {
        asset_id: assetId,
        signals: [
            {
                instance_id: CALENDAR_RETURN_INSTANCE_ID,
                signal_code: CALENDAR_RETURN_SIGNAL_CODE,
                status: 'ok',
                series: [
                    {
                        key: 'calendar_return',
                        points: points.map(([date, value]) => ({
                            date,
                            value,
                            provenance: {
                                status: value === null ? 'missing_reference' : 'available',
                                reference_target_date: date,
                                current_price_date: date,
                                current_price_days_back: 0,
                                reference_price_date: value === null ? null : date,
                                reference_price_days_back: value === null ? null : 0,
                                current_fx_date: null,
                                current_fx_days_back: null,
                                reference_fx_date: null,
                                reference_fx_days_back: null,
                            },
                        })),
                    },
                ],
            },
        ],
    };
}

describe('rollingWindowDays — the largest window that fits the period on screen', () => {
    it.each([
        ['2026-10-01', '2026-10-29', 7],
        ['2026-08-01', '2026-10-29', 30],
        ['2026-04-01', '2026-10-29', 90],
        ['2025-01-01', '2026-10-29', 365],
        ['2026-10-28', '2026-10-29', 7],
    ])('%s → %s is a window of %i days (the smallest when none fits)', (start, end, days) => {
        expect(rollingWindowDays(start, end)).toBe(days);
    });
});

describe('buildRollingQuery', () => {
    it('asks the rolling return of each asset once, without prices, over the period, with the window of the period', () => {
        const items = buildRollingQuery([3, 3, 9], SCOPE);
        expect(items).toHaveLength(2);
        expect(items[0]).toEqual({
            asset_id: 3,
            date_range: {start: '2026-01-01', end: '2026-10-29'},
            include_price: false,
            include_events: false,
            signals: [{instance_id: CALENDAR_RETURN_INSTANCE_ID, signal_code: CALENDAR_RETURN_SIGNAL_CODE, params: {window_days: 90}}],
        });
        expect(items.map((entry) => entry.asset_id)).toEqual([3, 9]);
    });
});

describe('the window the user chose (F-2)', () => {
    it('rollingAutoPreset is the preset behind the automatic window: the largest that fits', () => {
        expect(rollingAutoPreset('2026-01-01', '2026-10-29')).toBe('3m');
        expect(rollingAutoPreset('2026-10-01', '2026-10-29')).toBe('1w');
        expect(rollingAutoPreset('2025-01-01', '2026-10-29')).toBe('1y');
    });

    it('without a choice the query keeps the automatic window; with one, the chosen days', () => {
        const auto = buildRollingQuery([3], SCOPE)[0].signals[0].params.window_days;
        expect(auto).toBe(rollingWindowDays(SCOPE.start!, SCOPE.end!));
        expect(buildRollingQuery([3], {...SCOPE, windowDays: 7})[0].signals[0].params.window_days).toBe(7);
        expect(buildRollingQuery([3], {...SCOPE, windowDays: 365})[0].signals[0].params.window_days).toBe(365);
    });

    it('the window is part of the question: another window is another scope key, no window is the automatic one', () => {
        expect(rollingScopeKey({...SCOPE, windowDays: 7})).not.toBe(rollingScopeKey(SCOPE));
        expect(rollingScopeKey({...SCOPE, windowDays: 7})).not.toBe(rollingScopeKey({...SCOPE, windowDays: 30}));
        expect(rollingScopeKey({...SCOPE, windowDays: undefined})).toBe(rollingScopeKey(SCOPE));
    });
});

describe('rollingLine — the percent of the price over the window, one point per day the signal sent', () => {
    const view = (state: CalendarReturnView['state'], points: Array<[string, number, boolean?]>): CalendarReturnView => ({
        state,
        points: points.map(([date, value, missing]) => ({date, value, ...(missing ? {missing: true} : {})})),
        contextByDate: new Map(),
        problem: null,
    });

    it('takes the values as they are (percentage points) and keeps the days without a value as gaps, never as zero', () => {
        const line = rollingLine(
            '3-1',
            'Asset 3 · Broker 1',
            view('partial', [
                ['2026-01-02', 1.5],
                ['2026-01-03', 0, true],
                ['2026-01-04', -2],
            ]),
        );
        expect(line.id).toBe('3-1');
        expect(line.label).toBe('Asset 3 · Broker 1');
        expect(line.kind).toBe('position');
        expect(line.points).toEqual([
            {date: '2026-01-02', value: 1.5},
            {date: '2026-01-03', value: null},
            {date: '2026-01-04', value: -2},
        ]);
        expect(line.complete, 'a view with a gap is not complete: the legend marks it').toBe(false);
    });

    it('a complete view is a complete line', () => {
        expect(rollingLine('3-1', 'A', view('ready', [['2026-01-02', 1]])).complete).toBe(true);
    });

    it('an unavailable or failed view has no points: the line is drawn empty and marked incomplete', () => {
        const line = rollingLine('3-1', 'A', emptyCalendarReturnView('unavailable'));
        expect(line.points).toEqual([]);
        expect(line.complete).toBe(false);
    });
});

describe('createPositionsRollingController', () => {
    const answerFor = (ids: number[]) => ({
        items: ids.map((id) =>
            item(id, [
                ['2026-01-02', id],
                ['2026-01-03', id + 0.5],
            ]),
        ),
    });
    type State = {views: Map<number, CalendarReturnView>; loading: boolean; failed: boolean};
    const fresh = (): State => ({views: new Map(), loading: false, failed: false});

    it('asks the assets once and keeps their views by asset', async () => {
        const fetcher = vi.fn(async (items: Array<{asset_id: number}>) => answerFor(items.map((entry) => entry.asset_id)));
        const controller = createPositionsRollingController(fetcher as never);
        let state = fresh();
        controller.subscribe((next) => (state = next));

        controller.request([3, 9], SCOPE);
        await vi.waitFor(() => expect(state.views.size).toBe(2));

        expect(fetcher).toHaveBeenCalledTimes(1);
        expect(state.views.get(3)?.points.map((point) => point.value)).toEqual([3, 3.5]);
        expect(state.loading).toBe(false);
        expect(state.failed).toBe(false);
    });

    it('asks nothing again for assets and a scope it already has; a new asset asks for the missing ones', async () => {
        const fetcher = vi.fn(async (items: Array<{asset_id: number}>) => answerFor(items.map((entry) => entry.asset_id)));
        const controller = createPositionsRollingController(fetcher as never);
        let state = fresh();
        controller.subscribe((next) => (state = next));

        controller.request([3], SCOPE);
        await vi.waitFor(() => expect(state.views.size).toBe(1));
        controller.request([3], SCOPE);
        expect(fetcher).toHaveBeenCalledTimes(1);

        controller.request([3, 9], SCOPE);
        await vi.waitFor(() => expect(state.views.size).toBe(2));
        expect(fetcher).toHaveBeenCalledTimes(2);
        expect(
            fetcher.mock.calls[1][0].map((entry) => entry.asset_id),
            'only the asset it lacks',
        ).toEqual([9]);
    });

    it('a new scope (another period, a Refresh) asks again for everything ticked', async () => {
        const fetcher = vi.fn(async (items: Array<{asset_id: number}>) => answerFor(items.map((entry) => entry.asset_id)));
        const controller = createPositionsRollingController(fetcher as never);
        controller.request([3], SCOPE);
        await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));

        controller.sync({...SCOPE, start: '2026-06-01'});
        await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
        expect((fetcher.mock.calls[1][0] as unknown as Array<{date_range: {start: string}}>)[0].date_range.start).toBe('2026-06-01');
        expect(rollingScopeKey({...SCOPE, version: 1})).not.toBe(rollingScopeKey(SCOPE));
    });

    it('a new window asks again for everything ticked, with that window', async () => {
        const fetcher = vi.fn(async (items: Array<{asset_id: number}>) => answerFor(items.map((entry) => entry.asset_id)));
        const controller = createPositionsRollingController(fetcher as never);
        controller.request([3, 9], SCOPE);
        await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));

        // The page's sync (the user picked 1W): the views are another question's, so both assets are asked again.
        controller.sync({...SCOPE, windowDays: 7});
        await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
        const asked = fetcher.mock.calls[1][0] as unknown as Array<{asset_id: number; signals: Array<{params: {window_days: number}}>}>;
        expect(asked.map((entry) => entry.asset_id)).toEqual([3, 9]);
        expect(asked[0].signals[0].params.window_days).toBe(7);

        // The same window again: nothing new to ask.
        controller.sync({...SCOPE, windowDays: 7});
        expect(fetcher).toHaveBeenCalledTimes(2);
    });

    it('says when the request failed, and asks again at the next call', async () => {
        const fetcher = vi
            .fn()
            .mockRejectedValueOnce(new Error('boom'))
            .mockImplementation(async (items: Array<{asset_id: number}>) => answerFor(items.map((entry) => entry.asset_id)));
        const controller = createPositionsRollingController(fetcher as never);
        let state = fresh();
        controller.subscribe((next) => (state = next));

        controller.request([3], SCOPE);
        await vi.waitFor(() => expect(state.failed).toBe(true));
        controller.request([3], SCOPE);
        await vi.waitFor(() => expect(state.views.size).toBe(1));
        expect(state.failed).toBe(false);
    });

    it('does not ask before the page is ready, nor for no asset', async () => {
        const fetcher = vi.fn(async () => ({items: []}));
        const controller = createPositionsRollingController(fetcher as never);
        controller.request([3], {...SCOPE, ready: false});
        controller.request([], SCOPE);
        await Promise.resolve();
        expect(fetcher).not.toHaveBeenCalled();
    });

    it('a late answer of a disposed controller is dropped', async () => {
        let release!: () => void;
        const fetcher = vi.fn(async () => {
            await new Promise<void>((resolve) => (release = resolve));
            return answerFor([3]);
        });
        const controller = createPositionsRollingController(fetcher as never);
        let state = fresh();
        controller.subscribe((next) => (state = next));
        controller.request([3], SCOPE);
        controller.dispose();
        release();
        await new Promise((resolve) => setTimeout(resolve, 0));
        expect(state.views.size).toBe(0);
    });
});
