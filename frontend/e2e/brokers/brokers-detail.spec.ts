import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {expectChartCanvas, showChartTooltip} from '../fixtures/charts';
import {TEST_USER} from '../fixtures/test-users';
import {appears} from '../fixtures/probe';

/**
 * Ensure at least one broker exists for the test user.
 * If no broker cards are visible, create one via the UI.
 */
async function ensureBrokerExists(page: Page): Promise<void> {
    await navigateTo(page, '/brokers');
    const brokerCards = page.locator('[data-testid^="broker-card-"]');

    // The page says when its list has landed; a fixed sleep used to report zero cards
    // under load and send this helper down the "create one" path it never needed.
    await page.waitForSelector('[data-testid="brokers-page"][data-busy="false"]', {timeout: 20_000});
    const count = await brokerCards.count();

    if (count === 0) {
        // Create a broker so the detail tests have something to work with. The name must
        // be unique: a fixed one collides with a concurrent worker doing the same, and
        // the modal then stays open on the validation error.
        await page.getByTestId('add-broker-button').click();
        await expect(page.getByTestId('broker-modal')).toBeVisible();
        await page.getByTestId('broker-name-input').fill(`E2E Detail Test Broker ${Date.now()}-${process.pid}`);
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
/**
 * Opens the detail page of the first broker card on screen.
 *
 * The mock always ships seven brokers, so "no card appeared" is a failure and not a
 * reason to skip: returning a boolean here let every caller write `if (!ok) return`,
 * which marks a test green without testing anything.
 */
async function goToFirstBrokerDetail(page: Page): Promise<void> {
    await navigateTo(page, '/brokers');

    const brokerCards = page.locator('[data-testid^="broker-card-"]');
    await expect(brokerCards.first(), 'the mock always ships brokers — an empty list means the page never loaded').toBeVisible({timeout: 8_000});

    await brokerCards.first().click();
    await expect(page).toHaveURL(/\/brokers\/\d+/, {timeout: 5000});
    await expect(page.getByTestId('broker-detail-page')).toBeVisible();
    // Wait for broker data to load (broker-name is inside {#if broker})
    await expect(page.getByTestId('broker-name')).toBeVisible({timeout: 10000});
}

/** The one broker the mock fills with positions — see populate_mock_data.py. */
const BROKER_WITH_HOLDINGS = 'Interactive Brokers';

/**
 * Opens the broker that actually has positions.
 *
 * "The first card" is not an identity. The list is ordered by name and other specs
 * legitimately create brokers of their own, so `.first()` landed on whatever happened to
 * sort first — frequently one with no positions at all. Every test below then hit
 * `if (rows === 0) return` and reported green without exercising a single line of the
 * FIFO panel: measured, **ten of the twenty-two tests in this file** were exiting that
 * way, which is why LotCustodyModal sat at 11.9% coverage while two tests appeared to
 * cover it.
 */
async function goToBrokerWithHoldings(page: Page): Promise<void> {
    await navigateTo(page, '/brokers');

    const card = page.locator('[data-testid^="broker-card-"]').filter({hasText: BROKER_WITH_HOLDINGS});
    await expect(card.first(), `${BROKER_WITH_HOLDINGS} is the broker the mock gives positions to — check populate_mock_data.py`).toBeVisible({timeout: 8_000});

    await card.first().click();
    await expect(page).toHaveURL(/\/brokers\/\d+/, {timeout: 5000});
    await expect(page.getByTestId('broker-detail-page')).toBeVisible();
    await expect(page.getByTestId('broker-name')).toBeVisible({timeout: 10000});
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

// Earned parallel: this file's blocks own the data they touch and wait on published
// state, so they share the backend with their neighbours instead of queueing behind
// them. Verified by a green run of the whole category at 4 workers.
test.describe.configure({mode: 'parallel'});

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
        await goToFirstBrokerDetail(page);

        // broker-name is already verified by the helper
        await expect(page.getByTestId('broker-name')).toBeVisible();
    });

    test('broker detail page shows cash balances section', async ({page}) => {
        await goToFirstBrokerDetail(page);

        await expect(page.getByTestId('broker-cash-balances')).toBeVisible({timeout: 5000});
    });

    test('broker detail page shows holdings section', async ({page}) => {
        await goToFirstBrokerDetail(page);

        // broker-holdings lives on the "Posizioni" tab, not the default "Panoramica" one.
        await goToPosizioniTab(page);
        await expect(page.getByTestId('broker-holdings')).toBeVisible({timeout: 5000});
    });

    test('broker detail page shows transactions section', async ({page}) => {
        await goToFirstBrokerDetail(page);

        await goToTransazioniTab(page);
        await expect(page.getByTestId('broker-transactions')).toBeVisible({timeout: 5000});
    });

    test('broker detail page has show-import-history button', async ({page}) => {
        await goToFirstBrokerDetail(page);

        // broker-show-import-history is always visible (unlike the import/new-tx
        // buttons next to it, which require OWNER or EDITOR role)
        await goToTransazioniTab(page);
        await expect(page.getByTestId('broker-show-import-history')).toBeVisible({timeout: 5000});
    });

    test('broker detail page has edit button', async ({page}) => {
        await goToFirstBrokerDetail(page);

        // broker-edit-button is inside {#if canEdit}
        await expect(page.getByTestId('broker-edit-button')).toBeVisible({timeout: 5000});
    });

    test('can open edit modal from detail page', async ({page}) => {
        await goToFirstBrokerDetail(page);

        await page.getByTestId('broker-edit-button').click();
        await expect(page.getByTestId('broker-modal')).toBeVisible({timeout: 5000});
    });

    test('can navigate back from detail page', async ({page}) => {
        await goToFirstBrokerDetail(page);

        await page.getByTestId('broker-back-button').click();
        await expect(page.getByTestId('brokers-page')).toBeVisible({timeout: 5000});
    });

    test('can open import files modal', async ({page}) => {
        await goToFirstBrokerDetail(page);

        await goToTransazioniTab(page);
        await page.getByTestId('broker-show-import-history').click();
        await expect(page.getByTestId('import-files-modal')).toBeVisible({timeout: 5000});
    });

    test('can close import files modal', async ({page}) => {
        await goToFirstBrokerDetail(page);

        await goToTransazioniTab(page);
        await page.getByTestId('broker-show-import-history').click();
        await expect(page.getByTestId('import-files-modal')).toBeVisible({timeout: 5000});

        // Close by pressing Escape
        await page.keyboard.press('Escape');
        await expect(page.getByTestId('import-files-modal')).not.toBeVisible({timeout: 3000});
    });

    test('import files modal can open file preview', async ({page}) => {
        await goToFirstBrokerDetail(page);

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
            const rows = page.locator('[data-testid="broker-holdings"] tbody tr[data-row-id]');
            // Assert, do not probe. This broker has positions by construction, so an empty
            // table means either the page had not finished loading or the mock changed —
            // and both are things a run must say out loud. `count()` answers about *this
            // instant* and never retries, which is how ten tests here turned "slow" and
            // "wrong broker" alike into "nothing to do, green".
            await expect(rows.first(), `${BROKER_WITH_HOLDINGS} must have at least one position — check populate_mock_data.py`).toBeVisible({timeout: 10_000});
            return rows.first();
        }

        test('clicking the "Analyze Lots" row action opens the FIFO lots panel', async ({page}) => {
            await goToBrokerWithHoldings(page);

            const row = await firstHoldingRow(page);

            await clickRowAction(page, row, 'analyze-lots');
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});
            await expect(page.getByTestId('lots-analysis-panel-title')).toBeVisible();

            // ?asset=<id> reflected in the URL (bookmarkable panel state).
            await expect(page).toHaveURL(/[?&]asset=\d+/);
        });

        test('closing the panel clears the ?asset= query param', async ({page}) => {
            await goToBrokerWithHoldings(page);

            const row = await firstHoldingRow(page);

            await clickRowAction(page, row, 'analyze-lots');
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});

            await page.getByTestId('lots-analysis-panel-close').click();
            await expect(page.getByTestId('lots-analysis-panel')).not.toBeVisible({timeout: 5000});
            await expect(page).not.toHaveURL(/[?&]asset=\d+/);
        });

        test('clicking the "View Asset" row action navigates to asset detail', async ({page}) => {
            await goToBrokerWithHoldings(page);

            const row = await firstHoldingRow(page);

            await clickRowAction(page, row, 'view-asset');
            await expect(page).toHaveURL(/\/assets\/\d+/, {timeout: 5000});
        });

        test('right-clicking a holding row shows a context menu with both actions', async ({page}) => {
            await goToBrokerWithHoldings(page);

            const row = await firstHoldingRow(page);

            await row.click({button: 'right'});
            await expect(page.getByTestId('context-menu')).toBeVisible({timeout: 5000});
            await expect(page.getByTestId('context-menu-action-view-asset')).toBeVisible();
            await expect(page.getByTestId('context-menu-action-analyze-lots')).toBeVisible();

            await page.getByTestId('context-menu-action-analyze-lots').click();
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});
        });

        test('WAC/Price chart EUR|% toggle switches without breaking the panel', async ({page}) => {
            await goToBrokerWithHoldings(page);

            const row = await firstHoldingRow(page);

            await clickRowAction(page, row, 'analyze-lots');
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});
            await expectChartCanvas(page, 'lot-wac-price-chart');

            await page.getByTestId('lot-wac-toggle-percentage').click();
            await expectChartCanvas(page, 'lot-wac-price-chart');

            await page.getByTestId('lot-wac-toggle-absolute').click();
            await expectChartCanvas(page, 'lot-wac-price-chart');
        });

        test('clicking a Gantt segment overlay selects the lot and reflects in the unified table', async ({page}) => {
            await goToBrokerWithHoldings(page);

            const row = await firstHoldingRow(page);

            await clickRowAction(page, row, 'analyze-lots');
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});
            await expectChartCanvas(page, 'lot-gantt-chart', 10_000);

            // Invisible per-lane hit target, absolutely positioned over the ECharts custom
            // series bar (no fixed HTML column anymore — see LotGanttChart.svelte OverlayRect).
            const segmentOverlay = page.locator('[data-testid^="lot-gantt-segment-"]').first();
            // The panel is open on a broker that has lots, so a Gantt with no segment is a
            // defect or a load that never finished — not a reason to call this test done.
            await expect(segmentOverlay, 'the Gantt must draw at least one lot segment').toBeVisible({timeout: 10_000});

            const testid = await segmentOverlay.getAttribute('data-testid');
            const lotId = testid?.replace('lot-gantt-segment-', '');
            expect(lotId).toBeTruthy();

            const tableRow = page.locator(`[data-row-id="${lotId}"]`);
            await expect(tableRow).not.toHaveClass(/selected/);

            await segmentOverlay.click();
            await expect(tableRow).toHaveClass(/selected/, {timeout: 5000});
        });

        test('clicking the Custody cell opens the modal without changing row selection', async ({page}) => {
            await goToBrokerWithHoldings(page);

            const row = await firstHoldingRow(page);

            await clickRowAction(page, row, 'analyze-lots');
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});

            const custodyCell = page.locator('[data-testid^="unified-lots-custody-"]').first();
            await expect(custodyCell, 'the unified lots table must render a custody cell').toBeVisible({timeout: 10_000});

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
            await goToBrokerWithHoldings(page);

            const row = await firstHoldingRow(page);

            await clickRowAction(page, row, 'analyze-lots');
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});

            const tableRow = page.locator('[data-testid="unified-lots-table"] tbody tr[data-row-id]').first();
            await expect(tableRow, 'the unified lots table must have at least one lot row').toBeVisible({timeout: 10_000});

            await tableRow.click({button: 'right'});
            await expect(page.getByTestId('context-menu')).toBeVisible({timeout: 5000});

            const viewDetail = page.getByTestId('context-menu-action-lot-view-details-action');
            await expect(viewDetail).toBeVisible();
            await viewDetail.click();

            await expect(page.getByTestId('lot-custody-modal-title')).toBeVisible({timeout: 5000});
            // Summary shows the additive fields regardless of the lot's custody/transfer history.
            await expect(page.getByTestId('lot-custody-modal-summary')).toContainText(/./);
        });

        test('the lot detail modal renders its three sections and the net breakdown', async ({page}) => {
            // Until the navigation above was anchored to a broker that actually has
            // positions, every test in this block exited early and this modal was never
            // opened by this file at all. Opening it is not the same as exercising it:
            // the two tests above assert the title and that the summary is non-empty,
            // which leaves the P&L maths, the custody rows and the event history — the
            // bulk of the component — unread.
            await goToBrokerWithHoldings(page);
            const row = await firstHoldingRow(page);
            await clickRowAction(page, row, 'analyze-lots');
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});

            const tableRow = page.locator('[data-testid="unified-lots-table"] tbody tr[data-row-id]').first();
            await expect(tableRow, 'the unified lots table must have at least one lot row').toBeVisible({timeout: 10_000});
            await tableRow.click({button: 'right'});
            await expect(page.getByTestId('context-menu')).toBeVisible({timeout: 5000});
            await page.getByTestId('context-menu-action-lot-view-details-action').click();

            const modal = page.getByTestId('lot-custody-modal');
            await expect(modal).toBeVisible({timeout: 5000});

            // The three sections the modal is made of.
            await expect(page.getByTestId('lot-custody-modal-summary')).toBeVisible();
            await expect(page.getByTestId('lot-custody-modal-current-custody')).toBeVisible();
            await expect(page.getByTestId('lot-custody-modal-history')).toBeVisible();
            await expect(page.getByTestId('lot-custody-modal-lot-id')).toContainText(/\S/);

            // The derived P&L figures. Their *values* depend on prices this test does not
            // own, so the assertion is that each one resolved to something printable —
            // a blank here means a derived threw or a format helper returned undefined,
            // which is exactly what never running this component would hide.
            for (const tid of ['lot-custody-modal-asset-income', 'lot-custody-modal-market-pnl', 'lot-custody-modal-total-pnl']) {
                await expect(page.getByTestId(tid), `${tid} must render a value`).toContainText(/\S/);
            }
        });

        test('the lot detail modal breaks down fees and taxes for a lot that carries them', async ({page}) => {
            // The net breakdown is behind `{#if lotHasNetCosts}`, so this looks for a lot
            // that actually has allocated costs rather than assuming the first one does —
            // filtering to "a lot" is not the same as finding one that can still show what
            // the test is about.
            //
            // Until the mock grew an asset-attached FEE and TAX on Apple/IB, no lot in the
            // database qualified: every other FEE/TAX row has `asset_id=None`, an
            // account-level charge the FIFO engine has nothing to attach to. This whole
            // section of the modal was unreachable, which is why it went uncovered.
            await goToBrokerWithHoldings(page);
            const row = await firstHoldingRow(page);
            await clickRowAction(page, row, 'analyze-lots');
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});

            const rows = page.locator('[data-testid="unified-lots-table"] tbody tr[data-row-id]');
            await expect(rows.first()).toBeVisible({timeout: 10_000});
            const modal = page.getByTestId('lot-custody-modal');
            const breakdown = page.getByTestId('lot-custody-modal-net-breakdown');

            const candidates = Math.min(await rows.count(), 8);
            let found = false;
            for (let i = 0; i < candidates; i++) {
                await rows.nth(i).click({button: 'right'});
                await expect(page.getByTestId('context-menu')).toBeVisible({timeout: 5000});
                await page.getByTestId('context-menu-action-lot-view-details-action').click();
                await expect(modal).toBeVisible({timeout: 5000});

                if (await appears(breakdown, 2_000)) {
                    found = true;
                    break;
                }
                await page.getByTestId('lot-custody-modal-close').click();
                await expect(modal).toBeHidden({timeout: 5000});
            }

            expect(found, `no lot among the first ${candidates} carries allocated fees or taxes — the mock must keep an asset-attached FEE/TAX, see populate_mock_data.py`).toBe(true);
            await expect(page.getByTestId('lot-custody-modal-allocated-fees')).toContainText(/\S/);
            await expect(page.getByTestId('lot-custody-modal-allocated-taxes')).toContainText(/\S/);
            // Either a net figure or the explicit "unavailable" dash — both legitimate,
            // an empty node is not.
            await expect(page.getByTestId('lot-custody-modal-net-total-pnl')).toContainText(/\S/);
        });

        test('the lot detail modal closes from both the header and the footer', async ({page}) => {
            await goToBrokerWithHoldings(page);
            const row = await firstHoldingRow(page);
            await clickRowAction(page, row, 'analyze-lots');
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});

            const tableRow = page.locator('[data-testid="unified-lots-table"] tbody tr[data-row-id]').first();
            await expect(tableRow).toBeVisible({timeout: 10_000});
            const modal = page.getByTestId('lot-custody-modal');

            for (const closeTestId of ['lot-custody-modal-close', 'lot-custody-modal-footer-close']) {
                await tableRow.click({button: 'right'});
                await expect(page.getByTestId('context-menu')).toBeVisible({timeout: 5000});
                await page.getByTestId('context-menu-action-lot-view-details-action').click();
                await expect(modal).toBeVisible({timeout: 5000});

                await page.getByTestId(closeTestId).click();
                await expect(modal, `${closeTestId} must close the modal`).toBeHidden({timeout: 5000});
            }
        });

        test('row context menu "Go to lot in Gantt" pulses the matching Gantt lane', async ({page}) => {
            await goToBrokerWithHoldings(page);

            const row = await firstHoldingRow(page);

            await clickRowAction(page, row, 'analyze-lots');
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});
            await expectChartCanvas(page, 'lot-gantt-chart', 10_000);

            const tableRow = page.locator('[data-testid="unified-lots-table"] tbody tr[data-row-id]').first();
            await expect(tableRow, 'the unified lots table must have at least one lot row').toBeVisible({timeout: 10_000});

            await tableRow.click({button: 'right'});
            await expect(page.getByTestId('context-menu')).toBeVisible({timeout: 5000});
            await page.getByTestId('context-menu-action-lot-view-gantt-action').click();

            // pulseLot() scrolls the Gantt into view and applies the pulse ring/glow to the
            // matching lane highlight — the chart staying rendered (canvas with real
            // dimensions) is the stable, low-risk assertion (the ring/glow is drawn inside
            // the ECharts canvas, not a DOM class).
            await expectChartCanvas(page, 'lot-gantt-chart');
        });

        test('Value presentation toggle: two independent buttons (Aggregate/Per lot), Asset-Global-style tri-state — neither pressed shows both', async ({page}) => {
            await goToBrokerWithHoldings(page);

            const row = await firstHoldingRow(page);

            await clickRowAction(page, row, 'analyze-lots');
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5000});

            const checkbox = page.locator('[data-testid="unified-lots-table"] tbody tr[data-row-id]').first().locator('.checkbox-btn, button').first();
            await expect(checkbox, 'the value presentation toggle must be present once the panel is open').toBeVisible({timeout: 10_000});
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
            await expectChartCanvas(page, 'lot-comparison-echart');

            // Press Per lot too -> both pressed -> still shows everything.
            await individualToggle.click();
            await expect(individualToggle).toHaveAttribute('aria-pressed', 'true');
            await expectChartCanvas(page, 'lot-comparison-echart');

            // Un-press Aggregate -> only Per lot pressed -> exclusive individual view.
            await aggregateToggle.click();
            await expect(aggregateToggle).toHaveAttribute('aria-pressed', 'false');
            await expectChartCanvas(page, 'lot-comparison-echart');

            // Un-press Per lot too -> neither pressed -> implicit "show both" (tri-state rule).
            await individualToggle.click();
            await expect(individualToggle).toHaveAttribute('aria-pressed', 'false');
            await expect(aggregateToggle).toHaveAttribute('aria-pressed', 'false');
            await expectChartCanvas(page, 'lot-comparison-echart');
        });
    });
});

/**
 * GrowthChart P&L mode on a broker page (phase I70).
 *
 * The regression this block exists for: the broker page mounted `<GrowthChart>`
 * **without** `onRequestPnlCandles`, so activating the candles submode fired no
 * request at all and every candle was a gap sentinel. The plot still had a
 * canvas of exactly the right size, so anything asserting presence stayed green
 * through the whole defect. Every assertion below is therefore on the *data*:
 * the report body the click causes, the points that come back, and the rows the
 * chart's own tooltip formatter reads out of what it drew.
 *
 * Why `Interactive Brokers` and not "a broker": the seeded set has eight, and
 * only this one carries enough transactions to produce a history. The rest
 * render "no data available" — picking by position would have tested the empty
 * state and called it a pass. `goToBrokerWithHoldings()` already encodes that,
 * and the broker id is then read back from the URL rather than assumed, so the
 * scoping assertion compares against the page the test is genuinely on.
 *
 * Plan §3.3 — "one broker or Broker detail: total candle only" — is the second
 * half: this mount deliberately omits `brokerPnlHistory`, and the absence of a
 * per-broker overlay is asserted against the presence of the total candle, so
 * "nothing is there" cannot pass for "the overlay is gone".
 */

type BrokerPnlSubmode = 'line' | 'candles' | 'income';

/** `EUR 1,234.56` / `EUR -12.30` — an unsigned tooltip amount (the OHLC rows). */
const BROKER_PLAIN_AMOUNT = /^[A-Z]{3}\s-?[\d.,]+$/;
/** `+EUR 359.04` / `−EUR 12.00` — a signed tooltip amount (P&L rows; U+2212). */
const BROKER_SIGNED_AMOUNT = /^[+\u2212][A-Z]{3}\s[\d.,]+$/;

interface BrokerReportCall {
    body: Record<string, unknown> & {broker_ids?: number[]};
    json: Record<string, any> | null;
}

/** Record every portfolio report the page issues, request body *and* response. */
async function recordBrokerReports(page: Page): Promise<BrokerReportCall[]> {
    const calls: BrokerReportCall[] = [];
    await page.route(/\/api\/v1\/portfolio\/report(\?.*)?$/, async (route) => {
        const body = route.request().postDataJSON();
        const response = await route.fetch();
        const json = await response.json().catch(() => null);
        calls.push({body, json});
        await route.fulfill({response});
    });
    return calls;
}

/** The element GrowthChart publishes `data-chart-ready`/`data-chart-renders` on. */
function brokerGrowthHost(chart: Locator): Locator {
    return chart.locator('[data-chart-ready]');
}

async function brokerChartRenders(host: Locator): Promise<number> {
    return Number((await host.getAttribute('data-chart-renders')) ?? '0');
}

/**
 * Open Interactive Brokers' overview and wait until its GrowthChart has drawn.
 *
 * This page publishes no `data-busy`, but `renderChart` refuses to run while
 * `history` is empty — so `data-chart-ready="true"` is the app stating that the
 * report landed *and* ECharts painted it. Returns the chart and the broker id
 * the URL resolved to.
 */
async function openBrokerGrowthChart(page: Page): Promise<{chart: Locator; brokerId: number}> {
    await goToBrokerWithHoldings(page);

    const brokerId = Number(new URL(page.url()).pathname.split('/').filter(Boolean).pop());
    expect(Number.isFinite(brokerId), 'the detail URL carries the broker id').toBe(true);

    const chart = page.getByTestId('growth-chart');
    await expect(chart).toBeVisible({timeout: 15_000});
    await expect(brokerGrowthHost(chart)).toHaveAttribute('data-chart-ready', 'true', {timeout: 30_000});
    return {chart, brokerId};
}

/** Select a P&L submode and wait for the redraw it causes (counter read first). */
async function selectBrokerSubmode(chart: Locator, submode: BrokerPnlSubmode): Promise<void> {
    const button = chart.getByTestId(`growth-pnl-submode-${submode}`);
    await expect(button).toBeVisible({timeout: 10_000});

    if ((await button.getAttribute('aria-pressed')) !== 'true') {
        const host = brokerGrowthHost(chart);
        const before = await brokerChartRenders(host);
        await button.click();
        await expect.poll(() => brokerChartRenders(host), {timeout: 15_000}).toBeGreaterThan(before);
    }
    await expect(button).toHaveAttribute('aria-pressed', 'true');
}

test.describe('Broker detail — GrowthChart P&L mode', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('activating candles fetches a candle report scoped to this broker', async ({page}) => {
        test.setTimeout(60_000);
        const reports = await recordBrokerReports(page);
        const {chart, brokerId} = await openBrokerGrowthChart(page);

        // The defect this pins produced *zero* candle requests, so the opening
        // state matters as much as the closing one.
        expect(reports.length, 'the overview loads at least one report').toBeGreaterThan(0);
        expect(
            reports.filter((call) => call.body.include_pnl_candles === true),
            'candles stay off the ordinary overview load',
        ).toHaveLength(0);

        await chart.getByTestId('growth-toggle-pnl').click();
        await selectBrokerSubmode(chart, 'candles');

        await expect.poll(() => reports.filter((call) => call.body.include_pnl_candles === true).length, {timeout: 20_000}).toBeGreaterThan(0);
        const candleCall = reports.find((call) => call.body.include_pnl_candles === true);

        // Scoped to *this* broker: the dashboard's own loader would have answered
        // with whole-portfolio OHLC under a single broker's heading — a wrong
        // number, which is worse than the empty plot it replaced.
        expect(candleCall?.body.broker_ids, 'the candle report is scoped to the broker whose page this is').toEqual([brokerId]);

        const series = candleCall?.json?.pnl_candles;
        expect(series?.hypothetical).toBe(true);
        const points: Array<Record<string, {amount: string} | undefined>> = series?.points ?? [];
        expect(points.length, `${BROKER_WITH_HOLDINGS} has the transactions to produce candles — check populate_mock_data.py`).toBeGreaterThan(0);

        const amount = (value?: {amount: string}) => Number(value?.amount);
        const holed = points.filter((point) => ['open', 'high', 'low', 'close'].some((key) => !Number.isFinite(amount(point[key]))));
        expect(holed, 'every candle carries four real numbers — the gap sentinels the defect produced are exactly what must not come back').toHaveLength(0);
        expect(
            points.some((point) => amount(point.close) !== 0),
            'this broker moves somewhere in the window',
        ).toBe(true);

        await expect(chart.getByTestId('growth-pnl-candles-hypothetical-label')).toBeVisible();
    });

    test('line and income submodes render this broker own figures', async ({page}) => {
        test.setTimeout(60_000);
        const reports = await recordBrokerReports(page);
        const {chart, brokerId} = await openBrokerGrowthChart(page);

        // The income submode plots four sparse sections this page has to ask for
        // eagerly. A submode wired to props nobody fetched would still draw axes
        // and still look fine, so the request is checked before the picture.
        const overview = reports.find((call) => call.body.include_income_history === true);
        expect(overview, 'the broker overview requests the sparse income family on its ordinary load').toBeTruthy();
        expect({
            income: overview?.body.include_income_history,
            cost: overview?.body.include_cost_history,
            deposit: overview?.body.include_deposit_history,
            acquisition: overview?.body.include_acquisition_funding,
        }).toEqual({income: true, cost: true, deposit: true, acquisition: true});
        expect(overview?.body.broker_ids, 'and scoped to this broker, not to the whole portfolio').toEqual([brokerId]);

        await chart.getByTestId('growth-toggle-pnl').click();

        // Line: the total P&L row, and nothing but it — this mount has no
        // per-broker overlay to add a second row (plan §3.3).
        await selectBrokerSubmode(chart, 'line');
        await showChartTooltip(page, chart, chart.getByText(BROKER_SIGNED_AMOUNT), 10_000, 1);
        await expect(chart.getByText(BROKER_SIGNED_AMOUNT)).toHaveCount(1);

        // Income: dividend, interest and their total — three signed rows at the
        // floor, which a submode that never bound its income series could not
        // produce. Not an exact count: the batch-2 rows (costs, deposit,
        // acquisition) are sparse and only join on a day that had that activity,
        // so an equality would pin which day the pointer happened to land on.
        await selectBrokerSubmode(chart, 'income');
        await showChartTooltip(page, chart, chart.getByText(BROKER_SIGNED_AMOUNT), 10_000, 3);
        await expect(chart.getByText(BROKER_SIGNED_AMOUNT).first()).toBeVisible();
    });

    test('the candles submode shows the total candle only, with no per-broker overlay', async ({page}) => {
        test.setTimeout(60_000);
        const {chart} = await openBrokerGrowthChart(page);
        await chart.getByTestId('growth-toggle-pnl').click();
        await selectBrokerSubmode(chart, 'candles');

        // The barrier first: a full OHLC quad on screen means the total candle is
        // drawn and its tooltip is up. Without it, "no overlay" would also be true
        // of a chart that had rendered nothing at all.
        await showChartTooltip(page, chart, chart.getByText(BROKER_PLAIN_AMOUNT), 20_000, 4);
        await expect(chart.getByText(BROKER_PLAIN_AMOUNT), 'open, close, high and low — the total candle in full').toHaveCount(4);

        // An overlay line would add a signed row per broker, named after it.
        await expect(chart.getByText(BROKER_SIGNED_AMOUNT), 'no per-broker P&L row belongs on a single-broker page').toHaveCount(0);
        await expect(chart.getByText(BROKER_WITH_HOLDINGS, {exact: true}), 'the broker name would only appear here as an overlay legend row').toHaveCount(0);
    });
});
