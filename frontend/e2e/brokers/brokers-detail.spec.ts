import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo, setLanguage} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {expectChartCanvas, showChartTooltip} from '../fixtures/charts';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';
import {daysAgoIso} from '../fixtures/dates';
import {commitCreates} from '../fixtures/owned-pair';
import path from 'path';
import {fileURLToPath} from 'url';
import {appears} from '../fixtures/probe';
import {lotIsOpenish, type LotOpenish} from '../../src/lib/features/brokers/lots/lotsAnalysisHelpers';
import {resolveUiLocale} from '../../src/lib/stores/app/uiLocaleRule';

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
 * Opens the detail page of the first broker card on screen.
 *
 * The mock always ships seven brokers, so "no card appeared" is a failure and not a
 * reason to skip: returning a boolean here let every caller write `if (!ok) return`,
 * which marks a test green without testing anything.
 *
 * It starts from the broker list already on screen and does not navigate to it. The
 * outer beforeEach (`ensureBrokerExists`) leaves the list landed, so navigating again
 * repeated the whole list load — the brokers, plus a whole-portfolio report left in
 * flight on the backend — for nothing, and under load that was time the test did not
 * have (C-58). The list's address is therefore a precondition, asserted and not assumed:
 * a caller that starts elsewhere navigates to /brokers first.
 *
 * The precondition checks the address, not the page, so it costs nothing on either
 * path. A caller on the wrong page fails here with that message, within the default
 * expect timeout; on the right page, the card assertion below verifies the list itself,
 * and its message says what went wrong.
 *
 * After the click it waits for the detail page, on a navigation budget, before checking
 * the new address. SvelteKit changes the address only when the navigation completes, once
 * the detail page's code has loaded — and each test fetches that code again, in a fresh
 * browser context — so on a loaded machine the address changed later than the 5 s its
 * check used to allow. With the page on screen, the address check is immediate.
 * `goToBrokerWithHoldings`, the card-click test and the "View Asset" test follow the same order.
 */
async function goToFirstBrokerDetail(page: Page): Promise<void> {
    await expect(page, 'the broker list must be the current page — the outer beforeEach (ensureBrokerExists) leaves it landed; a caller that starts elsewhere navigates to /brokers first').toHaveURL(/\/brokers(?:[?#]|$)/);

    const brokerCards = page.locator('[data-testid^="broker-card-"]');
    await expect(brokerCards.first(), 'the mock always ships brokers — an empty list means the page never loaded').toBeVisible({timeout: 8_000});

    await brokerCards.first().click();
    await expect(page.getByTestId('broker-detail-page'), 'a broker card opens its detail page — not mounted in time means the click did not navigate, or the route had not finished loading').toBeVisible({timeout: 10_000});
    await expect(page).toHaveURL(/\/brokers\/\d+/);
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
 *
 * Like `goToFirstBrokerDetail`, it opens the broker from the list already on screen and
 * asserts the list's address first: the outer beforeEach leaves it landed, and navigating
 * again repeated the whole list load for nothing (C-58). The callers outside that
 * describe start on the Dashboard and navigate to /brokers first.
 */
async function goToBrokerWithHoldings(page: Page): Promise<void> {
    await expect(page, 'the broker list must be the current page — the outer beforeEach (ensureBrokerExists) leaves it landed; a caller that starts elsewhere navigates to /brokers first').toHaveURL(/\/brokers(?:[?#]|$)/);

    const card = page.locator('[data-testid^="broker-card-"]').filter({hasText: BROKER_WITH_HOLDINGS});
    await expect(card.first(), `${BROKER_WITH_HOLDINGS} is the broker the mock gives positions to — check populate_mock_data.py`).toBeVisible({timeout: 8_000});

    await card.first().click();
    await expect(page.getByTestId('broker-detail-page'), `the ${BROKER_WITH_HOLDINGS} card opens its detail page — not mounted in time means the click did not navigate, or the route had not finished loading`).toBeVisible({timeout: 10_000});
    await expect(page).toHaveURL(/\/brokers\/\d+/);
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

/**
 * The lots panel the "Analyze Lots" action opens, from the row actions or the context menu: the
 * URL first, then the panel (Y-34).
 *
 * The action mounts nothing itself: the broker page's `openAssetPanel` starts a same-route `goto`
 * to `buildAssetPanelUrl(…)` (`assetPanelUrl.ts`), which writes `?asset=<id>` into the URL. The
 * URL wait covers that navigation, with a 30 s ceiling: under load it queues on a busy main
 * thread. The page then reads the parameter back in a `$:` block (`getAssetPanelAssetId`) and
 * mounts `LotsAnalysisPanel` under `{#if open && assetId != null}`: the panel wait covers that
 * mount, with 10 s. On 17/10 (gate I) a single 5 s wait covering both expired once at a 1-minute
 * load near 90, while the same test passed in a run alone at a load of 28 (40/40). Why the URL
 * gets a ceiling of its own, and why the action is not retried: the Y-33 paragraph of
 * `goToSeededAssetDetail`, in `assets/asset-detail.spec.ts`.
 */
async function expectLotsPanelOpen(page: Page): Promise<void> {
    await expect(page, 'the "Analyze Lots" action opens the lots panel — the URL carries ?asset=<id>').toHaveURL(/[?&]asset=\d+/, {timeout: 30_000});
    await expect(page.getByTestId('lots-analysis-panel'), 'the lots panel mounts once ?asset= is in the URL').toBeVisible({timeout: 10_000});
}

/** The mirror of `expectLotsPanelOpen` for the panel's close (Y-34): the URL without `?asset=` first, with a 30 s ceiling, then the panel hidden, with 10 s. */
async function expectLotsPanelClosed(page: Page): Promise<void> {
    await expect(page, 'closing the lots panel clears ?asset= from the URL').not.toHaveURL(/[?&]asset=\d+/, {timeout: 30_000});
    await expect(page.getByTestId('lots-analysis-panel'), 'the lots panel unmounts once ?asset= has left the URL').toBeHidden({timeout: 10_000});
}

// Earned parallel: this file's blocks own the data they touch and wait on published
// state, so they share the backend with their neighbours instead of queueing behind
// them. Verified by a green run of the whole category at 4 workers.
test.describe.configure({mode: 'parallel'});

test.describe('Broker Detail Page', () => {
    // An explicit budget for the chain every test here walks: login, the broker list, then the
    // broker page. A describe's timeout runs from the start of the test, so it also covers the
    // beforeEach below (login and list), as in the FIFO block. C-58 gave only that block 60 s,
    // this one's slowest test then taking 13 s; at load ~70 a test has since reached its first
    // click only after ~24 s, leaving the broker page a few seconds of the default 30 s. Only
    // the timeout is set: the file's parallel mode is inherited unchanged.
    test.describe.configure({timeout: 60_000});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await ensureBrokerExists(page);
    });

    test('can navigate to broker detail by clicking card', async ({page}) => {
        // On the list the beforeEach left landed. An `if (count > 0)` here counted the cards
        // before the list arrived, found none and passed without clicking: assert, do not probe.
        const brokerCards = page.locator('[data-testid^="broker-card-"]');
        await expect(brokerCards.first(), 'the mock always ships brokers — an empty list means the page never loaded').toBeVisible({timeout: 8_000});

        await brokerCards.first().click();
        await expect(page.getByTestId('broker-detail-page'), 'a broker card opens its detail page — not mounted in time means the click did not navigate, or the route had not finished loading').toBeVisible({timeout: 10_000});
        await expect(page).toHaveURL(/\/brokers\/\d+/);
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
        // An explicit budget for the chain every test here walks: login, the broker list, the
        // broker page, Posizioni, the lots panel with its table and charts, then menus and
        // modals — the chain the axisBuilder and P&L blocks below already budget at 60 s. A
        // describe's timeout runs from the start of the test, so it also covers the outer
        // beforeEach (login and list); at the default 30 s it ran out under load (C-58). Only
        // the timeout is set: the file's parallel mode is inherited unchanged.
        test.describe.configure({timeout: 60_000});

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
            await expectLotsPanelOpen(page);
            await expect(page.getByTestId('lots-analysis-panel-title')).toBeVisible();

            // ?asset=<id> reflected in the URL (bookmarkable panel state).
            await expect(page).toHaveURL(/[?&]asset=\d+/);
        });

        test('closing the panel clears the ?asset= query param', async ({page}) => {
            await goToBrokerWithHoldings(page);

            const row = await firstHoldingRow(page);

            await clickRowAction(page, row, 'analyze-lots');
            await expectLotsPanelOpen(page);

            await page.getByTestId('lots-analysis-panel-close').click();
            await expectLotsPanelClosed(page);
        });

        test('clicking the "View Asset" row action navigates to asset detail', async ({page}) => {
            await goToBrokerWithHoldings(page);

            const row = await firstHoldingRow(page);

            await clickRowAction(page, row, 'view-asset');
            await expect(page.getByTestId('asset-detail-page'), 'the "View Asset" row action opens the asset detail page — not mounted in time means the action did not navigate, or the route had not finished loading').toBeVisible({timeout: 10_000});
            await expect(page).toHaveURL(/\/assets\/\d+/);
        });

        test('right-clicking a holding row shows a context menu with both actions', async ({page}) => {
            await goToBrokerWithHoldings(page);

            const row = await firstHoldingRow(page);

            await row.click({button: 'right'});
            await expect(page.getByTestId('context-menu')).toBeVisible({timeout: 5000});
            await expect(page.getByTestId('context-menu-action-view-asset')).toBeVisible();
            await expect(page.getByTestId('context-menu-action-analyze-lots')).toBeVisible();

            await page.getByTestId('context-menu-action-analyze-lots').click();
            await expectLotsPanelOpen(page);
        });

        test('WAC/Price chart EUR|% toggle switches without breaking the panel', async ({page}) => {
            await goToBrokerWithHoldings(page);

            const row = await firstHoldingRow(page);

            await clickRowAction(page, row, 'analyze-lots');
            await expectLotsPanelOpen(page);
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
            await expectLotsPanelOpen(page);
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
            await expect(tableRow).toHaveAttribute('data-selected', 'false');

            await segmentOverlay.click();
            await expect(tableRow).toHaveAttribute('data-selected', 'true', {timeout: 5000});
        });

        test('clicking the Custody cell opens the modal without changing row selection', async ({page}) => {
            await goToBrokerWithHoldings(page);

            const row = await firstHoldingRow(page);

            await clickRowAction(page, row, 'analyze-lots');
            await expectLotsPanelOpen(page);

            const custodyCell = page.locator('[data-testid^="unified-lots-custody-"]').first();
            await expect(custodyCell, 'the unified lots table must render a custody cell').toBeVisible({timeout: 10_000});

            const testid = await custodyCell.getAttribute('data-testid');
            const lotId = testid?.replace('unified-lots-custody-', '');
            const tableRow = page.locator(`[data-row-id="${lotId}"]`);
            await expect(tableRow).toHaveAttribute('data-selected', 'false');

            await custodyCell.click();

            // Modal opens...
            await expect(page.getByTestId('lot-custody-modal-title')).toBeVisible({timeout: 5000});
            // ...but the row's selection state is untouched by the custody click.
            await expect(tableRow).toHaveAttribute('data-selected', 'false');
        });

        test('row context menu "View lot detail" opens the modal for any lot, including one with no transfer', async ({page}) => {
            await goToBrokerWithHoldings(page);

            const row = await firstHoldingRow(page);

            await clickRowAction(page, row, 'analyze-lots');
            await expectLotsPanelOpen(page);

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
            await expectLotsPanelOpen(page);

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
            await expectLotsPanelOpen(page);

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
            await expectLotsPanelOpen(page);

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
            await expectLotsPanelOpen(page);
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

        // ── The comparison chart's presentation controls ─────────────────────────────────────
        //
        // What these two replace: a test pressing an Aggregate / Per-lot pair (`lots-value-*`) that
        // left the component in 59c160325, when Value mode became aggregate-only. Its
        // `if (!visible) return` then ended it on every run — green without testing anything — and
        // it picked its lot by a CSS class.
        //
        // Today's controls are two-button groups that publish `aria-pressed`
        // (LotComparisonChart.svelte): the mode, Value | Return; Value's Y axis, Auto | From 0; and,
        // in Return mode only, the unit, Abs | %, and Return's own Y axis, Auto | From 0. Their state
        // is the component's `$state` and nothing is persisted, so every test starts from the
        // defaults the component declares: Value, Auto, Abs, Auto.
        //
        // What a floor does to the axis (`yAxis.min: 0` in Value mode) is not read here: unlike
        // GrowthChart or PerformanceChart, this chart publishes no handle on its ECharts instance
        // (`__lfChart`), and adding one is a product change. The assertions stop at what the user is
        // told — which button is pressed, which controls are offered — and at the chart finishing a
        // redraw after every click, with something to draw.

        /**
         * Open the lots panel from the first holding, as the tests above do, and wait until its
         * comparison chart has drawn — before any lot is picked.
         *
         * Nothing picked is not nothing to draw: until the user picks lots, the panel compares every
         * visible one (plan v3 §13, `effectiveSelectedLots`), so `lot-comparison-empty` only shows
         * when no lot is visible at all. The chart stays `invisible` until it has something to draw,
         * which makes its visibility the barrier on the histories it waits for.
         *
         * The title comes first, for the reason `openLotsPanelSettled` gives: the panel's currency is
         * the asset's own once the asset cache resolves (the base currency before), and a currency
         * change reloads the panel and mounts every chart again — this one with its presentation back
         * at the defaults, under a test that has just changed them. The title gains the asset name in
         * the same update. The name is the broker summary's, for the id the panel wrote into the URL.
         */
        async function openComparisonChart(page: Page): Promise<Locator> {
            await goToBrokerWithHoldings(page);
            const row = await firstHoldingRow(page);
            await clickRowAction(page, row, 'analyze-lots');
            await expectLotsPanelOpen(page);
            await expect(page).toHaveURL(/[?&]asset=\d+/);

            const url = new URL(page.url());
            const brokerId = Number(url.pathname.split('/').filter(Boolean).pop());
            const assetId = Number(url.searchParams.get('asset'));
            const summaryResponse = await page.request.get(`/api/v1/brokers/${brokerId}/summary`);
            expect(summaryResponse.ok(), `broker ${brokerId} summary answered ${summaryResponse.status()}`).toBe(true);
            const summary = (await summaryResponse.json()) as {holdings?: {asset_id: number; asset_name: string}[] | null};
            const assetName = summary.holdings?.find((holding) => holding.asset_id === assetId)?.asset_name;
            if (!assetName) throw new Error(`Asset ${assetId}, opened from the first ${BROKER_WITH_HOLDINGS} holding, is missing from broker ${brokerId}'s summary`);
            await expect(page.getByTestId('lots-analysis-panel-title'), `the title gains "${assetName}" once the asset cache has resolved — from then on the panel's currency is final and its charts are not mounted again`).toContainText(assetName, {timeout: 10_000});

            const chart = page.getByTestId('lot-comparison-echart');
            await expect(chart, `the comparison chart must show ${assetName}'s lots before any is picked — it stays invisible until it has something to draw`).toBeVisible({timeout: 20_000});
            await expectChartCanvas(page, 'lot-comparison-echart');
            await expect(chart).toHaveAttribute('data-chart-ready', 'true', {timeout: 10_000});
            await expect(page.getByTestId('lot-comparison-empty'), 'nothing picked yet, and still a chart: the empty state is for a panel with no visible lot').toHaveCount(0);
            return chart;
        }

        /** One choice per group: `chosen` pressed, and no other button of its group. */
        async function expectChoice(group: Locator, chosen: Locator, what: string): Promise<void> {
            await expect(chosen, `${what}: pressed`).toHaveAttribute('aria-pressed', 'true');
            await expect(group.getByRole('button', {pressed: true}), `${what}: exactly one button of the pair pressed`).toHaveCount(1);
        }

        /**
         * Press one presentation button of the comparison chart and wait for the redraw it causes.
         *
         * Each button sets a value rather than toggling it, so pressing the current choice changes
         * nothing and no redraw would come: the button must start unpressed. The render counter
         * (`data-chart-renders`, from attachChartReady) is read before the click and polled for a
         * delta, so the redraw proven finished after the click. The canvas is checked only after it —
         * the element survives the click, and checked at once it would show the picture being
         * replaced — and the container goes `invisible` whenever the chosen presentation has nothing
         * to draw, so the check is also the proof that it has data.
         */
        async function pressAndRedraw(page: Page, button: Locator, what: string): Promise<void> {
            const chart = page.getByTestId('lot-comparison-echart');
            await expect(button, `${what}: the button must be offered, and not pressed yet`).toHaveAttribute('aria-pressed', 'false');
            const before = await chartRenders(chart);
            await button.click();
            await expect(button, `${what}: the button must report itself pressed`).toHaveAttribute('aria-pressed', 'true');
            await expect.poll(() => chartRenders(chart), {message: `${what}: the comparison chart must finish the redraw the click caused`, timeout: 10_000}).toBeGreaterThan(before);
            await expect(chart, `${what}: the chart must still have something to draw — it goes invisible on "no data"`).toBeVisible();
            await expectChartCanvas(page, 'lot-comparison-echart');
        }

        test('comparison chart: a picked lot keeps it drawn, Value/Return swap the toolbar, and each mode keeps its own Y-axis floor (aria-pressed)', async ({page}) => {
            const chart = await openComparisonChart(page);
            const modeGroup = page.getByTestId('lot-comparison-mode-toggle');
            const valueFloor = page.getByTestId('lot-comparison-value-yaxis-toggle');
            const returnUnit = page.getByTestId('lot-comparison-return-abs-pct-toggle');
            const returnFloor = page.getByTestId('lot-comparison-return-yaxis-toggle');

            // Pick a lot by the state the table publishes — DataTable writes `data-selected` on the
            // row and `data-state` on its checkbox — and address it by its own id from then on. Which
            // lot does not matter to the controls, so the first row is taken; that it still gives the
            // chart something to draw is asserted below, not assumed. The panel opens with nothing
            // picked, and that is checked too: the checkbox toggles, and would unpick a picked lot.
            const lotRows = page.locator('[data-testid="unified-lots-table"] tbody tr[data-row-id]');
            await expect(lotRows.first(), `the first ${BROKER_WITH_HOLDINGS} holding must have at least one lot to pick — check populate_mock_data.py`).toBeVisible({timeout: 10_000});
            const lotId = await lotRows.first().getAttribute('data-row-id');
            if (!lotId) throw new Error('A row of the unified lots table carries an empty data-row-id');
            const lotRow = page.locator(`[data-testid="unified-lots-table"] tbody tr[data-row-id="${lotId}"]`);
            const lotCheckbox = lotRow.getByTestId(`dt-row-checkbox-${lotId}`);
            await expect(lotRow, 'the panel opens with no lot picked').toHaveAttribute('data-selected', 'false');
            await expect(lotCheckbox).toHaveAttribute('data-state', 'unchecked');

            const rendersBeforePick = await chartRenders(chart);
            await lotCheckbox.click();
            await expect(lotCheckbox).toHaveAttribute('data-state', 'checked');
            await expect(lotRow, `lot ${lotId} is picked`).toHaveAttribute('data-selected', 'true');
            await expect.poll(() => chartRenders(chart), {message: `the comparison chart must redraw for lot ${lotId} alone`, timeout: 10_000}).toBeGreaterThan(rendersBeforePick);
            await expect(chart, `lot ${lotId} alone must still give the chart something to draw — it goes invisible on "no data"`).toBeVisible();
            await expectChartCanvas(page, 'lot-comparison-echart');
            await expect(page.getByTestId('lot-comparison-empty'), 'picking a lot narrows the comparison, it does not empty it').toHaveCount(0);

            // The defaults. Return's controls are not rendered in Value mode ({#if}), so their absence
            // is asserted once a control of the same toolbar has shown up.
            await expectChoice(modeGroup, page.getByTestId('lot-comparison-mode-value'), 'default mode Value');
            await expect(valueFloor).toBeVisible();
            await expectChoice(valueFloor, page.getByTestId('lot-comparison-value-yaxis-auto'), 'default Value Y axis Auto');
            await expect(returnUnit, 'Abs/% belongs to Return mode').toHaveCount(0);
            await expect(returnFloor, "Return's Y-axis floor belongs to Return mode").toHaveCount(0);

            await pressAndRedraw(page, page.getByTestId('lot-comparison-value-yaxis-zero'), 'Value Y axis From 0');
            await expectChoice(valueFloor, page.getByTestId('lot-comparison-value-yaxis-zero'), 'Value Y axis From 0');

            // Value → Return swaps the toolbar, and Return's floor is its own: still Auto.
            await pressAndRedraw(page, page.getByTestId('lot-comparison-mode-return'), 'Return mode');
            await expectChoice(modeGroup, page.getByTestId('lot-comparison-mode-return'), 'mode Return');
            await expect(returnUnit).toBeVisible();
            await expect(returnFloor).toBeVisible();
            await expect(valueFloor, "Value's Y-axis floor leaves with Value mode").toHaveCount(0);
            await expectChoice(returnUnit, page.getByTestId('lot-comparison-return-abs'), 'default Return unit Abs');
            await expectChoice(returnFloor, page.getByTestId('lot-comparison-return-yaxis-auto'), "Return's own Y axis, Auto — From 0 on Value's does not carry over");

            // Return → Value swaps it back, and Value's floor kept its From 0 through the round trip.
            await pressAndRedraw(page, page.getByTestId('lot-comparison-mode-value'), 'Value mode again');
            await expectChoice(modeGroup, page.getByTestId('lot-comparison-mode-value'), 'mode Value again');
            await expect(valueFloor).toBeVisible();
            await expect(returnUnit).toHaveCount(0);
            await expect(returnFloor).toHaveCount(0);
            await expectChoice(valueFloor, page.getByTestId('lot-comparison-value-yaxis-zero'), "Value's Y axis after a round trip through Return");

            // …and the pair's other half.
            await pressAndRedraw(page, page.getByTestId('lot-comparison-value-yaxis-auto'), 'Value Y axis Auto');
            await expectChoice(valueFloor, page.getByTestId('lot-comparison-value-yaxis-auto'), 'Value Y axis Auto again');
        });

        test('comparison chart in Return mode: Abs/% and the Y-axis floor switch both ways, one button per pair pressed, the chart drawn after each click', async ({page}) => {
            // No lot picked here: the chart shows the panel's own selection, every visible lot. The %
            // view needs a lot whose opening value is above zero — the others have no percentage to
            // give — and asking that of the set rather than of one row keeps this test about the
            // controls.
            await openComparisonChart(page);
            const returnUnit = page.getByTestId('lot-comparison-return-abs-pct-toggle');
            const returnFloor = page.getByTestId('lot-comparison-return-yaxis-toggle');

            await pressAndRedraw(page, page.getByTestId('lot-comparison-mode-return'), 'Return mode');
            await expectChoice(returnUnit, page.getByTestId('lot-comparison-return-abs'), 'default Return unit Abs');
            await expectChoice(returnFloor, page.getByTestId('lot-comparison-return-yaxis-auto'), 'default Return Y axis Auto');

            // Each pair moves on its own: the unit leaves the floor alone, and the floor the unit.
            await pressAndRedraw(page, page.getByTestId('lot-comparison-return-pct'), 'Return unit % (needs a visible lot whose opening value is above zero)');
            await expectChoice(returnUnit, page.getByTestId('lot-comparison-return-pct'), 'Return unit %');
            await expectChoice(returnFloor, page.getByTestId('lot-comparison-return-yaxis-auto'), 'Return Y axis, untouched by the unit');

            await pressAndRedraw(page, page.getByTestId('lot-comparison-return-yaxis-zero'), 'Return Y axis From 0');
            await expectChoice(returnFloor, page.getByTestId('lot-comparison-return-yaxis-zero'), 'Return Y axis From 0');
            await expectChoice(returnUnit, page.getByTestId('lot-comparison-return-pct'), 'Return unit, untouched by the floor');

            // Back the other way: each pair's other half.
            await pressAndRedraw(page, page.getByTestId('lot-comparison-return-abs'), 'Return unit Abs');
            await expectChoice(returnUnit, page.getByTestId('lot-comparison-return-abs'), 'Return unit Abs again');

            await pressAndRedraw(page, page.getByTestId('lot-comparison-return-yaxis-auto'), 'Return Y axis Auto');
            await expectChoice(returnFloor, page.getByTestId('lot-comparison-return-yaxis-auto'), 'Return Y axis Auto again');
        });
    });
});

/**
 * The lots charts must never merge their responsive x-axis patch into a chart that holds no option.
 *
 * The defect: `TypeError: Cannot read properties of undefined (reading 'axisBuilder')`, thrown by
 * ECharts 6's `CartesianAxisView.render`. Each lots chart watches its container with a
 * ResizeObserver and, when the usable width is compact (< 480 px), merges a lazy patch
 * `setOption({xAxis: {splitNumber, axisLabel}}, {lazyUpdate: true})`. Merged into an instance that
 * `renderChart()` has just `init()`-ed or `clear()`-ed because there is nothing to draw, it leaves a
 * model with one x-axis and no grid, and the next ECharts frame throws. That frame belongs to
 * ECharts' own loop, not to anything a test awaits, so the only reliable observable is the uncaught
 * exception: every test here collects `pageerror` from before its first navigation and ends on that
 * list being empty.
 *
 * Two UI triggers are pinned:
 * - the Gantt Open/Closed filter narrowed to a state that leaves no lane — deterministic: the sticky
 *   axis node is unmounted, its instance cleared, and the ResizeObserver still reports the removed
 *   node at width 0, which is compact by definition;
 * - the phone load path of the comparison chart — racy on its own (it depends on when the selection
 *   response lands), made deterministic by holding that response.
 *
 * The WAC/price chart has the same site but no UI path reaches its cleared state today; its pin is
 * the source contract in `chartCoreHelpers.test.ts`.
 */

/** The narrowest common phone width, and the house way to get it inside a desktop-project test
 *  (see dashboard.spec.ts): at 375 px the comparison chart's usable width is below the 480 px
 *  threshold, so its policy is compact and the patch path is live from the first paint. */
const PHONE_VIEWPORT = {width: 375, height: 800};

/** An asset held on Interactive Brokers whose every lot is open-ish. */
interface AllOpenLotsAsset {
    id: number;
    name: string;
}

/** The two fields `lotIsOpenish` reads, plus the id the selection request needs. */
type ProbedLot = LotOpenish & {lot_id: number};

/** The uncaught exceptions of one test, and the step each one arrived in. */
interface PageErrorLog {
    /** Every entry reads `[step] message <- frame <- frame <- frame`. */
    readonly list: string[];
    /** Name the step that starts now; call it right before the action that begins the step. */
    mark(step: string): void;
}

/**
 * Collect every uncaught exception the page raises, tagged with the step it arrived in.
 *
 * Registered before the first navigation because the defect throws from ECharts' frame loop, in a
 * frame no action of the test awaits — a listener armed later could miss it. The stack of such a
 * throw is ECharts' own (the axis view, called from its frame loop) and never names the chart, so
 * the step is what tells the triggers apart: several lots charts share the defect and more than one
 * trigger is live at 375 px. Page errors and command replies travel in order, so an error thrown
 * before a step's last await returned carries that step's name.
 */
function collectPageErrors(page: Page): PageErrorLog {
    const list: string[] = [];
    let current = 'login';
    page.on('pageerror', (error) => {
        const frames = (error.stack ?? '')
            .split('\n')
            .slice(1, 4)
            .map((line) => line.trim());
        list.push([`[${current}] ${error.message}`, ...frames].join(' <- '));
    });
    return {
        list,
        mark: (step) => {
            current = step;
        },
    };
}

/** One `POST /portfolio/lots/analysis`, read-only, failing loudly on a non-2xx. */
async function lotsAnalysis(page: Page, body: {asset_id: number; broker_ids: number[]; selected_lot_ids?: number[]; requested_analyses: string[]}): Promise<Record<string, unknown>> {
    const response = await page.request.post('/api/v1/portfolio/lots/analysis', {data: body});
    expect(response.ok(), `lots analysis ${body.requested_analyses.join('+')} for asset ${body.asset_id} answered ${response.status()}`).toBe(true);
    return (await response.json()) as Record<string, unknown>;
}

/**
 * Find an Interactive Brokers holding whose lots are all open-ish, with a value history to draw.
 *
 * Why this shape: the Open/Closed filter is tri-state and exclusive per lot (`filterVisibleLots`:
 * both off means both on; an open-ish lot lands only in the open bucket), so a single state empties
 * the Gantt only for an asset whose lots are all in the other one. Turning "Open" off on an all-open
 * asset leaves no lane. The value history is required because the comparison chart stays hidden
 * without one, and the tests below wait for it to show data.
 *
 * Why read-only on the mock rather than self-owned data: an asset with lots means committed
 * transactions, and `Transaction` has no `user_id` — every other worker would see them, and the
 * test would owe a cleanup. The mock already ships such holdings and nothing here writes.
 *
 * Why this is safe beside neighbours: no test in this file writes transactions or lots, and the
 * candidates are walked in ascending `asset_id`, so the seeded assets (created by
 * populate_mock_data.py before any test runs) come first and an asset created by another spec is
 * only reached if no seeded one qualifies. The choice is a state checked right before use and
 * checked again in the UI after the toggle, so a concurrent writer can only make the precondition
 * fail loudly, never turn the test into a silent pass.
 *
 * The predicate is the product's own `lotIsOpenish`, imported rather than restated, so the probe
 * and the filter cannot disagree about which bucket a lot belongs to.
 */
async function findAllOpenLotsAsset(page: Page, brokerId: number): Promise<AllOpenLotsAsset> {
    const summaryResponse = await page.request.get(`/api/v1/brokers/${brokerId}/summary`);
    expect(summaryResponse.ok(), `broker ${brokerId} summary answered ${summaryResponse.status()}`).toBe(true);
    const summary = (await summaryResponse.json()) as {holdings?: {asset_id: number; asset_name: string}[] | null};
    const candidates = new Map<number, string>();
    for (const holding of summary.holdings ?? []) candidates.set(holding.asset_id, holding.asset_name);

    const verdicts: string[] = [];
    for (const [id, name] of [...candidates].sort(([a], [b]) => a - b)) {
        const analysis = await lotsAnalysis(page, {asset_id: id, broker_ids: [brokerId], requested_analyses: ['LOT_SUMMARY']});
        const lots = (Array.isArray(analysis.lots) ? analysis.lots : []) as ProbedLot[];
        const closed = lots.filter((lot) => !lotIsOpenish(lot)).length;
        if (lots.length === 0 || closed > 0) {
            verdicts.push(`${id} ${name}: ${lots.length} lots, ${closed} closed`);
            continue;
        }

        // The same request the panel's selection step sends for an implicit "all lots" selection.
        const histories = await lotsAnalysis(page, {asset_id: id, broker_ids: [brokerId], selected_lot_ids: lots.map((lot) => lot.lot_id), requested_analyses: ['VALUE_HISTORY', 'RETURN_HISTORY']});
        if (!Array.isArray(histories.value_history) || histories.value_history.length === 0) {
            verdicts.push(`${id} ${name}: all ${lots.length} lots open, no value history`);
            continue;
        }

        // Which asset a green run exercised, for whoever reads the report next.
        test.info().annotations.push({type: 'all-open-lots asset', description: `${id} ${name}`});
        return {id, name};
    }

    throw new Error(`No ${BROKER_WITH_HOLDINGS} holding has only open lots and a value history, so no single state filter can empty its Gantt — check populate_mock_data.py. Candidates: ${verdicts.join('; ') || 'none'}`);
}

/** Interactive Brokers' id, read back from the page the helper landed on, and the asset to use. */
async function resolveAllOpenLotsAsset(page: Page): Promise<{brokerId: number; asset: AllOpenLotsAsset}> {
    // Called right after login, on the Dashboard: the helper opens the broker from the list.
    await navigateTo(page, '/brokers');
    await goToBrokerWithHoldings(page);
    const brokerId = Number(new URL(page.url()).pathname.split('/').filter(Boolean).pop());
    expect(Number.isFinite(brokerId), 'the detail URL carries the broker id').toBe(true);
    return {brokerId, asset: await findAllOpenLotsAsset(page, brokerId)};
}

/** The deep link the page writes itself (`?tab=posizioni&asset=`), so the panel mounts at the
 *  viewport under test from its first paint instead of after a desktop-sized layout. */
function lotsPanelUrl(brokerId: number, assetId: number): string {
    return `/brokers/${brokerId}?tab=posizioni&asset=${assetId}`;
}

/** The render counter `attachChartReady` publishes on a chart container. */
async function chartRenders(chart: Locator): Promise<number> {
    return Number((await chart.getAttribute('data-chart-renders')) ?? '0');
}

/**
 * Let the page run `count` rendering frames.
 *
 * Not a clock wait: it counts frames, not milliseconds, and the defect is scheduled on frames. A
 * ResizeObserver callback runs in a frame's rendering step; the Gantt merges its patch right there,
 * the comparison chart one requestAnimationFrame later; ECharts applies a lazy patch on the next
 * tick of its own rAF loop, and that tick is where it throws. Three frames cover the longest of
 * those chains, and on a slow machine each frame is simply longer. The promise settles in the page,
 * so any pageerror raised in those frames reaches the test before this call returns: the protocol
 * delivers events and replies in order.
 */
async function runFrames(page: Page, count = 3): Promise<void> {
    await page.evaluate(
        (frames) =>
            new Promise<void>((resolve) => {
                const step = (left: number): void => {
                    if (left === 0) resolve();
                    else requestAnimationFrame(() => step(left - 1));
                };
                step(frames);
            }),
        count,
    );
}

/**
 * Open the lots panel on `asset` and wait until it has settled with data.
 *
 * The title barrier comes first on purpose. The panel's currency prop is the asset's own currency
 * once the asset cache resolves (the base currency before), and a currency change re-issues the
 * main request, which swaps every chart for the loading skeleton and mounts it again. The title
 * gains the asset name in the same update, so once it shows, the charts found afterwards are the
 * final ones and cannot be remounted under the test's feet.
 */
async function openLotsPanelSettled(page: Page, brokerId: number, asset: AllOpenLotsAsset): Promise<void> {
    await navigateTo(page, lotsPanelUrl(brokerId, asset.id));
    await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 10_000});
    await expect(page.getByTestId('lots-analysis-panel-title')).toContainText(asset.name, {timeout: 10_000});

    // The Gantt has drawn its lanes, the sticky axis the defect patches is mounted, and the
    // comparison chart shows data (it stays `invisible` while it has nothing to draw).
    await expect(page.getByTestId('lot-gantt-echart')).toHaveAttribute('data-chart-ready', 'true', {timeout: 20_000});
    await expect(page.getByTestId('lot-gantt-sticky-axis')).toBeVisible();
    await expect(page.getByTestId('lot-comparison-echart')).toBeVisible({timeout: 20_000});
}

/**
 * Turn "Open" off so no lane is left, let the defect's frames run, then turn it back on.
 *
 * Turning "Open" off leaves only closed lots, which this asset has none of: `chartHasData` goes
 * false, both chart containers unmount, `renderChart()` clears both instances, and the
 * ResizeObserver still watching the removed axis node fires at width 0 — on the current code, the
 * patch lands on the cleared axis instance here.
 *
 * The frame wait sits before turning "Open" back on because that remount disposes the old axis
 * instance, and a disposed instance skips its pending frame: restoring too early could cancel the
 * very throw this test exists to see. It also orders the evidence: the throw happens on the frame
 * after the removal, the remounted chart can only report ready on a later one, and the pageerror
 * reaches the test before the answer to any later poll.
 */
async function emptyThenRestoreGantt(page: Page, asset: AllOpenLotsAsset, pageErrors: PageErrorLog): Promise<void> {
    const filterOpen = page.getByTestId('lot-gantt-filter-open');
    const lanes = page.getByTestId('lot-gantt-echart');

    await expect(filterOpen).toHaveAttribute('aria-pressed', 'true');
    pageErrors.mark('emptying the Gantt');
    await filterOpen.click();
    await expect(filterOpen).toHaveAttribute('aria-pressed', 'false');
    await expect(page.getByTestId('lot-gantt-filter-closed')).toHaveAttribute('aria-pressed', 'true');

    // Verified, not assumed: the probe said every lot is open, and this is the UI agreeing. The
    // filter control is still on screen, so "no lanes" cannot be "no Gantt at all".
    await expect(page.getByTestId('lot-gantt-state-filter')).toBeVisible();
    await expect(lanes, `${asset.name} (asset ${asset.id}) still draws Gantt lanes with only closed lots shown, so it has a closed lot after all — the mock changed (populate_mock_data.py) or something wrote to this asset during the run`).toHaveCount(0);
    await expect(page.getByTestId('lot-gantt-sticky-axis')).toHaveCount(0);

    await runFrames(page);

    pageErrors.mark('restoring the Gantt');
    await filterOpen.click();
    await expect(filterOpen).toHaveAttribute('aria-pressed', 'true');
    await expect(lanes).toHaveAttribute('data-chart-ready', 'true', {timeout: 10_000});
}

/**
 * Hold every selection request (the lots-analysis POST that asks for VALUE_HISTORY) until release.
 *
 * The panel fetches in two steps: the main analysis (lots, Gantt, WAC — no `selected_lot_ids`),
 * then, once the lots are known, the value/return histories of the selection. The comparison chart
 * mounts between the two with nothing to draw and clears itself: that window is the defect's, and
 * the network decides how long it stays open. Holding the second request keeps it open as long as
 * the test needs, without touching the first. After release, later selection requests pass through.
 */
async function holdSelectionHistories(page: Page): Promise<{held: () => number; release: () => Promise<void>}> {
    const pending: Array<() => Promise<void>> = [];
    let heldTotal = 0;
    let released = false;
    await page.route(/\/api\/v1\/portfolio\/lots\/analysis(\?.*)?$/, async (route) => {
        const body = route.request().postDataJSON() as {requested_analyses?: unknown} | null;
        const analyses = Array.isArray(body?.requested_analyses) ? body.requested_analyses : [];
        if (!released && analyses.includes('VALUE_HISTORY')) {
            heldTotal += 1;
            pending.push(() => route.continue());
            return;
        }
        await route.continue();
    });
    return {
        held: () => heldTotal,
        release: async () => {
            released = true;
            await Promise.all(pending.splice(0).map((resume) => resume()));
        },
    };
}

test.describe('Lots charts axisBuilder guard', () => {
    // No beforeEach on purpose: each test arms its pageerror collector before its first navigation,
    // login included, so nothing the pages do can throw unseen.

    test('Gantt state filter leaving no lane keeps the sticky axis error-free on desktop', async ({page}) => {
        // Login, the broker page, the probe requests and a full panel load before the action.
        test.setTimeout(60_000);
        const pageErrors = collectPageErrors(page);
        await login(page, TEST_USER);
        pageErrors.mark('broker page and asset probe');
        const {brokerId, asset} = await resolveAllOpenLotsAsset(page);

        // Default desktop viewport: the comparison chart is wide here and never patches, so this case
        // isolates the Gantt's sticky axis.
        pageErrors.mark('opening the lots panel');
        await openLotsPanelSettled(page, brokerId, asset);
        await emptyThenRestoreGantt(page, asset, pageErrors);

        expect(pageErrors.list, `uncaught page errors while ${asset.name} (asset ${asset.id}) had its Gantt emptied by the state filter and restored at 1280 px — "axisBuilder" is the responsive x-axis patch merged into a cleared chart`).toEqual([]);
    });

    test('Gantt state filter leaving no lane keeps the sticky axis and the comparison chart error-free at 375 px', async ({page}) => {
        test.setTimeout(60_000);
        const pageErrors = collectPageErrors(page);
        await login(page, TEST_USER);
        pageErrors.mark('broker page and asset probe');
        const {brokerId, asset} = await resolveAllOpenLotsAsset(page);

        // Phone width from the panel's first paint: the Gantt path as on desktop, plus the comparison
        // chart, which unmounts with the empty selection and remounts cleared when "Open" comes back.
        await page.setViewportSize(PHONE_VIEWPORT);
        pageErrors.mark('opening the lots panel');
        await openLotsPanelSettled(page, brokerId, asset);
        await emptyThenRestoreGantt(page, asset, pageErrors);

        // The comparison chart shows data again only once the new selection response has landed; a
        // throw from its cleared remount has happened by then.
        await expect(page.getByTestId('lot-comparison-echart')).toBeVisible({timeout: 20_000});

        expect(pageErrors.list, `uncaught page errors while ${asset.name} (asset ${asset.id}) had its Gantt emptied by the state filter and restored at 375 px — "axisBuilder" is the responsive x-axis patch merged into a cleared chart`).toEqual([]);
    });

    test('opening the lots panel at 375 px with the selection histories held keeps the comparison chart error-free', async ({page}) => {
        test.setTimeout(60_000);
        const pageErrors = collectPageErrors(page);
        await login(page, TEST_USER);
        pageErrors.mark('broker page and asset probe');
        const {brokerId, asset} = await resolveAllOpenLotsAsset(page);

        // Armed before the navigation: the selection request leaves as soon as the main one lands.
        const selection = await holdSelectionHistories(page);
        await page.setViewportSize(PHONE_VIEWPORT);
        pageErrors.mark('opening the lots panel, histories held');
        await navigateTo(page, lotsPanelUrl(brokerId, asset.id));
        await expect(page.getByTestId('lots-analysis-panel-title')).toContainText(asset.name, {timeout: 10_000});

        // The state the defect needs, verified: the chart is mounted, has painted its cleared frame,
        // shows nothing (it stays `invisible` without data), and its histories are really held.
        const comparison = page.getByTestId('lot-comparison-echart');
        await expect(comparison).toBeAttached({timeout: 20_000});
        await expect.poll(() => selection.held(), {message: 'the selection request must be held, or the chart is not in the state this test is about', timeout: 10_000}).toBeGreaterThan(0);
        await expect.poll(() => chartRenders(comparison), {timeout: 10_000}).toBeGreaterThanOrEqual(1);
        await expect(comparison).toBeHidden();

        // ResizeObserver → rAF (patch) → ECharts frame (throw): let that chain finish before the data
        // can arrive, so the release cannot pre-empt it.
        await runFrames(page);

        const before = await chartRenders(comparison);
        pageErrors.mark('releasing the histories');
        await selection.release();
        await expect(comparison).toBeVisible({timeout: 20_000});
        await expect.poll(() => chartRenders(comparison), {message: 'the comparison chart must paint the released histories', timeout: 10_000}).toBeGreaterThan(before);

        expect(pageErrors.list, `uncaught page errors while ${asset.name} (asset ${asset.id}) loaded its lots panel at 375 px with the selection histories held — "axisBuilder" is the responsive x-axis patch merged into a cleared chart`).toEqual([]);
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

/**
 * `EUR 1,234.56` / `EUR -12.30` — an unsigned tooltip amount (the OHLC rows). The
 * minus is the browser locale's own (D23): ASCII in English, U+2212 in Swedish.
 */
const BROKER_PLAIN_AMOUNT = /^[A-Z]{3}\s[-\u2212]?[\d.,]+$/;
/**
 * `EUR +359.04` / `EUR -12.00` / `EUR 0.00` — a P&L or income tooltip amount.
 * One form for every signed row (D23b): the sign after the currency, the minus
 * the locale's own, ASCII or U+2212 (D23). Sign optional: a zero carries none, by
 * design (a green zero read as a gain), so a signed-only pattern stops counting a
 * row on the day its value is zero.
 */
const BROKER_AMOUNT = /^[A-Z]{3}\s[+\-\u2212]?[\d.,]+$/;

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
    // The beforeEach leaves the page on the Dashboard: the helper opens the broker from the list.
    await navigateTo(page, '/brokers');
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
        // A hook runs before the test can raise its own timeout, and this one waits for a
        // whole-portfolio report: it gets the budget the three tests ask for themselves.
        test.setTimeout(60_000);
        await login(page, TEST_USER);

        // login() returns once the app has arrived — the Dashboard it lands on has mounted with the
        // shell, but has not finished loading — and that Dashboard asks its own report, with the
        // income family and `broker_ids` set to every broker the user owns. A recorder armed before
        // it has asked records it, and `reports.find(...)` then reads the portfolio's request as this
        // broker's overview. So every test starts from a landing page that has finished asking.
        const dashboard = page.getByTestId('dashboard-page');
        await expect(dashboard, 'login() lands TEST_USER on the Dashboard').toBeVisible({timeout: 15_000});
        await waitForSettled(dashboard, 30_000);
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
        // per-broker overlay to add a second row (plan §3.3). Counted by ROW, not by
        // sign: every value row of the tooltip is `<span>label</span><b>value</b>`,
        // so "one value cell, and it is an amount" is exact whatever the total is at
        // the pointer — a zero total prints unsigned, and an overlay row with no
        // value that day would print `—`, which an amount count would never see.
        await selectBrokerSubmode(chart, 'line');
        await showChartTooltip(page, chart, chart.getByText(BROKER_AMOUNT), 10_000, 1);
        await expect(chart.locator('div > span + b'), 'exactly one value row, the total P&L — an amount, sign optional').toHaveText([BROKER_AMOUNT]);

        // Income: dividend, interest and their total — three rows at the floor,
        // which a submode that never bound its income series could not produce.
        // Not an exact count: the batch-2 rows (costs, deposit, acquisition) are
        // sparse and only join on a day that had that activity, so an equality
        // would pin which day the pointer happened to land on. Sign optional for
        // the same reason: the three are always written, but on a week without a
        // dividend or an interest payment all three are zero, and a zero is unsigned.
        await selectBrokerSubmode(chart, 'income');
        const amounts = chart.getByText(BROKER_AMOUNT);
        await showChartTooltip(page, chart, amounts, 10_000, 3);
        await expect.poll(() => amounts.count(), {message: 'dividend, interest and their total are always in the income tooltip, zero or not'}).toBeGreaterThanOrEqual(3);
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

        // An overlay line would add a row per broker, named after it, so the value
        // rows must be exactly the four OHLC values. Counted BY ROW, never by sign:
        // after D23b a losing broker row reads exactly like a negative OHLC value
        // (`EUR -12.00`), and a zero one like any unsigned amount, so no pattern can
        // tell the two apart. Every value row is `<span>label</span><b>value</b>`.
        await expect(chart.locator('div > span + b'), 'the four OHLC values and nothing else — an overlay would add a fifth, broker-named row').toHaveText([BROKER_PLAIN_AMOUNT, BROKER_PLAIN_AMOUNT, BROKER_PLAIN_AMOUNT, BROKER_PLAIN_AMOUNT]);
        await expect(chart.getByText(BROKER_WITH_HOLDINGS, {exact: true}), 'the broker name would only appear here as an overlay legend row').toHaveCount(0);
    });
});

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Import history modal — uploading a BRIM file.
 *
 * `POST /brokers/import/upload` reads `broker_id` from the multipart **form**
 * (`Form(...)`). BrokerImportFilesModal sent it as a query parameter and put only
 * `file` in the FormData, so every upload from this modal answered 422 and the user
 * got nothing but an error banner. The status is asserted first because it *is* the
 * defect; the stored file is then read back through the API, scoped to a broker this
 * test creates — the mock seeds its own `generic_simple.csv` on Interactive Brokers,
 * so matching by file name alone would prove nothing.
 */
const API = '/api/v1';
const BRIM_UPLOAD_PATH = `${API}/brokers/import/upload`;
/** The repository's synthetic Generic CSV sample — never a real broker export. */
const SAMPLE_BRIM_REPORT = path.resolve(__dirname, '../../../backend/app/services/brim_providers/sample_reports/generic_simple.csv');
const SAMPLE_BRIM_REPORT_NAME = path.basename(SAMPLE_BRIM_REPORT);

type BrimFileInfo = {file_id: string; filename: string; target_broker_id: number | null};

/** A broker this test owns. The name goes through `uniqueSuffix()`: `brokers.name` is uniquely indexed. */
async function createOwnedBroker(page: Page, name: string): Promise<number> {
    const response = await page.request.post(`${API}/brokers`, {data: [{name, allow_cash_overdraft: true}]});
    expect(response.ok(), `create owned broker: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const {results} = (await response.json()) as {results: Array<{name: string; success: boolean; broker_id: number | null}>};
    const created = results.find((result) => result.name === name);
    if (!created?.success || typeof created.broker_id !== 'number') throw new Error(`Owned broker "${name}" was not created: ${JSON.stringify(results)}`);
    return created.broker_id;
}

/**
 * The BRIM files stored on one broker. The list endpoint also returns legacy files that
 * carry no broker at all, so the target is filtered here rather than assumed.
 */
async function brimFilesOn(page: Page, brokerId: number): Promise<BrimFileInfo[]> {
    const response = await page.request.get(`${API}/brokers/import/files?broker_ids=${brokerId}`);
    expect(response.ok(), `list the BRIM files of broker ${brokerId}: HTTP ${response.status()}`).toBe(true);
    const files = (await response.json()) as BrimFileInfo[];
    return files.filter((file) => file.target_broker_id === brokerId);
}

/**
 * Delete every BRIM file on the owned broker, then the broker. Scoped to the id this
 * test created, never to "whatever appeared since"; when the upload never happened
 * there is simply no file to delete, so the red this block exists for stays the only red.
 */
async function deleteOwnedBrokerAndFiles(page: Page, brokerId: number): Promise<void> {
    const failures: string[] = [];
    try {
        for (const file of await brimFilesOn(page, brokerId)) {
            const response = await page.request.delete(`${API}/brokers/import/files/${file.file_id}`);
            if (!response.ok()) failures.push(`BRIM file ${file.file_id}: HTTP ${response.status()}`);
        }
    } catch (error) {
        failures.push(`list the BRIM files of broker ${brokerId}: ${String(error)}`);
    }
    try {
        const response = await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`);
        const body = (await response.json().catch(() => null)) as {results?: Array<{id: number; success: boolean}>} | null;
        if (!response.ok() || !body?.results?.find((result) => result.id === brokerId)?.success) failures.push(`broker ${brokerId}: HTTP ${response.status()} ${JSON.stringify(body)}`);
    } catch (error) {
        failures.push(`broker ${brokerId}: ${String(error)}`);
    }
    expect(failures, 'cleanup removes the BRIM files and the broker this test created').toEqual([]);
}

test.describe('Broker detail — import history upload', () => {
    let ownedBrokerId: number | undefined;

    test.beforeEach(async ({page}) => {
        ownedBrokerId = undefined;
        await login(page, TEST_USER);
    });

    // afterEach, not `finally`: a cleanup throwing from `finally` would replace the
    // assertion error it follows, and that assertion is the point of this block.
    test.afterEach(async ({page}) => {
        if (ownedBrokerId !== undefined) await deleteOwnedBrokerAndFiles(page, ownedBrokerId);
    });

    test('uploads a report from the import history modal to its own broker', async ({page}) => {
        test.setTimeout(60_000);
        // Sorts after every seeded broker, so a neighbour's "first card" stays a mock broker.
        const brokerName = `Upload regression history ${uniqueSuffix()}`;
        const brokerId = await createOwnedBroker(page, brokerName);
        ownedBrokerId = brokerId;

        await navigateTo(page, `/brokers/${brokerId}`);
        await expect(page.getByTestId('broker-name')).toHaveText(brokerName, {timeout: 10_000});
        await goToTransazioniTab(page);
        await page.getByTestId('broker-show-import-history').click();
        const modal = page.getByTestId('import-files-modal');
        await expect(modal).toBeVisible({timeout: 5_000});

        await modal.getByTestId('import-files-upload-toggle').click();
        const uploader = modal.getByTestId('file-uploader');
        await expect(uploader).toBeVisible({timeout: 5_000});
        await uploader.getByTestId('file-input').setInputFiles(SAMPLE_BRIM_REPORT);
        const submit = uploader.getByTestId('file-upload-submit');
        await expect(submit).toBeVisible({timeout: 5_000});

        // Armed before the click: a response is an edge, not a state.
        const uploadResponse = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === BRIM_UPLOAD_PATH, {timeout: 15_000});
        await submit.click();
        const upload = await uploadResponse;
        const body = await upload.text();
        expect(upload.status(), `POST ${BRIM_UPLOAD_PATH} from the import history modal: ${body}`).toBe(200);

        const uploaded = JSON.parse(body) as BrimFileInfo;
        expect(uploaded, 'the modal uploads to the broker whose history it shows').toMatchObject({filename: SAMPLE_BRIM_REPORT_NAME, target_broker_id: brokerId});
        const stored = (await brimFilesOn(page, brokerId)).filter((file) => file.filename === SAMPLE_BRIM_REPORT_NAME);
        expect(
            stored.map((file) => file.file_id),
            `${SAMPLE_BRIM_REPORT_NAME} is stored exactly once on broker ${brokerId}`,
        ).toEqual([uploaded.file_id]);

        // …and the modal lists it: on success handleUpload reloads this broker's files.
        await expect(modal.locator(`[data-row-id="${uploaded.file_id}"]`)).toBeVisible({timeout: 8_000});
    });

    // ── C1: one upload action is one report-set batch (design D-S22) ─────────────
    //
    // Every file of one upload carries the same client-generated `batch_id` (a UUID in
    // the multipart form), and the next upload from the same modal opens a new batch:
    // the server builds report sets per batch, so an id shared by two uploads would
    // merge two sets, and no id at all leaves every file a set of its own. Read back
    // from this page's own upload responses, never from a shared list.
    const SECOND_BRIM_REPORT = path.resolve(__dirname, '../../../backend/app/services/brim_providers/sample_reports/generic_with_assets.csv');
    const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    type UploadedInfo = BrimFileInfo & {batch_id?: string | null};

    /** The upload responses `action` produces on this page: exactly `expected` of them, each a 200. */
    async function uploadsDuring(page: Page, expected: number, action: () => Promise<void>): Promise<UploadedInfo[]> {
        const replies: Array<Promise<{status: number; body: string}>> = [];
        const listener = (response: Awaited<ReturnType<Page['waitForResponse']>>) => {
            if (response.request().method() === 'POST' && new URL(response.url()).pathname === BRIM_UPLOAD_PATH) replies.push(response.text().then((body) => ({status: response.status(), body})));
        };
        // Armed before the action: a response is an edge, not a state.
        page.on('response', listener);
        try {
            await action();
            await expect.poll(() => replies.length, {message: `${expected} upload response(s) from one action`, timeout: 15_000}).toBe(expected);
        } finally {
            page.off('response', listener);
        }
        const settled = await Promise.all(replies);
        for (const {status, body} of settled) expect(status, `POST ${BRIM_UPLOAD_PATH}: ${body}`).toBe(200);
        return settled.map(({body}) => JSON.parse(body) as UploadedInfo);
    }

    /** Opens the modal's uploader and submits `files`; ends once the uploader has handed them over. */
    async function uploadFromHistoryModal(modal: Locator, files: string[]): Promise<void> {
        await modal.getByTestId('import-files-upload-toggle').click();
        const uploader = modal.getByTestId('file-uploader');
        await expect(uploader).toBeVisible({timeout: 5_000});
        await uploader.getByTestId('file-input').setInputFiles(files);
        await uploader.getByTestId('file-upload-submit').click();
        // handleUpload hides the uploader as soon as it starts sending.
        await expect(uploader).toBeHidden({timeout: 5_000});
    }

    function expectUuid(value: string | null | undefined, what: string): string {
        expect(typeof value === 'string' && UUID_PATTERN.test(value), `${what}: ${JSON.stringify(value)} must be a UUID`).toBe(true);
        return value as string;
    }

    test('C1 one upload from the import history modal gives its files one fresh batch id', async ({page}) => {
        test.setTimeout(60_000);
        const brokerName = `Upload batch history ${uniqueSuffix()}`;
        const brokerId = await createOwnedBroker(page, brokerName);
        ownedBrokerId = brokerId;

        await navigateTo(page, `/brokers/${brokerId}`);
        await expect(page.getByTestId('broker-name')).toHaveText(brokerName, {timeout: 10_000});
        await goToTransazioniTab(page);
        await page.getByTestId('broker-show-import-history').click();
        const modal = page.getByTestId('import-files-modal');
        await expect(modal).toBeVisible({timeout: 5_000});

        const together = await uploadsDuring(page, 2, () => uploadFromHistoryModal(modal, [SAMPLE_BRIM_REPORT, SECOND_BRIM_REPORT]));
        expect(
            together.map((file) => file.target_broker_id),
            'both files go to this broker',
        ).toEqual([brokerId, brokerId]);
        const batchIds = together.map((file) => file.batch_id);
        const batchId = expectUuid(batchIds[0], 'batch_id of the first upload');
        expect(batchIds, 'the files of one upload share one batch_id').toEqual([batchId, batchId]);

        // The list reloads once the upload is over, so the next upload starts from an idle modal.
        for (const file of together) await expect(modal.locator(`[data-row-id="${file.file_id}"]`)).toBeVisible({timeout: 8_000});
        const [next] = await uploadsDuring(page, 1, () => uploadFromHistoryModal(modal, [SAMPLE_BRIM_REPORT]));
        expect(expectUuid(next.batch_id, 'batch_id of the next upload'), 'every upload action opens a new batch').not.toBe(batchId);
    });
});

/**
 * 6b — the Bulk editor opened before the transaction types are cached.
 *
 * The editor snapshots its rows when it opens, to tell "nothing to discard" from unsaved work.
 * With the type rules not cached yet it takes its slow path: rows held back until the types
 * arrive, and the snapshot written as `''` while the rows stand at `[]`, whose key is `'[]'`.
 * With rows (edit, clone, delete) the snapshot is written again once the types land; with none
 * (create, import) it never is, so every close asks to discard changes nobody made.
 *
 * The broker page is where that happens for real: unlike the transactions page it never loads
 * the types itself, and the cache is module state, empty after every full load. So each test
 * loads the page from scratch, on a broker it owns, and checks that premise instead of assuming
 * it — no request for the types before the click, one answered after the editor opened.
 *
 * Why the barriers before each close: the editor's open sequence awaits four reference caches
 * (brokers, currencies, assets, types) and then opens its auto-opened child again — the form,
 * or the import wizard — if that child is closed by then. A child closed before the sequence
 * ends comes back over the editor. So the page's own loads have landed before the click, and
 * the types are in the page before the child is closed.
 */

/** The caches the Bulk editor awaits when it opens (`ensure*Loaded`), by endpoint. */
const BULK_REFERENCE_PATHS = {
    types: `${API}/transactions/types`,
    brokers: `${API}/brokers`,
    assets: `${API}/assets/query`,
    currencies: `${API}/utilities/currencies`,
} as const;
type BulkReference = keyof typeof BULK_REFERENCE_PATHS;
const BULK_REFERENCES = Object.keys(BULK_REFERENCE_PATHS) as BulkReference[];

/** The page's GET requests to the four caches since the watch began. */
interface BulkReferenceLoads {
    requested: Record<BulkReference, number>;
    /** Requests whose whole answer has arrived (`requestfinished`). */
    finished: Record<BulkReference, number>;
    /** Requests to any of the four still waiting for their answer. */
    inFlight: () => number;
}

/** Count the reference loads request by request: each one is settled by its own finished or failed event. */
function watchBulkReferenceLoads(page: Page): BulkReferenceLoads {
    const counter = () => Object.fromEntries(BULK_REFERENCES.map((name) => [name, 0])) as Record<BulkReference, number>;
    const requested = counter();
    const finished = counter();
    const pending = new Map<object, BulkReference>();
    const referenceOf = (request: {method(): string; url(): string}) => (request.method() === 'GET' ? BULK_REFERENCES.find((name) => BULK_REFERENCE_PATHS[name] === new URL(request.url()).pathname) : undefined);
    page.on('request', (request) => {
        const name = referenceOf(request);
        if (!name) return;
        requested[name] += 1;
        pending.set(request, name);
    });
    page.on('requestfinished', (request) => {
        const name = pending.get(request);
        if (!name) return;
        pending.delete(request);
        finished[name] += 1;
    });
    page.on('requestfailed', (request) => {
        pending.delete(request);
    });
    return {requested, finished, inFlight: () => pending.size};
}

/**
 * Load the owned broker's page from scratch and stop on its Transactions tab, the premise verified.
 *
 * The watch starts on a blank page, so it counts that one document's requests and nothing the
 * landing page left in flight; `page.goto` is the full load that empties the types cache.
 */
async function openBrokerTransactionsCold(page: Page, brokerId: number, brokerName: string): Promise<BulkReferenceLoads> {
    await page.goto('about:blank');
    const loads = watchBulkReferenceLoads(page);
    await navigateTo(page, `/brokers/${brokerId}`);
    await expect(page.getByTestId('broker-name')).toHaveText(brokerName, {timeout: 10_000});
    await goToTransazioniTab(page);
    await expect
        .poll(() => ({brokers: loads.finished.brokers > 0, assets: loads.finished.assets > 0, currencies: loads.finished.currencies > 0, inFlight: loads.inFlight()}), {
            message: 'the broker page has loaded its brokers, assets and currencies itself, and nothing is in flight, before the Bulk editor opens',
            timeout: 15_000,
        })
        .toEqual({brokers: true, assets: true, currencies: true, inFlight: 0});
    expect(loads.requested.types, 'premise: the broker page never asked for the transaction types, so the Bulk editor opens on an empty types cache (its slow path)').toBe(0);
    return loads;
}

/** The premise's second half: once open, the editor fetched the types itself — and every load its open sequence awaits has landed. */
async function bulkFetchedTheTypes(loads: BulkReferenceLoads): Promise<void> {
    await expect
        .poll(() => ({typesAnswered: loads.finished.types > 0, inFlight: loads.inFlight()}), {
            message: 'premise: the Bulk editor fetched the transaction types itself after opening (it opened before they were cached), and its reference loads have landed',
            timeout: 15_000,
        })
        .toEqual({typesAnswered: true, inFlight: 0});
}

/**
 * Close the Bulk editor while it holds no row, and prove its discard guard stayed silent.
 *
 * The premise first: the editor's body is on screen and holds no row, so there is nothing to
 * discard. `requestClose()` is either/or — it opens the guard and returns, or it closes the
 * editor — so after one click the outcome is read as one state, and a guard that fired is
 * reported by name instead of as a timeout on an editor that stayed open.
 */
async function closeEmptyBulkWithoutGuard(page: Page): Promise<void> {
    const bulk = page.getByTestId('tx-bulk-modal');
    const discard = page.getByTestId('confirm-modal-confirm');
    const body = page.getByTestId('tx-bulk-body');
    await expect(body).toBeVisible();
    await expect(body.locator('tbody tr[data-row-id]'), 'the editor holds no row: nothing was added').toHaveCount(0);
    await waitForSettled(page.getByTestId('tx-bulk-modal-root'));

    await page.getByTestId('tx-bulk-close').click();
    await expect
        .poll(async () => ((await discard.isVisible()) ? 'discard guard' : (await bulk.isVisible()) ? 'open' : 'closed'), {
            message: 'one click on the close button of an editor holding no row closes it, without asking to discard changes',
            timeout: 5_000,
        })
        .toBe('closed');
    await expect(discard).toHaveCount(0);
}

test.describe('Broker detail — the Bulk editor opened before the transaction types are cached (6b)', () => {
    let ownedBrokerId: number | undefined;

    test.beforeEach(async ({page}) => {
        ownedBrokerId = undefined;
        await login(page, TEST_USER);
    });

    // afterEach, not `finally`: a cleanup throwing from `finally` would replace the assertion
    // error it follows. Nothing is saved here, so the owned broker is all there is to remove.
    test.afterEach(async ({page}) => {
        if (ownedBrokerId !== undefined) await deleteOwnedBrokerAndFiles(page, ownedBrokerId);
    });

    test('B6a New transaction on a cold broker page, its form closed untouched: the Bulk closes without asking to discard', async ({page}) => {
        test.setTimeout(60_000);
        // Sorts after every seeded broker, so a neighbour's "first card" stays a mock broker.
        const brokerName = `Unsaved guard new ${uniqueSuffix()}`;
        ownedBrokerId = await createOwnedBroker(page, brokerName);
        const loads = await openBrokerTransactionsCold(page, ownedBrokerId, brokerName);

        await page.getByTestId('broker-new-transaction').click();
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});
        const form = page.getByTestId('tx-form-modal');
        await expect(form, 'creating from the broker page opens the Bulk editor with its form already open').toBeVisible({timeout: 5_000});
        await bulkFetchedTheTypes(loads);
        // The in-page side of the same fact: the type select lists no type until the type rules
        // are in the page, so it shows the selected type — with its icon — only from then on.
        await expect(form.getByTestId('tx-form-type').locator('img')).toHaveCount(1, {timeout: 5_000});

        await form.getByTestId('tx-form-cancel').click();
        await expect(form, 'the untouched form closes on its own Cancel, without a guard of its own').toBeHidden({timeout: 5_000});
        await expect(page.getByTestId('confirm-modal-confirm')).toHaveCount(0);

        await closeEmptyBulkWithoutGuard(page);
    });

    test('B6b Import on a cold broker page, its wizard closed untouched: the Bulk closes without asking to discard', async ({page}) => {
        test.setTimeout(60_000);
        const brokerName = `Unsaved guard import ${uniqueSuffix()}`;
        ownedBrokerId = await createOwnedBroker(page, brokerName);
        const loads = await openBrokerTransactionsCold(page, ownedBrokerId, brokerName);

        await page.getByTestId('broker-import-transactions').click();
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});
        const wizard = page.getByTestId('import-wizard-modal');
        await expect(wizard, 'importing from the broker page opens the Bulk editor with its import wizard already open').toBeVisible({timeout: 5_000});
        await bulkFetchedTheTypes(loads);
        // The wizard's first step is idle only once its brokers, type rules and plugins are in the page.
        await waitForSettled(page.getByTestId('import-wizard-step1'));

        await page.getByTestId('import-wizard-close').click();
        await expect(wizard, 'the untouched wizard closes without a guard of its own').toBeHidden({timeout: 5_000});
        await expect(page.getByTestId('confirm-modal-confirm')).toHaveCount(0);

        await closeEmptyBulkWithoutGuard(page);
    });
});

// ============================================================================
// The quota badge in the UI language
// ============================================================================

/**
 * The signed-in user's share, in the badge beside the broker's name, written the reader's way.
 *
 * Defect (after train 37): the page prints `formatSharePercentage(v)` — that is
 * `(Math.round(v * 10000) / 100).toFixed(1)` — and a `%`, so a French reader gets `45.7%` where
 * French writes `45,7 %`, with a decimal comma and a no-break space before the sign. The cure
 * hands the same pre-rounded value to the shared `formatPercent` with
 * `{signed: false, digits: 1, locale: $currentLanguage}`: same digit, same rounding, no sign; only
 * the notation follows the UI language.
 *
 * Data. A broker this test creates, whose complete access list it then sets to one row: the
 * signed-in user, OWNER of 45.67% — a figure with a decimal in both notations that rounds to one
 * digit without a tie. A new broker gives its creator 100%; the PUT makes the figure the test's
 * own instead of the default's, and the answer is checked to be exactly that one row.
 *
 * Expectations. The French string is computed by the browser's own Intl (`page.evaluate`) and
 * never written down: Chromium may put U+202F before the `%` where Node puts U+00A0. The English
 * text is the one literal — today's exact badge, which the cure must leave alone.
 *
 * Language. Through the header selector (`setLanguage`), which writes only this browser context's
 * localStorage: no other test sees the French, and the context ends with the test. The page is a
 * legacy component, where a template call whose expression does not name `$currentLanguage` keeps
 * the notation it had at mount (R20, BrokerCard.test.ts) — so one test opens the page in French and
 * the other switches language with the page on screen.
 *
 * Reading. The badge's text, trimmed of the template's whitespace (its role icon carries none),
 * polled and compared exactly: `toHaveText` normalises whitespace, which would let a plain space
 * pass for the no-break one.
 */

/** The signed-in user's share of the owned broker, a fraction as the API stores it. */
const QUOTA_SHARE = 0.4567;
/** What the page computes before printing, `Math.round(share * 10000) / 100`; the cure keeps it. */
const QUOTA_PERCENT = Math.round(QUOTA_SHARE * 10000) / 100;
/** Today's English badge, exactly: one digit and a `%` — no sign, no space. */
const QUOTA_ENGLISH = '45.7%';

/** `text` with its no-break spaces spelled out, so a message tells U+00A0 and U+202F from a space. */
function spelledSpaces(text: string): string {
    return text.replace(/[\u00a0\u202f]/g, (space) => `\\u${space.charCodeAt(0).toString(16).padStart(4, '0')}`);
}

/** The signed-in user's id, from the session `page.request` shares with the page. */
async function signedInUserId(page: Page): Promise<number> {
    const response = await page.request.get(`${API}/auth/me`);
    expect(response.ok(), `GET /auth/me: HTTP ${response.status()}`).toBe(true);
    const id = ((await response.json()) as {user?: {id?: unknown}}).user?.id;
    if (typeof id !== 'number') throw new Error(`GET /auth/me returned no user id: ${JSON.stringify(id)}`);
    return id;
}

/**
 * Make the signed-in user OWNER of `share` of a broker the test created. The bulk PUT replaces the
 * whole access list, and that list is this one row: the answer must be exactly it.
 */
async function setOwnQuota(page: Page, brokerId: number, share: number): Promise<void> {
    const userId = await signedInUserId(page);
    const response = await page.request.put(`${API}/brokers/${brokerId}/access`, {data: [{user_id: userId, role: 'OWNER', share_percentage: share}]});
    expect(response.ok(), `PUT the access list of broker ${brokerId}: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const {results} = (await response.json()) as {results: Array<{user_id: number; role: string; share_percentage: number | string}>};
    // Cardinality is the premise, not a guess: the test owns this broker's complete access list.
    expect(
        results.map((row) => ({user_id: row.user_id, role: row.role, share: Number(row.share_percentage)})),
        'the owned broker has one access row: its creator, OWNER of the share set',
    ).toEqual([{user_id: userId, role: 'OWNER', share}]);
}

/** Open the owned broker's page; ends once its own name — and, inside the same block, the badge — is on screen. */
async function openOwnedBroker(page: Page, brokerId: number, brokerName: string): Promise<void> {
    await navigateTo(page, `/brokers/${brokerId}`);
    await expect(page.getByTestId('broker-name')).toHaveText(brokerName, {timeout: 10_000});
    await expect(page.getByTestId('broker-quota-badge')).toBeVisible();
}

/** The badge as the reader sees it: the share and its unit. */
async function quotaBadgeText(page: Page): Promise<string> {
    return ((await page.getByTestId('broker-quota-badge').textContent()) ?? '').trim();
}

/** The badge's figure in French notation, one digit, from the browser's own Intl. */
async function frenchQuota(page: Page): Promise<string> {
    const french = await page.evaluate(([percent, digits]) => new Intl.NumberFormat('fr', {style: 'percent', minimumFractionDigits: digits, maximumFractionDigits: digits}).format(percent / 100), [QUOTA_PERCENT, 1] as const);
    expect(french, 'control: this browser has French ICU data, so the two notations differ').toContain(',');
    return french;
}

test.describe('Broker detail — the quota badge in the UI language', () => {
    let ownedBrokerId: number | undefined;

    test.beforeEach(async ({page}) => {
        ownedBrokerId = undefined;
        await login(page, TEST_USER);
    });

    // afterEach, not `finally`: a cleanup throwing from `finally` would replace the assertion
    // error it follows, and that assertion is the point of this block.
    test.afterEach(async ({page}) => {
        if (ownedBrokerId !== undefined) await deleteOwnedBrokerAndFiles(page, ownedBrokerId);
    });

    /** A broker of this test's own, whose badge shows QUOTA_SHARE. */
    async function createQuotaBroker(page: Page): Promise<{brokerId: number; brokerName: string}> {
        // Never sorts first, so a neighbour's "first card" stays a mock broker.
        const brokerName = `Quota badge locale ${uniqueSuffix()}`;
        const brokerId = await createOwnedBroker(page, brokerName);
        ownedBrokerId = brokerId;
        await setOwnQuota(page, brokerId, QUOTA_SHARE);
        return {brokerId, brokerName};
    }

    test('opened with the UI in French, the badge writes the share in French notation', async ({page}) => {
        test.setTimeout(45_000);
        const {brokerId, brokerName} = await createQuotaBroker(page);
        await setLanguage(page, 'fr');
        await openOwnedBroker(page, brokerId, brokerName);
        await expect(page.locator('html'), 'control: the page opened in French').toHaveAttribute('lang', 'fr');

        const french = await frenchQuota(page);
        await expect.poll(() => quotaBadgeText(page), {message: `the badge in French notation, ${spelledSpaces(french)}`, timeout: 5_000}).toBe(french);
    });

    test('switched to French with the page on screen, the badge follows: today’s English text first, then French notation', async ({page}) => {
        test.setTimeout(45_000);
        const {brokerId, brokerName} = await createQuotaBroker(page);
        // English explicitly: a session starts in the language of the user's settings.
        await setLanguage(page, 'en');
        await openOwnedBroker(page, brokerId, brokerName);
        await expect.poll(() => quotaBadgeText(page), {message: 'English UI (control): the badge is exactly today’s text', timeout: 5_000}).toBe(QUOTA_ENGLISH);

        await setLanguage(page, 'fr');
        const french = await frenchQuota(page);
        await expect.poll(() => quotaBadgeText(page), {message: `en → fr in place: the badge in French notation, ${spelledSpaces(french)}`, timeout: 5_000}).toBe(french);
    });
});

// ============================================================================
// A FAILED lots analysis names the transaction to fix (J-12)
// ============================================================================

/**
 * A lots analysis whose FIFO replay of the quantities breaks draws no lot and names the transactions to fix (J-12,
 * panel half; the developer's decision N81, option A).
 *
 * The contract. On `calculation_status: FAILED` the panel takes no lot-derived section of the answer (lots, Gantt,
 * events, per-lot price history, income): the WAC/price chart keeps its average-cost lines and the market price line,
 * which comes from the lot-independent `market_price_history` (Y-30), and the Gantt, the lots table and
 * the comparison chart are not rendered. `LotAnalysisFailedNotice` (`lots-analysis-panel-failed`) explains, then lists
 * each issue flagged `fails_analysis` as `lots-analysis-failed-row-{code}-{transaction id}`: the broker's name, the day
 * of the transaction, the message, and a button to `/transactions?highlight=<id>`. The banner keeps the other issues.
 * J's backend half answers a FAILED analysis with those sections null and each blocking issue carrying
 * `transaction_date` and `fails_analysis: true`.
 *
 * When it can run: once J's half is in dev. Before that, the failure premise — the analysis read through the API
 * before the page is opened — goes red naming the missing flag, instead of a row that times out.
 *
 * The data, every row the test's own. A broker allowing both cash overdraft and shorting: a commit's balance check
 * (`_validate_broker_balances`) is skipped only when both are allowed, and the BUY is not funded. A manual EUR stock
 * with four closes; EUR everywhere, so no rate enters the replay. BUY 10 at 100, forty days ago; SELL 15 at 110, thirty
 * days ago: the SELL closes the long lot and, the broker allowing it, opens a short lot of 5 (engine `_apply_sell`).
 * That replays, and it is the control: on it the same page draws the Gantt, the table and the comparison. Then
 * ADJUSTMENT −2, twenty days ago, without cost (a negative adjustment needs none): no long unit is left to take it and
 * the broker holds −5, so the engine refuses it (`_apply_adjustment_out`: SHORT_ADJUSTMENT_NOT_SUPPORTED, missing 2),
 * a code that fails the whole replay (`_QUANTITATIVE_FAILURE_CODES`). Nothing else is raised: no transfer, no income,
 * one currency. The broker's name holds no digit, so no number in the notice row can be the name's. Afterwards the
 * broker goes first — `force` takes its transactions — then the asset with its closes.
 *
 * Expectations.
 * - The day: `formatDay` in the interface locale the app's own rule chooses (`resolveUiLocale`, imported from
 *   `uiLocaleRule.ts`), written by this browser's Intl (`dayAsThePanelWritesIt`) and never written down here.
 * - No bare broker id: the row's text, its day taken out, read as numbers — a group separator joins the digits, so
 *   `1,234` reads `1234` — and none is the broker's id. The catalogue printed «(broker {broker_id})» until J-12.
 * - The missing sections are unmounted, so they are counted: zero, behind two barriers — the WAC chart, drawn in the
 *   same branch of the panel, and the control, where the same broker and asset drew all three.
 * - The WAC chart out of its «no data» state: the chart publishes it on its root, `data-state="drawn"` exactly when it
 *   draws (`showChart`: no «no data» overlay) and `"empty"` otherwise; a finished render (`data-chart-ready`) then says
 *   the drawing is complete.
 * - The market price line with it (Y-30): the chart publishes on the same root `data-price-line="drawn"` when it draws
 *   that line — out of «no data», some point of the line valued in the current display mode — and `"absent"` otherwise.
 *   The line is `market_price_history`, the asset's marks whatever lots are open, so the FAILED analysis keeps it; the
 *   control draws it first, from the asset's closes and the BUY and SELL marks.
 * - The banner is drawn from the same answer, in the same update, as the notice: once the notice row is on screen its
 *   presence is settled, and reading it is not a probe. With this data it should be absent; present, it is opened
 *   first, since its groups are rendered only open.
 * - The landing: the transactions page consumes `?highlight=` by pulsing the row — a transient CSS class, not read
 *   here — and opening the transaction read-only. That read-only form — the switch to edit, the footer naming the id,
 *   no Save — is the view-mode signal transactions-modals.spec.ts reads (T11). The address the button goes to is read
 *   as a navigation armed before the click: the page drops the parameter once it has read it.
 */

/** The scenario's one currency: the asset's, its cash's and — once the asset is known — the panel's. */
const UNBUILDABLE_CURRENCY = 'EUR';

/** The code the ADJUSTMENT raises: the notice row and the banner group the tests look for. */
const SHORT_ADJUSTMENT = 'SHORT_ADJUSTMENT_NOT_SUPPORTED';

/** What a J-12 test created, recorded the moment it exists: the cleanup deletes exactly this. */
interface UnbuildableOwned {
    brokerId?: number;
    assetId?: number;
}

/** The test's broker and asset holding a short of 5: BUY and SELL committed, the ADJUSTMENT still to come. */
interface ShortPosition {
    broker: {id: number; name: string};
    asset: {id: number; name: string};
    /** The days of the BUY, the SELL and the ADJUSTMENT: forty, thirty and twenty days ago. */
    days: {buy: string; sell: string; adjustment: string};
    buyId: number;
    sellId: number;
}

/** A data-quality issue as the lots analysis serialises it, reduced to what the premises read. */
interface AnalysisIssue {
    code: string;
    message_params?: Record<string, unknown> | null;
}

/** `uniqueSuffix()` without a digit: each digit becomes a capital letter (0 → A … 9 → J). Its random part is lower-case, so it stays unique. */
function digitFreeSuffix(): string {
    return uniqueSuffix().replace(/\d/g, (digit) => String.fromCharCode(65 + Number(digit)));
}

/** A broker of the test's own that allows shorting and cash overdraft, its name without a digit. */
async function createShortingBroker(page: Page, owned: UnbuildableOwned): Promise<{id: number; name: string}> {
    // Never sorts first, so a neighbour's "first card" stays a mock broker.
    const name = `Unbuildable lots ${digitFreeSuffix()}`;
    expect(name, 'control: the broker name holds no digit').not.toMatch(/\d/);
    const response = await page.request.post(`${API}/brokers`, {data: [{name, allow_cash_overdraft: true, allow_asset_shorting: true}]});
    const body = (await response.json().catch(() => null)) as {results?: Array<{name: string; success: boolean; broker_id: number | null}>} | null;
    const created = body?.results?.find((result) => result.name === name);
    if (typeof created?.broker_id === 'number') owned.brokerId = created.broker_id;
    expect(response.ok(), `create the shorting broker: HTTP ${response.status()} ${JSON.stringify(body)}`).toBe(true);
    if (!created?.success || typeof created.broker_id !== 'number') throw new Error(`The shorting broker "${name}" was not created: ${JSON.stringify(body)}`);
    return {id: created.broker_id, name};
}

/** A manual stock of the test's own, in UNBUILDABLE_CURRENCY, with `closes` stored. */
async function createPricedAsset(page: Page, owned: UnbuildableOwned, closes: ReadonlyArray<{date: string; close: number}>): Promise<{id: number; name: string}> {
    const name = `Unbuildable lots asset ${uniqueSuffix()}`;
    const response = await page.request.post(`${API}/assets`, {data: [{display_name: name, currency: UNBUILDABLE_CURRENCY, asset_type: 'STOCK'}]});
    const body = (await response.json().catch(() => null)) as {results?: Array<{asset_id?: number | null; display_name?: string; success?: boolean}>} | null;
    const created = body?.results?.find((result) => result.display_name === name);
    if (typeof created?.asset_id === 'number') owned.assetId = created.asset_id;
    expect(response.ok(), `create the asset: HTTP ${response.status()} ${JSON.stringify(body)}`).toBe(true);
    if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`The asset "${name}" was not created: ${JSON.stringify(body)}`);
    const assetId = created.asset_id;

    const stored = await page.request.post(`${API}/assets/prices`, {data: [{asset_id: assetId, prices: closes}]});
    const storedBody = (await stored.json().catch(() => null)) as {results?: Array<{asset_id: number; count: number}>} | null;
    expect(stored.ok(), `store the closes of asset ${assetId}: HTTP ${stored.status()} ${JSON.stringify(storedBody)}`).toBe(true);
    expect(storedBody?.results?.find((result) => result.asset_id === assetId)?.count, `the ${closes.length} closes of asset ${assetId} are stored`).toBe(closes.length);
    return {id: assetId, name};
}

/** The broker, the asset with its closes, and the BUY and the SELL that leave the broker short of 5. */
async function seedShortPosition(page: Page, owned: UnbuildableOwned): Promise<ShortPosition> {
    const days = {buy: daysAgoIso(40), sell: daysAgoIso(30), adjustment: daysAgoIso(20)};
    const broker = await createShortingBroker(page, owned);
    const asset = await createPricedAsset(page, owned, [
        {date: days.buy, close: 100},
        {date: days.sell, close: 110},
        {date: days.adjustment, close: 105},
        {date: daysAgoIso(5), close: 108},
    ]);
    const [buyId, sellId] = await commitCreates(
        page,
        [
            {broker_id: broker.id, asset_id: asset.id, type: 'BUY', date: days.buy, quantity: '10', cash: {code: UNBUILDABLE_CURRENCY, amount: '-1000'}},
            {broker_id: broker.id, asset_id: asset.id, type: 'SELL', date: days.sell, quantity: '-15', cash: {code: UNBUILDABLE_CURRENCY, amount: '1650'}},
        ],
        'commit BUY 10, then SELL 15: a long lot closed, a short lot of 5 opened',
    );
    test.info().annotations.push({type: 'J-12 data', description: `broker ${broker.id}, asset ${asset.id}: BUY ${buyId} on ${days.buy}, SELL ${sellId} on ${days.sell}`});
    return {broker, asset, days, buyId, sellId};
}

/** ADJUSTMENT −2 on the short, twenty days ago — the row the replay cannot take. Returns its id. */
async function commitShortAdjustment(page: Page, position: ShortPosition): Promise<number> {
    const [adjustmentId] = await commitCreates(page, [{broker_id: position.broker.id, asset_id: position.asset.id, type: 'ADJUSTMENT', date: position.days.adjustment, quantity: '-2'}], 'commit ADJUSTMENT −2 on the short position');
    test.info().annotations.push({type: 'J-12 data', description: `ADJUSTMENT ${adjustmentId} on ${position.days.adjustment}`});
    return adjustmentId;
}

/** The analysis of the test's broker and asset, read through the API: its status, its lot ids, its issues. */
async function readLotsAnalysis(page: Page, position: ShortPosition): Promise<{status: unknown; lotIds: number[]; issues: AnalysisIssue[]}> {
    const analysis = await lotsAnalysis(page, {asset_id: position.asset.id, broker_ids: [position.broker.id], requested_analyses: ['LOT_SUMMARY']});
    const lots = Array.isArray(analysis.lots) ? (analysis.lots as Array<{lot_id: number}>) : [];
    const issues = (analysis.data_quality as {issues?: unknown} | null | undefined)?.issues;
    return {status: analysis.calculation_status, lotIds: lots.map((lot) => lot.lot_id).sort((a, b) => a - b), issues: Array.isArray(issues) ? (issues as AnalysisIssue[]) : []};
}

/** The control's premise: BUY and SELL replay — a long lot and a short one, each named after the transaction that opened it. */
async function expectReplayPremise(page: Page, position: ShortPosition): Promise<void> {
    const {status, lotIds, issues} = await readLotsAnalysis(page, position);
    expect(status, `premise: a SELL past the holding opens a short on a broker that allows it — issues ${JSON.stringify(issues)}`).not.toBe('FAILED');
    expect(lotIds, 'premise: the BUY opened a lot, the SELL closed it and opened a short one (a lot id is its opening transaction id)').toEqual([position.buyId, position.sellId].sort((a, b) => a - b));
}

/** The failure's premise, J's half of the contract: FAILED, and the ADJUSTMENT the one issue flagged blocking, with its broker and its day. */
async function expectFailurePremise(page: Page, position: ShortPosition, adjustmentId: number): Promise<void> {
    const {status, issues} = await readLotsAnalysis(page, position);
    expect(status, `premise: an ADJUSTMENT on a short position fails the replay — issues ${JSON.stringify(issues)}`).toBe('FAILED');
    const blocking = issues.filter((issue) => issue.message_params?.fails_analysis === true).map((issue) => ({code: issue.code, transaction_id: issue.message_params?.transaction_id, broker_id: issue.message_params?.broker_id, transaction_date: issue.message_params?.transaction_date}));
    expect(blocking, `premise (J’s backend half of J-12): the ADJUSTMENT is the one issue flagged fails_analysis, with its broker and its day — issues ${JSON.stringify(issues)}`).toEqual([
        {code: SHORT_ADJUSTMENT, transaction_id: adjustmentId, broker_id: position.broker.id, transaction_date: position.days.adjustment},
    ]);
}

/**
 * The test's broker page on its Positions tab, the lots panel open on the test's asset and every load of the page in.
 *
 * A new document each time: the panel's answers are cached in the page, and a row written through the API marks none of
 * them stale. The title gains the asset's name once the asset cache resolves, which is when the panel's currency becomes
 * the asset's and, if it changed, the analysis is asked again (see `openLotsPanelSettled`). The page's Refresh button
 * holds every one of those loads (`pageBusy`), so its `data-busy` going false says the last answer is on screen.
 */
async function openOwnedLotsPanel(page: Page, position: ShortPosition): Promise<void> {
    await navigateTo(page, lotsPanelUrl(position.broker.id, position.asset.id));
    await expect(page.getByTestId('broker-name'), 'the page is the test’s own broker').toHaveText(position.broker.name, {timeout: 10_000});
    await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 10_000});
    await expect(page.getByTestId('lots-analysis-panel-title'), `the title gains "${position.asset.name}" once the asset cache has resolved: the panel's currency is final`).toContainText(position.asset.name, {timeout: 10_000});
    await waitForSettled(page.getByTestId('broker-refresh'), 30_000);
    await expect(page.getByTestId('lots-analysis-panel-loading'), 'the analysis has answered').toHaveCount(0);
    await expect(page.getByTestId('lots-analysis-panel-error'), 'the analysis answered without an error').toHaveCount(0);
}

/**
 * A calendar day as the lots panel writes it, `formatDay` (`$lib/utils/core/formatAxisDate`): the day read on the local
 * calendar, then `toLocaleDateString(uiLocale(), {year: 'numeric', month: 'short', day: 'numeric'})` — never written
 * down here.
 *
 * The locale is the one the app itself would choose. The rule is the app's own, `resolveUiLocale`
 * (`src/lib/stores/app/uiLocaleRule.ts`, M-18), imported as `lotIsOpenish` is: a module that imports nothing, so
 * Playwright loads it (`uiLocale.test.ts` holds it to that). It gets what the app gives it — the interface language,
 * which the root layout keeps on `<html lang>`, and the browser's primary tag, `navigator.language` — both read in one
 * `page.evaluate`. The rule runs here, in Node; the day is then written in the page, by the browser's own Intl, the one
 * that writes the panel's figures.
 */
async function dayAsThePanelWritesIt(page: Page, iso: string): Promise<string> {
    const {language, browserTag} = await page.evaluate(() => ({language: document.documentElement.lang, browserTag: navigator.language}));
    const locale = resolveUiLocale(language, browserTag);
    test.info().annotations.push({type: 'J-12 locale', description: `UI language ${language}, browser ${browserTag} → ${locale}`});
    return page.evaluate(
        ({day, uiLocale}) => {
            const [year, month, date] = day.split('-').map(Number);
            return new Date(year, month - 1, date).toLocaleDateString(uiLocale, {year: 'numeric', month: 'short', day: 'numeric'});
        },
        {day: iso, uiLocale: locale},
    );
}

/** The numbers written in `text`, as bare digits: a group separator inside one is dropped, so `1,234` reads `1234`. */
function numbersIn(text: string): string[] {
    return (text.match(/\d+(?:[.,'’\u00a0\u202f]\d{3})*/g) ?? []).map((number) => number.replace(/\D/g, ''));
}

/**
 * `code` is not a group of the banner. The banner is drawn from the same answer, in the same update, as the notice
 * (`applyMain`, `partitionLotIssues`): once the notice row is on screen whether it is there is settled, and reading it
 * is not a probe. Present, it is opened first — its groups are rendered only open — and a group of its own is the
 * barrier for the absence.
 */
async function expectBannerWithout(page: Page, code: string): Promise<void> {
    const banner = page.getByTestId('lot-data-quality-banner');
    const present = (await banner.count()) > 0;
    test.info().annotations.push({type: 'J-12 banner', description: present ? 'present: opened and read' : 'absent: no issue besides the blocking one'});
    if (present) {
        const toggle = banner.getByTestId('lot-data-quality-toggle');
        if ((await toggle.getAttribute('aria-expanded')) !== 'true') await toggle.click();
        await expect(toggle).toHaveAttribute('aria-expanded', 'true');
        await expect.poll(() => banner.locator('[data-testid^="lot-data-quality-issue-"]').count(), {message: 'barrier: the open banner lists its groups'}).toBeGreaterThan(0);
    }
    await expect(page.getByTestId(`lot-data-quality-issue-${code}`), `${code} broke the replay: it is the notice's, not a group of the banner`).toHaveCount(0);
}

/**
 * Delete what the test created: the broker first — `force` takes its transactions — then the asset with its closes.
 * The page is left first, so nothing on it reloads these rows while they go; every step is tried whatever happened to
 * the one before.
 */
async function deleteUnbuildableOwned(page: Page, owned: UnbuildableOwned): Promise<void> {
    if (owned.brokerId === undefined && owned.assetId === undefined) return;
    const failures: string[] = [];
    await page.goto('about:blank').catch((error: unknown) => failures.push(`leave the page: ${String(error)}`));
    if (owned.brokerId !== undefined) {
        try {
            await deleteOwnedBrokerAndFiles(page, owned.brokerId);
        } catch (error) {
            failures.push(String(error));
        }
    }
    if (owned.assetId !== undefined) {
        const assetId = owned.assetId;
        try {
            const response = await page.request.delete(`${API}/assets?asset_ids=${assetId}`);
            const body = (await response.json().catch(() => null)) as {results?: Array<{asset_id: number; success: boolean; message?: string | null}>} | null;
            if (!response.ok() || !body?.results?.find((result) => result.asset_id === assetId)?.success) failures.push(`asset ${assetId}: HTTP ${response.status()} ${JSON.stringify(body)}`);
        } catch (error) {
            failures.push(`asset ${assetId}: ${String(error)}`);
        }
    }
    expect(failures, 'cleanup removes the broker with its transactions, and the asset with its closes').toEqual([]);
}

test.describe('Broker detail — a FAILED lots analysis names the transaction to fix (J-12)', () => {
    // An explicit budget for the chain these tests walk: login, the seeding requests, the broker page with its lots
    // panel — twice in J12-1, the control and then the failure — and, in J12-2, the transactions page. A describe's
    // timeout runs from the start of the test, so it covers the beforeEach too. The file's parallel mode is inherited:
    // every row these tests read is their own.
    test.describe.configure({timeout: 90_000});

    let owned: UnbuildableOwned = {};

    test.beforeEach(async ({page}) => {
        owned = {};
        await login(page, TEST_USER);
    });

    // afterEach, not `finally`: a cleanup throwing from `finally` would replace the assertion error it follows.
    test.afterEach(async ({page}) => {
        await deleteUnbuildableOwned(page, owned);
    });

    test('J12-1 an ADJUSTMENT on a short fails the analysis BUY and SELL had drawn: one row with the broker’s name and the day, the average-cost lines and the market price line, no Gantt, table, comparison or banner group', async ({page}) => {
        const position = await seedShortPosition(page, owned);

        // The control, on the same broker and asset before the row that breaks them: the replay goes through and the
        // three sections a failure removes are drawn — so their absence below is the failure's doing, not the data's.
        await expectReplayPremise(page, position);
        await openOwnedLotsPanel(page, position);
        await expect(page.getByTestId('lot-gantt-echart'), 'control: the Gantt draws its lanes').toHaveAttribute('data-chart-ready', 'true', {timeout: 20_000});
        const lotsTable = page.getByTestId('unified-lots-table');
        for (const lotId of [position.buyId, position.sellId]) {
            await expect(lotsTable.locator(`tbody tr[data-row-id="${lotId}"]`), `control: lot ${lotId} has its row in the lots table`).toBeVisible({timeout: 10_000});
        }
        await expect(page.getByTestId('lot-comparison-chart'), 'control: the comparison chart is drawn').toBeVisible();
        // The market price line, which the failure below keeps (Y-30): the asset's closes mark every day from the BUY's on.
        await expect(page.getByTestId('lot-wac-price-chart'), 'control: the WAC chart draws the market price line, from the asset’s closes and the BUY and SELL marks').toHaveAttribute('data-price-line', 'drawn', {timeout: 10_000});
        await expect(page.getByTestId('lots-analysis-panel-failed'), 'control: an analysis that replays has no failure notice').toHaveCount(0);

        const adjustmentId = await commitShortAdjustment(page, position);
        await expectFailurePremise(page, position, adjustmentId);
        await openOwnedLotsPanel(page, position);

        // 1. The notice: one row, the ADJUSTMENT's, naming its broker and its day.
        const notice = page.getByTestId('lots-analysis-panel-failed');
        await expect(notice, 'a FAILED analysis shows the notice').toBeVisible();
        await expect(notice.getByTestId('lots-analysis-failed-explanation')).toBeVisible();
        const row = notice.getByTestId(`lots-analysis-failed-row-${SHORT_ADJUSTMENT}-${adjustmentId}`);
        await expect(row, 'the ADJUSTMENT has its row').toBeVisible();
        await expect(notice.locator('[data-testid^="lots-analysis-failed-row-"]'), 'every row of this asset is the test’s own: one breaks the replay, one is listed').toHaveCount(1);

        await expect(row.getByTestId('lots-analysis-failed-broker'), 'the broker, by its name').toHaveText(position.broker.name);

        const day = await dayAsThePanelWritesIt(page, position.days.adjustment);
        const [year, , dayOfMonth] = position.days.adjustment.split('-').map(Number);
        expect(day, `control: the day is written out, not left as ${position.days.adjustment}`).not.toBe(position.days.adjustment);
        expect(numbersIn(day), `control: "${day}" carries the year and the day of the month`).toEqual(expect.arrayContaining([String(year), String(dayOfMonth)]));
        const date = row.getByTestId('lots-analysis-failed-date');
        await expect(date, `the day of the ADJUSTMENT, ${position.days.adjustment}, as the panel writes a day`).toHaveText(day);

        await expect(row.getByTestId(`lots-analysis-failed-goto-${adjustmentId}`), 'a button to the ADJUSTMENT').toBeVisible();

        // Barriers: an empty message, or a key the catalogue did not resolve, would let the check below pass on nothing.
        const message = row.getByTestId('lots-analysis-failed-message');
        await expect(message, 'barrier: the message is written').toHaveText(/\S/);
        await expect(message, 'barrier: the catalogue resolved its key').not.toHaveText('dataQuality.shortAdjustmentNotSupported');
        // One read of a settled row: its broker, its day and its message are on screen above.
        const rowText = (await row.textContent()) ?? '';
        const dayText = (await date.textContent()) ?? '';
        expect(rowText, 'control: the row holds the day read above').toContain(dayText);
        expect(numbersIn(rowText.replace(dayText, ' ')), `the row writes no bare broker id (${position.broker.id}), it names the broker — «${rowText.trim()}»`).not.toContain(String(position.broker.id));

        // 2. The average-cost lines and the market price line: the WAC chart drawn with both — the price line is the asset's
        //    own series, not the lots', so a FAILED analysis keeps it (Y-30) — and none of the three lot sections the
        //    control showed.
        await expect(page.getByTestId('lot-wac-price-chart'), 'the WAC chart draws its average-cost lines, not its «no data» state').toHaveAttribute('data-state', 'drawn', {timeout: 10_000});
        await expect(page.getByTestId('lot-wac-price-chart').locator('[data-chart-ready]'), 'the WAC chart finished drawing its average-cost lines').toHaveAttribute('data-chart-ready', 'true', {timeout: 10_000});
        await expect(page.getByTestId('lot-wac-price-chart'), 'the market price line stays with a FAILED analysis: it is the asset’s series, not the lots’ (Y-30)').toHaveAttribute('data-price-line', 'drawn', {timeout: 10_000});
        for (const section of ['lot-gantt-chart', 'unified-lots-table', 'lot-comparison-chart']) {
            await expect(page.getByTestId(section), `${section} is not rendered for a FAILED analysis`).toHaveCount(0);
        }

        // 3. The banner keeps what did not break the replay: the ADJUSTMENT is not one of its groups.
        await expectBannerWithout(page, SHORT_ADJUSTMENT);
    });

    test('J12-2 the failed row’s button opens its transaction, read-only, on the transactions page', async ({page}) => {
        const position = await seedShortPosition(page, owned);
        const adjustmentId = await commitShortAdjustment(page, position);
        await expectFailurePremise(page, position, adjustmentId);
        await openOwnedLotsPanel(page, position);

        const row = page.getByTestId('lots-analysis-panel-failed').getByTestId(`lots-analysis-failed-row-${SHORT_ADJUSTMENT}-${adjustmentId}`);
        await expect(row, 'the ADJUSTMENT has its row').toBeVisible();
        const button = row.getByTestId(`lots-analysis-failed-goto-${adjustmentId}`);
        await expect(button).toBeVisible();

        // Armed before the click: a navigation is an edge, and the transactions page drops the parameter once read.
        const navigated = page.waitForURL(new RegExp(`/transactions\\?highlight=${adjustmentId}(?:&|$)`), {waitUntil: 'commit', timeout: 15_000});
        await button.click();
        await navigated;

        // 4. The transactions page reads ?highlight= and opens that transaction read-only — the view-mode signal of
        //    transactions-modals.spec.ts (T11): the switch to edit, the footer naming the row, no Save.
        await expect(page.getByTestId('tx-form-modal'), 'the transactions page opens the transaction the row named').toBeVisible({timeout: 20_000});
        await expect(page.getByTestId('tx-form-readonly-footer'), `the form is the ADJUSTMENT's, #${adjustmentId}`).toContainText(new RegExp(`#${adjustmentId}\\b`));
        await expect(page.getByTestId('tx-form-switch-edit'), 'opened read-only: the form offers the switch to edit').toBeVisible();
        await expect(page.getByTestId('tx-form-save'), '…and no Save').toBeHidden();
        await expect(page, 'on the transactions page').toHaveURL(/\/transactions(?:[?#]|$)/);
    });
});
