/**
 * The PAC allocator (beta) end to end on real data — gap 3 of the 1.2 E2E list (devWiki:
 * `decisions/e2e-gaps-of-1-2-before-release`).
 *
 * Until now the planner reached a browser only through the gallery (`fixtures/galleryPac.ts`), which photographs it: no
 * spec checked that the plan on screen is the one the engine computed, from data LibreFolio holds. Nothing is routed
 * here. A disposable account holds two positions and some cash in its own broker; the test opens the planner from the
 * Tools hub and follows the path a user takes:
 *
 *   1. «copy from LibreFolio», three times: the broker's cash (Liquidity, which brings the broker with it), the two
 *      positions with their stored prices (Assets, «Your Assets») and their current weights as the targets (Targets,
 *      «Copy current distribution»); the only value typed is the budget, the part of the cash to invest;
 *   2. «Calculate plan» runs the real engine. The tool's own request, captured on the wire, carries what was copied —
 *      the two Assets and their stored prices, the broker's balance and the budget, the 60/40 weights of the positions
 *      — and its own answer is a plan proven optimal;
 *   3. the screen prints that answer: the run state, the result state and the proof are the answer's, and so is every
 *      amount — per Asset the value after the plan, the ideal value and the signed gap from it, per order the amount and
 *      the fee — compared on sign and digits at the currency's minor unit, the precision the planner prints
 *      (planner/format.ts, R14); the format follows the browser's locale, the value does not. What the plan buys, and
 *      what it takes from the cash, stay within the budget.
 *
 * No oracle: whether the engine computes right is the business of the backend tests (`test_pac_planner_*`); this spec
 * proves that the planner sends what LibreFolio holds and prints what the engine answered. The prices (90 and 40 EUR,
 * 60/40 targets on a 1000 EUR budget) leave no exact split in whole units, so the gaps carry a sign.
 *
 * Beta. The planner is read through its `data-testid`s and the states it publishes (`data-state`, `data-busy`,
 * `data-step`, `data-view`, `data-proof`, …) and DataTable's own `data-row-id`/`data-column-id` — never a text, a
 * layout or a class. The tool is a plugin: its code is read from the catalogue (`GET /tools/catalog`), as the entry
 * whose interface is the compiled planner (`ui.component_key`, registered in src/lib/features/tools/registry.ts).
 *
 * Ownership. The account owns everything the test reads: one broker with a deposit and two purchases, and two manual
 * Assets (no provider: only the quotes stored here price them) — global rows, uniquely named, deleted by id. The
 * planner's draft lives in the page and nothing is saved; the calculation writes nothing. Brokers (with their
 * transactions), Assets (with their prices) and the account are deleted in the fixture's teardown.
 *
 * Offline. No sync, no live price: the copies and the re-read before the calculation are database reads
 * (`POST /portfolio/allocation-source`), the calculation a local solver (`POST /tools/compute`).
 */

import {expect, test as base, type APIRequestContext, type Locator, type Page, type Request} from './fixtures/playwright';
import {eventSeq, waitForEvent, waitForSettled} from './fixtures/app-events';
import {daysAgoIso} from './fixtures/dates';
import {deleteDisposableUser, prepareOnboardingAccount, registerDisposableUser, type DisposableUser} from './fixtures/onboarding-accounts';
import {optionsClosed} from './fixtures/probe';
import {uniqueSuffix} from './fixtures/unique';

const API = '/api/v1';
const TOOLS_CATALOG_PATH = `${API}/tools/catalog`;
const TOOLS_COMPUTE_PATH = `${API}/tools/compute`;

/** The compiled planner's interface key (registry.ts, `defineToolRenderer(…, {componentKey})`): how the catalogue names the tool this spec drives. */
const PLANNER_COMPONENT_KEY = 'pac-allocator';

/** One currency for everything — cash, prices, valuation — so the plan needs no exchange rate. */
const CURRENCY = 'EUR';
/** The account's money: deposited before the purchases. */
const DEPOSIT = 5000;
/** The part of the broker's cash the plan may invest: the one value the user types. */
const BUDGET = 1000;
/**
 * The two positions. Held: 20 × 90 = 1800 and 30 × 40 = 1200, so the current distribution is 60/40 and the broker keeps
 * 5000 − 3000 = 2000 of cash. Invested: 1000 at 60/40 is 600/400, which no whole number of units at 90 and 40 hits.
 */
const POSITIONS = [
    {tag: 'A', price: 90, units: 20, weight: 0.6},
    {tag: 'B', price: 40, units: 30, weight: 0.4},
] as const;
const CASH_LEFT = DEPOSIT - POSITIONS.reduce((sum, position) => sum + position.price * position.units, 0);
/** The purchases, and the first of the daily quotes stored up to yesterday: never today, which the backend may still see as tomorrow. */
const BUY_DAYS_AGO = 10;
const DEPOSIT_DAYS_AGO = 12;

/** Full loads, the hub's catalogue and the planner's chunk on a cold lane. */
const PAGE_TIMEOUT_MS = 30_000;
/** One `POST /portfolio/allocation-source`: a database read. */
const READ_TIMEOUT_MS = 20_000;
/** A dialog, a step, a re-render after a click, on a machine that may be loaded. */
const UI_TIMEOUT_MS = 10_000;
/** The re-read, then the tool: its own contract waits at most 65 s (tool_plugins/pac_allocator, `client_timeout_ms`). */
const CALCULATION_TIMEOUT_MS = 75_000;

type Owned = {user: DisposableUser | null; brokerIds: number[]; assetIds: number[]};
type HeldAsset = {id: number; name: string; price: number; units: number; weight: number};
type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};

type CatalogItem = {tool_code: string; ui: {component_key: string}};

/** The wire, as much of it as this spec reads (backend schemas/pac_allocator.py). */
type WireMoney = {amount: string; currency: string};
type PacAsk = {
    valuation_currency: string;
    assets: Array<{asset_id: string; identity: {kind: string; source_asset_id?: string}; quote: (WireMoney & {quote_base_quantity: string}) | null}>;
    brokers: Array<{broker_id: string; identity: {kind: string; source_broker_id?: string}}>;
    existing_cash?: Array<{broker_id: string; available: WireMoney; selected: WireMoney}>;
    contributions?: unknown[];
    target_weights: Array<{asset_id: string; weight: string}>;
};
type ComputeAsk = {items: Array<{correlation_id: string; tool_code: string; parameters: PacAsk}>};
type ExactNumber = {kind: 'finite_decimal'; value: string} | {kind: 'exact_ratio'; numerator: string; denominator: string};
type ExactMoney = {value: ExactNumber; currency: string};
type PacAssetRow = {asset_id: string; target_value: ExactMoney; final_value: ExactMoney; residual: ExactMoney};
type PacOrderRow = {order_id: string; asset_id: string; broker_id: string; cash_debit: WireMoney; fee: WireMoney};
type PacResult = {
    result_state: string;
    stop_reason?: string;
    issues: unknown[];
    proof?: {kind: string};
    catalogs?: {currencies: Array<{currency: string; minor_unit: string}>};
    primary_solution?: {asset_rows: PacAssetRow[]; order_rows: PacOrderRow[]; accounting: {final_invested: ExactMoney; fixed_reference: ExactMoney}};
};
type ComputeAnswer = {results: Array<{correlation_id: string; status: string; result?: PacResult; error?: unknown}>};

/** An amount as the screen prints it, reduced to what does not depend on the locale. */
type Figure = {sign: '' | '+' | '-'; digits: string};
/** An amount: how it is printed, and its value in units of its last printed digit. */
type Amount = {figure: Figure; units: bigint; scale: number};

const DECIMAL = /^([+-])?(\d+)(?:\.(\d+))?$/;

/**
 * A wait armed before the action and awaited later. If the test fails in between, the pending wait would reject
 * unobserved when the page closes, and that noise would be reported beside the real failure; awaiting the returned
 * promise still throws as usual.
 */
function armed<T>(wait: Promise<T>): Promise<T> {
    wait.catch(() => undefined);
    return wait;
}

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

/** A value for a quoted CSS attribute selector. */
function attr(value: string): string {
    return value.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

const escapeRegExp = (text: string): string => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

function isCompute(req: Request): boolean {
    return req.method() === 'POST' && new URL(req.url()).pathname === TOOLS_COMPUTE_PATH;
}

// ---------------------------------------------------------------------------
// Amounts: sign and digits, at the precision printed
// ---------------------------------------------------------------------------

/** Sign and digits of a printed amount; the currency, the separators and a `≈` belong to the locale and the rounding. */
function printed(text: string | null): Figure {
    const value = text ?? '';
    const firstDigit = value.search(/\d/);
    const head = firstDigit < 0 ? value : value.slice(0, firstDigit);
    return {sign: /[-\u2212]/.test(head) ? '-' : head.includes('+') ? '+' : '', digits: value.replace(/\D/g, '')};
}

function ratioOf(value: ExactNumber, what: string): [bigint, bigint] {
    if (value.kind === 'exact_ratio') return [BigInt(value.numerator), BigInt(value.denominator)];
    const match = DECIMAL.exec(value.value);
    if (!match) throw new Error(`${what}: ${JSON.stringify(value)} is not a decimal`);
    const [, sign, integer, fraction = ''] = match;
    return [BigInt(`${sign === '-' ? '-' : ''}${integer}${fraction}`), 10n ** BigInt(fraction.length)];
}

/**
 * An amount the engine computed, as the planner prints it (format.ts, R14): rounded half away from zero to the minor
 * unit of its currency; a sign always when it is negative, and a «+» too when the column is signed.
 */
function computedAmount(money: ExactMoney, places: number, signed: boolean, what: string): Amount {
    const [numerator, denominator] = ratioOf(money.value, what);
    const negative = numerator < 0n !== denominator < 0n;
    const magnitude = (numerator < 0n ? -numerator : numerator) * 10n ** BigInt(places);
    const divisor = denominator < 0n ? -denominator : denominator;
    let units = magnitude / divisor;
    if ((magnitude % divisor) * 2n >= divisor) units += 1n;
    if (units === 0n && magnitude !== 0n) throw new Error(`${what}: ${JSON.stringify(money)} is under one minor unit, which the planner prints with more digits (format.ts, G3) — a case this spec does not model`);
    return {figure: {sign: units === 0n ? '' : negative ? '-' : signed ? '+' : '', digits: units.toString().padStart(places + 1, '0')}, units: negative ? -units : units, scale: places};
}

/** An amount the engine posted (an order's amount, a fee), as the planner prints it: every digit it has, at least the minor unit's. */
function postedAmount(money: WireMoney, places: number, what: string): Amount {
    const match = DECIMAL.exec(money.amount);
    if (!match) throw new Error(`${what}: ${JSON.stringify(money)} is not a decimal`);
    const [, sign, integer, fraction = ''] = match;
    const decimals = fraction.replace(/0+$/, '').padEnd(places, '0');
    const units = BigInt(`${integer}${decimals}`);
    const negative = sign === '-' && units !== 0n;
    return {figure: {sign: negative ? '-' : '', digits: units.toString().padStart(decimals.length + 1, '0')}, units: negative ? -units : units, scale: decimals.length};
}

/**
 * The cell prints `expected`: same sign, same digits. Retried until it does, then read once more: the amount returned
 * is the one on screen, at the scale of the digits it printed.
 */
async function shows(cell: Locator, expected: Amount, what: string): Promise<Amount> {
    await expect(cell, `${what}: exactly one cell`).toHaveCount(1, {timeout: UI_TIMEOUT_MS});
    await expect.poll(async () => printed(await cell.textContent()), {message: `${what} must print the answer's sign and digits`, timeout: UI_TIMEOUT_MS}).toEqual(expected.figure);
    const shown = printed(await cell.textContent());
    return {figure: shown, units: BigInt(shown.digits) * (shown.sign === '-' ? -1n : 1n), scale: expected.scale};
}

function total(amounts: readonly Amount[]): {units: bigint; scale: number} {
    const scale = Math.max(0, ...amounts.map((amount) => amount.scale));
    return {units: amounts.reduce((sum, amount) => sum + amount.units * 10n ** BigInt(scale - amount.scale), 0n), scale};
}

function decimalText(units: bigint, scale: number): string {
    const negative = units < 0n;
    const digits = (negative ? -units : units).toString().padStart(scale + 1, '0');
    const text = scale === 0 ? digits : `${digits.slice(0, -scale)}.${digits.slice(-scale)}`;
    return negative ? `-${text}` : text;
}

/** The sum of `amounts` is at most the budget. */
function expectWithinBudget(amounts: readonly Amount[], what: string): void {
    const sum = total(amounts);
    expect(sum.units <= BigInt(BUDGET) * 10n ** BigInt(sum.scale), `${what} add up to ${decimalText(sum.units, sum.scale)} ${CURRENCY}, more than the budget of ${BUDGET} ${CURRENCY}`).toBe(true);
}

/** Fraction digits of a currency's minor unit, as the answer's catalogue publishes it (`0.01` → 2). */
function minorPlaces(result: PacResult, currency: string): number {
    const spec = result.catalogs?.currencies.find((item) => item.currency === currency);
    const match = spec ? DECIMAL.exec(spec.minor_unit) : null;
    if (!match) throw new Error(`The answer's currency catalogue has no usable minor unit for ${currency}: ${JSON.stringify(result.catalogs?.currencies ?? null)}`);
    return (match[3] ?? '').replace(/0+$/, '').length;
}

// ---------------------------------------------------------------------------
// Owned rows: seeding and cleanup
// ---------------------------------------------------------------------------

/** Every id is recorded for cleanup before it is checked. */
async function createBroker(page: Page, owned: Owned, name: string): Promise<number> {
    const brokers = await jsonFrom<{results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>}>(await page.request.post(`${API}/brokers`, {data: [{name, opened_at: daysAgoIso(400)}]}), 'create the owned broker');
    const broker = brokers.results.find((item) => item.name === name);
    if (typeof broker?.broker_id === 'number') owned.brokerIds.push(broker.broker_id);
    if (!broker?.success || typeof broker.broker_id !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(brokers)}`);
    return broker.broker_id;
}

/** A manual Asset: no provider, so nothing ever prices it but the quotes this test stores. */
async function createManualAsset(page: Page, owned: Owned, name: string): Promise<number> {
    const item = {display_name: name, currency: CURRENCY, asset_type: 'ETF', quote_base_quantity: 1, active: true};
    const assets = await jsonFrom<{results: Array<{asset_id: number | null; display_name: string; success: boolean; message?: string}>}>(await page.request.post(`${API}/assets`, {data: [item]}), 'create an owned Asset');
    const asset = assets.results.find((result) => result.display_name === name);
    if (typeof asset?.asset_id === 'number') owned.assetIds.push(asset.asset_id);
    if (!asset?.success || typeof asset.asset_id !== 'number') throw new Error(`Asset creation failed: ${JSON.stringify(assets)}`);
    return asset.asset_id;
}

async function seedDailyQuotes(page: Page, assetId: number, close: number): Promise<void> {
    const prices: Array<{date: string; close: number; currency: string}> = [];
    for (let days = BUY_DAYS_AGO; days >= 1; days -= 1) prices.push({date: daysAgoIso(days), close, currency: CURRENCY});
    const seeded = await jsonFrom<{results: Array<{asset_id: number; count: number}>}>(await page.request.post(`${API}/assets/prices`, {data: [{asset_id: assetId, prices}]}), 'store the Asset quotes');
    expect(seeded.results.find((item) => item.asset_id === assetId)?.count, 'every quote is stored').toBe(prices.length);
}

async function commitTransactions(page: Page, creates: unknown[], purpose: string): Promise<void> {
    const committed = await jsonFrom<{committed: boolean; issues?: unknown[]}>(await page.request.post(`${API}/transactions/commit`, {data: {creates}}), purpose);
    expect(committed.committed, `${purpose}: rolled back — ${JSON.stringify(committed.issues ?? [])}`).toBe(true);
}

/**
 * Delete in dependency order, each step scoped to an id this test recorded.
 *
 * The page is unmounted first. The planner holds a draft that was never saved, so leaving raises the browser's
 * leave-page dialog (PacPlannerTool.svelte, `beforeNavigate`), which Playwright accepts when no dialog listener is
 * registered — none is. The broker goes before the Assets (an Asset with transactions cannot be deleted; `force` takes
 * the broker's transactions with it); the Assets take their quotes with them; the account goes last, through the
 * standalone `request` context it was registered with, which signs in on its own.
 */
async function cleanupOwned(page: Page, request: APIRequestContext, owned: Owned): Promise<void> {
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<void>) => {
        try {
            await action();
        } catch (error) {
            failures.push(`${label}: ${String(error)}`);
        }
    };
    await attempt('unmount the planner', async () => {
        await page.goto('about:blank');
    });
    for (const brokerId of owned.brokerIds) {
        await attempt(`broker ${brokerId}`, async () => {
            const result = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`), 'delete the owned broker and its transactions');
            expect(result.results.find((item) => item.id === brokerId)?.success).toBe(true);
        });
    }
    for (const assetId of owned.assetIds) {
        await attempt(`asset ${assetId}`, async () => {
            const result = await jsonFrom<{results: Array<{asset_id: number; success: boolean}>}>(await page.request.delete(`${API}/assets?asset_ids=${assetId}`), 'delete an owned Asset and its quotes');
            expect(result.results.find((item) => item.asset_id === assetId)?.success).toBe(true);
        });
    }
    const user = owned.user;
    if (user) {
        await attempt(`account ${user.username}`, async () => {
            await deleteDisposableUser(request, user);
        });
    }
    expect(failures, 'every cleanup step is scoped to rows this test created').toEqual([]);
}

const test = base.extend<{owned: Owned}>({
    owned: async ({page, request}, use) => {
        const owned: Owned = {user: null, brokerIds: [], assetIds: []};
        try {
            await use(owned);
        } finally {
            await cleanupOwned(page, request, owned);
        }
    },
});

// ---------------------------------------------------------------------------
// The planner
// ---------------------------------------------------------------------------

/** The code of the tool whose interface is the compiled planner, read from the catalogue: tools are plugins. */
async function plannerToolCode(page: Page): Promise<string> {
    const catalog = await jsonFrom<{items: CatalogItem[]}>(await page.request.get(TOOLS_CATALOG_PATH), 'GET /tools/catalog');
    const planners = catalog.items.filter((item) => item.ui.component_key === PLANNER_COMPONENT_KEY);
    expect(
        planners.map((item) => item.tool_code),
        `the catalogue must list exactly one tool drawn by «${PLANNER_COMPONENT_KEY}» (backend tool_plugins/pac_allocator); it lists ${JSON.stringify(catalog.items.map((item) => [item.tool_code, item.ui.component_key]))}`,
    ).toHaveLength(1);
    return planners[0].tool_code;
}

/** Pick a currency in a CurrencySearchSelect: its search, then the option. Ends on the list closed. */
async function chooseCurrency(scope: Locator, testId: string, code: string): Promise<void> {
    const select = scope.getByTestId(testId);
    const trigger = select.getByTestId(`${testId}-trigger`);
    await trigger.click();
    await expect(trigger).toHaveAttribute('aria-expanded', 'true', {timeout: UI_TIMEOUT_MS});
    await select.getByTestId(`${testId}-search`).fill(code);
    // The currency catalogue is read once per language: the first open of a session waits for it.
    const option = select.getByTestId(`search-select-option-${code}`);
    await expect(option, `${code} is not offered`).toBeVisible({timeout: READ_TIMEOUT_MS});
    await option.click();
    await expect(trigger).toHaveAttribute('aria-expanded', 'false', {timeout: UI_TIMEOUT_MS});
    await optionsClosed(scope.page());
}

/** «Continue», and the step it must lead to: a problem left on the step it leaves holds the wizard there, with its alert. */
async function continueTo(planner: Locator, step: string): Promise<Locator> {
    await planner.getByTestId('pac-planner-continue').click();
    await expect(planner, `«Continue» must reach the ${step} step; a step with a problem stays, showing pac-planner-step-alert`).toHaveAttribute('data-step', step, {timeout: UI_TIMEOUT_MS});
    const section = planner.getByTestId('pac-planner-step');
    await expect(section).toHaveAttribute('data-step', step);
    return section;
}

/** A section of the result: allocation, plan, exposures, ledger or proof (ResultSection.svelte). */
function resultSection(view: Locator, id: string): Locator {
    return view.locator(`[data-testid="pac-planner-result-section"][data-section="${attr(id)}"]`);
}

test.describe('PAC allocator (beta) on real data — 1.2 gap 3', () => {
    test('copied from LibreFolio, calculated by the engine, printed as the engine answered, within the budget', async ({page, request, owned}) => {
        test.setTimeout(180_000);

        const {brokerId, assets} = await test.step('seed: a disposable account holding two priced positions and cash in its own broker', async () => {
            const user = await registerDisposableUser(request, 'pac');
            owned.user = user;
            // Every onboarding flow skipped over the API, so no guide or tour overlay competes for the clicks.
            await prepareOnboardingAccount(page, user, []);
            const suffix = uniqueSuffix();
            const brokerId = await createBroker(page, owned, `pac-real-broker-${suffix}`);
            const assets: HeldAsset[] = [];
            for (const position of POSITIONS) {
                const name = `PAC real ${position.tag} ${suffix}`;
                const id = await createManualAsset(page, owned, name);
                await seedDailyQuotes(page, id, position.price);
                assets.push({id, name, price: position.price, units: position.units, weight: position.weight});
            }
            await commitTransactions(
                page,
                [
                    {broker_id: brokerId, type: 'DEPOSIT', date: daysAgoIso(DEPOSIT_DAYS_AGO), cash: {code: CURRENCY, amount: String(DEPOSIT)}, description: `pac-real deposit ${suffix}`},
                    ...assets.map((asset) => ({
                        broker_id: brokerId,
                        asset_id: asset.id,
                        type: 'BUY',
                        date: daysAgoIso(BUY_DAYS_AGO),
                        quantity: String(asset.units),
                        cash: {code: CURRENCY, amount: String(-asset.units * asset.price)},
                        description: `pac-real purchase ${suffix}`,
                    })),
                ],
                'commit the deposit and the two purchases',
            );
            return {brokerId, assets};
        });
        const assetBySource = new Map(assets.map((asset) => [String(asset.id), asset]));

        const {code, planner} = await test.step('the Tools hub opens the PAC allocator', async () => {
            const code = await plannerToolCode(page);
            // A full load: the stores of the session read the broker and the Assets created after the sign-in.
            await page.goto('/tools');
            const hub = page.getByTestId('tools-hub');
            await expect(hub).toBeVisible({timeout: PAGE_TIMEOUT_MS});
            await waitForSettled(hub, PAGE_TIMEOUT_MS);
            const card = hub.getByTestId(`tool-card-${code}`);
            await expect(card, 'the hub offers the planner with its interface loaded').toHaveAttribute('data-interface-state', 'ready');
            await card.getByTestId('tool-open').click();
            await expect(page).toHaveURL(new RegExp(`/tools/${escapeRegExp(encodeURIComponent(code))}(?:[?#]|$)`), {timeout: PAGE_TIMEOUT_MS});
            const host = page.getByTestId('tool-host');
            await expect(host, 'the tool page settles on its interface').toHaveAttribute('data-state', 'ready', {timeout: PAGE_TIMEOUT_MS});
            await expect(host).toHaveAttribute('data-busy', 'false');
            const planner = host.getByTestId('pac-planner');
            await expect(planner).toHaveAttribute('data-view', 'wizard', {timeout: UI_TIMEOUT_MS});
            await expect(planner).toHaveAttribute('data-step', 'scenario');
            await expect(planner).toHaveAttribute('data-state', 'idle');
            return {code, planner};
        });

        await test.step(`Scenario: the plan is valued in ${CURRENCY}, the currency of every amount here`, async () => {
            await chooseCurrency(planner.getByTestId('pac-planner-scenario'), 'pac-planner-scenario-currency', CURRENCY);
            await continueTo(planner, 'liquidity');
        });

        await test.step("Liquidity: the broker's cash copied from LibreFolio, then the budget as the amount to use", async () => {
            await planner.getByTestId('pac-planner-liquidity-copy-open').click();
            const dialog = page.getByTestId('pac-planner-liquidity-copy');
            await expect(dialog.getByTestId('pac-planner-liquidity-copy-body'), 'the brokers the account owns were not read').toHaveAttribute('data-state', 'ready', {timeout: READ_TIMEOUT_MS});
            const row = dialog.locator(`[data-testid="pac-planner-liquidity-copy-broker"][data-broker-id="${brokerId}"]`);
            await expect(row, 'the account owns its broker: it may be copied').toHaveAttribute('data-selectable', 'true');
            await row.getByTestId('pac-planner-liquidity-copy-check').check();
            await expect(row).toHaveAttribute('data-selected', 'true');
            await dialog.getByTestId('pac-planner-liquidity-copy-apply').click();
            await expect(dialog).toHaveCount(0, {timeout: UI_TIMEOUT_MS});

            const copied = planner.locator('[data-testid="pac-planner-cash"][data-origin="copied"]');
            await expect(copied, `the broker moved ${CURRENCY} only: one copied cash row`).toHaveCount(1, {timeout: UI_TIMEOUT_MS});
            await expect(copied.getByTestId('pac-planner-cash-currency')).toHaveAttribute('data-currency', CURRENCY);
            const toUse = copied.getByTestId('pac-planner-cash-selected');
            await toUse.fill(String(BUDGET));
            await expect(toUse).toHaveValue(String(BUDGET));
            await expect(copied.getByTestId('pac-planner-cash-exceeds'), 'the budget is within the copied balance').toHaveCount(0);
            await continueTo(planner, 'brokers');
        });

        await test.step('Brokers: the broker came with its cash, with one order mode in the currency it moved', async () => {
            const broker = planner.locator('[data-testid="pac-planner-broker"][data-origin="copied"]');
            await expect(broker).toHaveCount(1);
            await expect(broker.getByTestId('pac-planner-broker-mode')).toHaveCount(1);
            await expect(broker.getByTestId('pac-planner-broker-mode')).toHaveAttribute('data-currency', CURRENCY);
            await continueTo(planner, 'assets');
        });

        await test.step('Assets: «Your Assets» brings the two positions, then their stored prices', async () => {
            await planner.getByTestId('pac-planner-owned-assets-open').click();
            const dialog = page.getByTestId('pac-planner-owned-assets');
            const body = dialog.getByTestId('pac-planner-owned-assets-body');
            await expect(body, 'the positions of the account were not read').toHaveAttribute('data-state', 'ready', {timeout: READ_TIMEOUT_MS});
            for (const asset of assets) {
                await expect(body.locator(`[data-testid="pac-planner-owned-assets-asset"][data-asset-id="${asset.id}"]`), `${asset.name} is held in the account's broker: listed, and ticked`).toHaveAttribute('data-selected', 'true');
            }
            const count = body.getByTestId('pac-planner-owned-assets-count');
            await expect(count, 'the account holds these two Assets and nothing else').toHaveAttribute('data-total', String(assets.length));
            await expect(count).toHaveAttribute('data-selected', String(assets.length));
            await dialog.getByTestId('pac-planner-owned-assets-apply').click();
            await expect(dialog).toHaveCount(0, {timeout: UI_TIMEOUT_MS});

            // The draft is this test's own: its Asset cards are exactly the two just added, each read once (AssetsStep, `readFacts`).
            const cards = planner.locator('[data-testid="pac-planner-asset"]');
            await expect(cards).toHaveCount(assets.length, {timeout: UI_TIMEOUT_MS});
            for (let index = 0; index < assets.length; index += 1) {
                await expect(cards.nth(index), 'its stored price was copied').toHaveAttribute('data-price', 'set', {timeout: READ_TIMEOUT_MS});
                await expect(cards.nth(index), 'the price stays LibreFolio’s («Auto»)').toHaveAttribute('data-price-mode', 'auto');
            }
            await expect(planner.getByTestId('pac-planner-assets')).toHaveAttribute('data-busy', 'false', {timeout: READ_TIMEOUT_MS});
            await continueTo(planner, 'routing');
        });

        await test.step('Routing: each Asset may be bought on the broker', async () => {
            const routes = planner.locator('[data-testid="pac-planner-route"]');
            await expect(routes, 'one route per Asset on the one broker').toHaveCount(assets.length);
            for (let index = 0; index < assets.length; index += 1) {
                await expect(routes.nth(index), 'a new route starts allowed').toHaveAttribute('data-enabled', 'true');
                await expect(routes.nth(index), `the broker has an order mode in ${CURRENCY}`).toHaveAttribute('data-ready', 'true');
            }
            await continueTo(planner, 'targets');
        });

        await test.step('Targets: «Copy current distribution» turns the weights of the positions into the targets', async () => {
            await planner.getByTestId('pac-planner-distribution-open').click();
            const dialog = page.getByTestId('pac-planner-distribution');
            const body = dialog.getByTestId('pac-planner-distribution-body');
            await expect(body, 'the current distribution was not read').toHaveAttribute('data-state', 'ready', {timeout: READ_TIMEOUT_MS});
            await expect(body, 'both positions are priced: the distribution is complete').toHaveAttribute('data-status', 'complete');
            await dialog.getByTestId('pac-planner-distribution-apply').click();
            // No target was set yet, so nothing is replaced and nothing is asked (DistributionDialog.svelte, `use`).
            await expect(page.getByTestId('pac-planner-distribution-confirm')).toHaveCount(0);
            await expect(dialog).toHaveCount(0, {timeout: UI_TIMEOUT_MS});
            await expect(planner.getByTestId('pac-planner-targets-control'), 'the copied weights add up to 100%').toHaveAttribute('data-state', 'balanced');
            // Every amount is in one currency: no rate is needed, so the FX step is not on the way (draft, `visibleSteps`).
            await continueTo(planner, 'strategy');
            await continueTo(planner, 'review');
        });

        const calculation = await test.step('Review → «Calculate plan»: the tool’s own request carries what was copied, its answer is a proven plan', async () => {
            const review = planner.getByTestId('pac-planner-review');
            await expect(review.getByTestId('pac-planner-review-problems'), 'the draft is complete').toHaveCount(0);
            const calculate = review.getByTestId('pac-planner-calculate');
            await expect(calculate).toBeEnabled();

            const computed = armed(page.waitForResponse((response) => isCompute(response.request()), {timeout: CALCULATION_TIMEOUT_MS}));
            const since = await eventSeq(page);
            await calculate.click();
            const response = await computed;
            const ask = response.request().postDataJSON() as ComputeAsk;
            const answer = await jsonFrom<ComputeAnswer>(response, `POST ${TOOLS_COMPUTE_PATH}`);

            expect(
                ask.items.map((item) => item.tool_code),
                'one calculation, by the tool the hub opened',
            ).toEqual([code]);
            const [item] = ask.items;
            const sent = item.parameters;
            expect(sent.valuation_currency).toBe(CURRENCY);
            const sourceOf = new Map(sent.assets.map((asset) => [asset.asset_id, asset.identity.source_asset_id ?? null]));
            const brokerOf = new Map(sent.brokers.map((broker) => [broker.broker_id, broker.identity.source_broker_id ?? null]));
            const bySource = <T extends {source: string | null}>(rows: T[]): T[] => [...rows].sort((left, right) => String(left.source).localeCompare(String(right.source)));
            expect(bySource(sent.assets.map((asset) => ({source: asset.identity.source_asset_id ?? null, price: asset.quote ? Number(asset.quote.amount) : null, currency: asset.quote?.currency ?? null}))), 'the two Assets held, each with the price LibreFolio stores').toEqual(
                bySource(assets.map((asset) => ({source: String(asset.id), price: asset.price, currency: CURRENCY}))),
            );
            expect(
                (sent.existing_cash ?? []).map((cash) => ({broker: brokerOf.get(cash.broker_id) ?? null, available: [Number(cash.available.amount), cash.available.currency], selected: [Number(cash.selected.amount), cash.selected.currency]})),
                "the broker's cash: its whole balance available, the budget to use",
            ).toEqual([{broker: String(brokerId), available: [CASH_LEFT, CURRENCY], selected: [BUDGET, CURRENCY]}]);
            expect(sent.contributions ?? [], 'no money but the copied cash').toEqual([]);
            expect(bySource(sent.target_weights.map((target) => ({source: sourceOf.get(target.asset_id) ?? null, weight: Number(target.weight)}))), 'the targets are the current distribution of the positions').toEqual(
                bySource(assets.map((asset) => ({source: String(asset.id), weight: asset.weight}))),
            );

            const outcome = answer.results.find((result) => result.correlation_id === item.correlation_id);
            if (outcome?.status !== 'success' || !outcome.result) throw new Error(`The tool did not answer the calculation with a result: ${JSON.stringify(outcome ?? answer)}`);
            const result = outcome.result;
            expect(result.result_state, `the engine must find a plan; its issues: ${JSON.stringify(result.issues)}`).toBe('ready_incumbent');
            expect({proof: result.proof?.kind, stop: result.stop_reason}, 'a small problem is solved to the proven optimum').toEqual({proof: 'optimal_proven', stop: 'completed'});
            const solution = result.primary_solution;
            if (!solution) throw new Error(`A ready plan without its solution: ${JSON.stringify(result)}`);
            expect(solution.asset_rows.map((row) => row.asset_id).sort(), 'one result row per Asset sent').toEqual([...sourceOf.keys()].sort());
            expect(solution.order_rows.length, 'the plan buys').toBeGreaterThan(0);
            return {since, result, solution, sourceOf};
        });
        const {result, solution, sourceOf} = calculation;
        const places = minorPlaces(result, CURRENCY);
        const nameOf = (plannerAssetId: string): string => assetBySource.get(sourceOf.get(plannerAssetId) ?? '')?.name ?? plannerAssetId;
        const view = planner.getByTestId('pac-planner-result');

        await test.step('the run ends on the answer’s state, and says so', async () => {
            await expect(planner, 'the calculation must end').toHaveAttribute('data-busy', 'false', {timeout: CALCULATION_TIMEOUT_MS});
            await expect(planner).toHaveAttribute('data-view', 'result');
            await expect(planner, 'the run state is the answer’s').toHaveAttribute('data-state', result.result_state);
            const completed = await waitForEvent(page, 'tool.pac-plan.completed', {since: calculation.since, timeout: UI_TIMEOUT_MS});
            expect(completed.detail, 'the planner reports the plan it received').toMatchObject({resultState: result.result_state, issues: result.issues.length});
            await expect(view).toHaveAttribute('data-state', result.result_state);
            await expect(view, 'the result describes the draft on screen').toHaveAttribute('data-stale', 'false');
            await expect(planner.getByTestId('pac-planner-refresh-notice'), 'every copied fact was found again in LibreFolio before the calculation').toHaveAttribute('data-missing', '0');
            const outcome = view.getByTestId('pac-planner-outcome');
            await expect(outcome).toHaveAttribute('data-state', result.result_state);
            await expect(outcome.locator('[data-testid="pac-planner-outcome-badge"][data-badge="availability"]'), 'a plan is available').toHaveAttribute('data-tone', 'success');
            await expect(outcome.locator('[data-testid="pac-planner-outcome-badge"][data-badge="proof"]'), 'and it is proven').toHaveAttribute('data-tone', 'success');
        });

        await test.step('per Asset: the value after the plan, the ideal value and the signed gap are the answer’s, and what is bought fits the budget', async () => {
            const allocation = resultSection(view, 'allocation');
            await expect(allocation, 'the allocation per Asset opens by default').toHaveAttribute('data-open', 'true');
            const table = allocation.getByTestId('pac-planner-assets-table');
            const bought: Amount[] = [];
            for (const row of solution.asset_rows) {
                const name = nameOf(row.asset_id);
                const shown = table.locator(`[data-row-id="${attr(row.asset_id)}"]`);
                await expect(shown, `${name}: one row`).toHaveCount(1, {timeout: UI_TIMEOUT_MS});
                bought.push(await shows(shown.locator('[data-column-id="finalValue"]'), computedAmount(row.final_value, places, false, `${name}, value after the plan`), `${name}, value after the plan`));
                await shows(shown.locator('[data-column-id="targetValue"]'), computedAmount(row.target_value, places, false, `${name}, ideal value`), `${name}, ideal value`);
                await shows(shown.getByTestId('pac-planner-assets-residual'), computedAmount(row.residual, places, true, `${name}, gap from the ideal`), `${name}, gap from the ideal`);
            }
            await shows(table.getByTestId('dt-footer-finalValue'), computedAmount(solution.accounting.final_invested, places, false, 'total value after the plan'), 'total value after the plan');
            await shows(table.getByTestId('dt-footer-targetValue'), computedAmount(solution.accounting.fixed_reference, places, false, 'base of the targets'), 'base of the targets');
            expectWithinBudget(bought, 'The values after the plan shown per Asset');
        });

        await test.step('per order: the amount and the fee are the answer’s, and what leaves the cash fits the budget', async () => {
            const plan = resultSection(view, 'plan');
            await expect(plan, 'the operational plan opens by default').toHaveAttribute('data-open', 'true');
            const spent: Amount[] = [];
            for (const order of solution.order_rows) {
                const what = `order ${order.order_id} (${nameOf(order.asset_id)})`;
                expect([order.cash_debit.currency, order.fee.currency], `${what}: paid in ${CURRENCY}, the one currency here`).toEqual([CURRENCY, CURRENCY]);
                const shown = plan.locator(`[data-testid="pac-planner-plan-orders"][data-broker="${attr(order.broker_id)}"] [data-row-id="${attr(order.order_id)}"]`);
                await expect(shown, `${what}: one row in the orders of its broker`).toHaveCount(1, {timeout: UI_TIMEOUT_MS});
                await expect(shown.getByTestId('pac-planner-plan-order'), `${what}: for the Asset the answer names`).toHaveAttribute('data-asset', order.asset_id);
                spent.push(await shows(shown.locator('[data-column-id="cashDebit"]'), postedAmount(order.cash_debit, places, `${what}, amount`), `${what}, amount`));
                spent.push(await shows(shown.locator('[data-column-id="fee"]'), postedAmount(order.fee, places, `${what}, fee`), `${what}, fee`));
            }
            expectWithinBudget(spent, 'The order amounts and fees shown');
        });

        await test.step('proof: the verdict on screen is the answer’s', async () => {
            // «Proof and timings» opens the section — never closes it — and brings it into view (ResultView.svelte, `gotoProof`).
            await view.getByTestId('pac-planner-goto-proof').click();
            const proof = resultSection(view, 'proof');
            await expect(proof).toHaveAttribute('data-open', 'true', {timeout: UI_TIMEOUT_MS});
            await expect(proof.getByTestId('pac-planner-proof'), 'the proof shown is the answer’s').toHaveAttribute('data-proof', result.proof?.kind ?? '');
        });
    });
});
