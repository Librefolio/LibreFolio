import {expect, test, type Page} from '../fixtures/playwright';

import {gotoDashboard, gotoFirstAsset, gotoFirstBroker, gotoFx, openAiExportPanel, readVisibleSelectionIds, setupAiExportPage} from './helpers';

const DATASETS = {
    portfolio: ['portfolio.overview_and_history', 'portfolio.asset_history'],
    broker: ['broker.overview_and_history', 'broker.asset_history'],
    asset: ['asset.position_and_history', 'asset.market_history'],
    fx: ['fx.market_and_exposure', 'fx.market_history'],
} as const;

const ANALYSES = {
    portfolio: ['portfolio.pac_planning', 'portfolio.rebalancing', 'portfolio.performance_market_drivers', 'portfolio.fiscal_lots'],
    broker: ['broker.review', 'broker.performance_market_drivers', 'broker.fiscal_lots'],
    asset: ['asset.position_review', 'asset.market_analysis'],
    fx: ['fx.pair_analysis', 'fx.exposure_impact'],
} as const;

async function expectDomainCatalog(page: Page, datasetIds: readonly string[], analysisIds: readonly string[]): Promise<void> {
    const panel = await openAiExportPanel(page);

    const datasetCategory = page.getByTestId('ai-export-category-dataset');
    await datasetCategory.click();
    await expect(datasetCategory).toHaveAttribute('aria-pressed', 'true', {timeout: 2_000});
    await expect(page.getByTestId('ai-export-category-analysis')).toHaveAttribute('aria-pressed', 'false', {timeout: 2_000});
    expect(await readVisibleSelectionIds(page)).toEqual(datasetIds);

    const analysisCategory = page.getByTestId('ai-export-category-analysis');
    await analysisCategory.click();
    await expect(analysisCategory).toHaveAttribute('aria-pressed', 'true', {timeout: 2_000});
    await expect(datasetCategory).toHaveAttribute('aria-pressed', 'false', {timeout: 2_000});
    expect(await readVisibleSelectionIds(page)).toEqual(analysisIds);

    await page.keyboard.press('Escape');
    await expect(panel.menu).toBeHidden({timeout: 2_000});
}

test.setTimeout(90_000);

test.describe('AI Export V1 catalog', () => {
    test.beforeEach(async ({context, page}) => {
        await context.grantPermissions(['clipboard-read', 'clipboard-write']);
        await setupAiExportPage(page);
    });

    test('shows exact Portfolio Dataset and Analysis IDs plus performance-driver label/icon', async ({page}) => {
        await gotoDashboard(page);
        await expectDomainCatalog(page, DATASETS.portfolio, ANALYSES.portfolio);

        const panel = await openAiExportPanel(page);
        await page.getByTestId('ai-export-category-analysis').click();
        await page.getByTestId('ai-export-selection-button').click();

        const marketDrivers = page.getByTestId('ai-export-selection-option-portfolio.performance_market_drivers');
        await expect(marketDrivers).toContainText('Portfolio Performance & Market Drivers', {timeout: 2_000});
        const icon = page.getByTestId('ai-export-selection-option-portfolio.performance_market_drivers-icon');
        await expect(icon).toBeVisible({timeout: 2_000});
        expect((await icon.getAttribute('class')) ?? '').toContain('lucide-newspaper');
        const lossOffset = page.getByTestId('ai-export-selection-option-portfolio.fiscal_lots');
        await expect(lossOffset).toContainText('Capital-Loss Offset Strategies', {timeout: 2_000});
        await expect(lossOffset).toContainText('official tax-loss inventory, jurisdiction, regime, expiries, and legal rules', {timeout: 2_000});

        await marketDrivers.click();
        await page.keyboard.press('Escape');
        await expect(panel.menu).toBeHidden({timeout: 2_000});
    });

    test('shows only Broker V1 selections on Broker Detail', async ({page}) => {
        await gotoFirstBroker(page);
        await expectDomainCatalog(page, DATASETS.broker, ANALYSES.broker);
    });

    test('shows only Asset V1 selections on Asset Detail', async ({page}) => {
        await gotoFirstAsset(page);
        await expectDomainCatalog(page, DATASETS.asset, ANALYSES.asset);
    });

    test('shows only FX V1 selections on FX Detail', async ({page}) => {
        await gotoFx(page, 'EUR-USD');
        await expectDomainCatalog(page, DATASETS.fx, ANALYSES.fx);
    });
});
