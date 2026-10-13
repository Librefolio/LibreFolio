/**
 * The pairs a transaction spec works on — its own when it writes, a seeded one when it only reads.
 *
 * ## Why this exists
 *
 * `tx-split-promote` (C3) and `tx-paired-edit` (TODO-B) each carried a copy of the same helpers: an account of
 * their own, two brokers it owns, a funded TRANSFER between them, and the cleanup that deletes it all. The
 * read-only tests of the same specs, and of `tx-clone`, found their rows by scanning the table — row after row,
 * by position, by CSS class — and took whatever came first.
 *
 * ## The two ways in
 *
 * - **A test that commits owns its rows.** {@link openAccountWithPair} registers a disposable account, takes it
 *   through the welcome hand-off, creates two brokers it owns, funds the giver and saves a TRANSFER pair between
 *   them, then reads the link back. Rows on that account are invisible to every other spec. {@link
 *   cleanupOwnedAccount} deletes the brokers — `force` takes every row on them, whatever the test made of the
 *   pair — and the account last. {@link openOwnedAccount} is the same account without the pair, for a test that
 *   needs brokers of its own.
 * - **A test that only reads borrows a seeded row**, found by the marker `populate_mock_data.py` writes into its
 *   description, and verified rather than assumed: {@link seededPair} insists on two halves linked to each other,
 *   on brokers the signed-in user can edit unless told otherwise; {@link seededRow} on one standalone row on such
 *   a broker. A copy someone cloned carries the same description, so the seeded row is the oldest one. The caller
 *   then narrows the table to those ids instead of scanning it.
 */

import {randomUUID} from 'crypto';
import {expect, type APIRequestContext, type Page} from './playwright';
import {daysAgoIso} from './dates';
import {createOwnedBroker, deleteDisposableUser, prepareOnboardingAccount, registerDisposableUser, type DisposableUser, type OwnedBroker} from './onboarding-accounts';

const API = '/api/v1';

type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type CommitBody = {committed: boolean; issues?: unknown[]; results?: Array<{operation: string; index: number; ids: number[]}>};

/** A transaction as `GET /transactions` returns it (`TXReadItem`), reduced to what the specs read. */
export type TxRow = {
    id: number;
    broker_id: number;
    asset_id?: number | null;
    type: string;
    date: string;
    quantity: string;
    cash?: {code: string; amount: string} | null;
    related_transaction_id?: number | null;
    tags?: string[] | null;
    description?: string | null;
};
/** A broker as `GET /brokers` lists it, with the signed-in user's role on it. */
export type BrokerRow = {id: number; name: string; user_role?: string | null};
/** A seeded linked pair: `giver` is the half that sends, `receiver` the half that takes. */
export type SeededPair = {giver: TxRow; receiver: TxRow};

/** What a committing test created, recorded the moment it exists so the cleanup finds all of it. */
export type OwnedAccount = {user: DisposableUser | null; brokerIds: number[]};
/** A saved asset TRANSFER between the account's two brokers: `fromId` sends from `giver`, `toId` receives on `receiver`, both on `date`. */
export type OwnedPair = {fromId: number; toId: number; giver: OwnedBroker; receiver: OwnedBroker; date: string; description: string};

/** Nothing created yet: what a test starts from, and what its cleanup then leaves alone. */
export function emptyOwnedAccount(): OwnedAccount {
    return {user: null, brokerIds: []};
}

// ---------------------------------------------------------------------------
// API primitives
// ---------------------------------------------------------------------------

/** The response's JSON, once its status says it succeeded — or a failure naming `purpose` and the server's answer. */
export async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    return (await response.json()) as T;
}

/** Commit `creates` as one batch; returns the id of each create, in request order. */
export async function commitCreates(page: Page, creates: Array<Record<string, unknown>>, purpose: string): Promise<number[]> {
    const body = await jsonFrom<CommitBody>(await page.request.post(`${API}/transactions/commit`, {data: {creates}}), purpose);
    expect(body.committed, `${purpose}: rolled back — ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    return creates.map((_, index) => {
        const id = body.results?.find((item) => item.operation === 'create' && item.index === index)?.ids[0];
        if (typeof id !== 'number') throw new Error(`${purpose}: the commit returned no id for create #${index} — ${JSON.stringify(body.results)}`);
        return id;
    });
}

/** `GET /transactions` with `params`, as the user signed in on `page` sees them. */
export async function readTransactions(page: Page, params: Record<string, string | number | boolean> = {}): Promise<TxRow[]> {
    return jsonFrom<TxRow[]>(await page.request.get(`${API}/transactions`, {params}), `read the transactions ${JSON.stringify(params)}`);
}

/** Every broker the user signed in on `page` can see, each with that user's role on it. */
export async function listBrokers(page: Page): Promise<BrokerRow[]> {
    const {items} = await jsonFrom<{items: BrokerRow[]}>(await page.request.get(`${API}/brokers`), 'list the brokers');
    return items;
}

/** Whether the role reported on `broker` lets its user edit the broker's rows. */
export function canEdit(broker: BrokerRow | undefined): boolean {
    return broker?.user_role === 'OWNER' || broker?.user_role === 'EDITOR';
}

/** The seeded asset with this exact ticker — read, never assumed. */
export async function seededAssetId(page: Page, ticker: string): Promise<number> {
    const assets = await jsonFrom<Array<{id: number}>>(await page.request.get(`${API}/assets/query?ticker=${encodeURIComponent(ticker)}`), `look up the ${ticker} asset`);
    if (assets.length !== 1) throw new Error(`Expected exactly one asset with ticker ${ticker}, found ${assets.length} — check populate_mock_data.py`);
    return assets[0].id;
}

// ---------------------------------------------------------------------------
// Seeded rows, borrowed read-only
// ---------------------------------------------------------------------------

/** The half of a pair that sends, read the way the transactions table reads it: a negative quantity, or a negative cash amount when it moves no quantity. */
function sends(tx: TxRow): boolean {
    const quantity = Number(tx.quantity);
    if (Number.isFinite(quantity) && quantity !== 0) return quantity < 0;
    return Number(tx.cash?.amount ?? 0) < 0;
}

/**
 * The seeded pair whose description starts with `marker`, verified: two rows linked to each other, visible to the
 * signed-in user and — unless `editable` is false — both on brokers that user can edit. Giver first.
 */
export async function seededPair(page: Page, marker: string, opts: {editable?: boolean} = {}): Promise<SeededPair> {
    const rows = (await readTransactions(page)).filter((tx) => (tx.description ?? '').startsWith(marker));
    const byId = new Map(rows.map((tx) => [tx.id, tx]));
    const linked = rows.filter((tx) => tx.related_transaction_id != null && tx.id < tx.related_transaction_id && byId.get(tx.related_transaction_id)?.related_transaction_id === tx.id);
    if (linked.length === 0) throw new Error(`No pair described "${marker}…" with both halves linked to each other is visible to this user (${rows.length} row(s) carry the marker) — check populate_mock_data.py`);
    const first = linked.reduce((oldest, tx) => (tx.id < oldest.id ? tx : oldest));
    const partner = byId.get(first.related_transaction_id as number) as TxRow;
    const pair = sends(first) ? {giver: first, receiver: partner} : {giver: partner, receiver: first};
    expect(sends(pair.receiver), `premise: exactly one half of "${marker}" #${first.id}/#${partner.id} sends`).toBe(false);
    if (opts.editable ?? true) {
        const brokers = new Map((await listBrokers(page)).map((broker) => [broker.id, broker]));
        for (const half of [pair.giver, pair.receiver]) {
            expect(canEdit(brokers.get(half.broker_id)), `premise: "${marker}" #${half.id} sits on a broker this user can edit (${JSON.stringify(brokers.get(half.broker_id) ?? null)})`).toBe(true);
        }
    }
    return pair;
}

/** The seeded standalone row described exactly `description`, verified: linked to nothing, on a broker the signed-in user can edit. */
export async function seededRow(page: Page, description: string): Promise<TxRow> {
    const rows = (await readTransactions(page)).filter((tx) => tx.description === description);
    if (rows.length === 0) throw new Error(`No row described "${description}" is visible to this user — check populate_mock_data.py`);
    const row = rows.reduce((oldest, tx) => (tx.id < oldest.id ? tx : oldest));
    expect(row.related_transaction_id ?? null, `premise: "${description}" #${row.id} is a standalone row`).toBeNull();
    const broker = (await listBrokers(page)).find((candidate) => candidate.id === row.broker_id);
    expect(canEdit(broker), `premise: "${description}" #${row.id} sits on a broker this user can edit (${JSON.stringify(broker ?? null)})`).toBe(true);
    return row;
}

// ---------------------------------------------------------------------------
// Owned accounts, for the tests that commit
// ---------------------------------------------------------------------------

/** Register a disposable account, record it in `owned` before anything else, and sign `page` in through the welcome hand-off. */
export async function openOwnedAccount(page: Page, request: APIRequestContext, owned: OwnedAccount, tag: string): Promise<void> {
    owned.user = await registerDisposableUser(request, tag);
    await prepareOnboardingAccount(page, owned.user, []);
}

/**
 * A disposable account holding one saved asset TRANSFER between two brokers it owns.
 *
 * The giver is funded first — a deposit, then a buy — so neither the transfer nor an edit of its quantity takes
 * it below zero. The asset is the seeded Ethereum, which this only reads. `tag` must stay short: it goes into the
 * account's username, which is capped at 50 characters.
 */
export async function openAccountWithPair(page: Page, request: APIRequestContext, owned: OwnedAccount, tag: string): Promise<OwnedPair> {
    await openOwnedAccount(page, request, owned, tag);
    const giver = await createOwnedBroker(page, `${tag}-from`, owned.brokerIds);
    const receiver = await createOwnedBroker(page, `${tag}-to`, owned.brokerIds);
    const assetId = await seededAssetId(page, 'ETH-USD');

    const funding = [
        {broker_id: giver.id, type: 'DEPOSIT', date: daysAgoIso(10), cash: {code: 'USD', amount: '100'}},
        {broker_id: giver.id, asset_id: assetId, type: 'BUY', date: daysAgoIso(9), quantity: '0.01', cash: {code: 'USD', amount: '-30'}},
    ];
    await commitCreates(page, funding, 'fund the giver broker');

    const linkUuid = randomUUID();
    const date = daysAgoIso(5);
    const description = `Owned pair ${tag}`;
    const transfer = [
        {broker_id: giver.id, asset_id: assetId, type: 'TRANSFER', date, quantity: '-0.001', link_uuid: linkUuid, description},
        {broker_id: receiver.id, asset_id: assetId, type: 'TRANSFER', date, quantity: '0.001', link_uuid: linkUuid, description, cost_basis_mode: 'auto'},
    ];
    const [fromId, toId] = await commitCreates(page, transfer, 'commit the owned TRANSFER pair');

    // The premise, read back rather than inferred: the two halves point at each other.
    const halves = await jsonFrom<TxRow[]>(await page.request.get(`${API}/transactions?ids=${fromId}&ids=${toId}`), 'read the owned pair back');
    const linkOf = new Map(halves.map((tx) => [tx.id, tx.related_transaction_id ?? null] as const));
    expect([linkOf.get(fromId), linkOf.get(toId)], 'premise: the two halves of the owned pair are linked to each other').toEqual([toId, fromId]);
    return {fromId, toId, giver, receiver, date, description};
}

/**
 * Leave the page, then delete the account: its brokers first — `force` takes their transactions with them, the
 * pair and whatever the test made of it — and the account last. Only what `owned` recorded.
 */
export async function cleanupOwnedAccount(page: Page, request: APIRequestContext, owned: OwnedAccount): Promise<void> {
    const user = owned.user;
    if (!user) return; // nothing was created: brokers only ever exist under the account
    try {
        // Unmount the page first, so nothing on it reloads the rows while they go.
        await page.goto('about:blank');
    } finally {
        await deleteDisposableUser(request, user, owned.brokerIds);
    }
}
