/**
 * tx-event-reconciliation.spec.ts — N68 (lot X5-3): re-link the transactions that lost their asset event.
 *
 * Changing an asset's currency deletes its prices and every non-SPLIT event, and disconnects the transactions that were
 * linked to a deleted event (`asset_event_id` NULL, the transactions stay). The Transactions page now has a button,
 * `tx-reconcile-events-button`, that opens the reconciliation modal (`event-reconciliation-modal`): one row per
 * transaction that could take an event and has none, with the verdict the server found for it —
 * `data-status="unique"` (exactly one event of the corresponding type that SAME day), `"none"` (no event that day) or
 * `"several"` — and `data-candidate-count`. The user links the unique rows, one by one (`event-reconciliation-link-{id}`)
 * or all at once (`event-reconciliation-link-all`, ONE `POST /transactions/commit`); nothing is linked on its own and a
 * `several` row is never guessed. Backend contract: `GET /transactions/event-reconciliation`; the link is the existing
 * `commit` with `updates: [{id, asset_event_id}]`.
 *
 * Contract (what the tests below pin).
 *   - the modal lists the account's unlinked transactions, each with its status and candidate count, and offers the link
 *     only on the unique ones;
 *   - linking one row sends the link, removes that row from the list, leaves the others, and the page reloads its data;
 *     read back through the API, that transaction carries the event id and no other transaction changed;
 *   - «link all» links every unique row with a SINGLE commit, leaves the `none` and `several` rows, and when nothing else is
 *     left the empty state shows (`event-reconciliation-empty`) with nothing left to link;
 *   - an account with nothing to link sees the empty state at once; closing the modal links nothing.
 *
 * Data. Each test registers a disposable account (fixtures/owned-pair.ts), so the reconciliation list holds only the rows
 * it seeded — «link all» can never touch another spec's transactions — and a broker of its own, where the account is
 * OWNER. It creates a manual USD asset of its own (`createOwnedAsset`, asset-events-owned.ts), writes its own events, and
 * commits its own transactions, UNLINKED:
 *   - unique A  — a DIVIDEND on day 20 ago, with a DIVIDEND event that day;
 *   - unique B  — a DIVIDEND on day 18 ago, with a DIVIDEND event that day;
 *   - none      — a DIVIDEND on day 15 ago, with no event;
 *   - several   — an ADJUSTMENT on day 10 ago, with a SPLIT and a PRICE_ADJUSTMENT event that day (the two types an
 *                 ADJUSTMENT corresponds to; one type and one day cannot hold two events, so a DIVIDEND cannot be «several»).
 * `afterEach` deletes the broker (`force`: its transactions go with it), the asset (its prices and events go with it) and the
 * account, in that order.
 *
 * Key data-testids: tx-reconcile-events-button, event-reconciliation-modal|-loading|-empty|-error|-close|-link-all,
 * event-reconciliation-row-{id} [data-status, data-candidate-count], event-reconciliation-link-{id},
 * transactions-page [data-busy].
 *
 * Expected. Red before the cure, by absence: the button does not exist, so every test that opens the modal fails at it.
 */
import {expect, test, type APIRequestContext, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {commitCreates, emptyOwnedAccount, jsonFrom, openOwnedAccount, cleanupOwnedAccount, type OwnedAccount} from '../fixtures/owned-pair';
import {createOwnedBroker} from '../fixtures/onboarding-accounts';
import {createOwnedAsset, deleteOwned, seedEvents, type Owned} from '../assets/asset-events-owned';

const API = '/api/v1';
const COMMIT_PATH = `${API}/transactions/commit`;
const UI_TIMEOUT = 10_000;

// Each account goes through the real welcome hand-off before the page is even opened.
test.setTimeout(90_000);

/** What a seeded world holds, by role: the ids a test reads and asserts on. */
type World = {
    brokerId: number;
    assetId: number;
    /** The transaction with exactly one event the same day, and that event. */
    uniqueA: {tx: number; event: number};
    uniqueB: {tx: number; event: number};
    /** The transaction with no event the same day. */
    none: {tx: number};
    /** The ADJUSTMENT with a SPLIT and a PRICE_ADJUSTMENT the same day. */
    several: {tx: number; events: number[]};
};
type StoredTx = {id: number; asset_event_id: number | null};

let account: OwnedAccount;
let owned: Owned;

test.beforeEach(() => {
    account = emptyOwnedAccount();
    // The same array as the account's: a broker is recorded once, deleted once.
    owned = {assetIds: [], brokerIds: account.brokerIds};
});

// afterEach, not `finally`: it runs after a timeout too, and an error of its own is reported beside the test's.
test.afterEach(async ({page, request}) => {
    if (!account.user) return;
    // Brokers first (`force` takes their transactions), then the assets with their events; the account last.
    await deleteOwned(page, owned);
    account.brokerIds.length = 0;
    await cleanupOwnedAccount(page, request, account);
});

// ---------------------------------------------------------------------------
// Owned data (API)
// ---------------------------------------------------------------------------

/** A disposable account with a broker it owns; nothing else. */
async function openAccountWithBroker(page: Page, request: APIRequestContext): Promise<number> {
    await openOwnedAccount(page, request, account, 'recon');
    const broker = await createOwnedBroker(page, 'recon', account.brokerIds);
    return broker.id;
}

/** The world described in the header; `withUnresolvable: false` seeds only the two unique rows. */
async function seedWorld(page: Page, request: APIRequestContext, opts: {withUnresolvable?: boolean} = {}): Promise<World> {
    const withUnresolvable = opts.withUnresolvable ?? true;
    const brokerId = await openAccountWithBroker(page, request);
    const asset = await createOwnedAsset(page, owned, {label: 'E2E reconciliation'});

    const dayA = daysAgoIso(20);
    const dayB = daysAgoIso(18);
    const dayNone = daysAgoIso(15);
    const daySeveral = daysAgoIso(10);
    const events = await seedEvents(page, asset.id, [
        {date: dayA, type: 'DIVIDEND', amount: '1.25', notes: 'recon-unique-a'},
        {date: dayB, type: 'DIVIDEND', amount: '1.5', notes: 'recon-unique-b'},
        ...(withUnresolvable
            ? [
                  {date: daySeveral, type: 'SPLIT', amount: '2', notes: 'recon-several-split'},
                  {date: daySeveral, type: 'PRICE_ADJUSTMENT', amount: '1.5', notes: 'recon-several-price'},
              ]
            : []),
    ]);

    const dividend = (date: string, amount: string) => ({broker_id: brokerId, asset_id: asset.id, type: 'DIVIDEND', date, cash: {code: 'USD', amount}});
    const creates = [dividend(dayA, '5'), dividend(dayB, '6'), ...(withUnresolvable ? [dividend(dayNone, '7'), {broker_id: brokerId, asset_id: asset.id, type: 'ADJUSTMENT', date: daySeveral, quantity: '5', cost_basis_override: {code: 'USD', amount: '10'}}] : [])];
    const ids = await commitCreates(page, creates, 'commit the unlinked transactions');

    const world: World = {
        brokerId,
        assetId: asset.id,
        uniqueA: {tx: ids[0], event: events[0]},
        uniqueB: {tx: ids[1], event: events[1]},
        none: {tx: withUnresolvable ? ids[2] : -1},
        several: {tx: withUnresolvable ? ids[3] : -1, events: withUnresolvable ? [events[2], events[3]] : []},
    };
    // The premise, read back rather than inferred: every seeded transaction exists and none is linked yet.
    const stored = await storedTransactions(page, ids);
    expect(
        stored.map((tx) => tx.asset_event_id),
        'premise: the seeded transactions start unlinked',
    ).toEqual(ids.map(() => null));
    return world;
}

/** The transactions with these ids, as the API stores them. */
async function storedTransactions(page: Page, ids: number[]): Promise<StoredTx[]> {
    const rows = await jsonFrom<StoredTx[]>(await page.request.get(`${API}/transactions?${ids.map((id) => `ids=${id}`).join('&')}`), `read transactions ${ids.join(', ')}`);
    return ids.map((id) => {
        const row = rows.find((candidate) => candidate.id === id);
        if (!row) throw new Error(`Transaction ${id} is missing from the API: ${JSON.stringify(rows)}`);
        return row;
    });
}

async function linkedEventOf(page: Page, id: number): Promise<number | null> {
    return (await storedTransactions(page, [id]))[0].asset_event_id;
}

// ---------------------------------------------------------------------------
// The page
// ---------------------------------------------------------------------------

/** The Transactions page, settled. */
async function openTransactions(page: Page): Promise<void> {
    await navigateTo(page, '/transactions');
    await expect(page.getByTestId('transactions-page')).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
}

/** The reconciliation modal, opened from the page and loaded (its loading state gone). */
async function openReconciliation(page: Page): Promise<void> {
    await openTransactions(page);
    const button = page.getByTestId('tx-reconcile-events-button');
    await expect(button, 'the page offers the reconciliation among its actions').toBeVisible({timeout: UI_TIMEOUT});
    await button.click();
    await expect(page.getByTestId('event-reconciliation-modal')).toBeVisible({timeout: UI_TIMEOUT});
    await expect(page.getByTestId('event-reconciliation-loading')).toHaveCount(0, {timeout: UI_TIMEOUT});
}

const row = (page: Page, txId: number) => page.getByTestId(`event-reconciliation-row-${txId}`);
const linkButton = (page: Page, txId: number) => page.getByTestId(`event-reconciliation-link-${txId}`);

/** «Link all» offers nothing: absent, or present and disabled. */
async function expectNothingToLinkAll(page: Page): Promise<void> {
    const all = page.getByTestId('event-reconciliation-link-all');
    await expect(async () => {
        if ((await all.count()) > 0) await expect(all).toBeDisabled();
    }).toPass({timeout: UI_TIMEOUT});
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Event reconciliation (N68)', () => {
    test('lists each unlinked transaction with the server’s verdict, and offers the link only on the unique ones', async ({page, request}) => {
        const world = await seedWorld(page, request);

        await openReconciliation(page);

        await expect(row(page, world.uniqueA.tx)).toHaveAttribute('data-status', 'unique', {timeout: UI_TIMEOUT});
        await expect(row(page, world.uniqueA.tx)).toHaveAttribute('data-candidate-count', '1');
        await expect(row(page, world.uniqueB.tx)).toHaveAttribute('data-status', 'unique');
        await expect(row(page, world.uniqueB.tx)).toHaveAttribute('data-candidate-count', '1');
        await expect(row(page, world.none.tx)).toHaveAttribute('data-status', 'none');
        await expect(row(page, world.none.tx)).toHaveAttribute('data-candidate-count', '0');
        await expect(row(page, world.several.tx)).toHaveAttribute('data-status', 'several');
        await expect(row(page, world.several.tx)).toHaveAttribute('data-candidate-count', String(world.several.events.length));

        await expect(linkButton(page, world.uniqueA.tx)).toBeVisible();
        await expect(linkButton(page, world.uniqueB.tx)).toBeVisible();
        await expect(linkButton(page, world.none.tx), 'nothing to link on a none row').toHaveCount(0);
        await expect(linkButton(page, world.several.tx), 'a several row is never guessed').toHaveCount(0);
        await expect(page.getByTestId('event-reconciliation-link-all')).toBeEnabled();
        await expect(page.getByTestId('event-reconciliation-empty')).toHaveCount(0);
        await expect(page.getByTestId('event-reconciliation-error')).toHaveCount(0);
    });

    test('linking one unique row sends it, removes it from the list, leaves the others and reloads the page', async ({page, request}) => {
        const world = await seedWorld(page, request);
        await openReconciliation(page);
        await expect(row(page, world.uniqueA.tx)).toHaveAttribute('data-status', 'unique', {timeout: UI_TIMEOUT});

        // The page reloads its transactions when something was linked: armed before the click, after the first load.
        const reloaded = page.waitForRequest((req) => req.method() === 'GET' && new URL(req.url()).pathname === `${API}/transactions`, {timeout: UI_TIMEOUT});
        reloaded.catch(() => undefined); // awaited below; a failure earlier must not leave this one unhandled
        const [committed] = await Promise.all([page.waitForRequest((req) => req.method() === 'POST' && new URL(req.url()).pathname === COMMIT_PATH, {timeout: UI_TIMEOUT}), linkButton(page, world.uniqueA.tx).click()]);

        expect(committed.postDataJSON(), 'the link is the commit the app already uses: one update, the transaction and its only candidate').toEqual({updates: [{id: world.uniqueA.tx, asset_event_id: world.uniqueA.event}]});
        await expect(row(page, world.uniqueA.tx)).toHaveCount(0, {timeout: UI_TIMEOUT});
        await reloaded;
        // The others are untouched, and the page still lists them.
        await expect(row(page, world.uniqueB.tx)).toHaveAttribute('data-status', 'unique');
        await expect(row(page, world.none.tx)).toHaveAttribute('data-status', 'none');
        await expect(row(page, world.several.tx)).toHaveAttribute('data-status', 'several');
        await expect(page.getByTestId('event-reconciliation-error')).toHaveCount(0);

        // Read back: the transaction took the event; nothing else was linked.
        expect(await linkedEventOf(page, world.uniqueA.tx)).toBe(world.uniqueA.event);
        expect(await linkedEventOf(page, world.uniqueB.tx)).toBeNull();
        expect(await linkedEventOf(page, world.none.tx)).toBeNull();
        expect(await linkedEventOf(page, world.several.tx)).toBeNull();
    });

    test('link all links every unique row with ONE commit and leaves the none and the several rows', async ({page, request}) => {
        const world = await seedWorld(page, request);
        await openReconciliation(page);
        await expect(row(page, world.uniqueA.tx)).toHaveAttribute('data-status', 'unique', {timeout: UI_TIMEOUT});

        const commits: Array<{updates?: Array<{id: number; asset_event_id: number}>}> = [];
        page.on('request', (req) => {
            if (req.method() === 'POST' && new URL(req.url()).pathname === COMMIT_PATH) commits.push(req.postDataJSON());
        });
        await page.getByTestId('event-reconciliation-link-all').click();

        await expect(row(page, world.uniqueA.tx)).toHaveCount(0, {timeout: UI_TIMEOUT});
        await expect(row(page, world.uniqueB.tx)).toHaveCount(0, {timeout: UI_TIMEOUT});
        expect(commits, 'ONE commit for all the unique rows').toHaveLength(1);
        expect([...(commits[0].updates ?? [])].sort((left, right) => left.id - right.id)).toEqual(
            [
                {id: world.uniqueA.tx, asset_event_id: world.uniqueA.event},
                {id: world.uniqueB.tx, asset_event_id: world.uniqueB.event},
            ].sort((left, right) => left.id - right.id),
        );
        // What cannot be linked by itself stays, and is still not offered.
        await expect(row(page, world.none.tx)).toHaveAttribute('data-status', 'none');
        await expect(row(page, world.several.tx)).toHaveAttribute('data-status', 'several');
        await expectNothingToLinkAll(page);

        expect(await linkedEventOf(page, world.uniqueA.tx)).toBe(world.uniqueA.event);
        expect(await linkedEventOf(page, world.uniqueB.tx)).toBe(world.uniqueB.event);
        expect(await linkedEventOf(page, world.none.tx)).toBeNull();
        expect(await linkedEventOf(page, world.several.tx)).toBeNull();
    });

    test('when link all links the last rows, the empty state shows and nothing is left to link', async ({page, request}) => {
        const world = await seedWorld(page, request, {withUnresolvable: false});
        await openReconciliation(page);
        await expect(row(page, world.uniqueA.tx)).toHaveAttribute('data-status', 'unique', {timeout: UI_TIMEOUT});
        await expect(row(page, world.uniqueB.tx)).toHaveAttribute('data-status', 'unique');

        await page.getByTestId('event-reconciliation-link-all').click();

        await expect(page.getByTestId('event-reconciliation-empty')).toBeVisible({timeout: UI_TIMEOUT});
        await expect(row(page, world.uniqueA.tx)).toHaveCount(0);
        await expect(row(page, world.uniqueB.tx)).toHaveCount(0);
        await expectNothingToLinkAll(page);
        expect(await linkedEventOf(page, world.uniqueA.tx)).toBe(world.uniqueA.event);
        expect(await linkedEventOf(page, world.uniqueB.tx)).toBe(world.uniqueB.event);
    });
});

test.describe('Event reconciliation — nothing to link (N68)', () => {
    test('an account with nothing to relink sees the empty state at once, with nothing to link', async ({page, request}) => {
        await openAccountWithBroker(page, request);

        await openReconciliation(page);

        await expect(page.getByTestId('event-reconciliation-empty')).toBeVisible({timeout: UI_TIMEOUT});
        await expect(page.getByTestId('event-reconciliation-error')).toHaveCount(0);
        await expectNothingToLinkAll(page);
    });

    test('closing the modal links nothing', async ({page, request}) => {
        const world = await seedWorld(page, request);
        await openReconciliation(page);
        await expect(row(page, world.uniqueA.tx)).toHaveAttribute('data-status', 'unique', {timeout: UI_TIMEOUT});
        const commits: string[] = [];
        page.on('request', (req) => {
            if (req.method() === 'POST' && new URL(req.url()).pathname === COMMIT_PATH) commits.push(req.url());
        });

        await page.getByTestId('event-reconciliation-close').click();

        await expect(page.getByTestId('event-reconciliation-modal')).toBeHidden({timeout: UI_TIMEOUT});
        expect(commits, 'closing commits nothing').toEqual([]);
        expect(await linkedEventOf(page, world.uniqueA.tx)).toBeNull();
        expect(await linkedEventOf(page, world.uniqueB.tx)).toBeNull();
    });
});
