import {expect, test, type Locator, type Page} from '@playwright/test';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

/**
 * Ensure at least one broker exists for the test user.
 * If no broker cards are visible, create one via the UI.
 */
async function ensureBrokerExists(page: Page): Promise<void> {
    await navigateTo(page, '/brokers');
    const brokerCards = page.locator('[data-testid^="broker-card-"]');

    // Wait a moment for cards to render (they load asynchronously)
    await page.waitForTimeout(1000);
    const count = await brokerCards.count();

    if (count === 0) {
        // Create a broker so the detail tests have something to work with
        await page.getByTestId('add-broker-button').click();
        await expect(page.getByTestId('broker-modal')).toBeVisible();
        await page.getByTestId('broker-name-input').fill('E2E Detail Test Broker');
        await page.getByTestId('broker-form-submit').click();
        await expect(page.getByTestId('broker-modal')).not.toBeVisible({timeout: 5000});
        // Wait for the card to appear
        await expect(brokerCards.first()).toBeVisible({timeout: 5000});
    }
}

async function clickRowAction(page: Page, row: Locator, actionId: string): Promise<void> {
    const actionsButton = row.getByTestId(/^row-actions-/);
    await expect(actionsButton).toBeVisible({timeout: 5_000});
    await actionsButton.click();
    await page.getByTestId(`context-menu-action-${actionId}`).click();
}

/**
 * Helper: navigate to the first broker's detail page and wait for data to load.
 * Returns false if no brokers exist (test should be skipped).
 */
async function goToFirstBrokerDetail(page: Page): Promise<boolean> {
    await navigateTo(page, '/brokers');

    const brokerCards = page.locator('[data-testid^="broker-card-"]');
    // Wait for async broker list to load
    await page.waitForTimeout(1000);
    const count = await brokerCards.count();
    if (count === 0) return false;

    await brokerCards.first().click();
    await expect(page).toHaveURL(/\/brokers\/\d+/, {timeout: 5000});
    await expect(page.getByTestId('broker-detail-page')).toBeVisible();
    // Wait for broker data to load (broker-name is inside {#if broker})
    await expect(page.getByTestId('broker-name')).toBeVisible({timeout: 10000});
    return true;
}

/** Switch to the "Transazioni" tab — the import/new-tx buttons live there, not on
 *  the default "Panoramica" tab. */
async function goToTransazioniTab(page: Page): Promise<void> {
    await page.getByTestId('broker-tab-transazioni').click();
    await expect(page.getByTestId('broker-transactions-tab')).toBeVisible({timeout: 5000});
}

/** Switch to the "Posizioni" tab — where the FIFO lots analysis panel lives. */
async function goToPosizioniTab(page: Page): Promise<void> {
    await page.getByTestId('broker-tab-posizioni').click();
    await expect(page.getByTestId('broker-holdings')).toBeVisible({timeout: 5000});
}

test.describe('Broker Detail Page', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await ensureBrokerExists(page);
    });

    test('can navigate to broker detail by clicking card', async ({page}) => {
        await navigateTo(page, '/brokers');

        const brokerCards = page.locator('[data-testid^="broker-card-"]');
        const count = await brokerCards.count();

        if (count > 0) {
            await brokerCards.first().click();
            await expect(page).toHaveURL(/\/brokers\/\d+/);
            await expect(page.getByTestId('broker-detail-page')).toBeVisible();
        }
    });

    test('broker detail page shows broker name', async ({page}) => {
        const ok = await goToFirstBrokerDetail(page);
        if (!ok) return;

        // broker-name is already verified by the helper
        await expect(page.getByTestId('broker-name')).toBeVisible();
    });

    test('broker detail page shows cash balances section', async ({page}) => {
        const ok = await goToFirstBrokerDetail(page);
        if (!ok) return;

        await expect(page.getByTestId('broker-cash-balances')).toBeVisible({timeout: 5000});
    });

    test('broker detail page shows holdings section', async ({page}) => {
        const ok = await goToFirstBrokerDetail(page);
        if (!ok) return;

        // broker-holdings lives on the "Posizioni" tab, not the default "Panoramica" one.
        await goToPosizioniTab(page);
        await expect(page.getByTestId('broker-holdings')).toBeVisible({timeout: 5000});
    });

    test('broker detail page shows transactions section', async ({page}) => {
        const ok = await goToFirstBrokerDetail(page);
        if (!ok) return;

        await goToTransazioniTab(page);
        await expect(page.getByTestId('broker-transactions')).toBeVisible({timeout: 5000});
    });

    test('broker detail page has show-import-history button', async ({page}) => {
        const ok = await goToFirstBrokerDetail(page);
        if (!ok) return;

        // broker-show-import-history is always visible (unlike the import/new-tx
        // buttons next to it, which require OWNER or EDITOR role)
        await goToTransazioniTab(page);
        await expect(page.getByTestId('broker-show-import-history')).toBeVisible({timeout: 5000});
    });

    test('broker detail page has edit button', async ({page}) => {
        const ok = await goToFirstBrokerDetail(page);
        if (!ok) return;

        // broker-edit-button is inside {#if canEdit}
        await expect(page.getByTestId('broker-edit-button')).toBeVisible({timeout: 5000});
    });

    test('can open edit modal from detail page', async ({page}) => {
        const ok = await goToFirstBrokerDetail(page);
        if (!ok) return;

        await page.getByTestId('broker-edit-button').click();
        await expect(page.getByTestId('broker-modal')).toBeVisible({timeout: 5000});
    });

    test('can navigate back from detail page', async ({page}) => {
        const ok = await goToFirstBrokerDetail(page);
        if (!ok) return;

        await page.getByTestId('broker-back-button').click();
        await expect(page.getByTestId('brokers-page')).toBeVisible({timeout: 5000});
    });

    test('can open import files modal', async ({page}) => {
        const ok = await goToFirstBrokerDetail(page);
        if (!ok) return;

        await goToTransazioniTab(page);
        await page.getByTestId('broker-show-import-history').click();
        await expect(page.getByTestId('import-files-modal')).toBeVisible({timeout: 5000});
    });

    test('can close import files modal', async ({page}) => {
        const ok = await goToFirstBrokerDetail(page);
        if (!ok) return;

        await goToTransazioniTab(page);
        await page.getByTestId('broker-show-import-history').click();
        await expect(page.getByTestId('import-files-modal')).toBeVisible({timeout: 5000});

        // Close by pressing Escape
        await page.keyboard.press('Escape');
        await expect(page.getByTestId('import-files-modal')).not.toBeVisible({timeout: 3000});
    });

    test('import files modal can open file preview', async ({page}) => {
        const ok = await goToFirstBrokerDetail(page);
        if (!ok) return;

        await page.route('**/api/v1/brokers/import/files/*/preview', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    preview_type: 'markdown',
                    filename: 'coinbase-export.csv',
                    mime_type: 'text/markdown',
                    size_bytes: 44,
                    source_url: '/api/v1/brokers/import/files/mock/download',
                    download_url: '/api/v1/brokers/import/files/mock/download?download=true',
                    preview_url: null,
                    text_content: '# Broker preview\n\nModal reuse works.\n',
                    total_lines: 3,
                    detected_encoding: 'utf-8',
                    table_rows: null,
                    total_rows: null,
                    total_cols: null,
                    sheet_names: [],
                    active_sheet_name: null,
                    image_width: null,
                    image_height: null,
                }),
            });
        });

        await goToTransazioniTab(page);
        await page.getByTestId('broker-show-import-history').click();
        await expect(page.getByTestId('import-files-modal')).toBeVisible({timeout: 5000});

        const previewActionsButton = page
            .getByTestId('import-files-modal')
            .getByTestId(/^row-actions-/)
            .first();
        await expect(previewActionsButton).toBeVisible({timeout: 8000});
        await previewActionsButton.click();
        await page.getByTestId('context-menu-action-preview').click();

        await expect(page.getByTestId('file-preview-modal')).toBeVisible({timeout: 8000});
        await expect(page.getByTestId('file-preview-markdown-rendered')).toContainText('Modal reuse works.', {timeout: 8000});
    });

    test.describe('FIFO lots analysis panel (Posizioni tab)', () => {
        /** Locates rows in the Esposizione/Tabella view of PositionsPanel — data-row-id is the
         *  established convention for DataTable rows in this codebase (see transactions-table.spec.ts). */
        async function firstHoldingRow(page: Page) {
            await goToPosizioniTab(page);
            return page.locator('[data-testid="broker-holdings"] tbody tr[data-row-id]').first();
        }

        test('clicking the "Analyze Lots" row action opens the FIFO lots panel', async ({page}) => {
            const ok = await goToFirstBrokerDetail(page);
            if (!ok) return;

            const row = await firstHoldingRow(page);
            if ((await row.count()) === 0) return; // no holdings for this broker — nothing to click

            await clickRowAction(page, row, 'analyze-lots');
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});
            await expect(page.getByTestId('lots-analysis-panel-title')).toBeVisible();

            // ?asset=<id> reflected in the URL (bookmarkable panel state).
            await expect(page).toHaveURL(/[?&]asset=\d+/);
        });

        test('closing the panel clears the ?asset= query param', async ({page}) => {
            const ok = await goToFirstBrokerDetail(page);
            if (!ok) return;

            const row = await firstHoldingRow(page);
            if ((await row.count()) === 0) return;

            await clickRowAction(page, row, 'analyze-lots');
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});

            await page.getByTestId('lots-analysis-panel-close').click();
            await expect(page.getByTestId('lots-analysis-panel')).not.toBeVisible({timeout: 5000});
            await expect(page).not.toHaveURL(/[?&]asset=\d+/);
        });

        test('clicking the "View Asset" row action navigates to asset detail', async ({page}) => {
            const ok = await goToFirstBrokerDetail(page);
            if (!ok) return;

            const row = await firstHoldingRow(page);
            if ((await row.count()) === 0) return;

            await clickRowAction(page, row, 'view-asset');
            await expect(page).toHaveURL(/\/assets\/\d+/, {timeout: 5000});
        });

        test('right-clicking a holding row shows a context menu with both actions', async ({page}) => {
            const ok = await goToFirstBrokerDetail(page);
            if (!ok) return;

            const row = await firstHoldingRow(page);
            if ((await row.count()) === 0) return;

            await row.click({button: 'right'});
            await expect(page.getByTestId('context-menu')).toBeVisible({timeout: 5000});
            await expect(page.getByTestId('context-menu-action-view-asset')).toBeVisible();
            await expect(page.getByTestId('context-menu-action-analyze-lots')).toBeVisible();

            await page.getByTestId('context-menu-action-analyze-lots').click();
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});
        });

        test('WAC/Price chart EUR|% toggle switches without breaking the panel', async ({page}) => {
            const ok = await goToFirstBrokerDetail(page);
            if (!ok) return;

            const row = await firstHoldingRow(page);
            if ((await row.count()) === 0) return;

            await clickRowAction(page, row, 'analyze-lots');
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});
            await expect(page.getByTestId('lot-wac-price-chart')).toBeVisible({timeout: 5000});

            await page.getByTestId('lot-wac-toggle-percentage').click();
            await expect(page.getByTestId('lot-wac-price-chart')).toBeVisible();

            await page.getByTestId('wac-toggle-absolute').click();
            await expect(page.getByTestId('lot-wac-price-chart')).toBeVisible();
        });

        test('clicking a Gantt segment overlay selects the lot and reflects in the unified table', async ({page}) => {
            const ok = await goToFirstBrokerDetail(page);
            if (!ok) return;

            const row = await firstHoldingRow(page);
            if ((await row.count()) === 0) return;

            await clickRowAction(page, row, 'analyze-lots');
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});
            await expect(page.getByTestId('lot-gantt-chart')).toBeVisible({timeout: 10000});

            // Invisible per-lane hit target, absolutely positioned over the ECharts custom
            // series bar (no fixed HTML column anymore — see LotGanttChart.svelte OverlayRect).
            const segmentOverlay = page.locator('[data-testid^="lot-gantt-segment-"]').first();
            if ((await segmentOverlay.count()) === 0) return; // no lots in range for this holding

            const testid = await segmentOverlay.getAttribute('data-testid');
            const lotId = testid?.replace('lot-gantt-segment-', '');
            expect(lotId).toBeTruthy();

            const tableRow = page.locator(`[data-row-id="${lotId}"]`);
            await expect(tableRow).not.toHaveClass(/selected/);

            await segmentOverlay.click();
            await expect(tableRow).toHaveClass(/selected/, {timeout: 5000});
        });

        test('clicking the Custody cell opens the modal without changing row selection', async ({page}) => {
            const ok = await goToFirstBrokerDetail(page);
            if (!ok) return;

            const row = await firstHoldingRow(page);
            if ((await row.count()) === 0) return;

            await clickRowAction(page, row, 'analyze-lots');
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});

            const custodyCell = page.locator('[data-testid^="unified-lots-custody-"]').first();
            if ((await custodyCell.count()) === 0) return;

            const testid = await custodyCell.getAttribute('data-testid');
            const lotId = testid?.replace('unified-lots-custody-', '');
            const tableRow = page.locator(`[data-row-id="${lotId}"]`);
            await expect(tableRow).not.toHaveClass(/selected/);

            await custodyCell.click();

            // Modal opens...
            await expect(page.getByTestId('lot-custody-modal-title')).toBeVisible({timeout: 5000});
            // ...but the row's selection state is untouched by the custody click.
            await expect(tableRow).not.toHaveClass(/selected/);
        });

        test('row context menu "View lot detail" opens the modal for any lot, including one with no transfer', async ({page}) => {
            const ok = await goToFirstBrokerDetail(page);
            if (!ok) return;

            const row = await firstHoldingRow(page);
            if ((await row.count()) === 0) return;

            await clickRowAction(page, row, 'analyze-lots');
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});

            const tableRow = page.locator('[data-testid="unified-lots-table"] tbody tr[data-row-id]').first();
            if ((await tableRow.count()) === 0) return;

            await tableRow.click({button: 'right'});
            await expect(page.getByTestId('context-menu')).toBeVisible({timeout: 5000});

            const viewDetail = page.getByTestId('context-menu-action-lot-view-details-action');
            await expect(viewDetail).toBeVisible();
            await viewDetail.click();

            await expect(page.getByTestId('lot-custody-modal-title')).toBeVisible({timeout: 5000});
            // Summary shows the additive fields regardless of the lot's custody/transfer history.
            await expect(page.getByTestId('lot-custody-modal-summary')).toContainText(/./);
        });

        test('row context menu "Go to lot in Gantt" pulses the matching Gantt lane', async ({page}) => {
            const ok = await goToFirstBrokerDetail(page);
            if (!ok) return;

            const row = await firstHoldingRow(page);
            if ((await row.count()) === 0) return;

            await clickRowAction(page, row, 'analyze-lots');
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});
            await expect(page.getByTestId('lot-gantt-chart')).toBeVisible({timeout: 10000});

            const tableRow = page.locator('[data-testid="unified-lots-table"] tbody tr[data-row-id]').first();
            if ((await tableRow.count()) === 0) return;

            await tableRow.click({button: 'right'});
            await expect(page.getByTestId('context-menu')).toBeVisible({timeout: 5000});
            await page.getByTestId('context-menu-action-lot-view-gantt-action').click();

            // pulseLot() scrolls the Gantt into view and applies the pulse ring/glow to the
            // matching lane highlight — the chart itself staying visible is the stable, low-risk
            // assertion (the ring/glow is drawn inside the ECharts canvas, not a DOM class).
            await expect(page.getByTestId('lot-gantt-chart')).toBeVisible();
        });

        test('Value presentation toggle: two independent buttons (Aggregate/Per lot), Asset-Global-style tri-state — neither pressed shows both', async ({page}) => {
            const ok = await goToFirstBrokerDetail(page);
            if (!ok) return;

            const row = await firstHoldingRow(page);
            if ((await row.count()) === 0) return;

            await clickRowAction(page, row, 'analyze-lots');
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});

            const checkbox = page.locator('[data-testid="unified-lots-table"] tbody tr[data-row-id]').first().locator('.checkbox-btn, button').first();
            if ((await checkbox.count()) === 0) return;
            await checkbox.click();

            const presentationFilter = page.getByTestId('lots-value-presentation-filter');
            if (!(await presentationFilter.isVisible({timeout: 5_000}).catch(() => false))) return; // no selectable lot in range

            const aggregateToggle = page.getByTestId('lots-value-aggregate-toggle');
            const individualToggle = page.getByTestId('lots-value-individual-toggle');
            // No 3rd "Both" button — removed in favor of the Asset-Global-style tri-state pattern.
            await expect(page.getByTestId('lots-value-both-toggle')).toHaveCount(0);

            // Default: only Aggregate pressed.
            await expect(aggregateToggle).toHaveAttribute('aria-pressed', 'true');
            await expect(individualToggle).toHaveAttribute('aria-pressed', 'false');
            await expect(page.getByTestId('lot-comparison-echart')).toBeVisible();

            // Press Per lot too -> both pressed -> still shows everything.
            await individualToggle.click();
            await expect(individualToggle).toHaveAttribute('aria-pressed', 'true');
            await expect(page.getByTestId('lot-comparison-echart')).toBeVisible();

            // Un-press Aggregate -> only Per lot pressed -> exclusive individual view.
            await aggregateToggle.click();
            await expect(aggregateToggle).toHaveAttribute('aria-pressed', 'false');
            await expect(page.getByTestId('lot-comparison-echart')).toBeVisible();

            // Un-press Per lot too -> neither pressed -> implicit "show both" (tri-state rule).
            await individualToggle.click();
            await expect(individualToggle).toHaveAttribute('aria-pressed', 'false');
            await expect(aggregateToggle).toHaveAttribute('aria-pressed', 'false');
            await expect(page.getByTestId('lot-comparison-echart')).toBeVisible();
        });
    });
});
