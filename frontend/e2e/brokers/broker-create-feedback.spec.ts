import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {eventSeq, waitForEvent, waitForSettled} from '../fixtures/app-events';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';
import {schemas} from '../../src/lib/api/generated';

const API = '/api/v1/brokers';
const UI_TIMEOUT = 10_000;

type OwnedBroker = {id: number; name: string};
type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

async function createOwnedBroker(page: Page, name: string): Promise<OwnedBroker> {
    const response = schemas.BRBulkCreateResponse.parse(
        await jsonFrom(
            await page.request.post(API, {
                data: [{name, opened_at: '2020-01-02'}],
            }),
            'create owned broker',
        ),
    );
    const result = response.results.find((item) => item.name === name);
    if (typeof result?.broker_id !== 'number') throw new Error(`Owned broker id missing: ${JSON.stringify(response)}`);
    expect(result.success).toBe(true);
    return {id: result.broker_id, name};
}

async function cleanupOwnedBrokers(page: Page, brokers: OwnedBroker[]) {
    const failures: string[] = [];
    try {
        await page.goto('about:blank');
    } catch (error) {
        failures.push(`unmount page: ${String(error)}`);
    }
    for (const broker of brokers) {
        try {
            const response = await page.request.get(`${API}/${broker.id}`);
            if (response.status() === 404) continue;
            const current = await jsonFrom<{id: number; name: string}>(response, 'read owned broker before cleanup');
            if (current.name !== broker.name) continue;
            const result = schemas.BRBulkDeleteResponse.parse(await jsonFrom(await page.request.delete(`${API}?ids=${broker.id}&force=true`), 'delete owned broker'));
            expect(result.results.find((item) => item.id === broker.id)?.success).toBe(true);
        } catch (error) {
            failures.push(`${broker.id}: ${String(error)}`);
        }
    }
    expect(failures, 'cleanup is limited to this case’s own broker identities').toEqual([]);
}

test.setTimeout(60_000);

test.describe('Broker create feedback', () => {
    test('keeps create feedback scoped to the broker modal and global brokers page', async ({page}) => {
        const owned: OwnedBroker[] = [];
        try {
            await login(page, TEST_USER);
            await navigateTo(page, '/brokers');
            await expect(page.getByTestId('brokers-page')).toBeVisible();
            await waitForSettled(page.getByTestId('brokers-page'));

            const duplicateName = `Broker feedback ${uniqueSuffix()} <b>owned</b>`;
            const duplicateBroker = await createOwnedBroker(page, duplicateName);
            owned.push(duplicateBroker);

            await page.getByTestId('add-broker-button').click();
            const modal = page.getByTestId('broker-modal');
            await expect(modal).toBeVisible();

            const nameInput = page.getByTestId('broker-name-input');
            await nameInput.fill(duplicateName);
            await expect(nameInput).toHaveValue(duplicateName);
            await page.getByTestId('broker-form-submit').click();
            await expect(page.getByTestId('info-banner-error')).toBeVisible();
            await expect(page.getByTestId('toast-success')).toHaveCount(0);
            await expect(modal).toBeVisible();

            await page.getByTestId('broker-modal-close').click();
            await expect(page.getByTestId('broker-modal-discard-confirm')).toBeVisible();
            await page.getByTestId('broker-modal-discard').click();
            await expect(modal).toBeHidden();

            await page.getByTestId('add-broker-button').click();
            await expect(modal).toBeVisible();
            await expect(page.getByTestId('info-banner-error')).toHaveCount(0);
            await expect(nameInput).toHaveValue('');

            const createdName = `Broker feedback ${uniqueSuffix()} <i>new</i>`;
            const since = await eventSeq(page);
            await nameInput.fill(createdName);
            await expect(nameInput).toHaveValue(createdName);
            const [createdResponse] = await Promise.all([
                page.waitForResponse(
                    (response) =>
                        new URL(response.url()).pathname === API &&
                        response.request().method() === 'POST' &&
                        response
                            .request()
                            .postDataJSON()
                            ?.some((item: {name?: string}) => item.name === createdName),
                ),
                page.getByTestId('broker-form-submit').click(),
            ]);
            const createdResult = schemas.BRBulkCreateResponse.parse(await jsonFrom(createdResponse, 'create broker from the reopened modal'));
            const created = createdResult.results.find((item) => item.name === createdName);
            if (typeof created?.broker_id !== 'number') throw new Error('Created broker has no owned response ID');
            const createdId = created.broker_id;
            owned.push({id: createdId, name: createdName});
            expect(created.success).toBe(true);

            const createdEvent = await waitForEvent(page, 'broker.created', {since, timeout: UI_TIMEOUT});
            expect(createdEvent.detail).toEqual({brokerId: createdId});

            await expect(page.getByTestId('toast-success')).toBeVisible({timeout: UI_TIMEOUT});
            await expect(page.getByTestId('toast-success').locator('i')).toHaveCount(0);
            await expect(page.getByTestId('broker-modal')).toBeHidden({timeout: UI_TIMEOUT});
            await waitForSettled(page.getByTestId('brokers-page'));

            const createdCard = page.getByTestId(`broker-card-${createdId}`).filter({hasText: createdName});
            await expect(createdCard).toBeVisible({timeout: UI_TIMEOUT});
        } finally {
            await cleanupOwnedBrokers(page, owned);
        }
    });
});
