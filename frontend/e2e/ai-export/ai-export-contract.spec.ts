import {expect, test, type Page, type Request} from '../fixtures/playwright';
import {TEST_USER} from '../fixtures/test-users';

import {API_TIMEOUT, UI_TIMEOUT, exportCurrentSelection, gotoDashboard, gotoFirstBroker, gotoFx, gotoSeededAsset, isSnapshotPost, numericScopeId, openAiExportPanel, selectAiExportSelection, setupAiExportPage, waitForClipboard} from './helpers';

const ASSET_OVERVIEW_FIXTURE = {
    displayName: 'Apple Inc.',
    ticker: 'AAPL',
} as const;
const PUBLIC_CONTRACT_VERSION = 1;

interface ExpectedDatasetRequest {
    readonly domain: 'portfolio' | 'broker' | 'asset' | 'fx';
    readonly id: string;
    readonly brokerId?: number;
    readonly assetId?: number;
    readonly baseCurrency?: string;
    readonly quoteCurrency?: string;
}

function expectIsoPeriod(payload: Record<string, unknown>): void {
    const period = payload.period as {start?: unknown; end?: unknown};
    expect(period.start).toEqual(expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/));
    expect(period.end).toEqual(expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/));
    expect(String(period.start) < String(period.end)).toBe(true);
}

// V1 broker scope is optional on portfolio/asset/fx requests. The dashboard surface
// always sends its explicit owned-broker set (beta F2: the export must aggregate the
// same brokers the dashboard shows, never fall back to "every accessible broker"),
// so portfolio payloads from the dashboard carry `broker_ids`. Assert the canonical
// shape the backend enforces (NonEmptyBrokerIds: unique positive ints, min 1,
// ascending) — never the literal IDs, which are shared-DB fixture data.
function expectCanonicalBrokerIds(value: unknown): void {
    expect(Array.isArray(value), 'broker_ids must be an array').toBe(true);
    const ids = value as unknown[];
    expect(ids.length, 'broker_ids must be non-empty').toBeGreaterThan(0);
    for (const id of ids) {
        expect(Number.isInteger(id), 'broker_ids entries must be integers').toBe(true);
        expect(id as number, 'broker_ids entries must be positive').toBeGreaterThan(0);
    }
    expect(ids, 'broker_ids must be sorted ascending').toEqual([...(ids as number[])].sort((left, right) => left - right));
    expect(new Set(ids).size, 'broker_ids must be unique').toBe(ids.length);
}

function expectUppercaseCurrency(value: unknown, field: string): void {
    expect(typeof value, `${field} must be a string`).toBe('string');
    expect(value, `${field} must be uppercase`).toBe(String(value).toUpperCase());
    expect(value, `${field} must contain uppercase letters only`).toEqual(expect.stringMatching(/^[A-Z]+$/));
}

function expectDatasetRequest(payload: Record<string, unknown>, expected: ExpectedDatasetRequest): void {
    expect(payload.domain).toBe(expected.domain);
    expect(payload.selection).toEqual({
        kind: 'dataset',
        id: expected.id,
        version: PUBLIC_CONTRACT_VERSION,
    });
    expect(payload.detail_level).toBe('compact');
    expect(payload.expected_catalog_version).toBe(PUBLIC_CONTRACT_VERSION);
    expectUppercaseCurrency(payload.target_currency, 'target_currency');
    expectIsoPeriod(payload);

    if (expected.domain === 'portfolio') {
        expectCanonicalBrokerIds(payload.broker_ids);
        expect(payload).not.toHaveProperty('broker_id');
        expect(payload).not.toHaveProperty('asset_id');
        expect(payload).not.toHaveProperty('base_currency');
        expect(payload).not.toHaveProperty('quote_currency');
    } else if (expected.domain === 'broker') {
        expect(payload.broker_id).toBe(expected.brokerId);
        expect(payload).not.toHaveProperty('broker_ids');
        expect(payload).not.toHaveProperty('asset_id');
        expect(payload).not.toHaveProperty('base_currency');
        expect(payload).not.toHaveProperty('quote_currency');
    } else if (expected.domain === 'asset') {
        expect(payload.asset_id).toBe(expected.assetId);
        expect(payload).not.toHaveProperty('broker_ids');
        expect(payload).not.toHaveProperty('broker_id');
        expect(payload).not.toHaveProperty('base_currency');
        expect(payload).not.toHaveProperty('quote_currency');
    } else {
        expect(payload.base_currency).toBe(expected.baseCurrency);
        expect(payload.quote_currency).toBe(expected.quoteCurrency);
        expect(payload).not.toHaveProperty('broker_ids');
        expect(payload).not.toHaveProperty('broker_id');
        expect(payload).not.toHaveProperty('asset_id');
    }
}

async function exportDataset(page: Page, id: string): Promise<Record<string, unknown>> {
    await openAiExportPanel(page);
    await selectAiExportSelection(page, 'dataset', id);
    await page.getByTestId('ai-export-detail-compact').click();
    return (await exportCurrentSelection(page)).payload;
}

async function captureDatasetRequest(page: Page, id: string): Promise<Record<string, unknown>> {
    const panel = await openAiExportPanel(page);
    await selectAiExportSelection(page, 'dataset', id);
    await page.getByTestId('ai-export-detail-compact').click();

    const requestPromise = page.waitForRequest(isSnapshotPost, {timeout: 8_000});
    const responsePromise = page.waitForResponse((response) => isSnapshotPost(response.request()), {timeout: API_TIMEOUT});
    await page.getByTestId('ai-export-copy-button').click();
    const [request, response] = await Promise.all([requestPromise, responsePromise]);
    const failureBody = response.status() === 200 ? '' : await response.text();
    expect(response.status(), failureBody).toBe(200);

    if (await panel.menu.isVisible()) {
        await page.keyboard.press('Escape');
        await expect(panel.menu).toBeHidden({timeout: 2_000});
    }
    return request.postDataJSON() as Record<string, unknown>;
}

const BROKER_LIST_PATH = '/api/v1/brokers';
const AI_EXPORT_CATALOG_PATH = '/api/v1/ai-export/catalog';
/**
 * How long a cold load of the Dashboard may take to bring the AI-export catalogue in while the broker list waits at
 * the gate. Kept well below the page's own request timeout (`DEFAULT_TIMEOUT`, 30 s, zodios-client.ts): held past
 * that, the broker list fails inside the page and the Dashboard is left with no scope at all — a different state from
 * the one under test, which would surface as a confusing red further down.
 */
const HELD_LIST_BUDGET_MS = 20_000;

interface BrokerListItem {
    readonly id: number;
    readonly user_role?: string | null;
    readonly user_share_percentage?: string | number | null;
}

function isGetOf(request: Request, path: string): boolean {
    return request.method() === 'GET' && new URL(request.url()).pathname === path;
}

/** The brokers the Dashboard aggregates: OWNER with a share unset or above zero, as `getOwnedBrokers()` keeps them (brokerStore.ts). Ascending. */
function ownedBrokerIds(items: readonly BrokerListItem[] | undefined): number[] {
    return (items ?? [])
        .filter((broker) => broker.user_role === 'OWNER' && (broker.user_share_percentage == null || Number.parseFloat(String(broker.user_share_percentage)) > 0))
        .map((broker) => broker.id)
        .sort((left, right) => left - right);
}

interface BrokerListGate {
    /** How many broker-list requests the page has sent into the gate so far. */
    held(): number;
    /** Lets every held request go on, and every later one straight through. Idempotent. */
    release(): void;
}

/**
 * Holds every `GET /api/v1/brokers` the page sends — the list `ensureBrokersLoaded()` asks for (brokerStore.ts) — until
 * `release()`. The gate delays, it never answers: a held request leaves through `route.fallback()`, so any other route
 * registered on the same URL still gets its turn and the backend answers as usual. Other methods on that path fall back
 * at once, and the pattern stops at the path, so `/brokers/{id}` (icon hydration) and `/brokers/{id}/summary` never
 * enter it. `page.request` does not go through page routes: the owned-set reading goes around the gate.
 */
async function holdBrokerList(page: Page): Promise<BrokerListGate> {
    let release!: () => void;
    const released = new Promise<void>((resolve) => {
        release = resolve;
    });
    let held = 0;
    await page.route(/\/api\/v1\/brokers(?:\?.*)?$/, async (route) => {
        if (!isGetOf(route.request(), BROKER_LIST_PATH)) {
            await route.fallback();
            return;
        }
        held += 1;
        await released;
        // A request the page abandoned meanwhile has nothing left to go on: the test reports the missing answer itself.
        await route.fallback().catch(() => undefined);
    });
    return {held: () => held, release: () => release()};
}

// One test here exports four surfaces in sequence, so the whole-test budget has to
// clear API_TIMEOUT plus three ordinary exports — otherwise a single slow response
// gets reported as "test timeout", which names nothing, instead of "waitForResponse
// timed out", which names the endpoint that stalled.
test.setTimeout(180_000);

// Earned parallel: this file's blocks own the data they touch and wait on published
// state, so they share the backend with their neighbours instead of queueing behind
// them. Verified by a green run of the whole category at 4 workers.
test.describe.configure({mode: 'parallel'});

test.describe('AI Export request and clipboard contract', () => {
    test.beforeEach(async ({context, page}) => {
        await context.grantPermissions(['clipboard-read', 'clipboard-write']);
        await setupAiExportPage(page);
    });

    test('sends V1 Dataset request shape and domain scope across all surfaces', async ({page}) => {
        await test.step('Portfolio Dataset', async () => {
            await gotoDashboard(page);
            const payload = await exportDataset(page, 'portfolio.overview_and_history');
            expectDatasetRequest(payload, {
                domain: 'portfolio',
                id: 'portfolio.overview_and_history',
            });

            await waitForClipboard(page, ['portfolio.overview_and_history'], 'Portfolio Dataset clipboard was not populated');
        });

        await test.step('Broker Dataset', async () => {
            await gotoFirstBroker(page);
            const brokerId = numericScopeId(page, 'brokers');
            const payload = await captureDatasetRequest(page, 'broker.overview_and_history');
            expectDatasetRequest(payload, {
                domain: 'broker',
                id: 'broker.overview_and_history',
                brokerId,
            });
        });

        await test.step('Asset Dataset', async () => {
            await gotoSeededAsset(page, ASSET_OVERVIEW_FIXTURE);
            const assetId = numericScopeId(page, 'assets');
            const payload = await captureDatasetRequest(page, 'asset.position_and_history');
            expectDatasetRequest(payload, {
                domain: 'asset',
                id: 'asset.position_and_history',
                assetId,
            });
        });

        await test.step('FX Dataset', async () => {
            await gotoFx(page, 'EUR-USD');
            const payload = await captureDatasetRequest(page, 'fx.market_and_exposure');
            expectDatasetRequest(payload, {
                domain: 'fx',
                id: 'fx.market_and_exposure',
                baseCurrency: 'EUR',
                quoteCurrency: 'USD',
            });
        });
    });

    test('exports V1 performance-market-drivers analysis contract', async ({page}) => {
        await gotoDashboard(page);
        await openAiExportPanel(page);
        await selectAiExportSelection(page, 'analysis', 'portfolio.performance_market_drivers');
        await page.getByTestId('ai-export-detail-compact').click();

        const notes = 'Review dated drivers, conflicting evidence, and unexplained material moves.';
        await page.getByTestId('ai-export-user-notes').fill(notes);
        const {payload} = await exportCurrentSelection(page);

        expect(payload.domain).toBe('portfolio');
        expect(payload.selection).toEqual({
            kind: 'analysis',
            id: 'portfolio.performance_market_drivers',
            version: PUBLIC_CONTRACT_VERSION,
            instruction_template_id: 'portfolio.performance_market_drivers.instructions',
            instruction_template_version: PUBLIC_CONTRACT_VERSION,
            response_contract_id: 'portfolio.performance_market_drivers.response',
            response_contract_version: PUBLIC_CONTRACT_VERSION,
        });
        expect(payload.detail_level).toBe('compact');
        expect(payload.expected_catalog_version).toBe(PUBLIC_CONTRACT_VERSION);
        expectCanonicalBrokerIds(payload.broker_ids);
        expectUppercaseCurrency(payload.target_currency, 'target_currency');
        expectIsoPeriod(payload);

        await waitForClipboard(page, ['portfolio.performance_market_drivers', notes], 'Performance-market-drivers Analysis clipboard was not populated');
    });

    test('exports capital-loss offset analysis with FIFO and fiscal-input contract', async ({page}) => {
        await gotoDashboard(page);
        await openAiExportPanel(page);
        await selectAiExportSelection(page, 'analysis', 'portfolio.fiscal_lots');
        await page.getByTestId('ai-export-detail-compact').click();

        const notes = 'Prioritize losses expiring first without changing strategic exposures unnecessarily.';
        await page.getByTestId('ai-export-user-notes').fill(notes);
        const {payload} = await exportCurrentSelection(page);

        expect(payload.domain).toBe('portfolio');
        expect(payload.selection).toEqual({
            kind: 'analysis',
            id: 'portfolio.fiscal_lots',
            version: PUBLIC_CONTRACT_VERSION,
            instruction_template_id: 'portfolio.fiscal_lots.instructions',
            instruction_template_version: PUBLIC_CONTRACT_VERSION,
            response_contract_id: 'portfolio.fiscal_lots.response',
            response_contract_version: PUBLIC_CONTRACT_VERSION,
        });
        expect(payload.detail_level).toBe('compact');
        expect(payload.expected_catalog_version).toBe(PUBLIC_CONTRACT_VERSION);
        expectCanonicalBrokerIds(payload.broker_ids);
        expectUppercaseCurrency(payload.target_currency, 'target_currency');
        expectIsoPeriod(payload);

        const clipboard = await waitForClipboard(page, ['portfolio.fiscal_lots', 'dataset_id: portfolio.fifo', notes], 'Capital-loss offset Analysis clipboard was not populated');
        expect(clipboard).toContain('dataset_id: portfolio.fifo');
    });

    /**
     * F2 on the Dashboard's AI Export. On a cold load the owned brokers arrive in `onMount` (`ensureBrokersLoaded()`),
     * the AI-export catalogue in parallel. An export started before the brokers leaves with no `broker_ids`, which the
     * backend widens to every broker the user can see: the clipboard would hold another portfolio than the one on screen.
     * So the trigger may open only once the owned scope is known.
     *
     * The broker list is held at a gate across a cold load. With the catalogue in — the one thing the trigger waits for
     * today — and the scope still unknown, the trigger must be disabled. Nothing on the page publishes "catalogue applied":
     * the catalogue response having finished is the nearest signal there is. Released, the list lands, the trigger opens,
     * and the export carries exactly the owned brokers of the list the page itself received — read off that very response,
     * so a neighbour creating or deleting a broker of this user in the meantime cannot move the expectation.
     */
    test('the Dashboard enables AI Export only once the owned broker scope is known, and the export carries it', async ({page}) => {
        const listed = await page.request.get(BROKER_LIST_PATH);
        expect(listed.ok(), `GET ${BROKER_LIST_PATH} → HTTP ${listed.status()}`).toBe(true);
        const ownedBefore = ownedBrokerIds(((await listed.json()) as {items?: BrokerListItem[]}).items);
        if (ownedBefore.length === 0) throw new Error(`${TEST_USER.username} owns no broker with a share above zero, so the Dashboard has no scope to export. Check populate_mock_data.py seeding.`);

        // A cold load is a new document with every store empty. The login left a live Dashboard behind: it is unloaded
        // first, so that nothing it still has in flight can be held, counted or awaited as the new document's request.
        await page.goto('about:blank');
        const gate = await holdBrokerList(page);
        try {
            const trigger = page.getByTestId('ai-export-button');
            const catalogAnswered = page.waitForResponse((response) => isGetOf(response.request(), AI_EXPORT_CATALOG_PATH), {timeout: HELD_LIST_BUDGET_MS});
            // Awaited below; the empty catch only keeps a failure in between from also surfacing as an unhandled rejection.
            void catalogAnswered.catch(() => undefined);
            await gotoDashboard(page);
            await expect.poll(() => gate.held(), {message: 'the cold load of /dashboard never asked for its broker list: nothing is held, so nothing here is tested', timeout: UI_TIMEOUT}).toBeGreaterThan(0);

            const catalog = await catalogAnswered;
            expect(catalog.status(), catalog.status() === 200 ? '' : await catalog.text()).toBe(200);
            expect(await catalog.finished(), 'the AI-export catalogue never finished loading').toBeNull();
            await expect(trigger).toBeVisible();
            await expect(trigger, 'AI Export is enabled while the owned brokers are still unknown: an export from here leaves without broker_ids, and the backend widens it to every broker the user can see (F2)').toBeDisabled();

            const listAnswered = page.waitForResponse((response) => isGetOf(response.request(), BROKER_LIST_PATH), {timeout: UI_TIMEOUT});
            gate.release();
            const answer = await listAnswered;
            expect(answer.status(), answer.status() === 200 ? '' : await answer.text()).toBe(200);
            const owned = ownedBrokerIds(((await answer.json()) as {items?: BrokerListItem[]}).items);
            expect(owned.length, `the broker list the page received holds no owned broker (owned before the load: [${ownedBefore.join(', ')}]). Check populate_mock_data.py seeding.`).toBeGreaterThan(0);
            await expect(trigger, 'the owned brokers are known, yet AI Export stays disabled').toBeEnabled({timeout: UI_TIMEOUT});

            const payload = await exportDataset(page, 'portfolio.overview_and_history');
            expect(payload.domain).toBe('portfolio');
            expectCanonicalBrokerIds(payload.broker_ids);
            expect(payload.broker_ids, `the export is not scoped to the brokers the user owns in the list the page received (owned before the load: [${ownedBefore.join(', ')}])`).toEqual(owned);
        } finally {
            gate.release();
            await page.unrouteAll({behavior: 'ignoreErrors'});
        }
    });
});
