/**
 * «Updating prices…» while the server catches up on prices (release 1.3, workstream Z, lot Z5).
 *
 * At startup, at the first request after a silence and at a scheduled wake-up, the scheduler runs the jobs that are due
 * in the background. While such a catch-up is about to run or runs, every `/api/` response carries
 * `X-LibreFolio-Price-Refresh: starting|running`, and the response interceptor hands the headers to
 * `priceRefresh.observe`. From the first one, the tracker asks `GET /api/v1/system/price-refresh` every 3 s through
 * `startActivePolling` (so it pauses in a hidden tab and after two minutes without input, and waits longer after
 * failures), shows an `info` instance notice while a job runs, and when the catch-up is over hides it and, if it saw a
 * job run and the catch-up updated something, asks the portfolio views to refresh (`notifyPricesCaughtUp`: the caches
 * turn stale, and the Dashboard or a broker's page on screen reloads in background). Without the header it asks nothing:
 * an idle instance can still sleep.
 *
 * The pages without a session (an invitation, a password reset) get the header too. The question is asked with `fetch`,
 * not through the API client, whose error handler sends a 401 to the login page and would lose the link the page came
 * with; an answer 4xx ends the tracking and the headers are ignored until the next session reset (a sign-in).
 *
 * Usage (the interceptor, `lib/api/zodios-client.ts`):
 *   priceRefresh.observe(response.headers);
 *
 * @module lib/features/price-refresh/priceRefresh
 */

import {startActivePolling, type ActivePolling, type PollOutcome} from '$lib/features/live-updates/activePolling';
import type {InstanceNotice} from '$lib/features/instance/instanceNotices.svelte';
import {notifyPricesCaughtUp} from '$lib/stores/portfolio/portfolioMutation';
import {registerClientSessionReset} from '$lib/stores/app/clientSession';

/** The response header, as axios exposes it (lower case). */
export const PRICE_REFRESH_HEADER = 'x-librefolio-price-refresh';
export const PRICE_REFRESH_NOTICE_ID = 'liveUpdates.priceRefresh';
export const PRICE_REFRESH_MESSAGE_KEY = 'liveUpdates.priceRefresh.running';
/** The status route, asked with `fetch`. */
export const PRICE_REFRESH_STATUS_PATH = '/api/v1/system/price-refresh';
/** Between two questions while a catch-up is tracked. */
export const PRICE_REFRESH_POLL_MS = 3_000;
/** A catch-up that stays `starting` this many answers in a row is no longer tracked: its run never came. */
export const PRICE_REFRESH_MAX_STARTING_POLLS = 10;
/** This many failed questions in a row end the tracking, and the notice with it. */
export const PRICE_REFRESH_MAX_FAILURES = 5;

export type PriceRefreshState = 'idle' | 'starting' | 'running';

/** `GET /api/v1/system/price-refresh`. */
export interface PriceRefreshStatus {
    state: PriceRefreshState;
    reason: string | null;
    job: string | null;
    since: string | null;
    last_finished_at: string | null;
    last_refreshed: boolean;
}

export interface PriceRefreshDeps {
    fetchStatus: () => Promise<PriceRefreshStatus>;
    notices: {show(notice: InstanceNotice): void; hide(id: string): void};
    refreshPortfolio: () => void;
    startPolling: typeof startActivePolling;
}

export interface PriceRefreshTracker {
    /** The headers of a successful response: a catch-up starts the tracking, a running one shows the notice. */
    observe(headers: unknown): void;
    readonly tracking: boolean;
    readonly noticeShown: boolean;
    /** No more questions, and the notice hidden. */
    stop(): void;
    /** As `stop()`, and the headers heard again after a 4xx: for the session reset. */
    reset(): void;
}

const NOTICE: InstanceNotice = {id: PRICE_REFRESH_NOTICE_ID, severity: 'info', messageKey: PRICE_REFRESH_MESSAGE_KEY};

/** `starting` or `running` from the response's headers (axios `AxiosHeaders` or a plain object); null otherwise. */
export function readPriceRefreshHeader(headers: unknown): 'starting' | 'running' | null {
    if (headers === null || typeof headers !== 'object') return null;
    const source = headers as {get?: unknown} & Record<string, unknown>;
    const raw = typeof source.get === 'function' ? (source as {get: (name: string) => unknown}).get(PRICE_REFRESH_HEADER) : source[PRICE_REFRESH_HEADER];
    if (typeof raw !== 'string') return null;
    const value = raw.trim().toLowerCase();
    return value === 'starting' || value === 'running' ? value : null;
}

/** The status route answered with an HTTP error. */
export class PriceRefreshStatusError extends Error {
    constructor(readonly status: number) {
        super(`GET ${PRICE_REFRESH_STATUS_PATH} answered ${status}`);
        this.name = 'PriceRefreshStatusError';
    }
}

async function fetchStatusFromApi(): Promise<PriceRefreshStatus> {
    const response = await fetch(PRICE_REFRESH_STATUS_PATH, {credentials: 'same-origin', headers: {Accept: 'application/json'}});
    if (!response.ok) throw new PriceRefreshStatusError(response.status);
    return (await response.json()) as PriceRefreshStatus;
}

/** The HTTP status of a failed question: `PriceRefreshStatusError`, or an axios-like `response.status`; null otherwise. */
function httpStatusOf(error: unknown): number | null {
    if (error instanceof PriceRefreshStatusError) return error.status;
    const status = error !== null && typeof error === 'object' ? (error as {response?: {status?: unknown}}).response?.status : undefined;
    return typeof status === 'number' ? status : null;
}

/**
 * The app's notice area, loaded on first use (Z-20): imported statically, its runes would run wherever the API
 * client is imported, the AI Export probe's Node bridge included. One promise for every call, so a `hide` never
 * overtakes its `show`.
 */
let noticeArea: Promise<typeof import('$lib/features/instance/instanceNotices.svelte')> | null = null;

function loadNoticeArea(): Promise<typeof import('$lib/features/instance/instanceNotices.svelte')> {
    noticeArea ??= import('$lib/features/instance/instanceNotices.svelte');
    return noticeArea;
}

export function createPriceRefresh(deps: Partial<PriceRefreshDeps> = {}): PriceRefreshTracker {
    // The defaults are read when used, not when this module loads: the API client imports this module, and a test that
    // mocks one of these modules only in part (the client's own tests) must still load it.
    const fetchStatus = deps.fetchStatus ?? fetchStatusFromApi;
    const notices = deps.notices ?? {
        show: (notice: InstanceNotice) => void loadNoticeArea().then(({instanceNotices}) => instanceNotices.show(notice)),
        hide: (id: string) => void loadNoticeArea().then(({instanceNotices}) => instanceNotices.hide(id)),
    };
    const refreshPortfolio = deps.refreshPortfolio ?? (() => notifyPricesCaughtUp());
    const startPolling: typeof startActivePolling = deps.startPolling ?? ((options) => startActivePolling(options));

    let poller: ActivePolling | null = null;
    let noticeShown = false;
    /** A job of the tracked catch-up was seen running, by a header or by an answer. */
    let runningSeen = false;
    let startingPolls = 0;
    let failures = 0;
    /** A 4xx answer (no session, a blocked instance): the headers are ignored until the session reset. */
    let suspended = false;

    function showNotice(): void {
        runningSeen = true;
        if (noticeShown) return;
        noticeShown = true;
        notices.show(NOTICE);
    }

    function stop(): void {
        const current = poller;
        poller = null;
        current?.stop();
        if (noticeShown) {
            noticeShown = false;
            notices.hide(PRICE_REFRESH_NOTICE_ID);
        }
        runningSeen = false;
        startingPolls = 0;
        failures = 0;
    }

    async function check(): Promise<PollOutcome> {
        const tracked = poller;
        let status: PriceRefreshStatus;
        try {
            status = await fetchStatus();
        } catch (error) {
            if (poller !== tracked) return {ok: false};
            const status = httpStatusOf(error);
            if (status !== null && status >= 400 && status < 500) {
                stop();
                suspended = true;
                return {ok: false};
            }
            failures += 1;
            if (failures >= PRICE_REFRESH_MAX_FAILURES) stop();
            return {ok: false};
        }
        // An answer to a tracking that ended meanwhile changes nothing.
        if (poller !== tracked) return {ok: true};
        failures = 0;
        if (status.state === 'running') {
            startingPolls = 0;
            showNotice();
            return {ok: true};
        }
        if (status.state === 'starting') {
            startingPolls += 1;
            if (startingPolls >= PRICE_REFRESH_MAX_STARTING_POLLS) stop();
            return {ok: true};
        }
        const refresh = runningSeen && status.last_refreshed === true;
        stop();
        if (refresh) refreshPortfolio();
        return {ok: true};
    }

    function observe(headers: unknown): void {
        if (suspended) return;
        const value = readPriceRefreshHeader(headers);
        if (value === null) return;
        if (value === 'running') showNotice();
        if (poller === null) {
            startingPolls = 0;
            failures = 0;
            poller = startPolling({run: check, intervalMs: PRICE_REFRESH_POLL_MS});
        }
    }

    return {
        observe,
        get tracking() {
            return poller !== null;
        },
        get noticeShown() {
            return noticeShown;
        },
        stop,
        reset() {
            stop();
            suspended = false;
        },
    };
}

/** The app's tracker; the interceptor feeds it, and signing out resets it. */
export const priceRefresh: PriceRefreshTracker = createPriceRefresh();

registerClientSessionReset('priceRefresh', () => priceRefresh.reset());
