/**
 * The edit pencil of a transaction opened read-only from a broker's Transactions tab, on a 375 px phone (lane 66, TL-1b).
 *
 * A double-click on a row of the tab opens it in `TransactionFormModal mode="view"`. The Transactions page gives that
 * form `onSwitchToEdit` and `canEdit`, so the view offers its pencil (`tx-form-switch-edit`): a tap closes the view and
 * opens the row in edit, as «Edit» on the row does. The broker's tab (`PortfolioTransactionsTab.svelte`) gave neither, so
 * the view had no pencil — met on a phone, on a commission (a FEE linked to a BUY, folded under it).
 *
 *   (a) An owned broker, a BUY with its linked FEE and TAX; the FEE unfolded and double-clicked → the view of the FEE
 *       (its parent section names the BUY) → the pencil is visible, its whole box inside 0..375 → a tap → the view is
 *       gone and the FEE is open in edit (`tx-form-save` visible; the edit form's parent section names the BUY and its
 *       description is the FEE's own).
 *   (b) The same seed, the BUY double-clicked → the view offers the pencil.
 *   (c) Guard — the Dashboard's Transactions tab is the same component with `hideActions` and no writer: nobody edits
 *       from there, so the view of the BUY has no pencil. Its absence is read only after the view is shown and settled,
 *       with its close button on screen (rule 17).
 *   (d) The BUY double-clicked → «Open» on its FEE in the view's charges section → the same window shows the FEE (its
 *       parent section names the BUY) → the pencil, inside 0..375 → a tap → the FEE is open in edit, as in (a).
 *   (e) A parent outside the tab's list: a BUY dated 400 days ago (the tab's default period is the last 3 months,
 *       `defaultRange()` of `stores/dateRangeStore.svelte.ts`) with its FEE dated 5 days ago (a charge's date is free,
 *       `services/transactions/charges.py`). The FEE, a row of its own on the tab, double-clicked → «Open» on its parent
 *       → the view of the BUY, whose row is NOT on the tab (the premise) → the pencil → a tap → the BUY is open in edit.
 *       The bulk workspace resolves rows only from the client store: this case proves the tab adds the shown row first.
 *
 * testids relied on: broker-detail-page · broker-tab-transazioni · broker-transactions-tab · broker-transactions ·
 * tx-table · tr[data-row-id="tx-<id>"] · tx-desc-<id> · tx-charges-badge-<id>[data-expanded] · tx-form-modal ·
 * tx-form-modal-root[data-busy] · tx-form-parent[data-parent-id] · tx-form-description · tx-form-switch-edit ·
 * tx-form-save · tx-form-close · tx-bulk-modal-root · dashboard-page · dashboard-transactions-tab · tx-form-charges ·
 * tx-form-charge-open-saved-<id> · tx-form-parent-open.
 * Never the translated words.
 *
 * Every test works on an account of its own (`../fixtures/linked-charges.ts`): a disposable user, a broker it owns, a
 * funding DEPOSIT, a BUY and its FEE and TAX ((e): an older DEPOSIT, the old BUY and its recent FEE, no TAX). Nothing is
 * saved from the edit form. The afterEach deletes what of its
 * rows is left, then the account.
 */
import {expect, test, type APIRequestContext, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {cleanupOwnedAccount, emptyOwnedAccount, jsonFrom, type OwnedAccount} from '../fixtures/owned-pair';
import {COMMIT_PATH, openFundedAccount, readByIds, seedLinkedBuy, type CommitBody} from '../fixtures/linked-charges';
import {daysAgoIso} from '../fixtures/dates';

test.setTimeout(90_000);

const PHONE = {width: 375, height: 812};

const brokerTable = (page: Page) => page.getByTestId('broker-transactions');
const brokerRow = (page: Page, id: number) => brokerTable(page).locator(`tr[data-row-id="tx-${id}"]`);

/** The broker's page on the Transactions tab; ends with the row `anchorId` on screen. */
async function openBrokerTransactionsTab(page: Page, brokerId: number, anchorId: number): Promise<void> {
    await navigateTo(page, `/brokers/${brokerId}`);
    await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 20_000});
    await page.getByTestId('broker-tab-transazioni').click();
    await expect(page.getByTestId('broker-transactions-tab')).toBeVisible({timeout: 10_000});
    await expect(brokerTable(page).getByTestId('tx-table')).toBeVisible({timeout: 20_000});
    await expect(brokerRow(page, anchorId), `the row #${anchorId} is on the tab`).toBeVisible({timeout: 10_000});
}

/** Unfold the BUY's charges (only if folded); ends with the FEE row on screen. */
async function unfoldCharges(page: Page, buyId: number, feeId: number): Promise<void> {
    const badge = brokerRow(page, buyId).getByTestId(`tx-charges-badge-${buyId}`);
    await expect(badge, 'the BUY carries its charges badge').toBeVisible({timeout: 10_000});
    if ((await badge.getAttribute('data-expanded')) !== 'true') await badge.click();
    await expect(badge).toHaveAttribute('data-expanded', 'true');
    await expect(brokerRow(page, feeId), 'the open badge shows the FEE under the BUY').toBeVisible({timeout: 5_000});
}

/** Double-click a row open; ends on the form in view mode, loaded (nothing to save, the root settled). */
async function openInView(page: Page, row: Locator, txId: number): Promise<void> {
    await row.getByTestId(`tx-desc-${txId}`).dblclick();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 8_000});
    await waitForSettled(page.getByTestId('tx-form-modal-root'), 15_000);
    await expect(page.getByTestId('tx-form-close'), 'the view is on screen').toBeVisible();
    await expect(page.getByTestId('tx-form-save'), 'view mode: nothing to save').toBeHidden();
}

/** The view-mode pencil is on screen, its whole box inside the phone's viewport. */
async function expectPencilReachable(page: Page, what: string): Promise<Locator> {
    const pencil = page.getByTestId('tx-form-switch-edit');
    await expect(pencil, `the view of ${what}, opened from the broker's Transactions tab, offers no edit pencil`).toBeVisible({timeout: 5_000});
    const box = await pencil.boundingBox();
    expect(box, 'the pencil has a box').not.toBeNull();
    const right = box!.x + box!.width;
    expect.soft(box!.x, `the pencil starts inside the viewport (left ${box!.x})`).toBeGreaterThanOrEqual(0);
    expect.soft(right, `the pencil ends inside the ${PHONE.width} px viewport (right edge ${right})`).toBeLessThanOrEqual(PHONE.width);
    return pencil;
}

/**
 * After the pencil's tap: the view closed and the row is open in edit, alone (the bulk workspace on that one row opens its
 * form directly). `parentId` given: the edit form is a charge of that parent.
 */
async function expectOpenInEdit(page: Page, description: string, parentId?: number): Promise<void> {
    await expect(page.getByTestId('tx-form-switch-edit'), 'edit mode: the pencil is gone').toHaveCount(0, {timeout: 8_000});
    await expect(page.getByTestId('tx-form-save'), 'the row is open in edit: Save is offered').toBeVisible({timeout: 10_000});
    await expect(page.getByTestId('tx-bulk-modal-root'), 'the edit runs in the workspace, as «Edit» on the row').toBeVisible();
    await expect(page.getByTestId('tx-form-modal'), 'one form on screen: the view has closed').toHaveCount(1, {timeout: 8_000});
    const form = page.getByTestId('tx-form-modal');
    if (parentId !== undefined) {
        await expect(form.getByTestId('tx-form-parent'), 'the edit form is a charge of the BUY').toHaveAttribute('data-parent-id', String(parentId), {timeout: 5_000});
    }
    await expect(form.getByTestId('tx-form-description'), 'the edit form is the row the view showed').toHaveValue(description);
}

/** A BUY dated before the tab's period, with a FEE linked to it dated inside the period (the BUY funded by its own DEPOSIT). */
async function seedOldParentRecentFee(page: Page, request: APIRequestContext, owned: OwnedAccount, committed: number[], tag: string): Promise<{brokerId: number; marker: string; buyId: number; feeId: number}> {
    const {broker, assetId, marker} = await openFundedAccount(page, request, owned, committed, tag, 'TxVE');
    // 400 days ago: well before the default period's start (3 months), so the BUY is not in the list the tab loads.
    const [depositDate, buyDate, feeDate] = [daysAgoIso(410), daysAgoIso(400), daysAgoIso(5)];
    const body = await jsonFrom<CommitBody>(
        await page.request.post(COMMIT_PATH, {
            data: {
                creates: [
                    {broker_id: broker.id, type: 'DEPOSIT', date: depositDate, cash: {code: 'USD', amount: '1000'}, description: `Old deposit ${marker}`},
                    {ref: 'p', broker_id: broker.id, asset_id: assetId, type: 'BUY', date: buyDate, quantity: '10', cash: {code: 'USD', amount: '-100'}, description: `Buy ${marker}`},
                    {broker_id: broker.id, asset_id: assetId, type: 'FEE', date: feeDate, quantity: '0', cash: {code: 'USD', amount: '-5'}, description: `Fee ${marker}`, parent_ref: 'p'},
                ],
            },
        }),
        'commit the old BUY with its recent FEE',
    );
    expect(body.committed, `rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    const ids = [0, 1, 2].map((index) => {
        const id = body.results?.find((item) => item.operation === 'create' && item.index === index)?.ids?.[0];
        if (typeof id !== 'number') throw new Error(`no id for create #${index}: ${JSON.stringify(body.results)}`);
        return id;
    });
    committed.push(...ids);
    const [, buyId, feeId] = ids;

    // The premise, read back rather than inferred: the FEE is linked to the BUY and keeps its own, recent date.
    const back = await readByIds(page, [buyId, feeId]);
    expect(back.get(feeId)?.parent_transaction_id ?? null, 'premise: the FEE is linked to the BUY').toBe(buyId);
    expect([back.get(buyId)?.date, back.get(feeId)?.date], 'premise: the BUY is old, its FEE recent').toEqual([buyDate, feeDate]);
    return {brokerId: broker.id, marker, buyId, feeId};
}

test.describe('Broker page, Transactions tab on a 375 px phone — the view of a row offers the edit pencil (66 TL-1b)', () => {
    let owned = emptyOwnedAccount();
    let committedIds: number[] = [];

    test.beforeEach(async ({page}) => {
        owned = emptyOwnedAccount();
        committedIds = [];
        // Before anything renders: the runner's projects are 1280 px (desktop) and 430 px (mobile), neither is 375.
        await page.setViewportSize(PHONE);
    });

    // afterEach, not `finally`: it runs after a timeout too. Only the rows still there are deleted, together, then the
    // account and its brokers.
    test.afterEach(async ({page, request}) => {
        try {
            if (owned.user && committedIds.length > 0) {
                const left = [...(await readByIds(page, committedIds)).keys()];
                if (left.length > 0) await page.request.post(COMMIT_PATH, {data: {deletes: left}});
            }
        } finally {
            await cleanupOwnedAccount(page, request, owned);
        }
    });

    test('(a) the FEE linked to a BUY: the view offers the pencil inside the screen; a tap opens the FEE in edit', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'tvea', 'TxVE');
        expect(await page.evaluate(() => window.innerWidth), 'premise: the page is 375 px wide').toBe(PHONE.width);
        await openBrokerTransactionsTab(page, s.broker.id, s.buyId);
        await unfoldCharges(page, s.buyId, s.feeId);

        await openInView(page, brokerRow(page, s.feeId), s.feeId);
        // Presence: the view shows the FEE — a charge whose parent section names the BUY.
        await expect(page.getByTestId('tx-form-parent'), 'the view shows a charge of the BUY').toHaveAttribute('data-parent-id', String(s.buyId), {timeout: 5_000});
        await expect(page.getByTestId('tx-form-description')).toHaveValue(`Fee ${s.marker}`);

        const pencil = await expectPencilReachable(page, 'a FEE');
        await pencil.click();

        // The view closed and the same FEE (not its TAX sibling) is open in edit.
        await expectOpenInEdit(page, `Fee ${s.marker}`, s.buyId);
    });

    test('(b) the BUY with its charges: the view offers the pencil', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'tveb', 'TxVE');
        await openBrokerTransactionsTab(page, s.broker.id, s.buyId);

        await openInView(page, brokerRow(page, s.buyId), s.buyId);
        await expect(page.getByTestId('tx-form-description'), 'the view shows the BUY').toHaveValue(`Buy ${s.marker}`);
        await expect(page.getByTestId('tx-form-switch-edit'), "the view of a BUY, opened from the broker's Transactions tab, offers no edit pencil").toBeVisible({timeout: 5_000});
    });

    // Guard: green today too (no pencil anywhere in the tab yet). It keeps the fix from giving the pencil to a tab where
    // nobody edits.
    test('(c) guard — the Dashboard Transactions tab (same component, hideActions): the view has no pencil', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'tvec', 'TxVE');
        await navigateTo(page, '/dashboard?tab=transazioni');
        await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 20_000});
        const tab = page.getByTestId('dashboard-transactions-tab');
        const row = tab.locator(`tr[data-row-id="tx-${s.buyId}"]`);
        await expect(row, `the BUY #${s.buyId} is on the Dashboard tab`).toBeVisible({timeout: 30_000});

        await openInView(page, row, s.buyId);
        // Presence barrier before the absence: the view shows this BUY and its close button (sibling control) is on screen.
        await expect(page.getByTestId('tx-form-description'), 'the view shows the BUY').toHaveValue(`Buy ${s.marker}`);
        await expect(page.getByTestId('tx-form-close')).toBeVisible();
        await expect(page.getByTestId('tx-form-switch-edit'), 'the Dashboard view offers no pencil: nobody edits from there').toHaveCount(0);
    });

    test('(d) the view of the BUY, «Open» on its FEE: the same window shows the FEE; the pencil opens the FEE in edit', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'tved', 'TxVE');
        await openBrokerTransactionsTab(page, s.broker.id, s.buyId);

        await openInView(page, brokerRow(page, s.buyId), s.buyId);
        await expect(page.getByTestId('tx-form-description'), 'the view shows the BUY').toHaveValue(`Buy ${s.marker}`);
        const openFee = page.getByTestId('tx-form-charges').getByTestId(`tx-form-charge-open-saved-${s.feeId}`);
        await expect(openFee, "the BUY's charges section offers «Open» on its FEE").toBeVisible({timeout: 10_000});
        await openFee.click();

        // The same window now shows the FEE: a charge whose parent section names the BUY.
        await expect(page.getByTestId('tx-form-parent'), 'the view now shows a charge of the BUY').toHaveAttribute('data-parent-id', String(s.buyId), {timeout: 8_000});
        await expect(page.getByTestId('tx-form-description'), 'the view shows the FEE, not its TAX sibling').toHaveValue(`Fee ${s.marker}`);
        await expect(page.getByTestId('tx-form-modal'), '«Open» moves inside the same window').toHaveCount(1);

        const pencil = await expectPencilReachable(page, 'a FEE reached with «Open»');
        await pencil.click();
        await expectOpenInEdit(page, `Fee ${s.marker}`, s.buyId);
    });

    test("(e) a parent outside the tab's list, reached with «Open» from its FEE: the pencil opens the BUY in edit", async ({page, request}) => {
        const s = await seedOldParentRecentFee(page, request, owned, committedIds, 'tvee');
        await openBrokerTransactionsTab(page, s.brokerId, s.feeId);
        // The list is loaded (the FEE is on screen, a row of its own): its parent, before the period, is not in it.
        await expect(brokerRow(page, s.buyId), 'premise: the old BUY is not in the list the tab loaded').toHaveCount(0);

        await openInView(page, brokerRow(page, s.feeId), s.feeId);
        await expect(page.getByTestId('tx-form-description'), 'the view shows the FEE').toHaveValue(`Fee ${s.marker}`);
        const parent = page.getByTestId('tx-form-parent');
        await expect(parent, 'the view shows a charge of the BUY').toHaveAttribute('data-parent-id', String(s.buyId), {timeout: 5_000});
        await parent.getByTestId('tx-form-parent-open').click();

        // The same window now shows the BUY, fetched by id.
        await expect(page.getByTestId('tx-form-description'), 'the view now shows the BUY').toHaveValue(`Buy ${s.marker}`, {timeout: 8_000});
        await expect(page.getByTestId('tx-form-modal'), '«Open» moves inside the same window').toHaveCount(1);
        await expect(brokerRow(page, s.buyId), 'premise: the BUY shown is still not a row of the tab').toHaveCount(0);

        const pencil = await expectPencilReachable(page, 'a BUY outside the list, reached with «Open»');
        await pencil.click();
        await expectOpenInEdit(page, `Buy ${s.marker}`);
    });
});
