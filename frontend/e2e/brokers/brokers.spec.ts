import type {Route} from '@playwright/test';
import {expect, test as base, type Locator, type Page, type Request} from '../fixtures/playwright';
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

const REPORT_PATH = '/api/v1/portfolio/report';
const BROKERS_PATH = '/api/v1/brokers';
/** A page load, or a round trip to the backend (the report is computed on the spot). A deadline, never a delay. */
const ROUND_TRIP_MS = 30_000;
/** The sign-in, a full page load and a held round trip, with room for one deadline that runs out on a red. */
const REFRESH_TEST_MS = 90_000;

/** What a report asks (`fetchReport`, portfolioStore): the fields read here, and the rest compared whole. */
type ReportBody = Record<string, unknown> & {include_breakdown?: boolean; broker_ids?: number[]};

/** The report of the cards (`loadBrokers`, brokers/+page.svelte): the only report that asks the breakdown by broker. */
function isCardsReport(request: Request): boolean {
    if (request.method() !== 'POST' || new URL(request.url()).pathname !== REPORT_PATH) return false;
    return (request.postDataJSON() as ReportBody | null)?.include_breakdown === true;
}

/** The list of brokers (`refreshAllBrokers`, brokerStore): always asked with the inaccessible ones included. */
function isBrokerList(request: Request): boolean {
    const url = new URL(request.url());
    return request.method() === 'GET' && url.pathname === BROKERS_PATH && url.searchParams.get('include_inaccessible') === 'true';
}

/** What a report asks but its brokers: the rest of the cache key (currency, period, every include flag). */
function questionOf(request: Request): Record<string, unknown> {
    const body: ReportBody = (request.postDataJSON() as ReportBody | null) ?? {};
    const question = {...body};
    delete question.broker_ids;
    return question;
}

/** The brokers a report asks about, in id order. */
function brokersOf(request: Request): number[] {
    return [...((request.postDataJSON() as ReportBody | null)?.broker_ids ?? [])].sort((a, b) => a - b);
}

/** Reports the test holds, and owns until it lets them through. */
interface ReportHold {
    /** Every report held so far, in arrival order. */
    readonly held: Request[];
    /** Lets every held report through as if it had never been held; from then on the hold lets everything through. */
    release(): Promise<void>;
    /** `release()`, then the route goes: for `finally`. */
    dispose(): Promise<void>;
}

/** Holds every `POST /portfolio/report` the page sends from now until `release()`; every other request goes through untouched. */
async function holdReports(page: Page): Promise<ReportHold> {
    const held: Request[] = [];
    const waiting: Route[] = [];
    let open = false;
    const matches = (url: URL): boolean => url.pathname === REPORT_PATH;
    const handler = async (route: Route): Promise<void> => {
        if (open || route.request().method() !== 'POST') {
            await route.fallback();
            return;
        }
        held.push(route.request());
        waiting.push(route);
    };
    await page.route(matches, handler);
    const release = async (): Promise<void> => {
        open = true;
        // A request whose page went away cannot be let through any more, and there is nobody to deliver it to.
        await Promise.all(waiting.splice(0).map((route) => route.fallback().catch(() => undefined)));
    };
    return {
        held,
        release,
        dispose: async () => {
            await release();
            await page.unroute(matches, handler);
        },
    };
}

/** Busy, as the user meets it: the button says it is waiting, and cannot be pressed. */
async function expectBusy(button: Locator, why: string): Promise<void> {
    await expect(button, why).toHaveAttribute('data-busy', 'true');
    await expect(button, why).toBeDisabled();
}

/** Idle: nothing of the page is pending, and the button can be pressed again. A round trip away at most. */
async function expectIdle(button: Locator, why: string): Promise<void> {
    await expect(button, why).toHaveAttribute('data-busy', 'false', {timeout: ROUND_TRIP_MS});
    await expect(button, why).toBeEnabled();
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

    /**
     * Y-14: the list's Refresh recalculates the cards, as the Dashboard's and a broker's page's do: it asks the report of
     * the cards again with `force`, past the page's cache (portfolioStore), where the first load left it fresh. Red today:
     * the Refresh re-reads the list (`refreshAllBrokers`) and asks the report unforced, the fresh cached one answers, and
     * nothing reaches the network — the cards keep the figures of the first load.
     *
     * Fresh: nothing in this document marks the cached report stale between the two loads — no write, no
     * `requestPortfolioRefresh()`, no price catch-up (the E2E backend runs with `--no-scheduler`). The Refresh must ask
     * the same question (checked below), so that only the force can send it. Its brokers are part of the cache key too: a
     * neighbour creating or deleting a broker of TEST_USER between the two loads (brokers-detail, broker-recovery and
     * broker-create-feedback do, in `front-broker all`) makes the Refresh miss the cache whatever it forces — a green that
     * does not isolate the force, never a red. This file creates brokers on disposable accounts only.
     *
     * The report is held (`page.route`, let through with `route.fallback()`), so its pending state belongs to the test.
     * Any `POST /portfolio/report` once the page has settled is the Refresh's: `loadBrokers` is the page's only
     * `fetchReport`, the cards ask nothing, and the page reloads nothing in background (it listens to no portfolio
     * signal). `navigateTo` is a document load: the Dashboard the sign-in landed on is gone, with its reports. Busy or idle
     * is read from `data-busy` and `disabled` only. Read-only: TEST_USER, nothing written; the hold is released and
     * unrouted in `finally`.
     */
    test.describe('Broker List Refresh', () => {
        test.describe.configure({timeout: REFRESH_TEST_MS});

        test('Refresh asks the report of the cards again even when its cache is fresh, and holds its button until it is back (Y-14)', async ({page}) => {
            // The first load, settled: the list, then the report of the cards, answered — so in the page's cache, fresh.
            const firstLoad: Request[] = [];
            const recordCardsReport = (request: Request): void => {
                if (isCardsReport(request)) firstLoad.push(request);
            };
            page.on('request', recordCardsReport);
            await navigateTo(page, '/brokers');
            await waitForSettled(page.getByTestId('brokers-page'), ROUND_TRIP_MS);
            const refresh = page.getByTestId('brokers-refresh');
            await expectIdle(refresh, 'the list of brokers settled with its Refresh button still waiting');
            page.off('request', recordCardsReport);
            expect(firstLoad.length, `precondition: the first load asked the report of the cards (${TEST_USER.username} has brokers: populate_mock_data.py)`).toBeGreaterThan(0);
            // The latest the page asked: the question its cache holds for the page as it stands.
            const cached = firstLoad[firstLoad.length - 1];
            expect((await cached.response())?.ok(), 'precondition: the report of the cards was answered at the first load, so the page cached it').toBe(true);

            const gate = await holdReports(page);
            try {
                const listBack = page.waitForResponse((response) => isBrokerList(response.request()), {timeout: ROUND_TRIP_MS});
                await refresh.click();
                const list = await listBack;
                expect(list.ok(), `the list of brokers Refresh asks again: HTTP ${list.status()}`).toBe(true);
                // The report is asked once the list is in, inside the same Refresh.
                await expect.poll(() => gate.held.length, {message: 'Refresh never asked the report of the cards again: the cached one, still fresh, answered for it (Y-14)', timeout: ROUND_TRIP_MS}).toBeGreaterThan(0);
                const asked = gate.held[0];
                await expectBusy(refresh, 'Refresh asked the report of the cards again, and its button does not wait for it');

                // The question the cache holds, asked again, about the brokers of the refreshed list: the first load's, unless a
                // neighbour changed them (see above).
                expect(questionOf(asked), 'the report Refresh asks is not the question of the cards').toEqual(questionOf(cached));
                const {items = []} = (await list.json()) as {items?: Array<{id: number; user_role?: string | null}>};
                const shown = items
                    .filter((broker) => broker.user_role != null)
                    .map((broker) => broker.id)
                    .sort((a, b) => a - b);
                expect(brokersOf(asked), 'the report Refresh asks is not about the brokers of the refreshed list').toEqual(shown);

                await gate.release();
                await expectIdle(refresh, 'the report of the cards is back, and the Refresh button still waits');
                expect((await asked.response())?.ok(), 'the report of the cards Refresh asked again failed').toBe(true);
            } finally {
                await gate.dispose();
            }
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
