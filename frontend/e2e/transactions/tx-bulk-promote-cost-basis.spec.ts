/**
 * tx-bulk-promote-cost-basis.spec.ts — the bulk editor's side of a promote that leaves the
 * receiving side of an asset TRANSFER without a cost basis (d7c148564).
 *
 * `validate_cost_basis` (`backend/app/services/transactions/transaction_batch_stages.py`) checks promoted
 * pairs: once two ADJUSTMENTs are promoted into a TRANSFER, the receiving side (quantity > 0)
 * needs a cost basis like any other receiver, unless it is in Auto mode, and without one the
 * whole batch is refused. A promoted NEW row is checked as the create it is — `{operation:
 * 'create', index: <its create index>}` — which the editor maps onto its rows with
 * `resolveBulkIssueRows` (`$lib/features/transactions/bulk/bulkDisplay.ts`): `create:<i>` names the new
 * row, and the jump lands on the one row the pair is shown as (the other half is its hidden
 * partner). A promoted SAVED row is checked on the promote that paired it — `{operation:
 * 'promote', index: <promote index>, ref_id: <its id>}` (`_check_promoted_saved_cost_basis`) —
 * but only the API reaches that check now: see «PC2's saved receiver» below.
 *
 *   PC1  a NEW incoming ADJUSTMENT, Manual with an empty cost basis, promoted with a SAVED
 *        outgoing one through the selection toolbar → one `create` issue on its create index;
 *   PC2  (the offer, not the save) a SAVED incoming ADJUSTMENT without a cost basis, linked to a
 *        SPLIT event, beside a NEW outgoing one that cancels it → neither the banner nor the
 *        selection toolbar offers the merge, and the two rows stay apart;
 *   PC2b (the 💡, not the save) PC2's linked receiver and an unlinked twin, both saved and left out
 *        of the editor, beside a NEW outgoing −5 → the database search, and the 💡, offer the twin,
 *        never the linked receiver;
 *   PC2c (the 💡, not the save) the linked receiver and its unlinked twin in the editor, a SAVED
 *        outgoing −5 outside it → the −5 is offered to the twin only, nothing to the linked receiver;
 *   PC3  PC1's pair merged by the banner's «Merge all» together with a valid cash pair → the one
 *        `create` issue, and the jump lands on PC1's pair, not on the other one;
 *   PC4  (the banner, not the save) a new +5 beside a saved −3 and a saved −5 of the same asset:
 *        the banner offers one merge only, the −5's, never the crossed −3 / +5 the backend's
 *        promote rule refuses (`assetQuantitiesCancel`, `$lib/features/transactions/bulk/promoteSuggest.ts`);
 *   PC5  (the selection toolbar, not the save) two new ADJUSTMENTs, −123456789012.123456 on A and
 *        +123456789012.123457 on B, opposite as doubles and not as decimals → neither the banner nor
 *        the selection toolbar offers the merge; the regression test of C-46, see «PC5» below;
 *   PC6  (the 💡's window, not the save) a new +5 on B, two saved −5 on A outside the editor, today and
 *        yesterday → with «Max Δ days» at 0 the 💡 offers today's alone, and moving the slider to 1
 *        searches again and offers both; red until the cure, see «PC6» below;
 *   PC7  (W-B70, the notes' limit) «Merge all», combining both texts, on two saved cash pairs: the pair whose
 *        notes combine into exactly 500 characters is merged and saved; the pair whose notes would combine into
 *        501 is left as two rows, each with its own notes, and the editor says so — a warning and the app event
 *        `tx.bulk.promote-all.left-for-manual-merge`, `{pairs: 1}`; red until the cure, see «PC7» below.
 *
 * PC1 and PC3, the two tests whose save is refused, each prove three things: the commit's answer, read
 * against the request the editor actually sent (indexes are looked up there by id and link_uuid,
 * never assumed); that nothing was written (the owned ledger is exactly as it was before the
 * save); and that the refused-save banner's issue (`tx-bulk-error` → `tx-bulk-issue`, i.e.
 * `jumpToIssue`) highlights the pair's row — `data-highlighted`, published by DataTable's
 * `navigateToRowId` — and no other. An unrelated saved row of an earlier date sits first in every
 * grid, so "the first row" is never the right answer by accident.
 *
 * ## PC2's saved receiver: linked to a SPLIT event, and so never promoted
 *
 * A saved incoming ADJUSTMENT without a cost basis cannot be created plainly through the public
 * API: a create without one is refused with `costBasisRequired` itself (backend test B2.8); Auto
 * mode stores the computed average cost (0 for an empty pool) or refuses with `wacFxUnavailable`;
 * and an update that clears it is refused with `costBasisRequired` too (since decision P5 an
 * explicit `null` removes a cost basis: `_apply_update_values()`, `batch_edits.py`). The one such row the
 * app itself stores is an ADJUSTMENT linked to a SPLIT asset event and saved in Auto mode, whose
 * cost the engines derive from the split ratio (`_compute_wac_for_auto_items`, `is_split_linked`;
 * backend test
 * `test_forward_split_whose_adjustment_has_no_cost_is_retyped_only_once_the_adjustment_has_one` asserts
 * `cost_basis_override is None`). The form saves the same row whenever a positive ADJUSTMENT is
 * linked to a split.
 *
 * Since lot 42 (D2) a row linked to an asset event is never promoted: no promote target —
 * TRANSFER, CASH_TRANSFER, FX_CONVERSION — accepts the link (`event_compatible: false`). The
 * editor offers no merge for it: the banner, «Merge all» and the selection toolbar all ask
 * `findPromoteMatch` (`$lib/features/transactions/transactionTypeStore.ts`), and `buildPromoteCtx`
 * hands it each row's `asset_event_id`. A promote sent anyway is refused by the backend with
 * `eventTypeIncompatible` on the promote (`apply_promotes` → `_promoted_state_issues`; backend
 * test `test_promote_split_linked_adjustment_is_rejected`) and is not applied, so the saved-row
 * cost-basis check never sees it. The UI therefore has no path left to «a saved receiver without
 * a cost basis, promoted»: the one such row the public API stores is event-linked. The backend's
 * saved-row check (`_check_promoted_saved_cost_basis`, the `promote` issue with `ref_id`) is
 * reachable only through the API, by a promote whose `resolved_fields: {cost_basis_override:
 * null}` clears a saved receiver's cost basis — the editor's merge modal resolves description and
 * tags, never a cost basis. That path is covered by
 * `test_promote_saved_saved_clearing_cost_basis_is_rejected`, in the same backend file
 * (`backend/test_scripts/test_api/test_transactions_batch_split_promote.py`).
 *
 * PC2 keeps that row and its precondition check, and asserts the UI side of D2. Before lot 42 the
 * banner offered exactly this merge (the previous PC2 asserted the offer, green), so the absences
 * PC2 asserts now negate an assertion that used to pass.
 *
 * ## PC2b and PC2c: the 💡's side of D2, regression tests
 *
 * The 💡 (`tx-bulk-suggest-import`, its count in a `<span>`) offers the saved rows outside the
 * editor that the database search (`POST /transactions/promote-suggest`, `promote_suggest_bulk`)
 * proposes as the other half of a row, and opens them in the picker. The search used to ignore
 * `asset_event_id` on both sides, and so offered the pairs D2 forbids: a row the user could import
 * and never merge. Both tests were written red against that, and are green regression tests since
 * the cure:
 *   - candidate side (PC2b): a saved row linked to an asset event is never a candidate when the
 *     rule's target type refuses the link, which every promote target does;
 *   - input side (PC2c): the editor sends each row's `asset_event_id` (an optional field of
 *     `TXPromoteSuggestInput`), and a linked row gets no candidate. PC2c is the one that goes red if
 *     the editor stops sending the field while the backend still honours it.
 * Their API counterparts are B3.8–B3.10 in
 * `backend/test_scripts/test_api/test_transactions_batch_split_promote.py`.
 *
 * The answer is asynchronous (debounced, 500 ms) and `data-busy` does not cover it, so no absence
 * stands alone. Each test waits for the response to the request that asks about the row under test
 * (recognised by its body: debounced requests about other rows come first), reads the answer, and
 * anchors every absence on a twin the search must still offer. The 💡 is not shown before that
 * answer lands, since no earlier answer offers anything, so a count of exactly 1 can only come from it.
 *
 * ## PC5: the selection toolbar compared doubles (C-46), regression test
 *
 * Two paths offer an asset TRANSFER merge. The banner asks `findPromoteMatch` and
 * `assetQuantitiesCancel`, which compares the signed decimal strings exactly, as the backend's
 * `_validate_linked_pair` compares `Decimal`s. The selection toolbar (`selectedForPromote` in
 * TransactionBulkModal → `promote-toolbar-confirm`) asked `findPromoteMatch` only, whose TRANSFER rule
 * is `qA !== 0 && qA === -qB` on JavaScript numbers (`buildPromoteCtx` reads `Number(quantity)`): two
 * quantities opposite as doubles and not as decimals passed the toolbar and not the banner, and two
 * new rows merged that way were refused on save with `pairQuantityMismatch`. Since C-46 the toolbar
 * asks `assetQuantitiesCancel` too; PC5 was written red against the old behaviour.
 *
 * The pair fits the column (`Numeric(18, 6)`) and the form (12 integer digits, 6 decimals). Between
 * 2^36 and 2^37 consecutive doubles are 2^-16 ≈ 1.5e-5 apart, about 15 steps of the 6th decimal, so
 * 123456789012.123456 and 123456789012.123457 are one double (0x423CBE991A141F9B), inside the run
 * .123452–.123466 that rounds to it; neither ends on a zero the form would strip, so the text typed is
 * the text the form must keep. The test re-checks the premise in Node, whose `Number()` is the browser's.
 *
 * The positive control comes first, in the same editor: A's same −123456789012.123456 against an exact
 * +123456789012.123456 on B, one digit away from the pair under test. The banner offers it and its
 * selection shows the toolbar's merge; the banner then merges it, so that the banner is hidden again
 * and none of its rows is selected when the pair under test is typed. Nothing is saved.
 *
 * ## PC6: the 💡's window, red until the cure
 *
 * «Max Δ days» (`promote-suggest-delta-input`, a range 0–14 kept in sessionStorage, so 3 in a fresh
 * context) is the window of the banner and of the 💡's database search, which sends it as
 * `tolerance_days`. Two defects (C-47):
 *   - at 0 the endpoint answers 422 (it declares `tolerance_days` ≥ 1) and the editor only logs it,
 *     so the 💡 offers nothing, while the banner at 0 does offer same-day pairs;
 *   - moving the slider does not search again: the search key is the rows alone, and the window is
 *     read when the debounce fires, so the 💡 keeps the window of the last search until a row changes.
 * PC6 asserts the contract of the cure: 0 is the same day only (`date ± 0`), and the window is part of
 * the search key, so moving the slider starts a new, debounced search. Its first half is soft, so one
 * run reports both defects. Its API counterpart is B3.11.
 *
 * Every request is recognised by the `tolerance_days` of its URL and by the new row in its body, never
 * taken as "the next one": the opening search, about the fund alone, comes first. The new receiver is
 * Manual with no cost basis on purpose. An Auto row has its average cost written back by every
 * validation round, and until a search about the rows has succeeded, each rewrite asks again with the
 * window the slider shows when the debounce fires: a request at 1 could then come from a rewrite rather
 * than from the slider. With nothing to rewrite the rows, once the editor has settled a request at 1
 * can only come from the slider.
 *
 * ## PC7: «Merge all» never writes notes past 500 characters, red until the cure (W-B70)
 *
 * A transaction's notes hold 500 characters (`max_length=500` on a create and on a promote's
 * `resolved_fields`, counted by Python's `len()`). «Merge all» combining both texts writes `left\nright`
 * into the two rows of every pair it merges, and nothing checks the length: two notes of 250 combine into
 * 501 characters, the pair is shown merged, and the save is refused on its promote (`string_too_long`),
 * nothing saved. The decision (D-W70-4 a): such a pair is left unmerged, each row keeping its own notes —
 * no text is ever cut — and the editor says so, with a warning toast and the app event
 * `tx.bulk.promote-all.left-for-manual-merge`, `{pairs: <how many>}`, whose name and detail are what PC7
 * reads (never the toast's text); every other pair is merged as before. The limit is inclusive, and PC7
 * sits on both sides of it: the merged pair combines into exactly 500 characters and its save is asserted,
 * so a limit off by one in either direction, in the editor or against the backend, turns it red.
 *
 * Both pairs are saved rows (edit + edit: the promote carries the combined notes as `resolved_fields`),
 * each a WITHDRAWAL on A and a DEPOSIT on B of an amount no other row shares, so the banner offers exactly
 * these two pairs and «Merge all» is on offer. The notes open on words that tell the four rows apart; a
 * filler only sets their length. Today PC7 is red on the pair that must stay two rows: «Merge all» merges
 * it into one, whose notes are the 501 characters. Its save is not asserted refused: that is today's defect,
 * and the cure's save must go through.
 *
 * ## The save gate
 *
 * Save opens `tx-bulk-unseen-suggestions` instead of committing while a merge suggestion is still
 * on offer and unseen: the banner's pairs until the banner is touched, the 💡's saved
 * counterparts until it is opened. PC1 and PC3 merge every suggested pair before saving — the
 * banner, first seen on screen, is then asserted gone — and the 💡 could only offer saved rows of
 * the owned asset outside the editor, of which there are none. So Save must reach the commit:
 * `saveExpectingRefusal` waits for the refused-save banner OR the gate, and fails by name if it is
 * the gate, rather than clicking past it. In PC7 the banner still offers the pair left behind, but it
 * has been touched («Merge all» is clicked inside it), and the 💡 has nothing to offer either: every
 * owned row but the float is in the editor, the float pairs with none, and no other row of the user
 * carries the pairs' amounts. Its save, `saveExpectingCommit`, names the gate too if nothing is sent.
 *
 * ## Owned data, parallel-safe
 *
 * Each test creates its own asset and two brokers (PC2, PC2b and PC2c also a SPLIT event) through
 * the API and writes only there, so no neighbour can add a balance, an average-cost input or a
 * promote candidate (an asset TRANSFER pairs one asset only, here the owned one). Cleanup
 * force-deletes the two brokers with every row on them, then the event, then the asset — ids this
 * test created, nothing else. The day is the browser's own (the form's default date for a new row),
 * so a new row and its saved counterpart share the window of the banner and of the database search.
 *
 * Runs on the desktop project, like every transactions spec the runner registers.
 */
import {expect, test as base, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {eventSeq, waitForEvent, waitForSettled} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';

const API = '/api/v1';
const COMMIT_PATH = `${API}/transactions/commit`;
const SUGGEST_PATH = `${API}/transactions/promote-suggest`;
const TEST_PORT = process.env.TEST_PORT || '6041';
const UI_TIMEOUT = 10_000;
/** A save first lets the editor's validate round trip settle, then waits for the commit. */
const SAVE_TIMEOUT = 20_000;
/** A promote-suggest search leaves 500 ms after the change that asks it (debounced): ten debounces bound the wait for one. */
const SEARCH_TIMEOUT = 5_000;
/** The issue `_append_cost_basis_issue` writes, whatever the operation it names. */
const COST_BASIS_REQUIRED = {code: 'costBasisRequired', field: 'cost_basis_override'} as const;

type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type Money = {code: string; amount: string};
type CreateItem = {
    broker_id: number;
    asset_id?: number;
    type: string;
    date: string;
    quantity: string;
    cash?: Money;
    description?: string;
    link_uuid?: string | null;
    cost_basis_override?: Money | null;
    cost_basis_mode?: string | null;
    asset_event_id?: number;
};
type PromoteItem = {id_a?: number; id_b?: number; link_uuid_a?: string; link_uuid_b?: string; resolved_fields?: Record<string, unknown>};
type CommitRequest = {creates?: CreateItem[]; updates?: Array<{id: number}>; deletes?: number[]; splits?: unknown[]; promotes?: PromoteItem[]};
type Issue = {operation: string; index: number; ref_id?: number | null; code?: string | null; field?: string | null};
type CommitBody = {committed: boolean; issues?: Issue[]; results?: Array<{operation: string; index?: number; ids?: number[]; status?: string}>};
type LedgerRow = {id: number; broker_id: number; type: string; quantity: string; related_transaction_id: number | null; cost_basis_override: Money | null; asset_event_id: number | null; description?: string | null};
/** One row the editor asks the database search about (`TXPromoteSuggestInput`), as the editor sends it. */
type SuggestInput = {id: number; type: string; broker_id: number; date: string; asset_id?: number | null; quantity?: number | null; asset_event_id?: number | null};
/** One promote-suggest request: the rows it asked about, and the candidates per asked id (JSON keys are strings). */
type SuggestAnswer = {inputs: SuggestInput[]; results: Record<string, Array<{id: number}>>};
/** One promote-suggest exchange, however it was answered: the window in its URL, the rows it asked about, the status, and the candidates (on a 200) or the body. */
type SuggestReply = {toleranceDays: string | null; inputs: SuggestInput[]; status: number; results: SuggestAnswer['results'] | null; body: string};

type Owned = {
    suffix: string;
    /** The browser's calendar day: the date the form gives a new row. */
    today: string;
    brokerIds: number[];
    assetIds: number[];
    /** Each owned event with its asset: the events delete is scoped by asset (decision 21, I-12a). */
    events: Array<{id: number; assetId: number}>;
};
type Broker = {id: number; name: string};
type Brokers = {a: Broker; b: Broker};
type Asset = {id: number; name: string};
/** A row saved through the API: the label names it in messages, the id and the description find it. */
type Saved = {label: string; id: number; description: string};

// ---------------------------------------------------------------------------
// Owned data (API)
// ---------------------------------------------------------------------------

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

function isCommitRequest(request: {method(): string; url(): string}): boolean {
    return request.method() === 'POST' && new URL(request.url()).pathname === COMMIT_PATH;
}

function isSuggestRequest(request: {method(): string; url(): string}): boolean {
    return request.method() === 'POST' && new URL(request.url()).pathname === SUGGEST_PATH;
}

const byId = (a: number, b: number) => a - b;

/** The day before an ISO date, on the calendar: no clock involved. */
function dayBefore(isoDate: string): string {
    const day = new Date(`${isoDate}T00:00:00Z`);
    day.setUTCDate(day.getUTCDate() - 1);
    return day.toISOString().slice(0, 10);
}

/** The app's `todayIso()`, computed where the app computes it: in the browser. */
async function browserToday(page: Page): Promise<string> {
    return page.evaluate(() => {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    });
}

/** One EUR asset and two brokers only this test knows; every id is recorded for cleanup before anything can fail. */
async function ownAssetAndBrokers(page: Page, owned: Owned): Promise<{asset: Asset; brokers: Brokers}> {
    const assetName = `PCB asset ${owned.suffix}`;
    const assets = await jsonFrom<{results: Array<{asset_id: number | null; display_name: string; success: boolean}>}>(await page.request.post(`${API}/assets`, {data: [{display_name: assetName, currency: 'EUR', asset_type: 'ETF'}]}), 'create the owned asset');
    const created = assets.results.find((item) => item.display_name === assetName);
    if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`Asset creation failed: ${JSON.stringify(assets)}`);
    owned.assetIds.push(created.asset_id);

    const names = [`PCB broker A ${owned.suffix}`, `PCB broker B ${owned.suffix}`];
    const brokers = await jsonFrom<{results: Array<{broker_id: number | null; name: string; success: boolean}>}>(await page.request.post(`${API}/brokers`, {data: names.map((name) => ({name, opened_at: '2020-01-01'}))}), 'create the owned brokers');
    for (const item of brokers.results) {
        if (item.success && typeof item.broker_id === 'number' && names.includes(item.name)) owned.brokerIds.push(item.broker_id);
    }
    const [a, b] = names.map((name): Broker => {
        const id = brokers.results.find((item) => item.name === name && item.success)?.broker_id;
        if (typeof id !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(brokers)}`);
        return {id, name};
    });
    return {asset: {id: created.asset_id, name: assetName}, brokers: {a, b}};
}

/** A 2:1 SPLIT event on the owned asset, recorded the way the providers record one; returns its id. */
async function ownSplitEvent(page: Page, owned: Owned, asset: Asset, date: string): Promise<number> {
    const notes = `PCB split ${owned.suffix}`;
    await jsonFrom(await page.request.post(`${API}/assets/events`, {data: [{asset_id: asset.id, events: [{date, type: 'SPLIT', value: {code: 'EUR', amount: '2'}, notes}]}]}), 'create the owned SPLIT event');
    const queried = await jsonFrom<{items: Array<{asset_id: number; events: Array<{id: number; type: string; notes?: string | null}>}>}>(await page.request.post(`${API}/assets/events/query`, {data: [{asset_id: asset.id, date_range: {start: date, end: date}}]}), 'read the owned SPLIT event back');
    const event = queried.items.find((item) => item.asset_id === asset.id)?.events.find((candidate) => candidate.type === 'SPLIT' && candidate.notes === notes);
    if (!event) throw new Error(`The owned SPLIT event was not found: ${JSON.stringify(queried)}`);
    owned.events.push({id: event.id, assetId: asset.id});
    return event.id;
}

function adjustment(broker: Broker, asset: Asset, date: string, quantity: string, description: string, extra: Partial<CreateItem> = {}): CreateItem {
    return {broker_id: broker.id, asset_id: asset.id, type: 'ADJUSTMENT', date, quantity, description, ...extra};
}

function cashRow(broker: Broker, type: 'DEPOSIT' | 'WITHDRAWAL', date: string, amount: string, description: string): CreateItem {
    return {broker_id: broker.id, type, date, quantity: '0', cash: {code: 'EUR', amount}, description};
}

/** Notes of exactly `length` characters, all ASCII: `marker`, the words that tell a row apart, then a filler. */
function notesOf(marker: string, length: number): string {
    const notes = `${marker} ${'x'.repeat(length - marker.length - 1)}`;
    expect(notes, `notes of ${length} characters`).toHaveLength(length);
    return notes;
}

/** Commit the owned rows in one batch; returns them in the order given, each with its id. */
async function commitOwnedRows(page: Page, rows: Array<{label: string; create: CreateItem}>): Promise<Saved[]> {
    const body = await jsonFrom<CommitBody>(await page.request.post(COMMIT_PATH, {data: {creates: rows.map((row) => row.create)}}), 'commit the owned rows');
    expect(body.committed, `owned rows rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    return rows.map((row, index) => {
        const id = body.results?.find((result) => result.operation === 'create' && result.index === index && result.status === 'success')?.ids?.[0];
        if (typeof id !== 'number') throw new Error(`Owned row "${row.label}" got no id: ${JSON.stringify(body.results)}`);
        return {label: row.label, id, description: row.create.description ?? ''};
    });
}

/** Every row on the two owned brokers, by id. */
async function readOwnedLedger(page: Page, brokers: Brokers): Promise<LedgerRow[]> {
    const rows: LedgerRow[] = [];
    for (const broker of [brokers.a, brokers.b]) {
        rows.push(...(await jsonFrom<LedgerRow[]>(await page.request.get(`${API}/transactions`, {params: {broker_id: broker.id}}), `read the rows of ${broker.name}`)));
    }
    return rows.sort((x, y) => byId(x.id, y.id));
}

function ledgerShape(rows: LedgerRow[]) {
    return rows.map((row) => ({id: row.id, broker_id: row.broker_id, type: row.type, quantity: Number(row.quantity), related_transaction_id: row.related_transaction_id, cost_basis_override: row.cost_basis_override}));
}

/** The refused batch wrote nothing: same rows, each still of its own type, unlinked, with the same cost basis. */
async function expectLedgerUntouched(page: Page, brokers: Brokers, before: LedgerRow[]): Promise<void> {
    expect(ledgerShape(await readOwnedLedger(page, brokers)), 'the refused batch wrote nothing: the owned ledger is exactly as it was before the save').toEqual(ledgerShape(before));
}

/** Force-delete the owned brokers with every row on them, then the event, then the asset. */
async function cleanupOwned(page: Page, owned: Owned): Promise<void> {
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<void>) => {
        try {
            await action();
        } catch (error) {
            failures.push(`${label}: ${String(error)}`);
        }
    };
    // Leave the page first: an editor still open on these rows goes with it, unsaved.
    await attempt('leave the page', async () => {
        await page.goto('about:blank');
    });
    // The brokers first: `force` deletes every row on them (a linked half included), and only then
    // will the event and the asset go — both refuse while a transaction still points at them.
    if (owned.brokerIds.length > 0) {
        await attempt(`brokers ${owned.brokerIds.join(', ')}`, async () => {
            const query = new URLSearchParams([...owned.brokerIds.map((id) => ['ids', String(id)]), ['force', 'true']]);
            const result = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?${query}`), 'delete the owned brokers');
            for (const id of owned.brokerIds) expect(result.results.find((item) => item.id === id)?.success, `broker ${id} deleted`).toBe(true);
        });
    }
    for (const ownedEvent of owned.events) {
        await attempt(`event ${ownedEvent.id}`, async () => {
            const result = await jsonFrom<{results: Array<{event_id: number; status: string}>}>(await page.request.delete(`${API}/assets/events?asset_id=${ownedEvent.assetId}&ids=${ownedEvent.id}`), 'delete the owned event');
            expect(result.results.find((item) => item.event_id === ownedEvent.id)?.status).toBe('deleted');
        });
    }
    for (const assetId of owned.assetIds) {
        await attempt(`asset ${assetId}`, async () => {
            const result = await jsonFrom<{results: Array<{asset_id: number; success: boolean}>}>(await page.request.delete(`${API}/assets?asset_ids=${assetId}`), 'delete the owned asset');
            expect(result.results.find((item) => item.asset_id === assetId)?.success).toBe(true);
        });
    }
    expect(failures, 'every cleanup operation is scoped to ids this test created').toEqual([]);
}

const test = base.extend<{owned: Owned}>({
    owned: async ({page}, use, testInfo) => {
        const baseURL = testInfo.project.use.baseURL;
        if (!baseURL || new URL(baseURL).port !== TEST_PORT || !['localhost', '127.0.0.1'].includes(new URL(baseURL).hostname)) {
            throw new Error(`These checks write owned rows and may only run against the local test backend on port ${TEST_PORT}`);
        }
        const owned: Owned = {suffix: `pcb${testInfo.workerIndex}-${uniqueSuffix()}`, today: '', brokerIds: [], assetIds: [], events: []};
        try {
            await login(page, TEST_USER);
            owned.today = await browserToday(page);
            await use(owned);
        } finally {
            await cleanupOwned(page, owned);
        }
    },
});

test.setTimeout(90_000);

// ---------------------------------------------------------------------------
// The editor
// ---------------------------------------------------------------------------

function bulkRows(page: Page): Locator {
    return page.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]');
}

/** The editor rows carrying a description only this test wrote. */
function bulkRowsWith(page: Page, description: string): Locator {
    return bulkRows(page).filter({hasText: description});
}

/**
 * The transactions page on the two owned brokers only → tick the saved rows → Edit. Ends with
 * every one of them in the editor's grid and no form on top of it: two rows or more never
 * auto-open the form, and the form one row opens by itself (to edit that row) is closed untouched.
 */
async function openEditorOn(page: Page, brokers: Brokers, rows: Saved[]): Promise<void> {
    await navigateTo(page, `/transactions?${new URLSearchParams({broker_ids: `${brokers.a.id},${brokers.b.id}`})}`);
    const transactionsPage = page.getByTestId('transactions-page');
    await expect(transactionsPage).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(transactionsPage, 20_000);
    const table = transactionsPage.getByTestId('tx-table');
    for (const row of rows) {
        const checkbox = table.getByTestId(`dt-row-checkbox-tx-${row.id}`);
        await expect(checkbox, `${row.label} is on screen`).toBeVisible({timeout: UI_TIMEOUT});
        if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
    }
    const toolbar = transactionsPage.getByTestId('selection-toolbar');
    await expect(toolbar).toHaveAttribute('data-selected-count', String(rows.length));
    await toolbar.getByTestId('toolbar-action-edit').click();
    await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: UI_TIMEOUT});
    if (rows.length === 1) {
        // One selected row is an edit of that row: the editor opens its form on top of the grid.
        const form = page.getByTestId('tx-form-modal');
        await expect(form, 'one row opens its own form').toBeVisible({timeout: UI_TIMEOUT});
        await form.getByTestId('tx-form-cancel').click();
        await expect(form, 'closed untouched').toBeHidden({timeout: UI_TIMEOUT});
    }
    for (const row of rows) await expect(bulkRowsWith(page, row.description), `${row.label} is in the editor`).toHaveCount(1, {timeout: UI_TIMEOUT});
    await expect(page.getByTestId('tx-form-modal')).toBeHidden();
}

async function selectType(page: Page, typeCode: string): Promise<void> {
    await page.getByTestId('tx-form-type').click();
    const option = page.getByTestId(`search-select-option-${typeCode}`);
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
}

async function pickBroker(page: Page, broker: Broker): Promise<void> {
    const trigger = page.getByTestId('tx-form-broker-wrap').getByRole('combobox');
    await expect(trigger).toBeVisible({timeout: UI_TIMEOUT});
    if ((await trigger.getAttribute('aria-expanded')) !== 'true') await trigger.click();
    const option = page.getByTestId(`search-select-option-${broker.id}`);
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
    await expect(trigger).toContainText(broker.name);
}

/** The asset select searches inline: narrow it to the owned asset's unique name, then pick it by id. */
async function pickAsset(page: Page, asset: Asset): Promise<void> {
    const trigger = page.getByTestId('tx-form-asset-trigger');
    await expect(trigger).toBeVisible({timeout: UI_TIMEOUT});
    if ((await trigger.getAttribute('aria-expanded')) !== 'true') await trigger.click();
    const search = page.getByTestId('tx-form-asset-search');
    await expect(search).toBeVisible({timeout: UI_TIMEOUT});
    await search.fill(asset.name);
    const option = page.getByTestId(`search-select-option-${asset.id}`);
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
    await expect(trigger).toContainText(asset.name);
}

async function fillQuantity(page: Page, quantity: string): Promise<void> {
    const input = page.getByTestId('tx-form-quantity');
    await expect(input).toBeVisible({timeout: UI_TIMEOUT});
    await input.fill(quantity);
    await input.blur();
    await expect(input, 'the form keeps every digit typed, after its own reformatting on blur').toHaveValue(quantity);
}

/** The description lives in the collapsible optional `<details>`: read its real `open` state, never click blind. */
async function fillDescription(page: Page, text: string): Promise<void> {
    const details = page.locator('details:has([data-testid="tx-form-optional-toggle"])');
    await expect(details).toBeVisible({timeout: UI_TIMEOUT});
    if (!(await details.evaluate((element) => (element as HTMLDetailsElement).open))) await page.getByTestId('tx-form-optional-toggle').click();
    await expect(details).toHaveAttribute('open', '');
    const description = page.getByTestId('tx-form-description');
    await description.fill(text);
    await expect(description).toHaveValue(text);
}

/** Push the form's draft into the grid. */
async function applyForm(page: Page): Promise<void> {
    const apply = page.getByTestId('tx-form-save');
    await expect(apply).toBeEnabled({timeout: UI_TIMEOUT});
    await apply.click();
    await expect(page.getByTestId('tx-form-modal')).toBeHidden({timeout: UI_TIMEOUT});
}

/**
 * `+ Add row` → the form → one ADJUSTMENT pushed into the grid.
 *
 * `withoutCostBasis` is the receiver under test, NOT in Auto mode: Manual is chosen first, before
 * the form is complete enough to validate (Auto is the form's default for a positive ADJUSTMENT,
 * and an Auto validate writes the computed cost into the field), and the field is then left alone,
 * as by a user who skips it. The form's own warning (`tx-form-cost-basis-warning`: positive
 * quantity, not Auto, no amount) proves the draft is in exactly that state when it is applied.
 */
async function addAdjustment(page: Page, row: {broker: Broker; asset: Asset; quantity: string; description: string; withoutCostBasis?: boolean}): Promise<void> {
    await page.getByTestId('tx-bulk-add-row').click();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: UI_TIMEOUT});
    await selectType(page, 'ADJUSTMENT');
    const manual = page.getByTestId('tx-form-cost-basis-toggle-manual');
    if (row.withoutCostBasis) {
        await expect(manual).toBeVisible({timeout: UI_TIMEOUT});
        await manual.click();
        await expect(manual).toHaveAttribute('aria-pressed', 'true');
    }
    await pickBroker(page, row.broker);
    await pickAsset(page, row.asset);
    await fillQuantity(page, row.quantity);
    await fillDescription(page, row.description);
    if (row.withoutCostBasis) {
        await expect(manual, 'the receiver stays in Manual mode').toHaveAttribute('aria-pressed', 'true');
        await expect(page.getByTestId('tx-form-cost-basis-input-amount'), 'with no cost basis typed').toHaveValue('');
        await expect(page.getByTestId('tx-form-cost-basis-warning'), 'the form says it: Manual, positive quantity, no amount').toBeVisible();
    }
    await applyForm(page);
}

/** `+ Add row` → the form → one EUR DEPOSIT pushed into the grid. */
async function addDeposit(page: Page, row: {broker: Broker; amount: string; description: string}): Promise<void> {
    await page.getByTestId('tx-bulk-add-row').click();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: UI_TIMEOUT});
    await selectType(page, 'DEPOSIT');
    await pickBroker(page, row.broker);
    const amount = page.getByTestId('tx-form-cash-amount');
    await expect(amount).toBeVisible({timeout: UI_TIMEOUT});
    await amount.fill(row.amount);
    await amount.blur();
    await expect(amount).toHaveValue(row.amount);
    // The saved half is in EUR, and a cash transfer needs one currency on both sides.
    await expect(page.getByTestId('tx-form-cash-currency')).toHaveText('EUR');
    await fillDescription(page, row.description);
    await applyForm(page);
}

/** Bring the checkbox of every row of an ALREADY-FILTERED locator to `checked`, whatever state it starts in. */
async function selectBulkRows(rows: Locator, count: number): Promise<void> {
    await expect(rows).toHaveCount(count, {timeout: UI_TIMEOUT});
    for (let i = 0; i < count; i++) {
        const checkbox = rows.nth(i).locator('[data-testid^="dt-row-checkbox-"]');
        await expect(checkbox).toBeVisible({timeout: UI_TIMEOUT});
        if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
    }
}

/** The reverse of `selectBulkRows`: every row of an ALREADY-FILTERED locator back to `unchecked`. */
async function unselectBulkRows(rows: Locator, count: number): Promise<void> {
    await expect(rows).toHaveCount(count, {timeout: UI_TIMEOUT});
    for (let i = 0; i < count; i++) {
        const checkbox = rows.nth(i).locator('[data-testid^="dt-row-checkbox-"]');
        await expect(checkbox).toBeVisible({timeout: UI_TIMEOUT});
        if ((await checkbox.getAttribute('data-state')) !== 'unchecked') await checkbox.click();
        await expect(checkbox).toHaveAttribute('data-state', 'unchecked');
    }
}

/** The banner offers the pairs this test built, and nothing else: items 0..count-1, no item `count`. */
async function expectBannerOffers(page: Page, count: number): Promise<Locator> {
    const banner = page.getByTestId('promote-suggest-banner');
    await expect(banner).toBeVisible({timeout: UI_TIMEOUT});
    for (let i = 0; i < count; i++) await expect(banner.getByTestId(`promote-suggest-item-${i}`)).toBeVisible();
    await expect(banner.getByTestId(`promote-suggest-item-${count}`)).toHaveCount(0);
    return banner;
}

/**
 * The database search's answer to the one promote-suggest request whose rows `asks` recognises.
 * Arm it BEFORE the action that makes the editor ask.
 *
 * The 💡 derives from this answer, which leaves 500 ms after the rows settle (debounced) and which
 * `data-busy` does not cover; requests about the rows on screen earlier exist too. So the request
 * is recognised by its body, never taken as "the next one".
 */
function suggestAnswer(page: Page, asks: (inputs: SuggestInput[]) => boolean): Promise<SuggestAnswer> {
    const asked = page.waitForResponse((response) => isSuggestRequest(response.request()) && asks(response.request().postDataJSON() as SuggestInput[]), {timeout: SAVE_TIMEOUT});
    const answer = asked.then(async (response) => ({inputs: response.request().postDataJSON() as SuggestInput[], results: (await jsonFrom<{results: SuggestAnswer['results']}>(response, 'promote-suggest')).results}));
    // If the test fails before it awaits the answer, the wait must not outlive it as an unhandled rejection.
    void answer.catch(() => undefined);
    return answer;
}

/** The ids the answer offers to the row asked under `id`. */
function candidatesOf(answer: SuggestAnswer, id: number): number[] {
    return (answer.results[String(id)] ?? []).map((candidate) => candidate.id);
}

/** The answer next to what the editor asked, with this test's ids named: what a red prints, and the report keeps (`suggest answer` annotation). */
function describeSuggest(answer: SuggestAnswer, ids: Record<string, number>): string {
    const described = JSON.stringify({ids, asked: answer.inputs, results: answer.results});
    test.info().annotations.push({type: 'suggest answer', description: described});
    return described;
}

/**
 * The exchange of the one promote-suggest request whose URL asks for `tolerance_days=<toleranceDays>` and whose
 * rows `asks` recognises, however it is answered: in PC6 a refused window is the defect, not a broken test.
 * Arm it BEFORE the action that makes the editor ask. Recognised by its window and its body, like `suggestAnswer`.
 */
function suggestReply(page: Page, toleranceDays: number, asks: (inputs: SuggestInput[]) => boolean, timeout = SAVE_TIMEOUT): Promise<SuggestReply> {
    const windowOf = (request: {url(): string}) => new URL(request.url()).searchParams.get('tolerance_days');
    const asked = page.waitForResponse((response) => isSuggestRequest(response.request()) && windowOf(response.request()) === String(toleranceDays) && asks(response.request().postDataJSON() as SuggestInput[]), {timeout});
    const reply = asked.then(async (response) => {
        const body = await response.text();
        return {toleranceDays: windowOf(response.request()), inputs: response.request().postDataJSON() as SuggestInput[], status: response.status(), results: response.ok() ? (JSON.parse(body) as {results: SuggestAnswer['results']}).results : null, body};
    });
    // If the test fails before it awaits the reply, the wait must not outlive it as an unhandled rejection.
    void reply.catch(() => undefined);
    return reply;
}

/** A reply next to what the editor asked, with this test's ids named (`suggest reply` annotation). */
function describeReply(reply: SuggestReply, ids: Record<string, number>): string {
    const described = JSON.stringify({ids, tolerance_days: reply.toleranceDays, status: reply.status, asked: reply.inputs, answer: reply.results ?? reply.body});
    test.info().annotations.push({type: 'suggest reply', description: described});
    return described;
}

/**
 * «Max Δ days» to `days`. The range input is filled like any other; that the editor took the value is read
 * where the editor keeps it, in sessionStorage, written by its own effect.
 */
async function setSuggestWindow(page: Page, days: number): Promise<void> {
    const slider = page.getByTestId('promote-suggest-delta-input');
    await expect(slider).toBeVisible({timeout: UI_TIMEOUT});
    await slider.fill(String(days));
    await expect(slider).toHaveValue(String(days));
    await expect.poll(() => page.evaluate(() => sessionStorage.getItem('lf-suggest-delta-days')), {message: `the editor's window is ${days}`, timeout: UI_TIMEOUT}).toBe(String(days));
}

/**
 * Save All on a batch the backend must refuse; returns the request the editor sent and the answer.
 *
 * The save gate is handled explicitly (see the header): with every suggested pair merged, Save
 * must reach the commit. Whichever comes first — the refused-save banner or the
 * `tx-bulk-unseen-suggestions` gate — is waited for, and the gate fails the test by name.
 */
async function saveExpectingRefusal(page: Page): Promise<{request: CommitRequest; body: CommitBody}> {
    await waitForSettled(page.getByTestId('tx-bulk-modal-root'), SAVE_TIMEOUT);
    const save = page.getByTestId('tx-bulk-commit');
    await expect(save).toBeEnabled({timeout: UI_TIMEOUT});
    const answered = page.waitForResponse((response) => isCommitRequest(response.request()), {timeout: SAVE_TIMEOUT});
    // If the gate opens nothing is ever sent: the assertion below says so, and this wait must not
    // outlive the test as an unhandled rejection.
    void answered.catch(() => undefined);
    await save.click();
    const gate = page.getByTestId('tx-bulk-unseen-suggestions');
    const refused = page.getByTestId('tx-bulk-error');
    await expect(gate.or(refused), 'Save answers with the refused-save banner (or, wrongly, with the unseen-suggestions gate)').toBeVisible({timeout: SAVE_TIMEOUT});
    await expect(gate, 'Save opened the unseen-suggestions gate: a merge suggestion was still on offer, and nothing was committed').toHaveCount(0);
    const response = await answered;
    return {request: response.request().postDataJSON() as CommitRequest, body: await jsonFrom<CommitBody>(response, 'Save All')};
}

/**
 * Save All on a batch the backend must accept; returns the request the editor sent and the answer, whatever it says
 * (the caller asserts `committed` next to the answer described).
 *
 * As for `saveExpectingRefusal`, Save must reach the commit (see «The save gate» in the header). A save that sends
 * nothing names the unseen-suggestions gate if that is what stands in the way, before the wait's own timeout is
 * reported.
 */
async function saveExpectingCommit(page: Page): Promise<{request: CommitRequest; body: CommitBody}> {
    await waitForSettled(page.getByTestId('tx-bulk-modal-root'), SAVE_TIMEOUT);
    const save = page.getByTestId('tx-bulk-commit');
    await expect(save).toBeEnabled({timeout: UI_TIMEOUT});
    const answered = page.waitForResponse((response) => isCommitRequest(response.request()), {timeout: SAVE_TIMEOUT});
    // Handled below; this keeps a rejection from surfacing as unhandled before it is awaited.
    void answered.catch(() => undefined);
    await save.click();
    const response = await answered.catch(async (error: unknown): Promise<never> => {
        await expect(page.getByTestId('tx-bulk-unseen-suggestions'), 'Save opened the unseen-suggestions gate instead of committing: a merge suggestion was still on offer, unseen').toHaveCount(0);
        throw error;
    });
    return {request: response.request().postDataJSON() as CommitRequest, body: await jsonFrom<CommitBody>(response, 'Save All')};
}

/** The index, among the creates the editor sent, of the one new row a promote consumes by link_uuid. */
function consumedCreateIndex(request: CommitRequest, promote: PromoteItem): number {
    const uuids = [promote.link_uuid_a, promote.link_uuid_b].filter((uuid): uuid is string => !!uuid);
    const indices = (request.creates ?? []).flatMap((create, index) => (create.link_uuid && uuids.includes(create.link_uuid) ? [index] : []));
    expect(indices, `exactly one create carries the promote's link_uuid: ${JSON.stringify(request)}`).toHaveLength(1);
    return indices[0];
}

/**
 * The commit's answer next to what the editor sent, with this test's ids named: what a red has to
 * print, and what the report keeps on a green (`commit answer` annotation).
 */
function describeAnswer(request: CommitRequest, body: CommitBody, ids: Record<string, number>): string {
    const answer = JSON.stringify({ids, committed: body.committed, issues: body.issues ?? [], results: body.results ?? [], sent: {creates: request.creates ?? [], updates: request.updates ?? [], promotes: request.promotes ?? []}});
    test.info().annotations.push({type: 'commit answer', description: answer});
    return answer;
}

/** The refused-save banner's one issue jumps to `pairRow`, and only there. */
async function expectIssueJumpsTo(page: Page, pairRow: Locator, otherRows: Locator[]): Promise<void> {
    const issue = page.getByTestId('tx-bulk-error').getByTestId('tx-bulk-issue');
    await expect(issue, 'the refused-save banner lists the one issue').toHaveCount(1);
    await expect(pairRow, 'the pair is one row on screen').toHaveCount(1);
    for (const row of [pairRow, ...otherRows]) await expect(row).toHaveAttribute('data-highlighted', 'false');
    await issue.click();
    await expect(pairRow, 'the issue jumps to the row the pair is shown as').toHaveAttribute('data-highlighted', 'true');
    for (const row of otherRows) await expect(row, 'and to no other row').toHaveAttribute('data-highlighted', 'false');
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Bulk editor — a promoted receiver without a cost basis is refused', () => {
    test('PC1: a new receiver, Manual with no cost basis, promoted with a saved sender → create issue, pointed at the pair', async ({page, owned}) => {
        const {asset, brokers} = await ownAssetAndBrokers(page, owned);
        const transfer = `PCB transfer ${owned.suffix}`;
        // A: the position (+10, with its cost) and, the next day, the outgoing −5 that will be promoted.
        const [fund, sender] = await commitOwnedRows(page, [
            {label: 'fund', create: adjustment(brokers.a, asset, dayBefore(owned.today), '10', `PCB fund ${owned.suffix}`, {cost_basis_override: {code: 'EUR', amount: '50'}})},
            {label: 'sender', create: adjustment(brokers.a, asset, owned.today, '-5', transfer)},
        ]);
        const before = await readOwnedLedger(page, brokers);
        expect(before.map((row) => row.id)).toEqual([fund.id, sender.id].sort(byId));

        await openEditorOn(page, brokers, [fund, sender]);
        await addAdjustment(page, {broker: brokers.b, asset, quantity: '5', description: transfer, withoutCostBasis: true});
        const pairRows = bulkRowsWith(page, transfer);
        await expect(pairRows).toHaveCount(2, {timeout: UI_TIMEOUT});

        // The banner offers the pair — the presence behind the absence asserted once it is merged —
        // and the selection toolbar merges it, as tx-bulk-promote-exec PE5 does for a new + saved pair.
        const banner = await expectBannerOffers(page, 1);
        await selectBulkRows(pairRows, 2);
        await page.getByTestId('promote-toolbar-confirm').click();
        await expect(pairRows, 'the two rows collapse into one pair row').toHaveCount(1, {timeout: UI_TIMEOUT});
        await expect(banner, 'the merged pair was the only suggestion').toBeHidden();

        const {request, body} = await saveExpectingRefusal(page);
        const answer = describeAnswer(request, body, {fund: fund.id, sender: sender.id});
        expect(body.committed, `the batch must be refused — ${answer}`).toBe(false);
        const promote = (request.promotes ?? []).find((item) => item.id_a === sender.id || item.id_b === sender.id);
        expect(promote, `the saved sender is promoted — ${answer}`).toBeTruthy();
        const receiverIndex = consumedCreateIndex(request, promote!);
        const receiver = request.creates![receiverIndex];
        expect(receiver, `the new receiver is the create the promote consumes — ${answer}`).toMatchObject({broker_id: brokers.b.id, asset_id: asset.id, type: 'ADJUSTMENT', description: transfer});
        expect(Number(receiver.quantity), answer).toBe(5);
        expect(receiver.cost_basis_override ?? null, `the receiver is sent without a cost basis — ${answer}`).toBeNull();
        expect(receiver.cost_basis_mode ?? null, `and not in Auto mode — ${answer}`).toBeNull();
        expect(body.issues, `one issue: the new receiver, checked as the create it is — ${answer}`).toEqual([expect.objectContaining({...COST_BASIS_REQUIRED, operation: 'create', index: receiverIndex})]);
        expect(body.issues![0].ref_id ?? null, answer).toBeNull();

        await expectIssueJumpsTo(page, pairRows, [bulkRowsWith(page, fund.description)]);
        await expectLedgerUntouched(page, brokers, before);
    });

    test('PC2: a saved receiver linked to a SPLIT event is never offered for a merge — not by the banner, not by the selection', async ({page, owned}) => {
        const {asset, brokers} = await ownAssetAndBrokers(page, owned);
        const split = await ownSplitEvent(page, owned, asset, owned.today);
        const transfer = `PCB transfer ${owned.suffix}`;
        const [fund, receiver] = await commitOwnedRows(page, [
            {label: 'fund', create: adjustment(brokers.a, asset, dayBefore(owned.today), '10', `PCB fund ${owned.suffix}`, {cost_basis_override: {code: 'EUR', amount: '50'}})},
            // Auto on a SPLIT-linked ADJUSTMENT: the one incoming row the app stores without a cost basis (see the header).
            {label: 'receiver', create: adjustment(brokers.b, asset, owned.today, '5', transfer, {asset_event_id: split, cost_basis_mode: 'auto'})},
        ]);
        const before = await readOwnedLedger(page, brokers);
        expect(before.map((row) => row.id)).toEqual([fund.id, receiver.id].sort(byId));
        const savedReceiver = before.find((row) => row.id === receiver.id);
        expect(savedReceiver, 'precondition: an incoming ADJUSTMENT, standalone, linked to the split, saved WITHOUT a cost basis').toMatchObject({broker_id: brokers.b.id, type: 'ADJUSTMENT', related_transaction_id: null, cost_basis_override: null, asset_event_id: split});
        expect(Number(savedReceiver!.quantity)).toBe(5);

        await openEditorOn(page, brokers, [fund, receiver]);
        // The banner derives from the rows on screen, synchronously (see PC4): the saved rows alone pair with nothing.
        const banner = page.getByTestId('promote-suggest-banner');
        await expect(banner, 'the saved rows alone pair with nothing').toBeHidden();
        // A new −5 on A with the receiver's asset, day and description: it cancels the saved +5 on B exactly,
        // so the one thing standing between the two rows and a merge is the receiver's link to the split.
        await addAdjustment(page, {broker: brokers.a, asset, quantity: '-5', description: transfer});
        const pairRows = bulkRowsWith(page, transfer);
        await expect(pairRows, 'the saved receiver and the new sender are two rows').toHaveCount(2, {timeout: UI_TIMEOUT});
        await expect(banner, 'the banner offers no merge for a row linked to an asset event').toBeHidden();

        // The selection toolbar asks the same question of the same two rows. The two checked boxes are the
        // anchor: a checkbox hands the selection to the editor in its own click handler, and the promote
        // button derives from that selection, so both are drawn in the same update.
        await selectBulkRows(pairRows, 2);
        await expect(page.getByTestId('promote-toolbar-confirm'), 'nor does the selection toolbar, with both rows selected').toHaveCount(0);

        // The rows stay apart: still two, and the receiver — the half a merge would hide — has no partner.
        await expect(pairRows, 'still two rows').toHaveCount(2);
        const receiverRow = pairRows.filter({hasText: brokers.b.name});
        await expect(receiverRow, 'the saved receiver is a row of its own').toHaveCount(1);
        await expect(receiverRow.getByTestId('tx-bulk-date'), 'with no partner').toHaveAttribute('data-partner-date', '');

        // Nothing was saved: the editor is left open and discarded by the cleanup.
        await expectLedgerUntouched(page, brokers, before);
    });

    test('PC2b: the 💡 offers a new −5 its unlinked twin, never the saved receiver linked to a SPLIT event', async ({page, owned}) => {
        const {asset, brokers} = await ownAssetAndBrokers(page, owned);
        const split = await ownSplitEvent(page, owned, asset, owned.today);
        const [fund, receiver, twin] = await commitOwnedRows(page, [
            {label: 'fund', create: adjustment(brokers.a, asset, dayBefore(owned.today), '10', `PCB fund ${owned.suffix}`, {cost_basis_override: {code: 'EUR', amount: '50'}})},
            // PC2's receiver, linked to the split, and its unlinked twin: same broker, day and quantity. Both stay out of the editor.
            {label: 'linked receiver', create: adjustment(brokers.b, asset, owned.today, '5', `PCB linked ${owned.suffix}`, {asset_event_id: split, cost_basis_mode: 'auto'})},
            {label: 'twin', create: adjustment(brokers.b, asset, owned.today, '5', `PCB twin ${owned.suffix}`, {cost_basis_override: {code: 'EUR', amount: '25'}})},
        ]);
        const before = await readOwnedLedger(page, brokers);
        expect(before.map((row) => row.id)).toEqual([fund.id, receiver.id, twin.id].sort(byId));
        const savedRow = (id: number) => before.find((row) => row.id === id);
        expect(savedRow(receiver.id), 'precondition: the receiver is saved standalone, linked to the split').toMatchObject({broker_id: brokers.b.id, type: 'ADJUSTMENT', related_transaction_id: null, asset_event_id: split});
        expect(savedRow(twin.id), 'precondition: its twin is saved standalone, unlinked').toMatchObject({broker_id: brokers.b.id, type: 'ADJUSTMENT', related_transaction_id: null, asset_event_id: null});

        await openEditorOn(page, brokers, [fund]);
        // The new −5 on A is asked under a negative id the test cannot know: its request is recognised by the row.
        const isNewSender = (input: SuggestInput) => input.id < 0 && input.broker_id === brokers.a.id && input.asset_id === asset.id && Number(input.quantity) === -5;
        const answered = suggestAnswer(page, (inputs) => inputs.some(isNewSender));
        await addAdjustment(page, {broker: brokers.a, asset, quantity: '-5', description: `PCB sender ${owned.suffix}`});
        const answer = await answered;
        const senderKey = answer.inputs.find(isNewSender)!.id;
        const described = describeSuggest(answer, {fund: fund.id, linkedReceiver: receiver.id, twin: twin.id, newSender: senderKey});
        const offered = candidatesOf(answer, senderKey);
        // The positive the absences hang on: the search answers this row, and offers it the twin.
        expect(offered, `the search offers the new −5 its unlinked twin — ${described}`).toContain(twin.id);
        expect.soft(offered, `and never the receiver linked to the split — ${described}`).not.toContain(receiver.id);

        // The 💡 is not shown before this answer lands (the fund alone has no counterpart), so a count of
        // exactly 1 can only come from it: the twin, not the twin and the linked receiver.
        const bulb = page.getByTestId('tx-bulk-suggest-import');
        await expect.soft(bulb.locator('span'), 'the 💡 offers one row: the twin').toHaveText('1', {timeout: UI_TIMEOUT});
        // What it opens, by transaction id: the picker lists the twin (the presence) and not the linked receiver.
        await bulb.click();
        const picker = page.getByTestId('tx-picker-content');
        await expect(picker.locator(`tr[data-row-id="tx-${twin.id}"]`), 'the picker lists the twin').toBeVisible({timeout: UI_TIMEOUT});
        await expect(picker.locator(`tr[data-row-id="tx-${receiver.id}"]`), 'and never the linked receiver').toHaveCount(0);

        // Nothing was saved: the editor is left open and discarded by the cleanup.
        await expectLedgerUntouched(page, brokers, before);
    });

    test('PC2c: the 💡 offers a saved −5 to the unlinked twin only, never to the receiver linked to a SPLIT event', async ({page, owned}) => {
        const {asset, brokers} = await ownAssetAndBrokers(page, owned);
        const split = await ownSplitEvent(page, owned, asset, owned.today);
        const [fund, receiver, twin, sender] = await commitOwnedRows(page, [
            {label: 'fund', create: adjustment(brokers.a, asset, dayBefore(owned.today), '10', `PCB fund ${owned.suffix}`, {cost_basis_override: {code: 'EUR', amount: '50'}})},
            // In the editor: PC2's receiver, linked to the split, and its unlinked twin, the control.
            {label: 'linked receiver', create: adjustment(brokers.b, asset, owned.today, '5', `PCB linked ${owned.suffix}`, {asset_event_id: split, cost_basis_mode: 'auto'})},
            {label: 'twin', create: adjustment(brokers.b, asset, owned.today, '5', `PCB twin ${owned.suffix}`, {cost_basis_override: {code: 'EUR', amount: '25'}})},
            // Out of it: the saved −5 that both would pair with.
            {label: 'sender', create: adjustment(brokers.a, asset, owned.today, '-5', `PCB sender ${owned.suffix}`)},
        ]);
        const before = await readOwnedLedger(page, brokers);
        expect(before.map((row) => row.id)).toEqual([fund.id, receiver.id, twin.id, sender.id].sort(byId));
        const savedRow = (id: number) => before.find((row) => row.id === id);
        expect(savedRow(receiver.id), 'precondition: the receiver is saved standalone, linked to the split').toMatchObject({broker_id: brokers.b.id, type: 'ADJUSTMENT', related_transaction_id: null, asset_event_id: split});
        expect(savedRow(twin.id), 'precondition: its twin is saved standalone, unlinked').toMatchObject({broker_id: brokers.b.id, type: 'ADJUSTMENT', related_transaction_id: null, asset_event_id: null});
        expect(savedRow(sender.id), 'precondition: the −5 is saved standalone, unlinked').toMatchObject({broker_id: brokers.a.id, type: 'ADJUSTMENT', related_transaction_id: null, asset_event_id: null});

        // The editor asks about its saved rows as soon as it opens: the wait is armed first.
        const answered = suggestAnswer(page, (inputs) => [receiver.id, twin.id].every((id) => inputs.some((input) => input.id === id)));
        await openEditorOn(page, brokers, [fund, receiver, twin]);
        // Side check: nothing pairs inside the editor. The receiver and the twin share a broker, and the −5 is outside.
        await expect(page.getByTestId('promote-suggest-banner'), 'the banner offers nothing').toBeHidden();

        const answer = await answered;
        const described = describeSuggest(answer, {fund: fund.id, linkedReceiver: receiver.id, twin: twin.id, sender: sender.id});
        // The input side: the editor tells the search the receiver's link (the promote-suggest inputs of
        // TransactionBulkModal). If the editor stops sending it, this check goes red while the backend still honours it.
        expect.soft(answer.inputs.find((input) => input.id === receiver.id)?.asset_event_id ?? null, `the editor sends the receiver's link — ${described}`).toBe(split);
        // The positive the absences hang on: the twin is offered the −5.
        expect(candidatesOf(answer, twin.id), `the search offers the twin the saved −5 — ${described}`).toContain(sender.id);
        expect.soft(candidatesOf(answer, receiver.id), `and offers the linked receiver nothing — ${described}`).toEqual([]);
        // The 💡 is not shown before this answer lands, so a count of exactly 1 can only come from it: the
        // −5 offered once, to the twin, not a second time to the linked receiver.
        await expect(page.getByTestId('tx-bulk-suggest-import').locator('span'), 'the 💡 offers the −5 once: to the twin').toHaveText('1', {timeout: UI_TIMEOUT});

        // Nothing was saved: the editor is left open and discarded by the cleanup.
        await expectLedgerUntouched(page, brokers, before);
    });

    test('PC3: «Merge all» of two pairs → the one create issue points at the asset pair, not at the cash pair', async ({page, owned}) => {
        const {asset, brokers} = await ownAssetAndBrokers(page, owned);
        const transfer = `PCB transfer ${owned.suffix}`;
        const wire = `PCB wire ${owned.suffix}`;
        // The second pair is a cash one on purpose: a WITHDRAWAL and a DEPOSIT can only meet each other,
        // so the pairs «Merge all» takes do not depend on how the banner matches asset quantities —
        // which PC4 checks on its own. (The selection toolbar asks `findPromoteMatch`, which compares the
        // quantities as JavaScript numbers, then, since C-46, the exact `assetQuantitiesCancel`: see PC5.)
        const [fund, float, sender, withdrawal] = await commitOwnedRows(page, [
            {label: 'fund', create: adjustment(brokers.a, asset, dayBefore(owned.today), '10', `PCB fund ${owned.suffix}`, {cost_basis_override: {code: 'EUR', amount: '50'}})},
            {label: 'float', create: cashRow(brokers.a, 'DEPOSIT', dayBefore(owned.today), '1000', `PCB float ${owned.suffix}`)},
            {label: 'sender', create: adjustment(brokers.a, asset, owned.today, '-5', transfer)},
            {label: 'withdrawal', create: cashRow(brokers.a, 'WITHDRAWAL', owned.today, '-173', wire)},
        ]);
        const before = await readOwnedLedger(page, brokers);
        expect(before.map((row) => row.id)).toEqual([fund.id, float.id, sender.id, withdrawal.id].sort(byId));

        await openEditorOn(page, brokers, [fund, sender, withdrawal]);
        await addAdjustment(page, {broker: brokers.b, asset, quantity: '5', description: transfer, withoutCostBasis: true});
        await addDeposit(page, {broker: brokers.b, amount: '173', description: wire});
        const transferRows = bulkRowsWith(page, transfer);
        const wireRows = bulkRowsWith(page, wire);
        await expect(transferRows).toHaveCount(2, {timeout: UI_TIMEOUT});
        await expect(wireRows).toHaveCount(2, {timeout: UI_TIMEOUT});

        // Two pairs on offer, which is what makes «Merge all» appear at all.
        const banner = await expectBannerOffers(page, 2);
        await banner.getByTestId('promote-suggest-merge-all').click();
        const mergeAll = page.getByTestId('promote-all-modal');
        await expect(mergeAll).toBeVisible({timeout: UI_TIMEOUT});
        await mergeAll.getByTestId('promote-all-confirm').click();
        await expect(mergeAll).toBeHidden({timeout: UI_TIMEOUT});
        await expect(transferRows, 'the asset pair is one row').toHaveCount(1, {timeout: UI_TIMEOUT});
        await expect(wireRows, 'the cash pair is one row').toHaveCount(1, {timeout: UI_TIMEOUT});
        await expect(banner, 'both suggestions are merged').toBeHidden();

        const {request, body} = await saveExpectingRefusal(page);
        const answer = describeAnswer(request, body, {fund: fund.id, float: float.id, sender: sender.id, withdrawal: withdrawal.id});
        expect(body.committed, `the batch must be refused — ${answer}`).toBe(false);
        const promotes = request.promotes ?? [];
        expect(promotes, `«Merge all» sends one promote per pair — ${answer}`).toHaveLength(2);
        const transferPromote = promotes.find((item) => item.id_a === sender.id || item.id_b === sender.id);
        const wirePromote = promotes.find((item) => item.id_a === withdrawal.id || item.id_b === withdrawal.id);
        expect(transferPromote, `the saved sender is promoted — ${answer}`).toBeTruthy();
        expect(wirePromote, `the saved withdrawal is promoted — ${answer}`).toBeTruthy();
        const receiverIndex = consumedCreateIndex(request, transferPromote!);
        const depositIndex = consumedCreateIndex(request, wirePromote!);
        const receiver = request.creates![receiverIndex];
        expect(receiver, `the new receiver is the create the asset promote consumes — ${answer}`).toMatchObject({broker_id: brokers.b.id, asset_id: asset.id, type: 'ADJUSTMENT', description: transfer});
        expect(Number(receiver.quantity), answer).toBe(5);
        expect(receiver.cost_basis_override ?? null, `the receiver is sent without a cost basis — ${answer}`).toBeNull();
        expect(receiver.cost_basis_mode ?? null, `and not in Auto mode — ${answer}`).toBeNull();
        expect(request.creates![depositIndex], `the new deposit is the create the cash promote consumes — ${answer}`).toMatchObject({broker_id: brokers.b.id, type: 'DEPOSIT', description: wire, cash: {code: 'EUR'}});
        expect(body.issues, `one issue: the asset receiver; the cash pair is valid — ${answer}`).toEqual([expect.objectContaining({...COST_BASIS_REQUIRED, operation: 'create', index: receiverIndex})]);

        await expectIssueJumpsTo(page, transferRows, [bulkRowsWith(page, fund.description), wireRows]);
        await expectLedgerUntouched(page, brokers, before);
    });

    test('PC4: the banner offers a new +5 the saved −5 it cancels, never the saved −3 beside it', async ({page, owned}) => {
        const {asset, brokers} = await ownAssetAndBrokers(page, owned);
        const exact = `PCB exact ${owned.suffix}`;
        const short = `PCB short ${owned.suffix}`;
        // A: the position, then two saved outgoing legs of the same asset on the same day, −3 and −5.
        const [fund, shortLeg, exactLeg] = await commitOwnedRows(page, [
            {label: 'fund', create: adjustment(brokers.a, asset, dayBefore(owned.today), '10', `PCB fund ${owned.suffix}`, {cost_basis_override: {code: 'EUR', amount: '50'}})},
            {label: 'saved −3', create: adjustment(brokers.a, asset, owned.today, '-3', short)},
            {label: 'saved −5', create: adjustment(brokers.a, asset, owned.today, '-5', exact)},
        ]);
        const before = await readOwnedLedger(page, brokers);
        expect(before.map((row) => row.id)).toEqual([fund.id, shortLeg.id, exactLeg.id].sort(byId));

        await openEditorOn(page, brokers, [fund, shortLeg, exactLeg]);
        // The banner derives from the rows on screen, synchronously: with the saved rows alone — all on
        // broker A — there is nothing to offer.
        const banner = page.getByTestId('promote-suggest-banner');
        await expect(banner, 'the saved rows alone pair with nothing').toBeHidden();
        // A new +5 on B, with the −5's description: taking the −5's merge then needs no merge modal.
        await addAdjustment(page, {broker: brokers.b, asset, quantity: '5', description: exact});
        const exactRows = bulkRowsWith(page, exact);
        const shortRow = bulkRowsWith(page, short);
        await expect(exactRows, 'the saved −5 and the new +5 are two rows').toHaveCount(2, {timeout: UI_TIMEOUT});
        await expect(shortRow).toHaveCount(1);

        // Both saved legs are opposite in sign to the new +5, and only the −5 cancels it: one merge on
        // offer, so nothing for «Merge all» either. A banner item names its rows only in translated text,
        // so which pair it is gets proven by taking it.
        await expectBannerOffers(page, 1);
        await expect(banner.getByTestId('promote-suggest-merge-all'), 'one pair: no «Merge all»').toHaveCount(0);
        await banner.getByTestId('promote-suggest-link-0').click();
        await expect(exactRows, 'the offered merge was the −5 one: the +5 joined it into one pair row').toHaveCount(1, {timeout: UI_TIMEOUT});
        await expect(exactRows.getByTestId('tx-bulk-date'), 'the −5 row now carries its partner').toHaveAttribute('data-partner-date', /^\d{4}-\d{2}-\d{2}$/);
        await expect(shortRow.getByTestId('tx-bulk-date'), 'the −3 is still on its own').toHaveAttribute('data-partner-date', '');
        await expect(banner, 'and nothing is offered for the −3').toBeHidden();

        // Nothing was saved: the editor is left open and discarded by the cleanup.
        await expectLedgerUntouched(page, brokers, before);
    });

    test('PC5: two new legs opposite as doubles, not as decimals → no merge from the banner, none from the selection toolbar', async ({page, owned}) => {
        // A's leg is the same in both pairs. B's cancels it exactly in the control, and one digit off in the
        // 6th decimal in the pair under test: one double all the same (see «PC5» in the header).
        const out = '-123456789012.123456';
        const exactIn = '123456789012.123456';
        const nearIn = '123456789012.123457';
        expect(out, 'premise: the control is exactly opposite as decimals').toBe(`-${exactIn}`);
        expect(out, 'premise: the pair under test is not').not.toBe(`-${nearIn}`);
        expect(Number(out), 'premise: yet it is opposite as doubles, the comparison findPromoteMatch makes').toBe(-Number(nearIn));

        const {asset, brokers} = await ownAssetAndBrokers(page, owned);
        const exact = `PCB exact ${owned.suffix}`;
        const near = `PCB near ${owned.suffix}`;
        // The editor opens on A's fund, the earlier unrelated row. It does not cover A's legs, and the editor says
        // so (A's holdings would go negative): balances play no part in what the banner or the toolbar offers, and
        // nothing is saved.
        const [fund] = await commitOwnedRows(page, [{label: 'fund', create: adjustment(brokers.a, asset, dayBefore(owned.today), '10', `PCB fund ${owned.suffix}`, {cost_basis_override: {code: 'EUR', amount: '50'}})}]);
        const before = await readOwnedLedger(page, brokers);
        expect(before.map((row) => row.id)).toEqual([fund.id]);

        await openEditorOn(page, brokers, [fund]);
        const banner = page.getByTestId('promote-suggest-banner');
        const promote = page.getByTestId('promote-toolbar-confirm');

        // The positive control, typed through the same form: the banner offers it, and so does the toolbar.
        await addAdjustment(page, {broker: brokers.a, asset, quantity: out, description: exact});
        await addAdjustment(page, {broker: brokers.b, asset, quantity: exactIn, description: exact});
        const exactRows = bulkRowsWith(page, exact);
        await expect(exactRows, 'the control is two rows').toHaveCount(2, {timeout: UI_TIMEOUT});
        await expectBannerOffers(page, 1);
        await selectBulkRows(exactRows, 2);
        await expect(promote, 'the control: the selection toolbar offers the merge of two legs that cancel exactly').toBeVisible();
        // Unselected before the banner merges them: the merged row, still selected, would be a third row in the
        // selection below, and the toolbar asks about two rows only.
        await unselectBulkRows(exactRows, 2);
        await banner.getByTestId('promote-suggest-link-0').click();
        await expect(exactRows, 'the banner offered the control: its two rows are now one pair row').toHaveCount(1, {timeout: UI_TIMEOUT});
        await expect(banner, 'and it has nothing else to offer').toBeHidden();

        // The pair under test, typed through the form: addAdjustment reads each quantity back after the blur
        // (fillQuantity), and Apply is enabled only for a quantity within the form's 12 + 6 digits (applyForm).
        await addAdjustment(page, {broker: brokers.a, asset, quantity: out, description: near});
        await addAdjustment(page, {broker: brokers.b, asset, quantity: nearIn, description: near});
        const nearRows = bulkRowsWith(page, near);
        await expect(nearRows, 'the pair under test is two rows').toHaveCount(2, {timeout: UI_TIMEOUT});
        // Side check, the exact one: the banner derives from the rows on screen, synchronously (see PC4), and
        // compares the decimal strings.
        await expect(banner, 'the banner offers no merge: the two legs differ in the 6th decimal').toBeHidden();

        // The selection is exactly the two legs: their boxes checked, the anchor as in PC2, and no other.
        await selectBulkRows(nearRows, 2);
        for (const other of [bulkRowsWith(page, fund.description), exactRows]) await expect(other.locator('[data-testid^="dt-row-checkbox-"]'), 'no other row is selected').toHaveAttribute('data-state', 'unchecked');
        await expect(promote, `nor does the selection toolbar: Number() makes ${out} and ${nearIn} one double, and the save would be refused (pairQuantityMismatch)`).toHaveCount(0);
        await expect(nearRows, 'the two legs stay apart').toHaveCount(2);

        // Nothing was saved: the editor is left open and discarded by the cleanup.
        await expectLedgerUntouched(page, brokers, before);
    });

    test('PC6: the 💡 searches the window of «Max Δ days» — at 0 the same day only, and moving the slider searches again', async ({page, owned}) => {
        const {asset, brokers} = await ownAssetAndBrokers(page, owned);
        const yesterday = dayBefore(owned.today);
        // A: the position, then the two saved senders the 💡 may offer, yesterday and today. Only the fund goes into the editor.
        const [fund, sentYesterday, sentToday] = await commitOwnedRows(page, [
            {label: 'fund', create: adjustment(brokers.a, asset, dayBefore(yesterday), '20', `PCB fund ${owned.suffix}`, {cost_basis_override: {code: 'EUR', amount: '50'}})},
            {label: 'sent yesterday', create: adjustment(brokers.a, asset, yesterday, '-5', `PCB sent yesterday ${owned.suffix}`)},
            {label: 'sent today', create: adjustment(brokers.a, asset, owned.today, '-5', `PCB sent today ${owned.suffix}`)},
        ]);
        const before = await readOwnedLedger(page, brokers);
        expect(before.map((row) => row.id)).toEqual([fund.id, sentYesterday.id, sentToday.id].sort(byId));

        // The senders can reach the editor only through the 💡, and the opening search, about the fund alone at the
        // default window, offers nothing: the fund has no counterpart.
        await openEditorOn(page, brokers, [fund]);
        const bulbCount = page.getByTestId('tx-bulk-suggest-import').locator('span');
        await setSuggestWindow(page, 0);

        // The new +5 on B is asked under a negative id the test cannot know: its request is recognised by the row.
        // Manual with no cost basis, so that no validation round rewrites it (see «PC6» in the header).
        const isNewReceiver = (input: SuggestInput) => input.id < 0 && input.broker_id === brokers.b.id && input.asset_id === asset.id && Number(input.quantity) === 5;
        const atZero = suggestReply(page, 0, (inputs) => inputs.some(isNewReceiver));
        await addAdjustment(page, {broker: brokers.b, asset, quantity: '5', description: `PCB receiver ${owned.suffix}`, withoutCostBasis: true});
        const zero = await atZero;
        const key = zero.inputs.find(isNewReceiver)!.id;
        const ids = {fund: fund.id, sentYesterday: sentYesterday.id, sentToday: sentToday.id, newReceiver: key};
        const offered = (reply: SuggestReply) => ({status: reply.status, candidates: reply.results ? (reply.results[String(key)] ?? []).map((candidate) => candidate.id).sort(byId) : null});

        // 1. At 0, the same day only: today's sender, the presence yesterday's absence hangs on. Soft, so that the
        //    slider's half below runs and reports too.
        expect.soft(offered(zero), `tolerance_days=0 is the same day only, the new contract (C-47): the search answers 200 and offers the new +5 today's sender alone — ${describeReply(zero, ids)}`).toEqual({status: 200, candidates: [sentToday.id]});
        // The opening search offered nothing, so a count of exactly 1 can only come from this answer.
        await expect.soft(bulbCount, 'the 💡 offers that one sender').toHaveText('1', {timeout: UI_TIMEOUT});

        // 2. Moving the slider searches again: the same rows, the new window. Moved once the editor has settled, when
        //    nothing else is left to ask the search anything, so that a request at 1 can only come from the slider.
        await waitForSettled(page.getByTestId('tx-bulk-modal-root'), SAVE_TIMEOUT);
        const atOne = suggestReply(page, 1, (inputs) => inputs.some(isNewReceiver), SEARCH_TIMEOUT);
        await setSuggestWindow(page, 1);
        const one = await atOne.catch(() => null);
        expect(one, `moving the slider must start a search: no promote-suggest request with tolerance_days=1 about these rows went out within ${SEARCH_TIMEOUT} ms`).not.toBeNull();
        expect(one!.inputs, 'the same rows, asked again with the new window').toEqual(zero.inputs);
        expect(offered(one!), `tolerance_days=1 reaches yesterday: the search offers the new +5 both senders — ${describeReply(one!, ids)}`).toEqual({status: 200, candidates: [sentYesterday.id, sentToday.id].sort(byId)});
        // The count stood at 1 before this answer, so 2 can only come from it.
        await expect(bulbCount, 'the 💡 offers both senders').toHaveText('2', {timeout: UI_TIMEOUT});

        // Nothing was saved: the editor is left open and discarded by the cleanup.
        await expectLedgerUntouched(page, brokers, before);
    });

    test('PC7: «Merge all», combining both texts, merges the pair whose notes fit in 500 characters and leaves the other two rows, each with its own notes (W-B70)', async ({page, owned}) => {
        // The owned asset is not used: the brokers come with it.
        const {brokers} = await ownAssetAndBrokers(page, owned);
        const fitsMark = `PCB fits ${owned.suffix}`;
        const overMark = `PCB over ${owned.suffix}`;
        const fits = {out: notesOf(`${fitsMark} out`, 250), in: notesOf(`${fitsMark} in`, 249)};
        const over = {out: notesOf(`${overMark} out`, 250), in: notesOf(`${overMark} in`, 250)};
        expect(`${fits.out}\n${fits.in}`, 'premise: one pair’s notes combine into exactly 500 characters').toHaveLength(500);
        expect(`${over.out}\n${over.in}`, 'premise: the other’s into 501').toHaveLength(501);
        // A: the float (the day before, in no pair), then each pair's withdrawal; B: each pair's deposit. Each pair has an amount of its own.
        const [float, fitsOut, fitsIn, overOut, overIn] = await commitOwnedRows(page, [
            {label: 'float', create: cashRow(brokers.a, 'DEPOSIT', dayBefore(owned.today), '1000', `PCB float ${owned.suffix}`)},
            {label: 'fits out', create: cashRow(brokers.a, 'WITHDRAWAL', owned.today, '-137.31', fits.out)},
            {label: 'fits in', create: cashRow(brokers.b, 'DEPOSIT', owned.today, '137.31', fits.in)},
            {label: 'over out', create: cashRow(brokers.a, 'WITHDRAWAL', owned.today, '-248.69', over.out)},
            {label: 'over in', create: cashRow(brokers.b, 'DEPOSIT', owned.today, '248.69', over.in)},
        ]);
        const before = await readOwnedLedger(page, brokers);
        expect(before.map((row) => row.id)).toEqual([float.id, fitsOut.id, fitsIn.id, overOut.id, overIn.id].sort(byId));

        await openEditorOn(page, brokers, [fitsOut, fitsIn, overOut, overIn]);
        const fitsRows = bulkRowsWith(page, fitsMark);
        const overRows = bulkRowsWith(page, overMark);
        await expect(fitsRows, 'one pair is two rows').toHaveCount(2, {timeout: UI_TIMEOUT});
        await expect(overRows, 'and so is the other').toHaveCount(2, {timeout: UI_TIMEOUT});

        // Two pairs on offer, which is what makes «Merge all» appear; combining both texts is its default.
        const banner = await expectBannerOffers(page, 2);
        await banner.getByTestId('promote-suggest-merge-all').click();
        const mergeAll = page.getByTestId('promote-all-modal');
        await expect(mergeAll).toBeVisible({timeout: UI_TIMEOUT});
        await expect(mergeAll.getByTestId('promote-all-choice-merge').getByRole('radio'), 'combining both texts, the default').toBeChecked();
        const since = await eventSeq(page);
        await mergeAll.getByTestId('promote-all-confirm').click();
        await expect(mergeAll).toBeHidden({timeout: UI_TIMEOUT});

        // The pair whose notes fit is merged, as before: one row, with its partner, showing both texts.
        await expect(fitsRows, 'the pair whose notes combine into exactly 500 characters is merged into one row').toHaveCount(1, {timeout: UI_TIMEOUT});
        await expect(fitsRows.getByTestId('tx-bulk-date'), 'with its partner').toHaveAttribute('data-partner-date', owned.today);
        await expect(fitsRows, 'showing both texts').toContainText(`${fitsMark} out`);
        await expect(fitsRows).toContainText(`${fitsMark} in`);

        // The pair whose notes would not fit stays two rows, each with its own notes, whole. Today's red: «Merge all»
        // merges every pair, this one into a row whose notes are the 501 characters.
        await expect(overRows, 'the pair whose notes would combine into 501 characters stays two rows, unmerged').toHaveCount(2, {timeout: UI_TIMEOUT});
        for (const [notes, otherMark] of [
            [over.out, `${overMark} in`],
            [over.in, `${overMark} out`],
        ]) {
            const row = bulkRowsWith(page, notes);
            await expect(row, 'a row keeps its own notes, whole').toHaveCount(1);
            await expect(row, 'and only its own').not.toContainText(otherMark);
            await expect(row.getByTestId('tx-bulk-date'), 'with no partner').toHaveAttribute('data-partner-date', '');
        }

        // The editor says so: the app event counts the pairs left for a manual merge, and the user gets a warning.
        const leftBehind = await waitForEvent(page, 'tx.bulk.promote-all.left-for-manual-merge', {since});
        expect(leftBehind.detail, 'one pair left for a manual merge').toMatchObject({pairs: 1});
        await expect(page.getByTestId('toast-warning'), 'and a warning on screen').toBeVisible();
        // Left for a manual merge, not dropped: the banner still offers that pair, alone.
        await expectBannerOffers(page, 1);

        // Save: the merged pair is the one promote, its notes the 500 characters, and the batch is saved.
        const {request, body} = await saveExpectingCommit(page);
        const answer = describeAnswer(request, body, {float: float.id, fitsOut: fitsOut.id, fitsIn: fitsIn.id, overOut: overOut.id, overIn: overIn.id});
        expect(body.committed, `the batch is saved — ${answer}`).toBe(true);
        const promotes = request.promotes ?? [];
        expect(
            promotes.map((item) => [item.id_a ?? 0, item.id_b ?? 0].sort(byId)),
            `one promote, the fitting pair's — ${answer}`,
        ).toEqual([[fitsOut.id, fitsIn.id].sort(byId)]);
        const combined = promotes[0].resolved_fields?.description;
        expect([`${fits.out}\n${fits.in}`, `${fits.in}\n${fits.out}`], `its notes are both texts, one per line: the 500 characters — ${answer}`).toContain(combined);
        await expect(page.getByTestId('tx-bulk-modal'), 'a saved batch closes the editor').toBeHidden({timeout: UI_TIMEOUT});

        // What the database holds: the merged pair linked, with the combined notes; the other two rows as they were.
        const after = await readOwnedLedger(page, brokers);
        const savedRow = (id: number) => after.find((row) => row.id === id);
        expect(savedRow(fitsOut.id), 'the merged pair is a Cash Transfer, linked, with the combined notes').toMatchObject({type: 'CASH_TRANSFER', related_transaction_id: fitsIn.id, description: combined});
        expect(savedRow(fitsIn.id), 'on both legs').toMatchObject({type: 'CASH_TRANSFER', related_transaction_id: fitsOut.id, description: combined});
        expect(savedRow(overOut.id), 'the pair left behind is as it was: the withdrawal, unlinked, its own notes whole').toMatchObject({type: 'WITHDRAWAL', related_transaction_id: null, description: over.out});
        expect(savedRow(overIn.id), 'and the deposit, unlinked, its own notes whole').toMatchObject({type: 'DEPOSIT', related_transaction_id: null, description: over.in});
    });
});
