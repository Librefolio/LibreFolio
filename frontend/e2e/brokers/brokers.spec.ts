import {expect, test} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

// Earned parallel: this file's blocks own the data they touch and wait on published
// state, so they share the backend with their neighbours instead of queueing behind
// them. Verified by a green run of the whole category at 4 workers.
test.describe.configure({mode: 'parallel'});

test.describe('Brokers', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test.describe('Broker List Page', () => {
        test('can access brokers page', async ({page}) => {
            await navigateTo(page, '/brokers');
            await expect(page.getByTestId('brokers-page')).toBeVisible();
        });

        test('add broker button is visible', async ({page}) => {
            await navigateTo(page, '/brokers');
            await expect(page.getByTestId('add-broker-button')).toBeVisible();
        });

        test('refresh button is visible', async ({page}) => {
            await navigateTo(page, '/brokers');
            await expect(page.getByTestId('brokers-refresh')).toBeVisible();
        });
    });

    test.describe('Broker CRUD', () => {
        test('can open create broker modal', async ({page}) => {
            await navigateTo(page, '/brokers');
            await page.getByTestId('add-broker-button').click();
            await expect(page.getByTestId('broker-modal')).toBeVisible();
        });

        test('can close broker modal', async ({page}) => {
            await navigateTo(page, '/brokers');
            await page.getByTestId('add-broker-button').click();
            await expect(page.getByTestId('broker-modal')).toBeVisible();

            // Press Escape to close the modal
            await page.keyboard.press('Escape');
            await expect(page.getByTestId('broker-modal')).not.toBeVisible();
        });

        test('create broker with name', async ({page}) => {
            await navigateTo(page, '/brokers');
            await page.getByTestId('add-broker-button').click();
            await expect(page.getByTestId('broker-modal')).toBeVisible();

            // Fill required name field
            const brokerName = `Test Broker ${Date.now()}`;
            await page.getByTestId('broker-name-input').fill(brokerName);

            // Submit form
            await page.getByTestId('broker-form-submit').click();

            // Modal should close and broker should appear in list
            await expect(page.getByTestId('broker-modal')).not.toBeVisible({timeout: 5000});

            // The newly created broker must actually appear in the list.
            // Matching on the unique timestamped name keeps this independent
            // of any brokers already present.
            const newBrokerCard = page.locator('[data-testid^="broker-card-"]').filter({hasText: brokerName});
            await expect(newBrokerCard).toHaveCount(1, {timeout: 5000});
        });

        test('can open edit modal from broker card', async ({page}) => {
            await navigateTo(page, '/brokers');

            // Wait for broker cards to load
            const brokerCards = page.locator('[data-testid^="broker-card-"]');
            const count = await brokerCards.count();

            if (count > 0) {
                // Get the first broker card's id
                const firstCard = brokerCards.first();
                const testId = await firstCard.getAttribute('data-testid');
                const brokerId = testId?.replace('broker-card-', '');

                // Click edit button on first broker
                await page.getByTestId(`broker-edit-${brokerId}`).click();
                await expect(page.getByTestId('broker-modal')).toBeVisible();
            }
        });

        test('can open delete dialog from broker card', async ({page}) => {
            await navigateTo(page, '/brokers');

            // Wait for broker cards to load
            const brokerCards = page.locator('[data-testid^="broker-card-"]');
            const count = await brokerCards.count();

            if (count > 0) {
                // Get the first broker card's id
                const firstCard = brokerCards.first();
                const testId = await firstCard.getAttribute('data-testid');
                const brokerId = testId?.replace('broker-card-', '');

                // Click delete button on first broker
                await page.getByTestId(`broker-delete-${brokerId}`).click();
                await expect(page.getByTestId('delete-broker-dialog')).toBeVisible();

                // Cancel to close dialog
                await page.getByTestId('delete-broker-cancel').click();
                await expect(page.getByTestId('delete-broker-dialog')).not.toBeVisible();
            }
        });

        test('full broker CRUD flow: create, edit, delete', async ({page}) => {
            await navigateTo(page, '/brokers');

            // === CREATE ===
            const brokerName = `CRUD Test Broker ${Date.now()}`;
            await page.getByTestId('add-broker-button').click();
            await expect(page.getByTestId('broker-modal')).toBeVisible();
            await page.getByTestId('broker-name-input').fill(brokerName);
            await page.getByTestId('broker-form-submit').click();
            await expect(page.getByTestId('broker-modal')).not.toBeVisible({timeout: 5000});

            // Find the newly created broker card
            const newBrokerCard = page.locator('[data-testid^="broker-card-"]').filter({hasText: brokerName});
            await expect(newBrokerCard).toBeVisible({timeout: 5000});

            // Get broker ID from card
            const cardTestId = await newBrokerCard.getAttribute('data-testid');
            const brokerId = cardTestId?.replace('broker-card-', '');

            // === EDIT ===
            const editedName = `${brokerName} EDITED`;
            await page.getByTestId(`broker-edit-${brokerId}`).click();
            await expect(page.getByTestId('broker-modal')).toBeVisible();

            // Clear and fill with new name
            await page.getByTestId('broker-name-input').clear();
            await page.getByTestId('broker-name-input').fill(editedName);
            await page.getByTestId('broker-form-submit').click();
            await expect(page.getByTestId('broker-modal')).not.toBeVisible({timeout: 5000});

            // Verify edited name appears
            const editedBrokerCard = page.locator('[data-testid^="broker-card-"]').filter({hasText: editedName});
            await expect(editedBrokerCard).toBeVisible({timeout: 5000});

            // === DELETE ===
            await page.getByTestId(`broker-delete-${brokerId}`).click();
            await expect(page.getByTestId('delete-broker-dialog')).toBeVisible();

            // Confirm delete
            await page.getByTestId('delete-broker-confirm').click();
            await expect(page.getByTestId('delete-broker-dialog')).not.toBeVisible({timeout: 5000});

            // Verify the broker is gone — by the name this test owns, not by its ID.
            // The models declare `INTEGER PRIMARY KEY` with no AUTOINCREMENT, so SQLite
            // recycles the highest rowid: deleting the newest broker frees its ID, and a
            // concurrent create takes it straight back. Asserting "card <id> is absent"
            // then fails on a *different* broker while this one really was deleted.
            await expect(page.locator('[data-testid^="broker-card-"]').filter({hasText: editedName})).toHaveCount(0, {timeout: 5000});
        });
    });
});
