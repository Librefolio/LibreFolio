import {expect, test, type Page} from '@playwright/test';
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

        const previewButton = page.getByTestId('row-action-preview').first();
        await expect(previewButton).toBeVisible({timeout: 8000});
        await previewButton.click();

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

            await row.getByTestId('row-action-analyze-lots').click();
            await expect(page.getByTestId('fifo-lots-panel')).toBeVisible({timeout: 5000});
            await expect(page.getByTestId('fifo-lots-panel-title')).toBeVisible();

            // ?asset=<id> reflected in the URL (bookmarkable panel state).
            await expect(page).toHaveURL(/[?&]asset=\d+/);
        });

        test('closing the panel clears the ?asset= query param', async ({page}) => {
            const ok = await goToFirstBrokerDetail(page);
            if (!ok) return;

            const row = await firstHoldingRow(page);
            if ((await row.count()) === 0) return;

            await row.getByTestId('row-action-analyze-lots').click();
            await expect(page.getByTestId('fifo-lots-panel')).toBeVisible({timeout: 5000});

            await page.getByTestId('fifo-lots-panel-close').click();
            await expect(page.getByTestId('fifo-lots-panel')).not.toBeVisible({timeout: 5000});
            await expect(page).not.toHaveURL(/[?&]asset=\d+/);
        });

        test('clicking the "View Asset" row action navigates to asset detail', async ({page}) => {
            const ok = await goToFirstBrokerDetail(page);
            if (!ok) return;

            const row = await firstHoldingRow(page);
            if ((await row.count()) === 0) return;

            await row.getByTestId('row-action-view-asset').click();
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
            await expect(page.getByTestId('fifo-lots-panel')).toBeVisible({timeout: 5000});
        });

        test('WAC/Price chart EUR|% toggle switches without breaking the panel', async ({page}) => {
            const ok = await goToFirstBrokerDetail(page);
            if (!ok) return;

            const row = await firstHoldingRow(page);
            if ((await row.count()) === 0) return;

            await row.getByTestId('row-action-analyze-lots').click();
            await expect(page.getByTestId('fifo-lots-panel')).toBeVisible({timeout: 5000});
            await expect(page.getByTestId('asset-wac-price-chart')).toBeVisible({timeout: 5000});

            await page.getByTestId('asset-wac-price-mode-percent').click();
            await expect(page.getByTestId('asset-wac-price-chart')).toBeVisible();

            await page.getByTestId('asset-wac-price-mode-eur').click();
            await expect(page.getByTestId('asset-wac-price-chart')).toBeVisible();
        });
    });
});
