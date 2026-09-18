/**
 * Portfolio-level risk analysis: Dashboard and Broker Detail.
 *
 * Owner: the four-levels mandate. The shared scaffolding lives in
 * `risk-mocks.ts`; the Asset Global test lives in `risk-lab.spec.ts` and the
 * Asset Detail net in `risk-asset-detail.spec.ts`.
 */
import {expect, test} from '../fixtures/playwright';

import {login} from '../fixtures/auth-helpers';
import {expectChartCanvas} from '../fixtures/charts';
import {TEST_USER} from '../fixtures/test-users';
import {installRiskMocks, openDashboardRisk, openFirstBrokerRisk} from './risk-mocks';

// Earned parallel: this file's blocks own the data they touch and wait on published
// state, so they share the backend with their neighbours instead of queueing behind
// them. Verified by a green run of the whole category at 4 workers.
test.describe.configure({mode: 'parallel'});

test.describe('Risk analysis functional integration', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('dashboard renders base analytics, quality, warnings, sync and capability gate', async ({page}) => {
        const requests = await installRiskMocks(page);
        await openDashboardRisk(page);

        await expect(page.getByTestId('risk-beta-banner')).toBeVisible();
        await expect(page.getByTestId('risk-beta-banner')).toHaveCount(1);
        await expect(page.getByTestId('risk-kpi-section')).toBeVisible({timeout: 8_000});
        await expectChartCanvas(page, 'risk-correlation-heatmap', 8_000);
        await expect(page.getByTestId('risk-contribution-bars')).toBeVisible({timeout: 8_000});
        await expect(page.getByTestId('risk-var-section')).toBeVisible({timeout: 8_000});
        await expect(page.getByTestId('risk-correlation-section-partial')).toBeVisible();
        await expect(page.getByTestId('risk-correlation-section-warnings')).toBeVisible();
        await expect(page.getByTestId('risk-quality-summary')).toBeVisible();
        await expect(page.getByTestId('risk-analysis-panel').getByTestId('data-quality-banner')).toBeVisible();
        await expect(page.getByTestId('risk-frontier-capability')).toHaveAttribute('data-available', 'false');

        await expect
            .poll(
                () =>
                    requests
                        .filter((request) => request.scope.kind === 'portfolio')
                        .map((request) => request.mode)
                        .sort(),
                {timeout: 15_000},
            )
            .toEqual(['current_composition', 'historical']);

        await expect(page.getByTestId('risk-sync-button')).toBeEnabled();
        await page.getByTestId('risk-sync-button').click();
        await expect(page.getByTestId('page-sync-modal')).toBeVisible({timeout: 5_000});
    });

    test('per-analytic unavailable state remains isolated', async ({page}) => {
        await installRiskMocks(page, {unavailableVar: true});
        await openDashboardRisk(page);

        await expect(page.getByTestId('risk-kpi-section')).toBeVisible({timeout: 8_000});
        await expect(page.getByTestId('risk-var-section-unavailable')).toBeVisible({timeout: 8_000});
        await expectChartCanvas(page, 'risk-correlation-heatmap', 8_000);
    });

    test('broker tab sends a single-broker portfolio subset and labels it', async ({page}) => {
        const requests = await installRiskMocks(page);
        const brokerId = await openFirstBrokerRisk(page);

        await expect(page.getByTestId('risk-beta-banner')).toBeVisible();
        await expect(page.getByTestId('risk-beta-banner')).toHaveCount(1);
        await expect(page.getByTestId('risk-scope-label')).toBeVisible();
        await expect(page.getByTestId('risk-kpi-section')).toBeVisible({timeout: 8_000});
        await expect.poll(() => requests.some((request) => request.scope.kind === 'portfolio' && request.scope.broker_ids?.length === 1 && request.scope.broker_ids[0] === brokerId), {timeout: 15_000}).toBe(true);
    });
});
