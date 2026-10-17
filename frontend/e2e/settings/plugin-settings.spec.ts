/**
 * Settings › Plugins and «Configure» E2E (workstream X, lot CP11c): the plugin settings interface of lot CP11b
 * (`src/lib/features/plugin-settings/`), on the lane's own backend.
 *
 * Four concerns:
 *   1. Settings › Plugins, read only, as a member and as an administrator: `?tab=plugins` selects the tab and its read
 *      settles (`data-busy`); the asset family lists justETF and Borsa Italiana, configured, each with its one personal
 *      select on its default (`all`), editable, offering the options the plugin declares; the test-only mockprov is never
 *      listed. The list is opened and closed with Escape, nothing chosen, nothing saved: these two fields are the shared
 *      test users' own search preferences, which other specs search with.
 *   2. A member's own settings through «Configure» on mockprov: the instance's four fields read only (`adminOnly`), the
 *      instance secret only «set» or «not set»; a number and a personal secret saved and read back; then «Use the
 *      default» and «Clear», saved, both back where they were.
 *   3. An administrator's instance secret, mockprov's `api_key`: saved; never shown again («Replace» opens an empty
 *      field); cleared.
 *   4. Search: a provider the search stream reports NOT_CONFIGURED gets a «to configure» row whose «Configure» opens that
 *      plugin's settings over the asset dialog; a result marked 👑 brings the legend. The stream is simulated
 *      (`page.route`): no provider is asked anything. The settings dialog is closed without saving.
 *
 * mockprov through the asset dialog: the dialog's provider select never offers mockprov (`ProviderAssignmentSection.svelte`
 * filters it out, on purpose), so a test reaches it the way a user reaches any provider already assigned. It creates a
 * plain asset of its own, assigns it mockprov over the API under the one identifier the mock refuses to quote (a page
 * that polls the asset writes nothing back), opens the asset's edit dialog and clicks «Configure». mockprov's seven fields
 * make the dialog taller than the window: its body scrolls between the title and «Close» (the fix CP11c's first run asked
 * for), so both tests also check that «Close» stays in the window over the overflowing body and that Save is reached by
 * scrolling it.
 *
 * What is checked beyond the screen: each write as the browser sent it (`PATCH /api/v1/settings/plugins/bulk`: a number
 * as a number, a secret only in `secret_value`), the event `notify()` records for it (`pluginSettings.saved`, naming the
 * fields, never a value), and the state the API reads back, in which a saved secret never appears.
 *
 * Data: every write is the test's own and is undone by the `owned` fixture, whatever happened. Each mockprov field a
 * test may write is recorded before its Save and cleared afterwards over the API by the account that writes it (the
 * instance fields by the administrator, the personal ones by their user); then the asset is deleted. No other spec reads
 * mockprov's settings. The member test looks at the instance fields while the administrator test may be writing
 * `api_key`, so it never asserts their values: the file runs in parallel (the config's default). Assertions read test
 * ids, `data-*`, `aria-*`, the events and the API, never a translated text.
 *
 * Prerequisites: test users (`e2e_test_user` a member, `e2e_test_admin` an administrator); no environment variable sets a
 * mockprov field on the lane (`LIBREFOLIO_MOCKPROV_API_KEY`, `LIBREFOLIO_PLUGIN_ASSET_MOCKPROV_*`); the justETF and Borsa
 * Italiana preferences of both users on their default. Desktop, the runner's default project.
 */
import type {Route} from '@playwright/test';
import {schemas} from '../../src/lib/api/generated';
import {expect, test as base, type APIRequestContext, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {eventSeq, waitForSettled, type AppEvent} from '../fixtures/app-events';
import {TEST_ADMIN, TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';
import {goToAssetDetailPage, goToAssetsPage, openCreateAssetModal, openEditAssetModal} from '../assets/assets-helpers';

const API = '/api/v1';
const SETTINGS_PATH = `${API}/settings/plugins`;
const BULK_PATH = `${SETTINGS_PATH}/bulk`;
const SEARCH_STREAM_PATH = `${API}/assets/provider/search/stream`;
const SEARCH_PATH = `${API}/assets/provider/search`;

/** The test-only provider (`mockprov/plugin.py`): one setting of every kind, listed by the API only when named. */
const MOCKPROV = 'mockprov';
/** mockprov.get_current_value raises NOT_FOUND for exactly this identifier: a page that polls the asset writes nothing. */
const OFFLINE_IDENTIFIER = 'INVALID_TICKER_12345';
/** mockprov's instance fields, in their declared order. */
const SYSTEM_KEYS = ['api_key', 'region', 'price_tolerance', 'verbose'] as const;
/** mockprov's personal fields, in their declared order. */
const USER_KEYS = ['preferred_language', 'results_limit', 'personal_token'] as const;

/** The production plugins of the tab: the one personal select each declares, with its options in declared order. */
const TAB_PLUGINS = [
    {code: 'justetf', key: 'preferred_currency', options: ['all', 'EUR', 'USD', 'CHF', 'GBP']},
    {code: 'borsa_italiana', key: 'preferred_language', options: ['all', 'it', 'en']},
] as const;

/** The provider the simulated search reports NOT_CONFIGURED. */
const UNCONFIGURED = 'justetf';
/** The simulated search's one result: a fund line marked 👑, as justETF marks a fund's own currency. */
const CROWN_IDENTIFIER = 'E2ECROWN';

/** The events `PluginSettingsForm.save()` ends on: one per Save. */
const SAVE_OUTCOMES = ['pluginSettings.saved', 'pluginSettings.save.refused', 'pluginSettings.save.failed'];

type Account = {username: string; password: string};
type Scope = 'user' | 'system';
type Field = ReturnType<typeof schemas.PluginSettingFieldRead.parse>;
type SentItem = Record<string, unknown>;

/** What a test wrote, recorded before it writes it: undone after the test, whatever happened. */
interface Owned {
    /** The assets it created, with the account that created them. */
    assets: Array<{id: number; by: Account}>;
    /** The mockprov fields it may have written, with the account that writes them, and so clears them. */
    fields: Array<{key: string; scope: Scope; by: Account}>;
}

// =============================================================================
// Clean-up
// =============================================================================

async function signIn(api: APIRequestContext, account: Account): Promise<void> {
    const answer = await api.post(`${API}/auth/login`, {data: {username: account.username, password: account.password}});
    expect(answer.ok(), `POST ${API}/auth/login as ${account.username}: HTTP ${answer.status()} ${await answer.text()}`).toBe(true);
}

/**
 * Undo what the test recorded, on sessions of their own (the page's may be gone): per account, clear every mockprov field
 * it may have written, in one write, then delete its assets. Every step is tried whatever happened to the previous one;
 * every failure is returned, named.
 */
async function undo(page: Page, owned: Owned, open: () => Promise<APIRequestContext>): Promise<string[]> {
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<void>): Promise<void> => {
        try {
            await action();
        } catch (error) {
            failures.push(`${label}: ${String(error)}`);
        }
    };
    if (owned.fields.length === 0 && owned.assets.length === 0) return failures;

    // Off the page first: nothing still on screen reads the asset or the settings while they go.
    await attempt('leave the page', async () => {
        await page.goto('about:blank');
    });
    const accounts = new Map<string, Account>();
    for (const {by} of [...owned.fields, ...owned.assets]) accounts.set(by.username, by);
    for (const account of accounts.values()) {
        let session: APIRequestContext | null = null;
        try {
            session = await open();
            await signIn(session, account);
        } catch (error) {
            failures.push(`${account.username} cannot sign in for the clean-up: ${String(error)}`);
            await session?.dispose().catch(() => undefined);
            continue;
        }
        const api: APIRequestContext = session;
        // A field named twice in one write is refused: one item per field.
        const fields = [...new Map(owned.fields.filter(({by}) => by.username === account.username).map((field) => [field.key, field])).values()];
        if (fields.length > 0) {
            await attempt(`${account.username} clears mockprov's ${fields.map(({key}) => key).join(', ')}`, async () => {
                const items = fields.map(({key, scope}) => ({family: 'asset', plugin_code: MOCKPROV, field_key: key, scope, clear: true}));
                schemas.PluginSettingsBulkWrite.parse({items});
                const answer = await api.patch(BULK_PATH, {data: {items}});
                expect(answer.status(), `PATCH ${BULK_PATH}: ${await answer.text()}`).toBe(200);
            });
        }
        for (const asset of owned.assets.filter(({by}) => by.username === account.username)) {
            await attempt(`${account.username} deletes asset ${asset.id}`, async () => {
                const answer = await api.delete(`${API}/assets`, {params: {asset_ids: asset.id}});
                const body = (await answer.json().catch(() => null)) as {results?: Array<{asset_id: number; success: boolean}>} | null;
                expect(answer.ok(), `DELETE ${API}/assets?asset_ids=${asset.id}: HTTP ${answer.status()} ${JSON.stringify(body)}`).toBe(true);
                expect(body?.results?.find((result) => result.asset_id === asset.id)?.success, `asset ${asset.id} deleted: ${JSON.stringify(body)}`).toBe(true);
            });
        }
        await attempt(`${account.username} closes its clean-up session`, () => api.dispose());
    }
    return failures;
}

const test = base.extend<{owned: Owned}>({
    owned: async ({page, playwright, baseURL}, use) => {
        const owned: Owned = {assets: [], fields: []};
        let failures: string[] = [];
        try {
            await use(owned);
        } finally {
            failures = await undo(page, owned, () => playwright.request.newContext({baseURL}));
        }
        expect(failures, 'the clean-up clears every mockprov field the test may have written and deletes every asset it created').toEqual([]);
    },
});

// Sign-in, seeding over the API, the asset page and its dialog, and two saves each followed by a read share the budget.
test.setTimeout(60_000);

// =============================================================================
// Reads, seeding and the screens
// =============================================================================

/** A plugin's fields as `request`'s account reads them, and the answer as text: where a secret must never appear. */
async function readPlugin(request: APIRequestContext, code: string): Promise<{fields: Map<string, Field>; text: string}> {
    const answer = await request.get(SETTINGS_PATH, {params: {family: 'asset', plugin_code: code}});
    const text = await answer.text();
    expect(answer.status(), `GET ${SETTINGS_PATH}?family=asset&plugin_code=${code}: ${text}`).toBe(200);
    const plugin = schemas.PluginSettingsCatalogResponse.parse(JSON.parse(text)).plugins.find((entry) => entry.family === 'asset' && entry.plugin_code === code);
    if (!plugin) throw new Error(`GET ${SETTINGS_PATH} does not list ${code} when it is named: ${text}`);
    return {fields: new Map(plugin.fields.map((field) => [field.key, field])), text};
}

/**
 * A plain EUR stock of the test's own, priced by mockprov under the offline identifier: its id, recorded the moment the
 * create names it, so that the clean-up deletes it whatever follows.
 */
async function mockprovAsset(page: Page, owned: Owned, by: Account): Promise<number> {
    const name = `E2E plugin settings ${uniqueSuffix()}`;
    const created = await page.request.post(`${API}/assets`, {data: [schemas.FAAssetCreateItem.parse({display_name: name, currency: 'EUR', asset_type: 'STOCK'})]});
    const body = (await created.json().catch(() => null)) as {results?: Array<{asset_id?: number | null; display_name?: string; success?: boolean}>} | null;
    const result = body?.results?.find((entry) => entry.display_name === name);
    if (typeof result?.asset_id === 'number') owned.assets.push({id: result.asset_id, by});
    expect(created.status(), `POST ${API}/assets creates "${name}": ${JSON.stringify(body)}`).toBe(201);
    if (!result?.success || typeof result.asset_id !== 'number') throw new Error(`"${name}" was not created: ${JSON.stringify(body)}`);
    const assetId = result.asset_id;

    const assignment = schemas.FAProviderAssignmentItem.parse({asset_id: assetId, provider_code: MOCKPROV, identifier: OFFLINE_IDENTIFIER, identifier_type: 'TICKER', provider_params: null});
    const assigned = await page.request.post(`${API}/assets/provider`, {data: [assignment]});
    const assignedBody = (await assigned.json().catch(() => null)) as {results?: Array<{asset_id: number; success: boolean}>} | null;
    expect(assigned.ok(), `POST ${API}/assets/provider: HTTP ${assigned.status()} ${JSON.stringify(assignedBody)}`).toBe(true);
    expect(assignedBody?.results?.find((entry) => entry.asset_id === assetId)?.success, `mockprov assigned: ${JSON.stringify(assignedBody)}`).toBe(true);
    return assetId;
}

/** Settings › Plugins through its URL: the tab, once its read has landed. */
async function openPluginsTab(page: Page): Promise<Locator> {
    await navigateTo(page, '/settings?tab=plugins');
    await expect(page.getByTestId('settings-tab-plugins'), '?tab=plugins selects the Plugins tab').toHaveAttribute('aria-selected', 'true', {timeout: 10_000});
    const tab = page.getByTestId('plugin-settings-tab');
    await waitForSettled(tab);
    return tab;
}

/**
 * The asset's edit dialog, then mockprov's «Configure» in its provider panel: the settings dialog once mockprov's form is
 * on show — the form is drawn only when the plugin's read has landed.
 */
async function openMockprovConfigure(page: Page, assetId: number): Promise<{modal: Locator; form: Locator}> {
    await goToAssetDetailPage(page, String(assetId));
    await openEditAssetModal(page);
    // The edit data is in: an asset with a provider opens its provider panel by itself (AssetModal, populateFromEditData).
    await expect(page.getByTestId('asset-modal-form')).toHaveAttribute('data-snapshot-ready', 'true', {timeout: 10_000});
    const header = page.getByTestId('asset-modal-provider-header');
    if ((await header.getAttribute('data-expanded')) !== 'true') await header.click();
    await expect(header).toHaveAttribute('data-expanded', 'true');

    const configure = page.getByTestId('provider-configure');
    await expect(configure, 'mockprov declares settings: once they are read, the provider panel offers «Configure»').toBeVisible({timeout: 10_000});
    await expect(configure, 'mockprov requires nothing: configured').toHaveAttribute('data-configured', 'true');
    // Same `settingsEntry` as the button just shown: a configured plugin carries no «not configured» badge.
    await expect(page.getByTestId('provider-settings-status')).toHaveCount(0);
    await configure.click();

    const modal = page.getByTestId('plugin-settings-modal');
    await expect(modal).toBeVisible();
    await expect(modal.locator(`[data-plugin="${MOCKPROV}"]`), 'the dialog is mockprov’s').toHaveCount(1);
    const form = modal.getByTestId(`plugin-settings-form-${MOCKPROV}`);
    await expect(form, 'mockprov’s settings are read and drawn').toBeVisible({timeout: 10_000});
    await expect(form).toHaveAttribute('data-configured', 'true');

    // The dialog's frame holds over a form taller than the window. Checked here, freshly opened, while the body is still at
    // its top: a «Close» that scrolled with the form would be out of the window now. Save's half — reachable by scrolling the
    // body — is checked by save(). The precondition first: without an overflowing body, «Close in the window» proves nothing.
    const body = modal.getByTestId('plugin-settings-modal-body');
    await expect.poll(() => body.evaluate((element) => element.scrollHeight > element.clientHeight), {message: 'precondition: mockprov’s form is taller than the dialog’s body at this window size, so the body scrolls'}).toBe(true);
    await expect(modal.getByTestId('plugin-settings-modal-close'), '«Close» stays whole in the window while the form overflows the body').toBeInViewport({ratio: 1});
    return {modal, form};
}

/** One field of a plugin's form. */
function setting(form: Locator, key: string): Locator {
    return form.getByTestId(`plugin-setting-${key}`);
}

/** A write item as `writeItems()` sends it for mockprov. */
function sentItem(key: string, scope: Scope, write: {value: number} | {secret_value: string} | {clear: true}): SentItem {
    return {family: 'asset', plugin_code: MOCKPROV, field_key: key, scope, ...write};
}

/**
 * Save the form; return what it sent and what it recorded: the items of the `PATCH` (checked against the generated
 * schema) and the first save outcome recorded after the click, saved, refused or failed. Returns once the form has read
 * the plugin again (`data-busy` false), so what it shows is the server's state.
 */
async function save(page: Page, form: Locator): Promise<{items: SentItem[]; outcome: AppEvent}> {
    const button = form.getByTestId('plugin-settings-save');
    await expect(button, 'the edits are valid: Save is offered').toBeEnabled();
    // Reachable, not only enabled: brought into the window the way a user scrolls to it. A dialog taller than the window
    // with nothing to scroll leaves Save below the bottom edge, where no pointer reaches it.
    await button.scrollIntoViewIfNeeded();
    await expect(button, 'Save can be scrolled into the window: the «Configure» dialog must not run past the bottom of the window with nothing to scroll').toBeInViewport({ratio: 1});
    const since = await eventSeq(page);
    const sent = page.waitForRequest((request) => request.method() === 'PATCH' && new URL(request.url()).pathname === BULK_PATH, {timeout: 15_000});
    // Awaited below; handled here too, so a click that throws first leaves no unhandled rejection behind.
    sent.catch(() => undefined);
    await button.click();
    const body = (await sent).postDataJSON() as {items: SentItem[]};
    schemas.PluginSettingsBulkWrite.parse(body);
    const recorded = await page.waitForFunction(({names, after}) => (window as unknown as {__lf?: {events?: AppEvent[]}}).__lf?.events?.find((event) => event.seq > after && names.includes(event.name)) ?? null, {names: SAVE_OUTCOMES, after: since}, {timeout: 15_000});
    const outcome = (await recorded.jsonValue()) as AppEvent;
    await waitForSettled(form);
    return {items: body.items, outcome};
}

/** The save went through, and its event names the fields it wrote: never a value. */
function expectSaved(outcome: AppEvent, fields: string[], secret?: string): void {
    expect(outcome, `the save went through: ${JSON.stringify(outcome)}`).toMatchObject({name: 'pluginSettings.saved', detail: {family: 'asset', plugin_code: MOCKPROV, fields}});
    if (secret !== undefined) expect(JSON.stringify(outcome), 'the event names the fields, never a value').not.toContain(secret);
}

// =============================================================================
// The simulated search
// =============================================================================

interface SimulatedSearch {
    /** Every stream answered: its query and the providers it asked. */
    streams: Array<{query: string; providers: string[]}>;
    /** What the simulation could not answer as planned: the REST fallback (aborted), a stream with no provider to carry the result. */
    problems: string[];
}

/** The provider codes a search names, as the backend reads them: repeated or comma-separated. */
function searchedProviders(url: URL): string[] {
    return url.searchParams
        .getAll('providers')
        .flatMap((value) => value.split(','))
        .map((code) => code.trim())
        .filter((code) => code !== '');
}

/**
 * Answer the asset search from a simulated server, as `AssetSearchService.search_stream` answers: one event per provider
 * asked — `UNCONFIGURED` a `provider_error` NOT_CONFIGURED, the first other provider the one 👑 result, the rest nothing —
 * then `done`. The result is checked against the generated schema. The REST search, the client's fallback for a stream it
 * cannot read, is never expected: it is aborted and recorded, so no provider is ever reached.
 */
async function simulateSearch(page: Page): Promise<SimulatedSearch> {
    const simulation: SimulatedSearch = {streams: [], problems: []};
    await page.route(
        (url) => url.pathname === SEARCH_PATH,
        async (route: Route) => {
            simulation.problems.push(`the client fell back to the REST search: ${route.request().url()}`);
            await route.abort();
        },
    );
    await page.route(
        (url) => url.pathname === SEARCH_STREAM_PATH,
        async (route: Route) => {
            if (route.request().method() !== 'GET') return route.fallback();
            const url = new URL(route.request().url());
            const query = url.searchParams.get('q') ?? '';
            const asked = searchedProviders(url);
            simulation.streams.push({query, providers: asked});
            const carrier = asked.find((code) => code !== UNCONFIGURED);
            if (carrier === undefined) simulation.problems.push(`no provider but ${UNCONFIGURED} asked, none to carry the 👑 result: ${url.search}`);
            const results = (code: string) =>
                code === carrier
                    ? [
                          schemas.FAProviderSearchResultItem.parse({
                              identifier: CROWN_IDENTIFIER,
                              identifier_type: 'TICKER',
                              display_name: `E2E Crown Fund EUR 👑 (${query})`,
                              provider_code: code,
                              currency: 'EUR',
                              asset_type: 'ETF',
                              provider_url: null,
                              provider_params: null,
                              via_web: false,
                          }),
                      ]
                    : [];
            const events: Array<Record<string, unknown>> = asked.map((code) =>
                code === UNCONFIGURED ? {event: 'provider_error', provider_code: code, error: 'A required setting has no value (simulated)', error_code: 'NOT_CONFIGURED'} : {event: 'provider_results', provider_code: code, results: results(code)},
            );
            events.push({event: 'done', total_results: carrier === undefined ? 0 : 1, providers_queried: asked, providers_with_errors: asked.filter((code) => code === UNCONFIGURED)});
            await route.fulfill({status: 200, contentType: 'text/event-stream', body: events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join('')});
        },
    );
    return simulation;
}

// =============================================================================
// 1. Settings › Plugins, read only
// =============================================================================

test.describe('Settings › Plugins — read only', () => {
    for (const {who, account} of [
        {who: 'a member', account: TEST_USER},
        {who: 'an administrator', account: TEST_ADMIN},
    ]) {
        test(`${who}: ?tab=plugins lists justETF and Borsa Italiana, each personal select on its default, never mockprov`, async ({page}) => {
            await login(page, account);
            const tab = await openPluginsTab(page);
            const asset = tab.locator('[data-testid="plugin-settings-family"][data-family="asset"]');
            await expect(asset, 'the price sources are listed').toBeVisible();

            for (const plugin of TAB_PLUGINS) {
                const form = asset.getByTestId(`plugin-settings-form-${plugin.code}`);
                await expect(form, `${plugin.code} is listed`).toBeVisible();
                await expect(form).toHaveAttribute('data-configured', 'true');
                await expect(form.getByTestId('plugin-settings-status')).toHaveAttribute('data-configured', 'true');

                const field = setting(form, plugin.key);
                await expect(field).toHaveAttribute('data-type', 'select');
                await expect(field).toHaveAttribute('data-scope', 'user');
                await expect(field, `precondition: ${account.username} keeps ${plugin.code}'s ${plugin.key} on its default`).toHaveAttribute('data-source', 'default');
                await expect(field, 'a personal field is its user’s to change').toHaveAttribute('data-editable', 'true');

                // The options, looked at and left: the list opened, then closed with Escape, nothing chosen.
                const trigger = field.getByTestId('plugin-setting-select-button');
                await trigger.click();
                const dropdown = field.getByTestId('plugin-setting-select-dropdown');
                await expect(dropdown).toBeVisible();
                await expect(dropdown.getByRole('option'), `${plugin.code} declares ${plugin.options.join(', ')}`).toHaveCount(plugin.options.length);
                for (const value of plugin.options) await expect(dropdown.getByTestId(`plugin-setting-option-${value}`)).toBeVisible();
                await expect(dropdown.getByTestId('plugin-setting-option-all'), 'the default is the option in force').toHaveAttribute('aria-selected', 'true');
                await trigger.press('Escape');
                await expect(dropdown).toBeHidden();
                await expect(field).toHaveAttribute('data-edit', '');
                await expect(form.getByTestId('plugin-settings-save'), 'nothing was chosen: nothing to save').toBeDisabled();
                await expect(form.getByTestId('plugin-settings-discard')).toBeDisabled();
            }
            // Both production forms are on show above: a test-only plugin is never listed here.
            await expect(tab.getByTestId(`plugin-settings-form-${MOCKPROV}`)).toHaveCount(0);
        });
    }
});

// =============================================================================
// 2–3. «Configure» on mockprov, from the asset dialog
// =============================================================================

test.describe('«Configure» on mockprov, from the asset dialog', () => {
    test('a member: the instance fields are read only, a number and a personal secret are saved, then put back to the default and cleared', async ({page, owned}) => {
        await login(page, TEST_USER);
        const assetId = await mockprovAsset(page, owned, TEST_USER);
        const before = await readPlugin(page.request, MOCKPROV);
        expect(before.fields.get('results_limit'), 'precondition: the member keeps no results limit of their own').toMatchObject({source: 'default', value: 10, editable: true});
        expect(before.fields.get('personal_token'), 'precondition: the member has saved no token').toMatchObject({is_set: false, editable: true});

        const {form} = await openMockprovConfigure(page, assetId);

        // The instance's fields: shown to a member, never changeable by one, with the reason.
        for (const key of SYSTEM_KEYS) {
            const row = setting(form, key);
            await expect(row).toHaveAttribute('data-scope', 'system');
            await expect(row, `precondition: no environment variable sets mockprov's ${key} on this lane`).toHaveAttribute('data-locked', 'false');
            await expect(row, `${key} is the instance's: read only for a member`).toHaveAttribute('data-editable', 'false');
            await expect(row.locator('[data-testid="plugin-setting-note"][data-note="adminOnly"]'), 'the reason: administrators only').toBeVisible();
        }
        await expect(setting(form, 'verbose').getByTestId('plugin-setting-toggle')).toBeDisabled();
        // The instance secret: only whether it is set — the administrator test may be writing it now — and no control.
        const apiKey = setting(form, 'api_key');
        await expect(apiKey.getByTestId('plugin-setting-secret-state')).toHaveAttribute('data-state', /^(set|unset)$/);
        for (const control of ['plugin-setting-secret-input', 'plugin-setting-replace', 'plugin-setting-clear']) await expect(apiKey.getByTestId(control), `no ${control} on the instance secret`).toHaveCount(0);

        // The member's own fields.
        for (const key of USER_KEYS) {
            await expect(setting(form, key)).toHaveAttribute('data-scope', 'user');
            await expect(setting(form, key), `${key} is the member's own`).toHaveAttribute('data-editable', 'true');
        }
        const limit = setting(form, 'results_limit');
        const limitInput = limit.getByTestId('plugin-setting-input');
        await expect(limit).toHaveAttribute('data-source', 'default');
        await expect(limitInput).toHaveValue('10');
        const token = setting(form, 'personal_token');
        const tokenInput = token.getByTestId('plugin-setting-secret-input');
        const tokenState = token.getByTestId('plugin-setting-secret-state');
        await expect(tokenInput, 'a secret is never prefilled').toHaveValue('');
        await expect(tokenInput, 'nor offered a saved password').toHaveAttribute('autocomplete', 'new-password');
        await expect(form.getByTestId('plugin-settings-save'), 'nothing typed yet').toBeDisabled();

        // Saved: a number and a secret.
        const secret = `e2e-token-${uniqueSuffix()}`;
        await limitInput.fill('25');
        await expect(limit).toHaveAttribute('data-edit', 'text');
        await tokenInput.fill(secret);
        await expect(token).toHaveAttribute('data-edit', 'secret');
        owned.fields.push({key: 'results_limit', scope: 'user', by: TEST_USER}, {key: 'personal_token', scope: 'user', by: TEST_USER});
        const first = await save(page, form);
        expect(first.items, 'the write: the number as a number, the secret only in secret_value').toEqual([sentItem('results_limit', 'user', {value: 25}), sentItem('personal_token', 'user', {secret_value: secret})]);
        expectSaved(first.outcome, ['results_limit', 'personal_token'], secret);

        await expect(limit, 'the limit is the member’s own now').toHaveAttribute('data-source', 'db');
        await expect(limit).toHaveAttribute('data-edit', '');
        await expect(limitInput).toHaveValue('25');
        await expect(tokenState, 'the secret reads «set», nothing more').toHaveAttribute('data-state', 'set');
        await expect(token.getByTestId('plugin-setting-replace')).toBeVisible();
        await expect(token.getByTestId('plugin-setting-secret-input'), 'the typed secret is dropped with its field').toHaveCount(0);
        const saved = await readPlugin(page.request, MOCKPROV);
        expect(saved.fields.get('results_limit')).toMatchObject({source: 'db', value: 25});
        expect(saved.fields.get('personal_token')).toMatchObject({source: 'db', is_set: true});
        expect(saved.text, 'the API never sends a secret back').not.toContain(secret);

        // Back: «Use the default» on the number, «Clear» on the secret, one save.
        await limit.getByTestId('plugin-setting-default').click();
        await expect(limit).toHaveAttribute('data-edit', 'clear');
        await expect(limit.locator('[data-testid="plugin-setting-note"][data-note="toDefault"]')).toBeVisible();
        await expect(limitInput, 'the default shows while it is pending').toHaveValue('10');
        await token.getByTestId('plugin-setting-clear').click();
        await expect(token).toHaveAttribute('data-edit', 'clear');
        await expect(tokenState).toHaveAttribute('data-state', 'clearing');
        const second = await save(page, form);
        expect(second.items, 'the write: both saved values deleted').toEqual([sentItem('results_limit', 'user', {clear: true}), sentItem('personal_token', 'user', {clear: true})]);
        expectSaved(second.outcome, ['results_limit', 'personal_token']);

        await expect(limit, 'the limit is the default again').toHaveAttribute('data-source', 'default');
        await expect(limitInput).toHaveValue('10');
        await expect(limit.getByTestId('plugin-setting-default'), 'on its default: nothing to put back').toHaveCount(0);
        await expect(token.getByTestId('plugin-setting-secret-input'), 'no token: its empty field again').toHaveValue('');
        await expect(tokenState, 'an unset secret its user may write shows its field, no state').toHaveCount(0);
        const cleared = await readPlugin(page.request, MOCKPROV);
        expect(cleared.fields.get('results_limit')).toMatchObject({source: 'default', value: 10});
        expect(cleared.fields.get('personal_token')).toMatchObject({is_set: false});
    });

    test('an administrator: the instance secret is saved, never shown again, then cleared', async ({page, owned}) => {
        await login(page, TEST_ADMIN);
        const assetId = await mockprovAsset(page, owned, TEST_ADMIN);
        const before = await readPlugin(page.request, MOCKPROV);
        expect(before.fields.get('api_key'), "precondition: neither an environment variable nor a saved value sets mockprov's api_key").toMatchObject({is_set: false, locked: false, source: 'none', editable: true});

        const {form} = await openMockprovConfigure(page, assetId);
        for (const key of SYSTEM_KEYS) await expect(setting(form, key), `an administrator writes the instance's ${key}`).toHaveAttribute('data-editable', 'true');
        const apiKey = setting(form, 'api_key');
        const keyInput = apiKey.getByTestId('plugin-setting-secret-input');
        const keyState = apiKey.getByTestId('plugin-setting-secret-state');
        await expect(apiKey).toHaveAttribute('data-source', 'none');
        await expect(keyInput, 'a secret is never prefilled').toHaveValue('');
        await expect(keyInput, 'nor offered a saved password').toHaveAttribute('autocomplete', 'new-password');

        // Saved.
        const secret = `e2e-api-key-${uniqueSuffix()}`;
        await keyInput.fill(secret);
        await expect(apiKey).toHaveAttribute('data-edit', 'secret');
        owned.fields.push({key: 'api_key', scope: 'system', by: TEST_ADMIN});
        const first = await save(page, form);
        expect(first.items, 'the write: the secret only in secret_value').toEqual([sentItem('api_key', 'system', {secret_value: secret})]);
        expectSaved(first.outcome, ['api_key'], secret);

        await expect(keyState, 'the secret reads «set», nothing more').toHaveAttribute('data-state', 'set');
        await expect(apiKey).toHaveAttribute('data-source', 'db');
        await expect(apiKey.getByTestId('plugin-setting-clear')).toBeVisible();
        await expect(apiKey.getByTestId('plugin-setting-secret-input'), 'the typed secret is dropped with its field').toHaveCount(0);
        const saved = await readPlugin(page.request, MOCKPROV);
        expect(saved.fields.get('api_key')).toMatchObject({source: 'db', is_set: true});
        expect(saved.text, 'the API never sends a secret back').not.toContain(secret);

        // «Replace» opens an empty field — the saved secret never comes back to the browser — and «Cancel» leaves it be.
        await apiKey.getByTestId('plugin-setting-replace').click();
        await expect(apiKey.getByTestId('plugin-setting-secret-input'), 'Replace opens an empty field').toHaveValue('');
        await expect(keyState, 'replacing: the field instead of the state').toHaveCount(0);
        await apiKey.getByTestId('plugin-setting-cancel-replace').click();
        await expect(keyState).toHaveAttribute('data-state', 'set');
        await expect(form.getByTestId('plugin-settings-save'), 'a cancelled replace leaves nothing to save').toBeDisabled();

        // Cleared.
        await apiKey.getByTestId('plugin-setting-clear').click();
        await expect(apiKey).toHaveAttribute('data-edit', 'clear');
        await expect(keyState).toHaveAttribute('data-state', 'clearing');
        const second = await save(page, form);
        expect(second.items, 'the write: the saved secret deleted').toEqual([sentItem('api_key', 'system', {clear: true})]);
        expectSaved(second.outcome, ['api_key']);

        await expect(apiKey, 'no value from anywhere').toHaveAttribute('data-source', 'none');
        await expect(apiKey.getByTestId('plugin-setting-secret-input'), 'unset: its empty field again').toHaveValue('');
        await expect(keyState, 'an unset secret its writer may write shows its field, no state').toHaveCount(0);
        const cleared = await readPlugin(page.request, MOCKPROV);
        expect(cleared.fields.get('api_key')).toMatchObject({source: 'none', is_set: false});
    });
});

// =============================================================================
// 4. Search: a provider to configure, and the 👑 legend
// =============================================================================

test.describe('Search — a provider to configure, and the 👑 legend', () => {
    test('NOT_CONFIGURED gives justETF a «to configure» row whose «Configure» opens its settings over the asset dialog; a 👑 result brings the legend', async ({page}) => {
        await login(page, TEST_USER);
        const simulation = await simulateSearch(page);
        await goToAssetsPage(page);
        await openCreateAssetModal(page);
        const dialog = page.getByTestId('asset-modal');
        const search = dialog.getByTestId('asset-tour-search');
        // Search Online asks only the providers it has listed: the list comes from the backend, after the dialog opens.
        await expect(search.getByTestId(`asset-search-provider-${UNCONFIGURED}`), `precondition: Search Online asks ${UNCONFIGURED}`).toHaveAttribute('data-selected', 'true', {timeout: 10_000});

        // Its input has no test id: it is the one text field of the search block.
        const query = `E2E plugin settings ${uniqueSuffix()}`;
        await search.locator('[data-search-autocomplete] input[type="text"]').fill(query);
        const results = search.getByTestId('asset-search-results');
        await expect(results, 'the search ends').toHaveAttribute('data-state', /^(results|empty|error)$/, {timeout: 15_000});
        expect(simulation.problems, 'the simulated stream answered the search').toEqual([]);
        expect(
            simulation.streams.find((stream) => stream.query === query),
            `the stream asked ${UNCONFIGURED}`,
        ).toMatchObject({providers: expect.arrayContaining([UNCONFIGURED])});
        await expect(results).toHaveAttribute('data-state', 'results');

        const row = results.locator(`[data-testid="asset-search-not-configured"][data-provider="${UNCONFIGURED}"]`);
        await expect(row, `${UNCONFIGURED} said NOT_CONFIGURED: a row says it must be configured`).toBeVisible();
        await expect(results.getByTestId('asset-search-not-configured'), 'only the provider that said so').toHaveCount(1);
        await expect(results.locator(`[data-testid^="asset-search-result-"][data-identifier="${CROWN_IDENTIFIER}"]`), 'the 👑 result is listed').toHaveCount(1);
        await expect(results.getByTestId('asset-search-crown-legend'), 'a result shows 👑: the legend says what it means').toBeVisible();

        await row.getByTestId('asset-search-configure').click();
        const modal = page.getByTestId('plugin-settings-modal');
        await expect(modal).toBeVisible();
        await expect(modal.locator(`[data-plugin="${UNCONFIGURED}"]`), `the dialog is ${UNCONFIGURED}'s`).toHaveCount(1);
        const form = modal.getByTestId(`plugin-settings-form-${UNCONFIGURED}`);
        await expect(form, `${UNCONFIGURED}'s settings are read and drawn`).toBeVisible({timeout: 10_000});
        const currency = setting(form, 'preferred_currency');
        await expect(currency).toHaveAttribute('data-source', 'default');
        await expect(currency).toHaveAttribute('data-editable', 'true');
        await expect(form.getByTestId('plugin-settings-save'), 'nothing chosen: nothing to save').toBeDisabled();

        // Closed without saving: the settings dialog goes, the asset dialog under it stays.
        await modal.getByTestId('plugin-settings-modal-close').click();
        await expect(modal).toHaveCount(0);
        await expect(dialog.getByTestId('asset-modal-form'), 'the asset dialog under it stays open').toBeVisible();
        const after = await readPlugin(page.request, UNCONFIGURED);
        expect(after.fields.get('preferred_currency'), 'nothing was written: the member’s justETF preference is still the default').toMatchObject({source: 'default', value: 'all'});
    });
});
