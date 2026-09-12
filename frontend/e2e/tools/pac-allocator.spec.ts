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
 *      share), a zero-position candidate, all three visibility scopes, OWNER
 *      cash whose backend aggregate differs from any frontend sum, a
 *      superseded source response arriving late, and a source outage.
 *      Synthetic mocks written inside a spec are ours to shape; the STOP rule
 *      covers captured real-world snapshots, which this is not.
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
 * `PacContextEditor` keys editable fields by *position* (`pac-display-name-3`),
 * and position is mutable: a removal or a duplication renumbers everything
 * after it. So no assertion in this file trusts an index it did not just create.
 * Manual rows are found through their owned display-name value. Imported rows
 * deliberately expose no canonical-id inputs; they are found through exact
 * source facts from this spec's response and their own `data-row-index`.
 * Scanning to find an identified row is the sanctioned shape; picking
 * `.nth(0)` and hoping is not.
 *
 * ## Known observability gaps (asserted around, reported, not worked around)
 *
 * - `PacContextEditor` renders the broker name, the ownership share and the
 *   snapshot date as bare text with no `data-testid` and no `data-*` attribute,
 *   so they are not independently machine-readable. The spec scopes itself to a
 *   `pac-row` by the fixture's untranslated broker name and verifies those
 *   literal source values plus the exact locked facts and full payload on the
 *   wire. Canonical instrument/context ids are intentionally absent from the
 *   DOM and are verified only on the captured request.
 * - The valuation-only tooltip meaning, native-cash explanation wording,
 *   `CurrencySearchSelect` compact prop, and compact Analyze label have no
 *   locale-independent state attribute. This spec asserts the identified
 *   controls, equation/payload, and explanation structure, but does not infer
 *   those semantics from translated copy or CSS.
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
    broker_icon_url: string | null;
    broker_portal_url: string | null;
    broker_default_import_plugin: string | null;
    ownership_share_percent: string;
    custody_quantity: string;
}

interface SourceAssetWire {
    asset_id: number;
    instrument_key: string;
    candidate_key: string;
    name: string;
    ticker: string | null;
    asset_type: string;
    icon_url: string | null;
    active: boolean;
    usage_scope: 'owned' | 'other_users' | 'observed';
    quote: SourceQuoteWire;
    contexts: SourceContextWire[];
}

interface SourceCashBalanceWire {
    currency: string;
    amount: string;
}

interface SourceCashSourceWire {
    broker_id: number;
    broker_name: string;
    broker_icon_url: string | null;
    broker_portal_url: string | null;
    broker_default_import_plugin: string | null;
    ownership_share_percent: string;
    balances: SourceCashBalanceWire[];
}

interface AllocationSourceWire {
    generated_at: string;
    as_of_date: string;
    assets: SourceAssetWire[];
    cash_sources: SourceCashSourceWire[];
    selected_cash_balances: SourceCashBalanceWire[];
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
        candidate_key: 'candidate:asset:900001',
        name: 'PAC fixture multi-custody ETF',
        ticker: 'PACMC',
        asset_type: 'ETF',
        icon_url: null,
        active: true,
        usage_scope: 'owned',
        quote: {
            raw_price: '123.450000000001',
            currency: 'USD',
            quote_base_quantity: 100,
            reference_date: referenceDate,
            source: 'pac-fixture-close',
            days_before_requested: 1,
        },
        contexts: [
            {
                context_key: 'asset:900001:broker:9001',
                broker_id: 9001,
                broker_name: 'PAC fixture broker A',
                broker_icon_url: null,
                broker_portal_url: null,
                broker_default_import_plugin: null,
                ownership_share_percent: '25',
                custody_quantity: '12.345678901234',
            },
            {
                context_key: 'asset:900001:broker:9002',
                broker_id: 9002,
                broker_name: 'PAC fixture broker B',
                broker_icon_url: null,
                broker_portal_url: null,
                broker_default_import_plugin: null,
                ownership_share_percent: '0',
                custody_quantity: '7.000000000001',
            },
            {
                context_key: 'asset:900001:broker:9003',
                broker_id: 9003,
                broker_name: 'PAC fixture broker C',
                broker_icon_url: null,
                broker_portal_url: null,
                broker_default_import_plugin: null,
                ownership_share_percent: '100',
                custody_quantity: '0.000000000001',
            },
        ],
    };
}

/** An owned asset with no saved price. The gallery must keep it, not hide it. */
function missingPriceAsset(): SourceAssetWire {
    return {
        asset_id: 900_002,
        instrument_key: 'asset:900002',
        candidate_key: 'candidate:asset:900002',
        name: 'PAC fixture unpriced asset',
        ticker: null,
        asset_type: 'STOCK',
        icon_url: null,
        active: true,
        usage_scope: 'owned',
        quote: {raw_price: null, currency: 'EUR', quote_base_quantity: 1, reference_date: null, source: null, days_before_requested: null},
        contexts: [
            {
                context_key: 'asset:900002:broker:9004',
                broker_id: 9004,
                broker_name: 'PAC fixture broker D',
                broker_icon_url: null,
                broker_portal_url: null,
                broker_default_import_plugin: null,
                ownership_share_percent: '100',
                custody_quantity: '3',
            },
        ],
    };
}

function zeroCandidateAsset(): SourceAssetWire {
    return {
        asset_id: 900_003,
        instrument_key: 'asset:900003',
        candidate_key: 'candidate:asset:900003',
        name: 'PAC fixture zero-position candidate',
        ticker: 'PACZERO',
        asset_type: 'ETF',
        icon_url: null,
        active: true,
        usage_scope: 'owned',
        quote: {
            raw_price: '88.765432100001',
            currency: 'CHF',
            quote_base_quantity: 1000,
            reference_date: REFERENCE_DATE,
            source: 'pac-fixture-candidate-close',
            days_before_requested: 0,
        },
        contexts: [],
    };
}

function privateScopedAsset(scope: 'other_users' | 'observed', assetId: number): SourceAssetWire {
    return {
        ...zeroCandidateAsset(),
        asset_id: assetId,
        instrument_key: `asset:${assetId}`,
        candidate_key: `candidate:asset:${assetId}`,
        name: `PAC ${scope} candidate`,
        ticker: scope === 'other_users' ? 'PACOTHER' : 'PACOBS',
        usage_scope: scope,
        active: scope === 'other_users',
        contexts: [
            {
                context_key: `asset:${assetId}:broker:${assetId + 1000}`,
                broker_id: assetId + 1000,
                broker_name: `PAC private broker ${assetId}`,
                broker_icon_url: null,
                broker_portal_url: `https://private.invalid/${assetId}`,
                broker_default_import_plugin: `private-plugin-${assetId}`,
                ownership_share_percent: '37.500000000001',
                custody_quantity: '987654.321000000001',
            },
        ],
    };
}

function sourcePayload(asOfDate: string, assets: SourceAssetWire[], cash: {cashSources?: SourceCashSourceWire[]; selectedCashBalances?: SourceCashBalanceWire[]} = {}): AllocationSourceWire {
    return {
        generated_at: `${asOfDate}T12:00:00+00:00`,
        as_of_date: asOfDate,
        assets,
        cash_sources: cash.cashSources ?? [],
        selected_cash_balances: cash.selectedCashBalances ?? [],
    };
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

function semanticDecimalText(value: string): string {
    if (!value.includes('.')) return value;
    return value.replace(/0+$/, '').replace(/\.$/, '');
}

function semanticDecimalOrDash(value: string | null): string {
    return value === null ? '—' : semanticDecimalText(value);
}

async function expectSourceMetadata(row: Locator, context: SourceContextWire, sourceDate: string, quote: SourceQuoteWire): Promise<void> {
    await expect(row).toContainText(context.broker_name);
    await expect(row).toContainText(new RegExp(`(?:^|\\s)${regexLiteral(semanticDecimalText(context.ownership_share_percent))}%(?:\\s|$)`));
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
    const body = request.postDataJSON() as {allocation_source?: {as_of_date?: string; selected_cash_broker_ids?: number[]} | null} | null;
    return body?.allocation_source?.as_of_date ?? null;
}

function selectedCashBrokerIdsOf(request: Request): number[] {
    const body = request.postDataJSON() as {allocation_source?: {selected_cash_broker_ids?: number[]} | null} | null;
    return body?.allocation_source?.selected_cash_broker_ids ?? [];
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
async function routeAllocationSource(page: Page, resolve: (asOfDate: string, selectedCashBrokerIds: readonly number[]) => Promise<SourceOutcome> | SourceOutcome): Promise<void> {
    await page.route(`**${REPORT_PATH}`, async (route) => {
        const asOfDate = sourceDateOf(route.request());
        if (asOfDate === null) return route.fallback();
        const outcome = await resolve(asOfDate, selectedCashBrokerIdsOf(route.request()));
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
 * Pick the contribution-mode `SimpleSelect` option *by its value*.
 *
 * Driven from the keyboard, and not because clicking is hard: the option list is
 * `position: fixed`, recomputed from the trigger on every scroll event, so a
 * pointer click makes the harness scroll to reach it and the reposition then
 * moves it again. The list geometry is therefore *asserted* here (a list a user
 * cannot see at all is a defect, and this says so with the numbers in the
 * message) and the selection itself goes through `Home` + `ArrowDown`, which is
 * the component's own keyboard model:
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

type CashMode = 'not_supplied' | 'none' | 'broker_copy' | 'manual';

async function selectCashMode(page: Page, mode: CashMode): Promise<void> {
    const button = page.getByTestId(`pac-cash-mode-${mode.replace('_', '-')}`);
    await expect(button).toBeVisible();
    await button.click();
    await expect(button).toHaveAttribute('aria-pressed', 'true');
    if (mode === 'manual') await expect(page.getByTestId('pac-cash-row')).toHaveCount(1);
    else if (mode === 'broker_copy') await expect(page.getByTestId('pac-cash-broker-copy')).toBeVisible();
    else await expect(page.getByTestId(mode === 'none' ? 'pac-cash-none' : 'pac-cash-not-supplied')).toBeVisible();
}

async function setGridMode(page: Page, index: number, mode: 'whole' | 'fractional'): Promise<void> {
    const selected = page.getByTestId(`pac-grid-${mode}-${index}`);
    const other = page.getByTestId(`pac-grid-${mode === 'whole' ? 'fractional' : 'whole'}-${index}`);
    await expect(selected).toBeVisible();
    await selected.click();
    await expect(selected).toHaveAttribute('aria-pressed', 'true');
    await expect(other).toHaveAttribute('aria-pressed', 'false');
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

/** A locked source row identified by an exact broker fact from the response. */
async function sourceRowForContext(page: Page, context: SourceContextWire, label: string): Promise<{index: number; row: Locator}> {
    const row = page.getByTestId('pac-row').filter({hasText: context.broker_name});
    await expect(row, `${label}: source row`).toHaveCount(1);
    const rawIndex = await row.getAttribute('data-row-index');
    expect(rawIndex, `${label}: source row is missing data-row-index`).not.toBeNull();
    const index = Number(rawIndex);
    expect(Number.isSafeInteger(index), `${label}: source row has invalid data-row-index "${rawIndex}"`).toBe(true);
    return {index, row};
}

/** The sole row carrying a given origin, found by its data contract. */
async function rowIndexByOrigin(page: Page, origin: string, label: string): Promise<number> {
    const rows = page.getByTestId('pac-row');
    const total = await rows.count();
    const matches: number[] = [];
    for (let position = 0; position < total; position += 1) {
        const row = rows.nth(position);
        if ((await row.getAttribute('data-origin')) !== origin) continue;
        const rawIndex = await row.getAttribute('data-row-index');
        if (rawIndex === null) continue;
        const index = Number(rawIndex);
        if (Number.isSafeInteger(index)) matches.push(index);
    }
    expect(matches, `${label}: rows with data-origin="${origin}"`).toHaveLength(1);
    const [index] = matches;
    if (index === undefined) throw new Error(`${label}: no row with data-origin="${origin}"`);
    return index;
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

async function fillManualRow(page: Page, index: number, values: {name: string; quantity: string; price: string; currency: string; target: string; grid?: 'whole' | 'fractional'; step?: string; quoteBasis?: string; quoteDate?: string}): Promise<void> {
    await field(page, 'pac-display-name', index).fill(values.name);
    await field(page, 'pac-initial-quantity', index).fill(values.quantity);
    await field(page, 'pac-raw-price', index).fill(values.price);
    await selectCurrency(page, `pac-asset-currency-${index}`, values.currency);
    await field(page, 'pac-target-weight', index).fill(values.target);
    if (values.grid) await setGridMode(page, index, values.grid);
    if (values.step !== undefined) await field(page, 'pac-step-quantity', index).fill(values.step);
    if (values.quoteBasis !== undefined) await field(page, 'pac-price-basis', index).fill(values.quoteBasis);
    if (values.quoteDate) await setDate(page, `pac-price-date-${index}`, values.quoteDate);
}

/** Open the collapsed FX section and turn on manual valuation rates. */
async function enableManualRates(page: Page): Promise<void> {
    await expect(page.getByTestId('pac-valuation-rates')).toBeVisible();
    const disclosure = page.getByTestId('pac-valuation-rates-toggle');
    await disclosure.click();
    await expect(disclosure).toHaveAttribute('aria-expanded', 'true');
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
// Two manual rows (10 units at 10 EUR, and 0 units), 50/50 targets, 10 USD of
// existing cash at an explicit 0.9 rate and 5 EUR of contributions. Manual
// canonical ids remain hidden and distinct. Every number the backend derives
// from the visible facts is exact and is asserted below, on the wire and DOM.
// =========================================================================
async function fillDeterministicScenario(page: Page): Promise<void> {
    await selectCurrency(page, 'pac-report-currency', 'EUR');
    await setDate(page, 'pac-as-of-date', REFERENCE_DATE);

    const primary = await addManualRow(page);
    await fillManualRow(page, primary, {
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
        name: SECONDARY_NAME,
        quantity: '0',
        price: '10',
        currency: 'EUR',
        target: '50',
        grid: 'whole',
        step: '1',
        quoteDate: REFERENCE_DATE,
    });

    await selectCashMode(page, 'manual');
    await expect(page.getByTestId('pac-cash-row')).toHaveCount(1);
    await selectCurrency(page, 'pac-cash-currency-0', 'USD');
    await field(page, 'pac-cash-amount', 0).fill('10');

    await selectSimpleOption(page, 'pac-contributions-mode', 'custom');
    await expect(page.getByTestId('pac-contributions-row')).toHaveCount(1);
    await selectCurrency(page, 'pac-contributions-currency-0', 'EUR');
    await field(page, 'pac-contributions-amount', 0).fill('5');
    await field(page, 'pac-contributions-monetary-step', 0).fill('0.01');

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
    expect(parameters.contributions).toEqual([{currency: 'EUR', amount: '5', monetary_step: '0.01'}]);
    expect(parameters.valuation_rates).toEqual([{currency: 'USD', rate_to_report: '0.9', reference_date: REFERENCE_DATE}]);
    expect(parameters).not.toHaveProperty('solver');
    expect(parameters).not.toHaveProperty('orders');

    const rows = parameters.rows ?? [];
    expect(rows).toHaveLength(2);
    const primary = only(rows, (row) => row.name === PRIMARY_NAME, 'primary PAC input row');
    const secondary = only(rows, (row) => row.name === SECONDARY_NAME, 'secondary PAC input row');
    expect(primary.row_key).not.toBe(secondary.row_key);
    expect(primary.instrument_key).toBeTruthy();
    expect(secondary.instrument_key).toBeTruthy();
    expect(primary.instrument_key).not.toBe(secondary.instrument_key);
    expect(primary).toEqual({
        row_key: primary.row_key,
        instrument_key: primary.instrument_key,
        name: PRIMARY_NAME,
        initial_quantity: '10',
        quote: {raw_price: '10', currency: 'EUR', quote_base_quantity: 1, reference_date: REFERENCE_DATE},
        target_percent: '50',
        buy_grid: {mode: 'whole', quantity_step: '1'},
    });
    expect(secondary).toEqual({
        row_key: secondary.row_key,
        instrument_key: secondary.instrument_key,
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
        instrument_key: primaryInput.instrument_key,
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
        instrument_key: secondaryInput.instrument_key,
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
    expect(output.normalized.contributions).toEqual([{currency: 'EUR', amount: '5', monetary_step: '0.01'}]);
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
    await expect(result).toHaveAttribute('data-view', 'formatted');
    await expect(page.getByTestId('pac-view-formatted')).toHaveAttribute('aria-pressed', 'true');
    await expect(page.getByTestId('pac-view-exact')).toHaveAttribute('aria-pressed', 'false');
    await expect(page.getByTestId('pac-total-invested')).toHaveText('100 EUR');
    await expect(page.getByTestId('pac-total-existing-cash')).toHaveText('9 EUR');
    await expect(page.getByTestId('pac-total-contributions')).toHaveText('5 EUR');
    await expect(page.getByTestId('pac-total-combined-cash')).toHaveText('14 EUR');
    await expect(page.getByTestId('pac-max-gap')).not.toContainText('/');
    await expect(page.getByTestId('pac-squared-gap')).not.toContainText('/');

    const primary = page.getByTestId('pac-result-row').filter({hasText: PRIMARY_NAME});
    const secondary = page.getByTestId('pac-result-row').filter({hasText: SECONDARY_NAME});
    await expect(primary).toHaveCount(1);
    await expect(secondary).toHaveCount(1);
    await expect(primary).toContainText('100 EUR');
    await expect(primary).not.toContainText('10000 / 100');
    await expect(secondary).not.toContainText('-5000 / 100');
    await expect(page.getByTestId('pac-denominator-note')).toBeVisible();

    const cashPools = page.getByTestId('pac-cash-pools');
    await expect(cashPools).toBeVisible();
    const nativePoolExplanation = await cashPools.evaluate((section) => {
        const child = section.children.item(1);
        return {tagName: child?.tagName ?? null, hasText: Boolean(child?.textContent?.trim())};
    });
    expect(nativePoolExplanation).toEqual({tagName: 'P', hasText: true});
    await expect(page.getByTestId('pac-cash-pool')).toHaveCount(2);

    await page.getByTestId('pac-view-exact').click();
    await expect(result).toHaveAttribute('data-view', 'exact');
    await expect(page.getByTestId('pac-max-gap')).toHaveText('5000 / 100');
    await expect(page.getByTestId('pac-squared-gap')).toHaveText('50000000 / 10000');
    await expect(primary).toContainText('10000 / 100');
    await expect(secondary).toContainText('-5000 / 100');

    await page.getByTestId('pac-view-formatted').click();
    await expect(result).toHaveAttribute('data-view', 'formatted');
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
                for (const node of Array.from(document.getElementsByTagName('*'))) {
                    const testId = node.getAttribute('data-testid');
                    if ((testId === 'tool-host-catalog-loading' || testId === 'tool-host-component-loading') && (node as HTMLElement).getClientRects().length > 0) {
                        probe.seen = true;
                    }
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

    test('opens with compact valuation settings and funding first, accepts manual input while loading, and enforces 28/32 capacity', async ({page}, testInfo) => {
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
        const scenario = page.getByTestId('pac-scenario');
        const reportCurrency = scenario.getByTestId('pac-report-currency');
        const reportCurrencyTrigger = scenario.getByTestId('pac-report-currency-trigger');
        const asOfRoot = scenario.getByTestId('pac-as-of-date-root');
        const asOfDate = asOfRoot.getByTestId('pac-as-of-date');
        await expect(reportCurrency).toContainText(baseCurrency);
        await expect(reportCurrencyTrigger).toContainText(baseCurrency);
        await expect(asOfDate).toHaveValue(today);
        await expect(page.getByTestId('pac-no-rows')).toBeVisible();
        await expect(page.getByTestId('pac-row')).toHaveCount(0);
        await expect(scenario.getByTestId('pac-valuation-settings-info')).toBeVisible();
        await expect(page.getByTestId('pac-valuation-rates')).toHaveCount(0);

        // One compact currency control and one typed/calendar picker. The date
        // label lives outside the picker exactly once; an empty picker `label`
        // must not duplicate it inside the root.
        await expect(reportCurrency).toHaveCount(1);
        await expect(reportCurrencyTrigger).toHaveCount(1);
        await expect(asOfRoot).toHaveCount(1);
        await expect(asOfDate).toHaveAttribute('type', 'text');
        const asOfStructure = await asOfRoot.evaluate((root) => {
            const external = root.parentElement;
            const externalText = external?.children.item(0)?.textContent?.trim() ?? '';
            return {
                externalTag: external?.tagName ?? null,
                externalTextPresent: externalText.length > 0,
                duplicatedInside: externalText.length > 0 && (root.textContent ?? '').includes(externalText),
                internalLabels: root.getElementsByTagName('label').length,
                valuationControlCount: external?.parentElement?.children.length ?? 0,
            };
        });
        expect(asOfStructure).toEqual({externalTag: 'LABEL', externalTextPresent: true, duplicatedInside: false, internalLabels: 0, valuationControlCount: 2});

        const orderedSections = tool.getByTestId(/^(pac-funding|pac-owned-assets)$/);
        await expect(orderedSections).toHaveCount(2);
        expect(await orderedSections.evaluateAll((sections) => sections.map((section) => section.getAttribute('data-testid'))), 'funding must precede the asset gallery').toEqual(['pac-funding', 'pac-owned-assets']);

        // Manual entry does not wait for the portfolio.
        const index = await addManualRow(page);
        await field(page, 'pac-display-name', index).fill('PAC manual while loading');
        await expect(page.getByTestId('pac-owned-assets-loading')).toBeVisible();
        await expect(page.getByTestId(`pac-initial-state-${index}`)).toBeVisible();
        await expect(page.getByTestId(`pac-target-state-${index}`)).toBeVisible();
        for (const prefix of ['pac-initial-quantity', 'pac-raw-price', 'pac-target-weight', 'pac-step-quantity']) {
            await expect(field(page, prefix, index)).toHaveAttribute('type', 'text');
            await expect(field(page, prefix, index)).toHaveAttribute('inputmode', 'decimal');
        }
        await expect(page.getByTestId(`pac-asset-currency-${index}-trigger`)).toHaveCount(1);
        await expect(page.getByTestId(`pac-price-date-${index}`)).toHaveAttribute('type', 'text');
        const quoteBasis = field(page, 'pac-price-basis', index);
        await expect(quoteBasis).toHaveAttribute('type', 'number');
        await expect(quoteBasis).toHaveAttribute('min', '1');
        await expect(quoteBasis).toHaveAttribute('step', '1');
        await quoteBasis.fill('1000');
        await expect(quoteBasis).toHaveValue('1000');
        await expect(page.getByTestId(`pac-grid-whole-${index}`)).toHaveAttribute('aria-pressed', 'true');
        await expect(page.getByTestId(`pac-grid-fractional-${index}`)).toHaveAttribute('aria-pressed', 'false');
        await expect(field(page, 'pac-step-quantity', index)).toHaveValue('1');

        held.open();
        await expect(page.getByTestId('pac-owned-asset-900001')).toBeVisible({timeout: 20_000});
        await expect(page.getByTestId('pac-owned-assets-loading')).toHaveCount(0);
        expect(releasedFor).toBe(today);
        // The row the user typed while the portfolio was loading is still there.
        await expect(field(page, 'pac-display-name', index)).toHaveValue('PAC manual while loading');
        await expect(tool).toHaveAttribute('data-busy', 'false');

        for (let ownedRows = 1; ownedRows < 28; ownedRows += 1) {
            await page.getByTestId('pac-add-manual-asset').click();
        }
        await expect(page.getByTestId('pac-row')).toHaveCount(28);
        await expect(page.getByTestId('pac-selected-context-count')).toContainText('28');
        await expect(page.getByTestId('pac-row-limit-warning')).toBeVisible();
        for (let ownedRows = 28; ownedRows < 32; ownedRows += 1) {
            await page.getByTestId('pac-add-manual-asset').click();
        }
        await expect(page.getByTestId('pac-row')).toHaveCount(32);
        await expect(page.getByTestId('pac-selected-context-count')).toContainText('32');
        await page.getByTestId('pac-add-manual-asset').click();
        await expect(page.getByTestId('pac-row')).toHaveCount(32);
    });

    test('keeps manual entry available when the allocation source is empty and when it fails, and recovers on retry', async ({page}) => {
        await login(page, TEST_USER_2);
        let sourceMode: 'empty' | 'failure' | 'recovered' = 'empty';
        await routeAllocationSource(page, (asOfDate) => {
            if (sourceMode === 'failure') return 'reject';
            return sourcePayload(asOfDate, sourceMode === 'recovered' ? [missingPriceAsset()] : []);
        });

        await navigateTo(page, TOOL_ROUTE);
        await waitForPacTool(page);
        await expect(page.getByTestId('pac-owned-assets-empty')).toBeVisible({timeout: 20_000});
        const emptyRow = await addManualRow(page);
        await field(page, 'pac-display-name', emptyRow).fill('PAC manual without portfolio');
        await expect(field(page, 'pac-display-name', emptyRow)).toHaveValue('PAC manual without portfolio');
        // Now the failing source. The editor must stay usable and must offer an
        // explicit retry — nothing here retries on its own.
        sourceMode = 'failure';
        await navigateTo(page, TOOL_ROUTE);
        await waitForPacTool(page);
        await expect(page.getByTestId('pac-owned-assets-error')).toBeVisible({timeout: 20_000});

        const fallbackRow = await addManualRow(page);
        await field(page, 'pac-display-name', fallbackRow).fill('PAC manual fallback');
        await field(page, 'pac-initial-quantity', fallbackRow).fill('4.500000000001');
        await expect(field(page, 'pac-initial-quantity', fallbackRow)).toHaveValue('4.500000000001');

        sourceMode = 'recovered';
        await page.getByTestId('pac-owned-assets-retry').click();
        await expect(page.getByTestId('pac-owned-asset-900002')).toBeVisible({timeout: 20_000});
        await expect(page.getByTestId('pac-owned-assets-error')).toHaveCount(0);
        await expect(field(page, 'pac-display-name', fallbackRow)).toHaveValue('PAC manual fallback');
    });

    test('renders the real OWNER catalogue by canonical asset and imports identified contexts as locked facts with hidden ids', async ({page}) => {
        const user = TEST_ADMIN;
        await login(page, user);

        const sourceResponse = page.waitForResponse((response) => sourceDateOf(response.request()) !== null, {timeout: 30_000});
        await navigateTo(page, TOOL_ROUTE);
        await waitForPacTool(page);
        const source = ((await (await sourceResponse).json()) as {allocation_source: AllocationSourceWire}).allocation_source;

        const ownedAssets = source.assets.filter((asset) => asset.usage_scope === 'owned');
        if (ownedAssets.length === 0) {
            throw new Error(`${user.username} is expected to own broker positions — see populate_mock_data.py (populate_broker_user_access / populate_transactions)`);
        }

        // The default scope is OWNER. Each card is tied to an id in this exact
        // response, never to a global seeded count.
        await expect(page.getByTestId('pac-owned-assets-loading')).toHaveCount(0, {timeout: 20_000});
        for (const asset of ownedAssets) {
            await expect(page.getByTestId(`pac-owned-asset-${asset.asset_id}`), `card for asset ${asset.asset_id}`).toHaveCount(1);
        }
        const unpricedAssets = ownedAssets.filter((asset) => asset.quote.raw_price === null);
        if (unpricedAssets.length === 0) {
            throw new Error(`${user.username} is expected to own the seeded unpriced holding — see populate_assets / populate_transactions in backend/test_scripts/test_db/populate_mock_data.py`);
        }
        for (const asset of unpricedAssets) {
            await expect(page.getByTestId(`pac-owned-asset-${asset.asset_id}`), `unpriced card for asset ${asset.asset_id}`).toBeVisible();
        }
        // The asset under test is identified by id, chosen deterministically as
        // the one with the most custody contexts (ties resolved by id) — never
        // "the first card".
        const contextualAssets = ownedAssets.filter((asset) => asset.contexts.length > 0);
        if (contextualAssets.length === 0) {
            throw new Error(`${user.username} is expected to own at least one custody context — see populate_transactions in backend/test_scripts/test_db/populate_mock_data.py`);
        }
        const target = contextualAssets.reduce((selected, candidate) => (candidate.contexts.length > selected.contexts.length || (candidate.contexts.length === selected.contexts.length && candidate.asset_id < selected.asset_id) ? candidate : selected));
        const card = page.getByTestId(`pac-owned-asset-${target.asset_id}`);
        await expect(card).toHaveAttribute('aria-pressed', 'false');
        await card.click();

        // Atomic: every OWNER custody context of that one canonical asset, and
        // nothing else, in a draft that started empty.
        await expect(page.getByTestId('pac-row')).toHaveCount(target.contexts.length);
        await expect(card).toHaveAttribute('aria-pressed', 'true');

        for (const context of target.contexts) {
            const {index, row} = await sourceRowForContext(page, context, `context ${context.context_key}`);
            await expectSourceMetadata(row, context, source.as_of_date, target.quote);
            await expect(page.getByTestId(`pac-imported-initial-quantity-${index}`)).toContainText(semanticDecimalText(context.custody_quantity));
            await expect(page.getByTestId(`pac-imported-price-${index}`)).toContainText(semanticDecimalOrDash(target.quote.raw_price));
            await expect(page.getByTestId(`pac-imported-price-${index}`)).toContainText(target.quote.currency);
            await expect(page.getByTestId(`pac-imported-price-basis-${index}`)).toContainText(String(target.quote.quote_base_quantity));
            for (const prefix of ['pac-display-name', 'pac-initial-quantity', 'pac-raw-price', 'pac-asset-currency', 'pac-price-basis', 'pac-price-date', 'pac-instrument-id', 'pac-custody-context']) {
                await expect(page.getByTestId(`${prefix}-${index}`)).toHaveCount(0);
            }
            await expect(row).not.toContainText(target.instrument_key);
            await expect(row).not.toContainText(context.context_key);
            // The copy carries locked facts, while target and grid remain the
            // user's editable decisions with coherent whole-unit defaults.
            await expect(field(page, 'pac-target-weight', index)).toHaveValue('');
            await expect(page.getByTestId(`pac-grid-whole-${index}`)).toHaveAttribute('aria-pressed', 'true');
            await expect(page.getByTestId(`pac-grid-fractional-${index}`)).toHaveAttribute('aria-pressed', 'false');
            await expect(field(page, 'pac-step-quantity', index)).toHaveValue('1');
        }

        // Unmodified copies are dropped without a question.
        await card.click();
        await expect(page.getByTestId('pac-row')).toHaveCount(0);
        await expect(page.getByTestId('pac-confirm-deselect')).toHaveCount(0);
        await expect(card).toHaveAttribute('aria-pressed', 'false');
    });

    test('filters a multi-scope gallery without leaking foreign details and imports OWNER contexts plus a zero candidate as locked facts', async ({page}, testInfo) => {
        const user = principal(testInfo.project.name, TEST_USER, TEST_ALICE);
        await login(page, user);
        const asset = multiContextAsset(REFERENCE_DATE);
        const unpriced = missingPriceAsset();
        const zeroCandidate = zeroCandidateAsset();
        const otherUsers = privateScopedAsset('other_users', 900_004);
        const observed = privateScopedAsset('observed', 900_005);
        let requestedDate = '';
        await routeAllocationSource(page, (asOfDate) => {
            requestedDate = asOfDate;
            return sourcePayload(asOfDate, [observed, asset, otherUsers, unpriced, zeroCandidate]);
        });
        await rejectCompute(page);

        await navigateTo(page, TOOL_ROUTE);
        await waitForPacTool(page);
        await selectCurrency(page, 'pac-report-currency', 'EUR');

        const card = page.getByTestId(`pac-owned-asset-${asset.asset_id}`);
        const unpricedCard = page.getByTestId(`pac-owned-asset-${unpriced.asset_id}`);
        const zeroCard = page.getByTestId(`pac-owned-asset-${zeroCandidate.asset_id}`);
        const otherCard = page.getByTestId(`pac-owned-asset-${otherUsers.asset_id}`);
        const observedCard = page.getByTestId(`pac-owned-asset-${observed.asset_id}`);
        await expect(card).toHaveCount(1);
        // An asset with no saved price keeps its card: the user decides what to
        // do about the missing quote, the gallery does not decide for them.
        await expect(unpricedCard).toHaveCount(1);
        await expect(unpricedCard).toBeVisible();
        await expect(zeroCard).toBeVisible();
        await expect(otherCard).toHaveCount(0);
        await expect(observedCard).toHaveCount(0);
        await expect(page.getByTestId('pac-valuation-rates')).toHaveCount(0);

        const ownedScope = page.getByTestId('pac-asset-scope-owned');
        const otherScope = page.getByTestId('pac-asset-scope-other_users');
        const observedScope = page.getByTestId('pac-asset-scope-observed');
        await expect(ownedScope).toHaveAttribute('aria-pressed', 'true');
        await expect(otherScope).toHaveAttribute('aria-pressed', 'false');
        await expect(observedScope).toHaveAttribute('aria-pressed', 'false');
        expect(await ownedScope.evaluate((button) => button.lastElementChild?.textContent?.trim())).toBe('3');
        expect(await otherScope.evaluate((button) => button.lastElementChild?.textContent?.trim())).toBe('1');
        expect(await observedScope.evaluate((button) => button.lastElementChild?.textContent?.trim())).toBe('1');

        await otherScope.click();
        await observedScope.click();
        await expect(otherCard).toHaveAttribute('data-usage-scope', 'other_users');
        await expect(otherCard).toHaveAttribute('data-lifecycle', 'active');
        await expect(observedCard).toHaveAttribute('data-usage-scope', 'observed');
        await expect(observedCard).toHaveAttribute('data-lifecycle', 'inactive');
        for (const [privateCard, privateAsset] of [
            [otherCard, otherUsers],
            [observedCard, observed],
        ] as const) {
            const privateContext = only(privateAsset.contexts, () => true, `private context for ${privateAsset.asset_id}`);
            await expect(privateCard).not.toContainText(privateContext.broker_name);
            if (privateContext.broker_default_import_plugin) {
                await expect(privateCard).not.toContainText(privateContext.broker_default_import_plugin);
            }
            await expect(privateCard).not.toContainText(semanticDecimalText(privateContext.ownership_share_percent));
            await expect(privateCard).not.toContainText(semanticDecimalText(privateContext.custody_quantity));
        }

        await card.click();
        await expect(page.getByTestId('pac-row')).toHaveCount(asset.contexts.length);
        await expect(page.getByTestId('pac-valuation-rates')).toBeVisible();

        for (const context of asset.contexts) {
            const {index, row} = await sourceRowForContext(page, context, `fixture context ${context.context_key}`);
            await expectSourceMetadata(row, context, requestedDate, asset.quote);
            await expect(page.getByTestId(`pac-imported-initial-quantity-${index}`)).toContainText(semanticDecimalText(context.custody_quantity));
            await expect(page.getByTestId(`pac-imported-price-${index}`)).toContainText(semanticDecimalOrDash(asset.quote.raw_price));
            await expect(page.getByTestId(`pac-imported-price-${index}`)).toContainText('USD');
            await expect(page.getByTestId(`pac-imported-price-basis-${index}`)).toContainText('100');
            await expect(page.getByTestId(`pac-imported-ownership-share-${index}`)).toContainText(`${semanticDecimalText(context.ownership_share_percent)}%`);
            for (const prefix of ['pac-display-name', 'pac-initial-quantity', 'pac-raw-price', 'pac-asset-currency', 'pac-price-basis', 'pac-price-date', 'pac-instrument-id', 'pac-custody-context']) {
                await expect(page.getByTestId(`${prefix}-${index}`)).toHaveCount(0);
            }
            await expect(row).not.toContainText(asset.instrument_key);
            await expect(row).not.toContainText(context.context_key);
            await expect(field(page, 'pac-target-weight', index)).toHaveValue('');
            await expect(page.getByTestId(`pac-grid-whole-${index}`)).toHaveAttribute('aria-pressed', 'true');
            await expect(page.getByTestId(`pac-grid-fractional-${index}`)).toHaveAttribute('aria-pressed', 'false');
            await expect(field(page, 'pac-step-quantity', index)).toHaveValue('1');
        }

        await zeroCard.click();
        await expect(page.getByTestId('pac-row')).toHaveCount(asset.contexts.length + 1);
        const candidateRow = page.getByTestId('pac-row').filter({hasText: zeroCandidate.name});
        await expect(candidateRow).toHaveCount(1);
        const rawCandidateIndex = await candidateRow.getAttribute('data-row-index');
        expect(rawCandidateIndex, 'zero candidate row is missing data-row-index').not.toBeNull();
        const candidateIndex = Number(rawCandidateIndex);
        expect(Number.isSafeInteger(candidateIndex), `zero candidate row index "${rawCandidateIndex}"`).toBe(true);
        await expect(candidateRow).toHaveAttribute('data-origin', 'catalog_candidate');
        await expect(candidateRow).toHaveAttribute('data-source-mode', 'locked');
        await expect(page.getByTestId(`pac-imported-initial-quantity-${candidateIndex}`)).toContainText('0');
        await expect(page.getByTestId(`pac-imported-price-${candidateIndex}`)).toContainText(semanticDecimalOrDash(zeroCandidate.quote.raw_price));
        await expect(page.getByTestId(`pac-imported-price-${candidateIndex}`)).toContainText('CHF');
        await expect(page.getByTestId(`pac-imported-price-basis-${candidateIndex}`)).toContainText('1000');
        await expect(page.getByTestId(`pac-imported-ownership-share-${candidateIndex}`)).toHaveCount(0);
        await expect(candidateRow).not.toContainText(zeroCandidate.instrument_key);
        await expect(candidateRow).not.toContainText(zeroCandidate.candidate_key);

        // What actually leaves the browser: the same decimals, digit for digit,
        // with the quote basis the source declared and coherent default grid.
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
                buy_grid: {mode: 'whole', quantity_step: '1'},
            });
        }
        const candidateWire = only(parameters.rows ?? [], (candidate) => candidate.row_key === zeroCandidate.candidate_key, 'wire row for the zero-position candidate');
        expect(candidateWire).toEqual({
            row_key: zeroCandidate.candidate_key,
            instrument_key: zeroCandidate.instrument_key,
            name: zeroCandidate.name,
            initial_quantity: '0',
            quote: {raw_price: '88.765432100001', currency: 'CHF', quote_base_quantity: 1000, reference_date: REFERENCE_DATE},
            target_percent: '',
            buy_grid: {mode: 'whole', quantity_step: '1'},
        });

        await expect(page.getByTestId('pac-client-error')).toHaveAttribute('data-error-code', 'request_rejected');
    });

    test('duplicates a locked import into a source-free editable manual row while keeping canonical ids hidden', async ({page}, testInfo) => {
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
        const {index: original, row: originalRow} = await sourceRowForContext(page, sourceContext, 'imported context');
        await expect(originalRow).toHaveAttribute('data-origin', 'portfolio_context');
        await expect(originalRow).toHaveAttribute('data-source-mode', 'locked');

        await field(page, 'pac-target-weight', original).fill('42.5');
        await setGridMode(page, original, 'fractional');
        await field(page, 'pac-step-quantity', original).fill('2.500000000001');

        await page.getByTestId(`pac-duplicate-asset-${original}`).click();
        await expect(page.getByTestId('pac-row')).toHaveCount(2);

        const copy = await rowIndexByOrigin(page, 'manual_duplicate', 'source-free duplicate');
        const copiedRow = page.getByTestId('pac-row').filter({has: field(page, 'pac-display-name', copy)});
        await expect(copiedRow).toHaveCount(1);
        await expect(copiedRow).toHaveAttribute('data-source-mode', 'manual');
        await expect(copiedRow.getByTestId(`pac-initial-state-${copy}`)).toBeVisible();
        await expect(copiedRow.getByTestId(`pac-target-state-${copy}`)).toBeVisible();
        await expect(copiedRow.getByTestId(`pac-imported-initial-quantity-${copy}`)).toHaveCount(0);
        await expect(copiedRow.getByTestId(`pac-provider-source-${copy}`)).toHaveCount(0);
        await expect(field(page, 'pac-display-name', copy)).toBeEnabled();
        await expect(field(page, 'pac-display-name', copy)).toHaveValue(asset.name);
        await expect(field(page, 'pac-initial-quantity', copy)).toBeEnabled();
        await expect(field(page, 'pac-initial-quantity', copy)).toHaveValue(sourceContext.custody_quantity);
        await expect(field(page, 'pac-raw-price', copy)).toBeEnabled();
        await expect(field(page, 'pac-raw-price', copy)).toHaveValue(asset.quote.raw_price ?? '');
        await expect(page.getByTestId(`pac-asset-currency-${copy}-trigger`)).toContainText(asset.quote.currency);
        await expect(field(page, 'pac-price-basis', copy)).toHaveValue(String(asset.quote.quote_base_quantity));
        await expect(field(page, 'pac-price-date', copy)).toHaveValue(asset.quote.reference_date ?? '');
        await expect(field(page, 'pac-target-weight', copy)).toHaveValue('42.5');
        await expect(page.getByTestId(`pac-grid-fractional-${copy}`)).toHaveAttribute('aria-pressed', 'true');
        await expect(field(page, 'pac-step-quantity', copy)).toHaveValue('2.500000000001');

        for (const index of [original, copy]) {
            await expect(page.getByTestId(`pac-instrument-id-${index}`)).toHaveCount(0);
            await expect(page.getByTestId(`pac-custody-context-${index}`)).toHaveCount(0);
        }
        await expect(originalRow).not.toContainText(asset.instrument_key);
        await expect(originalRow).not.toContainText(contextKey);

        // The wire is the complete statement: everything but the row key.
        const {parameters} = await analyzeAndCapture(page);
        const rows = parameters.rows ?? [];
        expect(rows).toHaveLength(2);
        const sourceRow = only(rows, (row) => row.row_key === contextKey, 'source row on the wire');
        const copyRow = only(rows, (row) => row.row_key !== contextKey, 'duplicated row on the wire');
        const {row_key: sourceKey, ...sourcePayloadRest} = sourceRow;
        const {row_key: copiedKey, ...copyPayloadRest} = copyRow;
        expect(copiedKey).not.toBe(sourceKey);
        expect(copyPayloadRest).toEqual(sourcePayloadRest);
        expect(sourcePayloadRest).toMatchObject({
            initial_quantity: sourceContext.custody_quantity,
            target_percent: '42.5',
            buy_grid: {mode: 'fractional', quantity_step: '2.500000000001'},
        });
        await expect(copiedRow).not.toContainText(copyRow.instrument_key);
        await expect(copiedRow).not.toContainText(copyRow.row_key);

        // The duplicate is independent. Deselecting the source asset confirms
        // the modified locked row, then removes only that row.
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
        await expect(page.getByTestId('pac-row')).toHaveCount(1);
        await expect(card).toHaveAttribute('aria-pressed', 'false');
        const remaining = await rowIndexWhere(page, 'pac-display-name', 'PAC edited duplicate', 'manual duplicate after source deselection');
        await expect(page.getByTestId('pac-row')).toHaveAttribute('data-origin', 'manual_duplicate');
        await expect(field(page, 'pac-display-name', remaining)).toHaveValue('PAC edited duplicate');
    });

    test('asks before directly removing a locked source row whose editable target changed', async ({page}, testInfo) => {
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
        const {index: rowIndex, row} = await sourceRowForContext(page, sourceContext, 'source-linked context');
        await expect(row).toHaveAttribute('data-source-mode', 'locked');
        await field(page, 'pac-target-weight', rowIndex).fill('42.5');

        await page.getByTestId(`pac-remove-asset-${rowIndex}`).click();
        const confirmation = page.getByTestId('pac-confirm-deselect');
        await expect(confirmation).toBeVisible();
        await expect(page.getByTestId('pac-row')).toHaveCount(1);
        await expect(field(page, 'pac-target-weight', rowIndex)).toHaveValue('42.5');

        await page.getByTestId('confirm-modal-cancel').click();
        await expect(confirmation).toHaveCount(0);
        await expect(page.getByTestId('pac-row')).toHaveCount(1);
        await expect(field(page, 'pac-target-weight', rowIndex)).toHaveValue('42.5');

        await page.getByTestId(`pac-remove-asset-${rowIndex}`).click();
        await expect(confirmation).toBeVisible();
        await page.getByTestId('confirm-modal-confirm').click();
        await expect(page.getByTestId('pac-row')).toHaveCount(0);
        await expect(card).toHaveAttribute('aria-pressed', 'false');
    });

    test('marks locked rows stale, ignores a superseded source response, and refreshes facts without replacing target or grid choices', async ({page}, testInfo) => {
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
        const {index} = await sourceRowForContext(page, sourceContext, 'imported context');

        await field(page, 'pac-target-weight', index).fill('42.5');
        await setGridMode(page, index, 'fractional');
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

        const {index: afterResponses, row: staleRow} = await sourceRowForContext(page, sourceContext, 'context after late responses');
        await expect(staleRow).toContainText(base.name);
        await expect(staleRow).not.toContainText('PAC fresh name');
        await expect(page.getByTestId(`pac-imported-initial-quantity-${afterResponses}`)).toContainText(semanticDecimalText(initialQuantity));
        // Arriving is not applying: a fresh source never rewrites the draft on its own.
        await expect(page.getByTestId('pac-stale-source')).toBeVisible();

        await page.getByTestId('pac-refresh-copied-facts').click();
        await expect(page.getByTestId('pac-confirm-refresh')).toHaveCount(0);

        const refreshedContext = {...sourceContext, custody_quantity: '99.000000000001'};
        const {index: refreshed, row: refreshedRow} = await sourceRowForContext(page, refreshedContext, 'context after refresh');
        await expect(refreshedRow).toContainText('PAC fresh name');
        await expect(refreshedRow).not.toContainText('PAC superseded name');
        await expect(page.getByTestId(`pac-imported-initial-quantity-${refreshed}`)).toContainText('99.000000000001');
        await expect(page.getByTestId(`pac-imported-price-${refreshed}`)).toContainText('200.000000000001');
        await expect(refreshedRow).toContainText(currentDate);
        // The user's own decisions survive a refresh of the facts.
        await expect(field(page, 'pac-target-weight', refreshed)).toHaveValue('42.5');
        await expect(field(page, 'pac-step-quantity', refreshed)).toHaveValue('2.5');
        await expect(page.getByTestId(`pac-grid-fractional-${refreshed}`)).toHaveAttribute('aria-pressed', 'true');
        await expect(page.getByTestId('pac-stale-source')).toHaveCount(0);
        expect(unexpectedDates, 'the tool asked the allocation source for a date this test did not set').toEqual([]);
    });

    test('uses OWNER backend cash aggregates, serializes contribution steps, and exposes a conditional valuation equation without converting locally', async ({page}, testInfo) => {
        const user = principal(testInfo.project.name, TEST_USER, TEST_USER_2);
        await login(page, user);
        const cashSources: SourceCashSourceWire[] = [
            {
                broker_id: 9101,
                broker_name: 'PAC OWNER cash A',
                broker_icon_url: null,
                broker_portal_url: null,
                broker_default_import_plugin: null,
                ownership_share_percent: '25',
                balances: [
                    {currency: 'EUR', amount: '100.10'},
                    {currency: 'USD', amount: '5.50'},
                ],
            },
            {
                broker_id: 9102,
                broker_name: 'PAC OWNER cash B',
                broker_icon_url: null,
                broker_portal_url: null,
                broker_default_import_plugin: null,
                ownership_share_percent: '75',
                balances: [
                    {currency: 'EUR', amount: '300.20'},
                    {currency: 'CHF', amount: '7.25'},
                ],
            },
        ];
        const backendAggregate = [
            {currency: 'EUR', amount: '777.770000000001'},
            {currency: 'USD', amount: '8.880000000001'},
        ];
        await routeAllocationSource(page, (asOfDate, selectedBrokerIds) => {
            const selection = [...selectedBrokerIds].sort((left, right) => left - right);
            const selectedCashBalances = selection.join(',') === '9101,9102' ? backendAggregate : selection.join(',') === '9101' ? [{currency: 'EUR', amount: '111.110000000001'}] : [];
            return sourcePayload(asOfDate, [], {cashSources, selectedCashBalances});
        });
        await rejectCompute(page);

        await navigateTo(page, TOOL_ROUTE);
        await waitForPacTool(page);
        await expect(page.getByTestId('pac-owned-assets-empty')).toBeVisible({timeout: 20_000});

        await selectCurrency(page, 'pac-report-currency', 'EUR');
        await expect(page.getByTestId('pac-valuation-rates')).toHaveCount(0);
        const index = await addManualRow(page);
        await fillManualRow(page, index, {
            name: PRIMARY_NAME,
            quantity: '1',
            price: '10',
            currency: 'USD',
            target: '100',
            quoteBasis: '1000',
        });

        // A foreign currency is pointed out, never resolved behind the user's back.
        await expect(page.getByTestId('pac-valuation-rates')).toBeVisible();
        await expect(page.getByTestId('pac-fx-needed')).toBeVisible();
        await expect(page.getByTestId('pac-rate-row')).toHaveCount(0);

        await expect(page.getByTestId('pac-cash-not-supplied')).toBeVisible();
        await expect(page.getByTestId('pac-contributions-not-supplied')).toBeVisible();
        const omitted = await analyzeAndCapture(page);
        expect(omitted.parameters.cash_balances).toBeNull();
        expect(omitted.parameters.contributions).toBeNull();
        expect(omitted.parameters.valuation_rates).toEqual([]);
        const omittedRow = only(omitted.parameters.rows ?? [], (row) => row.name === PRIMARY_NAME, 'omitted-mode PAC row');
        expect(omittedRow.quote?.quote_base_quantity).toBe(1000);

        await selectCashMode(page, 'none');
        await selectSimpleOption(page, 'pac-contributions-mode', 'none');
        await expect(page.getByTestId('pac-cash-none')).toBeVisible();
        await expect(page.getByTestId('pac-contributions-none')).toBeVisible();
        const explicitNone = await analyzeAndCapture(page);
        expect(explicitNone.parameters.cash_balances).toEqual([]);
        expect(explicitNone.parameters.contributions).toEqual([]);
        expect(explicitNone.parameters.valuation_rates).toEqual([]);

        await selectCashMode(page, 'broker_copy');
        const brokerA = page.getByTestId('pac-cash-broker-9101');
        const brokerB = page.getByTestId('pac-cash-broker-9102');
        await expect(brokerA).toBeEnabled();
        await expect(brokerB).toBeEnabled();
        const brokerARequest = page.waitForRequest((request) => sourceDateOf(request) !== null && selectedCashBrokerIdsOf(request).join(',') === '9101', {timeout: 20_000});
        await brokerA.click();
        await brokerARequest;
        await expect(page.getByTestId('pac-allocator-tool')).toHaveAttribute('data-cash-source', 'ready');

        const bothBrokersRequest = page.waitForRequest((request) => sourceDateOf(request) !== null && selectedCashBrokerIdsOf(request).join(',') === '9101,9102', {timeout: 20_000});
        await brokerB.click();
        await bothBrokersRequest;
        await expect(page.getByTestId('pac-allocator-tool')).toHaveAttribute('data-cash-source', 'ready');
        await expect(page.getByTestId('pac-cash-aggregate-EUR')).toContainText('777.770000000001');
        await expect(page.getByTestId('pac-cash-aggregate-USD')).toContainText('8.880000000001');
        const copiedCash = await analyzeAndCapture(page);
        expect(copiedCash.parameters.cash_balances).toEqual(backendAggregate);
        expect(copiedCash.parameters.cash_balances).not.toEqual([
            {currency: 'EUR', amount: '400.30'},
            {currency: 'USD', amount: '5.50'},
            {currency: 'CHF', amount: '7.25'},
        ]);

        await selectCashMode(page, 'manual');
        await selectSimpleOption(page, 'pac-contributions-mode', 'custom');
        await expect(page.getByTestId('pac-cash-row')).toHaveCount(1);
        await expect(page.getByTestId('pac-contributions-row')).toHaveCount(1);
        await expect(field(page, 'pac-cash-monetary-step', 0)).toHaveCount(0);
        const contributionStep = field(page, 'pac-contributions-monetary-step', 0);
        await expect(contributionStep).toHaveValue('0.01');
        await selectCurrency(page, 'pac-cash-currency-0', 'USD');
        await field(page, 'pac-cash-amount', 0).fill('500.000000000001');
        await selectCurrency(page, 'pac-contributions-currency-0', 'EUR');
        await field(page, 'pac-contributions-amount', 0).fill('200.000000000001');
        await contributionStep.fill('0.000000000001');

        await enableManualRates(page);
        await expect(page.getByTestId('pac-rate-info')).toBeVisible();
        await expect(page.getByTestId('pac-rate-row')).toHaveCount(0);
        await page.getByTestId('pac-add-rate').click();
        await expect(page.getByTestId('pac-rate-row')).toHaveCount(1);
        await selectCurrency(page, 'pac-rate-currency-0', 'USD');
        await field(page, 'pac-rate-value', 0).fill('0.900000000001');
        await setDate(page, 'pac-rate-date-0', REFERENCE_DATE);

        const rateRow = page.getByTestId('pac-rate-row');
        await expect(rateRow).toContainText('1');
        await expect(rateRow).toContainText('=');
        await expect(rateRow).toContainText('EUR');
        await expect(page.getByTestId('pac-rate-currency-0-trigger')).toContainText('USD');
        await expect(field(page, 'pac-rate-value', 0)).toHaveValue('0.900000000001');
        const equationTargetsReportCurrency = await rateRow.evaluate((row) => {
            const text = row.textContent ?? '';
            const one = text.indexOf('1');
            const native = text.indexOf('USD', one + 1);
            const equals = text.indexOf('=', native + 1);
            const report = text.indexOf('EUR', equals + 1);
            return one >= 0 && native > one && equals > native && report > equals;
        });
        expect(equationTargetsReportCurrency, 'valuation equation must read from one native unit into the current report currency').toBe(true);
        const rateDateStructure = await page.getByTestId('pac-rate-date-0-root').evaluate((root) => {
            let ancestorLabels = 0;
            let ancestor: Element | null = root.parentElement;
            while (ancestor) {
                if (ancestor.tagName === 'LABEL') ancestorLabels += 1;
                if ((ancestor as HTMLElement).dataset.testid === 'pac-rate-row') break;
                ancestor = ancestor.parentElement;
            }
            return {
                externalTag: root.parentElement?.tagName ?? null,
                ancestorLabels,
                internalLabels: root.getElementsByTagName('label').length,
            };
        });
        expect(rateDateStructure).toEqual({externalTag: 'LABEL', ancestorLabels: 1, internalLabels: 0});

        const entered = await analyzeAndCapture(page);
        expect(entered.parameters.cash_balances).toEqual([{currency: 'USD', amount: '500.000000000001'}]);
        expect(entered.parameters.contributions).toEqual([{currency: 'EUR', amount: '200.000000000001', monetary_step: '0.000000000001'}]);
        expect(entered.parameters.valuation_rates).toEqual([{currency: 'USD', rate_to_report: '0.900000000001', reference_date: REFERENCE_DATE}]);
        const enteredRow = only(entered.parameters.rows ?? [], (row) => row.name === PRIMARY_NAME, 'entered-mode PAC row');
        expect(enteredRow.quote).toMatchObject({currency: 'USD', raw_price: '10', quote_base_quantity: 1000});
        expect(entered.parameters).not.toHaveProperty('solver');
        expect(entered.parameters).not.toHaveProperty('orders');
    });

    test('analyzes ready facts in formatted and exact views, marks edits stale, and renders a real invalid result', async ({page}, testInfo) => {
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

        // A non-positive quote is accepted by the editor as an exact decimal
        // and rejected by the domain contract, yielding a successful platform
        // response whose PAC availability is `invalid`.
        await field(page, 'pac-target-weight', primaryIndex).fill('50');
        await field(page, 'pac-raw-price', primaryIndex).fill('0');
        const invalidResponse = page.waitForResponse((candidate) => isComputeRequest(candidate.request()), {timeout: 30_000});
        await page.getByTestId('pac-analyze').click();
        expect((await invalidResponse).status()).toBe(200);
        await expect(tool).toHaveAttribute('data-busy', 'false', {timeout: 40_000});
        await expect(page.getByTestId('pac-result')).toHaveAttribute('data-state', 'invalid');
        await expect(page.getByTestId('pac-result')).toHaveAttribute('data-view', 'formatted');
        await expect(page.getByTestId('pac-issues')).toBeVisible();
        await expect(page.getByTestId('pac-denominator-note')).toBeVisible();
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
            await expect(page.getByTestId(`pac-instrument-id-${row}`)).toHaveCount(0);
            await expect(page.getByTestId(`pac-custody-context-${row}`)).toHaveCount(0);
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
