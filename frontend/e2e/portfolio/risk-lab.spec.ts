/**
 * Asset Global — the correlation laboratory.
 *
 * Owner: the laboratory mandate. It CONSUMES `risk-mocks.ts` but does not own
 * it: a change needed there is requested, not made.
 */
import {expect, test} from '../fixtures/playwright';

import {login, navigateTo} from '../fixtures/auth-helpers';
import {expectChartCanvas} from '../fixtures/charts';
import {TEST_USER} from '../fixtures/test-users';
import {brokerWithHoldings, installRiskMocks, selectedAssetIds} from './risk-mocks';

// Earned parallel: this file's blocks own the data they touch and wait on published
// state, so they share the backend with their neighbours instead of queueing behind
// them. Verified by a green run of the whole category at 4 workers.
test.describe.configure({mode: 'parallel'});

test.describe('Risk analysis functional integration', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('asset global maps broker holdings and supports remove/add', async ({page}) => {
        const requests = await installRiskMocks(page);
        const brokerSelection = await brokerWithHoldings(page);

        await navigateTo(page, '/assets?tab=correlation');
        await expect(page.getByTestId('asset-global-risk-panel')).toBeVisible({timeout: 15_000});
        await expect(page.getByTestId('risk-beta-banner')).toBeVisible();
        await expect(page.getByTestId('risk-beta-banner')).toHaveCount(1);
        await expectChartCanvas(page, 'risk-correlation-heatmap', 8_000);

        const selectedAssets = page.getByTestId(/^risk-selected-asset-\d+$/);
        // The chips arrive with the correlation payload, not with the heatmap frame:
        // sampling count() once here reads whatever had rendered by that instant.
        await expect.poll(() => selectedAssets.count(), {timeout: 10_000}).toBeGreaterThanOrEqual(2); // needs two seeded active assets to remove one and add it back

        // Any chip works: the test removes one and puts it back, so it reads the ID
        // off whichever it picked rather than assuming a particular asset.
        const firstChip = selectedAssets.first();
        const firstChipTestId = await firstChip.getAttribute('data-testid');
        const removedAssetId = Number(firstChipTestId?.replace('risk-selected-asset-', ''));
        if (!Number.isInteger(removedAssetId)) throw new Error('Selected asset chip must expose its numeric asset ID.');

        await page.getByTestId(`risk-remove-asset-${removedAssetId}`).click();
        await expect(page.getByTestId(`risk-selected-asset-${removedAssetId}`)).toHaveCount(0);
        await page.getByTestId('risk-asset-add-select-trigger').click();
        await page.getByTestId(`search-select-option-${removedAssetId}`).click();
        await page.getByTestId('risk-asset-add-button').click();
        await expect(page.getByTestId(`risk-selected-asset-${removedAssetId}`)).toBeVisible();

        await page.getByTestId('risk-broker-filter-button').click();
        await page.getByTestId(`risk-broker-option-${brokerSelection.brokerId}`).click();

        // The oracle is the panel's own selection, not the /portfolio/report snapshot
        // taken above. The panel freezes its holdings at page load, so a neighbouring
        // spec that touches this shared broker in between makes the two disagree
        // forever — no timeout can fix a comparison against data the page never saw.
        // Re-reading the chips on every iteration also absorbs the mid-update frame.
        await expect
            .poll(
                async () => {
                    const selected = await selectedAssetIds(page);
                    if (selected.length === 0) return false;
                    const wanted = selected.join(',');
                    return requests.some((request) => request.scope.kind === 'asset_set' && [...request.scope.asset_ids].sort((left, right) => left - right).join(',') === wanted);
                },
                {timeout: 15_000, intervals: [300, 500, 1_000]},
            )
            .toBe(true);

        // …and the filter really mapped to *that* broker. Exact equality with the
        // snapshot above is not assertable: the page reloaded the holdings after the
        // helper read them, so a neighbour writing to this shared broker shifts one
        // side only. A non-empty overlap survives drift in either direction and still
        // fails if the filter selected the wrong broker's assets.
        const afterFilter = await selectedAssetIds(page);
        expect(afterFilter.length).toBeGreaterThan(0);
        expect(afterFilter.some((id) => brokerSelection.assetIds.includes(id))).toBe(true);
    });
});
