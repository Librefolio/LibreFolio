import {expect, test, type Page} from '@playwright/test';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

/**
 * Ensure at least one broker exists for the test user.
 * If no broker cards are visible, create one via the UI.
 */
async function ensureBrokerExists(page: Page): Promise<void> {
	await navigateTo(page, '/brokers');
	const brokerCards = page.locator('[data-testid^="broker-card-"]');

	// Wait a moment for cards to render (they load asynchronously)
	await page.waitForTimeout(1000);
	const count = await brokerCards.count();

	if (count === 0) {
		// Create a broker so the detail tests have something to work with
		await page.getByTestId('add-broker-button').click();
		await expect(page.getByTestId('broker-modal')).toBeVisible();
		await page.getByTestId('broker-name-input').fill('E2E Detail Test Broker');
		await page.getByTestId('broker-form-submit').click();
		await expect(page.getByTestId('broker-modal')).not.toBeVisible({timeout: 5000});
		// Wait for the card to appear
		await expect(brokerCards.first()).toBeVisible({timeout: 5000});
	}
}

/**
 * Helper: navigate to the first broker's detail page and wait for data to load.
 * Returns false if no brokers exist (test should be skipped).
 */
async function goToFirstBrokerDetail(page: Page): Promise<boolean> {
	await navigateTo(page, '/brokers');

	const brokerCards = page.locator('[data-testid^="broker-card-"]');
	// Wait for async broker list to load
	await page.waitForTimeout(1000);
	const count = await brokerCards.count();
	if (count === 0) return false;

	await brokerCards.first().click();
	await expect(page).toHaveURL(/\/brokers\/\d+/, {timeout: 5000});
	await expect(page.getByTestId('broker-detail-page')).toBeVisible();
	// Wait for broker data to load (broker-name is inside {#if broker})
	await expect(page.getByTestId('broker-name')).toBeVisible({timeout: 10000});
	return true;
}

test.describe('Broker Detail Page', () => {
	test.beforeEach(async ({page}) => {
		await login(page, TEST_USER);
		await ensureBrokerExists(page);
	});

	test('can navigate to broker detail by clicking card', async ({page}) => {
		await navigateTo(page, '/brokers');

		const brokerCards = page.locator('[data-testid^="broker-card-"]');
		const count = await brokerCards.count();

		if (count > 0) {
			await brokerCards.first().click();
			await expect(page).toHaveURL(/\/brokers\/\d+/);
			await expect(page.getByTestId('broker-detail-page')).toBeVisible();
		}
	});

	test('broker detail page shows broker name', async ({page}) => {
		const ok = await goToFirstBrokerDetail(page);
		if (!ok) return;

		// broker-name is already verified by the helper
		await expect(page.getByTestId('broker-name')).toBeVisible();
	});

	test('broker detail page shows cash balances section', async ({page}) => {
		const ok = await goToFirstBrokerDetail(page);
		if (!ok) return;

		await expect(page.getByTestId('broker-cash-balances')).toBeVisible({timeout: 5000});
	});

	test('broker detail page shows holdings section', async ({page}) => {
		const ok = await goToFirstBrokerDetail(page);
		if (!ok) return;

		await expect(page.getByTestId('broker-holdings')).toBeVisible({timeout: 5000});
	});

	test('broker detail page shows transactions section', async ({page}) => {
		const ok = await goToFirstBrokerDetail(page);
		if (!ok) return;

		await expect(page.getByTestId('broker-transactions')).toBeVisible({timeout: 5000});
	});

	test('broker detail page has import files button', async ({page}) => {
		const ok = await goToFirstBrokerDetail(page);
		if (!ok) return;

		// import-files-button is inside {#if canEdit} — requires OWNER or EDITOR role
		await expect(page.getByTestId('import-files-button')).toBeVisible({timeout: 5000});
	});

	test('broker detail page has edit button', async ({page}) => {
		const ok = await goToFirstBrokerDetail(page);
		if (!ok) return;

		// broker-edit-button is inside {#if canEdit}
		await expect(page.getByTestId('broker-edit-button')).toBeVisible({timeout: 5000});
	});

	test('can open edit modal from detail page', async ({page}) => {
		const ok = await goToFirstBrokerDetail(page);
		if (!ok) return;

		await page.getByTestId('broker-edit-button').click();
		await expect(page.getByTestId('broker-modal')).toBeVisible({timeout: 5000});
	});

	test('can navigate back from detail page', async ({page}) => {
		const ok = await goToFirstBrokerDetail(page);
		if (!ok) return;

		await page.getByTestId('broker-back-button').click();
		await expect(page.getByTestId('brokers-page')).toBeVisible({timeout: 5000});
	});

	test('can open import files modal', async ({page}) => {
		const ok = await goToFirstBrokerDetail(page);
		if (!ok) return;

		await page.getByTestId('import-files-button').click();
		await expect(page.getByTestId('import-files-modal')).toBeVisible({timeout: 5000});
	});

	test('can close import files modal', async ({page}) => {
		const ok = await goToFirstBrokerDetail(page);
		if (!ok) return;

		await page.getByTestId('import-files-button').click();
		await expect(page.getByTestId('import-files-modal')).toBeVisible({timeout: 5000});

		// Close by pressing Escape
		await page.keyboard.press('Escape');
		await expect(page.getByTestId('import-files-modal')).not.toBeVisible({timeout: 3000});
	});
});


