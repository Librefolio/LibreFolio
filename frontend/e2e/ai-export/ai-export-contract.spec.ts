import {expect, test, type Page} from '@playwright/test';

import {API_TIMEOUT, exportCurrentSelection, gotoDashboard, gotoFirstBroker, gotoFx, gotoSeededAsset, isSnapshotPost, numericScopeId, openAiExportPanel, selectAiExportSelection, setupAiExportPage, waitForClipboard} from './helpers';

const ASSET_OVERVIEW_FIXTURE = {
    displayName: 'Apple Inc.',
    ticker: 'AAPL',
} as const;

interface ExpectedDatasetRequest {
    readonly domain: 'portfolio' | 'broker' | 'asset' | 'fx';
    readonly id: string;
    readonly brokerId?: number;
    readonly assetId?: number;
    readonly baseCurrency?: string;
    readonly quoteCurrency?: string;
}

function expectIsoPeriod(payload: Record<string, unknown>): void {
    const period = payload.period as {start?: unknown; end?: unknown};
    expect(period.start).toEqual(expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/));
    expect(period.end).toEqual(expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/));
    expect(String(period.start) < String(period.end)).toBe(true);
}

function expectUppercaseCurrency(value: unknown, field: string): void {
    expect(typeof value, `${field} must be a string`).toBe('string');
    expect(value, `${field} must be uppercase`).toBe(String(value).toUpperCase());
    expect(value, `${field} must contain uppercase letters only`).toEqual(expect.stringMatching(/^[A-Z]+$/));
}

function expectDatasetRequest(payload: Record<string, unknown>, expected: ExpectedDatasetRequest): void {
    expect(payload.domain).toBe(expected.domain);
    expect(payload.selection).toEqual({
        kind: 'dataset',
        id: expected.id,
        version: 3,
    });
    expect(payload.detail_level).toBe('compact');
    expect(payload.expected_catalog_version).toBe(3);
    expectUppercaseCurrency(payload.target_currency, 'target_currency');
    expectIsoPeriod(payload);

    if (expected.domain === 'portfolio') {
        expect(payload).not.toHaveProperty('broker_ids');
        expect(payload).not.toHaveProperty('broker_id');
        expect(payload).not.toHaveProperty('asset_id');
        expect(payload).not.toHaveProperty('base_currency');
        expect(payload).not.toHaveProperty('quote_currency');
    } else if (expected.domain === 'broker') {
        expect(payload.broker_id).toBe(expected.brokerId);
        expect(payload).not.toHaveProperty('broker_ids');
        expect(payload).not.toHaveProperty('asset_id');
        expect(payload).not.toHaveProperty('base_currency');
        expect(payload).not.toHaveProperty('quote_currency');
    } else if (expected.domain === 'asset') {
        expect(payload.asset_id).toBe(expected.assetId);
        expect(payload).not.toHaveProperty('broker_ids');
        expect(payload).not.toHaveProperty('broker_id');
        expect(payload).not.toHaveProperty('base_currency');
        expect(payload).not.toHaveProperty('quote_currency');
    } else {
        expect(payload.base_currency).toBe(expected.baseCurrency);
        expect(payload.quote_currency).toBe(expected.quoteCurrency);
        expect(payload).not.toHaveProperty('broker_ids');
        expect(payload).not.toHaveProperty('broker_id');
        expect(payload).not.toHaveProperty('asset_id');
    }
}

async function exportDataset(page: Page, id: string): Promise<Record<string, unknown>> {
    await openAiExportPanel(page);
    await selectAiExportSelection(page, 'dataset', id);
    await page.getByTestId('ai-export-detail-compact').click();
    return (await exportCurrentSelection(page)).payload;
}

async function captureDatasetRequest(page: Page, id: string): Promise<Record<string, unknown>> {
    const panel = await openAiExportPanel(page);
    await selectAiExportSelection(page, 'dataset', id);
    await page.getByTestId('ai-export-detail-compact').click();

    const requestPromise = page.waitForRequest(isSnapshotPost, {timeout: 8_000});
    const responsePromise = page.waitForResponse((response) => isSnapshotPost(response.request()), {timeout: API_TIMEOUT});
    await page.getByTestId('ai-export-copy-button').click();
    const [request, response] = await Promise.all([requestPromise, responsePromise]);
    const failureBody = response.status() === 200 ? '' : await response.text();
    expect(response.status(), failureBody).toBe(200);

    if (await panel.menu.isVisible()) {
        await page.keyboard.press('Escape');
        await expect(panel.menu).toBeHidden({timeout: 2_000});
    }
    return request.postDataJSON() as Record<string, unknown>;
}

test.setTimeout(120_000);

test.describe('AI Export request and clipboard contract', () => {
    test.beforeEach(async ({context, page}) => {
        await context.grantPermissions(['clipboard-read', 'clipboard-write']);
        await setupAiExportPage(page);
    });

    test('sends V3 Dataset request shape and domain scope across all surfaces', async ({page}) => {
        await test.step('Portfolio Dataset', async () => {
            await gotoDashboard(page);
            const payload = await exportDataset(page, 'portfolio.overview_and_history');
            expectDatasetRequest(payload, {
                domain: 'portfolio',
                id: 'portfolio.overview_and_history',
            });

            const clipboard = await waitForClipboard(page, ['Snapshot Metadata and Dataset Manifest', 'Snapshot Data'], 'Portfolio Dataset clipboard was not populated');
            expect(clipboard).not.toContain('Analysis Objective');
            expect(clipboard).not.toContain('Response Contract');
            expect(clipboard).not.toContain('User Notes');
            expect(clipboard).not.toContain('Response Language');
        });

        await test.step('Broker Dataset', async () => {
            await gotoFirstBroker(page);
            const brokerId = numericScopeId(page, 'brokers');
            const payload = await captureDatasetRequest(page, 'broker.overview_and_history');
            expectDatasetRequest(payload, {
                domain: 'broker',
                id: 'broker.overview_and_history',
                brokerId,
            });
        });

        await test.step('Asset Dataset', async () => {
            await gotoSeededAsset(page, ASSET_OVERVIEW_FIXTURE);
            const assetId = numericScopeId(page, 'assets');
            const payload = await captureDatasetRequest(page, 'asset.position_and_history');
            expectDatasetRequest(payload, {
                domain: 'asset',
                id: 'asset.position_and_history',
                assetId,
            });
        });

        await test.step('FX Dataset', async () => {
            await gotoFx(page, 'EUR-USD');
            const payload = await captureDatasetRequest(page, 'fx.market_and_exposure');
            expectDatasetRequest(payload, {
                domain: 'fx',
                id: 'fx.market_and_exposure',
                baseCurrency: 'EUR',
                quoteCurrency: 'USD',
            });
        });
    });

    test('exports V3 performance-market-drivers analysis with dated research contract', async ({page}) => {
        await gotoDashboard(page);
        await openAiExportPanel(page);
        await selectAiExportSelection(page, 'analysis', 'portfolio.performance_market_drivers');
        await page.getByTestId('ai-export-detail-compact').click();

        const notes = 'Review dated drivers, conflicting evidence, and unexplained material moves.';
        await page.getByTestId('ai-export-user-notes').fill(notes);
        const {payload} = await exportCurrentSelection(page);

        expect(payload.domain).toBe('portfolio');
        expect(payload.selection).toEqual({
            kind: 'analysis',
            id: 'portfolio.performance_market_drivers',
            version: 3,
            instruction_template_id: 'portfolio.performance_market_drivers.instructions',
            instruction_template_version: 3,
            response_contract_id: 'portfolio.performance_market_drivers.response',
            response_contract_version: 3,
        });
        expect(payload.detail_level).toBe('compact');
        expect(payload.expected_catalog_version).toBe(3);
        expect(payload).not.toHaveProperty('broker_ids');
        expectUppercaseCurrency(payload.target_currency, 'target_currency');
        expectIsoPeriod(payload);

        const clipboard = await waitForClipboard(page, ['Analysis Objective', 'Response Contract', 'Snapshot Data', 'Response Language', 'User Notes', notes], 'Performance-market-drivers Analysis clipboard was not populated');
        expect(clipboard).toContain('assess dated market drivers for every held Asset without overstating causality');
        expect(clipboard).toContain('supported, plausible, inferred, speculative, or unexplained');
        expect(clipboard).toContain('Per-Asset Short- and Long-Horizon Thesis');
        expect(clipboard).toContain('Please provide your answer in: English.');
    });
});
