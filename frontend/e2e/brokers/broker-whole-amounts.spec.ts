import {expect, test, type Page, type Request} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

/**
 * The broker's page shows the whole broker, not the owner's share of it (MF6-3, D4; Y6-7).
 *
 * `e2e_test_user` owns 30 % of the first mock broker. The Dashboard counts the user's share of every broker, so a deposit
 * of 1 000 there is 300; the broker's own page shows the broker, and its Transactions tab lists the whole 1 000. Before,
 * the Patrimonio of that page was the share while the Transactions were whole: «modifica e visualizzazione non tornano».
 *
 * The page asks `apply_ownership_share: false`; the Dashboard never does. The number is read from the answer the page
 * received, not from a formatted cell, and compared with the same question asked directly with the flag on and off.
 *
 * The Risk tab follows the page (`wholeBroker` on the risk panels, J's prop): on the broker page its portfolio scope carries
 * `apply_ownership_share: false`, so the stress impacts and the scope value match the net worth printed above; on the
 * Dashboard the scope is what it always was: the share stays on (the schema default).
 */

type BrokerListItem = {id: number; name: string; user_role?: string | null; user_share_percentage?: string | number | null};
type ReportBody = {broker_ids?: number[]; apply_ownership_share?: boolean; include_summary?: boolean; include_history?: boolean};
type RiskBody = {scope?: {kind?: string; broker_ids?: number[]; apply_ownership_share?: boolean}};
type ReportAnswer = {summary?: {net_worth?: {amount: string | number}} | null};

async function postReport(page: Page, body: Record<string, unknown>): Promise<ReportAnswer> {
    const response = await page.request.post('/api/v1/portfolio/report', {data: {include_summary: true, include_history: false, include_allocation_history: false, include_breakdown: false, include_positions_contribution: false, ...body}});
    expect(response.ok(), `POST /portfolio/report → HTTP ${response.status()}`).toBe(true);
    return (await response.json()) as ReportAnswer;
}

/** A risk query on a portfolio scope — the asset and asset-set ones belong to other panels. */
function isPortfolioRiskQuery(request: Request): boolean {
    if (request.method() !== 'POST' || new URL(request.url()).pathname !== '/api/v1/risk/query') return false;
    return (request.postDataJSON() as RiskBody).scope?.kind === 'portfolio';
}

const netWorth = (answer: ReportAnswer): number => Number(answer.summary?.net_worth?.amount ?? 0);

/**
 * A broker TEST_USER owns with less than the whole, and whose net worth the share changes: scanned, not assumed (the
 * share is what the precondition needs, and a neighbour spec may have changed a broker).
 */
async function findScaledBroker(page: Page): Promise<{broker: BrokerListItem; whole: number; scaled: number}> {
    const response = await page.request.get('/api/v1/brokers');
    expect(response.ok(), 'GET /brokers').toBe(true);
    const items = ((await response.json()) as {items: BrokerListItem[]}).items;
    const owned = items.filter((broker) => broker.user_role === 'OWNER' && Number(broker.user_share_percentage ?? 1) > 0 && Number(broker.user_share_percentage ?? 1) < 1);
    for (const broker of owned) {
        const scaled = netWorth(await postReport(page, {broker_ids: [broker.id]}));
        const whole = netWorth(await postReport(page, {broker_ids: [broker.id], apply_ownership_share: false}));
        if (whole > 0 && Math.abs(whole - scaled) > 0.005) return {broker, whole, scaled};
    }
    throw new Error('e2e_test_user owns no broker with a share below 100 % and a net worth: check the first broker of populate_mock_data.py (OWNER, 30 %)');
}

test.describe('Broker page — the whole broker, not the owner’s share', () => {
    test('the report the broker page asks counts the brokers whole, and its answer is the unscaled one', async ({page}) => {
        test.setTimeout(90_000);
        await login(page, TEST_USER);
        const {broker, whole, scaled} = await findScaledBroker(page);
        expect(whole, 'the share changes the net worth, or the case proves nothing').toBeGreaterThan(scaled);

        const reportAnswered = page.waitForResponse((response) => {
            if (!response.url().endsWith('/api/v1/portfolio/report') || response.request().method() !== 'POST') return false;
            const body = response.request().postDataJSON() as ReportBody;
            return body.include_summary === true && body.include_history !== false && body.broker_ids?.length === 1 && body.broker_ids[0] === broker.id;
        });
        await navigateTo(page, `/brokers/${broker.id}`);
        const response = await reportAnswered;
        expect((response.request().postDataJSON() as ReportBody).apply_ownership_share, 'the broker page counts the broker whole').toBe(false);
        const shown = netWorth((await response.json()) as ReportAnswer);
        expect(shown).toBeCloseTo(whole, 2);
        expect(shown).not.toBeCloseTo(scaled, 2);
    });

    test('the Dashboard keeps the owner’s share: it never asks for the whole broker', async ({page}) => {
        test.setTimeout(90_000);
        await login(page, TEST_USER);
        const asked = page.waitForRequest((request) => request.url().endsWith('/api/v1/portfolio/report') && request.method() === 'POST' && (request.postDataJSON() as ReportBody).include_history !== false, {timeout: 30_000});
        await navigateTo(page, '/dashboard');
        const body = (await asked).postDataJSON() as ReportBody;
        expect(body.apply_ownership_share, 'the Dashboard sends no whole-broker flag: the user’s share is what it shows').toBeUndefined();
    });

    test('the Risk tab of the broker page asks its scope whole', async ({page}) => {
        test.setTimeout(120_000);
        await login(page, TEST_USER);
        const {broker} = await findScaledBroker(page);

        const brokerRiskAsked = page.waitForRequest((request) => isPortfolioRiskQuery(request), {timeout: 45_000});
        await navigateTo(page, `/brokers/${broker.id}?tab=rischio`);
        await expect(page.getByTestId('broker-risk-tab')).toBeVisible({timeout: 30_000});
        const brokerScope = ((await brokerRiskAsked).postDataJSON() as RiskBody).scope;
        expect(brokerScope?.broker_ids, 'the risk scope of the broker page is this broker').toEqual([broker.id]);
        expect(brokerScope?.apply_ownership_share, 'the broker page asks its risk with the brokers whole').toBe(false);
    });

    test('the Risk tab of the Dashboard never asks for the whole broker', async ({page}) => {
        test.setTimeout(120_000);
        await login(page, TEST_USER);
        const dashboardRiskAsked = page.waitForRequest((request) => isPortfolioRiskQuery(request), {timeout: 45_000});
        await navigateTo(page, '/dashboard?tab=rischio');
        await expect(page.getByTestId('dashboard-risk-tab')).toBeVisible({timeout: 30_000});
        const dashboardScope = ((await dashboardRiskAsked).postDataJSON() as RiskBody).scope;
        expect(dashboardScope?.kind).toBe('portfolio');
        // The API client fills the schema default (`true`) in; what matters is that the Dashboard never turns the share off.
        expect(dashboardScope?.apply_ownership_share, 'the Dashboard risk scope keeps the owner’s share').not.toBe(false);
    });
});
