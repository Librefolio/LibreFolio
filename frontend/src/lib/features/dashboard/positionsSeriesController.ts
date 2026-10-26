/**
 * The daily series of the positions the user ticked, asked once for a page (Y5-2, #48).
 *
 * The Dashboard and a broker's page both show `PositionsPanel` and give it the same four things: the answer of
 * `POST /portfolio/positions-series`, whether it is on its way, whether it failed, and a function to ask for the ticked
 * positions. This controller is that, for one scope (brokers, period, currency): it asks, keeps the newest answer and
 * forgets a late one, and asks again only when the scope or the ticked set is not covered by what it already has.
 *
 * It computes nothing: every figure of a series is the backend's.
 *
 * It is a Svelte store (`subscribe`), not rune state: the broker's page is a legacy-mode component, which does not follow
 * a rune read through a getter, but follows `$controller` in both modes.
 *
 * @module features/dashboard/positionsSeriesController
 */

import {writable, type Readable} from 'svelte/store';
import {zodiosApi} from '$lib/api';
import {positionLineId, type PositionKey, type PositionsSeriesQuery, type PositionsSeriesResponse} from './positionsSeries';

/** What a page's report is asked for: the series is asked for the same scope, so the lines and the rest agree. */
export interface PositionsSeriesScope {
    /** The brokers of the scope; none or empty = every broker the user can read, as the report. */
    brokerIds?: ReadonlyArray<number>;
    start?: string;
    end?: string;
    currency?: string;
    /** False while the page cannot ask yet (the brokers are not known): nothing goes out. */
    ready: boolean;
    /** Bumped by the page when its figures are asked again (Refresh, a price catch-up): the series follows. */
    version?: number;
}

export type PositionsSeriesFetcher = (body: PositionsSeriesQuery) => Promise<PositionsSeriesResponse>;

const defaultFetcher: PositionsSeriesFetcher = (body) => zodiosApi.get_positions_series_api_v1_portfolio_positions_series_post(body);

/** The body of the request: the report's scope, plus the positions. */
export function buildPositionsSeriesQuery(keys: ReadonlyArray<PositionKey>, scope: PositionsSeriesScope): PositionsSeriesQuery {
    const body: PositionsSeriesQuery = {positions: keys.map((key) => ({asset_id: key.asset_id, broker_id: Array.isArray(key.broker_id) ? (key.broker_id[0] ?? null) : (key.broker_id ?? null)}))};
    if (scope.brokerIds && scope.brokerIds.length > 0) body.broker_ids = [...scope.brokerIds];
    if (scope.start || scope.end) body.date_range = {...(scope.start ? {start: scope.start} : {}), ...(scope.end ? {end: scope.end} : {})};
    if (scope.currency) body.target_currency = scope.currency;
    return body;
}

/** Two scopes are the same question when this is equal. */
export function positionsSeriesScopeKey(scope: PositionsSeriesScope): string {
    return [scope.brokerIds ? [...scope.brokerIds].sort((a, b) => a - b).join(',') : '', scope.start ?? '', scope.end ?? '', scope.currency ?? '', scope.version ?? 0].join('|');
}

/** What the panel shows: the newest answer, whether a request is on its way, whether the last one failed. */
export interface PositionsSeriesState {
    response: PositionsSeriesResponse | null;
    loading: boolean;
    failed: boolean;
}

export interface PositionsSeriesController extends Readable<PositionsSeriesState> {
    /** The user ticked these positions (the panel's `onRequestPositionsSeries`). */
    request(keys: PositionKey[], scope: PositionsSeriesScope): void;
    /** The page's scope may have changed: ask again for the ticked positions if the answer is another scope's. */
    sync(scope: PositionsSeriesScope): void;
    /** The page is gone: a late answer is dropped. */
    dispose(): void;
}

export function createPositionsSeriesController(fetcher: PositionsSeriesFetcher = defaultFetcher): PositionsSeriesController {
    const state = writable<PositionsSeriesState>({response: null, loading: false, failed: false});
    const patch = (change: Partial<PositionsSeriesState>) => state.update((current) => ({...current, ...change}));

    let wanted: PositionKey[] = [];
    // What was asked last and has not failed: in flight or on screen. A failure forgets it, so the next call asks again.
    let asked: {scope: string; ids: Set<string>} | null = null;
    let sequence = 0;
    let disposed = false;

    async function ask(scope: PositionsSeriesScope): Promise<void> {
        if (!scope.ready || wanted.length === 0 || disposed) return;
        const keys = wanted;
        const mine = ++sequence;
        asked = {scope: positionsSeriesScopeKey(scope), ids: new Set(keys.map(positionLineId))};
        patch({loading: true, failed: false});
        try {
            const answer = await fetcher(buildPositionsSeriesQuery(keys, scope));
            if (disposed || mine !== sequence) return;
            patch({response: answer});
        } catch {
            if (disposed || mine !== sequence) return;
            asked = null;
            patch({failed: true});
        } finally {
            if (!disposed && mine === sequence) patch({loading: false});
        }
    }

    /** Whether what is on screen, or on its way, already answers the ticked positions for this scope. */
    function covered(scope: PositionsSeriesScope): boolean {
        return asked !== null && asked.scope === positionsSeriesScopeKey(scope) && wanted.every((key) => asked!.ids.has(positionLineId(key)));
    }

    return {
        subscribe: state.subscribe,
        /** The user ticked these positions (the panel's `onRequestPositionsSeries`). */
        request(keys: PositionKey[], scope: PositionsSeriesScope): void {
            wanted = keys;
            if (covered(scope)) return;
            void ask(scope);
        },
        /** The page's scope may have changed: ask again for the ticked positions if the answer is another scope's. */
        sync(scope: PositionsSeriesScope): void {
            if (wanted.length === 0 || covered(scope)) return;
            void ask(scope);
        },
        /** The page is gone: a late answer is dropped. */
        dispose(): void {
            disposed = true;
            sequence += 1;
        },
    };
}
