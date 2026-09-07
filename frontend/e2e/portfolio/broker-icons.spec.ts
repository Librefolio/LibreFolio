import {expect, test} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

// The icon this spec patches onto the broker under test. The data URL makes the
// assertion source-independent: the cell can only contain it if it read the
// patched broker payload (icon_url wins the icon chain over portal favicon and
// plugin icon), never from a real network fetch or a cached asset file.
const IBKR_ICON_DATA_URL = 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><rect width="16" height="16" rx="3" fill="#0d2f6e"/><text x="8" y="11" text-anchor="middle" font-size="7" fill="#f5f4ef">IB</text></svg>');

// Earned parallel: this file's blocks own the data they touch (the route
// interceptions live inside each test's own browser context) and wait on
// published state, so they share the backend with their neighbours instead of
// queueing behind them. Verified by a green run of the whole category at 4
// workers.
test.describe.configure({mode: 'parallel'});

test.describe('Portfolio broker icons', () => {
    test.beforeEach(async ({page}) => {
        await page.route('**/api/v1/transactions**', async (route) => {
            await route.fulfill({status: 200, contentType: 'application/json', body: '[]'});
        });

        // Patch an explicit icon onto the broker the test then looks for. The broker
        // must be one e2e_test_user OWNS with share > 0: since F2 the dashboard
        // aggregates owned brokers only, so the pre-F2 choice (Recrowd, EDITOR-only
        // for this user) no longer renders any position there. 'Interactive
        // Brokers' is brokers[0] of the mock data — OWNER 30% for e2e_test_user,
        // with open AAPL/MSFT positions — so its rows are in scope.
        await page.route(/\/api\/v1\/brokers(\?.*)?$/, async (route) => {
            const response = await route.fetch();
            const brokers = (await response.json()) as {items: Array<Record<string, unknown>>; inaccessible?: unknown[]};
            const patchedItems = brokers.items.map((broker) =>
                broker.name === 'Interactive Brokers'
                    ? {
                          ...broker,
                          icon_url: IBKR_ICON_DATA_URL,
                          portal_url: 'https://www.interactivebrokers.com',
                          default_import_plugin: 'broker_generic_csv',
                      }
                    : broker,
            );
            await route.fulfill({response, json: {...brokers, items: patchedItems}});
        });

        await login(page, TEST_USER);
    });

    test('dashboard positions broker cell uses shared broker icon data instead of falling back to briefcase', async ({page}) => {
        await page.goto('/dashboard');
        await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 15_000});

        // positions-panel lives on the "Posizioni" tab, not the default "Panoramica" one.
        await page.getByTestId('dashboard-tab-posizioni').click();
        await expect(page.getByTestId('positions-panel')).toBeVisible({timeout: 10_000});

        await page.getByTestId('positions-toggle-holdings').click();
        await page.getByTestId('positions-toggle-table').click();

        // The panel renders skeletons until the portfolio report lands, and that report
        // costs real work (FIFO at runtime) so under a loaded backend it takes far longer
        // than the assertion below would allow. Wait for the panel's own busy flag rather
        // than picking a bigger number.
        await expect(page.getByTestId('positions-panel')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
        await expect(page.getByTestId('exposure-table')).toBeVisible({timeout: 10_000});

        // Any IB row's broker cell works: they all render the same BrokerBadge for
        // the same broker, and the name filter (not a position) is what picks them.
        const positionsPanel = page.getByTestId('positions-panel');
        const ibkrCell = positionsPanel.getByRole('button', {name: 'Interactive Brokers'}).first();
        await expect(ibkrCell).toBeVisible({timeout: 10_000});

        const ibkrHtml = await ibkrCell.innerHTML();
        expect(ibkrHtml).toContain('data:image/svg+xml');
        expect(ibkrHtml).not.toContain('lucide-briefcase');
    });
});
