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
 * FB-19 (the window is a DataTable with column filters, a selection bar and the creation of the missing events):
 *   - the event column names the event (`[data-event-type]`: its code, the emoji the catalogue of event types gives it and its
 *     name in the interface language, read from the translation catalogue and never typed here);
 *   - the asset and broker column filters narrow the list, and «link every row» links only the unique rows still shown;
 *   - «Create event» (one row) and «Create events» (the selected rows) open the creation dialog: ONE line per event (rows of the
 *     same asset, day and type share it), the value suggested from the transaction's cash, ONE `POST /assets/events` (mode
 *     `create`), then the rows are `unique` and nothing is linked until the user links them; a refusal (here: an event that
 *     appeared behind the dialog's back, 409) keeps the dialog open and creates nothing;
 *   - «Link selected» links the selected unique rows only, and a selection with nothing to act on says so (`-notice`).
 * Each FB-19 test seeds its own account, brokers, assets and events (the helpers below), like the N68 ones.
 *
 * Key data-testids: tx-reconcile-events-button, event-reconciliation-modal|-loading|-empty|-error|-close|-link-all|-notice|-table,
 * event-reconciliation-row-{id} [data-status, data-candidate-count], event-reconciliation-link-{id}, event-reconciliation-create-{id},
 * event-reconciliation-create-modal|-row-{id} [data-transactions]|-type-{id}|-amount-{id}|-confirm|-cancel|-error,
 * dt-row-checkbox-{id}, selection-bar-action-link|-create, col-filter-trigger-{column}, filter-enum-option-{value},
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
import {createOwnedAsset, deleteOwned, seedEvents, storedEvents, EVENTS_PATH, type Owned, type OwnedAsset} from '../assets/asset-events-owned';
import {t as catalogueText} from '../fixtures/i18n-data';

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

// ---------------------------------------------------------------------------
// FB-19 helpers: the table, its filters, its selection, the creation dialog
// ---------------------------------------------------------------------------

type NewEventBody = Array<{asset_id: number; mode: string; events: Array<{date: string; type: string; value: {code: string; amount: string}}>}>;
type StoredEventRow = {id: number; date: string; type: string; value: {code: string; amount: string}};

/** The JSON bodies of the POSTs to `pathname` this page sends from now on (listen BEFORE the action). */
function recordPosts<T>(page: Page, pathname: string): T[] {
    const bodies: T[] = [];
    page.on('request', (req) => {
        if (req.method() === 'POST' && new URL(req.url()).pathname === pathname) bodies.push(req.postDataJSON() as T);
    });
    return bodies;
}

type CommitBody = {updates?: Array<{id: number; asset_event_id: number}>};
const byId = (left: {id: number}, right: {id: number}) => left.id - right.id;

/** The language the page is drawn in, once its dictionary is in (`<html lang>`). */
async function pageLanguage(page: Page): Promise<string> {
    const html = page.locator('html');
    await expect(html, 'the page has its dictionary').toHaveAttribute('data-i18n-ready', 'true');
    return ((await html.getAttribute('lang')) ?? '').split('-')[0];
}

/** event code → emoji, as the server's catalogue of event types gives it (the one the app draws). */
async function eventEmojis(page: Page): Promise<Map<string, string>> {
    const body = await jsonFrom<{event_types: Array<{code: string; emoji: string}>}>(await page.request.get(`${API}/transactions/types`), 'read the catalogue of event types');
    return new Map(body.event_types.map((type) => [type.code, type.emoji]));
}

/** A disposable account with `brokers` brokers and `assets` USD assets of its own; ids in creation order. */
async function seedAccount(page: Page, request: APIRequestContext, shape: {brokers: number; assets: number}): Promise<{brokerIds: number[]; assets: OwnedAsset[]}> {
    const brokerIds = [await openAccountWithBroker(page, request)];
    for (let index = 1; index < shape.brokers; index++) brokerIds.push((await createOwnedBroker(page, `recon-${index}`, account.brokerIds)).id);
    const assets: OwnedAsset[] = [];
    for (let index = 0; index < shape.assets; index++) assets.push(await createOwnedAsset(page, owned, {label: `E2E reconciliation ${index}`}));
    return {brokerIds, assets};
}

const dividendTx = (brokerId: number, assetId: number, date: string, amount: string) => ({broker_id: brokerId, asset_id: assetId, type: 'DIVIDEND', date, cash: {code: 'USD', amount}});

/** Premise, read back: every transaction exists and none is linked. */
async function expectUnlinked(page: Page, ids: number[]): Promise<void> {
    const stored = await storedTransactions(page, ids);
    expect(
        stored.map((tx) => tx.asset_event_id),
        'premise: the seeded transactions start unlinked',
    ).toEqual(ids.map(() => null));
}

/** The events of the asset on that day and type (the asset is the test's own). */
async function eventsOn(page: Page, assetId: number, date: string, type: string): Promise<StoredEventRow[]> {
    return (await storedEvents(page, assetId)).filter((event) => event.date === date && event.type === type);
}

/** The column filter of the table in the window: its funnel and its popover. */
function columnFilter(page: Page, column: string) {
    const table = page.getByTestId('event-reconciliation-table');
    return {trigger: table.getByTestId(`col-filter-trigger-${column}`), popover: table.getByTestId(`dt-header-${column}`).getByTestId('column-filter')};
}

/** Pick one option of an enum column filter (the option is a value: an asset id, a broker id) and close the popover. */
async function pickFilterOption(page: Page, column: string, value: string | number): Promise<void> {
    const {trigger, popover} = columnFilter(page, column);
    await trigger.click();
    await expect(popover).toBeVisible({timeout: UI_TIMEOUT});
    const option = popover.getByTestId(`filter-enum-option-${value}`);
    await expect(option, 'the filter offers this value, not picked yet').toHaveAttribute('data-checked', 'false', {timeout: UI_TIMEOUT});
    await option.click();
    await expect(option).toHaveAttribute('data-checked', 'true');
    await trigger.click();
    await expect(popover).toBeHidden();
}

/**
 * Clear a column filter with the popover's reset button. Not by unticking its option: the options come from the rows still in the list,
 * and once the rows of the filtered value are linked the value is no longer offered while the filter is still set.
 */
async function resetColumnFilter(page: Page, column: string): Promise<void> {
    const {trigger, popover} = columnFilter(page, column);
    await trigger.click();
    await expect(popover).toBeVisible({timeout: UI_TIMEOUT});
    await popover.getByTestId('column-filter-reset').click();
    await trigger.click();
    await expect(popover).toBeHidden();
}

/** Tick (or untick) the selection checkbox of a row. */
async function setSelected(page: Page, txId: number, selected: boolean): Promise<void> {
    const box = page.getByTestId(`dt-row-checkbox-${txId}`);
    await expect(box).toBeVisible({timeout: UI_TIMEOUT});
    if ((await box.getAttribute('data-state')) !== (selected ? 'checked' : 'unchecked')) await box.click();
    await expect(box).toHaveAttribute('data-state', selected ? 'checked' : 'unchecked');
}

const createModal = (page: Page) => page.getByTestId('event-reconciliation-create-modal');

/** The creation dialog, open with exactly the lines the caller expects (one per event to create). */
async function expectCreateModalOpen(page: Page, lines: number): Promise<void> {
    await expect(createModal(page)).toBeVisible({timeout: UI_TIMEOUT});
    await expect(createModal(page).locator('[data-transactions]'), 'the dialog draws one line per event').toHaveCount(lines, {timeout: UI_TIMEOUT});
}

/** The amount typed in a line, as a number: the suggestion is the transaction's cash, whatever zeros the server wrote after the point. */
async function lineAmount(page: Page, lineId: number): Promise<number> {
    return Number(await page.getByTestId(`event-reconciliation-create-amount-${lineId}`).inputValue());
}

// ---------------------------------------------------------------------------
// FB-19 tests
// ---------------------------------------------------------------------------

test.describe('Event reconciliation — the table (FB-19)', () => {
    test('the event column names each event: its code, its emoji and its name in the interface language', async ({page, request}) => {
        const {brokerIds, assets} = await seedAccount(page, request, {brokers: 1, assets: 1});
        const [brokerId] = brokerIds;
        const [asset] = assets;
        const days = {dividend: daysAgoIso(20), interest: daysAgoIso(19), split: daysAgoIso(18), price: daysAgoIso(17), adjustment: daysAgoIso(16), noDividend: daysAgoIso(15)};
        await seedEvents(page, asset.id, [
            {date: days.dividend, type: 'DIVIDEND', amount: '1.25', notes: 'recon-col-dividend'},
            {date: days.interest, type: 'INTEREST', amount: '0.75', notes: 'recon-col-interest'},
            {date: days.split, type: 'SPLIT', amount: '2', notes: 'recon-col-split'},
            {date: days.price, type: 'PRICE_ADJUSTMENT', amount: '1.5', notes: 'recon-col-price'},
        ]);
        const adjustment = (date: string) => ({broker_id: brokerId, asset_id: asset.id, type: 'ADJUSTMENT', date, quantity: '5', cost_basis_override: {code: 'USD', amount: '10'}});
        const [dividend, interest, split, price, adjustmentNoEvent, dividendNoEvent] = await commitCreates(
            page,
            [
                dividendTx(brokerId, asset.id, days.dividend, '5'),
                {broker_id: brokerId, asset_id: asset.id, type: 'INTEREST', date: days.interest, cash: {code: 'USD', amount: '3'}},
                adjustment(days.split),
                adjustment(days.price),
                adjustment(days.adjustment),
                dividendTx(brokerId, asset.id, days.noDividend, '7'),
            ],
            'commit one transaction per kind of event',
        );
        await expectUnlinked(page, [dividend, interest, split, price, adjustmentNoEvent, dividendNoEvent]);

        await openReconciliation(page);
        const lang = await pageLanguage(page);
        const emojis = await eventEmojis(page);
        // The name is the catalogue's, in the language the page is drawn in; for an adjustment with no event yet, the transaction's own.
        const expectations = [
            {tx: dividend, code: 'DIVIDEND', emoji: emojis.get('DIVIDEND'), key: 'assetDetail.eventType.DIVIDEND'},
            {tx: interest, code: 'INTEREST', emoji: emojis.get('INTEREST'), key: 'assetDetail.eventType.INTEREST'},
            {tx: split, code: 'SPLIT', emoji: emojis.get('SPLIT'), key: 'assetDetail.eventType.SPLIT'},
            {tx: price, code: 'PRICE_ADJUSTMENT', emoji: emojis.get('PRICE_ADJUSTMENT'), key: 'assetDetail.eventType.PRICE_ADJUSTMENT'},
            {tx: adjustmentNoEvent, code: 'ADJUSTMENT', emoji: emojis.get('PRICE_ADJUSTMENT'), key: 'transactions.types.ADJUSTMENT'},
            {tx: dividendNoEvent, code: 'DIVIDEND', emoji: emojis.get('DIVIDEND'), key: 'assetDetail.eventType.DIVIDEND'},
        ];
        for (const {tx, code, emoji, key} of expectations) {
            expect(emoji, `the catalogue gives ${code} an emoji`).toMatch(/\p{Extended_Pictographic}/u);
            const label = catalogueText(lang, key);
            expect(label, `the "${lang}" catalogue has ${key}`).not.toBe(key);
            await expect(row(page, tx), `row of ${code} is listed`).toBeVisible({timeout: UI_TIMEOUT});
            const cell = page
                .locator('tr')
                .filter({has: row(page, tx)})
                .locator('[data-event-type]');
            await expect(cell).toHaveAttribute('data-event-type', code);
            await expect(cell, `the event column draws the emoji and the name of ${code}`).toHaveText(`${emoji} ${label}`);
        }
        // What decides the verdicts under the names: the four with an event are unique, the other two have none.
        for (const tx of [dividend, interest, split, price]) await expect(row(page, tx)).toHaveAttribute('data-status', 'unique');
        for (const tx of [adjustmentNoEvent, dividendNoEvent]) await expect(row(page, tx)).toHaveAttribute('data-status', 'none');
    });
});

test.describe('Event reconciliation — filters (FB-19)', () => {
    /** Two brokers (X, Y) × two assets (A, B): four unique rows, the same day, each asset with one event. */
    async function seedGrid(page: Page, request: APIRequestContext) {
        const {brokerIds, assets} = await seedAccount(page, request, {brokers: 2, assets: 2});
        const [brokerX, brokerY] = brokerIds;
        const [assetA, assetB] = assets;
        const day = daysAgoIso(20);
        const [eventA] = await seedEvents(page, assetA.id, [{date: day, type: 'DIVIDEND', amount: '1.25', notes: 'recon-grid-a'}]);
        const [eventB] = await seedEvents(page, assetB.id, [{date: day, type: 'DIVIDEND', amount: '2.5', notes: 'recon-grid-b'}]);
        const [ax, ay, bx, by] = await commitCreates(page, [dividendTx(brokerX, assetA.id, day, '5'), dividendTx(brokerY, assetA.id, day, '6'), dividendTx(brokerX, assetB.id, day, '7'), dividendTx(brokerY, assetB.id, day, '8')], 'commit the four unlinked dividends');
        await expectUnlinked(page, [ax, ay, bx, by]);
        return {brokerX, brokerY, assetA, assetB, eventA, eventB, ax, ay, bx, by};
    }

    /** Open the window and wait until all four rows are drawn and unique. */
    async function openGrid(page: Page, grid: Awaited<ReturnType<typeof seedGrid>>): Promise<void> {
        await openReconciliation(page);
        for (const tx of [grid.ax, grid.ay, grid.bx, grid.by]) await expect(row(page, tx)).toHaveAttribute('data-status', 'unique', {timeout: UI_TIMEOUT});
    }

    test('the asset filter narrows the list, and link all links only the unique rows still shown', async ({page, request}) => {
        const grid = await seedGrid(page, request);
        await openGrid(page, grid);

        await pickFilterOption(page, 'asset', grid.assetA.id);
        await expect(row(page, grid.ax)).toBeVisible();
        await expect(row(page, grid.ay)).toBeVisible();
        await expect(row(page, grid.bx), 'the other asset’s rows are filtered out').toHaveCount(0);
        await expect(row(page, grid.by)).toHaveCount(0);

        const commits = recordPosts<CommitBody>(page, COMMIT_PATH);
        await page.getByTestId('event-reconciliation-link-all').click();
        await expect(row(page, grid.ax)).toHaveCount(0, {timeout: UI_TIMEOUT});
        await expect(row(page, grid.ay)).toHaveCount(0);

        expect(commits, 'ONE commit').toHaveLength(1);
        expect([...(commits[0].updates ?? [])].sort(byId), 'exactly the unique rows of the filtered asset').toEqual(
            [
                {id: grid.ax, asset_event_id: grid.eventA},
                {id: grid.ay, asset_event_id: grid.eventA},
            ].sort(byId),
        );
        // Read back: the filtered-out rows were not linked.
        expect(await linkedEventOf(page, grid.ax)).toBe(grid.eventA);
        expect(await linkedEventOf(page, grid.ay)).toBe(grid.eventA);
        expect(await linkedEventOf(page, grid.bx)).toBeNull();
        expect(await linkedEventOf(page, grid.by)).toBeNull();

        // Clear the filter: the rows that were hidden are still there, unique, and still offered.
        await resetColumnFilter(page, 'asset');
        await expect(row(page, grid.bx)).toHaveAttribute('data-status', 'unique', {timeout: UI_TIMEOUT});
        await expect(row(page, grid.by)).toHaveAttribute('data-status', 'unique');
        await expect(page.getByTestId('event-reconciliation-link-all')).toBeEnabled();
        expect(commits, 'clearing the filter sends nothing').toHaveLength(1);
    });

    test('the broker filter narrows the list, and link all links only the unique rows still shown', async ({page, request}) => {
        const grid = await seedGrid(page, request);
        await openGrid(page, grid);

        await pickFilterOption(page, 'broker', grid.brokerY);
        await expect(row(page, grid.ay)).toBeVisible();
        await expect(row(page, grid.by)).toBeVisible();
        await expect(row(page, grid.ax), 'the other broker’s rows are filtered out').toHaveCount(0);
        await expect(row(page, grid.bx)).toHaveCount(0);

        const commits = recordPosts<CommitBody>(page, COMMIT_PATH);
        await page.getByTestId('event-reconciliation-link-all').click();
        await expect(row(page, grid.ay)).toHaveCount(0, {timeout: UI_TIMEOUT});
        await expect(row(page, grid.by)).toHaveCount(0);

        expect(commits, 'ONE commit').toHaveLength(1);
        expect([...(commits[0].updates ?? [])].sort(byId), 'exactly the unique rows of the filtered broker').toEqual(
            [
                {id: grid.ay, asset_event_id: grid.eventA},
                {id: grid.by, asset_event_id: grid.eventB},
            ].sort(byId),
        );
        expect(await linkedEventOf(page, grid.ay)).toBe(grid.eventA);
        expect(await linkedEventOf(page, grid.by)).toBe(grid.eventB);
        expect(await linkedEventOf(page, grid.ax)).toBeNull();
        expect(await linkedEventOf(page, grid.bx)).toBeNull();

        await resetColumnFilter(page, 'broker');
        await expect(row(page, grid.ax)).toHaveAttribute('data-status', 'unique', {timeout: UI_TIMEOUT});
        await expect(row(page, grid.bx)).toHaveAttribute('data-status', 'unique');
    });
});

test.describe('Event reconciliation — selection (FB-19)', () => {
    test('link selected links the selected unique rows only; a selection with nothing to act on says so and sends nothing', async ({page, request}) => {
        const world = await seedWorld(page, request);
        await openReconciliation(page);
        await expect(row(page, world.uniqueA.tx)).toHaveAttribute('data-status', 'unique', {timeout: UI_TIMEOUT});
        const commits = recordPosts<CommitBody>(page, COMMIT_PATH);

        // A unique row and a none row: only the unique one is sent.
        await setSelected(page, world.uniqueA.tx, true);
        await setSelected(page, world.none.tx, true);
        await page.getByTestId('selection-bar-action-link').click();
        await expect(row(page, world.uniqueA.tx)).toHaveCount(0, {timeout: UI_TIMEOUT});
        expect(commits, 'ONE commit').toHaveLength(1);
        expect(commits[0].updates, 'only the selected unique row').toEqual([{id: world.uniqueA.tx, asset_event_id: world.uniqueA.event}]);
        await expect(row(page, world.uniqueB.tx), 'a unique row that was not selected stays').toHaveAttribute('data-status', 'unique');
        await expect(row(page, world.none.tx)).toHaveAttribute('data-status', 'none');
        expect(await linkedEventOf(page, world.uniqueA.tx)).toBe(world.uniqueA.event);
        expect(await linkedEventOf(page, world.uniqueB.tx)).toBeNull();
        expect(await linkedEventOf(page, world.none.tx)).toBeNull();
        // The link cleared the selection.
        await expect(page.getByTestId(`dt-row-checkbox-${world.none.tx}`)).toHaveAttribute('data-state', 'unchecked');

        // Only a none row: nothing to link, said, and no request.
        await setSelected(page, world.none.tx, true);
        await expect(page.getByTestId('event-reconciliation-notice')).toHaveCount(0);
        await page.getByTestId('selection-bar-action-link').click();
        await expect(page.getByTestId('event-reconciliation-notice')).toBeVisible({timeout: UI_TIMEOUT});
        expect(commits, 'nothing to link sends no commit').toHaveLength(1);

        // Opening the creation dialog for it clears the notice; cancelling creates nothing.
        await page.getByTestId('selection-bar-action-create').click();
        await expectCreateModalOpen(page, 1);
        await expect(page.getByTestId('event-reconciliation-notice')).toHaveCount(0);
        await page.getByTestId('event-reconciliation-create-cancel').click();
        await expect(createModal(page)).toBeHidden({timeout: UI_TIMEOUT});

        // Only a unique row: nothing to create, said, and no dialog.
        await setSelected(page, world.none.tx, false);
        await setSelected(page, world.uniqueB.tx, true);
        await page.getByTestId('selection-bar-action-create').click();
        await expect(page.getByTestId('event-reconciliation-notice')).toBeVisible({timeout: UI_TIMEOUT});
        await expect(createModal(page)).toHaveCount(0);
        expect(await linkedEventOf(page, world.uniqueB.tx)).toBeNull();
    });
});

test.describe('Event reconciliation — create the missing events (FB-19)', () => {
    test('create event from a row: the value is suggested from its cash, ONE request creates it, the row becomes unique and can be linked', async ({page, request}) => {
        const {brokerIds, assets} = await seedAccount(page, request, {brokers: 1, assets: 1});
        const [asset] = assets;
        const day = daysAgoIso(15);
        const [tx] = await commitCreates(page, [dividendTx(brokerIds[0], asset.id, day, '7.5')], 'commit a dividend with no event');
        await expectUnlinked(page, [tx]);
        expect(await eventsOn(page, asset.id, day, 'DIVIDEND'), 'premise: no event that day').toEqual([]);

        await openReconciliation(page);
        await expect(row(page, tx)).toHaveAttribute('data-status', 'none', {timeout: UI_TIMEOUT});
        await expect(row(page, tx)).toHaveAttribute('data-candidate-count', '0');
        await expect(linkButton(page, tx), 'nothing to link yet').toHaveCount(0);

        await page.getByTestId(`event-reconciliation-create-${tx}`).click();
        await expectCreateModalOpen(page, 1);
        const line = page.getByTestId(`event-reconciliation-create-row-${tx}`);
        await expect(line).toHaveAttribute('data-transactions', '1');
        await expect(page.getByTestId(`event-reconciliation-create-type-${tx}`), 'a dividend can only be a dividend').toHaveAttribute('data-event-type', 'DIVIDEND');
        // The value starts from the transaction's cash (the asset is in USD, so is the cash).
        await expect.poll(() => lineAmount(page, tx), {message: 'the value is suggested from the cash'}).toBe(7.5);
        await expect(page.getByTestId('event-reconciliation-create-confirm')).toBeEnabled();

        const creates = recordPosts<NewEventBody>(page, EVENTS_PATH);
        const commits = recordPosts<CommitBody>(page, COMMIT_PATH);
        await page.getByTestId('event-reconciliation-create-confirm').click();

        // The dialog closes and the window reads its list again: the row now has an event.
        await expect(createModal(page)).toBeHidden({timeout: UI_TIMEOUT});
        await expect(row(page, tx)).toHaveAttribute('data-status', 'unique', {timeout: UI_TIMEOUT});
        await expect(row(page, tx)).toHaveAttribute('data-candidate-count', '1');
        expect(creates, 'ONE request creates the events').toHaveLength(1);
        expect(creates[0], 'one item, for the asset, in mode create').toHaveLength(1);
        expect(creates[0][0].asset_id).toBe(asset.id);
        expect(creates[0][0].mode).toBe('create');
        expect(creates[0][0].events, 'one event: the transaction’s day and type, its currency and value').toHaveLength(1);
        expect(creates[0][0].events[0]).toMatchObject({date: day, type: 'DIVIDEND', value: {code: 'USD'}});
        expect(Number(creates[0][0].events[0].value.amount)).toBe(7.5);
        // Read back: the event exists with that value, and creating it linked nothing.
        const stored = await eventsOn(page, asset.id, day, 'DIVIDEND');
        expect(stored, 'the event was created').toHaveLength(1);
        expect(Number(stored[0].value.amount)).toBe(7.5);
        expect(stored[0].value.code).toBe('USD');
        expect(await linkedEventOf(page, tx), 'creating the event links nothing').toBeNull();
        expect(commits, 'no commit yet').toEqual([]);

        // Now it is a row like the others: link it.
        await linkButton(page, tx).click();
        await expect(row(page, tx)).toHaveCount(0, {timeout: UI_TIMEOUT});
        expect(commits).toHaveLength(1);
        expect(commits[0].updates).toEqual([{id: tx, asset_event_id: stored[0].id}]);
        expect(await linkedEventOf(page, tx)).toBe(stored[0].id);
    });

    test('create events for two selected rows of different assets: one dialog with two lines, ONE request with two items, both rows become unique', async ({page, request}) => {
        const {brokerIds, assets} = await seedAccount(page, request, {brokers: 1, assets: 2});
        const [assetA, assetB] = assets;
        const day = daysAgoIso(15);
        const [txA, txB] = await commitCreates(page, [dividendTx(brokerIds[0], assetA.id, day, '4'), dividendTx(brokerIds[0], assetB.id, day, '6')], 'commit two dividends with no event');
        await expectUnlinked(page, [txA, txB]);

        await openReconciliation(page);
        await expect(row(page, txA)).toHaveAttribute('data-status', 'none', {timeout: UI_TIMEOUT});
        await expect(row(page, txB)).toHaveAttribute('data-status', 'none');
        await setSelected(page, txA, true);
        await setSelected(page, txB, true);
        await page.getByTestId('selection-bar-action-create').click();

        await expectCreateModalOpen(page, 2);
        await expect(page.getByTestId(`event-reconciliation-create-row-${txA}`)).toHaveAttribute('data-transactions', '1');
        await expect(page.getByTestId(`event-reconciliation-create-row-${txB}`)).toHaveAttribute('data-transactions', '1');
        await expect.poll(() => lineAmount(page, txA)).toBe(4);
        await expect.poll(() => lineAmount(page, txB)).toBe(6);
        // The user may change the suggestion.
        await page.getByTestId(`event-reconciliation-create-amount-${txA}`).fill('3.25');
        await expect(page.getByTestId(`event-reconciliation-create-amount-${txA}`)).toHaveValue('3.25');

        const creates = recordPosts<NewEventBody>(page, EVENTS_PATH);
        await page.getByTestId('event-reconciliation-create-confirm').click();

        await expect(createModal(page)).toBeHidden({timeout: UI_TIMEOUT});
        await expect(row(page, txA)).toHaveAttribute('data-status', 'unique', {timeout: UI_TIMEOUT});
        await expect(row(page, txB)).toHaveAttribute('data-status', 'unique', {timeout: UI_TIMEOUT});
        expect(creates, 'ONE request for both events').toHaveLength(1);
        expect(creates[0], 'one item per asset').toHaveLength(2);
        const itemA = creates[0].find((item) => item.asset_id === assetA.id);
        const itemB = creates[0].find((item) => item.asset_id === assetB.id);
        expect(itemA?.mode).toBe('create');
        expect(itemB?.mode).toBe('create');
        expect(itemA?.events).toHaveLength(1);
        expect(itemB?.events).toHaveLength(1);
        expect(itemA?.events[0]).toMatchObject({date: day, type: 'DIVIDEND', value: {code: 'USD'}});
        expect(Number(itemA?.events[0].value.amount)).toBe(3.25);
        expect(Number(itemB?.events[0].value.amount)).toBe(6);
        const storedA = await eventsOn(page, assetA.id, day, 'DIVIDEND');
        const storedB = await eventsOn(page, assetB.id, day, 'DIVIDEND');
        expect(storedA.map((event) => Number(event.value.amount))).toEqual([3.25]);
        expect(storedB.map((event) => Number(event.value.amount))).toEqual([6]);
        expect(await linkedEventOf(page, txA), 'creating links nothing').toBeNull();
        expect(await linkedEventOf(page, txB)).toBeNull();
    });

    test('two rows of the same asset, day and type share ONE line and one event', async ({page, request}) => {
        const {brokerIds, assets} = await seedAccount(page, request, {brokers: 1, assets: 1});
        const [asset] = assets;
        const day = daysAgoIso(15);
        const [tx1, tx2] = await commitCreates(page, [dividendTx(brokerIds[0], asset.id, day, '4'), dividendTx(brokerIds[0], asset.id, day, '6')], 'commit two dividends of the same day with no event');
        await expectUnlinked(page, [tx1, tx2]);

        await openReconciliation(page);
        await expect(row(page, tx1)).toHaveAttribute('data-status', 'none', {timeout: UI_TIMEOUT});
        await expect(row(page, tx2)).toHaveAttribute('data-status', 'none');
        await setSelected(page, tx1, true);
        await setSelected(page, tx2, true);
        await page.getByTestId('selection-bar-action-create').click();

        await expectCreateModalOpen(page, 1);
        const lines = createModal(page).locator('[data-transactions]');
        await expect(lines, 'one line serves both rows').toHaveAttribute('data-transactions', '2');
        // The line is named by the first transaction of its group: one of the two.
        const lineTestId = (await lines.getAttribute('data-testid')) ?? '';
        const lineId = Number(lineTestId.replace('event-reconciliation-create-row-', ''));
        expect([tx1, tx2], 'the line is named by one of its transactions').toContain(lineId);
        await page.getByTestId(`event-reconciliation-create-amount-${lineId}`).fill('2.5');
        await expect(page.getByTestId(`event-reconciliation-create-amount-${lineId}`)).toHaveValue('2.5');

        const creates = recordPosts<NewEventBody>(page, EVENTS_PATH);
        await page.getByTestId('event-reconciliation-create-confirm').click();

        await expect(createModal(page)).toBeHidden({timeout: UI_TIMEOUT});
        await expect(row(page, tx1)).toHaveAttribute('data-status', 'unique', {timeout: UI_TIMEOUT});
        await expect(row(page, tx2)).toHaveAttribute('data-status', 'unique', {timeout: UI_TIMEOUT});
        await expect(row(page, tx1)).toHaveAttribute('data-candidate-count', '1');
        await expect(row(page, tx2)).toHaveAttribute('data-candidate-count', '1');
        expect(creates, 'ONE request').toHaveLength(1);
        expect(creates[0]).toHaveLength(1);
        expect(creates[0][0].events, 'one event for both transactions').toHaveLength(1);
        const stored = await eventsOn(page, asset.id, day, 'DIVIDEND');
        expect(stored).toHaveLength(1);
        expect(Number(stored[0].value.amount)).toBe(2.5);

        // Both link to that one event, in one commit.
        const commits = recordPosts<CommitBody>(page, COMMIT_PATH);
        await page.getByTestId('event-reconciliation-link-all').click();
        await expect(row(page, tx1)).toHaveCount(0, {timeout: UI_TIMEOUT});
        await expect(row(page, tx2)).toHaveCount(0);
        expect(commits).toHaveLength(1);
        expect([...(commits[0].updates ?? [])].sort(byId)).toEqual(
            [
                {id: tx1, asset_event_id: stored[0].id},
                {id: tx2, asset_event_id: stored[0].id},
            ].sort(byId),
        );
        expect(await linkedEventOf(page, tx1)).toBe(stored[0].id);
        expect(await linkedEventOf(page, tx2)).toBe(stored[0].id);
    });

    test('a refused creation keeps the dialog open with its error and creates nothing, not even the events that were fine', async ({page, request}) => {
        const {brokerIds, assets} = await seedAccount(page, request, {brokers: 1, assets: 2});
        const [assetA, assetB] = assets;
        const day = daysAgoIso(15);
        const [txA, txB] = await commitCreates(page, [dividendTx(brokerIds[0], assetA.id, day, '4'), dividendTx(brokerIds[0], assetB.id, day, '6')], 'commit two dividends with no event');
        await expectUnlinked(page, [txA, txB]);

        await openReconciliation(page);
        await expect(row(page, txA)).toHaveAttribute('data-status', 'none', {timeout: UI_TIMEOUT});
        await expect(row(page, txB)).toHaveAttribute('data-status', 'none');
        await setSelected(page, txA, true);
        await setSelected(page, txB, true);
        await page.getByTestId('selection-bar-action-create').click();
        await expectCreateModalOpen(page, 2);
        await expect.poll(() => lineAmount(page, txA)).toBe(4);
        await expect.poll(() => lineAmount(page, txB)).toBe(6);

        // Behind the dialog's back, the asset B gets the very event the dialog is about to create: a `create` refuses it (409).
        await seedEvents(page, assetB.id, [{date: day, type: 'DIVIDEND', amount: '9', notes: 'recon-behind-the-back'}]);
        const creates = recordPosts<NewEventBody>(page, EVENTS_PATH);
        const [refusal] = await Promise.all([page.waitForResponse((res) => res.request().method() === 'POST' && new URL(res.url()).pathname === EVENTS_PATH, {timeout: UI_TIMEOUT}), page.getByTestId('event-reconciliation-create-confirm').click()]);

        expect(refusal.status(), 'the server refuses an event that already exists').toBe(409);
        await expect(page.getByTestId('event-reconciliation-create-error')).toBeVisible({timeout: UI_TIMEOUT});
        await expect(createModal(page), 'the dialog stays open').toBeVisible();
        await expect(page.getByTestId('event-reconciliation-create-confirm'), 'the user can correct and try again').toBeEnabled();
        expect(creates, 'one request, refused').toHaveLength(1);
        // Read back: nothing was created — the fine line (asset A) either — and the event B already had is untouched.
        expect(await eventsOn(page, assetA.id, day, 'DIVIDEND'), 'all or nothing: the asset without a conflict got no event').toEqual([]);
        const heldByB = await eventsOn(page, assetB.id, day, 'DIVIDEND');
        expect(heldByB.map((event) => Number(event.value.amount))).toEqual([9]);
        expect(await linkedEventOf(page, txA)).toBeNull();
        expect(await linkedEventOf(page, txB)).toBeNull();

        // Cancelling closes the dialog; the window still shows both rows as they were read.
        await page.getByTestId('event-reconciliation-create-cancel').click();
        await expect(createModal(page)).toBeHidden({timeout: UI_TIMEOUT});
        await expect(row(page, txA)).toHaveAttribute('data-status', 'none');
        await expect(page.getByTestId('event-reconciliation-modal')).toBeVisible();
    });
});
