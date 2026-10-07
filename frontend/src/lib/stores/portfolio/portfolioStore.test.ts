import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const reportApi = vi.hoisted(() => vi.fn());

vi.mock('$lib/api', () => ({
    zodiosApi: {
        get_portfolio_report_api_v1_portfolio_report_post: reportApi,
    },
}));

import {transitionClientSession} from '$lib/stores/app/clientSession';

let fetchReport: typeof import('./portfolioStore.svelte').fetchReport;
let invalidate: typeof import('./portfolioStore.svelte').invalidate;
/**
 * The module, read by name for what the page cache adds (`resetPortfolioCache`, `peekReport`): a
 * missing export fails the case that needs it, with the contract in the message, instead of the
 * import, and the type check of this file does not depend on the export landing first.
 */
let store: Record<string, unknown>;

type ReportOptions = {includeBrokerPnlHistory?: boolean; includePnlCandles?: boolean; includeIncomeHistory?: boolean; includeCostHistory?: boolean; includeDepositHistory?: boolean; includeAcquisitionFunding?: boolean};
/** `fetchReport`'s arguments without `force`: the same key, read synchronously. */
type PeekReport = (brokerIds?: number[], dateFrom?: string, dateTo?: string, targetCurrency?: string, includeContribution?: boolean, includeBreakdown?: boolean, includeHistory?: boolean, includeAllocationHistory?: boolean, options?: ReportOptions) => {report: unknown; stale: boolean} | null;

function resetPortfolioCache(): void {
    expect(typeof store.resetPortfolioCache, 'portfolioStore exports no resetPortfolioCache(): the hard clear a session change needs, now that invalidate() keeps the data').toBe('function');
    (store.resetPortfolioCache as () => void)();
}

function peekReport(...args: Parameters<PeekReport>): ReturnType<PeekReport> {
    expect(typeof store.peekReport, 'portfolioStore exports no peekReport(...): a page cannot read the cached report synchronously, so it can only show a skeleton while it asks again').toBe('function');
    return (store.peekReport as PeekReport)(...args);
}

function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void} {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((settle) => {
        resolve = settle;
    });
    return {promise, resolve};
}

beforeAll(async () => {
    Object.defineProperty(globalThis, '$state', {
        configurable: true,
        value: <T>(value: T): T => value,
    });
    const module = await import('./portfolioStore.svelte');
    ({fetchReport, invalidate} = module);
    store = module as unknown as Record<string, unknown>;
});

describe('portfolioStore account isolation', () => {
    beforeEach(() => {
        reportApi.mockReset();
        // A hard clear between cases: `invalidate()` now marks the reports stale and keeps them.
        resetPortfolioCache();
    });

    it('never reuses the same filter key across users', async () => {
        transitionClientSession(null);
        transitionClientSession(101);
        reportApi.mockResolvedValueOnce({summary: {net_worth: 'A'}});
        expect(await fetchReport(undefined, '2025-01-01', '2025-12-31', 'EUR')).toMatchObject({
            summary: {net_worth: 'A'},
        });

        transitionClientSession(null);
        transitionClientSession(202);
        reportApi.mockResolvedValueOnce({summary: {net_worth: 'B'}});
        expect(await fetchReport(undefined, '2025-01-01', '2025-12-31', 'EUR')).toMatchObject({
            summary: {net_worth: 'B'},
        });

        expect(reportApi).toHaveBeenCalledTimes(2);
    });

    it('drops an in-flight response from the previous account', async () => {
        let resolveUserA: (report: unknown) => void = () => undefined;
        transitionClientSession(null);
        transitionClientSession(301);
        reportApi.mockImplementationOnce(
            () =>
                new Promise((resolve) => {
                    resolveUserA = resolve;
                }),
        );
        const staleRequest = fetchReport(undefined, '2025-01-01', '2025-12-31', 'EUR');

        transitionClientSession(null);
        transitionClientSession(302);
        reportApi.mockResolvedValueOnce({summary: {net_worth: 'B'}});
        const currentReport = await fetchReport(undefined, '2025-01-01', '2025-12-31', 'EUR');

        resolveUserA({summary: {net_worth: 'A'}});
        expect(await staleRequest).toBeNull();
        expect(currentReport).toMatchObject({summary: {net_worth: 'B'}});
    });
});

/**
 * Page cache, phase 1 (R2 / N, decision E1 of 06/10): show the old data, refresh in background.
 *
 * Invalidating no longer throws a report away: `invalidate()` marks it stale and keeps it, a page
 * reads it synchronously with `peekReport(...)` and shows it at once, and `fetchReport` asks again
 * — once per key, however many callers — and stores the fresh answer. Only a session change (or
 * `resetPortfolioCache()`) forgets everything: another account's data is never shown.
 *
 * Red first: `resetPortfolioCache` and `peekReport` do not exist yet, `invalidate()` still clears,
 * and a request in flight when it runs is still discarded.
 */
describe('portfolioStore — stale-while-revalidate (page cache, phase 1)', () => {
    const FROM = '2025-01-01';
    const TO = '2025-12-31';
    const OWNED = [5, 1];
    /** What the Dashboard's main load asks for on top of the defaults (`loadAll`). */
    const DASHBOARD_OPTIONS: ReportOptions = {includeBrokerPnlHistory: true, includeIncomeHistory: true, includeCostHistory: true, includeDepositHistory: true, includeAcquisitionFunding: true};

    let nextUser = 500;
    /** A fresh account per case: the key carries the user, so no case can see another's reports. */
    function freshAccount(): void {
        transitionClientSession(null);
        transitionClientSession(++nextUser);
    }

    function report(marker: string, amount: string) {
        return {marker, summary: {net_worth: {code: 'EUR', amount}, period_pnl: {code: 'EUR', amount}}};
    }

    beforeEach(() => {
        reportApi.mockReset();
        resetPortfolioCache();
        freshAccount();
    });

    it('answers peekReport() synchronously, from the very key fetchReport() uses, and from nothing else', async () => {
        const main = report('main', '2317.78');
        const contribution = report('contribution', '2317.78');
        reportApi.mockResolvedValueOnce(main).mockResolvedValueOnce(contribution);

        expect(peekReport(OWNED, FROM, TO, 'EUR', false, false, true, true, DASHBOARD_OPTIONS), 'nothing was fetched yet').toBeNull();
        await fetchReport(OWNED, FROM, TO, 'EUR', false, undefined, undefined, undefined, undefined, DASHBOARD_OPTIONS);
        await fetchReport(OWNED, FROM, TO, 'EUR', false, true, false, false, false);

        const peeked = peekReport([1, 5], FROM, TO, 'EUR', false, false, true, true, DASHBOARD_OPTIONS);
        expect(peeked, 'peekReport must answer now, not with a promise').not.toBeInstanceOf(Promise);
        expect(peeked, 'the broker order is not part of the key').toMatchObject({report: main, stale: false});
        expect(peekReport(OWNED, FROM, TO, 'EUR', true, false, false, false)).toMatchObject({report: contribution, stale: false});
        expect(peekReport(OWNED, FROM, TO, 'EUR', false, false, true, true), 'the options are part of the key').toBeNull();
        expect(peekReport(OWNED, FROM, TO, 'USD', false, false, true, true, DASHBOARD_OPTIONS), 'the currency is part of the key').toBeNull();
        expect(peekReport([1], FROM, TO, 'EUR', false, false, true, true, DASHBOARD_OPTIONS), 'the brokers are part of the key').toBeNull();
        expect(peekReport(undefined, FROM, TO, 'EUR', false, false, true, true, DASHBOARD_OPTIONS), '"all brokers" is not the owned set').toBeNull();

        // A fresh report is served without asking.
        expect(await fetchReport(OWNED, FROM, TO, 'EUR', false, undefined, undefined, undefined, undefined, DASHBOARD_OPTIONS)).toMatchObject(main);
        expect(reportApi).toHaveBeenCalledTimes(2);
    });

    it('invalidate() marks every cached report stale and keeps it, without asking anything', async () => {
        const main = report('main', '100');
        const contribution = report('contribution', '100');
        reportApi.mockResolvedValueOnce(main).mockResolvedValueOnce(contribution);
        await fetchReport(OWNED, FROM, TO, 'EUR');
        await fetchReport(OWNED, FROM, TO, 'EUR', false, true, false, false, false);

        invalidate();

        expect(peekReport(OWNED, FROM, TO, 'EUR'), 'invalidate() threw the report away: the page has nothing to show while it asks again').toMatchObject({report: main, stale: true});
        expect(peekReport(OWNED, FROM, TO, 'EUR', true, false, false, false)).toMatchObject({report: contribution, stale: true});
        expect(reportApi, 'invalidate() itself must not ask: the page that shows the report decides when').toHaveBeenCalledTimes(2);
    });

    it('asks once for a stale report however many callers ask, keeps the old one readable meanwhile, then stores the fresh one', async () => {
        const old = report('old', '100');
        const fresh = report('fresh', '125');
        reportApi.mockResolvedValueOnce(old);
        await fetchReport(OWNED, FROM, TO, 'EUR');
        invalidate();

        const answer = deferred<unknown>();
        reportApi.mockImplementationOnce(() => answer.promise);
        const first = fetchReport(OWNED, FROM, TO, 'EUR');
        const second = fetchReport([1, 5], FROM, TO, 'EUR');
        await vi.waitFor(() => expect(reportApi, 'a stale report was not asked again').toHaveBeenCalledTimes(2));
        expect(peekReport(OWNED, FROM, TO, 'EUR'), 'while the refresh is in flight, the old report is what the page shows').toMatchObject({report: old, stale: true});

        answer.resolve(fresh);
        expect(await first).toMatchObject(fresh);
        expect(await second).toMatchObject(fresh);
        expect(reportApi, 'two callers of one stale key sent two requests').toHaveBeenCalledTimes(2);
        expect(peekReport(OWNED, FROM, TO, 'EUR'), 'the fresh answer was not stored, or is still marked stale').toMatchObject({report: fresh, stale: false});

        expect(await fetchReport(OWNED, FROM, TO, 'EUR'), 'once fresh again, the report is served without asking').toMatchObject(fresh);
        expect(reportApi).toHaveBeenCalledTimes(2);
    });

    it('asks again when forced, even for a fresh report, once per key', async () => {
        const cached = report('cached', '100');
        const forced = report('forced', '110');
        reportApi.mockResolvedValueOnce(cached);
        await fetchReport(OWNED, FROM, TO, 'EUR');

        const answer = deferred<unknown>();
        reportApi.mockImplementationOnce(() => answer.promise);
        const first = fetchReport(OWNED, FROM, TO, 'EUR', true);
        const second = fetchReport(OWNED, FROM, TO, 'EUR', true);
        await vi.waitFor(() => expect(reportApi, '«Aggiorna» forces: a fresh report must be asked again').toHaveBeenCalledTimes(2));
        answer.resolve(forced);

        expect(await first).toMatchObject(forced);
        expect(await second).toMatchObject(forced);
        expect(reportApi, 'two forced callers of one key sent two requests').toHaveBeenCalledTimes(2);
        expect(peekReport(OWNED, FROM, TO, 'EUR')).toMatchObject({report: forced, stale: false});
    });

    it('keeps the answer of a request that was in flight when invalidate() ran: returned and stored, still stale', async () => {
        const landed = report('landed', '140');
        const answer = deferred<unknown>();
        reportApi.mockImplementationOnce(() => answer.promise);
        const inFlight = fetchReport(OWNED, FROM, TO, 'EUR');
        await vi.waitFor(() => expect(reportApi).toHaveBeenCalledTimes(1));

        // On the asset page the live price ticks every 30-60 s: a refresh discarded by each mark
        // would never land.
        invalidate();
        answer.resolve(landed);

        expect(await inFlight, 'a mark discarded the refresh in flight').toMatchObject(landed);
        expect(peekReport(OWNED, FROM, TO, 'EUR'), 'the answer was not stored, or the mark that arrived during the flight was lost').toMatchObject({report: landed, stale: true});
        expect(reportApi).toHaveBeenCalledTimes(1);
    });

    it('resolves null when the refresh fails and keeps the stale report on screen', async () => {
        const old = report('old', '100');
        reportApi.mockResolvedValueOnce(old);
        await fetchReport(OWNED, FROM, TO, 'EUR');
        invalidate();

        reportApi.mockRejectedValueOnce(new Error('synthetic: report engine unreachable'));
        expect(await fetchReport(OWNED, FROM, TO, 'EUR')).toBeNull();

        expect(reportApi).toHaveBeenCalledTimes(2);
        expect(peekReport(OWNED, FROM, TO, 'EUR'), 'a failed refresh emptied the cache: the page would trade the old figures for an empty card').toMatchObject({report: old, stale: true});
    });

    it('resetPortfolioCache() forgets everything, and an answer that lands after it is neither returned nor kept', async () => {
        const cached = report('cached', '100');
        reportApi.mockResolvedValueOnce(cached);
        await fetchReport(OWNED, FROM, TO, 'EUR');

        const late = deferred<unknown>();
        reportApi.mockImplementationOnce(() => late.promise);
        const straddling = fetchReport(OWNED, FROM, TO, 'USD');
        await vi.waitFor(() => expect(reportApi).toHaveBeenCalledTimes(2));

        resetPortfolioCache();
        expect(peekReport(OWNED, FROM, TO, 'EUR'), 'a hard reset kept a report').toBeNull();

        late.resolve(report('late', '999'));
        expect(await straddling, 'an answer to a question asked before the reset was handed back').toBeNull();
        expect(peekReport(OWNED, FROM, TO, 'USD'), 'an answer that landed after the reset was cached').toBeNull();

        const again = report('again', '101');
        reportApi.mockResolvedValueOnce(again);
        expect(await fetchReport(OWNED, FROM, TO, 'EUR'), 'after a reset the same question asks again').toMatchObject(again);
        expect(reportApi).toHaveBeenCalledTimes(3);
    });

    it('forgets everything on a session change: the next account, and the same one back, find nothing', async () => {
        const userId = nextUser;
        reportApi.mockResolvedValueOnce(report('mine', '100'));
        await fetchReport(OWNED, FROM, TO, 'EUR');
        expect(peekReport(OWNED, FROM, TO, 'EUR'), 'precondition: the report is cached').toMatchObject({stale: false});

        transitionClientSession(null);
        expect(peekReport(OWNED, FROM, TO, 'EUR')).toBeNull();
        transitionClientSession(++nextUser);
        expect(peekReport(OWNED, FROM, TO, 'EUR'), 'another account read a report it never asked for').toBeNull();

        transitionClientSession(null);
        transitionClientSession(userId);
        expect(peekReport(OWNED, FROM, TO, 'EUR'), 'a logout only marked the report stale: a session change must forget it').toBeNull();
    });
});
