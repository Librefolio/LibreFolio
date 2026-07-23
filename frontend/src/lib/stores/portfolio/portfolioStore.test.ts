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

describe('portfolioStore account isolation', () => {
    beforeAll(async () => {
        Object.defineProperty(globalThis, '$state', {
            configurable: true,
            value: <T>(value: T): T => value,
        });
        ({fetchReport, invalidate} = await import('./portfolioStore.svelte'));
    });

    beforeEach(() => {
        reportApi.mockReset();
        invalidate();
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
