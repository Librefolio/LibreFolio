/**
 * «Search online» with a provider that is not configured (project 76, lot N3a): the asset dialog's search block switches
 * off the chip of a provider the list `GET /api/v1/assets/provider` says is not configured, leaves it out of every search,
 * and a touch on it opens the common window `PluginNotConfiguredModal` in the viewer's case.
 *
 * No shipped provider has a required setting, so every provider is configured on the test backend: the list is read from
 * the lane's backend and ONE real searchable entry (`justetf`) is rewritten as not configured (`page.route`, the page's
 * own): nothing is written to any setting, no environment variable is set. The search stream is simulated too, as in
 * `settings/plugin-settings.spec.ts`: every provider asked answers nothing, the REST fallback is aborted, so no
 * third-party source is ever reached and the providers each search named are recorded.
 *
 * Three cases:
 *   1. a member, a value to set (`missing_member`): the chip is off, out of the search, kept in its place; the window
 *      names the plugin, links the read-only Settings › Plugins in a new tab and offers no «Configure»; Close closes it;
 *   2. an administrator, a value to set (`missing_admin`): «Configure» swaps the window for that plugin's settings
 *      dialog; nothing is saved (the provider's real settings are shared) and no write is sent;
 *   3. an administrator, the managed profile (`invalid_locked_setting` naming no variable, `managed`): no button in the
 *      window; Escape closes it.
 *
 * Assertions read test ids, `data-*` and `aria-*` only, never a translated text. Nothing is written: the file runs in
 * parallel (the config's default). Both projects.
 *
 * Prerequisites: test users (`e2e_test_user` a member, `e2e_test_admin` an administrator); justETF listed by the backend
 * as a configured search provider.
 */
import type {Request, Route} from '@playwright/test';
import {schemas} from '../../src/lib/api/generated';
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_ADMIN, TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';
import {goToAssetsPage, openCreateAssetModal} from './assets-helpers';

const API = '/api/v1';
const PROVIDER_LIST_PATH = `${API}/assets/provider`;
const SEARCH_STREAM_PATH = `${API}/assets/provider/search/stream`;
const SEARCH_PATH = `${API}/assets/provider/search`;
const SETTINGS_BULK_PATH = `${API}/settings/plugins/bulk`;

/** The real searchable provider the simulated list reports not configured. */
const UNCONFIGURED = 'justetf';
/** The search component never shows the test-only provider (`AssetSearchAutocomplete.readProviders`). */
const HIDDEN = 'mockprov';

type ProviderEntry = ReturnType<typeof schemas.FAProviderInfo.parse>;
type Readiness = Pick<ProviderEntry, 'missing_settings' | 'missing_reason' | 'invalid_variables'>;

/** A value to set: justETF's own personal select, a real undotted key (no group to read for its label). */
const MISSING_FIELDS: Readiness = {missing_settings: ['preferred_currency'], missing_reason: 'missing_fields', invalid_variables: []};
/** The managed profile: an invalid locked setting that names no variable (decision N2b). */
const MANAGED: Readiness = {missing_settings: [], missing_reason: 'invalid_locked_setting', invalid_variables: []};

// Sign-in, the assets page in two waves, the dialog and its provider list share the budget.
test.setTimeout(60_000);

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
});
