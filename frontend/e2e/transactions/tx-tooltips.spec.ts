/**
 * Transaction Tooltip E2E Tests — Phase 07 Bugfix Round 1
 *
 * Covers:
 * - Bug 8:      Linked pair tooltip shows favicon + bold name + role SVG icon
 * - Enhancement: Tooltip content for all access levels (OWNER/EDITOR/VIEWER/Hidden)
 *
 * Prerequisites: backend test mode (port 8001), mock data populated
 * with asymmetric broker access pairs.
 *
 * Mock data contract: populate_mock_data.py creates Asym-a through Asym-d
 * pairs. If a test fails because expected rows are missing, fix
 * populate_mock_data.py — never skip.
 */
import {expect, test, type Page} from '@playwright/test';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

test.setTimeout(15_000);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 8_000});
    await page.waitForTimeout(400);
}

/** Find a row containing ALL given substrings. Throws if not found. */
async function findRow(page: Page, ...substrings: string[]) {
    const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
    const count = await rows.count();
    for (let i = 0; i < count; i++) {
        const row = rows.nth(i);
        const text = (await row.textContent()) ?? '';
        if (substrings.every((s) => text.includes(s))) {
            return row;
        }
    }
    throw new Error(`Row matching [${substrings.join(', ')}] not found. Check populate_mock_data.py.`);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Transaction Linked Pair Tooltips', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
    });

    // === Bug 8 — Tooltip contains HTML with favicon + bold name + SVG icon ===
    test('paired tooltip shows broker name in bold for OWNER↔EDITOR pair', async ({page}) => {
        // Asym-a: Apple Inc. on IB→Directa (OWNER↔EDITOR=full)
        // findRow matches by textContent — both "Directa" and "Apple" appear in description
        const row = await findRow(page, 'Directa', 'Apple');

        // Find the link icon inside the row and scroll into view
        // The icon is inside a Tooltip wrapper → .tx-links-slot contains the .tx-link-icon button
        const linkIcon = row.locator('.tx-link-icon, .tx-links-slot').first();
        await linkIcon.scrollIntoViewIfNeeded();
        await expect(linkIcon).toBeVisible({timeout: 5_000});

        await linkIcon.hover();
        await page.waitForTimeout(600);

        // Tooltip must appear with HTML content
        const tooltip = page.locator('[data-testid="tooltip-content"]');
        await expect(tooltip).toBeVisible({timeout: 3_000});
        const html = await tooltip.innerHTML();
        expect(html, 'Tooltip should contain <strong> for broker name').toContain('<strong>');
        expect(html, 'Tooltip should contain SVG role icon').toContain('<svg');
    });

    test('paired tooltip for hidden broker shows lock icon', async ({page}) => {
        // Asym-d: IB→HiddenBroker — find a row with "access-test" tag on IB
        // whose tooltip contains "Hidden Admin Broker"
        const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
        const count = await rows.count();
        let foundHiddenTooltip = false;

        for (let i = 0; i < Math.min(count, 20); i++) {
            const row = rows.nth(i);
            const text = (await row.textContent()) ?? '';
            if (!text.includes('access-test')) continue;

            const linkIcon = row.locator('.tx-link-icon, .tx-links-slot').first();
            if (!(await linkIcon.isVisible().catch(() => false))) continue;

            await linkIcon.hover();
            await page.waitForTimeout(500);

            const tooltip = page.locator('[data-testid="tooltip-content"]');
            if (await tooltip.isVisible({timeout: 1_000}).catch(() => false)) {
                const html = await tooltip.innerHTML();
                if (html.includes('Hidden Admin Broker')) {
                    expect(html, 'Hidden broker tooltip should have SVG lock').toContain('<svg');
                    foundHiddenTooltip = true;
                    break;
                }
            }
            // Move mouse away to close tooltip
            await page.mouse.move(0, 0);
            await page.waitForTimeout(200);
        }
        expect(foundHiddenTooltip, 'Should find tooltip with Hidden Admin Broker').toBe(true);
    });
});
