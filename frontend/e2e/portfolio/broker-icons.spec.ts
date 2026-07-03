import {expect, test} from '@playwright/test';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

const RECROWD_ICON_DATA_URL = 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><rect width="16" height="16" rx="3" fill="#1a4031"/><text x="8" y="11" text-anchor="middle" font-size="8" fill="#f5f4ef">R</text></svg>');

test.describe('Portfolio broker icons', () => {
    test.beforeEach(async ({page}) => {
        await page.route('**/api/v1/transactions**', async (route) => {
            await route.fulfill({status: 200, contentType: 'application/json', body: '[]'});
        });

        await page.route('**/api/v1/brokers', async (route) => {
            const response = await route.fetch();
            const brokers = (await response.json()) as Array<Record<string, unknown>>;
            const patched = brokers.map((broker) =>
                broker.name === 'Recrowd'
                    ? {
                          ...broker,
                          icon_url: RECROWD_ICON_DATA_URL,
                          portal_url: 'https://www.recrowd.com',
                          default_import_plugin: 'broker_generic_csv',
                      }
                    : broker,
            );
            await route.fulfill({response, json: patched});
        });

        await login(page, TEST_USER);
    });

    test('dashboard positions broker cell uses shared broker icon data instead of falling back to briefcase', async ({page}) => {
        await page.goto('/dashboard');
        await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 15_000});
        await expect(page.getByTestId('positions-panel')).toBeVisible({timeout: 10_000});

        await page.getByTestId('positions-toggle-exposure').click();
        await page.getByTestId('positions-toggle-table').click();
        await page.getByTestId('positions-toggle-open').click();
        await expect(page.getByTestId('exposure-table')).toBeVisible({timeout: 10_000});

        const positionsPanel = page.getByTestId('positions-panel');
        const recrowdCell = positionsPanel.getByRole('button', {name: 'Recrowd'}).first();
        await expect(recrowdCell).toBeVisible({timeout: 10_000});

        const recrowdHtml = await recrowdCell.innerHTML();
        expect(recrowdHtml).toContain('data:image/svg+xml');
        expect(recrowdHtml).not.toContain('lucide-briefcase');
    });
});
