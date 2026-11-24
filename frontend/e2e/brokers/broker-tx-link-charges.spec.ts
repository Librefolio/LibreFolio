/**
 * «Link the charges» from the broker page's Transactions tab, as on the Transactions page (lane 66, lot TL-5).
 *
 * The Transactions page offers it in its selection bar (`toolbar-action-link-charges`, F6): the same rules
 * (`linkSelection` in `chargeLinkRules.ts`: hidden / off with a reason / ok), the same panel
 * (`tx-charges-modal-content`, `data-mode="link"`), the same save (`linkCommit`, event `tx.charges.linked`). Until TL-5
 * the tab's bar held only Edit, Clone and Delete.
 *
 *   (a) A saved BUY and a FEE linked to nothing, same broker, asset and date, ticked on the tab → «Link» is on → the
 *       panel in link mode → confirm → the event `tx.charges.linked` names the BUY and the FEE; the tab reloads (the
 *       selection bar goes, the page settles, the BUY carries the charges badge with the FEE folded under it); and on
 *       the server the FEE points at the BUY, which counts one charge.
 *   (b) A BUY with an asset and a FEE without one, ticked together → «Link» is there but off (`aria-disabled`, not
 *       the native `disabled`), with the code `data-disabled-reason="noAsset"`.
 *
 * testids relied on: broker-detail-page · broker-tab-transazioni · broker-transactions-tab · broker-transactions ·
 * tx-table · tr[data-row-id="tx-<id>"] · dt-row-checkbox-tx-<id> · selection-toolbar[data-selected-count] ·
 * toolbar-action-delete · toolbar-action-link-charges[aria-disabled][data-disabled-reason] ·
 * tx-charges-modal-content[data-mode] · tx-charges-modal-confirm · broker-detail-page[data-busy] ·
 * broker-refresh[data-busy] · tx-charges-badge-<id>[data-expanded] · tx-charge-arrow-<id>.
 * The verdict is the server, read back by id, and the event's payload; never the translated words.
 *
 * Every test works on an account of its own (`../fixtures/linked-charges.ts`): a disposable user, a broker it owns, a
 * funding DEPOSIT and its BUY and FEE. The afterEach deletes what of its rows is left, then the account.
 */
import {expect, test, type APIRequestContext, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {eventSeq, waitForEvent, waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {commitCreates, cleanupOwnedAccount, emptyOwnedAccount, type OwnedAccount} from '../fixtures/owned-pair';
import {COMMIT_PATH, openFundedAccount, readByIds, seedBuyAndFreeFee, type FundedAccount} from '../fixtures/linked-charges';

test.setTimeout(90_000);

const txTable = (page: Page) => page.getByTestId('broker-transactions');
const tableRow = (page: Page, id: number) => txTable(page).locator(`tr[data-row-id="tx-${id}"]`);

/** The broker's page on the Transactions tab; ends with every row of `ids` on screen. */
async function openTransactionsTab(page: Page, brokerId: number, ids: number[]): Promise<void> {
    await navigateTo(page, `/brokers/${brokerId}`);
    await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 20_000});
    await page.getByTestId('broker-tab-transazioni').click();
    await expect(page.getByTestId('broker-transactions-tab')).toBeVisible({timeout: 10_000});
    await expect(txTable(page).getByTestId('tx-table')).toBeVisible({timeout: 20_000});
    for (const id of ids) await expect(tableRow(page, id), `#${id} is on the tab`).toBeVisible({timeout: 10_000});
}

/** Tick a row of the tab's table; ends checked. */
async function ensureChecked(page: Page, id: number): Promise<void> {
    const checkbox = txTable(page).getByTestId(`dt-row-checkbox-tx-${id}`);
    await expect(checkbox).toBeVisible({timeout: 8_000});
    if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked');
}

/**
 * Tick these rows; ends on the selection bar counting them and offering «Delete». That barrier comes first: only once
 * the bar is there and holds the rows does the presence (or absence) of «Link» mean something.
 */
async function selectRows(page: Page, ids: number[]): Promise<Locator> {
    for (const id of ids) await ensureChecked(page, id);
    const bar = txTable(page).getByTestId('selection-toolbar');
    await expect(bar).toHaveAttribute('data-selected-count', String(ids.length), {timeout: 5_000});
    await expect(bar.getByTestId('toolbar-action-delete')).toBeVisible({timeout: 5_000});
    return bar;
}

/**
 * After «Link»: the tab reloaded on its own. The selection bar is gone; the page has settled — the root
 * (`broker-detail-page`, its refresh included) and `broker-refresh`, which publishes every `pageBusy` load of the page,
 * the tab's transactions among them (the tab's container publishes no `data-busy` of its own) — and the BUY row carries
 * the closed charges badge with the FEE folded away; opened, the badge shows the FEE row with its `↳` arrow.
 */
async function expectTabShowsLink(page: Page, buyId: number, feeId: number): Promise<void> {
    await expect(txTable(page).getByTestId('selection-toolbar'), 'the selection is cleared after the link').toBeHidden({timeout: 8_000});
    await waitForSettled(page.getByTestId('broker-detail-page'), 20_000);
    await waitForSettled(page.getByTestId('broker-refresh'), 20_000);
    const badge = tableRow(page, buyId).getByTestId(`tx-charges-badge-${buyId}`);
    await expect(badge, 'the tab did not reload: the BUY shows no charges badge').toBeVisible({timeout: 10_000});
    await expect(badge).toHaveAttribute('data-expanded', 'false');
    // The badge is the presence barrier: only now does the FEE's absence mean «folded», not «not drawn yet».
    await expect(tableRow(page, feeId), 'the FEE folds under its BUY').toHaveCount(0);
    await badge.click();
    await expect(badge).toHaveAttribute('data-expanded', 'true');
    await expect(tableRow(page, feeId), 'the open badge shows the FEE under the BUY').toBeVisible({timeout: 5_000});
    await expect(tableRow(page, feeId).getByTestId(`tx-charge-arrow-${feeId}`)).toBeVisible();
}

/** A funded account with a BUY (with the asset) and a FEE without an asset, same broker and date, not linked. */
async function seedBuyAndAssetlessFee(page: Page, request: APIRequestContext, owned: OwnedAccount, committed: number[], tag: string): Promise<FundedAccount & {buyId: number; feeId: number}> {
    const funded = await openFundedAccount(page, request, owned, committed, tag, 'ChgK');
    const {broker, assetId, marker} = funded;
    const date = daysAgoIso(5);
    const [buyId, feeId] = await commitCreates(
        page,
        [
            {broker_id: broker.id, asset_id: assetId, type: 'BUY', date, quantity: '10', cash: {code: 'USD', amount: '-100'}, description: `Buy ${marker}`},
            {broker_id: broker.id, type: 'FEE', date, quantity: '0', cash: {code: 'USD', amount: '-5'}, description: `Fee ${marker}`},
        ],
        'commit a BUY and a FEE without an asset',
    );
    committed.push(buyId, feeId);

    // The premise, read back rather than inferred: the FEE has no asset and no parent, the BUY has the asset.
    const back = await readByIds(page, [buyId, feeId]);
    expect(back.get(buyId)?.asset_id ?? null, 'premise: the BUY has the asset').toBe(assetId);
    expect(back.get(feeId)?.asset_id ?? null, 'premise: the FEE has no asset').toBeNull();
    expect(back.get(feeId)?.parent_transaction_id ?? null, 'premise: the FEE is linked to nothing').toBeNull();
    return {...funded, buyId, feeId};
}

test.describe('Broker page, Transactions tab — «Link the charges» from the selection bar, as on the Transactions page', () => {
    let owned = emptyOwnedAccount();
    let committedIds: number[] = [];

    test.beforeEach(() => {
        owned = emptyOwnedAccount();
        committedIds = [];
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

    test('(a) a BUY and a free FEE ticked on the tab: «Link» → the panel → confirm; the FEE points at the BUY', async ({page, request}) => {
        const s = await seedBuyAndFreeFee(page, request, owned, committedIds, 'chgk1', 'ChgK');
        await openTransactionsTab(page, s.broker.id, [s.buyId, s.feeId]);

        const bar = await selectRows(page, [s.buyId, s.feeId]);
        const link = bar.getByTestId('toolbar-action-link-charges');
        await expect(link, 'the tab offers no «Link» for a BUY and a free FEE of the same broker, asset and date').toBeVisible({timeout: 5_000});
        await expect(link).not.toHaveAttribute('aria-disabled', 'true');
        await expect(link).not.toHaveAttribute('data-disabled-reason', /.+/);
        await link.click();

        const content = page.getByTestId('tx-charges-modal-content');
        await expect(content).toBeVisible({timeout: 8_000});
        await expect(content).toHaveAttribute('data-mode', 'link');
        const confirm = content.getByTestId('tx-charges-modal-confirm');
        await expect(confirm).toBeEnabled({timeout: 5_000});
        const since = await eventSeq(page);
        await confirm.click();

        const event = await waitForEvent(page, 'tx.charges.linked', {since, timeout: 15_000});
        expect(event.detail, 'the event names the BUY and the FEE').toEqual({parent: s.buyId, charges: [s.feeId]});
        await expect(content).toBeHidden({timeout: 8_000});

        // The tab itself updated, not only the server: the selection is cleared, and once the page has settled the BUY
        // folds its FEE under it, as the Transactions page shows a linked charge (F5).
        await expectTabShowsLink(page, s.buyId, s.feeId);

        const after = await readByIds(page, [s.buyId, s.feeId]);
        const dump = `server ${JSON.stringify([...after.values()])}`;
        expect(after.get(s.feeId)?.parent_transaction_id ?? null, `the FEE points at the BUY: ${dump}`).toBe(s.buyId);
        expect(after.get(s.buyId)?.charges_count, `the BUY counts one charge: ${dump}`).toBe(1);
    });

    test('(b) a BUY with an asset and a FEE without one ticked on the tab: «Link» is there, off, with the reason noAsset', async ({page, request}) => {
        const s = await seedBuyAndAssetlessFee(page, request, owned, committedIds, 'chgk2');
        await openTransactionsTab(page, s.broker.id, [s.buyId, s.feeId]);

        const bar = await selectRows(page, [s.buyId, s.feeId]);
        const link = bar.getByTestId('toolbar-action-link-charges');
        await expect(link, 'the tab offers no «Link» for a BUY and a FEE: it must be there, off').toBeVisible({timeout: 5_000});
        // Off, but reachable (66 F7): `aria-disabled`, not the native `disabled`, so the reason opens on a tap.
        await expect(link).toHaveAttribute('aria-disabled', 'true');
        await expect(link).not.toHaveAttribute('disabled');
        await expect(link).toHaveAttribute('data-disabled-reason', 'noAsset');
    });
});
