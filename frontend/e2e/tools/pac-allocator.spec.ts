/**
 * PAC allocator — end-to-end coverage of the redesigned Tools/PAC surface.
 *
 * ## What is real here, and what is mocked, and why
 *
 * The deterministic calculation and stale-response scenarios cross
 * `/api/v1/tools/compute` and run the real `pac_allocator` plugin. Tests whose
 * subject is only editor serialization terminate the transport with a
 * deterministic 503 after capturing the request, so parallel workers cannot
 * contend for the platform's one-active-batch-per-principal reservation. The
 * component test
 * (`src/lib/features/tools/pac-allocator/PacAllocatorTool.test.ts`) already
 * proves the editor's behaviour against a mocked `runTool`, so repeating that
 * here would buy nothing but seconds. The three cases that cannot be produced by
 * a healthy server on demand — a transport rejection, a stopped wait, a
 * platform-level item failure — are produced by rewriting the *transport*, never
 * by faking the tool.
 *
 * The **allocation source** (`POST /api/v1/portfolio/report` with
 * `allocation_source`) is covered twice, on purpose:
 *
 *   1. against the real backend, where the spec asserts that the gallery and the
 *      imported rows match *the response the page actually received* — an
 *      assertion that stays true no matter what a neighbouring spec did to the
 *      shared database, and that would go red the day the UI dropped or
 *      duplicated a canonical asset; the populated admin fixture also supplies
 *      a genuinely unpriced holding, whose card must remain present;
 *   2. against a synthetic payload authored in this file, which is the only way
 *      to pin the states the seeded fixture does not contain: a canonical asset
 *      held in three OWNER custody contexts (one of them at a 0 % ownership
 *      share), a superseded source response arriving late, and a source outage.
 *      It repeats the unpriced state so the exact null quote can be asserted on
 *      the wire. Synthetic mocks written inside a spec are ours to shape; the
 *      STOP rule covers captured real-world snapshots, which this is not.
 *
 * ## Selectors
 *
 * `data-testid` only, plus attribute refinement on top of one. Nothing here
 * matches a CSS class or a translated string: the app ships in EN/IT/FR/ES and
 * the runner may run in any of them. Where a deterministic *decimal* is
 * asserted it is read out of a field value (`inputValue()`), a `data-*`
 * attribute, or the untranslated `"<amount> <currency>"` / `"<num> / <den>"`
 * strings that `PacResultPanel` composes with plain template literals — never
 * out of a sentence.
 *
 * ## Row identity
 *
 * `PacContextEditor` keys its fields by *position* (`pac-display-name-3`), and
 * position is mutable: a removal or a duplication renumbers everything after it.
 * So no assertion in this file trusts an index it did not just create. Rows are
 * located with `rowIndexWhere()`, which scans the rows and returns the index of
 * the one whose own field carries the value this test owns (the custody context
 * key of a source row, the display name of a manual row). Scanning to *find* an
 * identified row is the sanctioned shape; picking `.nth(0)` and hoping is not.
 *
 * ## Known observability gaps (asserted around, reported, not worked around)
 *
 * - `PacContextEditor` renders the broker name, the ownership share and the
 *   snapshot date as bare text with no `data-testid` and no `data-*` attribute,
 *   so they are not independently machine-readable. The spec scopes itself to a
 *   `pac-row` by the fixture's untranslated broker name and verifies those
 *   literal source values in the row as well as the custody context key (which
 *   embeds the broker id), instrument key, display name, exact custody quantity,
 *   whole quote, and full row payload on the wire.
 * - `pac-cash` is used twice: once by the grid `<section>` in
 *   `PacAllocatorTool.svelte` and once by the cash `<article>` in
 *   `PacMoneySection.svelte`. The id is ambiguous, so this file never selects
 *   it and addresses the money sections through `pac-cash-*` / `pac-contributions-*`.
 */
import {expect, test, type Locator, type Page, type Request} from '../fixtures/playwright';
import {login, navigateTo, openMobileMenu} from '../fixtures/auth-helpers';
import {eventSeq, waitForEvent} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
import {TEST_ADMIN, TEST_USER, TEST_USER_2} from '../fixtures/test-users';
import type {ToolComputeRequest, ToolComputeResponse, ToolInput, ToolOutput} from '../../src/lib/features/tools/contracts';

const TOOL_CODE = 'pac_allocator';
const TOOL_ROUTE = `/tools/${TOOL_CODE}`;
const HUB_ROUTE = '/tools';
const COMPUTE_PATH = '/api/v1/tools/compute';
const CATALOG_PATH = '/api/v1/tools/catalog';
const REPORT_PATH = '/api/v1/portfolio/report';
const SETTINGS_PATH = '/api/v1/settings/user';

/** A past date, used wherever the scenario needs a fixed quote/rate reference. */
const REFERENCE_DATE = '2026-09-08';
const PRIMARY_NAME = 'PAC E2E primary context';
const SECONDARY_NAME = 'PAC E2E secondary context';
const REVISED_NAME = 'PAC E2E primary context revised';
const SHARED_INSTRUMENT = 'pac-e2e-instrument';

type TestUser = typeof TEST_USER;
type PacInput = ToolInput<'pac_allocator', '1.0.0'>;
type PacInputRow = NonNullable<PacInput['rows']>[number];
type PacOutput = ToolOutput<'pac_allocator', '1.0.0'>;
type PacReady = Extract<PacOutput, {availability: 'ready'}>;

const TEST_ALICE: TestUser = {
    username: 'e2e_user_alice',
    email: 'alice@test.example.com',
    password: 'AlicePass123!',
};

const TEST_BOB: TestUser = {
    username: 'e2e_user_bob',
    email: 'bob@test.example.com',
    password: 'BobPass123!',
};

const TEST_CAROL: TestUser = {
    username: 'e2e_user_carol',
    email: 'carol@test.example.com',
    password: 'CarolPass123!',
};

// The compute platform allows one active batch per principal. Real compute
// scenarios use a distinct seeded principal per concurrent desktop/mobile case.
function principal(projectName: string, desktop: TestUser, mobile: TestUser): TestUser {
    return projectName === 'mobile' ? mobile : desktop;
}

test.setTimeout(90_000);

// =========================================================================
// Wire shapes of the allocation source. Declared here rather than imported:
// these objects are this spec's own synthetic fixture, and the parsed real
// response is read through the same shape so both paths assert identically.
// =========================================================================
interface SourceQuoteWire {
    raw_price: string | null;
    currency: string;
    quote_base_quantity: number;
    reference_date: string | null;
    source: string | null;
    days_before_requested: number | null;
}

interface SourceContextWire {
    context_key: string;
    broker_id: number;
    broker_name: string;
    ownership_share_percent: string;
    custody_quantity: string;
}

interface SourceAssetWire {
    asset_id: number;
    instrument_key: string;
    name: string;
    ticker: string | null;
    asset_type: string;
    icon_url: string | null;
    quote: SourceQuoteWire;
    contexts: SourceContextWire[];
}

interface AllocationSourceWire {
    generated_at: string;
    as_of_date: string;
    assets: SourceAssetWire[];
}

/**
 * The canonical fixture asset: one instrument, three OWNER custody contexts,
 * one of which carries a 0 % ownership share — the seeded database has no
 * OWNER-at-0 % row, and "0 % of it is mine" must still import the full custody
 * quantity, because `custody_quantity` is deliberately not share-scaled.
 */
function multiContextAsset(referenceDate: string): SourceAssetWire {
    return {
        asset_id: 900_001,
        instrument_key: 'asset:900001',
        name: 'PAC fixture multi-custody ETF',
        ticker: 'PACMC',
        asset_type: 'ETF',
        icon_url: null,
        quote: {
            raw_price: '123.450000000001',
            currency: 'USD',
            quote_base_quantity: 100,
            reference_date: referenceDate,
            source: 'pac-fixture-close',
            days_before_requested: 1,
        },
        contexts: [
            {context_key: 'asset:900001:broker:9001', broker_id: 9001, broker_name: 'PAC fixture broker A', ownership_share_percent: '25', custody_quantity: '12.345678901234'},
            {context_key: 'asset:900001:broker:9002', broker_id: 9002, broker_name: 'PAC fixture broker B', ownership_share_percent: '0', custody_quantity: '7.000000000001'},
            {context_key: 'asset:900001:broker:9003', broker_id: 9003, broker_name: 'PAC fixture broker C', ownership_share_percent: '100', custody_quantity: '0.000000000001'},
        ],
    };
}

/** An owned asset with no saved price. The gallery must keep it, not hide it. */
function missingPriceAsset(): SourceAssetWire {
    return {
        asset_id: 900_002,
        instrument_key: 'asset:900002',
        name: 'PAC fixture unpriced asset',
        ticker: null,
        asset_type: 'STOCK',
        icon_url: null,
        quote: {raw_price: null, currency: 'EUR', quote_base_quantity: 1, reference_date: null, source: null, days_before_requested: null},
        contexts: [{context_key: 'asset:900002:broker:9004', broker_id: 9004, broker_name: 'PAC fixture broker D', ownership_share_percent: '100', custody_quantity: '3'}],
    };
}

function sourcePayload(asOfDate: string, assets: SourceAssetWire[]): AllocationSourceWire {
    return {generated_at: `${asOfDate}T12:00:00+00:00`, as_of_date: asOfDate, assets};
}

// =========================================================================
// Route plumbing.
// =========================================================================

/** A promise the test decides when to settle. */
function gate(): {promise: Promise<void>; open: () => void} {
    let open!: () => void;
    const promise = new Promise<void>((resolve) => {
        open = resolve;
    });
    return {promise, open};
}

function only<T>(items: readonly T[], predicate: (item: T) => boolean, label: string): T {
    const matches = items.filter(predicate);
    expect(matches, label).toHaveLength(1);
    const [match] = matches;
    if (!match) throw new Error(`${label}: expected exactly one match`);
    return match;
}

function regexLiteral(value: string): string {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

async function expectSourceMetadata(row: Locator, context: SourceContextWire, sourceDate: string, quote: SourceQuoteWire): Promise<void> {
    await expect(row).toContainText(context.broker_name);
    await expect(row).toContainText(new RegExp(`(?:^|\\s)${regexLiteral(context.ownership_share_percent)}%(?:\\s|$)`));
    await expect(row).toContainText(sourceDate);
    if (quote.reference_date !== null) await expect(row).toContainText(quote.reference_date);
    if (quote.source !== null) await expect(row).toContainText(quote.source);
}

function isComputeRequest(request: Request): boolean {
    return request.method() === 'POST' && new URL(request.url()).pathname === COMPUTE_PATH;
}

/**
 * The as-of date a report request is asking the allocation source for, or null
 * when it is not a source request at all — the dashboard calls the very same
 * endpoint without `allocation_source`.
 */
function sourceDateOf(request: Request): string | null {
    if (request.method() !== 'POST') return null;
    if (new URL(request.url()).pathname !== REPORT_PATH) return null;
    const body = request.postDataJSON() as {allocation_source?: {as_of_date?: string} | null} | null;
    return body?.allocation_source?.as_of_date ?? null;
}

type SourceOutcome = AllocationSourceWire | 'reject';

/**
 * Answer the tool's allocation-source requests from this file instead of the
 * database. Only the *source* request is taken over: the dashboard asks the same
 * endpoint without `allocation_source`, and that request is passed through
 * untouched.
 *
 * The whole report body is synthesised (only `metadata` is required by the
 * response schema), so no server round trip is paid and the payload is exactly
 * what the resolver returns — including the ordering, which the gallery is
 * expected to preserve.
 */
async function routeAllocationSource(page: Page, resolve: (asOfDate: string) => Promise<SourceOutcome> | SourceOutcome): Promise<void> {
    await page.route(`**${REPORT_PATH}`, async (route) => {
        const asOfDate = sourceDateOf(route.request());
        if (asOfDate === null) return route.fallback();
        const outcome = await resolve(asOfDate);
        if (outcome === 'reject') {
            return route.fulfill({status: 503, contentType: 'application/json', body: JSON.stringify({detail: 'pac e2e: allocation source unavailable'})});
        }
        return route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                metadata: {target_currency: 'EUR', generated_at: `${asOfDate}T12:00:00+00:00`},
                allocation_source: outcome,
            }),
        });
    });
}

/** Capture-only scenarios do not consume the shared Tool execution pool. */
async function rejectCompute(page: Page): Promise<void> {
    await page.route(`**${COMPUTE_PATH}`, async (route) => {
        await route.fulfill({status: 503, contentType: 'application/json', body: '{}'});
    });
}

// =========================================================================
// Navigation.
// =========================================================================

async function openToolsHub(page: Page, user: TestUser): Promise<Locator> {
    await login(page, user);
    // Requirement: reached through the sidebar, the way a user reaches it.
    await openMobileMenu(page);
    await page.getByTestId('nav-tools').click();
    await expect(page).toHaveURL(new RegExp(`${HUB_ROUTE}$`));

    const hub = page.getByTestId('tools-hub');
    // `data-busy` covers both waves: the catalogue fetch and the per-entry
    // interface preload. Only once it is false is the PAC renderer warm.
    await expect(hub).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
    return hub;
}

async function waitForPacTool(page: Page): Promise<Locator> {
    const host = page.getByTestId('tool-host');
    await expect(host).toHaveAttribute('data-state', 'ready', {timeout: 30_000});
    await expect(host).toHaveAttribute('data-busy', 'false');
    const tool = page.getByTestId('pac-allocator-tool');
    await expect(tool).toBeVisible();
    await expect(tool).toHaveAttribute('data-busy', 'false');
    return tool;
}

/** Direct URL: a cold document legitimately shows a loading state, so nothing here forbids one. */
async function openPacDirect(page: Page, user: TestUser): Promise<Locator> {
    await login(page, user);
    await navigateTo(page, TOOL_ROUTE);
    return waitForPacTool(page);
}

// =========================================================================
// Field helpers.
// =========================================================================

function field(page: Page, prefix: string, index: number): Locator {
    return page.getByTestId(`${prefix}-${index}`);
}

async function browserDate(page: Page, dayOffset = 0): Promise<string> {
    return page.evaluate((offset: number) => {
        const date = new Date();
        date.setDate(date.getDate() + offset);
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    }, dayOffset);
}

/** Type an ISO date and commit it. */
async function setDate(page: Page, testid: string, iso: string): Promise<void> {
    const input = page.getByTestId(testid);
    const root = page.getByTestId(`${testid}-root`);
    await expect(input).toBeVisible();
    // The click is load-bearing, not defensive. `SingleDatePicker` treats Enter
    // as "commit and close" only when its calendar is open, and as "open the
    // calendar" when it is not — and the calendar opens on *focus*. A second
    // `fill()` on a field that is already focused therefore fires no focus
    // event, and the Enter that follows would open the picker instead of
    // committing the date, leaving the draft on the old value while the input
    // shows the new one. Clicking first makes the state the same every time.
    await input.click();
    await expect(root).toHaveAttribute('data-open', 'true');
    await input.fill(iso);
    await input.press('Enter');
    await expect(input).toHaveValue(iso);
    await expect(root).toHaveAttribute('data-open', 'false');
    // `data-invalid` is armed by Enter: a date the picker refused would leave
    // the typed text on screen and this flag true, which `toHaveValue` alone
    // cannot tell apart from a committed value.
    await expect(root).toHaveAttribute('data-invalid', 'false');
}

/**
 * Pick a currency in a `CurrencySearchSelect`.
 *
 * The option list is shared by every SearchSelect in the app
 * (`search-select-option-*`), so the previous list must be gone before the next
 * one opens — otherwise the click can land in the wrong dropdown.
 */
async function selectCurrency(page: Page, testId: string, code: string): Promise<void> {
    await optionsClosed(page);
    const trigger = page.getByTestId(`${testId}-trigger`);
    await expect(trigger).toBeVisible();
    await trigger.click();
    const search = page.getByTestId(`${testId}-search`);
    await expect(search).toBeVisible();
    await search.fill(code);
    const option = page.getByTestId(`search-select-option-${code}`);
    await expect(option).toBeVisible();
    await option.click();
    await optionsClosed(page);
    await expect(trigger).toContainText(code);
}

/**
 * Pick a `SimpleSelect` option *by its value*.
 *
 * Driven from the keyboard, and not because clicking is hard: the option list is
 * `position: fixed`, recomputed from the trigger on every scroll event, so a
 * pointer click makes the harness scroll to reach it and the reposition then
 * moves it again. On the 1280×720 desktop project that chase never converged —
 * the purchase-grid list of a row near the bottom of the page reported
 * "element is outside of the viewport" through 175 click retries, while the
 * same selection on the taller mobile viewport succeeded. So the list geometry
 * is *asserted* here (a list a user cannot see at all is a defect, and this
 * says so with the numbers in the message) and the selection itself goes
 * through `Home` + `ArrowDown`, which is the component's own keyboard model:
 * `aria-activedescendant` names the highlighted option by value, so nothing in
 * this helper depends on where an option sits in the list either.
 */
async function selectSimpleOption(page: Page, testId: string, value: string): Promise<void> {
    const trigger = page.getByTestId(`${testId}-button`);
    await expect(trigger).toBeVisible();
    await trigger.click();
    await expect(trigger).toHaveAttribute('aria-expanded', 'true');

    const dropdown = page.getByTestId(`${testId}-dropdown`);
    await expect(dropdown).toBeVisible();
    const box = await dropdown.boundingBox();
    const viewport = page.viewportSize();
    expect(box, `${testId}: the open option list has no box`).not.toBeNull();
    expect(viewport, 'viewport size').not.toBeNull();
    if (!box || !viewport) throw new Error(`${testId}: option list geometry unavailable`);
    const onScreen = box.y + box.height > 0 && box.y < viewport.height && box.x + box.width > 0 && box.x < viewport.width;
    expect(onScreen, `${testId}: the open option list sits entirely outside the ${viewport.width}×${viewport.height} viewport (${JSON.stringify(box)}) — nobody can choose from it`).toBe(true);

    const wanted = `-option-${value === '' ? '__empty__' : encodeURIComponent(value)}`;
    await trigger.press('Home');
    await expect(trigger).toHaveAttribute('aria-activedescendant', /-option-/);
    const visited = new Set<string>();
    let active = await trigger.getAttribute('aria-activedescendant');
    while (active && !active.endsWith(wanted) && !visited.has(active)) {
        visited.add(active);
        await trigger.press('ArrowDown');
        await expect
            .poll(async () => trigger.getAttribute('aria-activedescendant'), {
                message: `${testId}: keyboard navigation did not leave option "${active}"`,
            })
            .not.toBe(active);
        active = await trigger.getAttribute('aria-activedescendant');
    }
    expect(active, `${testId}: option "${value}" was never highlighted`).toContain(wanted);
    await trigger.press('Enter');
    await expect(trigger).toHaveAttribute('aria-expanded', 'false');
}

/**
 * The index of the row whose own `prefix` field holds `expected`.
 *
 * Row indices are renumbered by every removal and every duplication, so an index
 * captured before such an action means nothing after it. This walks the rows and
 * identifies one by a value the test owns — the exhaustive-scan shape, not a
 * positional pick.
 */
async function rowIndexWhere(page: Page, prefix: string, expected: string, label: string): Promise<number> {
    let found = -1;
    await expect
        .poll(
            async () => {
                found = -1;
                const rows = page.getByTestId('pac-row');
                const total = await rows.count();
                for (let position = 0; position < total; position += 1) {
                    const index = await rows.nth(position).getAttribute('data-row-index');
                    if (index === null) continue;
                    const candidate = page.getByTestId(`${prefix}-${index}`);
                    if ((await candidate.count()) !== 1) continue;
                    if ((await candidate.inputValue()) === expected) {
                        found = Number(index);
                        return true;
                    }
                }
                return false;
            },
            {message: `${label}: no pac-row whose ${prefix} field holds "${expected}"`, timeout: 15_000},
        )
        .toBe(true);
    return found;
}

/** Every custody context key currently in the draft, in row order. */
async function custodyKeys(page: Page): Promise<string[]> {
    const rows = page.getByTestId('pac-row');
    const total = await rows.count();
    const keys: string[] = [];
    for (let position = 0; position < total; position += 1) {
        const index = await rows.nth(position).getAttribute('data-row-index');
        if (index === null) continue;
        keys.push(await page.getByTestId(`pac-custody-context-${index}`).inputValue());
    }
    return keys;
}

/** Add one manual row to a draft this test controls, and return its index. */
async function addManualRow(page: Page): Promise<number> {
    const rows = page.getByTestId('pac-row');
    const before = await rows.count();
    await page.getByTestId('pac-add-manual-asset').click();
    await expect(rows).toHaveCount(before + 1);
    // The new row is appended, so its index is `before` by construction — this
    // is the one place an index is safe, because this test just created it.
    return before;
}

async function fillManualRow(page: Page, index: number, values: {instrument: string; name: string; quantity: string; price: string; currency: string; target: string; grid?: 'whole' | 'fractional'; step?: string; quoteDate?: string}): Promise<void> {
    await field(page, 'pac-instrument-id', index).fill(values.instrument);
    await field(page, 'pac-display-name', index).fill(values.name);
    await field(page, 'pac-initial-quantity', index).fill(values.quantity);
    await field(page, 'pac-raw-price', index).fill(values.price);
    await selectCurrency(page, `pac-asset-currency-${index}`, values.currency);
    await field(page, 'pac-target-weight', index).fill(values.target);
    if (values.grid) await selectSimpleOption(page, `pac-grid-mode-${index}`, values.grid);
    if (values.step !== undefined) await field(page, 'pac-step-quantity', index).fill(values.step);
    if (values.quoteDate) await setDate(page, `pac-price-date-${index}`, values.quoteDate);
}

/** Open the collapsed FX section and turn on manual valuation rates. */
async function enableManualRates(page: Page): Promise<void> {
    // The collapsed disclosure does not publish its own test id. Reach it by
    // keyboard from the next identified control rather than introducing a CSS,
    // role, translated-text or coordinate selector.
    const analyze = page.getByTestId('pac-analyze');
    await expect(analyze).toBeVisible();
    await analyze.focus();
    await page.keyboard.press('Shift+Tab');
    await page.keyboard.press('Enter');
    const toggle = page.getByTestId('pac-enable-rates');
    await expect(toggle).toBeVisible();
    await toggle.click();
    await expect(page.getByTestId('pac-add-rate')).toBeVisible();
}

// =========================================================================
// Compute helpers.
// =========================================================================

interface CapturedAnalyze {
    body: ToolComputeRequest;
    correlationId: string;
    parameters: PacInput;
}

/** Click Analyze, capture what left the browser, and wait for the tool to stop being busy. */
async function analyzeAndCapture(page: Page): Promise<CapturedAnalyze> {
    const tool = page.getByTestId('pac-allocator-tool');
    const pending = page.waitForRequest(isComputeRequest, {timeout: 30_000});
    await page.getByTestId('pac-analyze').click();
    const request = await pending;
    const body = request.postDataJSON() as ToolComputeRequest;
    const item = only(body.items, (candidate) => candidate.tool_code === TOOL_CODE, 'PAC compute item');
    expect(item.contract_version).toBe('1.0.0');
    expect(item.implementation_version).toBe('1.0.0');
    await expect(tool).toHaveAttribute('data-busy', 'false', {timeout: 40_000});
    return {body, correlationId: item.correlation_id, parameters: item.parameters as PacInput};
}

function available<T>(value: T): {availability: 'available'; reason_codes: never[]; value: T} {
    return {availability: 'available', reason_codes: [], value};
}

function money(amount: string) {
    return available({currency: 'EUR', amount});
}

function ratio(numerator: string, denominator: string, approximation: string, unit: 'percent' | 'percentage_points' | 'percentage_points_squared') {
    return available({
        numerator,
        denominator,
        unit,
        approximation,
        approximation_decimal_places: 28,
        approximation_exact: true,
    });
}

// =========================================================================
// The deterministic manual scenario analysed against the real Tool API.
//
// Two custody rows on the *same* instrument (10 units at 10 EUR, and 0 units),
// 50/50 targets, 10 USD of existing cash at an explicit 0.9 rate and 5 EUR of
// contributions. Every number the backend derives from that is exact and is
// asserted below, both on the wire and in the DOM.
// =========================================================================
async function fillDeterministicScenario(page: Page): Promise<void> {
    await selectCurrency(page, 'pac-report-currency', 'EUR');
    await setDate(page, 'pac-as-of-date', REFERENCE_DATE);

    const primary = await addManualRow(page);
    await fillManualRow(page, primary, {
        instrument: SHARED_INSTRUMENT,
        name: PRIMARY_NAME,
        quantity: '10',
        price: '10',
        currency: 'EUR',
        target: '50',
        grid: 'whole',
        step: '1',
        quoteDate: REFERENCE_DATE,
    });

    const secondary = await addManualRow(page);
    await fillManualRow(page, secondary, {
        instrument: SHARED_INSTRUMENT,
        name: SECONDARY_NAME,
        quantity: '0',
        price: '10',
        currency: 'EUR',
        target: '50',
        grid: 'whole',
        step: '1',
        quoteDate: REFERENCE_DATE,
    });

    await selectSimpleOption(page, 'pac-cash-mode', 'custom');
    await expect(page.getByTestId('pac-cash-row')).toHaveCount(1);
    await selectCurrency(page, 'pac-cash-currency-0', 'USD');
    await field(page, 'pac-cash-amount', 0).fill('10');

    await selectSimpleOption(page, 'pac-contributions-mode', 'custom');
    await expect(page.getByTestId('pac-contributions-row')).toHaveCount(1);
    await selectCurrency(page, 'pac-contributions-currency-0', 'EUR');
    await field(page, 'pac-contributions-amount', 0).fill('5');

    await enableManualRates(page);
    await page.getByTestId('pac-add-rate').click();
    await expect(page.getByTestId('pac-rate-row')).toHaveCount(1);
    await selectCurrency(page, 'pac-rate-currency-0', 'USD');
    await field(page, 'pac-rate-value', 0).fill('0.9');
    await setDate(page, 'pac-rate-date-0', REFERENCE_DATE);

    // Both viewport projects must be able to reach every control that the
    // scenario used; the component publishes no overflow state, so this is the
    // honest substitute for one.
    await expect(page.getByTestId('pac-analyze')).toBeVisible();
}

function assertScenarioRequest(parameters: PacInput): {primary: PacInputRow; secondary: PacInputRow} {
    expect(Object.keys(parameters).sort()).toEqual(['as_of_date', 'cash_balances', 'contributions', 'operation', 'report_currency', 'rows', 'valuation_rates']);
    expect(parameters.operation).toBe('analyze');
    expect(parameters.report_currency).toBe('EUR');
    expect(parameters.as_of_date).toBe(REFERENCE_DATE);
    expect(parameters.cash_balances).toEqual([{currency: 'USD', amount: '10'}]);
    expect(parameters.contributions).toEqual([{currency: 'EUR', amount: '5'}]);
    expect(parameters.valuation_rates).toEqual([{currency: 'USD', rate_to_report: '0.9', reference_date: REFERENCE_DATE}]);
    expect(parameters).not.toHaveProperty('solver');
    expect(parameters).not.toHaveProperty('orders');

    const rows = parameters.rows ?? [];
    expect(rows).toHaveLength(2);
    const primary = only(rows, (row) => row.name === PRIMARY_NAME, 'primary PAC input row');
    const secondary = only(rows, (row) => row.name === SECONDARY_NAME, 'secondary PAC input row');
    expect(primary.row_key).not.toBe(secondary.row_key);
    expect(primary.instrument_key).toBe(SHARED_INSTRUMENT);
    expect(secondary.instrument_key).toBe(SHARED_INSTRUMENT);
    expect(primary).toEqual({
        row_key: primary.row_key,
        instrument_key: SHARED_INSTRUMENT,
        name: PRIMARY_NAME,
        initial_quantity: '10',
        quote: {raw_price: '10', currency: 'EUR', quote_base_quantity: 1, reference_date: REFERENCE_DATE},
        target_percent: '50',
        buy_grid: {mode: 'whole', quantity_step: '1'},
    });
    expect(secondary).toEqual({
        row_key: secondary.row_key,
        instrument_key: SHARED_INSTRUMENT,
        name: SECONDARY_NAME,
        initial_quantity: '0',
        quote: {raw_price: '10', currency: 'EUR', quote_base_quantity: 1, reference_date: REFERENCE_DATE},
        target_percent: '50',
        buy_grid: {mode: 'whole', quantity_step: '1'},
    });
    return {primary, secondary};
}

function assertReadyOutput(output: PacOutput, primaryInput: PacInputRow, secondaryInput: PacInputRow): asserts output is PacReady {
    expect(output.availability).toBe('ready');
    if (output.availability !== 'ready') throw new Error(`Expected ready PAC output, got ${output.availability}`);
    expect({
        operation: output.operation,
        result_kind: output.result_kind,
        numeric_policy_id: output.numeric_policy_id,
        trade_feasibility: output.trade_feasibility,
        optimization: output.optimization,
        issues: output.issues,
    }).toEqual({
        operation: 'analyze',
        result_kind: 'initial_state_analysis',
        numeric_policy_id: 'pac-initial-state-v1',
        trade_feasibility: 'not_evaluated',
        optimization: 'not_run',
        issues: [],
    });

    expect(output.rows).toHaveLength(2);
    const primary = only(output.rows, (row) => row.name === PRIMARY_NAME, 'primary PAC output row');
    const secondary = only(output.rows, (row) => row.name === SECONDARY_NAME, 'secondary PAC output row');
    expect(primary).toEqual({
        row_index: 0,
        row_key: primaryInput.row_key,
        instrument_key: SHARED_INSTRUMENT,
        name: PRIMARY_NAME,
        quantity: available('10'),
        initial_value_native: available({currency: 'EUR', amount: '100'}),
        initial_value_reporting: money('100'),
        current_weight_percent: ratio('10000', '100', '100', 'percent'),
        target_percent: available('50'),
        deviation_pp: ratio('5000', '100', '50', 'percentage_points'),
    });
    expect(secondary).toEqual({
        row_index: 1,
        row_key: secondaryInput.row_key,
        instrument_key: SHARED_INSTRUMENT,
        name: SECONDARY_NAME,
        quantity: available('0'),
        initial_value_native: available({currency: 'EUR', amount: '0'}),
        initial_value_reporting: money('0'),
        current_weight_percent: ratio('0', '100', '0', 'percent'),
        target_percent: available('50'),
        deviation_pp: ratio('-5000', '100', '-50', 'percentage_points'),
    });

    expect(output.totals).toEqual({
        initial_invested_reporting: money('100'),
        existing_cash_reporting: money('9'),
        contributions_reporting: money('5'),
        cash_plus_contributions_reporting: money('14'),
        target_total_percent: available('100'),
        max_abs_gap_pp: ratio('5000', '100', '50', 'percentage_points'),
        squared_gap_pp2: ratio('50000000', '10000', '5000', 'percentage_points_squared'),
    });

    expect(output.cash_pools.availability).toBe('available');
    if (output.cash_pools.availability !== 'available') throw new Error('Expected available PAC cash pools');
    expect(output.cash_pools.value).toHaveLength(2);
    expect(only(output.cash_pools.value, (pool) => pool.currency === 'EUR', 'EUR PAC cash pool')).toEqual({
        currency: 'EUR',
        existing_amount: '0',
        contribution_amount: '5',
        combined_amount: '5',
        existing_reporting: money('0'),
        contribution_reporting: money('5'),
        combined_reporting: money('5'),
    });
    expect(only(output.cash_pools.value, (pool) => pool.currency === 'USD', 'USD PAC cash pool')).toEqual({
        currency: 'USD',
        existing_amount: '10',
        contribution_amount: '0',
        combined_amount: '10',
        existing_reporting: money('9'),
        contribution_reporting: money('0'),
        combined_reporting: money('9'),
    });

    expect(output.normalized.cash_balances).toEqual([
        {currency: 'EUR', amount: '0'},
        {currency: 'USD', amount: '10'},
    ]);
    expect(output.normalized.contributions).toEqual([
        {currency: 'EUR', amount: '5'},
        {currency: 'USD', amount: '0'},
    ]);
    expect(output.normalized.valuation_rates).toEqual([
        {currency: 'EUR', rate_to_report: '1', reference_date: null},
        {currency: 'USD', rate_to_report: '0.9', reference_date: REFERENCE_DATE},
    ]);
}

/**
 * The DOM half of the same result. `PacResultPanel` composes these strings with
 * plain template literals (`${amount} ${currency}`, `${numerator} / ${denominator}`),
 * so they are exact backend decimals, not translated copy.
 */
async function expectReadyDom(page: Page): Promise<void> {
    const result = page.getByTestId('pac-result');
    await expect(result).toBeVisible();
    await expect(result).toHaveAttribute('data-state', 'ready');
    await expect(result).toHaveAttribute('data-stale', 'false');
    await expect(page.getByTestId('pac-total-invested')).toHaveText('100 EUR');
    await expect(page.getByTestId('pac-total-existing-cash')).toHaveText('9 EUR');
    await expect(page.getByTestId('pac-total-contributions')).toHaveText('5 EUR');
    await expect(page.getByTestId('pac-total-combined-cash')).toHaveText('14 EUR');
    await expect(page.getByTestId('pac-max-gap')).toHaveText('5000 / 100');
    await expect(page.getByTestId('pac-squared-gap')).toHaveText('50000000 / 10000');

    const primary = page.getByTestId('pac-result-row').filter({hasText: PRIMARY_NAME});
    const secondary = page.getByTestId('pac-result-row').filter({hasText: SECONDARY_NAME});
    await expect(primary).toHaveCount(1);
    await expect(secondary).toHaveCount(1);
    await expect(primary).toContainText('100 EUR');
    await expect(primary).toContainText('10000 / 100');
    await expect(secondary).toContainText('-5000 / 100');
    await expect(page.getByTestId('pac-normalized-details')).toBeVisible();
}

// =========================================================================

test.describe('PAC allocator', () => {
    test('reaches the tool from the sidebar, offers the whole card as the only open action, and keeps documentation independent', async ({page}, testInfo) => {
        const user = principal(testInfo.project.name, TEST_USER, TEST_USER_2);
        const hub = await openToolsHub(page, user);

        const catalogResponse = await page.request.get(CATALOG_PATH);
        expect(catalogResponse.status(), 'tool catalogue').toBe(200);
        const catalog = (await catalogResponse.json()) as {items: {tool_code: string; contract_version: string; documentation: {path: string}}[]};
        const descriptor = only(catalog.items, (item) => item.tool_code === TOOL_CODE, 'PAC catalogue entry');

        const card = page.getByTestId(`tool-card-${TOOL_CODE}`);
        await expect(card).toBeVisible();
        await expect(card).toHaveAttribute('data-interface-state', 'ready');

        // The open affordance is the card itself: one overlay anchor, covering
        // the card, carrying no visible label of its own.
        const open = card.getByTestId('tool-open');
        await expect(open).toHaveCount(1);
        await expect(open).toBeVisible();
        await expect(open).toBeEmpty();
        await expect(open).toHaveAttribute('href', TOOL_ROUTE);
        const cardBox = await card.boundingBox();
        const openBox = await open.boundingBox();
        expect(cardBox, 'tool card box').not.toBeNull();
        expect(openBox, 'open overlay box').not.toBeNull();
        if (!cardBox || !openBox) throw new Error('tool card geometry unavailable');
        // The overlay is inset into the card's padding box, so it is exactly the
        // card's 1px border narrower and shorter on each side. Anything beyond
        // that would be a part of the card that does not open the tool.
        expect(Math.abs(openBox.x - cardBox.x)).toBeLessThanOrEqual(2);
        expect(Math.abs(openBox.y - cardBox.y)).toBeLessThanOrEqual(2);
        expect(Math.abs(openBox.width - cardBox.width)).toBeLessThanOrEqual(4);
        expect(Math.abs(openBox.height - cardBox.height)).toBeLessThanOrEqual(4);

        // The version is stated once. `1.0.0` is a wire value, not a sentence:
        // counting it in the card's own text is locale-independent.
        await expect
            .poll(async () => (await card.innerText()).split(descriptor.contract_version).length - 1, {
                message: `the PAC card should state version ${descriptor.contract_version} exactly once`,
            })
            .toBe(1);

        // Refresh belongs to the hub header, not to the cards, and it really
        // re-reads the catalogue.
        const refresh = hub.getByTestId('tools-hub-refresh');
        await expect(refresh).toHaveCount(1);
        await expect(refresh).toBeVisible();
        await expect(card.getByTestId('tools-hub-refresh')).toHaveCount(0);
        // Icon-only on a narrow viewport: the label span collapses, the
        // accessible name does not. Same contract on both projects.
        expect(await refresh.getAttribute('aria-label'), 'hub refresh accessible name').toBeTruthy();
        const catalogReload = page.waitForRequest((request) => request.method() === 'GET' && new URL(request.url()).pathname === CATALOG_PATH, {timeout: 20_000});
        await refresh.click();
        await catalogReload;
        await expect(hub).toHaveAttribute('data-busy', 'false', {timeout: 30_000});

        // Documentation is its own action: it opens the docs and leaves the hub
        // where it was, instead of falling through to the card's open overlay.
        const docs = card.getByTestId(`tool-docs-${TOOL_CODE}`);
        await expect(docs).toBeVisible();
        expect(await docs.getAttribute('aria-label'), 'documentation accessible name').toBeTruthy();
        const popupPromise = page.context().waitForEvent('page', {timeout: 15_000});
        await docs.click();
        const popup = await popupPromise;
        await popup.waitForLoadState('domcontentloaded').catch(() => undefined);
        expect(new URL(popup.url()).pathname).toContain(descriptor.documentation.path.replace(/\/$/, ''));
        await popup.close();
        await expect(page).toHaveURL(new RegExp(`${HUB_ROUTE}$`));
        await expect(page.getByTestId('tool-host')).toHaveCount(0);
    });

    test('mounts the PAC renderer on a warm navigation without showing a tool loading state', async ({page}, testInfo) => {
        const user = principal(testInfo.project.name, TEST_USER, TEST_ALICE);
        await openToolsHub(page, user);

        // Sample at frame boundaries rather than through a MutationObserver.
        // The host's first render does contain the catalogue-loading branch,
        // but the mount effect replaces it inside the same flush — so it is
        // never part of a painted frame, and "the user saw a spinner" is
        // exactly the question worth asking. The frame counter is here so a
        // stalled rAF cannot pass this test by never looking.
        await page.evaluate(() => {
            const probe = {seen: false, frames: 0, running: true};
            (window as unknown as {__pacProbe?: typeof probe}).__pacProbe = probe;
            const sample = () => {
                if (!probe.running) return;
                probe.frames += 1;
                const nodes = document.querySelectorAll('[data-testid="tool-host-catalog-loading"],[data-testid="tool-host-component-loading"]');
                for (const node of Array.from(nodes)) {
                    if ((node as HTMLElement).getClientRects().length > 0) probe.seen = true;
                }
                requestAnimationFrame(sample);
            };
            requestAnimationFrame(sample);
        });

        // Clicking the middle of the card — not a dedicated button — is what
        // "the whole card is the target" means in practice.
        await page.getByTestId(`tool-card-${TOOL_CODE}`).click();
        await expect(page).toHaveURL(new RegExp(`${TOOL_ROUTE}$`));
        await waitForPacTool(page);

        const probe = await page.evaluate(() => {
            const state = (window as unknown as {__pacProbe?: {seen: boolean; frames: number; running: boolean}}).__pacProbe;
            if (state) state.running = false;
            return state ?? {seen: true, frames: 0, running: false};
        });
        expect(probe.frames, 'the frame sampler never ran, so it proves nothing').toBeGreaterThan(1);
        expect(probe.seen, 'a warm navigation painted a tool loading state').toBe(false);

        // A direct URL is a cold document: a loading state there is truthful,
        // so it is not forbidden — only the outcome is asserted.
        await navigateTo(page, TOOL_ROUTE);
        await waitForPacTool(page);
    });

    test('opens on the local date, the account base currency and no rows, and accepts a manual asset while the source is still loading', async ({page}, testInfo) => {
        const user = principal(testInfo.project.name, TEST_USER, TEST_ALICE);
        await login(page, user);

        const settingsResponse = await page.request.get(SETTINGS_PATH);
        expect(settingsResponse.status(), 'user settings').toBe(200);
        const settings = (await settingsResponse.json()) as {base_currency?: string | null};
        const baseCurrency = settings.base_currency || 'EUR';

        const held = gate();
        let releasedFor = '';
        await routeAllocationSource(page, async (asOfDate) => {
            await held.promise;
            releasedFor = asOfDate;
            return sourcePayload(asOfDate, [multiContextAsset(REFERENCE_DATE)]);
        });

        await navigateTo(page, TOOL_ROUTE);
        const tool = await waitForPacTool(page);

        // The source request is in flight: that is a state the gallery reports.
        await expect(page.getByTestId('pac-owned-assets-loading')).toBeVisible();

        const today = await browserDate(page);
        await expect(page.getByTestId('pac-as-of-date')).toHaveValue(today);
        await expect(page.getByTestId('pac-report-currency-trigger')).toContainText(baseCurrency);
        await expect(page.getByTestId('pac-no-rows')).toBeVisible();
        await expect(page.getByTestId('pac-row')).toHaveCount(0);

        // Custom controls, not native ones: a searchable currency select and a
        // typed/calendar date picker rather than <input type="date">.
        await expect(page.getByTestId('pac-as-of-date')).toHaveAttribute('type', 'text');
        await expect(page.getByTestId('pac-as-of-date-root')).toHaveCount(1);
        await expect(page.getByTestId('pac-report-currency-trigger')).toHaveCount(1);

        // Manual entry does not wait for the portfolio.
        const index = await addManualRow(page);
        await field(page, 'pac-display-name', index).fill('PAC manual while loading');
        await expect(page.getByTestId('pac-owned-assets-loading')).toBeVisible();
        for (const prefix of ['pac-initial-quantity', 'pac-raw-price', 'pac-target-weight', 'pac-step-quantity']) {
            await expect(field(page, prefix, index)).toHaveAttribute('type', 'text');
            await expect(field(page, prefix, index)).toHaveAttribute('inputmode', 'decimal');
        }
        await expect(page.getByTestId(`pac-asset-currency-${index}-trigger`)).toHaveCount(1);
        await expect(page.getByTestId(`pac-price-date-${index}`)).toHaveAttribute('type', 'text');
        await expect(page.getByTestId(`pac-price-basis-${index}-button`)).toHaveCount(1);
        await expect(page.getByTestId(`pac-grid-mode-${index}-button`)).toHaveCount(1);

        held.open();
        await expect(page.getByTestId('pac-owned-asset-900001')).toBeVisible({timeout: 20_000});
        await expect(page.getByTestId('pac-owned-assets-loading')).toHaveCount(0);
        expect(releasedFor).toBe(today);
        // The row the user typed while the portfolio was loading is still there.
        await expect(field(page, 'pac-display-name', index)).toHaveValue('PAC manual while loading');
        await expect(tool).toHaveAttribute('data-busy', 'false');
    });

    test('keeps manual entry available when the allocation source is empty and when it fails, and recovers on retry', async ({page}) => {
        // TEST_USER_2 holds no OWNER access in the seeded fixture, so its
        // allocation source is genuinely empty. Verified, not assumed.
        await login(page, TEST_USER_2);
        const today = await browserDate(page);
        const probe = await page.request.post(REPORT_PATH, {
            data: {include_summary: false, include_history: false, include_allocation_history: false, include_positions_contribution: false, include_breakdown: false, allocation_source: {as_of_date: today}},
        });
        expect(probe.status(), 'allocation source probe').toBe(200);
        const probeBody = (await probe.json()) as {allocation_source?: AllocationSourceWire | null};
        if ((probeBody.allocation_source?.assets ?? []).length !== 0) {
            throw new Error(`${TEST_USER_2.username} is expected to hold no OWNER broker access — see populate_broker_user_access() in backend/test_scripts/test_db/populate_mock_data.py`);
        }

        await navigateTo(page, TOOL_ROUTE);
        await waitForPacTool(page);
        await expect(page.getByTestId('pac-owned-assets-empty')).toBeVisible({timeout: 20_000});
        const emptyRow = await addManualRow(page);
        await field(page, 'pac-display-name', emptyRow).fill('PAC manual without portfolio');
        await expect(field(page, 'pac-display-name', emptyRow)).toHaveValue('PAC manual without portfolio');

        // Now the failing source. The editor must stay usable and must offer an
        // explicit retry — nothing here retries on its own.
        let sourceFails = true;
        await routeAllocationSource(page, (asOfDate) => (sourceFails ? 'reject' : sourcePayload(asOfDate, [missingPriceAsset()])));
        await navigateTo(page, TOOL_ROUTE);
        await waitForPacTool(page);
        await expect(page.getByTestId('pac-owned-assets-error')).toBeVisible({timeout: 20_000});

        const fallbackRow = await addManualRow(page);
        await field(page, 'pac-display-name', fallbackRow).fill('PAC manual fallback');
        await field(page, 'pac-initial-quantity', fallbackRow).fill('4.500000000001');
        await expect(field(page, 'pac-initial-quantity', fallbackRow)).toHaveValue('4.500000000001');

        sourceFails = false;
        await page.getByTestId('pac-owned-assets-retry').click();
        await expect(page.getByTestId('pac-owned-asset-900002')).toBeVisible({timeout: 20_000});
        await expect(page.getByTestId('pac-owned-assets-error')).toHaveCount(0);
        await expect(field(page, 'pac-display-name', fallbackRow)).toHaveValue('PAC manual fallback');
    });

    test('renders one card per canonical asset of the real allocation source and imports the contexts of an identified asset', async ({page}) => {
        const user = TEST_ADMIN;
        await login(page, user);

        const sourceResponse = page.waitForResponse((response) => sourceDateOf(response.request()) !== null, {timeout: 30_000});
        await navigateTo(page, TOOL_ROUTE);
        await waitForPacTool(page);
        const source = ((await (await sourceResponse).json()) as {allocation_source: AllocationSourceWire}).allocation_source;

        if (source.assets.length === 0) {
            throw new Error(`${user.username} is expected to own broker positions — see populate_mock_data.py (populate_broker_user_access / populate_transactions)`);
        }

        // Canonical grouping: one card per asset id, and no card for anything
        // the backend did not send. Both counts come from the response this
        // page received, never from a hardcoded fixture size.
        await expect(page.getByTestId('pac-owned-assets-loading')).toHaveCount(0, {timeout: 20_000});
        for (const asset of source.assets) {
            await expect(page.getByTestId(`pac-owned-asset-${asset.asset_id}`), `card for asset ${asset.asset_id}`).toHaveCount(1);
        }
        const unpricedAssets = source.assets.filter((asset) => asset.quote.raw_price === null);
        if (unpricedAssets.length === 0) {
            throw new Error(`${user.username} is expected to own the seeded unpriced holding — see populate_assets / populate_transactions in backend/test_scripts/test_db/populate_mock_data.py`);
        }
        for (const asset of unpricedAssets) {
            await expect(page.getByTestId(`pac-owned-asset-${asset.asset_id}`), `unpriced card for asset ${asset.asset_id}`).toBeVisible();
        }
        // `pac-owned-assets-*` (empty/loading/error/refresh/retry/search) never
        // matches this prefix: those ids carry an `s` where this one has a dash.
        await expect(page.getByTestId(/^pac-owned-asset-\d+$/)).toHaveCount(source.assets.length);

        // The asset under test is identified by id, chosen deterministically as
        // the one with the most custody contexts (ties resolved by id) — never
        // "the first card".
        const target = source.assets.reduce((selected, candidate) => (candidate.contexts.length > selected.contexts.length || (candidate.contexts.length === selected.contexts.length && candidate.asset_id < selected.asset_id) ? candidate : selected));
        const card = page.getByTestId(`pac-owned-asset-${target.asset_id}`);
        await expect(card).toHaveAttribute('aria-pressed', 'false');
        await card.click();

        // Atomic: every OWNER custody context of that one canonical asset, and
        // nothing else, in a draft that started empty.
        await expect(page.getByTestId('pac-row')).toHaveCount(target.contexts.length);
        await expect(card).toHaveAttribute('aria-pressed', 'true');

        for (const context of target.contexts) {
            const index = await rowIndexWhere(page, 'pac-custody-context', context.context_key, `context ${context.context_key}`);
            const sourceRow = page.getByTestId('pac-row').filter({hasText: context.broker_name});
            await expect(sourceRow, `source metadata row for ${context.context_key}`).toHaveCount(1);
            await expectSourceMetadata(sourceRow, context, source.as_of_date, target.quote);
            await expect(field(page, 'pac-initial-quantity', index)).toHaveValue(context.custody_quantity);
            await expect(field(page, 'pac-instrument-id', index)).toHaveValue(target.instrument_key);
            await expect(field(page, 'pac-display-name', index)).toHaveValue(target.name);
            await expect(field(page, 'pac-raw-price', index)).toHaveValue(target.quote.raw_price ?? '');
            await expect(field(page, 'pac-price-date', index)).toHaveValue(target.quote.reference_date ?? '');
            await expect(page.getByTestId(`pac-asset-currency-${index}-trigger`)).toContainText(target.quote.currency);
            // The copy carries facts, never a decision: target and grid stay blank.
            await expect(field(page, 'pac-target-weight', index)).toHaveValue('');
            await expect(field(page, 'pac-step-quantity', index)).toHaveValue('');
        }

        // Unmodified copies are dropped without a question.
        await card.click();
        await expect(page.getByTestId('pac-row')).toHaveCount(0);
        await expect(page.getByTestId('pac-confirm-deselect')).toHaveCount(0);
        await expect(card).toHaveAttribute('aria-pressed', 'false');
    });

    test('imports every OWNER context of a canonical asset including a 0% share, keeps unpriced assets, and copies exact decimals', async ({page}, testInfo) => {
        const user = principal(testInfo.project.name, TEST_USER, TEST_ALICE);
        await login(page, user);
        const asset = multiContextAsset(REFERENCE_DATE);
        const unpriced = missingPriceAsset();
        await routeAllocationSource(page, (asOfDate) => sourcePayload(asOfDate, [asset, unpriced]));
        await rejectCompute(page);

        await navigateTo(page, TOOL_ROUTE);
        await waitForPacTool(page);

        const card = page.getByTestId(`pac-owned-asset-${asset.asset_id}`);
        const unpricedCard = page.getByTestId(`pac-owned-asset-${unpriced.asset_id}`);
        await expect(card).toHaveCount(1);
        // An asset with no saved price keeps its card: the user decides what to
        // do about the missing quote, the gallery does not decide for them.
        await expect(unpricedCard).toHaveCount(1);
        await expect(unpricedCard).toBeVisible();

        await card.click();
        await expect(page.getByTestId('pac-row')).toHaveCount(asset.contexts.length);
        expect(new Set(await custodyKeys(page))).toEqual(new Set(asset.contexts.map((context) => context.context_key)));

        for (const context of asset.contexts) {
            const index = await rowIndexWhere(page, 'pac-custody-context', context.context_key, `fixture context ${context.context_key}`);
            const sourceRow = page.getByTestId('pac-row').filter({hasText: context.broker_name});
            await expect(sourceRow, `source metadata row for ${context.context_key}`).toHaveCount(1);
            await expectSourceMetadata(sourceRow, context, REFERENCE_DATE, asset.quote);
            await expect(field(page, 'pac-initial-quantity', index)).toHaveValue(context.custody_quantity);
            await expect(field(page, 'pac-instrument-id', index)).toHaveValue(asset.instrument_key);
            await expect(field(page, 'pac-display-name', index)).toHaveValue(asset.name);
            await expect(field(page, 'pac-raw-price', index)).toHaveValue('123.450000000001');
            await expect(field(page, 'pac-price-date', index)).toHaveValue(REFERENCE_DATE);
            await expect(field(page, 'pac-target-weight', index)).toHaveValue('');
            await expect(field(page, 'pac-step-quantity', index)).toHaveValue('');
        }

        await unpricedCard.click();
        await expect(page.getByTestId('pac-row')).toHaveCount(asset.contexts.length + 1);
        const unpricedContext = only(unpriced.contexts, (context) => context.broker_id === 9004, 'unpriced fixture context');
        const unpricedIndex = await rowIndexWhere(page, 'pac-custody-context', unpricedContext.context_key, 'unpriced context');
        await expect(field(page, 'pac-raw-price', unpricedIndex)).toHaveValue('');
        await expect(field(page, 'pac-price-date', unpricedIndex)).toHaveValue('');
        await expect(field(page, 'pac-initial-quantity', unpricedIndex)).toHaveValue('3');

        // What actually leaves the browser: the same decimals, digit for digit,
        // with the quote basis the source declared and no invented target/grid.
        const {parameters} = await analyzeAndCapture(page);
        expect(parameters.rows).toHaveLength(asset.contexts.length + 1);
        for (const context of asset.contexts) {
            const row = only(parameters.rows ?? [], (candidate) => candidate.row_key === context.context_key, `wire row ${context.context_key}`);
            expect(row).toEqual({
                row_key: context.context_key,
                instrument_key: asset.instrument_key,
                name: asset.name,
                initial_quantity: context.custody_quantity,
                quote: {raw_price: '123.450000000001', currency: 'USD', quote_base_quantity: 100, reference_date: REFERENCE_DATE},
                target_percent: '',
                buy_grid: {mode: null, quantity_step: ''},
            });
        }
        const unpricedRow = only(parameters.rows ?? [], (candidate) => candidate.row_key === unpricedContext.context_key, 'wire row for the unpriced asset');
        expect(unpricedRow.initial_quantity).toBe('3');
        expect(unpricedRow.quote).toEqual({raw_price: null, currency: 'EUR', quote_base_quantity: 1, reference_date: null});

        await expect(page.getByTestId('pac-client-error')).toHaveAttribute('data-error-code', 'request_rejected');
    });

    test('duplicates the whole payload except the custody key, and confirms before dropping an edited copy', async ({page}, testInfo) => {
        const user = principal(testInfo.project.name, TEST_USER, TEST_ALICE);
        await login(page, user);
        const base = multiContextAsset(REFERENCE_DATE);
        const sourceContext = only(base.contexts, (context) => context.broker_id === 9001, 'primary fixture context');
        const asset: SourceAssetWire = {...base, contexts: [sourceContext]};
        await routeAllocationSource(page, (asOfDate) => sourcePayload(asOfDate, [asset]));
        await rejectCompute(page);

        await navigateTo(page, TOOL_ROUTE);
        await waitForPacTool(page);

        const card = page.getByTestId(`pac-owned-asset-${asset.asset_id}`);
        await card.click();
        const contextKey = sourceContext.context_key;
        const original = await rowIndexWhere(page, 'pac-custody-context', contextKey, 'imported context');

        await field(page, 'pac-target-weight', original).fill('42.5');
        await selectSimpleOption(page, `pac-grid-mode-${original}`, 'whole');
        await field(page, 'pac-step-quantity', original).fill('2.500000000001');

        await page.getByTestId(`pac-duplicate-asset-${original}`).click();
        await expect(page.getByTestId('pac-row')).toHaveCount(2);

        // The duplicate is found by the one field that must differ, not by index.
        const keys = await custodyKeys(page);
        const duplicateKey = only(keys, (key) => key !== contextKey, 'duplicated custody key');
        expect(duplicateKey).not.toBe(contextKey);
        const copy = await rowIndexWhere(page, 'pac-custody-context', duplicateKey, 'duplicated row');
        const source = await rowIndexWhere(page, 'pac-custody-context', contextKey, 'source row after duplication');

        for (const prefix of ['pac-instrument-id', 'pac-display-name', 'pac-initial-quantity', 'pac-raw-price', 'pac-price-date', 'pac-target-weight', 'pac-step-quantity']) {
            expect(await field(page, prefix, copy).inputValue(), `${prefix} of the duplicate`).toBe(await field(page, prefix, source).inputValue());
        }

        // The wire is the complete statement: everything but the row key.
        const {parameters} = await analyzeAndCapture(page);
        const rows = parameters.rows ?? [];
        expect(rows).toHaveLength(2);
        const sourceRow = only(rows, (row) => row.row_key === contextKey, 'source row on the wire');
        const copyRow = only(rows, (row) => row.row_key === duplicateKey, 'duplicated row on the wire');
        const {row_key: sourceKey, ...sourcePayloadRest} = sourceRow;
        const {row_key: copiedKey, ...copyPayloadRest} = copyRow;
        expect(copiedKey).not.toBe(sourceKey);
        expect(copyPayloadRest).toEqual(sourcePayloadRest);
        expect(sourcePayloadRest).toMatchObject({
            initial_quantity: sourceContext.custody_quantity,
            target_percent: '42.5',
            buy_grid: {mode: 'whole', quantity_step: '2.500000000001'},
        });

        // Now make the copy diverge from what was imported, and try to drop the
        // asset: the edited copy must not disappear silently.
        await field(page, 'pac-display-name', copy).fill('PAC edited duplicate');
        await card.click();
        const confirmation = page.getByTestId('pac-confirm-deselect');
        await expect(confirmation).toBeVisible();
        await expect(page.getByTestId('pac-row')).toHaveCount(2);

        await page.getByTestId('confirm-modal-cancel').click();
        await expect(confirmation).toHaveCount(0);
        await expect(page.getByTestId('pac-row')).toHaveCount(2);
        await expect(field(page, 'pac-display-name', copy)).toHaveValue('PAC edited duplicate');

        await card.click();
        await expect(confirmation).toBeVisible();
        await page.getByTestId('confirm-modal-confirm').click();
        await expect(page.getByTestId('pac-row')).toHaveCount(0);
        await expect(card).toHaveAttribute('aria-pressed', 'false');
    });

    test('asks before directly removing an edited source-linked copy', async ({page}, testInfo) => {
        const user = principal(testInfo.project.name, TEST_USER, TEST_ALICE);
        await login(page, user);
        const base = multiContextAsset(REFERENCE_DATE);
        const sourceContext = only(base.contexts, (context) => context.broker_id === 9001, 'primary fixture context');
        const asset: SourceAssetWire = {...base, contexts: [sourceContext]};
        await routeAllocationSource(page, (asOfDate) => sourcePayload(asOfDate, [asset]));

        await navigateTo(page, TOOL_ROUTE);
        await waitForPacTool(page);

        const card = page.getByTestId(`pac-owned-asset-${asset.asset_id}`);
        await card.click();
        const rowIndex = await rowIndexWhere(page, 'pac-custody-context', sourceContext.context_key, 'source-linked context');
        await field(page, 'pac-display-name', rowIndex).fill('PAC edited before direct removal');

        await page.getByTestId(`pac-remove-asset-${rowIndex}`).click();
        const confirmation = page.getByTestId('pac-confirm-deselect');
        await expect(confirmation).toBeVisible();
        await expect(page.getByTestId('pac-row')).toHaveCount(1);
        await expect(field(page, 'pac-display-name', rowIndex)).toHaveValue('PAC edited before direct removal');

        await page.getByTestId('confirm-modal-cancel').click();
        await expect(confirmation).toHaveCount(0);
        await expect(page.getByTestId('pac-row')).toHaveCount(1);

        await page.getByTestId(`pac-remove-asset-${rowIndex}`).click();
        await expect(confirmation).toBeVisible();
        await page.getByTestId('confirm-modal-confirm').click();
        await expect(page.getByTestId('pac-row')).toHaveCount(0);
        await expect(card).toHaveAttribute('aria-pressed', 'false');
    });

    test('marks copied rows stale on a date change, ignores a superseded source response, and asks before overwriting edited facts', async ({page}, testInfo) => {
        // Production cancels the preceding request as its first line of defence.
        // This test deliberately lets source requests outlive that cancellation
        // so it can exercise the independent sequence/date guard against a real
        // late response. The switch is enabled only after login and the initial
        // source load, immediately before this scenario creates the race.
        await page.addInitScript(() => {
            const abort = AbortController.prototype.abort;
            AbortController.prototype.abort = function (reason?: unknown): void {
                if (document.documentElement?.dataset.pacE2eAllowLateSource === 'true') return;
                abort.call(this, reason);
            };
        });

        const user = principal(testInfo.project.name, TEST_USER, TEST_ALICE);
        await login(page, user);

        const today = await browserDate(page);
        const supersededDate = await browserDate(page, -1);
        const currentDate = await browserDate(page, -2);
        const base = multiContextAsset(REFERENCE_DATE);
        const sourceContext = only(base.contexts, (context) => context.broker_id === 9001, 'primary fixture context');
        const contextKey = sourceContext.context_key;
        const initialQuantity = sourceContext.custody_quantity;

        const superseded = gate();
        const current = gate();
        const unexpectedDates: string[] = [];
        await routeAllocationSource(page, async (asOfDate) => {
            if (asOfDate === today) return sourcePayload(asOfDate, [{...base, contexts: [sourceContext]}]);
            if (asOfDate === supersededDate) {
                await superseded.promise;
                return sourcePayload(asOfDate, [{...base, name: 'PAC superseded name', contexts: [{...sourceContext, custody_quantity: '88'}]}]);
            }
            if (asOfDate === currentDate) {
                await current.promise;
                return sourcePayload(asOfDate, [
                    {
                        ...base,
                        name: 'PAC fresh name',
                        quote: {...base.quote, raw_price: '200.000000000001', reference_date: currentDate},
                        contexts: [{...sourceContext, custody_quantity: '99.000000000001'}],
                    },
                ]);
            }
            // Recorded rather than thrown: an exception inside a route handler
            // hangs the request and reports as a timeout somewhere else.
            unexpectedDates.push(asOfDate);
            return sourcePayload(asOfDate, []);
        });

        await navigateTo(page, TOOL_ROUTE);
        await waitForPacTool(page);
        await page.getByTestId(`pac-owned-asset-${base.asset_id}`).click();
        const index = await rowIndexWhere(page, 'pac-custody-context', contextKey, 'imported context');

        await field(page, 'pac-display-name', index).fill('PAC edited local name');
        await field(page, 'pac-target-weight', index).fill('42.5');
        await selectSimpleOption(page, `pac-grid-mode-${index}`, 'whole');
        await field(page, 'pac-step-quantity', index).fill('2.5');
        await page.evaluate(() => {
            document.documentElement.dataset.pacE2eAllowLateSource = 'true';
        });

        // A different as-of date makes every copied fact a claim about another
        // day. The editor says so instead of quietly keeping the old numbers.
        const supersededRequest = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === REPORT_PATH && ((request.postDataJSON() as {allocation_source?: {as_of_date?: string}} | null)?.allocation_source?.as_of_date ?? null) === supersededDate, {
            timeout: 20_000,
        });
        await setDate(page, 'pac-as-of-date', supersededDate);
        await supersededRequest;
        await expect(page.getByTestId('pac-stale-source')).toBeVisible();

        const currentRequest = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === REPORT_PATH && ((request.postDataJSON() as {allocation_source?: {as_of_date?: string}} | null)?.allocation_source?.as_of_date ?? null) === currentDate, {
            timeout: 20_000,
        });
        await setDate(page, 'pac-as-of-date', currentDate);
        await currentRequest;

        // Settle the current request first. The refresh control is enabled again
        // only once that latest request has been consumed.
        const currentResponse = page.waitForResponse((response) => sourceDateOf(response.request()) === currentDate, {timeout: 20_000});
        current.open();
        const freshResponse = await currentResponse;
        expect(freshResponse.status()).toBe(200);
        await freshResponse.finished();
        await expect(page.getByTestId('pac-owned-assets-refresh')).toBeEnabled({timeout: 20_000});

        // Only now let the old request finish. Waiting through the response body
        // is the barrier proving that the superseded payload arrived *after*
        // the current payload, rather than merely being released near it.
        const supersededResponse = page.waitForResponse((response) => sourceDateOf(response.request()) === supersededDate, {timeout: 20_000});
        superseded.open();
        const lateResponse = await supersededResponse;
        expect(lateResponse.status()).toBe(200);
        await lateResponse.finished();

        const afterResponses = await rowIndexWhere(page, 'pac-custody-context', contextKey, 'context after late responses');
        await expect(field(page, 'pac-display-name', afterResponses)).toHaveValue('PAC edited local name');
        await expect(field(page, 'pac-initial-quantity', afterResponses)).toHaveValue(initialQuantity);
        // Arriving is not applying: a fresh source never rewrites the draft on its own.
        await expect(page.getByTestId('pac-stale-source')).toBeVisible();

        await page.getByTestId('pac-refresh-copied-facts').click();
        const refreshConfirm = page.getByTestId('pac-confirm-refresh');
        await expect(refreshConfirm).toBeVisible();
        await page.getByTestId('confirm-modal-cancel').click();
        await expect(refreshConfirm).toHaveCount(0);
        await expect(field(page, 'pac-display-name', afterResponses)).toHaveValue('PAC edited local name');

        await page.getByTestId('pac-refresh-copied-facts').click();
        await expect(refreshConfirm).toBeVisible();
        await page.getByTestId('confirm-modal-confirm').click();

        const refreshed = await rowIndexWhere(page, 'pac-custody-context', contextKey, 'context after refresh');
        await expect(field(page, 'pac-display-name', refreshed)).toHaveValue('PAC fresh name');
        await expect(field(page, 'pac-initial-quantity', refreshed)).toHaveValue('99.000000000001');
        await expect(field(page, 'pac-raw-price', refreshed)).toHaveValue('200.000000000001');
        await expect(field(page, 'pac-price-date', refreshed)).toHaveValue(currentDate);
        // The user's own decisions survive a refresh of the facts.
        await expect(field(page, 'pac-target-weight', refreshed)).toHaveValue('42.5');
        await expect(field(page, 'pac-step-quantity', refreshed)).toHaveValue('2.5');
        await expect(page.getByTestId('pac-stale-source')).toHaveCount(0);
        expect(unexpectedDates, 'the tool asked the allocation source for a date this test did not set').toEqual([]);
    });

    test('serializes cash and contributions by tri-state mode and never invents a valuation rate', async ({page}, testInfo) => {
        const user = principal(testInfo.project.name, TEST_USER, TEST_USER_2);
        await login(page, user);
        await routeAllocationSource(page, (asOfDate) => sourcePayload(asOfDate, []));
        await rejectCompute(page);

        await navigateTo(page, TOOL_ROUTE);
        await waitForPacTool(page);
        await expect(page.getByTestId('pac-owned-assets-empty')).toBeVisible({timeout: 20_000});

        await selectCurrency(page, 'pac-report-currency', 'EUR');
        const index = await addManualRow(page);
        await fillManualRow(page, index, {
            instrument: SHARED_INSTRUMENT,
            name: PRIMARY_NAME,
            quantity: '1',
            price: '10',
            currency: 'USD',
            target: '100',
        });

        // A foreign currency is pointed out, never resolved behind the user's back.
        await expect(page.getByTestId('pac-fx-needed')).toBeVisible();
        await expect(page.getByTestId('pac-rate-row')).toHaveCount(0);

        await expect(page.getByTestId('pac-cash-not-supplied')).toBeVisible();
        await expect(page.getByTestId('pac-contributions-not-supplied')).toBeVisible();
        const omitted = await analyzeAndCapture(page);
        expect(omitted.parameters.cash_balances).toBeNull();
        expect(omitted.parameters.contributions).toBeNull();
        expect(omitted.parameters.valuation_rates).toEqual([]);

        await selectSimpleOption(page, 'pac-cash-mode', 'none');
        await selectSimpleOption(page, 'pac-contributions-mode', 'none');
        await expect(page.getByTestId('pac-cash-none')).toBeVisible();
        await expect(page.getByTestId('pac-contributions-none')).toBeVisible();
        const explicitNone = await analyzeAndCapture(page);
        expect(explicitNone.parameters.cash_balances).toEqual([]);
        expect(explicitNone.parameters.contributions).toEqual([]);
        expect(explicitNone.parameters.valuation_rates).toEqual([]);

        await selectSimpleOption(page, 'pac-cash-mode', 'custom');
        await selectSimpleOption(page, 'pac-contributions-mode', 'custom');
        await expect(page.getByTestId('pac-cash-row')).toHaveCount(1);
        await expect(page.getByTestId('pac-contributions-row')).toHaveCount(1);
        await selectCurrency(page, 'pac-cash-currency-0', 'USD');
        await field(page, 'pac-cash-amount', 0).fill('500.000000000001');
        await selectCurrency(page, 'pac-contributions-currency-0', 'EUR');
        await field(page, 'pac-contributions-amount', 0).fill('200.000000000001');

        await enableManualRates(page);
        await expect(page.getByTestId('pac-rate-row')).toHaveCount(0);
        await page.getByTestId('pac-add-rate').click();
        await expect(page.getByTestId('pac-rate-row')).toHaveCount(1);
        await selectCurrency(page, 'pac-rate-currency-0', 'USD');
        await field(page, 'pac-rate-value', 0).fill('0.900000000001');
        await setDate(page, 'pac-rate-date-0', REFERENCE_DATE);

        const entered = await analyzeAndCapture(page);
        expect(entered.parameters.cash_balances).toEqual([{currency: 'USD', amount: '500.000000000001'}]);
        expect(entered.parameters.contributions).toEqual([{currency: 'EUR', amount: '200.000000000001'}]);
        expect(entered.parameters.valuation_rates).toEqual([{currency: 'USD', rate_to_report: '0.900000000001', reference_date: REFERENCE_DATE}]);
    });

    test('analyzes a deterministic manual scenario against the real tool API', async ({page}, testInfo) => {
        const user = principal(testInfo.project.name, TEST_BOB, TEST_CAROL);
        const tool = await openPacDirect(page, user);
        await fillDeterministicScenario(page);

        const requestPromise = page.waitForRequest(isComputeRequest, {timeout: 30_000});
        const responsePromise = page.waitForResponse((response) => isComputeRequest(response.request()), {timeout: 30_000});
        await page.getByTestId('pac-analyze').click();
        const [request, response] = await Promise.all([requestPromise, responsePromise]);

        const requestBody = request.postDataJSON() as ToolComputeRequest;
        expect(requestBody.items).toHaveLength(1);
        const item = only(requestBody.items, (candidate) => candidate.tool_code === TOOL_CODE, 'PAC compute item');
        const sent = assertScenarioRequest(item.parameters as PacInput);

        expect(response.status(), response.status() === 200 ? '' : await response.text()).toBe(200);
        const responseBody = (await response.json()) as ToolComputeResponse;
        expect(responseBody.request_id).toBe(requestBody.request_id);
        expect(responseBody.success_count).toBe(1);
        expect(responseBody.failed_count).toBe(0);
        const platformResult = only(responseBody.results, (result) => result.correlation_id === item.correlation_id && result.tool_code === TOOL_CODE, 'PAC platform result');
        expect(platformResult.status).toBe('success');
        if (platformResult.status !== 'success') throw new Error(`PAC platform failed with ${platformResult.error.code}`);
        expect(platformResult.execution_id).toBeTruthy();
        assertReadyOutput(platformResult.result as PacOutput, sent.primary, sent.secondary);

        await expect(tool).toHaveAttribute('data-busy', 'false', {timeout: 40_000});
        await expectReadyDom(page);

        // Execution metrics are a platform fact reported next to the result, not inside it.
        const metrics = page.getByTestId('tool-execution-metrics');
        await expect(metrics).toBeVisible();
        await expect(page.getByTestId('pac-result').getByTestId('tool-execution-metrics')).toHaveCount(0);

        // A successful result remains inspectable after a draft edit, but it
        // must advertise that it no longer describes the fields on screen.
        const primaryIndex = await rowIndexWhere(page, 'pac-display-name', PRIMARY_NAME, 'primary row after analysis');
        await field(page, 'pac-target-weight', primaryIndex).fill('49');
        await expect(page.getByTestId('pac-result')).toHaveAttribute('data-stale', 'true');
        await expect(page.getByTestId('pac-result-stale')).toBeVisible();
    });

    test('ignores a real compute response when the draft changes in flight', async ({page}, testInfo) => {
        const user = principal(testInfo.project.name, TEST_ADMIN, TEST_ALICE);
        const tool = await openPacDirect(page, user);
        await fillDeterministicScenario(page);

        const fetched = gate();
        const release = gate();
        let heldStatus: number | undefined;
        let heldBody: ToolComputeResponse | undefined;
        await page.route(`**${COMPUTE_PATH}`, async (route) => {
            const response = await route.fetch();
            heldStatus = response.status();
            heldBody = (await response.json()) as ToolComputeResponse;
            fetched.open();
            await release.promise;
            await route.fulfill({response}).catch(() => undefined);
        });

        const requestPromise = page.waitForRequest(isComputeRequest, {timeout: 30_000});
        await page.getByTestId('pac-analyze').click();

        try {
            const request = await requestPromise;
            const item = only((request.postDataJSON() as ToolComputeRequest).items, (candidate) => candidate.tool_code === TOOL_CODE, 'PAC compute item');
            await fetched.promise;
            expect(heldStatus).toBe(200);
            if (!heldBody) throw new Error('the real PAC compute response was not captured');
            expect(heldBody.success_count).toBe(1);
            const heldResult = only(heldBody.results, (result) => result.correlation_id === item.correlation_id, 'held PAC platform result');
            expect(heldResult.status).toBe('success');
            if (heldResult.status !== 'success') throw new Error(`held PAC result failed with ${heldResult.error.code}`);
            expect((heldResult.result as PacOutput).availability).toBe('ready');
            await expect(tool).toHaveAttribute('data-busy', 'true');

            const revisionBefore = Number(await tool.getAttribute('data-revision'));
            expect(Number.isSafeInteger(revisionBefore)).toBe(true);
            const primary = await rowIndexWhere(page, 'pac-display-name', PRIMARY_NAME, 'primary manual row');
            await field(page, 'pac-display-name', primary).fill(REVISED_NAME);
            await expect.poll(async () => Number(await tool.getAttribute('data-revision'))).toBeGreaterThan(revisionBefore);
            await expect(page.getByTestId('pac-request-stale')).toBeVisible();
        } finally {
            release.open();
        }

        await expect(tool).toHaveAttribute('data-busy', 'false', {timeout: 40_000});
        await expect(page.getByTestId('pac-response-ignored')).toBeVisible();
        await expect(page.getByTestId('pac-result')).toHaveCount(0);
        const revised = await rowIndexWhere(page, 'pac-display-name', REVISED_NAME, 'revised manual row');
        await expect(field(page, 'pac-display-name', revised)).toHaveValue(REVISED_NAME);
    });

    test('preserves the draft when the request is rejected, when waiting is stopped, and when the platform fails the item', async ({page}, testInfo) => {
        const user = principal(testInfo.project.name, TEST_USER, TEST_USER_2);
        const tool = await openPacDirect(page, user);

        await selectCurrency(page, 'pac-report-currency', 'EUR');
        await setDate(page, 'pac-as-of-date', REFERENCE_DATE);
        const index = await addManualRow(page);
        await fillManualRow(page, index, {
            instrument: SHARED_INSTRUMENT,
            name: PRIMARY_NAME,
            quantity: '10',
            price: '10',
            currency: 'EUR',
            target: '100',
            grid: 'whole',
            step: '1',
            quoteDate: REFERENCE_DATE,
        });

        async function expectDraftIntact(): Promise<void> {
            const row = await rowIndexWhere(page, 'pac-display-name', PRIMARY_NAME, 'manual row after a failure');
            await expect(page.getByTestId('pac-report-currency-trigger')).toContainText('EUR');
            await expect(page.getByTestId('pac-as-of-date')).toHaveValue(REFERENCE_DATE);
            await expect(field(page, 'pac-instrument-id', row)).toHaveValue(SHARED_INSTRUMENT);
            await expect(field(page, 'pac-initial-quantity', row)).toHaveValue('10');
            await expect(field(page, 'pac-raw-price', row)).toHaveValue('10');
            await expect(field(page, 'pac-target-weight', row)).toHaveValue('100');
            await expect(field(page, 'pac-step-quantity', row)).toHaveValue('1');
        }

        type ComputeMode = 'reject' | 'hold' | 'fail-item';
        let mode: ComputeMode = 'reject';
        const held = gate();
        await page.route(`**${COMPUTE_PATH}`, async (route) => {
            if (mode === 'reject') {
                return route.fulfill({status: 503, contentType: 'application/json', body: '{}'});
            }
            if (mode === 'hold') {
                await held.promise;
                return route.fulfill({status: 503, contentType: 'application/json', body: '{}'}).catch(() => undefined);
            }
            // A platform-level item failure: the transport is healthy and the
            // identity is the server's own, only the item outcome is rewritten.
            const response = await route.fetch();
            const body = (await response.json()) as ToolComputeResponse;
            const original = only(body.results, (result) => result.tool_code === TOOL_CODE, 'real PAC compute response item');
            const failure = {
                contract_version: original.contract_version,
                correlation_id: original.correlation_id,
                error: {code: 'execution_failed', issue_count: 0, issues: [], retryable: true},
                execution_id: original.execution_id,
                implementation_version: original.implementation_version,
                metrics: original.metrics,
                schema_fingerprint: original.schema_fingerprint,
                status: 'error',
                tool_code: original.tool_code,
            };
            return route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({...body, results: [failure], success_count: 0, failed_count: 1}),
            });
        });

        // 1. The transport says no.
        let since = await eventSeq(page);
        const rejected = page.waitForResponse((response) => isComputeRequest(response.request()), {timeout: 30_000});
        await page.getByTestId('pac-analyze').click();
        expect((await rejected).status()).toBe(503);
        const rejectionEvent = await waitForEvent(page, 'tool.pac-analyze.failed', {since});
        expect(rejectionEvent.detail).toMatchObject({kind: 'http', code: 'request_rejected'});
        await expect(tool).toHaveAttribute('data-busy', 'false', {timeout: 20_000});
        await expect(page.getByTestId('pac-client-error')).toHaveAttribute('data-error-code', 'request_rejected');
        await expect(page.getByTestId('pac-platform-error')).toHaveCount(0);
        await expect(page.getByTestId('pac-result')).toHaveCount(0);
        await expectDraftIntact();

        // 2. The user stops waiting. That is not a server cancellation, and the
        //    draft is not a casualty of it either.
        mode = 'hold';
        await page.getByTestId('pac-analyze').click();
        const stop = page.getByTestId('pac-stop-waiting');
        await expect(stop).toBeVisible({timeout: 20_000});
        await stop.click();
        await expect(tool).toHaveAttribute('data-busy', 'false', {timeout: 20_000});
        await expect(page.getByTestId('pac-client-error')).toHaveAttribute('data-error-code', 'waiting_stopped');
        await expect(page.getByTestId('pac-result')).toHaveCount(0);
        await expectDraftIntact();
        held.open();

        // 3. The platform accepts the batch and fails the item.
        mode = 'fail-item';
        since = await eventSeq(page);
        await page.getByTestId('pac-analyze').click();
        const platformEvent = await waitForEvent(page, 'tool.pac-analyze.platform-failed', {since});
        expect(platformEvent.detail).toMatchObject({code: 'execution_failed', retryable: true});
        await expect(tool).toHaveAttribute('data-busy', 'false', {timeout: 40_000});
        await expect(page.getByTestId('pac-platform-error')).toHaveAttribute('data-error-code', 'execution_failed');
        await expect(page.getByTestId('pac-client-error')).toHaveCount(0);
        await expect(page.getByTestId('pac-result')).toHaveCount(0);
        await expectDraftIntact();
    });

    test('discards an in-flight response when the authenticated account changes', async ({page}, testInfo) => {
        const originalUser = principal(testInfo.project.name, TEST_ADMIN, TEST_ALICE);
        const replacementUser = principal(testInfo.project.name, TEST_USER_2, TEST_USER);
        await login(page, originalUser);
        await routeAllocationSource(page, (asOfDate) => sourcePayload(asOfDate, []));
        await navigateTo(page, TOOL_ROUTE);
        const tool = await waitForPacTool(page);

        const index = await addManualRow(page);
        await field(page, 'pac-display-name', index).fill('PAC session-bound draft');

        const requestArrived = gate();
        const releaseResponse = gate();
        const routeSettled = gate();
        await page.route(`**${COMPUTE_PATH}`, async (route) => {
            requestArrived.open();
            await releaseResponse.promise;
            try {
                await route.fulfill({status: 503, contentType: 'application/json', body: '{}'});
            } catch {
                // The account transition aborts the old request. A late route
                // fulfilment may therefore lose its consumer, which is success.
            } finally {
                routeSettled.open();
            }
        });

        const since = await eventSeq(page);
        await page.getByTestId('pac-analyze').click();
        await requestArrived.promise;
        await expect(tool).toHaveAttribute('data-busy', 'true');

        try {
            await openMobileMenu(page);
            await page.getByTestId('logout-button').click();
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 20_000});
        } finally {
            releaseResponse.open();
        }
        await routeSettled.promise;

        const unexpectedEvents = await page.evaluate((after) => {
            const events = (window as unknown as {__lf?: {events?: {seq: number; name: string}[]}}).__lf?.events;
            if (!events) throw new Error('application event ring is unavailable after the account transition');
            return events.filter((event) => event.seq > after && (event.name === 'tool.pac-analyze.failed' || event.name === 'tool.pac-analyze.platform-failed')).map((event) => event.name);
        }, since);
        expect(unexpectedEvents, 'session_changed is intentionally silent').toEqual([]);

        await login(page, replacementUser);
        await navigateTo(page, TOOL_ROUTE);
        await waitForPacTool(page);
        await expect(page.getByTestId('pac-no-rows')).toBeVisible();
        await expect(page.getByTestId('pac-row')).toHaveCount(0);
        await expect(page.getByTestId('pac-result')).toHaveCount(0);
        await expect(page.getByTestId('pac-client-error')).toHaveCount(0);
        await expect(page.getByTestId('pac-platform-error')).toHaveCount(0);
    });
});
