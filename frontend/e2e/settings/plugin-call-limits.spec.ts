/**
 * The «Calls» block of a plugin's card E2E (project 76, lot U5): an administrator sets a call limit in «Configure» and
 * the block shows «count / limit», on the lane's own backend.
 *
 * The provider is `mockcount` (`backend/app/services/asset_source_providers/mockcount/plugin.py`): test-only, counted
 * at the call boundary like a provider that calls out, no network, and its fields are the five core call limits only.
 * It belongs to this spec: no other spec sets its limits. `mockprov` is never touched (it is not counted, and a limit on
 * it would be an instance setting of the shared backend that stops every spec using it), nor is CoinGecko's key.
 *
 * mockcount through the asset dialog, as `plugin-settings.spec.ts` reaches mockprov: the provider select never offers a
 * test-only provider, so the test creates a plain asset of its own, assigns it mockcount over the API, opens the asset's
 * edit dialog and clicks «Configure». Before U5 mockcount had no settings card (its only fields were the limits, which
 * the interface filtered out): «Configure» on it is part of what this spec proves.
 *
 * The limit: the week's, set far above anything a test run counts (`LIMIT`), so the window never fills under the other
 * specs' price reads. Precondition, checked over the API: no saved value and no variable on the week's limit. What is
 * checked beyond the screen: the write as the browser sent it (one instance item, the number as a number), the event the
 * save records (`pluginSettings.saved`, naming the field), and the catalogue read back (the field saved, the usage
 * window's limit). The limit is cleared over the API by the administrator after the test, whatever happened, and the
 * asset deleted.
 *
 * Assertions read test ids, `data-*`, the events and the API, never a translated text. Desktop, the runner's default
 * project. Prerequisites: test users (`e2e_test_admin` an administrator); no `LIBREFOLIO_PLUGIN_ASSET_MOCKCOUNT_*` on the
 * lane.
 */
import {schemas} from '../../src/lib/api/generated';
import {expect, test as base, type APIRequestContext, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {eventSeq, waitForSettled, type AppEvent} from '../fixtures/app-events';
import {TEST_ADMIN} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';
import {goToAssetDetailPage, openEditAssetModal} from '../assets/assets-helpers';

const API = '/api/v1';
const SETTINGS_PATH = `${API}/settings/plugins`;
const BULK_PATH = `${SETTINGS_PATH}/bulk`;

const MOCKCOUNT = 'mockcount';
/** The limit this spec owns: the week's. */
const WINDOW = 'week';
const FIELD_KEY = `call_limit_${WINDOW}`;
/** Far above any week of a test run: the window never fills while the limit is set. */
const LIMIT = 1_000_000;

type Account = {username: string; password: string};

/** What the test created or may have written: undone after it, whatever happened. */
interface Owned {
    assets: number[];
    /** The limit was (maybe) written: cleared afterwards. */
    limit: boolean;
}

async function signIn(api: APIRequestContext, account: Account): Promise<void> {
    const answer = await api.post(`${API}/auth/login`, {data: {username: account.username, password: account.password}});
    expect(answer.ok(), `POST ${API}/auth/login as ${account.username}: HTTP ${answer.status()} ${await answer.text()}`).toBe(true);
}

/** Clear the limit and delete the assets, as the administrator, on a session of its own; every failure returned, named. */
async function undo(page: Page, owned: Owned, open: () => Promise<APIRequestContext>): Promise<string[]> {
    const failures: string[] = [];
    if (!owned.limit && owned.assets.length === 0) return failures;
    await page.goto('about:blank').catch((error) => failures.push(`leave the page: ${String(error)}`));
    let api: APIRequestContext | null = null;
    try {
        api = await open();
        await signIn(api, TEST_ADMIN);
    } catch (error) {
        failures.push(`the administrator cannot sign in for the clean-up: ${String(error)}`);
        await api?.dispose().catch(() => undefined);
        return failures;
    }
    if (owned.limit) {
        try {
            const items = [{family: 'asset', plugin_code: MOCKCOUNT, field_key: FIELD_KEY, scope: 'system', clear: true}];
            schemas.PluginSettingsBulkWrite.parse({items});
            const answer = await api.patch(BULK_PATH, {data: {items}});
            expect(answer.status(), `PATCH ${BULK_PATH} clears ${MOCKCOUNT}'s ${FIELD_KEY}: ${await answer.text()}`).toBe(200);
        } catch (error) {
            failures.push(String(error));
        }
    }
    for (const id of owned.assets) {
        try {
            const answer = await api.delete(`${API}/assets`, {params: {asset_ids: id}});
            const body = (await answer.json().catch(() => null)) as {results?: Array<{asset_id: number; success: boolean}>} | null;
            expect(body?.results?.find((result) => result.asset_id === id)?.success, `asset ${id} deleted: HTTP ${answer.status()} ${JSON.stringify(body)}`).toBe(true);
        } catch (error) {
            failures.push(String(error));
        }
    }
    await api.dispose().catch(() => undefined);
    return failures;
}

const test = base.extend<{owned: Owned}>({
    owned: async ({page, playwright, baseURL}, use) => {
        const owned: Owned = {assets: [], limit: false};
        let failures: string[] = [];
        try {
            await use(owned);
        } finally {
            failures = await undo(page, owned, () => playwright.request.newContext({baseURL}));
        }
        expect(failures, 'the clean-up clears mockcount’s week limit and deletes the test’s asset').toEqual([]);
    },
});

// Sign-in, seeding over the API, the asset page and its dialog, a save and its read share the budget.
test.setTimeout(60_000);

type Entry = ReturnType<typeof schemas.PluginSettingsPluginRead.parse>;

/** mockcount's entry as the administrator reads it (named: a test-only plugin is listed only so). */
async function readMockcount(request: APIRequestContext): Promise<Entry> {
    const answer = await request.get(SETTINGS_PATH, {params: {family: 'asset', plugin_code: MOCKCOUNT}});
    const text = await answer.text();
    expect(answer.status(), `GET ${SETTINGS_PATH}?family=asset&plugin_code=${MOCKCOUNT}: ${text}`).toBe(200);
    const entry = schemas.PluginSettingsCatalogResponse.parse(JSON.parse(text)).plugins.find((candidate) => candidate.family === 'asset' && candidate.plugin_code === MOCKCOUNT);
    if (!entry) throw new Error(`GET ${SETTINGS_PATH} does not list ${MOCKCOUNT} when it is named (is the backend in test mode?): ${text}`);
    return entry;
}

/** The usage windows of an entry: the generated type of `call_usage` is wider than the object the server sends. */
function usageWindows(entry: Entry): Array<{window: string; count: number; limit: number | null; full: boolean}> {
    const usage = entry.call_usage as {windows?: Array<{window: string; count: number; limit: number | null; full: boolean}>} | null | undefined;
    return usage?.windows ?? [];
}

/** A plain EUR stock of the test's own, priced by mockcount: its id, recorded the moment the create names it. */
async function mockcountAsset(page: Page, owned: Owned): Promise<number> {
    const name = `E2E call limits ${uniqueSuffix()}`;
    const created = await page.request.post(`${API}/assets`, {data: [schemas.FAAssetCreateItem.parse({display_name: name, currency: 'EUR', asset_type: 'STOCK'})]});
    const body = (await created.json().catch(() => null)) as {results?: Array<{asset_id?: number | null; display_name?: string; success?: boolean}>} | null;
    const result = body?.results?.find((entry) => entry.display_name === name);
    if (typeof result?.asset_id === 'number') owned.assets.push(result.asset_id);
    expect(created.status(), `POST ${API}/assets creates "${name}": ${JSON.stringify(body)}`).toBe(201);
    if (!result?.success || typeof result.asset_id !== 'number') throw new Error(`"${name}" was not created: ${JSON.stringify(body)}`);
    const assetId = result.asset_id;

    const assignment = schemas.FAProviderAssignmentItem.parse({asset_id: assetId, provider_code: MOCKCOUNT, identifier: 'MOCK', identifier_type: 'TICKER', provider_params: null});
    const assigned = await page.request.post(`${API}/assets/provider`, {data: [assignment]});
    const assignedBody = (await assigned.json().catch(() => null)) as {results?: Array<{asset_id: number; success: boolean}>} | null;
    expect(assignedBody?.results?.find((entry) => entry.asset_id === assetId)?.success, `mockcount assigned: HTTP ${assigned.status()} ${JSON.stringify(assignedBody)}`).toBe(true);
    return assetId;
}

test.describe('«Calls» on mockcount, from the asset dialog', () => {
    test('an administrator sets the week’s limit: the box shows «count / limit», the catalogue reads it back', async ({page, owned}) => {
        await login(page, TEST_ADMIN);
        const before = await readMockcount(page.request);
        const field = before.fields.find((candidate) => candidate.key === FIELD_KEY);
        expect(field, `precondition: mockcount lists ${FIELD_KEY}`).toBeDefined();
        expect(field, `precondition: nothing sets ${FIELD_KEY} (no saved value, no variable on the lane)`).toMatchObject({source: 'none', locked: false, editable: true});
        expect(
            usageWindows(before).map((window) => window.window),
            'precondition: mockcount owns a count',
        ).toEqual(['minute', 'hour', 'day', 'week', 'month']);

        const assetId = await mockcountAsset(page, owned);
        await goToAssetDetailPage(page, String(assetId));
        await openEditAssetModal(page);
        await expect(page.getByTestId('asset-modal-form')).toHaveAttribute('data-snapshot-ready', 'true', {timeout: 10_000});
        const header = page.getByTestId('asset-modal-provider-header');
        if ((await header.getAttribute('data-expanded')) !== 'true') await header.click();
        await expect(header).toHaveAttribute('data-expanded', 'true');
        const configure = page.getByTestId('provider-configure');
        await expect(configure, 'mockcount’s limits are settings: the provider panel offers «Configure»').toBeVisible({timeout: 10_000});
        await configure.click();

        const modal = page.getByTestId('plugin-settings-modal');
        await expect(modal.locator(`[data-plugin="${MOCKCOUNT}"]`), 'the dialog is mockcount’s').toHaveCount(1);
        const form = modal.getByTestId(`plugin-settings-form-${MOCKCOUNT}`);
        await expect(form, 'mockcount’s card is read and drawn').toBeVisible({timeout: 10_000});
        const block = form.getByTestId('plugin-settings-calls');
        await expect(block).toBeVisible();
        await expect(block).toHaveAttribute('data-managed', 'false');
        const boxes = block.getByTestId('plugin-settings-calls-window');
        await expect(boxes).toHaveCount(5);
        const box = block.locator(`[data-testid="plugin-settings-calls-window"][data-window="${WINDOW}"]`);
        await expect(box).toHaveAttribute('data-control', 'input');
        await expect(box).toHaveAttribute('data-limit', '');
        await expect(box).toHaveAttribute('data-count', /^\d+$/);
        await expect(box.getByTestId('plugin-settings-calls-limit'), 'no limit yet: the count alone').toHaveCount(0);
        const input = box.getByTestId('plugin-settings-calls-input');
        await expect(input).toHaveValue('');

        await input.fill(String(LIMIT));
        await expect(box).toHaveAttribute('data-edit', 'text');
        const save = form.getByTestId('plugin-settings-save');
        await expect(save).toBeEnabled();
        await save.scrollIntoViewIfNeeded();
        owned.limit = true;
        const since = await eventSeq(page);
        const sent = page.waitForRequest((request) => request.method() === 'PATCH' && new URL(request.url()).pathname === BULK_PATH, {timeout: 15_000});
        sent.catch(() => undefined);
        await save.click();
        const body = (await sent).postDataJSON() as {items: unknown[]};
        expect(body.items, 'one instance item, the number as a number').toEqual([{family: 'asset', plugin_code: MOCKCOUNT, field_key: FIELD_KEY, scope: 'system', value: LIMIT}]);
        const recorded = await page.waitForFunction((after) => (window as unknown as {__lf?: {events?: AppEvent[]}}).__lf?.events?.find((event) => event.seq > after && event.name.startsWith('pluginSettings.save')) ?? null, since, {timeout: 15_000});
        expect((await recorded.jsonValue()) as AppEvent).toMatchObject({name: 'pluginSettings.saved', detail: {family: 'asset', plugin_code: MOCKCOUNT, fields: [FIELD_KEY]}});
        await waitForSettled(form);

        // Read again after the save: «count / limit» on screen, the field saved and the window's limit through the API
        await expect(box).toHaveAttribute('data-limit', String(LIMIT));
        await expect(box.getByTestId('plugin-settings-calls-limit')).toBeVisible();
        await expect(box).toHaveAttribute('data-state', 'open');
        await expect(box).toHaveAttribute('data-edit', '');
        await expect(input).toHaveValue(String(LIMIT));
        const after = await readMockcount(page.request);
        expect(after.fields.find((candidate) => candidate.key === FIELD_KEY)).toMatchObject({source: 'db', value: LIMIT});
        expect(usageWindows(after).find((window) => window.window === WINDOW)).toMatchObject({limit: LIMIT, full: false});
    });
});
