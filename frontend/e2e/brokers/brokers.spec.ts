import {expect, test as base, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {eventSeq, waitForEvent, waitForSettled} from '../fixtures/app-events';
import {deleteDisposableUser, registerDisposableUser, skipDueFlowsExcept, type DisposableUser} from '../fixtures/onboarding-accounts';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';

/** A disposable account, and the ids of the brokers it created that are still the teardown's to delete. */
type DisposableOwner = {user: DisposableUser; brokerIds: number[]};

/**
 * The tests that create brokers do it as an account of their own.
 *
 * A broker `TEST_USER` creates is listed by every later spec that reads `TEST_USER`'s brokers, for the rest of the
 * run. So `owner` registers a disposable account and signs the page in past onboarding: every guide is skipped over
 * the API, for this account only, so none takes over the broker page. The teardown runs after a red or a timeout too.
 * It deletes by id the brokers the test recorded, then the account. Deleting the account also deletes every broker it
 * was the last owner of, so a broker whose id the test never got to record does not survive either.
 */
const test = base.extend<{owner: DisposableOwner}>({
    owner: async ({page, request}, use) => {
        const user = await registerDisposableUser(request, 'brokers');
        const owner: DisposableOwner = {user, brokerIds: []};
        try {
            await login(page, user);
            await skipDueFlowsExcept(page, []);
            await use(owner);
        } finally {
            await deleteDisposableUser(request, user, owner.brokerIds);
        }
    },
});

/**
 * The broker the modal has just created, named by its `broker.created` event, recorded for the teardown. `since` is
 * the event counter read before the submit: the ring is retained, so reading it once the modal has closed misses nothing.
 */
async function recordCreatedBroker(page: Page, owner: DisposableOwner, since: number): Promise<number> {
    const created = await waitForEvent(page, 'broker.created', {since});
    const brokerId = created.detail?.brokerId;
    if (typeof brokerId !== 'number') throw new Error(`broker.created carries no broker id: ${JSON.stringify(created.detail)}`);
    owner.brokerIds.push(brokerId);
    return brokerId;
}

/** The broker `TEST_USER` owns in the seed (backend/test_scripts/test_db/populate_mock_data.py, populate_brokers). */
const SEEDED_OWNED_BROKER = 'Interactive Brokers';

/**
 * Open the broker list, wait for the card of `SEEDED_OWNED_BROKER`, and return that broker's id.
 *
 * The read-only card tests act on this card, by id. "The first card" is whichever broker sorts first at that moment,
 * possibly a neighbour's that is about to be deleted. And a card count read once can come back 0 while the list is
 * still loading, and the tests then passed without opening anything.
 */
async function openSeededOwnedCard(page: Page): Promise<number> {
    const response = await page.request.get('/api/v1/brokers');
    expect(response.ok(), `list ${TEST_USER.username}'s brokers: HTTP ${response.status()}`).toBe(true);
    const {items} = (await response.json()) as {items: Array<{id: number; name: string}>};
    const broker = items.find((item) => item.name === SEEDED_OWNED_BROKER);
    if (!broker) throw new Error(`"${SEEDED_OWNED_BROKER}" is not among ${TEST_USER.username}'s brokers: it is seeded by backend/test_scripts/test_db/populate_mock_data.py (populate_brokers)`);
    await navigateTo(page, '/brokers');
    await waitForSettled(page.getByTestId('brokers-page'));
    await expect(page.getByTestId(`broker-card-${broker.id}`)).toBeVisible();
    return broker.id;
}

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

        test('can open edit modal from broker card', async ({page}) => {
            const brokerId = await openSeededOwnedCard(page);

            // Click edit button on the card
            await page.getByTestId(`broker-edit-${brokerId}`).click();
            await expect(page.getByTestId('broker-modal')).toBeVisible();
        });

        test('can open delete dialog from broker card', async ({page}) => {
            const brokerId = await openSeededOwnedCard(page);

            // Click delete button on the card
            await page.getByTestId(`broker-delete-${brokerId}`).click();
            await expect(page.getByTestId('delete-broker-dialog')).toBeVisible();

            // Cancel to close dialog: the seeded broker stays
            await page.getByTestId('delete-broker-cancel').click();
            await expect(page.getByTestId('delete-broker-dialog')).not.toBeVisible();
        });
    });
});

test.describe('Broker CRUD on a disposable account', () => {
    // The account's registration, two sign-ins (the browser's, then the teardown's) and the flow share the budget.
    test.setTimeout(60_000);

    test('create broker with name', async ({page, owner}) => {
        await navigateTo(page, '/brokers');
        await page.getByTestId('add-broker-button').click();
        await expect(page.getByTestId('broker-modal')).toBeVisible();

        // Fill required name field. Broker names are unique across the instance: the suffix mixes time, worker and chance.
        const brokerName = `Test Broker ${uniqueSuffix()}`;
        await page.getByTestId('broker-name-input').fill(brokerName);

        // Submit form
        const since = await eventSeq(page);
        await page.getByTestId('broker-form-submit').click();

        // Modal should close and broker should appear in list
        await expect(page.getByTestId('broker-modal')).not.toBeVisible({timeout: 5000});
        const brokerId = await recordCreatedBroker(page, owner, since);

        // The newly created broker must actually appear in the list.
        // Matching on the unique name keeps this independent
        // of any brokers already present.
        const newBrokerCard = page.locator('[data-testid^="broker-card-"]').filter({hasText: brokerName});
        await expect(newBrokerCard).toHaveCount(1, {timeout: 5000});
        await expect(newBrokerCard, 'the card is the broker the creation reported').toHaveAttribute('data-testid', `broker-card-${brokerId}`);
    });

    test('full broker CRUD flow: create, edit, delete', async ({page, owner}) => {
        await navigateTo(page, '/brokers');

        // === CREATE ===
        const brokerName = `CRUD Test Broker ${uniqueSuffix()}`;
        await page.getByTestId('add-broker-button').click();
        await expect(page.getByTestId('broker-modal')).toBeVisible();
        await page.getByTestId('broker-name-input').fill(brokerName);
        const createdSince = await eventSeq(page);
        await page.getByTestId('broker-form-submit').click();
        await expect(page.getByTestId('broker-modal')).not.toBeVisible({timeout: 5000});
        const brokerId = await recordCreatedBroker(page, owner, createdSince);

        // Find the newly created broker card: the one the creation reported
        const newBrokerCard = page.locator('[data-testid^="broker-card-"]').filter({hasText: brokerName});
        await expect(newBrokerCard).toBeVisible({timeout: 5000});
        await expect(newBrokerCard).toHaveAttribute('data-testid', `broker-card-${brokerId}`);

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
        const deletedSince = await eventSeq(page);
        await page.getByTestId('delete-broker-confirm').click();
        await expect(page.getByTestId('delete-broker-dialog')).not.toBeVisible({timeout: 5000});
        const deleted = await waitForEvent(page, 'broker.deleted', {since: deletedSince});
        expect(deleted.detail?.brokerId, 'the delete went through for this broker').toBe(brokerId);
        // Gone through the UI, so no longer the teardown's: its id may already name a neighbour's new broker.
        owner.brokerIds.splice(owner.brokerIds.indexOf(brokerId), 1);

        // Verify the broker is gone — by the name this test owns, not by its ID.
        // The models declare `INTEGER PRIMARY KEY` with no AUTOINCREMENT, so SQLite
        // recycles the highest rowid: deleting the newest broker frees its ID, and a
        // concurrent create takes it straight back. Asserting "card <id> is absent"
        // then fails on a *different* broker while this one really was deleted.
        await expect(page.locator('[data-testid^="broker-card-"]').filter({hasText: editedName})).toHaveCount(0, {timeout: 5000});
    });
});
