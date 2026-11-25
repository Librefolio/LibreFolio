/**
 * An FX provider that is not configured, in the FX pair dialog's route picker (project 76, lot N3c). A provider the list
 * `GET /api/v1/fx/providers` says is not configured switches off every route through it: the row is reachable
 * (`aria-disabled`, not `disabled`), a touch opens the common window `PluginNotConfiguredModal` and never adds the route.
 * In edit mode a provider the pair's saved routes already use is never switched off, and a saved route through it shows
 * a triangle that opens the same window.
 *
 * No shipped FX provider has a required setting, so every provider is configured on the test backend: the list is the
 * lane's real answer with ONE real provider (`BOE`, whose currency list is static in its plugin) rewritten as not
 * configured, through the page's own `page.route`; nothing is written to any setting, no environment variable is set.
 * The provider, the pair of case 1 and the premises of case 2 are read from the real list (`page.request`, which the
 * page's routes never touch), never assumed.
 *
 * Two cases (the runner runs the `desktop` project; both are written for `mobile` too):
 *   1. a new pair (a member) with no saved route: the direct route through the patched provider is switched off, a route
 *      through another (direct when one serves the pair, else a 2-step chain) is not; a touch on it opens the window
 *      (`missing_member`) and adds nothing; a chain through it is switched off too. The dialog is never saved.
 *   2. a pair whose saved route goes through the patched provider (a member): the saved row carries the triangle, which
 *      opens the window; the picker's chains through that provider stay on (the pair already uses it). Never saved.
 *
 * FX routes are global (no `user_id`), so case 2 owns its pair: one per project (a run of both projects runs it twice at
 * the same time), on currencies no seed row and no other spec uses, verified empty (no route, no rate) before anything
 * is written, created through the API before the page loads, and deleted after the test whatever happened. The detail page's sync is
 * answered by the test (aborted, counted: none expected), so the bank is never asked. Assertions read test ids, `data-*`
 * and `aria-*` only, never a translated text. The file runs in parallel (the config's default).
 *
 * Prerequisites: test user `e2e_test_user` (a member); BOE listed by the backend as a configured provider with GBP as a
 * base, CNY and DKK among its targets.
 */
import type {Route} from '@playwright/test';
import {schemas} from '../../src/lib/api/generated';
import {expect, test as base, type Locator, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToFxDetailPage, goToFxPage, openAddPairModal, selectCurrency} from './fx-helpers';

const API = '/api/v1';
const PROVIDER_LIST_PATH = `${API}/fx/providers`;
const ROUTES_PATH = `${API}/fx/providers/routes`;
const SYNC_PATH = `${API}/fx/currencies/sync`;

/** The real provider the simulated list reports not configured: a static currency list (BOE plugin), so the premises hold. */
const UNCONFIGURED = 'BOE';
/** A value to set, the shape the backend gives a provider with a required setting left empty (N1, N2b). */
const MISSING_FIELDS = {configured: false, missing_settings: ['api_key'], missing_reason: 'missing_fields', invalid_variables: []};

/**
 * Case 2's pair, one per project: both run at the same time against the same global table. Neither currency appears in
 * `populate_mock_data.py` nor in another spec's pairs (checked 2026-11-17); the test still verifies the pair is empty.
 */
const OWNED_PAIR: Record<string, readonly [string, string]> = {desktop: ['CNY', 'GBP'], mobile: ['DKK', 'GBP']};

// Sign-in, the FX page in two waves, the dialog and the provider list share the budget.
base.setTimeout(60_000);

type ProviderEntry = ReturnType<typeof schemas.FXProviderInfo.parse>;

/** The real provider list, as the lane's backend answers it to the signed-in user (not routed: `page.request`). */
async function realProviders(page: Page): Promise<ProviderEntry[]> {
    const response = await page.request.get(PROVIDER_LIST_PATH);
    expect(response.ok(), `GET ${PROVIDER_LIST_PATH}: HTTP ${response.status()}`).toBe(true);
    return ((await response.json()) as unknown[]).map((entry) => schemas.FXProviderInfo.parse(entry));
}

/** The providers that convert `a` to `b` in one step, either way round, as the picker's graph reads them. */
function directProviders(list: ProviderEntry[], a: string, b: string): string[] {
    return list
        .filter((p) => p.code !== 'MANUAL' && !p.currencies_unavailable)
        .filter((p) => {
            const targets = p.target_currencies ?? [];
            return (p.base_currencies.includes(a) && targets.includes(b)) || (p.base_currencies.includes(b) && targets.includes(a));
        })
        .map((p) => p.code);
}

/** The patched provider as the real list gives it: present, configured, with its currency list. */
function patchedEntry(list: ProviderEntry[]): ProviderEntry {
    const entry = list.find((p) => p.code === UNCONFIGURED);
    if (!entry || entry.configured === false || entry.currencies_unavailable || (entry.target_currencies ?? []).length === 0) {
        throw new Error(`precondition: the backend lists ${UNCONFIGURED} as a configured FX provider with its currencies: ${JSON.stringify(entry ?? null)}`);
    }
    return entry;
}

/** Whether a 2-step chain from `a` to `b` goes through the patched provider on one of its legs. */
function hasChainThroughPatched(list: ProviderEntry[], a: string, b: string): boolean {
    const currencies = new Set(list.flatMap((p) => [...p.base_currencies, ...(p.target_currencies ?? [])]));
    return [...currencies].some((via) => {
        if (via === a || via === b) return false;
        const first = directProviders(list, a, via);
        const second = directProviders(list, via, b);
        return (first.includes(UNCONFIGURED) && second.length > 0) || (second.includes(UNCONFIGURED) && first.length > 0);
    });
}

/** Whether a 2-step chain from `a` to `b` exists with neither leg through the patched provider. */
function hasChainAvoidingPatched(list: ProviderEntry[], a: string, b: string): boolean {
    const others = list.filter((p) => p.code !== UNCONFIGURED);
    const currencies = new Set(others.flatMap((p) => [...p.base_currencies, ...(p.target_currencies ?? [])]));
    return [...currencies].some((via) => via !== a && via !== b && directProviders(others, a, via).length > 0 && directProviders(others, via, b).length > 0);
}

/** A 2-step chain of the open picker with neither leg through the patched provider, once drawn (its group opened when not already). */
async function chainAvoidingPatched(picker: Locator): Promise<Locator> {
    const toggle = picker.getByTestId('fx-route-chain-toggle-2');
    await expect(toggle, 'a 2-step chain group is drawn').toBeVisible({timeout: 10_000});
    if ((await toggle.getAttribute('data-expanded')) !== 'true') await toggle.click();
    await expect(toggle).toHaveAttribute('data-expanded', 'true');
    const row = picker.getByTestId('fx-route-chain-section-2').locator(`[data-route-key]:not([data-route-key*=":${UNCONFIGURED}|"]):not([data-route-key$=":${UNCONFIGURED}"])`).first();
    await expect(row, `a 2-step chain avoiding ${UNCONFIGURED} is drawn`).toBeVisible({timeout: 10_000});
    return row;
}

/**
 * Route the page's provider list: the real answer, the patched provider rewritten as not configured, every other entry
 * untouched. Every GET is patched — the picker reads the list again when it mounts. Returns how many lists were patched.
 */
async function patchProviderList(page: Page): Promise<{patched: number; problems: string[]}> {
    const state = {patched: 0, problems: [] as string[]};
    await page.route(
        (url) => url.pathname === PROVIDER_LIST_PATH,
        async (route: Route) => {
            if (route.request().method() !== 'GET') return route.fallback();
            const response = await route.fetch();
            const entries = (await response.json()) as Array<Record<string, unknown>>;
            if (!entries.some((entry) => entry.code === UNCONFIGURED)) state.problems.push(`${UNCONFIGURED} missing from the real list`);
            const patched = entries.map((entry) => (entry.code === UNCONFIGURED ? {...entry, ...MISSING_FIELDS} : entry));
            // The rewritten list must still be one the client accepts.
            patched.forEach((entry) => schemas.FXProviderInfo.parse(entry));
            state.patched += 1;
            await route.fulfill({response, json: patched});
        },
    );
    return state;
}

/** The route picker of the open dialog, expanded (a click on its toggle only when it is not already open). */
async function openPicker(dialog: Locator): Promise<Locator> {
    const toggle = dialog.getByTestId('fx-route-picker-toggle');
    await expect(toggle).toBeVisible({timeout: 10_000});
    if ((await toggle.getAttribute('data-open')) !== 'true') await toggle.click();
    await expect(toggle).toHaveAttribute('data-open', 'true');
    const picker = dialog.getByTestId('fx-route-picker');
    await expect(picker).toBeVisible();
    return picker;
}

/**
 * The picker's 2-step chains through the patched provider, once drawn: the search narrows the group to that provider
 * (an open group draws only its first 200 chains), the group is opened only when it is not already.
 */
async function chainsThroughPatched(picker: Locator): Promise<{section: Locator; rows: Locator}> {
    const search = picker.getByTestId('fx-route-search');
    await search.fill(UNCONFIGURED.toLowerCase());
    await expect(search).toHaveValue(UNCONFIGURED.toLowerCase());
    const toggle = picker.getByTestId('fx-route-chain-toggle-2');
    await expect(toggle, 'a 2-step chain group is drawn').toBeVisible({timeout: 10_000});
    if ((await toggle.getAttribute('data-expanded')) !== 'true') await toggle.click();
    await expect(toggle).toHaveAttribute('data-expanded', 'true');
    const section = picker.getByTestId('fx-route-chain-section-2');
    // A route key is `FROM-TO:CODE` per step, joined by `|`: the provider on a leg is `:CODE|` or a trailing `:CODE`.
    const rows = section.locator(`[data-route-key*=":${UNCONFIGURED}|"], [data-route-key$=":${UNCONFIGURED}"]`);
    await expect(rows.first(), `a 2-step chain through ${UNCONFIGURED} is drawn`).toBeVisible({timeout: 10_000});
    return {section, rows};
}

/** The common window, once drawn: the patched provider, a member's case. */
async function expectWindow(page: Page): Promise<Locator> {
    const modal = page.getByTestId('plugin-not-configured-modal');
    await expect(modal).toBeVisible({timeout: 5_000});
    await expect(modal).toHaveAttribute('data-plugin', UNCONFIGURED);
    await expect(modal).toHaveAttribute('data-case', 'missing_member');
    return modal;
}

/** Close the window with its own button (Escape could reach the dialog underneath): the dialog stays open. */
async function closeWindow(page: Page, modal: Locator): Promise<void> {
    await modal.getByTestId('plugin-not-configured-close').click();
    await expect(modal).toHaveCount(0);
    await expect(page.getByTestId('fx-add-pair-modal'), 'the pair dialog underneath stays open').toBeVisible();
}

/** The slugs (codes sorted, as stored) of every pair that has a saved route. */
async function pairsWithRoutes(page: Page): Promise<Set<string>> {
    const routes = await page.request.get(ROUTES_PATH);
    expect(routes.ok(), `GET ${ROUTES_PATH}: HTTP ${routes.status()}`).toBe(true);
    const items = ((await routes.json()) as {items?: Array<{base: string; quote: string}>}).items ?? [];
    return new Set(items.map((r) => [r.base, r.quote].sort().join('-')));
}

/** The routes and rates already stored on a pair, one line each; empty when the pair holds nothing. */
async function rowsOnPair(page: Page, pair: readonly [string, string]): Promise<string[]> {
    const [b, q] = [...pair].sort();
    const routes = await page.request.get(ROUTES_PATH);
    expect(routes.ok(), `GET ${ROUTES_PATH}: HTTP ${routes.status()}`).toBe(true);
    const items = ((await routes.json()) as {items?: Array<{base: string; quote: string; priority: number}>}).items ?? [];
    const taken = items.filter((r) => r.base === b && r.quote === q).map((r) => `route priority ${r.priority}`);
    const rates = await page.request.get(`${API}/backup/fx/${b}/${q}/rates?format=json`);
    expect(rates.ok(), `read ${b}-${q} rates: HTTP ${rates.status()}`).toBe(true);
    const rows = ((await rates.json()) as {rows: unknown[]}).rows;
    if (rows.length > 0) taken.push(`${rows.length} rate(s)`);
    return taken;
}

/** The pairs a test took ownership of (verified empty, then written): deleted after the test, whatever happened. */
const test = base.extend<{owned: Array<readonly [string, string]>}>({
    owned: async ({page}, use) => {
        const owned: Array<readonly [string, string]> = [];
        const failures: string[] = [];
        try {
            await use(owned);
        } finally {
            if (owned.length > 0) {
                // Off the page first: nothing still on screen reads the pair while it goes.
                await page.goto('about:blank').catch((error) => failures.push(`leave the page: ${String(error)}`));
            }
            for (const pair of owned) {
                const [b, q] = [...pair].sort();
                try {
                    const route = await page.request.delete(ROUTES_PATH, {data: [{base: b, quote: q}]});
                    expect(route.ok(), `DELETE ${ROUTES_PATH} ${b}-${q}: HTTP ${route.status()} ${await route.text()}`).toBe(true);
                    const rates = await page.request.delete(`${API}/fx/currencies/rate`, {data: [{from: b, to: q, delete_all: true}]});
                    expect(rates.ok(), `DELETE rates ${b}-${q}: HTTP ${rates.status()} ${await rates.text()}`).toBe(true);
                    expect(await rowsOnPair(page, pair), `${b}-${q} is left as it was found: empty`).toEqual([]);
                } catch (error) {
                    failures.push(`clean up ${b}-${q}: ${String(error)}`);
                }
            }
        }
        expect(failures, 'the clean-up deletes every pair the test created').toEqual([]);
    },
});

test.describe('FX pair dialog — a provider that is not configured', () => {
    // The provider list is read again while the dialog mounts: a read still in flight when the test ends would make its
    // route.fetch() fail after the test, an error outside any test that leaves the next one not run (FB7c triage).
    // Detached here with ignoreErrors, the handler is dropped instead of awaited.
    test.afterEach(async ({page}) => {
        await page.unrouteAll({behavior: 'ignoreErrors'});
    });

    test('a new pair: the route through it is switched off, a touch opens the window and adds nothing', async ({page}) => {
        const simulation = await patchProviderList(page);
        await login(page, TEST_USER);

        // The pair, from the real list: one the patched provider serves directly, and another provider too.
        const real = await realProviders(page);
        const patched = patchedEntry(real);
        // The dialog never offers a pair that already has a route (`FxPairAddModal`, `excludedForQuote`): one without.
        const configured = await pairsWithRoutes(page);
        // Never case 2's currencies: a neighbour may be saving that pair right now, and the dialog would then hide it.
        const owned = new Set(
            Object.values(OWNED_PAIR)
                .flat()
                .filter((code) => !patched.base_currencies.includes(code)),
        );
        const pairs = patched.base_currencies
            .flatMap((from) => [...(patched.target_currencies ?? [])].sort().map((to) => [from, to].sort() as [string, string]))
            .filter(([from, to]) => from !== to && !owned.has(from) && !owned.has(to) && !configured.has(`${from}-${to}`) && directProviders(real, from, to).includes(UNCONFIGURED));
        // Another route not through it: a direct one when another provider serves the pair, else a chain avoiding it (the
        // network-read catalogues can be missing on a cold lane, the static ones never are).
        const withDirect = pairs.map((pair) => ({pair, other: directProviders(real, ...pair).find((code) => code !== UNCONFIGURED)})).find(({other}) => other !== undefined);
        const chosen = withDirect ?? pairs.map((pair) => ({pair, other: undefined})).find(({pair}) => hasChainAvoidingPatched(real, ...pair));
        if (!chosen) throw new Error(`precondition: a pair with no saved route that ${UNCONFIGURED} serves directly and another route serves too: ${JSON.stringify(real.map((p) => p.code))}`);
        const [baseCode, quoteCode] = chosen.pair;
        const other = chosen.other;
        test.info().annotations.push({type: 'pair', description: `${baseCode}-${quoteCode}, other route: ${other ? `direct ${other}` : 'a 2-step chain'}`});
        expect(hasChainThroughPatched(real, baseCode, quoteCode), `premise: a 2-step chain ${baseCode}→${quoteCode} goes through ${UNCONFIGURED}`).toBe(true);

        await goToFxPage(page);
        await openAddPairModal(page);
        const dialog = page.getByTestId('fx-add-pair-modal');
        // Quote first: the base select opens the empty quote by itself on choice.
        await selectCurrency(page, dialog.getByTestId('fx-add-pair-quote'), quoteCode);
        await selectCurrency(page, dialog.getByTestId('fx-add-pair-base'), baseCode);
        const picker = await openPicker(dialog);

        // The presence barrier: a route through another provider is drawn, on.
        const onRow = other ? picker.getByTestId(`fx-route-direct-${other}`) : await chainAvoidingPatched(picker);
        await expect(onRow, `${baseCode}-${quoteCode}: a route through a configured provider is on`).toHaveAttribute('data-needs-setup', 'false', {timeout: 10_000});
        await expect(onRow).not.toHaveAttribute('aria-disabled', 'true');
        const offRow = picker.getByTestId(`fx-route-direct-${UNCONFIGURED}`);
        await expect(offRow, `the list says ${UNCONFIGURED} is not configured: its route is switched off`).toHaveAttribute('data-needs-setup', 'true');
        await expect(offRow).toHaveAttribute('aria-disabled', 'true');
        await expect(offRow, 'switched off, not disabled: reachable, so a touch can say why').toHaveJSProperty('disabled', false);
        await expect(offRow).toHaveAttribute('title', /.+/);
        await expect(offRow).toHaveAttribute('data-route-key', `${baseCode}-${quoteCode}:${UNCONFIGURED}`);
        await expect(dialog.getByTestId('fx-route-selected'), 'a new pair starts with no route').toHaveCount(0);

        // `aria-disabled` reads as «not enabled» to Playwright, so the touch is forced: prove first the row is on screen, whole.
        await offRow.scrollIntoViewIfNeeded();
        await expect(offRow).toBeInViewport({ratio: 1});
        await offRow.click({force: true});
        const modal = await expectWindow(page);
        await expect(dialog.getByTestId('fx-route-selected'), 'the touch added no route').toHaveCount(0);
        await expect(offRow, 'still offered in the picker: an added route would have left it').toBeVisible();
        await closeWindow(page, modal);
        await expect(dialog.getByTestId('fx-route-selected')).toHaveCount(0);
        await expect(offRow).toHaveAttribute('data-needs-setup', 'true');

        // A chain through the provider is switched off too.
        const {rows} = await chainsThroughPatched(picker);
        await expect(rows.first()).toHaveAttribute('data-needs-setup', 'true');
        await expect(rows.first()).toHaveAttribute('aria-disabled', 'true');
        await expect(rows.and(page.locator('[data-needs-setup="false"]')), `every chain through ${UNCONFIGURED} is switched off`).toHaveCount(0);

        expect(simulation.problems, 'the list was read from the backend and patched as planned').toEqual([]);
        expect(simulation.patched, 'the page read the patched list').toBeGreaterThan(0);
        // Not saved: the dialog is left open, the page closes with the test.
    });

    test('a pair whose saved route goes through it: the triangle opens the window, its other routes stay on', async ({page, owned}) => {
        const pair = OWNED_PAIR[test.info().project.name];
        if (!pair) throw new Error(`no owned pair declared for project "${test.info().project.name}": add one to OWNED_PAIR`);
        const [baseCode, quoteCode] = [...pair].sort();
        const slug = `${baseCode}-${quoteCode}`;

        await login(page, TEST_USER);
        const real = await realProviders(page);
        patchedEntry(real);
        expect(directProviders(real, baseCode, quoteCode), `premise: ${UNCONFIGURED} converts ${slug} in one step`).toContain(UNCONFIGURED);
        expect(hasChainThroughPatched(real, baseCode, quoteCode), `premise: a 2-step chain ${baseCode}→${quoteCode} goes through ${UNCONFIGURED}`).toBe(true);

        // Ownership first, writes after: a row already on the pair is someone else's, and the clean-up deletes the pair.
        expect(await rowsOnPair(page, pair), `${slug} must be empty for this test to own it: pick currencies no seed row and no other spec uses`).toEqual([]);
        owned.push(pair);
        const created = await page.request.post(ROUTES_PATH, {data: [{base: baseCode, quote: quoteCode, priority: 1, chain_steps: [{from: baseCode, to: quoteCode, provider: UNCONFIGURED}]}]});
        expect(created.ok(), `create the ${slug} route through ${UNCONFIGURED}: HTTP ${created.status()} ${await created.text()}`).toBe(true);

        // Patched before the page builds its graph; the sync is the test's, so the bank is never asked.
        const simulation = await patchProviderList(page);
        const syncs: string[] = [];
        await page.route(
            (url) => url.pathname === SYNC_PATH,
            async (route: Route) => {
                syncs.push(route.request().postData() ?? '');
                await route.abort();
            },
        );

        await goToFxDetailPage(page, slug);
        await page.getByTestId('fx-detail-provider-btn').click();
        const dialog = page.getByTestId('fx-add-pair-modal');
        await expect(dialog).toBeVisible({timeout: 5_000});

        // The saved route, read back, carries the triangle: the proof the patched list reached the picker.
        const saved = dialog.getByTestId('fx-route-selected');
        await expect(saved, 'the pair has the one route this test saved').toHaveCount(1, {timeout: 10_000});
        await expect(saved).toHaveAttribute('data-route-key', `${baseCode}-${quoteCode}:${UNCONFIGURED}`);
        const triangle = saved.getByTestId('fx-route-needs-setup');
        await expect(triangle, `${UNCONFIGURED} is not configured: the saved route says so`).toBeVisible({timeout: 10_000});
        await expect(triangle).toHaveAttribute('data-provider', UNCONFIGURED);
        // A standard Button (85 BTN-2c): the setup hint is its name, aria-label; no native title.
        await expect(triangle).toHaveAttribute('aria-label', /.+/);

        await triangle.click();
        const modal = await expectWindow(page);
        await closeWindow(page, modal);
        await expect(saved, 'the saved route is kept').toHaveCount(1);
        await expect(saved.getByTestId('fx-route-needs-setup')).toBeVisible();

        // The pair already uses the provider: its other routes are never switched off.
        const picker = await openPicker(dialog);
        const {section, rows} = await chainsThroughPatched(picker);
        await expect(rows.first(), `${UNCONFIGURED} is on the pair: its chains stay on`).toHaveAttribute('data-needs-setup', 'false');
        await expect(rows.first()).not.toHaveAttribute('aria-disabled', 'true');
        await expect(section.locator('[data-needs-setup="true"]'), 'no chain of the group is switched off').toHaveCount(0);

        expect(simulation.problems, 'the list was read from the backend and patched as planned').toEqual([]);
        expect(simulation.patched, 'the page read the patched list').toBeGreaterThan(0);
        expect(syncs, 'nothing asked the bank for the pair').toEqual([]);
        // Not saved: the clean-up leaves the page and deletes the pair.
    });
});
