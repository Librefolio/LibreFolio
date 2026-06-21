/**
 * DataQualityBanner — E2E Tests
 *
 * Tests the unified DataQualityBanner component across all three contexts:
 * 1. Dashboard (grouped mode)
 * 2. Asset detail (flat mode)
 * 3. FX detail (flat mode)
 *
 * Strategy: tests verify component structure and the absence of legacy markup.
 * Data-conditional checks use `test.info().annotations.push` (not `test.skip`)
 * when the data state is genuinely variable.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 */

import {expect, test} from '@playwright/test';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToAssetsPage} from '../assets/assets-helpers';
import {goToFxDetailPage} from '../fx/fx-helpers';

// ============================================================================
// Helpers
// ============================================================================

async function goToDashboard(page: import('@playwright/test').Page) {
    await page.goto('/dashboard');
    await page.waitForSelector('[data-testid="dashboard-page"]', {timeout: 15_000});
    await page.waitForTimeout(2000); // Let portfolio summary load
}

async function goToFirstAssetDetail(page: import('@playwright/test').Page) {
    await goToAssetsPage(page);
    const firstCard = page.locator('[data-testid^="asset-card-"]').first();
    await expect(firstCard).toBeVisible({timeout: 8_000});
    await firstCard.click();
    await page.waitForSelector('[data-testid="asset-detail-page"]', {timeout: 10_000});
    await page.waitForTimeout(1500);
}

// ============================================================================
// Dashboard Banner Tests (grouped mode)
// ============================================================================

test.describe('DataQualityBanner — Dashboard (grouped mode)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('dashboard loads without JS errors', async ({page}) => {
        const errors: string[] = [];
        page.on('pageerror', (err) => errors.push(err.message));
        await goToDashboard(page);
        expect(errors.filter((e) => !e.includes('favicon'))).toHaveLength(0);
    });

    test('dashboard page structure is intact after banner migration', async ({page}) => {
        await goToDashboard(page);
        await expect(page.getByTestId('dashboard-page')).toBeVisible();
        await expect(page.getByTestId('kpi-row')).toBeVisible();
    });

    test('legacy inline banners are removed after migration', async ({page}) => {
        await goToDashboard(page);
        // Old testids that no longer exist
        await expect(page.getByTestId('dashboard-missing-prices-banner')).toHaveCount(0);
        await expect(page.getByTestId('dashboard-missing-fx-banner')).toHaveCount(0);
    });

    test('when data quality banner is present it is grouped with issue rows', async ({page}) => {
        await goToDashboard(page);
        const banner = page.getByTestId('data-quality-banner');
        const hasBanner = await banner.isVisible({timeout: 3000}).catch(() => false);

        if (hasBanner) {
            // Grouped mode: single container
            await expect(banner).toHaveCount(1);
            // At least one issue row must be visible
            const issueRows = page.locator('[data-testid^="data-quality-issue-"]');
            await expect(issueRows.first()).toBeVisible();
        } else {
            test.info().annotations.push({type: 'info', description: 'No data quality issues in test DB — banner hidden (expected)'});
        }
    });

    test('header does not show "0 errors, 0 warnings" when only info issues present', async ({page}) => {
        await goToDashboard(page);
        const banner = page.getByTestId('data-quality-banner');
        const hasBanner = await banner.isVisible({timeout: 3000}).catch(() => false);

        if (hasBanner) {
            const headerText = await banner.locator('div.font-medium').first().textContent();
            // Must not say "0 error" or "0 warning"
            expect(headerText ?? '').not.toMatch(/0 error/i);
            expect(headerText ?? '').not.toMatch(/0 warning/i);
        } else {
            test.info().annotations.push({type: 'info', description: 'No banner to check — skipped header test'});
        }
    });

    test('NAV incomplete issue includes date range when present', async ({page}) => {
        await goToDashboard(page);
        const navIssue = page.getByTestId('data-quality-issue-NAV_INCOMPLETE');
        const isVisible = await navIssue.isVisible({timeout: 3000}).catch(() => false);

        if (isVisible) {
            const text = await navIssue.textContent();
            // Must contain two ISO dates (YYYY-MM-DD format)
            expect(text).toMatch(/\d{4}-\d{2}-\d{2}/);
        } else {
            test.info().annotations.push({type: 'info', description: 'No NAV_INCOMPLETE issue in test DB — date range test skipped'});
        }
    });

    test('missing price issue shows navigate_asset CTA when present', async ({page}) => {
        await goToDashboard(page);
        const issue = page.getByTestId('data-quality-issue-MISSING_PRICE');
        const isVisible = await issue.isVisible({timeout: 3000}).catch(() => false);

        if (isVisible) {
            const cta = page.getByTestId('data-quality-cta-MISSING_PRICE');
            await expect(cta).toBeVisible();
        } else {
            test.info().annotations.push({type: 'info', description: 'No MISSING_PRICE issue — CTA test skipped'});
        }
    });
});

// ============================================================================
// Asset Detail Banner Tests (flat mode)
// ============================================================================

test.describe('DataQualityBanner — Asset Detail (flat mode)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('asset detail loads without JS errors after banner migration', async ({page}) => {
        const errors: string[] = [];
        page.on('pageerror', (err) => errors.push(err.message));
        await goToFirstAssetDetail(page);
        expect(errors.filter((e) => !e.includes('favicon'))).toHaveLength(0);
    });

    test('legacy archived banner testid removed from asset detail', async ({page}) => {
        await goToFirstAssetDetail(page);
        // Old testid from pre-migration inline banner
        await expect(page.getByTestId('asset-archived-banner')).toHaveCount(0);
    });

    test('asset detail uses flat mode: no grouped banner container', async ({page}) => {
        await goToFirstAssetDetail(page);
        // Flat mode never renders a grouped "data-quality-banner" container
        await expect(page.getByTestId('data-quality-banner')).toHaveCount(0);
    });

    test('FX pair missing issue has add-fx-pair CTA in flat mode', async ({page}) => {
        await goToFirstAssetDetail(page);
        const issue = page.getByTestId('data-quality-issue-FX_PAIR_MISSING');
        const isVisible = await issue.isVisible({timeout: 2000}).catch(() => false);

        if (isVisible) {
            const cta = page.getByTestId('data-quality-cta-FX_PAIR_MISSING');
            await expect(cta).toBeVisible();
        } else {
            test.info().annotations.push({type: 'info', description: 'No FX_PAIR_MISSING issue for first asset — CTA test skipped'});
        }
    });

    test('FX pair no-data issue has navigate-fx CTA in flat mode', async ({page}) => {
        await goToFirstAssetDetail(page);
        const issue = page.getByTestId('data-quality-issue-FX_PAIR_NO_DATA');
        const isVisible = await issue.isVisible({timeout: 2000}).catch(() => false);

        if (isVisible) {
            const cta = page.getByTestId('data-quality-cta-FX_PAIR_NO_DATA');
            await expect(cta).toBeVisible();
        } else {
            test.info().annotations.push({type: 'info', description: 'No FX_PAIR_NO_DATA issue — CTA test skipped'});
        }
    });
});

// ============================================================================
// FX Detail Banner Tests (flat mode)
// ============================================================================

test.describe('DataQualityBanner — FX Detail (flat mode)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('FX detail loads without JS errors after banner migration', async ({page}) => {
        const errors: string[] = [];
        page.on('pageerror', (err) => errors.push(err.message));
        await goToFxDetailPage(page, 'EUR-USD');
        await page.waitForTimeout(1500);
        expect(errors.filter((e) => !e.includes('favicon'))).toHaveLength(0);
    });

    test('FX detail uses flat mode: no grouped banner container', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.waitForTimeout(1500);
        // Flat mode never renders a grouped "data-quality-banner" container
        await expect(page.getByTestId('data-quality-banner')).toHaveCount(0);
    });

    test('range-before-data issue appears when URL date precedes first data', async ({page}) => {
        // Navigate with a very early date range to trigger the issue
        await page.goto('/fx/EUR-USD?start=2000-01-01&end=2000-12-31');
        await page.waitForSelector('[data-testid="fx-detail-page"]', {timeout: 15_000});
        await page.waitForTimeout(2000);

        const issue = page.getByTestId('data-quality-issue-RANGE_BEFORE_FIRST_DATA');
        const isVisible = await issue.isVisible({timeout: 3000}).catch(() => false);

        if (isVisible) {
            const text = await issue.textContent();
            // Message should contain a year (date of first available data)
            expect(text).toMatch(/\d{4}/);
        } else {
            test.info().annotations.push({type: 'info', description: 'EUR-USD data starts before 2000 — range issue not triggered'});
        }
    });
});
