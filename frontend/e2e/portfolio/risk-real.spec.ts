/**
 * Risk on real data, from the wire to the screen — gap 1 of the 1.2 E2E list (devWiki:
 * `decisions/e2e-gaps-of-1-2-before-release`).
 *
 * Every other risk E2E answers `/risk/query` with `page.route` (`risk-mocks.ts`): no real answer of the engine ever
 * reached the screen, so a drift between the real contract and the mocks would go unnoticed. Nothing is routed here.
 * A disposable account holds two seeded stocks with a long price history, the Dashboard's Risk tab asks the real
 * engine, and each test follows the page's own answer to the screen:
 *
 *   R1 — level 1 prints the engine's daily VaR (the histogram's cut) and its daily and monthly CVaR (the cards), the
 *        histogram is the engine's distribution (bins, observations), and the level shows no error and no empty state;
 *   R2 — level 4's historical replay, run for real over the panel's period, prints the engine's composition return and,
 *        per holding, its own return and its contribution.
 *
 * Both check every risk answer the page received against the generated Zod schemas — the contract the mocks were
 * supposed to mirror. A figure is compared on its sign and its digits, at the precision the screen prints it: the
 * format follows the interface language, the value does not. No oracle: whether the engine computes right is the
 * business of `test_risk_metrics_oracle.py` and `test_risk_api.py`; this spec proves the screen says what it said.
 *
 * Which answer is on screen. The panel shows the answer to the last question it asked — an earlier one may have been
 * superseded or discarded (`riskPanelController.svelte.ts`, `loadBaseAttempt`) — so every risk request is recorded from
 * before the navigation, and the screen is compared with the answer to the last one asked once nothing is left to ask:
 * the panel's `data-busy="false"`, and the page's Refresh (`sync-button`) idle, which waits for every base wave of the
 * panel — the panel has no Refresh of its own (Y11, decision 48).
 *
 * Ownership. Each test registers its own account, which owns the whole portfolio under test: one broker, a deposit and
 * two purchases of seeded stocks (Apple and Microsoft: global rows, only read here) dated far enough back for the
 * monthly VaR's minimum window, the precondition read back from the seeded quotes rather than assumed. The broker (with
 * its transactions) and the account are deleted by id in the fixture teardown; no global row is written.
 *
 * Offline. The seed's prices and EUR-USD rates are read, never synced: the Dashboard polls no live price, and no sync
 * control is pressed.
 */

import {expect, test as base, type APIRequestContext, type Locator, type Page, type Request} from '../fixtures/playwright';
import {schemas} from '../../src/lib/api/generated';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso, localIso, todayIso} from '../fixtures/dates';
import {deleteDisposableUser, prepareOnboardingAccount, registerDisposableUser, type DisposableUser} from '../fixtures/onboarding-accounts';
import {uniqueSuffix} from '../fixtures/unique';

const API = '/api/v1';
const RISK_API = `${API}/risk`;
const RISK_QUERY_PATH = `${RISK_API}/query`;
const RISK_CATALOG_PATH = `${RISK_API}/catalog`;
const RISK_SCENARIO_CATALOG_PATH = `${RISK_API}/scenario-catalog`;
const RISK_ELIGIBILITY_PATH = `${RISK_API}/eligibility`;

/** Two stocks the seed quotes on every weekday of its year of prices (`populate_mock_data.py`, `populate_price_history`). */
const SEEDED_STOCKS = ['Apple Inc.', 'Microsoft Corporation'] as const;
/** Units bought of each. */
const UNITS = 10;
/**
 * The purchase, in days before today, moved back to a weekday (the seed quotes no weekend). The period it opens must
 * hold the monthly VaR's minimum — 20 windows of about 21 observations, two months of weekdays — and stay inside the
 * seed's year of prices: 200 days does both with room to spare.
 */
const BUY_DAYS_AGO = 200;
/** Fewest days of its own quotes a holding must show in the period: well above the ~41 the monthly VaR needs. */
const MIN_QUOTED_DAYS = 60;
/** How old a holding's last quote may be at the period's end (`STALE_PRICE_THRESHOLD_DAYS`): a weekend, not a gap. */
const MAX_QUOTE_AGE_DAYS = 7;

/** Level 1's two VaR instances (`riskAnalysisHelpers.ts`), restated: a spec cannot resolve `$lib`. */
const DAILY_VAR_INSTANCE = 'base-historical-historical_var';
const MONTHLY_VAR_INSTANCE = 'base-historical-historical_var-monthly';
/** The analytics level 1 renders (`RiskLevelsPanel.svelte`, `L1_CODES`). */
const L1_CODES: readonly string[] = ['historical_var', 'drawdown_summary', 'historical_kpi'];

/** The engine works on real series, on a machine that may be loaded: generous bounds, never a sleep. */
const ENGINE_TIMEOUT_MS = 90_000;
/** How long a figure may take to reach the screen once its answer is in. */
const FIGURE_TIMEOUT_MS = 15_000;

type Period = {start: string; end: string};
type SeededStock = {id: number; name: string; currency: string; buyClose: string};
type Holdings = {brokerId: number; stocks: SeededStock[]; period: Period};
type Owned = {user: DisposableUser | null; brokerIds: number[]};
type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type CommitBody = {committed: boolean; issues?: unknown[]};

type RiskAnalyticAsk = {instance_id: string; analytic_code: string; parameters?: Record<string, unknown> | null};
type RiskQueryBody = {
    scope: {kind: string; broker_ids?: number[] | null};
    date_range: {start: string; end?: string | null};
    target_currency: string;
    mode: string;
    analytics: RiskAnalyticAsk[];
};
type RiskQueryAnswer = ReturnType<typeof schemas.RiskQueryResponse.parse>;
type RiskResult = NonNullable<RiskQueryAnswer['items']>[number];
type RiskExchange = {path: string; request: Request};
/** The question whose answer is on screen, that answer parsed by the generated schema, and how many such questions the page asked. */
type ShownAnswer = {body: RiskQueryBody; answer: RiskQueryAnswer; asked: number};
/** A percentage as the screen prints it, in any of the four languages. */
type Figure = {negative: boolean; magnitude: number; decimals: number; bound: '<' | '>' | null};

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

// ---------------------------------------------------------------------------
// Figures: sign and digits, at the precision printed
// ---------------------------------------------------------------------------

/**
 * The first percentage of a text: an optional «<»/«>» bound (`shareFormat.ts`), an optional sign (U+2212, the hyphen
 * `Intl` writes, or «+»), digits with either decimal separator, then «%» after an optional (no-break) space. The
 * sentences that carry a figure — the histogram's cut, the replay's total — hold no other percentage in any language.
 */
const PERCENT = /([<>])?\s*([+\-\u2212])?\s*(\d+)(?:[.,](\d+))?\s*%/;

function readFigure(text: string): Figure | null {
    const match = PERCENT.exec(text);
    if (!match) return null;
    const [, bound, sign, integer, fraction = ''] = match;
    return {
        bound: bound === '<' || bound === '>' ? bound : null,
        negative: sign === '-' || sign === '\u2212' || bound === '>',
        magnitude: Number(`${integer}.${fraction || '0'}`),
        decimals: fraction.length,
    };
}

/**
 * Why `text` does not print `expected` (a signed fraction, as the engine answers it), or null when it does: the digits
 * must equal the engine's figure rounded to the decimals on screen — within half a unit of the last one printed — and
 * the sign must be the engine's.
 */
function figureMismatch(text: string, expected: number): string | null {
    const figure = readFigure(text);
    if (!figure) return `no percentage in «${text}»`;
    const percent = expected * 100;
    if (figure.bound) {
        // «< 0.01%»: a figure two decimals would still round to zero.
        if (Math.abs(percent) >= 0.005) return `«${text}» is a bound, the engine answered ${percent}%`;
        return percent !== 0 && figure.negative !== percent < 0 ? `«${text}» has the wrong sign for ${percent}%` : null;
    }
    if (figure.decimals < 1) return `«${text}» prints no decimal: too coarse to tell the engine's ${percent}% from a neighbour`;
    const gap = Math.abs(figure.magnitude - Math.abs(percent));
    if (gap > 0.5 * 10 ** -figure.decimals + 1e-9) return `«${text}» reads ${figure.negative ? '−' : ''}${figure.magnitude}%, the engine answered ${percent}% (off by ${gap})`;
    if (figure.magnitude > 0 && figure.negative !== percent < 0) return `«${text}» has the wrong sign for the engine's ${percent}%`;
    return null;
}

async function expectFigure(locator: Locator, expected: number, label: string): Promise<void> {
    await expect(locator, `${label}: on screen`).toBeVisible({timeout: FIGURE_TIMEOUT_MS});
    await expect(async () => {
        const text = (await locator.textContent({timeout: 5_000})) ?? '';
        expect(figureMismatch(text, expected), `${label}: the screen against the engine`).toBeNull();
    }).toPass({timeout: FIGURE_TIMEOUT_MS});
}

/** A count printed inside a sentence that holds no other digit, in any language. */
async function expectDigits(locator: Locator, expected: string, label: string): Promise<void> {
    await expect(locator, `${label}: on screen`).toBeVisible({timeout: FIGURE_TIMEOUT_MS});
    await expect(async () => {
        const text = (await locator.textContent({timeout: 5_000})) ?? '';
        expect(text.replace(/\D/g, ''), `${label}: the screen reads «${text}»`).toBe(expected);
    }).toPass({timeout: FIGURE_TIMEOUT_MS});
}

// ---------------------------------------------------------------------------
// The risk traffic of the page, and its contract
// ---------------------------------------------------------------------------

/** Every request the page sends to the risk engine from now on, in order. Armed before the navigation, read once the page has settled. */
function recordRiskTraffic(page: Page): RiskExchange[] {
    const traffic: RiskExchange[] = [];
    page.on('request', (request) => {
        const path = new URL(request.url()).pathname;
        if (path.startsWith(`${RISK_API}/`)) traffic.push({path, request});
    });
    return traffic;
}

function riskQueryBody(request: Request): RiskQueryBody | null {
    if (request.method() !== 'POST' || new URL(request.url()).pathname !== RISK_QUERY_PATH) return null;
    return request.postDataJSON() as RiskQueryBody;
}

/** The base wave level 1 reads: the historical one, which carries the daily VaR. */
function isHistoricalWave(body: RiskQueryBody): boolean {
    return body.mode === 'historical' && body.analytics.some((analytic) => analytic.instance_id === DAILY_VAR_INSTANCE);
}

function isReplay(body: RiskQueryBody): boolean {
    return body.analytics.some((analytic) => analytic.analytic_code === 'stress' && analytic.parameters?.method === 'historical_replay');
}

function breachOf(result: {success: boolean; error?: {issues: unknown}}): string | null {
    return result.success ? null : JSON.stringify(result.error?.issues ?? null);
}

/** Why an answer of the risk API breaks its generated schema, or null. A risk endpoint with no schema mapped here is a breach too: the claim is about every answer. */
function contractBreach(path: string, body: unknown): string | null {
    if (path === RISK_QUERY_PATH) return breachOf(schemas.RiskQueryResponse.safeParse(body));
    if (path === RISK_CATALOG_PATH) return breachOf(schemas.RiskCatalogResponse.safeParse(body));
    if (path === RISK_SCENARIO_CATALOG_PATH) return breachOf(schemas.RiskScenarioCatalogResponse.safeParse(body));
    if (path === RISK_ELIGIBILITY_PATH) return breachOf(schemas.RiskEligibilityResponse.safeParse(body));
    return `no generated schema is mapped to ${path} in this spec`;
}

async function expectRiskContract(traffic: RiskExchange[]): Promise<void> {
    expect(traffic.length, 'the page asked the risk engine nothing').toBeGreaterThan(0);
    const breaches: string[] = [];
    for (const {path, request} of traffic) {
        const response = await request.response();
        if (!response) {
            breaches.push(`${request.method()} ${path}: no answer`);
            continue;
        }
        if (!response.ok()) {
            breaches.push(`${request.method()} ${path}: HTTP ${response.status()} ${await response.text()}`);
            continue;
        }
        const breach = contractBreach(path, await response.json());
        if (breach) breaches.push(`${request.method()} ${path}: ${breach}`);
    }
    expect(breaches, `every risk answer the page received passes the generated schema (${traffic.length} answers)`).toEqual([]);
}

/**
 * The answer on screen for the questions `matches` selects: the answer to the last one the page asked — an earlier
 * one was superseded or discarded — parsed by the generated schema. Read once the panel has settled.
 */
async function shownAnswer(traffic: RiskExchange[], matches: (body: RiskQueryBody) => boolean, purpose: string): Promise<ShownAnswer> {
    const asked = traffic.flatMap(({request}) => {
        const body = riskQueryBody(request);
        return body && matches(body) ? [{request, body}] : [];
    });
    const last = asked.at(-1);
    if (!last) throw new Error(`${purpose}: the page never asked it`);
    const response = await last.request.response();
    if (!response) throw new Error(`${purpose}: the question got no answer`);
    const parsed = schemas.RiskQueryResponse.safeParse(await jsonFrom<unknown>(response, purpose));
    if (!parsed.success) throw new Error(`${purpose} breaks the generated schema: ${JSON.stringify(parsed.error.issues)}`);
    return {body: last.body, answer: parsed.data, asked: asked.length};
}

/** An analytic the engine answered with figures: `ok`, or `partial` — a complete answer with a caveat, which the levels render. */
function expectAnswered(result: RiskResult, purpose: string): void {
    expect(['ok', 'partial'], `${purpose}: ${result.instance_id} came back ${result.status} — ${JSON.stringify(result.error ?? null)}`).toContain(result.status);
}

function resultOf(answer: RiskQueryAnswer, instanceId: string, purpose: string): RiskResult {
    const items = answer.items ?? [];
    const result = items.find((item) => item.instance_id === instanceId);
    if (!result) throw new Error(`${purpose}: the answer carries no ${instanceId}; it carries ${JSON.stringify(items.map((item) => item.instance_id))}`);
    expectAnswered(result, purpose);
    return result;
}

// ---------------------------------------------------------------------------
// Owned rows: seeding and cleanup
// ---------------------------------------------------------------------------

/** `days` before today on the local calendar, moved back to the Friday when it falls on a weekend. */
function weekdayDaysAgo(days: number): string {
    const day = new Date();
    day.setDate(day.getDate() - days);
    while (day.getDay() === 0 || day.getDay() === 6) day.setDate(day.getDate() - 1);
    return localIso(day);
}

function daysBetween(fromIso: string, toIso: string): number {
    return Math.round((Date.parse(toIso) - Date.parse(fromIso)) / 86_400_000);
}

function amountOf(cents: number): string {
    return (cents / 100).toFixed(2);
}

/**
 * A seeded stock, found by its exact name, with its precondition read back rather than assumed: quoted on the day of
 * the purchase, on enough days of the period for the monthly VaR, and up to the period's end.
 */
async function seededStock(page: Page, name: string, period: Period): Promise<SeededStock> {
    const found = await jsonFrom<Array<{id: number; display_name: string; currency: string}>>(await page.request.get(`${API}/assets/query?search=${encodeURIComponent(name)}`), `look up the seeded «${name}»`);
    const matches = found.filter((asset) => asset.display_name === name);
    expect(matches, `exactly one seeded «${name}» is expected — check populate_mock_data.py`).toHaveLength(1);
    const asset = matches[0];

    const query = {asset_id: asset.id, date_range: {start: period.start, end: period.end}};
    schemas.FAPriceQueryItem.parse(query);
    const body = await jsonFrom<{items?: Array<{asset_id: number; prices?: Array<{date: string; close: string; backward_fill_info?: unknown}>}>}>(await page.request.post(`${API}/assets/prices/query`, {data: [query]}), `read the quotes of «${name}»`);
    // A point the query carried forward from an earlier day says so in `backward_fill_info`: only the others are quotes.
    const quoted = (body.items?.find((item) => item.asset_id === asset.id)?.prices ?? []).filter((point) => point.backward_fill_info == null);
    const onBuyDay = quoted.find((point) => point.date === period.start);
    if (!onBuyDay) throw new Error(`Precondition: «${name}» has no quote of its own on ${period.start}; populate_mock_data.py (populate_price_history) quotes it every weekday of the last year.`);
    expect(quoted.length, `precondition: «${name}» is quoted on at least ${MIN_QUOTED_DAYS} days of ${period.start} → ${period.end}`).toBeGreaterThanOrEqual(MIN_QUOTED_DAYS);
    const lastQuote = quoted[quoted.length - 1].date;
    expect(daysBetween(lastQuote, period.end), `precondition: «${name}» is quoted up to the period's end; its last quote is ${lastQuote}`).toBeLessThanOrEqual(MAX_QUOTE_AGE_DAYS);
    return {id: asset.id, name, currency: asset.currency, buyClose: onBuyDay.close};
}

/** Every id is recorded for cleanup before it is checked. */
async function createBroker(page: Page, owned: Owned, name: string): Promise<number> {
    const brokers = await jsonFrom<{results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>}>(await page.request.post(`${API}/brokers`, {data: [{name, opened_at: daysAgoIso(BUY_DAYS_AGO + 30)}]}), 'create an owned broker');
    const broker = brokers.results.find((item) => item.name === name);
    if (typeof broker?.broker_id === 'number') owned.brokerIds.push(broker.broker_id);
    if (!broker?.success || typeof broker.broker_id !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(brokers)}`);
    return broker.broker_id;
}

async function commitTransactions(page: Page, creates: unknown[], purpose: string): Promise<void> {
    const committed = await jsonFrom<CommitBody>(await page.request.post(`${API}/transactions/commit`, {data: {creates}}), purpose);
    expect(committed.committed, `${purpose}: rolled back — ${JSON.stringify(committed.issues ?? [])}`).toBe(true);
}

/**
 * A disposable account that owns the whole portfolio under test, its guides skipped so no overlay covers the panel:
 * one broker, and on one weekday 200 days ago a deposit and a purchase of each seeded stock. Each purchase costs its
 * quote of the day to the cent and the deposit is their sum, so the account holds no cash: the series under test is
 * the two stocks'.
 */
async function holdSeededStocks(page: Page, request: APIRequestContext, owned: Owned, tag: string): Promise<Holdings> {
    const user = await registerDisposableUser(request, tag);
    owned.user = user;
    await prepareOnboardingAccount(page, user, []);

    const period = {start: weekdayDaysAgo(BUY_DAYS_AGO), end: todayIso()};
    const stocks: SeededStock[] = [];
    for (const name of SEEDED_STOCKS) stocks.push(await seededStock(page, name, period));

    const suffix = uniqueSuffix();
    const brokerId = await createBroker(page, owned, `risk-real-broker-${suffix}`);
    const cents = stocks.map((stock) => Math.round(Number(stock.buyClose) * UNITS * 100));
    const funding = new Map<string, number>();
    stocks.forEach((stock, index) => funding.set(stock.currency, (funding.get(stock.currency) ?? 0) + cents[index]));
    await commitTransactions(
        page,
        [
            ...[...funding].map(([currency, total]) => ({broker_id: brokerId, type: 'DEPOSIT', date: period.start, cash: {code: currency, amount: amountOf(total)}, description: `risk-real funding ${suffix}`})),
            ...stocks.map((stock, index) => ({broker_id: brokerId, asset_id: stock.id, type: 'BUY', date: period.start, quantity: String(UNITS), cash: {code: stock.currency, amount: amountOf(-cents[index])}, description: `risk-real purchase ${suffix}`})),
        ],
        'commit the funding and the two purchases',
    );
    return {brokerId, stocks, period};
}

/**
 * Delete in dependency order, each step scoped to an id this test recorded: the page is unmounted first, so nothing
 * reads the rows while they go; the broker takes its transactions with it (`force`); the account goes last, through the
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
    await attempt('unmount the dashboard', async () => {
        await page.goto('about:blank');
    });
    for (const brokerId of owned.brokerIds) {
        await attempt(`broker ${brokerId}`, async () => {
            const result = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`), 'delete the owned broker and its transactions');
            expect(result.results.find((item) => item.id === brokerId)?.success).toBe(true);
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
        const owned: Owned = {user: null, brokerIds: []};
        try {
            await use(owned);
        } finally {
            await cleanupOwned(page, request, owned);
        }
    },
});

// ---------------------------------------------------------------------------
// The Risk tab
// ---------------------------------------------------------------------------

/**
 * A full load of the Dashboard on its Risk tab over `period`, its risk traffic recorded from before the navigation.
 *
 * Returns once the panel has nothing left to ask: the catalog is in, the first base waves are in (the panel's
 * `data-busy`), and nothing is being asked again — the page's Refresh publishes `data-busy="true"` while any base wave
 * of the panel is pending, a later one included — so the answers on screen are final. The first answer of the
 * historical wave is awaited as the page's own response: the real engine answered.
 */
async function openRiskTab(page: Page, period: Period): Promise<{panel: Locator; traffic: RiskExchange[]}> {
    const traffic = recordRiskTraffic(page);
    const historicalAnswer = armed(
        page.waitForResponse(
            (response) => {
                const body = riskQueryBody(response.request());
                return body !== null && isHistoricalWave(body);
            },
            {timeout: ENGINE_TIMEOUT_MS},
        ),
    );
    await page.goto(`/dashboard?${new URLSearchParams({tab: 'rischio', start: period.start, end: period.end}).toString()}`);
    await expect(page.getByTestId('dashboard-risk-tab')).toBeVisible({timeout: 30_000});
    const answered = await historicalAnswer;
    expect(answered.ok(), `the historical wave: HTTP ${answered.status()}`).toBe(true);

    const panel = page.getByTestId('risk-levels-panel');
    await expect(panel).toHaveAttribute('data-catalog', 'ready', {timeout: ENGINE_TIMEOUT_MS});
    await waitForSettled(panel, ENGINE_TIMEOUT_MS);
    await expect(page.getByTestId('sync-button'), 'nothing is still being asked: the answers on screen are final').toHaveAttribute('data-busy', 'false', {timeout: ENGINE_TIMEOUT_MS});
    // Behind the settled panel, so the absence is a statement about a finished load.
    await expect(panel.getByTestId('risk-load-error'), 'the base waves loaded').toHaveCount(0);
    return {panel, traffic};
}

/**
 * Open level 4 and its historical replay, whichever state each was in. Asked before clicking, never toggled blind: the
 * section starts closed today, and a reader's tools come back from per-user storage (D376/D377), so the replay is first
 * seen settled into exactly one of its two states — its box, or its «add» button — and only then acted on.
 */
async function openReplay(panel: Locator): Promise<Locator> {
    const level4 = panel.getByTestId('risk-level-4');
    await expect(level4).toBeVisible({timeout: FIGURE_TIMEOUT_MS});
    if ((await level4.getAttribute('data-open')) !== 'true') await panel.getByTestId('risk-level-4-toggle').click();
    await expect(level4).toHaveAttribute('data-open', 'true', {timeout: FIGURE_TIMEOUT_MS});
    await expect(level4.getByTestId('risk-l4')).toBeVisible({timeout: FIGURE_TIMEOUT_MS});

    const box = level4.getByTestId('risk-l4-replay');
    const add = level4.getByTestId('risk-l4-add-replay');
    await expect(box.or(add), 'level 4 shows the replay either open or offered, exactly once').toHaveCount(1, {timeout: FIGURE_TIMEOUT_MS});
    if ((await add.count()) > 0) await add.click();
    await expect(box).toBeVisible({timeout: FIGURE_TIMEOUT_MS});
    return box;
}

test.describe('Risk on real data — the engine’s answer, from the wire to the screen (gap 1)', () => {
    test('R1 — level 1 prints the engine’s daily VaR and its daily and monthly CVaR, with no error or empty state', async ({page, request, owned}) => {
        test.setTimeout(240_000);
        const holdings = await test.step('seed: a disposable account holds two seeded stocks bought 200 days ago', () => holdSeededStocks(page, request, owned, 'riskl1'));
        const {panel, traffic} = await test.step('open the Dashboard Risk tab over that period, nothing routed', () => openRiskTab(page, holdings.period));
        const shown = await shownAnswer(traffic, isHistoricalWave, 'the historical wave on screen');

        await test.step('the question on screen is this account’s portfolio over the period of the URL', async () => {
            expect(shown.body.scope, 'the Risk tab asks for the owned broker').toMatchObject({kind: 'portfolio', broker_ids: [holdings.brokerId]});
            expect(shown.body.date_range, 'over the Dashboard’s period').toMatchObject(holdings.period);
        });

        const {daily, monthly, cut} = await test.step('the engine answered every analytic level 1 renders', async () => {
            const level1Results = (shown.answer.items ?? []).filter((item) => L1_CODES.includes(item.analytic_code));
            expect(
                level1Results.map((item) => item.instance_id),
                'the answer carries both VaR horizons',
            ).toEqual(expect.arrayContaining([DAILY_VAR_INSTANCE, MONTHLY_VAR_INSTANCE]));
            for (const result of level1Results) expectAnswered(result, 'level 1');
            const daily = schemas.RiskVarCvarOutput.parse(resultOf(shown.answer, DAILY_VAR_INSTANCE, 'the daily VaR').output);
            const monthly = schemas.RiskVarCvarOutput.parse(resultOf(shown.answer, MONTHLY_VAR_INSTANCE, 'the monthly VaR').output);
            const cut = daily.var_bin_edge;
            if (cut == null) throw new Error(`The daily VaR carries no histogram cut: ${JSON.stringify(daily)}`);
            expect(cut, 'the histogram’s cut is the daily VaR, on the return axis').toBeCloseTo(-daily.value_at_risk, 12);
            test.info().annotations.push({
                type: 'engine',
                description: `statuses ${level1Results.map((item) => `${item.instance_id}=${item.status}`).join(', ')}; daily VaR ${daily.value_at_risk}, daily CVaR ${daily.conditional_value_at_risk}, monthly CVaR ${monthly.conditional_value_at_risk}; historical waves asked: ${shown.asked}`,
            });
            return {daily, monthly, cut};
        });

        const level1 = panel.getByTestId('risk-level-1');
        await test.step('level 1 prints the engine’s figures', async () => {
            await expect(level1.getByTestId('risk-l1-cards')).toBeVisible({timeout: FIGURE_TIMEOUT_MS});
            // The bad day and the bad month lead with the CVaR (`buildHurtRows`), written as a loss.
            await expectFigure(level1.getByTestId('risk-l1-card-day-value'), -daily.conditional_value_at_risk, 'bad day — the daily CVaR');
            await expectFigure(level1.getByTestId('risk-l1-card-month-value'), -monthly.conditional_value_at_risk, 'bad month — the monthly CVaR');
            // The VaR itself is the histogram's cut: the threshold, located on the return axis.
            await expectFigure(level1.getByTestId('risk-l1-histogram-cut'), cut, 'the histogram’s cut — the daily VaR');
            const bins = daily.return_bins ?? [];
            expect(bins.length, 'the daily VaR publishes its return distribution').toBeGreaterThan(0);
            await expect(level1.getByTestId('risk-l1-histogram-bars'), 'one bar per bin of the engine').toHaveAttribute('data-bin-count', String(bins.length));
            await expectDigits(level1.getByTestId('risk-l1-histogram-observations'), String(bins.reduce((total, bin) => total + bin.count, 0)), 'the histogram’s observations');
        });

        await test.step('level 1 shows no error and no empty state', async () => {
            // Behind the figures above, the presence barrier: each absence is a statement about a rendered level.
            await expect(level1.getByTestId('risk-level-1-alert'), 'no analytic of level 1 is missing or failed').toHaveCount(0);
            await expect(level1.getByTestId('risk-l1-empty')).toHaveCount(0);
            await expect(level1.getByTestId('risk-l1-histogram-empty')).toHaveCount(0);
        });

        await test.step('every risk answer the page received passes the generated Zod schemas', () => expectRiskContract(traffic));
    });

    test('R2 — level 4’s historical replay prints the engine’s composition return and each holding’s return and contribution', async ({page, request, owned}) => {
        test.setTimeout(240_000);
        const holdings = await test.step('seed: a disposable account holds two seeded stocks bought 200 days ago', () => holdSeededStocks(page, request, owned, 'riskl4'));
        const {panel, traffic} = await test.step('open the Dashboard Risk tab over that period, nothing routed', () => openRiskTab(page, holdings.period));
        const replay = await test.step('open level 4 and its historical replay', () => openReplay(panel));

        const shown = await test.step('run the replay over the panel’s period: the real engine answers', async () => {
            const run = replay.getByTestId('risk-replay-run');
            await expect(run).toBeEnabled({timeout: FIGURE_TIMEOUT_MS});
            const replayAnswer = armed(
                page.waitForResponse(
                    (response) => {
                        const body = riskQueryBody(response.request());
                        return body !== null && isReplay(body);
                    },
                    {timeout: ENGINE_TIMEOUT_MS},
                ),
            );
            await run.click();
            const answered = await replayAnswer;
            expect(answered.ok(), `the replay: HTTP ${answered.status()}`).toBe(true);
            // Run is disabled while its replay is asked: enabled again, the answer on screen is final.
            await expect(run, 'the replay is no longer running').toBeEnabled({timeout: ENGINE_TIMEOUT_MS});
            await expect(replay.getByTestId('risk-replay-total')).toBeVisible({timeout: FIGURE_TIMEOUT_MS});
            return shownAnswer(traffic, isReplay, 'the replay on screen');
        });

        const output = await test.step('the engine replayed the composition over that period', async () => {
            const asked = shown.body.analytics.find((analytic) => analytic.analytic_code === 'stress');
            expect(asked?.parameters?.replay_range, 'the replay asks over the panel’s period').toEqual(holdings.period);
            expect(shown.body.scope, 'for the owned broker').toMatchObject({kind: 'portfolio', broker_ids: [holdings.brokerId]});
            const items = shown.answer.items ?? [];
            const result = items.find((item) => item.analytic_code === 'stress');
            if (!result) throw new Error(`The replay's answer carries no stress result: ${JSON.stringify(items.map((item) => item.instance_id))}`);
            expectAnswered(result, 'the replay');
            const output = schemas.RiskStressOutput.parse(result.output);
            expect(output.method).toBe('historical_replay');
            test.info().annotations.push({
                type: 'engine',
                description: `replay ${result.status}: composition ${output.portfolio_return}; impacts ${JSON.stringify((output.impacts ?? []).map((impact) => [impact.asset_id, impact.shock_return, impact.contribution_return]))}; replays asked: ${shown.asked}`,
            });
            return output;
        });

        await test.step('level 4 prints the engine’s figures', async () => {
            const total = output.portfolio_return;
            if (typeof total !== 'number') throw new Error(`A replay of a portfolio carries its composition return; this one carries ${JSON.stringify(total)}`);
            await expectFigure(replay.getByTestId('risk-replay-total'), total, 'the composition’s return over the period');
            const tornado = replay.getByTestId('risk-replay-tornado');
            for (const stock of holdings.stocks) {
                const impact = (output.impacts ?? []).find((item) => item.asset_id === stock.id);
                if (!impact) throw new Error(`The replay left «${stock.name}» out: ${JSON.stringify(output.impacts ?? [])}`);
                const contribution = impact.contribution_return;
                if (typeof contribution !== 'number') throw new Error(`A holding of a portfolio carries its contribution; «${stock.name}» carries ${JSON.stringify(contribution)}`);
                const row = tornado.locator(`tbody tr[data-row-id="asset:${stock.id}"]`);
                await expectFigure(row.getByTestId('risk-replay-tornado-return'), impact.shock_return, `«${stock.name}» — its own return`);
                await expectFigure(row.getByTestId('risk-replay-tornado-contribution'), contribution, `«${stock.name}» — its contribution`);
            }
        });

        await test.step('level 4 shows no error', async () => {
            // Behind the figures above, the presence barrier.
            await expect(panel.getByTestId('risk-level-4-errors'), 'no step of level 4 failed').toHaveCount(0);
            await expect(replay.getByTestId('risk-replay-nothing')).toHaveCount(0);
        });

        await test.step('every risk answer the page received passes the generated Zod schemas', () => expectRiskContract(traffic));
    });
});
