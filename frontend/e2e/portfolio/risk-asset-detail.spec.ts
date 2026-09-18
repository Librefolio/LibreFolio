/**
 * Asset Detail — ⚠️ THIS FILE HAS NO OWNER, AND THAT IS THE POINT.
 *
 * Asset Detail is parked (D8, D47) and must come out of the risk redesign
 * IDENTICAL. These two tests are the only thing that will PROVE it once the
 * four-levels and laboratory mandates are done (D82).
 *
 * So: do not adapt them to make them pass. Adapting them deletes the very
 * evidence they exist to produce. If one of them goes red, the page changed —
 * that is a finding, not a maintenance chore.
 *
 * `openFirstAssetDetail` lives here rather than in `risk-mocks.ts` because this
 * file is its only consumer: it keeps the surface shared with the redesign as
 * small as it can honestly be.
 */
import {expect, test, type Page} from '../fixtures/playwright';

import {login} from '../fixtures/auth-helpers';
import {expectChartCanvas} from '../fixtures/charts';
import {TEST_USER} from '../fixtures/test-users';
import {goToAssetsPage} from '../assets/assets-helpers';
import {installRiskMocks, waitForRiskCatalog, type RiskRequest} from './risk-mocks';

async function openFirstAssetDetail(page: Page): Promise<number> {
    await goToAssetsPage(page);
    const firstCard = page.getByTestId(/^asset-card-\d+$/).first();
    await expect(firstCard).toBeVisible({timeout: 8_000});
    const testId = await firstCard.getAttribute('data-testid');
    const assetId = Number(testId?.replace('asset-card-', ''));
    if (!Number.isInteger(assetId) || assetId <= 0) throw new Error('Seeded asset card must expose a numeric data-testid.');
    await firstCard.click();
    await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 12_000});
    await expect(page.getByTestId('asset-detail-tab-overview')).toBeVisible({timeout: 12_000});
    return assetId;
}

// Earned parallel: this file's blocks own the data they touch and wait on published
// state, so they share the backend with their neighbours instead of queueing behind
// them. Verified by a green run of the whole category at 4 workers.
test.describe.configure({mode: 'parallel'});

test.describe('Risk analysis functional integration', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('asset detail preserves Overview and exposes Risk through its dedicated tab', async ({page}) => {
        await installRiskMocks(page);
        await openFirstAssetDetail(page);

        await expect(page.getByTestId('asset-detail-signals-toggle')).toBeVisible({timeout: 8_000});
        await expect(page.getByTestId('risk-beta-banner')).toHaveCount(0);
        await expect(page.getByTestId('asset-detail-risk-panel')).toHaveCount(0);

        await page.getByTestId('asset-detail-tab-risk').click();
        await expect(page).toHaveURL(/[?&]tab=risk(?:&|$)/);
        await expect(page.getByTestId('asset-detail-risk-panel')).toBeVisible({timeout: 12_000});
        await expect(page.getByTestId('risk-beta-banner')).toBeVisible();
        await expect(page.getByTestId('risk-beta-banner')).toHaveCount(1);
        await expect(page.getByTestId('asset-detail-signals-toggle')).toHaveCount(0);

        await page.getByTestId('asset-risk-configure-signals').click();
        await expect(page.getByTestId('asset-detail-signals-toggle')).toBeVisible({timeout: 8_000});
        await expect(page.getByTestId('asset-detail-signals-toggle')).toHaveAttribute('aria-expanded', 'true');
        await expect(page.getByTestId('asset-detail-risk-panel')).toHaveCount(0);
    });

    test('asset Risk runs typed scenarios, exposes replay audit and switches simulation view', async ({page}) => {
        const requests = await installRiskMocks(page);
        const assetId = await openFirstAssetDetail(page);
        await page.getByTestId('asset-detail-tab-risk').click();
        await expect(page.getByTestId('asset-detail-risk-panel')).toBeVisible({timeout: 12_000});

        // The comparison section renders only once the capability catalog has landed:
        // wait for the panel to say so, rather than for the section to appear — an
        // absent section is otherwise indistinguishable from an unsupported one.
        await waitForRiskCatalog(page);
        await expect(page.getByTestId('risk-comparison-controls')).toBeVisible({timeout: 12_000});
        await page.getByTestId('risk-comparison-asset-select-trigger').click();
        const comparisonOption = page.getByTestId(/^search-select-option-\d+$/).first();
        await expect(comparisonOption).toBeVisible({timeout: 5_000});
        await comparisonOption.click();
        await page.getByTestId('risk-comparison-run').click();
        await expectChartCanvas(page, 'risk-comparison-chart', 8_000);

        const stressBucketInputs = page.getByTestId(/^risk-stress-bucket-input-/);
        await expect(stressBucketInputs).toHaveCount(1, {timeout: 8_000});
        await page.getByTestId('risk-stress-show-all').check();
        await expect.poll(() => stressBucketInputs.count(), {timeout: 8_000}).toBeGreaterThan(1);
        const stressBucketInput = stressBucketInputs.first();
        await expect(stressBucketInput).toBeVisible({timeout: 8_000});
        const stressBucketTestId = await stressBucketInput.getAttribute('data-testid');
        const stressBucketId = stressBucketTestId?.replace('risk-stress-bucket-input-', '');
        if (!stressBucketId) throw new Error('Stress bucket input must expose its canonical bucket ID.');
        await stressBucketInput.fill('-25');
        await page.getByTestId('risk-stress-run').click();
        await expect(page.getByTestId('risk-stress-impacts')).toBeVisible({timeout: 8_000});
        await expect(page.getByTestId('risk-stress-audit')).toBeVisible();
        await expect(page.getByTestId(`risk-stress-audit-asset-${assetId}`)).toBeVisible();

        await page.getByTestId('risk-replay-proxy-select-trigger').click();
        const proxyOption = page.getByTestId(/^search-select-option-\d+$/).first();
        await expect(proxyOption).toBeVisible({timeout: 5_000});
        const proxyOptionTestId = await proxyOption.getAttribute('data-testid');
        const proxyAssetId = Number(proxyOptionTestId?.replace('search-select-option-', ''));
        if (!Number.isInteger(proxyAssetId) || proxyAssetId <= 0) throw new Error('Replay proxy option must expose a numeric asset ID.');
        await proxyOption.click();
        await page.getByTestId('risk-replay-run').click();
        await expect(page.getByTestId('risk-replay-audit')).toBeVisible({timeout: 8_000});
        await expect(page.getByTestId(`risk-replay-audit-proxy-${assetId}`)).toBeVisible();
        await expect(page.getByTestId('risk-replay-audit-missing-history-policy')).toBeVisible();
        await expect(page.getByTestId('risk-replay-audit-composition-policy')).toBeVisible();
        await expect(page.getByTestId('risk-replay-audit-proxy-series-usage')).toBeVisible();

        const simulationQuery = page.waitForRequest(
            (request) => {
                if (request.method() !== 'POST' || !request.url().includes('/api/v1/risk/query')) return false;
                const body = request.postDataJSON() as RiskRequest;
                return body.analytics.some((analytic) => analytic.analytic_code === 'simulation');
            },
            {timeout: 10_000},
        );
        await expect(page.getByTestId('risk-simulation-run')).toBeEnabled();
        await page.getByTestId('risk-simulation-run').click();
        await simulationQuery;
        await expect(page.getByTestId('risk-simulation-chart')).toBeVisible({timeout: 12_000});
        await expect(page.getByTestId('risk-simulation-assumptions')).toBeVisible();
        await page.getByTestId('risk-simulation-view-terminal').click();
        await expect(page.getByTestId('risk-simulation-terminal-distribution')).toBeVisible({timeout: 5_000});

        await expect
            .poll(
                () => {
                    const assetRequests = requests.filter((request) => request.scope.kind === 'asset' && request.scope.asset_id === assetId);
                    return new Set(assetRequests.flatMap((request) => request.analytics.map((analytic) => analytic.analytic_code)));
                },
                {timeout: 15_000},
            )
            .toEqual(new Set(['comparison', 'historical_kpi', 'historical_var', 'simulation', 'stress']));

        const hypotheticalRequest = requests.flatMap((request) => request.analytics).find((analytic) => analytic.analytic_code === 'stress' && analytic.parameters?.method === 'hypothetical');
        expect(hypotheticalRequest?.parameters).toMatchObject({
            method: 'hypothetical',
            dimension: 'asset_class',
            bucket_shocks: {
                [stressBucketId]: -0.25,
            },
        });

        const replayRequest = requests.flatMap((request) => request.analytics).find((analytic) => analytic.analytic_code === 'stress' && analytic.parameters?.method === 'historical_replay');
        expect(replayRequest?.parameters).toMatchObject({
            method: 'historical_replay',
            missing_history_policy: 'manual_proxy_or_exclude',
            proxy_assets: [{asset_id: assetId, proxy_asset_id: proxyAssetId}],
            excluded_assets: [],
        });

        const simulationRequest = requests.flatMap((request) => request.analytics).find((analytic) => analytic.analytic_code === 'simulation');
        expect(simulationRequest?.parameters).toMatchObject({
            sampling_method: 'mc',
            path_count: 8192,
            random_seed: 123456,
        });
        expect(simulationRequest?.parameters).not.toHaveProperty('seed');
    });
});
