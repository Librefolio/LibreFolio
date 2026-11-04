/**
 * The rolling return of the ticked positions (FB-15): the third view of the positions chart, beside Abs and %.
 *
 * Abs and % read each position's own P&L; to compare positions with each other the developer asked for something else too (testlist,
 * 28/10): the percent the asset's PRICE moved over a window that rolls along the period. That is the signal the Assets cards and pages
 * already draw, `ASSET_CALENDAR_ROLLING_RETURN`, asked from the same bulk price query with no prices in the answer. It is per asset, not
 * per position: two brokers holding the same asset have the same line. The portfolio has no price, so the portfolio line is not drawn in
 * this view.
 *
 * It computes nothing: the window is the largest preset that fits the period (as the Assets list's «auto»), the values are the
 * backend's percentage points, and a day without a value stays a gap.
 *
 * It is a Svelte store (`subscribe`), like `positionsSeriesController`, so that the broker's legacy-mode page follows it too.
 *
 * @module features/dashboard/positionsRolling
 */

import {writable, type Readable} from 'svelte/store';
import {zodiosApi} from '$lib/api';
import {calendarReturnRangeDays, calendarReturnWindowDays, DEFAULT_CALENDAR_RETURN_WINDOW, largestCalendarReturnPresetFor} from '$lib/components/charts/calendarReturnWindow';
import {CALENDAR_RETURN_INSTANCE_ID, CALENDAR_RETURN_SIGNAL_CODE, extractCalendarReturnViewsByAsset, type CalendarReturnView} from '$lib/components/charts/priceChartHelpers';
import type {PositionLine} from './positionsSeries';

/** The period the rolling return is asked for: the page's own. */
export interface RollingScope {
    start?: string;
    end?: string;
    /** False while the page cannot ask yet: nothing goes out. */
    ready: boolean;
    /** Bumped by the page when its figures are asked again (Refresh, a price catch-up): the views follow. */
    version?: number;
}

/** One item of `POST /assets/prices/query`, as this view asks it. */
export interface RollingQueryItem {
    asset_id: number;
    date_range: {start: string; end: string};
    include_price: false;
    include_events: false;
    signals: Array<{instance_id: string; signal_code: string; params: {window_days: number}}>;
}

export type RollingFetcher = (items: RollingQueryItem[]) => Promise<{items?: unknown[]}>;

const defaultFetcher: RollingFetcher = async (items) => (await zodiosApi.query_prices_bulk_api_v1_assets_prices_query_post(items as never)) as {items?: unknown[]};

/** The window of the period on screen: the largest preset that fits it, the smallest when none does. */
export function rollingWindowDays(start: string, end: string): number {
    const preset = largestCalendarReturnPresetFor(calendarReturnRangeDays(start, end));
    return calendarReturnWindowDays({...DEFAULT_CALENDAR_RETURN_WINDOW, kind: 'preset', preset}) ?? 30;
}

/** The request: each asset once, its rolling return over the period, no prices. */
export function buildRollingQuery(assetIds: ReadonlyArray<number>, scope: RollingScope): RollingQueryItem[] {
    const start = scope.start ?? '';
    const end = scope.end ?? '';
    const windowDays = rollingWindowDays(start, end);
    return [...new Set(assetIds)].map((asset_id) => ({
        asset_id,
        date_range: {start, end},
        include_price: false,
        include_events: false,
        signals: [{instance_id: CALENDAR_RETURN_INSTANCE_ID, signal_code: CALENDAR_RETURN_SIGNAL_CODE, params: {window_days: windowDays}}],
    }));
}

/** Two scopes are the same question when this is equal. */
export function rollingScopeKey(scope: RollingScope): string {
    return [scope.start ?? '', scope.end ?? '', scope.version ?? 0].join('|');
}

/**
 * The line of a position in the Rolling view: its asset's rolling return, in percentage points. A day without a value is a gap, never a zero.
 * A view with a gap, or one the backend could not give, is marked incomplete in the legend.
 */
export function rollingLine(id: string, label: string, view: CalendarReturnView): PositionLine {
    return {
        id,
        label,
        points: view.points.map((point) => ({date: point.date, value: point.missing ? null : point.value})),
        closedOn: null,
        complete: view.state === 'ready',
        kind: 'position',
    };
}

/** What the panel shows: the views by asset, whether a request is on its way, whether the last one failed. */
export interface PositionsRollingState {
    views: Map<number, CalendarReturnView>;
    loading: boolean;
    failed: boolean;
}

export interface PositionsRollingController extends Readable<PositionsRollingState> {
    /** The Rolling view needs these assets (the panel's `onRequestPositionsRolling`). */
    request(assetIds: ReadonlyArray<number>, scope: RollingScope): void;
    /** The page's scope may have changed: ask again for the wanted assets if the views are another scope's. */
    sync(scope: RollingScope): void;
    /** The page is gone: a late answer is dropped. */
    dispose(): void;
}

export function createPositionsRollingController(fetcher: RollingFetcher = defaultFetcher): PositionsRollingController {
    const state = writable<PositionsRollingState>({views: new Map(), loading: false, failed: false});
    const patch = (change: Partial<PositionsRollingState>) => state.update((current) => ({...current, ...change}));

    let wanted: number[] = [];
    // What the views on screen answer: their scope, and the assets they hold. A new scope forgets them.
    let held: {scope: string; ids: Set<number>} | null = null;
    let sequence = 0;
    let disposed = false;

    async function ask(scope: RollingScope, ids: number[]): Promise<void> {
        if (!scope.ready || ids.length === 0 || disposed) return;
        const mine = ++sequence;
        const key = rollingScopeKey(scope);
        patch({loading: true, failed: false});
        try {
            const answer = await fetcher(buildRollingQuery(ids, scope));
            if (disposed || mine !== sequence) return;
            const fresh = extractCalendarReturnViewsByAsset(answer.items ?? [], ids);
            const keep = held && held.scope === key ? held.ids : new Set<number>();
            held = {scope: key, ids: new Set([...keep, ...ids])};
            state.update((current) => ({...current, views: new Map([...(keep.size > 0 ? current.views : new Map()), ...fresh])}));
        } catch {
            if (disposed || mine !== sequence) return;
            patch({failed: true});
        } finally {
            if (!disposed && mine === sequence) patch({loading: false});
        }
    }

    /** The assets the views on screen do not answer for this scope. */
    function missing(scope: RollingScope): number[] {
        if (!held || held.scope !== rollingScopeKey(scope)) return wanted;
        return wanted.filter((id) => !held!.ids.has(id));
    }

    return {
        subscribe: state.subscribe,
        request(assetIds, scope) {
            wanted = [...new Set(assetIds)];
            void ask(scope, missing(scope));
        },
        sync(scope) {
            void ask(scope, missing(scope));
        },
        dispose() {
            disposed = true;
            sequence += 1;
        },
    };
}
