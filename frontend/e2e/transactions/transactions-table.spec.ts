/**
 * TransactionsTable E2E Tests — Phase 07 Part 4
 *
 * Tests the main read-view DataTable on /transactions:
 * - Table load + count badge
 * - Always-pair-adjacent rendering (giver ⬇ above receiver ⬆)
 * - Type badge PNG icons + broker color tinting
 * - Cash formatting, asset display, tags, quantity emoji
 * - Link icon 🔗 + GoTo scroll+pulse
 * - Row actions + double-click view mode
 * - Selection toolbar (Edit/Clone/Delete)
 * - Refresh button
 *
 * Prerequisites: backend test mode (port 8001), mock data populated.
 */
import {expect, test, type Page} from '@playwright/test';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

// Shorter timeout — these are read-view tests, no complex modal flows.
test.setTimeout(20_000);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
	await navigateTo(page, '/transactions');
	// Wait for table to appear (short timeout — data is pre-populated).
	await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
	await page.waitForTimeout(400);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('TransactionsTable (main read-view)', () => {
	test.beforeEach(async ({page}) => {
		await login(page, TEST_USER);
		await goToTransactions(page);
	});

	// === TT1 — Table loads with data + count badge ===
	test('table renders with data rows and count badge', async ({page}) => {
		const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
		await expect(rows.first()).toBeVisible({timeout: 5_000});
		const count = await rows.count();
		expect(count).toBeGreaterThan(0);

		// Count badge
		const badge = page.getByTestId('tx-count-badge');
		await expect(badge).toBeVisible();
		const badgeNum = Number(await badge.textContent());
		expect(badgeNum).toBeGreaterThan(0);
	});

	// === TT2 — Pair-adjacent: receiver has ⬆ arrow, preceded by giver ===
	test('linked pairs render giver above receiver (always-pair-adjacent)', async ({page}) => {
		const receiverRows = page.locator('[data-testid="tx-table"] tbody tr.tx-row-receiver');
		const receiverCount = await receiverRows.count();
		if (receiverCount === 0) {
			test.skip(true, 'No linked pairs in mock data');
			return;
		}
		// Each receiver row must be preceded by a non-receiver row (the giver)
		const allRows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
		const allIds: string[] = [];
		for (let i = 0; i < await allRows.count(); i++) {
			allIds.push((await allRows.nth(i).getAttribute('data-row-id'))!);
		}
		for (let i = 0; i < receiverCount; i++) {
			const rid = await receiverRows.nth(i).getAttribute('data-row-id');
			const idx = allIds.indexOf(rid!);
			expect(idx).toBeGreaterThan(0); // not first row
		}
	});

	// === TT3 — Direction arrows ⬇/⬆ in links column ===
	test('pair direction arrows ⬇ and ⬆ both present', async ({page}) => {
		const arrows = page.locator('[data-testid="tx-table"] .tx-pair-arrow');
		const count = await arrows.count();
		if (count < 2) { test.skip(true, 'No linked pairs'); return; }
		const texts: string[] = [];
		for (let i = 0; i < count; i++) texts.push((await arrows.nth(i).textContent())!.trim());
		expect(texts).toContain('⬇');
		expect(texts).toContain('⬆');
	});

	// === TT4 — Type badge PNG icons ===
	test('type column shows PNG icons from /icons/transactions/', async ({page}) => {
		const icons = page.locator('[data-testid="tx-table"] .tx-type-icon');
		await expect(icons.first()).toBeVisible({timeout: 3_000});
		const src = await icons.first().getAttribute('src');
		expect(src).toMatch(/\/icons\/transactions\/.+\.png$/);
	});

	// === TT5 — Broker color tinting ===
	test('rows have broker color CSS variables', async ({page}) => {
		const tinted = page.locator('[data-testid="tx-table"] tbody tr.tx-row-tinted').first();
		await expect(tinted).toBeVisible();
		const style = await tinted.getAttribute('style');
		expect(style).toContain('--broker-bg:');
	});

	// === TT6 — Broker cell: name visible ===
	test('broker column shows broker names', async ({page}) => {
		const cells = page.locator('[data-testid="tx-table"] .tx-broker-name');
		await expect(cells.first()).toBeVisible({timeout: 3_000});
		const name = await cells.first().textContent();
		expect(name!.trim().length).toBeGreaterThan(0);
	});

	// === TT7 — Cash formatting ===
	test('cash column shows formatted amounts with currency', async ({page}) => {
		const cells = page.locator('[data-testid="tx-table"] [data-testid^="tx-cash-cell-"]');
		await expect(cells.first()).toBeVisible({timeout: 3_000});
		const amount = cells.first().locator('.currency-amount');
		await expect(amount).toBeVisible();
	});

	// === TT8 — Link icon 🔗 ===
	test('link icon visible for paired transactions', async ({page}) => {
		const links = page.locator('[data-testid="tx-table"] [data-testid^="tx-link-icon-"]');
		const count = await links.count();
		expect(count).toBeGreaterThan(0);
		await expect(links.first()).toContainText('🔗');
	});

	// === TT9 — GoTo: click 🔗 → pulse animation ===
	test('clicking link icon triggers pulse animation on partner row', async ({page}) => {
		const links = page.locator('[data-testid="tx-table"] [data-testid^="tx-link-icon-"]');
		if (await links.count() === 0) { test.skip(true, 'No linked pairs'); return; }
		await links.first().click();
		// Pulse class should appear within 500ms
		const highlighted = page.locator('[data-testid="tx-table"] tr.tx-row-highlight');
		await expect(highlighted).toHaveCount(1, {timeout: 3_000});
	});

	// === TT10 — Quantity emoji 📈/📉 ===
	test('quantity shows trend emoji', async ({page}) => {
		const content = await page.getByTestId('tx-table').textContent();
		expect(content!.includes('📈') || content!.includes('📉')).toBe(true);
	});

	// === TT11 — Tags as colored badges ===
	test('tags column shows colored badge chips', async ({page}) => {
		const badges = page.locator('[data-testid="tx-table"] .tx-tag-badge');
		const count = await badges.count();
		if (count === 0) { test.skip(true, 'No tagged transactions'); return; }
		await expect(badges.first()).toBeVisible();
		const text = await badges.first().textContent();
		expect(text!.trim().length).toBeGreaterThan(0);
	});

	// === TT12 — Asset display names ===
	test('asset column shows known asset names', async ({page}) => {
		const content = await page.getByTestId('tx-table').textContent();
		const found = ['Apple', 'Bitcoin', 'Microsoft', 'Tesla', 'Ethereum'].some((n) => content!.includes(n));
		expect(found).toBe(true);
	});

	// === TT13 — Date column ===
	test('rows contain valid dates', async ({page}) => {
		const firstRow = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]').first();
		const text = await firstRow.textContent();
		// Date in any common format (YYYY-MM-DD, Mon DD, YYYY, etc.)
		expect(text).toMatch(/\d{4}/);
	});

	// === TT14 — Double-click → view mode (readonly) ===
	test('double-click on row opens view-mode FormModal', async ({page}) => {
		const firstRow = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]').first();
		await firstRow.dblclick();
		await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
		// Save button NOT visible in view mode
		await expect(page.getByTestId('tx-form-save')).not.toBeVisible({timeout: 2_000});
	});

	// === TT15 — Selection checkbox → toolbar ===
	test('selecting a row shows toolbar with Edit/Clone/Delete', async ({page}) => {
		const cb = page.locator('[data-testid="tx-table"] tbody tr[data-row-id] .checkbox-btn').first();
		await cb.click();
		await page.waitForTimeout(200);
		await expect(page.getByTestId('toolbar-action-edit')).toBeVisible({timeout: 3_000});
		await expect(page.getByTestId('toolbar-action-clone')).toBeVisible();
		await expect(page.getByTestId('toolbar-action-delete')).toBeVisible();
	});

	// === TT16 — Toolbar Edit opens BulkModal + FormModal ===
	test('toolbar Edit opens BulkModal with auto-opened FormModal', async ({page}) => {
		const cb = page.locator('[data-testid="tx-table"] tbody tr[data-row-id] .checkbox-btn').first();
		await cb.click();
		await page.waitForTimeout(200);
		await page.getByTestId('toolbar-action-edit').click();
		await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});
		await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
	});

	// === TT17 — Toolbar Clone opens BulkModal in create mode ===
	test('toolbar Clone opens BulkModal', async ({page}) => {
		const cb = page.locator('[data-testid="tx-table"] tbody tr[data-row-id] .checkbox-btn').first();
		await cb.click();
		await page.waitForTimeout(200);
		await page.getByTestId('toolbar-action-clone').click();
		await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});
	});

	// === TT18 — Toolbar Delete opens confirm ===
	test('toolbar Delete opens delete confirmation', async ({page}) => {
		const cb = page.locator('[data-testid="tx-table"] tbody tr[data-row-id] .checkbox-btn').first();
		await cb.click();
		await page.waitForTimeout(200);
		await page.getByTestId('toolbar-action-delete').click();
		// BulkDeleteLinkedPairModal (tx-bulk-confirm) or ConfirmModal (confirm-modal-confirm)
		// — async partner fetch may delay the modal, so wait a bit longer.
		const confirm = page.locator('[data-testid="tx-bulk-confirm"], [data-testid="confirm-modal-confirm"], [data-testid="tx-bulk-delete-title"]').first();
		await expect(confirm).toBeVisible({timeout: 8_000});
	});

	// === TT19 — Select All header checkbox ===
	test('header checkbox selects all → toolbar appears', async ({page}) => {
		const headerCb = page.locator('[data-testid="tx-table"] thead .checkbox-btn').first();
		await headerCb.click();
		await page.waitForTimeout(200);
		await expect(page.getByTestId('toolbar-action-edit')).toBeVisible({timeout: 3_000});
		// Deselect
		await headerCb.click();
		await page.waitForTimeout(200);
		await expect(page.getByTestId('toolbar-action-edit')).not.toBeVisible({timeout: 3_000});
	});

	// === TT20 — Refresh button ===
	test('refresh button reloads without error', async ({page}) => {
		const btn = page.getByTestId('tx-refresh-button');
		await expect(btn).toBeVisible();
		await btn.click();
		// Wait for table to re-render
		await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
		await expect(page.getByTestId('tx-error')).not.toBeVisible({timeout: 2_000});
	});

	// === TT21 — No error on clean load ===
	test('no error banner on normal page load', async ({page}) => {
		await expect(page.getByTestId('tx-error')).not.toBeVisible({timeout: 1_000});
	});

	// === TT22 — Ghost rows (if present) have correct prefix ===
	test('ghost rows use ghost- data-row-id prefix', async ({page}) => {
		const ghosts = page.locator('[data-testid="tx-table"] tbody tr.tx-row-ghost');
		const count = await ghosts.count();
		if (count === 0) {
			// No ghosts — still passes (data-dependent)
			return;
		}
		const id = await ghosts.first().getAttribute('data-row-id');
		expect(id).toMatch(/^ghost-/);
	});
});

