/**
 * R1 broker deletion outcomes. Real, independently owned brokers; the cascade
 * case owns one synthetic opening deposit. Only failure replies are intercepted,
 * for the precise owned DELETE. No shared broker, helper, or runner mutations.
 */
import {expect, test as base, type Page, type Request, type Response} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {eventSeq, waitForEvent, waitForSettled, type AppEvent} from '../fixtures/app-events';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';
import {schemas} from '../../src/lib/api/generated';

const API = '/api/v1/brokers';
const UI_TIMEOUT = 10_000;
type OwnedBroker = {id: number; name: string; deleted: boolean};
type Owned = {suffix: string; brokers: OwnedBroker[]};
type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

async function cleanupOwned(page: Page, owned: Owned) {
    const failures: string[] = [];
    try {
        await page.goto('about:blank');
    } catch (error) {
        failures.push(`unmount page: ${String(error)}`);
    }
    for (const broker of owned.brokers) {
        if (broker.deleted) continue;
        try {
            const response = await page.request.get(`${API}/${broker.id}`);
            if (response.status() === 404) continue;
            const current = await jsonFrom<{id: number; name: string}>(response, 'read owned broker before cleanup');
            // SQLite may recycle a deleted id. Never delete its new owner.
            if (current.name !== broker.name) continue;
            const result = schemas.BRBulkDeleteResponse.parse(await jsonFrom(await page.request.delete(`${API}?ids=${broker.id}&force=true`), 'delete owned broker and its synthetic opening deposit'));
            expect(result.results.find((item) => item.id === broker.id)?.success).toBe(true);
        } catch (error) {
            failures.push(`${broker.id}: ${String(error)}`);
        }
    }
    expect(failures, 'cleanup is limited to this case’s surviving broker identities').toEqual([]);
}

const test = base.extend<{owned: Owned}>({
    owned: async ({page}, use, testInfo) => {
        const baseURL = testInfo.project.use.baseURL;
        if (!baseURL || new URL(baseURL).port !== '6041' || !['localhost', '127.0.0.1'].includes(new URL(baseURL).hostname)) {
            throw new Error('Broker recovery requires the shared local test backend on port 6041');
        }
        const origin = new URL(baseURL).origin;
        await page.route('**/*', async (route) => {
            const url = new URL(route.request().url());
            if (['http:', 'https:'].includes(url.protocol) && url.origin !== origin) {
                await route.abort('blockedbyclient');
                return;
            }
            await route.fallback();
        });
        const owned: Owned = {suffix: `w${testInfo.workerIndex}-${uniqueSuffix()}`, brokers: []};
        try {
            await login(page, TEST_USER);
            await use(owned);
        } finally {
            await cleanupOwned(page, owned);
        }
    },
});

test.setTimeout(60_000);

async function createBroker(page: Page, owned: Owned, deposits = 0): Promise<OwnedBroker> {
    const name = `Recovery O'Neil <b>synthetic</b> ${owned.suffix}`;
    const response = schemas.BRBulkCreateResponse.parse(
        await jsonFrom(
            await page.request.post(API, {
                data: [
                    {
                        name,
                        opened_at: '2020-01-02',
                        ...(deposits === 1 ? {initial_balances: [{code: 'EUR', amount: 10}]} : {}),
                    },
                ],
            }),
            'create owned recovery broker',
        ),
    );
    const result = response.results.find((item) => item.name === name);
    if (typeof result?.broker_id !== 'number') throw new Error(`Owned broker id missing: ${JSON.stringify(response)}`);
    const broker = {id: result.broker_id, name, deleted: false};
    owned.brokers.push(broker);
    expect(result.success).toBe(true);
    expect(result.deposits_created ?? 0).toBe(deposits);
    return broker;
}

async function openDelete(page: Page, broker: OwnedBroker) {
    await navigateTo(page, '/brokers');
    await expect(page.getByTestId('brokers-page')).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(page.getByTestId('brokers-page'));
    const card = page.getByTestId(`broker-card-${broker.id}`).filter({hasText: broker.name});
    await expect(card).toBeVisible({timeout: UI_TIMEOUT});
    await card.getByTestId(`broker-delete-${broker.id}`).click();
    await expect(page.getByTestId('delete-broker-dialog')).toBeVisible({timeout: UI_TIMEOUT});
    await expect(page.getByTestId('delete-broker-confirm')).toBeEnabled();
    return card;
}

function matchesDelete(request: Request, brokerId: number): boolean {
    const url = new URL(request.url());
    return request.method() === 'DELETE' && url.pathname === API && url.searchParams.getAll('ids').includes(String(brokerId));
}

async function confirmRealDelete(page: Page, brokerId: number, force: boolean): Promise<Response> {
    const [response] = await Promise.all([page.waitForResponse((candidate) => matchesDelete(candidate.request(), brokerId), {timeout: UI_TIMEOUT}), page.getByTestId(force ? 'delete-broker-force-delete' : 'delete-broker-confirm').click()]);
    const query = new URL(response.url()).searchParams;
    expect(query.getAll('ids')).toEqual([String(brokerId)]);
    expect(query.get('force')).toBe(String(force));
    return response;
}

/** Call after a pending/terminal-state barrier, never instead of one. */
async function expectNoDeletionSuccess(page: Page, brokerId: number, since: number) {
    const successes = await page.evaluate(
        ({id, after}) => {
            const events = (window as unknown as {__lf?: {events?: AppEvent[]}}).__lf?.events;
            if (!events) throw new Error('Application event buffer is not mounted');
            return events.filter((event) => event.seq > after && event.name === 'broker.deleted' && event.detail?.brokerId === id);
        },
        {id: brokerId, after: since},
    );
    expect(successes).toEqual([]);
    await expect(page.getByTestId('toast-success')).toHaveCount(0);
}

for (const deposits of [0, 1]) {
    test(`real deletion with ${deposits} owned transaction(s) publishes the exact success outcome`, async ({page, owned}) => {
        const broker = await createBroker(page, owned, deposits);
        const card = await openDelete(page, broker);
        let since = await eventSeq(page);

        if (deposits === 1) {
            const blockedResponse = await confirmRealDelete(page, broker.id, false);
            const blocked = schemas.BRBulkDeleteResponse.parse(await jsonFrom(blockedResponse, 'nonforce owned deletion'));
            expect(blocked.results.find((item) => item.id === broker.id)).toMatchObject({success: false, transaction_count: 1});
            const event = await waitForEvent(page, 'broker.delete.blocked', {since, timeout: UI_TIMEOUT});
            expect(event.detail).toEqual({brokerId: broker.id, transactionCount: 1});
            await expect(page.getByTestId('delete-broker-force-delete')).toBeEnabled({timeout: UI_TIMEOUT});
            await expect(page.getByTestId('delete-broker-dialog').getByTestId('info-banner-warning')).toBeVisible();
            await expect(page.getByTestId('toast-error')).toHaveCount(0);
            await expectNoDeletionSuccess(page, broker.id, since);
            since = await eventSeq(page);
        }

        const response = await confirmRealDelete(page, broker.id, deposits === 1);
        const deleted = schemas.BRBulkDeleteResponse.parse(await jsonFrom(response, 'real owned deletion'));
        const result = deleted.results.find((item) => item.id === broker.id);
        if (result?.success) broker.deleted = true;
        expect(result).toMatchObject({id: broker.id, success: true, deleted_count: 1, transactions_deleted: deposits});
        const event = await waitForEvent(page, 'broker.deleted', {since, timeout: UI_TIMEOUT});
        // Success DTO uses transactions_deleted; transaction_count is the blocker.
        expect(event.detail).toEqual({brokerId: broker.id, transactionCount: deposits});
        await expect(page.getByTestId('toast-success')).toBeVisible({timeout: UI_TIMEOUT});
        await expect(page.getByTestId('toast-success').locator('b')).toHaveCount(0);
        await expect(page.getByTestId('toast-error')).toHaveCount(0);
        await expect(page.getByTestId('delete-broker-dialog')).toBeHidden({timeout: UI_TIMEOUT});
        await waitForSettled(page.getByTestId('brokers-page'));
        // ID + owned name: a recycled id is not evidence our broker survived.
        await expect(card).toHaveCount(0, {timeout: UI_TIMEOUT});
    });
}

for (const failure of ['false-result', 'missing-result', 'http-error'] as const) {
    test(`${failure} never announces success and retains the real owned broker`, async ({page, owned}) => {
        const broker = await createBroker(page, owned);
        const card = await openDelete(page, broker);
        let release!: () => void;
        const gate = new Promise<void>((resolve) => {
            release = resolve;
        });
        const requests: Array<{ids: string[]; force: string | null}> = [];
        await page.route('**/api/v1/brokers?*', async (route) => {
            if (!matchesDelete(route.request(), broker.id)) {
                await route.fallback();
                return;
            }
            const query = new URL(route.request().url()).searchParams;
            requests.push({ids: query.getAll('ids'), force: query.get('force')});
            await gate;
            const body =
                failure === 'http-error'
                    ? {detail: 'Synthetic deletion unavailable'}
                    : schemas.BRBulkDeleteResponse.parse({
                          results:
                              failure === 'missing-result'
                                  ? []
                                  : [
                                        {
                                            id: broker.id,
                                            success: false,
                                            deleted_count: 0,
                                            transaction_count: 0,
                                            transactions_deleted: 0,
                                            message: 'Synthetic deletion refused',
                                        },
                                    ],
                          success_count: 0,
                          total_deleted: 0,
                          errors: [],
                      });
            await route.fulfill({status: failure === 'http-error' ? 500 : 200, contentType: 'application/json', body: JSON.stringify(body)});
        });
        const since = await eventSeq(page);
        try {
            await page.getByTestId('delete-broker-confirm').click();
            await expect.poll(() => requests.length, {timeout: UI_TIMEOUT}).toBe(1);
            expect(requests).toEqual([{ids: [String(broker.id)], force: 'false'}]);
            await expect(page.getByTestId('delete-broker-confirm')).toBeDisabled();
            await expectNoDeletionSuccess(page, broker.id, since);
            release();

            const event = await waitForEvent(page, 'broker.delete.failed', {since, timeout: UI_TIMEOUT});
            expect(event.detail).toMatchObject({brokerId: broker.id});
            if (failure === 'missing-result') expect(event.detail?.reason).toBe('missing-result');
            if (failure === 'false-result') expect(event.detail?.reason).toBe('Synthetic deletion refused');
            await expect(page.getByTestId('toast-error')).toBeVisible({timeout: UI_TIMEOUT});
            await expect(page.getByTestId('delete-broker-confirm')).toBeEnabled({timeout: UI_TIMEOUT});
            await expect(page.getByTestId('delete-broker-dialog')).toBeVisible();
            await expectNoDeletionSuccess(page, broker.id, since);
            await expect(card).toBeVisible();
            const current = await jsonFrom<{id: number; name: string}>(await page.request.get(`${API}/${broker.id}`), 'verify failed deletion retained broker');
            expect(current).toMatchObject({id: broker.id, name: broker.name});
            await page.getByTestId('delete-broker-cancel').click();
            await expect(page.getByTestId('delete-broker-dialog')).toBeHidden({timeout: UI_TIMEOUT});
        } finally {
            release();
        }
    });
}
