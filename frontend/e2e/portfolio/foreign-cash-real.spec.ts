/**
 * Foreign cash on real data — release 1.2, gap 2: the «FX on cash» row of the Performance view and the daily
 * revaluation of foreign cash, until now proven by backend tests only (`test_portfolio_service_native_cash.py`,
 * `TestFxOnCashContributionRows`, and `test_portfolio_engine/test_foreign_cash_revaluation.py`).
 *
 * The feature. Foreign cash is valued every day at that day's rate (`NativeCash.value_at`): the headline cash moves
 * with the rate while the native balances do not, and it is the sum of the broker cards. What the rate did to each
 * broker's foreign cash over the period — its foreign balances at the day's rate at both ends of the window, less
 * the window's foreign movements at their own dates (`NativeCash.exchange_results`) — is one «FX on cash» row of
 * `positions_contribution.other_effects` per broker (category Other), after the unallocated income and cost rows,
 * in access order; the reconciliation residual drops by the same amount.
 *
 * The scenario, on a disposable account that owns the whole dashboard and reports in EUR:
 *   - X, a currency reserved for this spec (below), with two MANUAL rates: EUR/X 1.25 on d1 (1 X = 0.8 EUR) and 1.6
 *     on d2 (1 X = 0.625 EUR); every day in between falls back on d1's rate;
 *   - broker «X»: DEPOSIT 1000 X on d1, a capital of 800 EUR;
 *   - broker «EUR»: DEPOSIT 500 EUR on d1, then INTEREST 10 EUR without asset on dI;
 *   - the window is (start, d2], with d1 < start < dI < d2: the deposit of X comes before it, so the window holds no
 *     foreign movement and the exchange result is the balance times the change of the EUR value of 1 X.
 *
 * The oracle is computed in exact rationals from those inputs, never read back from the application:
 *   - FX on cash of broker «X» over (start, d2] = 1000 × (1/1.6 − 1/1.25) = −175 EUR. Over (start, d2 − 1] the rate
 *     has not moved: the result is 0 and no row is shown;
 *   - other_effects over (start, d2] = [Unallocated income +10 («EUR»), FX on cash −175 («X»)] and nothing else: no
 *     row for the EUR-only broker, and no residual — the period other result is −175, all of it exchange;
 *   - headline cash, net worth and gain/loss are the sums of the broker cards: 800 + 510 = 1310 and +10 at the end
 *     of d2 − 1, 625 + 510 = 1135 and −165 at the end of d2, while the native balances stay 1000 X and 510 EUR.
 *
 * Why two reports one day apart are the cheapest proof of «revalued daily». Between the report ending on d2 − 1 and
 * the one ending on d2 nothing is booked and the native balances are the same: the only thing that changes is the
 * rate, on d2. The cash of broker «X» going from 800 to 625 across those two consecutive days is the revaluation of
 * the very day the rate changed — not the rate of the deposit's date, which would leave it at 800 (the defect that
 * step F fixed), nor the latest rate known when the report is asked, which would already show 625 on d2 − 1. Each
 * report is checked against the sum of its own broker cards.
 *
 * On screen, the Dashboard of the window (start, d2]: the net worth reads the revalued cash (the account holds
 * nothing else), and the Performance × table view shows the «FX on cash» row of broker «X» — found by the key the
 * component derives from the order of the page's own `other_effects`, never by a position on screen — with the
 * oracle's digits and sign. No text is read: digits, a sign, test ids and ISO codes only.
 *
 * Ownership. The account owns every row the assertions read; its brokers (with their transactions) and the account
 * are deleted by id when the test ends, pass or fail. FX rates and routes are global tables, so the spec reserves
 * one currency per Playwright project — sorting after EUR, so the rates are stored as given, and used by no other
 * test, seed or spec — deletes its leftovers first, verifies the pair is empty, and deletes it at the end.
 */

import {expect, test as base, type APIRequestContext, type Page, type Request} from '../fixtures/playwright';
import {schemas} from '../../src/lib/api/generated';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso, todayIso} from '../fixtures/dates';
import {deleteDisposableUser, prepareOnboardingAccount, registerDisposableUser, type DisposableUser} from '../fixtures/onboarding-accounts';
import {uniqueSuffix} from '../fixtures/unique';

const API = '/api/v1';
const REPORT_PATH = `${API}/portfolio/report`;
const FX_RATE_PATH = `${API}/fx/currencies/rate`;
const FX_CONVERT_PATH = `${API}/fx/currencies/convert`;
const FX_ROUTES_PATH = `${API}/fx/providers/routes`;

/**
 * The currency reserved for this spec, one per Playwright project, because FX rates and routes are global rows. Each
 * sorts after EUR, so the pair is stored as EUR-X with the rates as given, and none is used by any other test, seed
 * or spec. The runner runs the desktop project only; the mobile code exists so that a manual run of both projects
 * never shares a pair.
 */
const RESERVED_CURRENCY: Readonly<Record<string, string>> = {desktop: 'NAD', mobile: 'MZN'};

/** The inputs. Every expected figure below is computed from these, exactly. */
const X_PER_EUR_ON_D1 = '1.25';
const X_PER_EUR_ON_D2 = '1.6';
const X_DEPOSIT = '1000';
const EUR_DEPOSIT = '500';
const EUR_INTEREST = '10';

/** The backend's descriptions of the two rows this account produces: a contract of the API, not a label. */
const FX_ON_CASH = 'FX on cash';
const UNALLOCATED_INCOME = 'Unallocated income';

type Money = {code: string; amount: string};
type EffectRow = {description: string; category: string; period_pnl: string; broker_id?: number | null; broker_name?: string | null};
type BrokerCard = {broker_id: number; broker_name: string; net_worth: Money; gain_loss: Money; cash_total: Money; cash_balances?: Money[]};
type ReportSummary = {net_worth: Money; cash_total: Money; total_gain_loss: Money; cash_balances?: Money[]; by_broker?: BrokerCard[] | null; period_other_result?: Money | null};
type ReportBody = {metadata?: {target_currency?: string} | null; summary?: ReportSummary | null; positions_contribution?: {other_effects?: EffectRow[]} | null};
type ReportRequestBody = {include_summary?: boolean; include_history?: boolean; include_positions_contribution?: boolean; date_range?: {start?: string; end?: string} | null};
type CommitBody = {committed: boolean; issues?: unknown[]};
type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type Owned = {user: DisposableUser | null; brokerIds: number[]; fxQuotes: string[]};
type OwnedBroker = {id: number; name: string};

// ---------------------------------------------------------------------------
// Exact arithmetic: the oracle
// ---------------------------------------------------------------------------

function gcd(a: bigint, b: bigint): bigint {
    while (b !== 0n) [a, b] = [b, a % b];
    return a === 0n ? 1n : a;
}

/**
 * An exact rational, `n / d` in lowest terms with `d > 0`: the oracle's arithmetic. The backend computes in Decimal and
 * answers fixed-point strings; a binary float would round 1/1.25 and turn an exact comparison into a tolerance.
 */
class Exact {
    private constructor(
        readonly n: bigint,
        readonly d: bigint,
    ) {}

    /** A plain decimal string, as the API writes one (`-175.000`, `1000`). */
    static of(text: string): Exact {
        const match = /^([-+]?)(\d+)(?:\.(\d*))?$/.exec(text.trim());
        if (!match) throw new Error(`"${text}" is not a plain decimal`);
        const [, sign, whole, fraction = ''] = match;
        return Exact.ratio(BigInt(`${sign === '-' ? '-' : ''}${whole}${fraction}`), 10n ** BigInt(fraction.length));
    }

    private static ratio(n: bigint, d: bigint): Exact {
        if (d === 0n) throw new Error('division by zero');
        const sign = d < 0n ? -1n : 1n;
        const divisor = gcd(n < 0n ? -n : n, d < 0n ? -d : d);
        return new Exact((sign * n) / divisor, (sign * d) / divisor);
    }

    plus(other: Exact): Exact {
        return Exact.ratio(this.n * other.d + other.n * this.d, this.d * other.d);
    }

    minus(other: Exact): Exact {
        return Exact.ratio(this.n * other.d - other.n * this.d, this.d * other.d);
    }

    times(other: Exact): Exact {
        return Exact.ratio(this.n * other.n, this.d * other.d);
    }

    inverse(): Exact {
        return Exact.ratio(this.d, this.n);
    }

    get negative(): boolean {
        return this.n < 0n;
    }

    /** The plain decimal without trailing zeros (`-175`, `0.625`). Throws when the value has no finite decimal form. */
    toString(): string {
        let rest = this.d;
        let twos = 0;
        let fives = 0;
        while (rest % 2n === 0n) {
            rest /= 2n;
            twos += 1;
        }
        while (rest % 5n === 0n) {
            rest /= 5n;
            fives += 1;
        }
        if (rest !== 1n) throw new Error(`${this.n}/${this.d} has no finite decimal form: pick rates whose inverse is exact`);
        const scale = Math.max(twos, fives);
        const scaled = (this.n * 10n ** BigInt(scale)) / this.d;
        const digits = (scaled < 0n ? -scaled : scaled).toString().padStart(scale + 1, '0');
        const whole = digits.slice(0, digits.length - scale);
        const fraction = digits.slice(digits.length - scale).replace(/0+$/, '');
        return `${scaled < 0n ? '-' : ''}${whole}${fraction ? `.${fraction}` : ''}`;
    }

    /** The digits a two-decimal amount shows once sign and separators are dropped: 1135 → `113500`, −175 → `17500`. */
    centsDigits(): string {
        const abs = this.n < 0n ? -this.n : this.n;
        if ((abs * 100n) % this.d !== 0n) throw new Error(`${this.toString()} is not a whole number of cents`);
        const cents = (abs * 100n) / this.d;
        return `${cents / 100n}${(cents % 100n).toString().padStart(2, '0')}`;
    }
}

const sum = (values: Exact[]): Exact => values.reduce((total, value) => total.plus(value), Exact.of('0'));

/** An API amount as an exact decimal string, so `-175.000` and `-175` compare equal and `-175.0001` does not. */
function exactly(text: string | null | undefined, what: string): string {
    if (text == null) throw new Error(`${what}: the API returned no amount`);
    return Exact.of(text).toString();
}

function money(value: Money | null | undefined, what: string): {code: string; amount: string} {
    if (!value) throw new Error(`${what}: the API returned no amount`);
    return {code: value.code, amount: exactly(value.amount, what)};
}

function eur(value: Exact): {code: string; amount: string} {
    return {code: 'EUR', amount: value.toString()};
}

// ---------------------------------------------------------------------------
// HTTP
// ---------------------------------------------------------------------------

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

function reportRequestBody(req: Request): ReportRequestBody | null {
    if (req.method() !== 'POST' || new URL(req.url()).pathname !== REPORT_PATH) return null;
    return req.postDataJSON() as ReportRequestBody | null;
}

/** The dashboard's main load: the request that carries the summary and the daily history. */
function isMainReport(req: Request): boolean {
    const body = reportRequestBody(req);
    return body?.include_summary === true && body.include_history === true && body.include_positions_contribution !== true;
}

/** The Performance view's lazy load: the request that carries `positions_contribution`. */
function isContributionReport(req: Request): boolean {
    return reportRequestBody(req)?.include_positions_contribution === true;
}

/** The report of a window, with the broker cards and the contribution, read through the API as the account. */
async function readReport(page: Page, range: {start: string; end: string}, purpose: string): Promise<ReportBody> {
    const query = {date_range: range, include_summary: true, include_history: false, include_allocation_history: false, include_breakdown: true, include_positions_contribution: true};
    schemas.PortfolioReportQuery.parse(query);
    return jsonFrom<ReportBody>(await page.request.post(REPORT_PATH, {data: query}), purpose);
}

function summaryOf(report: ReportBody, what: string): ReportSummary {
    if (!report.summary) throw new Error(`${what}: the report has no summary`);
    return report.summary;
}

/** other_effects with every amount exact, in the order the API gave them. */
function effectRows(report: ReportBody, what: string): Array<{description: string; category: string; period_pnl: string; broker_id: number | null; broker_name: string | null}> {
    const effects = report.positions_contribution?.other_effects;
    if (!effects) throw new Error(`${what}: the report has no positions_contribution.other_effects`);
    return effects.map((effect) => ({description: effect.description, category: effect.category, period_pnl: exactly(effect.period_pnl, `${what}: ${effect.description}`), broker_id: effect.broker_id ?? null, broker_name: effect.broker_name ?? null}));
}

/** Native balances as [code, exact amount], by code: their order is not the subject. */
function nativeBalances(balances: Money[] | undefined, what: string): Array<[string, string]> {
    return (balances ?? []).map((balance): [string, string] => [balance.code, exactly(balance.amount, what)]).sort(([a], [b]) => a.localeCompare(b));
}

function digitsOf(text: string | null): string {
    return (text ?? '').replace(/\D/g, '');
}

// ---------------------------------------------------------------------------
// FX pair: reset, configure, probe
// ---------------------------------------------------------------------------

function reservedCurrency(): string {
    const project = test.info().project.name;
    const code = RESERVED_CURRENCY[project];
    if (!code) throw new Error(`No currency is reserved for project "${project}": reserve one that sorts after EUR and that no other test, seed or spec uses`);
    return code;
}

/** Delete every rate and every route of EUR-`quote`. Both deletions succeed (with a count of 0) when there is nothing. */
async function deleteReservedPair(page: Page, quote: string): Promise<void> {
    const rates = await jsonFrom<{results: Array<{base: string; quote: string; success: boolean}>}>(await page.request.delete(FX_RATE_PATH, {data: [{from: 'EUR', to: quote, delete_all: true}]}), `delete every EUR-${quote} rate`);
    expect(rates.results.find((item) => item.base === 'EUR' && item.quote === quote)?.success, `delete every EUR-${quote} rate`).toBe(true);
    const routes = await jsonFrom<{results: Array<{base: string; quote: string; success: boolean}>}>(await page.request.delete(FX_ROUTES_PATH, {data: [{base: 'EUR', quote}]}), `delete the EUR-${quote} routes`);
    expect(routes.results.find((item) => item.base === 'EUR' && item.quote === quote)?.success, `delete the EUR-${quote} routes`).toBe(true);
}

/** Start from an empty reserved pair — leftovers of an interrupted run deleted — and verify it, not infer it. */
async function resetReservedPair(page: Page, quote: string): Promise<void> {
    await deleteReservedPair(page, quote);
    const routes = await jsonFrom<{items?: Array<{base: string; quote: string}>}>(await page.request.get(FX_ROUTES_PATH), 'list the FX routes');
    expect(
        (routes.items ?? []).filter((route) => route.base === 'EUR' && route.quote === quote),
        `precondition: no EUR-${quote} route is configured`,
    ).toEqual([]);
    const probe = await page.request.post(FX_CONVERT_PATH, {data: [{from_amount: {code: quote, amount: '1'}, to: 'EUR', date_range: {start: todayIso()}}]});
    expect(probe.status(), `precondition: no EUR-${quote} rate exists, so converting ${quote} today must fail — got ${await probe.text()}`).toBe(404);
}

/** Rates typed in by hand (source MANUAL), as the user would: EUR sorts first, so they are stored as given. */
async function storeManualRates(page: Page, quote: string, points: Array<{date: string; rate: string}>): Promise<void> {
    const rates = points.map((point) => ({date: point.date, base: 'EUR', quote, rate: point.rate}));
    for (const rate of rates) schemas.FXUpsertItem.parse(rate);
    const stored = await jsonFrom<{results: Array<{success: boolean; date: string; base: string; quote: string; rate: string}>}>(await page.request.post(FX_RATE_PATH, {data: rates}), `store the EUR-${quote} rates`);
    expect(
        stored.results.map((item) => ({success: item.success, date: item.date, base: item.base, quote: item.quote, rate: exactly(item.rate, `the EUR-${quote} rate of ${item.date}`)})),
        `every EUR-${quote} rate is stored as given`,
    ).toEqual(rates.map((rate) => ({success: true, date: rate.date, base: 'EUR', quote, rate: exactly(rate.rate, 'input rate')})));
}

// ---------------------------------------------------------------------------
// Owned rows: seeding and cleanup
// ---------------------------------------------------------------------------

/** Every id is recorded for cleanup before it is checked. */
async function createBroker(page: Page, owned: Owned, name: string): Promise<OwnedBroker> {
    const brokers = await jsonFrom<{results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>}>(await page.request.post(`${API}/brokers`, {data: [{name, opened_at: daysAgoIso(400)}]}), 'create an owned broker');
    const broker = brokers.results.find((item) => item.name === name);
    if (typeof broker?.broker_id === 'number') owned.brokerIds.push(broker.broker_id);
    if (!broker?.success || typeof broker.broker_id !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(brokers)}`);
    return {id: broker.broker_id, name};
}

async function commitTransactions(page: Page, batch: {creates: unknown[]}, purpose: string): Promise<void> {
    const committed = await jsonFrom<CommitBody>(await page.request.post(`${API}/transactions/commit`, {data: batch}), purpose);
    expect(committed.committed, `${purpose}: rolled back — ${JSON.stringify(committed.issues ?? [])}`).toBe(true);
}

/**
 * Delete in dependency order, each step scoped to an id this test recorded.
 *
 * The page is unmounted first, so no reload of the dashboard reads rows while they go. The brokers go first (`force`
 * takes their transactions with them), the reserved FX pair after them, the account last. Brokers and FX rows are
 * deleted by the account that created them (`page.request` shares the browser's session); the account itself through
 * the standalone `request` context it was registered with, which signs in on its own.
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
    await attempt('unmount the dashboard', async () => {
        await page.goto('about:blank');
    });
    for (const brokerId of owned.brokerIds) {
        await attempt(`broker ${brokerId}`, async () => {
            const result = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`), 'delete an owned broker and its transactions');
            expect(result.results.find((item) => item.id === brokerId)?.success).toBe(true);
        });
    }
    for (const quote of owned.fxQuotes) {
        await attempt(`fx pair EUR-${quote}`, async () => {
            await deleteReservedPair(page, quote);
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
        const owned: Owned = {user: null, brokerIds: [], fxQuotes: []};
        try {
            await use(owned);
        } finally {
            await cleanupOwned(page, request, owned);
        }
    },
});

// ---------------------------------------------------------------------------
// The test
// ---------------------------------------------------------------------------

test.describe('Foreign cash on real data — FX on cash and daily revaluation (release 1.2, gap 2)', () => {
    test('the FX on cash row is the exchange result of the window, and the headline cash is revalued on the day the rate moves', async ({page, request, owned}) => {
        test.setTimeout(150_000);
        const quote = reservedCurrency();
        expect(quote > 'EUR', `precondition: ${quote} sorts after EUR, so EUR-${quote} is stored with the rates as given`).toBe(true);
        // Computed once: a midnight during the run must not move a day.
        const d1 = daysAgoIso(60);
        const start = daysAgoIso(50);
        const dI = daysAgoIso(40);
        const dayBefore = daysAgoIso(31);
        const d2 = daysAgoIso(30);

        // ── The oracle, from the inputs only ──
        const unitOnD1 = Exact.of(X_PER_EUR_ON_D1).inverse(); // 1 X = 0.8 EUR
        const unitOnD2 = Exact.of(X_PER_EUR_ON_D2).inverse(); // 1 X = 0.625 EUR
        const xCapital = Exact.of(X_DEPOSIT).times(unitOnD1); // the deposit, converted at its own date: 800
        const eurCapital = Exact.of(EUR_DEPOSIT);
        const xCash = {[dayBefore]: Exact.of(X_DEPOSIT).times(unitOnD1), [d2]: Exact.of(X_DEPOSIT).times(unitOnD2)}; // 800, 625
        const eurCash = Exact.of(EUR_DEPOSIT).plus(Exact.of(EUR_INTEREST)); // 510 from dI on
        const exchange = Exact.of(X_DEPOSIT).times(unitOnD2.minus(unitOnD1)); // −175
        expect(exchange.negative, 'the scenario is a loss: X loses value against EUR on d2').toBe(true);

        const {fxBroker, eurBroker} = await test.step(`seed: EUR-${quote} ${X_PER_EUR_ON_D1} on d1 and ${X_PER_EUR_ON_D2} on d2, ${X_DEPOSIT} ${quote} at one broker, EUR and an interest at another`, async () => {
            const user = await registerDisposableUser(request, 'fxcash');
            owned.user = user;
            await prepareOnboardingAccount(page, user, []);
            owned.fxQuotes.push(quote);
            await resetReservedPair(page, quote);
            await storeManualRates(page, quote, [
                {date: d1, rate: X_PER_EUR_ON_D1},
                {date: d2, rate: X_PER_EUR_ON_D2},
            ]);
            const suffix = uniqueSuffix();
            const fxBroker = await createBroker(page, owned, `fxcash-${quote}-${suffix}`);
            const eurBroker = await createBroker(page, owned, `fxcash-EUR-${suffix}`);
            await commitTransactions(
                page,
                {
                    creates: [
                        {broker_id: fxBroker.id, type: 'DEPOSIT', date: d1, cash: {code: quote, amount: X_DEPOSIT}, description: `fxcash ${quote} deposit ${suffix}`},
                        {broker_id: eurBroker.id, type: 'DEPOSIT', date: d1, cash: {code: 'EUR', amount: EUR_DEPOSIT}, description: `fxcash EUR deposit ${suffix}`},
                        {broker_id: eurBroker.id, type: 'INTEREST', date: dI, cash: {code: 'EUR', amount: EUR_INTEREST}, description: `fxcash interest ${suffix}`},
                    ],
                },
                `commit the ${quote} deposit, the EUR deposit and the interest`,
            );
            return {fxBroker, eurBroker};
        });

        const incomeRow = {description: UNALLOCATED_INCOME, category: 'Income', period_pnl: Exact.of(EUR_INTEREST).toString(), broker_id: eurBroker.id, broker_name: eurBroker.name};
        const fxRow = {description: FX_ON_CASH, category: 'Other', period_pnl: exchange.toString(), broker_id: fxBroker.id, broker_name: fxBroker.name};
        const expectedEffects = [incomeRow, fxRow];

        await test.step(`API, window (start, d2]: one FX on cash row of ${exchange} for broker ${quote}, after the unallocated income, none for the EUR broker, no residual`, async () => {
            const report = await readReport(page, {start, end: d2}, 'report of (start, d2]');
            expect(report.metadata?.target_currency, 'precondition: the account reports in EUR, the currency of the oracle').toBe('EUR');
            expect(effectRows(report, '(start, d2]'), `other_effects of (start, d2]: the oracle is ${X_DEPOSIT} × (1/${X_PER_EUR_ON_D2} − 1/${X_PER_EUR_ON_D1}) = ${exchange}`).toEqual(expectedEffects);
            expect(money(summaryOf(report, '(start, d2]').period_other_result, 'period_other_result of (start, d2]'), 'the FX on cash row and the residual (none) add up to the period other result').toEqual(eur(exchange));
        });

        await test.step('API, window (start, d2 − 1]: the rate has not moved inside it, so no FX on cash row and nothing left over', async () => {
            const report = await readReport(page, {start, end: dayBefore}, 'report of (start, d2 − 1]');
            expect(effectRows(report, '(start, d2 − 1]'), 'other_effects of (start, d2 − 1]: the interest only').toEqual([incomeRow]);
            expect(money(summaryOf(report, '(start, d2 − 1]').period_other_result, 'period_other_result of (start, d2 − 1]')).toEqual(eur(Exact.of('0')));
        });

        await test.step(`API, two reports one day apart: the headline cash follows the rate of d2 with the native balances unchanged, and is the sum of the cards on both`, async () => {
            for (const end of [dayBefore, d2]) {
                const when = end === d2 ? 'end of d2' : 'end of d2 − 1';
                const summary = summaryOf(await readReport(page, {start, end}, `report ending on ${end}`), when);
                const expectedCards = [
                    {broker_id: fxBroker.id, cash: eur(xCash[end]), net_worth: eur(xCash[end]), gain_loss: eur(xCash[end].minus(xCapital)), balances: [[quote, Exact.of(X_DEPOSIT).toString()]]},
                    {broker_id: eurBroker.id, cash: eur(eurCash), net_worth: eur(eurCash), gain_loss: eur(eurCash.minus(eurCapital)), balances: [['EUR', eurCash.toString()]]},
                ].sort((a, b) => a.broker_id - b.broker_id);
                const cards = (summary.by_broker ?? [])
                    .map((card) => ({
                        broker_id: card.broker_id,
                        cash: money(card.cash_total, `${when}: card cash`),
                        net_worth: money(card.net_worth, `${when}: card net worth`),
                        gain_loss: money(card.gain_loss, `${when}: card gain/loss`),
                        balances: nativeBalances(card.cash_balances, `${when}: card balances`),
                    }))
                    .sort((a, b) => a.broker_id - b.broker_id);
                expect(cards, `${when}: the account's two broker cards, revalued at the day's rate`).toEqual(expectedCards);

                const headline = {cash: money(summary.cash_total, `${when}: cash_total`), net_worth: money(summary.net_worth, `${when}: net_worth`), gain_loss: money(summary.total_gain_loss, `${when}: total_gain_loss`)};
                const cardSums = {
                    cash: eur(sum(cards.map((card) => Exact.of(card.cash.amount)))),
                    net_worth: eur(sum(cards.map((card) => Exact.of(card.net_worth.amount)))),
                    gain_loss: eur(sum(cards.map((card) => Exact.of(card.gain_loss.amount)))),
                };
                expect(headline, `${when}: the headline is the sum of the broker cards`).toEqual(cardSums);
                expect(headline, `${when}: the headline the oracle expects`).toEqual({cash: eur(xCash[end].plus(eurCash)), net_worth: eur(xCash[end].plus(eurCash)), gain_loss: eur(xCash[end].plus(eurCash).minus(xCapital).minus(eurCapital))});
                expect(nativeBalances(summary.cash_balances, `${when}: balances`), `${when}: the native balances do not move`).toEqual([
                    ['EUR', eurCash.toString()],
                    [quote, Exact.of(X_DEPOSIT).toString()],
                ]);
            }
        });

        const navOnD2 = xCash[d2].plus(eurCash);

        await test.step(`Dashboard of (start, d2]: the net worth reads the revalued cash, ${navOnD2} EUR`, async () => {
            const mainAnswer = armed(page.waitForResponse((res) => isMainReport(res.request()), {timeout: 30_000}));
            await page.goto(`/dashboard?${new URLSearchParams({start, end: d2}).toString()}`);
            const answer = await mainAnswer;
            expect((answer.request().postDataJSON() as ReportRequestBody).date_range, 'precondition: the URL seeds the dashboard period').toMatchObject({start, end: d2});
            const shown = await jsonFrom<ReportBody>(answer, 'dashboard report');
            expect(shown.metadata?.target_currency, 'precondition: the dashboard reports in EUR').toBe('EUR');
            const summary = summaryOf(shown, 'dashboard report');
            expect({cash: money(summary.cash_total, 'dashboard cash_total'), net_worth: money(summary.net_worth, 'dashboard net_worth')}, 'the report the dashboard asked for holds the revalued cash, and nothing else').toEqual({cash: eur(navOnD2), net_worth: eur(navOnD2)});

            await waitForSettled(page.getByTestId('dashboard-page'), 30_000);
            const netWorth = page.getByTestId('kpi-net-worth').getByTestId('kpi-value');
            await expect(netWorth).toBeVisible({timeout: 15_000});
            // The value is tweened: it reaches the figure, it does not start there.
            await expect.poll(async () => digitsOf(await netWorth.textContent()), {timeout: 15_000, message: `the net worth reads ${navOnD2} once separators are dropped`}).toBe(navOnD2.centsDigits());
            await expect(netWorth, 'a positive net worth carries no minus').not.toHaveText(/[-−]/);
        });

        await test.step(`Dashboard, Performance × table: the FX on cash row of broker ${quote}, keyed by the page's own order, reads ${exchange}`, async () => {
            // Armed before the clicks: the Performance view asks for the contribution as soon as it shows.
            const contributionAnswer = armed(page.waitForResponse((res) => isContributionReport(res.request()), {timeout: 30_000}));
            await page.getByTestId('dashboard-tab-posizioni').click();
            const panel = page.getByTestId('positions-panel');
            await expect(panel).toBeVisible({timeout: 15_000});
            // Setters, not toggles: a click on the view already shown changes nothing.
            await panel.getByTestId('positions-toggle-performance').click();
            await panel.getByTestId('positions-toggle-table').click();

            const answer = await contributionAnswer;
            expect((answer.request().postDataJSON() as ReportRequestBody).date_range, 'precondition: the contribution covers the dashboard period').toMatchObject({start, end: d2});
            const rows = effectRows(await jsonFrom<ReportBody>(answer, 'the Performance view contribution'), 'the Performance view contribution');
            expect(rows, 'the page receives the oracle rows').toEqual(expectedEffects);

            // The key OtherPeriodEffectsTable derives: effect-{index in other_effects}-{category}-{broker_id}.
            const keyOf = (description: string, brokerId: number) => {
                const index = rows.findIndex((row) => row.description === description && row.broker_id === brokerId);
                expect(index, `the page's other_effects carry a ${description} row for broker ${brokerId}`).toBeGreaterThanOrEqual(0);
                return `effect-${index}-${rows[index].category}-${brokerId}`;
            };
            const fxKey = keyOf(FX_ON_CASH, fxBroker.id);
            const incomeKey = keyOf(UNALLOCATED_INCOME, eurBroker.id);

            await waitForSettled(panel, 30_000);
            const fxRowOnScreen = page.getByTestId(`other-period-effects-row-${fxKey}`);
            await expect(fxRowOnScreen, `the FX on cash row of broker ${quote} is on screen (${fxKey})`).toBeVisible({timeout: 15_000});
            await expect(fxRowOnScreen.getByTestId(`broker-badge-${fxBroker.id}`), 'the row names its broker through the broker badge').toBeVisible();
            const fxAmount = page.getByTestId(`other-period-effects-pnl-${fxKey}`);
            await expect.poll(async () => digitsOf(await fxAmount.textContent()), {timeout: 10_000, message: `${fxKey} reads ${exchange} once separators are dropped`}).toBe(exchange.centsDigits());
            await expect(fxAmount, 'the exchange loss carries the minus').toHaveText(/[-−]/);
            await expect(fxAmount, 'and no plus').not.toHaveText(/\+/);

            // The other row of the account, under its own key: the two rows are not confused.
            const incomeAmount = page.getByTestId(`other-period-effects-pnl-${incomeKey}`);
            await expect.poll(async () => digitsOf(await incomeAmount.textContent()), {timeout: 10_000, message: `${incomeKey} reads +${EUR_INTEREST}`}).toBe(Exact.of(EUR_INTEREST).centsDigits());
            await expect(incomeAmount, 'the interest is a gain and carries the plus').toHaveText(/\+/);
        });
    });
});
