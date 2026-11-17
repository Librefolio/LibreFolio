/**
 * A provider that is not configured, in the asset dialog (project 76, lots N3a and N3b). N3a: the search block switches off
 * the chip of a provider the list `GET /api/v1/assets/provider` says is not configured, leaves it out of every search, and
 * a touch on it opens the common window `PluginNotConfiguredModal` in the viewer's case. N3b: the provider panel's select
 * switches off that provider's option the same way — choosing it opens the window and never changes the provider — except
 * for the provider saved on the asset, which stays choosable and shows the warning on its «Configure».
 *
 * No shipped provider has a required setting, so every provider is configured on the test backend: the list is read from
 * the lane's backend and ONE real searchable entry (`justetf`) is rewritten as not configured (`page.route`, the page's
 * own): nothing is written to any setting, no environment variable is set. The search stream is simulated too, as in
 * `settings/plugin-settings.spec.ts`: every provider asked answers nothing, the REST fallback is aborted, so no
 * third-party source is ever reached and the providers each search named are recorded.
 *
 * Five cases:
 *   1. a member, a value to set (`missing_member`): the chip is off, out of the search, kept in its place; the window
 *      names the plugin, links the read-only Settings › Plugins in a new tab and offers no «Configure»; Close closes it;
 *   2. an administrator, a value to set (`missing_admin`): «Configure» swaps the window for that plugin's settings
 *      dialog; nothing is saved (the provider's real settings are shared) and no write is sent;
 *   3. an administrator, the managed profile (`invalid_locked_setting` naming no variable, `managed`): no button in the
 *      window; Escape closes it;
 *   4. a member, a new asset, the provider select (N3b): the option is off, reachable, never chosen; choosing it opens the
 *      window and leaves the selection as it was;
 *   5. a member, an asset whose saved provider is the patched one (N3b): its option stays choosable, «Configure» carries
 *      the warning, the old text badge is gone.
 *
 * Assertions read test ids, `data-*` and `aria-*` only, never a translated text. Cases 1–4 write nothing; case 5 creates
 * its own asset through the API (justETF assigned with an ISIN before anything is patched), never saves the dialog, keeps
 * the detail page's price sync off the network (`POST /assets/prices/sync` answered empty) and deletes the asset after the
 * test, whatever happened. The file runs in parallel (the config's default). Both projects.
 *
 * Prerequisites: test users (`e2e_test_user` a member, `e2e_test_admin` an administrator); justETF listed by the backend
 * as a configured search provider.
 */
import type {APIRequestContext, Request, Route} from '@playwright/test';
import {schemas} from '../../src/lib/api/generated';
import {expect, test as base, type Locator, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_ADMIN, TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';
import {goToAssetDetailPage, goToAssetsPage, openCreateAssetModal, openEditAssetModal} from './assets-helpers';

const API = '/api/v1';
const PROVIDER_LIST_PATH = `${API}/assets/provider`;
const SEARCH_STREAM_PATH = `${API}/assets/provider/search/stream`;
const SEARCH_PATH = `${API}/assets/provider/search`;
const SETTINGS_BULK_PATH = `${API}/settings/plugins/bulk`;
const PRICES_SYNC_PATH = `${API}/assets/prices/sync`;
const PROBE_PATH = `${API}/assets/provider/probe`;

/** The real searchable provider the simulated list reports not configured. */
const UNCONFIGURED = 'justetf';
/** The search component never shows the test-only provider (`AssetSearchAutocomplete.readProviders`). */
const HIDDEN = 'mockprov';
/** A syntactically valid ISIN (check digit included) for the justETF assignment; nothing ever asks justETF about it. */
const JUSTETF_ISIN = 'IE00B4L5Y983';

type ProviderEntry = ReturnType<typeof schemas.FAProviderInfo.parse>;
type Readiness = Pick<ProviderEntry, 'missing_settings' | 'missing_reason' | 'invalid_variables'>;

/** A value to set: justETF's own personal select, a real undotted key (no group to read for its label). */
const MISSING_FIELDS: Readiness = {missing_settings: ['preferred_currency'], missing_reason: 'missing_fields', invalid_variables: []};
/** The managed profile: an invalid locked setting that names no variable (decision N2b). */
const MANAGED: Readiness = {missing_settings: [], missing_reason: 'invalid_locked_setting', invalid_variables: []};

// Sign-in, the assets page in two waves, the dialog and its provider list share the budget.
base.setTimeout(60_000);

interface Simulation {
    /** The provider list as the backend answered it, before the patch: the order and the default-searched set. */
    real: ProviderEntry[] | null;
    /** Every simulated search stream: its query and the providers it named. */
    streams: Array<{query: string; providers: string[]}>;
    /** What could not go as planned: the REST fallback reached, the patched entry missing from the real list. */
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
 * Route the page's provider list and asset search. The list is the lane's real answer with `UNCONFIGURED`'s entry
 * rewritten as not configured (`readiness`), the rest untouched and every entry checked against the generated schema; the
 * search stream answers every provider asked with nothing, then `done`; the REST search is aborted and recorded.
 */
async function simulate(page: Page, readiness: Readiness): Promise<Simulation> {
    const simulation: Simulation = {real: null, streams: [], problems: []};
    await page.route(
        (url) => url.pathname === PROVIDER_LIST_PATH,
        async (route: Route) => {
            // POST on the same path assigns a provider: never this test's, and never rewritten.
            if (route.request().method() !== 'GET') return route.fallback();
            const response = await route.fetch();
            const entries = ((await response.json()) as unknown[]).map((entry) => schemas.FAProviderInfo.parse(entry));
            simulation.real = entries;
            const target = entries.find((entry) => entry.code === UNCONFIGURED);
            if (!target?.supports_search || target.configured === false) {
                simulation.problems.push(`precondition: the backend lists ${UNCONFIGURED} as a configured search provider: ${JSON.stringify(target)}`);
            }
            const patched = entries.map((entry) => (entry.code === UNCONFIGURED ? schemas.FAProviderInfo.parse({...entry, configured: false, ...readiness}) : entry));
            await route.fulfill({response, json: patched});
        },
    );
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
            const asked = searchedProviders(url);
            simulation.streams.push({query: url.searchParams.get('q') ?? '', providers: asked});
            const events: Array<Record<string, unknown>> = asked.map((code) => ({event: 'provider_results', provider_code: code, results: []}));
            events.push({event: 'done', total_results: 0, providers_queried: asked, providers_with_errors: []});
            await route.fulfill({status: 200, contentType: 'text/event-stream', body: events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join('')});
        },
    );
    return simulation;
}

/**
 * Sign in, open «Add Asset» and return its search block once the patched list has landed: the switched-off chip is drawn,
 * and a configured chip is drawn selected beside it (the presence barrier for every absence asserted after).
 */
async function openSearch(page: Page, account: {username: string; password: string}, readiness: Readiness): Promise<{simulation: Simulation; search: Locator; chip: Locator}> {
    await login(page, account);
    const simulation = await simulate(page, readiness);
    await goToAssetsPage(page);
    await openCreateAssetModal(page);
    const search = page.getByTestId('asset-modal').getByTestId('asset-tour-search');
    const chip = search.getByTestId(`asset-search-provider-${UNCONFIGURED}`);
    await expect(chip, `the list says ${UNCONFIGURED} is not configured: its chip is switched off`).toHaveAttribute('data-configured', 'false', {timeout: 10_000});
    await expect(chip).toHaveAttribute('aria-disabled', 'true');
    await expect(chip, 'never selected').toHaveAttribute('data-selected', 'false');
    await expect(search.locator('[data-testid^="asset-search-provider-"][data-configured="true"][data-selected="true"]').first(), 'the configured providers are drawn, selected').toBeVisible();
    expect(simulation.problems, 'the list was read from the backend and patched as planned').toEqual([]);
    return {simulation, search, chip};
}

/**
 * Touch the switched-off chip: the common window, once it is drawn. The chip is `aria-disabled` on purpose — reachable, so
 * a touch can say why — and Playwright reads `aria-disabled` as «not enabled», so the click is forced; the window open
 * right after is the proof it landed on the chip.
 */
async function openWindow(page: Page, chip: Locator): Promise<Locator> {
    // Forced, so the hit-target check is skipped: prove first that the chip is on screen, whole.
    await chip.scrollIntoViewIfNeeded();
    await expect(chip).toBeInViewport({ratio: 1});
    await chip.click({force: true});
    const modal = page.getByTestId('plugin-not-configured-modal');
    await expect(modal).toBeVisible({timeout: 5_000});
    await expect(modal).toHaveAttribute('data-plugin', UNCONFIGURED);
    return modal;
}

type Account = {username: string; password: string};

/** An asset a test created, with the account that created it: deleted after the test, whatever happened. */
interface OwnedAsset {
    id: number;
    by: Account;
}

/**
 * Delete the assets a test recorded, on a session of their own per account (the page's may be gone): every deletion is
 * tried whatever happened to the previous one, every failure is returned, named.
 */
async function deleteOwned(page: Page, owned: OwnedAsset[], open: () => Promise<APIRequestContext>): Promise<string[]> {
    const failures: string[] = [];
    if (owned.length === 0) return failures;
    // Off the page first: nothing still on screen reads the asset while it goes.
    await page.goto('about:blank').catch((error) => failures.push(`leave the page: ${String(error)}`));
    const accounts = new Map(owned.map(({by}) => [by.username, by]));
    for (const account of accounts.values()) {
        let api: APIRequestContext | null = null;
        try {
            api = await open();
            const signedIn = await api.post(`${API}/auth/login`, {data: {username: account.username, password: account.password}});
            expect(signedIn.ok(), `POST ${API}/auth/login as ${account.username}: HTTP ${signedIn.status()}`).toBe(true);
            for (const asset of owned.filter(({by}) => by.username === account.username)) {
                try {
                    const answer = await api.delete(`${API}/assets`, {params: {asset_ids: asset.id}});
                    const body = (await answer.json().catch(() => null)) as {results?: Array<{asset_id: number; success: boolean}>} | null;
                    expect(answer.ok(), `DELETE ${API}/assets?asset_ids=${asset.id}: HTTP ${answer.status()} ${JSON.stringify(body)}`).toBe(true);
                    expect(body?.results?.find((result) => result.asset_id === asset.id)?.success, `asset ${asset.id} deleted: ${JSON.stringify(body)}`).toBe(true);
                } catch (error) {
                    failures.push(`${account.username} deletes asset ${asset.id}: ${String(error)}`);
                }
            }
        } catch (error) {
            failures.push(`${account.username} cannot sign in for the clean-up: ${String(error)}`);
        } finally {
            await api?.dispose().catch(() => undefined);
        }
    }
    return failures;
}

const test = base.extend<{owned: OwnedAsset[]}>({
    owned: async ({page, playwright, baseURL}, use) => {
        const owned: OwnedAsset[] = [];
        let failures: string[] = [];
        try {
            await use(owned);
        } finally {
            failures = await deleteOwned(page, owned, () => playwright.request.newContext({baseURL}));
        }
        expect(failures, 'the clean-up deletes every asset the test created').toEqual([]);
    },
});

/**
 * A plain asset of the signed-in account with justETF assigned, through the API: recorded in `owned` as soon as the create
 * names it. The real list says justETF is configured, so the assignment is accepted (N2 refuses only a provider that is
 * not); it reaches no third party (no probe, no fetch).
 */
async function justetfAsset(page: Page, owned: OwnedAsset[], by: Account): Promise<number> {
    const name = `E2E not configured saved ${uniqueSuffix()}`;
    const created = await page.request.post(`${API}/assets`, {data: [schemas.FAAssetCreateItem.parse({display_name: name, currency: 'EUR', asset_type: 'ETF'})]});
    const body = (await created.json().catch(() => null)) as {results?: Array<{asset_id?: number | null; display_name?: string; success?: boolean}>} | null;
    const result = body?.results?.find((entry) => entry.display_name === name);
    if (typeof result?.asset_id === 'number') owned.push({id: result.asset_id, by});
    expect(created.status(), `POST ${API}/assets creates "${name}": ${JSON.stringify(body)}`).toBe(201);
    if (!result?.success || typeof result.asset_id !== 'number') throw new Error(`"${name}" was not created: ${JSON.stringify(body)}`);
    const assetId = result.asset_id;

    const assignment = schemas.FAProviderAssignmentItem.parse({asset_id: assetId, provider_code: UNCONFIGURED, identifier: JUSTETF_ISIN, identifier_type: 'ISIN', provider_params: null});
    const assigned = await page.request.post(PROVIDER_LIST_PATH, {data: [assignment]});
    const assignedBody = (await assigned.json().catch(() => null)) as {results?: Array<{asset_id: number; success: boolean}>} | null;
    expect(assigned.ok(), `POST ${PROVIDER_LIST_PATH}: HTTP ${assigned.status()} ${JSON.stringify(assignedBody)}`).toBe(true);
    expect(assignedBody?.results?.find((entry) => entry.asset_id === assetId)?.success, `${UNCONFIGURED} assigned: ${JSON.stringify(assignedBody)}`).toBe(true);
    return assetId;
}

/**
 * Keep the asset detail page off the network: its mount syncs the asset's prices, which for a justETF asset would ask
 * justETF. The sync is answered empty (a valid `FABulkRefreshResponse`), a provider probe is refused; both are recorded.
 */
async function keepOffline(page: Page): Promise<{syncs: number; probes: number}> {
    const calls = {syncs: 0, probes: 0};
    await page.route(
        (url) => url.pathname === PRICES_SYNC_PATH,
        async (route: Route) => {
            calls.syncs += 1;
            await route.fulfill({status: 200, json: schemas.FABulkRefreshResponse.parse({results: [], success_count: 0})});
        },
    );
    await page.route(
        (url) => url.pathname === PROBE_PATH,
        async (route: Route) => {
            calls.probes += 1;
            await route.abort();
        },
    );
    return calls;
}

/** The asset dialog's provider panel, expanded (a click on its header only when it is not already). */
async function expandProviderPanel(page: Page): Promise<void> {
    const header = page.getByTestId('asset-modal-provider-header');
    await expect(header).toBeVisible();
    if ((await header.getAttribute('data-expanded')) !== 'true') await header.click();
    await expect(header).toHaveAttribute('data-expanded', 'true');
}

/** Open the provider select: its dropdown, once the patched provider's option is drawn in it. */
async function openProviderSelect(page: Page): Promise<Locator> {
    const trigger = page.getByTestId('provider-code-select-button');
    await expect(trigger).toBeEnabled({timeout: 10_000});
    await trigger.click();
    await expect(trigger).toHaveAttribute('aria-expanded', 'true');
    const dropdown = page.getByTestId('provider-code-select-dropdown');
    await expect(dropdown.getByTestId(`provider-option-${UNCONFIGURED}`)).toBeVisible({timeout: 10_000});
    return dropdown;
}

/** The test ids of the options the select marks selected (none, or one). */
async function selectedOptions(dropdown: Locator): Promise<Array<string | null>> {
    return dropdown.locator('[data-testid^="provider-option-"][aria-selected="true"]').evaluateAll((elements) => elements.map((element) => element.getAttribute('data-testid')));
}

/** A configured provider the select offers: any real entry but the patched one and the hidden test-only one. */
function configuredSibling(simulation: Simulation): string {
    const sibling = (simulation.real ?? []).find((entry) => entry.code !== UNCONFIGURED && entry.code !== HIDDEN && entry.configured !== false);
    if (!sibling) throw new Error(`precondition: the backend lists a configured provider other than ${UNCONFIGURED}: ${JSON.stringify(simulation.real)}`);
    return sibling.code;
}

test.describe('Search online — a provider that is not configured', () => {
    test('a member: the chip is off, kept in place and out of the search; its window links Settings › Plugins, no «Configure»', async ({page}) => {
        const {simulation, search, chip} = await openSearch(page, TEST_USER, MISSING_FIELDS);

        // Kept in its place: the chips in the order of the backend's list, the switched-off one among them.
        const real = simulation.real ?? [];
        const expectedOrder = real.filter((entry) => entry.supports_search && entry.code !== HIDDEN).map((entry) => `asset-search-provider-${entry.code}`);
        const chips = search.locator('[data-testid^="asset-search-provider-"]');
        await expect(chips).toHaveCount(expectedOrder.length);
        expect(await chips.evaluateAll((elements) => elements.map((element) => element.getAttribute('data-testid'))), 'the chip order is the list order, the switched-off chip in its place').toEqual(expectedOrder);

        // A search names every other default provider, never the switched-off one.
        const query = `E2E not configured ${uniqueSuffix()}`;
        const streamed = page.waitForRequest((request: Request) => new URL(request.url()).pathname === SEARCH_STREAM_PATH && new URL(request.url()).searchParams.get('q') === query, {timeout: 15_000});
        streamed.catch(() => undefined);
        await search.locator('[data-search-autocomplete] input[type="text"]').fill(query);
        const asked = searchedProviders(new URL((await streamed).url()));
        const expectedAsked = real.filter((entry) => entry.supports_search && entry.code !== HIDDEN && entry.code !== UNCONFIGURED && entry.configured !== false).map((entry) => entry.code);
        expect(asked.length, 'the search asked the configured providers').toBeGreaterThan(0);
        expect(asked, `the search never names ${UNCONFIGURED}`).not.toContain(UNCONFIGURED);
        expect([...asked].sort(), 'every configured searchable provider, selected by default, is asked').toEqual([...expectedAsked].sort());
        const results = search.getByTestId('asset-search-results');
        await expect(results, 'the simulated search ends, with nothing found').toHaveAttribute('data-state', 'empty', {timeout: 15_000});
        expect(simulation.problems, 'the simulated stream answered the search').toEqual([]);
        await expect(chip, 'a search leaves the chip off').toHaveAttribute('data-selected', 'false');

        // The results list is drawn below the chips, in the flow: the forced touch below lands on the chip.
        const streamsBefore = simulation.streams.length;
        const modal = await openWindow(page, chip);
        await expect(modal).toHaveAttribute('data-case', 'missing_member');
        await expect(modal.getByTestId('plugin-not-configured-message')).toHaveAttribute('data-variant', 'warning');
        const link = modal.getByTestId('plugin-not-configured-settings-link');
        await expect(link, 'a member is sent to the read-only settings').toBeVisible();
        await expect(link).toHaveAttribute('href', '/settings/plugins');
        await expect(link, 'in a new tab: the open dialog underneath is kept').toHaveAttribute('target', '_blank');
        await expect(modal.getByTestId('plugin-not-configured-close')).toBeVisible();
        await expect(modal.getByTestId('plugin-not-configured-configure'), 'a member cannot configure').toHaveCount(0);
        expect(simulation.streams.length, 'the touch searched nothing').toBe(streamsBefore);

        await modal.getByTestId('plugin-not-configured-close').click();
        await expect(modal).toHaveCount(0);
        await expect(page.getByTestId('asset-modal-form'), 'the asset dialog underneath stays open').toBeVisible();
        await expect(chip, 'closing leaves the chip off').toHaveAttribute('data-selected', 'false');
    });

    test('an administrator, a value to set: «Configure» opens the plugin’s settings; closed, nothing saved', async ({page}) => {
        const writes: string[] = [];
        page.on('request', (request) => {
            if (request.method() === 'PATCH' && new URL(request.url()).pathname === SETTINGS_BULK_PATH) writes.push(request.url());
        });
        const {chip} = await openSearch(page, TEST_ADMIN, MISSING_FIELDS);

        const modal = await openWindow(page, chip);
        await expect(modal).toHaveAttribute('data-case', 'missing_admin');
        await expect(modal.getByTestId('plugin-not-configured-message')).toHaveAttribute('data-variant', 'warning');
        const configure = modal.getByTestId('plugin-not-configured-configure');
        await expect(configure, 'an administrator can set the value').toBeVisible();
        await expect(modal.getByTestId('plugin-not-configured-close')).toBeVisible();
        await expect(modal.getByTestId('plugin-not-configured-settings-link'), 'no link: the settings are one click away').toHaveCount(0);

        await configure.click();
        const settings = page.getByTestId('plugin-settings-modal');
        await expect(settings).toBeVisible({timeout: 5_000});
        await expect(modal, '«Configure» swaps the window for the settings').toHaveCount(0);
        await expect(settings.locator(`[data-plugin="${UNCONFIGURED}"]`), `the dialog is ${UNCONFIGURED}'s`).toHaveCount(1);
        const form = settings.getByTestId(`plugin-settings-form-${UNCONFIGURED}`);
        await expect(form, `${UNCONFIGURED}'s settings are read and drawn`).toBeVisible({timeout: 10_000});
        await expect(form.getByTestId('plugin-settings-save'), 'nothing chosen: nothing to save').toBeDisabled();

        // Closed without saving: the provider's real settings are shared with every other spec.
        await settings.getByTestId('plugin-settings-modal-close').click();
        await expect(settings).toHaveCount(0);
        await expect(page.getByTestId('plugin-not-configured-modal')).toHaveCount(0);
        await expect(page.getByTestId('asset-modal-form'), 'the asset dialog underneath stays open').toBeVisible();
        await expect(chip, 'nothing saved: the chip stays off').toHaveAttribute('data-configured', 'false');
        expect(writes, 'no settings write was sent').toEqual([]);
    });

    test('an administrator, the managed profile: the window has no button; Escape closes it', async ({page}) => {
        const {chip} = await openSearch(page, TEST_ADMIN, MANAGED);

        const modal = await openWindow(page, chip);
        await expect(modal).toHaveAttribute('data-case', 'managed');
        const message = modal.getByTestId('plugin-not-configured-message');
        await expect(message, 'the window says why').toBeVisible();
        await expect(message).toHaveAttribute('data-variant', 'error');
        // The message is drawn above: the window is whole, and it has nothing to press.
        await expect(modal.locator('button'), 'the managed profile offers nothing to do').toHaveCount(0);
        await expect(modal.getByTestId('plugin-not-configured-settings-link')).toHaveCount(0);

        await page.keyboard.press('Escape');
        await expect(modal).toHaveCount(0);
        await expect(page.getByTestId('asset-modal-form'), 'Escape closes only the window: the asset dialog stays').toBeVisible();
        await expect(chip).toHaveAttribute('data-configured', 'false');
    });

    test('a member, a new asset: the provider select switches the option off; choosing it opens the window, the selection stays', async ({page}) => {
        const {simulation} = await openSearch(page, TEST_USER, MISSING_FIELDS);
        await expandProviderPanel(page);
        const dropdown = await openProviderSelect(page);

        // The presence barrier: a configured option is drawn, choosable, beside the switched-off one.
        const sibling = dropdown.getByTestId(`provider-option-${configuredSibling(simulation)}`);
        await expect(sibling, 'a configured provider is choosable').toHaveAttribute('data-needs-setup', 'false');
        await expect(sibling).toHaveAttribute('aria-disabled', 'false');
        const option = dropdown.getByTestId(`provider-option-${UNCONFIGURED}`);
        await expect(option, `the list says ${UNCONFIGURED} is not configured: its option is switched off`).toHaveAttribute('data-needs-setup', 'true');
        await expect(option).toHaveAttribute('aria-disabled', 'true');
        await expect(option, 'switched off, not disabled: reachable, so choosing it can say why').toHaveJSProperty('disabled', false);
        await expect(option, 'never selected').toHaveAttribute('aria-selected', 'false');
        const before = await selectedOptions(dropdown);

        const modal = await openWindow(page, option);
        await expect(modal).toHaveAttribute('data-case', 'missing_member');
        await expect(dropdown, 'choosing it closes the list').toHaveCount(0);
        await modal.getByTestId('plugin-not-configured-close').click();
        await expect(modal).toHaveCount(0);
        await expect(page.getByTestId('asset-modal-form'), 'the asset dialog underneath stays open').toBeVisible();

        // The selection is what it was: the option was reached, never chosen.
        const reopened = await openProviderSelect(page);
        await expect(reopened.getByTestId(`provider-option-${UNCONFIGURED}`), 'still not selected').toHaveAttribute('aria-selected', 'false');
        await expect(reopened.getByTestId(`provider-option-${UNCONFIGURED}`), 'still switched off').toHaveAttribute('data-needs-setup', 'true');
        expect(await selectedOptions(reopened), 'the selection is unchanged').toEqual(before);
        await page.getByTestId('provider-code-select-button').click();
        await expect(reopened).toHaveCount(0);
        expect(simulation.problems, 'the list was patched as planned').toEqual([]);
    });

    test('a member, the asset’s saved provider is not configured: its option stays choosable, «Configure» carries the warning', async ({page, owned}) => {
        await login(page, TEST_USER);
        // Assigned before anything is patched: the list route only rewrites GET, the assignment is a POST on the same path.
        const assetId = await justetfAsset(page, owned, TEST_USER);
        const offline = await keepOffline(page);
        const simulation = await simulate(page, MISSING_FIELDS);

        await goToAssetDetailPage(page, String(assetId));
        await openEditAssetModal(page);
        // The edit data is in: an asset with a provider opens its provider panel by itself (AssetModal, populateFromEditData).
        await expect(page.getByTestId('asset-modal-form')).toHaveAttribute('data-snapshot-ready', 'true', {timeout: 10_000});
        await expandProviderPanel(page);

        // The proof the patched list reached this panel: «Configure» says the saved provider needs setting up.
        const configure = page.getByTestId('provider-configure');
        await expect(configure, `${UNCONFIGURED} is saved on the asset and not configured: «Configure» says so`).toHaveAttribute('data-configured', 'false', {timeout: 10_000});
        await expect(configure.getByTestId('provider-configure-warning'), 'the yellow triangle on «Configure»').toBeVisible();
        await expect(page.getByTestId('provider-settings-status'), 'no text badge on an editable panel').toHaveCount(0);

        const dropdown = await openProviderSelect(page);
        const option = dropdown.getByTestId(`provider-option-${UNCONFIGURED}`);
        await expect(option, 'the saved provider is never switched off').toHaveAttribute('data-needs-setup', 'false');
        await expect(option).toHaveAttribute('aria-disabled', 'false');
        await expect(option, 'it is the selection').toHaveAttribute('aria-selected', 'true');
        await page.getByTestId('provider-code-select-button').click();
        await expect(dropdown).toHaveCount(0);

        // Closed without saving: the provider and its settings are left as they are.
        await page.getByTestId('asset-modal-cancel').click();
        await expect(page.getByTestId('asset-modal-form')).toHaveCount(0);
        expect(simulation.problems, 'the list was patched as planned').toEqual([]);
        expect(offline.probes, 'nothing probed the provider').toBe(0);
    });
});
