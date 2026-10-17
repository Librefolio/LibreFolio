/**
 * priceRefresh — «Aggiornamento prezzi…» in the web app (workstream Z, lot Z5; plan phase01SleepWake §Z5, N-Z5-1…5).
 *
 * While the server catches up the missing prices (at startup, on the user's return after a silence, on a scheduled
 * wake-up) every API answer carries `X-LibreFolio-Price-Refresh: starting|running`. The axios interceptor hands each
 * answer's headers to `priceRefresh.observe()`; from the first such header the app asks `GET /system/price-refresh` every
 * `PRICE_REFRESH_POLL_MS` (never polling for nothing: only after a header said a catch-up runs), shows an `info` notice
 * that cannot be dismissed while a job runs, and asks the portfolio to refresh once the catch-up is over — only when a job
 * ran during this tracking and the catch-up updated something.
 *
 * The contract under test:
 *   1. `readPriceRefreshHeader(headers)`: `AxiosHeaders` (`get`, any case) or a plain object with the lower-case key; the
 *      value trimmed and lower-cased; only `starting` / `running` count, anything else — absent, `idle`, garbage, headers
 *      that are not an object — is null.
 *   2. `observe(headers)`: null does nothing. `running` shows the notice at once. Either value starts the tracking when
 *      none runs: `startPolling({run: check, intervalMs: PRICE_REFRESH_POLL_MS})`, once per tracking.
 *   3. `check()`, the poll's `run`: `running` shows the notice and remembers it was seen, `{ok: true}`; `starting` keeps
 *      polling, and `PRICE_REFRESH_MAX_STARTING_POLLS` of them in a row stop the tracking; `idle` stops it, then calls
 *      `refreshPortfolio()` once only if `running` was seen during this tracking (header or status) and `last_refreshed`
 *      is true; a success resets the count of failures.
 *   3b. A page without a session (`/invite`, `/reset-password`, `/verify-email`) gets the header too, and its status
 *      question gets a 401: `fetchStatus()` rejecting with an HTTP status from 400 to 499 — `PriceRefreshStatusError.status`,
 *      or else `error.response.status`, axios-like — ends the tracking at once, as `stop()` does, without a refresh and
 *      without counting a failure, and suspends the tracker: from then on `observe()` ignores every header, `running`
 *      included. `reset()` (the session reset: a sign-in) lifts the suspension; `stop()` alone does not.
 *   3c. Any other rejection — a 5xx, an error without a status (the network), a status that is not a number — is a
 *      failure, as before: `{ok: false}`, and `PRICE_REFRESH_MAX_FAILURES` in a row end the tracking without a refresh
 *      and without a suspension.
 *   4. The notice is exactly `{id: PRICE_REFRESH_NOTICE_ID, severity: 'info', messageKey: PRICE_REFRESH_MESSAGE_KEY}`,
 *      shown once per tracking.
 *   5. `stop()`: the poller stopped, the notice hidden if shown, `tracking` false; a later header starts a new tracking.
 *      `reset()` is `stop()` that also lifts a suspension, and the app's `priceRefresh` is reset when the signed-in
 *      account changes.
 *   6. The defaults: `notices` = `instanceNotices`, `refreshPortfolio` = `notifyPricesCaughtUp` — the portfolio bus's
 *      `{kind: 'prices'}`, which the open Dashboard and broker page reload on (lot Z-13); never `requestPortfolioRefresh`,
 *      «Aggiorna»'s `{kind: 'refresh'}`, which no page can tell from its own refresh —, `startPolling` =
 *      `startActivePolling`; `fetchStatus` = `fetch(PRICE_REFRESH_STATUS_PATH, {credentials: 'same-origin', headers:
 *      {Accept: 'application/json'}})`, never the API client (whose error interceptor sends a 401 to the login page and
 *      loses the link token of the page): a response that is not ok throws `PriceRefreshStatusError(response.status)`,
 *      an ok one gives `response.json()`.
 *
 * Every tracker under test is `createPriceRefresh(deps)` with every dependency injected: a fake `startPolling` records the
 * options it was given and hands the test the poll's `run`, which the test calls by hand — no timer, no clock —; a fake
 * `notices` records `show` and `hide`; `fetchStatus` answers what the test scripts, a held answer included. The cases of
 * the default `fetchStatus` build a tracker without one and put a fake `fetch` in place of the global
 * (`vi.stubGlobal`, undone after each case), with `$lib/api` replaced by a trap meanwhile. Only the cases of the app's
 * own `priceRefresh` (rule 5's account change, rule 6's defaults) take a freshly imported module graph, with
 * `startActivePolling` and the bus's two signals — `notifyPricesCaughtUp` and `requestPortfolioRefresh` — replaced by
 * `vi.doMock` and the real `instanceNotices` and `clientSession` of that graph. The node environment: the module is
 * plain TypeScript.
 *
 * Red until `frontend/src/lib/features/price-refresh/priceRefresh.ts` exists: the import fails, the whole file is red.
 * Rule 3b and the default `fetchStatus` of rule 6 stay red until `PRICE_REFRESH_STATUS_PATH` and
 * `PriceRefreshStatusError` are exported, a 4xx suspends the tracker and the default asks with `fetch`. The cases of
 * rule 3c and the 4xx answering a tracking that already ended guard what stays as it was.
 *
 * Lot Z-13 (rule 6's default refresh): the app-instance cases of the default refresh stay red until `priceRefresh.ts`
 * calls `notifyPricesCaughtUp()` instead of `requestPortfolioRefresh()`. The mock of the bus provides both functions, so
 * the file loads whatever the bus exports today, and the red is the call counts, not an import.
 *
 * Lot Z-20 (rule 6's default `notices`, N-Z20-1): `instanceNotices.svelte` holds module-level `$state`, and the API
 * client imports this module, so the AI Export probe — which loads the client with Vite and no Svelte compiler — would
 * evaluate it and die on `rune_outside_svelte`. This module imports only its type statically (`import type
 * {InstanceNotice}`), and the default `notices` loads it with `import()` on the first `show` or `hide`, through one
 * shared promise: the calls reach it in their order — a `hide` never ahead of its `show` — even when both are issued
 * before the module has loaded. The notice therefore reaches `instanceNotices` a few microtasks after the call: the
 * app-instance cases wait for it (`vi.waitFor`) instead of reading the list in the same tick. The cases of the lazy load
 * build a tracker with every dependency injected but `notices`, in a freshly imported graph where
 * `instanceNotices.svelte` is a `vi.doMock` fake that records each evaluation of it and, when a case holds it, waits — a
 * module still on its way. Red until the static import goes: importing this module evaluates the fake (and the held
 * case stops at its premise). The case of the delivery guards what stays: shown, then hidden, once each, with the
 * contract notice and its id.
 */
import {AxiosError, AxiosHeaders} from 'axios';
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import type {Mock} from 'vitest';
import type {ActivePolling, ActivePollingOptions, PollOutcome} from '$lib/features/live-updates/activePolling';
import type {InstanceNotice} from '$lib/features/instance/instanceNotices.svelte';
import {PRICE_REFRESH_HEADER, PRICE_REFRESH_MAX_FAILURES, PRICE_REFRESH_MAX_STARTING_POLLS, PRICE_REFRESH_MESSAGE_KEY, PRICE_REFRESH_NOTICE_ID, PRICE_REFRESH_POLL_MS, PRICE_REFRESH_STATUS_PATH, PriceRefreshStatusError, createPriceRefresh, readPriceRefreshHeader} from './priceRefresh';
import type {PriceRefreshStatus, PriceRefreshState} from './priceRefresh';

/** The literals of the contract, never read from the module under test. */
const HEADER = 'x-librefolio-price-refresh';
const NOTICE: InstanceNotice = {id: 'liveUpdates.priceRefresh', severity: 'info', messageKey: 'liveUpdates.priceRefresh.running'};
const POLL_MS = 3_000;
const MAX_STARTING = 10;
const MAX_FAILURES = 5;
const STATUS_PATH = '/api/v1/system/price-refresh';

interface FakePoller {
    options: ActivePollingOptions;
    stop: Mock<() => void>;
}

/** `startActivePolling` faked: each start is recorded with its options; `run()` calls the latest poller's `run` by hand. */
function fakePolling() {
    const pollers: FakePoller[] = [];
    const start = vi.fn((options: ActivePollingOptions): ActivePolling => {
        const poller: FakePoller = {options, stop: vi.fn()};
        pollers.push(poller);
        return {
            get state() {
                return poller.stop.mock.calls.length > 0 ? 'stopped' : 'running';
            },
            pollNow: vi.fn(),
            stop: poller.stop,
        };
    });
    const latest = (): FakePoller => {
        expect(pollers.length, 'premise: a poller was started').toBeGreaterThan(0);
        return pollers[pollers.length - 1];
    };
    const run = async (): Promise<PollOutcome | void> => await latest().options.run();
    return {start, pollers, latest, run};
}

function status(state: PriceRefreshState, extra: Partial<PriceRefreshStatus> = {}): PriceRefreshStatus {
    return {
        state,
        reason: state === 'idle' ? null : 'return',
        job: state === 'running' ? 'current_price' : null,
        since: state === 'idle' ? null : '2026-10-16T06:00:00+00:00',
        last_finished_at: null,
        last_refreshed: false,
        ...extra,
    };
}

/** A rejection of `fetchStatus` with a value that is not an `Error`: `answers.push(new Rejection({response: {status: 403}}))`. */
class Rejection {
    readonly reason: unknown;

    constructor(reason: unknown) {
        this.reason = reason;
    }
}

type Answer = PriceRefreshStatus | Error | Rejection | Promise<PriceRefreshStatus>;

/** A promise the test settles when it chooses: an answer still on its way. */
function held<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((settle, fail) => {
        resolve = settle;
        reject = fail;
    });
    return {promise, resolve, reject};
}

/** A tracker with every dependency faked; `answers` is the queue of what `fetchStatus` gives: a status, an `Error` or a `Rejection` to reject with, or a promise held by the test. */
function setup() {
    const polling = fakePolling();
    const notices = {show: vi.fn<(notice: InstanceNotice) => void>(), hide: vi.fn<(id: string) => void>()};
    const refreshPortfolio = vi.fn<() => void>();
    const answers: Answer[] = [];
    const fetchStatus = vi.fn(async (): Promise<PriceRefreshStatus> => {
        const next = answers.shift();
        if (next === undefined) throw new Error('test: fetchStatus called with no answer scripted');
        if (next instanceof Rejection) throw next.reason;
        if (next instanceof Error) throw next;
        return await next;
    });
    const tracker = createPriceRefresh({fetchStatus, notices, refreshPortfolio, startPolling: polling.start});
    return {tracker, polling, notices, refreshPortfolio, fetchStatus, answers};
}

/** A tracker suspended by a 401 (rule 3b): a running header, then its status question answered 401. The mocks' calls are cleared, so a case counts only what follows. */
async function suspendedTracker() {
    const context = setup();
    context.tracker.observe(runningHeader);
    context.answers.push(new PriceRefreshStatusError(401));
    await context.polling.run();
    expect(context.tracker.tracking, 'premise: the 401 ended the tracking').toBe(false);
    expect(context.polling.latest().stop, 'premise: the 401 stopped the poller').toHaveBeenCalledTimes(1);
    context.polling.start.mockClear();
    context.notices.show.mockClear();
    context.notices.hide.mockClear();
    return context;
}

/** An axios error for an HTTP status, as an API-client call rejects: the status in `response.status`. */
function axiosError(status: number): AxiosError {
    return Object.assign(new AxiosError(`Request failed with status code ${status}`, 'ERR_BAD_REQUEST'), {response: {status}});
}

/** A `fetch` response with a JSON body. */
function jsonResponse(httpStatus: number, body: unknown): Response {
    return new Response(JSON.stringify(body), {status: httpStatus, headers: {'content-type': 'application/json'}});
}

const startingHeader = {[HEADER]: 'starting'};
const runningHeader = {[HEADER]: 'running'};

describe('constants', () => {
    it('the header, the notice, the cadence and the bounds of the contract', () => {
        expect(PRICE_REFRESH_HEADER).toBe(HEADER);
        expect(PRICE_REFRESH_NOTICE_ID).toBe(NOTICE.id);
        expect(PRICE_REFRESH_MESSAGE_KEY).toBe(NOTICE.messageKey);
        expect(PRICE_REFRESH_POLL_MS).toBe(POLL_MS);
        expect(PRICE_REFRESH_MAX_STARTING_POLLS).toBe(MAX_STARTING);
        expect(PRICE_REFRESH_MAX_FAILURES).toBe(MAX_FAILURES);
    });

    it('the status route, as a same-origin path', () => {
        expect(PRICE_REFRESH_STATUS_PATH).toBe(STATUS_PATH);
    });

    it('PriceRefreshStatusError is an Error that carries the HTTP status', () => {
        const error = new PriceRefreshStatusError(401);

        expect(error).toBeInstanceOf(Error);
        expect(error).toBeInstanceOf(PriceRefreshStatusError);
        expect(error.status).toBe(401);
        expect(error.name).toBe('PriceRefreshStatusError');
    });
});

describe('readPriceRefreshHeader', () => {
    it('reads AxiosHeaders whatever the case of the name', () => {
        expect(readPriceRefreshHeader(new AxiosHeaders({'X-LibreFolio-Price-Refresh': 'running'}))).toBe('running');
        expect(readPriceRefreshHeader(new AxiosHeaders({[HEADER]: 'starting'}))).toBe('starting');
    });

    it('reads a plain object with the lower-case key, the value trimmed and lower-cased', () => {
        expect(readPriceRefreshHeader({[HEADER]: 'starting'})).toBe('starting');
        expect(readPriceRefreshHeader({[HEADER]: ' Running '})).toBe('running');
        expect(readPriceRefreshHeader({[HEADER]: 'STARTING', 'content-type': 'application/json'})).toBe('starting');
    });

    it.each([
        ['absent', {'content-type': 'application/json'}],
        ['idle', {[HEADER]: 'idle'}],
        ['garbage', {[HEADER]: 'refreshing'}],
        ['empty', {[HEADER]: ''}],
        ['AxiosHeaders without it', new AxiosHeaders({'content-type': 'application/json'})],
        ['AxiosHeaders idle', new AxiosHeaders({[HEADER]: 'idle'})],
        ['undefined', undefined],
        ['null', null],
        ['a string', 'running'],
        ['a number', 42],
    ])('anything else is null: %s', (_label, headers) => {
        expect(readPriceRefreshHeader(headers)).toBeNull();
    });
});

describe('observe', () => {
    it('a header that is not starting or running does nothing', () => {
        const {tracker, polling, notices} = setup();

        tracker.observe({[HEADER]: 'idle'});
        tracker.observe({'content-type': 'application/json'});
        tracker.observe(undefined);

        expect(polling.start).not.toHaveBeenCalled();
        expect(notices.show).not.toHaveBeenCalled();
        expect(tracker.tracking).toBe(false);
        expect(tracker.noticeShown).toBe(false);
    });

    it('starting starts the tracking — one poller at the contract cadence — and shows no notice yet', () => {
        const {tracker, polling, notices} = setup();

        tracker.observe(startingHeader);

        expect(polling.start).toHaveBeenCalledTimes(1);
        expect(polling.latest().options).toEqual({run: expect.any(Function), intervalMs: POLL_MS});
        expect(tracker.tracking).toBe(true);
        expect(notices.show).not.toHaveBeenCalled();
        expect(tracker.noticeShown).toBe(false);
    });

    it('running shows the notice at once, exactly the contract notice, and starts the tracking', () => {
        const {tracker, polling, notices} = setup();

        tracker.observe(runningHeader);

        expect(notices.show).toHaveBeenCalledTimes(1);
        expect(notices.show.mock.calls[0][0]).toStrictEqual(NOTICE);
        expect(tracker.noticeShown).toBe(true);
        expect(polling.start).toHaveBeenCalledTimes(1);
        expect(tracker.tracking).toBe(true);
    });

    it('more headers while tracking start no second poller, and the notice is shown once per tracking', () => {
        const {tracker, polling, notices} = setup();

        tracker.observe(startingHeader);
        tracker.observe(startingHeader);
        expect(notices.show).not.toHaveBeenCalled();
        tracker.observe(runningHeader);
        tracker.observe(runningHeader);
        tracker.observe(new AxiosHeaders({'X-LibreFolio-Price-Refresh': 'running'}));

        expect(polling.start).toHaveBeenCalledTimes(1);
        expect(notices.show).toHaveBeenCalledTimes(1);
        expect(notices.show.mock.calls[0][0]).toStrictEqual(NOTICE);
    });
});

describe('check: running and starting', () => {
    it('running shows the notice once and answers {ok: true}', async () => {
        const {tracker, polling, notices, answers} = setup();
        tracker.observe(startingHeader);
        answers.push(status('running'), status('running'));

        expect(await polling.run()).toEqual({ok: true});
        expect(notices.show).toHaveBeenCalledTimes(1);
        expect(notices.show.mock.calls[0][0]).toStrictEqual(NOTICE);
        expect(tracker.noticeShown).toBe(true);

        expect(await polling.run()).toEqual({ok: true});
        expect(notices.show, 'no repeated show for the same tracking').toHaveBeenCalledTimes(1);
        expect(tracker.tracking).toBe(true);
        expect(polling.latest().stop).not.toHaveBeenCalled();
    });

    it(`starting keeps polling, and ${MAX_STARTING} in a row stop the tracking without a refresh`, async () => {
        const {tracker, polling, refreshPortfolio, answers} = setup();
        tracker.observe(startingHeader);

        for (let poll = 1; poll < MAX_STARTING; poll++) {
            answers.push(status('starting'));
            await polling.run();
            expect(tracker.tracking, `still tracking after ${poll} starting answers`).toBe(true);
            expect(polling.latest().stop).not.toHaveBeenCalled();
        }
        answers.push(status('starting'));
        await polling.run();

        expect(polling.latest().stop).toHaveBeenCalledTimes(1);
        expect(tracker.tracking).toBe(false);
        expect(refreshPortfolio).not.toHaveBeenCalled();
    });

    it('a running answer breaks a streak of starting answers', async () => {
        const {tracker, polling, answers} = setup();
        tracker.observe(startingHeader);
        const poll = async (state: PriceRefreshState, times: number) => {
            for (let index = 0; index < times; index++) {
                answers.push(status(state));
                await polling.run();
            }
        };

        await poll('starting', MAX_STARTING - 1);
        await poll('running', 1);
        await poll('starting', MAX_STARTING - 1);
        expect(tracker.tracking, `${MAX_STARTING - 1} starting answers since the running one`).toBe(true);

        await poll('starting', 1);
        expect(tracker.tracking).toBe(false);
        expect(polling.latest().stop).toHaveBeenCalledTimes(1);
    });
});

describe('check: idle', () => {
    it('after a running status, a refreshed catch-up stops the tracking, hides the notice and refreshes the portfolio once', async () => {
        const {tracker, polling, notices, refreshPortfolio, answers} = setup();
        tracker.observe(startingHeader);
        answers.push(status('running'), status('idle', {last_finished_at: '2026-10-16T06:01:00+00:00', last_refreshed: true}));

        await polling.run();
        await polling.run();

        expect(polling.latest().stop).toHaveBeenCalledTimes(1);
        expect(notices.hide).toHaveBeenCalledWith(NOTICE.id);
        expect(tracker.tracking).toBe(false);
        expect(tracker.noticeShown).toBe(false);
        expect(refreshPortfolio).toHaveBeenCalledTimes(1);
    });

    it('running seen by the header counts as seen', async () => {
        const {tracker, polling, refreshPortfolio, answers} = setup();
        tracker.observe(runningHeader);
        answers.push(status('idle', {last_refreshed: true}));

        await polling.run();

        expect(tracker.tracking).toBe(false);
        expect(refreshPortfolio).toHaveBeenCalledTimes(1);
    });

    it('a refreshed catch-up during which running was never seen does not refresh', async () => {
        const {tracker, polling, notices, refreshPortfolio, answers} = setup();
        tracker.observe(startingHeader);
        answers.push(status('starting'), status('idle', {last_refreshed: true}));

        await polling.run();
        await polling.run();

        expect(polling.latest().stop).toHaveBeenCalledTimes(1);
        expect(tracker.tracking).toBe(false);
        expect(notices.show).not.toHaveBeenCalled();
        expect(refreshPortfolio).not.toHaveBeenCalled();
    });

    it('a catch-up that updated nothing stops the tracking and hides the notice without a refresh', async () => {
        const {tracker, polling, notices, refreshPortfolio, answers} = setup();
        tracker.observe(runningHeader);
        answers.push(status('running'), status('idle', {last_refreshed: false}));

        await polling.run();
        await polling.run();

        expect(polling.latest().stop).toHaveBeenCalledTimes(1);
        expect(notices.hide).toHaveBeenCalledWith(NOTICE.id);
        expect(tracker.noticeShown).toBe(false);
        expect(refreshPortfolio).not.toHaveBeenCalled();
    });
});

describe('check: failures', () => {
    it(`a rejected status answers {ok: false}; ${MAX_FAILURES} in a row stop the tracking, no refresh`, async () => {
        const {tracker, polling, notices, refreshPortfolio, answers} = setup();
        tracker.observe(runningHeader);

        for (let failure = 1; failure < MAX_FAILURES; failure++) {
            answers.push(new Error('network'));
            expect(await polling.run()).toMatchObject({ok: false});
            expect(tracker.tracking, `still tracking after ${failure} failures`).toBe(true);
        }
        answers.push(new Error('network'));
        await polling.run();

        expect(polling.latest().stop).toHaveBeenCalledTimes(1);
        expect(tracker.tracking).toBe(false);
        expect(notices.hide).toHaveBeenCalledWith(NOTICE.id);
        expect(refreshPortfolio).not.toHaveBeenCalled();
    });

    it('a success resets the count of failures', async () => {
        const {tracker, polling, answers} = setup();
        tracker.observe(startingHeader);
        const fail = async (times: number) => {
            for (let index = 0; index < times; index++) {
                answers.push(new Error('network'));
                await polling.run();
            }
        };

        await fail(MAX_FAILURES - 1);
        answers.push(status('starting'));
        await polling.run();
        await fail(MAX_FAILURES - 1);
        expect(tracker.tracking, `${MAX_FAILURES - 1} failures since the success`).toBe(true);

        await fail(1);
        expect(tracker.tracking).toBe(false);
        expect(polling.latest().stop).toHaveBeenCalledTimes(1);
    });
});

describe('stop and reset', () => {
    it.each(['stop', 'reset'] as const)('%s stops the poller and hides the notice; a later header starts a new tracking, with its own notice', (method) => {
        const {tracker, polling, notices} = setup();
        tracker.observe(runningHeader);
        const first = polling.latest();

        tracker[method]();

        expect(first.stop).toHaveBeenCalledTimes(1);
        expect(notices.hide).toHaveBeenCalledWith(NOTICE.id);
        expect(tracker.tracking).toBe(false);
        expect(tracker.noticeShown).toBe(false);

        tracker.observe(runningHeader);
        expect(polling.start).toHaveBeenCalledTimes(2);
        expect(polling.latest()).not.toBe(first);
        expect(tracker.tracking).toBe(true);
        expect(notices.show).toHaveBeenCalledTimes(2);
        expect(notices.show.mock.calls[1][0]).toStrictEqual(NOTICE);
    });

    it('running seen belongs to one tracking: the next one, never running, does not refresh', async () => {
        const {tracker, polling, refreshPortfolio, answers} = setup();
        tracker.observe(runningHeader);
        tracker.stop();

        tracker.observe(startingHeader);
        answers.push(status('idle', {last_refreshed: true}));
        await polling.run();

        expect(tracker.tracking).toBe(false);
        expect(refreshPortfolio).not.toHaveBeenCalled();
    });
});

describe('check: a 4xx suspends (rule 3b)', () => {
    it('a 401 after a running header stops the poller and hides the notice, with no refresh', async () => {
        const {tracker, polling, notices, refreshPortfolio, answers} = setup();
        tracker.observe(runningHeader);
        expect(tracker.noticeShown, 'premise: the running header showed the notice').toBe(true);
        answers.push(new PriceRefreshStatusError(401));

        await polling.run();

        expect(polling.latest().stop).toHaveBeenCalledTimes(1);
        expect(notices.hide).toHaveBeenCalledWith(NOTICE.id);
        expect(tracker.tracking).toBe(false);
        expect(tracker.noticeShown).toBe(false);
        expect(refreshPortfolio).not.toHaveBeenCalled();
    });

    it.each([
        ['a plain {response: {status: 403}}', () => new Rejection({response: {status: 403}})],
        ['an AxiosError with a 403 response', () => axiosError(403)],
    ])('%s, axios-like: the same', async (_label, rejection) => {
        const {tracker, polling, notices, refreshPortfolio, answers} = setup();
        tracker.observe(runningHeader);
        answers.push(rejection());

        await polling.run();

        expect(polling.latest().stop).toHaveBeenCalledTimes(1);
        expect(notices.hide).toHaveBeenCalledWith(NOTICE.id);
        expect(tracker.tracking).toBe(false);
        expect(tracker.noticeShown).toBe(false);
        expect(refreshPortfolio).not.toHaveBeenCalled();
    });

    it.each([400, 404, 499])('%i, anywhere in the 4xx range, suspends too', async (httpStatus) => {
        const {tracker, polling, answers} = setup();
        tracker.observe(startingHeader);
        answers.push(new PriceRefreshStatusError(httpStatus));

        await polling.run();

        expect(polling.latest().stop).toHaveBeenCalledTimes(1);
        expect(tracker.tracking).toBe(false);
        tracker.observe(runningHeader);
        expect(polling.start, 'suspended: the next header starts no poller').toHaveBeenCalledTimes(1);
        expect(tracker.noticeShown).toBe(false);
    });

    it(`a 4xx after ${MAX_FAILURES - 1} failures suspends: it is not one more failure`, async () => {
        const {tracker, polling, answers} = setup();
        tracker.observe(runningHeader);
        for (let failure = 1; failure < MAX_FAILURES; failure++) {
            answers.push(failure % 2 === 0 ? new TypeError('Failed to fetch') : new PriceRefreshStatusError(500));
            await polling.run();
        }
        expect(tracker.tracking, `premise: ${MAX_FAILURES - 1} failures keep the tracking`).toBe(true);
        answers.push(new PriceRefreshStatusError(401));

        await polling.run();

        expect(polling.latest().stop).toHaveBeenCalledTimes(1);
        expect(tracker.tracking).toBe(false);
        tracker.observe(runningHeader);
        expect(polling.start, 'suspended: a header after the 401 starts no poller, as one would after a fifth failure').toHaveBeenCalledTimes(1);
        expect(tracker.noticeShown).toBe(false);
    });

    it('a 4xx answering a tracking that reset() ended does not suspend the next one', async () => {
        const {tracker, polling, answers} = setup();
        tracker.observe(runningHeader);
        const first = polling.latest();
        const answer = held<PriceRefreshStatus>();
        answers.push(answer.promise);
        const question = first.options.run(); // the status question leaves; its answer is still on its way
        tracker.reset(); // a sign-in meanwhile
        tracker.observe(runningHeader); // the first header of the new session
        expect(polling.start, 'premise: the new session tracks').toHaveBeenCalledTimes(2);

        answer.reject(new PriceRefreshStatusError(401));
        await question;

        expect(tracker.tracking, 'the 401 answered the tracking reset() ended: the new one goes on').toBe(true);
        expect(polling.latest().stop).not.toHaveBeenCalled();
        expect(tracker.noticeShown).toBe(true);
    });
});

describe('while suspended (rule 3b)', () => {
    it('a running or a starting header starts no poller and shows no notice', async () => {
        const {tracker, polling, notices} = await suspendedTracker();

        tracker.observe(runningHeader);
        tracker.observe(startingHeader);
        tracker.observe(new AxiosHeaders({'X-LibreFolio-Price-Refresh': 'running'}));

        expect(polling.start).not.toHaveBeenCalled();
        expect(notices.show).not.toHaveBeenCalled();
        expect(tracker.tracking).toBe(false);
        expect(tracker.noticeShown).toBe(false);
    });

    it('stop() does not lift the suspension', async () => {
        const {tracker, polling, notices} = await suspendedTracker();

        tracker.stop();
        tracker.observe(runningHeader);
        tracker.observe(startingHeader);

        expect(polling.start).not.toHaveBeenCalled();
        expect(notices.show).not.toHaveBeenCalled();
        expect(tracker.tracking).toBe(false);
    });

    it('reset() lifts it: a header tracks again, notice and all, and the new tracking runs to its end', async () => {
        const {tracker, polling, notices, refreshPortfolio, answers} = await suspendedTracker();

        tracker.reset();
        tracker.observe(runningHeader);

        expect(polling.start).toHaveBeenCalledTimes(1);
        expect(polling.latest().options).toEqual({run: expect.any(Function), intervalMs: POLL_MS});
        expect(tracker.tracking).toBe(true);
        expect(notices.show).toHaveBeenCalledTimes(1);
        expect(notices.show.mock.calls[0][0]).toStrictEqual(NOTICE);
        answers.push(status('idle', {last_refreshed: true}));
        await polling.run();
        expect(tracker.tracking).toBe(false);
        expect(refreshPortfolio).toHaveBeenCalledTimes(1);
    });

    it('a 4xx after reset() suspends again', async () => {
        const {tracker, polling, answers} = await suspendedTracker();
        tracker.reset();
        tracker.observe(startingHeader);
        answers.push(new PriceRefreshStatusError(403));

        await polling.run();

        expect(tracker.tracking).toBe(false);
        tracker.observe(runningHeader);
        expect(polling.start, 'one poller, the one the second 4xx ended').toHaveBeenCalledTimes(1);
        expect(tracker.noticeShown).toBe(false);
    });
});

describe('check: other failures still count (rule 3c)', () => {
    const OTHER_FAILURES: [string, () => Error | Rejection][] = [
        ['a 500', () => new PriceRefreshStatusError(500)],
        ['a 503', () => new PriceRefreshStatusError(503)],
        ['an axios-like 502', () => axiosError(502)],
        ['a network error, without a status', () => new TypeError('Failed to fetch')],
        ['a status that is not a number', () => new Rejection({response: {status: '401'}})],
    ];

    it.each(OTHER_FAILURES)('%s answers {ok: false} and keeps the tracking: no suspension', async (_label, failure) => {
        const {tracker, polling, notices, answers} = setup();
        tracker.observe(runningHeader);
        answers.push(failure());

        expect(await polling.run()).toMatchObject({ok: false});

        expect(tracker.tracking).toBe(true);
        expect(polling.latest().stop).not.toHaveBeenCalled();
        expect(tracker.noticeShown).toBe(true);
        expect(notices.hide).not.toHaveBeenCalled();
    });

    it(`500s and network errors, ${MAX_FAILURES} in a row, end the tracking without a suspension: a later header tracks again`, async () => {
        const {tracker, polling, notices, refreshPortfolio, answers} = setup();
        tracker.observe(runningHeader);

        for (let failure = 0; failure < MAX_FAILURES; failure++) {
            answers.push(OTHER_FAILURES[failure % OTHER_FAILURES.length][1]());
            await polling.run();
            if (failure < MAX_FAILURES - 1) expect(tracker.tracking, `still tracking after ${failure + 1} failures`).toBe(true);
        }

        expect(polling.latest().stop).toHaveBeenCalledTimes(1);
        expect(tracker.tracking).toBe(false);
        expect(notices.hide).toHaveBeenCalledWith(NOTICE.id);
        expect(refreshPortfolio).not.toHaveBeenCalled();
        tracker.observe(runningHeader);
        expect(polling.start, 'not suspended: a later header starts a new poller').toHaveBeenCalledTimes(2);
        expect(tracker.tracking).toBe(true);
        expect(tracker.noticeShown).toBe(true);
    });
});

describe('the default fetchStatus (rule 6)', () => {
    /** Set when anything imports `$lib/api` during a case: the trap below. */
    let apiClientImported = false;

    beforeEach(() => {
        apiClientImported = false;
        vi.doMock('$lib/api', () => {
            apiClientImported = true;
            throw new Error('test: the default fetchStatus must not go through the API client');
        });
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        vi.doUnmock('$lib/api');
    });

    /** A tracker built without `fetchStatus`, and a fake `fetch` in place of the global. */
    function withFetch() {
        const fetchMock = vi.fn<(input: unknown, init?: unknown) => Promise<Response>>();
        vi.stubGlobal('fetch', fetchMock);
        const polling = fakePolling();
        const notices = {show: vi.fn<(notice: InstanceNotice) => void>(), hide: vi.fn<(id: string) => void>()};
        const refreshPortfolio = vi.fn<() => void>();
        const tracker = createPriceRefresh({notices, refreshPortfolio, startPolling: polling.start});
        return {fetchMock, tracker, polling, notices, refreshPortfolio};
    }

    it('asks PRICE_REFRESH_STATUS_PATH with fetch, same-origin credentials and JSON accepted; a 200 body is the status', async () => {
        const {fetchMock, tracker, polling, notices} = withFetch();
        fetchMock.mockResolvedValueOnce(jsonResponse(200, status('running')));
        tracker.observe(startingHeader);

        const outcome = await polling.run();

        expect(fetchMock).toHaveBeenCalledTimes(1);
        expect(fetchMock).toHaveBeenCalledWith(STATUS_PATH, expect.objectContaining({credentials: 'same-origin', headers: {Accept: 'application/json'}}));
        expect(apiClientImported, 'the default fetchStatus went through the API client').toBe(false);
        expect(outcome).toEqual({ok: true});
        expect(notices.show).toHaveBeenCalledTimes(1);
        expect(tracker.noticeShown).toBe(true);
    });

    it('a 200 idle body after a running header ends the tracking and refreshes once', async () => {
        const {fetchMock, tracker, polling, refreshPortfolio} = withFetch();
        fetchMock.mockResolvedValueOnce(jsonResponse(200, status('idle', {last_finished_at: '2026-10-16T06:01:00+00:00', last_refreshed: true})));
        tracker.observe(runningHeader);

        await polling.run();

        expect(refreshPortfolio).toHaveBeenCalledTimes(1);
        expect(tracker.tracking).toBe(false);
    });

    it('a 401 suspends: the poller stopped, the notice hidden, no refresh, the next header ignored', async () => {
        const {fetchMock, tracker, polling, notices, refreshPortfolio} = withFetch();
        fetchMock.mockResolvedValueOnce(jsonResponse(401, {detail: 'Not authenticated'}));
        tracker.observe(runningHeader);

        await polling.run();

        expect(fetchMock).toHaveBeenCalledTimes(1);
        expect(polling.latest().stop).toHaveBeenCalledTimes(1);
        expect(notices.hide).toHaveBeenCalledWith(NOTICE.id);
        expect(tracker.tracking).toBe(false);
        expect(refreshPortfolio).not.toHaveBeenCalled();
        tracker.observe(runningHeader);
        expect(polling.start, 'suspended: the next header starts no poller').toHaveBeenCalledTimes(1);
    });

    it('a 500, or fetch rejecting, is a failure: {ok: false}, still tracking', async () => {
        const {fetchMock, tracker, polling} = withFetch();
        fetchMock.mockResolvedValueOnce(jsonResponse(500, {detail: 'Internal Server Error'})).mockRejectedValueOnce(new TypeError('fetch failed'));
        tracker.observe(runningHeader);

        expect(await polling.run()).toMatchObject({ok: false});
        expect(await polling.run()).toMatchObject({ok: false});

        expect(fetchMock).toHaveBeenCalledTimes(2);
        expect(tracker.tracking).toBe(true);
        expect(polling.latest().stop).not.toHaveBeenCalled();
    });
});

describe('the app instance', () => {
    const ACTIVE_POLLING = '$lib/features/live-updates/activePolling';
    const PORTFOLIO_MUTATION = '$lib/stores/portfolio/portfolioMutation';

    /** A freshly imported graph: `startActivePolling` and the bus's two signals replaced — `notifyPricesCaughtUp` (the price catch-up, Z-13) and `requestPortfolioRefresh` («Aggiorna») —, the rest real. */
    async function freshGraph() {
        vi.resetModules();
        const polling = fakePolling();
        const notifyPricesCaughtUp = vi.fn<() => void>();
        const requestPortfolioRefresh = vi.fn<() => void>();
        vi.doMock(ACTIVE_POLLING, async (importOriginal) => ({...(await importOriginal<Record<string, unknown>>()), startActivePolling: polling.start}));
        vi.doMock(PORTFOLIO_MUTATION, async (importOriginal) => ({...(await importOriginal<Record<string, unknown>>()), notifyPricesCaughtUp, requestPortfolioRefresh}));
        const module = await import('./priceRefresh');
        const {instanceNotices} = await import('$lib/features/instance/instanceNotices.svelte');
        const session = await import('$lib/stores/app/clientSession');
        return {module, polling, notifyPricesCaughtUp, requestPortfolioRefresh, instanceNotices, session};
    }

    afterEach(() => {
        vi.doUnmock(ACTIVE_POLLING);
        vi.doUnmock(PORTFOLIO_MUTATION);
        vi.unstubAllGlobals();
        vi.resetModules();
    });

    it('priceRefresh polls with startActivePolling and shows its notice through instanceNotices', async () => {
        const {module, polling, instanceNotices} = await freshGraph();

        module.priceRefresh.observe(runningHeader);

        expect(polling.start).toHaveBeenCalledTimes(1);
        expect(polling.latest().options).toEqual({run: expect.any(Function), intervalMs: POLL_MS});
        // The default notices reach instanceNotices through import() (Z-20): a few microtasks after the call.
        await vi.waitFor(() => expect(instanceNotices.list.filter((notice) => notice.id === NOTICE.id)).toEqual([NOTICE]));
        module.priceRefresh.stop();
        await vi.waitFor(() => expect(instanceNotices.list.filter((notice) => notice.id === NOTICE.id)).toEqual([]));
    });

    it('a tracker without refreshPortfolio refreshes through notifyPricesCaughtUp, never through requestPortfolioRefresh (Z-13)', async () => {
        const {module, polling, notifyPricesCaughtUp, requestPortfolioRefresh} = await freshGraph();
        const fetchStatus = vi.fn(async () => status('idle', {last_finished_at: '2026-10-16T06:01:00+00:00', last_refreshed: true}));
        const tracker = module.createPriceRefresh({fetchStatus, startPolling: polling.start});

        tracker.observe(runningHeader);
        await polling.run();

        expect(fetchStatus).toHaveBeenCalledTimes(1);
        expect(notifyPricesCaughtUp, 'the end of a catch-up that updated something must send the price signal, {kind: "prices"}: the open Dashboard and broker page reload on it').toHaveBeenCalledTimes(1);
        expect(requestPortfolioRefresh, '«Aggiorna»’s signal is not the price catch-up: sent here, the open page cannot tell it from its own refresh, and keeps the old figures').not.toHaveBeenCalled();
    });

    it('the app’s priceRefresh, with its default fetch, refreshes through notifyPricesCaughtUp once a catch-up that updated something is over (Z-13)', async () => {
        const {module, polling, notifyPricesCaughtUp, requestPortfolioRefresh, instanceNotices} = await freshGraph();
        const fetchMock = vi.fn(async () => jsonResponse(200, status('idle', {last_finished_at: '2026-10-16T06:01:00+00:00', last_refreshed: true})));
        vi.stubGlobal('fetch', fetchMock);
        module.priceRefresh.observe(runningHeader);
        await vi.waitFor(() => {
            expect(
                instanceNotices.list.filter((notice) => notice.id === NOTICE.id),
                'premise: the notice is on',
            ).toEqual([NOTICE]);
        });

        await polling.run();

        expect(fetchMock).toHaveBeenCalledTimes(1);
        await vi.waitFor(() => {
            expect(
                instanceNotices.list.filter((notice) => notice.id === NOTICE.id),
                'the idle answer hides the notice',
            ).toEqual([]);
        });
        expect(notifyPricesCaughtUp, 'the app’s tracker did not send the price signal at the end of the catch-up').toHaveBeenCalledTimes(1);
        expect(requestPortfolioRefresh, 'the app’s tracker still sends «Aggiorna»’s signal').not.toHaveBeenCalled();
        expect(module.priceRefresh.tracking).toBe(false);
    });

    it('the app’s priceRefresh sends neither signal when the catch-up updated nothing, or when no job was seen running', async () => {
        const {module, polling, notifyPricesCaughtUp, requestPortfolioRefresh} = await freshGraph();
        const fetchMock = vi
            .fn<() => Promise<Response>>()
            .mockResolvedValueOnce(jsonResponse(200, status('idle', {last_finished_at: '2026-10-16T06:01:00+00:00', last_refreshed: false})))
            .mockResolvedValueOnce(jsonResponse(200, status('idle', {last_finished_at: '2026-10-16T06:02:00+00:00', last_refreshed: true})));
        vi.stubGlobal('fetch', fetchMock);

        module.priceRefresh.observe(runningHeader);
        await polling.run();
        expect(module.priceRefresh.tracking, 'premise: the first catch-up is over').toBe(false);

        module.priceRefresh.observe(startingHeader);
        await polling.run();

        expect(fetchMock, 'premise: both catch-ups were asked about').toHaveBeenCalledTimes(2);
        expect(polling.start, 'premise: two trackings').toHaveBeenCalledTimes(2);
        expect(notifyPricesCaughtUp, 'a catch-up that updated nothing, or one whose job this page never saw run, must not reload the open page').not.toHaveBeenCalled();
        expect(requestPortfolioRefresh).not.toHaveBeenCalled();
    });

    it('a change of the signed-in account resets priceRefresh: its poller stopped, no tracking', async () => {
        const {module, polling, session} = await freshGraph();
        session.transitionClientSession('user-a'); // the first identity of the page load: nothing to reset yet
        module.priceRefresh.observe(runningHeader);
        expect(module.priceRefresh.tracking, 'premise: tracking').toBe(true);

        expect(session.transitionClientSession('user-b'), 'premise: a real change of account').toBe(true);

        expect(polling.latest().stop).toHaveBeenCalledTimes(1);
        expect(module.priceRefresh.tracking).toBe(false);
        expect(module.priceRefresh.noticeShown).toBe(false);
    });

    it('a 401 from the status route suspends priceRefresh on a page without a session, and the sign-in lifts the suspension', async () => {
        const {module, polling, session} = await freshGraph();
        const fetchMock = vi.fn(async () => jsonResponse(401, {detail: 'Not authenticated'}));
        vi.stubGlobal('fetch', fetchMock);
        session.transitionClientSession(null); // the page load resolves no account: /invite, /reset-password, /verify-email
        module.priceRefresh.observe(runningHeader);

        await polling.run();

        expect(fetchMock).toHaveBeenCalledTimes(1);
        expect(module.priceRefresh.tracking, 'premise: the 401 ended the tracking').toBe(false);
        module.priceRefresh.observe(runningHeader);
        expect(polling.start, 'suspended: no poller for a header after the 401').toHaveBeenCalledTimes(1);
        expect(module.priceRefresh.noticeShown).toBe(false);

        expect(session.transitionClientSession('user-a'), 'premise: the sign-in is a change of account').toBe(true);
        module.priceRefresh.observe(runningHeader);

        expect(polling.start, 'the sign-in lifted the suspension').toHaveBeenCalledTimes(2);
        expect(module.priceRefresh.tracking).toBe(true);
        module.priceRefresh.stop();
    });
});

describe('the default notices, loaded by the first notice (Z-20, N-Z20-1)', () => {
    const NOTICES_MODULE = '$lib/features/instance/instanceNotices.svelte';

    /**
     * A freshly imported `priceRefresh` whose `instanceNotices.svelte` is a fake: `evaluated` records each evaluation of
     * it, and while `load.held` is set an evaluation waits for it — the module still on its way.
     */
    async function lazyNoticesGraph() {
        vi.resetModules();
        const evaluated = vi.fn<() => void>().mockName('instanceNotices.svelte evaluated');
        const show = vi.fn<(notice: InstanceNotice) => void>().mockName('instanceNotices.show');
        const hide = vi.fn<(id: string) => void>().mockName('instanceNotices.hide');
        const load: {held: Promise<void> | null} = {held: null};
        vi.doMock(NOTICES_MODULE, async () => {
            evaluated();
            if (load.held) await load.held;
            return {instanceNotices: {show, hide}};
        });
        const module = await import('./priceRefresh');
        return {module, evaluated, show, hide, load};
    }

    /** A tracker of that graph with every dependency faked but `notices`: the default is the subject. */
    function defaultNoticesTracker(create: typeof createPriceRefresh) {
        const polling = fakePolling();
        const answers: PriceRefreshStatus[] = [];
        const fetchStatus = vi.fn(async (): Promise<PriceRefreshStatus> => {
            const next = answers.shift();
            if (next === undefined) throw new Error('test: fetchStatus called with no answer scripted');
            return next;
        });
        const tracker = create({fetchStatus, refreshPortfolio: vi.fn<() => void>(), startPolling: polling.start});
        return {tracker, polling, answers};
    }

    afterEach(async () => {
        await vi.dynamicImportSettled();
        vi.doUnmock(NOTICES_MODULE);
        vi.resetModules();
    });

    it('importing priceRefresh — which builds the app’s tracker — evaluates no instanceNotices.svelte, nor does a tracker built without notices', async () => {
        const {module, evaluated} = await lazyNoticesGraph();
        defaultNoticesTracker(module.createPriceRefresh);

        // An import() started at load or at creation would have reached the fake by now.
        await vi.dynamicImportSettled();

        expect(
            evaluated,
            'instanceNotices.svelte holds module-level $state: priceRefresh must import only its type statically and load it with import() on the first show or hide — the API client imports priceRefresh, and the AI Export probe loads the client without the Svelte compiler, where a rune throws rune_outside_svelte',
        ).not.toHaveBeenCalled();
    });

    it('a tracker without notices shows its notice in instanceNotices, loaded by that first show, and hides it there: once each, the show first', async () => {
        const {module, evaluated, show, hide} = await lazyNoticesGraph();
        const {tracker, polling, answers} = defaultNoticesTracker(module.createPriceRefresh);

        tracker.observe(runningHeader);
        await vi.waitFor(() => expect(show, 'the running header’s notice never reached instanceNotices').toHaveBeenCalledTimes(1));
        expect(hide).not.toHaveBeenCalled();
        answers.push(status('idle', {last_finished_at: '2026-10-16T06:01:00+00:00', last_refreshed: false}));
        await polling.run();
        await vi.waitFor(() => expect(hide, 'the idle answer’s hide never reached instanceNotices').toHaveBeenCalledTimes(1));

        expect(show).toHaveBeenCalledTimes(1);
        expect(show.mock.calls[0][0]).toStrictEqual(NOTICE);
        expect(hide).toHaveBeenCalledWith(NOTICE.id);
        expect(show.mock.invocationCallOrder[0], 'shown, then hidden').toBeLessThan(hide.mock.invocationCallOrder[0]);
        expect(evaluated, 'instanceNotices.svelte is loaded once').toHaveBeenCalledTimes(1);
        expect(tracker.tracking).toBe(false);
        expect(tracker.noticeShown).toBe(false);
    });

    it('a show and a hide issued while instanceNotices.svelte is still loading reach it in their order, through one load', async () => {
        const {module, evaluated, show, hide, load} = await lazyNoticesGraph();
        expect(evaluated, 'premise: importing priceRefresh loaded no instanceNotices.svelte (see the first case)').not.toHaveBeenCalled();
        const loading = held<void>();
        load.held = loading.promise;
        try {
            const {tracker, polling, answers} = defaultNoticesTracker(module.createPriceRefresh);

            tracker.observe(runningHeader);
            await vi.waitFor(() => expect(evaluated, 'premise: the first show starts loading instanceNotices.svelte').toHaveBeenCalledTimes(1));
            answers.push(status('idle', {last_refreshed: false}));
            await polling.run();
            expect(tracker.noticeShown, 'premise: the idle answer hid the notice').toBe(false);
            expect(show, 'premise: the module is held, so nothing has reached it yet').not.toHaveBeenCalled();
            expect(hide).not.toHaveBeenCalled();

            loading.resolve();
            await vi.waitFor(() => expect(hide, 'the hide never reached instanceNotices').toHaveBeenCalledTimes(1));

            expect(show).toHaveBeenCalledTimes(1);
            expect(show.mock.calls[0][0]).toStrictEqual(NOTICE);
            expect(hide).toHaveBeenCalledWith(NOTICE.id);
            expect(show.mock.invocationCallOrder[0], 'a hide that overtakes its show leaves the notice on screen for good').toBeLessThan(hide.mock.invocationCallOrder[0]);
            expect(evaluated, 'one load, shared by every call: two import() racing each other settle in no promised order').toHaveBeenCalledTimes(1);
        } finally {
            loading.resolve();
        }
    });
});
