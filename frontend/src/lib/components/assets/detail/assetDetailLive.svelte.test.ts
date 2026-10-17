// @vitest-environment jsdom
//
// The docblock above is load-bearing. Under the default `node` environment a `.svelte.ts` is compiled for the server,
// where `$effect` never runs: "the poller did not restart" would pass on an effect that never ran at all
// (`$test/runes.svelte`). `assertEffectsRun()` in `beforeAll` fails the whole file loudly if the docblock is ever lost.
/**
 * AssetDetailLive — the live updates of the asset detail page (F26, decision 31), moved out of the page verbatim by
 * FE5c (piece 9b). One poll of `POST /assets/prices/current` feeds the price summary and the chart's last point.
 *
 * The contract under test:
 *   - **The effect.** The constructor reads nothing from the page: the `$derived` it declares is lazy. The effect reads
 *     `assetInfo` (its id and currency), `displayCurrency`, `fxConversionMissing`, `isHeadToday` and, through that
 *     `$derived`, whether `providerAssignment` has a provider code, and nothing else: a change to one of those re-runs
 *     it — the poller stopped, and a new one started unless the head left today, the asset is gone or no provider is
 *     assigned — while a change to anything else leaves the poller alone. A provider code that comes or goes re-runs
 *     it; the page reloading the assignment after a sync or an edit — a new object, with the same code or another
 *     one — does not (Z-8, N-ZA-3): the poll asks the backend, which reads the assignment of the moment.
 *   - **Stopped.** With the chart ending before today, no asset, or no provider code — a manual asset, or an assignment
 *     not loaded yet, which the page loads alongside the asset (Z-8: without a provider `POST /assets/prices/current`
 *     only echoes the stored price, and every answer counts as a portfolio mutation) —: no poller, `updatesState`
 *     `stopped`, the price and the conversion flag cleared, the flash put out with its timer, and no reference left for
 *     the next tick. The asset and the code may land in either order: the poller starts once both are in; a code lost
 *     while it runs stops it.
 *   - **Running.** One `startActivePolling` with `run`, `ASSET_DETAIL_LIVE_INTERVAL_MS` and `onstatechange`, which
 *     feeds `updatesState`; the page's destruction stops the poller and leaves no timer behind.
 *   - **A poll** asks for the asset's quote and hands the poller the outcome of the answer (`livePollOutcome`), or
 *     `livePollFailure` when the request throws. It writes nothing when the request throws, when there is no item, no
 *     value or a value that is not a finite number, or when the answer lands after the route moved to another asset,
 *     after the effect re-ran, or after the page was destroyed — not even the reference of the next tick.
 *   - **The summary.** The direction against the previous native value: a move lights the flash and bumps
 *     `flashToken`, a flat tick changes nothing, and the flash decays to neutral `LIVE_PRICE_FLASH_DECAY_MS` after the
 *     latest move; a re-run of the effect puts a lit flash out at once, with its timer, and leaves `flashToken` alone.
 *     The native price when no conversion is needed (the asset's own currency, no display currency, no asset currency,
 *     the FX pair missing); otherwise the price converted for today, or the native price with `conversionFailed` when
 *     the conversion answers no amount or throws. A conversion landing after the effect re-ran writes nothing.
 *   - **The chart head.** Nothing while the chart loads, while the calendar view loads in calendar mode, for an answer
 *     with an error or no date, or for a close the chart already has on that date — and without a provider code there
 *     is no poll at all (Stopped), so no answer reaches the chart head: it has no provider check of its own. The
 *     close compared with the poll is the point's native one, `original_close ?? close` — a converted point keeps it in
 *     `original_close`, a point left native for want of a rate in `close` — so a converted chart reloads only when the
 *     native price moved. A converted chart, or the calendar mode, is reloaded — `invalidateAssetPriceStore`, then
 *     `loadChartData(true)` — and the poll lasts until the reload lands. Otherwise today's point is merged into
 *     `chartData`, through its setter.
 *   - **`resetPrice()`** clears the price and the conversion flag, and nothing else.
 *   - **The change over the range** (X-R59, decision N80): the summary's Δ from the first day of the range on screen to
 *     the live price, computed by the backend. The page may hand `rangeStart`, that first day; without one no change is
 *     asked. The effect reads it beside the rest, so a new start restarts the poller, and every run of the effect,
 *     stopped or running, puts `rangeDelta` back to null — unknown — at once. A poll sends `rangeStartFor(rangeStart,
 *     today)` as the `range_start` query of its quote request, with the display currency as `target_currency` only when
 *     the price is converted, and the asset ids alone when there is no day to send. An answer that writes the price
 *     writes `rangeDelta` with it, after the conversion: the answer's `range_change` as the summary shows it, or no change
 *     when no start was sent or the conversion failed (a native price beside a change in the display currency). Nothing
 *     else writes it; `resetPrice()` clears it too.
 *
 * `startActivePolling` is mocked: each call is recorded with its options, and a case runs a poll itself by calling
 * `run()` — no cadence, no activity tracking, no timer. `$lib/api` and `invalidateAssetPriceStore` are mocked;
 * `livePriceService` and `assetDetailChartPoints` are the real ones (pure). The page is a reactive box the case owns,
 * handed to the instance as the page hands it: an object of getters, with a setter for `chartData`. `rangeStart` is a
 * getter only for a case that gives it, even as `undefined`: every other case hands the instance the page as it was
 * before X-R59. The clock is faked only around the decay of the flash.
 */
import {beforeAll, beforeEach, describe, expect, it, onTestFinished, vi} from 'vitest';
import type {Mock} from 'vitest';
import {flushSync} from 'svelte';
import {readFileSync} from 'node:fs';
import {join} from 'node:path';
import type {ActivePolling, ActivePollingOptions, ActivePollingState, PollOutcome} from '$lib/features/live-updates/activePolling';
import type {RangeDelta} from '$lib/utils/rangeChange';

const {api, startActivePolling, invalidateAssetPriceStore} = vi.hoisted(() => ({
    api: {
        get_current_prices_bulk_api_v1_assets_prices_current_post: vi.fn<(assetIds: number[]) => Promise<unknown>>(),
        convert_currency_bulk_api_v1_fx_currencies_convert_post: vi.fn<(items: ConvertRequestItem[]) => Promise<unknown>>(),
    },
    startActivePolling: vi.fn<(options: ActivePollingOptions) => ActivePolling>(),
    invalidateAssetPriceStore: vi.fn<(assetId: number) => void>(),
}));

// `livePriceService` imports `axiosInstance` too, for `fetchCurrentPrices`, which nothing here calls.
vi.mock('$lib/api', () => ({zodiosApi: api, axiosInstance: {post: vi.fn()}}));
vi.mock('$lib/features/live-updates/activePolling', () => ({startActivePolling}));
vi.mock('$lib/stores/assetPriceStoreRegistry', () => ({invalidateAssetPriceStore}));

import {assertEffectsRun, effectRoot, reactiveBox} from '$test/runes.svelte';
import {ASSET_DETAIL_LIVE_INTERVAL_MS} from '$lib/features/live-updates/cadence';
import {todayIso} from '$lib/utils/dateOnly';
import {AssetDetailLive, LIVE_PRICE_FLASH_DECAY_MS, type AssetDetailLiveInput} from './assetDetailLive.svelte';

const pricesEndpoint = api.get_current_prices_bulk_api_v1_assets_prices_current_post;
const convertEndpoint = api.convert_currency_bulk_api_v1_fx_currencies_convert_post;

// --- Fixtures -------------------------------------------------------------------------------------------------------

const ASSET_ID = 7;
const OTHER_ASSET_ID = 8;
/** The date of every quote. */
const AS_OF = '2026-10-16';

/** A point of the page's chart: the fields that matter here. */
interface ChartPoint {
    date: string;
    close: number;
    /** The native close of a point the chart load converted into the display currency; absent or null otherwise. */
    original_close?: number | null;
    open?: number;
    volume?: number;
    currency?: string;
}

/** The page's state that `AssetDetailLiveInput` reads, owned by each case. */
interface PageState {
    assetInfo: {id: number; currency: string} | null;
    pageAssetId: number;
    displayCurrency: string;
    fxConversionMissing: boolean;
    isHeadToday: boolean;
    providerAssignment: {provider_code?: string | null} | null;
    loading: boolean;
    primaryMode: 'price' | 'calendar-return';
    calendarReturnView: {state: string};
    chartData: ChartPoint[];
    /** The first day of the range on screen (X-R59): a getter only when the case gives it, see `mount()`. */
    rangeStart?: string;
}

/** One amount of the conversion request. */
interface ConvertRequestItem {
    from_amount: {code: string; amount: string};
    to: string;
    date_range: {start: string; end: string};
}

/** A poller the effect started: the options it was given, and its controls. */
interface StartedPoller {
    options: ActivePollingOptions;
    stop: Mock<() => void>;
    pollNow: Mock<() => void>;
}

/** Every poller the effect started in the current case, in order. */
const started: StartedPoller[] = [];

/** An asset quoted in USD and shown in USD, the chart reaching today without today's point, a provider assigned. */
function pageDefaults(): PageState {
    return {
        assetInfo: {id: ASSET_ID, currency: 'USD'},
        pageAssetId: ASSET_ID,
        displayCurrency: 'USD',
        fxConversionMissing: false,
        isHeadToday: true,
        providerAssignment: {provider_code: 'yfinance'},
        loading: false,
        primaryMode: 'price',
        calendarReturnView: {state: 'ready'},
        chartData: [
            {date: '2026-10-14', close: 98},
            {date: '2026-10-15', close: 99},
        ],
    };
}

/**
 * The instance, built as the page builds it: inside an effect root, over a reactive page read through getters, with a
 * setter for `chartData`. Every getter call is recorded; the root is torn down when the case ends.
 */
function mount(overrides: Partial<PageState> = {}) {
    const page = reactiveBox<PageState>({...pageDefaults(), ...overrides});
    const reads: string[] = [];
    const chartWrites = vi.fn<(points: ChartPoint[]) => void>();
    const loadChartData = vi.fn<(force: boolean) => Promise<void>>(async () => {});
    const read = <K extends keyof PageState>(key: K): PageState[K] => {
        reads.push(key);
        return page[key];
    };
    const input: AssetDetailLiveInput = {
        get assetInfo() {
            return read('assetInfo');
        },
        get pageAssetId() {
            return read('pageAssetId');
        },
        get displayCurrency() {
            return read('displayCurrency');
        },
        get fxConversionMissing() {
            return read('fxConversionMissing');
        },
        get isHeadToday() {
            return read('isHeadToday');
        },
        get providerAssignment() {
            return read('providerAssignment');
        },
        get loading() {
            return read('loading');
        },
        get primaryMode() {
            return read('primaryMode');
        },
        get calendarReturnView() {
            return read('calendarReturnView');
        },
        get chartData() {
            return read('chartData');
        },
        set chartData(points) {
            chartWrites(points);
            page.chartData = points;
        },
        loadChartData: (force) => loadChartData(force),
    };
    // The range start (X-R59) is a getter only when the case gives it, even as `undefined`: every other case hands the
    // instance the page as it was before, and its effect reads what it read before.
    if ('rangeStart' in overrides) Object.defineProperty(input, 'rangeStart', {enumerable: true, get: () => read('rangeStart')});
    const root = effectRoot(() => new AssetDetailLive(input));
    /** The reads made while the instance was built, before any effect could run. */
    const readsWhileBuilding = reads.length;
    flushSync();
    let stopped = false;
    const stop = () => {
        if (stopped) return;
        stopped = true;
        root.stop();
    };
    onTestFinished(stop);
    return {live: root.value, page, reads, readsWhileBuilding, chartWrites, loadChartData, stop};
}

type Mounted = ReturnType<typeof mount>;

/** The poller the effect started last. */
function lastPoller(): StartedPoller {
    const poller = started[started.length - 1];
    if (!poller) throw new Error('the effect started no poller');
    return poller;
}

/** One poll, as the poller's timer would run it; resolves to the outcome the poller would be handed. */
async function poll(poller: StartedPoller = lastPoller()): Promise<PollOutcome | void> {
    return poller.options.run();
}

/** One item of `POST /assets/prices/current` for the asset, as its provider quotes it. */
function quote(value: string | null, overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {asset_id: ASSET_ID, value, currency: 'USD', as_of_date: AS_OF, source: 'provider:yfinance', error: null, error_code: null, retry_after: null, ...overrides};
}

/** The quote endpoint's answer. */
function prices(...items: Array<Record<string, unknown>>) {
    return {results: items, success_count: items.length, errors: []};
}

/** The next quote request answers `value`. */
function quoteNext(value: string | null, overrides: Record<string, unknown> = {}): void {
    pricesEndpoint.mockResolvedValueOnce(prices(quote(value, overrides)));
}

/** The conversion endpoint's answer for one amount into EUR. */
function conversion(amount: string | null) {
    return {results: [{from_amount: {code: 'USD', amount: '100'}, to_amount: {code: 'EUR', amount}, conversion_date: AS_OF}], success_count: 1, errors: []};
}

interface Deferred<T> {
    promise: Promise<T>;
    resolve: (value: T) => void;
    reject: (reason: unknown) => void;
}

/** A promise the case settles by hand: a request still in flight. */
function deferred<T>(): Deferred<T> {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((settle, fail) => {
        resolve = settle;
        reject = fail;
    });
    return {promise, resolve, reject};
}

/** The next quote request stays in flight until the case settles it. */
function holdNextQuote(): Deferred<unknown> {
    const answer = deferred<unknown>();
    pricesEndpoint.mockReturnValueOnce(answer.promise);
    return answer;
}

/** The next conversion request stays in flight until the case settles it; `sent` resolves once the request is out. */
function holdNextConversion(): {answer: Deferred<unknown>; sent: Promise<void>} {
    const answer = deferred<unknown>();
    const sent = deferred<void>();
    convertEndpoint.mockImplementationOnce(() => {
        sent.resolve();
        return answer.promise;
    });
    return {answer, sent: sent.promise};
}

/** What the price summary shows. */
function summary(live: AssetDetailLive) {
    return {currentPrice: live.currentPrice, conversionFailed: live.conversionFailed, direction: live.direction, flashToken: live.flashToken};
}

/** Plain copies of chart points: the page's chart is a deep `$state`, so the points it holds are proxies. */
function plain(points: readonly ChartPoint[]): ChartPoint[] {
    return points.map((point) => ({...point}));
}

/** The day the conversion of a live price asks for (`#applyLiveSummary`): the UTC date. */
function utcToday(): string {
    return new Date().toISOString().slice(0, 10);
}

/** Fake timers for this case only. Call it before `mount()`: the root is torn down first, then the real clock is back. */
function useFakeClock(): void {
    vi.useFakeTimers();
    onTestFinished(() => {
        vi.useRealTimers();
    });
}

beforeAll(() => {
    assertEffectsRun();
});

beforeEach(() => {
    started.length = 0;
    startActivePolling.mockReset();
    startActivePolling.mockImplementation((options) => {
        const poller: StartedPoller = {options, stop: vi.fn<() => void>(), pollNow: vi.fn<() => void>()};
        started.push(poller);
        return {state: 'running', stop: poller.stop, pollNow: poller.pollNow};
    });
    invalidateAssetPriceStore.mockReset();
    pricesEndpoint.mockReset();
    convertEndpoint.mockReset();
});

// --- The polling effect ---------------------------------------------------------------------------------------------

// An arrow of these tables that assigns an object or an array to the page has a block body: as the arrow's value, the
// assignment is checked in dev and reads back as the proxy the page keeps, not the object (`assignment_value_stale`).

/** A change of the page, applied by a case. */
interface PageChange {
    change: string;
    apply: (page: PageState) => void;
}

/** What the effect polls with: a change re-runs it. */
const POLLED_WITH: PageChange[] = [
    {change: 'the display currency', apply: (page) => (page.displayCurrency = 'EUR')},
    {change: "the asset's currency", apply: (page) => (page.assetInfo!.currency = 'CHF')},
    {change: 'the FX gap', apply: (page) => (page.fxConversionMissing = true)},
    {
        change: 'the asset',
        apply: (page) => {
            page.assetInfo = {id: OTHER_ASSET_ID, currency: 'USD'};
        },
    },
];

/**
 * What only a landing poll reads: a change leaves the poller alone. The provider is not among them: by having a code or
 * not, it decides whether there is a poller at all (Z-8).
 */
const READ_ON_LANDING: PageChange[] = [
    {change: 'the asset of the route', apply: (page) => (page.pageAssetId = OTHER_ASSET_ID)},
    {change: 'the chart loading', apply: (page) => (page.loading = true)},
    {change: 'the chart mode', apply: (page) => (page.primaryMode = 'calendar-return')},
    {
        change: 'the calendar view',
        apply: (page) => {
            page.calendarReturnView = {state: 'loading'};
        },
    },
    {
        change: 'the chart data',
        apply: (page) => {
            page.chartData = [];
        },
    },
];

/** When there is nothing to poll yet. */
const NOT_YET: Array<{when: string; overrides: Partial<PageState>}> = [
    {when: 'the chart ends before today', overrides: {isHeadToday: false}},
    {when: 'there is no asset yet', overrides: {assetInfo: null}},
    // Z-8: a manual asset has no assignment, and any asset has none until it has loaded. Without a provider
    // the quote endpoint only echoes the stored price, and every answer counts as a portfolio mutation.
    {when: 'no provider is assigned', overrides: {providerAssignment: null}},
    {when: 'the provider assignment has no code', overrides: {providerAssignment: {provider_code: null}}},
    {when: 'the provider code is empty', overrides: {providerAssignment: {provider_code: ''}}},
];

/** What stops a running poll and what brings it back: the page then behaves as on a range that ends in the past. */
const LEAVES: Array<{leaves: string; leave: (page: PageState) => void; back: (page: PageState) => void}> = [
    {leaves: 'the head leaves today', leave: (page) => (page.isHeadToday = false), back: (page) => (page.isHeadToday = true)},
    // Z-8: an edit removing the provider, and the page's own reload, which empties the assignment before loading it.
    {
        leaves: 'the provider is unassigned',
        leave: (page) => (page.providerAssignment = null),
        back: (page) => {
            page.providerAssignment = {provider_code: 'yfinance'};
        },
    },
    {
        leaves: 'the provider assignment loses its code',
        leave: (page) => {
            page.providerAssignment = {provider_code: null};
        },
        back: (page) => {
            page.providerAssignment = {provider_code: 'yfinance'};
        },
    },
];

describe('AssetDetailLive — the polling effect', () => {
    it('reads nothing from the page while it is built; its effect then reads the asset, the currencies, the FX gap, the head and the provider', () => {
        const {reads, readsWhileBuilding} = mount();

        // The page builds the instance in the middle of its script: a read here would reach state the page has not
        // declared yet.
        expect(readsWhileBuilding).toBe(0);
        expect(new Set(reads)).toEqual(new Set(['assetInfo', 'displayCurrency', 'fxConversionMissing', 'isHeadToday', 'providerAssignment']));
    });

    it("starts one poller at the asset page's cadence, whose state becomes the page's, and whose poll asks for the asset's quote", async () => {
        const {live} = mount();

        expect(startActivePolling).toHaveBeenCalledTimes(1);
        expect(startActivePolling).toHaveBeenCalledWith({run: expect.any(Function), intervalMs: ASSET_DETAIL_LIVE_INTERVAL_MS, onstatechange: expect.any(Function)});
        // Until the poller reports a state, the page reads the initial one.
        expect(live.updatesState).toBe('stopped');
        const states: ActivePollingState[] = ['running', 'paused-idle', 'paused-hidden', 'running'];
        for (const state of states) {
            lastPoller().options.onstatechange?.(state);
            expect(live.updatesState).toBe(state);
        }

        quoteNext('100');
        await poll();
        expect(pricesEndpoint).toHaveBeenCalledTimes(1);
        expect(pricesEndpoint).toHaveBeenCalledWith([ASSET_ID]);
    });

    it.each(POLLED_WITH)('restarts on a change of $change: the old poller stopped, a new one started', ({apply}) => {
        const {page} = mount();
        const first = lastPoller();

        apply(page);
        flushSync();

        expect(first.stop).toHaveBeenCalledTimes(1);
        expect(startActivePolling).toHaveBeenCalledTimes(2);
        expect(lastPoller()).not.toBe(first);
        expect(lastPoller().stop).not.toHaveBeenCalled();
    });

    it.each(READ_ON_LANDING)('does not restart on a change of $change, which only a landing poll reads', ({apply}) => {
        const {page} = mount();

        apply(page);
        flushSync();

        expect(startActivePolling).toHaveBeenCalledTimes(1);
        expect(lastPoller().stop).not.toHaveBeenCalled();
    });

    it.each(NOT_YET)('starts no poller while $when — stopped, nothing shown — and starts one as soon as it can', ({overrides}) => {
        const {live, page} = mount(overrides);

        expect(startActivePolling).not.toHaveBeenCalled();
        expect(live.updatesState).toBe('stopped');
        expect(summary(live)).toEqual({currentPrice: null, conversionFailed: false, direction: 'neutral', flashToken: 0});

        page.isHeadToday = true;
        page.assetInfo = {id: ASSET_ID, currency: 'USD'};
        page.providerAssignment = {provider_code: 'yfinance'};
        flushSync();

        expect(startActivePolling).toHaveBeenCalledTimes(1);
    });

    it('waits for the provider assignment, which may land after the asset: none, then one without a code, start nothing; the code arriving alone starts the poller', () => {
        const {live, page} = mount({providerAssignment: null});
        expect(startActivePolling).not.toHaveBeenCalled();

        page.providerAssignment = {provider_code: null};
        flushSync();
        expect(startActivePolling).not.toHaveBeenCalled();
        expect(live.updatesState).toBe('stopped');

        page.providerAssignment = {provider_code: 'yfinance'};
        flushSync();
        expect(startActivePolling).toHaveBeenCalledTimes(1);
        expect(startActivePolling).toHaveBeenCalledWith({run: expect.any(Function), intervalMs: ASSET_DETAIL_LIVE_INTERVAL_MS, onstatechange: expect.any(Function)});
        lastPoller().options.onstatechange?.('running');
        expect(live.updatesState).toBe('running');
    });

    // Z-8, N-ZA-3: the provider reaches the effect as a `$derived` boolean, whether there is a code. The page reassigns
    // the assignment each time it reloads its metadata, after a sync or an edit — a new object, usually with the same
    // code — and, read straight, that would restart the poller, whose start polls at once: one more write for nothing.
    it('does not restart when the assignment is reloaded — a new object with the same code, or another code — but stops when the code goes', () => {
        const {live, page} = mount({providerAssignment: {provider_code: 'yfinance'}});
        const first = lastPoller();
        first.options.onstatechange?.('running');

        // The page's reload: a new object, the same code.
        page.providerAssignment = {provider_code: 'yfinance'};
        flushSync();
        expect(startActivePolling).toHaveBeenCalledTimes(1);
        expect(first.stop).not.toHaveBeenCalled();
        expect(live.updatesState).toBe('running');

        // Another provider: the poll asks the backend, which reads the assignment of the moment.
        page.providerAssignment = {provider_code: 'justetf'};
        flushSync();
        expect(startActivePolling).toHaveBeenCalledTimes(1);
        expect(first.stop).not.toHaveBeenCalled();
        expect(live.updatesState).toBe('running');

        // The control: the same kind of change, a new object, is seen once it carries no code — the effect is not deaf.
        page.providerAssignment = {provider_code: null};
        flushSync();
        expect(first.stop).toHaveBeenCalledTimes(1);
        expect(startActivePolling).toHaveBeenCalledTimes(1);
        expect(live.updatesState).toBe('stopped');
    });

    it.each(LEAVES)('resets when $leaves: the poller stopped, `stopped`, price and flag cleared, the flash out, no reference left for the next tick', async ({leave, back}) => {
        const {live, page} = mount({displayCurrency: 'EUR'});
        const first = lastPoller();
        first.options.onstatechange?.('running');
        quoteNext('100');
        convertEndpoint.mockResolvedValueOnce(conversion('92'));
        await poll();
        quoteNext('101');
        convertEndpoint.mockRejectedValueOnce(new Error('rate unavailable'));
        await poll();
        expect(summary(live)).toEqual({currentPrice: 101, conversionFailed: true, direction: 'up', flashToken: 1});
        expect(live.updatesState).toBe('running');

        leave(page);
        flushSync();

        expect(first.stop).toHaveBeenCalledTimes(1);
        expect(startActivePolling).toHaveBeenCalledTimes(1);
        expect(live.updatesState).toBe('stopped');
        // `flashToken` only grows: it re-keys the flash, it shows nothing by itself.
        expect(summary(live)).toEqual({currentPrice: null, conversionFailed: false, direction: 'neutral', flashToken: 1});

        back(page);
        flushSync();
        expect(startActivePolling).toHaveBeenCalledTimes(2);
        quoteNext('99');
        convertEndpoint.mockResolvedValueOnce(conversion('91'));
        await poll();

        // 99 is below 101, the last quote before the reset: a reference kept across it would light a 'down' flash.
        expect(summary(live)).toEqual({currentPrice: 91, conversionFailed: false, direction: 'neutral', flashToken: 1});
    });

    it('stops its poller when the page is destroyed', () => {
        const {stop} = mount();
        const poller = lastPoller();

        stop();

        expect(poller.stop).toHaveBeenCalledTimes(1);
        expect(startActivePolling).toHaveBeenCalledTimes(1);
    });
});

// --- A poll ---------------------------------------------------------------------------------------------------------

/** Answers with no price to show. */
const UNUSABLE: Array<{answer: string; response: unknown}> = [
    {answer: 'an empty body', response: undefined},
    {answer: 'no results at all', response: {}},
    {answer: 'no item', response: prices()},
    {answer: 'a null value', response: prices(quote(null))},
    {answer: 'a value that is not a number', response: prices(quote('n/a'))},
    {answer: 'an infinite value', response: prices(quote('Infinity'))},
];

/** What can move under a quote request in flight, and the price shown once it has. */
const MOVES: Array<{move: string; apply: (mounted: Mounted) => void; shown: number | null}> = [
    {move: 'the route moved to another asset', apply: ({page}) => (page.pageAssetId = OTHER_ASSET_ID), shown: 100},
    {move: 'the display currency changed', apply: ({page}) => (page.displayCurrency = 'EUR'), shown: 100},
    {move: 'the head left today', apply: ({page}) => (page.isHeadToday = false), shown: null},
    // Z-8: the poll stops with the provider, and so does what it was still bringing.
    {move: 'the provider was unassigned', apply: ({page}) => (page.providerAssignment = null), shown: null},
    {move: 'the page was destroyed', apply: ({stop}) => stop(), shown: 100},
];

describe('a poll — the outcome it hands the poller, and what it writes', () => {
    it('hands back {ok: true} for a quote, and the end of the pause for a paused provider, whose last price still shows', async () => {
        const {live} = mount();
        quoteNext('100');
        await expect(poll()).resolves.toEqual({ok: true});

        quoteNext('98.32', {source: 'db:last_known', error_code: 'RATE_LIMITED', retry_after: 300});
        const before = Date.now();
        const outcome = await poll();
        const after = Date.now();

        expect(outcome).toEqual({ok: true, notBefore: expect.any(Number)});
        const {notBefore} = outcome as PollOutcome;
        expect(notBefore).toBeGreaterThanOrEqual(before + 300_000);
        expect(notBefore).toBeLessThanOrEqual(after + 300_000);
        expect(live.currentPrice).toBe(98.32);
    });

    it('hands back a failure when the request throws, and writes nothing: the last price stays, and so does the reference of the next tick', async () => {
        const {live, chartWrites, loadChartData} = mount();
        quoteNext('100');
        await poll();
        const shown = summary(live);

        pricesEndpoint.mockRejectedValueOnce(new Error('Network Error'));
        await expect(poll()).resolves.toEqual({ok: false});

        expect(summary(live)).toEqual(shown);
        expect(chartWrites).toHaveBeenCalledTimes(1); // the first quote's point, and nothing since
        expect(loadChartData).not.toHaveBeenCalled();
        expect(convertEndpoint).not.toHaveBeenCalled();

        quoteNext('101');
        await poll();
        expect(live.direction).toBe('up');
    });

    it("hands a 429's Retry-After on to the poller as the earliest next poll", async () => {
        mount();
        pricesEndpoint.mockRejectedValueOnce({isAxiosError: true, message: 'Request failed with status code 429', response: {status: 429, headers: {'retry-after': '120'}}});

        const before = Date.now();
        const outcome = await poll();
        const after = Date.now();

        expect(outcome).toEqual({ok: false, notBefore: expect.any(Number)});
        const {notBefore} = outcome as PollOutcome;
        expect(notBefore).toBeGreaterThanOrEqual(before + 120_000);
        expect(notBefore).toBeLessThanOrEqual(after + 120_000);
    });

    it.each(UNUSABLE)('writes nothing for $answer, and hands back {ok: true}', async ({response}) => {
        const {live, chartWrites, loadChartData} = mount();
        quoteNext('100');
        await poll();
        const shown = summary(live);

        pricesEndpoint.mockResolvedValueOnce(response);
        await expect(poll()).resolves.toEqual({ok: true});

        expect(summary(live)).toEqual(shown);
        expect(chartWrites).toHaveBeenCalledTimes(1); // the first quote's point, and nothing since
        expect(loadChartData).not.toHaveBeenCalled();
        expect(convertEndpoint).not.toHaveBeenCalled();
    });

    it.each(MOVES)('drops an answer that lands after $move: its outcome handed back, nothing written', async ({apply, shown}) => {
        const mounted = mount();
        const {live, chartWrites, loadChartData} = mounted;
        quoteNext('100');
        await poll();
        const answer = holdNextQuote();
        const landing = poll();

        apply(mounted);
        flushSync();
        answer.resolve(prices(quote('105')));

        await expect(landing).resolves.toEqual({ok: true});
        expect(summary(live)).toEqual({currentPrice: shown, conversionFailed: false, direction: 'neutral', flashToken: 0});
        expect(chartWrites).toHaveBeenCalledTimes(1); // the first quote's point, and nothing since
        expect(loadChartData).not.toHaveBeenCalled();
        expect(convertEndpoint).not.toHaveBeenCalled();
    });

    it('keeps no trace of a dropped answer, not even the reference of the next tick', async () => {
        const {live, page} = mount();
        quoteNext('100');
        await poll();
        const answer = holdNextQuote();
        const landing = poll();
        page.displayCurrency = 'EUR';
        flushSync();
        answer.resolve(prices(quote('90')));
        await landing;

        quoteNext('95');
        convertEndpoint.mockResolvedValueOnce(conversion('87.40'));
        await poll();

        // 95 against 100, the last quote shown: down. Against the dropped 90 it would have been up.
        expect(summary(live)).toEqual({currentPrice: 87.4, conversionFailed: false, direction: 'down', flashToken: 1});
    });
});

// --- The price summary ----------------------------------------------------------------------------------------------

/** When the native price is shown as it is. */
const NO_CONVERSION: Array<{when: string; overrides: Partial<PageState>}> = [
    {when: "the page shows the asset's currency", overrides: {}},
    {when: 'the page has no display currency yet', overrides: {displayCurrency: ''}},
    {when: 'the asset has no currency', overrides: {assetInfo: {id: ASSET_ID, currency: ''}}},
    {when: 'the FX pair is missing', overrides: {displayCurrency: 'EUR', fxConversionMissing: true}},
];

/** Conversion answers with no amount in them. */
const NO_AMOUNT: Array<{answer: string; response: unknown}> = [
    {answer: 'no result', response: {results: [], success_count: 0, errors: []}},
    {answer: 'no results at all', response: {}},
    {answer: 'a result without an amount', response: conversion(null)},
];

/** How a conversion in flight settles. */
const CONVERSION_SETTLES: Array<{settles: string; settle: (answer: Deferred<unknown>) => void}> = [
    {settles: 'its result', settle: (answer) => answer.resolve(conversion('93'))},
    {settles: 'its failure', settle: (answer) => answer.reject(new Error('rate unavailable'))},
];

describe('the price summary', () => {
    it('shows the native price when no conversion is needed, and flashes every move against the previous quote', async () => {
        const {live} = mount();

        quoteNext('100');
        await poll();
        // The first quote has nothing to compare with.
        expect(summary(live)).toEqual({currentPrice: 100, conversionFailed: false, direction: 'neutral', flashToken: 0});

        quoteNext('101');
        await poll();
        expect(summary(live)).toEqual({currentPrice: 101, conversionFailed: false, direction: 'up', flashToken: 1});

        quoteNext('99.5');
        await poll();
        expect(summary(live)).toEqual({currentPrice: 99.5, conversionFailed: false, direction: 'down', flashToken: 2});

        // A second move the same way bumps the token again, so the flash element is re-keyed and its animation restarts.
        quoteNext('99');
        await poll();
        expect(summary(live)).toEqual({currentPrice: 99, conversionFailed: false, direction: 'down', flashToken: 3});
        expect(convertEndpoint).not.toHaveBeenCalled();
    });

    it.each(NO_CONVERSION)('shows the native price, unconverted and unflagged, when $when', async ({overrides}) => {
        const {live} = mount(overrides);
        quoteNext('100');
        await poll();

        expect(live.currentPrice).toBe(100);
        expect(live.conversionFailed).toBe(false);
        expect(convertEndpoint).not.toHaveBeenCalled();
    });

    it('converts the native price into the display currency, for today, and shows the result', async () => {
        const {live} = mount({displayCurrency: 'EUR'});
        quoteNext('100');
        convertEndpoint.mockResolvedValueOnce(conversion('92.15'));

        const dayBefore = utcToday();
        await poll();
        const dayAfter = utcToday();

        expect(summary(live)).toEqual({currentPrice: 92.15, conversionFailed: false, direction: 'neutral', flashToken: 0});
        expect(convertEndpoint).toHaveBeenCalledTimes(1);
        const [request] = convertEndpoint.mock.calls[0];
        expect(request).toEqual([{from_amount: {code: 'USD', amount: '100'}, to: 'EUR', date_range: {start: expect.any(String), end: expect.any(String)}}]);
        const {start, end} = request[0].date_range;
        expect(end).toBe(start);
        // Whichever side of midnight the call fell on.
        expect([dayBefore, dayAfter]).toContain(start);
    });

    it.each(NO_AMOUNT)('falls back to the native price, flagged, when the conversion answers $answer', async ({response}) => {
        const {live} = mount({displayCurrency: 'EUR'});
        quoteNext('100');
        convertEndpoint.mockResolvedValueOnce(response);
        await poll();

        expect(live.currentPrice).toBe(100);
        expect(live.conversionFailed).toBe(true);
    });

    it('falls back to the native price, flagged, when the conversion throws — and the next conversion that answers clears the flag', async () => {
        const {live} = mount({displayCurrency: 'EUR'});
        quoteNext('100');
        convertEndpoint.mockRejectedValueOnce(new Error('rate unavailable'));
        await poll();
        expect(live.currentPrice).toBe(100);
        expect(live.conversionFailed).toBe(true);

        quoteNext('100');
        convertEndpoint.mockResolvedValueOnce(conversion('92.15'));
        await poll();
        expect(live.currentPrice).toBe(92.15);
        expect(live.conversionFailed).toBe(false);
    });

    it('clears a conversion failure as soon as a price needs no conversion', async () => {
        const {live, page} = mount({displayCurrency: 'EUR'});
        quoteNext('100');
        convertEndpoint.mockRejectedValueOnce(new Error('rate unavailable'));
        await poll();
        expect(live.conversionFailed).toBe(true);

        page.displayCurrency = 'USD';
        flushSync();
        quoteNext('100');
        await poll();

        expect(live.currentPrice).toBe(100);
        expect(live.conversionFailed).toBe(false);
    });

    it('compares native values across a display currency switch: a new rate is no move, a new price is', async () => {
        const {live, page} = mount();
        quoteNext('100');
        await poll();

        page.displayCurrency = 'EUR';
        flushSync();
        expect(startActivePolling).toHaveBeenCalledTimes(2);
        quoteNext('100');
        convertEndpoint.mockResolvedValueOnce(conversion('92.15'));
        await poll();

        // The price shown went from 100 to 92.15; the asset's did not move.
        expect(summary(live)).toEqual({currentPrice: 92.15, conversionFailed: false, direction: 'neutral', flashToken: 0});
        expect(convertEndpoint.mock.calls[0][0][0].to).toBe('EUR');

        quoteNext('101');
        convertEndpoint.mockResolvedValueOnce(conversion('93.07'));
        await poll();
        expect(summary(live)).toEqual({currentPrice: 93.07, conversionFailed: false, direction: 'up', flashToken: 1});
    });

    it.each(CONVERSION_SETTLES)('drops a conversion that lands after the effect re-ran: $settles writes no price, no flag, and no chart head', async ({settle}) => {
        const {live, page, loadChartData} = mount({displayCurrency: 'EUR'});
        quoteNext('100');
        convertEndpoint.mockResolvedValueOnce(conversion('92'));
        await poll();
        expect(live.currentPrice).toBe(92);
        loadChartData.mockClear();
        invalidateAssetPriceStore.mockClear();

        const conversionInFlight = holdNextConversion();
        quoteNext('101');
        const landing = poll();
        await conversionInFlight.sent;
        page.displayCurrency = 'CHF';
        flushSync();
        settle(conversionInFlight.answer);
        await landing;

        expect(live.currentPrice).toBe(92);
        expect(live.conversionFailed).toBe(false);
        // The converted chart reloads on every landing poll: here, none.
        expect(invalidateAssetPriceStore).not.toHaveBeenCalled();
        expect(loadChartData).not.toHaveBeenCalled();
    });
});

// --- The flash of a tick --------------------------------------------------------------------------------------------

/** What re-runs the effect without stopping the poll: the old poller stopped, a new one started. */
const RERUNS: Array<{rerun: string; change: Partial<PageState>}> = [
    {rerun: 'a display currency switch', change: {displayCurrency: 'EUR'}},
    {rerun: 'a move to another asset', change: {assetInfo: {id: OTHER_ASSET_ID, currency: 'USD'}, pageAssetId: OTHER_ASSET_ID}},
];

describe('the flash of a tick (fake clock)', () => {
    it('decays to neutral LIVE_PRICE_FLASH_DECAY_MS after the latest move: a flat tick neither cuts nor extends it, a new move restarts it', async () => {
        useFakeClock();
        const {live} = mount();
        quoteNext('100');
        await poll();
        // The first quote has nothing to compare with: no flash, no timer.
        expect(live.direction).toBe('neutral');
        expect(vi.getTimerCount()).toBe(0);

        quoteNext('101');
        await poll();
        expect(live.direction).toBe('up');
        expect(vi.getTimerCount()).toBe(1);
        vi.advanceTimersByTime(LIVE_PRICE_FLASH_DECAY_MS - 1);
        expect(live.direction).toBe('up');
        vi.advanceTimersByTime(1);
        expect(live.direction).toBe('neutral');
        expect(vi.getTimerCount()).toBe(0);

        // A flat tick 1000 ms into a flash leaves its decay where it was.
        quoteNext('102');
        await poll();
        vi.advanceTimersByTime(1000);
        quoteNext('102');
        await poll();
        expect(live.direction).toBe('up');
        vi.advanceTimersByTime(LIVE_PRICE_FLASH_DECAY_MS - 1000);
        expect(live.direction).toBe('neutral');

        // A new move 1000 ms into a flash restarts the decay from the new move.
        quoteNext('101');
        await poll();
        vi.advanceTimersByTime(1000);
        quoteNext('100');
        await poll();
        expect(vi.getTimerCount()).toBe(1);
        vi.advanceTimersByTime(LIVE_PRICE_FLASH_DECAY_MS - 1);
        expect(live.direction).toBe('down');
        vi.advanceTimersByTime(1);
        expect(live.direction).toBe('neutral');
        expect(live.flashToken).toBe(4);
    });

    it.each(LEAVES)('is put out at once when $leaves, and its timer with it', async ({leave}) => {
        useFakeClock();
        const {live, page} = mount();
        quoteNext('100');
        await poll();
        quoteNext('101');
        await poll();
        expect(live.direction).toBe('up');
        expect(vi.getTimerCount()).toBe(1);

        leave(page);
        flushSync();

        expect(live.direction).toBe('neutral');
        expect(vi.getTimerCount()).toBe(0);
    });

    it.each(RERUNS)('is put out at once when $rerun re-runs the effect, and its timer with it, `flashToken` left as it is', async ({change}) => {
        useFakeClock();
        const {live, page} = mount();
        quoteNext('100');
        await poll();
        quoteNext('101');
        await poll();
        expect(live.direction).toBe('up');
        expect(live.flashToken).toBe(1);
        expect(vi.getTimerCount()).toBe(1);

        Object.assign(page, change);
        flushSync();

        // A re-run, not a stop: the poll goes on with a new poller.
        expect(startActivePolling).toHaveBeenCalledTimes(2);
        expect(live.direction).toBe('neutral');
        expect(vi.getTimerCount()).toBe(0);
        vi.advanceTimersByTime(LIVE_PRICE_FLASH_DECAY_MS);
        expect(live.direction).toBe('neutral');
        // `flashToken` re-keys the flash element: a bump here would restart the animation it puts out.
        expect(live.flashToken).toBe(1);
    });

    it('leaves no timer behind when the page is destroyed', async () => {
        useFakeClock();
        const {stop} = mount();
        quoteNext('100');
        await poll();
        quoteNext('101');
        await poll();
        expect(vi.getTimerCount()).toBe(1);

        stop();

        expect(vi.getTimerCount()).toBe(0);
    });

    it('lasts as long as the CSS animation it ends (src/app.css, .lf-price-flash-*)', () => {
        const css = readFileSync(join(process.cwd(), 'src', 'app.css'), 'utf8');
        const animation = /animation:\s*lf-price-flash\s+(\d+(?:\.\d+)?)(ms|s)\b/.exec(css);

        expect(animation, 'no `animation: lf-price-flash <duration>` in src/app.css').not.toBeNull();
        const [, amount, unit] = animation as RegExpExecArray;
        expect(Math.round(Number(amount) * (unit === 's' ? 1000 : 1))).toBe(LIVE_PRICE_FLASH_DECAY_MS);
    });
});

// --- The chart head -------------------------------------------------------------------------------------------------

/** A close the chart already has on the quote's date. */
const SAME_CLOSE: Array<{mode: string; overrides: Partial<PageState>}> = [
    {mode: 'in price mode', overrides: {}},
    {mode: 'in calendar mode, which would reload otherwise', overrides: {primaryMode: 'calendar-return'}},
];

/**
 * What holds the chart head back. No provider is not among them: without a provider code there is no poller (Z-8, see
 * `NOT_YET`), so no answer reaches the chart head, and an answer in flight when the code goes is dropped (`MOVES`).
 */
const HELD_BACK: Array<{when: string; overrides?: Partial<PageState>; item?: Record<string, unknown>}> = [
    {when: 'the chart is loading', overrides: {loading: true}},
    {when: 'the calendar view is loading in calendar mode', overrides: {primaryMode: 'calendar-return', calendarReturnView: {state: 'loading'}}},
    {when: 'the answer carries an error', item: {error: 'provider timeout'}},
    {when: 'the answer has no date', item: {as_of_date: null}},
];

/** When the chart is reloaded rather than merged into. */
const RELOADS: Array<{when: string; overrides: Partial<PageState>}> = [
    {when: 'the chart is converted into another currency', overrides: {displayCurrency: 'EUR'}},
    {when: 'the chart shows calendar returns', overrides: {primaryMode: 'calendar-return'}},
];

/**
 * Today's point of a chart converted into EUR, as the chart load leaves it, when the native price is 100 USD: converted
 * with its native close in `original_close`, or left native, its `close` the native one, for want of a rate that day.
 */
const NATIVE_100_ON_CONVERTED: Array<{point: string; today: ChartPoint}> = [
    {point: 'converted, with `original_close`', today: {date: AS_OF, close: 92, original_close: 100}},
    {point: 'left native, `original_close` null', today: {date: AS_OF, close: 100, original_close: null}},
    {point: 'left native, without `original_close`', today: {date: AS_OF, close: 100}},
];

/**
 * Native prices that moved off 100, the `original_close` of today's point `{close: 92, original_close: 100}` on a chart
 * converted into EUR: to a new price, or onto the converted close, which compared with `close` would pass for no move.
 */
const NATIVE_MOVES_ON_CONVERTED: Array<{to: string; quoted: string; converted: string}> = [
    {to: 'a new price, 101', quoted: '101', converted: '92.92'},
    {to: 'the converted close, 92', quoted: '92', converted: '84.64'},
];

describe('the chart head', () => {
    it("merges today's point into the chart through its setter: the polled close and currency, the point's other fields kept", async () => {
        const {page, chartWrites, loadChartData} = mount({
            chartData: [
                {date: '2026-10-15', close: 99},
                {date: AS_OF, close: 100, open: 98, volume: 1200},
            ],
        });
        quoteNext('101.5');
        await poll();

        const merged = [
            {date: '2026-10-15', close: 99},
            {date: AS_OF, close: 101.5, open: 98, volume: 1200, currency: 'USD'},
        ];
        expect(chartWrites).toHaveBeenCalledTimes(1);
        expect(plain(chartWrites.mock.calls[0][0])).toEqual(merged);
        expect(plain(page.chartData)).toEqual(merged);
        expect(loadChartData).not.toHaveBeenCalled();
        expect(invalidateAssetPriceStore).not.toHaveBeenCalled();
    });

    it("appends today's point when the chart does not have it yet", async () => {
        const {page} = mount();
        quoteNext('100');
        await poll();

        expect(plain(page.chartData)).toEqual([
            {date: '2026-10-14', close: 98},
            {date: '2026-10-15', close: 99},
            {date: AS_OF, close: 100, currency: 'USD'},
        ]);
    });

    it.each(SAME_CLOSE)('writes nothing when the chart already has the polled close on that date, $mode', async ({overrides}) => {
        const {live, chartWrites, loadChartData} = mount({...overrides, chartData: [{date: AS_OF, close: 101.5, open: 98}]});
        quoteNext('101.5');
        await poll();

        expect(live.currentPrice).toBe(101.5);
        expect(chartWrites).not.toHaveBeenCalled();
        expect(loadChartData).not.toHaveBeenCalled();
        expect(invalidateAssetPriceStore).not.toHaveBeenCalled();
    });

    it.each(HELD_BACK)('leaves the chart alone when $when — the summary still shows the price', async ({overrides, item}) => {
        const {live, chartWrites, loadChartData} = mount(overrides);
        quoteNext('101.5', item);
        await poll();

        expect(live.currentPrice).toBe(101.5);
        expect(chartWrites).not.toHaveBeenCalled();
        expect(loadChartData).not.toHaveBeenCalled();
        expect(invalidateAssetPriceStore).not.toHaveBeenCalled();
    });

    it('lets a loading calendar view hold the chart back only in calendar mode', async () => {
        const {page, chartWrites} = mount({primaryMode: 'price', calendarReturnView: {state: 'loading'}});
        quoteNext('100');
        await poll();

        expect(chartWrites).toHaveBeenCalledTimes(1);
        expect(plain(page.chartData).map((point) => point.date)).toContain(AS_OF);
    });

    it.each(RELOADS)('reloads the chart instead of merging when $when: the price store invalidated, then a forced load', async ({overrides}) => {
        const {chartWrites, loadChartData} = mount(overrides);
        quoteNext('101.5');
        convertEndpoint.mockResolvedValue(conversion('93.50')); // asked only when the chart is converted
        await poll();

        expect(invalidateAssetPriceStore).toHaveBeenCalledTimes(1);
        expect(invalidateAssetPriceStore).toHaveBeenCalledWith(ASSET_ID);
        expect(loadChartData).toHaveBeenCalledTimes(1);
        expect(loadChartData).toHaveBeenCalledWith(true);
        expect(invalidateAssetPriceStore.mock.invocationCallOrder[0]).toBeLessThan(loadChartData.mock.invocationCallOrder[0]);
        expect(chartWrites).not.toHaveBeenCalled();
    });

    it.each(NATIVE_100_ON_CONVERTED)('reloads nothing when the native price did not move on a converted chart whose point for today is $point', async ({today}) => {
        const {live, chartWrites, loadChartData} = mount({displayCurrency: 'EUR', chartData: [today]});
        quoteNext('100');
        convertEndpoint.mockResolvedValueOnce(conversion('92'));
        await poll();

        expect(live.currentPrice).toBe(92);
        expect(chartWrites).not.toHaveBeenCalled();
        expect(loadChartData).not.toHaveBeenCalled();
        expect(invalidateAssetPriceStore).not.toHaveBeenCalled();
    });

    it.each(NATIVE_MOVES_ON_CONVERTED)("reloads a converted chart when the native price moved off today's `original_close` to $to: the price store invalidated, then a forced load", async ({quoted, converted}) => {
        const {chartWrites, loadChartData} = mount({displayCurrency: 'EUR', chartData: [{date: AS_OF, close: 92, original_close: 100}]});
        quoteNext(quoted);
        convertEndpoint.mockResolvedValueOnce(conversion(converted));
        await poll();

        expect(invalidateAssetPriceStore).toHaveBeenCalledTimes(1);
        expect(invalidateAssetPriceStore).toHaveBeenCalledWith(ASSET_ID);
        expect(loadChartData).toHaveBeenCalledTimes(1);
        expect(loadChartData).toHaveBeenCalledWith(true);
        expect(invalidateAssetPriceStore.mock.invocationCallOrder[0]).toBeLessThan(loadChartData.mock.invocationCallOrder[0]);
        expect(chartWrites).not.toHaveBeenCalled();
    });

    it('lasts until the reload lands, so the poller cannot start another poll over it', async () => {
        const {loadChartData} = mount({displayCurrency: 'EUR'});
        const reload = deferred<void>();
        const reloading = deferred<void>();
        loadChartData.mockImplementationOnce(() => {
            reloading.resolve();
            return reload.promise;
        });
        quoteNext('101.5');
        convertEndpoint.mockResolvedValueOnce(conversion('93.50'));
        let landed = false;
        const landing = poll().then((outcome) => {
            landed = true;
            return outcome;
        });

        await reloading.promise;
        expect(landed).toBe(false);

        reload.resolve();
        await expect(landing).resolves.toEqual({ok: true});
        expect(landed).toBe(true);
    });
});

// --- resetPrice() ---------------------------------------------------------------------------------------------------

describe('resetPrice()', () => {
    it('clears the price and the conversion flag, and nothing else: the flash, the state and the poller stay; the next poll shows a price again', async () => {
        const {live} = mount({displayCurrency: 'EUR'});
        lastPoller().options.onstatechange?.('running');
        quoteNext('100');
        convertEndpoint.mockResolvedValueOnce(conversion('92'));
        await poll();
        quoteNext('101');
        convertEndpoint.mockRejectedValueOnce(new Error('rate unavailable'));
        await poll();
        expect(summary(live)).toEqual({currentPrice: 101, conversionFailed: true, direction: 'up', flashToken: 1});

        live.resetPrice();

        expect(summary(live)).toEqual({currentPrice: null, conversionFailed: false, direction: 'up', flashToken: 1});
        expect(live.updatesState).toBe('running');
        expect(startActivePolling).toHaveBeenCalledTimes(1);
        expect(lastPoller().stop).not.toHaveBeenCalled();

        quoteNext('101');
        convertEndpoint.mockResolvedValueOnce(conversion('93'));
        await poll();
        expect(live.currentPrice).toBe(93);
        expect(live.conversionFailed).toBe(false);
    });
});

// --- The change over the range (X-R59) ------------------------------------------------------------------------------

/** A range start well in the past: on or before today, whatever day the suite runs. */
const PAST_START = '2025-10-16';
/** Another start in the past: the range on screen moved. */
const OTHER_PAST_START = '2024-10-16';
/** A range start after today, whatever day the suite runs. */
const FUTURE_START = '9999-12-31';

/** No change, known: what the summary shows where there is none. Not null, which is a change not known yet. */
const NO_CHANGE: RangeDelta = {abs: null, pct: null};

/** The `range_change` of a quote of 99 USD as the backend answers it, from 88 USD on the range's first day; as the summary shows it. */
const CHANGE_TO_99 = {reference_date: PAST_START, change_abs: '11', change_ratio: '0.125'};
const DELTA_TO_99: RangeDelta = {abs: 11, pct: 12.5};
/** A quote of 110 USD, from 88 USD. */
const CHANGE_TO_110 = {reference_date: PAST_START, change_abs: '22', change_ratio: '0.25'};
const DELTA_TO_110: RangeDelta = {abs: 22, pct: 25};
/** A quote shown converted, 92 EUR: its change in EUR, as the backend computes it with `target_currency`, from 80 EUR. */
const CHANGE_TO_92_EUR = {reference_date: PAST_START, change_abs: '12', change_ratio: '0.15'};
const DELTA_TO_92_EUR: RangeDelta = {abs: 12, pct: 15};
/** A quote shown converted, 93 EUR, from 80 EUR. */
const CHANGE_TO_93_EUR = {reference_date: PAST_START, change_abs: '13', change_ratio: '0.1625'};
const DELTA_TO_93_EUR: RangeDelta = {abs: 13, pct: 16.25};
/** The `range_change` of a quote whose range the backend could not value: no price on its first day, or no rate. */
const NO_RANGE_VALUE = {reference_date: null, change_abs: null, change_ratio: null};

/** The price the summary shows, and its change over the range. */
function priceAndChange(live: AssetDetailLive) {
    return {price: live.currentPrice, change: live.rangeDelta};
}

/** A change of the range start, from what the page handed to what it hands now. */
const RANGE_START_CHANGES: Array<{change: string; from: string | undefined; to: string | undefined}> = [
    {change: 'another day', from: PAST_START, to: OTHER_PAST_START},
    {change: 'a day where there was none', from: undefined, to: PAST_START},
    {change: 'none where there was a day', from: PAST_START, to: undefined},
];

/** What re-runs the effect without stopping the poll: what it polls with, and the range start. */
const RERUNS_WITH_A_RANGE: PageChange[] = [...POLLED_WITH, {change: 'the range start', apply: (page) => (page.rangeStart = OTHER_PAST_START)}];

/** How the quote is asked for with a range start in the past, by what the page shows: the queries of the request. */
const ASKED_WITH_A_START: Array<{when: string; overrides: Partial<PageState>; queries: Record<string, string>}> = [
    {when: "the page shows the asset's currency", overrides: {}, queries: {range_start: PAST_START}},
    {when: 'the page converts the price into another currency', overrides: {displayCurrency: 'EUR'}, queries: {range_start: PAST_START, target_currency: 'EUR'}},
    {when: 'the FX pair is missing, so the price is shown native', overrides: {displayCurrency: 'EUR', fxConversionMissing: true}, queries: {range_start: PAST_START}},
    {when: 'the page has no display currency yet', overrides: {displayCurrency: ''}, queries: {range_start: PAST_START}},
    {when: 'the asset has no currency', overrides: {assetInfo: {id: ASSET_ID, currency: ''}}, queries: {range_start: PAST_START}},
];

/** When a poll has no range start to send. */
const NO_START_TO_SEND: Array<{when: string; overrides: Partial<PageState>}> = [
    {when: 'the page hands none', overrides: {rangeStart: undefined}},
    {when: 'the page has no range start at all', overrides: {}},
    {when: 'it is the "min" sentinel, not yet a day', overrides: {rangeStart: 'min'}},
    {when: 'it is a day the calendar does not have', overrides: {rangeStart: '2026-02-30'}},
    {when: 'it falls after today', overrides: {rangeStart: FUTURE_START}},
    {when: 'it falls after today, on a page that converts the price', overrides: {rangeStart: FUTURE_START, displayCurrency: 'EUR'}},
];

/** Answers with no price to show, though their item carries a change over the range. */
const UNUSABLE_WITH_A_CHANGE: Array<{answer: string; response: unknown}> = [
    {answer: 'an empty body', response: undefined},
    {answer: 'no item', response: prices()},
    {answer: 'a null value', response: prices(quote(null, {range_change: CHANGE_TO_110}))},
    {answer: 'a value that is not a number', response: prices(quote('n/a', {range_change: CHANGE_TO_110}))},
    {answer: 'an infinite value', response: prices(quote('Infinity', {range_change: CHANGE_TO_110}))},
];

/** What can move under a quote request in flight, and the change shown once it has: the last one, or none known. */
const MOVES_UNDER_A_RANGE: Array<{move: string; apply: (mounted: Mounted) => void; shown: RangeDelta | null}> = [
    {move: 'the route moved to another asset', apply: ({page}) => (page.pageAssetId = OTHER_ASSET_ID), shown: DELTA_TO_99},
    {move: 'the display currency changed', apply: ({page}) => (page.displayCurrency = 'EUR'), shown: null},
    {move: 'the range start changed', apply: ({page}) => (page.rangeStart = OTHER_PAST_START), shown: null},
    {move: 'the head left today', apply: ({page}) => (page.isHeadToday = false), shown: null},
    {move: 'the provider was unassigned', apply: ({page}) => (page.providerAssignment = null), shown: null},
    {move: 'the page was destroyed', apply: ({stop}) => stop(), shown: DELTA_TO_99},
];

// X-R59: the summary's Δ runs from the first day of the range on screen to the live price, and the backend computes it
// with the quote (`POST /assets/prices/current?range_start=…`): `rangeDelta` replaces the page's own arithmetic on the
// chart's first close. Red today: the poll sends no queries, and the instance has no `rangeDelta`.
describe('the change over the range (X-R59)', () => {
    describe('the effect', () => {
        it('knows no change before a poll lands, with a range start or without', () => {
            expect(mount().live.rangeDelta, 'no range start').toBeNull();
            expect(mount({rangeStart: PAST_START}).live.rangeDelta, 'a range start').toBeNull();
        });

        it('reads the range start in its effect, beside the rest, and nothing while it is built', () => {
            const {reads, readsWhileBuilding} = mount({rangeStart: PAST_START});

            expect(readsWhileBuilding).toBe(0);
            expect(new Set(reads)).toEqual(new Set(['assetInfo', 'displayCurrency', 'fxConversionMissing', 'isHeadToday', 'providerAssignment', 'rangeStart']));
        });

        it.each(RANGE_START_CHANGES)('restarts on a change of the range start, $change: the old poller stopped, a new one started', ({from, to}) => {
            const {page} = mount({rangeStart: from});
            const first = lastPoller();

            page.rangeStart = to;
            flushSync();

            expect(first.stop).toHaveBeenCalledTimes(1);
            expect(startActivePolling).toHaveBeenCalledTimes(2);
            expect(lastPoller()).not.toBe(first);
            expect(lastPoller().stop).not.toHaveBeenCalled();
        });

        it.each(RERUNS_WITH_A_RANGE)('drops the change at once when a change of $change re-runs the effect: none known until the next poll lands', async ({apply}) => {
            const {live, page} = mount({rangeStart: PAST_START});
            quoteNext('99', {range_change: CHANGE_TO_99});
            await poll();
            expect(live.rangeDelta, 'precondition: the change of the first quote').toEqual(DELTA_TO_99);

            apply(page);
            flushSync();

            // A re-run, not a stop: the poll goes on with a new poller.
            expect(startActivePolling).toHaveBeenCalledTimes(2);
            expect(live.rangeDelta).toBeNull();
        });

        it.each(LEAVES)('drops the change with the price when $leaves', async ({leave}) => {
            const {live, page} = mount({rangeStart: PAST_START});
            quoteNext('99', {range_change: CHANGE_TO_99});
            await poll();
            expect(live.rangeDelta, 'precondition: the change of the first quote').toEqual(DELTA_TO_99);

            leave(page);
            flushSync();

            expect(priceAndChange(live)).toEqual({price: null, change: null});
        });
    });

    describe('the request of a poll', () => {
        it.each(ASKED_WITH_A_START)('asks with the range start, the display currency only for a converted price, and shows the change answered: $when', async ({overrides, queries}) => {
            const {live} = mount({rangeStart: PAST_START, ...overrides});
            quoteNext('99', {range_change: CHANGE_TO_99});
            convertEndpoint.mockResolvedValue(conversion('92')); // asked only when the price is converted
            await poll();

            expect(pricesEndpoint.mock.calls, 'one request: the asset ids, then its queries').toStrictEqual([[[ASSET_ID], {queries}]]);
            expect(live.rangeDelta).toEqual(DELTA_TO_99);
        });

        it('raises a range start before 1900 to 1900-01-01, the first day the backend values', async () => {
            mount({rangeStart: '1850-06-01'});
            quoteNext('99', {range_change: CHANGE_TO_99});
            await poll();

            expect(pricesEndpoint.mock.calls).toStrictEqual([[[ASSET_ID], {queries: {range_start: '1900-01-01'}}]]);
        });

        it('sends a range start on today: a range of one day', async () => {
            // Read before the poll, which reads today after it: never a later day than the poll's, either side of midnight.
            const today = todayIso();
            mount({rangeStart: today});
            quoteNext('99', {range_change: CHANGE_TO_99});
            await poll();

            expect(pricesEndpoint.mock.calls).toStrictEqual([[[ASSET_ID], {queries: {range_start: today}}]]);
        });

        it('asks with the range start its effect read, and reads none of its own while it polls', async () => {
            const {reads} = mount({rangeStart: PAST_START});
            const readsBeforePoll = reads.length;
            quoteNext('99', {range_change: CHANGE_TO_99});
            await poll();

            expect(pricesEndpoint.mock.calls).toStrictEqual([[[ASSET_ID], {queries: {range_start: PAST_START}}]]);
            expect(reads.slice(readsBeforePoll), 'the poll read the range start of the moment: it asks with its effect’s, as it converts into its effect’s currency').not.toContain('rangeStart');
        });

        it.each(NO_START_TO_SEND)('asks with the asset ids alone, one argument, and shows no change once a usable answer lands, when $when', async ({overrides}) => {
            const {live} = mount(overrides);
            quoteNext('99', {range_change: null});
            convertEndpoint.mockResolvedValue(conversion('92')); // asked only when the price is converted
            await poll();

            expect(pricesEndpoint.mock.calls, 'exactly the asset ids: no queries, not even empty ones').toStrictEqual([[[ASSET_ID]]]);
            expect(live.currentPrice, 'control: the answer was usable').not.toBeNull();
            expect(live.rangeDelta, 'no change, known: not null, which is a change not known yet').toEqual(NO_CHANGE);
        });
    });

    describe('what a poll writes', () => {
        it("writes the quote's change with its price, poll after poll", async () => {
            const {live} = mount({rangeStart: PAST_START});

            quoteNext('99', {range_change: CHANGE_TO_99});
            await poll();
            expect(priceAndChange(live)).toEqual({price: 99, change: DELTA_TO_99});

            quoteNext('110', {range_change: CHANGE_TO_110});
            await poll();
            expect(priceAndChange(live)).toEqual({price: 110, change: DELTA_TO_110});
        });

        it('writes the change the backend computed in the display currency, beside the converted price', async () => {
            const {live} = mount({rangeStart: PAST_START, displayCurrency: 'EUR'});
            quoteNext('99', {range_change: CHANGE_TO_92_EUR});
            convertEndpoint.mockResolvedValueOnce(conversion('92'));
            await poll();

            expect(live.conversionFailed).toBe(false);
            expect(priceAndChange(live)).toEqual({price: 92, change: DELTA_TO_92_EUR});
        });

        it('writes it in the same step as the price, once the conversion has landed', async () => {
            const {live} = mount({rangeStart: PAST_START, displayCurrency: 'EUR'});
            quoteNext('99', {range_change: CHANGE_TO_92_EUR});
            convertEndpoint.mockResolvedValueOnce(conversion('92'));
            await poll();
            expect(priceAndChange(live), 'precondition: the first quote, converted').toEqual({price: 92, change: DELTA_TO_92_EUR});

            const conversionInFlight = holdNextConversion();
            quoteNext('101', {range_change: CHANGE_TO_93_EUR});
            const landing = poll();
            await conversionInFlight.sent;
            expect(priceAndChange(live), 'while the new price converts, the summary keeps the last one and its change').toEqual({price: 92, change: DELTA_TO_92_EUR});

            conversionInFlight.answer.resolve(conversion('93'));
            await landing;
            expect(priceAndChange(live)).toEqual({price: 93, change: DELTA_TO_93_EUR});
        });

        it.each(NO_AMOUNT)('shows no change when the conversion answers $answer: the price is shown native, the change would be in the display currency', async ({response}) => {
            const {live} = mount({rangeStart: PAST_START, displayCurrency: 'EUR'});
            quoteNext('99', {range_change: CHANGE_TO_92_EUR});
            convertEndpoint.mockResolvedValueOnce(response);
            await poll();

            expect(live.conversionFailed).toBe(true);
            expect(priceAndChange(live)).toEqual({price: 99, change: NO_CHANGE});
        });

        it('shows no change when the conversion throws, and the change again once a conversion answers', async () => {
            const {live} = mount({rangeStart: PAST_START, displayCurrency: 'EUR'});
            quoteNext('99', {range_change: CHANGE_TO_92_EUR});
            convertEndpoint.mockRejectedValueOnce(new Error('rate unavailable'));
            await poll();
            expect(live.conversionFailed).toBe(true);
            expect(priceAndChange(live)).toEqual({price: 99, change: NO_CHANGE});

            quoteNext('101', {range_change: CHANGE_TO_93_EUR});
            convertEndpoint.mockResolvedValueOnce(conversion('93'));
            await poll();
            expect(live.conversionFailed).toBe(false);
            expect(priceAndChange(live)).toEqual({price: 93, change: DELTA_TO_93_EUR});
        });

        it('shows no change when the backend could not value the range: no price on its first day, or no rate', async () => {
            const {live} = mount({rangeStart: PAST_START, displayCurrency: 'EUR'});
            quoteNext('99', {range_change: NO_RANGE_VALUE});
            convertEndpoint.mockResolvedValueOnce(conversion('92'));
            await poll();

            expect(priceAndChange(live)).toEqual({price: 92, change: NO_CHANGE});
        });

        it('keeps the change it shows when the request throws', async () => {
            const {live} = mount({rangeStart: PAST_START});
            quoteNext('99', {range_change: CHANGE_TO_99});
            await poll();
            expect(live.rangeDelta, 'precondition: the change of the first quote').toEqual(DELTA_TO_99);

            pricesEndpoint.mockRejectedValueOnce(new Error('Network Error'));
            await expect(poll()).resolves.toEqual({ok: false});

            expect(priceAndChange(live)).toEqual({price: 99, change: DELTA_TO_99});
        });

        it.each(UNUSABLE_WITH_A_CHANGE)('keeps the change it shows for $answer: an answer that writes no price writes no change', async ({response}) => {
            const {live} = mount({rangeStart: PAST_START});
            quoteNext('99', {range_change: CHANGE_TO_99});
            await poll();
            expect(live.rangeDelta, 'precondition: the change of the first quote').toEqual(DELTA_TO_99);

            pricesEndpoint.mockResolvedValueOnce(response);
            await poll();

            expect(priceAndChange(live)).toEqual({price: 99, change: DELTA_TO_99});
        });

        it.each(MOVES_UNDER_A_RANGE)('drops the change of an answer that lands after $move', async ({apply, shown}) => {
            const mounted = mount({rangeStart: PAST_START});
            quoteNext('99', {range_change: CHANGE_TO_99});
            await poll();
            expect(mounted.live.rangeDelta, 'precondition: the change of the first quote').toEqual(DELTA_TO_99);
            const answer = holdNextQuote();
            const landing = poll();

            apply(mounted);
            flushSync();
            answer.resolve(prices(quote('110', {range_change: CHANGE_TO_110})));
            await landing;

            expect(mounted.live.rangeDelta).toEqual(shown);
        });

        it.each(CONVERSION_SETTLES)('drops the change with a conversion that lands after the effect re-ran: $settles writes none', async ({settle}) => {
            const {live, page} = mount({rangeStart: PAST_START, displayCurrency: 'EUR'});
            quoteNext('99', {range_change: CHANGE_TO_92_EUR});
            convertEndpoint.mockResolvedValueOnce(conversion('92'));
            await poll();
            expect(live.rangeDelta, 'precondition: the change of the first quote').toEqual(DELTA_TO_92_EUR);

            const conversionInFlight = holdNextConversion();
            quoteNext('101', {range_change: CHANGE_TO_93_EUR});
            const landing = poll();
            await conversionInFlight.sent;
            page.displayCurrency = 'CHF';
            flushSync();
            settle(conversionInFlight.answer);
            await landing;

            expect(live.rangeDelta).toBeNull();
        });
    });

    it('resetPrice() clears the change with the price; the next poll shows one again', async () => {
        const {live} = mount({rangeStart: PAST_START});
        quoteNext('99', {range_change: CHANGE_TO_99});
        await poll();
        expect(live.rangeDelta, 'precondition: the change of the first quote').toEqual(DELTA_TO_99);

        live.resetPrice();
        expect(priceAndChange(live)).toEqual({price: null, change: null});

        quoteNext('110', {range_change: CHANGE_TO_110});
        await poll();
        expect(priceAndChange(live)).toEqual({price: 110, change: DELTA_TO_110});
    });
});
