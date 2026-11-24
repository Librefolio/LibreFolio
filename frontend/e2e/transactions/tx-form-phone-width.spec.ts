/**
 * The transaction form on a phone fits the screen sideways (testlist 3.9).
 *
 * At 375 px the form scrolled sideways instead of shrinking, in view mode and in edit mode, and the edit pencil
 * of view mode was hard to reach. The «Required» block is a `<fieldset>` (`tx-form-required`), whose UA default
 * `min-inline-size: min-content` takes the full width of the one-line asset label («IWDA · iShares Core MSCI World
 * UCITS ETF USD (Acc)»): the fieldset outgrows the body and `tx-form-body` scrolls sideways. A short-named asset
 * (AAPL) does not show it, so the rows here are of the seeded IWDA, whose display name is the long one.
 *
 * Measured, not looked at: `scrollWidth` against `clientWidth` of `tx-form-body` and `tx-form-modal-root`, and the
 * pencil's box against the viewport. Each test owns a disposable account and brokers of its own; `afterEach`
 * deletes them, rows included.
 */
import {randomUUID} from 'crypto';
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {createOwnedBroker} from '../fixtures/onboarding-accounts';
import {cleanupOwnedAccount, commitCreates, emptyOwnedAccount, jsonFrom, openOwnedAccount, readTransactions, seededAssetId} from '../fixtures/owned-pair';

const API = '/api/v1';
const PHONE = {width: 375, height: 812};
/** The seeded asset with the long display name (populate_mock_data.py, the USD share class of iShares Core MSCI World). */
const LONG_TICKER = 'IWDA';

/** The seeded IWDA: its id and the display name the asset field shows. */
async function longNamedAsset(page: Page): Promise<{id: number; name: string}> {
    const id = await seededAssetId(page, LONG_TICKER);
    const [asset] = await jsonFrom<Array<{id: number; display_name: string}>>(await page.request.get(`${API}/assets/query?ticker=${LONG_TICKER}`), `read the ${LONG_TICKER} display name`);
    expect(asset.id, `premise: one ${LONG_TICKER}`).toBe(id);
    expect(asset.display_name.length, `premise: ${LONG_TICKER} has a long display name ("${asset.display_name}")`).toBeGreaterThan(30);
    return {id, name: asset.display_name};
}

/** The table narrowed to one transaction (`id_min`/`id_max`), ending with that row on screen. */
async function goToTransactionById(page: Page, txId: number): Promise<Locator> {
    await navigateTo(page, `/transactions?id_min=${txId}&id_max=${txId}`);
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    const row = page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="tx-${txId}"]`);
    await expect(row, `transaction ${txId} must be on screen`).toBeVisible({timeout: 10_000});
    return row;
}

/**
 * The form has loaded and shows the long asset label: the presence barrier before a measure, so a «fits» can never
 * come from a form whose asset field is still empty.
 */
async function formShowsLongAsset(page: Page, assetName: string): Promise<void> {
    const root = page.getByTestId('tx-form-modal-root');
    await waitForSettled(root, 15_000);
    await expect(root.getByTestId('tx-form-asset-trigger'), 'the asset field shows the long IWDA label').toContainText(assetName, {timeout: 10_000});
}

type Widths = {viewport: number; body: {scroll: number; client: number}; root: {scroll: number; client: number}; required: number[]; trigger: number};

/** The sideways sizes of the form: the body and the modal root (scroll vs client), each «Required» fieldset and the asset trigger. */
async function measureForm(page: Page): Promise<Widths> {
    return page.evaluate(() => {
        const byId = (id: string) => document.querySelector<HTMLElement>(`[data-testid="${id}"]`);
        const box = (el: HTMLElement | null) => ({scroll: el?.scrollWidth ?? -1, client: el?.clientWidth ?? -1});
        return {
            viewport: window.innerWidth,
            body: box(byId('tx-form-body')),
            root: box(byId('tx-form-modal-root')),
            required: [...document.querySelectorAll<HTMLElement>('[data-testid="tx-form-required"]')].map((el) => Math.round(el.getBoundingClientRect().width)),
            trigger: Math.round(byId('tx-form-asset-trigger')?.getBoundingClientRect().width ?? -1),
        };
    });
}

/** Soft: both modes are measured in one run, so the report names every overflow, not only the first. */
function expectNoSidewaysScroll(w: Widths, mode: string): void {
    const sizes = `viewport ${w.viewport}, tx-form-required ${w.required.join('/')} px, asset trigger ${w.trigger} px`;
    expect.soft(w.body.scroll, `${mode}: tx-form-body scrolls sideways — scrollWidth ${w.body.scroll} > clientWidth ${w.body.client} (${sizes})`).toBeLessThanOrEqual(w.body.client + 1);
    expect.soft(w.root.scroll, `${mode}: tx-form-modal-root scrolls sideways — scrollWidth ${w.root.scroll} > clientWidth ${w.root.client} (${sizes})`).toBeLessThanOrEqual(w.root.client + 1);
}

/** The view-mode pencil is on screen, its whole box inside the viewport. */
async function expectPencilReachable(page: Page): Promise<void> {
    const pencil = page.getByTestId('tx-form-switch-edit');
    await expect(pencil, 'view mode offers the edit pencil').toBeVisible({timeout: 5_000});
    const box = await pencil.boundingBox();
    expect(box, 'the pencil has a box').not.toBeNull();
    const right = box!.x + box!.width;
    expect.soft(box!.x, `the pencil starts inside the viewport (left ${box!.x})`).toBeGreaterThanOrEqual(0);
    expect.soft(right, `the pencil ends inside the ${PHONE.width} px viewport (right edge ${right})`).toBeLessThanOrEqual(PHONE.width);
}

/** Double-click the row open in view mode, measure; switch to edit with the pencil, measure again. */
async function measureViewThenEdit(page: Page, txId: number, assetName: string, label: string, premise: () => Promise<void>): Promise<void> {
    const row = await goToTransactionById(page, txId);
    await row.getByTestId(`tx-desc-${txId}`).dblclick();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
    await expect(page.getByTestId('tx-form-save'), 'view mode: nothing to save').toBeHidden();
    await premise();
    await formShowsLongAsset(page, assetName);

    expectNoSidewaysScroll(await measureForm(page), `${label}, view mode`);
    await expectPencilReachable(page);

    await page.getByTestId('tx-form-switch-edit').click();
    await expect(page.getByTestId('tx-form-switch-edit'), 'edit mode: the pencil is gone').toBeHidden({timeout: 5_000});
    await expect(page.getByTestId('tx-form-save'), 'edit mode offers Save').toBeVisible({timeout: 5_000});
    await premise();
    await formShowsLongAsset(page, assetName);

    expectNoSidewaysScroll(await measureForm(page), `${label}, edit mode`);
}

test.describe('Transaction form on a 375 px phone (testlist 3.9)', () => {
    let owned = emptyOwnedAccount();

    test.beforeEach(async ({page}) => {
        owned = emptyOwnedAccount();
        // Before anything renders: the runner's projects are 1280 px (desktop) and 430 px (mobile), neither is 375.
        await page.setViewportSize(PHONE);
    });

    test.afterEach(async ({page, request}) => {
        await cleanupOwnedAccount(page, request, owned);
    });

    test('a BUY of IWDA: no sideways scroll in view and edit mode, the pencil inside the screen', async ({page, request}, testInfo) => {
        test.setTimeout(90_000);
        await openOwnedAccount(page, request, owned, `phw_${testInfo.project.name}`);
        expect(await page.evaluate(() => window.innerWidth), 'premise: the page is 375 px wide').toBe(PHONE.width);
        const broker = await createOwnedBroker(page, 'phw', owned.brokerIds);
        const asset = await longNamedAsset(page);
        const marker = `Phone width ${uniqueSuffix()}`;
        await commitCreates(page, [{broker_id: broker.id, type: 'DEPOSIT', date: daysAgoIso(10), cash: {code: 'USD', amount: '1000'}, description: `Deposit ${marker}`}], 'fund the owned broker');
        const [buyId] = await commitCreates(page, [{broker_id: broker.id, asset_id: asset.id, type: 'BUY', date: daysAgoIso(9), quantity: '2', cash: {code: 'USD', amount: '-200'}, description: `Buy ${marker}`}], 'a BUY of IWDA');

        await measureViewThenEdit(page, buyId, asset.name, 'BUY', async () => {
            await expect(page.getByTestId('tx-form-required'), 'the single layout shows its «Required» fieldset').toBeVisible({timeout: 5_000});
        });
    });

    test('an asset TRANSFER pair of IWDA: no sideways scroll in view and edit mode, the pencil inside the screen', async ({page, request}, testInfo) => {
        test.setTimeout(90_000);
        await openOwnedAccount(page, request, owned, `phwp_${testInfo.project.name}`);
        expect(await page.evaluate(() => window.innerWidth), 'premise: the page is 375 px wide').toBe(PHONE.width);
        const giver = await createOwnedBroker(page, 'phwp-from', owned.brokerIds);
        const receiver = await createOwnedBroker(page, 'phwp-to', owned.brokerIds);
        const asset = await longNamedAsset(page);
        const marker = `Phone width pair ${uniqueSuffix()}`;
        await commitCreates(
            page,
            [
                {broker_id: giver.id, type: 'DEPOSIT', date: daysAgoIso(10), cash: {code: 'USD', amount: '1000'}, description: `Deposit ${marker}`},
                {broker_id: giver.id, asset_id: asset.id, type: 'BUY', date: daysAgoIso(9), quantity: '2', cash: {code: 'USD', amount: '-200'}, description: `Buy ${marker}`},
            ],
            'fund the giver with IWDA',
        );
        const linkUuid = randomUUID();
        const date = daysAgoIso(5);
        const [fromId, toId] = await commitCreates(
            page,
            [
                {broker_id: giver.id, asset_id: asset.id, type: 'TRANSFER', date, quantity: '-1', link_uuid: linkUuid, description: marker},
                {broker_id: receiver.id, asset_id: asset.id, type: 'TRANSFER', date, quantity: '1', link_uuid: linkUuid, description: marker, cost_basis_mode: 'auto'},
            ],
            'an IWDA TRANSFER pair between the two owned brokers',
        );
        const halves = new Map((await readTransactions(page, {broker_id: giver.id})).map((tx) => [tx.id, tx.related_transaction_id ?? null] as const));
        expect(halves.get(fromId), 'premise: the giver half is linked to the receiver half').toBe(toId);

        await measureViewThenEdit(page, fromId, asset.name, 'TRANSFER pair', async () => {
            await expect(page.getByTestId('tx-form-dual-split'), 'the pair layout is on screen').toBeVisible({timeout: 5_000});
            await expect(page.getByTestId('tx-form-required'), 'the pair layout shows its «Required» fieldset').toBeVisible({timeout: 5_000});
        });
    });
});
