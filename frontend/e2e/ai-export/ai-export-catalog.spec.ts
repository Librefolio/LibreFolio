import {expect, test, type Page} from '@playwright/test';

import {gotoDashboard, gotoFirstAsset, gotoFirstBroker, gotoFx, openAiExportPanel, readVisibleSelectionIds, setupAiExportPage} from './helpers';

const DATASETS = {
    portfolio: ['portfolio.overview', 'portfolio.performance_flows', 'portfolio.technical_summary', 'portfolio.asset_snapshot', 'portfolio.asset_comparison', 'portfolio.drawdown_context', 'portfolio.income_evidence', 'portfolio.technical', 'portfolio.fifo', 'portfolio.all_data'],
    broker: ['broker.overview', 'broker.performance_flows', 'broker.technical_summary', 'broker.asset_comparison', 'broker.drawdown_context', 'broker.concentration_evidence', 'broker.cost_efficiency_evidence', 'broker.technical', 'broker.fifo', 'broker.all_data'],
    asset: ['asset.overview', 'asset.position_performance', 'asset.position_context', 'asset.drawdown_context', 'asset.market_technical', 'asset.all_data'],
    fx: ['fx.overview', 'fx.market_context', 'fx.conversion_timing_context', 'fx.market_technical', 'fx.direct_exposure', 'fx.all_data'],
} as const;

const ANALYSES = {
    portfolio: ['portfolio.pac_planning', 'portfolio.rebalancing', 'portfolio.performance_attribution', 'portfolio.market_events_review', 'portfolio.income_review', 'portfolio.fifo_review', 'portfolio.technical_breadth', 'portfolio.description'],
    broker: ['broker.review', 'broker.cost_efficiency', 'broker.concentration_context', 'broker.fifo_review'],
    asset: ['asset.trend_analysis', 'asset.position_review'],
    fx: ['fx.trend_review', 'fx.conversion_timing', 'fx.exposure_impact'],
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

test.describe('AI Export V2 catalog', () => {
    test.beforeEach(async ({context, page}) => {
        await context.grantPermissions(['clipboard-read', 'clipboard-write']);
        await setupAiExportPage(page);
    });

    test('shows exact Portfolio Dataset and Analysis IDs plus market-events label/icon', async ({page}) => {
        await gotoDashboard(page);
        await expectDomainCatalog(page, DATASETS.portfolio, ANALYSES.portfolio);

        const panel = await openAiExportPanel(page);
        await page.getByTestId('ai-export-category-analysis').click();
        await page.getByTestId('ai-export-selection-button').click();

        const marketEvents = page.getByTestId('ai-export-selection-option-portfolio.market_events_review');
        await expect(marketEvents).toContainText('Portfolio News & Price Drivers', {timeout: 2_000});
        const icon = page.getByTestId('ai-export-selection-option-portfolio.market_events_review-icon');
        await expect(icon).toBeVisible({timeout: 2_000});
        expect((await icon.getAttribute('class')) ?? '').toContain('lucide-newspaper');

        await marketEvents.click();
        await page.keyboard.press('Escape');
        await expect(panel.menu).toBeHidden({timeout: 2_000});
    });

    test('shows only Broker V2 selections on Broker Detail', async ({page}) => {
        await gotoFirstBroker(page);
        await expectDomainCatalog(page, DATASETS.broker, ANALYSES.broker);
    });

    test('shows only Asset V2 selections on Asset Detail', async ({page}) => {
        await gotoFirstAsset(page);
        await expectDomainCatalog(page, DATASETS.asset, ANALYSES.asset);
    });

    test('shows only FX V2 selections on FX Detail', async ({page}) => {
        await gotoFx(page, 'EUR-USD');
        await expectDomainCatalog(page, DATASETS.fx, ANALYSES.fx);
    });
});
