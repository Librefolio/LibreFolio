/**
 * Gallery, Assets — the Provider Data Comparison dialog (`assets/create-provider-compare`), as a new asset meets it
 * right after a Search Online result is picked (mkdocs_src/docs/user/assets/create-edit.en.md, «Check the provider's
 * data»): an identifier row with its main-code chooser, a Type row drawn as icon badges, a distribution row.
 *
 * ## The flow
 *
 * Assets → Add asset; under More Info one sector row typed by hand (the editor's «+» gives the first sector at 100%),
 * as a user who starts describing the fund before searching; then the fund's ISIN typed into Search Online and the one
 * result picked. The pick (AssetModal.svelte, `applySearchResult`) fills the empty form from the result — name, type
 * ETF, currency, ticker `NWGE` — and asks the provider twice: a connection test (`current_price` + `history`,
 * `autoTriggerProbe`) and its details (`metadata`, `fetchAndCompareMetadata`). The details fill every field still
 * empty (the ISIN, the description, the geographic split) and three differ, so the comparison opens with three rows:
 * - `identifier_ticker`: `NWGE` from the search against `NWGE.MI`, the listing the provider's details name — two codes
 *   of one type, so the row is the chooser (IdentifierPrimaryChooser.svelte) with the provider's code proposed;
 * - `asset_type`: ETF against Equity ETF, a refinement, so it is offered (`isFamilyOnlyProposal` is false);
 * - `sector_area`: the sector typed by hand against the provider's split.
 * The ticker, not an ISIN, carries the identifier row: an ISIN row adds the placement-code note (`isIsin`), and on the
 * phone, where the dialog's body stays capped at 60vh, the Type row would then leave the screen.
 *
 * Nothing is created: the dialog and the form are both cancelled, the form through its discard confirmation. The fund
 * is invented — `Northwind Global Equity UCITS ETF`, ISIN `IE000NWGE006` (a valid check digit) — so the duplicate-name
 * check and the reuse prompt (wizard only) never fire.
 *
 * ## The screen
 *
 * The dialog's body is capped at 60% of the screen (ProviderComparisonModal.svelte, `max-h-[60vh]`) and its three rows are
 * taller than that on either project. On the desktop only — coordinator's decision, provisional, the simulation shot's rule
 * (galleryRiskLab.ts, «Screens taller than the desktop's») — {@link fitScreenToCompareDialog} gives the shot a screen tall
 * enough for the body to stop scrolling, width and scale unchanged, so the whole dialog and its three rows are in one image;
 * {@link restoreCompareScreen} puts the project's screen back right after the shot. The mobile project keeps its phone,
 * with the body scrolled to the identifier row and the Type row (`revealRows`).
 *
 * ## What is mocked, and why
 *
 * The gallery is offline (galleryReportSets.ts, `guardGalleryOffline`): it answers every search as "no results" and
 * aborts every provider probe, recording it as a failure. {@link mockProviderCompare} registers two routes after it —
 * Playwright tries the routes registered last first — that answer this one fund instead:
 * - `GET /assets/provider/search/stream` (and the REST search the client falls back to): one `provider_results` event per
 *   provider asked, the fund under `yfinance`, nothing under the others, then `done` (asset_sources/search.py);
 * - `POST /assets/provider/probe` for `yfinance`/`NWGE`: the operations asked, the metadata as the backend sends it
 *   (`FAAssetPatchItem.model_dump(mode="json")`: decimals as strings).
 * Every body is checked against the generated Zod schemas before it is sent, as the client checks it on arrival. Any
 * other search is answered empty; any other probe falls through to the guard, which aborts it — and is listed in
 * `problems`. No price is asked: a sync only follows a save, which never happens.
 */

import type {APIResponse} from '@playwright/test';
import {schemas} from '../../src/lib/api/generated';
import {expect, type Locator, type Page} from './playwright';
import {expectNoToast, waitForStillness} from './galleryReportSets';
import {imagesSettled, parkPointer} from './galleryRiskLab';

/** The provider the fund is found with: a registered searchable plugin that takes tickers (yahoo_finance.py). */
const PROVIDER = 'yfinance';

/** The invented fund: everything the search and the provider say about it. */
export const COMPARE_FUND = {
    isin: 'IE000NWGE006',
    name: 'Northwind Global Equity UCITS ETF',
    currency: 'EUR',
    searchTicker: 'NWGE',
    providerTicker: 'NWGE.MI',
    searchType: 'ETF',
    providerType: 'ETF_STOCK',
    /** The provider's split, three sectors (FinancialSector names, so every language translates them). */
    sectors: {Technology: '0.45', Financials: '0.30', 'Health Care': '0.25'},
    countries: {USA: '0.68', JPN: '0.06', GBR: '0.04', Other: '0.22'},
} as const;

/** The three rows the dialog opens with, in its own order (ProviderComparisonModal.svelte, `DIFF_FIELD_SECTIONS`). */
export const COMPARE_FIELDS = ['identifier_ticker', 'asset_type', 'sector_area'] as const;

const SEARCH_STREAM_PATH = '/api/v1/assets/provider/search/stream';
const SEARCH_PATH = '/api/v1/assets/provider/search';
const PROBE_PATH = '/api/v1/assets/provider/probe';

/** The spec's `waitForMotionSettled`: nothing is animating in the scope. */
export type MotionSettled = (scope: Locator, what: string) => Promise<void>;

/** What the routes answered: the searches by query, the probes by their operations, and what they could not answer. */
export interface ProviderCompareMock {
    searches: string[];
    probes: string[];
    problems: string[];
}

type ProbeRequest = {provider_code?: unknown; identifier?: unknown; identifier_type?: unknown; operations?: unknown};

/** Today and a year ago, in the runner's local time: the dates a fresh connection test reports. */
function isoDay(offsetDays = 0): string {
    const day = new Date();
    day.setDate(day.getDate() + offsetDays);
    return `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`;
}

/** The provider codes a search names, as the backend reads them: repeated or comma-separated. */
function searchedProviders(url: URL): string[] {
    return url.searchParams
        .getAll('providers')
        .flatMap((value) => value.split(','))
        .map((code) => code.trim())
        .filter((code) => code !== '');
}

function searchResult() {
    return schemas.FAProviderSearchResultItem.parse({
        identifier: COMPARE_FUND.searchTicker,
        identifier_type: 'TICKER',
        display_name: COMPARE_FUND.name,
        provider_code: PROVIDER,
        currency: COMPARE_FUND.currency,
        asset_type: COMPARE_FUND.searchType,
        provider_url: null,
        provider_params: null,
        via_web: false,
    });
}

/** The provider's details, the shape the backend dumps (`FAAssetPatchItem`, mode json): every field present, decimals as text. */
function metadataPatch() {
    const patch = {
        asset_id: 0,
        display_name: COMPARE_FUND.name,
        currency: COMPARE_FUND.currency,
        asset_type: COMPARE_FUND.providerType,
        icon_url: null,
        quote_base_quantity: null,
        classification_params: {
            short_description: 'Global developed-market equities, physically replicated, accumulating.',
            geographic_area: {distribution: {...COMPARE_FUND.countries}},
            sector_area: {distribution: {...COMPARE_FUND.sectors}},
        },
        active: null,
        is_benchmark: null,
        user_url: null,
        identifier_isin: COMPARE_FUND.isin,
        identifier_ticker: COMPARE_FUND.providerTicker,
        identifier_cusip: null,
        identifier_sedol: null,
        identifier_figi: null,
        identifier_uuid: null,
        identifier_other: null,
    };
    schemas.FAAssetPatchItem.parse(patch);
    return patch;
}

function probeAnswer(identifier: string, operations: readonly string[]) {
    const body = {
        provider_code: PROVIDER,
        identifier,
        total_execution_time_ms: 18,
        provider_url: null,
        ...(operations.includes('current_price') ? {current_price: {success: true, execution_time_ms: 6, value: '84.12', currency: COMPARE_FUND.currency, as_of_date: isoDay()}} : {}),
        ...(operations.includes('history') ? {history: {success: true, execution_time_ms: 9, points_count: 251, date_range: `${isoDay(-365)} → ${isoDay()}`}} : {}),
        ...(operations.includes('metadata') ? {metadata: {success: true, execution_time_ms: 11, patch_data: metadataPatch()}} : {}),
    };
    schemas.FAProviderProbeResponse.parse(body);
    return body;
}

async function jsonOk<T>(response: APIResponse, what: string): Promise<T> {
    expect(response.ok(), `${what} answered HTTP ${response.status()}`).toBe(true);
    return (await response.json()) as T;
}

/**
 * Answer the fund's search and its provider probes (see the module notes), on every page load of the test: routes stay with
 * the page. Register after the gallery's outer beforeEach — inside the test — so they are tried before the offline guard.
 * Fails at once when the registry no longer offers `yfinance` as a searchable provider: the result would be filed under a
 * provider the search never asks.
 */
export async function mockProviderCompare(page: Page): Promise<ProviderCompareMock> {
    const providers = await jsonOk<Array<{code?: string; supports_search?: boolean}>>(await page.request.get('/api/v1/assets/provider'), 'GET /api/v1/assets/provider');
    expect(
        providers.some((provider) => provider.code === PROVIDER && provider.supports_search === true),
        `${PROVIDER} is not a searchable provider of this backend`,
    ).toBe(true);
    // Every body checked once, here: a schema that moved fails the test now, with Zod's own message, not as a hung request.
    searchResult();
    probeAnswer(COMPARE_FUND.searchTicker, ['current_price', 'history', 'metadata']);
    const mock: ProviderCompareMock = {searches: [], probes: [], problems: []};

    await page.route(
        (url) => url.pathname === SEARCH_STREAM_PATH || url.pathname === SEARCH_PATH,
        async (route) => {
            if (route.request().method() !== 'GET') return route.fallback();
            const url = new URL(route.request().url());
            const query = (url.searchParams.get('q') ?? '').trim();
            mock.searches.push(query);
            const codes = searchedProviders(url);
            try {
                const results = query.toUpperCase() === COMPARE_FUND.isin ? [searchResult()] : [];
                if (url.pathname === SEARCH_PATH) {
                    const body = schemas.FAProviderSearchResponse.parse({query, total_results: results.length, results, providers_queried: codes, providers_with_errors: []});
                    await route.fulfill({json: body});
                    return;
                }
                if (results.length > 0 && !codes.includes(PROVIDER)) mock.problems.push(`the search did not ask ${PROVIDER}: ${url.search}`);
                const events = [...codes.map((code) => ({event: 'provider_results', provider_code: code, results: code === PROVIDER ? results : []})), {event: 'done', total_results: results.length, providers_queried: codes, providers_with_errors: []}];
                await route.fulfill({status: 200, contentType: 'text/event-stream', body: events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join('')});
            } catch (error) {
                mock.problems.push(`the search of "${query}" could not be answered: ${String(error)}`);
                await route.abort().catch(() => undefined);
            }
        },
    );

    await page.route(
        (url) => url.pathname === PROBE_PATH,
        async (route) => {
            if (route.request().method() !== 'POST') return route.fallback();
            let request: ProbeRequest | null = null;
            try {
                request = route.request().postDataJSON() as ProbeRequest;
            } catch {
                /* not JSON: told apart below */
            }
            const raw = request?.operations;
            const operations = Array.isArray(raw) ? raw.filter((operation): operation is string => typeof operation === 'string') : [];
            if (request === null || request.provider_code !== PROVIDER || request.identifier !== COMPARE_FUND.searchTicker || request.identifier_type !== 'TICKER' || operations.length === 0) {
                // The offline guard aborts it and records it: the test fails at its end either way, this names it.
                mock.problems.push(`an unexpected provider probe: ${route.request().postData() ?? '(no body)'}`);
                return route.fallback();
            }
            mock.probes.push([...operations].sort().join('+'));
            try {
                await route.fulfill({json: probeAnswer(COMPARE_FUND.searchTicker, operations)});
            } catch (error) {
                mock.problems.push(`the probe ${operations.join('+')} could not be answered: ${String(error)}`);
                await route.abort().catch(() => undefined);
            }
        },
    );
    return mock;
}

/**
 * Scroll the comparison's body — its scroll box, capped at 60vh — so the identifier row and the Type row are both on show,
 * with as much as fits of the distribution row under them; when the two rows do not fit together, the Type row is kept
 * whole and the identifier row loses its top. Only that box scrolls.
 */
async function revealRows(dialog: Locator): Promise<void> {
    await dialog.evaluate((root) => {
        const card = (field: string) => root.querySelector(`[data-testid="comparison-card"][data-field="${field}"]`);
        const first = card('identifier_ticker');
        const last = card('asset_type');
        const box = root.querySelector('[data-testid="comparison-body"]');
        if (!(first instanceof HTMLElement) || !(last instanceof HTMLElement) || !(box instanceof HTMLElement)) throw new Error('the comparison has no identifier row, no Type row or no body');
        if (box.scrollHeight <= box.clientHeight) return;
        const frame = box.getBoundingClientRect();
        const from = first.getBoundingClientRect().top - frame.top + box.scrollTop - 8;
        const to = last.getBoundingClientRect().bottom - frame.top + box.scrollTop + 8;
        box.scrollTop = to - from <= box.clientHeight ? from : to - box.clientHeight;
    });
    await waitForStillness(dialog.getByTestId('comparison-body'), 'the comparison body');
}

/**
 * From the Assets page (loaded, its language and theme set), open the comparison as the module notes describe it and end on
 * it framed: its three rows, the provider's ticker proposed as the main code, the form behind it settled — the connection
 * test passed, the details read — and the dialog done opening. Returns the dialog (`comparison-modal`, its backdrop).
 */
export async function openProviderCompare(page: Page, motionSettled: MotionSettled): Promise<Locator> {
    await page.getByTestId('assets-add-button').click();
    const modal = page.getByTestId('asset-modal');
    const form = modal.getByTestId('asset-modal-form');
    await expect(form).toHaveAttribute('data-snapshot-ready', 'true', {timeout: 5_000});
    const search = modal.getByTestId('asset-tour-search');
    // Search Online asks only the providers it has listed: the list comes from the backend, after the modal opens.
    await expect(search.getByTestId(`asset-search-provider-${PROVIDER}`), `Search Online does not ask ${PROVIDER}`).toHaveAttribute('data-selected', 'true', {timeout: 10_000});

    // More Info opens by itself only for an asset with identifiers: a new one starts closed.
    const moreInfo = modal.getByTestId('asset-modal-more-info');
    if ((await moreInfo.getAttribute('data-expanded')) !== 'true') await moreInfo.click();
    await expect(moreInfo).toHaveAttribute('data-expanded', 'true');
    const sectors = modal.getByTestId('distribution-editor-sector');
    const typed = sectors.locator('[data-testid^="distribution-entry-sector-"]');
    await expect(typed).toHaveCount(0);
    await sectors.getByTestId('distribution-add-sector').click();
    await expect(typed).toHaveCount(1);
    const typedSector = ((await typed.getAttribute('data-testid')) ?? '').slice('distribution-entry-sector-'.length);
    if (typedSector === '') throw new Error('the typed sector row carries no key');

    // The ISIN in Search Online (its input has no test id: it is the one text field of the search block), then the fund.
    await search.locator('[data-search-autocomplete] input[type="text"]').fill(COMPARE_FUND.isin);
    const results = search.getByTestId('asset-search-results');
    await expect(results, 'the search found nothing').toHaveAttribute('data-state', 'results', {timeout: 10_000});
    const hit = results.locator(`[data-testid^="asset-search-result-"][data-provider="${PROVIDER}"][data-identifier="${COMPARE_FUND.searchTicker}"]`);
    await expect(hit).toHaveCount(1);
    await hit.click();

    const dialog = page.getByTestId('comparison-modal');
    await expect(dialog, 'the pick opened no comparison').toBeVisible({timeout: 15_000});
    const body = dialog.getByTestId('comparison-body');
    await expect(body, 'the comparison does not hold exactly the three rows the provider contradicts').toHaveAttribute('data-total-count', String(COMPARE_FIELDS.length));
    await expect(body, 'every row starts ticked').toHaveAttribute('data-selected-count', String(COMPARE_FIELDS.length));
    for (const field of COMPARE_FIELDS) await expect(body.locator(`[data-testid="comparison-card"][data-field="${field}"]`)).toHaveCount(1);

    const chooser = body.getByTestId('comparison-chooser-identifier_ticker');
    const proposed = chooser.getByTestId(`comparison-chooser-identifier_ticker-option-${COMPARE_FUND.providerTicker}`);
    await expect(proposed, "the provider's code is not proposed as the main one").toHaveAttribute('aria-checked', 'true');
    await expect(chooser.getByTestId(`comparison-chooser-identifier_ticker-option-${COMPARE_FUND.searchTicker}`)).toHaveAttribute('aria-checked', 'false');
    const currentType = body.getByTestId('comparison-current-asset_type').getByTestId('comparison-type-badge');
    const providerType = body.getByTestId('comparison-provider-asset_type').getByTestId('comparison-type-badge');
    await expect(currentType).toHaveAttribute('data-type', COMPARE_FUND.searchType);
    await expect(providerType).toHaveAttribute('data-type', COMPARE_FUND.providerType);
    await expect(body.getByTestId('comparison-current-sector_area').locator(`[data-testid="comparison-dist-entry"][data-dist-key="${typedSector}"]`)).toHaveAttribute('data-dist-pct', '100.00%');
    await expect(body.getByTestId('comparison-provider-sector_area').getByTestId('comparison-dist-entry')).toHaveCount(Object.keys(COMPARE_FUND.sectors).length);

    // The form behind it settled: the details read, the connection test passed (its status icon is in the dimmed form).
    await expect(form).toHaveAttribute('data-busy', 'false');
    await expect(modal.getByTestId('asset-modal-provider-status')).toHaveAttribute('data-status', 'passed', {timeout: 10_000});

    await motionSettled(dialog, 'the comparison dialog');
    await revealRows(dialog);
    await expect(proposed, 'the main-code chooser is out of the shot').toBeInViewport();
    await expect(providerType, 'the Type row is out of the shot').toBeInViewport();
    return dialog;
}

/**
 * The dialog's own box — ModalBase's content, with the title above the body and the buttons under it — found as the body's
 * parent: it carries no test id of its own. `comparison-modal` is the backdrop around it, as large as the screen.
 */
function dialogBox(dialog: Locator): Locator {
    return dialog.getByTestId('comparison-body').locator('..');
}

/** The last steps before the shot: the pointer parked, the type icons loaded, nothing animating or moving, no toast. */
export async function settleProviderCompareShot(page: Page, dialog: Locator, motionSettled: MotionSettled): Promise<void> {
    await parkPointer(page);
    await imagesSettled(dialog);
    await motionSettled(dialog, 'the comparison dialog');
    await waitForStillness(dialogBox(dialog), 'the comparison dialog');
    await expectNoToast(page);
}

/** The screen a page had before {@link fitScreenToCompareDialog} grew it: what {@link restoreCompareScreen} puts back. */
const screensBeforeCompare = new WeakMap<Page, {width: number; height: number}>();

/**
 * DESKTOP ONLY — the simulation shot's rule (galleryRiskLab.ts, «Screens taller than the desktop's»), coordinator's decision,
 * provisional. The body is capped at 60% of the screen and the dialog at 90% (ProviderComparisonModal.svelte, ModalBase.svelte),
 * so the screen becomes tall enough for the whole body, `ceil((scrollHeight + 1) / 0.6)`, and for the whole dialog around it, never
 * shorter than the project's, width and scale unchanged — measured with the dialog still, every combination (its sentences wrap
 * differently in each language), and logged (📐) under `shot`. Ends on the body no longer scrolling, the dialog settled again and
 * the dialog and its three rows asserted whole in the shot. {@link restoreCompareScreen}, right after the shot, puts the
 * project's screen back. Reverting the decision is deleting the one call in the spec.
 */
export async function fitScreenToCompareDialog(page: Page, dialog: Locator, shot: string, motionSettled: MotionSettled): Promise<void> {
    const screen = page.viewportSize();
    if (!screen) throw new Error('the page has no viewport');
    const own = screensBeforeCompare.get(page) ?? screen;
    screensBeforeCompare.set(page, own);
    const body = dialog.getByTestId('comparison-body');
    const box = dialogBox(dialog);
    await motionSettled(dialog, 'the comparison dialog');
    await waitForStillness(box, 'the comparison dialog');
    const measured = await body.evaluate((element) => {
        const content = element.parentElement;
        if (!content?.querySelector('[data-testid="comparison-cancel"]')) throw new Error("the comparison body's parent is not the dialog box that holds its buttons");
        return {scroll: element.scrollHeight, client: element.clientHeight, dialog: content.getBoundingClientRect().height};
    });
    // scrollHeight is a whole number of pixels: one more keeps a fraction of a pixel from leaving the body scrolling.
    const whole = measured.scroll + 1;
    // The dialog as tall as it is with its whole body: its title and buttons, plus the body unscrolled.
    const block = Math.ceil(measured.dialog - measured.client) + whole;
    // At 90% the dialog keeps at least 5% of the screen above and below it, more than the backdrop's own 16 px padding.
    const height = Math.max(own.height, Math.ceil(whole / 0.6), Math.ceil(block / 0.9));
    if (height !== screen.height) await page.setViewportSize({width: own.width, height});
    console.log(`  📐 ${shot}: block ${block} px (body ${measured.scroll} px) → screen ${own.width}×${height}`);
    await expect.poll(() => body.evaluate((element) => element.scrollHeight <= element.clientHeight), {message: 'the comparison body still scrolls on the fitted screen'}).toBe(true);
    await settleProviderCompareShot(page, dialog, motionSettled);
    await expect(box, 'the comparison dialog is not whole in the shot').toBeInViewport({ratio: 1});
    for (const field of COMPARE_FIELDS) {
        await expect(body.locator(`[data-testid="comparison-card"][data-field="${field}"]`), `the ${field} row is not whole in the shot`).toBeInViewport({ratio: 1});
    }
}

/**
 * Put back the screen the page had before {@link fitScreenToCompareDialog} and end on the page laid out for it; a no-op when
 * nothing grew it (the mobile project, or the decision reverted). Called right after the tall shot, inside the same combination:
 * the next one's asset form opens on the project's screen.
 */
export async function restoreCompareScreen(page: Page): Promise<void> {
    const own = screensBeforeCompare.get(page);
    if (!own) return;
    screensBeforeCompare.delete(page);
    const screen = page.viewportSize();
    if (screen?.width === own.width && screen.height === own.height) return;
    await page.setViewportSize(own);
    await expect.poll(() => page.evaluate(() => window.innerHeight), {message: "the screen did not go back to the project's"}).toBe(own.height);
}

/** Cancel the comparison, then the asset form through its discard confirmation; end on both gone, nothing saved. */
export async function closeProviderCompare(page: Page): Promise<void> {
    const dialog = page.getByTestId('comparison-modal');
    await dialog.getByTestId('comparison-cancel').click();
    await expect(dialog).toHaveCount(0);
    const modal = page.getByTestId('asset-modal');
    await modal.getByTestId('asset-modal-cancel').click();
    // The pick filled the form, so it is dirty and asks first.
    const discard = page.getByTestId('asset-modal-discard-confirm');
    await expect(discard).toBeVisible();
    await discard.locator('..').getByTestId('confirm-modal-confirm').click();
    await expect(modal).toHaveCount(0);
}
