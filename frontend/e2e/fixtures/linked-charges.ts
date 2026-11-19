/**
 * A saved parent with its linked charges, on an account of the test's own (lane 66).
 *
 * ## Why this exists
 *
 * `tx-charges-write` (F7-b) and `tx-bulk-charges-grid` (F7-c1) both need the same seed: a disposable account with a
 * broker it owns, funded by its own DEPOSIT, and a BUY with a FEE and a TAX committed linked to it in one batch
 * (`ref` / `parent_ref`). Playwright does not let a spec import another one, so the helpers live here instead of in
 * two copies.
 *
 * - {@link openFundedAccount}: the account, its broker and the funding DEPOSIT (ten days ago, 1000 USD).
 * - {@link seedLinkedBuy}: the same, plus the BUY (five days ago) and its FEE and TAX, the link read back by id as the
 *   premise: both charges point at the BUY, which counts two.
 * - {@link readByIds}: the server's state of some ids; an id that no longer exists is simply absent.
 *
 * Cleanup stays with the spec (its afterEach deletes what of its ids is left, then `cleanupOwnedAccount`): every id
 * these helpers commit is pushed onto the `committed` list the spec hands them.
 */
import {expect, type APIRequestContext, type Page} from './playwright';
import {daysAgoIso} from './dates';
import {uniqueSuffix} from './unique';
import {createOwnedBroker, type OwnedBroker} from './onboarding-accounts';
import {commitCreates, jsonFrom, openOwnedAccount, seededAssetId, type OwnedAccount} from './owned-pair';

const API = '/api/v1';
export const COMMIT_PATH = `${API}/transactions/commit`;

/** A transaction read back by id, reduced to what the lane-66 specs check. */
export type ChargeTx = {
    id: number;
    type: string;
    broker_id: number;
    asset_id?: number | null;
    date: string;
    quantity: string;
    cash?: {code: string; amount: string} | null;
    description?: string | null;
    parent_transaction_id?: number | null;
    charges_count?: number;
};
type CommitResult = {operation: string; index: number; ids?: number[]; status?: string};
export type CommitBody = {committed?: boolean; issues?: unknown[]; results?: CommitResult[]};

/** A funded account: its broker, the asset the seed trades, the marker in every description, the funding DEPOSIT. */
export type FundedAccount = {broker: OwnedBroker; assetId: number; marker: string; depositId: number};
/** A funded account with a BUY and its FEE and TAX, linked, on one asset and date. */
export type LinkedBuy = FundedAccount & {buyId: number; feeId: number; taxId: number};

/** These transactions as the server has them now; an id that no longer exists is simply absent. */
export async function readByIds(page: Page, ids: number[]): Promise<Map<number, ChargeTx>> {
    if (ids.length === 0) return new Map();
    const query = ids.map((id) => `ids=${id}`).join('&');
    const rows = await jsonFrom<ChargeTx[]>(await page.request.get(`${API}/transactions?${query}`), `read transactions ${ids.join(',')}`);
    return new Map(rows.map((tx) => [tx.id, tx] as const));
}

/** Open a disposable account with one broker it owns, funded by its own DEPOSIT. `prefix` starts the marker. */
export async function openFundedAccount(page: Page, request: APIRequestContext, owned: OwnedAccount, committed: number[], tag: string, prefix: string): Promise<FundedAccount> {
    const marker = `${prefix} ${uniqueSuffix()}`;
    await openOwnedAccount(page, request, owned, tag);
    const broker = await createOwnedBroker(page, tag, owned.brokerIds);
    const assetId = await seededAssetId(page, 'ETH-USD');
    // Fund the broker first: a BUY and its charges take cash out of it.
    const [depositId] = await commitCreates(page, [{broker_id: broker.id, type: 'DEPOSIT', date: daysAgoIso(10), cash: {code: 'USD', amount: '1000'}, description: `Deposit ${marker}`}], 'fund the broker');
    committed.push(depositId);
    return {broker, assetId, marker, depositId};
}

/** A funded account with a BUY and a FEE and a TAX committed linked to it (`ref` / `parent_ref`), the link read back. */
export async function seedLinkedBuy(page: Page, request: APIRequestContext, owned: OwnedAccount, committed: number[], tag: string, prefix: string): Promise<LinkedBuy> {
    const funded = await openFundedAccount(page, request, owned, committed, tag, prefix);
    const {broker, assetId, marker} = funded;
    const date = daysAgoIso(5);
    const charge = {broker_id: broker.id, asset_id: assetId, date, quantity: '0', parent_ref: 'p'};
    const body = await jsonFrom<CommitBody>(
        await page.request.post(COMMIT_PATH, {
            data: {
                creates: [
                    {ref: 'p', broker_id: broker.id, asset_id: assetId, type: 'BUY', date, quantity: '10', cash: {code: 'USD', amount: '-100'}, description: `Buy ${marker}`},
                    {...charge, type: 'FEE', cash: {code: 'USD', amount: '-5'}, description: `Fee ${marker}`},
                    {...charge, type: 'TAX', cash: {code: 'USD', amount: '-2'}, description: `Tax ${marker}`},
                ],
            },
        }),
        'commit the BUY with its linked charges',
    );
    expect(body.committed, `rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    const idAt = (index: number): number => {
        const id = body.results?.find((item) => item.operation === 'create' && item.index === index)?.ids?.[0];
        if (typeof id !== 'number') throw new Error(`no id for create #${index}: ${JSON.stringify(body.results)}`);
        return id;
    };
    const [buyId, feeId, taxId] = [idAt(0), idAt(1), idAt(2)];
    committed.push(buyId, feeId, taxId);

    // The premise, read back rather than inferred: both charges point at the BUY, which counts two.
    const back = await readByIds(page, [buyId, feeId, taxId]);
    expect([back.get(feeId)?.parent_transaction_id ?? null, back.get(taxId)?.parent_transaction_id ?? null], 'premise: the FEE and the TAX are linked to the BUY').toEqual([buyId, buyId]);
    expect(back.get(buyId)?.charges_count, 'premise: the BUY counts two charges').toBe(2);
    return {...funded, buyId, feeId, taxId};
}
