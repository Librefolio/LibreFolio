/**
 * tx-split-refusal.spec.ts — W-B39: a Split pair or a Promote pair refused by the server says why.
 *
 * The Transactions page commits a Split pair (row menu → split → the `tx-action-modal` confirmation) and a Promote
 * pair (selection toolbar → «Link as pair» → its confirmation) on its own, through `commitTransactions`, which
 * raises no toast. On `committed: false` the page only wrote the issues to the console: the confirmation stayed
 * open with no reason on screen, so a refusal looked like a server that never answered — and a network error was
 * just as silent.
 *
 * Contract (W-B39):
 *   - a refused commit raises an error toast (`toast-error`): the action's title, then each distinct reason,
 *     worded by `resolveIssueMessage` as the editor's banners word it;
 *   - the issue's parameters reach the words and no `{placeholder}` is left: a split refused for a missing
 *     exchange rate names the pair (`USD`); a promote refused on a broker names that broker by its owned name,
 *     resolved through the page's broker context, never as `Broker #id`;
 *   - the confirmation stays open, its confirm usable again, so the user can remove the cause and retry;
 *   - nothing changed: the one commit the page sent was answered by the refusal, and after Cancel the pair is
 *     still linked and the two rows still standalone, read back through the API.
 *
 * The refusal is served by `page.route` on `POST /api/v1/transactions/commit` (every other method continues).
 * It is a `TXBatchResponse` as the server serialises one — `results: []`, `success_count: 0`, `errors: []`,
 * `committed: false`, one `TXValidationIssue`, `wac_results: null` — because the generated Zodios client validates
 * responses (`validate: 'response'`): a body off the schema would reach the page as a network error and test the
 * wrong path. The split issue is the one `batch_costs._wac_fx_unavailable` writes (`wacFxUnavailable` on
 * `cost_basis_override`, on the receiving leg, which takes the handed-over cost — the row this test clicks); the
 * promote issue is the one `transaction_batch_stages._access_issue` writes (`accessDenied` with `brokerId`), as if
 * the account had lost EDITOR on the receiving broker since the page loaded. Setup, read-back and cleanup go
 * through `page.request` and `request`, which `page.route` never intercepts.
 *
 * Before the cure both tests are red at the toast: the page logs the refusal and shows nothing.
 *
 * Owned data: each test registers a disposable account (fixtures/owned-pair.ts), so its rows are invisible to
 * every other spec. The split test holds the funded asset TRANSFER pair `openAccountWithPair` builds; the promote
 * test a WITHDRAWAL and a DEPOSIT with identical fields on two brokers it creates with `allow_cash_overdraft`, so
 * no funding row is needed. `afterEach` deletes the brokers with `force` — every row on them goes too — then the
 * account.
 *
 * Runs on the desktop project, like every transactions spec the runner registers.
 *
 * Key data-testids used:
 *   transactions-page [data-busy]                    — the page's own "every load wave is in"
 *   tr[data-row-id="tx-{id}"], tx-link-icon-{id}     — an owned row, and its link shown
 *   row-actions-tx-{id} → context-menu → context-menu-action-split
 *   tx-action-modal, tx-action-modal-confirm|-cancel — the split confirmation
 *   dt-row-checkbox-tx-{id} [data-state]             — ticking the two promote candidates
 *   selection-toolbar [data-selected-count]          — the page selection
 *   toolbar-action-promote                           — «Link as pair», offered only when a promote rule matches
 *   confirm-modal-confirm|-cancel                    — its plain confirm, when the two rows' fields agree
 *   promote-merge-modal                              — the merge modal, absent when they agree
 *   toast-error                                      — the refusal: its variant and its parameters, never its words
 */

import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {cleanupOwnedAccount, commitCreates, emptyOwnedAccount, jsonFrom, openAccountWithPair, openOwnedAccount, type OwnedAccount, type TxRow} from '../fixtures/owned-pair';

const API = '/api/v1';
const COMMIT_PATH = `${API}/transactions/commit`;
const UI_TIMEOUT = 10_000;
/** The verdicts follow the intercepted commit: by then the refusal is already in the page. */
const VERDICT_TIMEOUT = 5_000;

// Each account goes through the real welcome hand-off before the page is even opened.
test.setTimeout(60_000);

type PairItem = {id_a: number; id_b: number; resolved_fields?: Record<string, unknown>};
/** What the page sent to the commit endpoint. */
type CommitPayload = {creates?: unknown[]; updates?: unknown[]; deletes?: number[]; splits?: PairItem[]; promotes?: PairItem[]};
/** One `TXValidationIssue`, every field the server serialises. */
type Issue = {operation: 'split' | 'promote'; index: number; ref_id: number | null; error: string; code: string; params: Record<string, unknown> | null; field: string | null};
/** A refused `TXBatchResponse`, as the server serialises one. */
type Refusal = {results: []; success_count: 0; errors: string[]; committed: false; issues: Issue[]; wac_results: null};
type Broker = {id: number; name: string};
/** The two facts a refused commit must leave as they were, per row. */
type LinkFacts = Record<number, {type: string | null; related: number | null}>;

const byId = (a: number, b: number) => a - b;

// ---------------------------------------------------------------------------
// The refusal
// ---------------------------------------------------------------------------

/** A refused commit as the server answers one: nothing written, one issue. */
function refusal(issue: Issue): Refusal {
    return {results: [], success_count: 0, errors: [], committed: false, issues: [issue], wac_results: null};
}

/**
 * Answer every POST the page sends to the commit endpoint with `body`, and record what it sent; any other method
 * goes on to the server. Installed once the owned data exists — and `page.request` is never routed anyway.
 */
async function refuseCommits(page: Page, body: Refusal): Promise<CommitPayload[]> {
    const sent: CommitPayload[] = [];
    await page.route(
        (url) => url.pathname === COMMIT_PATH,
        async (route) => {
            const request = route.request();
            if (request.method() !== 'POST') {
                await route.continue();
                return;
            }
            sent.push(request.postDataJSON() as CommitPayload);
            await route.fulfill({status: 200, contentType: 'application/json', json: body});
        },
    );
    return sent;
}

/** The commit the page sent — the refused one, and the only one. */
async function theCommitSent(sent: CommitPayload[], operation: string): Promise<CommitPayload> {
    await expect.poll(() => sent.length, {message: `the ${operation} reached the commit endpoint, where it was refused`, timeout: UI_TIMEOUT}).toBe(1);
    return sent[0];
}

/** A payload with each pair item's two ids in ascending order: which half the page names first is not the subject. */
function normalised(payload: CommitPayload): Record<string, unknown> {
    const pairs = (items: PairItem[]) => items.map(({id_a, id_b, ...rest}) => ({ids: [id_a, id_b].sort(byId), ...rest}));
    return {...payload, ...(payload.splits ? {splits: pairs(payload.splits)} : {}), ...(payload.promotes ? {promotes: pairs(payload.promotes)} : {})};
}

/**
 * The refusal reached the user: an error toast, with `parameter` — a value of the issue, never a word of the
 * catalogue — in it, and no `{placeholder}` left unfilled. Before the cure the page shows nothing: the red is here.
 */
async function expectRefusalToast(page: Page, operation: string, parameter: string): Promise<void> {
    const toast = page.getByTestId('toast-error');
    await expect(toast, `W-B39: a refused ${operation} raises an error toast`).toBeVisible({timeout: VERDICT_TIMEOUT});
    await expect(toast, `the ${operation} toast leaves no {placeholder} unfilled`).not.toContainText('{');
    await expect(toast, `the ${operation} toast names ${parameter}, a parameter of the issue`).toContainText(parameter);
}

// ---------------------------------------------------------------------------
// Owned data (API)
// ---------------------------------------------------------------------------

/** A broker the account owns, allowed below zero cash; recorded for cleanup the moment it exists. */
async function createOverdraftBroker(page: Page, owned: OwnedAccount, label: string): Promise<Broker> {
    const name = `W-B39 ${label} ${uniqueSuffix()}`;
    const body = await jsonFrom<{results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>}>(await page.request.post(`${API}/brokers`, {data: [{name, opened_at: '2020-01-01', allow_cash_overdraft: true}]}), `create the owned broker "${label}"`);
    const created = body.results.find((item) => item.name === name);
    if (!created?.success || typeof created.broker_id !== 'number') throw new Error(`The owned broker "${label}" got no id: ${JSON.stringify(created ?? body)}`);
    owned.brokerIds.push(created.broker_id);
    return {id: created.broker_id, name};
}

/** Type and link of each row, read back through the API as the account sees them. */
async function linkFacts(page: Page, ids: number[]): Promise<LinkFacts> {
    const rows = await jsonFrom<TxRow[]>(await page.request.get(`${API}/transactions?${ids.map((id) => `ids=${id}`).join('&')}`), `read back transactions ${ids.join(', ')}`);
    const byRow = new Map(rows.map((row) => [row.id, row]));
    return Object.fromEntries(ids.map((id) => [id, {type: byRow.get(id)?.type ?? null, related: byRow.get(id)?.related_transaction_id ?? null}]));
}

// ---------------------------------------------------------------------------
// The page
// ---------------------------------------------------------------------------

function transactionsPage(page: Page): Locator {
    return page.getByTestId('transactions-page');
}

function tableRow(page: Page, id: number): Locator {
    return transactionsPage(page).getByTestId('tx-table').locator(`tr[data-row-id="tx-${id}"]`);
}

/** The Transactions page — the account sees nothing but its own rows — settled, with every row `ids` on screen. */
async function openTransactions(page: Page, ids: number[]): Promise<void> {
    await navigateTo(page, '/transactions');
    await expect(transactionsPage(page)).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(transactionsPage(page), 20_000);
    for (const id of ids) await expect(tableRow(page, id), `transaction ${id} is on screen`).toBeVisible({timeout: UI_TIMEOUT});
}

/** A linked row's own menu → split: ends with the split confirmation on screen. */
async function openSplitConfirm(page: Page, id: number): Promise<Locator> {
    await tableRow(page, id).getByTestId(`row-actions-tx-${id}`).click();
    const menu = page.getByTestId('context-menu');
    await expect(menu).toBeVisible({timeout: UI_TIMEOUT});
    await menu.getByTestId('context-menu-action-split').click();
    const modal = page.getByTestId('tx-action-modal');
    await expect(modal).toBeVisible({timeout: UI_TIMEOUT});
    return modal;
}

/** Tick each row — on a fresh page none is ticked, which is checked first — and end with the toolbar holding exactly them. */
async function selectRows(page: Page, ids: number[]): Promise<void> {
    for (const id of ids) {
        const checkbox = tableRow(page, id).getByTestId(`dt-row-checkbox-tx-${id}`);
        await expect(checkbox, `precondition: transaction ${id} starts unticked`).toHaveAttribute('data-state', 'unchecked');
        await checkbox.click();
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
    }
    await expect(transactionsPage(page).getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', String(ids.length));
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('W-B39 — a refused Split pair or Promote pair says why', () => {
    let owned: OwnedAccount = emptyOwnedAccount();

    test.beforeEach(() => {
        owned = emptyOwnedAccount();
    });

    // afterEach, not `finally`: it runs after a timeout too, and an error of its own is reported beside the
    // test's instead of replacing it.
    test.afterEach(async ({page, request}) => {
        await cleanupOwnedAccount(page, request, owned);
    });

    test('S1 split refused for a missing exchange rate: an error toast names the pair, the confirmation stays, the pair stays linked', async ({page, request}, testInfo) => {
        const pair = await openAccountWithPair(page, request, owned, `wb39s_${testInfo.project.name}`);
        await openTransactions(page, [pair.fromId, pair.toId]);
        await expect(transactionsPage(page).getByTestId(`tx-link-icon-${pair.toId}`), 'precondition: the owned pair shows as linked').toBeVisible({timeout: UI_TIMEOUT});

        const sent = await refuseCommits(
            page,
            refusal({
                operation: 'split',
                index: 0,
                ref_id: pair.toId,
                error: 'WAC calculation failed: missing FX pairs USD/EUR',
                code: 'wacFxUnavailable',
                params: {pairs: ['USD/EUR'], pair_details: [{pair: 'USD/EUR', dates: [pair.date]}]},
                field: 'cost_basis_override',
            }),
        );

        // From the receiving leg: the row a split hands the cost to, so the row the server names.
        const modal = await openSplitConfirm(page, pair.toId);
        await modal.getByTestId('tx-action-modal-confirm').click();
        const payload = await theCommitSent(sent, 'split');
        expect(normalised(payload), 'the request splits the owned pair, and does nothing else').toEqual({splits: [{ids: [pair.fromId, pair.toId].sort(byId)}]});

        await expectRefusalToast(page, 'split', 'USD');
        await expect(modal, 'a refusal keeps the confirmation open').toBeVisible();
        await expect(modal.getByTestId('tx-action-modal-confirm'), 'and its confirm can be pressed again').toBeEnabled();
        expect(sent, 'the page sent no second commit').toHaveLength(1);

        await modal.getByTestId('tx-action-modal-cancel').click();
        await expect(modal).toBeHidden({timeout: UI_TIMEOUT});
        expect(await linkFacts(page, [pair.fromId, pair.toId]), 'nothing changed: still one linked TRANSFER pair').toEqual({
            [pair.fromId]: {type: 'TRANSFER', related: pair.toId},
            [pair.toId]: {type: 'TRANSFER', related: pair.fromId},
        });
        await expect(transactionsPage(page).getByTestId(`tx-link-icon-${pair.toId}`), 'and the table still shows the link').toBeVisible();
    });

    test('P1 promote refused on a broker: an error toast names the broker, the confirmation stays, the rows stay standalone', async ({page, request}, testInfo) => {
        await openOwnedAccount(page, request, owned, `wb39p_${testInfo.project.name}`);
        const from = await createOverdraftBroker(page, owned, 'from');
        const to = await createOverdraftBroker(page, owned, 'to');
        // The two halves of a cash transfer with every field equal — date, currency, amount, description, no tags —
        // so «Link as pair» matches CASH_TRANSFER and goes straight to its plain confirm, never to the merge modal.
        const date = daysAgoIso(5);
        const description = `W-B39 promote ${uniqueSuffix()}`;
        const [withdrawal, deposit] = await commitCreates(
            page,
            [
                {broker_id: from.id, type: 'WITHDRAWAL', date, cash: {code: 'EUR', amount: '-100'}, description},
                {broker_id: to.id, type: 'DEPOSIT', date, cash: {code: 'EUR', amount: '100'}, description},
            ],
            'commit the two standalone halves',
        );
        const standalone: LinkFacts = {[withdrawal]: {type: 'WITHDRAWAL', related: null}, [deposit]: {type: 'DEPOSIT', related: null}};
        expect(await linkFacts(page, [withdrawal, deposit]), 'precondition: two standalone rows').toEqual(standalone);

        await openTransactions(page, [withdrawal, deposit]);
        await selectRows(page, [withdrawal, deposit]);

        // The broker-access refusal the server writes on a promote, here on the receiving broker.
        const sent = await refuseCommits(
            page,
            refusal({
                operation: 'promote',
                index: 0,
                ref_id: deposit,
                error: `Access denied: EDITOR required for broker ${to.id}`,
                code: 'accessDenied',
                params: {brokerId: to.id},
                field: null,
            }),
        );

        const promote = transactionsPage(page).getByTestId('selection-toolbar').getByTestId('toolbar-action-promote');
        await expect(promote, 'precondition: the two rows match a promote rule').toBeVisible({timeout: UI_TIMEOUT});
        await promote.click();
        const confirm = page.getByTestId('confirm-modal-confirm');
        await expect(confirm).toBeVisible({timeout: UI_TIMEOUT});
        await expect(page.getByTestId('promote-merge-modal'), 'precondition: the fields agree, so the plain confirm and no merge modal').toHaveCount(0);

        await confirm.click();
        const payload = await theCommitSent(sent, 'promote');
        expect(normalised(payload), 'the request promotes the two ticked rows, with nothing to resolve, and does nothing else').toEqual({promotes: [{ids: [withdrawal, deposit].sort(byId)}]});

        await expectRefusalToast(page, 'promote', to.name);
        await expect(confirm, 'a refusal keeps the confirmation open').toBeVisible();
        expect(sent, 'the page sent no second commit').toHaveLength(1);

        await page.getByTestId('confirm-modal-cancel').click();
        await expect(confirm).toHaveCount(0, {timeout: UI_TIMEOUT});
        expect(await linkFacts(page, [withdrawal, deposit]), 'nothing changed: still two standalone rows').toEqual(standalone);
        await expect(tableRow(page, withdrawal)).toBeVisible();
        await expect(transactionsPage(page).getByTestId(`tx-link-icon-${withdrawal}`), 'and the table shows no link').toHaveCount(0);
    });
});
