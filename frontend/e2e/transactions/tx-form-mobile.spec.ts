/**
 * The transaction form on an Android-sized phone (lane 66, lot TL-1d).
 *
 * What the developer saw on a ~412 px phone:
 *
 *   (a) The read-only view of a saved BUY of an asset with a long name (`TransactionFormModal mode="view"`, a row
 *       double-clicked on the Transactions page): the content runs past the right edge (type, cash currency, asset,
 *       broker, the «ID · Created … · Updated …» footer). And, in view only, the quantity was empty and the amount showed
 *       the raw signed value (`-1234.56`) with the danger border — the view showed raw values and ran the checks, the
 *       edit form did not.
 *   (b) The date field of the New and Edit forms cut («2026-11-2…»): below 768 px `app.css` forces 16 px on every
 *       input (iOS zoom guard), and `SingleDatePicker`'s input is monospace in a half-width column.
 *   (c) A «+ Fee» charge in the linked charges section of a New BUY: below `sm` the trash button wraps alone onto its
 *       own line, between the amount and the note. It belongs on the title line, right-aligned.
 *   (d) Guard at 1280 px: the charge row keeps title, amount and buttons on one line; the view shows the same values.
 *   (e) A saved BUY with its saved FEE (seeded linked, `../fixtures/linked-charges.ts`), opened in the Bulk edit form at
 *       320 and 360 px: the FEE's three buttons (Open, Unlink, trash) sit on its title line, right-aligned — with
 *       `flex-wrap` the buttons may wrap before the title gives up room.
 *   (f) The Transactions page, a saved BUY with its FEE (`seedLinkedBuy`), opened in view at 412 and 375 px: the amount as
 *       its magnitude and the quantity, no invalid mark and no hint, no sideways overflow, the read-only charges section
 *       listing the FEE.
 *   (g) The same from a broker's Transactions tab on a fresh page (P-18 was met there): `GET /transactions/types` is held
 *       by the test until the view is open, so the form opens without type rules, as on a cold page and a slow network;
 *       the checks of (f), the amount and quantity hard and retried (the rebuild after the rules arrive).
 *
 * Measured, never looked at: `scrollWidth` against `clientWidth`, boxes against the viewport, vertical centres of the
 * charge row's parts, and the values of the inputs read as numbers. The verdict never reads a translated word.
 *
 * Hooks relied on: transactions-page[data-busy] · tx-table tbody tr[data-row-id="tx-<id>"] · tx-desc-<id> ·
 * tx-form-modal · tx-form-modal-root[data-busy] · tx-form-body · tx-form-save · tx-form-close · tx-form-asset-trigger ·
 * tx-form-quantity[aria-invalid][aria-describedby] · tx-form-cash-amount[aria-invalid] · [data-cell-invalid] ·
 * tx-form-quantity-significant-error · tx-form-cash-significant-error · tx-form-cash-hint · tx-form-cash-derived ·
 * tx-form-readonly-footer · tx-form-date-wrap ·
 * tx-add-button · row-actions-* · context-menu-action-edit · tx-bulk-modal · tx-form-charges ·
 * tx-form-charges-add-FEE · tx-form-charge-row[data-charge-id=""][data-charge-type] · tx-form-charge-remove-<key> ·
 * tx-form-charge-cash-<key>-amount · tx-form-charge-title · tx-form-charge-open-/unlink-<key> · broker-detail-page ·
 * broker-tab-transazioni · broker-transactions-tab · broker-transactions.
 *
 * Hooks this spec asks the product for (missing today, so a red on them is partly the missing hook):
 *   - `tx-form-charge-title` — the type label of a charge row. Until it exists the measure falls back to the first
 *     element of the row's first line, so the geometry is still reported; a soft check names the missing hook.
 *   - the date input of the form has no testid (`TxFormSingleSection` passes none to `SingleDatePicker`), so it is
 *     found as the one textbox inside `tx-form-date-wrap`.
 *   - the quantity's entry hint has no testid: it is found by the id its input names in `aria-describedby`.
 *   - the cash cell's sign state (the red border of a negative amount) is a CSS class only, no attribute: the spec
 *     asserts the cause (no leading minus) instead.
 *
 * Every test works on an account of its own (a disposable user, a broker it owns, an asset with a long name it creates,
 * an EUR DEPOSIT and a BUY). The afterEach deletes the brokers (`force` takes their rows), the asset, then the account.
 */
import {writeFileSync} from 'node:fs';
import type {TestInfo} from '@playwright/test';
import {expect, test, type APIRequestContext, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {createOwnedBroker} from '../fixtures/onboarding-accounts';
import {cleanupOwnedAccount, commitCreates, emptyOwnedAccount, jsonFrom, openOwnedAccount, readTransactions, type OwnedAccount} from '../fixtures/owned-pair';
import {measureSidewaysOverflow} from '../fixtures/phone-overflow';
import {readByIds, seedLinkedBuy, type LinkedBuy} from '../fixtures/linked-charges';

const API = '/api/v1';
const PHONE_HEIGHT = 812;
const DESKTOP = {width: 1280, height: 720};
/** The widths of the developer's phone (~412) and of the common small phones. */
const VIEW_WIDTHS = [412, 375] as const;
/** 640: the narrowest two-column width (`sm`) still under the 16 px zoom guard of app.css (below 768). */
const DATE_WIDTHS = [320, 360, 375, 412, 640] as const;
/** A saved charge's three buttons (Open, Unlink, trash) need the most room on the title line. */
const SAVED_CHARGE_WIDTHS = [320, 360] as const;
const CHARGE_WIDTHS = [412, 375] as const;

/** A BUY like the one in the report: 10 units for 1234.56 EUR. */
const BUY_QUANTITY = 10;
const BUY_CASH = 1234.56;
/** Same line: the vertical centres of two boxes on one flex line, ± this many px. */
const SAME_LINE_PX = 4;

type Seed = {assetId: number; assetName: string; buyId: number; buyDate: string};

// ---------------------------------------------------------------------------
// Setup and cleanup
// ---------------------------------------------------------------------------

/** A disposable account with a broker, an EUR asset with a long name, an EUR DEPOSIT and the BUY, read back by id. */
async function seedLongNamedBuy(page: Page, request: APIRequestContext, owned: OwnedAccount, assetIds: number[], tag: string): Promise<Seed> {
    await openOwnedAccount(page, request, owned, tag);
    const broker = await createOwnedBroker(page, tag, owned.brokerIds);

    const assetName = `Global Momentum Equity Long Name UCITS ETF Accumulating ${uniqueSuffix()}`;
    const created = await jsonFrom<{results: Array<{asset_id: number | null; display_name: string; success: boolean; message?: string}>}>(await page.request.post(`${API}/assets`, {data: [{display_name: assetName, currency: 'EUR', asset_type: 'ETF'}]}), 'create the long-named asset');
    const mine = created.results.find((item) => item.display_name === assetName);
    if (typeof mine?.asset_id === 'number') assetIds.push(mine.asset_id);
    if (!mine?.success || typeof mine.asset_id !== 'number') throw new Error(`The asset ${assetName} was not created: ${mine?.message ?? 'missing result'}`);

    const buyDate = daysAgoIso(9);
    await commitCreates(page, [{broker_id: broker.id, type: 'DEPOSIT', date: daysAgoIso(10), cash: {code: 'EUR', amount: '5000'}, description: `Deposit ${assetName}`}], 'fund the broker in EUR');
    const [buyId] = await commitCreates(page, [{broker_id: broker.id, asset_id: mine.asset_id, type: 'BUY', date: buyDate, quantity: String(BUY_QUANTITY), cash: {code: 'EUR', amount: `-${BUY_CASH}`}, description: `Buy ${assetName}`}], 'the BUY of the long-named asset');

    // The premise, read back rather than inferred: the server holds 10 units for -1234.56 EUR.
    const buy = (await readTransactions(page, {broker_id: broker.id})).find((tx) => tx.id === buyId);
    expect(Number(buy?.quantity), `premise: the BUY holds ${BUY_QUANTITY} units (${JSON.stringify(buy)})`).toBe(BUY_QUANTITY);
    expect(Number(buy?.cash?.amount), `premise: the BUY paid -${BUY_CASH} EUR (${JSON.stringify(buy)})`).toBe(-BUY_CASH);
    return {assetId: mine.asset_id, assetName, buyId, buyDate};
}

/** Brokers first (`force` takes their rows), then the asset — the account must still be signed in — then the account. */
async function cleanup(page: Page, request: APIRequestContext, owned: OwnedAccount, assetIds: number[]): Promise<void> {
    if (!owned.user) return;
    try {
        await page.goto('about:blank');
        for (const id of [...owned.brokerIds]) {
            const result = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?ids=${id}&force=true`), `delete the owned broker ${id}`);
            if (result.results.find((item) => item.id === id)?.success) owned.brokerIds = owned.brokerIds.filter((other) => other !== id);
        }
        for (const id of assetIds) {
            const result = await jsonFrom<{results: Array<{asset_id: number; success: boolean; message?: string}>}>(await page.request.delete(`${API}/assets?asset_ids=${id}`), `delete the owned asset ${id}`);
            const mine = result.results.find((item) => item.asset_id === id);
            expect(mine?.success, `owned asset ${id} deleted: ${mine?.message ?? 'missing result'}`).toBe(true);
        }
    } finally {
        await cleanupOwnedAccount(page, request, owned);
    }
}

// ---------------------------------------------------------------------------
// Navigation
// ---------------------------------------------------------------------------

/** Resize, and prove the page took the width before anything is measured. */
async function setWidth(page: Page, width: number, height = PHONE_HEIGHT): Promise<void> {
    await page.setViewportSize({width, height});
    await expect.poll(() => page.evaluate(() => window.innerWidth), {message: `the page is ${width} px wide`}).toBe(width);
}

/** The table narrowed to one transaction, ending with that row on screen. */
async function goToTransaction(page: Page, txId: number): Promise<Locator> {
    await navigateTo(page, `/transactions?id_min=${txId}&id_max=${txId}`);
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    const row = page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="tx-${txId}"]`);
    await expect(row, `transaction ${txId} must be on screen`).toBeVisible({timeout: 10_000});
    return row;
}

/** Double-click the row: the read-only view, loaded, showing the long asset name. */
async function openView(page: Page, seed: Seed): Promise<Locator> {
    const row = await goToTransaction(page, seed.buyId);
    await row.getByTestId(`tx-desc-${seed.buyId}`).dblclick();
    const form = page.getByTestId('tx-form-modal');
    await expect(form).toBeVisible({timeout: 8_000});
    await expect(form.getByTestId('tx-form-save'), 'view mode: nothing to save').toBeHidden();
    await waitForSettled(form.getByTestId('tx-form-modal-root'), 15_000);
    await expect(form.getByTestId('tx-form-asset-trigger'), 'the view shows the long asset name').toContainText(seed.assetName, {timeout: 10_000});
    await expect(form.getByTestId('tx-form-readonly-footer'), 'the view shows its id footer').toBeVisible();
    return form;
}

/** «+ New» on the Transactions page: the Bulk opens with its row form on top (a BUY by default). */
async function openNewForm(page: Page): Promise<Locator> {
    await navigateTo(page, '/transactions');
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    await page.getByTestId('tx-add-button').click();
    await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 8_000});
    const form = page.getByTestId('tx-form-modal');
    await expect(form, '«+ New» auto-opens the form').toBeVisible({timeout: 8_000});
    await expect(form.getByTestId('tx-form-save'), 'the New form is editable').toBeVisible({timeout: 8_000});
    return form;
}

/** Row action ⋮ → Edit on the table: the Bulk opens with that one row's form on top. */
async function openEditForm(page: Page, txId: number): Promise<Locator> {
    const row = await goToTransaction(page, txId);
    await row.hover();
    const kebab = row.getByTestId(/^row-actions-/);
    await expect(kebab).toBeVisible({timeout: 5_000});
    await kebab.click();
    const edit = page.getByTestId('context-menu-action-edit');
    await expect(edit, 'the row menu offers Edit').toBeVisible({timeout: 5_000});
    await edit.click();
    await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 8_000});
    const form = page.getByTestId('tx-form-modal');
    await expect(form, 'one edited row auto-opens its form').toBeVisible({timeout: 8_000});
    await expect(form.getByTestId('tx-form-save'), 'the Edit form is editable').toBeVisible({timeout: 8_000});
    return form;
}

// ---------------------------------------------------------------------------
// Measures
// ---------------------------------------------------------------------------

/** A number shown in an input: plain decimal, a comma read as the decimal separator. NaN when empty. */
function shownNumber(text: string): number {
    const plain = text.replace(/[\s  ']/g, '').replace(/−/g, '-');
    if (plain === '') return Number.NaN;
    return Number(plain.includes('.') && plain.includes(',') ? plain.replace(/,/g, '') : plain.replace(',', '.'));
}

type ViewSizes = {viewport: number; body: {scroll: number; client: number}; root: {scroll: number; client: number; left: number; right: number}; panel: {scroll: number; client: number; left: number; right: number}};

/** The sideways sizes of the open form: body and root (scroll vs client), the panel's box against the viewport. */
async function measureView(page: Page): Promise<ViewSizes> {
    return page.evaluate(() => {
        const root = document.querySelector<HTMLElement>('[data-testid="tx-form-modal-root"]');
        const body = document.querySelector<HTMLElement>('[data-testid="tx-form-body"]');
        // The panel ModalBase draws around the form: the root's parent.
        const panel = root?.parentElement ?? null;
        const box = (el: HTMLElement | null) => {
            const rect = el?.getBoundingClientRect();
            return {scroll: el?.scrollWidth ?? -1, client: el?.clientWidth ?? -1, left: Math.round(rect?.left ?? -1), right: Math.round(rect?.right ?? -1)};
        };
        return {viewport: window.innerWidth, body: {scroll: body?.scrollWidth ?? -1, client: body?.clientWidth ?? -1}, root: box(root), panel: box(panel)};
    });
}

type ViewValues = {quantity: string; quantityInvalid: string | null; quantityDescribedBy: string | null; cash: string; cashInvalid: string | null; cellsInvalid: string[]; significantErrors: number};

/** What the view shows in its quantity and amount, and every invalid mark it carries. */
async function readViewValues(form: Locator): Promise<ViewValues> {
    const quantity = form.getByTestId('tx-form-quantity');
    const cash = form.getByTestId('tx-form-cash-amount');
    await expect(quantity, 'the view shows the quantity field').toBeVisible({timeout: 5_000});
    await expect(cash, 'the view shows the amount field').toBeVisible({timeout: 5_000});
    return {
        quantity: await quantity.inputValue(),
        quantityInvalid: await quantity.getAttribute('aria-invalid'),
        quantityDescribedBy: await quantity.getAttribute('aria-describedby'),
        cash: await cash.inputValue(),
        cashInvalid: await cash.getAttribute('aria-invalid'),
        cellsInvalid: await form.locator('[data-cell-invalid]').evaluateAll((els) => els.map((el) => `${el.getAttribute('data-cell')}=${el.getAttribute('data-cell-invalid')}`)),
        significantErrors: await form.locator('[data-testid="tx-form-quantity-significant-error"], [data-testid="tx-form-cash-significant-error"], [data-testid="tx-form-quantity-digits-error"]').count(),
    };
}

/** The view shows the saved values as the edit form does: 10 units, the magnitude 1234.56, and no check fired. Soft. */
function expectViewValues(v: ViewValues, label: string): void {
    const dump = JSON.stringify(v);
    expect.soft(shownNumber(v.quantity), `${label}: the quantity field shows ${BUY_QUANTITY} — ${dump}`).toBe(BUY_QUANTITY);
    expect.soft(v.cash.trim().startsWith('-') || v.cash.trim().startsWith('−'), `${label}: the amount shows the magnitude, no leading minus — ${dump}`).toBe(false);
    expect.soft(Math.abs(shownNumber(v.cash)), `${label}: the amount shows ${BUY_CASH} — ${dump}`).toBe(BUY_CASH);
    expect.soft(v.quantityInvalid, `${label}: the quantity is not marked invalid in read-only — ${dump}`).not.toBe('true');
    expect.soft(v.cashInvalid, `${label}: the amount is not marked invalid in read-only — ${dump}`).not.toBe('true');
    expect.soft(v.cellsInvalid, `${label}: no cell marked invalid in read-only — ${dump}`).toEqual([]);
    expect.soft(v.significantErrors, `${label}: no digits error under a field in read-only — ${dump}`).toBe(0);
}

/**
 * Read-only shows no entry hint: the sign hint under the quantity (no testid: the id its input names in
 * `aria-describedby`) and the one under the amount (`tx-form-cash-hint`). Soft; returns what was on screen, for the dump.
 * Called after `readViewValues`, so the fields are already on screen with their values (the presence barrier).
 */
async function expectNoHintsInView(form: Locator, v: ViewValues, label: string): Promise<Record<string, unknown>> {
    const quantityHint = v.quantityDescribedBy ? form.locator(`[id="${v.quantityDescribedBy}"]`) : null;
    const cashHint = form.getByTestId('tx-form-cash-hint');
    const seen = {
        quantityHintId: v.quantityDescribedBy,
        quantityHintCount: quantityHint ? await quantityHint.count() : 0,
        cashHintCount: await cashHint.count(),
        cashDerivedCount: await form.getByTestId('tx-form-cash-derived').count(),
    };
    const dump = JSON.stringify(seen);
    if (quantityHint) await expect.soft(quantityHint, `${label}: the quantity's entry hint is shown in read-only — ${dump}`).toBeHidden({timeout: 2_000});
    await expect.soft(cashHint, `${label}: the amount's entry hint is shown in read-only — ${dump}`).toBeHidden({timeout: 2_000});
    return seen;
}

type DateSizes = {value: string; scroll: number; client: number; fontSize: string; textWidth: number; contentWidth: number};

/** The date input of the form: its scroll vs client width, and the width its text needs against the room it has. */
async function measureDate(form: Locator): Promise<DateSizes> {
    const wrap = form.getByTestId('tx-form-date-wrap');
    // No testid on the form's date input (TxFormSingleSection passes none): the one textbox of its wrapper.
    const input = wrap.getByRole('textbox');
    await expect(input, 'the date field is one input').toHaveCount(1);
    await expect(input, 'the date field shows an ISO date').toHaveValue(/^\d{4}-\d{2}-\d{2}$/, {timeout: 5_000});
    await form.page().evaluate(() => document.fonts.ready.then(() => undefined));
    return input.evaluate((el: HTMLInputElement) => {
        const style = getComputedStyle(el);
        const ctx = document.createElement('canvas').getContext('2d');
        let textWidth = -1;
        if (ctx) {
            ctx.font = `${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
            textWidth = Math.ceil(ctx.measureText(el.value).width);
        }
        const contentWidth = el.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
        return {value: el.value, scroll: el.scrollWidth, client: el.clientWidth, fontSize: style.fontSize, textWidth, contentWidth: Math.floor(contentWidth)};
    });
}

/** The whole date shows: nothing scrolls inside the input and the text fits its room. Soft. */
function expectDateFits(d: DateSizes, label: string): void {
    const dump = JSON.stringify(d);
    expect.soft(d.scroll, `${label}: the date input scrolls — scrollWidth ${d.scroll} > clientWidth ${d.client} (${dump})`).toBeLessThanOrEqual(d.client);
    expect.soft(d.textWidth, `${label}: the date text needs ${d.textWidth} px, the input has ${d.contentWidth} px (${dump})`).toBeLessThanOrEqual(d.contentWidth);
}

type Box = {top: number; bottom: number; left: number; right: number; centerY: number};
type ChargeBoxes = {titleHook: boolean; row: Box; title: Box | null; amount: Box | null; trash: Box | null; open: Box | null; unlink: Box | null};

/** The boxes of a charge row: the row, its title (the hook, else the first element of its first line), amount, trash. */
async function measureCharge(row: Locator): Promise<ChargeBoxes> {
    return row.evaluate((el) => {
        const box = (node: Element | null | undefined) => {
            if (!node) return null;
            const r = node.getBoundingClientRect();
            return {top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), right: Math.round(r.right), centerY: Math.round(r.top + r.height / 2)};
        };
        const hooked = el.querySelector('[data-testid="tx-form-charge-title"]');
        // Until the hook exists: the first line's first part, its first child (the type label).
        const fallback = el.firstElementChild?.firstElementChild?.firstElementChild;
        return {
            titleHook: hooked !== null,
            row: box(el)!,
            title: box(hooked ?? fallback),
            amount: box(el.querySelector('[data-testid^="tx-form-charge-cash-"][data-testid$="-amount"]')),
            trash: box(el.querySelector('[data-testid^="tx-form-charge-remove-"]')),
            open: box(el.querySelector('[data-testid^="tx-form-charge-open-"]')),
            unlink: box(el.querySelector('[data-testid^="tx-form-charge-unlink-"]')),
        };
    });
}

/** The trash sits on the title's line, at the row's right edge. With `amountToo`, the amount is on that line as well. Soft. */
function expectTrashOnTitleLine(c: ChargeBoxes, label: string, amountToo: boolean): void {
    const dump = JSON.stringify(c);
    expect.soft(c.titleHook, `${label}: the charge row publishes tx-form-charge-title — ${dump}`).toBe(true);
    expect(c.title, `${label}: the charge row has a title — ${dump}`).not.toBeNull();
    expect(c.trash, `${label}: the new charge offers its trash — ${dump}`).not.toBeNull();
    expect.soft(Math.abs(c.trash!.centerY - c.title!.centerY), `${label}: the trash is on the title line — trash top ${c.trash!.top}, title top ${c.title!.top} (${dump})`).toBeLessThanOrEqual(SAME_LINE_PX);
    expect.soft(c.trash!.right, `${label}: the trash is right-aligned — trash right ${c.trash!.right}, row right ${c.row.right} (${dump})`).toBeGreaterThanOrEqual(c.row.right - SAME_LINE_PX);
    if (amountToo) {
        expect(c.amount, `${label}: the charge has its amount — ${dump}`).not.toBeNull();
        expect.soft(Math.abs(c.amount!.centerY - c.title!.centerY), `${label}: the amount is on the title line — amount top ${c.amount!.top}, title top ${c.title!.top} (${dump})`).toBeLessThanOrEqual(SAME_LINE_PX);
    }
}

/** A saved charge's three buttons (Open, Unlink, trash) sit on the title's line, the rightmost at the row's right edge. Soft. */
function expectSavedChargeIconsOnTitleLine(c: ChargeBoxes, label: string): void {
    const dump = JSON.stringify(c);
    expect(c.title, `${label}: the charge row has a title — ${dump}`).not.toBeNull();
    const icons = {open: c.open, unlink: c.unlink, trash: c.trash};
    for (const [name, icon] of Object.entries(icons)) {
        expect(icon, `${label}: the saved charge offers its ${name} button — ${dump}`).not.toBeNull();
        expect.soft(Math.abs(icon!.centerY - c.title!.centerY), `${label}: the ${name} button is on the title line — ${name} top ${icon!.top}, title top ${c.title!.top} (${dump})`).toBeLessThanOrEqual(SAME_LINE_PX);
    }
    const rightmost = Math.max(...Object.values(icons).map((icon) => icon!.right));
    expect.soft(rightmost, `${label}: the buttons are right-aligned — rightmost ${rightmost}, row right ${c.row.right} (${dump})`).toBeGreaterThanOrEqual(c.row.right - SAME_LINE_PX);
}

/** «+ Fee» in the form's charges section: the one new FEE row. */
async function addFee(form: Locator): Promise<Locator> {
    const section = form.getByTestId('tx-form-charges');
    const add = section.getByTestId('tx-form-charges-add-FEE');
    await expect(add, 'the New BUY form offers «+ Fee»').toBeVisible({timeout: 8_000});
    await add.click();
    const row = section.locator('[data-testid="tx-form-charge-row"][data-charge-id=""][data-charge-type="FEE"]');
    await expect(row).toHaveCount(1);
    await expect(row.locator('[data-testid^="tx-form-charge-remove-"]')).toBeVisible();
    return row;
}

/**
 * Hold `GET /transactions/types` until `release()`: a page loaded with this hold has no type rules until the test says so,
 * as a cold page on a slow network. `requests()` counts the calls the hold caught.
 */
async function holdTypes(page: Page): Promise<{release: () => void; requests: () => number; dispose: () => Promise<void>}> {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
        release = resolve;
    });
    let count = 0;
    const pattern = '**/api/v1/transactions/types*';
    await page.route(pattern, async (route) => {
        count += 1;
        await gate;
        await route.continue();
    });
    return {release, requests: () => count, dispose: () => page.unroute(pattern)};
}

/** The double-clicked row's read-only view, on screen and settled; `table` scopes the row (a page or a tab). */
async function openViewOfRow(page: Page, table: Locator, txId: number): Promise<Locator> {
    const row = table.locator(`tr[data-row-id="tx-${txId}"]`);
    await expect(row, `the row #${txId} is on screen`).toBeVisible({timeout: 10_000});
    await row.getByTestId(`tx-desc-${txId}`).dblclick();
    const form = page.getByTestId('tx-form-modal');
    await expect(form).toBeVisible({timeout: 8_000});
    await expect(form.getByTestId('tx-form-save'), 'view mode: nothing to save').toBeHidden();
    return form;
}

/** The saved quantity and amount magnitude of the seeded BUY, read back from the server. */
async function savedBuyFigures(page: Page, seed: LinkedBuy): Promise<{quantity: number; magnitude: number}> {
    const buy = (await readByIds(page, [seed.buyId])).get(seed.buyId);
    const quantity = Number(buy?.quantity);
    const amount = Number(buy?.cash?.amount);
    expect(quantity, `premise: the BUY has a quantity (${JSON.stringify(buy)})`).toBeGreaterThan(0);
    expect(amount, `premise: the BUY paid cash, stored negative (${JSON.stringify(buy)})`).toBeLessThan(0);
    return {quantity, magnitude: Math.abs(amount)};
}

/**
 * The read-only view of the seeded BUY with its FEE: the amount as its magnitude and the quantity (hard, retried: a
 * rebuild after the type rules arrive is what is waited for), no invalid mark and no hint (soft), no sideways overflow
 * (soft), and the charges section, loaded, listing the FEE (hard). Returns the measures for the dump.
 */
async function expectParentView(page: Page, form: Locator, seed: LinkedBuy, figures: {quantity: number; magnitude: number}, label: string): Promise<Record<string, unknown>> {
    const quantity = form.getByTestId('tx-form-quantity');
    const cash = form.getByTestId('tx-form-cash-amount');
    await expect(cash, `${label}: the amount field`).toBeVisible({timeout: 8_000});
    await expect.poll(async () => cash.inputValue(), {message: `${label}: the amount shows the magnitude ${figures.magnitude}, no minus`, timeout: 10_000}).toMatch(/^[^-−]/);
    await expect.poll(async () => shownNumber(await cash.inputValue()), {message: `${label}: the amount shows ${figures.magnitude}`, timeout: 5_000}).toBe(figures.magnitude);
    await expect.poll(async () => shownNumber(await quantity.inputValue()), {message: `${label}: the quantity shows ${figures.quantity}`, timeout: 5_000}).toBe(figures.quantity);

    const section = form.getByTestId('tx-form-charges');
    await expect(section, `${label}: the read-only charges section`).toBeVisible({timeout: 8_000});
    await expect(section).toHaveAttribute('data-state', 'ready', {timeout: 8_000});
    await expect(section.locator(`[data-testid="tx-form-charge-row"][data-charge-id="${seed.feeId}"]`), `${label}: the FEE is listed`).toHaveAttribute('data-charge-type', 'FEE', {timeout: 8_000});

    const values = await readViewValues(form);
    const dump = JSON.stringify(values);
    expect.soft(values.quantityInvalid, `${label}: the quantity is not marked invalid — ${dump}`).not.toBe('true');
    expect.soft(values.cashInvalid, `${label}: the amount is not marked invalid — ${dump}`).not.toBe('true');
    expect.soft(values.cellsInvalid, `${label}: no cell marked invalid — ${dump}`).toEqual([]);
    expect.soft(values.significantErrors, `${label}: no digits error — ${dump}`).toBe(0);
    const hints = await expectNoHintsInView(form, values, label);

    const sizes = await measureView(page);
    const rootOverflow = await measureSidewaysOverflow(page, '[data-testid="tx-form-modal-root"]');
    const bodyOverflow = await measureSidewaysOverflow(page, '[data-testid="tx-form-body"]');
    const named = `(offenders ${JSON.stringify([...rootOverflow.offenders, ...bodyOverflow.offenders])}, sizes ${JSON.stringify(sizes)})`;
    expect.soft(sizes.body.scroll, `${label}: tx-form-body scrolls sideways ${named}`).toBeLessThanOrEqual(sizes.body.client + 1);
    expect.soft(sizes.panel.right, `${label}: the modal panel ends past the screen ${named}`).toBeLessThanOrEqual(sizes.viewport);
    expect.soft(Math.max(rootOverflow.over, bodyOverflow.over), `${label}: something ends past the form's edge ${named}`).toBeLessThanOrEqual(1);
    return {values, hints, sizes, rootOverflow, bodyOverflow};
}

/** The measures of a run, kept beside its results (green runs included) and attached: what a report quotes. */
async function keepMeasures(testInfo: TestInfo, name: string, dumps: Record<string, unknown>): Promise<void> {
    const path = testInfo.outputPath(name);
    writeFileSync(path, JSON.stringify(dumps, null, 2));
    await testInfo.attach(name, {path, contentType: 'application/json'});
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Transaction form on an Android phone (TL-1d)', () => {
    let owned = emptyOwnedAccount();
    let assetIds: number[] = [];

    test.beforeEach(() => {
        owned = emptyOwnedAccount();
        assetIds = [];
    });

    test.afterEach(async ({page, request}) => {
        await cleanup(page, request, owned, assetIds);
    });

    test('(a) view of a saved BUY of a long-named asset at 412 and 375 px: no sideways overflow, the saved values, no checks', async ({page, request}, testInfo) => {
        test.setTimeout(120_000);
        const seed = await seedLongNamedBuy(page, request, owned, assetIds, `tl1da_${testInfo.project.name}`);
        const dumps: Record<string, unknown> = {};

        for (const width of VIEW_WIDTHS) {
            await setWidth(page, width);
            const form = await openView(page, seed);
            const label = `view at ${width} px`;

            const sizes = await measureView(page);
            const overflow = await measureSidewaysOverflow(page, '[data-testid="tx-form-modal-root"]');
            // The body scrolls (overflow-y: auto), so the root's measure skips what is inside it: the body is measured on its own.
            const bodyOverflow = await measureSidewaysOverflow(page, '[data-testid="tx-form-body"]');
            const values = await readViewValues(form);
            const hints = await expectNoHintsInView(form, values, label);
            dumps[width] = {sizes, overflow, bodyOverflow, values, hints};
            const named = `(offenders ${JSON.stringify([...overflow.offenders, ...bodyOverflow.offenders])}, sizes ${JSON.stringify(sizes)})`;
            expect.soft(sizes.body.scroll, `${label}: tx-form-body scrolls sideways — scrollWidth ${sizes.body.scroll} > clientWidth ${sizes.body.client} ${named}`).toBeLessThanOrEqual(sizes.body.client + 1);
            expect.soft(sizes.root.scroll, `${label}: tx-form-modal-root scrolls sideways — scrollWidth ${sizes.root.scroll} > clientWidth ${sizes.root.client} ${named}`).toBeLessThanOrEqual(sizes.root.client + 1);
            expect.soft(sizes.panel.scroll, `${label}: the modal panel scrolls sideways — scrollWidth ${sizes.panel.scroll} > clientWidth ${sizes.panel.client} ${named}`).toBeLessThanOrEqual(sizes.panel.client + 1);
            expect.soft(sizes.panel.right, `${label}: the modal panel ends past the ${width} px screen ${named}`).toBeLessThanOrEqual(width);
            expect.soft(overflow.over, `${label}: something inside the form ends past its edge ${named}`).toBeLessThanOrEqual(1);
            expect.soft(bodyOverflow.over, `${label}: something inside tx-form-body ends past its edge ${named}`).toBeLessThanOrEqual(1);
            expectViewValues(values, label);

            await form.getByTestId('tx-form-close').click();
            await expect(form).toBeHidden({timeout: 5_000});
        }
        await keepMeasures(testInfo, 'tl1d-view-measures.json', dumps);
    });

    test('(b) the date field shows the whole date at 320, 360, 375, 412 and 640 px, in the New form and in the Edit form', async ({page, request}, testInfo) => {
        test.setTimeout(120_000);
        const seed = await seedLongNamedBuy(page, request, owned, assetIds, `tl1db_${testInfo.project.name}`);
        const dumps: Record<string, unknown> = {};

        // New: opened at the narrowest width, then resized through the others (CSS re-lays it out).
        await setWidth(page, DATE_WIDTHS[0]);
        const newForm = await openNewForm(page);
        for (const width of DATE_WIDTHS) {
            await setWidth(page, width);
            const d = await measureDate(newForm);
            dumps[`new-${width}`] = d;
            expectDateFits(d, `New form at ${width} px`);
        }

        // Edit: ⋮ → Edit on the table, the Bulk's row form; a fresh page load leaves the New draft behind.
        await page.goto('about:blank');
        await setWidth(page, DATE_WIDTHS[0]);
        const editForm = await openEditForm(page, seed.buyId);
        await expect(editForm.getByTestId('tx-form-asset-trigger'), 'the Edit form shows the BUY').toContainText(seed.assetName, {timeout: 10_000});
        await expect(editForm.getByTestId('tx-form-date-wrap').getByRole('textbox'), 'the Edit form shows the BUY date').toHaveValue(seed.buyDate);
        for (const width of DATE_WIDTHS) {
            await setWidth(page, width);
            const d = await measureDate(editForm);
            dumps[`edit-${width}`] = d;
            expectDateFits(d, `Edit form at ${width} px`);
        }
        await keepMeasures(testInfo, 'tl1d-date-measures.json', dumps);
    });

    test('(c) a «+ Fee» charge of a New BUY at 412 and 375 px: the trash on the title line, right-aligned', async ({page, request}, testInfo) => {
        test.setTimeout(90_000);
        await openOwnedAccount(page, request, owned, `tl1dc_${testInfo.project.name}`);
        await createOwnedBroker(page, 'tl1dc', owned.brokerIds);
        const dumps: Record<string, unknown> = {};

        await setWidth(page, CHARGE_WIDTHS[0]);
        const form = await openNewForm(page);
        const row = await addFee(form);
        for (const width of CHARGE_WIDTHS) {
            await setWidth(page, width);
            const c = await measureCharge(row);
            dumps[width] = c;
            expectTrashOnTitleLine(c, `charge row at ${width} px`, false);
        }
        await keepMeasures(testInfo, 'tl1d-charge-measures.json', dumps);
    });

    test('(d) guard at 1280 px: the charge row on one line, the view of the BUY with the same values', async ({page, request}, testInfo) => {
        test.setTimeout(120_000);
        const seed = await seedLongNamedBuy(page, request, owned, assetIds, `tl1dd_${testInfo.project.name}`);
        await setWidth(page, DESKTOP.width, DESKTOP.height);
        const dumps: Record<string, unknown> = {};

        const view = await openView(page, seed);
        const values = await readViewValues(view);
        dumps.view = values;
        expectViewValues(values, 'view at 1280 px');
        await view.getByTestId('tx-form-close').click();
        await expect(view).toBeHidden({timeout: 5_000});

        const form = await openNewForm(page);
        const c = await measureCharge(await addFee(form));
        dumps.charge = c;
        expectTrashOnTitleLine(c, 'charge row at 1280 px', true);
        await keepMeasures(testInfo, 'tl1d-desktop-measures.json', dumps);
    });

    test('(e) a saved BUY with its saved FEE, in the Bulk edit form at 320 and 360 px: Open, Unlink and trash on the title line, right-aligned', async ({page, request}, testInfo) => {
        test.setTimeout(90_000);
        const committed: number[] = [];
        const seed = await seedLinkedBuy(page, request, owned, committed, `tl1de_${testInfo.project.name}`, 'TL1d saved charge');
        const dumps: Record<string, unknown> = {};

        await setWidth(page, SAVED_CHARGE_WIDTHS[0]);
        const form = await openEditForm(page, seed.buyId);
        const section = form.getByTestId('tx-form-charges');
        await expect(section, 'the BUY form lists its charges').toBeVisible({timeout: 8_000});
        await expect(section).toHaveAttribute('data-state', 'ready', {timeout: 8_000});
        const row = section.locator(`[data-testid="tx-form-charge-row"][data-charge-id="${seed.feeId}"]`);
        await expect(row, 'the saved FEE is listed').toHaveAttribute('data-charge-type', 'FEE', {timeout: 8_000});
        for (const prefix of ['tx-form-charge-open-', 'tx-form-charge-unlink-', 'tx-form-charge-remove-']) {
            await expect(row.locator(`[data-testid^="${prefix}"]`), `the saved FEE offers ${prefix}*`).toBeVisible({timeout: 5_000});
        }
        for (const width of SAVED_CHARGE_WIDTHS) {
            await setWidth(page, width);
            const c = await measureCharge(row);
            dumps[width] = c;
            expectSavedChargeIconsOnTitleLine(c, `saved charge row at ${width} px`);
        }
        await keepMeasures(testInfo, 'tl1d-saved-charge-measures.json', dumps);
    });

    test('(f) the Transactions page, a saved BUY with its FEE, at 412 and 375 px: magnitude, quantity, no marks or hints, no overflow, the charges section', async ({page, request}, testInfo) => {
        test.setTimeout(120_000);
        const seed = await seedLinkedBuy(page, request, owned, [], `tl1df_${testInfo.project.name}`, 'TL1d parent view');
        const figures = await savedBuyFigures(page, seed);
        const dumps: Record<string, unknown> = {figures};

        for (const width of VIEW_WIDTHS) {
            await setWidth(page, width);
            await goToTransaction(page, seed.buyId);
            const form = await openViewOfRow(page, page.getByTestId('tx-table'), seed.buyId);
            await waitForSettled(form.getByTestId('tx-form-modal-root'), 15_000);
            dumps[width] = await expectParentView(page, form, seed, figures, `Transactions page view at ${width} px`);
            await form.getByTestId('tx-form-close').click();
            await expect(form).toBeHidden({timeout: 5_000});
        }
        await keepMeasures(testInfo, 'tl1d-parent-view-measures.json', dumps);
    });

    test("(g) a broker's Transactions tab on a fresh page, the type rules held until the view is open, at 412 and 375 px: magnitude, quantity, no marks or hints, no overflow, the charges section", async ({page, request}, testInfo) => {
        test.setTimeout(120_000);
        const seed = await seedLinkedBuy(page, request, owned, [], `tl1dg_${testInfo.project.name}`, 'TL1d broker view');
        const figures = await savedBuyFigures(page, seed);
        const dumps: Record<string, unknown> = {figures};

        for (const width of VIEW_WIDTHS) {
            await setWidth(page, width);
            // A fresh page load (no visit to /transactions): the type rules are module state, empty again, and held.
            const types = await holdTypes(page);
            try {
                await navigateTo(page, `/brokers/${seed.broker.id}`);
                await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 20_000});
                await page.getByTestId('broker-tab-transazioni').click();
                await expect(page.getByTestId('broker-transactions-tab')).toBeVisible({timeout: 10_000});
                const table = page.getByTestId('broker-transactions');
                await expect(table.getByTestId('tx-table')).toBeVisible({timeout: 20_000});
                const form = await openViewOfRow(page, table, seed.buyId);
                const heldAtOpen = types.requests();
                types.release();
                await waitForSettled(form.getByTestId('tx-form-modal-root'), 15_000);
                dumps[width] = {typesRequestsHeldAtOpen: heldAtOpen, ...(await expectParentView(page, form, seed, figures, `broker tab view at ${width} px`))};
                await form.getByTestId('tx-form-close').click();
                await expect(form).toBeHidden({timeout: 5_000});
            } finally {
                types.release();
                await types.dispose();
            }
        }
        await keepMeasures(testInfo, 'tl1d-broker-view-measures.json', dumps);
    });
});
